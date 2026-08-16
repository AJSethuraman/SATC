"""DCF / intrinsic-value engine (pure calculation).

Research aid — NOT investment advice and NOT a price target. Every number here
is a scenario estimate that falls out of explicit, editable assumptions.

The load-bearing correctness rule (design-critic bug F1): LEVERED and
OWNER_EARNINGS free cash flow already belong to EQUITY holders, so they are
discounted at the given ``discount_rate`` (a cost of equity) and net debt is
NOT subtracted — the present value of those flows *is* the equity value. Only
UNLEVERED (FCFF) is an enterprise flow: discount, then subtract net debt to get
equity. Subtracting net debt from a levered flow would double-count leverage and
systematically understate fair value.

Layering:
- ``dcf_value`` / ``reverse_dcf_implied_growth`` are the pure unit-test seam:
  plain floats in, an auditable ``DcfResult`` out, no series/DB/network.
- ``run_dcf`` / ``reverse_dcf`` / ``run_financial_valuation`` / ``run_valuation``
  read the normalized series + derived metrics + optional market context and
  feed the core. Non-positive denominators or missing inputs yield a status
  (UNAVAILABLE / NEGATIVE_FCF / NOT_APPLICABLE) with a reason — never a bogus
  number.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from stock_helper.features.metrics import DerivedMetric
from stock_helper.industry.sic_buckets import FINANCIAL_BUCKETS
from stock_helper.normalization.facts import MetricSeries
from stock_helper.valuation import (
    INSUFFICIENT_DATA,
    NEGATIVE_FCF,
    NOT_APPLICABLE,
    OK,
    UNAVAILABLE,
    VALUATION_VERSION,
)
from stock_helper.valuation.stats import median
from stock_helper.valuation.types import (
    EXIT_MULTIPLE,
    GORDON,
    LEVERED,
    UNLEVERED,
    Assumptions,
)

# Estimated stage-1 growth is capped to a sane band: never below the long-run
# terminal growth (that would be a self-contradiction), never above this ceiling
# (extrapolating a >15% CAGR into a multi-year explicit window is not honest).
GROWTH_CEILING = 0.15


@dataclass
class DcfResult:
    """One fully-auditable DCF scenario. Carries not just the headline value but
    every input, the formula, and the source tags/accessions so a reviewer can
    reconstruct the number. Any field may be None when the scenario could not be
    computed — ``status`` and ``caveats`` say why."""

    status: str = OK
    method: str = "dcf"
    # Headline outputs
    equity_value: float | None = None
    enterprise_value: float | None = None
    fair_value_per_share: float | None = None
    margin_of_safety: float | None = None  # (fair - price) / fair; None w/o price
    # Value decomposition
    pv_explicit: float | None = None
    terminal_value: float | None = None  # undiscounted TV at year N
    pv_terminal: float | None = None
    terminal_weight: float | None = None  # pv_terminal / equity_value
    projection: list[tuple[int, float, float]] = field(default_factory=list)
    # Inputs (provenance)
    base_fcf: float | None = None
    fcf_basis: str = LEVERED
    net_debt: float = 0.0
    shares: float | None = None
    discount_rate: float | None = None
    terminal_growth: float | None = None
    stage1_growth: float | None = None
    stage1_years: int | None = None
    fade_to_terminal: bool = False
    terminal_method: str = GORDON
    formula: str = ""
    period_ends: list[date] = field(default_factory=list)
    input_tags: list[str] = field(default_factory=list)
    input_accessions: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)  # method-specific extras
    engine_version: str = VALUATION_VERSION


@dataclass
class ReverseDcfResult:
    """What stage-1 growth the *current* price already implies. A market-expectation
    diagnostic, not a recommendation: if the implied growth looks unattainable the
    stock is priced for perfection; if it's trivially low the market is skeptical."""

    status: str = OK
    implied_growth: float | None = None
    target_price: float | None = None
    target_equity_value: float | None = None
    historical_fcf_cagr: float | None = None
    discount_rate: float | None = None
    terminal_growth: float | None = None
    stage1_years: int | None = None
    caveat: str = ""
    caveats: list[str] = field(default_factory=list)
    engine_version: str = VALUATION_VERSION


