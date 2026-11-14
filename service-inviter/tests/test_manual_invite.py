"""Invited by hand. The owner, 14 Nov 2026: "if i manual invite somebody how do we inform them in
the welcome / price message". What they said in chat in the last two minutes says what and where;
they get the same welcome and price as anyone the addon invites."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}


def by_hand(g, name):
    g.run(f'C_PartyInfo.InviteUnit("{name}")')


def join(g, name):
    g.run(f'UNITS.party2 = {{ "{name}", "MAGE", 40, "Orgrimmar" }} GROUP["{name}"] = true')
    g.event("CHAT_MSG_SYSTEM", f"{name} joins the party.")


def test_a_buyer_you_invite_by_hand_gets_the_welcome_with_the_price():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { enabled = false, marks = false }')   # the addon invites nobody itself
    say_trade(g, "Kaldrok", "wtb summon to TB")
    assert list(g.g.INVITED.values()) == []
    by_hand(g, "Kaldrok")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").dest') == "Thunder Bluff"
    join(g, "Kaldrok")
    said = [m for _, _, m in g.sent()]
    assert said and "35 silver" in said[-1] and "TB" in said[-1]


def test_someone_who_said_nothing_hears_what_we_sell():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { enabled = false, marks = false }')
    by_hand(g, "Friendo")
    join(g, "Friendo")
    said = [m for _, _, m in g.sent()]
    assert said and "We have summons to TB 35 silver" in said[-1]
