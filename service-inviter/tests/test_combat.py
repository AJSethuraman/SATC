"""The customer window in a fight. It holds the buttons that cast, so the game won't let an addon
hide or move it in combat. The owner, 14 Nov 2026, mid-fight, with four "game blocked" errors on
screen: "whoa what i cant even close it"."""
from test_group import world

ME = ("Me", "WARLOCK", 60, "Orgrimmar")
COMBAT = 'function InCombatLockdown() return INCOMBAT end INCOMBAT = false'


def opened():
    g = world({"player": ME}, "summons = { price = 35 }", extra=COMBAT)
    g.run('SlashCmdList.SERVICEINVITER("")')
    assert g.eval("ServiceInviterJobs:IsShown()")
    return g


def test_closing_in_combat_fades_it_now_and_closes_it_after():
    g = opened()
    g.run("INCOMBAT = true")
    g.run('ServiceInviterJobs._scripts.OnDragStart(ServiceInviterJobs)')   # no StartMoving, no block
    g.run('SlashCmdList.SERVICEINVITER("")')                               # the X does the same
    assert g.eval("ServiceInviterJobs:IsShown()")                          # never Hide() in combat
    assert g.eval("ServiceInviterJobs._alpha") == 0
    assert any("closes when combat ends" in p for p in g.printed())
    g.run("INCOMBAT = false")
    g.event("PLAYER_REGEN_ENABLED")
    assert not g.eval("ServiceInviterJobs:IsShown()")
    assert g.eval("ServiceInviterJobs._alpha") == 1


def test_asking_for_it_back_mid_fight_brings_it_back_and_it_stays():
    g = opened()
    g.run("INCOMBAT = true")
    g.run('SlashCmdList.SERVICEINVITER("")')
    g.run('SlashCmdList.SERVICEINVITER("")')
    assert g.eval("ServiceInviterJobs._alpha") == 1
    g.run("INCOMBAT = false")
    g.event("PLAYER_REGEN_ENABLED")
    assert g.eval("ServiceInviterJobs:IsShown()")


def test_out_of_combat_it_just_closes():
    g = opened()
    g.run('SlashCmdList.SERVICEINVITER("")')
    assert not g.eval("ServiceInviterJobs:IsShown()")
