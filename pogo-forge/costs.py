"""
Cost engine.

Every number comes from gamedata.json, which is extracted from Niantic's own
game master. Nothing here is estimated. Where something genuinely can't be
determined, the function says so rather than returning a plausible number.

Level notation: a float in 0.5 steps, 1.0 to 50.0 (51.0 with the best-buddy
bonus). Powering up moves half a level at a time.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "gamedata.json").read_text("utf-8"))
CPM: dict[str, float] = DATA["cpm"]
UP = DATA["upgrade"]
SPECIES: dict[str, dict] = DATA["species"]

MAX_LEVEL = float(UP["max_level"])
BEST_BUDDY_MAX = MAX_LEVEL + UP["best_buddy_bonus"]


class Unknown(Exception):
    """Raised when the answer isn't determinable from the data we have."""


# ------------------------------------------------------------------ lookups --
def norm(name: str) -> str:
    return name.strip().upper().replace(" ", "_").replace("-", "_")


def base_stats(name: str) -> dict:
    s = SPECIES.get(norm(name))
    if not s:
        raise Unknown(f"no base stats on file for {name!r}")
    return s


def cpm(level: float) -> float:
    key = f"{level:g}"
    if key not in CPM:
        raise Unknown(f"no CP multiplier for level {level:g}")
    return CPM[key]


def levels(lo: float, hi: float) -> list[float]:
    """Every half-level step from lo up to and including hi."""
    n = round((hi - lo) * 2)
    return [lo + i * 0.5 for i in range(n + 1)]


# --------------------------------------------------------------- CP and HP --
def cp_at(name: str, ivs: tuple[int, int, int], level: float) -> int:
    """CP for a given species, IV spread and level. Floor, minimum 10."""
    s = base_stats(name)
    ia, id_, ih = ivs
    m = cpm(level)
    raw = ((s["atk"] + ia)
           * math.sqrt(s["def"] + id_)
           * math.sqrt(s["sta"] + ih)
           * m * m) / 10
    return max(10, math.floor(raw))


def hp_at(name: str, iv_hp: int, level: float) -> int:
    s = base_stats(name)
    return max(10, math.floor((s["sta"] + iv_hp) * cpm(level)))


def iv_percent(ivs: tuple[int, int, int]) -> float:
    return round(sum(ivs) / 45 * 100, 1)


def max_level_under_cp(name: str, ivs: tuple[int, int, int], cap: int,
                       ceiling: float = BEST_BUDDY_MAX) -> float | None:
    """Highest half-level whose CP stays at or under the cap.

    Returns None when even level 1 exceeds it — the Pokemon can't be used in
    that league at all.
    """
    best = None
    for lv in levels(1.0, ceiling):
        try:
            if cp_at(name, ivs, lv) <= cap:
                best = lv
            else:
                break
        except Unknown:
            break
    return best


# ------------------------------------------------------------------- costs --
@dataclass
class Cost:
    dust: int = 0
    candy: int = 0
    xl_candy: int = 0
    steps: int = 0
    notes: list[str] = field(default_factory=list)

    def __add__(self, o: "Cost") -> "Cost":
        return Cost(self.dust + o.dust, self.candy + o.candy,
                    self.xl_candy + o.xl_candy, self.steps + o.steps,
                    self.notes + o.notes)

    def dict(self) -> dict:
        return asdict(self)


def _step_cost(level: float, shadow: bool, purified: bool) -> tuple[int, int, int]:
    """Cost of one half-level step starting at `level`.

    The tables are indexed by whole level: both half-steps within a level cost
    the same. XL candy replaces regular candy from level 40 up.
    """
    idx = int(level) - 1
    dust_tbl, candy_tbl = UP["dust"], UP["candy"]
    if idx < 0 or idx >= len(dust_tbl):
        raise Unknown(f"no upgrade cost recorded for level {level:g}")

    dust = dust_tbl[idx]
    candy = candy_tbl[idx]
    xl = 0

    if level >= UP["xl_from_level"]:
        xl_idx = int(level) - UP["xl_from_level"]
        xl_tbl = UP["xl_candy"]
        if xl_idx < len(xl_tbl):
            xl = xl_tbl[xl_idx]

    if shadow:
        dust = math.ceil(dust * UP["shadow_dust_mult"])
        candy = math.ceil(candy * UP["shadow_candy_mult"])
        xl = math.ceil(xl * UP["shadow_candy_mult"])
    elif purified:
        dust = math.ceil(dust * UP["purified_dust_mult"])
        candy = math.ceil(candy * UP["purified_candy_mult"])
        xl = math.ceil(xl * UP["purified_candy_mult"])

    return dust, candy, xl


