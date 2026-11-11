-- The fight: a player, monsters and spells moving through a small arena. Pure Lua, no WoW calls.
-- Damage, mana and resists all come from Tree.lua, so spending a point changes what happens here.
--
-- Spells that can be cast so far are the ones with an entry in Combat.SHAPES. Anything else is
-- refused with "not implemented yet" rather than silently doing nothing.
local _, ns = ...
ns = ns or {}

local Combat = {}
ns.Combat = Combat

local Skills, Tree, Sim = ns.Skills, ns.Tree, ns.Sim

-- How each implemented spell behaves.
--   bolt: flies from the player toward the target point and hits the first monster in its path
--   aoe : hits everything within `radius` of the centre, which is the target point or, with at="self", the player
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
}

Combat.PLAYER_SPEED = 140
Combat.CORE = 10
Combat.CHILL_SECONDS, Combat.FREEZE_SECONDS = 3, 2
Combat.MONSTER_REACH, Combat.MONSTER_COOLDOWN = 22, 1.0

local function dist(ax, ay, bx, by)
  local dx, dy = ax - bx, ay - by
  return math.sqrt(dx * dx + dy * dy)
end

function Combat.xp_for_next(level) return level * level * 10 end

function Combat.new(opts)
  opts = opts or {}
  local st = Tree.new({ level = 1 })
  local w = {
    w = opts.w or 600, h = opts.h or 400, time = 0, over = false,
    rng = Sim.rng(opts.seed or 1),
    player = { x = 300, y = 40, tx = nil, ty = nil, level = 1, xp = 0, st = st,
               maxlife = 60, life = 60, maxmana = 33, mana = 33 },
    monsters = {}, projectiles = {}, log = {},
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
  w.monsters[#w.monsters + 1] = m
  return m
end

function Combat.move_to(w, x, y) w.player.tx, w.player.ty = x, y end

local function roll(w, lo, hi) return lo + w.rng() * (hi - lo) end

-- Apply one spell's damage to one monster, after resists. Returns the damage dealt.
local function hit(w, id, m)
  local p, sk = w.player, Skills.byId[id]
  local lo, hi = Tree.damage(p.st, id)
  local resist = Tree.effective_resist(p.st, sk.element, m.resist[sk.element] or 0)
  local dmg = math.max(0, Tree.after_resist(roll(w, lo, hi), resist))
  m.life = m.life - dmg
  if dmg > 0 and sk.effect then
    local lvl = Tree.points_in(p.st, id)
    local val = sk.effect.base + sk.effect.per_level * (lvl - 1)
    if sk.effect.type == "chill_pct" then m.chill = Combat.CHILL_SECONDS m.chill_pct = val
    elseif sk.effect.type == "freeze_chance_pct" and w.rng() * 100 < val then m.freeze = Combat.FREEZE_SECONDS end
  end
  if m.life <= 0 and not m.dead then
    m.dead = true
    p.xp = p.xp + m.xp
    while p.xp >= Combat.xp_for_next(p.level) do
      p.xp = p.xp - Combat.xp_for_next(p.level)
      p.level = p.level + 1
      p.st.level = p.level
      p.maxlife, p.maxmana = p.maxlife + 6, p.maxmana + 3
      p.life, p.mana = p.maxlife, p.maxmana          -- a level-up refills both
    end
  end
  return dmg
end

local function explode(w, id, cx, cy)
  local radius = Combat.SHAPES[id].radius
  for _, m in ipairs(w.monsters) do
    if not m.dead and dist(cx, cy, m.x, m.y) <= radius + m.radius then hit(w, id, m) end
  end
end

-- true, or false plus why. Spends mana at cast time.
function Combat.cast(w, id, tx, ty)
  local p, shape = w.player, Combat.SHAPES[id]
  if w.over then return false, "you are dead" end
  if not Skills.byId[id] then return false, "no such skill" end
  if Tree.points_in(p.st, id) < 1 then return false, "no points in " .. Skills.byId[id].name end
  if not shape then return false, "not implemented yet" end
  local cost = Tree.mana_cost(p.st, id)
  if p.mana < cost then return false, "not enough mana" end
  p.mana = p.mana - cost
  if shape.shape == "aoe" and shape.at == "self" then
    explode(w, id, p.x, p.y)
  else
    local d = dist(p.x, p.y, tx, ty)
    if d < 1 then d = 1 end
    w.projectiles[#w.projectiles + 1] = {
      id = id, x = p.x, y = p.y, vx = (tx - p.x) / d * shape.speed, vy = (ty - p.y) / d * shape.speed,
      left = shape.range,
    }
  end
  return true
end

local function step_projectiles(w, dt)
  local keep = {}
  for _, pr in ipairs(w.projectiles) do
    local shape, gone = Combat.SHAPES[pr.id], false
    local nx, ny = pr.x + pr.vx * dt, pr.y + pr.vy * dt
    -- a bolt touches with its own size; an exploding spell touches with a small core, then the blast spreads
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

function Combat.step(w, dt)
  if w.over then return end
  local p = w.player
  w.time = w.time + dt
  -- walk toward the clicked point
  if p.tx then
    local d = dist(p.x, p.y, p.tx, p.ty)
    local stepd = Combat.PLAYER_SPEED * dt
    if d <= stepd then p.x, p.y, p.tx, p.ty = p.tx, p.ty, nil, nil
    else p.x, p.y = p.x + (p.tx - p.x) / d * stepd, p.y + (p.ty - p.y) / d * stepd end
  end
  -- mana comes back; Evocation speeds it up
  local regen = 1.0 * (1 + Tree.bonus(p.st, "mana_regen_pct", "fire") / 100)
  p.mana = math.min(p.maxmana, p.mana + regen * dt)
  step_projectiles(w, dt)
  -- monsters
  for _, m in ipairs(w.monsters) do
    if not m.dead then
      if m.chill > 0 then m.chill = m.chill - dt end
      if m.freeze > 0 then m.freeze = m.freeze - dt end
      m.cd = math.max(0, m.cd - dt)
      if m.freeze <= 0 then
        local d = dist(m.x, m.y, p.x, p.y)
        if d > Combat.MONSTER_REACH then
          local sp = m.speed * ((m.chill > 0) and (1 - (m.chill_pct or 0) / 100) or 1) * dt
          m.x, m.y = m.x + (p.x - m.x) / d * sp, m.y + (p.y - m.y) / d * sp
        elseif m.cd <= 0 then
          p.life = p.life - roll(w, m.dmg[1], m.dmg[2])
          m.cd = Combat.MONSTER_COOLDOWN
          if p.life <= 0 then p.life, w.over = 0, true end
        end
      end
    end
  end
end

-- Put a character at a given level (health and mana scale with it) and refill both.
function Combat.set_level(w, level, xp)
  local p = w.player
  p.level, p.xp, p.st.level = level, xp or 0, level
  p.maxlife, p.maxmana = 60 + 6 * (level - 1), 33 + 3 * (level - 1)
  p.life, p.mana = p.maxlife, p.maxmana
end

-- What survives between sessions: level, experience and spent points. Plain data, safe for SavedVariables.
function Combat.snapshot(w)
  local pts = {}
  for id, n in pairs(w.player.st.points) do if n > 0 then pts[id] = n end end
  return { level = w.player.level, xp = w.player.xp, points = pts }
end

-- Restore a snapshot. Anything unknown or out of range is dropped rather than trusted.
function Combat.restore(w, snap)
  if type(snap) ~= "table" then return false end
  local level = math.floor(tonumber(snap.level) or 1)
  if level < 1 then level = 1 end
  Combat.set_level(w, level, math.max(0, tonumber(snap.xp) or 0))
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

function Combat.alive_monsters(w)
  local n = 0
  for _, m in ipairs(w.monsters) do if not m.dead then n = n + 1 end end
  return n
end

return Combat
