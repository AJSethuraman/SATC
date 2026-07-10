"""Threshold/config layer tests: merging, evaluation, severity bands."""

from __future__ import annotations

import json

import pytest

from ucpa.metrics.results import MetricResult
from ucpa.products.base import ThresholdCheck
from ucpa.thresholds import (
    deep_merge,
    evaluate_checks,
    get_limit,
    load_default_thresholds,
    load_thresholds,
)


def _result(**summary) -> MetricResult:
    return MetricResult(metric="m", status="computed", summary=summary)


CHECK_MAX = ThresholdCheck("credit_card.delinquency.max_dpd30plus_balance_rate", "rate", "max", "30+ rate")
CONFIG = {"credit_card": {"delinquency": {"max_dpd30plus_balance_rate": 0.035}}}


def test_defaults_load_and_resolve() -> None:
    config = load_default_thresholds()
    assert get_limit(config, "credit_card.delinquency.max_dpd30plus_balance_rate") == 0.035
    assert get_limit(config, "credit_card.nope.missing") is None


def test_deep_merge_overrides_leaf_only() -> None:
    merged = deep_merge(
        load_default_thresholds(),
        {"credit_card": {"delinquency": {"max_dpd30plus_balance_rate": 0.999}}},
    )
    assert get_limit(merged, "credit_card.delinquency.max_dpd30plus_balance_rate") == 0.999
    # Sibling limits untouched by the override.
    assert get_limit(merged, "credit_card.charge_offs.max_gross_co_rate_t12") == 0.055


def test_client_config_file_override(tmp_path) -> None:
    client = tmp_path / "client.json"
    client.write_text(json.dumps({"credit_card": {"vintage": {"max_cum_loss_mob12": 0.05}}}))
    config = load_thresholds(client)
    assert get_limit(config, "credit_card.vintage.max_cum_loss_mob12") == 0.05


@pytest.mark.parametrize(
    "observed,expected_severity",
    [
        (0.040, "EXCEPTION"),  # breach
        (0.034, "WATCH"),      # within 10% under the max
        (0.020, None),         # comfortably inside
    ],
)
def test_max_direction(observed: float, expected_severity: str | None) -> None:
    exceptions = evaluate_checks(_result(rate=observed), [CHECK_MAX], CONFIG)
    if expected_severity is None:
        assert exceptions == []
    else:
        assert len(exceptions) == 1
        assert exceptions[0].severity == expected_severity


def test_min_direction() -> None:
    check = ThresholdCheck("credit_card.recoveries.min_recovery_rate_t12", "rate", "min", "rec rate")
    config = {"credit_card": {"recoveries": {"min_recovery_rate_t12": 0.08}}}
    assert evaluate_checks(_result(rate=0.05), [check], config)[0].severity == "EXCEPTION"
    assert evaluate_checks(_result(rate=0.085), [check], config)[0].severity == "WATCH"
    assert evaluate_checks(_result(rate=0.20), [check], config) == []


def test_missing_summary_value_skipped() -> None:
    assert evaluate_checks(_result(rate=None), [CHECK_MAX], CONFIG) == []
    assert evaluate_checks(_result(), [CHECK_MAX], CONFIG) == []


def test_missing_limit_skipped() -> None:
    assert evaluate_checks(_result(rate=0.99), [CHECK_MAX], {}) == []
