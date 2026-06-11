"""Hand-computed correctness tests on a tiny toy panel.

Every expected value below was computed by hand from the toy fixture in
conftest.py, so these tests prove the metric definitions -- not just their
stability.
"""

from __future__ import annotations

import pandas as pd
import pytest

from ucpa.metrics.charge_offs import compute_charge_off_rates, compute_recovery_trends
from ucpa.metrics.delinquency import compute_delinquency_distribution
from ucpa.metrics.migration import compute_migration_matrix
from ucpa.metrics.utilization import compute_utilization_distribution
from ucpa.metrics.vintage import compute_vintage_curves

APPROX = dict(rel=1e-12, abs=1e-12)


def test_delinquency_distribution_toy(toy_tape: pd.DataFrame) -> None:
    result = compute_delinquency_distribution(toy_tape)
    # Latest month (2024-03) open rows: A1 CURRENT 100, A2 DPD60 200, A3 CURRENT 100.
    assert result.summary["total_accounts"] == 3
    assert result.summary["total_balance"] == pytest.approx(400.0, **APPROX)
    assert result.summary["dpd30plus_balance_rate"] == pytest.approx(200.0 / 400.0, **APPROX)
    assert result.summary["dpd90plus_balance_rate"] == pytest.approx(0.0, **APPROX)
    assert result.summary["dpd30plus_account_rate"] == pytest.approx(1.0 / 3.0, **APPROX)
    dist = result.tables["distribution"].set_index("bucket")
    assert dist.loc["DPD60", "accounts"] == 1
    assert dist.loc["CURRENT", "balance"] == pytest.approx(200.0, **APPROX)


def test_migration_matrix_toy(toy_tape: pd.DataFrame) -> None:
    result = compute_migration_matrix(toy_tape)
    counts = result.tables["counts"].set_index("from_bucket")
    # Month1->2: A1 C->C, A2 C->D30, A3 D30->C, A4 D120->CO.
    # Month2->3: A1 C->C, A2 D30->D60, A3 C->C. (A4 in CO at t: excluded.)
    assert counts.loc["CURRENT", "CURRENT"] == 3
    assert counts.loc["CURRENT", "DPD30"] == 1
    assert counts.loc["DPD30", "CURRENT"] == 1
    assert counts.loc["DPD30", "DPD60"] == 1
    assert counts.loc["DPD120", "CO"] == 1
    assert result.summary["transitions_observed"] == 7

    row_pct = result.tables["row_pct"].set_index("from_bucket")
    assert row_pct.loc["CURRENT", "DPD30"] == pytest.approx(0.25, **APPROX)
    assert row_pct.loc["DPD120", "CO"] == pytest.approx(1.0, **APPROX)

    # Dollar-weighted: CURRENT rows at t are A1 m1 (100), A2 m1 (200),
    # A1 m2 (100), A3 m2 (100) = 500 total; A2's 200 rolled to DPD30.
    assert result.summary["current_to_dpd30"] == pytest.approx(200.0 / 500.0, **APPROX)
    # From DPD30 at t: A3 300 cured, A2 200 rolled -> cure 300/500, roll 200/500.
    assert result.summary["dpd30_cure_rate"] == pytest.approx(300.0 / 500.0, **APPROX)
    assert result.summary["dpd30_to_dpd60"] == pytest.approx(200.0 / 500.0, **APPROX)


def test_charge_off_rates_toy(toy_tape: pd.DataFrame) -> None:
    result = compute_charge_off_rates(toy_tape)
    # Open balances: m1 = 100+200+300+400 = 1000; m2 = 400; m3 = 400.
    # Gross CO = 400 in m2. Window = 3 months -> annualizer 12/3 = 4.
    avg_balance = (1000.0 + 400.0 + 400.0) / 3.0
    assert result.summary["gross_co_rate_t12"] == pytest.approx(400.0 * 4.0 / avg_balance, **APPROX)
    # Net: recoveries of 50 in m3.
    assert result.summary["net_co_rate_t12"] == pytest.approx(350.0 * 4.0 / avg_balance, **APPROX)
    monthly = result.tables["monthly"]
    assert monthly["gross_charge_offs"].tolist() == [0.0, 400.0, 0.0]
    assert monthly["recoveries"].tolist() == [0.0, 0.0, 50.0]


def test_recovery_trends_toy(toy_tape: pd.DataFrame) -> None:
    result = compute_recovery_trends(toy_tape)
    assert result.summary["cumulative_recovery_rate"] == pytest.approx(50.0 / 400.0, **APPROX)
    assert result.summary["recovery_amount_total"] == pytest.approx(50.0, **APPROX)


def test_vintage_curves_toy(toy_tape: pd.DataFrame) -> None:
    result = compute_vintage_curves(toy_tape)
    curves = result.tables["curves"].set_index("months_on_book")
    # A4: originated 2023-06 (cohort 2023Q2, line 800), charged off 2024-02
    # at MOB 8 for $400 -> cumulative loss 50% from MOB 8 onward.
    assert curves.loc[7, "2023Q2"] == pytest.approx(0.0, **APPROX)
    assert curves.loc[8, "2023Q2"] == pytest.approx(0.5, **APPROX)
    assert curves.loc[9, "2023Q2"] == pytest.approx(0.5, **APPROX)
    # 2023Q4 cohort (A1-A3, line 3000) has no losses.
    assert curves.loc[5, "2023Q4"] == pytest.approx(0.0, **APPROX)
    summary = result.tables["cohort_summary"].set_index("cohort")
    assert summary.loc["2023Q2", "orig_credit_line"] == pytest.approx(800.0, **APPROX)
    assert summary.loc["2023Q2", "cum_loss_latest"] == pytest.approx(0.5, **APPROX)


def test_utilization_distribution_toy(toy_tape: pd.DataFrame) -> None:
    result = compute_utilization_distribution(toy_tape)
    # Latest month open: A1 100/1000, A2 200/1000, A3 100/1000.
    assert result.summary["portfolio_utilization"] == pytest.approx(400.0 / 3000.0, **APPROX)
    assert result.summary["high_util_balance_share"] == pytest.approx(0.0, **APPROX)
    assert result.summary["open_to_buy_total"] == pytest.approx(2600.0, **APPROX)
