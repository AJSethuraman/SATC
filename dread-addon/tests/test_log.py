"""Log.lua (Dread's own message window) against a stand-in client."""
from pathlib import Path
import re
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
ALL, PRINTED = {}, {}
local function obj(parent)
  local o = { scripts = {}, shown = false, parent = parent, lines = {} }
  ALL[#ALL + 1] = o
  return setmetatable(o, { __index = function(t, k)
    if not k:match("^%u") then return nil end
    if k == "SetScript" then return function(self, n, f) self.scripts[n] = f end end
    if k == "Show" then return function(self) self.shown = true end end
    if k == "Hide" then return function(self) self.shown = false end end
    if k == "IsShown" then return function(self) return self.shown end end
    if k == "SetFontObject" then return function(self, f) if f == nil then error("font object is nil") end if NO_FONTS then error("no such font") end self.fontset = true end end
    if k == "SetFont" then return function(self, path, size, flags) if NO_FONTS or NO_FONT_FILE then error("cannot load font") end self.fontset = true end end
    if k == "AddMessage" then return function(self, m) if not self.fontset then error("Font not set") end self.lines[#self.lines + 1] = m end end
    if k == "Clear" then return function(self) self.lines = {} self.cleared = (self.cleared or 0) + 1 end end
    if k == "SetText" then return function(self, t) if (self.kind == "EditBox" or self.kind == "ScrollingMessageFrame") and not self.fontset then error("Font not set") end self.text = t end end
    if k == "SetSize" then return function(self, w, h) self.size = { w, h } end end
    if k == "GetWidth" then return function(self) return self.size and self.size[1] or 100 end end
    if k == "GetHeight" then return function(self) return self.size and self.size[2] or 100 end end
    if k == "SetPoint" then return function(self, p, rel, rp, x, y)
      if type(rel) == "number" or rel == nil then x, y, rel, rp = rel or 0, rp or 0, nil, p end
      self.pts = { p, rel, rp, x or 0, y or 0 } end end
    if k == "GetPoint" then return function(self) local q = self.pts or { "CENTER", nil, "CENTER", 0, 0 } return q[1], q[2], q[3], q[4], q[5] end end
    if k == "StartMoving" then return function(self) self.moving = true end end
    if k == "StartSizing" then return function(self) self.sizing = true end end
    if k == "StopMovingOrSizing" then return function(self) self.moving, self.sizing = false, false end end
    if k == "SetFocus" then return function(self) self.focused = true end end
    if k == "HighlightText" then return function(self) self.highlighted = true end end
    if k == "CreateTexture" or k == "CreateFontString" then return function(self) return obj(self) end end
    return function(self, ...) return self end
  end })
end
function CreateFrame(kind, name, parent) local o = obj(parent); o.kind = kind; o.name = name return o end
UIParent = obj()
function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end PRINTED[#PRINTED + 1] = table.concat(t, " ") end
function date() return "12:34:56" end
function find_frame(kind) for _, o in ipairs(ALL) do if o.kind == kind then return o end end end
function find_button(text) for _, o in ipairs(ALL) do if o.kind == "Button" and o.text == text then return o end end end
'''


def boot(prelude=""):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK + "\n" + prelude)
    ns = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Log.lua"), ns)
    return lua, ns


def window(lua):
    return lua.eval("(function() for _, o in ipairs(ALL) do if o.name == 'DreadLogFrame' then return o end end end)()")


def msgframe(lua):
    return lua.eval("(function() for _, o in ipairs(ALL) do if o.kind == 'ScrollingMessageFrame' then return o end end end)()")


def lines(ns):
    return [str(v) for v in ns.Log.lines().values()]


def printed(lua):
    return [str(v) for v in lua.eval("PRINTED").values()]


def test_a_message_lands_in_the_window_with_a_timestamp_and_opens_it():
    lua, ns = boot()
    ns.log("hello there")
    assert window(lua).shown is True
    assert len(lines(ns)) == 1 and lines(ns)[0].endswith("hello there") and "12:34:56" in lines(ns)[0]
    assert list(msgframe(lua).lines.values()) == lines(ns)


def test_nothing_goes_to_the_general_chat_tab_by_default():
    lua, ns = boot()
    ns.log("quiet please")
    assert printed(lua) == []


def test_chat_mirroring_can_be_switched_on_and_off():
    lua, ns = boot()
    assert ns.Log.set_chat(True) is True
    ns.log("loud")
    assert printed(lua) == ["loud"]                                      # the message, without the timestamp
    assert ns.Log.set_chat(False) is False
    ns.log("quiet again")
    assert printed(lua) == ["loud"]


def test_closing_the_window_keeps_it_closed_until_you_ask_for_it():
    lua, ns = boot()
    ns.log("first")
    lua.eval("find_button('X')").scripts.OnClick(lua.eval("find_button('X')"))
    assert window(lua).shown is False and lua.eval("DreadDB.log.hidden") is True
    ns.log("second")                                                     # arrives while closed
    assert window(lua).shown is False                                    # and does not reopen it
    assert ns.Log.toggle() is True                                       # /dread log opens it
    assert window(lua).shown is True and lua.eval("DreadDB.log.hidden") is None
    assert [l.split(" ", 1)[1] for l in lines(ns)] == ["first", "second"]
    assert ns.Log.toggle() is False and window(lua).shown is False


def test_messages_sent_before_the_window_exists_replay_into_it_when_it_is_built():
    lua, ns = boot("DreadDB = { log = { hidden = true } }")              # closed from last time
    ns.log("one"); ns.log("two")
    assert window(lua).shown is False
    ns.Log.toggle()
    assert [l.split(" ", 1)[1] for l in msgframe(lua).lines.values()] == ["one", "two"]


def test_only_the_last_500_lines_are_kept():
    lua, ns = boot()
    for i in range(520):
        ns.log(f"line {i}")
    got = lines(ns)
    assert len(got) == 500 and got[0].endswith("line 20") and got[-1].endswith("line 519")


def test_clear_empties_the_buffer_and_the_window():
    lua, ns = boot()
    ns.log("a"); ns.log("b")
    b = lua.eval("find_button('Clear')")
    b.scripts.OnClick(b)
    assert lines(ns) == [] and msgframe(lua).cleared == 1
    ns.log("c")
    assert len(lines(ns)) == 1


def test_copy_gives_plain_text_with_colour_codes_and_timestamps_colour_removed():
    lua, ns = boot()
    ns.log("|cffff5555Dread|r pings: 6 of 10 answered")
    ns.log("plain line")
    ns.Log.copy()
    edit = lua.eval("(function() for _, o in ipairs(ALL) do if o.kind == 'EditBox' then return o end end end)()")
    box = lua.eval("find_frame('Frame')")
    assert "|c" not in str(edit.text) and "|r" not in str(edit.text)
    assert str(edit.text) == "12:34:56 Dread pings: 6 of 10 answered\n12:34:56 plain line"
    assert edit.focused is True and edit.highlighted is True            # ready for Ctrl+C
    ns.Log.copy()                                                        # opening it twice does not stack boxes
    assert len([o for o in lua.eval("ALL").values() if o.kind == "EditBox"]) == 1


def test_where_you_put_the_window_and_how_big_you_made_it_is_saved_and_restored():
    lua, ns = boot()
    ns.log("x")
    w = window(lua)
    bar = [o for o in lua.eval("ALL").values() if o.kind == "Frame" and o.scripts.OnDragStop is not None][0]
    bar.scripts.OnDragStart(bar)
    assert w.moving is True
    lua.eval("function(w) w.pts = { 'BOTTOMRIGHT', nil, 'BOTTOMRIGHT', -30, 40 }; w.size = { 600, 300 } end")(w)
    bar.scripts.OnDragStop(bar)
    saved = lua.eval("DreadDB.log")
    assert saved.w == 600 and saved.h == 300
    assert (saved.point[1], saved.point[2], saved.point[3], saved.point[4]) == ("BOTTOMRIGHT", "BOTTOMRIGHT", -30, 40)
    # a fresh session reads it back
    lua2, ns2 = boot("DreadDB = { log = { point = { 'BOTTOMRIGHT', 'BOTTOMRIGHT', -30, 40 }, w = 600, h = 300 } }")
    ns2.log("again")
    w2 = window(lua2)
    assert w2.size[1] == 600 and w2.size[2] == 300 and w2.pts[1] == "BOTTOMRIGHT" and w2.pts[4] == -30


def test_a_client_that_cannot_make_the_window_still_keeps_the_messages():
    lua, ns = boot("CreateFrame = function() error('no frames today') end")
    ns.log("still here")
    assert lines(ns)[0].endswith("still here")


# ---------------------------------------------------------------- every module uses it
def test_every_modules_messages_go_to_the_log_not_to_chat_and_the_toc_loads_the_log_first():
    toc = (DREAD / "Dread.toc").read_text().splitlines()
    luas = [l for l in toc if l.endswith(".lua")]
    assert luas[0] == "Log.lua"
    for f in ("Net.lua", "Visuals.lua", "Game.lua", "Dread.lua"):
        src = (DREAD / f).read_text()
        assert "ns.log(msg)" in src, f"{f} does not use the log"
        assert not re.search(r'^\s*print\(', src, re.M), f"{f} prints straight to chat"


# ---------------------------------------------------------------- "I no longer see any text"
def test_a_message_window_with_no_chat_font_still_shows_text_by_using_a_font_file():
    # ChatFontNormal is not defined in the stand-in, like a client where it is missing: the old code never set a font
    # and WoW raised "Font not set" from AddMessage, so every message vanished.
    lua, ns = boot()
    ns.log("visible please")
    assert msgframe(lua).fontset is True
    assert [l.split(" ", 1)[1] for l in msgframe(lua).lines.values()] == ["visible please"]
    assert printed(lua) == []                                            # and it did not need the chat tab


def test_the_chat_font_is_used_when_there_is_one():
    lua, ns = boot("ChatFontNormal = {}")
    ns.log("x")
    assert msgframe(lua).fontset is True and len(list(msgframe(lua).lines.values())) == 1


def test_when_no_font_can_be_set_at_all_messages_go_to_the_chat_tab_instead_of_vanishing():
    lua, ns = boot("NO_FONTS = true")
    ns.log("must not be lost")
    assert printed(lua) == ["must not be lost"]                          # the fallback
    assert lines(ns)[0].endswith("must not be lost")                     # and the buffer has it


def test_with_chat_mirroring_on_a_failed_window_does_not_print_twice():
    lua, ns = boot("NO_FONTS = true")
    ns.Log.set_chat(True)
    ns.log("once")
    assert printed(lua) == ["once"]


def test_the_copy_box_gets_a_font_too():
    lua, ns = boot()
    ns.log("copy me")
    ns.Log.copy()                                                        # SetText on an EditBox with no font raises in the real client
    edit = lua.eval("(function() for _, o in ipairs(ALL) do if o.kind == 'EditBox' then return o end end end)()")
    assert edit.fontset is True and "copy me" in str(edit.text)


def test_an_error_inside_the_window_does_not_stop_the_command_that_logged():
    lua, ns = boot("NO_FONTS = true")
    ns.log("one"); ns.log("two"); ns.log("three")                        # none of these raises
    assert len(lines(ns)) == 3
