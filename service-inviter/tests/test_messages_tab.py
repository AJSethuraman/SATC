"""The Messages tab (the owner, 14 Nov 2026: "make a tab that can be used for the chats only so
it's all in one spot ... Send on invite, Send on entry, Send on arrival"). Each message's Off is
its on/off; an empty pay or "what else is here" box says nothing."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}


def setup(g):
    g.run("S = ServiceInviter_Test.BuildSetup() S:Show() S.Load()")


def pick(g, kind, opt):
    g.run(f'local c = ServiceInviter_Test.SetupChecks().route_{kind}_{opt} c._scripts.OnClick(c) S.Save() S.Load()')


def test_off_beside_a_message_turns_it_off():
    g = world(LOCK, "summons = { price = 35 }")
    setup(g)
    pick(g, "welcome", "off")
    assert g.eval('ServiceInviter_Test.Opt("welcome")') is False
    pick(g, "thanks", "off")
    assert g.eval("ServiceInviterDB.thanks") is False
    pick(g, "alert", "off")
    assert g.eval("ServiceInviterDB.raidalert") is False
    assert g.eval("ServiceInviter_Test.SetupChecks().route_welcome_off:GetChecked()")
    pick(g, "welcome", "whisper")
    assert g.eval('ServiceInviter_Test.Opt("welcome")') is True


def test_empty_arrival_boxes_say_nothing():
    g = world({**LOCK, "party2": ("Kaldrok", "MAGE", 40, "Thunder Bluff")}, "summons = { price = 35 }, blessing = { on = true, price = 10 }")
    setup(g)
    g.run('local b = ServiceInviter_Test.SetupBoxes() b.paymsg:SetText("") b.offermsg:SetText("") S.Save()')
    say_trade(g, "Kaldrok", "wtb summon to TB")
    g.run('local J = ServiceInviter_Test.Jobs J.Joined("Kaldrok") J.Set("Kaldrok", "summoned")')
    assert g.eval('ServiceInviter_Test.ArrivalText(ServiceInviter_Test.Jobs.Get("Kaldrok"))') is None


def test_looking_for_still_counts_and_split_messages_are_always_joined():
    """The owner, 14 Nov 2026: "just assume split messages, no toggle", "no WTB only"."""
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { strictbuy = true, fragments = false, marks = false }')   # old saved settings
    say_trade(g, "Kaldrok", "LF summon to TB")
    assert list(g.g.INVITED.values()) == ["Kaldrok"]
    say_trade(g, "Mirasha", "wtb summon")
    say_trade(g, "Mirasha", "to TB")
    assert "Mirasha" in list(g.g.INVITED.values())
