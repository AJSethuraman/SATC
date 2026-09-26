"""The arithmetic, checked by hand on a six-loan book, and the plant found in
the synthetic one."""

import pytest

from conftest import cube, row, table
from origination_cube import engine, stats, synth
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
    """The share of loans is tested by the pooled two-proportion z (statistics.md
    A1, ruling OC-37), by hand: 40 bad of 400 against 180 of 3,600. It was the
    unpooled test on n - 1 until 25 Sep 2026, which this test used to hold."""
    import math
    rows = [row(i, 600, "A" if i < 400 else "B", 100, 1 if (i < 40 or 400 <= i < 580) else 0, 0)
            for i in range(4000)]
    res = engine.run(cube(), table(rows))
    s = res.grids[0].cell("600 - 649", "A").rates["outcome_loans"]
    pbar = 220 / 4000
    se = math.sqrt(pbar * (1 - pbar) * (1 / 400 + 1 / 3600))
    want = math.erfc(abs(0.10 - 0.05) / se / math.sqrt(2))
    assert s.vs_rest == pytest.approx(2.0) and s.test == engine.Z_TEST
    assert s.p_book == pytest.approx(want, rel=1e-9)
    unpooled = math.sqrt(0.1 * 0.9 / 399 + 0.05 * 0.95 / 3599)
    assert s.p_book != pytest.approx(math.erfc(0.05 / unpooled / math.sqrt(2)), rel=1e-3)


def test_peers_are_the_parent_without_the_pocket(book):
    res = engine.run(cube(), table(book))
    g = res.grids[0]
    s = g.cell("600 - 649", "A").rates["gco_rate"]
    # rest of under-650 is channel B: loan 5, 100 / 400
    assert s.vs_band == pytest.approx(0.25 / 0.25)
    # (the rest of its segment was worked out too until 25 Sep 2026, never shown, and is gone)
    assert not hasattr(s, "vs_dim") and not hasattr(s, "p_dim")


def test_the_plant_is_significant_and_its_neighbours_are_not_overstated(tmp_path):
    cfg, data = synth.write(tmp_path, n=20000)
    res = engine.run(cfgmod.load(cfg), read_table(data))
    g = res.grids[0]
    plant = g.cell(g.band_labels[0], "Broker").rates["gco_rate"]
    # GCO is shuffled (statistics.md B2): no shuffle came near the plant, so its p is the smallest a
    # count of shuffles can print, 1 in B + 1, before the allowance for many tests. It read under 1e-6
    # from the ratio z test this replaced (25 Sep 2026)
    assert plant.test == engine.SHUFFLE_TEST and plant.hits_book == plant.hits_band == 0
    assert plant.p_book < 0.01 and plant.p_band < 0.01
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


def test_revenue_is_judged_by_the_revenue_setting():
    """The firm, 25 Sep 2026, after the seventh walk: one revenue yardstick on every tab."""
    from origination_cube.config import Benchmark
    import dataclasses
    fields = {f.name for f in dataclasses.fields(Benchmark)}
    base = dict(min_units=30, min_events=0, worse_at=1.25, better_at=0.8, confidence=0.95, power=0.8,
                compare_to="peers", many_tests="none", materiality=("none", 0))
    b = Benchmark(**{k: v for k, v in base.items() if k in fields}, revenue_line=0.05)
    judge, luck = engine.revenue_bench(b)
    assert not luck and engine.reading_of(0.94, 400, judge, 30, 0.001, higher_is="better") == engine.WORSE
    assert engine.reading_of(0.96, 400, judge, 30, 0.001, higher_is="better") == engine.IN_LINE
    judge, luck = engine.revenue_bench(dataclasses.replace(b, revenue_line="luck"))
    assert luck
    assert engine.reading_of(0.97, 400, judge, 30, 0.001, higher_is="better", luck_only=True) == engine.WORSE
    assert engine.reading_of(0.80, 400, judge, 30, 0.3, higher_is="better", luck_only=True) == engine.IN_LINE
    judge, luck = engine.revenue_bench(dataclasses.replace(b, revenue_line="losses"))
    assert not luck and judge.worse_at == 1.25


def test_every_ranr_reading_follows_the_revenue_setting(tmp_path):
    """The wiring, not just the rule: under each revenue setting, every tested
    RANR pocket reads what that setting says (both tabs agreeing proved nothing
    when both used the wrong line)."""
    import dataclasses
    cfg, data = synth.write(tmp_path, n=8000)
    base, tbl = cfgmod.load(cfg), read_table(data)
    for rl in (0.05, "luck", "losses"):
        c = dataclasses.replace(base, benchmark=dataclasses.replace(base.benchmark, revenue_line=rl))
        b, n = c.benchmark, 0
        for g in engine.run(c, tbl).grids:
            for _, cell in g.inner():
                s = cell.rates["ranr_rate"]
                if s.reading_band in (engine.THIN, engine.FEW, None) or not s.vs_band or s.vs_band <= 0:
                    continue
                real = s.p_band is not None and s.p_band < 1 - b.confidence
                if rl == "luck":
                    want = engine.IN_LINE if not real else engine.WORSE if s.vs_band < 1 else engine.BETTER
                else:
                    lo, hi = (1 / b.worse_at, 1 / b.better_at) if rl == "losses" else (1 - rl, 1 + rl)
                    if abs(s.vs_band - lo) < 1e-9 or abs(s.vs_band - hi) < 1e-9:
                        continue                                  # on a line: either reading is fair
                    if lo < s.vs_band < hi:
                        want = engine.IN_LINE
                    elif s.vs_band < lo:
                        want = engine.WORSE if real else engine.UNSURE_WORSE
                    else:
                        want = engine.BETTER if real else engine.UNSURE_BETTER
                assert s.reading_band == want, (rl, s.vs_band, s.p_band, s.reading_band, want)
                n += 1
        assert n, rl


