-- The playable window: draws the world from Combat.lua / Zone.lua with WoW's own art and takes the mouse and keys.
--   Left click   walk; click a monster to attack it with your wand (free, no mana)
--   Right click  cast the selected skill at the cursor      Shift + left click  cast without moving
--   1-8          select a skill slot                         Tab / mouse wheel   rotate to the next slot
--   I            gear (what you have found and wear)
--   K            skill tree: hover a skill and press 1-8 to put it on that slot
-- Drag the window by its title bar. The rules all live in Combat.lua / Tree.lua; this file draws and listens.
local ADDON, ns = ...
local Combat, Tree, Skills, Zone, Fx, Map = ns.Combat, ns.Tree, ns.Skills, ns.Zone, ns.Fx, ns.Map

local Game = {}
ns.Game = Game

local VW, VH = 640, 400            -- the field as it sits on screen, in the same units Combat.lua uses
local zoom, vw, vh = 1.4, 640 * 1.4, 400 * 1.4   -- how much world the field shows (units); zoom 1 = VW x VH, more = further out
local HUD_H, TITLE_H = 104, 24
local MAX_MON, MAX_DOODAD, MAX_PROJ, MAX_BLAST, MAX_FLOAT, MAX_DROP = 14, 22, 16, 6, 20, 8
local MAX_EFF, MAX_ZAP, MAX_BUFF, ZAP_DOTS, MAX_PART = 40, 10, 8, 8, 320
local SLOTS = 8
local ATTACK_RANGE = 300           -- how close you get to a clicked monster before the wand starts firing
local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end

-- Animation ids (AnimationData). 0 stand, 1 death, 4 walk, 5 run, 16 unarmed attack are standard; the cast id is a
-- guess to be corrected with /dread animtest.
Game.ANIM = { STAND = 0, DEATH = 1, WALK = 4, RUN = 5, ATTACK = 16, CAST = 51 }

-- Spell icons: guesses from memory of WoW's icon names.
local ICONS = {
  scorch="Spell_Fire_SoulBurn", evocation="Spell_Nature_Purge", dragons_breath="Spell_Fire_Incinerate",
  blazing_speed="Spell_Fire_BurningSpeed", fireball="Spell_Fire_FlameBolt", flamestrike="Spell_Fire_SelfDestruct",
  combustion="Spell_Fire_SealOfFire", meteor="Spell_Fire_Meteorstorm", master_of_flame="Spell_Fire_FlameShock",
  flame_spirit="Spell_Fire_Elemental_Totem",
  frostbolt="Spell_Frost_FrostBolt02", ice_barrier="Spell_Ice_Lament", frost_nova="Spell_Frost_FrostNova",
  ice_lance="Spell_Frost_FrostBolt", frost_armor="Spell_Frost_FrostArmor02", glacial_spike="Spell_Frost_Glacier",
  blizzard="Spell_Frost_IceStorm", icicle_cloak="Spell_Frost_ChillingArmor", frozen_orb="Spell_Frost_FrozenCore",
  piercing_cold="Spell_Frost_ChillingBlast",
  arcing_bolts="Spell_Nature_Lightning", static_shock="Spell_Nature_LightningShield", force_pull="Spell_Nature_WispSplode",
  thunder_nova="Spell_Nature_ThunderClap", lightning_bolt="Spell_Nature_Lightning", chain_lightning="Spell_Nature_ChainLightning",
  blink="Spell_Arcane_Blink", storm_cloud="Spell_Nature_CallStorm", mana_shield="Spell_Shadow_DetectLesserInvisibility",
  conductor="Spell_Nature_StormReach", wand="INV_Wand_07",
}
local function icon_path(id) return "Interface\\Icons\\" .. (ICONS[id] or "INV_Misc_QuestionMark") end


-- One line each, so a tooltip always says what the skill does.
local DESC = {
  scorch = "A bolt of fire.", dragons_breath = "A cone of flame in front of you for a second.",
  blazing_speed = "Run faster for 6 seconds, leaving burning ground behind you.", fireball = "A fireball that explodes where you click.",
  flamestrike = "Sets the chosen ground on fire for 4 seconds.", combustion = "Your fire spells hit harder for 10 seconds.",
  meteor = "A meteor lands where you click after a second, and the ground burns.", flame_spirit = "A spirit of fire that shoots the nearest monster for 15 seconds.",
  frostbolt = "A bolt of frost that chills.", ice_barrier = "Absorbs damage for 15 seconds.", frost_nova = "A ring of frost around you that chills everything it hits.",
  ice_lance = "A fast frost lance that can freeze.", frost_armor = "Take less damage for 20 seconds; whatever hits you is chilled.",
  glacial_spike = "A frost spike that explodes where you click.", blizzard = "An icy storm over the chosen ground for 5 seconds.",
  icicle_cloak = "For 15 seconds, whatever bites you takes frost damage.", frozen_orb = "An orb of frost that rolls to the target, hurting everything it passes.",
  arcing_bolts = "Three bolts of lightning in a spread.", static_shock = "Takes a share of the life of every monster near you. Wounds, never kills.",
  force_pull = "Pulls globes to you and throws nearby monsters back, stunned.", thunder_nova = "A ring of lightning around you.",
  lightning_bolt = "A fast bolt of lightning.", chain_lightning = "Lightning that jumps to up to three more monsters.",
  blink = "Teleport to where you click (up to 360 units).", storm_cloud = "For 8 seconds, lightning strikes monsters near you.",
  mana_shield = "Turn on and off: part of the damage you take comes out of your mana instead of your life.",
}
Game.DESC = DESC

local COLORS = { fire = { 1, 0.45, 0.1 }, cold = { 0.45, 0.75, 1 }, lightning = { 0.75, 0.6, 1 }, physical = { 0.9, 0.9, 0.9 } }
local function element_of(id) if id == "wand" then return "physical" end return Skills.byId[id].element end

-- Spell-effect models by fileDataID (from the community listfile; modern clients want ids, not paths).
local PROJ_MODEL = { scorch = 166129, fireball = 166129, frostbolt = 166214, ice_lance = 166214, glacial_spike = 166214,
                     arcing_bolts = 166497, lightning_bolt = 166497 }
local PROJ_SCALE = { scorch = 0.6, ice_lance = 0.7, arcing_bolts = 0.5, glacial_spike = 1.3 }
local BLAST_MODEL = { fire = 166114, cold = 166210, lightning = 166496 }

local world, area, cam = nil, nil, { x = 0, y = 0 }
local bar, sel = {}, 1
local target, hover_id
local toast_t = 0
local frame, arena, hud, tree_frame, handle
local ground, ground2, ground3, edge
local mon_f, doodad_f, proj_f, blast_f, float_f, drop_f = {}, {}, {}, {}, {}, {}
local doodad_slot = {}                -- scenery piece -> its frame, so models are not reassigned as you walk
local player_model
local life_orb, mana_orb, xp_bar, info_text, hint_text, over_text, zone_text, toast_text, exit_marks
local reset_btn, reset_armed
local solid_f, solid_on, solid_sizes = {}, false, {}
local eff_f, zap_f, buff_f, buff_shown = {}, {}, {}, {}
local fx, part_f, fx_drawn = nil, {}, 0
local mini, mini_cells, mini_dots, maps, mini_area, mini_clock = nil, {}, {}, {}, nil, 0
local target_ring
local RETARGET, MINI_W, MINI_H, MINI_DOTS = 300, 168, 105, 150
local slots = {}
Game.tree_buttons = {}
Game.paused = false

local function say(msg)
  msg = "|cffff5555Dread|r " .. msg
  if ns.log then ns.log(msg) else print(msg) end
end

---------------------------------------------------------------- what happened, recorded as it happens (Capture.lua)
function Game.session()
  if not Game._cap then
    DreadDB = DreadDB or {}
    Game._cap = ns.Capture.session(DreadDB, ns.BUILD, time and time() or 0)
  end
  return Game._cap
end

function Game.shot(why)                                           -- a screenshot of this moment, if the budget and the setting allow
  if DreadDB and DreadDB.shots == false then return false end
  if ns.Capture.shot_allowed(Game.session(), why) then return ns.Capture.shot() end
  return false
end

function Game.capture_enter(name)
  local s = Game.session()
  ns.Capture.enter(s, name)
  if s.areas[name].entered == 1 then Game.shot("arrived " .. name) end        -- the first look at each place
end

-- Monsters drawn from a bare model are white. The first time the game opens, quietly look for creature ids that give them their skins
-- (it stops as soon as every monster is covered, or at the end of the range, and is not repeated once it has finished).
Game.autofind = true
function Game.maybe_find()
  if not Game.autofind then return false end
  DreadDB = DreadDB or {}
  if ns.Finder.complete(DreadDB.found) or (DreadDB.found_scan and DreadDB.found_scan.done) or ns.Finder.running() then return false end
  return ns.Finder.start(nil, nil, say)
end

function Game.set_shots(on)
  DreadDB = DreadDB or {}
  if on == "on" or on == true then DreadDB.shots = true elseif on == "off" or on == false then DreadDB.shots = false end
  return DreadDB.shots ~= false
end

---------------------------------------------------------------- the save
local function save()
  if not world then return end
  DreadDB = DreadDB or {}
  DreadDB.char = Combat.snapshot(world)
  local b = {}
  for i = 1, SLOTS do b[i] = bar[i] or false end
  DreadDB.bar = b
end
ns.Gear.on_change = save                                      -- wearing or throwing away from the gear window is saved too

local function castable(id) return Combat.SHAPES[id] ~= nil and id ~= "wand" end

