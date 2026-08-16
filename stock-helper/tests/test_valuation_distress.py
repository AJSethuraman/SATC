"""Distress / manipulation panel: Ohlson O, Zmijewski, Montier C.

All offline (conftest.mk_series; no DB / network / price fetch). The O-score,
Zmijewski X, and their probabilities are asserted against hand-computed values so
a coefficient or definition regression fails loudly. A clean company reads low on
every model; a stressed one reads high on all of them; and the panel / stress
report fold the three bankruptcy screens into an agreement signal.
"""

import math
from datetime import date

import pytest

from conftest import mk_series
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.industry.sic_buckets import BANKING, INDUSTRIALS
from stock_helper.valuation import NOT_APPLICABLE, OK
from stock_helper.valuation.factors import (
    DISTRESS,
    SAFE,
    compute_ohlson_o_score,
    compute_quality_factors,
    compute_zmijewski_score,
)
from stock_helper.valuation.forensics import (
    compute_montier_c_score,
    compute_stress_report,
)

D_PREV = date(2022, 12, 31)
D_CURR = date(2023, 12, 31)


def _two_year(spec: dict[str, tuple[float, float]]) -> dict:
    """key -> (prev_value, curr_value) into two-year MetricSeries."""
    return {
        key: mk_series(key, [(D_PREV, prev), (D_CURR, curr)])
        for key, (prev, curr) in spec.items()
    }


def _one_year(spec: dict[str, float]) -> dict:
    return {key: mk_series(key, [(D_CURR, v)]) for key, v in spec.items()}


# --------------------------------------------------------------------------- #
# Hand-built companies
# --------------------------------------------------------------------------- #

# A healthy company: modest growth (<10%), positive & rising income, cash >
# earnings, flat working-capital structure. Every distress model reads "safe"
# and the Montier C-score is 0.
CLEAN = {
    "total_assets": (1000.0, 1050.0),
    "total_liabilities": (400.0, 400.0),
    "current_assets": (500.0, 500.0),
    "current_liabilities": (200.0, 200.0),
    "net_income": (120.0, 150.0),
    "operating_cash_flow": (160.0, 200.0),
    "depreciation_amortization": (50.0, 50.0),
    "revenue": (1000.0, 1000.0),
    "accounts_receivable": (100.0, 100.0),
    "inventory": (100.0, 100.0),
    "cash": (100.0, 100.0),
    "ppe_net": (300.0, 300.0),
    "retained_earnings": (300.0, 350.0),
    "operating_income": (200.0, 250.0),
    "equity": (600.0, 650.0),
}

# A distressed company: 20% asset growth, negative income in BOTH years,
# liabilities exceeding assets (negative equity), collapsing revenue, ballooning
# receivables & inventory, and a falling depreciation rate.
STRESSED = {
    "total_assets": (1000.0, 1200.0),
    "total_liabilities": (900.0, 1300.0),
    "current_assets": (300.0, 250.0),
    "current_liabilities": (400.0, 600.0),
    "net_income": (-50.0, -100.0),
    "operating_cash_flow": (-80.0, -200.0),
    "depreciation_amortization": (100.0, 40.0),
    "revenue": (1000.0, 800.0),
    "accounts_receivable": (100.0, 200.0),
    "inventory": (100.0, 250.0),
    "cash": (50.0, 20.0),
    "ppe_net": (500.0, 300.0),
    "retained_earnings": (-200.0, -400.0),
    "operating_income": (-60.0, -150.0),
    "equity": (100.0, -100.0),
}


# --------------------------------------------------------------------------- #
# Ohlson O-score
# --------------------------------------------------------------------------- #


def test_ohlson_clean_low_probability():
    # Hand computation at t=2023 (prior NI = 120):
    #   SIZE=ln(1050)=6.9565454, TLTA=400/1050=.3809524, WCTA=300/1050=.2857143,
    #   CLCA=200/500=.4, NITA=150/1050=.1428571, FUTL=(150+50)/400=.5,
    #   INTWO=0, OENEG=0, CHIN=(150-120)/270=.1111111.
    #   O = -1.32 -0.407*SIZE +6.03*TLTA -1.43*WCTA +0.0757*CLCA -2.37*NITA
    #       -1.83*FUTL +0.285*0 -1.72*0 -0.521*CHIN = -3.5439229
    #   P = 1/(1+exp(3.5439229)) = 0.0280881
    res = compute_ohlson_o_score(_two_year(CLEAN), {})
    assert res is not None
    assert res.value == pytest.approx(-3.5439229, abs=1e-4)
    assert res.detail["probability"] == pytest.approx(0.0280881, abs=1e-5)
    assert res.detail["zone"] == SAFE
    assert res.values_used["INTWO"] == 0.0
    assert res.values_used["OENEG"] == 0.0
    assert res.input_tags and res.input_accessions


