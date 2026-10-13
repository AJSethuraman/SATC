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

The scenarios, on the workbook's scale (threshold_engine.scale: Moderate a band
around the median of the periods kept, Moderate-Low below it, High at a robust
z), with the bank's stated settings:

A. Keep everything.
B. Remove the largest spell, whatever is left.
C. Remove the largest spell only if another spell is unusual at the line;
   otherwise keep it.

Recency. Scenario C is then repeated at each stated half-life: a period's
weight halves for every ``half_life`` years of its age, counted back from the
latest observation. Only the median is weighted. The typical yearly move, the
spread of levels and the worst kept stay at full weight. Effective quarters,
(sum w)^2 / sum w^2, say how much history a half-life really uses. The scale's
own refusals apply: a weighted median at or below zero on a floored measure is
refused, not scaled.
"""
from __future__ import annotations

import math
import statistics
from typing import Optional, Sequence

from .scale import scale as scale_lines, score as scale_score
from .scale import recency_weights, weighted_median  # noqa: F401
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


def evidence(points: Sequence[Point], name: str, unit: str, direction: str,
             frequency: str, smoothing: int, scale: Optional[dict],
             floor_at_zero: bool, half_lives: Sequence[float] = ()) -> dict:
    """``scale``: dict(halfwidth, low_step, high_z, on_the_line), the workbook's
    settings, or None for the evidence alone (no scenario or recency lines)."""
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

    def kept_list(removed):
        return [None if removed is not None and _inside(removed, p.date) else p.value for p in series]

    def lines(kept, weights=None):
        r = scale_lines(kept, direction, scale["halfwidth"], scale["low_step"], scale["high_z"],
                        floor_at_zero, weights, periods_per_year=12 // STEP_MONTHS[frequency])
        latest = series[-1].value
        r["latest_score"] = (None if r["bounds"] is None else
                             scale_score(latest, r["bounds"], direction, scale["on_the_line"], floor_at_zero))
        return r

    def scenario(label, removed):
        return dict(lines(kept_list(removed)), scenario=label,
                    removed=None if removed is None else (removed["start"], removed["end"]))

    scenarios, recency = [], []
    if scale is not None:
        scenarios.append(scenario("A. Keep everything", None))
        if largest:
            scenarios.append(scenario("B. Remove the largest spell", largest))
            c = largest if unusual_others else None
            scenarios.append(dict(scenario(
                "C. Remove it only if another spell is unusual (z >= %g)" % LINE, c),
                decided_by=("%s spell, z %.1f" % (unusual_others[0]["start"],
                                                  unusual_others[0]["robust_z"])
                            if unusual_others else "no other spell reaches z %g" % LINE)))
        kept_c = kept_list(largest if unusual_others else None)
        for hl in half_lives:
            w = recency_weights([p.date for p in series], hl)
            kw = [x for v, x in zip(kept_c, w) if v is not None]
            recency.append(dict(lines(kept_c, w), half_life_years=hl,
                                effective_quarters=sum(kw) ** 2 / sum(x * x for x in kw)))

    # Departure windows are 2, 3 and 4 years whatever the frequency.
    per_year = 12 // STEP_MONTHS[frequency]
    deps = departures(work, tuple(L * per_year // 4 for L in BRIDGE_LENGTHS))
    for d in deps:
        d["mean_departure"] *= sign            # back to the measure's own units

    return {"recency": recency, "departures": deps, "profile": pr, "sd_of_change": sd_change, "spells": spells,
            "unusual_count": {str(l): sum(1 for s in spells if s["robust_z"] >= l)
                              for l in LINES},
            "largest": largest,
            "next_unusual": unusual_others[0] if unusual_others else None,
            "scenarios": scenarios,
            "settings": {"scale": scale, "floor_at_zero": floor_at_zero, "line": LINE,
                         "frequency": frequency}}


BRIDGE_LENGTHS = (8, 12, 16)
ROUNDS = 3


def departures(work: Sequence[Point], lengths=BRIDGE_LENGTHS, rounds=ROUNDS):
    """Temporary departures: stretches that leave the series' path and come back.

    For a window of W periods, draw a straight bridge from its first value to
    its last and take the mean of the series minus the bridge over the periods
    in between. Negative is a dip below the path, positive a rise above it.
    Each window is ranked, by robust z, against every window of the same length.

    In sequence: the most extreme window, in either direction and at any of the
    stated lengths, is reported and set aside, together with one window-length
    either side of it, since a bridge anchored there still has an end inside the
    event; then the next is found among the windows that touch nothing set
    aside. One extreme event otherwise
    hides the next: a bridge drawn across the start of a large rise always sits
    above the series, so the shoulders of the largest event read as the deepest
    dips. Rosner's generalised ESD test works one outlier at a time for the
    same reason.

    Values are in "higher is worse" space; a positive departure is worse than
    the path around it. The data cannot say why a stretch departed. That is
    the bank's to record.
    """
    v = [p.value for p in work]
    pool = []
    for w in lengths:
        rows = []
        for st in range(0, len(v) - w):
            en = st + w
            dev = [v[t] - (v[st] + (v[en] - v[st]) * (t - st) / w) for t in range(st + 1, en)]
            rows.append((sum(dev) / len(dev), st, en, w))
        if not rows:
            continue
        means = [r[0] for r in rows]
        for r in rows:
            pool.append((robust_z(r[0], means), r, len(rows)))
    found, aside = [], []
    for _ in range(rounds):
        free = [x for x in pool if all(x[1][2] < a or x[1][1] > b for a, b in aside)]
        if not free:
            break
        z, (mean, st, en, w), n = max(free, key=lambda x: abs(x[0]))
        if not math.isfinite(z):
            break
        same_length = sorted((x for x in free if x[1][3] == w), key=lambda x: x[1][0],
                             reverse=mean > 0)
        found.append({"direction": "above the path" if mean > 0 else "below the path",
                      "first": work[st + 1].date, "last": work[en - 1].date,
                      "bridge_from": work[st].date, "bridge_to": work[en].date,
                      "length": w, "mean_departure": mean, "robust_z": z,
                      "rank": 1, "of": len(same_length)})
        aside.append((st - w, en + w))
    return found


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
    per = "month" if pr["measure"]["frequency"] == "monthly" else "quarter"
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
            " %s-to-%s change (%s)." % (per, per, f(ev["sd_of_change"]))]
    for s in ev["spells"]:
        d = s["dip"]
        out.append("   %s  %s" % (s["start"], "no dip" if not d else
                   "dip of %s at %s = %.1f sd" % (f(d["depth"]), d["date"], d["in_sd_of_change"])))
    out.append("   This choice changes how many cycles are counted, not the cutoffs below.")

    sc_ = ev["settings"]["scale"]
    if sc_:
        out += ["", "SCENARIOS, on the workbook's scale (Moderate half-width %g, Moderate-Low step %g, "
                "High z %g; a value on a line takes the %s score)"
                % (sc_["halfwidth"], sc_["low_step"], sc_["high_z"], sc_["on_the_line"])]

    def row(r):
        if r["bounds"] is None:
            return "REFUSED: " + r["refused"]
        return "median %s, typical yearly move %s, worst kept %s, lines %s, latest scores %d" % (
            f(r["median"]), f(r["typical_yearly_move"]), f(r["worst"]),
            " / ".join("%.3f" % b for b in r["bounds"]), r["latest_score"])
    for sc in ev["scenarios"]:
        out.append("   %s" % sc["scenario"] + ("  [%s]" % sc["decided_by"] if "decided_by" in sc else ""))
        out.append("      " + row(sc))
    if ev["recency"]:
        out += ["", "RECENCY (scenario C, the median weighted by a half-life; everything else at full weight)"]
        for r in ev["recency"]:
            out.append("   %g-yr half-life, %.0f effective %ss: %s" % (
                r["half_life_years"], r["effective_quarters"], per, row(r)))
    if ev["departures"]:
        out += ["", "4. TEMPORARY DEPARTURES (left the path and came back; the largest first, then set aside)",
                "   first     last      direction        mean off the path  robust z  rank"]
        for d in ev["departures"]:
            out.append("   %s  %s  %-15s  %+17.3f  %8.1f  1 of %d (%d-%s windows)" % (
                d["first"], d["last"], d["direction"], d["mean_departure"], d["robust_z"],
                d["of"], d["length"], per))
        out.append("   The data finds the departure; why it happened is the bank's to record.")
    out += ["", "These are statistics and their consequences, not a recommendation.",
            "The z-scores are distances from the bulk of history, not probabilities:",
            "neighbouring %ss of a trailing-twelve-month rate are not independent." % per]
    return "\n".join(out)
