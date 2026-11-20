"""The window and the flow (/gaunt), driven through a stand-in for the WoW client. It cannot say how anything looks; it proves the file
loads on both Lua versions, every step runs, and the rules (what hides behind a wall, what a key does) hold."""
import math
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
G = Path(__file__).resolve().parents[1] / "Gauntlet"

MOCK = r'''
ALL, FRAMES, PRINTED, SOUNDS, TIMERS = {}, {}, {}, {}, {}
SHOTS, CURSOR, BAD_TEX = 0, { 500, 400 }, {}
SlashCmdList = {}
local function obj(kind, name)
  local o = { kind = kind, name = name, scripts = {}, shown = true, level = 1 }
  ALL[#ALL + 1] = o
  return setmetatable(o, { __index = function(t, k)
    if k == "SetScript" then return function(self, n, f) self.scripts[n] = f end end
    if k == "CreateTexture" then return function(self) return obj("Texture") end end
    if k == "CreateFontString" then return function(self) return obj("FontString") end end
    if k == "SetTexture" then return function(self, id) if BAD_TEX[id] then error("bad texture") end self.texture, self.flat = id, nil end end
    if k == "SetColorTexture" then return function(self, r, g, b) self.flat, self.texture = { r, g, b }, nil end end
    if k == "SetTexCoord" then return function(self, a, b, c, d) self.coords = { a, b, c, d } end end
    if k == "SetVertexColor" then return function(self, r, g, b) self.color = { r, g, b } end end
    if k == "SetSize" then return function(self, w, h) self.size = { w, h } end end
    if k == "SetPoint" then return function(self, p, rel, rp, x, y)
      if type(rel) == "number" or rel == nil then x, y, rel, rp = rel, rp, nil, p end
      self.pts = { point = p, x = x or 0, y = y or 0 } end end
    if k == "ClearAllPoints" then return function(self) self.pts = nil end end
    if k == "Show" then return function(self) self.shown = true end end
    if k == "Hide" then return function(self) self.shown = false end end
    if k == "IsShown" then return function(self) return self.shown end end
    if k == "SetText" then return function(self, s) self.text = s end end
    if k == "SetAlpha" then return function(self, a) self.alpha = a end end
    if k == "SetFrameLevel" then return function(self, l) self.level = l end end
    if k == "GetFrameLevel" then return function(self) return self.level end end
    if k == "GetEffectiveScale" then return function() return 1 end end
    if k == "GetCenter" then return function() return 500, 400 end end
    if k == "SetCreature" then return function(self, id) if NO_MODELS then error("no models") end self.creature = id end end
    if k == "SetModel" then return function(self, id) if NO_MODELS then error("no models") end self.model = id end end
    if k == "SetPropagateKeyboardInput" then return function(self, v) self.propagate = v end end
    if k == "HighlightText" then return function(self) self.highlighted = true end end
    return function(self, ...) return self end
  end })
end
function CreateFrame(kind, name) local o = obj(kind, name); if name then FRAMES[name] = o end return o end
UIParent = obj("UIParent")
function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end PRINTED[#PRINTED + 1] = table.concat(t, " ") end
function time() return 777 end
function GetCursorPosition() return CURSOR[1], CURSOR[2] end
function GetScreenWidth() return 2560 end
function GetScreenHeight() return 1440 end
function PlaySoundFile(id) SOUNDS[#SOUNDS + 1] = id; return true end
function Screenshot() SHOTS = SHOTS + 1 end
C_Timer = { After = function(sec, fn) TIMERS[#TIMERS + 1] = fn end }
function run_timers() local t = TIMERS; TIMERS = {}; for _, f in ipairs(t) do f() end end
'''


def boot(prelude=""):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK + "\n" + prelude)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Gauntlet', ns) end")
    for f in ("Ray", "Level", "Rules", "Nav", "Gen", "Play", "Bench", "Render", "Gauntlet", "Main"):
        ld(str(G / f"{f}.lua"), ns)
    return lua, ns


def frame(lua):
    return lua.eval("FRAMES.GauntletFrame")


def tick(lua, n, dt=1 / 75):
    f = frame(lua)
    for _ in range(n):
        f.scripts.OnUpdate(f, dt)


