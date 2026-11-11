-- The places you explore. Pure data and layout, no WoW calls. Every number is a tuning knob.
--
-- Two areas for the beta: a moor with a starting camp, scattered monster packs and a cave mouth in the far corner,
-- and the cave beneath it with a boss. Killing the boss finishes the quest and pays one skill point.
--
-- Art is WoW's own, by file ID from the community listfile (fileDataIDs), e.g. 188954 is the Tirisfall grass texture.
-- Whether every ID exists in the Forever client is unproven until it has been drawn there.
local _, ns = ...
ns = ns or {}

local Zone = {}
ns.Zone = Zone

local Sim = ns.Sim

Zone.START = "moor"

-- Model ids that drew in Test 3 (SetCreature). Names and numbers are placeholders.
Zone.BESTIARY = {
  wolf   = { name = "Moor Wolf", cid = 299,  life = 20, speed = 75, dmg = { 2, 4 }, xp = 8 },
  tusker = { name = "Tusker",    cid = 3098, life = 34, speed = 52, dmg = { 3, 6 }, xp = 12 },
  mudfin = { name = "Mudfin",    cid = 46,   life = 26, speed = 62, dmg = { 2, 5 }, xp = 11, resist = { cold = 50 } },
  brute  = { name = "Brute",     cid = 6,    life = 44, speed = 55, dmg = { 3, 7 }, xp = 16 },
  imp    = { name = "Gloom Imp", cid = 3101, life = 22, speed = 78, dmg = { 2, 5 }, xp = 15, resist = { fire = 75 } },
}

-- Terrain textures and scenery models (fileDataIDs). Size is how big to draw the model; r is how big the part you bump into is.
-- Ground: a base texture tiled every `tile` units, with a second, much bigger dirt layer faded over it so the tiling is hard to see.
-- 187126 elwynn grass, 187113 elwynn dirt, 188950 tirisfall dirt-rock, 187140 elwynn gravel.
Zone.GROUND = {
  moor = { base = 187126, tint = { 0.72, 0.82, 0.55 }, tile = 512,
           overlay = 187113, overlay_tint = { 0.8, 0.7, 0.5 }, overlay_alpha = 0.22, overlay_tile = 1100,
           patch = 187070, patch_tint = { 0.6, 0.75, 0.45 }, patch_alpha = 0.3, patch_tile = 1700 },   -- duskwood grass: darker patches
  cave = { base = 188950, tint = { 0.5, 0.45, 0.45 }, tile = 512,
           overlay = 187140, overlay_tint = { 0.6, 0.55, 0.5 }, overlay_alpha = 0.22, overlay_tile = 1000,
           patch = 187113, patch_tint = { 0.45, 0.4, 0.38 }, patch_alpha = 0.3, patch_tile = 1500 },
}
Zone.SCENERY = {
  -- w, h: how big it should LOOK, in world units. r: the solid part you cannot walk through (always inside w).
  -- frame: the model's frame is this many times w, so nothing is cut off; cam: the camera distance that shrinks it back
  -- to w (a model fills its frame at distance 1, so it looks about frame/cam times w/frame = w).
  tree   = { ids = { 204124, 204129 },                   w = 80,  h = 100, r = 18, frame = 2.2, cam = 2.2 },   -- tirisfalgladetree01, canopytree02
  fallen = { ids = { 204125, 204126, 204127, 204128 },   w = 110, h = 60,  r = 18, frame = 2.0, cam = 2.0 },   -- tirisfallfallentree01-04
  bush   = { ids = { 204097, 204098, 204099 },           w = 44,  h = 36,  r = 0,  frame = 2.0, cam = 2.0 },
  grave  = { ids = { 204105, 204106, 204107, 204108 },   w = 40,  h = 44,  r = 0,  frame = 2.0, cam = 2.0 },   -- brillgraves01-04
  rock   = { ids = { 189499, 189500, 189501 },           w = 70,  h = 56,  r = 22, frame = 2.0, cam = 2.0 },   -- duskwoodboulder01-03
}

