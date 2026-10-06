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
    5 High from           Moderate-High's line + high_fraction x (worst kept
                          - Moderate-High's line)

For a measure where lower is worse (a credit score), "-" and "+" swap and the
worst kept is the lowest. The three multipliers are the bank's; nothing here
has a default.
"""
from __future__ import annotations

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


def scale(kept: Sequence[Optional[float]], direction: str, halfwidth: float, low_step: float,
          high_fraction: float, floor_at_zero: bool) -> dict:
    """Lines where scores 2, 3, 4 and 5 begin, or a refusal saying why not."""
    vals = [v for v in kept if v is not None]
    s = 1.0 if direction == "higher_is_worse" else -1.0
    med = statistics.median(vals)
    move = typical_yearly_move(kept)
    worst = max(vals) if s > 0 else min(vals)
    out = {"median": med, "typical_yearly_move": move, "worst": worst, "bounds": None, "refused": None}
    b3 = med - s * halfwidth * move
    b4 = med + s * halfwidth * move
    b2 = med - s * low_step * move
    b5 = b4 + high_fraction * (worst - b4)
    if floor_at_zero and s > 0 and med <= 0:
        out["refused"] = "the median is at or below zero"
    elif low_step <= halfwidth:
        out["refused"] = "Moderate-Low must begin further from the median than Moderate"
    elif s * (worst - b4) <= 0:
        out["refused"] = "nothing kept is worse than Moderate-High's line"
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
