"""Forensic / earnings-manipulation + balance-sheet stress calculation core.

All offline: two-year series are built with conftest.mk_series; derived metrics
come from compute_derived_metrics. No DB, no network, no price fetch.

The clean-company M-score is hand-computed in test_beneish_clean_company with
the exact expected value and a tight tolerance.
"""

from datetime import date

import pytest

from conftest import mk_series
from stock_helper.features.metrics import compute_derived_metrics
from stock_helper.valuation.forensics import (
    compute_beneish_m_score,
    compute_stress_report,
)

# Two consecutive fiscal year-ends: t-1 (prev) and t (curr).
D_PREV = date(2022, 12, 31)
D_CURR = date(2023, 12, 31)


def _two_year(spec: dict[str, tuple[float, float]]) -> dict:
    """Build a series dict from key -> (prev_value, curr_value)."""
    return {
        key: mk_series(key, [(D_PREV, prev), (D_CURR, curr)])
        for key, (prev, curr) in spec.items()
    }


# A stable company: every Beneish index is exactly 1.0 (proportions identical
# across the two years) except TATA, which is (NI - OCF)/assets = (90-100)/1000.
_CLEAN = {
    "revenue": (1000.0, 1000.0),
    "cost_of_revenue": (600.0, 600.0),
    "accounts_receivable": (100.0, 100.0),
    "current_assets": (300.0, 300.0),
    "ppe_net": (400.0, 400.0),
    "total_assets": (1000.0, 1000.0),
    "depreciation_amortization": (100.0, 100.0),
    "sga_expense": (150.0, 150.0),
    "current_liabilities": (200.0, 200.0),
    "long_term_debt": (300.0, 300.0),
    "net_income": (90.0, 90.0),
    "operating_cash_flow": (100.0, 100.0),
    "operating_income": (250.0, 250.0),
    "inventory": (100.0, 100.0),
}

# Hand computation (all indices = 1 except TATA = -0.01):
#   coeff-weighted sum of the seven unit indices
#     = 0.920 + 0.528 + 0.404 + 0.892 + 0.115 - 0.172 - 0.327 = 2.360
#   TATA term = 4.679 * (-0.01) = -0.04679
#   M = -4.84 + 2.360 - 0.04679 = -2.52679
_CLEAN_M = -2.52679


# --------------------------------------------------------------------------- #
# Beneish M-score
# --------------------------------------------------------------------------- #


def test_beneish_clean_company():
    res = compute_beneish_m_score(_two_year(_CLEAN))
    assert res is not None

    # Every index is exactly 1.0 by construction, TATA is -0.01.
    for name in ("DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI"):
        assert res.indices[name] == pytest.approx(1.0), name
    assert res.indices["TATA"] == pytest.approx(-0.01)

    # Hand-computed M within a tight band, and in the non-manipulator range.
    assert res.m_score == pytest.approx(_CLEAN_M, abs=1e-4)
    assert -2.8 < res.m_score < -2.4
    assert res.flag is False

    # Provenance carried.
    assert res.period_ends == {"t": D_CURR, "t_minus_1": D_PREV}
    assert res.input_tags
    assert res.input_accessions
    assert res.formula.startswith("M = -4.84")


def test_beneish_manipulator():
    # Bump receivables (DSRI) and accruals (TATA); everything else stays clean.
    spec = dict(_CLEAN)
    spec["accounts_receivable"] = (100.0, 400.0)  # DSRI: (400/1000)/(100/1000) = 4.0
    spec["net_income"] = (90.0, 200.0)
    spec["operating_cash_flow"] = (100.0, -100.0)  # TATA: (200-(-100))/1000 = 0.3

    res = compute_beneish_m_score(spec_series := _two_year(spec))
    assert res is not None

    # The two intended indices moved; the rest are still ~1.
    assert res.indices["DSRI"] == pytest.approx(4.0)
    assert res.indices["TATA"] == pytest.approx(0.3)
    assert res.indices["GMI"] == pytest.approx(1.0)
    assert res.indices["SGI"] == pytest.approx(1.0)

    # M = -4.84 + 0.920*4 + (0.528+0.404+0.892+0.115-0.172-0.327) + 4.679*0.3
    #   = -4.84 + 3.68 + 1.44 + 1.4037 = 1.6837
    assert res.m_score == pytest.approx(1.6837, abs=1e-4)
    assert res.m_score > -1.78
    assert res.flag is True
    # sanity: the series really has two years
    assert len(spec_series["revenue"].points) == 2


