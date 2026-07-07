"""Enterprise value + market-multiples calculation core.

All offline: series are built with conftest.mk_series and MarketContext is
constructed directly (no price fetch, no DB)."""

from datetime import date

import pytest

from conftest import mk_series
from stock_helper.features.context import MarketContext
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.industry.sic_buckets import BANKING, INDUSTRIALS
from stock_helper.valuation.multiples import (
    compute_enterprise_value,
    compute_multiples,
    peer_relative_valuation,
    self_history_valuation,
)

D = date
END = date(2024, 12, 31)


def _market(*, market_cap, price=10.0, shares=None):
    """Minimal MarketContext carrying only what the EV/multiples core reads."""
    return MarketContext(
        price=price,
        price_date=D(2025, 1, 2),
        momentum_12_1=None,
        volatility_60d=None,
        market_cap=market_cap,
        pe=None,
        ps=None,
        shares=shares,
        shares_source="shares_outstanding",
    )


def _series(values: dict[str, float]):
    return {k: mk_series(k, [(END, v)]) for k, v in values.items()}


# --------------------------------------------------------------------------- #
# Enterprise value
# --------------------------------------------------------------------------- #


def test_enterprise_value_bridge():
    # market_cap=500, total_debt=200, preferred=10, minority=20, cash=50 -> EV=680.
    series = _series(
        {
            "long_term_debt": 200.0,  # -> derived total_debt = 200
            "preferred_equity": 10.0,
            "minority_interest": 20.0,
            "cash": 50.0,
            "marketable_securities": 0.0,
        }
    )
    derived = compute_derived_metrics(series)
    ev = compute_enterprise_value(series, derived, _market(market_cap=500.0))

    assert ev is not None
    assert ev.enterprise_value == 680.0
    assert ev.total_debt == 200.0
    assert ev.cash == 50.0
    assert ev.preferred == 10.0
    assert ev.minority == 20.0
    assert ev.net_debt == 150.0
    assert ev.components["market_cap"] == 500.0


def test_missing_market_returns_none():
    series = _series({"long_term_debt": 100.0, "cash": 10.0})
    derived = compute_derived_metrics(series)
    assert compute_enterprise_value(series, derived, None) is None
    # market present but no market cap -> also None.
    assert compute_enterprise_value(series, derived, _market(market_cap=None)) is None


def test_net_cash_ev_nonpositive():
    # No debt, huge cash -> EV <= 0. EV multiples undefined, never negative.
    series = _series({"cash": 5000.0, "operating_income": 100.0, "revenue": 400.0})
    derived = compute_derived_metrics(series)
    ev = compute_enterprise_value(series, derived, _market(market_cap=500.0))

    assert ev is not None
    assert ev.enterprise_value == 500.0 - 5000.0  # -4500
    assert ev.enterprise_value <= 0

    multiples = compute_multiples(series, derived, _market(market_cap=500.0), ev, bucket=INDUSTRIALS)
    for key in ("ev_ebit", "ev_ebitda", "ev_sales"):
        m = multiples[key]
        assert m.value is None
        assert m.undefined_reason
    # No EV-based multiple slips through as a negative "cheap" number.
    assert multiples["ev_ebit"].value is None
    assert multiples["earnings_yield"].value is None  # yield denom (EV) non-positive


# --------------------------------------------------------------------------- #
# Multiples
# --------------------------------------------------------------------------- #


def test_ev_multiples_known():
    # EV=680; EBIT=85 -> 8.0; EBITDA=100 (op_inc 85 + D&A 15) -> 6.8; Sales=340 -> 2.0.
    series = _series(
        {
            "long_term_debt": 200.0,
            "preferred_equity": 10.0,
            "minority_interest": 20.0,
            "cash": 50.0,
            "operating_income": 85.0,
            "depreciation_amortization": 15.0,
            "revenue": 340.0,
        }
    )
    derived = compute_derived_metrics(series)
    market = _market(market_cap=500.0)
    ev = compute_enterprise_value(series, derived, market)
    assert ev.enterprise_value == 680.0
    assert derived["ebitda"].latest == 100.0

    multiples = compute_multiples(series, derived, market, ev, bucket=INDUSTRIALS)
    assert multiples["ev_ebit"].value == pytest.approx(8.0)
    assert multiples["ev_ebitda"].value == pytest.approx(6.8)
    assert multiples["ev_sales"].value == pytest.approx(2.0)


def test_negative_ebit_multiple_undefined():
    # EV > 0 but EBIT < 0 -> EV/EBIT undefined via non-positive denominator.
    series = _series(
        {
            "long_term_debt": 200.0,
            "cash": 50.0,
            "operating_income": -30.0,
            "revenue": 340.0,
        }
    )
    derived = compute_derived_metrics(series)
    market = _market(market_cap=500.0)
    ev = compute_enterprise_value(series, derived, market)
    assert ev.enterprise_value > 0

    multiples = compute_multiples(series, derived, market, ev, bucket=INDUSTRIALS)
    m = multiples["ev_ebit"]
    assert m.value is None
    assert m.undefined_reason is not None
    assert "EBIT" in m.undefined_reason
    # ev_sales still defined (revenue positive) -> proves it's the denominator, not EV.
    assert multiples["ev_sales"].value == pytest.approx(650.0 / 340.0)


