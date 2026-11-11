"""Gear: Items.lua (the rules) and how Combat.lua uses it. Numbers are worked by hand in the comments."""
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


def fixed(lua, v):
    return lua.eval(f"function() return {v} end")


def item(lua, slot="body", rarity="magic", ilvl=5, base=None, **stats):
    from_base = {"weapon": "Staff", "head": "Hood", "body": "Robe", "ring": "Ring", "amulet": "Amulet"}[slot]
    return lua.table_from({"slot": slot, "rarity": rarity, "ilvl": ilvl, "base": base or from_base, "stats": lua.table_from(stats)})


def world(env, rng=0.5):
    lua, ns = env
    w = ns.Combat.new(lua.table_from({"seed": 1}))
    w.rng = fixed(lua, rng)
    return w


def monster(env, w, x, y, life=100, **kw):
    lua, ns = env
    return ns.Combat.add_monster(w, lua.table_from({"x": x, "y": y, "life": life, **kw}))


# ---------------------------------------------------------------- rolling
def test_a_roll_with_the_generator_pinned_at_half_gives_exactly_this_robe(env):
    lua, ns = env
    it = ns.Items.roll(fixed(lua, 0.5), 10, False)
    # slot: 1+floor(.5*5)=3 -> body. Not rare (.5 >= .2): 1-2 affixes, 1+floor(.5*2)=2. Body can take life and mana only.
    # first pick index 2 -> mana: floor(3 + 3*.5 + .8*10 + .5) = 13. then life: floor(4 + 4*.5 + 1.2*10 + .5) = 18.
    assert it.slot == "body" and it.rarity == "magic" and it.ilvl == 10 and it.base == "Vestment"
    assert it.stats.mana == 13 and it.stats.life == 18


def lcg(lua, seed):
    return lua.eval(f"(function() local s = {seed + 1}; return function() s = (s * 1103515245 + 12345) % 2147483648; return s / 2147483648 end end)()")


def test_rare_means_three_or_four_bonuses_where_the_slot_can_hold_them_and_magic_one_or_two(env):
    lua, ns = env
    for seed in range(60):
        it = ns.Items.roll(lcg(lua, seed), 8, True)
        n = len(list(it.stats.keys()))
        assert it.rarity == "rare"
        assert (n == 2) if it.slot == "body" else (3 <= n <= 4)         # a robe can only carry life and mana
    for seed in range(60):
        it = ns.Items.roll(fixed(lua, 0.5), 8, False)                  # a pinned half never beats the 20% rare chance
        assert it.rarity == "magic" and 1 <= len(list(it.stats.keys())) <= 2


def test_bonuses_only_appear_on_slots_that_may_carry_them(env):
    lua, ns = env
    allowed = {"weapon": {"dmg_pct", "fire_pct", "cold_pct", "lightning_pct"},
               "head": {"life", "mana", "mana_regen_pct"}, "body": {"life", "mana"},
               "ring": {"life", "mana", "dmg_pct", "mana_regen_pct"}, "amulet": {"life", "mana", "dmg_pct", "fire_pct", "cold_pct", "lightning_pct"}}
    for seed in range(300):
        it = ns.Items.roll(lcg(lua, seed), 12, seed % 3 == 0)
        assert set(it.stats.keys()) <= allowed[str(it.slot)]


def test_higher_item_level_means_bigger_numbers(env):
    lua, ns = env
    lo = ns.Items.roll(fixed(lua, 0.5), 2, False)
    hi = ns.Items.roll(fixed(lua, 0.5), 30, False)
    assert hi.stats.life > lo.stats.life and hi.stats.mana > lo.stats.mana


# ---------------------------------------------------------------- wearing
def test_a_better_item_replaces_the_worn_one_and_a_worse_one_is_left(env):
    lua, ns = env
    gear = lua.table()
    a = item(lua, life=10)
    b = item(lua, life=30)
    c = item(lua, life=20)
    assert ns.Items.consider(gear, a)[0] is True and gear.body.stats.life == 10
    ok, old = ns.Items.consider(gear, b)
    assert ok is True and old.stats.life == 10 and gear.body.stats.life == 30
    assert ns.Items.consider(gear, c)[0] is False and gear.body.stats.life == 30


