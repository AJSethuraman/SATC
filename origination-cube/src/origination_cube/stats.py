"""The statistics behind the tests and the suggested thresholds, in plain Python.

No numpy here: the shuffle test (docs/statistics.md B2) is in perm.py, which
needs it. The letters and numbers below (A1, B1 ...) are the sections of
docs/statistics.md, the firm's reference for every test; tests/test_stats.py
reproduces each worked example there by calling these functions. The normal
quantile below is copied from portfolio-analysis-pack/src/analysis_pack/stats.py
(25 Sep 2026), where it is checked against Excel's NORM.S.INV; keep the two in
step by hand.

For the share of loans (a yes/no per loan) the smallest gap and the loans
needed are A3's power formula, exactly (ruling OC-37). For the dollar rates
they are still the approximation below, until the later wave that reads RANR
as a difference in points.

WHY THE SUGGESTIONS ARE COMPUTED, NOT FIXED. How many loans a pocket needs
before its rate means anything depends on the book: on its loss rate, on how
much loss sizes vary, and on how big a gap the firm wants to be able to see.
A fixed 30 is the same for a book losing 1% and one losing 10%, which is
wrong for at least one of them. So the suggestion is the textbook sample-size
calculation for comparing a rate with its peers, fed with the book's own
numbers:

    loans needed = ((z_conf + z_power * sqrt(gap)) * S_d / (x_bar * (gap - 1) * R))^2

    R      the book's rate, SUM(top) / SUM(bottom)
    d_i    each loan's top minus R times its bottom  (top_i - R * bottom_i)
    S_d    the standard deviation of d across the book's loans
    x_bar  the average bottom per loan (average balance, for a loss rate)
    gap    the multiple of the rate the firm wants to be able to see (worse_at)
    z_conf the normal quantile for the confidence, two-sided
    z_power the normal quantile for how often a real gap should be caught

S_d / (x_bar * sqrt(n)) is the standard error of a ratio of two sums (the
"ratio estimator", Cochran, Sampling Techniques, 3rd ed. 1977, section 6.3).
The sqrt(gap) lets a pocket that really is worse be noisier than the book, as
a count of bad loans is (its variance grows with its rate). With it, a plain
bad-loan rate of 4.65% gives the textbook two-proportion answers: about 2,750
loans to see a 1.25x gap and about 200 to see a 2x gap
(tests/test_stats.py).
It covers a dollar loss rate and a bad-loan rate alike: for a bad-loan rate
weighted by balance, top_i is the balance when the loan went bad and zero
otherwise. Two simplifications, stated because they are simplifications:
the pocket's loans are assumed to vary as much as the book's do, and the
peer group is assumed much bigger than the pocket, so its own noise is left
out. Both make the number a guide, not a guarantee, and the output says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_A = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
      1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
_B = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
      6.680131188771972e+01, -1.328068155288572e+01)
_C = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
      -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
_D = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
      3.754408661907416e+00)


def _norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def norm_s_inv(p: float) -> float:
    """The standard normal quantile: the z such that P(Z <= z) = p.

    Twin of Excel's NORM.S.INV. Refuses outside (0, 1) the way Excel does
    (Excel returns #NUM!; here a ValueError, which the caller turns into a
    refusal rather than a number).
    """
    if not (0.0 < p < 1.0):
        raise ValueError(f"norm_s_inv needs 0 < p < 1, got {p!r}")
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        x = ((((( _C[0]*q + _C[1])*q + _C[2])*q + _C[3])*q + _C[4])*q + _C[5]) / \
            (((( _D[0]*q + _D[1])*q + _D[2])*q + _D[3])*q + 1)
    elif p <= phigh:
        q = p - 0.5
        r = q * q
        x = ((((( _A[0]*r + _A[1])*r + _A[2])*r + _A[3])*r + _A[4])*r + _A[5]) * q / \
            ((((( _B[0]*r + _B[1])*r + _B[2])*r + _B[3])*r + _B[4])*r + 1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -((((( _C[0]*q + _C[1])*q + _C[2])*q + _C[3])*q + _C[4])*q + _C[5]) / \
             (((( _D[0]*q + _D[1])*q + _D[2])*q + _D[3])*q + 1)
    # One Newton step on the exact CDF takes the approximation to full double.
    for _ in range(2):
        e = _norm_cdf(x) - p
        d = _norm_pdf(x)
        if d == 0.0:
            break
        x -= e / d
    return x


def z_for_confidence(confidence: float) -> float:
    """z such that the central interval covers `confidence`: NORM.S.INV(1-(1-c)/2)."""
    return norm_s_inv(1.0 - (1.0 - confidence) / 2.0)


@dataclass(frozen=True)
class LoansNeeded:
    """How many loans a pocket needs before a gap of `gap` shows reliably.
    Guidance on what a pocket of a given size can and cannot show; never a
    gate, because a larger gap shows in a smaller pocket (a 6x pocket of 500
    loans is plain even where a 1.25x gap would need 3,500)."""
    measure: str
    loans: int | None           # None when the book's rate is zero, or no pocket of this book could show the gap
    rate: float | None
    s_d: float
    x_bar: float
    gap: float
    confidence: float
    power: float
    book_loans: int
    method: str = "ratio"       # "ratio": the approximation above; "two_prop": A3, for a yes/no per loan

    def sentence(self) -> str:
        if self.loans is None and self.rate:
            return (f"{self.measure}: no pocket of this book could tell a {self.gap:g}x gap from luck "
                    f"{self.power:.0%} of the time at {self.confidence:.0%} confidence")
        if self.loans is None:
            return f"{self.measure}: the book's rate is zero, so no gap can be sized"
        share = self.loans / self.book_loans if self.book_loans else 0
        return (f"{self.measure}: about {self.loans:,} loans before a {self.gap:g}x gap can be told from luck "
                f"{self.power:.0%} of the time at {self.confidence:.0%} confidence "
                f"({share:.1%} of this book's loans)")


def loans_needed(measure: str, pairs: list[tuple[float, float]], gap: float, confidence: float,
                 power: float) -> LoansNeeded:
    """`pairs` is (top, bottom) per loan that entered the rate."""
    n = len(pairs)
    sy = math.fsum(p[0] for p in pairs)
    sx = math.fsum(p[1] for p in pairs)
    rate = sy / sx if sx else None
    x_bar = sx / n if n else 0.0
    if not rate or n < 2 or gap <= 1:
        return LoansNeeded(measure, None, rate, 0.0, x_bar, gap, confidence, power, n)
    d = [y - rate * x for y, x in pairs]
    mean_d = math.fsum(d) / n
    s_d = math.sqrt(math.fsum((v - mean_d) ** 2 for v in d) / (n - 1))
    z = norm_s_inv(1 - (1 - confidence) / 2) + norm_s_inv(power) * math.sqrt(gap)
    need = (z * s_d / (x_bar * (gap - 1) * rate)) ** 2
    return LoansNeeded(measure, math.ceil(need), rate, s_d, x_bar, gap, confidence, power, n)


# --------------------------------------------------------------------------
# A yes/no per loan (the share of loans): the pooled two-proportion z test (A1)
# at or above the fewest-loans floor, Fisher's exact test (B1) below it, and
# A3's power for "smallest gap it could show" and "loans needed".


def pooled_se(x1: float, n1: int, x2: float, n2: int) -> float | None:
    """A1's standard error of the gap under "no difference": both groups share
    the pooled rate (x1 + x2) / (n1 + n2)."""
    if n1 <= 0 or n2 <= 0:
        return None
    pbar = (x1 + x2) / (n1 + n2)
    return math.sqrt(max(pbar * (1 - pbar), 0.0) * (1 / n1 + 1 / n2))


def two_prop_z(x1: float, n1: int, x2: float, n2: int) -> tuple[float | None, float | None]:
    """A1: (z, two-sided p) for x1 bad of n1 against x2 bad of n2, pooled (ruling
    OC-37). None where there is nothing to compare."""
    se = pooled_se(x1, n1, x2, n2)
    if se is None:
        return None, None
    if se == 0:                     # every loan bad, or none: the two rates are the same
        return 0.0, 1.0
    z = (x1 / n1 - x2 / n2) / se
    return z, math.erfc(abs(z) / math.sqrt(2.0))


def _hypergeom_logs(n1: int, K: int, N: int) -> tuple[int, list[float]]:
    """(lowest k, log P(k) for every k it can take) for the bad count in n1 loans
    drawn from N of which K are bad. Built by the ratio of neighbours,
    P(k+1)/P(k) = (K-k)(n1-k) / ((k+1)(N-K-n1+k+1)), so it stays exact for books
    of a million loans where C(N, n1) itself would overflow."""
    if not (0 <= K <= N and 0 <= n1 <= N):
        raise ValueError(f"hypergeometric needs 0 <= K <= N and 0 <= n1 <= N; got n1={n1}, K={K}, N={N}")
    lo, hi = max(0, n1 - (N - K)), min(K, n1)
    logs = [0.0]
    for k in range(lo, hi):
        logs.append(logs[-1] + math.log((K - k) * (n1 - k)) - math.log((k + 1) * (N - K - n1 + k + 1)))
    top = max(logs)
    norm = top + math.log(math.fsum(math.exp(v - top) for v in logs))
    return lo, [v - norm for v in logs]


def hypergeom_pmf(k: int, n1: int, K: int, N: int) -> float:
    """B1's P(k) = C(K, k) C(N - K, n1 - k) / C(N, n1)."""
    lo, logs = _hypergeom_logs(n1, K, N)
    return math.exp(logs[k - lo]) if lo <= k < lo + len(logs) else 0.0


