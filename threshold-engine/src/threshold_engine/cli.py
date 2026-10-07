"""Run the engine on a CSV of dated values. Two commands:

    python -m threshold_engine profile SERIES.csv --name ... --unit ...
        --direction ... --frequency ... --smoothing ...

reports facts about the series and decides nothing: its distribution, every
spell worse than the median, how often each upper percentile was reached, the
percentiles without the largest spell, and where the latest value ranks.

    python -m threshold_engine cutoffs SERIES.csv --name ... --unit ... --direction ...
        --frequency ... --smoothing ... --floor-at-zero yes|no
        --scale-points ... --top-fraction ... --episode-height ...
        --materiality ...|none --outlier-ratio ... --min-other-episodes ...
        [--window FIRST LAST] [--exclude FIRST LAST REASON ...] [--json]

Every setting is required, as it is in ``Settings``: the command will not run
on a value nobody stated. ``--materiality none`` and the absence of
``--window`` and ``--exclude`` are statements, recorded as such.

The CSV has a ``date,value`` header; lines starting with ``#`` are notes.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys

from .engine import Measure, Refused, Settings, run
from .backtest import backtest, report as backtest_report
from .evidence import evidence, report as evidence_report
from .profile import profile, report
from .series import Point, SeriesError


def _yes_no(text):
    if text not in ("yes", "no"):
        raise argparse.ArgumentTypeError("say yes or no")
    return text == "yes"


def _materiality(text):
    return None if text == "none" else float(text)


def _measure_args(p):
    p.add_argument("csv")
    req = p.add_argument_group("the measure, all required")
    req.add_argument("--name", required=True)
    req.add_argument("--unit", required=True)
    req.add_argument("--direction", required=True,
                     choices=["higher_is_worse", "lower_is_worse"])
    req.add_argument("--frequency", required=True, choices=["quarterly", "monthly"])
    req.add_argument("--smoothing", required=True, type=int,
                     help="trailing periods averaged; 1 = none")


def _parser():
    top = argparse.ArgumentParser(prog="python -m threshold_engine",
                                  description=__doc__.split("\n\n")[0])
    sub = top.add_subparsers(dest="command", required=True)
    pr = sub.add_parser("profile", help="facts about the series; no judgement settings")
    _measure_args(pr)
    pr.add_argument("--json", action="store_true")
    ev = sub.add_parser("evidence", help="statistics for each judgement point, "
                        "and the cutoffs under each answer")
    _measure_args(ev)
    ev.add_argument("--floor-at-zero", required=True, type=_yes_no)
    ev.add_argument("--scale-points", required=True, type=int)
    ev.add_argument("--top-fraction", required=True, type=float)
    ev.add_argument("--half-lives", type=float, nargs="+", default=[],
                    metavar="YEARS", help="repeat scenario C with the normal level "
                    "weighted toward recent years at each half-life")
    ev.add_argument("--json", action="store_true")
    bt = sub.add_parser("backtest", help="how predictive a percentile scale would "
                        "have been, with and without recency weighting")
    _measure_args(bt)
    bt.add_argument("--floor-at-zero", required=True, type=_yes_no)
    bt.add_argument("--percentiles", required=True, type=float, nargs="+",
                    metavar="P", help="where scores 2, 3, ... begin, e.g. 50 75 90 95")
    bt.add_argument("--horizon", required=True, type=int,
                    help="periods ahead the score is judged against")
    bt.add_argument("--min-history", required=True, type=int,
                    help="periods of history before the first test")
    bt.add_argument("--half-lives", type=float, nargs="+", default=[], metavar="YEARS")
    bt.add_argument("--json", action="store_true")
    wbp = sub.add_parser("workbook", help="one run, one Excel workbook: facts, evidence, "
                         "backtest and live cutoffs for every product")
    wbp.add_argument("out", help="the .xlsx to write")
    wbp.add_argument("--series", required=True, action="append", metavar="LABEL=FILE",
                     help="one per product, e.g. \"Credit card=cards.csv\"")
    m = wbp.add_argument_group("the measure, shared by every product, all required")
    m.add_argument("--name", required=True)
    m.add_argument("--unit", required=True)
    m.add_argument("--direction", required=True, choices=["higher_is_worse", "lower_is_worse"])
    m.add_argument("--frequency", required=True, choices=["quarterly"])
    m.add_argument("--smoothing", required=True, type=int)
    m.add_argument("--floor-at-zero", required=True, type=_yes_no)
    j = wbp.add_argument_group("starting values for the Settings tab, all required")
    j.add_argument("--moderate-halfwidth", required=True, type=float,
                   help="Moderate's half-width around the median, in typical yearly moves")
    j.add_argument("--low-step", required=True, type=float,
                   help="Moderate-Low begins this many typical yearly moves below the median")
    j.add_argument("--high-z", required=True, type=float,
                   help="High begins at the median plus this many robust spreads of the quarters kept")
    j.add_argument("--on-the-line", required=True, choices=["worse", "better"])
    b = wbp.add_argument_group("the backtest, all required")
    b.add_argument("--percentiles", required=True, type=float, nargs="+", metavar="P")
    b.add_argument("--horizon", required=True, type=int)
    b.add_argument("--min-history", required=True, type=int)
    wbp.add_argument("--half-lives", type=float, nargs="+", default=[], metavar="YEARS")
    p = sub.add_parser("cutoffs", help="candidate cutoffs from the bank's stated settings")
    _measure_args(p)
    p.add_argument("--floor-at-zero", required=True, type=_yes_no)
    s = p.add_argument_group("the bank's settings, all required")
    s.add_argument("--scale-points", required=True, type=int)
    s.add_argument("--top-fraction", required=True, type=float)
    s.add_argument("--episode-height", required=True, type=float)
    s.add_argument("--materiality", required=True, type=_materiality,
                   help="a level in the measure's units, or 'none'")
    s.add_argument("--outlier-ratio", required=True, type=float)
    s.add_argument("--min-other-episodes", required=True, type=int)
    p.add_argument("--window", nargs=2, metavar=("FIRST", "LAST"))
    p.add_argument("--exclude", nargs=3, action="append", default=[],
                   metavar=("FIRST", "LAST", "REASON"))
    p.add_argument("--json", action="store_true", help="print the full result as JSON")
    return top


def _read(path):
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(line for line in fh if not line.startswith("#"))
        return [Point(r["date"], float(r["value"])) for r in rows]


def _report(r):
    m, u = r.measure, r.measure.unit
    out = ["%s, %s to %s, %d observations" % (
        m.name, r.provenance["first"], r.provenance["last"], r.provenance["observations"]),
        "data sha256 %s" % r.provenance["data_sha256"], "",
        "Stress episodes (%d, %d complete):" % (r.outlier["episodes"], r.outlier["complete"])]
    for e in r.episodes:
        flag = "" if e.complete else ("  OPEN" if e.end is None else "  START UNSEEN")
        out.append("  %s to %s, peak %.3f%s on %s%s" % (
            e.start, e.end or "now", e.peak, u, e.peak_date, flag))
    o = r.outlier
    if o["excess_ratio"] is None:
        out.append("Outlier test: one episode, nothing to compare it with.")
    else:
        verdict = ("excluded, %s to %s (%d periods)" % o["run"] if o["excluded"]
                   else "kept: %d other complete episode(s), %d needed"
                   % (o["other_complete"], r.settings.min_other_episodes)
                   if o["is_outlier"] else "not an outlier")
        out.append("Outlier test: worst rose %.2fx the next worst; %s."
                   % (o["excess_ratio"], verdict))
    out.append("Complete episodes by height setting: " + ", ".join(
        "%g:%d" % fc for fc in r.sweep))
    out += ["", "Normal level %.3f%s, worst retained %.3f%s" % (r.normal, u, r.anchor, u),
            "Candidate cutoffs (score n+1 begins at):"]
    for i, b in enumerate(r.bounds):
        out.append("  %d -> %d  at %.3f%s" % (i + 1, i + 2, b, u))
    out.append("Latest %s: %.3f%s, score %d" % (r.latest.date, r.latest.value, u, r.latest_score))
    out += ["", "Candidates for the bank to accept, adjust or reject; not thresholds."]
    return "\n".join(out)


def main(argv=None):
    a = _parser().parse_args(argv)
    if a.command == "profile":
        try:
            pr = profile(_read(a.csv), a.name, a.unit, a.direction, a.frequency,
                         a.smoothing)
        except (SeriesError, ValueError) as exc:
            print("REFUSED: %s" % exc, file=sys.stderr)
            return 2
        print(json.dumps(pr, indent=2) if a.json else report(pr))
        return 0
    if a.command == "workbook":
        pairs = []
        for item in a.series:
            label, sep, path = item.partition("=")
            if not sep or not label or not path:
                print("REFUSED: --series takes LABEL=FILE, not %r" % item, file=sys.stderr)
                return 2
            pairs.append((label, path))
        try:
            from .workbook import build
            r = build(a.out, pairs, a.name, a.unit, a.direction, a.frequency, a.smoothing,
                      a.floor_at_zero, a.moderate_halfwidth, a.low_step, a.high_z, a.on_the_line,
                      a.half_lives,
                      a.percentiles, a.horizon, a.min_history)
        except (SeriesError, ValueError, OSError) as exc:
            print("REFUSED: %s" % exc, file=sys.stderr)
            return 2
        print("Wrote %s: %s, %d quarters" % (r["path"], ", ".join(r["products"]), r["quarters"]))
        return 0
    if a.command == "backtest":
        try:
            r = backtest(_read(a.csv), a.name, a.unit, a.direction, a.frequency,
                         a.smoothing, a.percentiles, a.horizon, a.min_history,
                         a.floor_at_zero, a.half_lives)
        except (SeriesError, ValueError) as exc:
            print("REFUSED: %s" % exc, file=sys.stderr)
            return 2
        print(json.dumps(r, indent=2) if a.json else backtest_report(r))
        return 0
    if a.command == "evidence":
        try:
            ev = evidence(_read(a.csv), a.name, a.unit, a.direction, a.frequency,
                          a.smoothing, a.scale_points, a.top_fraction, a.floor_at_zero,
                          a.half_lives)
        except (SeriesError, ValueError) as exc:
            print("REFUSED: %s" % exc, file=sys.stderr)
            return 2
        print(json.dumps(ev, indent=2, default=str) if a.json else evidence_report(ev))
        return 0
    m = Measure(a.name, a.unit, a.direction, a.frequency, a.smoothing, a.floor_at_zero)
    s = Settings(a.scale_points, a.top_fraction, a.episode_height, a.materiality,
                 a.outlier_ratio, a.min_other_episodes,
                 tuple(a.window) if a.window else None,
                 tuple(tuple(x) for x in a.exclude))
    r = run(m, s, _read(a.csv))
    if isinstance(r, Refused):
        print("REFUSED at %s (%s): %s" % (r.stage, r.code, r.reason), file=sys.stderr)
        return 2
    print(json.dumps(dataclasses.asdict(r), indent=2) if a.json else _report(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
