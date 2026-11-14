"""The guild is the team, and the copies share their books. The owner, 14 Nov 2026: "how will it
save and share out customers?", "i think guild is good i like that", and "i want as much to work
through guild as possible - like the idea of this being a 'community' addon. so auto detect and
stuff should work from guild and understand if guild is in party it is not a customer"."""
from test_group import world, say_trade
from test_team import COMMS, pump, teamlog

GUILD = COMMS + """
function IsInGuild() return true end
ROSTER = { "Me-Forever", "Bone Charms-Forever", "Grandma-Forever" }
function GetNumGuildMembers() return #ROSTER end
function GetGuildRosterInfo(i) return ROSTER[i] end
"""
ME = ("Me", "SHAMAN", 60, "Thunder Bluff")
BONE = ("Bone Charms", "WARLOCK", 60, "Thunder Bluff")


def guild_world(units, services="summons = { price = 35 }"):
    g = world(units, services, extra=GUILD)
    g.run('ServiceInviterDB.opts = { marks = false }')
    g.event("GUILD_ROSTER_UPDATE")
    return g


def two():
    """Me and Bone, in the same guild, not grouped, no team list typed by anyone."""
    me = guild_world({"player": ME})
    bone = guild_world({"player": BONE})
    for g in (me, bone):
        g.run("ServiceInviter_Test.Jobs.SayHi(true)")
    pump(me, bone, "Me")
    pump(bone, me, "Bone Charms")
    return me, bone


def drain(src, dst, sender, rounds=6):
    """Let src answer what it was asked, a line at a time, and deliver it."""
    for _ in range(rounds):
        src.run("CLOCK = CLOCK + 3 ServiceInviter_Test.Jobs.BookTick()")
        src.run("while #ServiceInviter_Test.Jobs.outbox > 0 do ServiceInviter_Test.Jobs.Drain() end")
        pump(src, dst, sender)
        pump(dst, src, "Me" if sender != "Me" else "Bone Charms")


def test_a_guildmate_in_the_party_is_not_a_customer_addon_or_not():
    g = guild_world({"player": ME, "raid1": ("Grandma", "PRIEST", 60, "Thunder Bluff"),
                     "raid2": ("Yeet Lock", "WARLOCK", 60, "Thunder Bluff")})
    g.event("CHAT_MSG_SYSTEM", "Grandma joins the party.")
    assert g.eval('ServiceInviter_Test.Jobs.Get("Grandma")') is None
    say_trade(g, "Grandma", "wtb summon to TB")
    assert list(g.g.INVITED.values()) == []
    # someone outside the guild is a customer as always
    say_trade(g, "Kaldrok", "wtb summon to TB")
    assert list(g.g.INVITED.values()) == ["Kaldrok"]


def test_guildmates_running_it_find_each_other_with_nothing_typed():
    me, bone = two()
    assert me.eval('ServiceInviter_Test.Jobs.IsTeam("Bone Charms")')
    assert bone.eval('ServiceInviter_Test.Jobs.IsTeam("Me")')
    assert "sent to guild: here" in teamlog(me)


def test_the_box_turns_it_off():
    g = world({"player": ME, "raid1": ("Grandma", "PRIEST", 60, "Thunder Bluff")}, "summons = { price = 35 }", extra=GUILD)
    g.run('ServiceInviterDB.opts = { marks = false, guildteam = false }')
    g.event("GUILD_ROSTER_UPDATE")
    assert not g.eval('ServiceInviter_Test.Jobs.InMyGuild("Grandma")')
    assert not g.eval('ServiceInviter_Test.Jobs.TeamOn()')


BOOK = """ServiceInviterDB.customers = {
  Kaldrok = { n = 3, by = { summons = 3 }, worth = 105, first = 100, last = 900, to = { ["Thunder Bluff"] = 3 } },
  ["Momma Lovesme"] = { n = 1, by = { summons = 1 }, worth = 35, first = 200, last = 200, to = { Undercity = 1 } } }
ServiceInviterDB.scammers = { Sneaky = { n = 1, owed = 35, last = 500 } }
ServiceInviterDB.analytics = { n = 4, worth = 140, since = 100, to = { ["Thunder Bluff"] = 3, Undercity = 1 },
  by = { summons = 4 }, hour = { [20] = 4 }, day = { [6] = 4 }, near = { n = 2, worth = 70, why = { ["out of shards"] = 2 }, to = {} } }"""


def test_my_book_reaches_my_guildmate_and_their_lists_count_it():
    me = guild_world({"player": ME})
    me.run(BOOK)
    bone = guild_world({"player": BONE, "raid1": ("Yeet Lock", "WARLOCK", 60, "Thunder Bluff")})
    for g in (me, bone):
        g.run("ServiceInviter_Test.Jobs.SayHi(true)")
    pump(me, bone, "Me")          # my hello: my book is at change 4
    pump(bone, me, "Bone Charms")  # Bone's hello, and his WANT
    drain(me, bone, "Me")
    assert bone.eval('ServiceInviterDB.teambooks["Me"].rev') == 4
    assert bone.eval('ServiceInviter_Test.Jobs.Book()["Kaldrok"].n') == 3
    assert bone.eval('ServiceInviter_Test.Jobs.Book()["Kaldrok"].to["Thunder Bluff"]') == 3
    assert bone.eval('ServiceInviter_Test.Jobs.Analytics().hour[20]') == 4
    assert bone.eval('ServiceInviter_Test.Jobs.Analytics().near.why["out of shards"]') == 2
    # my non-payer is his too: never invited
    assert bone.eval('ServiceInviter_Test.Jobs.Scammer("Sneaky")')
    say_trade(bone, "Sneaky", "wtb summon to TB")
    assert list(bone.g.INVITED.values()) == []
    # and a regular of mine is a regular to him
    say_trade(bone, "Kaldrok", "wtb summon to TB")
    assert bone.eval('ServiceInviter_Test.Jobs.Before(ServiceInviter_Test.Jobs.Get("Kaldrok"))') == 3
    assert "their book is up to date (change 4)" in teamlog(bone)


