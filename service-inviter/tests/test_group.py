"""The live paths with a group in the world: chat in, invite, join, arrive, pay, advertise.
Members are stubbed as the game reports them (name, class, level, zone)."""
import pytest

from conftest import Game

TRADE = ("", "2. Trade - City", "", "", "", "", "Trade")


def world(units, services="", extra=""):
    """units: {unit: (name, CLASS, level, zone or None)}. services: Lua table body for db.services."""
    rows = ", ".join(
        f'{u} = {{ "{n}", "{c}", {lvl}, {("nil" if z is None else repr(z).replace(chr(39), chr(34)))} }}'
        for u, (n, c, lvl, z) in units.items())
    before = f"""
UNITS = {{ {rows} }}
function UnitExists(u) return UNITS[u] ~= nil end
function UnitName(u) local x = UNITS[u] return x and x[1] end
function GetUnitName(u) local x = UNITS[u] return x and x[1] end
function UnitClass(u) local x = UNITS[u] if not x then return nil end return x[2], x[2] end
function UnitLevel(u) local x = UNITS[u] return x and x[3] end
function GetRealZoneText() return UNITS.player[4] end
C_Map = {{ GetBestMapForUnit = function(u) return UNITS[u] and u end,
          GetMapInfo = function(u) local x = UNITS[u] return x and x[4] and {{ name = x[4] }} end }}
function UnitFactionGroup() return "Horde" end
GROUP = {{}} for u, x in pairs(UNITS) do if u ~= "player" then GROUP[x[1]] = true end end
function UnitIsVisible() return true end
function CheckInteractDistance() return true end
function GetChannelList() return 2, "Trade - City", false end
{extra}
"""
    g = Game(before)
    if services:
        g.run(f"ServiceInviterDB.services = {{ {services} }}")
    return g


def say_trade(g, sender, text):
    g.event("CHAT_MSG_CHANNEL", text, sender, *TRADE)


def whisper(g, sender, text):
    g.event("CHAT_MSG_WHISPER", text, sender, "", "", "", "", "", "", "")


def invited(g):
    return list(g.g.INVITED.values())


def job(g, name, field):
    return g.eval(f'ServiceInviter_Test.Jobs.Get("{name}").{field}')


ME_ORG_SHAMAN = ("Me", "SHAMAN", 60, "Orgrimmar")


# -- Who gets invited, from who is in the group ---------------------------------------------------

def test_lockpicking_buyer_is_invited_when_you_are_a_rogue_selling_it():
    g = world({"player": ("Me", "ROGUE", 60, "Thunder Bluff")}, "lockpick = { on = true }")
    say_trade(g, "Kaldrok", "WTB someone to open my lockbox")
    assert invited(g) == ["Kaldrok"]
    assert job(g, "Kaldrok", "service") == "lockpick"


def test_lockpicking_buyer_is_not_invited_with_no_rogue():
    g = world({"player": ME_ORG_SHAMAN}, "lockpick = { on = true }")
    say_trade(g, "Kaldrok", "WTB someone to open my lockbox")
    assert invited(g) == []


def test_summons_follow_the_warlock():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Undercity")})
    say_trade(g, "Kaldrok", "WTB summon to UC")
    say_trade(g, "Mirasha", "WTB summon to TB")
    assert invited(g) == ["Kaldrok"]
    assert job(g, "Kaldrok", "dest") == "Undercity"


def test_where_the_warlock_is_unknown_nobody_is_invited_for_summons():
    """The owner, 12 Nov 2026, on the old fallback list: "what's the point in this ... we might as
    well just not try to identify their location". We never assume a place."""
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, None)})
    say_trade(g, "Kaldrok", "WTB summon to TB")
    assert invited(g) == []


TWO_LOCKS = {"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
             "party2": ("Ashfel", "WARLOCK", 60, "Undercity")}


def test_two_warlocks_take_requests_for_both_places():
    """The owner: "also what if we had multiple warlocks"."""
    g = world(TWO_LOCKS)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    say_trade(g, "Mirasha", "WTB summon to UC")
    say_trade(g, "Thrall", "WTB summon to Org")
    assert invited(g) == ["Kaldrok", "Mirasha"]


