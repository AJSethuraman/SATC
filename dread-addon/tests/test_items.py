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
    it = ns.Items.roll(fixed(lua, 0.5), 10, "magic")
    # slot: 1+floor(.5*8)=5 -> amulet. Forced magic: 1-2 bonuses, 1+floor(.5*2)=2. An amulet can carry life, mana, spell damage,
    # fire, cold, lightning and the four attributes (10 choices). First pick 1+floor(.5*10)=6 -> lightning: floor(4 + 4*.5 + .6*10 + .5) = 12.
    # Then 9 left, 1+floor(.5*9)=5 -> cold (life, mana, dmg, fire, cold, ...): also 12. Base 1+floor(.5*3)=2 -> Pendant.
    assert it.slot == "amulet" and it.rarity == "magic" and it.ilvl == 10 and it.base == "Pendant"
    assert it.stats.lightning_pct == 12 and it.stats.cold_pct == 12 and len(list(it.stats.keys())) == 2


def lcg(lua, seed):
    return lua.eval(f"(function() local s = {seed + 1}; return function() s = (s * 1103515245 + 12345) % 2147483648; return s / 2147483648 end end)()")


def test_each_tier_carries_its_own_number_of_bonuses_and_unique_has_a_name(env):
    lua, ns = env
    for seed in range(60):
        n = lambda tier: ns.Items.roll(lcg(lua, seed), 8, tier)
        c, m, r, u = n("common"), n("magic"), n("rare"), n("unique")
        assert (c.rarity, m.rarity, r.rarity, u.rarity) == ("common", "magic", "rare", "unique")
        assert len(list(c.stats.keys())) == 1 and 1 <= len(list(m.stats.keys())) <= 2
        assert 3 <= len(list(r.stats.keys())) <= 4 and 4 <= len(list(u.stats.keys())) <= 5
        assert u.title in list(ns.Items.UNIQUE_NAMES[u.slot].values()) and c.title is None and r.title is None
        assert ns.Items.name(u) == u.title


def test_the_roll_picks_the_tier_from_the_cut_points_and_a_boss_is_rare_or_unique(env):
    lua, ns = env
    for pinned, tier in ((0.005, "unique"), (0.05, "rare"), (0.3, "magic"), (0.7, "common")):
        assert ns.Items.roll(fixed(lua, pinned), 5).rarity == tier
    assert ns.Items.roll(fixed(lua, 0.5), 5, "boss").rarity == "rare"
    assert ns.Items.roll(fixed(lua, 0.1), 5, "boss").rarity == "unique"      # under the boss's 25%


def test_a_common_bonus_is_weaker_than_a_magic_one_at_the_same_level_and_unique_is_stronger(env):
    lua, ns = env
    c = ns.Items.roll(fixed(lua, 0.5), 20, "common")
    m = ns.Items.roll(fixed(lua, 0.5), 20, "magic")
    u = ns.Items.roll(fixed(lua, 0.5), 20, "unique")
    top = lambda it: max(it.stats.values())
    assert top(c) < top(m) < top(u)


def test_bonuses_only_appear_on_slots_that_may_carry_them(env):
    lua, ns = env
    attrs = {"int", "vit", "str", "dex"}
    allowed = {"weapon": {"dmg_pct", "fire_pct", "cold_pct", "lightning_pct"} | attrs,
               "gloves": {"life", "dmg_pct", "mana_regen_pct"} | attrs, "belt": {"life", "mana", "mana_regen_pct"} | attrs,
               "boots": {"life", "mana"} | attrs,
               "head": {"life", "mana", "mana_regen_pct"} | attrs, "body": {"life", "mana"} | attrs,
               "ring": {"life", "mana", "dmg_pct", "mana_regen_pct"} | attrs, "amulet": {"life", "mana", "dmg_pct", "fire_pct", "cold_pct", "lightning_pct"} | attrs}
    for seed in range(300):
        it = ns.Items.roll(lcg(lua, seed), 12, seed % 3 == 0)
        assert set(it.stats.keys()) <= allowed[str(it.slot)]


def test_higher_item_level_means_bigger_numbers(env):
    lua, ns = env
    lo = ns.Items.roll(fixed(lua, 0.5), 2, False)
    hi = ns.Items.roll(fixed(lua, 0.5), 30, False)
    assert sum(hi.stats.values()) > sum(lo.stats.values())


