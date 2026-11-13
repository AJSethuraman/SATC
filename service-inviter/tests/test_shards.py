"""Soul shards. The owner, 13 Nov 2026: "i want a running counter of summons - like our inv and
expected amount left so it knows to stop"; other warlocks' shards are typed ("I type the
number"), yours are read from your bags ("built in for the lock")."""
from test_group import world, say_trade

HELPER = {"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}
ME_LOCK = {"player": ("Me", "WARLOCK", 60, "Thunder Bluff")}
BAG = "SHARDS = 0 function GetItemCount(id) if id == 6265 then return SHARDS end return 0 end"


def invited(g):
    return list(g.g.INVITED.values())


def test_not_counting_until_you_type_a_number():
    g = world(HELPER)
    for n in ("Aa", "Bb", "Cc"):
        say_trade(g, n, "WTB summon to TB")
    assert len(invited(g)) == 3


def test_it_stops_inviting_when_the_queue_would_use_the_last_shard():
    g = world(HELPER)
    g.run('SlashCmdList.SERVICEINVITER("shards 2")')
    for n in ("Aa", "Bb", "Cc"):
        say_trade(g, n, "WTB summon to TB")
    assert invited(g) == ["Aa", "Bb"]
    assert any("out of soul shards" in p for p in g.printed())


def test_another_warlocks_summon_takes_one_off_the_typed_count():
    g = world(HELPER)
    g.run('SlashCmdList.SERVICEINVITER("shards 3")')
    say_trade(g, "Aa", "WTB summon to TB")
    g.event("CHAT_MSG_SYSTEM", "Aa joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    assert g.status("Aa") == "summoned"
    assert g.eval("ServiceInviterDB.shards") == 2


def test_the_warlock_counts_their_own_bags():
    g = world(ME_LOCK, extra=BAG)
    g.run('ServiceInviterDB.role = "lock" SHARDS = 1')
    say_trade(g, "Aa", "WTB summon to TB")
    say_trade(g, "Bb", "WTB summon to TB")
    assert invited(g) == ["Aa"]
    g.run("SHARDS = 5")
    say_trade(g, "Cc", "WTB summon to TB")
    assert invited(g) == ["Aa", "Cc"]


def test_bags_and_typed_add_up():
    g = world(ME_LOCK, extra=BAG)
    g.run('SHARDS = 4 ServiceInviterDB.shards = 6')
    assert g.eval("(ServiceInviter_Test.Jobs.Shards())") == 10
    g.run('SlashCmdList.SERVICEINVITER("shards")')
    assert any("shards: 10 (4 yours, 6 typed), 0 summons queued, 10 left" in p for p in g.printed())


def test_the_window_shows_shards_left():
    g = world(HELPER)
    g.run('SlashCmdList.SERVICEINVITER("shards 5")')
    say_trade(g, "Aa", "WTB summon to TB")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterJobs.statShards:GetText()") == "4"
    g.run('SlashCmdList.SERVICEINVITER("shards off")')
    g.run("ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterJobs.statShards:GetText()") == "-"


def test_portals_and_lockpicks_dont_care_about_shards():
    g = world({"player": ("Me", "ROGUE", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}, "lockpick = { on = true }")
    g.run('SlashCmdList.SERVICEINVITER("shards 0")')
    say_trade(g, "Aa", "WTB lockbox opened")
    assert invited(g) == ["Aa"]
