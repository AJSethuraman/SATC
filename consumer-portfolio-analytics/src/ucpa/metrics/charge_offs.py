"""Gross and net charge-off rates, plus recovery trends.

Definitions
-----------
* Monthly gross charge-offs = sum of write-off amounts in the month (the
  balance on each account's first charge-off-flagged row).
* ``gross_co_rate_t12`` = trailing-12-month gross charge-off dollars divided
  by the average monthly open balance over the same window.  Because a
  12-month sum over an average monthly balance is already an annual rate,
  no further annualization applies (windows shorter than 12 months are
  scaled to annual).  This matches the FRED CORCCACBS convention
  (annualized net charge-offs / average loans; here split gross vs net).
* ``net_co_rate_t12`` = same, with trailing-12-month recoveries netted out.
  Requires Tier 2 recovery detail; without it the net rate is reported as a
  data gap rather than silently equated to gross.
"""

from __future__ import annotations

import pandas as pd

from ucpa.data_model import F_AS_OF_DATE, F_RECOVERY_AMOUNT
from ucpa.metrics.common import charge_off_events, monthly_outstanding
from ucpa.metrics.results import (
    STATUS_COMPUTED,
    STATUS_PARTIAL,
    DataGapFinding,
    MetricResult,
)
from ucpa.tier_detector import field_present

TRAILING_MONTHS = 12


def _monthly_frame(tape: pd.DataFrame) -> pd.DataFrame:
    """Per-month open balance, gross charge-offs, and recoveries."""
    outstanding = monthly_outstanding(tape)
    frame = outstanding.rename("open_balance").to_frame()

    events = charge_off_events(tape)
    gross = (
        events.groupby("co_date", sort=True)["co_amount"].sum()
        if not events.empty
        else pd.Series(dtype=float)
    )
    frame["gross_charge_offs"] = gross.reindex(frame.index).fillna(0.0)

    if field_present(tape, F_RECOVERY_AMOUNT):
        rec = tape.groupby(F_AS_OF_DATE, sort=True)[F_RECOVERY_AMOUNT].sum()
        frame["recoveries"] = rec.reindex(frame.index).fillna(0.0)
        frame["net_charge_offs"] = frame["gross_charge_offs"] - frame["recoveries"]
    frame.index.name = "as_of_date"
    return frame


def _trailing_rate(frame: pd.DataFrame, flow_col: str) -> float:
    window = frame.tail(TRAILING_MONTHS)
    avg_balance = float(window["open_balance"].mean())
    if avg_balance <= 0:
        return 0.0
    annualizer = 12.0 / len(window)
    return float(window[flow_col].sum()) * annualizer / avg_balance


def compute_charge_off_rates(tape: pd.DataFrame) -> MetricResult:
    """Trailing-12-month gross/net charge-off rates and the monthly series."""
    frame = _monthly_frame(tape)
    has_recovery = "recoveries" in frame.columns

    monthly = frame.copy()
    monthly["gross_co_rate_annualized"] = (
        (monthly["gross_charge_offs"] * 12.0) / monthly["open_balance"]
    ).fillna(0.0)

    summary: dict[str, object] = {
        "gross_co_rate_t12": _trailing_rate(frame, "gross_charge_offs"),
        "gross_co_amount_t12": float(frame["gross_charge_offs"].tail(TRAILING_MONTHS).sum()),
        "avg_open_balance_t12": float(frame["open_balance"].tail(TRAILING_MONTHS).mean()),
    }
    gaps: list[DataGapFinding] = []
    if has_recovery:
        summary["net_co_rate_t12"] = _trailing_rate(frame, "net_charge_offs")
        summary["recovery_amount_t12"] = float(frame["recoveries"].tail(TRAILING_MONTHS).sum())
    else:
        summary["net_co_rate_t12"] = None
        gaps.append(
            DataGapFinding(
                metric="charge_off_rates",
                scope="net_charge_off_rate",
                missing_fields=(F_RECOVERY_AMOUNT,),
                tier_required=2,
                description=(
                    "Net charge-off rate requires post-charge-off recovery detail; "
                    "only the gross rate could be computed."
                ),
            )
        )

    return MetricResult(
        metric="charge_off_rates",
        status=STATUS_PARTIAL if gaps else STATUS_COMPUTED,
        summary=summary,
        tables={"monthly": monthly.reset_index()},
        gaps=gaps,
    )


def compute_recovery_trends(tape: pd.DataFrame) -> MetricResult:
    """Recovery dollars over time and recovery rates vs gross charge-offs.

    ``cumulative_recovery_rate`` = lifetime recoveries to date / lifetime
    gross charge-offs to date.  ``recovery_rate_t12`` = trailing-12-month
    recoveries / trailing-12-month gross charge-offs.
    """
    frame = _monthly_frame(tape)
    rec = frame["recoveries"]
    gross = frame["gross_charge_offs"]

    cum_gross = float(gross.sum())
    cum_rec = float(rec.sum())
    t12_gross = float(gross.tail(TRAILING_MONTHS).sum())
    t12_rec = float(rec.tail(TRAILING_MONTHS).sum())

    trend = pd.DataFrame(
        {
            "as_of_date": frame.index,
            "recoveries": rec.to_numpy(),
            "gross_charge_offs": gross.to_numpy(),
            "cumulative_recovery_rate": (
                rec.cumsum() / gross.cumsum().replace(0.0, float("nan"))
            ).fillna(0.0).to_numpy(),
        }
    )

    summary = {
        "cumulative_recovery_rate": cum_rec / cum_gross if cum_gross else 0.0,
        "recovery_rate_t12": t12_rec / t12_gross if t12_gross else 0.0,
        "recovery_amount_total": cum_rec,
    }
    return MetricResult(
        metric="recovery_trends",
        status=STATUS_COMPUTED,
        summary=summary,
        tables={"trend": trend},
    )
