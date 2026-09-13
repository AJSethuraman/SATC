"""
Build gamedata.json from Niantic's published game master.

The full game master is ~19MB; this pulls out the tables the cost calculator
needs and nothing else. Re-run it after a major game update.

    python fetch_gamedata.py

Source: PokeMiners/game_masters, which mirrors the file the client downloads.

Provenance, precisely: everything written here is read out of Niantic's file
EXCEPT the `community` block, which is typed by hand and labelled as such at
the point it is written. This file's header used to say "Nothing here is a
community estimate" while the IV floors sat in the middle of it; that was
wrong, and the whole design rests on knowing which numbers are Niantic's.

The output carries `version`, the sha256 of the game master it was built from.
Results are a pure function of that file plus the user's inputs, so the stamp
is what turns a refetch from a silent change into a visible one.
"""

import datetime
import hashlib
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

SRC = "https://raw.githubusercontent.com/PokeMiners/game_masters/master/latest/latest.json"
OUT = Path(__file__).parent / "gamedata.json"

# V0282_POKEMON_GARDEVOIR -> base form.  Anything with a suffix is a variant.
BASE_FORM = re.compile(r"^V(\d{4})_POKEMON_([A-Z0-9_]+)$")

# Everything an evolution needs that is not candy. The game master carries all
# of it and the extractor used to drop every field, so the planner would quote
# "Evolve to Bellossom: 100 candy" for an evolution that also needs a Sun
# Stone. Costing only the part that happens to be candy is the same failure as
# guessing: a confident answer that is not the whole answer.
#
# Each entry is (game-master key, how to phrase it). The phrasing takes the
# field's value where it carries one and ignores it where the key alone is the
# requirement.
REQUIREMENTS = [
    ("evolutionItemRequirement", lambda v: f"needs {_item_name(v)}"),
    ("lureItemRequirement", lambda v: f"needs to be at a {_item_name(v)}"),
    ("kmBuddyDistanceRequirement", lambda v: f"needs {v:g} km walked as your buddy"),
    ("mustBeBuddy", lambda v: "needs to be your current buddy"),
    ("onlyDaytime", lambda v: "daytime only"),
    ("onlyNighttime", lambda v: "night-time only"),
    ("onlyFullMoon", lambda v: "full moon only"),
    ("onlyDuskPeriod", lambda v: "dusk only"),
    ("onlyUpsideDown", lambda v: "hold the phone upside down"),
    ("genderRequirement", lambda v: f"{str(v).lower()} only"),
    ("evolutionMoveRequirement", lambda v: f"needs to know {_item_name(v)}"),
]


