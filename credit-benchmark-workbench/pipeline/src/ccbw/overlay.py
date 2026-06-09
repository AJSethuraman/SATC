"""Private-borrower overlay: peer positioning, departure flags, and
departure-vs-normalization framing.

Input: a private borrower's figures (1-3 fiscal years). Output: each metric
positioned within the *adjusted* peer distribution, severity-graded flags,
and -- where history is available -- an explicit framing of whether the
metric is moving away from the peer baseline (structural departure) or
toward it (normalization), with the mechanism note attached.

Severity grading against the adjusted distribution (direction-aware):
    in_range  : inside p25-p75
    watch     : beyond p75 risky side (or p25 for lower-is-riskier)
    departure : beyond p90 risky side (or p10)
    severe    : beyond the survivorship-extended tail by a further 25% of IQR,
                or a structurally meaningless reading (e.g. negative EBITDA)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .mechanisms import mechanism_for
from .metrics import HIGHER_RISK, METRICS
from .segments import SEGMENTS

SEVERITY_ORDER = ["in_range", "watch", "departure", "severe"]


@dataclass
class BorrowerYear:
    """One fiscal year of borrower financials, USD raw units (enter 12.5e6
    for $12.5M). All fields optional except fy; metrics needing missing
    inputs are skipped with a gap note."""
    fy: int
    revenue: Optional[float] = None
    ebitda: Optional[float] = None            # lender-normalized EBITDA OK; basis-labeled
    total_debt: Optional[float] = None
    cash: Optional[float] = None
    interest_expense: Optional[float] = None
    capex: Optional[float] = None
    cogs: Optional[float] = None
    receivables: Optional[float] = None
    inventory: Optional[float] = None
    payables: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_assets: Optional[float] = None
    rent_expense: Optional[float] = None


def borrower_ratios(years: list[BorrowerYear], segment: str) -> dict[int, dict[str, float]]:
    """Compute the same ratio set as the public panel, per borrower year."""
    seg = SEGMENTS[segment]
    out: dict[int, dict[str, float]] = {}
    ys = sorted(years, key=lambda y: y.fy)
    for i, y in enumerate(ys):
        r: dict[str, float] = {}
        if y.ebitda and y.ebitda > 0:
            if y.total_debt is not None:
                r["debt_ebitda"] = y.total_debt / y.ebitda
                if y.cash is not None:
                    r["net_debt_ebitda"] = (y.total_debt - y.cash) / y.ebitda
            if y.revenue and y.revenue > 0:
                r["ebitda_margin"] = y.ebitda / y.revenue * 100
        elif y.ebitda is not None and y.ebitda <= 0:
            r["debt_ebitda"] = float("nan")  # graded severe downstream
        if y.interest_expense and y.interest_expense > 0 and y.ebitda is not None:
            r["interest_coverage"] = y.ebitda / y.interest_expense
            if y.capex is not None:
                r["fcc_proxy"] = (y.ebitda - y.capex) / y.interest_expense
        if y.revenue and y.revenue > 0:
            if y.cogs is not None:
                r["gross_margin"] = (y.revenue - y.cogs) / y.revenue * 100
            if y.receivables is not None:
                r["dso"] = y.receivables / y.revenue * 365
        if y.cogs and y.cogs > 0:
            if y.inventory is not None:
                r["dio"] = y.inventory / y.cogs * 365
            if y.payables is not None:
                r["dpo"] = y.payables / y.cogs * 365
        if all(k in r for k in ("dso", "dio", "dpo")):
            r["ccc"] = r["dso"] + r["dio"] - r["dpo"]
        if y.current_assets is not None and y.current_liabilities:
            r["current_ratio"] = y.current_assets / y.current_liabilities
        if y.total_assets and y.total_debt is not None:
            r["debt_assets"] = y.total_debt / y.total_assets * 100
        if seg.rent_adjusted and y.rent_expense is not None \
                and y.ebitda is not None and y.total_debt is not None:
            ebitdar = y.ebitda + y.rent_expense
            if ebitdar > 0:
                r["rent_adj_leverage"] = (y.total_debt + 8 * y.rent_expense) / ebitdar
        if seg.through_cycle_leverage and y.total_debt is not None and i >= 2:
            window = [p.ebitda for p in ys[i - 2:i + 1] if p.ebitda is not None]
            if len(window) == 3 and sum(window) > 0:
                r["debt_ebitda_3y"] = y.total_debt / (sum(window) / 3)
        prev = ys[i - 1] if i > 0 else None
        if prev and prev.revenue and y.revenue and prev.fy == y.fy - 1:
            r["rev_growth"] = (y.revenue / prev.revenue - 1) * 100
        # drop suppressed metrics for the segment
        for sk in seg.suppressed_metrics:
            r.pop(sk, None)
        out[y.fy] = r
    return out


def interp_percentile(value: float, dist: dict) -> float:
    """Approximate the borrower's percentile within a p10..p90 summary by
    piecewise-linear interpolation; clamped to [2, 98] outside the tails."""
    knots = [(2.0, None), (10, "p10"), (25, "p25"), (50, "p50"),
             (75, "p75"), (90, "p90"), (98.0, None)]
    pts = [(p, dist[k]) for p, k in knots if k]
    if value <= pts[0][1]:
        return 2.0 if value < pts[0][1] else 10.0
    if value >= pts[-1][1]:
        return 98.0 if value > pts[-1][1] else 90.0
    for (p0, v0), (p1, v1) in zip(pts, pts[1:]):
        if v0 <= value <= v1:
            if v1 == v0:
                return (p0 + p1) / 2
            return p0 + (p1 - p0) * (value - v0) / (v1 - v0)
        if v1 < v0:  # non-monotonic summary (degenerate); fall back to median side
            return 50.0
    return 50.0


def grade(value: float, dist: dict, direction: str) -> str:
    if math.isnan(value):
        return "severe"
    iqr = abs(dist["p75"] - dist["p25"])
    if direction == HIGHER_RISK:
        if value > dist["p90"] + 0.25 * iqr:
            return "severe"
        if value > dist["p90"]:
            return "departure"
        if value > dist["p75"]:
            return "watch"
    else:
        if value < dist["p10"] - 0.25 * iqr:
            return "severe"
        if value < dist["p10"]:
            return "departure"
        if value < dist["p25"]:
            return "watch"
    return "in_range"


def departure_framing(
    metric: str,
    values_by_fy: dict[int, float],
    peer_median: float,
    direction: str,
) -> dict:
    """Classify the borrower's trajectory relative to the peer baseline.

    structural_departure : outside and moving away (gap widening)
    normalization        : outside but moving toward the peer median
    persistent_departure : outside, gap roughly static (< 10% relative move)
    stable_in_range      : inside the band (handled by caller for messaging)
    """
    fys = sorted(values_by_fy)
    latest = values_by_fy[fys[-1]]
    if len(fys) < 2 or math.isnan(latest):
        return {"classification": "single_period",
                "narrative": ("Single-period figure: departure vs. "
                              "normalization cannot be distinguished without "
                              "at least two fiscal years -- obtain history "
                              "before treating the gap as structural.")}
    prior = values_by_fy[fys[0]]
    gap_now = latest - peer_median
    gap_then = prior - peer_median
    per_yr = (abs(gap_now) - abs(gap_then)) / (fys[-1] - fys[0])
    rel_move = ((abs(gap_now) - abs(gap_then)) / abs(gap_then)
                if gap_then not in (0,) and abs(gap_then) > 1e-12 else None)

    if rel_move is not None and abs(rel_move) < 0.10:
        cls = "persistent_departure"
        narrative = (
            f"Gap to peer median roughly static over FY{fys[0]}-FY{fys[-1]} "
            "-- a persistent structural departure. The question is whether "
            "the business model explains a permanently different level, not "
            "when it will revert.")
    elif abs(gap_now) < abs(gap_then):
        cls = "normalization"
        narrative = (
            f"Moving toward the peer baseline (gap closing ~"
            f"{abs(per_yr):.2g}/yr since FY{fys[0]}) -- reads as "
            "normalization toward the segment norm rather than new "
            "deterioration; confirm the driver is durable, not one-off.")
    else:
        cls = "structural_departure"
        narrative = (
            f"Moving away from the peer baseline (gap widening ~"
            f"{abs(per_yr):.2g}/yr since FY{fys[0]}) -- a structural "
            "departure in motion, the pattern that precedes migration to "
            "criticized status; mechanism review warranted now.")
    return {"classification": cls, "narrative": narrative,
            "gap_now": gap_now, "gap_prior": gap_then}


@dataclass
class OverlayResult:
    segment: str
    bucket: str
    fy: int
    metrics: dict[str, dict] = field(default_factory=dict)
    coverage_gaps: list[str] = field(default_factory=list)


def overlay_borrower(
    years: list[BorrowerYear],
    segment: str,
    bucket: str,
    adjusted_benchmarks: dict,
    view: str = "adjusted",
) -> OverlayResult:
    """Position a borrower against the (segment, bucket) benchmark set.

    ``view`` selects which distribution grades the flags: 'adjusted'
    (default -- the private-calibrated view) or 'raw' (for side-by-side
    challenge). Both distributions are attached to every metric regardless.
    """
    seg_b = adjusted_benchmarks["segments"][segment]["buckets"][bucket]
    ratios = borrower_ratios(years, segment)
    fys = sorted(ratios)
    latest_fy = fys[-1]
    res = OverlayResult(segment=segment, bucket=bucket, fy=latest_fy,
                        coverage_gaps=list(seg_b.get("coverage_gaps", [])))

    for mkey, value in ratios[latest_fy].items():
        mb = seg_b["metrics"].get(mkey)
        if mb is None:
            continue
        raw_cur = mb.get("current")
        adj_cur = (mb.get("adjusted") or {}).get("current")
        use = adj_cur if view == "adjusted" else raw_cur
        entry: dict = {
            "value": value,
            "unit": mb["unit"],
            "basis": mb["basis"],
            "label": mb["label"],
            "raw_dist": raw_cur,
            "adjusted_dist": adj_cur,
            "baseline_pre2020": mb.get("baseline_pre2020"),
            "adjusted_baseline": (mb.get("adjusted") or {}).get("baseline_pre2020"),
            "adjustment_note": mb.get("adjustment_note"),
            "coverage_gaps": list(mb.get("coverage_gaps", [])),
            "sources": mb.get("sources", []),
            "mechanism": mechanism_for(mkey, segment),
        }
        if use is None:
            entry["flag"] = "no_benchmark"
            entry["framing"] = {
                "classification": "no_benchmark",
                "narrative": "Peer distribution suppressed for thin coverage "
                             "-- no defensible comparison at this size band; "
                             "see coverage gaps."}
        else:
            entry["percentile"] = (None if math.isnan(value)
                                   else interp_percentile(value, use))
            entry["flag"] = grade(value, use, mb["direction"])
            if entry["flag"] == "in_range":
                entry["framing"] = {
                    "classification": "stable_in_range",
                    "narrative": "Within the adjusted interquartile peer "
                                 "range; no departure to frame."}
            else:
                hist = {fy: ratios[fy][mkey] for fy in fys if mkey in ratios[fy]}
                entry["framing"] = departure_framing(
                    mkey, hist, use["p50"], mb["direction"])
        res.metrics[mkey] = entry

    # borrower-side gaps: inputs that blocked primary metrics
    seg_spec = SEGMENTS[segment]
    for pm in seg_spec.primary_metrics:
        if pm in METRICS and pm not in res.metrics:
            res.coverage_gaps.append(
                f"{METRICS[pm].label}: not computable from the inputs "
                "provided (missing borrower fields) -- a primary metric for "
                "this segment is unverified.")
    return res
