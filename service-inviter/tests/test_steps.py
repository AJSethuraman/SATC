"""Customer rows follow the service, and Paid finishes the job.

The design review of 12 Nov 2026 found the rows only knew summons: a lockpicking buyer who
joined put "Summon Kaldrok" on the big button when you were the warlock (reproduced), and a
portal or lockpick customer could never be marked Paid. The owner, the same day: "Paid should
also remove from party and maybe send a thank you"."""
from test_group import world, say_trade

LOCK_ME = ("Me", "WARLOCK", 60, "Thunder Bluff")
ROGUE = ("Sly", "ROGUE", 60, "Thunder Bluff")
KICK = "KICKED = {} function UninviteUnit(n) KICKED[#KICKED + 1] = n end"


def lockpick_customer(price="", lead=True, extra=""):
    units = {"player": LOCK_ME, "party1": ROGUE}
    g = world(units, f"lockpick = {{ on = true{', price = ' + price if price else ''} }}",
              extra=KICK + extra + ("" if lead else " function UnitIsGroupLeader() return false end"))
    g.run('ServiceInviterDB.role = "lock"')
    say_trade(g, "Kaldrok", "WTB someone to open my lockbox")
    g.run('UNITS.party2 = { "Kaldrok", "MAGE", 44, "Thunder Bluff" } GROUP["Kaldrok"] = true')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    return g


def row(g, field):
    return g.eval(f"ServiceInviterJobs.rows[1].{field}")


def click(g, button):
    g.run(f"ServiceInviterJobs.rows[1].{button}._scripts.OnClick(ServiceInviterJobs.rows[1].{button})")


def whispers(g):
    return [(to, m) for ch, to, m in g.sent() if ch == "WHISPER"]


def test_a_lockpick_customer_is_never_offered_a_summon():
    g = lockpick_customer()
    assert g.eval("ServiceInviterNext:GetText()") != "Summon Kaldrok"
    assert "Ritual of Summoning" not in (g.eval('ServiceInviterNext:GetAttribute("macrotext")') or "")
    assert row(g, "summon")._shown is False


def test_a_free_service_finishes_with_done():
    g = lockpick_customer()
    assert row(g, "paid")._shown is True
    assert g.eval("ServiceInviterJobs.rows[1].paid:GetText()") == "Done"


def test_a_paid_service_finishes_with_paid_even_when_someone_else_collects():
    g = lockpick_customer(price="20")
    assert g.eval("ServiceInviterJobs.rows[1].paid:GetText()") == "Paid"
    assert row(g, "paid")._shown is True


def test_paid_thanks_them_then_removes_them():
    g = lockpick_customer(price="20")
    click(g, "paid")
    assert whispers(g) == [("Kaldrok", "Thanks Kaldrok! Enjoy.")]
    assert list(g.g.KICKED.values()) == ["Kaldrok"]
    assert g.status("Kaldrok") == "paid"


def test_done_on_a_free_service_thanks_and_removes_too():
    g = lockpick_customer()
    click(g, "paid")
    assert whispers(g) == [("Kaldrok", "Thanks Kaldrok! Enjoy.")]
    assert list(g.g.KICKED.values()) == ["Kaldrok"]
    assert g.status("Kaldrok") == "done"


def test_not_leader_thanks_but_does_not_remove():
    g = lockpick_customer(price="20", lead=False)
    click(g, "paid")
    assert whispers(g) == [("Kaldrok", "Thanks Kaldrok! Enjoy.")]
    assert list(g.g.KICKED.values()) == []
    assert any("ask the leader" in p for p in g.printed())


def test_thank_you_text_is_yours_and_blank_turns_it_off():
    g = lockpick_customer(price="20")
    g.run('ServiceInviterDB.thanksmsg = "ty {name}, come back soon"')
    click(g, "paid")
    assert whispers(g) == [("Kaldrok", "ty Kaldrok, come back soon")]
    g = lockpick_customer(price="20")
    g.run('ServiceInviterDB.thanksmsg = ""')
    click(g, "paid")
    assert whispers(g) == []
    assert list(g.g.KICKED.values()) == ["Kaldrok"]


def test_a_trade_that_pays_thanks_them_and_waits_for_your_click_to_remove():
    """Removing someone from a game event, with no click, risks the game's block popup; the
    thanks goes out, and the x on the row removes them."""
    g = lockpick_customer(price="20")
    g.run('ServiceInviterDB.payee = { mode = "me" } UNITS.NPC = UNITS.party2 TRADEMONEY = 2000')
    g.event("TRADE_SHOW")
    g.event("TRADE_ACCEPT_UPDATE", 1, 1)
    g.event("TRADE_CLOSED")
    assert g.status("Kaldrok") == "paid"
    assert whispers(g) == [("Kaldrok", "Thanks Kaldrok! Enjoy.")]
    assert list(g.g.KICKED.values()) == []


def test_a_summon_customer_can_be_marked_paid_once_summoned_whoever_collects():
    g = world({"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}, extra=KICK)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").service') == "summons"
    assert row(g, "paid")._shown is False            # not summoned yet
    g.run('ServiceInviter_Test.Jobs.Set("Kaldrok", "summoned") ServiceInviter_Test.Refresh()')
    assert row(g, "paid")._shown is True
    assert row(g, "trade")._shown is False           # Grimtotem collects, not you


def test_the_big_button_still_summons_your_own_summon_customer():
    g = world({"player": LOCK_ME}, extra=KICK)
    g.run('ServiceInviterDB.role = "lock"')
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterNext:GetText()") == "Summon Kaldrok"


def test_the_big_button_only_summons_people_coming_to_where_you_stand():
    """The owner, 12 Nov 2026: "like it knows that i can only summon to uc and to only let me try
    to do that with the next person in queue?". You in UC, a second warlock in TB; the TB buyer
    asked first, but the button skips them for the UC buyer."""
    g = world({"player": ("Me", "WARLOCK", 60, "Undercity"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}, extra=KICK)
    g.run('ServiceInviterDB.role = "lock"')
    say_trade(g, "Kaldrok", "WTB summon to TB")
    say_trade(g, "Mirasha", "WTB summon to UC")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterNext:GetText()") == "Summon Mirasha"
    assert row(g, "summon")._shown is False          # Kaldrok's row: Grimtotem's customer


def test_trade_opens_by_itself_for_a_paid_lockpick_when_you_collect():
    """Codex review, 12 Nov 2026: auto-trade only ever fired for summon customers, because only
    they reach "arrived"; a lockpick customer you collect from, in range, never got a trade."""
    g = lockpick_customer(price="20")
    g.run('ServiceInviterDB.payee = { mode = "me" } ServiceInviterDB.autotrade = true')
    g.run("CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()")
    assert list(g.g.TRADES.values()) == ["party2"]
    g.run("CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()")
    assert len(g.g.TRADES) == 1                       # once, not every second
