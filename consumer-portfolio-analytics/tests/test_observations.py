"""Observation-layer tests: determinism, severity rules, gap-aware skipping."""

from __future__ import annotations

import pandas as pd
import pytest

from ucpa.engine import run_review
from ucpa.generator import degrade_to_tier
from ucpa.metrics.results import MetricResult, ReviewResult, ThresholdException
from ucpa.observations import derive_observations
from ucpa.products import CreditCardModule
from ucpa.tier_detector import TierDetectionResult


@pytest.fixture(scope="module")
def review(small_tape: pd.DataFrame) -> ReviewResult:
    return run_review(small_tape, CreditCardModule())


def test_golden_observations(review: ReviewResult) -> None:
    """Same tape => identical observation list (IDs, severities, order)."""
    got = [(o.rule_id, o.severity) for o in review.observations]
    assert got == [
        ("OBS-DQ-01", "INFO"),
        ("OBS-DQ-02", "INFO"),
        ("OBS-MIG-01", "INFO"),
        ("OBS-MIG-02", "INFO"),
        ("OBS-CO-01", "INFO"),
        ("OBS-CO-02", "ELEVATED"),
        ("OBS-REC-01", "NOTABLE"),
        ("OBS-VIN-01", "ELEVATED"),
        ("OBS-CON-01", "ELEVATED"),
        ("OBS-UTL-01", "INFO"),
        ("OBS-LIN-01", "ELEVATED"),
        ("OBS-TS-01", "ELEVATED"),
        ("OBS-DAT-01", "INFO"),
    ]


def test_observations_embed_computed_numbers(review: ReviewResult) -> None:
    dq = review.result_for("delinquency_distribution").summary
    obs_dq = next(o for o in review.observations if o.rule_id == "OBS-DQ-01")
    assert f"{dq['dpd30plus_balance_rate']:.2%}" in obs_dq.text


def test_observations_are_deterministic(small_tape: pd.DataFrame, review: ReviewResult) -> None:
    second = run_review(small_tape, CreditCardModule())
    assert [(o.rule_id, o.severity, o.text) for o in second.observations] == [
        (o.rule_id, o.severity, o.text) for o in review.observations
    ]


def test_blocked_metrics_skip_rules(small_tape: pd.DataFrame) -> None:
    """A Tier 0 snapshot yields only the rules its data supports."""
    review0 = run_review(degrade_to_tier(small_tape, 0), CreditCardModule())
    ids = [o.rule_id for o in review0.observations]
    assert ids == ["OBS-DQ-01", "OBS-DAT-01"]
    data_obs = review0.observations[-1]
    assert data_obs.severity == "NOTABLE"  # gaps present
    assert "Tier 0" in data_obs.text


# ---------------------------------------------------------------------------
# Severity boundary tests on a hand-built minimal review.
# ---------------------------------------------------------------------------
def _mini_review(yoy_delta: float, exceptions: list[ThresholdException] | None = None) -> ReviewResult:
    return ReviewResult(
        product_type="CREDIT_CARD",
        tier_detection=TierDetectionResult(detected_tier=2, is_panel=True, field_presence={}),
        portfolio_summary={},
        metric_results=[
            MetricResult(
                metric="portfolio_time_series",
                status="computed",
                summary={"dpd30plus_yoy_delta": yoy_delta},
            )
        ],
        exceptions=exceptions or [],
        gaps=[],
        thresholds_used={},
    )


def _dq_trend_severity(yoy_delta: float, **kwargs) -> str:
    review = _mini_review(yoy_delta, **kwargs)
    obs = [o for o in derive_observations(review) if o.rule_id == "OBS-DQ-02"]
    assert len(obs) == 1
    return obs[0].severity


@pytest.mark.parametrize(
    "delta,expected",
    [
        (0.0060, "ELEVATED"),  # > +0.5pp YoY
        (0.0030, "NOTABLE"),   # > +0.1pp
        (0.0005, "INFO"),      # de minimis increase
        (-0.0040, "INFO"),     # improving
    ],
)
def test_dq_trend_severity_boundaries(delta: float, expected: str) -> None:
    assert _dq_trend_severity(delta) == expected


def test_threshold_breach_escalates_observation() -> None:
    """An EXCEPTION on the same summary key forces at least ELEVATED."""
    exc = ThresholdException(
        metric="portfolio_time_series",
        check="30+ DPD rate YoY change (pp)",
        summary_key="dpd30plus_yoy_delta",
        observed=0.0005,
        limit=0.0001,
        direction="max",
        severity="EXCEPTION",
        message="",
    )
    # Magnitude alone would be INFO; the breach escalates it.
    assert _dq_trend_severity(0.0005, exceptions=[exc]) == "ELEVATED"


def test_no_metrics_no_observations_crash() -> None:
    review = ReviewResult(
        product_type="CREDIT_CARD",
        tier_detection=TierDetectionResult(detected_tier=0, is_panel=False, field_presence={}),
        portfolio_summary={},
        metric_results=[],
        exceptions=[],
        gaps=[],
        thresholds_used={},
    )
    obs = derive_observations(review)
    assert [o.rule_id for o in obs] == ["OBS-DAT-01"]
