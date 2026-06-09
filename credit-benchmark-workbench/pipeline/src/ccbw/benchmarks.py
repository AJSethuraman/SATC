"""Benchmark construction: per-segment, per-size-bucket distributions.

For each (segment, size bucket, metric):
* current-year percentile distribution (p10/p25/p50/p75/p90, n),
* a pre-2020 baseline (pooled FY2015-2019 company-year observations) so a
  current reading can be judged against history rather than a possibly
  distorted recent period,
* a 3-year median trend,
* explicit coverage-gap notes wherever n is thin -- the smallest band is
  expected to be the thinnest in public data, and that is reported, not
  hidden.

Bucketing is by the company's *median* EBITDA across its panel years, not
the single-year EBITDA. The single-year choice lets a large company whose
EBITDA collapsed migrate INTO a smaller band and poison that band's
distributions with distress -- a $200M-EBITDA name fallen to $40M is a
distressed upper-middle-market credit, not a core-middle-market peer. The
size class is the company; the deterioration stays visible in its own
band's distribution and in the backtest.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .metrics import METRICS, Measurement, compute_measurements
from .panel import PanelRow
from .segments import BUCKET_BY_KEY, SEGMENTS, SIZE_BUCKETS, size_bucket_for_ebitda

THIN_N = 8          # below this, stats carry a thin-coverage warning
MIN_N = 3           # below this, percentiles are suppressed entirely
BASELINE_YEARS = (2015, 2019)
TREND_YEARS = 3


def percentile(sorted_vals: list[float], p: float) -> float:
    """Linear-interpolation percentile (inclusive), p in [0, 100]."""
    if not sorted_vals:
        raise ValueError("empty")
    k = (len(sorted_vals) - 1) * p / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def dist_stats(vals: list[float]) -> Optional[dict]:
    clean = sorted(v for v in vals if v is not None and not math.isnan(v))
    if len(clean) < MIN_N:
        return None
    return {
        "n": len(clean),
        "p10": percentile(clean, 10),
        "p25": percentile(clean, 25),
        "p50": percentile(clean, 50),
        "p75": percentile(clean, 75),
        "p90": percentile(clean, 90),
    }


@dataclass
class CompanyYearObs:
    """One company-year's measurements, tagged for grouping."""
    cik: int
    entity: str
    fy: int
    segment: str
    bucket: Optional[str]
    measurements: dict[str, Measurement]
    gaps: list[str] = field(default_factory=list)


