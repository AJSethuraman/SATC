"""The second choice (PRD §5.42, ruled 18 Sep 2026, docket D11: "B: a second
choice"): everyone still commits blind at once; a brain may give a fallback of
the five action slots; the referee applies it only when the first choice is
stale at resolution; a stale second is a stale turn; there is no third; the
stale event says which choice it was and what follows.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.models import ACTION_SCHEMA_VERSION, AgentAction, SecondChoice, ValidationError, action_json_schema
from arena.providers import MockDecisionProvider, ProviderResult
from arena.storage import ArenaStore

CONTESTED = (2, 0)   # a Threshold floor tile every scout, mystic and scoundrel can reach from its spawn


def _raw(action: str, *, tile=None, target=None, item=None, fallback=None, note="a plan") -> str:
    return json.dumps({
        "action": action, "target": target, "destination": None, "item": item,
        "tile": list(tile) if tile else None,
        "speech": {"mode": "silent", "to": None, "text": ""},
        "note": {"objective": note, "reads": []},
        "deal": None,
        "fallback": fallback,
    })


class RaceForOneTile(MockDecisionProvider):
    """Round 1: everyone who can step onto the contested tile does, with a
    second choice; the rest guard. Later rounds: guard, so the round loop has
    nothing else to resolve."""

    def __init__(self, second):
        self.second = second   # a dict for the fallback, or None

    def decide(self, manifest, prompt, observation):
        legal = observation["legal_actions"]
        # the match is one round long; whoever can reach the tile goes for it
        step = next((e for e in legal if e["action"] == "step" and tuple(e.get("tile") or ()) == CONTESTED), None)
        if step:
            return ProviderResult(_raw("step", tile=CONTESTED, fallback=self.second), 10, 20, "test", "race")
        return ProviderResult(_raw("guard"), 10, 20, "test", "race")


GUARD = {"action": "guard", "target": None, "destination": None, "item": None, "tile": None}


class SecondChoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifests = load_manifests()

    def tearDown(self):
        self.temp.cleanup()

    def run_match(self, provider, rounds=1):
        store = ArenaStore(self.root / "m.db")
        engine = ArenaEngine(store, provider, max_rounds=rounds, parallel_agents=False)
        match_id = engine.run(self.manifests, seed=7)
        bundle = store.replay_bundle(match_id)
        store.close()
        return [e for e in sorted(bundle["events"], key=lambda e: e["seq"]) if e["round_no"] == 1], bundle

    # ---- the contract ----------------------------------------------------

    def test_the_contract_carries_a_second_choice_and_its_schema_is_pinned(self):
        self.assertEqual(ACTION_SCHEMA_VERSION, "agent-action-1.1")
        a = AgentAction.from_dict(json.loads(_raw("take", item="ember_crown", fallback=GUARD)))
        self.assertEqual(a.fallback, SecondChoice(action="guard"))
        self.assertEqual(a.as_dict()["fallback"], GUARD)
        self.assertEqual(a.second().action, "guard")
        self.assertEqual(a.second().speech.mode, "silent")
        self.assertEqual(a.second().note, a.note)
        self.assertIsNone(AgentAction.from_dict(json.loads(_raw("guard"))).fallback)
        schema = action_json_schema()
        self.assertIn("fallback", schema["required"])
        self.assertEqual(schema["properties"]["fallback"]["type"], ["object", "null"])
        self.assertEqual(sorted(schema["properties"]["fallback"]["properties"]), ["action", "destination", "item", "target", "tile"])

    def test_a_malformed_second_choice_is_refused_by_name(self):
        for bad, message in (
            ({"action": "fly"}, "fallback.action"),
            ({"action": "guard", "speech": {"mode": "say"}}, "unknown fallback fields"),
            ({"action": "step", "tile": [1]}, "fallback.tile"),
            ("guard", "fallback must be an object"),
        ):
            with self.assertRaises(ValidationError) as ctx:
                AgentAction.from_dict(json.loads(_raw("guard", fallback=bad)))
            self.assertIn(message, str(ctx.exception), bad)

    # ---- the referee -----------------------------------------------------

    def test_the_second_choice_resolves_when_the_first_is_stale_and_never_otherwise(self):
        events, bundle = self.run_match(RaceForOneTile(GUARD))
        steps = [e for e in events if e["event_type"] == "step" and e["payload"]["changes"]["tile"][1] == list(CONTESTED)]
        stale = [e for e in events if e["event_type"] == "stale_action"]
        self.assertEqual(len(steps), 1, "exactly one body reaches the tile")
        self.assertGreaterEqual(len(stale), 2, "the rest arrive to find it taken")
        winner = steps[0]["actor_id"]
        for e in stale:
            self.assertNotEqual(e["actor_id"], winner)
            self.assertEqual(e["payload"]["choice"], "first")
            self.assertEqual(e["payload"]["referee_decision"], "second_choice_follows")
            self.assertEqual(e["payload"]["second_choice"], GUARD)
            self.assertIn("the second choice follows", e["public_text"])
            self.assertEqual(e["payload"]["points"], 0)
            # the very next thing that happens to this character in the round is the guard
            after = [x for x in events if x["seq"] > e["seq"] and x["actor_id"] == e["actor_id"]]
            self.assertTrue(after and after[0]["event_type"] == "guard", after[:1])
        # the one who got there first spent no second choice
        self.assertFalse([e for e in events if e["event_type"] == "guard" and e["actor_id"] == winner])
        # never a penalty, and the decision record carries the second choice for the replay
        self.assertFalse([e for e in events if e["event_type"] == "invalid_action_fallback"])
        racers = {d["agent_id"] for d in bundle["decisions"] if d["round_no"] == 1 and d["action"]["action"] == "step"}
        for d in bundle["decisions"]:
            if d["round_no"] == 1 and d["agent_id"] in racers:
                self.assertEqual(d["action"]["fallback"], GUARD)

    def test_a_stale_second_choice_is_a_stale_turn_and_there_is_no_third(self):
        again = {"action": "step", "target": None, "destination": None, "item": None, "tile": list(CONTESTED)}
        events, _ = self.run_match(RaceForOneTile(again))
        stale = [e for e in events if e["event_type"] == "stale_action"]
        firsts = [e for e in stale if e["payload"]["choice"] == "first"]
        seconds = [e for e in stale if e["payload"]["choice"] == "second"]
        self.assertTrue(firsts)
        self.assertEqual(len(seconds), len(firsts), "each stale first is followed by exactly one stale second")
        for e in seconds:
            self.assertEqual(e["payload"]["referee_decision"], "no_effect_no_penalty")
            self.assertIn("either", e["public_text"])
            self.assertIsNone(e["payload"]["second_choice"])
        # no third: nobody gets a guard or any other action after their stale second
        acted = {"guard", "step", "move", "attack_hit", "attack_miss", "stale_action", "rest", "search_failure",
                 "cache_found", "seal_activated", "item_taken", "item_used", "invalid_action_fallback"}
        for e in seconds:
            after = [x for x in events if x["seq"] > e["seq"] and x["actor_id"] == e["actor_id"] and x["event_type"] in acted]
            self.assertFalse(after, after[:1])
        self.assertFalse([e for e in events if e["event_type"] == "invalid_action_fallback"])

    def test_a_second_choice_that_was_not_legal_at_the_freeze_is_ignored_without_penalty(self):
        illegal = {"action": "attack", "target": "crown_warden", "destination": None, "item": None, "tile": None}
        events, _ = self.run_match(RaceForOneTile(illegal))
        stale = [e for e in events if e["event_type"] == "stale_action"]
        self.assertTrue(stale)
        for e in stale:
            self.assertEqual(e["payload"]["choice"], "first")
            self.assertEqual(e["payload"]["referee_decision"], "no_effect_no_penalty")
            self.assertIsNone(e["payload"]["second_choice"])
            self.assertIn("never legal", e["public_text"])
        self.assertFalse([e for e in events if e["event_type"] in ("attack_hit", "attack_miss", "invalid_action_fallback")])

    def test_without_a_second_choice_nothing_changes(self):
        events, _ = self.run_match(RaceForOneTile(None))
        stale = [e for e in events if e["event_type"] == "stale_action"]
        self.assertTrue(stale)
        for e in stale:
            self.assertEqual(e["public_text"].split("'s ")[1], "action finds nothing there.")
            self.assertEqual(e["payload"]["referee_decision"], "no_effect_no_penalty")
            self.assertIsNone(e["payload"]["second_choice"])

    def test_the_mock_gives_a_second_choice_for_anything_a_rival_can_reach_first(self):
        store = ArenaStore(self.root / "mock.db")
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=True)
        match_id = engine.run(self.manifests, seed=52)
        bundle = store.replay_bundle(match_id)
        store.close()
        contested = [d for d in bundle["decisions"] if d["action"]["action"] in ("take", "interact", "attack", "step", "search")]
        self.assertTrue(contested)
        self.assertTrue(all(d["action"]["fallback"] == GUARD for d in contested))
        self.assertTrue(all(d["action"]["fallback"] is None for d in bundle["decisions"] if d["action"]["action"] in ("guard", "rest", "move")))
        followed = [e for e in bundle["events"] if e["event_type"] == "stale_action" and e["payload"]["referee_decision"] == "second_choice_follows"]
        self.assertTrue(followed, "the mock match has collisions, and each now gets its second choice")


if __name__ == "__main__":
    unittest.main()
