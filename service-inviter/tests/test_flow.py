"""The owner's flow, 14 Nov 2026, end to end with two copies in one guild: 1 (Me) and 2 (Bone
Charms, the point of contact) both listen; Bone whispers each buyer the service and price as he
invites them; on joining, only a regular hears more; the summon-starting line and the arrival
(pay who, how much, and that a blessing can be asked for) go by whisper; and either of us can mark
a non-payer, which the other's list shows."""
from test_guild import guild_world, drain
from test_team import pump, teamlog
from test_group import say_trade

ME = ("Me", "PALADIN", 60, "Thunder Bluff")
BONE = ("Bone Charms", "PRIEST", 60, "Thunder Bluff")
YEET = ("Yeet Lock", "WARLOCK", 60, "Thunder Bluff")


def team():
    me = guild_world({"player": ME, "raid1": BONE, "raid2": YEET}, "summons = { price = 35 }, blessing = { on = true, price = 10 }")
    bone = guild_world({"player": BONE, "raid1": ME, "raid2": YEET}, "summons = { price = 35 }, blessing = { on = true, price = 10 }")
    for g in (me, bone):
        g.run('SlashCmdList.SERVICEINVITER("team poc Bone Charms")')
        g.run("ServiceInviter_Test.Jobs.SayHi(true)")
    pump(me, bone, "Me")
    pump(bone, me, "Bone Charms")
    return me, bone


def join(g, name):
    g.run(f'UNITS.raid3 = {{ "{name}", "MAGE", 44, "Orgrimmar" }} GROUP["{name}"] = true')
    g.event("CHAT_MSG_SYSTEM", f"{name} has joined the raid group.")


def test_the_whole_flow():
    me, bone = team()
    say_trade(me, "Kaldrok", "wtb summon to TB")           # 1 hears it
    pump(me, bone, "Me")                                  # handed to 2
    assert list(bone.g.INVITED.values()) == ["Kaldrok"]
    first = bone.sent()
    assert first == [("WHISPER", "Kaldrok", "Hi Kaldrok! Yeet Lock will summon you to TB. 35 silver. Pay Yeet Lock when you land.")]
    for g in (me, bone):
        join(g, "Kaldrok")
    assert bone.sent() == first and me.sent() == []         # not a regular: nothing more on joining
    for g in (me, bone):
        g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "raid2", 698, "Ritual of Summoning")')
    alert = bone.sent()[len(first):]
    assert alert and alert[0][:2] == ("WHISPER", "Kaldrok") and "PAY Yeet Lock 35 silver" in alert[0][2]
    bone.run('UNITS.raid3[4] = "Thunder Bluff" CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()')
    landed = bone.sent()[-1]
    assert landed == ("WHISPER", "Kaldrok", "Welcome to TB, Kaldrok! Please pay Yeet Lock 35 silver. Also here: free blessings. Just ask!")
    assert me.sent() == []                                  # only the point of contact talks


def test_a_regular_hears_the_regulars_line_on_joining():
    me, bone = team()
    bone.run('ServiceInviterDB.customers = { Kaldrok = { n = 4, by = { summons = 4 }, worth = 140, first = 1, last = 2, to = {} } }')
    say_trade(bone, "Kaldrok", "wtb summon to TB")
    join(bone, "Kaldrok")
    said = [m for _, _, m in bone.sent()]
    assert len(said) == 2 and "Welcome back" in said[1] and "35 silver" not in said[1]


def test_either_of_us_marks_a_non_payer_and_the_other_list_shows_it():
    me, bone = team()
    say_trade(me, "Kaldrok", "wtb summon to TB")
    pump(me, bone, "Me")
    for g in (me, bone):
        join(g, "Kaldrok")
    me.run('SlashCmdList.SERVICEINVITER("scam Kaldrok")')   # 1 marks him; 2 invited him
    pump(me, bone, "Me")                                    # my hello says my book moved
    pump(bone, me, "Bone Charms")                           # Bone asks for it
    drain(me, bone, "Me")
    assert bone.status("Kaldrok") == "scammed"
    assert any("Me marked Kaldrok as not paying" in p for p in bone.printed())


