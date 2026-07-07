"""Derived financial metrics from canonical annual series.

Pure calculation layer: takes normalized series in, returns DerivedMetric
objects with values per period, the formula used, and the source tags and
accessions that fed it. No fetching, no database access.
"""

from dataclasses import dataclass, field
from datetime import date

from stock_helper.normalization.facts import MetricSeries

METRICS_VERSION = "metrics-0.1"


@dataclass
class DerivedMetric:
    key: str
    label: str
    unit: str  # "ratio", "USD", "shares", "pct"
    formula: str
    points: list[tuple[date, float]]  # ascending by period_end
    input_tags: list[str] = field(default_factory=list)
    input_accessions: list[str] = field(default_factory=list)

    @property
    def latest(self) -> float | None:
        return self.points[-1][1] if self.points else None

    def last_n(self, n: int) -> list[float]:
        return [v for _, v in self.points[-n:]]


def _aligned(a: MetricSeries, b: MetricSeries) -> list[tuple[date, float, float]]:
    """Join two series on identical period_end dates."""
    b_map = dict(b.values())
    return [(end, value, b_map[end]) for end, value in a.values() if end in b_map]


def _ratio_metric(
    key: str,
    label: str,
    formula: str,
    numer: MetricSeries | None,
    denom: MetricSeries | None,
    unit: str = "ratio",
) -> DerivedMetric | None:
    if numer is None or denom is None:
        return None
    points = [
        (end, n / d) for end, n, d in _aligned(numer, denom) if d not in (0, 0.0)
    ]
    if not points:
        return None
    return DerivedMetric(
        key=key, label=label, unit=unit, formula=formula, points=points,
        input_tags=[numer.tag, denom.tag],
        input_accessions=sorted(set(numer.accessions()) | set(denom.accessions())),
    )


