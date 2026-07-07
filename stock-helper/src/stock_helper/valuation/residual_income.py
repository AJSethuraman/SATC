"""Residual-income (Edwards-Bell-Ohlson) equity valuation — pure calculation core.

Residual income anchors value on **book value plus the present value of
economic profit earned on that book**, so it works precisely where a
free-cash-flow DCF is weakest: firms with no / negative / lumpy FCF, and
balance-sheet businesses (banks, insurers) where book value is economically
meaningful and the DCF machinery is invalid.

The model (multi-stage EBO):

    V0 = B0 + Σ_{t=1..T} PV(RI_t) + PV(terminal)

with book value compounding ``B_t = B_{t-1} * (1 + g)`` and residual income
``RI_t = (ROE - Ke) * B_{t-1}`` — the spread of return on equity over the cost
of equity, earned on the prior period's book. Each RI_t is discounted at Ke.
The terminal value capitalises continuing residual income beyond the explicit
horizon with a persistence parameter ω in [0, 1] (Ohlson's information
dynamics): ``TV_T = RI_{T+1} / (1 + Ke - ω)``, guarded so ``(1 + Ke - ω) > 0``.

Honesty rules (shared across the engine):
- When ROE ≤ Ke the residual income is zero or negative, so value lands at or
  **below** book. That is the correct economic reading — a business that does
  not out-earn its cost of equity is worth no more than its book — and it is
  reported straight, never floored up to book.
- A non-positive book value, a non-positive cost of equity, a broken terminal
  denominator, or a non-positive share count returns a non-OK status with a
  reason — never a fabricated number.

Research aid, NOT investment advice. Every value here is a scenario estimate
that falls out of explicit, editable assumptions (ROE, Ke, g, persistence),
carried with the source filing accessions so any figure is auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from stock_helper.industry.sic_buckets import is_financial
from stock_helper.normalization.facts import MetricSeries
from stock_helper.valuation import (
    OK,
    UNAVAILABLE,
    VALUATION_VERSION,
)

if TYPE_CHECKING:  # avoid importing the heavy (pandas/sqlmodel) context module
    from stock_helper.features.context import MarketContext
    from stock_helper.features.metrics import DerivedMetric

# A hard cap on the sustainable book-growth assumption, applied in the run_
# wrapper. Kept strictly below Ke so terminal economics stay conservative and
# an aggressive retention/ROE product cannot manufacture runaway book growth.
_MAX_GROWTH_HEADROOM = 0.0  # growth capped at cost_of_equity + this headroom


@dataclass
class ResidualIncomeResult:
    """One residual-income valuation with full provenance.

    ``fair_value_per_share`` is None when the share count is non-positive (the
    equity value still stands). When ``status != OK`` the monetary fields are
    None and ``caveats``/``formula`` carry the reason. ``ri_projection`` is the
    per-year ``(year, residual_income, present_value)`` schedule."""

    status: str
    fair_value_per_share: float | None
    equity_value: float | None
    book_value_0: float | None
    pv_residual_incomes: float | None
    pv_terminal: float | None
    ri_projection: list[tuple[int, float, float]] = field(default_factory=list)
    roe: float | None = None
    cost_of_equity: float | None = None
    growth: float | None = None
    persistence: float | None = None
    shares: float | None = None
    formula: str = ""
    caveats: list[str] = field(default_factory=list)
    input_accessions: list[str] = field(default_factory=list)
    engine_version: str = VALUATION_VERSION


def _unavailable(reason: str, **carried) -> ResidualIncomeResult:
    """A non-OK result that reports *why* rather than a bogus number."""
    return ResidualIncomeResult(
        status=UNAVAILABLE,
        fair_value_per_share=None,
        equity_value=None,
        book_value_0=carried.get("book_value_0"),
        pv_residual_incomes=None,
        pv_terminal=None,
        roe=carried.get("roe"),
        cost_of_equity=carried.get("cost_of_equity"),
        growth=carried.get("growth"),
        persistence=carried.get("persistence"),
        shares=carried.get("shares"),
        formula="V0 = B0 + Σ PV((ROE-Ke)*B_{t-1}) + PV(terminal)",
        caveats=[reason],
        input_accessions=carried.get("input_accessions", []),
    )


def residual_income_value(
    book_value_0: float,
    roe: float,
    cost_of_equity: float,
    growth: float,
    years: int = 5,
    persistence: float = 0.6,
    shares: float | None = None,
) -> ResidualIncomeResult:
    """Pure numeric core of the multi-stage residual-income (EBO) model.

    V0 = B0 + Σ_{t=1..T} PV(RI_t) + PV(terminal), where B_t = B_{t-1}*(1+g),
    RI_t = (ROE - Ke) * B_{t-1}, and each RI_t is discounted at Ke. The terminal
    capitalises continuing residual income with persistence ω:
    TV_T = RI_{T+1} / (1 + Ke - ω), discounted T periods to today.

    Returns a non-OK ``ResidualIncomeResult`` (with the reason in ``caveats``)
    when:
    - ``book_value_0 <= 0`` — the model is anchored on positive book; a negative
      book breaks both the ROE meaning and the compounding base.
    - ``cost_of_equity <= 0`` — no sane discount rate.
    - ``years < 1``.
    - ``(1 + Ke - ω) <= 0`` — the terminal denominator is non-positive, so the
      continuing-value geometric series does not converge.

    ROE ≤ Ke (value at or below book) is a valid, reported outcome — NOT an
    error. ``fair_value_per_share`` is None when ``shares`` is None or ≤ 0.
    """
    carried = {
        "book_value_0": book_value_0,
        "roe": roe,
        "cost_of_equity": cost_of_equity,
        "growth": growth,
        "persistence": persistence,
        "shares": shares,
    }
    if book_value_0 <= 0:
        return _unavailable(
            "Book value (B0) is non-positive; residual income needs a positive "
            "equity base to compound and to make ROE meaningful.",
            **carried,
        )
    if cost_of_equity <= 0:
        return _unavailable(
            "Cost of equity (Ke) is non-positive; no valid discount rate.",
            **carried,
        )
    if years < 1:
        return _unavailable("years must be >= 1 for an explicit RI horizon.", **carried)

    terminal_denominator = 1.0 + cost_of_equity - persistence
    if terminal_denominator <= 0:
        return _unavailable(
            f"Terminal denominator (1 + Ke - ω) = {terminal_denominator:.4f} is "
            "non-positive; continuing residual income does not converge. Lower "
            "the persistence ω or raise Ke.",
            **carried,
        )

    spread = roe - cost_of_equity
    projection: list[tuple[int, float, float]] = []
    pv_residual_incomes = 0.0
    book_prev = book_value_0
    for t in range(1, years + 1):
        residual_income = spread * book_prev
        present_value = residual_income / (1.0 + cost_of_equity) ** t
        projection.append((t, residual_income, present_value))
        pv_residual_incomes += present_value
        book_prev = book_prev * (1.0 + growth)  # book at end of year t

    book_terminal = book_prev  # B_T after the loop
    ri_next = spread * book_terminal  # RI_{T+1} = (ROE-Ke) * B_T
    terminal_value = ri_next / terminal_denominator
    pv_terminal = terminal_value / (1.0 + cost_of_equity) ** years

    equity_value = book_value_0 + pv_residual_incomes + pv_terminal

    fair_value_per_share = None
    if shares is not None and shares > 0:
        fair_value_per_share = equity_value / shares

    caveats = [
        "Residual-income (Edwards-Bell-Ohlson) scenario estimate, not a price "
        "target or advice.",
        f"Assumptions: ROE={roe:.4f}, Ke={cost_of_equity:.4f}, g={growth:.4f}, "
        f"persistence ω={persistence:.2f}, horizon={years}y.",
    ]
    if spread <= 0:
        caveats.append(
            "ROE does not exceed the cost of equity, so residual income is "
            "non-positive and value lands at or below book value. This is the "
            "correct economic reading and is reported unfloored."
        )
    if shares is None or shares <= 0:
        caveats.append(
            "Per-share value unavailable: share count is missing or non-positive."
        )

    return ResidualIncomeResult(
        status=OK,
        fair_value_per_share=fair_value_per_share,
        equity_value=equity_value,
        book_value_0=book_value_0,
        pv_residual_incomes=pv_residual_incomes,
        pv_terminal=pv_terminal,
        ri_projection=projection,
        roe=roe,
        cost_of_equity=cost_of_equity,
        growth=growth,
        persistence=persistence,
        shares=shares,
        formula=(
            "V0 = B0 + Σ_{t=1..T} (ROE-Ke)*B_{t-1}/(1+Ke)^t + "
            "[(ROE-Ke)*B_T/(1+Ke-ω)]/(1+Ke)^T ; B_t = B_{t-1}*(1+g)"
        ),
        caveats=caveats,
    )


# --------------------------------------------------------------------------- #
# Series-driven wrapper (assembles inputs, then calls the pure core)
# --------------------------------------------------------------------------- #


def _sustainable_growth(
    roe: float,
    derived: dict[str, DerivedMetric],
    cost_of_equity: float,
) -> tuple[float, str]:
    """Capped sustainable book-growth g = ROE * (1 - payout).

    Payout is dividends-per-share / diluted EPS when both are available and EPS
    is positive (clamped to [0, 1]); otherwise full retention (payout = 0) is
    assumed. The result is capped at the cost of equity so a high ROE × full
    retention cannot imply book growth above the discount rate. Returns
    ``(growth, note)`` where the note documents the payout basis used."""
    dps = derived.get("dividends_per_share")
    eps = derived.get("eps_diluted")
    payout = 0.0
    if (
        dps is not None
        and eps is not None
        and dps.latest is not None
        and eps.latest is not None
        and eps.latest > 0
    ):
        payout = max(0.0, min(1.0, dps.latest / eps.latest))
        basis = f"payout = DPS/EPS = {payout:.3f}"
    else:
        basis = "payout assumed 0 (dividends-per-share or EPS unavailable)"

    raw = roe * (1.0 - payout)
    cap = cost_of_equity + _MAX_GROWTH_HEADROOM
    growth = min(raw, cap)
    note = f"g = ROE*(1-payout) = {raw:.4f} ({basis})"
    if growth < raw:
        note += f", capped at Ke ({cap:.4f})"
    return growth, note


def _roe_from_series(series: dict[str, MetricSeries]) -> float | None:
    """Fallback ROE = net_income.latest / average(equity[t-1], equity[t]).

    Uses the same 2-year-average equity convention as features/metrics.roe.
    None if net income or two equity points are unavailable, or average equity
    is non-positive."""
    ni = series.get("net_income")
    eq = series.get("equity")
    if ni is None or eq is None or len(eq.points) < 2:
        return None
    eq_vals = eq.values()
    avg_equity = (eq_vals[-2][1] + eq_vals[-1][1]) / 2.0
    if avg_equity <= 0:
        return None
    return ni.latest.value / avg_equity


def run_residual_income(
    series: dict[str, MetricSeries],
    derived: dict[str, DerivedMetric],
    market: MarketContext | None,
    cost_of_equity: float,
    *,
    bucket: str | None = None,
) -> ResidualIncomeResult:
    """Assemble residual-income inputs from canonical series and value the equity.

    Book value B0 comes from ``equity.latest`` (the point-in-time book). ROE
    prefers the derived ``roe`` metric (net_income / 2-year-average equity),
    falling back to a latest-point computation. Growth is a capped sustainable
    growth ``ROE * (1 - payout)``. Shares come from ``market.shares`` when a
    price context is available, else the latest ``shares_outstanding``.

    Applicable to **all** industry buckets, banks included — that is the whole
    point of a book-anchored model. Returns a non-OK result (with the reason)
    when equity, ROE, or a positive share count cannot be obtained.
    """
    eq_series = series.get("equity")
    if eq_series is None or not eq_series.points:
        return _unavailable("Stockholders' equity (book value) unavailable.",
                            cost_of_equity=cost_of_equity)
    book_value_0 = eq_series.latest.value

    roe_metric = derived.get("roe")
    roe = roe_metric.latest if roe_metric is not None else None
    if roe is None:
        roe = _roe_from_series(series)
    if roe is None:
        return _unavailable(
            "ROE unavailable (need net income and equity to compute it).",
            book_value_0=book_value_0,
            cost_of_equity=cost_of_equity,
        )

    growth, growth_note = _sustainable_growth(roe, derived, cost_of_equity)

    shares: float | None = None
    if market is not None and getattr(market, "shares", None):
        shares = market.shares
    else:
        so = series.get("shares_outstanding")
        if so is not None and so.points and so.latest.value > 0:
            shares = so.latest.value

    # Provenance: every series that fed an input.
    accessions: set[str] = set(eq_series.accessions())
    for key in ("net_income", "dividends_per_share", "eps_diluted",
                "shares_outstanding"):
        s = series.get(key)
        if s is not None:
            accessions.update(s.accessions())

    result = residual_income_value(
        book_value_0=book_value_0,
        roe=roe,
        cost_of_equity=cost_of_equity,
        growth=growth,
        years=5,
        persistence=0.6,
        shares=shares,
    )
    result.input_accessions = sorted(accessions)
    result.caveats.append(growth_note)
    if bucket is not None and is_financial(bucket):
        result.caveats.append(
            "Financial bucket: book value is economically meaningful here, so a "
            "book-anchored residual-income read is especially appropriate "
            "(FCF-DCF is not valid for balance-sheet businesses)."
        )
    return result
