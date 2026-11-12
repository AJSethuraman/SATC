"""The buff button: one key that always casts the right buff on the next person who needs it.
The owner, 12 Nov 2026: "can it be like... queued to a single button somehow that always goes to
the last person or someone who asks for it" ... "it would not need to be in combat used ever
really - this is really just for buffs"."""
from test_group import world, say_trade

PRIEST_TB = {"player": ("Me", "PRIEST", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}
SPELLS = """
CASTS = {}
function GetSpellSubtext(s) if s == "Power Word: Fortitude" then return "Rank 6" end end
"""


def macro(g):
    return g.eval('ServiceInviterBuffButton:GetAttribute("macrotext")')


def label(g):
    return g.eval("ServiceInviter_Test.BuffLabel()")


def arrive(g, name):
    g.run(f'''local J = ServiceInviter_Test.Jobs J.Joined("{name}") J.Set("{name}", "summoned")
             UNITS.party2 = {{ "{name}", "MAGE", 44, "Thunder Bluff" }} GROUP["{name}"] = true
             CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()''')


def test_a_customer_landing_where_you_are_is_queued_for_your_buff():
    g = world(PRIEST_TB, "fort = { on = true }", extra=SPELLS)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    arrive(g, "Kaldrok")
    assert macro(g) == "/cast [@Kaldrok] Power Word: Fortitude"
    assert label(g) == "Fortitude -> Kaldrok"


def test_someone_asking_in_party_is_queued():
    g = world(PRIEST_TB, "fort = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "can i get fort pls", "Grimtotem", "", "", "", "", "", "", "")
    assert macro(g) == "/cast [@Grimtotem] Power Word: Fortitude"


def test_a_successful_cast_moves_to_the_next_person():
    g = world(PRIEST_TB, "fort = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "fort?", "Grimtotem", "", "", "", "", "", "", "")
    g.event("CHAT_MSG_WHISPER", "stam buff pls", "Grimtotem", "", "", "", "", "", "", "")   # already queued: no double
    say_trade(g, "Kaldrok", "WTB summon to TB")
    arrive(g, "Kaldrok")
    assert label(g) == "Fortitude -> Grimtotem (+1)"
    g.event("UNIT_SPELLCAST_SUCCEEDED", "player", "cast-guid", 0, "Power Word: Fortitude")
    assert macro(g) == "/cast [@Kaldrok] Power Word: Fortitude"
    g.event("UNIT_SPELLCAST_SUCCEEDED", "player", "cast-guid", 0, "Power Word: Fortitude")
    assert label(g) == "No buffs waiting"


def test_too_low_level_steps_down_a_rank():
    g = world(PRIEST_TB, "fort = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "fort pls", "Grimtotem", "", "", "", "", "", "", "")
    g.event("UI_ERROR_MESSAGE", 50, "Target is too low level")
    assert macro(g) == "/cast [@Grimtotem] Power Word: Fortitude(Rank 5)"
    g.event("UI_ERROR_MESSAGE", 50, "Target is too low level")
    assert macro(g) == "/cast [@Grimtotem] Power Word: Fortitude(Rank 4)"


def test_nothing_queued_for_buffs_you_cant_cast():
    g = world({"player": ("Me", "SHAMAN", 60, "Thunder Bluff")}, "fort = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "fort pls", "Grimtotem", "", "", "", "", "", "", "")
    assert label(g) == "No buffs waiting"


def test_someone_who_leaves_drops_out_of_the_queue():
    g = world(PRIEST_TB, "fort = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "fort pls", "Grimtotem", "", "", "", "", "", "", "")
    g.run('GROUP["Grimtotem"] = nil UNITS.party1 = nil ServiceInviter_Test.RefreshBuff()')
    assert label(g) == "No buffs waiting"


def test_blessing_uses_the_one_you_chose():
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")},
              'blessing = { on = true, spell = "Blessing of Wisdom" }', extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "wisdom pls", "Grimtotem", "", "", "", "", "", "", "")
    assert macro(g) == "/cast [@Grimtotem] Blessing of Wisdom"


def test_si_bind_buff():
    g = world(PRIEST_TB, extra=SPELLS + "BOUND = {} function SetBindingClick(k, b) BOUND[k] = b return true end")
    g.eval('SlashCmdList.SERVICEINVITER("bind buff F8")')
    assert g.eval("BOUND.F8") == "ServiceInviterBuffButton"


def test_opening_the_list_later_still_shows_the_buff_button():
    """Found by looking at the drawn window: people asked before the list was open, and the
    button stayed hidden."""
    g = world(PRIEST_TB, "fort = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "fort pls", "Grimtotem", "", "", "", "", "", "", "")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterJobs.buffBtn:IsShown()") is True
    assert g.eval("ServiceInviterJobs.buffBtn:GetText()") == "Fortitude -> Grimtotem"


# -- Paladins: the word picks the blessing --------------------------------------------------
# The owner: "so if im a paladin how will it work? can they say wisdom or something and it knows
# to queue that".

PALADIN_TB = {"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
              "party2": ("Kaldrok", "ROGUE", 44, "Thunder Bluff")}
KNOWN = SPELLS + """
KNOWN = { ["Blessing of Might"] = true, ["Blessing of Wisdom"] = true, ["Blessing of Salvation"] = true }
function GetSpellInfo(s) if type(s) == "string" and KNOWN[s] then return s end end
"""


def party(g, who, text):
    g.event("CHAT_MSG_PARTY", text, who, "", "", "", "", "", "", "")


def test_wisdom_queues_blessing_of_wisdom():
    g = world(PALADIN_TB, "blessing = { on = true }", extra=KNOWN)
    party(g, "Grimtotem", "can i get wisdom pls")
    assert macro(g) == "/cast [@Grimtotem] Blessing of Wisdom"
    assert label(g) == "Wisdom -> Grimtotem"


def test_each_person_gets_the_blessing_they_asked_for():
    g = world(PALADIN_TB, "blessing = { on = true }", extra=KNOWN)
    party(g, "Grimtotem", "wisdom?")
    party(g, "Kaldrok", "might pls")
    assert macro(g) == "/cast [@Grimtotem] Blessing of Wisdom"
    g.event("UNIT_SPELLCAST_SUCCEEDED", "player", "g", 0, "Blessing of Wisdom")
    assert macro(g) == "/cast [@Kaldrok] Blessing of Might"


def test_just_blessing_gets_the_one_set_on_the_buffs_tab():
    g = world(PALADIN_TB, 'blessing = { on = true, spell = "Blessing of Salvation" }', extra=KNOWN)
    party(g, "Grimtotem", "blessing pls")
    assert macro(g) == "/cast [@Grimtotem] Blessing of Salvation"


def test_asking_again_switches_their_blessing_instead_of_adding_one():
    g = world(PALADIN_TB, "blessing = { on = true }", extra=KNOWN)
    party(g, "Grimtotem", "wisdom pls")
    party(g, "Grimtotem", "actually might")
    assert macro(g) == "/cast [@Grimtotem] Blessing of Might"
    assert label(g) == "Might -> Grimtotem"


def test_a_blessing_you_dont_have_is_not_queued_and_you_are_told():
    g = world(PALADIN_TB, "blessing = { on = true }", extra=KNOWN)
    party(g, "Grimtotem", "kings pls")
    assert label(g) == "No buffs waiting"
    assert any("Blessing of Kings" in line for line in g.printed())


def test_everyday_sentences_with_might_or_light_are_not_requests():
    g = world(PALADIN_TB, "blessing = { on = true }", extra=KNOWN)
    party(g, "Grimtotem", "i might be afk for a few minutes")
    party(g, "Kaldrok", "it is getting light out here in the barrens")
    assert label(g) == "No buffs waiting"
    party(g, "Kaldrok", "might pls")          # control: a short ask still counts
    assert label(g) == "Might -> Kaldrok"
