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
    nan = float("nan")
    return pd.DataFrame({
        "Loan No": ["L-101", "L-102", "L-103", "L-104", "L-105"],
        "Curr Bal": [15000, 25000, 8000, 120000, 5000],
        "Orig FICO": [710, 640, 690, 705, 720],
        "Back-end DTI": [0.30, 0.45, 0.38, 0.50, 0.20],
        "Days Past Due": [0, 100, 200, 95, 45],
        "Structure": ["closed_end", "closed_end", "open_end",
                      "residential_secured", "open_end"],
        "Product": ["auto", "auto", "card", "heloc", "card"],
        # Unsecured products carry no LTV -> WA-LTV self-suppresses for them.
        "CLTV": [nan, nan, nan, 0.82, nan],
        "Orig Date": ["2023-01-15", "2022-06-10", "2021-03-01",
                      "2022-11-20", "2023-02-05"],
        "CO Flag": ["N", "N", "Y", "N", "N"],
        "CO Date": ["", "", "2023-05-01", "", ""],
        "CO Amount": [nan, nan, 8000, nan, nan],
        "Prior Bucket": ["current", "60-89", "120-179", "30-59", "current"],
    })


def demo_cohorts():
    """Three illustrative derived cohorts over the full demo — deliberately
    overlapping (L-102 is in both 'high-balance delinquent' and 'subprime auto')
    so the overlap matrix + residual have something to show."""
    from popbench.cohorts import Cohort, Rule
    return [
        Cohort("high_bal_delq", "High-balance delinquent (>=$20k, >=90 DPD)",
               (Rule("current_balance", ">=", 20000), Rule("dpd_min", ">=", 90))),
        Cohort("subprime_auto", "Subprime auto (FICO<660, auto)",
               (Rule("fico_orig", "<", 660), Rule("product_type", "==", "auto"))),
        Cohort("card", "Card product", (Rule("product_type", "==", "card"),)),
    ]


def dirty_population() -> pd.DataFrame:
    """A population the gate must refuse: a duplicate loan id and an unparseable
    balance."""
    return pd.DataFrame({
        "Loan No": ["L-001", "L-001", "L-003", "L-004"],
        "Curr Bal": [10000, "n/a", 30000, 40000],
        "Orig FICO": [720, 680, 760, 700],
    })
