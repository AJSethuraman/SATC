"""Run the engine on CSVs of dated values. Seven commands: workbook (the
deliverable: every product in one Excel file with live lines), profile,
evidence, backtest, peers, template and internal. docs/WHAT-IT-DOES.md says
what each does.

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
merger record into ``DIR/mergers.json`` and who absorbed whom into
``DIR/absorptions.json``.

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

    python -m threshold_engine internal template OUT.csv | check FILE
        [--exclusions FILE] | series FILE --out-dir DIR | pull --cache DIR
        --first YYYYQn --last YYYYQn | reconcile FILE --cache DIR --roster
        FILE --exclusions FILE --tolerance X --out FILE.csv

KeyBank's own figures, run on site only (docs/INTERNAL-IMPORT.md): write the
empty file, check a filled one (every problem at once, exit 2), write its
charge-off and past-due series, fetch the Call Report fields reconcile reads
into a cache of their own, and reconcile the file with the filing from that
cache, never the network.

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
from .series import SeriesError, read_csv
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
    _scale_args(wbp.add_argument_group("starting values for Your settings on the Assess tab, all required"))
    b = wbp.add_argument_group("the backtest, all required")
    b.add_argument("--percentiles", required=True, type=_number, nargs="+", metavar="P")
    b.add_argument("--horizon", required=True, type=int)
    b.add_argument("--min-history", required=True, type=int)
    wbp.add_argument("--half-lives", type=_number, nargs="+", default=[], metavar="YEARS")
    sw = wbp.add_argument_group(
        "the synthesis (the Synthesis tab), optional; a series given --synthesis needs --translation and "
        "--leads, and --peer-percentiles when it has peers, each stated for that series")
    sw.add_argument("--synthesis", action="append", default=[],
                    metavar="LABEL=industry:FILE;filed:FILE;peers:FOLDER",
                    help="the industry series (required) and, optionally, KeyBank's filed series and the peers "
                         "(a folder: every .csv in it; or a pattern such as banks/credit-card_*_net.csv) for the "
                         "series LABEL, whose --series file is the internal one")
    sw.add_argument("--translation", action="append", default=[], metavar="LABEL=median ratio|none",
                    help="how that series' industry lines are carried to the internal level")
    sw.add_argument("--peer-percentiles", action="append", default=[], metavar="LABEL=P2,P3,P4,P5",
                    help="the percentile across peers for lines 2, 3, 4 and 5, rising")
    sw.add_argument("--leads", action="append", default=[], metavar="LABEL=SOURCE,SOURCE,SOURCE,SOURCE",
                    help="where lines 2, 3, 4 and 5 are taken from: internal, industry or peers")
    _peers_parser(sub)
    _template_parser(sub)
    _internal_parser(sub)
    bk = sub.add_parser("book", help="one workbook from one book file: Summary, Decide (one series at a time, "
                                     "decisions kept in the file), Thresholds, Assess and, if the book says so, "
                                     "the peer tabs. Every setting is in the book; none has a default")
    bk.add_argument("book", help="the book (.json); its relative paths are read from its own folder")
    bk.add_argument("out", help="the .xlsx to write")
    sy = sub.add_parser("synthesize", help="internal, industry and peers side by side, line by line; "
                        "each line taken from the source you name")
    g = sy.add_argument_group("the series, all required except the peers")
    g.add_argument("--internal", required=True, metavar="FILE", help="KeyBank's own series (date,value)")
    g.add_argument("--industry", required=True, metavar="FILE")
    g.add_argument("--filed", metavar="FILE", help="KeyBank's filed series, to carry peers to the internal level")
    g.add_argument("--peer", action="append", default=[], metavar="NAME=FILE",
                   help="one peer's series; repeat for each (peers build writes them to SERIES-DIR/banks)")
    j = sy.add_argument_group("the judgements, all required")
    j.add_argument("--unit", required=True)
    j.add_argument("--direction", required=True, choices=["higher_is_worse", "lower_is_worse"])
    _scale_args(j)
    j.add_argument("--floor-at-zero", required=True, type=_yes_no)
    j.add_argument("--translation", required=True, choices=["median ratio", "none"],
                   help="how industry lines are carried to the internal level")
    j.add_argument("--peer-percentiles", nargs=4, type=_number, metavar="P",
                   help="the percentile across peers for lines 2, 3, 4 and 5; required with --peer")
    j.add_argument("--leads", required=True, nargs=4, choices=["internal", "industry", "peers"],
                   metavar="SOURCE", help="where lines 2, 3, 4 and 5 come from: internal, industry or peers")
    co = sub.add_parser("compare", help="two series of one measure side by side, by calendar quarter: "
                        "the cross-check (facts only, no tolerance)")
    co.add_argument("a", help="a date,value CSV")
    co.add_argument("b", help="the series to compare it with")
    co.add_argument("--every", action="store_true", help="one line per quarter as well")
    return top


# ---------------------------------------------------------------- peers

def _peer_products():
    from .peers.books import PRODUCTS
    return list(PRODUCTS)


def _peer_product(text):
    """A product, or a combined one: "All consumer", or two or more joined by
    " + " (books.members)."""
    from .peers.books import members
    try:
        members(text)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))
    return text


_PRODUCTS_HELP = "%s; \"All consumer\"; or two or more joined by \" + \", e.g. \"Credit card + Other consumer\""


def _peers_parser(sub):
    """``peers pull`` and ``peers build``: docs/PEERS-SPEC.md, "cli.py additions"."""
    pe = sub.add_parser("peers", help="KeyBank against its peers, from public FDIC Call Reports")
    ps = pe.add_subparsers(dest="peers_command", required=True)

    pu = ps.add_parser("pull", help="fetch every filer's quarters into a cache folder")
    pu.add_argument("--cache", required=True, metavar="DIR")
    pu.add_argument("--first", required=True, metavar="YYYYQn")
    pu.add_argument("--last", required=True, metavar="YYYYQn")
    pu.add_argument("--products", required=True, nargs="+", type=_peer_product, metavar="PRODUCT",
                    help="whose fields to pull: " + _PRODUCTS_HELP % ", ".join(_peer_products()))
    pu.add_argument("--mergers", metavar="SINCE",
                    help="also pull the merger record from this date (YYYY-MM-DD) into DIR/mergers.json")
    pu.add_argument("--delinquency", required=True, type=_yes_no, metavar="yes|no",
                    help="yes: also pull the products' delinquency and nonaccrual fields")
    pu.add_argument("--refresh", action="store_true", help="fetch every quarter again, even if cached")

    cp = ps.add_parser("classes-pull", help="each peer's 10-Q (or 10-K) for one quarter from SEC EDGAR into a "
                                            "cache folder: what its consumer loan classes hold")
    cp.add_argument("--cache", required=True, metavar="DIR")
    cp.add_argument("--classes", required=True, metavar="FILE",
                    help="the loan classes file (config/peer-loan-classes.json): whose filings to fetch")
    cp.add_argument("--quarter", required=True, metavar="YYYYQn")
    cp.add_argument("--user-agent", required=True, metavar="\"NAME EMAIL\"",
                    help="who is asking, with a contact email: SEC's fair-access policy requires it; not stored")
    cp.add_argument("--refresh", action="store_true", help="fetch again, even if held")

    lb = ps.add_parser("large-banks-pull", help="the Philadelphia Fed's large bank credit card balances file for "
                                                "one quarter (every quarter since 2012Q3 is in it) into DIR/large-banks")
    lb.add_argument("--cache", required=True, metavar="DIR")
    lb.add_argument("--quarter", required=True, metavar="YYYYQn")
    lb.add_argument("--refresh", action="store_true", help="fetch again, even if held")

    il = ps.add_parser("industry-long", help="the industry's net and gross charge-off series over a cache that "
                                             "reaches before 2006, as separate series (Source 'Industry (every "
                                             "bank) from YYYY'), from the cache only")
    il.add_argument("out_dir", metavar="OUT_DIR")
    il.add_argument("--cache", required=True, metavar="DIR")
    il.add_argument("--first", required=True, metavar="YYYYQn")
    il.add_argument("--last", required=True, metavar="YYYYQn")
    il.add_argument("--products", required=True, nargs="+", type=_peer_product, metavar="PRODUCT")
    il.add_argument("--absorptions", required=True, metavar="FILE",
                    help="the absorptions file 'peers pull --mergers' wrote")
    il.add_argument("--reporting-changes", required=True, metavar="FILE", help="config/reporting-changes.json")

    bu = ps.add_parser("build", help="the peer workbook and the series CSVs, from the cache only")
    bu.add_argument("out", help="the .xlsx to write")
    bu.add_argument("--cache", required=True, metavar="DIR")
    bu.add_argument("--roster", required=True, metavar="FILE")
    bu.add_argument("--series-dir", required=True, metavar="DIR")
    w = bu.add_argument_group("what to read, all required")
    w.add_argument("--first", required=True, metavar="YYYYQn")
    w.add_argument("--last", required=True, metavar="YYYYQn")
    w.add_argument("--products", required=True, nargs="+", type=_peer_product, metavar="PRODUCT",
                   help=_PRODUCTS_HELP % ", ".join(_peer_products()))
    w.add_argument("--mergers", required=True, metavar="FILE",
                   help="{cert: [quarter-end dates]}, as 'peers pull --mergers' writes it")
    w.add_argument("--absorptions", required=True, metavar="FILE",
                   help="who absorbed whom, as 'peers pull --mergers' writes it beside the merger record")
    w.add_argument("--extra-acquisitions", required=True, nargs="*", metavar="CERT=QUARTER",
                   help="acquisitions the FDIC record does not show, e.g. 6672=2022Q2; "
                        "give the flag with nothing after it to state there are none")
    w.add_argument("--delinquency", required=True, type=_yes_no, metavar="yes|no",
                   help="yes: also the delinquency view on the Peers tab, DelinquencyData and, per product, measure "
                        "and basis, the "
                        "delinquency CSVs, under the rules below (the cache must hold the fields)")
    w.add_argument("--reporting-changes", required=True, metavar="FILE",
                   help="the registry of Call Report changes (config/reporting-changes.json): each series file "
                        "notes every change touching it, and the charts mark the quarters")
    w.add_argument("--industry-combined", required=True, nargs="*", metavar="PRODUCT+PRODUCT",
                   help="industry series for products summed together, e.g. \"Other consumer+Auto\"; "
                        "give the flag with nothing after it to state there are none")
    r = bu.add_argument_group("the rules, all required")
    # float, not _number: peers.run.at_least refuses NaN and infinity for these by name.
    r.add_argument("--jump", required=True, type=float,
                   help="a quarter-on-quarter balance move above this (0.25 = 25%%) is structural; "
                        "under --delinquency yes it blanks a four-quarter average, never a quarter-end rate")
    r.add_argument("--acquisition-share", required=True, type=float,
                   help="leave out a bank's windows around a quarter whose acquisitions, added "
                        "together, brought in at least this share of its book (0.05 = 5%%)")
    r.add_argument("--min-book", required=True, type=float,
                   help="the smallest average balance ($000) whose rate is kept; for delinquency, "
                        "the quarter-end balance")
    r.add_argument("--exempt-self", required=True, type=_yes_no,
                   help="yes: the bank itself is drawn whatever its size")
    r.add_argument("--pro-forma", required=True, type=_yes_no,
                   help="yes: each bank's charge-offs and balances include those of every bank it "
                        "absorbed, before the absorption (an acquisition no longer breaks its history); "
                        "no: each bank as filed")
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


def _peers_industry_long(a):
    """``peers industry-long``: peers.long_industry.write."""
    from .peers import long_industry as LI
    try:
        LI.write(a.out_dir, cache=a.cache, first=a.first, last=a.last, products=a.products,
                 absorptions=a.absorptions, reporting_changes=a.reporting_changes)
    except ValueError as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2
    return 0


def _peers_large_banks_pull(a):
    """``peers large-banks-pull``: peers.large_banks.pull."""
    from .peers import large_banks as LB
    try:
        LB.pull(a.cache, a.quarter, refresh=a.refresh)
    except ValueError as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 2
    return 0


def _peers_classes_pull(a):
    """``peers classes-pull``: peers.classes.pull for the banks the loan classes file names."""
    from .peers import classes, loan_classes_tab
    spec = loan_classes_tab.load(a.classes)
    classes.pull(a.cache, spec["banks"], a.quarter, a.user_agent, refresh=a.refresh)
    return 0


def _peers_build(a):
    """``peers build``: peers.run.build with the flags as stated."""
    from .peers import run
    run.build(a.out, cache=a.cache, roster=a.roster, series_dir=a.series_dir, first=a.first,
              last=a.last, products=a.products, mergers=a.mergers, absorptions=a.absorptions,
              extra_acquisitions=a.extra_acquisitions, industry_combined=a.industry_combined,
              jump=a.jump, acquisition_share=a.acquisition_share, min_book=a.min_book, exempt_self=a.exempt_self, pro_forma=a.pro_forma, pack=a.pack,
              min_banks=a.min_banks, rank_by=a.rank_by, last_n=a.last_n, min_obs=a.min_obs,
              base_quarter=a.base_quarter, index_min_book=a.index_min_book,
              lagged_years=a.lagged_years, lag_years=a.lag_years,
              normalisation_years=a.normalisation_years, mix_base_year=a.mix_base_year,
              delinquency=a.delinquency, reporting_changes=a.reporting_changes)
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
              "quarters, then run: python -m threshold_engine template check %s %s"
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
          "command's --series; its backtest runs only when --min-history + --horizon + "
          "--smoothing - 1 is %d or less, and otherwise says it was not tested." % (a.file, a.key,
                                                                                     T.TEMPLATES[a.key].title, n, n))
    return 0


_read = read_csv


# ---------------------------------------------------------------- internal

def _internal_parser(sub):
    """``internal template|check|series|pull|reconcile``: docs/INTERNAL-IMPORT.md."""
    it = sub.add_parser("internal", help="KeyBank's own figures, run on site only: check the file, "
                        "write its series, reconcile it with the Call Report")
    ins = it.add_subparsers(dest="internal_command", required=True)
    te = ins.add_parser("template", help="write the empty internal file and its exclusions file")
    te.add_argument("out", help="the .csv to write; OUT.exclusions.csv is written beside it")
    ch = ins.add_parser("check", help="OK, or every problem at once (exit 2)")
    ch.add_argument("file")
    ch.add_argument("--exclusions", metavar="FILE", help="also check this exclusions file")
    se = ins.add_parser("series", help="one date,value CSV per product, segment and measure")
    se.add_argument("file")
    se.add_argument("--out-dir", required=True, metavar="DIR")
    pu = ins.add_parser("pull", help="fetch every Call Report field reconcile reads into a cache of its own")
    pu.add_argument("--cache", required=True, metavar="DIR")
    pu.add_argument("--first", required=True, metavar="YYYYQn")
    pu.add_argument("--last", required=True, metavar="YYYYQn")
    re_ = ins.add_parser("reconcile", help="filed, less named exclusions, against internal; from the "
                         "cache only")
    re_.add_argument("file")
    r = re_.add_argument_group("all required")
    r.add_argument("--cache", required=True, metavar="DIR")
    r.add_argument("--roster", required=True, metavar="FILE",
                   help="the peer roster; its 'self' bank is the Call Report filer compared")
    r.add_argument("--exclusions", required=True, metavar="FILE",
                   help="the named exclusions; a file with a header and no rows states there are none")
    r.add_argument("--tolerance", required=True, type=_number,
                   help="the share of the internal figure an unexplained remainder may be, e.g. 0.01")
    r.add_argument("--out", required=True, metavar="FILE.csv")


def _problems(path, problems, what):
    print("REFUSED: %s does not pass as %s; %d problem%s:"
          % (path, what, len(problems), "" if len(problems) == 1 else "s"), file=sys.stderr)
    for p in problems:
        print("  - %s" % p, file=sys.stderr)
    return 2


def _internal(a):
    """Run an internal command; a refusal prints every problem and returns 2."""
    from . import internal as I
    cmd = a.internal_command
    if cmd == "template":
        out, ex = I.write_template(a.out)
        print("Wrote %s and %s. Answer every [STATE: ...] line, add the rows, then run: "
              "python -m threshold_engine internal check %s --exclusions %s" % (out, ex, out, ex))
        return 0
    if cmd == "pull":
        data = I.pull(a.cache, a.first, a.last)
        print("Cache %s: %d quarters, %s to %s, with %s" % (a.cache, len(data), a.first, a.last,
                                                          ", ".join(I.FIELDS)))
        return 0
    # Both files are checked before either refusal is printed, so every
    # problem is listed at once.
    bad = [(a.file, I.check(a.file), "an internal file")]
    if getattr(a, "exclusions", None):
        bad.append((a.exclusions, I.check_exclusions(a.exclusions), "an exclusions file"))
    bad = [b for b in bad if b[1]]
    if bad:
        for path, problems, what in bad:
            _problems(path, problems, what)
        return 2
    internal = I.read(a.file)
    ex = I.read_exclusions(a.exclusions) if getattr(a, "exclusions", None) else None
    if cmd == "check":
        qs = sorted({r.quarter for r in internal.rows}, key=I.qindex)
        worked = {}
        for r in internal.rows:
            if r.worked_out:
                worked[r.worked_out] = worked.get(r.worked_out, 0) + 1
        print("OK: %s passes: %d rows, %s to %s; %s." % (
            a.file, len(internal.rows), qs[0], qs[-1],
            "; ".join("%s / %s %d quarters" % (p, s, len(internal.rows_for(p, s)))
                      for p, s in internal.keys())))
        if worked:
            print("Worked out from the other two: %s." % ", ".join(
                "%s on %d row%s" % (k, n, "" if n == 1 else "s") for k, n in worked.items()))
        if internal.extra_columns:
            print("Further columns carried through, never compared with public data: %s."
                  % ", ".join(internal.extra_columns))
        if ex is not None:
            print("OK: %s passes: %d exclusion%s." % (a.exclusions, len(ex.rows),
                                                       "" if len(ex.rows) == 1 else "s"))
        return 0
    if cmd == "series":
        made = I.write_all_series(internal, a.out_dir)
        written = [m for m in made if m["written"]]
        print("Wrote %d of %d series to %s." % (len(written), len(made), a.out_dir))
        for m in made:
            if not m["written"]:
                print("Not written: %s has no value." % m["path"].name)
        return 0
    from .peers import roster as R
    bank = R.self_bank(R.load(a.roster))
    try:
        filed = I.read_filed(internal, a.cache)
        rows = I.reconcile(internal, filed, ex, a.tolerance, bank=bank,
                           absorptions=I.read_absorptions(a.cache))
    except I.Refused as exc:
        return _problems(exc.path, exc.problems, "exclusions for this internal file")
    notes = I.reconcile_notes(internal, ex, bank, a.tolerance,
                              "Source: FDIC Call Report, from the cache %s, certificate %s." % (a.cache, bank["cert"]))
    I.write_reconciliation(rows, notes, a.out)
    count = {}
    for r in rows:
        count[r["within_tolerance"]] = count.get(r["within_tolerance"], 0) + 1
    print("Wrote %s: %d rows; within tolerance %d, outside %d, not measured %d. Compared %s with %s "
          "(certificate %s)." % (a.out, len(rows), count.get(I.YES, 0), count.get(I.NO, 0),
                                 count.get(I.NOT_MEASURED, 0), internal.notes["entity"], bank["name"],
                                 bank["cert"]))
    for r in rows:
        if r["within_tolerance"] == I.NO:
            print("  outside: %s %s %s, remainder %s" % (r["quarter"], r["comparison"], r["measure"],
                                                        I._cell(r["remainder"])))
    return 0


def _refused(exc):
    print("REFUSED: %s" % exc, file=sys.stderr)
    return 2


def main(argv=None):
    a = _parser().parse_args(argv)
    if a.command == "internal":
        try:
            return _internal(a)
        except (ValueError, OSError, RuntimeError) as exc:
            return _refused(exc)
    if a.command == "template":
        try:
            return _template(a)
        except (ValueError, OSError) as exc:
            return _refused(exc)
    if a.command == "peers":
        try:
            return {"pull": _peers_pull, "classes-pull": _peers_classes_pull,
                    "large-banks-pull": _peers_large_banks_pull,
                    "industry-long": _peers_industry_long}.get(a.peers_command, _peers_build)(a)
        except (ValueError, OSError, RuntimeError) as exc:
            return _refused(exc)
    if a.command == "book":
        try:
            from .book import build as build_book
            r = build_book(a.book, a.out)
        except (SeriesError, ValueError, OSError, RuntimeError) as exc:
            return _refused(exc)
        print("Wrote %s: %d series, %d quarters; open it on Summary, decide on Decide"
              % (r["path"], len(r["products"]), r["quarters"]))
        return 0
    if a.command == "synthesize":
        try:
            from .synthesis import report as synthesis_report, synthesize
            peers = {}
            for item in a.peer:
                name, sep, path = item.partition("=")
                if not sep or not name or not path:
                    return _refused("--peer takes NAME=FILE, not %r" % item)
                if name in peers:
                    return _refused("--peer names %s twice; each peer once" % name)
                peers[name] = read_csv(path)
            r = synthesize(read_csv(a.internal), read_csv(a.industry), read_csv(a.filed) if a.filed else None,
                           peers, direction=a.direction, halfwidth=a.moderate_halfwidth, low_step=a.low_step,
                           high_z=a.high_z, floor_at_zero=a.floor_at_zero, on_the_line=a.on_the_line,
                           translation=a.translation, peer_percentiles=a.peer_percentiles, leads=a.leads)
        except (SeriesError, ValueError, OSError) as exc:
            return _refused(exc)
        print(synthesis_report(r, a.unit))
        return 0
    if a.command == "compare":
        try:
            from .compare import files
            print(files(a.a, a.b, a.every))
        except (SeriesError, ValueError, OSError) as exc:
            return _refused(exc)
        return 0
    if a.command == "profile":
        try:
            pr = profile(_read(a.csv), a.name, a.unit, a.direction, a.frequency, a.smoothing)
        except (SeriesError, ValueError, OSError) as exc:
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
            from .synthesis_tab import from_flags
            from .workbook import build
            syn = from_flags(a.synthesis, a.translation, a.peer_percentiles, a.leads, [lb for lb, _ in pairs])
            r = build(a.out, pairs, a.name, a.unit, a.direction, a.frequency, a.smoothing,
                      a.floor_at_zero, a.moderate_halfwidth, a.low_step, a.high_z, a.on_the_line,
                      a.half_lives, a.percentiles, a.horizon, a.min_history, synthesis=syn)
        except (SeriesError, ValueError, OSError) as exc:
            return _refused(exc)
        print("Wrote %s: %s, %d quarters%s" % (r["path"], ", ".join(r["products"]), r["quarters"],
                                               "; synthesis for %s" % ", ".join(r["synthesis"])
                                               if r["synthesis"] else ""))
        return 0
    if a.command == "backtest":
        try:
            r = backtest(_read(a.csv), a.name, a.unit, a.direction, a.frequency,
                         a.smoothing, a.percentiles, a.horizon, a.min_history,
                         a.floor_at_zero, a.half_lives)
        except (SeriesError, ValueError, OSError) as exc:
            return _refused(exc)
        print(json.dumps(r, indent=2) if a.json else backtest_report(r))
        return 0
    try:                                                    # evidence
        ev = evidence(_read(a.csv), a.name, a.unit, a.direction, a.frequency, a.smoothing,
                      dict(halfwidth=a.moderate_halfwidth, low_step=a.low_step,
                           high_z=a.high_z, on_the_line=a.on_the_line),
                      a.floor_at_zero, a.half_lives)
    except (SeriesError, ValueError, OSError) as exc:
        return _refused(exc)
    print(json.dumps(ev, indent=2, default=str) if a.json else evidence_report(ev))
    return 0


if __name__ == "__main__":
    sys.exit(main())
