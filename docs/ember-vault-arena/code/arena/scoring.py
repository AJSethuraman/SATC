from __future__ import annotations

"""Scoring table, caps, the no-farming rules, and the placement comparator.

The engine owns ``_score`` (which writes to the store); this module owns every
NUMBER and every DECISION about whether a point is earned.  Helpers that touch
per-agent counters are marked "mutating" — they are the single place a cap or a
no-farming ledger is advanced, so a new call site cannot forget it.
"""

import hashlib
from types import MappingProxyType
from typing import Any, Mapping


SCORING_VERSION = "ember-vault-scoring-0.2"

SCORING: Mapping[str, int] = MappingProxyType(
    {
        "seal_activated": 5,
        "monster_hit": 1,  # per successful hit, capped per agent per round
        "guardian_finishing_blow": 3,
        "warden_finishing_blow": 5,
        "cache_first_find": 2,
        "crown_taken": 4,
        "attunement_round": 2,
        "secret_objective": 6,
        "survived_act_ii": 2,
        "direct_elimination": 2,  # max once per victim
        "invalid_action": -2,
        "invalid_output": -2,
        "extraction": 10,  # on top of first place, for display
    }
)

MONSTER_HIT_POINT_CAP_PER_ROUND = 3
ROUND_HIT_COUNTER = "monster_hit_points_this_round"

# Collateral damage may eliminate, but it scores NOTHING and its kill events are
# flagged as accidents.
COLLATERAL_SCORES_NOTHING = True

# The ruleset reads "take Crown +4" without qualification, so every take pays.
# It is not farmable: an agent gets one action per round, so a drop-and-retake
# cycle costs two rounds and destroys the attunement progress that is the only
# route to the +10 extraction.  ``crown["taken_by"]`` is tracked regardless, so
# flipping this to a first-take-only policy is a one-line change.
CROWN_TAKE_FIRST_ONLY = False

SURVIVAL_ACT = 2  # "survive through Act II" == alive at the end of round 7

OBJECTIVE_DEFS: Mapping[str, Mapping[str, Any]] = MappingProxyType(
    {
        "monster_hunter": {
            "id": "monster_hunter",
            "description": "Deal at least 8 credited damage to monsters.",
            "metric": "monster_damage",
            "required": 8,
        },
        "lorekeeper": {
            "id": "lorekeeper",
            "description": "Set foot in both gate rooms before the match ends.",
            "metric": "gate_rooms_visited",
            "required": 2,
        },
        "oathbreaker": {
            "id": "oathbreaker",
            "description": "Deal at least 4 credited damage to other agents.",
            "metric": "agent_damage",
            "required": 4,
        },
        "treasure_hoarder": {
            "id": "treasure_hoarder",
            "description": "End the match carrying at least 8 points of loot value.",
            "metric": "loot_value",
            "required": 8,
        },
    }
)


def points_for(category: str) -> int:
    return SCORING[category]


# ---------------------------------------------------------------------------
# per-round monster damage cap
# ---------------------------------------------------------------------------


def monster_hit_points_available(agent: Mapping[str, Any]) -> int:
    """Peek without spending — used by the observation's score_breakdown."""
    spent = agent.get(ROUND_HIT_COUNTER, 0)
    return max(0, MONSTER_HIT_POINT_CAP_PER_ROUND - spent)


def register_monster_hit(agent: dict[str, Any]) -> int:
    """MUTATING. Returns the points earned for this hit and spends the cap slot.

    Collateral damage must NOT call this: it neither scores nor consumes a slot.
    """
    spent = agent.get(ROUND_HIT_COUNTER, 0)
    agent[ROUND_HIT_COUNTER] = spent + 1
    return 1 if spent < MONSTER_HIT_POINT_CAP_PER_ROUND else 0


def reset_round_counters(agent: dict[str, Any]) -> dict[str, Any]:
    """MUTATING. Call in the same round-start loop that zeroes guard.

    Returns a ``changes`` fragment so the reset is visible in ``round_started``.
    """
    before = agent.get(ROUND_HIT_COUNTER, 0)
    agent[ROUND_HIT_COUNTER] = 0
    if before:
        return {ROUND_HIT_COUNTER: [before, 0]}
    return {}


# ---------------------------------------------------------------------------
# kills
# ---------------------------------------------------------------------------


def finishing_blow(monster_id: str) -> tuple[str | None, int]:
    """(category, points) for the killing blow on a monster."""
    if monster_id == "crown_warden":
        return "warden_finishing_blow", SCORING["warden_finishing_blow"]
    if monster_id in {"ironwood_guardian", "ossuary_guardian"}:
        return "guardian_finishing_blow", SCORING["guardian_finishing_blow"]
    return None, 0


def register_direct_elimination(killer: dict[str, Any], victim_id: str) -> int:
    """MUTATING. +2 the first time this killer eliminates this victim, else 0."""
    victims = killer.setdefault("direct_eliminations", [])
    if victim_id in victims:
        return 0
    victims.append(victim_id)
    victims.sort()
    return SCORING["direct_elimination"]


