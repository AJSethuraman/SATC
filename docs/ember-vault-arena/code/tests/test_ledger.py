"""The call ledger tells the truth about tokens and money (PRD §5.31).

Three defects the forge's 12 Sep 2026 smoke re-run exposed, each pinned here:
the ledger printed only the uncached input count (2, for a 2,062-token
prompt); cache creation was never recorded; and cost_of subtracted the cached
count from the uncached one, zeroing the tokens billed at full rate.
"""
from __future__ import annotations

import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from arena.cli import print_ledger
from arena.providers import AnthropicProvider
from arena.storage import SCHEMA, ArenaStore


class _Store:
    def __init__(self, decisions):
        self._decisions = decisions

    def replay_bundle(self, match_id):
        return {"decisions": self._decisions}


def _decision(**over):
    base = {
        "round_no": 1, "agent_id": "dask", "validity": "valid", "error_kind": None,
        "latency_ms": 7844.0, "input_tokens": 2, "output_tokens": 341,
        "cached_tokens": 2060, "cache_creation_tokens": 0, "cost_usd": 0.0525,
        "fallback_reason": None, "provider": "agent_sdk", "model": "claude-opus-5",
    }
    base.update(over)
    return base


class CostArithmeticTests(unittest.TestCase):
    def test_three_input_counts_are_priced_separately(self):
        # the forge's dask call: 2 uncached, 2,060 read from cache, 341 out
        provider = AnthropicProvider(client=object(), model="claude-opus-5")
        cost = provider.cost_of("claude-opus-5", 2, 341, 2060)
        self.assertAlmostEqual(cost, (2 * 5.0 + 2060 * 0.5 + 341 * 25.0) / 1e6)
        # a cold call that writes the cache pays 1.25x on the written tokens
        cold = provider.cost_of("claude-opus-5", 2, 341, 0, cache_creation=2060)
        self.assertAlmostEqual(cold, (2 * 5.0 + 2060 * 6.25 + 341 * 25.0) / 1e6)
        self.assertGreater(cold, cost)

    def test_the_forge_arena_probe_reconciles_to_the_cent(self):
        # runs/20260912T090748Z-sdk-probe-arena.md: two models, a 1-hour cache write
        provider = AnthropicProvider(client=object(), model="claude-opus-5")
        opus = provider.cost_of("claude-opus-5", 2, 342, 2060, cache_creation=3945, cache_creation_1h=3945)
        self.assertAlmostEqual(opus, 0.049040, places=6)
        model_usage = {
            "claude-haiku-4-5-20251001": {"inputTokens": 3403, "outputTokens": 16, "cacheReadInputTokens": 0,
                                          "cacheCreationInputTokens": 0, "canonicalModel": "claude-haiku-4-5"},
            "claude-opus-5": {"inputTokens": 2, "outputTokens": 342, "cacheReadInputTokens": 2060,
                              "cacheCreationInputTokens": 3945, "canonicalModel": "claude-opus-5"},
        }
        self.assertAlmostEqual(provider.price_usage(model_usage, one_hour_tokens=3945), 0.052523, places=6)
        # a five-minute write is the cheaper 1.25x
        five = provider.cost_of("claude-opus-5", 2, 342, 2060, cache_creation=3945, cache_creation_1h=0)
        self.assertLess(five, opus)

    def test_an_unknown_model_prices_nothing_rather_than_guessing(self):
        provider = AnthropicProvider(client=object(), model="claude-opus-5")
        # "opus" is the alias the SDK route asks for; the table is keyed by id
        self.assertIsNone(provider.cost_of("opus", 2, 341, 2060))


class LedgerPrintTests(unittest.TestCase):
    def _printed(self, decisions):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print_ledger(_Store(decisions), "m")
        return out.getvalue()

    def test_cached_and_written_tokens_are_columns(self):
        text = self._printed([_decision(), _decision(agent_id="fen", cache_creation_tokens=2060, cached_tokens=0)])
        header = text.splitlines()[0]
        for column in ("in", "cached", "wrote", "out"):
            self.assertIn(column, header.split())
        dask = next(line for line in text.splitlines() if " dask " in line)
        self.assertIn("2060", dask)   # the cache reads the old ledger hid as `in 2`
        fen = next(line for line in text.splitlines() if " fen " in line)
        self.assertIn("2060", fen)    # cache creation, previously unrecorded

    def test_totals_line_names_the_helper_model_cost_hidden_in_usage_json(self):
        import json
        breakdown = json.dumps({
            "claude-haiku-4-5-20251001": {"costUSD": 0.003488, "canonicalModel": "claude-haiku-4-5"},
            "claude-opus-5": {"costUSD": 0.048605, "canonicalModel": "claude-opus-5"},
        })
        text = self._printed([_decision(usage_json=breakdown, cost_usd=0.052093),
                              _decision(agent_id="fen", usage_json=breakdown, cost_usd=0.052093)])
        self.assertIn("other models billed: $0.0070 (in usage_json)", text)
        # without a breakdown the line stays as it was
        self.assertNotIn("other models", self._printed([_decision()]))

    def test_totals_line_sums_every_count(self):
        text = self._printed([_decision(), _decision(agent_id="fen", output_tokens=484)])
        self.assertIn("tokens: in 4; cached 4120; cache written 0; out 825", text)
        self.assertIn("answered by the model: 2 of 2", text)


class MigrationTests(unittest.TestCase):
    def test_a_database_from_before_the_column_gains_it_on_open(self):
        old_schema = (SCHEMA.replace("    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,\n", "")
                      .replace("    cache_creation_1h_tokens INTEGER NOT NULL DEFAULT 0,\n", "")
                      .replace("    usage_json TEXT,\n", ""))
        self.assertNotEqual(old_schema, SCHEMA)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "arena.db"
            conn = sqlite3.connect(path)
            conn.executescript(old_schema)
            conn.commit()
            before = {row[1] for row in conn.execute("PRAGMA table_info(decisions)")}
            conn.close()
            self.assertNotIn("cache_creation_tokens", before)
            store = ArenaStore(path)
            after = {row[1] for row in store.conn.execute("PRAGMA table_info(decisions)")}
            self.assertIn("cache_creation_tokens", after)
            self.assertIn("cache_creation_1h_tokens", after)
            self.assertIn("usage_json", after)
            store.close()
            # opening again is harmless
            ArenaStore(path).close()


if __name__ == "__main__":
    unittest.main()
