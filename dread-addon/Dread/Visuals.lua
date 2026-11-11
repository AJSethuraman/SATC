-- Test 3: which WoW visuals can an addon window show on Forever?  /dread visuals
-- Every probe is wrapped so one failure cannot stop the rest. Candidates are guesses to be tested:
-- a name that fails is the finding, and a "worked" line only means the call did not error, so LOOK at the window.
local ADDON, ns = ...
local V = {}
ns.Visuals = V

local function say(msg)
  msg = "|cffff5555Dread|r " .. msg
  if ns.log then ns.log(msg) else print(msg) end
end

-- Creature ids to try with SetCreature. Chosen from memory of Classic NPCs; what matters is whether
-- *any* model draws, not which animal it is.
V.CREATURES = { 299, 721, 6, 46, 3098, 3101 }
-- Spell-effect models to try with SetModel (paths from memory; fileDataIDs would be the modern form).
V.SPELLS = {
  "Spells\\Fireball_Missile_Low.m2",
  "Spells\\Frostbolt_Missile.m2",
  "Spells\\Lightningboltmissile.m2",
}
-- Ground and backdrop textures to tile.
V.TILES = {
  "Interface\\FrameGeneral\\UI-Background-Rock",
  "Interface\\FrameGeneral\\UI-Background-Marble",
  "Interface\\DialogFrame\\UI-DialogBox-Background",
  "Interface\\Tooltips\\UI-Tooltip-Background",
  "Interface\\WorldMap\\Mulgore\\Mulgore1",
  "Interface\\WorldMap\\Barrens\\Barrens1",
}

local frame, results, parts

local function probe(name, fn)
  local ok, err = pcall(fn)
  results[#results + 1] = name .. ": " .. (ok and "no error" or ("ERROR " .. tostring(err)))
end

local function label(parent, text, x, y)
  local fs = parent:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
  fs:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
  fs:SetText(text)
  return fs
end

local function slot(i)            -- ten model slots on two rows
  local col, row = (i - 1) % 5, math.floor((i - 1) / 5)
  return 12 + col * 125, -30 - row * 150
end

function V.run()
  results = {}
  if not frame then
    frame = CreateFrame("Frame", "DreadVisualsFrame", UIParent, "BackdropTemplate")
    frame:SetSize(650, 480)
    frame:SetPoint("CENTER")
    frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
    frame:SetBackdropColor(0.05, 0.05, 0.05, 0.92)
    frame:SetBackdropBorderColor(0.6, 0.1, 0.1, 1)
    frame:SetMovable(true); frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    label(frame, "Dread test 3: visuals.  /dread stop to close.  Top: 3D models.  Bottom: textures.", 12, -10)
  end
  frame:Show()
  for _, p in ipairs(parts or {}) do p:Hide() end
  parts = {}

  local models, n = {}, 0
  local function newModel(title, setup)
    n = n + 1
    local x, y = slot(n)
    local m = CreateFrame("PlayerModel", nil, frame)
    m:SetSize(115, 120)
    m:SetPoint("TOPLEFT", frame, "TOPLEFT", x, y - 14)
    parts[#parts + 1] = m
    local fs = label(frame, title, x, y)
    parts[#parts + 1] = fs
    probe("model " .. title, function() setup(m) end)
    models[#models + 1] = { title = title, m = m }
  end

  newModel("player", function(m) m:SetUnit("player") end)
  newModel("target", function(m) m:SetUnit("target") end)
  for _, id in ipairs(V.CREATURES) do
    newModel("creature " .. id, function(m) m:SetCreature(id) end)
  end
  for _, path in ipairs({ V.SPELLS[1], V.SPELLS[2] }) do
    newModel(path:match("([^\\]+)%.m2$") or path, function(m) m:SetModel(path) end)
  end

  -- textures
  local y = -330
  label(frame, "textures (tiled where they exist)", 12, y + 14)
  for i, path in ipairs(V.TILES) do
    local t = frame:CreateTexture(nil, "ARTWORK")
    t:SetSize(96, 96)
    t:SetPoint("TOPLEFT", frame, "TOPLEFT", 12 + (i - 1) * 105, y - 4)
    probe("texture " .. path, function() t:SetTexture(path) end)
    parts[#parts + 1] = t
    local short = path:match("([^\\]+)$")
    parts[#parts + 1] = label(frame, short, 12 + (i - 1) * 105, y - 104)
  end

  C_Timer.After(1.0, function()
    for _, e in ipairs(models) do
      local ok, id = pcall(function() return e.m:GetModelFileID() end)
      results[#results + 1] = "model " .. e.title .. " file id: " .. (ok and tostring(id) or "(no such call)")
    end
    for _, r in ipairs(results) do say(r) end
    DreadDB = DreadDB or {}
    DreadDB.results = DreadDB.results or {}
    DreadDB.results.test3 = table.concat(results, " | ")
    say("done. Send a screenshot of the window and this chat: which boxes show a model, which show nothing.")
  end)
end

function V.hide() if frame then frame:Hide() end end

return V