def fisher_exact(k: int, n1: int, K: int, N: int) -> float:
    """B1: two-sided p of Fisher's exact test. A pocket of n1 loans with k bad,
    in N loans (pocket and rest) with K bad: the sum of P(k') over every count
    k' no more likely than k. Ties are kept within a relative 1e-7, the
    rounding of the arithmetic, never dropped by it."""
    if not (0 <= k <= n1 and k <= K and n1 - k <= N - K):
        raise ValueError(f"a pocket of {n1} can't have {k} bad when {K} of {N} are bad")
    lo, logs = _hypergeom_logs(n1, K, N)
    cut = logs[k - lo] + math.log1p(1e-7)
    return min(1.0, math.fsum(math.exp(v) for v in logs if v <= cut))


def power_two_prop(p1: float, n1: int, p2: float, n2: int, confidence: float) -> float:
    """A3: the chance a pocket of n1 at a true rate p1 is called different from a
    rest of n2 at p2, by A1 at `confidence`, two-sided.
    power = PHI((|p1 - p2| - z * SE0) / SE1), SE0 under "no difference" (pooled),
    SE1 when the gap is real."""
    pbar = (n1 * p1 + n2 * p2) / (n1 + n2)
    se0 = math.sqrt(max(pbar * (1 - pbar), 0.0) * (1 / n1 + 1 / n2))
    se1 = math.sqrt(max(p1 * (1 - p1), 0.0) / n1 + max(p2 * (1 - p2), 0.0) / n2)
    edge = abs(p1 - p2) - z_for_confidence(confidence) * se0
    if se1 == 0:
        return 1.0 if edge > 0 else 0.0
    return _norm_cdf(edge / se1)


