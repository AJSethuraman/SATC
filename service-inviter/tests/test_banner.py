"""The click-the-portal banner (design review, 12 Nov 2026): a small label naming the event,
the instruction as the loudest line, then who is being summoned, to where, and who gets paid;
a bar counts down the 14 seconds."""
from test_group import world, say_trade

ME_TB = ("Me", "SHAMAN", 60, "Thunder Bluff")
LOCK_TB = ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")


def summoning(payee=None):
    g = world({"player": ME_TB, "party1": LOCK_TB})
    if payee:
        g.run(f'ServiceInviterDB.payee = {{ mode = "{payee}" }}')
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run('UNITS.party2 = { "Kaldrok", "ROGUE", 44, "Orgrimmar" } GROUP["Kaldrok"] = true')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    return g


def banner(g, field):
    return g.eval(f"ServiceInviterAlert.{field}:GetText()")


def test_the_banner_says_what_to_do_who_where_and_who_gets_paid():
    g = summoning()
    assert banner(g, "label") == "RITUAL OF SUMMONING STARTED"
    assert banner(g, "title") == "CLICK THE PORTAL"
    assert banner(g, "sub") == "Summoning Kaldrok to Thunder Bluff. Pay Grimtotem."


def test_when_you_collect_it_says_pay_you():
    g = summoning(payee="me")
    assert banner(g, "sub") == "Summoning Kaldrok to Thunder Bluff. Pay: you."


def test_the_bar_counts_down_and_the_pulse_stops_after_two_seconds():
    g = summoning()
    a = "ServiceInviterAlert"
    g.run(f"{a}._scripts.OnUpdate({a}, 7)")
    assert abs(g.eval(f"{a}.barWidth") - 280) < 1        # half of 560 left after 7 of 14 seconds
    g.run(f"{a}._scripts.OnUpdate({a}, 0)")
    assert g.eval(f"{a}.alpha") == 1                     # steady after the first two seconds
    g.run(f"{a}._scripts.OnUpdate({a}, 8)")
    assert g.eval(f"{a}:IsShown()") is False
