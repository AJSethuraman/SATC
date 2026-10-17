"""Cooperative objective sites (PRD §5.3, built 19 Sep 2026): a site wakes
only when every one of its hands is lent by a different character in the
same round, and pays each of them; too few hands lapses in public and the
try is shown in the next digest. The Gallery's braziers take two, the Bone
Well's winch two, the Bell Tower's bell three."""
from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from arena import rules, world
from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.models import AgentAction
from arena.providers import MockDecisionProvider
from arena.rng import HashRNG
from arena.storage import ArenaStore


class SiteTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifests = load_manifests()
        self.ids = sorted(m.id for m in self.manifests)
        self._stores = []

    def tearDown(self):
        for store in self._stores:
            store.close()
        self.temp.cleanup()

    def engine(self, name="unit.db", seed=7, round_no=3):
        store = ArenaStore(self.root / name)
        self._stores.append(store)
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=False)
        engine.match_id = "unit"
        engine.manifests = {m.id: m for m in self.manifests}
        engine.state = rules.new_match_state(self.manifests, seed)
        engine.state["status"] = "running"
        engine.state["round"] = round_no
        engine.state["act"] = rules.act_for_round(round_no)
        engine.rng = HashRNG(seed)
        return engine

    def events(self, engine, kind):
        return [e for e in engine.store.events_for_match(engine.match_id) if e["event_type"] == kind]

    def put(self, engine, agent_id, room, tile):
        engine.state["agents"][agent_id]["room"] = room
        engine.state["agents"][agent_id]["tile"] = list(tile)

    def obs(self, engine, agent_id):
        return rules.visible_observation(deepcopy(engine.state), agent_id, "lorekeeper", [])


class TheRegistry(SiteTestCase):
    def test_three_sites_with_their_hands_drawn_as_features(self):
        self.assertEqual(sorted(world.SITES), ["gallery_braziers", "tower_bell", "well_winch"])
        self.assertEqual(len(world.SITES["tower_bell"]["hands"]), 3)
        for sid, site in world.SITES.items():
            for hand in site["hands"]:
                self.assertIn(hand, world.ROOMS[site["room"]]["grid"]["features"])
                self.assertEqual(world.site_of_hand(hand), sid)
        self.assertIsNone(world.site_of_hand("seal"))
        state = rules.new_match_state(self.manifests, 1)
        self.assertEqual(sorted(state["sites"]), sorted(world.SITES))
        self.assertTrue(all(s["status"] == "waiting" and s["hands"] == {} for s in state["sites"].values()))


