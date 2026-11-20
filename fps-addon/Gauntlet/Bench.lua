-- The speed test and the report. Pure: the numbers come in, the verdict and the text come out.
local _, ns = ...
ns = ns or {}
local Bench = {}
ns.Bench = Bench

Bench.COLUMNS = { 160, 240, 320 }        -- how many columns the view is cut into, one pass of the test each
Bench.SECONDS = 6                        -- how long each pass runs
Bench.PASS_FPS, Bench.LOW_FPS = 60, 30   -- a width passes if it averages this and its worst 1% of frames stays above the second number

-- Where the camera is at time t seconds: round the circle on the level's route, facing the way it is going, with a slow wobble of the
-- view so the whole run is repeatable and every column changes all the time.
function Bench.pose(t)
  local r = ns.Level.ROUTE
  local w = 0.45
  local a = w * t
  local ang = a + math.pi / 2 + 0.3 * math.sin(t * 0.9)
  return r.cx + r.r * math.cos(a), r.cy + r.r * math.sin(a), ang
end

-- Frame times (seconds) -> { n, avg, min, low } in frames per second. `low` is the average of the slowest 1% of frames.
function Bench.stats(dts)
  local n, sum, worst = #dts, 0, 0
  for _, d in ipairs(dts) do sum = sum + d; if d > worst then worst = d end end
  if n == 0 or sum <= 0 then return { n = 0, avg = 0, min = 0, low = 0 } end
  local sorted = {}
  for i, d in ipairs(dts) do sorted[i] = d end
  table.sort(sorted, function(a, b) return a > b end)
  local k = math.max(1, math.floor(n / 100))
  local tail = 0
  for i = 1, k do tail = tail + sorted[i] end
  return { n = n, avg = n / sum, min = 1 / worst, low = k / tail }
end

-- results: list of { columns, avg, low }. GO if a width of 240 or more holds 60; MAYBE if only a narrower one does; NO-GO if none does.
function Bench.verdict(results)
  local best
  for _, r in ipairs(results) do
    if r.avg >= Bench.PASS_FPS and r.low >= Bench.LOW_FPS and (not best or r.columns > best) then best = r.columns end
  end
  if best and best >= 240 then return { word = "GO", best = best } end
  if best then return { word = "MAYBE", best = best } end
  return { word = "NO-GO", best = nil }
end

local function ok(b) return b and "ok" or "FAILED" end

-- assets: { textures = { {id, name, ok} }, models = { {name, ok, file} }, sounds = { {id, ok} } }; extra: { build, size, notes }
function Bench.report(results, assets, extra)
  extra = extra or {}
  local out = {}
  local function add(t) out[#out + 1] = t end
  add("GAUNTLET REPORT   build " .. tostring(extra.build or "?") .. "   screen " .. tostring(extra.size or "?"))
  add("")
  add("TEST 1: speed (columns drawn per frame, textured, walking and turning)")
  for _, r in ipairs(results or {}) do
    add(string.format("  %3d columns   %3d fps average   %3d lowest   %3d in the slowest 1%%   %s", r.columns, math.floor(r.avg + 0.5), math.floor(r.min + 0.5), math.floor(r.low + 0.5),
        (r.avg >= Bench.PASS_FPS and r.low >= Bench.LOW_FPS) and "holds 60" or "too slow"))
  end
  if #(results or {}) == 0 then add("  not run (type /gaunt test, wait for it to finish, then /reload)") end
  local v = Bench.verdict(results or {})
  if #(results or {}) > 0 then add("  verdict: " .. v.word .. (v.best and (" (use " .. v.best .. " columns)") or "")) end
  if assets then
    add("")
    add("TEST 2: assets")
    local good, total = 0, #(assets.textures or {})
    for _, t in ipairs(assets.textures or {}) do if t.ok then good = good + 1 end end
    add(string.format("  wall textures that draw: %d of %d", good, total))
    for _, t in ipairs(assets.textures or {}) do if not t.ok then add("    no: " .. t.id .. " " .. t.name) end end
    for _, m in ipairs(assets.models or {}) do add(string.format("  model %-22s %s%s", m.name, ok(m.ok), m.file and (", file " .. tostring(m.file)) or "")) end
    for _, s in ipairs(assets.sounds or {}) do add(string.format("  sound file %d: %s", s.id, s.ok and "will play" or "will not play")) end
  end
  if extra.notes then
    add("")
    for _, n in ipairs(extra.notes) do add(n) end
  end
  return table.concat(out, "\n")
end

-- The report of a play session: how long each level took, what killed you, what you used, how it ran. run is Main's record.
local function mmss(sec) sec = math.floor(sec) return string.format("%d:%02d", math.floor(sec / 60), sec % 60) end
function Bench.game_report(run, extra)
  extra = extra or {}
  local out = {}
  local function add(t) out[#out + 1] = t end
  local fps = (run.fps_n or 0) > 0 and math.floor(run.fps_sum / run.fps_n + 0.5) or 0
  add(string.format("GAUNTLET GAME REPORT   build %s   played %s   fps avg %d, lowest %d   columns %s", tostring(extra.build or "?"), mmss(run.play or 0), fps,
      run.fps_min and math.floor(run.fps_min) or 0, tostring(extra.columns or "?")))
  add("")
  add("LEVELS (time, kills, pickups, deaths)")
  local ns_ = {}
  for n in pairs(run.levels or {}) do ns_[#ns_ + 1] = n end
  table.sort(ns_)
  for _, n in ipairs(ns_) do
    local l = run.levels[n]
    add(string.format("  %d %-22s %6s  kills %2d/%2d  pickups %2d/%2d  deaths %d%s", n, tostring(l.name), mmss(l.time or 0), l.kills or 0, l.total or 0, l.picked or 0, l.pickups or 0, l.deaths or 0,
        l.done and "  done" or ""))
  end
  if run.mouse then add(string.format("MOUSE: turns seen from cursor movement %d, from facing %d", run.mouse.delta or 0, run.mouse.facing or 0)) end
  add("")
  add("DEATHS: " .. #(run.deaths or {}))
  for i, d in ipairs(run.deaths or {}) do
    add(string.format("  #%d  level %d at %s: %s", i, d.level, mmss(d.at or 0), d.hits or "?"))
  end
  local hb = {}
  for name, v in pairs(run.hurt_by or {}) do hb[#hb + 1] = { name = name, v = v } end
  table.sort(hb, function(a, b) if a.v ~= b.v then return a.v > b.v end return a.name < b.name end)
  local parts = {}
  for _, h in ipairs(hb) do parts[#parts + 1] = string.format("%s %d", h.name, math.floor(h.v + 0.5)) end
  add("DAMAGE TAKEN FROM: " .. (#parts > 0 and table.concat(parts, ", ") or "nothing"))
  local sh = {}
  for name, v in pairs(run.shots or {}) do sh[#sh + 1] = { name = name, v = v } end
  table.sort(sh, function(a, b) if a.v ~= b.v then return a.v > b.v end return a.name < b.name end)
  parts = {}
  for _, h in ipairs(sh) do parts[#parts + 1] = h.name .. " " .. h.v end
  add("SHOTS FIRED: " .. (#parts > 0 and table.concat(parts, ", ") or "none"))
  add("SCREENSHOTS: " .. (run.shots_taken or 0))
  add("ERRORS: " .. (#(run.errors or {}) == 0 and "none" or ""))
  for _, e in ipairs(run.errors or {}) do add(string.format("  x%d: %s", e.n, e.msg)) end
  return table.concat(out, "\n")
end

return Bench
