"""Walk-forward engine + stats + cost model.

These lock the *direction* of the honest-significance machinery: a perfect
predictor scores IC ~ 1 and a positive Sharpe, pure noise scores IC ~ 0 with a
tiny t-stat and a low deflated Sharpe, costs and the embargo only ever subtract,
and the DSR rewards a bigger Sharpe while penalizing more trials.
"""

from datetime import date, timedelta

import numpy as np
import pytest

from stock_helper.backtest import BACKTEST_VERSION
from stock_helper.backtest.costs import apply_costs, transaction_cost_bps
from stock_helper.backtest.engine import RebalanceObs, walk_forward
from stock_helper.backtest.stats import (
    bootstrap_mean_ci,
    deflated_sharpe_ratio,
    quantile_spread,
    spearman_ic,
)

D0 = date(2020, 1, 1)


def _dt(i: int) -> date:
    return D0 + timedelta(days=30 * i)


# ---------------------------------------------------------------- (1) spearman_ic


def test_spearman_monotone_inverse_constant():
    # Perfectly monotone -> +1. Hand-check: ranks are identical, Pearson = 1.
    assert spearman_ic([1.0, 2.0, 3.0, 4.0], [10.0, 20.0, 30.0, 40.0]) == pytest.approx(1.0)
    # Perfectly inverse -> -1.
    assert spearman_ic([1.0, 2.0, 3.0, 4.0], [40.0, 30.0, 20.0, 10.0]) == pytest.approx(-1.0)
    # Constant signal -> zero rank variance -> None.
    assert spearman_ic([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) is None
    # Fewer than 3 paired points -> None.
    assert spearman_ic([1.0, 2.0], [1.0, 2.0]) is None
    # Ties averaged: still a valid, non-degenerate correlation.
    assert spearman_ic([1.0, 1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0]) is not None


# ---------------------------------------------------- (2) perfect-predictor panel


def _perfect_panel(n_dates=6, n_names=10, seed=1):
    """signal == forward_return each date (IC == 1). A small per-date offset
    keeps the top-quantile return positive but varying, so Sharpe is defined."""
    rng = np.random.default_rng(seed)
    base = np.linspace(-0.05, 0.15, n_names)  # mean +0.05, top names clearly positive
    panel = []
    for i in range(n_dates):
        offset = float(rng.uniform(-0.02, 0.02))
        rets = base + offset
        names = [f"N{k}" for k in range(n_names)]
        sig = {nm: float(r) for nm, r in zip(names, rets, strict=True)}
        fwd = dict(sig)  # perfect predictor
        panel.append(RebalanceObs(as_of=_dt(i), signals=sig, forward_returns=fwd))
    return panel


def test_perfect_predictor_scores_high():
    res = walk_forward(_perfect_panel(), horizon_days=20, q=5)
    assert res.mean_ic == pytest.approx(1.0)
    assert res.quantile_spread_mean > 0
    assert res.sharpe is not None and res.sharpe > 0
    assert res.top_quantile_return_mean > 0
    assert res.engine_version == BACKTEST_VERSION
    assert any("SURVIVORSHIP" in c.upper() for c in res.caveats)


# ------------------------------------------------------------- (3) random panel


def test_random_panel_scores_near_zero():
    rng = np.random.default_rng(42)
    n_names = 20
    panel = []
    for i in range(30):
        names = [f"N{k}" for k in range(n_names)]
        sig = {nm: float(rng.normal()) for nm in names}
        fwd = {nm: float(rng.normal()) for nm in names}  # independent of signal
        panel.append(RebalanceObs(as_of=_dt(i), signals=sig, forward_returns=fwd))
    res = walk_forward(panel, horizon_days=20, embargo_dates=0, q=5, n_trials=100)
    assert abs(res.mean_ic) < 0.25
    assert abs(res.ic_t_stat) < 2.5
    # With no real edge and many trials, the deflated Sharpe stays low.
    assert res.deflated_sharpe is not None and res.deflated_sharpe < 0.75


# ---------------------------------------------------------------- (4) embargo


def test_embargo_reduces_n_dates():
    panel = _perfect_panel(n_dates=9)
    none = walk_forward(panel, horizon_days=20, embargo_dates=0)
    heavy = walk_forward(panel, horizon_days=20, embargo_dates=2)
    assert none.n_dates == 9
    assert heavy.n_dates < none.n_dates


# ----------------------------------------------------------------- (5) costs


def test_costs_reduce_return():
    assert transaction_cost_bps(1.0, half_spread_bps=5.0, impact_bps=5.0) == pytest.approx(10.0)
    assert transaction_cost_bps(0.5) == pytest.approx(5.0)
    # Net is strictly below gross when any trading happens.
    assert apply_costs(0.02, 1.0) < 0.02
    assert apply_costs(0.02, 0.0) == pytest.approx(0.02)  # no turnover, no cost
    # At the engine level the first rebalance always trades, so net < gross.
    res = walk_forward(_perfect_panel(), horizon_days=20, half_spread_bps=20.0, impact_bps=20.0)
    assert res.net_return_mean < res.top_quantile_return_mean


# --------------------------------------------------------------- (6) bootstrap


def test_bootstrap_brackets_mean():
    values = [0.01, 0.03, -0.02, 0.04, 0.00, 0.05, -0.01, 0.02]
    lo, hi, mean = bootstrap_mean_ci(values, n_boot=3000, seed=7)
    assert mean == pytest.approx(float(np.mean(values)))
    assert lo <= mean <= hi
    assert bootstrap_mean_ci([]) == (None, None, None)


# --------------------------------------------------------------------- (7) DSR


def test_dsr_directions():
    # Higher observed Sharpe -> higher DSR (more evidence of a real edge).
    low = deflated_sharpe_ratio(0.2, n_trials=10, n_obs=120)
    high = deflated_sharpe_ratio(0.5, n_trials=10, n_obs=120)
    assert 0.0 <= low <= 1.0 and 0.0 <= high <= 1.0
    assert high > low
    # More trials -> lower DSR (multiple-testing penalty raises the bar).
    few = deflated_sharpe_ratio(0.5, n_trials=1, n_obs=120)
    many = deflated_sharpe_ratio(0.5, n_trials=200, n_obs=120)
    assert few > many
    # Hand-check the single-trial reduction to the plain probabilistic Sharpe:
    # SR0 = 0, stat = 0.5 * sqrt(119) ~= 5.454, Phi(5.454) ~= 1.0.
    assert few == pytest.approx(0.99999997, abs=1e-6)


# ------------------------------------------------------- quantile_spread guard


def test_quantile_spread_needs_enough_points():
    assert quantile_spread([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], q=5) is None  # < q*2
    sig = [float(x) for x in range(10)]
    ret = [float(x) for x in range(10)]
    assert quantile_spread(sig, ret, q=5) > 0  # monotone -> top beats bottom