def key(lua, k, down=True):
    f = frame(lua)
    (f.scripts.OnKeyDown if down else f.scripts.OnKeyUp)(f, k)


def said(lua):
    return [str(v) for v in lua.eval("PRINTED").values()]


def to_walk(lua, ns):
    ns.Gauntlet.walk()
    tick(lua, 2)
    return ns.Gauntlet.state()


def ahead(S, dist):
    """A point `dist` in front of where the player stands and faces."""
    return S.x + math.cos(S.ang) * dist, S.y + math.sin(S.ang) * dist


# ---------------------------------------------------------------- the whole run
def test_the_run_goes_speed_test_then_assets_then_a_walk_and_saves_a_report():
    lua, ns = boot()
    ns.Gauntlet.run()
    assert ns.Gauntlet.mode() == "bench" and frame(lua).shown
    n_passes = 0
    widths = []
    for _ in range(3000):
        r = ns.Gauntlet.render()
        if not widths or widths[-1] != r.n:
            widths.append(r.n)
        tick(lua, 1)
        if ns.Gauntlet.mode() == "walk":
            break
    assert widths == [160, 240, 320]                                            # each width ran in turn
    assert ns.Gauntlet.mode() == "walk"
    S = ns.Gauntlet.state()
    assert [int(r.columns) for r in S.results.values()] == [160, 240, 320]
    assert all(abs(r.avg - 75) < 1 for r in S.results.values())                  # the stand-in runs at 75 fps
    text = str(lua.eval("GauntletDB.report"))
    assert "TEST 1" in text and "TEST 2" in text and "verdict: GO (use 320 columns)" in text
    assert "wall textures that draw: 14 of 14" in text and "sound file 567721: will play" in text and "build" in text and "2560x1440" in text
    msgs = said(lua)
    assert any("speed test: GO" in m for m in msgs)


def test_screenshots_are_taken_for_you_during_the_speed_test_and_on_the_texture_page():
    lua, ns = boot()
    ns.Gauntlet.run()
    for _ in range(3000):
        tick(lua, 1)
        lua.eval("run_timers")()
        if ns.Gauntlet.mode() == "walk":
            break
    assert lua.eval("SHOTS") == 2


def test_a_run_makes_the_model_pool_once_and_the_texture_page_is_hidden_when_the_walk_starts():
    lua, ns = boot()
    ns.Gauntlet.run()
    R = ns.Gauntlet.render()
    assert len(list(R.models.values())) == 6
    for _ in range(3000):
        tick(lua, 1)
        if ns.Gauntlet.mode() == "walk":
            break
    assert all(not s.tex.shown for s in R.swatches.values())
    ns.Gauntlet.run()
    assert len(list(R.models.values())) == 6                                     # running again does not make more


# ---------------------------------------------------------------- the picture
def test_walls_are_drawn_as_strips_taller_when_nearer_with_the_right_texture_slice():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    shown = [c for c in R.cols.values() if c.tex.shown]
    assert len(shown) == 160 and all(c.tex.size[2] > 0 for c in shown)
    # facing +x from (3.5, 4.5) along the open row: the far wall at x 23 ("1" kind, the first texture) is 19.5 away: a strip 360 / 19.5 tall
    mid = R.cols[80]
    assert mid.tex.size[2] == pytest.approx(360 / 19.5, rel=0.01)
    assert mid.tex.texture == 129765 and mid.id == 1
    c = mid.tex.coords
    assert c[1] == pytest.approx(0.5, abs=0.1) and c[2] - c[1] == pytest.approx(1 / 40) and c[3] == 0 and c[4] == 1   # a 1/40 slice of the texture's width
    assert mid.tex.pts.y == pytest.approx((360 - 360 / 19.5) / 2)                  # centred on the horizon


def test_turning_to_a_nearer_wall_makes_its_strip_taller():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    far = R.cols[80].tex.size[2]                                                      # 19.5 away
    S.x, S.y, S.ang = 3.5, 1.5, -math.pi / 2                                          # next to the top wall (0.5 away), facing it
    tick(lua, 1)
    near = R.cols[80].tex.size[2]
    assert near == pytest.approx(360 * 1.2) and near > far * 20                       # 360 / 0.5 would be 720: it is capped at 1.2 of the view's height


