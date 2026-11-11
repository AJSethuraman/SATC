-- The fight: a player, monsters and spells moving through an area. Pure Lua, no WoW calls.
-- Damage, mana and resists all come from Tree.lua, so spending a point changes what happens here.
--
-- Spells that can be cast are the ones with an entry in Combat.SHAPES. Anything else is refused with
-- "not implemented yet" rather than silently doing nothing.
local _, ns = ...
ns = ns or {}

local Combat = {}
ns.Combat = Combat

local Skills, Tree, Sim, Items = ns.Skills, ns.Tree, ns.Sim, ns.Items

-- bolt: flies from the player toward the target point and hits the first monster in its path
-- aoe : explodes where it lands (at = "target") or around the player (at = "self"), hitting all within `radius`
Combat.SHAPES = {
  scorch         = { shape = "bolt", speed = 320, range = 420, radius = 10 },
  frostbolt      = { shape = "bolt", speed = 300, range = 420, radius = 10 },
  ice_lance      = { shape = "bolt", speed = 420, range = 460, radius = 8 },
  arcing_bolts   = { shape = "volley", count = 3, spread = 0.22, speed = 380, range = 380, radius = 8 },
  lightning_bolt = { shape = "bolt", speed = 700, range = 520, radius = 8 },
  chain_lightning = { shape = "bolt", speed = 700, range = 520, radius = 8, chain = 3, chain_range = 150 },
  fireball       = { shape = "aoe", at = "target", radius = 55, speed = 300, range = 440 },
  glacial_spike  = { shape = "aoe", at = "target", radius = 50, speed = 340, range = 440 },
  frost_nova     = { shape = "aoe", at = "self", radius = 90, chill_pct = 40 },
  thunder_nova   = { shape = "aoe", at = "self", radius = 100 },
  -- the rest of the skills, one behaviour each (see CASTERS below)
  dragons_breath = { shape = "cone", range = 150, half = 0.6, duration = 1.0, tick = 0.2 },
  blazing_speed  = { shape = "trail", duration = 6 },
  flamestrike    = { shape = "zone", range = 440, radius = 70, duration = 4, tick = 0.5 },
  combustion     = { shape = "buff", duration = 10 },
  meteor         = { shape = "delayed", range = 440, delay = 1.0, radius = 85, burn_t = 3 },
  flame_spirit   = { shape = "summon", range = 260, place_range = 200, duration = 15, interval = 0.8 },
  ice_barrier    = { shape = "buff", duration = 15 },
  frost_armor    = { shape = "buff", duration = 20 },
  blizzard       = { shape = "zone", range = 440, radius = 110, duration = 5, tick = 0.4, chill_pct = 35 },
  icicle_cloak   = { shape = "buff", duration = 15 },
  frozen_orb     = { shape = "orb", range = 440, speed = 160, radius = 75, tick = 0.3, scale = 0.35, linger = 0.4 },
  static_shock   = { shape = "static", radius = 130 },
  force_pull     = { shape = "pull", radius = 320, push_radius = 140, push = 90 },
  blink          = { shape = "blink", range = 360 },
  storm_cloud    = { shape = "storm", duration = 8, tick = 0.6, radius = 170 },
  mana_shield    = { shape = "toggle" },
  -- the free basic attack (a mage's wand): no mana, a short cooldown, plain damage that grows with level
  wand           = { shape = "bolt", speed = 450, range = 360, radius = 8 },
}
-- Skills that need no aim: they act on you or on everything around you. The window casts these the moment you press their key.
local SELF_SHAPES = { static = true, pull = true, buff = true, toggle = true, trail = true, storm = true }
function Combat.self_cast(id)
  local sh = Combat.SHAPES[id]
  if not sh or id == "wand" then return false end
  return SELF_SHAPES[sh.shape] == true or (sh.shape == "aoe" and sh.at == "self")
end
Combat.WAND_COOLDOWN = 0.7
function Combat.wand_damage(level) return 2 + level, 4 + 2 * level end

Combat.MANA_REGEN = 0.04          -- fraction of max mana per second, before Evocation
Combat.DROP_CHANCE, Combat.DROP_RESTORE, Combat.PICKUP_RADIUS, Combat.DROP_LIFETIME = 0.18, 0.35, 26, 25
Combat.PLAYER_RADIUS = 10
Combat.CORE = 10                  -- an exploding spell touches with a small core, then the blast spreads
Combat.PLAYER_SPEED = 140
Combat.CHILL_SECONDS, Combat.FREEZE_SECONDS = 3, 2
Combat.MONSTER_REACH, Combat.MONSTER_COOLDOWN = 22, 1.0
Combat.MAX_QUEST_POINTS = 12
Combat.ITEM_CHANCE, Combat.BOSS_ITEMS = 0.12, 2       -- an ordinary kill drops gear one time in eight; a boss always drops two
Combat.MONSTER_LIFE_MULT, Combat.MONSTER_DMG_MULT = 1.3, 1.25   -- area monsters are tougher, so gear is what keeps you ahead


local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end

local function dist(ax, ay, bx, by)
  local dx, dy = ax - bx, ay - by
  return math.sqrt(dx * dx + dy * dy)
end

local function push(ev, w, e) w.events[#w.events + 1] = e end

-- Life and mana before gear, from level alone.
function Combat.base_life(level) return 60 + 6 * (level - 1) end
function Combat.base_mana(level) return 33 + 3 * (level - 1) end

-- Everything gear adds up to, worked out in one place: attributes first (intelligence: +2 mana and +0.5% spell damage each,
-- vitality: +3 life, strength: +1% wand damage, dexterity: +0.3% walking speed), then the plain bonuses on top.
function Combat.derived(level, gear)
  local t = Items.totals(gear)
  local int, vit, str, dex = t.int or 0, t.vit or 0, t.str or 0, t.dex or 0
  local general = t.dmg_pct or 0
  return {
    life = Combat.base_life(level) + (t.life or 0) + 3 * vit,
    mana = Combat.base_mana(level) + (t.mana or 0) + 2 * int,
    spell_pct = general + 0.5 * int, wand_pct = general + str,
    fire_pct = t.fire_pct or 0, cold_pct = t.cold_pct or 0, lightning_pct = t.lightning_pct or 0,
    regen_pct = t.mana_regen_pct or 0, speed_pct = 0.3 * dex,
  }
end

-- Re-total max life and mana from level and gear. Life and mana keep their share of the maximum.
function Combat.recalc(w)
  local p = w.player
  local d = Combat.derived(p.level, p.gear)
  local lf, mf = p.life / p.maxlife, p.mana / p.maxmana
  p.maxlife, p.maxmana = d.life, d.mana
  p.life, p.mana = math.min(p.maxlife, lf * p.maxlife), math.min(p.maxmana, mf * p.maxmana)
end

-- Percent damage the gear adds to a spell of this element; the wand is physical and gets the wand bonus instead.
function Combat.gear_dmg_pct(p, element)
  local d = Combat.derived(p.level, p.gear)
  if element == "physical" or element == nil then return d.wand_pct end
  return d.spell_pct + (d[element .. "_pct"] or 0)
end

-- What putting this bag item on would change, as differences in the derived numbers.
function Combat.compare(w, index)
  local p = w.player
  local item = p.bag[index]
  if not item then return nil end
  local trial = {}
  for k, v in pairs(p.gear) do trial[k] = v end
  trial[Items.place(p.gear, item.slot)] = item
  local a, b = Combat.derived(p.level, p.gear), Combat.derived(p.level, trial)
  local diff = {}
  for k, v in pairs(b) do diff[k] = v - a[k] end
  return diff
end

-- Pick an item up. An empty slot wears it at once (nothing to choose); otherwise it goes in the bag, if there is room.
-- Returns "worn", "bagged" or "full".
function Combat.take_item(w, item)
  local p = w.player
  local place = Items.place(p.gear, item.slot)
  if not p.gear[place] then
    p.gear[place] = item
    Combat.recalc(w)
    push(nil, w, { k = "item", item = item, how = "worn", rarity = item.rarity })
    return "worn"
  end
  if #p.bag >= Items.BAG_MAX then return "full" end
  p.bag[#p.bag + 1] = item
  push(nil, w, { k = "item", item = item, how = "bagged", rarity = item.rarity })
  return "bagged"
end

function Combat.equip(w, index, place)
  if Items.equip(w.player.gear, w.player.bag, index, place) then Combat.recalc(w); return true end
  return false
end

-- Take what is worn in a place off, into the bag. False if the place is empty or the bag is full.
function Combat.unequip(w, place)
  local p = w.player
  local it = p.gear[place]
  if not it or #p.bag >= Items.BAG_MAX then return false end
  p.gear[place] = nil
  p.bag[#p.bag + 1] = it
  Combat.recalc(w)
  return true
end

function Combat.trash(w, index)
  if w.player.bag[index] then table.remove(w.player.bag, index); return true end
  return false
end

function Combat.xp_for_next(level) return level * level * 10 end

function Combat.new(opts)
  opts = opts or {}
  local st = Tree.new({ level = 1 })
  local w = {
    w = opts.w or 600, h = opts.h or 400, time = 0, over = false,
    rng = Sim.rng(opts.seed or 1),
    player = { x = 300, y = 40, tx = nil, ty = nil, level = 1, xp = 0, st = st,
               maxlife = 60, life = 60, maxmana = 33, mana = 33, wand_cd = 0, cast_at = -10, buffs = {}, gear = {}, bag = {} },
    monsters = {}, projectiles = {}, events = {}, drops = {}, obstacles = {}, flags = {}, effects = {},
  }
  return w
end

function Combat.add_monster(w, m)
  m.maxlife = m.life
  m.resist = m.resist or { fire = 0, cold = 0, lightning = 0 }
  m.speed = m.speed or 60
  m.dmg = m.dmg or { 3, 6 }
  m.radius = m.radius or 12
  m.xp = m.xp or 10
  m.chill, m.freeze, m.cd = 0, 0, 0
  m.aggro = m.aggro or 1e9          -- how close you must come before it notices you (default: always)
  m.awake = false
  w.monsters[#w.monsters + 1] = m
  return m
end

function Combat.move_to(w, x, y) w.player.tx, w.player.ty = x, y end

local function roll(w, lo, hi) return lo + w.rng() * (hi - lo) end

-- A monster that notices you brings its whole pack with it.
local function wake(w, m)
  m.awake = true
  if m.pack then
    for _, o in ipairs(w.monsters) do if o.pack == m.pack and not o.dead then o.awake = true end end
  end
end

-- Trees and rocks: circles you and the monsters cannot walk through.
-- Returns the corrected position and the obstacle that was in the way, if any.
local function slide(w, x, y, rad)
  local blocker
  for _, o in ipairs(w.obstacles) do
    local dx, dy = x - o.x, y - o.y
    local d, min = math.sqrt(dx * dx + dy * dy), o.r + rad
    if d < min then
      blocker = blocker or o
      if d < 0.001 then dx, dy, d = 1, 0, 1 end
      x, y = o.x + dx / d * min, o.y + dy / d * min
    end
  end
  return math.max(0, math.min(w.w, x)), math.max(0, math.min(w.h, y)), blocker
end

-- Walk `len` toward (tx, ty); if something is in the way, go around it instead of pushing against it.
local function walk(w, x, y, tx, ty, len, rad)
  local dx, dy = tx - x, ty - y
  local d = math.sqrt(dx * dx + dy * dy)
  if d < 0.001 then return x, y end
  dx, dy = dx / d, dy / d
  local nx, ny, blocker = slide(w, x + dx * len, y + dy * len, rad)
  if blocker then
    local ox, oy = x - blocker.x, y - blocker.y
    local od = math.sqrt(ox * ox + oy * oy)
    if od < 0.001 then ox, oy, od = 1, 0, 1 end
    local tx1, ty1 = -oy / od, ox / od                         -- along the edge of the obstacle
    if tx1 * dx + ty1 * dy < 0 then tx1, ty1 = -tx1, -ty1 end  -- the way that is nearer the target
    nx, ny = slide(w, x + tx1 * len, y + ty1 * len, rad)
  end
  return nx, ny
end

-- Apply one spell's (or the wand's) damage to one monster, after resists. Returns the damage dealt.
local function hit(w, id, m, scale)
  local p = w.player
  local lo, hi, element, sk
  if id == "wand" then
    lo, hi = Combat.wand_damage(p.level)
    element = "physical"
  else
    sk = Skills.byId[id]
    lo, hi = Tree.damage(p.st, id)
    element = sk.element
  end
  local resist = Tree.effective_resist(p.st, element, m.resist[element] or 0)
  local amount = roll(w, lo, hi) * (scale or 1) * (1 + Combat.gear_dmg_pct(p, element) / 100)
  if element == "fire" and p.buffs.combustion then amount = amount * (1 + p.buffs.combustion.pct / 100) end
  local dmg = math.max(0, Tree.after_resist(amount, resist))
  m.life = m.life - dmg
  wake(w, m)
  push(nil, w, { k = "hit", id = id, x = m.x, y = m.y, dmg = dmg })
  if dmg > 0 and sk and sk.effect then
    local lvl = Tree.points_in(p.st, id)
    local val = sk.effect.base + sk.effect.per_level * (lvl - 1)
    if sk.effect.type == "chill_pct" then m.chill = Combat.CHILL_SECONDS m.chill_pct = val
    elseif sk.effect.type == "freeze_chance_pct" and w.rng() * 100 < val then m.freeze = Combat.FREEZE_SECONDS end
  end
  local shp = Combat.SHAPES[id]
  if dmg > 0 and shp and shp.chill_pct then m.chill, m.chill_pct = Combat.CHILL_SECONDS, shp.chill_pct end
  if m.life <= 0 and not m.dead then
    m.dead, m.died_at = true, w.time
    push(nil, w, { k = "kill", x = m.x, y = m.y, xp = m.xp, name = m.name })
    if m.boss then push(nil, w, { k = "boss_dead", name = m.name }) end
    if w.rng() < Combat.DROP_CHANCE then
      local kind = (w.rng() < 0.5) and "mana" or "life"
      w.drops[#w.drops + 1] = { kind = kind, x = m.x, y = m.y, t = Combat.DROP_LIFETIME }
      push(nil, w, { k = "drop", kind = kind, x = m.x, y = m.y })
    end
    do                                                   -- gear: bosses always, the rest now and then; items are as good as you are
      local n = m.boss and Combat.BOSS_ITEMS or ((w.rng() < Combat.ITEM_CHANCE) and 1 or 0)
      for i = 1, n do
        local item = Items.roll(w.rng, p.level + (m.boss and 2 or 0), m.boss and "boss" or nil)
        local a = (i / math.max(1, n)) * 2 * math.pi
        w.drops[#w.drops + 1] = { kind = "item", item = item, x = m.x + math.cos(a) * 14 * (n - 1), y = m.y + math.sin(a) * 14 * (n - 1), t = Combat.DROP_LIFETIME * 2 }
        push(nil, w, { k = "drop", kind = "item", x = m.x, y = m.y })
      end
    end
    p.xp = p.xp + m.xp
    while p.xp >= Combat.xp_for_next(p.level) do
      p.xp = p.xp - Combat.xp_for_next(p.level)
      p.level = p.level + 1
      p.st.level = p.level
      Combat.recalc(w)
      p.life, p.mana = p.maxlife, p.maxmana          -- a level-up refills both
      push(nil, w, { k = "level", level = p.level })
    end
  end
  return dmg
end

local function explode(w, id, cx, cy, radius)
  radius = radius or Combat.SHAPES[id].radius
  push(nil, w, { k = "blast", id = id, x = cx, y = cy, r = radius })
  for _, m in ipairs(w.monsters) do
    if not m.dead and dist(cx, cy, m.x, m.y) <= radius + m.radius then hit(w, id, m) end
  end
end

-- A buff or skill number at the player's level in it (the `effect` line of its table entry).
local function eff(w, id)
  local sk, n = Skills.byId[id], Tree.points_in(w.player.st, id)
  if not sk.effect or n < 1 then return 0 end
  return sk.effect.base + sk.effect.per_level * (n - 1)
end

-- Everything that hurts the player goes through here, so shields and armour apply to all of it.
local function hurt(w, amount, attacker)
  local p, b = w.player, w.player.buffs
  if b.frost_armor then
    amount = amount * (1 - math.min(75, b.frost_armor.pct) / 100)
    if attacker then attacker.chill, attacker.chill_pct = Combat.CHILL_SECONDS, 40 end
  end
  if b.mana_shield and p.mana > 0 then
    local take = math.min(p.mana, amount * b.mana_shield.pct / 100)
    p.mana, amount = p.mana - take, amount - take
  end
  if b.ice_barrier and b.ice_barrier.amount > 0 then
    local soak = math.min(b.ice_barrier.amount, amount)
    b.ice_barrier.amount, amount = b.ice_barrier.amount - soak, amount - soak
  end
  if b.icicle_cloak and attacker and not attacker.dead then hit(w, "icicle_cloak", attacker, 1) end
  p.life = p.life - amount
  if p.life <= 0 then p.life, w.over = 0, true end
end

-- Lightning that jumps: from a monster that was just hit to the nearest others in range.
local function chain(w, id, from, n, range)
  local done, cur = { [from] = true }, from
  for _ = 1, n do
    local best, bd = nil, range
    for _, m in ipairs(w.monsters) do
      if not m.dead and not done[m] then
        local d = dist(cur.x, cur.y, m.x, m.y)
        if d <= bd then best, bd = m, d end
      end
    end
    if not best then return end
    push(nil, w, { k = "zap", id = id, x1 = cur.x, y1 = cur.y, x2 = best.x, y2 = best.y })
    hit(w, id, best, 1)
    done[best], cur = true, best
  end
end

local function fire_angle(w, id, ang)
  local p, shape = w.player, Combat.SHAPES[id]
  w.projectiles[#w.projectiles + 1] = {
    id = id, x = p.x, y = p.y, vx = math.cos(ang) * shape.speed, vy = math.sin(ang) * shape.speed, left = shape.range,
  }
end

local function fire(w, id, tx, ty)
  local p, shape = w.player, Combat.SHAPES[id]
  local d = dist(p.x, p.y, tx, ty)
  if d < 1 then d = 1 end
  -- A bolt is aimed in a direction and flies its full range. An area spell is aimed at a point: it lands there,
  -- or at its maximum range if you clicked further away.
  local left = shape.range
  if shape.shape == "aoe" then left = math.min(shape.range, d) end
  w.projectiles[#w.projectiles + 1] = {
    id = id, x = p.x, y = p.y, vx = (tx - p.x) / d * shape.speed, vy = (ty - p.y) / d * shape.speed,
    left = left,
  }
end

local function clamp_target(p, tx, ty, range)
  local d = dist(p.x, p.y, tx, ty)
  if d <= range or d < 0.001 then return tx, ty end
  return p.x + (tx - p.x) / d * range, p.y + (ty - p.y) / d * range
end

local function add_effect(w, e) w.effects[#w.effects + 1] = e; return e end

-- One entry per kind of skill. Each gets the world, the skill id, where you clicked and the skill's table entry.
local CASTERS = {}
CASTERS.bolt = function(w, id, tx, ty) fire(w, id, tx, ty) end
CASTERS.aoe = function(w, id, tx, ty, shape)
  if shape.at == "self" then explode(w, id, w.player.x, w.player.y) else fire(w, id, tx, ty) end
end
CASTERS.volley = function(w, id, tx, ty, shape)
  local p = w.player
  local base = atan2(ty - p.y, tx - p.x)
  for i = 1, shape.count do fire_angle(w, id, base + (i - (shape.count + 1) / 2) * shape.spread) end
end
CASTERS.cone = function(w, id, tx, ty, shape)
  local p = w.player
  local d = math.max(1, dist(p.x, p.y, tx, ty))
  add_effect(w, { kind = "cone", id = id, x = p.x, y = p.y, dx = (tx - p.x) / d, dy = (ty - p.y) / d,
                  range = shape.range, half = shape.half, t = shape.duration, tick = shape.tick, next = 0 })
end
CASTERS.trail = function(w, id, tx, ty, shape)
  w.player.buffs[id] = { t = shape.duration, pct = eff(w, id), drop = 0 }
end
CASTERS.zone = function(w, id, tx, ty, shape)
  local x, y = clamp_target(w.player, tx, ty, shape.range)
  add_effect(w, { kind = "zone", id = id, x = x, y = y, r = shape.radius, t = shape.duration, tick = shape.tick, next = 0 })
end
CASTERS.buff = function(w, id, tx, ty, shape)
  local v = eff(w, id)
  w.player.buffs[id] = { t = shape.duration, pct = v, amount = v }
end
CASTERS.toggle = function(w, id)
  local b = w.player.buffs
  if b[id] then b[id] = nil else b[id] = { pct = math.min(80, eff(w, id)) } end
end
CASTERS.delayed = function(w, id, tx, ty, shape)
  local x, y = clamp_target(w.player, tx, ty, shape.range)
  add_effect(w, { kind = "delayed", id = id, x = x, y = y, r = shape.radius, t = shape.delay, burn_t = shape.burn_t })
end
CASTERS.summon = function(w, id, tx, ty, shape)
  for _, e in ipairs(w.effects) do if e.kind == "summon" then e.t = 0 end end      -- only one at a time
  local x, y = clamp_target(w.player, tx, ty, shape.place_range)
  add_effect(w, { kind = "summon", id = id, x = x, y = y, range = shape.range, t = shape.duration, cd = 0.3, interval = shape.interval })
end
CASTERS.orb = function(w, id, tx, ty, shape)
  local p = w.player
  local x, y = clamp_target(p, tx, ty, shape.range)
  local d = dist(p.x, p.y, x, y)
  add_effect(w, { kind = "orb", id = id, x = p.x, y = p.y, tx = x, ty = y, speed = shape.speed, r = shape.radius,
                  t = d / shape.speed + shape.linger, tick = shape.tick, next = 0, scale = shape.scale })
end
CASTERS.storm = function(w, id, tx, ty, shape)
  add_effect(w, { kind = "storm", id = id, r = shape.radius, t = shape.duration, tick = shape.tick, next = 0.3 })
end
CASTERS.static = function(w, id, tx, ty, shape)
  local p = w.player
  push(nil, w, { k = "blast", id = id, x = p.x, y = p.y, r = shape.radius })
  local pct = eff(w, id) / 100
  for _, m in ipairs(w.monsters) do
    if not m.dead and dist(p.x, p.y, m.x, m.y) <= shape.radius + m.radius then
      local cut = m.life * (m.boss and pct / 3 or pct)               -- a share of what is left; bosses lose a third of that
      cut = math.max(0, math.min(cut, m.life - 1))                   -- it can wound, never kill
      m.life = m.life - cut
      wake(w, m)
      push(nil, w, { k = "hit", id = id, x = m.x, y = m.y, dmg = cut })
    end
  end
end
CASTERS.pull = function(w, id, tx, ty, shape)
  local p = w.player
  push(nil, w, { k = "blast", id = id, x = p.x, y = p.y, r = shape.push_radius })
  for _, d in ipairs(w.drops) do
    if dist(p.x, p.y, d.x, d.y) <= shape.radius then d.x, d.y = p.x, p.y end        -- globes come to you
  end
  for _, m in ipairs(w.monsters) do
    local d = dist(p.x, p.y, m.x, m.y)
    if not m.dead and d <= shape.push_radius + m.radius then
      local ux, uy = (m.x - p.x) / math.max(d, 1), (m.y - p.y) / math.max(d, 1)
      m.x, m.y = slide(w, m.x + ux * shape.push, m.y + uy * shape.push, m.radius * 0.6)
      m.freeze = math.max(m.freeze, 0.6)                              -- and what was near is knocked back and stunned
      wake(w, m)
    end
  end
end
CASTERS.blink = function(w, id, tx, ty, shape)
  local p = w.player
  local x, y = clamp_target(p, tx, ty, shape.range)
  x, y = slide(w, x, y, Combat.PLAYER_RADIUS)
  push(nil, w, { k = "blink", id = id, x0 = p.x, y0 = p.y, x1 = x, y1 = y })
  p.x, p.y, p.tx, p.ty = x, y, nil, nil
end

-- true, or false plus why. Spends mana at cast time.
function Combat.cast(w, id, tx, ty)
  local p, shape = w.player, Combat.SHAPES[id]
  if w.over then return false, "you are dead" end
  if id == "wand" or not Skills.byId[id] then return false, "no such skill" end
  if Tree.points_in(p.st, id) < 1 then return false, "no points in " .. Skills.byId[id].name end
  local kind = Skills.byId[id].kind
  if kind == "passive" or kind == "mastery" then return false, "always on, nothing to cast" end
  if not shape then return false, "not implemented yet" end
  local cost = Tree.mana_cost(p.st, id)
  if p.mana < cost then return false, "not enough mana" end
  p.mana = p.mana - cost
  p.cast_at = w.time
  push(nil, w, { k = "cast", id = id, x = tx, y = ty })
  CASTERS[shape.shape](w, id, tx, ty, shape)
  return true
end

-- The free attack. true, or false plus why.
function Combat.attack(w, tx, ty)
  local p = w.player
  if w.over then return false, "you are dead" end
  if p.wand_cd > 0 then return false, "cooling down" end
  p.wand_cd = Combat.WAND_COOLDOWN
  p.cast_at = w.time
  push(nil, w, { k = "cast", id = "wand", x = tx, y = ty })
  fire(w, "wand", tx, ty)
  return true
end

local function step_projectiles(w, dt)
  local keep = {}
  for _, pr in ipairs(w.projectiles) do
    local shape, gone = Combat.SHAPES[pr.id], false
    local nx, ny = pr.x + pr.vx * dt, pr.y + pr.vy * dt
    local touch = (shape.shape == "aoe") and Combat.CORE or shape.radius
    for _, m in ipairs(w.monsters) do
      if not m.dead and dist(nx, ny, m.x, m.y) <= touch + m.radius then
        if shape.shape == "aoe" then explode(w, pr.id, nx, ny)
        else
          hit(w, pr.id, m)
          if shape.chain then chain(w, pr.id, m, shape.chain, shape.chain_range) end
        end
        gone = true
        break
      end
    end
    pr.left = pr.left - math.sqrt((nx - pr.x) ^ 2 + (ny - pr.y) ^ 2)
    pr.x, pr.y = nx, ny
    if not gone and pr.left <= 0 then
      if shape.shape == "aoe" then explode(w, pr.id, nx, ny) end
      gone = true
    end
    if not gone and (nx < 0 or ny < 0 or nx > w.w or ny > w.h) then gone = true end
    if not gone then keep[#keep + 1] = pr end
  end
  w.projectiles = keep
end

local function tick_effect(w, e)
  local p = w.player
  if e.kind == "zone" or e.kind == "orb" then
    for _, m in ipairs(w.monsters) do
      if not m.dead and dist(e.x, e.y, m.x, m.y) <= e.r + m.radius then hit(w, e.id, m, e.scale or 1) end
    end
  elseif e.kind == "cone" then
    local cosh = math.cos(e.half)
    for _, m in ipairs(w.monsters) do
      local d = dist(p.x, p.y, m.x, m.y)
      if not m.dead and d <= e.range + m.radius then
        local dot = d < 1 and 1 or ((m.x - p.x) * e.dx + (m.y - p.y) * e.dy) / d
        if dot >= cosh then hit(w, e.id, m, 1) end
      end
    end
  elseif e.kind == "storm" then
    local near = {}
    for _, m in ipairs(w.monsters) do
      if not m.dead and dist(p.x, p.y, m.x, m.y) <= e.r then near[#near + 1] = m end
    end
    if #near > 0 then
      local m = near[1 + math.floor(w.rng() * #near)]
      push(nil, w, { k = "zap", id = e.id, x1 = m.x, y1 = m.y + 160, x2 = m.x, y2 = m.y })
      hit(w, e.id, m, 1)
    end
  end
end

local function step_effects(w, dt)
  local p, keep, later = w.player, {}, {}
  for _, e in ipairs(w.effects) do
    e.t = e.t - dt
    if e.kind == "cone" or e.kind == "storm" then e.x, e.y = p.x, p.y end         -- these travel with you
    if e.kind == "orb" then
      local d = dist(e.x, e.y, e.tx, e.ty)
      local stepd = e.speed * dt
      if d <= stepd then e.x, e.y = e.tx, e.ty else e.x, e.y = e.x + (e.tx - e.x) / d * stepd, e.y + (e.ty - e.y) / d * stepd end
    end
    if e.kind == "delayed" then
      if e.t <= 0 then
        explode(w, e.id, e.x, e.y, e.r)
        later[#later + 1] = { kind = "zone", id = e.id, x = e.x, y = e.y, r = e.r, t = e.burn_t, tick = 0.5, next = 0.5, scale = 0.25 }
      end
    elseif e.kind == "summon" then
      e.cd = e.cd - dt
      if e.cd <= 0 and e.t > 0 then
        local best, bd = nil, e.range
        for _, m in ipairs(w.monsters) do
          if not m.dead then
            local d = dist(e.x, e.y, m.x, m.y)
            if d <= bd then best, bd = m, d end
          end
        end
        if best then
          push(nil, w, { k = "zap", id = e.id, x1 = e.x, y1 = e.y, x2 = best.x, y2 = best.y })
          hit(w, e.id, best, 1)
          e.cd = e.interval
        end
      end
    else
      e.next = e.next - dt
      while e.next <= 0 do
        e.next = e.next + e.tick
        tick_effect(w, e)
      end
    end
    if e.t > 0 then keep[#keep + 1] = e end
  end
  for _, e in ipairs(later) do keep[#keep + 1] = e end
  w.effects = keep
end

local function step_buffs(w, dt)
  local p = w.player
  for id, b in pairs(p.buffs) do
    if b.t then
      b.t = b.t - dt
      if b.t <= 0 or (id == "ice_barrier" and b.amount <= 0) then p.buffs[id] = nil end
    end
  end
end

local function step_drops(w, dt)
  local p, keep = w.player, {}
  for _, d in ipairs(w.drops) do
    d.t = d.t - dt
    if dist(p.x, p.y, d.x, d.y) <= Combat.PICKUP_RADIUS then
      if d.kind == "item" and #p.bag >= Items.BAG_MAX and (p.gear[Items.place(p.gear, d.item.slot)] ~= nil) then   -- no room: leave it where it lies and say so now and then
        keep[#keep + 1] = d
        if (p.full_warn or -99) + 3 < w.time then p.full_warn = w.time; push(nil, w, { k = "full", item = d.item }) end
      else
        if d.kind == "item" then Combat.take_item(w, d.item)
        elseif d.kind == "mana" then p.mana = math.min(p.maxmana, p.mana + Combat.DROP_RESTORE * p.maxmana)
        else p.life = math.min(p.maxlife, p.life + Combat.DROP_RESTORE * p.maxlife) end
        push(nil, w, { k = "pickup", kind = d.kind, x = d.x, y = d.y })
      end
    elseif d.t > 0 then
      keep[#keep + 1] = d
    end
  end
  w.drops = keep
end

function Combat.step(w, dt)
  if w.over then return end
  local p = w.player
  w.time = w.time + dt
  p.wand_cd = math.max(0, p.wand_cd - dt)
  -- walk toward the clicked point
  if p.tx then
    local d = dist(p.x, p.y, p.tx, p.ty)
    local bs = p.buffs.blazing_speed
    local stepd = Combat.PLAYER_SPEED * (bs and (1 + bs.pct / 100) or 1) * (1 + Combat.derived(p.level, p.gear).speed_pct / 100) * dt
    if bs then
      bs.drop = bs.drop - dt
      if bs.drop <= 0 then                                           -- it leaves a trail of fire while you run
        bs.drop = 0.2
        add_effect(w, { kind = "zone", id = "blazing_speed", x = p.x, y = p.y, r = 22, t = 2, tick = 0.4, next = 0 })
      end
    end
    if d <= stepd then p.x, p.y, p.tx, p.ty = p.tx, p.ty, nil, nil
    else p.x, p.y = walk(w, p.x, p.y, p.tx, p.ty, stepd, Combat.PLAYER_RADIUS) end
  end
  -- mana comes back; Evocation speeds it up
  local regen = p.maxmana * Combat.MANA_REGEN * (1 + (Tree.bonus(p.st, "mana_regen_pct", "fire") + Combat.derived(p.level, p.gear).regen_pct) / 100)
  p.mana = math.min(p.maxmana, p.mana + regen * dt)
  step_projectiles(w, dt)
  step_effects(w, dt)
  step_buffs(w, dt)
  step_drops(w, dt)
  -- monsters
  for _, m in ipairs(w.monsters) do
    if not m.dead then
      if not m.awake and dist(m.x, m.y, p.x, p.y) <= m.aggro then wake(w, m) end
      if m.chill > 0 then m.chill = m.chill - dt end
      if m.freeze > 0 then m.freeze = m.freeze - dt end
      m.cd = math.max(0, m.cd - dt)
      m.moving = false
      if m.awake and m.freeze <= 0 then
        local d = dist(m.x, m.y, p.x, p.y)
        if m.ranged and d <= m.ranged.range and d > Combat.MONSTER_REACH then       -- a quill rat stops and throws from where it stands
          if m.cd <= 0 then
            hurt(w, roll(w, m.dmg[1], m.dmg[2]), m)
            m.cd, m.bite_at = m.ranged.cd, w.time
            push(nil, w, { k = "zap", id = "wand", x1 = m.x, y1 = m.y + 10, x2 = p.x, y2 = p.y + 10 })
          end
        elseif d > Combat.MONSTER_REACH then
          local sp = m.speed * ((m.chill > 0) and (1 - (m.chill_pct or 0) / 100) or 1) * dt
          m.x, m.y = walk(w, m.x, m.y, p.x, p.y, sp, m.radius * 0.6)
          m.moving = true
        elseif m.cd <= 0 then
          hurt(w, roll(w, m.dmg[1], m.dmg[2]), m)
          m.cd, m.bite_at = Combat.MONSTER_COOLDOWN, w.time
          push(nil, w, { k = "bite", x = m.x, y = m.y })
        end
      end
    end
  end
end

function Combat.alive_monsters(w)
  local n = 0
  for _, m in ipairs(w.monsters) do if not m.dead then n = n + 1 end end
  return n
end

-- Move to a new area (a zone from Zone.lua): swaps the map, the monsters and the player's position.
function Combat.enter(w, area)
  local function copy(t) local c = {} for k, v in pairs(t) do c[k] = (type(v) == "table") and copy(v) or v end return c end
  w.area, w.w, w.h = area.name, area.w, area.h
  w.obstacles, w.projectiles, w.drops, w.monsters, w.effects = area.obstacles or {}, {}, {}, {}, {}
  local p = w.player
  p.x, p.y, p.tx, p.ty = area.spawn.x, area.spawn.y, nil, nil
  for _, t in ipairs(area.monsters or {}) do
    local m = copy(t)
    m.life = m.life * Combat.MONSTER_LIFE_MULT
    if m.dmg then m.dmg = { m.dmg[1] * Combat.MONSTER_DMG_MULT, m.dmg[2] * Combat.MONSTER_DMG_MULT } end
    Combat.add_monster(w, m)
  end
end

-- Hand over what happened since the last call (hits, blasts, kills, level-ups...) so the screen can show it.
function Combat.drain(w)
  local e = w.events
  w.events = {}
  return e
end

-- Put a character at a given level (health and mana scale with it) and refill both.
function Combat.set_level(w, level, xp)
  local p = w.player
  p.level, p.xp, p.st.level = level, xp or 0, level
  p.maxlife, p.maxmana = Combat.base_life(level), Combat.base_mana(level)
  p.life, p.mana = p.maxlife, p.maxmana
  Combat.recalc(w)
  p.life, p.mana = p.maxlife, p.maxmana
end

-- What survives between sessions: level, experience, spent points, quest points and quest flags.
-- Plain data, safe for SavedVariables.
function Combat.snapshot(w)
  local pts, flags = {}, {}
  for id, n in pairs(w.player.st.points) do if n > 0 then pts[id] = n end end
  for k, v in pairs(w.flags) do if v then flags[k] = true end end
  local gear = {}
  for _, slot in ipairs(Items.GEAR_SLOTS) do
    local it = w.player.gear[slot]
    if it then
      local stats = {}
      for k, v in pairs(it.stats) do stats[k] = v end
      gear[slot] = { slot = it.slot, rarity = it.rarity, ilvl = it.ilvl, base = it.base, stats = stats, title = it.title }
    end
  end
  local bag = {}
  for i, it in ipairs(w.player.bag) do
    local stats = {}
    for k, v in pairs(it.stats) do stats[k] = v end
    bag[i] = { slot = it.slot, rarity = it.rarity, ilvl = it.ilvl, base = it.base, stats = stats, title = it.title }
  end
  return { level = w.player.level, xp = w.player.xp, points = pts,
           quest_points = w.player.st.quest_points, flags = flags, gear = gear, bag = bag }
end

-- Restore a snapshot. Anything unknown or out of range is dropped rather than trusted.
function Combat.restore(w, snap)
  if type(snap) ~= "table" then return false end
  local level = math.floor(tonumber(snap.level) or 1)
  if level < 1 then level = 1 end
  w.player.gear = {}
  for _, place in ipairs(Items.GEAR_SLOTS) do
    local it = type(snap.gear) == "table" and Items.clean(snap.gear[place]) or nil
    if it and Items.fits(place, it.slot) then w.player.gear[place] = it end
  end
  w.player.bag = {}
  if type(snap.bag) == "table" then
    for i = 1, Items.BAG_MAX do
      local it = Items.clean(snap.bag[i])
      if it then w.player.bag[#w.player.bag + 1] = it end
    end
  end
  Combat.set_level(w, level, math.max(0, tonumber(snap.xp) or 0))
  local q = math.floor(tonumber(snap.quest_points) or 0)
  w.player.st.quest_points = math.max(0, math.min(Combat.MAX_QUEST_POINTS, q))
  w.flags = {}
  for k, v in pairs(type(snap.flags) == "table" and snap.flags or {}) do
    if type(k) == "string" and v == true then w.flags[k] = true end
  end
  w.player.st.points = {}
  local budget = Tree.points_total(w.player.st)
  for id, n in pairs(type(snap.points) == "table" and snap.points or {}) do
    if Skills.byId[id] and type(n) == "number" and n >= 1 then
      n = math.min(math.floor(n), Skills.MAX_POINTS, budget)
      w.player.st.points[id] = n
      budget = budget - n
    end
  end
  return true
end

return Combat
