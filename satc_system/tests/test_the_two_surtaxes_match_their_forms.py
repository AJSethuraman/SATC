"""The two surtaxes, tied to Form 8959 and Form 8960.

Parts six and seven of nine. They pair because they share a shape — a rate
applied to income above a threshold — and a trap: **the thresholds look the same
and are not the same thing.** Both are $200,000 for a single filer, but Form 8959
measures WAGES AND SELF-EMPLOYMENT INCOME against it, and Form 8960 measures
MODIFIED ADJUSTED GROSS INCOME. A client with $190,000 of wages and $50,000 of
interest is over one and under the other.

**FORM 8959 — Additional Medicare Tax, 0.9%.** The structure that matters is
that the threshold is consumed by wages FIRST and self-employment income uses
what is left:

    Part I    line 4  Medicare wages
              line 5  the threshold
              line 6  subtract 5 from 4, "if zero or less, enter -0-"
              line 7  multiply by 0.9%
    Part II   line 8  self-employment income from Schedule SE line 6
              line 10 the threshold again
              line 11 wages from line 4
              line 12 subtract 11 from 10, "if zero or less, enter -0-"
              line 13 subtract 12 from 8, "if zero or less, enter -0-"
              line 14 multiply by 0.9%

The engine adds wages and SE income and subtracts the threshold once. That is
arithmetically the same thing, and `_by_form_8959` below walks the form's own
lines instead so the two are genuinely different routes.

**FORM 8960 — Net Investment Income Tax, 3.8%.** The 3.8% applies to the
**lesser** of net investment income or the amount of MAGI over the threshold —
so it is capped twice, and a test that only ever exercises one of the two caps
proves half the rule.

WHAT THIS FOUND. The arithmetic of both is right, in both directions of the
lesser-of. **What is not right is the SCOPE of net investment income**, and it
runs both ways: Form 8960 Part I also counts rents, royalties, annuities and
passive business income — none of which this estimator has a field for, so a
landlord is understated — and Part II allows deductions against that income,
none of which are modelled, so somebody with investment interest expense is
overstated. That is now printed with the estimate rather than left in a
docstring, because a preparer cannot act on a comment in a file they never open.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest

from satc.withholding.engine import estimate
from satc.withholding.models import EstimatorInput
from satc.withholding.tax_data import load_tax_tables

# ── the statutes, as literals ─────────────────────────────────────────────────
ADDL_MEDICARE_RATE = Decimal("0.009")        # IRC 3101(b)(2)
NIIT_RATE = Decimal("0.038")                 # IRC 1411(a)
THRESHOLDS = {                               # both are statutory, NOT indexed
    "single": Decimal("200000"),
    "married_jointly": Decimal("250000"),
    "married_separately": Decimal("125000"),
    "head_of_household": Decimal("200000"),
}
SE_FACTOR = Decimal("0.9235")
SE_FLOOR = Decimal("400")


@pytest.fixture(scope="module")
def tables():
    got, _ = load_tax_tables(2025)
    return got


def _cents(v):
    return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _by_form_8959(wages, se_income, threshold):
    """Form 8959 Parts I and II, walked by their own line numbers."""
    l4 = Decimal(wages)
    l6 = max(l4 - threshold, Decimal(0))
    l7 = l6 * ADDL_MEDICARE_RATE
    l10 = threshold
    l11 = l4
    l12 = max(l10 - l11, Decimal(0))          # threshold left after wages
    l13 = max(Decimal(se_income) - l12, Decimal(0))
    l14 = l13 * ADDL_MEDICARE_RATE
    return _cents(l7 + l14)


def _se_line_6(net_se):
    """Schedule SE line 6, which Form 8959 line 8 reads — floor included."""
    base = Decimal(net_se) * SE_FACTOR
    return Decimal(0) if base < SE_FLOOR else base


def _estimate(wages=0, se=0, interest=0, ltcg=0, status="single"):
    return estimate(EstimatorInput.from_dict({
        "filing_status": status, "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": wages,
                    "pay_periods_remaining": 1, "federal_tax_withheld_per_period": 0},
        "other_income": {"self_employment_net": se, "interest": interest,
                         "long_term_capital_gains": ltcg}}))


# ── the constants ─────────────────────────────────────────────────────────────

def test_the_rates_are_the_statutory_ones(tables):
    assert tables.additional_medicare_rate == ADDL_MEDICARE_RATE
    assert tables.niit_rate == NIIT_RATE


@pytest.mark.parametrize("status,threshold", THRESHOLDS.items())
def test_both_thresholds_are_the_statutory_ones(tables, status, threshold):
    assert tables.additional_medicare_threshold(status) == threshold
    assert tables.niit_threshold(status) == threshold


def test_neither_threshold_is_inflation_indexed(tables):
    """IRC 1411(b) and 3101(b)(2) fix these in statute. If a future crosswalk
    year indexes them, that is a change to the law and not a table refresh —
    this test is where somebody finds out."""
    for year in (2024, 2025):
        got, _ = load_tax_tables(year)
        assert got.niit_threshold("single") == Decimal("200000"), year
        assert got.additional_medicare_threshold("single") == Decimal("200000"), year


def test_the_two_thresholds_are_the_same_number_and_not_the_same_thing():
    """THE TRAP. Both are $200,000 for a single filer, and they measure
    different things — wages against one, total income against the other. A
    client can be over one and under the other, and this proves it."""
    r = _estimate(wages=190000, interest=50000)
    assert r.breakdown.additional_medicare_tax == 0, "wages are under the 8959 threshold"
    assert r.breakdown.net_investment_income_tax > 0, "AGI is over the 8960 threshold"


# ── Form 8959 ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("wages,se", [
    (250000, 0),        # wages alone over the threshold
    (150000, 100000),   # threshold consumed partly by wages, rest by SE
    (0, 300000),        # SE alone
    (190000, 20000),    # only the combination crosses it
    (500000, 0),        # well over
    (100000, 50000),    # nowhere near
])
def test_additional_medicare_matches_form_8959(wages, se):
    got = _estimate(wages=wages, se=se).breakdown.additional_medicare_tax
    assert got == _by_form_8959(wages, _se_line_6(se), THRESHOLDS["single"])


def test_wages_consume_the_threshold_before_self_employment_income():
    """Form 8959 Part II line 12 subtracts the wages from the threshold. The
    engine adds the two and subtracts once — the same answer, and this is the
    case that would expose it if it were not."""
    only_wages = _estimate(wages=200000).breakdown.additional_medicare_tax
    only_se = _estimate(se=Decimal("200000") / SE_FACTOR).breakdown.additional_medicare_tax
    both = _estimate(wages=100000, se=Decimal("100000") / SE_FACTOR).breakdown.additional_medicare_tax
    assert only_wages == 0 and only_se == 0
    assert both == 0, "splitting income across the two parts crossed a threshold it should not"


def test_a_spouse_s_wages_count_toward_the_same_threshold():
    """A joint return measures combined wages against $250,000."""
    r = estimate(EstimatorInput.from_dict({
        "filing_status": "married_jointly", "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": 200000,
                    "pay_periods_remaining": 1},
        "other_income": {"spouse_taxable_wages": 100000}}))
    assert r.breakdown.additional_medicare_tax == _cents(
        (Decimal("300000") - THRESHOLDS["married_jointly"]) * ADDL_MEDICARE_RATE)


# ── Form 8960 ─────────────────────────────────────────────────────────────────

def test_the_tax_is_capped_by_investment_income():
    """One arm of the lesser-of: plenty of income over the threshold, little of
    it investment income."""
    r = _estimate(wages=300000, interest=50000)
    over = r.breakdown.adjusted_gross_income - THRESHOLDS["single"]
    assert over > Decimal("50000"), "wrong precondition — the other arm binds"
    assert r.breakdown.net_investment_income_tax == _cents(Decimal("50000") * NIIT_RATE)


def test_the_tax_is_capped_by_the_amount_over_the_threshold():
    """The other arm: almost all of it is investment income, so the threshold
    does the capping. A suite that only tested the first arm would pass with the
    `min` replaced by either operand."""
    r = _estimate(wages=0, interest=300000)
    over = r.breakdown.adjusted_gross_income - THRESHOLDS["single"]
    assert over < Decimal("300000"), "wrong precondition — the other arm binds"
    assert r.breakdown.net_investment_income_tax == _cents(over * NIIT_RATE)


def test_below_the_threshold_there_is_no_tax_however_much_is_investment_income():
    r = _estimate(wages=0, interest=150000)
    assert r.breakdown.adjusted_gross_income < THRESHOLDS["single"]
    assert r.breakdown.net_investment_income_tax == 0


def test_wages_alone_over_the_threshold_produce_no_niit():
    """The control that catches the commonest way to get this wrong: applying
    3.8% to income over the threshold regardless of what kind it is."""
    r = _estimate(wages=400000)
    assert r.breakdown.adjusted_gross_income > THRESHOLDS["single"]
    assert r.breakdown.net_investment_income_tax == 0


def test_retirement_distributions_are_not_investment_income():
    """IRC 1411(c)(5) excludes distributions from qualified plans. They raise
    AGI — and therefore the amount over the threshold — without being taxable
    under 1411 themselves."""
    r = estimate(EstimatorInput.from_dict({
        "filing_status": "single", "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": 150000,
                    "pay_periods_remaining": 1},
        "other_income": {"taxable_retirement_distributions": 200000}}))
    assert r.breakdown.adjusted_gross_income > THRESHOLDS["single"]
    assert r.breakdown.net_investment_income_tax == 0


# ── what is NOT modelled, declared on the estimate ────────────────────────────

def test_the_estimate_says_what_its_investment_income_leaves_out():
    """Not a docstring. A preparer cannot act on a comment in a file they never
    open, and the omission runs in BOTH directions — so the note has to say
    which client is too high and which is too low."""
    said = " ".join(_estimate(wages=300000, interest=50000).notes)
    assert "Rents, royalties" in said
    assert "too low" in said and "too high" in said
    assert "MAGI" in said


def test_the_note_is_absent_when_the_tax_does_not_apply():
    """A caveat printed on every estimate is a caveat nobody reads."""
    said = " ".join(_estimate(wages=80000).notes)
    assert "Rents, royalties" not in said


# ── the denominator ───────────────────────────────────────────────────────────

def test_no_income_no_surtaxes():
    r = _estimate(wages=50000)
    assert r.breakdown.additional_medicare_tax == 0
    assert r.breakdown.net_investment_income_tax == 0


def test_the_two_rates_are_different_numbers():
    """Without this a suite could pass with both set to the same value."""
    assert ADDL_MEDICARE_RATE != NIIT_RATE
