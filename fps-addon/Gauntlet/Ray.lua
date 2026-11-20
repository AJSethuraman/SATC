-- The raycaster: pure maths, no WoW calls. A map is a grid of unit squares; each is empty or a wall of some kind (1-9).
-- Walls are cast the way early first-person shooters did it: one ray per screen column, found by stepping square to square.
local _, ns = ...
ns = ns or {}
local Ray = {}
ns.Ray = Ray

local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end
Ray.atan2 = atan2

-- rows: strings, one per row, top row first. '.' or ' ' is empty; '1'..'9' are walls of that kind; anything else is wall kind 1.
function Ray.parse(rows)
  local map = { h = #rows, w = 0, cells = {} }
  for y, row in ipairs(rows) do
    map.w = math.max(map.w, #row)
    map.cells[y] = {}
    for x = 1, #row do
      local c = row:sub(x, x)
      if c == "." or c == " " then map.cells[y][x] = 0
      elseif c:match("%d") and c ~= "0" then map.cells[y][x] = tonumber(c)
      else map.cells[y][x] = 1 end
    end
  end
  return map
end

-- The wall kind at a world position (each square is 1 x 1, the top-left square spans 0..1). Outside the map is wall kind 1.
function Ray.at(map, x, y)
  local cx, cy = math.floor(x) + 1, math.floor(y) + 1
  local row = map.cells[cy]
  if not row then return 1 end
  return row[cx] or 1
end

function Ray.blocked(map, x, y) return Ray.at(map, x, y) ~= 0 end

-- Cast one ray from (ox, oy) in direction (dx, dy). Returns the distance to the wall measured along the camera direction's
-- perpendicular (so there is no fish-eye), which face was hit (0 = a wall facing left/right, 1 = facing up/down), the wall kind,
-- and how far along that wall face the hit was (0..1, for picking a column of the texture).
function Ray.cast(map, ox, oy, dx, dy, maxdist)
  maxdist = maxdist or 64
  local mx, my = math.floor(ox), math.floor(oy)
  local ddx = (dx == 0) and 1e30 or math.abs(1 / dx)
  local ddy = (dy == 0) and 1e30 or math.abs(1 / dy)
  local stepx, stepy, sdx, sdy
  if dx < 0 then stepx, sdx = -1, (ox - mx) * ddx else stepx, sdx = 1, (mx + 1 - ox) * ddx end
  if dy < 0 then stepy, sdy = -1, (oy - my) * ddy else stepy, sdy = 1, (my + 1 - oy) * ddy end
  local side, id = 0, 0
  for _ = 1, 4 * (map.w + map.h + 4) do
    if sdx < sdy then sdx, mx, side = sdx + ddx, mx + stepx, 0
    else sdy, my, side = sdy + ddy, my + stepy, 1 end
    id = Ray.at(map, mx + 0.5, my + 0.5)
    if id ~= 0 then break end
  end
  local perp
  if side == 0 then perp = (mx - ox + (1 - stepx) / 2) / dx else perp = (my - oy + (1 - stepy) / 2) / dy end
  if perp > maxdist then perp, id = maxdist, 0 end
  local wallx
  if side == 0 then wallx = oy + perp * dy else wallx = ox + perp * dx end
  wallx = wallx - math.floor(wallx)
  if (side == 0 and dx > 0) or (side == 1 and dy < 0) then wallx = 1 - wallx end         -- so the texture is not mirrored on some faces
  return perp, side, id, wallx
end

-- The camera: position, the angle it faces (radians, 0 = towards +x, growing clockwise on the map as y grows down), and the field of
-- view. Fills `out` with, for each of n columns, { dist, side, id, u }, left to right, and returns it.
function Ray.columns(map, ox, oy, ang, fov, n, out)
  out = out or {}
  local dirx, diry = math.cos(ang), math.sin(ang)
  local k = math.tan(fov / 2)
  local px, py = -diry * k, dirx * k                      -- the camera plane, at right angles to the way you face
  for i = 1, n do
    local cam = 2 * (i - 0.5) / n - 1
    local c = out[i]
    if not c then c = {}; out[i] = c end
    c.dist, c.side, c.id, c.u = Ray.cast(map, ox, oy, dirx + px * cam, diry + py * cam)
  end
  return out
end

-- Where a thing at (sx, sy) appears on screen: the column it is centred on (1..n, fractional) and how far in front of you it is.
-- Nil if it is behind you.
function Ray.sprite(ox, oy, ang, fov, n, sx, sy)
  local dirx, diry = math.cos(ang), math.sin(ang)
  local k = math.tan(fov / 2)
  local px, py = -diry * k, dirx * k
  local rx, ry = sx - ox, sy - oy
  local inv = 1 / (px * diry - dirx * py)
  local tx = inv * (diry * rx - dirx * ry)
  local ty = inv * (-py * rx + px * ry)
  if ty <= 0.05 then return nil end
  return (n / 2) * (1 + tx / ty) + 0.5, ty
end

-- Walk by (dx, dy), sliding along walls instead of stopping dead, keeping a body of radius r clear of them. Returns the new position.
function Ray.move(map, x, y, dx, dy, r)
  r = r or 0.2
  local function free(px, py)
    return not (Ray.blocked(map, px - r, py - r) or Ray.blocked(map, px + r, py - r) or Ray.blocked(map, px - r, py + r) or Ray.blocked(map, px + r, py + r))
  end
  if free(x + dx, y) then x = x + dx end
  if free(x, y + dy) then y = y + dy end
  return x, y
end

-- What a shot from (ox, oy) towards `ang` hits first: the nearest of `things` (each { x, y, r, dead }) before a wall. Returns the thing
-- and its distance, or nil. A thing is a disc of radius r; the ray hits it if it passes within r of its centre.
function Ray.hitscan(map, ox, oy, ang, things, range)
  range = range or 40
  local dx, dy = math.cos(ang), math.sin(ang)
  local wall = Ray.cast(map, ox, oy, dx, dy, range)
  local best, bestd
  for _, t in ipairs(things) do
    if not t.dead then
      local rx, ry = t.x - ox, t.y - oy
      local along = rx * dx + ry * dy
      if along > 0 and along < wall then
        local off = math.abs(rx * dy - ry * dx)
        if off <= (t.r or 0.3) and (not bestd or along < bestd) then best, bestd = t, along end
      end
    end
  end
  return best, bestd
end

return Ray