def test_ohlson_stressed_high_probability():
    # At t=2023 (prior NI = -50):
    #   SIZE=ln(1200)=7.0900769, TLTA=1300/1200=1.0833333, WCTA=-350/1200=-.2916667,
    #   CLCA=600/250=2.4, NITA=-100/1200=-.0833333, FUTL=(-100+40)/1300=-.0461538,
    #   INTWO=1, OENEG=1, CHIN=(-100+50)/150=-.3333333.
    #   O = 1.9463136 ; P = 1/(1+exp(-1.9463136)) = 0.8750
    res = compute_ohlson_o_score(_two_year(STRESSED), {})
    assert res is not None
    assert res.value == pytest.approx(1.9463136, abs=1e-4)
    assert res.detail["probability"] == pytest.approx(0.8750, abs=1e-3)
    assert res.detail["probability"] > 0.5
    assert res.detail["zone"] == DISTRESS
    assert res.values_used["INTWO"] == 1.0  # negative income both years
    assert res.values_used["OENEG"] == 1.0  # liabilities exceed assets


def test_ohlson_needs_two_years_and_guards():
    # Single year -> no prior net income for CHIN/INTWO -> None.
    assert compute_ohlson_o_score(_one_year({
        "total_assets": 1050.0, "total_liabilities": 400.0,
        "current_assets": 500.0, "current_liabilities": 200.0,
        "net_income": 150.0, "depreciation_amortization": 50.0,
    }), {}) is None
    # Non-positive total assets -> None (ln undefined / bogus ratios).
    bad = dict(CLEAN)
    bad["total_assets"] = (1000.0, 0.0)
    assert compute_ohlson_o_score(_two_year(bad), {}) is None


# --------------------------------------------------------------------------- #
# Zmijewski score
# --------------------------------------------------------------------------- #


def test_zmijewski_clean_low_probability():
    # At t=2023: ROA=150/1050=.1428571, TLTA=400/1050=.3809524, CACL=500/200=2.5.
    #   X = -4.3 -4.5*ROA +5.7*TLTA -0.004*CACL = -2.7814286 ; P=Phi(X) ~ 0.0027.
    res = compute_zmijewski_score(_two_year(CLEAN), {})
    assert res is not None
    assert res.value == pytest.approx(-2.7814286, abs=1e-4)
    assert res.detail["probability"] < 0.05
    assert res.detail["zone"] == SAFE


def test_zmijewski_stressed_high_probability():
    # At t=2023: ROA=-100/1200=-.0833333, TLTA=1300/1200=1.0833333,
    #   CACL=250/600=.4166667. X = 2.2483333 ; P=Phi(X) ~ 0.9877 -> distress.
    res = compute_zmijewski_score(_two_year(STRESSED), {})
    assert res is not None
    assert res.value == pytest.approx(2.2483333, abs=1e-4)
    assert res.detail["probability"] > 0.5
    assert res.detail["zone"] == DISTRESS


def test_zmijewski_phi_known_value():
    # Phi(0) = 0.5. Construct X exactly 0: NI=0 (ROA=0), CACL=1 (-0.004), and
    # TLTA chosen so 5.7*TLTA = 4.304 -> TL/TA = 4304/5700; with 5.7/5700 = 1/1000
    # the leverage term is exactly 4.304, so X = -4.3 + 4.304 - 0.004 = 0.
    res = compute_zmijewski_score(_one_year({
        "net_income": 0.0, "total_assets": 5700.0, "total_liabilities": 4304.0,
        "current_assets": 100.0, "current_liabilities": 100.0,
    }), {})
    assert res is not None
    assert res.value == pytest.approx(0.0, abs=1e-9)
    assert res.detail["probability"] == pytest.approx(0.5, abs=1e-9)
    # Independent identity check of the CDF used.
    assert 0.5 * (1.0 + math.erf(0.0 / math.sqrt(2.0))) == pytest.approx(0.5)


def test_zmijewski_guards():
    assert compute_zmijewski_score(_one_year({
        "net_income": 100.0, "total_assets": 0.0, "total_liabilities": 400.0,
        "current_assets": 500.0, "current_liabilities": 200.0,
    }), {}) is None  # TA <= 0


# --------------------------------------------------------------------------- #
# Montier C-score
# --------------------------------------------------------------------------- #


def test_montier_clean_zero():
    res = compute_montier_c_score(_two_year(CLEAN), {})
    assert res is not None
    assert res.value == 0.0
    assert res.detail["flags"] == {
        "growing_gap_ni_ocf": 0,
        "dso_rising": 0,
        "dsi_rising": 0,
        "other_current_assets_rising": 0,
        "declining_depreciation": 0,
        "asset_growth_gt_10pct": 0,
    }
    assert res.detail["uncomputable"] == []
    assert res.detail["omitted"] == []
    assert res.detail["max"] == 6


