-- The game itself: one level at a time. The player, the enemies and what they do, shots and rockets, pickups, doors, the exit.
-- Pure: nothing here touches the screen. Main.lua reads the state and draws it, and feeds in the keys.
local _, ns = ...
ns = ns or {}
local Play = {}
ns.Play = Play

local Rules, Ray, Nav, Gen = ns.Rules, ns.Ray, ns.Nav, ns.Gen

local PLAYER_R = 0.25
Play.NOISE = 12                          -- a shot wakes enemies this close (and in sight)
Play.PICKUP = 0.6

local function dist(ax, ay, bx, by) return math.sqrt((ax - bx) ^ 2 + (ay - by) ^ 2) end
local function push(w, e) w.events[#w.events + 1] = e end
local function roll(w, lo, hi) return lo + w.rng() * (hi - lo) end

-- carry: what you bring from the last level (health, armour, ammo, weapons); none means a fresh start.
function Play.new(n, seed, carry) return Play.from(Gen.level(n, seed), n, seed, carry) end

-- The same, from a level you already have (the tests build small ones by hand).
function Play.from(lv, n, seed, carry)
  local map = Ray.parse(lv.rows)
  local s = carry or Rules.START
  local w = {
    n = n, seed = seed, lv = lv, map = map, time = 0, rng = Gen.rng(seed + 7), events = {}, over = false, done = false, won = false,
    player = { x = lv.start.x, y = lv.start.y, ang = lv.start.angle, hp = s.hp, armor = s.armor, key_count = 0, weapon = 1, cool = 0, kick = 0,
               ammo = { bullets = s.bullets, shells = s.shells, rockets = s.rockets }, weapons = { s.weapons[1], s.weapons[2], s.weapons[3], s.weapons[4] } },
    enemies = {}, pickups = {}, shots = {}, rockets = {}, exit = { x = lv.exit.x, y = lv.exit.y },
    stats = { kills = 0, total = 0, picked = 0, pickups_total = 0 }, nav = nil, nav_cell = nil, last_locked = -9,
  }
  local scale = 1 + Rules.HP_PER_LEVEL * (n - 1)
  for _, e in pairs(lv.enemies) do
    local d = Rules.ENEMIES[e.kind]
    w.enemies[#w.enemies + 1] = { kind = e.kind, def = d, x = e.x, y = e.y, hp = d.hp * scale, maxhp = d.hp * scale, r = d.r, state = "idle", cool = 0.5 + w.rng(),
                                  flash = 0, dead = false, ang = 0, id = #w.enemies + 1 }
  end
  for _, i in pairs(lv.pickups) do w.pickups[#w.pickups + 1] = { kind = i.kind, x = i.x, y = i.y, taken = false } end
  w.stats.total, w.stats.pickups_total = #w.enemies, #w.pickups
  -- start with the best weapon you carry that has ammo
  for i = 4, 1, -1 do
    local wp = Rules.WEAPONS[i]
    if w.player.weapons[i] and w.player.ammo[wp.ammo] >= wp.use then w.player.weapon = i; break end
  end
  return w
end

-- What you bring to the next level.
function Play.carry(w)
  local p = w.player
  return { hp = math.max(p.hp, 50), armor = p.armor, bullets = p.ammo.bullets, shells = p.ammo.shells, rockets = p.ammo.rockets,
           weapons = { p.weapons[1], p.weapons[2], p.weapons[3], p.weapons[4] } }
end

---------------------------------------------------------------- hurting and healing
function Play.hurt(w, amount, from)
  local p = w.player
  if w.over or w.done then return end
  if p.armor > 0 then
    local soak = math.min(p.armor, amount * Rules.ARMOR_ABSORB)
    p.armor, amount = p.armor - soak, amount - soak
  end
  p.hp = p.hp - amount
  push(w, { k = "hurt", amount = amount, from = from })
  if p.hp <= 0 then p.hp, w.over = 0, true; push(w, { k = "dead" }) end
end

local function wake(w, e)
  if e.state == "idle" and not e.dead then
    e.state = "chase"
    push(w, { k = "wake", kind = e.kind, x = e.x, y = e.y })
  end
end

local function damage(w, e, amount)
  if e.dead then return end
  e.hp = e.hp - amount
  e.flash = 0.15
  wake(w, e)
  push(w, { k = "hit", x = e.x, y = e.y, amount = amount })
  if e.hp <= 0 then
    e.dead, e.died = true, w.time
    w.stats.kills = w.stats.kills + 1
    push(w, { k = "kill", kind = e.kind, boss = e.def.boss and true or false, x = e.x, y = e.y })
  end
end

---------------------------------------------------------------- walking, doors, weapons
local function open_door(w, cx, cy)
  w.map.cells[cy][cx] = 0
  push(w, { k = "door", x = cx - 0.5, y = cy - 0.5 })
end

-- Walk: fwd and side are -1..1 (forward, strafe right). Bumping a door opens it; a locked one needs the key.
function Play.move(w, fwd, side, dt, speed)
  if w.over or w.done then return end
  local p = w.player
  speed = speed or 3.4
  local c, s = math.cos(p.ang), math.sin(p.ang)
  local dx = (c * fwd - s * side) * speed * dt
  local dy = (s * fwd + c * side) * speed * dt
  if dx == 0 and dy == 0 then return end
  local nx, ny = Ray.move(w.map, p.x, p.y, dx, dy, PLAYER_R)
  if nx == p.x and ny == p.y then                                              -- blocked: is it a door?
    local len = math.sqrt(dx * dx + dy * dy)
    local tx, ty = p.x + dx / len * (PLAYER_R + 0.12), p.y + dy / len * (PLAYER_R + 0.12)
    local cx, cy = math.floor(tx) + 1, math.floor(ty) + 1
    local v = w.map.cells[cy] and w.map.cells[cy][cx]
    if v == Rules.DOOR then
      open_door(w, cx, cy)
    elseif v == Rules.LOCKED then
      if p.key_count > 0 then
        p.key_count = p.key_count - 1
        open_door(w, cx, cy)
        push(w, { k = "unlock" })
      elseif w.time - w.last_locked > 1.5 then
        w.last_locked = w.time
        push(w, { k = "locked" })
      end
    end
  end
  p.x, p.y = nx, ny
end

function Play.select(w, i)
  if i >= 1 and i <= 4 and w.player.weapons[i] and w.player.weapon ~= i then
    w.player.weapon = i
    push(w, { k = "switch", weapon = i })
    return true
  end
  return false
end

function Play.cycle(w, dir)
  local p = w.player
  for step = 1, 4 do
    local i = ((p.weapon - 1 + dir * step) % 4) + 1
    if p.weapons[i] then return Play.select(w, i) end
  end
  return false
end

local function best_with_ammo(w)
  local p = w.player
  for i = 4, 1, -1 do
    local wp = Rules.WEAPONS[i]
    if p.weapons[i] and p.ammo[wp.ammo] >= wp.use then return i end
  end
  return nil
end

local function explode(w, x, y, radius, dmg)
  push(w, { k = "explode", x = x, y = y })
  for _, e in ipairs(w.enemies) do
    if not e.dead then
      local d = dist(x, y, e.x, e.y) - e.r
      if d < radius then damage(w, e, dmg * (1 - math.max(0, d) / radius)) end
    end
  end
  local d = dist(x, y, w.player.x, w.player.y)
  if d < radius then Play.hurt(w, dmg * 0.5 * (1 - d / radius), "your own rocket") end
end

-- Pull the trigger. Returns true if a shot was fired.
function Play.fire(w)
  local p = w.player
  if w.over or w.done or p.cool > 0 then return false end
  local wp = Rules.WEAPONS[p.weapon]
  if p.ammo[wp.ammo] < wp.use then
    local b = best_with_ammo(w)
    push(w, { k = "empty" })
    if b then Play.select(w, b) end
    return false
  end
  p.ammo[wp.ammo] = p.ammo[wp.ammo] - wp.use
  p.cool, p.kick = wp.rate, 1
  push(w, { k = "shot", weapon = p.weapon, sound = wp.sound })
  for _, e in ipairs(w.enemies) do                              -- the noise wakes the ones that can hear it and see you
    if e.state == "idle" and not e.dead and dist(e.x, e.y, p.x, p.y) < Play.NOISE then
      local d = dist(e.x, e.y, p.x, p.y)
      if Ray.cast(w.map, e.x, e.y, (p.x - e.x) / d, (p.y - e.y) / d) >= d - 0.2 then wake(w, e) end
    end
  end
  if wp.speed then
    w.rockets[#w.rockets + 1] = { x = p.x + math.cos(p.ang) * 0.5, y = p.y + math.sin(p.ang) * 0.5, vx = math.cos(p.ang) * wp.speed, vy = math.sin(p.ang) * wp.speed, left = 40 }
  else
    for _ = 1, wp.pellets do
      local a = p.ang + (w.rng() - 0.5) * 2 * wp.spread
      local e, d = Ray.hitscan(w.map, p.x, p.y, a, w.enemies, 40)
      if e then damage(w, e, wp.dmg * (wp.pellets > 1 and math.max(0.35, 1 - d / 14) or 1)) end
    end
  end
  if p.ammo[wp.ammo] < wp.use then                              -- ran dry: go to the best weapon that has ammo
    local b = best_with_ammo(w)
    if b and b ~= p.weapon then Play.select(w, b) end
  end
  return true
end

---------------------------------------------------------------- enemies
local function los(w, ax, ay, bx, by)
  local d = dist(ax, ay, bx, by)
  if d < 0.01 then return true, 0 end
  return Ray.cast(w.map, ax, ay, (bx - ax) / d, (by - ay) / d) >= d - 0.2, d
end

local function step_to(w, e, tx, ty, dt)
  local d = dist(e.x, e.y, tx, ty)
  if d < 0.05 then return end
  local ux, uy = (tx - e.x) / d, (ty - e.y) / d
  local cx, cy = math.floor(e.x + ux * 0.55) + 1, math.floor(e.y + uy * 0.55) + 1       -- a door in the way: open it
  if w.map.cells[cy] and w.map.cells[cy][cx] == Rules.DOOR then open_door(w, cx, cy) end
  local sp = e.def.speed * dt
  local nx, ny = Ray.move(w.map, e.x, e.y, ux * sp, uy * sp, e.r * 0.8)
  for _, o in ipairs(w.enemies) do                                  -- do not stand inside each other
    if o ~= e and not o.dead then
      local dd = dist(nx, ny, o.x, o.y)
      if dd < e.r + o.r and dd > 0.001 then nx, ny = nx + (nx - o.x) / dd * 0.04, ny + (ny - o.y) / dd * 0.04 end
    end
  end
  e.x, e.y, e.ang = nx, ny, math.atan2 and math.atan2(uy, ux) or math.atan(uy, ux)
  e.moving = true
end

local function attack_ranged(w, e, d)
  local def = e.def
  if def.kind == "shoot" then
    local hit = def.chance * (1 - 0.5 * d / def.range)
    push(w, { k = "enemyshot", x = e.x, y = e.y, kind = e.kind })
    if w.rng() < hit then Play.hurt(w, roll(w, def.dmg[1], def.dmg[2]), def.name) end
  else
    local p = w.player
    local ux, uy = (p.x - e.x) / d, (p.y - e.y) / d
    w.shots[#w.shots + 1] = { x = e.x, y = e.y, vx = ux * def.shot, vy = uy * def.shot, dmg = roll(w, def.dmg[1], def.dmg[2]), boss = def.boss and true or false, name = def.name, left = def.range + 6 }
    push(w, { k = "enemyshot", x = e.x, y = e.y, kind = e.kind, fire = true })
  end
end

local function step_enemy(w, e, dt)
  local p = w.player
  e.moving = false
  if e.flash > 0 then e.flash = e.flash - dt end
  if e.dead then return end
  e.cool = math.max(0, e.cool - dt)
  local see, d = los(w, e.x, e.y, p.x, p.y)
  if e.state == "idle" then
    if see and d < e.def.wake then wake(w, e) end
    return
  end
  local def = e.def
  if e.windup then                                                     -- winding up a ranged attack: stand still, then let go
    e.windup = e.windup - dt
    if e.windup <= 0 then
      e.windup = nil
      e.cool = def.cool
      if see then attack_ranged(w, e, d) end
    end
    return
  end
  local melee = def.kind == "melee" and def or def.melee
  if melee and d <= (melee.reach or 1) + PLAYER_R then               -- close enough to bite
    if e.cool <= 0 then
      e.cool = melee.cool or def.cool
      Play.hurt(w, roll(w, melee.dmg[1], melee.dmg[2]), def.name)
      push(w, { k = "bite", x = e.x, y = e.y, kind = e.kind })
    end
    return
  end
  if (def.kind == "shoot" or def.kind == "fire") and see and d <= def.range then      -- in range and in sight: stop and fire
    if e.cool <= 0 then e.windup = def.windup; push(w, { k = "windup", x = e.x, y = e.y, kind = e.kind, boss = def.boss and true or false }) end
    return
  end
  if see then                                                         -- straight at you
    step_to(w, e, p.x, p.y, dt)
  else                                                                -- round the walls
    local nx, ny = Nav.next(w.nav or {}, w.map, e.x, e.y)
    if nx then step_to(w, e, nx, ny, dt) end
  end
end

local function step_shots(w, dt)
  local keep = {}
  for _, s in ipairs(w.shots) do
    s.x, s.y = s.x + s.vx * dt, s.y + s.vy * dt
    s.left = s.left - math.sqrt(s.vx ^ 2 + s.vy ^ 2) * dt
    local gone = s.left <= 0 or Ray.blocked(w.map, s.x, s.y)
    if not gone and dist(s.x, s.y, w.player.x, w.player.y) < 0.4 then
      Play.hurt(w, s.dmg, s.name)
      push(w, { k = "fireball_hit", x = s.x, y = s.y, boss = s.boss })
      gone = true
    end
    if not gone then keep[#keep + 1] = s end
  end
  w.shots = keep
end

local function step_rockets(w, dt)
  local keep, wp = {}, Rules.WEAPONS[4]
  for _, r in ipairs(w.rockets) do
    r.x, r.y = r.x + r.vx * dt, r.y + r.vy * dt
    r.left = r.left - math.sqrt(r.vx ^ 2 + r.vy ^ 2) * dt
    local boom = r.left <= 0 or Ray.blocked(w.map, r.x, r.y)
    if not boom then
      for _, e in ipairs(w.enemies) do
        if not e.dead and dist(r.x, r.y, e.x, e.y) < e.r + 0.15 then boom = true break end
      end
    end
    if boom then explode(w, r.x, r.y, wp.radius, wp.dmg) else keep[#keep + 1] = r end
  end
  w.rockets = keep
end

---------------------------------------------------------------- pickups and the exit
local function try_take(w, it)
  local p, def = w.player, Rules.ITEMS[it.kind]
  local g = def.give
  if g.hp then
    if p.hp >= Rules.MAX_HP then return false end
    p.hp = math.min(Rules.MAX_HP, p.hp + g.hp)
  end
  if g.armor then
    if p.armor >= Rules.MAX_ARMOR then return false end
    p.armor = math.min(Rules.MAX_ARMOR, p.armor + g.armor)
  end
  for _, a in ipairs({ "bullets", "shells", "rockets" }) do
    if g[a] then
      if p.ammo[a] >= Rules.AMMO_MAX[a] and not g.weapon then return false end
      p.ammo[a] = math.min(Rules.AMMO_MAX[a], p.ammo[a] + g[a])
    end
  end
  if g.weapon then
    local had = p.weapons[g.weapon]
    p.weapons[g.weapon] = true
    if not had then Play.select(w, g.weapon) end
  end
  if g.key then p.key_count = p.key_count + g.key end
  return true
end

local function step_items(w)
  local p = w.player
  for _, it in ipairs(w.pickups) do
    if not it.taken and dist(it.x, it.y, p.x, p.y) < Play.PICKUP and try_take(w, it) then
      it.taken = true
      w.stats.picked = w.stats.picked + 1
      push(w, { k = "pickup", kind = it.kind, name = Rules.ITEMS[it.kind].name })
    end
  end
end

local function boss_alive(w)
  for _, e in ipairs(w.enemies) do if e.def.boss and not e.dead then return true end end
  return false
end

---------------------------------------------------------------- the clock
function Play.step(w, dt)
  if w.over or w.done then return end
  local p = w.player
  w.time = w.time + dt
  p.cool = math.max(0, p.cool - dt)
  p.kick = math.max(0, p.kick - dt * 6)
  local cell = (math.floor(p.y) + 1) * 1000 + (math.floor(p.x) + 1)
  if cell ~= w.nav_cell then w.nav_cell = cell; w.nav = Nav.field(w.map, p.x, p.y) end      -- the way to you, redone when you change square
  for _, e in ipairs(w.enemies) do step_enemy(w, e, dt) end
  step_shots(w, dt)
  step_rockets(w, dt)
  step_items(w)
  if dist(p.x, p.y, w.exit.x, w.exit.y) < 1.0 then
    if w.lv.boss and boss_alive(w) then
      if w.time - w.last_locked > 2 then w.last_locked = w.time; push(w, { k = "blocked_exit" }) end
    else
      w.done = true
      w.won = w.n >= Rules.LEVELS
      push(w, { k = w.won and "win" or "level_done" })
    end
  end
end

return Play
