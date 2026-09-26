"""The adversarial pass on the cube's arithmetic (26 Sep 2026): four findings,
written by another model as tests that failed against the code, taken in by
hand (only this file crossed over from branch adversarial/origination-cube-stats,
31be7d46), fixed, and moved here so nothing can put the bugs back.

1. A p-value exactly at the bar read "significant" at 95%, 99% and 99.9% and
   "not significant" at 90% (1 - 0.95 is 0.050000000000000044). stats.bar().
2. Cochran's Q was centred on ln OR_MH, not A8's weighted mean; that version
   only ever leans toward "the pockets disagree", and flipped the verdict.
3. A rate that couldn't be worked out was reported as "the book's rate is zero".
4. A pocket the shuffle test couldn't answer still said a shuffle test ran.

Two assertions were corrected in triage: the Cochran's Q cases asserted the
flip itself (cube below 0.05, A8 above), which is the bug, not the rule; and
the closing family count expected 3 GCO tests against the band where the
rule gives 2 (the zero-balance pocket leaves its band neighbour nothing to be
compared with).

Every engine run here names its own shuffle count (200).
"""

from __future__ import annotations

import math

import pytest

from conftest import cube, row, table
from origination_cube import checks, engine, perm, stats


class _Bench:
    """The five fields reading_of reads from a benchmark."""
    def __init__(self, confidence: float):
        self.worse_at, self.better_at, self.confidence, self.min_events = 1.25, 0.8, confidence, 0


# --------------------------------------------------------------------------
# Finding 1: a p-value exactly at the bar reads "significant" at 95%, 99% and
# 99.9% confidence, and "not significant" at 90%.


@pytest.mark.parametrize("confidence, hits", [(0.95, 499), (0.99, 99), (0.999, 9)])
def test_a_p_value_exactly_at_the_bar_is_not_significant(confidence, hits):
    """statistics.md, conventions: "The reading is significant (p-value below
    the bar) or not significant". reading_of writes the same rule as
    `p >= 1 - bench.confidence` -> not significant. But `1 - 0.95` is
    0.050000000000000044 in floating point, so a p-value of exactly 0.05 sits
    below the computed bar and reads "worse" (significant); at 90% the bar is
    0.09999999999999998, so 0.1 reads "worse, not significant". The same rule
    gives opposite answers at the bar depending on the confidence chosen.

    Reachable: the shuffle test's p is (hits + 1) / (B + 1) (B2). With
    `shuffles: 9999` (the cube file accepts 100 to 1,000,000) and 499 hits the
    p is 500 / 10,000 = 0.05 exactly. Bonferroni (p x m) and BH (p x m / rank)
    can land on the bar the same way."""
    p = perm.Shuffled(0.02, hits, 9_999).p
    assert p == round(1 - confidence, 6)                          # exactly at the bar
    assert engine.reading_of(2.0, 100, _Bench(confidence), 2, p, events=50) == engine.UNSURE_WORSE


def test_a_profit_gap_at_the_bar_is_not_significant_either():
    """reading_gap (profit, NEXT-GOAL 3.2) writes the bar as `p < 1 - confidence`
    -> real. At p = 0.05 and 95% that is 0.05 < 0.050000000000000044, so a
    profit shortfall at the bar counts as real under the "test" line and reads
    "worse" under a points line, where the rule says "not significant"."""
    p = perm.Shuffled(-0.01, 499, 9_999).p
    assert p == 0.05
    assert engine.reading_gap(-0.01, 1000.0, engine.ProfitLine("test"), p, 0.95) == engine.IN_LINE
    assert engine.reading_gap(-0.01, 1000.0, engine.ProfitLine("points", 0.005), p, 0.95) == engine.UNSURE_WORSE


# --------------------------------------------------------------------------
# Finding 2: Cochran's Q is centred on ln OR_MH, not on A8's weighted mean, and
# that flips the steadiness verdict.


def _a8(strata: list[tuple[int, int, int, int]]) -> tuple[float, int]:
    """statistics.md A8, as written: theta_h = ln(ad/bc), w_h = 1/v_h,
    theta_bar = sum(w theta) / sum(w), Q = sum w (theta - theta_bar)^2 on
    (pockets - 1) degrees of freedom. No zero cells in the cases below, so no
    Haldane correction is needed."""
    th, ws = [], []
    for a, b, c, d in strata:
        th.append(math.log(a * d / (b * c)))
        ws.append(1 / (1 / a + 1 / b + 1 / c + 1 / d))
    tbar = sum(w * t for w, t in zip(ws, th)) / sum(ws)
    q = sum(w * (t - tbar) ** 2 for w, t in zip(ws, th))
    return q, len(strata)


