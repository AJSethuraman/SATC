from __future__ import annotations

"""The v0.2 world: map, acts, seals, contraction, crown ledger, legality and the
observation builder.

Two structural commitments hold this module together:

P1. ``state["rooms"]`` is STATIC after ``new_match_state``.  Sealing never
    mutates a room dict; the single source of truth for closure is
    ``state["contraction"]["sealed"]`` and effective adjacency comes from the
    pure helper ``open_neighbors``.  Two copies of the topology therefore cannot
    desync.

P2. Every mutable list in state that feeds a hash, an RNG index or a "first in
    sorted order" rule is kept SORTED at all times, via ``floor_add`` /
    ``floor_remove`` / ``inventory_add`` / ``inventory_remove``.  The exceptions
    are deliberate append-ordered histories: ``visited``,
    ``contraction["sealed"]``, ``crown["taken_by"]``.

THE SEAM: ``is_legal(action, observation)`` is DEFINED as set membership in the
output of ``enumerate_legal_actions(observation)``.  There is exactly one rules
implementation and no second predicate that can drift from what the agent saw.
"""

from copy import deepcopy
from typing import Any, Mapping, Sequence

from . import combat, grid, items, memory, scoring
from .models import AgentAction, AgentManifest, BUILDS, RULESET_VERSION


# ---------------------------------------------------------------------------
# map
# ---------------------------------------------------------------------------

ROOM_ORDER: tuple[str, ...] = (
    "threshold",
    "ironwood_gate",
    "ossuary_gate",
    "vault",
    "egress",
)

ROOMS: dict[str, dict[str, Any]] = {
    "threshold": {
        "name": "The Threshold",
        "description": "Rain hammers the outer stair; two gates wait inland.",
        "neighbors": ["ironwood_gate", "ossuary_gate"],
        "kind": "start",
        "seal_id": None,
        "cache_id": None,
        "guardian_id": None,
    },
    "ironwood_gate": {
        "name": "The Ironwood Gate",
        "description": "Living timber grown through the arch, wet with sap.",
        "neighbors": ["threshold", "vault"],
        "kind": "gate",
        "seal_id": "ironwood_seal",
        "cache_id": "ironwood_cache",
        "guardian_id": "ironwood_guardian",
    },
    "ossuary_gate": {
        "name": "The Ossuary Gate",
        "description": "A stacked-bone arch that clicks when anyone breathes.",
        "neighbors": ["threshold", "vault"],
        "kind": "gate",
        "seal_id": "ossuary_seal",
        "cache_id": "ossuary_cache",
        "guardian_id": "ossuary_guardian",
    },
    "vault": {
        "name": "The Ember Vault",
        "description": "The Crown burns inside its Warden.",
        "neighbors": ["egress", "ironwood_gate", "ossuary_gate"],
        "kind": "vault",
        "seal_id": None,
        "cache_id": None,
        "guardian_id": "crown_warden",
    },
    "egress": {
        "name": "The Moonlit Egress",
        "description": "Open sky. Leaving here with an attuned Crown ends the match.",
        "neighbors": ["vault"],
        "kind": "egress",
        "seal_id": None,
        "cache_id": None,
        "guardian_id": None,
    },
}

SEAL_ROOMS: tuple[str, ...] = ("ironwood_gate", "ossuary_gate")
START_ROOM = "threshold"
VAULT_ROOM = "vault"
EGRESS_ROOM = "egress"
CONTRACTION_REFUGE = "vault"  # force-move destination, a constant not an adjacency

CROWN_ITEM_ID = items.CROWN_ID
CROWN_ESCAPE_ATTUNEMENT = 2
DEFAULT_MAX_ROUNDS = 12
STARTING_TOKEN_BUDGET = 18_000

# Acts. Total functions over any positive round, so a short or long match never
# raises — later contraction entries simply never fire.
ACT_I_LAST_ROUND = 4
ACT_II_LAST_ROUND = 7
ACT_NAMES: dict[int, str] = {
    1: "Act I — The Gates",
    2: "Act II — The Long Knife",
    3: "Act III — The Contraction",
}

# Ordered, absolute round numbers. One room per round; vault and egress never
# seal.
CONTRACTION_SCHEDULE: tuple[tuple[int, str], ...] = (
    (9, "threshold"),
    (10, "ironwood_gate"),
    (11, "ossuary_gate"),
)

MONSTER_TEMPLATES: dict[str, dict[str, Any]] = {
    "ironwood_guardian": {
        "id": "ironwood_guardian",
        "name": "Ironwood Guardian",
        "kind": "guardian",
        "room": "ironwood_gate",
        "tile": [2, 1],
        "reach": 1,
        "max_hp": 12,
        "hp": 12,
        "power": 3,
        "armor": 1,
        "guard": 0,
        "death_cause": None,
        "defeated_by": None,
        "collateral_taken": 0,
    },
    "ossuary_guardian": {
        "id": "ossuary_guardian",
        "name": "Ossuary Guardian",
        "kind": "guardian",
        "room": "ossuary_gate",
        "tile": [2, 1],
        "reach": 1,
        "max_hp": 12,
        "hp": 12,
        "power": 3,
        "armor": 0,
        "guard": 0,
        "death_cause": None,
        "defeated_by": None,
        "collateral_taken": 0,
    },
    "crown_warden": {
        "id": "crown_warden",
        "name": "Crown Warden",
        "kind": "warden",
        "room": "vault",
        "tile": [3, 2],
        "reach": 2,
        "max_hp": 20,
        "hp": 20,
        "power": 4,
        "armor": 2,
        "guard": 0,
        "death_cause": None,
        "defeated_by": None,
        "collateral_taken": 0,
    },
}

