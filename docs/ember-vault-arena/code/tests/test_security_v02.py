from __future__ import annotations

"""Adversarial regression tests for the v0.2 audit findings.

Every test here failed before its fix and passes after. They are written from
the ATTACKER's side: a hostile provider that edits what the referee handed it, a
rival polling the public HTTP surface mid-match, and a camper trying to reach
the vault without ever lighting a seal.
"""

import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from typing import Any

from arena import rules
from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.models import AgentManifest, ProviderResult
from arena.providers import MockDecisionProvider
from arena.server import ArenaHTTPServer
from arena.storage import ArenaStore


# ---------------------------------------------------------------------------
# [1] the provider must not be able to forge its own legality oracle
# ---------------------------------------------------------------------------


class ForgedLegalActionProvider(MockDecisionProvider):
    """Mutates the observation it is handed, in place, then acts on the forgery.

    This is the exact exploit the auditor demonstrated: append a move the
    referee never offered to ``observation['legal_actions']`` and then return
    it. If the referee re-reads that list to judge legality, the move lands.
    """

    def __init__(self, agent_id: str, forged: dict[str, Any]):
        self.agent_id = agent_id
        self.forged = forged
        self.saw_legal_action_count = 0
        self.mutated_manifest_ids: list[str] = []
        self.manifest_writes_rejected: list[str] = []

    def decide(
        self,
        manifest: AgentManifest,
        prompt: dict[str, Any],
        observation: dict[str, Any],
    ) -> ProviderResult:
        if manifest.id != self.agent_id:
            return super().decide(manifest, prompt, observation)
        entry = dict(self.forged)
        entry.setdefault("label", "forged")
        observation["legal_actions"].append(entry)
        self.saw_legal_action_count = len(observation["legal_actions"])
        # also try to rewrite the world the referee scores against
        observation["public_state"]["seals"] = {
            "ironwood_gate": "active",
            "ossuary_gate": "active",
        }
        try:
            manifest.secret_objective = "PWNED"
        except Exception:  # frozen dataclass — the write bounces
            self.manifest_writes_rejected.append(manifest.id)
        else:
            self.mutated_manifest_ids.append(manifest.id)
        return ProviderResult(
            raw_output=json.dumps(
                {
                    "action": self.forged["action"],
                    "target": self.forged.get("target"),
                    "destination": self.forged.get("destination"),
                    "item": self.forged.get("item"),
                    "speech": "",
                    "reasoning_summary": "forged",
                    "memory_write": "forged",
                }
            ),
            input_tokens=10,
            output_tokens=10,
            provider="test-hostile",
            model="forger",
        )


class ProviderSeamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifests = load_manifests()
        self._stores: list[ArenaStore] = []

    def tearDown(self):
        for store in self._stores:
            store.close()
        self.temp.cleanup()

    def engine(self, provider, name="sec.db", seed=7) -> ArenaEngine:
        store = ArenaStore(self.root / name)
        self._stores.append(store)
        engine = ArenaEngine(store, provider, parallel_agents=False)
        return engine

    def events(self, engine: ArenaEngine, event_type: str) -> list[dict]:
        with engine.store.lock:
            rows = engine.store.conn.execute(
                "SELECT * FROM events WHERE match_id=? AND event_type=? ORDER BY seq",
                (engine.match_id, event_type),
            ).fetchall()
        return [
            {**dict(row), "payload": json.loads(row["payload_json"])} for row in rows
        ]

    def test_provider_cannot_forge_a_legal_action_by_mutating_the_observation(self):
        victim = self.manifests[0].id
        provider = ForgedLegalActionProvider(
            victim, {"action": "move", "destination": rules.VAULT_ROOM}
        )
        engine = self.engine(provider, "forge.db")
        engine.max_rounds = 2
        engine.run(self.manifests, 4242)

        # the exploit ran at all
        self.assertGreater(provider.saw_legal_action_count, 0)

        moves = [
            event
            for event in self.events(engine, "move")
            if event["actor_id"] == victim
        ]
        self.assertEqual(
            [event["payload"].get("to") for event in moves],
            [],
            "forged move must never resolve",
        )
        self.assertEqual(engine.state["seals"]["ironwood_gate"], "inactive")
        self.assertEqual(engine.state["seals"]["ossuary_gate"], "inactive")
        self.assertNotEqual(engine.state["agents"][victim]["room"], rules.VAULT_ROOM)

        rejected = [
            event
            for event in self.events(engine, "invalid_action_fallback")
            if event["actor_id"] == victim
        ]
        self.assertTrue(rejected, "forged action must be penalised, not silently kept")
        self.assertGreater(engine.state["agents"][victim]["invalid_actions"], 0)
        self.assertLessEqual(
            engine.state["agents"][victim]["score_breakdown"].get("invalid_action", 0),
            -2,
        )

    def test_provider_mutations_do_not_touch_the_referee_copies(self):
        victim = self.manifests[0].id
        provider = ForgedLegalActionProvider(
            victim, {"action": "move", "destination": rules.VAULT_ROOM}
        )
        engine = self.engine(provider, "copies.db")
        engine.max_rounds = 1
        engine.run(self.manifests, 99)

        # either the write bounced off the frozen dataclass or it hit a copy;
        # what matters is the referee's own manifest never changed.
        self.assertTrue(
            provider.manifest_writes_rejected or provider.mutated_manifest_ids
        )
        self.assertNotEqual(engine.manifests[victim].secret_objective, "PWNED")
        self.assertEqual(
            engine.manifests[victim].secret_objective,
            {m.id: m.secret_objective for m in self.manifests}[victim],
        )

    def test_legality_oracle_is_captured_before_the_provider_runs(self):
        """Even a hand-built FrozenDecision cannot smuggle an action in through
        the observation dict: only ``legal_keys`` is consulted."""
        from arena.engine import FrozenDecision
        from arena.models import AgentAction

        action = AgentAction(action="move", destination=rules.VAULT_ROOM)
        decision = FrozenDecision(
            action=action,
            observation={
                "legal_actions": [
                    {
                        "action": "move",
                        "destination": rules.VAULT_ROOM,
                        "target": None,
                        "item": None,
                    }
                ]
            },
            legal_keys=frozenset({rules.action_key({"action": "guard"})}),
            legal_actions_hash="x",
            validity="valid",
            fallback_reason=None,
        )
        self.assertFalse(ArenaEngine._legal_in_frozen_decision(decision))


# ---------------------------------------------------------------------------
# [2] + [3] + [4] the public read surface
# ---------------------------------------------------------------------------

SECRET_MARKERS = (
    "SECRET-SYSPROMPT",
    "SECRET-STRATEGY",
)


def _secret_manifests() -> list[AgentManifest]:
    out = []
    for index, base in enumerate(load_manifests()):
        out.append(
            AgentManifest(
                id=base.id,
                name=base.name,
                system_prompt=f"SECRET-SYSPROMPT-{index} {base.system_prompt}",
                personality=base.personality,
                strategy=f"SECRET-STRATEGY-{index} {base.strategy}",
                build=base.build,
                secret_objective=base.secret_objective,
            )
        )
    return out


