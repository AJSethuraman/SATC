"""Workers and stasis. The owner, 13 Nov 2026: "there needs to be a command that stops it from
running altogether so it's just in stasis and there needs to be a way to mark workers so that it
doesnt get confused when a worker joins after the raid forms" -- "if someone is just there
clicking they won't be a warlock summoning they are just there and click"."""
from test_group import world, say_trade

LOCK = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}


def party(g):
    return [m for ch, _, m in g.sent() if ch in ("PARTY", "RAID")]


def test_a_worker_who_joins_gets_no_row_and_no_welcome():
    g = world(LOCK)
    g.run('SlashCmdList.SERVICEINVITER("worker Clicky Bob")')
    g.event("CHAT_MSG_SYSTEM", "Clicky Bob joins the party.")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Clicky Bob")') is None
    assert party(g) == []


def test_a_worker_asking_for_a_summon_in_chat_is_not_invited():
    g = world(LOCK)
    g.run('SlashCmdList.SERVICEINVITER("worker Clicky")')
    say_trade(g, "Clicky", "WTB summon to TB")
    assert list(g.g.INVITED.values()) == []


def test_someone_else_who_joins_still_gets_a_row():
    g = world(LOCK)
    g.run('SlashCmdList.SERVICEINVITER("worker Clicky")')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Kaldrok")') is not None


def test_workers_group_marks_everyone_but_customers():
    g = world(LOCK)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.run('UNITS.party2 = { "Kaldrok", "MAGE", 44, "Orgrimmar" } GROUP["Kaldrok"] = true')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run('UNITS.party3 = { "Clicky", "PRIEST", 60, "Thunder Bluff" } GROUP["Clicky"] = true')
    g.run('SlashCmdList.SERVICEINVITER("workers group")')
    assert g.eval('ServiceInviter_Test.Jobs.IsWorker("Clicky")') is True
    assert g.eval('ServiceInviter_Test.Jobs.IsWorker("Grimtotem")') is True
    assert g.eval('ServiceInviter_Test.Jobs.IsWorker("Kaldrok")') is False


def test_marking_a_worker_removes_their_joined_row_and_toggles_off():
    g = world(LOCK)
    g.event("CHAT_MSG_SYSTEM", "Clicky joins the party.")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Clicky")') is not None
    g.run('SlashCmdList.SERVICEINVITER("worker clicky")')
    assert g.eval('ServiceInviter_Test.Jobs.Get("Clicky")') is None
    g.run('SlashCmdList.SERVICEINVITER("worker Clicky")')
    assert g.eval('ServiceInviter_Test.Jobs.IsWorker("Clicky")') is False


def test_stop_hears_nothing_and_start_wakes_it():
    g = world(LOCK)
    g.run('SlashCmdList.SERVICEINVITER("stop")')
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Mirasha joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    assert list(g.g.INVITED.values()) == [] and g.sent() == []
    assert g.eval('ServiceInviter_Test.Jobs.All()[1]') is None
    g.run('SlashCmdList.SERVICEINVITER("start")')
    say_trade(g, "Kaldrok", "WTB summon to TB")
    assert list(g.g.INVITED.values()) == ["Kaldrok"]


def test_our_workers_box_picks_from_the_group_and_saves():
    """The owner, 13 Nov 2026: "i want it more like it is in the lock tab where i can say these are
    our locks"."""
    g = world({**LOCK, "party2": ("Clicky", "PRIEST", 60, "Thunder Bluff")})
    g.run('''S = ServiceInviter_Test.BuildSetup() S:Show() S.ShowTab(1)
        ServiceInviter_Test.ShowPicker(ServiceInviter_Test.SetupBoxes().workers, false, "Our workers", "workers")''')
    labels = [g.eval(f"ServiceInviterPicker.buttons[{i}]:GetText()") for i in (1, 2)]
    assert any("Grimtotem" in l for l in labels) and any("Clicky" in l for l in labels)
    assert not any("(you)" in (l or "") for l in labels)
    g.run("ServiceInviterPicker.buttons[2]._scripts.OnClick()")
    g.run("S.Save()")
    assert g.eval('ServiceInviter_Test.Jobs.IsWorker("Clicky")') is True
    g.run('SlashCmdList.SERVICEINVITER("worker Bob")')
    g.run("S.Load()")
    assert g.eval("ServiceInviter_Test.SetupBoxes().workers:GetText()") == "Bob, Clicky"
    g.run('ServiceInviter_Test.SetupBoxes().workers:SetText("Bob") S.Save()')
    assert g.eval('ServiceInviter_Test.Jobs.IsWorker("Clicky")') is False


def test_stopped_your_own_invites_never_open_the_window():
    """The owner, 14 Nov 2026: "if i /si stop it should stop opening /si customers altogether, i
    am not currently using si"."""
    g = world(LOCK)
    g.run('SlashCmdList.SERVICEINVITER("stop")')
    g.run('C_PartyInfo.InviteUnit("Friendo")')                       # an invite you typed yourself
    assert g.eval("ServiceInviter_Test.Jobs.All()[1]") is None
    assert not g.eval("ServiceInviterJobs and ServiceInviterJobs:IsShown()")
    g.run('SlashCmdList.SERVICEINVITER("")')                         # /si on its own
    assert not g.eval("ServiceInviterJobs and ServiceInviterJobs:IsShown()")
    assert any("/si start to wake it" in p for p in g.printed())


def test_the_tools_tab_runs_the_commands():
    """The owner, 14 Nov 2026: "i want the addon to have a debug panel/command panel or something -
    there are too many to remember"."""
    g = world(LOCK)
    g.run('''S = ServiceInviter_Test.BuildSetup() S:Show() S.Load()
        ServiceInviter_Test.SetupBoxes().testtarget:SetText("Main Character")
        S.tools["Test mode on"]._scripts.OnClick()''')
    assert g.eval("ServiceInviterDB.dryrun") is True and g.eval("ServiceInviterDB.testto") == "Main Character"
    g.run('S.tools["Test mode off"]._scripts.OnClick()')
    assert not g.eval("ServiceInviterDB.dryrun")
    g.run('ServiceInviter_Test.SetupBoxes().toolname:SetText("Momma Lovesme") S.tools["Didn\'t pay"]._scripts.OnClick()')
    assert g.eval('ServiceInviterDB.scammers["Momma Lovesme"].n') == 1
    g.run('S.tools["Stop everything"]._scripts.OnClick()')
    assert g.eval("ServiceInviterDB.stasis") is True
    g.run('S.tools["Start again"]._scripts.OnClick()')
    assert not g.eval("ServiceInviterDB.stasis")
