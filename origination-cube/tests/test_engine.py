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
    assert res.total.rates["gco_rate"].rate == pytest.approx(150 / 2000)
    assert res.total.rates["outcome_booked"].rate == pytest.approx(500 / 2000)
    low_a = g.cell("600 - 649", "A").rates["gco_rate"]      # loans 1, 2
    assert low_a.num == 50 and low_a.den == 200 and low_a.units == 2
    assert low_a.rate == pytest.approx(0.25)
    assert low_a.vs_topline == pytest.approx(0.25 / 0.075)
    assert low_a.excess == pytest.approx(50 - 0.075 * 200)
    # 3.3x the book's rate, but on two loans: the test cannot tell it from luck
    assert low_a.reading_topline == engine.UNSURE


def test_vs_topline_is_share_of_losses_over_share_of_volume(book):
    res = engine.run(cube(), table(book))
    t = res.total.rates["gco_rate"]
    for _, c in res.grids[0].inner():
        s = c.rates["gco_rate"]
        if s.num:
            assert s.vs_topline == pytest.approx((s.num / t.num) / (s.den / t.den))


def test_median_benchmark_leaves_out_thin_cells(book):
    res = engine.run(cube(benchmark={"min_units": 2, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95,
                                         "power": 0.8, "min_events": 1, "compare_to": "topline",
                                         "many_tests": "none", "materiality": "none"}), table(book))
    g = res.grids[0]
    # cells with 2+ loans: under650/A (0.25), 650+/B (0/1200 = 0). Thin: 650+/A, under650/B.
    assert g.benchmarks["gco_rate"] == pytest.approx(0.125)
    assert g.cell("600 - 649", "B").rates["gco_rate"].reading_median == engine.THIN


def test_signed_values_pass_through(book):
    book.append(row(7, 700, "A", 100, 0, -30))       # a recovery, say (D47)
    res = engine.run(cube(), table(book))
    assert res.total.rates["gco_rate"].num == 120


def test_missing_by_rule_gets_its_own_row_and_is_counted(book):
    book.append(row(7, -9999, "A", 100, 1, 40))
    res = engine.run(cube(missing={"SCORE": {"below": -1000}}), table(book))
    g = res.grids[0]
    assert engine.MISSING_RULE_LABEL in g.band_labels
    assert g.cell(engine.MISSING_RULE_LABEL, "A").rows == 1
    # the score is missing, but the loan's balance and losses are real: they stay in the rate
    assert res.total.rates["gco_rate"].num == 190
    assert res.left_out["score_median"][("SCORE", "missing by rule")] == 1


def test_missing_values_list_applies_to_a_dimension(book):
    book.append(row(7, 600, "UNK", 100, 0, 0))
    res = engine.run(cube(missing={"CHAN": {"values": ["UNK"]}}), table(book))
    assert engine.MISSING_RULE_LABEL in res.grids[0].dim_labels


def test_the_tie_out_can_fail(book):
    """Check the checker: tamper with one cell and the tie-out must go red."""
    res = engine.run(cube(), table(book))
    g = res.grids[0]
    g.cell("600 - 649", "A").rates["gco_rate"].num += 1
    with pytest.raises(engine.TieOutError, match="gco_rate numerator"):
        engine.tie_out(g, res.total, res.measures, res.rows)


def test_the_tie_out_catches_a_dropped_row(book):
    res = engine.run(cube(), table(book))
    g = res.grids[0]
    del g.cells[("600 - 649", "B")]
    with pytest.raises(engine.TieOutError, match="rows"):
        engine.tie_out(g, res.total, res.measures, res.rows)


def test_the_plant_is_the_worst_pocket(tmp_path):
    cfg, data = synth.write(tmp_path, n=20000)
    res = engine.run(cfgmod.load(cfg), read_table(data))
    g = res.grids[0]
    for m in ("outcome_booked", "gco_rate"):
        ranked = sorted(g.inner(), key=lambda kc: -kc[1].rates[m].excess)
        (band, chan), top = ranked[0]
        assert (band, chan) == (g.band_labels[0], "Broker")
        assert top.rates[m].vs_topline > 4
        assert top.rates[m].reading_topline == engine.WORSE
    # RANR has no plant: no populated pocket may read as a real difference (a gap
    # past the threshold that the test calls luck is allowed; that is the test working)
    for (b, d), c in g.inner():
        if c.rates["ranr_rate"].units >= 30:
            assert c.rates["ranr_rate"].reading_topline not in (engine.WORSE, engine.BETTER)


