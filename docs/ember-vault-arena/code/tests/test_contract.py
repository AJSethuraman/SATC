from __future__ import annotations

"""agent-action-1.0, the brain loader, notes, whispers, give, and the two
hosted adapters through fakes (PRD seams 1, 3 and 4)."""

import asyncio
import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from arena import rules
from arena.brains import load_brain, load_brains, parse_brain
from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.models import (
    ACTION_SCHEMA_VERSION,
    AgentAction,
    AgentManifest,
    Note,
    Speech,
    ValidationError,
    action_json_schema,
    manifest_json_schema,
)
from arena.providers import (
    AgentSDKProvider,
    AnthropicProvider,
    MockDecisionProvider,
    compile_prompt,
    provider_from_name,
)
from arena.storage import ArenaStore, canonical_json

ROOT = Path(__file__).resolve().parent.parent


# ── the pinned schemas are the generated schemas (tenet S8) ─────────────────

class SchemaPinTests(unittest.TestCase):
    def test_pinned_action_schema_equals_generated(self):
        pinned = json.loads((ROOT / "schemas" / "agent-action.schema.json").read_text())
        self.assertEqual(pinned, action_json_schema())
        self.assertEqual(pinned["description"], ACTION_SCHEMA_VERSION)
        self.assertEqual(pinned["$schema"], "http://json-schema.org/draft-07/schema#")

    def test_pinned_manifest_schema_equals_generated(self):
        pinned = json.loads((ROOT / "schemas" / "agent-manifest.schema.json").read_text())
        self.assertEqual(pinned, manifest_json_schema())

    def test_schema_and_validator_agree_on_a_good_action(self):
        raw = {
            "action": "guard", "target": None, "destination": None, "item": None,
            "tile": None, "speech": {"mode": "whisper", "to": "nix", "text": "later"},
            "note": {"objective": "hold", "reads": [{"who": "nix", "stance": "trust", "why": "shared"}]},
            "deal": None,
        }
        action = AgentAction.from_dict(raw)
        self.assertEqual(action.as_dict(), raw)


class ActionContractTests(unittest.TestCase):
    def _raw(self, **over):
        raw = {
            "action": "guard", "target": None, "destination": None, "item": None,
            "tile": None, "speech": {"mode": "silent", "to": None, "text": ""},
            "note": {"objective": "", "reads": []}, "deal": None,
        }
        raw.update(over)
        return raw

    def test_deal_must_be_null_in_1_0(self):
        with self.assertRaisesRegex(ValidationError, "deal must be null"):
            AgentAction.from_dict(self._raw(deal={"kind": "offer"}))

    def test_note_is_required(self):
        raw = self._raw(); del raw["note"]
        with self.assertRaisesRegex(ValidationError, "note is required"):
            AgentAction.from_dict(raw)

    def test_old_fields_are_unknown(self):
        with self.assertRaisesRegex(ValidationError, "unknown action fields"):
            AgentAction.from_dict(self._raw(reasoning_summary="x"))

    def test_whisper_needs_a_target_and_say_refuses_one(self):
        with self.assertRaisesRegex(ValidationError, "whisper needs"):
            Speech.from_raw({"mode": "whisper", "to": None, "text": "psst"})
        with self.assertRaisesRegex(ValidationError, "only for a whisper"):
            Speech.from_raw({"mode": "say", "to": "nix", "text": "hi"})

    def test_speech_and_note_caps(self):
        with self.assertRaises(ValidationError):
            Speech.from_raw({"mode": "say", "to": None, "text": "x" * 301})
        with self.assertRaises(ValidationError):
            Note.from_raw({"objective": "x" * 121, "reads": []})
        with self.assertRaises(ValidationError):
            Note.from_raw({"objective": "", "reads": [{"who": f"a{i}", "stance": "trust", "why": ""} for i in range(5)]})


# ── brains ──────────────────────────────────────────────────────────────────

GOOD_BRAIN = """# Ash the Quiet
Build: scout

## Voice
Says little. Means it.

## Wants
The Crown, if nobody is looking.

## Treats
Strangers: warily. Allies: fairly. Betrayers: never again.

## Never
Never speaks first.
"""


