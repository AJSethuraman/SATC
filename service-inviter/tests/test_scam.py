"""Didn't pay. The owner, 14 Nov 2026: "add a scam button rather than paid to record them as prior
scammers and publicly say it when they join"."""
from test_group import world, say_trade
from test_steps import lockpick_customer, click, whispers

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}


def chat(g):
    return [m for ch, _, m in g.sent() if ch in ("PARTY", "RAID")]


def test_scam_shows_under_paid_and_records_them_and_removes_them_without_thanks():
    g = lockpick_customer(price="20")
    assert g.eval("ServiceInviterJobs.rows[1].scam._shown") is True
    assert g.eval('ServiceInviterJobs.rows[1].scam:GetAttribute("macrotext")') == "/uninvite Kaldrok"
    click(g, "scam")
    assert g.status("Kaldrok") == "scammed"
    assert list(g.g.KICKED.values()) == ["Kaldrok"]
    assert whispers(g) == []                                       # no thank-you
    e = g.eval('ServiceInviterDB.scammers["Kaldrok"]')
    assert e.n == 1 and e.owed == 20


def test_no_scam_button_on_a_free_service():
    g = lockpick_customer()
    assert g.eval("ServiceInviterJobs.rows[1].scam._shown") is False


def test_they_are_called_out_when_they_join_and_get_no_welcome():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.scammers = { ["Momma Lovesme"] = { n = 1, owed = 35 } }')
    g.event("CHAT_MSG_SYSTEM", "Momma Lovesme joins the party.")
    assert chat(g) == ["Heads up: Momma Lovesme didn't pay last time."]


def test_they_are_never_invited_from_chat():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.scammers = { ["Momma Lovesme"] = { n = 1, owed = 35 } }')
    say_trade(g, "Momma Lovesme", "WTB summon to TB")
    assert list(g.g.INVITED.values()) == []
    assert any("didn't pay last time" in p for p in g.printed())


def test_your_own_words_and_empty_is_quiet():
    g = world(LOCK)
    g.run('ServiceInviterDB.scammers = { Kaldrok = { n = 1 } } ServiceInviterDB.scammsg = "{name} owes us, pay first"')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert chat(g) == ["Kaldrok owes us, pay first"]
    g = world(LOCK)
    g.run('ServiceInviterDB.scammers = { Kaldrok = { n = 1 } } ServiceInviterDB.scammsg = ""')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert chat(g) == []


def test_unscam_clears_them_and_the_list_opens_to_copy():
    g = world(LOCK)
    g.run('ServiceInviterDB.scammers = { ["Momma Lovesme"] = { n = 2, owed = 70, last = 1763000000 } }')
    g.run('SlashCmdList.SERVICEINVITER("scammers")')
    assert "Momma Lovesme: 2 times, owed 70 silver" in g.eval("ServiceInviterCopy.box:GetText()")
    g.run('SlashCmdList.SERVICEINVITER("unscam momma lovesme")')
    assert g.eval('ServiceInviterDB.scammers["Momma Lovesme"]') is None