# --------------------------------------------------------------------------
# Which test runs where (docs/statistics.md, "Which test, where"), 25 Sep 2026


def _bench(**kw):
    b = {"min_units": 71, "min_events": 10, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95, "power": 0.8,
         "compare_to": "peers", "many_tests": "none", "materiality": "none"}
    b.update(kw)
    return b


def _pockets(spec):
    """Rows from (score, channel, loans, bad): balance 1,000, a bad loan loses 400."""
    rows, i = [], 0
    for score, chan, n, bad in spec:
        for k in range(n):
            rows.append(row(i, score, chan, 1000, 1 if k < bad else 0, 400 if k < bad else 0, 20))
            i += 1
    return rows


def test_walk_6_defect_8_a_small_pocket_gets_the_exact_test():
    """Walk 6, defect 8: 29 bad of 50, under the suggested fewest loans of 71, read
    "too few loans to test". Below fewest loans the share of loans now gets
    Fisher's exact test (B1), which needs no minimum, and the pocket is worse."""
    rows = _pockets([(600, "A", 50, 29), (600, "B", 300, 24), (700, "A", 400, 28), (700, "B", 400, 28)])
    res = engine.run(cube(benchmark=_bench()), table(rows))
    g = res.grids[0]
    s = g.cell("600 - 649", "A").rates["outcome_loans"]
    assert s.test == engine.EXACT_TEST
    assert s.p_band == pytest.approx(stats.fisher_exact(29, 50, 53, 350), rel=1e-12)
    assert s.p_book == pytest.approx(stats.fisher_exact(29, 50, 29 + 24 + 28 + 28, 1150), rel=1e-12)
    assert s.reading_band == s.reading_topline == s.flag == engine.WORSE
    big = g.cell("600 - 649", "B").rates["outcome_loans"]           # at or above the floor: A1
    assert big.test == engine.Z_TEST
    assert big.p_band == pytest.approx(stats.two_prop_z(24, 300, 29, 50)[1], rel=1e-12)
    # the dollar rates are shuffled at any size (B2 has no floor)
    gco = g.cell("600 - 649", "A").rates["gco_rate"]
    assert gco.test == engine.SHUFFLE_TEST and gco.hits_band == 0 and gco.reading_band == engine.WORSE


def test_walk_6_defect_8_on_the_synthetic_book(tmp_path):
    """The same pocket where the walk found it: every-20 score bands on the
    8,000-loan synthetic book, fewest loans at the suggested 71."""
    import copy
    import math
    cfg, data = synth.write(tmp_path, n=8000)
    raw, tbl = copy.deepcopy(cfgmod.load(cfg).raw), read_table(data)
    raw["bands"] = [{"name": "fico", "field": "FICO", "edges": list(range(500, 861, 20))}]
    rate = 0.07125890736342043                         # the book's share of loans with the outcome
    raw["benchmark"]["min_units"] = math.ceil(5 / rate)
    res = engine.run(cfgmod.parse(raw), tbl)
    assert res.total.rates["outcome_loans"].rate == pytest.approx(rate)
    s = res.grids[0].cell("580 - 599", "Broker").rates["outcome_loans"]
    assert (s.units, s.num) == (50, 29) and s.units < 71
    assert s.test == engine.EXACT_TEST and s.flag == engine.WORSE and s.p_band < 1e-6


def test_a_pocket_below_fewest_losses_still_refuses():
    """Only fewest losses stops a test: 5 bad of 60 under a floor of 10 losses is
    too few to test, for the share of loans and for GCO alike. RANR has no loss
    floor, as before."""
    rows = _pockets([(600, "A", 60, 5), (600, "B", 300, 24), (700, "A", 400, 28), (700, "B", 400, 28)])
    res = engine.run(cube(benchmark=_bench()), table(rows))
    c = res.grids[0].cell("600 - 649", "A")
    assert c.rates["outcome_loans"].flag == engine.FEW
    assert c.rates["gco_rate"].flag == engine.FEW
    assert c.rates["ranr_rate"].flag not in (engine.FEW, engine.THIN, None)
    # and nothing reads "too few loans" any more
    assert not any(cell.rates[m].flag == engine.THIN for _, cell in res.grids[0].inner() for m in cell.rates)


def test_the_family_is_the_inner_pockets_only():
    """A2: one family is one grid, one rate, one comparison. On the Test 1 book
    (2 x 2) that is 4 tests; counting the band and segment totals made it 8
    (the audit, item b), and they are never shown."""
    rows = _pockets([(600, "Broker", 1000, 150), (600, "Branch", 1000, 50),
                     (700, "Broker", 1000, 50), (700, "Branch", 1000, 50)])
    res = engine.run(cube(benchmark=_bench(min_units=30, many_tests="bonferroni")), table(rows))
    g = res.grids[0]
    for (b, d), c in g.inner():
        s = c.rates["outcome_loans"]
        rest = [x for k, x in g.inner() if k != (b, d)]
        raw = stats.two_prop_z(s.num, s.units, sum(x.rates["outcome_loans"].num for x in rest), 3000)[1]
        assert s.p_book == pytest.approx(min(1.0, 4 * raw), rel=1e-9), (b, d)
    assert all(c.rates["outcome_loans"].p_book is None for k, c in g.cells.items() if engine.ALL in k)
    # A1's worked example, through the engine: Broker 600 against Branch 600, z 7.45
    s = g.cell("600 - 649", "Broker").rates["outcome_loans"]
    assert s.p_band == pytest.approx(min(1.0, 4 * stats.two_prop_z(150, 1000, 50, 1000)[1]), rel=1e-9)
