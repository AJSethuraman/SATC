"""Gen.lua, Nav.lua, Rules.lua: the generated levels are always playable. Run over many seeds and every level, so a bad layout cannot hide."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
G = Path(__file__).resolve().parents[1] / "Gauntlet"


@pytest.fixture(scope="module")
def make():
    def boot():
        lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        ns = lua.table()
        ld = lua.eval("function(p, ns) return loadfile(p)('Gauntlet', ns) end")
        for f in ("Ray", "Rules", "Nav", "Gen", "Play"):
            ld(str(G / f"{f}.lua"), ns)
        return lua, ns
    return boot


@pytest.fixture()
def env(make):
    return make()


def cells(ns, lv):
    return ns.Ray.parse(lv.rows)


def flood(ns, m, sx, sy, locked_blocks):
    seen, todo = set(), [(int(sx), int(sy))]
    while todo:
        x, y = todo.pop()
        if (x, y) in seen:
            continue
        v = m.cells[y + 1][x + 1] if 0 <= y < m.h and 0 <= x < m.w else None
        if v is None or not (v == 0 or v == 5 or (v == 6 and not locked_blocks)):
            continue
        seen.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return seen


LEVELS = [(n, s) for n in range(1, 6) for s in (1, 2, 3, 7, 42, 99)]


@pytest.mark.parametrize("n,seed", LEVELS)
def test_a_generated_level_is_a_sealed_rectangle_with_everything_in_open_squares(env, n, seed):
    lua, ns = env
    lv = ns.Gen.level(n, seed)
    rows = [str(r) for r in lv.rows.values()]
    S = ns.Gen.size(n)
    assert len(rows) == S and all(len(r) == S for r in rows)
    assert all(c != "." for c in rows[0] + rows[-1]) and all(r[0] != "." and r[-1] != "." for r in rows)
    m = cells(ns, lv)
    for name, things in (("enemy", lv.enemies), ("item", lv.pickups)):
        for t in things.values():
            assert ns.Ray.at(m, t.x, t.y) == 0, f"{name} {t.kind} stands in a wall at {t.x},{t.y}"
    assert ns.Ray.at(m, lv.start.x, lv.start.y) == 0 and ns.Ray.at(m, lv.exit.x, lv.exit.y) == 0


@pytest.mark.parametrize("n,seed", LEVELS)
def test_the_exit_is_reachable_only_through_the_locked_door_and_the_key_is_on_the_near_side(env, n, seed):
    lua, ns = env
    lv = ns.Gen.level(n, seed)
    m = cells(ns, lv)
    near = flood(ns, m, lv.start.x, lv.start.y, True)
    far = flood(ns, m, lv.start.x, lv.start.y, False)
    ex = (int(lv.exit.x), int(lv.exit.y))
    assert ex not in near and ex in far
    keys = [i for i in lv.pickups.values() if i.kind == "key"]
    assert len(keys) == 1 and (int(keys[0].x), int(keys[0].y)) in near
    locked = [(x, y) for y in range(m.h) for x in range(m.w) if m.cells[y + 1][x + 1] == 6]
    assert len(locked) == 1                                                         # exactly one lock, one key


@pytest.mark.parametrize("n,seed", LEVELS)
def test_every_enemy_and_pickup_can_be_reached_from_the_start(env, n, seed):
    lua, ns = env
    lv = ns.Gen.level(n, seed)
    m = cells(ns, lv)
    far = flood(ns, m, lv.start.x, lv.start.y, False)
    for t in list(lv.enemies.values()) + list(lv.pickups.values()):
        assert (int(t.x), int(t.y)) in far


@pytest.mark.parametrize("n,seed", LEVELS)
def test_doors_sit_in_straight_corridors_and_never_in_the_start_room(env, n, seed):
    lua, ns = env
    lv = ns.Gen.level(n, seed)
    m = cells(ns, lv)
    first = lv.rooms[1]
    for y in range(m.h):
        for x in range(m.w):
            if m.cells[y + 1][x + 1] in (5, 6):
                wall = lambda v: v not in (0, 5, 6)                                       # two doors side by side are still a passage
                lr = (wall(m.cells[y + 1][x]), wall(m.cells[y + 1][x + 2]))
                ud = (wall(m.cells[y][x + 1]), wall(m.cells[y + 2][x + 1]))
                assert (lr == (False, False) and ud == (True, True)) or (ud == (False, False) and lr == (True, True)), (x, y)
                assert not (first.x <= x + 1 < first.x + first.w and first.y <= y + 1 < first.y + first.h)      # the generator counts squares from 1


def test_levels_are_repeatable_and_different_seeds_differ(env):
    lua, ns = env
    a, b, c = ns.Gen.level(2, 5), ns.Gen.level(2, 5), ns.Gen.level(2, 6)
    assert [str(r) for r in a.rows.values()] == [str(r) for r in b.rows.values()]
    assert [str(r) for r in a.rows.values()] != [str(r) for r in c.rows.values()]
    assert a.start.x == b.start.x and len(list(a.enemies.values())) == len(list(b.enemies.values()))


def test_each_level_hands_out_the_next_weapon_and_the_last_has_a_boss_and_nothing_else_does(env):
    lua, ns = env
    guns = {1: "scatter", 2: "repeater", 3: "rocket"}
    for n in range(1, 6):
        lv = ns.Gen.level(n, 3)
        kinds = [i.kind for i in lv.pickups.values()]
        if n in guns:
            assert kinds.count(guns[n]) == 1
        bosses = [e for e in lv.enemies.values() if e.kind == "boss"]
        assert len(bosses) == (1 if n == 5 else 0) and lv.boss == (n == 5)
        assert any(k == "armor" for k in kinds) and any(k in ("health", "bigheal") for k in kinds)


def test_later_levels_are_bigger_and_more_crowded_and_use_the_roster_for_their_level(env):
    lua, ns = env
    sizes = [ns.Gen.size(n) for n in range(1, 6)]
    assert sizes == sorted(sizes) and sizes[0] < sizes[-1] and max(sizes) <= 56
    counts = [len(list(ns.Gen.level(n, 11).enemies.values())) for n in (1, 4)]
    assert counts[1] > counts[0]
    lv1 = ns.Gen.level(1, 11)
    assert {e.kind for e in lv1.enemies.values()} <= {"wolf", "kobold"}
    lv3 = ns.Gen.level(3, 11)
    assert {e.kind for e in lv3.enemies.values()} <= {"kobold", "murloc", "imp"}


def test_the_boss_arena_is_the_big_last_room_with_the_boss_in_it_and_the_lock_in_front(env):
    lua, ns = env
    lv = ns.Gen.level(5, 4)
    last = lv.rooms[len(list(lv.rooms.values()))]
    assert last.w == 11 and last.h == 11
    boss = [e for e in lv.enemies.values() if e.kind == "boss"][0]
    assert last.x - 1 <= boss.x < last.x - 1 + last.w and last.y - 1 <= boss.y < last.y - 1 + last.h
    assert abs(lv.exit.x - (last.x - 1 + last.w / 2)) < 1e-9 and abs(lv.exit.y - (last.y - 1 + last.h / 2)) < 1e-9


def test_the_first_room_has_no_enemies_and_has_ammo(env):
    lua, ns = env
    for n in range(1, 6):
        lv = ns.Gen.level(n, 8)
        r = lv.rooms[1]
        assert not [e for e in lv.enemies.values() if r.x - 1 <= e.x < r.x - 1 + r.w and r.y - 1 <= e.y < r.y - 1 + r.h]
        assert any(i.kind == "bullets" and r.x - 1 <= i.x < r.x - 1 + r.w for i in lv.pickups.values())


# ---------------------------------------------------------------- Nav
def test_the_flood_counts_steps_round_walls_and_leaves_sealed_places_empty(env):
    lua, ns = env
    m = ns.Ray.parse(lua.table_from(["1111111", "1..1..1", "1.11.11", "1.....1", "1111111"]))
    f = ns.Nav.field(m, 1.5, 1.5)
    assert f[2][2] == 0 and f[3][2] == 1 and f[4][2] == 2 and f[4][5] == 5 and f[3][5] == 6 and f[2][5] == 7
    sealed = ns.Nav.field(ns.Ray.parse(lua.table_from(["11111", "1.1.1", "11111"])), 1.5, 1.5)
    assert sealed[2][4] is None


def test_a_monster_heads_for_the_neighbour_nearest_the_goal_and_not_through_a_wall(env):
    lua, ns = env
    m = ns.Ray.parse(lua.table_from(["1111111", "1..1..1", "1.11.11", "1.....1", "1111111"]))
    f = ns.Nav.field(m, 5.5, 1.5)                                                   # the goal is top right
    x, y = ns.Nav.next(f, m, 1.5, 1.5)                                              # top left: it has to go down and round, not right
    assert (x, y) == (1.5, 2.5)
    x, y = ns.Nav.next(f, m, 4.5, 3.5)
    assert (x, y) == (4.5, 2.5)
    assert ns.Nav.next(f, m, 5.5, 1.5)[0] is None                                   # already there: nowhere nearer


def test_locked_doors_block_a_monster_and_ordinary_ones_do_not(env):
    lua, ns = env
    ordinary = ns.Nav.field(ns.Ray.parse(lua.table_from(["11111", "1.5.1", "11111"])), 1.5, 1.5)
    locked = ns.Nav.field(ns.Ray.parse(lua.table_from(["11111", "1.6.1", "11111"])), 1.5, 1.5)
    assert ordinary[2][4] == 2 and locked[2][4] is None
