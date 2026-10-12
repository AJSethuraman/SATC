"""Run the engine on CSVs of dated values. Six commands: workbook (the
deliverable: every product in one Excel file with live lines), profile,
evidence, backtest, peers and template. docs/WHAT-IT-DOES.md says what each
does.

    python -m threshold_engine profile SERIES.csv --name ... --unit ...
        --direction ... --frequency ... --smoothing ...

reports facts about the series and decides nothing: its distribution, every
spell worse than the median, how often each upper percentile was reached, the
percentiles without the largest spell, and where the latest value ranks.

    python -m threshold_engine evidence SERIES.csv ... --moderate-halfwidth ...
        --low-step ... --high-z ... --on-the-line worse|better

puts statistics on each judgement and shows the lines under three scenarios,
on the same scale as the workbook (threshold_engine.scale).

    python -m threshold_engine peers pull --cache DIR --first 2006Q1
        --last 2026Q2 --products ... --delinquency yes|no [--mergers SINCE]
        [--refresh]

fetches every FDIC filer's quarter into ``DIR/q{YYYYMMDD}.json`` (only the
quarters not already there), with the products' delinquency and nonaccrual
fields when ``--delinquency yes``, and, with ``--mergers``, the classified
merger record into ``DIR/mergers.json``.

    python -m threshold_engine peers build OUT.xlsx --cache DIR --roster
        config/peers.json --jump 0.25 --min-book 1000000 --pack all|regionals
        --series-dir DIR --delinquency yes|no ...

reads the cache (never the network), writes the peer workbook, and per product
the ``date,value`` CSVs the ``workbook`` command reads: the pack composite,
the bank itself and the industry, each gross and net; with ``--delinquency
yes``, the same three per product, delinquency measure and basis, named
``PRODUCT_WHO_delinquency-MEASURE_BASIS.csv``. docs/PEERS-SPEC.md and
docs/V1-ROUND2-SPEC.md, section A. Both are peers/run.py, which the window
calls too.

    python -m threshold_engine template list | write KEY OUT.csv | check KEY FILE.csv

lists the templates for internal measures, writes an empty one with its
checklist, or checks a filled one: OK, or every problem at once and exit 2.
A checked file is an ordinary series. docs/V1-ROUND2-SPEC.md, section B.

Every setting that is a judgement is required: the command will not run on a
value nobody stated. The CSV has a ``date,value`` header; lines starting with
``#`` are notes.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys

from .backtest import backtest, report as backtest_report
from .evidence import evidence, report as evidence_report
from .profile import profile, report
from .series import Point, SeriesError
# The bodies of `peers pull` and `peers build` live in peers/run.py, which the
# window calls too, so the two cannot drift. These names stay for the tests.
from .peers.run import series_note as _series_note  # noqa: F401
from .peers.run import unbroken_tail as _unbroken_tail  # noqa: F401



def _number(text: str) -> float:
    """A float that is a real number: argparse's float takes 'nan' and 'inf'."""
    value = float(text)
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError("%r is not a number" % text)
    return value

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
    g.add_argument("--moderate-halfwidth", required=True, type=_number,
                   help="Moderate's half-width around the median, in typical yearly moves")
    g.add_argument("--low-step", required=True, type=_number,
                   help="Moderate-Low begins this many typical yearly moves below the median")
    g.add_argument("--high-z", required=True, type=_number,
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
    ev.add_argument("--half-lives", type=_number, nargs="+", default=[],
                    metavar="YEARS", help="repeat scenario C with the median "
                    "weighted toward recent years at each half-life")
    ev.add_argument("--json", action="store_true")
    bt = sub.add_parser("backtest", help="how predictive a percentile scale would "
                        "have been, with and without recency weighting")
    _measure_args(bt)
    bt.add_argument("--floor-at-zero", required=True, type=_yes_no)
    bt.add_argument("--percentiles", required=True, type=_number, nargs="+",
                    metavar="P", help="where scores 2, 3, ... begin, e.g. 50 75 90 95")
    bt.add_argument("--horizon", required=True, type=int,
                    help="periods ahead the score is judged against")
    bt.add_argument("--min-history", required=True, type=int,
                    help="periods of history before the first test")
    bt.add_argument("--half-lives", type=_number, nargs="+", default=[], metavar="YEARS")
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
    b.add_argument("--percentiles", required=True, type=_number, nargs="+", metavar="P")
    b.add_argument("--horizon", required=True, type=int)
    b.add_argument("--min-history", required=True, type=int)
    wbp.add_argument("--half-lives", type=_number, nargs="+", default=[], metavar="YEARS")
    _peers_parser(sub)
    _template_parser(sub)
    return top


# ---------------------------------------------------------------- peers

def _peer_products():
    from .peers.books import PRODUCTS
    return list(PRODUCTS)


def _peers_parser(sub):
    """``peers pull`` and ``peers build``: docs/PEERS-SPEC.md, "cli.py additions"."""
    pe = sub.add_parser("peers", help="KeyBank against its peers, from public FDIC Call Reports")
    ps = pe.add_subparsers(dest="peers_command", required=True)

    pu = ps.add_parser("pull", help="fetch every filer's quarters into a cache folder")
    pu.add_argument("--cache", required=True, metavar="DIR")
    pu.add_argument("--first", required=True, metavar="YYYYQn")
    pu.add_argument("--last", required=True, metavar="YYYYQn")
    pu.add_argument("--products", required=True, nargs="+", choices=_peer_products(),
                    metavar="PRODUCT", help="whose fields to pull: %s" % ", ".join(_peer_products()))
    pu.add_argument("--mergers", metavar="SINCE",
                    help="also pull the merger record from this date (YYYY-MM-DD) into DIR/mergers.json")
    pu.add_argument("--delinquency", required=True, type=_yes_no, metavar="yes|no",
                    help="yes: also pull the products' delinquency and nonaccrual fields")
    pu.add_argument("--refresh", action="store_true", help="fetch every quarter again, even if cached")

    bu = ps.add_parser("build", help="the peer workbook and the series CSVs, from the cache only")
    bu.add_argument("out", help="the .xlsx to write")
    bu.add_argument("--cache", required=True, metavar="DIR")
    bu.add_argument("--roster", required=True, metavar="FILE")
    bu.add_argument("--series-dir", required=True, metavar="DIR")
    w = bu.add_argument_group("what to read, all required")
    w.add_argument("--first", required=True, metavar="YYYYQn")
    w.add_argument("--last", required=True, metavar="YYYYQn")
    w.add_argument("--products", required=True, nargs="+", choices=_peer_products(), metavar="PRODUCT")
    w.add_argument("--mergers", required=True, metavar="FILE",
                   help="{cert: [quarter-end dates]}, as 'peers pull --mergers' writes it")
    w.add_argument("--extra-acquisitions", required=True, nargs="*", metavar="CERT=QUARTER",
                   help="acquisitions the FDIC record does not show, e.g. 6672=2022Q2; "
                        "give the flag with nothing after it to state there are none")
    w.add_argument("--delinquency", required=True, type=_yes_no, metavar="yes|no",
                   help="yes: also the Delinquency tabs and, per product, measure and basis, the "
                        "delinquency CSVs, under the rules below (the cache must hold the fields)")
    w.add_argument("--industry-combined", required=True, nargs="*", metavar="PRODUCT+PRODUCT",
                   help="industry series for products summed together, e.g. \"Other consumer+Auto\"; "
                        "give the flag with nothing after it to state there are none")
    r = bu.add_argument_group("the rules, all required")
    # float, not _number: peers.run.at_least refuses NaN and infinity for these by name.
    r.add_argument("--jump", required=True, type=float,
                   help="a quarter-on-quarter balance move above this (0.25 = 25%%) is structural; "
                        "under --delinquency yes it blanks a four-quarter average, never a quarter-end rate")
    r.add_argument("--min-book", required=True, type=float,
                   help="the smallest average balance ($000) whose rate is kept; for delinquency, "
                        "the quarter-end balance")
    r.add_argument("--exempt-self", required=True, type=_yes_no,
                   help="yes: the bank itself is drawn whatever its size")
    r.add_argument("--pack", required=True, choices=["all", "regionals"])
    r.add_argument("--min-banks", required=True, type=int,
                   help="kept banks a composite or band needs")
    r.add_argument("--rank-by", required=True, choices=["gross", "net"])
    r.add_argument("--last-n", required=True, type=int, help="quarters best and worst are ranked over")
    r.add_argument("--min-obs", required=True, type=int, help="kept quarters a bank needs to be ranked")
    a = bu.add_argument_group("the side analyses, all required")
    a.add_argument("--base-quarter", required=True, metavar="YYYYQn", help="the balance index's base")
    a.add_argument("--index-min-book", required=True, type=float,
                   help="the smallest book ($000) at the base that is indexed")
    a.add_argument("--lagged-years", required=True, type=int, nargs="+", metavar="YEAR")
    a.add_argument("--lag-years", required=True, type=int)
    a.add_argument("--normalisation-years", required=True, type=int, nargs=2, metavar=("BASE", "END"))
    a.add_argument("--mix-base-year", required=True, type=int)


def _peers_pull(a):
    """``peers pull``: peers.run.pull with the flags as stated."""
    from .peers import run
    run.pull(cache=a.cache, first=a.first, last=a.last, products=a.products,
             delinquency=a.delinquency, mergers_since=a.mergers, refresh=a.refresh)
    return 0


def _peers_build(a):
    """``peers build``: peers.run.build with the flags as stated."""
    from .peers import run
    run.build(a.out, cache=a.cache, roster=a.roster, series_dir=a.series_dir, first=a.first,
              last=a.last, products=a.products, mergers=a.mergers,
              extra_acquisitions=a.extra_acquisitions, industry_combined=a.industry_combined,
              jump=a.jump, min_book=a.min_book, exempt_self=a.exempt_self, pack=a.pack,
              min_banks=a.min_banks, rank_by=a.rank_by, last_n=a.last_n, min_obs=a.min_obs,
              base_quarter=a.base_quarter, index_min_book=a.index_min_book,
              lagged_years=a.lagged_years, lag_years=a.lag_years,
              normalisation_years=a.normalisation_years, mix_base_year=a.mix_base_year,
              delinquency=a.delinquency)
    return 0


# ---------------------------------------------------------------- template

def _template_parser(sub):
    """``template list|write|check``: docs/V1-ROUND2-SPEC.md, section B."""
    te = sub.add_parser("template", help="templates for internal measures: list, write an empty "
                        "one, check a filled one")
    ts = te.add_subparsers(dest="template_command", required=True)
    ts.add_parser("list", help="every template: key, title, unit and direction")
    wr = ts.add_parser("write", help="write an empty template and its checklist")
    wr.add_argument("key")
    wr.add_argument("out", help="the .csv to write; OUT.checklist.md is written beside it")
    ch = ts.add_parser("check", help="OK, or every problem at once (exit 2)")
    ch.add_argument("key")
    ch.add_argument("file")


def _template(a):
    """Run a template command. ``check`` prints OK, the number of quarters
    and what the workbook command needs of its own settings to build from
    that many, and returns 0; or prints
    every problem under one REFUSED line and returns 2; an unknown key, a file
    that cannot be read, or a write that would overwrite a file is refused
    (ValueError, OSError), also with 2."""
    from . import templates as T
    if a.template_command == "list":
        width = max(len(k) for k in T.TEMPLATES)
        for t in T.TEMPLATES.values():
            print("%-*s  %s  (%s; %s)" % (width, t.key, t.title, t.unit,
                                         t.direction.replace("_", " ")))
        return 0
    if a.template_command == "write":
        csv_path, md = T.write_template(a.key, a.out)
        print("Wrote %s and %s: template %s (%s). Answer every [STATE: ...] line, add the "
              "quarters, then run: threshold-engine template check %s %s"
              % (csv_path, md, a.key, T.TEMPLATES[a.key].title, a.key, csv_path))
        return 0
    problems = T.check(a.key, a.file)
    if problems:
        print("REFUSED: %s does not pass template %s; %d problem%s:"
              % (a.file, a.key, len(problems), "" if len(problems) == 1 else "s"), file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        return 2
    # The check's floor (9 quarters) is the scale's; the workbook's backtest
    # needs --min-history + --horizon quarters after smoothing, settings stated
    # on that command, so the OK line gives the count to set them against
    # rather than promising a build the check cannot know about.
    n = len(_read(a.file))
    print("OK: %s passes template %s (%s): %d quarters. It is an ordinary series for the workbook "
          "command's --series, which builds from it only when --min-history + --horizon + "
          "--smoothing - 1 is %d or less." % (a.file, a.key, T.TEMPLATES[a.key].title, n, n))
    return 0


def _read(path):
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(line for line in fh if not line.startswith("#"))
        return [Point(r["date"], float(r["value"])) for r in rows]


def _refused(exc):
    print("REFUSED: %s" % exc, file=sys.stderr)
    return 2


def main(argv=None):
    a = _parser().parse_args(argv)
    if a.command == "template":
        try:
            return _template(a)
        except (ValueError, OSError) as exc:
            return _refused(exc)
    if a.command == "peers":
        try:
            return _peers_pull(a) if a.peers_command == "pull" else _peers_build(a)
        except (ValueError, OSError, RuntimeError) as exc:
            return _refused(exc)
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
