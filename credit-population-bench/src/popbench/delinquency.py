"""Delinquency normalization, dollar/count rates, and URCCP classification.

The file may carry its delinquency signal in any of three forms — an actual DPD
day count, a pre-bucketed aging label, or a status code — and the reviewer maps
whichever one it has. This module normalizes all three to the canonical
delinquency buckets (recording the mapping for the ``_cleaning`` audit),
computes delinquency rates on **both a dollar and a count basis** (every value
basis-labeled) with cumulative 30+/60+/90+ roll-ups, and classifies the pool
per URCCP using the **shared floors** — so the 90/120/180 constants are the same
ones ``credit-review-os`` enforces.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from satc_credit_core.urccp import resolve_classification_dpd

from popbench import contract
from popbench.cleaning import CleaningRecord
from popbench.mapping import Mapping

# Canonical delinquency buckets (finer display grade; PRD §Slice-3). Each is
# (id, label, low DPD). Classification uses the low bound, so a loan in
# "90-119" is >=90 and a loan with an exact day count classifies on its days.
BUCKETS: tuple[tuple[str, str, int], ...] = (
    ("current", "Current", 0),
    ("dpd_1_29", "1-29 DPD", 1),
    ("dpd_30_59", "30-59 DPD", 30),
    ("dpd_60_89", "60-89 DPD", 60),
    ("dpd_90_119", "90-119 DPD", 90),
    ("dpd_120_149", "120-149 DPD", 120),
    ("dpd_150_179", "150-179 DPD", 150),
    ("dpd_180_plus", "180+ DPD", 180),
)
BUCKET_IDS = tuple(b[0] for b in BUCKETS)
BUCKET_LABEL = {b[0]: b[1] for b in BUCKETS}
_BUCKET_LOW = {b[0]: b[2] for b in BUCKETS}
_LOWS_DESC = sorted(BUCKETS, key=lambda b: b[2], reverse=True)  # for day-count binning
CLASSIFICATION_TYPES = ("closed_end", "open_end", "residential_secured")
RESIDENTIAL_LTV_QUALIFIER = 0.60   # URCCP residential ≥90-DPD qualifier (a knob)


class FeatureUnavailable(ValueError):
    """A requested analysis needs a field that was not mapped."""

    def __init__(self, feature: str, missing: str):
        self.feature = feature
        self.missing = missing
        super().__init__(f"analysis {feature!r} unavailable: {missing}")


# --- form resolution -------------------------------------------------------

def delinquency_form(mapping: Mapping) -> str:
    """Which of the three delinquency forms is mapped. Prefers the day count
    (most precise). Raises FeatureUnavailable if none is mapped."""
    for form in contract.DELINQUENCY_FORMS:
        if mapping.has(form):
            return form
    raise FeatureUnavailable(
        "delinquency",
        "map one of a DPD day count, an aging bucket, or a status code "
        f"({', '.join(contract.DELINQUENCY_FORMS)})")


def _bucket_for_days(days: float) -> str:
    for bid, _label, low in _LOWS_DESC:
        if days >= low:
            return bid
    return "current"


def _bucket_for_label(raw: str) -> str | None:
    """Map an aging label to a canonical bucket by its leading DPD number.
    'Current'/'0' -> current; '180+' -> dpd_180_plus; '90-119' -> dpd_90_119."""
    s = str(raw).strip().lower()
    if s in ("current", "curr", "0", "c", "performing"):
        return "current"
    m = re.search(r"\d+", s)
    if not m:
        return None
    return _bucket_for_days(int(m.group(0)))


def normalize(df: pd.DataFrame, mapping: Mapping,
              status_map: dict[str, str] | None = None,
              ) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Add ``dpd_bucket_canon`` (+ ``dpd_min`` low bound) from whichever form is
    mapped. Unmappable values are a hard error (raised as ValueError) — the
    population is meant to be clean before this runs."""
    form = delinquency_form(mapping)
    out = df.copy()
    records: list[CleaningRecord] = []

    if form == "dpd_days":
        days = out["dpd_days"].astype("float64")
        out["dpd_bucket_canon"] = days.map(_bucket_for_days)
        records.append(CleaningRecord("bucketize_dpd_days", "dpd_days",
                                      int(days.notna().sum()),
                                      "binned day count to canonical buckets"))
    elif form == "dpd_bucket":
        mapped = out["dpd_bucket"].map(_bucket_for_label)
        bad = out["dpd_bucket"][mapped.isna()].dropna().unique().tolist()
        if bad:
            raise ValueError(f"unmappable aging labels {bad!r}; add them upstream")
        out["dpd_bucket_canon"] = mapped
        records.append(CleaningRecord("map_aging_label", "dpd_bucket",
                                      int(mapped.notna().sum()),
                                      "aging labels -> canonical buckets"))
    else:  # dpd_status
        smap = {str(k).strip().lower(): v for k, v in (status_map or {}).items()}
        mapped = out["dpd_status"].astype("string").str.strip().str.lower().map(smap)
        bad = out["dpd_status"][mapped.isna()].dropna().unique().tolist()
        if bad:
            raise ValueError(
                f"status codes {bad!r} have no [DELQ_STATUS] mapping; declare them")
        out["dpd_bucket_canon"] = mapped
        records.append(CleaningRecord("map_status_code", "dpd_status",
                                      int(mapped.notna().sum()),
                                      "status codes -> canonical buckets"))

    out["dpd_min"] = out["dpd_bucket_canon"].map(_BUCKET_LOW).astype("float64")
    return out, records


