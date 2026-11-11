"""Game.lua needs the WoW API. This drives it through a stand-in client: open the window, spend points, click, cast,
press keys, walk through the cave mouth, kill the boss, die, restart. It proves the wiring and that nothing errors;
it cannot show how anything LOOKS."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
FRAMES, ALL, PRINTED, CURSOR, PROPAGATE, TIMERS = {}, {}, {}, {0, 0}, {}, {}
SlashCmdList = {}
SHIFT = false
local function obj(parent)
  local o = { scripts = {}, shown = false, parent = parent }
  ALL[#ALL + 1] = o
  return setmetatable(o, { __index = function(t, k)
    -- Real frames answer methods (CamelCase) and have nothing for fields they do not own (lowercase).
    if not k:match("^%u") then return nil end
    if k == "GetLeft" or k == "GetBottom" then return function() return 0 end end
    if k == "GetFrameLevel" then return function() return 1 end end
    -- like WoW: a frame's effective scale is its own scale times its parent's
    if k == "GetEffectiveScale" then return function(self) return (self.scale or 1) * (self.parent and self.parent:GetEffectiveScale() or 1) end end
    if k == "GetWidth" or k == "GetHeight" then return function() return 100 end end
    if k == "SetScript" then return function(self, n, f) self.scripts[n] = f end end
    if k == "Show" then return function(self) self.shown = true end end
    if k == "Hide" then return function(self) self.shown = false end end
    if k == "SetShown" then return function(self, b) self.shown = b and true or false end end
    if k == "IsShown" then return function(self) return self.shown end end
    if k == "SetScale" then return function(self, v) self.scale = v end end
    if k == "RegisterForDrag" then return function(self, ...) self.drag = { ... } end end
    if k == "SetPropagateKeyboardInput" then return function(self, v) PROPAGATE[#PROPAGATE + 1] = v end end
    if k == "SetAnimation" then return function(self, id) self.last_anim = id end end
    if k == "SetFacing" then return function(self, r) self.facing = r end end
    if k == "SetUnit" then return function(self, u) self.unit = u end end
    if k == "SetModel" then return function(self, id) if NO_MODELS then error("no models here") end self.model = id end end
    if k == "SetCreature" then return function(self, id) if NO_MODELS then error("no models here") end self.creature = id end end
    if k == "SetTexture" then return function(self, id) self.texture = id end end
    if k == "SetVertexColor" then return function(self, r, g, b) self.color = { r, g, b } end end
    if k == "SetModelScale" then return function(self, v) self.modelscale = v end end
    if k == "SetRotation" then return function(self, v) self.rotation = v end end
    if k == "SetTexCoord" then return function(self, ...) self.coords = { ... } end end
    if k == "SetCamDistanceScale" then return function(self, v) self.camscale = v end end
    if k == "SetSize" then return function(self, w, h) self.size = { w, h } end end
    if k == "SetHeight" then return function(self, h) self.height = h end end
    if k == "SetWidth" then return function(self, w) self.width = w end end
    if k == "SetText" then return function(self, t) self.text = t end end
    if k == "ClearAllPoints" then return function(self) self.pts = nil end end
    if k == "SetPoint" then return function(self, point, rel, rp, x, y)
      if type(rel) == "number" or rel == nil then x, y, rel, rp = rel or 0, rp or 0, nil, point
      elseif x == nil then x, y = 0, 0 end
      self.pts = { point = point, rel = rel, rp = rp, x = x or 0, y = y or 0 } end end
    if k == "SetAlpha" then return function(self, v) self.alpha = v end end
    if k == "CreateTexture" or k == "CreateFontString" or k == "CreateMaskTexture" then return function(self) return obj(self) end end
    if k == "CreateLine" then return function() if NO_LINES then error("no lines here") end return obj() end end
    return function(self, ...) return self end
  end })
end
function CreateFrame(kind, name, parent, tmpl) local o = obj(parent); o.kind = kind; if name then FRAMES[name] = o end return o end
UIParent = obj()
TIPS = {}
GameTooltip = { SetOwner = function(self) TIPS = {} end, AddLine = function(self, t) TIPS[#TIPS + 1] = t end, Show = function() end, Hide = function() end }
C_Timer = { After = function(sec, fn) TIMERS[#TIMERS + 1] = fn end }
function run_timers() local t = TIMERS TIMERS = {} for _, f in ipairs(t) do f() end end
function GetCursorPosition() return CURSOR[1], CURSOR[2] end
function IsShiftKeyDown() return SHIFT end
function GetFramerate() return 60 end
function time() return 12345 end
function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end PRINTED[#PRINTED + 1] = table.concat(t, " ") end
function player_model() for _, o in ipairs(ALL) do if o.unit == "player" and o.kind == "PlayerModel" then return o end end end
'''


def boot(prelude="", with_slash=False):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(prelude + "\n" + MOCK)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Items", "Combat", "Zone", "Map", "Fx", "Gear", "Game") + (("Visuals", "Dread") if with_slash else ()):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


def slash(lua, text):
    lua.eval("SlashCmdList.DREAD")(text)


def said(lua):
    return [str(v) for v in lua.eval("PRINTED").values()]


def tick(lua, n, dt=1 / 30):
    f = lua.eval("FRAMES.DreadGameFrame")
    for _ in range(n):
        f.scripts.OnUpdate(f, dt)


def click_world(lua, ns, button, wx, wy):
    cam = ns.Game.camera()
    vw, vh = ns.Game.view()
    field = [o for o in lua.eval("ALL").values() if o.kind == "Frame" and o.size is not None and abs(o.size[1] - vw) < 0.01 and abs(o.size[2] - vh) < 0.01][0]
    sc = field.GetEffectiveScale(field)                                  # pixels per field unit
    lua.execute(f"CURSOR[1], CURSOR[2] = {(wx - cam.x) * sc}, {(wy - cam.y) * sc}")
    f = lua.eval("FRAMES.DreadGameFrame")
    f.scripts.OnMouseDown(f, button)


def key(lua, k):
    f = lua.eval("FRAMES.DreadGameFrame")
    f.scripts.OnKeyDown(f, k)


def learn(ns, lua, *ids, level=12):
    w = ns.Game.world()
    ns.Combat.set_level(w, level, 0)
    for i in ids:
        b = ns.Game.tree_buttons[i]
        b.scripts.OnClick(b)


def open_game(lua, ns, close_tree=True):
    ns.Game.toggle()
    tick(lua, 2)
    if close_tree and lua.eval("FRAMES.DreadTreeFrame.shown"):
        key(lua, "K")


def first_monster(w):
    return w.monsters[1]


def teleport_next_to(ns, lua, w, m, dx=-150, dy=0):
    w.player.x, w.player.y, w.player.tx, w.player.ty = m.x + dx, m.y + dy, None, None
    tick(lua, 1)


# ---------------------------------------------------------------- opening
def test_a_new_character_opens_on_the_tree_and_the_world_waits():
    lua, ns = boot()
    ns.Game.toggle()
    assert lua.eval("FRAMES.DreadTreeFrame.shown") is True
    assert ns.Game.area().name == "moor" and len(list(ns.Game.tree_buttons.keys())) == 30
    w = ns.Game.world()
    t = w.time
    tick(lua, 900)                                                    # thirty seconds of dithering over the tree
    assert w.time == t and w.over is False and w.player.life == w.player.maxlife


def test_the_moor_is_drawn_with_real_ground_and_scenery():
    lua, ns = boot()
    open_game(lua, ns)
    tick(lua, 3)
    allo = list(lua.eval("ALL").values())
    base = [o for o in allo if o.texture == 187126]
    over = [o for o in allo if o.texture == 187113]
    assert len(base) == 1 and len(over) == 1                          # grass, and the big dirt layer over it
    assert over[0].alpha == pytest.approx(0.22)                        # faded, so it only breaks up the tiling
    models = [o for o in allo if o.model is not None and o.kind == "PlayerModel" and o.camscale is not None]
    assert len(models) >= 4                                            # scenery frames got a model AND a camera distance
    assert all(isinstance(o.model, int) and o.model > 1000 for o in models)


def test_the_ground_scrolls_with_the_camera_and_the_two_layers_tile_differently():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    allo = list(lua.eval("ALL").values())
    base = [o for o in allo if o.texture == 187126][0]
    over = [o for o in allo if o.texture == 187113][0]
    w.player.x, w.player.y = 1200, 700
    tick(lua, 2)
    cam = ns.Game.camera()
    b, o = list(base.coords.values()), list(over.coords.values())
    vw, vh = ns.Game.view()
    assert b[0] == pytest.approx(cam.x / 512) and b[1] == pytest.approx((cam.x + vw) / 512)
    assert o[0] == pytest.approx(cam.x / 1100)                         # the dirt layer tiles at 1100 units, not 512


def test_tile_size_and_scenery_camera_can_be_tuned_live_and_are_saved():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    base = [o for o in lua.eval("ALL").values() if o.texture == 187126][0]
    w.player.x, w.player.y = 1200, 700
    assert ns.Game.set_tile(128) == 128
    tick(lua, 2)
    cam = ns.Game.camera()
    assert list(base.coords.values())[0] == pytest.approx(cam.x / 128)
    assert ns.Game.set_tile("rubbish") == "default" and ns.Game.set_tile(5) == "default"      # nonsense falls back, does not break
    tick(lua, 2)
    assert list(base.coords.values())[0] == pytest.approx(cam.x / 512)
    # scenery camera: default from the zone, then tuned, applied to frames already showing
    frames = [o for o in lua.eval("ALL").values() if o.camscale is not None]
    assert frames and ns.Game.cam_for("tree") == pytest.approx(2.2)
    assert ns.Game.set_cam("tree", 3) == 3
    assert any(o.camscale == 3 for o in frames)
    assert lua.eval("DreadDB.cam.tree") == 3 and ns.Game.cam_for("tree") == 3
    assert ns.Game.set_cam("spaceship", 2)[0] is None and ns.Game.set_cam("tree", 99)[0] is None


def test_scenery_frames_are_bigger_than_the_model_so_nothing_is_cut_off():
    lua, ns = boot()
    open_game(lua, ns)
    tick(lua, 3)
    spec = ns.Zone.SCENERY.tree
    assert spec.frame >= 1.5 and spec.cam > 1                          # the screenshot showed trees clipped at the frame edge
    shown = [o for o in lua.eval("ALL").values() if o.owner is not None and o.camscale is not None]
    assert shown
    for o in shown:                                                    # and the frames really are that much bigger than the model
        k = ns.Zone.SCENERY[o.owner.kind].frame
        assert o.size[1] == pytest.approx(o.owner.w * k) and o.size[2] == pytest.approx(o.owner.h * k)


# ---------------------------------------------------------------- the window and the mouse
def test_right_click_is_free_only_the_title_bar_drags():
    lua, ns = boot()
    ns.Game.toggle()
    dragging = [(o.drag, o.kind) for o in lua.eval("ALL").values() if o.drag is not None]
    flat = [b for d, _ in dragging for b in d.values()]
    assert "RightButton" not in flat                                  # the bug: right button used to move the window
    assert "LeftButton" in flat and len(dragging) == 1               # a single drag handle
    assert lua.eval("FRAMES.DreadGameFrame.drag") is None            # and the game window itself is not draggable


def test_walking_is_animated_and_faces_where_you_are_going():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    pm = lua.eval("player_model()")
    tick(lua, 2)
    assert pm.last_anim == 0                                          # standing
    click_world(lua, ns, "LeftButton", w.player.x + 300, w.player.y)
    tick(lua, 3)
    assert pm.last_anim == 5 and pm.facing == pytest.approx(0.0)     # running, facing east
    tick(lua, 90)
    assert pm.last_anim == 0                                          # arrived: standing again


# ---------------------------------------------------------------- fighting
def test_clicking_a_monster_attacks_with_the_free_wand():
    lua, ns = boot()
    open_game(lua, ns)                                                # no skill points spent at all
    w = ns.Game.world()
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -200, 0)
    mana = w.player.mana
    click_world(lua, ns, "LeftButton", m.x, m.y)
    tick(lua, 120)
    assert m.life < m.maxlife or m.dead is True                       # the wand hurt it
    assert w.player.mana >= mana                                      # and cost nothing
    assert m.awake is True                                            # and woke it (and its pack)


def test_a_far_monster_is_walked_up_to_before_the_wand_fires():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -310, 0)                          # on screen, but just outside wand range (300)
    click_world(lua, ns, "LeftButton", m.x, m.y)
    x0 = w.player.x
    tick(lua, 30)
    assert w.player.x > x0                                            # it walked toward the target first


def test_right_click_casts_the_selected_skill_and_costs_mana():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch")
    key(lua, "K")
    w = ns.Game.world()
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -200, 0)
    mana = w.player.mana
    pm = lua.eval("player_model()")
    click_world(lua, ns, "RightButton", m.x, m.y)
    tick(lua, 2)
    assert w.player.mana < mana + 0.5 and pm.last_anim == 51          # spent mana, cast animation


def test_shift_click_casts_without_walking():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch")
    key(lua, "K")
    w = ns.Game.world()
    lua.execute("SHIFT = true")
    mana = w.player.mana
    click_world(lua, ns, "LeftButton", w.player.x + 200, w.player.y)
    lua.execute("SHIFT = false")
    assert w.player.mana < mana and w.player.tx is None


# ---------------------------------------------------------------- the skill bar
def test_learning_fills_the_bar_and_the_number_keys_select():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch", "frostbolt")
    bar, sel = ns.Game.bar()
    assert bar[1] == "scorch" and bar[2] == "frostbolt" and sel == 1
    key(lua, "K")
    key(lua, "2")
    assert ns.Game.bar()[1] == 2
    key(lua, "1")
    assert ns.Game.bar()[1] == 1
    prop = list(lua.eval("PROPAGATE").values())
    assert prop[-1] is False                                           # handled keys are swallowed
    key(lua, "W")
    assert list(lua.eval("PROPAGATE").values())[-1] is True            # other keys still reach the game


def test_tab_and_the_wheel_rotate_through_the_bar_and_skip_empty_slots():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch", "frostbolt", "arcing_bolts")
    key(lua, "K")
    f = lua.eval("FRAMES.DreadGameFrame")
    assert ns.Game.bar()[1] == 1
    key(lua, "TAB");  assert ns.Game.bar()[1] == 2
    key(lua, "TAB");  assert ns.Game.bar()[1] == 3
    key(lua, "TAB");  assert ns.Game.bar()[1] == 1                      # wraps round
    f.scripts.OnMouseWheel(f, 1);   assert ns.Game.bar()[1] == 3        # wheel up (+1) goes back, wrapping
    f.scripts.OnMouseWheel(f, -1);  assert ns.Game.bar()[1] == 1        # wheel down (-1) goes forward


def test_hovering_a_skill_in_the_tree_and_pressing_a_number_puts_it_on_that_slot():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch", "frostbolt")                              # slots 1 and 2; the tree is open
    b = ns.Game.tree_buttons.frostbolt
    b.scripts.OnEnter(b)
    key(lua, "5")
    bar, sel = ns.Game.bar()
    assert bar[5] == "frostbolt" and bar[2] is None and sel == 5       # moved, not copied
    b.scripts.OnLeave(b)
    key(lua, "6")                                                       # nothing hovered: just selects (and slot 6 is empty)
    assert ns.Game.bar()[0][6] is None


def test_the_bar_is_saved_and_comes_back():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch", "frostbolt")
    b = ns.Game.tree_buttons.frostbolt
    b.scripts.OnEnter(b)
    key(lua, "4")
    saved = lua.eval("DreadDB")
    assert saved.bar[4] == "frostbolt" and saved.bar[1] == "scorch"


# ---------------------------------------------------------------- places
def test_walking_into_the_cave_mouth_changes_area_and_back_again():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    ex = ns.Game.area().exits[1]
    w.player.x, w.player.y = ex.x, ex.y
    tick(lua, 2)
    assert ns.Game.area().name == "cave" and w.area == "cave" and w.w == 1600
    assert any(m.boss for m in w.monsters.values())
    ground = [o for o in lua.eval("ALL").values() if o.texture == 188950]
    assert len(ground) == 1                                            # the cave floor texture
    back = ns.Game.area().exits[1]
    w.player.x, w.player.y = back.x, back.y
    tick(lua, 2)
    assert ns.Game.area().name == "moor"
    tick(lua, 30)
    assert ns.Game.area().name == "moor"                               # arriving did not bounce straight back in


def test_the_boss_quest_pays_one_skill_point_once():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    q0 = w.player.st.quest_points
    for _ in range(2):                                                  # the same news twice
        lua.eval("function(w) w.events[#w.events + 1] = { k = 'boss_dead', name = 'Grubb the Unwelcome' } end")(w)
        tick(lua, 1)
    assert w.player.st.quest_points == q0 + 1 and w.flags.den is True
    assert lua.eval("DreadDB.char.quest_points") == q0 + 1 and lua.eval("DreadDB.char.flags.den") is True


# ---------------------------------------------------------------- pause, death, restart
def test_opening_the_tree_mid_fight_pauses_it():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -100, 0)
    tick(lua, 10)
    key(lua, "K")                                                       # open the tree
    t = w.time
    tick(lua, 60)
    assert w.time == t
    key(lua, "K")
    tick(lua, 5)
    assert w.time > t


def test_dying_then_a_click_starts_again_and_keeps_the_character():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch")
    key(lua, "K")
    w = ns.Game.world()
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -60, 0)                             # right on top of a pack
    w.player.life = 0.5
    tick(lua, 600)
    assert ns.Game.world().over is True
    click_world(lua, ns, "LeftButton", 100, 100)
    w2 = ns.Game.world()
    assert w2.over is False and w2.player.st.points.scorch == 1 and w2.area == "moor"
    assert ns.Game.bar()[0][1] == "scorch"                              # and the bar


def test_window_scale_is_set_saved_and_kept_sane():
    lua, ns = boot()
    ns.Game.toggle()
    assert lua.eval("DreadDB.scale") == pytest.approx(1.6)
    assert lua.eval("FRAMES.DreadGameFrame.scale") == pytest.approx(1.6)
    assert ns.Game.set_scale(2.0) == 2.0
    assert lua.eval("FRAMES.DreadGameFrame.scale") == 2.0 and lua.eval("FRAMES.DreadTreeFrame.scale") == 2.0
    assert ns.Game.set_scale(50) == 3 and ns.Game.set_scale(0.1) == 0.8
    assert ns.Game.set_scale("nonsense") == pytest.approx(1.6)


def test_the_facing_nudge_is_applied_to_every_model():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    ns.Game.set_facing(1.5)
    click_world(lua, ns, "LeftButton", w.player.x + 300, w.player.y)
    tick(lua, 3)
    assert lua.eval("player_model()").facing == pytest.approx(1.5)      # east is 0, plus the nudge


def test_the_animation_tester_walks_through_the_ids():
    lua, ns = boot()
    ns.Game.animtest()
    lua.eval("run_timers")()
    lua.eval("run_timers")()                                          # the closing message is scheduled from inside the last step
    out = [str(v) for v in lua.eval("PRINTED").values()]
    assert sum("animation" in l for l in out) == 16 and any("Tell me which number" in l for l in out)


# ---------------------------------------------------------------- a client that refuses things
def test_a_client_without_models_or_lines_still_plays():
    lua, ns = boot("NO_LINES = true\nNO_MODELS = true")
    open_game(lua, ns)
    w = ns.Game.world()
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -150, 0)
    click_world(lua, ns, "LeftButton", m.x, m.y)
    tick(lua, 60)                                                       # nothing raised; the monster still got hit
    assert m.awake is True


# ---------------------------------------------------------------- two bugs found in review
def scenery_frames_showing(lua):
    return [o for o in lua.eval("ALL").values() if o.owner is not None and o.camscale is not None and o.shown]


def test_going_back_and_forth_does_not_use_up_the_scenery_frames():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    for trip in range(8):                                              # moor -> cave -> moor, over and over
        ex = ns.Game.area().exits[1]
        w.player.x, w.player.y = ex.x, ex.y
        tick(lua, 2)
        assert ns.Game.area().name == "cave"
        tick(lua, 2)
        back = ns.Game.area().exits[1]
        w.player.x, w.player.y = back.x, back.y
        tick(lua, 2)
        assert ns.Game.area().name == "moor"
        tick(lua, 2)
        assert len(scenery_frames_showing(lua)) >= 3, f"scenery vanished on trip {trip + 1}"
    # none of the frames is owned by a piece of scenery from an area we are no longer in
    here = {(d.x, d.y, d.id) for d in ns.Game.area().doodads.values()}
    assert all((o.owner.x, o.owner.y, o.owner.id) in here for o in scenery_frames_showing(lua))


def test_reset_starts_the_live_character_over_and_stays_reset():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch", "frostbolt")
    key(lua, "K")
    w = ns.Game.world()
    w.flags.den = True
    assert w.player.level == 12 and ns.Game.bar()[0][1] == "scorch"
    ns.Game.reset()                                                    # the window is open and the world is live
    w2 = ns.Game.world()
    assert w2.player.level == 1 and w2.player.xp == 0 and ns.Tree.points_spent(w2.player.st) == 0
    assert w2.flags.den is None and w2.player.st.quest_points == 0
    assert ns.Game.bar()[0][1] is None and ns.Game.area().name == "moor"
    ns.Game.toggle()                                                   # hide: this saves, and must save the NEW character
    saved = lua.eval("DreadDB.char")
    assert saved.level == 1 and saved.points.scorch is None
    ns.Game.toggle()                                                   # and showing it again keeps the new character
    assert ns.Game.world().player.level == 1


def test_reset_before_the_window_exists_just_clears_the_save():
    lua, ns = boot()
    lua.execute("DreadDB = { char = { level = 9, xp = 0, points = { scorch = 3 } }, bar = { 'scorch' } }")
    ns.Game.reset()
    assert lua.eval("DreadDB.char") is None and lua.eval("DreadDB.bar") is None
    ns.Game.toggle()
    assert ns.Game.world().player.level == 1


# ---------------------------------------------------------------- the bottom bar and the title bar
def extent(lua, o):
    """Left and right edge of a widget inside its parent, from its anchor and size; None if it cannot be worked out."""
    if o.pts is None or o.size is None or o.parent is None or o.parent.size is None:
        return None
    same = lua.eval("function(a, b) return a == b end")                  # Lua's own ==; Python wrappers are new on every access
    if o.pts.rel is not None and not same(o.pts.rel, o.parent):
        return None
    sc = o.scale or 1                                                    # a scaled frame draws its size and offsets that much bigger or smaller
    pw, w, x, pt = o.parent.size[1], o.size[1] * sc, o.pts.x * sc, o.pts.point
    if pt in ("TOPLEFT", "BOTTOMLEFT", "LEFT"):
        left = x
    elif pt in ("TOPRIGHT", "BOTTOMRIGHT", "RIGHT"):
        left = pw + x - w
    else:
        left = pw / 2 + x - w / 2
    return left, left + w, pw


def test_nothing_in_the_bottom_bar_or_title_bar_hangs_off_the_window():
    # The Skills button once sat past the right edge of the window. Every button and orb must lie inside its parent.
    lua, ns = boot()
    ns.Game.toggle()
    tick(lua, 2)
    checked = 0
    for o in lua.eval("ALL").values():
        if o.kind in ("Button", "Frame") and o.parent is not None and o.parent.size is not None:
            e = extent(lua, o)
            if e is None:
                continue
            left, right, pw = e
            assert left >= -0.5 and right <= pw + 0.5, f"a {o.kind} sticks out: {left:.0f}..{right:.0f} of {pw:.0f}"
            checked += 1
    assert checked >= 12                                               # 8 slots, 2 orbs, 2 buttons at least


def test_the_two_orbs_show_life_and_mana_as_fractions_and_numbers():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    life, mana = ns.Game.orbs()
    tick(lua, 2)
    assert life.frac == pytest.approx(1.0) and life.text.text == f"{w.player.maxlife}/{w.player.maxlife}"
    w.player.life = w.player.maxlife / 2
    w.player.mana = 0
    tick(lua, 1)
    assert life.frac == pytest.approx(0.5, abs=0.02) and mana.frac < 0.1
    assert life.text.text == f"{int(w.player.maxlife / 2)}/{w.player.maxlife}" and mana.text.text.endswith(f"/{w.player.maxmana}")
    assert life.fill.height == pytest.approx(84 * life.frac, abs=0.5)           # the fill really is that tall


def test_the_orbs_sit_at_opposite_ends_with_the_skill_bar_between_them():
    lua, ns = boot()
    ns.Game.toggle()
    life, mana = ns.Game.orbs()
    assert life.frame.pts.x < 5 and mana.frame.pts.x > 500
    slots_x = sorted(o.pts.x for o in lua.eval("ALL").values() if o.kind == "Button" and o.size is not None and o.size[1] == 40 and o.pts is not None)
    assert len(slots_x) == 8 and slots_x[0] > life.frame.pts.x + 96 - 1 and slots_x[-1] + 40 < mana.frame.pts.x + 1


# ---------------------------------------------------------------- the New game button
def find_button(lua, text):
    for o in lua.eval("ALL").values():
        if o.kind == "Button" and o.text == text:
            return o


def test_the_new_game_button_needs_two_clicks_and_then_really_resets():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch")
    key(lua, "K")
    btn = find_button(lua, "New game")
    assert btn is not None
    btn.scripts.OnClick(btn)                                           # first click only arms it
    assert btn.text == "Sure? Click" and ns.Game.world().player.level == 12
    btn.scripts.OnClick(btn)                                           # second click does it
    assert btn.text == "New game" and ns.Game.world().player.level == 1
    assert ns.Tree.points_spent(ns.Game.world().player.st) == 0


def test_an_armed_new_game_button_disarms_itself():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "scorch")
    btn = find_button(lua, "New game")
    btn.scripts.OnClick(btn)
    assert btn.text == "Sure? Click"
    lua.eval("run_timers")()                                           # three seconds pass
    assert btn.text == "New game"
    btn.scripts.OnClick(btn)                                           # so the next click is a first click again
    assert ns.Game.world().player.level == 12


def test_skills_and_new_game_live_in_the_title_bar():
    lua, ns = boot()
    ns.Game.toggle()
    for text in ("Skills (K)", "New game"):
        b = find_button(lua, text)
        assert b is not None and b.size[2] <= 22                       # fits inside the 24-high title bar
        assert b.parent.size[2] == 24


# ---------------------------------------------------------------- the blocking circles and scenery size
def test_the_solid_circles_match_the_obstacles_on_screen():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    w.player.x, w.player.y = 1200, 700
    tick(lua, 2)
    assert ns.Game.solid() is False and len(list(ns.Game.solid_sizes().values())) == 0     # nothing drawn by default
    ns.Game.set_solid(True)
    tick(lua, 2)
    cam = ns.Game.camera()
    vw, vh = ns.Game.view()
    on_screen = [o for o in w.obstacles.values() if -40 < o.x - cam.x < vw + 40 and -40 < o.y - cam.y < vh + 40]
    assert on_screen
    drawn = sorted(ns.Game.solid_sizes().values())
    assert drawn == sorted(o.r * 2 for o in on_screen)                  # one circle per obstacle in view, as wide as it blocks
    shown = [o for o in lua.eval("ALL").values() if o.shown and o.pts is not None and o.pts.point == "CENTER" and o.size is not None
             and o.size[1] == o.size[2] and o.size[1] in set(drawn)]
    assert len(shown) >= len(drawn)
    ns.Game.set_solid(False)
    tick(lua, 2)
    assert len(list(ns.Game.solid_sizes().values())) == 0


# ---------------------------------------------------------------- the typed commands (the path the player actually uses)
def test_slash_reset_really_resets_a_live_game():
    lua, ns = boot(with_slash=True)
    slash(lua, "play")
    learn(ns, lua, "scorch", "frostbolt")
    key(lua, "K")
    w = ns.Game.world()
    w.flags.den = True
    assert w.player.level == 12
    slash(lua, "reset")                                                 # typed, with the window open
    w2 = ns.Game.world()
    assert w2.player.level == 1 and ns.Tree.points_spent(w2.player.st) == 0 and w2.flags.den is None
    assert ns.Game.bar()[0][1] is None
    assert any("character reset" in l for l in said(lua))
    slash(lua, "play")                                                  # close: saves the NEW character
    assert lua.eval("DreadDB.char.level") == 1
    slash(lua, "play")
    assert ns.Game.world().player.level == 1                            # and it stays that way


def test_slash_reset_before_playing_and_after_a_reload_style_state():
    lua, ns = boot(with_slash=True)
    lua.execute("DreadDB = { char = { level = 9, xp = 0, points = { scorch = 3 } } }")
    slash(lua, "reset")
    assert lua.eval("DreadDB.char") is None
    slash(lua, "play")
    assert ns.Game.world().player.level == 1


def test_slash_commands_reach_the_game_settings():
    lua, ns = boot(with_slash=True)
    slash(lua, "play")
    slash(lua, "scale 2")
    assert lua.eval("DreadDB.scale") == 2 and lua.eval("FRAMES.DreadGameFrame.scale") == 2
    slash(lua, "tile 128");  assert lua.eval("DreadDB.tile") == 128
    slash(lua, "tile");      assert lua.eval("DreadDB.tile") is None
    slash(lua, "cam tree 3"); assert lua.eval("DreadDB.cam.tree") == 3
    slash(lua, "cam tree banana")
    assert lua.eval("DreadDB.cam.tree") == 3 and any("/dread cam" in l for l in said(lua))
    slash(lua, "facing 1.5"); assert lua.eval("DreadDB.facing") == 1.5
    assert ns.Game.solid() is False
    slash(lua, "solid");  assert ns.Game.solid() is True
    slash(lua, "solid");  assert ns.Game.solid() is False


def test_an_unknown_command_prints_the_list_and_includes_every_command():
    lua, ns = boot(with_slash=True)
    slash(lua, "banana")
    text = " ".join(said(lua))
    for word in ("play", "reset", "scale", "solid", "tile", "cam", "facing", "animtest", "skills", "visuals", "assets", "sound", "net", "version"):
        assert word in text, f"/dread {word} is missing from the help line"


def test_the_window_title_shows_which_build_this_is_and_does_not_collide_with_the_zone_name():
    lua, ns = boot()
    ns.BUILD = "11 Nov 21:00 UTC"
    ns.Game.toggle()
    titles = [o for o in lua.eval("ALL").values() if o.text is not None and str(o.text).startswith("Dread")]
    assert titles and "11 Nov 21:00 UTC" in titles[0].text and "drag here" not in titles[0].text     # short enough to leave room
    same = lua.eval("function(a, b) return a == b end")
    skills_btn = find_button(lua, "Skills (K)")
    zone = [o for o in lua.eval("ALL").values() if o.pts is not None and o.pts.point == "RIGHT" and o.pts.rel is not None and same(o.pts.rel, skills_btn)]
    assert len(zone) == 1                                                  # the zone name is pinned to the left edge of the Skills button


# ---------------------------------------------------------------- every skill through the real window
ACTIVE = ["scorch", "dragons_breath", "blazing_speed", "fireball", "flamestrike", "combustion", "meteor", "flame_spirit",
          "frostbolt", "ice_barrier", "frost_nova", "ice_lance", "frost_armor", "glacial_spike", "blizzard", "icicle_cloak", "frozen_orb",
          "arcing_bolts", "static_shock", "force_pull", "thunder_nova", "lightning_bolt", "chain_lightning", "blink", "storm_cloud", "mana_shield"]
BUFFS = ["blazing_speed", "combustion", "ice_barrier", "frost_armor", "icicle_cloak", "mana_shield"]


@pytest.mark.parametrize("sid", ACTIVE)
def test_every_active_skill_can_be_cast_from_the_window_and_drawn(sid):
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    ns.Combat.set_level(w, 30, 0)
    w.player.st.points[sid] = 1
    w.player.mana = w.player.maxmana = 500
    bar, sel = ns.Game.bar()
    for i in range(1, 9):
        bar[i] = None
    bar[1] = sid
    tick(lua, 2)
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -180, 0)
    click_world(lua, ns, "RightButton", m.x, m.y)
    mana_after = w.player.mana
    tick(lua, 90)                                                           # three seconds of drawing whatever it made
    assert ns.Combat.SHAPES[sid] is not None
    if sid in BUFFS:
        assert any(b.startswith(sid + ":") for b in ns.Game.buffs_shown().values()), f"{sid} shows no buff icon"
    click_world(lua, ns, "RightButton", m.x + 40, m.y)
    tick(lua, 60)


def test_zones_and_orbs_are_drawn_as_glowing_discs_in_the_right_place_and_size():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    w.player.st.points["flamestrike"] = 1
    w.player.mana = 500
    bar, sel = ns.Game.bar()
    bar[1] = "flamestrike"
    tick(lua, 2)
    click_world(lua, ns, "RightButton", w.player.x + 100, w.player.y)
    tick(lua, 3)
    cam = ns.Game.camera()
    zone = [e for e in w.effects.values() if e.kind == "zone"][0]
    discs = [o for o in lua.eval("ALL").values() if o.shown and o.size is not None and o.size[1] == o.size[2] == zone.r * 2
             and o.pts is not None and o.pts.point == "CENTER"]
    assert discs, "the zone is not drawn"
    d = discs[0]
    assert d.pts.x == pytest.approx(zone.x - cam.x) and d.pts.y == pytest.approx(zone.y - cam.y)


def test_beams_are_drawn_for_chain_lightning_and_fade():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    w.player.st.points["chain_lightning"] = 1
    w.player.mana = 500
    bar, sel = ns.Game.bar()
    bar[1] = "chain_lightning"
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -150, 0)
    click_world(lua, ns, "RightButton", m.x, m.y)
    seen = 0
    for _ in range(40):                                                     # a beam lasts 0.3 s, so look at every frame
        tick(lua, 1)
        seen = max(seen, len([o for o in lua.eval("ALL").values() if o.size is not None and o.size[1] == 16 and o.shown]))
    assert seen >= 8, "chain lightning drew no beam"                        # one beam is a row of 8 dots; the first pack has neighbours in jump range
    tick(lua, 60)
    assert not [o for o in lua.eval("ALL").values() if o.size is not None and o.size[1] == 16 and o.shown]    # and they fade away


def test_every_tooltip_says_what_the_skill_does_and_none_says_not_castable():
    lua, ns = boot()
    ns.Game.toggle()
    for i in range(1, 31):
        sid = str(ns.Skills[i].id)
        b = ns.Game.tree_buttons[sid]
        b.scripts.OnEnter(b)
        tips = " | ".join(str(t) for t in lua.eval("TIPS").values())
        assert "Not castable yet" not in tips, sid
        if sid in ACTIVE:
            assert str(ns.Game.DESC[sid]) in tips and "press 1-8" in tips, sid
        else:
            assert "Always on" in tips, sid
        b.scripts.OnLeave(b)


def test_every_active_skill_has_a_description():
    lua, ns = boot()
    for sid in ACTIVE:
        assert ns.Game.DESC[sid] is not None and len(str(ns.Game.DESC[sid])) > 10, sid


# ---------------------------------------------------------------- movement: particles, shield rings, spinning glows
def ready(lua, ns, sid):
    open_game(lua, ns)
    w = ns.Game.world()
    ns.Combat.set_level(w, 30, 0)
    w.player.st.points[sid] = 1
    w.player.mana = w.player.maxmana = 500
    bar, sel = ns.Game.bar()
    for i in range(1, 9):
        bar[i] = None
    bar[1] = sid
    tick(lua, 2)
    return w


def shown_dots(lua, size):
    return [o for o in lua.eval("ALL").values() if o.shown and o.size is not None and o.size[1] == size and o.size[2] == size
            and o.pts is not None and o.pts.point == "CENTER"]


def test_a_flying_bolt_is_drawn_with_a_trail_of_sparks():
    lua, ns = boot()
    w = ready(lua, ns, "scorch")
    assert ns.Game.particles_drawn() == 0                                    # nothing is going on
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -250, 0)
    click_world(lua, ns, "RightButton", w.player.x + 300, w.player.y)        # inside the view; the bolt keeps flying past the click
    tick(lua, 8)
    assert ns.Game.particles_drawn() >= 4                                    # sparks behind it


def test_a_shield_draws_a_ring_of_dots_around_you_and_it_turns():
    lua, ns = boot()
    w = ready(lua, ns, "ice_barrier")
    click_world(lua, ns, "RightButton", w.player.x + 50, w.player.y)
    tick(lua, 3)
    cam = ns.Game.camera()
    px, py = w.player.x - cam.x, w.player.y - cam.y + 20
    ring = shown_dots(lua, 8)                                                # the ice barrier's dots are exactly 8 wide
    assert len(ring) == 10
    assert all(((d.pts.x - px) ** 2 + ((d.pts.y - py) / 0.8) ** 2) ** 0.5 == pytest.approx(26, abs=0.5) for d in ring)
    before = sorted((round(d.pts.x), round(d.pts.y)) for d in ring)
    tick(lua, 15)
    after = sorted((round(d.pts.x), round(d.pts.y)) for d in shown_dots(lua, 8))
    assert before != after                                                   # the ring has moved on


def test_the_ring_goes_away_when_the_shield_does():
    lua, ns = boot()
    w = ready(lua, ns, "ice_barrier")
    click_world(lua, ns, "RightButton", w.player.x + 50, w.player.y)
    tick(lua, 3)
    assert len(shown_dots(lua, 8)) == 10
    w.player.buffs.ice_barrier = None
    tick(lua, 2)
    assert len(shown_dots(lua, 8)) == 0


def test_particle_detail_off_low_full_is_saved_and_obeyed():
    lua, ns = boot()
    w = ready(lua, ns, "combustion")
    click_world(lua, ns, "RightButton", w.player.x + 50, w.player.y)
    tick(lua, 30)
    full = ns.Game.particles_drawn()
    assert full > 10
    assert ns.Game.set_fx("off") == "off" and lua.eval("DreadDB.fx") == 0
    tick(lua, 30)
    assert ns.Game.particles_drawn() == 0                                    # even the shield rings are gone
    assert ns.Game.set_fx("low") == "low" and lua.eval("DreadDB.fx") == 0.5
    tick(lua, 60)
    low = ns.Game.particles_drawn()
    assert 0 < low < full
    assert ns.Game.set_fx("full") == "full"
    assert ns.Game.set_fx("banana") == "full" and lua.eval("DreadDB.fx") == 1      # nonsense changes nothing


def test_typed_fx_command_changes_the_detail_and_names_it():
    lua, ns = boot(with_slash=True)
    slash(lua, "play")
    slash(lua, "fx low")
    assert lua.eval("DreadDB.fx") == 0.5 and any("particle detail: low" in l for l in said(lua))
    slash(lua, "fx off");  assert lua.eval("DreadDB.fx") == 0
    slash(lua, "fx")                                                         # no word: just says what it is now
    assert any("particle detail: off" in l for l in said(lua))


def test_nothing_moves_while_the_tree_is_open():
    lua, ns = boot()
    w = ready(lua, ns, "combustion")
    click_world(lua, ns, "RightButton", w.player.x + 50, w.player.y)
    tick(lua, 20)
    key(lua, "K")                                                            # pause
    seen = sorted((round(d.pts.x), round(d.pts.y)) for d in shown_dots(lua, 9))
    tick(lua, 30)
    assert sorted((round(d.pts.x), round(d.pts.y)) for d in shown_dots(lua, 9)) == seen


def test_a_blast_makes_a_burst_and_it_dies_down():
    lua, ns = boot()
    w = ready(lua, ns, "fireball")
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -200, 0)
    click_world(lua, ns, "RightButton", m.x, m.y)
    peak = 0
    for _ in range(40):
        tick(lua, 1)
        peak = max(peak, ns.Game.particles_drawn())
    assert peak >= 30                                                        # the burst and ring when it lands
    tick(lua, 120)
    assert ns.Game.particles_drawn() <= 5                                    # and it has died down (a pack nearby may still glitter)


def test_projectile_glows_spin():
    lua, ns = boot()
    w = ready(lua, ns, "fireball")
    m = first_monster(w)
    teleport_next_to(ns, lua, w, m, -250, 0)
    click_world(lua, ns, "RightButton", w.player.x + 300, w.player.y)
    tick(lua, 3)
    spinning = [o for o in lua.eval("ALL").values() if o.rotation is not None]                 # (a texture inside a frame is shown with it)
    assert spinning
    r1 = {id(o): o.rotation for o in spinning}
    tick(lua, 3)
    assert any(o.rotation != r1.get(id(o)) for o in spinning)


def test_every_active_skill_can_still_be_cast_and_drawn_with_particles_on():
    # the whole list again, with detail at full: nothing in the particle code may raise for any skill
    for sid in ACTIVE:
        lua, ns = boot()
        w = ready(lua, ns, sid)
        m = first_monster(w)
        teleport_next_to(ns, lua, w, m, -180, 0)
        click_world(lua, ns, "RightButton", m.x, m.y)
        tick(lua, 60)


# ---------------------------------------------------------------- zoom: the field shows more of the world
def arena_frame(lua, ns):
    """The field: the frame exactly as wide and tall as the view."""
    vw, vh = ns.Game.view()
    for o in lua.eval("ALL").values():
        if o.kind == "Frame" and o.size is not None and abs(o.size[1] - vw) < 0.01 and abs(o.size[2] - vh) < 0.01:
            return o


def test_the_default_zoom_shows_more_world_in_the_same_space_on_screen():
    lua, ns = boot()
    ns.Game.toggle()
    vw, vh = ns.Game.view()
    assert (vw, vh) == (pytest.approx(640 * 1.4), pytest.approx(400 * 1.4))
    a = arena_frame(lua, ns)
    assert a.size[1] == pytest.approx(vw) and a.scale == pytest.approx(1 / 1.4)
    assert a.size[1] * a.scale == pytest.approx(640)                       # it still takes 640 units on screen
    assert a.pts.x == pytest.approx(10 * 1.4) and a.pts.y == pytest.approx(-(24 + 2) * 1.4)     # offsets are in the field's own units


def test_zoom_is_clamped_saved_and_applied_live():
    lua, ns = boot()
    ns.Game.toggle()
    assert ns.Game.set_zoom(2.0) == 2.0 and lua.eval("DreadDB.zoom") == 2.0
    assert ns.Game.view()[0] == pytest.approx(1280) and arena_frame(lua, ns).scale == pytest.approx(0.5)
    assert ns.Game.set_zoom(0.2) == 1 and ns.Game.set_zoom(40) == 2.6
    assert ns.Game.set_zoom("banana") == pytest.approx(1.4)                # nonsense falls back to the default
    ns.Game.set_zoom(1)
    assert ns.Game.view()[0] == 640 and arena_frame(lua, ns).scale == 1


def test_a_saved_zoom_is_used_when_the_window_is_built():
    lua, ns = boot("DreadDB = { zoom = 1.9 }")
    ns.Game.toggle()
    assert ns.Game.view()[0] == pytest.approx(640 * 1.9)


def test_the_camera_and_ground_follow_the_bigger_view_and_keep_you_in_the_middle():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    vw, vh = ns.Game.view()
    for (x, y) in ((10, 10), (2390, 1490), (1200, 750)):
        w.player.x, w.player.y = x, y
        tick(lua, 2)
        cam = ns.Game.camera()
        assert cam.x + vw / 2 == pytest.approx(w.player.x) and cam.y + vh / 2 == pytest.approx(w.player.y)     # dead centre, even in a corner
    base = [o for o in lua.eval("ALL").values() if o.texture == 187126][0]
    c = list(base.coords.values())
    assert c[1] - c[0] == pytest.approx(vw / 512)                          # the ground texture covers the whole bigger field


def test_a_click_anywhere_in_the_bigger_view_works_and_one_outside_it_does_not():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    w.player.x, w.player.y = 1200, 750
    tick(lua, 2)
    vw, vh = ns.Game.view()
    cam = ns.Game.camera()
    click_world(lua, ns, "LeftButton", cam.x + vw - 20, cam.y + 40)           # near the far edge of the bigger view
    assert w.player.tx == pytest.approx(cam.x + vw - 20)
    w.player.tx = None
    click_world(lua, ns, "LeftButton", cam.x + vw + 20, cam.y + 40)           # just outside
    assert w.player.tx is None


def test_the_typed_zoom_command_sets_it_and_says_so():
    lua, ns = boot(with_slash=True)
    slash(lua, "play")
    slash(lua, "zoom 1.8")
    assert lua.eval("DreadDB.zoom") == 1.8 and any("zoom 1.8" in l for l in said(lua))
    slash(lua, "zoom 99")
    assert lua.eval("DreadDB.zoom") == 2.6


# ---------------------------------------------------------------- the minimap
def teleport(ns, lua, w, x, y, ticks=8):
    w.player.x, w.player.y, w.player.tx, w.player.ty = x, y, None, None
    tick(lua, ticks)


def test_the_minimap_shows_what_you_have_seen_and_you_in_the_right_place():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    tick(lua, 8)
    mm = ns.Game.minimap()
    assert mm.shown is True and mm.cells > 15                              # the patch round the camp is revealed
    assert mm.monsters == 0 and mm.exits == 0                              # nothing near, and the cave mouth is far away
    me = [o for o in lua.eval("ALL").values() if o.shown and o.size is not None and o.size[1] == 5 and o.pts is not None and o.pts.point == "CENTER"]
    assert len(me) == 1                                                    # one yellow dot: you
    assert me[0].pts.x == pytest.approx(2 + w.player.x / 2400 * 168, abs=0.01) and me[0].pts.y == pytest.approx(2 + w.player.y / 1500 * 105, abs=0.01)


def test_walking_reveals_more_and_the_fog_stays_where_you_have_not_been():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    tick(lua, 8)
    first = ns.Game.minimap().cells
    teleport(ns, lua, w, 800, 500)
    second = ns.Game.minimap().cells
    assert second > first
    teleport(ns, lua, w, 800, 500)
    assert ns.Game.minimap().cells == second                               # standing still reveals nothing new
    assert ns.Game.minimap().cells < 200                                   # two patches of a 1000-cell map: most is still fog


def test_the_cave_mouth_appears_on_the_map_only_once_you_have_seen_it():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    tick(lua, 8)
    assert ns.Game.minimap().exits == 0
    teleport(ns, lua, w, 2100, 1200)                                       # within sight of the mouth at (2270, 1340)
    assert ns.Game.minimap().exits == 1
    teleport(ns, lua, w, 170, 150)                                         # and it stays known after you walk away
    assert ns.Game.minimap().exits == 1


def test_monsters_show_as_dots_only_when_close_and_alive():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    m = first_monster(w)
    teleport(ns, lua, w, m.x - 150, m.y)
    near = ns.Game.minimap().monsters
    assert near >= 1
    for mm_ in list(w.monsters.values())[:6]:
        mm_.dead = True
    teleport(ns, lua, w, m.x - 150, m.y)
    assert ns.Game.minimap().monsters < near


def test_m_and_the_typed_command_toggle_the_map_and_it_is_remembered():
    lua, ns = boot(with_slash=True)
    slash(lua, "play")
    tick(lua, 2)
    assert ns.Game.minimap().shown is True
    key(lua, "M")
    assert ns.Game.minimap().shown is False and lua.eval("DreadDB.map") is False
    slash(lua, "map")
    assert ns.Game.minimap().shown is True and any("minimap on" in l for l in said(lua))
    key(lua, "M")                                                          # off again, then a fresh session
    lua2, ns2 = boot("DreadDB = { map = false }")
    ns2.Game.toggle()
    assert ns2.Game.minimap().shown is False                               # off from last time stays off


def test_each_area_has_its_own_map():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    tick(lua, 8)
    moor_cells = ns.Game.minimap().cells
    ex = ns.Game.area().exits[1]
    teleport(ns, lua, w, ex.x, ex.y, ticks=3)
    assert ns.Game.area().name == "cave"
    tick(lua, 8)
    cave = ns.Game.minimap()
    assert 0 < cave.cells < moor_cells + 40                                # only the cave's own cells, not the moor's
    back = ns.Game.area().exits[1]
    teleport(ns, lua, w, back.x, back.y, ticks=3)
    assert ns.Game.area().name == "moor"
    tick(lua, 8)
    assert ns.Game.minimap().cells >= moor_cells                           # the moor remembers where you had been


# ---------------------------------------------------------------- auto attack keeps going
def count_wand_shots(ns, w, ticks_run, lua):
    """How many wand shots really left: wrap Combat.attack and count the calls that succeeded."""
    lua.execute("SHOTS = 0")
    lua.eval("function(c) local orig = c.attack; c.attack = function(...) local r = orig(...) if r == true then SHOTS = SHOTS + 1 end return r end end")(ns.Combat)
    tick(lua, ticks_run)
    return lua.eval("SHOTS")


def stand_off(env_lua, ns, count=3):
    """Put the player near the first pack with its members awake, tough enough to last, and return (world, monsters)."""
    lua = env_lua
    open_game(lua, ns)
    w = ns.Game.world()
    ms = [w.monsters[i] for i in range(1, count + 1)]
    for m in ms:
        m.life = m.maxlife = 400
        m.speed = 0
    w.player.x, w.player.y = ms[0].x - 150, ms[0].y
    tick(lua, 2)
    return w, ms


def test_clicking_a_monster_keeps_the_wand_going_until_it_is_dead():
    lua, ns = boot()
    w, ms = stand_off(lua, ns, 1)
    for m in list(w.monsters.values())[1:]:
        m.dead = True                                                      # pack-mates standing in front would take the bolts instead
    ms[0].life = 30
    click_world(lua, ns, "LeftButton", ms[0].x, ms[0].y)
    shots = count_wand_shots(ns, w, 300, lua)                              # ten seconds: 30 life at 3..6 a shot, one every 0.7 s
    assert ms[0].dead is True and shots >= 5                               # no more clicks needed


def test_when_the_target_dies_it_carries_on_with_the_nearest_monster_that_is_fighting():
    lua, ns = boot()
    w, ms = stand_off(lua, ns, 3)
    a, b, c = ms
    for m in ms:
        m.awake = True
    a.life, b.x, b.y, c.x, c.y = 20, a.x + 40, a.y, a.x + 200, a.y
    click_world(lua, ns, "LeftButton", a.x, a.y)
    for _ in range(150):
        tick(lua, 1)
        if a.dead:
            break
    assert a.dead is True
    tick(lua, 2)
    info = ns.Game.target_info()
    assert info is not None and info.name == b.name and round(info.x) == round(b.x)      # the nearer of the two left
    assert count_wand_shots(ns, w, 60, lua) >= 1                                        # and it is being shot


def test_it_does_not_go_after_sleeping_monsters_on_its_own():
    lua, ns = boot()
    w, ms = stand_off(lua, ns, 2)
    a, b = ms
    a.awake, b.awake = True, False
    b.aggro, b.pack = 1, 9999                                              # b really is asleep, and not in a's pack (which would wake with it)
    for m in list(w.monsters.values()):
        if m is not a and m is not b:
            m.dead = True                                                  # the rest of the pack is out of the picture
    b.x, b.y = a.x + 60, a.y
    a.life = 20
    click_world(lua, ns, "LeftButton", a.x, a.y)
    for _ in range(150):
        tick(lua, 1)
        if a.dead:
            break
    tick(lua, 3)
    assert ns.Game.target_info() is None and b.life == b.maxlife


def test_nothing_in_range_means_it_stops():
    lua, ns = boot()
    w, ms = stand_off(lua, ns, 1)
    for m in list(w.monsters.values())[1:]:
        m.dead = True                                                      # no one else is fighting
    ms[0].life = 20
    click_world(lua, ns, "LeftButton", ms[0].x, ms[0].y)
    for _ in range(150):
        tick(lua, 1)
        if ms[0].dead:
            break
    tick(lua, 3)
    assert ns.Game.target_info() is None


def test_casting_shift_casting_and_opening_the_tree_do_not_drop_the_target():
    lua, ns = boot()
    w, ms = stand_off(lua, ns, 1)
    ns.Combat.set_level(w, 30, 0)
    w.player.st.points["scorch"] = 1
    w.player.mana = w.player.maxmana = 500
    bar, sel = ns.Game.bar()
    bar[1] = "scorch"
    click_world(lua, ns, "LeftButton", ms[0].x, ms[0].y)
    assert ns.Game.target_info() is not None
    click_world(lua, ns, "RightButton", ms[0].x, ms[0].y)                 # a spell
    assert ns.Game.target_info() is not None
    lua.execute("SHIFT = true")
    click_world(lua, ns, "LeftButton", ms[0].x + 30, ms[0].y)              # a spell without moving
    lua.execute("SHIFT = false")
    assert ns.Game.target_info() is not None
    key(lua, "K"); tick(lua, 20); key(lua, "K")                            # tree open and shut
    assert ns.Game.target_info() is not None


def test_clicking_the_ground_or_dying_does_drop_the_target():
    lua, ns = boot()
    w, ms = stand_off(lua, ns, 1)
    click_world(lua, ns, "LeftButton", ms[0].x, ms[0].y)
    assert ns.Game.target_info() is not None
    click_world(lua, ns, "LeftButton", w.player.x - 60, w.player.y)       # walk away: you meant it
    assert ns.Game.target_info() is None
    click_world(lua, ns, "LeftButton", ms[0].x, ms[0].y)
    w.player.life = 0.1
    ms[0].awake = True
    ms[0].x, ms[0].y = w.player.x + 10, w.player.y
    tick(lua, 90)
    assert ns.Game.world().over is True
    click_world(lua, ns, "LeftButton", 100, 100)                           # start again
    assert ns.Game.target_info() is None


def test_a_ring_is_drawn_under_the_target_and_goes_when_there_is_none():
    lua, ns = boot()
    w, ms = stand_off(lua, ns, 1)
    ring = lambda: [o for o in lua.eval("ALL").values() if o.shown and o.size is not None and o.size[1] == o.size[2]
                    and o.pts is not None and o.pts.point == "CENTER" and o.alpha == 0.35 and abs(o.size[1] - (ms[0].radius + 12) * 2) < 4]
    assert ring() == []
    click_world(lua, ns, "LeftButton", ms[0].x, ms[0].y)
    tick(lua, 2)
    r = ring()
    assert len(r) == 1
    cam = ns.Game.camera()
    assert r[0].pts.x == pytest.approx(ms[0].x - cam.x, abs=1) and r[0].pts.y == pytest.approx(ms[0].y - cam.y - 4, abs=1)
    click_world(lua, ns, "LeftButton", w.player.x - 60, w.player.y)
    tick(lua, 2)
    assert ring() == []


# ---------------------------------------------------------------- the boss that changed size
def boss_frame(lua, ns):
    w = ns.Game.world()
    boss = [m for m in w.monsters.values() if m.boss][0]
    return boss, [o for o in lua.eval("ALL").values() if o.owner is not None and o.creature == boss.cid and o.size is not None and o.size[1] > 100][0]


def test_the_boss_is_made_big_by_its_frame_alone_and_never_scaled_twice():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    ex = ns.Game.area().exits[1]
    teleport(ns, lua, w, ex.x, ex.y, ticks=3)
    assert ns.Game.area().name == "cave"
    boss = [m for m in w.monsters.values() if m.boss][0]
    teleport(ns, lua, w, boss.x - 200, boss.y, ticks=6)
    b, f = boss_frame(lua, ns)
    assert f.size[1] == pytest.approx(64 * 1.8) and f.size[2] == pytest.approx(80 * 1.8)
    assert f.modelscale == 1                                                # not scaled a second time by the model


def test_the_bosss_size_does_not_change_while_it_fights():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    ex = ns.Game.area().exits[1]
    teleport(ns, lua, w, ex.x, ex.y, ticks=3)
    boss = [m for m in w.monsters.values() if m.boss][0]
    boss.awake = True
    boss.speed = 0
    teleport(ns, lua, w, boss.x - 20, boss.y, ticks=2)                      # right beside it: it bites, walks and stands in turn
    sizes = set()
    for _ in range(150):
        tick(lua, 1)
        b, f = boss_frame(lua, ns)
        sizes.add((round(f.size[1], 3), round(f.size[2], 3), f.modelscale))
    assert len(sizes) == 1                                                  # whatever it is doing, the frame and scale never move


def test_animation_switching_can_be_turned_off_and_back_on_and_is_saved():
    lua, ns = boot(with_slash=True)
    slash(lua, "play")
    tick(lua, 2)
    w = ns.Game.world()
    pm = lua.eval("player_model()")
    click_world(lua, ns, "LeftButton", w.player.x + 200, w.player.y)
    tick(lua, 3)
    assert pm.last_anim == 5                                                # running
    slash(lua, "anim off")
    assert lua.eval("DreadDB.anim") is False and any("model animations: off" in l for l in said(lua))
    click_world(lua, ns, "LeftButton", w.player.x + 100, w.player.y)
    tick(lua, 5)
    assert pm.last_anim == 0                                                # everything just stands
    slash(lua, "anim on")
    tick(lua, 5)
    assert pm.last_anim == 5 and lua.eval("DreadDB.anim") is True


def test_a_third_ground_layer_tiles_hugely_so_the_floor_has_patches_not_one_repeating_look():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    patch = [o for o in lua.eval("ALL").values() if o.texture == 187070][0]
    w.player.x, w.player.y = 1200, 700
    tick(lua, 2)
    cam = ns.Game.camera()
    assert list(patch.coords.values())[0] == pytest.approx(cam.x / 1700)
    assert patch.alpha == pytest.approx(0.3)


# ---------------------------------------------------------------- gear on screen
def put_item_at_player(lua, ns, w, rarity="rare", **stats):
    it = lua.table_from({"slot": "ring", "rarity": rarity, "ilvl": 5, "base": "Ring", "stats": lua.table_from(stats or {"life": 12})})
    w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x + 300, "y": w.player.y, "t": 30})


def drop_icons(lua):
    return [o for o in lua.eval("ALL").values() if o.texture == "Interface\\Icons\\INV_Misc_Bag_08"]


def test_a_dropped_item_is_drawn_as_a_bag_in_its_rarity_colour_and_a_potion_is_not(env=None):
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    put_item_at_player(lua, ns, w, "rare")
    tick(lua, 2)
    bag = drop_icons(lua)
    assert len(bag) == 1 and bag[0].shown and tuple(round(c, 2) for c in bag[0].color.values()) == (1, 0.85, 0.3)
    put_item_at_player(lua, ns, w, "magic")
    tick(lua, 2)
    assert tuple(round(c, 2) for c in drop_icons(lua)[0].color.values()) == (0.5, 0.65, 1)
    w.drops[1] = lua.table_from({"kind": "life", "x": w.player.x + 300, "y": w.player.y, "t": 30})
    tick(lua, 2)
    assert bag[0].texture == "Interface\\Icons\\INV_Potion_54"             # the same frame goes back to being a potion


def test_walking_onto_an_item_wears_it_tells_you_and_the_gear_window_lists_it():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    it = lua.table_from({"slot": "ring", "rarity": "rare", "ilvl": 5, "base": "Ring", "stats": lua.table_from({"life": 12})})
    w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x, "y": w.player.y, "t": 30})
    tick(lua, 2)
    assert w.player.gear.ring1.stats.life == 12 and w.player.maxlife == 72
    assert any("Rare item found!" in str(o.text) for o in lua.eval("ALL").values() if o.text)          # a short line on screen
    assert any("Rare Ring of Life" in l and "+12 Life" in l for l in said(lua))                         # the detail is in the log
    assert not lua.eval("FRAMES.DreadGearFrame") or not lua.eval("FRAMES.DreadGearFrame").shown          # and no window opened by itself
    key(lua, "I")
    frame = lua.eval("FRAMES.DreadGearFrame")
    assert frame.shown
    allt = [str(o.text) for o in lua.eval("ALL").values() if o.text]
    assert any("Ring: " in t and "Rare Ring of Life" in t for t in allt)                    # in its place on the doll
    assert any(t.startswith("Total:") and "+12 Life" in t for t in allt)
    key(lua, "I")
    assert not frame.shown


def test_the_doll_labels_name_every_place_and_the_totals_add_up():
    lua, ns = boot()
    gear = lua.table_from({"ring2": lua.table_from({"slot": "ring", "rarity": "magic", "ilvl": 3, "base": "Band", "stats": lua.table_from({"life": 9, "dmg_pct": 4})})})
    labels = {p: ns.Gear.slot_label(p, gear) for p in ("head", "amulet", "weapon", "body", "gloves", "belt", "boots", "ring1", "ring2")}
    assert "Magic Band of Life, Spell damage" in labels["ring2"] and labels["ring2"].startswith("Ring: ")
    assert "Helm" in labels["head"] and "Armor" in labels["body"] and "Gloves" in labels["gloves"] and "Boots" in labels["boots"]
    assert all("|cff888888" in labels[p] for p in labels if p != "ring2")             # empty places are dim
    t = ns.Gear.text(gear)
    assert "Total:  +9 Life,  +4% Spell damage" in t and "You:" not in t                # the summary line needs the player
    assert "nothing yet" in ns.Gear.text(lua.table())


def test_every_place_has_a_spot_on_the_doll_and_no_two_share_one():
    lua, ns = boot()
    spots = [(int(ns.Gear.LAYOUT[p][1]), int(ns.Gear.LAYOUT[p][2])) for p in ns.Items.GEAR_SLOTS.values()]
    assert len(spots) == 9 and len(set(spots)) == 9
    assert ns.Gear.LAYOUT.head[2] == 0 and ns.Gear.LAYOUT.weapon[2] == 1 and ns.Gear.LAYOUT.ring1[2] == 3     # helm on top, rings at the bottom


def gear_rows(lua):
    """The bag rows: (Wear button, x button, label) in order, as the window made them."""
    allo = list(lua.eval("ALL").values())
    wear = [o for o in allo if o.kind == "Button" and o.text == "Wear"]
    trash = [o for o in allo if o.kind == "Button" and o.text == "x"]
    return wear, trash


def bag_labels(lua):
    return [str(o.text) for o in lua.eval("ALL").values() if o.text and ("Magic " in str(o.text) or "Rare " in str(o.text)) and "Weapon:" not in str(o.text) and "Found" not in str(o.text)]


def test_the_bag_lists_what_you_did_not_wear_with_what_wearing_it_would_change_and_wear_swaps_it():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    for it in ({"slot": "head", "stats": {"str": 10}}, {"slot": "head", "stats": {"int": 10}}):
        it = lua.table_from({"slot": it["slot"], "rarity": "magic", "ilvl": 5, "base": "Hood", "stats": lua.table_from(it["stats"])})
        w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x, "y": w.player.y, "t": 30})
        tick(lua, 2)
    assert w.player.gear.head.stats.str == 10 and len(list(w.player.bag.values())) == 1     # the first was worn, the second waits
    key(lua, "I")
    labels = bag_labels(lua)
    assert any("Intelligence" in l and "+20 mana" in l and "+5% spell" in l and "-10% wand" in l for l in labels)
    wear, trash = gear_rows(lua)
    shown = [b for b in wear if b.shown]
    assert len(shown) == 1
    shown[0].scripts.OnClick(shown[0])
    assert w.player.gear.head.stats.int == 10 and w.player.bag[1].stats.str == 10        # swapped by your choice
    assert w.player.maxmana == 33 + 20
    assert lua.eval("DreadDB.char.gear.head.stats.int") == 10                              # and saved


def test_the_x_button_throws_a_bag_item_away():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    for stats in ({"str": 3}, {"vit": 3}):
        it = lua.table_from({"slot": "head", "rarity": "magic", "ilvl": 5, "base": "Hood", "stats": lua.table_from(stats)})
        w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x, "y": w.player.y, "t": 30})
        tick(lua, 2)
    key(lua, "I")
    wear, trash = gear_rows(lua)
    [b for b in trash if b.shown][0].scripts.OnClick([b for b in trash if b.shown][0])
    assert len(list(w.player.bag.values())) == 0 and w.player.gear.head.stats.str == 3


def test_a_full_bag_tells_you_to_make_room():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    w.player.gear.head = lua.table_from({"slot": "head", "rarity": "magic", "ilvl": 5, "base": "Hood", "stats": lua.table_from({"life": 1})})
    for i in range(16):
        w.player.bag[i + 1] = lua.table_from({"slot": "head", "rarity": "magic", "ilvl": 5, "base": "Hood", "stats": lua.table_from({"life": i + 2})})
    it = lua.table_from({"slot": "head", "rarity": "magic", "ilvl": 5, "base": "Hood", "stats": lua.table_from({"int": 3})})
    w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x, "y": w.player.y, "t": 30})
    tick(lua, 3)
    assert any("Bag full" in str(o.text) for o in lua.eval("ALL").values() if o.text)
    assert len(list(w.drops.values())) == 1


def test_an_open_gear_window_updates_when_you_pick_up_something_better():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    key(lua, "I")
    def gear_text():
        return [str(o.text) for o in lua.eval("ALL").values() if o.text and str(o.text).startswith("Total:")][0]
    assert "nothing yet" in gear_text()
    it = lua.table_from({"slot": "head", "rarity": "magic", "ilvl": 4, "base": "Hood", "stats": lua.table_from({"mana": 7})})
    w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x, "y": w.player.y, "t": 30})
    tick(lua, 2)
    assert "+7 Mana" in gear_text()


# ---------------------------------------------------------------- quiet for ordinary finds, loud for the good ones
def pick_up(lua, ns, rarity, slot="head", **stats):
    w = ns.Game.world()
    it = lua.table_from({"slot": slot, "rarity": rarity, "ilvl": 5, "base": {"head": "Hood", "ring": "Ring", "body": "Robe"}[slot],
                         "title": "Seal of Cinders" if rarity == "unique" else None, "stats": lua.table_from(stats or {"life": 4})})
    if rarity == "unique":
        it.slot, it.base = "ring", "Ring"
    w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x, "y": w.player.y, "t": 30})
    tick(lua, 2)


def toast(lua):
    return [str(o.text) for o in lua.eval("ALL").values() if o.text and ("item" in str(o.text).lower() and "found" in str(o.text).lower())]


def test_a_common_or_magic_find_is_one_quiet_line_and_never_opens_a_window():
    lua, ns = boot("SOUNDS = {}\nfunction PlaySound(id) SOUNDS[#SOUNDS + 1] = id end")
    open_game(lua, ns)
    pick_up(lua, ns, "common")
    assert toast(lua) == ["Found an item"]
    pick_up(lua, ns, "magic", slot="body")
    assert toast(lua) == ["Found an item"]
    gf = lua.eval("FRAMES.DreadGearFrame")
    assert gf is None or not gf.shown
    assert len(list(lua.eval("SOUNDS").values())) == 0                                       # no chime for ordinary finds
    assert any("Plain Hood" in l for l in said(lua)) and any("Magic Robe" in l for l in said(lua))


def test_a_rare_is_announced_louder_and_a_unique_loudest_with_a_chime():
    lua, ns = boot("SOUNDS = {}\nfunction PlaySound(id) SOUNDS[#SOUNDS + 1] = id end")
    open_game(lua, ns)
    pick_up(lua, ns, "rare")
    assert toast(lua) == ["Rare item found!"] and len(list(lua.eval("SOUNDS").values())) == 1
    pick_up(lua, ns, "unique", life=9)
    assert toast(lua) == ["UNIQUE ITEM FOUND!  Seal of Cinders"] and len(list(lua.eval("SOUNDS").values())) == 2
    assert any("Seal of Cinders" in l and "unique" in l for l in said(lua))


def test_the_bag_filters_only_change_what_is_listed():
    lua, ns = boot()
    G = ns.Gear
    bag = lua.table_from([
        lua.table_from({"slot": "ring", "rarity": "common", "ilvl": 1, "base": "Ring", "stats": lua.table_from({"life": 1})}),
        lua.table_from({"slot": "head", "rarity": "rare", "ilvl": 1, "base": "Hood", "stats": lua.table_from({"life": 1})}),
        lua.table_from({"slot": "ring", "rarity": "unique", "ilvl": 1, "base": "Ring", "stats": lua.table_from({"life": 1})}),
        lua.table_from({"slot": "ring", "rarity": "magic", "ilvl": 1, "base": "Ring", "stats": lua.table_from({"life": 1})}),
    ])
    G.slot_filter, G.min_rank = 0, 1
    assert list(G.visible(bag).values()) == [1, 2, 3, 4]
    G.cycle_rank(); G.cycle_rank()                                              # common -> magic -> rare and better
    assert G.min_rank == 3 and list(G.visible(bag).values()) == [2, 3]
    G.min_rank = 1
    for _ in range(4): G.cycle_slot()                                           # all, weapon, head, body, ring
    assert G.slot_filter == 4 and list(G.visible(bag).values()) == [1, 3, 4]
    for _ in range(5): G.cycle_slot()                                           # amulet, gloves, belt, boots, then round again
    assert G.slot_filter == 0                                                     # wraps back to every type
    G.cycle_rank(); G.cycle_rank(); G.cycle_rank(); G.cycle_rank()
    assert G.min_rank == 1                                                       # and so does the quality filter


def test_wearing_from_a_filtered_bag_picks_the_item_you_see_not_the_row_number():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    ns.Gear.slot_filter, ns.Gear.min_rank = 0, 1
    for slot, stats in (("head", {"str": 3}), ("head", {"vit": 3}), ("body", {"str": 1}), ("body", {"int": 5})):
        it = lua.table_from({"slot": slot, "rarity": "magic", "ilvl": 5, "base": {"head": "Hood", "body": "Robe"}[slot], "stats": lua.table_from(stats)})
        w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x, "y": w.player.y, "t": 30})
        tick(lua, 2)
    assert len(list(w.player.bag.values())) == 2          # head vit and body int wait; head str and body str are worn
    key(lua, "I")
    ns.Gear.cycle_slot(); ns.Gear.cycle_slot(); ns.Gear.cycle_slot()      # armor only (weapon, helm, armor)
    ns.Gear.refresh(w)
    wear, _ = gear_rows(lua)
    shown = [b for b in wear if b.shown]
    assert len(shown) == 1
    shown[0].scripts.OnClick(shown[0])                     # it is the first VISIBLE row, which is bag place 2
    assert w.player.gear.body.stats.int == 5 and w.player.bag[1].slot == "head"
    ns.Gear.slot_filter, ns.Gear.min_rank = 0, 1


# ---------------------------------------------------------------- skills that need no aim cast from their key
NO_AIM = ["static_shock", "force_pull", "frost_nova", "thunder_nova", "combustion", "ice_barrier", "frost_armor", "icicle_cloak",
          "mana_shield", "blazing_speed", "storm_cloud"]
AIMED = ["scorch", "fireball", "frostbolt", "ice_lance", "glacial_spike", "blizzard", "flamestrike", "meteor", "frozen_orb",
         "lightning_bolt", "chain_lightning", "arcing_bolts", "dragons_breath", "blink", "flame_spirit"]


def test_the_split_between_aimed_and_no_aim_skills_is_exactly_this():
    lua, ns = boot()
    assert [s for s in ACTIVE if ns.Combat.self_cast(s)] == [s for s in ACTIVE if s in NO_AIM]
    assert sorted(AIMED + NO_AIM) == sorted(ACTIVE)                      # every skill is in exactly one list
    assert ns.Combat.self_cast("wand") is False and ns.Combat.self_cast("nonsense") is False


def slot_one(lua, ns, sid):
    w = ns.Game.world()
    ns.Combat.set_level(w, 30, 0)
    w.player.st.points[sid] = 1
    w.player.mana = w.player.maxmana = 500
    bar, _ = ns.Game.bar()
    for i in range(1, 9):
        bar[i] = None
    bar[1] = sid
    tick(lua, 2)
    return w


@pytest.mark.parametrize("sid", NO_AIM)
def test_pressing_the_key_of_a_no_aim_skill_casts_it_without_a_click(sid):
    lua, ns = boot()
    open_game(lua, ns)
    w = slot_one(lua, ns, sid)
    mana = w.player.mana
    key(lua, "1")
    assert w.player.mana < mana, f"{sid} did not cast from its key"


@pytest.mark.parametrize("sid", AIMED)
def test_pressing_the_key_of_an_aimed_skill_only_selects_it(sid):
    lua, ns = boot()
    open_game(lua, ns)
    w = slot_one(lua, ns, sid)
    mana = w.player.mana
    key(lua, "1")
    assert w.player.mana == mana and ns.Game.bar()[1] == 1


def test_static_shock_from_the_key_hurts_what_is_close_and_not_what_is_far():
    lua, ns = boot()
    open_game(lua, ns)
    w = slot_one(lua, ns, "static_shock")
    near, far = w.monsters[1], w.monsters[2]
    near.x, near.y, far.x, far.y = w.player.x + 60, w.player.y, w.player.x + 400, w.player.y
    near.life = far.life = 100
    key(lua, "1")
    assert near.life < 100 and far.life == 100


def test_a_failed_key_cast_says_why_and_does_not_stop_the_game():
    lua, ns = boot()
    open_game(lua, ns)
    w = slot_one(lua, ns, "static_shock")
    w.player.mana = 0
    key(lua, "1")
    assert any("Static Shock" in str(o.text) for o in lua.eval("ALL").values() if o.text)
    assert w.player.mana == 0


def test_assigning_from_the_tree_does_not_also_cast_it():
    lua, ns = boot()
    ns.Game.toggle()
    learn(ns, lua, "frostbolt", "frost_nova", level=30)          # frost nova needs no aim
    w = ns.Game.world()
    w.player.mana = w.player.maxmana
    mana = w.player.mana
    b = ns.Game.tree_buttons["frost_nova"]
    b.scripts.OnEnter(b)
    key(lua, "5")
    bar, _ = ns.Game.bar()
    assert bar[5] == "frost_nova" and w.player.mana == mana


def doll_button(lua, label_start):
    return [o for o in lua.eval("ALL").values() if o.kind == "Button" and o.text and str(o.text).startswith(label_start)][0]


def wear(lua, ns, w, slot, base, **stats):
    it = lua.table_from({"slot": slot, "rarity": "magic", "ilvl": 5, "base": base, "stats": lua.table_from(stats)})
    w.drops[1] = lua.table_from({"kind": "item", "item": it, "x": w.player.x, "y": w.player.y, "t": 30})
    tick(lua, 2)


def test_the_doll_shows_both_rings_and_clicking_a_worn_place_takes_it_off():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    wear(lua, ns, w, "ring", "Ring", life=3)
    wear(lua, ns, w, "ring", "Band", vit=4)
    wear(lua, ns, w, "head", "Hood", int=5)
    key(lua, "I")
    rings = [o for o in lua.eval("ALL").values() if o.kind == "Button" and o.text and str(o.text).startswith("Ring: ")]
    assert len(rings) == 2                                                           # two ring places, both filled
    helm = doll_button(lua, "Helm: ")
    assert "Hood" in str(helm.text) and w.player.maxmana == 33 + 10
    helm.scripts.OnClick(helm)
    assert w.player.gear.head is None and w.player.bag[1].stats.int == 5 and w.player.maxmana == 33
    assert str(doll_button(lua, "|cff888888Helm").text).startswith("|cff888888")      # and the place shows empty
    assert lua.eval("DreadDB.char.gear.head") is None                                  # saved that way


def test_hovering_a_worn_place_lists_everything_on_the_item():
    lua, ns = boot()
    open_game(lua, ns)
    w = ns.Game.world()
    wear(lua, ns, w, "body", "Robe", vit=6, mana=4)
    key(lua, "I")
    b = doll_button(lua, "Armor: ")
    b.scripts.OnEnter(b)
    t = [str(o.text) for o in lua.eval("ALL").values() if o.text and "(magic, level 5)" in str(o.text)]
    assert t and "+6 Vitality" in t[0] and "+4 Mana" in t[0]
    b.scripts.OnLeave(b)
    assert not [o for o in lua.eval("ALL").values() if o.text and "(magic, level 5)" in str(o.text)]


# ---------------------------------------------------------------- the log goes with the game
def test_playing_opens_the_log_beside_the_window_and_closing_the_game_closes_it():
    lua, ns = boot()
    lua.execute("LOGCALLS = {}")
    ns.Log = lua.eval("{ open_beside = function(a) LOGCALLS[#LOGCALLS + 1] = 'open' LOGANCHOR = a end, close = function() LOGCALLS[#LOGCALLS + 1] = 'close' end }")
    ns.Game.toggle()                                                       # play
    assert list(lua.eval("LOGCALLS").values()) == ["open"]
    assert lua.eval("rawequal")(lua.eval("LOGANCHOR"), lua.eval("FRAMES.DreadGameFrame"))      # beside the game window itself
    ns.Game.toggle()                                                       # close
    assert list(lua.eval("LOGCALLS").values()) == ["open", "close"]
    ns.Game.toggle()
    assert list(lua.eval("LOGCALLS").values()) == ["open", "close", "open"]
