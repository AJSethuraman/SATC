"""Human-readable rendering of an :class:`~twe.models.EstimateResult`."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from twe.models import ZERO, EstimateResult, EstimatorInput

_STATUS_LABELS = {
    "single": "Single",
    "married_jointly": "Married filing jointly",
    "married_separately": "Married filing separately",
    "head_of_household": "Head of household",
}


_LABEL_WIDTH = 38
_VALUE_WIDTH = 14


def _usd(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _pct(value: Decimal) -> str:
    return f"{value * 100:.2f}%"


def _row(label: str, value: Decimal, *, subtract: bool = False) -> str:
    """A label/amount row with the amount right-aligned in a fixed column."""

    amount = _usd(value)
    if subtract:
        amount = f"- {amount}"
    return f"  {label:<{_LABEL_WIDTH}}{amount:>{_VALUE_WIDTH}}"


def render_text(result: EstimateResult) -> str:
    """Render a plain-text report suitable for a terminal."""

    b = result.breakdown
    r = result.recommendation
    status = _STATUS_LABELS.get(result.filing_status, result.filing_status)
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("  TAX WITHHOLDING ESTIMATE")
    lines.append("=" * 60)
    lines.append(f"  Tax year:       {result.tax_year_used}")
    lines.append(f"  Filing status:  {status}")
    lines.append("")

    lines.append("-- Projected annual income " + "-" * 33)
    lines.append(_row("Projected taxable wages", b.projected_taxable_wages))
    lines.append(_row("Total income", b.total_income))
    lines.append(_row("Adjustments to income", b.adjustments_total, subtract=True))
    lines.append(_row("Adjusted gross income (AGI)", b.adjusted_gross_income))
    lines.append(_row(f"Deduction ({b.deduction_kind})", b.deduction_used, subtract=True))
    lines.append(_row("Taxable income", b.taxable_income))
    lines.append("")

    lines.append("-- Projected tax liability " + "-" * 33)
    lines.append(_row("Ordinary income tax", b.ordinary_income_tax))
    if b.capital_gains_tax != 0:
        lines.append(_row("Capital gains / qual. dividend tax", b.capital_gains_tax))
    if b.self_employment_tax != 0:
        lines.append(_row("Self-employment tax", b.self_employment_tax))
    if b.additional_medicare_tax != 0:
        lines.append(_row("Additional Medicare tax", b.additional_medicare_tax))
    if b.net_investment_income_tax != 0:
        lines.append(_row("Net investment income tax", b.net_investment_income_tax))
    if b.nonrefundable_credits != 0:
        lines.append(_row("Nonrefundable credits", b.nonrefundable_credits, subtract=True))
    if b.refundable_credits != 0:
        lines.append(_row("Refundable credits", b.refundable_credits, subtract=True))
    lines.append(_row("TOTAL TAX LIABILITY", b.total_tax_liability))
    lines.append(f"  Marginal rate {_pct(b.marginal_rate)} | Effective rate {_pct(b.effective_rate)}")
    lines.append("")

    lines.append("-- Withholding & payments " + "-" * 34)
    multi_job = len(r.job_breakdown) > 1
    if multi_job:
        for job in r.job_breakdown:
            proj_rem = job.projected_withholding - job.ytd_withholding
            lines.append(
                f"  {job.name} ({job.pay_frequency}): "
                f"YTD {_usd(job.ytd_withholding)} ({job.periods_elapsed}/{job.periods_per_year}), "
                f"remaining {_usd(proj_rem)} ({job.periods_remaining} left)"
            )
    else:
        lines.append(f"  Pay periods remaining: {r.periods_remaining} of {r.periods_per_year}")
    lines.append(_row("Withheld year-to-date (all jobs)", r.ytd_withholding))
    lines.append(_row("Projected withholding (current rate)", r.projected_withholding_current_rate))
    if r.other_payments_total != 0:
        lines.append(_row("Other payments / spouse withholding", r.other_payments_total))
    lines.append(_row("Projected total payments", r.projected_total_payments))
    lines.append("")

    lines.append("-- Bottom line " + "-" * 45)
    if r.projected_balance >= 0:
        lines.append(f"  If nothing changes:  REFUND of {_usd(r.projected_balance)}")
    else:
        lines.append(f"  If nothing changes:  BALANCE DUE of {_usd(-r.projected_balance)}")

    if r.target_refund != 0:
        lines.append(f"  Target refund:       {_usd(r.target_refund)}")

    lines.append("")
    if r.is_over_withholding:
        reduction = r.adjusted_job_withholding_per_period - r.recommended_withholding_per_period
        job_label = f' ({r.adjusted_job_name})' if multi_job else ''
        lines.append("  You are on track to OVER-WITHHOLD for your target.")
        lines.append(_row(f"Current withholding / paycheck{job_label}", r.adjusted_job_withholding_per_period))
        lines.append(_row(f"Recommended withholding / paycheck{job_label}", r.recommended_withholding_per_period))
        lines.append(_row(f"Reduction / paycheck{job_label}", reduction))
        lines.append(
            f"  W-4 Step 3 entry ~ {_usd(reduction * r.periods_per_year)} "
            f"({_usd(reduction)} x {r.periods_per_year}/yr)"
        )
    else:
        on_job = f' on "{r.adjusted_job_name}"' if multi_job else ""
        lines.append("  RECOMMENDATION to hit your target:")
        lines.append(f"    Withhold about {_usd(r.recommended_withholding_per_period)} per paycheck{on_job}")
        lines.append(f"    That is {_usd(r.additional_withholding_per_period)} MORE than your current")
        lines.append(f"    paycheck withholding -- enter this as extra withholding on")
        lines.append(f"    that job's Form W-4, Step 4(c).")

    if r.safe_harbor_target is not None:
        lines.append("")
        lines.append("-- Safe harbor (avoid underpayment penalty) " + "-" * 16)
        lines.append(f"  Minimum payments to be penalty-safe:  {_usd(r.safe_harbor_target)}")
        if r.safe_harbor_additional_per_period is not None:
            lines.append(
                f"  Extra per paycheck for safe harbor:   {_usd(r.safe_harbor_additional_per_period)}"
            )

    if result.notes:
        lines.append("")
        lines.append("-- Notes " + "-" * 51)
        for note in result.notes:
            lines.append(f"  * {note}")

    lines.append("")
    lines.append("This is an estimate for planning only, not tax advice.")
    return "\n".join(lines)


def result_to_dict(result: EstimateResult) -> dict[str, Any]:
    """Convert a result to a JSON-serializable dict (Decimals -> str)."""

    return _decimalize(asdict(result))


def _decimalize(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _decimalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimalize(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Audit tape
# ---------------------------------------------------------------------------

_TAPE_W = 64
_TAPE_V = 14  # right-aligned value column width

_FREQ_LABELS: dict[str, str] = {
    "weekly": "Weekly (52/yr)",
    "biweekly": "Bi-weekly (26/yr)",
    "semimonthly": "Semi-monthly (24/yr)",
    "monthly": "Monthly (12/yr)",
    "annual": "Annual (1/yr)",
}


def _tsep(char: str = "-") -> str:
    return char * _TAPE_W


def _trow(label: str, value: Decimal, *, indent: int = 2, subtract: bool = False) -> str:
    amt = _usd(value)
    if subtract:
        amt = "- " + amt
    pad = " " * indent
    label_w = _TAPE_W - _TAPE_V - indent
    return f"{pad}{label:<{label_w}}{amt:>{_TAPE_V}}"


def render_tape(
    inp: EstimatorInput,
    result: EstimateResult,
    *,
    generated_at: str | None = None,
) -> str:
    """Render a full audit tape: all inputs, every calculation step, recommendation."""

    from datetime import datetime as _dt

    if generated_at is None:
        generated_at = _dt.now().strftime("%B %d, %Y  %I:%M %p")

    b = result.breakdown
    r = result.recommendation
    status = _STATUS_LABELS.get(result.filing_status, result.filing_status)

    lines: list[str] = []

    # ------------------------------------------------------------------ header
    lines += [
        _tsep("="),
        "  SETHURAMAN ACCOUNTING  ·  TAX  ·  CONSULTING",
        "  FEDERAL TAX WITHHOLDING ESTIMATE  —  AUDIT TAPE",
        _tsep("="),
        f"  Tax year:      {result.tax_year_used}",
        f"  Filing status: {status}",
        f"  Generated:     {generated_at}",
        _tsep("="),
    ]

    # ------------------------------------------------------------------ inputs
    lines += ["", _tsep(), "  SCENARIO INPUTS", _tsep(), ""]

    all_jobs = inp.jobs
    for i, job in enumerate(all_jobs):
        name = job.name or ("Paystub" if len(all_jobs) == 1 else f"Job {i + 1}")
        lines.append(f"  {name}")
        lines.append(f"    Frequency:  {_FREQ_LABELS.get(job.pay_frequency, job.pay_frequency)}")
        if job.taxable_wages_per_period is not None:
            lines.append(_trow("Taxable wages / period", job.taxable_wages_per_period, indent=4))
        if job.gross_pay_per_period != ZERO:
            lines.append(_trow("Gross pay / period", job.gross_pay_per_period, indent=4))
        lines.append(_trow("Federal withheld / period", job.federal_tax_withheld_per_period, indent=4))
        if job.retirement_pretax_per_period != ZERO:
            lines.append(_trow("Retirement pre-tax / period", job.retirement_pretax_per_period, indent=4))
        if job.other_pretax_per_period != ZERO:
            lines.append(_trow("Other pre-tax / period", job.other_pretax_per_period, indent=4))
        if job.ytd_taxable_wages is not None:
            lines.append(_trow("YTD taxable wages", job.ytd_taxable_wages, indent=4))
        if job.ytd_federal_tax_withheld is not None:
            lines.append(_trow("YTD federal withheld", job.ytd_federal_tax_withheld, indent=4))
        if job.pay_periods_remaining is not None:
            lines.append(f"    Periods remaining:  {job.pay_periods_remaining} of {job.periods_per_year}")
        else:
            lines.append(f"    Periods / year:     {job.periods_per_year}")
        lines.append("")

    oi = inp.other_income
    oi_items = [
        ("Interest", oi.interest),
        ("Ordinary dividends", oi.ordinary_dividends),
        ("Qualified dividends", oi.qualified_dividends),
        ("IRA / retirement distributions", oi.taxable_retirement_distributions),
        ("Taxable Social Security", oi.taxable_social_security),
        ("Long-term capital gains", oi.long_term_capital_gains),
        ("Short-term capital gains", oi.short_term_capital_gains),
        ("Net self-employment income", oi.self_employment_net),
        ("Unemployment compensation", oi.unemployment),
        ("Other taxable income", oi.other_taxable_income),
        ("Spouse taxable wages", oi.spouse_taxable_wages),
        ("Spouse federal withheld", oi.spouse_federal_tax_withheld),
    ]
    nonzero_oi = [(lbl, v) for lbl, v in oi_items if v != ZERO]
    if nonzero_oi:
        lines.append("  Other income:")
        for lbl, v in nonzero_oi:
            lines.append(_trow(lbl, v, indent=4))
        lines.append("")

    adj = inp.adjustments
    adj_items = [
        ("Traditional IRA deduction", adj.traditional_ira_deduction),
        ("HSA deduction", adj.hsa_deduction),
        ("Student loan interest", adj.student_loan_interest),
        ("Other adjustments", adj.other_adjustments),
    ]
    nonzero_adj = [(lbl, v) for lbl, v in adj_items if v != ZERO]
    if nonzero_adj:
        lines.append("  Adjustments (above the line):")
        for lbl, v in nonzero_adj:
            lines.append(_trow(lbl, v, indent=4))
        lines.append("")

    ded = inp.deductions
    if ded.itemized_total is not None:
        lines.append(_trow("Deductions  (itemized)", ded.itemized_total))
    else:
        lines.append("  Deductions:  Standard deduction")
    if ded.extra_standard_deductions:
        lines.append(f"    Extra standard deductions:  {ded.extra_standard_deductions}")
    lines.append("")

    cr = inp.credits
    cr_items = [
        ("Child tax credit", cr.child_tax_credit),
        ("Other nonrefundable credits", cr.other_nonrefundable_credits),
        ("Refundable credits", cr.refundable_credits),
    ]
    nonzero_cr = [(lbl, v) for lbl, v in cr_items if v != ZERO]
    if nonzero_cr:
        lines.append("  Credits:")
        for lbl, v in nonzero_cr:
            lines.append(_trow(lbl, v, indent=4))
        lines.append("")

    op = inp.other_payments
    op_items = [
        ("Estimated tax payments", op.estimated_tax_payments),
        ("Other withholding", op.other_withholding),
    ]
    nonzero_op = [(lbl, v) for lbl, v in op_items if v != ZERO]
    if nonzero_op:
        lines.append("  Other payments already made:")
        for lbl, v in nonzero_op:
            lines.append(_trow(lbl, v, indent=4))
        lines.append("")

    extras: list[str] = []
    if inp.target_refund != ZERO:
        extras.append(_trow("Target refund", inp.target_refund))
    if inp.prior_year_tax is not None:
        extras.append(_trow("Prior-year total tax", inp.prior_year_tax))
    if inp.prior_year_agi is not None:
        extras.append(_trow("Prior-year AGI", inp.prior_year_agi))
    if extras:
        lines += extras + [""]

    # ------------------------------------------------------------------ income
    lines += ["", _tsep(), "  INCOME COMPUTATION", _tsep(), ""]

    lines.append(_trow("Projected taxable wages", b.projected_taxable_wages))

    income_addends = [
        ("+ Interest", oi.interest),
        ("+ Ordinary dividends", oi.ordinary_dividends),
        ("+ IRA / retirement distributions", oi.taxable_retirement_distributions),
        ("+ Taxable Social Security", oi.taxable_social_security),
        ("+ Long-term capital gains", oi.long_term_capital_gains),
        ("+ Short-term capital gains", oi.short_term_capital_gains),
        ("+ Net self-employment income", oi.self_employment_net),
        ("+ Unemployment compensation", oi.unemployment),
        ("+ Other taxable income", oi.other_taxable_income),
        ("+ Spouse taxable wages", oi.spouse_taxable_wages),
    ]
    for lbl, v in income_addends:
        if v != ZERO:
            lines.append(_trow(lbl, v))

    lines += ["  " + "-" * (_TAPE_W - 2), _trow("TOTAL INCOME", b.total_income), ""]

    if b.adjustments_total != ZERO:
        for lbl, v in [
            ("- Traditional IRA deduction", adj.traditional_ira_deduction),
            ("- HSA deduction", adj.hsa_deduction),
            ("- Student loan interest", adj.student_loan_interest),
            ("- Other adjustments", adj.other_adjustments),
        ]:
            if v != ZERO:
                lines.append(_trow(lbl, v, subtract=True))
        lines += ["  " + "-" * (_TAPE_W - 2), ""]

    lines += [
        _trow("ADJUSTED GROSS INCOME (AGI)", b.adjusted_gross_income),
        _trow(f"- Deduction  ({b.deduction_kind})", b.deduction_used, subtract=True),
        "  " + "-" * (_TAPE_W - 2),
        _trow("TAXABLE INCOME", b.taxable_income),
    ]

    # ------------------------------------------------------------------- tax
    lines += ["", _tsep(), "  TAX COMPUTATION", _tsep(), ""]

    lines.append(_trow("Ordinary income tax", b.ordinary_income_tax))
    if b.capital_gains_tax != ZERO:
        lines.append(_trow("+ Cap. gains / qual. dividend tax", b.capital_gains_tax))
    if b.self_employment_tax != ZERO:
        lines.append(_trow("+ Self-employment tax", b.self_employment_tax))
    if b.additional_medicare_tax != ZERO:
        lines.append(_trow("+ Additional Medicare Tax (0.9%)", b.additional_medicare_tax))
    if b.net_investment_income_tax != ZERO:
        lines.append(_trow("+ Net Investment Income Tax (3.8%)", b.net_investment_income_tax))
    lines += ["  " + "-" * (_TAPE_W - 2), _trow("Income tax before credits", b.income_tax_before_credits), ""]

    if b.nonrefundable_credits != ZERO:
        lines.append(_trow("- Nonrefundable credits", b.nonrefundable_credits, subtract=True))
    if b.refundable_credits != ZERO:
        lines.append(_trow("- Refundable credits", b.refundable_credits, subtract=True))
    if b.nonrefundable_credits != ZERO or b.refundable_credits != ZERO:
        lines.append("  " + "-" * (_TAPE_W - 2))

    lines += [
        _trow("TOTAL TAX LIABILITY", b.total_tax_liability),
        "",
        f"  Marginal rate: {_pct(b.marginal_rate)}   |   Effective rate: {_pct(b.effective_rate)}",
    ]

    # ----------------------------------------------------------- withholding
    lines += ["", _tsep(), "  WITHHOLDING ANALYSIS", _tsep(), ""]

    multi_job = len(r.job_breakdown) > 1
    if multi_job:
        for job in r.job_breakdown:
            lines.append(f"  {job.name}  ({job.pay_frequency})")
            lines.append(_trow(f"  YTD withheld  ({job.periods_elapsed}/{job.periods_per_year} periods)", job.ytd_withholding))
            job_proj_remaining = job.projected_withholding - job.ytd_withholding
            if job_proj_remaining > ZERO:
                lines.append(_trow(f"  + Remaining  ({job.periods_remaining} periods, current rate)", job_proj_remaining))
        lines.append("")
        lines.append(_trow("YTD withheld — all jobs", r.ytd_withholding))
        proj_remaining = r.projected_withholding_current_rate - r.ytd_withholding
        if proj_remaining > ZERO:
            lines.append(_trow("+ Remaining — all jobs (current rate)", proj_remaining))
    else:
        proj_remaining = r.projected_withholding_current_rate - r.ytd_withholding
        lines.append(_trow(f"YTD withheld ({r.periods_elapsed}/{r.periods_per_year} periods)", r.ytd_withholding))
        if proj_remaining > ZERO:
            lines.append(_trow(f"+ Remaining ({r.periods_remaining} periods, current rate)", proj_remaining))
    if r.other_payments_total != ZERO:
        lines.append(_trow("+ Other payments / spouse withheld", r.other_payments_total))
    lines += [
        "  " + "-" * (_TAPE_W - 2),
        _trow("PROJECTED TOTAL PAYMENTS", r.projected_total_payments),
        "",
        _trow("Projected tax liability", b.total_tax_liability),
        _trow("- Projected total payments", r.projected_total_payments, subtract=True),
        "  " + "-" * (_TAPE_W - 2),
    ]
    if r.projected_balance >= ZERO:
        lines.append(_trow("PROJECTED REFUND", r.projected_balance))
    else:
        lines.append(_trow("PROJECTED BALANCE DUE", -r.projected_balance))

    # ------------------------------------------------------- recommendation
    lines += ["", _tsep(), "  RECOMMENDATION", _tsep(), ""]

    if inp.target_refund != ZERO:
        lines += [_trow("Target refund", inp.target_refund), ""]

    if r.is_over_withholding:
        reduction = r.adjusted_job_withholding_per_period - r.recommended_withholding_per_period
        step3_approx = reduction * r.periods_per_year
        job_label = f"  ({r.adjusted_job_name})" if multi_job else ""
        job_w4_owner = f"{r.adjusted_job_name}'s" if multi_job else "your"
        lines += [
            "  You are on track to OVER-WITHHOLD for your target.",
            "",
            _trow(f"Current withholding / paycheck{job_label}", r.adjusted_job_withholding_per_period),
            _trow(f"Recommended withholding / paycheck{job_label}", r.recommended_withholding_per_period),
            _trow(f"REDUCTION / PAYCHECK{job_label}", reduction),
            "",
            "  Form W-4 Step 3 (approx. annualized reduction):",
            f"    Enter ~{_usd(step3_approx)} in Step 3 of {job_w4_owner} W-4",
            f"    ({_usd(reduction)} × {r.periods_per_year} periods/yr = {_usd(step3_approx)})",
        ]
    else:
        on_job = f'  (for "{r.adjusted_job_name}" W-4)' if multi_job else ""
        lines += [
            "  Action recommended — currently UNDER-WITHHOLDING.",
            "",
            _trow("Recommended withholding / paycheck", r.recommended_withholding_per_period),
            _trow("Current withholding / paycheck", r.adjusted_job_withholding_per_period),
            _trow("EXTRA NEEDED / PAYCHECK  (W-4 Step 4c)", r.additional_withholding_per_period),
            "",
            f"  Enter {_usd(r.additional_withholding_per_period)} as additional withholding{on_job}",
            f"  on Form W-4, Step 4(c).  "
            f"({r.periods_remaining} pay period{'s' if r.periods_remaining != 1 else ''} remaining.)",
        ]

    # --------------------------------------------------------- safe harbor
    if r.safe_harbor_target is not None:
        lines += ["", _tsep(), "  SAFE HARBOR  (underpayment penalty threshold)", _tsep(), ""]
        met = r.projected_total_payments >= r.safe_harbor_target
        lines += [
            _trow("Minimum payments for safe harbor", r.safe_harbor_target),
            _trow("Projected total payments", r.projected_total_payments),
            "",
            f"  Status: {'SAFE HARBOR MET' if met else 'SAFE HARBOR NOT MET'}",
        ]
        if r.safe_harbor_additional_per_period is not None and r.safe_harbor_additional_per_period > ZERO:
            lines.append(_trow("Extra / paycheck for safe harbor", r.safe_harbor_additional_per_period))

    # ------------------------------------------------------------- notes
    if result.notes:
        lines += ["", _tsep(), "  NOTES", _tsep(), ""]
        for note in result.notes:
            lines.append(f"  * {note}")

    # ------------------------------------------------------------- footer
    lines += [
        "",
        _tsep("="),
        "  For planning purposes only — not tax advice.",
        "  Federal income tax only. Always verify with a qualified tax professional.",
        "  Sethuraman Accounting · Tax · Consulting",
        _tsep("="),
    ]

    return "\n".join(lines)
