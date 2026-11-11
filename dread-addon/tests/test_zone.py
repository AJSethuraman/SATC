"""The two areas (Dread/Zone.lua) under plain Lua."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"


def load():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Combat", "Zone"):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


@pytest.fixture()
def env():
    return load()


def items(t):
    return [t[i] for i in range(1, len(t) + 1)]


def dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def test_both_areas_exist_and_have_the_right_shape(env):
    lua, ns = env
    moor, cave = ns.Zone.get("moor"), ns.Zone.get("cave")
    assert moor.w == 2400 and moor.h == 1500 and cave.w == 1600 and cave.h == 1000
    assert ns.Zone.get("nowhere") is None and ns.Zone.START == "moor"
    assert moor.ground > 0 and cave.ground > 0 and moor.ground != cave.ground
    for fl in (moor.floor, cave.floor):                               # grass/dirt layering: two textures, the top one faded
        assert fl.base > 1000 and fl.overlay > 1000 and fl.base != fl.overlay
        assert 0 < fl.overlay_alpha < 1 and fl.overlay_tile > fl.tile >= 32
        assert len(items(fl.tint)) == 3 and len(items(fl.overlay_tint)) == 3


def test_the_layout_is_the_same_every_time(env):
    (lua1, ns1), (lua2, ns2) = load(), load()
    a, b = ns1.Zone.get("moor"), ns2.Zone.get("moor")
    assert len(items(a.doodads)) == len(items(b.doodads)) > 50
    assert all(x.id == y.id and x.x == y.x and x.y == y.y for x, y in zip(items(a.doodads), items(b.doodads)))
    assert all(x.x == y.x and x.life == y.life for x, y in zip(items(a.monsters), items(b.monsters)))


def test_the_moor_has_enough_packs_and_the_camp_is_safe(env):
    lua, ns = env
    moor = ns.Zone.get("moor")
    packs = {m.pack for m in items(moor.monsters)}
    assert len(packs) >= 8
    assert all(dist(m, moor.spawn) > 350 for m in items(moor.monsters))        # nothing within shouting distance of the camp
    assert all(dist(o, moor.spawn) > 190 for o in items(moor.obstacles))       # and no tree on top of you at the start


def test_every_pack_is_a_pack_and_everything_is_in_bounds(env):
    lua, ns = env
    for name in ("moor", "cave"):
        area = ns.Zone.get(name)
        by_pack = {}
        for m in items(area.monsters):
            by_pack.setdefault(m.pack, []).append(m)
            assert 0 < m.x < area.w and 0 < m.y < area.h
            assert m.cid > 0 and m.life > 0 and m.aggro > 0 and m.name
            assert m.resist is not None
        assert all(len(v) >= 2 for v in by_pack.values())
        for d in items(area.doodads):
            assert 0 < d.x < area.w and 0 < d.y < area.h and d.id > 0 and d.w > 0


def test_no_monster_starts_inside_a_tree_or_rock(env):
    lua, ns = env
    for name in ("moor", "cave"):
        area = ns.Zone.get(name)
        for m in items(area.monsters):
            for o in items(area.obstacles):
                assert dist(m, o) > o.r + m.radius * 0.6 - 0.1, f"{m.name} stands in an obstacle in {name}"


def test_the_cave_has_exactly_one_boss_and_a_quest(env):
    lua, ns = env
    cave = ns.Zone.get("cave")
    bosses = [m for m in items(cave.monsters) if m.boss is True]
    assert len(bosses) == 1 and bosses[0].name == cave.quest.boss and bosses[0].life >= 200
    assert cave.quest.reward_points == 1 and cave.quest.id == "den"
    assert not any(m.boss for m in items(ns.Zone.get("moor").monsters))


def test_the_exits_link_both_ways_and_land_somewhere_open(env):
    lua, ns = env
    moor, cave = ns.Zone.get("moor"), ns.Zone.get("cave")
    mx, cx = moor.exits[1], cave.exits[1]
    assert mx.to == "cave" and cx.to == "moor"
    # arriving in the moor from the cave puts you near the cave mouth, but not on top of it (or you would bounce straight back)
    assert cx.arrive is not None and 0 < cx.arrive.x < moor.w and 0 < cx.arrive.y < moor.h
    assert dist(cx.arrive, mx) > mx.r + 10
    assert dist(cave.spawn, cx) > cx.r + 10                      # same going the other way
    for a, ex in ((moor, mx), (cave, cx)):
        assert all(dist(o, ex) > o.r + 20 for o in items(a.obstacles))            # nothing blocks the way in


def test_scenery_ids_are_numbers_the_game_can_use(env):
    lua, ns = env
    for kind in ("tree", "fallen", "bush", "grave", "rock"):
        spec = ns.Zone.SCENERY[kind]
        assert all(isinstance(i, int) and i > 1000 for i in items(spec.ids))
    # only things that are meant to block (trunks, boulders) are obstacles
    obstacle_kinds = {d.kind for d in items(ns.Zone.get("moor").doodads) if d.r > 0}
    assert obstacle_kinds == {"tree", "fallen", "rock"}


def test_a_built_area_loads_into_a_fight_and_the_boss_is_the_boss(env):
    lua, ns = env
    w = ns.Combat.new(lua.table_from({"seed": 1}))
    ns.Combat.enter(w, ns.Zone.get("cave"))
    assert w.area == "cave" and w.w == 1600 and w.player.x == 150
    assert sum(1 for m in items(w.monsters) if m.boss) == 1
    assert all(m.awake is False for m in items(w.monsters))      # everything starts asleep
    assert len(items(w.obstacles)) > 20


def test_scenery_is_spaced_out_so_it_does_not_pile_up(env):
    lua, ns = env
    for name in ("moor", "cave"):
        d = items(ns.Zone.get(name).doodads)
        for i, a in enumerate(d):
            for b in d[i + 1:]:
                assert dist(a, b) >= 69.9, f"{a.kind} and {b.kind} overlap in {name}"


def test_what_blocks_you_fits_inside_what_you_see(env):
    # The first look at the moor had trees drawn about six times wider than the circle that stopped you,
    # so you seemed to walk through them. The solid part must be a real share of the visible footprint.
    lua, ns = env
    for kind in ("tree", "fallen", "rock"):
        spec = ns.Zone.SCENERY[kind]
        assert spec.r > 0
        assert 0.25 * spec.w <= spec.r * 2 <= spec.w, f"{kind}: solid width {spec.r * 2} against a visible width of {spec.w}"
    for kind in ("bush", "grave"):
        assert ns.Zone.SCENERY[kind].r == 0                                  # things you may walk over stay walkable


def test_the_camera_distance_shrinks_the_frame_back_to_the_footprint(env):
    # A model fills its frame at camera distance 1, so frame / cam is how big it looks. Frame = footprint x frame, so cam must equal frame.
    lua, ns = env
    for kind in ("tree", "fallen", "bush", "grave", "rock"):
        spec = ns.Zone.SCENERY[kind]
        assert spec.cam == spec.frame >= 1.5, f"{kind} would not look {spec.w} wide"


def test_the_build_stamp_is_a_real_string(env):
    lua, ns = env
    ns2 = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Build.lua"), ns2)
    assert isinstance(ns2.BUILD, str) and "UTC" in ns2.BUILD
