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
