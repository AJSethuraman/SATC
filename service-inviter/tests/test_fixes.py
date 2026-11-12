"""One test per bug found in v1.4.0, each failing against that version."""
import pytest


# -- Paid ---------------------------------------------------------------------

def _arrived(party):
    party.run('''local J = ServiceInviter_Test.Jobs
        J.New("Bob","wtb summon tb","t","Trade") J.Joined("Bob") J.Set("Bob","summoned") J.Set("Bob","arrived")
        UNITNAMES.NPC = "Bob"''')


def test_a_cancelled_trade_is_not_marked_paid(party):
    """Both accept at 25s, Bob changes the money (accepts reset), trade cancelled."""
    _arrived(party)
    party.event("TRADE_SHOW")
    party.g.TRADEMONEY = 2500
    party.event("TRADE_ACCEPT_UPDATE", 1, 1)
    party.g.TRADEMONEY = 0
    party.event("TRADE_ACCEPT_UPDATE", 0, 0)
    party.event("TRADE_CLOSED")
    assert party.status("Bob") == "arrived"
    assert party.eval("ServiceInviter_Test.Stats().paid") == 0


def test_a_completed_trade_is_still_marked_paid(party):
    """The control: without this, never marking anyone Paid would pass the test above."""
    _arrived(party)
    party.event("TRADE_SHOW")
    party.event("TRADE_ACCEPT_UPDATE", 1, 0)
    party.g.TRADEMONEY = 2500
    party.event("TRADE_ACCEPT_UPDATE", 1, 1)
    party.event("TRADE_CLOSED")
    assert party.status("Bob") == "paid"
    assert party.eval("ServiceInviter_Test.Stats().silver") == 25


# -- Who gets invited -----------------------------------------------------------

@pytest.mark.parametrize("message", [
    "WTB summon to TB will tip",
    "wtb summon tb, tips",
    "WTB summon to TB for guild group",
    "buying summ to tb, tip on arrival",
])
def test_buyers_who_mention_a_tip_or_their_guild_are_invited(game, message):
    ok, why = game.evaluate(message)
    assert ok, why


@pytest.mark.parametrize("message", [
    "summons to TB, tips appreciated",
    "need summon tb, tips welcome",          # no WTB/buying word: still treated as an ad
    "LF guild, need summon to tb tips",
    "WTS summons to TB, tips",
])
def test_ads_that_mention_tips_or_guild_are_still_skipped(game, message):
    ok, why = game.evaluate(message)
    assert not ok, why


def test_the_built_in_selftest_still_passes(game):
    game.eval('SlashCmdList.SERVICEINVITER("selftest")')
    assert any("0 failed" in line for line in game.printed()), [l for l in game.printed() if "FAIL" in l]


def test_links_in_chat_do_not_leak_their_payload_into_matching(game):
    norm = game.eval('ServiceInviter_Test.Norm("WTB |cff71d5ff|Hspell:698|h[Ritual of Summoning]|h|r to TB")')
    assert norm == " wtb ritual of summoning to tb "


# -- The summon alert -------------------------------------------------------------

def _waiting(party):
    party.run('ServiceInviter_Test.Jobs.New("Bob","wtb summon tb","t","Trade") ServiceInviter_Test.Jobs.Joined("Bob")')


def test_ritual_of_doom_is_not_a_summon(party):
    _waiting(party)
    party.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 18540, "Ritual of Doom")')
    assert party.sent() == []
    assert party.status("Bob") == "joined"


def test_ritual_of_summoning_still_is(party):
    """The control for the test above."""
    _waiting(party)
    party.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    assert any(ch == "PARTY" for ch, _, _ in party.sent())
    assert party.status("Bob") in ("summoned", "arrived")


# -- Buttons and commands -----------------------------------------------------------

def test_summon_button_keeps_accented_letters_in_the_name(game):
    game.run('''ServiceInviterDB.role = "lock"
        ServiceInviter_Test.Jobs.New("Thrálla","wtb summon tb","t","Trade") ServiceInviter_Test.Jobs.Joined("Thrálla")
        ServiceInviter_Test.Refresh()''')
    macro = game.eval('ServiceInviterJobs.rows[1].summon:GetAttribute("macrotext")')
    assert macro.startswith("/target Thrálla\n"), macro


@pytest.mark.parametrize("typed, silver", [("1.5g", 150), ("1g 25s", 125), ("25", 25), ("2g", 200), ("0.25g", 25)])
def test_price_command(game, typed, silver):
    game.eval(f'SlashCmdList.SERVICEINVITER("price {typed}")')
    assert game.eval('ServiceInviterCore.Setting(ServiceInviterDB, "summons").price') == silver


def test_selftest_points_at_this_addons_command(game):
    game.eval('SlashCmdList.SERVICEINVITER("selftest")')
    assert not any("/ti" in line for line in game.printed())


def test_the_header_does_not_claim_it_never_chats():
    from conftest import ADDON
    assert "Sends NO chat or whispers" not in ADDON.read_text()


def test_keyword_invites_still_skip_guild_and_tip_lines(game):
    """'guild' left the hard seller list; the short 'inv' keyword path must not start inviting 'guild inv'."""
    game.run('SetOpt = nil ServiceInviterDB.opts = { kwon = true }')
    game.event("CHAT_MSG_CHANNEL", "guild inv", "Randy", "", "2. Trade - City", "", "", "", "", "Trade")
    game.event("CHAT_MSG_CHANNEL", "inv pls", "Wanda", "", "2. Trade - City", "", "", "", "", "Trade")
    invited = list(game.g.INVITED.values())
    assert "Randy" not in invited
    assert "Wanda" in invited   # control: the keyword path still works


def test_the_list_keeps_the_longest_waiting_customers_on_screen(game):
    """Seven waiting, six rows: the newest is the one that waits off-screen (Codex on #487)."""
    game.run('''ServiceInviterDB.role = "lock"
        for i = 1, 7 do local n = "Cust" .. i
            ServiceInviter_Test.Jobs.New(n, "wtb summon tb", "t", "Trade") ServiceInviter_Test.Jobs.Joined(n) end
        ServiceInviter_Test.Refresh()''')
    shown = [game.eval(f"ServiceInviterJobs.rows[{i}].name:GetText()") for i in range(1, 7)]
    assert shown == [f"Cust{i}" for i in range(1, 7)]


def test_finished_rows_give_way_to_waiting_customers(game):
    game.run('''local J = ServiceInviter_Test.Jobs
        J.New("Done", "x", "t", "Trade") J.Joined("Done") J.Set("Done", "paid")
        for i = 1, 6 do local n = "Cust" .. i J.New(n, "x", "t", "Trade") J.Joined(n) end
        ServiceInviter_Test.Refresh()''')
    shown = [game.eval(f"ServiceInviterJobs.rows[{i}].name:GetText()") for i in range(1, 7)]
    assert "Done" not in shown and shown[0] == "Cust1"