def test_a_wall_texture_that_will_not_load_falls_back_to_its_plain_colour_and_the_rest_still_draw():
    lua, ns = boot("BAD_TEX = { [129765] = true }")
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    mid = R.cols[80]
    assert mid.tex.texture != 129765                                                  # the texture did not take
    assert tuple(round(v, 2) for v in mid.tex.flat.values()) == (0.55, 0.52, 0.5)
    assert R.wall_ok[1] is False
    S.x, S.y, S.ang = 18.5, 15.5, math.pi                                             # facing the dark brick room's wall, 0.5 away
    tick(lua, 1)                                                                      # a wall of another kind in view still takes its texture
    kinds = {c.id for c in R.cols.values() if c.tex.shown}
    assert 4 in kinds and R.cols[80].tex.shown


def test_nearer_walls_are_brighter_and_up_down_faces_are_darker():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    S.x, S.y, S.ang = 5.5, 3.5, 0                                                      # the wall at x 7 (row 3) is 1.5 away
    tick(lua, 1)
    bright = R.cols[80].tex.color[1]
    S.x, S.y, S.ang = 1.5, 3.5, 0                                                      # 5.5 away
    tick(lua, 1)
    dim = R.cols[80].tex.color[1]
    assert bright > dim and bright == pytest.approx(min(1, 1.15 - 1.5 * 0.09))
    S.x, S.y, S.ang = 3.5, 3.5, math.pi / 2                                            # facing down at the wall at y 6: an up/down face, 2.5 away
    tick(lua, 1)
    c = R.cols[80].tex.color[1]
    assert c == pytest.approx((1.15 - 0.09 * 2.5) * 0.8)                                # darkened to 0.8 of what a left/right face would be


# ---------------------------------------------------------------- the models
def models_shown(R):
    return [m for m in R.models.values() if m.shown]


def test_an_enemy_in_front_is_drawn_at_its_column_sized_by_distance_and_one_behind_you_is_not():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    S.x, S.y, S.ang = 6.5, 4.5, 0                                                      # the wolf is at 10.5, 4.5: 4 ahead, no wall between
    tick(lua, 1)
    m = R.models[1]
    assert m.shown and m.creature == 299
    size = 360 / 4 * 0.85
    assert m.size[2] == pytest.approx(size) and m.size[1] == pytest.approx(size * 0.8)
    assert m.pts.x == pytest.approx(320, abs=3)                                        # in the middle of the 640-wide view
    S.ang = math.pi                                                                    # turn round: it is behind you now
    tick(lua, 1)
    assert not m.shown


def test_a_nearer_enemy_is_drawn_bigger_and_in_front_of_a_farther_one():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    S.x, S.y, S.ang = 3.5, 4.5, 0
    S.enemies[1].x, S.enemies[1].y = 10.5, 4.5
    S.enemies[2].x, S.enemies[2].y = 6.5, 4.5
    tick(lua, 1)
    far, near = R.models[1], R.models[2]
    assert near.size[2] > far.size[2] and near.level > far.level


def test_an_enemy_behind_a_wall_is_hidden_and_shows_again_when_you_can_see_it():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    # the zombie is in the lower right room: from the start room facing it, walls are in the way
    z = S.enemies[6]
    S.x, S.y = 3.5, 4.5
    S.ang = math.atan2(z.y - S.y, z.x - S.x)
    tick(lua, 1)
    assert not R.models[6].shown
    S.x, S.y = 20.5, 17.0                                                              # in the same big room, clear sight
    S.ang = math.atan2(z.y - S.y, z.x - S.x)
    tick(lua, 1)
    assert R.models[6].shown and R.models[6].model == 126570                           # drawn from the bare model file


def test_a_downed_enemy_is_not_drawn():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    S.x, S.y, S.ang = 6.5, 4.5, 0
    tick(lua, 1)
    assert R.models[1].shown
    S.enemies[1].dead = True
    tick(lua, 1)
    assert not R.models[1].shown