def _item_name(raw: str) -> str:
    """ITEM_SUN_STONE -> 'Sun Stone'. Left recognisable rather than prettified.

    Unknown prefixes are stripped but the rest is passed through, so a new item
    shows up readable instead of being dropped for not matching a list.
    """
    s = str(raw)
    for prefix in ("ITEM_TROY_DISK_", "ITEM_OTHER_EVOLUTION_STONE_",
                   "ITEM_GEN4_EVOLUTION_", "ITEM_GEN5_EVOLUTION_", "ITEM_"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            if prefix == "ITEM_TROY_DISK_":
                s += "_LURE_MODULE"
            elif prefix.endswith("EVOLUTION_"):
                s = "SINNOH_STONE" if "GEN4" in prefix else "UNOVA_STONE"
            elif prefix == "ITEM_OTHER_EVOLUTION_STONE_":
                s = "EVOLUTION_ITEM_" + s
            break
    return s.replace("_", " ").title()


def fetch(url: str) -> tuple[list, str]:
    """Download the game master and return it with the digest of the bytes.

    The digest is what makes a refetch visible. Results are deterministic given
    a particular game master; they change when Niantic changes one, and without
    a stamp that change is silent.
    """
    print(f"downloading {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=300) as r:
        raw = r.read()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def requirements_of(branch: dict) -> list[str]:
    """Everything this evolution needs besides candy, in plain words."""
    out = []
    for key, phrase in REQUIREMENTS:
        v = branch.get(key)
        if v:
            out.append(phrase(v))
    return out


def build(gm: list, digest: str = "") -> dict:
    upgrades = level = None
    species: dict[str, dict] = {}
    type_chart: dict[str, list] = {}

    for entry in gm:
        d = entry.get("data", {})
        tid = d.get("templateId", "")
        if tid == "POKEMON_UPGRADE_SETTINGS":
            upgrades = d["pokemonUpgrades"]
        elif tid == "PLAYER_LEVEL_SETTINGS":
            level = d["playerLevel"]
        elif "typeEffective" in d:
            te = d["typeEffective"]
            name = te["attackType"].replace("POKEMON_TYPE_", "")
            type_chart[name] = te["attackScalar"]
        elif "pokemonSettings" in d:
            m = BASE_FORM.match(tid)
            if not m:
                continue
            s = d["pokemonSettings"]
            pid = s.get("pokemonId")
            stats = s.get("stats") or {}
            if not pid or "baseAttack" not in stats:
                continue
            name = m.group(2)
            # Prefer the entry whose suffix is exactly the pokemonId; that's
            # the base form. Variants (ALOLA, MEGA...) carry a longer name.
            if name != pid and pid in species:
                continue
            third = s.get("thirdMove") or {}
            # A handful of entries carry an unresolved numeric move id where
            # the name should be. Those are dropped rather than guessed at;
            # a wrong move name here would send someone to spend an Elite TM.
            clean = lambda ms: [m.replace("_FAST", "") for m in (ms or [])
                                if isinstance(m, str)]
            evolves = [
                {"to": b["evolution"], "candy": b.get("candyCost"),
                 # Candy alone is not the price of an evolution. 84 branches
                 # need an item, 28 a gender, 16 a buddy walk, and so on.
                 "needs": requirements_of(b),
                 # Trade evolutions are free of candy when traded. Quoting the
                 # candy without saying so overstates the cost.
                 "free_via_trade": bool(b.get("noCandyCostViaTrade")),
                 # The file's own weight where a branch carries one, not a
                 # verdict on whether the outcome is random. Wurmple is known
                 # to split at random and carries no weight here, so a boolean
                 # derived from this field would assert something the game
                 # master does not say.
                 "likelihood": b.get("evolutionLikelihoodWeight")}
                for b in (s.get("evolutionBranch") or [])
                if b.get("evolution") and b.get("candyCost") is not None
            ]
            # Branches with no candyCost at all are dropped above — Gholdengo
            # is bought with Gimmighoul Coins, not candy. Record that they
            # exist so the planner can say "not costed in candy" rather than
            # "no evolution on file", which is a different and false claim.
            uncosted = [b["evolution"] for b in (s.get("evolutionBranch") or [])
                        if b.get("evolution") and b.get("candyCost") is None]
            species[pid] = {
                "dex": int(m.group(1)),
                "atk": stats["baseAttack"],
                "def": stats["baseDefense"],
                "sta": stats["baseStamina"],
                "third_move_dust": third.get("stardustToUnlock"),
                "third_move_candy": third.get("candyToUnlock"),
                "evolves_to": evolves,
                "evolves_uncosted": uncosted,
                "types": [t.replace("POKEMON_TYPE_", "")
                          for t in (s.get("type"), s.get("type2")) if t],
                "fast": clean(s.get("quickMoves")),
                "charged": clean(s.get("cinematicMoves")),
                # Legacy moves: obtainable only with an Elite TM (or a past
                # event). Getting this wrong wastes a rare item, so it is
                # recorded from the game master rather than inferred.
                "legacy_fast": clean(s.get("eliteQuickMove")),
                "legacy_charged": clean(s.get("eliteCinematicMove")),
                "buddy_km": s.get("kmBuddyDistance"),
            }

    if not (upgrades and level and species):
        raise SystemExit("game master did not contain the expected templates")

    whole = level["cpMultiplier"]

    # Half-level CPM is the quadratic mean of the two neighbouring whole
    # levels. Verified against the published L1.5 value, 0.135137432.
    cpm: dict[str, float] = {}
    for i, v in enumerate(whole):
        lv = i + 1
        cpm[f"{lv}"] = v
        if i + 1 < len(whole):
            cpm[f"{lv}.5"] = math.sqrt((v**2 + whole[i + 1] ** 2) / 2)

    # attackScalar is indexed by the canonical type enum order, which is NOT
    # the order the type templates appear in the game master. Using appearance
    # order silently produces a plausible but wrong chart, so the order is
    # written out explicitly and checked against known relationships in the
    # test suite (Normal into Ghost, Dragon into Fairy, and eight more).
    CANON = ["NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK",
             "BUG", "GHOST", "STEEL", "FIRE", "WATER", "GRASS", "ELECTRIC",
             "PSYCHIC", "ICE", "DRAGON", "DARK", "FAIRY"]
    for atk, row in type_chart.items():
        if len(row) != len(CANON):
            raise SystemExit(f"type row for {atk} has {len(row)} entries, expected 18")
    chart = {atk: {CANON[i]: round(v, 6) for i, v in enumerate(row)}
             for atk, row in type_chart.items()}

    return {
        "source": SRC,
        # The digest of the game master these numbers came out of, and the day
        # it was pulled. Every figure downstream is a pure function of this
        # file plus the user's inputs, so without a stamp a refetch changes
        # answers silently. With one, the change is something you can see.
        "version": digest,
        "fetched": datetime.date.today().isoformat(),
        "cpm": cpm,
        "type_chart": chart,
        # --------------------------------------------------------------------
        # NOT FROM THE GAME MASTER. Everything above and below this block is
        # read out of Niantic's file; these ten numbers are typed in by hand
        # from community documentation.
        #
        # They are here because the header of this file used to claim
        # "Nothing here is a community estimate - it's the game's own numbers"
        # while these sat in the middle of it, and HANDOFF.md said dynamax.py
        # was the only module not sourced from Niantic. Both were false. A
        # search of the game master for a minimum-IV template returns nothing:
        # Niantic does not publish these.
        #
        # Minimum IV per stat by encounter source. Nothing reads them yet;
        # pvp.rank() takes a floor_iv but is not wired to this table.
        # --------------------------------------------------------------------
        "community": {
            "_provenance": "Typed by hand from community documentation. NOT in "
                           "the game master — a search for a minimum-IV "
                           "template returns zero results. Treat as unverified.",
            "iv_floors": {
                "wild": 0, "wild_weather": 4, "egg": 10, "raid": 10,
                "raid_weather": 10, "research": 10, "shadow_raid": 6,
                "trade": 1, "lucky": 12, "good_friend_trade": 1,
            },
        },
        "upgrade": {
            "dust": upgrades["stardustCost"],
            "candy": upgrades["candyCost"],
            "xl_candy": upgrades["xlCandyCost"],
            "xl_from_level": upgrades["xlCandyMinPokemonLevel"],
            "max_level": upgrades["maxNormalUpgradeLevel"],
            "best_buddy_bonus": upgrades.get("defaultCpBoostAdditionalLevel", 1),
            # Niantic's own statement that a level is two power-ups. The cost
            # tables are indexed by whole level and charged once per half
            # step; that was previously an assumption of the cost engine,
            # inferred from the published 1->40 and 40->50 totals matching.
            # It is a fact in the file, so it is read rather than assumed.
            "upgrades_per_level": upgrades["upgradesPerLevel"],
            "xl_min_player_level": upgrades["xlCandyMinPlayerLevel"],
            "shadow_dust_mult": upgrades["shadowStardustMultiplier"],
            "shadow_candy_mult": upgrades["shadowCandyMultiplier"],
            "purified_dust_mult": upgrades["purifiedStardustMultiplier"],
            "purified_candy_mult": upgrades["purifiedCandyMultiplier"],
        },
        "species": species,
    }


if __name__ == "__main__":
    gm, digest = fetch(SRC)
    data = build(gm, digest)
    OUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.name}: {len(data['species'])} species, {kb:.0f}KB",
          file=sys.stderr)
    print(f"game master sha256: {digest}", file=sys.stderr)