def test_same_input_same_output(tmp_path):
    cfg, data = synth.write(tmp_path, n=2000)
    a = engine.run(cfgmod.load(cfg), read_table(data))
    b = engine.run(cfgmod.load(cfg), read_table(data))
    assert [(k, c.rates["gco_rate"].rate) for k, c in a.grids[0].cells.items()] == \
           [(k, c.rates["gco_rate"].rate) for k, c in b.grids[0].cells.items()]


def test_the_test_matches_a_hand_two_proportion_z():
    """Unweighted flag (every balance 1): the ratio test is the textbook
    two-proportion z with each group's own variance."""
    import math
    from origination_cube import stats
    a = (400, 40.0, 400.0, 40.0, 400.0, 40.0)        # 40 bad of 400: 10%
    b = (3600, 180.0, 3600.0, 180.0, 3600.0, 180.0)  # 180 of 3,600: 5%
    idx, p = stats.compare(a, b)
    pa, pb = 0.10, 0.05
    se = math.sqrt(pa * (1 - pa) / 400 * 400 / 399 + pb * (1 - pb) / 3600 * 3600 / 3599)
    want = math.erfc(abs(pa - pb) / se / math.sqrt(2))
    assert idx == pytest.approx(2.0)
    assert p == pytest.approx(want, rel=1e-9)


def test_peers_are_the_parent_without_the_pocket(book):
    res = engine.run(cube(), table(book))
    g = res.grids[0]
    s = g.cell("600 - 649", "A").rates["gco_rate"]
    # rest of under-650 is channel B: loan 5, 100 / 400
    assert s.vs_band == pytest.approx(0.25 / 0.25)
    # rest of channel A is 650+ / A: loan 3, 0 / 200 -> no rate to divide by
    assert s.vs_dim is None


def test_the_plant_is_significant_and_its_neighbours_are_not_overstated(tmp_path):
    cfg, data = synth.write(tmp_path, n=20000)
    res = engine.run(cfgmod.load(cfg), read_table(data))
    g = res.grids[0]
    plant = g.cell(g.band_labels[0], "Broker").rates["gco_rate"]
    assert plant.p_book < 1e-6 and plant.p_band < 1e-6
    assert plant.reading_topline == engine.WORSE and plant.reading_band == engine.WORSE
    # the other under-620 pockets are worse than the book but better than their band, which the plant drags up
    other = g.cell(g.band_labels[0], "Branch").rates["gco_rate"]
    assert other.vs_topline > 1 and other.vs_band < 1


def test_a_pocket_says_the_smallest_gap_it_could_show(tmp_path):
    cfg, data = synth.write(tmp_path, n=20000)
    res = engine.run(cfgmod.load(cfg), read_table(data))
    g = res.grids[0]
    small = g.cell(g.band_labels[0], "Broker").rates["gco_rate"]          # ~530 loans
    large = g.cell("680 - 739", "Branch").rates["gco_rate"]    # ~2,700 loans
    assert small.smallest_gap > large.smallest_gap > 1
    need = res.loans_needed["gco_rate"]
    # a pocket exactly the suggested size can show exactly the worse_at gap
    from origination_cube import stats
    assert stats.smallest_gap(need.loans, need.rate, need.s_d, need.x_bar, 0.95, 0.8) == pytest.approx(1.25, abs=0.01)


def test_bands_by_count(book):
    res = engine.run(cube(bands=[{"name": "score", "field": "SCORE", "count": 2, "cut": "equal_loans"}]),
                     table(book))
    assert res.band_edges["score"] == (650.0,)       # median of 600 x3, 700 x3