local function pick(rand, list) return list[1 + math.floor(rand() * #list)] end

local function dist(ax, ay, bx, by) return math.sqrt((ax - bx) ^ 2 + (ay - by) ^ 2) end

-- Scatter scenery with a seeded generator, keeping it off the places that must stay clear.
local function scatter(rand, area, counts, keep_clear)
  local placed = {}
  for kind, n in pairs(counts) do
    local spec, tries = Zone.SCENERY[kind], 0
    local got = 0
    while got < n and tries < n * 40 do
      tries = tries + 1
      local x, y = 40 + rand() * (area.w - 80), 40 + rand() * (area.h - 80)
      local ok = true
      for _, c in ipairs(keep_clear) do if dist(x, y, c.x, c.y) < c.r then ok = false break end end
      if ok then
        for _, o in ipairs(placed) do if dist(x, y, o.x, o.y) < 70 then ok = false break end end
      end
      if ok then
        got = got + 1
        placed[#placed + 1] = { kind = kind, id = pick(rand, spec.ids), x = x, y = y, w = spec.w, h = spec.h, r = spec.r }
      end
    end
  end
  table.sort(placed, function(a, b) if a.kind ~= b.kind then return a.kind < b.kind end return a.x < b.x end)  -- same order every run
  area.doodads = placed
  area.obstacles = {}
  for _, d in ipairs(placed) do
    if d.r > 0 then area.obstacles[#area.obstacles + 1] = { x = d.x, y = d.y, r = d.r } end
  end
end

local function add_pack(rand, area, pack_id, cx, cy, kinds, aggro, extra)
  for i, key in ipairs(kinds) do
    local t = Zone.BESTIARY[key]
    local a = (i / #kinds) * 2 * math.pi + rand()
    local m = {
      x = cx + math.cos(a) * 36, y = cy + math.sin(a) * 36, name = t.name, cid = t.cid, life = t.life, speed = t.speed,
      dmg = { t.dmg[1], t.dmg[2] }, xp = t.xp, radius = 14, pack = pack_id, aggro = aggro or 190,
      resist = { fire = (t.resist and t.resist.fire) or 0, cold = (t.resist and t.resist.cold) or 0,
                 lightning = (t.resist and t.resist.lightning) or 0, physical = (t.resist and t.resist.physical) or 0 },
    }
    for k, v in pairs(extra or {}) do m[k] = v end
    area.monsters[#area.monsters + 1] = m
  end
end

local built = {}

local function build_moor()
  local rand = Sim.rng(4242)
  local area = { name = "moor", title = "The Gloam Moor", w = 2400, h = 1500, ground = Zone.GROUND.moor.base,
                 floor = Zone.GROUND.moor, spawn = { x = 170, y = 150 }, monsters = {} }
  area.exits = { { x = 2270, y = 1340, r = 50, to = "cave", label = "Cave mouth", arrive = nil } }
  -- packs of rising danger, from the camp out to the cave
  local packs = {
    { 700, 330, { "wolf", "wolf", "wolf" } },
    { 1150, 260, { "tusker", "tusker" } },
    { 520, 760, { "wolf", "wolf", "mudfin" } },
    { 1000, 700, { "brute", "tusker", "tusker" } },
    { 1550, 430, { "mudfin", "mudfin", "imp" } },
    { 1400, 950, { "brute", "brute", "wolf", "wolf" } },
    { 820, 1150, { "imp", "imp", "wolf" } },
    { 1850, 1000, { "brute", "imp", "imp", "tusker" } },
    { 2000, 1230, { "brute", "brute", "imp", "imp" } },
  }
  local clear = { { x = area.spawn.x, y = area.spawn.y, r = 190 }, { x = 2270, y = 1340, r = 140 } }
  for _, p in ipairs(packs) do clear[#clear + 1] = { x = p[1], y = p[2], r = 90 } end   -- keep trees out of the packs
  scatter(rand, area, { tree = 34, fallen = 12, bush = 26, grave = 10, rock = 16 }, clear)
  for i, p in ipairs(packs) do add_pack(rand, area, i, p[1], p[2], p[3]) end
  area.quest = { id = "den", title = "Clear the cave", hint = "Find the cave mouth in the far corner of the moor." }
  return area
end

local function build_cave()
  local rand = Sim.rng(9001)
  local area = { name = "cave", title = "The Hollow Den", w = 1600, h = 1000, ground = Zone.GROUND.cave.base,
                 floor = Zone.GROUND.cave, spawn = { x = 150, y = 500 }, monsters = {} }
  area.exits = { { x = 50, y = 500, r = 45, to = "moor", label = "Back to the moor", arrive = { x = 2200, y = 1290 } } }
  local packs = {
    { 520, 300, { "wolf", "wolf", "imp" } },
    { 600, 720, { "mudfin", "tusker", "tusker" } },
    { 1000, 500, { "brute", "imp", "imp" } },
    { 1250, 280, { "brute", "brute", "wolf" } },
    { 1250, 760, { "brute", "imp", "imp", "wolf" } },
  }
  local clear = { { x = area.spawn.x, y = area.spawn.y, r = 150 }, { x = 1450, y = 500, r = 170 } }
  for _, p in ipairs(packs) do clear[#clear + 1] = { x = p[1], y = p[2], r = 90 } end
  scatter(rand, area, { rock = 30, fallen = 4 }, clear)
  for i, p in ipairs(packs) do add_pack(rand, area, i, p[1], p[2], p[3]) end
  -- the boss and two guards, one pack
  add_pack(rand, area, 6, 1450, 500, { "brute", "brute" }, 260)
  area.monsters[#area.monsters + 1] = {
    x = 1470, y = 500, name = "Grubb the Unwelcome", cid = 6, life = 260, speed = 58, dmg = { 6, 12 }, xp = 120,
    radius = 24, scale = 1.8, pack = 6, aggro = 260, boss = true,
    resist = { fire = 0, cold = 0, lightning = 0, physical = 0 },
  }
  area.quest = { id = "den", title = "Clear the cave", boss = "Grubb the Unwelcome", reward_points = 1 }
  return area
end

function Zone.get(name)
  if not built[name] then
    if name == "moor" then built[name] = build_moor()
    elseif name == "cave" then built[name] = build_cave()
    else return nil end
  end
  return built[name]
end

return Zone
