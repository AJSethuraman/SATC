"""Stage 1: check the series and apply the declared smoothing.

Nothing here guesses. A gap inside the window is refused rather than
interpolated, because a filled-in quarter is a number nobody published.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
from dataclasses import dataclass
from pathlib import Path
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


def read_csv(path) -> List[Point]:
    """The ``date,value`` rows of a series file, lines starting with '#'
    skipped. A value that is not a finite number (``nan``, ``inf``: Python's
    ``float`` reads both) is refused, naming the file and the date: it is not
    an observation, and the calculations would carry it through silently.
    Every front door (the command line, the workbook, the window) reads here."""
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(line for line in fh if not line.startswith("#"))
        if not {"date", "value"} <= set(rows.fieldnames or ()):
            raise ValueError("%s must begin with the header line date,value (it has: %s)"
                             % (Path(path).name, ",".join(rows.fieldnames or ()) or "nothing"))
        out = []
        for n, r in enumerate(rows, start=2):
            if not (r["date"] or "").strip() or not (r["value"] or "").strip():
                raise ValueError("%s, row %d: a row needs both a date and a value (it has: %s)"
                                 % (Path(path).name, n, ",".join(x for x in (r["date"], r["value"]) if x) or "nothing"))
            try:
                v = float(r["value"])
            except ValueError:
                raise ValueError("%s, %s: the value %r is not a number" % (Path(path).name, r["date"], r["value"])) from None
            if not math.isfinite(v):
                raise ValueError("%s, %s: the value %r is not a number; a series holds only numbers"
                                 % (Path(path).name, r["date"], r["value"]))
            out.append(Point(r["date"], v))
        return out


#: What a product label may not hold. The workbook lists the products in a
#: dropdown written as one quoted, comma-separated list, so a comma splits a
#: label in two and a double quote breaks the list (Excel will not open the
#: file); a label beginning with '=' is written as a formula, not as text.
#: And Excel's MATCH ignores capitals, so labels that differ only in capitals
#: are one label. The window and ``workbook.build`` both apply these.
LABEL_RULE = "a label may not begin with '=' or hold a comma or a double quote"


def label_ok(label: str) -> bool:
    return not label.startswith("=") and "," not in label and '"' not in label


def _months(date: str) -> int:
    return int(date[:4]) * 12 + int(date[5:7]) - 1


def check(points: Sequence[Point], frequency: str) -> List[Point]:
    """Dates in order, one per period, no gaps. Returns them sorted."""
    if frequency not in STEP_MONTHS:
        raise SeriesError("frequency", "frequency must be one of %s, not %r"
                          % (sorted(STEP_MONTHS), frequency))
    if not points:
        raise SeriesError("empty", "the series has no observations")
    for p in points:
        # A real calendar date, written YYYY-MM-DD: 2020-13-31 or 2020-03-99
        # would otherwise pass the step test and become a quarter like 2020Q5.
        try:
            ok = len(p.date) == 10 and dt.date.fromisoformat(p.date).isoformat() == p.date
        except (TypeError, ValueError):
            ok = False
        if not ok:
            raise SeriesError("date", "%r is not a calendar date written YYYY-MM-DD" % (p.date,))
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
    if periods > len(points):
        raise SeriesError("smoothing", "smoothing over %d periods needs at least %d observations; the "
                          "series has %d" % (periods, periods, len(points)))
    out = []
    for i in range(periods - 1, len(points)):
        window = points[i - periods + 1:i + 1]
        out.append(Point(points[i].date, sum(p.value for p in window) / periods))
    return out
