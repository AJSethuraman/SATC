"""The ad goes to every channel you listen in, each on its own, less any you switch off (the
owner, 14 Nov 2026: "this needs to post to anything we watch, or have the option to. like maybe
not general sometimes")."""
from test_group import world

LOCK = {"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}
CHANNELS = '''function GetChannelList() return 1, "General - Thunder Bluff", false, 2, "Trade - English 50", false,
    4, "Trade - English 4", false, 5, "summons", false, 6, "LookingForGroup", false end'''


def posted(g):
    return [to for ch, to, m in g.sent() if ch == "CHANNEL"]


def test_one_press_each_goes_to_the_next_channel_until_all_have_it():
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    for _ in range(5):
        g.run("ServiceInviter_Test.PostAd()")
    assert sorted(posted(g)) == [1, 2, 4, 5]          # General, both Trades, summons; not LFG (not listened to)


def test_a_channel_switched_off_gets_no_ad():
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.run("S = ServiceInviter_Test.BuildSetup() S:Show() S.Load()")
    assert g.eval("S.adChipNames[1]") == "General - Thunder Bluff"
    assert g.eval("S.adChips[1]:GetText()") == "General"
    assert g.eval("S.adChips[2]:GetText()") == "Trade 50"
    g.run("S.adChips[1]:SetChecked(false) S.Save()")
    for _ in range(5):
        g.run("ServiceInviter_Test.PostAd()")
    assert sorted(posted(g)) == [2, 4, 5]
    assert g.eval('ServiceInviterDB.adskip["General - Thunder Bluff"]') is True


def test_the_queue_lists_what_is_ready_and_how_long_the_rest_wait():
    """The owner, 15 Nov 2026: "it lists below it what is ready for posting, then you press it or
    the binding and it post to the next in queue, you can spam it"."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    q = g.eval("ServiceInviter_Test.Jobs.AdQueueText()")
    assert q.count("ready") == 4 and "next" in q
    g.run("ServiceInviter_Test.PostAd() CLOCK = CLOCK + 60")
    q = g.eval("ServiceInviter_Test.Jobs.AdQueueText()")
    lines = q.split("\n")
    assert "ready" in lines[0] and "4:00" in lines[-1]          # the one just posted waits, last
    for _ in range(10):                                          # spam: only the ready ones go
        g.run("ServiceInviter_Test.PostAd()")
    assert len(posted(g)) == 4
    g.run("CLOCK = CLOCK + 241 ServiceInviter_Test.PostAd()")    # its wait is over: the next press posts there
    assert len(posted(g)) == 5


def test_a_channel_the_game_has_switched_off_is_skipped():
    """The owner, 15 Nov 2026: "i seem to have to click the button multiple times for it to send
    anything" -- presses went into channels the game had disabled (Trade outside a city)."""
    g = world(LOCK, "summons = { price = 35 }", extra='''function GetChannelList() return 2, "Trade - City", true,
        4, "Trade - English 4", false end''')
    g.run('ServiceInviterDB.role = "lock"')
    g.run("ServiceInviter_Test.PostAd()")
    assert posted(g) == [4]                    # the first press posts, in a channel that works


def echo(g):
    """The game shows your own ad back to you in the channel."""
    last = [m for ch, to, m in g.sent() if ch == "CHANNEL"][-1]
    g.event("CHAT_MSG_CHANNEL", last, "Me", "", "5. summons", "", "", "", "", "summons")


def test_an_ad_that_never_shows_up_is_reported_and_the_channel_tried_again():
    """The owner, 15 Nov 2026: "i have to press post in trade like 3 times then it works and for
    summons it just doesnt work at all"."""
    g = world(LOCK, "summons = { price = 35 }", extra='function GetChannelList() return 5, "summons", false end')
    g.run('ServiceInviterDB.role = "lock"')
    g.run("ServiceInviter_Test.PostAd()")
    g.event("CHAT_MSG_CHANNEL_NOTICE_USER", "You are not allowed to speak in this channel")
    g.run("CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.AdCheck()")
    said = " ".join(g.printed())
    assert "Your ad didn't show up in summons." in said and "not allowed to speak" in said
    assert g.eval("(ServiceInviter_Test.AdState())") == "ready"            # no wait started
    g.run("ServiceInviter_Test.PostAd() CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.AdCheck()")
    assert "Left out of the queue" in " ".join(g.printed())
    assert g.eval("(ServiceInviter_Test.AdState())") == "off"
    assert "didn't post twice" in g.eval("ServiceInviter_Test.Jobs.AdQueueText()")


def test_an_ad_that_shows_up_is_fine():
    g = world(LOCK, "summons = { price = 35 }", extra='function GetChannelList() return 5, "summons", false end')
    g.run('ServiceInviterDB.role = "lock"')
    g.run("ServiceInviter_Test.PostAd()")
    echo(g)
    g.run("CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.AdCheck()")
    assert "didn't show up" not in " ".join(g.printed())
    assert g.eval("(ServiceInviter_Test.AdState())") == "wait"