# ---------------------------------------------------------------- wearing
def test_equipping_from_the_bag_swaps_with_what_is_worn_and_keeps_the_place(env):
    lua, ns = env
    gear = lua.table_from({"body": item(lua, life=10)})
    bag = lua.table_from([item(lua, life=30), item(lua, "ring", life=1)])
    assert ns.Items.equip(gear, bag, 1) is True
    assert gear.body.stats.life == 30 and bag[1].stats.life == 10 and bag[2].slot == "ring"   # the old robe took the bag place
    assert ns.Items.equip(gear, bag, 2) is True                                            # an empty place: nothing swaps back
    assert gear.ring1.stats.life == 1 and len(list(bag.values())) == 1
    assert ns.Items.equip(gear, bag, 5) is False


def test_totals_add_every_worn_piece(env):
    lua, ns = env
    gear = lua.table_from({"body": item(lua, life=10, mana=5), "ring1": item(lua, "ring", life=7, dmg_pct=4), "ring2": item(lua, "ring", life=3)})
    t = ns.Items.totals(gear)
    assert t.life == 20 and t.mana == 5 and t.dmg_pct == 4          # both rings count


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


def test_an_item_for_an_empty_slot_is_worn_and_one_for_a_full_slot_goes_in_the_bag(env):
    lua, ns = env
    w = world(env)
    p = w.player
    w.drops[1] = lua.table_from({"kind": "item", "item": item(lua, life=20), "x": p.x, "y": p.y, "t": 30})
    ns.Combat.step(w, 1 / 60)
    assert p.gear.body.stats.life == 20 and p.maxlife == 80 and len(list(p.bag.values())) == 0
    w.drops[1] = lua.table_from({"kind": "item", "item": item(lua, int=9), "x": p.x, "y": p.y, "t": 30})
    ns.Combat.step(w, 1 / 60)
    assert p.gear.body.stats.life == 20                        # your choice: the new one waits in the bag
    assert len(list(p.bag.values())) == 1 and p.bag[1].stats.int == 9
    ev = [(e.k, e.how) for e in ns.Combat.drain(w).values() if e.k == "item"]
    assert ev == [("item", "worn"), ("item", "bagged")]


def test_a_full_bag_leaves_the_item_on_the_ground_and_tells_you_only_now_and_then(env):
    lua, ns = env
    w = world(env)
    p = w.player
    p.gear.body = item(lua, life=1)
    for i in range(16):
        p.bag[i + 1] = item(lua, life=i + 2)
    w.drops[1] = lua.table_from({"kind": "item", "item": item(lua, int=9), "x": p.x, "y": p.y, "t": 30})
    for _ in range(30):                                         # half a second standing on it
        ns.Combat.step(w, 1 / 60)
    assert len(list(w.drops.values())) == 1 and len(list(p.bag.values())) == 16
    assert [e.k for e in ns.Combat.drain(w).values()].count("full") == 1
    ns.Combat.trash(w, 16)                                      # make room and it is taken
    ns.Combat.step(w, 1 / 60)
    assert len(list(w.drops.values())) == 0 and p.bag[16].stats.int == 9


def test_attributes_do_what_they_say(env):
    lua, ns = env
    w = world(env)
    ns.Combat.take_item(w, item(lua, "ring", int=10))          # +20 mana, +5% spell damage
    ns.Combat.take_item(w, item(lua, "head", vit=10))          # +30 life
    ns.Combat.take_item(w, item(lua, "amulet", str=8, dex=10))  # +8% wand damage, +3% speed
    d = ns.Combat.derived(1, w.player.gear)
    assert d.mana == 33 + 20 and d.life == 60 + 30
    assert d.spell_pct == pytest.approx(5) and d.wand_pct == pytest.approx(8) and d.speed_pct == pytest.approx(3)
    assert ns.Combat.gear_dmg_pct(w.player, "fire") == pytest.approx(5) and ns.Combat.gear_dmg_pct(w.player, "physical") == pytest.approx(8)


def test_strength_does_nothing_for_a_spell_but_intelligence_does(env):
    lua, ns = env
    strong, clever = world(env), world(env)
    ns.Combat.take_item(strong, item(lua, "ring", str=20))
    ns.Combat.take_item(clever, item(lua, "ring", int=20))
    assert ns.Combat.gear_dmg_pct(strong.player, "cold") == 0 and ns.Combat.gear_dmg_pct(clever.player, "cold") == pytest.approx(10)
    assert ns.Combat.gear_dmg_pct(strong.player, "physical") == pytest.approx(20) and ns.Combat.gear_dmg_pct(clever.player, "physical") == 0


