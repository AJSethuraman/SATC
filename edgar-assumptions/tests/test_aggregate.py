import math

from satc_edgar.aggregate import (
    Tier,
    aggregate_tier,
    assign_tier,
    build_series,
    parse_tiers,
)
from satc_edgar.metrics import extract_annual_financials
from satc_edgar.stats import coefficient_of_variation, percentile
from tests.fixtures import make_companyfacts


def test_percentile_linear():
    xs = [1, 2, 3, 4]
    assert math.isclose(percentile(xs, 50), 2.5)
    assert math.isclose(percentile(xs, 25), 1.75)
    assert percentile([], 50) is None
    assert percentile([7], 90) == 7


def test_cv_undefined_for_zero_mean():
    assert coefficient_of_variation([1, -1]) is None  # mean ~0
    assert coefficient_of_variation([5]) is None  # n<2
    assert coefficient_of_variation([10, 10, 10]) == 0.0


def test_parse_tiers_default():
    tiers = parse_tiers("0-250M,250M-1B,1B-5B,5B+")
    assert [t.label for t in tiers] == ["0-250M", "250M-1B", "1B-5B", "5B+"]
    assert tiers[0].low == 0 and tiers[0].high == 250e6
    assert tiers[-1].high is None


def test_assign_tier_boundaries():
    tiers = parse_tiers("0-250M,250M-1B,1B-5B,5B+")
    assert assign_tier(100e6, tiers).label == "0-250M"
    assert assign_tier(250e6, tiers).label == "250M-1B"  # exclusive low edge
    assert assign_tier(10e9, tiers).label == "5B+"
    assert assign_tier(None, tiers) is None


def _series(cik, revenue, **kw):
    years = [2018, 2019, 2020, 2021, 2022]
    facts = make_companyfacts(cik, f"Co{cik}", years, revenue=revenue, **kw)
    recs = extract_annual_financials(facts, cik, f"Co{cik}", "")
    return build_series(recs, 5)


def test_aggregate_tier_low_confidence_flag():
    tier = Tier("1B-5B", 1e9, 5e9)
    series = [_series(1, 2000.0)]  # 1 company, min_sample 10
    tr = aggregate_tier(series, tier, min_sample=10)
    assert tr.low_confidence is True
    assert tr.n_companies == 1
    # distributions still produced
    assert tr.through_cycle["ebitda_margin"].p50 is not None


def test_through_cycle_volatility_present_with_growth():
    tier = Tier("1B-5B", 1e9, 5e9)
    # Growing revenue -> non-zero CV on size-linked metrics.
    series = [_series(i, 2000.0, growth=1.1) for i in range(1, 12)]
    tr = aggregate_tier(series, tier, min_sample=10)
    assert tr.low_confidence is False
    d = tr.through_cycle["ebitda_to_interest"]
    assert d.median_cv is not None and d.median_cv > 0
    assert d.p10 is not None and d.p90 is not None  # >=5 samples -> extremes


def test_window_filters_years():
    years = list(range(2010, 2023))
    facts = make_companyfacts(9, "Co9", years, revenue=1000.0)
    recs = extract_annual_financials(facts, 9, "Co9", "")
    s = build_series(recs, 3)
    assert [r.fiscal_year for r in s.records] == [2020, 2021, 2022]
