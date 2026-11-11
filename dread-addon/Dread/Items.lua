-- Gear: five slots, two rarities that matter (magic = 1-2 bonuses, rare = 3-4), bonuses that grow with the item level.
-- Pure rules, no WoW API. Names are plain WoW-flavoured words (no Diablo II names).
local _, ns = ...
local Items = {}
ns.Items = Items

-- What an item is (its type), and where it goes on you. Two rings: a ring goes to the free ring place, or swaps ring 1.
Items.SLOTS = { "weapon", "head", "body", "ring", "amulet", "gloves", "belt", "boots" }
Items.GEAR_SLOTS = { "head", "amulet", "weapon", "body", "gloves", "belt", "boots", "ring1", "ring2" }
Items.SLOT_LABEL = { weapon = "Weapon", head = "Helm", body = "Armor", ring = "Ring", amulet = "Amulet", gloves = "Gloves", belt = "Belt", boots = "Boots",
                     ring1 = "Ring", ring2 = "Ring" }
Items.BASES = {
  weapon = { "Staff", "Wand", "Scepter", "Rod" }, head = { "Hood", "Cowl", "Circlet" },
  body = { "Robe", "Vestment", "Tunic" }, ring = { "Ring", "Band", "Signet" }, amulet = { "Amulet", "Pendant", "Charm" },
  gloves = { "Gloves", "Mitts", "Gauntlets" }, belt = { "Belt", "Sash", "Cord" }, boots = { "Boots", "Sandals", "Treads" },
}

-- The place on you that an item of this type goes to: its own, or for a ring the empty ring place (else ring 1).
function Items.place(gear, item_slot)
  if item_slot ~= "ring" then return item_slot end
  if not gear.ring1 then return "ring1" end
  if not gear.ring2 then return "ring2" end
  return "ring1"
end

-- Which item types may sit in a place.
function Items.fits(place, item_slot)
  return place == item_slot or ((place == "ring1" or place == "ring2") and item_slot == "ring")
end

-- stat id -> { label, per_item_lo, per_item_hi at item level 1, growth per item level, weight for "is it better", suffix, slots allowed (nil = any) }
Items.STATS = {
  life            = { "Life",                      4, 8,  1.2,  1.0, "",  { "head", "body", "ring", "amulet", "gloves", "belt", "boots" } },
  mana            = { "Mana",                      3, 6,  0.8,  0.7, "",  { "head", "body", "ring", "amulet", "belt", "boots" } },
  dmg_pct         = { "Spell damage",              3, 6,  0.5,  3.0, "%", { "weapon", "ring", "amulet", "gloves" } },
  fire_pct        = { "Fire damage",               4, 8,  0.6,  2.0, "%", { "weapon", "amulet" } },
  cold_pct        = { "Cold damage",               4, 8,  0.6,  2.0, "%", { "weapon", "amulet" } },
  lightning_pct   = { "Lightning damage",          4, 8,  0.6,  2.0, "%", { "weapon", "amulet" } },
  mana_regen_pct  = { "Mana regeneration",         5, 10, 0.5,  1.5, "%", { "head", "ring", "gloves", "belt" } },
  -- attributes (any slot). What they do is in Combat.derived: int = mana and spell damage, vit = life, str = wand damage, dex = speed.
  int             = { "Intelligence",              2, 4,  0.4,  3.0, "",  nil },
  vit             = { "Vitality",                  2, 4,  0.4,  3.0, "",  nil },
  str             = { "Strength",                  2, 4,  0.4,  1.0, "",  nil },
  dex             = { "Dexterity",                 2, 4,  0.4,  1.0, "",  nil },
}
Items.STAT_ORDER = { "life", "mana", "dmg_pct", "fire_pct", "cold_pct", "lightning_pct", "mana_regen_pct", "int", "vit", "str", "dex" }
Items.BAG_MAX = 16

-- Four tiers. common: one small bonus. magic: 1-2. rare: 3-4. unique: 4-5, a bit bigger, and a name of its own.
Items.RARITIES = { "common", "magic", "rare", "unique" }
Items.RANK = { common = 1, magic = 2, rare = 3, unique = 4 }
Items.AFFIXES = { common = { 1, 1 }, magic = { 1, 2 }, rare = { 3, 4 }, unique = { 4, 5 } }
Items.POWER = { common = 0.7, magic = 1, rare = 1, unique = 1.25 }            -- multiplier on each bonus
-- Chance an ordinary drop is each tier, as a running total: under .01 unique, under .10 rare, under .45 magic, else common.
Items.CUT = { unique = 0.01, rare = 0.10, magic = 0.45 }
Items.BOSS_UNIQUE = 0.25                        -- a boss drop is rare, or this often unique
Items.UNIQUE_NAMES = {
  weapon = { "Emberthorn Staff", "Frostglass Rod", "Stormcaller's Wand", "Gloamwood Scepter" },
  head = { "Crown of the Tides", "Ashen Cowl", "Moonveil Circlet" },
  body = { "Dawnweave Robe", "Embershroud", "Gravewind Vestment" },
  ring = { "Seal of Cinders", "Band of the Deep", "Stormglass Ring" },
  amulet = { "Heart of the Moor", "Starfall Pendant", "Wyrmtooth Charm" },
  gloves = { "Cinderpalm Mitts", "Rimeclasp Gloves" }, belt = { "Girdle of Tides", "Thornwoven Sash" }, boots = { "Windstep Treads", "Marshwalkers" },
}
Items.MAX_ILVL = 99

