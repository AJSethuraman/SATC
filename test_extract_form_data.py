#!/usr/bin/env python3
"""Fake-text tests for the local tax form data extractor.

These tests use made-up text snippets only. They do not include real taxpayer
data. They exercise the label-anchored regex extraction for each supported form.
"""

from __future__ import annotations

import unittest

from extract_form_data import extract_form_fields

# Realistic-looking but entirely fake form text. Amounts print cents the way the
# real forms do, identifiers use clearly invalid sample numbers.
FAKE_W2 = (
    "Form W-2 Wage and Tax Statement 2024 "
    "a Employee's social security number 123-45-6789 "
    "b Employer identification number 12-3456789 "
    "1 Wages, tips, other compensation 52000.00 "
    "2 Federal income tax withheld 8000.00 "
    "3 Social security wages 53000.00 "
    "4 Social security tax withheld 3286.00 "
    "5 Medicare wages and tips 53000.00 "
    "6 Medicare tax withheld 768.50"
)

FAKE_1099_NEC = (
    "Form 1099-NEC Nonemployee Compensation 2024 "
    "PAYER'S TIN 98-7654321 RECIPIENT'S TIN 111-22-3333 "
    "1 Nonemployee compensation 15000.00 "
    "4 Federal income tax withheld 1500.00"
)

FAKE_1099_INT = (
    "Form 1099-INT 2023 Interest Income "
    "PAYER'S TIN 22-3334444 RECIPIENT'S TIN 222-33-4444 "
    "1 Interest income 1234.56 "
    "4 Federal income tax withheld 100.00"
)

FAKE_1099_DIV = (
    "Form 1099-DIV 2023 Dividends and Distributions "
    "PAYER'S TIN 55-6667777 RECIPIENT'S TIN 333-44-5555 "
    "1a Total ordinary dividends 2500.00 "
    "1b Qualified dividends 2000.00 "
    "2a Total capital gain distr 500.00"
)

FAKE_1099_R = (
    "Form 1099-R 2024 Distributions From Pensions "
    "PAYER'S TIN 44-5556666 RECIPIENT'S TIN 444-55-6666 "
    "1 Gross distribution 30000.00 "
    "2a Taxable amount 28000.00 "
    "4 Federal income tax withheld 3000.00 "
    "7 Distribution code 7"
)


class W2ExtractionTests(unittest.TestCase):
    def test_w2_core_fields(self) -> None:
        result = extract_form_fields("W2", FAKE_W2)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["tax_year"], "2024")
        self.assertEqual(result.values["employer_ein"], "12-3456789")
        self.assertEqual(result.values["employee_ssn"], "123-45-6789")
        self.assertEqual(result.values["box1_wages"], "52000.00")
        self.assertEqual(result.values["box2_federal_withholding"], "8000.00")
        self.assertEqual(result.values["box3_social_security_wages"], "53000.00")
        self.assertEqual(result.values["box4_social_security_tax"], "3286.00")
        self.assertEqual(result.values["box6_medicare_tax"], "768.50")

    def test_w2_missing_wages_flagged(self) -> None:
        result = extract_form_fields(
            "W2", "Form W-2 Wage and Tax Statement Employee's social security number 123-45-6789"
        )
        self.assertEqual(result.values["box1_wages"], "")
        self.assertTrue(result.needs_review, result)


class NecExtractionTests(unittest.TestCase):
    def test_nec_value_not_taken_from_title(self) -> None:
        result = extract_form_fields("1099_NEC", FAKE_1099_NEC)
        self.assertFalse(result.needs_review, result)
        # The form title repeats "Nonemployee Compensation"; the year next to it
        # must not be captured as the box 1 amount.
        self.assertEqual(result.values["box1_nonemployee_compensation"], "15000.00")
        self.assertEqual(result.values["box4_federal_withholding"], "1500.00")
        self.assertEqual(result.values["payer_tin"], "98-7654321")
        self.assertEqual(result.values["recipient_tin"], "111-22-3333")


class IntDivExtractionTests(unittest.TestCase):
    def test_int_fields(self) -> None:
        result = extract_form_fields("1099_INT_DIV", FAKE_1099_INT)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["interest_income"], "1234.56")
        self.assertEqual(result.values["ordinary_dividends"], "")

    def test_div_fields(self) -> None:
        result = extract_form_fields("1099_INT_DIV", FAKE_1099_DIV)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["ordinary_dividends"], "2500.00")
        self.assertEqual(result.values["qualified_dividends"], "2000.00")
        self.assertEqual(result.values["total_capital_gain"], "500.00")
        self.assertEqual(result.values["interest_income"], "")


class RExtractionTests(unittest.TestCase):
    def test_r_fields_including_code(self) -> None:
        result = extract_form_fields("1099_R", FAKE_1099_R)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["box1_gross_distribution"], "30000.00")
        self.assertEqual(result.values["box2a_taxable_amount"], "28000.00")
        self.assertEqual(result.values["box4_federal_withholding"], "3000.00")
        self.assertEqual(result.values["box7_distribution_code"], "7")


class AmountFormatTests(unittest.TestCase):
    def test_thousands_separator_and_cents(self) -> None:
        result = extract_form_fields(
            "W2", "Wages, tips, other compensation 1,234,567.89 Federal income tax withheld 0.00"
        )
        self.assertEqual(result.values["box1_wages"], "1234567.89")
        self.assertEqual(result.values["box2_federal_withholding"], "0.00")

    def test_bare_integer_is_not_an_amount(self) -> None:
        # No decimal and no thousands separator -> not treated as a dollar value.
        result = extract_form_fields("W2", "Wages, tips, other compensation 5")
        self.assertEqual(result.values["box1_wages"], "")


if __name__ == "__main__":
    unittest.main()
