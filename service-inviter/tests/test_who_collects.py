"""Who collects the money is a setting, not the role. Auto-trade and the Trade/Paid
buttons follow it. Before it is set, the lock collects (what the role text always said)."""
import pytest

ARRIVE = '''local J = ServiceInviter_Test.Jobs
J.New("Bob","wtb summon tb","t","Trade") J.Joined("Bob") J.Set("Bob","summoned")
CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()'''


@pytest.mark.parametrize("role, collect, opens_trade", [
    ("helper", None, False),   # default: the lock collects, so the helper never opens trade
    ("lock", None, True),
    ("helper", True, True),
    ("lock", False, False),    # tonight: the lock collected... or not, it is the owner's call
])
def test_auto_trade_follows_who_collects(party, role, collect, opens_trade):
    party.run(f'ServiceInviterDB.role = "{role}"')
    if collect is not None:
        party.run(f"ServiceInviterDB.collect = {'true' if collect else 'false'}")
    party.run(ARRIVE)
    assert (list(party.g.TRADES.values()) != []) == opens_trade


@pytest.mark.parametrize("collect", [True, False])
def test_trade_and_paid_buttons_follow_who_collects(party, collect):
    party.run(f'ServiceInviterDB.role = "helper" ServiceInviterDB.collect = {str(collect).lower()}')
    party.run(ARRIVE + ' ServiceInviter_Test.Refresh()')
    row = party.eval('ServiceInviterJobs.rows[1]')
    assert row.paid._shown is collect
    assert row.trade._shown is collect


def test_the_setup_window_saves_who_gets_paid(party):
    party.run('''local w = ServiceInviter_Test.BuildSetup() w:Show()
        local c = ServiceInviter_Test.SetupChecks() c.pay_me._scripts.OnClick(c.pay_me) w:Hide()''')
    assert party.eval("ServiceInviterDB.payee.mode") == "me"


def test_si_collect_toggles_always_me(game):
    game.eval('SlashCmdList.SERVICEINVITER("collect")')
    assert game.eval("ServiceInviterDB.payee.mode") == "me"
    game.eval('SlashCmdList.SERVICEINVITER("collect")')
    assert game.eval("ServiceInviterDB.payee.mode") == "place"


def test_no_whisper_until_someone_is_named(party):
    party.run('ServiceInviter_Test.Jobs.New("Bob","x","t","Trade") ServiceInviter_Test.Jobs.Joined("Bob")')
    party.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    assert [s for s in party.sent() if s[0] == "WHISPER"] == []
    assert any(s[0] == "PARTY" for s in party.sent())   # control: the alert still went


def test_a_named_whisper_still_goes(party):
    party.run('ServiceInviterDB.whisperto = "Friend"')
    party.run('ServiceInviter_Test.Jobs.New("Bob","x","t","Trade") ServiceInviter_Test.Jobs.Joined("Bob")')
    party.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    assert ("WHISPER", "Friend", "Summoning Bob. Next: nobody") in party.sent()
