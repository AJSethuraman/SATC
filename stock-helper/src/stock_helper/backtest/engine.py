"""Walk-forward backtest engine (pure over a provided panel; no DB/network).

Given a panel of rebalance observations (a cross-section of signal values and the
returns that followed, at each date), this measures whether the signal sorted
future returns out-of-sample. It is *walk-forward* only in that dates are consumed
in time order with an embargo so overlapping holding windows do not leak; it does
no fitting, so there is nothing to overfit here beyond the choice of signal.

Every result is degenerate-safe: a field that cannot be computed from the panel
is None rather than a fabricated number, and every result carries the standing
survivorship caveat.
"""

from dataclasses import dataclass, field
from datetime import date

import numpy as np

from stock_helper.backtest import BACKTEST_VERSION
from stock_helper.backtest.costs import apply_costs
from stock_helper.backtest.stats import (
    bootstrap_mean_ci,
    deflated_sharpe_ratio,
    ic_summary,
    quantile_spread,
    spearman_ic,
)

SURVIVORSHIP_CAVEAT = (
    "Educational walk-forward on NON-CANONICAL, SURVIVORSHIP-BIASED free prices — "
    "not a performance claim; delisted names are absent, which inflates results "
    "and hides distress."
)


@dataclass
class RebalanceObs:
    """One rebalance date: the signal cross-section and the realized forward
    returns keyed by the same names (e.g. tickers)."""

    as_of: date
    signals: dict[str, float]
    forward_returns: dict[str, float]


Panel = list[RebalanceObs]


@dataclass
class BacktestResult:
    mean_ic: float | None
    ic_t_stat: float | None
    ic_ci: tuple[float | None, float | None, float | None]
    quantile_spread_mean: float | None
    top_quantile_return_mean: float | None
    sharpe: float | None
    sharpe_annualized: float | None
    max_drawdown: float | None
    turnover_mean: float | None
    net_return_mean: float | None
    n_dates: int
    n_names_avg: float | None
    deflated_sharpe: float | None
    caveats: list = field(default_factory=list)
    engine_version: str = BACKTEST_VERSION


def _aligned(obs: RebalanceObs) -> tuple[list[str], list[float], list[float]]:
    """Names present with real numbers on BOTH the signal and the return side."""
    names: list[str] = []
    sig: list[float] = []
    ret: list[float] = []
    for name, s in obs.signals.items():
        r = obs.forward_returns.get(name)
        if s is None or r is None:
            continue
        try:
            fs, fr = float(s), float(r)
        except (TypeError, ValueError):
            continue
        if np.isnan(fs) or np.isnan(fr):
            continue
        names.append(name)
        sig.append(fs)
        ret.append(fr)
    return names, sig, ret


def _top_bucket(
    names: list[str], sig: list[float], ret: list[float], q: int
) -> tuple[set[str], float] | None:
    """Top signal-quantile: its member names and their mean forward return.

    Needs at least q aligned names so every bucket holds at least one name.
    """
    if len(names) < q:
        return None
    order = np.argsort(np.asarray(sig), kind="stable")
    idx_buckets = np.array_split(order, q)
    top_idx = idx_buckets[-1]
    top_names = {names[i] for i in top_idx}
    top_mean = float(np.mean([ret[i] for i in top_idx]))
    return top_names, top_mean


def _skew_kurtosis(xs: np.ndarray) -> tuple[float, float]:
    """Sample skewness and (non-excess) kurtosis; kurtosis=3 for a normal."""
    n = len(xs)
    mean = xs.mean()
    sd = xs.std(ddof=0)
    if sd == 0 or n < 2:
        return 0.0, 3.0
    z = (xs - mean) / sd
    return float(np.mean(z**3)), float(np.mean(z**4))


