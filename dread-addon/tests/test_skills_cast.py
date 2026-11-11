"""Every active skill does its own thing. Expected numbers are worked by hand in the comments; damage rolls are pinned
(rng 0 = the low end of each range) so the arithmetic is exact."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"


@pytest.fixture()
def env():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Items", "Combat"):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


def world(env, rng=0, **points):
    lua, ns = env
    w = ns.Combat.new(lua.table_from({"seed": 1, "w": 2000, "h": 2000}))
    w.rng = lua.eval(f"function() return {rng} end")
    for k, v in points.items():
        w.player.st.points[k] = v
    w.player.mana = w.player.maxmana = 500
    w.player.life = w.player.maxlife = 500
    return w


def mon(env, w, x, y, life=1000, **kw):
    lua, ns = env
    kw.setdefault("speed", 0)
    kw.setdefault("dmg", lua.table_from([0, 0]))
    return ns.Combat.add_monster(w, lua.table_from({"x": x, "y": y, "life": life, **kw}))


def run(ns, w, seconds, dt=1 / 60):
    for _ in range(int(round(seconds / dt))):
        ns.Combat.step(w, dt)


def cast(ns, w, sid, x, y):
    r = ns.Combat.cast(w, sid, x, y)
    return (r, None) if isinstance(r, bool) else r


def events(ns, w, kind):
    ev = ns.Combat.drain(w)
    return [ev[i] for i in range(1, len(ev) + 1) if ev[i].k == kind]


def lost(m):
    return m.maxlife - m.life


# ---------------------------------------------------------------- the whole list
ACTIVE = ["scorch", "dragons_breath", "blazing_speed", "fireball", "flamestrike", "combustion", "meteor", "flame_spirit",
          "frostbolt", "ice_barrier", "frost_nova", "ice_lance", "frost_armor", "glacial_spike", "blizzard", "icicle_cloak", "frozen_orb",
          "arcing_bolts", "static_shock", "force_pull", "thunder_nova", "lightning_bolt", "chain_lightning", "blink", "storm_cloud", "mana_shield"]
ALWAYS_ON = ["evocation", "master_of_flame", "piercing_cold", "conductor"]


def test_every_skill_is_either_castable_or_always_on(env):
    lua, ns = env
    ids = [ns.Skills[i].id for i in range(1, 31)]
    assert sorted(ids) == sorted(ACTIVE + ALWAYS_ON)
    for sid in ACTIVE:
        assert ns.Combat.SHAPES[sid] is not None, f"{sid} has no behaviour"
    for sid in ALWAYS_ON:
        assert ns.Combat.SHAPES[sid] is None and ns.Skills.byId[sid].kind in ("passive", "mastery")


@pytest.mark.parametrize("sid", ACTIVE)
def test_each_active_skill_casts_spends_mana_and_survives_twelve_seconds_of_play(env, sid):
    lua, ns = env
    w = world(env, **{sid: 1})
    w.player.x, w.player.y = 300, 300
    mon(env, w, 450, 300, life=5000, speed=40, dmg=lua.table_from([1, 2]))
    mon(env, w, 600, 420, life=5000, speed=40, dmg=lua.table_from([1, 2]))
    mana = w.player.mana
    r = cast(ns, w, sid, 450, 300)
    assert r[0] is True
    assert w.player.mana == pytest.approx(mana - ns.Tree.mana_cost(w.player.st, sid))
    assert len(events(ns, w, "cast")) == 1
    run(ns, w, 12)                                                       # nothing errors, whatever it does
    ns.Combat.cast(w, sid, 500, 320)


# ---------------------------------------------------------------- fire
def test_arcing_bolts_fires_a_spread_of_three(env):
    lua, ns = env
    w = world(env, arcing_bolts=1)
    cast(ns, w, "arcing_bolts", 600, 40)                                 # due east of (300, 40)
    vys = sorted(w.projectiles[i].vy for i in range(1, 4))
    assert len(list(w.projectiles.keys())) == 3
    assert vys[1] == pytest.approx(0, abs=1e-6) and vys[0] == pytest.approx(-vys[2]) and vys[2] == pytest.approx(380 * 0.2182, abs=1)   # sin(0.22) x 380


def test_chain_lightning_jumps_to_neighbours_in_range_but_not_beyond(env):
    lua, ns = env
    w = world(env, chain_lightning=1)                                    # level 1 = 8..40, pinned to 8
    a, b, c, d = (mon(env, w, 300, y) for y in (120, 220, 330, 600))     # gaps of 100, 110, 270 (jump range is 150)
    cast(ns, w, "chain_lightning", 300, 120)
    run(ns, w, 1.0)
    assert [lost(m) for m in (a, b, c, d)] == [pytest.approx(8), pytest.approx(8), pytest.approx(8), 0]
    assert len(events(ns, w, "zap")) == 2


def test_dragons_breath_burns_a_cone_in_front_for_a_second(env):
    lua, ns = env
    w = world(env, dragons_breath=1)                                     # 4..8, pinned to 4 a tick; a tick every 0.2 s for 1 s
    w.player.x, w.player.y = 300, 200
    ahead, behind, side, far = mon(env, w, 300, 280), mon(env, w, 300, 120), mon(env, w, 400, 200), mon(env, w, 300, 420)
    cast(ns, w, "dragons_breath", 300, 400)                              # north
    run(ns, w, 1.5)
    assert 20 <= lost(ahead) <= 24                                       # 5 or 6 ticks of 4
    assert lost(behind) == 0 and lost(side) == 0 and lost(far) == 0
    assert len(list(w.effects.keys())) == 0                              # and it is over


def test_blazing_speed_is_faster_and_leaves_burning_ground(env):
    lua, ns = env
    w = world(env, blazing_speed=1)                                      # +20% for 6 s
    cast(ns, w, "blazing_speed", 0, 0)
    assert w.player.buffs.blazing_speed.pct == 20
    pit = mon(env, w, 400, 40)                                           # on the way
    ns.Combat.move_to(w, 700, 40)
    run(ns, w, 1.0)
    assert w.player.x == pytest.approx(300 + 140 * 1.2, abs=1.5)         # 168 units in a second instead of 140
    trail = [e for e in w.effects.values() if e.id == "blazing_speed"]
    assert len(trail) >= 4
    assert lost(pit) > 0                                                 # the monster in the path was burned
    run(ns, w, 7)
    assert w.player.buffs.blazing_speed is None and len(list(w.effects.keys())) == 0


def test_flamestrike_burns_the_chosen_ground_for_four_seconds(env):
    lua, ns = env
    w = world(env, flamestrike=1)                                        # 10..18, pinned to 10 a tick, every 0.5 s
    inside, outside = mon(env, w, 300, 230), mon(env, w, 300, 330)       # zone at (300, 200), radius 70
    cast(ns, w, "flamestrike", 300, 200)
    run(ns, w, 5.0)
    assert 70 <= lost(inside) <= 90 and lost(outside) == 0               # 8 or 9 ticks
    assert len(list(w.effects.keys())) == 0


def test_flamestrike_aimed_too_far_lands_at_its_range(env):
    lua, ns = env
    w = world(env, flamestrike=1)
    cast(ns, w, "flamestrike", 300, 1800)
    assert w.effects[1].y == pytest.approx(40 + 440, abs=0.01)


def test_combustion_boosts_fire_damage_only_and_wears_off(env):
    lua, ns = env
    w = world(env, rng=0.5, combustion=1, scorch=1, frostbolt=1)         # +20% at level 1
    cast(ns, w, "combustion", 0, 0)
    assert w.player.buffs.combustion.pct == 20
    fire, ice = mon(env, w, 300, 130), mon(env, w, 330, 130)
    cast(ns, w, "scorch", 300, 130)
    run(ns, w, 1.0)
    assert lost(fire) == pytest.approx(8 * 1.2)                          # Scorch 6..10 middle 8, x1.2
    cast(ns, w, "frostbolt", 330, 130)
    run(ns, w, 1.0)
    assert lost(ice) == pytest.approx(6.5)                               # cold is untouched
    run(ns, w, 10)
    assert w.player.buffs.combustion is None


def test_meteor_falls_after_a_second_then_the_ground_burns(env):
    lua, ns = env
    w = world(env, meteor=1)                                             # 60..90 pinned to 60; burning ground a quarter of that
    m = mon(env, w, 300, 200)
    cast(ns, w, "meteor", 300, 200)
    run(ns, w, 0.5)
    assert lost(m) == 0 and len(events(ns, w, "blast")) == 0             # nothing yet: it is still falling
    run(ns, w, 0.6)
    assert lost(m) >= 60 and len(events(ns, w, "blast")) == 1
    run(ns, w, 3.5)
    assert 60 + 3 * 15 <= lost(m) <= 60 + 7 * 15                         # and the ground burned for 3 s
    assert len(list(w.effects.keys())) == 0


def test_flame_spirit_shoots_the_nearest_monster_and_only_one_exists(env):
    lua, ns = env
    w = world(env, flame_spirit=1)                                       # 10..16 pinned to 10, a shot every 0.8 s
    near, far = mon(env, w, 300, 300), mon(env, w, 300, 700)
    cast(ns, w, "flame_spirit", 300, 150)                                # placed 110 away; reaches 260
    run(ns, w, 2.5)
    assert lost(near) >= 30 and lost(far) == 0
    cast(ns, w, "flame_spirit", 320, 150)
    run(ns, w, 0.1)
    assert len([e for e in w.effects.values() if e.kind == "summon"]) == 1       # the new one replaced the old
    run(ns, w, 16)
    assert len(list(w.effects.keys())) == 0


def test_flame_spirit_ignores_monsters_beyond_its_reach(env):
    lua, ns = env
    w = world(env, flame_spirit=1)
    far = mon(env, w, 300, 700)                                          # 550 from the spirit; it reaches 260
    cast(ns, w, "flame_spirit", 300, 150)
    run(ns, w, 3.0)
    assert lost(far) == 0


# ---------------------------------------------------------------- cold
def bite_world(env, **points):
    lua, ns = env
    w = world(env, **points)
    biter = mon(env, w, 300, 50, life=500, dmg=lua.table_from([10, 10]))        # 10 away: bites at once, then every ~1 s
    return w, biter


def test_ice_barrier_soaks_exactly_its_amount_then_breaks(env):
    lua, ns = env
    w, biter = bite_world(env, ice_barrier=1)
    biter.dmg = lua.table_from([5, 5])
    cast(ns, w, "ice_barrier", 0, 0)
    assert w.player.buffs.ice_barrier.amount == 40
    run(ns, w, 0.1)
    assert w.player.life == 500 and w.player.buffs.ice_barrier.amount == 35
    run(ns, w, 7.8)                                                      # eight bites of 5 = 40: all soaked
    assert w.player.life == 500 and w.player.buffs.ice_barrier is None
    run(ns, w, 0.4)                                                      # the ninth gets through
    assert w.player.life == 495


def test_frost_armor_cuts_damage_and_chills_the_attacker(env):
    lua, ns = env
    w, biter = bite_world(env, frost_armor=1)
    cast(ns, w, "frost_armor", 0, 0)
    run(ns, w, 0.1)
    assert w.player.life == pytest.approx(500 - 10 * 0.85)               # 15% off a bite of 10
    assert biter.chill > 0 and biter.chill_pct == 40


def test_icicle_cloak_hurts_whatever_bites_you(env):
    lua, ns = env
    w, biter = bite_world(env, icicle_cloak=1)                           # 10..16 pinned to 10
    cast(ns, w, "icicle_cloak", 0, 0)
    run(ns, w, 0.1)
    assert lost(biter) == pytest.approx(10) and w.player.life == 490


def test_blizzard_chills_and_damages_the_area_for_five_seconds(env):
    lua, ns = env
    w = world(env, blizzard=1)                                           # 25..40 pinned to 25, every 0.4 s
    m, out = mon(env, w, 300, 220), mon(env, w, 300, 400)
    cast(ns, w, "blizzard", 300, 200)
    run(ns, w, 1.0)
    assert m.chill > 0 and m.chill_pct == 35 and out.chill == 0
    run(ns, w, 4.5)
    assert 25 * 11 <= lost(m) <= 25 * 14 and lost(out) == 0
    assert len(list(w.effects.keys())) == 0


def test_frozen_orb_rolls_toward_the_target_hurting_what_it_passes(env):
    lua, ns = env
    w = world(env, frozen_orb=1)                                         # 40..60 pinned to 40, x0.35 = 14 a tick, every 0.3 s
    m, out = mon(env, w, 300, 340), mon(env, w, 900, 40)
    cast(ns, w, "frozen_orb", 300, 340)                                  # 300 away at 160 a second
    run(ns, w, 1.0)
    assert w.effects[1].y == pytest.approx(40 + 160, abs=2) and lost(m) == 0
    run(ns, w, 1.8)
    assert lost(m) >= 14 * 2 and lost(out) == 0
    run(ns, w, 1.0)
    assert len(list(w.effects.keys())) == 0


def test_frost_nova_now_chills_what_it_hits(env):
    lua, ns = env
    w = world(env, frost_nova=1)
    m = mon(env, w, 300, 100)
    cast(ns, w, "frost_nova", 0, 0)
    assert m.chill > 0 and m.chill_pct == 40


# ---------------------------------------------------------------- lightning
def test_static_shock_takes_a_share_of_current_life_but_never_kills(env):
    lua, ns = env
    w = world(env, static_shock=1)                                       # 25%
    a = mon(env, w, 400, 40, life=100)
    boss = mon(env, w, 300, 140, life=120, boss=True)                    # bosses lose a third of the share
    frail = mon(env, w, 300, 40 + 60, life=1.5)
    out = mon(env, w, 900, 40, life=100)
    cast(ns, w, "static_shock", 0, 0)
    assert a.life == pytest.approx(75) and boss.life == pytest.approx(120 - 120 * 0.25 / 3)
    assert frail.life == pytest.approx(1.5 - 0.375) and frail.life > 0 and out.life == 100


def test_static_shock_cannot_finish_a_monster(env):
    lua, ns = env
    w = world(env, static_shock=1)                                       # 25% of 1.2 = 0.3, but only 0.2 may be taken
    m = mon(env, w, 300, 100, life=1.2)
    cast(ns, w, "static_shock", 0, 0)
    assert m.life == pytest.approx(1.0) and m.dead is None


def test_force_pull_fetches_globes_and_throws_back_what_is_close(env):
    lua, ns = env
    w = world(env, force_pull=1)
    w.drops[1] = lua.table_from({"kind": "mana", "x": 550, "y": 40, "t": 25})
    near, far = mon(env, w, 360, 40), mon(env, w, 900, 40)
    cast(ns, w, "force_pull", 0, 0)
    assert w.drops[1].x == w.player.x and w.drops[1].y == w.player.y     # the globe came to you
    assert near.x == pytest.approx(360 + 90) and near.freeze == pytest.approx(0.6)
    assert far.x == 900 and far.freeze <= 0


def test_blink_moves_you_there_clamps_to_range_and_respects_trees(env):
    lua, ns = env
    w = world(env, blink=1)
    ns.Combat.move_to(w, 900, 40)
    cast(ns, w, "blink", 500, 40)
    assert w.player.x == pytest.approx(500) and w.player.tx is None      # and you stop walking
    assert len(events(ns, w, "blink")) == 1
    cast(ns, w, "blink", 1500, 40)                                       # 1000 away; the range is 360
    assert w.player.x == pytest.approx(500 + 360)
    w.obstacles[1] = lua.table_from({"x": 1000, "y": 40, "r": 20})
    cast(ns, w, "blink", 1000, 40)                                       # straight into a tree
    assert ((w.player.x - 1000) ** 2 + (w.player.y - 40) ** 2) ** 0.5 >= 20 + 10 - 0.01


def test_storm_cloud_strikes_things_near_you_for_eight_seconds(env):
    lua, ns = env
    w = world(env, storm_cloud=1)                                        # 10..40 pinned to 10, a strike every 0.6 s
    far, near = mon(env, w, 800, 40), mon(env, w, 400, 40)               # radius 170; the far one is listed first
    cast(ns, w, "storm_cloud", 0, 0)
    run(ns, w, 8.6)
    assert 100 <= lost(near) <= 160 and lost(far) == 0
    assert len(events(ns, w, "zap")) >= 10 and len(list(w.effects.keys())) == 0


def test_mana_shield_takes_a_share_of_damage_from_mana_and_toggles(env):
    lua, ns = env
    ns.Combat.MANA_REGEN = 0                                             # so only the shield moves the mana
    w, biter = bite_world(env, mana_shield=1)
    cast(ns, w, "mana_shield", 0, 0)
    assert w.player.buffs.mana_shield.pct == 30
    mana = w.player.mana
    run(ns, w, 0.1)
    assert w.player.life == pytest.approx(500 - 7) and w.player.mana == pytest.approx(mana - 3)           # 30% of 10 from mana
    cast(ns, w, "mana_shield", 0, 0)
    assert w.player.buffs.mana_shield is None                            # the same key turns it off


def test_mana_shield_does_nothing_with_no_mana_left(env):
    lua, ns = env
    ns.Combat.MANA_REGEN = 0
    w, biter = bite_world(env, mana_shield=1)
    cast(ns, w, "mana_shield", 0, 0)
    w.player.mana = 0
    ns.Combat.step(w, 1 / 60)
    assert w.player.life == pytest.approx(490)


# ---------------------------------------------------------------- the bite goes through one door
def test_a_plain_bite_still_costs_exactly_its_damage(env):
    lua, ns = env
    w, biter = bite_world(env)
    run(ns, w, 0.1)
    assert w.player.life == 490


def test_two_shields_stack_in_order_armour_then_mana_then_barrier(env):
    lua, ns = env
    ns.Combat.MANA_REGEN = 0
    w, biter = bite_world(env, frost_armor=1, mana_shield=1, ice_barrier=1)
    for sid in ("frost_armor", "mana_shield", "ice_barrier"):
        cast(ns, w, sid, 0, 0)
    mana = w.player.mana
    run(ns, w, 0.1)
    # 10 -> armour 8.5 -> mana takes 30% = 2.55 -> 5.95 left -> the barrier takes all of it
    assert w.player.life == 500 and w.player.buffs.ice_barrier.amount == pytest.approx(40 - 5.95)
    assert w.player.mana == pytest.approx(mana - 2.55)
