"""The withholding estimation engine (ported from the standalone ``twe`` tool).

The flow mirrors a Form 1040 projection:

1. Project full-year taxable wages and other income (capital losses limited).
2. Subtract above-the-line adjustments to reach AGI.
3. Take the larger of the standard deduction and Schedule A -- built from its
   parts with the SALT cap and the medical and charity floors -- then the four
   Schedule 1-A deductions and the QBI deduction.
4. Tax ordinary income through the brackets and stack qualified dividends /
   long-term gains through the preferential 0/15/20% capital-gains rates.
5. Subtract nonrefundable credits (Schedule 8812 computed from the household)
   from income tax; add self-employment tax, the Additional Medicare Tax and the
   Net Investment Income Tax; subtract the refundable credits.
6. Compare projected payments -- withholding, estimates, and the two credits a
   paystub's federal line leaves out -- against the liability; translate the gap
   into a per-paycheck W-4 line 4c change, test the underpayment penalty, and
   lay out the estimated payments still due.

WHAT IT WAS NOT TOLD, IT ASSUMES OUT LOUD. The firm, 17 October 2026: "maybe we
won't have certain info and it has to make an assumption as to maybe standard
deduction instead of itemized". Every such fill-in is an :class:`Assumption` on
the result, with what would change if it is wrong; every hazard the inputs show
is a :class:`Check`. A TAX-LAW value is never assumed -- a year that is not on
file is refused by :mod:`satc.withholding.tax_data`. See DESIGN-PRINCIPLES §5a.

Tax constants come from SATC's dated crosswalk via
:mod:`satc.withholding.tax_data`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

from satc.withholding.models import (
    Assumption,
    Check,
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
THOUSAND = Decimal("1000")

_STATUS_LABEL = {
    "single": "Single",
    "married_jointly": "Married filing jointly",
    "married_separately": "Married filing separately",
    "head_of_household": "Head of household",
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def _nonneg(value: Decimal) -> Decimal:
    return value if value > ZERO else ZERO


def _usd(value: Decimal) -> str:
    return f"${value:,.0f}"


def _thousands_down(amount: Decimal) -> Decimal:
    return (amount / THOUSAND).to_integral_value(rounding=ROUND_FLOOR)


def _thousands_up(amount: Decimal) -> Decimal:
    return (amount / THOUSAND).to_integral_value(rounding=ROUND_CEILING)


def estimate(inp: EstimatorInput, *, today: date | None = None) -> EstimateResult:
    """Run a full withholding estimate for the given input.

    ``today`` places the estimate in the year (which estimated-tax due dates
    are still ahead); it defaults to the real date.
    """
    today = today or date.today()
    tables, notes = load_tax_tables(inp.tax_year)
    notes = list(notes)
    status = inp.filing_status or "single"
    ctx = _Context(inp=inp, tables=tables, status=status, today=today)
    breakdown, extra_notes = _build_breakdown(ctx)
    notes.extend(extra_notes)
    recommendation = _build_recommendation(ctx, breakdown)
    result = EstimateResult(
        tax_year_used=tables.tax_year, filing_status=status,
        breakdown=breakdown, recommendation=recommendation, notes=notes)
    result.assumptions = _assumptions(ctx)
    result.checks = _checks(ctx, breakdown, recommendation)
    result.headline = _headline(ctx, breakdown, recommendation)
    return result


@dataclass(slots=True)
class _Context:
    """What one estimate is working from, plus figures worked out on the way
    that the checks need to see again."""

    inp: EstimatorInput
    tables: TaxTables
    status: str
    today: date
    earned_income: Decimal = ZERO
    agi: Decimal = ZERO
    net_capital: Decimal = ZERO
    investment_income: Decimal = ZERO
    ctc_before_limit: Decimal = ZERO
    eitc_ineligible_reason: str = ""
    qbi_income: Decimal = ZERO
    qbi_over_threshold: bool = False
    medicare_wages: Decimal = ZERO


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


def _build_breakdown(ctx: _Context) -> tuple[TaxBreakdown, list[str]]:
    inp, tables, status = ctx.inp, ctx.tables, ctx.status
    notes: list[str] = []
    oi = inp.other_income

    projected_wages = _total_projected_wages(inp)
    se_tax, half_se = _self_employment_tax(oi.self_employment_net, projected_wages, tables)

    # CAPITAL GAINS NET BEFORE THEY ENTER INCOME, AND A NET LOSS IS CAPPED.
    # Schedule D line 21: a net capital loss reduces income by at most $3,000
    # ($1,500 MFS); the rest carries forward. Until 17 October 2026 the engine
    # added a loss in full, so a $20,000 loss cut income by $20,000.
    net_capital = oi.short_term_capital_gains + oi.long_term_capital_gains
    limit = tables.capital_loss_limit(status)
    capital_in_income = net_capital if net_capital >= ZERO else max(net_capital, -limit)
    carryover = _nonneg(-net_capital - limit)
    ctx.net_capital = net_capital

    total_income = (
        projected_wages + oi.interest + oi.ordinary_dividends
        + oi.taxable_retirement_distributions + oi.taxable_social_security
        + capital_in_income + oi.self_employment_net + oi.unemployment
        + oi.rental_and_passive_income + oi.other_taxable_income + oi.spouse_taxable_wages)

    adj = inp.adjustments
    adjustments_total = (adj.traditional_ira_deduction + adj.hsa_deduction
                         + adj.student_loan_interest + adj.other_adjustments + half_se)
    agi = _nonneg(total_income - adjustments_total)
    ctx.agi = agi
    magi = agi  # equal unless foreign/Puerto Rico income is excluded

    # -- the deduction: the larger of standard and itemized ------------------
    d = inp.deductions
    standard = tables.standard_deduction(status) + \
        tables.extra_standard_deduction(status) * _extra_boxes(inp, status)
    charity_cash = d.charitable_cash or ZERO
    nonitemizer_charity = min(charity_cash, tables.charity_nonitemizer_max(status))
    itemized = _itemized(ctx, agi)
    if itemized is not None and itemized > standard + nonitemizer_charity:
        deduction_used, deduction_kind = itemized, "itemized"
    else:
        deduction_used, deduction_kind = standard + nonitemizer_charity, "standard"

    # -- Schedule 1-A (line 13b) ---------------------------------------------
    tips, overtime, car, senior = _schedule_1a(ctx, magi)
    sched_1a = tips + overtime + car + senior

    # -- preferential income, then QBI ---------------------------------------
    net_lt = oi.long_term_capital_gains
    net_capital_gain = _nonneg(min(net_lt, net_capital))
    preferential_raw = _nonneg(oi.qualified_dividends) + net_capital_gain
    ti_before_qbi = _nonneg(agi - deduction_used - sched_1a)
    qbi = _qbi_deduction(ctx, ti_before_qbi, preferential_raw, half_se)
    taxable_income = _nonneg(ti_before_qbi - qbi)

    preferential = min(preferential_raw, taxable_income)
    ordinary_ti = taxable_income - preferential

    ordinary_tax = _bracket_tax(ordinary_ti, tables.ordinary_brackets(status))
    cap_gains_tax = _capital_gains_tax(ordinary_ti, preferential, tables, status)
    income_tax_before_credits = ordinary_tax + cap_gains_tax

    add_medicare = _additional_medicare_tax(ctx, projected_wages)
    ctx.investment_income = _nonneg(oi.interest + oi.ordinary_dividends + _nonneg(net_capital)
                                    + _nonneg(oi.rental_and_passive_income))
    niit = _net_investment_income_tax(ctx, agi)

    # -- credits ---------------------------------------------------------------
    # NONREFUNDABLE CREDITS OFFSET INCOME TAX ONLY. Form 1040 line 22 subtracts
    # them from the income tax on line 18; self-employment tax and the other
    # Schedule 2 taxes are added AFTER, on line 23. The engine used to let them
    # offset SE tax too, so a sole proprietor with little income tax and a
    # child credit showed a smaller bill than the return would.
    earned = _nonneg(projected_wages + oi.spouse_taxable_wages + oi.self_employment_net - half_se)
    ctx.earned_income = earned
    cr = inp.credits
    remaining_tax = income_tax_before_credits
    other_nonref = min(cr.other_nonrefundable_credits, remaining_tax)
    remaining_tax -= other_nonref
    if cr.child_tax_credit is not None:
        child_credit = min(cr.child_tax_credit, remaining_tax)
        actc = ZERO
        if cr.child_tax_credit > child_credit:
            notes.append(
                "The child tax credit typed in is more than the income tax, so part of it was not "
                "used. Leave that box blank and enter the children instead, and the estimator works "
                "out the refundable part (the additional child tax credit) itself.")
    else:
        child_credit, actc = _child_tax_credit(ctx, agi, remaining_tax, earned)
    remaining_tax -= child_credit
    nonrefundable_applied = other_nonref + child_credit

    eitc = _earned_income_credit(ctx, agi, earned)
    refundable = cr.refundable_credits + actc + eitc
    tax_after_credits = remaining_tax + se_tax + add_medicare + niit
    total_liability = tax_after_credits - refundable

    if oi.self_employment_net > ZERO or add_medicare > ZERO:
        notes.append(
            "SE tax and Additional Medicare Tax use projected Box 1 taxable wages as a proxy for "
            "SS/Medicare wages. These may differ when pre-tax deferrals (401(k), etc.) reduce Box 1; "
            "any difference is typically negligible for planning.")
    # THE FIGURES THIS RESTS ON WERE READ BY SOFTWARE, and nothing outside this
    # repository can say whether that reading was right.
    #
    # Eight of the nine computations behind an estimate are tied to an IRS
    # document. The ninth is the paystub reader, and it CANNOT be: **the IRS
    # publishes nothing describing what a paystub looks like.** So it is MARKED
    # rather than proved. The reader scores 126 of 126 on an eighteen-stub
    # corpus written here, which is not an accuracy figure.
    if any(job.ytd_taxable_wages is not None or job.ytd_federal_tax_withheld is not None
           for job in inp.jobs):
        notes.append(
            "Figures taken from a paystub were read by software. Nothing outside this "
            "machine can confirm a reading is right -- the IRS publishes no description "
            "of a paystub, so there is nothing to check one against. Compare the wages "
            "and withholding above against the stub before acting on this.")
    # WHAT THIS ESTIMATOR'S NET INVESTMENT INCOME LEAVES OUT, said when the tax
    # actually applies. Tied to Form 8960 on 7 September 2026: the lesser-of
    # rule, the 3.8% rate and the thresholds agree with the form; the SCOPE of
    # "net investment income" does not (no rents, royalties, annuities or
    # passive business income; no deductions against it). Rents, royalties
    # and passive K-1 income have had their own field since PR #451.
    if niit > ZERO:
        notes.append(
            "Net investment income here counts interest, dividends, capital gains and the "
            "rents, royalties and passive income entered. Annuities are NOT included, so "
            "somebody with a nonqualified annuity is too low; deductions against investment "
            "income are not modelled, so somebody with investment interest expense is too high. "
            "The threshold test uses AGI, which equals MAGI unless foreign earned income is "
            "excluded.")

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
        total_tax_liability=_money(total_liability),
        marginal_rate=marginal, effective_rate=effective.quantize(Decimal("0.0001")),
        itemized_computed=None if itemized is None else _money(itemized),
        standard_computed=_money(standard + nonitemizer_charity),
        schedule_1a_deduction=_money(sched_1a), tips_deduction=_money(tips),
        overtime_deduction=_money(overtime), car_loan_deduction=_money(car),
        senior_deduction=_money(senior), qbi_deduction=_money(qbi),
        capital_gain_in_income=_money(capital_in_income),
        capital_loss_carryover=_money(carryover),
        child_and_dependent_credit=_money(child_credit),
        additional_child_tax_credit=_money(actc), earned_income_credit=_money(eitc))
    return breakdown, notes


def _extra_boxes(inp: EstimatorInput, status: str) -> int:
    """How many age-or-blind boxes the standard deduction gets (Form 1040 page 1).

    The spouse's box counts on a joint return only. ``extra_standard_deductions``
    is the older single-number input and is added as given.
    """
    hh = inp.household
    boxes = int(bool(hh.taxpayer_65_or_older)) + hh.blind_count + inp.deductions.extra_standard_deductions
    if status == "married_jointly" and hh.spouse_65_or_older:
        boxes += 1
    return boxes


def _salt_limit(ctx: _Context, magi: Decimal, paid: Decimal) -> Decimal:
    """2025 Instructions for Schedule A, State and Local Tax Deduction Worksheet."""
    t = ctx.tables
    mfs = ctx.status == "married_separately"
    floor = t.salt_floor / 2 if mfs else t.salt_floor
    if paid <= floor:                                  # worksheet line 1, "No"
        return paid
    line1 = t.salt_cap
    threshold = t.salt_phasedown_threshold / 2 if mfs else t.salt_phasedown_threshold
    if magi > threshold:
        line9 = max(line1 - (magi - threshold) * t.salt_phasedown_rate, t.salt_floor)
    else:
        line9 = line1
    return min(line9 / 2 if mfs else line9, paid)      # line 10


def _itemized(ctx: _Context, agi: Decimal) -> Decimal | None:
    """Schedule A from its parts, or the finished figure, or None if neither."""
    d = ctx.inp.deductions
    if d.itemized_total is not None:
        return d.itemized_total
    if not d.itemized_parts_given():
        return None
    t = ctx.tables
    medical = _nonneg((d.medical_expenses or ZERO) - agi * t.medical_agi_floor)
    salt = _salt_limit(ctx, agi, (d.state_local_income_or_sales_tax or ZERO) + (d.property_taxes or ZERO))
    charity = (d.charitable_cash or ZERO) + (d.charitable_noncash or ZERO)
    charity = _nonneg(charity - agi * t.charity_itemized_floor_pct)
    return medical + salt + (d.mortgage_interest or ZERO) + charity + (d.other_itemized or ZERO)


def _schedule_1a(ctx: _Context, magi: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Schedule 1-A (Form 1040) 2025, Parts II-V, line for line.

    Tips, overtime and the senior deduction need a joint return if married
    (the form's caution on each part); car loan interest does not.
    """
    t, status, s1a, hh = ctx.tables, ctx.status, ctx.inp.schedule_1a, ctx.inp.household
    joint_ok = status != "married_separately"

    def phase_down(amount: Decimal, start: Decimal) -> Decimal:
        over = magi - start                                        # lines 10 / 18
        if over <= ZERO:
            return amount
        return _nonneg(amount - _thousands_down(over) * t.tips_overtime_phaseout_per_1000)

    tips = overtime = ZERO
    if joint_ok:
        start = t.tips_overtime_phaseout_start(status)
        tips = phase_down(min(_nonneg(s1a.qualified_tips), t.tips_max), start)
        overtime = phase_down(min(_nonneg(s1a.qualified_overtime), t.overtime_max(status)), start)

    car = min(_nonneg(s1a.car_loan_interest), t.car_loan_max)      # line 24
    over = magi - t.car_loan_phaseout_start(status)                # line 27
    if over > ZERO:
        car = _nonneg(car - _thousands_up(over) * t.car_loan_phaseout_per_1000)

    senior = ZERO
    if joint_ok:
        people = int(bool(hh.taxpayer_65_or_older))
        if status == "married_jointly" and hh.spouse_65_or_older:
            people += 1
        each = _nonneg(t.senior_amount - _nonneg(magi - t.senior_phaseout_start(status)) * t.senior_phaseout_rate)
        senior = each * people
    return tips, overtime, car, senior


