#!/usr/bin/env python3
"""Tests for the filed-packet form reader.

Detection/matching/apply logic is pure (no PDF). The end-to-end run needs PyMuPDF
and is skipped when absent.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import packet_reader as pr

try:
    import fitz  # PyMuPDF

    HAVE_FITZ = True
except Exception:  # pragma: no cover - depends on environment
    HAVE_FITZ = False

SIGS = pr.DEFAULT_FORM_SIGNATURES


class DetectTests(unittest.TestCase):
    def test_detects_federal_schedule_and_states(self) -> None:
        text = "Form 1040\nSchedule A (Form 1040) Itemized Deductions\nOhio IT 1040\nRITA Form 37"
        keys = [s["key"] for s in pr.detect_forms(text, SIGS)]
        self.assertIn("base_1040", keys)
        self.assertIn("schedule_a", keys)
        self.assertEqual(keys.count("state_return"), 2)  # Ohio + RITA both detected

    def test_no_false_positive(self) -> None:
        self.assertEqual(pr.detect_forms("a cover letter with no form numbers", SIGS), [])


class MatchTests(unittest.TestCase):
    def test_matches_by_name_tokens_any_order(self) -> None:
        clients = [{"client_name": "Jordan Sample"}, {"client_name": "Samantha M. Mcandrew"}]
        self.assertEqual(pr.match_client("Return for Mcandrew, Samantha M", clients), 1)
        self.assertIsNone(pr.match_client("Return for Someone Else", clients))


class ApplyTests(unittest.TestCase):
    def test_two_states_bill_as_quantity_two(self) -> None:
        client = {"client_name": "A"}
        detected = pr.detect_forms("Form 1040\nOhio IT 1040\nRITA Form 37", SIGS)
        pr.apply_detected(client, detected)
        self.assertIn({"service": "state_return", "quantity": 2}, client["services"])
        self.assertEqual([r["return_type"] for r in client["returns"]],
                         ["Federal Income Tax", "Ohio Income Tax", "RITA Income Tax"])
        self.assertTrue(client["return_filed"])

    def test_preserves_inline_services(self) -> None:
        client = {"client_name": "A", "services": [{"description": "Advisory", "price": 100}]}
        pr.apply_detected(client, pr.detect_forms("Form 1040\nSchedule C (Form 1040) Profit", SIGS))
        self.assertIn("schedule_c", client["services"])
        self.assertIn({"description": "Advisory", "price": 100}, client["services"])


@unittest.skipUnless(HAVE_FITZ, "PyMuPDF not installed")
class RunTests(unittest.TestCase):
    def test_reads_packet_and_updates_client(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Samantha Mcandrew", "tax_year": "2025"}]), encoding="utf-8"
            )
            doc = fitz.open()
            for title in ["Form 1040  Samantha Mcandrew", "Schedule A (Form 1040)", "Ohio IT 1040"]:
                doc.new_page().insert_text((72, 700), title, fontsize=11)
            doc.save(folder / "mcandrew_return.pdf")
            doc.close()

            result = pr.run_packet_reader(folder)
            self.assertEqual(result["clients_updated"], 1)
            client = json.loads((folder / "clients.json").read_text())[0]
            self.assertTrue(client["return_filed"])
            self.assertIn("schedule_a", client["services"])
            self.assertTrue((folder / pr.SIGNATURES_FILENAME).exists())

    def test_unmatched_packet_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(json.dumps([{"client_name": "Jordan Sample"}]), encoding="utf-8")
            doc = fitz.open()
            doc.new_page().insert_text((72, 700), "Form 1040 for Someone Unrelated")
            doc.save(folder / "other.pdf")
            doc.close()
            result = pr.run_packet_reader(folder)
            self.assertEqual(result["clients_updated"], 0)
            self.assertEqual(result["unmatched"], 1)


if __name__ == "__main__":
    unittest.main()
