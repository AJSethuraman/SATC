"""The engine: a dated signal in, candidate cutoffs and their evidence out.

    check -> smooth -> normal level -> stress episodes -> outlier test -> cutoffs

Every input that is a judgement belongs to the bank and is a required field of
``Settings`` with no default: the engine cannot be run without stating it, and
it is recorded in the result beside what it produced. What the data decides --
the normal level, the episodes, which one is the outlier, the cutoffs -- is
computed, and the result carries enough to recompute each by hand.

Where the evidence cannot support a scale, ``run`` returns ``Refused`` with a
code and a reason rather than a scale built on nothing.
"""
from __future__ import annotations

import hashlib
import statistics
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Sequence, Tuple, Union

from . import episodes as E
from .episodes import Episode
from .series import Point, SeriesError, check, smooth

VERSION = "0.1.0"
DIRECTIONS = ("higher_is_worse", "lower_is_worse")

#: The episode heights the complete-episode count is reported at, as fractions of
#: the normal level. A reporting grid only: nothing produced depends on it.
SWEEP_GRID = (0.05, 0.1, 0.15, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


@dataclass(frozen=True)
class Measure:
    """What the signal is. Described by whoever supplies it."""
    name: str
    unit: str
    direction: str            # "higher_is_worse" or "lower_is_worse"
    frequency: str            # "quarterly" or "monthly"
    smoothing: int            # trailing periods averaged; 1 = none
    floor_at_zero: bool       # a value at or below zero is always the best score


@dataclass(frozen=True)
class Settings:
    """The bank's choices. No field has a default, deliberately.

    scale_points        points on the rating scale, e.g. 5
    top_fraction        the worst score begins this fraction of the way from
                        the normal level to the worst retained peak
    episode_height      how far above the normal level a stretch must peak to
                        count as a stress episode, as a fraction of normal
    materiality         the level an episode's peak must reach to count, in
                        the measure's own units; None states that there is none
    outlier_ratio       the worst episode is an outlier when its rise above
                        normal is at least this multiple of the next worst's
    min_other_episodes  an outlier is excluded only if at least this many
                        other complete episodes remain to anchor the scale
    window              (first, last) dates to use; None states the whole series
    exclusions          declared (first, last, reason) periods left out of the
                        normal level and the anchor; () states none
    """
    scale_points: int
    top_fraction: float
    episode_height: float
    materiality: Optional[float]
    outlier_ratio: float
    min_other_episodes: int
    window: Optional[Tuple[str, str]]
    exclusions: Tuple[Tuple[str, str, str], ...]


@dataclass(frozen=True)
class Refused:
    """The evidence cannot support a scale. ``code`` is stable; ``reason`` is
    written for the person deciding what to do next."""
    stage: str
    code: str
    reason: str


@dataclass(frozen=True)
class Result:
    measure: Measure
    settings: Settings
    normal: float                     # median of the retained series
    anchor: float                     # worst retained level
    bounds: Tuple[float, ...]         # score i+1 begins at bounds[i]
    episodes: Tuple[Episode, ...]
    outlier: dict
    latest: Point
    latest_score: int
    sweep: Tuple[Tuple[float, int], ...]
    provenance: dict = field(default_factory=dict)


def score(value: float, bounds: Sequence[float], direction: str,
          floor_at_zero: bool) -> int:
    """The score a value takes. A value exactly on a bound takes the worse one."""
    if floor_at_zero and value <= 0:
        return 1
    if direction == "higher_is_worse":
        return 1 + sum(1 for b in bounds if value >= b)
    return 1 + sum(1 for b in bounds if value <= b)


def _check_settings(m: Measure, s: Settings) -> Optional[Refused]:
    problems = []
    if m.direction not in DIRECTIONS:
        problems.append("direction must be one of %s" % (DIRECTIONS,))
    if m.floor_at_zero and m.direction != "higher_is_worse":
        problems.append("floor_at_zero applies only to a higher-is-worse measure")
    if s.scale_points < 2:
        problems.append("scale_points must be 2 or more")
    if not 0 < s.top_fraction <= 1:
        problems.append("top_fraction must be above 0 and at most 1")
    if s.episode_height <= 0:
        problems.append("episode_height must be above 0")
    if s.outlier_ratio <= 1:
        problems.append("outlier_ratio must be above 1")
    if s.min_other_episodes < 1:
        problems.append("min_other_episodes must be 1 or more")
    if problems:
        return Refused("settings", "settings", "; ".join(problems))
    return None


def _fingerprint(points: Sequence[Point]) -> str:
    text = "\n".join("%s,%r" % (p.date, p.value) for p in points)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(measure: Measure, settings: Settings,
        points: Sequence[Point]) -> Union[Result, Refused]:
    bad = _check_settings(measure, settings)
    if bad:
        return bad
    try:
        checked = check(points, measure.frequency)
        smoothed = smooth(checked, measure.smoothing)
    except SeriesError as exc:
        return Refused("check", exc.code, str(exc))
    if settings.window:
        lo, hi = settings.window
        smoothed = [p for p in smoothed if lo <= p.date <= hi]
    if len(smoothed) < 3:
        return Refused("check", "too_short", "fewer than three observations "
                       "remain after smoothing and the window")

    # Work in a space where higher is always worse; mirror back at the end.
    sign = 1.0 if measure.direction == "higher_is_worse" else -1.0
    work = [Point(p.date, sign * p.value) for p in smoothed]
    values = [p.value for p in work]

    normal_full = statistics.median(values)
    if normal_full == 0:
        return Refused("normal", "normal_zero", "the normal level is zero, so an "
                       "episode height stated as a fraction of it is undefined")
    materiality = (None if settings.materiality is None
                   else sign * settings.materiality)
    eps = E.find(work, normal_full, settings.episode_height * abs(normal_full),
                 materiality)
    if not any(e.complete for e in eps):
        return Refused(
            "episodes", "no_episode",
            "no complete stress episode in the data at a height of %s of "
            "normal%s. There is no evidence here of what stress looks like for "
            "this measure: supply a longer history or set its cutoffs another "
            "way." % (settings.episode_height, "" if settings.materiality is None
                      else " and a materiality of %s" % settings.materiality))

    # ---- outlier test ---------------------------------------------------
    # The worst episode is compared with the next worst of any kind: a peak
    # seen is a level reached. Only complete episodes can anchor a scale once
    # the worst is set aside, because an open or unseen-start one may not
    # show its real peak.
    ranked = sorted(eps, key=lambda e: e.peak, reverse=True)
    top = ranked[0]
    anchors = [e for e in ranked[1:] if e.complete]
    outlier = {"episodes": len(eps), "complete": sum(e.complete for e in eps),
               "other_complete": len(anchors), "is_outlier": False,
               "excluded": False, "excess_ratio": None, "run": None}
    excluded_dates = set()
    if len(ranked) >= 2:
        second = ranked[1]
        rise_top, rise_second = top.peak - normal_full, second.peak - normal_full
        if rise_second > 0:
            ratio = rise_top / rise_second
            outlier["excess_ratio"] = ratio
            outlier["is_outlier"] = ratio >= settings.outlier_ratio
            if outlier["is_outlier"] and len(anchors) >= settings.min_other_episodes:
                i = next(k for k, p in enumerate(work) if p.date == top.peak_date)
                a = b = i
                while a - 1 >= 0 and work[a - 1].value > second.peak:
                    a -= 1
                while b + 1 < len(work) and work[b + 1].value > second.peak:
                    b += 1
                excluded_dates = {p.date for p in work[a:b + 1]}
                outlier["excluded"] = True
                outlier["run"] = (work[a].date, work[b].date, b - a + 1)
    for first, last, _reason in settings.exclusions:
        excluded_dates |= {p.date for p in work if first <= p.date <= last}

    retained = [p.value for p in work if p.date not in excluded_dates]
    normal = statistics.median(retained)
    anchor = max(retained)
    if anchor <= normal:
        return Refused("cutoffs", "bounds_not_increasing",
                       "the worst retained level does not exceed the normal "
                       "level, so no scale can rise between them")

    k = settings.scale_points
    span = settings.top_fraction * (anchor - normal)
    work_bounds = [normal + (span * i / (k - 2) if k > 2 else 0.0)
                   for i in range(k - 1)]
    bounds = tuple(sign * b for b in work_bounds)
    if measure.floor_at_zero and min(bounds) <= 0:
        return Refused("cutoffs", "bound_at_or_below_zero",
                       "a bound falls at or below zero, where every value is "
                       "already the best score by rule")

    latest = smoothed[-1]
    return Result(
        measure=measure, settings=settings,
        normal=sign * normal, anchor=sign * anchor, bounds=bounds,
        episodes=tuple(Episode(e.start, e.peak_date, sign * e.peak, e.end,
                               e.height, e.unseen_start) for e in eps),
        outlier=outlier, latest=latest,
        latest_score=score(latest.value, bounds, measure.direction,
                           measure.floor_at_zero),
        sweep=tuple(E.sweep(work, normal_full, SWEEP_GRID, materiality)),
        provenance={"engine": VERSION, "data_sha256": _fingerprint(checked),
                    "observations": len(checked),
                    "first": checked[0].date, "last": checked[-1].date,
                    "measure": asdict(measure), "settings": asdict(settings)})
