-- Particles: what makes the effects MOVE. Trails behind bolts, bursts where things land, flames rising off burning ground,
-- snow falling in a blizzard, rings that orbit you while a shield is up. Pure Lua, no WoW calls: Game.lua only draws what this says.
--
-- This never uses the combat random numbers (world.rng): drawing sparks must not change what the fight does.
local _, ns = ...
ns = ns or {}

local Fx = {}
ns.Fx = Fx

local Sim, Skills = ns.Sim, ns.Skills

Fx.MAX = 220
Fx.COLORS = {
  fire = { 1, 0.5, 0.12 }, cold = { 0.55, 0.82, 1 }, lightning = { 0.82, 0.72, 1 }, physical = { 1, 0.95, 0.8 },
  arcane = { 0.75, 0.45, 1 }, gold = { 1, 0.85, 0.3 },
}
local TAU = 2 * math.pi

function Fx.new(seed)
  return { list = {}, acc = setmetatable({}, { __mode = "k" }), rand = Sim.rng(seed or 7), time = 0, scale = 1 }
end

local function rnd(fx, a, b) return a + (b - a) * fx.rand() end

local function element_of(id)
  if id == nil or id == "wand" then return "physical" end
  local sk = Skills.byId[id]
  return sk and sk.element or "physical"
end

local function color_of(id) return Fx.COLORS[element_of(id)] end

