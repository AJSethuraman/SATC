-- Drawing the first-person view with WoW's own widgets: every screen column is a thin textured strip, enemies are real 3D models
-- placed by distance, the weapon is an icon at the bottom. The maths is in Ray.lua; this file only puts things on screen.
local _, ns = ...
ns = ns or {}
local Render = {}
ns.Render = Render

Render.VW, Render.VH = 640, 360              -- the view, in screen units
Render.FOV = 2 * math.atan(0.66)             -- about 66 degrees, the classic
Render.MAXCOLS = 320
Render.SLICE = 1 / 40                        -- how much of a wall texture's width one column shows
Render.WEAPON = "Interface\\Icons\\INV_Weapon_Rifle_01"
Render.FLASH = "Interface\\Cooldown\\star4"

local function try(fn, ...) return pcall(fn, ...) end

Render.WALLS = nil                           -- wall kind -> { file, color }; the game sets this to Rules.WALLS, the test level to Level.WALLS
Render.MAXMODELS, Render.MAXSPR = 12, 48
Render.ANIM = { STAND = 0, DEATH = 1, RUN = 5, ATTACK = 16 }

-- Build the window: a frame with the view inside it, the column pool, the model pool, the weapon and the text. Returns the state.
function Render.build(name)
  local R = { n = 160, cols = {}, models = {}, wall_ok = {}, shown_models = 0 }
  local f = CreateFrame("Frame", name or "GauntletFrame", UIParent, "BackdropTemplate")
  f:SetSize(Render.VW + 16, Render.VH + 64)
  f:SetPoint("CENTER")
  f:SetFrameStrata("DIALOG")
  if f.SetBackdrop then f:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 2 }) end
  if f.SetBackdropColor then f:SetBackdropColor(0, 0, 0, 0.95) end
  if f.SetBackdropBorderColor then f:SetBackdropBorderColor(0.6, 0.1, 0.1, 1) end
  f:SetMovable(true); f:EnableMouse(true); f:EnableKeyboard(true)
  R.frame = f
  local title = f:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  title:SetPoint("TOPLEFT", 10, -6)
  R.title = title

  local v = CreateFrame("Frame", nil, f)
  v:SetSize(Render.VW, Render.VH)
  v:SetPoint("TOPLEFT", f, "TOPLEFT", 8, -26)
  R.view = v
  -- ceiling and floor in bands, dark at the far edge of the room and lighter near you, so the room has depth
  R.bands = {}
  local NB = 8
  for i = 1, NB do
    local k = (i - 1) / (NB - 1)                    -- 0 at the horizon, 1 at the top or bottom edge
    local c = v:CreateTexture(nil, "BACKGROUND")
    c:SetPoint("TOPLEFT", v, "TOPLEFT", 0, -(i - 1) * Render.VH / 2 / NB); c:SetSize(Render.VW, Render.VH / 2 / NB + 1)
    c:SetColorTexture(0.05 + 0.07 * (1 - k), 0.05 + 0.06 * (1 - k), 0.08 + 0.08 * (1 - k), 1)
    local f = v:CreateTexture(nil, "BACKGROUND")
    f:SetPoint("BOTTOMLEFT", v, "BOTTOMLEFT", 0, (i - 1) * Render.VH / 2 / NB); f:SetSize(Render.VW, Render.VH / 2 / NB + 1)
    f:SetColorTexture(0.07 + 0.16 * k, 0.06 + 0.13 * k, 0.05 + 0.10 * k, 1)
    R.bands[#R.bands + 1] = c; R.bands[#R.bands + 1] = f
  end
  for i = 1, Render.MAXCOLS do
    local t = v:CreateTexture(nil, "ARTWORK")
    t:Hide()
    R.cols[i] = { tex = t, id = nil }
  end
  R.hud = f:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
  R.hud:SetPoint("BOTTOMLEFT", 10, 8)
  R.cross = v:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
  R.cross:SetPoint("CENTER"); R.cross:SetText("+")
  -- the weapon is drawn as a first-person gun from plain coloured blocks (a sleeve, a grip, a barrel), held low and to the right
  R.weapon = CreateFrame("Frame", nil, v)
  R.weapon:SetSize(160, 170); R.weapon:SetPoint("BOTTOM", v, "BOTTOM", 70, 0)
  R.parts = {}
  for i = 1, 9 do
    local t = R.weapon:CreateTexture(nil, "OVERLAY")
    t:Hide(); R.parts[i] = t
  end
  R.flash = v:CreateTexture(nil, "OVERLAY")
  R.flash:SetSize(110, 110); R.flash:SetPoint("BOTTOM", v, "BOTTOM", 70, 150); R.flash:SetBlendMode("ADD")
  try(R.flash.SetTexture, R.flash, Render.FLASH)
  R.flash:Hide()
  R.msg = v:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
  R.msg:SetPoint("TOP", v, "TOP", 0, -20)
  return R
end

function Render.set_columns(R, n)
  R.n = math.max(1, math.min(Render.MAXCOLS, n))
  for i = 1, Render.MAXCOLS do
    local c = R.cols[i]
    if i > R.n then c.tex:Hide(); c.id = nil end
  end
end

-- Give a wall kind's texture to a column, or its plain colour if the texture would not take. Done only when the column's kind changes.
local function dress(R, c, id)
  local walls = Render.WALLS or ns.Level.WALLS
  local w = walls[id] or walls[1]
  c.id = id
  if R.wall_ok[id] ~= false then
    local ok = try(c.tex.SetTexture, c.tex, w.file)
    if not ok then R.wall_ok[id] = false end
  end
  if R.wall_ok[id] == false then c.tex:SetColorTexture(w.color[1], w.color[2], w.color[3], 1) end
end

-- Draw the walls for a camera pose. cols: the output of Ray.columns for R.n columns.
function Render.walls(R, cols)
  local colw, vh = Render.VW / R.n, Render.VH
  for i = 1, R.n do
    local k, c = cols[i], R.cols[i]
    if k.id ~= 0 then
      if c.id ~= k.id then dress(R, c, k.id) end
      local h = math.min(vh * 1.2, vh / math.max(k.dist, 0.05))
      c.tex:ClearAllPoints()
      c.tex:SetPoint("BOTTOMLEFT", R.view, "BOTTOMLEFT", (i - 1) * colw, (vh - h) / 2)
      c.tex:SetSize(colw + 0.5, h)
      if R.wall_ok[k.id] ~= false then
        local u0 = math.min(k.u, 1 - Render.SLICE)
        c.tex:SetTexCoord(u0, u0 + Render.SLICE, 0, 1)
      end
      local shade = math.max(0.15, math.min(1, 1.15 - k.dist * 0.09)) * (k.side == 1 and 0.8 or 1)
      c.tex:SetVertexColor(shade, shade, shade)
      c.tex:Show()
    else
      c.tex:Hide()
    end
  end
end

-- Make the model frames for the enemies (once). Each enemy has either a creature id or a bare model file.
function Render.make_models(R, enemies)
  for i, e in ipairs(enemies) do
    local m = R.models[i]
    if not m then
      m = CreateFrame("PlayerModel", nil, R.view)
      m:Hide()
      R.models[i] = m
      if e.cid then m.ok = try(m.SetCreature, m, e.cid) else m.ok = try(m.SetModel, m, e.model) end
      m.enemy = e
    end
  end
end

-- Put each enemy where the camera sees it, sized by how far away it is, in front of nearer walls but not behind a wall that hides it.
function Render.enemies(R, x, y, ang, cols, enemies)
  local colw, vh = Render.VW / R.n, Render.VH
  local shown = 0
  for i, e in ipairs(enemies) do
    local m = R.models[i]
    if m then
      local col, depth
      if not e.dead then col, depth = ns.Ray.sprite(x, y, ang, Render.FOV, R.n, e.x, e.y) end
      local hide = true
      if col and depth < 24 then
        local ci = math.max(1, math.min(R.n, math.floor(col + 0.5)))
        if cols[ci] and (cols[ci].id == 0 or cols[ci].dist > depth - 0.3) then hide = false end     -- a wall in front of its middle hides it
      end
      if hide then
        m:Hide()
      else
        local size = vh / depth * 0.85
        m:SetSize(size * 0.8, size)
        m:ClearAllPoints()
        m:SetPoint("BOTTOM", R.view, "BOTTOMLEFT", (col - 0.5) * colw, vh / 2 - vh / (2 * depth))
        m:SetFrameLevel(R.view:GetFrameLevel() + 20 + math.max(0, 200 - math.floor(depth * 8)))        -- nearer ones in front
        m:SetAlpha(e.flash and 0.5 or 1)
        m:Show()
        shown = shown + 1
      end
    end
  end
  R.shown_models = shown
end

-- The weapon sways a little as you walk and kicks when it fires; the flash shows for a moment.
function Render.weapon(R, walking_t, kick)
  local bob = math.sin(walking_t * 8) * 4
  R.weapon:ClearAllPoints()
  R.weapon:SetPoint("BOTTOM", R.view, "BOTTOM", 70 + math.sin(walking_t * 4) * 6, bob - (kick or 0) * 14)
  if (kick or 0) > 0.5 then R.flash:Show() else R.flash:Hide() end
end

---------------------------------------------------------------- the game's enemies and things

-- Is this spot (given its column and depth) in view and not hidden behind a nearer wall?
local function visible(R, cols, col, depth)
  if not col or depth >= 24 then return false end
  local ci = math.max(1, math.min(R.n, math.floor(col + 0.5)))
  local k = cols[ci]
  return k ~= nil and (k.id == 0 or k.dist > depth - 0.3)
end

-- The nearest few enemies get a model frame each and keep it while they stay among the nearest, so a model is loaded once and not every frame.
function Render.game_models(R, x, y, ang, cols, enemies, now)
  R.pool = R.pool or {}
  for i = 1, Render.MAXMODELS do
    if not R.pool[i] then
      local m = CreateFrame("PlayerModel", nil, R.view)
      m:Hide()
      m.owner, m.anim = false, false                          -- false, not nil: a field that is not there must read as "no owner"
      R.pool[i] = m
    end
  end
  local cand = {}
  for _, e in ipairs(enemies) do
    if not (e.dead and now - (e.died or 0) > 4) then
      local col, depth = ns.Ray.sprite(x, y, ang, Render.FOV, R.n, e.x, e.y)
      if visible(R, cols, col, depth) then cand[#cand + 1] = { e = e, col = col, depth = depth } end
    end
  end
  table.sort(cand, function(a, b) return a.depth < b.depth end)
  local want, have = {}, {}
  for i = 1, math.min(Render.MAXMODELS, #cand) do want[cand[i].e] = cand[i] end
  for i = 1, Render.MAXMODELS do
    local m = R.pool[i]
    if m.owner and not want[m.owner] then m.owner = false; m:Hide() end
    if m.owner then have[m.owner] = m end
  end
  for i = 1, math.min(Render.MAXMODELS, #cand) do
    local e = cand[i].e
    if not have[e] then
      for j = 1, Render.MAXMODELS do
        local m = R.pool[j]
        if not m.owner then
          m.owner, m.anim = e, false
          m.ok = try(m.SetCreature, m, e.def.cid)
          have[e] = m
          break
        end
      end
    end
  end
  local colw, vh = Render.VW / R.n, Render.VH
  local shown = 0
  for i = 1, Render.MAXMODELS do
    local m = R.pool[i]
    local c = m.owner and want[m.owner]
    if c then
      local e = c.e
      local size = vh / c.depth * 0.85 * (e.def.scale or 1)
      m:SetSize(size * 0.8, size)
      m:ClearAllPoints()
      m:SetPoint("BOTTOM", R.view, "BOTTOMLEFT", (c.col - 0.5) * colw, vh / 2 - vh / (2 * c.depth))
      m:SetFrameLevel(R.view:GetFrameLevel() + 20 + math.max(0, 200 - math.floor(c.depth * 8)))
      local alpha = e.flash and e.flash > 0 and 0.5 or 1
      if e.dead then alpha = math.max(0, math.min(1, (4 - (now - (e.died or 0))) / 2)) end
      m:SetAlpha(alpha)
      local want_anim = e.dead and Render.ANIM.DEATH or ((e.windup or (e.cool or 0) > (e.def.cool or 1) - 0.3 and e.state == "chase") and Render.ANIM.ATTACK)
                        or (e.moving and Render.ANIM.RUN) or Render.ANIM.STAND
      if m.anim ~= want_anim then m.anim = want_anim; try(m.SetAnimation, m, want_anim) end
      m:Show()
      shown = shown + 1
    end
  end
  R.shown_models = shown
end

-- Gun shapes: { x, y, width, height, red, green, blue } in a 160 x 170 box, from its bottom left. Drawn back to front.
local SLEEVE, SKIN, STEEL, DARK, WOOD, BRASS, OLIVE = { 0.35, 0.22, 0.12 }, { 0.80, 0.62, 0.48 }, { 0.50, 0.52, 0.56 }, { 0.22, 0.23, 0.26 }, { 0.38, 0.22, 0.10 }, { 0.78, 0.60, 0.20 }, { 0.30, 0.36, 0.20 }
local function R7(x, y, w, h, c) return { x, y, w, h, c[1], c[2], c[3] } end
Render.GUNS = {
  INV_Weapon_Rifle_01 = { R7(50, 0, 80, 56, SLEEVE), R7(62, 44, 40, 36, SKIN), R7(66, 56, 30, 40, WOOD), R7(56, 90, 50, 26, STEEL), R7(68, 112, 26, 54, DARK), R7(76, 160, 10, 8, STEEL) },
  INV_Weapon_Rifle_06 = { R7(44, 0, 92, 56, SLEEVE), R7(56, 44, 44, 34, SKIN), R7(60, 60, 36, 36, WOOD), R7(52, 88, 54, 24, BRASS), R7(60, 110, 40, 44, DARK), R7(46, 150, 68, 16, STEEL) },
  INV_Weapon_Rifle_04 = { R7(50, 0, 84, 56, SLEEVE), R7(64, 44, 38, 34, SKIN), R7(66, 58, 30, 38, WOOD), R7(52, 92, 56, 22, STEEL), R7(34, 80, 30, 32, BRASS), R7(70, 112, 18, 54, DARK), R7(74, 160, 10, 8, BRASS) },
  INV_Misc_Bomb_02 = { R7(40, 0, 100, 56, SLEEVE), R7(52, 44, 48, 34, SKIN), R7(34, 70, 92, 80, OLIVE), R7(40, 150, 80, 16, DARK), R7(70, 78, 20, 16, STEEL), R7(56, 90, 12, 50, DARK) },
}

-- The weapon in your hands: draw its shape (the icon name picks it, and is what the game asks for).
function Render.set_weapon(R, icon)
  if R.weapon_icon == icon then return end
  R.weapon_icon = icon
  local shape = Render.GUNS[icon] or Render.GUNS.INV_Weapon_Rifle_01
  for i, t in ipairs(R.parts) do
    local p = shape[i]
    if p then
      t:ClearAllPoints(); t:SetPoint("BOTTOMLEFT", R.weapon, "BOTTOMLEFT", p[1], p[2]); t:SetSize(p[3], p[4])
      t:SetColorTexture(p[5], p[6], p[7], 1); t:Show()
    else
      t:Hide()
    end
  end
end

-- Flat things standing in the level (pickups, fireballs, the exit): icons sized by distance. list: { x, y, icon, size, lift, tint }.
function Render.sprites(R, x, y, ang, cols, list)
  R.spr = R.spr or {}
  local cand = {}
  for _, s in ipairs(list) do
    local col, depth = ns.Ray.sprite(x, y, ang, Render.FOV, R.n, s.x, s.y)
    if visible(R, cols, col, depth) then cand[#cand + 1] = { s = s, col = col, depth = depth } end
  end
  table.sort(cand, function(a, b) return a.depth > b.depth end)            -- far ones first, so near ones draw over them
  local colw, vh = Render.VW / R.n, Render.VH
  local used = 0
  for i = 1, math.min(Render.MAXSPR, #cand) do
    local c = cand[i]
    local t = R.spr[i]
    if not t then
      t = R.view:CreateTexture(nil, "OVERLAY")
      R.spr[i] = t
    end
    if t.icon ~= c.s.icon then t.icon = c.s.icon; try(t.SetTexture, t, "Interface\\Icons\\" .. c.s.icon) end
    local size = math.max(6, vh / c.depth * (c.s.size or 0.3))
    t:SetSize(size, size)
    t:ClearAllPoints()
    t:SetPoint("BOTTOM", R.view, "BOTTOMLEFT", (c.col - 0.5) * colw, vh / 2 - vh / (2 * c.depth) + (c.s.lift or 0) * vh / c.depth)
    local tint = c.s.tint
    if tint then t:SetVertexColor(tint[1], tint[2], tint[3]) else t:SetVertexColor(1, 1, 1) end
    t:Show()
    used = i
  end
  for i = used + 1, #R.spr do R.spr[i]:Hide() end
  R.shown_sprites = used
end

return Render
