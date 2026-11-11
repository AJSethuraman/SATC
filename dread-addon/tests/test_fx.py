"""The particle system (Dread/Fx.lua) under plain Lua. Numbers are worked by hand in the comments."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"


@pytest.fixture()
def env():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Combat", "Fx"):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


def world(env, **points):
    lua, ns = env
    w = ns.Combat.new(lua.table_from({"seed": 1, "w": 2000, "h": 2000}))
    w.rng = lua.eval("function() return 0 end")
    for k, v in points.items():
        w.player.st.points[k] = v
    w.player.mana = w.player.maxmana = 500
    return w


def cast(ns, w, sid, x, y):
    r = ns.Combat.cast(w, sid, x, y)
    return r if isinstance(r, bool) else r[0]


def run_fx(ns, fx, w, seconds, dt=1 / 60, step_world=True):
    for _ in range(int(round(seconds / dt))):
        if step_world:
            ns.Combat.step(w, dt)
        ns.Fx.update(fx, w, dt)


def plist(fx):
    return [fx.list[i] for i in range(1, len(fx.list) + 1)]


def blank(env):
    lua, ns = env
    return ns.Fx.new(5), world(env)


# ---------------------------------------------------------------- one particle
def test_a_particle_moves_ages_and_disappears(env):
    lua, ns = env
    fx, w = blank(env)
    ns.Fx.spark(fx, 100, 100, 100, 0, lua.table_from([1, 1, 1]), 0.5, 10, 2, 0.9, 0)
    run_fx(ns, fx, w, 0.25, step_world=False)
    p = plist(fx)[0]
    assert p.x == pytest.approx(125, abs=0.5) and p.y == pytest.approx(100)              # 100 units a second for a quarter second
    run_fx(ns, fx, w, 0.3, step_world=False)
    assert len(plist(fx)) == 0                                                          # its life (0.5 s) is over


def test_gravity_pulls_a_particle_down_and_rising_goes_up(env):
    lua, ns = env
    fx, w = blank(env)
    ns.Fx.spark(fx, 0, 0, 0, 0, lua.table_from([1, 1, 1]), 1.0, 5, 5, 1, -200)
    run_fx(ns, fx, w, 0.5, step_world=False)
    assert plist(fx)[0].vy == pytest.approx(-100, abs=2) and plist(fx)[0].y < 0          # v = g t, falling


def test_the_particle_count_never_exceeds_the_cap(env):
    lua, ns = env
    fx, w = blank(env)
    for _ in range(400):
        ns.Fx.burst(fx, 0, 0, lua.table_from([1, 1, 1]), 26, 100, 5.0, 5, 1)             # long-lived, far more than the cap
    assert len(plist(fx)) == ns.Fx.MAX == 220


def test_a_scale_of_zero_emits_nothing_and_half_emits_about_half(env):
    lua, ns = env
    counts = {}
    for scale in (0, 0.5, 1):
        w = world(env, scorch=1)
        cast(ns, w, "scorch", 1900, 40)
        fx = ns.Fx.new(5)
        fx.scale = scale
        run_fx(ns, fx, w, 0.2, step_world=False)
        counts[scale] = len(plist(fx))
    assert counts[0] == 0
    assert counts[1] == pytest.approx(14, abs=2) and counts[0.5] == pytest.approx(7, abs=2)      # 70 a second x 0.2 s, and half of it


# ---------------------------------------------------------------- bolts leave trails
def test_a_flying_bolt_leaves_a_trail_in_its_element_colour(env):
    lua, ns = env
    w = world(env, scorch=1, frostbolt=1)
    fx = ns.Fx.new(5)
    cast(ns, w, "scorch", 1900, 40)
    run_fx(ns, fx, w, 0.5, step_world=False)
    n = len(plist(fx))
    assert 15 <= n <= 36                                                                 # ~70 a second, the oldest already gone
    assert all(p.r == 1 and p.g < p.r and p.b < p.g for p in plist(fx))                  # fire is orange
    fx2, w2 = ns.Fx.new(5), world(env, frostbolt=1)
    cast(ns, w2, "frostbolt", 1900, 40)
    run_fx(ns, fx2, w2, 0.5, step_world=False)
    assert all(p.b > p.r for p in plist(fx2))                                            # frost is blue


def test_lightning_trails_are_brief_and_jittery(env):
    lua, ns = env
    w = world(env, lightning_bolt=1)
    fx = ns.Fx.new(5)
    cast(ns, w, "lightning_bolt", 1900, 40)
    run_fx(ns, fx, w, 0.3, step_world=False)
    assert plist(fx) and all(p.max <= 0.15 + 1e-9 for p in plist(fx))


def test_nothing_is_emitted_when_nothing_is_happening(env):
    lua, ns = env
    fx, w = blank(env)
    run_fx(ns, fx, w, 2.0)
    assert len(plist(fx)) == 0


def test_drawing_sparks_never_touches_the_combat_random_numbers(env):
    lua, ns = env
    w = world(env, flamestrike=1, ice_barrier=1, scorch=1)
    w.rng = lua.eval("function() error('the fight random numbers were used for sparks') end")
    for sid in ("ice_barrier",):
        w.rng = lua.eval("function() return 0 end")
        cast(ns, w, sid, 0, 0)
    cast(ns, w, "flamestrike", 400, 40)
    cast(ns, w, "scorch", 900, 40)
    w.rng = lua.eval("function() error('the fight random numbers were used for sparks') end")
    fx = ns.Fx.new(5)
    run_fx(ns, fx, w, 1.0, step_world=False)                                             # no stepping: only Fx runs
    ns.Fx.on_event(fx, lua.table_from({"k": "blast", "id": "fireball", "x": 300, "y": 300, "r": 55}), w)
    assert len(plist(fx)) > 0


def test_the_same_seed_gives_the_same_sparks(env):
    lua, ns = env
    out = []
    for _ in range(2):
        w = world(env, scorch=1)
        cast(ns, w, "scorch", 1900, 40)
        fx = ns.Fx.new(11)
        run_fx(ns, fx, w, 0.4, step_world=False)
        out.append([(round(p.x, 6), round(p.y, 6)) for p in plist(fx)])
    assert out[0] == out[1] and len(out[0]) > 5


# ---------------------------------------------------------------- landing, zones, shields
def test_a_blast_bursts_and_sends_a_ring_outward(env):
    lua, ns = env
    fx, w = blank(env)
    ns.Fx.on_event(fx, lua.table_from({"k": "blast", "id": "fireball", "x": 500, "y": 500, "r": 55}), w)
    ps = plist(fx)
    assert len(ps) == 19 + 18                                                            # min(26, 6 + 55/4) = 19 sparks and a ring of 18
    ring = ps[19:]
    assert all(((q.vx) ** 2 + (q.vy) ** 2) ** 0.5 == pytest.approx(55 / 0.4, rel=0.01) for q in ring)     # r / life, all outward


def test_hits_kills_levels_pickups_zaps_and_blinks_each_have_a_look(env):
    lua, ns = env
    fx, w = blank(env)
    ev = lambda **kw: ns.Fx.on_event(fx, lua.table_from(kw), w)
    ev(k="hit", id="scorch", x=1, y=1, dmg=5);            assert len(plist(fx)) == 5
    fx.list = lua.table()
    ev(k="kill", x=1, y=1, xp=5);                          assert len(plist(fx)) == 12 and plist(fx)[0].r > plist(fx)[0].b          # reddish
    fx.list = lua.table()
    ev(k="level", level=2);                                assert len(plist(fx)) == 24 + 16
    fx.list = lua.table()
    ev(k="pickup", kind="mana", x=1, y=1);                 assert len(plist(fx)) == 8 and plist(fx)[0].b > plist(fx)[0].r
    fx.list = lua.table()
    ev(k="blink", id="blink", x0=0, y0=0, x1=300, y1=0);   assert len(plist(fx)) == 28
    fx.list = lua.table()
    ev(k="zap", id="lightning_bolt", x1=0, y1=0, x2=400, y2=0)
    xs = sorted(round(q.x) for q in plist(fx))
    assert xs == [100, 200, 300]                                                         # evenly along the beam


def test_burning_ground_throws_flames_up_and_a_blizzard_drops_snow_and_a_bigger_area_emits_more(env):
    lua, ns = env
    wf = world(env, flamestrike=1)
    cast(ns, wf, "flamestrike", 300, 40)                                                 # radius 70: 4900 / 120 = ~41 a second
    ff = ns.Fx.new(5)
    run_fx(ns, ff, wf, 0.5, step_world=False)
    wb = world(env, blizzard=1)
    cast(ns, wb, "blizzard", 300, 40)                                                    # radius 110: 100 a second
    fb = ns.Fx.new(5)
    run_fx(ns, fb, wb, 0.5, step_world=False)
    nf, nb = len(plist(ff)), len(plist(fb))
    assert nb > nf * 1.8
    assert sum(q.vy for q in plist(ff)) / nf > 20                                        # flames rise
    assert sum(q.vy for q in plist(fb)) / nb < -15                                       # snow falls


def test_a_cone_sprays_forward_a_summoned_spirit_burns_and_a_storm_gathers(env):
    lua, ns = env
    for sid, aim, check in (("dragons_breath", (300, 400), lambda ps: sum(q.vy for q in ps) / len(ps) > 60),     # north of (300, 40)
                            ("flame_spirit", (300, 150), lambda ps: sum(q.vy for q in ps) / len(ps) > 20),
                            ("storm_cloud", (0, 0), lambda ps: sum(1 for q in ps if q.y > 40 + 50) >= len(ps) * 0.9)):    # the cloud sits above you
        w = world(env, **{sid: 1})
        assert cast(ns, w, sid, *aim)
        fx = ns.Fx.new(5)
        run_fx(ns, fx, w, 0.5, step_world=False)
        ps = plist(fx)
        assert len(ps) >= 5 and check(ps), sid


# ---------------------------------------------------------------- shields and statuses
def test_a_shield_is_a_ring_of_glowing_dots_circling_you(env):
    lua, ns = env
    w = world(env, ice_barrier=1)
    fx = ns.Fx.new(5)
    assert len(list(ns.Fx.auras(fx, w).values())) == 0                                   # nothing without a buff
    cast(ns, w, "ice_barrier", 0, 0)
    a = [ns.Fx.auras(fx, w)[i] for i in range(1, 12)]
    assert len(a) == 11                                                                  # the bubble and 10 dots
    dots = a[1:]
    assert all(d.size == 8 and d.b > d.r for d in dots)                                  # blue
    assert all(((d.x - w.player.x) ** 2 + ((d.y - w.player.y - 20) / 0.8) ** 2) ** 0.5 == pytest.approx(26, abs=0.01) for d in dots)
    before = [(d.x, d.y) for d in dots]
    fx.time = 0.5                                                                        # half a second later
    after = [(ns.Fx.auras(fx, w)[i].x, ns.Fx.auras(fx, w)[i].y) for i in range(2, 12)]
    assert before != after                                                               # it turns


def test_two_buffs_show_two_rings_at_different_radii_and_colours(env):
    lua, ns = env
    w = world(env, ice_barrier=1, mana_shield=1, combustion=1)
    for sid in ("ice_barrier", "mana_shield", "combustion"):
        cast(ns, w, sid, 0, 0)
    fx = ns.Fx.new(5)
    a = [ns.Fx.auras(fx, w)[i] for i in range(1, len(list(ns.Fx.auras(fx, w).values())) + 1)]
    assert len(a) == (1 + 10) + (1 + 10) + (1 + 8)                                       # combustion, ice barrier, mana shield (alphabetical)
    violet = [d for d in a if d.b > d.g and d.r > 0.6 and d.size == 7]
    assert len(violet) == 10                                                             # mana shield is violet
    orange = [d for d in a if d.r == 1 and d.b < 0.2]
    assert len(orange) >= 8                                                              # combustion is orange


def test_buffs_with_flames_throw_sparks_and_chilled_monsters_glitter(env):
    lua, ns = env
    w = world(env, combustion=1)
    cast(ns, w, "combustion", 0, 0)
    fx = ns.Fx.new(5)
    run_fx(ns, fx, w, 0.5, step_world=False)
    assert len(plist(fx)) >= 15 and plist(fx)[0].vy > 0                                  # flames lick upward
    # a chilled monster nearby glitters, a calm one and a far one do not
    w2 = world(env)
    w2.player.x, w2.player.y = 300, 300
    near = ns.Combat.add_monster(w2, lua.table_from({"x": 340, "y": 300, "life": 50, "speed": 0}))
    far = ns.Combat.add_monster(w2, lua.table_from({"x": 1400, "y": 300, "life": 50, "speed": 0}))
    calm = ns.Combat.add_monster(w2, lua.table_from({"x": 300, "y": 360, "life": 50, "speed": 0}))
    near.chill, far.chill = 3, 3
    fx2 = ns.Fx.new(5)
    run_fx(ns, fx2, w2, 0.5, step_world=False)
    ps = plist(fx2)
    assert len(ps) >= 3 and all(abs(q.x - 340) < 40 for q in ps)                         # only the near chilled one, and blue
    assert all(q.b > q.r for q in ps)


def test_dragons_breath_throws_hot_flame_particles_that_grow(env):
    lua, ns = env
    w = world(env, dragons_breath=1)
    fx = ns.Fx.new()
    assert cast(ns, w, "dragons_breath", w.player.x + 300, w.player.y)
    run_fx(ns, fx, w, 0.3)
    ps = plist(fx)
    assert len(ps) > 30                                       # a stream, not a few dots
    assert all(p.r == 1 and p.g >= 0.35 for p in ps)          # red-orange to yellow, never the old flat colour
    assert all(p.s1 > p.s0 for p in ps)                       # each puff swells as it flies
