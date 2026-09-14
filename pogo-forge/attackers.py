"""
Rate a Pokemon as a raid attacker, and rate a collection by type.

The question this answers is not "what is the best Ground attacker" — a list
anyone can look up — but "can I field six of them, out of what I actually own".
A raid party is six. One excellent Pokemon of a type and five empty slots loses
the back half of the fight.

Two things this module is careful about, both learned the hard way.

**A flat DPS bar is not comparable across types.** The best realistically
obtainable Ice attacker does about 13.1 DPS; the best Fighting attacker does
16.5. Scoring both against one number calls a finished Ice roster a crisis and
a thin Fighting roster fine. Everything here is scored against the ceiling of
its own type.

**DPS alone over-rates glass cannons.** Pheromosa tops raw Fighting DPS and has
85 defence: it dies immediately and you spend the raid re-entering. `bulk` is a
crude survivability weighting to sit beside DPS, not replace it — it is not the
blended rating community tier lists use, and the ordering it gives should be
read as directional.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import costs

MOVES: dict[str, dict] = costs.DATA["moves"]
CHART: dict[str, dict[str, float]] = costs.DATA["type_chart"]
TYPES = sorted(CHART)

# A neutral target. Raid bosses sit either side of this; the figure only has to
# be consistent, because every number here is used as a comparison.
NEUTRAL_DEFENCE = 180.0
STAB = 1.2
# Niantic's own, from BATTLE_SETTINGS.
SHADOW_ATTACK = 1.2
SHADOW_DEFENCE = 0.8333333
# A slot is worth taking into a raid at this share of its type's ceiling. Not a
# law — the point of expressing it as a share is that it travels across types.
GOOD_ENOUGH = 0.85
PARTY = 6


class NoMoveset(Exception):
    """The species has no same-type fast + charged pair for this type."""


@dataclass
class Rating:
    dps: float
    bulk: float
    fast: str
    charged: str

    def dict(self) -> dict:
        return {"dps": round(self.dps, 2), "bulk": round(self.bulk, 1),
                "fast": self.fast, "charged": self.charged}


def _cycle_dps(atk: float, types: list[str], fast: str, charged: str,
               defence: float = NEUTRAL_DEFENCE) -> float | None:
    """Damage per second over one charged-move cycle.

    GO's damage formula floors to an integer and adds one, which is why this
    is computed per move rather than as a smooth product — the flooring is
    real and at low move power it visibly quantises the result.
    """
    f, c = MOVES.get(fast), MOVES.get(charged)
    if not f or not c or f["duration"] <= 0 or c["duration"] <= 0 or f["energy"] <= 0:
        return None
    a = atk * costs.cpm(40.0)

    def hit(mv: dict) -> int:
        stab = STAB if mv["type"] in types else 1.0
        return math.floor(0.5 * mv["power"] * (a / defence) * stab) + 1

    n = math.ceil(abs(c["energy"]) / f["energy"])
    return (n * hit(f) + hit(c)) / (n * f["duration"] + c["duration"])


def rate(species: str, attack_type: str, *, iv_atk: int = 15,
         shadow: bool = False) -> Rating:
    """Best same-type moveset for this species attacking with `attack_type`.

    Both moves must be the attack type. A Fighting fast move with a Dark
    charged move is not a Fighting attacker; it is two half-attackers, and
    counting it as either overstates what it does.
    """
    s = costs.base_stats(species)
    atk = (s["atk"] + iv_atk) * (SHADOW_ATTACK if shadow else 1.0)
    dfn = (s["def"] + 15) * (SHADOW_DEFENCE if shadow else 1.0)
    best: Rating | None = None
    for fast in s["fast"] + s["legacy_fast"]:
        if MOVES.get(fast, {}).get("type") != attack_type:
            continue
        for charged in s["charged"] + s["legacy_charged"]:
            if MOVES.get(charged, {}).get("type") != attack_type:
                continue
            d = _cycle_dps(atk, s["types"], fast, charged)
            if d is None:
                continue
            ehp = (s["sta"] + 15) * costs.cpm(40.0) * (dfn * costs.cpm(40.0)) / 100
            r = Rating(d, d * ehp / 10, fast, charged)
            if best is None or r.dps > best.dps:
                best = r
    if best is None:
        raise NoMoveset(
            f"{species.title()} has no {attack_type.title()} fast and charged "
            "move pair, so it cannot attack with that type.")
    return best


def _ceiling(attack_type: str) -> Rating:
    """The best any species in the data reaches with this type.

    Megas are excluded: you field one at a time, so they are not the bar a
    party slot is measured against.
    """
    best = None
    for key in costs.SPECIES:
        try:
            r = rate(key, attack_type)
        except (NoMoveset, costs.Unknown):
            continue
        if best is None or r.dps > best.dps:
            best = r
    return best


_CEILINGS: dict[str, Rating] = {}


def ceiling(attack_type: str) -> Rating:
    if attack_type not in _CEILINGS:
        c = _ceiling(attack_type)
        if c is None:
            raise NoMoveset(f"nothing in the data attacks with {attack_type}")
        _CEILINGS[attack_type] = c
    return _CEILINGS[attack_type]


def offensive_value(attack_type: str) -> list[str]:
    """Which defending types this attack type beats.

    Normal beats nothing, so a Normal attacker is worth building for no raid
    however high its DPS. That is information the ranking has to carry.
    """
    return [d for d in TYPES if CHART[attack_type][d] > 1.0]


def coverage(collection: list[dict]) -> list[dict]:
    """How deep the collection goes in each attacking type.

    `collection` is a list of {species, shadow, iv_atk, ...} — whatever the
    importer produced. Types nothing is weak to are reported with hits 0 and
    sorted last rather than hidden, because "you have six Normal attackers and
    they are all useless" is worth being able to see.
    """
    out = []
    for t in TYPES:
        try:
            top = ceiling(t)
        except NoMoveset:
            continue
        bar = top.dps * GOOD_ENOUGH
        members = []
        for mon in collection:
            try:
                r = rate(mon["species"], t, iv_atk=mon.get("iv_atk", 15),
                         shadow=bool(mon.get("shadow")))
            except (NoMoveset, costs.Unknown):
                continue
            members.append({**mon, **r.dict(),
                            "share": round(r.dps / top.dps * 100, 1),
                            "strong": r.dps >= bar})
        members.sort(key=lambda m: -m["dps"])
        strong = [m for m in members if m["strong"]]
        hits = offensive_value(t)
        out.append({
            "type": t,
            "hits": len(hits),
            "beats": hits,
            "ceiling": round(top.dps, 2),
            "ceiling_moveset": f"{top.fast} + {top.charged}",
            "bar": round(bar, 2),
            "strong": len(strong),
            "usable": len(members),
            "short": max(0, PARTY - len(strong)),
            "members": members[:PARTY],
        })
    # Worst hole in the most valuable type first. A type nothing is weak to
    # sorts last however empty it is.
    out.sort(key=lambda r: (-(r["hits"] * r["short"]), -r["hits"], r["strong"]))
    return out
