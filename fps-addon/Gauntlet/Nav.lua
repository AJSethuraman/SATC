-- Finding a way round walls: how many steps every square is from a goal, so a monster that cannot see you can still walk to you.
local _, ns = ...
ns = ns or {}
local Nav = {}
ns.Nav = Nav

-- Can a monster walk through this square? Empty squares, and ordinary doors (they open for it); locked doors, no.
function Nav.walkable(map, cx, cy)
  local row = map.cells[cy]
  local v = row and row[cx]
  return v ~= nil and (v == 0 or v == 5)
end

-- Steps from (gx, gy), a world position, to every walkable square, by flood fill. field[cy][cx] = steps, nil if unreachable. Four directions.
function Nav.field(map, gx, gy)
  local f, queue, head = {}, {}, 1
  for y = 1, map.h do f[y] = {} end
  local sx, sy = math.floor(gx) + 1, math.floor(gy) + 1
  if not Nav.walkable(map, sx, sy) then return f end
  f[sy][sx] = 0
  queue[1] = { sx, sy }
  while queue[head] do
    local c = queue[head]; head = head + 1
    local d = f[c[2]][c[1]]
    for _, step in ipairs({ { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }) do
      local nx, ny = c[1] + step[1], c[2] + step[2]
      if f[ny] and f[ny][nx] == nil and Nav.walkable(map, nx, ny) then
        f[ny][nx] = d + 1
        queue[#queue + 1] = { nx, ny }
      end
    end
  end
  return f
end

-- Where to head from (x, y) to get nearer the goal the field was made for: the middle of the neighbouring square with the lowest
-- count, or nil if there is none lower (you are there, or cut off). Diagonals are used only when both squares beside are walkable.
function Nav.next(field, map, x, y)
  local cx, cy = math.floor(x) + 1, math.floor(y) + 1
  local here = field[cy] and field[cy][cx]
  if not here then return nil end
  local best, bx, by = here, nil, nil
  for dy = -1, 1 do
    for dx = -1, 1 do
      if dx ~= 0 or dy ~= 0 then
        local nx, ny = cx + dx, cy + dy
        local v = field[ny] and field[ny][nx]
        local ok = v ~= nil
        if ok and dx ~= 0 and dy ~= 0 then ok = Nav.walkable(map, cx + dx, cy) and Nav.walkable(map, cx, cy + dy) end
        if ok and v < best then best, bx, by = v, nx - 0.5, ny - 0.5 end
      end
    end
  end
  return bx, by
end

return Nav
