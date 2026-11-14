"""Test mode. The owner, 14 Nov 2026: "before using this tomorrow i want a dry test to ensure it
would work - i want to see the output of their whisper to me or something as if it would go to the
customer just to me instead"."""
import re
from test_group import world, say_trade

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Yeet Lock", "WARLOCK", 60, "Thunder Bluff")}


def clean(lines):
    return [re.sub(r"\|c[0-9a-fA-F]{8}|\|r", "", p) for p in lines]


def test_a_buyer_is_not_invited_and_every_message_shows_in_your_chat():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false } SlashCmdList.SERVICEINVITER("test")')
    say_trade(g, "Kaldrok Stonehoof", "wtb summon to TB")
    assert list(g.g.INVITED.values()) == [] and g.sent() == []
    out = " ".join(clean(g.printed()))
    assert "TEST would invite Kaldrok Stonehoof" in out and "quoted 35 silver" in out
    assert "1 welcome -> Kaldrok Stonehoof (party chat): Hi Kaldrok Stonehoof! Yeet Lock will summon you to TB. 35 silver." in out
    assert "2 summon starts -> Kaldrok Stonehoof (party chat): SUMMONING Kaldrok Stonehoof TO THUNDER BLUFF!" in out
    assert "4 thanks -> Kaldrok Stonehoof (whisper): Thanks Kaldrok Stonehoof! Enjoy." in out


def test_with_a_name_every_message_is_whispered_to_that_character_instead():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false } SlashCmdList.SERVICEINVITER("test Main Character")')
    say_trade(g, "Kaldrok Stonehoof", "wtb summon to TB")
    sent = g.sent()
    assert sent and all(ch == "WHISPER" and to == "Main Character" for ch, to, _ in sent)
    assert sent[0][2].startswith("[TEST 1 welcome -> Kaldrok Stonehoof, party chat] Hi Kaldrok Stonehoof!")
    assert list(g.g.INVITED.values()) == []


def test_the_quote_uses_that_moments_live_price():
    g = world(LOCK, "summons = { price = 35, match = true, floor = 20, undercut = 5 }")
    g.run('SlashCmdList.SERVICEINVITER("test")')
    say_trade(g, "Rival", "WTS summons to TB 30s")
    say_trade(g, "Kaldrok", "wtb summon to TB")
    assert "quoted 25 silver" in " ".join(clean(g.printed()))


def test_real_events_during_a_test_dont_reach_anyone_either():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.scammers = { Kaldrok = { n = 1 } } SlashCmdList.SERVICEINVITER("test")')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")            # someone else invited him
    assert g.sent() == []
    assert any("TEST (party chat): Heads up: Kaldrok didn't pay last time." in p for p in clean(g.printed()))


def test_test_off_invites_for_real_again():
    g = world(LOCK)
    g.run('SlashCmdList.SERVICEINVITER("test") SlashCmdList.SERVICEINVITER("test off")')
    say_trade(g, "Kaldrok", "wtb summon to TB")
    assert list(g.g.INVITED.values()) == ["Kaldrok"]
