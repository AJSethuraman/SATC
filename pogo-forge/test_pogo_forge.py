"""
Tests for pogo-forge.

The rule this suite follows: every assertion is anchored to something known
independently of this codebase. Published max-CP figures, documented type
relationships, real screenshots whose IVs are confirmed by a separate formula.

A test that asserts the code does what the code does proves nothing. If you
add a case, bring an external number with it.

    pip install pytest
    pytest -q
"""

import math
from pathlib import Path

import pytest
from PIL import Image

import appraisal
import costs as C
import pvp

FIXTURES = Path(__file__).parent / "fixtures"


# ============================================================ CP formula ===
# Max CP at level 40 for a perfect IV Pokemon is published for every species
# and widely cross-checked. If the CP formula or the CPM table drifts, these
# break immediately.
@pytest.mark.parametrize("species,expected", [
    ("mewtwo",   4178),
    ("slaking",  4431),
    ("magikarp",  274),
    ("gardevoir", 3093),
])
def test_max_cp_matches_published(species, expected):
    assert C.cp_at(species, (15, 15, 15), 40.0) == expected


def test_cpm_half_level_interpolation():
    # The level 1.5 multiplier is published to nine decimals.
    assert C.cpm(1.5) == pytest.approx(0.135137432, abs=1e-9)


def test_cpm_endpoints():
    assert C.cpm(1.0) == pytest.approx(0.094)
    assert C.cpm(40.0) == pytest.approx(0.7903)
    assert C.cpm(50.0) == pytest.approx(0.8403)


def test_cp_is_monotonic_in_level():
    # max_level_under_cp breaks out of its loop on the first level that
    # exceeds the cap. That is only safe if CP never decreases with level.
    prev = 0
    for lv in C.levels(1.0, C.BEST_BUDDY_MAX):
        cp = C.cp_at("azumarill", (0, 14, 15), lv)
        assert cp >= prev
        prev = cp


def test_floor_is_not_knife_edge():
    """CP uses floor() on a float. Confirm nothing sits near a boundary.

    If a raw CP landed within a hair of an integer, a difference in float
    rounding between machines could change the answer. Measured headroom is
    around 5e-4, three orders of magnitude of margin.
    """
    worst = 1.0
    for sp in ("azumarill", "mewtwo", "gardevoir", "magikarp", "medicham"):
        s = C.base_stats(sp)
        for lv in C.levels(1.0, C.MAX_LEVEL):
            m = C.cpm(lv)
            raw = ((s["atk"] + 15) * math.sqrt(s["def"] + 15)
                   * math.sqrt(s["sta"] + 15) * m * m) / 10
            worst = min(worst, abs(raw - round(raw)))
    assert worst > 1e-5


# ================================================================= costs ===
def test_best_buddy_level_is_free():
    """The +1 level from Best Buddy costs nothing.

    This was a real bug: level 49->51 was billed as two extra paid steps,
    overstating every max-level plan by 30,000 dust.
    """
    to_50 = C.power_up_cost(49.0, 50.0)
    to_51 = C.power_up_cost(49.0, 51.0)
    assert to_51.dust == to_50.dust
    assert to_51.xl_candy == to_50.xl_candy
    assert C.power_up_cost(50.0, 51.0).dust == 0


def test_power_up_totals():
    # 1 -> 40 is a long-published figure.
    assert C.power_up_cost(1.0, 40.0).dust == 270_000
    # 40 -> 50 likewise, and it is entirely XL candy.
    # The XL figure is pinned exactly in
    # test_forty_to_fifty_costs_296_xl_candy; `> 0` here would pass on any
    # indexing bug that still charged something.
    c = C.power_up_cost(40.0, 50.0)
    assert c.dust == 250_000
    assert c.candy == 0
    assert c.xl_candy == 296


def test_no_cost_when_already_there():
    assert C.power_up_cost(30.0, 30.0).dust == 0
    assert C.power_up_cost(30.0, 25.0).dust == 0


def test_shadow_costs_more_purified_less():
    plain = C.power_up_cost(20.0, 30.0)
    shadow = C.power_up_cost(20.0, 30.0, shadow=True)
    pure = C.power_up_cost(20.0, 30.0, purified=True)
    assert shadow.dust > plain.dust
    assert pure.dust < plain.dust


def test_multi_step_evolution():
    # Ralts to Gardevoir is two evolutions: 25 + 100.
    c, final = C.evolution_cost("ralts", "gardevoir")
    assert c.candy == 125
    assert final == "GARDEVOIR"