def _qbi_deduction(ctx: _Context, ti_before_qbi: Decimal, net_capital_gain: Decimal,
                   half_se: Decimal) -> Decimal:
    """Form 8995 for a sole proprietor: 20% of QBI, limited to 20% of taxable
    income less net capital gain. Above the threshold the wage and SSTB limits
    of Form 8995-A apply and are NOT modelled -- a check says so."""
    t = ctx.tables
    qbi = _nonneg(ctx.inp.other_income.self_employment_net - half_se)
    ctx.qbi_income = qbi
    if qbi <= ZERO:
        return ZERO
    ctx.qbi_over_threshold = ti_before_qbi > t.qbi_threshold(ctx.status)
    deduction = min(qbi * t.qbi_rate, _nonneg(ti_before_qbi - net_capital_gain) * t.qbi_rate)
    minimum, needs = t.qbi_minimum
    if minimum > ZERO and qbi >= needs:
        deduction = min(max(deduction, minimum), ti_before_qbi)
    return deduction


def _child_tax_credit(ctx: _Context, agi: Decimal, tax_room: Decimal,
                      earned: Decimal) -> tuple[Decimal, Decimal]:
    """Schedule 8812 (Form 1040) 2025, Parts I and II-A.

    Returns (credit used against income tax, additional child tax credit).
    Part II-B -- the Social Security alternative for three or more children --
    is not modelled; it can only make the refundable part larger.
    """
    t, hh = ctx.tables, ctx.inp.household
    kids = hh.children_under_17 or 0
    others = hh.other_dependents or 0
    line8 = kids * t.ctc_per_child + others * t.odc_per_dependent
    over = agi - t.ctc_phaseout_threshold(ctx.status)                # line 10
    reduction = _thousands_up(over) * t.ctc_phaseout_per_1000 if over > ZERO else ZERO
    line12 = _nonneg(line8 - reduction)
    ctx.ctc_before_limit = line12
    used = min(line12, _nonneg(tax_room))                             # line 14
    if kids == 0 or line12 <= used:
        return used, ZERO
    line17 = min(line12 - used, kids * t.actc_max_per_child)
    line20 = _nonneg(earned - t.actc_earned_income_floor) * t.actc_earned_income_rate
    return used, min(line17, line20)


