-- The test level: one map, four wall kinds, a few places to stand things. Pure data.
local _, ns = ...
ns = ns or {}
local Level = {}
ns.Level = Level

-- 1 stone, 2 brick, 3 old stone, 4 dark brick. A big room in the middle (for the speed test's route), a corridor, two side rooms.
Level.ROWS = {
  "111111111111111111111111",
  "1......1...............1",
  "1......1...............1",
  "1......1...............1",
  "1......................1",
  "1......1...............1",
  "1111.111...............1",
  "1..........222.222.....1",
  "1..........2.....2.....1",
  "1..........2.....2.....1",
  "1..........222.222.....1",
  "1......................1",
  "1.33333................1",
  "1.3...3.....44444......1",
  "1.3...3.....4....4.....1",
  "1.3...3.....4....4.....1",
  "1.3.333.....444.44.....1",
  "1......................1",
  "111111111111111111111111",
}
Level.START = { x = 3.5, y = 4.5, angle = 0 }

-- Where the speed test walks: a circle in the open middle of the big room, always inside open squares.
Level.ROUTE = { cx = 16.5, cy = 4.5, r = 2 }

-- Things standing about for the model test: creature ids that drew in the last game, and one bare model file.
Level.ENEMIES = {
  { x = 10.5, y = 4.5, r = 0.35, cid = 299, name = "wolf" },
  { x = 14.5, y = 11.5, r = 0.35, cid = 6, name = "kobold" },
  { x = 20.5, y = 8.5, r = 0.35, cid = 3098, name = "boar" },
  { x = 4.5, y = 9.5, r = 0.35, cid = 46, name = "murloc" },
  { x = 8.5, y = 16.5, r = 0.35, cid = 3101, name = "imp" },
  { x = 18.5, y = 15.5, r = 0.35, model = 126570, name = "zombie (bare model)" },
}

-- Wall kinds -> texture file ids (dungeon walls from the community listfile), then plain colours if a texture will not draw.
Level.WALLS = {
  [1] = { file = 129765, color = { 0.55, 0.52, 0.5 }, name = "uldaman plain wall" },
  [2] = { file = 2316172, color = { 0.6, 0.35, 0.3 }, name = "warsong brick wall" },
  [3] = { file = 126995, color = { 0.4, 0.5, 0.55 }, name = "blackfathom stone wall" },
  [4] = { file = 2930451, color = { 0.45, 0.25, 0.3 }, name = "vampire brick" },
}

-- Other wall textures to look at in the asset test, with what they are.
Level.CANDIDATES = {
  { 126995, "blackfathom stone wall" }, { 129765, "uldaman plain wall" }, { 129717, "lordaeron chamber wall" }, { 129723, "lordaeron wall" },
  { 129919, "dwarven wall" }, { 130209, "tauren wall" }, { 130320, "wyrmrest bricks" }, { 428572, "orc wall" },
  { 1720743, "jungle brick wall" }, { 2316172, "warsong brick wall" }, { 2930451, "vampire brick" }, { 1249327, "rock brick wall" },
  { 418811, "goblin wood wall" }, { 129439, "cave wall" },
}

-- Sounds to try on a shot: file ids of gunfire, and one bullet impact.
Level.SHOTS = { 567721, 567718, 567722 }
Level.IMPACT = 1315092

return Level
