"""Shared credit-core for the SATC credit-review tools.

The single home for correctness-critical constants and cross-cutting guards that
more than one tool depends on — so they are defined **once** and can never drift
between ``credit-review-os`` and ``credit-population-bench``:

- :mod:`satc_credit_core.urccp` — the URCCP classification floors (90/120/180)
  and the clock resolver (bank policy may only *tighten* the interagency floor,
  never loosen it — 65 FR 36903 / OCC Bulletin 2000-20 / FDIC FIL-40-2000).
- :mod:`satc_credit_core.pii` — the TIN/SSN byte-scan used by each tool's
  no-PII-leak guard.

This package is pure-Python and dependency-free so each tool can **vendor/inline
it into its emailable ASCII bundle** at transmission time while sharing it at
source time.
"""

from __future__ import annotations

from satc_credit_core.urccp import (
    BUCKET_START_DPD,
    URCCP_FLOORS,
    URCCPError,
    resolve_classification_dpd,
)

__all__ = [
    "URCCP_FLOORS",
    "BUCKET_START_DPD",
    "URCCPError",
    "resolve_classification_dpd",
]

__version__ = "0.1.0"