@dataclass
class SensitivityTable:
    """Fair-value-per-share grid over (stage-1 growth, discount rate). The point
    of a DCF is not the single number but how it moves with the two assumptions
    it is most sensitive to — this makes that fragility explicit."""

    growths: list[float] = field(default_factory=list)
    discount_rates: list[float] = field(default_factory=list)
    grid: list[list[float | None]] = field(default_factory=list)  # rows=growth
    base_growth: float | None = None
    base_discount_rate: float | None = None
    engine_version: str = VALUATION_VERSION


# --- pure core ---------------------------------------------------------------


def _project_fcfs(
    fcf_0: float, stage1_growth: float, stage1_years: int,
    terminal_growth: float, fade_to_terminal: bool,
) -> list[float]:
    """Projected FCF for years 1..N.

    Constant growth: FCF_t = fcf_0 * (1 + stage1_growth)**t. With
    ``fade_to_terminal`` the annual growth rate is linearly walked from
    stage1_growth (year 1) down to terminal_growth (year N), which avoids the
    unrealistic cliff of high growth abruptly collapsing into perpetuity.
    """
    fcfs: list[float] = []
    prev = fcf_0
    for t in range(1, stage1_years + 1):
        if fade_to_terminal and stage1_years > 1:
            g_t = stage1_growth + (terminal_growth - stage1_growth) * (t - 1) / (
                stage1_years - 1
            )
        else:
            g_t = stage1_growth
        prev = prev * (1.0 + g_t)
        fcfs.append(prev)
    return fcfs


def _fail(method: str, status: str, reason: str, **inputs: Any) -> DcfResult:
    return DcfResult(status=status, method=method, caveats=[reason], **inputs)


def dcf_value(
    fcf_0: float,
    stage1_growth: float,
    stage1_years: int,
    discount_rate: float,
    terminal_growth: float,
    shares: float | None,
    *,
    net_debt: float = 0.0,
    fcf_basis: str = LEVERED,
    fade_to_terminal: bool = False,
    terminal_method: str = GORDON,
    exit_multiple: float | None = None,
    terminal_ebitda: float | None = None,
) -> DcfResult:
    """Two-stage DCF. Pure: floats in, an auditable :class:`DcfResult` out.

    Equity vs enterprise flow (bug F1): for LEVERED / OWNER_EARNINGS the summed
    present value already IS equity value — net debt is recorded but NOT
    subtracted. For UNLEVERED the sum is enterprise value and net debt is
    subtracted to reach equity.
    """
    common = dict(
        base_fcf=fcf_0, fcf_basis=fcf_basis, net_debt=net_debt,
        shares=shares, discount_rate=discount_rate, terminal_growth=terminal_growth,
        stage1_growth=stage1_growth, stage1_years=stage1_years,
        fade_to_terminal=fade_to_terminal, terminal_method=terminal_method,
    )

    if stage1_years < 1:
        return _fail("dcf", INSUFFICIENT_DATA, "stage1_years must be >= 1", **common)

    # Terminal-value guards: never divide by a non-positive (r - g) and never
    # accept an exit multiple with no EBITDA to multiply.
    if terminal_method == GORDON and discount_rate <= terminal_growth:
        return _fail(
            "dcf", UNAVAILABLE,
            f"discount_rate ({discount_rate}) must exceed terminal_growth "
            f"({terminal_growth}) for a Gordon terminal value",
            **common,
        )
    if terminal_method == EXIT_MULTIPLE and (
        exit_multiple is None or terminal_ebitda is None
    ):
        return _fail(
            "dcf", UNAVAILABLE,
            "EXIT_MULTIPLE terminal needs both exit_multiple and terminal_ebitda",
            **common,
        )

    fcfs = _project_fcfs(
        fcf_0, stage1_growth, stage1_years, terminal_growth, fade_to_terminal
    )

    projection: list[tuple[int, float, float]] = []
    pv_explicit = 0.0
    for t, fcf_t in enumerate(fcfs, start=1):
        discounted = fcf_t / (1.0 + discount_rate) ** t
        pv_explicit += discounted
        projection.append((t, fcf_t, discounted))

    fcf_n = fcfs[-1]
    if terminal_method == EXIT_MULTIPLE:
        terminal_value = float(exit_multiple) * float(terminal_ebitda)
        tv_formula = "exit_multiple * terminal_ebitda"
    else:
        terminal_value = fcf_n * (1.0 + terminal_growth) / (
            discount_rate - terminal_growth
        )
        tv_formula = "FCF_N*(1+g_term)/(r-g_term)"
    pv_terminal = terminal_value / (1.0 + discount_rate) ** stage1_years

    pv_flows = pv_explicit + pv_terminal
    if fcf_basis == UNLEVERED:
        enterprise_value = pv_flows
        equity_value = enterprise_value - net_debt
        bridge = "EV = PV(FCFF); equity = EV - net_debt"
    else:  # LEVERED / OWNER_EARNINGS: flows already belong to equity holders
        equity_value = pv_flows
        enterprise_value = equity_value + net_debt  # informational only
        bridge = "equity = PV(levered FCF); net_debt NOT subtracted"

    fair_value_per_share: float | None = None
    caveats: list[str] = [
        "Scenario estimate from explicit assumptions — not advice, not a target."
    ]
    if shares is not None and shares > 0:
        fair_value_per_share = equity_value / shares
    else:
        caveats.append("shares <= 0 or missing — per-share value not computed")

    terminal_weight = (
        pv_terminal / equity_value if equity_value not in (0, 0.0) else None
    )
    if terminal_weight is not None and terminal_weight > 0.75:
        caveats.append(
            "Terminal value is >75% of equity value — result leans heavily on "
            "the perpetuity assumption."
        )

    return DcfResult(
        status=OK,
        method="dcf",
        equity_value=equity_value,
        enterprise_value=enterprise_value,
        fair_value_per_share=fair_value_per_share,
        margin_of_safety=None,
        pv_explicit=pv_explicit,
        terminal_value=terminal_value,
        pv_terminal=pv_terminal,
        terminal_weight=terminal_weight,
        projection=projection,
        base_fcf=fcf_0,
        fcf_basis=fcf_basis,
        net_debt=net_debt,
        shares=shares,
        discount_rate=discount_rate,
        terminal_growth=terminal_growth,
        stage1_growth=stage1_growth,
        stage1_years=stage1_years,
        fade_to_terminal=fade_to_terminal,
        terminal_method=terminal_method,
        formula=f"PV(FCF_1..N @ r) + PV(TV); TV={tv_formula}; {bridge}",
        caveats=caveats,
    )


