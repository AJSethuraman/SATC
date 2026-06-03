#!/usr/bin/env python3
"""Tests for the year-rollover tool. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import year_rollover as yr


class RollForwardTests(unittest.TestCase):
    def test_static_fields_carry_per_year_fields_reset(self) -> None:
        client = {
            "client_name": "Jo Sample", "email": "jo@x.com", "filing_status": "Single",
            "expected_documents": ["W-2"], "services": ["state_return"], "spouse_name": "Pat",
            "tax_year": "2024", "total": "440.00", "line_items": [{"x": 1}], "amount_paid": "440.00",
            "form_8879_signed": True, "engagement_letter_signed": "2025-02-01", "return_filed": "2025-03-01",
        }
        carried = yr.roll_forward(client, "2025")
        # static carries
        self.assertEqual(carried["client_name"], "Jo Sample")
        self.assertEqual(carried["expected_documents"], ["W-2"])
        self.assertEqual(carried["spouse_name"], "Pat")  # custom field preserved
        # year bumped
        self.assertEqual(carried["tax_year"], "2025")
        # per-year status wiped
        for gone in ("total", "line_items", "amount_paid", "form_8879_signed",
                     "engagement_letter_signed", "return_filed"):
            self.assertNotIn(gone, carried)

    def test_next_year_from_clients(self) -> None:
        self.assertEqual(yr.next_year([{"tax_year": "2024"}, {"tax_year": "2023"}]), "2025")
        self.assertEqual(yr.next_year([{"tax_year": "2024"}], explicit="2030"), "2030")
        self.assertEqual(yr.next_year([{}]), str(date.today().year))


class RunTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("No clients", yr.run_rollover(Path(d))["summary"])

    def test_creates_next_year_folder_with_config(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(json.dumps([
                {"client_name": "Jo Sample", "tax_year": "2024", "total": "100.00", "paid": True},
                {"client_name": "Riley Carter", "tax_year": "2024"},
            ]), encoding="utf-8")
            (folder / "firm.json").write_text(json.dumps({"firm_name": "Acme"}), encoding="utf-8")

            result = yr.run_rollover(folder)
            self.assertEqual(result["new_year"], "2025")
            self.assertEqual(result["client_count"], 2)

            target = folder / "2025"
            self.assertTrue((target / "firm.json").exists())  # config copied
            carried = json.loads((target / "clients.json").read_text())
            self.assertEqual({c["tax_year"] for c in carried}, {"2025"})
            self.assertTrue(all("total" not in c and "paid" not in c for c in carried))

            # Re-running does not duplicate clients.
            again = yr.run_rollover(folder)
            self.assertEqual(again["client_count"], 0)


if __name__ == "__main__":
    unittest.main()
