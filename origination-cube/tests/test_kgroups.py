"""docs/statistics.md B3, B4, B5 and B6, reproduced by the cube's own arithmetic (kgroups.py), and the
cross-checks the scope asks for (docs/capabilities-scope.md 4b):

- B3's statistic is the score test of the conditional logistic model at "no effect", worked out from the
  conditional likelihood's own derivatives, to 1e-9;
- those derivatives are the likelihood's: checked against finite differences of the likelihood itself, computed
  in 40-digit decimal arithmetic by brute force over every way the bad loans could have fallen;
- B5's odds ratios agree with the Mantel-Haenszel ones, to a tolerance justified below;
- statsmodels' ConditionalLogit on one small example, its numbers written in as literals (statsmodels 0.15.0,
  26 Sep 2026; the cube never imports it)."""

import math
from decimal import Decimal, getcontext
from itertools import product

import numpy as np
import pytest

from origination_cube import kgroups as kg
from origination_cube import stats

SCORES5 = [1, 2, 3, 4, 5]


def _pockets(*tables):
    return [kg.Pocket([n for n, _ in t], [b for _, b in t]) for t in tables]


# --------------------------------------------------------------------------
# B3 and B4: the worked examples

SIZES = (100, 400, 500, 400, 100)


def _u_shape():
    """B4's example: 16%, 3.8%, 4.0%, 3.8%, 16% in one pocket (16, 15, 20, 15, 16 bad: 15 of 400 is 3.75%,
    printed 3.8%) and 10%, 3%, 4%, 3%, 10% in another."""
    return _pockets(list(zip(SIZES, (16, 15, 20, 15, 16))), list(zip(SIZES, (10, 12, 20, 12, 10))))


def test_b3_b4_worked_example_a_u_lights_general_and_not_trend():
    a = kg.association(_u_shape(), SCORES5)
    assert round(a.general, 1) == 66.5 and round(a.general, 2) == 66.47
    assert a.df == 4 and a.p_general < 0.0001
    assert f"{a.trend:.3f}" == "0.000" and round(a.p_trend, 2) == 1.00


def test_b3_b4_worked_example_a_monotone_climb_lights_both():
    climb = _pockets(list(zip(SIZES, (8, 24, 35, 40, 18))))          # 8%, 6%, 7%, 10%, 18%
    a = kg.association(climb, SCORES5)
    assert round(a.p_general, 4) == 0.0014 and round(a.p_trend, 4) == 0.0011
    assert a.df == 4 and a.direction == 1


def test_b3_on_k_minus_1_degrees_of_freedom():
    a = kg.association(_u_shape(), SCORES5)
    assert a.p_general == stats.chi2_sf(a.general, 4)
    assert a.p_general != stats.chi2_sf(a.general, 5)


def test_b3_with_one_pocket_is_the_ordinary_chi_square_times_n_minus_1_over_n():
    """B3: "With one pocket, Q = (N - 1)/N x the ordinary chi-square test of the K x 2 table"."""
    t = np.array([[12, 88], [30, 370], [45, 455], [40, 360], [25, 75]], float)
    a = kg.association(_pockets(list(zip(t.sum(1), t[:, 0]))), SCORES5)
    exp = np.outer(t.sum(1), t.sum(0)) / t.sum()
    pearson = float(((t - exp) ** 2 / exp).sum())
    N = t.sum()
    assert a.general == pytest.approx((N - 1) / N * pearson, rel=1e-12)


def test_b3_with_two_groups_is_cochran_mantel_haenszel():
    """B3: "With two groups it collapses to A6". A6's worked example: pockets A and B, CMH 3.53."""
    pk = _pockets([(100, 8), (100, 4)], [(200, 20), (200, 12)])
    a = kg.association(pk, [1, 2])
    chi, _ = stats.cmh([(8, 92, 4, 96), (20, 180, 12, 188)])
    assert a.general == pytest.approx(chi, rel=1e-12) and round(a.general, 2) == 3.53
    assert a.trend == pytest.approx(chi, rel=1e-12)        # two groups: the trend is the same one comparison


