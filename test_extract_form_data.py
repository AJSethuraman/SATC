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

    def test_w2_whole_dollar_amounts_without_cents(self) -> None:
        # Many real W-2s print whole-dollar box values with no comma or cents.
        text = (
            "Form W-2 Wage and Tax Statement 2024 "
            "1 Wages, tips, other compensation 52000 "
            "2 Federal income tax withheld 8000 "
            "3 Social security wages 53000"
        )
        result = extract_form_fields("W2", text)
        self.assertEqual(result.values["box1_wages"], "52000")
        self.assertEqual(result.values["box2_federal_withholding"], "8000")
        self.assertEqual(result.values["box3_social_security_wages"], "53000")
        self.assertFalse(result.needs_review, result)


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


FAKE_1099_G = (
    "Form 1099-G 2024 Certain Government Payments "
    "PAYER'S TIN 11-2223333 RECIPIENT'S TIN 555-66-7777 "
    "1 Unemployment compensation 4800.00 "
    "2 State or local income tax refunds, credits, or offsets 320.00 "
    "4 Federal income tax withheld 480.00"
)

FAKE_1099_K = (
    "Form 1099-K 2024 Payment Card and Third Party Network Transactions "
    "PAYER'S TIN 33-4445555 PAYEE'S TIN 666-77-8888 "
    "1a Gross amount of payment card/third party network transactions 27500.00 "
    "4 Federal income tax withheld 0.00"
)

FAKE_SSA_1099 = (
    "Form SSA-1099 2024 Social Security Benefit Statement "
    "Beneficiary's social security number 777-88-9999 "
    "Box 3 Benefits paid in 2024 24000.00 "
    "Box 5 Net benefits for 2024 24000.00 "
    "Box 6 Voluntary federal income tax withheld 2400.00"
)

FAKE_1098_MORTGAGE = (
    "Form 1098 Mortgage Interest Statement 2024 "
    "RECIPIENT'S/LENDER'S TIN 44-5556666 PAYER'S/BORROWER'S TIN 888-99-0000 "
    "1 Mortgage interest received from payer(s)/borrower(s) 13250.75 "
    "5 Mortgage insurance premiums 600.00 "
    "6 Points paid on purchase of principal residence 1500.00"
)

FAKE_1098_T = (
    "Form 1098-T 2024 Tuition Statement "
    "FILER'S TIN 22-1112222 Student's TIN 123-00-4567 "
    "1 Payments received for qualified tuition and related expenses 12000.00 "
    "5 Scholarships or grants 4000.00"
)

FAKE_K1 = (
    "Schedule K-1 Form 1065 2024 Partner's Share of Income "
    "Partnership's employer identification number 99-8887777 "
    "Partner's identifying number 321-54-9876 "
    "1 Ordinary business income (loss) 45000.00 "
    "2 Net rental real estate income (loss) 5000.00 "
    "5 Interest income 250.00"
)


class MoreFormsTests(unittest.TestCase):
    def test_1099_g(self) -> None:
        result = extract_form_fields("1099_G", FAKE_1099_G)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["box1_unemployment_compensation"], "4800.00")
        self.assertEqual(result.values["box2_state_income_tax_refunds"], "320.00")

    def test_1099_k(self) -> None:
        result = extract_form_fields("1099_K", FAKE_1099_K)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["box1a_gross_amount"], "27500.00")

    def test_ssa_1099(self) -> None:
        result = extract_form_fields("SSA_1099", FAKE_SSA_1099)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["beneficiary_ssn"], "777-88-9999")
        self.assertEqual(result.values["box5_net_benefits"], "24000.00")
        self.assertEqual(result.values["box6_voluntary_withholding"], "2400.00")

    def test_1098_mortgage(self) -> None:
        result = extract_form_fields("1098_Mortgage", FAKE_1098_MORTGAGE)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["box1_mortgage_interest"], "13250.75")
        self.assertEqual(result.values["box6_points_paid"], "1500.00")

    def test_1098_tuition(self) -> None:
        result = extract_form_fields("1098_Tuition", FAKE_1098_T)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["box1_payments_received"], "12000.00")
        self.assertEqual(result.values["box5_scholarships_or_grants"], "4000.00")

    def test_k1(self) -> None:
        result = extract_form_fields("K1", FAKE_K1)
        self.assertFalse(result.needs_review, result)
        self.assertEqual(result.values["entity_ein"], "99-8887777")
        self.assertEqual(result.values["box1_ordinary_business_income"], "45000.00")
        self.assertEqual(result.values["box5_interest_income"], "250.00")

    def test_brokerage_always_flagged(self) -> None:
        result = extract_form_fields(
            "Brokerage_1099B",
            "Consolidated 1099-B 2024 PAYER'S TIN 12-3456789 Proceeds 10000.00 Cost basis 8000.00",
        )
        # 1099-B is transactional, so it is always flagged for manual review.
        self.assertTrue(result.needs_review, result)
        self.assertIn("transactional", " ".join(result.notes).lower())


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