class BrainLoaderTests(unittest.TestCase):
    def test_a_good_brain_loads_with_a_derived_objective(self):
        raw = parse_brain(GOOD_BRAIN, default_id="ash")
        manifest = AgentManifest.from_dict(raw)
        self.assertEqual((manifest.id, manifest.build, manifest.kind), ("ash", "scout", "character"))
        self.assertIn(manifest.secret_objective, {"monster_hunter", "lorekeeper", "oathbreaker", "treasure_hoarder"})
        self.assertEqual(manifest.never, "Never speaks first.")

    def test_over_the_cap_names_the_longest_section_and_the_overage(self):
        text = GOOD_BRAIN.replace("Says little. Means it.", "very long voice " * 125)
        with self.assertRaisesRegex(ValidationError, r"Over by \d+\. The longest section is '## Voice'"):
            AgentManifest.from_dict(parse_brain(text, default_id="ash"))

    def test_a_missing_section_is_named(self):
        text = GOOD_BRAIN.replace("## Never\nNever speaks first.\n", "")
        with self.assertRaisesRegex(ValidationError, "missing section.*## Never"):
            parse_brain(text, default_id="ash")

    def test_a_link_is_refused_by_section(self):
        text = GOOD_BRAIN.replace("Means it.", "See https://example.com")
        with self.assertRaisesRegex(ValidationError, "'## Voice' contains a link"):
            parse_brain(text, default_id="ash")

    def test_the_house_brains_load_and_use_each_build_twice(self):
        manifests = load_brains(ROOT / "brains" / "house")
        self.assertEqual(len(manifests), 8)
        builds = sorted(m.build for m in manifests)
        self.assertEqual(builds, ["mystic", "mystic", "scoundrel", "scoundrel", "scout", "scout", "vanguard", "vanguard"])

    def test_the_template_itself_is_not_a_brain_in_a_folder(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(4):
                (Path(d) / f"0{i}_brain{i}.md").write_text(GOOD_BRAIN.replace("Ash the Quiet", f"B{i}"), encoding="utf-8")
            (Path(d) / "TEMPLATE.md").write_text(GOOD_BRAIN, encoding="utf-8")
            self.assertEqual([m.id for m in load_brains(d)], ["brain0", "brain1", "brain2", "brain3"])


# ── the note round-trips; whispers reach one; give moves an item (seams 1, 3) ─

class NoteWhisperGiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manifests = load_manifests()

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, provider, seed=7, rounds=3):
        store = ArenaStore(Path(self.temp.name) / f"m{seed}.db")
        engine = ArenaEngine(store, provider, max_rounds=rounds, parallel_agents=False)
        return store, engine.run(self.manifests, seed)

    def test_the_note_written_in_one_round_is_the_your_note_of_the_next(self):
        seen: dict[str, list[str]] = {}

        class NotingProvider(MockDecisionProvider):
            def decide(self, manifest, prompt, observation):
                seen.setdefault(manifest.id, []).append(observation["your_note"]["objective"])
                result = super().decide(manifest, prompt, observation)
                raw = json.loads(result.raw_output)
                raw["note"] = {"objective": f"{manifest.id} round {observation['public_state']['round']}", "reads": []}
                return type(result)(canonical_json(raw), result.input_tokens, result.output_tokens, "mock", "mock")

        store, _ = self._run(NotingProvider())
        store.close()
        for agent_id, notes in seen.items():
            self.assertEqual(notes[0], "")
            self.assertEqual(notes[1], f"{agent_id} round 1")
            self.assertEqual(notes[2], f"{agent_id} round 2")

    def test_no_character_ever_sees_another_note_and_only_the_target_hears_a_whisper(self):
        state = rules.new_match_state(self.manifests, 99, 12)
        ids = sorted(state["agents"])
        a, b, c = ids[0], ids[1], ids[2]
        state["agents"][a]["note"] = {"objective": "A-PRIVATE-OBJECTIVE", "reads": []}
        state["round"] = 2
        state["recent_speech"] = [{
            "round": 1, "agent_id": a, "name": state["agents"][a]["name"], "mode": "whisper",
            "to": b, "text": "A-WHISPER-TEXT", "room": state["agents"][a]["room"], "addressed_ids": [b],
        }]
        for who in ids:
            obs = rules.visible_observation(deepcopy(state), who, self.manifests[0].secret_objective, [])
            blob = canonical_json(obs)
            if who != a:
                self.assertNotIn("A-PRIVATE-OBJECTIVE", blob)
            if who == b:
                self.assertIn("A-WHISPER-TEXT", blob)
                self.assertEqual(obs["whispers_seen"], [])
            elif who == a:
                self.assertNotIn("A-WHISPER-TEXT", blob)  # nobody hears their own line
            else:
                self.assertNotIn("A-WHISPER-TEXT", blob)
                self.assertEqual(obs["whispers_seen"], [{"round": 1, "from": a, "to": b}])

    def test_a_whisper_is_hidden_mid_match_and_revealed_when_complete(self):
        class Whisperer(MockDecisionProvider):
            def decide(self, manifest, prompt, observation):
                result = super().decide(manifest, prompt, observation)
                raw = json.loads(result.raw_output)
                others = [o["id"] for o in observation.get("visible_agents", [])]
                if others:
                    raw["speech"] = {"mode": "whisper", "to": others[0], "text": f"SECRET-{manifest.id}"}
                return type(result)(canonical_json(raw), result.input_tokens, result.output_tokens, "mock", "mock")

        store = ArenaStore(Path(self.temp.name) / "w.db")
        engine = ArenaEngine(store, Whisperer(), max_rounds=2, parallel_agents=False)
        # mid-match projection: run one round by hand through the public path
        match_id = engine.run(self.manifests, 5)
        bundle = store.replay_bundle(match_id)
        self.assertFalse(bundle["redacted"])
        self.assertTrue(any("SECRET-" in canonical_json(e) for e in bundle["events"]))
        # force the mid-match view and check the words are gone but the fact stays
        with store.lock:
            store.conn.execute("UPDATE matches SET status='running' WHERE id=?", (match_id,))
            store.conn.commit()
        live = store.replay_bundle(match_id)
        self.assertTrue(live["redacted"])
        self.assertNotIn("SECRET-", canonical_json(live))
        self.assertTrue(any(e["event_type"] == "agent_speech" and (e.get("payload") or {}).get("mode") == "whisper"
                            for e in live["events"]))
        self.assertNotIn("A-PRIVATE", canonical_json(live))
        self.assertTrue(all("note" not in d["action"] for d in live["decisions"]))
        store.close()

    def test_give_is_legal_only_with_an_item_and_a_neighbour_and_moves_the_item(self):
        state = rules.new_match_state(self.manifests, 3, 12)
        ids = sorted(state["agents"])
        giver, receiver = ids[0], ids[1]
        state["agents"][giver]["inventory"].append("healing_tonic")
        obs = rules.visible_observation(deepcopy(state), giver, "lorekeeper", [])
        gives = [e for e in obs["legal_actions"] if e["action"] == "give"]
        self.assertTrue(gives)
        self.assertTrue(all(g["item"] == "healing_tonic" for g in gives))
        self.assertIn(receiver, {g["target"] for g in gives})
        # and never the Crown
        state["agents"][giver]["inventory"].append(rules.CROWN_ITEM_ID)
        obs = rules.visible_observation(deepcopy(state), giver, "lorekeeper", [])
        self.assertFalse(any(g["item"] == rules.CROWN_ITEM_ID for g in obs["legal_actions"] if g["action"] == "give"))

        store = ArenaStore(Path(self.temp.name) / "g.db")
        engine = ArenaEngine(store, MockDecisionProvider(), max_rounds=1, parallel_agents=False)
        engine.match_id = "give-test"
        engine.state = state
        engine.manifests = {m.id: m for m in self.manifests}
        engine.rng = rules.__dict__.get("HashRNG", None) or __import__("arena.rng", fromlist=["HashRNG"]).HashRNG(3)
        for m in self.manifests:
            store.register_agent(m)
        store.create_match("give-test", 3, "ember-vault-0.2", 1, self.manifests)
        engine._give(giver, AgentAction(action="give", target=receiver, item="healing_tonic"))
        self.assertNotIn("healing_tonic", state["agents"][giver]["inventory"])
        self.assertIn("healing_tonic", state["agents"][receiver]["inventory"])
        events = store.events_for_match("give-test")
        self.assertTrue(any(e["event_type"] == "item_given" and e["target_id"] == receiver for e in events))
        store.close()


