-- The game window: puts the Play world on screen, reads the keys and the mouse, and moves from level to level. /gaunt plays.
local _, ns = ...
ns = ns or {}
local Main = {}
ns.Main = Main

local Rules, Ray, Play, Render, Bench = ns.Rules, ns.Ray, ns.Play, ns.Render, ns.Bench

local R                                -- the drawing state (Render.build)
local G                                -- the game's own state: stage, world, run record
local colbuf = {}

Main.COLUMNS = 320
Main.SCALE = nil          -- nil: fit the window to the screen; /gaunt scale N sets it
Main.SHOT_GAP, Main.SHOT_BUDGET = 15, 40
Main.mouse = true
Main.look = true         -- the mouse is locked to the middle and turns the view; where the client cannot lock it, the view turns with the cursor's movement
Main.debug = true        -- a line of mouse readings is shown while the lock is on
Main.edge = false        -- /gaunt mouse edge: the old turn, speed set by how far the cursor is from the middle (it keeps turning while it is off-centre)
Main.SENS = 0.0035       -- radians per pixel of mouse movement (/gaunt mouse sens N)

local TURN, KEYTURN, DEAD, SPEED = 5.0, 2.3, 0.08, 3.4
local KEYS = { W = true, A = true, S = true, D = true, Q = true, E = true, LEFT = true, RIGHT = true, UP = true, DOWN = true, SPACE = true,
               ["1"] = true, ["2"] = true, ["3"] = true, ["4"] = true, ENTER = true }

local function say(msg) print("|cffffaa33Gauntlet|r " .. msg) end

local function db()
  GauntletDB = GauntletDB or {}
  return GauntletDB
end

---------------------------------------------------------------- sounds, messages, pictures
local last_sound = {}
local function sound(name, index)
  if not PlaySoundFile then return end
  local id = Rules.SOUNDS[name]
  if type(id) == "table" then id = id[index or 1] end
  if not id then return end
  local t = G and G.clock or 0
  if last_sound[name] and t - last_sound[name] < 0.08 then return end
  last_sound[name] = t
  pcall(PlaySoundFile, id, "Master")
end
Main.sound = sound

local function message(text, seconds)
  G.msg, G.msg_t = text, seconds or 2.5
  R.msg:SetText(text)
end

local function shot(why)
  local run = G.run
  if db().shots == false then return false end
  if run.shots_taken >= Main.SHOT_BUDGET or G.clock - G.last_shot < Main.SHOT_GAP then return false end
  if not (Screenshot and C_Timer and C_Timer.After) then return false end
  run.shots_taken, G.last_shot = run.shots_taken + 1, G.clock
  C_Timer.After(0.35, function() pcall(Screenshot) end)
  return true
end

---------------------------------------------------------------- the run's record (for the report)
local function new_run()
  return { play = 0, levels = {}, deaths = {}, hurt_by = {}, shots = {}, shots_taken = 0, errors = {}, fps_n = 0, fps_sum = 0, fps_min = nil, started = time and time() or 0, mouse = { delta = 0, facing = 0, pos = 0 } }
end

local function level_rec(n)
  local l = G.run.levels[n]
  if not l then l = { name = Rules.LEVEL_NAMES[n] or ("Level " .. n), time = 0, kills = 0, total = 0, picked = 0, pickups = 0, deaths = 0 }; G.run.levels[n] = l end
  return l
end

local function save_report()
  db().game_report = Bench.game_report(G.run, { build = ns.BUILD, columns = R.n })
end

---------------------------------------------------------------- levels
local function save_progress(n, carry)
  db().progress = { level = n, seed = G.seed, carry = carry }
end

function Main.begin_level(n, carry)
  G.n, G.level_carry = n, carry or Rules.START
  G.w = Play.new(n, G.seed + n * 101, G.level_carry)
  G.stage, G.t_level = "play", 0
  G.hurt, G.pick = 0, 0
  local rec = level_rec(n)
  rec.total, rec.pickups = G.w.stats.total, G.w.stats.pickups_total
  G.title, G.mlabel = string.format("Gauntlet   level %d: %s", n, G.w.lv.name), nil
  R.title:SetText(G.title)
  message(string.format("LEVEL %d: %s", n, string.upper(G.w.lv.name)), 3)
  if n == 1 and not carry then save_progress(1, nil) else save_progress(n, G.level_carry) end
  Render.set_columns(R, Main.COLUMNS)
  Render.WALLS = Rules.WALLS