def test_a_client_that_cannot_load_models_does_not_stop_the_walk_and_the_report_says_so():
    lua, ns = boot("NO_MODELS = true")
    ns.Gauntlet.run()
    for _ in range(3000):
        tick(lua, 1)
        if ns.Gauntlet.mode() == "walk":
            break
    text = str(lua.eval("GauntletDB.report"))
    assert "model wolf" in text and "FAILED" in text


# ---------------------------------------------------------------- keys and the mouse
def test_w_walks_forward_s_back_a_d_strafe_q_e_turn_and_nothing_goes_through_walls():
    lua, ns = boot()
    S = to_walk(lua, ns)
    x0, y0 = S.x, S.y
    key(lua, "W"); tick(lua, 15); key(lua, "W", False)
    assert S.x > x0 + 0.5 and S.y == pytest.approx(y0)                                  # facing +x: forward is +x
    x1 = S.x
    key(lua, "S"); tick(lua, 15); key(lua, "S", False)
    assert S.x < x1 - 0.5
    y1 = S.y
    key(lua, "D"); tick(lua, 15); key(lua, "D", False)                                 # facing +x, right is +y (down the page)
    assert S.y > y1 + 0.5
    key(lua, "A"); tick(lua, 15); key(lua, "A", False)
    assert S.y == pytest.approx(y1, abs=0.01)
    a0 = S.ang
    key(lua, "E"); tick(lua, 15); key(lua, "E", False)
    assert S.ang > a0 + 0.3
    key(lua, "Q"); tick(lua, 15); key(lua, "Q", False)
    assert S.ang == pytest.approx(a0, abs=0.01)
    S.x, S.y, S.ang = 5.5, 3.5, 0
    key(lua, "W"); tick(lua, 400); key(lua, "W", False)                                # five seconds of walking at the wall at x 7 (row 3)
    assert S.x < 7 - 0.2 and S.x > 6.5


def test_a_key_that_is_not_ours_goes_through_to_the_game_and_ours_do_not():
    lua, ns = boot()
    to_walk(lua, ns)
    f = frame(lua)
    key(lua, "W")
    assert f.propagate is False
    key(lua, "F5")
    assert f.propagate is True
    key(lua, "W", False)


def test_a_released_key_stops_its_movement():
    lua, ns = boot()
    S = to_walk(lua, ns)
    key(lua, "W"); tick(lua, 5); key(lua, "W", False)
    x = S.x
    tick(lua, 30)
    assert S.x == x


def test_escape_stops_everything_and_hides_the_window_and_keeps_the_walk_in_the_report():
    lua, ns = boot()
    ns.Gauntlet.run()
    for _ in range(3000):
        tick(lua, 1)
        if ns.Gauntlet.mode() == "walk":
            break
    S = ns.Gauntlet.state()
    ns.Gauntlet.fire()
    key(lua, "ESCAPE")
    assert not frame(lua).shown and ns.Gauntlet.mode() is None
    assert "walked and shot: 1 shots, 1 hits, 0 enemies down" in str(lua.eval("GauntletDB.report"))


def test_the_mouse_turns_you_by_how_far_the_cursor_is_from_the_middle_and_not_inside_the_dead_zone():
    lua, ns = boot()
    S = to_walk(lua, ns)
    a0 = S.ang
    lua.execute("CURSOR[1] = 500 + 20")                                                # the window's middle is x 500: 20 off, inside the dead zone (0.12 of 320)
    tick(lua, 30)
    assert S.ang == pytest.approx(a0)
    lua.execute("CURSOR[1] = 500 + 160")                                               # half way to the edge: 0.5 of the turn rate (3.0) for a second
    tick(lua, 75)
    assert S.ang == pytest.approx(a0 + 1.5, abs=0.05)
    a1 = S.ang
    lua.execute("CURSOR[1] = 500 - 300")                                               # most of the way to the left edge: 0.94 of the rate, the other way
    tick(lua, 75)
    assert S.ang == pytest.approx(a1 - 3.0 * 300 / 320, abs=0.05)
    a2 = S.ang
    lua.execute("CURSOR[1] = 500 - 900")                                               # the cursor is out of the window altogether: no turning at all
    tick(lua, 75)
    assert S.ang == pytest.approx(a2)


