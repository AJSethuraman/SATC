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
    Household,
    OtherIncome,
    OtherPayments,
    Paystub,
    Schedule1A,
)
from satc.withholding.intake import paystub_from_fields
from satc.withholding.tax_data import TaxYearNotOnFile, available_years, staleness

__all__ = [
    "estimate", "available_years", "staleness", "TaxYearNotOnFile", "paystub_from_fields",
    "EstimatorInput", "EstimateResult",
    "Paystub", "Household", "Schedule1A", "OtherIncome", "Adjustments", "Deductions", "Credits", "OtherPayments",
]
