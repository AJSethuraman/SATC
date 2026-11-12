"""The two areas (Dread/Zone.lua) under plain Lua."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"


def load():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Items", "Combat", "Zone"):
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
    for name in ALL_AREAS:
        area = ns.Zone.get(name)
        by_pack = {}
        for m in items(area.monsters):
            by_pack.setdefault(m.pack, []).append(m)
            assert 0 < m.x < area.w and 0 < m.y < area.h
            assert ((m.cid or 0) > 0 or (m.model or 0) > 0) and m.life > 0 and m.aggro > 0 and m.name
            assert m.resist is not None
        assert all(len(v) >= 2 for v in by_pack.values())
        for d in items(area.doodads):
            assert 0 < d.x < area.w and 0 < d.y < area.h and d.id > 0 and d.w > 0


def test_no_monster_starts_inside_a_tree_or_rock(env):
    lua, ns = env
    for name in ALL_AREAS:
        area = ns.Zone.get(name)
        for m in items(area.monsters):
            for o in items(area.obstacles):
                assert dist(m, o) > o.r + m.radius * 0.6 - 0.1, f"{m.name} stands in an obstacle in {name}"


ALL_AREAS = ("moor", "cave", "fields", "burial")


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
    for kind in ("tree", "fallen", "bush", "grave", "rock", "pine", "icerock"):
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
    for name in ALL_AREAS:
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
    for kind in ("tree", "fallen", "bush", "grave", "rock", "pine", "icerock"):
        spec = ns.Zone.SCENERY[kind]
        assert spec.cam == spec.frame >= 1.5, f"{kind} would not look {spec.w} wide"


def test_the_build_stamp_is_a_real_string(env):
    lua, ns = env
    ns2 = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Build.lua"), ns2)
    assert isinstance(ns2.BUILD, str) and "UTC" in ns2.BUILD


def test_the_moor_is_populated_with_undead_and_vermin_and_the_cave_boss_is_a_big_zombie(env):
    lua, ns = env
    kinds = set(str(k) for k in ns.Zone.BESTIARY.keys())
    assert kinds == {"zombie", "ghoul", "quillrat", "bonewalker", "carrion"}
    names = {str(m.name) for a in ("moor", "cave") for m in items(ns.Zone.get(a).monsters)}
    assert {"Rotting Dead", "Hungry Ghoul", "Quill Rat", "Bone Walker", "Carrion Bird"} <= names
    boss = [m for m in items(ns.Zone.get("cave").monsters) if m.boss][0]
    assert boss.model == ns.Zone.BESTIARY.zombie.model and boss.scale == 1.8 and boss.name == "Rottenmaw the Unwelcome"


def test_quill_rats_carry_their_range_and_the_rest_do_not(env):
    lua, ns = env
    for a in ("moor", "cave"):
        for m in items(ns.Zone.get(a).monsters):
            if m.name == "Quill Rat":
                assert m.ranged.range == 210 and m.ranged.cd == pytest.approx(1.7)
            else:
                assert m.ranged is None


def test_every_monster_has_a_model_to_draw(env):
    lua, ns = env
    for a in ("moor", "cave"):
        assert all(isinstance(m.model, int) and m.model > 1000 for m in items(ns.Zone.get(a).monsters))


# ---------------------------------------------------------------- four areas, a second boss
def test_every_exit_leads_to_a_real_area_that_leads_back_and_nothing_overlaps_an_arrival(env):
    lua, ns = env
    for name in ALL_AREAS:
        a = ns.Zone.get(name)
        for ex in items(a.exits):
            dest = ns.Zone.get(ex.to)
            assert dest is not None, f"{name} exits to a missing area {ex.to}"
            back = [e for e in items(dest.exits) if e.to == name]
            assert back, f"{ex.to} has no way back to {name}"
            land = ex.arrive or dest.spawn
            assert 0 < land.x < dest.w and 0 < land.y < dest.h
            assert all(dist(land, e) > e.r + 10 for e in items(dest.exits)), f"you would arrive on an exit in {ex.to}"
            assert all(dist(o, land) > o.r + 10 for o in items(dest.obstacles)), f"you would arrive inside scenery in {ex.to}"


def test_the_areas_are_a_line_each_a_step_harder_than_the_one_before_it(env):
    lua, ns = env
    tiers = [ns.Zone.get(n).tier for n in ("moor", "cave", "fields", "burial")]
    assert tiers == [1, 1.5, 1.9, 2.3]
    assert tiers == sorted(tiers)
    assert ns.Zone.get("moor").exits[2].to == "fields" and ns.Zone.get("fields").exits[2].to == "burial"


def test_the_second_boss_is_a_ranged_caster_who_is_resistant_to_cold_and_pays_a_point(env):
    lua, ns = env
    b = ns.Zone.get("burial")
    bosses = [m for m in items(b.monsters) if m.boss]
    assert len(bosses) == 1 and bosses[0].name == "The Marrowmother" == b.quest.boss
    boss = bosses[0]
    assert boss.ranged.range == 300 and boss.resist.cold == 75 and boss.scale == 1.6
    assert b.quest.id == "burial" and b.quest.reward_points == 1
    guards = [m for m in items(b.monsters) if m.pack == boss.pack and not m.boss]
    assert len(guards) == 3                                                     # she does not come alone
    assert not any(m.boss for m in items(ns.Zone.get("fields").monsters))     # the fields have no boss, only packs


def test_each_quest_is_found_by_its_boss_and_there_are_two(env):
    lua, ns = env
    assert sorted(str(k) for k in ns.Zone.QUESTS.keys()) == ["burial", "den"]
    assert ns.Zone.quest_by_boss("Rottenmaw the Unwelcome").id == "den"
    assert ns.Zone.quest_by_boss("The Marrowmother").id == "burial"
    assert ns.Zone.quest_by_boss("Moor Wolf") is None


def test_the_new_areas_are_bigger_and_more_crowded_as_you_go_on(env):
    lua, ns = env
    n = {a: len(items(ns.Zone.get(a).monsters)) for a in ALL_AREAS}
    assert n["fields"] > n["moor"] > 20 and n["burial"] > 15
    assert ns.Zone.get("fields").w > ns.Zone.get("moor").w


def test_the_cold_ground_and_the_graveyard_use_their_own_art_and_scenery(env):
    lua, ns = env
    for a in ("fields", "burial"):
        f = ns.Zone.get(a).floor
        assert all(isinstance(f[k], int) and f[k] > 1000 for k in ("base", "overlay", "patch"))
    assert ns.Zone.get("fields").floor.base != ns.Zone.get("moor").floor.base
    kinds = lambda a: [d.kind for d in items(ns.Zone.get(a).doodads)]
    assert kinds("fields").count("pine") > 20 and kinds("burial").count("grave") > 30


def test_tougher_tiers_give_more_life_more_bite_and_more_experience(env):
    lua, ns = env
    def entered(tier):
        w = ns.Combat.new(lua.table_from({"seed": 1}))
        area = lua.table_from({"name": "x", "w": 500, "h": 500, "tier": tier, "spawn": lua.table_from({"x": 10, "y": 10}),
                               "monsters": lua.table_from([lua.table_from({"x": 400, "y": 400, "life": 100, "xp": 10, "dmg": lua.table_from([4, 8])})])})
        ns.Combat.enter(w, area)
        return w.monsters[1]
    a, b = entered(1), entered(2.3)
    assert b.life == pytest.approx(a.life * 2.3) and b.xp == pytest.approx(a.xp * 2.3 ** 1.5)           # experience grows faster than the danger
    assert b.dmg[1] == pytest.approx(a.dmg[1] * 1.65) and b.dmg[2] == pytest.approx(a.dmg[2] * 1.65)     # bite grows by half of the extra


def test_the_two_bosses_are_about_the_same_size_of_fight_once_the_area_scaling_is_applied(env):
    lua, ns = env
    def boss_life(area):
        w = ns.Combat.new(lua.table_from({"seed": 1}))
        ns.Combat.enter(w, ns.Zone.get(area))
        return [m.life for m in items(w.monsters) if m.boss][0]
    first, second = boss_life("cave"), boss_life("burial")
    assert first == pytest.approx(260 * 2.0 * 1.5) and second == pytest.approx(150 * 2.0 * 2.3)
    assert 0.8 * first < second < 1.2 * first                                    # she has less life but throws from range and brings guards: the same sort of fight, not a wall
