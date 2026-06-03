#!/usr/bin/env python3
"""Tests for Data Diagnostics, Payments/AR, and the Filing tracker. Stdlib only."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import diagnostics
import extract_form_data
import payments
import sort_tax_docs
import status_tracker as st


class DiagnosticsTests(unittest.TestCase):
    def test_w2_withholding_exceeds_wages_flagged(self) -> None:
        rows = [{"source_file": "w2.pdf", "page": "1", "needs_review": "False",
                 "box1_wages": "1000.00", "box2_federal_withholding": "1500.00"}]
        findings = diagnostics.check_rows("W2", rows)
        self.assertTrue(any("exceeds wages" in f["issue"] for f in findings))

    def test_flagged_row_and_missing_primary(self) -> None:
        rows = [{"source_file": "a.pdf", "page": "1", "needs_review": "True",
                 "box1_wages": "", "box2_federal_withholding": ""}]
        findings = diagnostics.check_rows("W2", rows)
        issues = " ".join(f["issue"] for f in findings)
        self.assertIn("Flagged during extraction", issues)
        self.assertIn("No primary amount", issues)

    def test_duplicate_detection(self) -> None:
        rows = [
            {"source_file": "a.pdf", "page": "1", "needs_review": "False", "box1_wages": "500.00"},
            {"source_file": "b.pdf", "page": "1", "needs_review": "False", "box1_wages": "500.00"},
        ]
        findings = diagnostics.check_rows("W2", rows)
        self.assertTrue(any("duplicate" in f["issue"].lower() for f in findings))

    def test_run_without_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = diagnostics.run_diagnostics(Path(d))
            self.assertIn("No extracted data", result["summary"])

    def test_run_reads_drake_csv(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            output = sort_tax_docs.setup_output_folders(folder)
            drake = output / extract_form_data.DRAKE_EXPORT_FOLDER_NAME
            drake.mkdir(parents=True, exist_ok=True)
            with (drake / "W2.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["source_file", "page", "needs_review",
                                                            "box1_wages", "box2_federal_withholding"])
                writer.writeheader()
                writer.writerow({"source_file": "w2.pdf", "page": "1", "needs_review": "False",
                                 "box1_wages": "1000.00", "box2_federal_withholding": "2000.00"})
            result = diagnostics.run_diagnostics(folder)
            self.assertGreaterEqual(result["warning_count"], 1)
            self.assertTrue(Path(result["report_path"]).exists())


class PaymentsTests(unittest.TestCase):
    def test_paid_partial_unpaid(self) -> None:
        paid = payments.evaluate_client({"total": "100.00", "amount_paid": "100.00"})
        self.assertEqual(paid["status"], payments.STATUS_PAID)
        partial = payments.evaluate_client({"total": "100.00", "amount_paid": "40.00"})
        self.assertEqual(partial["status"], payments.STATUS_PARTIAL)
        self.assertEqual(partial["balance"], 60.0)
        unpaid = payments.evaluate_client({"total": "100.00"})
        self.assertEqual(unpaid["status"], payments.STATUS_UNPAID)

    def test_aging_bucket(self) -> None:
        today = date(2026, 6, 1)
        row = payments.evaluate_client({"total": "100.00", "invoice_date": "2026-01-01"}, today)
        self.assertEqual(row["bucket"], "90+")

    def test_run_totals_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(json.dumps([
                {"client_name": "A", "total": "200.00", "amount_paid": "200.00"},
                {"client_name": "B", "total": "100.00"},
            ]), encoding="utf-8")
            result = payments.run_payments(folder)
            self.assertEqual(result["total_billed"], "300.00")
            self.assertEqual(result["total_collected"], "200.00")
            self.assertEqual(result["total_outstanding"], "100.00")
            self.assertTrue(Path(result["report_path"]).exists())


class FilingTrackerTests(unittest.TestCase):
    def test_declared_filed_is_on_file(self) -> None:
        status, _ = st.evaluate({"return_filed": "2026-04-10"}, "A", st.FILING_TRACKER, [])
        self.assertEqual(status, st.STATUS_ON_FILE)

    def test_filed_filename_matches(self) -> None:
        files = [Path("/x/Jordan_Sample_1040_filed.pdf")]
        status, _ = st.evaluate({}, "Jordan_Sample", st.FILING_TRACKER, files)
        self.assertEqual(status, st.STATUS_ON_FILE)


if __name__ == "__main__":
    unittest.main()
