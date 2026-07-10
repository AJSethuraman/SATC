"""Aggregation: revenue tiering, per-tier percentile distributions, cyclicality.

The product is the DISPERSION across size tiers, never a bare average. For each
metric, per tier, we report 10/25/50/75/90 percentiles, sample sizes, and a
through-cycle volatility read (median coefficient of variation across the
companies in that tier). Companies are ASSIGNED to a tier by most-recent-year
revenue; none are screened out by size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import stats
from .metrics import ALL_METRICS, CompanyYear, compute_metrics

DEFAULT_TIERS = "0-250M,250M-1B,1B-5B,5B+"


# --------------------------------------------------------------------------
# Tier definitions
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Tier:
    label: str
    low: float  # inclusive, USD
    high: Optional[float]  # exclusive, USD; None = open-ended

    def contains(self, revenue: float) -> bool:
        if revenue < self.low:
            return False
        if self.high is None:
            return True
        return revenue < self.high


_SUFFIX = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def _parse_amount(token: str) -> Optional[float]:
    token = token.strip().upper()
    if token in ("", "INF", "+"):
        return None
    mult = 1.0
    if token[-1] in _SUFFIX:
        mult = _SUFFIX[token[-1]]
        token = token[:-1]
    return float(token) * mult


def parse_tiers(spec: str) -> List[Tier]:
    """Parse a tier spec like ``0-250M,250M-1B,1B-5B,5B+`` into ``Tier``s.

    Each comma-separated band is ``low-high`` (USD, K/M/B/T suffixes allowed);
    a trailing ``+`` or omitted high makes the top band open-ended. Bands are
    sorted by lower bound for deterministic ordering.
    """
    tiers: List[Tier] = []
    for raw in spec.split(","):
        band = raw.strip()
        if not band:
            continue
        if band.endswith("+"):
            low = _parse_amount(band[:-1])
            tiers.append(Tier(label=band, low=low or 0.0, high=None))
            continue
        if "-" not in band:
            raise ValueError(f"Bad tier band '{band}': expected 'low-high' or 'low+'")
        lo_s, hi_s = band.split("-", 1)
        low = _parse_amount(lo_s) or 0.0
        high = _parse_amount(hi_s)
        tiers.append(Tier(label=band, low=low, high=high))
    tiers.sort(key=lambda t: t.low)
    return tiers


def assign_tier(revenue: Optional[float], tiers: Sequence[Tier]) -> Optional[Tier]:
    if revenue is None:
        return None
    for t in tiers:
        if t.contains(revenue):
            return t
    return None


# --------------------------------------------------------------------------
# Company-level rollup
# --------------------------------------------------------------------------
@dataclass
class CompanySeries:
    """All in-window fiscal years for one company, plus computed metrics."""

    cik: int
    name: str
    ticker: str
    records: List[CompanyYear]  # sorted by fiscal_year
    metrics_by_year: Dict[int, Dict[str, Optional[float]]] = field(default_factory=dict)

    @property
    def latest_year(self) -> Optional[int]:
        return self.records[-1].fiscal_year if self.records else None

    @property
    def latest_revenue(self) -> Optional[float]:
        return self.records[-1].revenue if self.records else None


def build_series(records: List[CompanyYear], years_window: int) -> Optional[CompanySeries]:
    """Filter a company's records to the lookback window and compute metrics.

    Window is relative to the company's most-recent in-data fiscal year so a
    7-year window keeps the latest 7 reported years even if reporting lags.
    """
    if not records:
        return None
    recs = sorted(records, key=lambda r: r.fiscal_year)
    latest = recs[-1].fiscal_year
    cutoff = latest - years_window + 1
    recs = [r for r in recs if r.fiscal_year >= cutoff]
    if not recs:
        return None
    first = recs[0]
    series = CompanySeries(cik=first.cik, name=first.name, ticker=first.ticker, records=recs)
    for r in recs:
        series.metrics_by_year[r.fiscal_year] = compute_metrics(r)
    return series


# --------------------------------------------------------------------------
# Per-tier distributions
# --------------------------------------------------------------------------
PERCENTILES = (10, 25, 50, 75, 90)


@dataclass
class MetricDist:
    metric: str
    p10: Optional[float] = None
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None
    n_company_years: int = 0
    n_companies: int = 0
    median_cv: Optional[float] = None  # through-cycle volatility (median across cos)


@dataclass
class RosterEntry:
    """One constituent company of a tier (for the readable roster)."""

    cik: int
    name: str
    ticker: str
    latest_revenue: Optional[float]
    n_years: int
    first_year: Optional[int]
    last_year: Optional[int]


@dataclass
class TierResult:
    tier: Tier
    n_companies: int
    low_confidence: bool
    # metric -> distribution
    current: Dict[str, MetricDist] = field(default_factory=dict)
    through_cycle: Dict[str, MetricDist] = field(default_factory=dict)
    shock_2020: Dict[str, Optional[float]] = field(default_factory=dict)
    roster: List[RosterEntry] = field(default_factory=list)


def _dist_from_values(metric: str, values: List[Optional[float]], n_companies: int,
                      cvs: Optional[List[Optional[float]]] = None,
                      allow_extremes: bool = True) -> MetricDist:
    xs = stats.clean(values)
    d = MetricDist(metric=metric, n_company_years=len(xs), n_companies=n_companies)
    if xs:
        d.p25 = stats.percentile(xs, 25)
        d.p50 = stats.percentile(xs, 50)
        d.p75 = stats.percentile(xs, 75)
        # 10th/90th only when the sample can support them.
        if allow_extremes and len(xs) >= 5:
            d.p10 = stats.percentile(xs, 10)
            d.p90 = stats.percentile(xs, 90)
    if cvs is not None:
        d.median_cv = stats.median(stats.clean(cvs))
    return d


def aggregate_tier(series_list: List[CompanySeries], tier: Tier, min_sample: int) -> TierResult:
    """Aggregate one tier's companies into current + through-cycle distributions."""
    n_companies = len(series_list)
    result = TierResult(
        tier=tier,
        n_companies=n_companies,
        low_confidence=n_companies < min_sample,
    )

    # Roster: largest-first by most-recent revenue, CIK as deterministic tiebreak.
    roster = [
        RosterEntry(
            cik=s.cik,
            name=s.name,
            ticker=s.ticker,
            latest_revenue=s.latest_revenue,
            n_years=len(s.records),
            first_year=s.records[0].fiscal_year if s.records else None,
            last_year=s.latest_year,
        )
        for s in series_list
    ]
    roster.sort(key=lambda r: (-(r.latest_revenue or 0.0), r.cik))
    result.roster = roster

    for metric in ALL_METRICS:
        # Through-cycle: every company-year value in the window.
        tc_values: List[Optional[float]] = []
        # Per-company CV across years (through-cycle volatility).
        company_cvs: List[Optional[float]] = []
        # Current norms: each company's most-recent-year value.
        current_values: List[Optional[float]] = []
        tc_company_count = 0
        cur_company_count = 0

        for s in series_list:
            per_year = [s.metrics_by_year[y].get(metric) for y in sorted(s.metrics_by_year)]
            clean_year_vals = stats.clean(per_year)
            if clean_year_vals:
                tc_values.extend(clean_year_vals)
                tc_company_count += 1
            company_cvs.append(stats.coefficient_of_variation(clean_year_vals))
            if s.latest_year is not None:
                cur_val = s.metrics_by_year[s.latest_year].get(metric)
                if cur_val is not None:
                    current_values.append(cur_val)
                    cur_company_count += 1

        result.through_cycle[metric] = _dist_from_values(
            metric, tc_values, tc_company_count, cvs=company_cvs
        )
        result.current[metric] = _dist_from_values(
            metric, current_values, cur_company_count
        )

    result.shock_2020 = _compute_2020_shock(series_list)
    return result


