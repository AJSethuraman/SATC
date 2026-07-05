"""Seam 1 — vintage summary, gross charge-off, loss triangle, roll matrix."""

import math

from popbench import contract, mapping, rolls, vintage
from popbench.engine import run_analysis


def _prep():
    from popbench import demo
    pop = demo.demo_population_full()
    props = mapping.propose(list(pop.columns))
    cols = [mapping.ColumnMap(p.header, p.field_id,
                              contract.UNIT_FRACTION if p.needs_unit else None)
            for p in props if p.field_id]
    m = mapping.confirm(cols)
    return run_analysis(pop, m).clean   # normalized: dpd_min present; dates parsed


def test_gross_charge_off_rate_both_bases():
    df = _prep()
    g = vintage.gross_charge_off_rate(df)
    assert g.co_count == 1 and math.isclose(g.co_dollars, 8000.0)   # L-103
    assert math.isclose(g.count_rate, 0.2)                          # 1/5
    assert math.isclose(g.dollar_rate, 8000.0 / 173000.0)
    assert "GROSS" in g.basis_note and "no recovery" in g.basis_note


def test_vintage_summary_by_year():
    df = _prep()
    rows = {r.vintage: r for r in vintage.vintage_summary(df, grain="year")}
    assert set(rows) == {"2021", "2022", "2023"}
    # 2021 = L-103 (charged off, its whole balance) -> cumulative gross loss 100%
    assert math.isclose(rows["2021"].cum_gross_loss_rate, 1.0)
    assert rows["2021"].co_count == 1
    # 2022 = L-102 + L-104, both currently >=90 DPD -> ever90 rate 100%, no CO
    assert rows["2022"].co_count == 0
    assert math.isclose(rows["2022"].ever90_balance_rate, 1.0)
    # 2023 = L-101 + L-105, neither >=90 DPD
    assert math.isclose(rows["2023"].ever90_balance_rate, 0.0)


def test_loss_triangle_positions_loss_by_mob():
    df = _prep()
    tri = vintage.loss_triangle(df, grain="year")
    # L-103: orig 2021-03, CO 2023-05 -> 26 MOB. So <=24 shows nothing, 36 shows all.
    assert math.isclose(tri.rows["2021"][24], 0.0)
    assert math.isclose(tri.rows["2021"][36], 1.0)


def test_roll_matrix_prior_to_current():
    df = _prep()
    rm = rolls.roll_matrix(df)
    # current prior -> L-101 stays current, L-105 rolls to 30-59 (count .5/.5).
    assert math.isclose(rm.count["current"]["current"], 0.5)
    assert math.isclose(rm.count["current"]["dpd_30_59"], 0.5)
    # dollar basis weights the big current-staying loan more (15k vs 5k).
    assert math.isclose(rm.dollar["current"]["current"], 0.75)
    # deterministic full rolls forward.
    assert math.isclose(rm.count["dpd_60_89"]["dpd_90_119"], 1.0)
    # prior label "120-179" bins to the finer canonical dpd_120_149 bucket.
    assert math.isclose(rm.count["dpd_120_149"]["dpd_180_plus"], 1.0)


def test_roll_matrix_absent_without_prior_bucket():
    import pandas as pd
    import pytest
    df = pd.DataFrame({"loan_id": ["a"], "current_balance": [1.0],
                       "dpd_bucket_canon": ["current"]})
    with pytest.raises(vintage.FeatureUnavailable):
        rolls.roll_matrix(df)   # no prior_dpd_bucket mapped
