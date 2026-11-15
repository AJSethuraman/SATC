-- Capture: what happened during a play session, recorded as it happens, so a report can be handed over without anyone writing one.
-- Pure rules (no WoW calls) except Capture.shot, which asks for a screenshot. State lives in DreadDB.cap, the last few sessions.
local _, ns = ...
local Capture = {}
ns.Capture = Capture

Capture.MAX_SESSIONS, Capture.MAX_DEATHS, Capture.MAX_ERRORS, Capture.MAX_RECENT = 3, 30, 12, 10
Capture.SHOT_GAP, Capture.SHOT_BUDGET = 15, 30            -- seconds between screenshots, and how many a session may take

function Capture.new_session(build, started)
  return { build = build or "?", started = started or 0, play = 0, area = nil, areas = {}, deaths = {}, casts = {}, kills = {}, bosses = {},
           items = { common = 0, magic = 0, rare = 0, unique = 0 }, finds = {}, levels = {}, errors = {}, shots = 0, shot_reasons = {},
           fps_n = 0, fps_sum = 0, fps_min = nil, recent = {}, last_shot = -1e9, last_hurt = -1e9 }
end

local function area_of(s, name)
  local a = s.areas[name]
  if not a then
    a = { entered = 0, time = 0, kills = 0, dealt = 0, taken = 0, deaths = 0, fps_n = 0, fps_sum = 0, fps_min = nil }
    s.areas[name] = a
  end
  return a
end

function Capture.enter(s, name)
  s.area = name
  area_of(s, name).entered = area_of(s, name).entered + 1
end

-- Time moves only while the game runs (not while the skill tree has it paused).
function Capture.tick(s, dt)
  s.play = s.play + dt
  if s.area then local a = area_of(s, s.area); a.time = a.time + dt end
end

function Capture.sample_fps(s, fps)
  if type(fps) ~= "number" or fps <= 0 then return end
  s.fps_n, s.fps_sum = s.fps_n + 1, s.fps_sum + fps
  s.fps_min = (s.fps_min == nil or fps < s.fps_min) and fps or s.fps_min
  if s.area then
    local a = area_of(s, s.area)
    a.fps_n, a.fps_sum = a.fps_n + 1, a.fps_sum + fps
    a.fps_min = (a.fps_min == nil or fps < a.fps_min) and fps or a.fps_min
  end
end

function Capture.error(s, msg)
  msg = tostring(msg):sub(1, 300)
  for _, e in ipairs(s.errors) do if e.msg == msg then e.n = e.n + 1 return end end    -- the same error every frame is one line with a count
  if #s.errors < Capture.MAX_ERRORS then s.errors[#s.errors + 1] = { msg = msg, n = 1, area = s.area, at = math.floor(s.play) } end
end