# --- delinquency rates (dollar AND count) ----------------------------------

@dataclass(frozen=True)
class RateRow:
    label: str
    count: int
    dollars: float
    count_rate: float       # n_bucket / N
    dollar_rate: float      # $_bucket / $total


def delinquency_rates(df: pd.DataFrame, weight: str = "current_balance") -> dict:
    """Per-bucket and cumulative (30+/60+/90+) delinquency rates on BOTH bases.

    Requires the frame to have been through :func:`normalize`."""
    if "dpd_min" not in df.columns:
        raise FeatureUnavailable("delinquency", "population not normalized")
    n = int(len(df))
    total_bal = float(df[weight].astype("float64").sum())

    def _row(label: str, mask: pd.Series) -> RateRow:
        sub = df[mask]
        cnt = int(len(sub))
        dol = float(sub[weight].astype("float64").sum())
        return RateRow(label, cnt, dol,
                       (cnt / n) if n else 0.0,
                       (dol / total_bal) if total_bal else 0.0)

    per_bucket = [_row(BUCKET_LABEL[bid], df["dpd_bucket_canon"] == bid)
                  for bid in BUCKET_IDS]
    cumulative = [_row(f"{t}+ DPD (cumulative)", df["dpd_min"] >= t)
                  for t in (30, 60, 90)]
    return {"n": n, "total_balance": total_bal,
            "per_bucket": per_bucket, "cumulative": cumulative,
            "basis_note": "each row shows BOTH count basis (n/N) and dollar basis ($/$)"}


# --- URCCP classification (shared floors) ----------------------------------

@dataclass(frozen=True)
class ClassRow:
    structure: str
    count: int
    balance: float
    substandard_count: int
    substandard_dollars: float
    loss_count: int | None
    loss_dollars: float | None
    note: str = ""


def classify_urccp(df: pd.DataFrame, overrides: dict | None = None,
                   weight: str = "current_balance",
                   ltv_qualifier: float = RESIDENTIAL_LTV_QUALIFIER) -> list[ClassRow]:
    """Classify the pool per URCCP, per structure present in the frame.

    Closed/open-end: Substandard = balances/counts with DPD >= substandard floor
    (90); Loss = DPD >= loss floor (120 closed / 180 open). Residential-secured:
    Substandard = qualifying >=90-DPD balances with LTV > the qualifier line
    (60% knob); Loss is a fair-value writedown (an attestation) and is reported
    as N/A here rather than computed (PRD non-goal). All figures use the SHARED
    floors from ``satc_credit_core``.
    """
    if "structure" not in df.columns:
        raise FeatureUnavailable("urccp", "field 'structure' not mapped")
    if "dpd_min" not in df.columns:
        raise FeatureUnavailable("urccp", "population not normalized (delinquency)")

    rows: list[ClassRow] = []
    for structure, grp in df.groupby("structure", sort=True):
        struct = str(structure)
        bal = grp[weight].astype("float64")
        total_bal = float(bal.sum())
        cnt = int(len(grp))
        if struct in ("closed_end", "open_end"):
            clk = resolve_classification_dpd(struct, overrides)
            sub_mask = grp["dpd_min"] >= clk["substandard_from_dpd"]
            loss_mask = grp["dpd_min"] >= clk["loss_from_dpd"]
            rows.append(ClassRow(
                struct, cnt, total_bal,
                int(sub_mask.sum()), float(bal[sub_mask].sum()),
                int(loss_mask.sum()), float(bal[loss_mask].sum())))
        elif struct == "residential_secured":
            if "ltv" not in grp.columns:
                rows.append(ClassRow(struct, cnt, total_bal, 0, 0.0, None, None,
                                     "residential Substandard needs LTV — field not mapped"))
                continue
            sub_mask = (grp["dpd_min"] >= 90) & (grp["ltv"].astype("float64") > ltv_qualifier)
            rows.append(ClassRow(
                struct, cnt, total_bal,
                int(sub_mask.sum()), float(bal[sub_mask].sum()), None, None,
                f"Loss = fair-value writedown (attestation), not computed; "
                f"Substandard qualifier LTV > {ltv_qualifier:.0%}"))
        else:
            rows.append(ClassRow(struct, cnt, total_bal, 0, 0.0, None, None,
                                 f"unknown structure {struct!r} — not classified"))
    return rows
