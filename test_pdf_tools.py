#!/usr/bin/env python3
"""Tests for pdf_utils and the PDF Merge/Split tool.

The PDF operations require PyMuPDF and are skipped when it is absent; the
no-op path needs no dependency.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pdf_tools

try:
    import fitz  # PyMuPDF
    import pdf_utils

    HAVE_FITZ = True
except Exception:  # pragma: no cover - depends on environment
    HAVE_FITZ = False


def _make_pdf(path: Path, pages: int, label: str = "x") -> None:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page().insert_text((72, 700), label)
    doc.save(str(path))
    doc.close()


class NoOpTests(unittest.TestCase):
    def test_no_pdf_tools_folder_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            result = pdf_tools.run_pdf_tools(Path(d))
            self.assertIn("nothing to do", result["summary"])
            self.assertEqual(result["split_files"], 0)


@unittest.skipUnless(HAVE_FITZ, "PyMuPDF not installed")
class PdfUtilsTests(unittest.TestCase):
    def test_merge(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_pdf(d / "a.pdf", 1)
            _make_pdf(d / "b.pdf", 2)
            out = pdf_utils.merge_pdfs([d / "a.pdf", d / "b.pdf"], d / "m.pdf")
            with fitz.open(out) as doc:
                self.assertEqual(doc.page_count, 3)
            self.assertIsNone(pdf_utils.merge_pdfs([], d / "empty.pdf"))

    def test_split(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_pdf(d / "doc.pdf", 3)
            outputs = pdf_utils.split_pdf(d / "doc.pdf", d)
            self.assertEqual(len(outputs), 3)
            for path in outputs:
                with fitz.open(path) as page_doc:
                    self.assertEqual(page_doc.page_count, 1)


@unittest.skipUnless(HAVE_FITZ, "PyMuPDF not installed")
class PdfToolsRunTests(unittest.TestCase):
    def test_merge_and_split_via_convention_folders(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            merge_dir = folder / "PDF_Tools" / "merge"
            split_dir = folder / "PDF_Tools" / "split"
            merge_dir.mkdir(parents=True)
            split_dir.mkdir(parents=True)
            _make_pdf(merge_dir / "one.pdf", 1)
            _make_pdf(merge_dir / "two.pdf", 1)
            _make_pdf(split_dir / "big.pdf", 4)

            result = pdf_tools.run_pdf_tools(folder)
            self.assertEqual(result["merged_inputs"], 2)
            self.assertEqual(result["split_files"], 4)
            output = folder / "PDF_Tools" / "output"
            self.assertTrue((output / "merged.pdf").exists())
            with fitz.open(output / "merged.pdf") as merged:
                self.assertEqual(merged.page_count, 2)
            self.assertEqual(len(list(output.glob("big_p*.pdf"))), 4)


if __name__ == "__main__":
    unittest.main()