CACHE_CONTENTS: dict[str, str] = {
    "ironwood_gate": "veteran_blade",
    "ossuary_gate": "healing_tonic",
}

OBSERVATION_SCHEMA_VERSION = "ember-vault-obs-0.2"
LEGALITY_VERSION = "ember-vault-legality-0.2"


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------


def new_match_state(
    manifests: list[AgentManifest],
    seed: int,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
) -> dict[str, Any]:
    agents: dict[str, Any] = {}
    for seat_index, manifest in enumerate(manifests):
        stats = BUILDS[manifest.build]
        agents[manifest.id] = {
            "id": manifest.id,
            "name": manifest.name,
            "build": manifest.build,
            "room": START_ROOM,
            # Tactical position. Seat order fixes the opening formation, so the
            # same roster always starts identically.
            "tile": list(grid.spawn_tile(START_ROOM, seat_index)),
            "move_range": grid.move_range(stats["speed"]),
            "reach": grid.reach_for_build(manifest.build),
            "hp": stats["max_hp"],
            "max_hp": stats["max_hp"],
            "power": stats["power"],
            "armor": stats["armor"],
            "speed": stats["speed"],
            "search": stats["search"],
            "guard": 0,
            "inventory": [],  # ALWAYS sorted (P2)
            "status": "active",
            "score": 0,
            "score_breakdown": {},
            "tokens_remaining": STARTING_TOKEN_BUDGET,
            "memory": [],
            "visited": [START_ROOM],  # append-ordered history
            "rest_used": False,
            "monster_damage": 0,
            "agent_damage": 0,
            "kills": 0,
            "invalid_actions": 0,
            "collateral_dealt": 0,
            "collateral_taken": 0,
            scoring.ROUND_HIT_COUNTER: 0,
            "direct_eliminations": [],
            "caches_found": [],
            "crown_takes": 0,
            "eliminated_round": None,
        }
    return {
        "ruleset_version": RULESET_VERSION,
        "seed": int(seed),
        "round": 0,
        "act": 1,
        "max_rounds": int(max_rounds),
        "status": "created",
        "ended_reason": None,
        "winner_agent_id": None,
        "rooms": deepcopy(ROOMS),  # STATIC forever (P1)
        "monsters": deepcopy(MONSTER_TEMPLATES),
        "agents": agents,
        "floor_items": {room_id: [] for room_id in ROOM_ORDER},
        # TRI-STATE, not bool: "inactive" | "active" | "voided". Contraction can
        # remove a gate room before its seal was ever activated; "voided" records
        # that the seal can never be lit and scores nothing. It does NOT satisfy
        # the vault gate — only "active" does — so the vault gate becomes
        # permanently closed and survivors reach the vault solely by referee
        # relocation.
        "seals": {room_id: "inactive" for room_id in SEAL_ROOMS},
        "seal_meta": {
            room_id: {"activated_by": None, "activated_round": None}
            for room_id in SEAL_ROOMS
        },
        "caches": {
            room_id: {
                "item_id": CACHE_CONTENTS[room_id],
                "found": False,
                "found_by": None,
                "found_round": None,
            }
            for room_id in SEAL_ROOMS
        },
        "crown": {
            "status": "locked",  # locked|floor|carried|escaped
            "carrier_id": None,
            "room": None,
            "attunement_rounds": 0,
            "unlocked_round": None,
            "transfers": 0,
            "taken_by": [],
            "hold_rounds_by_agent": {},
        },
        "contraction": {
            "schedule": [
                {"round": round_no, "room": room_id}
                for round_no, room_id in CONTRACTION_SCHEDULE
            ],
            "sealed": [],
            "contracting": [],
        },
        "collateral_damage": {"total": 0, "by_source": {}, "by_victim": {}},
        "room_reaction_uses": {room_id: 0 for room_id in ROOM_ORDER},
        "recent_speech": [],
    }


# ---------------------------------------------------------------------------
# sorted-collection helpers (P2)
# ---------------------------------------------------------------------------


def floor_add(state: dict[str, Any], room: str, item_id: str) -> None:
    pile = state["floor_items"][room]
    pile.append(item_id)
    pile.sort()


def floor_remove(state: dict[str, Any], room: str, item_id: str) -> bool:
    pile = state["floor_items"][room]
    if item_id not in pile:
        return False
    pile.remove(item_id)  # exactly one occurrence; never use a set
    pile.sort()
    return True