def test_dexterity_makes_you_walk_faster(env):
    lua, ns = env
    slow, quick = world(env), world(env)
    ns.Combat.take_item(quick, item(lua, "ring", dex=100))     # +30%
    for w in (slow, quick):
        w.player.x, w.player.y = 100, 500
        ns.Combat.move_to(w, 1000, 500)
        for _ in range(60):
            ns.Combat.step(w, 1 / 60)
    assert (quick.player.x - 100) == pytest.approx(1.3 * (slow.player.x - 100), rel=0.01)


def test_compare_shows_what_wearing_a_bag_item_would_change(env):
    lua, ns = env
    w = world(env)
    ns.Combat.take_item(w, item(lua, "head", str=10))          # worn
    ns.Combat.take_item(w, item(lua, "head", int=10, life=5))  # bag
    diff = ns.Combat.compare(w, 1)
    assert diff.mana == 20 and diff.life == 5 and diff.spell_pct == pytest.approx(5) and diff.wand_pct == pytest.approx(-10)
    assert ns.Combat.compare(w, 9) is None


def test_equip_and_trash_change_the_character_and_the_bag(env):
    lua, ns = env
    w = world(env)
    ns.Combat.take_item(w, item(lua, "head", str=10))
    ns.Combat.take_item(w, item(lua, "head", vit=10))
    assert ns.Combat.equip(w, 1) is True
    assert w.player.maxlife == 90 and w.player.bag[1].stats.str == 10
    assert ns.Combat.trash(w, 1) is True and len(list(w.player.bag.values())) == 0
    assert ns.Combat.equip(w, 1) is False and ns.Combat.trash(w, 1) is False


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
    ns.Combat.take_item(w, item(lua, "ring", ilvl=10, vit=2))              # the second ring place
    ns.Combat.take_item(w, item(lua, "head", ilvl=10, int=7))
    ns.Combat.take_item(w, item(lua, "head", ilvl=10, int=3))              # worn head is taken, so this one waits
    snap = ns.Combat.snapshot(w)
    w2 = world(env)
    assert ns.Combat.restore(w2, snap) is True
    assert w2.player.gear.ring1.stats.life == 15 and w2.player.gear.ring2.stats.vit == 2 and w2.player.maxlife == 60 + 15 + 6
    assert w2.player.bag[1].stats.int == 3                     # the bag comes back too


def test_a_tampered_save_is_cleaned_not_trusted(env):
    lua, ns = env
    snap = lua.table_from({"level": 1, "gear": lua.table_from({
        "ring1": lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 1, "rarity": "rare", "stats": lua.table_from({"life": 99999, "bogus": 5, "fire_pct": 10})}),
        "body": lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 1, "stats": lua.table_from({"life": 5})}),       # wrong slot for the key
        "head": lua.table_from({"slot": "head", "base": "Crown of Doom", "ilvl": 1, "stats": lua.table_from({"life": 5})}),  # not a real base
        "amulet": "nonsense"})})
    w = world(env)
    ns.Combat.restore(w, snap)
    ring = w.player.gear.ring1
    assert ring.stats.life == 12 and ring.stats.bogus is None and ring.stats.fire_pct is None   # capped at the most a level-1 roll can give; unknown and not-allowed dropped
    assert w.player.gear.body is None and w.player.gear.head is None and w.player.gear.amulet is None


def test_a_unique_with_an_unknown_name_is_only_a_rare_and_a_real_one_keeps_its_name(env):
    lua, ns = env
    fake = ns.Items.clean(lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 3, "rarity": "unique", "title": "Totally Fake Thing", "stats": lua.table_from({"life": 4})}))
    assert fake.rarity == "rare" and fake.title is None
    real = ns.Items.clean(lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 3, "rarity": "unique", "title": "Seal of Cinders", "stats": lua.table_from({"life": 4})}))
    assert real.rarity == "unique" and ns.Items.name(real) == "Seal of Cinders"
    assert ns.Items.clean(lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 3, "rarity": "godly", "stats": lua.table_from({"life": 4})})).rarity == "magic"


def test_a_unique_survives_save_and_load(env):
    lua, ns = env
    w = world(env)
    ns.Combat.take_item(w, lua.table_from({"slot": "ring", "rarity": "unique", "title": "Seal of Cinders", "ilvl": 5, "base": "Ring", "stats": lua.table_from({"int": 6})}))
    w2 = world(env)
    ns.Combat.restore(w2, ns.Combat.snapshot(w))
    assert w2.player.gear.ring1.rarity == "unique" and w2.player.gear.ring1.title == "Seal of Cinders"


