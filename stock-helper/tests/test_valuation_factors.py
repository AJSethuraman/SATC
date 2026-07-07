"""Quality + distress factor calculation core.

All offline: series are built with conftest.mk_series; MarketContext is
constructed directly (no price fetch, no DB). Exact numbers are asserted against
hand-computed values so a coefficient/definition regression fails loudly."""

import copy
from datetime import date

import pytest

from conftest import mk_series
from stock_helper.features.context import MarketContext
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.industry.sic_buckets import BANKING, INDUSTRIALS
from stock_helper.valuation import NOT_APPLICABLE, OK
from stock_helper.valuation.factors import (
    DISTRESS,
    GREY,
    SAFE,
    compute_accruals_quality,
    compute_altman_z,
    compute_gross_profitability,
    compute_magic_formula,
    compute_piotroski_f_score,
    compute_quality_factors,
)

Y = {2022: date(2022, 12, 31), 2023: date(2023, 12, 31), 2024: date(2024, 12, 31)}
END = date(2024, 12, 31)


def _series_from_spec(spec: dict[str, dict[int, float]]) -> dict:
    """spec: metric_key -> {year: value}. shares get the 'shares' unit."""
    out = {}
    for key, by_year in spec.items():
        unit = "shares" if "shares" in key else "USD"
        pts = [(Y[y], float(v)) for y, v in sorted(by_year.items())]
        out[key] = mk_series(key, pts, unit=unit)
    return out


def _latest(values: dict[str, float]) -> dict:
    return {k: mk_series(k, [(END, float(v))]) for k, v in values.items()}


def _market(*, market_cap):
    return MarketContext(
        price=10.0, price_date=date(2025, 1, 2), momentum_12_1=None,
        volatility_60d=None, market_cap=market_cap, pe=None, ps=None,
        shares=None, shares_source="shares_outstanding",
    )


# --------------------------------------------------------------------------- #
# Piotroski F-score
# --------------------------------------------------------------------------- #

# A three-year balance/flow set engineered so all nine tests pass -> score 9.
PERFECT_SPEC = {
    "total_assets": {2022: 800, 2023: 900, 2024: 1000},
    "net_income": {2023: 100, 2024: 150},
    "operating_cash_flow": {2023: 180, 2024: 200},
    "long_term_debt": {2023: 300, 2024: 250},
    "current_assets": {2023: 400, 2024: 500},
    "current_liabilities": {2023: 200, 2024: 200},
    "diluted_shares": {2023: 1000, 2024: 1000},
    "revenue": {2023: 1000, 2024: 1200},
    "gross_profit": {2023: 400, 2024: 540},
}


def test_piotroski_perfect_nine():
    res = compute_piotroski_f_score(_series_from_spec(PERFECT_SPEC))
    assert res is not None
    assert res.value == 9.0
    assert res.detail["tests"] == {
        "roa_positive": 1, "ocf_positive": 1, "roa_improved": 1, "accrual": 1,
        "ltd_ratio_fell": 1, "current_ratio_improved": 1, "no_new_shares": 1,
        "gross_margin_improved": 1, "asset_turnover_improved": 1,
    }
    assert res.detail["uncomputable"] == []


# Each override flips exactly one test to 0 -> score 8. (roa_positive needs a
# two-field override to keep ΔROA satisfied; ocf_positive is intentionally
# omitted — with the accrual test defined as OCF>NI it cannot be dropped in
# isolation: OCF<=0 while OCF>NI forces NI<0, which also breaks roa_positive.)
DROP_ONE = [
    ("roa_positive", {"net_income": {2024: 0, 2023: -100}}),
    ("roa_improved", {"net_income": {2024: 90}}),
    ("accrual", {"net_income": {2024: 250}}),
    ("ltd_ratio_fell", {"long_term_debt": {2024: 400}}),
    ("current_ratio_improved", {"current_liabilities": {2024: 300}}),
    ("no_new_shares", {"diluted_shares": {2024: 1100}}),
    ("gross_margin_improved", {"gross_profit": {2024: 380}}),
    ("asset_turnover_improved", {"revenue": {2024: 1000}}),
]


@pytest.mark.parametrize("flipped,override", DROP_ONE, ids=[c[0] for c in DROP_ONE])
def test_piotroski_drop_one(flipped, override):
    spec = copy.deepcopy(PERFECT_SPEC)
    for key, by_year in override.items():
        spec[key].update(by_year)
    res = compute_piotroski_f_score(_series_from_spec(spec))
    assert res is not None
    assert res.value == 8.0, res.detail["tests"]
    assert res.detail["tests"][flipped] == 0
    others = {k: v for k, v in res.detail["tests"].items() if k != flipped}
    assert all(v == 1 for v in others.values()), others