def _walk(node: Any, path: str = "$"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")
    else:
        yield path, node


class PublicSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifests = _secret_manifests()
        self.store = ArenaStore(self.root / "public.db")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    # -- [2] roster ------------------------------------------------------

    def test_list_agents_never_publishes_prompts_strategies_or_objectives(self):
        for manifest in self.manifests:
            self.store.register_agent(manifest)
        rows = self.store.list_agents()
        self.assertEqual(len(rows), len(self.manifests))
        blob = json.dumps(rows)
        for marker in SECRET_MARKERS:
            self.assertNotIn(marker, blob)
        self.assertNotIn("secret_objective", blob)
        for row in rows:
            self.assertEqual(
                sorted(row["manifest"].keys()),
                ["build", "id", "name", "personality"],
            )
            # the picker still has what it needs
            self.assertTrue(row["id"] and row["name"] and row["manifest"]["build"])

    def test_agents_endpoint_matches_the_projection(self):
        for manifest in self.manifests:
            self.store.register_agent(manifest)
        with _serve(self.store) as base:
            payload = _get(f"{base}/api/agents")
        blob = json.dumps(payload)
        for marker in SECRET_MARKERS:
            self.assertNotIn(marker, blob)
        self.assertNotIn("secret_objective", blob)
        self.assertNotIn("system_prompt", blob)
        self.assertNotIn("strategy", blob)

    # -- [3] + [4] mid-match replay --------------------------------------

    def _run_match(self, seed=777777, rounds=3) -> str:
        engine = ArenaEngine(
            self.store, MockDecisionProvider(), max_rounds=rounds, parallel_agents=False
        )
        match_id = engine.run(self.manifests, seed)
        # rewind status so the bundle is judged as an in-flight match
        with self.store.lock:
            self.store.conn.execute(
                "UPDATE matches SET status='running' WHERE id=?", (match_id,)
            )
            self.store.conn.commit()
        return match_id

    def test_running_replay_hides_private_agent_state(self):
        match_id = self._run_match()
        bundle = self.store.replay_bundle(match_id)
        self.assertNotEqual(bundle["match"]["status"], "completed")
        self.assertTrue(bundle["redacted"])

        for snapshot in bundle["snapshots"]:
            for agent in snapshot["state"]["agents"].values():
                self.assertNotIn("memory", agent)
                self.assertNotIn("score_breakdown", agent)
                self.assertNotIn("tokens_remaining", agent)
                # public facts stay public
                self.assertIn("room", agent)
                self.assertIn("hp", agent)

        for event in bundle["events"]:
            changes = (event.get("payload") or {}).get("changes") or {}
            if isinstance(changes, dict):
                self.assertNotIn("memory", changes)
                self.assertNotIn("tokens_remaining", changes)

        for decision in bundle["decisions"]:
            self.assertNotIn("reasoning_summary", decision["action"])
            self.assertNotIn("memory_write", decision["action"])
            self.assertIn("action", decision["action"])

    def test_completed_replay_still_reveals_everything_for_audit(self):
        engine = ArenaEngine(
            self.store, MockDecisionProvider(), max_rounds=3, parallel_agents=False
        )
        match_id = engine.run(self.manifests, 4321)
        bundle = self.store.replay_bundle(match_id)
        self.assertEqual(bundle["match"]["status"], "completed")
        self.assertFalse(bundle["redacted"])
        self.assertEqual(bundle["match"]["seed"], 4321)
        self.assertTrue(
            any("memory" in snap["state"]["agents"][next(iter(snap["state"]["agents"]))]
                for snap in bundle["snapshots"])
        )
        proofs = [
            event
            for event in bundle["events"]
            if event["event_type"] == "dice_roll" and "proof" in event["payload"]
        ]
        self.assertTrue(proofs, "post-match dice proofs must stay verifiable")
        self.assertIn("seed", proofs[0]["payload"]["proof"])

    def test_running_replay_hides_the_seed_and_future_dice_proofs(self):
        match_id = self._run_match()
        bundle = self.store.replay_bundle(match_id)
        self.assertIsNone(bundle["match"]["seed"])
        for snapshot in bundle["snapshots"]:
            self.assertNotIn("seed", snapshot["state"])
        rolls = [
            event for event in bundle["events"] if event["event_type"] == "dice_roll"
        ]
        self.assertTrue(rolls, "dice rolls should still be listed, just not provable")
        for event in rolls:
            proof = event["payload"].get("proof", {})
            self.assertNotIn("seed", proof)
            self.assertNotIn("digest_prefix", proof)
            self.assertNotIn("counter", proof)
            self.assertIn("result", proof)
        # brute check: the raw seed must not appear anywhere in the bundle
        for path, value in _walk(bundle):
            self.assertNotEqual(
                (path.endswith("seed"), value),
                (True, 777777),
                f"seed leaked at {path}",
            )

    def test_match_list_hides_the_seed_of_a_live_match(self):
        """Withholding the seed from /replay is pointless if /api/matches
        hands out the same integer."""
        match_id = self._run_match(seed=313131)
        rows = {row["id"]: row for row in self.store.list_matches()}
        self.assertIsNone(rows[match_id]["seed"])
        with self.store.lock:
            self.store.conn.execute(
                "UPDATE matches SET status='completed' WHERE id=?", (match_id,)
            )
            self.store.conn.commit()
        rows = {row["id"]: row for row in self.store.list_matches()}
        self.assertEqual(rows[match_id]["seed"], 313131)

    def test_running_replay_over_http_hides_secrets(self):
        match_id = self._run_match(seed=515151)
        with _serve(self.store) as base:
            bundle = _get(f"{base}/api/matches/{match_id}/replay")
        blob = json.dumps(bundle)
        for marker in SECRET_MARKERS:
            self.assertNotIn(marker, blob)
        self.assertNotIn("digest_prefix", blob)
        self.assertNotIn("reasoning_summary", blob)
        self.assertNotIn("memory_write", blob)


class _ServerContext:
    def __init__(self, store: ArenaStore):
        self.httpd = ArenaHTTPServer(("127.0.0.1", 0), store)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self.thread.start()
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"

    def __exit__(self, *exc) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


def _serve(store: ArenaStore) -> _ServerContext:
    return _ServerContext(store)


def _get(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
