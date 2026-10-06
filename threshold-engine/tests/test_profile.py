"""The profile: facts only, each checked against a hand calculation."""
import pytest

from conftest import load, quarters
from threshold_engine.profile import percentile, profile


def prof(values, direction="higher_is_worse"):
    return profile(quarters(values), "test", "%", direction, "quarterly", 1)


def test_percentiles_match_excel_percentile_inc():
    # =PERCENTILE.INC({1,2,3,4,10}, 0.9) is 7.6; 0.25 is 2.
    assert percentile([1, 2, 3, 4, 10], 90) == pytest.approx(7.6)
    assert percentile([1, 2, 3, 4, 10], 25) == 2
    assert percentile([5], 50) == 5


def test_spells_are_every_stretch_worse_than_the_median_with_their_timing():
    v = [1, 1, 2, 3, 2, 1, 1, 1, 4, 9, 6, 1, 1]       # median 1
    s = prof(v)["spells_worse_than_median"]
    assert [(x["peak"], x["periods"], x["periods_to_peak"], x["periods_peak_to_end"])
            for x in s] == [(3, 3, 2, 2), (9, 3, 2, 2)]
    assert [x["rank"] for x in s] == [2, 1]
    assert s[1]["peak_over_median"] == 9 and s[1]["peak_minus_median"] == 8


def test_a_spell_cut_by_either_edge_of_the_data_says_so():
    s = prof([3, 2, 1, 1, 1, 1, 4])["spells_worse_than_median"]
    assert s[0]["note"] == "under way at the first observation"
    assert s[-1]["note"] == "still under way at the last observation"
    assert not s[0]["complete"] and not s[-1]["complete"]


def test_exceedance_counts_share_spells_and_years():
    v = [1] * 8 + [5, 5] + [1] * 6 + [5] + [1] * 3     # 20 quarters, 2000-2004
    e = {x["level"]: x for x in prof(v)["exceedance"]}
    # 17 ones and 3 fives: p90 sits at rank 17.1 of 19, among the fives.
    assert e["p90"]["value"] == 5
    assert e["p95"]["share_at_or_worse"] == pytest.approx(3 / 20)
    assert e["p95"]["spells_worse"] == 2
    assert e["p95"]["longest"][2] == 2
    assert e["p95"]["years"] == ["2002", "2004"]


def test_the_largest_spell_is_removed_and_the_percentiles_recomputed():
    v = [1, 1, 2, 1, 1, 8, 9, 1, 1]
    w = prof(v)["without_largest_spell"]
    assert w["removed"][2] == 2 and w["observations"] == 7
    assert w["p100"] == 2


def test_latest_rank_and_when_history_was_last_this_bad():
    v = [1, 3, 1, 1, 2, 2]
    la = prof(v)["latest"]
    assert la["share_of_history_no_worse"] == pytest.approx(5 / 6)
    assert la["run_at_or_worse_since"] == quarters(v)[4].date
    assert la["last_this_bad_before"] == quarters(v)[1].date


def test_lower_is_worse_reads_percentiles_from_the_bad_end():
    # A credit score: p95 is the score only 5% of history was below.
    d = prof([700, 710, 720, 730, 740], "lower_is_worse")["distribution"]
    assert d["p95"] == pytest.approx(702) and d["p5"] == pytest.approx(738)
    assert d["worst"][1] == 700


def test_mortgage_facts_from_public_history():
    pr = profile(load("mortgage_nco_ttm.csv"), "mortgage", "%",
                 "higher_is_worse", "quarterly", 1)
    s = pr["spells_worse_than_median"]
    assert [round(x["peak"], 3) for x in s] == [0.235, 0.242, 2.49]
    assert s[0]["note"] == "under way at the first observation"
    w = pr["without_largest_spell"]
    assert w["removed"] == ("2007-04-01", "2016-10-01", 38)
    assert round(w["p100"], 3) == 0.242


def test_mean_and_sample_standard_deviation_match_excel_stdev_s():
    # =AVERAGE({2,4,4,4,5,5,7,9}) is 5; =STDEV.S(...) is 2.138.
    d = prof([2, 4, 4, 4, 5, 5, 7, 9])["distribution"]
    assert d["mean"] == 5 and d["sd"] == pytest.approx(2.13809, abs=1e-5)