def _childless_age_ok(ctx: _Context) -> bool:
    """With no qualifying child, the taxpayer -- or the spouse, on a joint
    return -- must be 25 through 64 at the end of the year. An age not given
    is assumed in range, and that is said in the assumptions."""
    hh = ctx.inp.household
    people = [(hh.taxpayer_under_25, hh.taxpayer_65_or_older)]
    if ctx.status == "married_jointly":
        people.append((hh.spouse_under_25, hh.spouse_65_or_older))
    return any(not under and not over for under, over in people)


def _earned_income_credit(ctx: _Context, agi: Decimal, earned: Decimal) -> Decimal:
    """IRC sec. 32 from the revenue procedure's table.

    The phase-in rate is the maximum credit over the earned income amount, and
    the phase-out rate the maximum credit over the phase-out range -- both read
    off the published columns rather than carried as constants. The IRS tables
    in the 1040 instructions work in $50 bands, so this can differ from them
    by a few dollars.
    """
    t, hh = ctx.tables, ctx.inp.household
    if earned <= ZERO:
        return ZERO
    if ctx.status == "married_separately":
        ctx.eitc_ineligible_reason = "married filing separately"
        return ZERO
    if ctx.investment_income > t.eitc_investment_income_limit:
        ctx.eitc_ineligible_reason = (f"investment income over {_usd(t.eitc_investment_income_limit)}")
        return ZERO
    kids = hh.eitc_children if hh.eitc_children is not None else (hh.children_under_17 or 0)
    if kids == 0 and not _childless_age_ok(ctx):
        ctx.eitc_ineligible_reason = "no qualifying children and nobody on the return aged 25 to 64"
        return ZERO
    row = t.eitc_row(ctx.status, kids)
    phase_in = row["max_credit"] / row["earned_income_amount"]
    phase_out = row["max_credit"] / (row["completed"] - row["threshold"])
    credit = min(earned * phase_in, row["max_credit"])
    over = max(agi, earned) - row["threshold"]
    if over > ZERO:
        credit -= over * phase_out
    return _nonneg(credit)


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
    rate_0, rate_15, rate_20 = tables.capital_gains_rates()
    tax = ZERO
    zero_room = _nonneg(zero_top - ordinary_ti)
    zero_amount = min(preferential, zero_room)
    remaining = preferential - zero_amount
    fifteen_start = max(ordinary_ti, zero_top)
    fifteen_room = _nonneg(fifteen_top - fifteen_start)
    fifteen_amount = min(remaining, fifteen_room)
    tax += zero_amount * rate_0
    tax += fifteen_amount * rate_15
    remaining -= fifteen_amount
    tax += remaining * rate_20
    return tax


