#!/usr/bin/env python3
"""Fake-text tests for the local tax document sorter classifier.

These tests use made-up text snippets only. They do not include real taxpayer data.
"""

from __future__ import annotations

import unittest

from sort_tax_docs import classify_text


class ClassificationTests(unittest.TestCase):
    """Conservative rule/scoring tests for common classification risks."""

    def assert_category(self, text: str, expected: str) -> None:
        result = classify_text(text)
        self.assertEqual(result.category, expected, result)

    def test_clear_w2(self) -> None:
        self.assert_category("Form W-2 Wage and Tax Statement", "W2")

    def test_clear_1099_nec(self) -> None:
        self.assert_category("Form 1099-NEC Nonemployee Compensation", "1099_NEC")

    def test_1099_nec_beats_w2_like_generic_text(self) -> None:
        result = classify_text(
            "1099-NEC Nonemployee Compensation recipient payer withholding state income W-2"
        )
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


if __name__ == "__main__":
    unittest.main()
