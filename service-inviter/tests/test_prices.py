"""Following the market. The owner, 14 Nov 2026: "dynamic pricing where we start at a certain
amount and will not go below a certain amount but otherwise we compete with by undercutting
another service by some amount". Same city only, a rival's ad counts for 5 minutes, and someone
already invited keeps the price they were told."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}
MATCH = "summons = { price = 35, match = true, floor = 20, undercut = 5 }"


def price(g, where="Thunder Bluff"):
    return g.eval(f'ServiceInviterCore.Setting(ServiceInviterDB, "summons", "{where}").price')


def test_a_rival_ad_moves_our_price_under_theirs():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s pst")
    assert price(g) == 25
    assert any("TB price now 25 silver" in p for p in g.printed())


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


def test_the_ad_shows_the_live_price():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s")
    assert "summons to TB 25 silver" in g.eval("ServiceInviter_Test.AdState()") or \
        "25 silver" in (g.eval('ServiceInviterCore.BuildAd(ServiceInviterDB, ServiceInviter_Test.Group(), "Horde", "{services}")') or "")


def test_si_prices_lists_rivals():
    g = world(LOCK, MATCH)
    say_trade(g, "Rival", "WTS summons to TB 30s")
    g.run('SlashCmdList.SERVICEINVITER("prices")')
    out = " ".join(g.printed())
    assert "undercut by 5 silver, never below 20 silver" in out and "TB: Rival at 30 silver" in out and "yours 25 silver" in out
