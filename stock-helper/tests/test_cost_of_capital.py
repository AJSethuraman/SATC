"""Cost-of-capital engine: CAPM Ke, after-tax Kd, WACC, tax rate, beta, FRED.

All figures below are hand-computed so a regression can't drift silently."""

from datetime import date

import pytest

from stock_helper.connectors.fred import FRED_OBSERVATIONS_URL, FredClient
from stock_helper.features.metrics import DerivedMetric
from stock_helper.valuation.cost_of_capital import (
    DEFAULT_TAX_RATE,
    after_tax_cost_of_debt,
    capm_cost_of_equity,
    compute_cost_of_capital,
    effective_tax_rate,
    estimate_beta,
    wacc,
)

# --- CAPM cost of equity -----------------------------------------------------

def test_capm_cost_of_equity():
    assert capm_cost_of_equity(0.04, 1.2, 0.05) == pytest.approx(0.10)


# --- After-tax cost of debt --------------------------------------------------

def test_after_tax_cost_of_debt():
    # (50/1000) * (1 - 0.25) = 0.05 * 0.75 = 0.0375
    assert after_tax_cost_of_debt(50, 1000, 0.25) == pytest.approx(0.0375)


def test_after_tax_cost_of_debt_none_when_no_debt():
    assert after_tax_cost_of_debt(50, 0, 0.25) is None
    assert after_tax_cost_of_debt(50, -100, 0.25) is None
    assert after_tax_cost_of_debt(None, 1000, 0.25) is None


# --- WACC --------------------------------------------------------------------

def test_wacc_blended():
    # We=0.8, Wd=0.2 -> 0.8*0.10 + 0.2*0.0375 = 0.08 + 0.0075 = 0.0875
    assert wacc(800, 200, 0.10, 0.0375) == pytest.approx(0.0875)


def test_wacc_all_equity_fallback_uses_ke_for_debt():
    # kd None -> debt slice charged at ke -> blend collapses to ke.
    assert wacc(800, 200, 0.10, None) == pytest.approx(0.10)


def test_wacc_none_when_no_capital_base():
    assert wacc(0, 0, 0.10, 0.0375) is None
    assert wacc(None, None, 0.10, 0.0375) is None


# --- Effective tax rate ------------------------------------------------------

def test_effective_tax_rate_basic():
    assert effective_tax_rate(210, 1000) == pytest.approx(0.21)


def test_effective_tax_rate_clamps_high():
    assert effective_tax_rate(700, 1000) == pytest.approx(0.5)


def test_effective_tax_rate_clamps_negative_to_zero():
    # A tax benefit (negative expense) clamps to 0.0, not a negative shield.
    assert effective_tax_rate(-100, 1000) == pytest.approx(0.0)


def test_effective_tax_rate_defaults_when_not_computable():
    assert effective_tax_rate(None, 1000) == DEFAULT_TAX_RATE
    assert effective_tax_rate(210, None) == DEFAULT_TAX_RATE
    assert effective_tax_rate(210, 0) == DEFAULT_TAX_RATE  # non-positive base
    assert effective_tax_rate(210, -500) == DEFAULT_TAX_RATE


# --- Beta --------------------------------------------------------------------

def test_estimate_beta_known_slope():
    # stock = 2 * market -> OLS slope = 2.0 exactly (clamped boundary is 2.5).
    market = [((i % 7) - 3) / 100.0 for i in range(80)]
    stock = [2.0 * m for m in market]
    beta = estimate_beta(stock, market)
    assert beta == pytest.approx(2.0)


def test_estimate_beta_none_when_too_few_points():
    market = [0.01 * ((i % 5) - 2) for i in range(59)]
    stock = [2.0 * m for m in market]
    assert estimate_beta(stock, market) is None


def test_estimate_beta_none_on_zero_market_variance():
    market = [0.01] * 80  # no variance -> undefined slope
    stock = [((i % 5) - 2) / 100.0 for i in range(80)]
    assert estimate_beta(stock, market) is None