def test_take_item_itself_refuses_when_the_bag_is_full(env):
    lua, ns = env
    w = world(env)
    w.player.gear.head = item(lua, "head", life=1)
    for i in range(16):
        w.player.bag[i + 1] = item(lua, "head", life=i + 2)
    assert ns.Combat.take_item(w, item(lua, "head", int=3)) == "full" and len(list(w.player.bag.values())) == 16


# ---------------------------------------------------------------- places on you
def test_the_nine_places_and_where_each_item_type_goes(env):
    lua, ns = env
    assert list(ns.Items.GEAR_SLOTS.values()) == ["head", "amulet", "weapon", "body", "gloves", "belt", "boots", "ring1", "ring2"]
    gear = lua.table()
    assert ns.Items.place(gear, "head") == "head" and ns.Items.place(gear, "ring") == "ring1"
    gear.ring1 = item(lua, "ring", life=1)
    assert ns.Items.place(gear, "ring") == "ring2"
    gear.ring2 = item(lua, "ring", life=1)
    assert ns.Items.place(gear, "ring") == "ring1"                         # both full: a new ring swaps ring 1
    assert ns.Items.fits("ring2", "ring") and not ns.Items.fits("ring2", "head") and not ns.Items.fits("head", "ring")


def test_two_rings_are_worn_together_and_a_third_goes_to_the_bag(env):
    lua, ns = env
    w = world(env)
    for life in (5, 6, 7):
        ns.Combat.take_item(w, item(lua, "ring", life=life))
    g = w.player.gear
    assert g.ring1.stats.life == 5 and g.ring2.stats.life == 6 and w.player.bag[1].stats.life == 7
    assert w.player.maxlife == 60 + 5 + 6


def test_a_ring_can_be_sent_to_either_ring_place_and_not_to_another_kind_of_place(env):
    lua, ns = env
    w = world(env)
    for life in (5, 6, 7):
        ns.Combat.take_item(w, item(lua, "ring", life=life))
    assert ns.Combat.equip(w, 1, "ring2") is True                          # the third ring replaces ring 2
    assert w.player.gear.ring2.stats.life == 7 and w.player.bag[1].stats.life == 6 and w.player.gear.ring1.stats.life == 5
    assert ns.Combat.equip(w, 1, "head") is False                          # a ring does not fit a helm
    assert w.player.gear.ring2.stats.life == 7


def test_taking_something_off_puts_it_in_the_bag_and_lowers_your_numbers(env):
    lua, ns = env
    w = world(env)
    ns.Combat.take_item(w, item(lua, "body", vit=10))                      # +30 life
    assert w.player.maxlife == 90
    assert ns.Combat.unequip(w, "body") is True
    assert w.player.gear.body is None and w.player.bag[1].stats.vit == 10 and w.player.maxlife == 60
    assert ns.Combat.unequip(w, "body") is False                           # nothing there
    assert ns.Combat.unequip(w, "head") is False


def test_taking_something_off_needs_room_in_the_bag(env):
    lua, ns = env
    w = world(env)
    ns.Combat.take_item(w, item(lua, "body", vit=10))
    for i in range(16):
        w.player.bag[i + 1] = item(lua, "head", life=i + 2)
    assert ns.Combat.unequip(w, "body") is False and w.player.gear.body.stats.vit == 10


def test_the_new_types_roll_and_carry_only_what_suits_them(env):
    lua, ns = env
    seen = set()
    for seed in range(400):
        it = ns.Items.roll(lcg(lua, seed), 10)
        seen.add(str(it.slot))
    assert {"gloves", "belt", "boots", "head", "body", "weapon", "ring", "amulet"} <= seen


def test_a_ring_in_the_wrong_saved_place_is_dropped_on_load(env):
    lua, ns = env
    snap = lua.table_from({"level": 1, "gear": lua.table_from({
        "head": lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 1, "rarity": "magic", "stats": lua.table_from({"life": 4})}),
        "ring2": lua.table_from({"slot": "ring", "base": "Ring", "ilvl": 1, "rarity": "magic", "stats": lua.table_from({"life": 4})})})})
    w = world(env)
    ns.Combat.restore(w, snap)
    assert w.player.gear.head is None and w.player.gear.ring2.stats.life == 4