def build_observations(
    panels: dict[int, list[PanelRow]],
    company_segments: dict[int, list[str]],
) -> list[CompanyYearObs]:
    """panels: cik -> rows ascending; company_segments: cik -> segment keys."""
    obs: list[CompanyYearObs] = []
    for cik, rows in panels.items():
        segs = company_segments.get(cik, [])
        if not segs:
            continue
        rows = sorted(rows, key=lambda r: r.fy)
        ebitdas = sorted(e for e in (r.get("ebitda") for r in rows)
                         if e is not None)
        company_bucket = None
        if ebitdas:
            median_ebitda = ebitdas[len(ebitdas) // 2]
            company_bucket = size_bucket_for_ebitda(median_ebitda)
        for seg in segs:
            for i, row in enumerate(rows):
                ms = compute_measurements(row, history=rows[:i], segment=seg)
                bucket = company_bucket
                obs.append(CompanyYearObs(
                    cik=cik, entity=row.entity, fy=row.fy, segment=seg,
                    bucket=bucket, measurements=ms, gaps=list(row.gaps),
                ))
    return obs


def _metric_values(group: list[CompanyYearObs], metric: str) -> tuple[list[float], int]:
    """Collect observations, winsorizing at the metric's analytic bounds.

    Clamping (not dropping) keeps distressed names in the distribution --
    a 30x leverage multiple on near-zero EBITDA is real distress, but as a
    raw value it destroys the percentile tails. Returns (values, n_clamped)
    so the clamping is disclosed on the benchmark cell.
    """
    wins = METRICS[metric].wins
    vals, clamped = [], 0
    for o in group:
        if metric not in o.measurements:
            continue
        v = o.measurements[metric].value
        if math.isnan(v):
            continue
        if wins:
            w = min(max(v, wins[0]), wins[1])
            if w != v:
                clamped += 1
            v = w
        vals.append(v)
    return vals, clamped


def build_benchmarks(
    obs: list[CompanyYearObs],
    current_fy: int,
) -> dict:
    """Produce the raw benchmark library (pre-adjustment).

    Structure: segments -> buckets -> metrics -> {current, baseline_pre2020,
    trend, coverage_gaps}. Every figure is labeled with its basis from the
    MetricSpec and its observation counts.
    """
    out: dict = {"current_fy": current_fy, "segments": {}}
    for seg_key, seg in SEGMENTS.items():
        seg_obs = [o for o in obs if o.segment == seg_key]
        seg_out = {"label": seg.label, "buckets": {}}
        for bucket in SIZE_BUCKETS:
            b_obs = [o for o in seg_obs if o.bucket == bucket.key]
            companies = {o.cik for o in b_obs}
            bucket_out: dict = {
                "label": bucket.label,
                "n_companies": len(companies),
                "coverage_gaps": [],
                "metrics": {},
            }
            metric_keys = [m for m in seg.primary_metrics if m in METRICS]
            # full metric set minus suppressions and segment-specific bases
            # that don't apply here, primary first
            inapplicable = set(seg.suppressed_metrics)
            if not seg.through_cycle_leverage:
                inapplicable.add("debt_ebitda_3y")
            if not seg.rent_adjusted:
                inapplicable.add("rent_adj_leverage")
            extras = [m for m in METRICS if m not in metric_keys
                      and m not in inapplicable]
            for mkey in metric_keys + extras:
                spec = METRICS[mkey]
                cur_vals, cur_clamped = _metric_values(
                    [o for o in b_obs if o.fy == current_fy], mkey)
                base_vals, base_clamped = _metric_values(
                    [o for o in b_obs
                     if BASELINE_YEARS[0] <= o.fy <= BASELINE_YEARS[1]], mkey)
                trend = []
                for fy in range(current_fy - TREND_YEARS + 1, current_fy + 1):
                    vals, _ = _metric_values([o for o in b_obs if o.fy == fy], mkey)
                    stats = dist_stats(vals)
                    if stats:
                        trend.append({"fy": fy, "p50": stats["p50"],
                                      "p25": stats["p25"], "p75": stats["p75"],
                                      "n": stats["n"]})
                cur = dist_stats(cur_vals)
                base = dist_stats(base_vals)
                gaps: list[str] = []
                if spec.wins and (cur_clamped or base_clamped):
                    gaps.append(
                        f"winsorized at analytic bounds [{spec.wins[0]:g}, "
                        f"{spec.wins[1]:g}]: {cur_clamped} current / "
                        f"{base_clamped} baseline observation(s) clamped "
                        "(distressed outliers kept, not dropped)")
                if cur is None:
                    gaps.append(
                        f"FY{current_fy}: n={len(cur_vals)} < {MIN_N}; current "
                        "distribution suppressed")
                elif cur["n"] < THIN_N:
                    gaps.append(
                        f"FY{current_fy}: thin coverage (n={cur['n']} "
                        f"company-years < {THIN_N}); percentiles unstable")
                if base is None:
                    gaps.append(
                        f"pre-2020 baseline (FY{BASELINE_YEARS[0]}-"
                        f"{BASELINE_YEARS[1]}): insufficient observations "
                        f"(n={len(base_vals)}); baseline suppressed")
                m_out = {
                    "label": spec.label,
                    "unit": spec.unit,
                    "direction": spec.direction,
                    "basis": spec.basis,
                    "primary": mkey in seg.primary_metrics,
                    "current": cur,
                    "baseline_pre2020": base,
                    "trend": trend,
                    "coverage_gaps": gaps,
                    "sources": [
                        f"Aggregated from {cur['n'] if cur else 0} company-FY "
                        f"observations, FY{current_fy}; baseline pooled "
                        f"FY{BASELINE_YEARS[0]}-{BASELINE_YEARS[1]} "
                        f"(n={base['n'] if base else 0}). Per-datapoint "
                        "provenance (CIK/accession/tag) in the panel file."
                    ],
                }
                bucket_out["metrics"][mkey] = m_out
            present = sum(1 for m in bucket_out["metrics"].values()
                          if m["current"] is not None)
            if len(companies) == 0:
                bucket_out["coverage_gaps"].append(
                    "No public companies fall in this EBITDA band for this "
                    "segment -- the public universe skews larger; rely on the "
                    "adjusted view of the nearest larger band and treat all "
                    "thresholds as indicative only.")
            elif len(companies) < 5:
                bucket_out["coverage_gaps"].append(
                    f"Only {len(companies)} public companies in this band "
                    "(public universe skews larger than private middle "
                    "market); distributions are indicative, not calibrated.")
            if present == 0 and len(companies) > 0:
                bucket_out["coverage_gaps"].append(
                    "Companies present but no metric met the minimum "
                    f"observation count ({MIN_N}).")
            seg_out["buckets"][bucket.key] = bucket_out
        seg_out["peer_definition"] = seg.peer_definition
        seg_out["normalization_rules"] = list(seg.normalization_rules)
        seg_out["cyclicality_treatment"] = seg.cyclicality_treatment
        out["segments"][seg_key] = seg_out
    return out
