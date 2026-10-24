"""Tax constants for the withholding estimator — read from SATC's crosswalk.

The standalone ``twe`` tool shipped its own ``data/<year>.json``. Here we instead
read SATC's dated, cited tax-law crosswalk (``configs/crosswalk/federal/*.yaml``)
so the estimator inherits citations, provenance, multi-year support, and the
"never guess a value" discipline. :class:`TaxTables` is the typed view the engine
consumes; :func:`load_tax_tables` resolves the year and REFUSES one that is not fully on
file -- it never runs a year on another year's figures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from satc.crosswalk import CrosswalkLibrary
from satc.crosswalk.loader import Crosswalk

# twe filing-status labels -> crosswalk keys.
_STATUS_TO_XWALK = {
    "single": "single",
    "married_jointly": "mfj",
    "married_separately": "mfs",
    "head_of_household": "hoh",
}
_UNMARRIED = {"single", "head_of_household"}


def _dec(value) -> Decimal:
    return Decimal(str(value))


@dataclass(slots=True)
class Bracket:
    rate: Decimal
    up_to: Decimal | None


class TaxTables:
    """A typed, crosswalk-backed view of the federal constants the engine needs."""

    def __init__(self, crosswalk: Crosswalk) -> None:
        self._x = crosswalk
        self.tax_year = crosswalk.tax_year

    # -- helpers ----------------------------------------------------------
    def _v(self, name: str):
        value = self._x.value(name)
        if value is None:
            raise KeyError(f"crosswalk parameter '{name}' is not published for "
                           f"{self._x.jurisdiction} {self._x.tax_year}")
        return value

    def _by_status(self, name: str, status: str) -> Decimal:
        return _dec(self._v(name)[_STATUS_TO_XWALK[status]])

    # -- deductions -------------------------------------------------------
    def standard_deduction(self, status: str) -> Decimal:
        return self._by_status("standard_deduction", status)

    def extra_standard_deduction(self, status: str) -> Decimal:
        extra = self._v("additional_std_deduction_age_or_blind")
        return _dec(extra["unmarried"] if status in _UNMARRIED else extra["married_per_spouse"])

    # -- ordinary brackets ------------------------------------------------
    def ordinary_brackets(self, status: str) -> list[Bracket]:
        raw = self._v(f"brackets_{_STATUS_TO_XWALK[status]}")
        return [Bracket(rate=_dec(b["rate"]),
                        up_to=None if b.get("up_to") is None else _dec(b["up_to"]))
                for b in raw]

    # -- preferential capital-gains thresholds ----------------------------
    def capital_gains_thresholds(self, status: str) -> tuple[Decimal, Decimal]:
        return (self._by_status("ltcg_0_pct_max", status),
                self._by_status("ltcg_15_pct_max", status))

    def capital_gains_rates(self) -> tuple[Decimal, Decimal, Decimal]:
        """The 0 / 15 / 20 percent preferential rates, in band order.

        Read from the dated table like every other rate. They were literals in
        `engine.py` until 7 September 2026 -- the only tax constants in the
        estimator carrying no citation, in a file whose entire discipline is that
        a reader can check each figure against the law.
        """
        return (_dec(self._v("ltcg_rate_0")),
                _dec(self._v("ltcg_rate_15")),
                _dec(self._v("ltcg_rate_20")))

    # -- payroll / SE / surtaxes ------------------------------------------
    @property
    def ss_wage_base(self) -> Decimal:
        return _dec(self._v("ss_wage_base"))

    @property
    def se_net_earnings_factor(self) -> Decimal:
        return _dec(self._v("se_net_earnings_factor"))

    @property
    def se_social_security_rate(self) -> Decimal:
        return _dec(self._v("se_social_security_rate"))

    @property
    def se_minimum_net_earnings(self) -> Decimal:
        """Below this, Schedule SE stops and no SE tax is owed (line 4c)."""
        return _dec(self._v("se_minimum_net_earnings"))

    @property
    def se_medicare_rate(self) -> Decimal:
        return _dec(self._v("se_medicare_rate"))

    def additional_medicare_threshold(self, status: str) -> Decimal:
        return self._by_status("addl_medicare_threshold", status)

    @property
    def additional_medicare_rate(self) -> Decimal:
        return _dec(self._v("addl_medicare_rate"))

    def niit_threshold(self, status: str) -> Decimal:
        return self._by_status("niit_threshold", status)

    @property
    def niit_rate(self) -> Decimal:
        return _dec(self._v("niit_rate"))

    # -- itemized deductions (Schedule A) ---------------------------------
    @property
    def salt_cap(self) -> Decimal:
        return _dec(self._v("salt_deduction_cap"))

    @property
    def salt_phasedown_threshold(self) -> Decimal:
        return _dec(self._v("salt_phasedown_threshold"))

    @property
    def salt_phasedown_rate(self) -> Decimal:
        return _dec(self._v("salt_phasedown_rate"))

    @property
    def salt_floor(self) -> Decimal:
        return _dec(self._v("salt_floor"))

    @property
    def medical_agi_floor(self) -> Decimal:
        return _dec(self._v("medical_agi_floor"))

    def capital_loss_limit(self, status: str) -> Decimal:
        return _dec(self._v("capital_loss_limit")["mfs" if status == "married_separately" else "other"])

    def charity_nonitemizer_max(self, status: str) -> Decimal:
        """Zero in a year that has no such deduction (it starts in 2026)."""
        raw = self._x.value("charity_nonitemizer_max")
        if raw is None:
            return Decimal("0")
        return _dec(raw["mfj" if status == "married_jointly" else "other"])

    @property
    def charity_itemized_floor_pct(self) -> Decimal:
        return _dec(self._x.value("charity_itemized_floor_pct", 0))

    # -- Schedule 1-A -----------------------------------------------------
    def _joint(self, name: str, status: str) -> Decimal:
        return _dec(self._v(name)["mfj" if status == "married_jointly" else "other"])

    @property
    def tips_max(self) -> Decimal:
        return _dec(self._v("tips_deduction_max"))

    def overtime_max(self, status: str) -> Decimal:
        return self._joint("overtime_deduction_max", status)

    def tips_overtime_phaseout_start(self, status: str) -> Decimal:
        return self._joint("tips_overtime_phaseout_start", status)

    @property
    def tips_overtime_phaseout_per_1000(self) -> Decimal:
        return _dec(self._v("tips_overtime_phaseout_per_1000"))

    @property
    def car_loan_max(self) -> Decimal:
        return _dec(self._v("car_loan_interest_max"))

    def car_loan_phaseout_start(self, status: str) -> Decimal:
        return self._joint("car_loan_phaseout_start", status)

    @property
    def car_loan_phaseout_per_1000(self) -> Decimal:
        return _dec(self._v("car_loan_phaseout_per_1000"))

    @property
    def senior_amount(self) -> Decimal:
        return _dec(self._v("senior_deduction_amount"))

    def senior_phaseout_start(self, status: str) -> Decimal:
        return self._joint("senior_deduction_phaseout_start", status)

    @property
    def senior_phaseout_rate(self) -> Decimal:
        return _dec(self._v("senior_deduction_phaseout_rate"))

    # -- credits ------------------------------------------------------------
    @property
    def ctc_per_child(self) -> Decimal:
        return _dec(self._v("ctc_per_child"))

    @property
    def odc_per_dependent(self) -> Decimal:
        return _dec(self._v("odc_per_dependent"))

    @property
    def actc_max_per_child(self) -> Decimal:
        return _dec(self._v("ctc_refundable_max"))

    def ctc_phaseout_threshold(self, status: str) -> Decimal:
        raw = self._v("ctc_phaseout_threshold")
        return _dec(raw["mfj"] if status == "married_jointly" else raw["unmarried"])

    @property
    def ctc_phaseout_per_1000(self) -> Decimal:
        return _dec(self._v("ctc_phaseout_rate_per_1000"))

    @property
    def actc_earned_income_floor(self) -> Decimal:
        return _dec(self._v("actc_earned_income_floor"))

    @property
    def actc_earned_income_rate(self) -> Decimal:
        return _dec(self._v("actc_earned_income_rate"))

    def eitc_row(self, status: str, children: int) -> dict[str, Decimal]:
        """One column of the revenue procedure's EITC table."""
        col = f"c{min(max(children, 0), 3)}"
        band = "mfj" if status == "married_jointly" else "other"
        return {
            "max_credit": _dec(self._v("eitc_max_credit")[col]),
            "earned_income_amount": _dec(self._v("eitc_earned_income_amount")[col]),
            "threshold": _dec(self._v("eitc_threshold_phaseout")[band][col]),
            "completed": _dec(self._v("eitc_completed_phaseout")[band][col]),
        }

    @property
    def eitc_investment_income_limit(self) -> Decimal:
        return _dec(self._v("eitc_investment_income_limit"))

    # -- QBI ------------------------------------------------------------------
    @property
    def qbi_rate(self) -> Decimal:
        return _dec(self._v("qbi_rate"))

    def qbi_threshold(self, status: str) -> Decimal:
        return self._by_status("qbi_threshold", status)

    @property
    def qbi_minimum(self) -> tuple[Decimal, Decimal]:
        """(minimum deduction, QBI needed for it); zeros before 2026."""
        return (_dec(self._x.value("qbi_minimum_deduction", 0)),
                _dec(self._x.value("qbi_minimum_qbi", 0)))

    # -- payments -------------------------------------------------------------
    @property
    def est_tax_due_dates(self) -> list[str]:
        return [str(d) for d in self._v("est_tax_due_dates")]

    @property
    def underpayment_penalty_floor(self) -> Decimal:
        return _dec(self._v("underpayment_penalty_floor"))

    @property
    def addl_medicare_employer_threshold(self) -> Decimal:
        return _dec(self._v("addl_medicare_employer_withholding_threshold"))

    # -- estimated-tax safe harbor ----------------------------------------
    def safe_harbor(self) -> dict[str, float]:
        x = self._x
        return {
            "current_year_pct": float(x.value("est_tax_safe_harbor_pct_current")),
            "prior_year_pct": float(x.value("est_tax_safe_harbor_pct_prior")),
            "prior_year_pct_high_income": float(x.value("est_tax_safe_harbor_pct_prior_high_agi")),
            "high_income_agi_threshold": float(x.value("est_tax_high_agi_threshold")),
            "high_income_agi_threshold_mfs": float(x.value("est_tax_high_agi_threshold_mfs")),
        }


