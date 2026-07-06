"""Vintage (cohort) analysis within a single file, plus the gross charge-off rate.

Group loans by origination period, then read seasoning and underwriting drift
off the cohorts. Two lenses:

- **Vintage summary** — per origination period: original count/balance, current
  balance, current ever-90+ (a point-in-time cumulative delinquency proxy), and
  the cumulative **gross** loss rate to date (charged-off balance / original).
- **Loss triangle** — cumulative gross-loss rate by months-on-book, positioning
  each charge-off on the timeline by ``orig_date -> chargeoff_date``.

"Gross" throughout: the file carries a charge-off flag/date/balance but no
recoveries, so every loss figure is labeled gross-only, no recovery data (no
net NCO — a v1 non-goal).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from popbench.delinquency import FeatureUnavailable

_TRUE = {"y", "yes", "true", "1", "t", "co", "charged off", "chargeoff", "charged-off"}


def _truthy(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower().isin(_TRUE).fillna(False)


def _period(ts: pd.Timestamp, grain: str) -> str:
    if pd.isna(ts):
        return "(no date)"
    if grain == "year":
        return f"{ts.year}"
    if grain == "quarter":
        return f"{ts.year}-Q{(ts.month - 1) // 3 + 1}"
    return f"{ts.year}-{ts.month:02d}"   # month


def _months_between(a: pd.Timestamp, b: pd.Timestamp) -> float:
    if pd.isna(a) or pd.isna(b):
        return float("nan")
    return (b.year - a.year) * 12 + (b.month - a.month)


@dataclass(frozen=True)
class VintageRow:
    vintage: str
    orig_count: int
    orig_balance: float
    current_balance: float
    co_count: int
    co_balance: float
    cum_gross_loss_rate: float     # co_balance / orig_balance
    ever90_balance_rate: float     # current >=90 DPD balance / orig_balance


def _orig_balance_series(df: pd.DataFrame) -> pd.Series:
    """Original balance if present, else current balance (a documented proxy)."""
    if "orig_amount" in df.columns and df["orig_amount"].notna().any():
        return df["orig_amount"].astype("float64")
    return df["current_balance"].astype("float64")


def vintage_summary(df: pd.DataFrame, grain: str = "year") -> list[VintageRow]:
    if "orig_date" not in df.columns:
        raise FeatureUnavailable("vintage", "field 'orig_date' not mapped")
    work = df.copy()
    work["__vintage__"] = work["orig_date"].map(lambda t: _period(t, grain))
    work["__origbal__"] = _orig_balance_series(work)
    has_co = "chargeoff_balance" in work.columns
    co_flag = _truthy(work["chargeoff_flag"]) if "chargeoff_flag" in work.columns \
        else pd.Series(False, index=work.index)

    rows: list[VintageRow] = []
    for v, grp in work.groupby("__vintage__", sort=True):
        orig_bal = float(grp["__origbal__"].sum())
        cur_bal = float(grp["current_balance"].astype("float64").sum())
        co_mask = co_flag.loc[grp.index]
        co_bal = float(grp.loc[co_mask, "chargeoff_balance"].astype("float64").sum()) if has_co else 0.0
        if "dpd_min" in grp.columns:
            ever90_bal = float(grp.loc[grp["dpd_min"] >= 90, "current_balance"].astype("float64").sum())
        else:
            ever90_bal = 0.0
        rows.append(VintageRow(
            str(v), int(len(grp)), orig_bal, cur_bal,
            int(co_mask.sum()), co_bal,
            (co_bal / orig_bal) if orig_bal else 0.0,
            (ever90_bal / orig_bal) if orig_bal else 0.0))
    return rows


@dataclass(frozen=True)
class Triangle:
    mob_bounds: tuple[int, ...]
    # vintage -> {mob_bound: cumulative gross-loss rate}
    rows: dict[str, dict[int, float]]


def loss_triangle(df: pd.DataFrame, grain: str = "year",
                  mob_bounds: tuple[int, ...] = (6, 12, 18, 24, 36)) -> Triangle:
    """Cumulative gross-loss rate by MOB, loss timed orig_date -> chargeoff_date."""
    for req in ("orig_date", "chargeoff_date", "chargeoff_balance"):
        if req not in df.columns:
            raise FeatureUnavailable("vintage_loss_triangle", f"field {req!r} not mapped")
    work = df.copy()
    work["__vintage__"] = work["orig_date"].map(lambda t: _period(t, grain))
    work["__origbal__"] = _orig_balance_series(work)
    work["__co_mob__"] = [
        _months_between(o, c)
        for o, c in zip(work["orig_date"], work["chargeoff_date"])]

    rows: dict[str, dict[int, float]] = {}
    for v, grp in work.groupby("__vintage__", sort=True):
        orig_bal = float(grp["__origbal__"].sum())
        rows[str(v)] = {}
        for m in mob_bounds:
            co = grp[(grp["__co_mob__"].notna()) & (grp["__co_mob__"] <= m)]
            cum = float(co["chargeoff_balance"].astype("float64").sum())
            rows[str(v)][m] = (cum / orig_bal) if orig_bal else 0.0
    return Triangle(tuple(mob_bounds), rows)


@dataclass(frozen=True)
class GrossChargeOff:
    dollar_rate: float          # Σ charged-off $ / Σ denominator $
    count_rate: float           # n charged off / N
    co_count: int
    co_dollars: float
    denominator_dollars: float
    basis_note: str = "GROSS charge-off (no recovery data); dollar AND count basis"


def gross_charge_off_rate(df: pd.DataFrame,
                          denom: str = "current_balance") -> GrossChargeOff:
    if "chargeoff_flag" not in df.columns or "chargeoff_balance" not in df.columns:
        raise FeatureUnavailable("gross_charge_off",
                                 "fields 'chargeoff_flag' + 'chargeoff_balance' not mapped")
    co = _truthy(df["chargeoff_flag"])
    n = int(len(df))
    co_dollars = float(df.loc[co, "chargeoff_balance"].astype("float64").sum())
    denom_field = "orig_amount" if (denom == "orig" and "orig_amount" in df.columns) else "current_balance"
    denom_dollars = float(df[denom_field].astype("float64").sum())
    return GrossChargeOff(
        (co_dollars / denom_dollars) if denom_dollars else 0.0,
        (int(co.sum()) / n) if n else 0.0,
        int(co.sum()), co_dollars, denom_dollars)
