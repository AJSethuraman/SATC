"""Validation: established failure models + deterioration backtest.

Private-middle-market default data is not publicly pullable, so validation
uses public proxies (directional checks, not calibration proof):

* **Altman Z' (private-firm revision)** -- book equity replaces market cap:
  Z' = 0.717*WC/TA + 0.847*RE/TA + 3.107*EBIT/TA + 0.420*BVE/TL + 0.998*S/TA.
  Zones: < 1.23 distress, 1.23-2.90 grey, > 2.90 safe. Chosen over the
  original Z because the user's borrowers are private (no market equity).
* **Ohlson O-score** -- nine-factor logit; the original deflates total
  assets by the GNP price index (base 1968). We use log of total assets in
  $M as the size term, which preserves ordering; absolute O-score levels are
  therefore comparative, not calibrated PDs -- noted in output.
* **Beaver's univariate ratio** -- CFO / total liabilities, the strongest
  single predictor in Beaver (1966).

The backtest asks the question that matters for a challenge function: when
the workbench's departure flags fire, does the name subsequently
deteriorate, and with how much lead time? Deterioration (public proxy for
migration to non-accrual) = within the horizon, any of: interest coverage
< 1.0x, EBITDA down >= 40% from the flag year, Z' newly in the distress
zone, or negative book equity. Reported: hit rate, capture rate, false
positives, and the lead-time distribution -- against rating-study
expectations that real warnings should lead distress by 1-3 years.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import median
from typing import Optional

from .metrics import METRICS
from .overlay import grade
from .panel import PanelRow

# ------------------------------------------------------------------ #
# Established failure models (reference flaggers)
# ------------------------------------------------------------------ #


def altman_z_private(row: PanelRow) -> Optional[float]:
    ta = row.get("total_assets")
    tl = row.get("total_liabilities")
    if not ta or ta <= 0:
        return None
    ca = row.get("current_assets")
    cl = row.get("current_liabilities")
    wc = (ca - cl) if ca is not None and cl is not None else None
    re_ = row.get("retained_earnings")
    ebit = row.get("operating_income")
    sales = row.get("revenue")
    bve = row.get("equity")
    if tl is None and bve is not None:
        tl = ta - bve
    if None in (wc, re_, ebit, sales, bve) or not tl or tl <= 0:
        return None
    return (0.717 * wc / ta + 0.847 * re_ / ta + 3.107 * ebit / ta
            + 0.420 * bve / tl + 0.998 * sales / ta)


Z_DISTRESS = 1.23
Z_SAFE = 2.90


def ohlson_o(row: PanelRow, prior: Optional[PanelRow] = None) -> Optional[float]:
    ta = row.get("total_assets")
    tl = row.get("total_liabilities")
    if tl is None and row.get("equity") is not None and ta:
        tl = ta - row.get("equity")
    ca, cl = row.get("current_assets"), row.get("current_liabilities")
    ni = row.get("net_income")
    cfo = row.get("operating_cash_flow")
    if None in (ta, tl, ca, cl, ni) or ta <= 0 or tl <= 0 or ca <= 0:
        return None
    wc = ca - cl
    size = math.log(ta / 1e6)  # $M; ordering-preserving stand-in for the
    # GNP-deflated original -- levels are comparative, not calibrated PDs.
    x = (-1.32 - 0.407 * size + 6.03 * tl / ta - 1.43 * wc / ta
         + 0.0757 * cl / ca - 1.72 * (1.0 if tl > ta else 0.0)
         - 2.37 * ni / ta
         - 1.83 * (cfo / tl if cfo is not None else 0.0)
         + 0.285 * (1.0 if (ni < 0 and prior is not None
                            and (prior.get("net_income") or 0) < 0) else 0.0))
    ni_prev = prior.get("net_income") if prior else None
    if ni_prev is not None and (abs(ni) + abs(ni_prev)) > 0:
        x += -0.521 * (ni - ni_prev) / (abs(ni) + abs(ni_prev))
    return x


def ohlson_probability(o: float) -> float:
    return 1.0 / (1.0 + math.exp(-o))


def beaver_cfo_tl(row: PanelRow) -> Optional[float]:
    cfo = row.get("operating_cash_flow")
    ta = row.get("total_assets")
    tl = row.get("total_liabilities")
    if tl is None and row.get("equity") is not None and ta:
        tl = ta - row.get("equity")
    if cfo is None or not tl or tl <= 0:
        return None
    return cfo / tl


# ------------------------------------------------------------------ #
# Deterioration events (public proxy for migration to non-accrual)
# ------------------------------------------------------------------ #


def deterioration_event(
    rows: list[PanelRow], flag_fy: int, horizon: int = 3
) -> Optional[dict]:
    """First deterioration within (flag_fy, flag_fy + horizon]."""
    by_fy = {r.fy: r for r in rows}
    base = by_fy.get(flag_fy)
    base_ebitda = base.get("ebitda") if base else None
    base_z = altman_z_private(base) if base else None
    for fy in range(flag_fy + 1, flag_fy + horizon + 1):
        r = by_fy.get(fy)
        if r is None:
            continue
        reasons = []
        ebitda, interest = r.get("ebitda"), r.get("interest_expense")
        if ebitda is not None and interest and interest > 0 and ebitda / interest < 1.0:
            reasons.append("interest coverage < 1.0x")
        if (base_ebitda and base_ebitda > 0 and ebitda is not None
                and ebitda <= 0.6 * base_ebitda):
            reasons.append("EBITDA decline >= 40% from flag year")
        z = altman_z_private(r)
        if z is not None and z < Z_DISTRESS and (base_z is None or base_z >= Z_DISTRESS):
            reasons.append(f"Altman Z' entered distress zone ({z:.2f} < {Z_DISTRESS})")
        eq = r.get("equity")
        if eq is not None and eq < 0:
            reasons.append("negative book equity")
        if reasons:
            return {"fy": fy, "lead_time": fy - flag_fy, "reasons": reasons}
    return None


# ------------------------------------------------------------------ #
# Backtest
# ------------------------------------------------------------------ #

CORE_FLAG_METRICS = ("debt_ebitda", "interest_coverage")


def severity_profile(obs_measurements: dict, seg_bucket_metrics: dict) -> dict[str, str]:
    """Grade every available metric against its ADJUSTED distribution."""
    severities: dict[str, str] = {}
    for mkey, meas in obs_measurements.items():
        mb = seg_bucket_metrics.get(mkey)
        if not mb:
            continue
        dist = (mb.get("adjusted") or {}).get("current")
        if not dist:
            continue
        severities[mkey] = grade(meas.value, dist, mb["direction"])
    return severities


def _is_adverse(s: str) -> bool:
    return s in ("watch", "departure", "severe")


def workbench_flag_rule(sev: dict[str, str]) -> Optional[str]:
    """The production flag rule (refined in backtesting -- see the rule
    comparison in the validation report): fire on any 'severe' reading, or
    'departure'-or-worse on a core risk metric (leverage / coverage)."""
    if any(s == "severe" for s in sev.values()):
        return "severe_metric"
    if any(sev.get(m) in ("departure", "severe") for m in CORE_FLAG_METRICS):
        return "core_departure"
    return None


# Candidate rules kept under test so every backtest regenerates the
# refinement evidence rather than citing a stale experiment.
ALT_RULES: dict[str, "callable"] = {
    "production: any severe | core departure": workbench_flag_rule,
    "core departure only": lambda sev: (
        "flag" if any(sev.get(m) in ("departure", "severe")
                      for m in CORE_FLAG_METRICS) else None),
    "loose: core departure | >=2 watch+ (rejected)": lambda sev: (
        "flag" if (any(sev.get(m) in ("departure", "severe")
                       for m in CORE_FLAG_METRICS)
                   or sum(1 for s in sev.values() if _is_adverse(s)) >= 2)
        else None),
    "core departure | >=2 watch+ incl core": lambda sev: (
        "flag" if (any(sev.get(m) in ("departure", "severe")
                       for m in CORE_FLAG_METRICS)
                   or (sum(1 for s in sev.values() if _is_adverse(s)) >= 2
                       and any(_is_adverse(sev.get(m, ""))
                               for m in CORE_FLAG_METRICS)))
        else None),
}


def workbench_flag(obs_measurements: dict, seg_bucket_metrics: dict) -> Optional[str]:
    return workbench_flag_rule(
        severity_profile(obs_measurements, seg_bucket_metrics))


@dataclass
class BacktestResult:
    flag_fy_range: tuple[int, int]
    horizon: int
    n_eligible: int = 0
    n_flagged: int = 0
    n_flagged_deteriorated: int = 0
    n_deteriorated_total: int = 0
    n_deteriorated_captured: int = 0
    lead_times: list[int] = field(default_factory=list)
    z_flagged: int = 0
    z_flagged_deteriorated: int = 0
    detail: list[dict] = field(default_factory=list)
    rule_stats: dict = field(default_factory=dict)   # rule -> {flagged, hits}

    @property
    def hit_rate(self) -> Optional[float]:
        return (self.n_flagged_deteriorated / self.n_flagged
                if self.n_flagged else None)

    @property
    def capture_rate(self) -> Optional[float]:
        return (self.n_deteriorated_captured / self.n_deteriorated_total
                if self.n_deteriorated_total else None)

    @property
    def false_positive_rate(self) -> Optional[float]:
        return ((self.n_flagged - self.n_flagged_deteriorated) / self.n_flagged
                if self.n_flagged else None)

    @property
    def median_lead_time(self) -> Optional[float]:
        return median(self.lead_times) if self.lead_times else None

    @property
    def z_hit_rate(self) -> Optional[float]:
        return (self.z_flagged_deteriorated / self.z_flagged
                if self.z_flagged else None)

    def summary(self) -> dict:
        return {
            "flag_fy_range": list(self.flag_fy_range),
            "horizon_years": self.horizon,
            "n_eligible_company_years": self.n_eligible,
            "n_flagged": self.n_flagged,
            "hit_rate": self.hit_rate,
            "false_positive_rate": self.false_positive_rate,
            "n_deteriorated_total": self.n_deteriorated_total,
            "capture_rate": self.capture_rate,
            "median_lead_time_years": self.median_lead_time,
            "lead_time_distribution": sorted(self.lead_times),
            "altman_z_reference": {
                "n_flagged": self.z_flagged,
                "hit_rate": self.z_hit_rate,
            },
            "rule_comparison": {
                name: {
                    "n_flagged": st["flagged"],
                    "hit_rate": (st["hits"] / st["flagged"]
                                 if st["flagged"] else None),
                    "capture_rate": (st["hits"] / self.n_deteriorated_total
                                     if self.n_deteriorated_total else None),
                }
                for name, st in self.rule_stats.items()
            },
            "base_deterioration_rate": (
                self.n_deteriorated_total / self.n_eligible
                if self.n_eligible else None),
            "caveats": [
                "Public-proxy validation only: deterioration events are "
                "public-financials proxies for migration to non-accrual, not "
                "observed private-loan defaults. Directional check, not "
                "calibration.",
                "Survivorship: companies that exit the panel (delisting, "
                "acquisition) truncate the horizon and bias hit rates down.",
                "Accounting-only signal: market-based measures are known to "
                "add predictive power beyond financial ratios (a structural "
                "limitation when working from financials alone).",
            ],
        }


def backtest(
    panels: dict[int, list[PanelRow]],
    obs_by_cik_fy: dict[tuple[int, int], dict],
    adjusted_benchmarks: dict,
    company_segments: dict[int, list[str]],
    company_buckets: dict[tuple[int, int], Optional[str]],
    flag_fy_range: tuple[int, int],
    horizon: int = 3,
) -> BacktestResult:
    """Run the departure-flag backtest over company-years in flag_fy_range.

    obs_by_cik_fy: (cik, fy) -> {metric: Measurement} (segment-specific
    measurement dicts keyed additionally by segment are flattened by caller
    -- one entry per (cik, fy) using the company's first segment).
    """
    res = BacktestResult(flag_fy_range=flag_fy_range, horizon=horizon)
    for cik, rows in panels.items():
        segs = company_segments.get(cik) or []
        if not segs:
            continue
        seg = segs[0]
        rows_sorted = sorted(rows, key=lambda r: r.fy)
        by_fy = {r.fy: r for r in rows_sorted}
        for fy in range(flag_fy_range[0], flag_fy_range[1] + 1):
            if fy not in by_fy:
                continue
            ms = obs_by_cik_fy.get((cik, fy))
            bucket = company_buckets.get((cik, fy))
            if ms is None or bucket is None:
                continue
            # need at least one observable future year to score
            if not any(f in by_fy for f in range(fy + 1, fy + horizon + 1)):
                continue
            seg_bucket = (adjusted_benchmarks["segments"][seg]["buckets"]
                          [bucket]["metrics"])
            res.n_eligible += 1
            event = deterioration_event(rows_sorted, fy, horizon)
            if event:
                res.n_deteriorated_total += 1
            sev = severity_profile(ms, seg_bucket)
            for name, rule in ALT_RULES.items():
                st = res.rule_stats.setdefault(name, {"flagged": 0, "hits": 0})
                if rule(sev):
                    st["flagged"] += 1
                    if event:
                        st["hits"] += 1
            flag = workbench_flag_rule(sev)
            z = altman_z_private(by_fy[fy])
            z_flag = z is not None and z < Z_DISTRESS
            if z_flag:
                res.z_flagged += 1
                if event:
                    res.z_flagged_deteriorated += 1
            if flag:
                res.n_flagged += 1
                if event:
                    res.n_flagged_deteriorated += 1
                    res.n_deteriorated_captured += 1
                    res.lead_times.append(event["lead_time"])
                res.detail.append({
                    "cik": cik, "entity": rows_sorted[0].entity, "fy": fy,
                    "segment": seg, "bucket": bucket, "flag": flag,
                    "deteriorated": bool(event),
                    "event": event,
                    "altman_z_at_flag": z,
                })
    return res
