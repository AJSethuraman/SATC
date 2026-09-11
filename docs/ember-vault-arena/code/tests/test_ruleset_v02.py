from __future__ import annotations

"""v0.2 ruleset tests: acts, seals, the Crown lifecycle, contraction, Wild
Swing determinism, collateral scoring, observation privacy and disclosure."""

import json
import tempfile
import unittest
from pathlib import Path

from arena import combat, items, rules, scoring
from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.models import AgentAction
from arena.providers import MockDecisionProvider
from arena.rng import HashRNG
from arena.storage import ArenaStore, canonical_json


CROWN = rules.CROWN_ITEM_ID


class GuardOnlyProvider(MockDecisionProvider):
    """Everyone camps. Used to prove the map cannot be skipped by waiting."""

    def decide(self, manifest, prompt, observation):
        from arena.models import ProviderResult

        return ProviderResult(
            raw_output=json.dumps(
                {
                    "action": "guard",
                    "target": None,
                    "destination": None,
                    "item": None,
                    "speech": "",
                    "reasoning_summary": "camp",
                    "memory_write": "camp",
                }
            ),
            input_tokens=10,
            output_tokens=10,
            provider="test",
            model="camper",
        )


class RulesetTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifests = load_manifests()
        self._stores: list[ArenaStore] = []

    def tearDown(self):
        for store in self._stores:
            store.close()
        self.temp.cleanup()

    # -- helpers ---------------------------------------------------------

    def engine(self, name: str = "unit.db", seed: int = 7) -> ArenaEngine:
        store = ArenaStore(self.root / name)
        self._stores.append(store)
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=False)
        engine.match_id = "unit"
        engine.manifests = {manifest.id: manifest for manifest in self.manifests}
        engine.state = rules.new_match_state(self.manifests, seed)
        engine.state["status"] = "running"
        engine.state["round"] = 1
        engine.rng = HashRNG(seed)
        return engine

    def observation(self, engine: ArenaEngine, agent_id: str) -> dict:
        return rules.visible_observation(
            engine.state,
            agent_id,
            engine.manifests[agent_id].secret_objective,
            [],
        )

    def events(self, engine: ArenaEngine, event_type: str) -> list[dict]:
        with engine.store.lock:
            rows = engine.store.conn.execute(
                "SELECT * FROM events WHERE match_id=? AND event_type=? ORDER BY seq",
                (engine.match_id, event_type),
            ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]

    def scores(self, engine: ArenaEngine, agent_id: str) -> list[dict]:
        with engine.store.lock:
            rows = engine.store.conn.execute(
                "SELECT * FROM scores WHERE match_id=? AND agent_id=? ORDER BY id",
                (engine.match_id, agent_id),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def has_action(observation, action, **slots) -> bool:
        for entry in observation["legal_actions"]:
            if entry["action"] != action:
                continue
            if all(entry.get(key) == value for key, value in slots.items()):
                return True
        return False

    def open_vault_state(self, engine: ArenaEngine, carrier: str, attunement: int):
        state = engine.state
        state["round"] = 8
        state["act"] = rules.act_for_round(8)
        state["monsters"]["crown_warden"]["hp"] = 0
        state["monsters"]["crown_warden"]["death_cause"] = "combat"
        state["seals"] = {room: "active" for room in rules.SEAL_ROOMS}
        state["agents"][carrier]["room"] = rules.VAULT_ROOM
        rules.inventory_add(state, carrier, CROWN)
        state["crown"].update(
            {
                "status": "carried",
                "carrier_id": carrier,
                "room": None,
                "attunement_rounds": attunement,
                "unlocked_round": 6,
            }
        )


# ---------------------------------------------------------------------------
# Crown: escape gate, attunement, transfers
# ---------------------------------------------------------------------------


class CrownTests(RulesetTestCase):
    def test_escape_illegal_at_attunement_zero_and_one_legal_at_two(self):
        move = AgentAction(action="move", destination=rules.EGRESS_ROOM)
        for attunement in (0, 1):
            engine = self.engine(f"escape_{attunement}.db")
            self.open_vault_state(engine, "bramble", attunement)
            observation = self.observation(engine, "bramble")
            self.assertFalse(
                self.has_action(observation, "move", destination=rules.EGRESS_ROOM),
                f"egress must not be enumerated at attunement {attunement}",
            )
            self.assertFalse(rules.is_legal(move, observation))
            self.assertFalse(rules.escape_gate_ok(engine.state, "bramble"))

        engine = self.engine("escape_2.db")
        self.open_vault_state(engine, "bramble", 2)
        observation = self.observation(engine, "bramble")
        self.assertTrue(
            self.has_action(observation, "move", destination=rules.EGRESS_ROOM)
        )
        self.assertTrue(rules.is_legal(move, observation))
        engine._resolve_action("bramble", move)
        self.assertEqual(engine.state["agents"]["bramble"]["status"], "escaped")
        self.assertEqual(engine.state["winner_agent_id"], "bramble")
        self.assertEqual(engine.state["crown"]["status"], "escaped")
        self.assertEqual(engine.state["ended_reason"], "extraction")
        self.assertIn(
            ("extraction", scoring.SCORING["extraction"]),
            [(row["category"], row["points"]) for row in self.scores(engine, "bramble")],
        )

    def test_non_carrier_can_never_enter_egress(self):
        engine = self.engine("noncarrier.db")
        self.open_vault_state(engine, "bramble", 2)
        engine.state["agents"]["nix"]["room"] = rules.VAULT_ROOM
        observation = self.observation(engine, "nix")
        self.assertFalse(
            self.has_action(observation, "move", destination=rules.EGRESS_ROOM)
        )
        self.assertFalse(
            rules.is_legal(
                AgentAction(action="move", destination=rules.EGRESS_ROOM), observation
            )
        )

    def test_attunement_ticks_at_end_of_round_only(self):
        engine = self.engine("attune.db")
        self.open_vault_state(engine, "bramble", 0)
        engine.state["round"] = 6
        engine._end_round_upkeep(6)
        self.assertEqual(engine.state["crown"]["attunement_rounds"], 1)
        engine.state["round"] = 7
        engine._end_round_upkeep(7)
        self.assertEqual(engine.state["crown"]["attunement_rounds"], 2)
        self.assertEqual(
            engine.state["crown"]["hold_rounds_by_agent"]["bramble"], 2
        )
        attunement_points = [
            row["points"]
            for row in self.scores(engine, "bramble")
            if row["category"] == "attunement_round"
        ]
        self.assertEqual(attunement_points, [2, 2])
        self.assertEqual(len(self.events(engine, "crown_attuned")), 2)

    def test_transfer_resets_attunement_and_re_awards_take(self):
        engine = self.engine("transfer.db")
        self.open_vault_state(engine, "bramble", 2)
        engine.state["agents"]["nix"]["room"] = rules.VAULT_ROOM

        # The carrier is eliminated: the Crown lands on that room's floor with
        # attunement zeroed AT DROP TIME, never advertising a stale value.
        engine._eliminate("bramble", "test elimination")
        crown = engine.state["crown"]
        self.assertEqual(crown["status"], "floor")
        self.assertIsNone(crown["carrier_id"])
        self.assertEqual(crown["attunement_rounds"], 0)
        self.assertEqual(crown["room"], rules.VAULT_ROOM)
        self.assertIn(CROWN, engine.state["floor_items"][rules.VAULT_ROOM])
        dropped = self.events(engine, "crown_dropped")
        self.assertEqual(dropped[-1]["payload"]["cause"], "elimination")

        transfers_before = crown["transfers"]
        engine._resolve_action("nix", AgentAction(action="take", item=CROWN))
        self.assertEqual(crown["status"], "carried")
        self.assertEqual(crown["carrier_id"], "nix")
        self.assertEqual(crown["attunement_rounds"], 0)
        self.assertEqual(crown["transfers"], transfers_before + 1)
        self.assertIn(
            ("crown_taken", scoring.SCORING["crown_taken"]),
            [(row["category"], row["points"]) for row in self.scores(engine, "nix")],
        )
        # A fresh holder cannot walk out on the transfer round.
        self.assertFalse(rules.escape_gate_ok(engine.state, "nix"))

    def test_crown_ledger_invariant_holds_through_the_lifecycle(self):
        engine = self.engine("ledger.db")
        self.assertTrue(rules.crown_ledger_ok(engine.state))
        self.open_vault_state(engine, "bramble", 1)
        self.assertTrue(rules.crown_ledger_ok(engine.state))
        engine._eliminate("bramble", "test")
        self.assertTrue(rules.crown_ledger_ok(engine.state))
        engine.state["agents"]["nix"]["room"] = rules.VAULT_ROOM
        engine._resolve_action("nix", AgentAction(action="take", item=CROWN))
        self.assertTrue(rules.crown_ledger_ok(engine.state))

    def test_crown_locked_until_the_warden_dies(self):
        engine = self.engine("locked.db")
        state = engine.state
        self.assertEqual(state["crown"]["status"], "locked")
        self.assertFalse(
            any(CROWN in pile for pile in state["floor_items"].values())
        )
        state["monsters"]["crown_warden"]["hp"] = 0
        engine._on_monster_death("crown_warden", "bramble", False, "attack")
        self.assertEqual(state["crown"]["status"], "floor")
        self.assertEqual(state["floor_items"][rules.VAULT_ROOM].count(CROWN), 1)
        self.assertTrue(self.events(engine, "crown_unlocked"))
        self.assertIn(
            ("warden_finishing_blow", 5),
            [(row["category"], row["points"]) for row in self.scores(engine, "bramble")],
        )


# ---------------------------------------------------------------------------
# Seals, the vault gate and acts
# ---------------------------------------------------------------------------


class GateTests(RulesetTestCase):
    def _stand_in_gate(self, engine: ArenaEngine, agent_id: str = "bramble"):
        engine.state["agents"][agent_id]["room"] = "ironwood_gate"
        engine.state["monsters"]["ironwood_guardian"]["hp"] = 0

    def test_neither_seal_alone_opens_the_vault(self):
        engine = self.engine("gate.db")
        self._stand_in_gate(engine)
        move = AgentAction(action="move", destination=rules.VAULT_ROOM)

        self.assertFalse(rules.vault_open(engine.state))
        observation = self.observation(engine, "bramble")
        self.assertFalse(
            self.has_action(observation, "move", destination=rules.VAULT_ROOM)
        )
        self.assertFalse(rules.is_legal(move, observation))

        engine.state["seals"]["ironwood_gate"] = "active"
        self.assertFalse(rules.vault_open(engine.state))
        observation = self.observation(engine, "bramble")
        self.assertFalse(
            self.has_action(observation, "move", destination=rules.VAULT_ROOM)
        )

        engine.state["seals"]["ossuary_gate"] = "active"
        self.assertTrue(rules.vault_open(engine.state))
        observation = self.observation(engine, "bramble")
        self.assertTrue(
            self.has_action(observation, "move", destination=rules.VAULT_ROOM)
        )
        self.assertTrue(rules.is_legal(move, observation))

    def test_seal_requires_a_dead_guardian_and_pays_five(self):
        engine = self.engine("seal.db")
        engine.state["agents"]["bramble"]["room"] = "ironwood_gate"
        observation = self.observation(engine, "bramble")
        self.assertFalse(self.has_action(observation, "interact", target="ironwood_seal"))

        engine.state["monsters"]["ironwood_guardian"]["hp"] = 0
        observation = self.observation(engine, "bramble")
        self.assertTrue(self.has_action(observation, "interact", target="ironwood_seal"))
        engine._resolve_action(
            "bramble", AgentAction(action="interact", target="ironwood_seal")
        )
        self.assertEqual(engine.state["seals"]["ironwood_gate"], "active")
        self.assertIn(
            ("seal_activated", 5),
            [(row["category"], row["points"]) for row in self.scores(engine, "bramble")],
        )

    def test_pvp_illegal_in_act_one_and_legal_in_act_two(self):
        engine = self.engine("pvp.db")
        state = engine.state
        state["agents"]["bramble"]["room"] = "threshold"
        state["agents"]["nix"]["room"] = "threshold"
        attack = AgentAction(action="attack", target="nix")

        state["round"] = 3
        state["act"] = rules.act_for_round(3)
        self.assertEqual(state["act"], 1)
        observation = self.observation(engine, "bramble")
        self.assertFalse(observation["public_state"]["agent_attacks_allowed"])
        self.assertFalse(self.has_action(observation, "attack", target="nix"))
        self.assertFalse(rules.is_legal(attack, observation))

        engine._invalid_action(
            "bramble", attack, "agent attacks are illegal in Act I"
        )
        self.assertEqual(state["agents"]["bramble"]["guard"], 2)
        self.assertIn(
            ("invalid_action", -2),
            [(row["category"], row["points"]) for row in self.scores(engine, "bramble")],
        )

        state["round"] = 5
        state["act"] = rules.act_for_round(5)
        self.assertEqual(state["act"], 2)
        observation = self.observation(engine, "bramble")
        self.assertTrue(observation["public_state"]["agent_attacks_allowed"])
        self.assertTrue(self.has_action(observation, "attack", target="nix"))
        self.assertTrue(rules.is_legal(attack, observation))

        hp_before = state["agents"]["nix"]["hp"]
        engine._resolve_action("bramble", attack)
        self.assertLessEqual(state["agents"]["nix"]["hp"], hp_before)

    def test_act_boundaries(self):
        expected = [1, 1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 3]
        self.assertEqual(
            [rules.act_for_round(round_no) for round_no in range(1, 13)], expected
        )


# ---------------------------------------------------------------------------
# Contraction
# ---------------------------------------------------------------------------


class ContractionTests(RulesetTestCase):
    def test_contracting_flag_is_visible_for_the_full_round_before_sealing(self):
        engine = self.engine("warning.db")
        engine.state["round"] = 9
        engine._flag_contracting_rooms(9)
        self.assertEqual(engine.state["contraction"]["contracting"], ["threshold"])
        observation = self.observation(engine, "bramble")
        self.assertEqual(observation["map"]["contracting"], ["threshold"])
        self.assertTrue(observation["room"]["contracting"])
        self.assertEqual(observation["room"]["seals_at_end_of_round"], 9)
        self.assertEqual(observation["map"]["sealed"], [])

    def test_contraction_force_moves_agents_and_seals_the_room(self):
        engine = self.engine("contract.db")
        state = engine.state
        state["round"] = 9
        engine._flag_contracting_rooms(9)
        self.assertFalse(rules.vault_open(state))  # both seals still inactive
        engine._apply_contraction(9, "threshold")

        for agent in state["agents"].values():
            self.assertEqual(agent["room"], rules.VAULT_ROOM)
            self.assertIn(rules.VAULT_ROOM, agent["visited"])
        self.assertIn("threshold", state["contraction"]["sealed"])
        self.assertEqual(state["contraction"]["contracting"], [])
        self.assertTrue(rules.is_sealed(state, "threshold"))
        self.assertEqual(rules.open_neighbors(state, "ironwood_gate"), ["vault"])
        self.assertEqual(state["floor_items"]["threshold"], [])

        forced = self.events(engine, "agent_force_moved")
        self.assertEqual(len(forced), len(state["agents"]))
        self.assertTrue(all(event["payload"]["from"] == "threshold" for event in forced))
        self.assertTrue(all(event["payload"]["gate_bypassed"] for event in forced))
        self.assertTrue(self.events(engine, "room_sealed"))

        # A sealed room is listed but unreachable.
        observation = self.observation(engine, "bramble")
        rooms = {room["id"]: room for room in observation["map"]["rooms"]}
        self.assertIn("threshold", rooms)
        self.assertTrue(rooms["threshold"]["sealed"])
        self.assertEqual(rooms["threshold"]["neighbors"], [])
        self.assertFalse(
            any(
                entry["destination"] == "threshold"
                for entry in observation["legal_actions"]
                if entry["action"] == "move"
            )
        )

    def test_unlit_seal_is_voided_and_permanently_CLOSES_the_vault_gate(self):
        """A seal swallowed unlit scores nothing AND opens nothing.

        Previously ``voided`` counted as satisfying the gate, which let an agent
        reach the vault with only one seal — or none — ever ACTIVE, skipping the
        whole seal economy. The map rule is "both seals must be ACTIVE".
        """
        engine = self.engine("void.db")
        state = engine.state
        state["round"] = 10
        state["seals"]["ossuary_gate"] = "active"
        engine._apply_contraction(10, "ironwood_gate")
        self.assertEqual(state["seals"]["ironwood_gate"], "voided")
        self.assertFalse(rules.vault_open(state))
        self.assertTrue(rules.gate_permanently_closed(state))
        voided = self.events(engine, "seal_voided")
        self.assertEqual(voided[0]["payload"]["points"], 0)
        for agent_id in state["agents"]:
            self.assertNotIn(
                "seal_activated",
                [row["category"] for row in self.scores(engine, agent_id)],
            )
        self.assertEqual(self.events(engine, "vault_gate_opened"), [])
        closed = self.events(engine, "vault_gate_permanently_closed")
        self.assertEqual(closed[-1]["payload"]["reason"], "voided")
        self.assertFalse(closed[-1]["payload"]["vault_open"])

    def test_a_voided_seal_never_makes_move_vault_legal(self):
        """The predicate sweep the auditor ran, as an assertion."""
        cases = {
            ("active", "inactive"): False,
            ("inactive", "inactive"): False,
            ("active", "voided"): False,
            ("voided", "voided"): False,
            ("voided", "active"): False,
            ("active", "active"): True,
        }
        for (ironwood, ossuary), expected in cases.items():
            with self.subTest(seals=(ironwood, ossuary)):
                engine = self.engine(f"sweep-{ironwood}-{ossuary}.db")
                state = engine.state
                state["seals"]["ironwood_gate"] = ironwood
                state["seals"]["ossuary_gate"] = ossuary
                state["agents"]["bramble"]["room"] = "ironwood_gate"
                state["monsters"]["ironwood_guardian"]["hp"] = 0
                move = AgentAction(action="move", destination=rules.VAULT_ROOM)
                observation = self.observation(engine, "bramble")
                self.assertEqual(rules.vault_open(state), expected)
                self.assertEqual(
                    self.has_action(observation, "move", destination=rules.VAULT_ROOM),
                    expected,
                )
                self.assertEqual(rules.is_legal(move, observation), expected)

    def test_forced_relocation_into_the_vault_does_not_satisfy_the_gate(self):
        engine = self.engine("relocate.db")
        state = engine.state
        state["round"] = 9
        engine._flag_contracting_rooms(9)
        engine._apply_contraction(9, "threshold")

        # everyone is IN the vault, and the gate is still shut
        for agent in state["agents"].values():
            self.assertEqual(agent["room"], rules.VAULT_ROOM)
        self.assertFalse(rules.vault_open(state))
        forced = self.events(engine, "agent_force_moved")
        self.assertTrue(all(event["payload"]["gate_bypassed"] for event in forced))

        # stepping back out means you cannot voluntarily step back in — not even
        # after contraction has voided a seal on the way past.
        state["round"] = 10
        state["seals"]["ossuary_gate"] = "active"  # one seal lit, one about to die
        engine._apply_contraction(10, "ironwood_gate")
        self.assertEqual(state["seals"]["ironwood_gate"], "voided")
        state["agents"]["bramble"]["room"] = "ossuary_gate"
        state["monsters"]["ossuary_guardian"]["hp"] = 0
        observation = self.observation(engine, "bramble")
        self.assertFalse(
            self.has_action(observation, "move", destination=rules.VAULT_ROOM)
        )
        self.assertFalse(observation["public_state"]["vault_open"])
        self.assertTrue(
            observation["public_state"]["vault_gate_permanently_closed"],
            "the closed gate must be DISCLOSED, not silently unreachable",
        )

    def test_camping_through_contraction_never_opens_the_vault(self):
        """End-to-end: nobody lights a seal, everybody guards.

        The auditor's zero-seal exploit run — the vault gate must stay shut for
        the whole match and no agent may ever enter it by choice.
        """
        store = ArenaStore(self.root / "camper.db")
        self._stores.append(store)
        engine = ArenaEngine(store, GuardOnlyProvider(), parallel_agents=False)
        engine.run(self.manifests, 11)

        self.assertEqual(
            sorted(set(engine.state["seals"].values())), ["voided"]
        )
        self.assertFalse(rules.vault_open(engine.state))
        self.assertTrue(rules.gate_permanently_closed(engine.state))
        self.assertEqual(self.events(engine, "vault_gate_opened"), [])

        voluntary = [
            event
            for event in self.events(engine, "move")
            if event["payload"].get("to") == rules.VAULT_ROOM
        ]
        self.assertEqual(voluntary, [], "no voluntary entry without both seals")
        for agent in engine.state["agents"].values():
            self.assertEqual(agent["score_breakdown"].get("seal_activated", 0), 0)

    def test_living_guardian_is_entombed_not_relocated(self):
        engine = self.engine("entomb.db")
        state = engine.state
        state["round"] = 10
        engine._apply_contraction(10, "ironwood_gate")
        guardian = state["monsters"]["ironwood_guardian"]
        self.assertEqual(guardian["hp"], 0)
        self.assertEqual(guardian["death_cause"], "contraction")
        self.assertIsNone(guardian["defeated_by"])
        self.assertEqual(guardian["room"], "ironwood_gate")
        self.assertEqual(
            [m["id"] for m in rules.living_monsters_in(state, rules.VAULT_ROOM)],
            ["crown_warden"],
        )
        for agent_id in state["agents"]:
            self.assertNotIn(
                "guardian_finishing_blow",
                [row["category"] for row in self.scores(engine, agent_id)],
            )

    def test_contraction_relocates_floor_items_including_the_crown(self):
        engine = self.engine("relocate.db")
        state = engine.state
        state["round"] = 10
        state["monsters"]["crown_warden"]["hp"] = 0
        rules.crown_unlock(state, 6)
        rules.floor_remove(state, rules.VAULT_ROOM, CROWN)
        rules.floor_add(state, "ironwood_gate", CROWN)
        state["crown"]["room"] = "ironwood_gate"
        engine._apply_contraction(10, "ironwood_gate")
        self.assertEqual(state["floor_items"]["ironwood_gate"], [])
        self.assertIn(CROWN, state["floor_items"][rules.VAULT_ROOM])
        self.assertEqual(state["crown"]["room"], rules.VAULT_ROOM)
        self.assertEqual(state["crown"]["status"], "floor")
        relocated = self.events(engine, "floor_items_relocated")
        self.assertTrue(relocated[-1]["payload"]["crown_moved"])

    def test_force_move_is_not_a_transfer(self):
        engine = self.engine("forcemove.db")
        self.open_vault_state(engine, "bramble", 1)
        engine.state["agents"]["bramble"]["room"] = "threshold"
        engine.state["round"] = 9
        engine._apply_contraction(9, "threshold")
        crown = engine.state["crown"]
        self.assertEqual(crown["carrier_id"], "bramble")
        self.assertEqual(crown["status"], "carried")
        self.assertEqual(crown["attunement_rounds"], 1)
        self.assertEqual(engine.state["agents"]["bramble"]["room"], rules.VAULT_ROOM)

    def test_contraction_consumes_no_dice(self):
        engine = self.engine("nodice.db")
        engine.state["round"] = 9
        before = engine.rng.counter
        engine._flag_contracting_rooms(9)
        engine._apply_contraction(9, "threshold")
        self.assertEqual(engine.rng.counter, before)


# ---------------------------------------------------------------------------
# Combat: Wild Swing determinism and collateral scoring
# ---------------------------------------------------------------------------


class CombatTests(RulesetTestCase):
    @staticmethod
    def _roller(seed: int):
        rng = HashRNG(seed)
        calls: list[tuple[int, str]] = []

        def roll(sides: int, label: str) -> int:
            calls.append((sides, label))
            return rng.roll(sides, label)[0]

        return roll, calls

    @staticmethod
    def _scene():
        attacker = combat.Combatant(
            id="attacker",
            name="Attacker",
            kind="agent",
            room="ironwood_gate",
            hp=10,
            max_hp=10,
            power=0,
            armor=1,
            guard=0,
            inventory=("healing_tonic", "veteran_blade"),
            alive=True,
        )
        target = combat.Combatant(
            id="target",
            name="Target",
            kind="monster",
            room="ironwood_gate",
            hp=12,
            max_hp=12,
            power=3,
            armor=40,  # unhittable: forces the Wild Swing branch
            guard=0,
            inventory=(),
            alive=True,
        )
        bystander = combat.Combatant(
            id="bystander",
            name="Bystander",
            kind="agent",
            room="ironwood_gate",
            hp=9,
            max_hp=9,
            power=2,
            armor=1,
            guard=0,
            inventory=(),
            alive=True,
        )
        other = combat.Combatant(
            id="zed",
            name="Zed",
            kind="agent",
            room="ironwood_gate",
            hp=8,
            max_hp=8,
            power=2,
            armor=0,
            guard=0,
            inventory=(),
            alive=True,
        )
        return attacker, target, [attacker, bystander, other, target]

    def _resolve(self, seed: int, round_no: int = 5):
        attacker, target, occupants = self._scene()
        roll, calls = self._roller(seed)
        resolution = combat.resolve_attack(
            round_no=round_no,
            attacker=attacker,
            target=target,
            room_id="ironwood_gate",
            room_occupants=occupants,
            room_reaction_uses={},
            roll=roll,
        )
        return resolution, calls

    def test_wild_swing_table_partitions_the_die(self):
        seen: set[int] = set()
        for face in combat.WILD_SWING_TABLE:
            self.assertFalse(seen & set(face.faces))
            seen |= set(face.faces)
        self.assertEqual(seen, set(range(1, combat.WILD_SWING_DIE + 1)))
        combat.validate_tables()

    def test_wild_swing_is_deterministic_per_seed(self):
        for seed in (1, 42, 20260724):
            first, first_calls = self._resolve(seed)
            second, second_calls = self._resolve(seed)
            self.assertEqual(first.outcome, "miss")
            self.assertEqual(first_calls, second_calls)
            self.assertEqual(
                [effect.as_dict() for effect in first.effects],
                [effect.as_dict() for effect in second.effects],
            )
            self.assertEqual(first.as_dict(), second.as_dict())

    def test_wild_swing_rng_labels_and_order(self):
        resolution, calls = self._resolve(42)
        self.assertEqual(calls[0], (20, "tohit:r5:attacker:target"))
        self.assertEqual(calls[1], (6, "wildswing:r5:attacker:target"))
        if resolution.wild_swing.face.face_id == "bystander_wears_it":
            self.assertEqual(calls[2][1], "wildswing_bystander:r5:attacker:target")
        else:
            self.assertEqual(len(calls), 2)

    def test_wild_swing_faces_are_all_reachable_and_drop_is_deterministic(self):
        faces = set()
        for seed in range(60):
            resolution, _ = self._resolve(seed)
            faces.add(resolution.wild_swing.face.face_id)
            if resolution.wild_swing.face.face_id == "you_wear_it":
                drop = [
                    effect for effect in resolution.effects if effect.kind == "drop_item"
                ]
                # first item in the sorted inventory, always
                self.assertEqual(drop[0].item_id, "healing_tonic")
        self.assertEqual(
            faces, {"you_wear_it", "bystander_wears_it", "room_wears_it"}
        )

    def test_ironwood_and_ossuary_room_reactions_differ(self):
        ironwood = combat.ROOM_REACTIONS["ironwood_gate"]
        ossuary = combat.ROOM_REACTIONS["ossuary_gate"]
        self.assertNotEqual(ironwood.effect_kind, ossuary.effect_kind)
        self.assertNotEqual(ironwood.flavor, ossuary.flavor)

    def test_monsters_never_roll_wild_swing(self):
        monster = combat.Combatant(
            id="crown_warden",
            name="Crown Warden",
            kind="monster",
            room="vault",
            hp=20,
            max_hp=20,
            power=0,
            armor=2,
            guard=0,
            inventory=(),
            alive=True,
        )
        agent = combat.Combatant(
            id="bramble",
            name="Bramble",
            kind="agent",
            room="vault",
            hp=10,
            max_hp=10,
            power=2,
            armor=40,
            guard=0,
            inventory=(),
            alive=True,
        )
        roll, calls = self._roller(3)
        resolution = combat.resolve_attack(
            round_no=2,
            attacker=monster,
            target=agent,
            room_id="vault",
            room_occupants=[monster, agent],
            room_reaction_uses={},
            roll=roll,
        )
        self.assertEqual(resolution.outcome, "miss")
        self.assertIsNone(resolution.wild_swing)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1].startswith("tohit:"))

    def test_monster_target_is_lowest_hp(self):
        low = combat.Combatant(
            "low", "Low", "agent", "vault", 3, 10, 2, 1, 0, (), True
        )
        high = combat.Combatant(
            "high", "High", "agent", "vault", 9, 10, 2, 1, 0, (), True
        )
        monster = combat.Combatant(
            "crown_warden", "Warden", "monster", "vault", 20, 20, 4, 2, 0, (), True
        )
        roll, calls = self._roller(11)
        chosen = combat.choose_monster_target(
            round_no=4, monster=monster, candidates=[high, low], roll=roll
        )
        self.assertEqual(chosen, "low")
        self.assertEqual(calls, [])  # no tie, no roll consumed

    def test_collateral_kill_awards_no_elimination_points(self):
        engine = self.engine("collateral.db")
        state = engine.state
        state["round"] = 6
        state["act"] = 2
        for agent_id in ("bramble", "nix"):
            state["agents"][agent_id]["room"] = "ironwood_gate"
        state["agents"]["nix"]["hp"] = 2
        effect = combat.Effect(
            kind="damage",
            event_type="wild_swing_bystander",
            phase="referee",
            actor_id="bramble",
            target_id="nix",
            target_kind="agent",
            amount=combat.BYSTANDER_DAMAGE,
            room_id="ironwood_gate",
            collateral=True,
            credited_to=None,
            cause="wild_swing_bystander",
            accident=True,
            public_text="Bramble's wild swing catches Nix for 2.",
            payload={"face_id": "bystander_wears_it"},
        )
        engine._apply_effect(effect)

        self.assertEqual(state["agents"]["nix"]["status"], "eliminated")
        self.assertEqual(state["agents"]["bramble"]["score"], 0)
        self.assertEqual(state["agents"]["bramble"]["direct_eliminations"], [])
        self.assertEqual(state["agents"]["bramble"]["collateral_dealt"], 2)
        self.assertEqual(state["collateral_damage"]["total"], 2)
        self.assertEqual(state["collateral_damage"]["by_source"]["bramble"], 2)
        self.assertEqual(state["collateral_damage"]["by_victim"]["nix"], 2)
        self.assertEqual(self.scores(engine, "bramble"), [])
        eliminated = self.events(engine, "agent_eliminated")[-1]["payload"]
        self.assertTrue(eliminated["collateral"])
        self.assertTrue(eliminated["accident"])
        self.assertIsNone(eliminated["credited_to"])
        self.assertEqual(eliminated["scoring"]["points"], 0)

    def test_collateral_warden_kill_still_unlocks_the_crown_for_zero_points(self):
        engine = self.engine("collateral_warden.db")
        state = engine.state
        state["round"] = 6
        state["agents"]["bramble"]["room"] = rules.VAULT_ROOM
        state["monsters"]["crown_warden"]["hp"] = 2
        engine._apply_effect(
            combat.Effect(
                kind="damage",
                event_type="wild_swing_bystander",
                phase="referee",
                actor_id="bramble",
                target_id="crown_warden",
                target_kind="monster",
                amount=2,
                room_id=rules.VAULT_ROOM,
                collateral=True,
                credited_to=None,
                cause="wild_swing_bystander",
                accident=True,
                public_text="A wild swing catches the Warden.",
            )
        )
        self.assertEqual(state["crown"]["status"], "floor")
        self.assertIn(CROWN, state["floor_items"][rules.VAULT_ROOM])
        self.assertEqual(state["monsters"]["crown_warden"]["death_cause"], "collateral")
        self.assertEqual(
            [row["category"] for row in self.scores(engine, "bramble")], []
        )
        defeated = self.events(engine, "monster_defeated")[-1]["payload"]
        self.assertEqual(defeated["scoring"]["points"], 0)
        self.assertTrue(defeated["collateral"])
        unlocked = self.events(engine, "crown_unlocked")[-1]["payload"]
        self.assertTrue(unlocked["collateral"])

    def test_direct_elimination_pays_once_per_victim(self):
        engine = self.engine("noFarm.db")
        state = engine.state
        state["round"] = 6
        killer = state["agents"]["bramble"]
        self.assertEqual(scoring.register_direct_elimination(killer, "nix"), 2)
        self.assertEqual(scoring.register_direct_elimination(killer, "nix"), 0)
        self.assertEqual(killer["direct_eliminations"], ["nix"])

    def test_monster_hit_points_cap_at_three_per_round(self):
        engine = self.engine("cap.db")
        agent = engine.state["agents"]["bramble"]
        awarded = [scoring.register_monster_hit(agent) for _ in range(4)]
        self.assertEqual(awarded, [1, 1, 1, 0])
        scoring.reset_round_counters(agent)
        self.assertEqual(scoring.register_monster_hit(agent), 1)


