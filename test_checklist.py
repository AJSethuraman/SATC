#!/usr/bin/env python3
"""Tests for the document checklist tool. Standard library only."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import checklist
import sort_tax_docs


class EvaluateTests(unittest.TestCase):
    def test_received_missing_and_manual(self) -> None:
        client = {"expected_documents": ["W-2", "1099-INT", "Other"]}
        rows, extras = checklist.evaluate_client(client, checklist.DEFAULT_DOC_MAP, {"W2"})
        status = {r["document"]: r["status"] for r in rows}
        self.assertEqual(status["W-2"], checklist.STATUS_RECEIVED)
        self.assertEqual(status["1099-INT"], checklist.STATUS_MISSING)
        self.assertEqual(status["Other"], checklist.STATUS_MANUAL)  # unmapped label

    def test_extras_are_received_but_unexpected(self) -> None:
        client = {"expected_documents": ["W-2"]}
        _, extras = checklist.evaluate_client(client, checklist.DEFAULT_DOC_MAP, {"W2", "1099_R"})
        self.assertEqual(extras, ["1099_R"])

    def test_no_expected_documents_yields_no_rows(self) -> None:
        rows, extras = checklist.evaluate_client({}, checklist.DEFAULT_DOC_MAP, {"W2"})
        self.assertEqual(rows, [])
        self.assertEqual(extras, ["W2"])


class ReceivedCategoriesTests(unittest.TestCase):
    def test_only_nonempty_folders_count(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)
            w2 = output / sort_tax_docs.CATEGORY_FOLDERS["W2"]
            w2.mkdir(parents=True)
            (w2 / "a.pdf").write_text("x", encoding="utf-8")
            (output / sort_tax_docs.CATEGORY_FOLDERS["1099_R"]).mkdir(parents=True)  # empty
            received = checklist.received_categories(output)
            self.assertIn("W2", received)
            self.assertNotIn("1099_R", received)


class RunTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = checklist.run_checklist(Path(d))
            self.assertEqual(result["client_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_end_to_end_writes_checklists_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jordan Sample", "expected_documents": ["W-2", "1099-R"]}]),
                encoding="utf-8",
            )
            output = sort_tax_docs.setup_output_folders(folder)
            w2 = output / sort_tax_docs.CATEGORY_FOLDERS["W2"]
            w2.mkdir(parents=True, exist_ok=True)
            (w2 / "w2.pdf").write_text("x", encoding="utf-8")  # W-2 received, 1099-R missing

            result = checklist.run_checklist(folder)
            self.assertEqual(result["client_count"], 1)
            self.assertEqual(result["total_missing"], 1)
            # The summary CSV is the report; no duplicate per-client HTML page is emitted.
            self.assertEqual(Path(result["report_path"]).name, "checklist_summary.csv")
            self.assertFalse((output / "Checklists" / "Jordan_Sample_checklist.html").exists())

            summary = output / "Checklists" / "checklist_summary.csv"
            with summary.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            by_doc = {r["document"]: r["status"] for r in rows}
            self.assertEqual(by_doc["W-2"], checklist.STATUS_RECEIVED)
            self.assertEqual(by_doc["1099-R"], checklist.STATUS_MISSING)

            # The dynamic mapping file is created so it can be edited.
            self.assertTrue((folder / checklist.MAP_FILENAME).exists())


if __name__ == "__main__":
    unittest.main()