def inventory_add(state: dict[str, Any], agent_id: str, item_id: str) -> None:
    inventory = state["agents"][agent_id]["inventory"]
    inventory.append(item_id)
    inventory.sort()


def inventory_remove(state: dict[str, Any], agent_id: str, item_id: str) -> bool:
    inventory = state["agents"][agent_id]["inventory"]
    if item_id not in inventory:
        return False
    inventory.remove(item_id)
    inventory.sort()
    return True


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------


def act_for_round(round_no: int) -> int:
    if round_no <= ACT_I_LAST_ROUND:
        return 1
    if round_no <= ACT_II_LAST_ROUND:
        return 2
    return 3


def act_name(act: int) -> str:
    return ACT_NAMES.get(act, f"Act {act}")


def sealing_room_for_round(round_no: int) -> str | None:
    for scheduled_round, room_id in CONTRACTION_SCHEDULE:
        if scheduled_round == round_no:
            return room_id
    return None


def contracting_rooms_for_round(round_no: int) -> list[str]:
    room_id = sealing_room_for_round(round_no)
    return [room_id] if room_id else []


def seal_round_for_room(room: str) -> int | None:
    for scheduled_round, room_id in CONTRACTION_SCHEDULE:
        if room_id == room:
            return scheduled_round
    return None


def is_sealed(state: Mapping[str, Any], room: str) -> bool:
    return room in state["contraction"]["sealed"]


def open_neighbors(state: Mapping[str, Any], room: str) -> list[str]:
    if is_sealed(state, room):
        return []
    return sorted(
        neighbor
        for neighbor in state["rooms"][room]["neighbors"]
        if not is_sealed(state, neighbor)
    )


def vault_open(state: Mapping[str, Any]) -> bool:
    """THE MAP RULE, literally: BOTH seals must be ACTIVE before any agent may
    move into the vault.

    ``voided`` does NOT satisfy the gate. A voided seal means contraction ate a
    gate room before anyone lit it, which makes the gate permanently
    unsatisfiable — see ``gate_permanently_closed``. That is a consequence of
    letting the seals go unlit, not a free pass through them: it used to be
    possible to skip the entire seal economy (+5 x2, the stated Act I/II
    objective) by camping in threshold until the round-9 contraction swept you
    into the vault for nothing.

    Referee RELOCATION is a separate concern and deliberately not routed through
    this predicate: contraction still force-moves survivors into the vault, and
    those events are flagged ``gate_bypassed``.
    """
    return all(status == "active" for status in state["seals"].values())


def gate_permanently_closed(state: Mapping[str, Any]) -> bool:
    """True once some seal can never be lit — its room sealed while inactive.

    Disclosed in the observation so an agent is never left guessing why the
    vault will not open; it is NOT a substitute for ``vault_open``.
    """
    return any(status == "voided" for status in state["seals"].values())


def pvp_allowed(state: Mapping[str, Any]) -> bool:
    return state.get("act", act_for_round(max(1, state.get("round", 1)))) >= 2


def crown_carrier(state: Mapping[str, Any]) -> str | None:
    crown = state["crown"]
    return crown["carrier_id"] if crown["status"] == "carried" else None


def rounds_remaining(state: Mapping[str, Any]) -> int:
    """INCLUSIVE of the current round: 12 at round 1, 1 at round 12.

    The convention is republished in the observation so a model never has to
    guess it.
    """
    round_no = state.get("round", 0)
    max_rounds = state["max_rounds"]
    if round_no <= 0:
        return max_rounds
    return max(0, max_rounds - round_no + 1)


def room_has_living_monster(state: Mapping[str, Any], room: str) -> bool:
    return any(
        monster["room"] == room and monster["hp"] > 0
        for monster in state["monsters"].values()
    )


def living_monsters_in(state: Mapping[str, Any], room: str) -> list[dict[str, Any]]:
    return [
        state["monsters"][monster_id]
        for monster_id in sorted(state["monsters"])
        if state["monsters"][monster_id]["room"] == room
        and state["monsters"][monster_id]["hp"] > 0
    ]


def living_bodies_in(state: Mapping[str, Any], room: str) -> list[dict[str, Any]]:
    """Agents AND monsters in one stable-sorted namespace (bystander pool)."""
    bodies = [
        state["agents"][agent_id]
        for agent_id in sorted(state["agents"])
        if state["agents"][agent_id]["room"] == room
        and state["agents"][agent_id]["status"] == "active"
        and state["agents"][agent_id]["hp"] > 0
    ]
    bodies.extend(living_monsters_in(state, room))
    return sorted(bodies, key=lambda body: body["id"])


def escape_gate_ok(state: Mapping[str, Any], agent_id: str) -> bool:
    agent = state["agents"][agent_id]
    crown = state["crown"]
    return (
        agent["status"] == "active"
        and agent["room"] == VAULT_ROOM
        and crown["status"] == "carried"
        and crown["carrier_id"] == agent_id
        and CROWN_ITEM_ID in agent["inventory"]
        and crown["attunement_rounds"] >= CROWN_ESCAPE_ATTUNEMENT
        and not is_sealed(state, EGRESS_ROOM)
    )


