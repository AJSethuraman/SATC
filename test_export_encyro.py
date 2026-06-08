#!/usr/bin/env python3
"""Tests for the Export for Encyro tool.

The HTML->PDF and merge steps require PyMuPDF, so those tests are skipped when it
is absent. The no-data path is checked without any dependency.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import export_encyro

try:
    import fitz  # PyMuPDF

    HAVE_PDF_DEPS = True
except Exception:  # pragma: no cover - depends on environment
    HAVE_PDF_DEPS = False


class NoDepNeededTests(unittest.TestCase):
    def test_no_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = export_encyro.run_encyro_export(Path(d))
            self.assertEqual(result["client_count"], 0)
            self.assertIn("No clients", result["summary"])

    def test_upload_notes_lists_recipient_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            notes = Path(d) / "UPLOAD_NOTES.txt"
            client = {"client_name": "Sam Sample", "email": "sam@example.com"}
            export_encyro.write_upload_notes(notes, client, [Path("a.pdf")], Path("Sam_packet.pdf"))
            text = notes.read_text()
            self.assertIn("sam@example.com", text)
            self.assertIn("Sam_packet.pdf", text)
            self.assertIn("a.pdf", text)


@unittest.skipUnless(HAVE_PDF_DEPS, "PyMuPDF not installed")
class ConversionTests(unittest.TestCase):
    def test_html_to_pdf_keeps_text(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "doc.pdf"
            export_encyro.html_to_pdf("<h1>Engagement Letter</h1><p>Hello World</p>", out)
            with fitz.open(out) as doc:
                self.assertGreaterEqual(doc.page_count, 1)
                self.assertIn("Hello World", doc[0].get_text())

    def test_merge_pdfs_concatenates(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            paths = []
            for name in ("one", "two"):
                p = d / f"{name}.pdf"
                export_encyro.html_to_pdf(f"<p>{name}</p>", p)
                paths.append(p)
            merged = export_encyro.merge_pdfs(paths, d / "packet.pdf")
            with fitz.open(merged) as doc:
                self.assertEqual(doc.page_count, 2)
            self.assertIsNone(export_encyro.merge_pdfs([], d / "empty.pdf"))

    def test_end_to_end_packet(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            client = {"client_name": "Jordan Q. Sample", "email": "j@example.com"}
            (folder / "clients.json").write_text(json.dumps([client]), encoding="utf-8")
            generated = folder / "Organized_Tax_Documents" / "Generated_Documents"
            generated.mkdir(parents=True)
            (generated / "Jordan_Q._Sample_engagement_letter.html").write_text(
                "<h1>Engagement Letter</h1><p>Please sign.</p>", encoding="utf-8"
            )

            result = export_encyro.run_encyro_export(folder)
            self.assertEqual(result["client_count"], 1)
            self.assertEqual(len(result["packets"]), 1)

            client_dir = folder / "Organized_Tax_Documents" / "Encyro_Ready" / "Jordan_Q._Sample"
            self.assertTrue((client_dir / "Jordan_Q._Sample_packet.pdf").exists())
            self.assertTrue((client_dir / "Jordan_Q._Sample_engagement_letter.pdf").exists())
            self.assertTrue((client_dir / "UPLOAD_NOTES.txt").exists())


if __name__ == "__main__":
    unittest.main()
