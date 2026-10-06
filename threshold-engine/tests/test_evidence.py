"""Evidence: the statistics behind each judgement point, and the scenarios."""
import math
import statistics

import pytest

from conftest import load, quarters
from threshold_engine.evidence import _deepest_dip, evidence, robust_z
from threshold_engine.series import Point


def ev(points, **kw):
    return evidence(points, "test", "%", kw.get("direction", "higher_is_worse"),
                    "quarterly", 1, 5, 0.75, kw.get("floor", True))


def test_robust_z_by_hand():
    # median 3, absolute deviations 2,1,0,1,2 -> MAD 1, scaled 1.4826.
    assert robust_z(7, [1, 2, 3, 4, 5]) == pytest.approx(4 / 1.4826)
    assert robust_z(4, [3, 3, 3]) == math.inf
    assert robust_z(3, [3, 3, 3]) == 0


def test_a_spell_is_measured_against_history_outside_it():
    v = [1, 1.2, 0.8, 1, 1.1, 0.9, 1, 6, 1, 1.05, 0.95, 1]
    e = ev(quarters(v))
    big = max(e["spells"], key=lambda s: s["peak"])
    outside = [x for i, x in enumerate(v) if i != 7]
    assert big["robust_z"] == pytest.approx(robust_z(6, outside))


def test_return_period_is_years_of_history_per_spell_this_bad():
    v = [1, 1, 3, 1, 1, 1, 5, 1, 1, 1, 1, 1]        # 3 years, two spells
    s = {x["peak"]: x for x in ev(quarters(v))["spells"]}
    assert s[3]["return_period_years"] == pytest.approx(1.5)
    assert s[5]["return_period_years"] == pytest.approx(3.0)


def test_the_deepest_dip_lies_between_two_higher_points():
    pts = quarters([2, 5, 3, 6, 2])
    d = _deepest_dip(pts, pts)
    assert d == {"date": pts[2].date, "depth": 2}
    assert _deepest_dip(quarters([2, 3, 4, 3, 2]), None) is None


def test_scenario_c_removes_the_largest_only_when_another_is_unusual():
    calm = [1, 1.1, 0.9, 1, 1.05, 0.95] * 3
    two = calm + [5] + calm + [9] + calm
    one = calm + [1.2] + calm + [9] + calm
    a, b = ev(quarters(two)), ev(quarters(one))
    assert a["scenarios"][2]["removed"] is not None
    assert a["scenarios"][2]["worst_kept"] == 5
    assert b["scenarios"][2]["removed"] is None
    assert b["scenarios"][2]["worst_kept"] == 9


def test_scenario_bounds_are_median_to_the_fraction_of_the_worst_kept():
    v = [1, 1.1, 0.9, 1, 3, 1, 0.95, 1.05, 8, 1]
    sc = ev(quarters(v))["scenarios"][0]
    m = statistics.median(v)
    assert sc["bounds"] == pytest.approx([m + i * 0.75 * (8 - m) / 3 for i in range(4)])


def test_lower_is_worse_measures_mirror():
    v = [1, 1.1, 0.9, 1, 1.05, 0.95, 4, 1, 1.1, 0.9, 1, 9, 1, 1]
    up = ev(quarters(v))
    down = ev(quarters([-x for x in v]), direction="lower_is_worse", floor=False)
    assert [s["robust_z"] for s in down["spells"]] == pytest.approx(
        [s["robust_z"] for s in up["spells"]])
    assert down["scenarios"][2]["bounds"] == pytest.approx(
        [-b for b in up["scenarios"][2]["bounds"]])


@pytest.mark.parametrize("name, unusual, removed", [
    ("cards", 2, True), ("mortgage", 1, False), ("home_equity", 1, False),
    ("other_consumer_as_filed", 1, False)])