def test_branching_evolution_refuses_to_guess():
    with pytest.raises(C.Unknown):
        C.evolution_cost("kirlia")          # Gallade or Gardevoir?
    with pytest.raises(C.Unknown):
        C.evolution_path("ralts", "pikachu")


def test_unknown_species_raises():
    with pytest.raises(C.Unknown):
        C.base_stats("sparklemon")


# =============================================================== PvP rank ===
def test_azumarill_rank_one_is_zero_fifteen_fifteen():
    """The best Great League Azumarill is 0/15/15. This is well known and is
    the canonical demonstration that a hundo is not the goal."""
    assert pvp.top("azumarill", 1500, 1)[0]["ivs"] == [0, 15, 15]


def test_hundo_is_bad_in_great_league():
    r = pvp.rank("azumarill", (15, 15, 15), 1500)
    assert r["rank"] > 2000
    assert 90 < r["percent"] < 96


def test_rank_one_is_one_hundred_percent():
    for sp in ("azumarill", "medicham", "empoleon", "corviknight"):
        assert pvp.top(sp, 1500, 1)[0]["percent"] == 100.0


def test_rank_one_respects_the_cap():
    for sp in ("azumarill", "empoleon", "corviknight", "altaria"):
        assert pvp.top(sp, 1500, 1)[0]["cp"] <= 1500


def test_iv_floor_reduces_the_ceiling():
    """Eggs and raids guarantee a minimum of 10 in every stat, which is bad
    for a capped league: it makes a low attack IV impossible."""
    wild = pvp._table("CORVIKNIGHT", 1500, 0)[0][3]
    egg = pvp._table("CORVIKNIGHT", 1500, 10)[0][3]
    assert egg < wild


# ============================================================ type chart ===
# Type effectiveness is documented outside this codebase. The scalars are
# indexed by the canonical enum order, not the order the templates appear in
# the game master — using the latter produces a plausible but wrong chart.
@pytest.mark.parametrize("atk,dfn,expected", [
    ("NORMAL",   "GHOST",    0.390625),
    ("DRAGON",   "FAIRY",    0.390625),
    ("FIGHTING", "GHOST",    0.390625),
    ("ELECTRIC", "GROUND",   0.390625),
    ("PSYCHIC",  "DARK",     0.390625),
    ("GRASS",    "WATER",    1.6),
    ("ICE",      "DRAGON",   1.6),
    ("FIRE",     "STEEL",    1.6),
    ("WATER",    "FIRE",     1.6),
    ("STEEL",    "FAIRY",    1.6),
    ("NORMAL",   "NORMAL",   1.0),
])
def test_type_chart(atk, dfn, expected):
    assert C.DATA["type_chart"][atk][dfn] == pytest.approx(expected)


def test_type_chart_is_complete():
    chart = C.DATA["type_chart"]
    assert len(chart) == 18
    for row in chart.values():
        assert len(row) == 18


# ============================================================== movesets ===
def test_legacy_moves_are_flagged():
    """Getting this wrong costs someone a rare Elite TM, so it is asserted
    against known cases rather than trusted."""
    assert "MOONBLAST" in C.SPECIES["ALTARIA"]["legacy_charged"]
    assert "MOONBLAST" not in C.SPECIES["ALTARIA"]["charged"]
    assert "AQUA_TAIL" in C.SPECIES["QUAGSIRE"]["legacy_charged"]
    assert "HYDRO_CANNON" in C.SPECIES["EMPOLEON"]["legacy_charged"]


def test_regular_moves_are_not_flagged_legacy():
    assert "DRAGON_BREATH" in C.SPECIES["ALTARIA"]["fast"]
    assert "SKY_ATTACK" in C.SPECIES["ALTARIA"]["charged"]
    assert "MUD_SHOT" in C.SPECIES["QUAGSIRE"]["fast"]


def test_no_move_appears_in_both_lists():
    for name, s in C.SPECIES.items():
        assert not (set(s["fast"]) & set(s["legacy_fast"])), name
        assert not (set(s["charged"]) & set(s["legacy_charged"])), name


def test_move_names_are_strings():
    # A few game master entries carry an unresolved numeric id; those are
    # dropped at extraction rather than guessed at.
    for s in C.SPECIES.values():
        for key in ("fast", "charged", "legacy_fast", "legacy_charged"):
            assert all(isinstance(m, str) for m in s[key])


def test_buddy_distance_present_and_sane():
    assert C.SPECIES["ROOKIDEE"]["buddy_km"] == 1.0
    assert C.SPECIES["REGISTEEL"]["buddy_km"] == 20.0
    for s in C.SPECIES.values():
        if s["buddy_km"] is not None:
            assert 1.0 <= s["buddy_km"] <= 20.0


