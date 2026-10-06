"""The whole run: refusals, the outlier rule, cutoffs, scoring, provenance."""
import dataclasses
import statistics

import pytest

from conftest import NCO, quarters, settings
from threshold_engine import Refused, Result, Settings, run, score

# Normal 1; a mild cycle to 3, a severe one to 9, back to normal each time.
TWO_CYCLES = [1, 1, 1, 2, 3, 2, 1, 1, 1, 4, 9, 6, 1, 1, 0.5]


def test_settings_have_no_defaults():
    with pytest.raises(TypeError):
        Settings()
    assert all(f.default is dataclasses.MISSING
               for f in dataclasses.fields(Settings))


@pytest.mark.parametrize("bad", [
    dict(scale_points=1), dict(top_fraction=0), dict(top_fraction=1.5),
    dict(episode_height=0), dict(outlier_ratio=1.0), dict(min_other_episodes=0)])
def test_impossible_settings_are_refused(bad):
    r = run(NCO, settings(**bad), quarters(TWO_CYCLES))
    assert isinstance(r, Refused) and r.code == "settings"


def test_an_unknown_direction_is_refused():
    m = dataclasses.replace(NCO, direction="sideways")
    assert run(m, settings(), quarters(TWO_CYCLES)).code == "settings"


def test_no_stress_episode_is_refused_not_scaled():
    r = run(NCO, settings(), quarters([1, 1.1, 1, 0.9, 1, 1.1, 1]))
    assert isinstance(r, Refused) and r.code == "no_episode"


def test_only_an_open_episode_is_refused():
    r = run(NCO, settings(), quarters([1, 1, 1, 1, 2, 3, 4]))
    assert r.code == "no_episode"


def test_an_outlier_with_an_anchor_left_is_excluded():
    r = run(NCO, settings(), quarters(TWO_CYCLES))
    assert isinstance(r, Result)
    assert r.outlier["is_outlier"] and r.outlier["excluded"]
    # Excluded: the quarters of the severe cycle above the mild cycle's peak.
    assert r.outlier["run"][2] == 3
    assert r.anchor == 3


def test_an_outlier_is_kept_when_too_few_anchors_remain():
    r = run(NCO, settings(min_other_episodes=2), quarters(TWO_CYCLES))
    assert r.outlier["is_outlier"] and not r.outlier["excluded"]
    assert r.anchor == 9


def test_no_outlier_below_the_ratio():
    r = run(NCO, settings(outlier_ratio=5.0), quarters(TWO_CYCLES))
    assert not r.outlier["is_outlier"] and r.anchor == 9


def test_bounds_run_from_normal_to_the_stated_fraction_of_the_anchor():
    r = run(NCO, settings(min_other_episodes=2), quarters(TWO_CYCLES))
    normal = statistics.median(TWO_CYCLES)
    step = 0.75 * (9 - normal) / 3
    assert r.bounds == pytest.approx([normal + i * step for i in range(4)])


def test_a_declared_exclusion_leaves_the_normal_level_and_anchor():
    pts = quarters(TWO_CYCLES)
    cut = (pts[9].date, pts[11].date, "declared by the bank in a test")
    r = run(NCO, settings(min_other_episodes=2, exclusions=(cut,)), pts)
    assert r.anchor == 3
    assert r.settings.exclusions == (cut,)


def test_a_window_limits_what_is_read():
    pts = quarters(TWO_CYCLES)
    r = run(NCO, settings(window=(pts[7].date, pts[-1].date)), pts)
    # The mild cycle is outside the window: one episode, nothing to anchor on.
    assert r.outlier["episodes"] == 1 and r.anchor == 9


def test_a_value_on_a_bound_takes_the_worse_score():
    assert score(2.0, [1.0, 2.0, 3.0, 4.0], "higher_is_worse", False) == 3
    assert score(2.0, [4.0, 3.0, 2.0, 1.0], "lower_is_worse", False) == 4


def test_a_loss_at_or_below_zero_is_always_the_best_score():
    assert score(-0.02, [0.1, 0.2, 0.3, 0.4], "higher_is_worse", True) == 1
    assert score(0.0, [0.0, 0.2, 0.3, 0.4], "higher_is_worse", True) == 1


def test_lower_is_worse_is_the_mirror_image():
    up = run(NCO, settings(), quarters(TWO_CYCLES))
    m = dataclasses.replace(NCO, direction="lower_is_worse", floor_at_zero=False)
    down = run(m, settings(), quarters([-v for v in TWO_CYCLES]))
    assert down.bounds == pytest.approx([-b for b in up.bounds])
    assert down.latest_score == up.latest_score


def test_floor_at_zero_refuses_a_lower_is_worse_measure():
    m = dataclasses.replace(NCO, direction="lower_is_worse")
    assert run(m, settings(), quarters(TWO_CYCLES)).code == "settings"


def test_provenance_fingerprints_the_data_and_records_every_setting():
    pts = quarters(TWO_CYCLES)
    a = run(NCO, settings(), pts)
    b = run(NCO, settings(), pts[:-1] + [dataclasses.replace(pts[-1], value=0.6)])
    assert a.provenance["data_sha256"] != b.provenance["data_sha256"]
    assert a.provenance["settings"] == dataclasses.asdict(settings())
    assert a.provenance["observations"] == len(pts)


def test_an_episode_whose_start_is_unseen_cannot_anchor_a_scale():
    # The mild cycle is already under way at the first quarter, so its real
    # peak may lie before the data. It cannot stand in for the outlier.
    r = run(NCO, settings(), quarters([3, 2, 1, 1, 1, 1, 4, 9, 6, 1, 1, 0.5]))
    assert r.outlier["is_outlier"] and r.outlier["other_complete"] == 0
    assert not r.outlier["excluded"] and r.anchor == 9
