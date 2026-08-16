"""Tests for the DCF / intrinsic-value engine.

Golden numbers are hand-computed and asserted exactly (money-critical). The
central invariant under test is bug F1: for LEVERED flows the present value IS
equity value and net debt is never subtracted.
"""

from datetime import date

import pytest

from conftest import mk_series
from stock_helper.features.metrics import DerivedMetric
from stock_helper.industry.sic_buckets import BANKING, TECHNOLOGY
from stock_helper.valuation import (
    NEGATIVE_FCF,
    NOT_APPLICABLE,
    OK,
    UNAVAILABLE,
)
from stock_helper.valuation.dcf import (
    dcf_value,
    ddm_gordon,
    justified_pb,
    reverse_dcf_implied_growth,
    run_dcf,
    sensitivity,
)
from stock_helper.valuation.types import LEVERED, UNLEVERED, Assumptions


class _Market:
    """Minimal MarketContext stand-in (only the fields run_dcf reads)."""

    def __init__(self, price=None, shares=None, market_cap=None):
        self.price = price
        self.shares = shares
        self.market_cap = market_cap


def _derived(key, values, tags=("Tag",)):
    return DerivedMetric(
        key=key, label=key, unit="USD", formula="test", points=list(values),
        input_tags=list(tags), input_accessions=["acc-1"],
    )


# --- pure core: golden values -------------------------------------------------


def test_dcf_two_stage_levered_golden():
    r = dcf_value(
        fcf_0=100.0, stage1_growth=0.10, stage1_years=5, discount_rate=0.10,
        terminal_growth=0.03, shares=50.0, fade_to_terminal=False,
        fcf_basis=LEVERED,
    )
    assert r.status == OK
    # r == g each year, so every discounted FCF is exactly 100 -> 500 total.
    assert r.pv_explicit == pytest.approx(500.0)
    assert r.terminal_value == pytest.approx(2369.7504285714, rel=1e-9)
    assert r.pv_terminal == pytest.approx(1471.4285714286, rel=1e-9)
    assert r.equity_value == pytest.approx(1971.4285714286, rel=1e-9)
    assert r.fair_value_per_share == pytest.approx(39.4285714286, rel=1e-9)
    assert r.terminal_weight == pytest.approx(1471.4285714286 / 1971.4285714286)


def test_levered_does_not_subtract_net_debt():
    """Bug F1: net debt must NOT reduce equity value for a levered flow."""
    no_debt = dcf_value(100.0, 0.10, 5, 0.10, 0.03, 50.0, net_debt=0.0)
    with_debt = dcf_value(100.0, 0.10, 5, 0.10, 0.03, 50.0, net_debt=500.0)
    assert with_debt.equity_value == pytest.approx(no_debt.equity_value)
    assert with_debt.equity_value == pytest.approx(1971.4285714286, rel=1e-9)
    # Enterprise value is informational for a levered flow: equity + net_debt.
    assert with_debt.enterprise_value == pytest.approx(1971.4285714286 + 500.0)


def test_unlevered_subtracts_net_debt():
    """UNLEVERED (FCFF) is the ONLY basis that subtracts net debt."""
    r = dcf_value(100.0, 0.10, 5, 0.10, 0.03, 50.0, net_debt=500.0,
                  fcf_basis=UNLEVERED)
    assert r.enterprise_value == pytest.approx(1971.4285714286, rel=1e-9)
    assert r.equity_value == pytest.approx(1971.4285714286 - 500.0, rel=1e-9)


@pytest.mark.parametrize("years", [1, 5, 20])
def test_dcf_flat_perpetuity_invariant(years):
    """With g=0 and terminal_growth=0, value = FCF/r regardless of horizon:
    the explicit window and the terminal value must trade off to a constant."""
    r = dcf_value(
        fcf_0=80.0, stage1_growth=0.0, stage1_years=years, discount_rate=0.08,
        terminal_growth=0.0, shares=10.0,
    )
    assert r.equity_value == pytest.approx(1000.0, rel=1e-9)


# --- reverse DCF --------------------------------------------------------------


@pytest.mark.parametrize("g", [0.02, 0.06, 0.10])
def test_reverse_dcf_round_trip(g):
    target = dcf_value(100.0, g, 5, 0.10, 0.03, 50.0).equity_value
    solved = reverse_dcf_implied_growth(target, 100.0, 5, 0.10, 0.03, 50.0)
    assert solved is not None
    assert solved == pytest.approx(g, abs=1e-4)


def test_reverse_dcf_out_of_bracket_returns_none():
    # A target far above the value at the top of the growth bracket (g=1.0)
    # cannot be reproduced by any growth in range -> None, never a guess.
    ceiling = dcf_value(100.0, 1.0, 5, 0.10, 0.03, 50.0).equity_value
    assert reverse_dcf_implied_growth(
        ceiling * 10.0, 100.0, 5, 0.10, 0.03, 50.0
    ) is None
    # And a target below the value at the bottom (g=-0.5).
    floor = dcf_value(100.0, -0.5, 5, 0.10, 0.03, 50.0).equity_value
    assert reverse_dcf_implied_growth(
        floor - 1e6, 100.0, 5, 0.10, 0.03, 50.0
    ) is None


