"""PaystubReader + estimator bridge tests (no PDF — exercises read_text)."""

from __future__ import annotations

from decimal import Decimal

from satc.ingest.readers import PaystubReader
from satc.ingest.readers.paystub import (
    LABEL_EMPLOYER,
    LABEL_FED_WH_CURRENT,
    LABEL_FED_WH_YTD,
    LABEL_GROSS_CURRENT,
    LABEL_GROSS_YTD,
    LABEL_PAY_FREQUENCY,
    LABEL_RETIREMENT_CURRENT,
)
from satc.withholding import EstimatorInput, estimate, paystub_from_fields

SAMPLE = """\
ACME WIDGETS LLC
Employer Name: ACME WIDGETS LLC
Pay Frequency: Bi-Weekly
Pay Period: 06/01/2025 - 06/14/2025      Pay Date: 06/20/2025

Earnings              Current        YTD
Gross Pay             2,500.00       30,000.00
Regular Hours         80.00

Deductions            Current        YTD
401(k)                250.00         3,000.00
Federal Income Tax    300.00         3,600.00
Social Security       155.00         1,860.00
Medicare              36.25          435.00
"""


def test_reader_extracts_current_and_ytd_columns():
    result = PaystubReader().read_text(SAMPLE)
    f = result.labeled_fields
    assert f[LABEL_GROSS_CURRENT] == "2500.00"
    assert f[LABEL_GROSS_YTD] == "30000.00"
    assert f[LABEL_FED_WH_CURRENT] == "300.00"
    assert f[LABEL_FED_WH_YTD] == "3600.00"
    assert f[LABEL_RETIREMENT_CURRENT] == "250.00"
    assert f[LABEL_PAY_FREQUENCY] == "biweekly"
    assert f[LABEL_EMPLOYER] == "ACME WIDGETS LLC"


def test_confidence_employer_is_low_frequency_in_context_is_high():
    result = PaystubReader().read_text(SAMPLE)
    conf = result.confidence_map()
    assert conf[LABEL_EMPLOYER] == "LOW"          # free text => review
    assert conf[LABEL_GROSS_CURRENT] == "HIGH"    # strict money
    assert conf[LABEL_PAY_FREQUENCY] == "HIGH"    # on a "Pay Frequency:" line


def test_frequency_without_context_is_uncertain():
    result = PaystubReader().read_text("Net check direct deposit; paid biweekly schedule")
    assert result.labeled_fields[LABEL_PAY_FREQUENCY] == "biweekly"
    assert LABEL_PAY_FREQUENCY in result.uncertain_labels


def test_whole_dollar_without_cents_is_not_taken():
    # No comma groups and no cents => not a confident money value, so not emitted.
    result = PaystubReader().read_text("Gross Pay   2500")
    assert LABEL_GROSS_CURRENT not in result.labeled_fields


def test_bridge_derives_remaining_periods_and_taxable_wages():
    fields = PaystubReader().read_text(SAMPLE).labeled_fields
    stub = paystub_from_fields(fields)
    assert stub.pay_frequency == "biweekly"
    assert stub.pay_periods_remaining == 14          # 30000 YTD / 2500 = 12 elapsed of 26
    assert stub.taxable_wages_per_period == Decimal("2250")   # 2500 gross - 250 401(k)
    assert stub.ytd_taxable_wages == Decimal("27000")        # 30000 - 250*12
    assert stub.name == "ACME WIDGETS LLC"


def test_reader_output_drives_an_estimate_end_to_end():
    fields = PaystubReader().read_text(SAMPLE).labeled_fields
    stub = paystub_from_fields(fields)
    result = estimate(EstimatorInput(filing_status="single", paystub=stub, tax_year=2025))
    # 27,000 YTD taxable + 2,250 * 14 remaining = 58,500 projected wages.
    assert result.breakdown.projected_taxable_wages == Decimal("58500.00")
    # 3,600 YTD withheld + 300 * 14 remaining = 7,800 projected withholding.
    assert result.recommendation.projected_withholding_current_rate == Decimal("7800.00")
