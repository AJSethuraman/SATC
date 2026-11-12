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
    assert has(lines, "When they join, party chat: Hi Kaldrok! Grimtotem will summon you to TB. 25s. Pay Grimtotem when you land.")
    assert has(lines, "When the summon starts, party chat: SUMMONING Kaldrok! PAY Grimtotem 25 SILVER IN THE TRADE WINDOW ON ARRIVAL!")
    assert has(lines, "When you invite, your chat only: invited Kaldrok")
    nothing_happened(g)


def test_with_no_warlock_it_says_so_and_shows_an_example():
    g = world({"player": ME_ORG})
    lines = preview(g, "Warlock")
    assert has(lines, "Nobody in your group can do summons right now")
    assert has(lines, "Hi Kaldrok! Warlock will summon you to Org. 25s. Pay Warlock when you land.")
    nothing_happened(g)
    # the example warlock is gone afterwards: still nothing on sale
    assert len(g.eval('ServiceInviterCore.OnSale(ServiceInviterDB, ServiceInviter_Test.Group(), "Horde")')) == 0


def test_a_service_not_offered_says_how_to_turn_it_on():
    g = world({"player": ("Me", "ROGUE", 60, "Thunder Bluff")})
    assert has(preview(g, "Rogue"), "lockpicking: not offered. Tick 'We sell lockpicking' to sell it.")


def test_rogue_tab_free_lockpicking():
    g = world({"player": ("Me", "ROGUE", 60, "Thunder Bluff")}, "lockpick = { on = true }")
    assert has(preview(g, "Rogue"), "When they join, party chat: Hi Kaldrok! I'll do lockpicking, come to me in TB. Free, tips welcome.")


def test_invite_off_is_explained():
    g = world({"player": ("Me", "PRIEST", 60, "Thunder Bluff")}, "fort = { on = true }")
    lines = preview(g, "Buffs")
    assert has(lines, "Fortitude: buyers aren't invited (Invite buyers is off)")


def test_mage_tab_shows_each_portal():
    g = world({"player": ME_ORG, "party1": ("Velenne", "MAGE", 60, "Orgrimmar")}, "portals = { on = true, price = 20 }")
    lines = preview(g, "Mage")
    assert has(lines, "Velenne will do a portal to UC, come to Velenne in Org. 20s. Pay Velenne there.")
    assert has(lines, "Velenne will do a portal to TB")


def test_arrival_message_or_why_there_is_none():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    assert has(preview(g, "Warlock"), "When they land: no message (nothing else on offer in TB)")
    g = world({"player": ("Me", "ROGUE", 60, "Thunder Bluff"), "party1": LOCK_TB}, "lockpick = { on = true }")
    assert has(preview(g, "Warlock"), "When they land, party chat: Welcome to TB, Kaldrok! Also here: free lockpicking. Just ask!")


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
    assert has(preview(g, "General"), "Nothing on sale, so nobody is invited.")


def test_advertise_tab_shows_the_ad_its_length_and_when_it_can_go():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    lines = preview(g, "Advertise")
    assert has(lines, "Trade, when you press the key: WTS summons to TB 25s | whisper inv")
    assert has(lines, "35 of 255 letters")
    assert has(lines, "Ready to post in Trade")
    nothing_happened(g)


def test_advertise_with_nothing_to_sell_shows_an_example():
    g = world({"player": ME_ORG})
    lines = preview(g, "Advertise")
    assert has(lines, "No ad right now: nothing to sell")
    assert has(lines, "WTS summons to Org 25s | whisper inv")


def test_paladin_preview_lists_the_words():
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff")}, "blessing = { on = true }")
    lines = preview(g, "Buffs")
    assert has(lines, "\"wisdom\" queues Blessing of Wisdom")
    assert has(lines, "plain \"blessing\" queues Blessing of Might")
    assert has(lines, "Buff button: No buffs waiting")


def test_the_button_prints_to_your_chat_only():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    g.run("ServiceInviter_Test.PrintPreview('Warlock')")
    printed = " ".join(g.printed())
    assert "Preview of the Warlock tab" in printed and "Grimtotem will summon you to TB" in printed
    nothing_happened(g)


def test_slash_preview():
    g = world({"player": ME_ORG, "party1": LOCK_TB})
    g.run('SlashCmdList.SERVICEINVITER("preview warlock")')
    assert "Grimtotem will summon you to TB" in " ".join(g.printed())


def test_every_tab_has_a_preview_button():
    g = world({"player": ME_ORG})
    w = g.eval("ServiceInviter_Test.BuildSetup()")
    assert w.preview is not None
    for tab in ("General", "Warlock", "Mage", "Rogue", "Buffs", "Advertise"):
        assert preview(g, tab)
