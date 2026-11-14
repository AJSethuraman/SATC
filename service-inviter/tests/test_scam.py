"""Didn't pay. The owner, 14 Nov 2026: "add a scam button rather than paid to record them as prior
scammers and publicly say it when they join"."""
from test_group import world, say_trade
from test_steps import lockpick_customer, click, whispers

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}


def chat(g):
    return [m for ch, _, m in g.sent() if ch in ("PARTY", "RAID")]


def test_scam_shows_under_paid_and_records_them_and_removes_them_without_thanks():
    g = lockpick_customer(price="20")
    assert g.eval("ServiceInviterJobs.rows[1].scam._shown") is True
    assert g.eval('ServiceInviterJobs.rows[1].scam:GetAttribute("macrotext")') == "/uninvite Kaldrok"
    click(g, "scam")
    assert g.status("Kaldrok") == "scammed"
    assert list(g.g.KICKED.values()) == ["Kaldrok"]
    assert whispers(g) == []                                       # no thank-you
    e = g.eval('ServiceInviterDB.scammers["Kaldrok"]')
    assert e.n == 1 and e.owed == 20


def test_no_scam_button_on_a_free_service():
    g = lockpick_customer()
    assert g.eval("ServiceInviterJobs.rows[1].scam._shown") is False


def test_they_are_called_out_when_they_join_and_get_no_welcome():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.scammers = { ["Momma Lovesme"] = { n = 1, owed = 35 } }')
    g.event("CHAT_MSG_SYSTEM", "Momma Lovesme joins the party.")
    assert chat(g) == ["Heads up: Momma Lovesme didn't pay last time."]


def test_they_are_never_invited_from_chat():
    g = world(LOCK, "summons = { price = 35 }")
    g.run('ServiceInviterDB.scammers = { ["Momma Lovesme"] = { n = 1, owed = 35 } }')
    say_trade(g, "Momma Lovesme", "WTB summon to TB")
    assert list(g.g.INVITED.values()) == []
    assert any("didn't pay last time" in p for p in g.printed())


def test_your_own_words_and_empty_is_quiet():
    g = world(LOCK)
    g.run('ServiceInviterDB.scammers = { Kaldrok = { n = 1 } } ServiceInviterDB.scammsg = "{name} owes us, pay first"')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert chat(g) == ["Kaldrok owes us, pay first"]
    g = world(LOCK)
    g.run('ServiceInviterDB.scammers = { Kaldrok = { n = 1 } } ServiceInviterDB.scammsg = ""')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert chat(g) == []


def test_unscam_clears_them_and_the_list_opens_to_copy():
    g = world(LOCK)
    g.run('ServiceInviterDB.scammers = { ["Momma Lovesme"] = { n = 2, owed = 70, last = 1763000000 } }')
    g.run('SlashCmdList.SERVICEINVITER("scammers")')
    assert "Momma Lovesme: 2 times, owed 70 silver" in g.eval("ServiceInviterCopy.box:GetText()")
    g.run('SlashCmdList.SERVICEINVITER("unscam momma lovesme")')
    assert g.eval('ServiceInviterDB.scammers["Momma Lovesme"]') is None


def test_paid_by_mistake_can_be_turned_into_scam_and_the_money_comes_off():
    """The owner, 14 Nov 2026: "i accidentally added paid to someone but meant to add scam"."""
    g = lockpick_customer(price="20")
    click(g, "paid")
    assert g.eval("ServiceInviter_Test.Stats().silver") == 20
    g.run("ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterJobs.rows[1].scam._shown") is True        # still there on a Paid row
    g.run('SlashCmdList.SERVICEINVITER("scam kaldrok")')
    assert g.status("Kaldrok") == "scammed"
    assert g.eval("ServiceInviter_Test.Stats().silver") == 0 and g.eval("ServiceInviter_Test.Stats().paid") == 0
    assert g.eval('ServiceInviterDB.scammers["Kaldrok"].n') == 1


