"""
PvP rank: where an IV spread sits among all 4,096 possibilities.

Under a CP cap, raw IVs stop mattering and stat product starts. A spread that
keeps attack low can be levelled higher before hitting the cap, which buys more
defense and HP for the same CP. That's why a hundo is usually a mediocre Great
League Pokemon.

Rank 1 is the best possible spread for that species at that cap. The percentage
is stat product relative to rank 1, which is the number that actually matters —
rank 40 at 99.2% is not meaningfully worse than rank 1.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

import costs

IV_RANGE = range(16)
SPREADS = [(a, d, s) for a in IV_RANGE for d in IV_RANGE for s in IV_RANGE]


@lru_cache(maxsize=256)
def _table(species: str, cap: int, floor_iv: int = 0) -> tuple:
    """Every spread ranked by stat product under a CP cap.

    Returns a tuple of (spread, level, cp, stat_product) sorted best first.
    Cached: the work is identical for every Pokemon of a species.
    """
    s = costs.base_stats(species)
    ba, bd, bs = s["atk"], s["def"], s["sta"]

    spreads = [sp for sp in SPREADS if min(sp) >= floor_iv]
    ivs = np.array(spreads, dtype=float)
    n = len(spreads)

    best_level = np.zeros(n)
    best_cp = np.zeros(n, dtype=int)

    atk = ba + ivs[:, 0]
    dfn = bd + ivs[:, 1]
    sta = bs + ivs[:, 2]

    for lv in costs.levels(1.0, costs.MAX_LEVEL):
        m = costs.cpm(lv)
        cp = np.floor(atk * np.sqrt(dfn) * np.sqrt(sta) * m * m / 10)
        cp = np.maximum(cp, 10)
        ok = cp <= cap
        best_level = np.where(ok, lv, best_level)
        best_cp = np.where(ok, cp.astype(int), best_cp)

    usable = best_level > 0
    mult = np.array([costs.cpm(lv) if lv > 0 else 0.0 for lv in best_level])
    product = (atk * mult) * (dfn * mult) * np.floor(sta * mult)
    product = np.where(usable, product, 0.0)

    order = np.argsort(-product, kind="stable")
    return tuple(
        (spreads[i], float(best_level[i]), int(best_cp[i]), float(product[i]))
        for i in order
    )


def rank(species: str, ivs: tuple[int, int, int], cap: int,
         floor_iv: int = 0) -> dict:
    """Where this spread ranks, and what it would look like built out."""
    table = _table(costs.norm(species), cap, floor_iv)
    best_product = table[0][3]
    for i, (sp, lv, cp, prod) in enumerate(table):
        if sp == tuple(ivs):
            return {
                "rank": i + 1,
                "of": len(table),
                "percent": round(prod / best_product * 100, 2) if best_product else 0.0,
                "level": lv,
                "cp": cp,
                "hp": costs.hp_at(species, ivs[2], lv) if lv > 0 else 0,
                "best_spread": list(table[0][0]),
                "best_cp": table[0][2],
                "best_level": table[0][1],
            }
    raise costs.Unknown(f"spread {ivs} not in the table")


def top(species: str, cap: int, n: int = 10) -> list[dict]:
    table = _table(costs.norm(species), cap)
    best = table[0][3]
    return [{"rank": i + 1, "ivs": list(sp), "level": lv, "cp": cp,
             "percent": round(prod / best * 100, 2)}
            for i, (sp, lv, cp, prod) in enumerate(table[:n])]