def test_each_customer_is_told_their_own_warlock():
    g = world(TWO_LOCKS)
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    sent = [m for ch, _, m in g.sent() if ch == "PARTY"]
    assert sent == ["Hi {rt4}Mirasha{rt4}! {rt3}Ashfel{rt3} will summon you to UC. 25 silver. Pay {rt3}Ashfel{rt3} when you land."]


def test_the_ad_lists_both_places():
    g = world(TWO_LOCKS)
    g.run("ServiceInviter_Test.PostAd()")
    assert [m for ch, _, m in g.sent() if ch == "CHANNEL"] == ["WTS summons to TB/UC 25 silver | whisper inv"]


def test_two_warlocks_in_one_place_are_one_offer():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
               "party2": ("Ashfel", "WARLOCK", 60, "Thunder Bluff")})
    g.run("ServiceInviter_Test.PostAd()")
    assert [m for ch, _, m in g.sent() if ch == "CHANNEL"] == ["WTS summons to TB 25 silver | whisper inv"]


def test_no_warlock_no_summon_invites():
    g = world({"player": ME_ORG_SHAMAN})
    say_trade(g, "Kaldrok", "WTB summon to TB")
    assert invited(g) == []


def test_a_level_47_mage_takes_uc_ports_but_not_tb_or_his_own_city():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Velenne", "MAGE", 47, "Orgrimmar")},
              "summons = { on = false }, portals = { on = true, price = 20 }")
    say_trade(g, "Kaldrok", "wtb port to UC")
    say_trade(g, "Mirasha", "wtb port to TB")
    say_trade(g, "Thrall", "wtb port to Org")
    assert invited(g) == ["Kaldrok"]
    assert job(g, "Kaldrok", "service") == "portals"


# -- Join, arrive, pay ------------------------------------------------------------------------------

def test_the_welcome_says_what_who_where_price_and_payee():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")})
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    sent = [m for ch, _, m in g.sent() if ch == "PARTY"]
    assert sent == ["Hi {rt3}Kaldrok{rt3}! {rt1}Grimtotem{rt1} will summon you to TB. 25 silver. Pay {rt1}Grimtotem{rt1} when you land."]