# ====================================================== appraisal reader ===
# Each fixture's IVs are confirmed by an independent path: they reproduce the
# CP and HP printed on the same screenshot, via the CP formula. The bars and
# the formula are unrelated routes to the same three numbers.
FIXTURE_CASES = [
    ("ralts.png",    "ralts",    296, 66,  [13, 14, 13], 20.0),
    ("quagsire.png", "quagsire", 1413, 157, [9, 12, 15], 26.0),
    ("piplup.png",   "piplup",   571, 91,  [10, 10, 12], 20.0),
    ("altaria.png",  "altaria",  1497, 137, [5, 15, 14], 28.0),
]


@pytest.mark.parametrize("fname,species,cp,hp,ivs,level", FIXTURE_CASES)
def test_reads_real_screenshots(fname, species, cp, hp, ivs, level):
    path = FIXTURES / fname
    if not path.exists():
        pytest.skip(f"fixture {fname} not present")
    r = appraisal.appraise(Image.open(path), species, cp=cp, hp=hp)
    assert r["ivs"] == ivs
    assert r["verified"] is True
    assert level in r["levels"]


@pytest.mark.parametrize("scale", [0.4, 0.5, 0.75, 1.0, 1.5, 2.0])
def test_reader_is_resolution_independent(scale):
    path = FIXTURES / "ralts.png"
    if not path.exists():
        pytest.skip("fixture not present")
    im = Image.open(path).convert("RGB")
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    assert [b.iv for b in appraisal.read_bars(im)] == [13, 14, 13]


@pytest.mark.parametrize("quality", [95, 70, 50])
def test_reader_survives_jpeg(quality):
    import io
    path = FIXTURES / "ralts.png"
    if not path.exists():
        pytest.skip("fixture not present")
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, "JPEG", quality=quality)
    buf.seek(0)
    assert [b.iv for b in appraisal.read_bars(Image.open(buf))] == [13, 14, 13]


def test_reader_refuses_rather_than_guessing():
    for img in (Image.new("RGB", (1179, 2556), (255, 255, 255)),
                Image.new("RGB", (40, 40), (240, 160, 64))):
        with pytest.raises(appraisal.ReadFailed):
            appraisal.read_bars(img)


def test_wrong_cp_fails_verification():
    """The whole point of the cross-check. A misread, a mistyped number or a
    wrong species must surface as unverified, never as a confident answer."""
    path = FIXTURES / "ralts.png"
    if not path.exists():
        pytest.skip("fixture not present")
    im = Image.open(path)
    assert appraisal.appraise(im, "ralts", cp=999, hp=66)["verified"] is False
    assert appraisal.appraise(im, "kirlia", cp=296, hp=66)["verified"] is False


def test_unverified_without_cp_and_hp():
    path = FIXTURES / "ralts.png"
    if not path.exists():
        pytest.skip("fixture not present")
    r = appraisal.appraise(Image.open(path), "ralts")
    assert r["verified"] is False
    assert r["ivs"] == [13, 14, 13]


# ============================================================ determinism ===
def test_identical_inputs_give_identical_output():
    first = C.plan("gardevoir", ivs=(13, 14, 13), from_level=8.0,
                   goal="cp_cap", cp_cap=1500)
    for _ in range(50):
        assert C.plan("gardevoir", ivs=(13, 14, 13), from_level=8.0,
                      goal="cp_cap", cp_cap=1500) == first


# ============================================================== coverage ===
import coverage as cov


def test_known_weaknesses():
    # Altaria is Dragon/Flying: Ice hits it 1.6 for Dragon and 1.6 for Flying.
    w = cov.weaknesses("altaria")
    assert w["ICE"] == pytest.approx(2.56)
    assert "FAIRY" in w and "DRAGON" in w and "ROCK" in w
    # Quagsire is Water/Ground: Grass is doubly super effective.
    assert cov.weaknesses("quagsire")["GRASS"] == pytest.approx(2.56)


def test_known_immunity_equivalent():
    # Electric does nothing to a Ground type.
    assert cov.incoming(["GROUND"], "ELECTRIC") == pytest.approx(0.390625)
    # Water/Ground is doubly resistant to Electric... no: Ground negates it,
    # Water is weak to it. Net is neutral-ish, which is the point of checking.
    q = cov.incoming(["WATER", "GROUND"], "ELECTRIC")
    assert q == pytest.approx(1.6 * 0.390625)