def mde_two_prop(n1: int, p2: float | None, n2: int, confidence: float, power: float) -> float | None:
    """A3's smallest gap it could show: the smallest rate p1 above p2 that a
    pocket of n1 against a rest of n2 at p2 catches `power` of the time, as the
    multiple p1 / p2. None when no rate short of 99.9% would be caught."""
    if not p2 or not 0 < p2 < 1 or n1 < 1 or n2 < 1:
        return None
    if power_two_prop(0.999, n1, p2, n2, confidence) < power:
        return None
    lo, hi = p2, 0.999
    for _ in range(100):
        mid = (lo + hi) / 2
        if power_two_prop(mid, n1, p2, n2, confidence) < power:
            lo = mid
        else:
            hi = mid
    return hi / p2


def loans_needed_two_prop(measure: str, rate: float | None, book_loans: int, gap: float, confidence: float,
                          power: float) -> LoansNeeded:
    """A3 turned round: the fewest loans a pocket of this book needs to catch a
    pocket at `gap` times the book's rate, against the rest of the book,
    `power` of the time. The rest is the book less the pocket, so a pocket past
    half the book only gets harder to read; when even half the book can't show
    the gap, there is no number (loans None, the rate kept)."""
    n = book_loans
    s_d = math.sqrt(rate * (1 - rate)) if rate and 0 < rate < 1 else 0.0
    out = dict(measure=measure, rate=rate, s_d=s_d, x_bar=1.0, gap=gap, confidence=confidence, power=power,
               book_loans=n, method="two_prop")
    if not rate or not 0 < rate < 1 or gap <= 1 or gap * rate >= 1 or n < 4:
        return LoansNeeded(loans=None, **out)

    def caught(n1: int) -> bool:
        return power_two_prop(gap * rate, n1, rate, n - n1, confidence) >= power

    lo, hi = 1, n // 2
    if not caught(hi):
        return LoansNeeded(loans=None, **out)
    while lo < hi:                  # the chance rises with the pocket up to half the book
        mid = (lo + hi) // 2
        if caught(mid):
            hi = mid
        else:
            lo = mid + 1
    return LoansNeeded(loans=lo, **out)