def test_totals_add_every_worn_piece(env):
    lua, ns = env
    gear = lua.table_from({"body": item(lua, life=10, mana=5), "ring": item(lua, "ring", life=7, dmg_pct=4)})
    t = ns.Items.totals(gear)
    assert t.life == 17 and t.mana == 5 and t.dmg_pct == 4


# ---------------------------------------------------------------- the effect in the fight
def test_gear_raises_max_life_and_mana_and_keeps_the_share_you_had(env):
    lua, ns = env
    w = world(env)
    w.player.life = w.player.maxlife / 2                      # half health: 30 of 60
    assert ns.Combat.take_item(w, item(lua, life=40, mana=10)) == "worn"
    assert w.player.maxlife == 100 and w.player.maxmana == 43
    assert w.player.life == pytest.approx(50)                  # still half


def test_gear_damage_percent_multiplies_what_a_spell_does(env):
    lua, ns = env
    base = world(env)
    boosted = world(env)
    for w in (base, boosted):
        w.player.st.points["scorch"] = 1
        w.player.mana = w.player.maxmana = 500
        monster(env, w, w.player.x + 100, w.player.y, life=1000, speed=0)
    ns.Combat.take_item(boosted, item(lua, "weapon", fire_pct=20, dmg_pct=10))
    for w in (base, boosted):
        ns.Combat.cast(w, "scorch", w.player.x + 100, w.player.y)
        for _ in range(60):
            ns.Combat.step(w, 1 / 60)
    d0 = 1000 - base.monsters[1].life
    d1 = 1000 - boosted.monsters[1].life
    assert d0 > 0 and d1 == pytest.approx(d0 * 1.3)            # +20% fire and +10% general add up to +30%


def test_the_wand_gets_the_general_bonus_but_not_an_element_bonus(env):
    lua, ns = env
    w = world(env)
    ns.Combat.take_item(w, item(lua, "weapon", fire_pct=50))
    assert ns.Combat.gear_dmg_pct(w.player, "physical") == 0
    ns.Combat.take_item(w, item(lua, "ring", dmg_pct=10))
    assert ns.Combat.gear_dmg_pct(w.player, "physical") == 10 and ns.Combat.gear_dmg_pct(w.player, "fire") == 60


def test_mana_regeneration_percent_speeds_up_regeneration(env):
    lua, ns = env
    a, b = world(env), world(env)
    for w in (a, b):
        w.player.mana = 0
    ns.Combat.take_item(b, item(lua, "head", mana_regen_pct=50))
    b.player.mana = 0
    for w in (a, b):
        for _ in range(60):
            ns.Combat.step(w, 1 / 60)
    # same 1 second; b has more max mana too, so compare the fraction of the maximum regained
    assert (b.player.mana / b.player.maxmana) == pytest.approx(1.5 * (a.player.mana / a.player.maxmana), rel=0.02)


# ---------------------------------------------------------------- drops
def kill_one(env, w, boss=False):
    m = monster(env, w, w.player.x + 150, w.player.y, life=1, speed=0, **({"boss": True} if boss else {}))
    w.player.mana = w.player.maxmana = 200
    w.player.st.points["scorch"] = 1
    env[1].Combat.cast(w, "scorch", m.x, m.y)
    for _ in range(90):
        env[1].Combat.step(w, 1 / 60)
    return m


def drops_of(w, kind):
    return [d for d in w.drops.values() if d.kind == kind]


def test_an_ordinary_kill_drops_gear_only_when_the_roll_is_under_the_chance(env):
    lua, ns = env
    w = world(env, rng=0.05)                                   # 0.05 < 0.12
    kill_one(env, w)
    assert len(drops_of(w, "item")) == 1
    w2 = world(env, rng=0.5)
    kill_one(env, w2)
    assert len(drops_of(w2, "item")) == 0


