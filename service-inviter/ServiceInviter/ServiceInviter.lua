-- Service Inviter v2.7.0
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
    local map = { healthstone = "healthstone", soulstone = "soulstone", food = "water", lockpick = "lockpick",
                  stam = "fort", motw = "motw", int = "ai", paladin = "blessing", portal = "portals" }
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
local MSG = {}   -- the default text of every message you can change
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
    local f = OutFrame()
    local line = "|cff80ff80Service Inviter|r: " .. msg
    if f and f.AddMessage then f:AddMessage(line) else print(line) end
end
local function D(msg) if debugOn then P("|cff999999" .. msg .. "|r") end end
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
            sawDest = true
            -- a summon fetches them from anywhere, so it answers a port request too;
            -- a port (a mage) needs them to come to you, so it does not answer a summon request
            if T.sum[d.key] then
                if wantsSum then return true, "summon to " .. d.label .. ", buy=" .. buy, "summons", d.label end
                if wantsPort then return true, "port request to " .. d.label .. ", you summon there, buy=" .. buy, "summons", d.label end
            end
            if wantsPort and T.port[d.key] then return true, "port to " .. d.label .. ", buy=" .. buy, "portals", d.label end
        end
    end
    if waived and not sawDest then return false, "no place named (needs one when there is no summon/port word)" end
    if (wantsSum or wantsPort) and T.sumAny then return true, "summon (any destination), buy=" .. buy, "summons" end
    if wantsPort and T.portAny then return true, "port (any destination), buy=" .. buy, "portals" end
    -- No place named ("WTB summon"): never assume where they want to go.
    return false, sawDest and "that destination/service is not checked" or "no place named"
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
local function JobPrice(j)
    return Core.Setting(ServiceInviterDB, (j and j.service) or "summons").price
end
-- Who gets paid for this customer, and whether that's you.
local function PayeeFor(j, g)
    g = g or GroupSnapshot()
    local key = (j and j.service) or "summons"
    local p = Core.Provider(g, key, j and j.dest or nil)
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
    db.analytics = a