def _se_earnings_subject_to_tax(net_se: Decimal, tables: TaxTables) -> Decimal:
    """Schedule SE line 4c, and ZERO where the schedule tells you to stop.

    THE FORM PUTS A FLOOR ON ITSELF AND THE ENGINE DID NOT HAVE IT. Line 4a
    multiplies net earnings by 92.35%; line 4c then says, in the form's own
    words, *"Combine lines 4a and 4b. If less than $400, stop; you don't owe
    self-employment tax."*

    Found on 7 September 2026 by tying the computation to the form rather than
    to our own constants: the engine charged **$56.52 on net earnings of $400**,
    where the form charges nothing.

    One function because TWO places need the answer, and they must not disagree:
    the SE tax itself, and the Additional Medicare Tax, whose Form 8959 line 8
    reads *"Enter your self-employment income from Schedule SE (Form 1040),
    Part I, line 6"* -- a line you never reach if 4c stopped you. That second
    use is an inference from the form, not a printed rule.
    """
    if net_se <= ZERO:
        return ZERO
    base = net_se * tables.se_net_earnings_factor
    return ZERO if base < tables.se_minimum_net_earnings else base


def _self_employment_tax(net_se: Decimal, wages_subject_to_ss: Decimal,
                         tables: TaxTables) -> tuple[Decimal, Decimal]:
    se_base = _se_earnings_subject_to_tax(net_se, tables)
    if se_base <= ZERO:
        return ZERO, ZERO
    ss_room = _nonneg(tables.ss_wage_base - wages_subject_to_ss)
    ss_taxable = min(se_base, ss_room)
    ss_tax = ss_taxable * tables.se_social_security_rate
    medicare_tax = se_base * tables.se_medicare_rate
    se_tax = ss_tax + medicare_tax
    return se_tax, se_tax / 2


