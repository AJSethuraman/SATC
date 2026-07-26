from __future__ import annotations

"""Deterministic last-6 episodic memory, projected from committed events.

There is no second memory store.  The only source is the append-only event log,
so for a given seed the log prefix visible at round R is byte-identical across
runs and there is nothing that can fall out of sync.

Determinism argument:
 1. Single append-only source; events are never mutated or deleted.
 2. ``ordinal`` is unique within a match, so ``(priority_rank, -ordinal)`` is a
    TOTAL order.  There is never a tie to break, so this module never calls
    HashRNG — which also means it cannot shift the dice stream.
 3. No run-dependent inputs: ``seq`` (globally autoincrementing) and
    ``created_at`` (wall clock) are dropped at the store boundary.
 4. Relevance is a WHITELIST keyed on ``event_type``; a new telemetry event can
    never silently reshuffle anyone's memory.
 5. Pure function of (event_log, agent_id, current_round).
"""

import json
from typing import Any, Mapping, Sequence


MEMORY_VERSION = "ember-vault-memory-0.2"

MEMORY_LIMIT = 6
MEMORY_WINDOW_ROUNDS = 4  # current round + 4 prior
MEMORY_TEXT_MAX = 160

# index = priority rank, 0 = most salient. PUBLISHED to agents.
MEMORY_PRIORITY: tuple[str, ...] = (
    "damage_received",
    "damage_dealt",
    "elimination_involving_me",
    "crown_change",
    "seal_change",
    "item_change",
    "speech_to_me",
    "observed_elimination",
)

START_ROOM = "threshold"

# event_type -> family. classify_event turns a family plus the agent's relation
# to the event into exactly one MEMORY_PRIORITY class.
RELEVANT_EVENT_TYPES: Mapping[str, str] = {
    # damage
    "attack_hit": "damage",
    "attack_agent": "damage",
    "attack_monster": "damage",
    "monster_attack": "damage",
    "wild_swing_self_damage": "damage",
    "wild_swing_bystander": "damage",
    "wild_swing_room_reaction": "damage",
    # elimination
    "agent_eliminated": "elimination",
    # crown
    "crown_unlocked": "crown",
    "crown_revealed": "crown",
    "crown_taken": "crown",
    "crown_dropped": "crown",
    "crown_attuned": "crown",
    "crown_extracted": "crown",
    "crown_escaped": "crown",
    # seals, contraction and forced relocation
    "seal_activated": "seal",
    "seal_voided": "seal",
    "vault_gate_opened": "seal",
    "vault_gate_permanently_closed": "seal",
    "vault_unlocked": "seal",
    "room_contracting": "seal",
    "room_sealing": "seal",
    "room_sealed": "seal",
    "agent_force_moved": "seal",
    # items
    "item_taken": "item",
    "item_used": "item",
    "item_dropped": "item",
    "cache_found": "item",
    "search_success": "item",
    "search_failure": "item",
    "wild_swing_self_drop": "item",
    # speech
    "agent_speech": "speech",
}

IGNORED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "dice_roll",
        "agent_resource_update",
        "round_started",
        "round_narration",
        "initiative_order",
        "action_skipped",
        "match_started",
        "act_started",
        "act_two_survival",
        "guard",
        "move",
        "rest",
        "attack_miss",
        "wild_swing_no_bystander",
        "monster_guard",
        "monster_defeated",
        "monster_entombed",
        "floor_items_relocated",
        "invalid_action_fallback",
        "invalid_output_fallback",
        "stale_action",
        "objective_reveal",
        "final_scores",
    }
)

# Events that reposition an agent; folded to reconstruct where it stood.
_MOVE_EVENT_TYPES = ("move", "agent_force_moved", "crown_extracted")


def memory_policy() -> dict[str, Any]:
    """Shipped inside every observation: an agent should be able to reason about
    what it is NOT being shown."""
    return {
        "limit": MEMORY_LIMIT,
        "window_rounds": MEMORY_WINDOW_ROUNDS,
        "priority": list(MEMORY_PRIORITY),
        "source": "committed_event_log",
        "version": MEMORY_VERSION,
    }


def is_known_event_type(event_type: str) -> bool:
    return event_type in RELEVANT_EVENT_TYPES or event_type in IGNORED_EVENT_TYPES