# ---------------------------------------------------------------------------
# Year resolution -- REFUSE a year that is not fully on file, never borrow one
# ---------------------------------------------------------------------------
#
# THE ESTIMATOR USED TO FALL BACK. Asked for 2026 while the 2026 file was a
# TCJA-sunset fixture, it ran the 2025 table and said so in a note under the
# result, which is the one place a busy preparer does not read. The firm,
# 17 October 2026, asking for this estimator: "also needs to be built with
# checks to ensure we don't accidentally use it without updating it for the
# right year".
#
# So three things are now true, and each has a test:
#
#   1. A year is OFFERED only when every parameter in REQUIRED is on file and
#      in force for it (`test_every_year_the_estimator_offers_is_complete.py`).
#   2. A year that is asked for and not offered RAISES, naming what is missing
#      and which file to add. It is never swapped for another year.
#   3. When the calendar has moved past the newest year on file, `staleness()`
#      says so, the screen shows it above the form, and from 1 January the test
#      suite goes red until the new year's file exists.

#: Every crosswalk parameter the engine reads. A year missing any one of these
#: is not offered.
REQUIRED: tuple[str, ...] = (
    "standard_deduction", "additional_std_deduction_age_or_blind",
    "brackets_single", "brackets_mfj", "brackets_mfs", "brackets_hoh",
    "ltcg_0_pct_max", "ltcg_15_pct_max", "ltcg_rate_0", "ltcg_rate_15", "ltcg_rate_20",
    "ss_wage_base", "se_net_earnings_factor", "se_social_security_rate",
    "se_medicare_rate", "se_minimum_net_earnings",
    "addl_medicare_threshold", "addl_medicare_rate", "addl_medicare_employer_withholding_threshold",
    "niit_threshold", "niit_rate",
    "est_tax_safe_harbor_pct_current", "est_tax_safe_harbor_pct_prior",
    "est_tax_safe_harbor_pct_prior_high_agi", "est_tax_high_agi_threshold",
    "est_tax_high_agi_threshold_mfs", "est_tax_due_dates", "underpayment_penalty_floor",
    "salt_deduction_cap", "salt_phasedown_threshold", "salt_phasedown_rate", "salt_floor",
    "medical_agi_floor", "capital_loss_limit",
    "ctc_per_child", "ctc_refundable_max", "ctc_phaseout_threshold", "odc_per_dependent",
    "ctc_phaseout_rate_per_1000", "actc_earned_income_floor", "actc_earned_income_rate",
    "eitc_max_credit", "eitc_earned_income_amount", "eitc_threshold_phaseout",
    "eitc_completed_phaseout", "eitc_investment_income_limit",
    "tips_deduction_max", "overtime_deduction_max", "tips_overtime_phaseout_start",
    "tips_overtime_phaseout_per_1000", "car_loan_interest_max", "car_loan_phaseout_start",
    "car_loan_phaseout_per_1000", "senior_deduction_amount",
    "senior_deduction_phaseout_start", "senior_deduction_phaseout_rate",
    "qbi_threshold", "qbi_rate",
)