def test_piotroski_missing_prior_year():
    # Only one fiscal year of data -> no YoY comparison possible -> None.
    spec = {"total_assets": {2024: 1000}, "net_income": {2024: 150}}
    assert compute_piotroski_f_score(_series_from_spec(spec)) is None


# --------------------------------------------------------------------------- #
# Gross profitability
# --------------------------------------------------------------------------- #


def test_gross_profitability_known():
    series = _latest({"gross_profit": 400.0, "total_assets": 900.0})
    res = compute_gross_profitability(series)
    assert res is not None
    assert res.value == pytest.approx(0.4444, abs=1e-4)


def test_gross_profitability_zero_assets_none():
    series = _latest({"gross_profit": 400.0, "total_assets": 0.0})
    assert compute_gross_profitability(series) is None


# --------------------------------------------------------------------------- #
# Magic Formula
# --------------------------------------------------------------------------- #


def test_magic_formula_known():
    # EBIT=100, EV=800 -> earnings_yield=0.125.
    # NWC_ex_cash=(300-50)-100=150; ppe=50 -> capital=200; roic=100/200=0.5.
    series = _latest({
        "operating_income": 100.0, "current_assets": 300.0, "cash": 50.0,
        "current_liabilities": 100.0, "ppe_net": 50.0,
    })
    derived = compute_derived_metrics(series)
    res = compute_magic_formula(series, derived, None, ev=800.0)
    assert res is not None
    assert res.value == pytest.approx(0.125)  # earnings yield headline
    assert res.detail["earnings_yield"] == pytest.approx(0.125)
    assert res.detail["roic"] == pytest.approx(0.5)


def test_magic_formula_no_ev_none():
    series = _latest({
        "operating_income": 100.0, "current_assets": 300.0, "cash": 50.0,
        "current_liabilities": 100.0, "ppe_net": 50.0,
    })
    assert compute_magic_formula(series, {}, None, ev=None) is None
    assert compute_magic_formula(series, {}, None, ev=0.0) is None  # EV<=0


def test_magic_formula_zero_capital_none():
    # NWC_ex_cash=(100-50)-50=0; ppe=0 -> capital=0 -> None (never a negative roic).
    series = _latest({
        "operating_income": 100.0, "current_assets": 100.0, "cash": 50.0,
        "current_liabilities": 50.0, "ppe_net": 0.0,
    })
    assert compute_magic_formula(series, {}, None, ev=800.0) is None


# --------------------------------------------------------------------------- #
# Accruals quality
# --------------------------------------------------------------------------- #


def test_accruals_known():
    series = _latest({
        "net_income": 100.0, "operating_cash_flow": 180.0, "total_assets": 850.0,
    })
    res = compute_accruals_quality(series)
    assert res is not None
    assert res.value == pytest.approx((100.0 - 180.0) / 850.0, abs=1e-6)  # -0.0941


def test_accruals_zero_assets_none():
    series = _latest({
        "net_income": 100.0, "operating_cash_flow": 180.0, "total_assets": 0.0,
    })
    assert compute_accruals_quality(series) is None


# --------------------------------------------------------------------------- #
# Altman Z / Z''
# --------------------------------------------------------------------------- #


def test_altman_z_grey_zone_manufacturer():
    # Manufacturer (SIC 3000) with market cap -> original Z.
    # TA=1000, TL=500, mktcap=500 -> X4=1.0. WC=100 -> X1=0.1. RE=200 -> X2=0.2.
    # EBIT=150 -> X3=0.15. revenue=1115 -> X5=1.115.
    # Z = 0.12+0.28+0.495+0.6+1.115 = 2.61 -> grey (1.81 <= 2.61 <= 2.99).
    series = _latest({
        "total_assets": 1000.0, "total_liabilities": 500.0,
        "current_assets": 300.0, "current_liabilities": 200.0,
        "retained_earnings": 200.0, "operating_income": 150.0, "revenue": 1115.0,
    })
    res = compute_altman_z(series, {}, _market(market_cap=500.0), sic="3000")
    assert res is not None
    assert res.value == pytest.approx(2.61)
    assert res.detail["zone"] == GREY
    assert "Z (1968" in res.detail["model"]


