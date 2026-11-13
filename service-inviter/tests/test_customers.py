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


def test_a_regular_is_welcomed_back_in_chat():
    """The owner, 13 Nov 2026: "can we even announce loyalty in the chat? that would be dope"."""
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false }')
    for _ in range(3):
        summon(g, "Kaldrok")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    welcomes = [m for ch, _, m in g.sent() if ch == "PARTY" and "Kaldrok" in m]
    assert welcomes[-1] == "Hi Kaldrok! Welcome back, 4th time with us! Grimtotem will summon you to TB. 35 silver. Pay Grimtotem when you land."
    assert "Welcome back" not in welcomes[0]                     # the first time is a normal welcome


def test_loyalty_can_be_turned_off_and_custom_text_gets_visits():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false, loyalty = false }')
    summon(g, "Kaldrok")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert "Welcome back" not in [m for ch, _, m in g.sent() if ch == "PARTY"][-1]
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false } ServiceInviterDB.welcomemsg = "YO {name}, VISIT {visits}!"')
    summon(g, "Kaldrok")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert [m for ch, _, m in g.sent() if ch == "PARTY"][-1] == "YO Kaldrok, VISIT 2nd!"


def test_ordinals():
    g = world(LOCK)
    o = lambda n: g.eval(f"ServiceInviter_Test.Ordinal({n})")
    assert [o(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101)] == \
        ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "101st"]


def test_the_book_keeps_whole_forever_names_apart():
    """The owner, 13 Nov 2026: "has to count both first and last name too". Two Busters stay two
    customers, and the ritual's target (read from the unit, first + surname) lands on the same
    entry as the name from chat."""
    from test_group import FOREVER_NAMES
    g = world(LOCK, "summons = { price = 35 }", extra=FOREVER_NAMES)
    summon(g, "Buster Wang")
    summon(g, "Buster Smith")
    summon(g, "Buster Wang")
    book = g.eval("ServiceInviterDB.customers")
    assert book["Buster Wang"].n == 2 and book["Buster Smith"].n == 1 and book["Buster"] is None
    # summoned by the ritual on its target: the target's name is read whole from the unit
    say_trade(g, "Buster Smith", "WTB summon to TB")
    g.run('UNITS.party2 = { "Buster Smith", "ROGUE", 30, "Orgrimmar" } GROUP["Buster Smith"] = true UNITS.party1target = UNITS.party2')
    g.event("CHAT_MSG_SYSTEM", "Buster Smith joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    assert g.eval('ServiceInviterDB.customers["Buster Smith"].n') == 2


def test_your_own_loyalty_line_in_capitals():
    """The owner, 13 Nov 2026: "HOW CAN I SAY SOMETHING LIKE THIS IS YOUR 4TH TIME!!"."""
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false } ServiceInviterDB.loyaltymsg = "THIS IS YOUR {visits} TIME!!"')
    for _ in range(3):
        summon(g, "Kaldrok")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert [m for ch, _, m in g.sent() if ch == "PARTY"][-1] == \
        "Hi Kaldrok! THIS IS YOUR 4TH TIME!! Grimtotem will summon you to TB. 35 silver. Pay Grimtotem when you land."


def test_one_box_empty_is_off():
    """The owner, 13 Nov 2026: "can you make this simpler?" -- the loyalty setting: one box,
    what's in it is the line, empty is off."""
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false }')
    g.run('''local w = ServiceInviter_Test.BuildSetup() w:Show()
        ServiceInviter_Test.SetupBoxes().loyaltymsg:SetText("") w:Hide() w:Show() w:Hide()''')
    assert g.eval("ServiceInviterDB.loyaltymsg") == ""
    assert g.eval("ServiceInviter_Test.SetupBoxes().loyaltymsg:GetText()") == ""
    summon(g, "Kaldrok")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert "Welcome back" not in [m for ch, _, m in g.sent() if ch == "PARTY"][-1]