# ── seam 4: the gateway through fakes ───────────────────────────────────────

def _prompt():
    manifests = load_manifests()
    state = rules.new_match_state(manifests, 1, 12)
    obs = rules.visible_observation(deepcopy(state), manifests[0].id, manifests[0].secret_objective, [])
    return manifests[0], compile_prompt(manifests[0], obs), obs


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Usage:
    def __init__(self, i, o, cached=0, created=0):
        self.input_tokens, self.output_tokens, self.cache_read_input_tokens = i, o, cached
        self.cache_creation_input_tokens = created


class _Response:
    def __init__(self, text, stop_reason="end_turn", model="claude-opus-5", cached=0, created=0):
        self.content = [_Block(text)]
        self.stop_reason = stop_reason
        self.model = model
        self.usage = _Usage(1000, 100, cached, created)
        self._request_id = "req_test"


class _FakeMessages:
    def __init__(self, outcome):
        self.outcome, self.calls = outcome, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class _FakeClient:
    def __init__(self, outcome):
        self.messages = _FakeMessages(outcome)


GOOD_JSON = canonical_json({
    "action": "guard", "target": None, "destination": None, "item": None, "tile": None,
    "speech": {"mode": "say", "to": None, "text": "Steady."},
    "note": {"objective": "survive", "reads": []}, "deal": None,
})


