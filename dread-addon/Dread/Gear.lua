-- The gear window (I): what you wear in its places on you, the bag, and what each bag item would change.
-- Square icon cells, edged in the item's tier colour. Click a worn one to take it off; click a bag one to wear it, shift-click to
-- throw it away; hover anything to read it. The rules are in Items.lua and Combat.lua.
local _, ns = ...
local Gear = {}
ns.Gear = Gear

local frame, summary, detail, bag_title, slot_btn, rank_btn
local doll, bagcells, shown_idx, world_ref = {}, {}, {}, nil
Gear.doll, Gear.bagcells = doll, bagcells                 -- for tests: the cells by place, and the bag cells in order

Gear.COLOR = { common = "|cffcccccc", magic = "|cff6f9fff", rare = "|cffffd24a", unique = "|cffff9a2e" }
local COLOR = Gear.COLOR
local BORDER = { common = { 0.62, 0.62, 0.62 }, magic = { 0.4, 0.55, 1 }, rare = { 1, 0.82, 0.25 }, unique = { 1, 0.6, 0.15 }, empty = { 0.28, 0.24, 0.22 } }
Gear.BORDER = BORDER

-- What each kind of item looks like (WoW's own icons).
Gear.ICON = { weapon = "INV_Staff_01", head = "INV_Helmet_01", body = "INV_Chest_Cloth_01", ring = "INV_Jewelry_Ring_01", amulet = "INV_Jewelry_Necklace_01",
              gloves = "INV_Gauntlets_01", belt = "INV_Belt_01", boots = "INV_Boots_01" }
local function icon_path(item_slot) return "Interface\\Icons\\" .. (Gear.ICON[item_slot] or "INV_Misc_QuestionMark") end

-- Where each place sits on the doll (column 0-4, row 0-2), the way Diablo II lays it out: helm and amulet on top, weapon and armor
-- in the middle, then gloves, ring, belt, ring, boots across the bottom.
Gear.LAYOUT = {
  head = { 2, 0 }, amulet = { 3, 0 }, weapon = { 0, 1 }, body = { 2, 1 },
  gloves = { 0, 2 }, ring1 = { 1, 2 }, belt = { 2, 2 }, ring2 = { 3, 2 }, boots = { 4, 2 },
}
local CELL, GAP, DOLL_X, DOLL_Y = 64, 6, 22, 36
local BAG_CELL, BAG_GAP, BAG_COLS, BAG_X, BAG_Y = 48, 4, 8, 22, 332

-- Everything one item says, one line each ("+12 Life"), headed by its name and level.
function Gear.item_text(it)
  local Items = ns.Items
  local out = { (COLOR[it.rarity] or "") .. Items.name(it) .. "|r  (" .. it.rarity .. ", level " .. it.ilvl .. ")" }
  for _, l in ipairs(Items.lines(it)) do out[#out + 1] = "   " .. l end
  return table.concat(out, "\n")
end

-- The totals under the doll: what the gear adds up to, and what that makes of you.
function Gear.text(gear, p)
  local Items = ns.Items
  local t, tot, out = Items.totals(gear), {}, {}
  for _, k in ipairs(Items.STAT_ORDER) do
    if t[k] then tot[#tot + 1] = "+" .. t[k] .. Items.STATS[k][6] .. " " .. Items.STATS[k][1] end
  end
  out[#out + 1] = "Total:  " .. (#tot > 0 and table.concat(tot, ",  ") or "nothing yet. Kill things and walk over what drops.")
  if p then
    local d = ns.Combat.derived(p.level, gear)
    out[#out + 1] = ("You:  %d life,  %d mana,  +%d%% spell damage,  +%d%% wand,  +%d%% speed"):format(
      math.floor(d.life + 0.5), math.floor(d.mana + 0.5), math.floor(d.spell_pct + 0.5), math.floor(d.wand_pct + 0.5), math.floor(d.speed_pct + 0.5))
    out[#out + 1] = "|cff888888Intelligence = mana and spell damage. Vitality = life. Strength = wand only. Dexterity = speed.|r"
  end
  return table.concat(out, "\n")
end

local function signed(v, fmt)
  local r = math.floor(v * 10 + 0.5) / 10
  if r == math.floor(r) then r = math.floor(r) end
  return (r > 0 and "|cff55ff55+" or "|cffff6666") .. r .. (fmt or "") .. "|r"
end

local SHOW = { { "life", " life" }, { "mana", " mana" }, { "spell_pct", "% spell" }, { "wand_pct", "% wand" },
               { "fire_pct", "% fire" }, { "cold_pct", "% cold" }, { "lightning_pct", "% lightning" },
               { "regen_pct", "% regen" }, { "speed_pct", "% speed" } }

-- "+20 mana  +5% spell  -10% wand": what wearing a bag item would change.
function Gear.compare_text(diff)
  local out = {}
  for _, e in ipairs(SHOW) do
    local v = diff[e[1]]
    if v and math.abs(v) >= 0.05 then out[#out + 1] = signed(v, e[2]) end
  end
  return #out > 0 and table.concat(out, "  ") or "|cff888888no change|r"
end

local function change() if Gear.on_change then Gear.on_change() end end

-- Filters for the bag: by type, and by how good it is. They only change what is listed, never what you own.
Gear.slot_filter, Gear.min_rank = 0, 1                      -- slot_filter 0 = every type; an index into Items.SLOTS otherwise
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
  return "Type: " .. (Gear.slot_filter == 0 and "all" or ns.Items.SLOT_LABEL[ns.Items.SLOTS[Gear.slot_filter]]),
         "Show: " .. (Gear.min_rank == 1 and "everything" or (ns.Items.RARITIES[Gear.min_rank] .. " and better"))
end

-- One square: a dark box with a coloured edge and an icon in it.
local function make_cell(parent, size)
  local c = CreateFrame("Button", nil, parent, "BackdropTemplate")
  c:SetSize(size, size)
  if c.SetBackdrop then c:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 2 }) end
  if c.SetBackdropColor then c:SetBackdropColor(0.06, 0.05, 0.05, 1) end
  c.icon = c:CreateTexture(nil, "ARTWORK")
  c.icon:SetPoint("TOPLEFT", 4, -4); c.icon:SetPoint("BOTTOMRIGHT", -4, 4)
  c.label = c:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
  c.label:SetPoint("BOTTOM", 0, 3)
  return c
end

-- Fill a cell with an item (or show it empty): icon, edge colour, and what it holds.
local function paint(c, item, empty_icon, empty_label)
  c.item = item
  local col = item and BORDER[item.rarity] or BORDER.empty
  if c.SetBackdropBorderColor then c:SetBackdropBorderColor(col[1], col[2], col[3], 1) end
  c.border = col
  if item then
    c.icon:SetTexture(icon_path(item.slot)); c.icon:SetDesaturated(false); c.icon:SetAlpha(1); c.icon:SetVertexColor(1, 1, 1)
    c.label:SetText("")
  elseif empty_icon then
    c.icon:SetTexture(icon_path(empty_icon)); c.icon:SetDesaturated(true); c.icon:SetAlpha(0.25); c.icon:SetVertexColor(1, 1, 1)
    c.label:SetText(empty_label or "")
  else
    c.icon:SetTexture(nil); c.label:SetText("")
  end
end

local function build()
  frame = CreateFrame("Frame", "DreadGearFrame", UIParent, "BackdropTemplate")
  frame:SetSize(430, 560)
  frame:SetPoint("CENTER", 0, 0)
  frame:SetFrameStrata("DIALOG")
  if frame.SetBackdrop then frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 2 }) end
  if frame.SetBackdropColor then frame:SetBackdropColor(0.04, 0.03, 0.03, 0.97) end
  if frame.SetBackdropBorderColor then frame:SetBackdropBorderColor(0.55, 0.45, 0.2, 1) end
  frame:SetMovable(true); frame:EnableMouse(true)
  frame:RegisterForDrag("LeftButton")
  frame:SetScript("OnDragStart", frame.StartMoving)
  frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
  local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
  title:SetPoint("TOP", 0, -10); title:SetText("Equipment")
  local close = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
  close:SetSize(22, 22); close:SetPoint("TOPRIGHT", -8, -8); close:SetText("X")
  close:SetScript("OnClick", function() frame:Hide() end)
  for _, place in ipairs(ns.Items.GEAR_SLOTS) do
    local col, row = Gear.LAYOUT[place][1], Gear.LAYOUT[place][2]
    local c = make_cell(frame, CELL)
    c:SetPoint("TOPLEFT", DOLL_X + col * (CELL + GAP), -(DOLL_Y + row * (CELL + GAP)))
    c.place = place
    c:SetScript("OnClick", function() if world_ref and ns.Combat.unequip(world_ref, place) then Gear.refresh(world_ref); if Gear.on_change then Gear.on_change() end end end)
    c:SetScript("OnEnter", function(self) if self.item then detail:SetText(Gear.item_text(self.item) .. "\n|cff888888click to take it off|r") end end)
    c:SetScript("OnLeave", function() detail:SetText(Gear.hint) end)
    doll[place] = c
  end
  summary = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
  summary:SetPoint("TOPLEFT", DOLL_X, -(DOLL_Y + 3 * (CELL + GAP) + 6)); summary:SetWidth(386); summary:SetJustifyH("LEFT")
  bag_title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  bag_title:SetPoint("TOPLEFT", DOLL_X, -(BAG_Y - 24))
  slot_btn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
  slot_btn:SetSize(110, 20); slot_btn:SetPoint("TOPRIGHT", -150, -(BAG_Y - 28))
  slot_btn:SetScript("OnClick", function() Gear.cycle_slot(); Gear.refresh(world_ref) end)
  rank_btn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
  rank_btn:SetSize(128, 20); rank_btn:SetPoint("TOPRIGHT", -16, -(BAG_Y - 28))
  rank_btn:SetScript("OnClick", function() Gear.cycle_rank(); Gear.refresh(world_ref) end)
  for i = 1, ns.Items.BAG_MAX do
    local col, row = (i - 1) % BAG_COLS, math.floor((i - 1) / BAG_COLS)
    local c = make_cell(frame, BAG_CELL)
    c:SetPoint("TOPLEFT", BAG_X + col * (BAG_CELL + BAG_GAP), -(BAG_Y + row * (BAG_CELL + BAG_GAP)))
    c:SetScript("OnClick", function(self)
      local bi = shown_idx[i]
      if not (world_ref and bi) then return end
      local done
      if IsShiftKeyDown and IsShiftKeyDown() then done = ns.Combat.trash(world_ref, bi) else done = ns.Combat.equip(world_ref, bi) end
      if done then Gear.refresh(world_ref); if Gear.on_change then Gear.on_change() end end
    end)
    c:SetScript("OnEnter", function(self)
      local bi = shown_idx[i]
      if bi and world_ref then
        detail:SetText(Gear.item_text(self.item) .. "\n\nIf you wear it:  " .. Gear.compare_text(ns.Combat.compare(world_ref, bi)) .. "\n|cff888888click to wear, shift-click to throw away|r")
      end
    end)
    c:SetScript("OnLeave", function() detail:SetText(Gear.hint) end)
    bagcells[i] = c
  end
  detail = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
  detail:SetPoint("TOPLEFT", DOLL_X, -(BAG_Y + 2 * (BAG_CELL + BAG_GAP) + 10)); detail:SetWidth(386); detail:SetJustifyH("LEFT"); detail:SetJustifyV("TOP")
  detail:SetText(Gear.hint)
end

Gear.hint = "|cff888888Hover anything to read it. Click a bag item to wear it, shift-click to throw it away. Click a worn item to take it off.|r"

function Gear.refresh(world)
  world_ref = world
  if not (frame and frame:IsShown()) then return end
  local p = world.player
  for place, c in pairs(doll) do
    local kind = (place == "ring1" or place == "ring2") and "ring" or place
    paint(c, p.gear[place], kind, ns.Items.SLOT_LABEL[place])
  end
  summary:SetText(Gear.text(p.gear, p))
  local idx = Gear.visible(p.bag)
  shown_idx = idx
  bag_title:SetText("Bag " .. #p.bag .. "/" .. ns.Items.BAG_MAX .. (#idx < #p.bag and ("  (showing " .. #idx .. ")") or ""))
  local a, b = filter_labels()
  slot_btn:SetText(a); rank_btn:SetText(b)
  for i = 1, ns.Items.BAG_MAX do
    local c, bi = bagcells[i], idx[i]
    paint(c, bi and p.bag[bi] or nil, nil)
  end
  detail:SetText(Gear.hint)
end

function Gear.toggle(world)
  if not frame then build() end
  if frame:IsShown() then frame:Hide() else frame:Show(); Gear.refresh(world) end
  return frame:IsShown()
end
