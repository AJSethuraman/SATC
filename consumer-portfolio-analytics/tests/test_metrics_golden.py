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
    assert float(small_tape["balance"].sum()) == GOLDEN(20435432.88, abs=1e-6)


def test_golden_delinquency(review) -> None:
    s = _summary(review, "delinquency_distribution")
    assert s["total_accounts"] == 488
    assert s["total_balance"] == GOLDEN(1120830.72, abs=1e-6)
    assert s["dpd30plus_balance_rate"] == GOLDEN(0.023123598896361442, rel=1e-12)
    assert s["dpd90plus_balance_rate"] == GOLDEN(0.004857709467492112, rel=1e-12)


def test_golden_migration(review) -> None:
    s = _summary(review, "migration_matrix")
    assert s["transitions_observed"] == 10197
    assert s["current_to_dpd30"] == GOLDEN(0.0069747398134039065, rel=1e-12)
    assert s["dpd30_to_dpd60"] == GOLDEN(0.343632974725284, rel=1e-12)
    assert s["dpd30_cure_rate"] == GOLDEN(0.4587476556058007, rel=1e-12)


def test_golden_vintage(review) -> None:
    s = _summary(review, "vintage_curves")
    assert s["cohorts"] == 10
    assert s["max_cum_loss_mob12"] == GOLDEN(0.008378405572755418, rel=1e-12)
    assert s["worst_cohort_mob12"] == "2022Q4"


def test_golden_concentration(review) -> None:
    s = _summary(review, "concentration")
    assert s["subprime_balance_share"] == GOLDEN(0.08336679958236691, rel=1e-12)
    assert s["below_prime_balance_share"] == GOLDEN(0.2801447751182266, rel=1e-12)
    assert s["score_band_hhi"] == GOLDEN(0.3430795710979177, rel=1e-12)
    assert s["max_vintage_year_share"] == GOLDEN(0.4610391210547834, rel=1e-12)


def test_golden_charge_offs(review) -> None:
    s = _summary(review, "charge_off_rates")
    assert s["gross_co_rate_t12"] == GOLDEN(0.04628384146944868, rel=1e-12)
    assert s["net_co_rate_t12"] == GOLDEN(0.042555079768690905, rel=1e-12)
    assert s["gross_co_amount_t12"] == GOLDEN(46344.27, abs=1e-6)


def test_golden_recoveries(review) -> None:
    s = _summary(review, "recovery_trends")
    assert s["cumulative_recovery_rate"] == GOLDEN(0.07513085312555401, rel=1e-12)
    assert s["recovery_rate_t12"] == GOLDEN(0.08056292611794294, rel=1e-12)


def test_golden_utilization(review) -> None:
    s = _summary(review, "utilization_distribution")
    assert s["portfolio_utilization"] == GOLDEN(0.24688024707330528, rel=1e-12)
    assert s["high_util_balance_share"] == GOLDEN(0.170243344151024, rel=1e-12)


def test_golden_line_management(review) -> None:
    s = _summary(review, "line_management")
    assert s["line_increase_events"] == 14
    assert s["exposure_added_total"] == GOLDEN(15300.0, abs=1e-9)
    assert s["increase_share_below_prime"] == GOLDEN(0.6274509803921569, rel=1e-12)


def test_golden_exceptions(review) -> None:
    flags = [(e.severity, e.metric, e.summary_key) for e in review.exceptions]
    assert flags == [
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
