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
