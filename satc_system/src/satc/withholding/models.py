"""Withholding-estimator domain models (ported from the standalone ``twe`` tool).

Inputs a user supplies (paystub figures, other income, adjustments, deductions,
credits, payments) and the results the engine produces (a full-year projection
plus a per-paycheck withholding recommendation). All money is :class:`Decimal`.

This module is pure: the tax constants live in SATC's dated crosswalk
(:mod:`satc.withholding.tax_data`), not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from decimal import Decimal
from typing import Any, Literal

FilingStatus = Literal[
    "single",
    "married_jointly",
    "married_separately",
    "head_of_household",
]

PayFrequency = Literal["weekly", "biweekly", "semimonthly", "monthly", "annual"]

ZERO = Decimal("0")

PERIODS_PER_YEAR: dict[str, int] = {
    "weekly": 52, "biweekly": 26, "semimonthly": 24, "monthly": 12, "annual": 1,
}


def to_decimal(value: Any) -> Decimal:
    """Coerce int/float/str/Decimal/None to a Decimal (None -> 0).

    Floats are routed through ``str`` first so ``0.1`` doesn't pick up
    binary-float noise.
    """
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _opt_decimal(value: Any) -> Decimal | None:
    return None if value is None else to_decimal(value)


@dataclass(slots=True)
class Paystub:
    """Per-paycheck figures lifted from a paystub.

    ``retirement_pretax_per_period`` and ``other_pretax_per_period`` are
    subtracted from gross to approximate federal taxable (Box 1) wages. Provide
    YTD figures for a mid-year estimate; otherwise they're inferred.
    """

    pay_frequency: PayFrequency
    taxable_wages_per_period: Decimal | None = None
    gross_pay_per_period: Decimal = ZERO
    federal_tax_withheld_per_period: Decimal = ZERO
    retirement_pretax_per_period: Decimal = ZERO
    other_pretax_per_period: Decimal = ZERO
    ytd_taxable_wages: Decimal | None = None
    ytd_federal_tax_withheld: Decimal | None = None
    pay_periods_remaining: int | None = None
    name: str = ""
    adjust_withholding: bool = False
    #: "you" or "spouse". Only matters when one person has two employers:
    #: each employer withholds Social Security up to the wage base on its own,
    #: and the excess comes back as a credit.
    owner: str = "you"

    @property
    def periods_per_year(self) -> int:
        return PERIODS_PER_YEAR[self.pay_frequency]

    @property
    def taxable_pay_per_period(self) -> Decimal:
        if self.taxable_wages_per_period is not None:
            return self.taxable_wages_per_period
        return (self.gross_pay_per_period
                - self.retirement_pretax_per_period
                - self.other_pretax_per_period)


@dataclass(slots=True)
class OtherIncome:
    """Income beyond the primary paycheck. Annual amounts."""

    interest: Decimal = ZERO
    ordinary_dividends: Decimal = ZERO
    qualified_dividends: Decimal = ZERO
    taxable_retirement_distributions: Decimal = ZERO
    taxable_social_security: Decimal = ZERO
    short_term_capital_gains: Decimal = ZERO
    long_term_capital_gains: Decimal = ZERO
    self_employment_net: Decimal = ZERO
    unemployment: Decimal = ZERO
    #: Net rents, royalties and passive K-1 income (Schedule E). Kept apart
    #: from other_taxable_income because it is investment income for the
    #: earned income credit (Pub. 596) and for the 3.8% tax (Form 8960 line 4a).
    rental_and_passive_income: Decimal = ZERO
    other_taxable_income: Decimal = ZERO
    spouse_taxable_wages: Decimal = ZERO
    spouse_federal_tax_withheld: Decimal = ZERO


@dataclass(slots=True)
class Household:
    """Facts about the people on the return. ``None`` means "not told".

    The estimator never treats None as a fact. It assumes a value, and every
    assumption it makes comes back in ``EstimateResult.assumptions`` with what
    would change if it is wrong.
    """

    taxpayer_65_or_older: bool | None = None
    spouse_65_or_older: bool | None = None
    #: Only asked for the earned income credit with no qualifying child, which
    #: needs somebody on the return aged 25 through 64 (IRC sec. 32(c)(1)(A)(ii)(II)).
    taxpayer_under_25: bool | None = None
    spouse_under_25: bool | None = None
    blind_count: int = 0
    children_under_17: int | None = None
    other_dependents: int | None = None
    #: Children who qualify for the earned income credit (under 19, or under
    #: 24 and a student). None = the children under 17 entered above.
    eitc_children: int | None = None


@dataclass(slots=True)
class Schedule1A:
    """The four below-the-line deductions new for 2025 (Schedule 1-A).

    Amounts are what QUALIFIES -- tips in a listed occupation, the overtime
    premium only (the "half" of time-and-a-half), interest on a loan for a new
    US-assembled personal vehicle. The estimator applies the caps and the
    income phase-outs; it cannot test eligibility.
    """

    qualified_tips: Decimal = ZERO
    qualified_overtime: Decimal = ZERO
    car_loan_interest: Decimal = ZERO


@dataclass(slots=True)
class Adjustments:
    """Above-the-line adjustments that reduce gross income to reach AGI."""

    traditional_ira_deduction: Decimal = ZERO
    hsa_deduction: Decimal = ZERO
    student_loan_interest: Decimal = ZERO
    other_adjustments: Decimal = ZERO


@dataclass(slots=True)
class Deductions:
    """Standard vs. itemized.

    Give the Schedule A parts and the estimator applies the SALT cap, the
    medical floor and (from 2026) the charity floor, then takes the larger of
    itemized and standard. ``itemized_total`` is a finished figure taken as
    given, for when the preparer has already done Schedule A. Nothing given at
    all = the standard deduction, recorded as an assumption.
    """

    itemized_total: Decimal | None = None
    extra_standard_deductions: int = 0
    medical_expenses: Decimal | None = None
    state_local_income_or_sales_tax: Decimal | None = None
    property_taxes: Decimal | None = None
    mortgage_interest: Decimal | None = None
    charitable_cash: Decimal | None = None
    charitable_noncash: Decimal | None = None
    other_itemized: Decimal | None = None

    def itemized_parts_given(self) -> bool:
        return any(getattr(self, n) is not None for n in _ITEMIZED_PARTS)


_ITEMIZED_PARTS = ("medical_expenses", "state_local_income_or_sales_tax", "property_taxes",
                   "mortgage_interest", "charitable_cash", "charitable_noncash", "other_itemized")


@dataclass(slots=True)
class Credits:
    """Typed credits. ``child_tax_credit`` None = compute it from the household's
    children and dependents (Schedule 8812); a figure typed here is used as is."""

    child_tax_credit: Decimal | None = None
    other_nonrefundable_credits: Decimal = ZERO
    refundable_credits: Decimal = ZERO


@dataclass(slots=True)
class OtherPayments:
    estimated_tax_payments: Decimal = ZERO
    other_withholding: Decimal = ZERO


@dataclass(slots=True)
class EstimatorInput:
    """The complete set of inputs for one withholding estimate."""

    filing_status: FilingStatus | None
    paystub: Paystub
    tax_year: int | None = None
    household: Household = field(default_factory=Household)
    schedule_1a: Schedule1A = field(default_factory=Schedule1A)
    additional_jobs: list[Paystub] = field(default_factory=list)
    other_income: OtherIncome = field(default_factory=OtherIncome)
    adjustments: Adjustments = field(default_factory=Adjustments)
    deductions: Deductions = field(default_factory=Deductions)
    credits: Credits = field(default_factory=Credits)
    other_payments: OtherPayments = field(default_factory=OtherPayments)
    target_refund: Decimal = ZERO
    prior_year_tax: Decimal | None = None
    prior_year_agi: Decimal | None = None

    @property
    def jobs(self) -> list[Paystub]:
        return [self.paystub, *self.additional_jobs]

    def adjusted_job(self) -> Paystub:
        for job in self.jobs:
            if job.adjust_withholding:
                return job
        return self.paystub

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EstimatorInput:
        """Build from a plain dict; unknown keys raise so typos surface."""
        data = dict(data)
        jobs_list = data.pop("jobs", None)
        raw_paystub = data.pop("paystub", None)
        raw_additional = data.pop("additional_jobs", None)

        if jobs_list is not None:
            if raw_paystub is not None or raw_additional is not None:
                raise ValueError("provide either 'jobs' or 'paystub'/'additional_jobs', not both")
            if not jobs_list:
                raise ValueError("'jobs' cannot be empty")
            raw_paystub = jobs_list[0]
            raw_additional = jobs_list[1:]

        paystub = _build(Paystub, raw_paystub or {}, _PAYSTUB_DECIMALS)
        additional_jobs = [_build(Paystub, j, _PAYSTUB_DECIMALS) for j in (raw_additional or [])]
        other_income = _build(OtherIncome, data.pop("other_income", {}), _ALL)
        adjustments = _build(Adjustments, data.pop("adjustments", {}), _ALL)
        deductions = _build_deductions(data.pop("deductions", {}))
        credits = _build_credits(data.pop("credits", {}))
        other_payments = _build(OtherPayments, data.pop("other_payments", {}), _ALL)
        household = _build_household(data.pop("household", {}))
        schedule_1a = _build(Schedule1A, data.pop("schedule_1a", {}), _ALL)

        # A missing filing status is ASSUMED (Single) and reported as such by
        # the engine. A wrong one is still refused: a typo is not "not told".
        filing_status = data.pop("filing_status", None) or None
        if filing_status is not None and filing_status not in _FILING_STATUSES:
            raise ValueError(f"unknown filing_status {filing_status!r}")

        instance = cls(
            filing_status=filing_status, paystub=paystub,
            tax_year=data.pop("tax_year", None), additional_jobs=additional_jobs,
            other_income=other_income, adjustments=adjustments, deductions=deductions,
            credits=credits, other_payments=other_payments,
            household=household, schedule_1a=schedule_1a,
            target_refund=to_decimal(data.pop("target_refund", 0)),
            prior_year_tax=_opt_decimal(data.pop("prior_year_tax", None)),
            prior_year_agi=_opt_decimal(data.pop("prior_year_agi", None)))
        if data:
            raise ValueError(f"unknown input keys: {sorted(data)}")
        return instance


_ALL = object()
_PAYSTUB_DECIMALS = {
    "gross_pay_per_period", "federal_tax_withheld_per_period",
    "retirement_pretax_per_period", "other_pretax_per_period",
    "ytd_taxable_wages", "ytd_federal_tax_withheld",
}


def _build(model: type, data: dict[str, Any], decimal_fields: Any) -> Any:
    valid = {f.name for f in fields(model)}
    unknown = set(data) - valid
    if unknown:
        raise ValueError(f"unknown keys for {model.__name__}: {sorted(unknown)}")
    kwargs: dict[str, Any] = {}
    for key, value in data.items():
        if key == "pay_periods_remaining":
            kwargs[key] = None if value is None else int(value)
        elif key in ("ytd_taxable_wages", "ytd_federal_tax_withheld", "taxable_wages_per_period"):
            kwargs[key] = _opt_decimal(value)
        elif key == "pay_frequency":
            kwargs[key] = value
        elif key == "adjust_withholding":
            kwargs[key] = bool(value)
        elif key in ("name", "owner"):
            kwargs[key] = str(value)
        elif decimal_fields is _ALL or key in decimal_fields:
            kwargs[key] = to_decimal(value)
        else:
            kwargs[key] = value
    return model(**kwargs)


_FILING_STATUSES = ("single", "married_jointly", "married_separately", "head_of_household")


def _check_keys(model: type, data: dict[str, Any]) -> None:
    unknown = set(data) - {f.name for f in fields(model)}
    if unknown:
        raise ValueError(f"unknown keys for {model.__name__}: {sorted(unknown)}")


def _build_deductions(data: dict[str, Any]) -> Deductions:
    _check_keys(Deductions, data)
    return Deductions(
        itemized_total=_opt_decimal(data.get("itemized_total")),
        extra_standard_deductions=int(data.get("extra_standard_deductions", 0)),
        **{n: _opt_decimal(data.get(n)) for n in _ITEMIZED_PARTS})


def _build_credits(data: dict[str, Any]) -> Credits:
    _check_keys(Credits, data)
    return Credits(
        child_tax_credit=_opt_decimal(data.get("child_tax_credit")),
        other_nonrefundable_credits=to_decimal(data.get("other_nonrefundable_credits")),
        refundable_credits=to_decimal(data.get("refundable_credits")))


def _opt_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("yes", "y", "true", "1"):
            return True
        if v in ("no", "n", "false", "0"):
            return False
        raise ValueError(f"expected yes/no, got {value!r}")
    return bool(value)


def _opt_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    n = int(float(value))
    if n < 0:
        raise ValueError(f"a count cannot be negative: {value!r}")
    return n


def _build_household(data: dict[str, Any]) -> Household:
    _check_keys(Household, data)
    return Household(
        taxpayer_65_or_older=_opt_bool(data.get("taxpayer_65_or_older")),
        spouse_65_or_older=_opt_bool(data.get("spouse_65_or_older")),
        taxpayer_under_25=_opt_bool(data.get("taxpayer_under_25")),
        spouse_under_25=_opt_bool(data.get("spouse_under_25")),
        blind_count=_opt_int(data.get("blind_count")) or 0,
        children_under_17=_opt_int(data.get("children_under_17")),
        other_dependents=_opt_int(data.get("other_dependents")),
        eitc_children=_opt_int(data.get("eitc_children")))


@dataclass(slots=True)
class TaxBreakdown:
    """Itemized projection of the full-year federal tax picture."""

    projected_taxable_wages: Decimal
    total_income: Decimal
    adjustments_total: Decimal
    adjusted_gross_income: Decimal
    deduction_used: Decimal
    deduction_kind: str
    taxable_income: Decimal
    ordinary_income_tax: Decimal
    capital_gains_tax: Decimal
    income_tax_before_credits: Decimal
    self_employment_tax: Decimal
    additional_medicare_tax: Decimal
    net_investment_income_tax: Decimal
    nonrefundable_credits: Decimal
    refundable_credits: Decimal
    total_tax_liability: Decimal
    marginal_rate: Decimal
    effective_rate: Decimal
    # Added 17 October 2026. Defaulted so a caller that builds a breakdown by
    # hand (the audit-tape tests do) still can.
    itemized_computed: Decimal | None = None
    standard_computed: Decimal = ZERO
    schedule_1a_deduction: Decimal = ZERO
    tips_deduction: Decimal = ZERO
    overtime_deduction: Decimal = ZERO
    car_loan_deduction: Decimal = ZERO
    senior_deduction: Decimal = ZERO
    qbi_deduction: Decimal = ZERO
    capital_gain_in_income: Decimal = ZERO
    capital_loss_carryover: Decimal = ZERO
    child_and_dependent_credit: Decimal = ZERO
    additional_child_tax_credit: Decimal = ZERO
    earned_income_credit: Decimal = ZERO


@dataclass(slots=True)
class JobProjection:
    name: str
    pay_frequency: str
    periods_per_year: int
    periods_remaining: int
    projected_taxable_wages: Decimal
    projected_withholding: Decimal
    periods_elapsed: int = 0
    ytd_withholding: Decimal = ZERO


@dataclass(slots=True)
class WithholdingRecommendation:
    """Per-paycheck guidance for the *adjusted job* (the one whose W-4 we tune)."""

    periods_per_year: int
    periods_remaining: int
    periods_elapsed: int
    ytd_withholding: Decimal
    projected_withholding_current_rate: Decimal
    other_payments_total: Decimal
    projected_total_payments: Decimal
    projected_balance: Decimal  # positive = refund, negative = balance due
    target_refund: Decimal
    required_remaining_withholding: Decimal
    recommended_withholding_per_period: Decimal
    additional_withholding_per_period: Decimal  # W-4 line 4c suggestion
    is_over_withholding: bool
    safe_harbor_target: Decimal | None = None
    safe_harbor_additional_per_period: Decimal | None = None
    adjusted_job_name: str = ""
    adjusted_job_pay_frequency: str = ""
    adjusted_job_withholding_per_period: Decimal = ZERO
    job_breakdown: list[JobProjection] = field(default_factory=list)
    # Added 17 October 2026: payments a paystub's "federal tax" line leaves out.
    additional_medicare_withheld: Decimal = ZERO
    excess_social_security_credit: Decimal = ZERO
    # The penalty test (IRC sec. 6654) and what to do about it.
    required_annual_payment: Decimal | None = None
    required_annual_payment_basis: str = ""
    penalty_risk: bool = False
    safe_harbor_shortfall: Decimal = ZERO
    estimated_payments_remaining: list[tuple[str, Decimal]] = field(default_factory=list)


@dataclass(slots=True)
class Assumption:
    """Something the estimator was not told and filled in, said out loud."""

    topic: str
    assumed: str
    if_wrong: str


@dataclass(slots=True)
class Check:
    """Something the estimator noticed. ``level`` is one of:

    * ``act``    -- money is on the line; somebody should do something
    * ``review`` -- the figure may be wrong; look before relying on it
    * ``info``   -- worth knowing, nothing to do
    """

    level: str
    title: str
    detail: str


@dataclass(slots=True)
class EstimateResult:
    tax_year_used: int
    filing_status: FilingStatus
    breakdown: TaxBreakdown
    recommendation: WithholdingRecommendation
    notes: list[str] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    headline: str = ""
