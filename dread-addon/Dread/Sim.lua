-- Pure game logic. No WoW API calls, so it runs under plain Lua and can be unit tested.
local _, ns = ...
ns = ns or {}

local Sim = {}
ns.Sim = Sim

-- Small deterministic random generator so a seed always gives the same run.
function Sim.rng(seed)
  local s = seed
  return function()
    s = (s * 1103515245 + 12345) % 2147483648
    return s / 2147483648
  end
end

-- n squares inside a w x h arena, each with a position and a velocity (units/sec).
function Sim.new(n, w, h, seed)
  local rand = Sim.rng(seed or 1)
  local world = { w = w, h = h, objs = {} }
  for i = 1, n do
    local angle = rand() * 2 * math.pi
    local speed = 40 + rand() * 80
    world.objs[i] = {
      x = rand() * w, y = rand() * h,
      vx = math.cos(angle) * speed, vy = math.sin(angle) * speed,
    }
  end
  return world
end

-- Move every object by dt seconds; bounce off the arena walls.
function Sim.step(world, dt)
  local w, h = world.w, world.h
  for _, o in ipairs(world.objs) do
    local x, y = o.x + o.vx * dt, o.y + o.vy * dt
    if x < 0 then x = -x; o.vx = -o.vx elseif x > w then x = 2 * w - x; o.vx = -o.vx end
    if y < 0 then y = -y; o.vy = -o.vy elseif y > h then y = 2 * h - y; o.vy = -o.vy end
    o.x, o.y = x, y
  end
end

-- Test 1 verdict from the samples. Thresholds are the spec's: >30 FPS, no memory growth.
-- fps: list of once-a-second FPS readings. memEarly / memLate: KB after a full collect
-- at 1 minute and at the end. Growth over 10% of memEarly counts as growth.
function Sim.verdict(fps, memEarly, memLate)
  if #fps == 0 then return "NO DATA", "no FPS samples" end
  local sum, min = 0, math.huge
  for _, f in ipairs(fps) do sum = sum + f; if f < min then min = f end end
  local avg = sum / #fps
  local growth = (memLate - memEarly) / memEarly
  local ok = min > 30 and growth <= 0.10
  local detail = string.format("fps avg %.1f min %.1f over %d samples; memory %.0f -> %.0f KB (%+.1f%%)",
    avg, min, #fps, memEarly, memLate, growth * 100)
  return ok and "PASS" or "FAIL", detail
end

return Sim
