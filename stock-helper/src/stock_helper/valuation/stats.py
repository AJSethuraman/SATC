"""Robust statistics for valuation & screening (single home; pure).

Robust (median/MAD) rather than mean/stdev because fundamental cross-sections
are heavy-tailed and outlier-driven — the outliers are exactly what we want to
find, so they must not distort the scale we measure them against. Every
function is None/NaN-safe and never divides by zero.
"""

import math


def _clean(xs: list[float | None]) -> list[float]:
    return [float(x) for x in xs if x is not None and not math.isnan(float(x))]


def median(xs: list[float | None]) -> float | None:
    vals = sorted(_clean(xs))
    n = len(vals)
    if n == 0:
        return None
    mid = n // 2
    if n % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def mad(xs: list[float | None], scaled: bool = True) -> float | None:
    """Median absolute deviation. Scaled ×1.4826 → comparable to stdev under
    normality. None if <2 values or all identical (degenerate spread)."""
    vals = _clean(xs)
    if len(vals) < 2:
        return None
    med = median(vals)
    deviations = [abs(v - med) for v in vals]
    m = median(deviations)
    if m is None or m == 0:
        return None
    return m * 1.4826 if scaled else m


def robust_zscore(
    value: float | None,
    center: float | None,
    spread: float | None,
    clip: float | None = 3.0,
) -> float | None:
    """(value - center) / spread, optionally clipped to ±clip. None if any input
    is None or spread is non-positive (never divide-by-zero)."""
    if value is None or center is None or spread is None or spread <= 0:
        return None
    z = (value - center) / spread
    if clip is not None:
        z = max(-clip, min(clip, z))
    return z


def winsorize(
    xs: list[float | None], p_low: float = 0.05, p_high: float = 0.95
) -> list[float]:
    """Clamp values to empirical quantiles to tame outliers before taking a
    mean/median of peers. No-op for n < 5 (too few to trust quantiles)."""
    vals = _clean(xs)
    if len(vals) < 5:
        return vals
    lo = _quantile(vals, p_low)
    hi = _quantile(vals, p_high)
    return [max(lo, min(hi, v)) for v in vals]


def _quantile(vals: list[float], q: float) -> float:
    s = sorted(vals)
    if not s:
        return float("nan")
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def percentile_of(x: float | None, xs: list[float | None]) -> float:
    """Percentile rank of x within xs: share of values <= x, in percent
    (0-100). Ties count as <=. Empty peer set -> 50.0 (neutral)."""
    vals = _clean(xs)
    if x is None or not vals:
        return 50.0
    below_or_equal = sum(1 for v in vals if v <= x)
    return below_or_equal / len(vals) * 100.0
