"""Standings are public in every digest (PRD §5.5, §5.22): everyone by
score with status and who carries the Crown, and nothing private."""
from __future__ import annotations

import unittest
from copy import deepcopy

from arena import rules
from arena.demo import load_manifests


class Standings(unittest.TestCase):
    def test_everyone_by_score_with_status_and_the_crown_and_nothing_private(self):
        manifests = load_manifests()
        state = rules.new_match_state(manifests, 9)
        ids = sorted(state["agents"])
        state["agents"][ids[2]]["score"] = 12
        state["agents"][ids[2]]["score_breakdown"] = {"seal_activated": 5, "cache_first_find": 2, "site_done": 5}
        state["agents"][ids[5]]["score"] = 7
        state["agents"][ids[7]]["status"] = "eliminated"
        state["agents"][ids[7]]["eliminated_round"] = 4
        state["agents"][ids[5]]["note"] = {"objective": "secret plan", "reads": []}
        state["crown"].update({"status": "carried", "carrier_id": ids[5], "room": None})
        for who in ids[:3]:
            obs = rules.visible_observation(deepcopy(state), who, "lorekeeper", [])
            rows = obs["standings"]
            self.assertEqual([r["id"] for r in rows][:2], [ids[2], ids[5]])
            self.assertEqual([r["rank"] for r in rows], list(range(1, 9)))
            self.assertEqual(next(r for r in rows if r["id"] == ids[7])["status"], "eliminated")
            self.assertEqual(next(r for r in rows if r["id"] == ids[7])["eliminated_round"], 4)
            self.assertEqual([r["id"] for r in rows if r["carrying_crown"]], [ids[5]])
            self.assertEqual(set(rows[0]), {"rank", "id", "name", "build", "status", "score", "carrying_crown", "eliminated_round"})
            text = str(rows)
            self.assertNotIn("secret plan", text)
            self.assertNotIn("seal_activated", text)
            self.assertNotIn("threshold", text)


if __name__ == "__main__":
    unittest.main()
