"""The buff button: one key that always casts the right buff on the next person who needs it.
The owner, 12 Nov 2026: "can it be like... queued to a single button somehow that always goes to
the last person or someone who asks for it" ... "it would not need to be in combat used ever
really - this is really just for buffs"."""
from test_group import world, say_trade

PRIEST_TB = {"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")}   # (a paladin since 14 Nov 2026: summons and blessings only)
SPELLS = """
CASTS = {}
function GetSpellSubtext(s) if s == "Blessing of Might" then return "Rank 6" end end
"""


def macro(g):
    """The buff macro, with the group slot it casts on read back as the person's name."""
    import re
    m = g.eval('ServiceInviterBuffButton:GetAttribute("macrotext")') or ""
    def name(u):
        unit = g.g.UNITS[u.group(1)]
        return "[@" + (unit[1] if unit else u.group(1)) + "]"
    return re.sub(r"\[@((?:party|raid)\d+)\]", name, m)


def raw_macro(g):
    return g.eval('ServiceInviterBuffButton:GetAttribute("macrotext")')


def label(g):
    return g.eval("ServiceInviter_Test.BuffLabel()")


def arrive(g, name):
    g.run(f'''local J = ServiceInviter_Test.Jobs J.Joined("{name}") J.Set("{name}", "summoned")
             UNITS.party2 = {{ "{name}", "MAGE", 44, "Thunder Bluff" }} GROUP["{name}"] = true
             CLOCK = CLOCK + 2 ServiceInviter_Test.CheckArrivals()''')


def test_a_customer_landing_where_you_are_is_queued_for_your_buff():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    arrive(g, "Kaldrok")
    assert macro(g) == "/cast [@Kaldrok] Blessing of Might"
    assert label(g) == "Might -> Kaldrok"


def test_someone_asking_in_party_is_queued():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "can i get might pls", "Grimtotem", "", "", "", "", "", "", "")
    assert macro(g) == "/cast [@Grimtotem] Blessing of Might"


def test_a_successful_cast_moves_to_the_next_person():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "might?", "Grimtotem", "", "", "", "", "", "", "")
    g.event("CHAT_MSG_WHISPER", "might please", "Grimtotem", "", "", "", "", "", "", "")   # already queued: no double
    say_trade(g, "Kaldrok", "WTB summon to TB")
    arrive(g, "Kaldrok")
    assert label(g) == "Might -> Grimtotem (+1)"
    g.event("UNIT_SPELLCAST_SUCCEEDED", "player", "cast-guid", 0, "Blessing of Might")
    assert macro(g) == "/cast [@Kaldrok] Blessing of Might"
    g.event("UNIT_SPELLCAST_SUCCEEDED", "player", "cast-guid", 0, "Blessing of Might")
    assert label(g) == "No buffs waiting"


def test_too_low_level_steps_down_a_rank():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "might pls", "Grimtotem", "", "", "", "", "", "", "")
    g.event("UI_ERROR_MESSAGE", 50, "Target is too low level")
    assert macro(g) == "/cast [@Grimtotem] Blessing of Might(Rank 5)"
    g.event("UI_ERROR_MESSAGE", 50, "Target is too low level")
    assert macro(g) == "/cast [@Grimtotem] Blessing of Might(Rank 4)"