def test_a_complementary_pair_shares_nothing():
    """Altaria and Quagsire have no weakness in common.

    Worth asserting because it is easy to assume otherwise: Altaria is badly
    weak to Ice, and Quagsire is part Ground, which is also weak to Ice. But
    Quagsire's Water half resists Ice and the two cancel to neutral. Reasoning
    about dual types by eye gets this wrong; multiplying the chart does not.
    """
    assert cov.shared_weaknesses(["altaria", "quagsire"]) == {}
    assert cov.suggest_partners(["altaria", "quagsire"]) == []


def test_partner_suggestion_covers_a_real_hole():
    # Altaria and Charizard are both weak to Rock and nothing else in common.
    assert set(cov.shared_weaknesses(["altaria", "charizard"])) == {"ROCK"}
    out = cov.suggest_partners(["altaria", "charizard"],
                               candidates=["empoleon", "quagsire", "registeel",
                                           "magikarp", "onix"])
    assert out, "expected at least one partner"
    for row in out:
        assert "ROCK" in row["covers"]
    # Known limitation, asserted so nobody "fixes" it by accident: this
    # ranks typings, not Pokemon. Onix is offered because Rock attacks really
    # do resist off its Ground half — it is a correct answer to the question
    # asked and a terrible answer to the question meant. Viability has to
    # come from the PvP rank and the meta, not from here.
    assert "Onix" in [r["species"] for r in out]


def test_no_partners_when_no_shared_hole():
    assert cov.shared_weaknesses([]) == {}


# =============================================================== dynamax ===
import dynamax as dm


def test_dynamax_full_build_matches_published_total():
    """Internal-consistency check against an independently published figure.

    Taking all three Max Moves from locked to level 3 on a group-1 Pokemon is
    documented as 5,400 Max Particles, 450 Candy and 120 Candy XL. That total
    is published separately from the per-level costs used to derive it, so a
    mistyped per-level number fails here.
    """
    c = dm.full_build(1, {"attack": 0, "guard": 0, "spirit": 0})
    assert c.particles == 5400
    assert c.candy == 450
    assert c.xl_candy == 120


def test_dynamax_real_build_is_cheaper_than_the_published_figure():
    """The 5,400 figure counts Max Attack from locked, but every Dynamax
    Pokemon arrives with it already at level 1. The real bill is one unlock
    lower, and quoting the published number would overstate it."""
    c = dm.full_build(1)
    assert c.particles == 5000
    assert c.candy == 400
    assert c.xl_candy == 120


def test_dynamax_particles_are_group_independent():
    # Only candy varies by group. This is why the planner can cost particles
    # exactly while asking the user only which group a species is in.
    totals = {g: dm.full_build(g).particles for g in dm.CANDY_GROUPS}
    assert len(set(totals.values())) == 1


def test_dynamax_candy_increases_with_group():
    candy = [dm.full_build(g).candy for g in (1, 2, 3, 4)]
    xl = [dm.full_build(g).xl_candy for g in (1, 2, 3, 4)]
    assert candy == sorted(candy) and len(set(candy)) == 4
    assert xl == sorted(xl) and len(set(xl)) == 4


def test_dynamax_unlock_costs_four_hundred_particles():
    assert dm.step_cost(1, 1).particles == 400
    assert dm.step_cost(1, 2).particles == 600
    assert dm.step_cost(1, 3).particles == 800


def test_dynamax_level_three_is_paid_in_xl():
    c = dm.step_cost(1, 3)
    assert c.xl_candy == 40
    assert c.candy == 0


def test_dynamax_default_start_state():
    """Dynamax Pokemon start with Max Attack at 1, the others locked. A build
    from that state must cost less than one starting from nothing."""
    from_default = dm.full_build(1)
    from_zero = dm.full_build(1, {"attack": 0, "guard": 0, "spirit": 0})
    assert from_default.particles < from_zero.particles
    assert from_zero.particles - from_default.particles == 400
    assert from_zero.candy - from_default.candy == 50


def test_dynamax_bad_group_and_level_rejected():
    with pytest.raises(ValueError):
        dm.step_cost(9, 1)
    with pytest.raises(ValueError):
        dm.step_cost(1, 4)


def test_dynamax_particle_days_uses_the_real_cap():
    # 5,400 particles at 800/day plus a 300 walking bonus is about five days.
    assert dm.days_of_particles(5400) == pytest.approx(4.9, abs=0.1)
    assert dm.days_of_particles(5400, walking=False) == pytest.approx(6.8, abs=0.1)


def test_dynamax_max_attack_typing_rule():
    assert dm.max_attack_type(True, "fairy") == "fixed by species"
    assert dm.max_attack_type(False, "fairy") == "FAIRY"
    assert "unknown" in dm.max_attack_type(False, None)


