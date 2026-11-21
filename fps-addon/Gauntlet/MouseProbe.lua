-- The mouse test: /gaunt mousetest. It asks you to move the mouse three ways, six seconds each, and records what the client reports
-- every frame (where the cursor is, how far it moved, which way you face, whether it is locked). It then picks the mouse mode that
-- works on this client, saves the choice, and shows the numbers to copy. Nothing to type or read in between.
local _, ns = ...
ns = ns or {}
local Probe = {}
ns.MouseProbe = Probe

Probe.PHASES = {
  { id = "free",  secs = 6, lock = false, text = "Step 1 of 3.  Move the mouse all over the screen.  Do not click." },
  { id = "lock",  secs = 6, lock = true,  text = "Step 2 of 3.  The mouse is locked now.  Keep moving it left and right." },
  { id = "right", secs = 6, lock = false, text = "Step 3 of 3.  HOLD the right mouse button and move the mouse left and right." },
}
Probe.NEEDED = 3                              -- a signal counts as working if it changed on at least this many frames

local function stat() return { frames = 0, facing_nil = 0, facing_changes = 0, fmin = nil, fmax = nil, flast = nil, cx_changes = 0, xmin = nil, xmax = nil, xlast = nil,
                                 delta_nonzero = 0, delta_sum = 0, locked = 0, right = 0 } end

function Probe.new()
  local P = { phase = 1, t = 0, done = false, stats = {} }
  for i = 1, #Probe.PHASES do P.stats[i] = stat() end
  return P
end

-- One frame's readings into the running totals for the current phase. r: { facing, cx, dx, locked, right } (any may be nil).
function Probe.sample(P, r)
  local s = P.stats[P.phase]
  s.frames = s.frames + 1
  if r.facing == nil then s.facing_nil = s.facing_nil + 1
  else
    if s.flast ~= nil and math.abs(r.facing - s.flast) > 1e-4 then s.facing_changes = s.facing_changes + 1 end
    s.flast = r.facing
    s.fmin = s.fmin and math.min(s.fmin, r.facing) or r.facing
    s.fmax = s.fmax and math.max(s.fmax, r.facing) or r.facing
  end
  if r.cx ~= nil then
    if s.xlast ~= nil and r.cx ~= s.xlast then s.cx_changes = s.cx_changes + 1 end
    s.xlast = r.cx
    s.xmin = s.xmin and math.min(s.xmin, r.cx) or r.cx
    s.xmax = s.xmax and math.max(s.xmax, r.cx) or r.cx
  end
  if r.dx and r.dx ~= 0 then s.delta_nonzero = s.delta_nonzero + 1; s.delta_sum = s.delta_sum + math.abs(r.dx) end
  if r.locked then s.locked = s.locked + 1 end
  if r.right then s.right = s.right + 1 end
end