def test_the_trend_uses_its_scores():
    """Reversed scores flip the direction and keep the size; scores 1, 1, 1, 1, 2 give another statistic."""
    climb = _pockets(list(zip(SIZES, (8, 24, 35, 40, 18))))
    up, down = kg.association(climb, SCORES5), kg.association(climb, [5, 4, 3, 2, 1])
    assert down.trend == pytest.approx(up.trend) and (up.direction, down.direction) == (1, -1)
    assert kg.association(climb, [1, 1, 1, 1, 2]).trend != pytest.approx(up.trend)


def test_a_pocket_too_small_to_read_on_its_own_still_counts_in_the_pooled_test():
    """The goal's rule (4b): the floors on Control govern per-pocket readings only. A pocket of 6 loans with 2
    bad is far under any floor, and it still moves the pooled statistic; only a pocket that cannot say anything
    (no bad loan, every loan bad, or one loan) adds nothing."""
    big = [(100, 8), (400, 24), (500, 35), (400, 40), (100, 18)]
    thin = [(1, 1), (1, 0), (2, 0), (1, 0), (1, 1)]
    with_thin = kg.association(_pockets(big, thin), SCORES5)
    alone = kg.association(_pockets(big), SCORES5)
    assert with_thin.pockets == 2 and with_thin.general != pytest.approx(alone.general)
    silent = [(3, 0), (1, 0), (2, 0), (1, 0), (1, 0)]
    assert kg.association(_pockets(big, silent), SCORES5).general == pytest.approx(alone.general, rel=1e-15)


# --------------------------------------------------------------------------
# The cross-check: B3 is the score test of the conditional logistic model at "no effect"


def _book(seed, pockets=12, k=5):
    """Pockets of different sizes and base rates, K groups, a planted effect: data with nothing lined up. The
    effect is planted on the odds, the same in every pocket, so the model B5 fits is the one that made it."""
    rng = np.random.default_rng(seed)
    out = []
    odds = np.array([2.0, 1.0, 1.0, 0.9, 3.0, 1.3])[:k]
    for _ in range(pockets):
        n = rng.integers(2, 400, size=k)
        base = rng.uniform(0.02, 0.2)
        o = base / (1 - base) * odds
        out.append(kg.Pocket(n, rng.binomial(n, o / (1 + o))))
    return out


@pytest.mark.parametrize("pockets", [_u_shape(), _book(1), _book(2, pockets=40), _book(3, pockets=3, k=3)],
                         ids=["worked example", "12 pockets", "40 pockets", "3 groups"])
def test_b3_equals_the_conditional_score_test_to_nine_digits(pockets):
    k = len(pockets[0].loans)
    general = kg.association(pockets, list(range(1, k + 1))).general
    for ref in range(k):                                    # whichever group is the reference
        q, df = kg.score_test(pockets, ref)
        assert df == k - 1
        assert abs(q - general) <= 1e-9 * max(1.0, general), (q, general)


def _brute_loglik(tables, b):
    """The conditional log-likelihood in 40-digit decimals, by summing over every split of each pocket's bad
    loans among its groups (every (m_1 .. m_K) with sum m_h): no recursion, no tilting, nothing shared with
    kgroups.py but the definition."""
    getcontext().prec = 40
    eb = [Decimal(x).exp() for x in b]
    total = Decimal(0)
    for loans, bad in tables:
        m = sum(bad)
        if m == 0 or m == sum(loans):
            continue
        num = Decimal(1)
        for k, d in enumerate(bad):
            num *= eb[k] ** d
        den = Decimal(0)
        for split in product(*(range(min(r, m) + 1) for r in loans)):
            if sum(split) != m:
                continue
            term = Decimal(1)
            for k, j in enumerate(split):
                term *= Decimal(math.comb(loans[k], j)) * eb[k] ** j
            den += term
        total += num.ln() - den.ln()
    return total


