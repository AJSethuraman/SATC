"""Tests for the Monte Carlo DCF sensitivity fan.

The load-bearing invariant: MC is a sampler wrapped around the audited pure
``dcf_value``. With all sds = 0 it must collapse EXACTLY onto the point
estimate — the simulation adds spread, never bias. prob_undervalued must move
monotonically with price, and everything must be reproducible under a seed.
"""

from datetime import date

from stock_helper.features.metrics import DerivedMetric
from stock_helper.valuation.dcf import dcf_value
from stock_helper.valuation.monte_carlo import (
    MonteCarloResult,
    run_monte_carlo_dcf,
    run_monte_carlo_from_dcf,
)

BASE = dict(
    fcf_0=100.0,
    stage1_growth=0.10,
    stage1_years=5,
    discount_rate=0.10,
    terminal_growth=0.03,
    shares=50.0,
)


def _derived_fcf(values):
    pts = [(date(2019 + i, 12, 31), v) for i, v in enumerate(values)]
    return {
        "free_cash_flow": DerivedMetric(
            key="free_cash_flow", label="FCF", unit="USD", formula="test",
            points=pts, input_tags=["Tag"], input_accessions=["acc-1"],
        )
    }


# --- (1) zero sds collapse to the point estimate ----------------------------


def test_zero_sds_collapse_to_point_estimate():
    point = dcf_value(
        BASE["fcf_0"], BASE["stage1_growth"], BASE["stage1_years"],
        BASE["discount_rate"], BASE["terminal_growth"], BASE["shares"],
    ).fair_value_per_share

    mc = run_monte_carlo_dcf(
        **BASE, growth_sd=0.0, discount_sd=0.0, terminal_sd=0.0, fcf_sd=0.0,
    )
    assert mc is not None
    assert abs(mc.median - point) < 1e-6
    # With no spread every quantile is the same point.
    assert abs(mc.p10 - point) < 1e-6
    assert abs(mc.p90 - point) < 1e-6
    assert abs(mc.mean - point) < 1e-6


# --- (2) prob_undervalued is monotone decreasing in price -------------------


def test_prob_undervalued_monotone_in_price():
    mc_mid = run_monte_carlo_dcf(**BASE, price=None)
    assert mc_mid is not None
    median = mc_mid.median

    at_median = run_monte_carlo_dcf(**BASE, price=median)
    far_below = run_monte_carlo_dcf(**BASE, price=median * 0.1)
    far_above = run_monte_carlo_dcf(**BASE, price=median * 10.0)

    # ~0.5 at the median, ~1.0 far below, ~0.0 far above.
    assert abs(at_median.prob_undervalued - 0.5) < 0.1
    assert far_below.prob_undervalued > 0.95
    assert far_above.prob_undervalued < 0.05
    # Strictly monotone decreasing as price rises.
    assert (
        far_below.prob_undervalued
        >= at_median.prob_undervalued
        >= far_above.prob_undervalued
    )


def test_prob_undervalued_none_without_price():
    mc = run_monte_carlo_dcf(**BASE, price=None)
    assert mc is not None
    assert mc.prob_undervalued is None


# --- (3) reproducibility -----------------------------------------------------


def test_same_seed_identical_median():
    a = run_monte_carlo_dcf(**BASE, seed=7)
    b = run_monte_carlo_dcf(**BASE, seed=7)
    assert a.median == b.median
    assert a.p10 == b.p10 and a.p90 == b.p90


def test_different_seed_close_but_not_identical():
    a = run_monte_carlo_dcf(**BASE, seed=7)
    b = run_monte_carlo_dcf(**BASE, seed=8)
    assert a.median != b.median
    # Different seeds should still land in the same neighborhood.
    assert abs(a.median - b.median) / a.median < 0.1


# --- (4) degenerate input -> None -------------------------------------------


def test_non_positive_fcf_returns_none():
    assert run_monte_carlo_dcf(**{**BASE, "fcf_0": 0.0}) is None
    assert run_monte_carlo_dcf(**{**BASE, "fcf_0": -50.0}) is None


def test_non_positive_shares_returns_none():
    assert run_monte_carlo_dcf(**{**BASE, "shares": 0.0}) is None


# --- (5) ordered quantiles with positive spread -----------------------------


def test_quantiles_ordered_with_positive_sds():
    mc = run_monte_carlo_dcf(
        **BASE, growth_sd=0.03, discount_sd=0.01, terminal_sd=0.005,
    )
    assert mc is not None
    assert mc.p10 < mc.median < mc.p90
    assert mc.p10 < mc.p25 < mc.median < mc.p75 < mc.p90
    assert mc.n_sims >= 100
    assert any("INPUT uncertainty only" in c for c in mc.caveats)


# --- from_dcf convenience ----------------------------------------------------


def test_from_dcf_derives_growth_sd_and_runs():
    dcf = dcf_value(
        BASE["fcf_0"], BASE["stage1_growth"], BASE["stage1_years"],
        BASE["discount_rate"], BASE["terminal_growth"], BASE["shares"],
    )
    derived = _derived_fcf([70.0, 82.0, 90.0, 100.0])
    mc = run_monte_carlo_from_dcf(dcf, derived, price=dcf.fair_value_per_share)
    assert isinstance(mc, MonteCarloResult)
    assert mc.p10 < mc.median < mc.p90
    # growth_sd is clamped into the documented band.
    assert 0.02 <= mc.inputs_summary["growth_sd"] <= 0.10
    assert mc.inputs_summary["growth_sd_source"] in ("historical", "floor_fallback")


def test_from_dcf_returns_none_without_base_fcf():
    dcf = dcf_value(
        -10.0, BASE["stage1_growth"], BASE["stage1_years"],
        BASE["discount_rate"], BASE["terminal_growth"], BASE["shares"],
    )
    # A negative-FCF DcfResult still carries base_fcf; simulate should honor the
    # same non-positive guard as the pure core.
    mc = run_monte_carlo_from_dcf(dcf, _derived_fcf([100.0, 110.0, 120.0]))
    assert mc is None