-- Which signals moved in a phase: a list of "delta", "facing", "cursor".
function Probe.working(s)
  local out = {}
  if s.delta_nonzero >= Probe.NEEDED then out[#out + 1] = "delta" end
  if s.facing_changes >= Probe.NEEDED then out[#out + 1] = "facing" end
  if s.cx_changes >= Probe.NEEDED then out[#out + 1] = "cursor" end
  return out
end

-- The mode to use: "look" (lock the mouse) if any signal moved while locked, otherwise "free" (turn with the cursor's own movement).
-- A client that gave nothing even with the cursor free gets "edge".
local function has(list, name) for _, v in ipairs(list) do if v == name then return true end end return false end

-- Which mode to use. Only a real mouse-movement signal while locked (the cursor delta) is trusted for "look": the player's facing is a smoothed
-- stand-in that can move without matching the mouse, so facing alone does not choose the lock. Otherwise the cursor's own movement ("free", with a
-- turn at the screen edge) is the dependable choice. "lockpos" and "edge" are for clients that give nothing better.
function Probe.verdict(P)
  local locked = Probe.working(P.stats[2])
  local free = Probe.working(P.stats[1])
  if has(locked, "delta") then return "look", locked end
  if has(free, "cursor") then return "free", free end
  if #locked > 0 and not has(locked, "facing") then return "lockpos", locked end    -- facing alone never chooses the lock
  return "edge", {}
end

local function f3(v) return v == nil and "none" or string.format("%.3f", v) end

function Probe.report(P, env)
  env = env or {}
  local out = {}
  local function add(t) out[#out + 1] = t end
  add("GAUNTLET MOUSE TEST   build " .. tostring(env.build or "?") .. "   client " .. tostring(env.client or "?"))
  add("functions present: " .. tostring(env.apis or "?"))
  for i, ph in ipairs(Probe.PHASES) do
    local s = P.stats[i]
    add("")
    add(string.format("%s  (%d frames)", ph.id:upper(), s.frames))
    add(string.format("  facing: nil on %d frames, changed on %d, range %s to %s", s.facing_nil, s.facing_changes, f3(s.fmin), f3(s.fmax)))
    add(string.format("  cursor x: changed on %d frames, range %s to %s", s.cx_changes, f3(s.xmin), f3(s.xmax)))
    add(string.format("  cursor delta: nonzero on %d frames, total %.0f", s.delta_nonzero, s.delta_sum))
    add(string.format("  client says locked on %d frames, right button down on %d", s.locked, s.right))
    local w = Probe.working(s)
    add("  signals that moved: " .. (#w > 0 and table.concat(w, ", ") or "none"))
  end
  local mode, sig = Probe.verdict(P)
  add("")
  add("CHOICE: " .. mode .. (#sig > 0 and (" (using " .. table.concat(sig, ", ") .. ")") or ""))
  return table.concat(out, "\n")
end

---------------------------------------------------------------- the window

local F, text
local P, started

local function read()
  local r = {}
  r.facing = GetPlayerFacing and GetPlayerFacing() or nil
  if GetCursorPosition then r.cx = (GetCursorPosition()) end
  if GetCursorDelta then r.dx = (GetCursorDelta()) end
  r.locked = IsMouselooking and IsMouselooking() and true or false
  r.right = IsMouseButtonDown and IsMouseButtonDown("RightButton") and true or false
  return r
end

local we_started = false                      -- did this test start the lock? Then it stops it, whatever IsMouselooking says
local function lock(on)
  if not (MouselookStart and MouselookStop) then return end
  if on then
    if not (IsMouselooking and IsMouselooking()) then MouselookStart() end
    we_started = true
  elseif we_started or (IsMouselooking and IsMouselooking()) then
    MouselookStop()
    we_started = false
  end
end

local function names()
  local list, found = { "GetPlayerFacing", "GetCursorPosition", "GetCursorDelta", "MouselookStart", "MouselookStop", "IsMouselooking", "IsMouseButtonDown" }, {}
  for _, n in ipairs(list) do found[#found + 1] = n .. (_G[n] and "=yes" or "=NO") end
  return table.concat(found, " ")
end

local function finish()
  lock(false)
  P.done = true
  F:Hide()
  local client = ""
  if GetBuildInfo then client = table.concat({ GetBuildInfo() }, " ") end
  local rep = Probe.report(P, { build = ns.BUILD, client = client, apis = names() })
  local mode = Probe.verdict(P)
  GauntletDB = GauntletDB or {}
  GauntletDB.mouse_probe = rep
  GauntletDB.mouse_mode, GauntletDB.mouse_mode_v = mode, 2      -- v2: choices saved by an older test (which trusted facing alone) are ignored
  if ns.Main and ns.Main.set_mouse_mode then ns.Main.set_mouse_mode(mode) end
  print("|cffffaa33Gauntlet|r mouse test done. Mode chosen: " .. mode .. ". /reload and run Collect-Gauntlet-Report.bat to send me the numbers.")
  if ns.Gauntlet and ns.Gauntlet.copy_text then ns.Gauntlet.copy_text(rep) end
end

local function on_update(_, dt)
  if not P or P.done then return end
  local ph = Probe.PHASES[P.phase]
  if not started then started = true; lock(ph.lock) end
  if ph.lock then lock(true) end
  Probe.sample(P, read())
  P.t = P.t + dt
  text:SetText(string.format("%s\n\n%d seconds left", ph.text, math.max(0, math.ceil(ph.secs - P.t))))
  if P.t >= ph.secs then
    lock(false)
    if P.phase >= #Probe.PHASES then finish(); return end
    P.phase, P.t, started = P.phase + 1, 0, false
  end
end

function Probe.state() return P end
function Probe.frame() return F end

function Probe.stop()
  if P and not P.done then lock(false); P.done = true end
  if F then F:Hide() end
end

function Probe.start()
  if ns.Main and ns.Main.stop then ns.Main.stop() end
  if ns.Gauntlet and ns.Gauntlet.stop then ns.Gauntlet.stop() end
  P, started = Probe.new(), false
  if not F then
    F = CreateFrame("Frame", "GauntletMouseProbe", UIParent, "BackdropTemplate")
    F:SetSize(560, 130); F:SetPoint("CENTER"); F:SetFrameStrata("FULLSCREEN_DIALOG")
    if F.SetBackdrop then F:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 2 }) end
    if F.SetBackdropColor then F:SetBackdropColor(0, 0, 0, 0.9) end
    text = F:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    text:SetPoint("CENTER"); text:SetWidth(520)
    F:SetScript("OnUpdate", on_update)
    F:EnableKeyboard(true)
    F:SetScript("OnKeyDown", function(self, key) if key == "ESCAPE" then Probe.stop(); print("|cffffaa33Gauntlet|r mouse test cancelled.") end end)
  end
  text:SetText("Mouse test starting...")
  F:Show()
end

return Probe
