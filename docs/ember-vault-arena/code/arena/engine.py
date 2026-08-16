from __future__ import annotations

"""The deterministic referee.

Round order (v0.2), stated once so tests, scoring and the map spec agree:

  P0  ROUND OPEN     round number, guard + per-round cap resets, ACT transition,
                     contraction warning, start snapshot, ``round_started``.
  P1  DECISIONS      observations frozen here (deepcopy + one committed event-log
                     cutoff shared by every agent).
  P2  INITIATIVE     d20 + speed.
  P3  ACTIONS        initiative order; a legal escape breaks the loop.
  P4  MONSTERS       deterministic: lowest-HP legal target, seeded tie-break.
                     No model call — the v0.1 ``choose_npc_actions`` LLM hop is
                     gone.
  P5  UPKEEP         attunement tick, contraction seal, Act II survival.
                     SKIPPED ENTIRELY when someone extracted this round.
  P6  NARRATION      model call, end snapshot, ``end_turn``.

Models never mutate state.  Typed code alone decides legality, dice, damage,
score, elimination and victory, and replay needs no model call.
"""

import hashlib
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from . import combat, grid, items, rules, scoring
from .models import (
    AgentAction,
    AgentManifest,
    ProviderResult,
    RULESET_VERSION,
    ValidationError,
)
from .providers import (
    DecisionProvider,
    MockDecisionProvider,
    compile_narration_prompt,
    compile_prompt,
)
from .rng import HashRNG
from .rules import (
    CROWN_ITEM_ID,
    EGRESS_ROOM,
    SEAL_ROOMS,
    VAULT_ROOM,
    new_match_state,
    visible_observation,
)
from .storage import ArenaStore, canonical_json


def _legal_actions_hash(observation: dict[str, Any]) -> str:
    """Fingerprint of the published legal_actions at freeze time.

    Recorded so an auditor can prove after the fact that the list an agent was
    judged against is the list it was shown, without trusting the copy that
    crossed the provider seam.
    """
    return hashlib.sha256(
        canonical_json(observation.get("legal_actions", [])).encode("utf-8")
    ).hexdigest()


@dataclass
class FrozenDecision:
    """What the referee kept for itself when the round was frozen.

    ``observation`` is the referee's OWN copy — the provider never sees this
    object, only a deepcopy — and ``legal_keys`` is the legality oracle captured
    at freeze time, before any untrusted code ran. Judging against the captured
    set (not against a dict the provider could have edited) is what keeps
    "typed code alone decides legality" true.
    """

    action: AgentAction
    observation: dict[str, Any]
    legal_keys: frozenset[tuple[str | None, ...]]
    legal_actions_hash: str
    validity: str
    fallback_reason: str | None