def test_arrival_offers_what_is_there():
    g = world({"player": ("Me", "ROGUE", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")},
              "lockpick = { on = true, invite = false }")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run('''local J = ServiceInviter_Test.Jobs J.Joined("Kaldrok") J.Set("Kaldrok", "summoned")
             CLOCK = CLOCK + 41 ServiceInviter_Test.CheckArrivals()''')  # no unit to see: 40s fallback
    sent = [m for ch, _, m in g.sent() if ch == "PARTY"]
    assert "Welcome to TB, {rt4}Kaldrok{rt4}! Also here: free lockpicking. Just ask!" in sent


def test_a_free_service_marks_a_tip_as_paid():
    g = world({"player": ("Me", "ROGUE", 60, "Thunder Bluff")}, "lockpick = { on = true }")
    say_trade(g, "Kaldrok", "WTB lockbox opened")
    g.run('''local J = ServiceInviter_Test.Jobs J.Joined("Kaldrok") J.Set("Kaldrok", "summoned") J.Set("Kaldrok", "arrived")
             UNITS.npc = { "Kaldrok" } function UnitName(u) if u == "NPC" then return "Kaldrok" end local x = UNITS[u] return x and x[1] end''')
    g.event("TRADE_SHOW")
    g.g.TRADEMONEY = 500
    g.event("TRADE_ACCEPT_UPDATE", 1, 1)
    g.event("TRADE_CLOSED")
    assert g.status("Kaldrok") == "paid"


# -- Advertising -----------------------------------------------------------------------------------

def test_posting_the_ad_and_an_inv_whisper_answering_it():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")})
    g.run("ServiceInviter_Test.PostAd()")
    chan = [(ch, to, m) for ch, to, m in g.sent() if ch == "CHANNEL"]
    assert chan == [("CHANNEL", 2, "WTS summons to TB 25 silver | whisper inv")]
    whisper(g, "Mirasha", "inv")
    assert invited(g) == ["Mirasha"]
    assert "answered your ad" in job(g, "Mirasha", "why")


def test_inv_whisper_without_an_ad_is_ignored_when_keywords_are_off():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")})
    whisper(g, "Mirasha", "inv")
    assert invited(g) == []


def test_the_ad_waits_between_posts():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")})
    g.run("ServiceInviter_Test.PostAd() ServiceInviter_Test.PostAd()")
    assert len([1 for ch, _, _ in g.sent() if ch == "CHANNEL"]) == 1
    g.run("CLOCK = CLOCK + 301 ServiceInviter_Test.PostAd()")
    assert len([1 for ch, _, _ in g.sent() if ch == "CHANNEL"]) == 2


def test_nothing_to_sell_posts_nothing():
    g = world({"player": ME_ORG_SHAMAN})
    g.run("ServiceInviter_Test.PostAd()")
    assert [1 for ch, _, _ in g.sent() if ch == "CHANNEL"] == []


# -- Carrying 1.x settings over --------------------------------------------------------------------

def test_old_extras_become_offered_services_that_dont_invite():
    g = world({"player": ME_ORG_SHAMAN})
    g.run('ServiceInviterDB.offers = { lockpick = true, food = true } ServiceInviterDB.price = 150')
    g.event("PLAYER_LOGIN")
    assert g.eval('ServiceInviterCore.Setting(ServiceInviterDB, "lockpick").on') is True
    assert g.eval('ServiceInviterCore.Setting(ServiceInviterDB, "lockpick").invite') is False
    assert g.eval('ServiceInviterCore.Setting(ServiceInviterDB, "water").on') is True
    assert g.eval('ServiceInviterCore.Setting(ServiceInviterDB, "summons").price') == 150


# -- Setup: who gets paid is picked from the group; who summons is shown ------------------------

def test_payee_pick_list_offers_the_group_and_fills_the_box():
    """The owner: "can 'who gets paid' be a suggestion/drop down from the raid/party?"."""
    g = world(TWO_LOCKS)
    g.run('''SETUP = ServiceInviter_Test.BuildSetup() SETUP:Show()
             BOX = ServiceInviter_Test.SetupBoxes().svc_summons_payee
             ServiceInviter_Test.ShowPicker(BOX, true)''')
    labels = [g.eval(f"ServiceInviterPicker.buttons[{i}]:GetText()") for i in range(1, 5)]
    assert labels == ["Default", "Me (Me)",
                      "|cff8788eeGrimtotem|r  (Thunder Bluff)", "|cff8788eeAshfel|r  (Undercity)"]
    g.run("ServiceInviterPicker.buttons[4]._scripts.OnClick()")
    assert g.eval("BOX:GetText()") == "Ashfel"


def test_warlock_tab_says_where_each_warlock_summons_to():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
               "party2": ("Ashfel", "WARLOCK", 60, None)})
    g.run("SETUP = ServiceInviter_Test.BuildSetup() SETUP:Show() SETUP.Refresh()")
    assert g.eval("SETUP.locks:GetText()") == "|cff8788eeGrimtotem|r: Thunder Bluff\n|cff8788eeAshfel|r: where? (the game didn't say)"


def test_a_warlocks_ritual_is_for_their_own_customer():
    """Ashfel (Undercity) starts summoning: the alert is for the customer going to Undercity,
    and says to pay Ashfel; Grimtotem's customer keeps waiting."""
    g = world(TWO_LOCKS)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party2", 698, "Ritual of Summoning")')
    alerts = [m for ch, _, m in g.sent() if m.startswith("SUMMONING")]
    assert alerts == ["SUMMONING {rt5}Mirasha{rt5} TO UNDERCITY! PAY {rt3}Ashfel{rt3} 25 silver IN THE TRADE WINDOW ON ARRIVAL!"]
    assert g.status("Mirasha") in ("summoned", "arrived")
    assert g.status("Kaldrok") == "joined"


