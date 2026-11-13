"""Services.lua: who can do what, who gets paid, and what gets said. The owner's asks of
12 Nov 2026 are quoted in docs/DESIGN.md; the expected lines are the prototype's output that
the owner saw and liked ("i like the idea")."""
import pytest
from lupa import lua51

from conftest import CORE


@pytest.fixture
def core():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute(CORE.read_text())
    return L


def member(name, cls, level=60, zone=None, me=False, knows=None):
    parts = [f'name="{name}"', f'class="{cls}"', f"level={level}", f"me={str(me).lower()}"]
    if zone:
        parts.append(f'zone="{zone}"')
    if knows is not None:
        parts.append("knows={" + ", ".join(f'["{k}"]=true' for k in knows) + "}")
    return "{" + ", ".join(parts) + "}"


def group(*members):
    return "{" + ", ".join(members) + "}"


def db(**services):
    """db(summons={"price": 25}, portals={"on": True, "price": 20}) -> a Lua table."""
    def val(v):
        if v is True or v is False:
            return str(v).lower()
        if isinstance(v, str):
            return f'"{v}"'
        if v is None:
            return "false"
        return str(v)
    body = ", ".join(f"{k}={{" + ", ".join(f"{f}={val(x)}" for f, x in fields.items()) + "}" for k, fields in services.items())
    return "{ services = {" + body + "} }"


def call(core, fn, *args):
    r = core.eval(f"function() return ServiceInviterCore.{fn}({', '.join(args)}) end")()
    return r if isinstance(r, tuple) else (r, None)


ME_ORG = member("Me", "SHAMAN", zone="Orgrimmar", me=True)
LOCK_TB = member("Grimtotem", "WARLOCK", zone="Thunder Bluff")
MAGE_47 = member("Velenne", "MAGE", 47, zone="Orgrimmar")
ON = db(summons={"price": 25}, portals={"on": True, "price": 20}, water={"on": True})


# -- The ad ----------------------------------------------------------------------------------

def test_ad_tonight(core):
    text, _ = call(core, "BuildAd", ON, group(ME_ORG, LOCK_TB), '"Horde"')
    assert text == "WTS summons to TB 25 silver | whisper inv"


def test_ad_grows_when_a_mage_joins_and_skips_the_city_he_is_in(core):
    text, _ = call(core, "BuildAd", ON, group(ME_ORG, LOCK_TB, MAGE_47), '"Horde"')
    assert text == "WTS summons to TB 25 silver, portals to UC 20 silver (at Org), free mage food & water (at Org) | whisper inv"


def test_ad_follows_the_warlock(core):
    lock_uc = member("Grimtotem", "WARLOCK", zone="Undercity")
    text, _ = call(core, "BuildAd", ON, group(ME_ORG, lock_uc), '"Horde"')
    assert text == "WTS summons to UC 25 silver | whisper inv"


def test_all_free_ad_drops_wts(core):
    rogue = member("Me", "ROGUE", zone="Thunder Bluff", me=True)
    text, _ = call(core, "BuildAd", db(lockpick={"on": True}), group(rogue), '"Horde"')
    assert text == "Free lockpicking (at TB) | whisper inv"


def test_nothing_to_sell_turns_the_ad_off(core):
    text, why = call(core, "BuildAd", ON, group(ME_ORG), '"Horde"')
    assert text is None and "nothing to sell" in why


def test_ad_over_the_chat_limit_is_refused(core):
    text, why = call(core, "BuildAd", ON, group(ME_ORG, LOCK_TB), '"Horde"', '"' + "x" * 250 + ' {services}"')
    assert text is None and "too long" in why


# -- Portals ------------------------------------------------------------------------------------

def test_level_47_mage_has_no_thunder_bluff_portal(core):
    cities = core.eval(f'ServiceInviterCore.PortalCities({MAGE_47}, "Horde", {{}})')
    assert list(cities.values()) == ["Undercity"]


def test_level_50_mage_in_tb_offers_org_and_uc(core):
    mage = member("Velenne", "MAGE", 50, zone="Thunder Bluff")
    assert list(core.eval(f'ServiceInviterCore.PortalCities({mage}, "Horde", {{}})').values()) == ["Orgrimmar", "Undercity"]


def test_alliance_portals(core):
    mage = member("Aria", "MAGE", 60, zone="Ironforge")
    assert list(core.eval(f'ServiceInviterCore.PortalCities({mage}, "Alliance", {{}})').values()) == ["Stormwind City", "Darnassus"]


def test_your_own_spellbook_wins_over_the_level_rule(core):
    me = member("Me", "MAGE", 60, zone="Thunder Bluff", me=True, knows=["Portal: Undercity"])
    assert list(core.eval(f'ServiceInviterCore.PortalCities({me}, "Horde", {{}})').values()) == ["Undercity"]