def test_nothing_queued_for_buffs_you_cant_cast():
    g = world({"player": ("Me", "SHAMAN", 60, "Thunder Bluff")}, "blessing = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "might pls", "Grimtotem", "", "", "", "", "", "", "")
    assert label(g) == "No buffs waiting"


def test_someone_who_leaves_drops_out_of_the_queue():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "might pls", "Grimtotem", "", "", "", "", "", "", "")
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
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "might pls", "Grimtotem", "", "", "", "", "", "", "")
    g.run("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    assert g.eval("ServiceInviterJobs.buffBtn:IsShown()") is True
    assert g.eval("ServiceInviterJobs.buffBtn:GetText()") == "Might -> Grimtotem"


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



def test_a_two_part_name_asking_in_raid_is_queued_and_cast_on_their_slot():
    """The owner, 14 Nov 2026: "my friend in chat said wisdom in raid and it didnt seem to do
    anything" -- "all things must keep 2 part names in mind". UnitInRaid by name doesn't find a
    two-part name, so the group itself is checked, and the macro names the slot, not the name."""
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Yeet Lock", "WARLOCK", 60, "Thunder Bluff")},
              "blessing = { on = true }",
              extra=" function UnitInParty(n) return false end function UnitInRaid(n) return nil end")
    g.event("CHAT_MSG_RAID", "wisdom", "Yeet Lock-Forever")
    assert raw_macro(g) == "/cast [@party1] Blessing of Wisdom"
    assert any("buff queued: Blessing of Wisdom for Yeet Lock" in p for p in g.printed())


def test_blessing_switched_off_says_so_once():
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")})
    g.event("CHAT_MSG_RAID", "wisdom", "Grimtotem")
    g.event("CHAT_MSG_RAID", "kings", "Grimtotem")
    told = [p for p in g.printed() if "'We offer a blessing' is off" in p]
    assert len(told) == 1 and "Grimtotem asked for Blessing of Wisdom" in told[0]


