"""Skill table and point rules (Dread/Skills.lua, Dread/Tree.lua), run under plain Lua.
Expected numbers are worked by hand in the comments, not copied from the code's output."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"


def load():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    loader = lua.eval("function(path, ns) return loadfile(path)('Dread', ns) end")
    loader(str(DREAD / "Skills.lua"), ns)
    loader(str(DREAD / "Tree.lua"), ns)
    return lua, ns


@pytest.fixture()
def env():
    return load()


def can(ns, st, sid):
    r = ns.Tree.can_allocate(st, sid)
    return (r, None) if isinstance(r, bool) else r


def alloc(ns, st, sid):
    r = ns.Tree.allocate(st, sid)
    return (r, None) if isinstance(r, bool) else r


def char(env, level=30, quest=0, **points):
    lua, ns = env
    st = ns.Tree.new(lua.table_from({"level": level, "quest_points": quest}))
    for k, v in points.items():
        st.points[k] = v
    return st


# ---------------------------------------------------------------- the table itself
def test_thirty_skills_ten_per_tree(env):
    lua, ns = env
    assert len(ns.Skills) == 30
    for tree in ("fire", "cold", "lightning"):
        assert sum(1 for i in range(1, 31) if ns.Skills[i].tree == tree) == 10


def test_table_validates_clean(env):
    lua, ns = env
    assert len(ns.Tree.validate()) == 0


def test_every_tree_has_a_mastery_and_a_first_skill_with_no_prerequisite(env):
    lua, ns = env
    for tree in ("fire", "cold", "lightning"):
        sk = [ns.Skills[i] for i in range(1, 31) if ns.Skills[i].tree == tree]
        assert any(s.kind == "mastery" and s.req == 30 for s in sk)
        assert any(s.req == 1 and len(s.prereqs) == 0 for s in sk)


def test_every_damaging_skill_has_a_synergy(env):
    lua, ns = env
    for i in range(1, 31):
        sk = ns.Skills[i]
        if sk.dmg is not None:
            assert sk.syn is not None and len(sk.syn) > 0, f"{sk.id} deals damage but has no synergy"


def test_each_tree_has_real_choices(env):
    lua, ns = env
    for tree in ("fire", "cold", "lightning"):
        n = sum(1 for i in range(1, 31) if ns.Skills[i].tree == tree and ns.Skills[i].syn is not None)
        assert n >= 5, f"{tree} has only {n} skills with synergies"


def test_the_validator_can_fail(env):
    lua, ns = env
    # a prerequisite at the same tier, a synergy from nowhere, and a duplicate id
    ns.Skills.byId.scorch.prereqs = lua.table_from(["frostbolt"])
    ns.Skills.byId.scorch.syn = lua.table_from([lua.table_from({"from": "nope", "pct": 5})])
    problems = list(ns.Tree.validate().values())
    assert any("not an earlier tier" in p for p in problems)
    assert any("unknown skill nope" in p for p in problems)


# ---------------------------------------------------------------- spending points
def test_nothing_without_points(env):
    lua, ns = env
    st = char(env, level=1)
    st.points["scorch"] = 1                      # the one point a level-1 character has
    ok, why = can(ns, st, "frostbolt")
    assert ok is False and why == "no points left"


def test_level_gate(env):
    lua, ns = env
    st = char(env, level=5, quest=10, scorch=1)
    ok, why = can(ns, st, "dragons_breath")      # needs character level 6
    assert ok is False and "level 6" in why
    st.level = 6
    assert can(ns, st, "dragons_breath")[0] is True


def test_prerequisite_gate(env):
    lua, ns = env
    st = char(env, level=30)
    ok, why = can(ns, st, "fireball")            # needs Scorch
    assert ok is False and why == "needs a point in Scorch"
    assert alloc(ns, st, "scorch")[0] is True
    assert can(ns, st, "fireball")[0] is True


def test_every_prerequisite_is_needed_not_just_one(env):
    lua, ns = env
    st = char(env, level=30, quest=12, scorch=1, dragons_breath=1)
    assert can(ns, st, "blazing_speed")[0] is False      # needs Evocation too
    st.points["evocation"] = 1
    assert can(ns, st, "blazing_speed")[0] is True


def test_twenty_points_is_the_cap(env):
    lua, ns = env
    st = char(env, level=30, quest=12)                         # 42 points, plenty
    for _ in range(20):
        assert alloc(ns, st, "scorch")[0] is True
    ok, why = alloc(ns, st, "scorch")
    assert ok is False and why == "already at the maximum" and st.points["scorch"] == 20


def test_you_cannot_have_everything(env):
    lua, ns = env
    # level 30 plus 12 quest points = 42 points. Fill the whole table greedily and see where it stops.
    st = char(env, level=30, quest=12)
    changed = True
    while changed:
        changed = False
        for i in range(1, 31):
            if alloc(ns, st, ns.Skills[i].id)[0]:
                changed = True
    assert ns.Tree.points_spent(st) == 42
    assert ns.Tree.points_free(st) == 0
    maxed = sum(1 for i in range(1, 31) if st.points[ns.Skills[i].id] == 20)
    assert maxed < 30        # 30 skills x 20 points is 600; the point budget forces choices


# ---------------------------------------------------------------- the maths, by hand
def test_synergy_worked_example(env):
    lua, ns = env
    # Scorch level 5: lo = 6 + 3*4 = 18, hi = 10 + 4*4 = 26.
    # Synergies: Fireball 3 pts x 14% + Meteor 2 pts x 8% + Flame Spirit 0 = 42 + 16 = 58%  -> x1.58
    # lo = 18*1.58 = 28.44, hi = 26*1.58 = 41.08
    st = char(env, scorch=5, fireball=3, meteor=2)
    lo, hi = ns.Tree.damage(st, "scorch")
    assert lo == pytest.approx(28.44) and hi == pytest.approx(41.08)


def test_no_points_means_no_damage_and_no_cost(env):
    lua, ns = env
    st = char(env, fireball=4)
    assert ns.Tree.damage(st, "scorch") == (None, None)
    assert ns.Tree.mana_cost(st, "scorch") is None


def test_synergy_comes_from_points_not_from_the_skill_existing(env):
    lua, ns = env
    plain = char(env, scorch=5)
    boosted = char(env, scorch=5, fireball=1)
    assert ns.Tree.damage(boosted, "scorch")[0] == pytest.approx(ns.Tree.damage(plain, "scorch")[0] * 1.14)


def test_fire_mastery_scales_fire_only(env):
    lua, ns = env
    # Master of Flame level 3 = 30 + 7*2 = 44%. Scorch level 1: lo 6 -> 8.64. Frostbolt level 1: lo 5 untouched.
    st = char(env, scorch=1, frostbolt=1, master_of_flame=3)
    assert ns.Tree.damage(st, "scorch")[0] == pytest.approx(8.64)
    assert ns.Tree.damage(st, "frostbolt")[0] == pytest.approx(5.0)


def test_mana_cost_and_the_lightning_discount(env):
    lua, ns = env
    # Lightning Bolt level 11: 8 + 0.3*10 = 11. Conductor level 3 = 10 + 2.5*2 = 15% off -> 9.35.
    st = char(env, lightning_bolt=11)
    assert ns.Tree.mana_cost(st, "lightning_bolt") == pytest.approx(11.0)
    st.points["conductor"] = 3
    assert ns.Tree.mana_cost(st, "lightning_bolt") == pytest.approx(9.35)
    assert ns.Tree.mana_cost(st, "scorch") is None            # no points there


def test_discount_is_for_its_own_element(env):
    lua, ns = env
    st = char(env, frostbolt=1, conductor=5)
    assert ns.Tree.mana_cost(st, "frostbolt") == pytest.approx(3.0)


def test_mana_cost_never_falls_below_the_floor(env):
    lua, ns = env
    # Force a cost under 1 (0.5 base, then a 15% discount -> 0.425). The floor is 1.
    ns.Skills.byId.lightning_bolt.mana = lua.table_from([0.5, 0])
    st = char(env, lightning_bolt=1, conductor=3)
    assert ns.Tree.mana_cost(st, "lightning_bolt") == 1


def test_resist_pierce_and_immunity(env):
    lua, ns = env
    # Piercing Cold level 5 = 20 + 4*4 = 36 off a normal resist: 50 -> 14.
    # An immune monster (100) loses only a fifth of it: 100 - 7.2 = 92.8.
    st = char(env, piercing_cold=5)
    assert ns.Tree.effective_resist(st, "cold", 50) == pytest.approx(14.0)
    assert ns.Tree.effective_resist(st, "cold", 100) == pytest.approx(92.8)
    assert ns.Tree.effective_resist(st, "fire", 50) == pytest.approx(50.0)      # cold mastery says nothing about fire


def test_resist_cannot_go_below_minus_100(env):
    lua, ns = env
    st = char(env, piercing_cold=20)
    assert ns.Tree.effective_resist(st, "cold", -90) == -100


def test_damage_after_resist(env):
    lua, ns = env
    assert ns.Tree.after_resist(100, 25) == pytest.approx(75.0)
    assert ns.Tree.after_resist(100, -50) == pytest.approx(150.0)
    assert ns.Tree.after_resist(100, 100) == pytest.approx(0.0)
