-- Minimal WoW API stubs so ServiceInviter.lua can load and be driven offline.
CLOCK = 1000
function GetTime() return CLOCK end
function time() return math.floor(CLOCK) end
SENT, INVITED, TRADES = {}, {}, {}
local function Stub()
  local o = { _scripts = {}, _attr = {}, _shown = false, _text = "", _checked = false }
  return setmetatable(o, { __index = function(t, k)
    local m = {
      SetScript = function(self, n, fn) self._scripts[n] = fn end,
      HookScript = function(self, n, fn) self._scripts[n] = fn end,
      GetScript = function(self, n) return self._scripts[n] end,
      CreateTexture = function() return Stub() end,
      CreateFontString = function() return Stub() end,
      Show = function(self) self._shown = true if self._scripts.OnShow then self._scripts.OnShow(self) end end,
      Hide = function(self) local was = self._shown self._shown = false if was and self._scripts.OnHide then self._scripts.OnHide(self) end end,
      IsShown = function(self) return self._shown end,
      SetText = function(self, s) self._text = s end,
      GetText = function(self) return self._text end,
      SetChecked = function(self, v) self._checked = v and true or false end,
      GetChecked = function(self) return self._checked end,
      SetAttribute = function(self, k2, v) self._attr[k2] = v end,
      GetAttribute = function(self, k2) return self._attr[k2] end,
      GetFont = function() return "font", 12, "" end,
      Disable = function(self) self._disabled = true end,
      Enable = function(self) self._disabled = false end,
      IsEnabled = function(self) return not self._disabled end,
      SetFontObject = function(self, f) self._font = f end,
    }
    return m[k] or function() end
  end })
end
FRAMES = {}
function CreateFrame(kind, name) local f = Stub() FRAMES[#FRAMES + 1] = f if name then _G[name] = f end return f end
UIParent = Stub() UIParent.GetWidth = function() return 1920 end UIParent.GetHeight = function() return 1080 end
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) PRINTED[#PRINTED + 1] = m end }
PRINTED = {}
function print(m) PRINTED[#PRINTED + 1] = m end
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
function Ambiguate(n) return (n:gsub("%-.*$", "")) end
PLAYER = "Me"
function UnitName(u) if u == "player" then return PLAYER end return UNITNAMES and UNITNAMES[u] end
GROUP = {}
function IsInGroup() return next(GROUP) ~= nil end
function IsInRaid() return false end
function UnitIsGroupLeader() return true end
function GetNumGroupMembers() local n = 1 for _ in pairs(GROUP) do n = n + 1 end return n end
function UnitInParty(n) return GROUP[n] ~= nil end
function UnitInRaid() return nil end
function UnitIsAFK() return false end
function UnitExists() return false end
function InCombatLockdown() return false end
C_PartyInfo = { InviteUnit = function(n) INVITED[#INVITED + 1] = n end }
function hooksecurefunc(t, k, fn) if type(t) == "string" then return end local orig = t[k] t[k] = function(...) orig(...) fn(...) end end
function SendChatMessage(m, ch, _, to) SENT[#SENT + 1] = { m = m, ch = ch, to = to } end
function GetTargetTradeMoney() return TRADEMONEY or 0 end
function InitiateTrade(u) TRADES[#TRADES + 1] = u end
SlashCmdList = {}
NUM_CHAT_WINDOWS = 10
function UnitIsVisible() return false end
function SetBindingClick() return true end
function SaveBindings() end
function GetCurrentBindingSet() return 1 end
