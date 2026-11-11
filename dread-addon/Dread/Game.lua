-- The playable window: draws the fight from Combat.lua with WoW's own art and takes the mouse and keys.
-- Left click walks. Right click casts the selected spell at the cursor. 1-9 select a spell. K opens the skill tree.
-- Everything about the rules lives in Combat.lua / Tree.lua; this file only draws and listens.
local ADDON, ns = ...
local Combat, Tree, Skills = ns.Combat, ns.Tree, ns.Skills

local Game = {}
ns.Game = Game

local AW, AH = 640, 400            -- the arena, in the same units Combat.lua uses
local HUD_H = 78
local MAX_MONSTER_FRAMES = 16

-- Spell icons: guesses from memory of WoW's icon names, to be fixed from a screenshot if any draw as a green square.
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
  conductor="Spell_Nature_StormReach",
}
local function icon_path(id) return "Interface\\Icons\\" .. (ICONS[id] or "INV_Misc_QuestionMark") end

local COLORS = { fire = {1, 0.45, 0.1}, cold = {0.45, 0.75, 1}, lightning = {0.75, 0.6, 1} }

-- The monsters of the moor. Models are WoW creature ids that drew in Test 3; names and numbers are placeholders.
local BESTIARY = {
  { name = "Moor Wolf",  cid = 299,  life = 20, speed = 75, dmg = { 2, 4 }, xp = 8 },
  { name = "Tusker",     cid = 3098, life = 34, speed = 52, dmg = { 3, 6 }, xp = 12 },
  { name = "Mudfin",     cid = 46,   life = 26, speed = 62, dmg = { 2, 5 }, xp = 11, resist = { cold = 50 } },
  { name = "Brute",      cid = 6,    life = 44, speed = 55, dmg = { 3, 7 }, xp = 16 },
  { name = "Gloom Imp",  cid = 3101, life = 22, speed = 78, dmg = { 2, 5 }, xp = 15, resist = { fire = 75 } },
}

local world, wave, selected = nil, 0, nil
local frame, arena, hud, tree_frame
local mframes, projs, floaters, flashes = {}, {}, {}, {}
local player_model, player_bar
local life_bar, mana_bar, xp_bar, info_text, hint_text, over_text
local slots = {}
Game.tree_buttons = {}

local function say(msg) print("|cffff5555Dread|r " .. msg) end

---------------------------------------------------------------- the save
local function save()
  if not world then return end
  DreadDB = DreadDB or {}
  DreadDB.char = Combat.snapshot(world)
end

local function new_world()
  local seed = (time and time() or 1) % 2147483647
  world = Combat.new({ w = AW, h = AH, seed = seed })
  if DreadDB and DreadDB.char then Combat.restore(world, DreadDB.char) end
  wave = 0
  selected = nil
end