# ---------------------------------------------------------------------------
# Observation: privacy and disclosure
# ---------------------------------------------------------------------------


class ObservationTests(RulesetTestCase):
    def test_observation_never_leaks_another_agents_private_data(self):
        engine = self.engine("privacy.db")
        state = engine.state
        state["agents"]["nix"]["memory"] = ["NIX-PRIVATE-SCRATCH-4242"]
        state["agents"]["nix"]["tokens_remaining"] = 12_345
        observation = self.observation(engine, "bramble")
        blob = canonical_json(observation)

        self.assertNotIn("NIX-PRIVATE-SCRATCH-4242", blob)
        self.assertNotIn("12345", blob)
        nix = engine.manifests["nix"]
        self.assertNotIn(nix.system_prompt, blob)
        self.assertNotIn(nix.strategy, blob)
        self.assertNotIn(nix.personality, blob)
        self.assertNotIn("created_at", blob)

        self.assertTrue(observation["visible_agents"])
        for other in observation["visible_agents"]:
            for forbidden in (
                "secret_objective",
                "score_breakdown",
                "tokens_remaining",
                "scratch_memory",
                "episodic_memory",
                "memory",
            ):
                self.assertNotIn(forbidden, other)
        # own secret objective is present for the owning agent only
        self.assertEqual(
            observation["secret_objective"]["id"],
            engine.manifests["bramble"].secret_objective,
        )

    def test_items_are_self_describing_everywhere(self):
        engine = self.engine("itemviews.db")
        state = engine.state
        rules.inventory_add(state, "bramble", "veteran_blade")
        rules.inventory_add(state, "nix", "healing_tonic")
        rules.floor_add(state, "threshold", "healing_tonic")
        observation = self.observation(engine, "bramble")

        piles = [observation["you"]["inventory"], observation["room"]["floor_items"]]
        piles.extend(other["inventory"] for other in observation["visible_agents"])
        self.assertTrue(any(piles))
        for pile in piles:
            for view in pile:
                self.assertIsInstance(view, dict)
                self.assertEqual(
                    set(view), {"id", "name", "effect", "consumed_on_use"}
                )
                self.assertIn(view["id"], items.ITEM_REGISTRY)

    def test_every_mechanical_item_hook_is_disclosed(self):
        engine = self.engine("disclosure.db")
        state = engine.state
        for item_id, definition in sorted(items.ITEM_REGISTRY.items()):
            state["agents"]["bramble"]["inventory"] = [item_id]
            observation = self.observation(engine, "bramble")
            me = observation["you"]
            effects = me["active_effects"]

            power_deltas = sum(e["delta"] for e in effects if e["stat"] == "power")
            armor_deltas = sum(e["delta"] for e in effects if e["stat"] == "armor")
            self.assertEqual(me["power_effective"], me["power_base"] + power_deltas)
            self.assertEqual(me["armor_effective"], me["armor_base"] + armor_deltas)

            if definition.passive_power:
                match = [
                    e
                    for e in effects
                    if e["source_id"] == item_id and e["stat"] == "power"
                ]
                self.assertEqual(len(match), 1, f"{item_id} power not disclosed")
                self.assertEqual(match[0]["delta"], definition.passive_power)
            if definition.passive_armor:
                match = [
                    e
                    for e in effects
                    if e["source_id"] == item_id and e["stat"] == "armor"
                ]
                self.assertEqual(len(match), 1, f"{item_id} armor not disclosed")
            if definition.heal:
                self.assertIn(str(definition.heal), definition.effect)
            if definition.consumed_on_use:
                self.assertIn("onsumed", definition.effect)
            if definition.is_crown:
                self.assertIn("attunement", definition.effect.lower())

            view = observation["you"]["inventory"][0]
            self.assertEqual(view["effect"], definition.effect)
            self.assertEqual(view["consumed_on_use"], definition.consumed_on_use)

    def test_effective_power_matches_the_resolver(self):
        engine = self.engine("power.db")
        state = engine.state
        rules.inventory_add(state, "bramble", "veteran_blade")
        rules.inventory_add(state, "bramble", "veteran_blade")  # does not stack
        observation = self.observation(engine, "bramble")
        agent = state["agents"]["bramble"]
        effective, _ = combat.effective_power(agent["power"], agent["inventory"])
        self.assertEqual(observation["you"]["power_effective"], effective)
        self.assertEqual(effective, agent["power"] + 1)

    def test_legal_actions_always_contain_guard_and_are_authoritative(self):
        engine = self.engine("legal.db")
        observation = self.observation(engine, "bramble")
        self.assertTrue(observation["legal_actions"])
        self.assertTrue(self.has_action(observation, "guard"))
        for entry in observation["legal_actions"]:
            self.assertTrue(
                rules.is_legal(
                    AgentAction(
                        action=entry["action"],
                        target=entry["target"],
                        destination=entry["destination"],
                        item=entry["item"],
                    ),
                    observation,
                )
            )
        self.assertFalse(
            rules.is_legal(AgentAction(action="use", item=CROWN), observation)
        )
        self.assertFalse(
            rules.is_legal(
                AgentAction(action="move", destination="nowhere"), observation
            )
        )


if __name__ == "__main__":
    unittest.main()
