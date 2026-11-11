-- Network probe: can two players running Dread exchange messages on Forever, how fast, and how much before it is throttled?
-- /dread net, in a party or raid. A friend who also has Dread answers by itself (they type nothing).
-- Alone, it still measures what this client will let you send: the throttle shows in the send result.
-- This decides whether multiplayer is realistic. It is a measurement, not a feature.
--
-- Every message is  KIND|sid|a|b  where sid is random per session. The game echoes your own messages back to you,
-- and a character's name is not a reliable way to tell the echo from a friend (names here carry a surname), so the
-- sid is how a message from yourself is recognised.
local ADDON, ns = ...
local Net = {}
ns.Net = Net

local PREFIX = "DREADNET"
Net.PING_COUNT, Net.BURST_COUNT, Net.BURST_BYTES = 10, 40, 200
Net.PACED_RATES, Net.PACED_SECONDS, Net.PACED_GAP = { 10, 5, 2, 1 }, 3, 6

-- What the client's send call returns (Enum.SendAddonMessageResult), so a number is readable.
Net.RESULT = { [0] = "Success", [1] = "InvalidPrefix", [2] = "InvalidMessage", [3] = "AddonMessageThrottle",
               [4] = "InvalidChatType", [5] = "NotInGroup", [6] = "TargetRequiresLogin", [7] = "AddOnMessageLockdown" }

local function say(msg)
  msg = "|cffff5555Dread|r " .. msg
  if ns.log then ns.log(msg) else print(msg) end
end

math.randomseed((time and time() or 1) + math.floor((GetTime and GetTime() or 0) * 1000))
Net.SID = tostring(math.random(10000000, 99999999))

local run, counts = nil, {}