def _additional_medicare_tax(ctx: _Context, projected_wages: Decimal) -> Decimal:
    # Form 8959 line 8 reads Schedule SE line 6, which does not exist when line
    # 4c stopped the schedule -- so the same floor applies here.
    inp, tables = ctx.inp, ctx.tables
    se_base = _se_earnings_subject_to_tax(_nonneg(inp.other_income.self_employment_net), tables)
    medicare_wages = projected_wages + inp.other_income.spouse_taxable_wages + se_base
    ctx.medicare_wages = medicare_wages
    threshold = tables.additional_medicare_threshold(ctx.status)
    excess = _nonneg(medicare_wages - threshold)
    return excess * tables.additional_medicare_rate


def _net_investment_income_tax(ctx: _Context, agi: Decimal) -> Decimal:
    if ctx.investment_income <= ZERO:
        return ZERO
    threshold = ctx.tables.niit_threshold(ctx.status)
    over_threshold = _nonneg(agi - threshold)
    base = min(ctx.investment_income, over_threshold)
    return base * ctx.tables.niit_rate


# ---------------------------------------------------------------------------
# Withholding recommendation and the penalty test
# ---------------------------------------------------------------------------

def _payroll_credits(ctx: _Context, projections: list[_JobProjection]) -> tuple[Decimal, Decimal]:
    """Two payments the paystub's federal-tax line does not show.

    1. ADDITIONAL MEDICARE TAX WITHHELD. An employer withholds 0.9% on wages it
       pays over $200,000, whatever the filing status (IRC sec. 3102(f)). It is
       a payment on Form 1040 line 25c via Form 8959. Without it, anyone paid
       more than $200,000 by one employer showed a balance due they do not owe.
    2. EXCESS SOCIAL SECURITY. Each employer withholds 6.2% up to the wage base
       on its own, so one person with two employers can overpay; the excess is
       a refundable credit (Schedule 3 line 11). Grouped by whose job it is.

    Both use projected Box 1 wages as the proxy for Medicare / Social Security
    wages, like the rest of the engine.
    """
    t = ctx.tables
    addl = sum((_nonneg(p.projected_wages - t.addl_medicare_employer_threshold) * t.additional_medicare_rate
                for p in projections), ZERO)
    employee_ss_rate = t.se_social_security_rate / 2   # 6.2%, IRC sec. 3101(a)
    excess = ZERO
    owners: dict[str, list[Decimal]] = {}
    for p in projections:
        owners.setdefault(p.job.owner or "you", []).append(p.projected_wages)
    for wages in owners.values():
        if len(wages) < 2:
            continue
        withheld = sum((min(w, t.ss_wage_base) for w in wages), ZERO) * employee_ss_rate
        owed = min(sum(wages, ZERO), t.ss_wage_base) * employee_ss_rate
        excess += _nonneg(withheld - owed)
    return addl, excess


def _installment_plan(ctx: _Context, required: Decimal, withholding: Decimal,
                      estimated_paid: Decimal) -> list[tuple[str, Decimal]]:
    """The 1040-ES payments still due, each bringing the total up to date.

    Form 1040-ES: a quarter of the required annual payment is due by each
    date, cumulatively. Withholding counts as paid evenly through the year
    (IRC sec. 6654(g)(1)); estimated payments already made count from the
    start. A date already passed is not spread over the dates left -- it is
    owed now, so it goes into the next payment. Spreading it left somebody
    starting in August a quarter short until January (Codex review, PR #451).
    """
    dates = ctx.tables.est_tax_due_dates
    plan: list[tuple[str, Decimal]] = []
    paid_in_plan = ZERO
    for k, d in enumerate(dates, start=1):
        if date.fromisoformat(d) < ctx.today:
            continue
        due_by_now = _nonneg((required - withholding) * k / len(dates) - estimated_paid)
        payment = _money(_nonneg(due_by_now - paid_in_plan))
        paid_in_plan += payment
        if payment > ZERO:
            plan.append((d, payment))
    return plan


