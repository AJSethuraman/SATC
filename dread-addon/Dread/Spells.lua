-- /dread spells: a page of real WoW spell-effect models (by fileDataID), looping, with numbers, so you can say which ones look right.
local _, ns = ...
local Spells = {}
ns.Spells = Spells

local PER, COLS = 12, 4
local frame, cells, title, current = nil, {}, nil, 1

function Spells.pages()
  local n = #ns.SpellData
  return math.max(1, math.ceil(n / PER))
end

-- the entries on a page, each with its overall number; the page number is clamped into range
function Spells.page(p)
  p = math.max(1, math.min(Spells.pages(), math.floor(tonumber(p) or 1)))
  local out = {}
  for i = (p - 1) * PER + 1, math.min(#ns.SpellData, p * PER) do
    out[#out + 1] = { n = i, id = ns.SpellData[i][1], name = ns.SpellData[i][2] }
  end
  return out, p
end

local function build()
  frame = CreateFrame("Frame", "DreadSpellsFrame", UIParent, "BackdropTemplate")
  frame:SetSize(620, 470)
  frame:SetPoint("CENTER")
  frame:SetFrameStrata("DIALOG")
  if frame.SetBackdrop then frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 }) end
  if frame.SetBackdropColor then frame:SetBackdropColor(0, 0, 0, 0.92) end
  frame:SetMovable(true); frame:EnableMouse(true)
  frame:RegisterForDrag("LeftButton")
  frame:SetScript("OnDragStart", frame.StartMoving)
  frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
  title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  title:SetPoint("TOPLEFT", 12, -10)
  for i = 1, PER do
    local col, row = (i - 1) % COLS, math.floor((i - 1) / COLS)
    local m = CreateFrame("PlayerModel", nil, frame)
    m:SetSize(140, 110)
    m:SetPoint("TOPLEFT", frame, "TOPLEFT", 10 + col * 150, -34 - row * 142)
    local fs = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    fs:SetPoint("TOPLEFT", m, "BOTTOMLEFT", 0, -2)
    fs:SetWidth(145)
    cells[i] = { m = m, fs = fs }
  end
  local function button(text, x, fn)
    local b = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    b:SetSize(80, 22); b:SetText(text); b:SetPoint("BOTTOMLEFT", x, 8)
    b:SetScript("OnClick", fn)
  end
  button("Prev", 10, function() Spells.show(current - 1) end)
  button("Next", 100, function() Spells.show(current + 1) end)
  button("Close", 530, function() frame:Hide() end)
end

function Spells.show(p)
  if not frame then build() end
  local list
  list, current = Spells.page(p)
  frame:Show()
  title:SetText("Dread spell models, page " .. current .. " of " .. Spells.pages() .. ".  Tell me the numbers that look right.")
  for i = 1, PER do
    local c, e = cells[i], list[i]
    if e then
      c.m:Show(); c.fs:SetText(e.n .. "  " .. e.id .. "  " .. e.name)
      pcall(function() c.m:SetModel(e.id) end)
      pcall(function() c.m:SetModelScale(1) end)
      pcall(function() c.m:SetAnimation(0) end)
    else
      c.m:Hide(); c.fs:SetText("")
    end
  end
  return current
end

function Spells.hide() if frame then frame:Hide() end end
