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
    assert sent == ["Hi Mirasha! Ashfel will summon you to UC. 25s. Pay Ashfel when you land."]


def test_the_ad_lists_both_places():
    g = world(TWO_LOCKS)
    g.run("ServiceInviter_Test.PostAd()")
    assert [m for ch, _, m in g.sent() if ch == "CHANNEL"] == ["WTS summons to TB/UC 25s | whisper inv"]


def test_two_warlocks_in_one_place_are_one_offer():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
               "party2": ("Ashfel", "WARLOCK", 60, "Thunder Bluff")})
    g.run("ServiceInviter_Test.PostAd()")
    assert [m for ch, _, m in g.sent() if ch == "CHANNEL"] == ["WTS summons to TB 25s | whisper inv"]


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
    assert sent == ["Hi Kaldrok! Grimtotem will summon you to TB. 25s. Pay Grimtotem when you land."]


def test_arrival_offers_what_is_there():
    g = world({"player": ("Me", "ROGUE", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")},
              "lockpick = { on = true, invite = false }")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run('''local J = ServiceInviter_Test.Jobs J.Joined("Kaldrok") J.Set("Kaldrok", "summoned")
             CLOCK = CLOCK + 41 ServiceInviter_Test.CheckArrivals()''')  # no unit to see: 40s fallback
    sent = [m for ch, _, m in g.sent() if ch == "PARTY"]
    assert "Welcome to TB, Kaldrok! Also here: free lockpicking. Just ask!" in sent


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
    assert chan == [("CHANNEL", 2, "WTS summons to TB 25s | whisper inv")]
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
    assert labels == ["Same as General tab", "Me (Me)",
                      "Grimtotem  (Thunder Bluff)", "Ashfel  (Undercity)"]
    g.run("ServiceInviterPicker.buttons[4]._scripts.OnClick()")
    assert g.eval("BOX:GetText()") == "Ashfel"


def test_warlock_tab_says_where_each_warlock_summons_to():
    g = world({"player": ME_ORG_SHAMAN, "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
               "party2": ("Ashfel", "WARLOCK", 60, None)})
    g.run("SETUP = ServiceInviter_Test.BuildSetup() SETUP:Show() SETUP.Refresh()")
    assert g.eval("SETUP.locks:GetText()") == "Grimtotem: Thunder Bluff\nAshfel: where? (the game didn't say)"


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
    assert alerts == ["SUMMONING Mirasha! PAY Ashfel 25 SILVER IN THE TRADE WINDOW ON ARRIVAL!"]
    assert g.status("Mirasha") in ("summoned", "arrived")
    assert g.status("Kaldrok") == "joined"


def test_payee_pick_list_alone_says_where_party_members_go():
    """The owner, seeing it alone: "wtf does this mean". It has a title and says what's missing."""
    g = world({"player": ME_ORG_SHAMAN})
    g.run('''SETUP = ServiceInviter_Test.BuildSetup() SETUP:Show()
             ServiceInviter_Test.ShowPicker(ServiceInviter_Test.SetupBoxes().svc_summons_payee, true, "Who gets paid for summons?")''')
    assert g.eval("ServiceInviterPicker.title:GetText()") == "Who gets paid for summons?"
    assert g.eval("ServiceInviterPicker.note:GetText()") == "Party and raid members show up here."
    assert g.eval("ServiceInviterPicker.sub:GetText()") == "General tab says: whoever is where they land"
