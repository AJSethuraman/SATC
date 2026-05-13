#!/usr/bin/env python3
"""Fake-text tests for the local tax document sorter classifier.

These tests use made-up text snippets only. They do not include real taxpayer data.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import sort_tax_docs
from sort_tax_docs import classify_text


class ClassificationTests(unittest.TestCase):
    """Conservative rule/scoring tests for common classification risks."""

    def assert_category(self, text: str, expected: str) -> None:
        result = classify_text(text)
        self.assertEqual(result.category, expected, result)

    def test_clear_w2(self) -> None:
        self.assert_category("Form W-2 Wage and Tax Statement", "W2")

    def test_exact_form_w2_text(self) -> None:
        self.assert_category("Form W-2", "W2")

    def test_exact_wage_and_tax_statement_text(self) -> None:
        self.assert_category("Wage and Tax Statement", "W2")

    def test_w2_structural_text_without_exact_form_title(self) -> None:
        result = classify_text(
            "Employee's social security number Employer identification number "
            "Employer's name, address, and ZIP code Wages, tips, other compensation "
            "Federal income tax withheld Social security wages Medicare wages and tips"
        )
        self.assertEqual(result.category, "W2", result)
        self.assertIn("EMPLOYEE'S SOCIAL SECURITY NUMBER", result.matched_keywords)
        self.assertIn("WAGES, TIPS, OTHER COMPENSATION", result.matched_keywords)

    def test_generic_w2_words_do_not_classify_w2(self) -> None:
        self.assert_category("wages tax statement withholding employer employee state income", "NeedsReview")

    def test_clear_1099_nec(self) -> None:
        self.assert_category("Form 1099-NEC Nonemployee Compensation", "1099_NEC")

    def test_1099_nec_beats_w2_like_generic_text(self) -> None:
        result = classify_text(
            "1099-NEC Nonemployee Compensation recipient payer withholding state income W-2"
        )
        self.assertEqual(result.category, "1099_NEC", result)
        self.assertNotEqual(result.category, "W2")

    def test_1099_nec_nonemployee_and_state_income_not_w2(self) -> None:
        result = classify_text("Nonemployee Compensation State Income withholding employee")
        self.assertEqual(result.category, "1099_NEC", result)
        self.assertNotEqual(result.category, "W2")

    def test_wealthfront_brokerage_not_w2_or_misc(self) -> None:
        result = classify_text("Wealthfront Brokerage LLC Tax Information Statement")
        self.assertIn(result.category, {"Brokerage_1099B", "NeedsReview"}, result)
        self.assertNotIn(result.category, {"W2", "1099_MISC"})

    def test_consolidated_brokerage_beats_int_div(self) -> None:
        self.assert_category(
            "Consolidated 1099 1099-INT 1099-DIV 1099-B Proceeds From Broker Cost Basis",
            "Brokerage_1099B",
        )

    def test_1099_misc_requires_form_identifier(self) -> None:
        self.assert_category("Form 1099-MISC Miscellaneous Information", "1099_MISC")
        self.assert_category("Miscellaneous information payer recipient tax statement", "NeedsReview")

    def test_1098_tuition_not_mortgage(self) -> None:
        result = classify_text("Form 1098-T Tuition Statement")
        self.assertEqual(result.category, "1098_Tuition", result)
        self.assertNotEqual(result.category, "1098_Mortgage")

    def test_mortgage_interest_statement(self) -> None:
        self.assert_category("Form 1098 Mortgage Interest Statement", "1098_Mortgage")

    def test_generic_tax_statement_needs_review(self) -> None:
        self.assert_category(
            "tax statement recipient payer state income withholding address TIN federal ID",
            "NeedsReview",
        )

    def test_random_receipt_needs_review(self) -> None:
        self.assert_category("coffee receipt total customer service", "NeedsReview")


class PdfFallbackTests(unittest.TestCase):
    """Tests for selectable-PDF text vs OCR fallback behavior."""

    def run_fake_pdf(self, selectable_text: str, ocr_text: str):
        original_selectable = sort_tax_docs.extract_pdf_selectable_text
        original_ocr = sort_tax_docs.ocr_pdf
        calls = {"ocr": 0}

        def fake_ocr(_file_path: Path) -> str:
            calls["ocr"] += 1
            return ocr_text

        try:
            sort_tax_docs.extract_pdf_selectable_text = lambda _file_path: selectable_text
            sort_tax_docs.ocr_pdf = fake_ocr
            text, ocr_used, note, result, debug_parts = sort_tax_docs.extract_text_and_classification(
                Path("fake.pdf")
            )
            return text, ocr_used, note, result, debug_parts, calls
        finally:
            sort_tax_docs.extract_pdf_selectable_text = original_selectable
            sort_tax_docs.ocr_pdf = original_ocr

    def test_selectable_pdf_clear_w2_skips_ocr(self) -> None:
        _text, ocr_used, note, result, _debug_parts, calls = self.run_fake_pdf(
            "Form W-2 Wage and Tax Statement", ""
        )
        self.assertEqual(result.category, "W2")
        self.assertFalse(ocr_used)
        self.assertEqual(calls["ocr"], 0)
        self.assertIn("OCR skipped", note)

    def test_long_generic_selectable_pdf_runs_ocr(self) -> None:
        generic = " ".join(["recipient payer tax statement address customer service"] * 20)
        _text, ocr_used, _note, result, _debug_parts, calls = self.run_fake_pdf(generic, "")
        self.assertTrue(ocr_used)
        self.assertEqual(calls["ocr"], 1)
        self.assertEqual(result.category, "NeedsReview")

    def test_inconclusive_selectable_plus_ocr_w2(self) -> None:
        _text, ocr_used, note, result, _debug_parts, calls = self.run_fake_pdf(
            "recipient payer address", "Wage and Tax Statement"
        )
        self.assertTrue(ocr_used)
        self.assertEqual(calls["ocr"], 1)
        self.assertEqual(result.category, "W2")
        self.assertIn("OCR used", note)

    def test_combined_selectable_and_ocr_classifies_w2_structural(self) -> None:
        selectable = "Employee's social security number Employer identification number"
        ocr = "Wages, tips, other compensation Federal income tax withheld"
        text, ocr_used, _note, result, _debug_parts, _calls = self.run_fake_pdf(selectable, ocr)
        self.assertTrue(ocr_used)
        self.assertEqual(result.category, "W2")
        self.assertIn(selectable, text)
        self.assertIn(ocr, text)

    def test_pdf_selectable_and_ocr_inconclusive_needs_review(self) -> None:
        _text, ocr_used, _note, result, _debug_parts, _calls = self.run_fake_pdf(
            "recipient payer address", "coffee receipt total"
        )
        self.assertTrue(ocr_used)
        self.assertEqual(result.category, "NeedsReview")


if __name__ == "__main__":
    unittest.main()
