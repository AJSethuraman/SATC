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


def demo_population_full() -> pd.DataFrame:
    """A richer synthetic population spanning URCCP branches, with messy headers
    and a delinquency day count — exercises delinquency rates + classification.
    100% fabricated; loan numbers only, no person data."""
    return pd.DataFrame({
        "Loan No": ["L-101", "L-102", "L-103", "L-104", "L-105"],
        "Curr Bal": [15000, 25000, 8000, 120000, 5000],
        "Orig FICO": [710, 640, 690, 705, 720],
        "Days Past Due": [0, 100, 200, 95, 45],
        "Structure": ["closed_end", "closed_end", "open_end",
                      "residential_secured", "open_end"],
        "Product": ["auto", "auto", "card", "heloc", "card"],
        "CLTV": [0.0, 0.0, 0.0, 0.82, 0.0],
    })


def dirty_population() -> pd.DataFrame:
    """A population the gate must refuse: a duplicate loan id and an unparseable
    balance."""
    return pd.DataFrame({
        "Loan No": ["L-001", "L-001", "L-003", "L-004"],
        "Curr Bal": [10000, "n/a", 30000, 40000],
        "Orig FICO": [720, 680, 760, 700],
    })
