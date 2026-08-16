"""Cost-of-capital engine: CAPM cost of equity, after-tax cost of debt, WACC.

Research aid — NOT investment advice. The discount rate a DCF uses is only as
defensible as its inputs, so this module derives Ke/Kd/WACC from explicit,
auditable pieces (risk-free rate, beta, equity risk premium, effective tax
rate, and the market-value equity/debt mix) and records a caveat for every
place it had to fall back to a default. Missing inputs degrade gracefully:
``compute_cost_of_capital`` always returns a result and never a bogus number —
the CAPM cost of equity is the floor, WACC never silently invents a debt cost.

Rules kept throughout: a non-positive or missing denominator yields None (with
a reason), never a fabricated ratio; every returned CostOfCapital carries its
method label and caveats so a reviewer can see exactly how it was built.
"""

from dataclasses import dataclass, field

from stock_helper.features.context import MarketContext
from stock_helper.features.metrics import DerivedMetric
from stock_helper.normalization.facts import MetricSeries

COST_OF_CAPITAL_VERSION = "cost-of-capital-0.1"

# Guardrails. Beta is clamped to a defensible band so a noisy OLS fit on thin
# data can't produce an absurd discount rate. The effective tax rate is clamped
# to [0, 0.5]: a negative rate (tax benefit year) or a >50% rate (one-off
# charges) shouldn't leak into a forward cost-of-debt shield.
BETA_MIN, BETA_MAX = 0.3, 2.5
TAX_RATE_MIN, TAX_RATE_MAX = 0.0, 0.5
DEFAULT_TAX_RATE = 0.21  # U.S. federal statutory corporate rate (TCJA, 2018-)
DEFAULT_BETA = 1.0  # market beta when a fit isn't derivable
MIN_BETA_POINTS = 60  # paired daily returns needed for a usable OLS slope


@dataclass
class CostOfCapital:
    """Assembled cost of capital with a full audit trail.

    ``method`` names how WACC was reached (e.g. "WACC (CAPM Ke, after-tax Kd)"
    or "cost of equity only (no debt cost)"); ``caveats`` list every fallback
    applied so the discount rate is never presented as more certain than it is.
    """

    ke: float  # cost of equity (CAPM)
    kd_after_tax: float | None  # after-tax cost of debt, None if not computable
    wacc: float  # blended discount rate (== ke when debt cost unavailable)
    beta: float
    risk_free: float
    erp: float
    tax_rate: float
    weight_equity: float | None
    weight_debt: float | None
    method: str
    caveats: list[str] = field(default_factory=list)
    engine_version: str = COST_OF_CAPITAL_VERSION


def effective_tax_rate(
    tax_expense: float | None, pretax_income: float | None
) -> float:
    """Effective tax rate = tax_expense / pretax_income, clamped to [0, 0.5].

    Falls back to the 21% statutory rate when not computable (missing inputs or
    a non-positive pretax base, where the ratio is meaningless). Always returns
    a usable rate — the caller records the fallback as a caveat.
    """
    if tax_expense is None or pretax_income is None or pretax_income <= 0:
        return DEFAULT_TAX_RATE
    rate = tax_expense / pretax_income
    return max(TAX_RATE_MIN, min(TAX_RATE_MAX, rate))


def estimate_beta(
    stock_returns: list[float], market_returns: list[float]
) -> float | None:
    """OLS slope beta = cov(stock, market) / var(market) on aligned returns.

    Needs at least ``MIN_BETA_POINTS`` paired daily returns; returns None on too
    few points or zero market variance (undefined slope). The result is clamped
    to [BETA_MIN, BETA_MAX] so thin-data noise can't drive an absurd Ke.
    """
    n = min(len(stock_returns), len(market_returns))
    if n < MIN_BETA_POINTS:
        return None
    xs = market_returns[:n]
    ys = stock_returns[:n]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    # Epsilon (not just <= 0): summation rounding leaves a tiny positive value
    # for a genuinely constant series, which would explode cov/var_x.
    if var_x <= 1e-15:
        return None
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    beta = cov / var_x
    return max(BETA_MIN, min(BETA_MAX, beta))


def capm_cost_of_equity(risk_free: float, beta: float, erp: float) -> float:
    """CAPM: Ke = risk_free + beta * equity_risk_premium."""
    return risk_free + beta * erp