def walk_forward(
    panel: Panel,
    *,
    horizon_days: int,
    embargo_dates: int = 1,
    q: int = 5,
    n_trials: int = 1,
    half_spread_bps: float = 5.0,
    impact_bps: float = 5.0,
    periods_per_year: float | None = None,
) -> BacktestResult:
    """Evaluate a signal panel out-of-sample, date by date.

    Dates are consumed in time order; a date is skipped when it lands within
    ``embargo_dates`` positions of the previously-USED date, so returns measured
    over overlapping holding windows do not double-count. For each used date we
    take the Spearman IC and the top-minus-bottom quantile spread, and we hold the
    top quantile as a portfolio, netting a turnover-scaled cost each rebalance
    (turnover approximated from name overlap with the prior top quantile; the
    first rebalance is a full build, turnover=1.0). Sharpe is the mean/std of that
    net series, annualized by ``periods_per_year`` (inferred as 252/horizon_days
    when None), and deflated for ``n_trials`` via the DSR multiple-testing penalty.
    """
    ordered = sorted(panel, key=lambda o: o.as_of)

    used: list[RebalanceObs] = []
    last_used = None
    for i, obs in enumerate(ordered):
        if last_used is None or (i - last_used) > embargo_dates:
            used.append(obs)
            last_used = i

    ics: list[float] = []
    spreads: list[float] = []
    gross_series: list[float] = []
    net_series: list[float] = []
    turnovers: list[float] = []
    name_counts: list[int] = []
    prev_top: set[str] | None = None

    for obs in used:
        names, sig, ret = _aligned(obs)
        name_counts.append(len(names))

        ic = spearman_ic(sig, ret)
        if ic is not None:
            ics.append(ic)

        spread = quantile_spread(sig, ret, q=q)
        if spread is not None:
            spreads.append(spread)

        bucket = _top_bucket(names, sig, ret, q)
        if bucket is not None:
            top_names, top_mean = bucket
            if prev_top is None or not top_names:
                turnover = 1.0
            else:
                turnover = len(top_names - prev_top) / len(top_names)
            net = apply_costs(
                top_mean, turnover, half_spread_bps=half_spread_bps, impact_bps=impact_bps
            )
            gross_series.append(top_mean)
            net_series.append(net)
            turnovers.append(turnover)
            prev_top = top_names

    caveats = [SURVIVORSHIP_CAVEAT]
    if not used:
        caveats.append("Empty panel after embargo — no dates to evaluate.")

    ic_stats = ic_summary(ics)
    ic_ci = bootstrap_mean_ci(ics)

    sharpe: float | None = None
    sharpe_ann: float | None = None
    max_dd: float | None = None
    dsr: float | None = None
    if len(net_series) >= 2:
        arr = np.asarray(net_series, dtype=float)
        sd = float(arr.std(ddof=1))
        mean = float(arr.mean())
        if sd > 0:
            sharpe = mean / sd
            ppy = periods_per_year
            if ppy is None and horizon_days and horizon_days > 0:
                ppy = 252.0 / horizon_days
            if ppy is not None and ppy > 0:
                sharpe_ann = sharpe * np.sqrt(ppy)
            skew, kurt = _skew_kurtosis(arr)
            dsr = deflated_sharpe_ratio(
                sharpe, n_trials=n_trials, n_obs=len(net_series), skew=skew, kurtosis=kurt
            )
        # Compounded equity curve and its worst peak-to-trough decline (<= 0).
        equity = np.cumprod(1.0 + arr)
        peak = np.maximum.accumulate(equity)
        max_dd = float((equity / peak - 1.0).min())

    return BacktestResult(
        mean_ic=ic_stats["mean_ic"],
        ic_t_stat=ic_stats["ic_t_stat"],
        ic_ci=ic_ci,
        quantile_spread_mean=(float(np.mean(spreads)) if spreads else None),
        top_quantile_return_mean=(float(np.mean(gross_series)) if gross_series else None),
        sharpe=sharpe,
        sharpe_annualized=sharpe_ann,
        max_drawdown=max_dd,
        turnover_mean=(float(np.mean(turnovers)) if turnovers else None),
        net_return_mean=(float(np.mean(net_series)) if net_series else None),
        n_dates=len(used),
        n_names_avg=(float(np.mean(name_counts)) if name_counts else None),
        deflated_sharpe=dsr,
        caveats=caveats,
        engine_version=BACKTEST_VERSION,
    )
