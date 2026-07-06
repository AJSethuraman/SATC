"""Seam 1 — the pandas engine vs hand-tallied values (the correctness seam)."""

import math

import pandas as pd

from popbench import metrics
from popbench.engine import run_analysis
from popbench import demo, mapping


def _confirmed(headers):
    proposals = mapping.propose(headers)
    return mapping.confirm([mapping.ColumnMap(p.header, p.field_id)
                            for p in proposals if p.field_id])


def test_weighted_average_both_bases_hand_tallied():
    df = pd.DataFrame({
        "current_balance": [10000.0, 20000.0, 30000.0, 40000.0],
        "fico_orig": [720.0, 680.0, 760.0, 700.0],
    })
    res = metrics.weighted_average(df, "fico_orig")
    # dollar: (10k*720 + 20k*680 + 30k*760 + 40k*700)/100k = 716.0
    assert math.isclose(res.dollar_weighted, 716.0)
    # count: (720+680+760+700)/4 = 715.0
    assert math.isclose(res.count_weighted, 715.0)
    assert res.n == 4
    assert math.isclose(res.coverage_dollars, 100000.0)


def test_dollar_and_count_can_diverge():
    # One big low-score loan drags the dollar basis below the count basis.
    df = pd.DataFrame({
        "current_balance": [1000.0, 99000.0],
        "fico_orig": [800.0, 600.0],
    })
    res = metrics.weighted_average(df, "fico_orig")
    assert math.isclose(res.dollar_weighted, (1000*800 + 99000*600) / 100000)
    assert math.isclose(res.count_weighted, 700.0)
    assert res.dollar_weighted < res.count_weighted  # the reason both bases ship


def test_empty_attribute_returns_none_not_crash():
    df = pd.DataFrame({"current_balance": [1000.0], "fico_orig": [float("nan")]})
    res = metrics.weighted_average(df, "fico_orig")
    assert res.dollar_weighted is None and res.count_weighted is None
    assert res.n == 0


def test_run_analysis_on_demo_population():
    pop = demo.demo_population()
    m = _confirmed(list(pop.columns))
    result = run_analysis(pop, m, attributes=["fico_orig"])
    assert result.population["count"] == 4
    assert math.isclose(result.population["total_balance"], 100000.0)
    (fico,) = result.wa
    assert math.isclose(fico.dollar_weighted, 716.0)
    assert math.isclose(fico.count_weighted, 715.0)
