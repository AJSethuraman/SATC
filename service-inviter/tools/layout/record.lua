-- Recording stubs for the layout check: every frame, texture and font string the addon
-- creates, with its layout calls, so tools/layout/check.py can draw the windows.
CLOCK = 1000
function GetTime() return CLOCK end
function time() return math.floor(CLOCK) end
SENT, INVITED, TRADES, PRINTED = {}, {}, {}, {}
ALL = {}
local nextId = 0
local function New(kind, parent, template, font)
  nextId = nextId + 1
  local o = { _id = nextId, _kind = kind, _parent = parent or false, _color = false, _justify = false, _fontsize = false, _name = "", _disabled = false, _nowrap = false, _template = template or "", _font = font or "",
              _points = {}, _scripts = {}, _attr = {}, _text = "", _checked = false, _hidden = false,
              _shown = false, _w = false, _h = false, _tc = false, _siStyle = false, _siSize = false }
  ALL[#ALL + 1] = o
  local m = {}
  function m.SetPoint(self, p, a, b, c, d)
    local rel, rp, x, y
    if type(a) == "table" then rel, rp, x, y = a, b, c, d
      if type(rp) == "number" then rp, x, y = p, b, c end
    elseif type(a) == "number" then x, y = a, b end
    self._points[#self._points + 1] = { p = p, rel = rel and rel._id or 0, rp = rp or p, x = x or 0, y = y or 0 }
  end
  function m.SetAllPoints(self) self._points = { { p = "TOPLEFT", rel = 0, rp = "TOPLEFT", x = 0, y = 0 }, { p = "BOTTOMRIGHT", rel = 0, rp = "BOTTOMRIGHT", x = 0, y = 0 } } end
  function m.ClearAllPoints(self) self._points = {} end
  function m.SetSize(self, w, h) self._w, self._h = w, h end
  function m.SetWidth(self, w) self._w = w end
  function m.SetHeight(self, h) self._h = h end
  function m.SetText(self, s) self._text = s if rawget(self, "_fs") then self._fs._text = s end end
  function m.GetText(self) return self._text end
  function m.SetChecked(self, v) self._checked = v and true or false end
  function m.GetChecked(self) return self._checked end
  function m.SetColorTexture(self, r, g, b, a) self._color = { r, g, b, a or 1 } end
  function m.SetJustifyH(self, j) self._justify = j end
  function m.Disable(self) self._disabled = true end
  function m.Enable(self) self._disabled = false end
  function m.SetFontObject(self, f) self._font = f end
  function m.SetTextColor(self, r, g, b) self._tc = { r, g, b } end
  function m.SetFontString(self, fs) self._fs = fs end
  function m.SetWordWrap(self, v) self._nowrap = not v end
  function m.SetFont(self, f, size) self._fontsize = size end
  function m.GetFont() return "font", 12, "" end
  function m.SetScript(self, n, fn) self._scripts[n] = fn end
  function m.HookScript(self, n, fn) self._scripts[n] = fn end
  function m.GetScript(self, n) return self._scripts[n] end
  function m.SetAttribute(self, k, v) self._attr[k] = v end
  function m.GetAttribute(self, k) return self._attr[k] end
  function m.Show(self) self._hidden = false local was = self._shown self._shown = true if not was and self._scripts.OnShow then self._scripts.OnShow(self) end end
  function m.Hide(self) self._hidden = true local was = self._shown self._shown = false if was and self._scripts.OnHide then self._scripts.OnHide(self) end end
  function m.IsShown(self) return self._shown end
  function m.CreateTexture(self) return New("Texture", self) end
  function m.CreateFontString(self, name, layer, font) return New("FontString", self, nil, font) end
  return setmetatable(o, { __index = function(_, k) return m[k] or function() end end })
end
function CreateFrame(kind, name, parent, template)
  local f = New(kind, parent, template) f._name = name or ""
  if name then _G[name] = f end
  return f
end
UIParent = New("UIParent") UIParent.GetWidth = function() return 1920 end UIParent.GetHeight = function() return 1080 end
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) PRINTED[#PRINTED + 1] = m end }
function print(m) PRINTED[#PRINTED + 1] = m end
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
function Ambiguate(n) return (n:gsub("%-.*$", "")) end
function UnitName(u) if u == "player" then return "Me" end return UNITNAMES and UNITNAMES[u] end
GROUP = {}
function IsInGroup() return next(GROUP) ~= nil end
function IsInRaid() return false end
function UnitIsGroupLeader() return true end
function GetNumGroupMembers() local n = 1 for _ in pairs(GROUP) do n = n + 1 end return n end
function UnitInParty(n) return GROUP[n] ~= nil end
function UnitInRaid() return nil end
function UnitIsAFK() return false end
function UnitExists() return false end
function UnitIsVisible() return false end
function InCombatLockdown() return false end
C_PartyInfo = { InviteUnit = function(n) INVITED[#INVITED + 1] = n end }
function hooksecurefunc() end
function SendChatMessage(m, ch, _, to) SENT[#SENT + 1] = { m = m, ch = ch, to = to } end
function GetTargetTradeMoney() return 0 end
function InitiateTrade(u) TRADES[#TRADES + 1] = u end
SlashCmdList = {}
NUM_CHAT_WINDOWS = 10
