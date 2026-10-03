"""Talkers (PRD §5.25, built 19 Sep 2026): three house side characters on the
same contract with a restricted legal set. They speak, whisper, offer and
accept; they move, give and guard; they cannot score, carry the Crown,
search, or win; a rival may attack one from act II (PRD §5.8) and its death
pays nobody and is public; monsters never hunt them; their brains are the
firm's, drafted here by the session."""
from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from arena import rules, scoring
from arena.demo import load_manifests, load_talkers
from arena.engine import ArenaEngine
from arena.models import AgentAction, AgentManifest, TALKER_ACTIONS
from arena.providers import MockDecisionProvider, compile_prompt, opening_template
from arena.rng import HashRNG
from arena.storage import ArenaStore


class TalkerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.characters = load_manifests()
        self.talkers = load_talkers()
        self.roster = self.characters + self.talkers
        self.ids = sorted(m.id for m in self.characters)
        self.tids = sorted(m.id for m in self.talkers)
        self._stores = []

    def tearDown(self):
        for store in self._stores:
            store.close()
        self.temp.cleanup()

    def engine(self, name="unit.db", seed=7, round_no=1):
        store = ArenaStore(self.root / name)
        self._stores.append(store)
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=False)
        engine.match_id = "unit"
        engine.manifests = {m.id: m for m in self.roster}
        engine.state = rules.new_match_state(self.roster, seed)
        engine.state["status"] = "running"
        engine.state["round"] = round_no
        engine.state["act"] = rules.act_for_round(round_no)
        engine.rng = HashRNG(seed)
        return engine

    def obs(self, engine, agent_id):
        m = engine.manifests[agent_id]
        return rules.visible_observation(deepcopy(engine.state), agent_id, m.secret_objective, [])

    def events(self, engine, kind):
        return [e for e in engine.store.events_for_match(engine.match_id) if e["event_type"] == kind]


