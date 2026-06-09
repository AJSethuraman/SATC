"""Ratio computation with explicit basis labels.

Every Measurement carries: value, unit ('x', '%', 'days', 'USD'), a
human-readable basis string (period basis, dollar-vs-unit, derivation), the
provenance of its inputs, and any gaps. Nothing is emitted unlabeled.

Direction metadata ('higher_is_riskier' / 'lower_is_riskier') drives flag
logic and the adjustment engine's tail treatment downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .panel import PanelRow
from .segments import SEGMENTS, SegmentSpec

HIGHER_RISK = "higher_is_riskier"
LOWER_RISK = "lower_is_riskier"


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    unit: str
    direction: str
    basis: str
    core: bool = False   # core risk metrics get tighter flag treatment


METRICS: dict[str, MetricSpec] = {m.key: m for m in [
    MetricSpec("debt_ebitda", "Total Debt / EBITDA", "x", HIGHER_RISK,
               "Fiscal-year basis. Total debt (incl. current portions & "
               "short-term borrowings, USD raw units) / EBITDA (operating "
               "income + D&A, no addbacks).", core=True),
    MetricSpec("net_debt_ebitda", "Net Debt / EBITDA", "x", HIGHER_RISK,
               "Fiscal-year basis. (Total debt - cash & equivalents) / "
               "EBITDA. Cash at fiscal year end (point-in-time)."),
    MetricSpec("debt_ebitda_3y", "Total Debt / 3yr-avg EBITDA", "x", HIGHER_RISK,
               "Through-cycle basis: spot total debt / trailing 3-fiscal-year "
               "average EBITDA. Used where single-year EBITDA is cyclical "
               "(agribusiness)."),
    MetricSpec("interest_coverage", "EBITDA / Interest", "x", LOWER_RISK,
               "Fiscal-year basis. EBITDA / gross interest expense "
               "(income-statement interest, not cash interest paid).", core=True),
    MetricSpec("fcc_proxy", "(EBITDA - Capex) / Interest", "x", LOWER_RISK,
               "Fiscal-year basis. Fixed-charge-coverage proxy; scheduled "
               "amortization not observable in public data (gap)."),
    MetricSpec("ebitda_margin", "EBITDA Margin", "%", LOWER_RISK,
               "Fiscal-year basis. EBITDA / revenue, both full-year USD "
               "raw-unit durations.", core=True),
    MetricSpec("gross_margin", "Gross Margin", "%", LOWER_RISK,
               "Fiscal-year basis. (Revenue - COGS) / revenue."),
    MetricSpec("dso", "Days Sales Outstanding", "days", HIGHER_RISK,
               "Year-end receivables / full-year revenue x 365. Point-in-time "
               "numerator over duration denominator -- seasonal balances "
               "distort; basis note applies."),
    MetricSpec("dio", "Days Inventory Outstanding", "days", HIGHER_RISK,
               "Year-end inventory / full-year COGS x 365. Point-in-time over "
               "duration; harvest/seasonal effects noted per segment."),
    MetricSpec("dpo", "Days Payables Outstanding", "days", LOWER_RISK,
               "Year-end payables / full-year COGS x 365. Higher DPO funds "
               "the cycle but can signal payment stretching -- read with CCC."),
    MetricSpec("ccc", "Cash Conversion Cycle", "days", HIGHER_RISK,
               "DSO + DIO - DPO, all on year-end-balance / full-year-flow "
               "basis."),
    MetricSpec("current_ratio", "Current Ratio", "x", LOWER_RISK,
               "Fiscal-year-end current assets / current liabilities "
               "(point-in-time)."),
    MetricSpec("debt_assets", "Total Debt / Total Assets", "%", HIGHER_RISK,
               "Fiscal-year-end basis, book values. Book-LTV proxy for CRE; "
               "book != market value of property (basis note)."),
    MetricSpec("rent_adj_leverage", "(Debt + 8x Rent) / EBITDAR", "x", HIGHER_RISK,
               "Rent-adjusted leverage, rating-agency convention (8x rent "
               "capitalization). EBITDAR = EBITDA + rent expense. Only where "
               "rent is disclosed."),
    MetricSpec("rev_growth", "Revenue Growth YoY", "%", LOWER_RISK,
               "Fiscal-year over prior fiscal-year revenue growth."),
    MetricSpec("ebitda_volatility", "EBITDA Growth Volatility (3y)", "%", HIGHER_RISK,
               "Std. deviation of YoY EBITDA growth over trailing 3 "
               "observations. Cyclicality measure."),
]}


@dataclass
class Measurement:
    metric: str
    value: float
    unit: str
    basis: str
    provenance: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


def _ratio(num: Optional[float], den: Optional[float],
           allow_negative_den: bool = False) -> Optional[float]:
    if num is None or den is None:
        return None
    if den == 0 or (den < 0 and not allow_negative_den):
        return None
    return num / den


def compute_measurements(
    row: PanelRow,
    history: Optional[list[PanelRow]] = None,
    segment: Optional[str] = None,
) -> dict[str, Measurement]:
    """Compute all applicable metrics for one company-year.

    ``history`` is the company's prior rows (ascending fy) for trend/
    through-cycle metrics. ``segment`` applies segment-specific extras and
    suppressions.
    """
    seg: Optional[SegmentSpec] = SEGMENTS.get(segment) if segment else None
    out: dict[str, Measurement] = {}

    def put(key: str, value: Optional[float], inputs: list[str],
            extra_gaps: Optional[list[str]] = None) -> None:
        if value is None:
            return
        if seg and key in seg.suppressed_metrics:
            return
        spec = METRICS[key]
        prov, gaps = [], list(extra_gaps or [])
        for concept in inputs:
            pv = row.values.get(concept)
            if pv is not None:
                prov += pv.provenance
                gaps += pv.notes
        out[key] = Measurement(metric=key, value=value, unit=spec.unit,
                               basis=spec.basis, provenance=prov, gaps=gaps)

    rev = row.get("revenue")
    ebitda = row.get("ebitda")
    debt = row.get("total_debt")
    cash = row.get("cash")
    interest = row.get("interest_expense")
    cogs = row.get("cogs")
    ta = row.get("total_assets")

    if ebitda is not None and ebitda > 0:
        put("debt_ebitda", _ratio(debt, ebitda), ["total_debt", "ebitda"])
        if debt is not None and cash is not None:
            put("net_debt_ebitda", (debt - cash) / ebitda,
                ["total_debt", "cash", "ebitda"])
    elif ebitda is not None and debt is not None:
        # Negative EBITDA: leverage multiple is meaningless, flag instead
        out["debt_ebitda"] = Measurement(
            metric="debt_ebitda", value=float("nan"), unit="x",
            basis=METRICS["debt_ebitda"].basis,
            gaps=["EBITDA <= 0: leverage multiple not meaningful; treat as "
                  "max-severity departure"],
        )

    if interest is not None and interest > 0:
        put("interest_coverage", _ratio(ebitda, interest),
            ["ebitda", "interest_expense"])
        capex = row.get("capex")
        if ebitda is not None and capex is not None:
            put("fcc_proxy", (ebitda - capex) / interest,
                ["ebitda", "capex", "interest_expense"])

    if rev and rev > 0:
        if ebitda is not None:
            put("ebitda_margin", ebitda / rev * 100, ["ebitda", "revenue"])
        if cogs is not None:
            put("gross_margin", (rev - cogs) / rev * 100, ["revenue", "cogs"])
        ar = row.get("receivables")
        if ar is not None:
            put("dso", ar / rev * 365, ["receivables", "revenue"])
    if cogs and cogs > 0:
        inv, ap = row.get("inventory"), row.get("payables")
        if inv is not None:
            put("dio", inv / cogs * 365, ["inventory", "cogs"])
        if ap is not None:
            put("dpo", ap / cogs * 365, ["payables", "cogs"])
    if all(k in out for k in ("dso", "dio", "dpo")):
        put("ccc", out["dso"].value + out["dio"].value - out["dpo"].value,
            ["receivables", "inventory", "payables", "revenue", "cogs"])

    ca, cl = row.get("current_assets"), row.get("current_liabilities")
    if ca is not None and cl and cl > 0:
        put("current_ratio", ca / cl, ["current_assets", "current_liabilities"])

    if ta and ta > 0 and debt is not None:
        put("debt_assets", debt / ta * 100, ["total_debt", "total_assets"])

    # Rent-adjusted leverage (healthcare)
    if seg and seg.rent_adjusted:
        rent = row.get("rent_expense")
        if rent is not None and ebitda is not None and debt is not None:
            ebitdar = ebitda + rent
            if ebitdar > 0:
                put("rent_adj_leverage", (debt + 8 * rent) / ebitdar,
                    ["total_debt", "rent_expense", "ebitda"])
        else:
            # surfaced as a gap, not silently absent
            gap = ("rent_adj_leverage: rent expense not disclosed in XBRL; "
                   "unadjusted leverage understates fixed obligations for "
                   "leased-facility operators")
            if gap not in row.gaps:
                row.gaps.append(gap)

    # History-dependent metrics
    if history:
        hist = sorted([r for r in history if r.fy < row.fy], key=lambda r: r.fy)
        prior = hist[-1] if hist else None
        if prior is not None and prior.fy == row.fy - 1:
            prev_rev = prior.get("revenue")
            if rev is not None and prev_rev and prev_rev > 0:
                put("rev_growth", (rev / prev_rev - 1) * 100, ["revenue"])
        # 3y average EBITDA leverage (through-cycle)
        if (seg is None or seg.through_cycle_leverage) and debt is not None:
            window = [r.get("ebitda") for r in hist[-2:]] + [ebitda]
            window = [e for e in window if e is not None]
            if len(window) == 3:
                avg = sum(window) / 3
                if avg > 0:
                    put("debt_ebitda_3y", debt / avg, ["total_debt", "ebitda"],
                        extra_gaps=["3y average uses this company's trailing "
                                    "three fiscal years"])
        # EBITDA growth volatility over trailing 3 YoY observations
        eb_series = [(r.fy, r.get("ebitda")) for r in hist] + [(row.fy, ebitda)]
        eb_series = [(fy, e) for fy, e in eb_series if e is not None]
        growths = []
        for (fy0, e0), (fy1, e1) in zip(eb_series, eb_series[1:]):
            if fy1 == fy0 + 1 and e0 and abs(e0) > 0:
                growths.append((e1 - e0) / abs(e0) * 100)
        if len(growths) >= 3:
            g = growths[-3:]
            mean = sum(g) / len(g)
            var = sum((x - mean) ** 2 for x in g) / (len(g) - 1)
            put("ebitda_volatility", var ** 0.5, ["ebitda"])

    return out
