-- Service Inviter: what the group sells, who in the group can do it, who gets paid, and
-- the words that go out (ads, welcomes, arrival offers). Pure logic: the caller passes in
-- the group as a list of members, so every rule here runs and is tested without the game.
--
-- A member is { name, class (e.g. "MAGE"), level, zone (or nil if unknown), me (true for
-- you), knows (for you only: a set of spell names you have, or nil if not read) }.
--
-- Facts used below were checked against Forever spell databases and guides on 12 Nov 2026;
-- see docs/DESIGN.md for the sources.

local C = {}
ServiceInviterCore = C

-- Short names used in chat.
C.SHORT = {
    ["Thunder Bluff"] = "TB", ["Orgrimmar"] = "Org", ["Undercity"] = "UC",
    ["Stormwind City"] = "SW", ["Ironforge"] = "IF", ["Darnassus"] = "Darn",
}
function C.Short(zone) return C.SHORT[zone] or zone end

-- Mage group portals in Forever: two capitals at 40, the third at 50 (Rune of Portals).
C.PORTALS = {
    Horde    = { { "Orgrimmar", 40 }, { "Undercity", 40 }, { "Thunder Bluff", 50 } },
    Alliance = { { "Stormwind City", 40 }, { "Ironforge", 40 }, { "Darnassus", 50 } },
}
C.PORTAL_SPELL = {
    ["Orgrimmar"] = "Portal: Orgrimmar", ["Undercity"] = "Portal: Undercity", ["Thunder Bluff"] = "Portal: Thunder Bluff",
    ["Stormwind City"] = "Portal: Stormwind", ["Ironforge"] = "Portal: Ironforge", ["Darnassus"] = "Portal: Darnassus",
}

