"""Month-over-month roll-rate / migration matrix.

Definitions
-----------
For every pair of *consecutive calendar months* in the panel, an account
observed in both months contributes one transition from its bucket in month
``t`` to its bucket in month ``t+1``.  Transitions *into* charge-off are
captured (the charge-off month row carries bucket ``CO``); rows already in
``CO`` at month ``t`` are excluded (charge-off is absorbing).

* ``counts``: summed transition counts over all month pairs.
* ``row_pct``: counts row-normalized -- the average account-level monthly
  migration matrix.
* ``balance_row_pct``: transitions weighted by the account balance at month
  ``t``, row-normalized -- the dollar roll-rate matrix.
* The headline ``current_to_dpd30`` / ``dpd30_to_dpd60`` roll rates are the
  balance-weighted averages over the full panel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ucpa.data_model import (
    BUCKET_CO,
    BUCKET_ORDER,
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_BALANCE,
    F_DELINQUENCY_BUCKET,
)
from ucpa.metrics.results import STATUS_COMPUTED, MetricResult

FROM_BUCKETS = [b for b in BUCKET_ORDER if b != BUCKET_CO]
TO_BUCKETS = list(BUCKET_ORDER)


def _row_normalize(matrix: pd.DataFrame) -> pd.DataFrame:
    totals = matrix.sum(axis=1)
    out = matrix.div(totals.where(totals > 0, other=np.nan), axis=0)
    return out.fillna(0.0)


def compute_migration_matrix(tape: pd.DataFrame) -> MetricResult:
    """Average monthly migration matrix and roll-rate trend over the panel."""
    cols = [F_ACCOUNT_ID, F_AS_OF_DATE, F_DELINQUENCY_BUCKET, F_BALANCE]
    panel = tape[cols].copy()
    panel["period"] = pd.PeriodIndex(panel[F_AS_OF_DATE], freq="M")

    nxt = panel[[F_ACCOUNT_ID, "period", F_DELINQUENCY_BUCKET]].copy()
    nxt["period"] = nxt["period"] - 1  # join month t+1's bucket onto month t
    merged = panel.merge(
        nxt.rename(columns={F_DELINQUENCY_BUCKET: "to_bucket"}),
        on=[F_ACCOUNT_ID, "period"],
        how="inner",
    )
    merged = merged[merged[F_DELINQUENCY_BUCKET] != BUCKET_CO]

    counts = (
        merged.groupby([F_DELINQUENCY_BUCKET, "to_bucket"], sort=False)
        .size()
        .unstack(fill_value=0)
        .reindex(index=FROM_BUCKETS, columns=TO_BUCKETS, fill_value=0)
        .astype(float)
    )
    balances = (
        merged.groupby([F_DELINQUENCY_BUCKET, "to_bucket"], sort=False)[F_BALANCE]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(index=FROM_BUCKETS, columns=TO_BUCKETS, fill_value=0.0)
    )
    counts.index.name = balances.index.name = "from_bucket"

    row_pct = _row_normalize(counts)
    balance_row_pct = _row_normalize(balances)

    # Monthly trend of the two front-end roll rates (balance-weighted).
    trend_rows = []
    for period, grp in merged.groupby("period", sort=True):
        cur = grp[grp[F_DELINQUENCY_BUCKET] == "CURRENT"]
        d30 = grp[grp[F_DELINQUENCY_BUCKET] == "DPD30"]
        cur_bal = float(cur[F_BALANCE].sum())
        d30_bal = float(d30[F_BALANCE].sum())
        trend_rows.append(
            {
                "from_month": period.to_timestamp(),
                "current_to_dpd30": float(cur.loc[cur["to_bucket"] == "DPD30", F_BALANCE].sum()) / cur_bal if cur_bal else 0.0,
                "dpd30_to_dpd60": float(d30.loc[d30["to_bucket"] == "DPD60", F_BALANCE].sum()) / d30_bal if d30_bal else 0.0,
            }
        )
    trend = pd.DataFrame(trend_rows)

    summary = {
        "transitions_observed": int(counts.values.sum()),
        "current_to_dpd30": float(balance_row_pct.loc["CURRENT", "DPD30"]),
        "dpd30_to_dpd60": float(balance_row_pct.loc["DPD30", "DPD60"]),
        "dpd60_to_dpd90": float(balance_row_pct.loc["DPD60", "DPD90"]),
        "dpd30_cure_rate": float(balance_row_pct.loc["DPD30", "CURRENT"]),
        "current_to_dpd30_accounts": float(row_pct.loc["CURRENT", "DPD30"]),
    }

    return MetricResult(
        metric="migration_matrix",
        status=STATUS_COMPUTED,
        summary=summary,
        tables={
            "counts": counts.reset_index(),
            "row_pct": row_pct.reset_index(),
            "balance_row_pct": balance_row_pct.reset_index(),
            "trend": trend,
        },
    )
