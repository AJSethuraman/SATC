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

-- Build the window: a frame with the view inside it, the column pool, the model pool, the weapon and the text. Returns the state.
function Render.build()
  local R = { n = 160, cols = {}, models = {}, wall_ok = {}, shown_models = 0 }
  local f = CreateFrame("Frame", "GauntletFrame", UIParent, "BackdropTemplate")
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
  R.ceiling = v:CreateTexture(nil, "BACKGROUND")
  R.ceiling:SetPoint("TOPLEFT"); R.ceiling:SetSize(Render.VW, Render.VH / 2); R.ceiling:SetColorTexture(0.1, 0.09, 0.12, 1)
  R.floor = v:CreateTexture(nil, "BACKGROUND")
  R.floor:SetPoint("BOTTOMLEFT"); R.floor:SetSize(Render.VW, Render.VH / 2); R.floor:SetColorTexture(0.2, 0.17, 0.13, 1)
  for i = 1, Render.MAXCOLS do
    local t = v:CreateTexture(nil, "ARTWORK")
    t:Hide()
    R.cols[i] = { tex = t, id = nil }
  end
  R.hud = f:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
  R.hud:SetPoint("BOTTOMLEFT", 10, 8)
  R.cross = v:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
  R.cross:SetPoint("CENTER"); R.cross:SetText("+")
  R.weapon = v:CreateTexture(nil, "OVERLAY")
  R.weapon:SetSize(170, 170); R.weapon:SetPoint("BOTTOM", v, "BOTTOM", 0, 0)
  try(R.weapon.SetTexture, R.weapon, Render.WEAPON)
  R.flash = v:CreateTexture(nil, "OVERLAY")
  R.flash:SetSize(90, 90); R.flash:SetPoint("BOTTOM", v, "BOTTOM", 0, 120); R.flash:SetBlendMode("ADD")
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
  local w = ns.Level.WALLS[id] or ns.Level.WALLS[1]
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
  R.weapon:SetPoint("BOTTOM", R.view, "BOTTOM", math.sin(walking_t * 4) * 6, bob - (kick or 0) * 14)
  if (kick or 0) > 0.5 then R.flash:Show() else R.flash:Hide() end
end

return Render
