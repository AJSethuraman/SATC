"""Domain models for the tax withholding estimator.

These dataclasses describe the *inputs* a user supplies (paystub figures, extra
income, adjustments, deductions, credits, and other payments) and the *results*
the engine produces (a fully itemized projection plus a per-paycheck
withholding recommendation).

All monetary values use :class:`decimal.Decimal` so currency math stays exact.
Helper constructors accept plain ``int``/``float``/``str`` and coerce them.
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

PayFrequency = Literal[
    "weekly",
    "biweekly",
    "semimonthly",
    "monthly",
    "annual",
]

ZERO = Decimal("0")

PERIODS_PER_YEAR: dict[str, int] = {
    "weekly": 52,
    "biweekly": 26,
    "semimonthly": 24,
    "monthly": 12,
    "annual": 1,
}


def to_decimal(value: Any) -> Decimal:
    """Coerce ``int``/``float``/``str``/``Decimal``/``None`` to a Decimal.

    ``None`` becomes :data:`ZERO`. Floats are routed through ``str`` first so a
    value like ``0.1`` does not pick up binary-float noise.
    """

    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


def _opt_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return to_decimal(value)


@dataclass(slots=True)
class Paystub:
    """Per-paycheck figures lifted straight from a paystub.

    ``retirement_pretax_per_period`` and ``other_pretax_per_period`` are
    subtracted from gross pay to approximate federal taxable wages (Box 1).
    Provide ``ytd_taxable_wages`` / ``ytd_federal_tax_withheld`` for a
    mid-year estimate; when omitted they are inferred from elapsed periods.
    """

    pay_frequency: PayFrequency
    gross_pay_per_period: Decimal = ZERO
    federal_tax_withheld_per_period: Decimal = ZERO
    retirement_pretax_per_period: Decimal = ZERO
    other_pretax_per_period: Decimal = ZERO
    ytd_taxable_wages: Decimal | None = None
    ytd_federal_tax_withheld: Decimal | None = None
    pay_periods_remaining: int | None = None
    name: str = ""
    adjust_withholding: bool = False  # apply the per-paycheck recommendation to this job

    @property
    def periods_per_year(self) -> int:
        return PERIODS_PER_YEAR[self.pay_frequency]

    @property
    def taxable_pay_per_period(self) -> Decimal:
        return (
            self.gross_pay_per_period
            - self.retirement_pretax_per_period
            - self.other_pretax_per_period
        )


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
    other_taxable_income: Decimal = ZERO
    spouse_taxable_wages: Decimal = ZERO
    spouse_federal_tax_withheld: Decimal = ZERO


@dataclass(slots=True)
class Adjustments:
    """Above-the-line adjustments that reduce gross income to reach AGI."""

    traditional_ira_deduction: Decimal = ZERO
    hsa_deduction: Decimal = ZERO
    student_loan_interest: Decimal = ZERO
    other_adjustments: Decimal = ZERO


@dataclass(slots=True)
class Deductions:
    """Standard vs. itemized deductions.

    When ``itemized_total`` is ``None`` the standard deduction for the filing
    status is used. ``extra_standard_deductions`` counts taxpayers who are 65+
    or blind (each box checked adds one additional standard deduction).
    """

    itemized_total: Decimal | None = None
    extra_standard_deductions: int = 0


@dataclass(slots=True)
class Credits:
    """Tax credits.

    ``child_tax_credit`` and ``other_nonrefundable_credits`` reduce tax but not
    below zero; ``refundable_credits`` can drive the result into a refund.
    """

    child_tax_credit: Decimal = ZERO
    other_nonrefundable_credits: Decimal = ZERO
    refundable_credits: Decimal = ZERO


@dataclass(slots=True)
class OtherPayments:
    """Tax already paid or withheld outside the primary paycheck (annual)."""

    estimated_tax_payments: Decimal = ZERO
    other_withholding: Decimal = ZERO


@dataclass(slots=True)
class EstimatorInput:
    """The complete set of inputs for one withholding estimate."""

    filing_status: FilingStatus
    paystub: Paystub
    tax_year: int | None = None
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
        """All jobs: the primary paystub followed by any additional jobs."""

        return [self.paystub, *self.additional_jobs]

    def adjusted_job(self) -> Paystub:
        """The job whose W-4 the per-paycheck recommendation targets.

        The first job flagged ``adjust_withholding`` wins; otherwise the
        primary paystub.
        """

        for job in self.jobs:
            if job.adjust_withholding:
                return job
        return self.paystub

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EstimatorInput:
        """Build an :class:`EstimatorInput` from a plain dict (e.g. parsed JSON).

        Accepts either a single ``paystub`` plus optional ``additional_jobs``
        list, or a ``jobs`` list (first entry becomes the primary paystub).
        Unknown keys raise ``ValueError`` so typos surface instead of being
        silently ignored. Monetary fields are coerced to ``Decimal``.
        """

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
        credits = _build(Credits, data.pop("credits", {}), _ALL)
        other_payments = _build(OtherPayments, data.pop("other_payments", {}), _ALL)

        filing_status = data.pop("filing_status", None)
        if filing_status is None:
            raise ValueError("filing_status is required")

        instance = cls(
            filing_status=filing_status,
            paystub=paystub,
            tax_year=data.pop("tax_year", None),
            additional_jobs=additional_jobs,
            other_income=other_income,
            adjustments=adjustments,
            deductions=deductions,
            credits=credits,
            other_payments=other_payments,
            target_refund=to_decimal(data.pop("target_refund", 0)),
            prior_year_tax=_opt_decimal(data.pop("prior_year_tax", None)),
            prior_year_agi=_opt_decimal(data.pop("prior_year_agi", None)),
        )
        if data:
            raise ValueError(f"unknown input keys: {sorted(data)}")
        return instance


# Sentinels describing which fields of a nested model are monetary.
_ALL = object()
_PAYSTUB_DECIMALS = {
    "gross_pay_per_period",
    "federal_tax_withheld_per_period",
    "retirement_pretax_per_period",
    "other_pretax_per_period",
    "ytd_taxable_wages",
    "ytd_federal_tax_withheld",
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
        elif key in ("ytd_taxable_wages", "ytd_federal_tax_withheld"):
            kwargs[key] = _opt_decimal(value)
        elif key == "pay_frequency":
            kwargs[key] = value
        elif key == "adjust_withholding":
            kwargs[key] = bool(value)
        elif key == "name":
            kwargs[key] = str(value)
        elif decimal_fields is _ALL or key in decimal_fields:
            kwargs[key] = to_decimal(value)
        else:
            kwargs[key] = value
    return model(**kwargs)


def _build_deductions(data: dict[str, Any]) -> Deductions:
    valid = {f.name for f in fields(Deductions)}
    unknown = set(data) - valid
    if unknown:
        raise ValueError(f"unknown keys for Deductions: {sorted(unknown)}")
    return Deductions(
        itemized_total=_opt_decimal(data.get("itemized_total")),
        extra_standard_deductions=int(data.get("extra_standard_deductions", 0)),
    )


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


@dataclass(slots=True)
class JobProjection:
    """Full-year projection for one job, for transparency in multi-job cases."""

    name: str
    pay_frequency: str
    periods_per_year: int
    periods_remaining: int
    projected_taxable_wages: Decimal
    projected_withholding: Decimal


@dataclass(slots=True)
class WithholdingRecommendation:
    """Per-paycheck guidance derived from the projection.

    The per-period figures (``periods_*`` and ``*_per_period``) refer to the
    *adjusted job* — the one whose W-4 the recommendation targets.
    """

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
    job_breakdown: list[JobProjection] = field(default_factory=list)


@dataclass(slots=True)
class EstimateResult:
    tax_year_used: int
    filing_status: FilingStatus
    breakdown: TaxBreakdown
    recommendation: WithholdingRecommendation
    notes: list[str] = field(default_factory=list)
