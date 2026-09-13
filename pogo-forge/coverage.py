"""
Type coverage.

The gap this fills: choosing a third team member by asking "what are my first
two both weak to" is a lookup against a fixed 18x18 table, not a judgment
call. Doing it in your head means nobody can check it.

Multipliers come from the game master's own type chart. Dual types multiply,
so a double weakness is 1.6 x 1.6 = 2.56 and a double resistance is
0.390625 x 0.390625, which is close enough to immunity to matter.
"""

from __future__ import annotations

import costs

CHART: dict[str, dict[str, float]] = costs.DATA["type_chart"]
TYPES = sorted(CHART)


def incoming(defender_types: list[str], attack_type: str) -> float:
    """Damage multiplier for one attack type against a defender's typing."""
    mult = 1.0
    for t in defender_types:
        mult *= CHART[attack_type][t]
    return mult


def weaknesses(species: str, threshold: float = 1.0) -> dict[str, float]:
    """Attack types that hit this species for more than neutral."""
    types = costs.base_stats(species)["types"]
    out = {a: incoming(types, a) for a in TYPES}
    return {a: round(m, 4) for a, m in sorted(out.items(), key=lambda kv: -kv[1])
            if m > threshold}


def resistances(species: str) -> dict[str, float]:
    types = costs.base_stats(species)["types"]
    out = {a: incoming(types, a) for a in TYPES}
    return {a: round(m, 4) for a, m in sorted(out.items(), key=lambda kv: kv[1])
            if m < 1.0}


def shared_weaknesses(team: list[str]) -> dict[str, float]:
    """Attack types every member of the team is weak to.

    These are the holes a third pick should close. A type that beats your
    whole team is worse than a type that beats one of them.
    """
    if not team:
        return {}
    sets = [weaknesses(m) for m in team]
    common = set(sets[0])
    for s in sets[1:]:
        common &= set(s)
    return {t: round(min(s[t] for s in sets), 4) for t in sorted(common)}


def suggest_partners(team: list[str], candidates: list[str] | None = None,
                     limit: int = 10) -> list[dict]:
    """Rank candidates by how many of the team's shared weaknesses they resist.

    This does not know anything about movesets, bulk or the current meta — it
    answers exactly one question, which is which typings plug the hole. Treat
    it as a shortlist, not a verdict.
    """
    holes = shared_weaknesses(team)
    if not holes:
        return []
    pool = candidates if candidates is not None else list(costs.SPECIES)
    scored = []
    for name in pool:
        try:
            res = resistances(name)
        except costs.Unknown:
            continue
        covered = {t: res[t] for t in holes if t in res}
        if not covered:
            continue
        # Score by how much damage is actually removed, not just a count.
        score = sum(1 - res[t] for t in covered)
        scored.append({
            "species": name.title(),
            "types": costs.base_stats(name)["types"],
            "covers": sorted(covered),
            "score": round(score, 3),
        })
    scored.sort(key=lambda r: (-len(r["covers"]), -r["score"], r["species"]))
    return scored[:limit]