def _compute_2020_shock(series_list: List[CompanySeries]) -> Dict[str, Optional[float]]:
    """Median 2019->2020 change per metric, to surface the COVID shock.

    For margins (ratios) this is the change in percentage points; for other
    metrics it is the percent change. Returns ``None`` where <2 companies have
    both years, with key ``_n`` carrying the contributing-company count.
    """
    from .metrics import PERCENT_METRICS

    out: Dict[str, Optional[float]] = {}
    contributors = 0
    for metric in ALL_METRICS:
        deltas: List[float] = []
        for s in series_list:
            v19 = s.metrics_by_year.get(2019, {}).get(metric)
            v20 = s.metrics_by_year.get(2020, {}).get(metric)
            if v19 is None or v20 is None:
                continue
            if metric in PERCENT_METRICS:
                deltas.append(v20 - v19)  # change in pp
            else:
                if v19 == 0:
                    continue
                deltas.append((v20 - v19) / abs(v19))  # fractional change
        out[metric] = stats.median(deltas) if deltas else None
        contributors = max(contributors, len(deltas))
    out["_n"] = float(contributors)
    return out


def cross_tier_trend(metric: str, tier_results: List[TierResult]) -> str:
    """Describe how a metric's median moves as size DECREASES (large -> small).

    Tiers are presented small->large elsewhere; here we read the median from
    the largest tier down to the smallest to characterise the size trend.
    """
    ordered = sorted(tier_results, key=lambda tr: tr.tier.low, reverse=True)  # large -> small
    medians = [(tr.tier.label, tr.through_cycle[metric].p50) for tr in ordered]
    pts = [(lbl, v) for lbl, v in medians if v is not None]
    if len(pts) < 2:
        return "insufficient tiers with data to read a size trend"
    first_v = pts[0][1]
    last_v = pts[-1][1]
    if abs(first_v) < 1e-12:
        return "flat / undefined trend"
    change = (last_v - first_v) / abs(first_v)
    direction = "rises" if change > 0.05 else ("falls" if change < -0.05 else "is roughly flat")
    return (
        f"median {direction} moving from largest ({pts[0][0]}: {first_v:.2f}) "
        f"to smallest ({pts[-1][0]}: {last_v:.2f}) tier"
    )
