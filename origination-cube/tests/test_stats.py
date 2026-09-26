"""The suggested floors against the textbook, and the materiality ladder by hand."""

import math

import pytest

from origination_cube import stats


def textbook_two_proportion(p0, gap, confidence=0.95, power=0.8):
    """n for one group against a known rate, variance under each hypothesis
    (Fleiss, Statistical Methods for Rates and Proportions, 3rd ed., 4.2)."""
    p1 = gap * p0
    za = stats.norm_s_inv(1 - (1 - confidence) / 2)
    zb = stats.norm_s_inv(power)
    return ((za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))) / (p1 - p0)) ** 2


@pytest.mark.parametrize("gap", [1.25, 1.5, 2.0])
def test_a_plain_bad_loan_rate_lands_on_the_textbook(gap):
    p0 = 0.0465
    n_book = 100000
    bads = round(p0 * n_book)
    pairs = [(1.0, 1.0)] * bads + [(0.0, 1.0)] * (n_book - bads)
    got = stats.loans_needed("bad", pairs, gap, 0.95, 0.8).loans
    want = textbook_two_proportion(bads / n_book, gap)
    assert got == pytest.approx(want, rel=0.06)


def test_a_dollar_rate_needs_more_loans_than_a_count_rate():
    # same loans, same bad share; losses vary in size, so the dollar rate is noisier
    pairs_count, pairs_dollar = [], []
    for i in range(20000):
        bad = i % 20 == 0
        bal = 10000 + (i % 7) * 5000
        pairs_count.append((1.0 if bad else 0.0, 1.0))
        pairs_dollar.append(((bal * (0.2 + (i % 5) * 0.2)) if bad else 0.0, bal))
    n_count = stats.loans_needed("c", pairs_count, 1.25, 0.95, 0.8).loans
    n_dollar = stats.loans_needed("d", pairs_dollar, 1.25, 0.95, 0.8).loans
    assert n_dollar > n_count


def test_stricter_settings_need_more_loans():
    pairs = [(1.0 if i % 25 == 0 else 0.0, 1.0) for i in range(50000)]
    base = stats.loans_needed("b", pairs, 1.25, 0.95, 0.8).loans
    assert stats.loans_needed("b", pairs, 1.25, 0.99, 0.8).loans > base
    assert stats.loans_needed("b", pairs, 1.25, 0.95, 0.9).loans > base
    assert stats.loans_needed("b", pairs, 2.0, 0.95, 0.8).loans < base


def test_a_zero_rate_cannot_be_sized():
    assert stats.loans_needed("b", [(0.0, 1.0)] * 100, 1.25, 0.95, 0.8).loans is None


def test_materiality_ladder_by_hand():
    ex = [500, 300, 100, 50, 50, -400, -600]      # positive excess totals 1,000
    rows = stats.materiality_ladder(ex, book_total=10000, shares=(0.01, 0.03, 0.05))
    # 1% = 100: 500, 300, 100 -> 900 of 1,000; 3% = 300: 500, 300; 5% = 500: 500 alone
    assert (rows[0].pockets, rows[0].captured) == (3, pytest.approx(0.9))
    assert (rows[1].pockets, rows[1].captured) == (2, pytest.approx(0.8))
    assert (rows[2].pockets, rows[2].captured) == (1, pytest.approx(0.5))


def test_the_pareto_cut():
    ex = [500, 300, 100, 50, 50]
    assert stats.threshold_explaining(ex, 0.8) == 300      # 500 + 300 = 80%
    assert stats.threshold_explaining(ex, 0.5) == 500
    assert stats.threshold_explaining([-1, -2], 0.8) is None


