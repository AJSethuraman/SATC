"""Forensic / earnings-manipulation and balance-sheet stress detection (pure).

Research red flags, NOT an accusation and NOT advice. Every number here is a
mechanical function of as-filed fundamentals and is carried with full provenance
(the exact values used, the source XBRL tags, the filing accessions, and the two
period ends compared), so any signal is auditable end to end.

Two entry points:

- ``compute_beneish_m_score``: the eight Beneish (1999) indices and the composite
  M-score from two consecutive fiscal years. M > -1.78 flags a company whose
  accruals/growth profile *resembles* that of known manipulators — a screen, not
  a verdict.
- ``compute_stress_report``: a broader red-flag scanner that combines the Beneish
  flag with independent accrual / cash-flow / leverage / margin stress signals
  into a count and a ranked list.

Money-critical invariant enforced throughout: every ratio goes through a
safe-division guard. A near-zero denominator NEVER produces a garbage or
infinite index — the affected index is returned as ``None`` and the composite
M-score is marked unavailable. Missing any required metric yields ``None``
(UNAVAILABLE) rather than a fabricated score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from stock_helper.features.metrics import DerivedMetric
from stock_helper.normalization.facts import MetricSeries
from stock_helper.valuation import OK, VALUATION_VERSION
from stock_helper.valuation.factors import (
    DISTRESS,
    FactorResult,
    compute_altman_z,
    compute_ohlson_o_score,
    compute_zmijewski_score,
)

if TYPE_CHECKING:  # avoid importing the heavy (pandas/sqlmodel) context module
    from stock_helper.features.context import MarketContext


# Beneish M-score coefficients (Beneish, 1999, "The Detection of Earnings
# Manipulation"). Eight-variable model.
_M_INTERCEPT = -4.84
_M_COEFFS = {
    "DSRI": 0.920,
    "GMI": 0.528,
    "AQI": 0.404,
    "SGI": 0.892,
    "DEPI": 0.115,
    "SGAI": -0.172,
    "TATA": 4.679,
    "LVGI": -0.327,
}
# Above this the model classifies a company as a "possible manipulator".
_M_THRESHOLD = -1.78

# Required raw metric keys for the Beneish computation. Missing any -> None.
_BENEISH_REQUIRED = (
    "revenue",
    "cost_of_revenue",
    "accounts_receivable",
    "current_assets",
    "ppe_net",
    "total_assets",
    "depreciation_amortization",
    "sga_expense",
    "current_liabilities",
    "long_term_debt",
    "net_income",
    "operating_cash_flow",
)

# Denominators with magnitude at or below this read as "effectively zero": the
# ratio would explode, so we decline rather than emit a meaningless number.
_EPS = 1e-9

# Stress-scanner thresholds (absolute, deliberately conservative research cuts).
_ACCRUAL_HI = 0.10  # Sloan accrual ratio (NI - OCF)/assets
_OCF_NI_FLOOR = 0.5  # OCF below this fraction of positive NI = divergence
_GROWTH_GAP = 0.15  # receivables/inventory growth minus sales growth
_LEVERAGE_JUMP = 0.10  # absolute YoY rise in debt/assets
_MARGIN_DROP = 0.05  # absolute YoY fall in operating margin

# Ranking of red flags, most severe first. ``worst`` is the first flag in this
# order that fired — a fixed, auditable priority rather than a fuzzy score.
_SEVERITY_ORDER = (
    "distress_model_agreement",
    "beneish_flag",
    "montier_high",
    "high_accruals",
    "ocf_ni_divergence",
    "receivables_outgrowing_sales",
    "inventory_bloat",
    "leverage_spike",
    "margin_collapse",
)

# Montier C-score: >= this many of the six earnings-quality flags = aggressive.
_MONTIER_HIGH = 4
# Distress-model panel: >= this many of {altman, ohlson, zmijewski} agreeing on
# distress is treated as a corroborated signal.
_DISTRESS_AGREE = 2


# --------------------------------------------------------------------------- #
# Result dataclasses (provenance-carrying)
# --------------------------------------------------------------------------- #


@dataclass
class BeneishResult:
    """Beneish M-score with all eight indices and full provenance.

    ``m_score is None`` <=> the composite could not be formed because at least one
    index was undefined (a near-zero denominator); ``flag`` is then False. Each
    index in ``indices`` may independently be None for the same reason. This is a
    manipulation *screen*, never an accusation — see ``caveats``.
    """

    m_score: float | None
    flag: bool
    indices: dict[str, float | None]
    index_inputs: dict[str, dict[str, float | None]]
    values_used: dict[str, dict[str, float]]
    period_ends: dict[str, date]  # {"t": ..., "t_minus_1": ...}
    formula: str
    input_tags: list[str] = field(default_factory=list)
    input_accessions: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    engine_version: str = VALUATION_VERSION


@dataclass
class StressReport:
    """A count + ranked list of independent balance-sheet / earnings red flags.

    Each entry in ``stress_flags`` is ``(key, reason, value)``: the flag key, a
    human reason, and the numeric figure that tripped it. ``worst`` is the
    highest-severity flag present (fixed priority order) or None. A research
    scanner — NOT an accusation of fraud, and NOT advice; see ``caveats``.
    """

    stress_flags: list[tuple[str, str, float]]
    flag_count: int
    worst: str | None
    m_score: float | None
    caveats: list[str] = field(default_factory=list)
    engine_version: str = VALUATION_VERSION


# --------------------------------------------------------------------------- #
# Safe arithmetic
# --------------------------------------------------------------------------- #


def _safe_div(num: float | None, den: float | None) -> float | None:
    """num / den, or None if either operand is None or |den| <= _EPS.

    The single choke point that keeps a near-zero denominator from ever
    producing an infinite or garbage index (a real-money correctness rule)."""
    if num is None or den is None or abs(den) <= _EPS:
        return None
    return num / den


def _minus_one(x: float | None) -> float | None:
    """1 - x, propagating None (used for the AQI asset-quality complement)."""
    return None if x is None else 1.0 - x


# --------------------------------------------------------------------------- #
# Beneish M-score
# --------------------------------------------------------------------------- #


def _two_year_values(
    series: dict[str, MetricSeries],
) -> tuple[dict[str, dict[str, float]], date, date] | None:
    """Extract each required metric's value at the two most recent period ends
    shared by ALL required series (t and t-1). None if any metric is missing or
    there are fewer than two common annual period ends (needs 2 consecutive FYs).
    """
    maps: dict[str, dict[date, float]] = {}
    for key in _BENEISH_REQUIRED:
        s = series.get(key)
        if s is None or len(s.points) < 2:
            return None
        maps[key] = dict(s.values())

    common = set.intersection(*(set(m) for m in maps.values()))
    if len(common) < 2:
        return None
    t_minus_1, t = sorted(common)[-2:]

    values = {
        key: {"t": maps[key][t], "t_minus_1": maps[key][t_minus_1]}
        for key in _BENEISH_REQUIRED
    }
    return values, t, t_minus_1


def _beneish_indices(
    v: dict[str, dict[str, float]],
) -> tuple[dict[str, float | None], dict[str, dict[str, float | None]]]:
    """The eight indices from the two-year value table, each None-safe.

    Also returns, per index, the intermediate ratios/levels it consumed so the
    result is fully auditable.
    """

    def t(key: str) -> float:
        return v[key]["t"]

    def p(key: str) -> float:  # prior year (t-1)
        return v[key]["t_minus_1"]

    # DSRI — days' sales in receivables index.
    dsr_t = _safe_div(t("accounts_receivable"), t("revenue"))
    dsr_p = _safe_div(p("accounts_receivable"), p("revenue"))
    dsri = _safe_div(dsr_t, dsr_p)

    # GMI — gross margin index (deterioration if > 1). GM = (Sales - COGS)/Sales.
    gm_t = _safe_div(t("revenue") - t("cost_of_revenue"), t("revenue"))
    gm_p = _safe_div(p("revenue") - p("cost_of_revenue"), p("revenue"))
    gmi = _safe_div(gm_p, gm_t)

    # AQI — asset quality index. AQ = 1 - (current_assets + ppe_net)/total_assets.
    aq_t = _minus_one(_safe_div(t("current_assets") + t("ppe_net"), t("total_assets")))
    aq_p = _minus_one(_safe_div(p("current_assets") + p("ppe_net"), p("total_assets")))
    aqi = _safe_div(aq_t, aq_p)

    # SGI — sales growth index.
    sgi = _safe_div(t("revenue"), p("revenue"))

    # DEPI — depreciation index. DepRate = D&A / (D&A + ppe_net).
    dr_t = _safe_div(t("depreciation_amortization"),
                     t("depreciation_amortization") + t("ppe_net"))
    dr_p = _safe_div(p("depreciation_amortization"),
                     p("depreciation_amortization") + p("ppe_net"))
    depi = _safe_div(dr_p, dr_t)

    # SGAI — SG&A index.
    sga_t = _safe_div(t("sga_expense"), t("revenue"))
    sga_p = _safe_div(p("sga_expense"), p("revenue"))
    sgai = _safe_div(sga_t, sga_p)

    # LVGI — leverage index. Lev = (current_liabilities + long_term_debt)/assets.
    lev_t = _safe_div(t("current_liabilities") + t("long_term_debt"), t("total_assets"))
    lev_p = _safe_div(p("current_liabilities") + p("long_term_debt"), p("total_assets"))
    lvgi = _safe_div(lev_t, lev_p)

    # TATA — total accruals to total assets (cash-flow proxy):
    #   (net_income_t - operating_cash_flow_t) / total_assets_t.
    # The original Beneish (1999) uses a balance-sheet accruals variant:
    #   (ΔCurrentAssets - ΔCash) - (ΔCurrentLiab - ΔCurrentDebt - ΔTaxPayable)
    #   - Depreciation, all over total assets. We use the cash-flow proxy because
    #   OCF is reliably tagged and the two agree closely absent large
    #   discontinued-ops / acquisition noise.
    tata = _safe_div(t("net_income") - t("operating_cash_flow"), t("total_assets"))

    indices: dict[str, float | None] = {
        "DSRI": dsri, "GMI": gmi, "AQI": aqi, "SGI": sgi,
        "DEPI": depi, "SGAI": sgai, "LVGI": lvgi, "TATA": tata,
    }
    index_inputs: dict[str, dict[str, float | None]] = {
        "DSRI": {"ar_t": t("accounts_receivable"), "sales_t": t("revenue"),
                 "ar_t_minus_1": p("accounts_receivable"), "sales_t_minus_1": p("revenue"),
                 "recv_ratio_t": dsr_t, "recv_ratio_t_minus_1": dsr_p},
        "GMI": {"gross_margin_t": gm_t, "gross_margin_t_minus_1": gm_p},
        "AQI": {"asset_quality_t": aq_t, "asset_quality_t_minus_1": aq_p},
        "SGI": {"sales_t": t("revenue"), "sales_t_minus_1": p("revenue")},
        "DEPI": {"dep_rate_t": dr_t, "dep_rate_t_minus_1": dr_p},
        "SGAI": {"sga_ratio_t": sga_t, "sga_ratio_t_minus_1": sga_p},
        "LVGI": {"leverage_t": lev_t, "leverage_t_minus_1": lev_p},
        "TATA": {"net_income_t": t("net_income"),
                 "operating_cash_flow_t": t("operating_cash_flow"),
                 "total_assets_t": t("total_assets")},
    }
    return indices, index_inputs


def compute_beneish_m_score(series: dict[str, MetricSeries]) -> BeneishResult | None:
    """Beneish eight-factor M-score from two consecutive fiscal years.

    Returns None (UNAVAILABLE) if any required metric is missing or there are
    not two common annual period ends. If a near-zero denominator makes any index
    undefined, that index is None and the composite ``m_score`` is None with a
    caveat — never a garbage score. ``flag`` (M > -1.78) means the accrual/growth
    profile *resembles* known manipulators; it is a screen, not a conclusion.
    """
    extracted = _two_year_values(series)
    if extracted is None:
        return None
    values, t, t_minus_1 = extracted

    indices, index_inputs = _beneish_indices(values)

    caveats = [
        "Beneish M-score is a statistical manipulation SCREEN, not proof of fraud "
        "or an accusation; false positives are common (esp. high-growth firms).",
        "Requires two clean consecutive fiscal years; restatements or M&A distort "
        "the year-over-year indices.",
    ]

    tags: set[str] = set()
    accns: set[str] = set()
    for key in _BENEISH_REQUIRED:
        s = series[key]
        tags.add(s.tag)
        accns.update(s.accessions())

    m_score: float | None
    if any(idx is None for idx in indices.values()):
        m_score = None
        flag = False
        caveats.append(
            "M-score unavailable: one or more indices had a near-zero denominator "
            "and were returned as None."
        )
    else:
        m_score = _M_INTERCEPT + sum(
            _M_COEFFS[name] * float(indices[name]) for name in _M_COEFFS
        )
        flag = m_score > _M_THRESHOLD

    return BeneishResult(
        m_score=m_score,
        flag=flag,
        indices=indices,
        index_inputs=index_inputs,
        values_used=values,
        period_ends={"t": t, "t_minus_1": t_minus_1},
        formula=(
            "M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI "
            "+ 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI"
        ),
        input_tags=sorted(tags),
        input_accessions=sorted(accns),
        caveats=caveats,
    )


# --------------------------------------------------------------------------- #
# Montier C-score (earnings-quality / aggressive-accounting flags)
# --------------------------------------------------------------------------- #

# The six Montier C-score flags, in order. Each fires +1 when accounting looks
# more aggressive year-over-year; a HIGHER total (0-6) is worse.
_MONTIER_FLAGS = (
    "growing_gap_ni_ocf",
    "dso_rising",
    "dsi_rising",
    "other_current_assets_rising",
    "declining_depreciation",
    "asset_growth_gt_10pct",
)
_MONTIER_ASSET_GROWTH = 0.10


def compute_montier_c_score(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
) -> FactorResult | None:
    """Montier C(ombined)-score: six 0/1 earnings-quality flags, summed 0-6.

    Flags (each +1 when the metric moved the *aggressive* way YoY):
      1. growing gap between accrual and cash earnings: (NI-OCF)/TA rose;
      2. days sales outstanding rising: receivables/revenue rose;
      3. days sales of inventory rising: inventory/revenue rose (0 if no
         inventory is reported);
      4. other current assets / revenue rose, where other current assets =
         current_assets - cash - receivables - inventory (omitted, with a note,
         if those pieces are not all available);
      5. declining depreciation rate: D&A/(D&A + net PP&E) fell;
      6. total-asset growth > 10% YoY.

    A HIGHER score means more aggressive accounting; C >= 4 is the common cut for
    "watch". Needs two consecutive fiscal years anchored on total assets, net
    income and operating cash flow; returns None if fewer than two such common
    period ends exist. A flag whose inputs are missing scores 0 and is listed in
    ``detail['uncomputable']`` (we never fire a red flag we cannot verify);
    flag 4 is dropped from the denominator when uncomputable (``detail['omitted']``).

    Reference: James Montier, "Cooking the Books, or More Sailing Under the Black
    Flag" (2008), and "Value Investing" (2009) — the six-signal C-score.
    """
    anchor = ("total_assets", "net_income", "operating_cash_flow")
    maps: dict[str, dict[date, float]] = {}
    for key in anchor:
        s = series.get(key)
        if s is None or len(s.points) < 2:
            return None
        maps[key] = dict(s.values())
    common = set.intersection(*(set(maps[k]) for k in anchor))
    if len(common) < 2:
        return None
    t_minus_1, t = sorted(common)[-2:]

    # Optional metric maps (each flag guards its own availability).
    def m(key: str) -> dict[date, float]:
        s = series.get(key)
        return dict(s.values()) if s else {}

    rev = m("revenue")
    ar = m("accounts_receivable")
    inv = m("inventory")
    cash = m("cash")
    ca = m("current_assets")
    da = m("depreciation_amortization")
    ppe = m("ppe_net")
    ta = maps["total_assets"]
    ni = maps["net_income"]
    ocf = maps["operating_cash_flow"]

    flags: dict[str, int] = {}
    uncomputable: list[str] = []
    omitted: list[str] = []

    def has(mp: dict[date, float]) -> bool:
        return t in mp and t_minus_1 in mp

    # 1. Growing gap between accrual earnings and cash earnings.
    def gap(pe: date) -> float | None:
        if ta.get(pe, 0.0) <= 0:
            return None
        return (ni[pe] - ocf[pe]) / ta[pe]

    g_t, g_p = gap(t), gap(t_minus_1)
    if g_t is None or g_p is None:
        uncomputable.append("growing_gap_ni_ocf")
        flags["growing_gap_ni_ocf"] = 0
    else:
        flags["growing_gap_ni_ocf"] = 1 if g_t > g_p else 0

    # 2. Days sales outstanding (receivables / revenue) rising.
    def ratio_over_rev(mp: dict[date, float], pe: date) -> float | None:
        if pe not in mp or rev.get(pe, 0.0) <= 0:
            return None
        return mp[pe] / rev[pe]

    if has(ar) and has(rev):
        dso_t, dso_p = ratio_over_rev(ar, t), ratio_over_rev(ar, t_minus_1)
        if dso_t is None or dso_p is None:
            uncomputable.append("dso_rising")
            flags["dso_rising"] = 0
        else:
            flags["dso_rising"] = 1 if dso_t > dso_p else 0
    else:
        uncomputable.append("dso_rising")
        flags["dso_rising"] = 0

    # 3. Days sales of inventory rising (0 if no inventory reported at all).
    if not inv:
        flags["dsi_rising"] = 0  # deliberately 0, not uncomputable
    elif has(inv) and has(rev):
        dsi_t, dsi_p = ratio_over_rev(inv, t), ratio_over_rev(inv, t_minus_1)
        if dsi_t is None or dsi_p is None:
            uncomputable.append("dsi_rising")
            flags["dsi_rising"] = 0
        else:
            flags["dsi_rising"] = 1 if dsi_t > dsi_p else 0
    else:
        uncomputable.append("dsi_rising")
        flags["dsi_rising"] = 0

    # 4. Other current assets / revenue rising. Omitted if not computable.
    def oca(pe: date) -> float | None:
        if rev.get(pe, 0.0) <= 0:
            return None
        if not (pe in ca and pe in cash and pe in ar and pe in inv):
            return None
        return (ca[pe] - cash[pe] - ar[pe] - inv[pe]) / rev[pe]

    oca_t, oca_p = oca(t), oca(t_minus_1)
    if oca_t is None or oca_p is None:
        omitted.append("other_current_assets_rising")
    else:
        flags["other_current_assets_rising"] = 1 if oca_t > oca_p else 0

    # 5. Declining depreciation rate: D&A / (D&A + net PP&E) fell.
    def dep_rate(pe: date) -> float | None:
        if pe not in da or pe not in ppe:
            return None
        denom = da[pe] + ppe[pe]
        if denom <= 0:
            return None
        return da[pe] / denom

    dr_t, dr_p = dep_rate(t), dep_rate(t_minus_1)
    if dr_t is None or dr_p is None:
        uncomputable.append("declining_depreciation")
        flags["declining_depreciation"] = 0
    else:
        flags["declining_depreciation"] = 1 if dr_t < dr_p else 0

    # 6. Total-asset growth > 10% YoY.
    if ta[t_minus_1] > 0:
        growth = ta[t] / ta[t_minus_1] - 1.0
        flags["asset_growth_gt_10pct"] = 1 if growth > _MONTIER_ASSET_GROWTH else 0
    else:
        uncomputable.append("asset_growth_gt_10pct")
        flags["asset_growth_gt_10pct"] = 0

    score = float(sum(flags.values()))
    max_score = 6 - len(omitted)

    used = [
        series.get(k) for k in (
            "total_assets", "net_income", "operating_cash_flow", "revenue",
            "accounts_receivable", "inventory", "cash", "current_assets",
            "depreciation_amortization", "ppe_net",
        )
    ]
    tags = sorted({s.tag for s in used if s is not None})
    accns: set[str] = set()
    for s in used:
        if s is not None:
            accns.update(s.accessions())

    caveats = [
        "Montier C-score is an aggressive-accounting SCREEN, not proof of "
        "manipulation or an accusation; higher = more aggressive.",
        "Needs two clean consecutive fiscal years; restatements or M&A distort "
        "the year-over-year flags.",
    ]
    if uncomputable:
        caveats.append(
            "Flags scored 0 because inputs were missing: " + ", ".join(uncomputable)
        )
    if omitted:
        caveats.append(
            "Flags omitted from the score (inputs unavailable), max reduced to "
            f"{max_score}: " + ", ".join(omitted)
        )

    return FactorResult(
        key="montier_c",
        label="Montier C-score (aggressive accounting)",
        value=score,
        status=OK,
        detail={
            "flags": flags,
            "uncomputable": uncomputable,
            "omitted": omitted,
            "max": max_score,
        },
        formula="sum of 6 binary earnings-quality flags (higher = more aggressive)",
        values_used={"total_assets_t": ta[t], "total_assets_t_minus_1": ta[t_minus_1]},
        input_tags=tags,
        input_accessions=sorted(accns),
        period_ends={"t": t, "t_minus_1": t_minus_1},
        caveats=caveats,
    )


# --------------------------------------------------------------------------- #
# Stress report
# --------------------------------------------------------------------------- #


def _aligned_last_two(
    a: MetricSeries | None, b: MetricSeries | None
) -> tuple[float, float, float, float] | None:
    """(a_prev, a_curr, b_prev, b_curr) over the two most recent period ends
    common to both series, or None if fewer than two are shared."""
    if a is None or b is None:
        return None
    amap, bmap = dict(a.values()), dict(b.values())
    common = sorted(set(amap) & set(bmap))
    if len(common) < 2:
        return None
    d_prev, d_curr = common[-2], common[-1]
    return amap[d_prev], amap[d_curr], bmap[d_prev], bmap[d_curr]


def _growth(prev: float, curr: float) -> float | None:
    """Relative YoY growth curr/prev - 1, or None if prev is ~0."""
    q = _safe_div(curr, prev)
    return None if q is None else q - 1.0


def compute_stress_report(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None = None,
) -> StressReport:
    """Scan independent forensic red flags and return a count + ranked list.

    Flags (each fires at most once, on the latest available year):
      - beneish_flag: Beneish M > -1.78
      - high_accruals: (NI - OCF)/assets > 0.10 (Sloan accrual ratio)
      - ocf_ni_divergence: NI > 0 but OCF < 0.5 * NI
      - receivables_outgrowing_sales: AR growth - revenue growth > 0.15
      - inventory_bloat: inventory growth - revenue growth > 0.15 (if inventory present)
      - leverage_spike: debt/assets rose > 0.10 absolute YoY
      - margin_collapse: operating margin fell > 0.05 absolute YoY
      - montier_high: Montier C-score >= 4 (aggressive-accounting flags)
      - distress_model_agreement: >= 2 of Altman/Ohlson/Zmijewski flag distress

    ``market`` is accepted for signature symmetry with the other engines but is
    not needed here (all flags are fundamentals-only). Text / 8-K flags
    (going-concern, Item 4.02 non-reliance) are layered in later by the compose
    stage — this function never fetches them.
    """
    flags: list[tuple[str, str, float]] = []

    # --- Beneish flag ---
    beneish = compute_beneish_m_score(series)
    m_score = beneish.m_score if beneish is not None else None
    if beneish is not None and beneish.flag and m_score is not None:
        flags.append((
            "beneish_flag",
            f"Beneish M-score {m_score:.2f} exceeds -1.78 (manipulation screen).",
            m_score,
        ))

    # --- High accruals (Sloan) ---
    accr = derived.get("accrual_proxy")
    if accr is not None and accr.latest is not None and accr.latest > _ACCRUAL_HI:
        flags.append((
            "high_accruals",
            f"Accrual ratio (NI-OCF)/assets {accr.latest:.2f} > {_ACCRUAL_HI:.2f}; "
            "earnings poorly backed by cash.",
            accr.latest,
        ))

    # --- OCF / NI divergence (latest common year) ---
    ni_s, ocf_s = series.get("net_income"), series.get("operating_cash_flow")
    if ni_s is not None and ocf_s is not None:
        ni_map, ocf_map = dict(ni_s.values()), dict(ocf_s.values())
        shared = sorted(set(ni_map) & set(ocf_map))
        if shared:
            d = shared[-1]
            ni, ocf = ni_map[d], ocf_map[d]
            if ni > 0 and ocf < _OCF_NI_FLOOR * ni:
                flags.append((
                    "ocf_ni_divergence",
                    f"Positive net income {ni:,.0f} but operating cash flow only "
                    f"{ocf:,.0f} (< {_OCF_NI_FLOOR:g}x NI).",
                    ocf,
                ))

    # --- Receivables outgrowing sales ---
    rev_s, ar_s = series.get("revenue"), series.get("accounts_receivable")
    pair = _aligned_last_two(ar_s, rev_s)
    if pair is not None:
        ar_prev, ar_curr, rev_prev, rev_curr = pair
        g_ar, g_rev = _growth(ar_prev, ar_curr), _growth(rev_prev, rev_curr)
        if g_ar is not None and g_rev is not None and (g_ar - g_rev) > _GROWTH_GAP:
            flags.append((
                "receivables_outgrowing_sales",
                f"Receivables grew {g_ar:.0%} vs sales {g_rev:.0%} "
                f"(gap {g_ar - g_rev:.0%} > {_GROWTH_GAP:.0%}).",
                g_ar - g_rev,
            ))

    # --- Inventory bloat (only if inventory is tagged) ---
    inv_s = series.get("inventory")
    pair = _aligned_last_two(inv_s, rev_s)
    if pair is not None:
        inv_prev, inv_curr, rev_prev, rev_curr = pair
        g_inv, g_rev = _growth(inv_prev, inv_curr), _growth(rev_prev, rev_curr)
        if g_inv is not None and g_rev is not None and (g_inv - g_rev) > _GROWTH_GAP:
            flags.append((
                "inventory_bloat",
                f"Inventory grew {g_inv:.0%} vs sales {g_rev:.0%} "
                f"(gap {g_inv - g_rev:.0%} > {_GROWTH_GAP:.0%}).",
                g_inv - g_rev,
            ))

    # --- Leverage spike (debt/assets YoY) ---
    dta = derived.get("debt_to_assets")
    if dta is not None and len(dta.points) >= 2:
        prev, curr = dta.points[-2][1], dta.points[-1][1]
        if (curr - prev) > _LEVERAGE_JUMP:
            flags.append((
                "leverage_spike",
                f"Debt/assets rose {curr - prev:.2f} YoY "
                f"({prev:.2f} -> {curr:.2f}, > {_LEVERAGE_JUMP:.2f}).",
                curr - prev,
            ))

    # --- Margin collapse (operating margin YoY) ---
    om = derived.get("operating_margin")
    if om is not None and len(om.points) >= 2:
        prev, curr = om.points[-2][1], om.points[-1][1]
        if (prev - curr) > _MARGIN_DROP:
            flags.append((
                "margin_collapse",
                f"Operating margin fell {prev - curr:.2f} YoY "
                f"({prev:.2f} -> {curr:.2f}, > {_MARGIN_DROP:.2f}).",
                prev - curr,
            ))

    # --- Montier C-score (aggressive accounting) ---
    montier = compute_montier_c_score(series, derived)
    if montier is not None and montier.value is not None and montier.value >= _MONTIER_HIGH:
        flags.append((
            "montier_high",
            f"Montier C-score {montier.value:.0f} of {montier.detail.get('max', 6)} "
            f">= {_MONTIER_HIGH}; multiple aggressive-accounting flags fired.",
            montier.value,
        ))

    # --- Distress-model agreement (Altman / Ohlson / Zmijewski panel) ---
    # Independent models corroborating each other is the real signal. Altman is
    # called without SIC/market (book-based Z'' path), matching this scanner's
    # fundamentals-only contract.
    distress_models = {
        "altman": compute_altman_z(series, derived, market, sic=None),
        "ohlson": compute_ohlson_o_score(series, derived),
        "zmijewski": compute_zmijewski_score(series, derived),
    }
    agree = [
        name for name, fr in distress_models.items()
        if fr is not None and fr.status == OK and fr.detail.get("zone") == DISTRESS
    ]
    if len(agree) >= _DISTRESS_AGREE:
        flags.append((
            "distress_model_agreement",
            f"{len(agree)} distress models agree ({', '.join(sorted(agree))}); "
            "corroborated across independent bankruptcy screens.",
            float(len(agree)),
        ))

    fired = {key for key, _, _ in flags}
    worst = next((k for k in _SEVERITY_ORDER if k in fired), None)

    caveats = [
        "Red-flag SCANNER for research triage — NOT an accusation of fraud, a "
        "conclusion, or investment advice. Any flag warrants reading the filings.",
        "Fundamentals-only: text/8-K flags (going-concern, Item 4.02 non-reliance) "
        "are added by the compose layer, not here.",
        "Distress-model agreement folds in Altman/Ohlson/Zmijewski; agreement "
        "across independent SCREENS is the signal, and none is a verdict.",
    ]

    return StressReport(
        stress_flags=flags,
        flag_count=len(flags),
        worst=worst,
        m_score=m_score,
        caveats=caveats,
    )
