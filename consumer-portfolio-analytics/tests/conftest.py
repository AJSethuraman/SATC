"""Shared fixtures: a small seeded tape and a hand-built toy panel."""

from __future__ import annotations

import pandas as pd
import pytest

from ucpa.generator import CardGeneratorConfig, generate_card_portfolio

SMALL_CONFIG = CardGeneratorConfig(
    n_accounts=500, n_months=36, origination_window_months=30, seed=42
)


@pytest.fixture(scope="session")
def small_tape() -> pd.DataFrame:
    """Small seeded Tier 2 tape used by the golden-number tests."""
    return generate_card_portfolio(SMALL_CONFIG)


@pytest.fixture()
def toy_tape() -> pd.DataFrame:
    """Hand-built 4-account / 3-month panel with hand-computed answers.

    Story:
      A1 stays current (balance 100, limit 1000).
      A2 rolls current -> 30 -> 60 (balance 200, limit 1000).
      A3 cures 30 -> current -> current (balance 300 then 100, limit 1000).
      A4 sits at 120+, charges off $400 in month 2 (limit 800), and posts a
         $50 recovery in month 3.
    """
    m1, m2, m3 = pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01"), pd.Timestamp("2024-03-01")
    o_late = pd.Timestamp("2023-10-01")
    o_early = pd.Timestamp("2023-06-01")

    def row(acct, orig, as_of, bal, bucket, co, limit, band, rec=0.0):
        return {
            "account_id": acct,
            "product_type": "CREDIT_CARD",
            "origination_date": orig,
            "as_of_date": as_of,
            "balance": bal,
            "delinquency_bucket": bucket,
            "charge_off_flag": co,
            "credit_limit": limit,
            "score_band": band,
            "payment_status": "MIN_PAY",
            "orig_score": 700,
            "current_score": 700,
            "utilization": bal / limit,
            "orig_credit_limit": limit,
            "recovery_amount": rec,
        }

    rows = [
        row("A1", o_late, m1, 100.0, "CURRENT", 0, 1000.0, "PRIME"),
        row("A1", o_late, m2, 100.0, "CURRENT", 0, 1000.0, "PRIME"),
        row("A1", o_late, m3, 100.0, "CURRENT", 0, 1000.0, "PRIME"),
        row("A2", o_late, m1, 200.0, "CURRENT", 0, 1000.0, "PRIME"),
        row("A2", o_late, m2, 200.0, "DPD30", 0, 1000.0, "PRIME"),
        row("A2", o_late, m3, 200.0, "DPD60", 0, 1000.0, "PRIME"),
        row("A3", o_late, m1, 300.0, "DPD30", 0, 1000.0, "NEAR_PRIME"),
        row("A3", o_late, m2, 100.0, "CURRENT", 0, 1000.0, "NEAR_PRIME"),
        row("A3", o_late, m3, 100.0, "CURRENT", 0, 1000.0, "NEAR_PRIME"),
        row("A4", o_early, m1, 400.0, "DPD120", 0, 800.0, "SUBPRIME"),
        row("A4", o_early, m2, 400.0, "CO", 1, 800.0, "SUBPRIME"),
        row("A4", o_early, m3, 0.0, "CO", 1, 800.0, "SUBPRIME", rec=50.0),
    ]
    return pd.DataFrame(rows)