def test_someone_with_a_two_part_name_already_in_the_group_is_not_invited_again():
    g = world({"player": ("Me", "SHAMAN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
               "party2": ("Momma Lovesme", "MAGE", 40, "Thunder Bluff")},
              extra=" function UnitInParty(n) return false end function UnitInRaid(n) return nil end")
    say_trade(g, "Momma Lovesme", "WTB summon to TB")
    assert list(g.g.INVITED.values()) == []


def test_untick_and_a_customer_who_lands_is_not_buffed_unless_they_ask():
    """The owner, 14 Nov 2026: "can i set it to not auto queue a blessing if they dont ask for one?"."""
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.run("ServiceInviterDB.opts = { buffarrivals = false }")
    say_trade(g, "Kaldrok", "WTB summon to TB")
    arrive(g, "Kaldrok")
    assert label(g) == "No buffs waiting"
    g.event("CHAT_MSG_PARTY", "might pls", "Kaldrok", "", "", "", "", "", "", "")
    assert label(g) == "Might -> Kaldrok"


# The owner, 14 Nov 2026: "can the blessing thing be more obvious what if i miss it? can it just
# appear at my mouse".

def test_the_buff_pops_up_at_the_mouse_with_a_sound_and_casts_on_click():
    g = world(PRIEST_TB, "blessing = { on = true }",
              extra=SPELLS + " function GetSpellTexture(s) if s == 'Blessing of Might' then return 'Interface/Might' end end SOUNDS = {} function PlaySound(s) SOUNDS[#SOUNDS + 1] = s end function GetCursorPosition() return 500, 300 end")
    g.event("CHAT_MSG_PARTY", "might pls", "Grimtotem", "", "", "", "", "", "", "")
    assert g.eval("ServiceInviterBuffPop:IsShown()")
    assert g.eval("ServiceInviterBuffPop.label:GetText()") == "Might -> Grimtotem"
    assert g.eval('ServiceInviterBuffPop:GetAttribute("macrotext")') == raw_macro(g)
    assert len(g.g.SOUNDS) == 1
    assert g.eval("ServiceInviterBuffPop.icon._tex") == "Interface/Might"     # the buff's own icon
    g.event("CHAT_MSG_PARTY", "might?", "Kaldrok", "", "", "", "", "", "", "")
    assert len(g.g.SOUNDS) == 1                                       # already up: no second sound


def test_the_pop_goes_away_when_nobody_is_waiting():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_PARTY", "might pls", "Grimtotem", "", "", "", "", "", "", "")
    g.event("UNIT_SPELLCAST_SUCCEEDED", "player", "cast-guid", 0, "Blessing of Might")
    assert not g.eval("ServiceInviterBuffPop:IsShown()")


def test_the_pop_can_be_turned_off():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.run("ServiceInviterDB.opts = { buffpop = false }")
    g.event("CHAT_MSG_PARTY", "might pls", "Grimtotem", "", "", "", "", "", "", "")
    assert not g.eval("ServiceInviterBuffPop and ServiceInviterBuffPop:IsShown()")


# The owner, 14 Nov 2026: "this guy left then asked for a buff" -- "it ignored him" -- "i want to
# offer a recent customer a buff if they have left".

def test_a_customer_who_left_can_still_ask_and_is_targeted_by_name():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    say_trade(g, "Momma Lovesme", "WTB summon to TB")                 # a customer on the list
    g.event("CHAT_MSG_WHISPER", "might pls", "Momma Lovesme", "", "", "", "", "", "", "")
    assert label(g) == "Might -> Momma Lovesme"
    assert raw_macro(g) == "/target Momma Lovesme\n/cast Blessing of Might\n/targetlasttarget"


def test_saying_it_nearby_works_too():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    say_trade(g, "Kaldrok", "WTB summon to TB")
    g.event("CHAT_MSG_SAY", "might?", "Kaldrok", "", "", "", "", "", "", "")
    assert label(g) == "Might -> Kaldrok"


def test_a_stranger_outside_the_group_is_still_ignored():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.event("CHAT_MSG_WHISPER", "might pls", "Randomguy", "", "", "", "", "", "", "")
    g.event("CHAT_MSG_SAY", "might pls", "Randomguy", "", "", "", "", "", "", "")
    assert label(g) == "No buffs waiting"


def test_a_customer_from_the_book_within_the_hour_counts_an_older_one_does_not():
    g = world(PRIEST_TB, "blessing = { on = true }", extra=SPELLS)
    g.run("ServiceInviterDB.customers = { Kaldrok = { n = 1, last = time() - 600 }, Oldie = { n = 1, last = time() - 7200 } }")
    g.event("CHAT_MSG_WHISPER", "might pls", "Oldie", "", "", "", "", "", "", "")
    assert label(g) == "No buffs waiting"
    g.event("CHAT_MSG_WHISPER", "might pls", "Kaldrok", "", "", "", "", "", "", "")
    assert label(g) == "Might -> Kaldrok"


# The owner, 14 Nov 2026: "can you make it so that blessing are recognized by fragments and stuff -
# this guy asked for wis".

import pytest


@pytest.mark.parametrize("ask, spell", [
    ("wis", "Blessing of Wisdom"), ("wis pls", "Blessing of Wisdom"), ("wisd?", "Blessing of Wisdom"),
    ("bow pls", "Blessing of Wisdom"), ("bok", "Blessing of Kings"), ("kin pls", "Blessing of Kings"),
    ("bom", "Blessing of Might"), ("mig", "Blessing of Might"), ("salv", "Blessing of Salvation"),
    ("sanc pls", "Blessing of Sanctuary"),
])
def test_short_forms_and_abbreviations_pick_the_blessing(ask, spell):
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")},
              "blessing = { on = true, words = \"blessing\" }")       # not in the Buyers say box
    g.event("CHAT_MSG_RAID", ask, "Grimtotem")
    assert raw_macro(g) == "/cast [@party1] " + spell


def test_ordinary_words_are_not_blessings():
    g = world({"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff")},
              "blessing = { on = true, words = \"blessing\" }")
    for said in ("wish me luck", "kind of lagging", "ok", "brb"):
        g.event("CHAT_MSG_RAID", said, "Grimtotem")
    assert label(g) == "No buffs waiting"


# The owner, 14 Nov 2026: "this guy asked for kings before loading in fully can it be set to cast
# when they are in range and i guess i can cancel somehow if they leave".

RANGE = " NEAR = {} function UnitInRange(u) local x = UNITS[u] return x ~= nil and NEAR[x[1]] == true, true end"
PALLY = {"player": ("Me", "PALADIN", 60, "Thunder Bluff"), "party1": ("Grimtotem", "WARLOCK", 60, "Thunder Bluff"),
         "party2": ("Kaldrok", "MAGE", 44, "Thunder Bluff")}