def after_tax_cost_of_debt(
    interest_expense: float | None, total_debt: float | None, tax_rate: float
) -> float | None:
    """After-tax Kd = (interest_expense / total_debt) * (1 - tax_rate).

    None when total_debt is missing/non-positive (no meaningful pre-tax cost) or
    interest_expense is missing. A non-positive denominator never fabricates a
    rate.
    """
    if interest_expense is None or total_debt is None or total_debt <= 0:
        return None
    pretax_kd = interest_expense / total_debt
    return pretax_kd * (1.0 - tax_rate)


def wacc(
    market_equity: float | None,
    total_debt: float | None,
    ke: float,
    kd_after_tax: float | None,
) -> float | None:
    """Market-value-weighted WACC = We*Ke + Wd*Kd.

    We = E/(E+D), Wd = D/(E+D). When ``kd_after_tax`` is None the debt slice is
    charged at Ke (all-equity-cost fallback) so the blend stays defined rather
    than dropping debt; the caller records that as a caveat. Returns None only
    when E + D <= 0 (no capital base to weight over).
    """
    equity = market_equity or 0.0
    debt = total_debt or 0.0
    total = equity + debt
    if total <= 0:
        return None
    we = equity / total
    wd = debt / total
    kd = kd_after_tax if kd_after_tax is not None else ke
    return we * ke + wd * kd


def compute_cost_of_capital(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    *,
    risk_free: float,
    beta: float | None = None,
    erp: float = 0.05,
) -> CostOfCapital:
    """Assemble Ke, Kd, and WACC from fundamentals + market context.

    Never returns None: missing pieces degrade with caveats and Ke is the floor.
    - Ke: CAPM with ``beta`` (or a 1.0 market-beta fallback, caveated).
    - Kd: interest_expense/total_debt (latest) shielded by the effective tax
      rate (statutory fallback when pretax income isn't computable).
    - WACC: market-cap vs total-debt weights; if either the debt cost or the
      market cap is unavailable, WACC falls back to Ke with a caveat.
    """
    caveats: list[str] = []

    # --- Beta -------------------------------------------------------------
    if beta is None:
        beta = DEFAULT_BETA
        caveats.append(
            f"No beta estimate available; using market beta = {DEFAULT_BETA:.1f}."
        )

    ke = capm_cost_of_equity(risk_free, beta, erp)

    # --- Effective tax rate ----------------------------------------------
    tax_latest = _latest(derived, "tax_expense")
    pretax_latest = _latest(derived, "pretax_income")
    tax_rate = effective_tax_rate(tax_latest, pretax_latest)
    if tax_latest is None or pretax_latest is None or pretax_latest <= 0:
        caveats.append(
            f"Effective tax rate not computable; using statutory {DEFAULT_TAX_RATE:.0%}."
        )

    # --- After-tax cost of debt ------------------------------------------
    interest_latest = _latest(derived, "interest_expense")
    debt_latest = _latest(derived, "total_debt")
    kd_after_tax = after_tax_cost_of_debt(interest_latest, debt_latest, tax_rate)
    if kd_after_tax is None:
        if debt_latest is None or debt_latest <= 0:
            caveats.append("No positive total debt; treating the company as all-equity.")
        else:
            caveats.append("Interest expense unavailable; cost of debt not computed.")

    # --- WACC weights -----------------------------------------------------
    market_cap = market.market_cap if market is not None else None
    weight_equity: float | None = None
    weight_debt: float | None = None
    wacc_value: float | None = None

    if market_cap is not None and market_cap > 0:
        wacc_value = wacc(market_cap, debt_latest, ke, kd_after_tax)
        if wacc_value is not None:
            total = market_cap + (debt_latest or 0.0)
            weight_equity = market_cap / total
            weight_debt = (debt_latest or 0.0) / total
            if kd_after_tax is None and (debt_latest or 0.0) > 0:
                caveats.append("Debt weight charged at cost of equity (no debt cost).")
            method = "WACC (CAPM Ke, after-tax Kd, market-value weights)"
        else:
            method = "cost of equity only (no capital base)"
    else:
        caveats.append("No market cap available; WACC falls back to cost of equity.")
        method = "cost of equity only (no market cap)"

    if wacc_value is None:
        wacc_value = ke  # Ke is the floor when WACC can't be blended.

    return CostOfCapital(
        ke=ke,
        kd_after_tax=kd_after_tax,
        wacc=wacc_value,
        beta=beta,
        risk_free=risk_free,
        erp=erp,
        tax_rate=tax_rate,
        weight_equity=weight_equity,
        weight_debt=weight_debt,
        method=method,
        caveats=caveats,
    )


def _latest(derived: dict[str, DerivedMetric], key: str) -> float | None:
    """Latest value of a derived metric, or None if absent/empty."""
    metric = derived.get(key)
    if metric is None:
        return None
    return metric.latest
