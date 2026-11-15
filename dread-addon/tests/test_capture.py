"""Capture.lua: what a play session recorded, and the report made from it. Numbers are worked by hand in the comments."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"


@pytest.fixture()
def env():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Items", "Capture"):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


def ev(lua, **kw):
    return lua.table_from(kw)


def session(env, build="1 Jan"):
    return env[1].Capture.new_session(build, 0)


def play(env, s, seconds):
    for _ in range(int(seconds)):
        env[1].Capture.tick(s, 1)


# ---------------------------------------------------------------- counting
def test_time_goes_to_the_area_you_are_in_and_only_while_the_game_runs(env):
    lua, ns = env
    s = session(env)
    play(env, s, 5)                                                 # no area yet: counted in the total only
    ns.Capture.enter(s, "moor"); play(env, s, 60)
    ns.Capture.enter(s, "cave"); play(env, s, 30)
    ns.Capture.enter(s, "moor"); play(env, s, 10)
    assert s.play == 105 and s.areas.moor.time == 70 and s.areas.cave.time == 30 and s.areas.moor.entered == 2


def test_kills_damage_and_casts_are_counted_by_area_and_name(env):
    lua, ns = env
    s = session(env)
    ns.Capture.enter(s, "moor")
    for e in (ev(lua, k="cast", id="arcing_bolts"), ev(lua, k="cast", id="arcing_bolts"), ev(lua, k="cast", id="wand"),
              ev(lua, k="hit", id="wand", dmg=7.5), ev(lua, k="hit", id="arcing_bolts", dmg=12.5),
              ev(lua, k="kill", name="Quill Rat"), ev(lua, k="kill", name="Quill Rat"), ev(lua, k="kill", name="Bone Walker"),
              ev(lua, k="hurt", amount=9, **{"from": "Quill Rat", "how": "thrown"})):
        ns.Capture.event(s, e)
    a = s.areas.moor
    assert s.casts.arcing_bolts == 2 and s.casts.wand == 1
    assert a.dealt == 20 and a.kills == 3 and a.taken == 9
    assert s.kills["Quill Rat"] == 2 and s.kills["Bone Walker"] == 1


def test_fps_is_averaged_and_the_lowest_is_kept_overall_and_per_area(env):
    lua, ns = env
    s = session(env)
    ns.Capture.enter(s, "moor")
    for f in (72, 70, 30):
        ns.Capture.sample_fps(s, f)
    ns.Capture.enter(s, "cave")
    ns.Capture.sample_fps(s, 60)
    ns.Capture.sample_fps(s, None); ns.Capture.sample_fps(s, 0)             # junk is ignored
    assert s.fps_n == 4 and s.fps_sum == 232 and s.fps_min == 30
    assert s.areas.moor.fps_min == 30 and s.areas.moor.fps_n == 3 and s.areas.cave.fps_min == 60


def test_the_same_error_every_frame_is_one_line_with_a_count_and_the_list_is_capped(env):
    lua, ns = env
    s = session(env)
    for _ in range(500):
        ns.Capture.error(s, "Game.lua:10: attempt to index nil")
    assert len(list(s.errors.values())) == 1 and s.errors[1].n == 500
    for i in range(40):
        ns.Capture.error(s, "different error " + str(i))
    assert len(list(s.errors.values())) == 12


# ---------------------------------------------------------------- deaths
def test_a_death_lists_what_hit_you_in_the_last_twelve_seconds_oldest_first(env):
    lua, ns = env
    s = session(env)
    ns.Capture.enter(s, "burial")
    play(env, s, 100)
    ns.Capture.event(s, ev(lua, k="hurt", amount=30, **{"from": "Bone Walker", "how": "melee"}))       # 100 s: too old by the death
    play(env, s, 20)
    ns.Capture.event(s, ev(lua, k="hurt", amount=22.4, **{"from": "The Marrowmother", "how": "thrown", "boss": True}))
    play(env, s, 3)
    ns.Capture.event(s, ev(lua, k="hurt", amount=18.6, **{"from": "The Marrowmother", "how": "thrown", "boss": True}))
    play(env, s, 1)
    why = ns.Capture.death(s, ev(lua, level=9, maxlife=120, awake=4, boss_awake=True))
    assert why == "death"
    d = s.deaths[1]
    hits = [(h["from"], h.amount, h.how, h.ago) for h in d.hits.values()]
    assert hits == [("The Marrowmother", 22, "thrown", 4.0), ("The Marrowmother", 19, "thrown", 1.0)]
    assert d.area == "burial" and d.level == 9 and d.maxlife == 120 and d.boss_awake is True and d.at == 124
    assert s.areas.burial.deaths == 1 and len(list(s.recent.values())) == 0


def test_only_the_last_thirty_deaths_are_kept(env):
    lua, ns = env
    s = session(env)
    for i in range(35):
        ns.Capture.death(s, ev(lua, level=i, maxlife=1))
    assert len(list(s.deaths.values())) == 30 and s.deaths[1].level == 5


# ---------------------------------------------------------------- what is worth a picture
def test_a_picture_is_allowed_after_a_gap_and_only_up_to_a_budget(env):
    lua, ns = env
    s = session(env)
    play(env, s, 100)
    assert ns.Capture.shot_allowed(s, "death") is True
    play(env, s, 5)
    assert ns.Capture.shot_allowed(s, "level 4") is False                 # 5 s after the last: too soon
    play(env, s, 11)
    assert ns.Capture.shot_allowed(s, "level 4") is True                  # 16 s: fine
    taken = 2
    for _ in range(60):                                                   # bounded, so a missing budget fails instead of looping
        play(env, s, 16)
        if not ns.Capture.shot_allowed(s, "x"):
            break
        taken += 1
    assert taken == 30 and s.shots == 30                                  # the budget


def test_rare_finds_and_bosses_are_worth_a_picture_and_ordinary_finds_are_not(env):
    lua, ns = env
    s = session(env)
    mk = lambda r: ev(lua, k="item", item=ev(lua, slot="ring", rarity=r, ilvl=5, base="Ring", stats=ev(lua, life=3)))
    assert ns.Capture.event(s, mk("common")) is None and ns.Capture.event(s, mk("magic")) is None
    assert ns.Capture.event(s, mk("rare")) == "found rare" and ns.Capture.event(s, mk("unique")) == "found unique"
    assert ns.Capture.event(s, ev(lua, k="boss_dead", name="The Marrowmother")) == "boss The Marrowmother"
    it = s["items"]
    assert it.common == 1 and it.magic == 1 and it.rare == 1 and it.unique == 1
    assert [f.rarity for f in s.finds.values()] == ["rare", "unique"]


def test_a_fight_picture_is_due_only_after_being_hit_and_a_quiet_minute_and_a_half(env):
    lua, ns = env
    s = session(env)
    play(env, s, 200)
    assert ns.Capture.combat_shot_due(s) is False                         # never hit
    ns.Capture.event(s, ev(lua, k="hurt", amount=5, **{"from": "x", "how": "melee"}))
    assert ns.Capture.combat_shot_due(s) is True
    ns.Capture.shot_allowed(s, "combat")
    play(env, s, 2)
    ns.Capture.event(s, ev(lua, k="hurt", amount=5, **{"from": "x", "how": "melee"}))
    assert ns.Capture.combat_shot_due(s) is False                         # one was taken 2 s ago
    play(env, s, 100)
    ns.Capture.event(s, ev(lua, k="hurt", amount=5, **{"from": "x", "how": "melee"}))
    assert ns.Capture.combat_shot_due(s) is True


# ---------------------------------------------------------------- storage and the picture call
def test_only_the_last_three_sessions_are_saved(env):
    lua, ns = env
    db = lua.table()
    for i in range(5):
        ns.Capture.session(db, "build " + str(i), i)
    assert len(list(db.cap.sessions.values())) == 3 and db.cap.sessions[1].build == "build 2"


def test_the_picture_call_is_made_a_moment_later_and_only_if_the_client_has_one(env):
    lua, ns = env
    assert ns.Capture.shot() is False                                     # no client call: nothing happens, no error
    lua.execute("SHOTS = 0; LATER = {}; function Screenshot() SHOTS = SHOTS + 1 end; C_Timer = { After = function(t, f) LATER[#LATER + 1] = { t = t, f = f } end }")
    assert ns.Capture.shot() is True and lua.eval("SHOTS") == 0           # not yet: it waits so the moment is on screen
    lua.execute("LATER[1].f()")
    assert lua.eval("SHOTS") == 1 and lua.eval("LATER[1].t") == pytest.approx(0.35)


# ---------------------------------------------------------------- the report
def test_the_report_says_what_happened_in_plain_text(env):
    lua, ns = env
    s = session(env, "12 Nov 02:10 UTC")
    ns.Capture.enter(s, "moor")
    play(env, s, 90)
    for f in (72, 70):
        ns.Capture.sample_fps(s, f)
    for e in (ev(lua, k="cast", id="arcing_bolts"), ev(lua, k="cast", id="arcing_bolts"), ev(lua, k="hit", id="arcing_bolts", dmg=40),
              ev(lua, k="kill", name="Quill Rat"), ev(lua, k="hurt", amount=10.4, **{"from": "Quill Rat", "how": "thrown"}),
              ev(lua, k="level", level=2), ev(lua, k="boss_dead", name="Rottenmaw the Unwelcome")):
        ns.Capture.event(s, e)
    ns.Capture.event(s, ev(lua, k="item", item=ev(lua, slot="ring", rarity="rare", ilvl=5, base="Ring", stats=ev(lua, life=3), title=None)))
    ns.Capture.death(s, ev(lua, level=2, maxlife=72, awake=2, boss_awake=False))
    ns.Capture.shot_allowed(s, "death")
    ns.Capture.error(s, "oops")
    text = str(ns.Capture.report(s, lua.table_from({"level": 2, "gear": "72 life", "settings": "zoom 1.4", "log": lua.table_from(["Found a thing", "Level 2!"])})))
    for needle in ("DREAD REPORT   build 12 Nov 02:10 UTC   played 1:30   fps avg 71, lowest 70",
                   "Character: level 2   72 life", "Settings: zoom 1.4",
                   "moor       1:30  kills   1  dealt    40  taken    10  deaths 1  fps 71/70  (entered 1x)",
                   "DEATHS: 1", "#1  moor at 1:30, level 2, 72 life: Quill Rat 10 thrown (0.0s before)",
                   "Rottenmaw the Unwelcome in moor at 1:30 (deaths before it: 0)",
                   "CASTS: arcing_bolts 2", "ITEMS FOUND: common 0, magic 0, rare 1, unique 0", "Rare Ring of Life (rare, level 5, moor)",
                   "LEVELS: 2 at 1:30 in moor", "SCREENSHOTS: 1 taken  (death@1:30)", "ERRORS:", "x1 in moor at 1:30: oops",
                   "LOG (last 2 lines)", "  Found a thing"):
        assert needle in text, needle


def test_an_empty_session_still_makes_a_report_that_says_nothing_happened(env):
    lua, ns = env
    text = str(ns.Capture.report(session(env)))
    assert "DEATHS: 0" in text and "BOSSES KILLED: none" in text and "CASTS: none" in text and "ERRORS: none" in text and "SCREENSHOTS: 0 taken" in text
