"""Stage 1: check the series and apply the declared smoothing.

Nothing here guesses. A gap inside the window is refused rather than
interpolated, because a filled-in quarter is a number nobody published.

One gap is not refused: quarters the file itself declares left out, on a
``# left-out:`` note line (``read_left_out``). The peers build writes one where
the jump left windows out only for a move in a quarter a reporting change or an
event names for the series (the firm, 17 Oct 2026, the commercial proposal's
question 16): the series continues across them, and they are never filled.
``check`` given those quarters returns the whole calendar, each declared
quarter as a ``Point`` whose value is None, so every reader measures a year as
four quarters of the calendar, never four observations, and leaves the
declared quarters out of everything it counts. A gap anywhere else, or a
declared quarter that holds a value, is still refused.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

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


#: The description every file is expected to give of itself: the keys the
#: internal templates ask for, which the Sources tab prints and marks "not
#: stated" when missing. Public files carry the same lines.
CORE_NOTES = ("measure", "as-of", "basis", "source")      # every series has these; a score has no numerator


def read_notes(path) -> List[Tuple[str, str]]:
    """A file's description of itself: every line before the data that starts
    with '#', as (key, text). '# measure: ...' gives ("measure", "..."); a
    line with no key gives ("note", text). Nothing is inferred."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("#"):
                continue
            text = line[1:].strip()
            m = re.match(r"([a-z][a-z0-9-]*):\s*(.*)$", text)
            out.append((m.group(1), m.group(2)) if m else ("note", text))
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


#: The key of the note line declaring the quarters a series leaves out and
#: continues across (``# left-out: 2024Q4 to 2025Q4. Why ...``).
LEFT_OUT_KEY = "left-out"
_RUNS = re.compile(r"(\d{4}Q[1-4](?: to \d{4}Q[1-4])?(?:, \d{4}Q[1-4](?: to \d{4}Q[1-4])?)*)\. ")


def _quarter_n(label: str) -> int:
    return int(label[:4]) * 4 + int(label[5]) - 1


def _quarter_date(n: int) -> str:
    return "%d-%s" % (n // 4, ("03-31", "06-30", "09-30", "12-31")[n % 4])


def left_out_line(labels: Sequence[str], why: str) -> str:
    """The ``left-out:`` note line for quarters (``YYYYQn``, in order) a series
    continues across: the runs, then ``why``."""
    runs: List[List[str]] = []
    for q in labels:
        if runs and _quarter_n(q) == _quarter_n(runs[-1][1]) + 1:
            runs[-1][1] = q
        else:
            runs.append([q, q])
    return "%s: %s. %s" % (LEFT_OUT_KEY, ", ".join(a if a == b else "%s to %s" % (a, b) for a, b in runs), why)


def left_out_dates(notes: Sequence[Tuple[str, str]]) -> List[str]:
    """The quarter-end dates (ISO) the ``left-out`` lines among ``notes``
    (``read_notes``' pairs) declare, in order. A ``left-out`` line that does
    not begin with its quarters is refused: it would declare nothing while
    looking as if it did. So is a run written backwards ("2025Q4 to
    2024Q4"), which would declare no quarter at all."""
    out: List[str] = []
    for key, text in notes:
        if key != LEFT_OUT_KEY:
            continue
        m = _RUNS.match(text)
        if not m:
            raise ValueError("a left-out note must begin with its quarters, like '2024Q4 to 2025Q4. ', not %r"
                             % text[:60])
        for run in m.group(1).split(", "):
            a, _, b = run.partition(" to ")
            if b and _quarter_n(b) < _quarter_n(a):
                raise ValueError("a left-out run must go forwards, like '2024Q4 to 2025Q4', not %r: written "
                                 "backwards it declares no quarter" % run)
            out += [_quarter_date(n) for n in range(_quarter_n(a), _quarter_n(b or a) + 1)]
    return sorted(set(out))


def read_left_out(path) -> List[str]:
    """The quarter-end dates a series file declares left out (``left_out_dates``
    over its notes); empty for a file that declares none."""
    return left_out_dates(read_notes(path))


def check(points: Sequence[Point], frequency: str, left_out: Sequence[str] = ()) -> List[Point]:
    """Dates in order, one per period, no gaps. Returns them sorted.

    ``left_out`` is the quarter-end dates the file declares left out
    (``read_left_out``): a gap made only of those is accepted, and the result
    is then the whole calendar, each of them a ``Point`` whose value is None.
    A declared quarter outside the first and last observation, or one that
    holds a value, is refused; so is a declaration on a monthly series."""
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
    declared = sorted(set(left_out))
    if declared and frequency != "quarterly":
        raise SeriesError("left-out", "only a quarterly series can declare quarters left out")
    held = {p.date for p in pts}
    for d in declared:
        if d in held:
            raise SeriesError("left-out", "%s is declared left out but holds a value" % d)
        if not (pts[0].date < d < pts[-1].date):
            raise SeriesError("left-out", "%s is declared left out but is not between the first and last "
                                          "observation (%s to %s)" % (d, pts[0].date, pts[-1].date))
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        gap = _months(b.date) - _months(a.date)
        if gap == 0:
            raise SeriesError("duplicate", "two observations for %s" % a.date)
        if gap != step:
            between = [_quarter_date(n) for n in range(_months(a.date) // 3 + 1, _months(b.date) // 3)]
            if gap % step or not declared or any(d not in declared for d in between):
                raise SeriesError(
                    "gap", "%s is followed by %s: expected one %s step. A missing "
                    "period is refused, not filled in." % (a.date, b.date, frequency))
            out += [Point(d, None) for d in between]
        out.append(b)
    if declared and len(out) != len(pts) + len(declared):
        raise SeriesError("left-out", "a quarter declared left out is not a quarter-end of this series")
    return out


def smooth(points: Sequence[Point], periods: int) -> List[Point]:
    """Trailing mean over ``periods`` observations, dated at the last one.

    ``periods=1`` is no smoothing. The first ``periods - 1`` observations have
    no full window and are dropped rather than averaged over fewer. A window
    holding a quarter left out (a value of None, ``check``) has no mean: None,
    never a mean of fewer. None at either end of the result is dropped, so a
    smoothed series still begins and ends with a value.
    """
    if periods < 1:
        raise SeriesError("smoothing", "smoothing must be 1 or more periods")
    if periods > len(points):
        raise SeriesError("smoothing", "smoothing over %d periods needs at least %d observations; the "
                          "series has %d" % (periods, periods, len(points)))
    out = []
    for i in range(periods - 1, len(points)):
        window = points[i - periods + 1:i + 1]
        out.append(Point(points[i].date, None if any(p.value is None for p in window)
                         else sum(p.value for p in window) / periods))
    while out and out[0].value is None:
        out.pop(0)
    while out and out[-1].value is None:
        out.pop()
    if not out:
        raise SeriesError("smoothing", "no %d periods in a row are left after the quarters left out" % periods)
    return out