def test_the_pop_waits_until_they_are_in_range():
    g = world(PALLY, "blessing = { on = true }", extra=RANGE)
    g.event("CHAT_MSG_RAID", "kings", "Grimtotem")
    assert not g.eval("ServiceInviterBuffPop and ServiceInviterBuffPop:IsShown()")
    assert label(g).endswith("(not in range yet)")
    g.run("NEAR.Grimtotem = true CLOCK = CLOCK + 1 ServiceInviter_Test.Tick(1)")
    assert g.eval("ServiceInviterBuffPop:IsShown()")
    assert g.eval("ServiceInviterBuffPop.label:GetText()") == "Kings -> Grimtotem"


def test_someone_in_range_goes_first():
    g = world(PALLY, "blessing = { on = true }", extra=RANGE)
    g.run("NEAR.Kaldrok = true")
    g.event("CHAT_MSG_RAID", "kings", "Grimtotem")
    g.event("CHAT_MSG_RAID", "wis", "Kaldrok")
    assert raw_macro(g) == "/cast [@party2] Blessing of Wisdom"


def test_right_click_skips_and_a_leaver_is_dropped():
    g = world(PALLY, "blessing = { on = true }", extra=RANGE)
    g.run("NEAR.Grimtotem = true NEAR.Kaldrok = true")
    g.event("CHAT_MSG_RAID", "kings", "Grimtotem")
    g.event("CHAT_MSG_RAID", "wis", "Kaldrok")
    g.run('local b = ServiceInviterBuffPop b._scripts.PostClick(b, "RightButton")')
    assert raw_macro(g) == "/cast [@party2] Blessing of Wisdom"
    g.run('UNITS.party2 = nil GROUP.Kaldrok = nil CLOCK = CLOCK + 1 ServiceInviter_Test.Tick(1)')
    assert label(g) == "No buffs waiting"


def test_hidden_range_answers_dont_break_the_buffs():
    """The owner's screenshot, 14 Nov 2026: "error in buffs: ... attempt to perform boolean test on
    local 'checked' (a secret boolean value)". Hidden answers count as unknown: the pop shows."""
    secret = """
        SECRET = setmetatable({}, { __tostring = function() return "secret" end })
        function issecretvalue(v) return v == SECRET end
        function UnitInRange(u) return SECRET, SECRET end
        function UnitIsConnected(u) return SECRET end
        function UnitIsVisible(u) return SECRET end"""
    g = world(PALLY, "blessing = { on = true }", extra=secret)
    g.event("CHAT_MSG_RAID", "kings", "Grimtotem")
    g.run("CLOCK = CLOCK + 1 ServiceInviter_Test.Tick(1)")
    assert not any("error in" in p for p in g.printed())
    assert g.eval("ServiceInviterBuffPop:IsShown()")
    assert raw_macro(g) == "/cast [@party1] Blessing of Kings"


def test_si_why_explains_a_buff_ask():
    """The owner, 14 Nov 2026: "buff thing isnt firing when they ask for it"."""
    g = world(PALLY, "blessing = { on = true }")
    g.event("CHAT_MSG_RAID", "kings pls", "Grimtotem")
    g.run('SlashCmdList.SERVICEINVITER("why grimtotem")')
    assert "queued Blessing of Kings" in g.printed()[-1]
    g = world(PALLY)                                                   # blessing not ticked
    g.event("CHAT_MSG_RAID", "kings pls", "Grimtotem")
    g.run('SlashCmdList.SERVICEINVITER("why grimtotem")')
    assert "'We offer a blessing' is off" in g.printed()[-1]
    g = world(PALLY, "blessing = { on = true }")
    g.event("CHAT_MSG_RAID", "kings pls", "Stranger")
    g.run('SlashCmdList.SERVICEINVITER("why stranger")')
    assert "not in your group" in g.printed()[-1]