@dataclass(frozen=True)
class MaterialityRow:
    threshold: float            # excess, in the numerator's units
    share_of_losses: float      # threshold / the book's total numerator
    pockets: int                # pockets with excess at or above the threshold
    captured: float             # share of the grid's positive excess those pockets hold


def materiality_ladder(excesses: list[float], book_total: float,
                       shares: tuple[float, ...] = (0.005, 0.01, 0.02, 0.05, 0.10)) -> list[MaterialityRow]:
    """What each candidate threshold keeps: how many pockets, and how much of
    the grid's bleed they explain. For designing the threshold with the
    trade-off in view rather than picking a number blind."""
    pos = sorted((e for e in excesses if e > 0), reverse=True)
    total = math.fsum(pos)
    out = []
    for s in shares:
        t = s * book_total
        kept = [e for e in pos if e >= t]
        out.append(MaterialityRow(t, s, len(kept), math.fsum(kept) / total if total else 0.0))
    return out


def threshold_explaining(excesses: list[float], share: float) -> float | None:
    """The smallest excess such that the pockets at or above it together hold
    `share` of the grid's positive excess (the Pareto cut). None when nothing
    bleeds."""
    pos = sorted((e for e in excesses if e > 0), reverse=True)
    total = math.fsum(pos)
    if total <= 0:
        return None
    run = 0.0
    for e in pos:
        run += e
        if run >= share * total - 1e-9 * total:
            return e
    return pos[-1]


# --------------------------------------------------------------------------
# One pocket against its peers. Everything is built from six sums per pocket
# (n, SUM y, SUM x, SUM y^2, SUM x^2, SUM x*y), which add up across pockets, so
# the peers of a pocket are its parent's sums minus its own, and Excel can do
# the same arithmetic from the same six columns.


