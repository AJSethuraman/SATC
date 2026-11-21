"""Two warlocks in one city: whoever casts the summon is the one paid. The owner, 14 Nov 2026:
"it can be the lock summoning - let's just make that how it works"."""
from test_group import world, say_trade

UNITS = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"),
         "party1": ("Bone Charms", "WARLOCK", 60, "Thunder Bluff"),
         "party2": ("Yeet Lock", "WARLOCK", 60, "Thunder Bluff")}


def joined(g):
    g.run('ServiceInviterDB.opts = { marks = false } ServiceInviterDB.role = "helper"')
    say_trade(g, "Kaldrok", "wtb summon to TB")
    g.run('UNITS.party3 = { "Kaldrok", "MAGE", 40, "Orgrimmar" }')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")


def test_the_welcome_names_one_and_the_one_who_casts_is_paid():
    g = world(UNITS, "summons = { price = 35 }")
    joined(g)
    welcome = " ".join(m for _, _, m in g.sent())
    assert "Pay Bone Charms" in welcome                     # before anyone casts: the first lock there
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party2", 698, "Ritual of Summoning")')
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").caster') == "Yeet Lock"
    alert = [m for _, _, m in g.sent() if "SUMMONING" in m]
    assert alert and "PAY Yeet Lock" in alert[-1]
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").caster') == "Yeet Lock"   # the first cast holds


def test_a_payee_you_named_is_kept():
    g = world(UNITS, "summons = { price = 35 }")
    g.run('ServiceInviterDB.payee = { mode = "me" }')
    joined(g)
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party2", 698, "Ritual of Summoning")')
    alert = [m for _, _, m in g.sent() if "SUMMONING" in m]
    assert alert and "PAY ME" in alert[-1]
