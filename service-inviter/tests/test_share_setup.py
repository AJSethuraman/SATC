"""Send my setup (the owner, 14 Nov 2026: "how do i 'share my setup' or whatever?"). Messages,
channels, the ad, prices and the team go to the team; each copy says Use it or No. What's about
one person stays put."""
from test_team import pair, pump


def send(src, dst, sender):
    src.run("while #ServiceInviter_Test.Jobs.outbox > 0 do CLOCK = CLOCK + 2 ServiceInviter_Test.Jobs.Drain() end")
    pump(src, dst, sender)


LONG = "Hi {name}! " + "x" * 300


def mine(me):
    me.run(f'''ServiceInviterDB.welcomemsg = "{LONG}" ServiceInviterDB.admsg = "WTS {{services}} pst"
        ServiceInviterDB.services.summons = {{ price = 50, floor = 30, mode = "undercut", undercut = 5, on = true, invite = true }}
        ServiceInviterDB.route = {{ thanks = "off" }} ServiceInviterDB.opts.general = false
        ServiceInviterDB.role = "lock" ServiceInviterDB.dryrun = true ServiceInviterDB.whisperto = "Helper"''')


def test_my_setup_reaches_my_friend_who_says_use_it():
    me, bone = pair()
    mine(me)
    me.run("ServiceInviter_Test.Jobs.ShareSetup()")
    send(me, bone, "Me")
    assert bone.eval("ServiceInviterSetupAsk:IsShown()")
    assert bone.eval("ServiceInviterSetupAsk.title:GetText()") == "Me sent their setup. Use it?"
    bone.run("ServiceInviterSetupAsk.use._scripts.OnClick()")
    assert bone.eval("ServiceInviterDB.welcomemsg") == LONG                 # long text arrives whole
    assert bone.eval("ServiceInviterDB.admsg") == "WTS {services} pst"
    assert bone.eval("ServiceInviterDB.services.summons.price") == 50
    assert bone.eval("ServiceInviterDB.services.summons.floor") == 30
    assert bone.eval("ServiceInviterDB.route.thanks") == "off"
    assert bone.eval("ServiceInviterDB.opts.general") is False
    assert bone.eval("ServiceInviterDB.team.poc") == "Bone Charms"
    # his own stays his
    assert bone.eval("ServiceInviterDB.role") != "lock"
    assert not bone.eval("ServiceInviterDB.dryrun")
    assert bone.eval("ServiceInviterDB.whisperto") != "Helper"


def test_no_keeps_his_own():
    me, bone = pair()
    mine(me)
    me.run("ServiceInviter_Test.Jobs.ShareSetup()")
    send(me, bone, "Me")
    bone.run("ServiceInviterSetupAsk.no._scripts.OnClick()")
    assert bone.eval("ServiceInviterDB.welcomemsg") != LONG


def test_use_it_without_asking():
    me, bone = pair()
    bone.run("ServiceInviterDB.takesetup = true")
    mine(me)
    me.run("ServiceInviter_Test.Jobs.ShareSetup()")
    send(me, bone, "Me")
    assert bone.eval("ServiceInviterDB.welcomemsg") == LONG
    assert not bone.eval("ServiceInviterSetupAsk and ServiceInviterSetupAsk:IsShown()")


def test_a_setup_with_a_piece_missing_is_not_used():
    me, bone = pair()
    bone.run("ServiceInviterDB.takesetup = true")
    mine(me)
    me.run("ServiceInviter_Test.Jobs.ShareSetup() table.remove(ServiceInviter_Test.Jobs.outbox, 1)")   # one line lost
    send(me, bone, "Me")
    assert bone.eval("ServiceInviterDB.welcomemsg") != LONG


def test_the_sender_hears_what_happened():
    """The owner, 14 Nov 2026: "i see it saying it sent them but nothing on his end is happening"."""
    me, bone = pair()
    mine(me)
    me.run("ServiceInviter_Test.Jobs.ShareSetup()")
    send(me, bone, "Me")
    pump(bone, me, "Bone Charms")
    assert any("Bone Charms got your setup and is being asked whether to use it" in p for p in me.printed())
    bone.run("ServiceInviterSetupAsk.use._scripts.OnClick()")
    pump(bone, me, "Bone Charms")
    assert any("Bone Charms is using your setup" in p for p in me.printed())


def test_the_ad_and_its_channels_go_too():
    """The owner, 15 Nov 2026: "does save setup also save advertise stuff"."""
    me, bone = pair()
    bone.run("ServiceInviterDB.takesetup = true")
    me.run('ServiceInviterDB.admsg = "WTS {services} pst" ServiceInviterDB.adwait = 3 '
           'ServiceInviterDB.adskip = { ["General - Thunder Bluff"] = true }')
    me.run("ServiceInviter_Test.Jobs.ShareSetup()")
    send(me, bone, "Me")
    assert bone.eval("ServiceInviterDB.admsg") == "WTS {services} pst"
    assert bone.eval("ServiceInviterDB.adwait") == 3
    assert bone.eval('ServiceInviterDB.adskip["General - Thunder Bluff"]') is True