def test_a_negative_comparison_keeps_the_direction():
    """Found writing up the tests for the firm, 25 Sep 2026: with the rest of a
    band earning -1.8% RANR, a pocket earning -3.8% read 2.11x, "better"."""
    from origination_cube import engine
    assert stats.multiple(-0.038, -0.018) < 1 < stats.multiple(0.01, -0.018)
    assert stats.multiple(0.06, 0.03) == pytest.approx(2.0)             # a positive comparison is unchanged
    assert stats.multiple(0.02, 0) is None

    def sums(rate, n=400, bal=10_000.0):                   # n loans, each earning `rate` of its balance, +/- 1%
        ys = [bal * (rate + (0.01 if i % 2 else -0.01)) for i in range(n)]
        return (n, sum(ys), bal * n, sum(y * y for y in ys), bal * bal * n, sum(y * bal for y in ys))

    idx, p = stats.compare(sums(-0.038), sums(-0.018))
    assert idx < 1 and p < 0.05

    class Bench:
        worse_at, better_at, confidence = 1.25, 0.8, 0.95
    assert engine.reading_of(idx, 400, Bench, 30, p, higher_is="better") == engine.WORSE
    idx, p = stats.compare(sums(0.005), sums(-0.018))
    assert engine.reading_of(idx, 400, Bench, 30, p, higher_is="better") == engine.BETTER


# --------------------------------------------------------------------------
# docs/statistics.md, worked example by worked example, through the cube's own
# functions, to the precision the document prints.


def test_a1_the_pooled_two_proportion_z_on_the_test_1_book():
    """A1: Broker 600, 150 of 1,000, against Branch 600 (50 of 1,000) and against
    the rest of the book (150 of 3,000). Pooled (ruling OC-37)."""
    assert round(stats.pooled_se(150, 1000, 50, 1000), 6) == 0.013416
    z, p = stats.two_prop_z(150, 1000, 50, 1000)
    assert round(z, 2) == 7.45 and p == pytest.approx(9e-14, rel=0.05)
    assert round(stats.pooled_se(150, 1000, 150, 3000), 6) == 0.009618
    assert round(stats.two_prop_z(150, 1000, 150, 3000)[0], 2) == 10.40


def test_a1_is_pooled_not_the_unpooled_test_it_replaced():
    """The audit's example (item b): 12 of 200 against 30 of 1,000 was p 0.090 by
    the unpooled test on n - 1; A1 gives 0.035."""
    assert round(stats.two_prop_z(12, 200, 30, 1000)[1], 4) == 0.0351


def test_a2_benjamini_hochberg():
    from origination_cube import engine
    got = engine.adjust([0.001, 0.008, 0.02, 0.04, 0.30], "bh")
    assert [round(x, 3) for x in got] == [0.005, 0.020, 0.033, 0.050, 0.300]
    assert sum(x <= 0.05 for x in got) == 4


def test_a3_the_smallest_gap_a_pocket_could_show():
    """A3: a pocket of 71 at the synthetic book's 7.13% against the rest of 8,000."""
    book = 0.0713
    for n, want in ((71, 2.37), (140, 1.95), (280, 1.67)):
        assert round(stats.mde_two_prop(n, book, 8000 - n, 0.95, 0.8), 2) == want
    at80 = stats.mde_two_prop(71, book, 7929, 0.95, 0.8)
    assert round(at80 * book, 3) == 0.169                       # 16.9%
    at50 = stats.mde_two_prop(71, book, 7929, 0.95, 0.5)        # caught half the time: just clears 1.96
    assert round(at50, 2) == 1.85 and round(at50 * book, 3) == 0.132
    # the 50% rate is exactly where A1's z reaches 1.96
    assert stats.two_prop_z(at50 * book * 71, 71, book * 7929, 7929)[0] == pytest.approx(1.96, abs=1e-3)


def test_a3_loans_needed_inverts_the_same_formula():
    at80 = stats.mde_two_prop(71, 0.0713, 7929, 0.95, 0.8)
    ln = stats.loans_needed_two_prop("outcome", 0.0713, 8000, at80, 0.95, 0.8)
    assert ln.loans == 71 and ln.method == "two_prop"
    assert stats.power_two_prop(at80 * 0.0713, 71, 0.0713, 7929, 0.95) >= 0.8
    assert stats.power_two_prop(at80 * 0.0713, 70, 0.0713, 7930, 0.95) < 0.8
    # a book too small for the gap says so, rather than a number bigger than the book
    small = stats.loans_needed_two_prop("outcome", 0.0713, 500, 1.25, 0.95, 0.8)
    assert small.loans is None and small.rate and "no pocket of this book" in small.sentence()


