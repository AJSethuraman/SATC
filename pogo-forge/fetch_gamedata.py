"""
Build gamedata.json from Niantic's published game master.

The full game master is ~19MB; this pulls out the four tables the cost
calculator needs and nothing else. Re-run it after a major game update.

    python fetch_gamedata.py

Source: PokeMiners/game_masters, which mirrors the file the client downloads.
Nothing here is a community estimate — it's the game's own numbers.
"""

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


def fetch(url: str) -> list:
    print(f"downloading {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def build(gm: list) -> dict:
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
                {"to": b["evolution"], "candy": b.get("candyCost")}
                for b in (s.get("evolutionBranch") or [])
                if b.get("evolution") and b.get("candyCost") is not None
            ]
            species[pid] = {
                "dex": int(m.group(1)),
                "atk": stats["baseAttack"],
                "def": stats["baseDefense"],
                "sta": stats["baseStamina"],
                "third_move_dust": third.get("stardustToUnlock"),
                "third_move_candy": third.get("candyToUnlock"),
                "evolves_to": evolves,
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
        "cpm": cpm,
        "type_chart": chart,
        # Minimum IV per stat by encounter source. These decide whether a
        # catch can ever be a good PvP Pokemon, so they belong next to the
        # rest of the fixed data.
        "iv_floors": {
            "wild": 0, "wild_weather": 4, "egg": 10, "raid": 10,
            "raid_weather": 10, "research": 10, "shadow_raid": 6,
            "trade": 1, "lucky": 12, "good_friend_trade": 1,
        },
        "upgrade": {
            "dust": upgrades["stardustCost"],
            "candy": upgrades["candyCost"],
            "xl_candy": upgrades["xlCandyCost"],
            "xl_from_level": upgrades["xlCandyMinPokemonLevel"],
            "max_level": upgrades["maxNormalUpgradeLevel"],
            "best_buddy_bonus": upgrades.get("defaultCpBoostAdditionalLevel", 1),
            "shadow_dust_mult": upgrades["shadowStardustMultiplier"],
            "shadow_candy_mult": upgrades["shadowCandyMultiplier"],
            "purified_dust_mult": upgrades["purifiedStardustMultiplier"],
            "purified_candy_mult": upgrades["purifiedCandyMultiplier"],
        },
        "species": species,
    }


if __name__ == "__main__":
    data = build(fetch(SRC))
    OUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.name}: {len(data['species'])} species, {kb:.0f}KB", file=sys.stderr)
