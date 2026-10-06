"""The independent road's Look additions of 30 Sep 2026, shared by by_hand_look.py (the Bureau book) and
by_hand_scout.py (the Scouting book); by_hand_book.py carries the same rules inline. From the tab's own words, no
PocketBook: P10 to P90 are "the 10th, 25th, 50th, 75th and 90th percentile" (Look, The lines), taken as Excel's
PERCENTILE.INC, which is numpy's default "linear"; the labels under the bars read 24k for 24,000 and 1.2M for
1,200,000 with the decimals the step between two labels needs (five labels across, whatever the bars); a grey line
sits where its value falls on the chart (10 slots for the low end, 100 for the bars, 10 for the high), none outside
From..To.
"""
import math
import statistics
from decimal import Decimal, ROUND_HALF_UP

import numpy as np

PCTS = (10, 25, 50, 75, 90)
PCT_LABELS = ("10th percentile (P10)", "25th percentile (P25)", "50th percentile (P50), the median",
              "75th percentile (P75)", "90th percentile (P90)")


def text_fmt(v, fmt):
    """TEXT(v, fmt). A spreadsheet rounds a number to 15 significant digits before it formats it, so a bar's start
    worked out as 3 x 0.175 = 0.5249999999999999 prints 0.53: this road's first try printed 0.52 (found on the
    Scouting book's income_to_sales labels, 30 Sep 2026), its own float error, not PocketBook's."""
    places = {"#,##0": 0, "#,##0.0": 1, "0.00": 2, "0.000": 3}[fmt]
    d = Decimal(f"{float(v):.15g}").quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return f"{d:,}" if fmt.startswith("#,") else str(d)


def general(v):
    s = f"{float(v):.10g}"
    return s[:-2] if s.endswith(".0") else s


def short_label(x, step, fmt):
    def unit(size, suffix):
        places = max(0, 1 - math.floor(math.log10(step / size)))
        d = Decimal(f"{float(x) / size:.15g}").quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        return general(float(d)) + suffix
    if abs(x) >= 1_000_000:
        return unit(1_000_000, "M")
    if abs(x) >= 1000:
        return unit(1000, "k")
    return text_fmt(x, fmt)


def look_format(vals):
    v = sorted(vals)
    if all(float(x).is_integer() for x in v):
        return "#,##0"
    big = max(abs(v[0]), abs(v[-1]), abs(statistics.median(v)))
    return "#,##0" if big >= 100 else "#,##0.0" if big >= 10 else "0.00" if big >= 1 else "0.000"


def percentiles(put, name, real):
    arr = np.array(real, dtype=float)
    for p_, lab in zip(PCTS, PCT_LABELS):
        put(["look", name, lab, 3], float(np.percentile(arr, p_)),
            "PERCENTILE.INC, numpy's linear, answered-missing values left out",
            plant=float(np.percentile(arr, p_, method="weibull")))      # a plant for mutate.py: PERCENTILE.EXC


def lines(put, name, real, lo, hi, bars, starts=None):
    """`starts`: the bars' starts as read (keys only: a start read back as 0.6000000000000001 names the same bar);
    each label is made from this road's own start, lo + i (hi - lo) / bars."""
    w, step, fmt = (hi - lo) / bars, (hi - lo) / 5, look_format(real)
    for i in range(bars):
        a = lo + i * w
        key = starts[i] if starts else float(a)
        put(["look-label", name, key], short_label(a, step, fmt), f"the bar's start, step {step:g}, {fmt}",
            plant=f"{a / 1000:.1f}k" if abs(a) >= 1000 else f"{a:.1f}")
    arr = np.array(real, dtype=float)
    for k, p_ in enumerate(PCTS):
        pv = float(np.percentile(arr, p_))
        put(["look-pline", name, k], 10 + 0.5 + 100 * (pv - lo) / (hi - lo) if lo <= pv <= hi else None,
            f"P{p_} = {pv:g} placed on the chart",
            plant=100 * (pv - lo) / (hi - lo) if lo <= pv <= hi else 50.0)   # a plant: no low-end slots


def from_figs(put, figs, values):
    """The bars the tab draws (From, To, how many), as read: the analyst's view, never a value."""
    got = {}
    for f in figs:
        k = f["key"]
        if k[0] == "look-bar" and k[1] in values:
            got.setdefault(k[1], {})[k[2]] = (k[3], k[4])
    for name, bars_ in got.items():
        starts = sorted(bars_)
        lo = round(starts[0], 9)
        hi = round(starts[-1] + bars_[starts[-1]][0], 9)
        lines(put, name, values[name], lo, hi, len(starts), starts)
