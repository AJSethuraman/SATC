"""Deterministic statistics helpers.

Pure-Python, no numpy: percentile/stdev are implemented explicitly so results
are identical across platforms and reproducible from cache. All functions
treat ``None`` inputs as "not available" and exclude them rather than imputing.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence


def clean(values: Iterable[Optional[float]]) -> List[float]:
    """Drop ``None`` / NaN / inf and return a plain list of floats."""
    out: List[float] = []
    for v in values:
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f):
            continue
        out.append(f)
    return out


def percentile(values: Sequence[float], p: float) -> Optional[float]:
    """Linear-interpolation percentile (NumPy 'linear' / type-7), ``p`` in 0..100.

    Expects the caller to pass already-cleaned numeric values. Returns ``None``
    for an empty sample.
    """
    if not values:
        return None
    xs = sorted(values)
    n = len(xs)
    if n == 1:
        return xs[0]
    rank = (p / 100.0) * (n - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return xs[int(rank)]
    frac = rank - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def median(values: Sequence[float]) -> Optional[float]:
    return percentile(values, 50.0)


def mean(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def sample_stdev(values: Sequence[float]) -> Optional[float]:
    """Sample (n-1) standard deviation. Returns ``None`` for n < 2."""
    n = len(values)
    if n < 2:
        return None
    m = sum(values) / n
    var = sum((x - m) ** 2 for x in values) / (n - 1)
    return math.sqrt(var)


def coefficient_of_variation(values: Sequence[float]) -> Optional[float]:
    """CV = sample stdev / |mean|.

    Returns ``None`` if fewer than 2 points or the mean is ~0 (CV undefined).
    Always non-negative.
    """
    if len(values) < 2:
        return None
    m = mean(values)
    if m is None or abs(m) < 1e-12:
        return None
    sd = sample_stdev(values)
    if sd is None:
        return None
    return sd / abs(m)
