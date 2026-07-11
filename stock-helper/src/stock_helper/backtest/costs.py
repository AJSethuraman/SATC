"""Trading friction model (pure).

A backtest that ignores costs flatters every high-turnover signal. The model is
deliberately crude and linear: each unit of turnover pays a half-spread (the cost
of crossing the bid/ask) plus a market-impact charge (pushing the price while
filling). Both are in basis points; defaults are placeholder retail-ish figures,
not calibrated venue data. Turnover is the fraction of the portfolio traded at a
rebalance (1.0 = fully replaced).
"""


def transaction_cost_bps(
    turnover: float, *, half_spread_bps: float = 5.0, impact_bps: float = 5.0
) -> float:
    """Round-trip-agnostic cost of a rebalance, in basis points.

    Cost scales linearly with turnover: (half_spread + impact) * turnover.
    """
    return (half_spread_bps + impact_bps) * float(turnover)


def apply_costs(
    gross_return: float,
    turnover: float,
    *,
    half_spread_bps: float = 5.0,
    impact_bps: float = 5.0,
) -> float:
    """Subtract the turnover-scaled transaction cost from a gross return.

    Cost in bps is converted to a return fraction (bps / 10_000) before it is
    deducted, so the result is directly comparable to ``gross_return``.
    """
    cost_bps = transaction_cost_bps(
        turnover, half_spread_bps=half_spread_bps, impact_bps=impact_bps
    )
    return float(gross_return) - cost_bps / 10_000.0