def reverse_dcf_implied_growth(
    target_equity_value: float,
    fcf_0: float,
    stage1_years: int,
    discount_rate: float,
    terminal_growth: float,
    shares: float | None,
    *,
    bracket: tuple[float, float] = (-0.5, 1.0),
    tol: float = 1e-5,
    max_iter: int = 200,
) -> float | None:
    """Bisection for the stage-1 growth whose DCF equity value equals
    ``target_equity_value``.

    Equity value is monotonically increasing in stage-1 growth (higher growth =>
    larger, later cash flows), so bisection is well-posed. Returns None when the
    target lies outside the value range spanned by ``bracket`` (i.e. no growth in
    that band reproduces it) — never an extrapolated guess.
    """

    def equity_at(g: float) -> float | None:
        return dcf_value(
            fcf_0, g, stage1_years, discount_rate, terminal_growth, shares,
        ).equity_value

    lo, hi = bracket
    f_lo, f_hi = equity_at(lo), equity_at(hi)
    if f_lo is None or f_hi is None:
        return None
    f_lo -= target_equity_value
    f_hi -= target_equity_value
    if f_lo == 0.0:
        return lo
    if f_hi == 0.0:
        return hi
    if (f_lo > 0) == (f_hi > 0):  # target outside the bracket's value range
        return None

    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        f_mid = equity_at(mid)
        if f_mid is None:
            return None
        f_mid -= target_equity_value
        if abs(f_mid) < tol or (hi - lo) / 2.0 < tol:
            return mid
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def ddm_gordon(
    dps_0: float, growth: float, cost_of_equity: float
) -> float | None:
    """Gordon dividend-discount value: DPS_0*(1+g)/(r-g). None if r <= g (no
    finite perpetuity) or the dividend base is non-positive."""
    if cost_of_equity <= growth or dps_0 is None or dps_0 <= 0:
        return None
    return dps_0 * (1.0 + growth) / (cost_of_equity - growth)


def justified_pb(
    roe: float, growth: float, cost_of_equity: float
) -> float | None:
    """Justified price-to-book from residual income: (ROE - g)/(r - g). None if
    r <= g. Multiply by book value per share for a fair value."""
    if roe is None or cost_of_equity <= growth:
        return None
    return (roe - growth) / (cost_of_equity - growth)