-- One game event from Combat.drain. Returns a screenshot reason when the moment is worth a picture, else nil.
function Capture.event(s, e)
  local k = e.k
  if k == "cast" then
    s.casts[e.id] = (s.casts[e.id] or 0) + 1
  elseif k == "hit" then
    if s.area and e.dmg then area_of(s, s.area).dealt = area_of(s, s.area).dealt + e.dmg end
  elseif k == "kill" then
    s.kills[e.name or "?"] = (s.kills[e.name or "?"] or 0) + 1
    if s.area then area_of(s, s.area).kills = area_of(s, s.area).kills + 1 end
  elseif k == "hurt" then
    if s.area then area_of(s, s.area).taken = area_of(s, s.area).taken + e.amount end
    s.last_hurt = s.play
    local r = s.recent
    r[#r + 1] = { from = e.from, amount = e.amount, how = e.how, boss = e.boss, t = s.play }
    if #r > Capture.MAX_RECENT then table.remove(r, 1) end
  elseif k == "level" then
    s.levels[#s.levels + 1] = { level = e.level, area = s.area, at = math.floor(s.play) }
  elseif k == "item" then
    local it = e.item
    s.items[it.rarity] = (s.items[it.rarity] or 0) + 1
    if it.rarity == "rare" or it.rarity == "unique" then
      s.finds[#s.finds + 1] = { name = ns.Items and ns.Items.name(it) or it.base, rarity = it.rarity, ilvl = it.ilvl, area = s.area }
    end
    if it.rarity == "rare" or it.rarity == "unique" then return "found " .. it.rarity end
  elseif k == "boss_dead" then
    s.bosses[#s.bosses + 1] = { name = e.name, area = s.area, at = math.floor(s.play), deaths_so_far = #s.deaths }
    return "boss " .. tostring(e.name)
  end
  return nil
end

-- You died: what killed you, in the order it happened.
function Capture.death(s, info)
  local d = { area = s.area, at = math.floor(s.play), level = info and info.level, maxlife = info and info.maxlife,
              awake = info and info.awake, boss_awake = info and info.boss_awake, hits = {} }
  for _, h in ipairs(s.recent) do
    if s.play - h.t <= 12 then d.hits[#d.hits + 1] = { from = h.from, amount = math.floor(h.amount + 0.5), how = h.how, ago = math.floor((s.play - h.t) * 10 + 0.5) / 10 } end
  end
  if #s.deaths >= Capture.MAX_DEATHS then table.remove(s.deaths, 1) end
  s.deaths[#s.deaths + 1] = d
  if s.area then area_of(s, s.area).deaths = area_of(s, s.area).deaths + 1 end
  s.recent = {}
  return "death"
end

-- May a screenshot be taken now? A gap between them, and a budget per session, so it never floods the folder.
function Capture.shot_allowed(s, reason)
  if s.shots >= Capture.SHOT_BUDGET then return false end
  if s.play - s.last_shot < Capture.SHOT_GAP then return false end
  s.shots, s.last_shot = s.shots + 1, s.play
  s.shot_reasons[#s.shot_reasons + 1] = { reason = reason, area = s.area, at = math.floor(s.play) }
  return true
end

-- A fight worth a picture now and then: you were hit in the last few seconds, and nothing has been taken for a minute and a half.
function Capture.combat_shot_due(s)
  return s.play - s.last_hurt < 4 and s.play - s.last_shot > 90
end

local function mmss(sec) sec = math.floor(sec) return string.format("%d:%02d", math.floor(sec / 60), sec % 60) end
local function avg(sum, n) return n > 0 and math.floor(sum / n + 0.5) or 0 end

-- The report, as plain text to paste. `x` carries what Capture does not own: { log = {lines}, level, gear = "text", settings = "text" }.
function Capture.report(s, x)
  x = x or {}
  local out = {}
  local function add(t) out[#out + 1] = t end
  add(string.format("DREAD REPORT   build %s   played %s   fps avg %d, lowest %d", s.build, mmss(s.play), avg(s.fps_sum, s.fps_n), s.fps_min and math.floor(s.fps_min) or 0))
  if x.level then add("Character: level " .. x.level .. (x.gear and ("   " .. x.gear) or "")) end
  if x.settings then add("Settings: " .. x.settings) end
  add("")
  add("AREAS (time, kills, damage dealt, damage taken, deaths, fps avg/lowest)")
  local names = {}
  for n in pairs(s.areas) do names[#names + 1] = n end
  table.sort(names)
  for _, n in ipairs(names) do
    local a = s.areas[n]
    add(string.format("  %-8s %6s  kills %3d  dealt %5d  taken %5d  deaths %d  fps %d/%d  (entered %dx)", n, mmss(a.time), a.kills, math.floor(a.dealt + 0.5), math.floor(a.taken + 0.5), a.deaths, avg(a.fps_sum, a.fps_n), a.fps_min and math.floor(a.fps_min) or 0, a.entered))
  end
  add("")
  add("DEATHS: " .. #s.deaths)
  for i, d in ipairs(s.deaths) do
    local parts = {}
    for _, h in ipairs(d.hits) do parts[#parts + 1] = string.format("%s %d %s (%.1fs before)", h.from, h.amount, h.how, h.ago) end
    add(string.format("  #%d  %s at %s, level %s, %s life%s: %s", i, tostring(d.area), mmss(d.at), tostring(d.level), tostring(d.maxlife and math.floor(d.maxlife) or "?"),
        d.boss_awake and ", boss awake" or "", #parts > 0 and table.concat(parts, "; ") or "no hits recorded"))
  end
  add("")
  add("BOSSES KILLED: " .. (#s.bosses == 0 and "none" or ""))
  for _, b in ipairs(s.bosses) do add(string.format("  %s in %s at %s (deaths before it: %d)", b.name, tostring(b.area), mmss(b.at), b.deaths_so_far)) end
  local casts = {}
  for id, n in pairs(s.casts) do casts[#casts + 1] = { id = id, n = n } end
  table.sort(casts, function(a, b) if a.n ~= b.n then return a.n > b.n end return a.id < b.id end)
  local cp = {}
  for _, c in ipairs(casts) do cp[#cp + 1] = c.id .. " " .. c.n end
  add("")
  add("CASTS: " .. (#cp > 0 and table.concat(cp, ", ") or "none"))
  add(string.format("ITEMS FOUND: common %d, magic %d, rare %d, unique %d", s.items.common, s.items.magic, s.items.rare, s.items.unique))
  for _, f in ipairs(s.finds) do add(string.format("  %s (%s, level %d, %s)", f.name, f.rarity, f.ilvl, tostring(f.area))) end
  if #s.levels > 0 then
    local lv = {}
    for _, l in ipairs(s.levels) do lv[#lv + 1] = string.format("%d at %s in %s", l.level, mmss(l.at), tostring(l.area)) end
    add("LEVELS: " .. table.concat(lv, "; "))
  end
  add(string.format("SCREENSHOTS: %d taken%s", s.shots, #s.shot_reasons > 0 and ("  (" .. (function() local r = {} for _, q in ipairs(s.shot_reasons) do r[#r + 1] = q.reason .. "@" .. mmss(q.at) end return table.concat(r, ", ") end)() .. ")") or ""))
  add("")
  add("ERRORS: " .. (#s.errors == 0 and "none" or ""))
  for _, e in ipairs(s.errors) do add(string.format("  x%d in %s at %s: %s", e.n, tostring(e.area), mmss(e.at), e.msg)) end
  if x.log and #x.log > 0 then
    add("")
    add("LOG (last " .. #x.log .. " lines)")
    for _, l in ipairs(x.log) do add("  " .. l) end
  end
  return table.concat(out, "\n")
end

-- Keep the saved sessions to the last few.
function Capture.session(db, build, started)
  db.cap = db.cap or { sessions = {} }
  local list = db.cap.sessions
  local s = Capture.new_session(build, started)
  list[#list + 1] = s
  while #list > Capture.MAX_SESSIONS do table.remove(list, 1) end
  return s
end

-- Take a screenshot a moment from now, so the thing that just happened is on screen. Does nothing without the client's call.
function Capture.shot()
  if not (Screenshot and C_Timer and C_Timer.After) then return false end
  C_Timer.After(0.35, function() pcall(Screenshot) end)
  return true
end

return Capture
