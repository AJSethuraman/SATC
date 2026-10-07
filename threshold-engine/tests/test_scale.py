"""The reference scale, checked against hand calculations."""
import pytest

from threshold_engine.scale import scale, score, typical_yearly_move


def test_typical_yearly_move_by_hand():
    # Values 0..9: every change over 4 periods is 4, so the spread is 0.
    assert typical_yearly_move(list(range(10))) == 0
    # Changes over 4: 1, 3, 2, 6, 2 -> median 2, distances 1, 1, 0, 4, 0 ->
    # MAD 1 -> 1.4826.
    v = [0, 0, 0, 0, 1, 3, 2, 6, 2]
    assert typical_yearly_move(v) == pytest.approx(1.4826)


def test_a_change_needs_both_ends_kept():
    v = [0, 0, 0, 0, 1, None, 2, 6, 2, 5]
    # Pairs four apart with both ends kept: (0,1) (0,2) (0,6) (1,2) -> changes
    # 1, 2, 6, 1 -> median 1.5, distances 0.5, 0.5, 4.5, 0.5 -> MAD 0.5.
    # Closing the gap instead would pair across it and give 1.4826.
    assert typical_yearly_move(v) == pytest.approx(1.4826 * 0.5)


def test_the_lines_by_hand():
    # median 2; changes over 4 are all 1 except one 3 -> move 0 is useless, so
    # build a series whose move is exactly 1.4826: changes 1,3,2,6,2 as above.
    v = [0, 0, 0, 0, 1, 3, 2, 6, 2]
    r = scale(v, "higher_is_worse", 0.5, 1.5, 2.0, False)
    med, m = 1, 1.4826
    # Levels 0,0,0,0,1,3,2,6,2: median 1; distances 1,1,1,1,0,2,1,5,1; MAD 1.
    spread = 1.4826
    b3, b4 = med - 0.5 * m, med + 0.5 * m
    assert r["median"] == med and r["worst"] == 6 and r["spread_of_levels"] == pytest.approx(spread)
    assert r["bounds"] == pytest.approx([med - 1.5 * m, b3, b4, med + 2.0 * spread])


def test_lower_is_worse_mirrors():
    v = [0, 0, 0, 0, 1, 3, 2, 6, 2]
    up = scale(v, "higher_is_worse", 0.5, 1.5, 2.0, False)
    down = scale([-x for x in v], "lower_is_worse", 0.5, 1.5, 2.0, False)
    assert down["bounds"] == pytest.approx([-b for b in up["bounds"]])
    assert score(-6, down["bounds"], "lower_is_worse", "worse", False) == 5


@pytest.mark.parametrize("args, why", [
    (dict(v=[-1, -1, 0, -1, -2, 0, -1, 1, -1]), "median is at or below zero"),
    (dict(hw=1.0, ls=0.5), "Moderate-Low must begin"),
    (dict(z=0.2), "High must begin beyond Moderate-High"),
    (dict(z=4.0), "beyond the worst quarter kept"),
])
def test_refusals(args, why):
    v = args.get("v", [0, 0, 0, 0, 1, 3, 2, 6, 2])
    r = scale(v, "higher_is_worse", args.get("hw", 0.5), args.get("ls", 1.5), args.get("z", 2.0), True)
    assert r["bounds"] is None and why in r["refused"]


def test_on_the_line():
    b = [1, 2, 3, 4]
    assert score(2, b, "higher_is_worse", "worse", True) == 3
    assert score(2, b, "higher_is_worse", "better", True) == 2
    assert score(0, b, "higher_is_worse", "worse", True) == 1
