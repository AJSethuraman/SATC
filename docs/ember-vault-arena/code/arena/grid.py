"""Tactical positioning: tiles inside rooms, movement range, and reach.

Before this module a room was a bucket -- you were in it or you were not, and
"range" did not exist as a concept.  Everything in the same room could hit
everything else, so position carried no information and Speed only broke
initiative ties.

Each room is now a small grid.  Bodies occupy a tile, movement is limited by
range, and an attack needs reach.  Two deliberate rulings live here:

1. MOVE RANGE = 1 + Speed.  Vanguard 1, Mystic 2, Scoundrel 3, Scout 4.  This
   is the first thing Speed has ever done besides initiative.

2. ATTACK REACH is per build, and is where the Mystic finally earns its
   fragility: Vanguard 1, Scoundrel 1, Scout 2, Mystic 3.  The 640-match
   simulation measured the Mystic at a 15.8% win rate against a 25% fair share
   -- 5.4 standard errors low, stable across every batch -- because it had
   Scout-tier HP with no compensating strength.  Reach is that compensation:
   it can now open fire from outside a Vanguard's step.  This is a balance
   change and must be re-simulated, not assumed.

Distance is Chebyshev (8-directional), so diagonals cost the same as
orthogonals.  That keeps reach circles square and legal-move sets small enough
to enumerate exhaustively, which is what lets legality and enumeration share
one predicate.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

GRID_VERSION = "ember-vault-grid-0.3"

# Per-room grid, the tile each doorway sits on, and named feature tiles.
# Door tiles are the only way between rooms: to transit you must be able to
# reach the door, which makes chokepoints real.
ROOM_GRIDS: dict[str, dict[str, Any]] = {
    "threshold": {
        "w": 5, "h": 3,
        "doors": {"ironwood_gate": (0, 1), "ossuary_gate": (4, 1)},
        "features": {},
        "spawn": [(2, 2), (1, 2), (3, 2), (2, 1), (1, 1), (3, 1), (0, 2), (4, 2)],
    },
    "ironwood_gate": {
        "w": 5, "h": 4,
        "doors": {"threshold": (2, 3), "vault": (2, 0)},
        "features": {"seal": (4, 0), "cache": (0, 0)},
        "spawn": [(2, 3), (1, 3), (3, 3), (2, 2), (1, 2), (3, 2), (0, 3), (4, 3)],
    },
    "ossuary_gate": {
        "w": 5, "h": 4,
        "doors": {"threshold": (2, 3), "vault": (2, 0)},
        "features": {"seal": (0, 0), "cache": (4, 0)},
        "spawn": [(2, 3), (1, 3), (3, 3), (2, 2), (1, 2), (3, 2), (0, 3), (4, 3)],
    },
    "vault": {
        "w": 7, "h": 5,
        "doors": {"ironwood_gate": (0, 4), "ossuary_gate": (6, 4), "egress": (3, 0)},
        "features": {"pedestal": (3, 2)},
        "spawn": [(3, 4), (2, 4), (4, 4), (1, 4), (5, 4), (0, 4), (6, 4), (3, 3)],
    },
    "egress": {
        "w": 3, "h": 2,
        "doors": {"vault": (1, 1)},
        "features": {},
        "spawn": [(1, 1), (0, 1), (2, 1), (1, 0), (0, 0), (2, 0), (1, 1), (0, 1)],
    },
}

# Move range = 1 + Speed. Reach is a flat per-build property.
BUILD_REACH: dict[str, int] = {
    "vanguard": 1,
    "scoundrel": 1,
    "scout": 2,
    "mystic": 3,
}
MONSTER_REACH: dict[str, int] = {
    "ironwood_guardian": 1,
    "ossuary_guardian": 1,
    "crown_warden": 2,
}
MONSTER_STEP = 1  # monsters close one tile per round


def grid_for(room: str) -> dict[str, Any]:
    return ROOM_GRIDS[room]


def in_bounds(room: str, tile: Iterable[int]) -> bool:
    g = ROOM_GRIDS.get(room)
    if not g:
        return False
    x, y = tuple(tile)[:2]
    return 0 <= int(x) < g["w"] and 0 <= int(y) < g["h"]


def distance(a: Iterable[int], b: Iterable[int]) -> int:
    """Chebyshev distance: diagonals cost the same as orthogonals."""
    ax, ay = tuple(a)[:2]
    bx, by = tuple(b)[:2]
    return max(abs(int(ax) - int(bx)), abs(int(ay) - int(by)))


def as_tile(value: Any) -> tuple[int, int] | None:
    """Accept [x, y] or {"x":..,"y":..}; reject anything else."""
    if isinstance(value, Mapping):
        if "x" in value and "y" in value:
            try:
                return int(value["x"]), int(value["y"])
            except (TypeError, ValueError):
                return None
        return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None
    return None


def tile_key(tile: Iterable[int]) -> str:
    x, y = tuple(tile)[:2]
    return f"{int(x)},{int(y)}"


def move_range(speed: int) -> int:
    return 1 + max(0, int(speed))


def reach_for_build(build: str) -> int:
    return BUILD_REACH.get(build, 1)


def door_tile(room: str, neighbor: str) -> tuple[int, int] | None:
    g = ROOM_GRIDS.get(room)
    if not g:
        return None
    t = g["doors"].get(neighbor)
    return tuple(t) if t else None  # type: ignore[return-value]


def feature_tile(room: str, feature: str) -> tuple[int, int] | None:
    g = ROOM_GRIDS.get(room)
    if not g:
        return None
    t = g["features"].get(feature)
    return tuple(t) if t else None  # type: ignore[return-value]


def spawn_tile(room: str, seat_index: int) -> tuple[int, int]:
    g = ROOM_GRIDS[room]
    slots = g["spawn"]
    return tuple(slots[seat_index % len(slots)])  # type: ignore[return-value]


def occupied_tiles(
    state: Mapping[str, Any], room: str, *, exclude: str | None = None
) -> set[tuple[int, int]]:
    """Tiles held by a living body. Two bodies may not share a tile."""
    taken: set[tuple[int, int]] = set()
    for agent in state.get("agents", {}).values():
        if agent.get("status") != "active" or agent.get("room") != room:
            continue
        if exclude is not None and agent.get("id") == exclude:
            continue
        t = as_tile(agent.get("tile"))
        if t:
            taken.add(t)
    for monster in state.get("monsters", {}).values():
        if monster.get("hp", 0) <= 0 or monster.get("room") != room:
            continue
        if exclude is not None and monster.get("id") == exclude:
            continue
        t = as_tile(monster.get("tile"))
        if t:
            taken.add(t)
    return taken


def reachable_tiles(
    state: Mapping[str, Any], room: str, origin: Iterable[int], rng_range: int,
    *, mover_id: str | None = None,
) -> list[tuple[int, int]]:
    """Every free in-bounds tile within range of origin, excluding origin.

    Deliberately range-limited rather than pathfound: a body does not block a
    step past it, only the tile it stands on.  Pathfinding through an
    eight-agent scrum would make legal_actions expensive to enumerate and hard
    for a model to reason about, and this map has no interior walls to route
    around.
    """
    g = ROOM_GRIDS.get(room)
    if not g:
        return []
    start = as_tile(origin)
    if not start:
        return []
    taken = occupied_tiles(state, room, exclude=mover_id)
    out: list[tuple[int, int]] = []
    for x in range(g["w"]):
        for y in range(g["h"]):
            t = (x, y)
            if t == start or t in taken:
                continue
            if distance(start, t) <= rng_range:
                out.append(t)
    out.sort()
    return out


def free_tile_near(
    state: Mapping[str, Any], room: str, preferred: Iterable[int],
    *, mover_id: str | None = None,
) -> tuple[int, int]:
    """The preferred tile if free, else the nearest free one. Deterministic.

    Used when a body must be placed somewhere legal -- arriving through a door,
    or being force-moved out of a collapsing room -- and the obvious tile is
    already held.
    """
    g = ROOM_GRIDS[room]
    want = as_tile(preferred) or (0, 0)
    taken = occupied_tiles(state, room, exclude=mover_id)
    if want not in taken and in_bounds(room, want):
        return want
    candidates = [
        (x, y)
        for x in range(g["w"])
        for y in range(g["h"])
        if (x, y) not in taken
    ]
    if not candidates:
        return want
    candidates.sort(key=lambda t: (distance(want, t), t))
    return candidates[0]


def in_reach(
    attacker_tile: Iterable[int], target_tile: Iterable[int], reach: int
) -> bool:
    a, b = as_tile(attacker_tile), as_tile(target_tile)
    if not a or not b:
        return False
    return distance(a, b) <= max(1, int(reach))


def adjacent_bodies(
    state: Mapping[str, Any], room: str, tile: Iterable[int], *, exclude: set[str]
) -> list[dict[str, Any]]:
    """Living bodies within one tile -- the candidate pool for a stray blow."""
    origin = as_tile(tile)
    if not origin:
        return []
    out: list[dict[str, Any]] = []
    for agent in state.get("agents", {}).values():
        if agent.get("status") != "active" or agent.get("room") != room:
            continue
        if agent.get("id") in exclude:
            continue
        t = as_tile(agent.get("tile"))
        if t and distance(origin, t) <= 1:
            out.append(agent)
    for monster in state.get("monsters", {}).values():
        if monster.get("hp", 0) <= 0 or monster.get("room") != room:
            continue
        if monster.get("id") in exclude:
            continue
        t = as_tile(monster.get("tile"))
        if t and distance(origin, t) <= 1:
            out.append(monster)
    out.sort(key=lambda b: str(b.get("id")))
    return out


def step_toward(
    state: Mapping[str, Any], room: str, origin: Iterable[int],
    goal: Iterable[int], steps: int, *, mover_id: str | None = None,
) -> tuple[int, int]:
    """Greedy deterministic approach, one tile at a time. Used by monsters."""
    cur = as_tile(origin) or (0, 0)
    want = as_tile(goal)
    if not want:
        return cur
    for _ in range(max(0, steps)):
        if distance(cur, want) <= 1:
            break
        taken = occupied_tiles(state, room, exclude=mover_id)
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nxt = (cur[0] + dx, cur[1] + dy)
                if not in_bounds(room, nxt) or nxt in taken:
                    continue
                key = (distance(nxt, want), nxt)
                if best is None or key < best[0]:
                    best = (key, nxt)
        if best is None or best[0][0] >= distance(cur, want):
            break
        cur = best[1]
    return cur
