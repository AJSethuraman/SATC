"""Where the regulars line went, said every time (the owner, 21 Nov 2026: "when it whispered a
frequent flyer including the price it did not raid announce it")."""
from test_group import world, whisper

BOOK = 'ServiceInviterDB.customers = { Kaldrok = { n = 3, by = { summons = 3 }, worth = 150, first = 1, last = 2, to = {} } }'


def run(extra):
    g = world({"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}, "summons = { price = 50 }", extra=extra)
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.route = { welcome = "whisper" } ' + BOOK)
    whisper(g, "Kaldrok", "wtb summon to TB")
    return g


def test_in_a_raid_as_leader_it_is_a_raid_warning():
    g = run("function IsInRaid() return true end function IsInGroup() return true end function UnitIsGroupLeader() return true end")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok has joined the raid group.")
    assert ("RAID_WARNING", None, "Welcome back {rt3}Kaldrok{rt3}, 4th time with us!") in g.sent()
    assert any("Kaldrok is a regular: said as a raid warning" in l for l in g.plain())


def test_in_a_party_it_says_why_it_was_not_a_raid_warning():
    g = run("function IsInRaid() return false end function IsInGroup() return true end")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert any(ch == "PARTY" and "4th time" in m for ch, _, m in g.sent())
    assert any("a party has no raid warning" in l for l in g.plain())


def test_in_a_raid_without_assist_it_says_so():
    g = run("function IsInRaid() return true end function IsInGroup() return true end "
            "function UnitIsGroupLeader() return false end function UnitIsGroupAssistant() return false end")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok has joined the raid group.")
    assert any(ch == "RAID" and "4th time" in m for ch, _, m in g.sent())
    assert any("needs raid leader or assist" in l for l in g.plain())


def test_a_whispered_welcome_never_says_their_visit_count_even_when_sent_on_joining():
    """The owner, 21 Nov 2026: "i mean it whispered to them it was their 4th time". With no word
    from the game that the invite went out, the welcome waits for them to join; it was built with
    the regulars line inside and whispered."""
    g = world({"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}, "summons = { price = 50 }",
              extra="NO_INVITE_ECHO = true function IsInRaid() return true end function IsInGroup() return true end "
                    "function UnitIsGroupLeader() return true end")
    g.run('ServiceInviterDB.role = "lock" ServiceInviterDB.route = { welcome = "whisper" } ' + BOOK)
    whisper(g, "Kaldrok", "wtb summon to TB")
    assert not any(ch == "WHISPER" for ch, _, _ in g.sent())                 # held: no confirmation yet
    g.event("CHAT_MSG_SYSTEM", "Kaldrok has joined the raid group.")
    whispers = [m for ch, _, m in g.sent() if ch == "WHISPER"]
    assert whispers and "50 silver" in whispers[0]
    assert not any("time with us" in m for m in whispers)
    assert ("RAID_WARNING", None, "Welcome back {rt3}Kaldrok{rt3}, 4th time with us!") in g.sent()