def normalize_event_log(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Read-only projection of committed events, ordered as given.

    DELIBERATELY DROPS ``seq`` (globally autoincrementing, so it differs between
    databases holding different numbers of matches) and ``created_at`` (wall
    clock).  Either leaking into an observation would make prompt bytes — and
    therefore the audit chain — run-dependent.  ``ordinal`` is the per-match
    index and is the only ordering identity allowed to leave the store.
    """
    normalized: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows):
        payload = row.get("payload")
        if payload is None and isinstance(row.get("payload_json"), str):
            try:
                payload = json.loads(row["payload_json"])
            except ValueError:
                payload = {}
        normalized.append(
            {
                "ordinal": ordinal,
                "round_no": row.get("round_no", 0),
                "phase": row.get("phase", ""),
                "event_type": row.get("event_type", ""),
                "actor_id": row.get("actor_id"),
                "target_id": row.get("target_id"),
                "public_text": row.get("public_text", ""),
                "payload": payload if isinstance(payload, dict) else {},
            }
        )
    return normalized


def room_timeline(
    event_log: Sequence[Mapping[str, Any]], agent_id: str, start_room: str = START_ROOM
) -> list[str]:
    """The agent's room at each ordinal, folded from the same committed log.

    Using the agent's LIVE room instead would retroactively rewrite what it
    "saw" — a determinism-adjacent correctness bug.
    """
    timeline: list[str] = []
    room = start_room
    for event in event_log:
        timeline.append(room)
        if event.get("actor_id") != agent_id:
            continue
        if event.get("event_type") not in _MOVE_EVENT_TYPES:
            continue
        destination = event.get("target_id")
        payload = event.get("payload") or {}
        if not destination:
            destination = payload.get("to") or payload.get("destination")
        changes = payload.get("changes") or {}
        if not destination and isinstance(changes.get("room"), list):
            destination = changes["room"][-1]
        if isinstance(destination, str):
            room = destination
    return timeline


def classify_event(
    event: Mapping[str, Any], agent_id: str, agent_room_at_event: str | None
) -> str | None:
    """Return one MEMORY_PRIORITY class, or None when irrelevant to this agent.

    Classification returns the FIRST matching class in MEMORY_PRIORITY order, so
    an event where the agent is both actor and target (wild-swing self damage)
    counts exactly once, as ``damage_received``.
    """
    family = RELEVANT_EVENT_TYPES.get(event.get("event_type", ""))
    if family is None:
        return None
    payload = event.get("payload") or {}
    actor_id = event.get("actor_id")
    target_id = event.get("target_id")

    if family == "damage":
        if _took_damage(event, agent_id):
            return "damage_received"
        if actor_id == agent_id:
            return "damage_dealt"
        return None

    if family == "elimination":
        if (
            target_id == agent_id
            or actor_id == agent_id
            or payload.get("credited_to") == agent_id
            or payload.get("killer_id") == agent_id
        ):
            return "elimination_involving_me"
        room = payload.get("room")
        if room is not None and room == agent_room_at_event:
            return "observed_elimination"
        return None

    if family == "crown":
        return "crown_change"

    if family == "seal":
        if event.get("event_type") == "agent_force_moved" and actor_id != agent_id:
            return None
        return "seal_change"

    if family == "item":
        return "item_change" if actor_id == agent_id else None

    if family == "speech":
        if actor_id == agent_id:
            return None
        addressed = payload.get("addressed_ids") or []
        return "speech_to_me" if agent_id in addressed else None

    return None


def _took_damage(event: Mapping[str, Any], agent_id: str) -> bool:
    payload = event.get("payload") or {}
    if event.get("target_id") == agent_id:
        changes = payload.get("changes") or {}
        hp = changes.get("hp")
        if isinstance(hp, list) and len(hp) == 2:
            return hp[1] < hp[0]
        # A damage-family event addressed to this agent counts even when the
        # engine did not attach an hp pair (e.g. a fully mitigated burst).
        return True
    for victim in payload.get("victims") or []:
        if isinstance(victim, Mapping) and victim.get("id") == agent_id:
            return True
        if victim == agent_id:
            return True
    return False


def project_episodic_memory(
    event_log: Sequence[Mapping[str, Any]],
    agent_id: str,
    current_round: int,
    limit: int = MEMORY_LIMIT,
) -> list[dict[str, Any]]:
    """Priority-weighted recency inside a window, backfilled, emitted in order.

    A pure priority sort lets a round-2 scratch haunt an agent through round 12;
    a pure recency sort drops "the Crown moved" in favour of "someone spoke".
    Window plus backfill keeps memory current AND full whenever six relevant
    events exist at all.
    """
    log = list(event_log)
    if log and "ordinal" not in log[0]:
        log = normalize_event_log(log)
    rooms = room_timeline(log, agent_id)

    candidates: list[tuple[int, int, str, Mapping[str, Any]]] = []
    for index, event in enumerate(log):
        room_at_event = rooms[index] if index < len(rooms) else None
        memory_class = classify_event(event, agent_id, room_at_event)
        if memory_class is None:
            continue
        candidates.append(
            (event.get("ordinal", index), event.get("round_no", 0), memory_class, event)
        )

    def sort_key(item: tuple[int, int, str, Mapping[str, Any]]) -> tuple[int, int]:
        ordinal, _round_no, memory_class, _event = item
        return (MEMORY_PRIORITY.index(memory_class), -ordinal)

    floor_round = max(0, current_round - MEMORY_WINDOW_ROUNDS)
    in_window = [item for item in candidates if item[1] >= floor_round]
    out_window = [item for item in candidates if item[1] < floor_round]

    selected = sorted(in_window, key=sort_key)[:limit]
    if len(selected) < limit:
        selected += sorted(out_window, key=sort_key)[: limit - len(selected)]

    selected.sort(key=lambda item: item[0])
    return [_render(memory_class, event, agent_id) for _o, _r, memory_class, event in selected]


def _render(
    memory_class: str, event: Mapping[str, Any], agent_id: str
) -> dict[str, Any]:
    return {
        "round": event.get("round_no", 0),
        "class": memory_class,
        "about_you": agent_id in (event.get("actor_id"), event.get("target_id")),
        "actor_id": event.get("actor_id"),
        "target_id": event.get("target_id"),
        "text": truncate(event.get("public_text", "")),
    }


def truncate(text: str, maximum: int = MEMORY_TEXT_MAX) -> str:
    """Slice on CHARACTERS, never bytes, and append a single ellipsis."""
    if len(text) <= maximum:
        return text
    return text[: maximum - 1] + "…"
