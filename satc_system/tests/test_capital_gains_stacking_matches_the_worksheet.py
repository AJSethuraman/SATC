"""Capital gains stacked on ordinary income, tied to the IRS worksheet.

The fifth of nine parts of the withholding engine checked against a source
outside our own code.

**STACKING** is the thing this tests. Long-term capital gains and qualified
dividends are taxed at 0%, 15% or 20% — but which band they fall in depends on
how much ORDINARY income sits underneath them. A client with $20,000 of wages
and $40,000 of gain pays **nothing** on it; the same $40,000 on $400,000 of wages
costs $6,000, and on $600,000 of wages it costs $8,000. Getting the order wrong
is not a rounding error, it is a different answer.

THE AUTHORITIES, and both are needed:

* **Rev. Proc. 2024-40 §2.03** — the breakpoints. *"the maximum zero rate amounts
  and maximum 15 percent rate amounts under § 1(j)(5)(B)"*: for All Other
  Individuals, **$48,350** and **$533,400**.
* **The Qualified Dividends and Capital Gain Tax Worksheet** in the Form 1040
  instructions — the METHOD. `_by_the_worksheet` below is that worksheet, written
  out by its own line numbers, and it is what the engine is compared against.

The engine does not implement the worksheet's twenty-five lines; it computes the
same thing directly, in seven. That is a reasonable thing to do and it is exactly
why this test exists: two routes to one number, and nothing until now compared
them.

WHAT THIS FOUND. The stacking is right — seven cases spanning all three bands
agree to the cent. **The RATES were bare literals in `engine.py`**: `0.15` and
`0.20`, the only tax constants in the estimator carrying no citation and no date,
in a file whose whole discipline is that a reader can check every figure against
the law. The thresholds beside them were cited; the rates had quietly opted out.
They now live in the dated table like everything else.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest

from satc.withholding.engine import estimate
from satc.withholding.models import EstimatorInput
from satc.withholding.tax_data import load_tax_tables

# ── Rev. Proc. 2024-40 §2.03, as literals ─────────────────────────────────────
BREAKPOINTS = {                      # (maximum zero rate, maximum 15 percent rate)
    "single": (Decimal("48350"), Decimal("533400")),          # "All Other Individuals"
    "married_jointly": (Decimal("96700"), Decimal("600050")),
    "married_separately": (Decimal("48350"), Decimal("300000")),
    "head_of_household": (Decimal("64750"), Decimal("566700")),
}
RATE_0 = Decimal("0.00")             # IRC 1(h)(1)(B)
RATE_15 = Decimal("0.15")            # IRC 1(h)(1)(C)
RATE_20 = Decimal("0.20")            # IRC 1(h)(1)(D)


@pytest.fixture(scope="module")
def tables():
    got, _ = load_tax_tables(2025)
    return got


def _cents(v):
    """Half UP — the tax convention, and what the engine uses. A previous
    tie-out lost two tests to Python's default banker's rounding on a half-cent."""
    return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _by_the_worksheet(taxable_income, preferential, status="single"):
    """The Qualified Dividends and Capital Gain Tax Worksheet, by its own lines.

    Written out longhand rather than simplified, because the point is to be a
    DIFFERENT route to the number than the engine takes. Simplifying it into the
    engine's seven lines would make this a copy of the thing it is checking.
    """
    thr0, thr15 = BREAKPOINTS[status]
    l1 = Decimal(taxable_income)                 # taxable income
    l4 = Decimal(preferential)                   # qualified dividends + net LTCG
    l5 = max(l1 - l4, Decimal(0))                # ordinary taxable income
    l7 = min(l1, thr0)
    l8 = min(l5, l7)
    l9 = l7 - l8                                 # taxed at 0%
    l10 = min(l1, l4)
    l12 = l10 - l9
    l14 = min(l1, thr15)
    l15 = l5 + l9
    l16 = max(l14 - l15, Decimal(0))
    l17 = min(l12, l16)                          # taxed at 15%
    l21 = l12 - l17                              # taxed at 20%
    return _cents(l9 * RATE_0 + l17 * RATE_15 + l21 * RATE_20)


def _estimate(wages, ltcg, status="single", qualified_dividends=0):
    return estimate(EstimatorInput.from_dict({
        "filing_status": status, "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": wages,
                    "pay_periods_remaining": 1, "federal_tax_withheld_per_period": 0},
        "other_income": {"long_term_capital_gains": ltcg,
                         "qualified_dividends": qualified_dividends,
                         "ordinary_dividends": qualified_dividends}}))


# ── the constants ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("status,expected", BREAKPOINTS.items())
def test_the_breakpoints_are_the_ones_the_revenue_procedure_prints(tables, status, expected):
    assert tables.capital_gains_thresholds(status) == expected


def test_the_rates_are_read_from_the_dated_table_not_hardcoded(tables):
    """THE FINDING. `0.15` and `0.20` were literals in `engine.py` — the only
    tax constants in the estimator with no citation and no date on them."""
    assert tables.capital_gains_rates() == (RATE_0, RATE_15, RATE_20)


def test_the_rates_carry_citations():
    """A constant in this file without a citation is the thing this file exists
    to prevent."""
    import pathlib

    import yaml

    root = pathlib.Path(__file__).resolve().parents[1]
    doc = yaml.safe_load((root / "configs" / "crosswalk" / "federal" / "2025.yaml")
                         .read_text(encoding="utf-8"))
    for key in ("ltcg_rate_0", "ltcg_rate_15", "ltcg_rate_20"):
        entry = doc["parameters"][key]
        assert entry.get("citation"), f"{key} carries no citation"
        assert "1(h)" in entry["citation"], f"{key} does not cite the rate statute"


# ── the stacking, against the worksheet ───────────────────────────────────────

@pytest.mark.parametrize("wages,ltcg", [
    (35000, 40000),      # part of the gain fills the 0% band
    (20000, 10000),      # entirely inside the 0% band
    (100000, 100000),    # entirely at 15%
    (0, 60000),          # gain with no ordinary income under it at all
    (400000, 300000),    # spans 15% and 20%
    (600000, 200000),    # entirely at 20%
    (30000, 5000),       # small gain, low income
    (36000, 600000),     # LOW ordinary income and a gain spanning all three bands
])
def test_the_engine_and_the_worksheet_agree(wages, ltcg):
    r = _estimate(wages, ltcg)
    assert r.breakdown.capital_gains_tax == _by_the_worksheet(
        r.breakdown.taxable_income, ltcg)


def test_a_big_gain_in_a_low_income_year_still_starts_its_15_percent_band_at_the_breakpoint():
    """A MUTANT SURVIVED AND THIS IS WHY IT DOES NOT ANY MORE.

    `fifteen_start = max(ordinary_ti, zero_top)`. Replacing it with plain
    `ordinary_ti` left all twenty-three tests passing, because the difference
    only shows when BOTH of two things are true at once and none of the original
    seven cases had both:

      * ordinary taxable income is BELOW the 0% breakpoint, and
      * the gain is large enough to run past the 15% breakpoint into 20%.

    That is a real client — somebody who sells a rental or a business in a year
    with little wage income. The 0% band they use up still occupies room under
    the 15% breakpoint; forgetting that hands them $485,050 of 15% band where
    they are entitled to less, and the answer moves by $1,405.00.

    The mutation is the finding, not the fix: the guard was right the whole time
    and the tests were too weak to say so.
    """
    r = _estimate(36000, 600000)
    ordinary_ti = r.breakdown.taxable_income - Decimal("600000")
    thr0, thr15 = BREAKPOINTS["single"]
    assert ordinary_ti < thr0, "wrong precondition — ordinary income is above the 0% top"
    assert r.breakdown.taxable_income > thr15, "wrong precondition — never reaches 20%"

    assert r.breakdown.capital_gains_tax == _by_the_worksheet(
        r.breakdown.taxable_income, 600000)
    # Worked by hand: ordinary TI 20,250 (36,000 less the 15,750 deduction), so
    # 28,100 of the gain sits in the 0% band; 485,050 at 15% = 72,757.50; the
    # last 86,850 at 20% = 17,370.00.
    assert r.breakdown.capital_gains_tax == Decimal("90127.50")


def test_the_same_gain_is_taxed_differently_depending_on_what_is_under_it():
    """THE WHOLE POINT OF STACKING, asserted as behaviour.

    $40,000 of gain on $20,000 of wages is mostly free; the same $40,000 on
    $400,000 of wages is taxed at 20%. A test suite that only ever checked one
    income level would not notice the order being wrong.
    """
    low = _estimate(20000, 40000).breakdown.capital_gains_tax
    middle = _estimate(400000, 40000).breakdown.capital_gains_tax
    high = _estimate(600000, 40000).breakdown.capital_gains_tax

    assert low < middle < high
    assert low == Decimal("0.00"), "the 0% band did not absorb a gain that fits in it"
    assert middle == _cents(Decimal("40000") * RATE_15)
    assert high == _cents(Decimal("40000") * RATE_20)

    # WHY THE MIDDLE CASE IS HERE. The first draft of this test asserted that
    # $40,000 of gain on $400,000 of wages was taxed at 20%, and the engine said
    # 15%. The engine was right: the 15% band runs to $533,400 of TAXABLE INCOME,
    # and 400,000 + 40,000 is nowhere near it. My expectation was the thing that
    # was wrong -- while the worksheet comparison beside it passed, which is the
    # argument for having a second route to the number rather than a hand-typed
    # figure.


def test_the_zero_band_is_measured_from_ordinary_income_not_from_zero():
    """The commonest way to get this wrong: applying the $48,350 to the GAIN
    rather than to ordinary income plus the gain."""
    r = _estimate(40000, 40000)
    # ordinary TI is 40,000 - 15,750 = 24,250, so only 24,100 of room remains
    ordinary_ti = r.breakdown.taxable_income - Decimal("40000")
    room = BREAKPOINTS["single"][0] - ordinary_ti
    assert room == Decimal("24100")
    taxed_at_15 = Decimal("40000") - room
    assert r.breakdown.capital_gains_tax == _cents(taxed_at_15 * RATE_15)


def test_qualified_dividends_stack_the_same_way_as_gains():
    """They are the same band on the worksheet — line 4 adds them together."""
    as_gain = _estimate(60000, 20000).breakdown.capital_gains_tax
    as_dividends = _estimate(60000, 0, qualified_dividends=20000).breakdown.capital_gains_tax
    assert as_gain == as_dividends


@pytest.mark.parametrize("status", sorted(BREAKPOINTS))
def test_every_filing_status_stacks_against_its_own_breakpoints(status):
    r = _estimate(80000, 80000, status=status)
    assert r.breakdown.capital_gains_tax == _by_the_worksheet(
        r.breakdown.taxable_income, 80000, status=status)


# ── the denominator and the controls ──────────────────────────────────────────

def test_no_preferential_income_means_no_preferential_tax():
    assert _estimate(80000, 0).breakdown.capital_gains_tax == 0


def test_the_worksheet_and_the_engine_are_not_the_same_code():
    """The denominator for every comparison above.

    If `_by_the_worksheet` ever became a call into the engine, every test here
    would pass while proving nothing. It is longhand on purpose — twenty-five
    lines' worth of the IRS's method against the engine's seven.
    """
    import inspect

    source = inspect.getsource(_by_the_worksheet)
    assert "estimate(" not in source
    assert "tables" not in source
    assert "l9" in source and "l17" in source, "the worksheet lines are gone"


def test_the_three_bands_are_genuinely_different_rates():
    """Without this, a suite could pass with all three set to the same number."""
    assert RATE_0 < RATE_15 < RATE_20