end
-- /si stats: who, where, what, when, since the book started
function Jobs.PrintStats()
    local db = ServiceInviterDB
    local a, book = db.analytics, type(db.customers) == "table" and db.customers or {}
    if type(a) ~= "table" or a.n == 0 then P("no stats yet: they start with the first summon or Paid") return end
    local people, back = 0, 0
    for _, c in pairs(book) do people = people + 1 if c.n > 1 then back = back + 1 end end
    local function top(t, name, limit)
        local list = {}
        for k, v in pairs(t or {}) do list[#list + 1] = { k, v } end
        table.sort(list, function(x, y) return x[2] > y[2] end)
        local out = {}
        for i = 1, math.min(limit or 99, #list) do out[#out + 1] = name(list[i][1]) .. " " .. list[i][2] end
        return #out > 0 and table.concat(out, ", ") or "none yet"
    end
    local DAYS = { "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat" }
    P("Since " .. Jobs.When(a.since):gsub(" %d+:%d+$", "") .. ": " .. a.n .. " uses by " .. people .. " customers (" .. back ..
        " came back), worth " .. Money(a.worth))
    P("Where they went: " .. top(a.to, function(k) return k end))
    P("Services: " .. top(a.by, function(k) return (Core.BY_KEY[k] and Core.BY_KEY[k].label) or k end))
    P("Busiest hours: " .. top(a.hour, function(h) return ("%02d:00"):format(h) end, 3))
    P("Busiest days: " .. top(a.day, function(d) return DAYS[d] or d end, 3))
end
-- Soul shards (the owner, 13 Nov 2026: "i want a running counter of summons - like our inv and
-- expected amount left so it knows to stop"). Yours are read from your bags when you're the
-- warlock ("built in for the lock"); other warlocks' you type: /si shards 20. Nil: not counting.
function Jobs.Shards()
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
    local c = j and type(ServiceInviterDB.customers) == "table" and ServiceInviterDB.customers[j.name]
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
    local book = type(ServiceInviterDB.customers) == "table" and ServiceInviterDB.customers or {}
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

function Jobs.Joined(name)
    local j = jobByName[name]
    if j and (j.status == "invited" or j.status == "asked") then Jobs.Set(name, "joined") return true end
    return false
end
function Jobs.Left(name)
    local j = jobByName[name]
    if j and (j.status == "joined" or j.status == "invited" or j.status == "summoned" or j.status == "arrived") then Jobs.Set(name, "left") end
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
    if t then pcall(SendChatMessage, t, "WHISPER", nil, j.name) end
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

local function Handle(text, sender, guid)
    if paused then return end
    local now0 = GetTime()
    local adOpen = lastAdAt and (now0 - lastAdAt) < AD_ANSWER_WINDOW
    if not (Opt("enabled") or Opt("kwon") or (adOpen and curChannel == "whisper")) or not sender or sender == "" then D("skip: addon off or no sender") return end
    if Opt("skipafk") and UnitIsAFK and UnitIsAFK("player") then D("skip: you are AFK (see 'Skip while I'm AFK')") return end
    local short = Ambiguate and Ambiguate(sender, "none") or sender
    if Jobs.IsWorker(short) then D("skip: " .. short .. " is one of your workers") return end
    if short == FullName("player") then return end
    if UnitInParty(short) or UnitInRaid(short) then D(short .. ": already in your group") return end
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
        local price = Core.Setting(ServiceInviterDB, svc).price
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
    if not ok and ServiceInviterDB.near ~= false and not HasAny(norm, SELLER)
        and HasAny(norm, BUY) and (HasAny(norm, SUMMON_WORDS) or HasAny(norm, PORT_WORDS)) then
        P("|cffffa040NEAR MISS|r " .. short .. " [" .. curChannel .. "] \"" .. text .. "\" -> " .. why)
    end

    -- Only talk about messages that look like summon/port talk, so debug stays readable.
    if ok or HasAny(norm, SUMMON_WORDS) or HasAny(norm, PORT_WORDS) then
        D("[" .. curChannel .. "] " .. short .. ": \"" .. text .. "\" -> " .. (ok and "MATCH" or "no") .. " (" .. why .. ")")
    end
    if not ok then return end

    if ServiceInviterDB.dryrun then
        P("|cffffd100DRY RUN|r would invite " .. short .. " because [" .. curChannel .. "] \"" .. text .. "\" = " .. why)
        return
    end

    if not UnderRateLimit(now) then P("|cffff8040matched " .. short .. " but hit the 6 invites/min limit|r") return end
    CanInvite()   -- turns a full party into a raid when you can

    lastInvite[short] = now
    fragments[short] = nil
    inviteTimes[#inviteTimes + 1] = now
    local job
    -- Always invite, leader or not, as it did through 2.4.1 (the owner, 13 Nov 2026: "it is so dumb
    -- to have to press invite - it worked yesterday"). 2.5.0 held them for a click; the declines
    -- turned out to happen to hand-typed invites too, so the click fixed nothing.
    DoInvite(short)
    pending[short] = now
    job = Jobs.New(short, text, why, curChannel)
    job.service, job.dest = svc, dest
    if answered then job.fromAd = true Stats().answers = (Stats().answers or 0) + 1 end
    if Opt("announce") then
        local what = JobWhere(job)
        if what == "" then what = answered and "(answered your ad)" or why end
        P("invited " .. short .. "  " .. what)
        -- exactly why, always (the owner, 13 Nov 2026: "why is it no longer telling me exactly why
        -- people are invited? i want that")
        P("|cff999999   because [" .. tostring(curChannel) .. "] \"" .. tostring(text) .. "\" = " .. tostring(why) .. "|r")
    end
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
    return (line:gsub("{visits}", function() return caps and nth:upper() or nth end))
end

local function WelcomeText(name, job)
    job = job or Jobs.Get(name)
    local g, fac = GroupSnapshot(), Faction()
    local loyal = job and Jobs.LoyaltyLine(job)
    local custom = ServiceInviterDB.welcomemsg
    if custom and custom ~= "" and custom ~= MSG.WELCOME then
        local key = (job and job.service) or "summons"
        local payee, mine = PayeeFor(job, g)
        local price = PriceText(JobPrice(job))
        local label = Core.BY_KEY[key].label
        local hasVisits = custom:find("{visits}", 1, true)
        custom = custom:gsub("{name}", function() return Jobs.Label(job, name) end):gsub("{price}", function() return price end)
        custom = custom:gsub("{payee}", function() return mine and "me" or Core.Label(g, payee) end):gsub("{service}", function() return label end)
        custom = custom:gsub("{visits}", function()
            local nth = Jobs.Ordinal(Jobs.Before(job) + 1)
            return (custom:gsub("{%a+}", "") == custom:gsub("{%a+}", ""):upper()) and nth:upper() or nth
        end)
        -- your own welcome without {visits}: a regular gets the "Regulars hear" line after it
        -- (the owner's: "THE COST IS {price} AND WE WILL SUMMON YOU SOON!" + "HEY FREQUENT FLYER!
        -- This is your {visits} time with us!")
        if loyal and not hasVisits then custom = custom:gsub("%s+$", "") .. " " .. loyal end
        return custom
    end
    if job and job.service then
        local text = Core.JoinWelcome(ServiceInviterDB, g, fac, job.service, Jobs.Label(job, name), job.dest)
        if text and loyal then text = text:gsub("^(Hi .-!) ", function(hi) return hi .. " " .. loyal .. " " end, 1) end
        if text then return text end
    end
    local list = Core.BuildAd(ServiceInviterDB, g, fac, "{services}")
    if list then return "Hi " .. name .. "! " .. (loyal and (loyal .. " ") or "") .. "We have " .. list .. ". What can we do for you?" end
    if loyal then return "Hi " .. name .. "! " .. loyal end
    return nil
end

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
    if not Opt("welcome") then
        if loyal then SendChatMessage("Hi " .. Jobs.Label(Jobs.Get(short), short) .. "! " .. loyal, channel) end
        return
    end
    local welcome = WelcomeText(short)
    if not welcome then D(short .. " joined; nothing on sale to welcome them with") return end
    D(short .. " joined, sending welcome to " .. channel)
    SendChatMessage(welcome, channel)
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
    if event == "CHAT_MSG_PARTY" or event == "CHAT_MSG_PARTY_LEADER" or event == "CHAT_MSG_RAID" or event == "CHAT_MSG_RAID_LEADER" then
        pcall(BuffAsk, text, sender)
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
    if event == "CHAT_MSG_CHANNEL" then
        local ch = (channelBaseName and channelBaseName ~= "") and channelBaseName or channelName
        if not ChannelAllowed(ch) then return end
    elseif event == "CHAT_MSG_SAY" then
        if not Opt("say") then return end
    elseif event == "CHAT_MSG_YELL" then
        if not Opt("yell") then return end
    elseif event == "CHAT_MSG_WHISPER" then
        curChannel = "whisper"
        pcall(BuffAsk, text, sender)
        if not KeywordHit(text, true) and not Opt("enabled") then return end
    end
    diag.heard = { ch = curChannel, who = sender, text = text, t = GetTime(), event = event }
    RememberSaid(sender, text, curChannel)
    Handle(text, sender, guid)
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
            if left <= 0 then return "ready", key, id, name, text end
            if not soonest or left < soonest then soonest = left end
        end
    end
    if not any then return "off", "you're not in any of the ad channels" end
    return "wait", soonest
end
local function AdLabel()
    local state, a = AdState()
    if state == "ready" then return "Post ad in " .. a:sub(1, 1):upper() .. a:sub(2), true end
    if state == "wait" then return ("Next ad in %d:%02d"):format(math.floor(a / 60), math.floor(a % 60)), false end
    return (a and a:find("nothing to sell", 1, true)) and "Nothing to sell" or "No ad", false
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
local function InGroupByName(name)
    return (UnitInParty and UnitInParty(name)) or (UnitInRaid and UnitInRaid(name)) or false
end
local buffKey = CreateFrame("Button", "ServiceInviterBuffButton", UIParent, "SecureActionButtonTemplate")
buffKey:SetAttribute("type", "macro")
buffKey:RegisterForClicks("AnyUp", "AnyDown")
buffKey:Hide()
buffDirty = false
local function BuffMacro(e)
    if not e then return "" end
    local spell = e.spell or Core.Setting(ServiceInviterDB, e.key).spell or ""
    return "/cast [@" .. e.name .. "] " .. spell .. (e.rank and ("(Rank " .. e.rank .. ")") or "")
end
local function BuffLabel()
    local e = buffQueue[1]
    if not e then return "No buffs waiting" end
    local def = Core.BY_KEY[e.key]
    local what = e.spell and e.spell:gsub("^Blessing of ", "") or def.label:gsub("^a ", "")
    return what .. " -> " .. e.name .. (#buffQueue > 1 and (" (+" .. (#buffQueue - 1) .. ")") or "")
end
RefreshBuff = function()
    -- drop anyone who left the group
    for i = #buffQueue, 1, -1 do if not InGroupByName(buffQueue[i].name) then table.remove(buffQueue, i) end end
    if InCombatLockdown and InCombatLockdown() then buffDirty = true return end
    buffDirty = false
    local m = BuffMacro(buffQueue[1])
    buffKey:SetAttribute("macrotext", m)
    if jobsWin and jobsWin.buffBtn then
        jobsWin.buffBtn:SetAttribute("macrotext", m)
        jobsWin.buffBtn:SetText(BuffLabel())
        if #MyBuffs() > 0 then jobsWin.buffBtn:Show() else jobsWin.buffBtn:Hide() end
    end
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
    D("buff queued: " .. (spell or key) .. " for " .. name)
    RefreshBuff()
end
QueueAllMyBuffs = function(name) for _, def in ipairs(MyBuffs()) do QueueBuff(name, def.key) end end
-- "fort pls" from someone in the group
BuffAsk = function(text, sender)
    if type(text) ~= "string" or IsSecret(text) or not sender then return end
    local name = Ambiguate and Ambiguate(sender, "none") or sender
    if name == FullName("player") or not InGroupByName(name) then return end
    local norm = Norm(text)
    -- asks are short ("wisdom pls", "can i get fort"); "i might be afk for a bit" is not one
    local count = 0
    for _ in norm:gmatch("%S+") do count = count + 1 end
    if count > 6 then return end
    for _, def in ipairs(MyBuffs()) do
        local words = Core.SplitWords(Core.Setting(ServiceInviterDB, def.key).words)
        if HasAny(norm, words) then
            if def.key == "blessing" then
                -- the word picks the blessing; the last one named wins ("wisdom... actually might")
                local spell, at = nil, 0
                for _, b in ipairs(Core.BLESSINGS) do
                    local i = norm:find(" " .. b.word .. " ", 1, true)
                    if i and i > at then spell, at = b.spell, i end
                end
                spell = spell or Core.Setting(ServiceInviterDB, "blessing").spell
                if KnowSpell(spell) then QueueBuff(name, def.key, spell)
                else P(name .. " asked for " .. spell .. ", which you don't have. Not queued.") end
            else
                QueueBuff(name, def.key)
            end
        end
    end
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
local ARRIVE_FALLBACK = 40   -- seconds after Summon before we assume they have arrived
local CLEAN_AFTER = 30       -- finished rows disappear after this many seconds

-- (The 1.x extras list is now the services in Services.lua: see MigrateServices.)
MSG.OFFERMSG = "Welcome {name}! Also on offer today: {offers}. Just ask!"

-- What else is on offer where this customer landed (nil = nothing, say nothing).
local function ArrivalText(job)
    if not job then return nil end
    local g = GroupSnapshot()
    local key = job.service or "summons"
    local p = Core.Provider(g, key, job.dest)
    local here = job.dest or (p and p.zone)
    local custom = ServiceInviterDB.offermsg
    if custom == MSG.OFFERMSG then custom = nil end
    return (Core.ArrivalOffer(ServiceInviterDB, g, Faction(), here, key, Jobs.Label(job), custom))
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
        if ACTIVE[j.status] then list[#list + 1] = j
        elseif j.tdone and now - j.tdone < CLEAN_AFTER then done[#done + 1] = j end
    end
    for _, j in ipairs(done) do list[#list + 1] = j end
    -- too many to show: the newest wait off-screen, never the one who has waited longest
    while #list > ROWS do table.remove(list) end
    return list
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

----------------------------------------------------------------------
-- Customer list look (the design review of 12 Nov 2026): dark and gold, flat, one filled
-- button. Colors are the review's tokens; status pills always carry the word, never color alone.
----------------------------------------------------------------------
local INK = {
    ground = "14110d", deep = "100e0a", panel = "1b1710", line = "3a3226", soft = "2a241b",
    text = "ece4d2", muted = "a39a86", gold = "f0c05a", goldInk = "1a1408", plain = "221d15",
}
INK.PILL = {   -- status -> fill, text
    asked = { "3d3414", "f5df8a" }, invited = { "3d3414", "f5df8a" }, joined = { "1f3a26", "9be3ad" }, summoned = { "1d3144", "9fd0ff" },
    arrived = { "143a3f", "8fe3ea" }, paid = { "2b3216", "cfe59a" }, done = { "2b3216", "cfe59a" },
    busy = { "4a2c12", "ffc58a" }, declined = { "4a1a1a", "ffa5a5" }, noanswer = { "2e2a22", "c9c0a8" },
    left = { "2e2a22", "c9c0a8" },
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
    plain = { INK.plain, INK.line, INK.text }, bare = { nil, nil, "8a8171" }, rail = { nil, nil, INK.text },
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
    b._siStyle, b._siSize = style, size or 14
    return b
end
-- The banner: a small label naming the event, the instruction as the loudest line, who is
-- being summoned, to where and who gets paid, and a bar for the 14 seconds it stays up.
-- Pulses for the first two seconds only (the design review of 12 Nov 2026).
local BANNER = { W = 560, SECS = 14 }
ShowAlert = function(title, sub, label)
    if not alertWin then
        local a = CreateFrame("Frame", "ServiceInviterAlert", UIParent)
        a:SetSize(BANNER.W, 104)
        a:SetPoint("TOP", 0, -150)
        a:SetFrameStrata("FULLSCREEN_DIALOG")
        local edge = Fill(a, "d9504a", "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
        local bg = Fill(a, "8a1414", "BACKGROUND", -7) bg:SetAllPoints()
        a.label = Text(a, 12, "ffd9d4")
        a.label:SetPoint("TOP", 0, -14)
        a.title = Text(a, 34, "ffffff", "GameFontNormalLarge")
        pcall(function() local f = a.title:GetFont() if f then a.title:SetFont(f, 34, "OUTLINE") end end)
        a.title:SetPoint("TOP", 0, -32)
        a.sub = Text(a, 14, "ffe9e5", "GameFontHighlight")
        a.sub:SetPoint("TOP", 0, -74)
        local track = Fill(a, "5a0c0c", "BORDER") track:SetPoint("BOTTOMLEFT", 0, 0) track:SetSize(BANNER.W, 4)
        a.bar = Fill(a, "ffd9d4", "ARTWORK") a.bar:SetPoint("BOTTOMLEFT", 0, 0) a.bar:SetSize(BANNER.W, 4)
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
    alertWin.label:SetText(label or "")
    alertWin.title:SetText(title)
    alertWin.sub:SetText(sub or "")
    alertWin.t = 0
    alertWin.bar:SetWidth(BANNER.W)
    alertWin:Show()
    if PlaySound then
        pcall(PlaySound, (SOUNDKIT and SOUNDKIT.RAID_WARNING) or 8959)
    end
end
-- "Summoning Kaldrok to Thunder Bluff. Pay Grimtotem."
local function BannerSub(who, job)
    local dest = job and job.dest
    local payee, mine = PayeeFor(job or { service = "summons" })
    local pay = (not JobPrice(job or { service = "summons" })) and " Free." or (mine and " Pay: you." or (" Pay " .. tostring(payee) .. "."))
    return "Summoning " .. who .. (dest and (" to " .. dest) or "") .. "." .. pay
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
    SendChatMessage(text, "WHISPER", nil, to)
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

----------------------------------------------------------------------
-- Preview: what each tab's messages will look like, printed in your own chat window only.
-- The owner, 12 Nov 2026: "i should be able to press debug buttons in each panel for things
-- like seeing what the message should look like". It runs the same code that sends the real
-- messages, for a pretend buyer (Kaldrok); it sends nothing, invites nobody, queues nothing.
-- When nobody in the group can do a service, it says so and shows an example with a
-- stand-in of the right class standing with you.
----------------------------------------------------------------------
local PV = {}
PV.TABS = { "General", "Warlock", "Mage", "Rogue", "Buffs", "Advertise" }
PV.KEYS = {
    Warlock = { "summons", "healthstone", "soulstone" }, Mage = { "portals", "water" },
    Rogue = { "lockpick" }, Buffs = { "fort", "motw", "ai", "blessing" },
}
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
        if tab == "General" then
            Head("On sale")
            local items = Core.OnSale(db, GroupSnapshot(), fac)
            local text = OnSaleText(items)
            if not text then
                Note("Nothing on sale, so nobody is invited. Tick a service on a class tab, and have someone in the group who can do it.")
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
        elseif tab == "Buffs" then
            for _, key in ipairs(PV.KEYS.Buffs) do ServicePreview(key) end
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
                local ok, err = pcall(function() SendChatMessage(AlertMsg(who, job, castZone), ch) end)
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
        local ok, err = pcall(ShowAlert, "CLICK THE PORTAL", BannerSub(who, job), "PORTAL IS UP")
        trace.banner = ok and "shown" or ("error: " .. tostring(err))
    elseif first then
        local ok, err = pcall(ShowAlert, "CLICK THE PORTAL", BannerSub(who, job), "RITUAL OF SUMMONING STARTED")
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
            if UnitInParty(nm) or UnitInRaid(nm) then
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
            if visible or (j.tsummon and now - j.tsummon > ARRIVE_FALLBACK) then
                Jobs.Set(j.name, "arrived")
                if visible then QueueAllMyBuffs(j.name) end
                -- tell them what else is on offer where they landed; nothing there = no message
                if not j.offered then
                    j.offered = true
                    local text = ArrivalText(j)
                    local ch = (IsInRaid and IsInRaid()) and "RAID" or ((IsInGroup and IsInGroup()) and "PARTY" or nil)
                    if text and ch then pcall(SendChatMessage, text, ch) end
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
    if tacc >= 1 then tacc = 0 if not ServiceInviterDB.stasis then Report("arrivals", pcall(CheckArrivals)) end end
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
    row.summon:Hide() row.offer:Hide() row.trade:Hide() row.paid:Hide() row.remove:Hide() row.reinvite:Hide()
    if not job then
        for _, t in ipairs(row.paint) do t:Hide() end
        row.name:SetText("") row.status:SetText("") row.where:SetText("") row.service:SetText("") row.age:SetText("") row.note:SetText("")
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
    row.name:SetText(Colored(job.name, job.class) .. (before > 0 and ("  |cff" .. INK.muted .. "· " .. before .. " before|r") or ""))
    row.bar:SetColorTexture(RGB(ClassHex(job.class) or INK.muted))
    row.service:SetText(ServiceLine(job))
    row.where:SetText(WhoLine(job, g))
    row.status:SetText(st[1])
    local pill = INK.PILL[job.status] or INK.PILL.left
    row.pill:SetColorTexture(RGB(pill[1]))
    row.status:SetTextColor(RGB(pill[2]))
    local waiting = job.status == "invited" or job.status == "joined"
    row.age:SetText(waiting and ("waiting " .. Since(job.ts or job.t)) or (Since(job.ts or job.t) .. " ago"))
    row.note:SetText("")
    local n = UnitFor(job.name) or CleanName(job.name)
    row.summon:SetAttribute("macrotext", "/target " .. n .. "\n/cast Ritual of Summoning")
    row.trade:SetAttribute("macrotext", "/target " .. n .. "\n/run InitiateTrade(\"target\")")
    row.paid:SetAttribute("macrotext", KickMacro(job))
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
            local p = Core.Provider(g, "summons", job.dest)
            row.note:SetText(p and (p.me and "Your summon" or (p.name .. " is up")) or "")
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

local function ApplyNext()
    local w = jobsWin
    local asking = false
    for _, j in ipairs(jobs) do if j.status == "asked" then asking = true break end end
    if Role() == "helper" and not asking then
        w.nextBtn:Hide()
        w.nextText:Show()
        local nxt, waiting = nil, 0
        for _, j in ipairs(jobs) do if NextStep(j) == "summon" then nxt = nxt or j waiting = waiting + 1 end end
        w.nextText:SetText(nxt and ("Next up: |cff" .. INK.gold .. nxt.name .. "|r" .. (waiting > 1 and ("  (+" .. (waiting - 1) .. " waiting)") or "")) or "Nobody waiting")
        w.nextMore:SetText("")
        w.nextSub:SetText(nxt and ("The warlock summons; you click the portal.") or "")
        return
    end
    w.nextBtn:Show()
    w.nextText:Hide()
    local job, step = NextJob()
    w.nextBtn.step, w.nextBtn.job = step, job
    -- how many more of yours are waiting after this one
    local more = 0
    for _, j in ipairs(jobs) do
        if j ~= job then
            local st = NextStep(j)
            if (st == "summon" and YouSummon(j)) or st == "offer" or ((st == "finish" or (st == "serve" and JobPrice(j))) and CollectsFor(j)) then more = more + 1 end
        end
    end
    w.nextMore:SetText(more > 0 and (more .. " more of yours waiting") or "")
    if not job then
        w.nextBtn:SetText("Nothing to do")
        w.nextBtn:SetAttribute("macrotext", "")
        w.nextSub:SetText("")
        return
    end
    local n = UnitFor(job.name) or CleanName(job.name)
    w.nextSub:SetText(ServiceLine(job) .. ", waiting " .. Since(job.ts or job.t))
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
end

RefreshJobs = function()
    if not jobsWin or not jobsWin:IsShown() then return end
    if InCombatLockdown and InCombatLockdown() then jobsDirty = true return end
    jobsDirty = false
    CheckArrivals()

    local list = VisibleJobs()
    for i = 1, ROWS do ApplyRow(jobsWin.rows[i], list[i]) end
    if #list == 0 then jobsWin.empty:Show() else jobsWin.empty:Hide() end
    ApplyNext()
    local wait, going, active = 0, 0, 0
    for _, j in ipairs(jobs) do
        if j.status == "joined" then wait = wait + 1 elseif j.status == "summoned" then going = going + 1 end
        if ACTIVE[j.status] then active = active + 1 end
    end
    jobsWin.count:SetText(active > 0 and (active .. " active") or "")
    local st = Stats()
    -- what we summoned and what that's worth (the owner, 13 Nov 2026: "it should still record
    -- EV - how many we summon. the paid will be inaccurate no matter what"). Collected is on
    -- the Setup's General page.
    jobsWin.statSummoned:SetText(tostring(st.summoned or 0))
    jobsWin.statEV:SetText(Money(st.ev or 0))
    local left = Jobs.ShardsLeft()
    jobsWin.statShards:SetText(left and tostring(math.max(0, left)) or "-")
    jobsWin.statWait:SetText(tostring(wait) .. (going > 0 and ("  (" .. going .. " coming)") or ""))
    RefreshBuff()   -- the buff button shows whoever is next, even if they asked before the list was open
    jobsWin.Fit(#list, jobsWin.buffBtn:IsShown())
    if jobsWin.adBtn then
        local label, ready = AdLabel()
        jobsWin.adBtn:SetText(label)
        if ready then jobsWin.adBtn:Enable() else jobsWin.adBtn:Disable() end
    end
end

local function BuildJobsUI()
    local W, ROW_H, GAP = 600, 80, 8
    local TOP = 204                                   -- where the first row starts
    local FOOT, FOOT_BUFF = 76, 126              -- the footer grows when you have a buff button
    local H = TOP + ROWS * (ROW_H + GAP) + 4 + FOOT
    local w = CreateFrame("Frame", "ServiceInviterJobs", UIParent)
    w:SetSize(W, H)
    w:SetPoint("CENTER", 0, 60)
    w:SetFrameStrata("DIALOG")
    w:SetClampedToScreen(true)
    w:SetMovable(true)
    w:EnableMouse(true)
    w:RegisterForDrag("LeftButton")
    w:SetScript("OnDragStart", function(self) self:StartMoving() end)
    w:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    local edge = Fill(w, INK.line, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
    local bg = Fill(w, INK.ground, "BACKGROUND", -7) bg:SetAllPoints()
    w:Hide()
    local function Line(y) local t = Fill(w, INK.soft, "BORDER") t:SetPoint("TOPLEFT", 0, y) t:SetSize(W, 1) return t end

    -- header: title, how many active, Post ad, Setup, close
    local title = Text(w, 20, INK.gold, "GameFontNormalLarge")
    title:SetPoint("TOPLEFT", 24, -21) title:SetText("Customers")
    w.count = Text(w, 13, INK.muted)
    w.count:SetPoint("TOPLEFT", 146, -26)
    local close = FlatButton(w, 36, 36, "bare", 16)
    close:SetPoint("TOPRIGHT", -12, -14) close:SetText("X")
    close:SetScript("OnClick", function() w:Hide() end)
    local setupBtn = FlatButton(w, 72, 36, "plain")
    setupBtn:SetPoint("TOPRIGHT", -56, -14) setupBtn:SetText("Setup")
    setupBtn:SetScript("OnClick", function() ToggleSetup() end)
    local adBtn = FlatButton(w, 150, 36, "plain")
    adBtn:SetPoint("TOPRIGHT", -136, -14) adBtn:SetText("Post ad")
    local regBtn = FlatButton(w, 90, 36, "plain")
    regBtn:SetPoint("TOPRIGHT", -294, -14) regBtn:SetText("Regulars")
    regBtn:SetScript("OnClick", function() Jobs.PrintRegulars("") end)
    w.regularsBtn = regBtn
    adBtn:SetScript("OnClick", function() PostAd() end)
    w.adBtn = adBtn
    Line(-64)

    -- your next job: the one big button. Secure buttons must listen for press AND release:
    -- newer clients fire them on press.
    local lbl = Text(w, 12, INK.muted)
    lbl:SetPoint("TOPLEFT", 24, -86) lbl:SetText("YOUR NEXT JOB")
    w.nextMore = Text(w, 13, INK.muted)
    w.nextMore:SetPoint("TOPRIGHT", -24, -86) w.nextMore:SetJustifyH("RIGHT")
    local nb = FlatButton(w, W - 48, 56, "gold", 20, true, "ServiceInviterNext")
    nb:SetPoint("TOPLEFT", 24, -106)
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
    w.nextText = Text(w, 18, INK.text)
    w.nextText:SetPoint("TOPLEFT", 24, -122)
    w.nextText:SetText("Nobody waiting")
    w.nextSub = Text(w, 13, INK.muted)
    w.nextSub:SetPoint("TOPLEFT", 24, -172) w.nextSub:SetWidth(W - 48) w.nextSub:SetJustifyH("LEFT")
    if w.nextSub.SetWordWrap then w.nextSub:SetWordWrap(false) end

    -- the rows
    w.rows = {}
    for i = 1, ROWS do
        local y = -TOP - (i - 1) * (ROW_H + GAP)
        local row = { paint = {} }
        local rEdge = Fill(w, INK.soft, "BACKGROUND", -6) rEdge:SetPoint("TOPLEFT", 24, y) rEdge:SetSize(W - 48, ROW_H)
        local rBg = Fill(w, INK.panel, "BACKGROUND", -5) rBg:SetPoint("TOPLEFT", 25, y - 1) rBg:SetSize(W - 50, ROW_H - 2)
        row.bar = Fill(w, INK.muted, "BORDER") row.bar:SetPoint("TOPLEFT", 25, y - 1) row.bar:SetSize(4, ROW_H - 2)
        row.pill = Fill(w, INK.PILL.joined[1], "BORDER") row.pill:SetPoint("TOPLEFT", 292, y - 16) row.pill:SetSize(96, 22)
        row.paint = { rEdge, rBg, row.bar, row.pill }

        row.name = Text(w, 16, INK.text, "GameFontHighlightLarge")
        row.name:SetPoint("TOPLEFT", 42, y - 12)
        row.name:SetWidth(236) row.name:SetJustifyH("LEFT")
        if row.name.SetWordWrap then row.name:SetWordWrap(false) end
        row.service = Text(w, 13, INK.text)
        row.service:SetPoint("TOPLEFT", 42, y - 36)
        row.service:SetWidth(236) row.service:SetJustifyH("LEFT")
        if row.service.SetWordWrap then row.service:SetWordWrap(false) end
        row.where = Text(w, 13, INK.muted)
        row.where:SetPoint("TOPLEFT", 42, y - 56)
        row.where:SetWidth(236) row.where:SetJustifyH("LEFT")
        if row.where.SetWordWrap then row.where:SetWordWrap(false) end
        row.status = Text(w, 12, INK.text)
        row.status:SetPoint("TOPLEFT", 292, y - 20)
        row.status:SetWidth(96)
        row.age = Text(w, 12, INK.muted)
        row.age:SetPoint("TOPLEFT", 294, y - 48)
        row.age:SetWidth(96) row.age:SetJustifyH("LEFT")
        row.note = Text(w, 13, INK.muted)
        row.note:SetPoint("TOPLEFT", 396, y - 32)
        row.note:SetWidth(140) row.note:SetJustifyH("RIGHT")
        if row.note.SetWordWrap then row.note:SetWordWrap(false) end

        local AX, AY = 396, y - 22          -- the action slot; Paid sits right of it
        row.summon = FlatButton(w, 84, 36, "ghost", 14, true)
        row.summon:SetPoint("TOPLEFT", AX, AY) row.summon:SetText("Summon")
        row.summon:RegisterForClicks("AnyUp", "AnyDown")
        row.summon:SetAttribute("type", "macro")
        row.summon:HookScript("PostClick", function() if row.job then Jobs.Set(row.job.name, "summoned") RefreshJobs() end end)

        row.offer = FlatButton(w, 84, 36, "ghost", 14, true)
        row.offer:SetPoint("TOPLEFT", AX, AY) row.offer:SetText("Offer")
        row.offer:RegisterForClicks("AnyUp", "AnyDown")
        row.offer:SetAttribute("type", "macro")
        row.offer:HookScript("PreClick", function()
            if row.job then row.offer:SetAttribute("macrotext", ((IsInRaid and IsInRaid()) and "/raid " or "/p ") .. OfferText(row.job.name)) end
        end)
        row.offer:HookScript("PostClick", function() if row.job then row.job.offered = true RefreshJobs() end end)

        row.trade = FlatButton(w, 84, 36, "ghost", 14, true)
        row.trade:SetPoint("TOPLEFT", AX, AY) row.trade:SetText("Trade")
        row.trade:RegisterForClicks("AnyUp", "AnyDown")
        row.trade:SetAttribute("type", "macro")
        row.trade:HookScript("PostClick", function()
            if row.job then pendingTrade = row.job.name D("Trade clicked for " .. row.job.name .. " (macro: " .. tostring(row.trade:GetAttribute("macrotext")) .. ")") end
        end)

        -- Invite / Re-invite: the game's /invite on your click (an addon's own invite becomes a
        -- mere suggestion when you're not the leader)
        row.reinvite = FlatButton(w, 84, 36, "ghost", 14, true)
        row.reinvite:SetPoint("TOPLEFT", AX, AY) row.reinvite:SetText("Re-invite")
        row.reinvite:RegisterForClicks("AnyUp", "AnyDown")
        row.reinvite:SetAttribute("type", "macro")
        row.reinvite:HookScript("PostClick", function()
            if row.job then Jobs.InviteClicked(row.job) RefreshJobs() end
        end)

        -- Paid and x run the game's /uninvite (set in ApplyRow), so the removal is yours, not
        -- the addon's, and the game doesn't block it
        row.paid = FlatButton(w, 56, 36, "plain", 14, true)
        row.paid:SetPoint("TOPLEFT", AX + 88, AY) row.paid:SetText("Paid")
        row.paid:RegisterForClicks("AnyUp", "AnyDown")
        row.paid:SetAttribute("type", "macro")
        row.paid:HookScript("PreClick", function() if row.job then Thank(row.job) end end)
        row.paid:HookScript("PostClick", function() if row.job then FinishJob(row.job.name) RefreshJobs() end end)

        row.remove = FlatButton(w, 28, 36, "bare", 14, true)
        row.remove:SetPoint("TOPLEFT", AX + 148, AY) row.remove:SetText("x")
        row.remove:RegisterForClicks("AnyUp", "AnyDown")
        row.remove:SetAttribute("type", "macro")
        row.remove:HookScript("PostClick", function()
            if not row.job then return end
            -- x = done with this customer: out of the group too, if you may
            RemoveFromGroup(row.job.name)
            Jobs.Remove(row.job.name)
            RefreshJobs()
        end)
        w.rows[i] = row
    end

    w.empty = Text(w, 14, INK.muted)
    w.empty:SetPoint("TOPLEFT", 24, -TOP - 30) w.empty:SetWidth(W - 48)
    w.empty:SetText("Nobody yet. Post an ad, or wait for someone to ask in chat.")

    -- footer: the session and New session, then the buff button when you have buffs to cast.
    -- The window is as tall as the customers it shows. Fit runs out of combat only
    -- (RefreshJobs never runs in combat, when the window can't be resized).
    local deep = Fill(w, INK.deep, "BACKGROUND", -6)
    local footLine = Fill(w, INK.soft, "BORDER")
    local bb = FlatButton(w, W - 48, 36, "plain", 14, true)
    bb:SetPoint("BOTTOMLEFT", 24, 16)
    bb:RegisterForClicks("AnyUp", "AnyDown")
    bb:SetAttribute("type", "macro")
    bb:SetText("No buffs waiting")
    bb:Hide()
    w.buffBtn = bb
    local stats = {}
    local function Stat(x, label)
        local l = Text(w, 12, INK.muted) l:SetText(label)
        local v = Text(w, 16, label == "Expected" and INK.gold or INK.text, "GameFontHighlightLarge")
        stats[#stats + 1] = { l, v, x }
        return v
    end
    w.statSummoned = Stat(24, "Summoned")
    w.statEV = Stat(104, "Expected")
    w.statWait = Stat(262, "Waiting")
    w.statShards = Stat(378, "Shards left")
    local newBtn = FlatButton(w, 100, 36, "plain")
    newBtn:SetText("New session")
    function w.Fit(shown, withBuff)
        local body = TOP + math.max(1, shown) * (ROW_H + GAP) + 4
        local f = withBuff and FOOT_BUFF or FOOT
        w:SetHeight(body + f)
        deep:ClearAllPoints() deep:SetPoint("TOPLEFT", 0, -body) deep:SetSize(W, f)
        footLine:ClearAllPoints() footLine:SetPoint("TOPLEFT", 0, -body) footLine:SetSize(W, 1)
        for _, st in ipairs(stats) do
            st[1]:ClearAllPoints() st[1]:SetPoint("TOPLEFT", st[3], -body - 14)
            st[2]:ClearAllPoints() st[2]:SetPoint("TOPLEFT", st[3], -body - 32)
        end
        newBtn:ClearAllPoints() newBtn:SetPoint("TOPRIGHT", -24, -body - 20)
    end
    w.Fit(1, false)
    newBtn:SetScript("OnClick", function() NewSession() RefreshJobs() P("new session started") end)

    local acc = 0
    w:SetScript("OnUpdate", function(_, elapsed)
        acc = acc + (elapsed or 0)
        if acc >= 1 then acc = 0 Report("customer list", pcall(RefreshJobs)) end
    end)
    w:SetScript("OnShow", RefreshJobs)
    return w
end

local function ToggleJobs()
    jobsWin = jobsWin or BuildJobsUI()
    if jobsWin:IsShown() then jobsWin:Hide() else jobsWin:Show() end
end

jobsChanged = function(openIt)
    if openIt and Opt("autoshow") then
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
    if not picker then
        picker = CreateFrame("Frame", "ServiceInviterPicker", UIParent)
        picker:SetFrameStrata("FULLSCREEN_DIALOG")
        picker:EnableMouse(true)
        local edge = Fill(picker, INK.gold, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
        local bg = Fill(picker, INK.ground, "BACKGROUND", -7) bg:SetAllPoints()
        picker.title = Text(picker, 14, INK.gold, "GameFontNormal")
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
            if m.class == only then entries[#entries + 1] = { Colored(m.me and (m.name .. " (you)") or m.name, m.class) .. (m.zone and ("  (" .. m.zone .. ")") or ""), m.name } end
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
    if only and #entries == 0 then picker.note:SetText("Nobody of that class in your group right now.")
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
    local RAIL, PW, H = 168, 900, 690          -- the side menu, then the 900-wide page
    local W = RAIL + PW
    local w = CreateFrame("Frame", "ServiceInviterSetup", UIParent)
    w:SetSize(W, H)
    w:SetPoint("CENTER", 0, 20)
    w:SetFrameStrata("DIALOG")
    w:SetClampedToScreen(true)
    w:SetMovable(true) w:EnableMouse(true)
    w:RegisterForDrag("LeftButton")
    w:SetScript("OnDragStart", function(self) self:StartMoving() end)
    w:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    -- solid and near black, so the setup is easy to read over anything behind it (the owner,
    -- 12 Nov 2026), in the customer list's dark and gold
    local edge = Fill(w, INK.line, "BACKGROUND", -8) edge:SetPoint("TOPLEFT", -1, 1) edge:SetPoint("BOTTOMRIGHT", 1, -1)
    local bg = Fill(w, INK.ground, "BACKGROUND", -7) bg:SetAllPoints()
    w.bg = bg
    local rail = Fill(w, INK.deep, "BACKGROUND", -6) rail:SetPoint("TOPLEFT", 0, 0) rail:SetSize(RAIL, H)
    local railLine = Fill(w, INK.soft, "BORDER") railLine:SetPoint("TOPLEFT", RAIL, 0) railLine:SetSize(1, H)
    w:Hide()

    local brand = Text(w, 16, INK.gold, "GameFontNormalLarge")
    brand:SetPoint("TOPLEFT", 20, -22) brand:SetText("Service Inviter")
    local title = Text(w, 20, INK.text, "GameFontHighlightLarge")
    title:SetPoint("TOPLEFT", RAIL + 28, -18) title:SetText("General")
    local close = FlatButton(w, 36, 36, "bare", 16)
    close:SetPoint("TOPRIGHT", -12, -10) close:SetText("X")
    close:SetScript("OnClick", function() w:Hide() end)

    local boxes, checks, radios = {}, {}, {}
    local optKeys = {}     -- checkboxes that simply map to an option
    local page             -- the tab being built

    local function Header(x, y, text)
        local fs = page:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        fs:SetPoint("TOPLEFT", x, y) fs:SetText(text)
        return fs
    end
    local function Label(x, y, text, font, width)
        local fs = page:CreateFontString(nil, "OVERLAY", font or "GameFontNormal")
        fs:SetPoint("TOPLEFT", x, y) fs:SetText(text)
        if width then fs:SetWidth(width) fs:SetJustifyH("LEFT") end
        return fs
    end
    local function Box(key, x, y, width, maxLetters)
        local eb = CreateFrame("EditBox", nil, page, "InputBoxTemplate")
        eb:SetPoint("TOPLEFT", x, y)
        eb:SetSize(width or 400, 22)
        eb:SetAutoFocus(false)
        eb:SetMaxLetters(maxLetters or 255)
        eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
        eb:SetScript("OnEnterPressed", function(self) self:ClearFocus() end)
        boxes[key] = eb
        return eb
    end
    local function Check(key, x, y, text, isOpt)
        local cb = CreateFrame("CheckButton", nil, page, "UICheckButtonTemplate")
        cb:SetSize(26, 26) cb:SetPoint("TOPLEFT", x, y)
        if text then
            local fs = page:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
            fs:SetPoint("LEFT", cb, "RIGHT", 2, 0) fs:SetText(text)
            cb.label = fs
        end
        checks[key] = cb
        if isOpt then optKeys[#optKeys + 1] = key end
        return cb
    end
    -- radio: checkboxes in a group where ticking one unticks the others
    local function Radio(group, key, x, y, text, onPick)
        local cb = Check(key, x, y, text)
        radios[group] = radios[group] or {}
        radios[group][#radios[group] + 1] = cb
        cb:SetScript("OnClick", function()
            for _, other in ipairs(radios[group]) do other:SetChecked(other == cb) end
            if onPick then onPick() end
        end)
        return cb
    end
    -- one service: offer it, price (blank = free), invite, words, who gets paid
    local function Service(key, x, y)
        local def = Core.BY_KEY[key]
        local k = "svc_" .. key .. "_"
        Check(k .. "on", x, y, (def.kind == "buff" and "We offer " or "We sell ") .. def.label)
        Label(x + 4, y - 32, "Price:")
        Box(k .. "g", x + 52, y - 28, 44, 5) Label(x + 100, y - 32, "g")
        Box(k .. "s", x + 116, y - 28, 30, 2) Label(x + 150, y - 32, "s", nil)
        Label(x + 166, y - 33, "blank = free", "GameFontHighlightSmall")
        Check(k .. "invite", x, y - 54, "Invite buyers who ask for it")
        local dy = 86
        if def.words then
            Label(x + 4, y - dy, "Buyers say:")
            Box(k .. "words", x + 92, y - dy + 4, 300, 200)
            dy = dy + 28
        end
        Label(x + 4, y - dy, "Who gets paid:")
        local pb = Box(k .. "payee", x + 112, y - dy + 4, 130, 40)
        PickButton(page, pb, true, "Who gets paid for " .. def.label .. "?", key)
        Label(x + 276, y - dy - 1, "blank = General tab", "GameFontHighlightSmall")
        return dy + 28
    end

    -- tabs ----------------------------------------------------------------
    local TABS = { "General", "Warlock", "Mage", "Rogue", "Buffs", "Advertise" }
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
        railBar:ClearAllPoints() railBar:SetPoint("TOPLEFT", 0, -64 - (i - 1) * 44)
        title:SetText(TABS[i])
        w.tab = i
    end
    for i, name in ipairs(TABS) do
        local pg = CreateFrame("Frame", nil, w)
        pg:SetPoint("TOPLEFT", RAIL, -14) pg:SetSize(PW, H - 14)   -- below the page title
        pages[i] = pg
        local sel = Fill(w, INK.panel, "BACKGROUND", -5) sel:SetPoint("TOPLEFT", 0, -64 - (i - 1) * 44) sel:SetSize(RAIL, 40)
        local b = FlatButton(w, RAIL, 40, "rail", 15)
        b:SetPoint("TOPLEFT", 0, -64 - (i - 1) * 44)
        b:GetFontString():ClearAllPoints() b:GetFontString():SetPoint("LEFT", 20, 0)
        b:SetText(name)
        b:SetScript("OnClick", function() ShowTab(i) end)
        b.sel = sel
        tabBtns[i] = b
    end
    railBar = Fill(w, INK.gold, "ARTWORK") railBar:SetSize(3, 40)
    w.pages, w.tabBtns, w.ShowTab, w.tab = pages, tabBtns, ShowTab, 1

    local L, R = 28, 470

    -- General: who gets invited, who gets paid, the messages ---------------
    page = pages[1]
    Header(L, -50, "Who gets invited")
    Check("enabled", L, -74, "Invite buyers of what we sell", true)
    Label(L, -108, "Listen in:")
    Check("trade", L + 76, -102, "Trade", true)
    Check("general", L + 156, -102, "General", true)
    Check("say", L + 246, -102, "Say", true)
    Check("yell", L + 316, -102, "Yell", true)
    Label(L, -138, "+ other channels:")
    Box("chanextra", L + 140, -134, 250, 100)
    Check("strictbuy", L, -162, "Only 'WTB' / 'buying' (skip LF, need, looking)", true)
    Check("fragments", L, -188, "Combine a person's split messages", true)
    Check("skipafk", L, -214, "Skip while I'm AFK", true)
    Check("announce", L, -240, "Show a line in chat when I invite", true)
    Check("autoshow", L, -266, "Open the customer list when I invite someone", true)
    Check("kwon", L, -292, "Auto-invite anyone who says:", true)
    Box("kwwords", L + 236, -294, 170, 60)
    Check("dryrun", L, -322, "Dry run")
    Check("near", L + 110, -322, "Near-miss lines")
    Check("debug", L + 270, -322, "Debug")
    Header(L, -362, "On sale right now")
    w.onsale = Label(L, -388, "", "GameFontHighlight", 410)

    Header(R, -50, "Who gets paid (default)")
    local function SyncTradeBox()
        local named = checks.pay_name and checks.pay_name:GetChecked()
        if named then checks.autotrade:Disable() else checks.autotrade:Enable() end
        if checks.autotrade.label then checks.autotrade.label:SetFontObject(named and "GameFontDisable" or "GameFontHighlight") end
    end
    Radio("pay", "pay_place", R, -74, "Whoever does it (the warlock, mage, rogue...)", SyncTradeBox)
    Label(R + 30, -100, "You get paid only if you pick 'Always me' (or 'Me' on a service).", "GameFontHighlightSmall")
    Radio("pay", "pay_me", R, -116, "Always me", SyncTradeBox)
    Radio("pay", "pay_name", R, -142, "Always:", SyncTradeBox)
    local pn = Box("payname", R + 100, -144, 160, 40)
    PickButton(page, pn, false, "Who always gets paid?")
    Check("autotrade", R, -172, "Open trade by itself when it's me and they're in range")
    Label(R, -202, "Each service can name its own payee on its tab.", "GameFontHighlightSmall")
    Header(R, -232, "Messages")
    Check("welcome", R, -256, "Welcome them when they join")
    Label(R, -286, "Welcome text, blank = automatic (what, who, where, price, who to pay).", "GameFontHighlightSmall", 400)
    Label(R, -300, "Yours can use {name} {service} {price} {payee} {visits}.", "GameFontHighlightSmall", 400)
    Box("welcomemsg", R + 4, -316, 396)
    Label(R, -348, "On arrival, blank = automatic (what else is on offer where they landed).", "GameFontHighlightSmall", 400)
    Label(R, -362, "Yours can use {name} {here} {offers}.", "GameFontHighlightSmall", 400)
    Box("offermsg", R + 4, -378, 396)
    Check("thanks", R, -410, "When they're done, whisper ({name}):")
    Box("thanksmsg", R + 4, -438, 396)
    Check("marks", R, -470, "Raid icon on whoever does it, in party and raid chat", true)
    Label(R, -500, "Regulars hear ({visits} = 4th, empty = off):")
    Box("loyaltymsg", R + 4, -522, 396)
    Header(R, -556, "This session")
    local sessText = Label(R, -582, "", "GameFontHighlight", 270)
    local sessBtn = FlatButton(page, 120, 30, "plain")
    sessBtn:SetPoint("TOPLEFT", R + 286, -576) sessBtn:SetText("New session")
    sessBtn:SetScript("OnClick", function() NewSession() sessText:SetText(SessionText()) RefreshJobs() end)
    w.sessText = sessText

    -- Warlock --------------------------------------------------------------
    page = pages[2]
    Service("summons", L, -50)
    Header(L, -168, "Who summons")
    Radio("role", "rolelock", L, -192, "I do (I'm the warlock)")
    Radio("role", "rolehelper", L, -218, "A friend in the group does; I click the portal")
    Header(L, -256, "Summons go to")
    w.locks = Label(L, -282, "", "GameFontHighlight", 410)
    Label(L, -330, "Each warlock summons to wherever they're standing. If the game can't tell where a warlock is, nobody is invited for their summons.", "GameFontHighlightSmall", 410)
    -- "Ours": only these count (the owner, 13 Nov 2026: "yeah our warlock and we can auto fill from the raid")
    local function Ours(cls, word, y)
        Header(L, y, "Our " .. word)
        Label(L, y - 26, "Only these sell. Blank = any " .. word:gsub("s$", "") .. " in the group who isn't a customer.", "GameFontHighlightSmall", 410)
        local b = Box("prov_" .. cls, L + 4, y - 46, 330, 200)
        PickButton(page, b, false, "Our " .. word .. " (from your group)", "class:" .. cls)
    end
    Ours("WARLOCK", "warlocks", -380)
    Header(R, -50, "When the warlock starts summoning")
    Check("raidalert", R, -74, "Say in raid ({name} {dest} {payee} {price}):")
    Box("alertmsg", R + 4, -102, 396)
    Label(R, -134, "Whisper to (blank = nobody):")
    Box("whisperto", R + 210, -130, 150, 40)
    Label(R, -162, "Whisper text ({name}, {next} = who waits longest):", "GameFontHighlightSmall")
    Box("whispermsg", R + 4, -178, 396)
    local y = -216
    y = y - Service("healthstone", R, y) - 8
    Service("soulstone", R, y)

    -- Mage -----------------------------------------------------------------
    page = pages[3]
    Service("portals", L, -50)
    Header(L, -168, "Portals")
    Label(L, -194, "Read from your spellbook if you're the mage, otherwise from the mage's level. A mage never offers the city he's standing in. Untick any they haven't trained:", "GameFontHighlightSmall", 410)
    w.portalChecks = {}
    for i, pl in ipairs(Core.PORTALS[Faction()] or {}) do
        local city = pl[1]
        Check("portal_" .. city, L, -236 - (i - 1) * 26, city .. "  (level " .. pl[2] .. ")")
        w.portalChecks[#w.portalChecks + 1] = city
    end
    Ours("MAGE", "mages", -330)
    Service("water", R, -50)

    -- Rogue ----------------------------------------------------------------
    page = pages[4]
    Service("lockpick", L, -50)
    Ours("ROGUE", "rogues", -210)

    -- Buffs ----------------------------------------------------------------
    page = pages[5]
    Label(L, -50, "Buffs are free unless you set a price. Offered once when a customer arrives where you are.", "GameFontHighlightSmall", 840)
    Service("fort", L, -76)
    Service("motw", R, -76)
    Service("ai", L, -236)
    local bh = Service("blessing", R, -236)
    Label(R + 4, -236 - bh - 4, "Blessing to cast:")
    Box("blessing_spell", R + 130, -236 - bh, 200, 60)
    Label(L, -420, "The buff button casts these on whoever is next: customers landing where you are, and anyone in the group who asks. Bind it with /si bind buff F8.", "GameFontHighlightSmall", 840)

    -- Advertise --------------------------------------------------------------
    page = pages[6]
    Header(L, -50, "Advertise")
    Label(L, -78, "The game only lets an ad go out when you press a key or click, so it's one press per ad. The text comes from what is on sale; a whispered 'inv' within 10 minutes counts as an answer to your ad.", "GameFontHighlightSmall", 840)
    Label(L, -118, "Ad ({wts} = 'WTS ' when anything is paid, {services} = what's on sale):")
    Box("admsg", L + 4, -136, 600)
    Label(L, -172, "Post in:")
    Check("adch_trade", L + 70, -166, "Trade")
    Check("adch_general", L + 160, -166, "General")
    Label(L + 270, -172, "+ other channels:")
    Box("adextra", L + 410, -168, 180, 100)
    Label(L, -206, "Wait between ads in a channel:")
    Box("adwait", L + 230, -202, 40, 3)
    Label(L + 280, -206, "minutes")
    Label(L, -240, "Preview:")
    w.adpreview = Label(L + 72, -240, "", "GameFontHighlight", 760)
    local post = FlatButton(page, 220, 34, "gold", 15)
    post:SetPoint("TOPLEFT", L, -282) post:SetText("Post ad")
    post:SetScript("OnClick", function() w.Save() PostAd() w.Load() end)
    w.adpost = post
    Label(L + 236, -290, "Bind a key so you don't need this window: /si bind ad F7", "GameFontHighlightSmall")

    local DEFAULTS_BY_KEY = {
        welcomemsg = "", offermsg = "", thanksmsg = MSG.THANKS, loyaltymsg = MSG.LOYALTY, alertmsg = MSG.ALERTMSG, whispermsg = MSG.WHISPERMSG, admsg = MSG.AD,
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
        w.onsale:SetText(#parts > 0 and table.concat(parts, ", ") or "Nothing. Nobody in the group can do what's ticked on the class tabs.")
        local locks = {}
        for _, m in ipairs(Core.Providers(GroupSnapshot(), "summons")) do
            locks[#locks + 1] = Colored(m.me and "You" or m.name, m.class) .. ": " .. (m.zone or "where? (the game didn't say)")
        end
        w.locks:SetText(#locks > 0 and table.concat(locks, "\n") or "No warlock in the group who can summon.")
        local text, why = Core.BuildAd(ServiceInviterDB, GroupSnapshot(), Faction(), ServiceInviterDB.admsg)
        w.adpreview:SetText(text or ("(no ad: " .. tostring(why) .. ")"))
        local label, ready = AdLabel()
        w.adpost:SetText(label)
        if ready then w.adpost:Enable() else w.adpost:Disable() end
        sessText:SetText(SessionText())
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
            boxes[k .. "payee"]:SetText(st.payee or "")
        end
        boxes.blessing_spell:SetText(Core.Setting(db, "blessing").spell or "")
        local prov = type(db.providers) == "table" and db.providers or {}
        for _, cls in ipairs({ "WARLOCK", "MAGE", "ROGUE" }) do boxes["prov_" .. cls]:SetText(prov[cls] or "") end
        local untick = Core.Setting(db, "portals").untick
        for _, city in ipairs(w.portalChecks) do checks["portal_" .. city]:SetChecked(not untick[city]) end
        SyncTradeBox()
        Refresh()
    end

    function w.Save()
        local db = ServiceInviterDB
        for key, def in pairs(DEFAULTS_BY_KEY) do
            local v = boxes[key]:GetText()
            if key == "loyaltymsg" and v == "" then db[key] = ""            -- empty = off
            elseif v == "" or v == def then db[key] = nil else db[key] = v end
        end
        local who = (boxes.whisperto:GetText():gsub("%s+", ""))
        db.whisperto = (who == "") and false or who
        db.raidalert = checks.raidalert:GetChecked() and true or false
        db.autotrade = checks.autotrade:GetChecked() and true or false
        SetOpt("welcome", checks.welcome:GetChecked() and true or false)
        db.thanks = checks.thanks:GetChecked() and true or false
        for _, k in ipairs(optKeys) do SetOpt(k, checks[k]:GetChecked() and true or false) end
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
            saved.payee = (boxes[k .. "payee"]:GetText():gsub("^%s+", ""):gsub("%s+$", ""))
            db.services[def.key] = saved
        end
        local untick = {}
        for _, city in ipairs(w.portalChecks) do if not checks["portal_" .. city]:GetChecked() then untick[city] = true end end
        db.services.portals.untick = untick
        local bs = boxes.blessing_spell:GetText():gsub("^%s+", ""):gsub("%s+$", "")
        db.services.blessing.spell = (bs ~= "") and bs or nil
        db.providers = {}
        for _, cls in ipairs({ "WARLOCK", "MAGE", "ROGUE" }) do
            local t = boxes["prov_" .. cls]:GetText():gsub("^[%s,]+", ""):gsub("[%s,]+$", "")
            db.providers[cls] = (t ~= "") and t or nil
        end
        RefreshJobs()
    end

    local save = FlatButton(w, 120, 34, "gold", 15)
    save:SetPoint("BOTTOMLEFT", RAIL + 28, 20) save:SetText("Save")
    save:SetScript("OnClick", function() w.Save() w.Load() P("setup saved") end)
    -- Preview: what this tab's messages look like, in your chat only (sends nothing)
    local prev = FlatButton(w, 180, 34, "plain", 14)
    prev:SetPoint("BOTTOMLEFT", RAIL + 160, 20) prev:SetText("Preview this tab")
    prev:SetScript("OnClick", function() w.Save() w.Load() PrintPreview(TABS[w.tab or 1]) end)
    w.preview = prev
    local test = FlatButton(w, 140, 34, "plain", 14)
    test:SetPoint("BOTTOMLEFT", RAIL + 352, 20) test:SetText("Test banner")
    test:SetScript("OnClick", function() ShowAlert("CLICK THE PORTAL", "Summoning Testy to Thunder Bluff. Pay: you.", "TEST: RITUAL OF SUMMONING STARTED") end)

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
        if rest == "" or rest == "off" then
            ServiceInviterDB.outframe = nil
            P("output: auto (window named TI, else main window)")
        elseif n and _G["ChatFrame" .. n] then
            ServiceInviterDB.outframe = n
            P("output now goes to chat window " .. n)
        else
            P("usage: /si out <chat window number 1-10>   or /si out off")
        end
    elseif cmd == "selftest" then SelfTest()
    elseif cmd == "dryrun" then
        ServiceInviterDB.dryrun = not ServiceInviterDB.dryrun
        P("dry run " .. (ServiceInviterDB.dryrun and "ON: it will only SAY who it would invite" or "OFF: it will really invite"))
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
        if jobsWin then jobsWin:Hide() end
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
    elseif cmd == "shards" then
        local r = rest:lower()
        if r == "off" then ServiceInviterDB.shards = nil
        elseif tonumber(r) then ServiceInviterDB.shards = math.max(0, math.floor(tonumber(r)))
        elseif r ~= "" then P("/si shards 20 (other warlocks' shards), /si shards off") return end
        local have, own, typed = Jobs.Shards()
        if not have then P("not counting shards. /si shards 20 to count other warlocks' shards") return end
        P("shards: " .. have .. (own and typed and (" (" .. own .. " yours, " .. typed .. " typed)") or "") ..
            ", " .. Jobs.Queued() .. " summons queued, " .. math.max(0, Jobs.ShardsLeft()) .. " left")
        RefreshJobs()
    elseif cmd == "stats" or cmd == "analytics" then
        Jobs.PrintStats()
    elseif cmd == "customers" or cmd == "regulars" then
        Jobs.PrintRegulars(rest)
    elseif cmd == "session" then
        if rest:lower() == "new" or rest:lower() == "reset" then NewSession() P("new session started")
        else P("session: " .. SessionText() .. "   (/si session new to start over)") end
    elseif cmd == "role" then
        local r = rest:lower()
        if r == "lock" or r == "warlock" then ServiceInviterDB.role = "lock" P("role: lock. Summon and Offer buttons are back. Who takes the money is separate: /si collect.")
        elseif r == "helper" then ServiceInviterDB.role = "helper" P("role: helper. Alerts you to click the portal; the lock does the summoning. Who takes the money is separate: /si collect.")
        else P("role is " .. Role() .. ". Use /si role helper  or  /si role lock") end
        RefreshJobs()
    elseif cmd == "alert" then
        ShowAlert("CLICK THE PORTAL", "Summoning Testy to Thunder Bluff. Pay: you.", "TEST: RITUAL OF SUMMONING STARTED")
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
        P("/si = customers | /si setup = every message and option | /si session = earnings | /si customers = your regulars (/si customers all, /si customers NAME) | /si stats = where, what, when | /si shards 20 = other warlocks' shards | /si worker NAME = one of yours, not a customer | /si workers group | /si stop = stasis, /si start | /si preview | /si status = what it hears | /si simcast = test the alert | /si session new | /si collect = who takes the money | /si on | /si off | /si selftest")
    end
end

-- Exposed for offline testing only.
ServiceInviter_Test = { Ordinal = function(n) return Jobs.Ordinal(n) end, Preview = function(t) return Preview(t) end, PrintPreview = function(t) return PrintPreview(t) end, BuffLabel = function() return BuffLabel() end, RefreshBuff = function() return RefreshBuff() end, ShowPicker = function(box, d, t, k) return ShowPicker(box, d, t, k) end, SetupChecks = function() setupWin = setupWin or BuildSetupUI() return setupWin.checks end, SetupBoxes = function() setupWin = setupWin or BuildSetupUI() return setupWin.boxes end, PostAd = function() return PostAd() end, AdState = function() return AdState() end, Group = function() return GroupSnapshot() end, LiveTargets = function() return LiveTargets() end, WelcomeText = function(n) return WelcomeText(n) end, ArrivalText = function(j) return ArrivalText(j) end, Norm = Norm, Evaluate = Evaluate, ToggleUI = ToggleUI, Opt = Opt, Jobs = Jobs, BuildSetup = function() setupWin = setupWin or BuildSetupUI() return setupWin end, WhisperText = WhisperText, Stats = Stats, NextStep = NextStep, OfferText = OfferText, NextJob = NextJob, OnCast = OnCast, CheckArrivals = CheckArrivals, Role = Role,
    Refresh = function() jobsWin = jobsWin or BuildJobsUI() RefreshJobs() end }
