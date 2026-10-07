"""Backtest: real-time thresholds, scored against what came next."""
import statistics

import pytest

from conftest import load, quarters
from threshold_engine.backtest import backtest, spearman, weighted_percentile
from threshold_engine.evidence import weighted_median


def bt(values, **kw):
    return backtest(quarters(values), "t", "%", kw.get("direction", "higher_is_worse"),
                    "quarterly", 1, kw.get("pct", (50, 75)), kw.get("horizon", 1),
                    kw.get("min_history", 4), kw.get("floor", False),
                    kw.get("half_lives", ()))


def test_spearman_by_hand():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1)
    # Ties share the average rank: x ranks 1, 2.5, 2.5, 4 against y ranks
    # 1, 3, 2, 4 gives 4.5 / sqrt(4.5 x 5) = 0.9487.
    assert spearman([1, 2, 2, 3], [1, 3, 2, 4]) == pytest.approx(0.9486833)
    assert spearman([1, 1, 1], [1, 2, 3]) is None


def test_weighted_percentile_agrees_with_the_weighted_median():
    for v, w in (([5, 1, 3, 2], [1, 1, 1, 1]), ([1, 2, 3], [1, 1, 2]), ([4, 9, 1], [3, 1, 1])):
        assert weighted_percentile(v, w, 50) == weighted_median(v, w)
    assert weighted_percentile([1, 2, 3, 4], [1] * 4, 50) == statistics.median([1, 2, 3, 4])
    assert weighted_percentile([1, 2, 3, 4], [1] * 4, 100) == 4


def test_every_period_is_scored_only_on_its_past():
    base = [1, 2, 1, 3, 2, 4, 1, 5, 2, 3, 1, 2]
    changed = base[:8] + [9, 9, 9, 9]
    a = bt(base)["runs"][0]["periods"]
    b = bt(changed)["runs"][0]["periods"]
    # Periods up to index 7 were scored before the change and must not move;
    # the first period to see a changed value (index 8) must.
    upto = [x for x in a if x["date"] <= quarters(base)[7].date]
    assert upto == b[:len(upto)]
    assert a[len(upto)]["bounds"] != b[len(upto)]["bounds"]


def test_the_number_of_periods_tested():
    r = bt(list(range(1, 21)), min_history=5, horizon=3)
    assert r["runs"][0]["periods_tested"] == 20 - 5 - 3 + 1


def test_a_persistent_series_scores_high_before_high_levels():
    # Blocks of three: a high quarter is usually followed by another.
    # The last quarter of each block turns, so the link is positive, not perfect.
    r = bt([1, 1, 1, 5, 5, 5] * 4, min_history=6, horizon=1)["runs"][0]
    assert r["score_vs_level_ahead"] == pytest.approx(1 / 3)
    two, three = r["by_score"][1], r["by_score"][2]
    assert three["mean_level_ahead"] > two["mean_level_ahead"]


def test_mean_change_by_score_by_hand():
    # min_history 2, horizon 1, one cut at the 50th percentile.
    # i=1: history [1,3], median 2, value 3 -> score 2; next 2, change -1.
    # i=2: history [1,3,2], median 2, value 2 -> score 2 (on the line); next 5, change +3.
    # i=3: history [1,3,2,5], median 2.5, value 5 -> score 2; next 1, change -4.
    r = backtest(quarters([1, 3, 2, 5, 1]), "t", "%", "higher_is_worse", "quarterly", 1,
                 (50,), 1, 2, False)
    s2 = r["runs"][0]["by_score"][1]
    assert s2["periods"] == 3 and s2["mean_change_ahead"] == pytest.approx(-2 / 3)
    assert r["runs"][0]["by_score"][0]["periods"] == 0


def test_lower_is_worse_mirrors():
    v = [1, 3, 2, 5, 1, 4, 2, 6, 3, 2, 5, 1]
    up, down = bt(v), bt([-x for x in v], direction="lower_is_worse")
    assert down["runs"][0]["score_vs_level_ahead"] == pytest.approx(up["runs"][0]["score_vs_level_ahead"])
    assert [b["periods"] for b in down["runs"][0]["by_score"]] == \
           [b["periods"] for b in up["runs"][0]["by_score"]]


def test_a_half_life_adds_a_run():
    r = bt([1, 3, 2, 5, 1, 4, 2, 6, 3, 2, 5, 1], half_lives=(1,))
    assert [x["half_life_years"] for x in r["runs"]] == [None, 1]


@pytest.mark.parametrize("bad", [dict(pct=(75, 50)), dict(pct=(0, 50)), dict(horizon=0),
                                 dict(min_history=1), dict(min_history=30)])
def test_impossible_settings_are_refused(bad):
    with pytest.raises(ValueError):
        bt([1, 3, 2, 5, 1, 4, 2, 6, 3, 2, 5, 1], **bad)


def test_public_cards_long_history_is_the_most_predictive_of_level():
    r = backtest(load("cards_nco_ttm.csv"), "c", "%", "higher_is_worse", "quarterly", 1,
                 (50, 75, 90, 95), 4, 41, True, (10, 5))
    lvl = [x["score_vs_level_ahead"] for x in r["runs"]]
    assert [round(x, 2) for x in lvl] == [0.80, 0.78, 0.68]
    assert all(x["score_vs_change_ahead"] < 0 for x in r["runs"])


def test_values_and_weights_must_be_the_same_length():
    with pytest.raises(ValueError):
        weighted_percentile([1, 2, 3, 4], [1, 1, 1], 50)
