"""The 2026 redesign of the customer window. It is a fixed 600 x 614 and never changes size, so
nothing moves in a fight (the owner, 14 Nov 2026: "the buff should like stay on top so the
screen doesnt shrink while i use it"; mid-fight: "whoa what i cant even close it"). Its cast
buttons are secure, so they only change out of combat."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}


def opened(units=LOCK, services="summons = { price = 35 }", extra=""):
    g = world(units, services, extra='function InCombatLockdown() return INCOMBAT end INCOMBAT = false\n' + extra)
    g.run('ServiceInviterDB.role = "lock" ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()')
    return g


def size(g):
    w = g.eval("ServiceInviterJobs")
    return (w._w if hasattr(w, "_w") else None, g.eval("ServiceInviterJobs:GetHeight()"))


def test_the_window_is_the_same_size_empty_full_and_with_blessings():
    g = opened({"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")},
               "summons = { price = 35 }, blessing = { on = true }")
    assert (g.eval("ServiceInviterJobs:GetWidth()"), g.eval("ServiceInviterJobs:GetHeight()")) == (600, 614)
    for i in range(8):
        say_trade(g, f"Buyer{chr(97 + i)}", "wtb summon to TB")
        g.run("ServiceInviter_Test.Refresh()")
        assert g.eval("ServiceInviterJobs:GetHeight()") == 614
    assert "2 more not shown" in g.eval("ServiceInviterJobs.count:GetText()")
    # a paladin: the blessing button takes its slot and the next-step button narrows; same window
    assert g.eval("ServiceInviterJobs.buffBtn:IsShown()")
    assert g.eval("ServiceInviterNext:GetWidth()") == 600 - 24 - 196 - 8
    assert g.eval("ServiceInviterJobs:GetHeight()") == 614


def test_the_next_step_button_says_the_step_and_is_gold_when_it_is_yours():
    g = opened()
    say_trade(g, "Kaldrok", "wtb summon to TB")
    g.run('ServiceInviter_Test.Jobs.Joined("Kaldrok") ServiceInviter_Test.Refresh()')
    assert g.eval("ServiceInviterNext:GetText()") == "Summon Kaldrok"
    assert g.eval("ServiceInviterJobs.heroVerb:GetText()") == "SUMMON"
    assert g.eval("ServiceInviterJobs.heroName:GetText()") == "Kaldrok"
    assert g.eval("ServiceInviterJobs.heroJob.name") == "Kaldrok"


def test_in_combat_nothing_on_the_window_is_touched():
    g = opened()
    say_trade(g, "Kaldrok", "wtb summon to TB")
    g.run('ServiceInviter_Test.Jobs.Joined("Kaldrok") ServiceInviter_Test.Refresh()')
    before = g.eval("ServiceInviterNext:GetAttribute('macrotext')")
    g.run('INCOMBAT = true ServiceInviter_Test.Jobs.Remove("Kaldrok") ServiceInviter_Test.Refresh()')
    assert g.eval("ServiceInviterNext:GetAttribute('macrotext')") == before   # left alone until the fight ends
    g.run('INCOMBAT = false')
    g.event("PLAYER_REGEN_ENABLED")
    assert g.eval("ServiceInviterNext:GetAttribute('macrotext')") == ""


def test_a_regular_keeps_their_count_on_the_row():
    g = opened()
    g.run('ServiceInviterDB.customers = { Kaldrok = { n = 3, by = { summons = 3 }, worth = 105, first = 1, last = 2, to = {} } }')
    say_trade(g, "Kaldrok", "wtb summon to TB")
    g.run("ServiceInviter_Test.Refresh()")
    assert "3 before" in g.eval("ServiceInviterJobs.rows[1].name:GetText()")