def sensitivity(
    base_inputs: dict[str, Any],
    growth_deltas: tuple[float, ...] = (-0.04, -0.02, 0.0, 0.02, 0.04),
    rate_deltas: tuple[float, ...] = (-0.02, -0.01, 0.0, 0.01, 0.02),
) -> SensitivityTable:
    """Grid of fair-value-per-share over (stage-1 growth, discount rate),
    perturbing ``base_inputs`` by each delta. Uses the pure core so the table is
    exactly consistent with the headline DCF. Cells where the perturbed scenario
    is invalid (e.g. r <= g_terminal) are None, not fabricated."""
    base_g = base_inputs["stage1_growth"]
    base_r = base_inputs["discount_rate"]
    growths = [base_g + d for d in growth_deltas]
    rates = [base_r + d for d in rate_deltas]

    grid: list[list[float | None]] = []
    for g in growths:
        row: list[float | None] = []
        for r in rates:
            kwargs = dict(base_inputs)
            kwargs["stage1_growth"] = g
            kwargs["discount_rate"] = r
            row.append(dcf_value(**kwargs).fair_value_per_share)
        grid.append(row)

    return SensitivityTable(
        growths=growths, discount_rates=rates, grid=grid,
        base_growth=base_g, base_discount_rate=base_r,
    )


# --- assembly (reads series / derived / market) ------------------------------


def _cagr_from_metric(m: DerivedMetric | None) -> tuple[float | None, str]:
    """Compound annual growth over a derived metric's history. Requires >=2
    periods and strictly positive endpoints (a CAGR across a sign change or from
    a non-positive base is meaningless)."""
    if m is None or len(m.points) < 2:
        return None, ""
    first = m.points[0][1]
    last = m.points[-1][1]
    years = len(m.points) - 1
    if first <= 0 or last <= 0:
        return None, ""
    cagr = (last / first) ** (1.0 / years) - 1.0
    return cagr, f"{m.key} CAGR over {years}y"


def estimate_growth(
    derived: dict[str, DerivedMetric], terminal_growth: float | None = None
) -> tuple[float | None, str]:
    """Estimate stage-1 growth: FCF CAGR if the FCF history is clean, else fall
    back to revenue CAGR. Capped to [terminal_growth, GROWTH_CEILING] so the
    projection can never grow slower than perpetuity or faster than 15%/yr.
    Returns (growth, method-note)."""
    floor = (
        terminal_growth if terminal_growth is not None
        else Assumptions().terminal_growth
    )

    cagr, note = _cagr_from_metric(derived.get("free_cash_flow"))
    if cagr is None:
        cagr, note = _cagr_from_metric(derived.get("revenue"))
        if cagr is not None:
            note = f"FCF CAGR unavailable; fell back to {note}"
    if cagr is None:
        return None, "no clean FCF or revenue history for a growth estimate"

    capped = max(floor, min(GROWTH_CEILING, cagr))
    if capped != cagr:
        note += f" (raw {cagr:.4f} capped to [{floor:.4f}, {GROWTH_CEILING:.2f}])"
    return capped, note


def _resolve_shares(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: Any | None,
) -> float | None:
    if market is not None and getattr(market, "shares", None):
        return market.shares
    so = derived.get("shares_outstanding")
    if so is not None and so.latest and so.latest > 0:
        return so.latest
    so_series = series.get("shares_outstanding")
    if so_series and so_series.latest.value > 0:
        return so_series.latest.value
    return None


def _net_debt(derived: dict[str, DerivedMetric]) -> float:
    """total_debt - cash, each treated as 0 when the metric is unmapped."""
    td = derived.get("total_debt")
    cash = derived.get("cash")
    debt_v = td.latest if td and td.latest is not None else 0.0
    cash_v = cash.latest if cash and cash.latest is not None else 0.0
    return debt_v - cash_v


