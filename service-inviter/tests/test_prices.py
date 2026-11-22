"""Following the market. The owner, 14 Nov 2026: "dynamic pricing where we start at a certain
amount and will not go below a certain amount but otherwise we compete with by undercutting
another service by some amount". Same city only, a rival's ad counts for 5 minutes, and someone
already invited keeps the price they were told."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}
MATCH = "summons = { price = 35, match = true, floor = 20, undercut = 5 }"


def price(g, where="Thunder Bluff", market="Trade - City"):
    """Our price for a city in a channel (say_trade posts in "2. Trade - City")."""
    return g.eval(f'(function() ServiceInviter_Test.Jobs.priceMarket = "{market}" local p = ServiceInviterCore.Setting(ServiceInviterDB, "summons", "{where}").price ServiceInviter_Test.Jobs.priceMarket = nil return p end)()')


def test_a_rival_ad_moves_our_price_under_theirs():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s pst")
    assert price(g) == 25
    assert any("TB price in [Trade - City] now 25 silver" in p for p in g.plain())


def test_never_below_the_floor_and_never_above_our_own_price():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 15s")
    assert price(g) == 20
    say_trade(g, "Rival", "WTS summons to TB 80s")
    assert price(g) == 35


def test_after_five_minutes_without_their_ad_it_goes_back_up():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s")
    g.run("CLOCK = CLOCK + 299")
    assert price(g) == 25
    g.run("CLOCK = CLOCK + 2")
    assert price(g) == 35


def test_only_the_same_city():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to UC 20s")
    assert price(g) == 35 and price(g, "Undercity") == 20


def test_no_floor_set_means_it_never_moves():
    g = world(LOCK, "summons = { price = 35, match = true }")
    say_trade(g, "Rival", "WTS summons to TB 20s")
    assert price(g) == 35


def test_switched_off_it_never_moves():
    g = world(LOCK, "summons = { price = 35, floor = 20 }")
    say_trade(g, "Rival", "WTS summons to TB 20s")
    assert price(g) == 35


def test_our_own_people_are_not_rivals():
    g = world(LOCK, MATCH)
    say_trade(g, "Grimtotem", "WTS summons to TB 20s")           # in our group
    g.run('ServiceInviterDB.workers = { Clicky = true }')
    say_trade(g, "Clicky", "WTS summons to TB 20s")              # our worker
    assert price(g) == 35


def test_the_welcome_and_the_invite_use_the_live_price_and_it_sticks():
    g = world(LOCK, MATCH)
    g.run("ServiceInviterDB.opts = { marks = false }")
    say_trade(g, "Rival", "WTS summons to TB 30s")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 25
    say_trade(g, "Rival", "WTS summons to TB 80s")              # the market moved: ours is 35 again
    assert price(g) == 35
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    welcome = [m for ch, _, m in g.sent() if ch == "PARTY"][-1]
    assert "25 silver" in welcome                                  # what he was told when invited


def test_a_buyer_offering_the_live_price_is_not_under_it():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s")
    say_trade(g, "Kaldrok", "WTB summon to TB 25s")
    assert list(g.g.INVITED.values()) == ["Kaldrok"]


def test_the_ad_in_a_channel_shows_that_channels_price():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s")
    state = g.eval("{ ServiceInviter_Test.AdState() }")
    assert state[1] == "ready" and state[5] == "WTS summons to TB 25 silver | whisper inv"


def test_si_prices_lists_rivals():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s")
    g.run('SlashCmdList.SERVICEINVITER("prices text")')
    out = " ".join(g.plain())
    assert "Summons 20 silver to 35 silver; other sellers: undercut by 5 silver" in out
    assert "TB  25 silver in [All channels]: Rival sells at 30 silver in Trade - City" in out
    assert 'Next ad: [Trade - City] "WTS summons to TB 25 silver' in out
    assert '[Trade - City] Rival: "WTS summons to TB 30s" -> counted: 30 silver' in out


# -- where a quote came from (the owner, 15 Nov 2026: "we had dynamic pricing put us at 35 but it
# still seemed to say 45 to people but it's hard to tell where they are coming from - could be
# like trade 2 or 40")

OTHER = ("4", "Trade - English 40", "", "", "", "", "Trade")


def test_the_invite_says_which_channel_and_why_that_price():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s pst")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    said = [p for p in g.plain() if "quoted" in p]
    assert said and "25 silver in [Trade - City]: Rival sells at 30 silver" in said[-1] and "undercut by 5 silver" in said[-1]
    g.run('SlashCmdList.SERVICEINVITER("why Kaldrok")')
    assert any("quoted 25 silver in [Trade - City]" in p for p in g.plain())


def test_another_trade_channel_gets_the_same_price():
    """The owner, 21 Nov 2026: "adjust all of one user's pricing to the same - if i spam in /2 for
    one price i'd do the same in /6 i don't want to be called out"."""
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s pst")          # Trade - City
    g.event("CHAT_MSG_CHANNEL", "WTB summon to TB", "Kaldrok", "", "4. Trade - English 40", "", "", "", "", "Trade - English 40")
    p = g.plain()
    assert any('because [Trade - English 40]' in l for l in p)
    q = [l for l in p if "quoted" in l][-1]
    assert "25 silver in [Trade - English 40]: Rival sells at 30 silver in Trade - City" in q
    assert price(g, market="Trade - English 40") == price(g, market="Trade - City") == 25


