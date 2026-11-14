"""The team: copies of the addon talking to each other, with one point of contact who invites and
whispers every customer. The owner, 14 Nov 2026: "i want to give it to 3-4 of us ... we share our
info and the addons talk", "i told you i want a point of contact, so that. it just gives them that
point in time price", and the test: "my hits go to him via the addon".

Two copies run side by side here, each in its own world; whatever one sends on the addon channel
is delivered to the other as the game would."""
import re
from test_group import world, say_trade

COMMS = """
ADDON_OUT = {}
C_ChatInfo = { RegisterAddonMessagePrefix = function() return true end,
               SendAddonMessage = function(p, m, d, t) ADDON_OUT[#ADDON_OUT + 1] = { p, m, d, t } end }
function IsInRaid() return true end
"""
ME = ("Me", "SHAMAN", 60, "Thunder Bluff")
BONE = ("Bone Charms", "PRIEST", 60, "Thunder Bluff")
YEET = ("Yeet Lock", "WARLOCK", 60, "Thunder Bluff")


def pair(services="summons = { price = 35 }"):
    me = world({"player": ME, "raid1": BONE, "raid2": YEET}, services, extra=COMMS)
    bone = world({"player": BONE, "raid1": ME, "raid2": YEET}, services, extra=COMMS)
    for g in (me, bone):
        g.run('ServiceInviterDB.opts = { marks = false } SlashCmdList.SERVICEINVITER("team add Me, Bone Charms, Yeet Lock")')
        g.run('SlashCmdList.SERVICEINVITER("team poc Bone Charms")')
    pump(me, bone, "Me")
    pump(bone, me, "Bone Charms")
    return me, bone


def pump(src, dst, sender):
    """Deliver everything src sent on the addon channel to dst, as CHAT_MSG_ADDON from sender."""
    out = src.g.ADDON_OUT
    msgs = [(out[i][1], out[i][2], out[i][3]) for i in range(1, len(out) + 1)]
    src.run("ADDON_OUT = {}")
    for p, m, d in msgs:
        dst.event("CHAT_MSG_ADDON", p, m, d, sender)
    return len(msgs)


def clean(lines):
    return [re.sub(r"\|c[0-9a-fA-F]{8}|\|r", "", p) for p in lines]


def test_the_copies_find_each_other_and_agree_on_the_point_of_contact():
    me, bone = pair()
    assert me.eval("ServiceInviter_Test.Jobs.POC()") == "Bone Charms"
    assert bone.eval("ServiceInviter_Test.Jobs.POC()") == "Bone Charms"


def test_your_buyer_is_handed_to_the_point_of_contact_who_invites():
    me, bone = pair()
    say_trade(me, "Kaldrok", "wtb summon to TB")
    assert list(me.g.INVITED.values()) == []                       # you never reach the stranger
    assert any("handed Kaldrok (Trade - City, quoted 35 silver) to Bone Charms" in p for p in clean(me.printed()))
    pump(me, bone, "Me")
    assert list(bone.g.INVITED.values()) == ["Kaldrok"]
    assert bone.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 35


def test_two_teammates_hearing_the_same_buyer_make_one_invite():
    me, bone = pair()
    say_trade(me, "Kaldrok", "wtb summon to TB")
    say_trade(bone, "Kaldrok", "wtb summon to TB")                 # Bone heard him too
    pump(me, bone, "Me")
    assert list(bone.g.INVITED.values()) == ["Kaldrok"]


def test_only_the_point_of_contact_talks_to_the_customer():
    me, bone = pair()
    say_trade(me, "Kaldrok", "wtb summon to TB")
    pump(me, bone, "Me")
    for g in (me, bone):
        g.run('UNITS.raid3 = { "Kaldrok", "MAGE", 44, "Orgrimmar" } GROUP["Kaldrok"] = true')
        g.event("CHAT_MSG_SYSTEM", "Kaldrok has joined the raid group.")
    assert me.sent() == []
    whispers = [(ch, to, m) for ch, to, m in bone.sent()]
    assert whispers == [("WHISPER", "Kaldrok", "Hi Kaldrok! Yeet Lock will summon you to TB. 35 silver. Pay Yeet Lock when you land.")]


def test_the_quote_is_your_channels_price_at_that_moment():
    me, bone = pair("summons = { price = 50, mode = 'undercut', floor = 25, undercut = 5 }")
    say_trade(me, "Rival", "WTS summons to TB 40s")                # only your channel has this seller
    say_trade(me, "Kaldrok", "wtb summon to TB")
    pump(me, bone, "Me")
    assert bone.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 35


