"""Run the engine on CSVs of dated values. Four commands: workbook (the
deliverable: every product in one Excel file with live lines), profile,
evidence and backtest. docs/WHAT-IT-DOES.md says what each does.

    python -m threshold_engine profile SERIES.csv --name ... --unit ...
        --direction ... --frequency ... --smoothing ...

reports facts about the series and decides nothing: its distribution, every
spell worse than the median, how often each upper percentile was reached, the
percentiles without the largest spell, and where the latest value ranks.

    python -m threshold_engine evidence SERIES.csv ... --moderate-halfwidth ...
        --low-step ... --high-z ... --on-the-line worse|better

puts statistics on each judgement and shows the lines under three scenarios,
on the same scale as the workbook (threshold_engine.scale).

Every setting that is a judgement is required: the command will not run on a
value nobody stated. The CSV has a ``date,value`` header; lines starting with
``#`` are notes.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys

from .backtest import backtest, report as backtest_report
from .evidence import evidence, report as evidence_report
from .profile import profile, report
from .series import Point, SeriesError


def _yes_no(text):
    if text not in ("yes", "no"):
        raise argparse.ArgumentTypeError("say yes or no")
    return text == "yes"


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


def _scale_args(g):
    g.add_argument("--moderate-halfwidth", required=True, type=float,
                   help="Moderate's half-width around the median, in typical yearly moves")
    g.add_argument("--low-step", required=True, type=float,
                   help="Moderate-Low begins this many typical yearly moves below the median")
    g.add_argument("--high-z", required=True, type=float,
                   help="High begins at the median plus this many robust spreads of the quarters kept")
    g.add_argument("--on-the-line", required=True, choices=["worse", "better"])


def _parser():
    top = argparse.ArgumentParser(prog="python -m threshold_engine",
                                  description=__doc__.split("\n\n")[0])
    sub = top.add_subparsers(dest="command", required=True)
    pr = sub.add_parser("profile", help="facts about the series; no judgement settings")
    _measure_args(pr)
    pr.add_argument("--json", action="store_true")
    ev = sub.add_parser("evidence", help="statistics for each judgement point, "
                        "and the lines under each answer, on the workbook's scale")
    _measure_args(ev)
    ev.add_argument("--floor-at-zero", required=True, type=_yes_no)
    _scale_args(ev.add_argument_group("the scale, all required"))
    ev.add_argument("--half-lives", type=float, nargs="+", default=[],
                    metavar="YEARS", help="repeat scenario C with the median "
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
    _scale_args(wbp.add_argument_group("starting values for the Settings tab, all required"))
    b = wbp.add_argument_group("the backtest, all required")
    b.add_argument("--percentiles", required=True, type=float, nargs="+", metavar="P")
    b.add_argument("--horizon", required=True, type=int)
    b.add_argument("--min-history", required=True, type=int)
    wbp.add_argument("--half-lives", type=float, nargs="+", default=[], metavar="YEARS")
    return top


def _read(path):
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(line for line in fh if not line.startswith("#"))
        return [Point(r["date"], float(r["value"])) for r in rows]


def _refused(exc):
    print("REFUSED: %s" % exc, file=sys.stderr)
    return 2


def main(argv=None):
    a = _parser().parse_args(argv)
    if a.command == "profile":
        try:
            pr = profile(_read(a.csv), a.name, a.unit, a.direction, a.frequency, a.smoothing)
        except (SeriesError, ValueError) as exc:
            return _refused(exc)
        print(json.dumps(pr, indent=2) if a.json else report(pr))
        return 0
    if a.command == "workbook":
        pairs = []
        for item in a.series:
            label, sep, path = item.partition("=")
            if not sep or not label or not path:
                return _refused("--series takes LABEL=FILE, not %r" % item)
            pairs.append((label, path))
        try:
            from .workbook import build
            r = build(a.out, pairs, a.name, a.unit, a.direction, a.frequency, a.smoothing,
                      a.floor_at_zero, a.moderate_halfwidth, a.low_step, a.high_z, a.on_the_line,
                      a.half_lives, a.percentiles, a.horizon, a.min_history)
        except (SeriesError, ValueError, OSError) as exc:
            return _refused(exc)
        print("Wrote %s: %s, %d quarters" % (r["path"], ", ".join(r["products"]), r["quarters"]))
        return 0
    if a.command == "backtest":
        try:
            r = backtest(_read(a.csv), a.name, a.unit, a.direction, a.frequency,
                         a.smoothing, a.percentiles, a.horizon, a.min_history,
                         a.floor_at_zero, a.half_lives)
        except (SeriesError, ValueError) as exc:
            return _refused(exc)
        print(json.dumps(r, indent=2) if a.json else backtest_report(r))
        return 0
    try:                                                    # evidence
        ev = evidence(_read(a.csv), a.name, a.unit, a.direction, a.frequency, a.smoothing,
                      dict(halfwidth=a.moderate_halfwidth, low_step=a.low_step,
                           high_z=a.high_z, on_the_line=a.on_the_line),
                      a.floor_at_zero, a.half_lives)
    except (SeriesError, ValueError) as exc:
        return _refused(exc)
    print(json.dumps(ev, indent=2, default=str) if a.json else evidence_report(ev))
    return 0


if __name__ == "__main__":
    sys.exit(main())