def test_dynamax_tier_lists_are_dated_and_populated():
    # These go stale. The date is asserted so nobody treats them as permanent.
    assert dm.SOURCE_DATE
    for lst in (dm.BEST_ATTACKERS, dm.BEST_DEFENDERS, dm.BEST_HEALERS):
        assert len(lst) >= 10


def test_dynamax_attacker_list_is_sorted_by_attack():
    stats = [a[1] for a in dm.BEST_ATTACKERS if not a[0].startswith("Zacian")]
    assert stats == sorted(stats, reverse=True)


# ==================================================== provenance and stamp ===
# This codebase's whole design rests on knowing which numbers are Niantic's
# and which are not. These tests defend that claim rather than any figure.
def test_gamedata_carries_a_version_stamp():
    """Every answer is a pure function of gamedata.json plus the user's input.

    Without a stamp, a refetch changes answers silently — which was gap 3 on
    the handoff list. With one, a change is something you can point at.
    """
    assert len(C.DATA.get("version", "")) == 64      # sha256 of the game master
    assert C.DATA.get("fetched")
    assert C.DATA["source"].startswith("https://")


def test_hand_typed_numbers_are_quarantined_and_labelled():
    """The IV floors are NOT in the game master — searching it for a
    minimum-IV template returns nothing. They used to sit at the top level of
    gamedata.json under a header claiming everything there was Niantic's.

    If a future extractor learns to read them from the file, move them out of
    `community` and delete this test. Do not add anything else to that block
    without a provenance line saying where it came from.
    """
    assert "iv_floors" not in C.DATA, "hand-typed data must not sit with Niantic's"
    community = C.DATA["community"]
    assert "NOT in the game master" in community["_provenance"]
    assert community["iv_floors"]["lucky"] == 12


def test_plan_reports_which_gamedata_it_used():
    p = C.plan("gardevoir", ivs=(13, 14, 13), from_level=8.0, goal="cp_cap",
               cp_cap=1500)
    assert p["gamedata_version"] == C.DATA["version"][:12]


# ================================================= power-up, exact figures ===
def test_forty_to_fifty_costs_296_xl_candy():
    """The published 40->50 bill is 250,000 dust and 296 XL Candy.

    The dust half of that was already asserted; the XL half was only checked
    for being greater than zero, which would have passed on any indexing bug
    that still charged something. Both halves come out of the same table walk,
    so pinning only one of them left the other free to drift.
    """
    c = C.power_up_cost(40.0, 50.0)
    assert c.dust == 250_000
    assert c.xl_candy == 296
    assert c.candy == 0


def test_a_level_is_two_power_ups_per_niantic():
    """The cost engine charges each whole-level table entry twice.

    That was an assumption inferred from the 1->40 and 40->50 totals coming
    out right. Niantic states it directly as upgradesPerLevel, so it is read
    from the file and checked against what the engine actually does.
    """
    assert C.UP["upgrades_per_level"] == 2
    steps = C.power_up_cost(20.0, 21.0).steps
    assert steps == C.UP["upgrades_per_level"]
    assert C.power_up_cost(1.0, 40.0).steps == 39 * C.UP["upgrades_per_level"]


def test_xl_candy_needs_trainer_level_31():
    # dynamax.py states this in prose; the game master carries the number.
    assert C.UP["xl_min_player_level"] == 31
    assert C.UP["xl_from_level"] == 40


# ============================================ evolutions cost more than candy ===
# The game master records 84 item requirements, 28 gender requirements, 16
# buddy-distance requirements and more. The extractor used to drop all of it,
# so the planner quoted "Evolve to Bellossom: 100 candy" for an evolution that
# also needs a Sun Stone. Each case below is a documented in-game requirement.
@pytest.mark.parametrize("src,dst,needle", [
    ("gloom", "bellossom", "Sun Stone"),
    ("sunkern", "sunflora", "Sun Stone"),
    ("onix", "steelix", "Metal Coat"),
    ("seadra", "kingdra", "Dragon Scale"),
    # "Up Grade", not the in-game "Up-Grade": _item_name turns underscores
    # into spaces and is deliberately not a hand-maintained name table, so
    # one hyphenated item comes out recognisable rather than exact.
    ("porygon", "porygon2", "Up Grade"),
    ("kirlia", "gallade", "Sinnoh Stone"),
    ("magneton", "magnezone", "Magnetic Lure Module"),
    ("eevee", "espeon", "km walked as your buddy"),
])
def test_evolution_states_what_it_needs_besides_candy(src, dst, needle):
    c, final = C.evolution_cost(src, dst)
    assert final == dst.upper()
    assert c.candy > 0
    blob = " ".join(c.requires)
    assert needle in blob, f"{src}->{dst} requires {needle!r}; got {c.requires}"


