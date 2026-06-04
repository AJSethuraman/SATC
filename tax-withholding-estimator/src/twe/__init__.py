"""Tax Withholding Estimator (twe).

A local-first, dependency-free estimator that projects your full-year federal
tax liability from paystub figures plus extra income, adjustments, deductions,
and credits, then recommends how much to withhold from each remaining paycheck.

For planning only -- not tax advice.
"""

from __future__ import annotations

from twe.engine import estimate
from twe.models import (
    Adjustments,
    Credits,
    Deductions,
    EstimateResult,
    EstimatorInput,
    OtherIncome,
    OtherPayments,
    Paystub,
)

__all__ = [
    "estimate",
    "EstimatorInput",
    "EstimateResult",
    "Paystub",
    "OtherIncome",
    "Adjustments",
    "Deductions",
    "Credits",
    "OtherPayments",
]

__version__ = "0.1.0"