def move_allowed(state: Mapping[str, Any], agent_id: str, destination: str) -> bool:
    agent = state["agents"][agent_id]
    if destination not in open_neighbors(state, agent["room"]):
        return False
    if destination == VAULT_ROOM and not vault_open(state):
        return False
    if destination == EGRESS_ROOM and not escape_gate_ok(state, agent_id):
        return False
    return True


def legal_moves(state: Mapping[str, Any], agent_id: str) -> list[str]:
    agent = state["agents"][agent_id]
    return [
        destination
        for destination in open_neighbors(state, agent["room"])
        if move_allowed(state, agent_id, destination)
    ]


def seal_activation_allowed(state: Mapping[str, Any], agent_id: str) -> bool:
    agent = state["agents"][agent_id]
    room = agent["room"]
    return (
        agent["status"] == "active"
        and room in SEAL_ROOMS
        and state["seals"][room] == "inactive"
        and not room_has_living_monster(state, room)
    )


def search_allowed(state: Mapping[str, Any], agent_id: str) -> bool:
    agent = state["agents"][agent_id]
    room = agent["room"]
    cache = state["caches"].get(room)
    return (
        agent["status"] == "active"
        and cache is not None
        and not cache["found"]
        and not room_has_living_monster(state, room)
    )


# ---------------------------------------------------------------------------
# crown ledger — every mutation funnels through these four helpers
# ---------------------------------------------------------------------------
#
# The crown item's authoritative LOCATION is floor_items / inventory;
# ``state["crown"]`` is a ledger the same code paths keep in lockstep. These
# helpers mutate state and RETURN a ``changes`` fragment; the engine emits the
# event. Routing every path through them is what makes it impossible to forget
# the attunement reset on a new code path.


def crown_unlock(state: dict[str, Any], round_no: int) -> dict[str, Any]:
    crown = state["crown"]
    before = crown["status"]
    crown["status"] = "floor"
    crown["room"] = VAULT_ROOM
    crown["unlocked_round"] = round_no
    floor_add(state, VAULT_ROOM, CROWN_ITEM_ID)
    return {
        "crown.status": [before, "floor"],
        "floor_items.vault.added": CROWN_ITEM_ID,
    }


def crown_to_carrier(state: dict[str, Any], agent_id: str) -> dict[str, Any]:
    crown = state["crown"]
    before_status = crown["status"]
    before_attunement = crown["attunement_rounds"]
    before_carrier = crown["carrier_id"]
    crown["status"] = "carried"
    crown["carrier_id"] = agent_id
    crown["room"] = None
    crown["attunement_rounds"] = 0  # every take is a transfer
    crown["transfers"] += 1
    crown["taken_by"].append(agent_id)
    state["agents"][agent_id]["crown_takes"] += 1
    return {
        "crown.status": [before_status, "carried"],
        "crown.carrier_id": [before_carrier, agent_id],
        "crown.attunement_rounds": [before_attunement, 0],
    }


def crown_to_floor(state: dict[str, Any], room: str) -> dict[str, Any]:
    """Attunement is zeroed at DROP time, not at the next take: the floor crown
    is published to every agent and must never advertise a stale attunement."""
    crown = state["crown"]
    before_status = crown["status"]
    before_attunement = crown["attunement_rounds"]
    before_carrier = crown["carrier_id"]
    crown["status"] = "floor"
    crown["carrier_id"] = None
    crown["room"] = room
    crown["attunement_rounds"] = 0
    crown["transfers"] += 1
    return {
        "crown.status": [before_status, "floor"],
        "crown.carrier_id": [before_carrier, None],
        "crown.attunement_rounds": [before_attunement, 0],
    }


def crown_extract(state: dict[str, Any], agent_id: str) -> dict[str, Any]:
    crown = state["crown"]
    before_status = crown["status"]
    crown["status"] = "escaped"
    crown["room"] = None
    crown["carrier_id"] = agent_id
    return {
        "crown.status": [before_status, "escaped"],
        "winner_agent_id": [state.get("winner_agent_id"), agent_id],
    }


def crown_attune(state: dict[str, Any]) -> dict[str, Any] | None:
    """END-of-round tick. Returns None when no live carrier holds the Crown."""
    crown = state["crown"]
    carrier_id = crown_carrier(state)
    if carrier_id is None:
        return None
    if state["agents"][carrier_id]["status"] != "active":
        return None
    before = crown["attunement_rounds"]
    crown["attunement_rounds"] = before + 1
    held = crown["hold_rounds_by_agent"]
    held[carrier_id] = held.get(carrier_id, 0) + 1
    return {
        "agent_id": carrier_id,
        "changes": {"crown.attunement_rounds": [before, crown["attunement_rounds"]]},
    }


