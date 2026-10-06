"""The seed places loot within its declared sites (PRD §5.2, built 19 Sep
2026): the map's caches are the sites, what the map put in them is the
pool, and the seed deals the pool over the sites."""
from __future__ import annotations

import unittest
from collections import Counter
from copy import deepcopy

from arena import items, rules, world
from arena.demo import load_manifests


class SeededLoot(unittest.TestCase):
    def test_the_same_seed_deals_the_same_and_the_pool_never_changes(self):
        for seed in (1, 52, 20260724):
            self.assertEqual(rules.seeded_loot(seed), rules.seeded_loot(seed))
            deal = rules.seeded_loot(seed)
            self.assertEqual(sorted(deal), sorted(world.CACHES))
            self.assertEqual(Counter(deal.values()), Counter(world.CACHES.values()))
            self.assertTrue(all(items.is_known_item(i) for i in deal.values()))

    def test_different_seeds_deal_differently_and_the_state_carries_the_deal(self):
        deals = {seed: tuple(sorted(rules.seeded_loot(seed).items())) for seed in range(1, 13)}
        self.assertGreater(len(set(deals.values())), 1)
        manifests = load_manifests()
        for seed in (3, 52):
            state = rules.new_match_state(manifests, seed)
            self.assertEqual({r: c["item_id"] for r, c in state["caches"].items()}, rules.seeded_loot(seed))
            # nobody is told what a cache holds until it is found
            for who in sorted(state["agents"])[:2]:
                state["agents"][who]["room"] = "bell_tower"
                obs = rules.visible_observation(deepcopy(state), who, "lorekeeper", [])
                self.assertIsNone(obs["room"]["cache"]["contains"])
                self.assertFalse(obs["room"]["cache"]["found"])


if __name__ == "__main__":
    unittest.main()
