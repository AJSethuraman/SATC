"""Residual-income (EBO) valuation + economic-profit spread.

The residual-income headline case is hand-computed below so the test pins the
exact arithmetic, not a snapshot of the code's own output.
"""

from datetime import date

import pytest

from conftest import mk_series
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.industry.sic_buckets import BANKING
from stock_helper.valuation import OK, UNAVAILABLE
from stock_helper.valuation.economic_profit import (
    EconomicProfitResult,
    compute_economic_profit,
    economic_profit_spread,
)
from stock_helper.valuation.residual_income import (
    residual_income_value,
    run_residual_income,
)

# --------------------------------------------------------------------------- #
# Residual income — pure core, hand-computed
# --------------------------------------------------------------------------- #


def test_residual_income_clean_case_hand_computed():
    """B0=1000, ROE=0.15, Ke=0.10, g=0.03, T=5, ω=0.6, shares=100.

    spread = ROE - Ke = 0.05.
    Book:  B0=1000, B1=1030, B2=1060.90, B3=1092.727, B4=1125.50881,
           B5=1159.2740743.
    RI_t = 0.05*B_{t-1}:  50, 51.5, 53.045, 54.63635, 56.2754405.
    PV_t = RI_t / 1.1^t:
        PV1 = 50/1.1        = 45.454545...
        PV2 = 51.5/1.21     = 42.561983...
        PV3 = 53.045/1.331  = 39.853494...
        PV4 = 54.63635/1.4641   = 37.317362...
        PV5 = 56.2754405/1.61051 = 34.942621...
        Σ PV(RI) = 200.130006 (approx).
    Terminal: RI_6 = 0.05*B5 = 57.9637037; 1+Ke-ω = 0.5;
        TV_5 = 57.9637037/0.5 = 115.9274074;
        PV_term = 115.9274074/1.61051 = 71.981799.
    V0 = 1000 + 200.130006 + 71.981799 = 1272.111805.
    fair_value_per_share = 1272.111805 / 100 = 12.72111805.
    """
    r = residual_income_value(
        book_value_0=1000.0, roe=0.15, cost_of_equity=0.10, growth=0.03,
        years=5, persistence=0.6, shares=100.0,
    )
    assert r.status == OK
    assert r.book_value_0 == 1000.0
    assert r.pv_residual_incomes == pytest.approx(200.130006, abs=1e-4)
    assert r.pv_terminal == pytest.approx(71.981799, abs=1e-4)
    assert r.equity_value == pytest.approx(1272.111805, abs=1e-4)
    assert r.fair_value_per_share == pytest.approx(12.72111805, abs=1e-6)
    # Per-year RI schedule matches the hand arithmetic.
    years = [row[0] for row in r.ri_projection]
    ris = [row[1] for row in r.ri_projection]
    assert years == [1, 2, 3, 4, 5]
    assert ris == pytest.approx(
        [50.0, 51.5, 53.045, 54.63635, 56.2754405]
    )


def test_residual_income_value_equals_book_when_roe_equals_ke():
    """ROE == Ke => spread 0 => every RI_t = 0 and terminal = 0 => V0 == B0."""
    r = residual_income_value(
        book_value_0=1000.0, roe=0.10, cost_of_equity=0.10, growth=0.03,
        shares=100.0,
    )
    assert r.status == OK
    assert r.equity_value == pytest.approx(1000.0)
    assert r.pv_residual_incomes == pytest.approx(0.0)
    assert r.pv_terminal == pytest.approx(0.0)
    assert r.fair_value_per_share == pytest.approx(10.0)


def test_residual_income_below_book_when_roe_below_ke_not_floored():
    """ROE < Ke => negative residual income => V0 < B0, reported honestly."""
    r = residual_income_value(
        book_value_0=1000.0, roe=0.05, cost_of_equity=0.10, growth=0.03,
        shares=100.0,
    )
    assert r.status == OK
    assert r.equity_value < 1000.0  # NOT floored at book
    assert r.fair_value_per_share < 10.0
    assert any("below book" in c for c in r.caveats)


def test_residual_income_terminal_denominator_guard():
    """(1 + Ke - ω) <= 0 must refuse rather than divide into a non-convergent
    continuing value. Ke=0.10, ω=1.20 => denominator = -0.10."""
    r = residual_income_value(
        book_value_0=1000.0, roe=0.15, cost_of_equity=0.10, growth=0.03,
        persistence=1.20, shares=100.0,
    )
    assert r.status == UNAVAILABLE
    assert r.equity_value is None
    assert any("Terminal denominator" in c for c in r.caveats)


