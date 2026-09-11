from __future__ import annotations

"""The golden replay (PRD §5.40, seam 2): a fresh mock match on seed 52 must
reproduce the pinned snapshot hashes, placements and audit validity, with no
model call. A rule change that moves the match must regenerate the pin with
tools/write_golden.py and say so; a change that moves it by accident fails
here."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from write_golden import GOLDEN, golden_record  # noqa: E402


class GoldenReplayTests(unittest.TestCase):
    def test_seed_52_reproduces_the_pinned_match(self):
        pinned = json.loads(GOLDEN.read_text(encoding="utf-8"))
        fresh = golden_record()
        self.assertEqual(fresh["ruleset_version"], pinned["ruleset_version"])
        self.assertEqual(fresh["action_schema_version"], pinned["action_schema_version"])
        self.assertEqual(fresh["prompt_version"], pinned["prompt_version"])
        self.assertEqual(fresh["snapshot_hashes"], pinned["snapshot_hashes"])
        self.assertEqual(fresh["placements"], pinned["placements"])
        self.assertEqual(fresh["final_scores"], pinned["final_scores"])
        self.assertEqual(fresh["winner"], pinned["winner"])
        self.assertEqual(fresh["event_count"], pinned["event_count"])
        self.assertTrue(fresh["audit_valid"])

    def test_the_pin_is_not_empty(self):
        pinned = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertGreater(len(pinned["snapshot_hashes"]), 10)
        self.assertEqual(len(pinned["placements"]), 8)


if __name__ == "__main__":
    unittest.main()