def ratio_se(n: int, sy: float, sx: float, syy: float, sxx: float, sxy: float) -> float | None:
    """Standard error of SUM(y)/SUM(x) over n loans (the ratio estimator)."""
    if n < 2 or sx == 0:
        return None
    r = sy / sx
    s_dd = (syy - 2 * r * sxy + r * r * sxx) / (n - 1)
    s_dd = max(s_dd, 0.0)            # rounding can leave a hair below zero
    return math.sqrt(s_dd / n) / (sx / n)


def multiple(ra: float, rb: float) -> float | None:
    """How many times its comparison a rate is: ra / rb, and, when the comparison
    is negative, 1 + (ra - rb) / |rb|, so a lower rate always gives a lower
    multiple. Two negative RANRs divided the plain way put the pocket earning
    less above 1.00x: -3.8% against -1.8% read 2.11x, "better" (found writing up
    the tests for the firm, 25 Sep 2026). With a positive comparison the two
    are the same number."""
    if not rb:
        return None
    return ra / rb if rb > 0 else 1 + (ra - rb) / abs(rb)


def compare(a: tuple, b: tuple) -> tuple[float | None, float | None]:
    """(a's rate over b's, two-sided p that the rates differ by luck).
    a and b are (n, sy, sx, syy, sxx, sxy). None where it cannot be worked out.
    The p is the ratio-estimator z test the audit found behind every rate
    (statistics.md A10). Since 25 Sep 2026 no pocket is judged by it: the share
    of loans uses two_prop_z and fisher_exact, every dollar rate perm.py."""
    if a[2] == 0 or b[2] == 0:
        return None, None
    ra, rb = a[1] / a[2], b[1] / b[2]
    idx = multiple(ra, rb)
    sea, seb = ratio_se(*a), ratio_se(*b)
    if sea is None or seb is None:
        return idx, None
    se = math.sqrt(sea * sea + seb * seb)
    if se == 0:
        return idx, (1.0 if ra == rb else 0.0)
    z = (ra - rb) / se
    return idx, math.erfc(abs(z) / math.sqrt(2.0))


def smallest_gap(n: int, rate: float | None, s_d: float, x_bar: float, confidence: float,
                 power: float) -> float | None:
    """The smallest multiple of the book's rate that a pocket of n loans like
    the book's could show, `power` of the time at `confidence`: the size
    calculation above, solved for the gap instead of the loans."""
    if not rate or n < 2 or x_bar == 0 or s_d == 0:
        return None
    za = norm_s_inv(1 - (1 - confidence) / 2)
    zb = norm_s_inv(power)

    def needed(g: float) -> float:
        return ((za + zb * math.sqrt(g)) * s_d / (x_bar * (g - 1) * rate)) ** 2

    lo, hi = 1.0 + 1e-9, 2.0
    while needed(hi) > n:
        hi *= 2
        if hi > 1e6:
            return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if needed(mid) > n:
            lo = mid
        else:
            hi = mid
    return hi


def smallest_gap_for(ln: LoansNeeded, n: int, confidence: float, power: float) -> float | None:
    """The smallest gap a pocket of n loans could show, by the method its rate
    was sized with: A3 for a yes/no per loan (a pocket of n against the rest of
    the book at the book's rate), the approximation above for a dollar rate."""
    if ln.method == "two_prop":
        return mde_two_prop(n, ln.rate, ln.book_loans - n, confidence, power)
    return smallest_gap(n, ln.rate, ln.s_d, ln.x_bar, confidence, power)


# --------------------------------------------------------------------------
# Splitting every pocket in two (the within-pocket split): is the high half
# worse than the low half, pocket for pocket, once FICO and segment are held
# fixed? Each pocket is one stratum. mantel_haenszel is copied from
# portfolio-analysis-pack/src/analysis_pack/stats.py (25 Sep 2026); keep the
# two in step by hand.

