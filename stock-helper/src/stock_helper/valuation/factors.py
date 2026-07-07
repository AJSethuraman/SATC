"""Quality and distress factor scores (pure calculation core).

The single home for cross-sectional quality / financial-strength factors:
Piotroski F-score, Novy-Marx gross profitability, a Greenblatt-style Magic
Formula variant, Sloan accruals quality, and the Altman Z / Z'' distress models.

Research flags, NOT advice or price targets. Every factor falls out of explicit
inputs carried with full provenance (the values used, the source XBRL tags, the
filing accessions, and the period ends) so any number here is auditable.

Money-critical invariants enforced throughout (mirrors valuation.multiples):
- A ratio is only computed when its denominator is positive. A non-positive
  denominator, a missing input, or a too-short history returns ``None`` (or a
  FactorResult with a non-OK status and a reason) — never a bogus / negative
  "cheap" number that a reader could act on.
- Nothing here fetches, reads a DB, or touches the network.

Definitional choices (documented so the audit trail is honest):
- ROA is ``net_income / average(total_assets over the two surrounding year
  ends)`` — the same 2-year-average convention the codebase already uses for ROE
  (features/metrics.py). This is why the Piotroski ΔROA test needs THREE asset
  points: ROA_t averages assets_{t} and assets_{t-1}; ROA_{t-1} averages
  assets_{t-1} and assets_{t-2}.
- EBIT is pinned to ``operating_income`` (same as valuation.multiples), so the
  Magic Formula and Altman X3 share one operating-earnings base.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

from stock_helper.features.metrics import DerivedMetric
from stock_helper.industry.sic_buckets import is_financial
from stock_helper.normalization.facts import MetricSeries
from stock_helper.valuation import (
    NOT_APPLICABLE,
    OK,
    UNAVAILABLE,
    VALUATION_VERSION,
)

if TYPE_CHECKING:  # avoid importing the heavy (pandas/sqlmodel) context module
    from stock_helper.features.context import MarketContext

# Altman zone labels.
SAFE = "safe"
GREY = "grey"
DISTRESS = "distress"

# Altman model labels.
Z_ORIGINAL = "Z (1968, manufacturer, market-based)"
Z_DOUBLE_PRIME = "Z'' (four-variable, book-based)"


# --------------------------------------------------------------------------- #
# Provenance-carrying result dataclasses
# --------------------------------------------------------------------------- #


@dataclass
class FactorResult:
    """One quality/distress factor with full provenance.

    ``value is None`` whenever ``status != OK`` (the factor could not be
    computed for the reason in ``reason``); a populated ``value`` always carries
    a positive/meaningful figure. ``detail`` holds factor-specific extras (e.g.
    the per-test 0/1 map for Piotroski, or ``model``/``zone`` for Altman)."""

    key: str
    label: str
    value: float | None
    status: str = OK
    reason: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    formula: str = ""
    values_used: dict[str, float] = field(default_factory=dict)
    input_tags: list[str] = field(default_factory=list)
    input_accessions: list[str] = field(default_factory=list)
    period_ends: dict[str, date] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)
    engine_version: str = VALUATION_VERSION


@dataclass
class QualityFactors:
    """The bundle of quality/distress factors for one company.

    ``metric_set`` is "financial" (banks/insurers → only ROA/ROE apply; the
    industrial factors are carried as NOT_APPLICABLE) or "industrial". The
    ``composite`` is a coverage-weighted 0-100 blend of the computed factors —
    a rough research summary, NOT a rating; ``coverage`` (0-1) says how much of
    the applicable factor set actually fed it, and ``note`` states both."""

    bucket: str
    metric_set: str
    factors: dict[str, FactorResult]
    composite: float | None
    coverage: float
    note: str = ""
    caveats: list[str] = field(default_factory=list)
    engine_version: str = VALUATION_VERSION


# --------------------------------------------------------------------------- #
# Small pure helpers (series lookups + provenance collection)
# --------------------------------------------------------------------------- #


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _provenance(
    *sources: MetricSeries | None,
) -> tuple[list[str], list[str]]:
    """Union of tags and accessions across the given series (skipping None)."""
    tags: list[str] = []
    accns: set[str] = set()
    for s in sources:
        if s is None:
            continue
        tags.append(s.tag)
        accns.update(s.accessions())
    return sorted(set(tags)), sorted(accns)


def _latest_common(
    series: dict[str, MetricSeries], keys: tuple[str, ...]
) -> tuple[date, dict[str, float]] | None:
    """Latest period_end at which EVERY requested series has a value, plus the
    aligned values there. None if any series is missing or they never overlap."""
    maps: dict[str, dict[date, float]] = {}
    for k in keys:
        s = series.get(k)
        if s is None or not s.points:
            return None
        maps[k] = dict(s.values())
    common = set.intersection(*[set(m) for m in maps.values()])
    if not common:
        return None
    d = max(common)
    return d, {k: maps[k][d] for k in keys}


def _gross_profit_map(
    series: dict[str, MetricSeries],
) -> tuple[dict[date, float], list[str], list[str]] | None:
    """Gross profit per period: the as-filed ``gross_profit`` series if present,
    else ``revenue - cost_of_revenue`` on aligned periods. None if neither."""
    gp = series.get("gross_profit")
    if gp is not None and gp.points:
        tags, accns = _provenance(gp)
        return dict(gp.values()), tags, accns
    rev, cogs = series.get("revenue"), series.get("cost_of_revenue")
    if rev is None or cogs is None:
        return None
    cogs_map = dict(cogs.values())
    out = {end: r - cogs_map[end] for end, r in rev.values() if end in cogs_map}
    if not out:
        return None
    tags, accns = _provenance(rev, cogs)
    return out, tags, accns


# --------------------------------------------------------------------------- #
# Piotroski F-score
# --------------------------------------------------------------------------- #


# The nine binary tests, in Piotroski (2000) order. Names are stable keys into
# ``detail['tests']``.
_PIOTROSKI_TESTS = (
    "roa_positive",
    "ocf_positive",
    "roa_improved",
    "accrual",
    "ltd_ratio_fell",
    "current_ratio_improved",
    "no_new_shares",
    "gross_margin_improved",
    "asset_turnover_improved",
)


def compute_piotroski_f_score(
    series: dict[str, MetricSeries],
) -> FactorResult | None:
    """Piotroski (2000) F-score: nine 0/1 fundamental-strength tests, summed 0-9.

    Needs >= 2 consecutive fiscal years (anchored on total assets); the ΔROA
    test additionally needs a 3rd (t-2) asset point. Returns None if fewer than
    two asset periods (or net income) are available — the score is meaningless
    without a year-over-year comparison. A test whose inputs are missing scores
    0 (we never credit an improvement we cannot verify) and is listed in
    ``detail['uncomputable']``.

    Reference: Joseph D. Piotroski, "Value Investing: The Use of Historical
    Financial Statement Information to Separate Winners from Losers", J. of
    Accounting Research 38 (2000), Supplement, pp. 1-41.
    """
    assets = series.get("total_assets")
    ni = series.get("net_income")
    if assets is None or ni is None:
        return None
    a = dict(assets.values())
    ni_map = dict(ni.values())
    a_dates = sorted(a)
    if len(a_dates) < 2 or len(ni_map) < 2:
        return None

    t, t1 = a_dates[-1], a_dates[-2]
    t2 = a_dates[-3] if len(a_dates) >= 3 else None

    def roa_at(pe: date, prev: date | None) -> float | None:
        if prev is None or pe not in ni_map or pe not in a or prev not in a:
            return None
        avg = (a[pe] + a[prev]) / 2.0
        return ni_map[pe] / avg if avg > 0 else None

    ocf = series.get("operating_cash_flow")
    ltd = series.get("long_term_debt")
    ca = series.get("current_assets")
    cl = series.get("current_liabilities")
    dsh = series.get("diluted_shares")
    rev = series.get("revenue")
    ocf_map = dict(ocf.values()) if ocf else {}
    ltd_map = dict(ltd.values()) if ltd else {}
    ca_map = dict(ca.values()) if ca else {}
    cl_map = dict(cl.values()) if cl else {}
    dsh_map = dict(dsh.values()) if dsh else {}
    rev_map = dict(rev.values()) if rev else {}
    gp = _gross_profit_map(series)
    gp_map = gp[0] if gp else {}

    roa_t = roa_at(t, t1)
    roa_t1 = roa_at(t1, t2)

    tests: dict[str, int] = {}
    uncomputable: list[str] = []

    def record(name: str, ok: bool | None) -> None:
        # ok is None when inputs are missing -> conservatively 0 + flagged.
        if ok is None:
            uncomputable.append(name)
            tests[name] = 0
        else:
            tests[name] = 1 if ok else 0

    # Profitability
    record("roa_positive", (roa_t > 0) if roa_t is not None else None)
    record("ocf_positive", (ocf_map[t] > 0) if t in ocf_map else None)
    record(
        "roa_improved",
        (roa_t > roa_t1) if (roa_t is not None and roa_t1 is not None) else None,
    )
    record(
        "accrual",  # cash earnings exceed accrual earnings
        (ocf_map[t] > ni_map[t]) if (t in ocf_map and t in ni_map) else None,
    )

    # Leverage / liquidity
    def ltd_ratio(pe: date) -> float | None:
        if pe in ltd_map and pe in a and a[pe] > 0:
            return ltd_map[pe] / a[pe]
        return None

    lr_t, lr_t1 = ltd_ratio(t), ltd_ratio(t1)
    record(
        "ltd_ratio_fell",
        (lr_t < lr_t1) if (lr_t is not None and lr_t1 is not None) else None,
    )

    def current_ratio(pe: date) -> float | None:
        if pe in ca_map and pe in cl_map and cl_map[pe] > 0:
            return ca_map[pe] / cl_map[pe]
        return None

    cr_t, cr_t1 = current_ratio(t), current_ratio(t1)
    record(
        "current_ratio_improved",
        (cr_t > cr_t1) if (cr_t is not None and cr_t1 is not None) else None,
    )
    record(
        "no_new_shares",  # diluted share count did not rise YoY
        (dsh_map[t] <= dsh_map[t1]) if (t in dsh_map and t1 in dsh_map) else None,
    )

    # Efficiency
    def gross_margin(pe: date) -> float | None:
        if pe in gp_map and pe in rev_map and rev_map[pe] > 0:
            return gp_map[pe] / rev_map[pe]
        return None

    gm_t, gm_t1 = gross_margin(t), gross_margin(t1)
    record(
        "gross_margin_improved",
        (gm_t > gm_t1) if (gm_t is not None and gm_t1 is not None) else None,
    )

    def asset_turnover(pe: date) -> float | None:
        if pe in rev_map and pe in a and a[pe] > 0:
            return rev_map[pe] / a[pe]
        return None

    at_t, at_t1 = asset_turnover(t), asset_turnover(t1)
    record(
        "asset_turnover_improved",
        (at_t > at_t1) if (at_t is not None and at_t1 is not None) else None,
    )

    score = float(sum(tests[name] for name in _PIOTROSKI_TESTS))
    tags, accns = _provenance(assets, ni, ocf, ltd, ca, cl, dsh, rev,
                              series.get("gross_profit"), series.get("cost_of_revenue"))
    period_ends = {"t": t, "t-1": t1}
    if t2 is not None:
        period_ends["t-2"] = t2

    caveats = [
        "ROA uses 2-year-average total assets (matches the codebase ROE convention).",
    ]
    if uncomputable:
        caveats.append(
            "Uncomputable tests scored 0 (input missing): " + ", ".join(uncomputable)
        )

    return FactorResult(
        key="piotroski_f",
        label="Piotroski F-score",
        value=score,
        status=OK,
        detail={"tests": tests, "uncomputable": uncomputable, "max": 9},
        formula="sum of 9 binary fundamental tests (profitability, leverage, efficiency)",
        values_used={
            "net_income_t": ni_map.get(t, float("nan")),
            "total_assets_t": a.get(t, float("nan")),
        },
        input_tags=tags,
        input_accessions=accns,
        period_ends=period_ends,
        caveats=caveats,
    )


# --------------------------------------------------------------------------- #
# Novy-Marx gross profitability
# --------------------------------------------------------------------------- #


def compute_gross_profitability(
    series: dict[str, MetricSeries],
) -> FactorResult | None:
    """Novy-Marx gross profitability: gross_profit / total_assets (latest).

    Higher is better ("the other side of value"). None if either input is
    missing or total assets is non-positive.

    Reference: Robert Novy-Marx, "The Other Side of Value: The Gross
    Profitability Premium", J. of Financial Economics 108 (2013), pp. 1-28.
    """
    gp = _gross_profit_map(series)
    assets = series.get("total_assets")
    if gp is None or assets is None or not assets.points:
        return None
    gp_map, gp_tags, gp_accns = gp
    a_map = dict(assets.values())
    common = set(gp_map) & set(a_map)
    if not common:
        return None
    d = max(common)
    ta = a_map[d]
    if ta <= 0:
        return None
    value = gp_map[d] / ta
    a_tags, a_accns = _provenance(assets)
    return FactorResult(
        key="gross_profitability",
        label="Gross profitability (Novy-Marx)",
        value=value,
        status=OK,
        formula="gross_profit / total_assets",
        values_used={"gross_profit": gp_map[d], "total_assets": ta},
        input_tags=sorted(set(gp_tags) | set(a_tags)),
        input_accessions=sorted(set(gp_accns) | set(a_accns)),
        period_ends={"latest": d},
    )


# --------------------------------------------------------------------------- #
# Magic Formula (Greenblatt-style variant)
# --------------------------------------------------------------------------- #


def _ev_value(ev: Any) -> float | None:
    """Accept either an EnterpriseValue dataclass or a raw float EV."""
    if ev is None:
        return None
    if hasattr(ev, "enterprise_value"):
        return float(ev.enterprise_value)
    try:
        return float(ev)
    except (TypeError, ValueError):
        return None


def compute_magic_formula(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    ev: Any,
) -> FactorResult | None:
    """Greenblatt-style Magic Formula, single-name VARIANT (not a ranked screen).

    earnings_yield = EBIT / EV   (EBIT = operating_income)
    roic           = EBIT / (NWC_ex_cash + net PP&E)
      where NWC_ex_cash = (current_assets - cash) - current_liabilities.

    Greenblatt combines a company's *ranks* of these two across a universe; we
    only have one company here, so this returns the two components (earnings
    yield as the headline ``value``, ROIC in ``detail``) and is labelled a
    variant. None if EV is missing/<=0 or invested capital is <=0 (a
    non-positive denominator would flip ROIC's sign misleadingly).

    Reference: Joel Greenblatt, "The Little Book That Still Beats the Market"
    (2010) — return on capital = EBIT / (net working capital + net fixed assets).
    """
    ev_val = _ev_value(ev)
    if ev_val is None or ev_val <= 0:
        return None

    ebit_s = series.get("operating_income")
    ca_s = series.get("current_assets")
    cash_s = series.get("cash")
    cl_s = series.get("current_liabilities")
    ppe_s = series.get("ppe_net")
    needed = _latest_common(
        series, ("operating_income", "current_assets", "cash",
                 "current_liabilities", "ppe_net")
    )
    if needed is None:
        return None
    d, vals = needed
    ebit = vals["operating_income"]
    nwc_ex_cash = (vals["current_assets"] - vals["cash"]) - vals["current_liabilities"]
    capital = nwc_ex_cash + vals["ppe_net"]
    if capital <= 0:
        return None

    earnings_yield = ebit / ev_val
    roic = ebit / capital
    tags, accns = _provenance(ebit_s, ca_s, cash_s, cl_s, ppe_s)
    ev_tags = list(getattr(ev, "input_tags", []) or [])
    ev_accns = list(getattr(ev, "input_accessions", []) or [])

    return FactorResult(
        key="magic_formula",
        label="Magic Formula (single-name variant)",
        value=earnings_yield,
        status=OK,
        detail={"earnings_yield": earnings_yield, "roic": roic},
        formula="earnings_yield=EBIT/EV; roic=EBIT/((current_assets-cash-current_liabilities)+ppe_net)",
        values_used={
            "ebit": ebit,
            "enterprise_value": ev_val,
            "nwc_ex_cash": nwc_ex_cash,
            "ppe_net": vals["ppe_net"],
            "invested_capital": capital,
        },
        input_tags=sorted(set(tags) | set(ev_tags)),
        input_accessions=sorted(set(accns) | set(ev_accns)),
        period_ends={"latest": d},
        caveats=[
            "Variant: components are reported for one company, NOT ranked against a "
            "universe as in Greenblatt's screen.",
            "EV embeds non-canonical market-price data (see EnterpriseValue source).",
        ],
    )


# --------------------------------------------------------------------------- #
# Sloan accruals quality
# --------------------------------------------------------------------------- #


def compute_accruals_quality(
    series: dict[str, MetricSeries],
) -> FactorResult | None:
    """Sloan (1996) accruals: (net_income - operating_cash_flow) / total_assets.

    LOWER is better: a high positive value means earnings are propped up by
    accruals rather than cash (low earnings quality, weaker persistence). The
    figure can legitimately be negative (cash exceeds earnings), which is a good
    sign, so the sign is kept; only a non-positive total-assets denominator makes
    it undefined (-> None).

    Reference: Richard G. Sloan, "Do Stock Prices Fully Reflect Information in
    Accruals and Cash Flows about Future Earnings?", The Accounting Review 71
    (1996), pp. 289-315 (cash-flow accruals measure).
    """
    got = _latest_common(series, ("net_income", "operating_cash_flow", "total_assets"))
    if got is None:
        return None
    d, vals = got
    ta = vals["total_assets"]
    if ta <= 0:
        return None
    value = (vals["net_income"] - vals["operating_cash_flow"]) / ta
    tags, accns = _provenance(
        series.get("net_income"),
        series.get("operating_cash_flow"),
        series.get("total_assets"),
    )
    return FactorResult(
        key="accruals_quality",
        label="Accruals (Sloan; lower is better)",
        value=value,
        status=OK,
        formula="(net_income - operating_cash_flow) / total_assets",
        values_used={
            "net_income": vals["net_income"],
            "operating_cash_flow": vals["operating_cash_flow"],
            "total_assets": ta,
        },
        input_tags=tags,
        input_accessions=accns,
        period_ends={"latest": d},
        caveats=["Lower is better; a high positive value flags low earnings quality."],
    )


# --------------------------------------------------------------------------- #
# Altman Z / Z'' distress
# --------------------------------------------------------------------------- #


def _int_sic(sic: str | int | None) -> int | None:
    if sic in (None, ""):
        return None
    try:
        return int(sic)
    except (TypeError, ValueError):
        return None


def compute_altman_z(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    sic: str | int | None,
) -> FactorResult | None:
    """Altman distress score, model chosen by SIC and data availability.

    Manufacturers (SIC 2000-3999) WITH a market cap get the original 1968 Z
    (uses market value of equity in X4). Everyone else gets the four-variable
    Z'' (Altman's non-manufacturer / emerging-market model), which is fully
    replayable from book values (no market price).

    Original Z (Altman 1968):
        Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
        X1=(current_assets-current_liabilities)/TA, X2=retained_earnings/TA,
        X3=EBIT/TA, X4=market_cap/total_liabilities, X5=revenue/TA.
        Zones: > 2.99 safe, < 1.81 distress, else grey.
    Z'' (Altman 1995/2000, four-variable):
        Z'' = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4   (no X5)
        X4 = book_equity / total_liabilities.
        Zones: > 2.6 safe, < 1.1 distress, else grey.

    Coefficients and cutoffs verified against Altman, "Financial Ratios,
    Discriminant Analysis and the Prediction of Corporate Bankruptcy", J. of
    Finance 23 (1968), pp. 589-609, and Altman, "Predicting Financial Distress
    of Companies: Revisiting the Z-Score and ZETA Models" (2000), Table 8 (Z'').

    Returns None if total assets or total liabilities is missing/non-positive
    (every X divides by TA; X4 divides by total liabilities).
    """
    got = _latest_common(
        series,
        ("total_assets", "total_liabilities", "current_assets",
         "current_liabilities", "retained_earnings", "operating_income"),
    )
    if got is None:
        return None
    d, vals = got
    ta = vals["total_assets"]
    tl = vals["total_liabilities"]
    if ta <= 0 or tl <= 0:
        return None

    working_capital = vals["current_assets"] - vals["current_liabilities"]
    ebit = vals["operating_income"]
    x1 = working_capital / ta
    x2 = vals["retained_earnings"] / ta
    x3 = ebit / ta

    market_cap = getattr(market, "market_cap", None) if market is not None else None
    code = _int_sic(sic)
    is_manufacturer = code is not None and 2000 <= code <= 3999

    used_series = [
        series.get("total_assets"), series.get("total_liabilities"),
        series.get("current_assets"), series.get("current_liabilities"),
        series.get("retained_earnings"), series.get("operating_income"),
    ]
    caveats: list[str] = []

    if is_manufacturer and market_cap is not None:
        # Original Z needs revenue (X5) and market value of equity (X4).
        rev_s = series.get("revenue")
        rev_map = dict(rev_s.values()) if rev_s else {}
        if d not in rev_map:
            return None
        x4 = market_cap / tl
        x5 = rev_map[d] / ta
        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
        zone = SAFE if z > 2.99 else DISTRESS if z < 1.81 else GREY
        model = Z_ORIGINAL
        formula = "1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5"
        used_series.append(rev_s)
        values_used = {
            "X1": x1, "X2": x2, "X3": x3, "X4": x4, "X5": x5,
            "market_cap": float(market_cap), "total_assets": ta,
            "total_liabilities": tl, "ebit": ebit,
        }
        caveats.append("X4 uses non-canonical market-price data (market cap).")
    else:
        # Z'' — book equity in X4, no sales ratio; replayable without prices.
        eq_s = series.get("equity")
        eq_map = dict(eq_s.values()) if eq_s else {}
        if d not in eq_map:
            return None
        book_equity = eq_map[d]
        x4 = book_equity / tl
        z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
        zone = SAFE if z > 2.6 else DISTRESS if z < 1.1 else GREY
        model = Z_DOUBLE_PRIME
        formula = "6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4"
        used_series.append(eq_s)
        values_used = {
            "X1": x1, "X2": x2, "X3": x3, "X4": x4,
            "book_equity": book_equity, "total_assets": ta,
            "total_liabilities": tl, "ebit": ebit,
        }
        if is_manufacturer:
            caveats.append("Manufacturer without market cap -> book-based Z'' used.")

    tags, accns = _provenance(*used_series)
    return FactorResult(
        key="altman_z",
        label="Altman distress score",
        value=z,
        status=OK,
        detail={"model": model, "zone": zone},
        formula=formula,
        values_used=values_used,
        input_tags=tags,
        input_accessions=accns,
        period_ends={"latest": d},
        caveats=caveats,
    )


# --------------------------------------------------------------------------- #
# ROA / ROE (used for financial-bucket companies and the composite)
# --------------------------------------------------------------------------- #


def _compute_roa(series: dict[str, MetricSeries]) -> FactorResult | None:
    got = _latest_common(series, ("net_income", "total_assets"))
    if got is None:
        return None
    d, vals = got
    ta = vals["total_assets"]
    if ta <= 0:
        return None
    tags, accns = _provenance(series.get("net_income"), series.get("total_assets"))
    return FactorResult(
        key="roa",
        label="Return on assets",
        value=vals["net_income"] / ta,
        status=OK,
        formula="net_income / total_assets",
        values_used={"net_income": vals["net_income"], "total_assets": ta},
        input_tags=tags,
        input_accessions=accns,
        period_ends={"latest": d},
    )


def _compute_roe(
    series: dict[str, MetricSeries], derived: dict[str, DerivedMetric]
) -> FactorResult | None:
    """ROE from the derived metric (net_income / 2-year-average equity) if
    available; else a latest-point net_income/equity fallback."""
    dm = derived.get("roe")
    if dm is not None and dm.latest is not None:
        d = dm.points[-1][0]
        return FactorResult(
            key="roe",
            label="Return on equity",
            value=dm.latest,
            status=OK,
            formula=dm.formula,
            input_tags=list(dm.input_tags),
            input_accessions=list(dm.input_accessions),
            period_ends={"latest": d},
        )
    got = _latest_common(series, ("net_income", "equity"))
    if got is None:
        return None
    d, vals = got
    eq = vals["equity"]
    if eq <= 0:
        return None
    tags, accns = _provenance(series.get("net_income"), series.get("equity"))
    return FactorResult(
        key="roe",
        label="Return on equity",
        value=vals["net_income"] / eq,
        status=OK,
        formula="net_income / equity (latest point)",
        values_used={"net_income": vals["net_income"], "equity": eq},
        input_tags=tags,
        input_accessions=accns,
        period_ends={"latest": d},
    )


# --------------------------------------------------------------------------- #
# Composite + dispatcher
# --------------------------------------------------------------------------- #


def _subscore(fr: FactorResult) -> float | None:
    """Map a computed factor to a rough 0-1 desirability sub-score for the
    composite. Anchors are deliberately loose research heuristics, not a rating;
    None means the factor does not contribute (not computed / not scorable)."""
    if fr.status != OK or fr.value is None:
        return None
    key = fr.key
    if key == "piotroski_f":
        return _clamp(fr.value / 9.0)
    if key == "gross_profitability":
        return _clamp(fr.value)  # GP/A rarely exceeds 1; higher better
    if key == "accruals_quality":
        return _clamp(0.5 - 5.0 * fr.value)  # lower (more negative) is better
    if key == "altman_z":
        zone = fr.detail.get("zone")
        return {SAFE: 1.0, GREY: 0.5, DISTRESS: 0.0}.get(zone)
    if key == "magic_formula":
        ey = fr.detail.get("earnings_yield", 0.0)
        roic = fr.detail.get("roic", 0.0)
        return (_clamp(ey / 0.15) + _clamp(roic / 0.25)) / 2.0
    if key == "roa":
        return _clamp(fr.value / 0.15)
    if key == "roe":
        return _clamp(fr.value / 0.20)
    return None


def _na(key: str, label: str, reason: str) -> FactorResult:
    return FactorResult(key=key, label=label, value=None,
                        status=NOT_APPLICABLE, reason=reason)


def compute_quality_factors(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    bucket: str,
    sic: str | int | None,
    market: MarketContext | None = None,
    ev: Any = None,
) -> QualityFactors:
    """Dispatch and bundle the quality/distress factors for one company.

    Financial buckets (banks/insurers/other-financial): only ROA and ROE are
    meaningful — the industrial factors (Piotroski, gross profitability, Magic
    Formula, accruals, Altman) are carried as NOT_APPLICABLE, because industrial
    margin/turnover/working-capital structure does not describe a balance-sheet
    business. Everyone else gets the full industrial set plus ROA/ROE.

    The composite (0-100) is a coverage-weighted blend of whichever applicable
    factors were actually computed — a rough research summary, not a rating.
    """
    factors: dict[str, FactorResult] = {}

    if is_financial(bucket):
        metric_set = "financial"
        applicable = ("roa", "roe")
        roa = _compute_roa(series)
        roe = _compute_roe(series, derived)
        factors["roa"] = roa or FactorResult(
            "roa", "Return on assets", None, status=UNAVAILABLE,
            reason="net_income / total_assets unavailable")
        factors["roe"] = roe or FactorResult(
            "roe", "Return on equity", None, status=UNAVAILABLE,
            reason="net_income / equity unavailable")
        na_reason = f"industrial factor not meaningful for financial bucket '{bucket}'"
        factors["piotroski_f"] = _na("piotroski_f", "Piotroski F-score", na_reason)
        factors["gross_profitability"] = _na(
            "gross_profitability", "Gross profitability (Novy-Marx)", na_reason)
        factors["magic_formula"] = _na(
            "magic_formula", "Magic Formula (single-name variant)", na_reason)
        factors["accruals_quality"] = _na(
            "accruals_quality", "Accruals (Sloan; lower is better)", na_reason)
        factors["altman_z"] = _na("altman_z", "Altman distress score", na_reason)
    else:
        metric_set = "industrial"
        applicable = (
            "piotroski_f", "gross_profitability", "magic_formula",
            "accruals_quality", "altman_z", "roa", "roe",
        )
        builders: dict[str, FactorResult | None] = {
            "piotroski_f": compute_piotroski_f_score(series),
            "gross_profitability": compute_gross_profitability(series),
            "magic_formula": compute_magic_formula(series, derived, market, ev),
            "accruals_quality": compute_accruals_quality(series),
            "altman_z": compute_altman_z(series, derived, market, sic),
            "roa": _compute_roa(series),
            "roe": _compute_roe(series, derived),
        }
        labels = {
            "piotroski_f": "Piotroski F-score",
            "gross_profitability": "Gross profitability (Novy-Marx)",
            "magic_formula": "Magic Formula (single-name variant)",
            "accruals_quality": "Accruals (Sloan; lower is better)",
            "altman_z": "Altman distress score",
            "roa": "Return on assets",
            "roe": "Return on equity",
        }
        for key in applicable:
            fr = builders[key]
            factors[key] = fr or FactorResult(
                key, labels[key], None, status=UNAVAILABLE,
                reason="required inputs unavailable")

    # Coverage-weighted composite over the applicable factor set.
    subs = [s for k in applicable if (s := _subscore(factors[k])) is not None]
    composite = round(sum(subs) / len(subs) * 100.0, 1) if subs else None
    coverage = len(subs) / len(applicable) if applicable else 0.0
    note = (
        f"Composite blends {len(subs)} of {len(applicable)} applicable factors "
        f"(coverage {coverage * 100:.0f}%); rough research summary, not a rating."
    )

    return QualityFactors(
        bucket=bucket,
        metric_set=metric_set,
        factors=factors,
        composite=composite,
        coverage=coverage,
        note=note,
        caveats=[
            "Factor scores are research flags, not advice or price targets.",
        ],
    )
