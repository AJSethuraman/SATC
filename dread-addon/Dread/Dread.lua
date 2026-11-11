-- /dread        Test 1: 100 moving squares, FPS and memory for 5 minutes
-- /dread assets Test 2: icons, sounds, one music track
-- /dread stop   stop whatever is running
-- Results are printed and also saved to DreadDB.results (SavedVariables).
local ADDON, ns = ...
local Sim, Skills, Tree = ns.Sim, ns.Skills, ns.Tree

DreadDB = DreadDB or {}
DreadDB.results = DreadDB.results or {}

local function say(msg) print("|cffff5555Dread|r " .. msg) end
local function record(key, value) DreadDB.results[key] = value; say(key .. ": " .. value) end

local function mem() return collectgarbage("count") end

---------------------------------------------------------------- Test 1
local W, H, N, DURATION = 600, 400, 100, 300
local frame, squares, world, running

local function buildFrame()
  if frame then return end
  frame = CreateFrame("Frame", "DreadFrame", UIParent, "BackdropTemplate")
  frame:SetSize(W + 20, H + 50)
  frame:SetPoint("CENTER")
  frame:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
  frame:SetBackdropColor(0, 0, 0, 0.85)
  frame:SetBackdropBorderColor(0.6, 0.1, 0.1, 1)
  frame:SetMovable(true); frame:EnableMouse(true)
  frame:RegisterForDrag("LeftButton")
  frame:SetScript("OnDragStart", frame.StartMoving)
  frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
  frame.text = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  frame.text:SetPoint("TOPLEFT", 10, -8)
  frame.arena = CreateFrame("Frame", nil, frame)
  frame.arena:SetSize(W, H)
  frame.arena:SetPoint("BOTTOMLEFT", 10, 10)
  squares = {}
  for i = 1, N do
    local t = frame.arena:CreateTexture(nil, "ARTWORK")
    t:SetSize(8, 8)
    t:SetColorTexture((i * 37 % 100) / 100, (i * 61 % 100) / 100, (i * 17 % 100) / 100, 1)
    squares[i] = t
  end
end

local function stopTest1(reason)
  if not running then return end
  running = nil
  frame:SetScript("OnUpdate", nil)
  frame:Hide()
  say("test 1 stopped: " .. reason)
end

