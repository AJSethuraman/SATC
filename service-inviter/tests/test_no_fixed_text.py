"""Every message a customer or the group gets is a text you can see and change in setup. The owner,
14 Nov 2026: "i dont want to communicate fixed text - not okay". Each box is set to a marker; a
customer goes through every step; anything sent that doesn't start with a marker was fixed text."""
from test_group import world, say_trade

UNITS = {"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}
MARKERS = '''ServiceInviterDB.welcomemsg = "WEL {name} {price}" ServiceInviterDB.askmsg = "ASK {name} {services}"
ServiceInviterDB.offermsg = "OFF {offers}" ServiceInviterDB.paymsg = "PAY {payee} {price}"
ServiceInviterDB.thanksmsg = "THX {name}" ServiceInviterDB.loyaltymsg = "REG {name}"
ServiceInviterDB.scammsg = "SCM {name}" ServiceInviterDB.alertmsg = "ALR {name} {dest}"
ServiceInviterDB.opts = { marks = false }'''
OK = ("WEL ", "ASK ", "OFF ", "PAY ", "THX ", "REG ", "SCM ", "ALR ")


def test_nothing_sent_is_fixed_text():
    g = world(UNITS, "summons = { price = 35 }, blessing = { on = true, price = 10 }")
    g.run(MARKERS)
    g.run('ServiceInviterDB.customers = { Kaldrok = { n = 2, by = { summons = 2 }, worth = 70, first = 1, last = 2, to = {} } }')
    # a regular buyer, start to finish
    say_trade(g, "Kaldrok", "wtb summon to TB")
    g.run('UNITS.party2 = { "Kaldrok", "MAGE", 40, "Orgrimmar" } GROUP["Kaldrok"] = true')
    g.event("CHAT_MSG_SYSTEM", "Kaldrok joins the party.")
    g.run('ServiceInviter_Test.OnCast("UNIT_SPELLCAST_START", "party1", 698, "Ritual of Summoning")')
    g.run('UNITS.party2[4] = "Thunder Bluff" CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()')
    g.run('local j = ServiceInviter_Test.Jobs.Get("Kaldrok") ServiceInviter_Test.Jobs.Set("Kaldrok", "paid")')
    g.run('ServiceInviter_Test.Jobs.Remove("Kaldrok")')
    # someone invited by hand who said nothing
    g.run('C_PartyInfo.InviteUnit("Friendo") UNITS.party3 = { "Friendo", "MAGE", 40, "Thunder Bluff" } GROUP["Friendo"] = true')
    g.event("CHAT_MSG_SYSTEM", "Friendo joins the party.")
    # a non-payer coming back
    g.run('ServiceInviterDB.scammers = { Sneaky = { n = 1, last = 5 } } UNITS.party4 = { "Sneaky", "ROGUE", 40, "Thunder Bluff" } GROUP["Sneaky"] = true')
    g.event("CHAT_MSG_SYSTEM", "Sneaky joins the party.")
    sent = [m for _, _, m in g.sent()]
    kinds = {m[:4] for m in sent}
    assert {"WEL ", "OFF ", "PAY ", "ASK ", "SCM ", "ALR "} <= kinds | {k for m in sent for k in OK if k.strip() in m}, sent
    fixed = [m for m in sent if not any(k.strip() in m for k in OK)]
    assert fixed == [], fixed
