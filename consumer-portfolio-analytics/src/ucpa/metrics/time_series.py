"""Portfolio-level monthly time series -- the longitudinal view.

Assembles one consolidated monthly panel of the portfolio's key asset-quality
indicators so trends (not just point-in-time levels) are a first-class
deliverable:

* open accounts, open balance, observed new originations,
* balance by delinquency bucket and the 30+/90+ DPD balance rates,
* gross charge-offs, recoveries (Tier 2), annualized monthly CO rate,
* portfolio utilization and >90%-utilized balance share (when the credit
  limit is available).

Trend-deterioration headlines (threshold-checkable):

* ``dpd30plus_yoy_delta`` -- latest 30+ DPD balance rate minus the rate 12
  months earlier (percentage points, as a decimal).
* ``gross_co_rate_yoy_delta`` -- trailing-12-month annualized gross
  charge-off rate minus the same measure ending 12 months earlier
  (requires >= 24 months of history).
* ``balance_growth_12m`` -- open-balance growth over the last 12 months
  (rapid growth can mask deterioration in rate denominators).

Headlines are ``None`` when the panel is too short to support them; the
threshold layer skips checks on missing values rather than guessing.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from ucpa.data_model import (
    BUCKET_ORDER,
    DELINQUENT_BUCKETS,
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_BALANCE,
    F_CREDIT_LIMIT,
    F_DELINQUENCY_BUCKET,
    F_ORIGINATION_DATE,
    F_RECOVERY_AMOUNT,
    F_UTILIZATION,
)
from ucpa.metrics.common import active_rows, charge_off_events
from ucpa.metrics.results import STATUS_COMPUTED, MetricResult
from ucpa.tier_detector import field_present

OPEN_BUCKETS = [b for b in BUCKET_ORDER if b != "CO"]
DPD90_PLUS = ["DPD90", "DPD120"]
HIGH_UTIL_THRESHOLD = 0.9


def _trailing12_co_rate(monthly: pd.DataFrame, end_pos: int) -> Optional[float]:
    """Annualized 12-month gross CO rate for the window ending at ``end_pos``."""
    if end_pos + 1 < 12:
        return None
    window = monthly.iloc[end_pos - 11 : end_pos + 1]
    avg_balance = float(window["open_balance"].mean())
    if avg_balance <= 0:
        return None
    return float(window["gross_charge_offs"].sum()) / avg_balance


def compute_portfolio_time_series(tape: pd.DataFrame) -> MetricResult:
    """Consolidated monthly portfolio panel plus YoY-deterioration headlines."""
    act = active_rows(tape)
    months = sorted(act[F_AS_OF_DATE].unique())

    bucket_bal = (
        act.pivot_table(
            index=F_AS_OF_DATE,
            columns=F_DELINQUENCY_BUCKET,
            values=F_BALANCE,
            aggfunc="sum",
            fill_value=0.0,
        )
        .reindex(months)
        .reindex(columns=OPEN_BUCKETS, fill_value=0.0)
    )
    monthly = pd.DataFrame(index=pd.Index(months, name=F_AS_OF_DATE))
    monthly["open_accounts"] = act.groupby(F_AS_OF_DATE)[F_ACCOUNT_ID].nunique().reindex(months)
    monthly["open_balance"] = bucket_bal.sum(axis=1)

    # New originations observed in the tape (first appearance at MOB 0).
    firsts = tape.sort_values([F_ACCOUNT_ID, F_AS_OF_DATE]).groupby(F_ACCOUNT_ID).first()
    orig_month = pd.PeriodIndex(firsts[F_ORIGINATION_DATE], freq="M").to_timestamp()
    monthly["new_originations"] = (
        pd.Series(1, index=orig_month).groupby(level=0).sum().reindex(months).fillna(0).astype(int)
    )

    for bucket in OPEN_BUCKETS:
        monthly[f"balance_{bucket.lower()}"] = bucket_bal[bucket]
    dq_bal = bucket_bal[list(DELINQUENT_BUCKETS)].sum(axis=1)
    dq90_bal = bucket_bal[DPD90_PLUS].sum(axis=1)
    monthly["dpd30plus_rate"] = (dq_bal / monthly["open_balance"]).fillna(0.0)
    monthly["dpd90plus_rate"] = (dq90_bal / monthly["open_balance"]).fillna(0.0)

    events = charge_off_events(tape)
    gross = (
        events.groupby("co_date")["co_amount"].sum()
        if not events.empty
        else pd.Series(dtype=float)
    )
    monthly["gross_charge_offs"] = gross.reindex(months).fillna(0.0)
    monthly["gross_co_rate_ann"] = (
        (monthly["gross_charge_offs"] * 12.0) / monthly["open_balance"]
    ).fillna(0.0)
    if field_present(tape, F_RECOVERY_AMOUNT):
        monthly["recoveries"] = (
            tape.groupby(F_AS_OF_DATE)[F_RECOVERY_AMOUNT].sum().reindex(months).fillna(0.0)
        )

    if field_present(tape, F_CREDIT_LIMIT):
        limit_by_month = act.groupby(F_AS_OF_DATE)[F_CREDIT_LIMIT].sum().reindex(months)
        monthly["portfolio_utilization"] = (monthly["open_balance"] / limit_by_month).fillna(0.0)
        if field_present(tape, F_UTILIZATION):
            util = act[F_UTILIZATION].astype(float)
        else:
            util = (act[F_BALANCE] / act[F_CREDIT_LIMIT].replace(0.0, np.nan)).fillna(0.0)
        high = act[util >= HIGH_UTIL_THRESHOLD]
        high_bal = high.groupby(F_AS_OF_DATE)[F_BALANCE].sum().reindex(months).fillna(0.0)
        monthly["high_util_balance_share"] = (high_bal / monthly["open_balance"]).fillna(0.0)

    n = len(monthly)
    latest = monthly.iloc[-1] if n else None

    dpd_yoy = None
    balance_growth = None
    if n >= 13:
        dpd_yoy = float(latest["dpd30plus_rate"] - monthly["dpd30plus_rate"].iloc[n - 13])
        prior_balance = float(monthly["open_balance"].iloc[n - 13])
        if prior_balance > 0:
            balance_growth = float(latest["open_balance"]) / prior_balance - 1.0

    co_now = _trailing12_co_rate(monthly, n - 1) if n else None
    co_prior = _trailing12_co_rate(monthly, n - 13) if n >= 24 else None
    co_yoy = (co_now - co_prior) if (co_now is not None and co_prior is not None) else None

    summary: dict[str, object] = {
        "months_observed": n,
        "latest_dpd30plus_rate": float(latest["dpd30plus_rate"]) if n else None,
        "dpd30plus_yoy_delta": dpd_yoy,
        "gross_co_rate_yoy_delta": co_yoy,
        "balance_growth_12m": balance_growth,
    }

    return MetricResult(
        metric="portfolio_time_series",
        status=STATUS_COMPUTED,
        summary=summary,
        tables={"monthly": monthly.reset_index()},
    )