def test_a_near_miss_says_the_channel_and_the_price_there():
    g = world(LOCK, MATCH)
    g.event("CHAT_MSG_CHANNEL", "WTB summon to TB 10s", "Cheapo", "", "4. Trade - English 40", "", "", "", "", "Trade - English 40")
    p = g.plain()
    near = [l for l in p if "NEAR MISS" in l]
    assert near and "[Trade - English 40]" in near[-1]
    assert any("price there: 35 silver in [Trade - English 40]: your max" in l for l in p)


def test_held_at_the_min_says_so():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 15s")
    out = g.eval('ServiceInviter_Test.Jobs.PriceWhy("summons", "Thunder Bluff", "Trade - City")')
    out = __import__("re").sub(r"\|c[0-9a-fA-F]{8}|\|r", "", out)
    assert out.startswith("20 silver in [Trade - City]") and "held at your min 20 silver" in out


def test_each_channel_has_its_own_color_and_the_price_color_says_what_set_it():
    """The owner, 15 Nov 2026: "can you color code the SI log tab ... much easier to tell if i know
    which chat it came from quickly"."""
    g = world(LOCK, MATCH)
    a = g.eval('ServiceInviter_Test.Jobs.ChanTag("Trade - English 2")')
    b = g.eval('ServiceInviter_Test.Jobs.ChanTag("Trade - English 40")')
    assert a[:10] != b[:10]                                             # different colors
    assert a == g.eval('ServiceInviter_Test.Jobs.ChanTag("Trade - English 2")')   # the same every time
    W = 'ServiceInviter_Test.Jobs.PriceWhy("summons", "Thunder Bluff", "Trade - City")'
    assert g.eval(W).startswith("|cffffffff35 silver")                  # white: your max
    say_trade(g, "Rival", "WTS summons to TB 30s pst")
    assert g.eval(W).startswith("|cff40ff4025 silver")                  # green: moved for a rival
    say_trade(g, "Rival", "WTS summons to TB 15s pst")
    assert g.eval(W).startswith("|cffffa04020 silver")                  # orange: held at your min
    assert g.eval('ServiceInviter_Test.Jobs.PriceWhy("summons", "Thunder Bluff", nil)').startswith("|cffff6060")   # red: no channel



def test_the_ad_prices_from_the_name_chat_lines_give_its_channel():
    """The owner, 15 Nov 2026: "the macro says 45, my friend says it's quoting people 35". The
    channel list can name a channel differently from its chat lines; rivals are kept under the
    chat line's name, so the ad goes by its channel number."""
    g = world(LOCK, MATCH, extra='function GetChannelList() return 2, "Trade (Services)", false end')
    g.event("CHAT_MSG_CHANNEL", "WTS summons to TB 30s", "Rival", "", "2. Trade (Services) - English 50", "", "", "", 2,
            "Trade (Services)")
    st = g.eval("{ ServiceInviter_Test.AdState() }")
    assert st[1] == "ready" and "25 silver" in st[5]
    g.event("CHAT_MSG_CHANNEL", "WTB summon to TB", "Kaldrok", "", "2. Trade (Services) - English 50", "", "", "", 2,
            "Trade (Services)")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 25        # the ad and the quote agree


