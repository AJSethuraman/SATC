"""Visuals.lua needs the WoW API, so this runs it against a stand-in that answers every call. It cannot say what
the real client draws. It only proves the file loads, runs end to end, and survives a client that refuses calls."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
local printed, timers = {}, {}
function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end printed[#printed + 1] = table.concat(t, " ") end
local function obj(refuse)
  local o = { scripts = {} }
  return setmetatable(o, { __index = function(t, k)
    if k == "SetScript" then return function(self, n, f) self.scripts[n] = f end end
    if k == "CreateTexture" or k == "CreateFontString" then return function() return obj(refuse) end end
    if refuse and refuse[k] then return function() error("call refused by client") end end
    return function(self, ...) return self end
  end })
end
function CreateFrame(kind, name, parent, tmpl) return obj(REFUSE) end
UIParent = obj()
C_Timer = { After = function(sec, fn) timers[#timers + 1] = fn end }
function run_timers() for _, f in ipairs(timers) do f() end timers = {} end
function get_printed() return printed end
'''


def run_with(refuse):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute("REFUSE = " + refuse + "\n" + MOCK)
    ns = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Visuals.lua"), ns)
    ns.Visuals.run()
    lua.eval("run_timers")()
    return [str(v) for v in lua.eval("get_printed")().values()], lua


def test_runs_end_to_end_and_reports_every_probe():
    out, lua = run_with("nil")
    text = "\n".join(out)
    assert "model player: no error" in text and "texture Interface\\WorldMap\\Mulgore\\Mulgore1: no error" in text
    assert text.count("model ") >= 20            # 10 models x (probe + file id)
    assert "done." in text
    assert "test3" in list(lua.eval("DreadDB.results").keys())


def test_a_client_that_refuses_calls_is_reported_not_fatal():
    out, lua = run_with("{ SetCreature = true, SetModel = true, SetUnit = true, GetModelFileID = true }")
    text = "\n".join(out)
    assert "ERROR" in text and "call refused by client" in text
    assert "(no such call)" in text
    assert "done." in text                       # one failing family did not stop the textures or the summary
    assert "texture Interface\\FrameGeneral\\UI-Background-Rock: no error" in text
