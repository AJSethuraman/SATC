"""The customer book (the owner, 13 Nov 2026: "can it store our customer base and how many times
they use us and when"). Kept with the addon's saved settings. A summon counts when it goes out,
anything else when you press Paid or Done."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}


def summon(g, name, clock_step=3600):
    say_trade(g, name, "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", f"{name} joins the party.")
    g.run(f'ServiceInviter_Test.Jobs.Set("{name}", "summoned") CLOCK = CLOCK + {clock_step}')
    g.run(f'ServiceInviter_Test.Jobs.Remove("{name}")')


def test_each_summon_is_recorded_with_when_and_what():
    g = world(LOCK, "summons = { price = 35 }")
    summon(g, "Kaldrok")
    summon(g, "Kaldrok")
    c = g.eval('ServiceInviterDB.customers["Kaldrok"]')
    assert c.n == 2 and c.by.summons == 2 and c.worth == 70
    assert c.first < c.last


def test_a_returning_customer_is_marked_on_their_row():
    g = world(LOCK, "summons = { price = 35 }")
    summon(g, "Kaldrok")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert "1 before" in g.eval("ServiceInviterJobs.rows[1].name:GetText()")


def test_si_customers_lists_regulars_and_one_persons_history():
    g = world(LOCK, "summons = { price = 35 }")
    summon(g, "Kaldrok") ; summon(g, "Kaldrok") ; summon(g, "Mirasha")
    g.run('SlashCmdList.SERVICEINVITER("customers")')
    out = " ".join(g.printed())
    assert out.index("Kaldrok") < out.index("Mirasha") and "2 times" in out
    g.run('SlashCmdList.SERVICEINVITER("customers mirasha")')
    assert "Mirasha: 1 time" in " ".join(g.printed())


def test_a_paid_lockpick_counts_when_paid():
    from test_steps import lockpick_customer, click
    g = lockpick_customer(price="20")
    click(g, "paid")
    c = g.eval('ServiceInviterDB.customers["Kaldrok"]')
    assert c.n == 1 and c.by.lockpick == 1 and c.worth == 20