def test_a_summon_ad_naming_no_city_counts_for_every_city():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons anywhere 30s pst")
    assert price(g) == 25
    g.run('SlashCmdList.SERVICEINVITER("prices text")')
    assert any("counted: 30 silver, no city named so every city" in l for l in g.plain())


def test_a_summon_ad_with_no_price_is_shown_as_not_counted():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB cheap pst")
    g.run('SlashCmdList.SERVICEINVITER("prices text")')
    assert any("not counted: no price in it" in l for l in g.plain())


def test_the_prices_window_is_a_grid_of_channels_by_cities():
    """The owner, 15 Nov 2026: "this is hard to like see because reading it is annoying - i want an
    easier to read maybe matrix or something"."""
    g = world(LOCK, MATCH, extra='function GetChannelList() return 2, "Trade (Services)", false, 4, "Trade", false end')
    g.event("CHAT_MSG_CHANNEL", "WTS summons to TB 30s", "Rival", "", "2. Trade (Services) - English 50", "", "", "", 2, "Trade (Services)")
    g.event("CHAT_MSG_CHANNEL", "anyone", "Someone", "", "4. Trade - English 4", "", "", "", 4, "Trade")
    g.run('SlashCmdList.SERVICEINVITER("prices")')
    W = "ServiceInviterPrices"
    assert g.eval(f"{W}:IsShown()")
    assert g.eval(f"{W}.colHead[1]:GetText()") == "TB"
    r1 = g.eval(f"{W}.rows[1].label:GetText()")
    assert r1 == "All channels" and g.eval(f"{W}.rows[1].nxt:IsShown()")
    assert "Trade (Services) 50" in g.eval(f"{W}.rows[1].nxt:GetText()")
    c11 = g.eval(f"{W}.rows[1].cells[1]:GetText()")
    assert c11 == "|cff40ff4025s|r"                                   # green: moved for a rival
    assert "Rival sells at 30 silver" in g.eval(f"{W}.rows[1].cells[1].why")
    assert not g.eval(f"{W}.rows[2].band:IsShown()")                  # one price everywhere: one row
    heard = g.eval(f"{W}.heard[1]:GetText()")
    assert "Rival" in heard and "counted: 30 silver" in heard
    assert "Max 35 silver" in g.eval(f"{W}.rule:GetText()") and "Min 20 silver" in g.eval(f"{W}.rule:GetText()")


def test_a_whisper_gets_the_price_the_ad_said():
    """The owner, 21 Nov 2026: "it correctly advertises for 50 but quotes 55 on invite" -- a whisper
    had no channel to price from, so it got the max."""
    g = world({"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}, "summons = { price = 55, match = true, floor = 30, undercut = 1 }")
    g.run('ServiceInviterDB.role = "lock"')
    say_trade(g, "Rival", "WTS summons to TB 51s pst")
    st = g.eval("{ ServiceInviter_Test.AdState() }")
    assert "50 silver" in st[5]
    g.event("CHAT_MSG_WHISPER", "wtb summon to TB", "Kaldrok", "", "", "", "", "", "", "")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 50
    assert any("quoted 50 silver in [Whisper]: Rival sells at 51 silver in Trade - City" in l for l in g.plain())


def test_a_whisper_with_no_rival_anywhere_is_the_max():
    g = world({"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}, "summons = { price = 55, match = true, floor = 30, undercut = 1 }")
    g.run('ServiceInviterDB.role = "lock"')
    g.event("CHAT_MSG_WHISPER", "inv", "Kaldrok", "", "", "", "", "", "", "")
    g.event("CHAT_MSG_WHISPER", "wtb summon to TB", "Momma", "", "", "", "", "", "", "")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Momma").price') == 55


def test_inv_answering_the_ad_gets_the_ads_price():
    g = world({"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}, "summons = { price = 55, match = true, floor = 30, undercut = 1 }")
    g.run('ServiceInviterDB.role = "lock"')
    say_trade(g, "Rival", "WTS summons to TB 51s pst")
    g.event("CHAT_MSG_WHISPER", "inv", "Kaldrok", "", "", "", "", "", "", "")
    j = 'ServiceInviter_Test.Jobs.Get("Kaldrok")'
    assert g.eval(f"{j}.price") == 50 and g.eval(f"{j}.dest") == "Thunder Bluff"
    assert "50 silver" in g.eval(f"ServiceInviter_Test.WelcomeText('Kaldrok', {j}, true)")