def test_asking_for_more_bands_than_the_values_allow_warns(book):
    res = engine.run(cube(bands=[{"name": "score", "field": "SCORE", "count": 5, "cut": "equal_loans"}]),
                     table(book))
    assert any("asked for 5 bands, got" in w for w in res.warnings)


def test_round_cuts_are_round_and_keep_the_count():
    edges = engine.cut_edges([float(x) for x in range(1, 100001)], 4, "round")
    assert edges == (25000.0, 50000.0, 75000.0)


def test_the_reading_and_its_test_compare_the_same_two_groups(tmp_path):
    """Found 25 Sep 2026: the printout put the whole-book multiple (pocket
    included) beside the p-value of the rest-of-book test. The reading now
    uses the rest-of-book multiple, which its test is about."""
    cfg, data = synth.write(tmp_path, n=20000)
    res = engine.run(cfgmod.load(cfg), read_table(data))
    s = res.grids[0].cell(res.grids[0].band_labels[0], "Broker").rates["gco_rate"]
    rest = res.total.rates["gco_rate"]
    want = s.rate / ((rest.num - s.num) / (rest.den - s.den))
    assert s.vs_rest == pytest.approx(want)
    assert s.vs_rest > s.vs_topline          # removing the pocket lowers its comparison


def test_a_big_pocket_is_read_against_the_rest_not_against_itself():
    """A pocket holding 60% of the book at 1.4x the rest of it is only 1.13x the
    whole book, because it is most of the book. Read against the book without
    it, it is 1.4x and worse; read against itself included, it would pass as
    in line. The word must come from the comparison its test made."""
    rows = []
    for i in range(3000):
        a = i < 1800
        loss = (140 if a else 100) if i % 10 == 0 else 0
        rows.append(row(i, 600, "A" if a else "B", 100, 1 if loss else 0, loss))
    res = engine.run(cube(), table(rows))
    s = res.grids[0].cell("600 - 649", "A").rates["gco_rate"]
    assert s.vs_topline == pytest.approx(0.14 / 0.124)
    assert s.vs_rest == pytest.approx(1.4)
    assert s.reading_topline == engine.WORSE


def test_a_yes_no_outcome_from_a_value(book):
    for i, r in enumerate(book):
        r["DECISION"] = "AUTO" if i % 2 == 0 else "MANUAL"
    res = engine.run(cube(outcome={"field": "DECISION", "is": "AUTO"}), table(book))
    assert res.total.rates["outcome_loans"].rate == pytest.approx(0.5)      # 3 of 6 loans
    # booked-weighted: loans 1, 3, 5 have 100 + 200 + 400 of 2,000
    assert res.total.rates["outcome_booked"].rate == pytest.approx(700 / 2000)


def test_straight_and_weighted_rates_side_by_side(book):
    res = engine.run(cube(), table(book))
    assert res.total.rates["outcome_loans"].rate == pytest.approx(2 / 6)     # loans 1 and 5 went bad
    assert res.total.rates["outcome_booked"].rate == pytest.approx(500 / 2000)


def test_a_missing_key_is_refused_and_repeats_are_reported(book):
    with pytest.raises(engine.ColumnsMissing, match="`LOAN` \\(used by key\\)"):
        engine.run(cube(key="LOAN"), table(book))
    book.append(dict(book[0]))
    res = engine.run(cube(), table(book))
    assert any("`ID` repeats: 1 value appears" in w for w in res.warnings)


def test_edges_that_would_print_alike_keep_their_precision():
    """Rounded labels must never merge two bands into one pocket."""
    labels = engine.band_labels((99.95, 100.2))
    assert len(set(labels)) == 3
    assert engine.band_labels((26803.1, 38548.6), 5000, 90000) == ["5,000 - 26,802", "26,803 - 38,548", "38,549 - 90,000"]


def test_bands_read_as_ranges():
    """The firm, 25 Sep 2026: "i want bands to be written in '0 - 660' form"."""
    assert engine.band_labels((620, 680, 740), 519, 850) == ["519 - 619", "620 - 679", "680 - 739", "740 - 850"]
    assert engine.band_labels((0.35, 0.42), 0.1, 0.9) == ["0.10 - 0.34", "0.35 - 0.41", "0.42 - 0.90"]
