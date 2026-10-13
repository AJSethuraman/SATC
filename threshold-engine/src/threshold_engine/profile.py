"""Facts about a series, for an expert to judge. No judgement settings.

``cutoffs`` (engine.run) decides what counts as stress from settings the bank
states. This module decides nothing. It reports what the series did, each
figure defined against one stated reference, so a reviewer can redo it by hand
and draw their own conclusion:

- coverage: first, last, how many observations, the smoothing applied
- distribution: percentiles, mean, standard deviation, and the dates of the
  lowest and highest values
- spells above the median: every unbroken stretch worse than the median, with
  start, peak, end, length, rise and fall times, and peak relative to median
- exceedance: for each upper percentile of the history, how often it was
  reached, in how many separate spells, the longest, and which years
- without the largest spell: the same percentiles with the largest spell's
  periods removed, so the weight one episode carries is a number, not a claim
- latest: where the latest value ranks in history, its change over the last
  year, and when history was last this bad before the current spell

Percentiles interpolate linearly between ranked observations, the method of
Excel's PERCENTILE.INC. "Worse" follows the measure's direction: higher for a
loss rate, lower for a credit score.
"""
from __future__ import annotations

import math
from typing import List, Sequence

from .series import STEP_MONTHS, Point, check, smooth

PERCENTILES = (0, 5, 10, 25, 50, 75, 90, 95, 100)
UPPER = (50, 75, 90, 95)


def percentile(values: Sequence[float], p: float) -> float:
    """Linear interpolation between ranked values (Excel PERCENTILE.INC)."""
    v = sorted(values)
    h = (len(v) - 1) * p / 100
    lo = math.floor(h)
    return v[lo] if lo + 1 >= len(v) else v[lo] + (h - lo) * (v[lo + 1] - v[lo])


def _spells(work: Sequence[Point], level: float, inclusive: bool) -> List[tuple]:
    """(first, last) index of each unbroken stretch worse than level, or at or
    worse than it when ``inclusive``."""
    worse = (lambda x: x >= level) if inclusive else (lambda x: x > level)
    out, i = [], 0
    while i < len(work):
        if worse(work[i].value):
            j = i
            while j + 1 < len(work) and worse(work[j + 1].value):
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def profile(points: Sequence[Point], name: str, unit: str, direction: str,
            frequency: str, smoothing: int) -> dict:
    if direction not in ("higher_is_worse", "lower_is_worse"):
        raise ValueError("direction must be higher_is_worse or lower_is_worse")
    checked = check(points, frequency)
    series = smooth(checked, smoothing)
    sign = 1.0 if direction == "higher_is_worse" else -1.0
    work = [Point(p.date, sign * p.value) for p in series]
    vals = [p.value for p in series]
    per_year = 12 // STEP_MONTHS[frequency]
    n = len(series)

    def real(x):                       # back from "higher is worse" space
        return sign * x

    # Percentiles are stated in the measure's own orientation: p95 is the value
    # only 5% of history was worse than.
    def worse_pct(values, p):
        return real(percentile([sign * x for x in values], p))

    dist = {"p%d" % p: worse_pct(vals, p) for p in PERCENTILES}
    mean = sum(vals) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in vals) / (n - 1)) if n > 1 else 0.0
    best = min(work, key=lambda p: p.value)
    worst = max(work, key=lambda p: p.value)

    median_w = sign * dist["p50"]
    spells = []
    for a, b in _spells(work, median_w, inclusive=False):
        k = max(range(a, b + 1), key=lambda i: work[i].value)
        end = work[b + 1].date if b + 1 < n else None
        spells.append({
            "start": work[a].date, "peak_date": work[k].date,
            "peak": real(work[k].value), "end": end,
            "periods": b - a + 1,
            "periods_to_peak": k - a + 1,
            "periods_peak_to_end": (b + 1 - k) if end else None,
            "peak_minus_median": abs(work[k].value - median_w),
            "peak_over_median": (real(work[k].value) / dist["p50"]
                                 if dist["p50"] else None),
            "complete": end is not None and a > 0,
            "note": ("under way at the first observation" if a == 0 else
                     "still under way at the last observation" if end is None
                     else ""),
        })
    by_peak = sorted(range(len(spells)), key=lambda i: -sign * spells[i]["peak"])
    for rank, i in enumerate(by_peak, 1):
        spells[i]["rank"] = rank

    exceed = []
    for p in UPPER:
        lvl_w = sign * dist["p%d" % p]
        runs = _spells(work, lvl_w, inclusive=True)
        hit = sum(1 for x in work if x.value >= lvl_w)
        longest = max(runs, key=lambda r: r[1] - r[0], default=None)
        exceed.append({
            "level": "p%d" % p, "value": dist["p%d" % p],
            "share_at_or_worse": hit / n, "spells_worse": len(runs),
            "longest": (None if longest is None else
                        (work[longest[0]].date, work[longest[1]].date,
                         longest[1] - longest[0] + 1)),
            "years": sorted({x.date[:4] for x in work if x.value >= lvl_w}),
        })

    without = None
    if spells:
        big = spells[by_peak[0]]
        kept = [p.value for p in series
                if not (big["start"] <= p.date <= (big["end"] or "9999")
                        and p.date != big["end"])]
        if kept:
            without = {"removed": (big["start"], big["end"], big["periods"]),
                       "observations": len(kept),
                       **{"p%d" % p: worse_pct(kept, p) for p in PERCENTILES}}

    last = series[-1]
    last_w = sign * last.value
    rank = sum(1 for x in work if x.value <= last_w) / n
    year_ago = series[-1 - per_year].value if n > per_year else None
    # Step back over the unbroken run at or worse than the latest value, then
    # find the last time before that run that history was this bad.
    i = n - 1
    while i - 1 >= 0 and work[i - 1].value >= last_w:
        i -= 1
    prior = [p for p in work[:i] if p.value >= last_w]
    latest = {"date": last.date, "value": last.value,
              "share_of_history_no_worse": rank,
              "change_over_year": None if year_ago is None else last.value - year_ago,
              "run_at_or_worse_since": work[i].date,
              "last_this_bad_before": prior[-1].date if prior else None}

    return {"measure": {"name": name, "unit": unit, "direction": direction,
                        "frequency": frequency, "smoothing": smoothing},
            "coverage": {"first": checked[0].date, "last": checked[-1].date,
                         "observations": len(checked), "after_smoothing": n},
            "distribution": dict(dist, mean=mean, sd=sd,
                                 best=(best.date, real(best.value)),
                                 worst=(worst.date, real(worst.value))),
            "spells_worse_than_median": spells,
            "exceedance": exceed,
            "without_largest_spell": without,
            "latest": latest}


