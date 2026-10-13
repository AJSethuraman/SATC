"""The rating scale, centred on normal. The workbook's Thresholds tab computes
the same thing with live formulas; this is the reference its tests are held to.

The bank, 6 October 2026: *"I would think median is a 3 if anything ...
there's likely a range around it that represents the same risk as the
center."* So Moderate is a band around the median of the quarters kept, as
wide as the measure's ordinary year-to-year movement says, and the other lines
are measured from it:

    typical yearly move   1.4826 x the median absolute deviation of every
                          four-quarter change whose both ends are kept
    3 Moderate from       median - halfwidth x typical yearly move
    4 Moderate-High from  median + halfwidth x typical yearly move
    2 Moderate-Low from   median - low_step x typical yearly move
    spread of levels      1.4826 x the median absolute deviation of the quarters
                          kept from their median
    5 High from           median + high_z x spread of levels: the same robust z
                          the evidence uses to call a level unusual. One number
                          with one meaning on every product, and it rests on the
                          bulk of history, not on the single worst quarter.

For a measure where lower is worse (a credit score), "-" and "+" swap and the
worst kept is the lowest. The three settings are the bank's; nothing here has a
default.
"""
from __future__ import annotations

import math
import statistics
from typing import Optional, Sequence

ROBUST_SCALE = 1.4826


def typical_yearly_move(kept: Sequence[Optional[float]], lag: int = 4) -> Optional[float]:
    """Robust spread of the change over ``lag`` periods, using only pairs whose
    both ends are kept (None marks a period left out or missing)."""
    changes = [b - a for a, b in zip(kept, kept[lag:]) if a is not None and b is not None]
    if len(changes) < 2:
        return None
    m = statistics.median(changes)
    return ROBUST_SCALE * statistics.median([abs(c - m) for c in changes])


def weighted_median(values, weights):
    """Midpoint of the lower and upper weighted medians: the first value at
    which cumulative weight reaches half, and the first at which it passes
    half. With equal weights this is the ordinary median."""
    pairs = sorted(zip(values, weights))
    half, cum, lower, upper = sum(weights) / 2, 0.0, None, None
    for v, w in pairs:
        cum += w
        if lower is None and cum >= half:
            lower = v
        if cum > half:
            upper = v
            break
    return (lower + upper) / 2


def recency_weights(dates, half_life_years):
    """0.5 ** (age in years / half-life), age counted back from the last date.

    A half-life must be a number above 0 years: 0 cannot be divided by, and a
    negative one would weigh old observations above recent ones, the reverse
    of what recency means. Refused here, so every front door refuses it."""
    if isinstance(half_life_years, bool) or not isinstance(half_life_years, (int, float))             or not half_life_years > 0 or not math.isfinite(half_life_years):
        raise ValueError("a half-life must be a number of years above 0, not %r" % (half_life_years,))
    def months(d):
        return int(d[:4]) * 12 + int(d[5:7])
    last = months(dates[-1])
    return [0.5 ** ((last - months(d)) / 12 / half_life_years) for d in dates]


def level_spread(vals: Sequence[float]) -> float:
    med = statistics.median(vals)
    return ROBUST_SCALE * statistics.median([abs(v - med) for v in vals])


def scale(kept: Sequence[Optional[float]], direction: str, halfwidth: float, low_step: float,
          high_z: float, floor_at_zero: bool,
          weights: Optional[Sequence[float]] = None) -> dict:
    """Lines where scores 2, 3, 4 and 5 begin, or a refusal saying why not.

    ``weights``, one per entry of ``kept``, weight the median only (recency):
    the typical yearly move, the spread of levels and the worst kept stay at
    full weight, so the scale does not forget what stress looked like."""
    vals = [v for v in kept if v is not None]
    s = 1.0 if direction == "higher_is_worse" else -1.0
    med = (statistics.median(vals) if weights is None else
           weighted_median(vals, [w for v, w in zip(kept, weights) if v is not None]))
    move = typical_yearly_move(kept)
    worst = max(vals) if s > 0 else min(vals)
    spread = level_spread(vals)
    out = {"median": med, "typical_yearly_move": move, "spread_of_levels": spread, "worst": worst,
           "bounds": None, "refused": None}
    if move is None:
        out["refused"] = "too little history kept for a typical yearly move (two four-quarter changes needed)"
        return out
    b3 = med - s * halfwidth * move
    b4 = med + s * halfwidth * move
    b2 = med - s * low_step * move
    b5 = med + s * high_z * spread
    if floor_at_zero and s > 0 and med <= 0:
        out["refused"] = "the median is at or below zero"
    elif low_step <= halfwidth:
        out["refused"] = "Moderate-Low must begin further from the median than Moderate"
    elif s * (b5 - b4) <= 0:
        out["refused"] = "High must begin beyond Moderate-High's line"
    elif s * (worst - b5) < 0:
        out["refused"] = "High would begin beyond the worst quarter kept: nothing kept could rate High"
    elif floor_at_zero and s > 0 and b2 <= 0:
        out["refused"] = "Moderate-Low would begin at or below zero"
    else:
        out["bounds"] = [b2, b3, b4, b5]
    return out


def score(value: float, bounds: Sequence[float], direction: str, on_the_line: str,
          floor_at_zero: bool) -> int:
    if floor_at_zero and direction == "higher_is_worse" and value <= 0:
        return 1
    if direction == "higher_is_worse":
        hit = (lambda b: value >= b) if on_the_line == "worse" else (lambda b: value > b)
    else:
        hit = (lambda b: value <= b) if on_the_line == "worse" else (lambda b: value < b)
    return 1 + sum(1 for b in bounds if hit(b))