class ArenaEngine:
    def __init__(
        self,
        store: ArenaStore,
        provider: DecisionProvider,
        *,
        max_rounds: int = rules.DEFAULT_MAX_ROUNDS,
        parallel_agents: bool = True,
    ):
        self.store = store
        self.provider = provider
        self.max_rounds = max_rounds
        self.parallel_agents = parallel_agents
        self.autopilot = MockDecisionProvider()
        self.match_id = ""
        self.state: dict[str, Any] = {}
        self.manifests: dict[str, AgentManifest] = {}
        self.rng = HashRNG(0)
        self.round_lines: list[str] = []

    # ------------------------------------------------------------------
    # match loop
    # ------------------------------------------------------------------

    def run(
        self,
        manifests: list[AgentManifest],
        seed: int = 20260724,
        match_id: str | None = None,
    ) -> str:
        if not 4 <= len(manifests) <= 8:
            raise ValueError("Ember Vault requires four to eight agents")
        if len({manifest.id for manifest in manifests}) != len(manifests):
            raise ValueError("agent IDs must be unique")
        self.match_id = match_id or f"ember-{seed}-{uuid.uuid4().hex[:8]}"
        self.manifests = {manifest.id: manifest for manifest in manifests}
        self.state = new_match_state(manifests, seed, self.max_rounds)
        self.state["status"] = "running"
        self.rng = HashRNG(seed)

        for manifest in manifests:
            self.store.register_agent(manifest)
        self.store.create_match(
            self.match_id,
            seed,
            RULESET_VERSION,
            self.max_rounds,
            manifests,
        )
        self._event(
            0,
            "setup",
            "match_started",
            None,
            None,
            "Rivals enter the Ember Vault. Only one Crown can leave.",
            {
                "agent_ids": [manifest.id for manifest in manifests],
                "ruleset_version": RULESET_VERSION,
                "max_rounds": self.max_rounds,
            },
        )
        self.store.save_snapshot(self.match_id, 0, "start", self.state)

        for round_no in range(1, self.max_rounds + 1):
            if self._is_terminal():
                break
            self._run_round(round_no)

        self._finalize()
        return self.match_id

    def _run_round(self, round_no: int) -> None:
        # -- P0 ROUND OPEN --------------------------------------------------
        self.state["round"] = round_no
        self.round_lines = []
        round_resets: dict[str, Any] = {}
        for agent_id in sorted(self.state["agents"]):
            agent = self.state["agents"][agent_id]
            if agent["guard"]:
                round_resets[f"agents.{agent_id}.guard"] = [agent["guard"], 0]
            agent["guard"] = 0
            cap_reset = scoring.reset_round_counters(agent)
            for key, pair in cap_reset.items():
                round_resets[f"agents.{agent_id}.{key}"] = pair
        for monster_id in sorted(self.state["monsters"]):
            monster = self.state["monsters"][monster_id]
            if monster["guard"]:
                round_resets[f"monsters.{monster_id}.guard"] = [monster["guard"], 0]
            monster["guard"] = 0

        self._apply_act_transition(round_no)
        self._flag_contracting_rooms(round_no)

        start_hash = self.store.save_snapshot(
            self.match_id, round_no, "start", self.state
        )
        self.store.start_turn(self.match_id, round_no, start_hash)
        self._event(
            round_no,
            "referee",
            "round_started",
            None,
            None,
            f"Round {round_no} begins.",
            {
                "round": round_no,
                "act": self.state["act"],
                "changes": round_resets,
            },
            include_in_narration=False,
        )

        # -- P1 DECISIONS ---------------------------------------------------
        decisions = self._collect_decisions(round_no)

        # -- P2 INITIATIVE --------------------------------------------------
        initiatives: list[tuple[int, str]] = []
        for agent_id in sorted(decisions):
            if self.state["agents"][agent_id]["status"] != "active":
                continue
            roll = self._roll(20, f"initiative:r{round_no}:{agent_id}", agent_id)
            total = roll + self.state["agents"][agent_id]["speed"]
            initiatives.append((total, agent_id))
        initiatives.sort(key=lambda pair: (-pair[0], pair[1]))
        self._event(
            round_no,
            "referee",
            "initiative_order",
            None,
            None,
            "Initiative locks in: "
            + ", ".join(
                f"{self.state['agents'][agent_id]['name']} ({initiative})"
                for initiative, agent_id in initiatives
            ),
            {"order": [{"agent_id": aid, "total": total} for total, aid in initiatives]},
        )

        # -- P3 ACTION RESOLUTION -------------------------------------------
        for _, agent_id in initiatives:
            if self.state["agents"][agent_id]["status"] != "active":
                self._event(
                    round_no,
                    "agent",
                    "action_skipped",
                    agent_id,
                    None,
                    f"{self.state['agents'][agent_id]['name']} cannot act.",
                    {"reason": "not_active"},
                )
                continue
            decision = decisions[agent_id]
            if not self._legal_in_frozen_decision(decision):
                self._invalid_action(
                    agent_id,
                    decision.action,
                    "action was not in the frozen start-of-round legal_actions",
                )
                continue
            self._resolve_action(agent_id, decision.action)
            if self.state.get("winner_agent_id"):
                break

        # -- P4 MONSTER PHASE (deterministic, no model call) -----------------
        if not self.state.get("winner_agent_id"):
            self._monster_phase(round_no)

        # -- P5 END-OF-ROUND UPKEEP -----------------------------------------
        # A legal escape ends the match IMMEDIATELY: no attunement tick, no
        # contraction seal, no Act II bonus in the round someone extracted.
        if not self.state.get("winner_agent_id"):
            self._end_round_upkeep(round_no)

        # -- P6 NARRATION ----------------------------------------------------
        narration = self._narrate(round_no)
        end_hash = self.store.save_snapshot(self.match_id, round_no, "end", self.state)
        self.store.end_turn(self.match_id, round_no, end_hash, narration)
        self._event(
            round_no,
            "narration",
            "round_narration",
            None,
            None,
            narration,
            {"source_event_count": len(self.round_lines)},
        )

    # ------------------------------------------------------------------
    # P0 helpers
    # ------------------------------------------------------------------

    def _apply_act_transition(self, round_no: int) -> None:
        new_act = rules.act_for_round(round_no)
        old_act = self.state["act"]
        if new_act == old_act and round_no != 1:
            return
        self.state["act"] = new_act
        self._event(
            round_no,
            "referee",
            "act_started",
            None,
            None,
            f"{rules.act_name(new_act)} opens.",
            {
                "act": new_act,
                "name": rules.act_name(new_act),
                "round": round_no,
                "pvp_allowed": new_act >= 2,
                "changes": {"act": [old_act, new_act]},
            },
        )

    def _flag_contracting_rooms(self, round_no: int) -> None:
        """A room is flagged for the FULL round whose END seals it, so the
        warning is inside every frozen observation of that round."""
        before = list(self.state["contraction"]["contracting"])
        flagged = rules.contracting_rooms_for_round(round_no)
        self.state["contraction"]["contracting"] = sorted(flagged)
        for room_id in sorted(set(flagged) - set(before)):
            self._event(
                round_no,
                "referee",
                "room_contracting",
                None,
                room_id,
                f"{self.state['rooms'][room_id]['name']} will seal at the end of "
                f"round {round_no}.",
                {
                    "room": room_id,
                    "seals_at_end_of_round": round_no,
                    "occupants": self._active_agents_in(room_id),
                    "changes": {
                        "contracting": [before, list(flagged)],
                    },
                },
            )

    # ------------------------------------------------------------------
    # P1 decisions
    # ------------------------------------------------------------------

    def _collect_decisions(self, round_no: int) -> dict[str, FrozenDecision]:
        active = sorted(
            agent_id
            for agent_id, agent in self.state["agents"].items()
            if agent["status"] == "active"
        )
        # ONE committed cutoff for the whole round: thread scheduling in the
        # fan-out below cannot vary what anybody remembers.
        event_log = self.store.events_for_match(self.match_id)
        frozen_state = deepcopy(self.state)
        observations = {
            agent_id: visible_observation(
                frozen_state,
                agent_id,
                self.manifests[agent_id].secret_objective,
                event_log,
            )
            for agent_id in active
        }
        # THE ORACLE IS CAPTURED HERE, before a single line of untrusted code
        # runs, and never re-read from a dict that crossed the provider seam.
        # A provider that edits its observation's ``legal_actions`` in place is
        # editing its own deepcopy and changes nothing the referee consults.
        legal_keys = {
            agent_id: rules.legal_key_set(observations[agent_id])
            for agent_id in active
        }
        legal_hashes = {
            agent_id: _legal_actions_hash(observations[agent_id])
            for agent_id in active
        }

        results: dict[str, tuple[ProviderResult, dict[str, Any], str, str | None]] = {}

        def invoke(
            agent_id: str,
        ) -> tuple[str, ProviderResult, dict[str, Any], str, str | None]:
            # Everything handed across the provider seam is a COPY. The
            # referee's own observation and manifest stay unreachable from
            # untrusted code, so mutation buys nothing.
            manifest = deepcopy(self.manifests[agent_id])
            observation = deepcopy(observations[agent_id])
            prompt = compile_prompt(manifest, observation)
            budget = self.state["agents"][agent_id]["tokens_remaining"]
            estimated = max(
                1,
                sum(len(message["content"]) for message in prompt["messages"]) // 4,
            )
            if budget < estimated + prompt["max_output_tokens"]:
                result = self.autopilot.decide(manifest, prompt, observation)
                return agent_id, result, prompt, "autopilot", "token budget exhausted"
            try:
                result = self.provider.decide(manifest, prompt, observation)
                return agent_id, result, prompt, "valid", None
            except Exception as exc:  # noqa: BLE001 - provider isolation
                result = self.autopilot.decide(manifest, prompt, observation)
                return (
                    agent_id,
                    result,
                    prompt,
                    "provider_fallback",
                    f"{type(exc).__name__}: {str(exc)[:160]}",
                )

        if self.parallel_agents and len(active) > 1:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(invoke, agent_id) for agent_id in active]
                for future in as_completed(futures):
                    agent_id, result, prompt, validity, reason = future.result()
                    results[agent_id] = (result, prompt, validity, reason)
        else:
            for agent_id in active:
                key, result, prompt, validity, reason = invoke(agent_id)
                results[key] = (result, prompt, validity, reason)

        frozen: dict[str, FrozenDecision] = {}
        for agent_id in active:
            result, prompt, validity, fallback_reason = results[agent_id]
            agent = self.state["agents"][agent_id]
            spent = result.input_tokens + result.output_tokens
            before_tokens = agent["tokens_remaining"]
            before_memory = list(agent["memory"])
            agent["tokens_remaining"] = max(0, agent["tokens_remaining"] - spent)
            try:
                raw = json.loads(result.raw_output.strip())
                action = AgentAction.from_dict(raw)
            except (json.JSONDecodeError, ValidationError) as exc:
                action = AgentAction(
                    action="guard",
                    reasoning_summary="Deterministic fallback after invalid output.",
                )
                validity = "invalid_output"
                fallback_reason = str(exc)
                agent["invalid_actions"] += 1
                self._score(
                    agent_id,
                    "invalid_output",
                    scoring.SCORING["invalid_output"],
                    "Malformed structured output",
                )
            if action.memory_write:
                # scratch memory stays 3 x 160 chars
                agent["memory"] = (agent["memory"] + [action.memory_write[:160]])[-3:]
            self._event(
                round_no,
                "resources",
                "agent_resource_update",
                agent_id,
                None,
                f"{agent['name']} spends {spent} tokens.",
                {
                    "changes": {
                        "tokens_remaining": [before_tokens, agent["tokens_remaining"]],
                        "memory": [before_memory, list(agent["memory"])],
                    }
                },
                include_in_narration=False,
            )
            if action.speech:
                self._emit_speech(round_no, agent_id, action.speech)
            self.store.log_decision(
                self.match_id,
                round_no,
                agent_id,
                prompt,
                result.raw_output,
                action.as_dict(),
                validity,
                fallback_reason,
                result.input_tokens,
                result.output_tokens,
                result.provider,
                result.model,
            )
            frozen[agent_id] = FrozenDecision(
                action=action,
                observation=observations[agent_id],
                legal_keys=legal_keys[agent_id],
                legal_actions_hash=legal_hashes[agent_id],
                validity=validity,
                fallback_reason=fallback_reason,
            )
        return frozen

    def _emit_speech(self, round_no: int, speaker_id: str, text: str) -> None:
        """``addressed_ids`` is computed at EMISSION time: immutable, auditable,
        computed once, and not gameable by naming an agent ``a``."""
        agent = self.state["agents"][speaker_id]
        addressed = self._addressed_ids(speaker_id, text)
        speech = {
            "round": round_no,
            "agent_id": speaker_id,
            "name": agent["name"],
            "text": text,
            "room": agent["room"],
            "addressed_ids": addressed,
        }
        self.state["recent_speech"] = (self.state["recent_speech"] + [speech])[-24:]
        self._event(
            round_no,
            "dialogue",
            "agent_speech",
            speaker_id,
            None,
            f'{agent["name"]}: “{text}”',
            {
                "speech": text,
                "room": agent["room"],
                "addressed_ids": addressed,
            },
        )

    def _addressed_ids(self, speaker_id: str, text: str) -> list[str]:
        addressed: list[str] = []
        for agent_id in sorted(self.state["agents"]):
            if agent_id == speaker_id:
                continue
            agent = self.state["agents"][agent_id]
            names = [agent_id]
            # A submitter naming an agent "a" must not capture every line.
            if len(agent["name"]) >= 3:
                names.append(agent["name"])
            for candidate in names:
                if re.search(rf"\b{re.escape(candidate)}\b", text, re.IGNORECASE):
                    addressed.append(agent_id)
                    break
        return addressed

    @staticmethod
    def _legal_in_frozen_decision(decision: FrozenDecision) -> bool:
        """THE seam: membership in the legality oracle CAPTURED AT FREEZE TIME.

        Deliberately does not re-read ``decision.observation['legal_actions']``.
        The published list and the captured set are built from the same bytes in
        P1, but only the captured set is out of reach of anything that ran after
        the freeze. There is still no second rules implementation to drift:
        ``legal_keys`` came from ``rules.legal_key_set``.
        """
        return rules.action_key(decision.action) in decision.legal_keys

    @staticmethod
    def _legal_in_frozen_observation(
        action: AgentAction, observation: dict[str, Any]
    ) -> bool:
        """Kept for tools and tests that only have an observation in hand.

        NOT used by the round loop — see ``_legal_in_frozen_decision``.
        """
        return rules.is_legal(action, observation)

    # ------------------------------------------------------------------
    # P3 action resolution
    # ------------------------------------------------------------------

    def _resolve_action(self, agent_id: str, action: AgentAction) -> None:
        handler: dict[str, Callable[[], None]] = {
            "guard": lambda: self._guard(agent_id),
            "move": lambda: self._move(agent_id, action),
            "step": lambda: self._step(agent_id, action),
            "attack": lambda: self._attack(agent_id, action.target),
            "search": lambda: self._search(agent_id, action),
            "interact": lambda: self._interact(agent_id, action),
            "take": lambda: self._take(agent_id, action),
            "use": lambda: self._use(agent_id, action),
            "rest": lambda: self._rest(agent_id),
        }
        run = handler.get(action.action)
        if run is None:
            self._invalid_action(agent_id, action, "unknown verb")
            return
        run()

    def _guard(self, agent_id: str) -> None:
        agent = self.state["agents"][agent_id]
        before = agent["guard"]
        agent["guard"] = 2
        self._event(
            self.state["round"],
            "agent",
            "guard",
            agent_id,
            None,
            f"{agent['name']} braces for the next blow.",
            {"changes": {"guard": [before, 2]}},
        )

    def _move(self, agent_id: str, action: AgentAction) -> None:
        agent = self.state["agents"][agent_id]
        destination = action.destination or ""
        if destination == EGRESS_ROOM:
            # Resolution-time re-check: the carrier may have fumbled the Crown
            # on an earlier initiative this round. STALE, never a penalty.
            if not rules.escape_gate_ok(self.state, agent_id):
                self._stale(agent_id, action, "the Crown is no longer attuned in hand")
                return
            self._crown_extract(agent_id)
            return
        if rules.is_sealed(self.state, destination):
            self._stale(agent_id, action, "that room has sealed")
            return
        self._move_agent(agent_id, destination, "move")

    def _step(self, agent_id: str, action: AgentAction) -> None:
        """Intra-room repositioning. Legality already proved the tile was free
        and in range at freeze time; a rival may have taken it since, which is
        STALE and never a penalty."""
        agent = self.state["agents"][agent_id]
        want = grid.as_tile(action.tile)
        if not want:
            self._invalid_action(agent_id, action, "step needs a tile")
            return
        room = agent["room"]
        if not grid.in_bounds(room, want):
            self._invalid_action(agent_id, action, "tile is outside the room")
            return
        if want in grid.occupied_tiles(self.state, room, exclude=agent_id):
            self._stale(agent_id, action, "another body reached that tile first")
            return
        before = list(agent.get("tile") or [])
        if grid.distance(before, want) > int(agent.get("move_range") or 1):
            self._invalid_action(agent_id, action, "tile is beyond move range")
            return
        agent["tile"] = list(want)
        hazard = grid.hazard_at(room, want)
        cover = grid.cover_bonus(room, want)
        self._event(
            self.state["round"],
            "agent",
            "step",
            agent_id,
            None,
            f"{agent['name']} moves to [{want[0]},{want[1]}]"
            + (f", into cover behind the {grid.prop_at(room, want)['name']}." if cover
               else "."),
            {
                "changes": {"tile": [before, list(want)]},
                "move_range": agent.get("move_range"),
                "distance": grid.distance(before, want),
                "cover": cover,
                "hazard": hazard["id"] if hazard else None,
            },
        )
        if hazard:
            # Ending a step in a hazard costs you. Chosen, not inflicted: the
            # tile was labelled in the observation the agent read.
            before_hp = agent["hp"]
            agent["hp"] = max(0, agent["hp"] - grid.HAZARD_DAMAGE)
            self._event(
                self.state["round"],
                "hazard",
                "hazard_burn",
                agent_id,
                None,
                f"The {hazard['name']} scorches {agent['name']} for "
                f"{before_hp - agent['hp']}.",
                {
                    "changes": {"hp": [before_hp, agent["hp"]]},
                    "hazard_id": hazard["id"],
                    "tile": list(want),
                    "collateral": True,
                    "credited_to": None,
                },
            )
            if agent["hp"] <= 0:
                # Nobody is credited for a fire: it scores like any accident.
                self._eliminate(
                    agent_id,
                    f"burned by the {hazard['name']}",
                    credited_to=None,
                    collateral=True,
                )

    def _place_on_arrival(self, agent_id: str, destination: str, origin: str) -> None:
        """Arriving through a doorway puts you AT that doorway, or the nearest
        free tile when the threshold is crowded."""
        agent = self.state["agents"][agent_id]
        door = grid.door_tile(destination, origin) or grid.spawn_tile(destination, 0)
        agent["tile"] = list(
            grid.free_tile_near(self.state, destination, door, mover_id=agent_id)
        )

    def _move_agent(self, agent_id: str, destination: str, event_type: str) -> None:
        agent = self.state["agents"][agent_id]
        before = agent["room"]
        agent["room"] = destination
        self._place_on_arrival(agent_id, destination, before)
        visited_added = None
        if destination not in agent["visited"]:
            agent["visited"].append(destination)
            visited_added = destination
        self._event(
            self.state["round"],
            "agent",
            event_type,
            agent_id,
            destination,
            f"{agent['name']} moves to {self.state['rooms'][destination]['name']}.",
            {
                "changes": {
                    "room": [before, destination],
                    "visited_added": visited_added,
                },
                "to": destination,
                "from": before,
            },
        )

    def _crown_extract(self, agent_id: str) -> None:
        agent = self.state["agents"][agent_id]
        crown = self.state["crown"]
        attunement = crown["attunement_rounds"]
        before_room = agent["room"]
        agent["room"] = EGRESS_ROOM
        if EGRESS_ROOM not in agent["visited"]:
            agent["visited"].append(EGRESS_ROOM)
        agent["status"] = "escaped"
        changes = rules.crown_extract(self.state, agent_id)
        changes["room"] = [before_room, EGRESS_ROOM]
        changes["status"] = ["active", "escaped"]
        self.state["winner_agent_id"] = agent_id
        self.state["status"] = "completed"
        self.state["ended_reason"] = "extraction"
        self._score(
            agent_id,
            "extraction",
            scoring.SCORING["extraction"],
            "Extracted with the Ember Crown",
        )
        self._event(
            self.state["round"],
            "referee",
            "crown_extracted",
            agent_id,
            EGRESS_ROOM,
            f"{agent['name']} walks out under open sky with the Ember Crown.",
            {
                "agent_id": agent_id,
                "attunement_rounds": attunement,
                "round": self.state["round"],
                "winner_agent_id": agent_id,
                "changes": changes,
            },
        )

    def _interact(self, agent_id: str, action: AgentAction) -> None:
        agent = self.state["agents"][agent_id]
        room_id = agent["room"]
        if room_id not in SEAL_ROOMS:
            self._invalid_action(agent_id, action, "no seal here")
            return
        if self.state["seals"][room_id] != "inactive":
            self._stale(agent_id, action, "the seal is already resolved")
            return
        if rules.room_has_living_monster(self.state, room_id):
            self._stale(agent_id, action, "a guardian still holds the seal")
            return
        self.state["seals"][room_id] = "active"
        self.state["seal_meta"][room_id] = {
            "activated_by": agent_id,
            "activated_round": self.state["round"],
        }
        self._score(
            agent_id,
            "seal_activated",
            scoring.SCORING["seal_activated"],
            f"Activated the {room_id} seal",
        )
        self._event(
            self.state["round"],
            "agent",
            "seal_activated",
            agent_id,
            self.state["rooms"][room_id]["seal_id"],
            f"{agent['name']} wakes the {self.state['rooms'][room_id]['name']} seal.",
            {
                "room": room_id,
                "points": scoring.SCORING["seal_activated"],
                "changes": {f"seals.{room_id}": ["inactive", "active"]},
            },
        )
        if rules.vault_open(self.state):
            self._event(
                self.state["round"],
                "referee",
                "vault_gate_opened",
                None,
                VAULT_ROOM,
                "Both seals burn. The Ember Vault stands open.",
                {"reason": "seals_active", "seals": dict(self.state["seals"])},
            )

    def _search(self, agent_id: str, action: AgentAction) -> None:
        agent = self.state["agents"][agent_id]
        room_id = agent["room"]
        cache = self.state["caches"].get(room_id)
        if cache is None:
            self._invalid_action(agent_id, action, "no cache here")
            return
        if cache["found"]:
            self._stale(agent_id, action, "the cache is already emptied")
            return
        roll = self._roll(
            6, f"search:r{self.state['round']}:{agent_id}:{room_id}", agent_id
        )
        total = roll + agent["search"]
        if total < 4:
            self._event(
                self.state["round"],
                "agent",
                "search_failure",
                agent_id,
                None,
                f"{agent['name']} searches the {room_id} and finds only dust.",
                {"roll": roll, "search_bonus": agent["search"], "total": total},
            )
            return
        item_id = cache["item_id"]
        points = scoring.cache_find_points(cache)
        cache["found"] = True
        cache["found_by"] = agent_id
        cache["found_round"] = self.state["round"]
        agent["caches_found"].append(room_id)
        rules.inventory_add(self.state, agent_id, item_id)
        if points:
            self._score(agent_id, "cache_first_find", points, f"First to open {room_id}")
        self._event(
            self.state["round"],
            "agent",
            "cache_found",
            agent_id,
            item_id,
            f"{agent['name']} digs out the {items.item_name(item_id)}.",
            {
                "room": room_id,
                "roll": roll,
                "search_bonus": agent["search"],
                "item": items.describe_item(item_id),
                "points": points,
                "changes": {
                    "inventory_added": item_id,
                    f"caches.{room_id}.found": [False, True],
                },
            },
        )

    def _take(self, agent_id: str, action: AgentAction) -> None:
        agent = self.state["agents"][agent_id]
        item_id = action.item or ""
        room_id = agent["room"]
        if item_id not in self.state["floor_items"][room_id]:
            self._stale(agent_id, action, "item already taken")
            return
        rules.floor_remove(self.state, room_id, item_id)
        rules.inventory_add(self.state, agent_id, item_id)
        self._event(
            self.state["round"],
            "agent",
            "item_taken",
            agent_id,
            item_id,
            f"{agent['name']} takes the {items.item_name(item_id)}.",
            {
                "item": items.describe_item(item_id),
                "changes": {"inventory_added": item_id, "floor_removed": item_id},
            },
        )
        if item_id == CROWN_ITEM_ID:
            self._crown_taken(agent_id)

    def _crown_taken(self, agent_id: str) -> None:
        crown = self.state["crown"]
        points = scoring.crown_take_points(crown, agent_id)
        changes = rules.crown_to_carrier(self.state, agent_id)
        if points:
            self._score(agent_id, "crown_taken", points, "Claimed the Ember Crown")
        agent = self.state["agents"][agent_id]
        self._event(
            self.state["round"],
            "referee",
            "crown_taken",
            agent_id,
            CROWN_ITEM_ID,
            f"{agent['name']} lifts the Ember Crown. Attunement resets to zero.",
            {
                "agent_id": agent_id,
                "points": points,
                "transfers": crown["transfers"],
                "changes": changes,
            },
        )

    def _use(self, agent_id: str, action: AgentAction) -> None:
        agent = self.state["agents"][agent_id]
        item_id = action.item or ""
        if item_id not in agent["inventory"]:
            self._stale(agent_id, action, "item unavailable")
            return
        before = agent["hp"]
        heal = items.heal_amount(item_id)
        agent["hp"] = min(agent["max_hp"], agent["hp"] + heal)
        removed = None
        if items.consumed_on_use(item_id):
            rules.inventory_remove(self.state, agent_id, item_id)
            removed = item_id
        self._event(
            self.state["round"],
            "agent",
            "item_used",
            agent_id,
            item_id,
            f"{agent['name']} uses the {items.item_name(item_id)}.",
            {
                "item": items.describe_item(item_id),
                "heal": heal,
                "changes": {"hp": [before, agent["hp"]], "inventory_removed": removed},
            },
        )

    def _rest(self, agent_id: str) -> None:
        agent = self.state["agents"][agent_id]
        before = agent["hp"]
        agent["hp"] = min(agent["max_hp"], agent["hp"] + 2)
        agent["rest_used"] = True
        self._event(
            self.state["round"],
            "agent",
            "rest",
            agent_id,
            None,
            f"{agent['name']} steals a breath from the vault.",
            {"changes": {"hp": [before, agent["hp"]], "rest_used": [False, True]}},
        )

    # ------------------------------------------------------------------
    # combat
    # ------------------------------------------------------------------

    def _attack(self, agent_id: str, target_id: str | None) -> None:
        attacker = self.state["agents"][agent_id]
        target_body = self._body(target_id)
        if target_body is None:
            self._invalid_action(
                agent_id, AgentAction(action="attack", target=target_id), "unknown target"
            )
            return
        if not self._is_valid_combat_target(attacker, target_body):
            self._stale(
                agent_id,
                AgentAction(action="attack", target=target_id),
                "target was defeated, eliminated or moved before resolution",
            )
            return
        self._run_attack(attacker, "agent", target_body)

    def _is_valid_combat_target(
        self, attacker: dict[str, Any], target: dict[str, Any]
    ) -> bool:
        if target["room"] != attacker["room"]:
            return False
        if target["hp"] <= 0:
            return False
        if "status" in target and target["status"] != "active":
            return False
        return True

    def _run_attack(
        self, attacker: dict[str, Any], attacker_kind: str, target: dict[str, Any]
    ) -> None:
        round_no = self.state["round"]
        room_id = attacker["room"]
        attacker_view = (
            combat.combatant_from_agent(attacker)
            if attacker_kind == "agent"
            else combat.combatant_from_monster(attacker)
        )
        target_view = (
            combat.combatant_from_agent(target)
            if "status" in target
            else combat.combatant_from_monster(target)
        )
        occupants = self._room_combatants(room_id)
        attacker_id = attacker["id"]
        target_id = target["id"]

        def roll(sides: int, label: str) -> int:
            return self._roll(sides, label, attacker_id, target_id)

        resolution = combat.resolve_attack(
            round_no=round_no,
            attacker=attacker_view,
            target=target_view,
            room_id=room_id,
            room_occupants=occupants,
            room_reaction_uses=self.state["room_reaction_uses"],
            roll=roll,
        )
        for effect in resolution.effects:
            self._apply_effect(effect)

    def _room_combatants(self, room_id: str) -> list[combat.Combatant]:
        bodies = [
            combat.combatant_from_agent(self.state["agents"][agent_id])
            for agent_id in sorted(self.state["agents"])
            if self.state["agents"][agent_id]["room"] == room_id
            and self.state["agents"][agent_id]["status"] == "active"
            and self.state["agents"][agent_id]["hp"] > 0
        ]
        bodies.extend(
            combat.combatant_from_monster(self.state["monsters"][monster_id])
            for monster_id in sorted(self.state["monsters"])
            if self.state["monsters"][monster_id]["room"] == room_id
            and self.state["monsters"][monster_id]["hp"] > 0
        )
        bodies.sort(key=lambda body: body.id)
        return bodies

    def _apply_effect(self, effect: combat.Effect) -> None:
        """The ONE place a combat effect touches state.

        ``collateral`` and ``credited_to`` are the only signals consulted when
        deciding whether anything scores.
        """
        if effect.kind == "damage":
            self._apply_damage_effect(effect)
            return
        if effect.kind == "drop_item":
            self._apply_drop_effect(effect)
            return
        if effect.kind == "strip_guard":
            self._apply_strip_guard_effect(effect)
            return
        if effect.kind == "reveal_item":
            self._apply_reveal_effect(effect)
            return
        self._emit_effect(effect, dict(effect.payload))

    def _apply_damage_effect(self, effect: combat.Effect) -> None:
        body = self._body(effect.target_id)
        if body is None or body["hp"] <= 0:
            return
        target_kind = "agent" if "status" in body else "monster"
        attacker = self.state["agents"].get(effect.actor_id or "")
        before = body["hp"]
        body["hp"] = max(0, before - effect.amount)
        applied = before - body["hp"]

        payload = dict(effect.payload)
        payload.update(
            {
                "applied": applied,
                "collateral": effect.collateral,
                "credited_to": effect.credited_to,
                "accident": effect.accident,
                "cause": effect.cause,
                "changes": {"hp": [before, body["hp"]]},
            }
        )

        if effect.collateral:
            ledger = self.state["collateral_damage"]
            ledger["total"] += applied
            source = effect.actor_id or "unknown"
            ledger["by_source"][source] = ledger["by_source"].get(source, 0) + applied
            victim = effect.target_id or "unknown"
            ledger["by_victim"][victim] = ledger["by_victim"].get(victim, 0) + applied
            if attacker is not None:
                attacker["collateral_dealt"] += applied
            body["collateral_taken"] = body.get("collateral_taken", 0) + applied
            payload["scoring"] = {"category": "collateral_no_credit", "points": 0}
        elif effect.credited_to and attacker is not None:
            if target_kind == "monster":
                attacker["monster_damage"] += applied
                points = scoring.register_monster_hit(attacker)
                if points:
                    self._score(
                        effect.credited_to,
                        "monster_hit",
                        points,
                        f"Damage to {body['name']}",
                    )
                payload["scoring"] = {
                    "category": "monster_hit",
                    "points": points,
                    "hits_this_round": attacker[scoring.ROUND_HIT_COUNTER],
                    "capped": points == 0,
                }
            else:
                attacker["agent_damage"] += applied
                payload["scoring"] = {"category": "agent_damage", "points": 0}

        self._emit_effect(effect, payload)

        if body["hp"] == 0:
            credited = None if effect.collateral else effect.credited_to
            if target_kind == "monster":
                self._on_monster_death(
                    body["id"], credited, effect.collateral, effect.cause
                )
            else:
                self._eliminate(
                    body["id"],
                    reason=effect.cause or "combat",
                    credited_to=credited,
                    collateral=effect.collateral,
                )

    def _apply_drop_effect(self, effect: combat.Effect) -> None:
        agent = self.state["agents"].get(effect.actor_id or "")
        item_id = effect.item_id or ""
        payload = dict(effect.payload)
        if agent is None or item_id not in agent["inventory"]:
            payload.update({"applied": False})
            self._emit_effect(effect, payload)
            return
        room_id = agent["room"]
        rules.inventory_remove(self.state, agent["id"], item_id)
        rules.floor_add(self.state, room_id, item_id)
        payload.update(
            {
                "applied": True,
                "changes": {
                    "inventory_removed": item_id,
                    "floor_added": item_id,
                    "room": room_id,
                },
            }
        )
        self._emit_effect(effect, payload)
        if item_id == CROWN_ITEM_ID:
            self._crown_dropped(room_id, "wild_swing_self_drop", agent["id"])

    def _apply_strip_guard_effect(self, effect: combat.Effect) -> None:
        body = self._body(effect.target_id)
        payload = dict(effect.payload)
        if body is None:
            payload["applied"] = False
            self._emit_effect(effect, payload)
            return
        before = body.get("guard", 0)
        body["guard"] = 0
        payload.update({"applied": bool(before), "changes": {"guard": [before, 0]}})
        self._emit_effect(effect, payload)

    def _apply_reveal_effect(self, effect: combat.Effect) -> None:
        room_id = effect.room_id or ""
        item_id = effect.item_id or ""
        before = self.state["room_reaction_uses"].get(room_id, 0)
        rules.floor_add(self.state, room_id, item_id)
        self.state["room_reaction_uses"][room_id] = before + 1
        payload = dict(effect.payload)
        payload.update(
            {
                "applied": True,
                "changes": {
                    f"floor_items.{room_id}.added": item_id,
                    f"room_reaction_uses.{room_id}": [before, before + 1],
                },
            }
        )
        self._emit_effect(effect, payload)

    def _emit_effect(self, effect: combat.Effect, payload: dict[str, Any]) -> None:
        self._event(
            self.state["round"],
            effect.phase,
            effect.event_type,
            effect.actor_id,
            effect.target_id,
            effect.public_text,
            payload,
        )

    def _on_monster_death(
        self,
        monster_id: str,
        credited_to: str | None,
        collateral: bool,
        cause: str,
    ) -> None:
        monster = self.state["monsters"][monster_id]
        if monster.get("death_cause"):
            return
        monster["death_cause"] = "collateral" if collateral else "combat"
        monster["defeated_by"] = credited_to
        category, points = scoring.finishing_blow(monster_id)
        if credited_to and category and points:
            killer = self.state["agents"].get(credited_to)
            if killer is not None:
                killer["kills"] += 1
            self._score(credited_to, category, points, f"Felled {monster['name']}")
        else:
            category, points = "collateral_kill_no_credit", 0
        self._event(
            self.state["round"],
            "referee",
            "monster_defeated",
            credited_to,
            monster_id,
            f"{monster['name']} falls.",
            {
                "monster_id": monster_id,
                "cause": cause,
                "collateral": collateral,
                "accident": collateral,
                "credited_to": credited_to,
                "scoring": {"category": category, "points": points},
            },
        )
        if monster_id == combat.WARDEN_ID:
            changes = rules.crown_unlock(self.state, self.state["round"])
            self._event(
                self.state["round"],
                "referee",
                "crown_unlocked",
                credited_to,
                CROWN_ITEM_ID,
                "The Ember Crown crashes free onto the vault floor.",
                {
                    "room": VAULT_ROOM,
                    "killer_id": credited_to,
                    "collateral": collateral,
                    "changes": changes,
                },
            )

    def _crown_dropped(self, room_id: str, cause: str, previous_carrier: str) -> None:
        changes = rules.crown_to_floor(self.state, room_id)
        self._event(
            self.state["round"],
            "referee",
            "crown_dropped",
            previous_carrier,
            CROWN_ITEM_ID,
            "The Ember Crown clatters to the floor, attunement broken.",
            {
                "cause": cause,
                "room": room_id,
                "previous_carrier": previous_carrier,
                "changes": changes,
            },
        )

    def _eliminate(
        self,
        agent_id: str,
        reason: str,
        *,
        credited_to: str | None = None,
        collateral: bool = False,
    ) -> None:
        agent = self.state["agents"][agent_id]
        if agent["status"] != "active":
            return  # idempotent: a body can be reached by two paths in a round
        agent["status"] = "eliminated"
        agent["eliminated_round"] = self.state["round"]
        room_id = agent["room"]
        dropped = sorted(agent["inventory"])
        for item_id in dropped:
            rules.floor_add(self.state, room_id, item_id)
        agent["inventory"] = []
        category, points = "collateral_kill_no_credit", 0
        if credited_to and not collateral:
            killer = self.state["agents"].get(credited_to)
            if killer is not None:
                earned = scoring.register_direct_elimination(killer, agent_id)
                if earned:
                    killer["kills"] += 1
                    self._score(
                        credited_to,
                        "direct_elimination",
                        earned,
                        f"Eliminated {agent['name']}",
                    )
                category, points = "direct_elimination", earned
        self._event(
            self.state["round"],
            "referee",
            "agent_eliminated",
            credited_to,
            agent_id,
            f"{agent['name']} is eliminated ({reason}).",
            {
                "reason": reason,
                "cause": reason,
                "room": room_id,
                "collateral": collateral,
                "accident": collateral,
                "credited_to": credited_to,
                "killer_id": credited_to,
                "scoring": {"category": category, "points": points},
                "changes": {
                    "status": ["active", "eliminated"],
                    "dropped_items": dropped,
                },
            },
        )
        if CROWN_ITEM_ID in dropped:
            self._crown_dropped(room_id, "elimination", agent_id)

    # ------------------------------------------------------------------
    # P4 monster phase — deterministic, no model call
    # ------------------------------------------------------------------

    def _monster_phase(self, round_no: int) -> None:
        for monster_id in sorted(self.state["monsters"]):
            if self.state.get("winner_agent_id"):
                return
            monster = self.state["monsters"][monster_id]
            if monster["hp"] <= 0:
                continue
            present = [
                self.state["agents"][agent_id]
                for agent_id in sorted(self.state["agents"])
                if self.state["agents"][agent_id]["room"] == monster["room"]
                and self.state["agents"][agent_id]["status"] == "active"
                and self.state["agents"][agent_id]["hp"] > 0
            ]
            if not present:
                continue

            # A monster attacks only what it can reach; otherwise it closes.
            # Deterministic throughout: nearest, then lowest HP, then id.
            reach = int(monster.get("reach", 1))
            m_tile = grid.as_tile(monster.get("tile"))
            in_reach = [
                a for a in present
                if not m_tile
                or not grid.as_tile(a.get("tile"))
                or grid.in_reach(m_tile, a["tile"], reach)
            ]
            if not in_reach and m_tile:
                quarry = min(
                    present,
                    key=lambda a: (
                        grid.distance(m_tile, grid.as_tile(a.get("tile")) or m_tile),
                        a["hp"],
                        a["id"],
                    ),
                )
                goal = grid.as_tile(quarry.get("tile"))
                before_tile = list(m_tile)
                moved_to = grid.step_toward(
                    self.state, monster["room"], m_tile, goal,
                    grid.MONSTER_STEP, mover_id=monster_id,
                )
                if tuple(moved_to) != tuple(m_tile):
                    monster["tile"] = list(moved_to)
                    self._event(
                        round_no, "monster", "monster_step", monster_id, quarry["id"],
                        f"{monster['name']} stalks toward {quarry['name']}.",
                        {
                            "changes": {"tile": [before_tile, list(moved_to)]},
                            "reach": reach,
                        },
                    )
                m_tile = grid.as_tile(monster.get("tile"))
                in_reach = [
                    a for a in present
                    if grid.in_reach(m_tile, a.get("tile") or m_tile, reach)
                ]
            if not in_reach:
                continue

            candidates = [combat.combatant_from_agent(a) for a in in_reach]
            monster_view = combat.combatant_from_monster(monster)

            def roll(sides: int, label: str, mid: str = monster_id) -> int:
                return self._roll(sides, label, mid)

            target_id = combat.choose_monster_target(
                round_no=round_no,
                monster=monster_view,
                candidates=candidates,
                roll=roll,
            )
            self._run_attack(monster, "monster", self.state["agents"][target_id])

    # ------------------------------------------------------------------
    # P5 end-of-round upkeep
    # ------------------------------------------------------------------

    def _end_round_upkeep(self, round_no: int) -> None:
        # P5.a ATTUNEMENT — before contraction, so a carrier force-moved out of
        # a sealing room still banks the round it survived.
        tick = rules.crown_attune(self.state)
        if tick:
            carrier_id = tick["agent_id"]
            self._score(
                carrier_id,
                "attunement_round",
                scoring.SCORING["attunement_round"],
                "Completed an attunement round",
            )
            self._event(
                round_no,
                "referee",
                "crown_attuned",
                carrier_id,
                CROWN_ITEM_ID,
                f"{self.state['agents'][carrier_id]['name']} settles deeper into "
                "the Crown.",
                {
                    "agent_id": carrier_id,
                    "attunement_rounds": self.state["crown"]["attunement_rounds"],
                    "changes": tick["changes"],
                },
            )

        # P5.b CONTRACTION
        room_id = rules.sealing_room_for_round(round_no)
        if room_id and not rules.is_sealed(self.state, room_id):
            self._apply_contraction(round_no, room_id)

        # P5.c ACT II SURVIVAL
        if round_no == rules.ACT_II_LAST_ROUND:
            survivors = [
                agent_id
                for agent_id in sorted(self.state["agents"])
                if self.state["agents"][agent_id]["status"] == "active"
            ]
            for agent_id in survivors:
                self._score(
                    agent_id,
                    "survived_act_ii",
                    scoring.SCORING["survived_act_ii"],
                    "Survived through Act II",
                )
            self._event(
                round_no,
                "referee",
                "act_two_survival",
                None,
                None,
                "The long knife of Act II is done; the survivors are counted.",
                {
                    "survivors": survivors,
                    "points": scoring.SCORING["survived_act_ii"],
                },
            )

        # P5.e TERMINAL CHECK
        if not any(
            agent["status"] == "active" for agent in self.state["agents"].values()
        ):
            self.state["ended_reason"] = self.state["ended_reason"] or "all_eliminated"

    def _apply_contraction(self, round_no: int, room_id: str) -> None:
        """Deterministic; consumes ZERO dice, so the roll counter stays aligned
        across replays regardless of how the map collapses."""
        contraction = self.state["contraction"]
        occupants = self._active_agents_in(room_id)
        living_monsters = [
            monster["id"] for monster in rules.living_monsters_in(self.state, room_id)
        ]
        self._event(
            round_no,
            "referee",
            "room_sealing",
            None,
            room_id,
            f"{self.state['rooms'][room_id]['name']} begins to close.",
            {
                "room": room_id,
                "round": round_no,
                "occupants": occupants,
                "floor_items": list(self.state["floor_items"][room_id]),
                "living_monsters": living_monsters,
            },
        )

        # 2. SEAL VOIDING — records that this seal can NEVER be lit. It scores 0
        #    and it does NOT open the vault: "both seals must be ACTIVE" is a
        #    hard map rule, so letting the gates go unlit permanently closes the
        #    vault gate instead of opening it for free.
        if room_id in SEAL_ROOMS and self.state["seals"][room_id] == "inactive":
            was_closed = rules.gate_permanently_closed(self.state)
            self.state["seals"][room_id] = "voided"
            self._event(
                round_no,
                "referee",
                "seal_voided",
                None,
                room_id,
                f"The {room_id} seal is swallowed unlit.",
                {
                    "room": room_id,
                    "points": 0,
                    "reason": "room sealed before the seal was activated",
                    "changes": {f"seals.{room_id}": ["inactive", "voided"]},
                },
            )
            if rules.gate_permanently_closed(self.state) and not was_closed:
                self._event(
                    round_no,
                    "referee",
                    "vault_gate_permanently_closed",
                    None,
                    VAULT_ROOM,
                    "With that seal gone unlit, the vault gate can never be opened.",
                    {
                        "reason": "voided",
                        "seals": dict(self.state["seals"]),
                        "vault_open": False,
                        "note": (
                            "only referee relocation reaches the vault from here"
                        ),
                    },
                )

        # 3. ENTOMBMENT — guardians are never relocated; the vault stays a
        #    single-monster room and nobody is paid a finishing blow.
        entombed = []
        for monster_id in living_monsters:
            monster = self.state["monsters"][monster_id]
            before = monster["hp"]
            monster["hp"] = 0
            monster["death_cause"] = "contraction"
            monster["defeated_by"] = None
            entombed.append(monster_id)
            self._event(
                round_no,
                "referee",
                "monster_entombed",
                None,
                monster_id,
                f"{monster['name']} is buried with the room.",
                {
                    "monster_id": monster_id,
                    "room": room_id,
                    "points": 0,
                    "changes": {"hp": [before, 0]},
                },
            )

        # 4. FORCED EVACUATION — RELOCATION, not entry. The brief mandates the
        #    sweep, so it happens whatever the seals say, but it never satisfies
        #    or substitutes for the gate: ``vault_open`` is untouched, the move
        #    is stamped ``gate_bypassed``, and nobody is paid for it.
        moved = []
        for agent_id in occupants:
            agent = self.state["agents"][agent_id]
            before_room = agent["room"]
            gate_bypassed = not rules.vault_open(self.state)
            agent["room"] = rules.CONTRACTION_REFUGE
            # Shoved through the nearest opening, not teleported onto a body.
            agent["tile"] = list(
                grid.free_tile_near(
                    self.state,
                    rules.CONTRACTION_REFUGE,
                    grid.door_tile(rules.CONTRACTION_REFUGE, before_room)
                    or grid.spawn_tile(rules.CONTRACTION_REFUGE, 0),
                    mover_id=agent_id,
                )
            )
            visited_added = None
            if rules.CONTRACTION_REFUGE not in agent["visited"]:
                agent["visited"].append(rules.CONTRACTION_REFUGE)
                visited_added = rules.CONTRACTION_REFUGE
            moved.append(agent_id)
            self._event(
                round_no,
                "referee",
                "agent_force_moved",
                agent_id,
                rules.CONTRACTION_REFUGE,
                f"{agent['name']} is swept into the Ember Vault.",
                {
                    "agent_id": agent_id,
                    "from": before_room,
                    "to": rules.CONTRACTION_REFUGE,
                    "reason": "contraction",
                    "gate_bypassed": gate_bypassed,
                    "changes": {
                        "room": [before_room, rules.CONTRACTION_REFUGE],
                        "visited_added": visited_added,
                    },
                },
            )

        # 5. FLOOR RELOCATION — without this a Crown dropped in a sealing room
        #    would be walled off and the match unwinnable by extraction.
        relocated = sorted(self.state["floor_items"][room_id])
        self.state["floor_items"][room_id] = []
        for item_id in relocated:
            rules.floor_add(self.state, rules.CONTRACTION_REFUGE, item_id)
        crown_moved = CROWN_ITEM_ID in relocated
        if relocated:
            self._event(
                round_no,
                "referee",
                "floor_items_relocated",
                None,
                room_id,
                "What was left on the floor slides into the vault.",
                {
                    "from": room_id,
                    "to": rules.CONTRACTION_REFUGE,
                    "items": relocated,
                    "crown_moved": crown_moved,
                },
            )
        if crown_moved:
            rules.crown_to_floor(self.state, rules.CONTRACTION_REFUGE)

        # 6. CLOSE
        before_sealed = list(contraction["sealed"])
        contraction["sealed"].append(room_id)
        contraction["contracting"] = [
            other for other in contraction["contracting"] if other != room_id
        ]
        self._event(
            round_no,
            "referee",
            "room_sealed",
            None,
            room_id,
            f"{self.state['rooms'][room_id]['name']} is gone.",
            {
                "room": room_id,
                "sealed": list(contraction["sealed"]),
                "agents_moved": moved,
                "items_moved": relocated,
                "monsters_entombed": entombed,
                "changes": {
                    "contraction.sealed": [before_sealed, list(contraction["sealed"])]
                },
            },
        )

    def _active_agents_in(self, room_id: str) -> list[str]:
        return [
            agent_id
            for agent_id in sorted(self.state["agents"])
            if self.state["agents"][agent_id]["room"] == room_id
            and self.state["agents"][agent_id]["status"] == "active"
        ]

    def _body(self, body_id: str | None) -> dict[str, Any] | None:
        if body_id is None:
            return None
        if body_id in self.state["agents"]:
            return self.state["agents"][body_id]
        if body_id in self.state["monsters"]:
            return self.state["monsters"][body_id]
        return None

    # ------------------------------------------------------------------
    # referee bookkeeping
    # ------------------------------------------------------------------

    def _invalid_action(self, agent_id: str, action: AgentAction, reason: str) -> None:
        agent = self.state["agents"][agent_id]
        agent["invalid_actions"] += 1
        self._score(
            agent_id, "invalid_action", scoring.SCORING["invalid_action"], reason
        )
        agent["guard"] = 2
        self._event(
            self.state["round"],
            "referee",
            "invalid_action_fallback",
            agent_id,
            None,
            f"{agent['name']}'s illegal action becomes Guard.",
            {
                "submitted_action": action.as_dict(),
                "reason": reason,
                "referee_decision": "guard",
                "points": scoring.SCORING["invalid_action"],
                "changes": {"guard": [0, 2]},
            },
        )

    def _stale(self, agent_id: str, action: AgentAction, reason: str) -> None:
        self._event(
            self.state["round"],
            "referee",
            "stale_action",
            agent_id,
            action.target or action.destination or action.item,
            f"{self.state['agents'][agent_id]['name']}'s action finds nothing there.",
            {
                "submitted_action": action.as_dict(),
                "reason": reason,
                "referee_decision": "no_effect_no_penalty",
                "points": 0,
            },
        )

    def _roll(
        self,
        sides: int,
        label: str,
        actor_id: str | None = None,
        target_id: str | None = None,
    ) -> int:
        value, proof = self.rng.roll(sides, label)
        self._event(
            self.state.get("round", 0),
            "dice",
            "dice_roll",
            actor_id,
            target_id,
            f"{label} → d{sides} = {value}",
            {"proof": proof},
            include_in_narration=False,
        )
        return value

    def _score(self, agent_id: str, category: str, points: int, detail: str) -> None:
        agent = self.state["agents"][agent_id]
        agent["score"] += points
        breakdown = agent["score_breakdown"]
        breakdown[category] = breakdown.get(category, 0) + points
        self.store.add_score(
            self.match_id,
            self.state.get("round", 0),
            agent_id,
            category,
            points,
            detail,
        )

    def _narrate(self, round_no: int) -> str:
        lines = list(self.round_lines)
        prompt = compile_narration_prompt(round_no, lines)
        fallback_reason = None
        try:
            result = self.provider.narrate(round_no, prompt, lines)
            narration = result.raw_output
            if not narration or len(narration) > 1_200:
                raise ValueError("narration length outside bounds")
        except Exception as exc:  # noqa: BLE001 - provider isolation
            fallback_reason = f"{type(exc).__name__}: {str(exc)[:160]}"
            result = self.autopilot.narrate(round_no, prompt, lines)
            narration = result.raw_output
        self.store.append_audit(
            self.match_id,
            "gm_narration",
            {
                "round_no": round_no,
                "prompt": prompt,
                "raw_output": narration,
                "usage": {
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "provider": result.provider,
                    "model": result.model,
                },
                "fallback_reason": fallback_reason,
            },
        )
        return narration

    def _event(
        self,
        round_no: int,
        phase: str,
        event_type: str,
        actor_id: str | None,
        target_id: str | None,
        public_text: str,
        payload: dict[str, Any],
        *,
        include_in_narration: bool = True,
    ) -> None:
        self.store.append_event(
            self.match_id,
            round_no,
            phase,
            event_type,
            actor_id,
            target_id,
            public_text,
            payload,
            self.state,
        )
        if include_in_narration and phase != "narration":
            self.round_lines.append(public_text)

    def _is_terminal(self) -> bool:
        if self.state.get("winner_agent_id"):
            return True
        return not any(
            agent["status"] == "active" for agent in self.state["agents"].values()
        )

    # ------------------------------------------------------------------
    # finalize
    # ------------------------------------------------------------------

    def _finalize(self) -> None:
        self.state["status"] = "completed"
        if not self.state["ended_reason"]:
            self.state["ended_reason"] = "rounds_exhausted"
        for agent_id in sorted(self.state["agents"]):
            agent = self.state["agents"][agent_id]
            objective = self.manifests[agent_id].secret_objective
            completed = scoring.objective_complete(self.state, agent_id, objective)
            if completed:
                self._score(
                    agent_id,
                    "secret_objective",
                    scoring.SCORING["secret_objective"],
                    f"Completed {objective}",
                )
            self._event(
                self.state["round"],
                "scoring",
                "objective_reveal",
                agent_id,
                None,
                (
                    f"{agent['name']}'s secret objective was "
                    f"{objective.replace('_', ' ')}"
                    + ("—completed." if completed else "—failed.")
                ),
                {"objective": objective, "completed": completed},
            )

        placements = scoring.placements(self.state)
        order = scoring.placement_order(self.state)
        if not self.state["winner_agent_id"] and order:
            self.state["winner_agent_id"] = order[0]
        self._event(
            self.state["round"],
            "scoring",
            "final_scores",
            None,
            None,
            "The vault tallies its debts.",
            {
                "placements": placements,
                "ended_reason": self.state["ended_reason"],
                "winner_agent_id": self.state["winner_agent_id"],
                "scores": {
                    agent_id: self.state["agents"][agent_id]["score"]
                    for agent_id in sorted(self.state["agents"])
                },
            },
        )
        self.store.save_snapshot(
            self.match_id, self.state["round"], "final", self.state
        )
        self.store.finish_match(self.match_id, self.state, placements)


def rerun_state_hashes(
    manifests: list[AgentManifest], seed: int, store_path: str
) -> list[str]:
    store = ArenaStore(store_path)
    try:
        match_id = ArenaEngine(
            store, MockDecisionProvider(), parallel_agents=False
        ).run(manifests, seed)
        bundle = store.replay_bundle(match_id)
        return [snapshot["state_hash"] for snapshot in bundle["snapshots"]]
    finally:
        store.close()
