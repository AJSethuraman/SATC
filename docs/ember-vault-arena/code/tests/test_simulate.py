"""The balance simulator runs (tools/simulate.py). It is an observer over the
mock and not part of the engine, but a slice on 18 Sep 2026 left it unable
to start (a name it did not import) and nothing said so until it was run by
hand. One seed through the worker, the aggregate and the report is the
proof that it runs; the numbers themselves are read by a person."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import simulate  # noqa: E402
from arena import rules  # noqa: E402


class TheSimulatorRuns(unittest.TestCase):
    def test_one_seed_through_the_worker_the_aggregate_and_the_report(self):
        record = simulate._worker((1_000_000, 8, 0.0))
        self.assertTrue(record.get("ok"), record.get("error"))
        self.assertEqual(record["status"], "completed")
        self.assertTrue(record["audit_ok"])
        self.assertEqual(record["rounds"], rules.DEFAULT_MAX_ROUNDS)
        self.assertTrue(record["reached_act4"])
        summary = simulate.aggregate([record], 8)
        self.assertEqual(summary["matches_completed"], 1)
        self.assertEqual(summary["act4_rate"], 100.0)
        lines = simulate.report(summary, 8, 1.0)
        text = "\n".join(lines)
        self.assertIn("reached Act IV", text)
        for label, key, check in simulate.TARGETS:
            self.assertIn(key, summary, label)
            check(summary[key])  # evaluates without raising


if __name__ == "__main__":
    unittest.main()