def test_altman_zprime_grey_zone_nonmanufacturer():
    # Non-manufacturer (SIC 7372, software) -> Z'' (book equity, no market).
    # TA=1000, TL=500. WC=50 -> X1=0.05. RE=100 -> X2=0.1. EBIT=50 -> X3=0.05.
    # equity=200 -> X4=0.4.
    # Z'' = 6.56*.05 + 3.26*.1 + 6.72*.05 + 1.05*.4 = .328+.326+.336+.42 = 1.41.
    series = _latest({
        "total_assets": 1000.0, "total_liabilities": 500.0,
        "current_assets": 200.0, "current_liabilities": 150.0,
        "retained_earnings": 100.0, "operating_income": 50.0, "equity": 200.0,
    })
    res = compute_altman_z(series, {}, market=None, sic="7372")
    assert res is not None
    assert res.value == pytest.approx(1.41)
    assert res.detail["zone"] == GREY  # 1.1 <= 1.41 <= 2.6
    assert "Z''" in res.detail["model"]


def test_altman_zone_boundaries():
    # Nudge the Z'' case across both cutoffs by moving book equity (X4 only).
    base = {
        "total_assets": 1000.0, "total_liabilities": 500.0,
        "current_assets": 200.0, "current_liabilities": 150.0,
        "retained_earnings": 100.0, "operating_income": 50.0,
    }
    # X1..X3 contribute 0.328+0.326+0.336 = 0.99; X4 = 1.05*equity/500.
    # equity=1000 -> Z''=0.99+2.1=3.09 > 2.6 -> safe.
    safe = compute_altman_z(_latest({**base, "equity": 1000.0}), {}, None, sic="7372")
    assert safe.detail["zone"] == SAFE
    # equity=25 -> Z''=0.99+0.0525=1.0425 < 1.1 -> distress.
    distress = compute_altman_z(_latest({**base, "equity": 25.0}), {}, None, sic="7372")
    assert distress.detail["zone"] == DISTRESS


def test_altman_zero_total_assets_none():
    series = _latest({
        "total_assets": 0.0, "total_liabilities": 500.0,
        "current_assets": 200.0, "current_liabilities": 150.0,
        "retained_earnings": 100.0, "operating_income": 50.0, "equity": 200.0,
    })
    assert compute_altman_z(series, {}, None, sic="7372") is None


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #


def test_bank_gets_roa_roe_not_industrial():
    # Two years of income + equity so the derived ROE (avg-equity) computes.
    series = _series_from_spec({
        "net_income": {2023: 90, 2024: 100},
        "equity": {2023: 900, 2024: 1100},
        "total_assets": {2023: 9000, 2024: 10000},
    })
    derived = compute_derived_metrics(series)
    qf = compute_quality_factors(series, derived, bucket=BANKING, sic="6022")

    assert qf.metric_set == "financial"
    assert qf.factors["piotroski_f"].status == NOT_APPLICABLE
    assert qf.factors["altman_z"].status == NOT_APPLICABLE
    assert qf.factors["gross_profitability"].status == NOT_APPLICABLE
    roe = qf.factors["roe"]
    assert roe.status == OK
    assert roe.value is not None
    # ROE = 100 / avg(900, 1100) = 100/1000 = 0.10.
    assert roe.value == pytest.approx(0.10)
    assert qf.factors["roa"].value == pytest.approx(100.0 / 10000.0)


def test_industrial_dispatch_has_full_set():
    series = _series_from_spec(PERFECT_SPEC)
    # Add the balance-sheet items the Altman/Magic factors need.
    series.update(_series_from_spec({
        "operating_income": {2023: 110, 2024: 130},
        "total_liabilities": {2023: 400, 2024: 500},
        "retained_earnings": {2023: 300, 2024: 350},
        "equity": {2023: 500, 2024: 500},
        "cash": {2023: 40, 2024: 50},
        "ppe_net": {2023: 200, 2024: 220},
    }))
    derived = compute_derived_metrics(series)
    qf = compute_quality_factors(
        series, derived, bucket=INDUSTRIALS, sic="3500",
        market=_market(market_cap=2000.0), ev=1500.0,
    )
    assert qf.metric_set == "industrial"
    assert qf.factors["piotroski_f"].status == OK
    assert qf.factors["piotroski_f"].value == 9.0
    assert qf.factors["altman_z"].status == OK
    assert qf.factors["magic_formula"].status == OK
    assert qf.composite is not None
    assert 0.0 <= qf.composite <= 100.0
    assert 0.0 < qf.coverage <= 1.0
