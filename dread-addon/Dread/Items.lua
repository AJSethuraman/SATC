-- Gear: five slots, two rarities that matter (magic = 1-2 bonuses, rare = 3-4), bonuses that grow with the item level.
-- Pure rules, no WoW API. Names are plain WoW-flavoured words (no Diablo II names).
local _, ns = ...
local Items = {}
ns.Items = Items

Items.SLOTS = { "weapon", "head", "body", "ring", "amulet" }
Items.SLOT_LABEL = { weapon = "Weapon", head = "Head", body = "Body", ring = "Ring", amulet = "Amulet" }
Items.BASES = {
  weapon = { "Staff", "Wand", "Scepter", "Rod" }, head = { "Hood", "Cowl", "Circlet" },
  body = { "Robe", "Vestment", "Tunic" }, ring = { "Ring", "Band", "Signet" }, amulet = { "Amulet", "Pendant", "Charm" },
}

-- stat id -> { label, per_item_lo, per_item_hi at item level 1, growth per item level, weight for "is it better", suffix, slots allowed (nil = any) }
Items.STATS = {
  life            = { "Life",                      4, 8,  1.2,  1.0, "",  { "head", "body", "ring", "amulet" } },
  mana            = { "Mana",                      3, 6,  0.8,  0.7, "",  { "head", "body", "ring", "amulet" } },
  dmg_pct         = { "Spell damage",              3, 6,  0.5,  3.0, "%", { "weapon", "ring", "amulet" } },
  fire_pct        = { "Fire damage",               4, 8,  0.6,  2.0, "%", { "weapon", "amulet" } },
  cold_pct        = { "Cold damage",               4, 8,  0.6,  2.0, "%", { "weapon", "amulet" } },
  lightning_pct   = { "Lightning damage",          4, 8,  0.6,  2.0, "%", { "weapon", "amulet" } },
  mana_regen_pct  = { "Mana regeneration",         5, 10, 0.5,  1.5, "%", { "head", "ring" } },
}
Items.STAT_ORDER = { "life", "mana", "dmg_pct", "fire_pct", "cold_pct", "lightning_pct", "mana_regen_pct" }

Items.MAGIC_AFFIXES, Items.RARE_AFFIXES = { 1, 2 }, { 3, 4 }
Items.RARE_SHARE = 0.2                          -- of ordinary drops; bosses always drop rare
Items.MAX_ILVL = 99

local function allowed(stat, slot)
  local list = Items.STATS[stat][7]
  if not list then return true end
  for _, s in ipairs(list) do if s == slot then return true end end
  return false
end

local function irand(rng, lo, hi) return lo + math.floor(rng() * (hi - lo + 1)) end

-- Roll one item. `rng` is the world's seeded generator; `rare` forces rare.
function Items.roll(rng, ilvl, rare)
  ilvl = math.max(1, math.min(Items.MAX_ILVL, math.floor(ilvl or 1)))
  local slot = Items.SLOTS[irand(rng, 1, #Items.SLOTS)]
  local is_rare = rare or rng() < Items.RARE_SHARE
  local range = is_rare and Items.RARE_AFFIXES or Items.MAGIC_AFFIXES
  local want = irand(rng, range[1], range[2])
  local pool = {}
  for _, k in ipairs(Items.STAT_ORDER) do if allowed(k, slot) then pool[#pool + 1] = k end end
  want = math.min(want, #pool)
  local stats = {}
  for _ = 1, want do
    local i = irand(rng, 1, #pool)
    local k = table.remove(pool, i)
    local s = Items.STATS[k]
    stats[k] = math.floor(s[2] + (s[3] - s[2]) * rng() + s[4] * ilvl + 0.5)
  end
  local bases = Items.BASES[slot]
  return { slot = slot, rarity = is_rare and "rare" or "magic", ilvl = ilvl, base = bases[irand(rng, 1, #bases)], stats = stats }
end

function Items.score(item)
  local total = 0
  for k, v in pairs(item.stats) do total = total + v * Items.STATS[k][5] end
  return total
end

-- A name that says what is on it: "Rare Robe of Life and Mana".
function Items.name(item)
  local parts = {}
  for _, k in ipairs(Items.STAT_ORDER) do if item.stats[k] then parts[#parts + 1] = Items.STATS[k][1] end end
  local tag = (item.rarity == "rare") and "Rare " or "Magic "
  if #parts == 0 then return tag .. item.base end
  return tag .. item.base .. " of " .. table.concat(parts, ", ", 1, math.min(2, #parts)) .. (#parts > 2 and " & more" or "")
end

function Items.lines(item)
  local out = {}
  for _, k in ipairs(Items.STAT_ORDER) do
    local v = item.stats[k]
    if v then out[#out + 1] = "+" .. v .. Items.STATS[k][6] .. " " .. Items.STATS[k][1] end
  end
  return out
end

-- Add up what the worn items give. gear: slot -> item.
function Items.totals(gear)
  local t = {}
  for _, slot in ipairs(Items.SLOTS) do
    local it = gear and gear[slot]
    if it then for k, v in pairs(it.stats) do t[k] = (t[k] or 0) + v end end
  end
  return t
end

-- Wear it if it beats what is in that slot. Returns true/false, and the item that was replaced (if any).
function Items.consider(gear, item)
  local cur = gear[item.slot]
  if cur and Items.score(cur) >= Items.score(item) then return false, nil end
  gear[item.slot] = item
  return true, cur
end

-- Untrusted data (SavedVariables): rebuild a clean item or return nil. Unknown stats and impossible numbers are dropped.
function Items.clean(raw)
  if type(raw) ~= "table" then return nil end
  local slot = raw.slot
  local ok = false
  for _, s in ipairs(Items.SLOTS) do if s == slot then ok = true end end
  if not ok then return nil end
  local bases, base = Items.BASES[slot], nil
  for _, b in ipairs(bases) do if b == raw.base then base = b end end
  if not base then return nil end
  local ilvl = tonumber(raw.ilvl)
  if not ilvl then return nil end
  ilvl = math.max(1, math.min(Items.MAX_ILVL, math.floor(ilvl)))
  local stats, n = {}, 0
  if type(raw.stats) == "table" then
    for _, k in ipairs(Items.STAT_ORDER) do
      local v = raw.stats[k]
      if type(v) == "number" and v >= 1 and allowed(k, slot) then
        local cap = math.floor(Items.STATS[k][3] + Items.STATS[k][4] * ilvl + 0.5)    -- the most a roll can give at that level
        stats[k] = math.min(math.floor(v), cap); n = n + 1
      end
    end
  end
  if n == 0 then return nil end
  return { slot = slot, rarity = (raw.rarity == "rare") and "rare" or "magic", ilvl = ilvl, base = base, stats = stats }
end

return Items