SMALL = [([12, 20, 8], [3, 2, 3]), ([5, 15, 10], [2, 3, 1]), ([9, 11, 6], [1, 1, 3])]


def test_the_derivatives_used_are_the_likelihoods_own():
    """Finite differences of the 40-digit brute-force likelihood, with a step of 1e-12, against the gradient and
    Hessian kgroups.py works out from its polynomials: equal to 1e-9. So the score test above is the
    likelihood's own, not B3's formula in another form."""
    pk = [kg.Pocket(l, b) for l, b in SMALL]
    for at in ([0.0, 0.0, 0.0], [0.4, 0.0, -0.7]):
        ll, grad, hess = kg.conditional_terms(pk, at)
        h = Decimal("1e-12")
        base = [Decimal(x) for x in at]

        def L(*moves):
            b = list(base)
            for i, d in moves:
                b[i] += d
            return _brute_loglik(SMALL, b)

        assert abs(float(L()) - ll) < 1e-12
        for i in range(3):
            g = (L((i, h)) - L((i, -h))) / (2 * h)
            assert abs(float(g) - grad[i]) < 1e-9, (i, float(g), grad[i])
            for j in range(3):
                d2 = (L((i, h), (j, h)) - L((i, h), (j, -h)) - L((i, -h), (j, h)) + L((i, -h), (j, -h))) / (4 * h * h)
                assert abs(float(d2) - hess[i, j]) < 1e-9, (i, j, float(d2), hess[i, j])
    # and the score test worked out entirely from the brute force equals B3 to nine digits
    h = Decimal("1e-12")
    zero = [Decimal(0)] * 3
    free = [0, 2]

    def L0(*moves):
        b = list(zero)
        for i, d in moves:
            b[i] += d
        return _brute_loglik(SMALL, b)

    U = np.array([float((L0((i, h)) - L0((i, -h))) / (2 * h)) for i in free])
    info = -np.array([[float((L0((i, h), (j, h)) - L0((i, h), (j, -h)) - L0((i, -h), (j, h)) + L0((i, -h), (j, -h)))
                             / (4 * h * h)) for j in free] for i in free])
    q = float(U @ np.linalg.solve(info, U))
    assert abs(q - kg.association(pk, [1, 2, 3]).general) < 1e-9


# --------------------------------------------------------------------------
# B5: the conditional fit


def test_conditional_fit_matches_statsmodels_conditional_logit_on_a_fixed_example():
    """statsmodels 0.15.0's ConditionalLogit (method="newton") on SMALL, one row per loan, the middle group the
    reference, run 26 Sep 2026 and written in here. Its standard errors come from a numerical Hessian, good to
    about 1e-7; the cube's are exact, so they are held to 1e-6."""
    fit = kg.conditional_fit([kg.Pocket(l, b) for l, b in SMALL], ref=1)
    assert fit.method == kg.CONDITIONAL and fit.settled
    assert fit.beta[0] == pytest.approx(0.6781154104748787, abs=1e-9)
    assert fit.beta[2] == pytest.approx(0.9834216932479295, abs=1e-9)
    assert fit.se[0] == pytest.approx(0.6348384347933421, rel=1e-6)
    assert fit.se[2] == pytest.approx(0.6195158551269502, rel=1e-6)
    assert fit.p[0] == pytest.approx(0.2854438064840893, rel=1e-6)
    assert fit.p[2] == pytest.approx(0.11242126647158837, rel=1e-6)
    assert fit.loglik == pytest.approx(-41.16383939165008, abs=1e-9)
    assert fit.odds[1] == 1.0 and fit.beta[1] == 0.0 and fit.se[1] is None


