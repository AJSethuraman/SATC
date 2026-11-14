-- Service Inviter v3.5.2
-- Watches chat for people asking to BUY what your group sells right now (summons to
-- where the warlock is, the mage's portals, lockpicking, water, stones, buffs) and sends
-- them a group invite. The rules live in Services.lua; docs/DESIGN.md says why. It also talks in your group and may
-- whisper (welcome, summon alert, extras on offer, the ritual whisper): turn
-- each off in /si setup if you are silenced.
--
-- Open the settings window with /si. /si jobs opens the customer list.
-- /si selftest runs a built-in check. /si dryrun shows who it WOULD invite.
--
-- Matching is order-independent ("WTB TB summon" == "summon to TB wtb"), strips
-- links/markers/punctuation, accepts abbreviations, joins a sender's last few
-- lines (fragments), and ALWAYS rejects anything that looks like a seller or ad.

ServiceInviterDB = ServiceInviterDB or {}
local ADDON_NAME = "ServiceInviter"
local blockedCalls = {}   -- calls the game refused this session (ADDON_ACTION_FORBIDDEN): never retried

-- One-time copy of settings from the old Trade Inviter addon.
local function MigrateLegacy()
    local old = _G["Trade" .. "InviterDB"]
    if type(old) ~= "table" or ServiceInviterDB.migrated then return end
    ServiceInviterDB.migrated = true
    if ServiceInviterDB.opts == nil and old.opts then ServiceInviterDB.opts = old.opts end
    for _, k in ipairs({ "welcomemsg", "blocked", "cooldown", "outframe", "near" }) do
        if ServiceInviterDB[k] == nil and old[k] ~= nil then ServiceInviterDB[k] = old[k] end
    end
end

-- One-time carry-over from 1.x: the old "extras offered on arrival" become those services,
-- offered but not invited for (they were never invite triggers), and the old price becomes the
-- summons price.
local function MigrateServices()
    local db = ServiceInviterDB
    if db.servicesMigrated then return end
    db.servicesMigrated = true
    db.services = db.services or {}
    local map = { paladin = "blessing" }   -- the only 1.x extra still sold (summons and blessings only, 14 Nov 2026)
    if type(db.offers) == "table" then
        for old, new in pairs(map) do
            if db.offers[old] then
                db.services[new] = db.services[new] or {}
                if db.services[new].on == nil then db.services[new].on = true end
                if db.services[new].invite == nil then db.services[new].invite = false end
            end
        end
    end
    if type(db.price) == "number" then
        db.services.summons = db.services.summons or {}
        if db.services.summons.price == nil then db.services.summons.price = db.price end
    end
end

-- Declared here, defined further down: the event handler and the buff queue use them
-- before the file reaches their definitions.
local IsSecret, SpellNameOf, jobsWin
local Jobs = {}   -- the customers (filled in further down; the group reading needs it)
local BuffAsk, BuffCastDone, BuffTooLow, RefreshBuff, QueueAllMyBuffs, buffDirty

local LIMIT = { FRAGMENT_WINDOW = 25, MAX_FRAGMENTS = 3, MAX_PER_MINUTE = 6, MAX_PARTY = 5 }

-- Destinations shown as checkboxes: key, label, keywords.
local DESTS = {
    { key = "tb",  label = "Thunder Bluff", words = { "tb", "thunder", "thunder bluff", "thunderbluff", "tbluff" } },
    { key = "org", label = "Orgrimmar",     words = { "org", "orgrimmar", "og" } },
    { key = "uc",  label = "Undercity",     words = { "uc", "undercity" } },
    { key = "bb",  label = "Booty Bay",     words = { "bb", "booty", "bootybay", "booty bay" } },
    { key = "gadget", label = "Gadgetzan",  words = { "gadgetzan", "gadget", "gadgetz" } },
    { key = "everlook", label = "Everlook", words = { "everlook" } },
    { key = "ratchet", label = "Ratchet",   words = { "ratchet" } },
    { key = "xroads", label = "Crossroads", words = { "crossroads", "xroads", "cross roads" } },
    { key = "sw", label = "Stormwind City", words = { "sw", "stormwind", "stormwind city" } },
    { key = "ironforge", label = "Ironforge", words = { "ironforge" } },
    { key = "darn", label = "Darnassus", words = { "darnassus", "darn" } },
}

local DEFAULTS = {
    enabled   = true,
    trade     = true,
    general   = true,
    say       = false,
    yell      = false,
    kwon = false,        -- keyword auto-invite ("inv", "invite") on/off
    strictbuy = false,   -- only WTB/buying count (ignore LF / need / looking)
    fragments = true,
    announce  = true,    -- print a line in your chat window when it invites
    skipafk   = true,
    autoshow  = true,    -- open the customer list when someone is invited
    loyalty   = true,    -- (until 2.3.2 the on/off for the loyalty line; now an empty line is off)
    marks     = true,    -- a raid icon on whoever does a service, in party/raid chat (text only: the game no longer lets addons put icons over heads)
    welcome   = true,    -- send a message to the group when an invited player joins
    buffarrivals = true, -- queue your buffs on a customer who lands where you are, unasked
    buffpop   = true,    -- the buff button pops up at your mouse when someone is waiting
    countshards = false, -- count soul shards and stop inviting summon buyers when they'd run out
    guildteam = true,    -- everyone in your guild running Service Inviter is on the team
    payremind = true,    -- on landing, tell them who to pay and how much
    -- Destination grid: do you SUMMON to it, and/or PORT to it?
    sum_tb  = true,  port_tb  = false,
    sum_org = false, port_org = false,
    sum_uc  = false, port_uc  = false,
    sum_bb = false, port_bb = false, sum_gadget = false, port_gadget = false,
    sum_everlook = false, port_everlook = false, sum_ratchet = false, port_ratchet = false,
    sum_xroads = false, port_xroads = false,
    sum_any = false, port_any = false,   -- "any other destination"
}

local BUY       = { "wtb", "wtbuy", "buying", "buy", "lf", "lfp", "lfs", "looking", "need", "needs", "wanted", "want" }
local STRICTBUY = { "wtb", "wtbuy", "buying", "buy" }
local SUMMON_WORDS = { "summon", "summons", "summoning", "summoned", "summ", "summs", "sumn", "sumns", "sum", "sums", "summin" }
local PORT_WORDS   = { "port", "ports", "portal", "portals", "tp", "teleport" }
-- ANY of these rejects the message outright. Safer to skip a real buyer than to invite a seller.
local SELLER = {
    "wts", "selling", "sell", "sale", "offering", "wtt", "lfm", "recruiting",
    "service", "services", "porting",
    -- another seller's ad (the owner's screenshot, 14 Nov 2026: "dont buy cheap TB summons PST we
    -- have them for 40s+tip" was taken for a buyer)
    "dont buy", "don t buy", "do not buy", "we have", "have them", "we got", "we sell", "we summon",
}
-- Ad words that buyers use too ("wtb summ tb, will tip", "for guild group"):
-- they only reject the message when there is no clear WTB/buying word.
local SOFTSELLER = { "tip", "tips", "guild" }
-- "Contact" words: sellers use them, but so do buyers ("wtb summ tb pst").
-- They only reject the message when there is no clear WTB/buying word.
local CONTACT = { "pst", "inv", "invite", "whisper", "pm", "msg" }

local debugOn = false  -- loaded from ServiceInviterDB.debug at login
local lastInvite = {}
local diag = { casts = {} }   -- what we last heard / saw, for /si status
local paused = false   -- true while the old Trade Inviter is also loaded (avoids double invites)
local pending = {}   -- invited players we are waiting to see join
local MSG = {}
MSG.SCAM = "Heads up: {name} didn't pay last time."   -- the default text of every message you can change
MSG.WELCOME = "WELCOME {name}! THE COST IS {price}. SUMMONING YOU SOON, I WILL TRADE YOU ON ARRIVAL!"
local fragments = {}
local inviteTimes = {}

-- Output goes to: the chat window you chose with /si out <number>, else a chat
-- window whose tab is named TI (or TradeInviter), else the main window.
local function OutFrame()
    local n = ServiceInviterDB and ServiceInviterDB.outframe
    if n and _G["ChatFrame" .. n] then return _G["ChatFrame" .. n] end
    if GetChatWindowInfo then
        for i = 1, (NUM_CHAT_WINDOWS or 10) do
            local name = GetChatWindowInfo(i)
            if name then
                local lname = name:lower()
                if (lname == "si" or lname == "ti" or lname == "serviceinviter" or lname == "service inviter") and _G["ChatFrame" .. i] then
                    return _G["ChatFrame" .. i]
                end
            end
        end
    end
    return DEFAULT_CHAT_FRAME
end
local function P(msg)
    if Jobs.capture then Jobs.capture[#Jobs.capture + 1] = msg return end   -- going to the copy window
    local f = OutFrame()
    local line = "|cff80ff80Service Inviter|r: " .. msg
    if f and f.AddMessage then f:AddMessage(line) else print(line) end
end
-- Every message to a customer, the group or a whisper goes through here: in test mode it goes
-- to you instead (your chat, or a whisper to /si test NAME), never to them.
-- {rt1}..{rt8} drawn as the icon, for test lines printed in your own chat (sent chat converts them itself)
function Jobs.Icons(text)
    local names = { star = 1, circle = 2, diamond = 3, triangle = 4, moon = 5, square = 6, cross = 7, x = 7, skull = 8 }
    text = tostring(text):gsub("{(%a+)}", function(w) local n = names[w:lower()] return n and ("{rt" .. n .. "}") or nil end)
    return (text:gsub("{rt(%d)}", "|TInterface\\TargetingFrame\\UI-RaidTargetingIcon_%1:0|t"))
end
-- Where each message goes: whisper the customer, the group (party/raid), or nowhere (the owner,
-- 14 Nov 2026: "i'd want to be able to adjust whether a chat goes to whisper or to raid/party like
-- it does now"). With a team, customer messages default to whispers and only the regulars line and
-- the didn't-pay call-out are public; solo keeps today's choices.
Jobs.ROUTE_KINDS = { "welcome", "alert", "arrival", "thanks", "loyal", "scam" }
Jobs.ROUTE_LABEL = { welcome = "Welcome + price", alert = "Summon starting", arrival = "When they land",
    thanks = "Thanks", loyal = "Regulars line", scam = "Didn't-pay call-out" }
function Jobs.RouteOf(kind)
    local r = type(ServiceInviterDB.route) == "table" and ServiceInviterDB.route[kind]
    if r then return r end
    if kind == "thanks" then return "whisper" end
    if kind == "loyal" or kind == "scam" then return "group" end
    return (Jobs.TeamOn and Jobs.TeamOn()) and "whisper" or "group"
end
-- groupCh: the party/raid (or raid warning) channel to use when it goes to the group
function Jobs.Route(kind, text, name, groupCh)
    if not text or text == "" then return end
    local r = Jobs.RouteOf(kind)
    if r == "off" then return end
    if r == "whisper" and name then Jobs.Send(text, "WHISPER", name)
    else
        local ch = groupCh or ((IsInRaid and IsInRaid()) and "RAID" or ((IsInGroup and IsInGroup()) and "PARTY" or nil))
        if ch then Jobs.Send(text, ch) end
    end
end
function Jobs.Send(text, ch, to)
    -- on a team, only the point of contact talks to customers and the group (the owner, 14 Nov 2026:
    -- "i want there to be a point of contact")
    if ch ~= "CHANNEL" and Jobs.POC then
        local poc = Jobs.POC()
        if poc and Jobs.Me and poc ~= Jobs.Me() then return end
    end
    if ServiceInviterDB and ServiceInviterDB.dryrun then
        local tt = ServiceInviterDB.testto
        local where = (ch == "WHISPER" and ("whisper to " .. tostring(to))) or (ch == "RAID_WARNING" and "raid warning") or (tostring(ch):lower() .. " chat")
        -- the target gets the message exactly as it would go out; your chat says what it was
        if tt and tt ~= "" then
            SendChatMessage(text, "WHISPER", nil, tt)
            P("|cffffd100TEST|r |cff999999(" .. where .. ") whispered to " .. tt .. " instead|r")
        else P("|cffffd100TEST|r |cff999999(" .. where .. "):|r " .. Jobs.Icons(text)) end
        return
    end
    SendChatMessage(text, ch, nil, to)
end
local function D(msg)
    if Jobs.whyNow then Jobs.whyNow.why = msg end   -- for /si why NAME
    if debugOn then P("|cff999999" .. msg .. "|r") end
end
-- An error in a background update, said once in your chat. The game hides Lua errors unless
-- told to show them, so without this a failing update just looks like a frozen window (the
-- owner, 13 Nov 2026: "it just kinda froze").
local Report
do
  local reported = {}
  Report = function(where, ok, err)
    if ok or reported[where] then return end
    reported[where] = true
    P("|cffff4040error in " .. where .. ": " .. tostring(err) .. "|r  Please screenshot this line and send it.")
  end
end

local function Opt(key)
    local o = ServiceInviterDB.opts
    if o and o[key] ~= nil then return o[key] end
    return DEFAULTS[key]
end

local function SetOpt(key, value)
    ServiceInviterDB.opts = ServiceInviterDB.opts or {}
    ServiceInviterDB.opts[key] = value
end

local function Norm(s)
    s = s or ""
    s = s:gsub("|c%x%x%x%x%x%x%x%x", "")
    s = s:gsub("|r", "")
    s = s:gsub("|H.-|h", "")   -- link payload ("|Hspell:698|h"); the [text] stays
    s = s:gsub("|h", "")
    s = s:lower()
    s = s:gsub("{.-}", " ")
    s = s:gsub("[^%w]+", " ")
    s = s:gsub("^%s+", ""):gsub("%s+$", "")
    return " " .. s .. " "
end

local function Has(norm, word)
    return norm:find(" " .. word .. " ", 1, true) ~= nil
end

local function HasAny(norm, list)
    for _, w in ipairs(list) do
        if Has(norm, w) then return w end
    end
    return nil
end

-- Your own channels from Setup ("+ other channels"): usually dedicated summon channels.
MSG.CHANNELS = "summons"
local function InExtraChannel(ch)
    ch = (ch or ""):lower()
    local list = ServiceInviterDB.chanextra
    if type(list) ~= "string" then list = MSG.CHANNELS end
    for name in list:lower():gmatch("[^,]+") do
        name = name:gsub("^%s+", ""):gsub("%s+$", "")
        if name ~= "" and ch:find(name, 1, true) then return true end
    end
    return false
end

-- Returns true, reason or false, reason.
-- dedicated = the message came from one of your own channels, where everybody is asking for
-- summons/ports anyway: "wtb uc" is enough, no summon/port word needed.
-- What can be bought right now. From the old checkboxes when nothing else is given
-- (and in the self-test), or from the group via LiveTargets (see below).
local function OptTargets()
    local T = { sum = {}, port = {}, items = {}, dests = DESTS }
    for _, d in ipairs(DESTS) do
        T.sum[d.key] = Opt("sum_" .. d.key) and true or false
        T.port[d.key] = Opt("port_" .. d.key) and true or false
    end
    T.sumAny = Opt("sum_any") and true or false
    T.portAny = Opt("port_any") and true or false
    return T
end

-- Returns ok, why, service key, place (a destination label) .
local function Evaluate(norm, dedicated, T)
    T = T or OptTargets()
    local dests = T.dests or DESTS
    local sell = HasAny(norm, SELLER)
    if sell then return false, "seller/ad word: " .. sell end

    local buy = HasAny(norm, Opt("strictbuy") and STRICTBUY or BUY)
    -- "summon me" / "port me" asks for one, and no seller says it ("can summon you" is a
    -- seller). The owner's screenshot, 12 Nov 2026: "hey anyone able to summon me to barrens
    -- or org?" had no WTB/LF word and was missed.
    if not buy and not Opt("strictbuy") then
        for _, list in ipairs({ SUMMON_WORDS, PORT_WORDS }) do
            for _, w in ipairs(list) do if not buy and Has(norm, w .. " me") then buy = w .. " me" end end
        end
    end
    if not buy then return false, "no buy word" end
    -- LF is a buying word as clear as WTB (the owner, 13 Nov 2026: "LF means looking for", on
    -- the near miss "LF UC SUmmon/port PST"). "LF guild" is looking for a guild, and "LFM" is
    -- a seller word above.
    local clear = HasAny(norm, STRICTBUY) or
        ((HasAny(norm, { "lf", "lfs", "lfp" }) or Has(norm, "looking for")) and not Has(norm, "lf guild"))
    if not clear then
        local soft = HasAny(norm, SOFTSELLER)
        if soft then return false, "seller/ad word '" .. soft .. "' without a WTB/buying word" end
        local c = HasAny(norm, CONTACT)
        if c then return false, "contact word '" .. c .. "' without a WTB/buying word" end
    end

    -- Lockpicking, water, stones, buffs: their own words, if someone here can do them.
    for _, it in ipairs(T.items or {}) do
        local w = HasAny(norm, it.words)
        if w then return true, it.label .. " ('" .. w .. "'), buy=" .. buy, it.key end
    end

    local wantsSum  = HasAny(norm, SUMMON_WORDS) ~= nil
    local wantsPort = HasAny(norm, PORT_WORDS) ~= nil
    local waived = false
    if not (wantsSum or wantsPort) then
        if dedicated then wantsSum, wantsPort, waived = true, true, true
        else return false, "no summon/port word" end
    end

    -- A place after "from" / "in" / "at" is where they ARE, not where they want to go:
    -- "port to UC from TB" is a UC request. Drop "from <place>" before matching.
    for _, d in ipairs(dests) do
        for _, w in ipairs(d.words) do
            for _, pre in ipairs({ " from ", " in ", " at " }) do
                local n, count = norm:gsub(pre .. w .. " ", " ")
                if count > 0 then norm = n end
            end
        end
    end

    -- "port to TB in UC": an explicit "to <place>" is the destination; any other place
    -- named (in/at UC) is where they are standing, so it does not count.
    -- Only the FIRST "to <place>" counts: "port to UC then to TB" wants UC next, and a summon
    -- to TB doesn't do that (the owner, 13 Nov 2026: "it shouldn't invite").
    local toKeys, anyTo, firstAt = {}, false, nil
    for _, d in ipairs(dests) do
        for _, w in ipairs(d.words) do
            for _, pre in ipairs({ " to ", " 2 " }) do
                local at = norm:find(pre .. w .. " ", 1, true)
                if at and (not firstAt or at < firstAt) then firstAt, toKeys = at, { [d.key] = true } anyTo = true end
            end
        end
    end

    local sawDest = false
    for _, d in ipairs(dests) do
        if (not anyTo or toKeys[d.key]) and HasAny(norm, d.words) then
            sawDest = sawDest or d.label
            -- a summon fetches them from anywhere, so it answers a port request too;
            -- a port (a mage) needs them to come to you, so it does not answer a summon request
            if T.sum[d.key] then
                if wantsSum then return true, "summon to " .. d.label .. ", buy=" .. buy, "summons", d.label end
                if wantsPort then return true, "port request to " .. d.label .. ", you summon there, buy=" .. buy, "summons", d.label end
            end
        end
    end
    if waived and not sawDest then return false, "no place named (needs one when there is no summon/port word)" end
    if (wantsSum or wantsPort) and T.sumAny then return true, "summon (any destination), buy=" .. buy, "summons" end
    -- No place named ("WTB summon"): never assume where they want to go.
    return false, sawDest and "that destination/service is not checked" or "no place named",
        (wantsSum or wantsPort) and "summons" or nil, sawDest or nil
end

----------------------------------------------------------------------
-- The group: who is here, what class and level, and where they are standing.
----------------------------------------------------------------------
local Core = ServiceInviterCore
local function Faction()
    local ok, f = pcall(function() return UnitFactionGroup and UnitFactionGroup("player") end)
    return (ok and (f == "Horde" or f == "Alliance")) and f or "Horde"
end
local function ZoneOf(unit)
    if unit == "player" then
        local ok, z = pcall(function() return GetRealZoneText and GetRealZoneText() end)
        if ok and type(z) == "string" and not IsSecret(z) and z ~= "" then return z end
        return nil
    end
    local ok, z = pcall(function()
        local id = C_Map and C_Map.GetBestMapForUnit and C_Map.GetBestMapForUnit(unit)
        local info = id and C_Map.GetMapInfo and C_Map.GetMapInfo(id)
        return info and info.name
    end)
    if ok and type(z) == "string" and not IsSecret(z) and z ~= "" then return z end
    return nil
end
-- Your own portals, from your spellbook (Forever spell ids; Portal: Undercity 11418 is
-- confirmed for Forever, the rest are Classic's). If none are found the ids may differ on
-- this client, so the level rule is used instead.
local PORTAL_IDS = { ["Portal: Orgrimmar"] = 11417, ["Portal: Undercity"] = 11418, ["Portal: Thunder Bluff"] = 11420,
    ["Portal: Stormwind"] = 10059, ["Portal: Ironforge"] = 11416, ["Portal: Darnassus"] = 11419 }
local function MyKnownPortals(cls)
    if cls ~= "MAGE" then return nil end
    local knows, any = {}, false
    for name, id in pairs(PORTAL_IDS) do
        local k = false
        if IsPlayerSpell then local ok, r = pcall(IsPlayerSpell, id) k = ok and r and true or false end
        if not k and IsSpellKnown then local ok, r = pcall(IsSpellKnown, id) k = ok and r and true or false end
        if k then knows[name] = true any = true end
    end
    return any and knows or nil
end
-- A unit's whole name. Forever names are first + surname, and UnitName gives them as two
-- pieces ("Yeet", "Lock"); GetUnitName(unit, true) gives "Yeet Lock" (the owner's /dump, 13
-- Nov 2026, after "why does it not capture yeet's full name"). Chat already sends the whole name.
local function FullName(unit)
    local ok, n = pcall(function() return GetUnitName and GetUnitName(unit, true) end)
    if ok and type(n) == "string" and not IsSecret(n) and n ~= "" then return Ambiguate and Ambiguate(n, "none") or n end
    local ok2, a = pcall(function() return UnitName and UnitName(unit) end)
    if ok2 and type(a) == "string" and not IsSecret(a) and a ~= "" then return a end
    return nil
end
local MARK_ORDER = { 1, 3, 4, 5, 6, 2, 7, 8 }   -- star, diamond, triangle, moon, square, circle, cross, skull
local assignedMarks = {}                         -- name -> icon we gave them, kept steady while they stay
local previewGroup                               -- set only while a Preview runs: a pretend group
local function GroupSnapshot()
    if previewGroup then return previewGroup end
    local g = {}
    local function add(unit, isMe)
        if not isMe and not (UnitExists and UnitExists(unit)) then return end
        -- anything the game hides (a secret value) is unknown: comparing one is an error
        local function plain(v) if v == nil or IsSecret(v) then return nil end return v end
        local name = FullName(unit)
        if type(name) ~= "string" then return end
        local okc, _, cls = pcall(UnitClass, unit)
        local okl, lvl = pcall(function() return UnitLevel and UnitLevel(unit) end)
        cls, lvl = okc and plain(cls) or nil, okl and plain(lvl) or nil
        local m = { name = name, unit = unit, class = cls, level = (type(lvl) == "number" and lvl > 0) and lvl or nil, zone = ZoneOf(unit) }
        local told = not isMe and Jobs.Team and Jobs.Team.seen[name]
        if told and told.zone and told.zone ~= "" and GetTime() - told.t < 150 then m.zone = told.zone end
        -- Who may provide (the owner, 13 Nov 2026: "so if a random lock were to join my party
        -- sitting in UC would it assume they can summon there?"). A customer (someone who asked
        -- for something) never does; with names given for a class, only those do (and you).
        local j = Jobs.Get and Jobs.Get(name)
        if j and j.service and j.status ~= "paid" and j.status ~= "done" and j.status ~= "left" then m.customer = true end
        if Jobs.IsWorker and Jobs.IsWorker(name) then m.customer, m.worker = nil, true end
        local only = type(ServiceInviterDB.providers) == "table" and ServiceInviterDB.providers[cls]
        if type(only) == "string" and only:find("%S") then
            local listed = false
            for nm in only:gmatch("[^,]+") do
                nm = nm:gsub("^%s+", ""):gsub("%s+$", "")
                if nm:lower() == name:lower() then listed = true end
            end
            if listed then m.customer = nil elseif not isMe then m.notProvider = true end
        end
        if isMe then
            m.me = true
            m.knows = MyKnownPortals(m.class)
            if ServiceInviterDB.role == "lock" then m.summoner = true else m.notSummoner = true end
        end
        g[#g + 1] = m
    end
    add("player", true)
    if IsInRaid and IsInRaid() then
        for i = 1, 40 do
            local u = "raid" .. i
            if not (UnitIsUnit and UnitIsUnit(u, "player")) then add(u) end
        end
    else
        for i = 1, 4 do add("party" .. i) end
    end
    -- Raid icons for whoever does a service (the owner: "I think that works fine"). An icon
    -- someone already put on them is kept and used; otherwise star, diamond, triangle, moon,
    -- square, circle, then cross and skull (groups use those two for kill targets).
    if Opt("marks") then
        local used = {}
        for _, m in ipairs(g) do
            local ok, idx = pcall(function() return GetRaidTargetIndex and GetRaidTargetIndex(m.unit) end)
            if ok and type(idx) == "number" and not IsSecret(idx) and idx >= 1 and idx <= 8 then m.mark = idx used[idx] = true end
        end
        for _, m in ipairs(g) do
            if not m.mark then
                local provides = false
                for _, def in ipairs(Core.SERVICES) do
                    if Core.Setting(ServiceInviterDB, def.key).on and Core.CanDo(m, def) then provides = true break end
                end
                if provides then
                    local want = assignedMarks[m.name]
                    if not want or used[want] then
                        want = nil
                        for _, idx in ipairs(MARK_ORDER) do if not used[idx] then want = idx break end end
                    end
                    if want then m.mark, m.markOurs = want, true used[want] = true assignedMarks[m.name] = want end
                end
            end
        end
    end
    return g
end
-- Is this name in the group? Two-part Forever names ("Yeet Lock") may not resolve through
-- UnitInParty/UnitInRaid, so the group itself is checked too; returns the name as the group
-- spells it. The owner, 14 Nov 2026: "all things must keep 2 part names in mind".
-- Non-payers (the owner, 14 Nov 2026: "add a scam button rather than paid to record them as
-- prior scammers and publicly say it when they join"). Kept with the saved settings.
-- Shared with the team: a name is on the list when its latest "didn't pay", in anyone's book, is
-- newer than its latest "paid after all". Returns the team's total and the name as written.
function Jobs.Scammer(name)
    if type(name) ~= "string" then return nil end
    local db = ServiceInviterDB
    local books = { type(db.scammers) == "table" and db.scammers or {} }
    for _, b in pairs(type(db.teambooks) == "table" and db.teambooks or {}) do books[#books + 1] = b.scammers or {} end
    local found, total, last, cleared = nil, { n = 0, owed = 0 }, -1, -1
    for _, t in ipairs(books) do
        for k, v in pairs(t) do
            if k:lower() == name:lower() then
                found = found or k
                total.n, total.owed = total.n + (v.n or 0), total.owed + (v.owed or 0)
                last = math.max(last, v.last or 0)
                cleared = math.max(cleared, v.cleared or -1)
                if (v.last or 0) > (total.last or 0) then total.last = v.last end
            end
        end
    end
    if not found or last <= cleared then return nil end
    return total, found
end
-- Everyone on the team's didn't-pay list now: { name = total }.
function Jobs.Scammers()
    local db, out, seen = ServiceInviterDB, {}, {}
    local books = { type(db.scammers) == "table" and db.scammers or {} }
    for _, b in pairs(type(db.teambooks) == "table" and db.teambooks or {}) do books[#books + 1] = b.scammers or {} end
    for _, t in ipairs(books) do
        for k in pairs(t) do
            if not seen[k:lower()] then
                seen[k:lower()] = true
                local v, nm = Jobs.Scammer(k)
                if v then out[nm] = v end
            end
        end
    end
    return out
end
function Jobs.ScamLine(name)
    local m = ServiceInviterDB.scammsg
    if m == nil then m = MSG.SCAM end
    if m == "" then return nil end
    return (m:gsub("{name}", function() return name end))
end
-- A recent customer: on the list now, or in the book within the hour (the owner, 14 Nov 2026: "i
-- want to offer a recent customer a buff if they have left"). Returns the name as recorded.
function Jobs.Recent(name)
    if type(name) ~= "string" or name == "" then return nil end
    for _, j in ipairs(Jobs.All and Jobs.All() or {}) do if j.name:lower() == name:lower() then return j.name end end
    local book = Jobs.Book()
    for k, c in pairs(book) do
        local now = (time and time()) or (os and os.time and os.time()) or 0
        if k:lower() == name:lower() and c.last and now - c.last < 3600 then return k end
    end
    return nil
end
function Jobs.InGroup(name)
    if type(name) ~= "string" or name == "" then return false end
    for _, m in ipairs(GroupSnapshot()) do
        if not m.me and m.name:lower() == name:lower() then return m.name end
    end
    if (UnitInParty and UnitInParty(name)) or (UnitInRaid and UnitInRaid(name)) then return name end
    return false
end
-- Class colors, so a busy list reads at a glance (the owner: "can this use class colors and
-- stuff to avoid a mass of confusing text"). The game's own colors when it has them.
local CLASS_HEX = { WARLOCK = "ff8788ee", MAGE = "ff3fc7eb", ROGUE = "fffff569", PRIEST = "ffffffff",
    DRUID = "ffff7c0a", PALADIN = "fff58cba", HUNTER = "ffaad372", SHAMAN = "ff0070dd", WARRIOR = "ffc69b6d" }
local function ClassHex(cls)
    local c = cls and RAID_CLASS_COLORS and RAID_CLASS_COLORS[cls]
    if type(c) == "table" and type(c.colorStr) == "string" then return c.colorStr end
    return cls and CLASS_HEX[cls] or nil
end
local function Colored(name, cls)
    local h = ClassHex(cls)
    return h and ("|c" .. h .. name .. "|r") or name
end
local function MemberName(m) return Colored(m.me and "you" or m.name, m.class) end

local function DestFor(zone)
    if not zone then return nil end
    local z = zone:lower()
    for _, d in ipairs(DESTS) do if d.label:lower() == z then return d end end
    return nil
end
-- What can be bought right now, from who is in the group (see docs/DESIGN.md).
local function LiveTargets(g)
    g = g or GroupSnapshot()
    local T = { sum = {}, port = {}, items = {}, dests = DESTS }
    for _, it in ipairs(Core.OnSale(ServiceInviterDB, g, Faction())) do
        if it.setting.invite then
            if it.def.kind == "summon" then
                -- each warlock summons to where they stand; unknown = no summon invites (never assume)
                local d = DestFor(it.where)
                if d then T.sum[d.key] = true
                elseif it.where then
                    -- a zone that isn't on the list: match its own name
                    local key = "zone:" .. it.where:lower()
                    if T.dests == DESTS then
                        T.dests = {}
                        for _, x in ipairs(DESTS) do T.dests[#T.dests + 1] = x end
                    end
                    -- "The Barrens" is just "barrens" in chat
                    local name = it.where:lower()
                    local words = { name }
                    if name:find("^the ") then words[2] = name:gsub("^the ", "") end
                    T.dests[#T.dests + 1] = { key = key, label = it.where, words = words }
                    T.sum[key] = true
                end
            elseif it.def.kind == "portal" then
                for _, city in ipairs(it.cities) do local d = DestFor(city) if d then T.port[d.key] = true end end
            elseif it.setting.words then
                T.items[#T.items + 1] = { key = it.key, label = it.def.label, words = Core.SplitWords(it.setting.words) }
            end
        end
    end
    return T
end

-- Returns true if we are the one who can invite directly (leader, or raid assistant).
-- If not, we still send the invite call: the game turns it into a "suggest invite"
-- to the leader when you are just a group member.
local function IsInviter()
    if not IsInGroup() then return true end
    if UnitIsGroupLeader("player") then return true end
    if IsInRaid() and UnitIsGroupAssistant and UnitIsGroupAssistant("player") then return true end
    return false
end

local function CanInvite()
    local direct = IsInviter()
    if direct and IsInGroup() and not IsInRaid() and GetNumGroupMembers() >= LIMIT.MAX_PARTY then
        if C_PartyInfo and C_PartyInfo.ConvertToRaid then
            C_PartyInfo.ConvertToRaid()
        elseif ConvertToRaid then
            ConvertToRaid()
        end
    end
    return true, direct
end

local function JobWhere(job, g)
    if not (job and job.service) then return "" end
    g = g or GroupSnapshot()
    local def = Core.BY_KEY[job.service]
    if not def then return "" end
    local p = Core.Provider(g, job.service, job.dest)
    local what
    if def.kind == "summon" then what = "-> " .. Core.Short(job.dest or (p and p.zone) or "?")
    elseif def.kind == "portal" then what = "portal -> " .. Core.Short(job.dest or "?")
    else what = def.label end
    return p and (what .. "  ·  " .. MemberName(p)) or what
end

local function DoInvite(name)
    SI_SELF_INVITING = true
    if C_PartyInfo and C_PartyInfo.InviteUnit then
        C_PartyInfo.InviteUnit(name)
    elseif InviteUnit then
        InviteUnit(name)
    end
    SI_SELF_INVITING = false
end

----------------------------------------------------------------------
-- Jobs: one row per customer we invited, from invite to paid.
----------------------------------------------------------------------
local JOB_STATUS = {
    asked     = { "Asked",     "|cfff0d470" },   -- waiting for your click to invite (you're not the leader)
    invited   = { "Invited",   "|cfff0d470" },
    joined    = { "In group",  "|cff8fe3a0" },
    summoned  = { "Summoning", "|cff8fbff0" },
    arrived   = { "Arrived",   "|cff8fe3f0" },
    paid      = { "Paid",      "|cffb6d98a" },
    done      = { "Done",      "|cffb6d98a" },   -- a free service, finished
    busy      = { "Has a group", "|cffffa040" },   -- invite failed: they are already in another group
    declined  = { "Declined",  "|cffff8080" },
    noanswer  = { "No answer", "|cffa89c78" },
    left      = { "Left",      "|cffa89c78" },
    scammed   = { "Didn't pay", "|cffff8080" },
}
local MAX_JOBS = 30
local INVITE_TIMEOUT = 120
local jobs = {}          -- newest last
local jobByName = {}
local jobsChanged = function() end   -- set by the jobs window
local jobsDirty = false
local RefreshJobs
local pendingTrade, dealName, dealMoney = nil, nil, 0   -- trade tracking (must be declared before the event handler)

local function Now() return (time and time()) or (os and os.time and os.time()) or 0 end
-- "Stats" is the current SESSION: it keeps counting across /reload and logout until you press New session.
local function Stats()
    local st = ServiceInviterDB.stats
    if type(st) ~= "table" then st = {} ServiceInviterDB.stats = st end
    st.start = st.start or Now()
    st.summoned = st.summoned or 0
    st.paid = st.paid or 0
    st.silver = st.silver or 0
    st.ev = st.ev or 0   -- expected silver: price of everyone summoned
    return st
end
-- The summons price (silver; 100 silver = 1 gold). Each service has its own: see JobPrice.
local function Price() return Core.Setting(ServiceInviterDB, "summons").price or 0 end
-- What one customer pays: their service's price, nil when it's free.
-- Following the market (the owner, 14 Nov 2026: "dynamic pricing where we start at a certain
-- amount and will not go below a certain amount but otherwise we compete with by undercutting
-- another service by some amount"). A rival's summon ad for a city counts for 5 minutes; your
-- price there is theirs minus your undercut, never above your own price nor below your floor.
-- No floor set = it never moves (it won't guess how low you'd go).
-- Each channel is its own market (the owner, 14 Nov 2026: "so 4 and 50 are kept apart, good, but
-- how does that work for 42 8 1 etc" -- "it has to detect the different channels it is seeing
-- and recognize sale posts in them to the same exact service and be dynamic to that chat").
-- "Trade - English 50" and "Trade - English 4" never see each other's sellers, so a rival counts
-- only in the channel they posted in, for the city they named. The price for a summon there: the
-- max (your price) when nobody is cheaper; otherwise undercut the cheapest rival by N silver, or
-- match them, never below the min (floor) nor above the max. No min set: it never moves.
Jobs.rivals = {}          -- [market][city][seller] = { price, t }
Jobs.RIVAL_LASTS = 300
function Jobs.MarketOf(channelName)
    if type(channelName) ~= "string" or IsSecret(channelName) or channelName == "" then return nil end
    return (channelName:gsub("^%d+%.%s*", ""))
end
-- the cheapest rival for a city in a market, seen in the last 5 minutes
function Jobs.Rival(where, market)
    market = market or Jobs.priceMarket
    local m = market and where and Jobs.rivals[market] and Jobs.rivals[market][where]
    if not m then return nil end
    local best
    for who, r in pairs(m) do
        if GetTime() - r.t <= Jobs.RIVAL_LASTS and (not best or r.price < best.price) then best = { price = r.price, t = r.t, who = who } end
    end
    return best
end
function Jobs.PriceMode(saved)
    local mode = saved.mode
    if mode == nil then mode = saved.match and "undercut" or "ignore" end   -- before 3.1: one tick box
    return mode
end
Core.LivePrice = function(key, base, saved, where)
    if key ~= "summons" or not where then return base end
    local mode = Jobs.PriceMode(saved)
    if mode == "ignore" then return base end
    local floor = tonumber(saved.floor)
    if not floor then return base end
    local r = Jobs.Rival(where)
    if not r then return base end
    local p = (mode == "match") and r.price or (r.price - (tonumber(saved.undercut) or 5))
    return math.max(floor, math.min(base, p))
end
-- A rival's ad: a seller word, a summon word, a price, and the cities it names. Not you, not
-- anyone in your group, not your workers.
function Jobs.WatchRival(text, sender, market)
    if type(text) ~= "string" or IsSecret(text) or type(sender) ~= "string" then return end
    if not market then return end
    local who = Ambiguate and Ambiguate(sender, "none") or sender
    if who == FullName("player") or Jobs.IsWorker(who) or Jobs.InGroup(who) or (Jobs.IsTeam and Jobs.IsTeam(who)) then return end
    local norm = Norm(text)
    if not HasAny(norm, SELLER) or not HasAny(norm, SUMMON_WORDS) then return end
    local price = Core.OfferedPrice(text)
    if not price or price <= 0 then return end
    local was = Jobs.priceMarket
    Jobs.priceMarket = market
    for _, d in ipairs(DESTS) do
        if HasAny(norm, d.words) then
            local before = Core.Setting(ServiceInviterDB, "summons", d.label).price
            Jobs.rivals[market] = Jobs.rivals[market] or {}
            Jobs.rivals[market][d.label] = Jobs.rivals[market][d.label] or {}
            Jobs.rivals[market][d.label][who] = { price = price, t = GetTime() }
            local now = Core.Setting(ServiceInviterDB, "summons", d.label).price
            if before ~= now then
                P("|cffffd100" .. Core.Short(d.label) .. " price in " .. market .. " now " .. (Core.Money(now) or "free") .. "|r (" .. who .. " is selling at " .. (Core.Money(price) or "?") .. ")")
            end
        end
    end
    Jobs.priceMarket = was
end
local function JobPrice(j)
    -- the price they were told when invited stays theirs; otherwise today's for where they go
    if j and j.price then return j.price end
    return Core.Setting(ServiceInviterDB, (j and j.service) or "summons", j and j.dest).price
end
-- Who gets paid for this customer, and whether that's you.
local function PayeeFor(j, g)
    g = g or GroupSnapshot()
    local key = (j and j.service) or "summons"
    local p = Core.Provider(g, key, j and j.dest or nil)
    -- once a summon starts, the warlock casting it is the one paid (the owner, 14 Nov 2026, on two
    -- warlocks in one city: "it can be the lock summoning - let's just make that how it works")
    if j and j.caster then
        p = nil
        for _, m in ipairs(g) do if m.name:lower() == j.caster:lower() then p = m end end
        p = p or { name = j.caster }
    end
    local here = (j and j.dest) or (p and p.zone)
    local payee = Core.Payee(ServiceInviterDB, g, key, p, here)
    local me = FullName("player")
    return payee, (payee == me), p
end
local function CollectsFor(j) local _, mine = PayeeFor(j) return mine end
-- {price} in every message you write: the same everywhere, the way the ad says it ("30s",
-- "1g50s", "free"). The owner, 12 Nov 2026, seeing "30s" in the welcome and "30 SILVER" in the
-- summon alert: "why does price say 30s on one and 30 silver on the other".
local function PriceText(silver) return Core.Money(silver) or "free" end
-- "1g 25s", "2g", "150s", "25" (a bare number = silver)  ->  silver, or nil
local function ParsePrice(text)
    text = (text or ""):lower()
    local g, sv = text:match("(%d*%.?%d+)%s*g"), text:match("(%d+)%s*s")
    if g or sv then return math.floor((tonumber(g) or 0) * 100 + 0.5) + (tonumber(sv) or 0) end
    local n = tonumber(text:match("^%s*(%d+)%s*$"))
    return n
end
local function Role() return ServiceInviterDB.role == "lock" and "lock" or "helper" end
MSG.WHISPERMSG = "Summoning {name}. Next: {next}"   -- {name} = who we summon, {next} = who has waited longest after
MSG.ALERTMSG = "SUMMONING {name} TO {dest}! PAY {payee} {price} IN THE TRADE WINDOW ON ARRIVAL!"
local OnCast            -- set below: reacts to a group member starting Ritual of Summoning
local ShowAlert         -- set below: big on-screen "click the portal" banner
local ToggleSetup       -- set below: opens the Setup window
local function AutoTradeOn()
    return ServiceInviterDB.autotrade ~= false
end
-- Who takes the money is a setting, not the role: some nights the lock collects,
-- some nights you do. Until it is set, the lock collects.
local function Collects()   -- 1.5 setting, still read by /si collect's first toggle
    local c = ServiceInviterDB.collect
    if c == nil then return Role() == "lock" end
    return c and true or false
end
local function Money(silver) return Core.Money(silver) or "0 silver" end

local function SessionText()
    local st = Stats()
    local text = "Real " .. Money(st.silver) .. " (" .. st.paid .. " paid)   EV " .. Money(st.ev) .. " (" .. st.summoned .. " summoned)"
    if st.ev > 0 then text = text .. "   " .. math.floor(st.silver * 100 / st.ev + 0.5) .. "% collected" end
    local hours = (Now() - st.start) / 3600
    if hours >= 0.083 and st.silver > 0 then text = text .. "  (" .. Money(math.floor(st.silver / hours)) .. "/hr)" end
    if (st.ads or 0) > 0 then text = text .. "   ads " .. st.ads .. ", answered " .. (st.answers or 0) end
    return text
end
local function NewSession() ServiceInviterDB.stats = nil return Stats() end

function Jobs.All() return jobs end
function Jobs.Get(name) return jobByName[name] end

function Jobs.New(name, text, why, channel)
    local old = jobByName[name]
    if old then
        for i, j in ipairs(jobs) do if j == old then table.remove(jobs, i) break end end
    end
    local job = { name = name, text = text, why = why, channel = channel, status = "invited", t = GetTime(), ts = GetTime() }
    jobs[#jobs + 1] = job
    jobByName[name] = job
    while #jobs > MAX_JOBS do
        local gone = table.remove(jobs, 1)
        if jobByName[gone.name] == gone then jobByName[gone.name] = nil end
    end
    jobsChanged(true)
    return job
end

function Jobs.Set(name, status)
    local j = jobByName[name]
    if not j or j.status == status then return j end
    if status == "summoned" then Stats().summoned = Stats().summoned + 1 Stats().ev = Stats().ev + (JobPrice(j) or 0) j.tsummon = GetTime() end
    -- the customer book: a summon counts when it goes out, anything else at Paid / Done
    if status == "summoned" or ((status == "paid" or status == "done") and j.service ~= "summons") then Jobs.Record(j) end
    if status == "arrived" then j.tarrive = GetTime() end
    if status == "paid" then Stats().paid = Stats().paid + 1 Stats().silver = Stats().silver + (j.amount or JobPrice(j) or 0) end
    if status == "paid" or status == "done" or status == "left" or status == "declined" or status == "noanswer" then j.tdone = GetTime() end
    j.status = status
    j.ts = GetTime()   -- when it got to this status, for "waiting 1m 20s"
    jobsChanged()
    return j
end

-- The customer book (the owner, 13 Nov 2026: "can it store our customer base and how many
-- times they use us and when"): kept in the saved settings, so it lasts across sessions.
-- { n = times, by = { summons = 3, ... }, worth = silver at your price then, first, last }
function Jobs.Record(j)
    if not j or j.recorded or Jobs.IsWorker(j.name) then return end
    j.recorded = true
    -- on a team, one copy records each visit, so the shared books don't count it twice: the point
    -- of contact's when one is online; otherwise the copy that invited them
    local poc = Jobs.POC()
    if poc and poc ~= Jobs.Me() then return end
    if not poc and j.why == "invited by someone else" then
        for _, nm in ipairs(Jobs.TeamPeople()) do if Jobs.Online(nm) and Jobs.InGroup(nm) then return end end
    end
    local db = ServiceInviterDB
    db.customers = type(db.customers) == "table" and db.customers or {}
    local now = Now()
    local c = db.customers[j.name] or { n = 0, by = {}, worth = 0, first = now }
    local key = j.service or "other"
    c.n = c.n + 1
    c.by[key] = (c.by[key] or 0) + 1
    c.worth = (c.worth or 0) + (JobPrice(j) or 0)
    c.last = now
    -- where they went, and the totals for /si stats (the owner, 13 Nov 2026: "it should also
    -- track analytics like where they went and stuff for us to know")
    local where = j.dest or "?"
    c.to = c.to or {}
    c.to[where] = (c.to[where] or 0) + 1
    c.rev = Jobs.Bump()
    db.customers[j.name] = c
    local a = type(db.analytics) == "table" and db.analytics or { n = 0, worth = 0, to = {}, by = {}, hour = {}, day = {}, since = now }
    local fmt = date or (os and os.date)
    local t = fmt and fmt("*t", now)
    a.n = a.n + 1
    a.worth = a.worth + (JobPrice(j) or 0)
    a.to[where] = (a.to[where] or 0) + 1
    a.by[key] = (a.by[key] or 0) + 1
    if type(t) == "table" then
        a.hour[t.hour] = (a.hour[t.hour] or 0) + 1
        a.day[t.wday] = (a.day[t.wday] or 0) + 1
    end
    a.rev = Jobs.Bump()
    db.analytics = a
end
-- Near misses: business we could have had (the owner, 14 Nov 2026: "when we record a near miss
-- can we have some data about how much business we could have had"). Counted once per person
-- per 10 minutes (split messages and repeats are one ask), valued at your price for the service.
function Jobs.NearMiss(name, why, key, dest)
    Jobs.nearSeen = Jobs.nearSeen or {}
    local now = GetTime()
    if Jobs.nearSeen[name] and now - Jobs.nearSeen[name] < 600 then return end
    Jobs.nearSeen[name] = now
    local db = ServiceInviterDB
    local a = type(db.analytics) == "table" and db.analytics or { n = 0, worth = 0, to = {}, by = {}, hour = {}, day = {}, since = Now() }
    a.near = type(a.near) == "table" and a.near or { n = 0, worth = 0, why = {}, to = {} }
    local w = tostring(why or "")
    local reason = (w:find("under your", 1, true) and "offered under your price")
        or (w:find("people; a summon", 1, true) and "asked for a group")
        or (w:find("soul shards", 1, true) and "out of shards")
        or (w:find("not checked", 1, true) and "a place you don't serve")
        or (w:find("no place named", 1, true) and "didn't say where")
        or ((w:find("seller", 1, true) or w:find("contact word", 1, true)) and "read as an ad")
        or (w:find("didn't pay", 1, true) and "didn't pay before")
        or w:gsub("%b''", ""):gsub("%d+", ""):sub(1, 40)
    local st = key and Core.BY_KEY[key] and Core.Setting(db, key, dest)
    local price = st and st.price or 0
    a.near.n = a.near.n + 1
    a.near.worth = a.near.worth + price
    a.near.why[reason] = (a.near.why[reason] or 0) + 1
    if dest then a.near.to[dest] = (a.near.to[dest] or 0) + 1 end
    a.rev = Jobs.Bump()
    db.analytics = a
end
-- /si stats: who, where, what, when, since the book started
function Jobs.PrintStats()
    local db = ServiceInviterDB
    local a, book = Jobs.Analytics(), Jobs.Book()
    local function NearLines()
        local nm = type(a) == "table" and a.near
        if not nm or nm.n == 0 then return end
        local function list(t)
            local l = {}
            for k, v in pairs(t) do l[#l + 1] = { k, v } end
            table.sort(l, function(x, y) return x[2] > y[2] end)
            local out = {}
            for _, e in ipairs(l) do out[#out + 1] = e[1] .. " " .. e[2] end
            return table.concat(out, ", ")
        end
        P("Near misses: " .. nm.n .. ", worth " .. Money(nm.worth) .. " at your prices")
        P("Why we missed them: " .. list(nm.why))
        if next(nm.to) then P("Where they wanted to go: " .. list(nm.to)) end
    end
    if type(a) ~= "table" or a.n == 0 then P("no customers yet: they start with the first summon or Paid") NearLines() return end
    -- uses and worth from the book, which began before these stats did ("198 uses by 203
    -- customers", the owner's /si stats, 14 Nov 2026)
    local people, back, uses, worth, first = 0, 0, 0, 0, a.since
    for _, c in pairs(book) do
        people = people + 1
        if c.n > 1 then back = back + 1 end
        uses, worth = uses + (c.n or 0), worth + (c.worth or 0)
        if c.first and (not first or c.first < first) then first = c.first end
    end
    local function top(t, name, limit)
        local list = {}
        for k, v in pairs(t or {}) do list[#list + 1] = { k, v } end
        table.sort(list, function(x, y) return x[2] > y[2] end)
        local out = {}
        for i = 1, math.min(limit or 99, #list) do out[#out + 1] = name(list[i][1]) .. " " .. list[i][2] end
        return #out > 0 and table.concat(out, ", ") or "none yet"
    end
    local DAYS = { "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat" }
    P("Since " .. Jobs.When(first):gsub(" %d+:%d+$", "") .. ": " .. uses .. " uses by " .. people .. " customers (" .. back ..
        " came back), worth " .. Money(worth))
    P("Where they went: " .. top(a.to, function(k) return k end))
    P("Services: " .. top(a.by, function(k) return (Core.BY_KEY[k] and Core.BY_KEY[k].label) or k end))
    P("Busiest hours: " .. top(a.hour, function(h) return ("%02d:00"):format(h) end, 3))
    P("Busiest days: " .. top(a.day, function(d) return DAYS[d] or d end, 3))
    NearLines()
end
-- Soul shards (the owner, 13 Nov 2026: "i want a running counter of summons - like our inv and
-- expected amount left so it knows to stop"). Yours are read from your bags when you're the
-- warlock ("built in for the lock"); other warlocks' you type: /si shards 20. Nil: not counting.
function Jobs.Shards()
    -- only when "Count soul shards" is ticked (the owner, 14 Nov 2026: "having 0 soul shards
    -- should not stop me from inviting if i skip inputting it" -- "maybe a toggle")
    if not Opt("countshards") then return nil end
    local typed = tonumber(ServiceInviterDB.shards)
    local okc, _, cls = pcall(UnitClass, "player")
    local own = okc and cls == "WARLOCK" and GetItemCount and (tonumber(GetItemCount(6265)) or 0) or nil
    if not typed and not own then return nil end
    return (own or 0) + (typed or 0), own, typed
end
-- Workers: your own people, there to click (the owner, 13 Nov 2026: "a way to mark workers so
-- that it doesnt get confused when a worker joins after the raid forms" -- "if someone is just
-- there clicking they won't be a warlock summoning they are just there and click"). A worker
-- never gets a customer row, a welcome or the regulars line, and is never invited from chat.
-- /si worker NAME (or your target), /si workers group marks everyone in the group now.
function Jobs.IsWorker(name)
    if Jobs.IsTeam and Jobs.IsTeam(name) then return true end   -- teammates are never customers
    -- nor is anyone in your guild, addon or not (the owner, 14 Nov 2026: "understand if guild is
    -- in party it is not a customer")
    if Jobs.InMyGuild and Jobs.InMyGuild(name) then return true end
    local w = ServiceInviterDB.workers
    if type(w) ~= "table" or not name then return false end
    name = name:lower()
    for k in pairs(w) do if k:lower() == name then return true end end
    return false
end
function Jobs.SetWorker(name, on)
    ServiceInviterDB.workers = type(ServiceInviterDB.workers) == "table" and ServiceInviterDB.workers or {}
    for k in pairs(ServiceInviterDB.workers) do if k:lower() == name:lower() then ServiceInviterDB.workers[k] = nil end end
    if on then
        -- the name as the game spells it, when they're in the group or on the list
        for _, m in ipairs(GroupSnapshot()) do if m.name:lower() == name:lower() then name = m.name end end
        for _, j in ipairs(jobs) do if j.name:lower() == name:lower() then name = j.name end end
        ServiceInviterDB.workers[name] = true
        local j = Jobs.Get(name)
        if j and not j.service then Jobs.Remove(name) end   -- the "joined your group" row goes
    end
    return name
end
-- summons still to do: buyers invited or waiting who haven't been summoned yet
function Jobs.Queued()
    local n = 0
    for _, j in ipairs(jobs) do
        if j.service == "summons" and (j.status == "invited" or j.status == "asked" or j.status == "joined") then n = n + 1 end
    end
    return n
end
function Jobs.ShardsLeft()
    local have = Jobs.Shards()
    return have and (have - Jobs.Queued()) or nil
end
-- Times they used you before this visit (0 for someone new).
function Jobs.Before(j)
    if j and j.previewBefore then return j.previewBefore end   -- Preview's pretend regular
    local c
    if j then for k, v in pairs(Jobs.Book()) do if k:lower() == j.name:lower() then c = v end end end
    if not c then return 0 end
    return c.n - (j.recorded and 1 or 0)
end
function Jobs.Ordinal(n)
    local tail = n % 100
    local suf = (tail >= 11 and tail <= 13) and "th" or ({ "st", "nd", "rd" })[n % 10] or "th"
    return n .. suf
end
function Jobs.When(t)
    local fmt = date or (os and os.date)
    return (fmt and t) and fmt("%b %d %H:%M", t) or "?"
end

-- Your regulars in chat: the top 10 by visits, or one person's history (/si customers NAME,
-- the first letters are enough). The owner, 13 Nov 2026: "how can i see the list of people in
-- game we have collected - or like top 10 at least".
function Jobs.PrintRegulars(want)
    local book = Jobs.Book()
    local function line(name, c)
        local by = {}
        for k, v in pairs(c.by or {}) do by[#by + 1] = v .. " " .. ((Core.BY_KEY[k] and Core.BY_KEY[k].label) or k) end
        table.sort(by)
        local to = {}
        for k, v in pairs(c.to or {}) do to[#to + 1] = v .. "x " .. k end
        table.sort(to)
        return name .. ": " .. c.n .. (c.n == 1 and " time" or " times") .. " (" .. table.concat(by, ", ") .. ")" ..
            (#to > 0 and (", to " .. table.concat(to, ", ")) or "") .. ", worth " ..
            Money(c.worth or 0) .. ", first " .. Jobs.When(c.first) .. ", last " .. Jobs.When(c.last)
    end
    want = (want or ""):lower()
    local all = want == "all"   -- /si customers all: everyone, not just the top 10
    if all then want = "" end
    if want ~= "" then
        for name, c in pairs(book) do
            if name:lower() == want or name:lower():find(want, 1, true) == 1 then P(line(name, c)) return end
        end
        P("no customer named " .. want .. " in the book")
        return
    end
    local list = {}
    for name, c in pairs(book) do list[#list + 1] = { name, c } end
    table.sort(list, function(a, b) if a[2].n ~= b[2].n then return a[2].n > b[2].n end return (a[2].last or 0) > (b[2].last or 0) end)
    if #list == 0 then P("the customer book is empty so far") return end
    local shown = all and #list or math.min(10, #list)
    P((all and "All " .. #list or ("Top " .. shown .. " of " .. #list)) .. " customers:" ..
        ((not all and #list > 10) and "  (/si customers all for everyone)" or ""))
    for i = 1, shown do P(i .. ". " .. line(list[i][1], list[i][2])) end
end

function Jobs.ClearLeft()
    local gone = {}
    for _, j in ipairs(jobs) do if j.status == "left" then gone[#gone + 1] = j.name end end
    for _, n in ipairs(gone) do Jobs.Remove(n) end
    P(#gone == 0 and "nobody on the list has left" or ("cleared " .. #gone .. " who left"))
end
function Jobs.Joined(name)
    local j = jobByName[name]
    if j and (j.status == "invited" or j.status == "asked") then Jobs.Set(name, "joined") return true end
    return false
end
function Jobs.Left(name)
    local j = jobByName[name]
    if j and (j.status == "joined" or j.status == "invited" or j.status == "summoned" or j.status == "arrived") then
        -- left after the summon, unpaid: the row stays with Paid and Scam until you pick one (the
        -- owner, 14 Nov 2026: "when someone leaves it takes away the option to pick scam?")
        if (j.status == "summoned" or j.status == "arrived") and JobPrice(j) then j.owes = true end
        Jobs.Set(name, "left")
    end
end
function Jobs.Declined(name)
    local j = jobByName[name]
    if j and j.status == "invited" then Jobs.Set(name, "declined") end
end
local BUSY_RETRY_SECONDS = 6
function Jobs.Busy(name)
    local j = jobByName[name]
    if not (j and j.status == "invited") then return end
    j.tries = (j.tries or 0) + 1
    if j.tries >= 2 then
        -- second failure: give up and take them off the list
        Jobs.Remove(name)
        P("|cffffa040" .. name .. " is still in another group|r - removed from the list")
        return
    end
    j.retryAt = GetTime() + BUSY_RETRY_SECONDS
    Jobs.Set(name, "busy")
    P("|cffffa040" .. name .. " is already in another group|r - will retry once in " .. BUSY_RETRY_SECONDS .. "s")
end
function Jobs.Expire(now)
    for _, j in ipairs(jobs) do
        if (j.status == "invited" or j.status == "asked") and now - j.t > INVITE_TIMEOUT * 1.5 then Jobs.Set(j.name, "noanswer") end
        if j.status == "busy" and now - j.t > 300 then Jobs.Set(j.name, "noanswer") end
    end
end
function Jobs.Remove(name)
    local j = jobByName[name]
    if not j then return end
    for i, x in ipairs(jobs) do if x == j then table.remove(jobs, i) break end end
    jobByName[name] = nil
    jobsChanged(true)
end
function Jobs.Clear() wipe(jobs) wipe(jobByName) jobsChanged(true) end

-- A customer's name in party/raid chat, between a raid icon of its own: one the helpers
-- aren't using, kept while they're a customer (the owner, 13 Nov 2026: "the raid icons
-- dont have anything for neato"). Chat only: the game won't let an addon mark heads.
function Jobs.Label(job, name)
    name = name or (job and job.name) or ""
    if not (job and Opt("marks")) then return name end
    if not job.mark then
        local used = {}
        for _, m in ipairs(GroupSnapshot()) do if m.mark then used[m.mark] = true end end
        for _, j in ipairs(jobs) do if j ~= job and j.mark and not j.tdone then used[j.mark] = true end end
        for _, idx in ipairs(MARK_ORDER) do if not used[idx] then job.mark = idx break end end
        if not job.mark then return name end   -- all eight in use: just the name
    end
    return Core.Mark(job.mark, name)
end

-- Thanks when they're done (the owner, 12 Nov 2026: "Paid should also remove from party and
-- maybe send a thank you"). A whisper, so it still reaches them after they leave the group.
MSG.THANKS = "Thanks {name}! Enjoy."
MSG.LOYALTY = "Welcome back, {visits} time with us!"
local function ThanksText(name)
    if ServiceInviterDB.thanks == false then return nil end
    local m = ServiceInviterDB.thanksmsg
    if m == nil then m = MSG.THANKS end
    if m == "" then return nil end
    return (m:gsub("{name}", function() return name end))
end
local function Thank(j)
    if not j or j.thanked then return end
    j.thanked = true
    local t = ThanksText(j.name)
    if t then pcall(Jobs.Route, "thanks", t, j.name) end
end

-- Companion mode: remember what each person last said, and when ANY invite goes
-- out (Trade Inviter, another addon, or you by hand) add that person to the list.
local lastSaid = {}
local function RememberSaid(sender, text, channel)
    if not sender or sender == "" then return end
    local short = Ambiguate and Ambiguate(sender, "none") or sender
    lastSaid[short] = { text = text, channel = channel, t = GetTime() }
    local n = 0
    for _ in pairs(lastSaid) do n = n + 1 end
    if n > 200 then
        local now = GetTime()
        for k, v in pairs(lastSaid) do if now - v.t > 120 then lastSaid[k] = nil end end
    end
end

local warned = false
local function OnInviteCall(name)
    local ok, err = pcall(function()
        if SI_SELF_INVITING or type(name) ~= "string" or name == "" then return end
        if ServiceInviterDB.stasis then return end   -- stopped: your own invites are yours alone
        local short = Ambiguate and Ambiguate(name, "none") or name
        local now = GetTime()
        local existing = jobByName[short]
        if existing and existing.status == "invited" and now - existing.t < 3 then return end
        local said = lastSaid[short]
        if said and now - said.t < 120 then
            Jobs.New(short, said.text, "invite sent by you or another addon", said.channel)
        else
            Jobs.New(short, "(manual invite)", "manual", "-")
        end
    end)
    if not ok and not warned then
        warned = true
        print("|cffff8040Service Inviter|r: tracking error (your invites are not affected): " .. tostring(err))
    end
end
if hooksecurefunc then
    pcall(function()
        if C_PartyInfo and C_PartyInfo.InviteUnit then hooksecurefunc(C_PartyInfo, "InviteUnit", OnInviteCall) end
    end)
    pcall(function()
        if InviteUnit then hooksecurefunc("InviteUnit", OnInviteCall) end
    end)
end

local function UnderRateLimit(now)
    local kept = {}
    for _, t in ipairs(inviteTimes) do
        if now - t < 60 then kept[#kept + 1] = t end
    end
    inviteTimes = kept
    return #inviteTimes < LIMIT.MAX_PER_MINUTE
end

local function IsBlocked(short, guid)
    local blocked = ServiceInviterDB.blocked
    if blocked and blocked[short:lower()] then return true end
    if guid and guid ~= "" and C_FriendList and C_FriendList.IsIgnoredByGUID
        and C_FriendList.IsIgnoredByGUID(guid) then
        return true
    end
    return false
end

local curChannel = ""
MSG.KEYWORDS = "inv, invite"
-- Keywords are for short, plain "inv" requests. Anything that reads like an ad or a
-- summon/port line (seller words, port/summon words, long text) goes to the normal matcher.
local lastAdAt                 -- when you last posted an ad (see Advertise)
local AD_ANSWER_WINDOW = 600   -- a whispered "inv" within 10 minutes of your ad answers it
local function KeywordHit(text, whisper, force)
    if not (Opt("kwon") or force) or type(text) ~= "string" or #text > 30 then return nil end
    local norm = Norm(text)
    local count = 0
    for _ in norm:gmatch("%S+") do count = count + 1 end
    if count > (whisper and 3 or 2) then return nil end
    if HasAny(norm, SELLER) or HasAny(norm, SOFTSELLER) or HasAny(norm, SUMMON_WORDS) or HasAny(norm, PORT_WORDS) then return nil end
    local list = ServiceInviterDB.kwwords
    if type(list) ~= "string" or list:gsub("[%s,]", "") == "" then list = MSG.KEYWORDS end
    local words = {}
    for w in (text:lower():gsub("[^%w%s]", " ")):gmatch("%S+") do words[w] = true end
    for k in list:lower():gmatch("[^,]+") do
        k = k:gsub("^%s+", ""):gsub("%s+$", "")
        if k ~= "" and words[k] then return k end
    end
end

-- Invite a buyer (or, in test mode, run them through without inviting): used for your own buyers
-- and for buyers a teammate hands you as the point of contact. quote: the price they were told.
function Jobs.InviteBuyer(short, text, why, svc, dest, quote, channel, market, answered, test)
    local now = GetTime()
    lastInvite[short] = now
    fragments[short] = nil
    if test then
        D("test mode: not invited")
        Jobs.Rehearse(short, text, why, svc, dest, channel, quote, test.to, market)
        return
    end
    -- no invites-a-minute cap (the owner, 14 Nov 2026: "do not limit the invites to 6 did we
    -- confirm that was needed"): it was ours, not the game's
    CanInvite()   -- turns a full party into a raid when you can
    inviteTimes[#inviteTimes + 1] = now
    -- Always invite, leader or not, as it did through 2.4.1 (the owner, 13 Nov 2026: "it is so dumb
    -- to have to press invite - it worked yesterday").
    DoInvite(short)
    pending[short] = now
    Jobs.invitedNow = true
    local job = Jobs.New(short, text, why, channel)
    job.service, job.dest, job.market = svc, dest, market
    job.price = quote   -- what they pay, even if the market moves
    if answered then job.fromAd = true Stats().answers = (Stats().answers or 0) + 1 end
    -- A whispered welcome goes with the invite, so they know the service and price before they
    -- accept (the owner's flow, 14 Nov 2026: "he whispers them including their price and the
    -- service so they know upfront what it is and they will be summoned soon"). When they join,
    -- only a regular hears anything more. In party/raid chat it waits for them to join, as before.
    if Opt("welcome") and Jobs.RouteOf("welcome") == "whisper" and Jobs.WelcomeText then
        local text = Jobs.WelcomeText(short, job, true)
        if text then Jobs.Route("welcome", text, short) job.welcomed = true end
    end
    if Opt("announce") then
        local what = JobWhere(job)
        if what == "" then what = answered and "(answered your ad)" or why end
        P("invited " .. short .. "  " .. what .. (market and ("  · " .. market .. ", " .. (Core.Money(quote) or "free")) or ""))
        -- exactly why, always (the owner, 13 Nov 2026: "why is it no longer telling me exactly why
        -- people are invited? i want that")
        P("|cff999999   because [" .. tostring(channel) .. "] \"" .. tostring(text) .. "\" = " .. tostring(why) .. "|r")
    end
    if Jobs.TeamSay then Jobs.TeamSay("GOT", short, FullName("player") or "") end
end
local function Handle(text, sender, guid)
    if paused then return end
    local now0 = GetTime()
    local adOpen = lastAdAt and (now0 - lastAdAt) < AD_ANSWER_WINDOW
    if not (Opt("enabled") or Opt("kwon") or (adOpen and curChannel == "whisper")) or not sender or sender == "" then D("skip: addon off or no sender") return end
    if Opt("skipafk") and UnitIsAFK and UnitIsAFK("player") then D("skip: you are AFK (see 'Skip while I'm AFK')") return end
    local short = Ambiguate and Ambiguate(sender, "none") or sender
    if Jobs.IsWorker(short) then D("skip: " .. short .. " is one of your workers") return end
    if Jobs.Scammer(short) then
        D("didn't pay last time")
        if not Jobs.Get(short) then P("|cffff8080skipped|r " .. short .. ": didn't pay last time (/si unscam " .. short .. " to clear)") end
        return
    end
    if short == FullName("player") then return end
    if Jobs.InGroup(short) then D(short .. ": already in your group") return end
    if IsBlocked(short, guid) then D(short .. ": blocked/ignored") return end

    local now = GetTime()
    local cooldown = ServiceInviterDB.cooldown or 180
    if lastInvite[short] and now - lastInvite[short] < cooldown then D(short .. ": invited recently (cooldown)") return end

    local norm = Norm(text)
    local kw = KeywordHit(text, curChannel == "whisper")
    local answered
    if not kw and adOpen and curChannel == "whisper" then
        kw = KeywordHit(text, true, true)
        answered = kw and math.floor(now - lastAdAt) or nil
    end
    local ded = InExtraChannel(curChannel)
    local T = LiveTargets()
    local ok, why, svc, dest
    if answered then ok, why = true, "answered your ad " .. answered .. "s ago"
    elseif kw then ok, why = true, "keyword '" .. kw .. "'"
    elseif Opt("enabled") then ok, why, svc, dest = Evaluate(norm, ded, T)
    else ok, why = false, "invites are off (only keywords are on)" end
    diag.eval = { who = short, ok = ok, why = why, t = GetTime() }

    if Opt("fragments") then
        local frags = fragments[short] or {}
        local fresh = {}
        for _, f in ipairs(frags) do
            if now - f.t < LIMIT.FRAGMENT_WINDOW then fresh[#fresh + 1] = f end
        end
        fresh[#fresh + 1] = { t = now, n = norm }
        while #fresh > LIMIT.MAX_FRAGMENTS do table.remove(fresh, 1) end
        fragments[short] = fresh

        if not ok and #fresh > 1 then
            local parts = {}
            for _, f in ipairs(fresh) do parts[#parts + 1] = f.n end
            ok, why, svc, dest = Evaluate(" " .. table.concat(parts, " ") .. " ", ded, T)
            if ok then why = "fragments: " .. why end
        end
    end

    -- A buyer naming less than your price is not invited (the owner, 13 Nov 2026, on "wtb tb sum
    -- 25s" at 35 silver: "this is below our price ... this should be filtered out"). Said as a
    -- near miss, so you can still invite them yourself.
    if ok and svc then
        local price = Core.Setting(ServiceInviterDB, svc, dest).price
        local offer = Core.OfferedPrice(text)
        if price and offer and offer < price then
            ok, why = false, "offers " .. Money(offer) .. ", under your " .. Money(price)
        end
    end
    -- a summon is one person at a time (the owner, 13 Nov 2026, on "WTB port for 2 to UC": "we
    -- would not want to accept multiple people for our summon"); a portal takes a group
    if ok and svc == "summons" then
        local heads = Core.PartySize(text)
        if heads then ok, why = false, "asks for " .. heads .. " people; a summon is one at a time" end
    end
    -- no shards left for them once the queue is summoned: stop inviting summon buyers
    if ok and svc == "summons" then
        local left = Jobs.ShardsLeft()
        if left and left <= 0 then
            ok, why = false, "out of soul shards (" .. Jobs.Shards() .. " left, " .. Jobs.Queued() .. " already queued; /si shards N to top up)"
        end
    end

    -- Near miss: sounds like a buyer (buy word + summon/port word, not a seller) but we said no.
    if not ok and not HasAny(norm, SELLER)
        and HasAny(norm, BUY) and (HasAny(norm, SUMMON_WORDS) or HasAny(norm, PORT_WORDS)) then
        Jobs.NearMiss(short, why, svc or "summons", dest)
        if ServiceInviterDB.near ~= false then
            P("|cffffa040NEAR MISS|r " .. short .. " [" .. curChannel .. "] \"" .. text .. "\" -> " .. why)
        end
    end

    -- Only talk about messages that look like summon/port talk, so debug stays readable.
    if ok or HasAny(norm, SUMMON_WORDS) or HasAny(norm, PORT_WORDS) then
        D("[" .. curChannel .. "] " .. short .. ": \"" .. text .. "\" -> " .. (ok and "MATCH" or "no") .. " (" .. why .. ")")
    end
    if not ok then return end

    local quote = Core.Setting(ServiceInviterDB, svc or "summons", dest).price   -- this channel's price, now
    -- a team with a point of contact who isn't you: hand them the buyer and the quote (the owner,
    -- 14 Nov 2026: "i told you i want a point of contact, so that. it just gives them that point in
    -- time price"). They invite and do the talking; you never reach the stranger.
    local poc = Jobs.POC and Jobs.POC()
    if poc and poc ~= FullName("player") then
        lastInvite[short] = now
        fragments[short] = nil
        Jobs.HandOff(poc, short, svc, dest, quote, curChannel, Jobs.market, text, why)
        Jobs.invitedNow = true
        return
    end
    Jobs.InviteBuyer(short, text, why, svc, dest, quote, curChannel, Jobs.market, answered,
        ServiceInviterDB.dryrun and { to = ServiceInviterDB.testto } or nil)
end
-- Join detection: the game prints "<name> joins the party." / "has joined the raid group."
local function PatternFrom(globalStr, fallback)
    local g = (type(globalStr) == "string" and globalStr ~= "") and globalStr or fallback
    g = g:gsub("([%^%$%(%)%%%.%[%]%*%+%-%?])", "%%%1")
    return "^" .. g:gsub("%%%%s", "(.+)"):gsub("%%%%1%%%$s", "(.+)") .. "$"
end
local JOIN_PATTERNS = {
    PatternFrom(ERR_JOINED_GROUP_S, "%s joins the party."),
    PatternFrom(ERR_RAID_MEMBER_ADDED_S, "%s has joined the raid group."),
}

-- The line a regular hears ("Regulars hear" box), filled in; nil for a first-timer or when
-- the box is empty. The owner, 13 Nov 2026: "can we even announce loyalty in the chat?",
-- "HOW CAN I SAY SOMETHING LIKE THIS IS YOUR 4TH TIME!!", "can you make this simpler?".
function Jobs.LoyaltyLine(job)
    local before = Jobs.Before(job)
    local line = ServiceInviterDB.loyaltymsg
    if line == nil then line = (Opt("loyalty") ~= false) and MSG.LOYALTY or "" end   -- an old unticked box: off
    if before <= 0 or line == "" then return nil end
    local caps = line:gsub("{%a+}", "") == line:gsub("{%a+}", ""):upper() and line:find("%a")
    local nth = Jobs.Ordinal(before + 1)
    line = line:gsub("{visits}", function() return caps and nth:upper() or nth end)
    -- {name} too (the owner, 13 Nov 2026: "can i use {name} in regular hear")
    return (line:gsub("{name}", function() return Jobs.Label(job, job.name) end))
end

local function WelcomeText(name, job, noLoyal)
    job = job or Jobs.Get(name)
    local g, fac = GroupSnapshot(), Faction()
    local loyal = job and not noLoyal and Jobs.LoyaltyLine(job)
    -- A regulars line with {name} in it greets them itself, so it takes the place of the hello at
    -- the start of the welcome rather than repeating the name (the owner, 13 Nov 2026: "i dont
    -- want them to see hi your name welcome back your name later").
    local named = loyal and (ServiceInviterDB.loyaltymsg or ""):find("{name}", 1, true)
    local function Lead(rest)
        rest = (rest or ""):gsub("^%s+", "")
        local sep = loyal:find("[%.!?]%s*$") and " " or ". "
        return rest ~= "" and (loyal:gsub("%s+$", "") .. sep .. rest) or loyal
    end
    local custom = ServiceInviterDB.welcomemsg
    if custom and custom ~= "" and custom ~= MSG.WELCOME then
        local key = (job and job.service) or "summons"
        local payee, mine = PayeeFor(job, g)
        local price = PriceText(JobPrice(job))
        local label = Core.BY_KEY[key].label
        local hasVisits = custom:find("{visits}", 1, true)
        -- the hello: the first sentence, when it carries {name} ("Hi {name}!")
        local greet = named and not hasVisits and custom:match("^%s*[^%.!?]-{name}[^%.!?]*[%.!?]+%s*")
        if greet then custom = custom:sub(#greet + 1) end
        custom = custom:gsub("{name}", function() return Jobs.Label(job, name) end):gsub("{price}", function() return price end)
        custom = custom:gsub("{payee}", function() return mine and "me" or Core.Label(g, payee) end):gsub("{service}", function() return label end)
            :gsub("{dest}", function() return (job and job.dest) or "" end)
        custom = custom:gsub("{visits}", function()
            local nth = Jobs.Ordinal(Jobs.Before(job) + 1)
            return (custom:gsub("{%a+}", "") == custom:gsub("{%a+}", ""):upper()) and nth:upper() or nth
        end)
        -- your own welcome without {visits}: a regular gets the "Regulars hear" line after it
        -- (the owner's: "THE COST IS {price} AND WE WILL SUMMON YOU SOON!" + "HEY FREQUENT FLYER!
        -- This is your {visits} time with us!")
        if greet then return Lead(custom) end
        if loyal and not hasVisits then custom = custom:gsub("%s+$", "") .. " " .. loyal end
        return custom
    end
    if job and job.service then
        local text = Core.JoinWelcome(ServiceInviterDB, g, fac, job.service, Jobs.Label(job, name), job.dest, job.price)
        if text and loyal and named then text = Lead((text:gsub("^Hi .-! ", "", 1)))
        elseif text and loyal then text = text:gsub("^(Hi .-!) ", function(hi) return hi .. " " .. loyal .. " " end, 1) end
        if text then return text end
    end
    local list = Core.BuildAd(ServiceInviterDB, g, fac, "{services}")
    if list and named then return Lead("We have " .. list .. ". What can we do for you?") end
    if list then return "Hi " .. name .. "! " .. (loyal and (loyal .. " ") or "") .. "We have " .. list .. ". What can we do for you?" end
    if loyal then return named and loyal or ("Hi " .. name .. "! " .. loyal) end
    return nil
end
Jobs.WelcomeText = WelcomeText

local LEAVE_PATTERNS = {
    PatternFrom(ERR_RAID_MEMBER_REMOVED_S, "%s has left the raid group."),
    PatternFrom(ERR_LEFT_GROUP_S, "%s leaves the party."),
}
local ALREADY_PATTERN = PatternFrom(ERR_ALREADY_IN_GROUP_S, "%s is already in a group.")
local DECLINE_PATTERN = PatternFrom(ERR_DECLINE_GROUP_S, "%s declines your group invitation.")

local function OnSystem(text)
    if not text then return end
    local function nm(w) return Ambiguate and Ambiguate(w, "none") or w end

    local a = text:match(ALREADY_PATTERN)
    if a then
        local short = nm(a)
        pending[short] = nil
        lastInvite[short] = nil   -- let them re-ask / be re-invited right away
        Jobs.Busy(short)
        return
    end
    -- "You have suggested that X join your group.": the game didn't invite them (an invite
    -- that wasn't a click, sent while not the leader). Put them back in line for your click.
    local sug = text:match(PatternFrom(_G and _G.ERR_INVITE_PLAYER_SUGGESTED_S, "You have suggested that %s join your group."))
    if sug then
        local j = Jobs.Get(nm(sug))
        -- The suggestion reaches the leader, who lets them in (the owner, 13 Nov 2026: "it is
        -- working when i am not assist and suggested invite"). They stay invited.
        if j then j.suggested = true end
        return
    end
    local d = text:match(DECLINE_PATTERN)
    if d then
        local j = Jobs.Get(nm(d))
        Jobs.Declined(nm(d))
        return
    end
    for _, pat in ipairs(LEAVE_PATTERNS) do
        local w = text:match(pat)
        if w then Jobs.Left(nm(w)) return end
    end

    local who
    for _, pat in ipairs(JOIN_PATTERNS) do
        who = text:match(pat)
        if who then break end
    end
    if not who then return end
    local short = nm(who)
    if Jobs.IsWorker(short) then pending[short] = nil return end   -- one of yours: nothing to do
    if Jobs.Scammer(short) then
        pending[short] = nil
        local line = Jobs.ScamLine(short)
        -- as a raid warning when you may (big, mid-screen, for everyone), else raid/party chat
        -- (the owner, 14 Nov 2026: "can the scam message be flashier to be more public")
        local ch = (IsInRaid and IsInRaid()) and "RAID" or "PARTY"
        if ch == "RAID" and Jobs.CanRemove() then ch = "RAID_WARNING" end
        if line then Jobs.Route("scam", line, short, ch) end
        P("|cffff8080" .. short .. " didn't pay last time.|r")
        return
    end
    -- Someone joined who nobody here invited (a friend invited them): give them a row too.
    if not Jobs.Get(short) and short ~= FullName("player") then
        Jobs.New(short, "(joined your group)", "invited by someone else", "-")
    end
    Jobs.Joined(short)
    local t = pending[short]
    pending[short] = nil
    local fresh = t and GetTime() - t <= 180          -- we invited them just now
    -- A regular always hears it, however they got in (the owner, 13 Nov 2026: "i want the regular
    -- coming back messages to always play if it detects someone joined again").
    local loyal = Jobs.LoyaltyLine(Jobs.Get(short) or { name = short })
    if not fresh and not loyal then return end
    local channel = (IsInRaid and IsInRaid()) and "RAID" or "PARTY"
    -- Someone else invited them, or the welcome is off: we don't know what they came for, so no
    -- service and no price, just hello and the regulars line (the owner, 13 Nov 2026: "if we dont
    -- know what we invited them for why would we show the price and service").
    if not fresh or not Opt("welcome") or (Jobs.Get(short) and Jobs.Get(short).welcomed) then
        -- with {name} in it, your line already greets them: no "Hi Kaldrok!" in front
        local named = (ServiceInviterDB.loyaltymsg or ""):find("{name}", 1, true)
        if loyal then Jobs.Route("loyal", named and loyal or ("Hi " .. Jobs.Label(Jobs.Get(short), short) .. "! " .. loyal), short, channel) end
        return
    end
    local welcome = WelcomeText(short)
    if not welcome then D(short .. " joined; nothing on sale to welcome them with") return end
    D(short .. " joined, sending welcome to " .. channel)
    Jobs.Route("welcome", welcome, short, channel)
end

local function ChannelAllowed(ch)
    ch = (ch or ""):lower()
    if Opt("trade") and (ch:find("trade", 1, true) or ch:find("services", 1, true)) then return true end
    if Opt("general") and ch:find("general", 1, true) then return true end
    if InExtraChannel(ch) then return true end
    return false
end

local f = CreateFrame("Frame")
f:RegisterEvent("CHAT_MSG_CHANNEL")
f:RegisterEvent("CHAT_MSG_SAY")
f:RegisterEvent("CHAT_MSG_WHISPER")
f:RegisterEvent("CHAT_MSG_YELL")
f:RegisterEvent("CHAT_MSG_SYSTEM")
f:RegisterEvent("PLAYER_LOGIN")
f:RegisterEvent("CHAT_MSG_ADDON")
f:RegisterEvent("GROUP_ROSTER_UPDATE")
f:RegisterEvent("GUILD_ROSTER_UPDATE")
f:RegisterEvent("ZONE_CHANGED_NEW_AREA")
f:RegisterEvent("PLAYER_REGEN_ENABLED")
f:RegisterEvent("UI_ERROR_MESSAGE")
f:RegisterEvent("ADDON_ACTION_FORBIDDEN")
f:RegisterEvent("ADDON_ACTION_BLOCKED")
f:RegisterEvent("CHAT_MSG_BN_WHISPER_INFORM")
f:RegisterEvent("CHAT_MSG_WHISPER_INFORM")
f:RegisterEvent("TRADE_SHOW")
f:RegisterEvent("TRADE_ACCEPT_UPDATE")
f:RegisterEvent("TRADE_CLOSED")
f:RegisterEvent("UNIT_SPELLCAST_START")
f:RegisterEvent("UNIT_SPELLCAST_CHANNEL_START")
f:RegisterEvent("UNIT_SPELLCAST_SUCCEEDED")
f:RegisterEvent("CHAT_MSG_PARTY")
f:RegisterEvent("CHAT_MSG_PARTY_LEADER")
f:RegisterEvent("CHAT_MSG_RAID")
f:RegisterEvent("CHAT_MSG_RAID_LEADER")
f.Handle = function(_, event, text, sender, arg3, channelName, _, _, _, _, channelBaseName, _, _, guid)
    -- stasis (/si stop): hears nothing, does nothing, until /si start (the owner, 13 Nov 2026:
    -- "a command that stops it from running altogether so it's just in stasis")
    if ServiceInviterDB and ServiceInviterDB.stasis then
        if event == "PLAYER_LOGIN" then P("|cffff8040stopped|r: hearing nothing and doing nothing. /si start to wake it.") end
        return
    end
    if event == "CHAT_MSG_ADDON" then
        -- prefix, message, how it came, who sent it
        Report("team", pcall(Jobs.TeamReceive, text, sender, arg3, channelName))
        return
    end
    if event == "GUILD_ROSTER_UPDATE" then Report("guild", pcall(Jobs.ReadGuild)) return end
    if event == "GROUP_ROSTER_UPDATE" or event == "ZONE_CHANGED_NEW_AREA" then
        if Jobs.TeamOn() and GetTime() - Jobs.Team.lastHi > 5 then Report("team", pcall(Jobs.SayHi, event == "GROUP_ROSTER_UPDATE")) end
        return
    end
    if event == "CHAT_MSG_PARTY" or event == "CHAT_MSG_PARTY_LEADER" or event == "CHAT_MSG_RAID" or event == "CHAT_MSG_RAID_LEADER" then
        local okb, errb = pcall(BuffAsk, text, sender)
        if not okb then Jobs.BuffNote(sender, text, "error: " .. tostring(errb)) end
        Report("buffs", okb, errb)
        return
    end
    if event == "UNIT_SPELLCAST_SUCCEEDED" and text == "player" then
        pcall(BuffCastDone, (type(channelName) == "string" and channelName) or SpellNameOf(arg3))
    end
    if event == "UNIT_SPELLCAST_START" or event == "UNIT_SPELLCAST_CHANNEL_START" or event == "UNIT_SPELLCAST_SUCCEEDED" then
        if OnCast then
            local ok, err = pcall(OnCast, event, text, arg3)
            if not ok then
                diag.errs = diag.errs or {}
                local msg = tostring(err)
                if not diag.errs[msg] then diag.errs[msg] = true P("|cffff4040error in ritual alert:|r " .. msg) end
            end
        end
        return
    end
    if event == "TRADE_SHOW" then
        dealName, dealMoney = nil, 0
        return
    end
    if event == "TRADE_ACCEPT_UPDATE" then
        -- both sides pressed Accept: remember who and how much they are paying
        if text == 1 and sender == 1 then
            -- who is on the other side: the trade window's partner, else the one we clicked Trade for
            local who
            local npc = FullName("NPC")
            if npc then
                npc = Ambiguate and Ambiguate(npc, "none") or npc
                if Jobs.Get(npc) then who = npc end
            end
            if not who and pendingTrade and Jobs.Get(pendingTrade) then who = pendingTrade end
            if not who then
                -- last resort: if exactly one customer has arrived, it is them
                local only, count = nil, 0
                for _, j in ipairs(jobs) do if j.status == "arrived" then only = j.name count = count + 1 end end
                if count == 1 then who = only end
            end
            dealName = who
            dealMoney = (GetTargetTradeMoney and GetTargetTradeMoney()) or 0
            D("trade accepted by both: " .. tostring(dealName) .. " pays " .. Money(math.floor(dealMoney / 100)))
        else
            -- someone took their Accept back (changed the money, moved an item): what we
            -- noted no longer stands, or a trade cancelled after this would count as Paid
            if dealName then D("trade accept taken back: " .. tostring(dealName) .. " not paid yet") end
            dealName, dealMoney = nil, 0
        end
        return
    end
    if event == "TRADE_CLOSED" then
        local who, money = dealName, dealMoney
        dealName, dealMoney = nil, 0
        if who and Jobs.Get(who) then
            local silver = math.floor(money / 100)
            local need = JobPrice(Jobs.Get(who))
            if silver > 0 and silver >= (need or 0) then
                Jobs.Get(who).amount = silver
                Jobs.Set(who, "paid")
                Thank(Jobs.Get(who))
                P(Colored(who, Jobs.Get(who).class) .. (need and " paid " or " tipped ") .. Money(silver) .. ". Marked Paid. Press x on their row to remove them.")
            elseif silver > 0 then
                P(who .. " traded " .. Money(silver) .. ", less than the " .. Money(need) .. " price. Not marked Paid.")
            end
        end
        return
    end
    if event == "CHAT_MSG_BN_WHISPER_INFORM" or event == "CHAT_MSG_WHISPER_INFORM" then
        diag.echo = { t = GetTime(), kind = event == "CHAT_MSG_BN_WHISPER_INFORM" and "Battle.net" or "normal" }
        return
    end
    -- The game stopped one of our calls. FORBIDDEN (its "blocked from an action only available
    -- to the Blizzard UI" popup) is for good: never make that call again this session. BLOCKED
    -- is for that moment (in combat, say): said once, and tried again next time.
    if event == "ADDON_ACTION_FORBIDDEN" or event == "ADDON_ACTION_BLOCKED" then
        if text == ADDON_NAME and type(sender) == "string" then
            local fn = sender:gsub("%(%)$", "")
            if event == "ADDON_ACTION_FORBIDDEN" and not blockedCalls[fn] then
                blockedCalls[fn] = true
                P("the game blocked " .. fn .. "(), which only Blizzard's own code may call. Service Inviter won't try it again this session. Please report it.")
            elseif event == "ADDON_ACTION_BLOCKED" then
                Report("game blocked " .. fn, false, fn .. "() was blocked just then (in combat?). It will try again next time.")
            end
        end
        return
    end
    if event == "UI_ERROR_MESSAGE" then
        local emsg = type(sender) == "string" and sender or (type(text) == "string" and text or "")
        local low = (type(SPELL_FAILED_LOWLEVEL) == "string" and SPELL_FAILED_LOWLEVEL ~= "") and SPELL_FAILED_LOWLEVEL or "too low level"
        if not IsSecret(emsg) and emsg:lower():find(low:lower(), 1, true) then pcall(BuffTooLow) end
        diag.uierr = { t = GetTime(), msg = tostring(sender or text) }
        if debugOn then D("game error: " .. tostring(text) .. (sender and (" / " .. tostring(sender)) or "")) end
        return
    end
    if event == "PLAYER_REGEN_ENABLED" then
        Jobs.AfterCombat()
        if jobsDirty then RefreshJobs() end
        if buffDirty then RefreshBuff() end
        return
    end
    if event == "PLAYER_LOGIN" then
        MigrateLegacy()
        MigrateServices()
        local isLoaded = (C_AddOns and C_AddOns.IsAddOnLoaded) or IsAddOnLoaded
        if isLoaded and isLoaded("TradeInviter") then
            paused = true
            P("Trade Inviter is running too: tracking and alerts only (no invites). /si on to take over.")
        end
        if not paused and not ServiceInviterDB.autoOn then
            ServiceInviterDB.autoOn = true
            if not Opt("enabled") then SetOpt("enabled", true) P("Trade Inviter is gone, so invites are now turned ON.") end
        end
        if not paused and not Opt("enabled") then
            P("|cffff8040Invites are OFF.|r Tick 'Invite people who ask for a summon/port' in /si setup (or type /si on).")
        end
        debugOn = ServiceInviterDB.debug and true or false
        if debugOn then P("debug is ON") end
        if IsInGuild and IsInGuild() then
            local ask = (C_GuildInfo and C_GuildInfo.GuildRoster) or GuildRoster
            if ask then pcall(ask) end
        end
        if Jobs.TeamOn() then Report("team", pcall(Jobs.SayHi, true)) end
        return
    end
    if event == "CHAT_MSG_SYSTEM" then
        if debugOn and text then
            local l = text:lower()
            if l:find("invit") or l:find("group") or l:find("party") or l:find("raid") then D("game says: " .. text) end
        end
        OnSystem(text)
        return
    end
    curChannel = tostring(channelBaseName ~= "" and channelBaseName or channelName)
    -- the market: the full channel name ("Trade - English 50"), or Say/Yell/whisper as one each
    Jobs.market = (event == "CHAT_MSG_CHANNEL" and Jobs.MarketOf(channelName)) or (event == "CHAT_MSG_SAY" and "Say") or
        (event == "CHAT_MSG_YELL" and "Yell") or nil
    if event == "CHAT_MSG_CHANNEL" then
        local ch = (channelBaseName and channelBaseName ~= "") and channelBaseName or channelName
        if not ChannelAllowed(ch) then return end
    elseif event == "CHAT_MSG_SAY" then
        Report("buffs", pcall(BuffAsk, text, sender))   -- a customer who left, standing nearby
        if not Opt("say") then return end
    elseif event == "CHAT_MSG_YELL" then
        if not Opt("yell") then return end
    elseif event == "CHAT_MSG_WHISPER" then
        curChannel = "whisper"
        Report("buffs", pcall(BuffAsk, text, sender))
        if not KeywordHit(text, true) and not Opt("enabled") then return end
    end
    Report("prices", pcall(Jobs.WatchRival, text, sender, Jobs.market))
    diag.heard = { ch = curChannel, who = sender, text = text, t = GetTime(), event = event }
    RememberSaid(sender, text, curChannel)
    -- what was decided about each person, for /si why NAME (the owner, 14 Nov 2026: "this didnt
    -- seem to register?")
    local who = (Ambiguate and type(sender) == "string" and Ambiguate(sender, "none")) or sender
    if type(who) == "string" then
        Jobs.heard = Jobs.heard or {}
        Jobs.heardN = (Jobs.heardN or 0) + 1
        if Jobs.heardN > 400 then Jobs.heard, Jobs.heardN = {}, 1 end
        Jobs.whyNow = { text = text, ch = curChannel, t = GetTime(), why = "not a buyer's message" }
        Jobs.heard[who:lower()] = Jobs.whyNow
    end
    Jobs.priceMarket = Jobs.market          -- every price worked out while handling this line is this channel's
    local ok, err = pcall(Handle, text, sender, guid)
    Jobs.priceMarket = nil
    if Jobs.whyNow and Jobs.invitedNow then Jobs.whyNow.why = "invited" end
    Jobs.whyNow, Jobs.invitedNow = nil, nil
    if not ok then error(err, 0) end
end
f:SetScript("OnEvent", function(self, event, ...) Report(event, pcall(f.Handle, self, event, ...)) end)

-- (The old settings window is gone: everything is in the Setup window, /si setup.)
local function ToggleUI() if ToggleSetup then ToggleSetup() end end

----------------------------------------------------------------------
-- Advertise: the game lets an ad go out only from a key press or click, so each ad is
-- one press. The text is built from what is on sale; the button tells you when you can
-- post again in each channel (so you don't get reported for spam).
----------------------------------------------------------------------
MSG.AD = "{wts}{services} | whisper inv"
local lastAdIn = {}   -- channel key -> when you last posted there
local function AdWait() return math.max(1, tonumber(ServiceInviterDB.adwait) or 5) * 60 end
local function AdChannels()
    local db, out = ServiceInviterDB, {}
    local ch = type(db.adchans) == "table" and db.adchans or { trade = true }
    if ch.trade then out[#out + 1] = "trade" end
    if ch.general then out[#out + 1] = "general" end
    for name in tostring(db.adextra or ""):lower():gmatch("[^,]+") do
        name = name:gsub("^%s+", ""):gsub("%s+$", "")
        if name ~= "" then out[#out + 1] = name end
    end
    return out
end
local function ChannelId(key)
    if not GetChannelList then return nil end
    local list = { GetChannelList() }
    for i = 1, #list, 3 do
        local id, name = list[i], list[i + 1]
        if type(name) == "string" and name:lower():find(key, 1, true) then return id, name end
    end
    return nil
end
-- "ready", key, id, name, text  |  "wait", seconds  |  "off", why
local function AdState()
    local text, why = Core.BuildAd(ServiceInviterDB, GroupSnapshot(), Faction(), ServiceInviterDB.admsg)
    if not text then return "off", why end
    if UnitIsAFK and UnitIsAFK("player") then return "off", "you're AFK" end
    local now, soonest, any = GetTime(), nil, false
    for _, key in ipairs(AdChannels()) do
        local id, name = ChannelId(key)
        if id then
            any = true
            local last = lastAdIn[key]
            local left = last and (AdWait() - (now - last)) or 0
            if left <= 0 then
                -- that channel's own price in the ad
                local was = Jobs.priceMarket
                Jobs.priceMarket = Jobs.MarketOf(name)
                local own = Core.BuildAd(ServiceInviterDB, GroupSnapshot(), Faction(), ServiceInviterDB.admsg)
                Jobs.priceMarket = was
                return "ready", key, id, name, own or text
            end
            if not soonest or left < soonest then soonest = left end
        end
    end
    if not any then return "off", "you're not in any of the ad channels" end
    return "wait", soonest
end
local function AdLabel()
    local state, a = AdState()
    if state == "ready" then return "Post in " .. a:sub(1, 1):upper() .. a:sub(2), true end
    if state == "wait" then return ("Next ad %d:%02d"):format(math.floor(a / 60), math.floor(a % 60)), false end
    return "Ad off", false
end
local function PostAd()
    local state, key, id, name, text = AdState()
    if state ~= "ready" then
        P(state == "wait" and ("next ad in " .. math.ceil(key) .. "s") or ("no ad: " .. tostring(key)))
        return
    end
    SendChatMessage(text, "CHANNEL", nil, id)
    local now = GetTime()
    lastAdIn[key] = now
    lastAdAt = now
    Stats().ads = (Stats().ads or 0) + 1
    D("ad posted in " .. tostring(name))
    if RefreshJobs then RefreshJobs() end
end
-- the channel the next ad goes to, as the game names it (for the setup's preview line)
function Jobs.AdChannelName()
    local _, _, _, name = AdState()
    return type(name) == "string" and name:gsub("^%d+%.%s*", ""):gsub(" %- .*$", "") or "Trade"
end
-- A named button so a key can press it: /si bind ad F7
local adKey = CreateFrame("Button", "ServiceInviterAdButton", UIParent)
adKey:SetScript("OnClick", function() PostAd() end)
adKey:Hide()

----------------------------------------------------------------------
-- The buff button: one key (/si bind buff F8) that casts the right buff on the next person
-- who needs it. The game only casts from a key press, so it's one press per buff; the addon
-- aims the button. Who is queued: customers landing where you are, and anyone in the group
-- who asks ("fort pls"). Out of combat only (the game won't let an addon re-aim it in combat).
----------------------------------------------------------------------
local buffQueue = {}   -- { name, key, spell, rank }
local function MyBuffs()
    local okc, _, cls = pcall(UnitClass, "player")
    local out = {}
    if not okc then return out end
    for _, def in ipairs(Core.SERVICES) do
        if def.kind == "buff" and def.class == cls and Core.Setting(ServiceInviterDB, def.key).on then out[#out + 1] = def end
    end
    return out
end
local InGroupByName = function(name) return Jobs.InGroup(name) end
local buffKey = CreateFrame("Button", "ServiceInviterBuffButton", UIParent, "SecureActionButtonTemplate")
buffKey:SetAttribute("type", "macro")
buffKey:RegisterForClicks("AnyUp", "AnyDown")
buffKey:Hide()
buffDirty = false
local function BuffMacro(e)
    if not e then return "" end
    local spell = e.spell or Core.Setting(ServiceInviterDB, e.key).spell or ""
    -- cast on their group slot (raid3), not their name: a two-part name ("Yeet Lock") is safest
    -- left out of the macro
    local at
    for _, m in ipairs(GroupSnapshot()) do
        if m.unit and not m.me and m.name:lower() == e.name:lower() then at = m.unit break end
    end
    local r = (e.rank and ("(Rank " .. e.rank .. ")") or "")
    -- not in the group (a customer who left): [@name] only reaches group members, so target them,
    -- cast, and go back to whoever you had targeted
    if not at then return "/target " .. e.name .. "\n/cast " .. spell .. r .. "\n/targetlasttarget" end
    return "/cast [@" .. at .. "] " .. spell .. (e.rank and ("(Rank " .. e.rank .. ")") or "")
end
-- In range to cast on? The pop waits for it (the owner, 14 Nov 2026: "this guy asked for kings
-- before loading in fully can it be set to cast when they are in range"). If the game can't say,
-- yes.
function Jobs.BuffInRange(e)
    if not e then return false end
    local unit
    for _, m in ipairs(GroupSnapshot()) do
        if m.unit and not m.me and m.name:lower() == e.name:lower() then unit = m.unit break end
    end
    if not unit then return true end   -- outside the group: the cast targets them by name
    -- every answer can be a hidden ("secret") value; test nothing until it's known not to be one
    -- (the owner's screenshot, 14 Nov 2026: "attempt to perform boolean test on local 'checked'
    -- (a secret boolean value)")
    local function plain(ok, v) if not ok or IsSecret(v) then return nil end return v end
    local conn = UnitIsConnected and plain(pcall(UnitIsConnected, unit))
    if conn == false then return false end
    if UnitInRange then
        local ok, r, checked = pcall(UnitInRange, unit)
        r, checked = plain(ok, r), plain(ok, checked)
        if checked and r ~= nil then return r and true or false end
    end
    if UnitIsVisible then
        local v = plain(pcall(UnitIsVisible, unit))
        if v ~= nil then return v and true or false end
    end
    return true                        -- the game won't say: show it, and a miss is just a miss
end
-- Right-click on the pop: skip this one
function Jobs.SkipBuff()
    local e = table.remove(buffQueue, 1)
    if e then P("skipped " .. (e.spell or Core.BY_KEY[e.key].label) .. " for " .. e.name) end
    RefreshBuff()
end
local function BuffLabel()
    local e = buffQueue[1]
    if not e then return "No buffs waiting" end
    local def = Core.BY_KEY[e.key]
    local what = e.spell and e.spell:gsub("^Blessing of ", "") or def.label:gsub("^a ", "")
    return what .. " -> " .. e.name .. (#buffQueue > 1 and (" (+" .. (#buffQueue - 1) .. ")") or "") ..
        (Jobs.BuffInRange(e) and "" or "  (not in range yet)")
end
RefreshBuff = function()
    -- drop anyone who left the group
    for i = #buffQueue, 1, -1 do
        local e = buffQueue[i]
        if not InGroupByName(e.name) and not (e.outside or Jobs.Recent(e.name)) then table.remove(buffQueue, i) end
    end
    if InCombatLockdown and InCombatLockdown() then buffDirty = true return end
    buffDirty = false
    -- whoever is in range goes first; the rest wait their turn
    if buffQueue[1] and not Jobs.BuffInRange(buffQueue[1]) then
        for i = 2, #buffQueue do
            if Jobs.BuffInRange(buffQueue[i]) then table.insert(buffQueue, 1, table.remove(buffQueue, i)) break end
        end
    end
    local m = BuffMacro(buffQueue[1])
    buffKey:SetAttribute("macrotext", m)
    if jobsWin and jobsWin.buffBtn then
        jobsWin.buffBtn:SetAttribute("macrotext", m)
        jobsWin.buffBtn:SetText(BuffLabel())
        if #MyBuffs() > 0 then jobsWin.buffBtn:Show() else jobsWin.buffBtn:Hide() end
    end
    local e = buffQueue[1]
    if e and not Jobs.BuffInRange(e) then e = nil end   -- the pop waits until they're in range
    if Jobs.BuffPop then Jobs.BuffPop(e and BuffLabel() or nil, m, e and (e.spell or Core.Setting(ServiceInviterDB, e.key).spell)) end
end
-- Do you have this spell? (Kings is a talent.) If the game can't say, assume yes.
local function KnowSpell(spell)
    if not spell then return false end
    local get = (C_Spell and C_Spell.GetSpellInfo) or GetSpellInfo
    if not get then return true end
    local ok, info = pcall(get, spell)
    if not ok then return true end
    return info ~= nil
end
local function QueueBuff(name, key, spell)
    if not name or name == "" then return end
    for _, e in ipairs(buffQueue) do
        if e.name == name and e.key == key then
            -- a paladin's blessing replaces their last one on that person: switch, don't add
            if spell and e.spell ~= spell then e.spell, e.rank = spell, nil RefreshBuff() end
            return
        end
    end
    buffQueue[#buffQueue + 1] = { name = name, key = key, spell = spell }
    P("buff queued: " .. (spell or Core.BY_KEY[key].label) .. " for " .. name .. " (press the buff button)")
    RefreshBuff()
end
QueueAllMyBuffs = function(name)
    for _, def in ipairs(MyBuffs()) do
        -- a blessing names which one ("Might -> Kaldrok", not "blessing -> Kaldrok")
        QueueBuff(name, def.key, def.key == "blessing" and Core.Setting(ServiceInviterDB, "blessing").spell or nil)
    end
end
-- "fort pls" from someone in the group
-- every buff ask leaves a note for /si why NAME (the owner, 14 Nov 2026: "buff thing isnt firing
-- when they ask for it")
function Jobs.BuffNote(sender, text, why)
    local who = (Ambiguate and type(sender) == "string" and not IsSecret(sender) and Ambiguate(sender, "none")) or sender
    if type(who) ~= "string" or IsSecret(who) then return end
    Jobs.heard = Jobs.heard or {}
    Jobs.heard[who:lower()] = { text = (type(text) == "string" and not IsSecret(text)) and text or "(hidden by the game)",
        ch = "buff ask", t = GetTime(), why = why }
end
BuffAsk = function(text, sender)
    if not sender then return end
    if type(text) ~= "string" or IsSecret(text) then Jobs.BuffNote(sender, nil, "the game hid what they said, so it can't be read") return end
    local noted
    local function note(why) noted = true Jobs.BuffNote(sender, text, why) end
    local name = Ambiguate and Ambiguate(sender, "none") or sender
    if name == FullName("player") then return end
    local inGroup = InGroupByName(name)
    local outside = false
    if not inGroup then
        local recent = Jobs.Recent(name)
        if not recent then note("not in your group, and not a recent customer") return end
        name, outside = recent, true
    end
    if type(inGroup) == "string" then name = inGroup end
    local norm = Norm(text)
    -- asks are short ("wisdom pls", "can i get fort"); "i might be afk for a bit" is not one
    local count = 0
    for _ in norm:gmatch("%S+") do count = count + 1 end
    if count > 6 then note("more than 6 words, so not read as an ask") return end
    -- a paladin whose blessing is switched off: say so, once a session, instead of nothing
    local okc, _, cls = pcall(UnitClass, "player")
    if okc and cls == "PALADIN" and not Core.Setting(ServiceInviterDB, "blessing").on then
        if Core.BlessingFor(norm) then note("asked for a blessing, but 'We offer a blessing' is off (Buffs tab)") end
        if not Jobs.toldBlessingOff then
            local spell = Core.BlessingFor(norm)
            if spell then
                Jobs.toldBlessingOff = true
                P(name .. " asked for " .. spell .. ", but 'We offer a blessing' is off (Setup, Buffs tab).")
            end
        end
    end
    local mine = MyBuffs()
    if #mine == 0 then
        if not (cls == "PALADIN") then note("no buff of yours is ticked on the Buffs tab") end
        return
    end
    local queued
    for _, def in ipairs(mine) do
        local words = Core.SplitWords(Core.Setting(ServiceInviterDB, def.key).words)
        local named = def.key == "blessing" and Core.BlessingFor(norm)   -- "wis", "bok", "kings"
        if named or HasAny(norm, words) then
            if def.key == "blessing" then
                -- the word picks the blessing; the last one named wins ("wisdom... actually might")
                local spell = named or Core.Setting(ServiceInviterDB, "blessing").spell
                if KnowSpell(spell) then QueueBuff(name, def.key, spell) queued = spell
                else note("asked for " .. tostring(spell) .. ", which you don't have") P(name .. " asked for " .. spell .. ", which you don't have. Not queued.") end
            else
                QueueBuff(name, def.key) queued = def.label
            end
        end
    end
    if queued then note("queued " .. queued .. (outside and " (outside the group: targeted by name)" or ""))
    elseif not noted then note("no buff word of yours in it") end
end
BuffCastDone = function(spellName)
    local e = buffQueue[1]
    if not e or type(spellName) ~= "string" then return end
    if spellName == (e.spell or Core.Setting(ServiceInviterDB, e.key).spell) then table.remove(buffQueue, 1) RefreshBuff() end
end
-- "Target is too low level": step down a rank and let the next press try again
BuffTooLow = function()
    local e = buffQueue[1]
    if not e then return end
    if not e.rank then
        local spell = e.spell or Core.Setting(ServiceInviterDB, e.key).spell
        local ok, sub = pcall(function() return (GetSpellSubtext and GetSpellSubtext(spell)) or (C_Spell and C_Spell.GetSpellSubtext and C_Spell.GetSpellSubtext(spell)) end)
        local top = ok and type(sub) == "string" and tonumber(sub:match("(%d+)")) or nil
        e.rank = top and (top - 1) or 1
    else
        e.rank = e.rank - 1
    end
    if e.rank < 1 then
        P(e.name .. " is too low level for " .. Core.BY_KEY[e.key].label .. ". Skipped.")
        table.remove(buffQueue, 1)
    end
    RefreshBuff()
end

----------------------------------------------------------------------
-- Customer list window (/si jobs)
----------------------------------------------------------------------
local ROWS = 6
local CLEAN_AFTER = 30       -- finished rows disappear after this many seconds

-- (The 1.x extras list is now the services in Services.lua: see MigrateServices.)
MSG.OFFERMSG = "Welcome {name}! Also on offer today: {offers}. Just ask!"

-- What else is on offer where this customer landed (nil = nothing, say nothing).
MSG.PAY = "Welcome to {here}, {name}! Please pay {payee} {price}."
local function ArrivalText(job)
    if not job then return nil end
    local g = GroupSnapshot()
    local key = job.service or "summons"
    local p = Core.Provider(g, key, job.dest)
    local here = job.dest or (p and p.zone)
    local custom = ServiceInviterDB.offermsg
    if custom == MSG.OFFERMSG then custom = nil end
    -- landed and not yet paid: who to pay and how much, again (the owner's flow, 14 Nov 2026:
    -- "upon arrival they are whispered to pay the price again to payee and that they can request
    -- a blessing")
    local price = JobPrice(job)
    local pay
    if price and price > 0 and job.status ~= "paid" and job.status ~= "done" and Opt("payremind") then
        local payee, mine = PayeeFor(job, g)
        local m = ServiceInviterDB.paymsg
        if m == nil or m == "" then m = MSG.PAY end
        pay = m:gsub("{name}", function() return Jobs.Label(job) end):gsub("{payee}", function() return mine and "me" or Core.Label(g, payee) end)
            :gsub("{price}", function() return PriceText(price) end):gsub("{here}", function() return here and Core.Short(here) or "" end)
    end
    local offer = Core.ArrivalOffer(ServiceInviterDB, g, Faction(), here, key, Jobs.Label(job), custom or (pay and "Also here: {offers}. Just ask!"))
    if pay and offer then return pay .. " " .. offer end
    return pay or offer
end

-- The one thing to do next for a customer:
-- wait (not in group yet) | summon | arriving | offer | finish | none
local function NextStep(job)
    if not job then return "none" end
    if job.status == "asked" then return "invite" end
    if job.status == "invited" then return "wait" end
    local def = Core.BY_KEY[job.service or "summons"]
    if def and def.kind ~= "summon" then
        -- portals, lockpicking, water, stones, buffs: the provider does it where they stand
        if job.status == "joined" or job.status == "arrived" then return "serve" end
        return "none"
    end
    if job.status == "joined" then return "summon" end
    if job.status == "summoned" then return "arriving" end
    if job.status == "arrived" then
        if not job.offered and ArrivalText(job) then return "offer" end
        return "finish"
    end
    return "none"
end

local function OfferText(name) return ArrivalText(Jobs.Get(name)) or "" end

local function UnitFor(name)
    local function same(u)
        if not (UnitExists and UnitExists(u)) then return false end
        local n = GetUnitName and GetUnitName(u, true) or UnitName(u)
        if not n then return false end
        return (Ambiguate and Ambiguate(n, "none") or n) == name
    end
    for i = 1, 4 do if same("party" .. i) then return "party" .. i end end
    for i = 1, 40 do if same("raid" .. i) then return "raid" .. i end end
    return nil
end

local function CleanName(n) return (tostring(n):gsub("[%s%c%p]", function(c) return c == "-" and c or "" end)) end

local ACTIVE = { asked = true, invited = true, joined = true, summoned = true, arrived = true, busy = true }

-- Which customers to show: everyone still in progress (oldest first, so the queue is
-- fair), then recently finished ones for a moment.
local function VisibleJobs()
    local now = GetTime()
    local list, done = {}, {}
    for _, j in ipairs(jobs) do
        if ACTIVE[j.status] or (j.status == "left" and j.owes) then list[#list + 1] = j
        elseif j.tdone and now - j.tdone < CLEAN_AFTER then done[#done + 1] = j end
    end
    for _, j in ipairs(done) do list[#list + 1] = j end
    -- too many to show: the newest wait off-screen, never the one who has waited longest
    local hidden = 0
    while #list > ROWS do table.remove(list) hidden = hidden + 1 end
    return list, hidden
end

-- The first customer who needs something from you.
-- Can you summon this customer? Only as the warlock, and only one coming to where you stand.
local function YouSummon(j)
    if Role() ~= "lock" then return false end
    local def = Core.BY_KEY[(j and j.service) or "summons"]
    if not def or def.kind ~= "summon" then return false end
    local p = Core.Provider(GroupSnapshot(), "summons", j.dest)
    return p == nil or p.me == true
end
-- The first customer who needs something from YOU (the big button never offers a job
-- someone else does: a lockpick buyer is not yours to summon).
local function NextJob()
    for _, j in ipairs(jobs) do if NextStep(j) == "invite" then return j, "invite" end end
    for _, j in ipairs(jobs) do
        local st = NextStep(j)
        if st == "summon" and YouSummon(j) then return j, st end
        if st == "offer" then return j, st end
        if (st == "finish" or (st == "serve" and JobPrice(j))) and CollectsFor(j) then return j, "finish" end
    end
    return nil, "none"
end

----------------------------------------------------------------------
-- Helper mode: the lock starts Ritual of Summoning -> alert + raid line
----------------------------------------------------------------------
local alertWin
local lastCastAt = 0
local RITUAL_ID = 698
Jobs.RITUAL_ID = RITUAL_ID

----------------------------------------------------------------------
-- Customer list look (the design review of 12 Nov 2026): dark and gold, flat, one filled
-- button. Colors are the review's tokens; status pills always carry the word, never color alone.
----------------------------------------------------------------------
-- The 2026 look (DESIGN-SPEC.md in the design handoff): dark, flat, one gold accent.
local INK = {
    frame = "3a424d", deep = "0d0f12", ground = "14171b", panel = "1b1f25", plain = "232830",
    soft = "2b313a", line = "3a424d", text = "ece9e2", muted = "9ba3ae", faint = "7b8490",
    gold = "e9b949", goldInk = "1a1405", wash = "3a2f12", danger = "e5484d", bannerBg = "2a0e11",
    silver = "c0c7d0", warn = "ff9a5b",
}
INK.PILL = {   -- status -> fill, text, bar (twelve statuses; lightness differs, not only hue)
    asked = { "2e2711", "f0c45c", "e9b949" }, invited = { "2e2711", "f0c45c", "e9b949" },
    joined = { "12291e", "6fd29a", "3fb97a" }, summoned = { "13253b", "7db8ff", "4c9bff" },
    arrived = { "0e2b2c", "5fd6d0", "2dbdb6" }, paid = { "1d2420", "a9c7b4", "5f8a72" }, done = { "1d2420", "a9c7b4", "5f8a72" },
    busy = { "33200f", "ff9a5b", "f07a2e" }, declined = { "351416", "ff8b8b", "e5484d" },
    noanswer = { "22262d", "9ba3ae", "4a525e" }, left = { "22262d", "9ba3ae", "4a525e" },
    scammed = { "3d1114", "ff6b6b", "e5484d" },
}
local function RGB(hex)
    hex = tostring(hex):gsub("^ff", "", 1)
    if #hex ~= 6 then return 1, 1, 1 end
    return tonumber(hex:sub(1, 2), 16) / 255, tonumber(hex:sub(3, 4), 16) / 255, tonumber(hex:sub(5, 6), 16) / 255
end
local function Fill(parent, hex, layer, sub)
    local t = parent:CreateTexture(nil, layer or "BACKGROUND", nil, sub)
    t:SetColorTexture(RGB(hex))
    return t
end
local function Text(parent, size, hex, font)
    local fs = parent:CreateFontString(nil, "OVERLAY", font or "GameFontHighlight")
    pcall(function() local f, _, fl = fs:GetFont() if f then fs:SetFont(f, size, fl) end end)
    fs:SetTextColor(RGB(hex or INK.text))
    return fs
end
-- Flat buttons: gold (the one main action), ghost (a row's action), plain, bare (the x).
INK.LOOK = {
    gold = { INK.gold, INK.gold, INK.goldInk }, ghost = { INK.panel, INK.gold, INK.gold },
    plain = { INK.plain, INK.soft, INK.text }, bare = { nil, nil, INK.muted }, rail = { nil, nil, INK.text },
    hero = { nil, nil, INK.text },
    chip = { INK.panel, INK.soft, INK.muted }, danger = { "2a1214", "6b2328", "ff8b8b" },   -- a secure button drawn by the window behind it; its text stays hidden
}
local function FlatButton(parent, w, h, style, size, secure, name)
    local b = CreateFrame("Button", name, parent, secure and "SecureActionButtonTemplate" or nil)
    b:SetSize(w, h)
    local look = INK.LOOK[style]
    if look[2] then local edge = Fill(b, look[2], "BACKGROUND", -1) edge:SetAllPoints() end
    if look[1] then
        local bg = Fill(b, look[1], "BACKGROUND", 0)
        bg:SetPoint("TOPLEFT", 1, -1) bg:SetPoint("BOTTOMRIGHT", -1, 1)
    end
    local hl = b:CreateTexture(nil, "HIGHLIGHT") hl:SetAllPoints() hl:SetColorTexture(1, 1, 1, 0.08)
    local fs = Text(b, size or 14, look[3])
    fs:SetPoint("CENTER")
    b:SetFontString(fs)
    if style == "hero" then fs:Hide() end
    b._siStyle, b._siSize = style, size or 14
    return b
end
-- Spell icons from the game (nothing shipped): by id or name, else the fallback path.
Jobs.RITUAL_ICON = "Interface\\Icons\\Spell_Shadow_Twilight"
Jobs.BLESS_ICONS = { Might = "Interface\\Icons\\Spell_Holy_FistOfJustice", Wisdom = "Interface\\Icons\\Spell_Holy_SealOfWisdom",
    Kings = "Interface\\Icons\\Spell_Magic_MageArmor", Salvation = "Interface\\Icons\\Spell_Holy_SealOfSalvation" }
function Jobs.SpellIcon(spell, fallback)
    local ok, tex = pcall(function()
        return (C_Spell and C_Spell.GetSpellTexture and C_Spell.GetSpellTexture(spell)) or (GetSpellTexture and GetSpellTexture(spell))
    end)
    if ok and tex and not IsSecret(tex) then return tex end
    return fallback
end
function Jobs.BlessIcon(spell)
    local short = tostring(spell or "Might"):gsub("^Blessing of ", ""):gsub("^Greater ", "")
    return Jobs.SpellIcon(spell or "Blessing of Might", Jobs.BLESS_ICONS[short] or Jobs.BLESS_ICONS.Might)
end
-- A tooltip on hover, for buttons that are a word or an icon.
function Jobs.Tip(b, text)
    b:HookScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_BOTTOM") GameTooltip:SetText(text) GameTooltip:Show()
    end)
    b:HookScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
end
-- 1:25, the time since a status started
function Jobs.Clock(t)
    local s = math.max(0, math.floor(GetTime() - (t or GetTime())))
    return math.floor(s / 60) .. ":" .. ("%02d"):format(s % 60)
end
-- 18g 60s, with the letters in gold and silver
function Jobs.MoneyShort(silver)
    silver = math.floor(tonumber(silver) or 0)
    local g, s = math.floor(silver / 100), silver % 100
    local G, S = "|cff" .. INK.gold .. "g|r", "|cff" .. INK.silver .. "s|r"
    if g > 0 and s > 0 then return g .. G .. " " .. s .. S end
    if g > 0 then return g .. G end
    return s .. S
end
-- The buff pops up at your mouse (the owner, 14 Nov 2026: "can the blessing thing be more
-- obvious what if i miss it? can it just appear at my mouse"). A gold button by the cursor, with
-- a sound, when someone is waiting; click it to cast; gone when nobody is. Out of combat only
-- (RefreshBuff never runs in combat, when the game won't move a button that casts).
function Jobs.BuffPop(label, macro, spell)
    local b = Jobs.pop
    if not label or Opt("buffpop") == false then if b then b:Hide() end return end
    if not b then
        -- a big icon of the buff itself, its name and who it's for underneath (the owner, 14 Nov
        -- 2026: "can it kind of just pop up with a large icon of that blessing")
        b = CreateFrame("Button", "ServiceInviterBuffPop", UIParent, "SecureActionButtonTemplate")
        b:SetSize(224, 68)
        b:SetFrameStrata("DIALOG")
        b:RegisterForClicks("AnyUp", "AnyDown")
        b:SetAttribute("type", "macro")
        -- right-click: skip this one (no cast)
        b:SetAttribute("type2", "macro") b:SetAttribute("macrotext2", "")
        b:HookScript("PostClick", function(_, button) if button == "RightButton" then Jobs.SkipBuff() end end)
        -- the 2026 look: a 224 x 68 card with a gold edge, the spell's icon, its name, and who
        local edge = Fill(b, INK.gold, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -2, 2) edge:SetPoint("BOTTOMRIGHT", 2, -2)
        local back = Fill(b, INK.deep, "BACKGROUND", -7) back:SetAllPoints()
        b.icon = b:CreateTexture(nil, "ARTWORK")
        b.icon:SetPoint("TOPLEFT", 12, -12) b.icon:SetSize(44, 44)
        local hl = b:CreateTexture(nil, "HIGHLIGHT") hl:SetAllPoints() hl:SetColorTexture(1, 1, 1, 0.06)
        b.spell = Text(b, 15, INK.text, "GameFontNormalLarge")
        b.spell:SetPoint("TOPLEFT", 68, -14) b.spell:SetWidth(146) b.spell:SetJustifyH("LEFT")
        b.label = Text(b, 12, INK.muted)
        b.label:SetPoint("TOPLEFT", 68, -38) b.label:SetWidth(146) b.label:SetJustifyH("LEFT")
        if b.label.SetWordWrap then b.label:SetWordWrap(false) b.spell:SetWordWrap(false) end
        b:Hide()
        Jobs.pop = b
    end
    b:SetAttribute("macrotext", macro)
    -- "Blessing of Wisdom -> Yeet Lock (+1)": the spell big, who for under it
    local what, who = tostring(label):match("^(.-)%s*%->%s*(.*)$")
    b.spell:SetText(((what or label):gsub("^Blessing of ", "")))
    b.label:SetText(who or "")
    local tex
    if spell then
        local ok, t = pcall(function()
            return (C_Spell and C_Spell.GetSpellTexture and C_Spell.GetSpellTexture(spell)) or (GetSpellTexture and GetSpellTexture(spell))
        end)
        if ok then tex = t end
    end
    b.icon:SetTexture(tex or "Interface\\Icons\\INV_Misc_QuestionMark")
    if not b:IsShown() then
        local x, y = GetCursorPosition and GetCursorPosition()
        local scale = (UIParent.GetEffectiveScale and UIParent:GetEffectiveScale()) or 1
        b:ClearAllPoints()
        if x and y then b:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", x / scale + 24, y / scale + 24)
        else b:SetPoint("CENTER", UIParent, "CENTER", 0, -120) end
        b:Show()
        if PlaySound then pcall(PlaySound, (SOUNDKIT and SOUNDKIT.RAID_WARNING) or 8959) end
    end
end
-- New session asks for the shards (the owner, 13 Nov 2026: "when you click new session it can
-- ask for the number of shards if you are summoning"). Only when summons are on sale. The
-- number is the other warlocks'; yours come from your bags. Blank = don't count; Skip = leave it.
function Jobs.AskShards()
    if not Opt("countshards") or not Core.Setting(ServiceInviterDB, "summons").on then return end
    local w = Jobs.shardWin
    if not w then
        w = CreateFrame("Frame", "ServiceInviterShards", UIParent)
        -- the 2026 look: one line, one box, OK and Skip
        w:SetSize(420, 168)
        w:SetPoint("CENTER", 0, 120)
        w:SetFrameStrata("DIALOG")
        w:EnableMouse(true)
        local edge = Fill(w, INK.frame, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
        local bg = Fill(w, INK.ground, "BACKGROUND", -7) bg:SetAllPoints()
        local head = Fill(w, INK.deep, "BACKGROUND", -6) head:SetPoint("TOPLEFT", 0, 0) head:SetSize(420, 48)
        local t = Text(w, 15, INK.text, "GameFontNormalLarge") t:SetPoint("TOPLEFT", 18, -16) t:SetText("New session")
        local icon = w:CreateTexture(nil, "ARTWORK") icon:SetPoint("TOPLEFT", 18, -66) icon:SetSize(20, 20)
        icon:SetTexture(Jobs.SpellIcon(Jobs.RITUAL_ID, Jobs.RITUAL_ICON))
        local q = Text(w, 13, INK.text) q:SetPoint("TOPLEFT", 46, -69) q:SetText("Other warlocks' shards")
        w.sub = Text(w, 12, INK.muted) w.sub:SetPoint("TOPLEFT", 46, -88) w.sub:SetWidth(250) w.sub:SetJustifyH("LEFT")
        local box = CreateFrame("EditBox", "ServiceInviterShardsBox", w)
        box:SetPoint("TOPLEFT", 330, -62) box:SetSize(72, 30) box:SetAutoFocus(false) box:SetMaxLetters(4)
        box:SetFontObject(ChatFontNormal)
        if box.SetTextInsets then box:SetTextInsets(8, 8, 0, 0) end
        local e1 = box:CreateTexture(nil, "BACKGROUND", nil, -2) e1:SetAllPoints() e1:SetColorTexture(RGB(INK.soft))
        local e2 = box:CreateTexture(nil, "BACKGROUND", nil, -1) e2:SetPoint("TOPLEFT", 1, -1) e2:SetPoint("BOTTOMRIGHT", -1, 1) e2:SetColorTexture(RGB(INK.deep))
        box._siStyle = "input"
        if box.SetNumeric then box:SetNumeric(true) end
        local ok = FlatButton(w, 100, 32, "gold", 13) ok:SetPoint("BOTTOMLEFT", 18, 16) ok:SetText("OK")
        local skip = FlatButton(w, 100, 32, "plain", 13) skip:SetPoint("LEFT", ok, "RIGHT", 8, 0) skip:SetText("Skip")
        local function Done()
            local n = tonumber(box:GetText() or "")
            ServiceInviterDB.shards = n and math.max(0, math.floor(n)) or nil
            w:Hide()
            local have = Jobs.Shards()
            P(have and ("counting shards: " .. have .. " (" .. Jobs.ShardsLeft() .. " left after the queue)") or "not counting shards")
            RefreshJobs()
        end
        ok:SetScript("OnClick", Done)
        box:SetScript("OnEnterPressed", Done)
        box:SetScript("OnEscapePressed", function() w:Hide() end)
        skip:SetScript("OnClick", function() w:Hide() end)
        w.box, w.ok, w.skip = box, ok, skip
        Jobs.shardWin = w
    end
    local _, own = Jobs.Shards()
    w.sub:SetText(own and ("Yours: " .. own .. ", from your bags") or "Blank: only yours")
    w.box:SetText(ServiceInviterDB.shards and tostring(ServiceInviterDB.shards) or "")
    w:Show()
    w.box:SetFocus()
    if w.box.HighlightText then w.box:HighlightText() end
end
-- A window to copy from (the owner, 13 Nov 2026: "can it not print the customer lists and stuff
-- into a window that i can copy and paste from easily"). The text comes up selected: Ctrl+C.
-- The lists, as tabs across the top of the copy window (the design review, 14 Nov 2026: eight
-- list buttons became one "Open lists"). Each fills the window with the same lines /si prints.
Jobs.LISTS = {
    { "Stats", "stats" }, { "Regulars", "customers" }, { "All", "customers all" }, { "Didn't pay", "scammers" },
    { "Names", "scammers names" }, { "Prices", "prices" }, { "Team", "team" }, { "Heard", "status" },
}
function Jobs.Lists(which)
    local pick = Jobs.LISTS[1]
    for _, l in ipairs(Jobs.LISTS) do if which and (l[1]:lower() == which:lower() or l[2] == which) then pick = l end end
    Jobs.Copy(pick[1], function() SlashCmdList.SERVICEINVITER(pick[2]) end, true)
end
function Jobs.Copy(title, fill, tabs)
    -- a list asked for from inside another list's fill: its lines join that one
    if Jobs.capture then fill() return end
    Jobs.capture = {}
    local ok, err = pcall(fill)
    local lines = Jobs.capture
    Jobs.capture = nil
    if not ok then P("|cffff4040error|r " .. tostring(err)) return end
    for i, l in ipairs(lines) do lines[i] = l:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "") end
    local text = table.concat(lines, "\n")
    local w = Jobs.copyWin
    if not w then
        w = CreateFrame("Frame", "ServiceInviterCopy", UIParent)
        w:SetSize(720, 480)
        w:SetPoint("CENTER")
        w:SetFrameStrata("DIALOG")
        w:EnableMouse(true) w:SetMovable(true) w:RegisterForDrag("LeftButton")
        w:SetScript("OnDragStart", w.StartMoving) w:SetScript("OnDragStop", w.StopMovingOrSizing)
        local edge = Fill(w, INK.frame, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
        local bg = Fill(w, INK.ground, "BACKGROUND", -7) bg:SetAllPoints()
        local head = Fill(w, INK.deep, "BACKGROUND", -6) head:SetPoint("TOPLEFT", 0, 0) head:SetSize(720, 48)
        local headLine = Fill(w, INK.soft, "BORDER") headLine:SetPoint("TOPLEFT", 0, -48) headLine:SetSize(720, 1)
        w.title = Text(w, 15, INK.text, "GameFontNormalLarge")
        w.title:SetPoint("TOPLEFT", 16, -16)
        local x = FlatButton(w, 28, 28, "bare", 15) x:SetPoint("TOPRIGHT", -10, -10) x:SetText("x")
        x:SetScript("OnClick", function() w:Hide() end)
        -- the list tabs: shown when opened as Lists
        w.tabs = {}
        local tx = 12
        for i, l in ipairs(Jobs.LISTS) do
            local tw = 18 + #l[1] * 7
            local b = FlatButton(w, tw, 30, "rail", 12)
            b:SetPoint("TOPLEFT", tx, -54) b:SetText(l[1])
            b:GetFontString():ClearAllPoints() b:GetFontString():SetPoint("CENTER")
            b:SetScript("OnClick", function() Jobs.Lists(l[1]) end)
            local bar = Fill(w, INK.gold, "ARTWORK") bar:SetPoint("TOPLEFT", tx, -82) bar:SetSize(tw, 2)
            w.tabs[i] = { b, bar, l[1] }
            tx = tx + tw + 4
        end
        local well = Fill(w, INK.deep, "BACKGROUND", -5) well:SetPoint("TOPLEFT", 12, -90) well:SetSize(696, 336)
        w.well = well
        local sf = CreateFrame("ScrollFrame", "ServiceInviterCopyScroll", w, "UIPanelScrollFrameTemplate")
        sf:SetPoint("TOPLEFT", 20, -98) sf:SetPoint("BOTTOMRIGHT", -34, 58)
        w.sf = sf
        local box = CreateFrame("EditBox", nil, sf)
        box:SetMultiLine(true) box:SetAutoFocus(false) box:SetFontObject(ChatFontNormal)
        box:SetPoint("TOPLEFT") box:SetSize(650, 320)
        box:SetScript("OnEscapePressed", function() w:Hide() end)
        -- read-only: anything typed is put back
        box:SetScript("OnTextChanged", function(self, user) if user then self:SetText(w.text or "") self:HighlightText() end end)
        sf:SetScrollChild(box)
        w.box = box
        local hint = Text(w, 12, INK.muted)
        hint:SetPoint("TOPLEFT", 16, -446) hint:SetText("Selected: Ctrl+C copies, Esc closes")
        local all = FlatButton(w, 100, 30, "plain", 13) all:SetPoint("TOPRIGHT", -12, -438) all:SetText("Select all")
        all:SetScript("OnClick", function() w.box:SetFocus() w.box:HighlightText() end)
        if UISpecialFrames then table.insert(UISpecialFrames, "ServiceInviterCopy") end
        Jobs.copyWin = w
    end
    -- with tabs, the text sits under them; without, it starts under the title
    for _, t in ipairs(w.tabs) do
        local on = t[3] == title
        if tabs then t[1]:Show() else t[1]:Hide() end
        if tabs and on then t[2]:Show() else t[2]:Hide() end
        t[1]:GetFontString():SetTextColor(RGB(on and INK.gold or INK.muted))
    end
    w.title:SetText(tabs and "Lists" or title)
    w.well:ClearAllPoints() w.well:SetPoint("TOPLEFT", 12, tabs and -90 or -60) w.well:SetSize(696, tabs and 336 or 366)
    w.sf:ClearAllPoints() w.sf:SetPoint("TOPLEFT", 20, tabs and -98 or -68) w.sf:SetPoint("BOTTOMRIGHT", -34, 58)
    w.text = text
    w.box:SetText(text)
    w:Show()
    w.box:SetFocus()
    w.box:HighlightText()
end
-- The banner: a small label naming the event, the instruction as the loudest line, who is
-- being summoned, to where and who gets paid, and a bar for the 14 seconds it stays up.
-- Pulses for the first two seconds only (the design review of 12 Nov 2026).
local BANNER = { W = 560, SECS = 14 }
ShowAlert = function(title, sub, label)
    if not alertWin then
        local a = CreateFrame("Frame", "ServiceInviterAlert", UIParent)
        a:SetSize(BANNER.W, 100)
        a:SetPoint("TOP", 0, -150)
        a:SetFrameStrata("FULLSCREEN_DIALOG")
        local edge = Fill(a, INK.danger, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -2, 2) edge:SetPoint("BOTTOMRIGHT", 2, -2)
        local bg = Fill(a, INK.bannerBg, "BACKGROUND", -7) bg:SetAllPoints()
        local iconBg = Fill(a, INK.danger, "BORDER") iconBg:SetPoint("TOPLEFT", 20, -18) iconBg:SetSize(56, 56)
        local icon = a:CreateTexture(nil, "ARTWORK") icon:SetPoint("TOPLEFT", 24, -22) icon:SetSize(48, 48)
        icon:SetTexture(Jobs.SpellIcon(Jobs.RITUAL_ID, Jobs.RITUAL_ICON))
        a.label = Text(a, 11, "ffb3b5")
        a.label:SetPoint("TOPLEFT", 96, -16)
        a.testBg = Fill(a, "5a1a1f", "BORDER") a.testBg:SetSize(44, 16)
        a.test = Text(a, 10, "ffe0e0") a.test:SetText("TEST") a.test:SetWidth(44)
        a.title = Text(a, 32, "ffffff", "GameFontNormalLarge")
        pcall(function() local f = a.title:GetFont() if f then a.title:SetFont(f, 32, "OUTLINE") end end)
        a.title:SetPoint("TOPLEFT", 96, -32)
        a.sub = Text(a, 14, "f2d4d6", "GameFontHighlight")
        a.sub:SetPoint("TOPLEFT", 96, -72) a.sub:SetWidth(BANNER.W - 112) a.sub:SetJustifyH("LEFT")
        local track = Fill(a, "4a1a1f", "BORDER") track:SetPoint("BOTTOMLEFT", 0, 0) track:SetSize(BANNER.W, 5)
        a.bar = Fill(a, "ffffff", "ARTWORK") a.bar:SetPoint("BOTTOMLEFT", 0, 0) a.bar:SetSize(BANNER.W, 5)
        a.t = 0
        a:SetScript("OnUpdate", function(self, el)
            self.t = self.t + (el or 0)
            if self.t > BANNER.SECS then self:Hide() return end
            self.barWidth = math.max(1, BANNER.W * (1 - self.t / BANNER.SECS))
            self.bar:SetWidth(self.barWidth)
            self.alpha = (self.t < 2) and (0.7 + 0.3 * math.abs(math.sin(self.t * 5))) or 1
            self:SetAlpha(self.alpha)
        end)
        a:EnableMouse(true)
        a:SetScript("OnMouseDown", function(self) self:Hide() end)
        a:Hide()
        alertWin = a
    end
    -- in test mode (or a test from the setup) the label carries a TEST chip
    local test = ServiceInviterDB.dryrun or (label or ""):find("TEST", 1, true)
    label = (label or ""):gsub("^TEST%s*·%s*", ""):gsub("^TEST:%s*", "")
    alertWin.label:SetText(label)
    local lx = 96 + 14 + math.floor(#label * 7.5)
    alertWin.testBg:ClearAllPoints() alertWin.testBg:SetPoint("TOPLEFT", lx, -14)
    alertWin.test:ClearAllPoints() alertWin.test:SetPoint("TOPLEFT", lx, -17)
    if test then alertWin.testBg:Show() alertWin.test:Show() else alertWin.testBg:Hide() alertWin.test:Hide() end
    alertWin.title:SetText(title)
    alertWin.sub:SetText(sub or "")
    alertWin.t = 0
    alertWin.bar:SetWidth(BANNER.W)
    alertWin:Show()
    if PlaySound then
        pcall(PlaySound, (SOUNDKIT and SOUNDKIT.RAID_WARNING) or 8959)
    end
end
-- "Kaldrok  »  Thunder Bluff  ·  Pay Grimtotem"
local function BannerSub(who, job)
    local dest = job and job.dest
    local payee, mine = PayeeFor(job or { service = "summons" })
    local pay = (not JobPrice(job or { service = "summons" })) and "Free" or ("Pay " .. (mine and "you" or tostring(payee)))
    return who .. (dest and ("  »  " .. dest) or "") .. "  ·  " .. pay
end

local function WhisperText(who, nxt)
    local m = ServiceInviterDB.whispermsg
    if not m or m == "" then m = MSG.WHISPERMSG end
    m = m:gsub("{name}", function() return who end)
    return (m:gsub("{next}", function() return nxt or "nobody" end))
end

-- Whisper through Battle.net when the name is a Battle.net friend (works while chat-muted),
-- otherwise a normal whisper to a character name.
local function FindBNetFriend(name)
    if not name or not BNGetNumFriends then return nil end
    local want = name:lower():gsub("#%d+$", "")
    local n = select(1, BNGetNumFriends()) or 0
    for i = 1, n do
        local info = C_BattleNet and C_BattleNet.GetFriendAccountInfo and C_BattleNet.GetFriendAccountInfo(i)
        if info and info.bnetAccountID then
            local function m(v) return type(v) == "string" and v:lower():gsub("#%d+$", "") == want end
            local hit = m(info.accountName) or m(info.battleTag)
            local g = info.gameAccountInfo
            if not hit and g and m(g.characterName) then hit = true end
            if hit then return info.bnetAccountID end
        end
    end
end
local function SendWhisperTo(to, text)
    local id = FindBNetFriend(to)
    if id and BNSendWhisper then
        BNSendWhisper(id, text)
        return "Battle.net friend " .. to
    end
    Jobs.Send(text, "WHISPER", to)
    return "character " .. to
end

local function WhisperTo()
    local w = ServiceInviterDB.whisperto
    if not w or w == "" then return nil end
    return w
end

local function AlertMsg(name, job, here)
    local m = ServiceInviterDB.alertmsg
    if not m or m == "" then m = MSG.ALERTMSG end
    job = job or Jobs.Get(name)
    local payee, mine = PayeeFor(job or { service = "summons" })
    local price = JobPrice(job or { service = "summons" })
    -- where they're being summoned to (the owner, 13 Nov 2026: "can the 'summoning name' part
    -- say where we are summoning to? so they know"). A text of your own without {dest} gets
    -- it after the name, in capitals when the rest is.
    -- a customer the addon didn't invite has no place on record: then where the warlock
    -- casting the ritual is standing, which is where they land (the owner, 13 Nov 2026: "why is
    -- dest us and not where we are??"). Not known at all: no place, never a made-up one.
    local dest = (job and job.dest) or here
    if dest and not m:find("{dest}", 1, true) then
        local caps = m:gsub("{%a+}", "") == m:gsub("{%a+}", ""):upper()
        m = m:gsub("{name}", "{name}" .. (caps and " TO " or " to ") .. "{dest}", 1)
    end
    if dest and m:gsub("{%a+}", "") == m:gsub("{%a+}", ""):upper() then dest = dest:upper() end
    if not dest then m = m:gsub(" ?[Tt][Oo] {dest}", "") end
    m = m:gsub("{dest}", function() return dest or "" end)
    m = m:gsub("{name}", function() return Jobs.Label(job, name) end):gsub("{payee}", function() return mine and "ME" or Core.Label(GroupSnapshot(), payee) end)
    return (m:gsub("{price}", function() return PriceText(price) end))
end

-- Test mode (the owner, 14 Nov 2026: "before using this tomorrow i want a dry test to ensure it
-- would work - i want to see the output of their whisper to me or something as if it would go to
-- the customer just to me instead"). A buyer it would invite gets no invite; every message they
-- would get, start to finish, with their real name, city and quoted price, goes to you instead:
-- in your chat, or whispered to the character set with /si test NAME.
function Jobs.Rehearse(name, said, why, svc, dest, channel, quote, target, market)
    local db = ServiceInviterDB
    local job = { name = name, service = svc or "summons", dest = dest, t = GetTime() }
    job.price = quote or Core.Setting(db, job.service, dest).price
    local to = target
    if to == nil then to = db.testto end
    local function out(step, where, text)
        if not text or text == "" then return end
        if to and to ~= "" then
            -- exactly what the customer would get, nothing added; your chat says what it was
            SendChatMessage(text, "WHISPER", nil, to)
            P("|cffffd100TEST|r |cff999999" .. step .. " -> " .. name .. " (" .. where .. "): whispered to " .. to .. " instead|r")
        else
            P("|cffffd100TEST|r |cff999999" .. step .. " -> " .. name .. " (" .. where .. "):|r " .. Jobs.Icons(text))
        end
    end
    local chat = (IsInRaid and IsInRaid()) and "raid chat" or "party chat"
    local function where(kind) local r = Jobs.RouteOf(kind) return (r == "whisper" and "whisper") or (r == "off" and nil) or chat end
    local plainOut = out
    out = function(step, w, text) if w then plainOut(step, w, text) end end
    P("|cffffd100TEST|r would invite " .. name .. " because [" .. tostring(market or channel) .. "] \"" .. tostring(said) .. "\" = " .. tostring(why) ..
        " · quoted " .. (Core.Money(job.price) or "free") .. (to and to ~= "" and (" · messages whispered to " .. to) or ""))
    if Opt("welcome") and Jobs.RouteOf("welcome") == "whisper" then
        out("1 invited", "whisper", WelcomeText(name, job, true))
        local loyal = Jobs.LoyaltyLine(job)
        if loyal then out("1b joins (a regular)", where("loyal"), loyal) end
    elseif Opt("welcome") then out("1 welcome", where("welcome"), WelcomeText(name, job)) end
    if job.service == "summons" and db.raidalert ~= false then out("2 summon starts", where("alert"), AlertMsg(name, job, dest)) end
    out("3 lands", where("arrival"), ArrivalText(job))
    out("4 thanks", where("thanks"), ThanksText(name))
end


----------------------------------------------------------------------
-- The team (3.1). The owner, 14 Nov 2026: "i want to give it to 3-4 of us, maybe 5 ... we share
-- our info and the addons talk", with one point of contact who invites and whispers every
-- customer ("i told you i want a point of contact"). Copies talk over the group's addon channel,
-- and by addon whisper to teammates who are online but not grouped. No team = solo, as before.
--
-- Messages (fields split by tabs):
--   HI   version, warlock (1/0), zone, ask       "I'm here"; ask = "?" wants a HI back
--   BUY  to, buyer, service, city, quote, channel, market, test, testto, why, said
--   GOT  buyer, by                                the point of contact invited them
----------------------------------------------------------------------
Jobs.Team = { PREFIX = "SvcInv1", seen = {}, told = {}, took = {}, lastHi = 0 }
function Jobs.Me() return FullName("player") end
if C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix then pcall(C_ChatInfo.RegisterAddonMessagePrefix, Jobs.Team.PREFIX) end

function Jobs.TeamMembers()
    local t = ServiceInviterDB.team
    local out = {}
    if type(t) == "table" and type(t.members) == "table" then for k in pairs(t.members) do out[#out + 1] = k end end
    table.sort(out)
    return out
end
function Jobs.IsTeam(name)
    if type(name) ~= "string" or IsSecret(name) then return false end
    if Jobs.Guildmate(name) then return true end
    local t = ServiceInviterDB.team
    if type(t) ~= "table" or type(t.members) ~= "table" then return false end
    name = name:lower()
    for k in pairs(t.members) do if k:lower() == name then return true end end
    return false
end
function Jobs.TeamOn() return #Jobs.TeamMembers() > 0 or Jobs.GuildTeam() end
function Jobs.SetTeam(name, on)
    ServiceInviterDB.team = type(ServiceInviterDB.team) == "table" and ServiceInviterDB.team or {}
    local t = ServiceInviterDB.team
    t.members = type(t.members) == "table" and t.members or {}
    for k in pairs(t.members) do if k:lower() == name:lower() then t.members[k] = nil end end
    if on then t.members[name] = true end
end
-- A teammate's copy has said hello recently (they're online and running it).
function Jobs.Online(name)
    if not name then return false end
    if name:lower() == (FullName("player") or ""):lower() then return true end
    for k, v in pairs(Jobs.Team.seen) do
        if k:lower() == name:lower() and GetTime() - v.t < 150 then return true end
    end
    return false
end
-- The point of contact now: the first on the list who is online (you count). Nil = nobody set,
-- or none online: then each copy works solo.
function Jobs.POC()
    if not Jobs.TeamOn() then return nil end
    local list = type(ServiceInviterDB.team) == "table" and ServiceInviterDB.team.poc or nil
    if type(list) ~= "string" then return nil end
    for nm in list:gmatch("[^,]+") do
        nm = nm:gsub("^%s+", ""):gsub("%s+$", "")
        if nm ~= "" and Jobs.Online(nm) then
            if nm:lower() == (FullName("player") or ""):lower() then return FullName("player") end
            return nm
        end
    end
    return nil
end
-- Send to the team: over the group channel, and by addon whisper to teammates seen online who
-- aren't in the group (never to someone offline: the game answers that with an error line).
function Jobs.TeamSay(...) return Jobs.TeamSend(false, ...) end
-- quiet = the guild line and whispers only, not the raid (book sharing: the guild reaches them all)
function Jobs.TeamSend(quiet, ...)
    if not Jobs.TeamOn() then return end
    local parts = { ... }
    for i, v in ipairs(parts) do parts[i] = tostring(v or ""):gsub("\t", " ") end
    local msg = table.concat(parts, "\t")
    if #msg > 250 then msg = msg:sub(1, 250) end
    local send = (C_ChatInfo and C_ChatInfo.SendAddonMessage) or SendAddonMessage
    if not send then return end
    local went, ok = {}, true
    if Jobs.GuildTeam() then
        local okc, res = pcall(send, Jobs.Team.PREFIX, msg, "GUILD")
        if not okc or res == false or (type(res) == "number" and res ~= 0) then ok = false end
        went[#went + 1] = "guild"
    end
    if IsInGroup and IsInGroup() and not (quiet and Jobs.GuildTeam()) then
        local dist = (IsInRaid and IsInRaid()) and "RAID" or "PARTY"
        pcall(send, Jobs.Team.PREFIX, msg, dist)
        went[#went + 1] = dist:lower()
    end
    local skipped = {}
    for _, nm in ipairs(Jobs.TeamMembers()) do
        if nm:lower() ~= (FullName("player") or ""):lower() and not Jobs.InGroup(nm) and not Jobs.Guildmate(nm) then
            if Jobs.Online(nm) then
                pcall(send, Jobs.Team.PREFIX, msg, "WHISPER", nm)
                went[#went + 1] = nm
            else skipped[#skipped + 1] = nm end
        end
    end
    Jobs.TeamLog("sent", #went > 0 and table.concat(went, ", ") or "nobody", msg,
        (#went == 0 and "not grouped and no teammate seen online" or nil) or
        (#skipped > 0 and ("not sent to " .. table.concat(skipped, ", ") .. ": not seen online") or nil))
    return ok
end
-- The team's hidden messages, kept for /si teamlog (the last 200) and shown live with /si debug.
-- The owner, 14 Nov 2026, on the copies talking without a chat window: "for debugging though".
Jobs.teamLog = {}
function Jobs.TeamWords(msg)
    local f = {}
    for part in (tostring(msg) .. "\t"):gmatch("(.-)\t") do f[#f + 1] = part end
    local function M(q) return Core.Money(tonumber(q)) or "free" end
    if f[1] == "HI" then
        return (f[5] == "?" and "here, who else is? " or "here: ") .. "version " .. (f[2] or "?") .. ", " ..
            (f[3] == "1" and "warlock" or "not a warlock") .. ((f[4] or "") ~= "" and (", in " .. f[4]) or "")
    elseif f[1] == "BUY" then
        return (f[9] == "1" and "TEST " or "") .. "buyer " .. (f[3] or "?") .. " for " .. (f[2] or "?") .. ": " .. (f[4] or "?") ..
            ((f[5] or "") ~= "" and (" to " .. f[5]) or "") .. ", quoted " .. M(f[6]) .. ", heard in " ..
            (((f[8] or "") ~= "" and f[8]) or ((f[7] or "") ~= "" and f[7]) or "?") ..
            ((f[9] == "1" and (f[10] or "") ~= "") and (", test whispers to " .. f[10]) or "") ..
            ((f[12] or "") ~= "" and (' ("' .. f[12] .. '")') or "")
    elseif f[1] == "GOT" then
        return (f[3] or "?") .. " invited " .. (f[2] or "?")
    elseif f[1] == "WANT" then
        return "asking " .. (f[2] or "?") .. " for their book since change " .. (f[3] or "?")
    elseif f[1] == "C" then
        return "book, customer " .. (f[3] or "?") .. ": " .. (f[4] or "?") .. " times"
    elseif f[1] == "S" then
        return "book, didn't pay: " .. (f[3] or "?") .. (((f[7] or "") ~= "") and " (paid after all)" or "")
    elseif f[1] == "A" then
        return "book, stats (" .. (f[3] or "?") .. ")"
    elseif f[1] == "PRICE" then
        return "prices for " .. (f[2] or "?") .. ": max " .. ((f[3] or "") ~= "" and f[3] or "default") .. ", min " .. ((f[4] or "") ~= "" and f[4] or "none") ..
            ", " .. ((f[5] or "") ~= "" and f[5] or "ignore") .. ((f[6] or "") ~= "" and (" " .. f[6]) or "")
    elseif f[1] == "END" then
        return "book sent, up to change " .. (f[2] or "?")
    end
    return "unknown: " .. tostring(msg)
end
function Jobs.TeamLog(dir, who, msg, note)
    local okc, clock = pcall(function() return (date or os.date)("%H:%M:%S") end)
    local line = (okc and clock or "") .. "  " .. (dir == "sent" and ("sent to " .. who) or ("from " .. who)) .. ": " ..
        Jobs.TeamWords(msg) .. (note and (" -- " .. note) or "")
    local log = Jobs.teamLog
    log[#log + 1] = line
    if #log > 200 then table.remove(log, 1) end
    if debugOn then P("|cff999999team " .. line .. "|r") end
end
function Jobs.PrintTeamLog()
    if #Jobs.teamLog == 0 then
        P("No team messages since you logged in." .. (Jobs.TeamOn() and "" or " The team list is empty, so nothing is sent: /si team add NAME."))
        return
    end
    for _, l in ipairs(Jobs.teamLog) do P(l) end
end
function Jobs.SayHi(ask)
    local okv, ver = pcall(function() return ((C_AddOns and C_AddOns.GetAddOnMetadata) or GetAddOnMetadata)(ADDON_NAME, "Version") end)
    Jobs.Team.lastHi = GetTime()
    Jobs.bookTold = Jobs.BookRev()
    Jobs.TeamSay("HI", okv and ver or "?", Role() == "lock" and "1" or "0", ZoneOf("player") or "", ask and "?" or "", Jobs.BookRev())
    Jobs.SendPrices()
end
-- Hand a buyer and their quote to the point of contact (marked as a test when you're testing).
function Jobs.HandOff(poc, buyer, svc, dest, quote, channel, market, said, why)
    local db = ServiceInviterDB
    local test = db.dryrun and "1" or "0"
    Jobs.TeamSay("BUY", poc, buyer, svc or "summons", dest or "", quote or "", channel or "", market or "", test,
        db.dryrun and (db.testto or FullName("player") or "") or "", why or "", tostring(said or ""):sub(1, 60))
    P((db.dryrun and "|cffffd100TEST|r " or "") .. "handed " .. buyer .. " (" .. tostring(market or channel) .. ", quoted " ..
        (Core.Money(quote) or "free") .. ") to " .. poc)
end
function Jobs.TeamReceive(prefix, msg, dist, sender)
    if prefix ~= Jobs.Team.PREFIX or type(msg) ~= "string" or IsSecret(msg) or type(sender) ~= "string" then return end
    local who = Ambiguate and Ambiguate(sender, "none") or sender
    local me = FullName("player") or ""
    if who:lower() == me:lower() then return end
    -- the same message by the guild line and the raid: heard once
    Jobs.Team.heard = Jobs.Team.heard or {}
    local key = who .. "\n" .. msg
    if Jobs.Team.heard[key] and GetTime() - Jobs.Team.heard[key] < 5 then return end
    Jobs.Team.heard[key] = GetTime()
    if dist == "GUILD" then Jobs.Team.guild[who] = true end
    local note = Jobs.TeamHear(msg, who, me)
    Jobs.TeamLog("from", who .. (dist and (" (" .. tostring(dist):lower() .. ")") or ""), msg, note)
end
-- Act on a teammate's message. Returns why it was ignored, or what it did, for the team log.
function Jobs.TeamHear(msg, who, me)
    local f = {}
    for part in (msg .. "\t"):gmatch("(.-)\t") do f[#f + 1] = part end
    local kind = f[1]
    if kind == "HI" then
        Jobs.Team.seen[who] = { t = GetTime(), ver = f[2], lock = f[3] == "1", zone = f[4] }
        if not Jobs.IsTeam(who) then
            if not Jobs.Team.told[who] then
                Jobs.Team.told[who] = true
                P("|cffffd100" .. who .. " runs Service Inviter too.|r /si team add " .. who .. " to share with them.")
            end
            return "not on your team, so only noted"
        end
        local want = Jobs.CheckBook(who, tonumber(f[6]))
        if f[5] == "?" and GetTime() - Jobs.Team.lastHi > 3 then Jobs.SayHi(false) return "answered" .. (want and ("; " .. want) or "") end
        return want
    end
    if not Jobs.IsTeam(who) then return "ignored: not on your team" end   -- only teammates are listened to
    Jobs.Team.seen[who] = Jobs.Team.seen[who] or { t = GetTime() }
    Jobs.Team.seen[who].t = GetTime()
    if kind == "BUY" then
        local to, buyer, svc, dest, quote, channel, market = f[2], f[3], f[4], f[5], tonumber(f[6]), f[7], f[8]
        if not to or to:lower() ~= me:lower() then return "ignored: meant for " .. tostring(to) end
        if not buyer or buyer == "" then return "ignored: no buyer name" end
        local now = GetTime()
        -- two teammates heard the same buyer: one invite
        if Jobs.Get(buyer) then return "ignored: already on your list" end
        local wait = tonumber(ServiceInviterDB.cooldown) or 180
        if Jobs.Team.took[buyer] and now - Jobs.Team.took[buyer] < wait then return "ignored: already handed to you in the last " .. math.ceil(wait / 60) .. " min" end
        Jobs.Team.took[buyer] = now
        local test = (f[9] == "1" or ServiceInviterDB.dryrun) and { to = (f[9] == "1" and f[10] ~= "" and f[10]) or ServiceInviterDB.testto } or nil
        P((test and "|cffffd100TEST|r " or "") .. who .. " handed you " .. buyer .. " (" .. tostring(market ~= "" and market or channel) ..
            ", quoted " .. (Core.Money(quote) or "free") .. ")")
        Jobs.InviteBuyer(buyer, f[12] or "", f[11] or "", svc ~= "" and svc or "summons", dest ~= "" and dest or nil, quote,
            channel, market ~= "" and market or nil, nil, test)
        return "inviting" .. (test and " (test)" or "")
    end
    if kind == "GOT" then return nil end
    if kind == "PRICE" then return Jobs.HearPrices(f, who) end
    if Jobs.BookHear(kind, f, who, me) then return Jobs.bookNote end
    return "ignored: unknown message"
end

----------------------------------------------------------------------
-- The guild is the team, and the copies share their books (the owner, 14 Nov 2026: "how will it
-- save and share out customers?" -- "i think guild is good i like that").
-- Everyone in your guild running Service Inviter is on the team, on any character, with nothing to
-- add; the team list still adds people outside the guild. Each copy keeps its own book (customers,
-- didn't pay, stats) and sends it to the team; each copy keeps the others' books too, so you see
-- the whole team's customers even when the one who served them is offline. Only the owner of a
-- book ever changes it, so there is nothing to argue over: theirs replaces what you held.
-- Each change to a book counts up its number (bookrev). A copy says its number with every hello;
-- a teammate who holds less asks (WANT) for what changed since, and gets it a line at a time.
----------------------------------------------------------------------
Jobs.Team.guild = {}
function Jobs.GuildTeam() return (Opt("guildteam") and IsInGuild and IsInGuild()) and true or false end
function Jobs.Guildmate(name)
    if not Jobs.GuildTeam() or type(name) ~= "string" then return false end
    for k in pairs(Jobs.Team.guild) do if k:lower() == name:lower() then return true end end
    return false
end
-- Your guild's names, read from the roster (the game sends it on login and when it changes).
Jobs.guildNames = {}
function Jobs.ReadGuild()
    local names = {}
    local n = GetNumGuildMembers and GetNumGuildMembers() or 0
    for i = 1, (tonumber(n) or 0) do
        local nm = GetGuildRosterInfo(i)
        if type(nm) == "string" and not IsSecret(nm) then
            names[(Ambiguate and Ambiguate(nm, "none") or nm):lower()] = true
        end
    end
    Jobs.guildNames = names
end
function Jobs.InMyGuild(name)
    if not Opt("guildteam") or type(name) ~= "string" or IsSecret(name) or not (IsInGuild and IsInGuild()) then return false end
    if Jobs.guildNames[name:lower()] then return true end
    -- not on the roster yet: ask the game about them if they're in the group
    if UnitIsInMyGuild then
        local units = {}
        for i = 1, 4 do units[#units + 1] = "party" .. i end
        for i = 1, 40 do units[#units + 1] = "raid" .. i end
        for _, u in ipairs(units) do
            local nm = GetUnitName and GetUnitName(u, true)
            if type(nm) == "string" and not IsSecret(nm) and nm:lower() == name:lower() then
                local ok, yes = pcall(UnitIsInMyGuild, u)
                if ok and yes == true then return true end
            end
        end
    end
    return false
end
-- Whose customers you hold, for the Team tab and /si team.
function Jobs.BooksLine()
    local parts = {}
    for who, b in pairs(type(ServiceInviterDB.teambooks) == "table" and ServiceInviterDB.teambooks or {}) do
        local n = 0
        for _ in pairs(b.customers or {}) do n = n + 1 end
        parts[#parts + 1] = who .. " " .. n
    end
    table.sort(parts)
    local mine = 0
    for _ in pairs(type(ServiceInviterDB.customers) == "table" and ServiceInviterDB.customers or {}) do mine = mine + 1 end
    return "Customers: yours " .. mine .. (#parts > 0 and (", " .. table.concat(parts, ", ")) or ", nobody else's yet") ..
        ". Lists and stats count everyone's."
end
-- One price list for the team (the owner, 14 Nov 2026: "sure makes sense, they will have the
-- min/max price and then the individual workers would price dynamically price based on their
-- chats right"). The point of contact's max, min and how to meet a cheaper rival are the team's;
-- each copy still prices a buyer from the rivals it sees in its own channels, by those rules.
-- Sent with the point of contact's hello; used while they're online; yours again when they're not.
Jobs.PRICE_FIELDS = { "price", "floor", "mode", "undercut" }
function Jobs.SendPrices()
    if Jobs.POC() ~= Jobs.Me() then return end
    local db = ServiceInviterDB
    for _, def in ipairs(Core.SERVICES) do
        local saved = (type(db.services) == "table" and db.services[def.key]) or {}
        local function enc(v) if v == false then return "free" end return v == nil and "" or tostring(v) end
        Jobs.TeamSay("PRICE", def.key, enc(saved.price), enc(saved.floor), enc(saved.mode or (saved.match and "undercut") or nil), enc(saved.undercut))
    end
end
function Jobs.HearPrices(f, who)
    if (Jobs.POC() or ""):lower() ~= who:lower() then return "ignored: prices only come from the point of contact" end
    local key = f[2]
    if not key or not Core.BY_KEY[key] then return "ignored: unknown service" end
    local function dec(v) if v == "free" then return false end if v == nil or v == "" then return nil end return tonumber(v) or v end
    Jobs.Team.prices = Jobs.Team.prices or {}
    if (Jobs.Team.prices.from or ""):lower() ~= who:lower() then Jobs.Team.prices = { from = who } end
    Jobs.Team.prices[key] = { price = dec(f[3]), floor = dec(f[4]), mode = dec(f[5]), undercut = dec(f[6]) }
    return "using their prices for " .. key
end
-- The point of contact's prices for a service, while they're the point of contact and it isn't you.
function Jobs.TeamPrices(key)
    local t = Jobs.Team and Jobs.Team.prices
    if not t or not t[key] then return nil end
    local poc = Jobs.POC()
    if not poc or poc == Jobs.Me() or poc:lower() ~= (t.from or ""):lower() then return nil end
    return t[key], t.from
end
Core.PriceOverride = function(db, key)
    if db ~= ServiceInviterDB then return nil end
    return (Jobs.TeamPrices(key))
end
-- A chat tab of its own for the addon's lines (the owner, 14 Nov 2026: "i still want to be able
-- to put the SI stuff in a separate chat window i can customize"). A tab named SI is used by
-- itself (OutFrame); this makes one with nothing else in it.
function Jobs.MakeTab()
    if InCombatLockdown and InCombatLockdown() then P("can't make a chat tab in combat") return end
    if GetChatWindowInfo then
        for i = 1, (NUM_CHAT_WINDOWS or 10) do
            local name = GetChatWindowInfo(i)
            if type(name) == "string" and name:lower() == "si" then
                ServiceInviterDB.outframe = nil
                P("your SI chat tab is already there (window " .. i .. ")")
                return
            end
        end
    end
    if not FCF_OpenNewWindow then P("this client can't make chat tabs; make one named SI yourself and my lines go there") return end
    local ok, f = pcall(FCF_OpenNewWindow, "SI")
    if not ok or not f then P("couldn't make the tab: " .. tostring(f)) return end
    if ChatFrame_RemoveAllMessageGroups then pcall(ChatFrame_RemoveAllMessageGroups, f) end
    if ChatFrame_RemoveAllChannels then pcall(ChatFrame_RemoveAllChannels, f) end
    ServiceInviterDB.outframe = nil
    P("made an SI chat tab: my lines go there now. Right-click the tab to move it, or change its font and colors.")
end
-- Everyone on the team: the list, and guildmates heard from.
function Jobs.TeamPeople()
    local seen, out = {}, {}
    for _, nm in ipairs(Jobs.TeamMembers()) do seen[nm:lower()] = true out[#out + 1] = nm end
    if Jobs.GuildTeam() then
        for nm in pairs(Jobs.Team.guild) do if not seen[nm:lower()] then seen[nm:lower()] = true out[#out + 1] = nm end end
    end
    table.sort(out)
    return out
end
-- Your book's number. The first time, every record already there gets one.
function Jobs.BookRev()
    local db = ServiceInviterDB
    if tonumber(db.bookrev) then return db.bookrev end
    local r, list = 0, {}
    for name, c in pairs(type(db.customers) == "table" and db.customers or {}) do list[#list + 1] = { name, c } end
    table.sort(list, function(a, b) return (a[2].last or 0) < (b[2].last or 0) end)
    for _, e in ipairs(list) do r = r + 1 e[2].rev = r end
    for _, e in pairs(type(db.scammers) == "table" and db.scammers or {}) do r = r + 1 e.rev = r end
    if type(db.analytics) == "table" then r = r + 1 db.analytics.rev = r end
    db.bookrev = r
    return r
end
function Jobs.Bump()
    ServiceInviterDB.bookrev = Jobs.BookRev() + 1
    return ServiceInviterDB.bookrev
end
-- A teammate's book, as you hold it.
function Jobs.TeamBook(who)
    local db = ServiceInviterDB
    db.teambooks = type(db.teambooks) == "table" and db.teambooks or {}
    for k, b in pairs(db.teambooks) do if k:lower() == who:lower() then return b end end
    local b = { rev = 0, customers = {}, scammers = {}, an = {} }
    db.teambooks[who] = b
    return b
end
-- Their hello says how far their book has got; ask for the rest.
function Jobs.CheckBook(who, rev)
    if not rev then return nil end
    local b = Jobs.TeamBook(who)
    if rev < (b.rev or 0) then   -- they started a fresh book: take it again from the start
        b.rev, b.customers, b.scammers, b.an = 0, {}, {}, {}
    end
    if rev <= (b.rev or 0) then return nil end
    Jobs.Team.asked = Jobs.Team.asked or {}
    local was = Jobs.Team.asked[who]
    if was and was.rev >= rev and GetTime() - was.t < 20 then return "their book: already asked" end
    Jobs.Team.asked[who] = { t = GetTime(), rev = rev }
    Jobs.TeamSend(true, "WANT", who, b.rev or 0)
    return "asked for their book since change " .. (b.rev or 0) .. " (they're at " .. rev .. ")"
end
local function Pairs(t)
    local out = {}
    for k, v in pairs(type(t) == "table" and t or {}) do out[#out + 1] = tostring(k):gsub("[,=]", " ") .. "=" .. tostring(v) end
    table.sort(out)
    return table.concat(out, ",")
end
local function Unpairs(s, numkeys)
    local t = {}
    for k, v in tostring(s or ""):gmatch("([^,=]+)=([^,]*)") do
        if numkeys and tonumber(k) then k = tonumber(k) end
        t[k] = tonumber(v) or 0
    end
    return t
end
-- What changed in your book since `since`, a line each, oldest first, then END.
function Jobs.BookLines(since)
    local db, out = ServiceInviterDB, {}
    local rev = Jobs.BookRev()
    for name, c in pairs(type(db.customers) == "table" and db.customers or {}) do
        if (c.rev or 0) > since then
            out[#out + 1] = { c.rev, { "C", c.rev, name, c.n or 0, c.worth or 0, c.first or 0, c.last or 0, Pairs(c.by), Pairs(c.to) } }
        end
    end
    for name, e in pairs(type(db.scammers) == "table" and db.scammers or {}) do
        if (e.rev or 0) > since then
            out[#out + 1] = { e.rev, { "S", e.rev, name, e.n or 0, e.owed or 0, e.last or 0, e.cleared or "" } }
        end
    end
    local a = db.analytics
    if type(a) == "table" and (a.rev or 0) > since then
        local nm = type(a.near) == "table" and a.near or { n = 0, worth = 0 }
        local r = a.rev
        out[#out + 1] = { r, { "A", r, "base", (a.n or 0) .. "|" .. (a.worth or 0) .. "|" .. (a.since or 0) .. "|" .. (nm.n or 0) .. "|" .. (nm.worth or 0) } }
        for _, part in ipairs({ "to", "by", "hour", "day" }) do out[#out + 1] = { r, { "A", r, part, Pairs(a[part]) } } end
        out[#out + 1] = { r, { "A", r, "nwhy", Pairs(nm.why) } }
        out[#out + 1] = { r, { "A", r, "nto", Pairs(nm.to) } }
    end
    table.sort(out, function(x, y) return x[1] < y[1] end)
    local lines = {}
    for _, e in ipairs(out) do lines[#lines + 1] = e[2] end
    lines[#lines + 1] = { "END", rev }
    return lines
end
-- Lines go out a few a second: the game drops addon messages sent faster than that.
Jobs.outbox = {}
Jobs.OUT_EVERY = 0.25
function Jobs.Drain()
    local item = Jobs.outbox[1]
    if not item then return end
    if Jobs.TeamSend(true, unpack(item)) == false then
        Jobs.outWait = GetTime() + 2   -- the game said slow down
        return
    end
    table.remove(Jobs.outbox, 1)
end
-- A teammate's book line, or their WANT. True when it was one of these.
function Jobs.BookHear(kind, f, who, me)
    Jobs.bookNote = nil
    if kind == "WANT" then
        if not f[2] or f[2]:lower() ~= me:lower() then Jobs.bookNote = "ignored: meant for " .. tostring(f[2]) return true end
        local since = tonumber(f[3]) or 0
        if Jobs.wantSince == nil or since < Jobs.wantSince then Jobs.wantSince = since end
        Jobs.wantAt = Jobs.wantAt or GetTime()   -- answered in 2s, once for everyone who asked
        Jobs.bookNote = "sending my book since change " .. since
        return true
    end
    if kind ~= "C" and kind ~= "S" and kind ~= "A" and kind ~= "END" then return false end
    local b = Jobs.TeamBook(who)
    if kind == "END" then
        local r = tonumber(f[2]) or 0
        if r > (b.rev or 0) then b.rev = r end
        Jobs.bookNote = "their book is up to date (change " .. r .. ")"
        if Jobs.team_refresh then Jobs.team_refresh() end
        return true
    end
    if tonumber(f[2]) and tonumber(f[2]) <= (b.rev or 0) then Jobs.bookNote = "already have it" return true end
    if kind == "C" then
        b.customers[f[3]] = { n = tonumber(f[4]) or 0, worth = tonumber(f[5]) or 0, first = tonumber(f[6]), last = tonumber(f[7]),
            by = Unpairs(f[8]), to = Unpairs(f[9]) }
        Jobs.bookNote = "saved their customer " .. f[3]
    elseif kind == "S" then
        b.scammers[f[3]] = { n = tonumber(f[4]) or 0, owed = tonumber(f[5]) or 0, last = tonumber(f[6]), cleared = tonumber(f[7]) }
        Jobs.bookNote = "saved their didn't-pay entry " .. f[3]
        -- marked by a teammate while on your list too: the row says so (the owner, 14 Nov 2026:
        -- "either of us can mark someone as a scammer - like the queue knows")
        local j = Jobs.Get(f[3])
        if j and j.status ~= "scammed" and Jobs.Scammer(f[3]) then
            Jobs.Set(j.name, "scammed")
            P("|cffff8080" .. who .. " marked " .. j.name .. " as not paying.|r")
        end
    else
        local part = f[3]
        if part == "base" then
            local n, worth, since, nn, nw = tostring(f[4] or ""):match("^(%-?[%d.]*)|(%-?[%d.]*)|(%-?[%d.]*)|(%-?[%d.]*)|(%-?[%d.]*)$")
            b.an.n, b.an.worth, b.an.since = tonumber(n) or 0, tonumber(worth) or 0, tonumber(since)
            b.an.near = b.an.near or {}
            b.an.near.n, b.an.near.worth = tonumber(nn) or 0, tonumber(nw) or 0
        elseif part == "nwhy" or part == "nto" then
            b.an.near = b.an.near or {}
            b.an.near[part == "nwhy" and "why" or "to"] = Unpairs(f[4])
        elseif part == "to" or part == "by" or part == "hour" or part == "day" then
            b.an[part] = Unpairs(f[4], part == "hour" or part == "day")
        end
        Jobs.bookNote = "saved their stats (" .. tostring(part) .. ")"
    end
    return true
end
-- Every 1s: answer WANTs, and say when your book moved so teammates come and get it.
function Jobs.BookTick()
    if Jobs.wantAt and GetTime() - Jobs.wantAt >= 2 then
        for _, l in ipairs(Jobs.BookLines(Jobs.wantSince or 0)) do Jobs.outbox[#Jobs.outbox + 1] = l end
        Jobs.wantAt, Jobs.wantSince = nil, nil
    end
    if Jobs.TeamOn() and Jobs.bookTold and Jobs.BookRev() > Jobs.bookTold and GetTime() - Jobs.Team.lastHi > 10 then
        Jobs.SayHi(false)
    end
end
-- The whole team's customers: yours plus every teammate's book, added up per person.
function Jobs.Book()
    local db, out, keyOf = ServiceInviterDB, {}, {}
    local function add(name, c)
        local k = name:lower()
        local m = keyOf[k]
        if not m then m = { n = 0, worth = 0, by = {}, to = {} } keyOf[k] = m out[name] = m end
        m.n = m.n + (c.n or 0)
        m.worth = m.worth + (c.worth or 0)
        if c.first and c.first > 0 and (not m.first or c.first < m.first) then m.first = c.first end
        if c.last and (not m.last or c.last > m.last) then m.last = c.last end
        for x, v in pairs(c.by or {}) do m.by[x] = (m.by[x] or 0) + v end
        for x, v in pairs(c.to or {}) do m.to[x] = (m.to[x] or 0) + v end
    end
    for name, c in pairs(type(db.customers) == "table" and db.customers or {}) do add(name, c) end
    for _, b in pairs(type(db.teambooks) == "table" and db.teambooks or {}) do
        for name, c in pairs(b.customers or {}) do add(name, c) end
    end
    return out
end
-- The whole team's stats.
function Jobs.Analytics()
    local db = ServiceInviterDB
    local mine = type(db.analytics) == "table" and db.analytics or nil
    local books = {}
    if mine then books[#books + 1] = mine end
    for _, b in pairs(type(db.teambooks) == "table" and db.teambooks or {}) do if b.an and b.an.n then books[#books + 1] = b.an end end
    if #books == 0 then return nil end
    local a = { n = 0, worth = 0, to = {}, by = {}, hour = {}, day = {}, near = { n = 0, worth = 0, why = {}, to = {} } }
    local function sum(dst, src) for k, v in pairs(src or {}) do dst[k] = (dst[k] or 0) + v end end
    for _, x in ipairs(books) do
        a.n, a.worth = a.n + (x.n or 0), a.worth + (x.worth or 0)
        if x.since and x.since > 0 and (not a.since or x.since < a.since) then a.since = x.since end
        for _, part in ipairs({ "to", "by", "hour", "day" }) do sum(a[part], x[part]) end
        if type(x.near) == "table" then
            a.near.n, a.near.worth = a.near.n + (x.near.n or 0), a.near.worth + (x.near.worth or 0)
            sum(a.near.why, x.near.why) sum(a.near.to, x.near.to)
        end
    end
    return a
end

----------------------------------------------------------------------
-- Preview: what each tab's messages will look like, printed in your own chat window only.
-- The owner, 12 Nov 2026: "i should be able to press debug buttons in each panel for things
-- like seeing what the message should look like". It runs the same code that sends the real
-- messages, for a pretend buyer (Kaldrok); it sends nothing, invites nobody, queues nothing.
-- When nobody in the group can do a service, it says so and shows an example with a
-- stand-in of the right class standing with you.
----------------------------------------------------------------------
local PV = {}
PV.TABS = { "General", "Warlock", "Paladin", "Advertise", "Team", "Tools" }
PV.KEYS = { Warlock = { "summons" }, Paladin = { "blessing" } }
PV.BUYER = "Kaldrok"
PV.CLASS_WORD = { WARLOCK = "Warlock", MAGE = "Mage", ROGUE = "Rogue", PRIEST = "Priest", DRUID = "Druid", PALADIN = "Paladin" }

-- What's on sale, as the setup's General tab shows it.
local function OnSaleText(items)
    local parts = {}
    for _, it in ipairs(items) do
        local what = it.def.label
        if it.def.kind == "summon" then what = it.where and ("summons to " .. Core.Short(it.where)) or "summons (where? not invited)" end
        if it.def.kind == "portal" then
            local c = {}
            for _, city in ipairs(it.cities) do c[#c + 1] = Core.Short(city) end
            what = "portals to " .. table.concat(c, "/")
        end
        parts[#parts + 1] = what .. " (" .. MemberName(it.provider) .. ")"
    end
    return #parts > 0 and table.concat(parts, ", ") or nil
end

-- The group plus a level 60 stand-in, in your zone, for each service nobody can do.
local function WithStandIns(g, keys)
    local out, added = {}, {}
    for _, m in ipairs(g) do out[#out + 1] = m end
    local here
    for _, m in ipairs(g) do if m.me then here = m.zone end end
    here = here or ((Faction() == "Alliance") and "Stormwind City" or "Orgrimmar")
    for _, key in ipairs(keys) do
        local def = Core.BY_KEY[key]
        if not Core.Provider(out, key) then
            local m = { name = PV.CLASS_WORD[def.class] or def.class, class = def.class, level = 60, zone = here, standIn = true }
            out[#out + 1] = m
            added[#added + 1] = m
        end
    end
    return out, added, here
end

local function Preview(tab)
    local out = {}
    local function Head(t) out[#out + 1] = "|cffffd100" .. t .. "|r" end
    local function Say(where, text) out[#out + 1] = "|cff999999" .. where .. ":|r " .. tostring(text) end
    local function Note(t) out[#out + 1] = "|cffbbbbbb" .. t .. "|r" end
    local db, fac = ServiceInviterDB, Faction()
    local chat = (IsInRaid and IsInRaid()) and "raid chat" or "party chat"

    local function ShowJob(job, full)
        local st, def = Core.Setting(db, job.service), Core.BY_KEY[job.service]
        if full then
            if not st.invite then Note(def.label .. ": buyers aren't invited (Invite buyers is off), so there's no invite or welcome; it's only offered when someone lands.")
            elseif Opt("announce") then Say("When you invite, your chat only", "invited " .. PV.BUYER .. "  " .. JobWhere(job)) end
        end
        if not st.invite then
            -- nobody joins for it, so nothing to welcome
        elseif Opt("welcome") then
            Say("When they join, " .. chat, WelcomeText(PV.BUYER, job) or "(nothing to say)")
            -- and as a regular hears it (the owner, 13 Nov 2026: "HOW CAN I TEST IT")
            local regular = {}
            for k, v in pairs(job) do regular[k] = v end
            regular.previewBefore = 3
            if Jobs.LoyaltyLine(regular) then
                Say("When a regular joins (4th visit), " .. chat, WelcomeText(PV.BUYER, regular) or "(nothing to say)")
            end
        elseif full then Note("No welcome (Welcome them when they join is off, General tab).") end
        if not full then return end
        if def.kind == "summon" then
            if db.raidalert ~= false then Say("When the summon starts, " .. chat, AlertMsg(PV.BUYER, job)) end
            local to = WhisperTo()
            if to then Say("When the summon starts, whisper to " .. to, WhisperText(PV.BUYER, nil)) end
        end
        local a = ArrivalText(job)
        local p = Core.Provider(GroupSnapshot(), job.service, job.dest)
        local here = (def.kind == "summon" and job.dest) or (p and p.zone)
        if a then Say("When they land, " .. chat, a)
        else Note("When they land: no message (nothing else on offer in " .. Core.Short(here or "?") .. ")") end
        local payee, mine = PayeeFor(job)
        if not st.price then Note("Free, so nobody collects.") return end
        Note("Paid to: " .. (mine and "you" or tostring(payee)) ..
            ((mine and AutoTradeOn()) and ". Trade opens by itself when they're in range." or ". Trade won't open by itself."))
    end

    local function ServicePreview(key)
        local def, st = Core.BY_KEY[key], Core.Setting(db, key)
        Head(def.label)
        if not st.on then
            Note(def.label .. ": not offered. Tick '" .. (def.kind == "buff" and "We offer " or "We sell ") .. def.label .. "' to " .. (def.kind == "buff" and "offer" or "sell") .. " it.")
            return
        end
        local g = GroupSnapshot()
        if #Core.Providers(g, key) == 0 then
            local _, added, here = WithStandIns(g, { key })
            local why = "it takes a level " .. def.level .. "+ " .. (PV.CLASS_WORD[def.class] or def.class):lower()
            for _, m in ipairs(g) do
                if m.me and def.kind == "summon" and m.class == def.class and m.notSummoner then why = why .. "; you're set as the helper, not the warlock" end
            end
            Note("Nobody in your group can do " .. def.label .. " right now (" .. why .. "). This example pretends a level 60 " ..
                added[1].name:lower() .. " is with you in " .. Core.Short(here) .. ".")
            g = WithStandIns(g, { key })
        end
        previewGroup = g
        local items = {}
        for _, it in ipairs(Core.OnSale(db, g, fac)) do if it.key == key then items[#items + 1] = it end end
        if #items == 0 then
            if def.kind == "portal" then Note("No portal to offer: every city is unticked, or the mage is standing in the only city they can port to.")
            else Note("Can't sell it: the game doesn't say where they are.") end
        end
        for _, it in ipairs(items) do
            if def.kind == "summon" and not it.where then
                Note("Nobody is invited for " .. it.provider.name .. "'s summons: the game doesn't say where they are.")
            elseif def.kind == "portal" then
                for i, city in ipairs(it.cities) do ShowJob({ name = PV.BUYER, service = key, dest = city }, i == 1) end
            else
                ShowJob({ name = PV.BUYER, service = key, dest = def.kind == "summon" and it.where or nil }, true)
            end
        end
        previewGroup = nil
    end

    local ok, err = pcall(function()
        if db.stasis then Note("Stopped (/si stop): nothing real goes out until /si start. This is what it would say.") end
        if tab == "General" then
            Head("On sale")
            local items = Core.OnSale(db, GroupSnapshot(), fac)
            local text = OnSaleText(items)
            if not text then
                Note("Nothing on sale right now, so nobody is invited. Tick a service on a class tab, and have someone in the group who can do it.")
                -- still show your welcome and the regulars line (the owner's screenshot, 13 Nov
                -- 2026: Preview on General, alone, showed only "Nothing on sale" again and again)
                local g, added, here = WithStandIns(GroupSnapshot(), { "summons" })
                do
                    Head("Welcome when they join")
                    if added[1] then Note("This example pretends a level 60 warlock is with you in " .. Core.Short(here) .. ".") end
                    previewGroup = g
                    ShowJob({ name = PV.BUYER, service = "summons", dest = here }, false)
                    previewGroup = nil
                    if not Opt("welcome") then Note("No welcome (Welcome them when they join is off).") end
                end
            else
                Say("On sale now", text)
                if not Opt("enabled") then Note("Inviting is off (Invite buyers of what we sell).") end
                Head("Welcome when they join, for each")
                for _, it in ipairs(items) do
                    if it.def.kind == "portal" then
                        for _, city in ipairs(it.cities) do ShowJob({ name = PV.BUYER, service = it.key, dest = city }, false) end
                    elseif it.where or it.def.kind ~= "summon" then
                        ShowJob({ name = PV.BUYER, service = it.key, dest = it.def.kind == "summon" and it.where or nil }, false)
                    end
                end
                if not Opt("welcome") then Note("No welcome (Welcome them when they join is off).") end
            end
            -- the call-out too (the owner, 14 Nov 2026: "why does the preview not show the scammer message")
            Head("Someone who didn't pay joins")
            local line = Jobs.ScamLine(PV.BUYER)
            local r = Jobs.RouteOf("scam")
            if not line then Note("Nothing is said (the Didn't pay box is empty).")
            elseif r == "off" then Note("Nothing is said (the call-out is Off on the Team tab).")
            else Say(r == "whisper" and "Whispered to them" or "Raid warning if you're leader or assist, else raid / party chat", Jobs.Icons(line)) end
        elseif tab == "Tools" then
            Head("Tools")
            Note("Buttons for every command: start and stop, test mode, look someone up, the lists, and the checks.")
        elseif tab == "Team" then
            Head("Team")
            local list = Jobs.TeamMembers()
            if #list == 0 then Note("No team: you work solo, as before.") else
                local parts = {}
                for _, nm in ipairs(list) do parts[#parts + 1] = nm .. (Jobs.Online(nm) and " (online)" or " (not seen)") end
                Say("Team", table.concat(parts, ", "))
                local poc = Jobs.POC()
                if not poc then Note("No point of contact online: each copy invites and talks for itself.")
                elseif poc == Jobs.Me() then Note("You're the point of contact: you invite and whisper every customer the team finds.")
                else Note("Your buyers go to " .. poc .. ", who invites and whispers them. You never message a stranger.") end
            end
            Head("Where each message goes")
            for _, kind in ipairs(Jobs.ROUTE_KINDS) do
                local r = Jobs.RouteOf(kind)
                Say(Jobs.ROUTE_LABEL[kind], (r == "whisper" and "whisper to the customer") or (r == "off" and "off") or "party / raid chat")
            end
        elseif tab == "Advertise" then
            Head("The ad")
            local g = GroupSnapshot()
            local text = Core.BuildAd(db, g, fac, db.admsg)
            local state, a = AdState()
            local chans = AdChannels()
            local first = chans[1] and (chans[1]:sub(1, 1):upper() .. chans[1]:sub(2)) or "No channel ticked"
            if text then
                Say(first .. ", when you press the key", text)
                Note(#text .. " of 255 letters")
            end
            if state == "ready" then Note("Ready to post in " .. a:sub(1, 1):upper() .. a:sub(2) .. ".")
            elseif state == "wait" then Note(("Can post again in %d:%02d."):format(math.floor(a / 60), math.floor(a % 60)))
            else Note("No ad right now: " .. tostring(a)) end
            if not text then
                local keys = {}
                for _, def in ipairs(Core.SERVICES) do if Core.Setting(db, def.key).on then keys[#keys + 1] = def.key end end
                local ex = #keys > 0 and Core.BuildAd(db, (WithStandIns(g, keys)), fac, db.admsg)
                if ex then Say("Example, with someone who can do each ticked service standing with you", ex) end
            end
        elseif tab == "Paladin" or tab == "Buffs" then
            for _, key in ipairs(PV.KEYS.Paladin) do ServicePreview(key) end
            Head("Buff button")
            Say("Buff button", BuffLabel())
            local mine = {}
            for _, def in ipairs(MyBuffs()) do mine[#mine + 1] = def.label end
            Note(#mine > 0 and ("You cast: " .. table.concat(mine, ", ") .. ". Asking in party, raid or a whisper queues them.")
                or "None of the ticked buffs are yours to cast, so nothing gets queued for you.")
            if Core.Setting(db, "blessing").on then
                local parts = {}
                for _, b in ipairs(Core.BLESSINGS) do
                    parts[#parts + 1] = "\"" .. b.word .. "\" queues " .. b.spell .. (KnowSpell(b.spell) and "" or " (you don't have it)")
                end
                Note(table.concat(parts, "; ") .. "; plain \"blessing\" queues " .. tostring(Core.Setting(db, "blessing").spell) .. ".")
            end
        else
            for _, key in ipairs(PV.KEYS[tab] or {}) do ServicePreview(key) end
        end
    end)
    previewGroup = nil
    if not ok then out[#out + 1] = "|cffff4040Preview failed: " .. tostring(err) .. "|r" end
    -- raid icons show as icons here; in party/raid chat the game draws {rt1} itself
    for i, s in ipairs(out) do
        out[i] = s:gsub("{rt(%d)}", "|TInterface\\TargetingFrame\\UI-RaidTargetingIcon_%1:0|t")
    end
    return out
end
local function PrintPreview(tab)
    P("|cffffd100Preview of the " .. tab .. " tab.|r Nothing is sent; only you see this. Pretend buyer: " .. PV.BUYER .. ".")
    for _, line in ipairs(Preview(tab)) do P(line) end
end

IsSecret = function(v)
    if issecretvalue then
        local ok, r = pcall(issecretvalue, v)
        if ok and r then return true end
    end
    return false
end
SpellNameOf = function(spellID)
    if spellID == nil or IsSecret(spellID) then return nil end
    local ok, r = pcall(function()
        if C_Spell and C_Spell.GetSpellName then return C_Spell.GetSpellName(spellID) end
        if GetSpellInfo then return (GetSpellInfo(spellID)) end
    end)
    if ok and type(r) == "string" then return r end
end
local function IsWarlock(unit)
    local ok, _, cls = pcall(UnitClass, unit)
    return ok and cls == "WARLOCK"
end
-- The client hides spell ids of other players' casts ("secret values"), so they
-- cannot be compared. When hidden, fall back to: a warlock in the group started a
-- cast or channel (the lock is the summoner in this service).
local function RitualCast(unit, spellID, nm, event)
    if spellID ~= nil and not IsSecret(spellID) then
        return spellID == RITUAL_ID
    elseif spellID ~= nil then
        -- the ritual is a channel; ordinary warlock casts (Shadow Bolt etc.) never fire
        -- CHANNEL_START, so only that event counts, and only with a customer waiting
        if not (IsWarlock(unit) and event == "UNIT_SPELLCAST_CHANNEL_START") then return false end
        for _, j in ipairs(jobs) do if j.status == "joined" then return true end end
        return false
    end
    nm = nm or SpellNameOf(spellID)
    if type(nm) ~= "string" or IsSecret(nm) then return false end
    nm = nm:lower()
    return (nm:find("ritual", 1, true)) and true or false
end

OnCast = function(event, unit, spellID, spellName)
    if ServiceInviterDB.stasis then return end
    if type(unit) ~= "string" then return end
    if not spellID and not spellName then return end
    local mine = (unit == "player")
    if not mine and not (unit:match("^party%d+$") or unit:match("^raid%d+$")) then return end
    do
        local nm = (not IsSecret(spellName)) and spellName or SpellNameOf(spellID)
        local sec = IsSecret(spellID)
        local rec = { unit = unit, name = (type(nm) == "string" and not IsSecret(nm)) and nm or (sec and "(hidden)" or "?"), id = sec and "hidden" or spellID, event = event, t = GetTime() }
        table.insert(diag.casts, 1, rec)
        while #diag.casts > 4 do table.remove(diag.casts) end
        if debugOn and event ~= "UNIT_SPELLCAST_SUCCEEDED" then D("cast: " .. tostring(UnitName and UnitName(unit) or unit) .. " " .. rec.name .. " (" .. tostring(rec.id) .. ") " .. event) end
    end
    if not RitualCast(unit, spellID, spellName, event) then return end

    -- who is it for: the caster's target if that is one of our customers, else the next one waiting
    local trace = { t = GetTime(), event = event, unit = unit, role = Role() }
    diag.last = trace
    local tname = FullName(unit .. "target")
    if tname and Ambiguate then tname = Ambiguate(tname, "none") end
    local job = tname and Jobs.Get(tname)
    -- With more than one warlock, a ritual is for a customer going to where THIS warlock stands.
    local castZone = ZoneOf(unit)
    local function forThisLock(j)
        return j.status == "joined" and (not castZone or not j.dest or j.dest == castZone)
    end
    if not (job and forThisLock(job)) and not event:find("SUCCE", 1, true) then
        -- target is not someone waiting for this warlock: use whoever has waited longest for them
        local waiting
        for _, j in ipairs(jobs) do if forThisLock(j) then waiting = j break end end
        job = waiting or job
    end
    -- someone the addon didn't invite, now being summoned: a summon customer, to where the
    -- warlock stands (their row, the alert, Expected and the arrival all follow from this)
    if job and not job.service then job.service, job.dest = "summons", castZone end
    local who = job and job.name or tname or "someone"
    local caster = FullName(unit) or unit
    if job and (job.status == "joined" or job.status == "summoned") and not job.caster then
        job.caster = Ambiguate and Ambiguate(caster, "none") or caster
    end
    trace.who, trace.target = who, tname
    D(caster .. " started Ritual of Summoning for " .. who .. " (" .. event .. ")")

    if mine then trace.stop = "that was you casting" return end
    if Role() ~= "helper" then trace.stop = "role is not helper (/si role helper)" return end

    local now = GetTime()
    local first = (now - lastCastAt) > 8
    local portalUp = event:find("SUCCE", 1, true) ~= nil
    trace.first = first

    -- 1) the messages first, so nothing else can get in their way
    if first then
        lastCastAt = now
        local to = WhisperTo()
        if to and FullName("player") ~= to then
            local nxt
            for _, j in ipairs(jobs) do if forThisLock(j) and j ~= job then nxt = j.name break end end
            local ok, err = pcall(SendWhisperTo, to, WhisperText(who, nxt))
            trace.whisper = ok and ("sent to " .. tostring(err)) or ("failed: " .. tostring(err))
        else
            trace.whisper = "off"
        end
        if ServiceInviterDB.raidalert ~= false then
            local ch = (IsInRaid and IsInRaid()) and "RAID" or ((IsInGroup and IsInGroup()) and "PARTY" or nil)
            if ch then
                local ok, err = pcall(function() Jobs.Route("alert", AlertMsg(who, job, castZone), who, ch) end)
                trace.raid = ok and ("sent to " .. ch) or ("failed: " .. tostring(err))
            else
                trace.raid = "not in a group"
            end
        else
            trace.raid = "off"
        end
    end

    -- 2) the banner
    if portalUp then
        local ok, err = pcall(ShowAlert, "CLICK PORTAL", BannerSub(who, job), "PORTAL IS UP")
        trace.banner = ok and "shown" or ("error: " .. tostring(err))
    elseif first then
        local ok, err = pcall(ShowAlert, "CLICK PORTAL", BannerSub(who, job), "SUMMONING")
        trace.banner = ok and "shown" or ("error: " .. tostring(err))
    end

    -- 3) mark the customer as being summoned
    -- only the first event of a cast marks anyone: raid1 and party1 both fire for one cast
    if first and job and job.status == "joined" then
        local ok, err = pcall(Jobs.Set, job.name, "summoned")
        trace.marked = ok and "yes" or ("error: " .. tostring(err))
        -- another warlock's shard: off the count you typed (yours come off your bags)
        local typed = tonumber(ServiceInviterDB.shards)
        if ok and typed then ServiceInviterDB.shards = math.max(0, typed - 1) end
    end
end

-- Arrival (and, for the lock, auto-open trade). Runs every second, window open or not.
local function CheckArrivals()
    local now = GetTime()
    Jobs.Expire(now)
    -- one automatic retry for people who were already in another group
    for _, j in ipairs(jobs) do
        if j.status == "busy" and j.retryAt and now >= j.retryAt then
            j.retryAt = nil
            local nm = j.name
            if Jobs.InGroup(nm) then
                Jobs.Set(nm, "joined")
            elseif Opt("enabled") or Opt("kwon") then
                lastInvite[nm] = now pending[nm] = now
                j.t = now
                Jobs.Set(nm, "invited")
                DoInvite(nm)
                D("retrying invite for " .. nm)
            end
        end
    end
    for _, j in ipairs(jobs) do
        if j.status == "summoned" then
            local u = UnitFor(j.name)
            local visible = u and UnitIsVisible and UnitIsVisible(u)
            -- Arrived = the game shows them there: near enough to see, or in the summon's city.
            -- No timer: a summon they never took isn't an arrival (the owner, 14 Nov 2026: "so
            -- they register as arrived after simply receiving the summon").
            local z = u and ZoneOf(u)
            local there = visible or (j.dest and z and z == j.dest)
            if there then
                Jobs.Set(j.name, "arrived")
                -- unasked, only if you want that (the owner, 14 Nov 2026: "can i set it to not auto
                -- queue a blessing if they dont ask for one?")
                if visible and Opt("buffarrivals") then QueueAllMyBuffs(j.name) end
                -- tell them what else is on offer where they landed; nothing there = no message
                if not j.offered then
                    j.offered = true
                    local text = ArrivalText(j)
                    local ch = (IsInRaid and IsInRaid()) and "RAID" or ((IsInGroup and IsInGroup()) and "PARTY" or nil)
                    if text then pcall(Jobs.Route, "arrival", text, j.name, ch) end
                end
            end
        elseif not blockedCalls.InitiateTrade and not j.tradeTried and AutoTradeOn() and CollectsFor(j)
            -- summons: just landed; anything else paid (portals, lockpicking...): in the group a
            -- while, and they come to you (the Codex review, 12 Nov 2026)
            and ((j.status == "arrived" and j.tarrive and now - j.tarrive < 60)
              or (NextStep(j) == "serve" and JobPrice(j) and j.ts and now - j.ts < 600)) then
            local u = UnitFor(j.name)
            if u and CheckInteractDistance and CheckInteractDistance(u, 2) then
                j.tradeTried = true
                pendingTrade = j.name
                local ok, err = pcall(InitiateTrade, u)
                D("auto trade to " .. j.name .. (ok and " sent" or (" failed: " .. tostring(err))))
            end
        end
    end
end
local ticker = CreateFrame("Frame")
local tacc = 0
ticker:SetScript("OnUpdate", function(_, el)
    tacc = tacc + (el or 0)
    Jobs.outAcc = (Jobs.outAcc or 0) + (el or 0)
    if Jobs.outAcc >= Jobs.OUT_EVERY and #Jobs.outbox > 0 and not (Jobs.outWait and GetTime() < Jobs.outWait) then
        Jobs.outAcc = 0
        Report("team books", pcall(Jobs.Drain))
    end
    if tacc >= 1 then
        tacc = 0
        if not ServiceInviterDB.stasis then
            Report("arrivals", pcall(CheckArrivals))
            if #buffQueue > 0 then Report("buffs", pcall(RefreshBuff)) end   -- range, and anyone who left
            if Jobs.TeamOn() and GetTime() - Jobs.Team.lastHi > 60 then Report("team", pcall(Jobs.SayHi, false)) end
            Report("team books", pcall(Jobs.BookTick))
        end
    end
end)

-- Take a customer out of the group: a click only (Paid, Done or x), and only as leader (or an
-- assistant in a raid); otherwise the leader has to.
-- Can you take people out of the group? The leader, or an assistant in a raid.
function Jobs.CanRemove()
    local lead = UnitIsGroupLeader and UnitIsGroupLeader("player")
    local assist = IsInRaid and IsInRaid() and UnitIsGroupAssistant and UnitIsGroupAssistant("player")
    return (lead or assist) and true or false
end
-- The removal itself is the game's own /uninvite, run by the secure Paid and x buttons on your
-- click: an addon calling UninviteUnit gets blocked (the owner's screenshot, 13 Nov 2026:
-- "UninviteUnit() was blocked", then a false "removed ..."). This only says what happens.
local function RemoveFromGroup(name)
    if not InGroupByName(name) then return end
    if Jobs.CanRemove() then
        P("removing " .. name .. " from the group")
        return
    end
    -- who is leader, so the message can name them
    local leader
    for _, m in ipairs(GroupSnapshot()) do
        if m.unit and UnitIsGroupLeader and UnitIsGroupLeader(m.unit) then leader = m.name end
    end
    P(name .. " is done. You're not the leader" .. (IsInRaid and IsInRaid() and " or an assistant" or "") ..
        ", so ask " .. (leader or "the leader") .. " to remove them.")
end
-- Paid (or Done, for a free service): thank them (before the button's /uninvite runs), then
-- mark them and say what happens to their spot in the group.
local function FinishJob(name)
    local j = Jobs.Get(name)
    if not j or j.status == "paid" or j.status == "done" then return end
    Thank(j)
    Jobs.Set(name, JobPrice(j) and "paid" or "done")
    RemoveFromGroup(name)
end
-- Scam: they didn't pay. On the list, out of the group (the button's /uninvite), no thanks.
function Jobs.Scam(name)
    local j = Jobs.Get(name)
    ServiceInviterDB.scammers = type(ServiceInviterDB.scammers) == "table" and ServiceInviterDB.scammers or {}
    local key = name
    for k in pairs(ServiceInviterDB.scammers) do if k:lower() == name:lower() then key = k end end
    local e = ServiceInviterDB.scammers[key] or { n = 0, owed = 0 }
    e.n = e.n + 1
    e.owed = (e.owed or 0) + ((j and JobPrice(j)) or 0)
    e.last = math.max(Now(), (e.cleared or 0) + 1)
    e.rev = Jobs.Bump()
    ServiceInviterDB.scammers[key] = e
    -- marked Paid by mistake (the owner, 14 Nov 2026: "i accidentally added paid to someone but
    -- meant to add scam"): the money comes back off the session
    if j and j.status == "paid" then
        local st = Stats()
        st.paid = math.max(0, (st.paid or 0) - 1)
        st.silver = math.max(0, (st.silver or 0) - (j.amount or JobPrice(j) or 0))
    end
    if j then Jobs.Set(name, "scammed") end
    if Jobs.TeamOn() then Jobs.SayHi(false) end   -- the team's copies come and get it now
    P("|cffff8080" .. name .. " recorded as not paying|r (" .. e.n .. (e.n == 1 and " time" or " times") .. "). Called out if they join again; never invited.")
    RemoveFromGroup(name)
end
-- The /uninvite a row's Paid and x buttons run: only when you may, and only for someone in the group.
local function KickMacro(job)
    if not (job and Jobs.CanRemove() and InGroupByName(job.name)) then return "" end
    return "/uninvite " .. job.name
end

local function Since(t)
    local s = math.max(0, math.floor(GetTime() - (t or GetTime())))
    if s < 60 then return s .. "s" end
    return math.floor(s / 60) .. "m " .. (s % 60) .. "s"
end
-- "Summons to Thunder Bluff", "Portal to Undercity", "Lockpicking"
local function ServiceLine(job)
    local def = job.service and Core.BY_KEY[job.service]
    if not def then return "Joined the group" end
    if def.kind == "summon" then return "Summons to " .. (job.dest or "?") end
    if def.kind == "portal" then return "Portal to " .. (job.dest or "?") end
    local l = def.label:gsub("^a ", "")
    return l:sub(1, 1):upper() .. l:sub(2)
end
-- The row's one meta line: » city · who does it (class colored), or the service when it isn't a
-- summon. What went wrong with an invite is the status pill's job now.
function Jobs.RowMeta(job, g)
    local def = job.service and Core.BY_KEY[job.service]
    if not def then return "|cff" .. INK.faint .. "joined the group|r" end
    local where = def.kind == "summon" and ("» " .. (job.dest or "?")) or ServiceLine(job)
    local p = Core.Provider(g, job.service, job.dest)
    if job.caster then p = { name = job.caster } for _, m in ipairs(g) do if m.name == job.caster then p = m end end end
    local who = p and (p.me and "you" or Colored(p.name, p.class)) or ("|cff" .. INK.faint .. "nobody here can|r")
    return where .. "  |cff" .. INK.faint .. "·|r  " .. who
end
-- Who does it and where, or what went wrong with the invite.
local function WhoLine(job, g)
    if job.status == "busy" then return "Invite failed, already in a group" end
    if job.status == "declined" then return "Declined the invite" end
    if job.status == "noanswer" then return "Didn't answer the invite" end
    if job.status == "left" then return "Left the group" end
    local def = job.service and Core.BY_KEY[job.service]
    if not def then return "" end
    local p = Core.Provider(g, job.service, job.dest)
    if not p then return "Nobody in the group can do this now" end
    local who = p.me and "You" or Colored(p.name, p.class)
    return who .. (p.zone and (" in " .. p.zone) or "")
end

local function ApplyRow(row, job)
    row.job = job
    row.summon:Hide() row.offer:Hide() row.trade:Hide() row.paid:Hide() row.remove:Hide() row.reinvite:Hide() row.scam:Hide()
    row.upBox:Hide() row.upIn:Hide()
    if not job then
        for _, t in ipairs(row.paint) do t:Hide() end
        row.name:SetText("") row.status:SetText("") row.where:SetText("") row.age:SetText("") row.note:SetText("")
        return
    end
    for _, t in ipairs(row.paint) do t:Show() end
    local st = JOB_STATUS[job.status] or { job.status, "" }
    if not job.class then
        local u = UnitFor(job.name)
        if u then local ok, _, cls = pcall(UnitClass, u) if ok then job.class = cls end end
    end
    local g = GroupSnapshot()
    local before = Jobs.Before(job)
    -- the name in its class color, and a regular's count (the redesign dropped it; kept)
    row.name:SetText(Colored(job.name, job.class) .. (before > 0 and ("  |cff" .. INK.muted .. "· " .. before .. " before|r") or ""))
    row.where:SetText(Jobs.RowMeta(job, g))
    row.status:SetText(st[1])
    local pill = INK.PILL[job.status] or INK.PILL.left
    row.pill:SetColorTexture(RGB(pill[1]))
    row.status:SetTextColor(RGB(pill[2]))
    -- whoever the cast strip is for: a gold bar and edge
    local nextUp = jobsWin and jobsWin.heroJob == job
    row.bar:SetColorTexture(RGB(nextUp and INK.gold or pill[3]))
    row.edge:SetColorTexture(RGB(nextUp and INK.gold or INK.panel))
    row.age:SetText(Jobs.Clock(job.ts or job.t))
    row.note:SetText("")
    local n = UnitFor(job.name) or CleanName(job.name)
    row.summon:SetAttribute("macrotext", "/target " .. n .. "\n/cast Ritual of Summoning")
    row.trade:SetAttribute("macrotext", "/target " .. n .. "\n/run InitiateTrade(\"target\")")
    row.paid:SetAttribute("macrotext", KickMacro(job))
    row.scam:SetAttribute("macrotext", KickMacro(job))
    row.remove:SetAttribute("macrotext", KickMacro(job))
    local step = NextStep(job)
    local lock = Role() == "lock"
    row.reinvite:SetAttribute("macrotext", "/invite " .. job.name)
    if job.status == "asked" or job.status == "busy" or job.status == "noanswer" or job.status == "declined" then
        row.reinvite:SetText(job.status == "asked" and "Invite" or "Re-invite")
        row.reinvite:Show()
    elseif step == "summon" then
        if YouSummon(job) then row.summon:Show()
        else
            -- their warlock is on the meta line; UP says it's theirs to do now
            local p = Core.Provider(g, "summons", job.dest)
            if p and not p.me then row.note:SetText("UP") row.upBox:Show() row.upIn:Show() end
        end
    elseif step == "arriving" then
        row.paid:Show()
    elseif step == "offer" then
        local mine = CollectsFor(job)
        if lock then row.offer:Show() elseif mine then row.trade:Show() end
        row.paid:Show()
    elseif step == "finish" then
        if CollectsFor(job) then row.trade:Show() end
        row.paid:Show()
    elseif step == "serve" then
        if JobPrice(job) and CollectsFor(job) then row.trade:Show() end
        row.paid:Show()
    end
    row.paid:SetText(JobPrice(job) and "Paid" or "Done")
    if job.status == "left" and job.owes then row.paid:Show() end
    if (row.paid:IsShown() and JobPrice(job)) or job.status == "paid" then row.scam:Show() end
    -- no Paid button: Scam, x and Clear left are what gets used (the owner, 14 Nov 2026: "having a
    -- paid button is kind of redundant, i hardly ever use it"). A trade that pays still marks Paid.
    row.paid:Hide()
    row.remove:Show()
end

-- After your click sends the game's /invite (the big button or a row's Invite): they're invited.
function Jobs.InviteClicked(job)
    if not job then return end
    local now = GetTime()
    job.t, job.tries, job.suggested = now, nil, nil
    lastInvite[job.name], pending[job.name] = now, now
    Jobs.Set(job.name, "invited")
end

-- The cast strip's look: gold when it's a click for you, quiet otherwise.
function Jobs.Hero(w, verb, name, plus, active)
    w.heroBg:SetColorTexture(RGB(active and INK.gold or INK.panel))
    w.heroVerb:SetText(verb or "")
    w.heroVerb:SetTextColor(RGB(active and INK.goldInk or INK.muted))
    w.heroName:SetText(name or "")
    -- no step word: the line sits in the middle
    w.heroName:ClearAllPoints() w.heroName:SetPoint("TOPLEFT", 76, (verb or "") ~= "" and -94 or -84)
    w.heroName:SetTextColor(RGB(active and INK.goldInk or (verb ~= "" and INK.text or INK.faint)))
    if w.heroIcon.SetAlpha then w.heroIcon:SetAlpha(active and 1 or 0.4) end
    if plus and plus > 0 then
        w.heroPlus:SetText("+" .. plus) w.heroPlus:Show() w.heroPlusBg:Show()
        w.heroPlusBg:SetColorTexture(RGB(active and INK.goldInk or INK.plain))
    else
        w.heroPlus:SetText("") w.heroPlus:Hide() w.heroPlusBg:Hide()
    end
end
Jobs.STEP_VERB = { invite = "INVITE", summon = "SUMMON", offer = "OFFER", finish = "TRADE", serve = "TRADE" }
local function ApplyNext()
    local w = jobsWin
    local asking = false
    for _, j in ipairs(jobs) do if j.status == "asked" then asking = true break end end
    if Role() == "helper" and not asking then
        -- the warlock summons; you click the portal: who's next, not a button
        w.nextBtn:Hide()
        local nxt, waiting = nil, 0
        for _, j in ipairs(jobs) do if NextStep(j) == "summon" then nxt = nxt or j waiting = waiting + 1 end end
        w.heroJob = nxt
        if nxt then Jobs.Hero(w, "NEXT UP", Colored(nxt.name, nxt.class), waiting - 1, false)
        else Jobs.Hero(w, "", "Nothing to do", 0, false) end
        return
    end
    w.nextBtn:Show()
    local job, step = NextJob()
    w.nextBtn.step, w.nextBtn.job = step, job
    w.heroJob = job
    -- how many more of yours are waiting after this one
    local more = 0
    for _, j in ipairs(jobs) do
        if j ~= job then
            local st = NextStep(j)
            if (st == "summon" and YouSummon(j)) or st == "offer" or ((st == "finish" or (st == "serve" and JobPrice(j))) and CollectsFor(j)) then more = more + 1 end
        end
    end
    if not job then
        w.nextBtn:SetText("Nothing to do")
        w.nextBtn:SetAttribute("macrotext", "")
        Jobs.Hero(w, "", "Nothing to do", 0, false)
        return
    end
    local n = UnitFor(job.name) or CleanName(job.name)
    if step == "invite" then
        w.nextBtn:SetText("Invite " .. job.name)
        w.nextBtn:SetAttribute("macrotext", "/invite " .. job.name)
    elseif step == "summon" then
        w.nextBtn:SetText("Summon " .. job.name)
        w.nextBtn:SetAttribute("macrotext", "/target " .. n .. "\n/cast Ritual of Summoning")
    elseif step == "offer" then
        w.nextBtn:SetText("Offer extras to " .. job.name)
        w.nextBtn:SetAttribute("macrotext", ((IsInRaid and IsInRaid()) and "/raid " or "/p ") .. OfferText(job.name))
    else
        w.nextBtn:SetText("Trade " .. job.name)
        w.nextBtn:SetAttribute("macrotext", "/target " .. n .. "\n/run InitiateTrade(\"target\")")
    end
    Jobs.Hero(w, Jobs.STEP_VERB[step] or "TRADE", job.name, more, true)
end
-- The blessing button's look: the spell, who for, and how many more.
function Jobs.ApplyBless(w)
    local e = buffQueue[1]
    if not e then
        w.blessSpell:SetText("BLESSINGS") w.blessWho:SetText("Nobody waiting") w.blessWho:SetTextColor(RGB(INK.faint))
        w.blessEdge:SetColorTexture(RGB(INK.soft))
        if w.blessIcon.SetAlpha then w.blessIcon:SetAlpha(0.4) end
        return
    end
    local spell = e.spell or "Blessing of Might"
    w.blessIcon:SetTexture(Jobs.BlessIcon(spell))
    w.blessSpell:SetText(spell:gsub("^Blessing of ", ""):gsub("^Greater ", ""):upper())
    local inRange = Jobs.BuffInRange(e)
    local cls
    local u = UnitFor(e.name)
    if u then local ok, _, c = pcall(UnitClass, u) if ok and not IsSecret(c) then cls = c end end
    if inRange then
        w.blessWho:SetText(Colored(e.name, cls) .. (#buffQueue > 1 and ("  |cff" .. INK.muted .. "+" .. (#buffQueue - 1) .. "|r") or ""))
        w.blessWho:SetTextColor(RGB(INK.text))
    else
        w.blessWho:SetText("Out of range") w.blessWho:SetTextColor(RGB(INK.warn))
    end
    w.blessEdge:SetColorTexture(RGB(inRange and INK.gold or INK.soft))
    if w.blessIcon.SetAlpha then w.blessIcon:SetAlpha(inRange and 1 or 0.5) end
end

RefreshJobs = function()
    if not jobsWin or not jobsWin:IsShown() then return end
    if InCombatLockdown and InCombatLockdown() then jobsDirty = true return end
    jobsDirty = false
    CheckArrivals()

    local list, hidden = VisibleJobs()
    ApplyNext()   -- first: the rows mark whoever the strip is for
    for i = 1, ROWS do ApplyRow(jobsWin.rows[i], list[i]) end
    if #list == 0 then jobsWin.empty:Show() jobsWin.emptyIcon:Show() else jobsWin.empty:Hide() jobsWin.emptyIcon:Hide() end
    local wait, going, active = 0, 0, 0
    for _, j in ipairs(jobs) do
        if j.status == "joined" then wait = wait + 1 elseif j.status == "summoned" then going = going + 1 end
        if ACTIVE[j.status] then active = active + 1 end
    end
    jobsWin.count:SetText(active .. " active" .. ((hidden or 0) > 0 and ("  |cff" .. INK.faint .. "· " .. hidden .. " more not shown|r") or ""))
    local st = Stats()
    -- what we summoned and what that's worth (the owner, 13 Nov 2026: "it should still record
    -- EV - how many we summon. the paid will be inaccurate no matter what"). Collected is on
    -- the Setup's General page.
    jobsWin.statSummoned:SetText(tostring(st.summoned or 0))
    jobsWin.statEV:SetText(Jobs.MoneyShort(st.ev or 0))
    local left = Jobs.ShardsLeft()
    jobsWin.statShards:SetText(left and tostring(math.max(0, left)) or "-")
    jobsWin.statWait:SetText(tostring(wait) .. (going > 0 and ("  |cff" .. INK.faint .. "+" .. going .. "|r") or ""))
    RefreshBuff()   -- the buff button shows whoever is next, even if they asked before the list was open
    jobsWin.Fit(#list, jobsWin.buffBtn:IsShown())
    Jobs.ApplyBless(jobsWin)
    if jobsWin.adBtn then
        local label, ready = AdLabel()
        jobsWin.adBtn:SetText(label)
        if ready then jobsWin.adBtn:Enable() else jobsWin.adBtn:Disable() end
        if jobsWin.adBtn.SetAlpha then jobsWin.adBtn:SetAlpha(ready and 1 or 0.55) end
    end
end

local function BuildJobsUI()
    -- The 2026 redesign (design handoff, reviewed 14 Nov 2026): fixed 600 x 614, so nothing moves
    -- or resizes when customers come and go, in combat or not. Six fixed rows: each row's buttons
    -- are secure macros bound to that customer and can't be rebound in combat, so the list never
    -- scrolls. Everything is drawn on the window itself (flat fills, 1px lines, game fonts and
    -- spell icons); only the buttons that cast are real secure buttons.
    local W, H = 600, 614
    local ROW_H, GAP, LIST_TOP, FOOT_TOP = 56, 6, 176, 550
    local w = CreateFrame("Frame", "ServiceInviterJobs", UIParent)
    w:SetSize(W, H)
    w:SetPoint("TOP", UIParent, "TOP", 0, -80)
    w:SetFrameStrata("DIALOG")
    w:SetClampedToScreen(true)
    w:SetMovable(true)
    w:EnableMouse(true)
    w:RegisterForDrag("LeftButton")
    -- The window holds buttons that cast, so in combat the game won't let it move or close (the
    -- owner, 14 Nov 2026, mid-fight: "whoa what i cant even close it"). Dragging waits for the
    -- fight to end, and closing fades it out now and closes it after (Jobs.CloseJobs).
    w:SetScript("OnDragStart", function(self)
        if InCombatLockdown and InCombatLockdown() then return end
        self.dragging = true self:StartMoving()
    end)
    w:SetScript("OnDragStop", function(self)
        if not self.dragging then return end
        self.dragging = nil
        self:StopMovingOrSizing()
        -- keep it pinned by the top-left wherever you drop it
        local l, t = self:GetLeft(), self:GetTop()
        if l and t then self:ClearAllPoints() self:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", l, t) end
    end)
    local edge = Fill(w, INK.frame, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
    local bg = Fill(w, INK.ground, "BACKGROUND", -7) bg:SetAllPoints()
    w:Hide()
    local function Rect(x, y, cw, ch, hex, layer, sub)
        local t = Fill(w, hex, layer or "BACKGROUND", sub or -6) t:SetPoint("TOPLEFT", x, y) t:SetSize(cw, ch) return t
    end
    local function Icon(x, y, size, path)
        local t = w:CreateTexture(nil, "ARTWORK") t:SetPoint("TOPLEFT", x, y) t:SetSize(size, size)
        t:SetTexture(path)
        return t
    end
    local function Caps(x, y, text, hex)
        local fs = Text(w, 11, hex or INK.muted) fs:SetPoint("TOPLEFT", x, y) fs:SetText(text) return fs
    end

    -- header: the summoning icon, Customers, then Regulars, the ad, Setup and close
    Rect(0, 0, W, 52, INK.deep)
    Rect(0, -52, W, 1, INK.soft, "BORDER")
    Icon(16, -16, 20, Jobs.SpellIcon(Jobs.RITUAL_ID, Jobs.RITUAL_ICON))
    local title = Text(w, 15, INK.text, "GameFontNormalLarge")
    title:SetPoint("TOPLEFT", 44, -19) title:SetText("Customers")
    local close = FlatButton(w, 28, 28, "bare", 15)
    close:SetPoint("TOPRIGHT", -12, -12) close:SetText("x")
    close:SetScript("OnClick", function() Jobs.CloseJobs() end)
    Jobs.Tip(close, "Close")
    local setupBtn = FlatButton(w, 64, 32, "plain", 13)
    setupBtn:SetPoint("TOPRIGHT", -48, -10) setupBtn:SetText("Setup")
    setupBtn:SetScript("OnClick", function() ToggleSetup() end)
    local adBtn = FlatButton(w, 150, 32, "ghost", 13)
    adBtn:SetPoint("TOPRIGHT", -120, -10) adBtn:SetText("Post ad")
    adBtn:SetScript("OnClick", function() PostAd() end)
    Jobs.Tip(adBtn, "Post the ad (bind a key: /si bind ad F7)")
    w.adBtn = adBtn
    local regBtn = FlatButton(w, 92, 32, "plain", 13)
    regBtn:SetPoint("TOPRIGHT", -278, -10) regBtn:SetText("Regulars")
    regBtn:SetScript("OnClick", function() Jobs.Copy("Regulars", function() Jobs.PrintRegulars("") end) end)
    w.regularsBtn = regBtn

    -- the cast strip: your next step (Invite / Summon / Offer / Trade + who) and, for a paladin,
    -- the blessing button. Secure buttons must listen for press AND release: newer clients fire
    -- them on press. The words are drawn on the window over the button; its own text is the
    -- label the tests read, kept hidden.
    local SX, SY, SH, BLESS_W = 12, -64, 64, 196
    w.heroBg = Rect(SX, SY, W - 24, SH, INK.panel, "BACKGROUND", -5)
    w.heroIcon = Icon(SX + 12, SY - 12, 40, Jobs.SpellIcon(Jobs.RITUAL_ID, Jobs.RITUAL_ICON))
    w.heroVerb = Caps(SX + 64, SY - 13, "")
    w.heroName = Text(w, 19, INK.text, "GameFontNormalLarge")
    w.heroName:SetPoint("TOPLEFT", SX + 64, SY - 30) w.heroName:SetWidth(260) w.heroName:SetJustifyH("LEFT")
    if w.heroName.SetWordWrap then w.heroName:SetWordWrap(false) end
    w.heroPlusBg = Rect(0, 0, 36, 24, INK.goldInk, "BORDER")
    w.heroPlus = Text(w, 13, INK.gold)
    local nb = FlatButton(w, W - 24, SH, "hero", 13, true, "ServiceInviterNext")
    nb:SetPoint("TOPLEFT", SX, SY)
    nb:RegisterForClicks("AnyUp", "AnyDown")
    nb:SetAttribute("type", "macro")
    nb:SetText("Nothing to do")
    nb:HookScript("PostClick", function(self)
        local job, step = self.job, self.step
        if not job then return end
        if step == "invite" then Jobs.InviteClicked(job)
        elseif step == "summon" then Jobs.Set(job.name, "summoned")
        elseif step == "offer" then job.offered = true
        elseif step == "finish" then pendingTrade = job.name end
        RefreshJobs()
    end)
    w.nextBtn = nb
    -- the blessing button: only for a paladin selling blessings (decided out of combat)
    local BX = W - 12 - BLESS_W
    w.blessBg = Rect(BX, SY, BLESS_W, SH, INK.panel, "BACKGROUND", -5)
    w.blessEdge = Rect(BX - 1, SY + 1, BLESS_W + 2, SH + 2, INK.soft, "BACKGROUND", -6)
    w.blessIcon = Icon(BX + 12, SY - 12, 40, Jobs.BlessIcon())
    w.blessSpell = Caps(BX + 64, SY - 13, "")
    w.blessWho = Text(w, 14, INK.text)
    w.blessWho:SetPoint("TOPLEFT", BX + 64, SY - 31) w.blessWho:SetWidth(BLESS_W - 72) w.blessWho:SetJustifyH("LEFT")
    if w.blessWho.SetWordWrap then w.blessWho:SetWordWrap(false) end
    local bb = FlatButton(w, BLESS_W, SH, "hero", 13, true)
    bb:SetPoint("TOPLEFT", BX, SY)
    bb:RegisterForClicks("AnyUp", "AnyDown")
    bb:SetAttribute("type", "macro")
    bb:SetText("No buffs waiting")
    bb:Hide()
    w.buffBtn = bb

    -- above the list: how many, and Clear left (the owner, 14 Nov 2026: "maybe a clear the
    -- people who have left the group")
    w.count = Text(w, 12, INK.muted)
    w.count:SetPoint("TOPLEFT", 14, -152)
    local clearBtn = FlatButton(w, 96, 26, "plain", 12)
    clearBtn:SetPoint("TOPRIGHT", -12, -144) clearBtn:SetText("Clear left")
    clearBtn:SetScript("OnClick", function() Jobs.ClearLeft() RefreshJobs() end)
    w.clearBtn = clearBtn

    -- the rows: bar | name and where | status | time | Scam | action | x
    local NX, PX, TX, BX2, AX, RX = 28, 214, 318, 380, 458, 556
    w.rows = {}
    for i = 1, ROWS do
        local y = -LIST_TOP - (i - 1) * (ROW_H + GAP)
        local row = {}
        local rEdge = Rect(12, y, W - 24, ROW_H, INK.panel, "BACKGROUND", -6)
        local rBg = Rect(13, y - 1, W - 26, ROW_H - 2, INK.panel, "BACKGROUND", -5)
        row.edge = rEdge
        row.bar = Rect(12, y, 4, ROW_H, INK.muted, "BORDER")
        row.pill = Rect(PX, y - 17, 98, 22, INK.PILL.joined[1], "BORDER")
        row.upBox = Rect(AX + 46, y - 16, 40, 24, INK.gold, "BORDER", 0)
        row.upIn = Rect(AX + 47, y - 17, 38, 22, INK.panel, "BORDER", 1)
        row.paint = { rEdge, rBg, row.bar, row.pill }

        row.name = Text(w, 14, INK.text, "GameFontHighlightLarge")
        row.name:SetPoint("TOPLEFT", NX, y - 10)
        row.name:SetWidth(180) row.name:SetJustifyH("LEFT")
        if row.name.SetWordWrap then row.name:SetWordWrap(false) end
        row.where = Text(w, 12, INK.muted)
        row.where:SetPoint("TOPLEFT", NX, y - 32)
        row.where:SetWidth(180) row.where:SetJustifyH("LEFT")
        if row.where.SetWordWrap then row.where:SetWordWrap(false) end
        row.service = row.where   -- one meta line now: -> city · who (the old two lines said it twice)
        row.status = Text(w, 12, INK.text)
        row.status:SetPoint("TOPLEFT", PX, y - 22) row.status:SetWidth(98)
        row.age = Text(w, 12, INK.muted)
        row.age:SetPoint("TOPLEFT", TX, y - 22)
        row.age:SetWidth(52) row.age:SetJustifyH("LEFT")
        row.note = Text(w, 11, INK.gold)
        row.note:SetPoint("TOPLEFT", AX + 46, y - 22) row.note:SetWidth(40)

        local AY = y - 12
        local function Slot(x, width, text, style)
            local b = FlatButton(w, width, 32, style or "ghost", 13, true)
            b:SetPoint("TOPLEFT", x, AY) b:SetText(text)
            b:RegisterForClicks("AnyUp", "AnyDown")
            b:SetAttribute("type", "macro")
            return b
        end
        row.summon = Slot(AX, 92, "Summon")
        row.summon:HookScript("PostClick", function() if row.job then Jobs.Set(row.job.name, "summoned") RefreshJobs() end end)
        row.offer = Slot(AX, 92, "Offer")
        row.offer:HookScript("PreClick", function()
            if row.job then row.offer:SetAttribute("macrotext", ((IsInRaid and IsInRaid()) and "/raid " or "/p ") .. OfferText(row.job.name)) end
        end)
        row.offer:HookScript("PostClick", function() if row.job then row.job.offered = true RefreshJobs() end end)
        row.trade = Slot(AX, 92, "Trade")
        row.trade:HookScript("PostClick", function()
            if row.job then pendingTrade = row.job.name D("Trade clicked for " .. row.job.name .. " (macro: " .. tostring(row.trade:GetAttribute("macrotext")) .. ")") end
        end)
        -- Invite / Re-invite: the game's /invite on your click (an addon's own invite becomes a
        -- mere suggestion when you're not the leader)
        row.reinvite = Slot(AX, 92, "Re-invite")
        row.reinvite:HookScript("PostClick", function() if row.job then Jobs.InviteClicked(row.job) RefreshJobs() end end)
        -- Paid (hidden since 3.0.1, kept for a trade that pays) and Scam run the game's
        -- /uninvite (set in ApplyRow), so the removal is yours and the game doesn't block it
        row.paid = Slot(BX2, 72, "Paid", "plain")
        row.paid:HookScript("PreClick", function() if row.job then Thank(row.job) end end)
        row.paid:HookScript("PostClick", function() if row.job then FinishJob(row.job.name) RefreshJobs() end end)
        row.scam = Slot(BX2, 72, "Scam", "plain")
        row.scam:HookScript("PostClick", function() if row.job then Jobs.Scam(row.job.name) RefreshJobs() end end)
        row.remove = Slot(RX, 28, "x", "bare")
        row.remove:HookScript("PostClick", function()
            if not row.job then return end
            -- x = done with this customer: out of the group too, if you may
            RemoveFromGroup(row.job.name)
            Jobs.Remove(row.job.name)
            RefreshJobs()
        end)
        w.rows[i] = row
    end

    -- empty: the summoning icon, dim, and two words
    w.emptyIcon = Icon(W / 2 - 24, -300, 48, Jobs.SpellIcon(Jobs.RITUAL_ID, Jobs.RITUAL_ICON))
    if w.emptyIcon.SetDesaturated then w.emptyIcon:SetDesaturated(true) end
    if w.emptyIcon.SetAlpha then w.emptyIcon:SetAlpha(0.35) end
    w.empty = Text(w, 14, INK.muted)
    w.empty:SetPoint("TOPLEFT", 0, -362) w.empty:SetWidth(W)
    w.empty:SetText("No customers")

    -- footer: the session, and New
    Rect(0, -FOOT_TOP, W, H - FOOT_TOP, INK.deep)
    Rect(0, -FOOT_TOP, W, 1, INK.soft, "BORDER")
    local function Stat(x, label)
        Caps(x, -FOOT_TOP - 12, label)
        local v = Text(w, 18, INK.text, "GameFontHighlightLarge")
        v:SetPoint("TOPLEFT", x, -FOOT_TOP - 30)
        return v
    end
    w.statSummoned = Stat(16, "SUMMONED")
    w.statEV = Stat(116, "EXPECTED")
    w.statWait = Stat(270, "WAITING")
    w.statShards = Stat(380, "SHARDS")
    local newBtn = FlatButton(w, 72, 32, "plain", 13)
    newBtn:SetPoint("TOPRIGHT", -12, -FOOT_TOP - 16) newBtn:SetText("New")
    newBtn:SetScript("OnClick", function() NewSession() RefreshJobs() P("new session started") Jobs.AskShards() end)
    Jobs.Tip(newBtn, "New session")

    -- the next-step button is full width unless there's a blessing button beside it. Out of
    -- combat only, like everything RefreshJobs does.
    function w.Fit(_, withBless)
        local nw = withBless and (W - 24 - BLESS_W - 8) or (W - 24)
        nb:SetWidth(nw)
        w.heroBg:SetWidth(nw)
        for _, t in ipairs({ w.blessBg, w.blessEdge, w.blessIcon, w.blessSpell, w.blessWho }) do
            if withBless then t:Show() else t:Hide() end
        end
        w.heroPlusBg:ClearAllPoints() w.heroPlusBg:SetPoint("TOPLEFT", SX + nw - 48, SY - 20)
        w.heroPlus:ClearAllPoints() w.heroPlus:SetPoint("TOPLEFT", SX + nw - 48, SY - 25) w.heroPlus:SetWidth(36)
    end
    w.Fit(1, false)

    local acc = 0
    w:SetScript("OnUpdate", function(_, elapsed)
        acc = acc + (elapsed or 0)
        if acc >= 1 then acc = 0 Report("customer list", pcall(RefreshJobs)) end
    end)
    w:SetScript("OnShow", RefreshJobs)
    return w
end

-- Close the customer window. In combat the game won't hide it, so it goes see-through now and
-- closes when the fight ends.
function Jobs.CloseJobs()
    local w = jobsWin
    if not w or not w:IsShown() then return end
    if InCombatLockdown and InCombatLockdown() then
        if not Jobs.closeLater then P("the customer list closes when combat ends") end
        Jobs.closeLater = true
        w:SetAlpha(0)
        return
    end
    Jobs.closeLater = nil
    w:Hide()
    w:SetAlpha(1)
end
function Jobs.AfterCombat()
    if Jobs.closeLater and jobsWin then Jobs.closeLater = nil jobsWin:Hide() jobsWin:SetAlpha(1) end
end
local function ToggleJobs()
    if ServiceInviterDB.stasis then P("|cffff8040stopped|r. /si start to wake it.") return end
    jobsWin = jobsWin or BuildJobsUI()
    if jobsWin:IsShown() and not Jobs.closeLater then Jobs.CloseJobs()
    elseif jobsWin:IsShown() then Jobs.closeLater = nil jobsWin:SetAlpha(1)   -- asked for back mid-fight
    elseif InCombatLockdown and InCombatLockdown() then P("the customer list can't open in combat. Try again after.")
    else jobsWin:SetAlpha(1) jobsWin:Show() end
end

jobsChanged = function(openIt)
    -- stopped: the window never opens by itself (the owner, 14 Nov 2026: "if i /si stop it should
    -- stop opening /si customers altogether, i am not currently using si")
    if openIt and Opt("autoshow") and not ServiceInviterDB.stasis then
        jobsWin = jobsWin or BuildJobsUI()
        if not (InCombatLockdown and InCombatLockdown()) and not jobsWin:IsShown() then jobsWin:Show() end
    end
    RefreshJobs()
end

----------------------------------------------------------------------
-- Setup window (/si setup): every message and setting, in the order things happen
----------------------------------------------------------------------
local setupWin

-- Pick list for "who gets paid": a titled menu with plain choices, the group listed below.
-- One shared frame; the box keeps working for a typed name.
local picker
-- The default payee in plain words, naming who that is for this service.
local DOER = { WARLOCK = "the warlock", MAGE = "the mage", ROGUE = "the rogue",
               PRIEST = "the priest", DRUID = "the druid", PALADIN = "the paladin" }
local function DefaultPayeeText(key)
    local d = type(ServiceInviterDB.payee) == "table" and ServiceInviterDB.payee or {}
    if d.mode == "me" then return "you" end
    if d.mode == "name" and d.name and d.name ~= "" then return d.name end
    local def = key and Core.BY_KEY[key]
    return def and DOER[def.class] or "whoever does it"
end
local function ShowPicker(box, withDefaults, title, key)
    local only = type(key) == "string" and key:match("^class:(%u+)$")   -- "Our warlocks": that class, added to the list
    if key == "workers" then only = "ANY" end                            -- "Our workers": anyone but customers
    if not picker then
        picker = CreateFrame("Frame", "ServiceInviterPicker", UIParent)
        picker:SetFrameStrata("FULLSCREEN_DIALOG")
        picker:EnableMouse(true)
        local edge = Fill(picker, INK.frame, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
        local bg = Fill(picker, INK.ground, "BACKGROUND", -7) bg:SetAllPoints()
        picker.title = Text(picker, 14, INK.text, "GameFontNormal")
        picker.title:SetPoint("TOPLEFT", 10, -9)
        picker.sub = Text(picker, 11, INK.muted, "GameFontHighlightSmall")
        picker.sub:SetPoint("TOPLEFT", 10, -26)
        picker.note = picker:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
        picker.buttons = {}
        picker:Hide()
    end
    if picker:IsShown() and picker.box == box then picker:Hide() return end
    picker.box = box
    picker.title:SetText(title or "Who gets paid?")
    local me = FullName("player") or "me"
    local entries = {}
    picker.sub:SetText(withDefaults and ("Default: " .. DefaultPayeeText(key)) or "")
    local top = withDefaults and 44 or 30
    if only then
        -- that class only, from the group or raid; a pick is added to the list
        for _, m in ipairs(GroupSnapshot()) do
            if (m.class == only or (only == "ANY" and not m.me and not m.customer)) then entries[#entries + 1] = { Colored(m.me and (m.name .. " (you)") or m.name, m.class) .. (m.zone and ("  (" .. m.zone .. ")") or ""), m.name } end
        end
    elseif withDefaults then
        entries[#entries + 1] = { "Default", "" }
        entries[#entries + 1] = { "Me (" .. me .. ")", "me" }
    else
        entries[#entries + 1] = { "Me (" .. me .. ")", me }
    end
    if not only then
        for _, m in ipairs(GroupSnapshot()) do
            if not m.me then entries[#entries + 1] = { Colored(m.name, m.class) .. (m.zone and ("  (" .. m.zone .. ")") or ""), m.name } end
        end
    end
    local W = 300
    for i, e in ipairs(entries) do
        local b = picker.buttons[i]
        if not b then
            b = FlatButton(picker, W - 20, 22, "plain", 13)
            b:GetFontString():ClearAllPoints() b:GetFontString():SetPoint("LEFT", 10, 0)
            picker.buttons[i] = b
        end
        b:SetSize(W - 20, 22)
        b:ClearAllPoints() b:SetPoint("TOPLEFT", 10, -top - (i - 1) * 24)
        b:SetText(e[1])
        b:SetScript("OnClick", function()
            if only then
                local cur = box:GetText() or ""
                local have = false
                for nm in cur:gmatch("[^,]+") do if nm:gsub("^%s+", ""):gsub("%s+$", ""):lower() == e[2]:lower() then have = true end end
                if not have then box:SetText(cur:find("%S") and (cur:gsub("%s+$", "") .. ", " .. e[2]) or e[2]) end
            else
                box:SetText(e[2])
            end
            picker:Hide()
        end)
        b:Show()
    end
    for i = #entries + 1, #picker.buttons do picker.buttons[i]:Hide() end
    local h = top + #entries * 24
    picker.note:ClearAllPoints() picker.note:SetPoint("TOPLEFT", 10, -h - 2)
    local alone = #GroupSnapshot() <= 1
    if only and #entries == 0 then picker.note:SetText(only == "ANY" and "Nobody but customers in your group right now." or "Nobody of that class in your group right now.")
    else picker.note:SetText(alone and "Party and raid members show up here." or (only and "Each pick is added to the list." or "Or type any name in the box.")) end
    picker:SetSize(W, h + 24)
    picker:ClearAllPoints() picker:SetPoint("TOPLEFT", box, "BOTTOMLEFT", -6, -2)
    picker:Show()
end
local function PickButton(parent, box, withDefaults, title, key)
    local b = CreateFrame("Button", nil, parent)
    b:SetSize(24, 24)
    b:SetPoint("LEFT", box, "RIGHT", 2, 0)
    if b.SetNormalTexture then
        b:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIcon-ScrollDown-Up")
        b:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIcon-ScrollDown-Down")
        b:SetHighlightTexture("Interface\\Buttons\\UI-Common-MouseHilight", "ADD")
    end
    b:SetScript("OnClick", function() ShowPicker(box, withDefaults, title, key) end)
    return b
end

local function BuildSetupUI()
    -- The 2026 redesign (design handoff, reviewed 14 Nov 2026): a 960 x 780 window, a rail of six
    -- tabs, two columns of rows (label left, control right), toggles for on/off, segments for a
    -- pick-one, flat inputs whose placeholder says what blank means, and chips that insert a
    -- {token} into the message box. The keys under checks/boxes are unchanged, so Load and Save
    -- (and /si) read and write exactly what they did.
    local RAIL, W, H, HEAD, FOOT = 168, 960, 780, 56, 64
    local PW = W - RAIL
    local w = CreateFrame("Frame", "ServiceInviterSetup", UIParent)
    w:SetSize(W, H)
    w:SetPoint("CENTER", 0, 20)
    w:SetFrameStrata("DIALOG")
    w:SetClampedToScreen(true)
    w:SetMovable(true) w:EnableMouse(true)
    w:RegisterForDrag("LeftButton")
    w:SetScript("OnDragStart", function(self) self:StartMoving() end)
    w:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    local edge = Fill(w, INK.frame, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
    local bg = Fill(w, INK.ground, "BACKGROUND", -7) bg:SetAllPoints()
    w.bg = bg
    local rail = Fill(w, INK.deep, "BACKGROUND", -6) rail:SetPoint("TOPLEFT", 0, 0) rail:SetSize(RAIL, H)
    local railLine = Fill(w, INK.soft, "BORDER") railLine:SetPoint("TOPLEFT", RAIL, 0) railLine:SetSize(1, H)
    local headLine = Fill(w, INK.soft, "BORDER") headLine:SetPoint("TOPLEFT", RAIL + 1, -HEAD) headLine:SetSize(PW - 1, 1)
    local foot = Fill(w, INK.deep, "BACKGROUND", -6) foot:SetPoint("TOPLEFT", RAIL + 1, -(H - FOOT)) foot:SetSize(PW - 1, FOOT)
    local footLine = Fill(w, INK.soft, "BORDER") footLine:SetPoint("TOPLEFT", RAIL + 1, -(H - FOOT)) footLine:SetSize(PW - 1, 1)
    w:Hide()

    local logo = w:CreateTexture(nil, "ARTWORK") logo:SetPoint("TOPLEFT", 18, -20) logo:SetSize(18, 18)
    logo:SetTexture(Jobs.SpellIcon(Jobs.RITUAL_ID, Jobs.RITUAL_ICON))
    local brand = Text(w, 14, INK.gold, "GameFontNormalLarge")
    brand:SetPoint("TOPLEFT", 44, -22) brand:SetText("Service Inviter")
    local title = Text(w, 18, INK.text, "GameFontHighlightLarge")
    title:SetPoint("TOPLEFT", RAIL + 28, -19) title:SetText("General")
    local close = FlatButton(w, 32, 32, "bare", 15)
    close:SetPoint("TOPRIGHT", -12, -12) close:SetText("x")
    close:SetScript("OnClick", function() w:Hide() end)

    local boxes, checks, radios = {}, {}, {}
    local optKeys = {}     -- toggles that simply map to an option
    local page             -- the tab being built
    local C1, C2, CW = 28, 416, 348     -- the two columns on a page, and their width
    local ROW = 36

    -- a section: small caps and a hairline under it
    local function Header(x, y, text, width)
        local fs = Text(page, 11, INK.muted) fs:SetPoint("TOPLEFT", x, y) fs:SetText(text:upper())
        local ln = Fill(page, INK.soft, "BORDER") ln:SetPoint("TOPLEFT", x, y - 18) ln:SetSize(width or CW, 1)
        return fs
    end
    -- a row's label (or, with the small font, a quiet note)
    local function Label(x, y, text, font, width)
        local small = font == "GameFontHighlightSmall"
        local fs = Text(page, small and 12 or 13, small and INK.muted or INK.text)
        fs:SetPoint("TOPLEFT", x, y) fs:SetText(text)
        if width then fs:SetWidth(width) fs:SetJustifyH("LEFT") end
        return fs
    end
    -- a flat input; the placeholder shows while it's empty and says what blank means
    local function Box(key, x, y, width, maxLetters, placeholder)
        local eb = CreateFrame("EditBox", nil, page)
        eb:SetPoint("TOPLEFT", x, y)
        eb:SetSize(width or 300, 30)
        eb:SetAutoFocus(false)
        eb:SetMaxLetters(maxLetters or 255)
        eb:SetFontObject(ChatFontNormal)
        if eb.SetTextInsets then eb:SetTextInsets(8, 8, 0, 0) end
        local e1 = eb:CreateTexture(nil, "BACKGROUND", nil, -2) e1:SetAllPoints() e1:SetColorTexture(RGB(INK.soft))
        local e2 = eb:CreateTexture(nil, "BACKGROUND", nil, -1) e2:SetPoint("TOPLEFT", 1, -1) e2:SetPoint("BOTTOMRIGHT", -1, 1) e2:SetColorTexture(RGB(INK.deep))
        eb._siStyle = "input"
        if placeholder then
            local ph = Text(page, 13, INK.faint) ph:SetPoint("TOPLEFT", x + 9, y - 8) ph:SetText(placeholder)
            ph._siStyle = "ph"
            local function Sync() if eb:GetText() == "" and not (eb.HasFocus and eb:HasFocus()) then ph:Show() else ph:Hide() end end
            eb:HookScript("OnTextChanged", Sync) eb:HookScript("OnEditFocusGained", Sync) eb:HookScript("OnEditFocusLost", Sync)
            eb.placeholder, eb.SyncPlaceholder = ph, Sync
        end
        eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
        eb:SetScript("OnEnterPressed", function(self) self:ClearFocus() end)
        boxes[key] = eb
        return eb
    end
    -- the picker from the group, beside a box
    local function Pick(box, withDefaults, title, key)
        local b = FlatButton(page, 30, 30, "plain", 13)
        b:SetPoint("LEFT", box, "RIGHT", 4, 0) b:SetText("+")
        b:SetScript("OnClick", function() ShowPicker(box, withDefaults, title, key) end)
        Jobs.Tip(b, "Pick from your group")
        return b
    end
    -- a toggle: a 34 x 18 track with a knob; checked = gold, knob right
    local function Check(key, x, y, text, isOpt)
        local cb = CreateFrame("CheckButton", nil, page)
        cb:SetSize(34, 18) cb:SetPoint("TOPLEFT", x, y)
        local track = cb:CreateTexture(nil, "BACKGROUND") track:SetAllPoints()
        local knob = cb:CreateTexture(nil, "ARTWORK") knob:SetSize(12, 12)
        cb._siStyle = "toggle"
        local set = cb.SetChecked
        local function Paint(on)
            track:SetColorTexture(RGB(on and INK.gold or INK.plain))
            knob:SetColorTexture(RGB(on and INK.goldInk or INK.faint))
            knob:ClearAllPoints() knob:SetPoint(on and "RIGHT" or "LEFT", on and -3 or 3, 0)
        end
        cb.SetChecked = function(self, v) set(self, v) Paint(v and true or false) end
        cb:HookScript("OnClick", function(self) Paint(self:GetChecked() and true or false) end)
        Paint(false)
        if text then cb.label = Label(x + 42, y - 1, text) end
        checks[key] = cb
        if isOpt then optKeys[#optKeys + 1] = key end
        return cb
    end
    -- a row with a label on the left and a toggle at the right edge of the column
    local function Toggle(key, col, y, text, isOpt)
        local cb = Check(key, col + CW - 34, y - 6, nil, isOpt)
        cb.label = Label(col, y - 6, text)
        return cb
    end
    -- a segment of a pick-one (radio) or an on/off chip (chip = true): text inside, gold when on
    local function Seg(group, key, x, y, width, text, onPick, chip)
        local cb = CreateFrame("CheckButton", nil, page)
        cb:SetSize(width, 30) cb:SetPoint("TOPLEFT", x, y)
        local e = cb:CreateTexture(nil, "BACKGROUND", nil, -2) e:SetAllPoints()
        local f = cb:CreateTexture(nil, "BACKGROUND", nil, -1) f:SetPoint("TOPLEFT", 1, -1) f:SetPoint("BOTTOMRIGHT", -1, 1)
        local fs = cb:CreateFontString(nil, "OVERLAY", "GameFontHighlight") fs:SetPoint("CENTER")
        cb:SetFontString(fs) cb:SetText(text)
        cb._siStyle = chip and "chipcheck" or "seg"
        local set = cb.SetChecked
        local function Paint(on)
            e:SetColorTexture(RGB(on and (chip and INK.gold or INK.wash) or INK.soft))
            f:SetColorTexture(RGB(on and INK.wash or INK.plain))
            fs:SetTextColor(RGB(on and INK.gold or INK.muted))
        end
        cb.SetChecked = function(self, v) set(self, v) Paint(v and true or false) end
        Paint(false)
        checks[key] = cb
        if group then
            radios[group] = radios[group] or {}
            radios[group][#radios[group] + 1] = cb
            cb:SetScript("OnClick", function()
                for _, other in ipairs(radios[group]) do other:SetChecked(other == cb) end
                if onPick then onPick() end
            end)
        else
            cb:HookScript("OnClick", function(self) Paint(self:GetChecked() and true or false) end)
        end
        return cb
    end
    -- the old radio call, as a segment sized to its words
    local function Radio(group, key, x, y, text, onPick)
        return Seg(group, key, x, y, 20 + #text * 7, text, onPick)
    end
    -- {tokens} that insert into a box, right-aligned to end at `right`
    local function Chips(box, right, y, tokens)
        local x = right
        for i = #tokens, 1, -1 do
            local t = tokens[i]
            local cw = 10 + #t * 6.5
            x = x - cw
            local b = FlatButton(page, cw, 22, "chip", 11)
            b:SetPoint("TOPLEFT", x, y) b:SetText(t)
            b:SetScript("OnClick", function() if box.Insert then box:SetFocus() box:Insert(t) end end)
            x = x - 4
        end
    end
    -- a key cap and a Bind button that waits for the next key you press
    local function KeyBind(x, y, what)
        local cap = FlatButton(page, 44, 30, "plain", 12)
        cap:SetPoint("TOPLEFT", x, y)
        local bind = FlatButton(page, 64, 30, "plain", 13)
        bind:SetPoint("TOPLEFT", x + 50, y) bind:SetText("Bind")
        local button = what == "ad" and "ServiceInviterAdButton" or "ServiceInviterBuffButton"
        local function Show()
            local key = GetBindingKey and GetBindingKey("CLICK " .. button .. ":LeftButton")
            cap:SetText(key or "-")
        end
        bind:SetScript("OnClick", function(self)
            if InCombatLockdown and InCombatLockdown() then P("can't change keys in combat") return end
            self:SetText("Press") self:EnableKeyboard(true)
            self:SetScript("OnKeyDown", function(me, key)
                me:EnableKeyboard(false) me:SetScript("OnKeyDown", nil) me:SetText("Bind")
                if key ~= "ESCAPE" then SlashCmdList.SERVICEINVITER("bind " .. what .. " " .. key) end
                Show()
            end)
        end)
        Show()
        return cap, Show
    end
    -- the payee for a service: Default (the General tab) / Doer / Me, or a name typed in the box
    local function PaidRow(k, col, y)
        Label(col, y - 6, "Paid")
        local x = col + 44
        Seg("payee_" .. k, k .. "pd_default", x, y, 64, "Default") x = x + 64
        Seg("payee_" .. k, k .. "pd_doer", x, y, 52, "Doer") x = x + 52
        Seg("payee_" .. k, k .. "pd_me", x, y, 40, "Me") x = x + 46
        local pb = Box(k .. "payee", x, y, col + CW - 34 - x, 40, "Name")
        Pick(pb, true, "Who gets paid?", k:match("^svc_(.-)_$"))
        -- a typed name wins over the segments
        pb:HookScript("OnTextChanged", function(self)
            if self:GetText():gsub("%s", "") ~= "" then for _, c in ipairs(radios["payee_" .. k]) do c:SetChecked(false) end end
        end)
    end
    -- one service: on, price (blank = free), invite, words, who gets paid
    local function Service(key, col, y)
        local def = Core.BY_KEY[key]
        local k = "svc_" .. key .. "_"
        Toggle(k .. "on", col, y, (def.kind == "buff" and "We offer " or "We sell ") .. def.label)
        y = y - ROW
        Label(col, y - 6, "Price")
        Box(k .. "g", col + CW - 152, y, 52, 5, "0") Label(col + CW - 96, y - 7, "|cff" .. INK.gold .. "g|r")
        Box(k .. "s", col + CW - 78, y, 52, 2, "free") Label(col + CW - 20, y - 7, "|cff" .. INK.silver .. "s|r")
        y = y - ROW
        Toggle(k .. "invite", col, y, "Invite buyers")
        y = y - ROW
        PaidRow(k, col, y)
        return y - ROW
    end

    -- tabs ----------------------------------------------------------------
    -- summons and blessings only (the owner, 14 Nov 2026: "we are only summoning and sometimes
    -- doing a blessing but not much else")
    local TABS = { "General", "Warlock", "Paladin", "Advertise", "Team", "Tools" }
    local pages, tabBtns = {}, {}
    -- the side menu: the page you're on is gold, with a bar beside it
    local railBar
    local function ShowTab(i)
        for j, pg in ipairs(pages) do
            local on = j == i
            if on then pg:Show() else pg:Hide() end
            local b = tabBtns[j]
            b._siStyle = on and "railOn" or "rail"
            b:GetFontString():SetTextColor(RGB(on and INK.gold or INK.text))
            if on then b.sel:Show() else b.sel:Hide() end
        end
        railBar:ClearAllPoints() railBar:SetPoint("TOPLEFT", 0, -72 - (i - 1) * 44)
        title:SetText(TABS[i])
        w.tab = i
    end
    for i, name in ipairs(TABS) do
        local pg = CreateFrame("Frame", nil, w)
        pg:SetPoint("TOPLEFT", RAIL, 0) pg:SetSize(PW, H - FOOT)
        pages[i] = pg
        local sel = Fill(w, INK.panel, "BACKGROUND", -5) sel:SetPoint("TOPLEFT", 0, -72 - (i - 1) * 44) sel:SetSize(RAIL, 40)
        local b = FlatButton(w, RAIL, 40, "rail", 14)
        b:SetPoint("TOPLEFT", 0, -72 - (i - 1) * 44)
        b:GetFontString():ClearAllPoints() b:GetFontString():SetPoint("LEFT", 24, 0)
        b:SetText(name)
        b:SetScript("OnClick", function() ShowTab(i) end)
        b.sel = sel
        tabBtns[i] = b
    end
    railBar = Fill(w, INK.gold, "ARTWORK") railBar:SetSize(3, 40)
    w.pages, w.tabBtns, w.ShowTab, w.tab = pages, tabBtns, ShowTab, 1
    local TOP = -84            -- the first section on every page

    -- General: who gets invited, who gets paid, the messages ---------------
    page = pages[1]
    local y = TOP
    Header(C1, y, "Invite") y = y - 28
    Toggle("enabled", C1, y, "Invite buyers", true) y = y - ROW
    Label(C1, y - 6, "Listen")
    Seg(nil, "yell", C1 + CW - 54, y, 54, "Yell", nil, true)
    Seg(nil, "say", C1 + CW - 106, y, 48, "Say", nil, true)
    Seg(nil, "general", C1 + CW - 184, y, 74, "General", nil, true)
    Seg(nil, "trade", C1 + CW - 248, y, 60, "Trade", nil, true)
    for _, k in ipairs({ "trade", "general", "say", "yell" }) do optKeys[#optKeys + 1] = k end
    y = y - ROW
    Label(C1, y - 6, "Also") Box("chanextra", C1 + 112, y, CW - 112, 100, "Other channels") y = y - ROW
    Toggle("strictbuy", C1, y, "WTB only", true) y = y - ROW
    Toggle("fragments", C1, y, "Merge split messages", true) y = y - ROW
    Toggle("skipafk", C1, y, "Skip when AFK", true) y = y - ROW
    -- how soon the same buyer can be invited again (the owner, 14 Nov 2026: "let's make re-invite
    -- setting adjustable in UI as well"); in minutes here, /si cooldown takes seconds
    Label(C1, y - 6, "Re-invite after") Box("cooldown", C1 + CW - 92, y, 56, 4, "180") Label(C1 + CW - 30, y - 7, "sec", "GameFontHighlightSmall") y = y - ROW
    Toggle("announce", C1, y, "Chat line on invite", true) y = y - ROW
    Toggle("autoshow", C1, y, "Open list on invite", true) y = y - ROW
    Label(C1, y - 6, "Auto-invite") Box("kwwords", C1 + 112, y, CW - 112 - 46, 60, "inv, invite")
    Check("kwon", C1 + CW - 34, y - 6, nil, true) y = y - ROW - 12
    Header(C1, y, "On sale") y = y - 28
    w.onsale = Label(C1, y - 4, "", nil, CW) y = y - 48
    -- the addon's own lines in a chat tab of their own (the owner, 14 Nov 2026: "i still want to be
    -- able to put the SI stuff in a separate chat window i can customize"): a tab named SI is
    -- used by itself; this makes one. Size, font and place are the game's own tab settings.
    Header(C1, y, "My lines go to") y = y - 28
    w.outWhere = Label(C1, y - 6, "", nil, CW - 140)
    local mk = FlatButton(page, 132, 30, "plain", 13)
    mk:SetPoint("TOPLEFT", C1 + CW - 132, y) mk:SetText("Make SI tab")
    mk:SetScript("OnClick", function() Jobs.MakeTab() w.Refresh() end)
    w.makeTab = mk

    y = TOP
    Header(C2, y, "Pay") y = y - 28
    local function SyncTradeBox()
        local named = checks.pay_name and checks.pay_name:GetChecked()
        if named then checks.autotrade:Disable() else checks.autotrade:Enable() end
        if checks.autotrade.label then checks.autotrade.label:SetTextColor(RGB(named and INK.faint or INK.text)) end
    end
    Label(C2, y - 6, "Paid")
    Seg("pay", "pay_place", C2 + 44, y, 56, "Doer", SyncTradeBox)
    Seg("pay", "pay_me", C2 + 100, y, 44, "Me", SyncTradeBox)
    Seg("pay", "pay_name", C2 + 144, y, 58, "Name", SyncTradeBox)
    local pn = Box("payname", C2 + 208, y, CW - 208 - 34, 40, "Name")
    Pick(pn, false, "Who always gets paid?")
    y = y - ROW
    Toggle("autotrade", C2, y, "Auto-open trade") y = y - ROW
    Toggle("marks", C2, y, "Raid icon on whoever does it", true) y = y - ROW - 12
    Header(C2, y, "Messages") y = y - 28
    local function Msg(key, text, tokens, toggleKey, placeholder, tokensBelow)
        Label(C2, y - 4, text)
        if toggleKey then Check(toggleKey, C2 + CW - 34, y - 3) end
        if tokens and not tokensBelow then Chips(nil, C2 + CW - (toggleKey and 42 or 0), y, tokens) end
        y = y - 26
        local b = Box(key, C2, y, CW, 255, placeholder)
        y = y - 34
        if tokens and tokensBelow then Chips(b, C2 + CW, y, tokens) y = y - 26 end
        return b
    end
    -- chips before the box exists insert into it, so wire them after
    -- each message: its name and {token} chips on one line, then the box with its on/off right
    -- beside it (the owner, 14 Nov 2026: "seems very confusing to have a toggle for welcome and
    -- pay but it isn't next to the actual message we send")
    local function MsgChips(key, text, tokens, toggleKey, placeholder, isOpt, below)
        Label(C2, y - 4, text)
        local y0 = y
        y = y - 26
        local b = Box(key, C2, y, toggleKey and (CW - 44) or CW, 255, placeholder)
        if toggleKey then Check(toggleKey, C2 + CW - 34, y - 6, nil, isOpt) end
        y = y - 40
        -- a long list of chips goes under the box
        if tokens and below then Chips(b, C2 + CW, y + 6, tokens) y = y - 24
        elseif tokens then Chips(b, C2 + CW, y0, tokens) end
        return b
    end
    MsgChips("welcomemsg", "Welcome", { "{name}", "{service}", "{dest}", "{price}", "{payee}", "{visits}" }, "welcome", "Auto", nil, true)
    MsgChips("offermsg", "Arrival", { "{name}", "{here}", "{offers}" }, nil, "Auto")
    MsgChips("paymsg", "Pay reminder", { "{here}", "{payee}", "{price}" }, "payremind", "Auto", true)
    MsgChips("thanksmsg", "Done", { "{name}" }, "thanks", "Off")
    MsgChips("loyaltymsg", "Regular", { "{name}", "{visits}" }, nil, "Off")
    MsgChips("scammsg", "Didn't pay", { "{name}", "{skull}" }, nil, "Off")

    -- Warlock --------------------------------------------------------------
    page = pages[2]
    y = TOP
    Header(C1, y, "Sell") y = y - 28
    y = Service("summons", C1, y) - 12
    Header(C1, y, "Who summons") y = y - 28
    Seg("role", "rolelock", C1, y, 120, "I summon")
    Seg("role", "rolehelper", C1 + 120, y, 150, "Friend summons")
    y = y - ROW - 12
    -- following the market, channel by channel: the price above is the max; never below the min
    -- (the owner, 14 Nov 2026: "each service will work with default min and max ... we dont want
    -- to offer below the min and we want to offer the max when possible")
    Header(C1, y, "Other sellers") y = y - 28
    Label(C1, y - 6, "Cheaper rival")
    Seg("pricemode", "pm_ignore", C1 + 112, y, 64, "Ignore")
    Seg("pricemode", "pm_match", C1 + 176, y, 60, "Match")
    Seg("pricemode", "pm_undercut", C1 + 236, y, 72, "Undercut")
    y = y - ROW
    Label(C1, y - 6, "Undercut by") Box("undercut", C1 + CW - 78, y, 52, 4, "5") Label(C1 + CW - 20, y - 7, "|cff" .. INK.silver .. "s|r") y = y - ROW
    Label(C1, y - 6, "Never below") Box("floor", C1 + CW - 152, y, 126, 4, "Never moves") Label(C1 + CW - 20, y - 7, "|cff" .. INK.silver .. "s|r")
    w.priceFrom = Label(C1, y - 46, "", "GameFontHighlightSmall", CW)

    y = TOP
    Header(C2, y, "Warlocks") y = y - 28
    -- one card per warlock in the group: who, and where they summon to (cities are read from the
    -- game; one it can't place sells nothing, so the card says so)
    w.lockCards = {}
    for i = 1, 4 do
        local cy = y - (i - 1) * 40
        local card = Fill(page, INK.panel, "BACKGROUND", -4) card:SetPoint("TOPLEFT", C2, cy) card:SetSize(CW, 34)
        local nm = Text(page, 13, INK.text) nm:SetPoint("TOPLEFT", C2 + 12, cy - 10) nm:SetWidth(130) nm:SetJustifyH("LEFT")
        local where = Text(page, 13, INK.muted) where:SetPoint("TOPLEFT", C2 + 148, cy - 10) where:SetWidth(CW - 160) where:SetJustifyH("LEFT")
        w.lockCards[i] = { card, nm, where }
    end
    w.locks = Label(C2, y - 162, "", "GameFontHighlightSmall", CW)
    Label(C2, y - 186, "Only these sell", "GameFontHighlightSmall")
    y = y - 206
    local pb = Box("prov_WARLOCK", C2, y, CW - 34, 200, "Any warlock in the group")
    Pick(pb, false, "Our warlocks (from your group)", "class:WARLOCK")
    y = y - ROW
    Toggle("countshards", C2, y, "Count shards", true) y = y - ROW - 12
    Header(C2, y, "When a summon starts") y = y - 28
    Label(C2, y - 4, "Raid line") Check("raidalert", C2 + CW - 34, y - 3)
    y = y - 26
    local am = Box("alertmsg", C2, y, CW, 255) y = y - 34
    Chips(am, C2 + CW, y, { "{name}", "{dest}", "{payee}", "{price}" }) y = y - 34
    Label(C2, y - 6, "Whisper to") Box("whisperto", C2 + 112, y, CW - 112, 40, "Nobody") y = y - ROW
    Label(C2, y - 4, "Whisper")
    local wm
    y = y - 26
    wm = Box("whispermsg", C2, y, CW, 255) y = y - 34
    Chips(wm, C2 + CW, y, { "{name}", "{next}" })

    -- Paladin --------------------------------------------------------------
    page = pages[3]
    y = TOP
    Header(C1, y, "Sell") y = y - 28
    y = Service("blessing", C1, y) - 12
    Header(C1, y, "Words") y = y - 28
    Box("svc_blessing_words", C1, y, CW, 200, "bless, blessing, buff") y = y - ROW - 4
    -- the word they use picks the blessing; this is only for a plain "blessing" (the owner,
    -- 13 Nov 2026: "can it not detect what they want? i have to have only blessing of might?")
    Label(C1, y - 6, "Just \"blessing\"") y = y - 30
    local BLESSINGS = { "Might", "Wisdom", "Kings", "Salvation", "Light", "Sanctuary" }
    for i, b in ipairs(BLESSINGS) do
        local col, line = (i - 1) % 3, math.floor((i - 1) / 3)
        Seg("bspell", "bs_" .. b:lower(), C1 + col * 116, y - line * 34, 116, b)
    end
    y = TOP
    Header(C2, y, "Casting") y = y - 28
    Toggle("buffarrivals", C2, y, "Buff them on landing, unasked", true) y = y - ROW
    Toggle("buffpop", C2, y, "Pop the button at my mouse", true) y = y - ROW
    Label(C2, y - 6, "Buff key")
    local _, showBuffKey = KeyBind(C2 + CW - 114, y, "buff")
    w.showBuffKey = showBuffKey

    -- Advertise --------------------------------------------------------------
    page = pages[4]
    local FW = PW - 56
    y = TOP
    Header(C1, y, "Ad", FW) y = y - 28
    Label(C1, y - 4, "Text") y = y - 26
    local ad = Box("admsg", C1, y, FW, 255) y = y - 34
    Chips(ad, C1 + FW, y + 60, { "{wts}", "{services}" })
    Label(C1, y - 8, "Preview", "GameFontHighlightSmall")
    local pvBg = Fill(page, INK.deep, "BACKGROUND", -4) pvBg:SetPoint("TOPLEFT", C1 + 80, y) pvBg:SetSize(FW - 80, 30)
    w.adpreview = Text(page, 13, "ffc0c0")
    w.adpreview:SetPoint("TOPLEFT", C1 + 90, y - 8) w.adpreview:SetWidth(FW - 100) w.adpreview:SetJustifyH("LEFT")
    if w.adpreview.SetWordWrap then w.adpreview:SetWordWrap(false) end
    y = y - ROW - 12
    Header(C1, y, "Channels", FW) y = y - 28
    Label(C1, y - 6, "Post in")
    Seg(nil, "adch_trade", C1 + FW - 340, y, 64, "Trade", nil, true)
    Seg(nil, "adch_general", C1 + FW - 270, y, 80, "General", nil, true)
    Box("adextra", C1 + FW - 184, y, 184, 100, "Other channels")
    y = y - ROW
    Label(C1, y - 6, "Wait") Box("adwait", C1 + FW - 150, y, 56, 3, "5") Label(C1 + FW - 88, y - 7, "min / channel", "GameFontHighlightSmall")
    y = y - ROW - 12
    Header(C1, y, "Post", FW) y = y - 30
    local post = FlatButton(page, 220, 44, "gold", 15)
    post:SetPoint("TOPLEFT", C1, y) post:SetText("Post ad")
    post:SetScript("OnClick", function() w.Save() PostAd() w.Load() end)
    Jobs.Tip(post, "The game sends an ad only on a key press or click: one press, one ad")
    w.adpost = post
    local _, showAdKey = KeyBind(C1 + 236, y - 7, "ad")
    w.showAdKey = showAdKey

    -- Team -------------------------------------------------------------------
    page = pages[5]
    y = TOP
    Header(C1, y, "Team", FW) y = y - 28
    Label(C1, y - 6, "Guild is the team") Check("guildteam", C1 + FW - 34, y - 6, nil, true) y = y - ROW
    -- one list for everyone who's ours outside the guild, addon or not: never a customer, and any
    -- of them running the addon shares with us (the owner, 14 Nov 2026: "workers is in multiple
    -- places, like in the Team and General screen")
    Label(C1, y - 6, "Ours, outside the guild")
    local tb = Box("team", C1 + 300, y, FW - 334, 400, "Names: never customers")
    boxes.workers = tb
    Pick(tb, false, "Ours (from your group)", "workers") y = y - ROW
    Label(C1, y - 6, "Point of contact")
    local pb2 = Box("poc", C1 + 300, y, FW - 334, 200, "Each works solo")
    Pick(pb2, false, "Point of contact (from your group)", "workers") y = y - ROW
    w.teamStatus = Label(C1, y - 4, "", nil, FW) y = y - 22
    w.teamBooks = Label(C1, y - 4, "", "GameFontHighlightSmall", FW) y = y - 34
    Header(C1, y, "Where each message goes", FW) y = y - 28
    local cols = { { "whisper", "Whisper" }, { "group", "Party" }, { "off", "Off" } }
    for i, c in ipairs(cols) do
        local h = Text(page, 11, INK.muted) h:SetPoint("TOPLEFT", C1 + 300 + (i - 1) * 146, y) h:SetWidth(140) h:SetText(c[2]:upper())
    end
    y = y - 22
    for _, kind in ipairs(Jobs.ROUTE_KINDS) do
        Label(C1, y - 7, Jobs.ROUTE_LABEL[kind])
        for i, c in ipairs(cols) do
            Seg("route_" .. kind, "route_" .. kind .. "_" .. c[1], C1 + 300 + (i - 1) * 146, y, 140, c[2])
        end
        y = y - 34
    end

    -- Tools: every command (the owner, 14 Nov 2026: "i want the addon to have a debug
    -- panel/command panel or something - there are too many to remember"). Each runs the same
    -- /si command you could type.
    page = pages[6]
    local function Run(cmd) w.Save() SlashCmdList.SERVICEINVITER(cmd) w.Load() end
    w.tools = {}
    local function Tool(x, y0, width, text, cmd, style)
        local b = FlatButton(page, width, 32, style or "plain", 13)
        b:SetPoint("TOPLEFT", x, y0) b:SetText(text)
        b:SetScript("OnClick", function() Run(type(cmd) == "function" and cmd() or cmd) end)
        w.tools[text] = b
        return b
    end
    local function Named(cmd) return function() return cmd .. " " .. (boxes.toolname:GetText():gsub("^%s+", ""):gsub("%s+$", "")) end end
    local function Target() local t = boxes.testtarget:GetText():gsub("^%s+", ""):gsub("%s+$", "") return t end
    y = TOP
    Header(C1, y, "Run") y = y - 28
    -- each toggle runs the command, which does more than flip a value (stop also closes the list;
    -- selling also brings back the auto-invite words; test mode takes whoever is in the box)
    local function RunToggle(key, text, on, off)
        local cb = Toggle(key, C1, y, text)
        cb:HookScript("OnClick", function(self) Run(self:GetChecked() and on() or off()) end)
        w.tools[text] = cb
        y = y - ROW
        return cb
    end
    RunToggle("running", "Running", function() return "start" end, function() return "stop" end)
    RunToggle("selling", "Selling", function() return "on" end, function() return "off" end)
    RunToggle("dryrun", "Test mode", function() local t = Target() return t ~= "" and ("test " .. t) or "test" end, function() return "test off" end)
    Toggle("near", C1, y, "Near-miss lines") y = y - ROW
    Toggle("debug", C1, y, "Debug") y = y - ROW
    Label(C1, y - 6, "Test whispers to")
    local tt = Box("testtarget", C1 + 140, y, CW - 174, 40, "You")
    Pick(tt, false, "Test whispers go to")
    y = y - ROW - 12
    Header(C1, y, "Session") y = y - 28
    w.sessTiles = {}
    for i, lbl in ipairs({ "Collected", "Expected", "Collected %" }) do
        local tx = C1 + (i - 1) * 118
        local tile = Fill(page, INK.panel, "BACKGROUND", -4) tile:SetPoint("TOPLEFT", tx, y) tile:SetSize(110, 56)
        local l = Text(page, 11, INK.muted) l:SetPoint("TOPLEFT", tx + 12, y - 10) l:SetText(lbl:upper())
        local v = Text(page, 17, INK.text) v:SetPoint("TOPLEFT", tx + 12, y - 28)
        w.sessTiles[i] = v
    end
    w.sessText = w.sessTiles[1]
    y = y - 66
    Tool(C1, y, 124, "New session", "session new")
    Tool(C1 + 130, y, 90, "Self-test", "selftest")
    Tool(C1 + 226, y, 122, "Team messages", "teamlog")

    y = TOP
    Header(C2, y, "Someone by name") y = y - 28
    local tn = Box("toolname", C2, y, CW - 34, 40, "Name")
    Pick(tn, false, "Someone by name")
    y = y - ROW - 4
    Tool(C2, y, 171, "Why", Named("why")) Tool(C2 + 177, y, 171, "History", Named("customers")) y = y - 38
    Tool(C2, y, 171, "Didn't pay", Named("scam"), "danger") Tool(C2 + 177, y, 171, "Paid after all", Named("unscam")) y = y - 38
    Tool(C2, y, 171, "Add to team", Named("team add")) Tool(C2 + 177, y, 171, "Remove from team", Named("team remove")) y = y - 38 - 12
    Header(C2, y, "Lists") y = y - 28
    Tool(C2, y, 171, "Open lists", "lists")
    local test = FlatButton(page, 171, 32, "plain", 13)
    test:SetPoint("TOPLEFT", C2 + 177, y) test:SetText("Test banner")
    test:SetScript("OnClick", function() ShowAlert("CLICK PORTAL", "Testy  »  Thunder Bluff  ·  Pay you", "TEST · SUMMONING") end)
    y = y - 44
    Label(C2, y, "Every button is also /si and the word.", "GameFontHighlightSmall", CW)

    local DEFAULTS_BY_KEY = {
        welcomemsg = "", offermsg = "", paymsg = "", thanksmsg = MSG.THANKS, loyaltymsg = MSG.LOYALTY, scammsg = MSG.SCAM, alertmsg = MSG.ALERTMSG, whispermsg = MSG.WHISPERMSG, admsg = MSG.AD,
    }

    local function Refresh()
        local items = Core.OnSale(ServiceInviterDB, GroupSnapshot(), Faction())
        local parts = {}
        for _, it in ipairs(items) do
            local what = it.def.label
            if it.def.kind == "summon" then what = it.where and ("summons to " .. Core.Short(it.where)) or "summons (where? not invited)" end
            if it.def.kind == "portal" then
                local c = {}
                for _, city in ipairs(it.cities) do c[#c + 1] = Core.Short(city) end
                what = "portals to " .. table.concat(c, "/")
            end
            parts[#parts + 1] = what .. " (" .. MemberName(it.provider) .. ")"
        end
        w.onsale:SetText(#parts > 0 and table.concat(parts, ", ") or ("|cff" .. INK.faint .. "Nothing: nobody in the group can do what's on|r"))
        -- the warlock cards
        local locks = Core.Providers(GroupSnapshot(), "summons")
        for i, c in ipairs(w.lockCards) do
            local m = locks[i]
            for _, part in ipairs(c) do if m then part:Show() else part:Hide() end end
            if m then
                c[2]:SetText(Colored(m.me and "You" or m.name, m.class))
                c[3]:SetText(m.zone and ("» " .. m.zone) or ("|cff" .. INK.warn .. "city unknown, not inviting|r"))
            end
        end
        w.locks:SetText(#locks == 0 and "No warlock in the group who can summon." or (#locks > #w.lockCards and ("+" .. (#locks - #w.lockCards) .. " more") or ""))
        local text, why = Core.BuildAd(ServiceInviterDB, GroupSnapshot(), Faction(), ServiceInviterDB.admsg)
        local chName = Jobs.AdChannelName and Jobs.AdChannelName() or "Trade"
        w.adpreview:SetText(text and ("[" .. chName .. "] " .. FullName("player") .. ": " .. text) or ("|cff" .. INK.faint .. "no ad: " .. tostring(why) .. "|r"))
        local ci = ChatTypeInfo and ChatTypeInfo.CHANNEL
        if ci and ci.r then w.adpreview:SetTextColor(ci.r, ci.g, ci.b) end
        local label, ready = AdLabel()
        w.adpost:SetText(label)
        if ready then w.adpost:Enable() else w.adpost:Disable() end
        if w.adpost.SetAlpha then w.adpost:SetAlpha(ready and 1 or 0.55) end
        local st = Stats()
        w.sessTiles[1]:SetText(Jobs.MoneyShort(st.silver or 0))
        w.sessTiles[2]:SetText(Jobs.MoneyShort(st.ev or 0))
        w.sessTiles[3]:SetText(((st.ev or 0) > 0 and math.floor((st.silver or 0) * 100 / st.ev + 0.5) or 0) .. "%")
        w.showAdKey() w.showBuffKey()
        local of = OutFrame()
        local tabName = of and of ~= DEFAULT_CHAT_FRAME and GetChatWindowInfo and of.GetID and GetChatWindowInfo(of:GetID())
        w.outWhere:SetText(tabName and ("The " .. tabName .. " chat tab") or "Your main chat")
        local _, from = Jobs.TeamPrices("summons")
        w.priceFrom:SetText(from and ("|cff" .. INK.gold .. "Prices now: " .. from .. "'s|r (point of contact). Yours are used when they're offline.") or "")
    end
    w.Refresh = Refresh

    function w.Load()
        local db = ServiceInviterDB
        for key, def in pairs(DEFAULTS_BY_KEY) do
            local v = db[key]
            if key == "welcomemsg" and v == MSG.WELCOME then v = nil end
            if key == "offermsg" and v == MSG.OFFERMSG then v = nil end
            boxes[key]:SetText(v or def) boxes[key]:SetCursorPosition(0)
        end
        boxes.whisperto:SetText(WhisperTo() or "")
        boxes.kwwords:SetText(db.kwwords or MSG.KEYWORDS) boxes.kwwords:SetCursorPosition(0)
        boxes.cooldown:SetText(tostring(tonumber(db.cooldown) or 180))
        boxes.chanextra:SetText(type(db.chanextra) == "string" and db.chanextra or MSG.CHANNELS) boxes.chanextra:SetCursorPosition(0)
        boxes.adextra:SetText(db.adextra or "")
        boxes.adwait:SetText(tostring(tonumber(db.adwait) or 5))
        local adch = type(db.adchans) == "table" and db.adchans or { trade = true }
        checks.adch_trade:SetChecked(adch.trade and true or false)
        checks.adch_general:SetChecked(adch.general and true or false)
        checks.raidalert:SetChecked(db.raidalert ~= false)
        checks.autotrade:SetChecked(db.autotrade ~= false)
        checks.welcome:SetChecked(Opt("welcome") and true or false)
        checks.thanks:SetChecked(db.thanks ~= false)
        for _, k in ipairs(optKeys) do checks[k]:SetChecked(Opt(k) and true or false) end
        checks.rolehelper:SetChecked(Role() == "helper")
        checks.rolelock:SetChecked(Role() == "lock")
        checks.dryrun:SetChecked(db.dryrun and true or false)
        checks.running:SetChecked(not db.stasis)
        checks.selling:SetChecked(Opt("enabled") and true or false)
        checks.near:SetChecked(db.near ~= false)
        checks.debug:SetChecked(db.debug and true or false)
        -- who gets paid by default
        local d = type(db.payee) == "table" and db.payee or {}
        local mode = d.mode or (db.collect == true and "me") or (db.collect == false and "notme") or "provider"
        checks.pay_place:SetChecked(mode == "place" or mode == "notme" or mode == "provider")
        checks.pay_me:SetChecked(mode == "me")
        checks.pay_name:SetChecked(mode == "name")
        boxes.payname:SetText(d.name or "")
        -- every service
        for _, def in ipairs(Core.SERVICES) do
            local st, k = Core.Setting(db, def.key), "svc_" .. def.key .. "_"
            checks[k .. "on"]:SetChecked(st.on)
            checks[k .. "invite"]:SetChecked(st.invite)
            if st.price then
                local g, sv = math.floor(st.price / 100), st.price % 100
                boxes[k .. "g"]:SetText(g > 0 and tostring(g) or "")
                boxes[k .. "s"]:SetText((sv > 0 or g == 0) and tostring(sv) or "")
            else
                boxes[k .. "g"]:SetText("") boxes[k .. "s"]:SetText("")
            end
            if boxes[k .. "words"] then boxes[k .. "words"]:SetText(st.words or "") boxes[k .. "words"]:SetCursorPosition(0) end
            -- Default (blank) / Doer / Me, or a name in the box
            local pv = st.payee or ""
            local seg = (pv == "" and "default") or ((pv == "provider" or pv == "place" or pv == "notme") and "doer") or (pv == "me" and "me") or nil
            boxes[k .. "payee"]:SetText(seg and "" or pv)
            for _, s2 in ipairs({ "default", "doer", "me" }) do checks[k .. "pd_" .. s2]:SetChecked(seg == s2) end
        end
        local spell = Core.Setting(db, "blessing").spell or "Blessing of Might"
        for _, c in ipairs(radios.bspell) do c:SetChecked(spell:lower():find(c:GetText():lower(), 1, true) ~= nil) end
        local sm = (type(db.services) == "table" and db.services.summons) or {}
        local mode = Jobs.PriceMode(sm)
        checks.pm_undercut:SetChecked(mode == "undercut") checks.pm_match:SetChecked(mode == "match") checks.pm_ignore:SetChecked(mode == "ignore")
        boxes.undercut:SetText(tostring(sm.undercut or 5))
        boxes.floor:SetText(sm.floor and tostring(sm.floor) or "")
        local prov = type(db.providers) == "table" and db.providers or {}
        boxes.prov_WARLOCK:SetText(prov.WARLOCK or "")
        -- the team list and the old workers list, as one
        local wl, seen = {}, {}
        for _, nm in ipairs(Jobs.TeamMembers()) do if not seen[nm:lower()] then seen[nm:lower()] = true wl[#wl + 1] = nm end end
        for k in pairs(type(db.workers) == "table" and db.workers or {}) do if not seen[k:lower()] then seen[k:lower()] = true wl[#wl + 1] = k end end
        table.sort(wl)
        boxes.team:SetText(table.concat(wl, ", "))
        boxes.poc:SetText((type(db.team) == "table" and db.team.poc) or "")
        for _, kind in ipairs(Jobs.ROUTE_KINDS) do
            local r = Jobs.RouteOf(kind)
            for _, opt in ipairs({ "whisper", "group", "off" }) do checks["route_" .. kind .. "_" .. opt]:SetChecked(r == opt) end
        end
        local poc = Jobs.POC()
        local online = {}
        for _, nm in ipairs(Jobs.TeamPeople()) do if Jobs.Online(nm) then online[#online + 1] = nm end end
        w.teamStatus:SetText(not Jobs.TeamOn() and "No team: working solo." or
            ("Online: " .. (#online > 0 and table.concat(online, ", ") or "nobody yet") .. ".  Point of contact now: " .. (poc or "nobody (each works solo)") .. "."))
        w.teamBooks:SetText(Jobs.BooksLine())
        SyncTradeBox()
        for _, b in pairs(boxes) do if b.SyncPlaceholder then b.SyncPlaceholder() end end
        Refresh()
    end

    function w.Save()
        local db = ServiceInviterDB
        for key, def in pairs(DEFAULTS_BY_KEY) do
            local v = boxes[key]:GetText()
            if (key == "loyaltymsg" or key == "scammsg") and v == "" then db[key] = ""   -- empty = off
            elseif v == "" or v == def then db[key] = nil else db[key] = v end
        end
        local who = (boxes.whisperto:GetText():gsub("%s+", ""))
        db.whisperto = (who == "") and false or who
        db.raidalert = checks.raidalert:GetChecked() and true or false
        db.autotrade = checks.autotrade:GetChecked() and true or false
        SetOpt("welcome", checks.welcome:GetChecked() and true or false)
        db.thanks = checks.thanks:GetChecked() and true or false
        for _, k in ipairs(optKeys) do SetOpt(k, checks[k]:GetChecked() and true or false) end
        do local n = tonumber(boxes.cooldown:GetText()) if n and n >= 0 then db.cooldown = math.floor(n + 0.5) end end
        do local kws = boxes.kwwords:GetText() db.kwwords = (kws:gsub("[%s,]", "") == "" or kws == MSG.KEYWORDS) and nil or kws end
        db.chanextra = boxes.chanextra:GetText()
        db.adextra = boxes.adextra:GetText()
        db.adwait = tonumber(boxes.adwait:GetText()) or 5
        db.adchans = { trade = checks.adch_trade:GetChecked() and true or false, general = checks.adch_general:GetChecked() and true or false }
        db.role = checks.rolelock:GetChecked() and "lock" or "helper"
        db.dryrun = checks.dryrun:GetChecked() and true or false
        db.near = checks.near:GetChecked() and true or false
        db.debug = checks.debug:GetChecked() and true or false
        debugOn = db.debug
        local mode = checks.pay_me:GetChecked() and "me" or (checks.pay_name:GetChecked() and "name" or "provider")
        db.payee = { mode = mode, name = (boxes.payname:GetText():gsub("^%s+", ""):gsub("%s+$", "")) }
        db.collect = nil   -- replaced by "who gets paid"
        db.services = db.services or {}
        for _, def in ipairs(Core.SERVICES) do
            local k = "svc_" .. def.key .. "_"
            local g, sv = tonumber(boxes[k .. "g"]:GetText()), tonumber(boxes[k .. "s"]:GetText())
            local saved = db.services[def.key] or {}
            saved.on = checks[k .. "on"]:GetChecked() and true or false
            saved.invite = checks[k .. "invite"]:GetChecked() and true or false
            saved.price = (g or sv) and ((g or 0) * 100 + (sv or 0)) or false
            if boxes[k .. "words"] then saved.words = boxes[k .. "words"]:GetText() end
            local typed = (boxes[k .. "payee"]:GetText():gsub("^%s+", ""):gsub("%s+$", ""))
            saved.payee = (typed ~= "" and typed) or (checks[k .. "pd_doer"]:GetChecked() and "provider") or
                (checks[k .. "pd_me"]:GetChecked() and "me") or ""
            db.services[def.key] = saved
        end
        local sm = db.services.summons
        sm.mode = (checks.pm_match:GetChecked() and "match") or (checks.pm_undercut:GetChecked() and "undercut") or "ignore"
        sm.match = nil
        sm.undercut = tonumber(boxes.undercut:GetText()) or 5
        sm.floor = tonumber(boxes.floor:GetText())   -- blank = no floor = it never moves
        local bs
        for _, c in ipairs(radios.bspell) do if c:GetChecked() then bs = "Blessing of " .. c:GetText() end end
        db.services.blessing.spell = bs
        db.providers = {}
        local t = boxes.prov_WARLOCK:GetText():gsub("^[%s,]+", ""):gsub("[%s,]+$", "")
        db.providers.WARLOCK = (t ~= "") and t or nil
        -- where each message goes: only what differs from the default the form showed is kept, so
        -- the defaults can follow the team (whispers) when you're on one
        db.route = nil
        local route = {}
        for _, kind in ipairs(Jobs.ROUTE_KINDS) do
            local pick = (checks["route_" .. kind .. "_whisper"]:GetChecked() and "whisper") or
                (checks["route_" .. kind .. "_off"]:GetChecked() and "off") or "group"
            if pick ~= Jobs.RouteOf(kind) then route[kind] = pick end
        end
        if next(route) then db.route = route end
        -- the team and point of contact
        local keep = {}
        for nm in boxes.team:GetText():gmatch("[^,]+") do nm = nm:gsub("^%s+", ""):gsub("%s+$", "") if nm ~= "" then keep[#keep + 1] = nm end end
        local before = Jobs.TeamOn()
        db.team = type(db.team) == "table" and db.team or {}
        db.team.members = {}
        for _, nm in ipairs(keep) do db.team.members[nm] = true end
        local pc = boxes.poc:GetText():gsub("^[%s,]+", ""):gsub("[%s,]+$", "")
        db.team.poc = (pc ~= "") and pc or nil
        if #keep == 0 and not db.team.poc then db.team = nil end
        if Jobs.TeamOn() and not before then Jobs.SayHi(true)
        elseif Jobs.TeamOn() and Jobs.POC() == Jobs.Me() then Jobs.SendPrices() end
        db.workers = nil   -- now kept as the team list (above)
        RefreshJobs()
    end

    -- the footer: Preview (what this tab's messages look like, in your chat only) and Save
    local save = FlatButton(w, 120, 34, "gold", 14)
    save:SetPoint("BOTTOMRIGHT", -28, 15) save:SetText("Save")
    save:SetScript("OnClick", function() w.Save() w.Load() P("setup saved") end)
    local prev = FlatButton(w, 104, 34, "plain", 13)
    prev:SetPoint("BOTTOMLEFT", RAIL + 28, 15) prev:SetText("Preview")
    prev:SetScript("OnClick", function() w.Save() w.Load() PrintPreview(TABS[w.tab or 1]) end)
    Jobs.Tip(prev, "What this tab's messages look like, in your chat only")
    w.preview = prev

    -- shrink to fit small screens so nothing runs off
    local function Fit()
        local sw, sh = UIParent:GetWidth(), UIParent:GetHeight()
        local sc = 1
        if type(sw) == "number" and type(sh) == "number" and sw > 0 and sh > 0 then
            sc = math.min(1, sw / (W + 40), sh / (H + 80))
        end
        w:SetScale(sc)
    end
    local acc = 0
    w:SetScript("OnUpdate", function(_, el) acc = acc + (el or 0) if acc >= 1 then acc = 0 Report("setup", pcall(Refresh)) end end)
    w:SetScript("OnShow", function() Fit() w.Load() ShowTab(w.tab or 1) end)
    w:SetScript("OnHide", function() w.Save() if picker then picker:Hide() end end)
    w.checks, w.boxes = checks, boxes
    return w
end

ToggleSetup = function()
    setupWin = setupWin or BuildSetupUI()
    if setupWin:IsShown() then setupWin:Hide() else setupWin:Show() end
end

----------------------------------------------------------------------
-- Self-test (/si selftest): checks the game functions it needs and runs
-- sample messages through the matcher using DEFAULT settings.
----------------------------------------------------------------------
local function SelfTest()
    local pass, fail = 0, 0
    local function Report(ok, label)
        if ok then pass = pass + 1 else fail = fail + 1 end
        P((ok and "|cff00ff00PASS|r " or "|cffff4040FAIL|r ") .. label)
    end

    -- Game functions it depends on.
    Report((C_PartyInfo and C_PartyInfo.InviteUnit) ~= nil or InviteUnit ~= nil, "invite function exists")
    Report(IsInGroup ~= nil and UnitIsGroupLeader ~= nil and GetNumGroupMembers ~= nil, "group functions exist")
    Report(Ambiguate ~= nil, "Ambiguate exists")
    Report(GetTargetTradeMoney ~= nil, "trade money reading exists (for automatic Paid)")
    Report(UnitIsVisible ~= nil, "arrival check exists (UnitIsVisible)")
    Report(SetBindingClick ~= nil and SaveBindings ~= nil, "key binding functions exist")
    local okUI, err = pcall(function() setupWin = setupWin or BuildSetupUI() end)
    Report(okUI, "settings window builds" .. (okUI and "" or (": " .. tostring(err))))
    local okJ, errJ = pcall(function() jobsWin = jobsWin or BuildJobsUI() end)
    Report(okJ, "customer list window builds" .. (okJ and "" or (": " .. tostring(errJ))))

    -- Customer list lifecycle, using a fake customer (stats restored after).
    local savedStats = ServiceInviterDB.stats
    ServiceInviterDB.stats = nil
    Jobs.New("Selftestdummy", "wtb summon tb", "test", "Trade")
    Report(Jobs.Get("Selftestdummy") and Jobs.Get("Selftestdummy").status == "invited", "job starts as Invited")
    Report(Jobs.Joined("Selftestdummy") and Jobs.Get("Selftestdummy").status == "joined", "job becomes In group when they join")
    Jobs.Set("Selftestdummy", "summoned") Jobs.Set("Selftestdummy", "paid")
    Report(Stats().summoned == 1 and Stats().paid == 1, "summoned/paid are counted once")
    Jobs.Remove("Selftestdummy")
    Report(Jobs.Get("Selftestdummy") == nil, "job can be removed")
    ServiceInviterDB.stats = savedStats

    -- Matcher, with default settings (your own settings are restored after).
    local saved = ServiceInviterDB.opts
    ServiceInviterDB.opts = nil
    local yes = { "wtb summ to tb pst", "wtb summon tb whisper me", "WTB TB summon", "wtb summon to tb", "need a summon to TB 25s", "[WTB] summon -> TB", "WTB  TB   summon" }
    local no = {
        "WTS port to TB 25s pst inv", "Selling ports to TB for 25s", "need summon tb pst inv", "wtb port to uc from tb", "wtb port from tb",
        "wtb summon tb selling", "wtb sword", "wtb summon org", "summon to tb",
    }
    for _, m in ipairs(yes) do
        local ok, why = Evaluate(Norm(m))
        Report(ok, "accepts: " .. m)
    end
    for _, m in ipairs(no) do
        local ok, why = Evaluate(Norm(m))
        Report(not ok, "rejects: " .. m .. "  (" .. why .. ")")
    end
    ServiceInviterDB.opts = saved

    local color = (fail == 0) and "|cff00ff00" or "|cffff4040"
    P(color .. pass .. " passed, " .. fail .. " failed|r")
    if fail == 0 then
        P("Next: /si dryrun, then have a friend say 'wtb summon tb' in Say (tick Say in /si setup).")
    end
end

----------------------------------------------------------------------
-- Slash commands
----------------------------------------------------------------------
local function SplitList(s)
    local list = {}
    for piece in s:gmatch("[^,]+") do
        local w = (piece:gsub("^%s+", ""):gsub("%s+$", "")):lower()
        if w ~= "" then list[#list + 1] = w end
    end
    return list
end

SLASH_SERVICEINVITER1 = "/si"
SlashCmdList["SERVICEINVITER"] = function(arg)
    arg = (arg or ""):gsub("^%s+", ""):gsub("%s+$", "")
    local cmd, rest = arg:match("^(%S*)%s*(.*)$")
    cmd = (cmd or ""):lower()
    if cmd == "" or cmd == "jobs" or cmd == "list" then ToggleJobs()
    elseif cmd == "setup" then ToggleSetup()
    elseif cmd == "config" or cmd == "options" or cmd == "settings" then ToggleUI()
    elseif cmd == "on" then
        paused = false SetOpt("enabled", true)
        if ServiceInviterDB.kwwas then SetOpt("kwon", true) ServiceInviterDB.kwwas = nil end
        P("on (all invites)")
    elseif cmd == "off" then
        -- master switch: stops summon/port matching AND keyword invites; /si on restores both
        if Opt("kwon") then ServiceInviterDB.kwwas = true end
        SetOpt("enabled", false) SetOpt("kwon", false)
        P("off (all invites stopped; /si on turns them back on)")
    elseif cmd == "debug" then
        debugOn = not debugOn
        ServiceInviterDB.debug = debugOn
        P("debug " .. (debugOn and "ON (stays on after /reload)" or "off"))
    elseif cmd == "near" then
        ServiceInviterDB.near = not (ServiceInviterDB.near ~= false)
        P("near-miss lines " .. (ServiceInviterDB.near ~= false and "ON" or "off"))
    elseif cmd == "out" then
        local n = tonumber(rest)
        if rest == "tab" or rest == "new" then Jobs.MakeTab()
        elseif rest == "" or rest == "off" then
            ServiceInviterDB.outframe = nil
            P("output: a chat tab named SI if you have one, else the main window. /si out tab makes one")
        elseif n and _G["ChatFrame" .. n] then
            ServiceInviterDB.outframe = n
            P("output now goes to chat window " .. n)
        else
            P("/si out tab = make an SI chat tab, /si out 3 = chat window 3, /si out off = automatic")
        end
    elseif cmd == "selftest" then SelfTest()
    elseif cmd == "dryrun" or cmd == "test" then
        local r = rest:gsub("^%s+", ""):gsub("%s+$", "")
        if r:lower() == "off" then ServiceInviterDB.dryrun = false
        elseif r:lower() == "on" or r == "" then ServiceInviterDB.dryrun = (cmd == "test") or not ServiceInviterDB.dryrun ServiceInviterDB.testto = nil
        else ServiceInviterDB.dryrun = true ServiceInviterDB.testto = r end
        if ServiceInviterDB.dryrun then
            P("|cffffd100TEST MODE ON|r: nobody is invited. Each buyer's messages go to " ..
                ((ServiceInviterDB.testto and ("a whisper to " .. ServiceInviterDB.testto)) or "your chat") .. " instead. /si test off to stop.")
        else
            P("test mode OFF: it will really invite")
        end
    elseif cmd == "test" then
        local ok, why = Evaluate(Norm(rest))
        P((ok and "WOULD invite" or "would NOT invite") .. " (" .. why .. ")")
    elseif cmd == "msg" then
        if rest == "" then P("welcome message: " .. (ServiceInviterDB.welcomemsg or MSG.WELCOME))
        else ServiceInviterDB.welcomemsg = rest P("welcome message set") end
    elseif cmd == "cooldown" then
        local n = tonumber(rest)
        if n and n >= 0 then ServiceInviterDB.cooldown = n P("cooldown " .. n .. "s") else P("usage: /si cooldown <seconds>") end
    elseif cmd == "block" then
        if rest ~= "" then
            ServiceInviterDB.blocked = ServiceInviterDB.blocked or {}
            ServiceInviterDB.blocked[rest:lower()] = true
            P("blocked " .. rest)
        end
    elseif cmd == "unblock" then
        if ServiceInviterDB.blocked then ServiceInviterDB.blocked[rest:lower()] = nil end
        P("unblocked " .. rest)
    elseif cmd == "bind" then
        -- /si bind F  (the big button)   or   /si bind ad F7  (post the ad)
        local forAd = rest:lower():match("^ad%s+") ~= nil
        local forBuff = rest:lower():match("^buff%s+") ~= nil
        local key = ((forAd or forBuff) and rest:gsub("^%S+%s+", "") or rest):upper():gsub("%s+", "")
        if key == "" then P("usage: /si bind <key>  (big button)   or   /si bind ad <key>  (post the ad)")
        elseif InCombatLockdown and InCombatLockdown() then P("can't change keys in combat")
        else
            jobsWin = jobsWin or BuildJobsUI()
            local target = forBuff and "ServiceInviterBuffButton" or (forAd and "ServiceInviterAdButton" or "ServiceInviterNext")
            if SetBindingClick and SetBindingClick(key, target) then
                if SaveBindings and GetCurrentBindingSet then SaveBindings(GetCurrentBindingSet()) end
                P(key .. (forBuff and " now casts the next buff in line" or (forAd and " now posts the ad (when it's ready)" or " now presses the big button (does the next thing for your next customer)")))
            else
                P("couldn't bind " .. key .. " (try another key)")
            end
        end
    elseif cmd == "ad" then PostAd()
    elseif cmd == "preview" then
        local want = rest:lower()
        local tab = (setupWin and setupWin.tab and PV.TABS[setupWin.tab]) or "General"
        for _, t in ipairs(PV.TABS) do if want ~= "" and t:lower():find(want, 1, true) == 1 then tab = t end end
        PrintPreview(tab)
    elseif cmd == "status" then
        do
            local items, parts = Core.OnSale(ServiceInviterDB, GroupSnapshot(), Faction()), {}
            for _, it in ipairs(items) do parts[#parts + 1] = it.def.label .. " (" .. (it.provider.me and "you" or it.provider.name) .. ", " .. tostring(it.where or "where?") .. ")" end
            P("on sale: " .. (#parts > 0 and table.concat(parts, ", ") or "nothing (nobody in the group can do what's ticked)"))
        end
        local isLoaded = (C_AddOns and C_AddOns.IsAddOnLoaded) or IsAddOnLoaded
        local ti = isLoaded and isLoaded("TradeInviter")
        P("invites: " .. (paused and "|cffff8040PAUSED (Trade Inviter is loaded)|r" or (Opt("enabled") and "|cff00ff00ON|r" or "|cffff4040OFF|r (tick it in /si setup or /si on)")) ..
          "   role: " .. Role() .. "   Trade Inviter loaded: " .. (ti and "yes" or "no") .. "   group: " .. ((IsInRaid and IsInRaid()) and "raid" or ((IsInGroup and IsInGroup()) and "party" or "none")))
        local h = diag.heard
        if h then
            P("last chat line heard (" .. math.floor(GetTime() - h.t) .. "s ago): [" .. tostring(h.ch) .. "] " .. tostring(h.who) .. ": " .. tostring(h.text) .. "   -> " ..
              (ChannelAllowed(h.ch) and "channel is listened to" or "|cffff4040channel NOT listened to|r (check Listen in)"))
        else
            P("no chat line heard yet from Trade/General/Say/Yell. Are you in those channels, and ticked under Listen in?")
        end
        local e = diag.eval
        if e then P("last decision (" .. math.floor(GetTime() - e.t) .. "s ago): " .. e.who .. " -> " .. (e.ok and "INVITE" or "no") .. " (" .. tostring(e.why) .. ")")
        else P("no message has reached the matcher yet (it only sees messages while invites are ON and you are not AFK)") end
        local l = diag.last
        if l then
            P("last ritual (" .. math.floor(GetTime() - l.t) .. "s ago, " .. tostring(l.event):gsub("UNIT_SPELLCAST_", "") .. "): for " .. tostring(l.who) .. " (lock's target: " .. tostring(l.target) .. ")" ..
              (l.stop and ("   STOPPED: " .. l.stop) or ("   whisper: " .. tostring(l.whisper) .. "   raid: " .. tostring(l.raid) .. "   banner: " .. tostring(l.banner) .. "   marked: " .. tostring(l.marked))))
        end
        do
            local e = diag.echo
            if e then P("whisper delivery: the game confirmed a " .. e.kind .. " whisper " .. math.floor(GetTime() - e.t) .. "s ago")
            else P("whisper delivery: the game has not confirmed any whisper yet (/si whispertest to try one)") end
            local u = diag.uierr
            if u then P("last game error (" .. math.floor(GetTime() - u.t) .. "s ago): " .. u.msg) end
        end
        if #diag.casts == 0 then
            P("no casts seen from you or your group yet. Have the lock start Ritual of Summoning, then /si status again.")
        else
            for _, c in ipairs(diag.casts) do
                P("cast " .. math.floor(GetTime() - c.t) .. "s ago: " .. tostring(UnitName and UnitName(c.unit) or c.unit) .. " (" .. c.unit .. ") " .. c.name .. " id " .. tostring(c.id) .. " " .. c.event:gsub("UNIT_SPELLCAST_", ""))
            end
        end
    elseif cmd == "stop" or cmd == "stasis" then
        ServiceInviterDB.stasis = true
        Jobs.CloseJobs()
        P("|cffff8040stopped|r: hearing nothing and doing nothing, even after a reload. /si start to wake it.")
    elseif cmd == "start" or cmd == "wake" then
        ServiceInviterDB.stasis = nil
        P("started again")
    elseif cmd == "worker" or cmd == "workers" then
        local r = rest:gsub("^%s+", ""):gsub("%s+$", "")
        if r:lower() == "group" then
            local n = 0
            for _, m in ipairs(GroupSnapshot()) do
                if not m.me and not m.customer then Jobs.SetWorker(m.name, true) n = n + 1 end
            end
            P(n .. " in your group marked as workers (customers left alone)")
        elseif r:lower() == "clear" then
            ServiceInviterDB.workers = nil P("worker list cleared")
        elseif r ~= "" or (cmd == "worker" and UnitExists and UnitExists("target")) then
            local name = r ~= "" and r or FullName("target")
            if name then
                local on = not Jobs.IsWorker(name)
                name = Jobs.SetWorker(name, on)
                P(name .. (on and " is a worker now (no row, no welcome, never invited)" or " is not a worker any more"))
            end
        end
        local list = {}
        for k in pairs(type(ServiceInviterDB.workers) == "table" and ServiceInviterDB.workers or {}) do list[#list + 1] = k end
        table.sort(list)
        P("workers: " .. (#list > 0 and table.concat(list, ", ") or "none") .. "   (/si worker NAME or your target, /si workers group, /si workers clear)")
        RefreshJobs()
    elseif cmd == "team" then
        local sub, arg = rest:match("^(%S*)%s*(.*)$")
        sub = (sub or ""):lower()
        local function each(f) for nm in (arg or ""):gmatch("[^,]+") do nm = nm:gsub("^%s+", ""):gsub("%s+$", "") if nm ~= "" then f(nm) end end end
        if sub == "add" then each(function(nm) Jobs.SetTeam(nm, true) end) Jobs.SayHi(true)
        elseif sub == "remove" then each(function(nm) Jobs.SetTeam(nm, false) end)
        elseif sub == "poc" or sub == "contact" then
            ServiceInviterDB.team = type(ServiceInviterDB.team) == "table" and ServiceInviterDB.team or {}
            ServiceInviterDB.team.poc = (arg ~= "" and arg) or nil
        elseif sub == "clear" then ServiceInviterDB.team = nil
        elseif sub ~= "" then P("/si team add NAME, NAME · /si team remove NAME · /si team poc NAME, BACKUP · /si team clear") return end
        local list = Jobs.TeamPeople()
        if not Jobs.TeamOn() then P("no team: working solo. Join a guild, or /si team add NAME, NAME to share with them") return end
        if Jobs.GuildTeam() then P("your guild is the team" .. (#list == 0 and ": no guildmate's copy heard from yet" or "")) end
        local parts = {}
        for _, nm in ipairs(list) do
            local s2 = Jobs.Team.seen[nm]
            parts[#parts + 1] = nm .. (Jobs.Online(nm) and (" (online" .. (s2 and s2.lock and ", warlock" or "") .. (s2 and s2.zone and s2.zone ~= "" and (", " .. s2.zone) or "") .. ")") or " (not seen)")
        end
        if #parts > 0 then P("team: " .. table.concat(parts, ", ")) end
        P(Jobs.BooksLine())
        local poc = Jobs.POC()
        local set = type(ServiceInviterDB.team) == "table" and ServiceInviterDB.team.poc
        P("point of contact: " .. (poc and (poc .. (poc == FullName("player") and " (you)" or "")) or "none online") ..
            (set and ("   (list: " .. set .. ")") or "   (/si team poc NAME, BACKUP to set one)"))
        RefreshJobs()
    elseif cmd == "prices" or cmd == "rivals" then
        local sm = (type(ServiceInviterDB.services) == "table" and ServiceInviterDB.services.summons) or {}
        local mode = Jobs.PriceMode(sm)
        local max = Core.Setting(ServiceInviterDB, "summons").price
        P("Summons " .. (sm.floor and (Core.Money(sm.floor) .. " to ") or "") .. (Core.Money(max) or "free") .. "; other sellers: " ..
            ((mode == "ignore" and "ignored (always the max)") or (mode == "match" and "matched") or ("undercut by " .. (sm.undercut or 5) .. " silver")) ..
            ((mode ~= "ignore" and not sm.floor) and " (no min set: prices don't move)" or ""))
        local any
        for market, cities in pairs(Jobs.rivals) do
            for where in pairs(cities) do
                local r = Jobs.Rival(where, market)
                if r then
                    any = true
                    local was = Jobs.priceMarket
                    Jobs.priceMarket = market
                    local ours = Core.Setting(ServiceInviterDB, "summons", where).price
                    Jobs.priceMarket = was
                    P(market .. ", " .. Core.Short(where) .. ": " .. r.who .. " at " .. (Core.Money(r.price) or "?") .. ", " ..
                        math.floor(GetTime() - r.t) .. "s ago; ours " .. (Core.Money(ours) or "free"))
                end
            end
        end
        if not any then P("no other seller's summon ad in the last 5 minutes, in any channel you're in") end
    elseif cmd == "why" then
        local h = rest ~= "" and Jobs.heard and Jobs.heard[rest:lower()]
        if not h then
            for k, v in pairs(Jobs.heard or {}) do if rest ~= "" and k:find(rest:lower(), 1, true) == 1 then h = v end end
        end
        if not h then P("haven't heard " .. (rest ~= "" and rest or "them") .. " say anything since the last reload (or not in a channel you listen to)") return end
        local j = Jobs.Get(rest)
        P(rest .. ", " .. math.floor(GetTime() - h.t) .. "s ago in [" .. tostring(h.ch) .. "]: \"" .. tostring(h.text) .. "\"")
        P("  -> " .. tostring(h.why):gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "") .. (j and ("  (on the list: " .. j.status .. ")") or ""))
    elseif (cmd == "scammers" or cmd == "scams") and rest:lower() == "names" then
        -- just the names, one a line, for the guild bot's lookup (the owner, 14 Nov 2026: "it just
        -- looks up names i just want a list i can copy and paste")
        Jobs.Copy("Didn't pay: names", function()
            local list = {}
            for k in pairs(Jobs.Scammers()) do list[#list + 1] = k end
            table.sort(list)
            if #list == 0 then P("nobody on the list") end
            for _, n in ipairs(list) do P(n) end
        end)
    elseif cmd == "scammers" or cmd == "scams" then
        Jobs.Copy("Didn't pay", function()
            local list = {}
            for k, v in pairs(Jobs.Scammers()) do list[#list + 1] = { k, v } end
            table.sort(list, function(a, b) return (a[2].last or 0) > (b[2].last or 0) end)
            if #list == 0 then P("nobody on the list") return end
            for _, e in ipairs(list) do
                P(e[1] .. ": " .. e[2].n .. (e[2].n == 1 and " time" or " times") .. ", owed " .. Money(e[2].owed or 0) .. ", last " .. Jobs.When(e[2].last))
            end
        end)
    elseif cmd == "scam" then
        if rest == "" then P("/si scam NAME: they didn't pay (also undoes a Paid by mistake)") return end
        local j = Jobs.Get(rest)
        if not j then for _, x in ipairs(jobs) do if x.name:lower() == rest:lower() then j = x end end end
        Jobs.Scam(j and j.name or rest)
        RefreshJobs()
    elseif cmd == "unscam" then
        -- kept as "cleared", so the team's copies clear it too
        local tot, key = Jobs.Scammer(rest)
        if key then
            ServiceInviterDB.scammers = type(ServiceInviterDB.scammers) == "table" and ServiceInviterDB.scammers or {}
            local mine
            for k in pairs(ServiceInviterDB.scammers) do if k:lower() == key:lower() then mine = k end end
            local e = ServiceInviterDB.scammers[mine or key] or { n = 0, owed = 0 }
            e.cleared = math.max(Now(), tot.last or 0)
            e.rev = Jobs.Bump()
            ServiceInviterDB.scammers[mine or key] = e
            if Jobs.TeamOn() then Jobs.SayHi(false) end
            P(key .. " is off the didn't-pay list")
        else P("nobody called " .. rest .. " on the list") end
    elseif cmd == "shards" then
        local r = rest:lower()
        if r == "off" then ServiceInviterDB.shards = nil SetOpt("countshards", false)
        elseif tonumber(r) then ServiceInviterDB.shards = math.max(0, math.floor(tonumber(r))) SetOpt("countshards", true)
        elseif r ~= "" then P("/si shards 20 (other warlocks' shards), /si shards off") return end
        local have, own, typed = Jobs.Shards()
        if not have then P("not counting shards. /si shards 20 to count other warlocks' shards") return end
        P("shards: " .. have .. (own and typed and (" (" .. own .. " yours, " .. typed .. " typed)") or "") ..
            ", " .. Jobs.Queued() .. " summons queued, " .. math.max(0, Jobs.ShardsLeft()) .. " left")
        RefreshJobs()
    elseif cmd == "lists" then
        Jobs.Lists(rest ~= "" and rest or nil)
    elseif cmd == "teamlog" or cmd == "log" then
        Jobs.Copy("Team messages", Jobs.PrintTeamLog)
    elseif cmd == "stats" or cmd == "analytics" then
        Jobs.Copy("Stats", Jobs.PrintStats)
    elseif cmd == "customers" or cmd == "regulars" then
        Jobs.Copy(rest ~= "" and rest:lower() ~= "all" and "Customer" or "Customers", function() Jobs.PrintRegulars(rest) end)
    elseif cmd == "session" then
        if rest:lower() == "new" or rest:lower() == "reset" then NewSession() P("new session started") Jobs.AskShards()
        else P("session: " .. SessionText() .. "   (/si session new to start over)") end
    elseif cmd == "role" then
        local r = rest:lower()
        if r == "lock" or r == "warlock" then ServiceInviterDB.role = "lock" P("role: lock. Summon and Offer buttons are back. Who takes the money is separate: /si collect.")
        elseif r == "helper" then ServiceInviterDB.role = "helper" P("role: helper. Alerts you to click the portal; the lock does the summoning. Who takes the money is separate: /si collect.")
        else P("role is " .. Role() .. ". Use /si role helper  or  /si role lock") end
        RefreshJobs()
    elseif cmd == "alert" then
        ShowAlert("CLICK PORTAL", "Testy  »  Thunder Bluff  ·  Pay you", "TEST · SUMMONING")
    elseif cmd == "whispertest" then
        local to = WhisperTo()
        if not to then P("no whisper recipient set (/si whisper <name>)") return end
        local ok, how = pcall(SendWhisperTo, to, "Service Inviter test whisper")
        P("whisper test: " .. (ok and ("sent to " .. tostring(how)) or ("FAILED: " .. tostring(how))) .. "  -- now /si status to see if the game confirmed it")
    elseif cmd == "simcast" then
        -- pretend the first other group member started Ritual of Summoning (tests the whole alert path)
        local u
        for i = 1, 4 do if UnitExists and UnitExists("party" .. i) then u = "party" .. i break end end
        if not u then for i = 1, 40 do if UnitExists and UnitExists("raid" .. i) and not (UnitIsUnit and UnitIsUnit("raid" .. i, "player")) then u = "raid" .. i break end end end
        if not u then P("simcast: you need at least one other person in your group") else
            lastCastAt = 0
            local ok, err = pcall(OnCast, "UNIT_SPELLCAST_START", u, RITUAL_ID)
            P("simcast as " .. u .. ": " .. (ok and "ran (see /si status)" or ("|cffff4040error:|r " .. tostring(err))))
        end
    elseif cmd == "alertmsg" then
        if rest == "" then P("raid alert: " .. (ServiceInviterDB.alertmsg or MSG.ALERTMSG) .. "   ({name} and {price} are filled in)")
        else ServiceInviterDB.alertmsg = rest P("raid alert message set") end
    elseif cmd == "raidalert" then
        ServiceInviterDB.raidalert = not (ServiceInviterDB.raidalert ~= false)
        P("raid line " .. (ServiceInviterDB.raidalert ~= false and "ON" or "off"))
    elseif cmd == "whisper" then
        local r = rest:gsub("%s+", "")
        if r == "" then P("ritual whisper goes to: " .. (WhisperTo() or "nobody") .. "   (/si whisper <name>  or  /si whisper off)")
        elseif r:lower() == "off" then ServiceInviterDB.whisperto = false P("ritual whisper off")
        else ServiceInviterDB.whisperto = r P("ritual whisper goes to " .. r) end
    elseif cmd == "collect" then
        -- toggles "who gets paid" between always you and whoever is where the customer lands
        local d = type(ServiceInviterDB.payee) == "table" and ServiceInviterDB.payee or {}
        local mode = d.mode or (ServiceInviterDB.collect == true and "me") or "provider"
        ServiceInviterDB.payee = { mode = (mode == "me") and "provider" or "me", name = d.name }
        ServiceInviterDB.collect = nil
        P("who gets paid: " .. (ServiceInviterDB.payee.mode == "me" and "always YOU (trade opens by itself when they're in range)" or "whoever does it (the warlock, mage, rogue...)"))
        RefreshJobs()
    elseif cmd == "autotrade" then
        ServiceInviterDB.autotrade = not AutoTradeOn()
        P("auto-open trade (and auto Paid) " .. (AutoTradeOn() and "ON: opens when a customer arrives in range; you click Accept" or "off"))
    elseif cmd == "offermsg" then
        if rest == "" then P("offer message: " .. (ServiceInviterDB.offermsg or MSG.OFFERMSG) .. "   ({name} and {offers} are filled in)")
        else ServiceInviterDB.offermsg = rest P("offer message set") end
    elseif cmd == "clear" then Jobs.Clear() P("customer list cleared")
    elseif cmd == "price" then
        local n = ParsePrice(rest)
        if n and n >= 0 then
            ServiceInviterDB.services = ServiceInviterDB.services or {}
            ServiceInviterDB.services.summons = ServiceInviterDB.services.summons or {}
            ServiceInviterDB.services.summons.price = (n > 0) and n or false
            ServiceInviterDB.price = nil
            P("summons price " .. (n > 0 and Money(n) or "free") .. " (other services: their tab in /si setup)")
        else P("usage: /si price 25   or   /si price 1g 25s   or   /si price 2g") end
    elseif cmd == "reset" then
        wipe(lastInvite) wipe(pending) wipe(fragments) inviteTimes = {}
        ServiceInviterDB = {}
        P("settings reset")
    else
        P("/si = customers | /si setup = every message and option | /si session = earnings | /si customers = your regulars (/si customers all, /si customers NAME) | /si stats = where, what, when | /si shards 20 = other warlocks' shards | /si worker NAME = one of yours, not a customer | /si workers group | /si why NAME = what it decided about them | /si team = your team and point of contact | /si teamlog = what the copies told each other | /si prices = other sellers and your live price | /si scam NAME = didn't pay, /si scammers (names), /si unscam NAME | /si stop = stasis, /si start | /si preview | /si status = what it hears | /si simcast = test the alert | /si session new | /si collect = who takes the money | /si on | /si off | /si selftest")
    end
end

-- Exposed for offline testing only.
ServiceInviter_Test = { Tick = function(el) ticker:GetScript("OnUpdate")(ticker, el) end, Ordinal = function(n) return Jobs.Ordinal(n) end, Preview = function(t) return Preview(t) end, PrintPreview = function(t) return PrintPreview(t) end, BuffLabel = function() return BuffLabel() end, RefreshBuff = function() return RefreshBuff() end, ShowPicker = function(box, d, t, k) return ShowPicker(box, d, t, k) end, SetupChecks = function() setupWin = setupWin or BuildSetupUI() return setupWin.checks end, SetupBoxes = function() setupWin = setupWin or BuildSetupUI() return setupWin.boxes end, PostAd = function() return PostAd() end, AdState = function() return AdState() end, Group = function() return GroupSnapshot() end, LiveTargets = function() return LiveTargets() end, WelcomeText = function(n) return WelcomeText(n) end, ArrivalText = function(j) return ArrivalText(j) end, Norm = Norm, Evaluate = Evaluate, ToggleUI = ToggleUI, Opt = Opt, Jobs = Jobs, BuildSetup = function() setupWin = setupWin or BuildSetupUI() return setupWin end, WhisperText = WhisperText, Stats = Stats, NextStep = NextStep, OfferText = OfferText, NextJob = NextJob, OnCast = OnCast, CheckArrivals = CheckArrivals, Role = Role,
    Refresh = function() jobsWin = jobsWin or BuildJobsUI() RefreshJobs() end }