def _build_recommendation(ctx: _Context, breakdown: TaxBreakdown) -> WithholdingRecommendation:
    inp, tables = ctx.inp, ctx.tables
    projections = [_project_job(job) for job in inp.jobs]
    total_ytd_wh = sum((p.ytd_withholding for p in projections), ZERO)
    total_projected_wh = sum((p.projected_withholding for p in projections), ZERO)
    addl_medicare_wh, excess_ss = _payroll_credits(ctx, projections)

    withholding_like = (inp.other_payments.other_withholding
                        + inp.other_income.spouse_federal_tax_withheld
                        + addl_medicare_wh + excess_ss)
    other_payments_total = inp.other_payments.estimated_tax_payments + withholding_like

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
    is_over = projected_balance > target

    # -- the penalty test: IRC sec. 6654, Pub. 505 chapter 4 -------------------
    required, basis = _required_annual_payment(ctx, liability)
    safe_harbor_target = None
    safe_harbor_additional = None
    if inp.prior_year_tax is not None:
        safe_harbor_target = required
        sh_required = required - already_secured - others_future_wh
        if a_remaining > 0:
            safe_harbor_additional = _money(_nonneg(sh_required / a_remaining - a_per_period_wh))
    withholding_total = total_projected_wh + withholding_like
    shortfall = _nonneg(required - projected_total_payments)
    penalty_risk = (liability - withholding_total >= tables.underpayment_penalty_floor
                    and shortfall > ZERO)
    plan = _installment_plan(ctx, required, withholding_total,
                             inp.other_payments.estimated_tax_payments) if penalty_risk else []

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
        job_breakdown=job_breakdown,
        additional_medicare_withheld=_money(addl_medicare_wh),
        excess_social_security_credit=_money(excess_ss),
        required_annual_payment=_money(required), required_annual_payment_basis=basis,
        penalty_risk=penalty_risk, safe_harbor_shortfall=_money(shortfall),
        estimated_payments_remaining=plan)


def _required_annual_payment(ctx: _Context, current_liability: Decimal) -> tuple[Decimal, str]:
    """The smaller of 90% of this year's tax and 100%/110% of last year's.

    Pub. 505: no penalty if last year's tax was zero. Without last year's tax
    only the 90% test can be run, and an assumption says so.
    """
    inp = ctx.inp
    sh = ctx.tables.safe_harbor()
    current = _nonneg(current_liability) * Decimal(str(sh["current_year_pct"]))
    if inp.prior_year_tax is None:
        return current, "90% of this year's tax; last year's tax was not given"
    if inp.prior_year_tax <= ZERO:
        return ZERO, "last year's tax was zero"
    pct = _prior_year_pct(inp, sh, ctx.status)
    prior = inp.prior_year_tax * pct
    if prior <= current:
        return prior, f"{pct * 100:.0f}% of last year's tax"
    return current, "90% of this year's tax"


def _prior_year_pct(inp: EstimatorInput, sh: dict, status: str) -> Decimal:
    if status == "married_separately":
        high_threshold = Decimal(str(sh["high_income_agi_threshold_mfs"]))
    else:
        high_threshold = Decimal(str(sh["high_income_agi_threshold"]))
    if inp.prior_year_agi is not None and inp.prior_year_agi > high_threshold:
        return Decimal(str(sh["prior_year_pct_high_income"]))
    return Decimal(str(sh["prior_year_pct"]))


def _safe_harbor_target(inp: EstimatorInput, tables: TaxTables,
                        current_liability: Decimal, status: str | None = None) -> Decimal:
    """Pub. 505 safe harbour: the smaller of 90% of this year and 100/110% of last."""
    status = status or inp.filing_status or "single"
    sh = tables.safe_harbor()
    current_target = _nonneg(current_liability) * Decimal(str(sh["current_year_pct"]))
    prior_target = (inp.prior_year_tax or ZERO) * _prior_year_pct(inp, sh, status)
    return min(current_target, prior_target)


# ---------------------------------------------------------------------------
# What it assumed, what it noticed, and the one-line answer
# ---------------------------------------------------------------------------

