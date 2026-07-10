"""Revolving-specific metrics: utilization distribution and line management.

Utilization distribution (Tier 1)
---------------------------------
Computed on the latest-month open snapshot.  Utilization is the reported
``utilization`` column when present (Tier 2), otherwise ``balance /
credit_limit``.  Headlines: portfolio (dollar-weighted) utilization, the
share of balances sitting on accounts >90% utilized, and total open-to-buy
(undrawn line) exposure.

Line management (Tier 2)
------------------------
Uses the monthly credit-limit history.  A line increase is any
month-over-month limit increase on an open account.  Headlines: exposure
added, the share of increase dollars granted to below-prime accounts, and
the "increases gone bad" rate -- the share of increase events (with at
least six months of subsequent observation) where the account hit 30+ DPD
within six months of the increase.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ucpa.data_model import (
    BUCKET_CO,
    DELINQUENT_BUCKETS,
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_BALANCE,
    F_CREDIT_LIMIT,
    F_DELINQUENCY_BUCKET,
    F_SCORE_BAND,
    F_UTILIZATION,
)
from ucpa.metrics.common import latest_snapshot
from ucpa.metrics.results import STATUS_COMPUTED, MetricResult
from ucpa.tier_detector import field_present

UTIL_EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0, float("inf"))
UTIL_LABELS = ("0-20%", "20-40%", "40-60%", "60-80%", "80-90%", "90-100%", ">100%")
HIGH_UTIL_THRESHOLD = 0.9
GONE_BAD_HORIZON = 6  # months after a line increase to watch for 30+ DPD


def compute_utilization_distribution(tape: pd.DataFrame) -> MetricResult:
    """Utilization distribution and line exposure at the latest month."""
    snap = latest_snapshot(tape).copy()
    if field_present(snap, F_UTILIZATION):
        util = snap[F_UTILIZATION].astype(float)
    else:
        util = (snap[F_BALANCE] / snap[F_CREDIT_LIMIT].replace(0.0, np.nan)).fillna(0.0)
    snap["_util"] = util

    buckets = pd.cut(util, bins=list(UTIL_EDGES), labels=list(UTIL_LABELS), right=False)
    dist = (
        snap.assign(_bucket=buckets.astype(str).to_numpy())
        .groupby("_bucket", sort=False)
        .agg(accounts=(F_ACCOUNT_ID, "nunique"), balance=(F_BALANCE, "sum"))
        .reindex(list(UTIL_LABELS), fill_value=0.0)
    )
    dist["accounts"] = dist["accounts"].fillna(0).astype(int)
    total_bal = float(dist["balance"].sum())
    dist["balance_share"] = dist["balance"] / total_bal if total_bal else 0.0
    dist.index.name = "utilization_bucket"

    total_limit = float(snap[F_CREDIT_LIMIT].sum())
    high_util_bal = float(snap.loc[snap["_util"] >= HIGH_UTIL_THRESHOLD, F_BALANCE].sum())
    open_to_buy = float((snap[F_CREDIT_LIMIT] - snap[F_BALANCE]).clip(lower=0.0).sum())

    summary = {
        "portfolio_utilization": total_bal / total_limit if total_limit else 0.0,
        "high_util_balance_share": high_util_bal / total_bal if total_bal else 0.0,
        "open_to_buy_total": open_to_buy,
        "total_credit_line": total_limit,
    }
    return MetricResult(
        metric="utilization_distribution",
        status=STATUS_COMPUTED,
        summary=summary,
        tables={"distribution": dist.reset_index()},
    )


def compute_line_management(tape: pd.DataFrame) -> MetricResult:
    """Line-increase activity and its subsequent delinquency performance."""
    cols = [F_ACCOUNT_ID, F_AS_OF_DATE, F_CREDIT_LIMIT, F_DELINQUENCY_BUCKET, F_SCORE_BAND]
    panel = (
        tape[cols]
        .sort_values([F_ACCOUNT_ID, F_AS_OF_DATE], kind="mergesort")
        .reset_index(drop=True)
    )
    grp = panel.groupby(F_ACCOUNT_ID, sort=False)
    prev_limit = grp[F_CREDIT_LIMIT].shift(1)
    open_row = panel[F_DELINQUENCY_BUCKET] != BUCKET_CO
    increases = panel[open_row & prev_limit.notna() & (panel[F_CREDIT_LIMIT] > prev_limit)].copy()
    increases["amount_added"] = (panel[F_CREDIT_LIMIT] - prev_limit).loc[increases.index]

    total_added = float(increases["amount_added"].sum())
    below_prime = increases[F_SCORE_BAND].isin(["NEAR_PRIME", "SUBPRIME"])
    added_below_prime = float(increases.loc[below_prime, "amount_added"].sum())

    # Increases gone bad: 30+ DPD within GONE_BAD_HORIZON months of increase.
    period = pd.PeriodIndex(panel[F_AS_OF_DATE], freq="M")
    panel["_pnum"] = period.astype("int64")
    dq = panel[panel[F_DELINQUENCY_BUCKET].isin(DELINQUENT_BUCKETS)]
    dq_months = dq.groupby(F_ACCOUNT_ID, sort=False)["_pnum"].agg(list)
    panel_end = int(panel["_pnum"].max())

    gone_bad = 0
    measurable = 0
    inc_pnum = panel["_pnum"].loc[increases.index]
    for acct, pnum in zip(increases[F_ACCOUNT_ID], inc_pnum):
        if panel_end - pnum < GONE_BAD_HORIZON:
            continue  # not enough subsequent observation to judge
        measurable += 1
        months = dq_months.get(acct)
        if months and any(pnum < m <= pnum + GONE_BAD_HORIZON for m in months):
            gone_bad += 1

    by_band = (
        increases.groupby(F_SCORE_BAND, sort=True)
        .agg(events=(F_ACCOUNT_ID, "size"), amount_added=("amount_added", "sum"))
        .reset_index()
    )

    summary = {
        "line_increase_events": int(len(increases)),
        "exposure_added_total": total_added,
        "increase_share_below_prime": added_below_prime / total_added if total_added else 0.0,
        "increases_gone_bad_rate": gone_bad / measurable if measurable else 0.0,
        "increases_measurable": measurable,
    }
    return MetricResult(
        metric="line_management",
        status=STATUS_COMPUTED,
        summary=summary,
        tables={"increases_by_band": by_band},
    )