def test_residual_income_non_positive_book_unavailable():
    r = residual_income_value(
        book_value_0=0.0, roe=0.15, cost_of_equity=0.10, growth=0.03, shares=100.0,
    )
    assert r.status == UNAVAILABLE
    assert r.equity_value is None


def test_residual_income_non_positive_cost_of_equity_unavailable():
    r = residual_income_value(
        book_value_0=1000.0, roe=0.15, cost_of_equity=0.0, growth=0.03, shares=100.0,
    )
    assert r.status == UNAVAILABLE


def test_residual_income_shares_non_positive_per_share_none():
    r0 = residual_income_value(
        book_value_0=1000.0, roe=0.15, cost_of_equity=0.10, growth=0.03, shares=0.0,
    )
    assert r0.status == OK
    assert r0.equity_value is not None
    assert r0.fair_value_per_share is None

    r_none = residual_income_value(
        book_value_0=1000.0, roe=0.15, cost_of_equity=0.10, growth=0.03, shares=None,
    )
    assert r_none.status == OK
    assert r_none.fair_value_per_share is None


# --------------------------------------------------------------------------- #
# Residual income — series-driven wrapper (works for banks)
# --------------------------------------------------------------------------- #


def _bank_series():
    """A tiny bank-like series: two equity points (for derived ROE), net income,
    and a point-in-time share count. No FCF at all — the RI model still works."""
    y1, y2 = date(2023, 12, 31), date(2024, 12, 31)
    series = {
        "equity": mk_series("equity", [(y1, 900.0), (y2, 1000.0)]),
        "net_income": mk_series("net_income", [(y1, 120.0), (y2, 142.5)]),
        "shares_outstanding": mk_series(
            "shares_outstanding", [(y2, 100.0)], unit="shares"
        ),
    }
    return series


def test_run_residual_income_works_for_banks():
    series = _bank_series()
    derived = compute_derived_metrics(series)
    # ROE = 142.5 / avg(900, 1000) = 142.5 / 950 = 0.15 exactly.
    assert derived["roe"].latest == pytest.approx(0.15)

    r = run_residual_income(series, derived, market=None, cost_of_equity=0.10,
                            bucket=BANKING)
    assert r.status == OK
    assert r.book_value_0 == 1000.0
    assert r.roe == pytest.approx(0.15)
    assert r.shares == 100.0
    assert r.fair_value_per_share is not None
    # Book value 1000, ROE 0.15 > Ke 0.10 => value above book.
    assert r.equity_value > 1000.0
    assert any("Financial bucket" in c for c in r.caveats)
    assert r.input_accessions  # provenance carried


def test_run_residual_income_unavailable_without_equity():
    y2 = date(2024, 12, 31)
    series = {"net_income": mk_series("net_income", [(y2, 100.0)])}
    derived = compute_derived_metrics(series)
    r = run_residual_income(series, derived, market=None, cost_of_equity=0.10)
    assert r.status == UNAVAILABLE
    assert r.equity_value is None


# --------------------------------------------------------------------------- #
# Economic profit (ROIC − WACC)
# --------------------------------------------------------------------------- #


def test_economic_profit_spread_creates_value():
    assert economic_profit_spread(0.18, 0.10) == pytest.approx(0.08)
    res = compute_economic_profit(0.18, 0.10)
    assert isinstance(res, EconomicProfitResult)
    assert res.spread == pytest.approx(0.08)
    assert res.creates_value is True


def test_economic_profit_spread_destroys_value():
    assert economic_profit_spread(0.06, 0.10) == pytest.approx(-0.04)
    res = compute_economic_profit(0.06, 0.10)
    assert res.spread == pytest.approx(-0.04)
    assert res.creates_value is False


def test_economic_profit_none_safe():
    assert economic_profit_spread(None, 0.10) is None
    assert economic_profit_spread(0.18, None) is None
    res = compute_economic_profit(None, 0.10)
    assert res.spread is None
    assert res.creates_value is False
    assert any("missing" in c.lower() for c in res.caveats)


def test_economic_profit_persistence_note():
    res = compute_economic_profit(
        0.18, 0.10, roic_history=[0.15, 0.05, 0.20, 0.12]
    )
    # Spreads vs WACC 0.10: +0.05, -0.05, +0.10, +0.02 => 3 of 4 positive.
    assert res.spread_history == pytest.approx([0.05, -0.05, 0.10, 0.02])
    assert "3 of the last 4" in res.persistence_note
