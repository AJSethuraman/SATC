"""Only a whisper invites by itself (the owner, 15 Nov 2026: "right now it auto invites from chat
(i do not want that to happen) I want to ONLY offer invites automatically from people who
whisper"). A buyer in a channel gets a row with an Invite button and their quote."""
from test_group import world, say_trade, whisper
from test_team import pair, pump

LOCK = {"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}


def plain_world():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.chanauto = nil')    # the default
    return g


def test_a_buyer_in_trade_is_offered_not_invited():
    g = plain_world()
    say_trade(g, "Kaldrok", "WTB summon to TB")
    assert list(g.g.INVITED.values()) == []
    assert g.status("Kaldrok") == "asked"
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 35
    said = " ".join(g.plain())
    assert "ASKED Kaldrok" in said and "press Invite on their row" in said
    assert not any(ch == "WHISPER" for ch, _, _ in g.sent())                  # nothing said to them yet


def test_a_whisper_invites_by_itself():
    g = plain_world()
    whisper(g, "Kaldrok", "wtb summon to TB")
    assert list(g.g.INVITED.values()) == ["Kaldrok"]
    whisper(g, "Momma", "inv")
    assert "Momma" in list(g.g.INVITED.values())


def test_pressing_invite_on_the_row_invites_and_the_welcome_follows_the_game_saying_so():
    g = plain_world()
    g.run('ServiceInviterDB.route = { welcome = "whisper" }')
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    b = "ServiceInviterJobs.rows[1].reinvite"
    assert g.eval(f"{b}:GetText()") == "Invite" and g.eval(f'{b}:GetAttribute("macrotext")') == "/invite Kaldrok"
    g.run(f"local b = {b} b._scripts.PostClick(b)")                          # the press (the game runs /invite)
    assert g.status("Kaldrok") == "invited"
    g.event("CHAT_MSG_SYSTEM", "You have invited Kaldrok to join your group.")
    assert any(ch == "WHISPER" and to == "Kaldrok" and "35 silver" in m for ch, to, m in g.sent())


def test_asking_again_in_trade_keeps_one_row():
    g = plain_world()
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run("CLOCK = CLOCK + 30")
    say_trade(g, "Kaldrok", "WTB summon to TB pls")
    assert sum(1 for p in g.plain() if "ASKED Kaldrok" in p) == 1
    assert g.status("Kaldrok") == "asked"


def test_the_switch_puts_channel_auto_invites_back():
    g = plain_world()
    g.run("S = ServiceInviter_Test.BuildSetup() S:Show() S.Load() S.checks.chanauto:SetChecked(true) S.Save()")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    assert list(g.g.INVITED.values()) == ["Kaldrok"]


def test_on_a_team_a_channel_buyer_is_offered_on_the_point_of_contacts_list():
    me, bone = pair()
    for g in (me, bone):
        g.run("ServiceInviterDB.chanauto = nil")
    say_trade(me, "Kaldrok", "WTB summon to TB")
    pump(me, bone, "Me")
    assert list(bone.g.INVITED.values()) == []
    assert bone.status("Kaldrok") == "asked"
    assert any("priced by" in p for p in bone.plain())