def power_up_cost(from_level: float, to_level: float, *,
                  shadow: bool = False, purified: bool = False) -> Cost:
    if to_level <= from_level:
        return Cost(notes=["Already at or above the target level."])
    if to_level > BEST_BUDDY_MAX:
        raise Unknown(f"level {to_level:g} is above the cap of {BEST_BUDDY_MAX:g}")

    c = Cost()
    # The best-buddy bonus grants +1 level at no cost, so only steps at or
    # below the normal cap are charged.
    paid_to = min(to_level, MAX_LEVEL)
    if paid_to > from_level:
        for lv in levels(from_level, paid_to - 0.5):
            d, cy, xl = _step_cost(lv, shadow, purified)
            c.dust += d
            c.candy += cy
            c.xl_candy += xl
            c.steps += 1

    if to_level > MAX_LEVEL:
        c.notes.append(
            f"The last {to_level - MAX_LEVEL:g} level comes from the Best Buddy "
            f"bonus, which costs nothing but requires Best Buddy status."
        )
    if c.xl_candy:
        c.notes.append("XL Candy is required from level 40 up.")
    if shadow:
        c.notes.append("Shadow surcharge applied.")
    if purified:
        c.notes.append("Purified discount applied.")
    return c


def second_charged_move_cost(name: str) -> Cost:
    s = base_stats(name)
    d, cy = s.get("third_move_dust"), s.get("third_move_candy")
    if d is None or cy is None:
        raise Unknown(f"no second-charged-move cost on file for {name}")
    return Cost(dust=d, candy=cy, notes=["Unlocks the second charged move slot."])


def evolution_path(name: str, to: str) -> list[tuple[str, int]]:
    """Shortest sequence of evolutions from `name` to `to`.

    Returns [(species, candy), ...] for each hop. Handles multi-step lines like
    Ralts to Gardevoir, which is two evolutions, not one.

    Breadth-first, so this is fewest-hops, not cheapest-candy. Evolution lines
    are trees with a single route to any given target, so the two coincide —
    but if that ever stops being true, this returns the shorter path, not the
    cheaper one.
    """
    start, target = norm(name), norm(to)
    if start == target:
        return []
    # Breadth-first: evolution lines are short and never cycle.
    queue: list[tuple[str, list[tuple[str, int]]]] = [(start, [])]
    seen = {start}
    while queue:
        cur, path = queue.pop(0)
        for b in (SPECIES.get(cur, {}).get("evolves_to") or []):
            nxt, hop = b["to"], path + [(b["to"], b["candy"])]
            if nxt == target:
                return hop
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, hop))
    raise Unknown(f"no evolution path from {name.title()} to {to.title()}")


def evolution_cost(name: str, to: str | None = None) -> tuple[Cost, str]:
    s = base_stats(name)
    branches = s.get("evolves_to") or []
    if not branches:
        raise Unknown(f"{name.title()} has no evolution on file")

    if to:
        hops = evolution_path(name, to)
        c = Cost(candy=sum(h[1] for h in hops))
        if len(hops) > 1:
            c.notes.append(
                "Two evolutions: " + " \u2192 ".join(h[0].title() for h in hops))
        return c, hops[-1][0]

    if len(branches) > 1:
        opts = ", ".join(b["to"].title() for b in branches)
        raise Unknown(f"{name.title()} branches — pick one of: {opts}")
    b = branches[0]
    return Cost(candy=b["candy"]), b["to"]


# -------------------------------------------------------------------- plan --
def plan(species: str, *, ivs: tuple[int, int, int], from_level: float,
         goal: str, target_level: float | None = None, cp_cap: int | None = None,
         evolve_to: str | None = None, second_move: bool = False,
         shadow: bool = False, purified: bool = False) -> dict:
    """Cost out a goal.

    goal is one of:
      level   — reach target_level
      cp_cap  — the highest level that stays under cp_cap (Great/Ultra League)
      max     — level 50, or 51 as a best buddy
    """
    final_species = norm(species)
    total = Cost()
    line_items: list[dict] = []

    if evolve_to:
        c, final_species = evolution_cost(species, evolve_to)
        total += c
        line_items.append({"label": f"Evolve to {final_species.title()}", **c.dict()})

    if goal == "level":
        if target_level is None:
            raise Unknown("goal 'level' needs a target level")
        target = float(target_level)
    elif goal == "cp_cap":
        if cp_cap is None:
            raise Unknown("goal 'cp_cap' needs a CP cap")
        target = max_level_under_cp(final_species, ivs, cp_cap)
        if target is None:
            return {"species": final_species,
                    "error": f"Even at level 1 this exceeds {cp_cap} CP."}
        if target < from_level:
            return {"species": final_species,
                    "error": f"Already above {cp_cap} CP at level {from_level:g}. "
                             "Powering up can't be undone."}
    elif goal == "max":
        target = BEST_BUDDY_MAX
    else:
        raise Unknown(f"unknown goal {goal!r}")

    c = power_up_cost(from_level, target, shadow=shadow, purified=purified)
    total += c
    if c.steps:
        line_items.append({
            "label": f"Power up {from_level:g} \u2192 {target:g} ({c.steps} steps)",
            **c.dict()})

    if second_move:
        c = second_charged_move_cost(final_species)
        total += c
        line_items.append({"label": "Unlock second charged move", **c.dict()})

    return {
        "species": final_species.title(),
        "ivs": list(ivs),
        "iv_percent": iv_percent(ivs),
        "from_level": from_level,
        "target_level": target,
        "cp_before": cp_at(final_species, ivs, from_level),
        "cp_after": cp_at(final_species, ivs, target),
        "hp_after": hp_at(final_species, ivs[2], target),
        "line_items": line_items,
        "total": total.dict(),
    }