def crown_ledger_ok(state: Mapping[str, Any]) -> bool:
    """The four-way invariant, assertable at every snapshot."""
    crown = state["crown"]
    on_floor = [
        room
        for room in state["floor_items"]
        if CROWN_ITEM_ID in state["floor_items"][room]
    ]
    carriers = [
        agent_id
        for agent_id in state["agents"]
        if CROWN_ITEM_ID in state["agents"][agent_id]["inventory"]
    ]
    copies = sum(
        state["floor_items"][room].count(CROWN_ITEM_ID) for room in state["floor_items"]
    ) + sum(
        state["agents"][agent_id]["inventory"].count(CROWN_ITEM_ID)
        for agent_id in state["agents"]
    )
    status = crown["status"]
    if status == "locked":
        return copies == 0
    if status == "floor":
        return (
            copies == 1
            and on_floor == [crown["room"]]
            and not carriers
            and crown["carrier_id"] is None
        )
    if status == "carried":
        return (
            copies == 1
            and carriers == [crown["carrier_id"]]
            and not on_floor
            and crown["room"] is None
        )
    if status == "escaped":
        return crown["carrier_id"] is not None and crown["room"] is None
    return False


# ---------------------------------------------------------------------------
# legality — one enumeration, and membership in it is the validator
# ---------------------------------------------------------------------------

ACTION_ORDER: tuple[str, ...] = (
    "move",
    "step",
    "attack",
    "take",
    "use",
    "interact",
    "search",
    "rest",
    "guard",
)

# Which slots are SIGNIFICANT per verb. Everything else is normalized away so a
# model that sends a stray field ({"action":"guard","target":"vex"}) is not
# falsely illegal.
SIGNIFICANT_SLOTS: Mapping[str, tuple[str, ...]] = {
    "guard": (),
    "rest": (),
    "search": (),
    "move": ("destination",),
    "attack": ("target",),
    "take": ("item",),
    "use": ("item",),
    "interact": ("target",),
    "step": ("tile",),
}


def _norm_id(value: Any) -> str | None:
    """All engine ids are lowercase [a-z0-9_-], so casefolding is loss-free and
    absorbs model capitalization."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value.casefold() if value else None


def _norm_tile(value: Any) -> str | None:
    t = grid.as_tile(value)
    return grid.tile_key(t) if t else None


def normalize_key(
    action: str,
    target: Any = None,
    destination: Any = None,
    item: Any = None,
    tile: Any = None,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    verb = (action or "").strip().lower()
    significant = SIGNIFICANT_SLOTS.get(verb)
    if significant is None:
        # Unknown verb: keep it raw. It can never match an enumerated entry.
        return (
            verb, _norm_id(target), _norm_id(destination), _norm_id(item),
            _norm_tile(tile),
        )
    return (
        verb,
        _norm_id(target) if "target" in significant else None,
        _norm_id(destination) if "destination" in significant else None,
        _norm_id(item) if "item" in significant else None,
        _norm_tile(tile) if "tile" in significant else None,
    )


def action_key(
    action: Any,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Accepts an AgentAction or any mapping with the five slots."""
    if isinstance(action, AgentAction):
        return normalize_key(
            action.action, action.target, action.destination, action.item, action.tile
        )
    if isinstance(action, Mapping):
        return normalize_key(
            action.get("action", ""),
            action.get("target"),
            action.get("destination"),
            action.get("item"),
            action.get("tile"),
        )
    raise TypeError(f"cannot key {type(action).__name__}")


def _entry(
    action: str,
    label: str,
    *,
    target: str | None = None,
    destination: str | None = None,
    item: str | None = None,
    tile: Any = None,
) -> dict[str, Any]:
    return {
        "action": action,
        "target": target,
        "destination": destination,
        "item": item,
        "tile": list(tile) if tile else None,
        "label": label,  # COSMETIC ONLY — never part of the key
    }


