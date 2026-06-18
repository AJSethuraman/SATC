"""The withholding estimation engine (ported from the standalone ``twe`` tool).

The flow mirrors a Form 1040 projection:

1. Project full-year taxable wages and other income.
2. Subtract above-the-line adjustments to reach AGI.
3. Apply the larger of the standard or itemized deduction.
4. Tax ordinary income through the brackets and stack qualified dividends /
   long-term gains through the preferential 0/15/20% capital-gains rates.
5. Add self-employment tax, the Additional Medicare Tax, and the Net Investment
   Income Tax; then subtract credits.
6. Compare projected payments against the liability and translate the gap into a
   per-paycheck withholding recommendation (Form W-4 line 4c style).

Tax constants come from SATC's dated crosswalk via
:mod:`satc.withholding.tax_data`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from satc.withholding.models import (
    EstimateResult,
    EstimatorInput,
    JobProjection,
    Paystub,
    TaxBreakdown,
    WithholdingRecommendation,
    ZERO,
)
from satc.withholding.tax_data import TaxTables, load_tax_tables

CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def _nonneg(value: Decimal) -> Decimal:
    return value if value > ZERO else ZERO


def estimate(inp: EstimatorInput) -> EstimateResult:
    """Run a full withholding estimate for the given input."""
    tables, notes = load_tax_tables(inp.tax_year)
    notes = list(notes)
    breakdown, extra_notes = _build_breakdown(inp, tables)
    notes.extend(extra_notes)
    recommendation = _build_recommendation(inp, tables, breakdown)
    return EstimateResult(
        tax_year_used=tables.tax_year, filing_status=inp.filing_status,
        breakdown=breakdown, recommendation=recommendation, notes=notes)


# ---------------------------------------------------------------------------
# Income / liability projection
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class _JobProjection:
    job: Paystub
    projected_wages: Decimal
    ytd_withholding: Decimal
    projected_withholding: Decimal
    periods_elapsed: int
    periods_remaining: int


def _project_job(job: Paystub) -> _JobProjection:
    periods_per_year = job.periods_per_year
    remaining = job.pay_periods_remaining
    if remaining is None:
        remaining = periods_per_year
    remaining = max(0, min(remaining, periods_per_year))
    elapsed = periods_per_year - remaining

    per_period = job.taxable_pay_per_period
    if per_period == ZERO and job.ytd_taxable_wages is not None and elapsed > 0:
        per_period = job.ytd_taxable_wages / elapsed

    if job.ytd_taxable_wages is not None:
        ytd_wages = job.ytd_taxable_wages
    else:
        ytd_wages = per_period * elapsed
    projected_wages = ytd_wages + per_period * remaining

    per_period_wh = job.federal_tax_withheld_per_period
    if job.ytd_federal_tax_withheld is not None:
        ytd_wh = job.ytd_federal_tax_withheld
    else:
        ytd_wh = per_period_wh * elapsed
    projected_wh = ytd_wh + per_period_wh * remaining

    return _JobProjection(
        job=job, projected_wages=projected_wages, ytd_withholding=ytd_wh,
        projected_withholding=projected_wh, periods_elapsed=elapsed,
        periods_remaining=remaining)


def _total_projected_wages(inp: EstimatorInput) -> Decimal:
    return sum((_project_job(job).projected_wages for job in inp.jobs), ZERO)


def _build_breakdown(inp: EstimatorInput, tables: TaxTables) -> tuple[TaxBreakdown, list[str]]:
    notes: list[str] = []
    oi = inp.other_income
    status = inp.filing_status

    projected_wages = _total_projected_wages(inp)
    se_tax, half_se = _self_employment_tax(oi.self_employment_net, projected_wages, tables)

    total_income = (
        projected_wages + oi.interest + oi.ordinary_dividends
        + oi.taxable_retirement_distributions + oi.taxable_social_security
        + oi.short_term_capital_gains + oi.long_term_capital_gains
        + oi.self_employment_net + oi.unemployment + oi.other_taxable_income
        + oi.spouse_taxable_wages)

    adj = inp.adjustments
    adjustments_total = (adj.traditional_ira_deduction + adj.hsa_deduction
                         + adj.student_loan_interest + adj.other_adjustments + half_se)
    agi = _nonneg(total_income - adjustments_total)

    standard = tables.standard_deduction(status)
    standard += tables.extra_standard_deduction(status) * inp.deductions.extra_standard_deductions
    if inp.deductions.itemized_total is not None and inp.deductions.itemized_total > standard:
        deduction_used, deduction_kind = inp.deductions.itemized_total, "itemized"
    else:
        deduction_used, deduction_kind = standard, "standard"

    taxable_income = _nonneg(agi - deduction_used)

    preferential = _nonneg(oi.qualified_dividends + oi.long_term_capital_gains)
    preferential = min(preferential, taxable_income)
    ordinary_ti = taxable_income - preferential

    ordinary_tax = _bracket_tax(ordinary_ti, tables.ordinary_brackets(status))
    cap_gains_tax = _capital_gains_tax(ordinary_ti, preferential, tables, status)
    income_tax_before_credits = ordinary_tax + cap_gains_tax

    add_medicare = _additional_medicare_tax(inp, tables, projected_wages)
    niit = _net_investment_income_tax(inp, tables, agi)
    tax_before_credits = income_tax_before_credits + se_tax + add_medicare + niit

    cr = inp.credits
    nonrefundable = cr.child_tax_credit + cr.other_nonrefundable_credits
    nonrefundable_applied = min(nonrefundable, tax_before_credits)
    refundable = cr.refundable_credits
    total_liability = tax_before_credits - nonrefundable_applied - refundable

    if nonrefundable > nonrefundable_applied:
        notes.append(
            "Nonrefundable credits exceeded tax before credits; the excess was not refunded. "
            "Some credits (e.g. the Additional Child Tax Credit) may be partly refundable in practice.")
    if oi.self_employment_net > ZERO or add_medicare > ZERO:
        notes.append(
            "SE tax and Additional Medicare Tax use projected Box 1 taxable wages as a proxy for "
            "SS/Medicare wages. These may differ when pre-tax deferrals (401(k), etc.) reduce Box 1; "
            "any difference is typically negligible for planning.")

    marginal = _marginal_rate(ordinary_ti, tables.ordinary_brackets(status))
    effective = (total_liability / agi) if agi > ZERO else ZERO

    breakdown = TaxBreakdown(
        projected_taxable_wages=_money(projected_wages), total_income=_money(total_income),
        adjustments_total=_money(adjustments_total), adjusted_gross_income=_money(agi),
        deduction_used=_money(deduction_used), deduction_kind=deduction_kind,
        taxable_income=_money(taxable_income), ordinary_income_tax=_money(ordinary_tax),
        capital_gains_tax=_money(cap_gains_tax),
        income_tax_before_credits=_money(income_tax_before_credits),
        self_employment_tax=_money(se_tax), additional_medicare_tax=_money(add_medicare),
        net_investment_income_tax=_money(niit), nonrefundable_credits=_money(nonrefundable_applied),
        refundable_credits=_money(refundable),
        total_tax_liability=_money(_nonneg(total_liability) if refundable == ZERO else total_liability),
        marginal_rate=marginal, effective_rate=effective.quantize(Decimal("0.0001")))
    return breakdown, notes


def _bracket_tax(amount: Decimal, brackets) -> Decimal:
    if amount <= ZERO:
        return ZERO
    tax = ZERO
    lower = ZERO
    for bracket in brackets:
        upper = bracket.up_to
        if upper is None or amount <= upper:
            tax += (amount - lower) * bracket.rate
            return tax
        tax += (upper - lower) * bracket.rate
        lower = upper
    return tax


def _marginal_rate(ordinary_ti: Decimal, brackets) -> Decimal:
    if ordinary_ti <= ZERO:
        return brackets[0].rate
    for bracket in brackets:
        upper = bracket.up_to
        if upper is None or ordinary_ti <= upper:
            return bracket.rate
    return brackets[-1].rate


def _capital_gains_tax(ordinary_ti: Decimal, preferential: Decimal,
                       tables: TaxTables, status: str) -> Decimal:
    """Preferential income stacked on top of ordinary TI through 0/15/20% bands."""
    if preferential <= ZERO:
        return ZERO
    zero_top, fifteen_top = tables.capital_gains_thresholds(status)
    tax = ZERO
    zero_room = _nonneg(zero_top - ordinary_ti)
    zero_amount = min(preferential, zero_room)
    remaining = preferential - zero_amount
    fifteen_start = max(ordinary_ti, zero_top)
    fifteen_room = _nonneg(fifteen_top - fifteen_start)
    fifteen_amount = min(remaining, fifteen_room)
    tax += fifteen_amount * Decimal("0.15")
    remaining -= fifteen_amount
    tax += remaining * Decimal("0.20")
    return tax


def _self_employment_tax(net_se: Decimal, wages_subject_to_ss: Decimal,
                         tables: TaxTables) -> tuple[Decimal, Decimal]:
    if net_se <= ZERO:
        return ZERO, ZERO
    se_base = net_se * tables.se_net_earnings_factor
    ss_room = _nonneg(tables.ss_wage_base - wages_subject_to_ss)
    ss_taxable = min(se_base, ss_room)
    ss_tax = ss_taxable * tables.se_social_security_rate
    medicare_tax = se_base * tables.se_medicare_rate
    se_tax = ss_tax + medicare_tax
    return se_tax, se_tax / 2


def _additional_medicare_tax(inp: EstimatorInput, tables: TaxTables,
                             projected_wages: Decimal) -> Decimal:
    se_base = _nonneg(inp.other_income.self_employment_net) * tables.se_net_earnings_factor
    medicare_wages = projected_wages + inp.other_income.spouse_taxable_wages + se_base
    threshold = tables.additional_medicare_threshold(inp.filing_status)
    excess = _nonneg(medicare_wages - threshold)
    return excess * tables.additional_medicare_rate


def _net_investment_income_tax(inp: EstimatorInput, tables: TaxTables, agi: Decimal) -> Decimal:
    oi = inp.other_income
    investment_income = _nonneg(
        oi.interest + oi.ordinary_dividends + oi.short_term_capital_gains
        + oi.long_term_capital_gains)
    if investment_income <= ZERO:
        return ZERO
    threshold = tables.niit_threshold(inp.filing_status)
    over_threshold = _nonneg(agi - threshold)
    base = min(investment_income, over_threshold)
    return base * tables.niit_rate


# ---------------------------------------------------------------------------
# Withholding recommendation
# ---------------------------------------------------------------------------

def _build_recommendation(inp: EstimatorInput, tables: TaxTables,
                          breakdown: TaxBreakdown) -> WithholdingRecommendation:
    projections = [_project_job(job) for job in inp.jobs]
    total_ytd_wh = sum((p.ytd_withholding for p in projections), ZERO)
    total_projected_wh = sum((p.projected_withholding for p in projections), ZERO)

    other_payments_total = (inp.other_payments.estimated_tax_payments
                            + inp.other_payments.other_withholding
                            + inp.other_income.spouse_federal_tax_withheld)

    liability = breakdown.total_tax_liability
    projected_total_payments = total_projected_wh + other_payments_total
    projected_balance = projected_total_payments - liability

    adjusted = inp.adjusted_job()
    adjusted_idx = next(i for i, p in enumerate(projections) if p.job is adjusted)
    adjusted_proj = projections[adjusted_idx]
    a_remaining = adjusted_proj.periods_remaining
    a_per_period_wh = adjusted.federal_tax_withheld_per_period
    a_ppy = adjusted.periods_per_year

    others_future_wh = sum(
        (p.projected_withholding - p.ytd_withholding
         for i, p in enumerate(projections) if i != adjusted_idx), ZERO)

    target = inp.target_refund
    already_secured = total_ytd_wh + other_payments_total
    required_from_adjusted = (liability + target) - already_secured - others_future_wh

    recommended_per_period = required_from_adjusted / a_remaining if a_remaining > 0 else ZERO
    additional_per_period = recommended_per_period - a_per_period_wh
    # Household-based: are projected payments already above the target refund?
    is_over = projected_balance > target

    safe_harbor_target = None
    safe_harbor_additional = None
    if inp.prior_year_tax is not None:
        safe_harbor_target = _safe_harbor_target(inp, tables, liability)
        sh_required = safe_harbor_target - already_secured - others_future_wh
        if a_remaining > 0:
            sh_per_period = sh_required / a_remaining
            safe_harbor_additional = _money(_nonneg(sh_per_period - a_per_period_wh))

    job_breakdown = [
        JobProjection(
            name=p.job.name or f"Job {i + 1}", pay_frequency=p.job.pay_frequency,
            periods_per_year=p.job.periods_per_year, periods_remaining=p.periods_remaining,
            projected_taxable_wages=_money(p.projected_wages),
            projected_withholding=_money(p.projected_withholding),
            periods_elapsed=p.periods_elapsed, ytd_withholding=_money(p.ytd_withholding))
        for i, p in enumerate(projections)]

    return WithholdingRecommendation(
        periods_per_year=a_ppy, periods_remaining=a_remaining,
        periods_elapsed=adjusted_proj.periods_elapsed, ytd_withholding=_money(total_ytd_wh),
        projected_withholding_current_rate=_money(total_projected_wh),
        other_payments_total=_money(other_payments_total),
        projected_total_payments=_money(projected_total_payments),
        projected_balance=_money(projected_balance), target_refund=_money(target),
        required_remaining_withholding=_money(_nonneg(required_from_adjusted)),
        recommended_withholding_per_period=_money(_nonneg(recommended_per_period)),
        additional_withholding_per_period=_money(_nonneg(additional_per_period)),
        is_over_withholding=is_over,
        safe_harbor_target=_money(safe_harbor_target) if safe_harbor_target is not None else None,
        safe_harbor_additional_per_period=safe_harbor_additional,
        adjusted_job_name=job_breakdown[adjusted_idx].name,
        adjusted_job_pay_frequency=adjusted.pay_frequency,
        adjusted_job_withholding_per_period=_money(a_per_period_wh),
        job_breakdown=job_breakdown)


def _safe_harbor_target(inp: EstimatorInput, tables: TaxTables,
                        current_liability: Decimal) -> Decimal:
    sh = tables.safe_harbor()
    current_target = current_liability * Decimal(str(sh["current_year_pct"]))
    prior_tax = inp.prior_year_tax or ZERO
    if inp.filing_status == "married_separately":
        high_threshold = Decimal(str(sh["high_income_agi_threshold_mfs"]))
    else:
        high_threshold = Decimal(str(sh["high_income_agi_threshold"]))
    prior_pct = Decimal(str(sh["prior_year_pct"]))
    if inp.prior_year_agi is not None and inp.prior_year_agi > high_threshold:
        prior_pct = Decimal(str(sh["prior_year_pct_high_income"]))
    prior_target = prior_tax * prior_pct
    return min(current_target, prior_target)
