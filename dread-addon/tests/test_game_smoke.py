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
    if k == "GetEffectiveScale" or k == "GetFrameLevel" then return function() return 1 end end
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
    for f in ("Sim", "Skills", "Tree", "Combat", "Zone", "Fx", "Game") + (("Visuals", "Dread") if with_slash else ()):
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
    lua.execute(f"CURSOR[1], CURSOR[2] = {wx - cam.x}, {wy - cam.y}")
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
    assert over[0].alpha == pytest.approx(0.3)                         # faded, so it only breaks up the tiling
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
    assert b[0] == pytest.approx(cam.x / 256) and b[1] == pytest.approx((cam.x + 640) / 256)
    assert o[0] == pytest.approx(cam.x / 640)                          # the dirt layer tiles at 640 units, not 256


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
    assert list(base.coords.values())[0] == pytest.approx(cam.x / 256)
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
    pw, w, x, pt = o.parent.size[1], o.size[1], o.pts.x, o.pts.point
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
    on_screen = [o for o in w.obstacles.values() if -40 < o.x - cam.x < 680 and -40 < o.y - cam.y < 440]
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
