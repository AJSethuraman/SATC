"""The W-4 line 4c figure — the one number a client actually acts on.

The eighth of nine parts of the withholding engine checked against a source
outside our own code, and the one that matters most on the day: everything else
in the estimate is context, and **this is the number somebody writes on a form
and hands to their employer.**

**Step 4(c)** is the box on Form W-4 headed *"Extra withholding"* — an amount the
employer takes out of every remaining paycheck on top of what the tables say.

THE AUTHORITY. IRS Publication 505, *How Do You Increase Your Withholding?*:

    "You can request that an additional amount be withheld from each paycheck by
     entering the additional amount in Step 4(c) of Form W-4."

and, on working the figure out:

    "determine the extra amount that you want to apply to that job and divide
     that amount by the number of paydays remaining"

**And the publication does the arithmetic itself**, which is the strongest kind
of source — a spouse with 49 pay periods remaining and a $4,459 shortfall enters
*"$91 ($4,459 ÷ 49 remaining paydays) on their Form W-4 in Step 4(c)."*

TWO CHECKS, AND THE SECOND IS THE ONE THAT MATTERS.

The first is that the engine performs that division. The second is a **closed
loop**: take the number the engine recommends, feed it back in as the new
per-paycheck withholding, and see whether the client actually lands where the
recommendation said they would. A figure that is arithmetically defensible and
does not land is worse than one that is obviously wrong, because nobody finds
out until April.

It lands to within the rounding — the recommendation is stated in whole cents, so
up to half a cent per paycheck is unrecoverable, and across eight paychecks that
is four cents. The test asserts that bound rather than exact zero, because
asserting zero would either fail or force a rounding mode nobody wants.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest

from satc.withholding.engine import estimate
from satc.withholding.models import EstimatorInput

# ── IRS Pub 505's own worked example ──────────────────────────────────────────
EG_SHORTFALL = Decimal("4459")
EG_PAYDAYS = 49
EG_PER_PAYDAY = Decimal("91")     # "$91 ($4,459 ÷ 49 remaining paydays)"

#: The recommendation is stated in cents, so each paycheck can be off by up to
#: half of one. Anything inside this is rounding; anything outside is a defect.
def _rounding_room(periods):
    return Decimal("0.005") * periods


def _run(*, withheld_per_period=395, periods_remaining=8, target_refund=0,
         ytd_wh=7110, ytd_wages=65000, frequency="biweekly", **extra):
    stub = {"pay_frequency": frequency, "gross_pay_per_period": 3800,
            "federal_tax_withheld_per_period": withheld_per_period,
            "pay_periods_remaining": periods_remaining,
            "ytd_taxable_wages": ytd_wages, "ytd_federal_tax_withheld": ytd_wh,
            "adjust_withholding": True}
    data = {"filing_status": "single", "tax_year": 2025, "paystub": stub,
            "target_refund": target_refund}
    data.update(extra)
    return estimate(EstimatorInput.from_dict(data))


# ── the IRS's own arithmetic ──────────────────────────────────────────────────

def test_the_publication_example_divides_cleanly():
    """Reproduced from the literals, so the figures above are checked rather
    than taken on trust. $4,459 over 49 paydays is exactly $91."""
    assert (EG_SHORTFALL / EG_PAYDAYS).quantize(Decimal("1")) == EG_PER_PAYDAY
    assert EG_PER_PAYDAY * EG_PAYDAYS == EG_SHORTFALL


def test_the_engine_divides_the_shortfall_by_the_paydays_remaining():
    """Pub 505's method, applied to a real estimate rather than a worked
    example: what is still owed, spread over the paychecks that are left."""
    r = _run()
    w = r.recommendation
    shortfall = r.breakdown.total_tax_liability - w.ytd_withholding
    assert w.periods_remaining == 8
    assert w.recommended_withholding_per_period == (
        shortfall / w.periods_remaining).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def test_line_4c_is_the_extra_on_top_of_what_is_already_withheld():
    """Step 4(c) is EXTRA withholding — not the new total. Confusing the two
    would tell a client to add their whole withholding again."""
    r = _run(withheld_per_period=395)
    w = r.recommendation
    assert w.additional_withholding_per_period == (
        w.recommended_withholding_per_period - Decimal("395"))


# ── the closed loop: does the number actually land? ───────────────────────────

@pytest.mark.parametrize("periods,withheld", [(8, 395), (13, 300), (4, 500), (26, 250)])
def test_taking_the_advice_lands_the_client_where_it_said(periods, withheld):
    """THE CHECK THAT MATTERS. A figure that is arithmetically defensible and
    does not land is worse than one that is obviously wrong, because nobody
    finds out until April."""
    first = _run(periods_remaining=periods, withheld_per_period=withheld)
    advised = first.recommendation.recommended_withholding_per_period

    after = _run(periods_remaining=periods,
                 withheld_per_period=float(advised))
    assert abs(after.recommendation.projected_balance) <= _rounding_room(periods), (
        f"following the advice left a balance of "
        f"{after.recommendation.projected_balance}")


def test_it_lands_on_a_target_refund_rather_than_on_zero():
    """A client who wants to be $500 ahead at filing should end up $500 ahead,
    not at zero — the target is part of what the recommendation solves for."""
    target = 500
    first = _run(target_refund=target)
    advised = first.recommendation.recommended_withholding_per_period

    after = _run(target_refund=target, withheld_per_period=float(advised))
    assert abs(after.recommendation.projected_balance - Decimal(target)) <= _rounding_room(8)


def test_a_bigger_target_asks_for_more_per_paycheck():
    """The control on the direction. A target that does not move the figure is
    a target being ignored."""
    none = _run(target_refund=0).recommendation.additional_withholding_per_period
    some = _run(target_refund=1000).recommendation.additional_withholding_per_period
    assert some > none


# ── what the figure has to account for ────────────────────────────────────────

def test_money_already_paid_reduces_what_is_asked_for():
    """Year-to-date withholding is already in the client's account. Ignoring it
    would ask them to pay their whole liability again over the remaining weeks."""
    less_paid = _run(ytd_wh=2000).recommendation.additional_withholding_per_period
    more_paid = _run(ytd_wh=9000).recommendation.additional_withholding_per_period
    assert more_paid < less_paid


def test_estimated_tax_payments_count_the_same_as_withholding():
    """Somebody who has been paying quarterly has already covered part of it."""
    without = _run().recommendation.additional_withholding_per_period
    with_payments = _run(other_payments={"estimated_tax_payments": 3000}
                         ).recommendation.additional_withholding_per_period
    assert with_payments < without


def test_fewer_paydays_left_means_more_per_payday():
    """THE SAME shortfall over four paychecks instead of thirteen.

    THE FIRST DRAFT OF THIS TEST WAS WRONG AND THE ENGINE WAS RIGHT. It varied
    `pay_periods_remaining` alone and expected the per-payday figure to rise —
    but paydays remaining also decides how much income is still to come, so the
    thirteen-payday case was a client earning $49,400 more and owing more tax.
    Two different people, not one person at two moments.

    Holding the annual picture still is what makes it one person: year-to-date
    wages are moved so both cases project the same $114,400 of income, and the
    same amount is already withheld. Then the only thing that differs is how
    many paychecks are left to spread the shortfall over.
    """
    per_period_wages = 3800
    annual = 65000 + 13 * per_period_wages          # 114,400 either way

    late = _run(periods_remaining=4,
                ytd_wages=annual - 4 * per_period_wages,
                ).recommendation.recommended_withholding_per_period
    early = _run(periods_remaining=13,
                 ytd_wages=annual - 13 * per_period_wages,
                 ).recommendation.recommended_withholding_per_period
    assert late > early, "the same shortfall over fewer paydays asked for less each time"


# ── the denominator and the edges ─────────────────────────────────────────────

def test_a_client_already_ahead_is_not_told_to_withhold_more():
    """Over-withheld, and the figure must not go negative on a form that has no
    way to express a negative."""
    r = _run(ytd_wh=30000)
    assert r.recommendation.additional_withholding_per_period == 0
    assert r.recommendation.is_over_withholding


def test_no_paydays_left_asks_for_nothing_rather_than_dividing_by_zero():
    """The last paycheck has gone. There is nowhere left to put it, and the
    honest answer is zero rather than a crash or an infinity."""
    r = _run(periods_remaining=0)
    assert r.recommendation.periods_remaining == 0
    assert r.recommendation.recommended_withholding_per_period == 0


def test_the_shortfall_in_the_base_case_is_real():
    """The denominator. Every test above is vacuous if this client already had
    enough withheld."""
    r = _run()
    assert r.recommendation.projected_balance < 0, "no shortfall — nothing to recommend"
    assert r.recommendation.additional_withholding_per_period > 0
