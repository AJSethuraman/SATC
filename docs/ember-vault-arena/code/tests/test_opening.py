"""The narrator's opening (PRD §5.26, asked by the firm 14 Sep 2026: "the
opening should explain rules and such and the characters (like our NPCs)").

Before round 1 the narrator sets the scene from a facts packet the referee
publishes: rooms, guardians and the Warden, the rules that will matter, the
contestants by name and build. Nothing secret is in the packet. A check
refuses an opening that is empty, too long, names a secret aim, or never
mentions the Crown or a room, and the deterministic template stands in.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.providers import MockDecisionProvider, ProviderResult, compile_opening_prompt, opening_template
from arena.storage import ArenaStore


class BadOpeningProvider(MockDecisionProvider):
    def __init__(self, text):
        self.text = text

    def narrate(self, round_no, prompt, event_lines):
        if prompt.get("kind") == "opening":
            return ProviderResult(self.text, 10, 20, "test", "bad-opening")
        return super().narrate(round_no, prompt, event_lines)


class OpeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifests = load_manifests()

    def tearDown(self):
        self.temp.cleanup()

    def run_match(self, provider, name="m.db"):
        store = ArenaStore(self.root / name)
        engine = ArenaEngine(store, provider, max_rounds=2, parallel_agents=False)
        match_id = engine.run(self.manifests, seed=5)
        bundle = store.replay_bundle(match_id)
        audit = store.audit_for_match(match_id) if hasattr(store, "audit_for_match") else None
        store.close()
        return engine, bundle, audit

    def test_the_opening_comes_before_round_1_and_names_the_world_and_the_eight(self):
        engine, bundle, _ = self.run_match(MockDecisionProvider())
        events = sorted(bundle["events"], key=lambda e: e["seq"])
        kinds = [e["event_type"] for e in events]
        self.assertIn("match_opening", kinds)
        self.assertLess(kinds.index("match_started"), kinds.index("match_opening"))
        self.assertLess(kinds.index("match_opening"), kinds.index("round_started"))
        opening = next(e for e in events if e["event_type"] == "match_opening")
        self.assertEqual(opening["round_no"], 0)
        text = opening["public_text"]
        state = bundle["snapshots"][0]["state"]
        for a in state["agents"].values():
            self.assertIn(a["name"], text)
            self.assertIn(a["build"], text)
        for r in state["rooms"].values():
            self.assertIn(r["name"], text)
        for m in state["monsters"].values():
            self.assertIn(m["name"], text)
        self.assertIn(str(engine.max_rounds), text)
        self.assertIn("Crown", text)
        self.assertIsNone(opening["payload"]["fallback_reason"])
        # nothing secret reaches the narrator or the audience
        facts = opening["payload"]["facts"]
        for m in self.manifests:
            self.assertNotIn(m.secret_objective.replace("_", " "), text.lower())
            self.assertNotIn(m.wants[:40], text)
        self.assertNotIn("secret", str(facts).lower())
        self.assertEqual([c["name"] for c in facts["contestants"]], [state["agents"][k]["name"] for k in sorted(state["agents"])])

    def test_the_check_refuses_by_reason_and_the_template_stands_in(self):
        from arena.rules import new_match_state
        store = ArenaStore(self.root / "facts.db")
        engine = ArenaEngine(store, MockDecisionProvider(), max_rounds=1, parallel_agents=False)
        engine.state = new_match_state(self.manifests, 5, 1)
        facts = engine.opening_facts()
        store.close()
        self.assertIsNone(ArenaEngine.validate_opening(opening_template(facts), facts))
        self.assertEqual(ArenaEngine.validate_opening("", facts), "empty opening")
        self.assertIn("1,600", ArenaEngine.validate_opening("x" * 1_601, facts))
        self.assertIn("secret aim", ArenaEngine.validate_opening("The Crown waits in The Threshold; Fen is a treasure hoarder.", facts))
        self.assertIn("Crown", ArenaEngine.validate_opening("The Threshold is wet.", facts))
        self.assertIn("room", ArenaEngine.validate_opening("The Crown waits.", facts))
        for bad in ("", "Fen is a lorekeeper and the Crown sits in The Ember Vault.", "The Crown."):
            _, bundle, _ = self.run_match(BadOpeningProvider(bad), name=f"bad-{len(bad)}.db")
            opening = next(e for e in bundle["events"] if e["event_type"] == "match_opening")
            self.assertEqual(opening["public_text"], opening_template(opening["payload"]["facts"]))
            self.assertTrue(opening["payload"]["fallback_reason"], bad)

    def test_the_prompt_carries_the_facts_and_nothing_else(self):
        facts = {"contestants": [{"name": "A", "build": "scout", "hp": 11}], "rooms": [], "closes": [], "rules": [], "max_rounds": 3, "monsters": []}
        prompt = compile_opening_prompt(facts)
        self.assertEqual(prompt["kind"], "opening")
        self.assertEqual(prompt["facts"], facts)
        self.assertEqual(len(prompt["messages"]), 2)
        self.assertIn("never guess at what any contestant wants", prompt["messages"][0]["content"])
        self.assertIn('"kind":"opening"', prompt["messages"][1]["content"].replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
