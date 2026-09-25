"""The arithmetic, checked by hand on a six-loan book, and the plant found in
the synthetic one."""

import pytest

from conftest import cube, row, table
from origination_cube import engine, synth
from origination_cube import config as cfgmod
from origination_cube.ingest import read_table


def test_rates_by_hand(book):
    res = engine.run(cube(), table(book))
    g = res.grids[0]
    # book: BAL 2000, GCO 150, bad balance 500
    assert res.total.rates["gco"].rate == pytest.approx(150 / 2000)
    assert res.total.rates["bad"].rate == pytest.approx(500 / 2000)
    low_a = g.cell("under 650", "A").rates["gco"]      # loans 1, 2
    assert low_a.num == 50 and low_a.den == 200 and low_a.units == 2
    assert low_a.rate == pytest.approx(0.25)
    assert low_a.vs_topline == pytest.approx(0.25 / 0.075)
    assert low_a.excess == pytest.approx(50 - 0.075 * 200)
    assert low_a.reading_topline == engine.WORSE


def test_vs_topline_is_share_of_losses_over_share_of_volume(book):
    res = engine.run(cube(), table(book))
    t = res.total.rates["gco"]
    for _, c in res.grids[0].inner():
        s = c.rates["gco"]
        if s.num:
            assert s.vs_topline == pytest.approx((s.num / t.num) / (s.den / t.den))


def test_median_benchmark_leaves_out_thin_cells(book):
    res = engine.run(cube(benchmark={"min_units": 2, "worse_at": 1.25, "better_at": 0.8}), table(book))
    g = res.grids[0]
    # cells with 2+ loans: under650/A (0.25), 650+/B (0/1200 = 0). Thin: 650+/A, under650/B.
    assert g.benchmarks["gco"] == pytest.approx(0.125)
    assert g.cell("under 650", "B").rates["gco"].reading_median == engine.THIN


def test_signed_values_pass_through(book):
    book.append(row(7, 700, "A", 100, 0, -30))       # a recovery, say (D47)
    res = engine.run(cube(), table(book))
    assert res.total.rates["gco"].num == 120


def test_missing_by_rule_gets_its_own_row_and_is_counted(book):
    book.append(row(7, -9999, "A", 100, 1, 40))
    res = engine.run(cube(missing={"SCORE": {"below": -1000}}), table(book))
    g = res.grids[0]
    assert engine.MISSING_RULE_LABEL in g.band_labels
    assert g.cell(engine.MISSING_RULE_LABEL, "A").rows == 1
    # the score is missing, but the loan's balance and losses are real: they stay in the rate
    assert res.total.rates["gco"].num == 190
    assert res.left_out["score_median"][("SCORE", "missing by rule")] == 1


def test_missing_values_list_applies_to_a_dimension(book):
    book.append(row(7, 600, "UNK", 100, 0, 0))
    res = engine.run(cube(missing={"CHAN": {"values": ["UNK"]}}), table(book))
    assert engine.MISSING_RULE_LABEL in res.grids[0].dim_labels


def test_the_tie_out_can_fail(book):
    """Check the checker: tamper with one cell and the tie-out must go red."""
    res = engine.run(cube(), table(book))
    g = res.grids[0]
    g.cell("under 650", "A").rates["gco"].num += 1
    with pytest.raises(engine.TieOutError, match="gco numerator"):
        engine.tie_out(g, res.total, res.measures, res.rows)


def test_the_tie_out_catches_a_dropped_row(book):
    res = engine.run(cube(), table(book))
    g = res.grids[0]
    del g.cells[("under 650", "B")]
    with pytest.raises(engine.TieOutError, match="rows"):
        engine.tie_out(g, res.total, res.measures, res.rows)


def test_the_plant_is_the_worst_pocket(tmp_path):
    cfg, data = synth.write(tmp_path, n=20000)
    res = engine.run(cfgmod.load(cfg), read_table(data))
    g = res.grids[0]
    for m in ("bad_rate", "gco_rate"):
        ranked = sorted(g.inner(), key=lambda kc: -kc[1].rates[m].excess)
        (band, chan), top = ranked[0]
        assert (band, chan) == ("under 620", "Broker")
        assert top.rates[m].vs_topline > 4
        assert top.rates[m].reading_topline == engine.WORSE
    # RANR has no plant: nothing in a populated cell reads worse
    for (b, d), c in g.inner():
        if c.rates["ranr_rate"].units >= 30:
            assert c.rates["ranr_rate"].reading_topline == engine.IN_LINE


def test_same_input_same_output(tmp_path):
    cfg, data = synth.write(tmp_path, n=2000)
    a = engine.run(cfgmod.load(cfg), read_table(data))
    b = engine.run(cfgmod.load(cfg), read_table(data))
    assert [(k, c.rates["gco_rate"].rate) for k, c in a.grids[0].cells.items()] == \
           [(k, c.rates["gco_rate"].rate) for k, c in b.grids[0].cells.items()]
