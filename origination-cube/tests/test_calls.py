"""The calls made on the Control tab, each applied, each checked by hand.
Walkthrough defect 1 (25 Sep 2026): five answers were required and then
silently dropped. Each test here fails if its answer stops being applied."""

import pytest

from conftest import BASE, cube, row, table
from origination_cube import engine


def bench(**kw):
    b = dict(BASE["benchmark"])
    b.update(kw)
    return b


def test_ranr_is_revenue_so_less_of_it_is_the_bleed(book):
    """The firm: 'RANR is a revenue metric ... bigger is better.' It is profit
    after losses (NEXT-GOAL 3.3), and still: less of it is the bleed."""
    for r, v in zip(book, (1, 1, 20, 20, 1, 20)):         # the under-650 loans earn little
        r["RANR"] = v
    res = engine.run(cube(), table(book))
    m = next(x for x in res.measures if x.name == "ranr_rate")
    assert m.higher_is == "better"
    g = res.grids[0]
    low = g.cell("600 - 649", "A").rates["ranr_rate"]
    top = res.total.rates["ranr_rate"].rate
    assert low.excess == pytest.approx(top * low.den - low.num)   # a shortfall, in RANR dollars
    assert low.excess > 0
    # and a pocket earning more than the book is not bleeding
    assert g.cell("650 - 700", "B").rates["ranr_rate"].excess < 0


def test_ranr_reads_worse_when_it_earns_less(book):
    rows = []
    for i in range(2000):
        a = i < 400
        rows.append(row(i, 600 if a else 700, "A", 100, 0, 0, ranr=(1.0 if i % 2 else 2.0) if a else 5.0))
    res = engine.run(cube(), table(rows))
    s = res.grids[0].cell("600 - 649", "A").rates["ranr_rate"]
    # 1.5% of booked dollars against 5%: 3.5 points less, a difference and never a multiple (NEXT-GOAL 3.2)
    assert s.vs_rest == pytest.approx(0.015 - 0.05)
    assert s.reading_topline == engine.WORSE                   # keeps less is worse, not better


def test_too_few_losses_to_test(book):
    rows = [row(i, 600, "A", 100, 1 if i < 3 else 0, 100 if i < 3 else 0) for i in range(60)] + \
           [row(100 + i, 700, "A", 100, 1 if i < 2 else 0, 100 if i < 2 else 0) for i in range(600)]
    res = engine.run(cube(benchmark=bench(min_events=5)), table(rows))
    s = res.grids[0].cell("600 - 649", "A").rates["gco_rate"]
    assert s.events == 3 and s.reading_topline == engine.FEW


def test_the_allowance_for_many_tests_by_hand():
    ps = [0.01, 0.04, 0.03, None, 0.20]
    assert engine.adjust(ps, "none") == ps
    assert engine.adjust(ps, "bonferroni") == [0.04, 0.16, 0.12, None, 0.8]
    # BH, m = 4: sorted 0.01, 0.03, 0.04, 0.20 -> 0.04, 0.06, 0.0533, 0.20 -> monotone 0.04, 0.0533, 0.0533, 0.20
    got = engine.adjust(ps, "bh")
    assert got[0] == pytest.approx(0.04) and got[2] == pytest.approx(0.16 / 3) and got[1] == pytest.approx(0.16 / 3)
    assert got[3] is None and got[4] == pytest.approx(0.20)


def test_the_allowance_is_applied_to_the_readings(tmp_path):
    from origination_cube import config as cfgmod, synth
    from origination_cube.ingest import read_table
    cfg, data = synth.write(tmp_path, n=6000)
    t = read_table(data)
    raw = cfgmod.load(cfg).raw
    none = engine.run(cfgmod.parse({**raw, "benchmark": {**raw["benchmark"], "many_tests": "none"}}), t)
    bonf = engine.run(cfgmod.parse({**raw, "benchmark": {**raw["benchmark"], "many_tests": "bonferroni"}}), t)
    pn = [c.rates["gco_rate"].p_book for _, c in none.grids[0].inner() if c.rates["gco_rate"].p_book is not None]
    pb = [c.rates["gco_rate"].p_book for _, c in bonf.grids[0].inner() if c.rates["gco_rate"].p_book is not None]
    assert all(b >= a for a, b in zip(pn, pb)) and any(b > a for a, b in zip(pn, pb))


def test_judged_against_decides_the_flag(book):
    res = engine.run(cube(benchmark=bench(compare_to="peers")), table(book))
    s = res.grids[0].cell("600 - 649", "A").rates["gco_rate"]
    assert s.flag == s.reading_band
    res = engine.run(cube(benchmark=bench(compare_to="topline")), table(book))
    s = res.grids[0].cell("600 - 649", "A").rates["gco_rate"]
    assert s.flag == s.reading_topline


def test_materiality_as_a_share_and_in_dollars(book):
    res = engine.run(cube(benchmark=bench(materiality="10% of losses")), table(book))
    assert res.materiality_line["gco_rate"] == pytest.approx(15.0)          # 10% of 150 GCO dollars
    g = res.grids[0]
    assert g.cell("600 - 649", "A").rates["gco_rate"].material is True      # excess 50 - 0.075 * 200 = 35
    res = engine.run(cube(benchmark=bench(materiality=40)), table(book))
    assert res.materiality_line["gco_rate"] == 40.0
    assert res.grids[0].cell("600 - 649", "A").rates["gco_rate"].material is False
    # a dollar line is a GCO amount: the outcome rates don't borrow it (the third walk, defect 8); a profit
    # shortfall is dollars too, and is held to the same line (NEXT-GOAL 3.2)
    assert res.materiality_line == {"gco_rate": 40.0, "ranr_rate": 40.0, "contribution_rate": 40.0}
    assert any("Outcome, share of loans: no materiality line" in w for w in res.warnings)
    assert not any("RANR" in w and "no materiality line" in w for w in res.warnings)
