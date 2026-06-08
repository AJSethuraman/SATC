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

    def test_state_address_does_not_falsely_detect_state_return(self) -> None:
        # A federal-only return whose address mentions a state must NOT detect that
        # state's return (the state name alone isn't enough; the title phrase is).
        text = "Form 1040 U.S. Individual Income Tax Return\nJohn Doe, 123 Main St, Columbus, Ohio 43004"
        labels = [s["label"] for s in pr.detect_forms(text, SIGS)]
        self.assertIn("Federal Income Tax", labels)
        self.assertNotIn("Ohio Income Tax", labels)

    def test_comprehensive_state_detection(self) -> None:
        for header, expected in [
            ("California Resident Income Tax Return Form 540", "California Income Tax"),
            ("Form IT-201 New York State Resident Income Tax Return", "New York Income Tax"),
            ("Illinois Department of Revenue IL-1040 Individual Income Tax Return", "Illinois Income Tax"),
            ("Massachusetts Resident Income Tax Return Form 1", "Massachusetts Income Tax"),
            ("Arizona Form 140 Resident Personal Income Tax Return", "Arizona Income Tax"),
            ("Virginia Form 760 Resident Individual Income Tax Return", "Virginia Income Tax"),
            ("North Carolina D-400 Individual Income Tax Return", "North Carolina Income Tax"),
        ]:
            labels = [s["label"] for s in pr.detect_forms(header, SIGS)]
            self.assertIn(expected, labels, header)


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

    def test_existing_quantity_service_not_double_billed(self) -> None:
        # A pre-existing {"service": state_return, "quantity": 2} must not duplicate when
        # the packet also detects a state return -- the packet quantity is authoritative.
        client = {"client_name": "A", "services": [{"service": "state_return", "quantity": 2}]}
        pr.apply_detected(client, pr.detect_forms("Form 1040\nOhio IT 1040\nRITA Form 37", SIGS))
        state_entries = [s for s in client["services"]
                         if s == "state_return" or (isinstance(s, dict) and s.get("service") == "state_return")]
        self.assertEqual(len(state_entries), 1)              # exactly one state_return entry
        self.assertEqual(state_entries[0], {"service": "state_return", "quantity": 2})  # 2 detected


class MatchSpecificityTests(unittest.TestCase):
    def test_picks_most_specific_client(self) -> None:
        clients = [{"client_name": "Jo Sample"}, {"client_name": "Jo Sample Jr"}]
        self.assertEqual(pr.match_client("Return for Jo Sample Jr", clients), 1)   # Jr, not Sr
        self.assertEqual(pr.match_client("Return for Jo Sample", clients), 0)      # Sr only


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
