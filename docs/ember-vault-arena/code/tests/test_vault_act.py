"""The Vault opens only in the last act (ruleset 0.5, PRD §5.4 "one
convergent terminal objective in act IV", built 19 Sep 2026): both seals lit
is the key and act IV is the hour. Lit before then, the seals arm the gate
and the referee says when it opens; lit in act IV, it opens at once."""
from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from arena import rules
from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.models import AgentAction
from arena.providers import MockDecisionProvider
from arena.rng import HashRNG
from arena.storage import ArenaStore


class VaultActTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifests = load_manifests()
        self._stores = []

    def tearDown(self):
        for s in self._stores:
            s.close()
        self.temp.cleanup()

    def engine(self, name="v.db", round_no=1):
        store = ArenaStore(self.root / name)
        self._stores.append(store)
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=False)
        engine.match_id = "unit"
        engine.manifests = {m.id: m for m in self.manifests}
        engine.state = rules.new_match_state(self.manifests, 5)
        engine.state["status"] = "running"
        engine.state["round"] = round_no
        engine.state["act"] = rules.act_for_round(round_no)
        engine.rng = HashRNG(5)
        return engine

    def events(self, engine, kind):
        return [e for e in engine.store.events_for_match(engine.match_id) if e["event_type"] == kind]

    def test_both_seals_lit_in_act_ii_arm_the_gate_and_it_opens_when_act_iv_begins(self):
        engine = self.engine(round_no=rules.ACT_I_LAST_ROUND + 2)
        state = engine.state
        state["seals"]["ironwood_gate"] = "active"
        state["monsters"]["ossuary_guardian"]["hp"] = 0
        state["agents"]["bramble"]["room"] = "ossuary_gate"
        engine._resolve_action("bramble", AgentAction(action="interact", target="ossuary_seal"))
        self.assertTrue(rules.seals_lit(state))
        self.assertFalse(rules.vault_open(state))
        self.assertEqual(self.events(engine, "vault_gate_opened"), [])
        lit = self.events(engine, "seals_lit")
        self.assertEqual(len(lit), 1)
        self.assertEqual(lit[0]["payload"]["opens_at_round"], rules.ACT_III_LAST_ROUND + 1)
        obs = rules.visible_observation(deepcopy(state), "bramble", "lorekeeper", [])
        self.assertTrue(obs["public_state"]["seals_lit"])
        self.assertFalse(obs["public_state"]["vault_open"])
        self.assertEqual(obs["public_state"]["vault_opens_at_round"], rules.ACT_III_LAST_ROUND + 1)
        self.assertFalse(any(e["action"] == "move" and e["destination"] == rules.VAULT_ROOM for e in obs["legal_actions"]))
        # acts II and III: shut; the first round of act IV: open, and the referee says so
        for round_no in (rules.ACT_II_LAST_ROUND, rules.ACT_III_LAST_ROUND):
            state["round"] = round_no
            self.assertFalse(rules.vault_open(state), round_no)
        state["round"] = rules.ACT_III_LAST_ROUND + 1
        engine._apply_act_transition(state["round"])
        self.assertTrue(rules.vault_open(state))
        opened = self.events(engine, "vault_gate_opened")
        self.assertEqual(len(opened), 1)
        self.assertEqual(opened[0]["payload"]["reason"], "last_act_with_seals_lit")
        obs = rules.visible_observation(deepcopy(state), "bramble", "lorekeeper", [])
        self.assertTrue(any(e["action"] == "move" and e["destination"] == rules.VAULT_ROOM for e in obs["legal_actions"]))

    def test_the_second_seal_lit_in_act_iv_opens_the_vault_at_once(self):
        engine = self.engine(name="late.db", round_no=rules.ACT_III_LAST_ROUND + 3)
        state = engine.state
        engine._apply_act_transition(state["round"])
        self.assertEqual(self.events(engine, "vault_gate_opened"), [])  # one seal still cold
        state["seals"]["ironwood_gate"] = "active"
        state["monsters"]["ossuary_guardian"]["hp"] = 0
        state["agents"]["nix"]["room"] = "ossuary_gate"
        engine._resolve_action("nix", AgentAction(action="interact", target="ossuary_seal"))
        self.assertTrue(rules.vault_open(state))
        opened = self.events(engine, "vault_gate_opened")
        self.assertEqual([e["payload"]["reason"] for e in opened], ["seals_active"])
        self.assertEqual(self.events(engine, "seals_lit"), [])

    def test_a_whole_mock_match_keeps_the_warden_alive_into_act_iv(self):
        store = ArenaStore(self.root / "whole.db")
        self._stores.append(store)
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=True)
        match_id = engine.run(self.manifests, seed=52)
        bundle = store.replay_bundle(match_id)
        warden_fell = next((e["round_no"] for e in bundle["events"] if e["event_type"] == "monster_defeated" and e.get("target_id") == "crown_warden"), None)
        self.assertTrue(warden_fell is None or warden_fell > rules.ACT_III_LAST_ROUND, warden_fell)
        first_open = next((e["round_no"] for e in bundle["events"] if e["event_type"] == "vault_gate_opened"), None)
        self.assertIsNotNone(first_open)
        self.assertGreaterEqual(first_open, rules.ACT_III_LAST_ROUND + 1)
        moved_in = [e["round_no"] for e in bundle["events"] if e["event_type"] == "move" and e.get("target_id") == rules.VAULT_ROOM]
        self.assertTrue(moved_in)
        self.assertTrue(all(r > rules.ACT_III_LAST_ROUND for r in moved_in), moved_in[:5])


if __name__ == "__main__":
    unittest.main()
