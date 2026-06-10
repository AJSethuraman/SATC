import math

from satc_edgar.metrics import (
    ALL_METRICS,
    compute_metrics,
    extract_annual_financials,
)
from tests.fixtures import make_companyfacts


def _latest(cik=111, **kw):
    facts = make_companyfacts(cik, "Test Co", [2018, 2019, 2020, 2021, 2022], **kw)
    recs = extract_annual_financials(facts, cik, "Test Co", "TST")
    return recs, recs[-1]


def test_extracts_all_years():
    recs, _ = _latest(revenue=1000.0)
    assert [r.fiscal_year for r in recs] == [2018, 2019, 2020, 2021, 2022]


def test_ebitda_reconstruction_oi_plus_da():
    recs, last = _latest(revenue=1000.0, op_margin=0.05, da_frac=0.02)
    # EBITDA = operating income + D&A = 50 + 20 = 70
    assert last.ebitda_method == "oi+da"
    assert math.isclose(last.ebitda, 1000 * 0.05 + 1000 * 0.02, rel_tol=1e-9)


def test_ebitda_excluded_when_da_missing():
    recs, last = _latest(revenue=1000.0, drop_da=True)
    assert last.ebitda is None
    assert any("missing_D&A" in n for n in last.notes)
    m = compute_metrics(last)
    # EBITDA-based metrics must be None, not imputed.
    assert m["debt_to_ebitda"] is None
    assert m["ebitda_margin"] is None
    # Non-EBITDA metrics still compute.
    assert m["current_ratio"] is not None
    assert m["net_margin"] is not None


def test_margin_values():
    recs, last = _latest(revenue=1000.0, gross_margin=0.18, op_margin=0.05)
    m = compute_metrics(last)
    assert math.isclose(m["gross_margin"], 0.18, rel_tol=1e-9)
    assert math.isclose(m["operating_margin"], 0.05, rel_tol=1e-9)


def test_total_debt_components():
    recs, last = _latest(revenue=1000.0, debt=1500.0)
    # components method: 1500 noncurrent + 150 current = 1650
    assert last.debt_method == "components"
    assert math.isclose(last.total_debt, 1650.0, rel_tol=1e-9)


def test_no_silent_imputation_on_zero_denominator():
    recs, last = _latest(revenue=1000.0)
    last.interest_expense = 0.0
    m = compute_metrics(last)
    assert m["ebitda_to_interest"] is None  # div by zero -> None


def test_cash_conversion_cycle_composes():
    recs, last = _latest(revenue=1000.0)
    m = compute_metrics(last)
    assert m["cash_conversion_cycle"] is not None
    assert math.isclose(
        m["cash_conversion_cycle"],
        m["days_sales_outstanding"] + m["days_inventory"] - m["days_payable"],
        rel_tol=1e-9,
    )


def test_all_metric_keys_present():
    recs, last = _latest(revenue=1000.0)
    m = compute_metrics(last)
    assert set(m.keys()) == set(ALL_METRICS)