def test_estimate_beta_clamps_to_band():
    # stock = 10 * market -> raw slope 10, clamped to 2.5.
    market = [((i % 7) - 3) / 100.0 for i in range(80)]
    stock = [10.0 * m for m in market]
    assert estimate_beta(stock, market) == pytest.approx(2.5)


# --- Assembly ----------------------------------------------------------------

class _FakeMarket:
    def __init__(self, market_cap):
        self.market_cap = market_cap


def _dm(key: str, value: float) -> DerivedMetric:
    return DerivedMetric(
        key=key, label=key, unit="USD", formula="test",
        points=[(date(2024, 12, 31), value)],
    )


def test_compute_cost_of_capital_full_stack():
    derived = {
        "interest_expense": _dm("interest_expense", 50.0),
        "total_debt": _dm("total_debt", 1000.0),
        "tax_expense": _dm("tax_expense", 210.0),
        "pretax_income": _dm("pretax_income", 1000.0),
    }
    result = compute_cost_of_capital(
        {}, derived, _FakeMarket(4000.0), risk_free=0.04, beta=1.2, erp=0.05
    )
    # Ke = 0.04 + 1.2*0.05 = 0.10
    assert result.ke == pytest.approx(0.10)
    assert result.tax_rate == pytest.approx(0.21)
    # Kd = (50/1000)*(1-0.21) = 0.0395
    assert result.kd_after_tax == pytest.approx(0.0395)
    # WACC: E=4000, D=1000 -> We=0.8, Wd=0.2 -> 0.8*0.10 + 0.2*0.0395 = 0.0879
    assert result.wacc == pytest.approx(0.0879)
    assert result.weight_equity == pytest.approx(0.8)
    assert result.weight_debt == pytest.approx(0.2)


def test_compute_cost_of_capital_degrades_to_ke():
    # No debt, no market cap, no tax data -> Ke is the floor, caveats explain.
    result = compute_cost_of_capital({}, {}, None, risk_free=0.042)
    assert result.beta == pytest.approx(1.0)  # fallback market beta
    assert result.tax_rate == DEFAULT_TAX_RATE
    assert result.kd_after_tax is None
    assert result.wacc == pytest.approx(result.ke)
    assert any("market beta" in c for c in result.caveats)
    assert any("market cap" in c for c in result.caveats)


# --- FRED client -------------------------------------------------------------

def _fred_transport(payload_value, api_key="testkey"):
    import json

    import httpx

    url = FRED_OBSERVATIONS_URL.format(series_id="DGS10", api_key=api_key)
    body = json.dumps(
        {"observations": [{"date": "2026-07-06", "value": payload_value}]}
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == url:
            return httpx.Response(200, text=body)
        return httpx.Response(404, text="not found")

    return httpx.MockTransport(handler)


def test_fred_risk_free_rate_percent_to_fraction(settings):
    cfg = settings.model_copy(update={"fred_api_key": "testkey"})
    client = FredClient(cfg, transport=_fred_transport("4.20"))
    assert client.risk_free_rate() == pytest.approx(0.042)


def test_fred_missing_marker_returns_none(settings):
    cfg = settings.model_copy(update={"fred_api_key": "testkey"})
    client = FredClient(cfg, transport=_fred_transport("."))
    assert client.risk_free_rate() is None


def test_fred_no_api_key_returns_none(settings):
    # No key -> inert client, never touches the transport.
    client = FredClient(settings, transport=_fred_transport("4.20"))
    assert client.risk_free_rate() is None


def test_fred_response_cached(settings):
    cfg = settings.model_copy(update={"fred_api_key": "testkey"})
    client = FredClient(cfg, transport=_fred_transport("4.20"))
    assert client.risk_free_rate() == pytest.approx(0.042)
    # Second call served from the disk cache; a torn-down transport proves it.
    client._client.close()
    assert client.risk_free_rate() == pytest.approx(0.042)
