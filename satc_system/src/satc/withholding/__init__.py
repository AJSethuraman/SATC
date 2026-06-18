"""Federal withholding estimator — ported from the standalone ``twe`` tool onto
SATC's dated tax-law crosswalk.

From paystub figures plus other income/adjustments/deductions/credits it projects
the full-year federal tax liability and recommends a per-paycheck withholding
change (Form W-4 line 4c style), with an optional estimated-tax safe-harbor target.
"""

from __future__ import annotations

from satc.withholding.engine import estimate
from satc.withholding.models import (
    Adjustments,
    Credits,
    Deductions,
    EstimateResult,
    EstimatorInput,
    OtherIncome,
    OtherPayments,
    Paystub,
)
from satc.withholding.tax_data import available_years

__all__ = [
    "estimate", "available_years", "EstimatorInput", "EstimateResult",
    "Paystub", "OtherIncome", "Adjustments", "Deductions", "Credits", "OtherPayments",
]
