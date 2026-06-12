"""Concentration analysis: score band, origination vintage, line size.

Computed on the latest-month open snapshot.  Each dimension produces a
balance-share table and a Herfindahl-Hirschman index (sum of squared
balance shares; 1.0 = fully concentrated).  Dimensions whose driver field
is missing are skipped and logged as data-gap findings -- the vintage
dimension only needs Tier 0, while score band and line size need Tier 1.
"""

from __future__ import annotations

import pandas as pd

from ucpa.data_model import (
    F_ACCOUNT_ID,
    F_BALANCE,
    F_CREDIT_LIMIT,
    F_ORIGINATION_DATE,
    F_SCORE_BAND,
    LINE_SIZE_EDGES,
    LINE_SIZE_LABELS,
    SCORE_BANDS,
)
from ucpa.metrics.common import latest_snapshot
from ucpa.metrics.results import (
    STATUS_COMPUTED,
    STATUS_PARTIAL,
    DataGapFinding,
    MetricResult,
)
from ucpa.tier_detector import field_present


def _share_table(snapshot: pd.DataFrame, key: pd.Series, order: list[str]) -> pd.DataFrame:
    df = snapshot.assign(_cat=key.astype(str).to_numpy())
    grouped = df.groupby("_cat", sort=False).agg(
        accounts=(F_ACCOUNT_ID, "nunique"), balance=(F_BALANCE, "sum")
    )
    grouped = grouped.reindex(order, fill_value=0.0)
    grouped["accounts"] = grouped["accounts"].fillna(0).astype(int)
    total = float(grouped["balance"].sum())
    grouped["balance_share"] = grouped["balance"] / total if total else 0.0
    grouped.index.name = "category"
    return grouped.reset_index()


def _hhi(table: pd.DataFrame) -> float:
    return float((table["balance_share"] ** 2).sum())


def compute_concentration(tape: pd.DataFrame) -> MetricResult:
    """Balance concentration by score band, vintage year, and line size."""
    snap = latest_snapshot(tape)
    tables: dict[str, pd.DataFrame] = {}
    gaps: list[DataGapFinding] = []
    summary: dict[str, object] = {}

    # Vintage year (Tier 0).
    vintage_year = pd.PeriodIndex(snap[F_ORIGINATION_DATE], freq="Y").astype(str)
    order = sorted(pd.unique(vintage_year))
    vt = _share_table(snap, pd.Series(vintage_year, index=snap.index), order)
    tables["by_vintage_year"] = vt
    summary["max_vintage_year_share"] = float(vt["balance_share"].max()) if len(vt) else 0.0
    summary["vintage_hhi"] = _hhi(vt)

    # Score band (Tier 1).
    if field_present(snap, F_SCORE_BAND):
        bt = _share_table(snap, snap[F_SCORE_BAND], list(SCORE_BANDS))
        tables["by_score_band"] = bt
        shares = bt.set_index("category")["balance_share"]
        summary["subprime_balance_share"] = float(shares.get("SUBPRIME", 0.0))
        summary["below_prime_balance_share"] = float(
            shares.get("SUBPRIME", 0.0) + shares.get("NEAR_PRIME", 0.0)
        )
        summary["score_band_hhi"] = _hhi(bt)
    else:
        gaps.append(
            DataGapFinding(
                metric="concentration",
                scope="score_band",
                missing_fields=(F_SCORE_BAND,),
                tier_required=1,
                description="Score-band concentration requires a risk grade or score band per account.",
            )
        )

    # Line size (Tier 1).
    if field_present(snap, F_CREDIT_LIMIT):
        buckets = pd.cut(
            snap[F_CREDIT_LIMIT],
            bins=list(LINE_SIZE_EDGES),
            labels=list(LINE_SIZE_LABELS),
            right=False,
        )
        lt = _share_table(snap, buckets, list(LINE_SIZE_LABELS))
        tables["by_line_size"] = lt
        summary["max_line_size_share"] = float(lt["balance_share"].max()) if len(lt) else 0.0
    else:
        gaps.append(
            DataGapFinding(
                metric="concentration",
                scope="line_size",
                missing_fields=(F_CREDIT_LIMIT,),
                tier_required=1,
                description="Line-size concentration requires the credit limit per account.",
            )
        )

    return MetricResult(
        metric="concentration",
        status=STATUS_PARTIAL if gaps else STATUS_COMPUTED,
        summary=summary,
        tables=tables,
        gaps=gaps,
    )
