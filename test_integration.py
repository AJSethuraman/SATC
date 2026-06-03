#!/usr/bin/env python3
"""End-to-end integration tests for the local tax tools.

These generate fake text PDFs with PyMuPDF and run the real sort + extract
pipeline (no mocking). They require the runtime dependencies (PyMuPDF, pandas,
openpyxl) and are skipped automatically when those are not installed. No real
taxpayer data is used. OCR is never triggered because the fake PDFs contain
selectable text that classifies on its own.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import fitz  # PyMuPDF
    import openpyxl  # noqa: F401  (used indirectly by pandas to read xlsx)
    import pandas as pd

    HAVE_RUNTIME_DEPS = True
except Exception:  # pragma: no cover - depends on environment
    HAVE_RUNTIME_DEPS = False

if HAVE_RUNTIME_DEPS:
    import extract_form_data
    import sort_tax_docs

W2 = """Form W-2 Wage and Tax Statement 2024
a Employee's social security number 123-45-6789
b Employer identification number 12-3456789
1 Wages, tips, other compensation 52000.00
2 Federal income tax withheld 8000.00
3 Social security wages 53000.00
4 Social security tax withheld 3286.00
5 Medicare wages and tips 53000.00
6 Medicare tax withheld 768.50"""

NEC = """Form 1099-NEC Nonemployee Compensation 2024
PAYER'S TIN 98-7654321 RECIPIENT'S TIN 111-22-3333
1 Nonemployee compensation 15000.00
4 Federal income tax withheld 1500.00"""

INT = """Form 1099-INT 2024 Interest Income
PAYER'S TIN 22-3334444 RECIPIENT'S TIN 222-33-4444
1 Interest income 1234.56
4 Federal income tax withheld 100.00"""

PENSION = """Form 1099-R 2024 Distributions From Pensions
PAYER'S TIN 44-5556666 RECIPIENT'S TIN 444-55-6666
1 Gross distribution 30000.00
2a Taxable amount 28000.00
4 Federal income tax withheld 3000.00
7 Distribution code 7"""


def _make_pdf(path: Path, pages: list[str]) -> None:
    document = fitz.open()
    for body in pages:
        page = document.new_page()
        y = 60
        for line in body.strip().splitlines():
            page.insert_text((50, y), line.strip(), fontsize=11)
            y += 18
    document.save(str(path))
    document.close()


@unittest.skipUnless(HAVE_RUNTIME_DEPS, "PyMuPDF/pandas/openpyxl not installed")
class PipelineIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        _make_pdf(self.folder / "w2_only.pdf", [W2])
        _make_pdf(self.folder / "nec_only.pdf", [NEC])
        _make_pdf(self.folder / "client_combined.pdf", [W2, INT, PENSION])

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_sort_splits_combined_pdf(self) -> None:
        result = sort_tax_docs.run_sort(self.folder, split_combined=True)
        output = Path(result["output_folder"])
        relative = {str(p.relative_to(output)) for p in output.rglob("*.pdf")}

        # Combined PDF is split into one filed PDF per form.
        self.assertIn("01_W2/W2_client_combined_p1.pdf", relative)
        self.assertIn("04_1099_INT_DIV/1099_INT_DIV_client_combined_p2.pdf", relative)
        self.assertIn("05_1099_R/1099_R_client_combined_p3.pdf", relative)
        # Single-form PDFs are filed whole.
        self.assertIn("01_W2/W2_w2_only.pdf", relative)
        self.assertIn("02_1099_NEC/1099_NEC_nec_only.pdf", relative)
        # The original combined PDF is left in place (split copies, never moves).
        self.assertTrue((self.folder / "client_combined.pdf").exists())

    def test_same_form_multipage_filed_whole(self) -> None:
        # A single W-2 spanning two pages must not be split into two files.
        _make_pdf(self.folder / "two_page_w2.pdf", [W2, W2])
        result = sort_tax_docs.run_sort(self.folder, split_combined=True)
        output = Path(result["output_folder"])
        filed = [p.name for p in output.rglob("*two_page_w2*.pdf")]
        self.assertEqual(filed, ["W2_two_page_w2.pdf"])

    def test_extraction_reads_fields_per_page(self) -> None:
        result = extract_form_data.run_extraction(self.folder)
        sheets = pd.read_excel(result["data_path"], sheet_name=None)

        # The combined PDF contributes one row per form page.
        w2 = sheets["W2"].fillna("")
        self.assertEqual(len(w2), 2)  # w2_only + combined page 1
        self.assertTrue((w2["Box 1 Wages"].astype(float) == 52000.0).all())

        pension = sheets["1099_R"].fillna("")
        self.assertEqual(float(pension.iloc[0]["Box 1 Gross Distribution"]), 30000.0)
        self.assertEqual(str(pension.iloc[0]["Box 7 Distribution Code"]), "7")

        interest = sheets["1099_INT_DIV"].fillna("")
        self.assertEqual(float(interest.iloc[0]["Interest Income (1099-INT Box 1)"]), 1234.56)

        self.assertEqual(result["review_count"], 0)


if __name__ == "__main__":
    unittest.main()
