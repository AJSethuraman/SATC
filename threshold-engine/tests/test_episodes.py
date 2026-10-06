"""Stage 3: planted cycles must be recovered exactly."""
from conftest import quarters
from threshold_engine.episodes import find, sweep

NORMAL = 1.0


def test_three_planted_cycles_are_three_episodes():
    v = [1, 1, 2, 3, 2, 1, 1, 1, 4, 1, 1, 0.5, 2.5, 1, 1]
    eps = find(quarters(v), NORMAL, 0.5, None)
    assert [e.peak for e in eps] == [3, 4, 2.5]
    assert all(e.complete for e in eps)


def test_a_crisis_with_a_second_bump_is_one_episode():
    # Rises, peaks, falls part-way, bumps again, only then returns to normal:
    # the shape of 2008 in mortgage. One episode, peak the higher of the two.
    v = [1, 2, 5, 3, 4, 2, 1, 1]
    eps = find(quarters(v), NORMAL, 0.5, None)
    assert len(eps) == 1
    assert eps[0].peak == 5 and eps[0].height == 4


def test_a_blip_below_the_height_is_not_an_episode():
    v = [1, 1.2, 1, 3, 1]
    eps = find(quarters(v), NORMAL, 0.5, None)
    assert [e.peak for e in eps] == [3]


def test_materiality_removes_peaks_that_never_reach_it():
    v = [1, 2, 1, 6, 1]
    assert [e.peak for e in find(quarters(v), NORMAL, 0.5, 5.0)] == [6]


def test_dates_are_first_above_peak_and_first_back():
    pts = quarters([1, 2, 3, 2, 1])
    (e,) = find(pts, NORMAL, 0.5, None)
    assert (e.start, e.peak_date, e.end) == (pts[1].date, pts[2].date, pts[4].date)


def test_an_episode_still_running_is_open_and_not_complete():
    (e,) = find(quarters([1, 1, 3, 4]), NORMAL, 0.5, None)
    assert e.end is None and not e.complete


def test_an_episode_under_way_at_the_first_observation_has_an_unseen_start():
    (e,) = find(quarters([3, 2, 1, 1]), NORMAL, 0.5, None)
    assert e.unseen_start and not e.complete


def test_the_sweep_counts_complete_episodes_at_each_height():
    v = [1, 1.3, 1, 2, 1, 4, 1, 5]          # the last is open
    assert sweep(quarters(v), NORMAL, (0.2, 0.5, 2.0, 5.0), None) == [
        (0.2, 3), (0.5, 2), (2.0, 1), (5.0, 0)]