# --- guards: never crash, never fabricate -------------------------------------


@pytest.mark.parametrize("g_term", [0.10, 0.12])
def test_terminal_growth_ge_discount_rate_guarded(g_term):
    r = dcf_value(100.0, 0.05, 5, 0.10, g_term, 50.0)  # r <= g_term
    assert r.status == UNAVAILABLE
    assert r.equity_value is None
    assert r.fair_value_per_share is None
    assert r.caveats  # reason recorded


@pytest.mark.parametrize("shares", [0.0, -10.0])
def test_zero_shares(shares):
    r = dcf_value(100.0, 0.10, 5, 0.10, 0.03, shares)
    assert r.fair_value_per_share is None
    assert r.equity_value is not None  # equity value still computed
    assert r.status == OK


# --- assembly -----------------------------------------------------------------


def test_run_dcf_not_applicable_for_bank():
    r = run_dcf(series={}, derived={}, bucket=BANKING, market=None)
    assert r.status == NOT_APPLICABLE


def test_negative_base_fcf():
    fcf = _derived("free_cash_flow", [
        (date(2022, 12, 31), -10.0),
        (date(2023, 12, 31), -20.0),
        (date(2024, 12, 31), -15.0),
    ])
    r = run_dcf(series={}, derived={"free_cash_flow": fcf}, bucket=TECHNOLOGY,
                market=None)
    assert r.status == NEGATIVE_FCF
    assert r.fair_value_per_share is None


def test_run_dcf_missing_fcf_unavailable():
    r = run_dcf(series={}, derived={}, bucket=TECHNOLOGY, market=None)
    assert r.status == UNAVAILABLE


def test_run_dcf_happy_path_levered_ignores_net_debt():
    """Full assembly: base FCF = median(last 3), explicit growth, and net debt
    recorded but NOT subtracted for the default LEVERED basis."""
    fcf = _derived("free_cash_flow", [
        (date(2022, 12, 31), 90.0),
        (date(2023, 12, 31), 100.0),
        (date(2024, 12, 31), 110.0),
    ])
    debt = _derived("total_debt", [(date(2024, 12, 31), 400.0)])
    cash = _derived("cash", [(date(2024, 12, 31), 100.0)])
    series = {"shares_outstanding": mk_series(
        "shares_outstanding", [(date(2024, 12, 31), 50.0)], unit="shares")}
    derived = {"free_cash_flow": fcf, "total_debt": debt, "cash": cash}
    a = Assumptions(discount_rate=0.10, terminal_growth=0.03, stage1_years=5,
                    growth_rate=0.10)
    market = _Market(price=20.0, shares=50.0)

    r = run_dcf(series, derived, bucket=TECHNOLOGY, market=market, assumptions=a)
    assert r.status == OK
    assert r.base_fcf == pytest.approx(100.0)  # median of 90/100/110
    assert r.net_debt == pytest.approx(300.0)  # 400 - 100
    # Same golden as the pure core: net debt does not reduce levered equity.
    assert r.equity_value == pytest.approx(1971.4285714286, rel=1e-9)
    assert r.fair_value_per_share == pytest.approx(39.4285714286, rel=1e-9)
    # margin of safety = (fair - price)/fair.
    assert r.margin_of_safety == pytest.approx(
        (39.4285714286 - 20.0) / 39.4285714286, rel=1e-9)
    assert r.input_tags  # provenance carried through
    assert r.period_ends == [date(2022, 12, 31), date(2023, 12, 31),
                             date(2024, 12, 31)]


# --- sensitivity --------------------------------------------------------------


def test_sensitivity_grid_shape_and_center():
    base = dict(fcf_0=100.0, stage1_growth=0.10, stage1_years=5,
                discount_rate=0.10, terminal_growth=0.03, shares=50.0)
    table = sensitivity(base, growth_deltas=(-0.02, 0.0, 0.02),
                        rate_deltas=(-0.01, 0.0, 0.01))
    assert len(table.grid) == 3 and all(len(row) == 3 for row in table.grid)
    # Center cell (zero deltas) reproduces the base fair value.
    assert table.grid[1][1] == pytest.approx(39.4285714286, rel=1e-9)
    # Monotonic: higher growth -> higher value; higher discount -> lower value.
    assert table.grid[2][1] > table.grid[1][1] > table.grid[0][1]
    assert table.grid[1][0] > table.grid[1][1] > table.grid[1][2]


# --- financial helpers --------------------------------------------------------


def test_ddm_and_justified_pb_known():
    # DDM: 2 * 1.03 / (0.08 - 0.03) = 2.06 / 0.05 = 41.2
    assert ddm_gordon(2.0, 0.03, 0.08) == pytest.approx(41.2)
    # Justified P/B: (0.15 - 0.03) / (0.08 - 0.03) = 0.12 / 0.05 = 2.4
    assert justified_pb(0.15, 0.03, 0.08) == pytest.approx(2.4)
    # Guards: r <= g must return None, never a negative/blown-up multiple.
    assert ddm_gordon(2.0, 0.10, 0.08) is None
    assert justified_pb(0.15, 0.10, 0.08) is None
