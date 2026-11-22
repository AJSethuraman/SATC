"""A whisper of "inv" invites, no ad needed and no switch (the owner, 15 Nov 2026: "when someone
whispers inv can it just auto invite no ask for confirmation")."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}


def test_a_whispered_inv_invites():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { marks = false }')   # Auto-invite off, no ad
    g.event("CHAT_MSG_WHISPER", "inv", "Kaldrok", "", "", "", "", "", "", "")
    assert list(g.g.INVITED.values()) == ["Kaldrok"]


def test_inv_in_trade_still_needs_auto_invite():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { marks = false }')
    say_trade(g, "Kaldrok", "inv")
    assert list(g.g.INVITED.values()) == []


def test_not_while_selling_is_off():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { marks = false, enabled = false }')
    g.event("CHAT_MSG_WHISPER", "inv", "Kaldrok", "", "", "", "", "", "", "")
    assert list(g.g.INVITED.values()) == []