def test_scam_by_name_for_someone_already_gone_from_the_list():
    g = world(LOCK)
    g.run('SlashCmdList.SERVICEINVITER("scam Momma Lovesme")')
    assert g.eval('ServiceInviterDB.scammers["Momma Lovesme"].n') == 1


def test_someone_who_leaves_after_the_summon_keeps_paid_and_scam():
    """The owner, 14 Nov 2026: "when someone leaves it takes away the option to pick scam?"."""
    g = world(LOCK, "summons = { price = 35 }")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run('ServiceInviter_Test.Jobs.Set("Kaldrok", "summoned")')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok leaves the party.")
    g.run("CLOCK = CLOCK + 600 ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.status("Kaldrok") == "left"
    assert g.eval("ServiceInviterJobs.rows[1].job.name") == "Kaldrok"     # still listed ten minutes on
    assert g.eval("ServiceInviterJobs.rows[1].scam._shown") is True
    g.run('local b = ServiceInviterJobs.rows[1].scam b._scripts.PostClick(b)')
    assert g.status("Kaldrok") == "scammed"


def test_someone_who_leaves_before_the_summon_owes_nothing():
    g = world(LOCK, "summons = { price = 35 }")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.event("CHAT_MSG_SYSTEM", "Kaldrok leaves the party.")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterJobs.rows[1].scam._shown") is False


def test_in_a_raid_as_leader_or_assistant_it_goes_out_as_a_raid_warning():
    """The owner, 14 Nov 2026: "can the scam message be flashier to be more public". {skull} is the
    game's own: party, raid and raid warning chat draw it as the icon."""
    g = world(LOCK, extra=" function IsInRaid() return true end")
    g.run('ServiceInviterDB.scammers = { Kaldrok = { n = 1 } } ServiceInviterDB.scammsg = "{skull} HEY {name} ! YOU ARE A SCAMMER! {skull}"')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok has joined the raid group.")
    assert [(ch, m) for ch, _, m in g.sent()] == [("RAID_WARNING", "{skull} HEY Kaldrok ! YOU ARE A SCAMMER! {skull}")]


def test_in_a_raid_without_lead_or_assist_it_goes_to_raid_chat():
    g = world(LOCK, extra=" function IsInRaid() return true end function UnitIsGroupLeader() return false end function UnitIsGroupAssistant() return false end")
    g.run('ServiceInviterDB.scammers = { Kaldrok = { n = 1 } }')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok has joined the raid group.")
    assert [ch for ch, _, m in g.sent()] == ["RAID"]


def test_the_names_export_for_the_guild_bot():
    """The owner, 14 Nov 2026: "it just looks up names i just want a list i can copy and paste"."""
    g = world(LOCK)
    g.run('ServiceInviterDB.scammers = { ["Momma Lovesme"] = { n = 2, owed = 70 }, Kaldrok = { n = 1, owed = 35 } }')
    g.run('SlashCmdList.SERVICEINVITER("scammers names")')
    assert g.eval("ServiceInviterCopy.box:GetText()") == "Kaldrok\nMomma Lovesme"



def test_clear_left_takes_everyone_who_left_off_the_list():
    """The owner, 14 Nov 2026: "maybe a clear the people who have left the group"."""
    g = world(LOCK, "summons = { price = 35 }")
    for n in ("Aa", "Bb", "Cc"):
        say_trade(g, n, "WTB summon to TB")
        g.event("CHAT_MSG_SYSTEM", f"{n} joins the party.")
    g.event("CHAT_MSG_SYSTEM", "Aa leaves the party.")
    g.event("CHAT_MSG_SYSTEM", "Bb leaves the party.")
    g.run("ServiceInviterJobs:Show() ServiceInviterJobs.clearBtn._scripts.OnClick()")
    assert [j.name for j in g.eval("ServiceInviter_Test.Jobs.All()").values()] == ["Cc"]