def test_mouse_turning_can_be_switched_off():
    lua, ns = boot()
    S = to_walk(lua, ns)
    lua.eval("SlashCmdList.GAUNTLET")("mouse off")
    a0 = S.ang
    lua.execute("CURSOR[1] = 700")
    tick(lua, 60)
    assert S.ang == a0 and any("mouse turning: off" in m for m in said(lua))
    lua.eval("SlashCmdList.GAUNTLET")("mouse on")
    tick(lua, 10)
    assert S.ang != a0


# ---------------------------------------------------------------- shooting
def test_a_shot_hits_the_enemy_in_front_three_hits_bring_it_down_and_it_stops_being_drawn():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    S.x, S.y, S.ang = 6.5, 4.5, 0                                                       # the wolf stands at 10.5, 4.5 straight ahead
    wolf = S.enemies[1]
    for i in range(3):
        assert ns.Gauntlet.fire() is True
        tick(lua, 30)                                                                  # past the 0.25 s gap
    assert wolf.hp == 0 and wolf.dead is True and S.shots == 3 and S.hits == 3 and S.kills == 1
    tick(lua, 1)
    assert not R.models[1].shown
    assert len(list(lua.eval("SOUNDS").values())) == 6                                  # a shot and an impact each time


def test_firing_is_limited_to_four_shots_a_second_and_a_miss_does_not_hit():
    lua, ns = boot()
    S = to_walk(lua, ns)
    S.x, S.y, S.ang = 6.5, 4.5, math.pi                                                # facing away from everything
    assert ns.Gauntlet.fire() is True
    assert ns.Gauntlet.fire() is False                                                  # the same instant: too soon
    tick(lua, 10)
    assert ns.Gauntlet.fire() is False                                                  # 0.13 s: still too soon
    tick(lua, 15)
    assert ns.Gauntlet.fire() is True
    assert S.shots == 2 and (S.hits or 0) == 0


def test_a_wall_stops_a_shot_and_the_click_and_the_space_bar_both_fire():
    lua, ns = boot()
    S = to_walk(lua, ns)
    z = S.enemies[6]
    S.x, S.y = 3.5, 4.5
    S.ang = math.atan2(z.y - S.y, z.x - S.x)                                            # aimed at the zombie through walls
    ns.Gauntlet.fire()
    assert (S.hits or 0) == 0
    tick(lua, 30)
    f = frame(lua)
    f.scripts.OnMouseDown(f, "LeftButton")
    assert S.shots == 2
    tick(lua, 30)
    key(lua, "SPACE"); tick(lua, 3); key(lua, "SPACE", False)
    assert S.shots == 3


def test_the_weapon_kicks_back_when_it_fires_and_the_flash_shows_only_for_a_moment():
    lua, ns = boot()
    S = to_walk(lua, ns)
    R = ns.Gauntlet.render()
    assert not R.flash.shown
    ns.Gauntlet.fire()
    tick(lua, 1)
    assert R.flash.shown
    y_kick = R.weapon.pts.y
    tick(lua, 30)
    assert not R.flash.shown and R.weapon.pts.y > y_kick - 0.01


# ---------------------------------------------------------------- the report command
def test_the_report_command_opens_a_box_with_the_report_and_says_so_when_there_is_none():
    lua, ns = boot()
    lua.eval("SlashCmdList.GAUNTLET")("report")
    assert any("no report yet" in m for m in said(lua))
    ns.Gauntlet.run()
    for _ in range(3000):
        tick(lua, 1)
        if ns.Gauntlet.mode() == "walk":
            break
    lua.eval("SlashCmdList.GAUNTLET")("report")
    edits = [o for o in lua.eval("ALL").values() if o.kind == "EditBox"]
    assert edits and "GAUNTLET REPORT" in str(edits[-1].text) and edits[-1].highlighted is True


def test_the_slash_command_with_anything_else_lists_the_commands():
    lua, ns = boot()
    lua.eval("SlashCmdList.GAUNTLET")("what")
    assert any("/gaunt test" in m for m in said(lua))