def test_unticked_portal_is_not_offered(core):
    mage = member("Velenne", "MAGE", 60, zone="Thunder Bluff")
    cities = core.eval(f'ServiceInviterCore.PortalCities({mage}, "Horde", {{ ["Undercity"] = true }})')
    assert list(cities.values()) == ["Orgrimmar"]


# -- Who gets paid ------------------------------------------------------------------------------

def payee(core, dbx, grp, key="summons", provider=LOCK_TB, here="Thunder Bluff"):
    return core.eval(f'ServiceInviterCore.Payee({dbx}, {grp}, "{key}", {provider}, "{here}")')


def test_default_payee_is_whoever_does_it_even_when_im_standing_with_them(core):
    """The owner, 12 Nov 2026: "but only when i select they pay me, right?". Being next to the
    warlock no longer makes you the payee; only picking "Me" does."""
    assert payee(core, ON, group(ME_ORG, LOCK_TB)) == "Grimtotem"
    me_tb = member("Me", "SHAMAN", zone="Thunder Bluff", me=True)
    assert payee(core, ON, group(me_tb, LOCK_TB)) == "Grimtotem"
    assert payee(core, '{ payee = { mode = "place" } }', group(me_tb, LOCK_TB)) == "Grimtotem"   # an old saved setting


def test_default_payee_always_me(core):
    assert payee(core, '{ payee = { mode = "me" } }', group(ME_ORG, LOCK_TB)) == "Me"


def test_default_payee_named(core):
    assert payee(core, '{ payee = { mode = "name", name = "Banker" } }', group(ME_ORG, LOCK_TB)) == "Banker"


def test_a_service_overrides_the_default(core):
    d = '{ payee = { mode = "me" }, services = { summons = { payee = "Grimtotem" } } }'
    assert payee(core, d, group(ME_ORG, LOCK_TB)) == "Grimtotem"


def test_old_i_collect_setting_still_means_me(core):
    assert payee(core, "{ collect = true }", group(ME_ORG, LOCK_TB)) == "Me"


# -- Welcome on joining ------------------------------------------------------------------------

def welcome(core, grp, key="summons", dest="nil", d=ON):
    text, why = call(core, "JoinWelcome", d, grp, '"Horde"', f'"{key}"', '"Kaldrok"', dest)
    return text or why


def test_welcome_summon_pay_the_warlock(core):
    assert welcome(core, group(ME_ORG, LOCK_TB)) == "Hi Kaldrok! Grimtotem will summon you to TB. 25 silver. Pay Grimtotem when you land."


def test_welcome_summon_pay_the_warlock_even_when_im_there(core):
    me_tb = member("Me", "SHAMAN", zone="Thunder Bluff", me=True)
    assert welcome(core, group(me_tb, LOCK_TB)) == "Hi Kaldrok! Grimtotem will summon you to TB. 25 silver. Pay Grimtotem when you land."


def test_welcome_summon_pay_me_when_i_picked_me(core):
    me_tb = member("Me", "SHAMAN", zone="Thunder Bluff", me=True)
    d = '{ payee = { mode = "me" } }'
    assert welcome(core, group(me_tb, LOCK_TB), d=d) == "Hi Kaldrok! Grimtotem will summon you to TB. 25 silver. Pay me when you land."


def test_welcome_im_the_warlock(core):
    me = member("Me", "WARLOCK", zone="Thunder Bluff", me=True)
    assert welcome(core, group(me)) == "Hi Kaldrok! I'll summon you to TB. 25 silver. Pay me when you land."


def test_welcome_portal_pay_the_mage_when_im_elsewhere(core):
    me_tb = member("Me", "SHAMAN", zone="Thunder Bluff", me=True)
    assert welcome(core, group(me_tb, LOCK_TB, MAGE_47), "portals", '"Undercity"') == \
        "Hi Kaldrok! Velenne will do a portal to UC, come to Velenne in Org. 20 silver. Pay Velenne there."


def test_welcome_portal_pay_the_mage_even_when_im_with_the_mage(core):
    assert welcome(core, group(ME_ORG, LOCK_TB, MAGE_47), "portals", '"Undercity"') == \
        "Hi Kaldrok! Velenne will do a portal to UC, come to Velenne in Org. 20 silver. Pay Velenne there."


def test_welcome_free_lockpicking(core):
    rogue = member("Me", "ROGUE", zone="Thunder Bluff", me=True)
    assert welcome(core, group(rogue), "lockpick", d=db(lockpick={"on": True})) == \
        "Hi Kaldrok! I'll do lockpicking, come to me in TB. Free, tips welcome."


