#!/usr/bin/env python3
"""Tests for the form-driven invoice fee calculator. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import invoice_calc

SCHEDULE = invoice_calc.DEFAULT_FEE_SCHEDULE


class ComputeTests(unittest.TestCase):
    def test_documents_map_to_schedules(self) -> None:
        # K-1 implies Schedule E ($130); W-2 needs no extra form. Base 1040 is $170.
        client = {"expected_documents": ["W-2", "K-1"]}
        items, subtotal, discount, total, warnings = invoice_calc.compute_line_items(client, SCHEDULE)
        descriptions = [i["description"] for i in items]
        self.assertTrue(any("Form 1040" in d for d in descriptions))
        self.assertTrue(any("Schedule E" in d for d in descriptions))
        self.assertEqual(subtotal, 300.0)        # 170 + 130
        self.assertEqual(discount, 0.0)           # K-1 is not a simple filer
        self.assertEqual(total, 300.0)
        self.assertEqual(warnings, [])

    def test_initial_plus_additional_pricing(self) -> None:
        # State return: 30 first + 30 each additional -> 2 states = 60. Base 170.
        client = {"services": [{"service": "state_return", "quantity": 2}]}
        items, subtotal, discount, total, _ = invoice_calc.compute_line_items(client, SCHEDULE)
        self.assertEqual(subtotal, 230.0)         # 170 + 60
        self.assertTrue(any("(x2)" in i["description"] for i in items))
        # only base + state -> still a simple filer -> express discount applies
        self.assertEqual(discount, -40.0)
        self.assertEqual(total, 190.0)

    def test_inline_service_and_unknown_warns(self) -> None:
        client = {"services": [{"description": "Custom advisory", "price": 125.0}, {"service": "mystery"}]}
        items, subtotal, _discount, total, warnings = invoice_calc.compute_line_items(client, {})
        self.assertEqual(subtotal, 125.0)
        self.assertEqual(total, 125.0)
        self.assertEqual(len(items), 1)
        self.assertTrue(any("mystery" in w for w in warnings))


class ExpressTests(unittest.TestCase):
    def test_w2_only_is_express(self) -> None:
        client = {"expected_documents": ["W-2"]}
        _items, subtotal, discount, total, _ = invoice_calc.compute_line_items(client, SCHEDULE)
        self.assertEqual(subtotal, 170.0)
        self.assertEqual(discount, -40.0)
        self.assertEqual(total, 130.0)

    def test_simple_interest_filer_is_express(self) -> None:
        client = {"expected_documents": ["W-2", "1099-INT"]}  # 1099-INT -> Schedule B ($5)
        _items, subtotal, discount, total, _ = invoice_calc.compute_line_items(client, SCHEDULE)
        self.assertEqual(subtotal, 175.0)
        self.assertEqual(discount, -40.0)

    def test_self_employed_is_not_express(self) -> None:
        client = {"expected_documents": ["W-2", "1099-NEC"]}  # -> Schedule C + SE
        _items, _subtotal, discount, _total, _ = invoice_calc.compute_line_items(client, SCHEDULE)
        self.assertEqual(discount, 0.0)

    def test_explicit_express_flag_overrides(self) -> None:
        # A complex filer can be forced express, and a simple one can opt out.
        forced = invoice_calc.compute_line_items({"expected_documents": ["1099-NEC"], "express": True}, SCHEDULE)
        self.assertEqual(forced[2], -40.0)
        opted_out = invoice_calc.compute_line_items({"expected_documents": ["W-2"], "express": False}, SCHEDULE)
        self.assertEqual(opted_out[2], 0.0)

    def test_percent_discount(self) -> None:
        schedule = {invoice_calc.BASE_FEE_KEY: {"description": "1040", "price": 200.0},
                    invoice_calc.EXPRESS_KEY: {"description": "Express", "percent": 10}}
        _items, subtotal, discount, total, _ = invoice_calc.compute_line_items({"expected_documents": ["W-2"]}, schedule)
        self.assertEqual((subtotal, discount, total), (200.0, -20.0, 180.0))


class RunTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = invoice_calc.run_invoice_calc(Path(d))
            self.assertEqual(result["invoiced_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_writes_totals_and_express_into_clients_json(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jordan Sample", "expected_documents": ["W-2"]}]),
                encoding="utf-8",
            )
            result = invoice_calc.run_invoice_calc(folder)
            self.assertEqual(result["invoiced_count"], 1)
            self.assertEqual(result["express_count"], 1)
            self.assertEqual(result["grand_total"], "130.00")  # 170 - 40 express

            client = json.loads((folder / "clients.json").read_text())[0]
            self.assertEqual(client["subtotal"], "170.00")
            self.assertEqual(client["discount"], "-40.00")
            self.assertEqual(client["total"], "130.00")
            self.assertTrue(client["express_applied"])
            self.assertTrue((folder / invoice_calc.FEE_SCHEDULE_FILENAME).exists())
            self.assertTrue(Path(result["worksheet_path"]).exists())


if __name__ == "__main__":
    unittest.main()