local function learned_spells()
  local list = {}
  for _, sk in ipairs(Skills) do
    if Tree.points_in(world.player.st, sk.id) > 0 and castable(sk.id) then list[#list + 1] = sk.id end
  end
  return list
end

-- New spells go into the first empty slot; spells you no longer have leave the bar.
local function sync_bar()
  local changed = false
  local have = {}
  for i = 1, SLOTS do
    local id = bar[i]
    if id and Tree.points_in(world.player.st, id) < 1 then bar[i], changed = nil, true end
    if bar[i] then have[bar[i]] = true end
  end
  for _, id in ipairs(learned_spells()) do
    if not have[id] then
      for i = 1, SLOTS do if not bar[i] then bar[i], have[id], changed = id, true, true; break end end
    end
  end
  if not bar[sel] then
    for i = 1, SLOTS do if bar[i] then sel = i; break end end
  end
  if changed then save() end
end

local function rotate(dir)
  for step = 1, SLOTS do
    local i = ((sel - 1 + dir * step) % SLOTS) + 1
    if bar[i] then sel = i; return end
  end
end

---------------------------------------------------------------- worlds and areas
local function enter(name, arrive)
  area = Zone.get(name)
  Game.capture_enter(name)
  Combat.enter(world, area)
  if arrive then world.player.x, world.player.y = arrive.x, arrive.y end
  target = nil
  doodad_slot = {}
  for _, f in ipairs(doodad_f) do f:Hide(); f.owner = nil end      -- free every scenery frame for the new area
  local fl = area.floor
  ground:SetTexture(fl.base, "REPEAT", "REPEAT")
  ground:SetVertexColor(fl.tint[1], fl.tint[2], fl.tint[3])
  ground2:SetTexture(fl.overlay, "REPEAT", "REPEAT")
  ground2:SetVertexColor(fl.overlay_tint[1], fl.overlay_tint[2], fl.overlay_tint[3])
  ground2:SetAlpha(fl.overlay_alpha)
  ground3:SetTexture(fl.patch, "REPEAT", "REPEAT")
  ground3:SetVertexColor(fl.patch_tint[1], fl.patch_tint[2], fl.patch_tint[3])
  ground3:SetAlpha(fl.patch_alpha)
  toast_text:SetTextColor(1, 1, 1); toast_text:SetText(area.title); toast_t = 3
end

local function new_world(into)                               -- into: the area to start in; none means the start of the game
  local seed = (time and time() or 1) % 2147483647
  world = Combat.new({ w = 2400, h = 1500, seed = seed })
  if DreadDB and DreadDB.char then Combat.restore(world, DreadDB.char) end
  bar = {}
  if DreadDB and type(DreadDB.bar) == "table" then
    for i = 1, SLOTS do local id = DreadDB.bar[i]; if type(id) == "string" and Skills.byId[id] then bar[i] = id end end
  end
  sel = 1
  hover_id = nil
  target = nil
  if frame then enter(into or Zone.START) end
  sync_bar()
end

---------------------------------------------------------------- small helpers
local function tex(parent, layer) return parent:CreateTexture(nil, layer or "ARTWORK") end
local function fstr(parent, size) return parent:CreateFontString(nil, "OVERLAY", size or "GameFontNormal") end
local function try(fn, ...) return pcall(fn, ...) end

local function world_xy()                 -- the cursor, in world coordinates
  local cx, cy = GetCursorPosition()
  local s = arena:GetEffectiveScale()                  -- the field has its own scale when zoomed
  return cx / s - arena:GetLeft() + cam.x, cy / s - arena:GetBottom() + cam.y
end

local function place(f, wx, wy, h)       -- feet of a model at a world position
  f:ClearAllPoints()
  f:SetPoint("BOTTOM", arena, "BOTTOMLEFT", wx - cam.x, wy - cam.y - h * 0.15)
end

local function depth(f, wy) f:SetFrameLevel(arena:GetFrameLevel() + 3 + math.floor((area.h - wy) / 6)) end

local function set_anim(f, id)
  if DreadDB and DreadDB.anim == false then id = Game.ANIM.STAND end        -- /dread anim off: every model just stands
  if f.anim ~= id then try(f.SetAnimation, f, id); f.anim = id end
end

local function face(f, dx, dy)
  if dx ~= 0 or dy ~= 0 then try(f.SetFacing, f, atan2(dy, dx) + (DreadDB and DreadDB.facing or 0)) end
end

---------------------------------------------------------------- the tree window
local function tooltip(btn, id)
  local sk = Skills.byId[id]
  local st = world.player.st
  GameTooltip:SetOwner(btn, "ANCHOR_RIGHT")
  GameTooltip:AddLine(sk.name, 1, 0.82, 0)
  GameTooltip:AddLine("Level " .. sk.req .. "  |  " .. sk.tree, 0.7, 0.7, 0.7)
  local pts = Tree.points_in(st, id)
  GameTooltip:AddLine("Points: " .. pts .. " / " .. Skills.MAX_POINTS, 1, 1, 1)
  if #sk.prereqs > 0 then
    local names = {}
    for _, p in ipairs(sk.prereqs) do names[#names + 1] = Skills.byId[p].name end
    GameTooltip:AddLine("Needs: " .. table.concat(names, ", "), 0.9, 0.6, 0.6)
  end
  if DESC[id] then GameTooltip:AddLine(DESC[id], 0.9, 0.9, 0.9, true) end
  if castable(id) then
    GameTooltip:AddLine("Hover and press 1-8 to put it on that slot of your bar", 0.5, 1, 0.5)
  elseif sk.kind == "passive" or sk.kind == "mastery" then
    GameTooltip:AddLine("Always on: nothing to cast", 0.6, 0.8, 1)
  end
  if sk.dmg then
    local lo, hi = Tree.damage(st, id)
    if lo then GameTooltip:AddLine(string.format("Damage now: %d - %d", math.floor(lo), math.floor(hi)), 0.6, 1, 0.6) end
    local s2 = { points = {}, level = 99, quest_points = 0 }
    for k, v in pairs(st.points) do s2.points[k] = v end
    s2.points[id] = math.min(Skills.MAX_POINTS, pts + 1)
    local lo2, hi2 = Tree.damage(s2, id)
    if lo2 then GameTooltip:AddLine(string.format("Next point: %d - %d", math.floor(lo2), math.floor(hi2)), 0.6, 0.8, 1) end
  end
  if sk.mana and pts > 0 then GameTooltip:AddLine(string.format("Mana: %.1f", Tree.mana_cost(st, id)), 0.5, 0.7, 1) end
  if sk.effect and pts > 0 then
    GameTooltip:AddLine(string.format("%s: %g", sk.effect.type, sk.effect.base + sk.effect.per_level * (pts - 1)), 0.8, 0.8, 0.8)
  end
  for _, s in ipairs(sk.syn or {}) do
    GameTooltip:AddLine(string.format("+%d%% per point in %s (you have %d)", s.pct, Skills.byId[s.from].name, Tree.points_in(st, s.from)), 0.9, 0.8, 0.4)
  end
  GameTooltip:Show()
end

local function refresh_tree()
  if not tree_frame then return end
  local st = world.player.st
  tree_frame.title:SetText(string.format("Skills   points to spend: %d", Tree.points_free(st)))
  for id, b in pairs(Game.tree_buttons) do
    local pts = Tree.points_in(st, id)
    local ok = Tree.can_allocate(st, id)
    b.count:SetText(pts > 0 and tostring(pts) or "")
    b.icon:SetDesaturated(pts == 0 and not ok)
    b.icon:SetAlpha((pts > 0 or ok) and 1 or 0.45)
  end
end

local function build_tree()
  tree_frame = CreateFrame("Frame", "DreadTreeFrame", UIParent, "BackdropTemplate")
  tree_frame:SetSize(3 * 4 * 50 + 40, 6 * 56 + 70)
  tree_frame:SetPoint("TOPLEFT", frame, "TOPRIGHT", 8, 0)
  tree_frame:SetClampedToScreen(true)
  tree_frame:SetFrameStrata("DIALOG")
  tree_frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
  tree_frame:SetBackdropColor(0, 0, 0, 0.92)
  tree_frame:SetBackdropBorderColor(0.6, 0.1, 0.1, 1)
  tree_frame:EnableMouse(true)
  local close = CreateFrame("Button", nil, tree_frame, "UIPanelButtonTemplate")
  close:SetSize(70, 20); close:SetPoint("TOPRIGHT", tree_frame, "TOPRIGHT", -8, -6); close:SetText("Close (K)")
  close:SetScript("OnClick", function() tree_frame:Hide() end)
  tree_frame.title = fstr(tree_frame)
  tree_frame.title:SetPoint("TOPLEFT", 14, -10)
  local gates = { [1] = 1, [6] = 2, [12] = 3, [18] = 4, [24] = 5, [30] = 6 }
  local col_of = { fire = 0, cold = 1, lightning = 2 }
  local seen = {}
  for _, sk in ipairs(Skills) do
    local key = sk.tree .. sk.req
    seen[key] = (seen[key] or 0) + 1
    local b = CreateFrame("Button", nil, tree_frame)
    b:SetSize(42, 42)
    b:SetPoint("TOPLEFT", tree_frame, "TOPLEFT", 20 + col_of[sk.tree] * 200 + (seen[key] - 1) * 50, -34 - (gates[sk.req] - 1) * 56)
    b.icon = tex(b); b.icon:SetAllPoints(b); b.icon:SetTexture(icon_path(sk.id))
    b.count = fstr(b, "GameFontHighlight"); b.count:SetPoint("BOTTOMRIGHT", b, "BOTTOMRIGHT", -2, 2)
    b:SetScript("OnClick", function()
      local ok, why = Tree.allocate(world.player.st, sk.id)
      if not ok then say(sk.name .. ": " .. tostring(why)) else sync_bar(); save() end
      refresh_tree()
    end)
    b:SetScript("OnEnter", function(self) hover_id = sk.id; tooltip(self, sk.id) end)
    b:SetScript("OnLeave", function() hover_id = nil; GameTooltip:Hide() end)
    Game.tree_buttons[sk.id] = b
  end
  for _, sk in ipairs(Skills) do                     -- lines to prerequisites, where the client can draw lines
    for _, p in ipairs(sk.prereqs) do
      try(function()
        local l = tree_frame:CreateLine(nil, "BACKGROUND")
        l:SetThickness(2)
        l:SetColorTexture(COLORS[sk.element][1], COLORS[sk.element][2], COLORS[sk.element][3], 0.5)
        l:SetStartPoint("CENTER", Game.tree_buttons[p])
        l:SetEndPoint("CENTER", Game.tree_buttons[sk.id])
      end)
    end
  end
  tree_frame:Hide()
end

---------------------------------------------------------------- the orbs
local ORB, MASK = 84, "Interface\\CharacterFrame\\TempPortraitAlphaMask"

-- A round gauge in the Diablo style: gold rim, dark glass, a fill that rises from the bottom, a little shine, the numbers in the middle.
-- The circle comes from a mask texture; if the client refuses masks the orb is simply square, it still works.
local function build_orb(parent, x, r, g, b)
  local frame_ = CreateFrame("Frame", nil, parent)
  frame_:SetSize(ORB + 12, ORB + 12)
  frame_:SetPoint("BOTTOMLEFT", parent, "BOTTOMLEFT", x, 4)
  local function disc(layer, size, cr, cg, cb, alpha)
    local t = frame_:CreateTexture(nil, layer)
    t:SetSize(size, size); t:SetPoint("CENTER", frame_, "CENTER", 0, 0)
    t:SetColorTexture(cr, cg, cb, alpha or 1)
    try(function()
      local m = frame_:CreateMaskTexture()
      m:SetTexture(MASK, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
      m:SetSize(size, size); m:SetPoint("CENTER", frame_, "CENTER", 0, 0)
      t:AddMaskTexture(m)
    end)
    return t
  end
  disc("BACKGROUND", ORB + 12, 0.62, 0.5, 0.2)          -- gold rim
  disc("BACKGROUND", ORB + 6, 0.05, 0.03, 0.03)        -- dark glass
  local fill = frame_:CreateTexture(nil, "ARTWORK")
  fill:SetColorTexture(r, g, b, 1)
  fill:SetPoint("BOTTOM", frame_, "BOTTOM", 0, 6); fill:SetSize(ORB, 1)
  try(function()
    local m = frame_:CreateMaskTexture()
    m:SetTexture(MASK, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
    m:SetSize(ORB, ORB); m:SetPoint("CENTER", frame_, "CENTER", 0, 0)
    fill:AddMaskTexture(m)
  end)
  local shine = disc("OVERLAY", ORB * 0.5, 1, 1, 1, 0.12)
  shine:ClearAllPoints(); shine:SetPoint("CENTER", frame_, "CENTER", -ORB * 0.16, ORB * 0.2)
  local text = frame_:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
  text:SetPoint("CENTER", frame_, "CENTER", 0, 0)
  local orb_ = { frame = frame_, text = text, fill = fill, frac = 0 }
  function orb_.set(frac, label)
    frac = math.max(0, math.min(1, frac))
    orb_.frac = frac
    fill:SetHeight(math.max(1, ORB * frac))
    text:SetText(label)
  end
  return orb_
end

---------------------------------------------------------------- the main window
local function model_pool(parent, n, w, h)
  local pool = {}
  for i = 1, n do
    local m = CreateFrame("PlayerModel", nil, parent)
    m:SetSize(w, h)
    m:Hide()
    pool[i] = m
  end
  return pool
end

-- Lua 5.1 (what WoW runs) lets one function use at most 60 outside variables, so the window is built in four steps.
local function build_minimap()
  mini = CreateFrame("Frame", nil, frame, "BackdropTemplate")
  mini:SetSize(MINI_W + 4, MINI_H + 4)
  mini:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -14, -(TITLE_H + 6))
  mini:SetFrameLevel(frame:GetFrameLevel() + 400)
  mini:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
  mini:SetBackdropColor(0, 0, 0, 0.55)
  mini:SetBackdropBorderColor(0.62, 0.5, 0.2, 1)
  for i = 1, MINI_DOTS do
    local d = mini:CreateTexture(nil, "OVERLAY")
    d:Hide()
    mini_dots[i] = d
  end
  if DreadDB and DreadDB.map == false then mini:Hide() else mini:Show() end
end

-- Zooming out shows more world: the field frame is made `zoom` times bigger and scaled down by the same factor, so it keeps
-- its size on screen while everything drawn in it (models, particles, ground) is smaller. The bottom bar is not affected.
local function apply_zoom(z)
  zoom, vw, vh = z, VW * z, VH * z
  if arena then
    arena:SetSize(vw, vh)
    arena:SetScale(1 / z)
    arena:ClearAllPoints()
    arena:SetPoint("TOPLEFT", frame, "TOPLEFT", 10 * z, -(TITLE_H + 2) * z)    -- anchor offsets are in the field's own (scaled) units
  end
end

local function build_window()
  frame = CreateFrame("Frame", "DreadGameFrame", UIParent, "BackdropTemplate")
  frame:SetSize(VW + 20, VH + HUD_H + TITLE_H + 14)
  frame:SetPoint("CENTER")
  frame:SetClampedToScreen(true)
  frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
  frame:SetBackdropColor(0, 0, 0, 0.95)
  frame:SetBackdropBorderColor(0.6, 0.1, 0.1, 1)
  frame:SetMovable(true); frame:EnableMouse(true); frame:EnableKeyboard(true); frame:EnableMouseWheel(true)

  -- only the title bar drags the window, so right click is free for casting
  handle = CreateFrame("Frame", nil, frame)
  handle:SetSize(VW + 20, TITLE_H)
  handle:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
  handle:EnableMouse(true)
  handle:RegisterForDrag("LeftButton")
  handle:SetScript("OnDragStart", function() frame:StartMoving() end)
  handle:SetScript("OnDragStop", function() frame:StopMovingOrSizing() end)
  local title = fstr(handle, "GameFontNormalSmall")
  title:SetPoint("LEFT", handle, "LEFT", 10, 0)
  title:SetText("Dread" .. (ns.BUILD and ("  (" .. ns.BUILD .. ")") or ""))
  zone_text = fstr(handle, "GameFontHighlightSmall")
  local skills_btn = CreateFrame("Button", nil, handle, "UIPanelButtonTemplate")
  skills_btn:SetSize(86, 20); skills_btn:SetPoint("RIGHT", handle, "RIGHT", -100, 0); skills_btn:SetText("Skills (K)")
  skills_btn:SetScript("OnClick", function() Game.toggle_tree() end)
  zone_text:SetPoint("RIGHT", skills_btn, "LEFT", -12, 0)
  -- reset asks twice, so a stray click cannot wipe a character
  reset_btn = CreateFrame("Button", nil, handle, "UIPanelButtonTemplate")
  reset_btn:SetSize(86, 20); reset_btn:SetPoint("RIGHT", handle, "RIGHT", -6, 0); reset_btn:SetText("New game")
  reset_btn:SetScript("OnClick", function() Game.press_reset() end)

end

local function build_arena()
  arena = CreateFrame("Frame", nil, frame)
  apply_zoom(zoom)
  arena:SetClipsChildren(true)
  ground = tex(arena, "BACKGROUND")
  ground:SetAllPoints(arena)
  ground:SetHorizTile(true); ground:SetVertTile(true)
  ground2 = arena:CreateTexture(nil, "BACKGROUND", nil, 1)         -- a big dirt layer over the grass, to hide the tiling
  ground2:SetAllPoints(arena)
  ground2:SetHorizTile(true); ground2:SetVertTile(true)
  ground3 = arena:CreateTexture(nil, "BACKGROUND", nil, 2)         -- a third, huge layer of a different ground: patches of variety instead of one repeating look
  ground3:SetAllPoints(arena)
  ground3:SetHorizTile(true); ground3:SetVertTile(true)
  edge = {}                                                        -- beyond the map: near-black void, with a lighter wall right at the boundary so the edge reads as an edge
  for i = 1, 4 do
    local v = arena:CreateTexture(nil, "BACKGROUND", nil, 3); v:SetColorTexture(0.01, 0.01, 0.02, 1); v:Hide()
    local wl = arena:CreateTexture(nil, "BACKGROUND", nil, 4); wl:SetColorTexture(0.42, 0.34, 0.22, 1); wl:Hide()
    edge[i] = { void = v, wall = wl }
  end

  doodad_f = model_pool(arena, MAX_DOODAD, 140, 170)
  mon_f = model_pool(arena, MAX_MON, 64, 80)
  for _, m in ipairs(mon_f) do
    m.fallback = tex(m, "ARTWORK"); m.fallback:SetAllPoints(m); m.fallback:SetColorTexture(0.7, 0.2, 0.2, 0.8); m.fallback:Hide()
    m.bar = tex(m, "OVERLAY"); m.bar:SetSize(40, 4); m.bar:SetPoint("BOTTOM", m, "TOP", 0, -2); m.bar:SetColorTexture(0.9, 0.1, 0.1, 1)
  end
  player_model = CreateFrame("PlayerModel", nil, arena)
  player_model:SetSize(70, 90)
  try(player_model.SetUnit, player_model, "player")

  target_ring = arena:CreateTexture(nil, "ARTWORK", nil, 1)
  target_ring:SetColorTexture(1, 0.15, 0.1, 1); target_ring:SetBlendMode("ADD"); target_ring:Hide()
  try(function()
    local m = arena:CreateMaskTexture()
    m:SetTexture(MASK, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
    m:SetAllPoints(target_ring)
    target_ring:AddMaskTexture(m)
  end)
  for i = 1, MAX_PROJ do
    local f = CreateFrame("PlayerModel", nil, arena); f:SetSize(70, 70); f:Hide()
    f.icon = tex(f, "OVERLAY"); f.icon:SetSize(26, 26); f.icon:SetPoint("CENTER"); f.icon:SetBlendMode("ADD")
    proj_f[i] = f
  end
  Game._mp = {}                                                    -- what monsters throw: a glowing bolt each, drawn where the rules say it is
  for i = 1, 12 do
    local t = tex(arena, "OVERLAY"); t:SetTexture("Interface\\Icons\\Spell_Shadow_ShadowBolt"); t:SetBlendMode("ADD"); t:Hide()
    Game._mp[i] = t
  end
  for i = 1, MAX_BLAST do
    local f = CreateFrame("PlayerModel", nil, arena); f:SetSize(150, 150); f:Hide()
    f.icon = tex(f, "OVERLAY"); f.icon:SetPoint("CENTER"); f.icon:SetBlendMode("ADD")
    f.life, f.max = 0, 0.6
    blast_f[i] = f
  end
  for i = 1, MAX_DROP do
    local t = tex(arena, "OVERLAY"); t:SetSize(22, 22); t:SetTexture(icon_path("wand")); t:Hide()
    t:SetTexture("Interface\\Icons\\INV_Potion_54"); t:SetDesaturated(true); drop_f[i] = t
  end
  for i = 1, MAX_FLOAT do
    local fs = fstr(arena, "GameFontHighlight"); fs:Hide(); float_f[i] = { fs = fs, t = 0 }
  end
  exit_marks = {}
  for i = 1, 2 do
    local t = tex(arena, "ARTWORK"); t:SetSize(56, 56); t:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")
    t:SetDesaturated(true); t:SetVertexColor(0.7, 0.4, 1); t:SetBlendMode("ADD"); t:Hide()
    local l = fstr(arena, "GameFontNormalSmall"); l:Hide()
    exit_marks[i] = { t = t, l = l }
  end
  for i = 1, MAX_EFF do                                          -- zones, trails, orbs, cones, markers
    local d = arena:CreateTexture(nil, "ARTWORK", nil, 2)
    d:SetColorTexture(1, 1, 1, 1); d:SetBlendMode("ADD"); d:Hide()
    try(function()
      local m = arena:CreateMaskTexture()
      m:SetTexture(MASK, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
      m:SetAllPoints(d)
      d:AddMaskTexture(m)
    end)
    local ic = arena:CreateTexture(nil, "ARTWORK", nil, 3)
    ic:SetSize(30, 30); ic:SetBlendMode("ADD"); ic:Hide()
    eff_f[i] = { disc = d, icon = ic }
  end
  for i = 1, MAX_ZAP do                                          -- a beam is a row of small glowing dots
    local z = { dots = {}, life = 0 }
    for j = 1, ZAP_DOTS do
      local t = arena:CreateTexture(nil, "OVERLAY", nil, 2)
      t:SetSize(16, 16); t:SetBlendMode("ADD"); t:Hide()
      z.dots[j] = t
    end
    zap_f[i] = z
  end
  for i = 1, MAX_BUFF do                                         -- active buffs, top left, with their timers
    local ic = arena:CreateTexture(nil, "OVERLAY", nil, 3)
    ic:SetSize(26, 26); ic:SetPoint("TOPLEFT", arena, "TOPLEFT", 6 + (i - 1) * 32, -6); ic:Hide()
    local tx = arena:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    tx:SetPoint("TOP", ic, "BOTTOM", 0, 0); tx:Hide()
    buff_f[i] = { icon = ic, text = tx }
  end
  fx = Fx.new(7)
  for i = 1, MAX_PART do                                         -- sparks, flames, snow, shield rings: small glowing dots
    local d = arena:CreateTexture(nil, "OVERLAY", nil, 4)
    d:SetColorTexture(1, 1, 1, 1); d:SetBlendMode("ADD"); d:Hide()
    try(function()
      local m = arena:CreateMaskTexture()
      m:SetTexture(MASK, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
      m:SetAllPoints(d)
      d:AddMaskTexture(m)
    end)
    part_f[i] = d
  end
  for i = 1, 48 do                                              -- the /dread solid circles
    local t = arena:CreateTexture(nil, "OVERLAY", nil, 3)
    t:SetColorTexture(1, 0.1, 0.1, 0.4); t:Hide()
    try(function()
      local m = arena:CreateMaskTexture()
      m:SetTexture(MASK, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
      m:SetAllPoints(t)
      t:AddMaskTexture(m)
    end)
    solid_f[i] = t
  end
  over_text = fstr(arena, "GameFontNormalLarge")
  over_text:SetPoint("CENTER", arena, "CENTER", 0, 0); over_text:Hide()
  toast_text = fstr(arena, "GameFontNormalLarge")
  toast_text:SetPoint("TOP", arena, "TOP", 0, -30)

end

local function build_hud()
  hud = CreateFrame("Frame", nil, frame)
  hud:SetSize(VW, HUD_H)
  hud:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 10, 6)
  life_orb = build_orb(hud, 0, 0.78, 0.08, 0.08)
  mana_orb = build_orb(hud, VW - (ORB + 12), 0.12, 0.28, 0.9)
  local mid = ORB + 12 + (VW - 2 * (ORB + 12) - SLOTS * 42) / 2      -- the skill bar sits centred between the orbs
  for i = 1, SLOTS do
    local b = CreateFrame("Button", nil, hud)
    b:SetSize(40, 40)
    b:SetPoint("TOPLEFT", hud, "TOPLEFT", mid + (i - 1) * 42, -6)
    b.bg = tex(b, "BACKGROUND"); b.bg:SetAllPoints(b); b.bg:SetColorTexture(0.12, 0.1, 0.08, 0.95)
    b.icon = tex(b); b.icon:SetAllPoints(b)
    b.key = fstr(b, "GameFontHighlightSmall"); b.key:SetPoint("TOPLEFT", 2, -2); b.key:SetText(tostring(i))
    b.sel = tex(b, "OVERLAY"); b.sel:SetAllPoints(b); b.sel:SetColorTexture(1, 0.85, 0.3, 0.35); b.sel:Hide()
    b:SetScript("OnClick", function() if bar[i] then sel = i end end)
    slots[i] = b
  end
  xp_bar = tex(hud); xp_bar:SetPoint("TOPLEFT", hud, "TOPLEFT", mid, -52); xp_bar:SetSize(SLOTS * 42 - 2, 5); xp_bar:SetColorTexture(0.9, 0.8, 0.2, 1)
  info_text = fstr(hud, "GameFontHighlightSmall"); info_text:SetPoint("TOPLEFT", hud, "TOPLEFT", mid, -62)
  hint_text = fstr(hud, "GameFontNormalSmall"); hint_text:SetPoint("TOPLEFT", hud, "TOPLEFT", mid - 20, -76)
  hint_text:SetWidth(SLOTS * 42 + 40)
  hint_text:SetJustifyH("LEFT")

end

local function build_input()
  frame:SetScript("OnMouseDown", function(_, button)
    if world.over then new_world(area and area.name); return end                -- you get up where you fell, not back at the start of the game
    local x, y = world_xy()
    if x < cam.x or y < cam.y or x > cam.x + vw or y > cam.y + vh then return end
    if button == "RightButton" then
      local id = bar[sel]
      if not id then hint_text:SetText("No skill on that slot. Open the tree (K), spend a point, hover the skill and press 1-8."); return end
      local ok, why = Combat.cast(world, id, x, y)
      if not ok then hint_text:SetText(Skills.byId[id].name .. ": " .. tostring(why)) end
    elseif button == "LeftButton" then
      if IsShiftKeyDown and IsShiftKeyDown() and bar[sel] then
        Combat.cast(world, bar[sel], x, y)
        return
      end
      target = nil
      for _, m in ipairs(world.monsters) do
        if not m.dead and math.sqrt((m.x - x) ^ 2 + (m.y - y) ^ 2) <= m.radius + 24 then target = m; break end
      end
      if not target then Combat.move_to(world, x, y) end
    end
  end)
  frame:SetScript("OnMouseWheel", function(_, delta) rotate(delta > 0 and -1 or 1) end)
  frame:SetScript("OnKeyDown", function(self, key)
    local handled = false
    local n = tonumber(key)
    if n and n >= 1 and n <= SLOTS then
      if tree_frame:IsShown() and hover_id and castable(hover_id) and Tree.points_in(world.player.st, hover_id) > 0 then
        for i = 1, SLOTS do if bar[i] == hover_id then bar[i] = nil end end
        bar[n], sel = hover_id, n
        hint_text:SetText(Skills.byId[hover_id].name .. " is now on slot " .. n)
        save()
      elseif bar[n] then
        if Combat.self_cast(bar[n]) then                                  -- no aim needed: the key is the whole cast, and right click stays on what it was
          if not world.over then
            local ok, why = Combat.cast(world, bar[n], world.player.x, world.player.y)
            if not ok then hint_text:SetText(Skills.byId[bar[n]].name .. ": " .. tostring(why)) end
          end
        else
          sel = n
        end
      end
      handled = true
    elseif key == "TAB" then rotate(1); handled = true
    elseif key == "K" then Game.toggle_tree(); handled = true
    elseif key == "M" then Game.toggle_map(); handled = true
    elseif key == "I" then ns.Gear.toggle(world); handled = true
    end
    self:SetPropagateKeyboardInput(not handled)
  end)
  frame:SetScript("OnUpdate", function(_, dt) Game.tick(dt) end)
end

local function build()
  build_window()
  build_arena()
  build_hud()
  build_input()
  build_tree()
  build_minimap()
  frame:Hide()
end

---------------------------------------------------------------- the minimap
local function mini_cell_color()
  if area.name == "cave" then return 0.42, 0.36, 0.3, 0.75 end
  return 0.22, 0.42, 0.2, 0.75
end

-- Reveal what you can see now, show only this area's revealed cells, then place the dots.
local function update_minimap(dt, p)
  local m = maps[area.name]
  if not m then m = Map.new(area.w, area.h); maps[area.name] = m end
  if mini_area ~= area.name then                                  -- changed area: swap which area's cells are showing
    for _, set in pairs(mini_cells) do for _, t in pairs(set) do t:Hide() end end
    mini_area = area.name
    for _, t in pairs(mini_cells[area.name] or {}) do t:Show() end
  end
  mini_cells[area.name] = mini_cells[area.name] or {}
  for _, c in ipairs(Map.reveal(m, p.x, p.y, 260)) do
    local t = mini:CreateTexture(nil, "ARTWORK")
    local l, b, w, h = Map.cell_rect(m, c.ix, c.iy, MINI_W, MINI_H)
    t:SetColorTexture(mini_cell_color())
    t:SetSize(w + 0.6, h + 0.6); t:SetPoint("BOTTOMLEFT", mini, "BOTTOMLEFT", 2 + l, 2 + b)
    mini_cells[area.name][c.iy * m.cols + c.ix] = t
  end
  mini_clock = mini_clock + dt
  if mini_clock < 0.15 then return end                            -- the dots do not need to move every frame
  mini_clock = 0
  local n, stats = 0, { obstacles = 0, monsters = 0, exits = 0 }
  local function dot(x, y, size, r, g, b, kind)
    if n < MINI_DOTS then
      n = n + 1
      local d, mx, my = mini_dots[n], Map.to_mini(m, x, y, MINI_W, MINI_H)
      d:SetColorTexture(r, g, b, 1); d:SetSize(size, size)
      d:ClearAllPoints(); d:SetPoint("CENTER", mini, "BOTTOMLEFT", 2 + mx, 2 + my); d:Show()
      if kind then stats[kind] = stats[kind] + 1 end
    end
  end
  for _, o in ipairs(world.obstacles) do
    if Map.is_seen(m, o.x, o.y) and n < MINI_DOTS - 50 then dot(o.x, o.y, 2, 0.1, 0.25, 0.1, "obstacles") end
  end
  for _, ex in ipairs(area.exits) do
    if Map.is_seen(m, ex.x, ex.y) then dot(ex.x, ex.y, 6, 0.8, 0.4, 1, "exits") end
  end
  for _, mon in ipairs(world.monsters) do
    if not mon.dead and (mon.x - p.x) ^ 2 + (mon.y - p.y) ^ 2 <= 380 * 380 then dot(mon.x, mon.y, 3, 1, 0.2, 0.2, "monsters") end
  end
  dot(p.x, p.y, 5, 1, 0.9, 0.2)                                  -- you
  for i = n + 1, MINI_DOTS do mini_dots[i]:Hide() end
  stats.seen = m.count
  Game._mini_stats = stats
end

function Game.toggle_map()
  DreadDB = DreadDB or {}
  if mini:IsShown() then mini:Hide(); DreadDB.map = false else mini:Show(); DreadDB.map = true end
  return mini:IsShown()
end

function Game.minimap()
  local st = Game._mini_stats or { obstacles = 0, monsters = 0, exits = 0, seen = 0 }
  local cells = 0
  for _ in pairs(mini_cells[area and area.name or ""] or {}) do cells = cells + 1 end
  return { shown = mini ~= nil and mini:IsShown(), cells = cells, obstacles = st.obstacles, monsters = st.monsters, exits = st.exits, seen = st.seen }
end

---------------------------------------------------------------- one frame of the game
local function vis(sx, sy, mx, my) return sx > -mx and sx < vw + mx and sy > -my and sy < vh + my end

local function draw_scenery()
  -- keep a scenery piece on the frame it already has; hand free frames to pieces that have just come into view
  local seen = {}
  for _, d in ipairs(area.doodads) do
    if vis(d.x - cam.x, d.y - cam.y, 80, 100) then
      seen[d] = true
      if not doodad_slot[d] then
        for _, f in ipairs(doodad_f) do
          if not f.owner then
            f.owner, doodad_slot[d] = d, f
            local spec = Zone.SCENERY[d.kind]
            f:SetSize(d.w * spec.frame, d.h * spec.frame)           -- bigger than the model, or it is cut off at the frame edge
            try(f.SetModel, f, d.id)
            try(f.SetCamDistanceScale, f, Game.cam_for(d.kind))
            f.fallback_missing = false
            f:Show()
            break
          end
        end
      end
    end
  end
  for d, f in pairs(doodad_slot) do
    if not seen[d] then f.owner, doodad_slot[d] = nil, nil; f:Hide() end
  end
  for d, f in pairs(doodad_slot) do
    place(f, d.x, d.y, d.h); depth(f, d.y)
  end
end

-- A beam between two points: a row of dots that fades.
local function start_zap(e)
  local el = element_of(e.id)
  for _, z in ipairs(zap_f) do
    if z.life <= 0 then
      z.life, z.max, z.x1, z.y1, z.x2, z.y2 = 0.3, 0.3, e.x1, e.y1, e.x2, e.y2
      for _, t in ipairs(z.dots) do t:SetTexture(icon_path(e.id)); t:SetVertexColor(COLORS[el][1], COLORS[el][2], COLORS[el][3]) end
      return
    end
  end
end

-- Timed effects (zones, trails, orbs, cones, markers, the spirit, the storm), beams, and the buff icons.
local function draw_effects(dt, p)
  local n = 0
  for _, e in ipairs(world.effects) do
    if n < MAX_EFF then
      local el = element_of(e.id)
      local c = COLORS[el]
      local x, y, size, alpha, icon = e.x, e.y, 0, 0.3 + 0.1 * math.sin(world.time * 8), nil
      if e.kind == "zone" or e.kind == "orb" then size = e.r * 2
      elseif e.kind == "cone" then size = 0                        -- the flames are the particles; a square under them looked wrong
      elseif e.kind == "delayed" then
        size, alpha, icon = e.r * 2, 0.15 + 0.35 * (1 - math.max(0, e.t)), "meteor"
      elseif e.kind == "summon" then size, icon = 30, e.id
      elseif e.kind == "storm" then size, y, icon, alpha = e.r * 2, e.y + 70, e.id, 0.12
      end
      if size > 0 and vis(x - cam.x, y - cam.y, size, size) then
        n = n + 1
        local f = eff_f[n]
        f.disc:SetVertexColor(c[1], c[2], c[3]); f.disc:SetAlpha(alpha)
        f.disc:SetSize(size, size); f.disc:ClearAllPoints(); f.disc:SetPoint("CENTER", arena, "BOTTOMLEFT", x - cam.x, y - cam.y); f.disc:Show()
        if icon or e.kind == "orb" then
          f.icon:SetTexture(icon_path(icon or e.id)); f.icon:SetVertexColor(c[1], c[2], c[3])
          try(f.icon.SetRotation, f.icon, world.time * ((e.kind == "orb") and 5 or 2))
          f.icon:ClearAllPoints(); f.icon:SetPoint("CENTER", arena, "BOTTOMLEFT", x - cam.x, y - cam.y + ((e.kind == "summon") and 18 or 0)); f.icon:Show()
        else
          f.icon:Hide()
        end
      end
    end
  end
  for i = n + 1, MAX_EFF do eff_f[i].disc:Hide(); eff_f[i].icon:Hide() end
  for _, z in ipairs(zap_f) do
    if z.life > 0 then
      z.life = z.life - dt
      for j, t in ipairs(z.dots) do
        local k = (j - 1) / (ZAP_DOTS - 1)
        t:ClearAllPoints()
        t:SetPoint("CENTER", arena, "BOTTOMLEFT", z.x1 + (z.x2 - z.x1) * k - cam.x, z.y1 + (z.y2 - z.y1) * k - cam.y)
        t:SetAlpha(math.max(0, z.life / z.max)); t:Show()
      end
      if z.life <= 0 then for _, t in ipairs(z.dots) do t:Hide() end end
    end
  end
  -- buff icons with what is left of each
  local names = {}
  for id in pairs(p.buffs) do names[#names + 1] = id end
  table.sort(names)
  buff_shown = {}
  for i = 1, MAX_BUFF do
    local b, f = p.buffs[names[i] or ""], buff_f[i]
    if b then
      local label = b.t and tostring(math.ceil(b.t)) or "on"
      if names[i] == "ice_barrier" then label = tostring(math.floor(b.amount)) end
      f.icon:SetTexture(icon_path(names[i])); f.icon:Show()
      f.text:SetText(label); f.text:Show()
      buff_shown[#buff_shown + 1] = names[i] .. ":" .. label
    else
      f.icon:Hide(); f.text:Hide()
    end
  end
end

-- Move the particles on and draw them, plus the rings around you while a shield or buff is up.
local function draw_fx(dt)
  local level = (DreadDB and DreadDB.fx) or 1
  fx.scale = level
  if not Game.paused then Fx.update(fx, world, dt) end
  local n = 0
  local function dot(x, y, size, alpha, r, g, b)
    local sx, sy = x - cam.x, y - cam.y
    if n < MAX_PART and sx > -30 and sx < vw + 30 and sy > -30 and sy < vh + 30 then
      n = n + 1
      local d = part_f[n]
      d:SetVertexColor(r, g, b); d:SetAlpha(alpha); d:SetSize(size, size)
      d:ClearAllPoints(); d:SetPoint("CENTER", arena, "BOTTOMLEFT", sx, sy); d:Show()
    end
  end
  if level > 0 then
    for _, q in ipairs(fx.list) do
      local k = q.t / q.max
      dot(q.x, q.y, q.s0 + (q.s1 - q.s0) * k, q.a0 * (1 - k), q.r, q.g, q.b)
    end
    for _, a in ipairs(Fx.auras(fx, world)) do dot(a.x, a.y, a.size, a.alpha, a.r, a.g, a.b) end
  end
  for i = n + 1, MAX_PART do part_f[i]:Hide() end
  fx_drawn = n
end

local function next_target(p)
  local best, bd = nil, RETARGET
  for _, m in ipairs(world.monsters) do
    if not m.dead and m.awake then                                -- only what is already fighting: it never wakes a sleeping pack
      local d = math.sqrt((m.x - p.x) ^ 2 + (m.y - p.y) ^ 2)
      if d <= bd then best, bd = m, d end
    end
  end
  return best
end

-- Draw the void and the boundary wall for whatever part of the view lies outside the map. Sides: 1 left, 2 right, 3 below, 4 above.
local WALL = 10
function Game.draw_edges(cx, cy)
  local rects = {                                                  -- x, y, w, h in view units, from the arena's bottom-left
    { 0, 0, math.max(0, -cx), vh },                                  -- left of x = 0
    { area.w - cx, 0, math.max(0, vw - (area.w - cx)), vh },        -- right of x = area.w
    { 0, 0, vw, math.max(0, -cy) },                                  -- below y = 0
    { 0, area.h - cy, vw, math.max(0, vh - (area.h - cy)) },        -- above y = area.h
  }
  local walls = {
    { -cx - WALL, 0, WALL, vh }, { area.w - cx, 0, WALL, vh }, { 0, -cy - WALL, vw, WALL }, { 0, area.h - cy, vw, WALL },
  }
  Game._edges = {}
  for i = 1, 4 do
    local r, wl, e = rects[i], walls[i], edge[i]
    if r[3] > 0 and r[4] > 0 then
      e.void:ClearAllPoints(); e.void:SetPoint("BOTTOMLEFT", arena, "BOTTOMLEFT", r[1], r[2]); e.void:SetSize(r[3], r[4]); e.void:Show()
    else
      e.void:Hide()
    end
    local inside = (i == 1 and cx < 0) or (i == 2 and cx + vw > area.w) or (i == 3 and cy < 0) or (i == 4 and cy + vh > area.h)
    if inside then
      e.wall:ClearAllPoints(); e.wall:SetPoint("BOTTOMLEFT", arena, "BOTTOMLEFT", wl[1], wl[2]); e.wall:SetSize(wl[3], wl[4]); e.wall:Show()
    else
      e.wall:Hide()
    end
    Game._edges[i] = { void = e.void:IsShown(), x = r[1], y = r[2], w = r[3], h = r[4] }
  end
end

local function advance(dt, p)
  -- walk up to a clicked monster and keep using the wand on it
  if target and not world.over and not Game.paused then
    if target.dead then target = next_target(p)                 -- the last one is down: carry on with whoever is fighting you
    else
      local d = math.sqrt((target.x - p.x) ^ 2 + (target.y - p.y) ^ 2)
      if d > ATTACK_RANGE then Combat.move_to(world, target.x, target.y)
      else p.tx, p.ty = nil, nil; Combat.attack(world, target.x, target.y) end
    end
  end
  if not world.over and not Game.paused then Combat.step(world, dt) end
  sync_bar()

  -- leave through an exit?
  if not Game.paused and not world.over then
    for _, ex in ipairs(area.exits) do
      if math.sqrt((p.x - ex.x) ^ 2 + (p.y - ex.y) ^ 2) <= ex.r then
        local dest = Zone.get(ex.to)
        enter(ex.to, ex.arrive or dest.spawn)
        break
      end
    end
  end

  -- the camera follows you
  cam.x = p.x - vw / 2                                            -- locked on you, like Diablo II: the room moves around you, even at the map's edge
  cam.y = p.y - vh / 2
  local fl = area.floor
  local T = (DreadDB and DreadDB.tile) or fl.tile
  ground:SetTexCoord(cam.x / T, (cam.x + vw) / T, -(cam.y + vh) / T, -cam.y / T)
  local T2 = fl.overlay_tile
  ground2:SetTexCoord(cam.x / T2, (cam.x + vw) / T2, -(cam.y + vh) / T2, -cam.y / T2)
  local T3 = fl.patch_tile
  ground3:SetTexCoord(cam.x / T3, (cam.x + vw) / T3, -(cam.y + vh) / T3, -cam.y / T3)
  Game.draw_edges(cam.x, cam.y)
  draw_scenery()
  do                                                              -- the blocking circles, when asked for
    local n = 0
    solid_sizes = {}
    if solid_on then
      for _, o in ipairs(world.obstacles) do
        local sx, sy = o.x - cam.x, o.y - cam.y
        if n < #solid_f and vis(sx, sy, 40, 40) then
          n = n + 1
          local t = solid_f[n]
          t:SetSize(o.r * 2, o.r * 2); t:ClearAllPoints(); t:SetPoint("CENTER", arena, "BOTTOMLEFT", sx, sy); t:Show()
          solid_sizes[#solid_sizes + 1] = o.r * 2
        end
      end
    end
    for i = n + 1, #solid_f do solid_f[i]:Hide() end
  end

end

local function draw_target_ring()
  if target and not target.dead and vis(target.x - cam.x, target.y - cam.y, 40, 40) then
    local size = (target.radius + 12) * 2 * (1 + 0.06 * math.sin(world.time * 6))
    target_ring:SetSize(size, size); target_ring:SetAlpha(0.35)
    target_ring:ClearAllPoints(); target_ring:SetPoint("CENTER", arena, "BOTTOMLEFT", target.x - cam.x, target.y - cam.y - 4); target_ring:Show()
  else
    target_ring:Hide()
  end
end

local function draw_actors(p)
  draw_target_ring()
  -- you
  place(player_model, p.x, p.y, 90); depth(player_model, p.y)
  local casting = (world.time - p.cast_at) < 0.5
  if world.over then set_anim(player_model, Game.ANIM.DEATH)
  elseif casting then set_anim(player_model, Game.ANIM.CAST)
  elseif p.tx then set_anim(player_model, Game.ANIM.RUN)
  else set_anim(player_model, Game.ANIM.STAND) end
  if p.tx then face(player_model, p.tx - p.x, p.ty - p.y)
  elseif target and not target.dead then face(player_model, target.x - p.x, target.y - p.y) end

  -- monsters: the boss first, then the nearest on screen. A frame stays with its monster until that monster drops out of the
  -- chosen set, so a model is not reassigned (and re-sized) every time the order shifts.
  local cand = {}
  for _, m in ipairs(world.monsters) do
    local gone = m.dead and (world.time - (m.died_at or 0) > 3)
    if not gone and vis(m.x - cam.x, m.y - cam.y, 60, 80) then cand[#cand + 1] = m end
  end
  table.sort(cand, function(a, b)
    if (a.boss and true or false) ~= (b.boss and true or false) then return a.boss and true or false end
    return (a.x - p.x) ^ 2 + (a.y - p.y) ^ 2 < (b.x - p.x) ^ 2 + (b.y - p.y) ^ 2
  end)
  local want, have = {}, {}
  for i = 1, math.min(MAX_MON, #cand) do want[cand[i]] = true end
  for _, f in ipairs(mon_f) do
    if f.owner and not want[f.owner] then f.owner = nil end
    if f.owner then have[f.owner] = f end
  end
  for i = 1, math.min(MAX_MON, #cand) do
    local m = cand[i]
    if not have[m] then
      for _, f in ipairs(mon_f) do
        if not f.owner then
          f.owner, f.anim = m, nil
          local ok
          local cid = m.cid or ns.Finder.npc_for(DreadDB and DreadDB.found, m.model)       -- a creature id gives the model its skin; a bare model comes out white
          if cid then ok = try(f.SetCreature, f, cid) else ok = try(f.SetModel, f, m.model) end
          f.fallback:SetShown(not ok)
          try(f.SetModelScale, f, 1)                            -- size comes from the frame alone (below); scaling the model as well made the boss twice as big as meant
          have[m] = f
          break
        end
      end
    end
  end
  for i = 1, MAX_MON do
    local f = mon_f[i]
    local m = f.owner
    if m then
      local size = (m.scale or 1)
      f:SetSize(64 * size, 80 * size)
      place(f, m.x, m.y, 80 * size); depth(f, m.y)
      f:SetAlpha(m.dead and 0.5 or ((m.freeze > 0) and 0.6 or 1))
      f.bar:SetWidth(math.max(1, 40 * math.max(0, m.life) / m.maxlife))
      f.bar:SetShown(not m.dead)
      if m.dead then set_anim(f, Game.ANIM.DEATH)
      elseif m.windup or (m.bite_at and world.time - m.bite_at < 0.45) then set_anim(f, Game.ANIM.ATTACK)           -- the wind-up shows: it is about to throw
      elseif m.moving then set_anim(f, Game.ANIM.WALK)
      else set_anim(f, Game.ANIM.STAND) end
      if not m.dead and m.awake then face(f, p.x - m.x, p.y - m.y) end
      f:Show()
    else
      f.owner = nil; f:Hide()
    end
  end

end

-- The detail goes to the Dread log (coloured by tier); the screen only gets a short line, louder the rarer it is.
local TOAST = { common = { "Found an item", 1.5, 0.8, 0.8, 0.8 }, magic = { "Found an item", 1.5, 0.55, 0.7, 1 },
                rare = { "Rare item found!", 3, 1, 0.85, 0.3 }, unique = { "UNIQUE ITEM FOUND!", 5, 1, 0.6, 0.18 } }
local function announce_item(e)
  local it, c = e.item, ns.Gear.COLOR[e.item.rarity] or ""
  say("Found " .. c .. ns.Items.name(it) .. "|r (" .. it.rarity .. ", level " .. it.ilvl .. "): " .. table.concat(ns.Items.lines(it), ", ")
      .. (e.how == "bagged" and "  [bag, I to wear]" or "  [worn]"))
  local t = TOAST[it.rarity] or TOAST.common
  toast_text:SetText(t[1] .. (it.rarity == "unique" and ("  " .. ns.Items.name(it)) or "")); toast_text:SetTextColor(t[3], t[4], t[5]); toast_t = t[2]
  if (it.rarity == "rare" or it.rarity == "unique") and PlaySound then pcall(PlaySound, 888) end      -- the level-up chime
end

local function draw_world_and_events(dt, p)
  -- spell effects
  draw_effects(dt, p)
  for i = 1, MAX_PROJ do
    local pr, f = world.projectiles[i], proj_f[i]
    if pr then
      local el = element_of(pr.id)
      local c = COLORS[el]
      if f.pid ~= pr.id then
        f.pid = pr.id
        f.icon:SetTexture(icon_path(pr.id)); f.icon:SetVertexColor(c[1], c[2], c[3])
        local mid = PROJ_MODEL[pr.id]
        if mid then try(f.SetModel, f, mid); try(f.SetModelScale, f, PROJ_SCALE[pr.id] or 1) end
      end
      f:ClearAllPoints(); f:SetPoint("CENTER", arena, "BOTTOMLEFT", pr.x - cam.x, pr.y - cam.y)
      try(f.icon.SetRotation, f.icon, world.time * 9)                -- the glow spins
      f.icon:SetSize(24 + 6 * math.sin(world.time * 14), 24 + 6 * math.sin(world.time * 14))
      face(f, pr.vx, pr.vy)
      f:SetFrameLevel(arena:GetFrameLevel() + 300)
      f:Show()
    else
      f.pid = nil; f:Hide()
    end
  end
  for i = 1, 12 do
    local q, t = world.mproj[i], Game._mp[i]
    if q then
      local size = q.boss and 40 or 22
      if q.boss then t:SetVertexColor(0.75, 0.35, 1) else t:SetVertexColor(1, 0.85, 0.5) end
      t:SetSize(size, size); t:ClearAllPoints(); t:SetPoint("CENTER", arena, "BOTTOMLEFT", q.x - cam.x, q.y - cam.y)
      try(t.SetRotation, t, world.time * 8)
      t:Show()
    else
      t:Hide()
    end
  end
  for _, e in ipairs(Combat.drain(world)) do
    Fx.on_event(fx, e, world)
    local why = ns.Capture.event(Game.session(), e)
    if why then Game.shot(why) end
    if e.k == "level" then Game.shot("level " .. e.level) end
    if e.k == "hit" and e.dmg > 0 then
      for _, fl in ipairs(float_f) do
        if fl.t <= 0 then
          fl.t, fl.x, fl.y = 0.8, e.x, e.y + 40
          fl.fs:SetText(tostring(math.floor(e.dmg + 0.5)))
          local c = COLORS[element_of(e.id)]; fl.fs:SetTextColor(c[1], c[2], c[3])
          break
        end
      end
    elseif e.k == "blast" then
      for _, f in ipairs(blast_f) do
        if f.life <= 0 then
          local el = element_of(e.id)
          f.life, f.x, f.y, f.r = f.max, e.x, e.y, e.r
          f.icon:SetTexture(icon_path(e.id)); f.icon:SetVertexColor(COLORS[el][1], COLORS[el][2], COLORS[el][3])
          if BLAST_MODEL[el] then try(f.SetModel, f, BLAST_MODEL[el]) end
          break
        end
      end
    elseif e.k == "zap" then
      start_zap(e)
    elseif e.k == "blink" then
      for _, at in ipairs({ { e.x0, e.y0 }, { e.x1, e.y1 } }) do
        for _, f in ipairs(blast_f) do
          if f.life <= 0 then
            f.life, f.x, f.y, f.r = f.max, at[1], at[2], 36
            f.icon:SetTexture(icon_path("blink")); f.icon:SetVertexColor(COLORS.lightning[1], COLORS.lightning[2], COLORS.lightning[3])
            break
          end
        end
      end
    elseif e.k == "level" then
      toast_text:SetTextColor(1, 1, 1); toast_text:SetText("Level " .. e.level .. "!  Press K to spend a skill point."); toast_t = 4
      save()
    elseif e.k == "item" then
      announce_item(e)
      ns.Gear.refresh(world)
      save()
    elseif e.k == "full" then
      toast_text:SetTextColor(1, 1, 1); toast_text:SetText("Bag full: open it with I and throw something away"); toast_t = 3
    elseif e.k == "kill" or e.k == "pickup" then
      save()
    elseif e.k == "boss_dead" then
      local q = Zone.quest_by_boss(e.name)
      if q and not world.flags[q.id] then
        world.flags[q.id] = true
        world.player.st.quest_points = world.player.st.quest_points + q.reward_points
        toast_text:SetTextColor(1, 0.85, 0.3); toast_text:SetText("Quest complete: " .. q.title .. ".  +" .. q.reward_points .. " skill point.  Press K."); toast_t = 6
        say("Quest complete: " .. q.title .. " (+" .. q.reward_points .. " skill point)")
        save()
      end
    end
  end
  draw_fx(dt)
  for _, fl in ipairs(float_f) do
    if fl.t > 0 then
      fl.t = fl.t - dt; fl.y = fl.y + 40 * dt
      fl.fs:ClearAllPoints(); fl.fs:SetPoint("CENTER", arena, "BOTTOMLEFT", fl.x - cam.x, fl.y - cam.y)
      fl.fs:SetAlpha(math.min(1, fl.t / 0.4)); fl.fs:Show()
      if fl.t <= 0 then fl.fs:Hide() end
    end
  end
  for _, f in ipairs(blast_f) do
    if f.life > 0 then
      f.life = f.life - dt
      local k = 1 - f.life / f.max
      f.icon:SetSize(f.r * 2 * (0.4 + 0.6 * k), f.r * 2 * (0.4 + 0.6 * k)); f.icon:SetAlpha(1 - k)
      f:ClearAllPoints(); f:SetPoint("CENTER", arena, "BOTTOMLEFT", f.x - cam.x, f.y - cam.y)
      f:SetFrameLevel(arena:GetFrameLevel() + 290)
      f:Show()
      if f.life <= 0 then f:Hide() end
    end
  end
  for i = 1, MAX_DROP do
    local d, t = world.drops[i], drop_f[i]
    if d then
      if d.kind == "item" then
        t:SetTexture("Interface\\Icons\\INV_Misc_Bag_08"); t:SetDesaturated(false); t:SetSize(26, 26)
        if d.item.rarity == "rare" then t:SetVertexColor(1, 0.85, 0.3) else t:SetVertexColor(0.5, 0.65, 1) end
      else
        t:SetTexture("Interface\\Icons\\INV_Potion_54"); t:SetDesaturated(true); t:SetSize(22, 22)
        t:SetVertexColor(d.kind == "mana" and 0.3 or 1, d.kind == "mana" and 0.5 or 0.2, d.kind == "mana" and 1 or 0.2)
      end
      t:ClearAllPoints(); t:SetPoint("CENTER", arena, "BOTTOMLEFT", d.x - cam.x, d.y - cam.y); t:Show()
    else
      t:Hide()
    end
  end
  for i, ex in ipairs(area.exits) do
    local mk = exit_marks[i]
    mk.t:ClearAllPoints(); mk.t:SetPoint("CENTER", arena, "BOTTOMLEFT", ex.x - cam.x, ex.y - cam.y)
    mk.l:ClearAllPoints(); mk.l:SetPoint("BOTTOM", mk.t, "TOP", 0, 2); mk.l:SetText(ex.label)
    local on = vis(ex.x - cam.x, ex.y - cam.y, 40, 40)
    mk.t:SetShown(on); mk.l:SetShown(on)
  end
  for i = #area.exits + 1, #exit_marks do                                  -- an area with fewer exits than the last one: hide the marks left over, or they sit on the screen where they were
    exit_marks[i].t:Hide(); exit_marks[i].l:Hide()
  end

end

local function update_hud(dt, p)
  update_minimap(dt, p)
  -- HUD
  life_orb.set(p.life / p.maxlife, math.floor(p.life) .. "/" .. p.maxlife)
  mana_orb.set(p.mana / p.maxmana, math.floor(p.mana) .. "/" .. p.maxmana)
  xp_bar:SetWidth(math.max(1, (SLOTS * 42 - 2) * p.xp / Combat.xp_for_next(p.level)))
  info_text:SetText(string.format("Level %d    Skill points %d    %d FPS", p.level, Tree.points_free(p.st), math.floor(GetFramerate())))
  zone_text:SetText(area.title .. (area.quest and (world.flags[area.quest.id] and "   Quest done" or ("   " .. area.quest.title)) or ""))
  for i = 1, SLOTS do
    local b, id = slots[i], bar[i]
    if id then b.icon:SetTexture(icon_path(id)); b.icon:SetAlpha(1) else b.icon:SetTexture(nil) end
    b.sel:SetShown(i == sel and id ~= nil)
  end
  if toast_t > 0 then
    toast_t = toast_t - dt
    toast_text:SetAlpha(math.min(1, toast_t)); toast_text:Show()
    if toast_t <= 0 then toast_text:Hide() end
  end
  if Game.paused then hint_text:SetText("Paused while the skill tree is open. Hover a skill and press 1-8 to put it on your bar. K closes it.")
  elseif Tree.points_spent(p.st) == 0 then hint_text:SetText("Left click: walk, or attack a monster with your wand (free). Press K to spend your first skill point. Drag the title bar to move the window.")
  end
  if world.over then
    over_text:SetText("You died.  Click to start again.\n(your level, skills and quest progress are kept)"); over_text:Show()
  else
    over_text:Hide()
  end
  if tree_frame:IsShown() then refresh_tree() end
end

local function tick_body(dt)
  if dt > 0.1 then dt = 0.1 end
  Game.paused = tree_frame:IsShown()
  local p = world.player
  local cap = Game.session()
  if not Game.paused then
    ns.Capture.tick(cap, dt)
    Game._fps_t = (Game._fps_t or 0) + dt
    if Game._fps_t >= 2 then Game._fps_t = 0; ns.Capture.sample_fps(cap, GetFramerate and GetFramerate() or nil) end
    if ns.Capture.combat_shot_due(cap) then Game.shot("combat") end
  end
  if world.over and not Game._died then                              -- the moment of death, with what killed you
    Game._died = true
    local awake, boss_awake = 0, false
    for _, m in ipairs(world.monsters) do
      if not m.dead and m.awake then awake = awake + 1; if m.boss then boss_awake = true end end
    end
    ns.Capture.death(cap, { level = p.level, maxlife = p.maxlife, awake = awake, boss_awake = boss_awake })
    Game.shot("death")
  elseif not world.over then
    Game._died = false
  end
  advance(dt, p)
  draw_actors(p)
  draw_world_and_events(dt, p)
  update_hud(dt, p)
end

-- An error in a frame must not stop the game, and must not be lost: it is recorded (once per kind, with a count) and shown once.
-- `Game.rethrow` (set by the tests) lets the error through, so a bug cannot hide behind this.
function Game.tick(dt)
  if Game.rethrow then return tick_body(dt) end
  local ok, err = pcall(tick_body, dt)
  if not ok then
    local s = Game.session()
    local before = #s.errors
    ns.Capture.error(s, err)
    if #s.errors > before then say("|cffff5555error|r " .. tostring(err):sub(1, 200) .. "   (/dread report has it)") end
  end
end

---------------------------------------------------------------- opening, closing, settings
Game.DEFAULT_SCALE = 1.6
function Game.set_scale(x)
  x = tonumber(x) or Game.DEFAULT_SCALE
  if x < 0.8 then x = 0.8 elseif x > 3 then x = 3 end
  DreadDB = DreadDB or {}
  DreadDB.scale = x
  if frame then frame:SetScale(x) end
  if tree_frame then tree_frame:SetScale(x) end
  return x
end

-- Which way the models face is not known until seen; this nudges it (radians), saved.
function Game.set_facing(r)
  DreadDB = DreadDB or {}
  DreadDB.facing = tonumber(r) or 0
  return DreadDB.facing
end

-- Live tuning, saved: how big the ground texture tiles (units), and how far the camera sits from each kind of scenery.
function Game.set_tile(n)
  DreadDB = DreadDB or {}
  n = tonumber(n)
  DreadDB.tile = (n and n >= 32 and n <= 2048) and n or nil
  return DreadDB.tile or "default"
end

function Game.cam_for(kind)
  return (DreadDB and DreadDB.cam and DreadDB.cam[kind]) or Zone.SCENERY[kind].cam
end

function Game.set_cam(kind, n)
  if not Zone.SCENERY[kind] then return nil, "unknown kind (tree, fallen, bush, grave, rock)" end
  n = tonumber(n)
  if not n or n < 0.3 or n > 10 then return nil, "pick a number between 0.3 and 10" end
  DreadDB = DreadDB or {}
  DreadDB.cam = DreadDB.cam or {}
  DreadDB.cam[kind] = n
  for d, f in pairs(doodad_slot) do
    if d.kind == kind then try(f.SetCamDistanceScale, f, n) end
  end
  return n
end

-- Start the character over: forget the save, and if the game is already built, replace the live world too
-- (otherwise closing the window would simply save the old character back).
function Game.reset()
  DreadDB = DreadDB or {}
  DreadDB.char, DreadDB.bar = nil, nil
  if frame then
    new_world()
    if Tree.points_spent(world.player.st) == 0 and tree_frame then refresh_tree(); tree_frame:Show() end
  end
end

-- The in-game button: the first click arms it, a second click within three seconds does it.
function Game.press_reset()
  if reset_armed then
    reset_armed = false
    reset_btn:SetText("New game")
    Game.reset()
    hint_text:SetText("New character: level 1, no skills.")
    return
  end
  reset_armed = true
  reset_btn:SetText("Sure? Click")
  C_Timer.After(3, function()
    if reset_armed then reset_armed = false; reset_btn:SetText("New game") end
  end)
end

function Game.toggle_tree()
  if tree_frame:IsShown() then tree_frame:Hide() else refresh_tree(); tree_frame:Show() end
end

function Game.toggle()
  if not frame then
    build()
    Game.set_scale(DreadDB and DreadDB.scale or Game.DEFAULT_SCALE)
    Game.set_zoom(DreadDB and DreadDB.zoom or Game.DEFAULT_ZOOM)
    new_world()
  end
  if frame:IsShown() then
    save(); frame:Hide(); tree_frame:Hide()
    if ns.Log then ns.Log.close() end                              -- the log goes with the game
  else
    if world.over then new_world(area and area.name) end
    frame:Show()
    if ns.Log then ns.Log.open_beside(frame) end                   -- and the log opens at its side
    Game.maybe_find()
    if Tree.points_spent(world.player.st) == 0 then refresh_tree(); tree_frame:Show() end
  end
end

-- /dread animtest: plays animation ids on your own model one at a time so the right ones can be picked by eye.
function Game.animtest()
  local ids = { 0, 1, 2, 4, 5, 6, 16, 17, 26, 32, 33, 34, 51, 52, 53, 54 }
  local f = CreateFrame("PlayerModel", nil, UIParent)
  f:SetSize(200, 260); f:SetPoint("CENTER", UIParent, "CENTER", 0, 100)
  try(f.SetUnit, f, "player")
  f:Show()
  for i, id in ipairs(ids) do
    C_Timer.After(i * 2.5, function()
      try(f.SetAnimation, f, id)
      say(string.format("[%d/%d] animation %d", i, #ids, id))
      if i == #ids then C_Timer.After(2.5, function() f:Hide(); say("done. Tell me which number looked like casting a spell, and which like an attack.") end) end
    end)
  end
end

-- Particle detail: 'off', 'low' (half) or 'full'. Saved. Useful if the frame rate drops in a big fight.
function Game.set_fx(level)
  local map = { off = 0, low = 0.5, full = 1 }
  DreadDB = DreadDB or {}
  if map[level] ~= nil then DreadDB.fx = map[level] end
  local v = DreadDB.fx or 1
  return v == 0 and "off" or (v == 1 and "full" or "low")
end
function Game.particles_drawn() return fx_drawn end
Game.DEFAULT_ZOOM = 1.4
function Game.set_zoom(x)
  x = tonumber(x) or Game.DEFAULT_ZOOM
  if x < 1 then x = 1 elseif x > 2.6 then x = 2.6 end
  DreadDB = DreadDB or {}
  DreadDB.zoom = x
  apply_zoom(x)
  return x
end
function Game.view() return vw, vh end
function Game.target_info()
  if target and not target.dead then return { name = target.name, x = target.x, y = target.y } end
end
function Game.set_anim_switching(on)
  DreadDB = DreadDB or {}
  if on == "on" or on == true then DreadDB.anim = true elseif on == "off" or on == false then DreadDB.anim = false end
  return DreadDB.anim ~= false
end
function Game.solid() return solid_on end
function Game.buffs_shown() return buff_shown end
function Game.solid_sizes() return solid_sizes end
function Game.set_solid(on) solid_on = on and true or false; return solid_on end
function Game.orbs() return life_orb, mana_orb end
function Game.world() return world end
function Game.camera() return cam end
function Game.area() return area end
function Game.bar() return bar, sel end

return Game
