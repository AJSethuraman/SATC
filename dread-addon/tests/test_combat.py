"""The fight (Dread/Combat.lua) under plain Lua. Expected numbers are worked by hand in the comments."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"


@pytest.fixture()
def env():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Combat"):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


def world(env, rng=0.5, **points):
    """A fresh world. rng is pinned so every damage roll lands exactly in the middle (0.5) or at the low end (0)."""
    lua, ns = env
    w = ns.Combat.new(lua.table_from({"seed": 1}))
    w.rng = lua.eval(f"function() return {rng} end")
    for k, v in points.items():
        w.player.st.points[k] = v
    return w


def monster(env, w, x, y, life=100, **kw):
    lua, ns = env
    return ns.Combat.add_monster(w, lua.table_from({"x": x, "y": y, "life": life, **kw}))


def run(ns, w, seconds, dt=1 / 60):
    for _ in range(int(round(seconds / dt))):
        ns.Combat.step(w, dt)


def cast(ns, w, sid, x, y):
    r = ns.Combat.cast(w, sid, x, y)
    return (r, None) if isinstance(r, bool) else r


# ---------------------------------------------------------------- casting rules
def test_cannot_cast_what_you_have_no_points_in(env):
    lua, ns = env
    w = world(env)
    assert cast(ns, w, "scorch", 300, 200) == (False, "no points in Scorch")


def test_unknown_and_unimplemented_spells_are_refused_not_ignored(env):
    lua, ns = env
    w = world(env, meteor=1, scorch=1)
    assert cast(ns, w, "nonsense", 0, 0) == (False, "no such skill")
    assert cast(ns, w, "meteor", 300, 200) == (False, "not implemented yet")
    assert w.player.mana == 33            # a refused cast costs nothing


def test_casting_spends_mana_and_runs_dry(env):
    lua, ns = env
    w = world(env, scorch=1)             # costs 3; the player starts with 33
    for _ in range(11):
        assert cast(ns, w, "scorch", 300, 200)[0] is True
    assert w.player.mana == pytest.approx(0)
    assert cast(ns, w, "scorch", 300, 200) == (False, "not enough mana")


def test_mana_comes_back_and_evocation_speeds_it_up(env):
    lua, ns = env
    # 4% of max mana a second: a 33 mana pool regains 1.32 a second. Evocation level 1 is +30% -> 1.716.
    w = world(env, scorch=1)
    w.player.mana = 0
    run(ns, w, 1.0)
    assert w.player.mana == pytest.approx(1.32, abs=0.02)
    w2 = world(env, scorch=1, evocation=1)
    w2.player.mana = 0
    run(ns, w2, 1.0)
    assert w2.player.mana == pytest.approx(1.716, abs=0.02)


def test_regen_grows_with_the_pool(env):
    lua, ns = env
    w = world(env)
    ns.Combat.set_level(w, 11, 0)                        # max mana 33 + 3*10 = 63 -> 2.52 a second
    w.player.mana = 0
    run(ns, w, 1.0)
    assert w.player.mana == pytest.approx(2.52, abs=0.03)


# ---------------------------------------------------------------- a bolt in flight
def test_a_bolt_flies_and_hits(env):
    lua, ns = env
    w = world(env, scorch=1)
    m = monster(env, w, 300, 200, life=50)
    cast(ns, w, "scorch", 300, 200)
    assert m.life == 50                                   # nothing happens until it arrives
    run(ns, w, 1.0)
    assert m.life == pytest.approx(42.0)                  # Scorch level 1 = 6..10, middle roll 8
    assert len(w.projectiles) == 0                        # and the bolt is used up


def test_a_bolt_that_misses_flies_off_and_vanishes(env):
    lua, ns = env
    w = world(env, scorch=1)
    m = monster(env, w, 100, 200, life=50)                # off to the side of the shot
    cast(ns, w, "scorch", 300, 400)
    run(ns, w, 3.0)
    assert m.life == 50 and len(w.projectiles) == 0


def test_resists_apply_in_the_fight(env):
    lua, ns = env
    w = world(env, scorch=1)
    immune = monster(env, w, 300, 120, life=50, resist=lua.table_from({"fire": 100, "cold": 0, "lightning": 0}))
    cast(ns, w, "scorch", 300, 120)
    run(ns, w, 1.0)
    assert immune.life == 50                              # fire immune: no damage
    w2 = world(env, scorch=1)
    half = monster(env, w2, 300, 120, life=50, resist=lua.table_from({"fire": 50, "cold": 0, "lightning": 0}))
    cast(ns, w2, "scorch", 300, 120)
    run(ns, w2, 1.0)
    assert half.life == pytest.approx(46.0)               # 8 damage, half resisted


def test_synergy_reaches_the_fight(env):
    lua, ns = env
    # Scorch level 1 with 2 points in Fireball: +14% x 2 = +28%. Middle roll 8 -> 10.24.
    w = world(env, scorch=1, fireball=2)
    m = monster(env, w, 300, 120, life=50)
    cast(ns, w, "scorch", 300, 120)
    run(ns, w, 1.0)
    assert m.life == pytest.approx(50 - 10.24)


def test_fire_mastery_reaches_the_fight_and_cold_pierce_beats_resist(env):
    lua, ns = env
    w = world(env, frostbolt=1, piercing_cold=1)          # pierce 20: a 50% resist becomes 30%
    m = monster(env, w, 300, 120, life=50, resist=lua.table_from({"fire": 0, "cold": 50, "lightning": 0}))
    cast(ns, w, "frostbolt", 300, 120)
    run(ns, w, 1.0)
    assert m.life == pytest.approx(50 - 6.5 * 0.7)        # Frostbolt 5..8 middle = 6.5, x0.7


# ---------------------------------------------------------------- statuses
def test_chill_slows_a_monster(env):
    lua, ns = env
    w = world(env, frostbolt=1)
    m = monster(env, w, 300, 120, life=200, speed=60)
    cast(ns, w, "frostbolt", 300, 120)
    run(ns, w, 0.5)
    assert m.chill > 0 and m.chill_pct == 25
    # a chilled monster 300 away moves at 60 * (1 - 0.25) = 45 per second
    far = monster(env, w, 300, 400, life=200, speed=60)
    far.chill, far.chill_pct = 3, 25
    y0 = far.y
    run(ns, w, 1.0)
    assert y0 - far.y == pytest.approx(45.0, abs=1.5)


def test_freeze_stops_a_monster_when_the_chance_lands(env):
    lua, ns = env
    w = world(env, rng=0, ice_lance=1)                    # rng 0 always lands the 10% chance
    m = monster(env, w, 300, 120, life=200, speed=60)
    cast(ns, w, "ice_lance", 300, 120)
    run(ns, w, 0.4)
    assert m.freeze > 0
    x0, y0 = m.x, m.y
    run(ns, w, 0.5)
    assert (m.x, m.y) == (x0, y0)
    w2 = world(env, rng=0.99, ice_lance=1)                # 0.99 never does
    m2 = monster(env, w2, 300, 120, life=200)
    cast(ns, w2, "ice_lance", 300, 120)
    run(ns, w2, 0.4)
    assert m2.freeze <= 0


# ---------------------------------------------------------------- area spells
def test_frost_nova_hits_only_what_is_in_range(env):
    lua, ns = env
    w = world(env, rng=0, frost_nova=1)
    near = monster(env, w, 300, 100, life=20, speed=0)    # 60 away, inside 90 + its own size
    far = monster(env, w, 300, 240, life=20, speed=0)     # 200 away
    cast(ns, w, "frost_nova", 0, 0)
    assert near.life == pytest.approx(16.0)               # Frost Nova level 1 low roll = 4
    assert far.life == 20


def test_fireball_explodes_on_contact_and_the_blast_spreads(env):
    lua, ns = env
    w = world(env, rng=0, fireball=1)
    a = monster(env, w, 300, 200, life=100, speed=0)
    b = monster(env, w, 340, 200, life=100, speed=0)      # 40 from the impact: inside the blast
    c = monster(env, w, 300, 400, life=100, speed=0)      # well outside it
    cast(ns, w, "fireball", 300, 200)
    run(ns, w, 1.0)
    assert a.life == pytest.approx(70.0) and b.life == pytest.approx(70.0)       # Fireball level 1 low roll = 30
    assert c.life == 100


# ---------------------------------------------------------------- killing, levelling, dying
def test_a_kill_gives_experience_and_a_level_refills_you(env):
    lua, ns = env
    w = world(env, rng=0.5, scorch=1)
    w.player.life, w.player.mana = 10, 5
    m = monster(env, w, 300, 120, life=1, xp=10, speed=0)
    cast(ns, w, "scorch", 300, 120)
    run(ns, w, 1.0)
    assert m.dead is True
    assert w.player.level == 2 and w.player.xp == 0                  # level 1 needs 1*1*10 = 10
    assert w.player.life == w.player.maxlife == 66 and w.player.mana == w.player.maxmana == 36
    assert ns.Tree.points_total(w.player.st) == 2                    # and that is a new skill point


def test_a_monster_bites_on_a_timer_and_you_can_die(env):
    lua, ns = env
    w = world(env, scorch=1)
    monster(env, w, 300, 50, life=100, dmg=lua.table_from([5, 5]), speed=0)      # 10 away: in reach
    run(ns, w, 0.1)
    assert w.player.life == 55                                        # first bite lands at once
    run(ns, w, 0.5)
    assert w.player.life == 55                                        # then it has to wait
    run(ns, w, 0.6)
    assert w.player.life == 50                                        # one second later, the next bite
    w.player.life = 3
    run(ns, w, 1.1)
    assert w.over is True and w.player.life == 0
    assert cast(ns, w, "scorch", 300, 200) == (False, "you are dead")


# ---------------------------------------------------------------- walking
def test_click_to_move_walks_there_and_stops(env):
    lua, ns = env
    w = world(env)
    ns.Combat.move_to(w, 300, 110)                                    # 70 away at 140 a second = 0.5 s
    run(ns, w, 0.25)
    assert w.player.y == pytest.approx(75.0, abs=0.5) and w.player.ty == 110
    run(ns, w, 0.5)
    assert w.player.y == 110 and w.player.ty is None


def test_same_seed_same_fight(env):
    lua, ns = env
    out = []
    for _ in range(2):
        lua2 = lupa.LuaRuntime(unpack_returned_tuples=True)
        ns2 = lua2.table()
        ld = lua2.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
        for f in ("Sim", "Skills", "Tree", "Combat"):
            ld(str(DREAD / f"{f}.lua"), ns2)
        w = ns2.Combat.new(lua2.table_from({"seed": 7}))
        w.player.st.points["scorch"] = 3
        ns2.Combat.add_monster(w, lua2.table_from({"x": 300, "y": 200, "life": 500, "speed": 0}))
        ns2.Combat.cast(w, "scorch", 300, 200)
        for _ in range(120):
            ns2.Combat.step(w, 1 / 60)
        out.append(w.monsters[1].life)
    assert out[0] == out[1]


def test_a_bolt_stops_at_the_end_of_its_range_inside_the_arena(env):
    lua, ns = env
    w = world(env, scorch=1)
    w.h = 2000                                                        # big enough that the wall is not what stops it
    far = monster(env, w, 300, 700, life=50, speed=0)                 # 660 away; Scorch reaches 420
    cast(ns, w, "scorch", 300, 1900)
    run(ns, w, 0.5)
    assert len(w.projectiles) == 1                                    # still flying at 160 units
    run(ns, w, 1.5)
    assert len(w.projectiles) == 0 and far.life == 50


def test_a_dead_monster_does_not_bite(env):
    lua, ns = env
    w = world(env, scorch=1)
    m = monster(env, w, 300, 50, life=100, dmg=lua.table_from([5, 5]), speed=0)
    m.dead = True
    run(ns, w, 3.0)
    assert w.player.life == 60


# ---------------------------------------------------------------- saving
def test_snapshot_round_trip(env):
    lua, ns = env
    w = world(env, scorch=3, fireball=2)
    ns.Combat.set_level(w, 9, 25)
    snap = ns.Combat.snapshot(w)
    w2 = world(env)
    assert ns.Combat.restore(w2, snap) is True
    assert w2.player.level == 9 and w2.player.xp == 25
    assert w2.player.st.points["scorch"] == 3 and w2.player.st.points["fireball"] == 2
    assert w2.player.maxlife == 60 + 6 * 8 and w2.player.life == w2.player.maxlife


def test_restore_does_not_trust_a_hand_edited_save(env):
    lua, ns = env
    w = world(env)
    bad = lua.table_from({"level": 3, "xp": 0, "points": lua.table_from({"scorch": 99, "made_up": 5, "frostbolt": -2})})
    ns.Combat.restore(w, bad)
    st = w.player.st
    assert st.points["scorch"] == 3                 # only 3 points exist at level 3, however many the file claims
    assert st.points["made_up"] is None and st.points["frostbolt"] is None
    assert ns.Tree.points_spent(st) <= ns.Tree.points_total(st)
    assert ns.Combat.restore(w, "garbage") is False


# ---------------------------------------------------------------- what the screen is told
def kinds(ns, w):
    ev = ns.Combat.drain(w)
    return [ev[i].k for i in range(1, len(ev) + 1)], ev


def test_events_report_hits_blasts_kills_and_levels(env):
    lua, ns = env
    w = world(env, rng=0, fireball=1)
    monster(env, w, 300, 200, life=1, xp=10, speed=0)
    cast(ns, w, "fireball", 300, 200)
    run(ns, w, 1.0)
    ks, ev = kinds(ns, w)
    assert ks.count("blast") == 1 and ks.count("hit") == 1 and ks.count("kill") == 1 and ks.count("level") == 1
    hit = [ev[i] for i in range(1, len(ev) + 1) if ev[i].k == "hit"][0]
    assert hit.dmg == pytest.approx(30.0) and hit.x == 300 and hit.y == 200


def test_draining_empties_the_list(env):
    lua, ns = env
    w = world(env, scorch=1)
    monster(env, w, 300, 120, life=50, speed=0)
    cast(ns, w, "scorch", 300, 120)
    run(ns, w, 1.0)
    assert len(kinds(ns, w)[0]) >= 1
    assert kinds(ns, w)[0] == []


# ---------------------------------------------------------------- the free attack
def test_the_wand_is_free_and_has_a_cooldown(env):
    lua, ns = env
    w = world(env)                                           # no skill points at all
    m = monster(env, w, 300, 120, life=50, speed=0)
    assert cast(ns, w, "wand", 300, 120) == (False, "no such skill")      # it is not a spell
    r = ns.Combat.attack(w, 300, 120)
    assert r is True and w.player.mana == 33                 # costs nothing
    assert ns.Combat.attack(w, 300, 120) == (False, "cooling down")
    run(ns, w, 1.0)
    assert m.life == pytest.approx(50 - 4.5)                 # level 1 wand = 3..6, middle roll 4.5
    assert ns.Combat.attack(w, 300, 120) is True             # ready again after 0.7 s


def test_wand_damage_grows_with_level(env):
    lua, ns = env
    lo, hi = ns.Combat.wand_damage(1)
    lo10, hi10 = ns.Combat.wand_damage(10)
    assert (lo, hi) == (3, 6) and (lo10, hi10) == (12, 24)


def test_physical_resist_applies_to_the_wand(env):
    lua, ns = env
    w = world(env)
    m = monster(env, w, 300, 120, life=50, speed=0, resist=lua.table_from({"fire": 0, "cold": 0, "lightning": 0, "physical": 50}))
    ns.Combat.attack(w, 300, 120)
    run(ns, w, 1.0)
    assert m.life == pytest.approx(50 - 2.25)


# ---------------------------------------------------------------- globes
def test_a_kill_can_drop_a_globe_and_walking_over_it_restores_35_percent(env):
    lua, ns = env
    w = world(env, rng=0)                                    # rng 0: always drops, always a mana globe
    w.player.mana = 0
    monster(env, w, 300, 60, life=1, speed=0)                # dies next to the player
    ns.Combat.attack(w, 300, 60)
    run(ns, w, 0.3)
    ks, ev = kinds(ns, w)
    assert "drop" in ks and "pickup" in ks                   # it landed within pickup range and was collected
    assert w.player.mana > 0.3 * w.player.maxmana            # 35% of 36 (it levelled up) plus a little regen
    assert len(w.drops) == 0


def test_a_globe_out_of_reach_waits_then_expires(env):
    lua, ns = env
    w = world(env)
    w.drops[1] = lua.table_from({"kind": "life", "x": 500, "y": 300, "t": 25})
    run(ns, w, 10)
    assert len(w.drops) == 1                                 # still there
    run(ns, w, 16)
    assert len(w.drops) == 0                                 # gone after 25 s


# ---------------------------------------------------------------- waking up
def test_monsters_sleep_until_you_come_close(env):
    lua, ns = env
    w = world(env)
    m = monster(env, w, 300, 360, life=50, speed=60, aggro=150)        # 320 away, notices at 150
    run(ns, w, 2.0)
    assert m.awake is False and m.y == 360
    ns.Combat.move_to(w, 300, 260)
    run(ns, w, 2.0)
    assert m.awake is True and m.y < 360


def test_waking_one_wakes_its_pack(env):
    lua, ns = env
    w = world(env)
    a = monster(env, w, 300, 150, life=50, speed=0, aggro=200, pack=1)         # 110 from the player: notices
    b = monster(env, w, 900, 900, life=50, speed=0, aggro=50, pack=1)          # far away, same pack
    c = monster(env, w, 900, 800, life=50, speed=0, aggro=50, pack=2)          # far away, another pack
    run(ns, w, 0.1)
    assert a.awake is True and b.awake is True and c.awake is False


def test_being_hit_wakes_a_sleeping_monster(env):
    lua, ns = env
    w = world(env, scorch=1)
    m = monster(env, w, 300, 360, life=200, speed=60, aggro=10, pack=7)
    cast(ns, w, "scorch", 300, 360)
    run(ns, w, 1.5)
    assert m.awake is True


# ---------------------------------------------------------------- trees and rocks
def test_you_cannot_walk_through_a_tree_but_you_do_get_round_it(env):
    lua, ns = env
    w = world(env)
    tree = (300, 120, 20)
    w.obstacles[1] = lua.table_from({"x": tree[0], "y": tree[1], "r": tree[2]})
    ns.Combat.move_to(w, 300, 250)                           # straight through it
    closest = 1e9
    for _ in range(360):
        ns.Combat.step(w, 1 / 60)
        closest = min(closest, ((w.player.x - 300) ** 2 + (w.player.y - 120) ** 2) ** 0.5)
    assert closest >= 20 + 10 - 0.5                          # never inside the trunk (tree + the player's own size)
    assert w.player.y == pytest.approx(250, abs=0.5)         # and it still got to the clicked spot


def test_monsters_go_round_trees_too(env):
    lua, ns = env
    w = world(env)
    w.obstacles[1] = lua.table_from({"x": 300, "y": 200, "r": 30})
    m = monster(env, w, 300, 300, life=50, speed=80)
    closest = 1e9
    for _ in range(240):                                     # watch every step, not just where it ends up
        ns.Combat.step(w, 1 / 60)
        closest = min(closest, ((m.x - 300) ** 2 + (m.y - 200) ** 2) ** 0.5)
    assert closest >= 30 + 12 * 0.6 - 0.5                    # never inside the trunk
    assert m.y < 200                                         # and it did get past, to the player


# ---------------------------------------------------------------- areas, quests, events
def test_entering_an_area_swaps_the_map_and_monsters_and_copies_them(env):
    lua, ns = env
    w = world(env)
    area = lua.table_from({"name": "cave", "w": 900, "h": 700,
                           "spawn": lua.table_from({"x": 50, "y": 350}),
                           "obstacles": lua.table_from([lua.table_from({"x": 400, "y": 300, "r": 20})]),
                           "monsters": lua.table_from([lua.table_from({"x": 800, "y": 350, "life": 40, "resist": lua.table_from({"fire": 10, "cold": 0, "lightning": 0})})])})
    monster(env, w, 1, 1, life=5)
    ns.Combat.enter(w, area)
    assert w.area == "cave" and w.w == 900 and w.player.x == 50 and w.player.y == 350
    assert len(w.monsters) == 1 and w.monsters[1].life == 40 and w.monsters[1].awake is False
    w.monsters[1].life = 1
    w.monsters[1].resist.fire = 99
    assert area.monsters[1].life == 40 and area.monsters[1].resist.fire == 10     # the area itself is untouched


def test_quest_points_and_flags_survive_a_save(env):
    lua, ns = env
    w = world(env)
    ns.Combat.set_level(w, 5, 0)
    w.player.st.quest_points = 1
    w.flags.den = True
    snap = ns.Combat.snapshot(w)
    w2 = world(env)
    ns.Combat.restore(w2, snap)
    assert w2.player.st.quest_points == 1 and w2.flags.den is True
    assert ns.Tree.points_total(w2.player.st) == 6                         # level 5 + 1 quest point


def test_a_hand_edited_save_cannot_claim_unlimited_quest_points(env):
    lua, ns = env
    w = world(env)
    ns.Combat.restore(w, lua.table_from({"level": 1, "quest_points": 500, "flags": lua.table_from({"den": True, "x": "yes"})}))
    assert w.player.st.quest_points == 12 and w.flags.den is True and w.flags.x is None


def test_events_for_cast_and_bite(env):
    lua, ns = env
    w = world(env, scorch=1)
    monster(env, w, 300, 50, life=500, speed=0, dmg=lua.table_from([1, 1]))       # 10 away and healthy: it bites
    cast(ns, w, "scorch", 300, 50)
    run(ns, w, 0.1)
    ks, ev = kinds(ns, w)
    assert "cast" in ks and "bite" in ks and "hit" in ks


def test_killing_a_boss_says_so(env):
    lua, ns = env
    w = world(env, scorch=1)
    monster(env, w, 300, 120, life=1, speed=0, boss=True, name="Big One")
    monster(env, w, 400, 120, life=1, speed=0, name="Small One")
    cast(ns, w, "scorch", 300, 120)
    run(ns, w, 1.0)
    ks, ev = kinds(ns, w)
    boss = [ev[i] for i in range(1, len(ev) + 1) if ev[i].k == "boss_dead"]
    assert len(boss) == 1 and boss[0].name == "Big One"       # the ordinary kill does not announce itself as a boss


# ---------------------------------------------------------------- area spells land where you click
def first_blast(ns, w):
    ev = ns.Combat.drain(w)
    blasts = [ev[i] for i in range(1, len(ev) + 1) if ev[i].k == "blast"]
    return blasts[0] if blasts else None


def test_a_fireball_cast_at_empty_ground_explodes_there_not_at_full_range(env):
    lua, ns = env
    w = world(env, fireball=1)                                           # player at (300, 40); nothing to hit
    cast(ns, w, "fireball", 300, 200)                                    # 160 away; the spell's range is 440
    run(ns, w, 2.0)
    b = first_blast(ns, w)
    assert b is not None and b.x == pytest.approx(300, abs=0.5) and b.y == pytest.approx(200, abs=6)    # one step of 5 units, no more


def test_a_fireball_aimed_past_its_range_explodes_at_its_range(env):
    lua, ns = env
    w = world(env, fireball=1)
    w.h = 2000
    cast(ns, w, "fireball", 300, 1900)                                   # far beyond 440
    run(ns, w, 3.0)
    b = first_blast(ns, w)
    assert b is not None and b.y == pytest.approx(40 + 440, abs=6)


def test_glacial_spike_also_lands_on_the_click(env):
    lua, ns = env
    w = world(env, glacial_spike=1)
    cast(ns, w, "glacial_spike", 300, 150)
    run(ns, w, 2.0)
    b = first_blast(ns, w)
    assert b is not None and b.y == pytest.approx(150, abs=7)


def test_a_bolt_still_flies_past_the_click_point(env):
    lua, ns = env
    w = world(env, scorch=1)
    cast(ns, w, "scorch", 300, 100)                                      # 60 away
    run(ns, w, 0.5)                                                      # 160 units flown: well past 100
    assert len(w.projectiles) == 1 and w.projectiles[1].y > 150          # bolts are not aimed at a point, only a direction
    assert first_blast(ns, w) is None
