-- The fight: a player, monsters and spells moving through an area. Pure Lua, no WoW calls.
-- Damage, mana and resists all come from Tree.lua, so spending a point changes what happens here.
--
-- Spells that can be cast are the ones with an entry in Combat.SHAPES. Anything else is refused with
-- "not implemented yet" rather than silently doing nothing.
local _, ns = ...
ns = ns or {}

local Combat = {}
ns.Combat = Combat

local Skills, Tree, Sim = ns.Skills, ns.Tree, ns.Sim

-- bolt: flies from the player toward the target point and hits the first monster in its path
-- aoe : explodes where it lands (at = "target") or around the player (at = "self"), hitting all within `radius`
Combat.SHAPES = {
  scorch         = { shape = "bolt", speed = 320, range = 420, radius = 10 },
  frostbolt      = { shape = "bolt", speed = 300, range = 420, radius = 10 },
  ice_lance      = { shape = "bolt", speed = 420, range = 460, radius = 8 },
  arcing_bolts   = { shape = "bolt", speed = 380, range = 380, radius = 8 },
  lightning_bolt = { shape = "bolt", speed = 700, range = 520, radius = 8 },
  fireball       = { shape = "aoe", at = "target", radius = 55, speed = 300, range = 440 },
  glacial_spike  = { shape = "aoe", at = "target", radius = 50, speed = 340, range = 440 },
  frost_nova     = { shape = "aoe", at = "self", radius = 90 },
  thunder_nova   = { shape = "aoe", at = "self", radius = 100 },
  -- the free basic attack (a mage's wand): no mana, a short cooldown, plain damage that grows with level
  wand           = { shape = "bolt", speed = 450, range = 360, radius = 8 },
}
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

local function dist(ax, ay, bx, by)
  local dx, dy = ax - bx, ay - by
  return math.sqrt(dx * dx + dy * dy)
end

local function push(ev, w, e) w.events[#w.events + 1] = e end

function Combat.xp_for_next(level) return level * level * 10 end

function Combat.new(opts)
  opts = opts or {}
  local st = Tree.new({ level = 1 })
  local w = {
    w = opts.w or 600, h = opts.h or 400, time = 0, over = false,
    rng = Sim.rng(opts.seed or 1),
    player = { x = 300, y = 40, tx = nil, ty = nil, level = 1, xp = 0, st = st,
               maxlife = 60, life = 60, maxmana = 33, mana = 33, wand_cd = 0, cast_at = -10 },
    monsters = {}, projectiles = {}, events = {}, drops = {}, obstacles = {}, flags = {},
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
local function hit(w, id, m)
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
  local dmg = math.max(0, Tree.after_resist(roll(w, lo, hi), resist))
  m.life = m.life - dmg
  wake(w, m)
  push(nil, w, { k = "hit", id = id, x = m.x, y = m.y, dmg = dmg })
  if dmg > 0 and sk and sk.effect then
    local lvl = Tree.points_in(p.st, id)
    local val = sk.effect.base + sk.effect.per_level * (lvl - 1)
    if sk.effect.type == "chill_pct" then m.chill = Combat.CHILL_SECONDS m.chill_pct = val
    elseif sk.effect.type == "freeze_chance_pct" and w.rng() * 100 < val then m.freeze = Combat.FREEZE_SECONDS end
  end
  if m.life <= 0 and not m.dead then
    m.dead, m.died_at = true, w.time
    push(nil, w, { k = "kill", x = m.x, y = m.y, xp = m.xp, name = m.name })
    if m.boss then push(nil, w, { k = "boss_dead", name = m.name }) end
    if w.rng() < Combat.DROP_CHANCE then
      local kind = (w.rng() < 0.5) and "mana" or "life"
      w.drops[#w.drops + 1] = { kind = kind, x = m.x, y = m.y, t = Combat.DROP_LIFETIME }
      push(nil, w, { k = "drop", kind = kind, x = m.x, y = m.y })
    end
    p.xp = p.xp + m.xp
    while p.xp >= Combat.xp_for_next(p.level) do
      p.xp = p.xp - Combat.xp_for_next(p.level)
      p.level = p.level + 1
      p.st.level = p.level
      p.maxlife, p.maxmana = p.maxlife + 6, p.maxmana + 3
      p.life, p.mana = p.maxlife, p.maxmana          -- a level-up refills both
      push(nil, w, { k = "level", level = p.level })
    end
  end
  return dmg
end

local function explode(w, id, cx, cy)
  local radius = Combat.SHAPES[id].radius
  push(nil, w, { k = "blast", id = id, x = cx, y = cy, r = radius })
  for _, m in ipairs(w.monsters) do
    if not m.dead and dist(cx, cy, m.x, m.y) <= radius + m.radius then hit(w, id, m) end
  end
end

local function fire(w, id, tx, ty)
  local p, shape = w.player, Combat.SHAPES[id]
  local d = dist(p.x, p.y, tx, ty)
  if d < 1 then d = 1 end
  w.projectiles[#w.projectiles + 1] = {
    id = id, x = p.x, y = p.y, vx = (tx - p.x) / d * shape.speed, vy = (ty - p.y) / d * shape.speed,
    left = shape.range,
  }
end

-- true, or false plus why. Spends mana at cast time.
function Combat.cast(w, id, tx, ty)
  local p, shape = w.player, Combat.SHAPES[id]
  if w.over then return false, "you are dead" end
  if id == "wand" or not Skills.byId[id] then return false, "no such skill" end
  if Tree.points_in(p.st, id) < 1 then return false, "no points in " .. Skills.byId[id].name end
  if not shape then return false, "not implemented yet" end
  local cost = Tree.mana_cost(p.st, id)
  if p.mana < cost then return false, "not enough mana" end
  p.mana = p.mana - cost
  p.cast_at = w.time
  push(nil, w, { k = "cast", id = id, x = tx, y = ty })
  if shape.shape == "aoe" and shape.at == "self" then
    explode(w, id, p.x, p.y)
  else
    fire(w, id, tx, ty)
  end
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
        if shape.shape == "aoe" then explode(w, pr.id, nx, ny) else hit(w, pr.id, m) end
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

local function step_drops(w, dt)
  local p, keep = w.player, {}
  for _, d in ipairs(w.drops) do
    d.t = d.t - dt
    if dist(p.x, p.y, d.x, d.y) <= Combat.PICKUP_RADIUS then
      if d.kind == "mana" then p.mana = math.min(p.maxmana, p.mana + Combat.DROP_RESTORE * p.maxmana)
      else p.life = math.min(p.maxlife, p.life + Combat.DROP_RESTORE * p.maxlife) end
      push(nil, w, { k = "pickup", kind = d.kind, x = d.x, y = d.y })
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
    local stepd = Combat.PLAYER_SPEED * dt
    if d <= stepd then p.x, p.y, p.tx, p.ty = p.tx, p.ty, nil, nil
    else p.x, p.y = walk(w, p.x, p.y, p.tx, p.ty, stepd, Combat.PLAYER_RADIUS) end
  end
  -- mana comes back; Evocation speeds it up
  local regen = p.maxmana * Combat.MANA_REGEN * (1 + Tree.bonus(p.st, "mana_regen_pct", "fire") / 100)
  p.mana = math.min(p.maxmana, p.mana + regen * dt)
  step_projectiles(w, dt)
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
        if d > Combat.MONSTER_REACH then
          local sp = m.speed * ((m.chill > 0) and (1 - (m.chill_pct or 0) / 100) or 1) * dt
          m.x, m.y = walk(w, m.x, m.y, p.x, p.y, sp, m.radius * 0.6)
          m.moving = true
        elseif m.cd <= 0 then
          p.life = p.life - roll(w, m.dmg[1], m.dmg[2])
          m.cd, m.bite_at = Combat.MONSTER_COOLDOWN, w.time
          push(nil, w, { k = "bite", x = m.x, y = m.y })
          if p.life <= 0 then p.life, w.over = 0, true end
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
  w.obstacles, w.projectiles, w.drops, w.monsters = area.obstacles or {}, {}, {}, {}
  local p = w.player
  p.x, p.y, p.tx, p.ty = area.spawn.x, area.spawn.y, nil, nil
  for _, t in ipairs(area.monsters or {}) do Combat.add_monster(w, copy(t)) end
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
  p.maxlife, p.maxmana = 60 + 6 * (level - 1), 33 + 3 * (level - 1)
  p.life, p.mana = p.maxlife, p.maxmana
end

-- What survives between sessions: level, experience, spent points, quest points and quest flags.
-- Plain data, safe for SavedVariables.
function Combat.snapshot(w)
  local pts, flags = {}, {}
  for id, n in pairs(w.player.st.points) do if n > 0 then pts[id] = n end end
  for k, v in pairs(w.flags) do if v then flags[k] = true end end
  return { level = w.player.level, xp = w.player.xp, points = pts,
           quest_points = w.player.st.quest_points, flags = flags }
end

-- Restore a snapshot. Anything unknown or out of range is dropped rather than trusted.
function Combat.restore(w, snap)
  if type(snap) ~= "table" then return false end
  local level = math.floor(tonumber(snap.level) or 1)
  if level < 1 then level = 1 end
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