def test_earnings_yield_keeps_negative_with_caveat():
    # Yields keep a negative numerator (honest) but flag it; denom (EV) positive.
    series = _series({"long_term_debt": 200.0, "cash": 50.0, "operating_income": -34.0})
    derived = compute_derived_metrics(series)
    market = _market(market_cap=500.0)
    ev = compute_enterprise_value(series, derived, market)  # EV = 650
    multiples = compute_multiples(series, derived, market, ev, bucket=INDUSTRIALS)

    ey = multiples["earnings_yield"]
    assert ey.value == pytest.approx(-34.0 / 650.0)
    assert ey.caveat and "negative" in ey.caveat


def test_financial_bucket_ev_multiple_caveat():
    series = _series(
        {"long_term_debt": 200.0, "cash": 50.0, "operating_income": 85.0}
    )
    derived = compute_derived_metrics(series)
    market = _market(market_cap=500.0)
    ev = compute_enterprise_value(series, derived, market)
    multiples = compute_multiples(series, derived, market, ev, bucket=BANKING)
    assert multiples["ev_ebit"].caveat and "financial" in multiples["ev_ebit"].caveat


# --------------------------------------------------------------------------- #
# Peer-relative
# --------------------------------------------------------------------------- #


def test_peer_relative_needs_three_peers():
    company_multiples: dict = {}
    out = peer_relative_valuation(
        company_multiples,
        {"pe": [15.0, 16.0]},  # only 2 peers
        company_metrics={"pe": 4.0, "price": 50.0},
        net_debt=0.0,
        shares=10.0,
    )
    assert out == {}


def test_peer_relative_implied_price_ev_bridge():
    # Peer EV/EBIT median = 8; EBIT=100 -> implied EV=800; net_debt=150 ->
    # implied equity=650; shares=50 -> implied price=13.0; price=10 -> +30%.
    out = peer_relative_valuation(
        {},
        {"ev_ebit": [7.0, 8.0, 9.0]},
        company_metrics={"ev_ebit": 100.0, "price": 10.0},
        net_debt=150.0,
        shares=50.0,
    )
    assert set(out) == {"ev_ebit"}
    prv = out["ev_ebit"]
    assert prv.peer_median == pytest.approx(8.0)
    assert prv.n_peers == 3
    assert prv.implied_price == pytest.approx(13.0)
    assert prv.upside_pct == pytest.approx(0.3)


def test_peer_relative_equity_multiple():
    # Equity multiple: implied price = peer_median * per-share metric.
    out = peer_relative_valuation(
        {},
        {"pe": [12.0, 14.0, 16.0]},  # median 14
        company_metrics={"pe": 5.0, "price": 60.0},  # eps per share = 5
        net_debt=0.0,
        shares=10.0,
    )
    assert out["pe"].implied_price == pytest.approx(70.0)
    assert out["pe"].upside_pct == pytest.approx((70.0 - 60.0) / 60.0)


def test_peer_relative_ignores_nonpositive_peers():
    # Negative peer multiples are dropped; drops below 3 -> key skipped.
    out = peer_relative_valuation(
        {},
        {"ev_ebit": [-5.0, 8.0, 9.0]},  # only 2 valid
        company_metrics={"ev_ebit": 100.0, "price": 10.0},
        net_debt=0.0,
        shares=10.0,
    )
    assert out == {}


# --------------------------------------------------------------------------- #
# Self-history
# --------------------------------------------------------------------------- #


def test_self_history_zscore_and_verdict():
    # P/E history [10,12,14,16]: median 13, MAD dev median 2 -> scaled 2.9652.
    # current 20 -> z = 7/2.9652 = 2.361 -> 'rich' (a normal multiple).
    # Earnings-yield history [.05,.06,.07,.08]: median .065, scaled MAD .014826.
    # current .12 -> z = .055/.014826 = 3.71 clipped to 3.0; yield sign inverted
    # -> 'cheap' (high yield = cheap).
    out = self_history_valuation(
        {"pe": 20.0, "earnings_yield": 0.12},
        {
            "pe": [10.0, 12.0, 14.0, 16.0],
            "earnings_yield": [0.05, 0.06, 0.07, 0.08],
        },
    )

    assert out["pe"].history_median == 13.0
    assert out["pe"].zscore == pytest.approx(7.0 / (2.0 * 1.4826), rel=1e-6)
    assert out["pe"].verdict == "rich"

    assert out["earnings_yield"].zscore == pytest.approx(3.0)  # clipped
    assert out["earnings_yield"].verdict == "cheap"  # sign inverted for yields


def test_self_history_needs_four_points():
    out = self_history_valuation({"pe": 20.0}, {"pe": [10.0, 12.0, 14.0]})
    assert out == {}


def test_self_history_in_line():
    out = self_history_valuation({"pe": 13.0}, {"pe": [10.0, 12.0, 14.0, 16.0]})
    assert out["pe"].verdict == "in-line"
