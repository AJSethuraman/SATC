"""An invite counts once the game says it went out (the owner, 15 Nov 2026: "it sends them the
message saying we have it but it is not actually inviting them but the addon says it is in the
queue"). No word from the game: no welcome whisper, the row goes back to Invite, and your chat
says why."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}


def caught(echo=True, extra=""):
    g = world(LOCK, "summons = { price = 35 }", extra=extra)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.opts = { marks = false } ServiceInviterDB.route = { welcome = "whisper" }')
    if not echo:
        g.run("NO_INVITE_ECHO = true")
    say_trade(g, "Kaldrok", "wtb summon to TB")
    return g


def test_the_welcome_waits_for_the_game_to_say_the_invite_went_out():
    g = caught(echo=True)
    assert [to for ch, to, m in g.sent()] == ["Kaldrok"]
    assert g.status("Kaldrok") == "invited"


def test_an_invite_the_game_never_confirms_goes_back_to_invite_with_the_reason():
    g = caught(echo=False)
    assert g.sent() == []                                        # no whisper to someone not invited
    g.event("UI_ERROR_MESSAGE", 0, "You can't invite players right now.")
    g.run("CLOCK = CLOCK + 5 ServiceInviter_Test.Jobs.InviteCheck()")
    assert g.status("Kaldrok") == "asked"
    said = " ".join(g.printed())
    assert "Kaldrok wasn't invited" in said and "You can't invite players right now." in said


def test_a_suggested_invite_says_so():
    g = caught(echo=False)
    g.event("CHAT_MSG_SYSTEM", "You have suggested that Kaldrok join your group.")
    assert any("suggested to the raid leader, not invited" in p for p in g.printed())