def compute_derived_metrics(series: dict[str, MetricSeries]) -> dict[str, DerivedMetric]:
    """All computable derived metrics. Missing inputs simply omit the metric —
    the signal layer reports those as UNAVAILABLE with the reason."""
    out: dict[str, DerivedMetric] = {}

    def add(metric: DerivedMetric | None) -> None:
        if metric is not None and metric.points:
            out[metric.key] = metric

    rev = series.get("revenue")
    cogs = series.get("cost_of_revenue")
    op = series.get("operating_income")
    ni = series.get("net_income")
    ocf = series.get("operating_cash_flow")
    capex = series.get("capex")
    assets = series.get("total_assets")

    # Pass-through levels the signal/valuation layers read directly
    for key, label, unit in [
        ("revenue", "Revenue", "USD"),
        ("operating_income", "Operating income", "USD"),
        ("operating_cash_flow", "Operating cash flow", "USD"),
        ("net_income", "Net income", "USD"),
        ("cash", "Cash & equivalents", "USD"),
        ("diluted_shares", "Diluted shares (wtd avg)", "shares"),
        ("shares_outstanding", "Shares outstanding", "shares"),
        ("buybacks", "Share repurchases", "USD"),
        ("dividends_per_share", "Dividends per share", "USD/shares"),
        ("eps_diluted", "Diluted EPS", "USD/shares"),
        ("total_assets", "Total assets", "USD"),
        ("total_liabilities", "Total liabilities", "USD"),
        ("equity", "Stockholders' equity", "USD"),
        ("current_assets", "Current assets", "USD"),
        ("current_liabilities", "Current liabilities", "USD"),
        ("retained_earnings", "Retained earnings", "USD"),
        ("ppe_net", "PP&E (net)", "USD"),
        ("goodwill", "Goodwill", "USD"),
        ("intangible_assets", "Intangible assets", "USD"),
        ("inventory", "Inventory", "USD"),
        ("depreciation_amortization", "Depreciation & amortization", "USD"),
        ("interest_expense", "Interest expense", "USD"),
        ("tax_expense", "Income tax expense", "USD"),
        ("pretax_income", "Pre-tax income", "USD"),
        ("capex", "Capital expenditures", "USD"),
        ("deposits", "Total deposits", "USD"),
        ("credit_loss_allowance", "Allowance for credit losses", "USD"),
        ("net_interest_income", "Net interest income", "USD"),
        ("nonperforming_loans", "Nonaccrual loans", "USD"),
        ("charge_offs", "Gross charge-offs", "USD"),
    ]:
        s = series.get(key)
        if s:
            out[key] = DerivedMetric(
                key=key, label=label, unit=unit, formula=f"as filed ({s.tag})",
                points=s.values(), input_tags=[s.tag], input_accessions=s.accessions(),
            )

    # Gross profit: as-filed tag preferred, else revenue - cost_of_revenue.
    gp = series.get("gross_profit")
    if gp:
        out["gross_profit"] = DerivedMetric(
            key="gross_profit", label="Gross profit", unit="USD",
            formula=f"as filed ({gp.tag})", points=gp.values(),
            input_tags=[gp.tag], input_accessions=gp.accessions(),
        )
    elif rev and cogs:
        points = [(end, r - c) for end, r, c in _aligned(rev, cogs)]
        if points:
            out["gross_profit"] = DerivedMetric(
                key="gross_profit", label="Gross profit", unit="USD",
                formula="revenue - cost_of_revenue", points=points,
                input_tags=[rev.tag, cogs.tag],
                input_accessions=sorted(set(rev.accessions()) | set(cogs.accessions())),
            )

    # Margins
    if rev and cogs:
        points = [
            (end, (r - c) / r) for end, r, c in _aligned(rev, cogs) if r not in (0, 0.0)
        ]
        if points:
            out["gross_margin"] = DerivedMetric(
                key="gross_margin", label="Gross margin", unit="ratio",
                formula="(revenue - cost_of_revenue) / revenue", points=points,
                input_tags=[rev.tag, cogs.tag],
                input_accessions=sorted(set(rev.accessions()) | set(cogs.accessions())),
            )
    add(_ratio_metric("operating_margin", "Operating margin",
                      "operating_income / revenue", op, rev))

    # EBITDA = operating income (== EBIT, our pinned definition) + D&A.
    da = series.get("depreciation_amortization")
    if op and da:
        points = [(end, o + d) for end, o, d in _aligned(op, da)]
        if points:
            out["ebitda"] = DerivedMetric(
                key="ebitda", label="EBITDA", unit="USD",
                formula="operating_income + depreciation_amortization", points=points,
                input_tags=[op.tag, da.tag],
                input_accessions=sorted(set(op.accessions()) | set(da.accessions())),
            )

    # Tangible book value = equity - goodwill - intangibles (missing terms -> 0).
    eq = series.get("equity")
    if eq:
        gw_map = dict(series["goodwill"].values()) if series.get("goodwill") else {}
        intang_map = dict(series["intangible_assets"].values()) if series.get("intangible_assets") else {}
        points = [
            (end, v - gw_map.get(end, 0.0) - intang_map.get(end, 0.0))
            for end, v in eq.values()
        ]
        tags = [eq.tag] + ([series["goodwill"].tag] if gw_map else []) + (
            [series["intangible_assets"].tag] if intang_map else [])
        if points:
            out["tangible_book"] = DerivedMetric(
                key="tangible_book", label="Tangible book value", unit="USD",
                formula="equity - goodwill - intangible_assets", points=points,
                input_tags=tags, input_accessions=eq.accessions(),
            )

    # ROE = net income / average equity (2-year avg, like nim_proxy).
    if ni and eq:
        eq_vals = eq.values()
        avg_eq = {
            curr_end: (prev_val + curr_val) / 2
            for (_, prev_val), (curr_end, curr_val) in zip(eq_vals, eq_vals[1:], strict=False)
        }
        points = [
            (end, v / avg_eq[end]) for end, v in ni.values()
            if end in avg_eq and avg_eq[end] not in (0, 0.0)
        ]
        if points:
            out["roe"] = DerivedMetric(
                key="roe", label="Return on equity", unit="ratio",
                formula="net_income / avg(equity[t-1], equity[t])", points=points,
                input_tags=[ni.tag, eq.tag],
                input_accessions=sorted(set(ni.accessions()) | set(eq.accessions())),
            )

    # Free cash flow (OCF - capex; capex sign is positive-as-outflow in XBRL)
    if ocf and capex:
        points = [(end, o - c) for end, o, c in _aligned(ocf, capex)]
        if points:
            out["free_cash_flow"] = DerivedMetric(
                key="free_cash_flow", label="Free cash flow", unit="USD",
                formula="operating_cash_flow - capex", points=points,
                input_tags=[ocf.tag, capex.tag],
                input_accessions=sorted(set(ocf.accessions()) | set(capex.accessions())),
            )

    add(_ratio_metric("ocf_to_net_income", "OCF / net income",
                      "operating_cash_flow / net_income", ocf, ni))

    # Accrual proxy (cash-flow approach): (NI - OCF) / total assets
    if ni and ocf and assets:
        asset_map = dict(assets.values())
        points = [
            (end, (n - o) / asset_map[end])
            for end, n, o in _aligned(ni, ocf)
            if end in asset_map and asset_map[end] not in (0, 0.0)
        ]
        if points:
            out["accrual_proxy"] = DerivedMetric(
                key="accrual_proxy", label="Accrual proxy", unit="ratio",
                formula="(net_income - operating_cash_flow) / total_assets",
                points=points,
                input_tags=[ni.tag, ocf.tag, assets.tag],
                input_accessions=sorted(
                    set(ni.accessions()) | set(ocf.accessions()) | set(assets.accessions())
                ),
            )

    # Total debt = long-term + current portion + short-term borrowings
    # (any subset that is tagged). Short-term borrowings (commercial paper,
    # revolvers) are added beyond the current portion of long-term debt.
    lt = series.get("long_term_debt")
    st = series.get("short_term_debt")
    stb = series.get("short_term_borrowings")
    debt_points: dict[date, float] = {}
    debt_tags, debt_accessions = [], set()
    for part in (lt, st, stb):
        if part is None:
            continue
        debt_tags.append(part.tag)
        debt_accessions.update(part.accessions())
        for end, value in part.values():
            debt_points[end] = debt_points.get(end, 0.0) + value
    if debt_points:
        out["total_debt"] = DerivedMetric(
            key="total_debt", label="Total debt", unit="USD",
            formula="long_term_debt + current portion + short_term_borrowings",
            points=sorted(debt_points.items()),
            input_tags=debt_tags, input_accessions=sorted(debt_accessions),
        )
    if debt_points and assets:
        asset_map = dict(assets.values())
        points = [
            (end, debt / asset_map[end])
            for end, debt in sorted(debt_points.items())
            if end in asset_map and asset_map[end] not in (0, 0.0)
        ]
        if points:
            out["debt_to_assets"] = DerivedMetric(
                key="debt_to_assets", label="Debt / assets", unit="ratio",
                formula="(long_term_debt + short_term_debt) / total_assets",
                points=points,
                input_tags=debt_tags + [assets.tag],
                input_accessions=sorted(debt_accessions | set(assets.accessions())),
            )

    add(_ratio_metric("interest_coverage", "Interest coverage",
                      "operating_income / interest_expense",
                      op, series.get("interest_expense")))
    add(_ratio_metric("current_ratio", "Current ratio",
                      "current_assets / current_liabilities",
                      series.get("current_assets"), series.get("current_liabilities")))

    # NIM proxy (banking): NII / average total assets. A true NIM divides by
    # average *earning* assets, which face XBRL rarely provides — hence "proxy",
    # and the signal caveat says so. Needs consecutive year-end asset values.
    nii, assets_series = series.get("net_interest_income"), assets
    if nii and assets_series:
        asset_values = assets_series.values()
        avg_assets = {
            curr_end: (prev_val + curr_val) / 2
            for (_, prev_val), (curr_end, curr_val) in zip(
                asset_values, asset_values[1:], strict=False
            )
        }
        points = [
            (end, value / avg_assets[end])
            for end, value in nii.values()
            if end in avg_assets and avg_assets[end] not in (0, 0.0)
        ]
        if points:
            out["nim_proxy"] = DerivedMetric(
                key="nim_proxy", label="NIM proxy", unit="ratio",
                formula="net_interest_income / avg(total_assets[t-1], total_assets[t])",
                points=points,
                input_tags=[nii.tag, assets_series.tag],
                input_accessions=sorted(
                    set(nii.accessions()) | set(assets_series.accessions())
                ),
            )

    return out


# --- small trend helpers shared with the signal layer -----------------------

def yoy_change(values: list[float]) -> float | None:
    """Latest year-over-year relative change, or None if not computable."""
    if len(values) < 2 or values[-2] == 0:
        return None
    return values[-1] / values[-2] - 1.0


def trend_direction(values: list[float], tolerance: float = 0.02) -> str:
    """Direction over the last up-to-3 values: 'improving' if consistently
    rising beyond tolerance (relative), 'deteriorating' if falling, 'stable'
    within tolerance, else 'mixed'. Descriptive, not predictive."""
    tail = values[-3:]
    if len(tail) < 2:
        return ""
    steps = []
    for prev, curr in zip(tail, tail[1:], strict=False):
        base = abs(prev) if prev != 0 else max(abs(curr), 1e-9)
        rel = (curr - prev) / base
        steps.append("up" if rel > tolerance else "down" if rel < -tolerance else "flat")
    if all(s in ("up", "flat") for s in steps) and "up" in steps:
        return "improving"
    if all(s in ("down", "flat") for s in steps) and "down" in steps:
        return "deteriorating"
    if all(s == "flat" for s in steps):
        return "stable"
    return "mixed"
