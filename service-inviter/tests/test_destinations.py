"""What a ticked box covers. The owner, 12 Nov 2026: a summon gets you "from anywhere", so it
covers port requests to that place too; port-only means a mage, who cannot summon. And a request
that names no place is not assumed to be Thunder Bluff."""
import pytest


def opts(game, **kv):
    body = ", ".join(f"{k} = {str(v).lower()}" for k, v in kv.items())
    game.run(f"ServiceInviterDB.opts = {{ {body} }}")


def test_summoning_to_a_place_takes_port_requests_for_it(game):
    ok, why = game.evaluate("WTB port to TB")          # defaults: summon to TB ticked, port to TB not
    assert ok, why


def test_summoning_to_a_place_still_takes_summon_requests(game):
    ok, why = game.evaluate("WTB summon to TB")
    assert ok, why


def test_port_only_takes_port_requests(game):
    opts(game, sum_tb=False, port_org=True)
    ok, why = game.evaluate("wtb port to org")
    assert ok, why


def test_port_only_does_not_take_summon_requests(game):
    """A mage cannot fetch someone from wherever they are."""
    opts(game, sum_tb=False, port_org=True)
    ok, why = game.evaluate("wtb summon to org")
    assert not ok, why


def test_a_summon_to_one_place_does_not_take_requests_for_another(game):
    ok, why = game.evaluate("WTB port to UC")
    assert not ok, why


@pytest.mark.parametrize("saved", ["", "nodest = true"])
def test_no_place_named_is_never_invited(game, saved):
    """The owner, 12 Nov 2026: "just delete it like we would never assume". A tick saved by
    an older version must do nothing either."""
    if saved:
        opts(game, nodest=True, sum_uc=True)
    ok, why = game.evaluate("WTB summon")
    assert not ok, why


def test_there_is_no_option_for_it(game):
    assert game.eval('ServiceInviter_Test.SetupChecks().nodest') is None
    from conftest import ADDON
    assert "nodest" not in ADDON.read_text()


@pytest.mark.parametrize("collect", [False, True])
def test_auto_trade_box_is_greyed_out_unless_you_collect(game, collect):
    game.run(f'ServiceInviterDB.collect = {str(collect).lower()} ServiceInviter_Test.BuildSetup():Show()')
    disabled = game.eval('rawget(ServiceInviter_Test.SetupChecks().autotrade, "_disabled") == true')
    assert disabled is (not collect)


def test_ticking_collect_ungreys_it_straight_away(game):
    game.run('ServiceInviterDB.collect = false ServiceInviter_Test.BuildSetup():Show()')
    game.run('''local c = ServiceInviter_Test.SetupChecks()
        c.collect:SetChecked(true) c.collect._scripts.OnClick(c.collect)''')
    assert game.eval('rawget(ServiceInviter_Test.SetupChecks().autotrade, "_disabled") == true') is False