def test_gallade_needs_a_stone_and_a_gender():
    """Two requirements on one hop. Reporting only the first is the same bug
    in a smaller form."""
    c, _ = C.evolution_cost("kirlia", "gallade")
    blob = " ".join(c.requires).lower()
    assert "sinnoh stone" in blob and "male only" in blob


def test_requirements_are_collected_across_every_hop():
    """Ralts to Gallade is two evolutions and the requirements sit on the
    second. Walking only the last hop, or only the first, loses them."""
    c, final = C.evolution_cost("ralts", "gallade")
    assert final == "GALLADE"
    assert c.candy == 125                      # 25 + 100, same as Gardevoir
    blob = " ".join(c.requires).lower()
    assert "sinnoh stone" in blob and "male only" in blob


def test_an_evolution_with_no_requirements_claims_none():
    # The counter-case: Ralts to Gardevoir needs nothing but candy. If this
    # ever reports a requirement, the extractor is inventing them.
    c, _ = C.evolution_cost("ralts", "gardevoir")
    assert c.requires == []


def test_trade_evolutions_say_the_candy_can_be_free():
    c, _ = C.evolution_cost("kadabra", "alakazam")
    assert any("trade" in n.lower() for n in c.notes)


def test_uncosted_evolution_refuses_without_claiming_it_cannot_evolve():
    """Gimmighoul evolves into Gholdengo for 999 Gimmighoul Coins, which is
    not candy and is not in the game master's candyCost. The old message was
    'has no evolution on file' — a different claim, and a false one."""
    with pytest.raises(C.Unknown) as e:
        C.evolution_cost("gimmighoul")
    msg = str(e.value).lower()
    assert "gholdengo" in msg and "not for candy" in msg


def test_plan_hoists_requirements_where_a_caller_cannot_miss_them():
    p = C.plan("gloom", ivs=(15, 15, 15), from_level=20.0, goal="level",
               target_level=25.0, evolve_to="bellossom")
    assert any("Sun Stone" in r for r in p["requires"])


# ======================================== how strong is the CP/HP check, exactly ===
def test_a_one_notch_misread_never_survives_verification():
    """The reader's most valuable property is that it refuses rather than
    guessing, and the CP/HP cross-check is what enforces it. The realistic
    failure is one bar read one step off, not a random spread.

    Measured on all four fixtures: of the six spreads one notch away from the
    truth, zero reproduce the same CP and HP at any level. So a single misread
    bar is always caught.
    """
    for species, cp, hp, truth in [
        ("ralts", 296, 66, (13, 14, 13)),
        ("quagsire", 1413, 157, (9, 12, 15)),
        ("piplup", 571, 91, (10, 10, 12)),
        ("altaria", 1497, 137, (5, 15, 14)),
    ]:
        for i in range(3):
            for delta in (-1, 1):
                n = list(truth)
                n[i] += delta
                if not 0 <= n[i] <= 15:
                    continue
                spread = tuple(n)
                survives = any(
                    C.cp_at(species, spread, lv) == cp
                    and C.hp_at(species, spread[2], lv) == hp
                    for lv in C.levels(1.0, C.BEST_BUDDY_MAX))
                assert not survives, (
                    f"{species}: misreading {truth} as {spread} would still "
                    f"reproduce CP {cp} / HP {hp} — the check would pass a "
                    "wrong answer")


def test_verified_means_consistent_not_unique():
    """Guards the wording as much as the code.

    'Confirmed' does not mean the spread is the only one that fits: for Ralts
    at CP 296 / HP 66, 69 of the 4,096 spreads reproduce both numbers. The
    check is a strong filter, not a proof of uniqueness, and the reader's
    own claim should not be read as more than that.

    Asserted as a range because the exact count is a property of one species
    at one CP, and pinning it exactly would break on a CPM refetch without
    telling anyone anything useful.
    """
    consistent = [
        (a, d, s)
        for a in range(16) for d in range(16) for s in range(16)
        if any(C.cp_at("ralts", (a, d, s), lv) == 296
               and C.hp_at("ralts", s, lv) == 66
               for lv in C.levels(1.0, C.BEST_BUDDY_MAX))
    ]
    assert (13, 14, 13) in consistent
    assert 1 < len(consistent) < 200


