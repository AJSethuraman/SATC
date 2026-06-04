"""Human-readable rendering of an :class:`~twe.models.EstimateResult`."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from twe.models import EstimateResult

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
            lines.append(
                f"  {job.name} ({job.pay_frequency}, {job.periods_remaining} left): "
                f"wages {_usd(job.projected_taxable_wages)}, withholding {_usd(job.projected_withholding)}"
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
        lines.append("  You are on track to OVER-WITHHOLD for your target.")
        lines.append(f"  You could reduce withholding to about {_usd(r.recommended_withholding_per_period)} / paycheck")
        lines.append("  (e.g. by claiming deductions/dependents on Form W-4 Step 3 or 4b).")
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
