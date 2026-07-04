"""Audit-tape workbook tests."""

from __future__ import annotations

from satc.withholding import EstimatorInput, estimate
from satc.withholding.audit_tape import build_audit_tape


def _result_and_input():
    inp = EstimatorInput.from_dict({
        "filing_status": "single", "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": 78000,
                    "federal_tax_withheld_per_period": 9000, "pay_periods_remaining": 1},
    })
    return estimate(inp), inp


def test_audit_tape_has_one_sheet_and_key_figures():
    result, inp = _result_and_input()
    wb = build_audit_tape(result, inp)
    ws = wb["Withholding Estimate"]
    text = "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)

    assert "Withholding Estimate — Tax Year 2025" in text
    assert "Projection — Form 1040 walk" in text
    assert "Total tax liability" in text
    # The cited tax-law basis must appear (this is a tax workpaper).
    assert "Tax-law basis (from the SATC crosswalk)" in text
    assert "Rev. Proc. 2024-40" in text          # 2025 bracket/standard-deduction citation
    assert "IRC sec. 1411" in text               # NIIT citation we backfilled

    # The total-liability value lands as a real number, not text.
    numbers = [c.value for row in ws.iter_rows() for c in row
               if isinstance(c.value, (int, float))]
    assert float(result.breakdown.total_tax_liability) in numbers
