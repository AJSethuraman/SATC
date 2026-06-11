"""Delinquency distribution by bucket (point-in-time and trend).

Definitions
-----------
* Distribution is taken at the latest as-of month over open (non-charged-off)
  accounts.
* ``dpd30plus_balance_rate`` = balance in DPD30..DPD120 / total open balance,
  matching the FRED DRCCLACBS-style 30+ day delinquency-rate convention.
* ``dpd90plus_balance_rate`` = balance in DPD90..DPD120 / total open balance
  (serious delinquency, NY Fed HHDC convention).
"""

from __future__ import annotations

import pandas as pd

from ucpa.data_model import (
    BUCKET_CO,
    BUCKET_DPD90,
    BUCKET_ORDER,
    DELINQUENT_BUCKETS,
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_BALANCE,
    F_DELINQUENCY_BUCKET,
)
from ucpa.metrics.common import active_rows, latest_snapshot
from ucpa.metrics.results import STATUS_COMPUTED, MetricResult

OPEN_BUCKETS = [b for b in BUCKET_ORDER if b != BUCKET_CO]
DPD90_PLUS = [b for b in DELINQUENT_BUCKETS if BUCKET_ORDER.index(b) >= BUCKET_ORDER.index(BUCKET_DPD90)]


def _bucket_rates(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Account/balance distribution over open buckets for one month of rows."""
    grouped = snapshot.groupby(F_DELINQUENCY_BUCKET, sort=False).agg(
        accounts=(F_ACCOUNT_ID, "nunique"), balance=(F_BALANCE, "sum")
    )
    dist = grouped.reindex(OPEN_BUCKETS, fill_value=0.0)
    dist["accounts"] = dist["accounts"].fillna(0).astype(int)
    total_bal = float(dist["balance"].sum())
    total_acct = int(dist["accounts"].sum())
    dist["account_pct"] = dist["accounts"] / total_acct if total_acct else 0.0
    dist["balance_pct"] = dist["balance"] / total_bal if total_bal else 0.0
    dist.index.name = "bucket"
    return dist


def compute_delinquency_distribution(tape: pd.DataFrame) -> MetricResult:
    """Delinquency distribution by bucket at the latest month, plus trend.

    Tables:
        ``distribution``: bucket x (accounts, balance, account_pct, balance_pct).
        ``trend``: per-month 30+/90+ balance rates (panel tapes only).
    """
    snap = latest_snapshot(tape)
    dist = _bucket_rates(snap)

    dq_bal = float(dist.loc[list(DELINQUENT_BUCKETS), "balance"].sum())
    dq90_bal = float(dist.loc[DPD90_PLUS, "balance"].sum())
    dq_acct = int(dist.loc[list(DELINQUENT_BUCKETS), "accounts"].sum())
    total_bal = float(dist["balance"].sum())
    total_acct = int(dist["accounts"].sum())

    summary = {
        "as_of": snap[F_AS_OF_DATE].max() if not snap.empty else None,
        "total_accounts": total_acct,
        "total_balance": total_bal,
        "dpd30plus_balance_rate": dq_bal / total_bal if total_bal else 0.0,
        "dpd90plus_balance_rate": dq90_bal / total_bal if total_bal else 0.0,
        "dpd30plus_account_rate": dq_acct / total_acct if total_acct else 0.0,
    }

    tables = {"distribution": dist.reset_index()}

    act = active_rows(tape)
    if act[F_AS_OF_DATE].nunique() > 1:
        rows = []
        for month, grp in act.groupby(F_AS_OF_DATE, sort=True):
            d = _bucket_rates(grp)
            tb = float(d["balance"].sum())
            rows.append(
                {
                    "as_of_date": month,
                    "total_balance": tb,
                    "dpd30plus_balance_rate": float(d.loc[list(DELINQUENT_BUCKETS), "balance"].sum()) / tb if tb else 0.0,
                    "dpd90plus_balance_rate": float(d.loc[DPD90_PLUS, "balance"].sum()) / tb if tb else 0.0,
                }
            )
        tables["trend"] = pd.DataFrame(rows)

    return MetricResult(
        metric="delinquency_distribution",
        status=STATUS_COMPUTED,
        summary=summary,
        tables=tables,
    )
