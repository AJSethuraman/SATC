"""Safe harbour, tied to IRS Publication 505 — including its own worked example.

SAFE HARBOUR is the rule that says how much you must pay in during the year to
be safe from an underpayment penalty even if you still owe at filing. It is the
number a client actually acts on: the recommendation says "withhold this much
more per paycheck", and safe harbour is the floor under it.

It was the largest thing in the withholding engine with no outside source. The
6 September tie-out proved the brackets and one computed figure and said so in
its own "what this does not prove" list; the firm's answer to matter 2 was
"build it, safe-harbour tie-out first". This is that.

THE AUTHORITY. IRS Publication 505, *Tax Withholding and Estimated Tax*, under
**Required Annual Payment — Line 12c**:

    General rule. The total amount you must pay is the smaller of:
      1. 90% of your total expected tax for 2026, or
      2. 100% of the total tax shown on your 2025 return...

    Higher income taxpayers. If your AGI for 2025 was more than $150,000
    ($75,000 if your filing status for 2026 is Married filing separately),
    substitute 110% for 100% in (2) above.

AND THE IRS DOES THE ARITHMETIC ITSELF, in the Example immediately below that,
which is the strongest kind of source there is — a published answer, not just a
published rule:

    Your total tax on the 2025 return was $42,581, and the expected tax for 2026
    is $71,253. Your 2025 AGI was $180,000. Because you had more than $150,000
    of AGI in 2025... 90% of the expected tax for 2026 is $64,128... 110% of the
    tax shown on the 2025 return is $46,839... the required annual payment is
    $46,839, the smaller of the two.

Captured from irs.gov on 6 September 2026; the capture is in
`docs/tie-out/withholding-2026-09-06/`.

Every figure below is a LITERAL from that publication, disagreeing with our
crosswalk rather than reading from it — the same shape as
`test_the_2025_tables_are_enacted_law.py`, and for the same reason: a test that
derives from the file under test can only prove the file is self-consistent.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from satc.withholding.engine import estimate
from satc.withholding.models import EstimatorInput
from satc.withholding.tax_data import load_tax_tables

# ── IRS Pub 505, "Required Annual Payment — Line 12c" ─────────────────────────
CURRENT_YEAR_PCT = Decimal("0.90")          # "90% of your total expected tax"
PRIOR_YEAR_PCT = Decimal("1.00")            # "100% of the total tax shown"
PRIOR_YEAR_PCT_HIGH_INCOME = Decimal("1.10")  # "substitute 110% for 100%"
HIGH_INCOME_AGI = Decimal("150000")         # "more than $150,000"
HIGH_INCOME_AGI_MFS = Decimal("75000")      # "($75,000 if ... Married filing separately)"

# ── the Example, verbatim ─────────────────────────────────────────────────────
EG_PRIOR_TAX = Decimal("42581")
EG_PRIOR_AGI = Decimal("180000")
EG_EXPECTED_TAX = Decimal("71253")
EG_NINETY_PCT = Decimal("64128")            # the IRS's own figure, whole dollars
EG_ANSWER = Decimal("46839")                # "the required annual payment is $46,839"


@pytest.fixture(scope="module")
def sh():
    tables, _ = load_tax_tables(2025)
    return tables.safe_harbor()


# ── the rule ──────────────────────────────────────────────────────────────────

def test_the_percentages_are_the_ones_pub_505_states(sh):
    assert Decimal(str(sh["current_year_pct"])) == CURRENT_YEAR_PCT
    assert Decimal(str(sh["prior_year_pct"])) == PRIOR_YEAR_PCT
    assert Decimal(str(sh["prior_year_pct_high_income"])) == PRIOR_YEAR_PCT_HIGH_INCOME


def test_the_high_income_thresholds_are_the_ones_pub_505_states(sh):
    """$150,000, and half of it for married filing separately."""
    assert Decimal(str(sh["high_income_agi_threshold"])) == HIGH_INCOME_AGI
    assert Decimal(str(sh["high_income_agi_threshold_mfs"])) == HIGH_INCOME_AGI_MFS


# ── the IRS's own worked example, run through our engine ──────────────────────

def _estimate(wages, *, status="single", prior_tax=None, prior_agi=None):
    data = {"filing_status": status, "tax_year": 2025,
            "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": wages,
                        "pay_periods_remaining": 1, "federal_tax_withheld_per_period": 0}}
    if prior_tax is not None:
        data["prior_year_tax"] = prior_tax
    if prior_agi is not None:
        data["prior_year_agi"] = prior_agi
    return estimate(EstimatorInput.from_dict(data))


def test_the_worked_example_lands_on_the_irs_published_answer():
    """THE TIE-OUT. Pub 505 publishes the answer; this must reach it.

    Wages are chosen so the engine's own current-year liability makes 90% of it
    LARGER than the 110% figure — which is the shape of the IRS's example, where
    $64,128 loses to $46,839. What is being proved is that the engine picks the
    smaller, and that its 110% arithmetic matches theirs.

    THE ONE DIFFERENCE, STATED RATHER THAN ROUNDED AWAY: the engine returns
    $46,839.10 and Pub 505 prints $46,839. 110% x 42,581 is exactly 46,839.10;
    the IRS rounded to whole dollars in its prose, as its worksheets do. Same
    number, two renderings — not a discrepancy, and it is written down here
    rather than hidden behind a `round()`.
    """
    r = _estimate(250000, prior_tax=EG_PRIOR_TAX, prior_agi=EG_PRIOR_AGI)
    target = r.recommendation.safe_harbor_target

    assert target == EG_PRIOR_TAX * PRIOR_YEAR_PCT_HIGH_INCOME == Decimal("46839.10")
    assert target.quantize(Decimal("1")) == EG_ANSWER
    # and the 90% road really was the loser, as it is in the example
    assert r.breakdown.total_tax_liability * CURRENT_YEAR_PCT > target


def test_the_irs_example_arithmetic_is_reproduced_independently():
    """The two roads of the example, computed here from the literals rather than
    from anything of ours — so the numbers above are checked, not assumed."""
    assert (EG_EXPECTED_TAX * CURRENT_YEAR_PCT).quantize(Decimal("1")) == EG_NINETY_PCT
    assert (EG_PRIOR_TAX * PRIOR_YEAR_PCT_HIGH_INCOME).quantize(Decimal("1")) == EG_ANSWER
    assert EG_ANSWER < EG_NINETY_PCT, "the example's answer is the smaller of the two"


# ── the branch that the threshold controls ────────────────────────────────────

def test_below_the_threshold_it_is_100_percent_not_110():
    """The control, and the one a preparer would notice: $10,000 of prior-year
    AGI either side of $150,000 changes what the client must pay in."""
    r = _estimate(250000, prior_tax=EG_PRIOR_TAX, prior_agi=Decimal("140000"))
    assert r.recommendation.safe_harbor_target == EG_PRIOR_TAX * PRIOR_YEAR_PCT


def test_the_threshold_is_more_than_not_at_least():
    """Pub 505 says "more than $150,000". Exactly $150,000 is NOT high income,
    and an off-by-one here silently charges somebody an extra 10%."""
    at = _estimate(250000, prior_tax=EG_PRIOR_TAX, prior_agi=HIGH_INCOME_AGI)
    over = _estimate(250000, prior_tax=EG_PRIOR_TAX, prior_agi=HIGH_INCOME_AGI + 1)
    assert at.recommendation.safe_harbor_target == EG_PRIOR_TAX * PRIOR_YEAR_PCT
    assert over.recommendation.safe_harbor_target == EG_PRIOR_TAX * PRIOR_YEAR_PCT_HIGH_INCOME


def test_married_filing_separately_uses_the_halved_threshold():
    """$75,000, not $150,000 — the figure Pub 505 puts in brackets and the one
    most easily missed."""
    under = _estimate(250000, status="married_separately",
                      prior_tax=EG_PRIOR_TAX, prior_agi=Decimal("70000"))
    over = _estimate(250000, status="married_separately",
                     prior_tax=EG_PRIOR_TAX, prior_agi=HIGH_INCOME_AGI_MFS + 1)
    assert under.recommendation.safe_harbor_target == EG_PRIOR_TAX * PRIOR_YEAR_PCT
    assert over.recommendation.safe_harbor_target == EG_PRIOR_TAX * PRIOR_YEAR_PCT_HIGH_INCOME


def test_the_90_percent_road_wins_when_it_is_smaller():
    """The other half of "the smaller of". A big prior-year tax and a small
    current year must fall back to 90% of this year's."""
    r = _estimate(60000, prior_tax=Decimal("90000"), prior_agi=Decimal("100000"))
    expected = r.breakdown.total_tax_liability * CURRENT_YEAR_PCT
    assert r.recommendation.safe_harbor_target == expected
    assert expected < Decimal("90000") * PRIOR_YEAR_PCT


# ── the denominator ───────────────────────────────────────────────────────────

def test_no_prior_year_tax_means_no_safe_harbour_at_all():
    """Not zero — ABSENT. A client who has not told us last year's tax has no
    prior-year road available, and inventing one at 0 would say they are already
    safe having paid nothing."""
    r = _estimate(250000)
    assert r.recommendation.safe_harbor_target is None
    assert r.recommendation.safe_harbor_additional_per_period is None


def test_the_two_roads_actually_differ_in_the_example_case():
    """Without this the picking test could pass on a coincidence."""
    r = _estimate(250000, prior_tax=EG_PRIOR_TAX, prior_agi=EG_PRIOR_AGI)
    ninety = r.breakdown.total_tax_liability * CURRENT_YEAR_PCT
    hundred_ten = EG_PRIOR_TAX * PRIOR_YEAR_PCT_HIGH_INCOME
    assert ninety != hundred_ten