local function add(fx, p)
  if fx.scale <= 0 or #fx.list >= Fx.MAX then return end
  p.t = 0
  fx.list[#fx.list + 1] = p
end

function Fx.spark(fx, x, y, vx, vy, color, life, s0, s1, a0, grav)
  add(fx, { x = x, y = y, vx = vx, vy = vy, max = life, s0 = s0, s1 = s1, a0 = a0 or 0.9,
            r = color[1], g = color[2], b = color[3], grav = grav or 0 })
end

function Fx.burst(fx, x, y, color, n, speed, life, s0, s1)
  for _ = 1, n do
    local a, sp = rnd(fx, 0, TAU), speed * rnd(fx, 0.4, 1)
    Fx.spark(fx, x, y, math.cos(a) * sp, math.sin(a) * sp, color, life * rnd(fx, 0.7, 1.2), s0, s1, 1, 0)
  end
end

function Fx.ring(fx, x, y, color, radius, n, life)
  for i = 1, n do
    local a = TAU * i / n
    Fx.spark(fx, x + math.cos(a) * radius * 0.3, y + math.sin(a) * radius * 0.3,
             math.cos(a) * radius / life, math.sin(a) * radius / life, color, life, 8, 3, 1, 0)
  end
end

-- Emit `per_second` particles for `key` (anything with identity), carrying the fraction over between frames.
local function rate(fx, key, per_second, dt, emit)
  local a = (fx.acc[key] or 0) + per_second * fx.scale * dt
  while a >= 1 do a = a - 1; emit() end
  fx.acc[key] = a
end

local function in_disc(fx, cx, cy, r)
  local a, d = rnd(fx, 0, TAU), r * math.sqrt(fx.rand())
  return cx + math.cos(a) * d, cy + math.sin(a) * d
end

---------------------------------------------------------------- one-off things that happen
function Fx.on_event(fx, e, world)
  local p = world.player
  if e.k == "hit" then
    Fx.burst(fx, e.x, e.y, color_of(e.id), 5, 90, 0.25, 6, 1)
  elseif e.k == "blast" then
    local c = color_of(e.id)
    Fx.burst(fx, e.x, e.y, c, math.min(26, 6 + math.floor(e.r / 4)), e.r * 2.2, 0.45, 10, 3)
    Fx.ring(fx, e.x, e.y, c, e.r, 18, 0.4)
  elseif e.k == "cast" then
    Fx.burst(fx, p.x, p.y + 20, color_of(e.id), 5, 70, 0.3, 6, 1)
  elseif e.k == "kill" then
    Fx.burst(fx, e.x, e.y, { 0.8, 0.2, 0.2 }, 12, 110, 0.5, 8, 2)
  elseif e.k == "level" then
    Fx.ring(fx, p.x, p.y, Fx.COLORS.gold, 70, 24, 0.8)
    Fx.burst(fx, p.x, p.y, Fx.COLORS.gold, 16, 90, 0.8, 9, 2)
  elseif e.k == "blink" then
    Fx.burst(fx, e.x0, e.y0, Fx.COLORS.arcane, 14, 100, 0.4, 8, 2)
    Fx.burst(fx, e.x1, e.y1, Fx.COLORS.arcane, 14, 100, 0.4, 8, 2)
  elseif e.k == "zap" then
    local c = color_of(e.id)
    for i = 1, 3 do
      local k = i / 4
      Fx.spark(fx, e.x1 + (e.x2 - e.x1) * k, e.y1 + (e.y2 - e.y1) * k, rnd(fx, -30, 30), rnd(fx, -30, 30), c, 0.25, 7, 1, 1, 0)
    end
  elseif e.k == "pickup" then
    Fx.burst(fx, e.x, e.y, e.kind == "mana" and { 0.3, 0.5, 1 } or { 1, 0.3, 0.3 }, 8, 60, 0.4, 6, 1)
  end
end

---------------------------------------------------------------- things that keep going
local function emit_projectile(fx, pr, dt)
  local el = element_of(pr.id)
  local c = Fx.COLORS[el]
  local lift = (el == "fire") and 35 or ((el == "cold") and -15 or 0)
  local jitter = (el == "lightning") and 14 or 6
  rate(fx, pr, 70, dt, function()
    Fx.spark(fx, pr.x + rnd(fx, -jitter, jitter), pr.y + rnd(fx, -jitter, jitter),
             -pr.vx * 0.12 + rnd(fx, -25, 25), -pr.vy * 0.12 + rnd(fx, -25, 25) + lift,
             c, (el == "lightning") and 0.15 or (0.3 + rnd(fx, 0, 0.15)), 9, 2, 0.9, 0)
  end)
end

local function emit_effect(fx, e, world, dt)
  local p = world.player
  local c = color_of(e.id)
  local el = element_of(e.id)
  if e.kind == "zone" then
    local per = math.min(160, e.r * e.r / 120)
    rate(fx, e, per, dt, function()
      local x, y = in_disc(fx, e.x, e.y, e.r)
      if el == "cold" then Fx.spark(fx, x, y + 40, rnd(fx, -8, 8), rnd(fx, -45, -20), c, 0.8, 6, 2, 0.8, 0)         -- snow falls
      else Fx.spark(fx, x, y, rnd(fx, -10, 10), rnd(fx, 40, 90), c, 0.5 + rnd(fx, 0, 0.3), 10, 3, 0.9, 0) end      -- flames rise
    end)
  elseif e.kind == "orb" then
    rate(fx, e, 60, dt, function()
      local a = fx.time * 6 + rnd(fx, 0, 1)
      Fx.spark(fx, e.x + math.cos(a) * 22, e.y + math.sin(a) * 22, -math.sin(a) * 40, math.cos(a) * 40, c, 0.35, 7, 2, 0.9, 0)
    end)
  elseif e.kind == "cone" then
    local base = math.atan2 and math.atan2(e.dy, e.dx) or math.atan(e.dy, e.dx)
    rate(fx, e, 120, dt, function()
      local a, sp = base + rnd(fx, -e.half, e.half), rnd(fx, 120, 220)
      Fx.spark(fx, p.x, p.y, math.cos(a) * sp, math.sin(a) * sp, c, 0.35, 10, 3, 0.9, 0)
    end)
  elseif e.kind == "storm" then
    rate(fx, e, 25, dt, function()
      Fx.spark(fx, p.x + rnd(fx, -e.r, e.r) * 0.6, p.y + 70 + rnd(fx, -10, 10), 0, 0, { 0.5, 0.45, 0.65 }, 0.7, 18, 8, 0.35, 0)
    end)
  elseif e.kind == "delayed" then
    rate(fx, e, 40, dt, function()
      Fx.spark(fx, e.x + rnd(fx, -20, 20), e.y + 200 + rnd(fx, 0, 60), 0, -220, c, 0.8, 9, 3, 0.9, 0)       -- it is coming down
    end)
  elseif e.kind == "summon" then
    rate(fx, e, 30, dt, function()
      Fx.spark(fx, e.x + rnd(fx, -8, 8), e.y + rnd(fx, 0, 14), rnd(fx, -8, 8), rnd(fx, 40, 80), c, 0.5, 9, 2, 0.9, 0)
    end)
  end
end

local function emit_buffs(fx, world, dt)
  local p = world.player
  for id, b in pairs(p.buffs) do
    if id == "combustion" or id == "blazing_speed" then
      rate(fx, b, id == "combustion" and 40 or 50, dt, function()
        Fx.spark(fx, p.x + rnd(fx, -10, 10), p.y + rnd(fx, 0, 25), rnd(fx, -15, 15), rnd(fx, 40, 110), Fx.COLORS.fire, 0.5, 9, 2, 0.9, 0)
      end)
    else                                                                 -- shields glitter now and then
      local c = (id == "mana_shield") and Fx.COLORS.arcane or Fx.COLORS.cold
      rate(fx, b, 12, dt, function()
        local a = rnd(fx, 0, TAU)
        Fx.spark(fx, p.x + math.cos(a) * 28, p.y + 18 + math.sin(a) * 28, 0, rnd(fx, 5, 25), c, 0.6, 6, 1, 0.9, 0)
      end)
    end
  end
  for _, m in ipairs(world.monsters) do
    if not m.dead and (m.chill > 0 or m.freeze > 0) then
      local dx, dy = m.x - p.x, m.y - p.y
      if dx * dx + dy * dy < 500 * 500 then
        rate(fx, m, m.freeze > 0 and 22 or 8, dt, function()
          Fx.spark(fx, m.x + rnd(fx, -12, 12), m.y + rnd(fx, 0, 40), 0, rnd(fx, -20, 10), Fx.COLORS.cold, 0.5, 6, 1, 0.9, 0)
        end)
      end
    end
  end
end

-- Emit from everything that is going on, then move and age what already exists.
function Fx.update(fx, world, dt)
  fx.time = fx.time + dt
  if fx.scale > 0 then
    for _, pr in ipairs(world.projectiles) do emit_projectile(fx, pr, dt) end
    for _, e in ipairs(world.effects) do emit_effect(fx, e, world, dt) end
    emit_buffs(fx, world, dt)
  end
  local keep = {}
  for _, q in ipairs(fx.list) do
    q.t = q.t + dt
    if q.t < q.max then
      q.vy = q.vy + q.grav * dt
      q.x, q.y = q.x + q.vx * dt, q.y + q.vy * dt
      keep[#keep + 1] = q
    end
  end
  fx.list = keep
end

---------------------------------------------------------------- auras around you: computed from state and time, not stored
-- Each buff is a ring of glowing dots circling the player, at its own radius and speed so two buffs do not hide each other.
Fx.AURAS = {
  ice_barrier   = { r = 26, n = 10, speed = 1.6, size = 8, color = "cold" },
  frost_armor   = { r = 33, n = 12, speed = -1.2, size = 6, color = "cold" },
  icicle_cloak  = { r = 40, n = 7,  speed = 2.4, size = 11, color = "cold" },
  mana_shield   = { r = 30, n = 10, speed = -2.0, size = 7, color = "arcane" },
  combustion    = { r = 22, n = 8,  speed = 4.0, size = 9, color = "fire" },
  blazing_speed = { r = 20, n = 6,  speed = 5.0, size = 8, color = "fire" },
}

function Fx.auras(fx, world)
  local p, out = world.player, {}
  local names = {}
  for id in pairs(p.buffs) do names[#names + 1] = id end
  table.sort(names)
  for _, id in ipairs(names) do
    local a = Fx.AURAS[id]
    if a then
      local c = Fx.COLORS[a.color]
      out[#out + 1] = { x = p.x, y = p.y + 20, size = a.r * 2.1, alpha = 0.10 + 0.04 * math.sin(fx.time * 3), r = c[1], g = c[2], b = c[3] }   -- a faint bubble
      for k = 1, a.n do
        local ang = fx.time * a.speed + TAU * k / a.n
        out[#out + 1] = { x = p.x + math.cos(ang) * a.r, y = p.y + 20 + math.sin(ang) * a.r * 0.8, size = a.size,
                          alpha = 0.55 + 0.35 * math.sin(fx.time * 5 + k), r = c[1], g = c[2], b = c[3] }
      end
    end
  end
  return out
end

return Fx