def test_the_engine_uses_a3_for_the_share_of_loans(tmp_path):
    """Replaces the approximation for the share of loans only; the dollar rates
    keep it until the wave that reads RANR as points."""
    from origination_cube import config as cfgmod, engine, synth
    from origination_cube.ingest import read_table
    cfg, data = synth.write(tmp_path, n=4000)
    res = engine.run(cfgmod.load(cfg), read_table(data))
    ln = res.loans_needed["outcome_loans"]
    t = res.total.rates["outcome_loans"]
    assert ln.method == "two_prop" and res.loans_needed["gco_rate"].method == "ratio"
    for _, c in res.grids[0].inner():
        s = c.rates["outcome_loans"]
        want = stats.mde_two_prop(s.units, t.rate, t.units - s.units, 0.95, 0.8)
        assert s.smallest_gap == (pytest.approx(want) if want else None)


A5_STRATA = [(8, 92, 4, 96), (20, 180, 12, 188)]         # pockets A and B: (high bad, high good, low bad, low good)


def test_a5_mantel_haenszel():
    assert round(stats.mantel_haenszel(A5_STRATA, 1.96)[0], 3) == 1.829


def test_a6_cmh_has_no_continuity_correction():
    """Ruling OC-36: A6's 3.53, p 0.060. With the 1959 test's half subtracted it
    was 2.962, p 0.085 (the audit, item j)."""
    chi, p = stats.cmh(A5_STRATA)
    assert round(chi, 4) == 3.5251 and round(p, 4) == 0.0604
    assert round(chi, 2) == 3.53 and round(p, 3) == 0.060
    assert stats.cmh_p(A5_STRATA) == p


def test_a8_cochrans_q():
    orr = stats.mantel_haenszel(A5_STRATA, 1.96)[0]
    q, k = stats.cochran_q(A5_STRATA, orr)
    assert (round(q, 3), k) == (0.061, 2)
    assert round(stats.steadiness_p(A5_STRATA, orr)[0], 2) == 0.81


def test_b1_fisher_exact_below_the_floor():
    """B1: 4 bad of 12 against 14 of 200 (N 212, K 18). The z test on the same
    counts is eight times too sure of itself."""
    probs = [round(stats.hypergeom_pmf(k, 12, 18, 212), 4) for k in range(6)]
    assert probs == [0.3346, 0.3950, 0.2007, 0.0579, 0.0105, 0.0013]
    assert [round(x, 3) for x in probs[:4]] == [0.335, 0.395, 0.201, 0.058]
    p = stats.fisher_exact(4, 12, 18, 212)
    assert round(p, 4) == 0.0119
    assert round(sum(stats.hypergeom_pmf(k, 12, 18, 212) for k in range(4, 13)), 4) == 0.0119
    z, pz = stats.two_prop_z(4, 12, 14, 200)
    assert round(z, 2) == 3.18 and round(pz, 4) == 0.0015


def test_fisher_is_two_sided():
    """Every count no more likely than the one seen, in either tail. The values
    are scipy.stats.fisher_exact's on the same tables (25 Sep 2026)."""
    # symmetric: the other tail is exactly as likely, and a tie must be counted, not lost to rounding
    assert stats.fisher_exact(2, 10, 10, 20) == pytest.approx(0.023014137565221155, rel=1e-12)
    assert stats.fisher_exact(8, 10, 10, 20) == pytest.approx(0.023014137565221155, rel=1e-12)
    # a pocket with none bad: its own tail is 0.335, the other tail adds the counts as unlikely as that
    assert stats.fisher_exact(0, 12, 18, 212) == pytest.approx(0.60504060271159, rel=1e-12)
    assert stats.fisher_exact(29, 50, 53, 350) == pytest.approx(5.0198262412038815e-15, rel=1e-9)


def test_fisher_holds_up_on_a_million_loans():
    """C(1,000,000, 50) overflows a float; the ratio of neighbours does not."""
    p = stats.fisher_exact(12, 50, 20_000, 1_000_000)          # expected 1: twelve is far out
    assert 0 < p < 1e-8
    assert stats.fisher_exact(1, 50, 20_000, 1_000_000) == pytest.approx(1.0, abs=1e-9)
    total = sum(stats.hypergeom_pmf(k, 50, 20_000, 1_000_000) for k in range(51))
    assert total == pytest.approx(1.0, abs=1e-12)
