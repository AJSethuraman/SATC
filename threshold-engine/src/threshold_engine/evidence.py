"""Evidence for each judgement point, and the cutoffs each answer produces.

The profile reports what a series did. This module puts numbers on the three
judgements the bank has to make, then shows the cutoffs under each answer, so
the choice is made looking at its consequences:

1. Which spells were stress? Each spell's peak is measured against the rest of
   history with a robust z-score: (peak - median) / (1.4826 x median absolute
   deviation), both taken over every period outside the spell. The median
   absolute deviation is used rather than the standard deviation so that one
   crisis cannot widen the yardstick it is measured with. 3.5 is the usual
   line for "unusual" (Iglewicz and Hoaglin, *How to Detect and Handle
   Outliers*, ASQC, 1993); the count is also given at 2.5 and 3.0.

2. Is the largest spell a different kind of event? Its robust z-score is set
   beside the next most unusual spell's, with the ratio of their peaks and how
   often history reached each level (a return period: years of history per
   spell that reached it). With one or two comparison spells, no test can
   separate "a different kind of event" from "a worse one of the same kind";
   the report says so rather than imply otherwise.

3. Was a long spell one cycle or two? The deepest dip inside each spell, between
   two higher points, is measured in standard deviations of the series'
   quarter-to-quarter change.

What these numbers are not: probabilities. A trailing-twelve-month rate moves
slowly, so neighbouring quarters are not independent draws, and a z-score here
says how far a level sits from the bulk of history, not how likely it was.

The scenarios, all on the same scale (normal level = median of the periods
kept; the top score begins ``top_fraction`` of the way to the worst period
kept, in equal steps):

A. Keep everything.
B. Remove the largest spell, whatever is left.
C. Remove the largest spell only if another spell is unusual at the line;
   otherwise keep it.

Recency. Scenario C is then repeated at each stated half-life: a period's
weight halves for every ``half_life`` years of its age, counted back from the
latest observation. Only the normal level is weighted, as a weighted median.
The worst period kept stays the anchor at full weight, so the scale does not
forget what stress looked like. Effective quarters, (sum w)^2 / sum w^2, say
how much history a half-life really uses. A half-life that puts the normal
level at or below zero on a floored measure is refused, not scaled: every
positive loss would score 2 or worse.
"""
from __future__ import annotations

import math
import statistics
from typing import Sequence

from .engine import score
from .profile import profile
from .series import STEP_MONTHS, Point, check, smooth

ROBUST_SCALE = 1.4826       # makes the MAD comparable to a standard deviation
LINES = (2.5, 3.0, 3.5)
LINE = 3.5


def robust_z(x: float, values: Sequence[float]) -> float:
    m = statistics.median(values)
    s = ROBUST_SCALE * statistics.median([abs(v - m) for v in values])
    if s == 0:                  # no spread: only a value off the median stands out
        return 0.0 if x == m else math.copysign(math.inf, x - m)
    return (x - m) / s


def _inside(spell, date):
    return spell["start"] <= date and (spell["end"] is None or date < spell["end"])


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
    """0.5 ** (age in years / half-life), age counted back from the last date."""
    def months(d):
        return int(d[:4]) * 12 + int(d[5:7])
    last = months(dates[-1])
    return [0.5 ** ((last - months(d)) / 12 / half_life_years) for d in dates]


def _bounds(values, k, top_fraction, weights=None):
    normal = (statistics.median(values) if weights is None
              else weighted_median(values, weights))
    anchor = max(values)
    step = top_fraction * (anchor - normal) / (k - 2) if k > 2 else 0.0
    return normal, anchor, [normal + i * step for i in range(k - 1)]