def test_payee_pick_list_alone_says_where_party_members_go():
    """The owner, seeing it alone: "wtf does this mean". It has a title and says what's missing."""
    g = world({"player": ME_ORG_SHAMAN})
    g.run('''SETUP = ServiceInviter_Test.BuildSetup() SETUP:Show()
             ServiceInviter_Test.ShowPicker(ServiceInviter_Test.SetupBoxes().svc_summons_payee, true, "Who gets paid for summons?", "summons")''')
    assert g.eval("ServiceInviterPicker.title:GetText()") == "Who gets paid for summons?"
    assert g.eval("ServiceInviterPicker.note:GetText()") == "Party and raid members show up here."
    # the owner: "so basically that would mean the warlock in general or what i am confused"
    assert g.eval("ServiceInviterPicker.sub:GetText()") == "Default: the warlock"


# -- Class colors and short lines -------------------------------------------------------------

def test_each_customer_row_says_where_and_who_in_class_color():
    """The owner: "can this use class colors and stuff to avoid a mass of confusing text"."""
    g = world(TWO_LOCKS)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.run("ServiceInviter_Test.Refresh()")
    rows = [(g.eval(f"ServiceInviterJobs.rows[{i}].service:GetText()"), g.eval(f"ServiceInviterJobs.rows[{i}].where:GetText()")) for i in (1, 2)]
    assert rows == [("Summons to Thunder Bluff", "|cff8788eeGrimtotem|r in Thunder Bluff"),
                    ("Summons to Undercity", "|cff8788eeAshfel|r in Undercity")]


def test_the_invite_line_says_who_and_exactly_why():
    """The owner, 13 Nov 2026: "why is it no longer telling me exactly why people are invited? i
    want that". 2.0.8 had moved the reason to debug only."""
    g = world(TWO_LOCKS)
    say_trade(g, "Kaldrok", "WTB summon to TB, will tip, pst")
    p = g.printed()
    i = next(i for i, l in enumerate(p) if "invited" in l)
    assert p[i].endswith("invited Kaldrok  -> TB  ·  |cff8788eeGrimtotem|r")
    assert 'because [Trade] "WTB summon to TB, will tip, pst"' in p[i + 1]
    assert "summon to Thunder Bluff" in p[i + 1]


def test_chat_lines_are_not_recolored():
    """The owner, on recoloring names only on their own screen: "no point if other cannot see it"."""
    g = world(TWO_LOCKS, extra="FILTERS = {} function ChatFrame_AddMessageEventFilter(ev, fn) FILTERS[ev] = fn end")
    assert g.eval("next(FILTERS)") is None


# -- Raid icons: who does it, marked in chat -------------------------------
# The owner, on the mockup (star for the first warlock, diamond for the second): "I think that works fine".

MARKS = """
MARKS_SET = {}
CURRENT = {}
function GetRaidTargetIndex(u) return CURRENT[u] end
function SetRaidTarget(u, i) MARKS_SET[#MARKS_SET + 1] = u .. "=" .. i CURRENT[u] = i end
"""


def test_each_warlock_gets_an_icon_in_the_welcome():
    g = world(TWO_LOCKS, extra=MARKS)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    sent = [m for ch, _, m in g.sent() if ch == "PARTY"]
    assert sent == ["Hi {rt4}Kaldrok{rt4}! {rt1}Grimtotem{rt1} will summon you to TB. 25 silver. Pay {rt1}Grimtotem{rt1} when you land.",
                    "Hi {rt5}Mirasha{rt5}! {rt3}Ashfel{rt3} will summon you to UC. 25 silver. Pay {rt3}Ashfel{rt3} when you land."]


def test_the_summon_alert_carries_the_icon():
    g = world(TWO_LOCKS, extra=MARKS)
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party2", 698, "Ritual of Summoning")')
    alerts = [m for ch, _, m in g.sent() if m.startswith("SUMMONING")]
    assert alerts == ["SUMMONING {rt4}Mirasha{rt4} TO UNDERCITY! PAY {rt3}Ashfel{rt3} 25 silver IN THE TRADE WINDOW ON ARRIVAL!"]