end

local function weapon_icon(w) return Rules.WEAPONS[w.player.weapon].icon end

---------------------------------------------------------------- drawing
local TINT_EXIT = { 0.6, 1, 0.6 }

local function things(w, boss_alive)
  local list = {}
  for _, it in ipairs(w.pickups) do
    if not it.taken then list[#list + 1] = { x = it.x, y = it.y, icon = Rules.ITEMS[it.kind].icon, size = 0.3, lift = 0.02 + 0.015 * math.sin(G.clock * 3 + it.x) } end
  end
  for _, s in ipairs(w.shots) do list[#list + 1] = { x = s.x, y = s.y, icon = "Spell_Fire_Fireball02", size = s.boss and 0.6 or 0.4, lift = 0.15, tint = s.boss and { 0.8, 0.4, 1 } or nil } end
  for _, r in ipairs(w.rockets) do list[#list + 1] = { x = r.x, y = r.y, icon = "INV_Misc_Bomb_02", size = 0.3, lift = 0.15 } end
  list[#list + 1] = { x = w.exit.x, y = w.exit.y, icon = "Spell_Holy_DivineIntervention", size = 0.7, lift = 0.1, tint = boss_alive and { 1, 0.3, 0.3 } or TINT_EXIT }
  return list
end

local function boss_alive(w)
  for _, e in ipairs(w.enemies) do if e.def.boss and not e.dead then return true end end
  return false
end

local function draw(dt)
  local w, p = G.w, G.w.player
  Ray.columns(w.map, p.x, p.y, p.ang, Render.FOV, R.n, colbuf)
  Render.walls(R, colbuf)
  Render.game_models(R, p.x, p.y, p.ang, colbuf, w.enemies, w.time)
  Render.sprites(R, p.x, p.y, p.ang, colbuf, things(w, w.lv.boss and boss_alive(w)))
  Render.set_weapon(R, weapon_icon(w))
  Render.weapon(R, G.walk, p.kick)
  -- screen tints: red when hurt, gold when you pick something up
  G.hurt = math.max(0, G.hurt - dt * 1.6)
  G.pick = math.max(0, G.pick - dt * 2.5)
  R.tint:SetAlpha(G.hurt)
  R.gold:SetAlpha(G.pick * 0.35)
  if G.msg_t and G.msg_t > 0 then
    G.msg_t = G.msg_t - dt
    if G.msg_t <= 0 and G.stage == "play" then R.msg:SetText("") end
  end
  -- the bar at the bottom
  R.h_hp:SetText(string.format("HEALTH %d", math.floor(p.hp + 0.5)))
  R.h_ar:SetText(string.format("ARMOR %d", math.floor(p.armor + 0.5)))
  local wp = Rules.WEAPONS[p.weapon]
  R.h_ammo:SetText(string.format("%s: %d", wp.name, p.ammo[wp.ammo]))
  R.h_keys:SetText(p.key_count > 0 and ("KEY x" .. p.key_count) or "")
  R.h_lvl:SetText(string.format("kills %d/%d", w.stats.kills, w.stats.total))
  for i = 1, 4 do
    local slot = R.slots[i]
    slot:SetAlpha(p.weapons[i] and (i == p.weapon and 1 or 0.5) or 0.12)
  end
  R.hud:SetText(string.format("%d fps", dt > 0 and math.floor(1 / dt + 0.5) or 0))
end

---------------------------------------------------------------- events
local function handle(e)
  local run, w = G.run, G.w
  local k = e.k
  if k == "shot" then
    sound("shot", e.sound)
    local name = Rules.WEAPONS[e.weapon].id
    run.shots[name] = (run.shots[name] or 0) + 1
  elseif k == "hit" then
    sound("impact")
  elseif k == "kill" then
    sound("die")
    if e.boss then message("GOREFANG IS DOWN! Find the way out.", 4); shot("boss") end
  elseif k == "wake" then
    sound("wake")
  elseif k == "hurt" then
    sound("hurt")
    G.hurt = math.min(0.55, 0.2 + e.amount / 60)
    run.hurt_by[e.from or "?"] = (run.hurt_by[e.from or "?"] or 0) + e.amount
    G.last_hits[#G.last_hits + 1] = string.format("%s %d", tostring(e.from), math.floor(e.amount + 0.5))
    if #G.last_hits > 6 then table.remove(G.last_hits, 1) end
  elseif k == "bite" then
    sound("bite")
  elseif k == "enemyshot" then
    sound(e.fire and "fire" or "shot", 1)
  elseif k == "explode" then
    sound("explode")
  elseif k == "pickup" then
    sound("pickup")
    G.pick = 1
    message("Picked up: " .. e.name, 1.5)
  elseif k == "door" then
    sound("door")
  elseif k == "unlock" then
    sound("door")
    message("Unlocked with the key", 2)
  elseif k == "locked" then
    message("Locked. Find the iron key.", 2)
  elseif k == "empty" then
    message("Out of ammo", 1.2)
  elseif k == "blocked_exit" then
    message("Defeat Gorefang first!", 2)
  elseif k == "switch" then
    message(Rules.WEAPONS[e.weapon].name, 1)
  end
end

local function finish_level(won)
  local w, rec = G.w, level_rec(G.n)
  rec.done = true
  rec.kills, rec.picked = w.stats.kills, w.stats.picked
  G.stage = won and "win" or "levelend"
  sound("win")
  shot(won and "win" or "level")
  local t = string.format("%d:%02d", math.floor(w.time / 60), math.floor(w.time) % 60)
  if won then
    message(string.format("YOU WIN!   %s  kills %d/%d.   SPACE plays again", t, w.stats.kills, w.stats.total), 600)
    db().progress = nil
    local best = db().best
    if not best or w.time < best then db().best = w.time end
  else
    message(string.format("LEVEL COMPLETE   %s  kills %d/%d  pickups %d/%d.   SPACE for the next level", t, w.stats.kills, w.stats.total, w.stats.picked, w.stats.pickups_total), 600)
  end
  save_report()
end

local function died()
  local rec = level_rec(G.n)
  rec.deaths = rec.deaths + 1
  rec.kills, rec.picked = G.w.stats.kills, G.w.stats.picked
  G.run.deaths[#G.run.deaths + 1] = { level = G.n, at = G.run.play, hits = table.concat(G.last_hits, "; ") }
  G.stage = "dead"
  message("YOU DIED.   SPACE tries the level again", 600)
  shot("death")
  save_report()
end

-- SPACE or a click on an end screen: carry on.
function Main.advance()
  if G.stage == "dead" then
    Main.begin_level(G.n, G.level_carry)
  elseif G.stage == "levelend" then
    Main.begin_level(G.n + 1, Play.carry(G.w))
  elseif G.stage == "win" then
    G.seed = (time and time() or 1) + G.n
    Main.begin_level(1, nil)
  end
end

---------------------------------------------------------------- the clock
-- True mouse look: the client's own mouselook turns the player with the mouse; the change in GetPlayerFacing each frame is how far
-- you turned, so the view follows the mouse exactly (no cursor to run out of screen). Falls back to the cursor-offset turn.
-- Instances hide the facing (it comes back nil), so look only when a value is really available.
local function look_on()
  return Main.mouse and Main.look and MouselookStart and MouselookStop and (GetCursorDelta or (GetPlayerFacing and GetPlayerFacing() ~= nil)) and true or false
end

-- How far the mouse turned you this frame, in radians (right is positive). Two sources, because clients differ: the cursor's own
-- movement (GetCursorDelta, pixels) and the change in the player's facing. Which one worked is counted, so the report can say.
local function look_turn()
  local m = G.run.mouse
  -- the facing baseline moves every frame, whichever signal is used, so a turn is never counted twice (mouselook turns the player too)
  local d = 0
  local f = GetPlayerFacing and GetPlayerFacing()
  if f then
    local last = G.face
    G.face = f
    if last then
      d = f - last
      if d > math.pi then d = d - 2 * math.pi elseif d < -math.pi then d = d + 2 * math.pi end
    end
  end
  if GetCursorDelta then
    local dx = GetCursorDelta()                 -- read once per frame: the client resets it on each read
    G.read_delta = dx
    if dx and dx ~= 0 then m.delta = m.delta + 1; return dx * Main.SENS end
  end
  if d ~= 0 then m.facing = m.facing + 1; return -d end      -- facing grows turning left; our angle grows turning right
  -- third signal: some clients keep reporting the cursor position while it is locked
  if GetCursorPosition then
    local x = GetCursorPosition()
    local last = G.lx
    G.lx = x
    if x and last and x ~= last then m.pos = m.pos + 1; return (x - last) * Main.SENS end
  end
  return 0
end

-- Keep the client's mouselook on while you play. A click (or anything else that grabs the mouse) ends it without telling us, so each frame
-- asks the client whether it is still looking and starts it again if not; our own flag alone would say "looking" long after it stopped.
local function mouselook(on)
  if not (MouselookStart and MouselookStop) then return end
  if on then
    local client = true
    if IsMouselooking then client = IsMouselooking() and true or false end
    if not G.looking or not client then MouselookStart(); G.looking = true; G.face = nil end
  elseif G.looking or (IsMouselooking and IsMouselooking()) then
    MouselookStop(); G.looking = false
  end
end

-- No lock available: turn by how far the cursor moved since the last frame. A still cursor does not turn you, so nothing sways.
local function free_turn()
  if not (Main.mouse and GetCursorPosition) then G.cx = nil; return 0 end
  local mx = GetCursorPosition()
  if not mx then return 0 end
  local last = G.cx
  G.cx = mx
  if not last then return 0 end
  return (mx - last) * Main.SENS
end

-- A line of what the client reports about the mouse, shown while the lock is on (/gaunt mouse debug hides it): for a client that gives no signal.
local function mouse_debug_line()
  local function v(fn, ...) if not fn then return "none" end local ok, a = pcall(fn, ...) if not ok then return "error" end return a == nil and "nil" or (type(a) == "number" and string.format("%.3f", a) or tostring(a)) end
  return string.format("facing %s   delta %s   cursor %s   locked %s   seen: delta %d  facing %d  cursor %d", v(GetPlayerFacing), GetCursorDelta and tostring(G.read_delta) or "none", v(GetCursorPosition),
    tostring(IsMouselooking and IsMouselooking() or false), G.run.mouse.delta, G.run.mouse.facing, G.run.mouse.pos or 0)
end

local function mouse_turn()
  if not (Main.mouse and GetCursorPosition) then return 0 end
  local mx = GetCursorPosition()
  if not mx then return 0 end
  -- measured across the whole screen (the catcher frame keeps the cursor from ever being "outside"); the window's own width if the screen size is unknown
  local off
  local uw = UIParent and UIParent.GetWidth and UIParent:GetWidth()
  local us = UIParent and UIParent.GetEffectiveScale and UIParent:GetEffectiveScale()
  if type(uw) == "number" and uw > 0 and type(us) == "number" and us > 0 then
    off = (mx / us - uw / 2) / (uw / 2)
  else
    local scale = R.frame:GetEffectiveScale() or 1
    local cx = R.frame:GetCenter()
    if not cx then return 0 end
    off = (mx / scale - cx) / (Render.VW / 2)
  end
  if math.abs(off) < DEAD then return 0 end
  off = math.max(-1, math.min(1, off))
  return (off * 0.5 + off * math.abs(off) * 0.5) * TURN      -- gentle near the middle, quick toward the edge
end

local function play_frame(dt)
  local w, k = G.w, G.keys
  local p = w.player
  local fwd = (k.W and 1 or 0) - (k.S and 1 or 0) + (k.UP and 1 or 0) - (k.DOWN and 1 or 0)
  local side = (k.D and 1 or 0) - (k.A and 1 or 0)
  local turn = (k.E and 1 or 0) - (k.Q and 1 or 0) + (k.RIGHT and 1 or 0) - (k.LEFT and 1 or 0)
  p.ang = p.ang + turn * KEYTURN * dt
  local label = not Main.mouse and "mouse off" or look_on() and "mouse locked" or Main.edge and "mouse: edge turn" or "mouse: follows cursor"
  if G.mlabel ~= label and G.title then G.mlabel = label; R.title:SetText(G.title .. "     [" .. label .. "]") end
  if Main.debug and R.dbg then R.dbg:SetText(look_on() and mouse_debug_line() or "") end
  if look_on() then G.cx = nil; mouselook(true); p.ang = p.ang + look_turn() else mouselook(false); if Main.edge then G.cx = nil; p.ang = p.ang + mouse_turn() * dt else p.ang = p.ang + free_turn() end end
  Play.move(w, fwd, side, dt, SPEED)
  if fwd ~= 0 or side ~= 0 then G.walk = G.walk + dt end
  local held = G.mouse_down or (IsMouseButtonDown and IsMouseButtonDown("LeftButton"))
  if k.SPACE or held then Play.fire(w) end
  Play.step(w, dt)
  local evs = w.events
  w.events = {}
  for _, e in ipairs(evs) do handle(e) end
  G.t_level = G.t_level + dt
  level_rec(G.n).time = G.t_level
  if w.won then finish_level(true) elseif w.done then finish_level(false) elseif w.over then died() end
end

local function frame_body(dt)
  if dt > 0.1 then dt = 0.1 end
  G.clock = G.clock + dt
  G.run.play = G.run.play + dt
  G.fps_t = G.fps_t + dt
  if G.fps_t >= 1 and dt > 0 then
    G.fps_t = 0
    local fps = 1 / dt
    local r = G.run
    r.fps_n, r.fps_sum = r.fps_n + 1, r.fps_sum + fps
    r.fps_min = (r.fps_min == nil or fps < r.fps_min) and fps or r.fps_min
  end
  if G.stage ~= "play" then mouselook(false); G.cx = nil end        -- end screens need a visible cursor to click
  if G.stage == "play" then
    play_frame(dt)
    if G.w.over and G.stage == "play" then died() end
    if G.stage == "play" and G.t_level > 90 and G.clock - G.last_shot > 90 and G.hurt > 0.3 then shot("fight") end
  end
  draw(dt)
end

local function on_update(_, dt)
  if Main.rethrow then return frame_body(dt) end
  local ok, err = pcall(frame_body, dt)
  if not ok then
    local msg = tostring(err):sub(1, 300)
    local found
    for _, e in ipairs(G.run.errors) do if e.msg == msg then e.n = e.n + 1; found = true end end
    if not found and #G.run.errors < 12 then
      G.run.errors[#G.run.errors + 1] = { msg = msg, n = 1 }
      say("|cffff5555error|r " .. msg:sub(1, 200) .. "   (/gaunt report has it)")
    end
  end
end

---------------------------------------------------------------- the window
local function build_hud()
  local f, v = R.frame, R.view
  R.dbg = v:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
  R.dbg:SetPoint("TOPLEFT", v, "TOPLEFT", 8, -6)
  local function text(x, w_)
    local fs = f:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    fs:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", x, 10)
    return fs
  end
  R.h_hp, R.h_ar, R.h_ammo, R.h_keys, R.h_lvl = text(10), text(130), text(235), text(480), text(560)
  R.tint = v:CreateTexture(nil, "OVERLAY")
  R.tint:SetAllPoints(v); R.tint:SetColorTexture(0.8, 0, 0, 1); R.tint:SetAlpha(0)
  R.gold = v:CreateTexture(nil, "OVERLAY")
  R.gold:SetAllPoints(v); R.gold:SetColorTexture(1, 0.85, 0.3, 1); R.gold:SetAlpha(0)
  R.slots = {}
  for i = 1, 4 do
    local t = v:CreateTexture(nil, "OVERLAY")
    t:SetSize(30, 30)
    t:SetPoint("BOTTOMRIGHT", v, "BOTTOMRIGHT", -8 - (4 - i) * 34, 6)
    pcall(t.SetTexture, t, "Interface\\Icons\\" .. Rules.WEAPONS[i].icon)
    t:SetAlpha(0.12)
    R.slots[i] = t
  end
end

local function ensure_window()
  if R then return end
  R = Render.build("GauntletGameFrame")
  if db().mouse_mode then Main.set_mouse_mode(db().mouse_mode) end        -- what /gaunt mousetest found works on this client
  if R.frame.SetScale then R.frame:SetScale(Main.scale()) end
  build_hud()
  R.frame:SetScript("OnUpdate", on_update)
  R.frame:SetScript("OnKeyDown", function(self, key)
    if key == "ESCAPE" then self:SetPropagateKeyboardInput(false); Main.stop(); return end
    if KEYS[key] and G then
      self:SetPropagateKeyboardInput(false)
      if G.stage ~= "play" then
        if key == "SPACE" or key == "ENTER" then Main.advance() end
        return
      end
      if key >= "1" and key <= "4" and #key == 1 then Play.select(G.w, tonumber(key)); return end
      G.keys[key] = true
    else
      self:SetPropagateKeyboardInput(true)
    end
  end)
  R.frame:SetScript("OnKeyUp", function(self, key) if G and G.keys then G.keys[key] = nil end end)
  -- A see-through frame over the whole screen, just under the game window: while you play, no click can reach anything else.
  local catcher = CreateFrame("Frame", nil, UIParent)
  catcher:SetAllPoints(UIParent); catcher:SetFrameStrata("HIGH"); catcher:EnableMouse(true)
  catcher:Hide()
  R.catcher = catcher
  local function down(self, button)
    if button == "LeftButton" and G then if G.stage == "play" then G.mouse_down = true else Main.advance() end end
  end
  catcher:EnableMouseWheel(true)
  catcher:SetScript("OnMouseWheel", function(self, delta) if G and G.stage == "play" then Play.cycle(G.w, delta > 0 and -1 or 1) end end)
  catcher:SetScript("OnMouseDown", down)
  catcher:SetScript("OnMouseUp", function(self, button) if button == "LeftButton" and G then G.mouse_down = false end end)
  R.frame:SetScript("OnMouseDown", function(self, button)
    if button ~= "LeftButton" or not G then return end
    if G.stage == "play" then G.mouse_down = true else Main.advance() end
  end)
  R.frame:SetScript("OnMouseUp", function(self, button) if button == "LeftButton" and G then G.mouse_down = false end end)
  R.frame:EnableMouseWheel(true)
  R.frame:SetScript("OnMouseWheel", function(self, delta) if G and G.stage == "play" then Play.cycle(G.w, delta > 0 and -1 or 1) end end)
  local drag = CreateFrame("Frame", nil, R.frame)
  drag:SetPoint("TOPLEFT"); drag:SetPoint("TOPRIGHT"); drag:SetHeight(22); drag:EnableMouse(true)
  drag:RegisterForDrag("LeftButton")
  drag:SetScript("OnDragStart", function() R.frame:StartMoving() end)
  drag:SetScript("OnDragStop", function() R.frame:StopMovingOrSizing() end)
end

-- Open the game: where you left off, or the first level.
function Main.start(fresh)
  ensure_window()
  if G and G.w and G.stage ~= "win" and not fresh and R.frame:IsShown() then return end
  G = { stage = "play", keys = {}, walk = 0, clock = 0, fps_t = 0, last_shot = -99, hurt = 0, pick = 0, last_hits = {}, run = new_run(),
        seed = (time and time() or 1) % 100000 }
  local prog = (not fresh) and db().progress
  R.frame:Show()
  if R.catcher then R.catcher:Show() end
  if prog and prog.level and prog.carry then
    G.seed = prog.seed or G.seed
    say("continuing at level " .. prog.level .. "  (/gaunt new starts over)")
    Main.begin_level(prog.level, prog.carry)
  else
    if fresh then db().progress = nil end
    Main.begin_level(1, nil)
  end
end

-- The window's scale: what you set, or the largest that fits the screen (the view is 16:9, so it fills most of it).
function Main.scale()
  if Main.SCALE then return Main.SCALE end
  local uw = UIParent and UIParent.GetWidth and UIParent:GetWidth()
  local uh = UIParent and UIParent.GetHeight and UIParent:GetHeight()
  if type(uw) ~= "number" or type(uh) ~= "number" or uw <= 0 or uh <= 0 then return 1.5 end
  return math.max(1, math.min(3, uw * 0.94 / (Render.VW + 16), uh * 0.92 / (Render.VH + 64)))
end

-- The mouse test picks "look" (lock the mouse), "free" (turn with the cursor's movement) or "edge" (turn by distance from the middle).
function Main.set_mouse_mode(mode)
  Main.mouse = true
  Main.look, Main.edge = (mode == "look"), (mode == "edge")
  if G and not Main.look then mouselook(false) end
end

function Main.stop()
  if G then mouselook(false) end
  if G and G.run then save_report() end
  if R then R.frame:Hide(); if R.catcher then R.catcher:Hide() end end
end

function Main.state() return G end
function Main.render() return R end

function Main.report_text()
  if G and G.run then return Bench.game_report(G.run, { build = ns.BUILD, columns = R and R.n }) end
  return db().game_report
end

function Main.set_columns(n)
  n = math.floor(tonumber(n) or Main.COLUMNS)
  Main.COLUMNS = math.max(80, math.min(Render.MAXCOLS, n))
  if R and G then Render.set_columns(R, Main.COLUMNS) end
  return Main.COLUMNS
end

SLASH_GAUNTLET1 = "/gaunt"
SlashCmdList.GAUNTLET = function(arg)
  arg = (arg or ""):lower():match("^%s*(.-)%s*$")
  local Gauntlet = ns.Gauntlet
  if arg == "" then Gauntlet.stop(); Main.probe_report = false; Main.start(false)
  elseif arg == "new" then Gauntlet.stop(); Main.probe_report = false; Main.start(true)
  elseif arg == "test" then Main.stop(); Main.probe_report = true; Gauntlet.run()
  elseif arg == "walk" then Main.stop(); Gauntlet.walk()
  elseif arg == "report" then
    local text
    if Main.probe_report then text = Gauntlet.report_text(); if not text then say("the speed test has not finished yet; wait for it, then try again"); return end else text = Main.report_text() or Gauntlet.report_text() end
    if text then Gauntlet.copy_text(text) else say("no report yet: play first with /gaunt") end
  elseif arg == "stop" then Main.stop(); if Gauntlet then Gauntlet.stop() end
  elseif arg == "mousetest" then ns.MouseProbe.start()
  elseif arg:match("^scale") then
    local n = tonumber(arg:match("^scale%s+([%d%.]+)"))
    Main.SCALE = n and math.max(0.6, math.min(3, n)) or nil
    if R and R.frame.SetScale then R.frame:SetScale(Main.scale()) end
    say("scale: " .. (Main.SCALE and tostring(Main.SCALE) or "fit to screen"))
  elseif arg:match("^cols") then say("columns: " .. Main.set_columns(arg:match("^cols%s+(%d+)")))
  elseif arg:match("^shots") then
    local on = arg:match("^shots%s+(%a+)")
    if on == "off" then db().shots = false elseif on == "on" then db().shots = true end
    say("automatic screenshots: " .. (db().shots == false and "off" or "on"))
  elseif arg:match("^mouse") then
    local w = arg:match("^mouse%s+(%a+)")
    if w == "on" then Main.mouse = true elseif w == "off" then Main.mouse = false; if G then mouselook(false) end
    elseif arg:match("^mouse%s+sens") then Main.SENS = math.max(0.0005, math.min(0.02, tonumber(arg:match("sens%s+([%d%.]+)")) or Main.SENS)); say("mouse sensitivity: " .. Main.SENS)
    elseif w == "edge" then Main.mouse = true; Main.look = false; Main.edge = true; if G then mouselook(false) end
    elseif w == "free" then Main.mouse = true; Main.look = false; Main.edge = false; if G then mouselook(false) end
    elseif w == "look" then Main.mouse = true; Main.look = true; Main.edge = false
    elseif w == "debug" then Main.debug = not Main.debug; if R and R.dbg and not Main.debug then R.dbg:SetText("") end; say("mouse readings line: " .. (Main.debug and "on" or "off")) end
    if ns.Gauntlet then ns.Gauntlet.mouse = Main.mouse end
    say("mouse turning: " .. (Main.mouse and "on" or "off"))
  else say("/gaunt (play) | /gaunt new | /gaunt report | /gaunt cols 240 | /gaunt mousetest (finds the mouse mode that works) | /gaunt scale 1.5 | /gaunt shots on|off | /gaunt mouse look|free|edge|off|sens 0.0035 | /gaunt test (speed and asset tests) | /gaunt stop") end
end

return Main