def run_dcf(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    bucket: str,
    market: Any | None,
    assumptions: Assumptions | None = None,
) -> DcfResult:
    """Assemble a DCF from normalized data. FCF-DCF is invalid for banks/insurers
    (their cash flows are not free cash flow in the industrial sense) — those
    buckets return NOT_APPLICABLE and should be routed to
    :func:`run_financial_valuation`."""
    a = assumptions or Assumptions()

    if bucket in FINANCIAL_BUCKETS:
        return DcfResult(
            status=NOT_APPLICABLE, method="dcf", fcf_basis=a.fcf_basis,
            caveats=[
                f"FCF-DCF is not applicable to financial bucket '{bucket}'; "
                "use dividend-discount / justified-P/B instead."
            ],
        )

    fcf = derived.get("free_cash_flow")
    if fcf is None or not fcf.points:
        return DcfResult(
            status=UNAVAILABLE, method="dcf", fcf_basis=a.fcf_basis,
            caveats=["free_cash_flow not available — cannot run a DCF."],
        )

    last3 = fcf.last_n(3)
    base_fcf = median(last3)
    period_ends = [d for d, _ in fcf.points[-3:]]
    if base_fcf is None:
        return DcfResult(
            status=UNAVAILABLE, method="dcf", fcf_basis=a.fcf_basis,
            caveats=["no usable free_cash_flow values for a base."],
        )
    if base_fcf <= 0:
        return DcfResult(
            status=NEGATIVE_FCF, method="dcf", base_fcf=base_fcf,
            fcf_basis=a.fcf_basis, period_ends=period_ends,
            input_tags=list(fcf.input_tags),
            input_accessions=list(fcf.input_accessions),
            caveats=[
                f"Median FCF base is non-positive ({base_fcf:.0f}) — a DCF on a "
                "negative cash-flow base would be meaningless."
            ],
        )

    growth_note = ""
    if a.growth_rate is not None:
        growth = a.growth_rate
        growth_note = "stage-1 growth from explicit assumption"
    else:
        growth, growth_note = estimate_growth(derived, a.terminal_growth)
        if growth is None:
            return DcfResult(
                status=UNAVAILABLE, method="dcf", base_fcf=base_fcf,
                fcf_basis=a.fcf_basis, period_ends=period_ends,
                caveats=[f"could not estimate growth: {growth_note}"],
            )

    net_debt = _net_debt(derived)
    shares = _resolve_shares(series, derived, market)

    result = dcf_value(
        base_fcf, growth, a.stage1_years, a.discount_rate, a.terminal_growth,
        shares, net_debt=net_debt, fcf_basis=a.fcf_basis,
        fade_to_terminal=a.fade_to_terminal, terminal_method=a.terminal_method,
        exit_multiple=a.exit_multiple,
        terminal_ebitda=(derived["ebitda"].latest if derived.get("ebitda") else None),
    )

    # Enrich with provenance + market-relative margin of safety.
    tags = list(fcf.input_tags)
    accessions = list(fcf.input_accessions)
    for key in ("total_debt", "cash"):
        m = derived.get(key)
        if m is not None:
            tags.extend(m.input_tags)
            accessions.extend(m.input_accessions)
    result.period_ends = period_ends
    result.input_tags = sorted(set(tags))
    result.input_accessions = sorted(set(accessions))
    result.caveats.append(growth_note)

    if (
        market is not None
        and getattr(market, "price", None)
        and result.fair_value_per_share
    ):
        fair = result.fair_value_per_share
        result.margin_of_safety = (fair - market.price) / fair

    return result


def reverse_dcf(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    bucket: str,
    market: Any | None,
    assumptions: Assumptions | None = None,
) -> ReverseDcfResult:
    """Solve for the stage-1 growth the current market cap already prices in.
    Requires a market price/cap; without it there is no target to invert."""
    a = assumptions or Assumptions()

    if market is None or not getattr(market, "price", None):
        return ReverseDcfResult(
            status=UNAVAILABLE,
            caveat="Reverse DCF needs a market price/cap (none available).",
            caveats=["price data unavailable"],
        )
    if bucket in FINANCIAL_BUCKETS:
        return ReverseDcfResult(
            status=NOT_APPLICABLE,
            caveat=f"Reverse FCF-DCF not applicable to financial bucket '{bucket}'.",
        )

    fcf = derived.get("free_cash_flow")
    if fcf is None or not fcf.points:
        return ReverseDcfResult(
            status=UNAVAILABLE, caveat="free_cash_flow unavailable.",
            caveats=["no FCF"],
        )
    base_fcf = median(fcf.last_n(3))
    if base_fcf is None or base_fcf <= 0:
        return ReverseDcfResult(
            status=NEGATIVE_FCF,
            caveat="Non-positive FCF base — reverse DCF is meaningless.",
        )

    shares = _resolve_shares(series, derived, market)
    target_equity = getattr(market, "market_cap", None)
    if target_equity is None and shares:
        target_equity = market.price * shares
    if target_equity is None:
        return ReverseDcfResult(
            status=UNAVAILABLE,
            caveat="No market cap and no share count to build a target.",
        )

    implied = reverse_dcf_implied_growth(
        target_equity, base_fcf, a.stage1_years, a.discount_rate,
        a.terminal_growth, shares,
    )
    hist_cagr, _ = _cagr_from_metric(fcf)

    caveat = (
        "Growth the current price implies given the assumed discount/terminal "
        "rates — an expectations gauge, not a forecast or recommendation."
    )
    if implied is None:
        caveat = (
            "Current price is outside the growth band [-50%, +100%]; no plausible "
            "stage-1 growth reproduces it under these assumptions."
        )

    return ReverseDcfResult(
        status=OK if implied is not None else INSUFFICIENT_DATA,
        implied_growth=implied,
        target_price=market.price,
        target_equity_value=target_equity,
        historical_fcf_cagr=hist_cagr,
        discount_rate=a.discount_rate,
        terminal_growth=a.terminal_growth,
        stage1_years=a.stage1_years,
        caveat=caveat,
    )