-- min / average / max in milliseconds, or nil with no samples.
function Net.summarize(rtts)
  if #rtts == 0 then return nil end
  local sum, lo, hi = 0, math.huge, 0
  for _, v in ipairs(rtts) do sum = sum + v; if v < lo then lo = v end; if v > hi then hi = v end end
  return { n = #rtts, min = lo, avg = sum / #rtts, max = hi }
end

-- The fastest tested rate at which the client took every message, or nil if even the slowest was refused some.
function Net.sustained(paced)
  local best
  for _, r in ipairs(Net.PACED_RATES) do
    local p = paced[r]
    if p and p.sent > 0 and p.ok == p.sent and (not best or r > best) then best = r end
  end
  return best
end

function Net.channel()
  if IsInGroup and IsInGroup() then
    return (IsInRaid and IsInRaid()) and "RAID" or "PARTY"
  end
  return nil
end

local function ok_result(detail)
  return detail == nil or detail == 0 or detail == true or detail == "Success"
end

-- Returns ok, detail. The detail is whatever the client said, unedited, because the client's refusals are the finding.
local function send(text, channel)
  local f = (C_ChatInfo and C_ChatInfo.SendAddonMessage) or SendAddonMessage
  if not f then return false, "no addon-message call exists" end
  local ok, res = pcall(f, PREFIX, text, channel)
  return ok, res
end

local function msg(kind, a, b) return kind .. "|" .. Net.SID .. "|" .. tostring(a) .. "|" .. tostring(b or "") end

function Net.receive(prefix, text, channel, sender)
  if prefix ~= PREFIX or type(text) ~= "string" then return end
  local kind, sid, a, b = text:match("^(%u+)|([^|]*)|([^|]*)|?(.*)$")
  if not kind or sid == Net.SID then return end                  -- not ours to read, or our own message coming back
  if kind == "PING" then
    send(msg("PONG", a, b), channel)
  elseif kind == "PONG" then
    if run and run.sent_at[tonumber(a)] then
      run.peer = run.peer or sender                              -- the first to answer is the one measured; everyone else is ignored
      if sender == run.peer then
        run.rtts[#run.rtts + 1] = (GetTime() - run.sent_at[tonumber(a)]) * 1000
      end
    end
  elseif kind == "BURST" then
    counts[sender] = (counts[sender] or 0) + 1
  elseif kind == "END" then
    send(msg("STAT", counts[sender] or 0, a), channel)
    counts[sender] = 0
  elseif kind == "STAT" then
    if run then
      run.peer = run.peer or sender
      if sender == run.peer then run.peer_got, run.peer_of = tonumber(a), tonumber(b) end
    end
  end
end

local function describe(code)
  return Net.RESULT[code] and (tostring(code) .. " = " .. Net.RESULT[code]) or tostring(code)
end

local function report()
  local r, parts = run, {}
  local s = Net.summarize(r.rtts)
  parts[#parts + 1] = s and string.format("pings: %d of %d answered, round trip %.0f / %.0f / %.0f ms (min / avg / max)", s.n, Net.PING_COUNT, s.min, s.avg, s.max)
                         or string.format("pings: 0 of %d answered by anyone else", Net.PING_COUNT)
  parts[#parts + 1] = string.format("burst: sent %d messages of %d bytes, %d accepted by the client, the friend received %s",
    Net.BURST_COUNT, Net.BURST_BYTES, r.accepted, r.peer_got and (r.peer_got .. " of " .. tostring(r.peer_of)) or "no report back")
  local rates = {}
  for _, rate in ipairs(Net.PACED_RATES) do
    local p = r.paced[rate]
    rates[#rates + 1] = string.format("%d/s %d of %d", rate, p.ok, p.sent)
  end
  local sus = Net.sustained(r.paced)
  parts[#parts + 1] = "paced sends, accepted of sent: " .. table.concat(rates, ", ")
                      .. (sus and (". The client took every message at " .. sus .. " a second") or ". The client refused some even at the slowest rate")
  if r.peer then parts[#parts + 1] = "measured against " .. tostring(r.peer) .. " (the first to answer; any others are ignored)" end
  if r.first_error ~= nil then parts[#parts + 1] = "the client said: " .. describe(r.first_error) end
  DreadDB = DreadDB or {}
  DreadDB.results = DreadDB.results or {}
  DreadDB.results.net = table.concat(parts, " | ")
  for _, l in ipairs(parts) do say(l) end
  run = nil
end

function Net.start()
  if run then say("a network test is already running"); return false end
  local channel = Net.channel()
  if not channel then say("join a party or raid, then /dread net (a friend who also has Dread makes it a full test)"); return false end
  run = { sent_at = {}, rtts = {}, accepted = 0, paced = {} }
  local t_burst = Net.PING_COUNT * 0.5 + 1.5
  local t_paced = t_burst + Net.PACED_GAP
  local t_end = t_paced + #Net.PACED_RATES * (Net.PACED_SECONDS + Net.PACED_GAP)
  say(string.format("testing over %s. About %d seconds; keep playing normally.", channel, math.ceil(t_end)))
  local function note(okcall, detail)
    if (not okcall or not ok_result(detail)) and run and run.first_error == nil then run.first_error = detail end
  end
  for i = 1, Net.PING_COUNT do
    C_Timer.After(i * 0.5, function()
      run.sent_at[i] = GetTime()
      note(send(msg("PING", i, GetTime()), channel))
    end)
  end
  C_Timer.After(t_burst, function()
    for i = 1, Net.BURST_COUNT do
      local head = "BURST|" .. Net.SID .. "|" .. i .. "|"
      local okcall, detail = send(head .. string.rep("x", Net.BURST_BYTES - #head), channel)      -- exactly BURST_BYTES long
      if okcall and ok_result(detail) then run.accepted = run.accepted + 1 else note(okcall, detail) end
    end
    send(msg("END", Net.BURST_COUNT), channel)
  end)
  -- steady rates, each after a pause so the budget has refilled: this finds what the client will let you keep doing
  for k, rate in ipairs(Net.PACED_RATES) do
    local t0 = t_paced + (k - 1) * (Net.PACED_SECONDS + Net.PACED_GAP)
    run.paced[rate] = { sent = 0, ok = 0 }
    for j = 0, rate * Net.PACED_SECONDS - 1 do
      C_Timer.After(t0 + j / rate, function()
        local p = run.paced[rate]
        p.sent = p.sent + 1
        local okcall, detail = send(msg("PACE", rate, j), channel)
        if okcall and ok_result(detail) then p.ok = p.ok + 1 else note(okcall, detail) end
      end)
    end
  end
  C_Timer.After(t_end + 1, report)
  return true
end

-- Answer the friend even when nobody has typed anything.
local frame = CreateFrame("Frame")
pcall(function() if C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix then C_ChatInfo.RegisterAddonMessagePrefix(PREFIX) end end)
pcall(function() frame:RegisterEvent("CHAT_MSG_ADDON") end)
frame:SetScript("OnEvent", function(_, _, prefix, text, channel, sender) Net.receive(prefix, text, channel, sender) end)
Net.frame = frame

return Net
