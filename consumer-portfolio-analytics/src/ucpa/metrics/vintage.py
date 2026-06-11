"""Vintage cumulative gross-loss curves by origination cohort.

Definitions
-----------
* Cohort = origination calendar quarter (e.g. ``2022Q3``).
* For a revolving product the loss-curve denominator is the cohort's total
  credit line at origination (``orig_credit_limit`` when available,
  otherwise each account's first observed limit).
* ``cum_loss(cohort, m)`` = cumulative gross charge-off dollars taken by the
  cohort through month-on-book ``m``, divided by the cohort denominator.
  Cells beyond a cohort's observed age are left blank (NaN).
* Vintage-deterioration headline: average cumulative loss at MOB 12 of
  cohorts originated in the most recent four quarters (with at least 12
  months of age) versus the same figure for all older cohorts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ucpa.data_model import F_ACCOUNT_ID, F_AS_OF_DATE, F_ORIGINATION_DATE
from ucpa.metrics.common import account_origination_limit, charge_off_events, months_between
from ucpa.metrics.results import STATUS_COMPUTED, MetricResult

CHECK_MOB = 12  # month-on-book checkpoint for the headline comparisons


def compute_vintage_curves(tape: pd.DataFrame) -> MetricResult:
    """Cumulative gross charge-off curves by origination quarter."""
    accounts = (
        tape.sort_values([F_ACCOUNT_ID, F_AS_OF_DATE], kind="mergesort")
        .groupby(F_ACCOUNT_ID, sort=True)
        .first()
    )
    orig_limit = account_origination_limit(tape)
    cohort = pd.PeriodIndex(accounts[F_ORIGINATION_DATE], freq="Q").astype(str)
    panel_end = pd.Period(tape[F_AS_OF_DATE].max(), freq="M")
    orig_period = pd.PeriodIndex(accounts[F_ORIGINATION_DATE], freq="M")
    account_age = pd.Series([(panel_end - p).n for p in orig_period], index=accounts.index)

    acct_df = pd.DataFrame(
        {"cohort": cohort, "orig_limit": orig_limit, "age": account_age}
    )
    cohort_denom = acct_df.groupby("cohort", sort=True)["orig_limit"].sum()
    cohort_age = acct_df.groupby("cohort", sort=True)["age"].min()
    cohort_accounts = acct_df.groupby("cohort", sort=True).size()

    events = charge_off_events(tape)
    if not events.empty:
        events = events.assign(
            mob=months_between(events["co_date"], events[F_ORIGINATION_DATE]).to_numpy(),
            cohort=pd.PeriodIndex(events[F_ORIGINATION_DATE], freq="Q").astype(str),
        )

    cohorts = list(cohort_denom.index)
    max_mob = int(cohort_age.max()) if len(cohort_age) else 0
    curve = pd.DataFrame(
        np.nan, index=pd.Index(range(max_mob + 1), name="months_on_book"), columns=cohorts
    )
    for c in cohorts:
        age = int(cohort_age.loc[c])
        denom = float(cohort_denom.loc[c])
        losses = np.zeros(age + 1)
        if not events.empty:
            ev = events[events["cohort"] == c]
            for mob, amt in zip(ev["mob"], ev["co_amount"]):
                if 0 <= mob <= age:
                    losses[int(mob)] += float(amt)
        curve.loc[0:age, c] = np.cumsum(losses) / denom if denom else 0.0

    at_check = curve.loc[CHECK_MOB] if max_mob >= CHECK_MOB else pd.Series(dtype=float)
    measurable = at_check.dropna()

    summary: dict[str, object] = {
        "cohorts": len(cohorts),
        "max_cum_loss_mob12": float(measurable.max()) if not measurable.empty else None,
        "worst_cohort_mob12": str(measurable.idxmax()) if not measurable.empty else None,
    }

    # Recent (latest 4 measurable quarters) vs seasoned cohorts at MOB 12.
    recent_ratio = None
    if len(measurable) >= 5:
        recent = measurable.iloc[-4:]
        seasoned = measurable.iloc[:-4]
        if float(seasoned.mean()) > 0:
            recent_ratio = float(recent.mean()) / float(seasoned.mean())
    summary["recent_vs_seasoned_mob12_ratio"] = recent_ratio

    cohort_summary = pd.DataFrame(
        {
            "cohort": cohorts,
            "accounts": cohort_accounts.reindex(cohorts).to_numpy(),
            "orig_credit_line": cohort_denom.reindex(cohorts).to_numpy(),
            "age_months": cohort_age.reindex(cohorts).to_numpy(),
            "cum_loss_mob12": [
                float(curve.loc[CHECK_MOB, c]) if int(cohort_age.loc[c]) >= CHECK_MOB else np.nan
                for c in cohorts
            ],
            "cum_loss_latest": [float(curve[c].dropna().iloc[-1]) for c in cohorts],
        }
    )

    return MetricResult(
        metric="vintage_curves",
        status=STATUS_COMPUTED,
        summary=summary,
        tables={"curves": curve.reset_index(), "cohort_summary": cohort_summary},
    )