def _assumptions(ctx: _Context) -> list[Assumption]:
    inp, t, status = ctx.inp, ctx.tables, ctx.status
    hh, d = inp.household, inp.deductions
    out: list[Assumption] = []
    add = lambda topic, assumed, if_wrong: out.append(Assumption(topic, assumed, if_wrong))  # noqa: E731

    if inp.filing_status is None:
        add("Filing status", "Single",
            "Married filing jointly roughly doubles the brackets and the standard deduction.")
    if inp.tax_year is None:
        add("Tax year", f"{t.tax_year}, the newest year on file", "Pick the year on the form.")
    if d.itemized_total is None and not d.itemized_parts_given():
        add("Deduction", f"Standard deduction ({_usd(t.standard_deduction(status))})",
            "If mortgage interest, state and property taxes and gifts to charity add up to more, "
            "enter them and the estimator will itemize.")
    if hh.taxpayer_65_or_older is None or (status == "married_jointly" and hh.spouse_65_or_older is None):
        add("Age", "Nobody on the return is 65 or older",
            f"Each person 65+ adds {_usd(t.extra_standard_deduction(status))} to the standard deduction "
            f"and up to {_usd(t.senior_amount)} more through the senior deduction.")
    if hh.children_under_17 is None and hh.other_dependents is None and inp.credits.child_tax_credit is None:
        add("Dependents", "No children or other dependents",
            f"Each child under 17 is worth up to {_usd(t.ctc_per_child)} in credit; "
            f"each other dependent {_usd(t.odc_per_dependent)}.")
    kids = hh.children_under_17 or 0
    eitc_reachable = ctx.earned_income > ZERO and status != "married_separately" and         max(ctx.agi, ctx.earned_income) < t.eitc_row(status, max(kids, 3))["completed"]
    if hh.eitc_children is None and kids > 0 and eitc_reachable:
        add("Earned income credit", "The children under 17 are the qualifying children",
            "Children under 19, or under 24 and a student, also count for this credit.")
    eitc_kids = hh.eitc_children if hh.eitc_children is not None else kids
    joint = status == "married_jointly"
    if (eitc_kids == 0 and eitc_reachable and not ctx.eitc_ineligible_reason
            and (hh.taxpayer_under_25 is None or (joint and hh.spouse_under_25 is None))):
        add("Earned income credit", "Somebody on the return is 25 or older",
            "With no qualifying child the credit needs somebody aged 25 to 64. "
            "If everyone is under 25, it is zero.")
    if inp.prior_year_tax is None:
        add("Last year's tax", "Not given, so only the 90%-of-this-year test was run",
            "Enter last year's total tax (Form 1040 line 24) -- paying that much "
            "(110% if last year's AGI was over $150,000) avoids the penalty however this year ends up.")
    for i, job in enumerate(inp.jobs):
        label = job.name or f"Job {i + 1}"
        if job.ytd_taxable_wages is None and job.pay_periods_remaining is None:
            add(f"{label}: pay so far", "Every paycheck this year matches this one, all year",
                "Enter the year-to-date figures from the latest paystub for a mid-year projection.")
        elif job.ytd_taxable_wages is None or job.ytd_federal_tax_withheld is None:
            add(f"{label}: pay so far", "Year-to-date wages or withholding were worked out from this paycheck",
                "A raise, bonus or W-4 change earlier in the year would make that wrong.")
    return out