def enumerate_legal_actions(observation: Mapping[str, Any]) -> list[dict[str, Any]]:
    """AUTHORITATIVE. Reads ONLY the observation, never live state, so the list
    an agent saw and the list used to judge it are the same object graph.

    Never returns an empty list: ``guard`` is unconditional.
    """
    public = observation["public_state"]
    room = observation["room"]
    me = observation["you"]
    crown = public["crown"]
    monsters = observation.get("visible_monsters", [])
    entries: list[dict[str, Any]] = [_entry("guard", "guard (brace: +2 Armor)")]

    # Tactical geometry, all read from the observation so the list the agent saw
    # is the list it is judged against.
    my_tile = grid.as_tile(me.get("tile"))
    my_move = int(me.get("move_range") or 1)
    my_reach = int(me.get("reach") or 1)
    grid_info = room.get("grid") or {}
    doors = grid_info.get("doors") or {}

    def _within(other_tile: Any, limit: int) -> bool:
        """True when no tile is known on either side -- a roomful of bodies with
        no geometry must stay playable rather than silently losing every action."""
        a, b = my_tile, grid.as_tile(other_tile)
        if not a or not b:
            return True
        return grid.distance(a, b) <= limit

    # RULING: room transit is legal from anywhere in the room and costs the whole
    # action, arriving at the destination's doorway. Gating transit on reaching
    # the door first was tried and abandoned -- a Vanguard (move range 1) needed
    # three turns to cross a gate room to the vault door, which is crippling
    # inside twelve rounds. Range governs WITHIN-room movement, where the
    # tactical decisions actually live.
    for destination in room.get("neighbors", []):
        if destination == VAULT_ROOM and not public.get("vault_open"):
            continue
        if destination == EGRESS_ROOM:
            if crown.get("carrier_id") != me["id"]:
                continue
            if crown.get("attunement_rounds", 0) < crown.get(
                "attunement_required", CROWN_ESCAPE_ATTUNEMENT
            ):
                continue
            entries.append(
                _entry(
                    "move",
                    "move to egress — ESCAPE AND WIN",
                    destination=destination,
                )
            )
            continue
        entries.append(
            _entry(
                "move",
                f"move to {destination} ({_room_name(observation, destination)})",
                destination=destination,
            )
        )

    def _range_note(other_tile: Any) -> str:
        a, b = my_tile, grid.as_tile(other_tile)
        if not a or not b:
            return ""
        return f", range {grid.distance(a, b)}/{my_reach}"

    for monster in monsters:
        if not _within(monster.get("tile"), my_reach):
            continue
        entries.append(
            _entry(
                "attack",
                f"attack {monster['id']} ({monster['name']}, "
                f"{monster['hp']}/{monster['max_hp']} HP"
                f"{_range_note(monster.get('tile'))})",
                target=monster["id"],
            )
        )
    if public.get("agent_attacks_allowed"):
        for other in observation.get("visible_agents", []):
            if other.get("status") != "active":
                continue
            if not _within(other.get("tile"), my_reach):
                continue
            entries.append(
                _entry(
                    "attack",
                    f"attack {other['id']} ({other['name']}, "
                    f"{other['hp']}/{other['max_hp']} HP)",
                    target=other["id"],
                )
            )

    # step: every free tile inside move range. Enumerated exhaustively, which is
    # affordable because range is small and the grids are tiny.
    for tile in (grid_info.get("reachable") or []):
        t = grid.as_tile(tile)
        if not t:
            continue
        entries.append(
            _entry(
                "step",
                f"step to [{t[0]},{t[1]}] "
                f"(distance {grid.distance(my_tile, t) if my_tile else '?'}/{my_move})",
                tile=t,
            )
        )

    # DEDUPE: keys form a set, so two Healing Tonics must not enumerate twice.
    for item_id in sorted({view["id"] for view in room.get("floor_items", [])}):
        entries.append(
            _entry(
                "take",
                f"take {item_id} ({items.item_name(item_id)})",
                item=item_id,
            )
        )
    for item_id in items.usable_item_ids([view["id"] for view in me.get("inventory", [])]):
        entries.append(
            _entry("use", f"use {item_id} ({items.item_name(item_id)})", item=item_id)
        )

    seal = room.get("seal")
    if seal and not seal["active"] and not monsters:
        entries.append(
            _entry(
                "interact",
                f"interact {seal['id']} (activate the seal, +5)",
                target=seal["id"],
            )
        )
    cache = room.get("cache")
    if cache and not cache["found"] and not monsters:
        entries.append(_entry("search", "search this room's cache"))
    if not monsters and me["hp"] < me["max_hp"] and not me.get("rest_used"):
        entries.append(_entry("rest", "rest (+2 HP, once per match)"))

    entries.sort(key=_entry_sort_key)
    return entries


def _entry_sort_key(entry: Mapping[str, Any]) -> tuple[int, str, str, str, str]:
    tile = entry.get("tile")
    return (
        ACTION_ORDER.index(entry["action"]),
        entry["target"] or "",
        entry["destination"] or "",
        entry["item"] or "",
        grid.tile_key(tile) if tile else "",
    )


def _room_name(observation: Mapping[str, Any], room_id: str) -> str:
    for room in observation.get("map", {}).get("rooms", []):
        if room["id"] == room_id:
            return room["name"]
    return room_id


def legal_key_set(
    observation: Mapping[str, Any],
) -> frozenset[tuple[str, str | None, str | None, str | None]]:
    """Prefers the PUBLISHED list already attached to the frozen observation, so
    the agent is judged against the exact bytes it read. Only recomputes when it
    is absent (tests and tools)."""
    listed = observation.get("legal_actions")
    if listed is None:
        listed = enumerate_legal_actions(observation)
    return frozenset(action_key(entry) for entry in listed)


def is_legal(action: Any, observation: Mapping[str, Any]) -> bool:
    """THE seam. A schema-valid action that is not in ``legal_actions`` is
    illegal, becomes guard, and costs -2."""
    return action_key(action) in legal_key_set(observation)


# ---------------------------------------------------------------------------
# observation — a pure function of frozen state. No I/O, no RNG, no clock.
# ---------------------------------------------------------------------------