class LendingHands(SiteTestCase):
    def test_hands_are_legal_in_the_room_while_the_site_waits_and_the_digest_says_what_it_needs(self):
        a, b = self.ids[:2]
        engine = self.engine()
        self.put(engine, a, "the_gallery", (1, 1))
        obs = self.obs(engine, a)
        hands = sorted(e["target"] for e in obs["legal_actions"] if e["action"] == "interact")
        self.assertEqual(hands, ["brazier_east", "brazier_west"])
        site = obs["room"]["sites"][0]
        self.assertEqual((site["id"], site["needs"], site["points"], site["status"]), ("gallery_braziers", 2, 4, "waiting"))
        self.assertIsNone(site["last_attempt"])
        self.assertIn("2 hands in one round", next(e["label"] for e in obs["legal_actions"] if e["action"] == "interact"))
        # nowhere else
        self.put(engine, b, "threshold", (2, 2))
        self.assertFalse([e for e in self.obs(engine, b)["legal_actions"] if e["action"] == "interact"])

    def test_one_hand_lapses_in_public_and_the_next_digest_shows_the_try(self):
        a, b = self.ids[:2]
        engine = self.engine()
        self.put(engine, a, "the_gallery", (1, 1))
        self.put(engine, b, "the_gallery", (2, 1))
        engine._resolve_action(a, AgentAction(action="interact", target="brazier_west"))
        self.assertEqual(engine.state["sites"]["gallery_braziers"]["hands"], {"brazier_west": a})
        lent = self.events(engine, "site_hand")
        self.assertEqual((lent[0]["actor_id"], lent[0]["target_id"], lent[0]["payload"]["lent"]), (a, "brazier_west", 1))
        engine._end_round_upkeep(3)
        lapsed = self.events(engine, "site_lapsed")
        self.assertEqual(len(lapsed), 1)
        self.assertIn("had 1", lapsed[0]["public_text"])
        rec = engine.state["sites"]["gallery_braziers"]
        self.assertEqual((rec["status"], rec["hands"], rec["last_attempt"]), ("waiting", {}, {"round": 3, "hands": {"brazier_west": a}}))
        self.assertEqual(engine.state["agents"][a]["score"], 0)
        self.assertEqual(self.obs(engine, b)["room"]["sites"][0]["last_attempt"], {"round": 3, "hands": {"brazier_west": a}})

    def test_two_hands_in_one_round_by_two_characters_wake_the_site_and_each_scores(self):
        a, b, c = self.ids[:3]
        engine = self.engine()
        for who, tile in ((a, (1, 1)), (b, (2, 1)), (c, (5, 1))):
            self.put(engine, who, "the_gallery", tile)
        engine._resolve_action(a, AgentAction(action="interact", target="brazier_west"))
        engine._resolve_action(b, AgentAction(action="interact", target="brazier_east"))
        engine._end_round_upkeep(3)
        done = self.events(engine, "site_done")
        self.assertEqual(sorted(e["actor_id"] for e in done), [a, b])
        self.assertTrue(all(e["payload"]["parties"] == [a, b] for e in done))
        self.assertIn("blazes end to end", done[0]["public_text"])
        for who in (a, b):
            self.assertEqual(engine.state["agents"][who]["score"], 4)
            self.assertEqual(engine.state["agents"][who]["score_breakdown"]["site_done"], 4)
        self.assertEqual(engine.state["agents"][c]["score"], 0)
        rec = engine.state["sites"]["gallery_braziers"]
        self.assertEqual((rec["status"], rec["done_round"], rec["done_by"]), ("done", 3, [a, b]))
        # done is done: no hand is legal any more, and a stale hand is no penalty
        self.assertFalse([e for e in self.obs(engine, c)["legal_actions"] if e["action"] == "interact"])
        engine._resolve_action(c, AgentAction(action="interact", target="brazier_west"))
        self.assertEqual(self.events(engine, "stale_action")[-1]["payload"]["reason"], "the site is already done")
        self.assertEqual(engine.state["agents"][c]["score"], 0)
        # everyone remembers a site waking
        obs = self.obs(engine, c)
        self.assertTrue(obs["room"]["sites"][0]["status"] == "done")

    def test_one_character_cannot_lend_both_hands_and_the_same_hand_twice_is_stale(self):
        a, b = self.ids[:2]
        engine = self.engine()
        self.put(engine, a, "the_gallery", (1, 1))
        self.put(engine, b, "the_gallery", (2, 1))
        engine._resolve_action(a, AgentAction(action="interact", target="brazier_west"))
        engine._resolve_action(b, AgentAction(action="interact", target="brazier_west"))
        self.assertEqual(self.events(engine, "stale_action")[-1]["payload"]["reason"], "that hand is already taken this round")
        self.assertEqual(engine.state["agents"][b]["score"], 0)
        engine._end_round_upkeep(3)
        self.assertEqual(engine.state["sites"]["gallery_braziers"]["status"], "waiting")
        self.assertEqual(len(self.events(engine, "site_lapsed")), 1)

    def test_the_bell_takes_three_and_a_monster_in_the_room_stops_a_hand(self):
        a, b, c, d = self.ids[:4]
        engine = self.engine(name="bell.db")
        for who, tile in ((a, (0, 0)), (b, (2, 1)), (c, (0, 2))):
            self.put(engine, who, "bell_tower", tile)
        for who, hand in ((a, "bell_rope_north"), (b, "bell_rope_east")):
            engine._resolve_action(who, AgentAction(action="interact", target=hand))
        engine._end_round_upkeep(3)
        self.assertEqual(engine.state["sites"]["tower_bell"]["status"], "waiting")
        engine.state["round"] = 4
        engine._round_events = []
        for who, hand in ((a, "bell_rope_north"), (b, "bell_rope_east"), (c, "bell_rope_south")):
            engine._resolve_action(who, AgentAction(action="interact", target=hand))
        engine._end_round_upkeep(4)
        self.assertEqual(engine.state["sites"]["tower_bell"]["done_by"], [a, b, c])
        self.assertEqual([engine.state["agents"][w]["score"] for w in (a, b, c)], [5, 5, 5])
        # a monster in the room holds the winch: no hand is legal, and a hand resolved anyway is stale
        engine = self.engine(name="hound.db")
        self.put(engine, d, "bone_well", (0, 1))
        engine.state["monsters"]["charnel_hound"]["room"] = "bone_well"
        engine.state["monsters"]["charnel_hound"]["tile"] = [1, 1]
        self.assertFalse([e for e in self.obs(engine, d)["legal_actions"] if e["action"] == "interact"])
        engine._resolve_action(d, AgentAction(action="interact", target="winch_crank"))
        self.assertEqual(self.events(engine, "stale_action")[-1]["payload"]["reason"], "a monster still holds the room")


class TheMockCoordinates(SiteTestCase):
    def test_two_mocks_in_the_gallery_take_different_hands_by_rank(self):
        a, b = self.ids[:2]
        engine = self.engine()
        self.put(engine, a, "the_gallery", (1, 1))
        self.put(engine, b, "the_gallery", (2, 1))
        mock = MockDecisionProvider()
        chosen = {who: mock._choose(self.obs(engine, who)) for who in (a, b)}
        self.assertEqual({chosen[a]["target"], chosen[b]["target"]}, {"brazier_west", "brazier_east"})
        self.assertTrue(all(c["action"] == "interact" for c in chosen.values()))
        # alone, the mock does not waste a turn on a two-hand site
        self.put(engine, b, "threshold", (2, 2))
        self.assertNotEqual(mock._choose(self.obs(engine, a))["action"], "interact")


if __name__ == "__main__":
    unittest.main()
