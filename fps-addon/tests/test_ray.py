"""Ray.lua and Level.lua under plain Lua. Every expected number is worked out by hand in the comment beside it."""
import math
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
G = Path(__file__).resolve().parents[1] / "Gauntlet"


@pytest.fixture()
def env():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Gauntlet', ns) end")
    for f in ("Ray", "Level"):
        ld(str(G / f"{f}.lua"), ns)
    return lua, ns


def room(lua, ns, w=11, h=3):
    """A flat-walled box: wall all round, open inside, w wide and h tall counting the walls."""
    rows = ["1" * w] + ["1" + "." * (w - 2) + "1" for _ in range(h - 2)] + ["1" * w]
    return ns.Ray.parse(lua.table_from(rows))


def test_parse_reads_empty_squares_numbered_walls_and_treats_other_marks_as_wall_one(env):
    lua, ns = env
    m = ns.Ray.parse(lua.table_from(["1.2", " 3#"]))
    assert m.w == 3 and m.h == 2
    assert [m.cells[1][i] for i in (1, 2, 3)] == [1, 0, 2] and [m.cells[2][i] for i in (1, 2, 3)] == [0, 3, 1]


def test_at_reads_the_square_a_point_is_in_and_outside_the_map_is_wall(env):
    lua, ns = env
    m = ns.Ray.parse(lua.table_from(["111", "1.1", "111"]))
    assert ns.Ray.at(m, 1.5, 1.5) == 0 and ns.Ray.at(m, 0.5, 1.5) == 1 and ns.Ray.at(m, 1.99, 1.01) == 0
    assert ns.Ray.at(m, -3, 1.5) == 1 and ns.Ray.at(m, 1.5, 40) == 1


def test_a_ray_straight_at_a_wall_measures_the_distance_to_it(env):
    lua, ns = env
    m = room(lua, ns)
    # from x 2.5 along +x the wall square at x 10 starts at 10.0: 7.5 away. It faces left/right (side 0); hit at y 1.5 -> u 0.5.
    d, side, id_, u = ns.Ray.cast(m, 2.5, 1.5, 1, 0)
    assert d == pytest.approx(7.5) and side == 0 and id_ == 1 and u == pytest.approx(0.5)
    d, side, id_, u = ns.Ray.cast(m, 2.5, 1.5, 0, 1)                         # straight down: the wall at y 2.0 is 0.5 away, a up/down face
    assert d == pytest.approx(0.5) and side == 1
    d, side, _, _ = ns.Ray.cast(m, 2.5, 1.5, -1, 0)                          # to the left the wall edge is at x 1.0: 1.5 away
    assert d == pytest.approx(1.5) and side == 0


def test_the_hit_position_along_the_wall_follows_where_the_ray_lands(env):
    lua, ns = env
    m = room(lua, ns, w=3, h=10)                                              # a tall thin shaft, x 1..2 open
    # looking down from (1.25, 1.5): lands on the bottom wall at x 1.25, so u would be 0.25, then 1 - u for a face looked at from above...
    _, side, _, u = ns.Ray.cast(m, 1.25, 1.5, 0, 1)
    assert side == 1 and u == pytest.approx(0.25)                              # dy > 0 keeps u as it is
    _, side, _, u = ns.Ray.cast(m, 1.25, 8.5, 0, -1)                           # looking up at the top wall: dy < 0 mirrors it to 0.75
    assert side == 1 and u == pytest.approx(0.75)


def test_a_ray_reports_the_kind_of_wall_it_hits(env):
    lua, ns = env
    m = ns.Ray.parse(lua.table_from(["1111", "1..3", "1111"]))
    assert ns.Ray.cast(m, 1.5, 1.5, 1, 0)[2] == 3


def test_there_is_no_fish_eye_a_flat_wall_is_the_same_distance_across_the_whole_view(env):
    lua, ns = env
    m = room(lua, ns, w=13, h=41)                                              # tall, so the side rays reach the far wall before a side wall
    cols = ns.Ray.columns(m, 2.5, 20.5, 0, math.radians(90), 9)                 # facing the right-hand wall at x 12: 9.5 away
    ds = [cols[i].dist for i in range(1, 10)]
    assert all(d == pytest.approx(9.5) for d in ds)


def test_columns_run_left_to_right_and_the_middle_one_looks_straight_ahead(env):
    lua, ns = env
    m = ns.Ray.parse(lua.table_from(["11111", "1...1", "1...1", "1...1", "11111"]))
    cols = ns.Ray.columns(m, 2.5, 2.5, 0, math.radians(90), 5)                 # facing +x: right of you is +y (down the page)
    assert cols[3].dist == pytest.approx(1.5)                                  # straight ahead to the wall at x 4
    assert cols[1].u != cols[5].u                                              # different parts of the wall are hit, so different texture columns
    assert len(list(cols.values())) == 5


def test_a_sprite_straight_ahead_is_in_the_middle_column_and_one_to_the_right_is_further_right(env):
    lua, ns = env
    fov = math.radians(90)
    col, depth = ns.Ray.sprite(1.5, 1.5, 0, fov, 100, 3.5, 1.5)               # 2 ahead, none sideways
    assert col == pytest.approx(50.5) and depth == pytest.approx(2)
    col, depth = ns.Ray.sprite(1.5, 1.5, 0, fov, 100, 3.5, 2.5)               # 2 ahead, 1 to the right: 50 * (1 + 1/2) + 0.5
    assert col == pytest.approx(75.5) and depth == pytest.approx(2)
    col, depth = ns.Ray.sprite(1.5, 1.5, 0, fov, 100, 3.5, 0.5)               # 1 to the left: 50 * (1 - 1/2) + 0.5
    assert col == pytest.approx(25.5)
    assert ns.Ray.sprite(1.5, 1.5, 0, fov, 100, 0.5, 1.5) is None             # behind you: not shown