def test_icons_are_never_put_over_heads():
    """SetRaidTarget is protected since patch 12.0 (Forever runs on those rules): calling it from
    a timer is what put up the "blocked from an action only available to the Blizzard UI" popup
    the owner saw on 12 Nov 2026. Icons stay in chat, which is only text."""
    g = world(TWO_LOCKS, extra=MARKS)
    for _ in range(5):
        g.run("CLOCK = CLOCK + 3 ServiceInviter_Test.CheckArrivals()")
    assert len(g.g.MARKS_SET) == 0


def test_an_icon_someone_already_put_on_the_warlock_is_kept_and_used():
    g = world(TWO_LOCKS, extra=MARKS + 'CURRENT["party1"] = 6')
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert "Pay {rt6}Grimtotem{rt6}" in [m for ch, _, m in g.sent() if ch == "PARTY"][0]


def test_icons_can_be_turned_off():
    g = world(TWO_LOCKS, extra=MARKS)
    g.run("ServiceInviterDB.opts = { marks = false }")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert "{rt" not in [m for ch, _, m in g.sent() if ch == "PARTY"][0]


def test_the_ad_in_trade_never_has_icons():
    g = world(TWO_LOCKS, extra=MARKS)
    g.run("ServiceInviter_Test.PostAd()")
    assert "{rt" not in [m for ch, _, m in g.sent() if ch == "CHANNEL"][0]


# -- When the game blocks a call -----------------------------------------------------------------

