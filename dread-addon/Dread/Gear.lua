-- The gear window (I): what you wear and what it adds. Text only; the rules are in Items.lua.
local _, ns = ...
local Gear = {}
ns.Gear = Gear

local frame, text, bag_title

Gear.COLOR = { common = "|cffcccccc", magic = "|cff6f9fff", rare = "|cffffd24a", unique = "|cffff9a2e" }
local COLOR = Gear.COLOR

function Gear.text(gear, p)
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
  if p then
    local d = ns.Combat.derived(p.level, gear)
    out[#out + 1] = ("You:  %d life,  %d mana,  +%d%% spell damage,  +%d%% wand,  +%d%% speed"):format(
      math.floor(d.life + 0.5), math.floor(d.mana + 0.5), math.floor(d.spell_pct + 0.5), math.floor(d.wand_pct + 0.5), math.floor(d.speed_pct + 0.5))
    out[#out + 1] = "|cff888888Intelligence = mana and spell damage. Vitality = life. Strength = wand only. Dexterity = speed.|r"
  end
  return table.concat(out, "\n")
end

local ROWS, ROW_H = 16, 20
local rows, world_ref, slot_btn, rank_btn, shown_idx = {}, nil, nil, nil, {}

local function signed(v, fmt)
  local r = math.floor(v * 10 + 0.5) / 10
  if r == math.floor(r) then r = math.floor(r) end
  return (r > 0 and "|cff55ff55+" or "|cffff6666") .. r .. (fmt or "") .. "|r"
end

local SHOW = { { "life", " life", "" }, { "mana", " mana", "" }, { "spell_pct", "% spell", "%" }, { "wand_pct", "% wand", "%" },
               { "fire_pct", "% fire", "%" }, { "cold_pct", "% cold", "%" }, { "lightning_pct", "% lightning", "%" },
               { "regen_pct", "% regen", "%" }, { "speed_pct", "% speed", "%" } }

-- "+20 mana  +5% spell  -10% wand": what wearing bag item i would change.
function Gear.compare_text(diff)
  local out = {}
  for _, e in ipairs(SHOW) do
    local v = diff[e[1]]
    if v and math.abs(v) >= 0.05 then out[#out + 1] = signed(v, e[2]) end
  end
  return #out > 0 and table.concat(out, "  ") or "|cff888888no change|r"
end

local function change() if Gear.on_change then Gear.on_change() end end

-- Filters for the bag: by slot, and by how good it is. They only change what is listed, never what you own.
Gear.slot_filter, Gear.min_rank = 0, 1                      -- slot_filter 0 = every slot; an index into Items.SLOTS otherwise
function Gear.cycle_slot() Gear.slot_filter = (Gear.slot_filter + 1) % (#ns.Items.SLOTS + 1); return Gear.slot_filter end
function Gear.cycle_rank() Gear.min_rank = Gear.min_rank % #ns.Items.RARITIES + 1; return Gear.min_rank end

-- The bag places that pass the filters, in bag order.
function Gear.visible(bag)
  local out, slot = {}, ns.Items.SLOTS[Gear.slot_filter]
  for i, it in ipairs(bag) do
    if (not slot or it.slot == slot) and ns.Items.RANK[it.rarity] >= Gear.min_rank then out[#out + 1] = i end
  end
  return out
end

local function filter_labels()
  return "Slot: " .. (Gear.slot_filter == 0 and "all" or ns.Items.SLOT_LABEL[ns.Items.SLOTS[Gear.slot_filter]]),
         "Show: " .. (Gear.min_rank == 1 and "everything" or (ns.Items.RARITIES[Gear.min_rank] .. " and better"))
end

local function build()
  frame = CreateFrame("Frame", "DreadGearFrame", UIParent, "BackdropTemplate")
  frame:SetSize(470, 640)
  frame:SetPoint("CENTER", 0, 0)
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
  text:SetPoint("TOPLEFT", 12, -34); text:SetWidth(446); text:SetJustifyH("LEFT")
  bag_title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  bag_title:SetPoint("TOPLEFT", 12, -240)
  slot_btn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
  slot_btn:SetSize(120, 20); slot_btn:SetPoint("TOPLEFT", 238, -236)
  slot_btn:SetScript("OnClick", function() Gear.cycle_slot(); Gear.refresh(world_ref) end)
  rank_btn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
  rank_btn:SetSize(150, 20); rank_btn:SetPoint("TOPLEFT", 362, -236)
  rank_btn:SetScript("OnClick", function() Gear.cycle_rank(); Gear.refresh(world_ref) end)
  for i = 1, ROWS do
    local y = -272 - (i - 1) * (ROW_H + 2)
    local eq = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    eq:SetSize(46, ROW_H); eq:SetText("Wear"); eq:SetPoint("TOPLEFT", 12, y)
    eq:SetScript("OnClick", function() if world_ref and shown_idx[i] and ns.Combat.equip(world_ref, shown_idx[i]) then Gear.refresh(world_ref); change() end end)
    local tr = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    tr:SetSize(24, ROW_H); tr:SetText("x"); tr:SetPoint("TOPLEFT", 62, y)
    tr:SetScript("OnClick", function() if world_ref and shown_idx[i] and ns.Combat.trash(world_ref, shown_idx[i]) then Gear.refresh(world_ref); change() end end)
    local fs = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    fs:SetPoint("TOPLEFT", 94, y - 4); fs:SetWidth(370); fs:SetJustifyH("LEFT")
    rows[i] = { eq = eq, tr = tr, fs = fs }
  end
end

function Gear.refresh(world)
  world_ref = world
  if not (frame and frame:IsShown()) then return end
  local p = world.player
  text:SetText(Gear.text(p.gear, p))
  local idx = Gear.visible(p.bag)
  shown_idx = idx
  bag_title:SetText("Bag " .. #p.bag .. "/" .. ns.Items.BAG_MAX .. (#idx < #p.bag and ("  (showing " .. #idx .. ")") or ""))
  local a, b = filter_labels()
  slot_btn:SetText(a); rank_btn:SetText(b)
  for i = 1, ROWS do
    local r, bi = rows[i], idx[i]
    local it = bi and p.bag[bi]
    if it then
      r.eq:Show(); r.tr:Show()
      r.fs:SetText((COLOR[it.rarity] or "") .. ns.Items.name(it) .. "|r  " .. Gear.compare_text(ns.Combat.compare(world, bi)))
    else
      r.eq:Hide(); r.tr:Hide(); r.fs:SetText("")
    end
  end
end

function Gear.toggle(world)
  if not frame then build() end
  if frame:IsShown() then frame:Hide() else frame:Show(); Gear.refresh(world) end
  return frame:IsShown()
end
