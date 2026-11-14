"""How soon the same buyer can be invited again, set on the General tab in seconds (the owner,
14 Nov 2026: "let's make re-invite setting adjustable in UI as well", then "re-invite should be
in seconds")."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}


def invites(g):
    return list(g.g.INVITED.values()).count("Kaldrok")


def test_the_box_sets_it_in_seconds_and_it_holds():
    g = world(LOCK, "summons = { price = 35 }")
    g.run("ServiceInviter_Test.BuildSetup().Load()")
    assert g.eval("ServiceInviter_Test.SetupBoxes().cooldown:GetText()") == "180"   # the default: 3 minutes
    g.run('local w = ServiceInviter_Test.BuildSetup() w.boxes.cooldown:SetText("600") w.Save()')
    assert g.eval("ServiceInviterDB.cooldown") == 600
    say_trade(g, "Kaldrok", "wtb summon to TB")
    g.run('ServiceInviter_Test.Jobs.Remove("Kaldrok") CLOCK = CLOCK + 300')
    say_trade(g, "Kaldrok", "wtb summon to TB")                   # 5 minutes on: not again
    assert invites(g) == 1
    g.run("CLOCK = CLOCK + 360")
    say_trade(g, "Kaldrok", "wtb summon to TB")                   # 11 minutes on: again
    assert invites(g) == 2
