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
    """A customer who has been summoned (was a lockpick buyer until 14 Nov 2026, when the addon
    became summons and blessings only). price "" = a free summon (Done, not Paid)."""
    units = {"player": LOCK_ME, "party1": ROGUE}
    g = world(units, f"summons = {{ price = {price or 'false'} }}",
              extra=KICK + extra + ("" if lead else " function UnitIsGroupLeader() return false end"))
    g.run('ServiceInviterDB.role = "lock"')
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run('UNITS.party2 = { "Kaldrok", "MAGE", 44, "Thunder Bluff" } GROUP["Kaldrok"] = true')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run('ServiceInviter_Test.Jobs.Set("Kaldrok", "summoned")')
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    return g


def row(g, field):
    return g.eval(f"ServiceInviterJobs.rows[1].{field}")


def click(g, button):
    """A click on a row button. Secure ones: PreClick, then the macro the game would run
    (/uninvite does the removal), then PostClick."""
    g.run(f'''local b = ServiceInviterJobs.rows[1].{button}
        if rawget(b._scripts, "PreClick") then b._scripts.PreClick(b) end
        local m = b:GetAttribute("macrotext") or ""
        local who = m:match("^/uninvite (.+)$")
        if who then KICKED = KICKED or {{}} KICKED[#KICKED + 1] = who end
        if rawget(b._scripts, "PostClick") then b._scripts.PostClick(b) end
        if rawget(b._scripts, "OnClick") then b._scripts.OnClick(b) end''')


def whispers(g):
    return [(to, m) for ch, to, m in g.sent() if ch == "WHISPER"]


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


def test_the_customer_window_shows_how_many_were_summoned_and_what_that_is_worth():
    """The owner, 13 Nov 2026: "it should still record EV - how many we summon. the paid will be
    inaccurate no matter waht because sometimes they leave and im not clicking it"."""
    g = world({"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}, "summons = { price = 35 }", extra=KICK)
    for n in ("Kaldrok", "Mirasha"):
        say_trade(g, n, "WTB summon to TB")
        g.event("CHAT_MSG_SYSTEM", f"{n} joins the party.")
        g.run(f'ServiceInviter_Test.Jobs.Set("{n}", "summoned")')
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterJobs.statSummoned:GetText()") == "2"
    assert g.eval("ServiceInviterJobs.statEV:GetText()") == "70 silver"


# The owner, 13 Nov 2026, clicking Paid on two customers: "removed Morne Paleblood from the group",
# then "Cydney Ironside is done. You're not the leader, so ask the leader to remove them." --
# "i dont see why im getting this". That line also covered "the game blocked a removal earlier",
# after which the addon stopped trying for the whole session.

def test_paid_still_removes_after_the_game_blocked_one_removal():
    g = lockpick_customer(price="20")
    g.event("ADDON_ACTION_BLOCKED", "ServiceInviter", "UninviteUnit()")
    click(g, "paid")
    assert list(g.g.KICKED.values()) == ["Kaldrok"]
    assert not any("not the leader" in p for p in g.printed())


def test_not_leader_names_the_leader():
    g = lockpick_customer(price="20", extra=' function UnitIsGroupLeader(u) return u == "party1" end')
    click(g, "paid")
    assert list(g.g.KICKED.values()) == []
    assert any("ask Sly to remove them" in p for p in g.printed())


def test_paid_removes_through_the_games_own_uninvite_not_a_blockable_call():
    """The owner's screenshot, 13 Nov 2026: "UninviteUnit() was blocked just then", followed by a
    false "removed Jefferis Rotloaf". Paid and x now run /uninvite on your click, like typing it."""
    g = lockpick_customer(price="20", extra=" CALLED = {} function UninviteUnit(n) CALLED[#CALLED + 1] = n end")
    assert g.eval("ServiceInviterJobs.rows[1].paid:GetAttribute(\"macrotext\")") == "/uninvite Kaldrok"
    assert g.eval("ServiceInviterJobs.rows[1].remove:GetAttribute(\"macrotext\")") == "/uninvite Kaldrok"
    click(g, "paid")
    assert len(g.g.CALLED) == 0                                   # never the blockable call
    assert any("removing Kaldrok from the group" in p for p in g.printed())
    assert whispers(g) == [("Kaldrok", "Thanks Kaldrok! Enjoy.")]


def test_not_leader_the_buttons_carry_no_uninvite():
    g = lockpick_customer(price="20", lead=False)
    assert g.eval("ServiceInviterJobs.rows[1].paid:GetAttribute(\"macrotext\")") == ""


def test_a_summon_they_never_take_is_not_an_arrival():
    """The owner, 14 Nov 2026: "so they register as arrived after simply receiving the summon".
    It used to mark them Arrived 40 seconds after the ritual started, taken or not."""
    seen = " function UnitIsVisible(u) local x = UNITS[u] return x ~= nil and x[4] == 'Thunder Bluff' end"
    g = world({"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}, extra=KICK + seen)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run('UNITS.party2 = { "Kaldrok", "MAGE", 44, "Orgrimmar" } GROUP["Kaldrok"] = true')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run('ServiceInviter_Test.Jobs.Set("Kaldrok", "summoned") CLOCK = CLOCK + 300 ServiceInviter_Test.CheckArrivals()')
    assert g.status("Kaldrok") == "summoned"                  # still in Orgrimmar: not arrived
    g.run('UNITS.party2[4] = "Thunder Bluff" CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()')
    assert g.status("Kaldrok") == "arrived"                   # took it: now in Thunder Bluff