def test_matched_pairs_the_conditional_fit_is_unbiased_where_the_unconditional_one_squares():
    """B5, "Breaks when": a constant per pocket biases thin pockets. The textbook case: 1-to-1 pairs, one loan in
    the group and one in the reference, one of the two bad. The conditional odds ratio is the discordant pairs'
    ratio, 60 / 30 = 2.0; the unconditional fit's is its square, 4.0 (Breslow & Day 1980, 7.2)."""
    pairs = [kg.Pocket([1, 1], [1, 0])] * 60 + [kg.Pocket([1, 1], [0, 1])] * 30 + [kg.Pocket([1, 1], [0, 0])] * 20
    cond = kg.conditional_fit(pairs, ref=1)
    unc = kg.unconditional_fit(pairs, ref=1)
    assert cond.odds[0] == pytest.approx(2.0, rel=1e-9)
    assert cond.se[0] == pytest.approx(math.sqrt(1 / 60 + 1 / 30), rel=1e-9)
    assert unc.odds[0] == pytest.approx(4.0, rel=1e-6)
    assert cond.pockets == 90                             # the 20 pairs with no bad loan say nothing


def test_conditional_and_unconditional_agree_on_big_pockets():
    """Where every pocket is large, conditioning costs nothing and changes nearly nothing: the scope's reason
    the unconditional fit is unbiased at that size."""
    rng = np.random.default_rng(5)
    pk = []
    for _ in range(4):
        n = np.array([800, 2000, 2400, 900])
        pk.append(kg.Pocket(n, rng.binomial(n, rng.uniform(0.04, 0.1) * np.array([1.8, 1.0, 1.0, 2.5]))))
    c, u = kg.conditional_fit(pk, 1), kg.unconditional_fit(pk, 1)
    for k in (0, 2, 3):
        assert abs(c.beta[k] - u.beta[k]) < 0.1 * c.se[k]


def test_b5_block_test_is_twice_the_log_likelihood_gain_on_k_minus_1_df():
    pk = _book(4, pockets=15, k=6)
    fit = kg.conditional_fit(pk, ref=2)
    assert fit.df == 5
    assert fit.block == pytest.approx(2 * (fit.loglik - fit.loglik0))
    assert fit.loglik0 == pytest.approx(kg.conditional_loglik(pk, np.zeros(6)), abs=1e-9)
    assert fit.loglik == pytest.approx(kg.conditional_loglik(pk, np.array([b for b in fit.beta])), abs=1e-9)
    assert fit.p_block == stats.chi2_sf(fit.block, 5)
    # and the block test is close to B3 (both ask "any difference?"; one is the score test, one the LR test)
    assert fit.block == pytest.approx(kg.association(pk, range(6)).general, rel=0.15)


def test_the_reference_group_is_the_one_compared_with():
    pk = _book(6, pockets=10, k=4)
    a, b = kg.conditional_fit(pk, ref=1), kg.conditional_fit(pk, ref=3)
    assert a.odds[1] == 1.0 and b.odds[3] == 1.0
    for k in range(4):
        # changing the reference only re-bases every log odds ratio
        assert a.beta[k] - a.beta[3] == pytest.approx(b.beta[k], abs=1e-8)
    assert a.block == pytest.approx(b.block, abs=1e-8)


def _mh_gap(pk, k, ref, fit):
    """How far B5's ln(odds ratio) sits from Mantel-Haenszel's, in standard deviations of that gap."""
    t = [(p.bad[k], p.loans[k] - p.bad[k], p.bad[ref], p.loans[ref] - p.bad[ref]) for p in pk]
    o, lo, hi = stats.mantel_haenszel(t, 1.96)
    se_mh = (math.log(hi) - math.log(o)) / 1.96                # Robins-Breslow-Greenland
    spread = se_mh ** 2 - fit.se[k] ** 2
    assert spread > 0                                          # the fit, the efficient one, is the tighter
    return abs(math.log(o) - fit.beta[k]) / math.sqrt(spread)