def test_public_history(name, unusual, removed):
    e = ev(load(name + "_nco_ttm.csv"))
    assert e["unusual_count"]["3.5"] == unusual
    assert (e["scenarios"][2]["removed"] is not None) == removed


def test_mortgage_2002_is_ordinary_and_the_2012_bump_is_noise():
    e = ev(load("mortgage_nco_ttm.csv"))
    z = {s["start"]: s for s in e["spells"]}
    assert z["2001-04-01"]["robust_z"] < 1
    assert z["2007-04-01"]["dip"]["in_sd_of_change"] < 1


def test_cards_2000_dip_is_large():
    e = ev(load("cards_nco_ttm.csv"))
    s = next(s for s in e["spells"] if s["start"] == "1996-04-01")
    assert s["dip"]["date"] == "2000-10-01"
    assert s["dip"]["in_sd_of_change"] == pytest.approx(3.4, abs=0.05)


def test_the_quarter_back_at_normal_is_not_inside_the_spell():
    from threshold_engine.evidence import _inside
    spell = {"start": "2000-04-01", "end": "2000-10-01"}
    assert _inside(spell, "2000-07-01") and not _inside(spell, "2000-10-01")


def test_spells_with_equal_peaks_share_a_return_period():
    v = [1, 1, 4, 1, 1, 1, 4, 1, 1, 1, 1, 1]        # 3 years, two peaks of 4
    assert [s["return_period_years"] for s in ev(quarters(v))["spells"]] == [1.5, 1.5]


def test_the_change_yardstick_is_the_sample_standard_deviation():
    # Changes 1, 2, 3: =STDEV.S is 1.
    assert ev(quarters([1, 2, 4, 7, 1]))["sd_of_change"] == pytest.approx(
        statistics.stdev([1, 2, 3, -6]))
    assert statistics.stdev([1, 2, 3, -6]) != pytest.approx(statistics.pstdev([1, 2, 3, -6]))


# ---- recency ---------------------------------------------------------------
from threshold_engine.evidence import recency_weights, weighted_median  # noqa: E402


@pytest.mark.parametrize("values", [[5, 1, 3], [4, 1, 3, 2], [2, 2, 7, 9, 1, 0]])
def test_equal_weights_give_the_ordinary_median(values):
    assert weighted_median(values, [1] * len(values)) == statistics.median(values)


def test_weighted_median_by_hand():
    # Weights 1, 1, 4 on values 1, 2, 3: half the weight (3) is reached at 3.
    assert weighted_median([1, 2, 3], [1, 1, 4]) == 3
    # Weights 1, 1, 2: cumulative 1, 2, 4; half is 2, reached at 2, passed at 3.
    assert weighted_median([1, 2, 3], [1, 1, 2]) == 2.5


def test_a_weight_halves_every_half_life():
    w = recency_weights(["2016-06-30", "2021-06-30", "2026-06-30"], 5)
    assert w == pytest.approx([0.25, 0.5, 1.0])


def test_recency_moves_the_normal_level_and_not_the_worst_kept():
    calm_then_quiet = [2] * 20 + [9] + [2] * 20 + [1] * 20
    e = evidence(quarters(calm_then_quiet, 1990), "t", "%", "higher_is_worse",
                 "quarterly", 1, 5, 0.75, True, half_lives=(2,))
    r = e["recency"][0]
    assert r["normal"] == 1 and r["worst_kept"] == 9
    assert e["scenarios"][0]["normal"] == 2
    # Weights r**k, r = 0.5 ** (1/8) per quarter, over 61 quarters:
    # (sum w)^2 / sum w^2, which tends to (1 + r) / (1 - r), about 23.
    r8 = 0.5 ** (1 / 8)
    w = [r8 ** k for k in range(61)]
    assert r["effective_quarters"] == pytest.approx(sum(w) ** 2 / sum(x * x for x in w))
    assert r["effective_quarters"] == pytest.approx((1 + r8) / (1 - r8), rel=0.02)


