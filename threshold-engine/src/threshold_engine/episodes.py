"""Stage 3: find the stress episodes in a series.

An episode is an unbroken stretch above the normal level whose peak rises at
least ``min_height`` above normal. A second peak inside the same stretch is the
same episode: 2008's mortgage losses peaked in 2010 and bumped again in 2012
without ever returning to normal, and counting that as two cycles would let the
crisis be compared against itself.

The rule is chosen so a reviewer can redo it with a ruler: draw the normal
level, find each stretch above it, measure each stretch's highest point.

An episode still above normal at the end of the data is *open*. One already
above normal at the first observation has an *unseen start*: its real peak may
lie before the data begins. Both are reported; neither counts as complete.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .series import Point


@dataclass(frozen=True)
class Episode:
    start: str              # first observation above normal
    peak_date: str
    peak: float
    end: Optional[str]      # first observation back at or below normal; None if open
    height: float           # peak less the normal level
    unseen_start: bool

    @property
    def complete(self) -> bool:
        return self.end is not None and not self.unseen_start


def _runs(v: Sequence[float], normal: float):
    """(first, last) index of each unbroken stretch strictly above normal."""
    runs, i, n = [], 0, len(v)
    while i < n:
        if v[i] > normal:
            j = i
            while j + 1 < n and v[j + 1] > normal:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs


def find(points: Sequence[Point], normal: float, min_height: float,
         materiality: Optional[float]) -> List[Episode]:
    """Every stretch above normal whose peak clears normal by ``min_height``
    and, when a materiality level is given, reaches it."""
    v = [p.value for p in points]
    out = []
    for a, b in _runs(v, normal):
        k = max(range(a, b + 1), key=lambda i: v[i])   # first of equal highs
        height = v[k] - normal
        if height < min_height:
            continue
        if materiality is not None and v[k] < materiality:
            continue
        out.append(Episode(
            start=points[a].date, peak_date=points[k].date, peak=v[k],
            end=points[b + 1].date if b + 1 < len(v) else None,
            height=height, unseen_start=(a == 0)))
    return out


def sweep(points: Sequence[Point], normal: float, fractions: Sequence[float],
          materiality: Optional[float]):
    """How many complete episodes at each height setting, as a fraction of
    normal.

    A count that holds across a wide band of settings is evidence; one that
    changes with every setting is reported as unstable, not chosen.
    """
    return [(f, sum(1 for e in find(points, normal, f * abs(normal), materiality)
                    if e.complete))
            for f in fractions]