---------------------------------------------------------------- monsters
local function spawn_wave()
  wave = wave + 1
  local n = math.min(14, 2 + wave * 2)
  for i = 1, n do
    local t = BESTIARY[1 + math.floor(world.rng() * #BESTIARY)]
    local res = { fire = 0, cold = 0, lightning = 0 }
    for k, v in pairs(t.resist or {}) do res[k] = v end
    local grow = 1 + (wave - 1) * 0.15           -- later waves hit harder and last longer
    local m = Combat.add_monster(world, {
      x = 40 + world.rng() * (AW - 80), y = AH - 20 - world.rng() * 60, life = math.floor(t.life * grow),
      speed = t.speed, dmg = { t.dmg[1] * grow, t.dmg[2] * grow }, xp = t.xp, resist = res, radius = 14,
    })
    m.cid, m.name = t.cid, t.name
  end
end

---------------------------------------------------------------- drawing helpers
local function tex(parent, layer) local t = parent:CreateTexture(nil, layer or "ARTWORK"); return t end
local function fstr(parent, size) local f = parent:CreateFontString(nil, "OVERLAY", size or "GameFontNormal"); return f end

local function arena_xy()
  local cx, cy = GetCursorPosition()
  local s = frame:GetEffectiveScale()
  return cx / s - arena:GetLeft(), cy / s - arena:GetBottom()
end

local function learned_spells()
  local list = {}
  for _, sk in ipairs(Skills) do
    if Tree.points_in(world.player.st, sk.id) > 0 and Combat.SHAPES[sk.id] then list[#list + 1] = sk.id end
  end
  return list
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
  if not Combat.SHAPES[id] and sk.kind ~= "passive" and sk.kind ~= "mastery" then
    GameTooltip:AddLine("Not castable yet in this build", 1, 0.3, 0.3)
  end
  if sk.dmg then
    local lo, hi = Tree.damage(st, id)
    if lo then GameTooltip:AddLine(string.format("Damage now: %d - %d", math.floor(lo), math.floor(hi)), 0.6, 1, 0.6) end
    local n = math.min(Skills.MAX_POINTS, pts + 1)
    local s2 = { points = {}, level = 99, quest_points = 0 }
    for k, v in pairs(st.points) do s2.points[k] = v end
    s2.points[id] = n
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
  tree_frame.title:SetText(string.format("Skills   points to spend: %d   (click to add one)", Tree.points_free(st)))
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
  tree_frame:SetMovable(true); tree_frame:EnableMouse(true)
  tree_frame:RegisterForDrag("LeftButton")
  tree_frame:SetScript("OnDragStart", tree_frame.StartMoving)
  tree_frame:SetScript("OnDragStop", tree_frame.StopMovingOrSizing)
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
    local x = 20 + col_of[sk.tree] * 200 + (seen[key] - 1) * 50
    local y = -34 - (gates[sk.req] - 1) * 56
    local b = CreateFrame("Button", nil, tree_frame)
    b:SetSize(42, 42)
    b:SetPoint("TOPLEFT", tree_frame, "TOPLEFT", x, y)
    b.icon = tex(b); b.icon:SetAllPoints(b); b.icon:SetTexture(icon_path(sk.id))
    b.count = fstr(b, "GameFontHighlight"); b.count:SetPoint("BOTTOMRIGHT", b, "BOTTOMRIGHT", -2, 2)
    b:SetScript("OnClick", function()
      local ok, why = Tree.allocate(world.player.st, sk.id)
      if not ok then say(sk.name .. ": " .. tostring(why)) else save() end
      refresh_tree()
    end)
    b:SetScript("OnEnter", function(self) tooltip(self, sk.id) end)
    b:SetScript("OnLeave", function() GameTooltip:Hide() end)
    Game.tree_buttons[sk.id] = b
  end
  for _, sk in ipairs(Skills) do                     -- arrows to prerequisites, where the client can draw lines
    for _, p in ipairs(sk.prereqs) do
      pcall(function()
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

---------------------------------------------------------------- the main window
local function build()
  frame = CreateFrame("Frame", "DreadGameFrame", UIParent, "BackdropTemplate")
  frame:SetSize(AW + 20, AH + HUD_H + 24)
  frame:SetPoint("CENTER")
  frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
  frame:SetBackdropColor(0, 0, 0, 0.95)
  frame:SetBackdropBorderColor(0.6, 0.1, 0.1, 1)
  frame:SetMovable(true); frame:EnableMouse(true); frame:EnableKeyboard(true)
  frame:RegisterForDrag("RightButton")
  frame:SetScript("OnDragStart", frame.StartMoving)
  frame:SetScript("OnDragStop", frame.StopMovingOrSizing)

  arena = CreateFrame("Frame", nil, frame)
  arena:SetSize(AW, AH)
  arena:SetPoint("TOPLEFT", frame, "TOPLEFT", 10, -10)
  arena:SetClipsChildren(true)
  local ground = tex(arena, "BACKGROUND")
  ground:SetAllPoints(arena)
  ground:SetTexture("Interface\\FrameGeneral\\UI-Background-Rock", "REPEAT", "REPEAT")
  ground:SetHorizTile(true); ground:SetVertTile(true)
  ground:SetVertexColor(0.55, 0.62, 0.38)             -- a dull moor green until proper terrain art is found

  player_model = CreateFrame("PlayerModel", nil, arena)
  player_model:SetSize(70, 90)
  player_model:SetUnit("player")
  player_model:SetFrameLevel(arena:GetFrameLevel() + 5)

  for i = 1, MAX_MONSTER_FRAMES do
    local m = CreateFrame("PlayerModel", nil, arena)
    m:SetSize(64, 80)
    m:Hide()
    m.fallback = tex(m, "ARTWORK"); m.fallback:SetAllPoints(m); m.fallback:SetColorTexture(0.7, 0.2, 0.2, 0.8); m.fallback:Hide()
    m.bar = tex(m, "OVERLAY"); m.bar:SetSize(40, 4); m.bar:SetPoint("BOTTOM", m, "TOP", 0, -2); m.bar:SetColorTexture(0.9, 0.1, 0.1, 1)
    mframes[i] = m
  end
  for i = 1, 24 do
    local t = tex(arena, "OVERLAY"); t:SetSize(26, 26); t:SetBlendMode("ADD"); t:Hide(); projs[i] = t
  end
  for i = 1, 24 do
    local f = fstr(arena, "GameFontHighlight"); f:Hide(); floaters[i] = { fs = f, t = 0 }
  end
  for i = 1, 12 do
    local t = tex(arena, "OVERLAY"); t:SetBlendMode("ADD"); t:Hide(); flashes[i] = { t = t, life = 0 }
  end

  hud = CreateFrame("Frame", nil, frame)
  hud:SetSize(AW, HUD_H)
  hud:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 10, 8)
  life_bar = tex(hud); life_bar:SetPoint("TOPLEFT", hud, "TOPLEFT", 0, 0); life_bar:SetSize(250, 14); life_bar:SetColorTexture(0.8, 0.1, 0.1, 1)
  mana_bar = tex(hud); mana_bar:SetPoint("TOPLEFT", hud, "TOPLEFT", 0, -18); mana_bar:SetSize(250, 14); mana_bar:SetColorTexture(0.15, 0.3, 0.9, 1)
  xp_bar = tex(hud); xp_bar:SetPoint("TOPLEFT", hud, "TOPLEFT", 0, -36); xp_bar:SetSize(250, 5); xp_bar:SetColorTexture(0.9, 0.8, 0.2, 1)
  info_text = fstr(hud, "GameFontHighlight"); info_text:SetPoint("TOPLEFT", hud, "TOPLEFT", 0, -46)
  hint_text = fstr(hud, "GameFontNormalSmall"); hint_text:SetPoint("TOPLEFT", hud, "TOPLEFT", 0, -62)
  for i = 1, 9 do
    local b = CreateFrame("Button", nil, hud)
    b:SetSize(40, 40)
    b:SetPoint("TOPLEFT", hud, "TOPLEFT", 270 + (i - 1) * 42, 0)
    b.icon = tex(b); b.icon:SetAllPoints(b)
    b.key = fstr(b, "GameFontHighlightSmall"); b.key:SetPoint("TOPLEFT", 2, -2); b.key:SetText(tostring(i))
    b.sel = tex(b, "OVERLAY"); b.sel:SetAllPoints(b); b.sel:SetColorTexture(1, 1, 1, 0.25); b.sel:Hide()
    b:SetScript("OnClick", function() local l = learned_spells(); if l[i] then selected = l[i] end end)
    b:Hide()
    slots[i] = b
  end
  local sk = CreateFrame("Button", nil, hud, "UIPanelButtonTemplate")
  sk:SetSize(80, 22); sk:SetPoint("TOPLEFT", hud, "TOPLEFT", 270 + 9 * 42 + 6, -9); sk:SetText("Skills (K)")
  sk:SetScript("OnClick", function() Game.toggle_tree() end)
  over_text = fstr(arena, "GameFontNormalLarge")
  over_text:SetPoint("CENTER", arena, "CENTER", 0, 0)
  over_text:Hide()

  frame:SetScript("OnMouseDown", function(_, button)
    if world.over then
      new_world(); return
    end
    local x, y = arena_xy()
    if x < 0 or y < 0 or x > AW or y > AH then return end
    if button == "LeftButton" then
      Combat.move_to(world, x, y)
    elseif button == "RightButton" and selected then
      local ok, why = Combat.cast(world, selected, x, y)
      if not ok then hint_text:SetText(Skills.byId[selected].name .. ": " .. tostring(why)) end
    end
  end)
  frame:SetScript("OnKeyDown", function(self, key)
    local handled = false
    local n = tonumber(key)
    if n and n >= 1 and n <= 9 then
      local l = learned_spells()
      if l[n] then selected = l[n]; handled = true end
    elseif key == "K" then
      Game.toggle_tree(); handled = true
    end
    self:SetPropagateKeyboardInput(not handled)
  end)
  frame:SetScript("OnUpdate", function(_, dt) Game.tick(dt) end)
  build_tree()
  frame:Hide()
end

local function place(f, x, y, w, h) f:ClearAllPoints(); f:SetPoint("BOTTOM", arena, "BOTTOMLEFT", x, y - h * 0.15) end

function Game.tick(dt)
  if dt > 0.1 then dt = 0.1 end
  -- Nothing moves while you are choosing skills, or before you have a spell to fight with.
  Game.paused = tree_frame:IsShown() or #learned_spells() == 0
  if not world.over and not Game.paused then
    Combat.step(world, dt)
    if Combat.alive_monsters(world) == 0 then spawn_wave() end
  end
  local p = world.player
  -- player
  place(player_model, p.x, p.y, 70, 90)
  player_model:SetFrameLevel(arena:GetFrameLevel() + 5 + math.floor((AH - p.y) / 4))
  -- monsters
  local idx = 0
  for _, m in ipairs(world.monsters) do
    local show = (not m.dead) or (world.time - (m.died_at or 0) < 1.0)
    if show and idx < MAX_MONSTER_FRAMES then
      idx = idx + 1
      local f = mframes[idx]
      if f.cid ~= m.cid then
        local ok = pcall(f.SetCreature, f, m.cid)       -- if the client refuses a model, show a plain square instead
        f.fallback:SetShown(not ok)
        f.cid = m.cid
      end
      place(f, m.x, m.y, 64, 80)
      f:SetFrameLevel(arena:GetFrameLevel() + 5 + math.floor((AH - m.y) / 4))
      f:SetAlpha(m.dead and 0.35 or ((m.freeze > 0) and 0.6 or 1))
      f.bar:SetWidth(math.max(1, 40 * math.max(0, m.life) / m.maxlife))
      f.bar:SetShown(not m.dead)
      f:Show()
    end
  end
  for i = idx + 1, MAX_MONSTER_FRAMES do mframes[i]:Hide(); mframes[i].cid = nil end
  -- projectiles
  for i = 1, #projs do
    local pr, t = world.projectiles[i], projs[i]
    if pr then
      local c = COLORS[Skills.byId[pr.id].element]
      t:SetTexture(icon_path(pr.id)); t:SetVertexColor(c[1], c[2], c[3])
      t:ClearAllPoints(); t:SetPoint("CENTER", arena, "BOTTOMLEFT", pr.x, pr.y); t:Show()
    else
      t:Hide()
    end
  end
  -- events: damage numbers and blasts
  for _, e in ipairs(Combat.drain(world)) do
    if e.k == "hit" and e.dmg > 0 then
      for _, fl in ipairs(floaters) do
        if fl.t <= 0 then
          fl.t, fl.x, fl.y = 0.8, e.x, e.y + 30
          fl.fs:SetText(tostring(math.floor(e.dmg + 0.5)))
          local c = COLORS[Skills.byId[e.id].element]; fl.fs:SetTextColor(c[1], c[2], c[3])
          break
        end
      end
    elseif e.k == "blast" then
      for _, fx in ipairs(flashes) do
        if fx.life <= 0 then
          fx.life, fx.max, fx.x, fx.y, fx.r, fx.id = 0.35, 0.35, e.x, e.y, e.r, e.id
          fx.t:SetTexture(icon_path(e.id))
          local c = COLORS[Skills.byId[e.id].element]; fx.t:SetVertexColor(c[1], c[2], c[3])
          break
        end
      end
    elseif e.k == "level" then
      hint_text:SetText("Level " .. e.level .. "!  Press K to spend your new skill point.")
      save()
    elseif e.k == "kill" then
      save()
    end
  end
  for _, fl in ipairs(floaters) do
    if fl.t > 0 then
      fl.t = fl.t - dt; fl.y = fl.y + 40 * dt
      fl.fs:ClearAllPoints(); fl.fs:SetPoint("CENTER", arena, "BOTTOMLEFT", fl.x, fl.y)
      fl.fs:SetAlpha(math.min(1, fl.t / 0.4)); fl.fs:Show()
      if fl.t <= 0 then fl.fs:Hide() end
    end
  end
  for _, fx in ipairs(flashes) do
    if fx.life > 0 then
      fx.life = fx.life - dt
      local k = 1 - fx.life / fx.max
      fx.t:SetSize(fx.r * 2 * (0.4 + 0.6 * k), fx.r * 2 * (0.4 + 0.6 * k))
      fx.t:ClearAllPoints(); fx.t:SetPoint("CENTER", arena, "BOTTOMLEFT", fx.x, fx.y)
      fx.t:SetAlpha(1 - k); fx.t:Show()
      if fx.life <= 0 then fx.t:Hide() end
    end
  end
  -- HUD
  life_bar:SetWidth(math.max(1, 250 * p.life / p.maxlife))
  mana_bar:SetWidth(math.max(1, 250 * p.mana / p.maxmana))
  xp_bar:SetWidth(math.max(1, 250 * p.xp / Combat.xp_for_next(p.level)))
  info_text:SetText(string.format("Life %d/%d   Mana %d/%d   Level %d   Points %d   Wave %d   %d FPS",
    math.floor(p.life), p.maxlife, math.floor(p.mana), p.maxmana, p.level, Tree.points_free(p.st), wave, math.floor(GetFramerate())))
  local list = learned_spells()
  if selected == nil or Tree.points_in(p.st, selected) < 1 then selected = list[1] end
  for i = 1, 9 do
    local b, id = slots[i], list[i]
    if id then
      b.icon:SetTexture(icon_path(id)); b.sel:SetShown(id == selected); b:Show()
    else
      b:Hide()
    end
  end
  if #list == 0 then hint_text:SetText("No spells yet. Press K (or the Skills button) and spend your skill point.")
  elseif Game.paused then hint_text:SetText("Paused while the skill tree is open. Press K or Close to fight.")
  elseif world.over then hint_text:SetText("")
  end
  if world.over then
    over_text:SetText("You died.  Click to start again.\n(your level and skill points are kept)")
    over_text:Show()
  else
    over_text:Hide()
  end
  if tree_frame:IsShown() then refresh_tree() end
end

-- The window is built at 640 x 400 and scaled up; the mouse maths already accounts for scale.
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

function Game.toggle_tree()
  if tree_frame:IsShown() then tree_frame:Hide() else refresh_tree(); tree_frame:Show() end
end

function Game.toggle()
  if not frame then build(); Game.set_scale(DreadDB and DreadDB.scale or Game.DEFAULT_SCALE) end
  if frame:IsShown() then
    save(); frame:Hide(); tree_frame:Hide()
  else
    if not world or world.over then new_world() end
    frame:Show()
    if #learned_spells() == 0 then
      refresh_tree(); tree_frame:Show()
    end
  end
end

function Game.world() return world end
function Game.wave() return wave end

return Game
