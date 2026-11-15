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




def test_an_ad_that_shows_up_is_fine():
    g = world(LOCK, "summons = { price = 35 }", extra='function GetChannelList() return 5, "summons", false end')
    g.run('ServiceInviterDB.role = "lock"')
    g.run("ServiceInviter_Test.PostAd()")
    echo(g)
    g.run("CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.AdCheck()")
    assert "didn't show up" not in " ".join(g.printed())
    assert g.eval("(ServiceInviter_Test.AdState())") == "wait"






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
function EditMacro(i, n, icon, body) MACRO_LIST[i].body = body return i end
function GetMacroInfo(i) local m = MACRO_LIST[i] if m then return m.name, "icon", m.body end end'''


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



def test_the_macro_follows_a_rival_price_even_on_a_client_that_wants_the_name_back():
    """The owner, 15 Nov 2026: "the macro does not seem to be updating with the dynamic pricing
    though the whispers are"."""
    strict = MACROS + """
function EditMacro(i, n, icon, body) if n == nil or icon == nil then error("Usage: EditMacro(index, name, icon, body)") end
    MACRO_LIST[i].body = body return i end"""
    g = world(LOCK, "summons = { price = 45, match = true, floor = 30, undercut = 1 }", extra=CHANNELS + "\n" + strict)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.run('SlashCmdList.SERVICEINVITER("macro")')
    assert "45" in g.eval("MACRO_LIST[1].body")
    g.event("CHAT_MSG_CHANNEL", "WTS summons to TB 36s pst", "Rival", "", "1. General - Thunder Bluff", "", "", "", "", "General - Thunder Bluff")
    g.run("ServiceInviter_Test.Tick(1)")
    body = g.eval("MACRO_LIST[1].body")
    assert body.startswith("/1 ") and "35" in body
    assert not any("Couldn't update" in p for p in g.printed())


def test_between_posts_the_macro_says_why_instead_of_nothing():
    """The owner, 15 Nov 2026: "actually the macro just doesnt seem to work at all though it did
    before" -- it had been stuck on its first ad (3.9.17's fix); now it empties between posts."""
    g = world(LOCK, "summons = { price = 35 }", extra='function GetChannelList() return 2, "Trade - City", false end\n' + MACROS)
    g.run('ServiceInviterDB.role = "lock"')
    g.run('SlashCmdList.SERVICEINVITER("macro")')
    body = g.eval("MACRO_LIST[1].body")
    assert body.startswith("/2 ")
    g.event("CHAT_MSG_CHANNEL", body[3:], "Me", "", "2. Trade - City", "", "", "", "", "Trade - City")
    g.run("ServiceInviter_Test.Tick(1)")
    assert g.eval("MACRO_LIST[1].body") == "/run ServiceInviter_AdWhy()"
    g.run("ServiceInviter_AdWhy()")
    said = g.plain()[-1]
    assert "no ad yet: next is [Trade - City] in" in said


def test_a_wait_under_a_minute():
    g = world(LOCK, "summons = { price = 35 }", extra='function GetChannelList() return 2, "Trade - City", false end')
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.adwait = 0.5 ServiceInviter_Test.PostAd()')
    g.run("CLOCK = CLOCK + 29")
    assert g.eval("(ServiceInviter_Test.AdState())") == "wait"
    g.run("CLOCK = CLOCK + 2")
    assert g.eval("(ServiceInviter_Test.AdState())") == "ready"



def test_an_ad_that_never_shows_up_is_reported_every_time_and_never_dropped():
    """The owner, 15 Nov 2026: "stop killing it after 2 attempts - impossible to troubleshoot"."""
    g = world(LOCK, "summons = { price = 35 }", extra='function GetChannelList() return 5, "summons", false end')
    g.run('ServiceInviterDB.role = "lock"')
    for n in range(1, 4):
        g.run("ServiceInviter_Test.PostAd()")
        g.event("CHAT_MSG_CHANNEL_NOTICE_USER", "You are not allowed to speak in this channel")
        g.run("CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.AdCheck()")
        said = " ".join(g.plain())
        assert f"Your ad didn't show up in [summons] ({n} in a row)" in said and "not allowed to speak" in said
        assert g.eval("(ServiceInviter_Test.AdState())") == "ready"        # still in the queue
    assert "last 3 didn't show up" in g.eval("ServiceInviter_Test.Jobs.AdQueueText()")


def test_muted_or_slowed_down_is_said_and_presses_still_go_out():
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.event("CHAT_MSG_SYSTEM", "We have temporarily suspended your chat and mail privileges. Check your email for more details.")
    assert any("chat is muted or suspended" in p for p in g.printed())
    assert press(g).startswith("/1 ")
    g.run("CLOCK = CLOCK + 11")
    g.event("UI_ERROR_MESSAGE", 0, "You are being rate limited.")
    assert any("slowing your chat down" in p for p in g.printed())
    assert press(g).startswith("/2 ")


def test_the_guild_try_counts_when_the_game_sends_the_bar_back_doubled():
    """The owner's screenshot, 15 Nov 2026: "Your ad didn't show up in [Guild] ... The game said:
    Trukt Hunt has joined the raid group." -- with the ad right there in guild chat."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true, adguild = true }')
    m = press(g)
    assert "|| whisper inv" in m                          # doubled: a lone bar is a broken code
    g.event("CHAT_MSG_SYSTEM", "Trukt Hunt has joined the raid group.")
    g.event("CHAT_MSG_GUILD", m[3:].replace("|", "||"), "Me-Forever")
    g.run("CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.AdCheck()")
    said = " ".join(g.plain())
    assert "showed up in guild chat" in said
    assert "didn't show up" not in said


def test_a_raid_join_is_not_the_reason_an_ad_failed():
    g = world(LOCK, "summons = { price = 35 }", extra='function GetChannelList() return 5, "summons", false end')
    g.run('ServiceInviterDB.role = "lock" ServiceInviter_Test.PostAd()')
    g.event("CHAT_MSG_SYSTEM", "Trukt Hunt has joined the raid group.")
    g.run("CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.AdCheck()")
    said = " ".join(g.plain())
    assert "didn't show up" in said and "Trukt Hunt" not in said


def test_every_bar_we_send_is_doubled_or_the_game_drops_the_line():
    """The owner, 15 Nov 2026: "ok the macro is straight up not working, it will not go into guild
    chat no matter how many times i press it ... it's just typing in the game - something we already
    do". Typed, the chat box doubles a "|"; a macro or addon sends a lone one, a broken code, and the
    game drops the whole line without a word."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS + "\n" + MACROS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.run('SlashCmdList.SERVICEINVITER("macro")')
    body = g.eval("MACRO_LIST[1].body")
    assert "|| whisper inv" in body and "| whisper" not in body.replace("||", "")
    g.run("ServiceInviter_Test.PostAd()")
    sent = [m for ch, _, m in g.sent() if ch == "CHANNEL"][-1]
    assert sent.replace("||", "").count("|") == 0
    assert g.eval('ServiceInviter_Test.Jobs.ChatSafe("a || b | c")') == "a || b || c"   # doubled ones stay
    # whispers and party lines too
    g.run('ServiceInviter_Test.Jobs.Send("hi | there", "WHISPER", "Kaldrok")')
    assert g.sent()[-1][2] == "hi || there"



def test_the_ui_button_posts_on_its_own_even_with_an_si_ad_macro():
    """The owner, 15 Nov 2026: "i want to go back to being able to press it from the UI instead of
    making an updating macro"."""
    g = world(LOCK, "summons = { price = 35 }", extra=CHANNELS + "\n" + MACROS)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { general = true }')
    g.run('SlashCmdList.SERVICEINVITER("macro")')
    m = press(g)
    assert m.startswith("/1 ") and "|| whisper inv" in m
    assert g.eval('ServiceInviterAdButton:GetAttribute("macro")') is None
