"""Golden-number stability tests: same seed => bit-identical metric outputs.

The expected values below were captured from the engine on the small seeded
fixture (seed 42, 500 accounts, 36 months).  Any change to these numbers
means either the generator or a metric definition changed -- both must be
deliberate, reviewed events, never drift.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ucpa.engine import run_review
from ucpa.products import CreditCardModule

GOLDEN = pytest.approx


@pytest.fixture(scope="module")
def review(small_tape: pd.DataFrame):
    return run_review(small_tape, CreditCardModule())


def _summary(review, metric: str) -> dict:
    result = review.result_for(metric)
    assert result is not None
    return result.summary


def test_tape_checksum(small_tape: pd.DataFrame) -> None:
    assert len(small_tape) == 10767
    assert float(small_tape["balance"].sum()) == GOLDEN(20442780.10, abs=1e-6)


def test_golden_delinquency(review) -> None:
    s = _summary(review, "delinquency_distribution")
    assert s["total_accounts"] == 490
    assert s["total_balance"] == GOLDEN(1121848.44, abs=1e-6)
    assert s["dpd30plus_balance_rate"] == GOLDEN(0.010977873267800774, rel=1e-12)
    assert s["dpd90plus_balance_rate"] == GOLDEN(0.0019097410341810523, rel=1e-12)


def test_golden_migration(review) -> None:
    s = _summary(review, "migration_matrix")
    assert s["transitions_observed"] == 10205
    assert s["current_to_dpd30"] == GOLDEN(0.00632954845704187, rel=1e-12)
    assert s["dpd30_to_dpd60"] == GOLDEN(0.3392131362405438, rel=1e-12)
    assert s["dpd30_cure_rate"] == GOLDEN(0.45522737360254506, rel=1e-12)


def test_golden_vintage(review) -> None:
    s = _summary(review, "vintage_curves")
    assert s["cohorts"] == 10
    assert s["max_cum_loss_mob12"] == GOLDEN(0.008378405572755418, rel=1e-12)
    assert s["worst_cohort_mob12"] == "2020Q4"


def test_golden_concentration(review) -> None:
    s = _summary(review, "concentration")
    assert s["subprime_balance_share"] == GOLDEN(0.08328845204794331, rel=1e-12)
    assert s["below_prime_balance_share"] == GOLDEN(0.27634590283871147, rel=1e-12)
    assert s["score_band_hhi"] == GOLDEN(0.3430957863589722, rel=1e-12)
    assert s["max_vintage_year_share"] == GOLDEN(0.4596053277927632, rel=1e-12)


def test_golden_charge_offs(review) -> None:
    s = _summary(review, "charge_off_rates")
    assert s["gross_co_rate_t12"] == GOLDEN(0.038211993171949794, rel=1e-12)
    assert s["net_co_rate_t12"] == GOLDEN(0.03502786489630878, rel=1e-12)
    assert s["gross_co_amount_t12"] == GOLDEN(38307.54, abs=1e-6)


def test_golden_recoveries(review) -> None:
    s = _summary(review, "recovery_trends")
    assert s["cumulative_recovery_rate"] == GOLDEN(0.07662554640971907, rel=1e-12)
    assert s["recovery_rate_t12"] == GOLDEN(0.0833279819064341, rel=1e-12)


def test_golden_utilization(review) -> None:
    s = _summary(review, "utilization_distribution")
    assert s["portfolio_utilization"] == GOLDEN(0.24643374389425696, rel=1e-12)
    assert s["high_util_balance_share"] == GOLDEN(0.17032971940487787, rel=1e-12)


def test_golden_line_management(review) -> None:
    s = _summary(review, "line_management")
    assert s["line_increase_events"] == 14
    assert s["exposure_added_total"] == GOLDEN(15300.0, abs=1e-9)
    assert s["increase_share_below_prime"] == GOLDEN(0.6274509803921569, rel=1e-12)


def test_golden_time_series(review) -> None:
    s = _summary(review, "portfolio_time_series")
    assert s["months_observed"] == 36
    assert s["latest_dpd30plus_rate"] == GOLDEN(0.010977873267800774, rel=1e-12)
    assert s["dpd30plus_yoy_delta"] == GOLDEN(-0.042294759644558, rel=1e-12)
    assert s["gross_co_rate_yoy_delta"] == GOLDEN(0.03214435037931211, rel=1e-12)
    assert s["balance_growth_12m"] == GOLDEN(0.4179716928546562, rel=1e-12)


def test_golden_exceptions(review) -> None:
    # The 36-month fixture is a young, still-ramping book: the YoY charge-off
    # and balance-growth trend checks legitimately fire on it.
    flags = [(e.severity, e.metric, e.summary_key) for e in review.exceptions]
    assert flags == [
        ("EXCEPTION", "portfolio_time_series", "gross_co_rate_yoy_delta"),
        ("EXCEPTION", "portfolio_time_series", "balance_growth_12m"),
        ("EXCEPTION", "concentration", "max_vintage_year_share"),
        ("WATCH", "recovery_trends", "recovery_rate_t12"),
        ("EXCEPTION", "line_management", "increase_share_below_prime"),
    ]


def test_rerun_is_identical(small_tape: pd.DataFrame, review) -> None:
    """Two engine runs over the same tape produce identical results."""
    second = run_review(small_tape, CreditCardModule())
    for first_result, second_result in zip(review.metric_results, second.metric_results):
        assert first_result.metric == second_result.metric
        assert first_result.status == second_result.status
        assert first_result.summary == second_result.summary
        assert set(first_result.tables) == set(second_result.tables)
        for name in first_result.tables:
            pd.testing.assert_frame_equal(
                first_result.tables[name], second_result.tables[name]
            )
