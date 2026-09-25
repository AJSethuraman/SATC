"""The statistics behind the suggested thresholds, in plain Python.

No numpy. The normal quantile below is copied from
portfolio-analysis-pack/src/analysis_pack/stats.py (25 Sep 2026), where it is
checked against Excel's NORM.S.INV; keep the two in step by hand.

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
    loans: int | None           # None when the book's rate is zero
    rate: float | None
    s_d: float
    x_bar: float
    gap: float
    confidence: float
    power: float
    book_loans: int

    def sentence(self) -> str:
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


def compare(a: tuple, b: tuple) -> tuple[float | None, float | None]:
    """(a's rate over b's, two-sided p that the rates differ by luck).
    a and b are (n, sy, sx, syy, sxx, sxy). None where it cannot be worked out."""
    if a[2] == 0 or b[2] == 0:
        return None, None
    ra, rb = a[1] / a[2], b[1] / b[2]
    idx = ra / rb if rb else None
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
