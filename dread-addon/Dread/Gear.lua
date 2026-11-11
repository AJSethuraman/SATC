-- The gear window (I): what you wear and what it adds. Text only; the rules are in Items.lua.
local _, ns = ...
local Gear = {}
ns.Gear = Gear

local frame, text

local COLOR = { magic = "|cff6f9fff", rare = "|cffffd24a" }

function Gear.text(gear)
  local Items = ns.Items
  local out = {}
  for _, slot in ipairs(Items.SLOTS) do
    local it = gear and gear[slot]
    if it then
      out[#out + 1] = Items.SLOT_LABEL[slot] .. ":  " .. (COLOR[it.rarity] or "") .. Items.name(it) .. "|r  (level " .. it.ilvl .. ")"
      for _, l in ipairs(Items.lines(it)) do out[#out + 1] = "      " .. l end
    else
      out[#out + 1] = Items.SLOT_LABEL[slot] .. ":  |cff888888nothing|r"
    end
  end
  local t, tot = Items.totals(gear), {}
  for _, k in ipairs(Items.STAT_ORDER) do
    if t[k] then tot[#tot + 1] = "+" .. t[k] .. Items.STATS[k][6] .. " " .. Items.STATS[k][1] end
  end
  out[#out + 1] = ""
  out[#out + 1] = "Total:  " .. (#tot > 0 and table.concat(tot, ",  ") or "nothing yet. Kill things and walk over what drops.")
  return table.concat(out, "\n")
end

local function build()
  frame = CreateFrame("Frame", "DreadGearFrame", UIParent, "BackdropTemplate")
  frame:SetSize(360, 330)
  frame:SetPoint("CENTER", 0, 40)
  frame:SetFrameStrata("DIALOG")
  if frame.SetBackdrop then frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 }) end
  if frame.SetBackdropColor then frame:SetBackdropColor(0, 0, 0, 0.94) end
  if frame.SetBackdropBorderColor then frame:SetBackdropBorderColor(0.6, 0.1, 0.1, 1) end
  frame:SetMovable(true); frame:EnableMouse(true)
  frame:RegisterForDrag("LeftButton")
  frame:SetScript("OnDragStart", frame.StartMoving)
  frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
  local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  title:SetPoint("TOPLEFT", 12, -10); title:SetText("Gear (I to close)")
  text = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
  text:SetPoint("TOPLEFT", 12, -34); text:SetWidth(336); text:SetJustifyH("LEFT")
end

function Gear.refresh(gear)
  if frame and frame:IsShown() then text:SetText(Gear.text(gear)) end
end

function Gear.toggle(gear)
  if not frame then build() end
  if frame:IsShown() then frame:Hide() else text:SetText(Gear.text(gear)); frame:Show() end
  return frame:IsShown()
end