#: Parameters the law starts in a given year, required of that year and every
#: later one. The accessors read a missing one as zero -- correct for 2025,
#: which has no such deduction -- so without this a 2027 file that left one out
#: would be offered as complete and quietly switch an enacted deduction off.
#: Found by Codex on #451.
REQUIRED_FROM: dict[int, tuple[str, ...]] = {
    2026: ("charity_nonitemizer_max", "charity_itemized_floor_pct",
           "qbi_minimum_deduction", "qbi_minimum_qbi"),
}


def required_for(tax_year: int) -> tuple[str, ...]:
    """Every parameter a year must hold in force before it is offered."""
    later = [n for start, names in sorted(REQUIRED_FROM.items())
             if tax_year >= start for n in names]
    return REQUIRED + tuple(later)


class TaxYearNotOnFile(KeyError):
    """The estimator was asked for a year it does not hold complete tables for."""

    def __str__(self) -> str:  # KeyError quotes its message; this one is read by people
        return str(self.args[0]) if self.args else ""


_LIBRARY = CrosswalkLibrary()


def missing_parameters(crosswalk: Crosswalk) -> list[str]:
    """The REQUIRED parameters this year does not hold in force."""
    out = []
    for name in required_for(crosswalk.tax_year):
        p = crosswalk.params.get(name)
        if p is None or p.is_pending or p.status != "in_force":
            out.append(name)
    return out


