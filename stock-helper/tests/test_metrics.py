"""Derived metric calculations and trend helpers."""

from datetime import date

import pytest

from conftest import mk_series
from stock_helper.features.metrics import (
    compute_derived_metrics,
    trend_direction,
    yoy_change,
)

D = date


def test_gross_and_operating_margin():
    series = {
        "revenue": mk_series("revenue", [(D(2023, 12, 31), 100.0), (D(2024, 12, 31), 120.0)]),
        "cost_of_revenue": mk_series("cost_of_revenue", [(D(2023, 12, 31), 60.0), (D(2024, 12, 31), 66.0)]),
        "operating_income": mk_series("operating_income", [(D(2024, 12, 31), 30.0)]),
    }
    derived = compute_derived_metrics(series)
    assert derived["gross_margin"].points == [(D(2023, 12, 31), 0.4), (D(2024, 12, 31), 0.45)]
    assert derived["operating_margin"].latest == 0.25
    assert "revenue" in derived  # pass-through level


def test_fcf_and_accruals():
    series = {
        "net_income": mk_series("net_income", [(D(2024, 12, 31), 90.0)]),
        "operating_cash_flow": mk_series("operating_cash_flow", [(D(2024, 12, 31), 110.0)]),
        "capex": mk_series("capex", [(D(2024, 12, 31), 30.0)]),
        "total_assets": mk_series("total_assets", [(D(2024, 12, 31), 1000.0)]),
    }
    derived = compute_derived_metrics(series)
    assert derived["free_cash_flow"].latest == 80.0
    assert derived["accrual_proxy"].latest == pytest.approx(-0.02)
    assert derived["ocf_to_net_income"].latest == pytest.approx(110.0 / 90.0)


def test_total_debt_combines_long_and_short():
    series = {
        "long_term_debt": mk_series("long_term_debt", [(D(2024, 12, 31), 300.0)]),
        "short_term_debt": mk_series("short_term_debt", [(D(2024, 12, 31), 100.0)]),
        "total_assets": mk_series("total_assets", [(D(2024, 12, 31), 1000.0)]),
    }
    assert compute_derived_metrics(series)["debt_to_assets"].latest == pytest.approx(0.4)


def test_missing_inputs_omit_metric():
    derived = compute_derived_metrics(
        {"revenue": mk_series("revenue", [(D(2024, 12, 31), 100.0)])}
    )
    assert "gross_margin" not in derived
    assert "debt_to_assets" not in derived


def test_zero_denominator_skipped():
    series = {
        "operating_income": mk_series("operating_income", [(D(2024, 12, 31), 30.0)]),
        "interest_expense": mk_series("interest_expense", [(D(2024, 12, 31), 0.0)]),
    }
    assert "interest_coverage" not in compute_derived_metrics(series)


def test_provenance_carried_into_derived():
    series = {
        "revenue": mk_series("revenue", [(D(2024, 12, 31), 100.0)], tag="Revenues"),
        "operating_income": mk_series("operating_income", [(D(2024, 12, 31), 25.0)], tag="OperatingIncomeLoss"),
    }
    metric = compute_derived_metrics(series)["operating_margin"]
    assert metric.input_tags == ["OperatingIncomeLoss", "Revenues"]
    assert metric.input_accessions == ["acc-2024"]


def test_yoy_change():
    assert yoy_change([100.0, 110.0]) == pytest.approx(0.10)
    assert yoy_change([100.0]) is None
    assert yoy_change([0.0, 50.0]) is None


def test_trend_direction():
    assert trend_direction([1.0, 1.1, 1.2]) == "improving"
    assert trend_direction([1.2, 1.1, 1.0]) == "deteriorating"
    assert trend_direction([1.0, 1.001, 0.999]) == "stable"
    assert trend_direction([1.0, 1.5, 1.0]) == "mixed"
    assert trend_direction([1.0]) == ""