def evidence(points: Sequence[Point], name: str, unit: str, direction: str,
             frequency: str, smoothing: int, scale_points: int,
             top_fraction: float, floor_at_zero: bool,
             half_lives: Sequence[float] = ()) -> dict:
    pr = profile(points, name, unit, direction, frequency, smoothing)
    sign = 1.0 if direction == "higher_is_worse" else -1.0
    series = smooth(check(points, frequency), smoothing)
    work = [Point(p.date, sign * p.value) for p in series]
    years = len(work) / (12 // STEP_MONTHS[frequency])

    spells = []
    for s in pr["spells_worse_than_median"]:
        outside = [p.value for p in work if not _inside(s, p.date)]
        inside = [p for p in work if _inside(s, p.date)]
        z = robust_z(sign * s["peak"], outside)
        reached = sum(1 for t in pr["spells_worse_than_median"]
                      if sign * t["peak"] >= sign * s["peak"])
        spells.append(dict(s, robust_z=z, return_period_years=years / reached,
                           dip=_deepest_dip(inside, work)))
    changes = [b.value - a.value for a, b in zip(work, work[1:])]
    sd_change = statistics.stdev(changes) if len(changes) > 1 else 0.0
    for s in spells:
        if s["dip"]:
            s["dip"]["in_sd_of_change"] = (s["dip"]["depth"] / sd_change
                                           if sd_change else math.inf)

    ranked = sorted(spells, key=lambda s: -sign * s["peak"])
    largest = ranked[0] if ranked else None
    unusual_others = [s for s in ranked[1:] if s["robust_z"] >= LINE]

    def scenario(label, removed):
        kept = [p for p in work if removed is None or not _inside(removed, p.date)]
        normal, anchor, b = _bounds([p.value for p in kept], scale_points, top_fraction)
        bounds = [sign * x for x in b]
        last = series[-1].value
        return {"scenario": label,
                "removed": None if removed is None else (removed["start"], removed["end"]),
                "normal": sign * normal, "worst_kept": sign * anchor, "bounds": bounds,
                "latest_score": score(last, bounds, direction, floor_at_zero)}

    scenarios = [scenario("A. Keep everything", None)]
    if largest:
        scenarios.append(scenario("B. Remove the largest spell", largest))
        c = largest if unusual_others else None
        scenarios.append(dict(scenario(
            "C. Remove it only if another spell is unusual (z >= %g)" % LINE, c),
            decided_by=("%s spell, z %.1f" % (unusual_others[0]["start"],
                                              unusual_others[0]["robust_z"])
                        if unusual_others else "no other spell reaches z %g" % LINE)))

    removed_c = largest if unusual_others else None
    kept_c = [p for p in work if removed_c is None or not _inside(removed_c, p.date)]
    recency = []
    for hl in half_lives:
        w = recency_weights([p.date for p in kept_c], hl)
        normal, anchor, b = _bounds([p.value for p in kept_c], scale_points,
                                    top_fraction, w)
        row = {"half_life_years": hl,
               "effective_quarters": sum(w) ** 2 / sum(x * x for x in w),
               "normal": sign * normal}
        if floor_at_zero and normal <= 0:
            row["refused"] = ("the weighted normal level is %.3f, at or below zero:"
                              " every positive loss would score 2 or worse" % normal)
        else:
            bounds = [sign * x for x in b]
            row.update(bounds=bounds, worst_kept=sign * anchor,
                       latest_score=score(series[-1].value, bounds, direction,
                                          floor_at_zero))
        recency.append(row)

    return {"recency": recency, "profile": pr, "sd_of_change": sd_change, "spells": spells,
            "unusual_count": {str(l): sum(1 for s in spells if s["robust_z"] >= l)
                              for l in LINES},
            "largest": largest,
            "next_unusual": unusual_others[0] if unusual_others else None,
            "scenarios": scenarios,
            "settings": {"scale_points": scale_points, "top_fraction": top_fraction,
                         "floor_at_zero": floor_at_zero, "line": LINE}}


def _deepest_dip(inside, work):
    """The deepest fall inside a spell between two higher points: the lowest
    point after the spell's first high, below the lower of the highest point
    before it and the highest point after it."""
    if len(inside) < 3:
        return None
    best = None
    for i in range(1, len(inside) - 1):
        left = max(p.value for p in inside[:i])
        right = max(p.value for p in inside[i + 1:])
        depth = min(left, right) - inside[i].value
        if depth > 0 and (best is None or depth > best["depth"]):
            best = {"date": inside[i].date, "depth": depth}
    return best


def report(ev: dict) -> str:
    pr, u = ev["profile"], ev["profile"]["measure"]["unit"]
    sign = 1.0 if pr["measure"]["direction"] == "higher_is_worse" else -1.0
    f = lambda x: "%.3f%s" % (x, u)                                # noqa: E731
    out = [pr["measure"]["name"], "",
           "1. WHICH SPELLS WERE STRESS",
           "   Robust z of each spell's peak against every period outside it.",
           "   3.5 is the usual line for unusual (Iglewicz and Hoaglin, 1993).",
           "   start       peak       robust z  history per spell this bad"]
    for s in ev["spells"]:
        out.append("   %s  %-9s  %8.1f  %5.1f years%s" % (
            s["start"], f(s["peak"]), s["robust_z"], s["return_period_years"],
            "  (%s)" % s["note"] if s["note"] else ""))
    out.append("   Spells unusual at 2.5 / 3.0 / 3.5: %s" % " / ".join(
        str(ev["unusual_count"][str(l)]) for l in LINES))

    lg, nx = ev["largest"], ev["next_unusual"]
    out += ["", "2. IS THE LARGEST SPELL A DIFFERENT KIND OF EVENT"]
    if lg is None:
        out.append("   No spell above the median.")
    elif nx is None:
        out.append("   The largest spell (%s, z %.1f) is the only unusual one. There"
                   " is nothing\n   unusual to compare it with: it is the series' only"
                   " evidence of stress." % (lg["start"], lg["robust_z"]))
    else:
        out.append("   Largest %s: peak %s, z %.1f, reached once in %.0f years."
                   % (lg["start"], f(lg["peak"]), lg["robust_z"], lg["return_period_years"]))
        out.append("   Next unusual %s: peak %s, z %.1f, reached or passed every %.0f years."
                   % (nx["start"], f(nx["peak"]), nx["robust_z"], nx["return_period_years"]))
        out.append("   Peak ratio %.2fx. With %d unusual spell(s) to compare against, no test"
                   " can\n   separate a different kind of event from a worse one of the same kind."
                   % (lg["peak"] / nx["peak"] if nx["peak"] else math.inf,
                      ev["unusual_count"]["3.5"] - 1))

    out += ["", "3. ONE CYCLE OR TWO",
            "   Deepest dip inside each spell, in standard deviations of the"
            " quarter-to-quarter change (%s)." % f(ev["sd_of_change"])]
    for s in ev["spells"]:
        d = s["dip"]
        out.append("   %s  %s" % (s["start"], "no dip" if not d else
                   "dip of %s at %s = %.1f sd" % (f(d["depth"]), d["date"], d["in_sd_of_change"])))
    out.append("   This choice changes how many cycles are counted, not the cutoffs below.")

    st = ev["settings"]
    out += ["", "SCENARIOS (scale 1-%d; top score begins %g of the way to the worst kept)"
            % (st["scale_points"], st["top_fraction"])]
    for sc in ev["scenarios"]:
        out.append("   %s" % sc["scenario"] + ("  [%s]" % sc["decided_by"] if "decided_by" in sc else ""))
        out.append("      normal %s, worst kept %s, cutoffs %s, latest scores %d" % (
            f(sc["normal"]), f(sc["worst_kept"]),
            " / ".join("%.3f" % b for b in sc["bounds"]), sc["latest_score"]))
    if ev["recency"]:
        out += ["", "RECENCY (scenario C, normal level weighted by a half-life; worst kept at full weight)",
                "   half-life  effective quarters  normal     cutoffs                          latest"]
        for r in ev["recency"]:
            out.append("   %5g yrs  %18.0f  %-9s  %s" % (
                r["half_life_years"], r["effective_quarters"], f(r["normal"]),
                "REFUSED: " + r["refused"] if "refused" in r else
                "%-31s  %d" % (" / ".join("%.3f" % b for b in r["bounds"]), r["latest_score"])))
    out += ["", "These are statistics and their consequences, not a recommendation.",
            "The z-scores are distances from the bulk of history, not probabilities:",
            "neighbouring quarters of a trailing-twelve-month rate are not independent."]
    return "\n".join(out)
