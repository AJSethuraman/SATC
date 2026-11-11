-- Dread's own message window, so nothing has to go to the General chat tab.
--   /dread log          show or hide it (closing it with the X keeps it closed until you ask for it again)
--   /dread log clear    empty it
--   /dread log copy     a box with the whole log as plain text: Ctrl+A, Ctrl+C, paste anywhere
--   /dread log chat     also copy every message to the General chat tab (off by default)
-- Messages are kept (the last 500) even while the window is hidden, and replay into it when it opens.
local ADDON, ns = ...
local Log = {}
ns.Log = Log

local MAX = 500
local lines, frame, msgframe, box = {}, nil, nil, nil

local function cfg()
  DreadDB = DreadDB or {}
  DreadDB.log = DreadDB.log or {}
  return DreadDB.log
end

local function stamp()
  local ok, t = pcall(date, "%H:%M:%S")
  return (ok and t) and ("|cff888888" .. t .. "|r ") or ""
end

function Log.lines() return lines end

-- The whole log with colour codes stripped, for copying out.
function Log.plain()
  local out = {}
  for i, l in ipairs(lines) do
    out[i] = l:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
  end
  return table.concat(out, "\n")
end

local function save_place()
  local c = cfg()
  local ok, p, _, rp, x, y = pcall(frame.GetPoint, frame, 1)
  if ok and p then c.point = { p, rp or p, x or 0, y or 0 } end
  local w, h = frame:GetWidth(), frame:GetHeight()
  if type(w) == "number" and type(h) == "number" then c.w, c.h = w, h end
end

local function build()
  if frame then return end
  local c = cfg()
  frame = CreateFrame("Frame", "DreadLogFrame", UIParent, "BackdropTemplate")
  frame:SetSize(c.w or 440, c.h or 230)
  local pt = c.point
  if type(pt) == "table" then frame:SetPoint(pt[1], UIParent, pt[2], pt[3], pt[4]) else frame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 20, -80) end
  frame:SetClampedToScreen(true)
  frame:SetFrameStrata("MEDIUM")
  frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
  frame:SetBackdropColor(0, 0, 0, 0.8)
  frame:SetBackdropBorderColor(0.6, 0.1, 0.1, 1)
  frame:SetMovable(true); frame:SetResizable(true); frame:EnableMouse(true)
  pcall(frame.SetResizeBounds, frame, 260, 110)
  pcall(frame.SetMinResize, frame, 260, 110)

  local bar = CreateFrame("Frame", nil, frame)
  bar:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
  bar:SetPoint("TOPRIGHT", frame, "TOPRIGHT", 0, 0)
  bar:SetHeight(20)
  bar:EnableMouse(true)
  bar:RegisterForDrag("LeftButton")
  bar:SetScript("OnDragStart", function() frame:StartMoving() end)
  bar:SetScript("OnDragStop", function() frame:StopMovingOrSizing(); save_place() end)
  local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
  title:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -5)
  title:SetText("Dread log")
  local function button(text, w, anchor_x, fn)
    local b = CreateFrame("Button", nil, bar, "UIPanelButtonTemplate")
    b:SetSize(w, 16); b:SetPoint("TOPRIGHT", bar, "TOPRIGHT", anchor_x, -2); b:SetText(text)
    b:SetScript("OnClick", fn)
    return b
  end
  button("X", 20, -3, function() cfg().hidden = true; frame:Hide() end)
  button("Clear", 44, -26, function() Log.clear() end)
  button("Copy", 44, -73, function() Log.copy() end)

  msgframe = CreateFrame("ScrollingMessageFrame", nil, frame)
  msgframe:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -24)
  msgframe:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -8, 8)
  pcall(msgframe.SetFontObject, msgframe, ChatFontNormal)
  msgframe:SetMaxLines(MAX)
  msgframe:SetFading(false)
  msgframe:SetJustifyH("LEFT")
  pcall(msgframe.SetInsertMode, msgframe, "BOTTOM")
  msgframe:EnableMouseWheel(true)
  msgframe:SetScript("OnMouseWheel", function(self, delta)
    if delta > 0 then self:ScrollUp() else self:ScrollDown() end
  end)
  local grip = CreateFrame("Button", nil, frame)
  grip:SetSize(16, 16); grip:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", 0, 0)
  local gt = grip:CreateTexture(nil, "OVERLAY"); gt:SetAllPoints(grip); gt:SetTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
  grip:SetScript("OnMouseDown", function() frame:StartSizing("BOTTOMRIGHT") end)
  grip:SetScript("OnMouseUp", function() frame:StopMovingOrSizing(); save_place() end)
  for _, l in ipairs(lines) do msgframe:AddMessage(l) end           -- what arrived before the window existed
end

function Log.chat_on() return DreadDB ~= nil and DreadDB.chat == true end

-- The one door every Dread message goes through.
function ns.log(msg)
  msg = tostring(msg)
  local ok = CreateFrame and pcall(build)           -- build first: it replays what is already in `lines`, and this line is not in it yet
  local line = stamp() .. msg
  lines[#lines + 1] = line
  if #lines > MAX then table.remove(lines, 1) end
  if Log.chat_on() then print(msg) end
  if ok and frame then
    msgframe:AddMessage(line)
    if not cfg().hidden and not frame:IsShown() then frame:Show() end
  end
end

function Log.toggle()
  pcall(build)
  if not frame then return false end
  if frame:IsShown() then
    cfg().hidden = true; frame:Hide()
  else
    cfg().hidden = nil; frame:Show()
  end
  return frame:IsShown()
end

function Log.clear()
  lines = {}
  if msgframe then msgframe:Clear() end
end

function Log.copy()
  if not box then
    box = CreateFrame("Frame", "DreadLogCopy", UIParent, "BackdropTemplate")
    box:SetSize(520, 300); box:SetPoint("CENTER"); box:SetFrameStrata("DIALOG")
    box:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
    box:SetBackdropColor(0, 0, 0, 0.95); box:SetBackdropBorderColor(0.6, 0.1, 0.1, 1)
    local hint = box:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    hint:SetPoint("TOPLEFT", 10, -8); hint:SetText("Ctrl+A, then Ctrl+C, then paste. Esc closes.")
    box.edit = CreateFrame("EditBox", nil, box)
    box.edit:SetMultiLine(true); box.edit:SetPoint("TOPLEFT", 10, -26); box.edit:SetSize(500, 262)
    pcall(box.edit.SetFontObject, box.edit, ChatFontNormal)
    box.edit:SetAutoFocus(true)
    box.edit:SetScript("OnEscapePressed", function() box:Hide() end)
  end
  box.edit:SetText(Log.plain())
  box:Show()
  box.edit:SetFocus(); box.edit:HighlightText()
end

function Log.set_chat(on)
  DreadDB = DreadDB or {}
  DreadDB.chat = on and true or nil
  return DreadDB.chat == true
end

return Log
