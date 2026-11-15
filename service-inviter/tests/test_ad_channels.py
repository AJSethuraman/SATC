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


def test_muted_turns_ads_off_until_you_log_in_again():
    """The owner, 15 Nov 2026: "if i use the addon to try and post it blanks twice, third time it
    just says rate limited after which i type immediately and it is still saying rate limited not
    muted". Once the game says muted, no press sends anything."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.event("CHAT_MSG_SYSTEM", "You are muted.")
    for _ in range(5):
        g.run("ServiceInviter_Test.PostAd()")
    assert posted(g) == []
    assert any("chat is suspended or muted" in p for p in g.printed())
    assert sum("chat is suspended or muted" in p for p in g.printed()) == 1      # said once, not every press


def test_slowed_down_by_the_game_means_no_ad_for_a_minute():
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.event("UI_ERROR_MESSAGE", 0, "You are being rate limited.")
    g.run("ServiceInviter_Test.PostAd()")
    assert posted(g) == []
    g.run("CLOCK = CLOCK + 61 ServiceInviter_Test.PostAd()")
    assert len(posted(g)) == 1


def test_unmuted_is_not_muted():
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.event("CHAT_MSG_SYSTEM", "You have been unmuted.")
    g.run("ServiceInviter_Test.PostAd()")
    assert len(posted(g)) == 1


def press(g, button="ServiceInviterAdButton"):
    """A key press or click: PreClick runs, then the game runs the button's macro."""
    g.run(f'{button}:GetScript("PreClick")({button}) MACROS_RUN = MACROS_RUN or {{}} '
          f'MACROS_RUN[#MACROS_RUN + 1] = {button}:GetAttribute("macrotext")')
    return g.eval("MACROS_RUN[#MACROS_RUN]")


def test_the_ad_button_is_a_macro_like_your_own():
    """The owner, 15 Nov 2026: "the trade thing is still happening - what gets me is a regular
    macro can do this". The press runs /<channel> <ad>, not the addon's own chat call."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    assert g.eval('ServiceInviterAdButton:GetAttribute("type")') == "macro"
    first = press(g)
    assert first.startswith("/1 ") and "35" in first
    assert posted(g) == []                                   # no SendChatMessage
    second = press(g)
    assert second.startswith("/2 ")                          # next channel in the queue
    for _ in range(3):
        press(g)
    assert press(g) == ""                                    # all four posted: nothing until the wait is over
    assert any("next ad in" in p for p in g.printed())


def test_the_main_window_and_setup_buttons_are_macros_too():
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.run("ServiceInviter_Test.Refresh() S = ServiceInviter_Test.BuildSetup() S:Show() S.Load() W = ServiceInviterJobs.adBtn P2 = S.adpost")
    assert press(g, "W").startswith("/1 ")
    assert press(g, "P2").startswith("/2 ")


def test_muted_means_the_button_runs_nothing():
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.event("CHAT_MSG_SYSTEM", "You are muted.")
    assert press(g) == ""


def test_the_game_line_for_a_suspended_chat_turns_ads_off():
    """The owner's screenshot, 15 Nov 2026."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.event("CHAT_MSG_SYSTEM", "We have temporarily suspended your chat and mail privileges. Check your email for more details.")
    assert press(g) == ""


def test_the_macro_runs_on_the_half_of_the_press_the_game_uses():
    """Key-down or key-up: the queue moves once per press, on the half the game runs the macro on."""
    for on_down in (True, False):
        g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
        g.run(f'ServiceInviterDB.role = "lock" ServiceInviterDB.opts = {{ general = true }} '
              f'function GetCVarBool(k) return {"true" if on_down else "false"} end')
        g.run('local b = ServiceInviterAdButton local pre = b:GetScript("PreClick") GOT = {} '
              'for _ = 1, 2 do for _, d in ipairs({ true, false }) do pre(b, "LeftButton", d) '
              'if d == GetCVarBool() then GOT[#GOT + 1] = b:GetAttribute("macrotext") end end end')
        assert g.eval("GOT[1]").startswith("/1 ")
        assert g.eval("GOT[2]").startswith("/2 ")       # one channel per press, not two


def test_try_it_in_guild():
    """The owner, 15 Nov 2026: "ok prove this works by letting me post it in guild"."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.run("S = ServiceInviter_Test.BuildSetup() S:Show() S.Load() S.checks.adguild:SetChecked(true) S.Save()")
    m = press(g)
    assert m.startswith("/g ") and "35" in m
    assert press(g).startswith("/g ")                     # no wait between tries
    g.event("CHAT_MSG_GUILD", m[3:], "Me")
    assert any("showed up in guild chat" in p for p in g.printed())
    g.run("CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.AdCheck()")
    assert not any("didn't show up" in p for p in g.printed())
    assert g.eval("ServiceInviter_Test.Stats().ads or 0") == 0   # a try isn't an ad
    g.run("S.checks.adguild:SetChecked(false) S.Save()")
    assert press(g).startswith("/1 ")


MACROS = '''MACRO_LIST = {}
function GetMacroIndexByName(n) for i, m in ipairs(MACRO_LIST) do if m.name == n then return i end end return 0 end
function CreateMacro(n, icon, body, perChar) MACRO_LIST[#MACRO_LIST + 1] = { name = n, body = body, char = perChar } return #MACRO_LIST end
function EditMacro(i, n, icon, body) MACRO_LIST[i].body = body return i end'''


def test_the_si_ad_macro_holds_the_next_ad_and_moves_on_when_it_posts():
    """The owner, 15 Nov 2026: "yeah nothing it is not working", of the button, and earlier "a
    regular macro can do this". So the addon writes the ad into a real macro of yours."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS + "\n" + MACROS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.run('SlashCmdList.SERVICEINVITER("macro")')
    assert g.eval("#MACRO_LIST") == 1 and g.eval("MACRO_LIST[1].name") == "SI Ad"
    body = g.eval("MACRO_LIST[1].body")
    assert body.startswith("/1 ") and "35" in body
    assert any("Made a macro called" in p for p in g.printed())
    # you press it: the game posts it, and your line shows up in General
    g.event("CHAT_MSG_CHANNEL", body[3:], "Me", "", "1. General - Thunder Bluff", "", "", "", "", "General - Thunder Bluff")
    g.run("ServiceInviter_Test.Tick(1)")
    assert g.eval("MACRO_LIST[1].body").startswith("/2 ")   # next channel
    assert g.eval("ServiceInviter_Test.Stats().ads") == 1
    g.run("ServiceInviter_Test.Tick(1)")
    assert g.eval("#MACRO_LIST") == 1                        # made once, then only edited


def test_the_macro_is_left_alone_until_you_ask_for_it():
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS + "\n" + MACROS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.run("ServiceInviter_Test.Tick(1)")
    assert g.eval("#MACRO_LIST") == 0
