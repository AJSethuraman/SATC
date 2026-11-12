-- The minimap's memory: which parts of an area you have seen. Pure Lua, no WoW calls.
-- The area is cut into square cells; walking reveals the cells around you, and they stay revealed (D2-style automap).
local _, ns = ...
ns = ns or {}

local Map = {}
ns.Map = Map

Map.CELL = 60

function Map.new(w, h)
  return { w = w, h = h, cols = math.ceil(w / Map.CELL), rows = math.ceil(h / Map.CELL), seen = {}, count = 0 }
end

local function key(m, ix, iy) return iy * m.cols + ix end

-- Reveal every cell within r of (x, y) (a cell counts if any part of it is that close). Returns the list of cells
-- that were NOT seen before, as {ix, iy} (0-based), so only those need drawing.
function Map.reveal(m, x, y, r)
  local c, fresh = Map.CELL, {}
  local ix0, ix1 = math.max(0, math.floor((x - r) / c)), math.min(m.cols - 1, math.floor((x + r) / c))
  local iy0, iy1 = math.max(0, math.floor((y - r) / c)), math.min(m.rows - 1, math.floor((y + r) / c))
  for iy = iy0, iy1 do
    for ix = ix0, ix1 do
      local dx, dy = (ix + 0.5) * c - x, (iy + 0.5) * c - y
      if math.sqrt(dx * dx + dy * dy) <= r + c * 0.5 then
        local k = key(m, ix, iy)
        if not m.seen[k] then
          m.seen[k] = true
          m.count = m.count + 1
          fresh[#fresh + 1] = { ix = ix, iy = iy }
        end
      end
    end
  end
  return fresh
end

function Map.cell_of(m, x, y)
  return math.max(0, math.min(m.cols - 1, math.floor(x / Map.CELL))), math.max(0, math.min(m.rows - 1, math.floor(y / Map.CELL)))
end

function Map.is_seen(m, x, y)
  local ix, iy = Map.cell_of(m, x, y)
  return m.seen[key(m, ix, iy)] == true
end

-- A world position on a minimap mw wide and mh tall (origin bottom left).
function Map.to_mini(m, x, y, mw, mh)
  return x / m.w * mw, y / m.h * mh
end

-- Where a cell sits on the minimap: left, bottom, width, height.
function Map.cell_rect(m, ix, iy, mw, mh)
  local c = Map.CELL
  return ix * c / m.w * mw, iy * c / m.h * mh, c / m.w * mw, c / m.h * mh
end

return Map