def test_a_half_life_that_puts_normal_at_zero_is_refused():
    e = evidence(load("mortgage_nco_ttm.csv"), "m", "%", "higher_is_worse",
                 "quarterly", 1, 5, 0.75, True, half_lives=(10, 5))
    assert "refused" not in e["recency"][0]
    assert "refused" in e["recency"][1] and "bounds" not in e["recency"][1]


def test_no_half_life_stated_means_no_recency_rows():
    assert ev(quarters([1, 2, 1, 5, 1]))["recency"] == []



# ---- temporary departures ---------------------------------------------------
from threshold_engine.evidence import departures  # noqa: E402


def _wavy(n=80):
    # a gentle, regular wave: every window departs a little, none stands out
    return [2 + 0.05 * ((i % 6) - 2.5) for i in range(n)]


def test_a_planted_dip_and_a_larger_planted_spike_are_found_largest_first():
    v = _wavy()
    for i, x in enumerate([1.2, 1.6, 1.0, 0.6, 1.0, 1.6, 1.2]):     # dip, quarters 50-56
        v[50 + i] -= x
    for i, x in enumerate([2, 3, 4, 3, 2]):                        # spike, quarters 15-19
        v[15 + i] += x
    d = departures(quarters(v), lengths=(8,), rounds=2)
    assert d[0]["direction"] == "above the path" and d[1]["direction"] == "below the path"
    q = quarters(v)
    assert q[15].date <= d[0]["first"] <= d[0]["last"] <= q[19].date or         d[0]["first"] <= q[17].date <= d[0]["last"]
    assert d[1]["first"] <= q[53].date <= d[1]["last"]


def test_the_bridge_is_drawn_from_the_window_ends():
    # One window of 4 over 1, 1, 1, 5, 1: bridge 1 -> 1; mean of 0, 4, 0 = 4/3.
    d = departures(quarters([1, 1, 1, 5, 1]), lengths=(4,), rounds=1)
    assert len(d) == 1 and d[0]["mean_departure"] == pytest.approx(4 / 3)
    q = quarters([1, 1, 1, 5, 1])
    assert (d[0]["bridge_from"], d[0]["first"], d[0]["last"], d[0]["bridge_to"]) == (
        q[0].date, q[1].date, q[3].date, q[4].date)


def test_after_the_largest_its_reach_is_set_aside():
    v = _wavy()
    for i, x in enumerate([2, 3, 4, 3, 2]):
        v[30 + i] += x
    d = departures(quarters(v), lengths=(8,), rounds=3)
    q = quarters(v)
    # nothing after the first may lie within one window-length of the spike
    for x in d[1:]:
        assert x["last"] < q[30 - 8].date or x["first"] > q[34 + 8].date


def test_cards_departures_from_public_history():
    e = ev(load("cards_nco_ttm.csv"))
    got = [(d["first"][:4], d["direction"]) for d in e["departures"]]
    assert got == [("2009", "above the path"), ("2001", "above the path"), ("2021", "below the path")]


def test_other_consumer_finds_the_pandemic_dip_second():
    e = ev(load("other_consumer_as_filed_nco_ttm.csv"))
    d = e["departures"][1]
    assert d["direction"] == "below the path" and d["first"].startswith("2021")



def test_a_lower_is_worse_measure_reports_departures_in_its_own_units():
    # A credit score falling below its path is the worse direction: reported as
    # worse ("above the path" in the engine's worse-is-higher terms) with a
    # negative change in score points.
    cards = ev(load("cards_nco_ttm.csv"))["departures"][0]
    from threshold_engine.series import Point
    mirrored = [Point(p.date, -p.value) for p in load("cards_nco_ttm.csv")]
    score = ev(mirrored, direction="lower_is_worse", floor=False)["departures"][0]
    assert score["direction"] == cards["direction"]
    assert score["mean_departure"] == pytest.approx(-cards["mean_departure"])