def mantel_haenszel(strata: list[tuple[int, int, int, int]], z: float) -> tuple[float | None, float | None, float | None]:
    """(OR_MH, lo, hi) over strata of (a, b, c, d). Mantel & Haenszel 1959;
    variance of ln OR_MH per Robins, Breslow & Greenland 1986, written the
    way the sheet's SUMPRODUCT helpers write it. None when a sum is zero."""
    P = Q = R = S = 0.0
    PR = PS = QR = QS = 0.0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n == 0:
            continue
        p = (a + d) / n
        q = (b + c) / n
        r = a * d / n
        s = b * c / n
        R += r; S += s
        PR += p * r; PS += p * s; QR += q * r; QS += q * s
    if R == 0.0 or S == 0.0:
        return None, None, None
    o = R / S
    var = PR / (2 * R * R) + (PS + QR) / (2 * R * S) + QS / (2 * S * S)
    se = math.sqrt(var)
    return o, math.exp(math.log(o) - z * se), math.exp(math.log(o) + z * se)


def cmh(strata: list[tuple[int, int, int, int]]) -> tuple[float | None, float | None]:
    """A6: (chi-square, two-sided p) of the Cochran-Mantel-Haenszel test that the
    common odds ratio is 1, with no continuity correction (ruling OC-36; Check
    names it). Strata are (a, b, c, d): high-half events, high-half
    non-events, low-half events, low-half non-events."""
    num = var = 0.0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n < 2:
            continue
        num += a - (a + b) * (a + c) / n
        var += (a + b) * (c + d) * (a + c) * (b + d) / (n * n * (n - 1))
    if var <= 0:
        return None, None
    chi = num * num / var
    return chi, math.erfc(math.sqrt(chi / 2))


def cmh_p(strata: list[tuple[int, int, int, int]]) -> float | None:
    """A6's p-value alone."""
    return cmh(strata)[1]


def chi2_sf(x: float, k: int) -> float:
    """P(chi-square with k degrees of freedom > x): the regularised upper
    incomplete gamma Q(k/2, x/2), by series or continued fraction
    (Numerical Recipes, 6.2)."""
    if x <= 0:
        return 1.0
    a, z = k / 2.0, x / 2.0
    gln = math.lgamma(a)
    if z < a + 1:
        term = total = 1.0 / a
        ap = a
        for _ in range(500):
            ap += 1
            term *= z / ap
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return max(0.0, 1.0 - total * math.exp(-z + a * math.log(z) - gln))
    b = z + 1 - a
    c = 1 / 1e-300
    d = 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-z + a * math.log(z) - gln) * h


def cochran_q(strata: list[tuple[int, int, int, int]], pooled_or: float | None) -> tuple[float | None, int]:
    """A8's Q: the pockets' log odds ratios (Woolf weights, 0.5 added to every
    cell of a pocket with a zero) spread about the pooled ratio. Centred on
    ln OR_MH rather than A8's weighted mean: on A8's example that moves p from
    0.80511 to 0.80510 (the audit, item j). Returns (Q, the pockets it rests on)."""
    if not pooled_or or pooled_or <= 0:
        return None, 0
    q, k = 0.0, 0
    for a, b, c, d in strata:
        if a + c == 0 or b + d == 0 or a + b == 0 or c + d == 0:
            continue
        if min(a, b, c, d) == 0:
            a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        w = 1 / (1 / a + 1 / b + 1 / c + 1 / d)
        q += w * (math.log(a * d / (b * c)) - math.log(pooled_or)) ** 2
        k += 1
    return q, k


def steadiness_p(strata: list[tuple[int, int, int, int]], pooled_or: float | None) -> tuple[float | None, int]:
    """Is the high-vs-low effect the same in every pocket? Cochran's Q (A8)
    against chi-square on pockets - 1. A small p means the effect differs
    between pockets: look at the heat map for which. Returns (p, the number of
    pockets it rests on)."""
    q, k = cochran_q(strata, pooled_or)
    if q is None or k < 2:
        return None, k
    return chi2_sf(q, k - 1), k
