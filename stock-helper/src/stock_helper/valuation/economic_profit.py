"""ROIC − WACC economic-profit spread — a value-creation read (pure core).

The single number that says whether a business earns more on its invested
capital than that capital costs. Damodaran's core theorem: **growth only creates
value when ROIC > WACC**; growth funded at a return below the cost of capital
destroys value no matter how fast the top line rises. So the sign of the spread
(ROIC − WACC), not the growth rate, is what separates value-creating from
value-destroying expansion.

This is a READ on economic profitability, NOT a valuation, a target, or advice.
It takes ROIC and WACC as already-computed inputs (both dimensionless rates) and
reports their spread, an interpretation, and — when a history is supplied — how
persistently the spread has been positive. Nothing here fetches or guesses; a
missing input yields ``None`` rather than a fabricated spread.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def economic_profit_spread(roic: float | None, wacc: float | None) -> float | None:
    """The economic-profit spread ROIC − WACC, or None if either input is None.

    Positive => the firm out-earns its cost of capital (value-creating);
    negative => it earns less than capital costs (value-destroying); ~zero =>
    it merely covers its cost of capital. Both inputs are decimal rates (e.g.
    0.18 for 18%)."""
    if roic is None or wacc is None:
        return None
    return roic - wacc


@dataclass
class EconomicProfitResult:
    """The economic-profit read for one company.

    ``creates_value`` is True iff ``spread > 0`` (strictly out-earning the cost
    of capital). ``spread_history`` holds any supplied historical spreads and
    ``persistence_note`` summarises how consistently they were positive — a
    single positive year is far weaker evidence than a persistent one. This is
    an economic-profitability read, not a price target."""

    spread: float | None
    roic: float | None
    wacc: float | None
    creates_value: bool
    spread_history: list[float] = field(default_factory=list)
    persistence_note: str = ""
    caveats: list[str] = field(default_factory=list)


def compute_economic_profit(
    roic: float | None,
    wacc: float | None,
    roic_history: list[float] | None = None,
) -> EconomicProfitResult:
    """Assemble the economic-profit read from ROIC and WACC.

    ``spread = ROIC − WACC``; ``creates_value`` is True iff the spread is
    strictly positive (Damodaran: only ROIC > WACC turns growth into value).
    When ``roic_history`` is given, each historical ROIC is compared against the
    *current* WACC to form a spread history, and ``persistence_note`` reports how
    many of those years the spread was positive — persistence, not a single
    year, is what makes the read credible.

    A missing ROIC or WACC yields ``spread = None`` and ``creates_value = False``
    (we never call a company value-creating on absent data) with the reason in
    ``caveats``."""
    spread = economic_profit_spread(roic, wacc)
    creates_value = spread is not None and spread > 0

    caveats = [
        "Economic-profit READ (ROIC vs WACC), not a valuation, target, or advice.",
        "Damodaran: growth creates value only when ROIC > WACC; below it, growth "
        "destroys value.",
    ]

    if spread is None:
        missing = "ROIC" if roic is None else "WACC"
        caveats.append(f"Spread unavailable: {missing} is missing.")

    spread_history: list[float] = []
    persistence_note = ""
    if roic_history and wacc is not None:
        spread_history = [r - wacc for r in roic_history]
        n = len(spread_history)
        positive = sum(1 for s in spread_history if s > 0)
        persistence_note = (
            f"Spread positive in {positive} of the last {n} year(s) "
            f"(ROIC history vs current WACC={wacc:.4f}); "
            + (
                "persistently value-creating."
                if positive == n
                else "value creation is not consistent — treat with caution."
                if positive > 0
                else "no year out-earned the cost of capital."
            )
        )
    elif roic_history and wacc is None:
        persistence_note = "History supplied but WACC is missing; no spread history."

    if spread is not None:
        if creates_value:
            interp = (
                f"ROIC {roic:.4f} exceeds WACC {wacc:.4f} by {spread:.4f}: the "
                "firm earns more on invested capital than that capital costs, so "
                "incremental growth is value-creating."
            )
        elif spread < 0:
            interp = (
                f"ROIC {roic:.4f} is below WACC {wacc:.4f} by {-spread:.4f}: the "
                "firm earns less than its cost of capital, so growth destroys "
                "value until the spread turns positive."
            )
        else:
            interp = (
                f"ROIC {roic:.4f} roughly equals WACC {wacc:.4f}: the firm merely "
                "covers its cost of capital; growth is value-neutral."
            )
        caveats.append(interp)

    return EconomicProfitResult(
        spread=spread,
        roic=roic,
        wacc=wacc,
        creates_value=creates_value,
        spread_history=spread_history,
        persistence_note=persistence_note,
        caveats=caveats,
    )