def test_b5_odds_ratios_agree_with_mantel_haenszel_within_the_spread_two_estimators_of_one_number_have():
    """Two estimators of one common odds ratio: B5's conditional fit of every group at once, and Mantel-Haenszel's
    pooling of each pocket's table of that group against the reference alone. They are not the same number
    (the fit also learns from the other groups, and Mantel-Haenszel is not the maximum of any likelihood), so
    nine digits is the wrong test. When one of two consistent estimators is efficient, their gap has standard
    deviation sqrt(SE_MH^2 - SE_fit^2) (Hausman 1978, lemma 2.1), so the gap measured in those units should
    behave like a standard normal. The tolerance is 4 of them: a gap that big happens by chance about once in
    16,000 comparisons, and a real fault (the wrong reference, a group's loans in another group) is dozens.

    The calibration is checked too: over 59 books with pockets as thin as 2 loans a group, about 5% of the
    236 gaps pass 2 standard deviations, as they should."""
    gaps = []
    for seed in range(1, 60):
        pk = _book(seed, pockets=20)
        fit = kg.conditional_fit(pk, ref=1)
        for k in (0, 2, 3, 4):
            gaps.append(_mh_gap(pk, k, 1, fit))
    assert max(gaps) < 4
    beyond = sum(g > 2 for g in gaps) / len(gaps)
    assert 0.01 < beyond < 0.10, beyond


def test_a_group_with_no_bad_loan_is_not_estimable_and_the_rest_is_fitted_at_the_limit():
    """Its odds ratio would be 0. The likelihood's limit is the pockets without its loans: the other groups' fit
    is the fit with that group taken out, and the block test uses the full likelihood at no effect."""
    pk = _pockets([(50, 5), (80, 4), (30, 0)], [(40, 6), (60, 3), (20, 0)])
    fit = kg.conditional_fit(pk, ref=1)
    assert fit.not_estimable == {2: kg.NO_BAD} and fit.odds[2] is None and fit.p[2] is None
    without = kg.conditional_fit(_pockets([(50, 5), (80, 4), (0, 0)], [(40, 6), (60, 3), (0, 0)]), ref=1)
    assert fit.beta[0] == pytest.approx(without.beta[0], abs=1e-9)
    assert fit.loglik0 == pytest.approx(kg.loglik_at_zero(pk)) and fit.df == 2


# --------------------------------------------------------------------------
# B5's worked example: scout-vs-measure.py's planted book, rebuilt with its seeds


def _make_book(n, seed):
    """docs/scout-vs-measure.py's make_book, line for line."""
    rng = np.random.default_rng(seed)
    fico = np.clip(rng.normal(680, 50, n), 500, 850)
    log_size = rng.normal(np.log(40000), 0.6, n)
    ratio = np.exp(rng.normal(-0.7, 0.8, n))
    noise1, noise2 = rng.normal(0, 1, n), rng.normal(0, 1, n)
    logit = np.log(0.05 / 0.95) - 0.02 * (fico - 680) + np.log(3) * (ratio > 2.0) + np.log(2) * (ratio < 0.1)
    bad = rng.random(n) < 1 / (1 + np.exp(-logit))
    return np.column_stack([fico, log_size, ratio, noise1, noise2]), bad.astype(int)


EDGES = [0.1, 0.25, 0.5, 1.0, 2.0]
REF = 2


def _design(X, with_bins=True):
    cols = [np.ones(len(X)), X[:, 0], X[:, 1]]
    b = np.digitize(X[:, 2], EDGES)
    if with_bins:
        cols += [(b == k).astype(float) for k in range(6) if k != REF]
    return np.column_stack(cols), b


@pytest.fixture(scope="module")
def planted():
    return _make_book(40000, 2223), _make_book(15000, 2024)