def test_montier_stressed_four_or_more():
    # Fires: growing gap (accrual earnings up vs cash), DSO up (AR/rev .10->.25),
    # DSI up (inv/rev .10->.3125), declining depreciation (.1667->.1176), asset
    # growth 20% > 10%. Other-CA/rev falls -> that flag 0. C = 5.
    res = compute_montier_c_score(_two_year(STRESSED), {})
    assert res is not None
    assert res.value == 5.0
    assert res.value >= 4  # the "watch" cut
    flags = res.detail["flags"]
    assert flags["growing_gap_ni_ocf"] == 1
    assert flags["dso_rising"] == 1
    assert flags["dsi_rising"] == 1
    assert flags["declining_depreciation"] == 1
    assert flags["asset_growth_gt_10pct"] == 1
    assert flags["other_current_assets_rising"] == 0
    assert res.detail["omitted"] == []


def test_montier_no_inventory_scores_zero_not_uncomputable():
    spec = dict(CLEAN)
    del spec["inventory"]
    res = compute_montier_c_score(_two_year(spec), {})
    assert res is not None
    assert res.detail["flags"]["dsi_rising"] == 0
    assert "dsi_rising" not in res.detail["uncomputable"]
    # Other-CA needs inventory -> that flag is omitted (max drops to 5).
    assert "other_current_assets_rising" in res.detail["omitted"]
    assert res.detail["max"] == 5


def test_montier_needs_two_years():
    assert compute_montier_c_score(_one_year({
        "total_assets": 1050.0, "net_income": 150.0, "operating_cash_flow": 200.0,
    }), {}) is None


# --------------------------------------------------------------------------- #
# Panel in compute_quality_factors
# --------------------------------------------------------------------------- #


def test_distress_panel_agreement_stressed():
    qf = compute_quality_factors(
        _two_year(STRESSED), {}, bucket=INDUSTRIALS, sic="3500", market=None,
    )
    assert qf.factors["ohlson_o"].status == OK
    assert qf.factors["ohlson_o"].detail["zone"] == DISTRESS
    assert qf.factors["zmijewski"].status == OK
    assert qf.factors["zmijewski"].detail["zone"] == DISTRESS
    assert qf.factors["altman_z"].detail["zone"] == DISTRESS

    panel = qf.distress_panel
    assert panel["distress_count"] == 3
    assert panel["available_count"] == 3
    assert panel["models_agree"] is True
    assert panel["agreement"] == "unanimous"
    assert any("distress panel" in c.lower() for c in qf.caveats)


def test_distress_panel_clean_no_agreement():
    qf = compute_quality_factors(
        _two_year(CLEAN), {}, bucket=INDUSTRIALS, sic="3500", market=None,
    )
    panel = qf.distress_panel
    assert panel["distress_count"] == 0
    assert panel["available_count"] == 3
    assert panel["models_agree"] is False
    assert panel["agreement"] == "none"


def test_financial_bucket_gets_not_applicable():
    qf = compute_quality_factors(
        _two_year(CLEAN), {}, bucket=BANKING, sic="6022", market=None,
    )
    assert qf.metric_set == "financial"
    assert qf.factors["ohlson_o"].status == NOT_APPLICABLE
    assert qf.factors["zmijewski"].status == NOT_APPLICABLE
    # No industrial distress model is available -> panel says so.
    assert qf.distress_panel["available_count"] == 0
    assert qf.distress_panel["agreement"] == "no_models"


# --------------------------------------------------------------------------- #
# Stress-report folding
# --------------------------------------------------------------------------- #


def test_stress_report_folds_panel_and_montier():
    series = _two_year(STRESSED)
    derived = compute_derived_metrics(series)
    report = compute_stress_report(series, derived)

    fired = {key for key, _, _ in report.stress_flags}
    assert "montier_high" in fired  # C-score 5 >= 4
    assert "distress_model_agreement" in fired  # 3 models agree
    # Agreement across independent models tops the severity order.
    assert report.worst == "distress_model_agreement"

    agree_value = next(v for k, _, v in report.stress_flags
                       if k == "distress_model_agreement")
    assert agree_value == 3.0


def test_stress_report_clean_no_new_flags():
    series = _two_year(CLEAN)
    derived = compute_derived_metrics(series)
    report = compute_stress_report(series, derived)
    fired = {key for key, _, _ in report.stress_flags}
    assert "montier_high" not in fired
    assert "distress_model_agreement" not in fired