-- Everything the group can sell. price: default in silver, nil = free. invite: whether a
-- buyer asking in chat gets invited (off = only offered on arrival). words: what buyers say
-- (travel services use the summon/port words in the matcher instead).
C.SERVICES = {
    { key = "summons",     class = "WARLOCK", level = 20, tab = "Warlock", kind = "summon", label = "summons",           on = true,  invite = true,  price = 25 },
    { key = "blessing",    class = "PALADIN", level = 1,  tab = "Paladin",   kind = "buff",   label = "blessings",         on = false, invite = false, spell = "Blessing of Might",
      words = "blessing, bless, kings, might, wisdom, salvation, salv, light, sanctuary, sanc" },
}
-- Paladin blessings by the word a buyer uses ("wisdom pls" = Blessing of Wisdom). Plain
-- "blessing" or "buff" gets the one set on the Buffs tab.
C.BLESSINGS = {
    { word = "wisdom", spell = "Blessing of Wisdom" }, { word = "might", spell = "Blessing of Might" },
    { word = "kings", spell = "Blessing of Kings" }, { word = "salvation", spell = "Blessing of Salvation" },
    { word = "salv", spell = "Blessing of Salvation" }, { word = "light", spell = "Blessing of Light" },
    { word = "sanctuary", spell = "Blessing of Sanctuary" }, { word = "sanc", spell = "Blessing of Sanctuary" },
}
-- What a buyer calls each blessing beyond its word (the owner, 14 Nov 2026: "can you make it so
-- that blessing are recognized by fragments and stuff - this guy asked for wis"): the usual
-- abbreviations, and any first 3+ letters of the word ("wis", "wisd", "kin", "mig", "sanc").
C.BLESSING_SHORT = { bok = "Blessing of Kings", bow = "Blessing of Wisdom", bom = "Blessing of Might",
    bos = "Blessing of Salvation", bol = "Blessing of Light", bosanc = "Blessing of Sanctuary" }
function C.BlessingFor(norm)
    local found, at = nil, 0
    local pos = 0
    for tok in (norm or ""):gmatch("%S+") do
        pos = pos + 1
        local spell = C.BLESSING_SHORT[tok]
        if not spell and #tok >= 3 then
            for _, b in ipairs(C.BLESSINGS) do
                if b.word:sub(1, #tok) == tok then spell = b.spell break end
            end
        end
        if spell then found, at = spell, pos end   -- the last one named wins
    end
    return found
end
C.BY_KEY = {}
for _, s in ipairs(C.SERVICES) do C.BY_KEY[s.key] = s end

-- Settings for one service: the catalog default, then what was saved.
-- Saved price: a number in silver, or false for "free" (blank box).
-- where: the city, for a price that follows the market there (C.LivePrice, set by the addon)
function C.Setting(db, key, where)
    local def = C.BY_KEY[key]
    if not def then return { on = false, invite = false, payee = "", words = "" } end   -- no longer sold
    local saved = (type(db) == "table" and type(db.services) == "table" and db.services[key]) or {}
    local price = def.price
    if key == "summons" and saved.price == nil and type(db) == "table" and type(db.price) == "number" then price = db.price end
    if saved.price ~= nil then price = saved.price or nil end
    if type(price) == "number" and price <= 0 then price = nil end   -- 0 is free (Lua counts 0 as true)
    if price and C.LivePrice then price = C.LivePrice(key, price, saved, where) or price end
    local function pick(field) if saved[field] ~= nil then return saved[field] end return def[field] end
    return {
        on = pick("on") and true or false,
        invite = pick("invite") and true or false,
        price = price,
        words = pick("words"),
        payee = saved.payee or "",          -- "" = the default from the General tab
        untick = saved.untick or {},        -- portals the mage has not trained
        spell = saved.spell or def.spell,   -- buffs: the spell the buff button casts (a paladin picks the blessing)
    }
end

function C.SplitWords(s)
    local list = {}
    for piece in tostring(s or ""):lower():gmatch("[^,]+") do
        piece = piece:gsub("^%s+", ""):gsub("%s+$", "")
        if piece ~= "" then list[#list + 1] = piece end
    end
    return list
end

-- Money in chat. nil = nil (free).
-- Spelled out (the owner, 13 Nov 2026: "spells out silver and gold instead of s and g"):
-- "25 silver", "1 gold", "1 gold 50 silver".
function C.Money(silver)
    if not silver then return nil end
    local copper = math.floor(silver * 100 + 0.5)
    local g, s, c = math.floor(copper / 10000), math.floor(copper / 100) % 100, copper % 100
    local parts = {}
    if g > 0 then parts[#parts + 1] = g .. " gold" end
    if s > 0 then parts[#parts + 1] = s .. " silver" end
    if c > 0 then parts[#parts + 1] = c .. " copper" end
    if #parts == 0 then return "0 silver" end
    return table.concat(parts, " ")
end

-- The price a buyer names, in silver ("25s", "25 silver", "1g", "1g50s", "1g 50s", "2 gold",
-- "50c", "25s50c" -- copper too, the owner: "need to know c too"), or nil when they name
-- none. A bare number is not a price ("lvl 25", "5 summons").
local UNIT = { g = 100, gold = 100, s = 1, silver = 1, sil = 1, c = 0.01, copper = 0.01, cop = 0.01 }
local function TokenPrice(t)            -- "1g50s25c" -> 150.25; nil unless the whole token is money
    local sum, any = 0, false
    local rest = t:gsub("(%d+)(%a+)", function(n, u)
        if UNIT[u] then sum, any = sum + tonumber(n) * UNIT[u], true return "" end
    end)
    if any and rest == "" then return sum end
    return nil
end
function C.OfferedPrice(text)
    local toks = {}
    for t in tostring(text or ""):lower():gsub("[^%w]", " "):gmatch("%S+") do toks[#toks + 1] = t end
    local i, total, found = 1, 0, false
    while i <= #toks do
        local t, used = toks[i], 1
        local amount = TokenPrice(t)
        if not amount and t:match("^%d+$") and UNIT[toks[i + 1] or ""] then amount, used = tonumber(t) * UNIT[toks[i + 1]], 2 end
        if amount then total, found = total + amount, true
        elseif found then break end            -- "1g 50s" adds up; stop at the next word
        i = i + used
    end
    return found and total or nil
end

-- How many people a request is for ("for 2", "x2", "2x", "2 ppl", "3 of us"), or nil for
-- one. "summon 2 uc" (2 = to) and "for 2 gold" (a price) are not a head count.
local HEADS = { ppl = true, people = true, players = true, peeps = true, guys = true, of = true, chars = true }
function C.PartySize(text)
    local t = " " .. tostring(text or ""):lower():gsub("[^%w]", " ") .. " "
    local n
    for num, after in t:gmatch(" for (%d+) (%a*)") do if not UNIT[after] then n = tonumber(num) end end
    n = n or tonumber(t:match(" x(%d+) ") or t:match(" (%d+)x "))
    if not n then
        for num, word in t:gmatch(" (%d+) (%a+)") do if HEADS[word] then n = tonumber(num) end end
    end
    return (n and n >= 2 and n <= 40) and n or nil
end

-- Who in the group can do a service: members of the class at or above its level. For you,
-- a spell list read from your spellbook wins over the level rule where it applies.
-- A member whose level the game didn't give us is not ruled out by level.
-- Summons follow your role: as the helper you are not the summoner even if you are a
-- warlock (notSummoner); as the lock you are the first choice (summoner).
function C.CanDo(member, def)
    if not member or not def or member.class ~= def.class then return false end
    if member.customer or member.notProvider then return false end   -- a customer, or not one of "ours"
    if member.level and member.level < def.level then return false end
    if def.kind == "summon" and member.notSummoner then return false end
    return true
end
function C.Providers(group, key)
    local def, out = C.BY_KEY[key], {}
    if not def then return out end   -- a service no longer sold (summons and blessings only)
    for _, m in ipairs(group or {}) do if C.CanDo(m, def) then out[#out + 1] = m end end
    if def.kind == "summon" then
        table.sort(out, function(a, b) return (a.summoner and 1 or 0) > (b.summoner and 1 or 0) end)
    end
    return out
end
-- The one to do it; with `where`, the one standing there (two warlocks in two places
-- each summon to their own).
-- For portals, `where` is the city they want: the first mage who can portal there.
function C.Provider(group, key, where)
    local list = C.Providers(group, key)
    if where and C.BY_KEY[key] and C.BY_KEY[key].kind == "portal" then
        for _, m in ipairs(list) do
            for _, city in ipairs(C.PortalCities(m)) do if city == where then return m end end
        end
        return nil
    end
    if where then for _, m in ipairs(list) do if m.zone == where then return m end end end
    return list[1]
end

-- The cities a mage can portal a customer to: what you know (your spellbook) or, for a
-- friend, what faction and level give; never the city they are standing in; minus any the
-- owner unticked. With no faction, either faction's list (the city names differ).
function C.PortalCities(mage, faction, untick)
    local out = {}
    local list = C.PORTALS[faction]
    if not list then
        list = {}
        for _, f in ipairs({ "Horde", "Alliance" }) do for _, pl in ipairs(C.PORTALS[f]) do list[#list + 1] = pl end end
    end
    for _, pl in ipairs(list) do
        local city, lvl = pl[1], pl[2]
        local has
        if mage.me and mage.knows then has = mage.knows[C.PORTAL_SPELL[city]] and true or false
        else has = (mage.level or 0) >= lvl end
        if has and city ~= mage.zone and not (untick or {})[city] then out[#out + 1] = city end
    end
    return out
end

-- What is on sale right now, given the group: a list of { key, def, setting, provider, where,
-- cities (portals) }. A service with nobody to do it is not on sale. Summons are one entry
-- per warlock, each to where that warlock stands (where = nil: the game didn't say, so
-- nothing is invited for it; we never assume a place).
function C.OnSale(db, group, faction)
    local out = {}
    for _, def in ipairs(C.SERVICES) do
        local st = C.Setting(db, def.key)
        if st.on and def.kind == "summon" then
            local seen = {}
            for _, p in ipairs(C.Providers(group, def.key)) do
                local k = p.zone or ("?" .. p.name)
                if not seen[k] then
                    seen[k] = true
                    out[#out + 1] = { key = def.key, def = def, setting = st, provider = p, where = p.zone }
                end
            end
        elseif st.on and def.kind == "portal" then
            -- every mage counts: each sells the cities no mage before them already covers
            local covered = {}
            for _, p in ipairs(C.Providers(group, def.key)) do
                local cities = {}
                for _, city in ipairs(C.PortalCities(p, faction, st.untick)) do
                    if not covered[city] then covered[city] = true cities[#cities + 1] = city end
                end
                if #cities > 0 then
                    out[#out + 1] = { key = def.key, def = def, setting = st, provider = p, where = p.zone, cities = cities }
                end
            end
        elseif st.on then
            local p = C.Provider(group, def.key)
            if p then out[#out + 1] = { key = def.key, def = def, setting = st, provider = p, where = p.zone } end
        end
    end
    return out
end

-- Who gets paid for a customer of this service, landing in `here`.
-- Default (db.payee): { mode = "provider" | "me" | "name", name = "..." }.
--   provider: the person doing the service. You only when you picked "me" (the owner,
--   12 Nov 2026: "but only when i select they pay me, right?"). An old saved "place"
--   means provider too.
-- Per service (setting.payee): "" = default, "me", "provider", or a name.
function C.Payee(db, group, key, provider, here)
    local me
    for _, m in ipairs(group or {}) do if m.me then me = m end end
    local myName = me and me.name or "me"
    local st = C.Setting(db, key)
    local rule = st.payee
    if rule == nil or rule == "" then
        local d = (type(db) == "table" and type(db.payee) == "table") and db.payee or {}
        local mode = d.mode
        if mode == nil and type(db) == "table" then
            -- 1.5/1.6 setting "I collect the payment" still means what it said
            if db.collect == true then mode = "me" elseif db.collect == false then mode = "notme" end
        end
        mode = mode or "provider"
        if mode == "me" then rule = "me"
        elseif mode == "name" and d.name and d.name ~= "" then rule = d.name
        elseif mode == "provider" or mode == "notme" then rule = mode
        else rule = "provider" end
    end
    if rule == "me" then return myName end
    if rule == "provider" then return provider and provider.name or myName end
    if rule == "notme" then
        if provider and not provider.me then return provider.name end
        return "someone else"
    end
    if rule == "place" then return provider and provider.name or myName end
    return rule
end

local function priceText(silver) return C.Money(silver) end

-- A name as said in party/raid chat: between its raid icons ({rt1}Yeet{rt1}) when the member
-- has one, so everyone can match the message to the person. The owner, 13 Nov 2026: "i want
-- them surrounding".
function C.Mark(mark, name) return mark and ("{rt" .. mark .. "}" .. name .. "{rt" .. mark .. "}") or name end
function C.Label(group, name)
    for _, m in ipairs(group or {}) do
        if m.name == name and m.mark then return C.Mark(m.mark, name) end
    end
    return name
end

-- The ad: built from what is on sale. Returns text or nil, why.
function C.BuildAd(db, group, faction, template)
    local parts, anyPaid = {}, false
    local places, summonSt = {}, nil
    local low
    for _, it in ipairs(C.OnSale(db, group, faction)) do
        if it.def.kind == "summon" and it.where then
            places[#places + 1] = C.Short(it.where) summonSt = it.setting
            -- one price in the ad: the lowest of the cities (each may be following a rival)
            local p = C.Setting(db, "summons", it.where).price
            if p and (not low or p < low) then low = p end
        end
    end
    if #places > 0 then
        local m = priceText(low or summonSt.price)
        if m then anyPaid = true end
        parts[#parts + 1] = "summons to " .. table.concat(places, "/") .. (m and (" " .. m) or "")
        if not m then parts[#parts] = "free " .. parts[#parts] end
    end
    for _, it in ipairs(C.OnSale(db, group, faction)) do
        local def, st = it.def, it.setting
        local text
        if def.kind == "summon" then
            text = nil
        elseif def.kind == "portal" then
            local short = {}
            for _, c in ipairs(it.cities) do short[#short + 1] = C.Short(c) end
            text = "portals to " .. table.concat(short, "/")
        else
            text = def.label
        end
        if text and def.kind ~= "buff" then
            local m = priceText(st.price)
            if m then anyPaid = true text = text .. " " .. m else text = "free " .. text end
            if def.kind ~= "summon" and it.where then text = text .. " (at " .. C.Short(it.where) .. ")" end
            parts[#parts + 1] = text
        end
    end
    if #parts == 0 then return nil, "nothing to sell: no one in the group can do what's ticked" end
    local list = table.concat(parts, ", ")
    if not anyPaid then list = list:gsub("^free ", "Free ") end
    local t = (template and template ~= "") and template or "{wts}{services} | whisper inv"
    t = t:gsub("{wts}", anyPaid and "WTS " or ""):gsub("{services}", function() return list end)
    if #t > 255 then return nil, "too long for chat (" .. #t .. " letters); untick something or shorten the ad" end
    return t
end

-- The welcome when an invited customer joins: what they get, who does it, where, the price,
-- and who to pay. Returns text or nil, why.
-- price: what this customer was quoted (fixed when invited); nil = today's price there
function C.JoinWelcome(db, group, faction, key, name, dest, quoted)
    local def = C.BY_KEY[key]
    if not def then return nil, "unknown service" end
    local p = C.Provider(group, key, (def.kind == "summon" or def.kind == "portal") and dest or nil)
    if not p then return nil, "nobody in the group can do it any more" end
    local st = C.Setting(db, key)
    local me
    for _, m in ipairs(group or {}) do if m.me then me = m end end
    local here = p.zone
    local payee = C.Payee(db, group, key, p, here)
    local payWord = (me and payee == me.name) and "me" or C.Label(group, payee)
    local mine = me and p.name == me.name
    local price = priceText(quoted or C.Setting(db, key, here).price)
    if def.kind == "summon" then
        local doer = mine and "I'll" or (C.Label(group, p.name) .. " will")
        return ("Hi %s! %s summon you to %s. %s. Pay %s when you land."):format(name, doer, C.Short(here or "us"), price or "Free", payWord)
    end
    local what = def.label
    if def.kind == "portal" then what = "a portal to " .. C.Short(dest or "your city") end
    local doer = mine and "I'll do" or (C.Label(group, p.name) .. " will do")
    local to = mine and "come to me" or ("come to " .. C.Label(group, p.name))
    if here then to = to .. " in " .. C.Short(here) end
    if not price then return ("Hi %s! %s %s, %s. Free, tips welcome."):format(name, doer, what, to) end
    return ("Hi %s! %s %s, %s. %s. Pay %s there."):format(name, doer, what, to, price, payWord)
end

-- On arrival: what else the group offers where the customer landed, leaving out what they
-- came for. Only people standing in `here` count. Returns text or nil, why.
function C.ArrivalOffer(db, group, faction, here, bought, name, template)
    if not here then return nil, "don't know where they landed" end
    local parts = {}
    for _, def in ipairs(C.SERVICES) do
        local st = C.Setting(db, def.key)
        if st.on and def.key ~= bought then
            local p
            for _, m in ipairs(group or {}) do if C.CanDo(m, def) and m.zone == here then p = m break end end
            if p then
                local text
                if def.kind == "portal" then
                    local cities = C.PortalCities(p, faction, st.untick)
                    if #cities > 0 then
                        local short = {}
                        for _, c in ipairs(cities) do short[#short + 1] = C.Short(c) end
                        text = "portals to " .. table.concat(short, "/")
                    end
                elseif def.kind ~= "summon" then
                    text = def.label
                end
                if text then
                    local m = priceText(st.price)
                    parts[#parts + 1] = m and (text .. " " .. m) or ("free " .. text)
                end
            end
        end
    end
    if #parts == 0 then return nil, "nothing else on offer there" end
    local t = (template and template ~= "") and template or "Welcome to {here}, {name}! Also here: {offers}. Just ask!"
    t = t:gsub("{here}", function() return C.Short(here) end):gsub("{name}", function() return name or "" end)
    t = t:gsub("{offers}", function() return table.concat(parts, ", ") end)
    return t
end