def report(pr: dict) -> str:
    u = pr["measure"]["unit"]
    f = lambda x: "%.3f%s" % (x, u)                       # noqa: E731
    d, c = pr["distribution"], pr["coverage"]
    worse = "higher" if pr["measure"]["direction"] == "higher_is_worse" else "lower"
    out = ["%s" % pr["measure"]["name"],
           "%s to %s, %d observations, smoothing %d (worse = %s)" % (
               c["first"], c["last"], c["observations"],
               pr["measure"]["smoothing"], worse), "",
           "DISTRIBUTION (percentiles: share of history no worse than the value)",
           "  " + "  ".join("%s %s" % (k, f(d[k])) for k in
                            ("p0", "p10", "p25", "p50", "p75", "p90", "p95", "p100")),
           "  mean %s, standard deviation %s" % (f(d["mean"]), f(d["sd"])),
           "  best %s on %s; worst %s on %s" % (f(d["best"][1]), d["best"][0],
                                                f(d["worst"][1]), d["worst"][0]),
           "", "SPELLS WORSE THAN THE MEDIAN (%s), in date order" % f(d["p50"]),
           "  rank  start       peak date   peak       x median  end         "
           "periods  to peak  peak to end"]
    for s in pr["spells_worse_than_median"]:
        out.append("  %4d  %s  %s  %-9s  %8s  %-10s  %7d  %7d  %11s  %s" % (
            s["rank"], s["start"], s["peak_date"], f(s["peak"]),
            "%.2f" % s["peak_over_median"] if s["peak_over_median"] else "-",
            s["end"] or "-", s["periods"], s["periods_to_peak"],
            s["periods_peak_to_end"] if s["periods_peak_to_end"] is not None else "-",
            s["note"]))
    out += ["", "HOW OFTEN EACH LEVEL WAS REACHED",
            "  level  value      share  spells  longest"]
    for e in pr["exceedance"]:
        lg = e["longest"]
        out.append("  %-5s  %-9s  %4.0f%%  %6d  %s" % (
            e["level"], f(e["value"]), 100 * e["share_at_or_worse"],
            e["spells_worse"], "%s to %s (%d)" % lg if lg else "-"))
        out.append("         years: %s" % _years(e["years"]))
    w = pr["without_largest_spell"]
    if w:
        out += ["", "PERCENTILES WITHOUT THE LARGEST SPELL (%s to %s, %d periods removed)"
                % (w["removed"][0], w["removed"][1] or "now", w["removed"][2]),
                "  " + "  ".join("%s %s -> %s" % (k, f(d[k]), f(w[k]))
                                 for k in ("p50", "p75", "p90", "p95", "p100"))]
    la = pr["latest"]
    out += ["", "LATEST %s: %s" % (la["date"], f(la["value"])),
            "  no worse than %.0f%% of history" % (100 * la["share_of_history_no_worse"]),
            "  change over the last year: %s" % (
                "-" if la["change_over_year"] is None else "%+.3f%s" % (la["change_over_year"], u)),
            "  at or worse than this since %s; before that, last this bad on %s" % (
                la["run_at_or_worse_since"], la["last_this_bad_before"] or "never")]
    return "\n".join(out)


def _years(ys):
    """'1991-1993, 2002, 2008-2011': runs of consecutive years."""
    if not ys:
        return "-"
    nums, runs = [int(y) for y in ys], []
    a = b = nums[0]
    for y in nums[1:]:
        if y == b + 1:
            b = y
        else:
            runs.append((a, b))
            a = b = y
    runs.append((a, b))
    return ", ".join(str(a) if a == b else "%d-%d" % (a, b) for a, b in runs)
