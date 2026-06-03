#!/usr/bin/env python3
"""Tests for per-client folders (batch) mode.

Uses only standard-library tools (intake, checklist, invoice) so no third-party
dependencies are required.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import batch
import generate_documents


class DiscoveryTests(unittest.TestCase):
    def test_roster_drives_subfolders(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            (parent / "clients.json").write_text(
                json.dumps([{"client_name": "Jordan Sample"}, {"client_name": "Riley Carter"}]),
                encoding="utf-8",
            )
            entries = batch.client_folders(parent)
            slugs = [slug for slug, _, _ in entries]
            self.assertEqual(slugs, ["Jordan_Sample", "Riley_Carter"])
            self.assertEqual(entries[0][1], parent / "Jordan_Sample")

    def test_duplicate_names_get_distinct_subfolders(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            (parent / "clients.json").write_text(
                json.dumps([{"client_name": "John Smith"}, {"client_name": "John Smith"}]),
                encoding="utf-8",
            )
            slugs = [slug for slug, _, _ in batch.client_folders(parent)]
            self.assertEqual(slugs, ["John_Smith", "John_Smith_2"])  # no shared subfolder

    def test_subfolders_without_roster(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            (parent / "Alice").mkdir()
            (parent / "Bob").mkdir()
            (parent / "Organized_Tax_Documents").mkdir()  # ignored
            entries = batch.client_folders(parent)
            slugs = sorted(slug for slug, _, _ in entries)
            self.assertEqual(slugs, ["Alice", "Bob"])


class RunBatchTests(unittest.TestCase):
    def test_each_client_processed_and_config_propagated(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            (parent / "clients.json").write_text(
                json.dumps([
                    {"client_name": "Jordan Sample", "expected_documents": ["W-2"]},
                    {"client_name": "Riley Carter", "expected_documents": ["K-1"]},
                ]),
                encoding="utf-8",
            )
            (parent / "firm.json").write_text(json.dumps({"firm_name": "Acme Tax"}), encoding="utf-8")

            result = batch.run_batch(parent, ["intake", "checklist"])
            self.assertEqual(result["client_count"], 2)

            jordan = parent / "Jordan_Sample"
            self.assertTrue((jordan / "clients.json").exists())
            self.assertTrue((jordan / "firm.json").exists())  # propagated
            self.assertTrue((jordan / "Organized_Tax_Documents" / "Checklists").exists())
            # the per-client data file holds only that client
            data = json.loads((jordan / "clients.json").read_text())
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["client_name"], "Jordan Sample")

    def test_invoice_results_aggregate_back_to_parent(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            (parent / "clients.json").write_text(
                json.dumps([
                    {"client_name": "Jordan Sample", "expected_documents": ["W-2"]},
                    {"client_name": "Riley Carter", "expected_documents": ["K-1"]},
                ]),
                encoding="utf-8",
            )
            batch.run_batch(parent, ["invoice"])
            parent_clients = json.loads((parent / "clients.json").read_text())
            self.assertEqual(len(parent_clients), 2)
            # each client now has computed line items and a total (propagated up)
            self.assertTrue(all("total" in c for c in parent_clients))
            jordan = next(c for c in parent_clients if c["client_name"] == "Jordan Sample")
            self.assertEqual(jordan["total"], "215.00")  # 200 base + 15 W-2


if __name__ == "__main__":
    unittest.main()
