"""Conditional single-period roll / transition matrix.

A one-row-per-loan snapshot can't produce roll rates on its own — but if the
file carries a **prior-period delinquency bucket** and the reviewer maps it, we
can compute one period of transitions (prior -> current) within the single
file, on both a dollar and a count basis. No prior-bucket column -> this simply
isn't produced (multi-snapshot machinery is a deferred non-goal).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from popbench.delinquency import BUCKET_IDS, BUCKET_LABEL, FeatureUnavailable, _bucket_for_label


@dataclass(frozen=True)
class RollMatrix:
    prior_buckets: list[str]                 # ordered canonical ids present as priors
    current_buckets: list[str]               # ordered canonical ids present as current
    dollar: dict[str, dict[str, float]]      # prior -> current -> rate ($ basis)
    count: dict[str, dict[str, float]]       # prior -> current -> rate (count basis)
    basis_note: str = "single-period prior->current; dollar AND count basis"


def roll_matrix(df: pd.DataFrame, weight: str = "current_balance") -> RollMatrix:
    if "prior_dpd_bucket" not in df.columns:
        raise FeatureUnavailable("roll_matrix", "field 'prior_dpd_bucket' not mapped")
    if "dpd_bucket_canon" not in df.columns:
        raise FeatureUnavailable("roll_matrix", "population not normalized (delinquency)")

    work = df.copy()
    prior = work["prior_dpd_bucket"].map(_bucket_for_label)
    if prior.isna().any():
        bad = work["prior_dpd_bucket"][prior.isna()].dropna().unique().tolist()
        raise ValueError(f"unmappable prior buckets {bad!r}")
    work["__prior__"] = prior
    cur = work["dpd_bucket_canon"]

    order = list(BUCKET_IDS)
    priors = [b for b in order if (work["__prior__"] == b).any()]
    currents = [b for b in order if (cur == b).any()]

    dollar: dict[str, dict[str, float]] = {}
    count: dict[str, dict[str, float]] = {}
    w = work[weight].astype("float64")
    for p in priors:
        pmask = work["__prior__"] == p
        p_dollars = float(w[pmask].sum())
        p_count = int(pmask.sum())
        dollar[p] = {}
        count[p] = {}
        for c in currents:
            moved = pmask & (cur == c)
            dollar[p][c] = (float(w[moved].sum()) / p_dollars) if p_dollars else 0.0
            count[p][c] = (int(moved.sum()) / p_count) if p_count else 0.0
    return RollMatrix(priors, currents, dollar, count)


def bucket_label(bucket_id: str) -> str:
    return BUCKET_LABEL.get(bucket_id, bucket_id)