def test_turning_the_camera_moves_a_sprite_across_the_view(env):
    lua, ns = env
    fov = math.radians(90)
    col, depth = ns.Ray.sprite(1.5, 1.5, math.radians(90), fov, 100, 1.5, 3.5)  # now facing +y, sprite 2 ahead in that direction
    assert col == pytest.approx(50.5) and depth == pytest.approx(2)


def test_walking_into_a_wall_stops_and_a_diagonal_slides_along_it(env):
    lua, ns = env
    m = room(lua, ns, w=8, h=8)
    x, y = ns.Ray.move(m, 1.5, 1.5, -1, 0, 0.2)                                # straight into the left wall: no movement
    assert (x, y) == (1.5, 1.5)
    x, y = ns.Ray.move(m, 1.3, 3.5, -0.5, 0.3, 0.2)                            # into the left wall at an angle: x blocked, y still moves
    assert x == pytest.approx(1.3) and y == pytest.approx(3.8)
    x, y = ns.Ray.move(m, 3.5, 3.5, 0.5, 0.25, 0.2)                            # in open space: both
    assert x == pytest.approx(4.0) and y == pytest.approx(3.75)


def test_a_shot_hits_the_nearest_thing_in_front_of_the_wall_and_misses_the_rest(env):
    lua, ns = env
    m = room(lua, ns, w=13, h=5)
    t = lambda x, y, **k: lua.table_from({"x": x, "y": y, "r": 0.3, **k})
    near, far, aside, behind_me, dead = t(5.5, 2.5), t(9.5, 2.5), t(6.5, 3.0), t(0.5, 2.5), t(4.5, 2.5, dead=True)
    things = lua.table_from([far, near, aside, behind_me, dead])
    hit, d = ns.Ray.hitscan(m, 2.5, 2.5, 0, things, 40)
    assert lua.eval("rawequal")(hit, near) and d == pytest.approx(3)           # the near one, 3 away; the dead one in front of it is skipped
    hit, d = ns.Ray.hitscan(m, 2.5, 2.5, math.radians(10), things, 40)         # aimed 10 degrees off: passes the near one, 3 away but 0.53 to the side
    assert hit is None or not lua.eval("rawequal")(hit, near)


def test_a_thing_behind_a_wall_cannot_be_shot(env):
    lua, ns = env
    m = ns.Ray.parse(lua.table_from(["111111", "1.1..1", "111111"]))
    ghost = lua.table_from({"x": 4.5, "y": 1.5, "r": 0.3})
    assert ns.Ray.hitscan(m, 1.5, 1.5, 0, lua.table_from([ghost]), 40)[0] is None


# ---------------------------------------------------------------- the level
def open_cells(lua, ns):
    m = ns.Ray.parse(ns.Level.ROWS)
    return m, [(x, y) for y in range(m.h) for x in range(m.w) if m.cells[y + 1][x + 1] == 0]


def test_the_level_is_a_rectangle_walled_all_round(env):
    lua, ns = env
    rows = [str(r) for r in ns.Level.ROWS.values()]
    assert len({len(r) for r in rows}) == 1
    assert set(rows[0]) <= set("123456789") and set(rows[-1]) <= set("123456789")
    assert all(r[0] != "." and r[-1] != "." for r in rows)


def test_the_player_and_every_enemy_start_in_open_squares_and_every_open_square_can_be_reached(env):
    lua, ns = env
    m, cells = open_cells(lua, ns)
    s = ns.Level.START
    assert ns.Ray.at(m, s.x, s.y) == 0
    for e in ns.Level.ENEMIES.values():
        assert ns.Ray.at(m, e.x, e.y) == 0, e.name
    seen, todo = set(), [(int(s.x), int(s.y))]
    while todo:
        c = todo.pop()
        if c in seen:
            continue
        seen.add(c)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dx, c[1] + dy)
            if n in set(cells) and n not in seen:
                todo.append(n)
    assert seen == set(cells)                                                  # no sealed room, no unreachable pocket


def test_the_speed_test_route_stays_in_open_squares(env):
    lua, ns = env
    m, _ = open_cells(lua, ns)
    r = ns.Level.ROUTE
    for i in range(360):
        a = math.radians(i)
        x, y = r.cx + r.r * math.cos(a), r.cy + r.r * math.sin(a)
        assert not any(ns.Ray.blocked(m, x + dx, y + dy) for dx in (-0.25, 0.25) for dy in (-0.25, 0.25)), (x, y)


def test_every_wall_kind_in_the_level_has_a_texture_and_a_colour_to_fall_back_on(env):
    lua, ns = env
    m, _ = open_cells(lua, ns)
    kinds = {m.cells[y][x] for y in range(1, m.h + 1) for x in range(1, m.w + 1)} - {0}
    for k in kinds:
        w = ns.Level.WALLS[k]
        assert isinstance(w.file, int) and w.file > 1000 and all(0 <= w.color[i] <= 1 for i in (1, 2, 3)), k
    ids = [c[1] for c in ns.Level.CANDIDATES.values()]
    assert len(ids) == len(set(ids)) and all(i > 1000 for i in ids)
