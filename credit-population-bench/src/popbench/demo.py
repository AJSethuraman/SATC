"""Synthetic demo populations — 100% fabricated, zero real PII.

Deliberately messy headers ("Loan No", "Curr Bal", "Orig FICO") so the demo
exercises the auto-propose mapping path, and a ``dirty_population`` variant that
the cleaning gate must refuse. Hand-tallied expected values for these fixtures
live in the tests.
"""

from __future__ import annotations

import pandas as pd


def demo_population() -> pd.DataFrame:
    """A tiny clean population with real-world-ish messy headers.

    Chosen so the weighted averages hand-tally to round numbers:
    dollar-weighted FICO = 716.0, count-weighted FICO = 715.0,
    total balance = 100,000, count = 4.
    """
    return pd.DataFrame({
        "Loan No": ["L-001", "L-002", "L-003", "L-004"],
        "Curr Bal": [10000, 20000, 30000, 40000],
        "Orig FICO": [720, 680, 760, 700],
        "Original Loan Amount": [12000, 25000, 30000, 48000],
    })


def dirty_population() -> pd.DataFrame:
    """A population the gate must refuse: a duplicate loan id and an unparseable
    balance."""
    return pd.DataFrame({
        "Loan No": ["L-001", "L-001", "L-003", "L-004"],
        "Curr Bal": [10000, "n/a", 30000, 40000],
        "Orig FICO": [720, 680, 760, 700],
    })