def _us_years() -> list[int]:
    return sorted(y for (y, j) in _LIBRARY.available() if j == "US")


def _usable_us_years() -> list[int]:
    usable = []
    for y in _us_years():
        cw = _LIBRARY.resolve_or_none(y, "US")
        if cw is not None and not missing_parameters(cw):
            usable.append(y)
    return usable


def available_years() -> list[int]:
    """Federal tax years the estimator can run on, newest last."""
    return _usable_us_years()


def incomplete_years() -> dict[int, list[str]]:
    """Years that have a file but are not offered, with what each one lacks."""
    out: dict[int, list[str]] = {}
    for y in _us_years():
        cw = _LIBRARY.resolve_or_none(y, "US")
        if cw is not None:
            missing = missing_parameters(cw)
            if missing:
                out[y] = missing
    return out


def staleness(today: date | None = None) -> str | None:
    """A warning when the calendar has moved past the newest year on file.

    None when the current calendar year is on file. This is what the screen
    shows above the form, and what the suite turns red on.
    """
    today = today or date.today()
    usable = _usable_us_years()
    newest = usable[-1] if usable else None
    if newest is not None and newest >= today.year:
        return None
    have = f"the newest tax year on file is {newest}" if newest else "no tax year is on file"
    return (f"It is {today.year} and {have}. Estimates for {today.year} are blocked until "
            f"configs/crosswalk/federal/{today.year}.yaml is added from the IRS revenue "
            f"procedure for {today.year}.")


def load_tax_tables(year: int | None) -> tuple[TaxTables, list[str]]:
    """Resolve ``(TaxTables, notes)`` for ``year``; RAISE if it is not fully on file.

    ``None`` means the newest complete year, and the engine records that as an
    assumption. Any named year must be on file in full -- there is no fallback.
    """
    usable = _usable_us_years()
    if not usable:
        raise TaxYearNotOnFile("No complete federal tax table is on file.")
    used = year if year is not None else usable[-1]
    if used not in usable:
        missing = incomplete_years().get(used)
        if missing:
            detail = (f"configs/crosswalk/federal/{used}.yaml is missing or not in force for "
                      + ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else ""))
        else:
            detail = f"there is no configs/crosswalk/federal/{used}.yaml"
        raise TaxYearNotOnFile(
            f"No complete {used} tax table is on file, so no {used} estimate can be run "
            f"({detail}). Years on file: {', '.join(str(y) for y in usable)}. The estimator "
            f"will not substitute another year's figures.")
    crosswalk = _LIBRARY.resolve(used, "US")

    notes: list[str] = []
    # WHAT THE TABLE DOES NOT CARRY, SAID ON THE SCREEN -- read from the dated
    # table so the list cannot drift from the year it describes.
    missing = crosswalk.value("obbba_not_modeled")
    if missing:
        notes.append(f"Not modelled for {used}: " + "; ".join(str(m) for m in missing) + ".")
    return TaxTables(crosswalk), notes