def test_beneish_missing_year():
    # Only one fiscal year available -> cannot form t vs t-1 -> None.
    one_year = {key: mk_series(key, [(D_CURR, prev)]) for key, (prev, _) in _CLEAN.items()}
    assert compute_beneish_m_score(one_year) is None


def test_beneish_missing_metric():
    # Drop a required metric entirely -> None (UNAVAILABLE), never a partial score.
    spec = dict(_CLEAN)
    del spec["sga_expense"]
    assert compute_beneish_m_score(_two_year(spec)) is None


def test_beneish_zero_denominator_safe():
    # Prior-year sales = 0 -> any index dividing by prior sales explodes.
    # Must NOT raise; affected indices are None and M is unavailable.
    spec = dict(_CLEAN)
    spec["revenue"] = (0.0, 1000.0)

    res = compute_beneish_m_score(_two_year(spec))
    assert res is not None  # a result object, not an exception
    assert res.indices["SGI"] is None  # Sales_t / Sales_{t-1} -> None
    assert res.indices["DSRI"] is None  # AR_{t-1}/Sales_{t-1} -> None
    assert res.m_score is None  # composite marked unavailable
    assert res.flag is False
    assert any("unavailable" in c.lower() for c in res.caveats)


# --------------------------------------------------------------------------- #
# Stress report
# --------------------------------------------------------------------------- #


def test_stress_report_counts():
    # Negative OCF with positive NI, receivables blowout, rising leverage, and a
    # margin collapse. Inventory is flat (no bloat) -> six of seven flags fire.
    spec = dict(_CLEAN)
    spec["accounts_receivable"] = (100.0, 400.0)  # receivables_outgrowing_sales
    spec["net_income"] = (90.0, 200.0)
    spec["operating_cash_flow"] = (100.0, -100.0)  # high_accruals + ocf_ni_divergence
    spec["long_term_debt"] = (300.0, 500.0)  # debt/assets 0.30 -> 0.50 -> leverage_spike
    spec["operating_income"] = (250.0, 100.0)  # op margin 0.25 -> 0.10 -> margin_collapse

    series = _two_year(spec)
    derived = compute_derived_metrics(series)
    report = compute_stress_report(series, derived)

    fired = {key for key, _, _ in report.stress_flags}
    assert fired == {
        "beneish_flag",
        "high_accruals",
        "ocf_ni_divergence",
        "receivables_outgrowing_sales",
        "leverage_spike",
        "margin_collapse",
    }
    assert "inventory_bloat" not in fired
    assert report.flag_count == 6
    assert report.worst == "beneish_flag"  # top of the severity order
    assert report.m_score is not None and report.m_score > -1.78

    # Each flag carries a numeric value and a reason string.
    for _key, reason, value in report.stress_flags:
        assert isinstance(reason, str) and reason
        assert isinstance(value, float)

    # Not-an-accusation framing is explicit.
    assert any("not an accusation" in c.lower() for c in report.caveats)


def test_stress_report_clean():
    series = _two_year(_CLEAN)
    derived = compute_derived_metrics(series)
    report = compute_stress_report(series, derived)

    assert report.stress_flags == []
    assert report.flag_count == 0
    assert report.worst is None
    assert report.m_score == pytest.approx(_CLEAN_M, abs=1e-4)