# ---------------------------------------------------------------------------
# crown and caches
# ---------------------------------------------------------------------------


def crown_take_points(crown: Mapping[str, Any], agent_id: str) -> int:
    """Points for a take. ``crown["taken_by"]`` must not yet include this take."""
    if CROWN_TAKE_FIRST_ONLY and agent_id in crown.get("taken_by", []):
        return 0
    return SCORING["crown_taken"]


def cache_find_points(cache: Mapping[str, Any]) -> int:
    """+2 to the FIRST agent to find a given cache; 0 to anybody after."""
    return 0 if cache.get("found") else SCORING["cache_first_find"]


# ---------------------------------------------------------------------------
# secret objectives
# ---------------------------------------------------------------------------


def objective_progress(state: Mapping[str, Any], agent_id: str, objective: str) -> dict[str, Any]:
    """Pure read of tracked counters. Safe to publish to the owning agent."""
    from . import items  # local import keeps this module import-light

    agent = state["agents"][agent_id]
    definition = OBJECTIVE_DEFS[objective]
    metric = definition["metric"]
    gate_rooms = set(state.get("seals", {}))
    values = {
        "monster_damage": agent.get("monster_damage", 0),
        "agent_damage": agent.get("agent_damage", 0),
        "gate_rooms_visited": len(gate_rooms & set(agent.get("visited", []))),
        "loot_value": items.loot_value(agent.get("inventory", [])),
    }
    current = values[metric]
    required = definition["required"]
    return {
        "id": definition["id"],
        "description": definition["description"],
        "reward_points": SCORING["secret_objective"],
        "progress": {metric: current, "required": required, "met": current >= required},
    }


def objective_complete(state: Mapping[str, Any], agent_id: str, objective: str) -> bool:
    return bool(objective_progress(state, agent_id, objective)["progress"]["met"])


# ---------------------------------------------------------------------------
# placement
# ---------------------------------------------------------------------------


def _tie_break_digest(seed: Any, agent_id: str) -> str:
    """Deterministic seeded tie-break that does NOT touch the HashRNG counter.

    Consuming a HashRNG roll here would shift the dice stream for every replay,
    so the last-resort ordering is a standalone SHA-256 over (seed, agent_id).
    """
    material = f"{seed}:placement:{agent_id}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def placement_key(state: Mapping[str, Any], agent: Mapping[str, Any]) -> tuple:
    """Sort ascending. Escaped winner first, then score desc, then the chain."""
    crown = state.get("crown", {})
    hold_rounds = crown.get("hold_rounds_by_agent", {}).get(agent["id"], 0)
    max_rounds = state.get("max_rounds", 12)
    # Alive/escaped agents count as "eliminated after the last round" so that
    # "later elimination / still alive first" is one comparison, not two.
    eliminated_round = agent.get("eliminated_round")
    survival_rank = max_rounds + 1 if eliminated_round is None else eliminated_round
    return (
        0 if agent["id"] == state.get("winner_agent_id") and agent.get("status") == "escaped" else 1,
        -agent.get("score", 0),
        -survival_rank,
        -hold_rounds,
        -agent.get("monster_damage", 0),
        agent.get("invalid_actions", 0),
        _tie_break_digest(state.get("seed"), agent["id"]),
        agent["id"],
    )


def placement_order(state: Mapping[str, Any]) -> list[str]:
    agents = [state["agents"][agent_id] for agent_id in sorted(state["agents"])]
    agents.sort(key=lambda agent: placement_key(state, agent))
    return [agent["id"] for agent in agents]


def placements(state: Mapping[str, Any]) -> dict[str, int]:
    return {
        agent_id: index
        for index, agent_id in enumerate(placement_order(state), start=1)
    }


# ---------------------------------------------------------------------------
# observation helper
# ---------------------------------------------------------------------------


def score_breakdown_view(state: Mapping[str, Any], agent_id: str) -> dict[str, Any]:
    """SELF ONLY. ``limits`` exists so a spent cap does not look like the
    referee silently ignoring hits."""
    agent = state["agents"][agent_id]
    crown = state.get("crown", {})
    breakdown = agent.get("score_breakdown", {})
    return {
        "total": agent.get("score", 0),
        "by_category": [
            {"category": category, "points": breakdown[category]}
            for category in sorted(breakdown)
        ],
        "limits": {
            "monster_hit_points_this_round": agent.get(ROUND_HIT_COUNTER, 0),
            "monster_hit_points_cap": MONSTER_HIT_POINT_CAP_PER_ROUND,
            "agents_you_have_already_eliminated": list(
                agent.get("direct_eliminations", [])
            ),
            "attunement_rounds_completed": crown.get("hold_rounds_by_agent", {}).get(
                agent_id, 0
            ),
            "survived_act_ii_awarded": "survived_act_ii" in breakdown,
        },
    }