def _checks(ctx: _Context, b: TaxBreakdown, rec: WithholdingRecommendation) -> list[Check]:
    inp, t, status = ctx.inp, ctx.tables, ctx.status
    oi, hh, s1a = inp.other_income, inp.household, inp.schedule_1a
    out: list[Check] = []
    add = lambda level, title, detail: out.append(Check(level, title, detail))  # noqa: E731

    # -- money on the line ---------------------------------------------------
    if rec.penalty_risk:
        plan = "; ".join(f"{_usd(a)} by {date.fromisoformat(dt):%b %d, %Y}"
                         for dt, a in rec.estimated_payments_remaining)
        how = (f"Either add about {_usd(rec.safe_harbor_shortfall / rec.periods_remaining)} per paycheck "
               f"(withholding counts as paid evenly through the year, so it also covers the months "
               f"already gone)" if rec.periods_remaining > 0 else "Withholding cannot fix it now")
        how += f", or pay estimated tax: {plan}." if plan else \
            ". Every estimated-tax due date for this year has passed; pay the balance with the return."
        add("act", "Underpayment penalty likely",
            f"Payments of {_usd(rec.projected_total_payments)} fall {_usd(rec.safe_harbor_shortfall)} short "
            f"of the {_usd(rec.required_annual_payment)} needed to avoid it "
            f"({rec.required_annual_payment_basis}). {how} Estimated payments made late in the "
            f"year may not avoid the penalty for earlier quarters.")
    if oi.self_employment_net > ZERO and inp.other_payments.estimated_tax_payments == ZERO \
            and b.self_employment_tax > ZERO:
        add("act" if rec.penalty_risk else "review", "Self-employment income with no estimated payments",
            f"Nothing withholds the {_usd(b.self_employment_tax)} of self-employment tax. "
            f"It has to come from estimated payments or extra withholding on a job.")
    if len(inp.jobs) >= 2 and rec.projected_balance < -t.underpayment_penalty_floor:
        add("act", "Two or more jobs and a balance due",
            "Each employer withholds as if its job were the only one. Ticking Step 2 on each "
            "W-4, or using the line 4(c) amount above, fixes that.")
    big_refund = rec.projected_balance - rec.target_refund
    if big_refund > THOUSAND and rec.periods_remaining > 0:
        cut = big_refund / rec.periods_remaining
        add("info", "More is being withheld than needed",
            f"About {_usd(big_refund)} more than the target refund. Withholding about "
            f"{_usd(cut)} less per paycheck on {rec.adjusted_job_name} would even it out.")
    if status == "married_separately" and (s1a.qualified_tips or s1a.qualified_overtime
                                           or hh.taxpayer_65_or_older):
        add("act", "Married filing separately loses deductions",
            "The tips, overtime and senior deductions are only allowed on a joint return. "
            "Compare a joint estimate before choosing.")
    if ctx.ctc_before_limit > b.child_and_dependent_credit + b.additional_child_tax_credit \
            and inp.credits.child_tax_credit is None and (hh.children_under_17 or 0) > 0:
        add("info", "Part of the child tax credit goes unused",
            f"{_usd(ctx.ctc_before_limit - b.child_and_dependent_credit - b.additional_child_tax_credit)} "
            "more than the income tax and the refundable limit allow.")

    # -- figures that may be wrong -------------------------------------------
    for i, job in enumerate(inp.jobs):
        p = rec.job_breakdown[i]
        if p.projected_taxable_wages > ZERO and p.projected_withholding == ZERO:
            add("review", f"No federal tax withheld on {p.name}",
                "Confirm against the paystub. An exempt W-4 stops all withholding.")
        if job.ytd_federal_tax_withheld is not None and p.periods_elapsed > 0 \
                and job.federal_tax_withheld_per_period > ZERO:
            avg = job.ytd_federal_tax_withheld / p.periods_elapsed
            ratio = avg / job.federal_tax_withheld_per_period
            if ratio < Decimal("0.75") or ratio > Decimal("1.33"):
                add("review", f"Withholding on {p.name} changed this year",
                    f"Year to date averages {_usd(avg)} a paycheck; the latest is "
                    f"{_usd(job.federal_tax_withheld_per_period)}. The projection uses the latest "
                    f"for the rest of the year.")
    if status == "married_jointly" and len(inp.jobs) == 1 and oi.spouse_taxable_wages == ZERO:
        add("review", "One paycheck on a joint return",
            "If the spouse works, add their paystub as a second job. Their wages change the bracket.")
    if b.capital_loss_carryover > ZERO:
        add("info", "Capital loss carries forward",
            f"Only {_usd(t.capital_loss_limit(status))} of the net loss counts this year; "
            f"{_usd(b.capital_loss_carryover)} carries to next year.")
    if ctx.qbi_over_threshold:
        add("review", "Business income above the QBI threshold",
            "The wage and service-business limits of Form 8995-A are not modelled, so the QBI "
            "deduction may be too large and the tax too low.")
    if oi.self_employment_net > ZERO and t.qbi_minimum[0] > ZERO and b.qbi_deduction == t.qbi_minimum[0]:
        add("review", "QBI minimum deduction applied",
            f"The {_usd(t.qbi_minimum[0])} minimum needs active participation in the business.")
    if b.itemized_computed is not None and b.deduction_kind == "standard" and \
            b.standard_computed - b.itemized_computed < THOUSAND:
        add("info", "Itemizing is close",
            f"Schedule A comes to {_usd(b.itemized_computed)} against a standard deduction of "
            f"{_usd(b.standard_computed)}. A little more deductible spending would tip it.")
    if inp.deductions.itemized_total is not None:
        add("review", "Itemized total taken as given",
            "The SALT cap and the medical and charity floors were not checked against it. "
            "Enter the parts instead to have them applied.")
    if b.earned_income_credit > ZERO:
        add("review", "Earned income credit included",
            f"{_usd(b.earned_income_credit)}, assuming everyone meets the residency, SSN and age rules. "
            "It is a large figure to get wrong; confirm eligibility.")
    if s1a.qualified_tips or s1a.qualified_overtime:
        add("review", "Tips and overtime taken as qualifying",
            "Only tips in a listed occupation and only the overtime premium (the half in "
            "time-and-a-half) qualify. The estimator cannot test that.")
    if rec.additional_medicare_withheld > ZERO or rec.excess_social_security_credit > ZERO:
        parts = []
        if rec.additional_medicare_withheld > ZERO:
            parts.append(f"{_usd(rec.additional_medicare_withheld)} of Additional Medicare Tax the employer withholds")
        if rec.excess_social_security_credit > ZERO:
            parts.append(f"{_usd(rec.excess_social_security_credit)} of Social Security withheld twice by two employers")
        add("info", "Counted payments the paystub's federal line leaves out", "; ".join(parts) + ".")
    if b.additional_medicare_tax > rec.additional_medicare_withheld + Decimal("100") and status == "married_jointly":
        add("info", "Additional Medicare Tax is under-withheld",
            f"Employers withhold it only above $200,000 per job, so about "
            f"{_usd(b.additional_medicare_tax - rec.additional_medicare_withheld)} of it is owed at filing.")

    # -- what this estimator does not cover ------------------------------------
    add("info", "Federal only",
        "State and city income tax, the alternative minimum tax, education and dependent-care "
        "credits are not computed. Enter credits you know in the credit boxes.")
    return out


def _headline(ctx: _Context, b: TaxBreakdown, rec: WithholdingRecommendation) -> str:
    bal = rec.projected_balance
    year = ctx.tables.tax_year
    if bal >= ZERO:
        line = f"On track for {year}: about {_usd(bal)} refund."
    else:
        line = f"Short for {year}: about {_usd(-bal)} due at filing."
        if rec.periods_remaining > 0 and rec.additional_withholding_per_period > ZERO:
            line += (f" Add {_usd(rec.additional_withholding_per_period)} per paycheck on "
                     f"{rec.adjusted_job_name} (W-4 line 4(c)) to break even.")
    if rec.penalty_risk:
        line += " An underpayment penalty is likely as things stand."
    return line
