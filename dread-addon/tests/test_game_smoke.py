"""Game.lua needs the WoW API. This drives it through a stand-in client: open the window, spend a point, click, cast,
press keys, die, restart. It proves the wiring and that nothing errors; it cannot show how anything LOOKS."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
FRAMES, PRINTED, CURSOR, PROPAGATE = {}, {}, {0, 0}, {}
local NUM = { GetLeft = 0, GetBottom = 0, GetEffectiveScale = 1, GetFrameLevel = 1, GetWidth = 100, GetHeight = 100 }
local function obj(name)
  local o = { scripts = {}, shown = false }
  return setmetatable(o, { __index = function(t, k)
    if NUM[k] then return function() return NUM[k] end end
    if k == "SetScript" then return function(self, n, f) self.scripts[n] = f end end
    if k == "Show" then return function(self) self.shown = true end end
    if k == "Hide" then return function(self) self.shown = false end end
    if k == "SetShown" then return function(self, b) self.shown = b and true or false end end
    if k == "IsShown" then return function(self) return self.shown end end
    if k == "SetScale" then return function(self, v) self.scale = v end end
    if k == "SetPropagateKeyboardInput" then return function(self, v) PROPAGATE[#PROPAGATE + 1] = v end end
    if k == "CreateTexture" or k == "CreateFontString" then return function() return obj() end end
    if k == "CreateLine" then return function() if NO_LINES then error("no lines here") end return obj() end end
    if k == "SetCreature" then return function() if NO_MODELS then error("no models here") end end end
    return function(self, ...) return self end
  end })
end
function CreateFrame(kind, name, parent, tmpl) local o = obj(); if name then FRAMES[name] = o end return o end
UIParent, GameTooltip = obj(), obj()
function GetCursorPosition() return CURSOR[1], CURSOR[2] end
function GetFramerate() return 60 end
function time() return 12345 end
function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end PRINTED[#PRINTED + 1] = table.concat(t, " ") end
'''


def boot(prelude=""):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(prelude + "\n" + MOCK)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Combat", "Game"):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


def tick(lua, n, dt=1 / 30):
    f = lua.eval("FRAMES.DreadGameFrame")
    for _ in range(n):
        f.scripts.OnUpdate(f, dt)


def click(lua, button, x, y):
    lua.execute(f"CURSOR[1], CURSOR[2] = {x}, {y}")
    f = lua.eval("FRAMES.DreadGameFrame")
    f.scripts.OnMouseDown(f, button)


def choose_scorch_and_close_the_tree(lua, ns):
    b = ns.Game.tree_buttons.scorch
    b.scripts.OnClick(b)
    f = lua.eval("FRAMES.DreadGameFrame")
    f.scripts.OnKeyDown(f, "K")                                       # close the tree: now the fight can start
    assert lua.eval("FRAMES.DreadTreeFrame.shown") is False


def test_opening_with_no_spells_shows_the_tree_and_a_point_can_be_spent():
    lua, ns = boot()
    ns.Game.toggle()
    assert lua.eval("FRAMES.DreadTreeFrame.shown") is True          # a new character is sent straight to the tree
    assert len(list(ns.Game.tree_buttons.keys())) == 30
    b = ns.Game.tree_buttons.scorch
    b.scripts.OnClick(b)
    assert ns.Game.world().player.st.points.scorch == 1
    assert lua.eval("DreadDB.char.points.scorch") == 1               # and it is saved
    b2 = ns.Game.tree_buttons.fireball                               # a locked skill: the click is refused, with a reason
    b2.scripts.OnClick(b2)
    assert ns.Game.world().player.st.points.fireball is None
    assert any("level 18" in str(v) or "no points left" in str(v) for v in lua.eval("PRINTED").values())


def test_walk_cast_kill_and_the_keys():
    lua, ns = boot()
    ns.Game.toggle()
    choose_scorch_and_close_the_tree(lua, ns)
    tick(lua, 3)
    w = ns.Game.world()
    assert len(list(w.monsters.keys())) == 4                          # wave 1
    # key 1 selects the first learned spell and is swallowed; an unrelated key passes through to the game
    f = lua.eval("FRAMES.DreadGameFrame")
    f.scripts.OnKeyDown(f, "1")
    f.scripts.OnKeyDown(f, "W")
    prop = list(lua.eval("PROPAGATE").values())
    assert prop[-2] is False and prop[-1] is True
    # left click walks
    click(lua, "LeftButton", 500, 60)
    tick(lua, 30)
    assert w.player.x > 400                                           # 140 units in a second, from x = 300
    # right click casts at the nearest monster, over and over, until something is hurt
    hurt = False
    for _ in range(20):
        nearest = min((w.monsters[i] for i in range(1, 5) if not w.monsters[i].dead),
                      key=lambda m: (m.x - w.player.x) ** 2 + (m.y - w.player.y) ** 2, default=None)
        if nearest is None:
            break
        click(lua, "RightButton", nearest.x, nearest.y)
        tick(lua, 6)
        if any(w.monsters[i].life < w.monsters[i].maxlife or w.monsters[i].dead for i in range(1, 5)):
            hurt = True
            break
    assert hurt
    # K opens and closes the tree
    shown = lua.eval("FRAMES.DreadTreeFrame.shown")
    f.scripts.OnKeyDown(f, "K")
    assert lua.eval("FRAMES.DreadTreeFrame.shown") != shown


def test_dying_then_a_click_starts_again_and_keeps_the_character():
    lua, ns = boot()
    ns.Game.toggle()
    choose_scorch_and_close_the_tree(lua, ns)
    tick(lua, 3)
    w = ns.Game.world()
    w.player.life = 0.5
    tick(lua, 600)                                                    # the wave catches up with a player who does nothing
    assert ns.Game.world().over is True
    click(lua, "LeftButton", 100, 100)
    w2 = ns.Game.world()
    assert w2.over is False and w2.player.st.points.scorch == 1       # a fresh fight, the same character


def test_a_client_without_lines_or_models_still_opens():
    lua, ns = boot("NO_LINES = true\nNO_MODELS = true")
    # SetCreature failing is reported by an error from the client; the window must not take the whole addon down
    try:
        ns.Game.toggle()
        tick(lua, 3)
        survived = True
    except Exception as e:                                            # pragma: no cover
        survived = False
        print(e)
    assert survived


def test_clearing_the_field_brings_the_next_wave_and_it_is_bigger():
    lua, ns = boot()
    ns.Game.toggle()
    choose_scorch_and_close_the_tree(lua, ns)
    tick(lua, 2)
    w = ns.Game.world()
    assert ns.Game.wave() == 1 and len(list(w.monsters.keys())) == 4
    for i in range(1, 5):
        w.monsters[i].dead = True
        w.monsters[i].died_at = w.time
    tick(lua, 2)
    assert ns.Game.wave() == 2
    assert len(list(w.monsters.keys())) == 4 + 6                      # wave 2 is 2 + 2*2 = 6 more


def test_nothing_attacks_while_you_are_still_choosing(env=None):
    # What happened on the first real run: the window opened on the tree, a wave spawned and killed the player
    # before the first point was spent.
    lua, ns = boot()
    ns.Game.toggle()
    tick(lua, 900)                                                    # thirty seconds of dithering over the tree
    w = ns.Game.world()
    assert w.over is False and w.player.life == w.player.maxlife
    assert len(list(w.monsters.keys())) == 0 and ns.Game.wave() == 0


def test_the_fight_waits_for_a_spell_even_with_the_tree_closed():
    lua, ns = boot()
    ns.Game.toggle()
    lua.eval("FRAMES.DreadTreeFrame:Hide()")                          # closed without choosing anything
    tick(lua, 300)
    assert ns.Game.wave() == 0 and ns.Game.world().over is False


def test_opening_the_tree_mid_fight_pauses_it():
    lua, ns = boot()
    ns.Game.toggle()
    choose_scorch_and_close_the_tree(lua, ns)
    tick(lua, 5)
    w = ns.Game.world()
    f = lua.eval("FRAMES.DreadGameFrame")
    f.scripts.OnKeyDown(f, "K")
    t = w.time
    tick(lua, 60)
    assert w.time == t                                                # frozen while the tree is up
    f.scripts.OnKeyDown(f, "K")
    tick(lua, 5)
    assert w.time > t


def test_window_scale_is_set_saved_and_kept_sane():
    lua, ns = boot()
    ns.Game.toggle()
    assert lua.eval("DreadDB.scale") == pytest.approx(1.6)            # bigger than the 640 x 400 it is built at
    assert lua.eval("FRAMES.DreadGameFrame.scale") == pytest.approx(1.6)      # and the window really is resized
    assert ns.Game.set_scale(2.0) == 2.0 and lua.eval("DreadDB.scale") == 2.0
    assert lua.eval("FRAMES.DreadGameFrame.scale") == 2.0 and lua.eval("FRAMES.DreadTreeFrame.scale") == 2.0
    assert ns.Game.set_scale(50) == 3 and ns.Game.set_scale(0.1) == 0.8
    assert ns.Game.set_scale("nonsense") == pytest.approx(1.6)
