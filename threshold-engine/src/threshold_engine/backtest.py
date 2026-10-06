"""How predictive would a set of thresholds have been, and what does recency do?

For any series, at every period from ``min_history`` onward, the thresholds are
rebuilt from only the history available at that moment -- nothing from the
future -- and the period is scored on them. The score is then set against what
happened ``horizon`` periods later. This is repeated with no weighting and at
each stated half-life, so the effect of recency is measured, not assumed.

The scale: score n+1 begins at the n-th stated percentile of the history so far,
in the measure's own orientation (for a loss rate, the 75th percentile is the
level only a quarter of history was worse than).

Three measures, each defined so it can be redone by hand:

- **Score vs level ahead**: Spearman rank correlation between today's score and
  the value ``horizon`` periods later. Does a higher score mean worse ahead?
- **Score vs change ahead**: Spearman between today's score and the change over
  the next ``horizon`` periods. Does a higher score mean it is about to get
  worse (positive), or that it tends to ease back (negative)?
- **By score**: for each score, how many periods took it, the average change
  that followed, and the average level that followed.

What these are not: significance tests. Consecutive periods share most of their
``horizon`` window, so the observations overlap and are not independent; a
correlation here describes the history, it does not prove a rule.

Weighted percentiles take the midpoint of the lower and upper weighted
quantile (the first value at which cumulative weight reaches p of the total,
and the first at which it passes it). The same rule is used at every weighting,
including none, so the comparison is like for like.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

from .engine import score
from .evidence import recency_weights
from .series import Point, check, smooth


def weighted_percentile(values, weights, p):
    if len(values) != len(weights):
        # zip would silently drop the extra values; here that would be the
        # future leaking in or out of the history, so it is refused.
        raise ValueError("%d values but %d weights" % (len(values), len(weights)))
    pairs = sorted(zip(values, weights))
    target, cum, lower, upper = p / 100 * sum(weights), 0.0, None, None
    for v, w in pairs:
        cum += w
        if lower is None and cum >= target:
            lower = v
        if cum > target:
            upper = v
            break
    return (lower + (lower if upper is None else upper)) / 2


def _ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r, i = [0.0] * len(x), 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1          # ties share the average rank
        i = j + 1
    return r


def spearman(a, b) -> Optional[float]:
    """Pearson correlation of the ranks; None when either side is constant."""
    ra, rb = _ranks(a), _ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else None


def backtest(points: Sequence[Point], name: str, unit: str, direction: str,
             frequency: str, smoothing: int, percentiles: Sequence[float],
             horizon: int, min_history: int, floor_at_zero: bool,
             half_lives: Sequence[float] = ()) -> dict:
    if direction not in ("higher_is_worse", "lower_is_worse"):
        raise ValueError("direction must be higher_is_worse or lower_is_worse")
    if list(percentiles) != sorted(set(percentiles)) or not all(0 < p < 100 for p in percentiles):
        raise ValueError("percentiles must rise strictly and lie between 0 and 100")
    if horizon < 1 or min_history < 2:
        raise ValueError("horizon must be 1 or more and min_history 2 or more")
    series = smooth(check(points, frequency), smoothing)
    if len(series) < min_history + horizon:
        raise ValueError("%d observations after smoothing; at least min_history + "
                         "horizon = %d are needed" % (len(series), min_history + horizon))
    sign = 1.0 if direction == "higher_is_worse" else -1.0
    vals = [p.value for p in series]
    dates = [p.date for p in series]

    runs = []
    for hl in [None] + list(half_lives):
        scores, ahead, change, tested = [], [], [], []
        for i in range(min_history - 1, len(series) - horizon):
            hist = [sign * v for v in vals[:i + 1]]
            w = [1.0] * (i + 1) if hl is None else recency_weights(dates[:i + 1], hl)
            bounds = [sign * weighted_percentile(hist, w, p) for p in percentiles]
            scores.append(score(vals[i], bounds, direction, floor_at_zero))
            tested.append({"date": dates[i], "value": vals[i], "bounds": bounds,
                           "score": scores[-1]})
            ahead.append(sign * vals[i + horizon])
            change.append(sign * (vals[i + horizon] - vals[i]))
        by_score = []
        for k in range(1, len(percentiles) + 2):
            idx = [j for j, s in enumerate(scores) if s == k]
            by_score.append({
                "score": k, "periods": len(idx),
                "mean_change_ahead": (sign * sum(change[j] for j in idx) / len(idx)
                                      if idx else None),
                "mean_level_ahead": (sign * sum(ahead[j] for j in idx) / len(idx)
                                     if idx else None)})
        runs.append({"half_life_years": hl, "periods_tested": len(scores),
                     "first_tested": dates[min_history - 1],
                     "last_tested": dates[len(series) - horizon - 1],
                     "score_vs_level_ahead": spearman(scores, ahead),
                     "score_vs_change_ahead": spearman(scores, change),
                     "by_score": by_score, "periods": tested})
    return {"measure": {"name": name, "unit": unit, "direction": direction,
                        "frequency": frequency, "smoothing": smoothing},
            "settings": {"percentiles": list(percentiles), "horizon": horizon,
                         "min_history": min_history, "floor_at_zero": floor_at_zero,
                         "half_lives": list(half_lives)},
            "runs": runs}


def report(bt: dict) -> str:
    s, m = bt["settings"], bt["measure"]
    u = m["unit"]
    f = lambda x: "-" if x is None else "%+.2f" % x                  # noqa: E731
    out = [m["name"],
           "Scale: score 2-%d begin at percentiles %s of the history available at"
           " the time." % (len(s["percentiles"]) + 1, "/".join("%g" % p for p in s["percentiles"])),
           "Horizon %d periods; first test after %d periods of history; %d tested."
           % (s["horizon"], s["min_history"], bt["runs"][0]["periods_tested"]), "",
           "                  Spearman: score vs     Mean change ahead by score (periods)",
           "weighting         level    change"]
    for r in bt["runs"]:
        out.append("%-16s  %6s   %6s    %s" % (
            "none" if r["half_life_years"] is None else "%g-yr half-life" % r["half_life_years"],
            f(r["score_vs_level_ahead"]), f(r["score_vs_change_ahead"]),
            "  ".join("%d: %s%s (%d)" % (b["score"], f(b["mean_change_ahead"]),
                                          u if b["mean_change_ahead"] is not None else "",
                                          b["periods"]) for b in r["by_score"])))
    out += ["",
            "Level: does a higher score mean worse %d periods later? (1 = perfectly)" % s["horizon"],
            "Change: positive = a higher score came before deterioration; negative = before easing.",
            "Periods overlap, so these describe the history; they are not significance tests."]
    return "\n".join(out)
