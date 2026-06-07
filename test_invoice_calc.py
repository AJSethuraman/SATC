#!/usr/bin/env python3
"""Tests for the form-driven invoice fee calculator. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import invoice_calc

SCHEDULE = invoice_calc.DEFAULT_FEE_SCHEDULE


def _discount_total(lines):
    return sum(invoice_calc.core.parse_money(d["amount"]) for d in lines)


class ComputeTests(unittest.TestCase):
    def test_documents_map_to_schedules(self) -> None:
        # K-1 implies Schedule E ($130); W-2 needs no extra form. Base 1040 is $170.
        client = {"expected_documents": ["W-2", "K-1"]}
        items, subtotal, discounts, total, warnings = invoice_calc.compute_line_items(client, SCHEDULE)
        descriptions = [i["description"] for i in items]
        self.assertTrue(any("Form 1040" in d for d in descriptions))
        self.assertTrue(any("Schedule E" in d for d in descriptions))
        self.assertEqual(subtotal, 300.0)        # 170 + 130
        self.assertEqual(discounts, [])           # K-1 is not a simple filer
        self.assertEqual(total, 300.0)
        self.assertEqual(warnings, [])

    def test_initial_plus_additional_pricing(self) -> None:
        # State return: 30 first + 30 each additional -> 2 states = 60. Base 170.
        client = {"services": [{"service": "state_return", "quantity": 2}]}
        items, subtotal, discounts, total, _ = invoice_calc.compute_line_items(client, SCHEDULE)
        self.assertEqual(subtotal, 230.0)         # 170 + 60
        self.assertTrue(any("(x2)" in i["description"] for i in items))
        # only base + state -> still a simple filer -> express discount applies
        self.assertEqual(_discount_total(discounts), -40.0)
        self.assertEqual(total, 190.0)

    def test_inline_service_and_unknown_warns(self) -> None:
        client = {"services": [{"description": "Custom advisory", "price": 125.0}, {"service": "mystery"}]}
        items, subtotal, _discounts, total, warnings = invoice_calc.compute_line_items(client, {})
        self.assertEqual(subtotal, 125.0)
        self.assertEqual(total, 125.0)
        self.assertEqual(len(items), 1)
        self.assertTrue(any("mystery" in w for w in warnings))


class DiscountTests(unittest.TestCase):
    def test_w2_only_is_express(self) -> None:
        _items, subtotal, discounts, total, _ = invoice_calc.compute_line_items({"expected_documents": ["W-2"]}, SCHEDULE)
        self.assertEqual(subtotal, 170.0)
        self.assertEqual([d["key"] for d in discounts], ["express"])
        self.assertEqual(total, 130.0)

    def test_self_employed_is_not_express(self) -> None:
        _items, _subtotal, discounts, _total, _ = invoice_calc.compute_line_items(
            {"expected_documents": ["W-2", "1099-NEC"]}, SCHEDULE)
        self.assertEqual(discounts, [])

    def test_express_is_deterministic_ignores_flag(self) -> None:
        # An 'express' field on the record must NOT change anything; only the rule matters.
        forced = invoice_calc.compute_line_items({"expected_documents": ["1099-NEC"], "express": True}, SCHEDULE)
        self.assertEqual(forced[2], [])  # still not a simple filer
        kept = invoice_calc.compute_line_items({"expected_documents": ["W-2"], "express": False}, SCHEDULE)
        self.assertEqual([d["key"] for d in kept[2]], ["express"])  # still express

    def test_friends_family_when_listed(self) -> None:
        client = {"expected_documents": ["W-2", "1099-NEC"], "discounts": ["friends_family"]}
        _items, subtotal, discounts, total, _ = invoice_calc.compute_line_items(client, SCHEDULE)
        self.assertEqual([d["key"] for d in discounts], ["friends_family"])  # 20% of subtotal
        self.assertEqual(_discount_total(discounts), -round(subtotal * 0.20, 2))

    def test_loyalty_automatic_for_returning(self) -> None:
        # Returning (e.g. carried by Year Rollover) gets loyalty; a complex one isn't express.
        client = {"expected_documents": ["W-2", "1099-NEC"], "returning": True}
        _items, _subtotal, discounts, _total, _ = invoice_calc.compute_line_items(client, SCHEDULE)
        self.assertEqual([d["key"] for d in discounts], ["loyalty"])

    def test_discounts_stack(self) -> None:
        # A returning simple filer who is also friends & family gets all three.
        client = {"expected_documents": ["W-2"], "returning": True, "discounts": ["friends_family"]}
        _items, subtotal, discounts, total, _ = invoice_calc.compute_line_items(client, SCHEDULE)
        self.assertEqual([d["key"] for d in discounts], ["express", "friends_family", "loyalty"])
        # 170 - 40 - 34 (20%) - 25 = 71
        self.assertEqual(total, 71.0)


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
            self.assertEqual(result["discounted_count"], 1)
            self.assertEqual(result["grand_total"], "130.00")  # 170 - 40 express

            client = json.loads((folder / "clients.json").read_text())[0]
            self.assertEqual(client["subtotal"], "170.00")
            self.assertEqual(client["discount"], "-40.00")
            self.assertEqual(client["total"], "130.00")
            self.assertEqual([d["description"] for d in client["discount_lines"]],
                             ["Express discount - simple filer"])
            self.assertTrue(client["express_applied"])
            self.assertTrue((folder / invoice_calc.FEE_SCHEDULE_FILENAME).exists())
            self.assertTrue(Path(result["worksheet_path"]).exists())


if __name__ == "__main__":
    unittest.main()