class AnthropicAdapterTests(unittest.TestCase):
    def test_a_turn_carries_cost_tokens_and_digests(self):
        manifest, prompt, obs = _prompt()
        client = _FakeClient(_Response(GOOD_JSON, cached=400, created=50))
        result = AnthropicProvider(client=client, model="claude-opus-5").decide(manifest, prompt, obs)
        self.assertIsNone(result.error_kind)
        self.assertEqual(result.raw_output, GOOD_JSON)
        self.assertEqual((result.input_tokens, result.output_tokens, result.cached_tokens), (1000, 100, 400))
        self.assertEqual(result.cache_creation_tokens, 50)
        self.assertEqual(result.cost_source, "provider_usage")
        # the API's input_tokens excludes cached and written tokens: three separate counts
        self.assertAlmostEqual(result.cost_usd, (1000 * 5.0 + 400 * 0.5 + 50 * 6.25 + 100 * 25.0) / 1e6)
        self.assertTrue(result.request_digest and result.response_digest)
        sent = client.messages.calls[0]
        self.assertEqual(sent["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(sent["output_config"]["effort"], "low")
        self.assertNotIn("system_prompt", sent["system"])  # platform rules only
        self.assertTrue(all(m["role"] == "user" for m in sent["messages"]))

    def test_a_refusal_is_a_panic_and_an_exception_is_network(self):
        manifest, prompt, obs = _prompt()
        refused = AnthropicProvider(client=_FakeClient(_Response("", stop_reason="refusal"))).decide(manifest, prompt, obs)
        self.assertEqual(refused.error_kind, "panic")
        down = AnthropicProvider(client=_FakeClient(RuntimeError("429 rate limited"))).decide(manifest, prompt, obs)
        self.assertEqual(down.error_kind, "network")
        self.assertIn("rate limited", down.stop_reason)


class _Result:
    """Shaped like claude-agent-sdk 0.2.152's ResultMessage, as inspected on
    11 Sep 2026: usage is a dict, errors a list, plus subtype/result/
    structured_output/total_cost_usd/session_id."""

    def __init__(self, subtype, structured=None, text="", cost=0.01, errors=None):
        self.subtype, self.structured_output, self.result = subtype, structured, text
        self.total_cost_usd, self.session_id = cost, "sess_test"
        # the top-level usage under-reports a schema-constrained call (forge probe,
        # 12 Sep 2026); model_usage carries the counts the cost is priced on
        self.usage = {"input_tokens": 2, "output_tokens": 80, "cache_read_input_tokens": 300,
                      "cache_creation_input_tokens": 0}
        self.model_usage = {"claude-opus-5": {"inputTokens": 900, "outputTokens": 80,
                                              "cacheReadInputTokens": 300, "cacheCreationInputTokens": 45,
                                              "costUSD": cost, "canonicalModel": "claude-opus-5"}}
        self.errors = errors or []
        self.is_error = subtype != "success"


def _fake_query(*results, delay=0.0):
    async def query(prompt, options):
        for r in results:
            if delay:
                await asyncio.sleep(delay)
            yield r
    return query


class _Opts(dict):
    def __init__(self, **kw):
        super().__init__(**kw)


class AgentSDKAdapterTests(unittest.TestCase):
    def _provider(self, *results, delay=0.0, timeout=5.0):
        return AgentSDKProvider(query=_fake_query(*results, delay=delay), options_factory=_Opts,
                               timeout_seconds=timeout, model="opus")

    def test_structured_output_becomes_the_raw_json(self):
        manifest, prompt, obs = _prompt()
        result = self._provider(_Result("success", structured=json.loads(GOOD_JSON))).decide(manifest, prompt, obs)
        self.assertIsNone(result.error_kind)
        self.assertEqual(json.loads(result.raw_output), json.loads(GOOD_JSON))
        self.assertEqual(result.cost_source, "sdk_estimate")
        self.assertEqual(result.cost_usd, 0.01)
        # the tokens come from model_usage (what the cost is priced on), not the
        # top-level usage, which said 2 uncached for this call
        self.assertEqual((result.input_tokens, result.output_tokens, result.cached_tokens), (900, 80, 300))
        self.assertEqual(result.cache_creation_tokens, 45)
        # the ledger carries the id the CLI billed, not the alias "opus" we asked for
        self.assertEqual(result.model, "claude-opus-5")

    def test_counts_fall_back_to_iterations_then_top_level_usage(self):
        from arena.providers import sdk_counts
        r = _Result("success")
        r.model_usage = None
        r.usage = {"input_tokens": 2, "output_tokens": 5, "cache_read_input_tokens": 10,
                   "cache_creation_input_tokens": 0,
                   "iterations": [{"input_tokens": 4000, "output_tokens": 300, "cache_read_input_tokens": 0,
                                   "cache_creation_input_tokens": 2000, "type": "message"},
                                  {"input_tokens": 2, "output_tokens": 5, "cache_read_input_tokens": 10,
                                   "cache_creation_input_tokens": 0, "type": "message"}]}
        self.assertEqual(sdk_counts(r, "opus"), (4002, 305, 10, 2000, "opus"))
        r.usage = {"input_tokens": 457, "output_tokens": 4, "cache_read_input_tokens": 0,
                   "cache_creation_input_tokens": 0}
        self.assertEqual(sdk_counts(r, "opus"), (457, 4, 0, 0, "opus"))

    def test_success_without_structured_output_and_max_retries_are_panics(self):
        manifest, prompt, obs = _prompt()
        self.assertEqual(self._provider(_Result("success", None, "prose")).decide(manifest, prompt, obs).error_kind, "panic")
        self.assertEqual(self._provider(_Result("error_max_structured_output_retries")).decide(manifest, prompt, obs).error_kind, "panic")
        failed = self._provider(_Result("error_during_execution", errors=["rate limited"])).decide(manifest, prompt, obs)
        self.assertEqual(failed.error_kind, "network")
        self.assertIn("rate limited", failed.stop_reason)

    def test_no_result_a_raise_and_a_timeout_are_network(self):
        manifest, prompt, obs = _prompt()
        self.assertEqual(self._provider().decide(manifest, prompt, obs).error_kind, "network")

        async def boom(prompt, options):
            raise RuntimeError("process died")
            yield  # pragma: no cover

        self.assertEqual(AgentSDKProvider(query=boom, options_factory=_Opts).decide(manifest, prompt, obs).error_kind, "network")
        slow = self._provider(_Result("success", structured=json.loads(GOOD_JSON)), delay=0.5, timeout=0.05)
        self.assertEqual(slow.decide(manifest, prompt, obs).error_kind, "network")

    def test_options_disable_tools_and_load_nothing_from_the_repo(self):
        captured = {}

        def factory(**kw):
            captured.update(kw)
            return kw

        manifest, prompt, obs = _prompt()
        AgentSDKProvider(query=_fake_query(_Result("success", structured=json.loads(GOOD_JSON))),
                         options_factory=factory).decide(manifest, prompt, obs)
        self.assertEqual(captured["tools"], [])
        self.assertEqual(captured["max_turns"], 1)
        self.assertEqual(captured["setting_sources"], [])
        self.assertEqual(captured["output_format"]["type"], "json_schema")
        self.assertNotIn(str(ROOT), captured["cwd"])


class EngineGatewayTests(unittest.TestCase):
    """The engine's side of seam 4: panic is never retried, network once."""

    def test_panic_is_called_once_and_network_twice_per_decision(self):
        calls = {"panic": 0, "network": 0}

        class Panicking(MockDecisionProvider):
            def decide(self, manifest, prompt, observation):
                calls["panic"] += 1
                r = super().decide(manifest, prompt, observation)
                return type(r)("", 0, 0, "fake", "fake", error_kind="panic", stop_reason="refusal")

        class Flaky(MockDecisionProvider):
            def decide(self, manifest, prompt, observation):
                calls["network"] += 1
                r = super().decide(manifest, prompt, observation)
                return type(r)("", 0, 0, "fake", "fake", error_kind="network", stop_reason="timeout")

        manifests = load_manifests()
        with tempfile.TemporaryDirectory() as d:
            for name, provider in (("panic", Panicking()), ("network", Flaky())):
                store = ArenaStore(Path(d) / f"{name}.db")
                match_id = ArenaEngine(store, provider, max_rounds=1, parallel_agents=False).run(manifests, 11)
                decisions = store.replay_bundle(match_id)["decisions"]
                self.assertEqual(len(decisions), len(manifests))
                self.assertTrue(all(dec["validity"] == f"{name}_fallback" for dec in decisions))
                self.assertTrue(all(dec["action"]["action"] == "guard" for dec in decisions))
                store.close()
        self.assertEqual(calls["panic"], len(manifests))
        self.assertEqual(calls["network"], 2 * len(manifests))

    def test_no_credential_reaches_a_replay_or_audit_export(self):
        secret = "sk-ant-TESTSECRET-DO-NOT-LEAK"
        manifests = load_manifests()
        old = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = secret
        try:
            with tempfile.TemporaryDirectory() as d:
                store = ArenaStore(Path(d) / "s.db")
                match_id = ArenaEngine(store, MockDecisionProvider(), max_rounds=2, parallel_agents=False).run(manifests, 12)
                blob = canonical_json(store.replay_bundle(match_id)) + canonical_json(store.verify_audit(match_id))
                rows = store.conn.execute("SELECT body_json FROM audit_log WHERE match_id=?", (match_id,)).fetchall()
                blob += "".join(r[0] for r in rows)
                self.assertNotIn(secret, blob)
                self.assertNotIn("Authorization", blob)
                store.close()
        finally:
            if old is None:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            else:
                os.environ["ANTHROPIC_API_KEY"] = old

    def test_provider_names(self):
        self.assertIsInstance(provider_from_name("mock"), MockDecisionProvider)
        self.assertIsInstance(provider_from_name("agent_sdk"), AgentSDKProvider)
        self.assertIsInstance(provider_from_name("anthropic"), AnthropicProvider)
        with self.assertRaises(ValueError):
            provider_from_name("nope")


if __name__ == "__main__":
    unittest.main()
