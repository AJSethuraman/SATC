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
    moves: dict[str, dict] = {}
    templates: list = []
    variants: list = []

    for entry in gm:
        d = entry.get("data", {})
        tid = d.get("templateId", "")
        if tid == "POKEMON_UPGRADE_SETTINGS":
            upgrades = d["pokemonUpgrades"]
        elif tid == "PLAYER_LEVEL_SETTINGS":
            level = d["playerLevel"]
        elif "moveSettings" in d:
            # What a move actually does. Without power, duration and energy the
            # species tables can name a moveset but cannot rate it — which is
            # why "which of mine is the best Ground attacker" had to be worked
            # out against the raw game master instead of from this file.
            mv = d["moveSettings"]
            mid = mv.get("movementId")
            if not isinstance(mid, str):
                continue          # unresolved numeric id: dropped, never guessed
            moves[mid.replace("_FAST", "")] = {
                "type": str(mv.get("pokemonType", "")).replace("POKEMON_TYPE_", ""),
                "power": mv.get("power", 0) or 0,
                # Seconds, because every formula that uses it wants seconds.
                "duration": (mv.get("durationMs") or 0) / 1000,
                # Niantic's sign convention: a fast move GAINS energy (positive),
                # a charged move SPENDS it (negative). Kept as written rather
                # than normalised, so it still reads like the source.
                "energy": mv.get("energyDelta", 0) or 0,
                "fast": mid.endswith("_FAST"),
            }
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
            # Collect every stats-bearing template. Which of them become their
            # own species is decided in a second pass, once the base form is
            # known to compare against.
            templates.append((m, s))

    for m, s in templates:
            pid = s["pokemonId"]
            stats = s["stats"]
            name = m.group(2)
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
            record = {
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

            if name == pid:
                # The base form. Its suffix is exactly the pokemonId.
                species[pid] = record
            else:
                # A variant: Alolan, Galarian, Hisuian, Zen, Origin, and so on.
                # Held aside and only kept if it actually differs -- decided
                # below, once every base form is known.
                variants.append((name, pid, record))

    # ------------------------------------------------------------ variants --
    # Regional and alternate forms used to be dropped entirely, so asking for
    # Alolan Ninetales silently answered about the Kanto one -- Fire, when the
    # real answer is Ice/Fairy. That was handoff gap 6.
    #
    # The filter is that a form earns its own entry only when its stats or its
    # typing actually differ from the base. 1,288 of the variant templates are
    # costumes and _NORMAL duplicates that match their base exactly and would
    # only bloat the file; 158 are real.
    # Two pokemonIds — Nidoran female and male — carry no template whose suffix
    # equals the id, so neither got a base form above. Both have exactly one
    # distinct stat set across their templates, so promoting one is safe rather
    # than a choice between real alternatives. Promote deterministically by
    # shortest suffix, and assert the safety rather than trusting it.
    for pid in {p for _, p, _ in variants} - set(species):
        mine = sorted((n, r) for n, p, r in variants if p == pid)
        distinct = {(r["atk"], r["def"], r["sta"], tuple(r["types"]))
                    for _, r in mine}
        if len(distinct) > 1:
            raise SystemExit(
                f"{pid} has no base-form template and its variants disagree on "
                f"stats: {distinct}. Promoting one would be a guess.")
        species[pid] = min(mine, key=lambda nr: (len(nr[0]), nr[0]))[1]

    forms: dict[str, dict] = {}
    for name, pid, record in variants:
        if species.get(pid) is record:
            continue                      # promoted above; it IS the base now
        base = species.get(pid)
        if base and (base["atk"], base["def"], base["sta"], base["types"]) == (
                record["atk"], record["def"], record["sta"], record["types"]):
            continue
        record["base_form"] = pid
        forms[name] = record
    species.update(forms)

    # Aliases, because nobody types "NINETALES_ALOLA". Built from the data
    # rather than hand-listed, so a new region needs no code change: the
    # suffix is whatever the game master calls it, and the reversed spelling
    # plus the -N/-AN endings people actually use are generated from it.
    ENDINGS = {"ALOLA": "ALOLAN", "GALAR": "GALARIAN", "HISUI": "HISUIAN",
               "PALDEA": "PALDEAN", "GALARIAN": "GALAR", "ALOLAN": "ALOLA",
               "HISUIAN": "HISUI", "PALDEAN": "PALDEA"}
    aliases: dict[str, str] = {}
    for key, record in forms.items():
        pid = record["base_form"]
        if not key.startswith(pid + "_"):
            continue
        suffix = key[len(pid) + 1:]
        spellings = {suffix} | {ENDINGS[p] + suffix[len(p):]
                                for p in ENDINGS if suffix.startswith(p)}
        # A compound suffix also answers to its region word alone: Galarian
        # Darmanitan is GALARIAN_STANDARD in the file, and nobody types that.
        # Where the short spelling is ambiguous (Galarian Darmanitan is both
        # Standard and Zen) the sorted() below makes the winner deterministic
        # and setdefault keeps the first — Standard, which is the one people
        # mean. The full key still resolves the other exactly.
        region = suffix.split("_")[0]
        if region != suffix:
            spellings |= {region} | {ENDINGS[region]} if region in ENDINGS else {region}
        for sp in sorted(spellings):
            for alias in (f"{sp}_{pid}", f"{pid}_{sp}"):
                # Never shadow a real species key.
                if alias not in species:
                    aliases.setdefault(alias, key)

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
        # move -> what it does. Keyed without the _FAST suffix, the same way
        # the species move lists are.
        "moves": moves,
        # alternative spellings -> the canonical species key
        "aliases": aliases,
    }


if __name__ == "__main__":
    gm, digest = fetch(SRC)
    data = build(gm, digest)
    OUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.name}: {len(data['species'])} species, {kb:.0f}KB",
          file=sys.stderr)
    print(f"game master sha256: {digest}", file=sys.stderr)