local function startTest1()
  buildFrame()
  world = Sim.new(N, W, H, 42)
  -- Test 2 hides the squares and shows icons; put things back so Test 1 always draws all N squares.
  for _, t in ipairs(squares) do t:Show() end
  for _, t in ipairs(frame.icons or {}) do t:Hide() end
  frame:Show()
  local elapsed, tick, fps, memEarly = 0, 0, {}, nil
  running = true
  collectgarbage("collect")
  local memStart = mem()
  frame:SetScript("OnUpdate", function(_, dt)
    Sim.step(world, dt)
    for i, o in ipairs(world.objs) do
      squares[i]:ClearAllPoints()
      squares[i]:SetPoint("BOTTOMLEFT", frame.arena, "BOTTOMLEFT", o.x, o.y)
    end
    elapsed, tick = elapsed + dt, tick + dt
    if tick >= 1 then
      tick = 0
      fps[#fps + 1] = GetFramerate()
      frame.text:SetText(string.format("Dread test 1   %d s / %d   FPS %.0f   Lua %.0f KB",
        elapsed, DURATION, fps[#fps], mem()))
    end
    if not memEarly and elapsed >= 60 then collectgarbage("collect"); memEarly = mem() end
    if elapsed >= DURATION then
      collectgarbage("collect")
      local verdict, detail = Sim.verdict(fps, memEarly or memStart, mem())
      stopTest1("finished")
      record("test1", verdict .. " | " .. detail .. string.format(" | caps: foreground %s, background %s (keep WoW in front)",
        tostring(GetCVar("maxFPS")), tostring(GetCVar("maxFPSBk"))))
    end
  end)
  say("test 1 running for " .. DURATION .. " s. Leave the window open. /dread stop to cancel.")
end

---------------------------------------------------------------- Test 2
-- Candidates are guesses to be tested, not known-good paths. The result is the finding.
local ICONS = {
  "INV_Sword_04", "INV_Shield_05", "INV_Helmet_08", "INV_Chest_Plate01", "INV_Boots_05",
  "INV_Misc_Bag_08", "INV_Potion_54", "INV_Potion_51", "INV_Misc_Gem_Ruby_02", "INV_Misc_Coin_01",
  "Spell_Fire_FlameBolt", "Spell_Frost_FrostBolt02", "Spell_Nature_Lightning", "Spell_Shadow_ShadowBolt",
  "Spell_Holy_HolyBolt", "Ability_Warrior_Charge", "Ability_Rogue_Sprint", "Ability_Hunter_SniperShot",
  "Spell_Nature_Regeneration", "INV_Misc_QuestionMark",
}
local SOUNDS = {
  { "kit: backpack open", function() return PlaySound(SOUNDKIT and SOUNDKIT.IG_BACKPACK_OPEN or 862) end },
  { "kit: coin",          function() return PlaySound(SOUNDKIT and SOUNDKIT.LOOT_WINDOW_COIN_SOUND or 120) end },
  { "kit: level up",      function() return PlaySound(SOUNDKIT and SOUNDKIT.UI_LEGENDARY_LOOT_TOAST or 63971) end },
  { "path: button",       function() return PlaySoundFile("Sound\\Interface\\iUiInterfaceButtonA.ogg", "SFX") end },
  { "path: quest done",   function() return PlaySoundFile("Sound\\Interface\\iQuestComplete.ogg", "SFX") end },
}
local MUSIC = "Sound\\Music\\ZoneMusic\\Undercity\\UC_Undercity.mp3"

local function runTest2()
  buildFrame()
  frame:Show()
  for _, t in ipairs(squares) do t:Hide() end
  if not frame.icons then
    frame.icons = {}
    for i, name in ipairs(ICONS) do
      local t = frame.arena:CreateTexture(nil, "ARTWORK")
      t:SetSize(40, 40)
      t:SetPoint("TOPLEFT", frame.arena, "TOPLEFT", ((i - 1) % 10) * 48 + 4, -math.floor((i - 1) / 10) * 48 - 4)
      frame.icons[i] = t
    end
  end
  local bad = {}
  for i, name in ipairs(ICONS) do
    local t = frame.icons[i]
    t:SetTexture("Interface\\Icons\\" .. name)
    t:Show()
    -- A missing file leaves the green "missing texture" or an empty path. Report what the client says.
    local got = t:GetTexture()
    if not got then bad[#bad + 1] = name end
  end
  frame.text:SetText("Dread test 2   icons below; sounds play one a second. Look and listen.")
  local iconNote = (#ICONS - #bad) .. "/" .. #ICONS .. " icons returned a texture"
  if #bad > 0 then iconNote = iconNote .. " (none: " .. table.concat(bad, ", ") .. ")" end
  record("test2_icons", iconNote .. ". GetTexture does not catch a bad path: confirm by eye, note any green squares.")

  local report = {}
  for i, s in ipairs(SOUNDS) do
    C_Timer.After(i, function()
      local ok, willPlay = pcall(s[2])
      report[#report + 1] = s[1] .. "=" .. (ok and tostring(willPlay) or "ERROR")
      if i == #SOUNDS then
        record("test2_sounds", table.concat(report, "; ") .. ". willPlay is not proof of audio: note which you actually heard.")
      end
    end)
  end
  C_Timer.After(#SOUNDS + 1, function()
    local ok, willPlay = pcall(PlayMusic, MUSIC)
    record("test2_music", MUSIC .. " -> " .. (ok and tostring(willPlay) or "ERROR") .. ". Listen, then /dread stopmusic.")
  end)
end


-- /dread sound: one at a time, each announced in chat just before it plays.
local function runSounds()
  local function cv(n) return n .. "=" .. tostring(GetCVar(n)) end
  say("sound settings: " .. table.concat({ cv("Sound_EnableAllSound"), cv("Sound_EnableSFX"), cv("Sound_EnableMusic"),
    cv("Sound_MasterVolume"), cv("Sound_SFXVolume"), cv("Sound_MusicVolume") }, ", "))
  local steps = {}
  for _, snd in ipairs(SOUNDS) do steps[#steps + 1] = snd end
  steps[#steps + 1] = { "music: " .. MUSIC, function() return PlayMusic(MUSIC) end }
  for i, st in ipairs(steps) do
    C_Timer.After((i - 1) * 3, function()
      say(string.format("[%d/%d] NOW: %s", i, #steps, st[1]))
      local ok, r = pcall(st[2])
      say("   returned " .. (ok and tostring(r) or "ERROR"))
    end)
  end
  C_Timer.After(#steps * 3, function() say("done. Tell me which numbers you heard. /dread stopmusic to stop music.") end)
end

-- /dread skills: check the skill table loaded and is well formed, then list it.
local function showSkills()
  local problems = Tree.validate()
  say(#Skills .. " skills loaded, " .. (#problems == 0 and "table is well formed" or (#problems .. " PROBLEMS")))
  for _, p in ipairs(problems) do say("   " .. p) end
  for _, tree in ipairs(Skills.trees) do
    say("|cffffd100" .. tree .. "|r")
    for _, sk in ipairs(Skills) do
      if sk.tree == tree then
        local pre = {}
        for _, id in ipairs(sk.prereqs) do pre[#pre + 1] = Skills.byId[id].name end
        say(string.format("  L%-2d %s%s", sk.req, sk.name, #pre > 0 and ("  <- " .. table.concat(pre, ", ")) or ""))
      end
    end
  end
end

---------------------------------------------------------------- slash command
SLASH_DREAD1 = "/dread"
SlashCmdList.DREAD = function(arg)
  arg = (arg or ""):lower():match("^%s*(.-)%s*$")
  if arg == "" then startTest1()
  elseif arg == "assets" then runTest2()
  elseif arg == "stop" then if running then stopTest1("cancelled") elseif frame then frame:Hide() end
  elseif arg == "sound" then runSounds()
  elseif arg == "skills" then showSkills()
  elseif arg == "stopmusic" then StopMusic()
  elseif arg == "results" then
    for k, v in pairs(DreadDB.results) do say(k .. ": " .. v) end
  else say("/dread | /dread assets | /dread sound | /dread skills | /dread stop | /dread stopmusic | /dread results") end
end
