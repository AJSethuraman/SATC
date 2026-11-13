"""Finder.lua: finding the creature ids whose model is the one wanted, so monsters get their skins instead of coming out white."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
TIMERS, SAID, MODELS = {}, {}, {}
CREATURE_FILE = {}                                   -- creature id -> the model file it loads (what the client would answer)
local function obj()
  local o = { scripts = {} }
  return setmetatable(o, { __index = function(t, k)
    if k == "SetCreature" then return function(self, id) if NO_SETCREATURE then error("nope") end self.cid = id end end
    if k == "GetModelFileID" then return function(self) return CREATURE_FILE[self.cid] end end
    return function(self, ...) return self end
  end })
end
function CreateFrame(kind) local o = obj(); o.kind = kind; if kind == "PlayerModel" then MODELS[#MODELS + 1] = o end return o end
UIParent = obj()
C_Timer = { After = function(sec, fn) TIMERS[#TIMERS + 1] = { sec = sec, fn = fn } end }
function run_timers(n) for _ = 1, n or 1 do local t = TIMERS; TIMERS = {}; for _, x in ipairs(t) do x.fn() end end end
function say(m) SAID[#SAID + 1] = m end
'''


@pytest.fixture()
def env():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    ns = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Finder.lua"), ns)
    return lua, ns


def said(lua):
    return [str(v) for v in lua.eval("SAID").values()]


# ---------------------------------------------------------------- the rules
def test_batches_cover_every_id_once_in_order(env):
    lua, ns = env
    b = [(x[1], x[2]) for x in ns.Finder.batches(1, 45, 20).values()]
    assert b == [(1, 20), (21, 40), (41, 45)]
    assert [(x[1], x[2]) for x in ns.Finder.batches(5, 5, 20).values()] == [(5, 5)]
    assert len(list(ns.Finder.batches(10, 9, 20).values())) == 0


def test_only_wanted_models_are_kept_a_few_of_each_and_never_twice(env):
    lua, ns = env
    found = lua.table()
    assert ns.Finder.consider(found, 999, 1) is False                       # not a model we want
    assert ns.Finder.consider(found, 126570, 1600) is True
    assert ns.Finder.consider(found, 126570, 1600) is False                 # the same id again
    for n in (1601, 1602, 1603, 1604):
        ns.Finder.consider(found, 126570, n)
    assert list(found[126570].values()) == [1600, 1601, 1602, 1603]         # the first four
    assert ns.Finder.npc_for(found, 126570) == 1600 and ns.Finder.npc_for(found, 125576) is None and ns.Finder.npc_for(None, 126570) is None


def test_complete_means_every_wanted_model_has_at_least_one_creature(env):
    lua, ns = env
    found = lua.table()
    for fid, npc in ((126570, 1), (124160, 2), (125576, 3), (125942, 4)):
        ns.Finder.consider(found, fid, npc)
    assert ns.Finder.complete(found) is False
    ns.Finder.consider(found, 123137, 5)
    assert ns.Finder.complete(found) is False                               # the skeleton mage is still missing
    ns.Finder.consider(found, 125947, 6)
    assert ns.Finder.complete(found) is True and ns.Finder.complete(None) is False


def test_the_wanted_models_are_exactly_the_ones_the_monsters_use():
    import re
    zone = (DREAD / "Zone.lua").read_text()
    used = {int(x) for x in re.findall(r"model = (\d+)", zone)}
    lua = lupa.LuaRuntime()
    ns = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Finder.lua"), ns)
    wanted = {int(k) for k in ns.Finder.TARGETS.keys()}
    assert used == wanted                                                     # every model a monster uses is searched for, and nothing else


# ---------------------------------------------------------------- the scan
def seed_files(lua, mapping):
    for npc, fid in mapping.items():
        lua.execute(f"CREATURE_FILE[{npc}] = {fid}")


def test_a_scan_asks_the_client_which_model_each_creature_loads_and_keeps_the_matches(env):
    lua, ns = env
    seed_files(lua, {7: 126570, 25: 124160, 26: 111111, 41: 125576})
    lua.execute("DreadDB = nil")
    assert ns.Finder.start(1, 60, lua.eval("say")) is True
    assert ns.Finder.running() is True
    assert len(list(lua.eval("MODELS").values())) == 20                     # a pool of hidden models, reused
    lua.eval("run_timers")(2)                                                # two batches in: 1-20 and 21-40 read
    assert ns.Finder.running() is True
    lua.eval("run_timers")(1)                                                # the third, 41-60, and then there is nothing left
    f = lua.eval("DreadDB.found")
    assert f[126570][1] == 7 and f[124160][1] == 25 and f[125576][1] == 41 and f[111111] is None
    assert ns.Finder.running() is False
    msgs = said(lua)
    assert "found creature 7 = zombie" in msgs and "found creature 25 = ghoul" in msgs and "found creature 41 = rat" in msgs
    assert any("model search done: 3 creature id(s) found" in m for m in msgs)
    assert lua.eval("DreadDB.found_scan.done") is True


def test_a_scan_stops_early_once_every_wanted_model_is_covered(env):
    lua, ns = env
    seed_files(lua, {3: 126570, 4: 124160, 5: 125576, 6: 125942, 7: 123137, 8: 125947})
    ns.Finder.start(1, 100000, lua.eval("say"))
    lua.eval("run_timers")(5)
    assert ns.Finder.running() is False                                      # found in the first batch: it did not scan on to 100000
    assert any("model search complete" in m and "every monster covered" in m for m in said(lua))
    assert lua.eval("DreadDB.found_scan.done") is True and lua.eval("DreadDB.found_scan.at") == 1


def test_a_scan_can_be_stopped_and_cannot_be_started_twice(env):
    lua, ns = env
    assert ns.Finder.start(1, 100000, lua.eval("say")) is True
    assert ns.Finder.start(1, 100000, lua.eval("say")) is False
    lua.eval("run_timers")(2)
    ns.Finder.stop()
    lua.eval("run_timers")(2)
    assert ns.Finder.running() is False and any("model search stopped" in m for m in said(lua))
    assert lua.eval("DreadDB.found_scan.done") is False                       # stopped is not finished: it may be run again


def test_a_client_that_refuses_creature_ids_does_not_break_the_scan(env):
    lua, ns = env
    lua.execute("NO_SETCREATURE = true")
    ns.Finder.start(1, 40, lua.eval("say"))
    lua.eval("run_timers")(4)
    assert ns.Finder.running() is False and lua.eval("next(DreadDB.found)") is None


def test_progress_is_reported_every_hundred_batches(env):
    lua, ns = env
    ns.Finder.start(1, 20 * 120, lua.eval("say"))
    lua.eval("run_timers")(105)
    assert any("model search: up to creature 2000" in m for m in said(lua))
