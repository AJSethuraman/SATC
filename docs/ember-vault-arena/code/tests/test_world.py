"""The Ember Vault is drawn once, in world.py, and the engine reads it
(PRD §5.2, built 18 Sep 2026): sixteen locations, five monsters, eight caches,
a relic on the floor, a contraction that seals the ring and the deeps from
the outside in and leaves the last round in the Vault, the Egress and the
Parapet. The registry validates itself at import, and this file proves the
validator catches a broken map."""
from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from arena import combat, grid, rules, world
from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.providers import MockDecisionProvider, opening_template
from arena.storage import ArenaStore


class TheRegistry(unittest.TestCase):
    def test_sixteen_locations_five_monsters_eight_caches_and_the_relic(self):
        self.assertEqual(len(world.ROOMS), 16)
        self.assertEqual(len(world.MONSTERS), 5)
        self.assertEqual(len(world.CACHES), 8)
        self.assertEqual(world.FLOOR_ITEMS, {"reliquary": ["marrow_reliquary"]})
        self.assertEqual(world.SEAL_ROOMS, ("ironwood_gate", "ossuary_gate"))
        self.assertEqual(world.ROOM_ORDER[:5], ("threshold", "ironwood_gate", "ossuary_gate", "vault", "egress"))
        # every module reads the same drawing
        self.assertEqual(set(rules.ROOMS), set(world.ROOMS))
        self.assertEqual(set(grid.ROOM_GRIDS), set(world.ROOMS))
        self.assertEqual(set(grid.ROOM_PROPS), set(world.ROOMS))
        self.assertEqual(set(combat.ROOM_REACTIONS), set(world.ROOMS))
        self.assertEqual(set(rules.MONSTER_TEMPLATES), set(world.MONSTERS))
        self.assertEqual(grid.MONSTER_REACH["crown_warden"], 2)
        for rid, r in world.ROOMS.items():
            self.assertEqual(rules.ROOMS[rid]["neighbors"], r["neighbors"])
            self.assertEqual(grid.door_tile(rid, r["neighbors"][0]), tuple(r["grid"]["doors"][r["neighbors"][0]]))

    def test_the_validator_catches_a_broken_map(self):
        def broken(mutate):
            saved = deepcopy(world.ROOMS), deepcopy(world.MONSTERS), world.CONTRACTION_SCHEDULE
            try:
                mutate()
                with self.assertRaises(ValueError):
                    world.validate()
            finally:
                world.ROOMS.clear(); world.ROOMS.update(saved[0])
                world.MONSTERS.clear(); world.MONSTERS.update(saved[1])
                world.CONTRACTION_SCHEDULE = saved[2]
            world.validate()

        broken(lambda: world.ROOMS["parapet"]["neighbors"].append("vault"))              # not symmetric
        broken(lambda: world.ROOMS["parapet"]["grid"]["doors"].pop("egress"))             # no door
        broken(lambda: world.ROOMS["bone_well"]["grid"]["features"].update(cache=(1, 0)))  # on the well mouth
        broken(lambda: world.MONSTERS["charnel_hound"].update(room="bone_well"))           # not its room's guardian
        broken(lambda: world.ROOMS["parapet"].update(layout=(13.0, 0.0)))                  # on top of the egress
        broken(lambda: setattr(world, "CONTRACTION_SCHEDULE", world.CONTRACTION_SCHEDULE + ((47, "vault"),)))
        # a room left open at the end but cut off from the Vault
        broken(lambda: setattr(world, "CONTRACTION_SCHEDULE", tuple(x for x in world.CONTRACTION_SCHEDULE if x[1] != "bone_well")))

    def test_contraction_seals_from_the_outside_in_and_leaves_the_last_round_connected(self):
        sealed = [room for _, room in world.CONTRACTION_SCHEDULE]
        self.assertEqual(set(world.ROOMS) - set(sealed), set(world.NEVER_SEALS))
        self.assertEqual(rules.sealing_rooms_for_round(46), ["root_hollow", "reliquary"])
        self.assertEqual(rules.sealing_rooms_for_round(47), ["ironwood_gate", "ossuary_gate"])
        self.assertEqual(rules.sealing_rooms_for_round(36), [])
        for round_no, _ in world.CONTRACTION_SCHEDULE:
            self.assertEqual(rules.act_for_round(round_no), rules.CONTRACTION_ACT)
        self.assertLess(max(r for r, _ in world.CONTRACTION_SCHEDULE), rules.DEFAULT_MAX_ROUNDS)


class TheEngineReadsIt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        store = ArenaStore(Path(cls.tmp.name) / "w.db")
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=True)
        cls.match_id = engine.run(load_manifests(), seed=52)
        cls.bundle = store.replay_bundle(cls.match_id)
        cls.audit = store.verify_audit(cls.match_id)
        store.close()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_match_state_carries_the_whole_map_and_the_relic(self):
        first = self.bundle["snapshots"][0]["state"]
        self.assertEqual(len(first["rooms"]), 16)
        self.assertEqual(sorted(first["monsters"]), sorted(world.MONSTERS))
        self.assertEqual(sorted(first["caches"]), sorted(world.CACHES))
        self.assertEqual(first["floor_items"]["reliquary"], ["marrow_reliquary"])
        self.assertEqual(sorted(first["floor_items"]), sorted(world.ROOMS))
        self.assertTrue(all(a["room"] == "threshold" for a in first["agents"].values()))
        self.assertTrue(self.audit["valid"])

    def test_by_the_last_round_everyone_alive_is_where_the_map_says(self):
        last = next(s["state"] for s in self.bundle["snapshots"] if s["round_no"] == rules.DEFAULT_MAX_ROUNDS and s["phase"] == "start")
        self.assertEqual(sorted(last["contraction"]["sealed"]), sorted(room for _, room in world.CONTRACTION_SCHEDULE))
        for a in last["agents"].values():
            if a["status"] == "active":
                self.assertIn(a["room"], world.NEVER_SEALS, a["id"])
        kinds = [e["event_type"] for e in self.bundle["events"]]
        self.assertEqual(kinds.count("room_sealed"), len(world.CONTRACTION_SCHEDULE))
        # the deep rooms were walked: the mock reached beyond July's five
        visited = set()
        for a in last["agents"].values():
            visited.update(a["visited"])
        self.assertGreater(len(visited), 5, sorted(visited))

    def test_the_opening_names_every_room_and_every_monster_inside_the_cap(self):
        opening = next(e for e in self.bundle["events"] if e["event_type"] == "match_opening")
        text = opening["public_text"]
        self.assertEqual(text, opening_template(opening["payload"]["facts"]))
        first = self.bundle["snapshots"][0]["state"]
        for r in first["rooms"].values():
            self.assertIn(r["name"], text)
        for m in first["monsters"].values():
            self.assertIn(m["name"], text)
        self.assertIsNone(opening["payload"]["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
