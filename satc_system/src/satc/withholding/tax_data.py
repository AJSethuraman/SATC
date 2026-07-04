"""Tax constants for the withholding estimator — read from SATC's crosswalk.

The standalone ``twe`` tool shipped its own ``data/<year>.json``. Here we instead
read SATC's dated, cited tax-law crosswalk (``configs/crosswalk/federal/*.yaml``)
so the estimator inherits citations, provenance, multi-year support, and the
"never guess a value" discipline. :class:`TaxTables` is the typed view the engine
consumes; :func:`load_tax_tables` resolves the year and falls back to the latest
fully-published federal table when a year (e.g. the 2026 sunset fixture) is not
fully in force.
"""

from __future__ import annotations

from dataclasses import dataclass
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
# Year resolution (with fallback to the latest fully-published federal table)
# ---------------------------------------------------------------------------

_LIBRARY = CrosswalkLibrary()


def _is_usable(crosswalk: Crosswalk) -> bool:
    """A federal table the estimator can fully run on (brackets + std deduction in force)."""
    return crosswalk.value("standard_deduction") is not None and \
        crosswalk.value("brackets_single") is not None


def _usable_us_years() -> list[int]:
    years = [y for (y, j) in _LIBRARY.available() if j == "US"]
    usable = []
    for y in years:
        cw = _LIBRARY.resolve_or_none(y, "US")
        if cw is not None and _is_usable(cw):
            usable.append(y)
    return sorted(usable)


def available_years() -> list[int]:
    """Federal tax years the estimator can run on, newest last."""
    return _usable_us_years()


def load_tax_tables(year: int | None) -> tuple[TaxTables, list[str]]:
    """Resolve ``(TaxTables, notes)`` for ``year``, falling back when needed."""
    usable = _usable_us_years()
    if not usable:
        raise KeyError("No fully-published federal crosswalk year is available.")
    latest = usable[-1]

    requested = year if year is not None else latest
    notes: list[str] = []
    if requested in usable:
        used = requested
    else:
        used = latest
        notes.append(
            f"Federal tax tables for {requested} are not fully published in the crosswalk; "
            f"using {used} tables for this estimate.")
    return TaxTables(_LIBRARY.resolve(used, "US")), notes