# ==================================================== the two level ceilings ===
def test_the_two_ceilings_differ_exactly_where_the_cap_does_not_bind():
    """costs.max_level_under_cp allows the Best Buddy level; pvp's table stops
    at 50. So the two modules answer the same question differently, and it is
    worth knowing precisely where.

    The first draft of this test assumed a league cap always binds before
    level 50 and so the two would agree at Great and Ultra League. That is
    false: Azumarill's maximum CP is well under 2,500, so Ultra League never
    binds for it and the two disagree by a level. The rule is not about the
    league, it is about whether the cap bound at all.
    """
    seen_both = set()
    for species in ("azumarill", "medicham", "altaria", "magikarp", "mewtwo"):
        for cap in (1500, 2500, 10000):
            pvp_level = pvp.rank(species, (0, 15, 15), cap)["level"]
            costs_level = C.max_level_under_cp(species, (0, 15, 15), cap)
            bound = costs_level < C.BEST_BUDDY_MAX
            if bound:
                assert pvp_level == costs_level, (
                    f"{species} @ {cap}: cap bound at {costs_level} but pvp "
                    f"said {pvp_level}")
            else:
                assert costs_level == C.BEST_BUDDY_MAX
                assert pvp_level == C.MAX_LEVEL
            seen_both.add(bound)
    # Both branches must actually occur, or this test proves only one of them.
    assert seen_both == {True, False}


# =========================================== the API refuses what it can't read ===
def test_a_mistyped_field_is_refused_not_defaulted():
    """Pydantic ignores unknown keys by default, which turns a client-side
    typo into a confident wrong answer.

    This exact body — plausible field names, neither of them real — used to
    return a fully itemised plan for a perfect 15/15/15 at level 1, with
    nothing anywhere in the response saying the input had been discarded.
    """
    from fastapi.testclient import TestClient
    import app as A

    with TestClient(A.app) as client:
        wrong = client.post("/api/cost", json={
            "species": "gloom", "ivs": [9, 12, 15], "level": 20,
            "goal": "level", "target_level": 25})
        assert wrong.status_code == 422, wrong.text

        right = client.post("/api/cost", json={
            "species": "gloom", "iv_atk": 9, "iv_def": 12, "iv_hp": 15,
            "from_level": 20, "goal": "level", "target_level": 25})
        assert right.status_code == 200
        assert right.json()["from_level"] == 20.0


def test_the_cost_api_reports_requirements_beyond_candy():
    """End to end, through the HTTP layer the phone actually talks to."""
    from fastapi.testclient import TestClient
    import app as A

    with TestClient(A.app) as client:
        r = client.post("/api/cost", json={
            "species": "gloom", "from_level": 20, "goal": "level",
            "target_level": 25, "evolve_to": "bellossom"})
        assert r.status_code == 200
        body = r.json()
        assert any("Sun Stone" in x for x in body["requires"]), body


def test_a_refusal_comes_back_the_same_shape_as_an_answer():
    """Gallade at 13/14/13 is already over 1,500 CP at level 20, so the
    planner refuses — correctly. It used to refuse with two keys and a raw
    uppercase species name, so a caller rendering a plan either special-cased
    it or showed nothing. The refusal is about the same Pokemon; it carries
    the same fields.
    """
    p = C.plan("ralts", ivs=(13, 14, 13), from_level=20.0, goal="cp_cap",
               cp_cap=1500, evolve_to="gallade")
    assert "error" in p
    assert p["species"] == "Gallade"
    assert p["gamedata_version"] == C.DATA["version"][:12]
    # The Sinnoh Stone is still needed whether or not the level goal works out.
    assert any("Sinnoh Stone" in r for r in p["requires"]), p["requires"]


# ============================================ dynamax is wired to the product ===
# dynamax.py was 187 lines with 14 passing tests and no caller: nothing in
# app.py imported it. Meanwhile the planner asked the user to type in nine
# numbers per species, six of which (the particles) are constants this module
# already knew. These tests hold the wiring in place.
import contextlib as _contextlib


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("POGO_FORGE_DB", str(tmp_path / "t.db"))
    import importlib
    import app as A
    importlib.reload(A)
    from fastapi.testclient import TestClient
    with TestClient(A.app) as c:
        yield c


def test_dynamax_module_is_reachable_from_the_app():
    """The regression that matters: an engine module nobody calls."""
    import app as A
    assert A.dynamax.PARTICLES[1] == 400


