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
  local v = Bench.verdict(results or {})
  add("  verdict: " .. v.word .. (v.best and (" (use " .. v.best .. " columns)") or ""))
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

return Bench
