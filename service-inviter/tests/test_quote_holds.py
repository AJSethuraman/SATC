"""A customer's price is the one they were quoted, at every step and on every copy (the owner, 15
Nov 2026: "when someone joins and the price changes in the middle of them being there, what happens
to their price? the intention was for someone to be told their quoted price at all points")."""
from test_group import world, say_trade
from test_team import pair, pump

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}
MATCH = "summons = { price = 45, match = true, floor = 30, undercut = 1 }"


def test_a_rival_after_the_invite_doesnt_change_what_they_pay():
    g = world(LOCK, MATCH)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 45
    say_trade(g, "Rival", "WTS summons to TB 36s pst")         # the market moves to 35
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    j = 'ServiceInviter_Test.Jobs.Get("Kaldrok")'
    assert "45 silver" in g.eval(f"ServiceInviter_Test.ArrivalText({j})")
    assert "35" not in g.eval(f"ServiceInviter_Test.ArrivalText({j})")


def test_a_teammates_copy_holds_the_customer_to_the_quote_the_inviter_gave():
    me, bone = pair("summons = { price = 45, match = true, floor = 30, undercut = 1 }")
    # Bone (the point of contact) invites at 45
    say_trade(bone, "Kaldrok", "WTB summon to TB")
    assert bone.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 45
    pump(bone, me, "Bone Charms")
    # my copy has seen a rival, so my own price there is 35
    say_trade(me, "Rival", "WTS summons to TB 36s pst")
    me.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert me.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 45


def test_someone_who_joined_with_no_quote_keeps_the_first_price_worked_out():
    g = world(LOCK, MATCH)
    g.run('local j = ServiceInviter_Test.Jobs.New("Kaldrok", "", "joined", "-") j.service = "summons" j.dest = "Thunder Bluff"')
    # worked out while a Trade line is being handled, so the channel's price applies
    said = ('(function() ServiceInviter_Test.Jobs.priceMarket = "Trade - City" local t = '
            'ServiceInviter_Test.ArrivalText(ServiceInviter_Test.Jobs.Get("Kaldrok")) '
            'ServiceInviter_Test.Jobs.priceMarket = nil return t end)()')
    assert "45 silver" in g.eval(said)
    say_trade(g, "Rival", "WTS summons to TB 36s pst")         # Trade - City moves to 35
    assert "45 silver" in g.eval(said)
