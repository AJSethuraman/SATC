-- Service Inviter v1.5.0
-- Watches chat for people asking to BUY a summon or port to a destination you
-- choose, and sends them a group invite. It also talks in your group and may
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

local FRAGMENT_WINDOW = 25
local MAX_FRAGMENTS   = 3
local MAX_PER_MINUTE  = 6
local MAX_PARTY       = 5

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
    nodest    = true,    -- "WTB summon" with no place named counts as Thunder Bluff
    announce  = true,    -- print a line in your chat window when it invites
    skipafk   = true,
    autoshow  = true,    -- open the customer list when someone is invited
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
local DEFAULT_WELCOME = "WELCOME {name}! THE COST IS {price}. SUMMONING YOU SOON, I WILL TRADE YOU ON ARRIVAL!"
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
local DEFAULT_CHANNELS = "summons"
local function InExtraChannel(ch)
    ch = (ch or ""):lower()
    local list = ServiceInviterDB.chanextra
    if type(list) ~= "string" then list = DEFAULT_CHANNELS end
    for name in list:lower():gmatch("[^,]+") do
        name = name:gsub("^%s+", ""):gsub("%s+$", "")
        if name ~= "" and ch:find(name, 1, true) then return true end
    end
    return false
end

-- Returns true, reason or false, reason.
-- dedicated = the message came from one of your own channels, where everybody is asking for
-- summons/ports anyway: "wtb uc" is enough, no summon/port word needed.
local function Evaluate(norm, dedicated)
    local sell = HasAny(norm, SELLER)
    if sell then return false, "seller/ad word: " .. sell end

    local buy = HasAny(norm, Opt("strictbuy") and STRICTBUY or BUY)
    if not buy then return false, "no buy word" end
    if not HasAny(norm, STRICTBUY) then
        local soft = HasAny(norm, SOFTSELLER)
        if soft then return false, "seller/ad word '" .. soft .. "' without a WTB/buying word" end
        local c = HasAny(norm, CONTACT)
        if c then return false, "contact word '" .. c .. "' without a WTB/buying word" end
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
    local strippedFrom = false
    for _, d in ipairs(DESTS) do
        for _, w in ipairs(d.words) do
            for _, pre in ipairs({ " from ", " in ", " at " }) do
                local n, count = norm:gsub(pre .. w .. " ", " ")
                if count > 0 then norm = n strippedFrom = true end
            end
        end
    end

    -- "port to TB in UC": an explicit "to <place>" is the destination; any other place
    -- named (in/at UC) is where they are standing, so it does not count.
    local toKeys, anyTo = {}, false
    for _, d in ipairs(DESTS) do
        for _, w in ipairs(d.words) do
            if norm:find(" to " .. w .. " ", 1, true) or norm:find(" 2 " .. w .. " ", 1, true) then toKeys[d.key] = true anyTo = true end
        end
    end

    local sawDest = false
    for _, d in ipairs(DESTS) do
        if (not anyTo or toKeys[d.key]) and HasAny(norm, d.words) then
            sawDest = true
            if wantsSum and Opt("sum_" .. d.key) then return true, "summon to " .. d.label .. ", buy=" .. buy end
            if wantsPort and Opt("port_" .. d.key) then return true, "port to " .. d.label .. ", buy=" .. buy end
        end
    end
    if waived and not sawDest then return false, "no place named (needs one when there is no summon/port word)" end
    if wantsSum and Opt("sum_any") then return true, "summon (any destination), buy=" .. buy end
    if wantsPort and Opt("port_any") then return true, "port (any destination), buy=" .. buy end
    if strippedFrom and not sawDest then sawDest = true end
    if not sawDest and Opt("nodest") then
        if wantsSum and Opt("sum_tb") then return true, "summon, no place named: assuming Thunder Bluff, buy=" .. buy end
        if wantsPort and Opt("port_tb") then return true, "port, no place named: assuming Thunder Bluff, buy=" .. buy end
    end
    return false, sawDest and "that destination/service is not checked" or "no checked destination"
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
    if direct and IsInGroup() and not IsInRaid() and GetNumGroupMembers() >= MAX_PARTY then
        if C_PartyInfo and C_PartyInfo.ConvertToRaid then
            C_PartyInfo.ConvertToRaid()
        elseif ConvertToRaid then
            ConvertToRaid()
        end
    end
    return true, direct
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
    invited   = { "Invited",   "|cfff0d470" },
    joined    = { "In group",  "|cff8fe3a0" },
    summoned  = { "Summoning", "|cff8fbff0" },
    arrived   = { "Arrived",   "|cff8fe3f0" },
    paid      = { "Paid",      "|cffb6d98a" },
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
local function Price() return ServiceInviterDB.price or 25 end   -- stored in silver (100 silver = 1 gold)
local function PriceParts(total)
    total = math.floor(tonumber(total) or Price())
    return math.floor(total / 100), total % 100