local function allowed(stat, slot)
  local list = Items.STATS[stat][7]
  if not list then return true end
  for _, s in ipairs(list) do if s == slot then return true end end
  return false
end

local function irand(rng, lo, hi) return lo + math.floor(rng() * (hi - lo + 1)) end

-- Roll one item. `rng` is the world's seeded generator. `force`: nil = a normal drop, "boss" = rare (sometimes unique), or a tier name.
function Items.roll(rng, ilvl, force)
  ilvl = math.max(1, math.min(Items.MAX_ILVL, math.floor(ilvl or 1)))
  local slot = Items.SLOTS[irand(rng, 1, #Items.SLOTS)]
  local tier = force
  if force == true then tier = "rare" end
  if force == "boss" then tier = (rng() < Items.BOSS_UNIQUE) and "unique" or "rare"
  elseif not Items.RANK[tier or ""] then
    local r = rng()
    tier = (r < Items.CUT.unique and "unique") or (r < Items.CUT.rare and "rare") or (r < Items.CUT.magic and "magic") or "common"
  end
  local range = Items.AFFIXES[tier]
  local want = irand(rng, range[1], range[2])
  local pool = {}
  for _, k in ipairs(Items.STAT_ORDER) do if allowed(k, slot) then pool[#pool + 1] = k end end
  want = math.min(want, #pool)
  local stats = {}
  for _ = 1, want do
    local i = irand(rng, 1, #pool)
    local k = table.remove(pool, i)
    local st = Items.STATS[k]
    stats[k] = math.max(1, math.floor((st[2] + (st[3] - st[2]) * rng() + st[4] * ilvl) * Items.POWER[tier] + 0.5))
  end
  local bases = Items.BASES[slot]
  local item = { slot = slot, rarity = tier, ilvl = ilvl, base = bases[irand(rng, 1, #bases)], stats = stats }
  if tier == "unique" then item.title = Items.UNIQUE_NAMES[slot][irand(rng, 1, #Items.UNIQUE_NAMES[slot])] end
  return item
end

-- A name that says what is on it: "Rare Robe of Life, Intelligence". A unique has its own name.
function Items.name(item)
  if item.rarity == "unique" and item.title then return item.title end
  local parts = {}
  for _, k in ipairs(Items.STAT_ORDER) do if item.stats[k] then parts[#parts + 1] = Items.STATS[k][1] end end
  local tag = ({ common = "Plain ", magic = "Magic ", rare = "Rare " })[item.rarity] or ""
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
  for _, place in ipairs(Items.GEAR_SLOTS) do
    local it = gear and gear[place]
    if it then for k, v in pairs(it.stats) do t[k] = (t[k] or 0) + v end end
  end
  return t
end

-- Put the bag item at `index` on, in `place` (a ring may be sent to ring1 or ring2; otherwise it picks), swapping with what is
-- there; the old item takes the bag place. True if it worked.
function Items.equip(gear, bag, index, place)
  local item = bag[index]
  if not item then return false end
  place = place or Items.place(gear, item.slot)
  if not Items.fits(place, item.slot) then return false end
  local old = gear[place]
  gear[place] = item
  if old then bag[index] = old else table.remove(bag, index) end
  return true
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
        local cap = math.floor((Items.STATS[k][3] + Items.STATS[k][4] * ilvl) * Items.POWER.unique + 0.5)   -- the most any roll can give at that level
        stats[k] = math.min(math.floor(v), cap); n = n + 1
      end
    end
  end
  if n == 0 then return nil end
  local rarity = Items.RANK[raw.rarity or ""] and raw.rarity or "magic"
  local title
  if rarity == "unique" then
    for _, n in ipairs(Items.UNIQUE_NAMES[slot]) do if n == raw.title then title = n end end
    if not title then rarity = "rare" end                                         -- a unique with a name we do not know is just a rare
  end
  return { slot = slot, rarity = rarity, ilvl = ilvl, base = base, stats = stats, title = title }
end

return Items