def test_the_regulars_line_goes_after_your_own_welcome():
    """The owner's own two lines, 13 Nov 2026: welcome "THE COST IS {price} AND WE WILL SUMMON YOU
    SOON!" and regulars "HEY FREQUENT FLYER! This is your {visits} time with us!"."""
    g = world(LOCK, "summons = { price = 35 }")
    g.run('''ServiceInviterDB.opts = { marks = false }
        ServiceInviterDB.welcomemsg = "THE COST IS {price} AND WE WILL SUMMON YOU SOON!"
        ServiceInviterDB.loyaltymsg = "HEY FREQUENT FLYER! This is your {visits} time with us!"''')
    say_trade(g, "Newbie", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Newbie joins the party.")
    for _ in range(3):
        summon(g, "Kaldrok")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    sent = [m for ch, _, m in g.sent() if ch == "PARTY"]
    assert sent[0] == "THE COST IS 35 silver AND WE WILL SUMMON YOU SOON!"
    assert sent[-1] == "THE COST IS 35 silver AND WE WILL SUMMON YOU SOON! HEY FREQUENT FLYER! This is your 4th time with us!"


def test_the_regulars_button_prints_the_top_ten():
    """The owner, 13 Nov 2026: "how can i see the list of people in game we have collected - or like
    top 10 at least"."""
    g = world(LOCK, "summons = { price = 35 }")
    for i in range(12):
        for _ in range(i + 1):
            summon(g, f"Buyer{i:02d}", clock_step=1)
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    before = len(g.printed())
    g.run("ServiceInviterJobs.regularsBtn._scripts.OnClick(ServiceInviterJobs.regularsBtn)")
    out = [p for p in g.printed()[before:] if ". Buyer" in p]
    assert len(out) == 10 and "Buyer11" in out[0] and "Buyer02" in out[-1]


def test_analytics_record_where_they_went_and_when():
    """The owner, 13 Nov 2026: "it should also track analytics like where they went and stuff for
    us to know"."""
    g = world({"player": ("Me", "SHAMAN", 60, "Orgrimmar"),
               "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
               "party2": ("Ashfel", "WARLOCK", 60, "Undercity")}, "summons = { price = 35 }")
    summon(g, "Kaldrok")
    summon(g, "Kaldrok")
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    g.run('ServiceInviter_Test.Jobs.Set("Mirasha", "summoned")')
    a = g.eval("ServiceInviterDB.analytics")
    assert a.n == 3 and a.to["Thunder Bluff"] == 2 and a.to["Undercity"] == 1 and a.by.summons == 3 and a.worth == 105
    assert sum(a.hour[h] or 0 for h in range(0, 24)) == 3
    assert g.eval('ServiceInviterDB.customers["Kaldrok"].to["Thunder Bluff"]') == 2
    g.run('SlashCmdList.SERVICEINVITER("stats")')
    out = " ".join(g.printed())
    assert "3 uses by 2 customers (1 came back)" in out and "Thunder Bluff 2" in out and "Undercity 1" in out
    assert "Busiest hours" in out and "summons 3" in out


def test_a_regular_invited_by_someone_else_still_hears_the_regulars_line():
    """The owner, 13 Nov 2026: "i want the regular coming back messages to always play if it
    detects someone joined again" -- "even if someone else invited them"."""
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false }')
    for _ in range(3):
        summon(g, "Kaldrok")
    before = len(g.sent())
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")      # the leader invited him, not us
    said = [m for ch, _, m in g.sent()[before:] if ch in ("PARTY", "RAID")]
    assert len(said) == 1 and "Welcome back, 4th time with us!" in said[0] and said[0].startswith("Hi Kaldrok!")


def test_someone_new_invited_by_someone_else_gets_nothing():
    g = world(LOCK, "summons = { price = 35 }")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert [m for ch, _, m in g.sent() if ch in ("PARTY", "RAID")] == []


def test_a_regular_hears_it_even_with_the_welcome_turned_off():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.opts = { marks = false, welcome = false }')
    summon(g, "Kaldrok")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert [m for ch, _, m in g.sent() if ch == "PARTY"][-1] == "Hi Kaldrok! Welcome back, 2nd time with us!"


def test_si_customers_all_lists_everyone():
    """The owner, 13 Nov 2026: "how can i see the full list of regulars"."""
    g = world(LOCK, "summons = { price = 35 }")
    for i in range(12):
        summon(g, f"Buyer{i:02d}", clock_step=1)
    before = len(g.printed())
    g.run('SlashCmdList.SERVICEINVITER("customers")')
    top = g.printed()[before:]
    assert any("(/si customers all for everyone)" in p for p in top)
    before = len(g.printed())
    g.run('SlashCmdList.SERVICEINVITER("customers all")')
    out = g.printed()[before:]
    assert "All 12 customers:" in out[0] and len([p for p in out if ". Buyer" in p]) == 12
