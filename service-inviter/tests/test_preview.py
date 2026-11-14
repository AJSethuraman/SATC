"""Preview: a button on every setup tab that prints what the messages will look like, in your
own chat window only. The owner, 12 Nov 2026: "i should be able to press debug buttons in each
panel for things like seeing what the message should look like and stuff".

A preview runs the same code that sends the real messages, so what it shows is what goes out.
It sends nothing, invites nobody and queues nothing."""
import re

from test_group import world

ME_ORG = ("Me", "SHAMAN", 60, "Orgrimmar")
LOCK_TB = ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")


def preview(g, tab):
    lines = g.eval(f'ServiceInviter_Test.Preview("{tab}")')
    out = [lines[i] for i in range(1, len(lines) + 1)]
    return [re.sub(r"\|c[0-9a-fA-F]{8}|\|r|\|T[^|]*\|t", "", s) for s in out]


def has(lines, text):
    return any(text in s for s in lines)


def nothing_happened(g):
    assert g.sent() == []
    assert list(g.g.INVITED.values()) == []
    assert g.eval("ServiceInviter_Test.Jobs.All()[1]") is None


def test_warlock_tab_shows_the_welcome_and_the_raid_alert_for_the_real_warlock():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    lines = preview(g, "Warlock")
    assert has(lines, "When they join, party chat: Hi Kaldrok! Grimtotem will summon you to TB. 25 silver. Pay Grimtotem when you land.")
    assert has(lines, "When the summon starts, party chat: SUMMONING Kaldrok TO THUNDER BLUFF! PAY Grimtotem 25 silver IN THE TRADE WINDOW ON ARRIVAL!")
    assert has(lines, "When you invite, your chat only: invited Kaldrok")
    nothing_happened(g)


def test_with_no_warlock_it_says_so_and_shows_an_example():
    g = world({"player": ME_ORG})
    lines = preview(g, "Warlock")
    assert has(lines, "Nobody in your group can do summons right now")
    assert has(lines, "Hi Kaldrok! Warlock will summon you to Org. 25 silver. Pay Warlock when you land.")
    nothing_happened(g)
    # the example warlock is gone afterwards: still nothing on sale
    assert len(g.eval('ServiceInviterCore.OnSale(ServiceInviterDB, ServiceInviter_Test.Group(), "Horde")')) == 0


def test_invite_off_is_explained():
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff")}, "blessing = { on = true }")
    lines = preview(g, "Paladin")
    assert has(lines, "blessings: buyers aren't invited (Invite buyers is off)")


def test_arrival_message_or_why_there_is_none():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    assert has(preview(g, "Warlock"), "When they land: no message (nothing else on offer in TB)")
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": LOCK_TB}, "blessing = { on = true }")
    assert has(preview(g, "Warlock"), "When they land, party chat: Welcome to TB, Kaldrok! Also here: free blessings. Just ask!")


def test_whisper_line_when_someone_is_set():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    g.run('ServiceInviterDB.whisperto = "Grimtotem"')
    assert has(preview(g, "Warlock"), "When the summon starts, whisper to Grimtotem: Summoning Kaldrok. Next: nobody")


def test_general_tab_lists_whats_on_sale_and_each_welcome():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    lines = preview(g, "General")
    assert has(lines, "On sale now: summons to TB (Grimtotem)")
    assert has(lines, "Hi Kaldrok! Grimtotem will summon you to TB.")


def test_general_tab_with_nothing_on_sale():
    g = world({"player": ME_ORG})
    assert has(preview(g, "General"), "Nothing on sale right now, so nobody is invited.")


def test_advertise_tab_shows_the_ad_its_length_and_when_it_can_go():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    lines = preview(g, "Advertise")
    assert has(lines, "Trade, when you press the key: WTS summons to TB 25 silver | whisper inv")
    assert has(lines, "41 of 255 letters")
    assert has(lines, "Ready to post in Trade")
    nothing_happened(g)


def test_advertise_with_nothing_to_sell_shows_an_example():
    g = world({"player": ME_ORG})
    lines = preview(g, "Advertise")
    assert has(lines, "No ad right now: nothing to sell")
    assert has(lines, "WTS summons to Org 25 silver | whisper inv")


def test_paladin_preview_lists_the_words():
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff")}, "blessing = { on = true }")
    lines = preview(g, "Buffs")
    assert has(lines, "\"wisdom\" queues Blessing of Wisdom")
    assert has(lines, "plain \"blessing\" queues Blessing of Might")
    assert has(lines, "Buff button: No buffs waiting")


