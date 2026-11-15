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
    g.run('SlashCmdList.SERVICEINVITER("prices")')
    out = " ".join(g.plain())
    assert "Summons 20 silver to 35 silver; other sellers: undercut by 5 silver" in out
    assert "TB  25 silver in [Trade - City]: Rival sells at 30 silver" in out
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


def test_the_same_city_in_another_trade_channel_is_your_max_and_says_so():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s pst")          # Trade - City
    g.event("CHAT_MSG_CHANNEL", "WTB summon to TB", "Kaldrok", "", "4. Trade - English 40", "", "", "", "", "Trade - English 40")
    p = g.plain()
    assert any('because [Trade - English 40]' in l for l in p)
    q = [l for l in p if "quoted" in l][-1]
    assert "35 silver in [Trade - English 40]: your max (no other seller for TB in this channel" in q


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
    g.run('SlashCmdList.SERVICEINVITER("prices")')
    assert any("counted: 30 silver, no city named so every city" in l for l in g.plain())


def test_a_summon_ad_with_no_price_is_shown_as_not_counted():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB cheap pst")
    g.run('SlashCmdList.SERVICEINVITER("prices")')
    assert any("not counted: no price in it" in l for l in g.plain())
