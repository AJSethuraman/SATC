#!/usr/bin/env python3
"""Tests for the invoice fee calculator. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import invoice_calc


class ComputeTests(unittest.TestCase):
    def test_base_plus_expected_documents(self) -> None:
        client = {"expected_documents": ["W-2", "K-1"]}
        items, total, warnings = invoice_calc.compute_line_items(client, invoice_calc.DEFAULT_FEE_SCHEDULE)
        descriptions = [i["description"] for i in items]
        self.assertIn("Form 1040 preparation", descriptions)  # base
        self.assertIn("Schedule K-1", descriptions)
        # 200 base + 15 (W-2) + 90 (K-1) = 305
        self.assertEqual(total, 305.0)
        self.assertEqual(warnings, [])

    def test_explicit_service_with_quantity(self) -> None:
        client = {"services": [{"service": "state_return", "quantity": 2}]}
        # No base? base is always added when present in schedule.
        items, total, _ = invoice_calc.compute_line_items(client, invoice_calc.DEFAULT_FEE_SCHEDULE)
        # base 200 + state 75 x2 = 350
        self.assertEqual(total, 350.0)
        self.assertTrue(any("(x2)" in i["description"] for i in items))

    def test_inline_service_and_unknown_warns(self) -> None:
        schedule = {}  # no base, nothing known
        client = {
            "services": [
                {"description": "Custom advisory", "price": 125.0},
                {"service": "mystery"},
            ]
        }
        items, total, warnings = invoice_calc.compute_line_items(client, schedule)
        self.assertEqual(total, 125.0)
        self.assertEqual(len(items), 1)
        self.assertTrue(any("mystery" in w for w in warnings))


class RunTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = invoice_calc.run_invoice_calc(Path(d))
            self.assertEqual(result["invoiced_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_writes_line_items_into_clients_json(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jordan Sample", "expected_documents": ["W-2"]}]),
                encoding="utf-8",
            )
            result = invoice_calc.run_invoice_calc(folder)
            self.assertEqual(result["invoiced_count"], 1)
            self.assertEqual(result["grand_total"], "215.00")  # 200 + 15

            clients = json.loads((folder / "clients.json").read_text())
            self.assertIn("line_items", clients[0])
            self.assertEqual(clients[0]["total"], "215.00")
            self.assertTrue((folder / invoice_calc.FEE_SCHEDULE_FILENAME).exists())
            worksheet = Path(result["worksheet_path"])
            self.assertTrue(worksheet.exists())


if __name__ == "__main__":
    unittest.main()