def visible_observation(
    state: Mapping[str, Any],
    agent_id: str,
    objective: str,
    event_log: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build the full v0.2 observation for one agent.

    Purity contract: no I/O, no store handle, no HashRNG, no clock, and no
    mutation of ``state`` or ``event_log``. Called with a deepcopy of state and a
    frozen event list; two calls with equal inputs return equal output and
    ``state_hash(state)`` is unchanged across the call.

    Every block except ``legal_actions`` is built first; the enumerator then runs
    over the partial observation, which is what makes the published list a
    function of exactly what the agent can see.
    """
    agent = state["agents"][agent_id]
    observation: dict[str, Any] = {
        "ruleset_version": state["ruleset_version"],
        "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
        "public_state": _build_public_state(state),
        "map": _build_map(state, agent),
        "you": _build_self(state, agent),
        "room": _build_room(state, agent),
        "visible_agents": _build_visible_agents(state, agent),
        "visible_monsters": _build_visible_monsters(state, agent),
        "secret_objective": scoring.objective_progress(state, agent_id, objective),
        "episodic_memory": memory.project_episodic_memory(
            event_log, agent_id, state.get("round", 0)
        ),
        "episodic_memory_policy": memory.memory_policy(),
        "scratch_memory": list(agent["memory"]),
        "recent_speech": _build_recent_speech(state, agent),
        "score_breakdown": scoring.score_breakdown_view(state, agent_id),
    }
    observation["legal_actions"] = enumerate_legal_actions(observation)
    return observation


# Back-compat alias for callers that prefer design 3's name.
build_observation = visible_observation


def _build_public_state(state: Mapping[str, Any]) -> dict[str, Any]:
    crown = state["crown"]
    act = state.get("act", act_for_round(max(1, state.get("round", 1))))
    return {
        "round": state["round"],
        "max_rounds": state["max_rounds"],
        "rounds_remaining": rounds_remaining(state),
        "rounds_remaining_convention": "inclusive_of_current_round",
        "act": act,
        "act_name": act_name(act),
        "agent_attacks_allowed": act >= 2,
        "seals": dict(state["seals"]),
        "vault_open": vault_open(state),
        "vault_gate_permanently_closed": gate_permanently_closed(state),
        "warden_alive": state["monsters"]["crown_warden"]["hp"] > 0,
        "crown": {
            "status": crown["status"],
            "carrier_id": crown["carrier_id"],
            "room": crown["room"],
            "attunement_rounds": crown["attunement_rounds"],
            "attunement_required": CROWN_ESCAPE_ATTUNEMENT,
        },
    }


def _build_map(state: Mapping[str, Any], agent: Mapping[str, Any]) -> dict[str, Any]:
    contracting = list(state["contraction"]["contracting"])
    visited = set(agent["visited"])
    return {
        "current_room": agent["room"],
        "rooms": [
            {
                "id": room_id,
                "name": state["rooms"][room_id]["name"],
                # Sealed rooms are STRIPPED from every neighbors array but stay
                # listed with sealed:true, so an exit that vanished has a visible
                # reason.
                "neighbors": open_neighbors(state, room_id),
                "sealed": is_sealed(state, room_id),
                "contracting": room_id in contracting,
                "seals_at_end_of_round": seal_round_for_room(room_id),
                "has_seal": room_id in SEAL_ROOMS,
                "seal_status": state["seals"].get(room_id),
                "guardian_id": state["rooms"][room_id]["guardian_id"],
                "visited": room_id in visited,
            }
            for room_id in ROOM_ORDER
        ],
        "sealed": list(state["contraction"]["sealed"]),
        "contracting": contracting,
        "visited": list(agent["visited"]),
        "schedule": [dict(entry) for entry in state["contraction"]["schedule"]],
    }


def _build_self(state: Mapping[str, Any], agent: Mapping[str, Any]) -> dict[str, Any]:
    inventory = list(agent["inventory"])
    power_effective, _ = combat.effective_power(agent["power"], inventory)
    armor_passive = items.passive_armor_bonus(inventory)
    active_effects = items.passive_disclosures(inventory)
    if agent["guard"]:
        active_effects.append(
            {
                "source_kind": "stance",
                "source_id": "guard",
                "source_name": "Guard stance",
                "stat": "armor",
                "delta": agent["guard"],
                "text": (
                    f"Guarding adds +{agent['guard']} Armor until your next turn "
                    "(it also raises the DC to hit you)."
                ),
            }
        )
    active_effects.sort(
        key=lambda entry: (entry["stat"], entry["source_kind"], entry["source_id"])
    )
    return {
        "id": agent["id"],
        "name": agent["name"],
        "build": agent["build"],
        "room": agent["room"],
        "status": agent["status"],
        # Tactical position and the two ranges derived from the build.
        "tile": list(agent.get("tile") or []),
        "move_range": agent.get("move_range", 1),
        "reach": agent.get("reach", 1),
        "hp": agent["hp"],
        "max_hp": agent["max_hp"],
        "power_base": agent["power"],
        "power_effective": power_effective,
        "armor_base": agent["armor"],
        "armor_effective": agent["armor"] + armor_passive + agent["guard"],
        "guard": agent["guard"],
        "rest_used": agent["rest_used"],
        "inventory": items.describe_items(inventory),
        "active_effects": active_effects,
        "carrying_crown": CROWN_ITEM_ID in inventory,
        "collateral_dealt": agent["collateral_dealt"],
        "collateral_taken": agent["collateral_taken"],
        "tokens_remaining": agent["tokens_remaining"],
        "invalid_actions": agent["invalid_actions"],
        "score": agent["score"],
    }


def _build_room(state: Mapping[str, Any], agent: Mapping[str, Any]) -> dict[str, Any]:
    room_id = agent["room"]
    room = state["rooms"][room_id]
    seal = None
    if room_id in SEAL_ROOMS:
        guardian_id = room["guardian_id"]
        guardian = state["monsters"].get(guardian_id)
        seal = {
            "id": room["seal_id"],
            "status": state["seals"][room_id],
            "active": state["seals"][room_id] in {"active", "voided"},
            "blocked_by_monster": (
                guardian_id if guardian and guardian["hp"] > 0 else None
            ),
        }
    cache_state = state["caches"].get(room_id)
    cache = None
    if cache_state is not None:
        cache = {
            "found": cache_state["found"],
            "found_by": cache_state["found_by"],
            "contains": (
                items.describe_item(cache_state["item_id"])
                if cache_state["found"]
                else None
            ),
        }
    return {
        "id": room_id,
        "name": room["name"],
        "description": room["description"],
        "neighbors": open_neighbors(state, room_id),
        "contracting": room_id in state["contraction"]["contracting"],
        "seals_at_end_of_round": seal_round_for_room(room_id),
        "seal": seal,
        "cache": cache,
        "floor_items": items.describe_items(list(state["floor_items"][room_id])),
        "grid": _build_grid(state, agent),
    }


def _build_grid(state: Mapping[str, Any], agent: Mapping[str, Any]) -> dict[str, Any]:
    """The room's tactical geometry, from this agent's seat.

    ``reachable`` is precomputed here rather than in the enumerator so the tile
    list the agent reads and the tile list its step is judged against are
    literally the same values.
    """
    room_id = agent["room"]
    g = grid.grid_for(room_id)
    here = grid.as_tile(agent.get("tile"))
    rng = int(agent.get("move_range") or 1)
    reachable = (
        grid.reachable_tiles(state, room_id, here, rng, mover_id=agent["id"])
        if here
        else []
    )
    return {
        "width": g["w"],
        "height": g["h"],
        "doors": {n: list(t) for n, t in g["doors"].items()},
        "features": {k: list(v) for k, v in g["features"].items()},
        "occupied": [list(t) for t in sorted(grid.occupied_tiles(state, room_id))],
        "reachable": [list(t) for t in reachable],
        "version": grid.GRID_VERSION,
    }


def _build_visible_agents(
    state: Mapping[str, Any], agent: Mapping[str, Any]
) -> list[dict[str, Any]]:
    views = []
    for other_id in sorted(state["agents"]):
        other = state["agents"][other_id]
        if other_id == agent["id"] or other["room"] != agent["room"]:
            continue
        inventory = list(other["inventory"])
        views.append(
            {
                "id": other["id"],
                "name": other["name"],
                "build": other["build"],
                "status": other["status"],
                "tile": list(other.get("tile") or []),
                "reach": other.get("reach", 1),
                "hp": other["hp"],
                "max_hp": other["max_hp"],
                "armor_effective": (
                    other["armor"]
                    + items.passive_armor_bonus(inventory)
                    + other["guard"]
                ),
                "carrying_crown": CROWN_ITEM_ID in inventory,
                "inventory": items.describe_items(inventory),
                # Totals only. Never another agent's score_breakdown, objective,
                # scratch memory, or token balance.
                "score_total": other["score"],
            }
        )
    return views


def _build_visible_monsters(
    state: Mapping[str, Any], agent: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "id": monster["id"],
            "name": monster["name"],
            "kind": monster["kind"],
            "hp": monster["hp"],
            "max_hp": monster["max_hp"],
            "armor_effective": monster["armor"] + monster["guard"],
            "guard": monster["guard"],
            "tile": list(monster.get("tile") or []),
            "reach": monster.get("reach", 1),
        }
        for monster in living_monsters_in(state, agent["room"])
    ]


def _build_recent_speech(
    state: Mapping[str, Any], agent: Mapping[str, Any]
) -> list[dict[str, Any]]:
    round_no = state.get("round", 0)
    entries = [
        speech
        for speech in state["recent_speech"]
        if speech.get("round", 0) >= round_no - 2
        and speech.get("room", agent["room"]) == agent["room"]
    ][-8:]
    return [
        {
            "round": speech.get("round", 0),
            "agent_id": speech.get("agent_id"),
            "name": speech.get("name"),
            "text": speech.get("text", ""),
            "directed_at_you": agent["id"] in (speech.get("addressed_ids") or []),
        }
        for speech in entries
    ]