def test_the_button_prints_to_your_chat_only():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    g.run("ServiceInviter_Test.PrintPreview('Warlock')")
    printed = re.sub(r"\|T[^|]*\|t", "", " ".join(g.printed()))   # icons draw as pictures here
    assert "Preview of the Warlock tab" in printed and "Grimtotem will summon you to TB" in printed
    nothing_happened(g)


def test_slash_preview():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    g.run('SlashCmdList.SERVICEINVITER("preview warlock")')
    assert "Grimtotem will summon you to TB" in re.sub(r"\|T[^|]*\|t", "", " ".join(g.printed()))


def test_every_tab_has_a_preview_button():
    g = world({"player": ME_ORG})
    w = g.eval("ServiceInviter_Test.BuildSetup()")
    assert w.preview is not None
    for tab in ("General", "Warlock", "Paladin", "Advertise", "Team"):
        assert preview(g, tab)


def test_price_reads_the_same_in_the_welcome_and_the_summon_alert():
    """The owner, 12 Nov 2026: "why does price say 30s on one and 30 silver on the other"."""
    g = world({"player": ME_ORG, "party1": LOCK_TB}, "summons = { price = 30 }")
    g.run('ServiceInviterDB.welcomemsg = "THE COST IS {price}." ServiceInviterDB.alertmsg = "PAY {payee} {price}!"')
    lines = preview(g, "Warlock")
    assert has(lines, "THE COST IS 30 silver.") and has(lines, "PAY Grimtotem 30 silver!")
    g.run("ServiceInviterDB.services.summons.price = 150")
    lines = preview(g, "Warlock")
    assert has(lines, "THE COST IS 1 gold 50 silver.") and has(lines, "PAY Grimtotem 1 gold 50 silver!")
    g.run("ServiceInviterDB.services.summons.price = false")
    lines = preview(g, "Warlock")
    assert has(lines, "THE COST IS free.") and has(lines, "PAY Grimtotem free!")


def test_preview_shows_how_a_regular_is_welcomed():
    """The owner, 13 Nov 2026, on the regulars line: "HOW CAN I TEST IT"."""
    g = world({"player": ME_ORG, "party1": LOCK_TB}, "summons = { price = 35 }")
    g.run('''ServiceInviterDB.opts = { marks = false }
        ServiceInviterDB.welcomemsg = "THE COST IS {price} AND WE WILL SUMMON YOU SOON!"
        ServiceInviterDB.loyaltymsg = "HEY FREQUENT FLYER! This is your {visits} time with us!"''')
    lines = preview(g, "Warlock")
    assert has(lines, "When they join, party chat: THE COST IS 35 silver AND WE WILL SUMMON YOU SOON!")
    assert has(lines, "When a regular joins (4th visit), party chat: THE COST IS 35 silver AND WE WILL SUMMON YOU SOON! HEY FREQUENT FLYER! This is your 4th time with us!")
    assert g.eval("ServiceInviterDB.customers") is None          # nothing was recorded


def test_general_alone_still_shows_your_welcome_and_the_regulars_line():
    """The owner's screenshot, 13 Nov 2026: alone, Preview on General printed only "Nothing on
    sale" every click, never their own welcome."""
    g = world({"player": ME_ORG}, "summons = { price = 35 }")
    g.run('''ServiceInviterDB.opts = { marks = false }
        ServiceInviterDB.welcomemsg = "Hi {name}! Your {service} is {price}. We will summon you soon!"
        ServiceInviterDB.loyaltymsg = "WELCOME BACK YOU FREQUENT FLYER!! This is your {visits} time"''')
    lines = preview(g, "General")
    assert has(lines, "Nothing on sale right now")
    assert has(lines, "pretends a level 60 warlock is with you in Org")
    assert has(lines, "When they join, party chat: Hi Kaldrok! Your summons is 35 silver. We will summon you soon!")
    assert has(lines, "WELCOME BACK YOU FREQUENT FLYER!! This is your 4th time")
    nothing_happened(g)


def test_preview_says_when_it_is_stopped():
    g = world({"player": ME_ORG})
    g.run('SlashCmdList.SERVICEINVITER("stop")')
    assert has(preview(g, "General"), "Stopped (/si stop)")