def test_a_blocked_call_is_named_and_never_retried():
    """The owner, 12 Nov 2026, with the game's "blocked from an action only available to the
    Blizzard UI" popup: "idk what caused this". Next time the addon says which call it was."""
    g = world({"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}, extra="TRADED = {} function InitiateTrade(u) TRADED[#TRADED + 1] = u end")
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.payee = { mode = "me" }')
    g.event("ADDON_ACTION_FORBIDDEN", "ServiceInviter", "InitiateTrade()")
    assert any("blocked InitiateTrade()" in p for p in g.printed())
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run('''local J = ServiceInviter_Test.Jobs J.Joined("Kaldrok") J.Set("Kaldrok", "summoned")
             UNITS.party1 = { "Kaldrok", "MAGE", 44, "Thunder Bluff" } GROUP["Kaldrok"] = true
             CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals() CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()''')
    assert len(g.g.TRADED) == 0


def test_another_addons_block_is_not_ours():
    g = world({"player": ("Me", "SHAMAN", 60, "Orgrimmar")})
    g.event("ADDON_ACTION_FORBIDDEN", "SomeOtherAddon", "CastSpellByName()")
    assert not any("blocked" in p for p in g.printed())


# -- "hey anyone able to summon me to barrens or org?" (the owner's screenshot, 12 Nov 2026) --------

SUMMONS_CH = ("", "6. summons", "", "", "", "", "summons")
TRIPLE = "hey anyone able to summon me to barrens or org?"


def ask_in_summons(units, text=TRIPLE, sender="Triple"):
    g = world(units, extra='function GetChannelList() return 6, "summons", false end')
    g.event("CHAT_MSG_CHANNEL", text, sender, *SUMMONS_CH)
    return g


def test_summon_me_is_a_request_with_a_warlock_in_org():
    g = ask_in_summons({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Orgrimmar")})
    assert invited(g) == ["Triple"]
    assert job(g, "Triple", "dest") == "Orgrimmar"


def test_the_barrens_is_matched_without_the():
    g = ask_in_summons({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "The Barrens")})
    assert invited(g) == ["Triple"]
    assert job(g, "Triple", "dest") == "The Barrens"


def test_summon_me_somewhere_nobody_is_still_not_invited():
    g = ask_in_summons({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")})
    assert invited(g) == []


def test_port_me_is_a_request_too():
    g = ask_in_summons({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Orgrimmar")}, "can someone port me to org")
    assert invited(g) == ["Triple"]


def test_a_seller_offering_to_summon_you_is_not_a_request():
    g = ask_in_summons({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Orgrimmar")}, "can summon you to org, 5g, whisper me")
    assert invited(g) == []


def test_icons_surround_the_name_and_customers_get_their_own():
    """The owner, 13 Nov 2026, on "SUMMONING Neato Smoothbrain! PLEASE PAY {star}Yeet": "the raid
    icons dont have anything for neato and i want them surrounding"."""
    g = world(TWO_LOCKS, extra=MARKS)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    sent = [m for ch, _, m in g.sent() if ch == "PARTY"]
    # warlocks: star and diamond; customers: the next free icons, kept per customer
    assert sent[0].startswith("Hi {rt4}Kaldrok{rt4}! {rt1}Grimtotem{rt1} will summon")
    assert sent[1].startswith("Hi {rt5}Mirasha{rt5}! {rt3}Ashfel{rt3} will summon")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party2", 698, "Ritual of Summoning")')
    assert [m for _, _, m in g.sent() if m.startswith("SUMMONING")] == \
        ["SUMMONING {rt5}Mirasha{rt5} TO UNDERCITY! PAY {rt3}Ashfel{rt3} 25 silver IN THE TRADE WINDOW ON ARRIVAL!"]


# -- Values the game hides (secret values) and errors that would stop the windows -------------------
# The owner, 13 Nov 2026, in a raid in Thunder Bluff with a level 22 warlock: the Warlock tab's
# "Summons go to" was blank (not even "no warlock") and the window "kinda froze" earlier: the
# once-a-second update was failing. The game hides Lua errors unless told to show them.

RAID_TB = {"player": ("Mooveover", "SHAMAN", 30, "Thunder Bluff"),
           "raid1": ("Yeet Lock", "WARLOCK", 22, "Thunder Bluff"),
           "raid2": ("Mooveover", "SHAMAN", 30, "Thunder Bluff")}
IN_RAID = """function IsInRaid() return true end
function UnitIsUnit(a, b) local x, y = UNITS[a], UNITS[b] return x ~= nil and y ~= nil and x[1] == y[1] end"""


def test_a_value_the_game_hides_counts_as_unknown_not_a_crash():
    """issecretvalue says the warlock's level, zone and raid icon are hidden: the group still reads,
    with those as unknown."""
    g = world(RAID_TB, extra=IN_RAID + """
function issecretvalue(v) return v == 22 or v == 8 end
function GetRaidTargetIndex(u) if u == "raid1" then return 8 end end""")
    g.run('UNITS.raid1[4] = 8')  # the zone comes back hidden too
    grp = g.eval("ServiceInviter_Test.Group()")
    lock = [grp[i] for i in range(1, len(grp) + 1) if grp[i].name == "Yeet Lock"][0]
    assert lock.level is None and lock.zone is None and lock.mark != 8


def test_the_warlock_tab_shows_the_warlock_in_a_raid():
    g = world(RAID_TB, extra=IN_RAID)
    g.run("local w = ServiceInviter_Test.BuildSetup() w:Show() w.ShowTab(2) w.Refresh()")
    assert g.eval("ServiceInviterSetup.locks:GetText()") == "|cff8788eeYeet Lock|r: Thunder Bluff"


def test_an_error_in_the_update_is_reported_once_in_chat():
    g = world(RAID_TB, extra=IN_RAID)
    g.run("local w = ServiceInviter_Test.BuildSetup() w:Show() ServiceInviterCore.OnSale = function() error('boom') end")
    for _ in range(3):
        g.run("ServiceInviterSetup._scripts.OnUpdate(ServiceInviterSetup, 1)")
    hits = [p for p in g.printed() if "boom" in p]
    assert len(hits) == 1 and "send" in hits[0].lower()


def test_the_summon_alert_says_where_even_with_your_own_text():
    """The owner, 13 Nov 2026: "can the 'summoning name' part say where we are summoning to? so
    they know". Their own text had no {dest}: it goes in after the name."""
    g = world(TWO_LOCKS)
    g.run('ServiceInviterDB.alertmsg = "SUMMONING {name}! PLEASE PAY {payee} {price} UPON ARRIVAL!" ServiceInviterDB.opts = { marks = false }')
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party2", 698, "Ritual of Summoning")')
    assert [m for _, _, m in g.sent() if m.startswith("SUMMONING")] == \
        ["SUMMONING Mirasha TO UNDERCITY! PLEASE PAY Ashfel 25 silver UPON ARRIVAL!"]


def test_a_customer_with_no_place_on_record_is_summoned_to_where_the_warlock_is():
    """The owner's screenshot, 13 Nov 2026: "SUMMONING Buster Wang TO us!" -- "why is dest us and
    not where we are??". Buster joined without being invited for a place."""
    g = world(TWO_LOCKS)
    g.run('ServiceInviterDB.opts = { marks = false }')
    g.run('UNITS.party3 = { "Buster", "ROGUE", 30, "Orgrimmar" } GROUP["Buster"] = true')
    g.event("CHAT_MSG_SYSTEM", "Buster joins the party.")          # nobody invited him for anything
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    alerts = [m for _, _, m in g.sent() if m.startswith("SUMMONING")]
    assert alerts and alerts[0].startswith("SUMMONING Buster TO THUNDER BLUFF!")
    assert "us" not in alerts[0].split("!")[0].lower().split()


# -- Forever names: first + surname --------------------------------------------------------------
# The owner's /dump on Yeet Lock, 13 Nov 2026: UnitName = "Yeet", "Lock"; GetUnitName(.., true) =
# "Yeet Lock"; UnitFullName = "Yeet", "Lock". Chat sends the whole name.

FOREVER_NAMES = """
function UnitName(u) local x = UNITS[u] if not x then return nil end
  local f, l = x[1]:match("^(%S+) (.+)$") if f then return f, l end return x[1] end
function GetUnitName(u, full) local x = UNITS[u] return x and x[1] end
"""


def test_a_forever_name_is_read_whole():
    g = world({"player": ("Mooveover Onyourleft", "SHAMAN", 30, "Thunder Bluff"),
               "party1": ("Yeet Lock", "WARLOCK", 22, "Thunder Bluff")}, extra=FOREVER_NAMES)
    g.run('ServiceInviterDB.opts = { marks = false }')
    say_trade(g, "Buster Wang", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Buster Wang joins the party.")
    sent = [m for ch, _, m in g.sent() if ch == "PARTY"]
    assert sent == ["Hi Buster Wang! Yeet Lock will summon you to TB. 25 silver. Pay Yeet Lock when you land."]


def test_someone_you_didnt_invite_becomes_a_summon_customer_when_summoned():
    g = world(TWO_LOCKS)
    g.run('UNITS.party3 = { "Buster", "ROGUE", 30, "Orgrimmar" } GROUP["Buster"] = true')
    g.event("CHAT_MSG_SYSTEM", "Buster joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    assert job(g, "Buster", "service") == "summons"
    assert job(g, "Buster", "dest") == "Thunder Bluff"


def test_an_offer_under_our_price_is_not_invited():
    """The owner, 13 Nov 2026: "wtb tb sum 25s" with summons at 35 silver -- "this is below our
    price im good bliind inviting but this should be filtered out"."""
    lock = {"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}
    for text, who, invite in [("wtb tb sum 25s", "Low", False), ("wtb tb sum 35s", "Fair", True),
                              ("wtb tb sum 1g", "Rich", True), ("wtb tb sum", "Blind", True)]:
        g = world(lock, "summons = { price = 35 }")
        say_trade(g, who, text)
        assert (invited(g) == [who]) is invite, text
    g = world(lock, "summons = { price = 35 }")
    say_trade(g, "Low", "wtb tb sum 25s")
    assert any("25 silver" in p and "35 silver" in p for p in g.printed())
