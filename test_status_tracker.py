#!/usr/bin/env python3
"""Tests for the engagement-letter and Form 8879 status trackers. Stdlib only."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import status_tracker as st


class EvaluateTests(unittest.TestCase):
    def test_declared_in_record_is_on_file(self) -> None:
        client = {"form_8879_signed": True}
        status, source = st.evaluate(client, "Jordan_Sample", st.FORM_8879_TRACKER, [])
        self.assertEqual(status, st.STATUS_ON_FILE)
        self.assertIn("declared", source)

    def test_matching_filename_is_on_file(self) -> None:
        files = [Path("/x/Jordan Sample - 8879 signed.pdf")]
        status, source = st.evaluate({}, "Jordan_Sample", st.FORM_8879_TRACKER, files)
        self.assertEqual(status, st.STATUS_ON_FILE)  # separators don't matter
        self.assertIn("8879", source)

    def test_keyword_must_match(self) -> None:
        files = [Path("/x/Jordan_Sample_engagement.pdf")]
        # engagement file should NOT satisfy the 8879 tracker
        status, _ = st.evaluate({}, "Jordan_Sample", st.FORM_8879_TRACKER, files)
        self.assertEqual(status, st.STATUS_OUTSTANDING)
        # ...but it satisfies the engagement tracker
        status2, _ = st.evaluate({}, "Jordan_Sample", st.ENGAGEMENT_TRACKER, files)
        self.assertEqual(status2, st.STATUS_ON_FILE)

    def test_other_client_file_does_not_match(self) -> None:
        files = [Path("/x/Someone_Else_8879.pdf")]
        status, _ = st.evaluate({}, "Jordan_Sample", st.FORM_8879_TRACKER, files)
        self.assertEqual(status, st.STATUS_OUTSTANDING)


class RunTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = st.run_engagement_tracker(Path(d))
            self.assertEqual(result["client_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_end_to_end_counts_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([
                    {"client_name": "Has It", "form_8879_signed": "2026-03-01"},
                    {"client_name": "Needs It"},
                ]),
                encoding="utf-8",
            )
            result = st.run_8879_tracker(folder)
            self.assertEqual(result["on_file_count"], 1)
            self.assertEqual(result["outstanding_count"], 1)

            report = Path(result["report_path"])
            self.assertTrue(report.exists())
            with report.open(encoding="utf-8") as handle:
                rows = {r["client"]: r["status"] for r in csv.DictReader(handle)}
            self.assertEqual(rows["Has_It"], st.STATUS_ON_FILE)
            self.assertEqual(rows["Needs_It"], st.STATUS_OUTSTANDING)
            self.assertTrue((Path(result["status_folder"]) / "form_8879_status.html").exists())

    def test_signed_documents_folder_is_searched(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jordan Sample"}]), encoding="utf-8"
            )
            output = st.sort_tax_docs.setup_output_folders(folder)
            signed = output / st.SIGNED_FOLDER_NAME
            signed.mkdir(parents=True, exist_ok=True)
            (signed / "Signed_Jordan_Sample_engagement_letter.pdf").write_text("x", encoding="utf-8")

            result = st.run_engagement_tracker(folder)
            self.assertEqual(result["on_file_count"], 1)


if __name__ == "__main__":
    unittest.main()