def test_a_boss_always_drops_two_rare_items(env):
    lua, ns = env
    w = world(env, rng=0.99)
    kill_one(env, w, boss=True)
    items = drops_of(w, "item")
    assert len(items) == 2 and all(d.item.rarity == "rare" for d in items)
    assert items[0].x != items[1].x or items[0].y != items[1].y        # not stacked on one spot


def test_item_level_follows_the_player_level_and_the_boss_is_two_higher(env):
    lua, ns = env
    w = world(env, rng=0.05)
    ns.Combat.set_level(w, 9)
    kill_one(env, w)
    assert list(drops_of(w, "item"))[0].item.ilvl == 9
    w = world(env, rng=0.99)
    ns.Combat.set_level(w, 9)
    kill_one(env, w, boss=True)
    assert list(drops_of(w, "item"))[0].item.ilvl == 11


def test_walking_over_an_item_wears_it_if_better_and_leaves_it_if_not(env):
    lua, ns = env
    w = world(env)
    p = w.player
    w.drops[1] = lua.table_from({"kind": "item", "item": item(lua, life=20), "x": p.x, "y": p.y, "t": 30})
    ns.Combat.step(w, 1 / 60)
    assert p.gear.body.stats.life == 20 and p.maxlife == 80
    w.drops[1] = lua.table_from({"kind": "item", "item": item(lua, life=5), "x": p.x, "y": p.y, "t": 30})
    ns.Combat.step(w, 1 / 60)
    assert p.gear.body.stats.life == 20                        # the worse one did not replace it
    kinds = [e.k for e in ns.Combat.drain(w).values()]
    assert "item" in kinds and "junk" in kinds


def test_area_monsters_are_tougher_than_the_zone_table_says(env):
    lua, ns = env
    w = world(env)
    area = lua.table_from({"name": "x", "w": 500, "h": 500, "spawn": lua.table_from({"x": 10, "y": 10}),
                           "monsters": lua.table_from([lua.table_from({"x": 400, "y": 400, "life": 100, "dmg": lua.table_from({"1": 4, "2": 8})})])})
    area.monsters[1].dmg = lua.table_from([4, 8])
    ns.Combat.enter(w, area)
    m = w.monsters[1]
    assert m.life == pytest.approx(130) and m.dmg[1] == pytest.approx(5) and m.dmg[2] == pytest.approx(10)


# ---------------------------------------------------------------- saving
def test_gear_survives_a_save_and_a_load(env):
    lua, ns = env
    w = world(env)
    ns.Combat.take_item(w, item(lua, "ring", ilvl=10, life=15, dmg_pct=5))
    snap = ns.Combat.snapshot(w)
    w2 = world(env)
    assert ns.Combat.restore(w2, snap) is True
    assert w2.player.gear.ring.stats.life == 15 and w2.player.maxlife == 75


def test_a_tampered_save_is_cleaned_not_trusted(env):
    lua, ns = env
    snap = lua.table_from({"level": 1, "gear": lua.table_from({
        "ring": lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 1, "rarity": "rare", "stats": lua.table_from({"life": 99999, "bogus": 5, "fire_pct": 10})}),
        "body": lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 1, "stats": lua.table_from({"life": 5})}),       # wrong slot for the key
        "head": lua.table_from({"slot": "head", "base": "Crown of Doom", "ilvl": 1, "stats": lua.table_from({"life": 5})}),  # not a real base
        "amulet": "nonsense"})})
    w = world(env)
    ns.Combat.restore(w, snap)
    ring = w.player.gear.ring
    assert ring.stats.life <= 9 and ring.stats.bogus is None and ring.stats.fire_pct is None   # capped at what level 1 can roll; unknown and not-allowed dropped
    assert w.player.gear.body is None and w.player.gear.head is None and w.player.gear.amulet is None
