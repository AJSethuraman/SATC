"""The minimap's memory (Dread/Map.lua) under plain Lua."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"


@pytest.fixture()
def env():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Map.lua"), ns)
    return lua, ns


def cells(t):
    return [(t[i].ix, t[i].iy) for i in range(1, len(t) + 1)]


def test_a_new_map_knows_its_size_and_has_seen_nothing(env):
    lua, ns = env
    m = ns.Map.new(2400, 1500)
    assert m.cols == 40 and m.rows == 25 and m.count == 0
    assert ns.Map.is_seen(m, 100, 100) is False


def test_revealing_marks_the_cells_around_you_and_returns_only_the_new_ones(env):
    lua, ns = env
    m = ns.Map.new(2400, 1500)
    first = cells(ns.Map.reveal(m, 1200, 750, 130))
    assert len(first) == m.count > 10
    assert ns.Map.is_seen(m, 1200, 750) and ns.Map.is_seen(m, 1300, 750)
    assert not ns.Map.is_seen(m, 1800, 750) and not ns.Map.is_seen(m, 1200, 1200)
    assert cells(ns.Map.reveal(m, 1200, 750, 130)) == []                    # again: nothing new
    count = m.count
    more = cells(ns.Map.reveal(m, 1320, 750, 130))                          # one step on: only the new strip
    assert 0 < len(more) < len(first) and m.count == count + len(more)
    assert not set(more) & set(first)


def test_the_revealed_area_is_a_round_patch_of_about_the_right_size(env):
    lua, ns = env
    m = ns.Map.new(2400, 1500)
    ns.Map.reveal(m, 1200, 750, 240)
    # a disc of radius 240 + half a cell is about pi * 270^2 / 60^2 = 63.6 cells
    assert 50 <= m.count <= 80
    assert not ns.Map.is_seen(m, 1200 + 400, 750)


def test_revealing_at_the_edge_stays_inside_the_map(env):
    lua, ns = env
    m = ns.Map.new(2400, 1500)
    for x, y in ((0, 0), (2400, 1500), (-50, 700), (3000, 700)):
        for c in cells(ns.Map.reveal(m, x, y, 260)):
            assert 0 <= c[0] < m.cols and 0 <= c[1] < m.rows


def test_cell_of_clamps_and_matches_is_seen(env):
    lua, ns = env
    m = ns.Map.new(2400, 1500)
    assert tuple(ns.Map.cell_of(m, 130, 70)) == (2, 1)
    assert tuple(ns.Map.cell_of(m, -10, 99999)) == (0, 24) and tuple(ns.Map.cell_of(m, 5000, -5)) == (39, 0)


def test_world_to_minimap_maps_corners_and_centre(env):
    lua, ns = env
    m = ns.Map.new(2400, 1500)
    assert tuple(ns.Map.to_mini(m, 0, 0, 168, 105)) == (0, 0)
    assert tuple(ns.Map.to_mini(m, 2400, 1500, 168, 105)) == (168, 105)
    x, y = ns.Map.to_mini(m, 1200, 750, 168, 105)
    assert x == pytest.approx(84) and y == pytest.approx(52.5)


def test_a_cells_rectangle_is_where_the_world_position_lands_and_tiles_the_map(env):
    lua, ns = env
    m = ns.Map.new(2400, 1500)
    l, b, w, h = ns.Map.cell_rect(m, 3, 2, 168, 105)
    assert l == pytest.approx(3 * 60 / 2400 * 168) and b == pytest.approx(2 * 60 / 1500 * 105)
    assert w == pytest.approx(60 / 2400 * 168) and h == pytest.approx(60 / 1500 * 105)
    px, py = ns.Map.to_mini(m, 3 * 60 + 30, 2 * 60 + 30, 168, 105)        # the middle of that cell
    assert l < px < l + w and b < py < b + h
    assert w * m.cols == pytest.approx(168) and h * m.rows == pytest.approx(105)
