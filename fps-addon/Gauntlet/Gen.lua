-- Level generator: seeded and repeatable. Rooms joined in a chain by corridors, doors in the corridors, the way to the exit behind a locked
-- door, the key in a room before it, enemies and pickups scattered by level. Pure; the same (level, seed) always makes the same level.
local _, ns = ...
ns = ns or {}
local Gen = {}
ns.Gen = Gen

local Rules, Ray, Nav = ns.Rules, ns.Ray, ns.Nav

-- A small repeatable random source (an LCG): rng() gives [0, 1).
function Gen.rng(seed)
  local s = (seed or 1) % 2147483647
  if s <= 0 then s = s + 2147483646 end
  return function()
    s = (s * 48271) % 2147483647
    return s / 2147483647
  end
end

local function irand(rng, lo, hi) return lo + math.floor(rng() * (hi - lo + 1)) end
local function pick(rng, list) return list[irand(rng, 1, #list)] end

-- Rooms and corridors are numbered from square 1; a world position inside square (x, y) is between x - 1 and x.
local function cx(r) return r.x + r.w / 2 - 1 end
local function cy(r) return r.y + r.h / 2 - 1 end

function Gen.size(n) return math.min(56, 36 + 4 * n) end

-- One attempt. Returns the level, or nil if the rooms would not fit or the lock is not a real chokepoint.
local function attempt(n, seed)
  local rng = Gen.rng(seed)
  local S = Gen.size(n)
  local boss = (n == Rules.LEVELS)
  local want = 6 + n
  local rooms = {}
  local function overlaps(r)
    for _, o in ipairs(rooms) do
      if r.x < o.x + o.w + 2 and o.x < r.x + r.w + 2 and r.y < o.y + o.h + 2 and o.y < r.y + r.h + 2 then return true end
    end
    return false
  end
  for _ = 1, 500 do
    if #rooms >= want then break end
    local w, h = irand(rng, 5, 9), irand(rng, 5, 9)
    local r = { x = irand(rng, 2, S - w - 2), y = irand(rng, 2, S - h - 2), w = w, h = h, kind = irand(rng, 1, 4) }
    if not overlaps(r) then rooms[#rooms + 1] = r end
  end
  if #rooms < 5 then return nil end
  if boss then                                                  -- the last room is a big arena
    local last = rooms[#rooms]
    last.w, last.h = 11, 11
    last.x, last.y = math.min(last.x, S - 13), math.min(last.y, S - 13)
    for i = 1, #rooms - 1 do
      local o = rooms[i]
      if last.x < o.x + o.w + 2 and o.x < last.x + last.w + 2 and last.y < o.y + o.h + 2 and o.y < last.y + last.h + 2 then return nil end
    end
  end
  table.sort(rooms, function(a, b) if a.x ~= b.x then return a.x < b.x end return a.y < b.y end)
  if boss then                                                  -- keep the arena last in the chain
    local bi
    for i, r in ipairs(rooms) do if r.w == 11 and r.h == 11 then bi = i end end
    if not bi then return nil end
    local a = table.remove(rooms, bi); rooms[#rooms + 1] = a
  end
  local open, owner, inroom = {}, {}, {}
  for y = 1, S do open[y], owner[y], inroom[y] = {}, {}, {} end
  for ri, r in ipairs(rooms) do
    for y = r.y, r.y + r.h - 1 do for x = r.x, r.x + r.w - 1 do open[y][x], owner[y][x], inroom[y][x] = true, r.kind, ri end end
  end
  local paths = {}                                              -- the corridor cells of each join, in order from room i to room i+1
  for i = 1, #rooms - 1 do
    local a, b = rooms[i], rooms[i + 1]
    local ax, ay = a.x + math.floor(a.w / 2), a.y + math.floor(a.h / 2)
    local bx, by = b.x + math.floor(b.w / 2), b.y + math.floor(b.h / 2)
    local path = {}
    local function carve(x, y)
      if not open[y][x] then open[y][x], owner[y][x] = true, a.kind end
      path[#path + 1] = { x, y }
    end
    local x, y = ax, ay
    local horizontal_first = rng() < 0.5
    local function go_x() while x ~= bx do x = x + (bx > x and 1 or -1); carve(x, y) end end
    local function go_y() while y ~= by do y = y + (by > y and 1 or -1); carve(x, y) end end
    if horizontal_first then go_x(); go_y() else go_y(); go_x() end
    paths[i] = path
  end
  -- Doors: a straight corridor square (walls either side, outside every room) becomes a door.
  local function straight(x, y)
    if inroom[y][x] or not open[y][x] then return false end
    local l, r2, u, d = open[y][x - 1], open[y][x + 1], open[y - 1] and open[y - 1][x], open[y + 1] and open[y + 1][x]
    return (l and r2 and not u and not d) or (u and d and not l and not r2)
  end
  local doors = {}                                              -- [y][x] = kind
  local function door_in(i, kind, from_end)
    local cand = {}
    for _, c in ipairs(paths[i]) do if straight(c[1], c[2]) and not (doors[c[2]] and doors[c[2]][c[1]]) then cand[#cand + 1] = c end end
    if #cand == 0 then return false end
    local c = from_end and cand[#cand] or cand[math.ceil(#cand / 2)]
    doors[c[2]] = doors[c[2]] or {}
    doors[c[2]][c[1]] = kind
    return true
  end
  for i = 1, #rooms - 2 do if rng() < 0.55 then door_in(i, Rules.DOOR, false) end end
  if not door_in(#rooms - 1, Rules.LOCKED, true) then return nil end
  -- the picture: open squares '.', doors, walls of the kind of the nearest room
  local rows = {}
  for y = 1, S do
    local row = {}
    for x = 1, S do
      if doors[y] and doors[y][x] then row[x] = tostring(doors[y][x])
      elseif open[y][x] then row[x] = "."
      else
        local k = 1
        for dy = -1, 1 do for dx = -1, 1 do
          local o = owner[y + dy] and owner[y + dy][x + dx]
          if o and open[y + dy][x + dx] then k = o end
        end end
        row[x] = tostring(k)
      end
    end
    rows[y] = table.concat(row)
  end
  -- things
  local function cell_in(r, margin)
    margin = margin or 1
    for _ = 1, 40 do
      local x, y = irand(rng, r.x + margin, r.x + r.w - 1 - margin), irand(rng, r.y + margin, r.y + r.h - 1 - margin)
      if not (doors[y] and doors[y][x]) then return x - 0.5, y - 0.5 end
    end
    return r.x + r.w / 2, r.y + r.h / 2
  end
  local first, last = rooms[1], rooms[#rooms]
  local out = { rows = rows, w = S, h = S, n = n, seed = seed, boss = boss, name = Rules.LEVEL_NAMES[n] or ("Level " .. n), rooms = rooms,
                start = { x = cx(first), y = cy(first), angle = 0 },
                exit = { x = cx(last), y = cy(last) }, enemies = {}, pickups = {} }
  local roster = Rules.ROSTER[math.min(n, #Rules.ROSTER)]
  for ri = 2, #rooms - 1 do
    local r = rooms[ri]
    local count = math.min(4, 1 + irand(rng, 0, 1 + math.floor(n / 2)) + (ri == 2 and -1 or 0))
    for _ = 1, math.max(1, count) do
      local x, y = cell_in(r, 1)
      out.enemies[#out.enemies + 1] = { x = x, y = y, kind = pick(rng, roster) }
    end
  end
  if boss then
    out.enemies[#out.enemies + 1] = { x = cx(last), y = last.y + 1.5, kind = "boss" }
    for i = 1, 4 do
      local a = i * math.pi / 2 + 0.7
      out.enemies[#out.enemies + 1] = { x = cx(last) + math.cos(a) * 3.5, y = cy(last) + math.sin(a) * 3.5, kind = "imp" }
    end
  end
  -- pickups: the key before the lock, a weapon a level, potions and ammo about
  local kr = rooms[irand(rng, 2, #rooms - 1)]
  local kx, ky = cell_in(kr, 1)
  out.pickups[#out.pickups + 1] = { x = kx, y = ky, kind = "key" }
  local x, y = cell_in(first, 1)
  out.pickups[#out.pickups + 1] = { x = x, y = y, kind = "bullets" }
  x, y = cell_in(first, 1)
  out.pickups[#out.pickups + 1] = { x = x, y = y, kind = n >= 2 and "shells" or "bullets" }
  local gun = ({ "scatter", "repeater", "rocket" })[n]
  if gun then
    local gr = rooms[irand(rng, 2, math.min(#rooms - 1, 4))]
    x, y = cell_in(gr, 1)
    out.pickups[#out.pickups + 1] = { x = x, y = y, kind = gun }
  end
  for ri = 2, #rooms do
    local r = rooms[ri]
    if rng() < 0.6 then x, y = cell_in(r, 1); out.pickups[#out.pickups + 1] = { x = x, y = y, kind = rng() < 0.2 and "bigheal" or "health" } end
    if rng() < 0.75 then
      x, y = cell_in(r, 1)
      local pool = n >= 3 and { "bullets", "shells", "rockets" } or { "bullets", "shells" }
      out.pickups[#out.pickups + 1] = { x = x, y = y, kind = pick(rng, pool) }
    end
  end
  x, y = cell_in(rooms[math.ceil(#rooms / 2)], 1)
  out.pickups[#out.pickups + 1] = { x = x, y = y, kind = "armor" }
  if boss then                                                  -- supplies before the arena
    for i = 1, 3 do
      x, y = cell_in(rooms[#rooms - 1], 1)
      out.pickups[#out.pickups + 1] = { x = x, y = y, kind = ({ "bigheal", "armor", "rockets" })[i] }
    end
  end
  -- the lock must really be a chokepoint, and the key must be on the near side of it
  local map = Ray.parse(rows)
  local function reach(block_locked)
    local f, seen, todo = {}, {}, { { math.floor(out.start.x) + 1, math.floor(out.start.y) + 1 } }
    while #todo > 0 do
      local c = table.remove(todo)
      local key = c[2] * 1000 + c[1]
      if not seen[key] then
        local v = map.cells[c[2]] and map.cells[c[2]][c[1]]
        if v == 0 or v == Rules.DOOR or (v == Rules.LOCKED and not block_locked) then
          seen[key] = true
          todo[#todo + 1] = { c[1] + 1, c[2] }; todo[#todo + 1] = { c[1] - 1, c[2] }; todo[#todo + 1] = { c[1], c[2] + 1 }; todo[#todo + 1] = { c[1], c[2] - 1 }
        end
      end
    end
    return seen
  end
  local near = reach(true)
  local function in_set(set, px, py) return set[(math.floor(py) + 1) * 1000 + (math.floor(px) + 1)] end
  if in_set(near, out.exit.x, out.exit.y) then return nil end                        -- there is a way round the lock
  if not in_set(near, kx, ky) then return nil end                                    -- the key is behind it
  if not in_set(reach(false), out.exit.x, out.exit.y) then return nil end            -- the exit cannot be reached at all
  return out
end

-- Make level n for a seed; if an attempt will not do, the next seed is tried, so a level is always produced.
function Gen.level(n, seed)
  seed = seed or 1
  for k = 0, 200 do
    local lv = attempt(n, seed * 977 + n * 131 + k * 7919)
    if lv then lv.attempts = k + 1; return lv end
  end
  error("could not make level " .. tostring(n))
end

return Gen
