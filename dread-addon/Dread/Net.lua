-- Network probe: can two players running Dread exchange messages on Forever, how fast, and how much before it is throttled?
-- /dread net, in a party with a friend who also has Dread installed (the friend does nothing; the addon answers by itself).
-- This decides whether multiplayer is realistic. It is a measurement, not a feature.
local ADDON, ns = ...
local Net = {}
ns.Net = Net

local PREFIX = "DREADNET"
Net.PING_COUNT, Net.BURST_COUNT, Net.BURST_BYTES = 10, 40, 200

local function say(msg) print("|cffff5555Dread|r " .. msg) end

local run, counts = nil, {}

-- min / average / max in milliseconds, or nil with no samples.
function Net.summarize(rtts)
  if #rtts == 0 then return nil end
  local sum, lo, hi = 0, math.huge, 0
  for _, v in ipairs(rtts) do sum = sum + v; if v < lo then lo = v end; if v > hi then hi = v end end
  return { n = #rtts, min = lo, avg = sum / #rtts, max = hi }
end

function Net.channel()
  if IsInGroup and IsInGroup() then
    return (IsInRaid and IsInRaid()) and "RAID" or "PARTY"
  end
  return nil
end

local function me()
  return (UnitName and UnitName("player")) or "?"
end

-- Returns ok, detail. The detail is whatever the client said, unedited, because the client's refusals are the finding.
local function send(text, channel)
  local f = (C_ChatInfo and C_ChatInfo.SendAddonMessage) or SendAddonMessage
  if not f then return false, "no addon-message call exists" end
  local ok, res = pcall(f, PREFIX, text, channel)
  return ok, res
end

function Net.receive(prefix, text, channel, sender)
  if prefix ~= PREFIX or type(text) ~= "string" then return end
  if sender and sender:match("^[^-]+") == me() then return end          -- our own message coming back
  local kind, a, b = text:match("^(%u+)|([^|]*)|?(.*)$")
  if kind == "PING" then
    send("PONG|" .. a .. "|" .. b, channel)
  elseif kind == "PONG" then
    if run and run.sent_at[tonumber(a)] then
      run.peer = run.peer or sender                         -- the first to answer is the one measured; everyone else is ignored
      if sender == run.peer then
        run.rtts[#run.rtts + 1] = (GetTime() - run.sent_at[tonumber(a)]) * 1000
      end
    end
  elseif kind == "BURST" then
    counts[sender] = (counts[sender] or 0) + 1
  elseif kind == "END" then
    send("STAT|" .. (counts[sender] or 0) .. "|" .. a, channel)
    counts[sender] = 0
  elseif kind == "STAT" then
    if run then
      run.peer = run.peer or sender
      if sender == run.peer then run.peer_got, run.peer_of = tonumber(a), tonumber(b) end
    end
  end
end

local function report()
  local r = run
  local parts = {}
  local s = Net.summarize(r.rtts)
  parts[#parts + 1] = s and string.format("pings: %d of %d answered, round trip %.0f / %.0f / %.0f ms (min / avg / max)", s.n, Net.PING_COUNT, s.min, s.avg, s.max)
                         or string.format("pings: 0 of %d answered", Net.PING_COUNT)
  parts[#parts + 1] = string.format("burst: sent %d messages of %d bytes, %d accepted by the client, the friend received %s",
    Net.BURST_COUNT, Net.BURST_BYTES, r.accepted, r.peer_got and (r.peer_got .. " of " .. tostring(r.peer_of)) or "no report back")
  if r.peer then parts[#parts + 1] = "measured against " .. tostring(r.peer) .. " (the first to answer; any others are ignored)" end
  if r.first_error then parts[#parts + 1] = "the client said: " .. tostring(r.first_error) end
  DreadDB = DreadDB or {}
  DreadDB.results = DreadDB.results or {}
  DreadDB.results.net = table.concat(parts, " | ")
  for _, l in ipairs(parts) do say(l) end
  run = nil
end

function Net.start()
  if run then say("a network test is already running"); return false end
  local channel = Net.channel()
  if not channel then say("join a party with a friend who has Dread installed, then /dread net"); return false end
  run = { sent_at = {}, rtts = {}, accepted = 0 }
  say("testing over " .. channel .. ": 10 pings, then a burst of 40 messages. About 10 seconds.")
  for i = 1, Net.PING_COUNT do
    C_Timer.After(i * 0.5, function()
      run.sent_at[i] = GetTime()
      local ok, detail = send("PING|" .. i .. "|" .. tostring(GetTime()), channel)
      if (not ok or detail == false) and not run.first_error then run.first_error = detail end
    end)
  end
  C_Timer.After(Net.PING_COUNT * 0.5 + 1.5, function()
    for i = 1, Net.BURST_COUNT do
      local head = "BURST|" .. i .. "|"
      local ok, detail = send(head .. string.rep("x", Net.BURST_BYTES - #head), channel)       -- exactly BURST_BYTES long
      -- a 0 / true / Enum "Success" result means the client took it; anything else is a refusal or a throttle
      if ok and (detail == nil or detail == 0 or detail == true or detail == "Success") then run.accepted = run.accepted + 1
      elseif not run.first_error then run.first_error = detail end
    end
    send("END|" .. Net.BURST_COUNT, channel)
  end)
  C_Timer.After(Net.PING_COUNT * 0.5 + 6, report)
  return true
end

-- Answer the friend even when nobody has typed anything.
local frame = CreateFrame("Frame")
pcall(function() if C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix then C_ChatInfo.RegisterAddonMessagePrefix(PREFIX) end end)
pcall(function() frame:RegisterEvent("CHAT_MSG_ADDON") end)
frame:SetScript("OnEvent", function(_, _, prefix, text, channel, sender) Net.receive(prefix, text, channel, sender) end)
Net.frame = frame

return Net
