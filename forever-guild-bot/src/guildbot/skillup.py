"""Skill-up planning: which recipes to craft to level a profession, cheapest first. Pure logic, no Discord and
no database.

Every recipe has four skill numbers (from the game's own tables, data/skill_ranges.csv): where it is learned,
where it turns yellow, green and gray. Below the yellow number it is orange: a skill-up every time. Yellow
is likely, green is rare, gray never.

"Cheap" here means the least raw material, not gold: a recipe's materials are expanded down to what you
gather (a Bronze Bar counts as the copper and tin behind it), so a 2-bar item beats a 6-bar item at the
same skill-up chance. Prices are not used."""
from __future__ import annotations

import csv
from functools import lru_cache
from math import ceil
from pathlib import Path

YELLOW_CHANCE = 0.75          # a rough, commonly quoted figure; the game does not publish it
LEARNABLE_WITHIN = 20        # an unlearned recipe is only suggested when its orange stretch ends within this many points

DATA = Path(__file__).parent / "data" / "skill_ranges.csv"


@lru_cache(maxsize=1)
def load_ranges(path: str = str(DATA)) -> dict[int, tuple[int, int, int]]:
    """recipe_id -> (learn_at, yellow_at, gray_at)."""
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.reader(line for line in f if not line.startswith("#")):
            if row and row[0].isdigit():
                out[int(row[0])] = (int(row[1]), int(row[2]), int(row[3]))
    return out


def color(skill: int, yellow_at: int, gray_at: int) -> str:
    """'orange', 'yellow', 'green' or 'gray' for a recipe at this skill (the recipe is already learned)."""
    green_at = (yellow_at + gray_at) // 2
    if skill < yellow_at:
        return "orange"
    if skill < green_at:
        return "yellow"
    return "green" if skill < gray_at else "gray"


def raw_cost(recipe_id: int, reagents: dict, makes: dict, maker: dict, _stack=()) -> dict[str, float]:
    """The raw materials behind one craft, as {name: amount}. A material that another recipe makes is replaced
    by that recipe's own materials (per item made); the rest is counted as it is.
    reagents: recipe_id -> [(item_id, name, quantity)]; makes: recipe_id -> items made per craft;
    maker: item_id -> the recipe that makes it."""
    out: dict[str, float] = {}
    for item_id, name, qty in reagents.get(recipe_id, ()):
        src = maker.get(item_id)
        if src is not None and src != recipe_id and src not in _stack and src in reagents and reagents[src]:
            inner = raw_cost(src, reagents, makes, maker, _stack + (recipe_id,))
            per = max(makes.get(src, 1), 1)
            for n, v in inner.items():
                out[n] = out.get(n, 0.0) + v * qty / per
        else:
            out[name] = out.get(name, 0.0) + qty
    return out


def effort(raw: dict[str, float]) -> float:
    return sum(raw.values())


def plan(skill: int, target: int, cands: list[dict]) -> dict:
    """Walk from `skill` up to `target`, always crafting the cheapest recipe that is still orange (a skill-up
    every craft). When nothing orange is left, the cheapest yellow one, counted at YELLOW_CHANCE.
    A candidate: {recipe_id, name, yellow_at, gray_at, effort, reagents: [(item_id, name, qty)]}.
    Returns {'steps': [{recipe, start, end, crafts, kind}], 'reached': skill, 'stuck': bool}."""
    steps: list[dict] = []
    s = skill
    while s < target:
        orange = [c for c in cands if c["learn_at"] <= s < c["yellow_at"]]
        pool, kind = (orange, "orange") if orange else (
            [c for c in cands if c["yellow_at"] <= s < (c["yellow_at"] + c["gray_at"]) // 2], "yellow")
        if not pool:
            break
        best = min(pool, key=lambda c: (c["effort"], c["name"]))
        limit = best["yellow_at"] if kind == "orange" else (best["yellow_at"] + best["gray_at"]) // 2
        end = min(target, limit)
        points = end - s
        crafts = points if kind == "orange" else ceil(points / YELLOW_CHANCE)
        if steps and steps[-1]["recipe"]["recipe_id"] == best["recipe_id"] and steps[-1]["kind"] == kind:
            steps[-1]["end"], steps[-1]["crafts"] = end, steps[-1]["crafts"] + crafts
        else:
            steps.append({"recipe": best, "start": s, "end": end, "crafts": crafts, "kind": kind})
        s = end
    return {"steps": steps, "reached": s, "stuck": s < target}


def shopping_list(steps: list[dict], makes: dict | None = None, maker: dict | None = None) -> list[tuple[str, int]]:
    """What to have in the bag, as the materials the recipes list (a Bronze Bar stays a Bronze Bar).
    A part an earlier step crafts (makes: recipe_id -> items per craft; maker: item_id -> recipe) is used up
    first by later steps and is not on the list: you just made it."""
    made_by = {}
    for iid, rid in (maker or {}).items():
        made_by.setdefault(rid, []).append(iid)
    need: dict[str, float] = {}
    stock: dict[int, float] = {}
    for st in steps:
        for iid, name, qty in st["recipe"]["reagents"]:
            want = qty * st["crafts"]
            used = min(stock.get(iid, 0.0), want)
            stock[iid] = stock.get(iid, 0.0) - used
            if want - used > 0:
                need[name] = need.get(name, 0.0) + want - used
        rid = st["recipe"]["recipe_id"]
        for iid in made_by.get(rid, ()):
            stock[iid] = stock.get(iid, 0.0) + st["crafts"] * max((makes or {}).get(rid, 1), 1)
    return sorted(((n, ceil(q)) for n, q in need.items()), key=lambda kv: (-kv[1], kv[0]))


def cheaper_gamble(skill: int, cands: list[dict], orange_pick: dict | None) -> dict | None:
    """The cheapest yellow recipe right now, but only when, even counting the misses, it costs less per
    skill point than the orange pick (or when there is no orange one at all)."""
    yel = [c for c in cands if color(skill, c["yellow_at"], c["gray_at"]) == "yellow" and c["learn_at"] <= skill]
    if not yel:
        return None
    best = min(yel, key=lambda c: (c["effort"], c["name"]))
    if orange_pick is None or best["effort"] / YELLOW_CHANCE < orange_pick["effort"]:
        return best
    return None


def worth_learning(skill: int, cands: list[dict], limit: int = 4) -> list[dict]:
    """Recipes the character does not know that would still give skill-ups at `skill` (orange first, then yellow,
    cheapest first). Their `learn_at` is not used: the game data's number for it is not the trainer's requirement."""
    # The table says nothing true about where a recipe starts being learnable (its learn_at is 1 for trainer recipes), so
    # an unlearned recipe only counts when its orange stretch ends soon: far-off recipes are not learnable yet.
    pool = [c for c in cands if color(skill, c["yellow_at"], c["gray_at"]) in ("orange", "yellow")
            and c["yellow_at"] - skill <= LEARNABLE_WITHIN]
    return sorted(pool, key=lambda c: (color(skill, c["yellow_at"], c["gray_at"]) != "orange", c["effort"], c["name"]))[:limit]


def materials_text(reagents: list[tuple[int, str, int]]) -> str:
    return ", ".join(f"{qty} {name}" for _i, name, qty in reagents) or "no materials listed"