def test_the_pay_reminder_can_be_turned_off():
    me, bone = team()
    bone.run('ServiceInviterDB.opts.payremind = false')
    say_trade(me, "Kaldrok", "wtb summon to TB")
    pump(me, bone, "Me")
    for g in (me, bone):
        join(g, "Kaldrok")
    for g in (me, bone):
        g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "raid2", 698, "Ritual of Summoning")')
    bone.run('UNITS.raid3[4] = "Thunder Bluff" CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()')
    landed = bone.sent()[-1]
    assert landed == ("WHISPER", "Kaldrok", "Also here: free blessings. Just ask!")   # the Arrival box, as written


def test_a_buyer_i_invite_by_hand_is_welcomed_by_the_point_of_contact():
    me, bone = team()
    me.run('ServiceInviterDB.opts.enabled = false')       # my copy invites nobody by itself
    say_trade(me, "Kaldrok", "wtb summon to TB")
    me.run('C_PartyInfo.InviteUnit("Kaldrok")')          # I invite him by hand
    pump(me, bone, "Me")
    assert "invited Kaldrok by hand: summons to Thunder Bluff, 35s" in teamlog(bone)
    # quoted as he's invited, the same welcome the addon's own invites get
    assert bone.sent() == [("WHISPER", "Kaldrok", "Hi Kaldrok! Yeet Lock will summon you to TB. 35 silver. Pay Yeet Lock when you land.")]
    for g in (me, bone):
        join(g, "Kaldrok")
    assert me.sent() == [] and len(bone.sent()) == 1           # not a regular: nothing more on joining


def test_only_the_point_of_contact_whispers_the_helper_even_by_battle_net():
    """The owner, 14 Nov 2026: "only the POC will whisper the lock who is next?"."""
    me, bone = team()
    for g in (me, bone):
        g.run('''ServiceInviterDB.role = "helper" ServiceInviterDB.whisperto = "Yeet Lock"
            BN_SENT = {} function BNSendWhisper(id, t) BN_SENT[#BN_SENT + 1] = t end
            function BNGetNumFriends() return 1 end
            C_BattleNet = { GetFriendAccountInfo = function() return { accountName = "Yeet Lock", battleTag = "Yeet#1",
                gameAccountInfo = { characterName = "Yeet Lock", isOnline = true } , bnetAccountID = 7 } end }''')
    say_trade(me, "Kaldrok", "wtb summon to TB")
    pump(me, bone, "Me")
    for g in (me, bone):
        join(g, "Kaldrok")
        g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "raid2", 698, "Ritual of Summoning")')
    mine = me.eval("#BN_SENT") + len([1 for ch, to, m in me.sent() if to == "Yeet Lock"])
    assert mine == 0
    his = bone.eval("#BN_SENT") + len([1 for ch, to, m in bone.sent() if to == "Yeet Lock"])
    assert his == 1


def test_the_point_of_contact_raid_warns_a_regular_and_a_non_payer():
    """The owner, 14 Nov 2026: "a regular and a scammer should be raid warned or whatever by POC"."""
    me, bone = team()
    for g in (me, bone):
        g.run('function UnitIsGroupLeader(u) return u == "player" end '
              'ServiceInviterDB.route = { loyal = "group", scam = "group" } '
              'ServiceInviterDB.customers = { Kaldrok = { n = 3, by = { summons = 3 }, worth = 105, first = 1, last = 2, to = {} } } '
              'ServiceInviterDB.scammers = { Sneaky = { n = 1, last = 5 } }')
    for g in (me, bone):
        join(g, "Kaldrok")
        g.run('UNITS.raid4 = { "Sneaky", "ROGUE", 40, "Thunder Bluff" } GROUP["Sneaky"] = true')
        g.event("CHAT_MSG_SYSTEM", "Sneaky has joined the raid group.")
    assert me.sent() == []                                   # only the point of contact
    warned = [m for ch, _, m in bone.sent() if ch == "RAID_WARNING"]
    assert any("Welcome back Kaldrok" in m for m in warned) and any("Sneaky" in m for m in warned)


def test_the_point_of_contact_invites_someone_i_invited_by_hand():
    """The owner, 15 Nov 2026: "it is not actually inviting them but the addon says it is in the
    queue" -- a muted character's invite to a stranger doesn't go through."""
    me, bone = team()
    me.run('ServiceInviterDB.opts.enabled = false')
    say_trade(me, "Kaldrok", "wtb summon to TB")
    me.run('C_PartyInfo.InviteUnit("Kaldrok")')
    pump(me, bone, "Me")
    assert "Kaldrok" in list(bone.g.INVITED.values())
