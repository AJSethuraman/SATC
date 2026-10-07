"""Stage 1: check the series and apply the declared smoothing.

Nothing here guesses. A gap inside the window is refused rather than
interpolated, because a filled-in quarter is a number nobody published.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

#: Months between consecutive observations, by declared frequency.
STEP_MONTHS = {"quarterly": 3, "monthly": 1}


@dataclass(frozen=True)
class Point:
    date: str          # ISO date, YYYY-MM-DD
    value: float


class SeriesError(ValueError):
    """The series cannot be used as declared. ``code`` names why."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _months(date: str) -> int:
    return int(date[:4]) * 12 + int(date[5:7]) - 1


def check(points: Sequence[Point], frequency: str) -> List[Point]:
    """Dates in order, one per period, no gaps. Returns them sorted."""
    if frequency not in STEP_MONTHS:
        raise SeriesError("frequency", "frequency must be one of %s, not %r"
                          % (sorted(STEP_MONTHS), frequency))
    if not points:
        raise SeriesError("empty", "the series has no observations")
    pts = sorted(points, key=lambda p: p.date)
    step = STEP_MONTHS[frequency]
    for a, b in zip(pts, pts[1:]):
        gap = _months(b.date) - _months(a.date)
        if gap == 0:
            raise SeriesError("duplicate", "two observations for %s" % a.date)
        if gap != step:
            raise SeriesError(
                "gap", "%s is followed by %s: expected one %s step. A missing "
                "period is refused, not filled in." % (a.date, b.date, frequency))
    return pts


def smooth(points: Sequence[Point], periods: int) -> List[Point]:
    """Trailing mean over ``periods`` observations, dated at the last one.

    ``periods=1`` is no smoothing. The first ``periods - 1`` observations have
    no full window and are dropped rather than averaged over fewer.
    """
    if periods < 1:
        raise SeriesError("smoothing", "smoothing must be 1 or more periods")
    out = []
    for i in range(periods - 1, len(points)):
        window = points[i - periods + 1:i + 1]
        out.append(Point(points[i].date, sum(p.value for p in window) / periods))
    return out