def test_your_test_run_goes_through_the_point_of_contact_to_your_target():
    """The owner's dry run: their hits go to the point of contact, whose copy whispers the exact
    customer messages to the target instead of the customer, and invites nobody."""
    me, bone = pair("summons = { price = 50, mode = 'undercut', floor = 25, undercut = 5 }")
    me.run('SlashCmdList.SERVICEINVITER("test Main Character")')
    say_trade(me, "Rival", "WTS summons to TB 40s")
    say_trade(me, "Kaldrok", "wtb summon to TB")
    assert any("TEST handed Kaldrok (Trade - City, quoted 35 silver) to Bone Charms" in p for p in clean(me.printed()))
    pump(me, bone, "Me")
    assert list(bone.g.INVITED.values()) == [] and list(me.g.INVITED.values()) == []
    sent = bone.sent()
    assert sent and all(ch == "WHISPER" and to == "Main Character" for ch, to, _ in sent)
    assert sent[0][2] == "Hi Kaldrok! Yeet Lock will summon you to TB. 35 silver. Pay Yeet Lock when you land."
    assert any("TEST Me handed you Kaldrok (Trade - City, quoted 35 silver)" in p for p in clean(bone.printed()))


def test_a_test_with_no_target_whispers_the_teammate_who_found_them():
    me, bone = pair()
    me.run('SlashCmdList.SERVICEINVITER("test")')
    say_trade(me, "Kaldrok", "wtb summon to TB")
    pump(me, bone, "Me")
    assert {to for ch, to, _ in bone.sent()} == {"Me"}


def test_with_the_point_of_contact_offline_you_work_solo():
    me = world({"player": ME, "raid1": BONE, "raid2": YEET}, "summons = { price = 35 }", extra=COMMS)
    me.run('SlashCmdList.SERVICEINVITER("team add Bone Charms") SlashCmdList.SERVICEINVITER("team poc Bone Charms")')
    say_trade(me, "Kaldrok", "wtb summon to TB")                 # Bone's copy never said hello
    assert list(me.g.INVITED.values()) == ["Kaldrok"]


def test_a_copy_that_isnt_on_the_team_is_noticed_but_not_trusted():
    me = world({"player": ME, "raid1": BONE}, extra=COMMS)
    me.event("CHAT_MSG_ADDON", "SvcInv1", "HI\t3.1.0\t0\tThunder Bluff\t?", "RAID", "Stranger")
    assert any("Stranger runs Service Inviter too." in p for p in clean(me.printed()))
    me.event("CHAT_MSG_ADDON", "SvcInv1", "BUY\tMe\tKaldrok\tsummons\tThunder Bluff\t1\tTrade\tTrade\t0\t\tx\ty", "RAID", "Stranger")
    assert list(me.g.INVITED.values()) == []


def test_teammates_are_never_customers():
    me, bone = pair()
    say_trade(me, "Yeet Lock", "wtb summon to TB")
    assert list(me.g.INVITED.values()) == [] and me.sent() == []


def test_a_warlock_teammate_says_where_they_stand():
    me = world({"player": ME, "raid1": ("Yeet Lock", "WARLOCK", 60, None)}, "summons = { price = 35 }", extra=COMMS)
    me.run('SlashCmdList.SERVICEINVITER("team add Yeet Lock")')
    say_trade(me, "Kaldrok", "wtb summon to UC")
    assert list(me.g.INVITED.values()) == []                       # the game doesn't say where Yeet is
    me.event("CHAT_MSG_ADDON", "SvcInv1", "HI\t3.1.0\t1\tUndercity\t", "RAID", "Yeet Lock")
    say_trade(me, "Mirasha", "wtb summon to UC")
    assert list(me.g.INVITED.values()) == ["Mirasha"]


def test_setup_saves_the_team_point_of_contact_routes_and_price_mode():
    g = world({"player": ME, "raid1": BONE, "raid2": YEET}, "summons = { price = 50 }", extra=COMMS)
    g.run('''S = ServiceInviter_Test.BuildSetup() S:Show() S.Load()
        local b, c = ServiceInviter_Test.SetupBoxes(), ServiceInviter_Test.SetupChecks()
        b.team:SetText("Bone Charms, Yeet Lock") b.poc:SetText("Bone Charms")
        c.route_scam_group:SetChecked(false) c.route_scam_off:SetChecked(true)
        c.pm_ignore:SetChecked(false) c.pm_match:SetChecked(true) b.floor:SetText("25")
        S.Save()''')
    assert g.eval('ServiceInviter_Test.Jobs.IsTeam("bone charms")') is True
    assert g.eval("ServiceInviterDB.team.poc") == "Bone Charms"
    assert g.eval('ServiceInviter_Test.Jobs.RouteOf("scam")') == "off"
    assert g.eval('ServiceInviter_Test.Jobs.RouteOf("welcome")') == "whisper"   # team default, not stored
    assert g.eval("ServiceInviterDB.route.welcome") is None
    assert g.eval("ServiceInviterDB.services.summons.mode") == "match" and g.eval("ServiceInviterDB.services.summons.floor") == 25


def test_match_charges_the_rivals_price():
    me, bone = pair("summons = { price = 50, mode = 'match', floor = 25 }")
    say_trade(me, "Rival", "WTS summons to TB 40s")
    say_trade(me, "Kaldrok", "wtb summon to TB")
    pump(me, bone, "Me")
    assert bone.eval('ServiceInviter_Test.Jobs.Get("Kaldrok").price') == 40


def test_solo_keeps_todays_message_routes():
    g = world({"player": ME, "raid1": YEET}, "summons = { price = 35 }")
    assert g.eval('ServiceInviter_Test.Jobs.RouteOf("welcome")') == "group"