end
-- {price} in messages: "25S" / "1G 25S" / "2G"   and   "25 SILVER" / "1 GOLD 25 SILVER" / "2 GOLD"
local function PriceShort(total)
    local g, sv = PriceParts(total)
    if g == 0 and sv == 0 then return "FREE" end
    local t = {}
    if g > 0 then t[#t + 1] = g .. "G" end
    if sv > 0 then t[#t + 1] = sv .. "S" end
    return table.concat(t, " ")
end
local function PriceLong(total)
    local g, sv = PriceParts(total)
    if g == 0 and sv == 0 then return "FREE" end
    local t = {}
    if g > 0 then t[#t + 1] = g .. " GOLD" end
    if sv > 0 then t[#t + 1] = sv .. " SILVER" end
    return table.concat(t, " ")
end
-- "1g 25s", "2g", "150s", "25" (a bare number = silver)  ->  silver, or nil
local function ParsePrice(text)
    text = (text or ""):lower()
    local g, sv = text:match("(%d*%.?%d+)%s*g"), text:match("(%d+)%s*s")
    if g or sv then return math.floor((tonumber(g) or 0) * 100 + 0.5) + (tonumber(sv) or 0) end
    local n = tonumber(text:match("^%s*(%d+)%s*$"))
    return n
end
local function Role() return ServiceInviterDB.role == "lock" and "lock" or "helper" end
local DEFAULT_WHISPERMSG = "Summoning {name}. Next: {next}"   -- {name} = who we summon, {next} = who has waited longest after
local DEFAULT_ALERTMSG = "SUMMONING {name}! PAY ME {price} IN THE TRADE WINDOW ON ARRIVAL!"
local OnCast            -- set below: reacts to a group member starting Ritual of Summoning
local ShowAlert         -- set below: big on-screen "click the portal" banner
local ToggleSetup       -- set below: opens the Setup window
local function AutoTradeOn()
    return ServiceInviterDB.autotrade ~= false
end
-- Who takes the money is a setting, not the role: some nights the lock collects,
-- some nights you do. Until it is set, the lock collects.
local function Collects()
    local c = ServiceInviterDB.collect
    if c == nil then return Role() == "lock" end
    return c and true or false
end
local function Money(silver)
    local g, s = math.floor(silver / 100), silver % 100
    if g > 0 then return g .. "g " .. s .. "s" end
    return s .. "s"
end

local function SessionText()
    local st = Stats()
    local text = "Real " .. Money(st.silver) .. " (" .. st.paid .. " paid)   EV " .. Money(st.ev) .. " (" .. st.summoned .. " summoned)"
    if st.ev > 0 then text = text .. "   " .. math.floor(st.silver * 100 / st.ev + 0.5) .. "% collected" end
    local hours = (Now() - st.start) / 3600
    if hours >= 0.083 and st.silver > 0 then text = text .. "  (" .. Money(math.floor(st.silver / hours)) .. "/hr)" end
    return text
end
local function NewSession() ServiceInviterDB.stats = nil return Stats() end

local Jobs = {}
function Jobs.All() return jobs end
function Jobs.Get(name) return jobByName[name] end

function Jobs.New(name, text, why, channel)
    local old = jobByName[name]
    if old then
        for i, j in ipairs(jobs) do if j == old then table.remove(jobs, i) break end end
    end
    local job = { name = name, text = text, why = why, channel = channel, status = "invited", t = GetTime() }
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
    if status == "summoned" then Stats().summoned = Stats().summoned + 1 Stats().ev = Stats().ev + Price() j.tsummon = GetTime() end
    if status == "arrived" then j.tarrive = GetTime() end
    if status == "paid" then Stats().paid = Stats().paid + 1 Stats().silver = Stats().silver + (j.amount or Price()) end
    if status == "paid" or status == "left" or status == "declined" or status == "noanswer" then j.tdone = GetTime() end
    j.status = status
    jobsChanged()
    return j
end

function Jobs.Joined(name)
    local j = jobByName[name]
    if j and j.status == "invited" then Jobs.Set(name, "joined") return true end
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
        if j.status == "invited" and now - j.t > INVITE_TIMEOUT then Jobs.Set(j.name, "noanswer") end
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
    return #inviteTimes < MAX_PER_MINUTE
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
local DEFAULT_KEYWORDS = "inv, invite"
-- Keywords are for short, plain "inv" requests. Anything that reads like an ad or a
-- summon/port line (seller words, port/summon words, long text) goes to the normal matcher.
local function KeywordHit(text, whisper)
    if not Opt("kwon") or type(text) ~= "string" or #text > 30 then return nil end
    local norm = Norm(text)
    local count = 0
    for _ in norm:gmatch("%S+") do count = count + 1 end
    if count > (whisper and 3 or 2) then return nil end
    if HasAny(norm, SELLER) or HasAny(norm, SOFTSELLER) or HasAny(norm, SUMMON_WORDS) or HasAny(norm, PORT_WORDS) then return nil end
    local list = ServiceInviterDB.kwwords
    if type(list) ~= "string" or list:gsub("[%s,]", "") == "" then list = DEFAULT_KEYWORDS end
    local words = {}
    for w in (text:lower():gsub("[^%w%s]", " ")):gmatch("%S+") do words[w] = true end
    for k in list:lower():gmatch("[^,]+") do
        k = k:gsub("^%s+", ""):gsub("%s+$", "")
        if k ~= "" and words[k] then return k end
    end
end

local function Handle(text, sender, guid)
    if paused then return end
    if not (Opt("enabled") or Opt("kwon")) or not sender or sender == "" then D("skip: addon off or no sender") return end
    if Opt("skipafk") and UnitIsAFK and UnitIsAFK("player") then D("skip: you are AFK (see 'Skip while I'm AFK')") return end
    local short = Ambiguate and Ambiguate(sender, "none") or sender
    if short == UnitName("player") then return end
    if UnitInParty(short) or UnitInRaid(short) then D(short .. ": already in your group") return end
    if IsBlocked(short, guid) then D(short .. ": blocked/ignored") return end

    local now = GetTime()
    local cooldown = ServiceInviterDB.cooldown or 180
    if lastInvite[short] and now - lastInvite[short] < cooldown then D(short .. ": invited recently (cooldown)") return end

    local norm = Norm(text)
    local kw = KeywordHit(text, curChannel == "whisper")
    local ded = InExtraChannel(curChannel)
    local ok, why
    if kw then ok, why = true, "keyword '" .. kw .. "'"
    elseif Opt("enabled") then ok, why = Evaluate(norm, ded)
    else ok, why = false, "invites are off (only keywords are on)" end
    diag.eval = { who = short, ok = ok, why = why, t = GetTime() }

    if Opt("fragments") then
        local frags = fragments[short] or {}
        local fresh = {}
        for _, f in ipairs(frags) do
            if now - f.t < FRAGMENT_WINDOW then fresh[#fresh + 1] = f end
        end
        fresh[#fresh + 1] = { t = now, n = norm }
        while #fresh > MAX_FRAGMENTS do table.remove(fresh, 1) end
        fragments[short] = fresh

        if not ok and #fresh > 1 then
            local parts = {}
            for _, f in ipairs(fresh) do parts[#parts + 1] = f.n end
            ok, why = Evaluate(" " .. table.concat(parts, " ") .. " ", ded)
            if ok then why = "fragments: " .. why end
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
    local _, direct = CanInvite()

    lastInvite[short] = now
    fragments[short] = nil
    inviteTimes[#inviteTimes + 1] = now
    DoInvite(short)
    pending[short] = now
    Jobs.New(short, text, why, curChannel)
    if Opt("announce") then
        local what = " because [" .. curChannel .. "] \"" .. text .. "\" = " .. why
        P(direct and ("invited " .. short .. what) or ("suggested invite for " .. short .. " (you are not the leader)" .. what))
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

local function WelcomeText(name)
    local msg = ServiceInviterDB.welcomemsg
    if not msg or msg == "" then msg = DEFAULT_WELCOME end
    msg = msg:gsub("{name}", name)
    return (msg:gsub("{price}", PriceShort()))
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
    local d = text:match(DECLINE_PATTERN)
    if d then Jobs.Declined(nm(d)) return end
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
    -- Someone joined who nobody here invited (a friend invited them): give them a row too.
    if not Jobs.Get(short) and short ~= (UnitName and UnitName("player")) then
        Jobs.New(short, "(joined your group)", "invited by someone else", "-")
    end
    Jobs.Joined(short)
    if not Opt("welcome") then return end
    local t = pending[short]
    if not t then return end
    pending[short] = nil
    if GetTime() - t > 180 then return end   -- stale invite, ignore
    local channel = (IsInRaid and IsInRaid()) and "RAID" or "PARTY"
    D(short .. " joined, sending welcome to " .. channel)
    SendChatMessage(WelcomeText(short), channel)
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
f:RegisterEvent("CHAT_MSG_BN_WHISPER_INFORM")
f:RegisterEvent("CHAT_MSG_WHISPER_INFORM")
f:RegisterEvent("TRADE_SHOW")
f:RegisterEvent("TRADE_ACCEPT_UPDATE")
f:RegisterEvent("TRADE_CLOSED")
f:RegisterEvent("UNIT_SPELLCAST_START")
f:RegisterEvent("UNIT_SPELLCAST_CHANNEL_START")
f:RegisterEvent("UNIT_SPELLCAST_SUCCEEDED")
f:SetScript("OnEvent", function(_, event, text, sender, arg3, channelName, _, _, _, _, channelBaseName, _, _, guid)
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
            local npc = UnitName and UnitName("NPC")
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
            if silver >= Price() then
                Jobs.Get(who).amount = silver
                Jobs.Set(who, "paid")
                P(who .. " paid " .. Money(silver) .. ". Marked Paid.")
            elseif silver > 0 then
                P(who .. " traded " .. Money(silver) .. ", less than your " .. Money(Price()) .. " price. Not marked Paid.")
            end
        end
        return
    end
    if event == "CHAT_MSG_BN_WHISPER_INFORM" or event == "CHAT_MSG_WHISPER_INFORM" then
        diag.echo = { t = GetTime(), kind = event == "CHAT_MSG_BN_WHISPER_INFORM" and "Battle.net" or "normal" }
        return
    end
    if event == "UI_ERROR_MESSAGE" then
        diag.uierr = { t = GetTime(), msg = tostring(sender or text) }
        if debugOn then D("game error: " .. tostring(text) .. (sender and (" / " .. tostring(sender)) or "")) end
        return
    end
    if event == "PLAYER_REGEN_ENABLED" then
        if jobsDirty then RefreshJobs() end
        return
    end
    if event == "PLAYER_LOGIN" then
        MigrateLegacy()
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
        if not KeywordHit(text, true) and not Opt("enabled") then return end
    end
    diag.heard = { ch = curChannel, who = sender, text = text, t = GetTime(), event = event }
    RememberSaid(sender, text, curChannel)
    Handle(text, sender, guid)
end)

-- (The old settings window is gone: everything is in the Setup window, /si setup.)
local function ToggleUI() if ToggleSetup then ToggleSetup() end end

----------------------------------------------------------------------
-- Customer list window (/si jobs)
----------------------------------------------------------------------
local jobsWin
local ROWS = 6
local ARRIVE_FALLBACK = 40   -- seconds after Summon before we assume they have arrived
local CLEAN_AFTER = 30       -- finished rows disappear after this many seconds

-- Extras you can offer. Tick the ones you can do right now (on by happenstance).
local OFFERS = {
    { key = "healthstone", label = "Healthstone" },
    { key = "lockpick",    label = "Lockpicking" },
    { key = "food",        label = "Mage food & water" },
    { key = "paladin",     label = "Paladin blessing" },
    { key = "stam",        label = "Stamina buff" },
    { key = "motw",        label = "Mark of the Wild" },
    { key = "int",         label = "Intellect buff" },
    { key = "soulstone",   label = "Soulstone" },
    { key = "portal",      label = "Mage portal" },
}
local DEFAULT_OFFERMSG = "Welcome {name}! Also on offer today: {offers}. Just ask!"

local function OffersOn()
    local on = {}
    local o = ServiceInviterDB.offers or {}
    for _, x in ipairs(OFFERS) do if o[x.key] then on[#on + 1] = x.label end end
    local other = ServiceInviterDB.offerother
    if type(other) == "string" and other:gsub("%s+", "") ~= "" then on[#on + 1] = other end
    return on
end

-- The one thing to do next for a customer:
-- wait (not in group yet) | summon | arriving | offer | finish | none
local function NextStep(job)
    if not job then return "none" end
    if job.status == "invited" then return "wait" end
    if job.status == "joined" then return "summon" end
    if job.status == "summoned" then return "arriving" end
    if job.status == "arrived" then
        if #OffersOn() > 0 and not job.offered then return "offer" end
        return "finish"
    end
    return "none"
end

local function OfferText(name)
    local msg = ServiceInviterDB.offermsg or DEFAULT_OFFERMSG
    msg = msg:gsub("{name}", name)
    msg = msg:gsub("{offers}", table.concat(OffersOn(), ", "))
    return msg
end

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

local ACTIVE = { invited = true, joined = true, summoned = true, arrived = true, busy = true }

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
local function NextJob()
    for _, j in ipairs(jobs) do
        local st = NextStep(j)
        if st == "summon" or st == "offer" or st == "finish" then return j, st end
    end
    return nil, "none"
end

----------------------------------------------------------------------
-- Helper mode: the lock starts Ritual of Summoning -> alert + raid line
----------------------------------------------------------------------
local alertWin
local lastCastAt = 0
local RITUAL_ID = 698

ShowAlert = function(title, sub)
    if not alertWin then
        local template = (BackdropTemplateMixin and "BackdropTemplate") or nil
        local a = CreateFrame("Frame", "ServiceInviterAlert", UIParent, template)
        a:SetSize(560, 96)
        a:SetPoint("TOP", 0, -150)
        a:SetFrameStrata("FULLSCREEN_DIALOG")
        local bg = a:CreateTexture(nil, "BACKGROUND")
        bg:SetAllPoints()
        bg:SetColorTexture(0.55, 0.05, 0.05, 0.92)
        a.title = a:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        pcall(function() local f, _, fl = a.title:GetFont() if f then a.title:SetFont(f, 34, "OUTLINE") end end)
        a.title:SetPoint("TOP", 0, -14)
        a.sub = a:CreateFontString(nil, "OVERLAY", "GameFontHighlightLarge")
        a.sub:SetPoint("TOP", a.title, "BOTTOM", 0, -8)
        a.t = 0
        a:SetScript("OnUpdate", function(self, el)
            self.t = self.t + (el or 0)
            if self.t > 14 then self:Hide() return end
            self:SetAlpha(0.7 + 0.3 * math.abs(math.sin(self.t * 5)))
        end)
        a:EnableMouse(true)
        a:SetScript("OnMouseDown", function(self) self:Hide() end)
        a:Hide()
        alertWin = a
    end
    alertWin.title:SetText(title)
    alertWin.sub:SetText(sub or "")
    alertWin.t = 0
    alertWin:Show()
    if PlaySound then
        pcall(PlaySound, (SOUNDKIT and SOUNDKIT.RAID_WARNING) or 8959)
    end
end

local function WhisperText(who, nxt)
    local m = ServiceInviterDB.whispermsg
    if not m or m == "" then m = DEFAULT_WHISPERMSG end
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

local function AlertMsg(name)
    local m = ServiceInviterDB.alertmsg
    if not m or m == "" then m = DEFAULT_ALERTMSG end
    m = m:gsub("{name}", name)
    return (m:gsub("{price}", PriceLong()))
end

local function IsSecret(v)
    if issecretvalue then
        local ok, r = pcall(issecretvalue, v)
        if ok and r then return true end
    end
    return false
end
local function SpellNameOf(spellID)
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
    local tname = UnitName and UnitName(unit .. "target")
    if tname and Ambiguate then tname = Ambiguate(tname, "none") end
    local job = tname and Jobs.Get(tname)
    if not (job and job.status == "joined") and not event:find("SUCCE", 1, true) then
        -- target is not someone waiting (stale/other target): use whoever has waited longest
        local waiting
        for _, j in ipairs(jobs) do if j.status == "joined" then waiting = j break end end
        job = waiting or job
    end
    local who = job and job.name or tname or "someone"
    local caster = (UnitName and UnitName(unit)) or unit
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
        if to and ((UnitName and UnitName("player")) ~= to) then
            local nxt
            for _, j in ipairs(jobs) do if j.status == "joined" and j ~= job then nxt = j.name break end end
            local ok, err = pcall(SendWhisperTo, to, WhisperText(who, nxt))
            trace.whisper = ok and ("sent to " .. tostring(err)) or ("failed: " .. tostring(err))
        else
            trace.whisper = "off"
        end
        if ServiceInviterDB.raidalert ~= false then
            local ch = (IsInRaid and IsInRaid()) and "RAID" or ((IsInGroup and IsInGroup()) and "PARTY" or nil)
            if ch then
                local ok, err = pcall(function() SendChatMessage(AlertMsg(who), ch) end)
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
        trace.banner = select(2, pcall(ShowAlert, "PORTAL IS UP - CLICK IT!", "Summoning " .. who .. "  (" .. caster .. ")")) and "error" or "shown"
    elseif first then
        local ok, err = pcall(ShowAlert, "CLICK THE PORTAL!", "Summoning " .. who .. "  (" .. caster .. ")")
        trace.banner = ok and "shown" or ("error: " .. tostring(err))
    end

    -- 3) mark the customer as being summoned
    -- only the first event of a cast marks anyone: raid1 and party1 both fire for one cast
    if first and job and job.status == "joined" then
        local ok, err = pcall(Jobs.Set, job.name, "summoned")
        trace.marked = ok and "yes" or ("error: " .. tostring(err))
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
                -- tell them what else is on offer; nothing ticked = no message
                if #OffersOn() > 0 and not j.offered then
                    j.offered = true
                    local ch = (IsInRaid and IsInRaid()) and "RAID" or ((IsInGroup and IsInGroup()) and "PARTY" or nil)
                    if ch then pcall(SendChatMessage, OfferText(j.name), ch) end
                end
            end
        elseif j.status == "arrived" and Collects() and AutoTradeOn() and not j.tradeTried and j.tarrive and now - j.tarrive < 60 then
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
    if tacc >= 1 then tacc = 0 pcall(CheckArrivals) end
end)

local function ApplyRow(row, job)
    row.job = job
    row.summon:Hide() row.offer:Hide() row.trade:Hide() row.paid:Hide() row.remove:Hide() row.reinvite:Hide()
    if not job then
        row.name:SetText("") row.status:SetText("")
        return
    end
    local st = JOB_STATUS[job.status] or { job.status, "" }
    row.name:SetText(job.name)
    row.status:SetText(st[2] .. st[1] .. "|r")
    local n = UnitFor(job.name) or CleanName(job.name)
    row.summon:SetAttribute("macrotext", "/target " .. n .. "\n/cast Ritual of Summoning")
    row.trade:SetAttribute("macrotext", "/target " .. n .. "\n/run InitiateTrade(\"target\")")
    local step = NextStep(job)
    local lock = Role() == "lock"
    if job.status == "busy" or job.status == "noanswer" or job.status == "declined" then
        row.reinvite:Show()
    elseif step == "summon" then
        if lock then row.summon:Show() end
    elseif step == "offer" then
        if lock then row.offer:Show() elseif Collects() then row.trade:Show() end
        if Collects() then row.paid:Show() end
    elseif step == "finish" then
        if Collects() then row.trade:Show() row.paid:Show() end
    end
    row.remove:Show()
end

local function ApplyNext()
    local w = jobsWin
    if Role() == "helper" then
        w.nextBtn:Hide()
        w.nextText:Show()
        local nxt, waiting = nil, 0
        for _, j in ipairs(jobs) do if j.status == "joined" then nxt = nxt or j waiting = waiting + 1 end end
        w.nextText:SetText(nxt and ("Next up: |cffffd100" .. nxt.name .. "|r" .. (waiting > 1 and ("  (+" .. (waiting - 1) .. " waiting)") or "")) or "Nobody waiting")
        return
    end
    w.nextBtn:Show()
    w.nextText:Hide()
    local job, step = NextJob()
    w.nextBtn.step, w.nextBtn.job = step, job
    if not job then
        w.nextBtn:SetText("Nothing to do")
        w.nextBtn:SetAttribute("macrotext", "")
        return
    end
    local n = UnitFor(job.name) or CleanName(job.name)
    if step == "summon" then
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

    local lock = Role() == "lock"
    local list = VisibleJobs()
    for i = 1, ROWS do ApplyRow(jobsWin.rows[i], list[i]) end
    ApplyNext()
    local wait, going = 0, 0
    for _, j in ipairs(jobs) do
        if j.status == "joined" then wait = wait + 1 elseif j.status == "summoned" then going = going + 1 end
    end
    jobsWin.footer:SetText("Session: " .. SessionText() .. "\nWaiting: " .. wait .. "    Being summoned: " .. going)
end

local function BuildJobsUI()
    local template = (BackdropTemplateMixin and "BackdropTemplate") or nil
    local w = CreateFrame("Frame", "ServiceInviterJobs", UIParent, template)
    w:SetSize(480, 210 + ROWS * 38)
    w:SetPoint("CENTER", 0, 120)
    w:SetFrameStrata("DIALOG")
    w:SetClampedToScreen(true)
    w:SetMovable(true)
    w:EnableMouse(true)
    w:RegisterForDrag("LeftButton")
    w:SetScript("OnDragStart", function(self) self:StartMoving() end)
    w:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    if w.SetBackdrop then
        w:SetBackdrop({
            bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
            edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
            tile = true, tileSize = 32, edgeSize = 32,
            insets = { left = 8, right = 8, top = 8, bottom = 8 },
        })
    end
    local bg = w:CreateTexture(nil, "BACKGROUND", nil, -8)
    bg:SetPoint("TOPLEFT", 6, -6)
    bg:SetPoint("BOTTOMRIGHT", -6, 6)
    bg:SetColorTexture(0, 0, 0, 0.92)
    w:Hide()

    local title = w:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    title:SetPoint("TOP", 0, -18)
    title:SetText("Customers")
    local close = CreateFrame("Button", nil, w, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", -4, -4)
    local setupBtn = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
    setupBtn:SetPoint("TOPLEFT", 16, -14)
    setupBtn:SetSize(80, 24) setupBtn:SetText("Setup")
    setupBtn:SetScript("OnClick", function() ToggleSetup() end)

    -- The big button: always does the next thing for whoever has waited longest.
    -- Secure buttons must listen for press AND release: newer clients fire them on press.
    local nb = CreateFrame("Button", "ServiceInviterNext", w, "SecureActionButtonTemplate,UIPanelButtonTemplate")
    nb:SetPoint("TOP", 0, -50)
    nb:SetSize(300, 40)
    nb:RegisterForClicks("AnyUp", "AnyDown")
    nb:SetAttribute("type", "macro")
    nb:SetText("Nothing to do")
    nb:HookScript("PostClick", function(self)
        local job, step = self.job, self.step
        if not job then return end
        if step == "summon" then Jobs.Set(job.name, "summoned")
        elseif step == "offer" then job.offered = true
        elseif step == "finish" then pendingTrade = job.name end
        RefreshJobs()
    end)
    w.nextBtn = nb
    w.nextText = w:CreateFontString(nil, "OVERLAY", "GameFontHighlightLarge")
    w.nextText:SetPoint("TOP", 0, -58)
    w.nextText:SetText("Nobody waiting")

    w.rows = {}
    for i = 1, ROWS do
        local y = -104 - (i - 1) * 38
        local row = {}
        row.name = w:CreateFontString(nil, "OVERLAY", "GameFontHighlightLarge")
        row.name:SetPoint("TOPLEFT", 24, y - 6)
        row.name:SetWidth(120) row.name:SetJustifyH("LEFT")
        row.status = w:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        row.status:SetPoint("TOPLEFT", 150, y - 7)
        row.status:SetWidth(96) row.status:SetJustifyH("LEFT")

        row.summon = CreateFrame("Button", nil, w, "SecureActionButtonTemplate,UIPanelButtonTemplate")
        row.summon:SetPoint("TOPLEFT", 252, y)
        row.summon:SetSize(100, 28) row.summon:SetText("Summon")
        row.summon:RegisterForClicks("AnyUp", "AnyDown")
        row.summon:SetAttribute("type", "macro")
        row.summon:HookScript("PostClick", function() if row.job then Jobs.Set(row.job.name, "summoned") RefreshJobs() end end)

        row.offer = CreateFrame("Button", nil, w, "SecureActionButtonTemplate,UIPanelButtonTemplate")
        row.offer:SetPoint("TOPLEFT", 252, y)
        row.offer:SetSize(100, 28) row.offer:SetText("Offer")
        row.offer:RegisterForClicks("AnyUp", "AnyDown")
        row.offer:SetAttribute("type", "macro")
        row.offer:HookScript("PreClick", function()
            if row.job then row.offer:SetAttribute("macrotext", ((IsInRaid and IsInRaid()) and "/raid " or "/p ") .. OfferText(row.job.name)) end
        end)
        row.offer:HookScript("PostClick", function() if row.job then row.job.offered = true RefreshJobs() end end)

        row.trade = CreateFrame("Button", nil, w, "SecureActionButtonTemplate,UIPanelButtonTemplate")
        row.trade:SetPoint("TOPLEFT", 252, y)
        row.trade:SetSize(100, 28) row.trade:SetText("Trade")
        row.trade:RegisterForClicks("AnyUp", "AnyDown")
        row.trade:SetAttribute("type", "macro")
        row.trade:HookScript("PostClick", function()
            if row.job then pendingTrade = row.job.name D("Trade clicked for " .. row.job.name .. " (macro: " .. tostring(row.trade:GetAttribute("macrotext")) .. ")") end
        end)

        row.paid = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
        row.paid:SetPoint("TOPLEFT", 358, y)
        row.paid:SetSize(70, 28) row.paid:SetText("Paid")
        row.paid:SetScript("OnClick", function() if row.job then Jobs.Set(row.job.name, "paid") end end)

        row.reinvite = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
        row.reinvite:SetPoint("TOPLEFT", 252, y)
        row.reinvite:SetSize(100, 28) row.reinvite:SetText("Re-invite")
        row.reinvite:SetScript("OnClick", function()
            if not row.job then return end
            local name = row.job.name
            local j = Jobs.New(name, row.job.text, "re-invited", row.job.channel or "-")
            lastInvite[name] = GetTime() pending[name] = GetTime()
            DoInvite(name)
            RefreshJobs()
        end)

        row.remove = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
        row.remove:SetPoint("TOPLEFT", 436, y)
        row.remove:SetSize(28, 28) row.remove:SetText("x")
        row.remove:SetScript("OnClick", function()
            if not row.job then return end
            local name = row.job.name
            -- x = done with this customer: take them out of the group too, if allowed
            local u = UnitFor(name)
            if u and (UnitInParty and UnitInParty(u) or UnitInRaid and UnitInRaid(u)) then
                local lead = UnitIsGroupLeader and UnitIsGroupLeader("player")
                local assist = UnitIsGroupAssistant and UnitIsGroupAssistant("player")
                if lead or assist then
                    pcall(UninviteUnit, name)
                    P("removed " .. name .. " from the group")
                else
                    P("removed " .. name .. " from the list (you are not leader/assist, so they stay in the group)")
                end
            end
            Jobs.Remove(name)
        end)
        w.rows[i] = row
    end

    w.footer = w:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    w.footer:SetPoint("BOTTOMLEFT", 24, 18)
    w.footer:SetJustifyH("LEFT") w.footer:SetWidth(330)
    local newBtn = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
    newBtn:SetPoint("BOTTOMRIGHT", -20, 22) newBtn:SetSize(110, 26) newBtn:SetText("New session")
    newBtn:SetScript("OnClick", function() NewSession() RefreshJobs() P("new session started") end)

    local acc = 0
    w:SetScript("OnUpdate", function(_, elapsed)
        acc = acc + (elapsed or 0)
        if acc >= 1 then acc = 0 RefreshJobs() end
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

local function Fill(msg, name, nxt, price)
    msg = msg:gsub("{name}", function() return name end)
    msg = msg:gsub("{price}", function() return price end)
    msg = msg:gsub("{next}", function() return nxt or "nobody" end)
    return msg
end

local function BuildSetupUI()
    local template = (BackdropTemplateMixin and "BackdropTemplate") or nil
    local w = CreateFrame("Frame", "ServiceInviterSetup", UIParent, template)
    w:SetSize(1010, 910)
    w:SetPoint("CENTER", 0, 0)
    w:SetFrameStrata("DIALOG")
    w:SetClampedToScreen(true)
    w:SetMovable(true) w:EnableMouse(true)
    w:RegisterForDrag("LeftButton")
    w:SetScript("OnDragStart", function(self) self:StartMoving() end)
    w:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    if w.SetBackdrop then
        w:SetBackdrop({
            bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
            edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
            tile = true, tileSize = 32, edgeSize = 32,
            insets = { left = 8, right = 8, top = 8, bottom = 8 },
        })
    end
    local bg = w:CreateTexture(nil, "BACKGROUND", nil, -8)
    bg:SetPoint("TOPLEFT", 6, -6) bg:SetPoint("BOTTOMRIGHT", -6, 6)
    bg:SetColorTexture(0, 0, 0, 0.92)
    w:Hide()

    local title = w:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    title:SetPoint("TOP", 0, -16) title:SetText("Service Inviter setup")
    local close = CreateFrame("Button", nil, w, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", -4, -4)
    local hint = w:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    hint:SetPoint("TOPLEFT", 30, -44) hint:SetWidth(950) hint:SetJustifyH("LEFT")
    hint:SetText("Everything in one place. Left: what happens, in order, and what is said. Right: who gets invited. In messages {name} = the customer, {price} = your price. Press Save when done.")

    -- the flow line down the left side, and a divider between the columns
    local line = w:CreateTexture(nil, "ARTWORK")
    line:SetColorTexture(0.9, 0.7, 0.1, 0.6)
    line:SetPoint("TOPLEFT", 18, -86) line:SetSize(2, 700)
    local divider = w:CreateTexture(nil, "ARTWORK")
    divider:SetColorTexture(0.5, 0.5, 0.5, 0.5)
    divider:SetPoint("TOPLEFT", 505, -86) divider:SetSize(1, 720)

    local boxes, checks, previews = {}, {}, {}
    local optKeys = {}     -- checkboxes that simply map to an option

    local function Header(x, y, num, text)
        local fs = w:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        fs:SetPoint("TOPLEFT", x, y)
        fs:SetText(num and ("|cffffd100" .. num .. "|r  " .. text) or ("|cffffd100" .. text .. "|r"))
    end
    local function Label(x, y, text)
        local fs = w:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        fs:SetPoint("TOPLEFT", x, y) fs:SetText(text)
    end
    local function Box(key, y, width, maxLetters, x)
        local eb = CreateFrame("EditBox", nil, w, "InputBoxTemplate")
        eb:SetPoint("TOPLEFT", x or 46, y)
        eb:SetSize(width or 440, 22)
        eb:SetAutoFocus(false)
        eb:SetMaxLetters(maxLetters or 255)
        eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
        eb:SetScript("OnEnterPressed", function(self) self:ClearFocus() end)
        boxes[key] = eb
        return eb
    end
    local function Preview(key, y)
        local fs = w:CreateFontString(nil, "OVERLAY", "GameFontDisable")
        fs:SetPoint("TOPLEFT", 50, y) fs:SetWidth(440) fs:SetJustifyH("LEFT")
        previews[key] = fs
    end
    -- a checkbox; text is optional (the places grid has none)
    local function Check(key, x, y, text, isOpt)
        local cb = CreateFrame("CheckButton", nil, w, "UICheckButtonTemplate")
        cb:SetSize(26, 26) cb:SetPoint("TOPLEFT", x, y)
        if text then
            local fs = w:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
            fs:SetPoint("LEFT", cb, "RIGHT", 2, 0) fs:SetText(text)
        end
        checks[key] = cb
        if isOpt then optKeys[#optKeys + 1] = key end
    end

    -- LEFT: the flow ------------------------------------------------
    Header(30, -78, "1", "Customer joins your group")
    Check("welcome", 40, -100, "Say this in raid / party when an invited person joins")
    Box("welcomemsg", -128)
    Preview("welcomemsg", -154)

    Header(30, -190, "2", "The lock starts summoning (banner: click the portal)")
    Check("raidalert", 40, -212, "Also say this in raid")
    Box("alertmsg", -242)
    Preview("alertmsg", -268)

    Header(30, -298, "3", "Whisper who is being summoned")
    Label(40, -322, "Whisper to (blank = no whisper):")
    Box("whisperto", -342, 200, 40)
    Label(40, -370, "Whisper text ({name} = who, {next} = who waits longest):")
    Box("whispermsg", -390)
    Preview("whispermsg", -416)

    Header(30, -446, "4", "Customer arrives")
    Check("collect", 40, -470, "I collect the payment")
    Check("autotrade", 220, -470, "Open trade by itself in range")
    Label(40, -504, "Price per customer (gold and/or silver):")
    Box("pricegold", -524, 60, 5)
    Label(112, -521, "gold")
    Box("pricesilver", -524, 50, 2, 170)
    Label(228, -521, "silver")

    Header(30, -558, "5", "Extras you can offer on arrival")
    Label(40, -582, "Tick what you offer. Sent on arrival; none ticked = no message.")
    for i, x in ipairs(OFFERS) do
        local col, row = (i - 1) % 3, math.floor((i - 1) / 3)
        Check("offer_" .. x.key, 40 + col * 150, -604 - row * 24, x.label)
    end
    Label(40, -682, "Other (your own, e.g. Lockbox opening):")
    Box("offerother", -702, 440, 60)
    Label(40, -734, "Offer message ({offers} = everything above):")
    Box("offermsg", -754)

    -- RIGHT: role, who gets invited, advanced ----------------------
    local X = 525
    Header(X, -78, nil, "Your role")
    Check("rolehelper", X, -102, "Helper: I click the portal (banner, raid line, whisper)")
    Check("rolelock", X, -128, "Warlock: I summon (Summon and Offer buttons)")
    checks.rolehelper:SetScript("OnClick", function() checks.rolehelper:SetChecked(true) checks.rolelock:SetChecked(false) end)
    checks.rolelock:SetScript("OnClick", function() checks.rolelock:SetChecked(true) checks.rolehelper:SetChecked(false) end)

    Header(X, -166, nil, "Who gets invited")
    Check("enabled", X, -190, "Invite people who ask for a summon/port", true)

    Label(X, -222, "Listen in:")
    Label(X + 120, -222, "+ other channels:")
    Box("chanextra", -224, 190, 100, X + 270)
    Check("trade", X + 10, -244, "Trade", true)
    Check("general", X + 100, -244, "General", true)
    Check("say", X + 210, -244, "Say", true)
    Check("yell", X + 290, -244, "Yell", true)

    Label(X, -280, "Which requests do you want?")
    local function Col(text, x)
        local fs = w:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        fs:SetPoint("TOPLEFT", x, -302) fs:SetText(text)
    end
    local places = {}
    for _, d in ipairs(DESTS) do places[#places + 1] = { d.label, d.key } end
    places[#places + 1] = { "Any other", "any" }
    local perBlock = math.ceil(#places / 2)
    for blk = 0, 1 do
        local bx = X + blk * 235
        Col("Summon", bx + 98) Col("Port", bx + 150)
        for r = 1, perBlock do
            local pl = places[blk * perBlock + r]
            if pl then
                local y = -318 - (r - 1) * 24
                local fs = w:CreateFontString(nil, "OVERLAY", "GameFontNormal")
                fs:SetPoint("TOPLEFT", bx + 6, y - 5) fs:SetText(pl[1])
                Check("sum_" .. pl[2], bx + 104, y, nil, true)
                Check("port_" .. pl[2], bx + 152, y, nil, true)
            end
        end
    end

    Header(X, -448, nil, "Matching")
    Check("strictbuy", X, -472, "Only 'WTB' / 'buying' (skip LF, need, looking)", true)
    Check("fragments", X, -498, "Combine a person's split messages", true)
    Check("nodest", X, -524, "No place named (\"WTB summ\") = assume Thunder Bluff", true)

    Header(X, -562, nil, "Other")
    Check("skipafk", X, -586, "Skip while I'm AFK", true)
    Check("announce", X, -612, "Show a line in chat when I invite", true)
    Check("autoshow", X, -638, "Open the customer list when I invite someone", true)

    Check("kwon", X, -664, "Auto-invite anyone who says:", true)
    Box("kwwords", -666, 170, 60, X + 262)

    Header(X, -706, nil, "Troubleshooting")
    Check("dryrun", X, -730, "Dry run (only say who it would invite)")
    Check("near", X, -756, "Near-miss lines")
    Check("debug", X + 215, -756, "Debug")

    local note = w:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    note:SetPoint("TOPLEFT", X, -792) note:SetWidth(450) note:SetJustifyH("LEFT")
    note:SetText("Sellers/ads (WTS, selling, service, tips...) are always skipped. pst/inv is fine if they say WTB.")

    Header(X, -826, nil, "This session")
    local sessText = w:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    sessText:SetPoint("TOPLEFT", X, -852) sessText:SetWidth(300) sessText:SetJustifyH("LEFT")
    local sessBtn = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
    sessBtn:SetPoint("TOPLEFT", X + 320, -846) sessBtn:SetSize(120, 26) sessBtn:SetText("New session")
    sessBtn:SetScript("OnClick", function() NewSession() sessText:SetText(SessionText()) RefreshJobs() end)
    w.sessText = sessText

    local DEFAULTS_BY_KEY = {
        welcomemsg = DEFAULT_WELCOME, alertmsg = DEFAULT_ALERTMSG,
        whispermsg = DEFAULT_WHISPERMSG, offermsg = DEFAULT_OFFERMSG,
    }

    local function UpdatePreviews()
        local n = (tonumber(boxes.pricegold:GetText()) or 0) * 100 + (tonumber(boxes.pricesilver:GetText()) or 0)
        local pr = PriceLong(n)
        previews.welcomemsg:SetText("Preview: " .. Fill(boxes.welcomemsg:GetText(), "Bob", nil, PriceShort(n)))
        previews.alertmsg:SetText("Preview: " .. Fill(boxes.alertmsg:GetText(), "Bob", nil, pr))
        previews.whispermsg:SetText("Preview: " .. Fill(boxes.whispermsg:GetText(), "Bob", "Cat", pr))
    end
    for _, k in ipairs({ "welcomemsg", "alertmsg", "whispermsg", "pricegold", "pricesilver" }) do
        boxes[k]:SetScript("OnTextChanged", UpdatePreviews)
    end

    function w.Load()
        local db = ServiceInviterDB
        for key, def in pairs(DEFAULTS_BY_KEY) do boxes[key]:SetText(db[key] or def) boxes[key]:SetCursorPosition(0) end
        boxes.whisperto:SetText(WhisperTo() or "")
        local pg, ps = PriceParts(Price())
        boxes.pricegold:SetText(tostring(pg))
        boxes.pricesilver:SetText(tostring(ps))
        boxes.offerother:SetText(db.offerother or "")
        boxes.kwwords:SetText(db.kwwords or DEFAULT_KEYWORDS) boxes.kwwords:SetCursorPosition(0)
        boxes.chanextra:SetText(type(db.chanextra) == "string" and db.chanextra or DEFAULT_CHANNELS) boxes.chanextra:SetCursorPosition(0)
        checks.raidalert:SetChecked(db.raidalert ~= false)
        checks.autotrade:SetChecked(db.autotrade ~= false)
        checks.collect:SetChecked(Collects())
        checks.welcome:SetChecked(Opt("welcome") and true or false)
        for _, k in ipairs(optKeys) do checks[k]:SetChecked(Opt(k) and true or false) end
        checks.rolehelper:SetChecked(Role() == "helper")
        checks.rolelock:SetChecked(Role() == "lock")
        local offers = db.offers or {}
        for _, x in ipairs(OFFERS) do checks["offer_" .. x.key]:SetChecked(offers[x.key] and true or false) end
        checks.dryrun:SetChecked(db.dryrun and true or false)
        checks.near:SetChecked(db.near ~= false)
        checks.debug:SetChecked(db.debug and true or false)
        UpdatePreviews()
        sessText:SetText(SessionText())
    end

    function w.Save()
        local db = ServiceInviterDB
        for key, def in pairs(DEFAULTS_BY_KEY) do
            local v = boxes[key]:GetText()
            if v == "" or v == def then db[key] = nil else db[key] = v end
        end
        local who = (boxes.whisperto:GetText():gsub("%s+", ""))
        db.whisperto = (who == "") and false or who
        local pg, ps = tonumber(boxes.pricegold:GetText()), tonumber(boxes.pricesilver:GetText())
        if pg or ps then db.price = (pg or 0) * 100 + (ps or 0) end
        db.raidalert = checks.raidalert:GetChecked() and true or false
        db.autotrade = checks.autotrade:GetChecked() and true or false
        db.collect = checks.collect:GetChecked() and true or false
        SetOpt("welcome", checks.welcome:GetChecked() and true or false)
        for _, k in ipairs(optKeys) do SetOpt(k, checks[k]:GetChecked() and true or false) end
        do local kws = boxes.kwwords:GetText() db.kwwords = (kws:gsub("[%s,]", "") == "" or kws == DEFAULT_KEYWORDS) and nil or kws end
        db.chanextra = boxes.chanextra:GetText()   -- empty = none (kept as ""), so the default only applies before first save
        local oth = boxes.offerother:GetText()
        db.offerother = (oth:gsub("%s+", "") == "") and nil or oth
        db.role = checks.rolelock:GetChecked() and "lock" or "helper"
        db.offers = db.offers or {}
        for _, x in ipairs(OFFERS) do db.offers[x.key] = checks["offer_" .. x.key]:GetChecked() and true or false end
        db.dryrun = checks.dryrun:GetChecked() and true or false
        db.near = checks.near:GetChecked() and true or false
        db.debug = checks.debug:GetChecked() and true or false
        debugOn = db.debug
        RefreshJobs()
    end

    local save = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
    save:SetPoint("BOTTOMLEFT", 30, 24) save:SetSize(110, 28) save:SetText("Save")
    save:SetScript("OnClick", function() w.Save() w.Load() P("setup saved") end)
    local test = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
    test:SetPoint("LEFT", save, "RIGHT", 10, 0) test:SetSize(130, 28) test:SetText("Test banner")
    test:SetScript("OnClick", function() ShowAlert("CLICK THE PORTAL!", "Summoning Testy  (test)") end)
    local reset = CreateFrame("Button", nil, w, "UIPanelButtonTemplate")
    reset:SetPoint("LEFT", test, "RIGHT", 10, 0) reset:SetSize(150, 28) reset:SetText("Reset messages")
    reset:SetScript("OnClick", function()
        local db = ServiceInviterDB
        db.welcomemsg, db.alertmsg, db.whispermsg, db.offermsg = nil, nil, nil, nil
        db.whisperto, db.raidalert, db.autotrade, db.price = nil, nil, nil, nil
        w.Load() P("messages back to defaults")
    end)

    -- shrink to fit small screens so nothing runs off
    local function Fit()
        local sw, sh = UIParent:GetWidth(), UIParent:GetHeight()
        local sc = 1
        if type(sw) == "number" and type(sh) == "number" and sw > 0 and sh > 0 then
            sc = math.min(1, sw / (1010 + 40), sh / (910 + 40))
        end
        w:SetScale(sc)
    end
    w.checks = checks
    w:SetScript("OnShow", function() Fit() w.Load() end)
    w:SetScript("OnHide", function() w.Save() end)
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
        if rest == "" then P("welcome message: " .. (ServiceInviterDB.welcomemsg or DEFAULT_WELCOME))
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
        local key = rest:upper():gsub("%s+", "")
        if key == "" then P("usage: /si bind <key>   e.g. /si bind F   or /si bind CTRL-F") 
        elseif InCombatLockdown and InCombatLockdown() then P("can't change keys in combat")
        else
            jobsWin = jobsWin or BuildJobsUI()
            if SetBindingClick and SetBindingClick(key, "ServiceInviterNext") then
                if SaveBindings and GetCurrentBindingSet then SaveBindings(GetCurrentBindingSet()) end
                P(key .. " now presses the big button (does the next thing for your next customer)")
            else
                P("couldn't bind " .. key .. " (try another key)")
            end
        end
    elseif cmd == "status" then
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
        ShowAlert("CLICK THE PORTAL!", "Summoning Testy  (test)")
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
        if rest == "" then P("raid alert: " .. (ServiceInviterDB.alertmsg or DEFAULT_ALERTMSG) .. "   ({name} and {price} are filled in)")
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
        ServiceInviterDB.collect = not Collects()
        P("payment: " .. (Collects() and "YOU collect (Trade and Paid buttons; trade opens by itself unless /si autotrade is off)" or "someone else collects (no trade window, no Trade/Paid buttons)"))
        RefreshJobs()
    elseif cmd == "autotrade" then
        ServiceInviterDB.autotrade = not AutoTradeOn()
        P("auto-open trade (and auto Paid) " .. (AutoTradeOn() and "ON: opens when a customer arrives in range; you click Accept" or "off"))
    elseif cmd == "offermsg" then
        if rest == "" then P("offer message: " .. (ServiceInviterDB.offermsg or DEFAULT_OFFERMSG) .. "   ({name} and {offers} are filled in)")
        else ServiceInviterDB.offermsg = rest P("offer message set") end
    elseif cmd == "clear" then Jobs.Clear() P("customer list cleared")
    elseif cmd == "price" then
        local n = ParsePrice(rest)
        if n and n >= 0 then ServiceInviterDB.price = n P("price " .. Money(n) .. " per customer") else P("usage: /si price 25   or   /si price 1g 25s   or   /si price 2g") end
    elseif cmd == "reset" then
        wipe(lastInvite) wipe(pending) wipe(fragments) inviteTimes = {}
        ServiceInviterDB = {}
        P("settings reset")
    else
        P("/si = customers | /si setup = every message and option | /si session = earnings | /si status = what it hears | /si simcast = test the alert | /si session new | /si collect = who takes the money | /si on | /si off | /si selftest")
    end
end

-- Exposed for offline testing only.
ServiceInviter_Test = { SetupChecks = function() setupWin = setupWin or BuildSetupUI() return setupWin.checks end, Norm = Norm, Evaluate = Evaluate, ToggleUI = ToggleUI, Opt = Opt, Jobs = Jobs, BuildSetup = function() setupWin = setupWin or BuildSetupUI() return setupWin end, WhisperText = WhisperText, Stats = Stats, NextStep = NextStep, OfferText = OfferText, NextJob = NextJob, OnCast = OnCast, CheckArrivals = CheckArrivals, Role = Role,
    Refresh = function() jobsWin = jobsWin or BuildJobsUI() RefreshJobs() end }
