-- /gaunt: runs the speed test, checks the assets, saves a report, then lets you walk the test level and shoot the models.
local _, ns = ...
ns = ns or {}
local Gauntlet = {}
ns.Gauntlet = Gauntlet

local Ray, Level, Bench, Render = ns.Ray, ns.Level, ns.Bench, ns.Render

local R, map, mode, S                 -- the drawing state, the parsed map, what is going on ("bench", "swatch", "walk"), the run's own state
local colbuf = {}

local function say(msg) print("|cffffaa33Gauntlet|r " .. msg) end
Gauntlet.say = say

local function shot(why)              -- a screenshot a moment from now, so the thing on screen is in it
  if Screenshot and C_Timer and C_Timer.After then
    C_Timer.After(0.35, function() pcall(Screenshot) end)
    return true
  end
  return false
end

local function copy_enemies()
  local out = {}
  for i, e in ipairs(Level.ENEMIES) do out[i] = { x = e.x, y = e.y, r = e.r, cid = e.cid, model = e.model, name = e.name, hp = 3, dead = false } end
  return out
end

---------------------------------------------------------------- the speed test, one width at a time
local function start_pass()
  Render.set_columns(R, Bench.COLUMNS[S.pass])
  S.t, S.dts, S.warm, S.shot = 0, {}, 10, false
  R.title:SetText(string.format("Gauntlet   speed test %d of %d: %d columns", S.pass, #Bench.COLUMNS, R.n))
end

local function draw_view(x, y, ang)
  Ray.columns(map, x, y, ang, Render.FOV, R.n, colbuf)
  Render.walls(R, colbuf)
  Render.enemies(R, x, y, ang, colbuf, S.enemies)
end

-- Textures, models and sounds: what drew, what loaded, what will play. Read once the tests have run, since models load a moment later.
local function check_assets()
  local a = { textures = {}, models = {}, sounds = {} }
  local probe = R.view:CreateTexture(nil, "BACKGROUND")
  for _, c in ipairs(Level.CANDIDATES) do
    local ok = pcall(probe.SetTexture, probe, c[1])
    a.textures[#a.textures + 1] = { id = c[1], name = c[2], ok = ok }
  end
  probe:Hide()
  for i, e in ipairs(S.enemies) do
    local m = R.models[i]
    a.models[#a.models + 1] = { name = e.name, ok = m and m.ok or false }
  end
  for _, id in ipairs(Level.SHOTS) do
    local ok = false
    if PlaySoundFile then ok = (select(1, pcall(PlaySoundFile, id, "Master")) and true or false) end
    a.sounds[#a.sounds + 1] = { id = id, ok = ok }
  end
  return a
end

local function size_text()
  if GetScreenWidth and GetScreenHeight then
    return string.format("%dx%d", math.floor((GetScreenWidth() or 0) + 0.5), math.floor((GetScreenHeight() or 0) + 0.5))
  end
  return "?"
end

local function finish_bench()
  S.assets = check_assets()
  S.notes = {}
  S.report = Bench.report(S.results, S.assets, { build = ns.BUILD, size = size_text(), notes = S.notes })
  GauntletDB = GauntletDB or {}
  GauntletDB.report, GauntletDB.at = S.report, time and time() or 0
  local v = Bench.verdict(S.results)
  say("speed test: " .. v.word .. (v.best and (", " .. v.best .. " columns hold 60 fps") or ""))
  for _, r in ipairs(S.results) do say(string.format("  %d columns: %d fps average, %d in the slowest 1%%", r.columns, math.floor(r.avg + 0.5), math.floor(r.low + 0.5))) end
  mode = "swatch"
  S.t = 0
  Gauntlet.show_swatches(true)
  R.msg:SetText("wall textures: do they all look like walls?")
end

local function update_bench(dt)
  S.t = S.t + dt
  local x, y, ang = Bench.pose(S.t)
  S.x, S.y, S.ang = x, y, ang
  draw_view(x, y, ang)
  Render.weapon(R, S.t, 0)
  if S.warm > 0 then S.warm = S.warm - 1 else S.dts[#S.dts + 1] = dt end
  R.hud:SetText(string.format("%d columns   %d fps now", R.n, dt > 0 and math.floor(1 / dt + 0.5) or 0))
  if S.pass == #Bench.COLUMNS and S.t >= 3 and not S.shot then S.shot = true; shot("bench") end
  if S.t >= Bench.SECONDS then
    local st = Bench.stats(S.dts)
    S.results[#S.results + 1] = { columns = R.n, avg = st.avg, min = st.min, low = st.low }
    if S.pass < #Bench.COLUMNS then
      S.pass = S.pass + 1
      start_pass()
    else
      finish_bench()
    end
  end
end

---------------------------------------------------------------- the picture of every candidate wall texture
function Gauntlet.show_swatches(on)
  if not R.swatches then
    R.swatches = {}
    local n = #Level.CANDIDATES
    local w = Render.VW / n
    for i, c in ipairs(Level.CANDIDATES) do
      local t = R.view:CreateTexture(nil, "OVERLAY")
      t:SetSize(w - 2, Render.VH * 0.6)
      t:SetPoint("TOPLEFT", R.view, "TOPLEFT", (i - 1) * w + 1, -70)
      pcall(t.SetTexture, t, c[1])
      t:SetTexCoord(0, 0.5, 0, 1)
      local l = R.view:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
      l:SetPoint("TOPLEFT", R.view, "TOPLEFT", (i - 1) * w + 1, -70 - Render.VH * 0.6 - 4)
      l:SetText(tostring(i))
      R.swatches[i] = { tex = t, label = l }
    end
  end
  for _, s in ipairs(R.swatches) do
    if on then s.tex:Show(); s.label:Show() else s.tex:Hide(); s.label:Hide() end
  end
end

---------------------------------------------------------------- walking and shooting
local KEYS = { W = true, A = true, S = true, D = true, Q = true, E = true, LEFT = true, RIGHT = true, UP = true, DOWN = true, SPACE = true }
local SPEED, TURN, KEYTURN, DEAD, SHOT_GAP = 3.0, 3.0, 2.3, 0.12, 0.25

-- A shot: the nearest enemy in front of a wall takes a hit; three hits and it falls over.
function Gauntlet.fire()
  if S.cool and S.cool > 0 then return false end
  S.cool, S.kick = SHOT_GAP, 1
  S.shots = (S.shots or 0) + 1
  if PlaySoundFile then pcall(PlaySoundFile, Level.SHOTS[1 + (S.shots % #Level.SHOTS)], "Master") end
  local e = Ray.hitscan(map, S.x, S.y, S.ang, S.enemies, 40)
  if e then
    S.hits = (S.hits or 0) + 1
    e.hp = e.hp - 1
    e.flash = 0.15
    if PlaySoundFile then pcall(PlaySoundFile, Level.IMPACT, "Master") end
    if e.hp <= 0 then e.dead = true; S.kills = (S.kills or 0) + 1 end
  end
  return true
end

local function mouse_turn()
  if not (GetCursorPosition and Gauntlet.mouse) then return 0 end
  local mx = GetCursorPosition()
  local scale = R.frame:GetEffectiveScale() or 1
  local cx = R.frame:GetCenter()
  if not (mx and cx) then return 0 end
  local off = (mx / scale - cx) / (Render.VW / 2)
  if math.abs(off) < DEAD or math.abs(off) > 1 then return 0 end                -- in the middle: straight; outside the window: not ours to read
  return off * TURN
end

local function update_walk(dt)
  local k = S.keys
  local fwd = (k.W and 1 or 0) - (k.S and 1 or 0) + (k.UP and 1 or 0) - (k.DOWN and 1 or 0)
  local side = (k.D and 1 or 0) - (k.A and 1 or 0)
  local turn = (k.E and 1 or 0) - (k.Q and 1 or 0) + (k.RIGHT and 1 or 0) - (k.LEFT and 1 or 0)
  S.ang = S.ang + turn * KEYTURN * dt + mouse_turn() * dt
  local c, s = math.cos(S.ang), math.sin(S.ang)
  local dx = (c * fwd - s * side) * SPEED * dt
  local dy = (s * fwd + c * side) * SPEED * dt
  S.x, S.y = Ray.move(map, S.x, S.y, dx, dy, 0.22)
  if fwd ~= 0 or side ~= 0 then S.walk = S.walk + dt end
  if k.SPACE then Gauntlet.fire() end
  if S.cool and S.cool > 0 then S.cool = S.cool - dt end
  if S.kick and S.kick > 0 then S.kick = math.max(0, S.kick - dt * 6) end
  for _, e in ipairs(S.enemies) do if e.flash then e.flash = e.flash > dt and e.flash - dt or nil end end
  draw_view(S.x, S.y, S.ang)
  Render.weapon(R, S.walk, S.kick)
  R.hud:SetText(string.format("%d fps   W/S move  A/D strafe  Q/E or mouse turn  click or space fires  Esc leaves   shots %d  hits %d  down %d",
      dt > 0 and math.floor(1 / dt + 0.5) or 0, S.shots or 0, S.hits or 0, S.kills or 0))
end

local function update_swatch(dt)
  S.t = S.t + dt
  draw_view(S.x, S.y, S.ang)
  if S.t >= 0.8 and not S.sshot then S.sshot = true; shot("textures") end
  if S.t >= 4 then Gauntlet.start_walk() end
end

function Gauntlet.start_walk()
  if mode == "swatch" then Gauntlet.show_swatches(false) end
  mode = "walk"
  R.msg:SetText("")
  R.title:SetText("Gauntlet   walk around and shoot the models")
  S.x, S.y, S.ang = Level.START.x, Level.START.y, Level.START.angle
  S.keys, S.walk, S.cool, S.kick = {}, 0, 0, 0
  Render.set_columns(R, S.final_columns or 160)
end

---------------------------------------------------------------- the window
local function on_update(_, dt)
  if dt > 0.1 then dt = 0.1 end
  if mode == "bench" then update_bench(dt)
  elseif mode == "swatch" then update_swatch(dt)
  elseif mode == "walk" then update_walk(dt) end
end

function Gauntlet.stop()
  if S and mode == "walk" then
    S.notes = S.notes or {}
    S.notes[1] = string.format("walked and shot: %d shots, %d hits, %d enemies down", S.shots or 0, S.hits or 0, S.kills or 0)
    if S.results then
      S.report = Bench.report(S.results, S.assets, { build = ns.BUILD, size = size_text(), notes = S.notes })
      GauntletDB = GauntletDB or {}
      GauntletDB.report = S.report
    end
  end
  mode = nil
  if R then R.frame:Hide() end
end

local function ensure_window()
  if R then return end
  Level = ns.Level
  map = Ray.parse(Level.ROWS)
  R = Render.build()
  R.frame:SetScript("OnUpdate", on_update)
  R.frame:SetScript("OnKeyDown", function(self, key)
    if key == "ESCAPE" then self:SetPropagateKeyboardInput(false); Gauntlet.stop(); return end
    if KEYS[key] and S then
      S.keys = S.keys or {}
      S.keys[key] = true
      self:SetPropagateKeyboardInput(false)
    else
      self:SetPropagateKeyboardInput(true)
    end
  end)
  R.frame:SetScript("OnKeyUp", function(self, key) if S and S.keys then S.keys[key] = nil end end)
  R.frame:SetScript("OnMouseDown", function(self, button) if mode == "walk" and button == "LeftButton" then Gauntlet.fire() end end)
  local drag = CreateFrame("Frame", nil, R.frame)
  drag:SetPoint("TOPLEFT"); drag:SetPoint("TOPRIGHT"); drag:SetHeight(22); drag:EnableMouse(true)
  drag:RegisterForDrag("LeftButton")
  drag:SetScript("OnDragStart", function() R.frame:StartMoving() end)
  drag:SetScript("OnDragStop", function() R.frame:StopMovingOrSizing() end)
end

Gauntlet.mouse = true

-- Everything: the speed test, then the assets, then the walk.
function Gauntlet.run()
  ensure_window()
  S = { pass = 1, results = {}, enemies = copy_enemies(), keys = {}, walk = 0 }
  S.x, S.y, S.ang = Bench.pose(0)
  Render.make_models(R, S.enemies)
  R.frame:Show()
  mode = "bench"
  start_pass()
  say("running the speed test (about " .. (#Bench.COLUMNS * Bench.SECONDS) .. " seconds), then the asset check, then you can walk around")
end

-- Straight into the walk, skipping the tests.
function Gauntlet.walk()
  ensure_window()
  S = { pass = 1, results = {}, enemies = copy_enemies(), keys = {}, walk = 0 }
  Render.make_models(R, S.enemies)
  R.frame:Show()
  mode = "swatch"
  Gauntlet.start_walk()
end

function Gauntlet.mode() return mode end
function Gauntlet.state() return S end
function Gauntlet.render() return R end

function Gauntlet.report_text()
  if S and S.report then return S.report end
  return GauntletDB and GauntletDB.report or nil
end

-- Some text in a box to select and copy.
function Gauntlet.copy_text(text)
  local box = CreateFrame("Frame", "GauntletCopy", UIParent, "BackdropTemplate")
  box:SetSize(560, 340); box:SetPoint("CENTER"); box:SetFrameStrata("TOOLTIP")
  if box.SetBackdrop then box:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 }) end
  if box.SetBackdropColor then box:SetBackdropColor(0, 0, 0, 0.95) end
  local hint = box:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
  hint:SetPoint("TOPLEFT", 10, -8); hint:SetText("Ctrl+A, then Ctrl+C, then paste it. Esc closes.")
  local edit = CreateFrame("EditBox", nil, box)
  edit:SetMultiLine(true); edit:SetPoint("TOPLEFT", 10, -26); edit:SetSize(540, 300)
  pcall(edit.SetFontObject, edit, ChatFontNormal or GameFontNormal)
  edit:SetAutoFocus(true)
  edit:SetScript("OnEscapePressed", function() box:Hide() end)
  edit:SetText(text)
  edit:HighlightText()
  box.edit = edit
  return true
end

-- The test report in a box.
function Gauntlet.copy_report()
  local text = Gauntlet.report_text()
  if not text then say("no report yet: type /gaunt test first") return false end
  return Gauntlet.copy_text(text)
end

return Gauntlet
