"""Population-level metrics — weighted-average attributes, on two bases.

The research doc's convention (Area 4): balance-weight every "level" attribute
metric by current UPB, and always also produce the count-basis view. This
module computes both and labels which is which. It is pure pandas over the
*clean* canonical frame; it never touches Excel.

Later slices add delinquency/loss rates (both dollar and count), URCCP
classification, vintage, and roll matrices; the shape here — a labeled,
both-bases result — is the pattern they follow.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

WEIGHT_DEFAULT = "current_balance"


@dataclass(frozen=True)
class WAResult:
    """One weighted-average attribute, reported on both bases."""

    attribute: str
    dollar_weighted: float | None   # Σ(Bᵢ·xᵢ)/ΣBᵢ, weight = current UPB
    count_weighted: float | None    # Σxᵢ/N  ("typical account")
    weight_field: str
    n: int                          # rows contributing (attribute non-null)
    coverage_dollars: float         # Σ balance over contributing rows
    note: str = ""


def _clean_pair(df: pd.DataFrame, attribute: str, weight: str) -> pd.DataFrame:
    cols = df[[attribute, weight]].copy()
    return cols[cols[attribute].notna() & cols[weight].notna()]


def weighted_average(df: pd.DataFrame, attribute: str,
                     weight: str = WEIGHT_DEFAULT) -> WAResult:
    """Balance-weighted and count-weighted average of ``attribute``.

    Contributing rows are those with a non-null attribute *and* a non-null
    weight; ``n``/``coverage_dollars`` report the base so a reader sees exactly
    how much of the population the figure rests on (denominators never move
    silently — the cleaning gate already refused nulls in required fields).
    """
    pair = _clean_pair(df, attribute, weight)
    n = int(len(pair))
    if n == 0:
        return WAResult(attribute, None, None, weight, 0, 0.0, "no contributing rows")
    w = pair[weight].astype("float64")
    x = pair[attribute].astype("float64")
    total_w = float(w.sum())
    dollar = float((w * x).sum() / total_w) if total_w else None
    count = float(x.mean())
    note = "" if total_w else "zero total weight — dollar basis undefined"
    return WAResult(attribute, dollar, count, weight, n, total_w, note)


def population_totals(df: pd.DataFrame, weight: str = WEIGHT_DEFAULT) -> dict:
    """Headline counts/balances for a population or segment."""
    n = int(len(df))
    bal = float(df[weight].astype("float64").sum()) if weight in df.columns else 0.0
    return {"count": n, "total_balance": bal, "weight_field": weight}


def weighted_average_table(df: pd.DataFrame, attributes: list[str],
                           weight: str = WEIGHT_DEFAULT) -> list[WAResult]:
    """WA for each attribute present in the frame (missing attributes skipped —
    a WA whose field wasn't mapped simply isn't produced; feature-gating with a
    named-missing-field message is the caller's job)."""
    return [weighted_average(df, a, weight) for a in attributes if a in df.columns]
