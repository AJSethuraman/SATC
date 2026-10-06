"""Interval arithmetic in plain Python, written to mirror the Excel formulas.

Every function here is the Python twin of a formula the workbook carries, and
the `_check` tab compares the two. The arithmetic is deliberately the same
shape as the formula text in `workbook.py` so that a disagreement means one of
them is wrong rather than that they rounded differently.

No numpy: the bank desk has none. The normal quantile and the inverse of the
regularised incomplete beta function are implemented here to double precision,
which is well inside the check tab's tolerance of one part in a million on an
interval bound.

Sources (the formulas are standard; the citations say which form is used):
- Wilson, E. B. (1927). Probable inference, the law of succession, and
  statistical inference. JASA 22:209-212. The form here is the one in Brown,
  Cai & DasGupta (2001), Statistical Science 16:101-133, eq. (4).
- Clopper, C. J. & Pearson, E. S. (1934). The use of confidence or fiducial
  limits illustrated in the case of the binomial. Biometrika 26:404-413. The
  beta-quantile form: lower = B^-1(alpha/2; x, n-x+1), upper =
  B^-1(1-alpha/2; x+1, n-x).
- The regularised incomplete beta by continued fraction follows Numerical
  Recipes (Press et al.), section 6.4; the normal quantile uses Acklam's
  rational approximation refined by one Newton step on math.erfc.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------
# Normal quantile — the twin of _xlfn.NORM.S.INV
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Regularised incomplete beta and its inverse — the twin of _xlfn.BETA.INV
# --------------------------------------------------------------------------

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (Numerical Recipes 6.4)."""
    max_it, eps, fpmin = 300, 3.0e-16, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_it + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def beta_cdf(x: float, a: float, b: float) -> float:
    """I_x(a, b): the regularised incomplete beta function, the Beta(a,b) CDF."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def beta_inv(p: float, a: float, b: float) -> float:
    """The x with I_x(a, b) = p. Twin of Excel's BETA.INV(p, a, b).

    Bisection to a bracket, then Newton on the CDF; monotone and bounded, so
    it cannot wander. Accurate to about 1e-14 on the cases the pack uses.
    """
    if not (0.0 <= p <= 1.0):
        raise ValueError(f"beta_inv needs 0 <= p <= 1, got {p!r}")
    if a <= 0.0 or b <= 0.0:
        raise ValueError("beta_inv needs a > 0 and b > 0")
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    x = a / (a + b)
    for _ in range(200):
        f = beta_cdf(x, a, b) - p
        if f == 0.0:
            return x
        if f < 0.0:
            lo = x
        else:
            hi = x
        # Newton step from the density, falling back to bisection when it
        # leaves the bracket or the density is degenerate.
        lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        if 0.0 < x < 1.0:
            dens = math.exp((a - 1.0) * math.log(x) + (b - 1.0) * math.log(1.0 - x) - lbeta)
        else:
            dens = 0.0
        nx = x - f / dens if dens > 0.0 else None
        if nx is None or not (lo < nx < hi):
            nx = 0.5 * (lo + hi)
        if abs(nx - x) < 1e-15:
            return nx
        x = nx
    return x


# --------------------------------------------------------------------------
# The intervals themselves
# --------------------------------------------------------------------------

def wilson(events: int, n: int, z: float) -> tuple[float, float]:
    """Wilson score interval for events/n at the given z. Mirrors the formula
    text in workbook.py term for term."""
    if n <= 0:
        raise ValueError("wilson needs n > 0")
    p = events / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z / denom * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return centre - half, centre + half


def clopper_pearson(events: int, n: int, confidence: float) -> tuple[float, float]:
    """Clopper-Pearson (exact) interval, the beta-quantile form Excel writes."""
    if n <= 0:
        raise ValueError("clopper_pearson needs n > 0")
    alpha = 1.0 - confidence
    lo = 0.0 if events == 0 else beta_inv(alpha / 2.0, events, n - events + 1)
    hi = 1.0 if events == n else beta_inv(1.0 - alpha / 2.0, events + 1, n - events)
    return lo, hi


def interval(events: int, n: int, confidence: float, method: str) -> tuple[float, float]:
    """The interval the workbook's METHOD switch selects."""
    if method == "Wilson":
        return wilson(events, n, z_for_confidence(confidence))
    if method == "Clopper-Pearson":
        return clopper_pearson(events, n, confidence)
    raise ValueError(f"unknown interval method {method!r}")


# --------------------------------------------------------------------------
# Odds ratios: crude (Woolf interval) and Mantel-Haenszel pooled (RBG interval)
# --------------------------------------------------------------------------

def crude_odds_ratio(a: int, b: int, c: int, d: int, z: float) -> tuple[float | None, float | None, float | None]:
    """(OR, lo, hi) from a 2x2 of flagged events a, flagged non-events b,
    unflagged events c, unflagged non-events d. None when any cell is zero
    (the sheet prints 'not estimable'). Woolf: exp(ln OR ± z·sqrt(1/a+1/b+1/c+1/d))."""
    if min(a, b, c, d) == 0:
        return None, None, None
    o = (a * d) / (b * c)
    se = math.sqrt(1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d)
    return o, math.exp(math.log(o) - z * se), math.exp(math.log(o) + z * se)


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


def survives_word(crude: tuple, pooled: tuple, threshold: float) -> str:
    """The step-4 word, the same rule as the sheet's formula (PRD §6.7):
    'no crude effect' when the crude interval contains 1 or is not estimable;
    'collapses' when the pooled OR has lost more than `threshold` of the crude
    log-odds; 'survives' when it kept it and the pooled interval excludes 1;
    'unknown' otherwise, including when the pooled OR is not estimable."""
    o, lo, hi = crude
    if o is None or lo <= 1.0 <= hi:
        return "no crude effect"
    m, mlo, mhi = pooled
    if m is None:
        return "unknown"
    kept = math.log(m) / math.log(o)
    if kept < 1.0 - threshold:
        return "collapses"
    if mlo > 1.0 or mhi < 1.0:
        return "survives"
    return "unknown"