class TheHouseTalkers(TalkerTestCase):
    def test_three_talkers_load_with_agenda_knows_holds_and_a_start(self):
        self.assertEqual(self.tids, ["coin", "vesper", "wick"])
        for t in self.talkers:
            self.assertEqual(t.kind, "talker")
            self.assertTrue(t.agenda and t.voice)
            self.assertTrue(t.knows)
            self.assertIn(t.start, rules.ROOMS)
            self.assertEqual(t.build, "")
        coin = next(t for t in self.talkers if t.id == "coin")
        self.assertEqual(coin.holds, ("healing_tonic",))
        state = rules.new_match_state(self.roster, 3)
        self.assertEqual(len(state["agents"]), 11)
        for t in self.talkers:
            a = state["agents"][t.id]
            self.assertEqual((a["kind"], a["room"], a["build"]), ("talker", t.start, ""))
        self.assertEqual(state["agents"]["coin"]["inventory"], ["healing_tonic"])
        # no two bodies share a tile at the start
        tiles = [(a["room"], tuple(a["tile"])) for a in state["agents"].values()]
        self.assertEqual(len(set(tiles)), len(tiles))
        with self.assertRaises(ValueError):
            ArenaEngine(ArenaStore(self.root / "x.db"), MockDecisionProvider()).run(self.characters + self.talkers * 2, seed=1)

    def test_a_talker_moves_gives_and_guards_and_nothing_else(self):
        engine = self.engine()
        obs = self.obs(engine, "coin")
        self.assertEqual(obs["you"]["kind"], "talker")
        self.assertIsNone(obs["secret_objective"])
        verbs = {e["action"] for e in obs["legal_actions"]}
        self.assertTrue(verbs)
        self.assertTrue(verbs <= set(TALKER_ACTIONS), verbs)
        self.assertIn("move", verbs)
        self.assertIn("guard", verbs)
        # in a room with a cache, a seal, a site and a rival: still only those three
        state = engine.state
        state["agents"]["wick"]["room"] = "bell_tower"
        state["agents"]["wick"]["tile"] = [0, 1]
        state["agents"][self.ids[0]]["room"] = "bell_tower"
        state["agents"][self.ids[0]]["tile"] = [1, 0]
        state["round"] = rules.ACT_I_LAST_ROUND + 1
        state["act"] = 2
        verbs = {e["action"] for e in self.obs(engine, "wick")["legal_actions"]}
        self.assertTrue(verbs <= set(TALKER_ACTIONS), verbs)
        # the contestant beside it sees a talker, and cannot attack it even in act II
        obs = self.obs(engine, self.ids[0])
        seen = next(v for v in obs["visible_agents"] if v["id"] == "wick")
        self.assertEqual(seen["kind"], "talker")
        # and can attack it from act II (PRD §5.8): a talker's death pays nothing and is public
        self.assertTrue([e for e in obs["legal_actions"] if e["action"] == "attack" and e["target"] == "wick"])
        self.assertNotIn("wick", [r["id"] for r in obs["standings"]])
        self.assertEqual(len(obs["standings"]), 8)

    def test_a_talker_never_scores_places_or_wins_and_cannot_hold_the_crown(self):
        engine = self.engine(round_no=10)
        state = engine.state
        a = self.ids[0]
        state["monsters"]["crown_warden"]["hp"] = 0
        rules.crown_unlock(state, 9)
        rules.floor_remove(state, rules.VAULT_ROOM, rules.CROWN_ITEM_ID)
        rules.inventory_add(state, a, rules.CROWN_ITEM_ID)
        rules.crown_to_carrier(state, a)
        for who in (a, "wick"):
            state["agents"][who]["room"] = rules.VAULT_ROOM
        state["agents"][a]["tile"], state["agents"]["wick"]["tile"] = [1, 3], [2, 3]
        obs = self.obs(engine, a)
        self.assertFalse([e for e in obs["legal_actions"] if e["action"] == "give" and e["item"] == rules.CROWN_ITEM_ID and e["target"] == "wick"])
        engine._resolve_action(a, AgentAction(action="give", target="wick", item=rules.CROWN_ITEM_ID))
        self.assertEqual(self.events(engine, "stale_action")[-1]["payload"]["reason"], "a talker cannot carry the Crown")
        self.assertEqual(state["crown"]["carrier_id"], a)
        # scoring a talker is a no-op, even the penalty
        engine._score("wick", "seal_activated", 5, "impossible")
        engine._invalid_action("wick", AgentAction(action="search"), "no")
        self.assertEqual(state["agents"]["wick"]["score"], 0)
        self.assertEqual(state["agents"]["wick"]["score_breakdown"], {})
        self.assertNotIn("wick", scoring.placements(state))
        self.assertEqual(sorted(scoring.placements(state)), self.ids)

    def test_a_monster_never_swings_at_a_talker(self):
        engine = self.engine(round_no=2)
        state = engine.state
        state["agents"]["vesper"]["room"] = "ironwood_gate"
        state["agents"]["vesper"]["tile"] = [2, 2]  # beside the guardian at [2,1]
        for who in self.ids:
            state["agents"][who]["room"] = "threshold"
        engine._monster_phase(2)
        self.assertFalse([e for e in self.events(engine, "attack_hit") + self.events(engine, "attack_miss") if e["target_id"] == "vesper"])
        self.assertEqual(state["agents"]["vesper"]["hp"], state["agents"]["vesper"]["max_hp"])

    def test_the_prompt_carries_the_agenda_and_the_talker_rules_and_never_the_player_sections(self):
        engine = self.engine()
        wick = engine.manifests["wick"]
        prompt = compile_prompt(wick, self.obs(engine, "wick"))
        system, config = prompt["messages"][0]["content"], prompt["messages"][1]["content"]
        self.assertIn("YOU ARE A TALKER", system)
        self.assertIn("cannot score, take the Crown, search, or win", system)
        self.assertIn(wick.agenda[:40], config)
        self.assertIn(wick.knows[0][:40], config)
        self.assertIn('author="house"', config)
        self.assertNotIn('"wants"', config)
        character = compile_prompt(engine.manifests[self.ids[0]], self.obs(engine, self.ids[0]))
        self.assertNotIn("YOU ARE A TALKER", character["messages"][0]["content"])
        self.assertIn('author="submitter"', character["messages"][1]["content"])

    def test_a_whole_match_with_eleven_runs_and_the_talkers_speak_deal_and_never_place(self):
        store = ArenaStore(self.root / "eleven.db")
        self._stores.append(store)
        engine = ArenaEngine(store, MockDecisionProvider(), max_rounds=8, parallel_agents=True)
        match_id = engine.run(self.roster, seed=11)
        bundle = store.replay_bundle(match_id)
        self.assertEqual(bundle["match"]["status"], "completed")
        self.assertTrue(store.verify_audit(match_id)["valid"])
        self.assertIn(bundle["match"]["winner_agent_id"], self.ids)
        by_id = {p["manifest"]["id"]: p for p in bundle["participants"]}
        self.assertEqual(len(by_id), 11)
        for tid in self.tids:
            self.assertIsNone(by_id[tid]["placement"])
            self.assertEqual(by_id[tid]["final_score"], 0)
        self.assertEqual(sorted(p["placement"] for pid, p in by_id.items() if pid in self.ids), list(range(1, 9)))
        final = next(e for e in bundle["events"] if e["event_type"] == "final_scores")
        self.assertEqual(sorted(final["payload"]["placements"]), self.ids)
        self.assertEqual(sorted(final["payload"]["scores"]), self.ids)
        reveals = [e["actor_id"] for e in bundle["events"] if e["event_type"] == "objective_reveal"]
        self.assertEqual(sorted(reveals), self.ids)
        # they spoke, and every action they took was in their set
        spoke = {e["actor_id"] for e in bundle["events"] if e["event_type"] == "agent_speech"}
        self.assertTrue(set(self.tids) & spoke)
        for d in bundle["decisions"]:
            if d["agent_id"] in self.tids:
                self.assertIn(d["action"]["action"], TALKER_ACTIONS, d["action"])
        opening = next(e for e in bundle["events"] if e["event_type"] == "match_opening")
        for t in self.talkers:
            self.assertIn(t.name, opening["public_text"])
        self.assertEqual([c["name"] for c in opening["payload"]["facts"]["contestants"]], [m.name for m in sorted(self.characters, key=lambda m: m.id)])
        self.assertEqual(len(opening["payload"]["facts"]["talkers"]), 3)
        self.assertNotIn("agenda", json.dumps(opening["payload"]["facts"]))


if __name__ == "__main__":
    unittest.main()
