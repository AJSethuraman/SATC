#!/usr/bin/env python3
"""Tests for the records-retention archiver. Standard library only."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

import retention
import sort_tax_docs


class GatherTests(unittest.TestCase):
    def test_collects_slug_matched_artifacts_and_intake(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            output = sort_tax_docs.setup_output_folders(folder)
            generated = output / "Generated_Documents"
            generated.mkdir(parents=True, exist_ok=True)
            (generated / "Jordan_Sample_engagement_letter.html").write_text("x", encoding="utf-8")
            (generated / "Other_Client_invoice.html").write_text("x", encoding="utf-8")
            (folder / "Jordan_Sample_intake.json").write_text("{}", encoding="utf-8")

            files = retention.gather_client_files(folder, output, "Jordan_Sample")
            names = {p.name for p in files}
            self.assertIn("Jordan_Sample_engagement_letter.html", names)
            self.assertIn("Jordan_Sample_intake.json", names)
            self.assertNotIn("Other_Client_invoice.html", names)


class RunTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = retention.run_retention(Path(d))
            self.assertEqual(result["archived_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_single_client_includes_source_documents(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "Jordan Sample", "tax_year": "2024"}]), encoding="utf-8"
            )
            output = sort_tax_docs.setup_output_folders(folder)
            generated = output / "Generated_Documents"
            generated.mkdir(parents=True, exist_ok=True)
            (generated / "Jordan_Sample_engagement_letter.html").write_text("x", encoding="utf-8")
            w2 = output / sort_tax_docs.CATEGORY_FOLDERS["W2"]
            w2.mkdir(parents=True, exist_ok=True)
            (w2 / "w2.pdf").write_text("x", encoding="utf-8")

            result = retention.run_retention(folder, retention_years=3)
            self.assertEqual(result["archived_count"], 1)
            zip_path = Path(result["archives"][0])
            self.assertEqual(zip_path.name, "Jordan_Sample_2024.zip")
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                self.assertIn("MANIFEST.txt", names)
                self.assertTrue(any("Source_Documents/" in n for n in names))  # single client
                manifest = archive.read("MANIFEST.txt").decode()
            self.assertIn(str(date.today().year + 3), manifest)  # keep-until year

    def test_multiple_clients_skip_source_documents(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "clients.json").write_text(
                json.dumps([{"client_name": "A"}, {"client_name": "B"}]), encoding="utf-8"
            )
            output = sort_tax_docs.setup_output_folders(folder)
            generated = output / "Generated_Documents"
            generated.mkdir(parents=True, exist_ok=True)
            (generated / "A_engagement_letter.html").write_text("x", encoding="utf-8")
            (generated / "B_engagement_letter.html").write_text("x", encoding="utf-8")
            w2 = output / sort_tax_docs.CATEGORY_FOLDERS["W2"]
            w2.mkdir(parents=True, exist_ok=True)
            (w2 / "w2.pdf").write_text("x", encoding="utf-8")

            result = retention.run_retention(folder)
            self.assertEqual(result["archived_count"], 2)
            with zipfile.ZipFile(Path(result["archives"][0])) as archive:
                self.assertFalse(any("Source_Documents/" in n for n in archive.namelist()))
            self.assertTrue(any("not auto-attributed" in w for w in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