def test_b5_worked_example_the_holdout_table(planted):
    """statistics.md B5's table: the identical binned regression on the 15,000 holdout loans. Every loan count,
    bad count is reproduced, and every printed figure but three, each off by one in its last digit.
    statistics.md prints 0.39 for 0.50 - 1.00's p-value, and 2.66 (2.07 - 3.42) for >= 2.00; the maximum of the
    likelihood gives 0.3963 and 2.6650 (2.0735 - 3.4252), which print 0.40 and 2.67 (2.07 - 3.43). The
    script's scikit-learn fit (lbfgs at its default tolerance, on an unscaled FICO) stops just short of the
    maximum. The fit here is the maximum: statsmodels' Logit, run by hand on 26 Sep 2026, gives the same
    figures and log-likelihood -3583.7993. Recorded for the firm, not corrected in statistics.md."""
    _, (X, y) = planted
    D, b = _design(X)
    beta, se, ll, settled = kg.logistic(D, y)
    assert settled and round(ll, 4) == -3583.7993
    want = {0: (372, 48, 1.77, 1.26, 2.49, "0.001"), 1: (2583, 196, 1.02, 0.85, 1.24, "0.81"),
            3: (4512, 322, 0.93, 0.79, 1.10, "0.40"), 4: (2192, 150, 0.89, 0.72, 1.09, "0.26"),
            5: (639, 106, 2.67, 2.07, 3.43, "2e-14")}
    assert ((b == REF).sum(), y[b == REF].sum()) == (4702, 347)
    for k, (n, bad, o, lo, hi, p) in want.items():
        j = 3 + [x for x in range(6) if x != REF].index(k)
        assert ((b == k).sum(), y[b == k].sum()) == (n, bad)
        assert round(math.exp(beta[j]), 2) == o
        assert round(math.exp(beta[j] - 1.96 * se[j]), 2) == lo and round(math.exp(beta[j] + 1.96 * se[j]), 2) == hi
        pz = kg.p_normal(beta[j] / se[j])
        assert (f"{pz:.0e}" if pz < 1e-4 else f"{pz:.3f}".rstrip("0") if pz < 0.01 else f"{pz:.2f}") == p, pz


def test_b5_worked_example_the_block_test_on_development(planted):
    """2 x (-9388.3 - (-9515.8)) = 255.0 on 5 df."""
    (X, y), _ = planted
    D1, _ = _design(X)
    D0, _ = _design(X, with_bins=False)
    _, _, l1, _ = kg.logistic(D1, y)
    _, _, l0, _ = kg.logistic(D0, y)
    assert (round(l1, 1), round(l0, 1)) == (-9388.3, -9515.8)
    assert round(2 * (l1 - l0), 1) == 255.0


# --------------------------------------------------------------------------
# B6's worked example


def test_b6_worked_example_on_the_holdout(planted):
    """Group "ratio >= 2": 4.3% of loans carry 9.1% of the bad loans, at 2.13x the book's rate. Group "ratio >= 2
    or < 0.1": 6.7% of loans, 13.2% of the bad loans, 1.95x."""
    _, (X, y) = planted
    group = list(np.digitize(X[:, 2], EDGES))
    none = [None] * len(group)
    c = kg.concentration(group, list(y), none, 5)
    assert (f"{c.flag_rate:.1%}", f"{c.capture:.1%}", f"{c.lift:.2f}") == ("4.3%", "9.1%", "2.13")
    c = kg.concentration(group, list(y), none, {0, 5})
    assert (f"{c.flag_rate:.1%}", f"{c.capture:.1%}", f"{c.lift:.2f}") == ("6.7%", "13.2%", "1.95")


def test_b6_capture_in_dollars_leaves_out_only_an_unreadable_gco():
    group = [0, 0, 1, 1, 1]
    bad = [1, 0, 1, 1, 0]
    gco = [100.0, 0.0, 300.0, None, 0.0]
    c = kg.concentration(group, bad, gco, 1)
    assert (c.loans, c.flag_rate, c.bad, c.capture) == (3, 0.6, 2, 2 / 3)
    assert (c.gco, c.gco_capture) == (300.0, 0.75)
    assert c.lift == pytest.approx((2 / 3) / (3 / 5))