def test_a_new_change_reaches_them_without_resending_the_rest():
    me, bone = two()
    me.run('ServiceInviterDB.customers = { Old = { n = 1, by = {}, worth = 0, first = 1, last = 1, to = {} } }')
    me.run("ServiceInviterDB.bookrev = nil ServiceInviter_Test.Jobs.BookRev()")
    me.run("ServiceInviter_Test.Jobs.SayHi(false)")
    pump(me, bone, "Me")
    pump(bone, me, "Bone Charms")
    drain(me, bone, "Me")
    assert bone.eval('ServiceInviterDB.teambooks["Me"].rev') == 1
    me.run('SlashCmdList.SERVICEINVITER("scam Newguy")')   # change 2
    me.run("CLOCK = CLOCK + 15 ServiceInviter_Test.Jobs.BookTick()")   # says hello with the new number
    me.run("ADDON_OUT_COPY = ADDON_OUT")
    pump(me, bone, "Me")
    pump(bone, me, "Bone Charms")
    me.run("CLOCK = CLOCK + 3 ServiceInviter_Test.Jobs.BookTick()")
    lines = me.eval("#ServiceInviter_Test.Jobs.outbox")
    assert lines == 2                                       # the one entry, then END
    drain(me, bone, "Me")
    assert bone.eval('ServiceInviter_Test.Jobs.Scammer("Newguy")')


def test_paid_after_all_on_any_copy_clears_it_for_everyone():
    me = guild_world({"player": ME})
    me.run(BOOK)
    bone = guild_world({"player": BONE})
    for g in (me, bone):
        g.run("ServiceInviter_Test.Jobs.SayHi(true)")
    pump(me, bone, "Me")
    pump(bone, me, "Bone Charms")
    drain(me, bone, "Me")
    bone.run('SlashCmdList.SERVICEINVITER("unscam Sneaky")')   # Bone clears my entry
    assert bone.eval('ServiceInviter_Test.Jobs.Scammer("Sneaky")') is None
    bone.run("CLOCK = CLOCK + 15 ServiceInviter_Test.Jobs.BookTick()")
    pump(bone, me, "Bone Charms")
    pump(me, bone, "Me")
    drain(bone, me, "Bone Charms")
    assert me.eval('ServiceInviter_Test.Jobs.Scammer("Sneaky")') is None


def test_a_visit_is_recorded_once_on_a_team():
    """Only the point of contact writes it down, so two books never count one summon twice."""
    me = guild_world({"player": ME, "raid1": BONE})
    bone = guild_world({"player": BONE, "raid1": ME})
    for g in (me, bone):
        g.run("ServiceInviter_Test.Jobs.SayHi(true)")
        g.run('SlashCmdList.SERVICEINVITER("team poc Me")')
    pump(me, bone, "Me")
    pump(bone, me, "Bone Charms")
    for g in (me, bone):
        g.run('ServiceInviter_Test.Jobs.New("Kaldrok", "(joined your group)", "invited by someone else", "-")')
        g.run('ServiceInviter_Test.Jobs.Set("Kaldrok", "summoned")')
    assert me.eval('ServiceInviterDB.customers["Kaldrok"].n') == 1
    assert bone.eval('ServiceInviterDB.customers') is None or bone.eval('ServiceInviterDB.customers["Kaldrok"]') is None


def test_a_big_book_is_sent_once_even_when_asked_again_mid_way():
    """The owner's 310 customers, 14 Nov 2026: "this would indicate he did not get my customer
    list". Asked again while it was still going out, the whole book used to be queued again."""
    me = guild_world({"player": ME})
    me.run('ServiceInviterDB.customers = {} for i = 1, 300 do ServiceInviterDB.customers["Buyer" .. i] = '
           '{ n = 1, by = { summons = 1 }, worth = 35, first = i, last = i, to = { ["Thunder Bluff"] = 1 } } end')
    bone = guild_world({"player": BONE})
    for g in (me, bone):
        g.run("ServiceInviter_Test.Jobs.SayHi(true)")
    pump(me, bone, "Me")
    pump(bone, me, "Bone Charms")                     # his WANT
    me.run("CLOCK = CLOCK + 3 ServiceInviter_Test.Jobs.BookTick()")
    queued = me.eval("#ServiceInviter_Test.Jobs.outbox")
    for _ in range(3):                               # he asks again, twice, while it's going out
        me.run("for i = 1, 40 do ServiceInviter_Test.Jobs.Drain() end")
        pump(me, bone, "Me")
        for g in (me, bone):
            g.run("CLOCK = CLOCK + 30")
        me.run("ServiceInviter_Test.Jobs.SayHi(false)")       # my hello: my book's number
        pump(me, bone, "Me")
        pump(bone, me, "Bone Charms")                        # he hasn't got it all yet: he asks again
        me.run("CLOCK = CLOCK + 3 ServiceInviter_Test.Jobs.BookTick()")
    assert me.eval("#ServiceInviter_Test.Jobs.outbox") < queued      # not piled up again
    drain(me, bone, "Me", rounds=20)
    n = bone.eval('(function() local n = 0 for _ in pairs(ServiceInviterDB.teambooks["Me"].customers) do n = n + 1 end return n end)()')
    assert n == 300
    assert any("got Me's customer book: 300 customers" in p for p in bone.printed())