def _add(client, species="charizard", **kw):
    body = {"species": species, "role": "attacker", "max_form": "dynamax"}
    body.update(kw)
    r = client.post("/api/roster", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_particles_are_known_without_asking_anyone(client):
    """A species with no recorded group still gets exact particle costs.

    This is the whole point: particles do not vary by species, so a missing
    group must not make them unknown. The planner used to report the entire
    step as unknown, which asked the user for a constant.
    """
    _add(client)
    steps = client.get("/api/plan").json()["steps"]
    by_slot = {s["slot"]: s for s in steps}
    # Max Attack starts at 1, so its next step is level 2; the others unlock.
    assert by_slot["attack"]["to_level"] == 2
    assert by_slot["attack"]["particles"] == 600
    assert by_slot["guard"]["to_level"] == 1
    assert by_slot["guard"]["particles"] == 400
    assert by_slot["spirit"]["particles"] == 400
    for s in steps:
        assert s["cost_source"] == "unknown"
        assert s["candy"] is None
        assert "charizard" in s["needs"].lower()


def test_candy_is_refused_rather_than_assumed(client):
    """A wrong group misstates candy by up to 40%, so no group means no candy
    figure — not a default of group 1."""
    _add(client)
    for s in client.get("/api/plan").json()["steps"]:
        assert s["candy"] is None and s["candy_xl"] is None
        assert s["cost_group"] is None


def test_one_recorded_group_costs_every_slot_and_level(client):
    """Nine numbers replaced by one choice."""
    _add(client)
    assert client.post("/api/cost-groups",
                       json={"species": "charizard", "cost_group": 2}
                       ).status_code == 201
    steps = {s["slot"]: s for s in client.get("/api/plan").json()["steps"]}
    assert steps["guard"]["cost_source"] == "group"
    assert steps["guard"]["cost_group"] == 2
    # Group 2: 60 candy to level 1, 110 to level 2, 45 XL to level 3.
    assert steps["guard"]["candy"] == 60          # unlock, level 1
    assert steps["attack"]["candy"] == 110        # already at 1, so level 2
    assert steps["guard"]["needs"] is None


def test_an_observed_cost_beats_the_community_tables(client):
    """dynamax.py's groups are community-documented, not Niantic's. A number
    you watched the game charge you outranks them, and the step says so."""
    _add(client)
    client.post("/api/cost-groups", json={"species": "charizard", "cost_group": 1})
    client.post("/api/costs", json={
        "species": "charizard", "slot": "guard", "to_level": 1,
        "particles": 400, "candy": 77, "candy_xl": 0})
    steps = {s["slot"]: s for s in client.get("/api/plan").json()["steps"]}
    assert steps["guard"]["cost_source"] == "observed"
    assert steps["guard"]["candy"] == 77
    # The other slots still come from the group, untouched.
    assert steps["spirit"]["cost_source"] == "group"
    assert steps["spirit"]["candy"] == 50


def test_a_group_can_be_taken_back(client):
    """Recording a guess must be reversible — guessing wrong is worse than
    not knowing."""
    _add(client)
    client.post("/api/cost-groups", json={"species": "charizard", "cost_group": 4})
    assert client.get("/api/plan").json()["steps"][0]["cost_source"] == "group"
    assert client.delete("/api/cost-groups/charizard").status_code == 204
    assert client.get("/api/plan").json()["steps"][0]["cost_source"] == "unknown"


def test_the_group_table_says_it_is_not_niantic(client):
    """The provenance rule, at the API boundary. These numbers are the one
    part of the cost engine Niantic does not publish."""
    body = client.get("/api/cost-groups").json()
    assert body["particles"] == {"1": 400, "2": 600, "3": 800}
    assert body["groups"]["1"]["level_1"] == 50
    assert "not Niantic" in body["source"]
    assert dm.SOURCE_DATE in body["source"]


def test_a_group_outside_one_to_four_is_refused(client):
    for bad in (0, 5, -1):
        r = client.post("/api/cost-groups",
                        json={"species": "charizard", "cost_group": bad})
        assert r.status_code == 422, f"group {bad} was accepted"


def test_the_schema_is_created_however_the_app_is_started(tmp_path, monkeypatch):
    """init_db() used to run only under `if __name__ == "__main__"`.

    So `python app.py` worked and `uvicorn app:app` — which is what SETUP.md's
    NSSM and Task Scheduler advice leads to — came up with no tables. The app
    would start fine and fail on the first request that touched the database.
    """
    monkeypatch.setenv("POGO_FORGE_DB", str(tmp_path / "fresh.db"))
    import importlib
    import sqlite3
    import app as A
    importlib.reload(A)

    assert not A.DB_PATH.exists(), "nothing should exist before startup"
    from fastapi.testclient import TestClient
    with TestClient(A.app) as c:                 # entering runs startup
        assert c.get("/api/plan").status_code == 200
    tables = {r[0] for r in sqlite3.connect(A.DB_PATH).execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"pokemon", "max_move", "species_cost_group", "move_cost"} <= tables
