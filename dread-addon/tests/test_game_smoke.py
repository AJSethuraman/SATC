"""Game.lua needs the WoW API. This drives it through a stand-in client: open the window, spend points, click, cast,
press keys, walk through the cave mouth, kill the boss, die, restart. It proves the wiring and that nothing errors;
it cannot show how anything LOOKS."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
FRAMES, ALL, PRINTED, CURSOR, PROPAGATE, TIMERS = {}, {}, {}, {0, 0}, {}, {}
SHIFT = false
local function obj()
  local o = { scripts = {}, shown = false }
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
    if k == "SetTexCoord" then return function(self, ...) self.coords = { ... } end end
    if k == "SetCamDistanceScale" then return function(self, v) self.camscale = v end end
    if k == "SetSize" then return function(self, w, h) self.size = { w, h } end end
    if k == "SetAlpha" then return function(self, v) self.alpha = v end end
    if k == "CreateTexture" or k == "CreateFontString" then return function() return obj() end end
    if k == "CreateLine" then return function() if NO_LINES then error("no lines here") end return obj() end end
    return function(self, ...) return self end
  end })
end
function CreateFrame(kind, name, parent, tmpl) local o = obj(); o.kind = kind; if name then FRAMES[name] = o end return o end
UIParent, GameTooltip = obj(), obj()
C_Timer = { After = function(sec, fn) TIMERS[#TIMERS + 1] = fn end }
function run_timers() local t = TIMERS TIMERS = {} for _, f in ipairs(t) do f() end end
function GetCursorPosition() return CURSOR[1], CURSOR[2] end
function IsShiftKeyDown() return SHIFT end
function GetFramerate() return 60 end
function time() return 12345 end
function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end PRINTED[#PRINTED + 1] = table.concat(t, " ") end
function player_model() for _, o in ipairs(ALL) do if o.unit == "player" and o.kind == "PlayerModel" then return o end end end
'''


def boot(prelude=""):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(prelude + "\n" + MOCK)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("Sim", "Skills", "Tree", "Combat", "Zone", "Game"):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


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