@pytest.mark.parametrize("strata", [
    [(8, 57, 4, 39), (1, 48, 6, 33)],                              # two pockets
    [(11, 106, 3, 51), (4, 82, 3, 62), (6, 120, 6, 25)],           # three pockets, every cell at least 3
])
def test_a8_cochrans_q_is_centred_on_the_weighted_mean_log_odds_ratio(strata):
    """statistics.md A8 centres Q on theta_bar, the weighted mean of the pockets'
    log odds ratios. stats.cochran_q centres it on ln OR_MH instead, noting
    that on A8's worked example this moves p from 0.80511 to 0.80510. The
    weighted mean is the centre that minimises Q, so the cube's Q is never
    smaller than A8's and its p never larger: the deviation is one-directional,
    toward "the pockets disagree". It is not always negligible. On these
    strata A8 gives p just above 0.05 (no evidence the pockets disagree) and
    the cube gives p just below it (they disagree). A random search found the
    verdict flipping in about 1 in 300 strata sets with small cells, and 1 in
    1,200 with every cell at least 3."""
    orr = stats.mantel_haenszel(strata, 1.96)[0]
    q, k = _a8(strata)
    want = stats.chi2_sf(q, k - 1)     # the cube's chi2 tail matches scipy to 3e-14 (the adversarial pass)
    got, pockets = stats.steadiness_p(strata, orr)
    assert pockets == k
    assert got == pytest.approx(want, rel=1e-9)                   # A8, as written
    assert got >= 0.05 and want >= 0.05                           # the verdict no longer flips


# --------------------------------------------------------------------------
# Finding 3: a rate that cannot be worked out is reported as "zero".


def test_an_absent_rate_is_not_reported_as_the_book_s_rate_being_zero():
    """LoansNeeded.rate is None when SUM(bottom) is zero or nothing entered the
    rate: there is no rate, which is a different fact from a rate of zero
    (a book that lost nothing). sentence() collapses both into "the book's
    rate is zero, so no gap can be sized". Reached from the engine by a GCO
    column that is blank on every row: the Check tab then tells the reader
    the book's GCO rate is zero, when no GCO was read at all."""
    empty = stats.loans_needed("gco_rate", [], 1.25, 0.95, 0.8)
    no_dollars = stats.loans_needed("gco_rate", [(0.0, 0.0)] * 10, 1.25, 0.95, 0.8)
    unknown = stats.loans_needed_two_prop("outcome_loans", None, 100, 1.25, 0.95, 0.8)
    for ln in (empty, no_dollars, unknown):
        assert ln.rate is None and ln.loans is None
        assert "zero" not in ln.sentence(), ln.sentence()
    # and the case the sentence is right about, kept apart from the three above
    assert "zero" in stats.loans_needed("gco_rate", [(0.0, 100.0)] * 10, 1.25, 0.95, 0.8).sentence()

    rows = [row(i, 600 + 100 * (i % 2), "AB"[i % 3 == 0], 100, int(i % 5 == 0), "", 10) for i in range(80)]
    bench = {"min_units": 2, "min_events": 1, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95, "power": 0.8,
             "compare_to": "topline", "many_tests": "none", "materiality": "none", "shuffles": 200}
    res = engine.run(cube(benchmark=bench), table(rows))
    assert res.total.rates["gco_rate"].rate is None and res.total.rates["gco_rate"].units == 0
    assert "zero" not in res.loans_needed["gco_rate"].sentence(), res.loans_needed["gco_rate"].sentence()


# --------------------------------------------------------------------------
# Finding 4: a pocket that got no answer from the shuffle test still says a
# shuffle test ran.


def test_a_pocket_the_shuffle_test_could_not_answer_names_no_test():
    """RateStat.test's contract (engine.py): which test gave p_book and p_band;
    "None when nothing was tested". _build_grid sets it to "shuffle" for every
    dollar-rate pocket before the shuffle runs, and _shuffle_tests only fills
    p and hits for pockets with dollars on both sides (perm.RestGap: a pocket
    with no dollars gets no answer). A pocket whose loans all carry a zero
    balance therefore ends with test "shuffle", p None and hits None: the
    label says a test ran where none could. The workbook's Test column prints
    the fallback "N shuffles" for it."""
    rows, i = [], 0
    for score, chan, n, bad, bal in ((600, "A", 40, 8, 0), (600, "B", 40, 2, 1000),
                                     (700, "A", 40, 2, 1000), (700, "B", 40, 2, 1000)):
        for j in range(n):
            flag = 1 if j < bad else 0
            rows.append(row(i, score, chan, bal, flag, 400 * flag, 20))
            i += 1
    bench = {"min_units": 2, "min_events": 1, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95, "power": 0.8,
             "compare_to": "topline", "many_tests": "none", "materiality": "none", "shuffles": 200}
    res = engine.run(cube(benchmark=bench), table(rows))
    s = res.grids[0].cell("600 - 649", "A").rates["gco_rate"]
    assert s.rate is None and s.p_book is None and s.p_band is None and s.hits_book is None
    assert s.test is None, f"test={s.test!r} with no p-value and no hits"
    # nothing was tested for this pocket, so it is in no family: 3 GCO pockets against the book, and against the
    # band only the two 700 pockets (600 / B's band neighbour has no dollars to be compared with)
    fam = {f[3]: f[4] for f in checks.families(res) if f[2] == "gco_rate"}
    assert fam == {"the rest of the book": 3, "the rest of its band": 2}