# -- On arrival ------------------------------------------------------------------------------------

def arrival(core, grp, d, here="Thunder Bluff", bought="summons"):
    text, why = call(core, "ArrivalOffer", d, grp, '"Horde"', f'"{here}"', f'"{bought}"', '"Kaldrok"')
    return text or why


EVERYTHING = db(summons={"price": 25}, portals={"on": True, "price": 20}, water={"on": True},
                lockpick={"on": True}, healthstone={"on": True}, fort={"on": True})


def test_arrival_lists_only_whats_in_that_zone(core):
    g = group(member("Me", "ROGUE", zone="Thunder Bluff", me=True), LOCK_TB,
              member("Sela", "PRIEST", zone="Thunder Bluff"), MAGE_47)
    assert arrival(core, g, EVERYTHING) == \
        "Welcome to TB, Kaldrok! Also here: free healthstones, free lockpicking, free Fortitude. Just ask!"


def test_arrival_with_the_mage_there_too(core):
    g = group(member("Me", "ROGUE", zone="Thunder Bluff", me=True), LOCK_TB,
              member("Velenne", "MAGE", 47, zone="Thunder Bluff"))
    assert arrival(core, g, EVERYTHING) == \
        "Welcome to TB, Kaldrok! Also here: free healthstones, portals to Org/UC 20 silver, free mage food & water, free lockpicking. Just ask!"


def test_arrival_says_nothing_when_nothing_else_is_there(core):
    g = group(member("Me", "SHAMAN", zone="Thunder Bluff", me=True), LOCK_TB)
    assert arrival(core, g, db(summons={"price": 25})) == "nothing else on offer there"


# -- Settings --------------------------------------------------------------------------------------

def test_blank_price_is_free(core):
    assert core.eval('ServiceInviterCore.Setting({ services = { summons = { price = false } } }, "summons").price') is None


def test_old_price_carries_over_to_summons(core):
    assert core.eval('ServiceInviterCore.Setting({ price = 150 }, "summons").price') == 150


def test_nobody_to_do_it_means_not_on_sale(core):
    items = core.eval(f'ServiceInviterCore.OnSale({ON}, {group(ME_ORG)}, "Horde")')
    assert len(items) == 0


# -- Codex review of 12 Nov 2026 ------------------------------------------------------------------

def test_a_zero_price_is_free(core):
    """1.x's `/si price 0` was free; Lua treats 0 as true, so it read as "0s" and "WTS"."""
    assert core.eval('ServiceInviterCore.Setting({ price = 0 }, "summons").price') is None
    assert core.eval('ServiceInviterCore.Setting({ services = { lockpick = { price = 0 } } }, "lockpick").price') is None
    rogue = member("Me", "ROGUE", zone="Thunder Bluff", me=True)
    text, _ = call(core, "BuildAd", "{ services = { lockpick = { on = true, price = 0 } } }", group(rogue), '"Horde"')
    assert text == "Free lockpicking (at TB) | whisper inv"


def test_every_mage_counts_for_portals(core):
    """A level 40 mage listed first must not hide a level 60 mage's Thunder Bluff portal."""
    low = member("Velenne", "MAGE", 40, zone="Orgrimmar")
    high = member("Aldris", "MAGE", 60, zone="Undercity")
    d = db(portals={"on": True, "price": 20})
    text, _ = call(core, "BuildAd", d, group(ME_ORG, low, high), '"Horde"')
    assert text == "WTS portals to UC 20 silver (at Org), portals to Org/TB 20 silver (at UC) | whisper inv"
    # each city goes to a mage who can do it
    assert core.eval(f'ServiceInviterCore.Provider({group(ME_ORG, low, high)}, "portals", "Thunder Bluff").name') == "Aldris"
    assert core.eval(f'ServiceInviterCore.Provider({group(ME_ORG, low, high)}, "portals", "Undercity").name') == "Velenne"


def test_the_welcome_names_the_mage_who_can_do_that_city(core):
    low = member("Velenne", "MAGE", 40, zone="Orgrimmar")
    high = member("Aldris", "MAGE", 60, zone="Undercity")
    d = db(portals={"on": True, "price": 20})
    assert welcome(core, group(ME_ORG, low, high), "portals", '"Thunder Bluff"', d=d) == \
        "Hi Kaldrok! Aldris will do a portal to TB, come to Aldris in UC. 20 silver. Pay Aldris there."


def test_money_is_spelled_out(core):
    """The owner, 13 Nov 2026: "spells out silver and gold instead of s and g"."""
    m = lambda v: core.eval(f"ServiceInviterCore.Money({v})")
    assert (m(25), m(100), m(150), m(200)) == ("25 silver", "1 gold", "1 gold 50 silver", "2 gold")
