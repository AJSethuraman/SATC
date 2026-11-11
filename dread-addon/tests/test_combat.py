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
    w = world(env, scorch=1)
    w.player.mana = 0
    run(ns, w, 1.0)
    assert w.player.mana == pytest.approx(1.0, abs=0.02)                 # 1 per second
    w2 = world(env, scorch=1, evocation=1)
    w2.player.mana = 0
    run(ns, w2, 1.0)
    assert w2.player.mana == pytest.approx(1.3, abs=0.02)                # +30% at level 1


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