def run_financial_valuation(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    bucket: str,
    market: Any | None,
    assumptions: Assumptions | None = None,
) -> DcfResult:
    """DDM + justified-P/B valuation for banks/insurers, reported side by side
    (never averaged — they answer different questions and disagreeing is signal).
    ``extra`` carries ddm_fair_value and justified_pb_fair_value with their
    inputs; ``fair_value_per_share`` is deliberately left None."""
    a = assumptions or Assumptions()

    if bucket not in FINANCIAL_BUCKETS:
        return DcfResult(
            status=NOT_APPLICABLE, method="ddm+justified_pb",
            caveats=[f"Financial valuation only applies to {FINANCIAL_BUCKETS}."],
        )

    dps = derived.get("dividends_per_share")
    roe_m = derived.get("roe")
    equity = derived.get("equity")
    shares = _resolve_shares(series, derived, market)

    caveats = [
        "Bank/insurer valuation: DDM and justified-P/B reported side by side, "
        "not averaged. Research flag, not advice."
    ]
    coe = a.discount_rate  # flat cost-of-equity assumption

    growth = a.growth_rate
    if growth is None:
        growth, note = estimate_growth(derived, a.terminal_growth)
        if growth is None:
            growth = a.terminal_growth
            note = "no growth history — used terminal growth"
        caveats.append(note)

    dps_0 = dps.latest if dps and dps.latest is not None else None
    roe = roe_m.latest if roe_m and roe_m.latest is not None else None
    bvps = None
    if equity and equity.latest and shares and shares > 0:
        bvps = equity.latest / shares

    ddm_val = ddm_gordon(dps_0, growth, coe) if dps_0 is not None else None
    jpb = justified_pb(roe, growth, coe) if roe is not None else None
    jpb_fair = jpb * bvps if (jpb is not None and bvps is not None) else None

    if ddm_val is None:
        caveats.append("DDM unavailable (no dividend, or cost-of-equity <= growth).")
    if jpb_fair is None:
        caveats.append("Justified-P/B unavailable (missing ROE / book value).")

    tags: list[str] = []
    accessions: list[str] = []
    for m in (dps, roe_m, equity):
        if m is not None:
            tags.extend(m.input_tags)
            accessions.extend(m.input_accessions)

    status = OK if (ddm_val is not None or jpb_fair is not None) else UNAVAILABLE
    return DcfResult(
        status=status,
        method="ddm+justified_pb",
        fair_value_per_share=None,  # side by side; do not average
        shares=shares,
        discount_rate=coe,
        terminal_growth=a.terminal_growth,
        stage1_growth=growth,
        formula="DDM: DPS_0*(1+g)/(r-g); justified_pb: (ROE-g)/(r-g) * BVPS",
        input_tags=sorted(set(tags)),
        input_accessions=sorted(set(accessions)),
        caveats=caveats,
        extra={
            "ddm_fair_value": ddm_val,
            "justified_pb": jpb,
            "justified_pb_fair_value": jpb_fair,
            "book_value_per_share": bvps,
            "dps_0": dps_0,
            "roe": roe,
            "growth": growth,
        },
    )


def run_valuation(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    bucket: str,
    market: Any | None,
    assumptions: Assumptions | None = None,
) -> DcfResult:
    """Dispatcher: financial buckets get DDM + justified-P/B, everything else
    gets FCF-DCF. Keeps callers from having to know the routing rule."""
    if bucket in FINANCIAL_BUCKETS:
        return run_financial_valuation(series, derived, bucket, market, assumptions)
    return run_dcf(series, derived, bucket, market, assumptions)
