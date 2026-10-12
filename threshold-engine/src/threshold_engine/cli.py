"""Run the engine on CSVs of dated values. Five commands: workbook (the
deliverable: every product in one Excel file with live lines), profile,
evidence, backtest and peers. docs/WHAT-IT-DOES.md says what each does.

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
        --last 2026Q2 --products ... [--mergers SINCE] [--refresh]

fetches every FDIC filer's quarter into ``DIR/q{YYYYMMDD}.json`` (only the
quarters not already there) and, with ``--mergers``, the classified merger
record into ``DIR/mergers.json``.

    python -m threshold_engine peers build OUT.xlsx --cache DIR --roster
        config/peers.json --jump 0.25 --min-book 1000000 --pack all|regionals
        --series-dir DIR ...

reads the cache (never the network), writes the peer workbook, and per product
the ``date,value`` CSVs the ``workbook`` command reads: the pack composite,
the bank itself and the industry, each gross and net. docs/PEERS-SPEC.md.

Every setting that is a judgement is required: the command will not run on a
value nobody stated. The CSV has a ``date,value`` header; lines starting with
``#`` are notes.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path

from .backtest import backtest, report as backtest_report
from .evidence import evidence, report as evidence_report
from .profile import profile, report
from .series import Point, SeriesError



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
    w.add_argument("--industry-combined", required=True, nargs="*", metavar="PRODUCT+PRODUCT",
                   help="industry series for products summed together, e.g. \"Other consumer+Auto\"; "
                        "give the flag with nothing after it to state there are none")
    r = bu.add_argument_group("the rules, all required")
    # float, not _number: _at_least refuses NaN and infinity for these by name.
    r.add_argument("--jump", required=True, type=float,
                   help="a quarter-on-quarter balance move above this (0.25 = 25%%) is structural")
    r.add_argument("--min-book", required=True, type=float,
                   help="the smallest average balance ($000) whose rate is kept")
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


def _slug(text):
    """'Credit card' -> 'credit-card'."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _fields(products):
    from .peers.books import PRODUCTS
    return [f for p in products for f in PRODUCTS[p]]


def _peers_pull(a):
    """Fetch the quarters not already cached; with --mergers, the merger record.

    Everything stated is checked before the first request, so a typo in the
    --mergers date never costs a whole pull before the command refuses."""
    from .peers import fdic
    quarters = fdic.quarter_ends(a.first, a.last)
    if a.mergers:
        fdic.quarter_end(a.mergers)                         # refuses anything but YYYY-MM-DD
    cache = Path(a.cache)
    before = {q for q in quarters if (cache / ("q%s.json" % q)).exists()}
    data = fdic.pull(quarters, _fields(a.products), cache, refresh=a.refresh)
    fetched = len(quarters) if a.refresh else len(quarters) - len(before)
    print("Cache %s: %d quarters %s to %s, %d fetched, %d already there"
          % (cache, len(quarters), a.first, a.last, fetched, len(quarters) - fetched))
    print("Filers in %s: %d" % (a.last, len(data[quarters[-1]])))
    if a.mergers:
        m = fdic.pull_mergers(a.mergers)
        path = cache / "mergers.json"
        path.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")
        print("Wrote %s: %d acquirers since %s" % (path, len(m), a.mergers))
    return 0


def _unbroken_tail(rows):
    """The latest unbroken run of ``(quarter, value)`` pairs, the quarters
    before it that are left out, and the quarters after it that are left out.

    The workbook refuses a series with a gap, and a gap is never filled, so a
    series whose values break off (a quarter not kept) is written from the
    first quarter after its last break. A series whose latest quarters have no
    value ends at its last value. What is left out, at either end, is named,
    not hidden: unnamed, an older value would be read as the latest one.
    """
    rows = list(rows)
    end = len(rows)
    while end and rows[end - 1][1] is None:
        end -= 1
    start = end
    while start and rows[start - 1][1] is not None:
        start -= 1
    return rows[start:end], [q for q, _ in rows[:start]], [q for q, _ in rows[end:]]


def _series_note(note, tail, before, after):
    """The note lines for a series written from ``tail``: the given note, then
    what is left out before the run and after it. An empty ``tail`` is not
    written, so it has no note."""
    if not tail:
        return []
    lines = list(note)
    if before:
        lines.append("Written from %s, the first quarter after the last break; %d earlier quarters "
                     "(%s to %s) are left out, because the workbook refuses a gap and a gap is not "
                     "filled." % (tail[0][0], len(before), before[0], before[-1]))
    if after:
        which = ("the latest quarter, %s, has" % after[0] if len(after) == 1 else
                 "the %d latest quarters, %s to %s, have" % (len(after), after[0], after[-1]))
        lines.append("Ends at %s, not at the last quarter read: %s no value, so the last value "
                     "here is not the latest quarter's." % (tail[-1][0], which))
    return lines


def _at_least(flag, value, low):
    """Refuse a stated rule below its floor. NaN and infinity are refused too:
    nothing is above NaN, so a NaN jump would quietly switch the rule off."""
    if not (math.isfinite(value) and value >= low):
        raise ValueError("%s must be a number of at least %s, not %r" % (flag, low, value))


def _load_mergers(path):
    """``{cert: [quarter-end dates]}`` from the --mergers file, every date
    checked here, so a bad file is refused by name rather than failing later."""
    from .peers.books import quarter_end
    try:
        mergers = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("%s is not valid JSON: %s" % (path, exc)) from None
    if not isinstance(mergers, dict):
        raise ValueError("%s must hold {cert: [quarter-end dates]}" % path)
    for cert, dates in mergers.items():
        if not isinstance(dates, list) or not all(isinstance(d, str) for d in dates):
            raise ValueError("%s: certificate %s must have a list of quarter-end dates, not %r"
                             % (path, cert, dates))
        for d in dates:
            try:
                quarter_end(d)
            except ValueError:
                raise ValueError("%s: certificate %s has %r, which is not a quarter-end date"
                                 % (path, cert, d)) from None
    return mergers


def _extras(items, roster, quarters):
    """``{cert: [YYYYQn]}`` from --extra-acquisitions. A certificate not on the
    roster, or a quarter outside the data read, is refused: a typo there would
    otherwise be ignored and the acquisition's growth counted as organic."""
    from .peers import fdic
    from .peers.books import label
    certs = {b["cert"] for b in roster}
    extras = {}
    for item in items:
        cert, sep, q = item.partition("=")
        cert, q = cert.strip(), q.strip()
        if not sep or not cert.isdigit() or not re.fullmatch(r"\d{4}Q[1-4]", q):
            raise ValueError("--extra-acquisitions takes CERT=YYYYQn, not %r" % item)
        if cert not in certs:
            raise ValueError("--extra-acquisitions names certificate %s, which is not on the roster"
                             % cert)
        if fdic.quarter_ends(q, q)[0] not in quarters:
            raise ValueError("--extra-acquisitions gives %s for %s, outside the quarters read (%s to %s)"
                             % (q, cert, label(quarters[0]), label(quarters[-1])))
        extras.setdefault(cert, []).append(q)
    return extras


def _combined(items):
    """``[[product, ...]]`` from --industry-combined: two or more distinct
    product names joined by ``+``."""
    from .peers.books import PRODUCTS
    out = []
    for item in items:
        names = [n.strip() for n in item.split("+")]
        if len(names) < 2 or len(set(names)) != len(names) or any(n not in PRODUCTS for n in names):
            raise ValueError("--industry-combined takes two or more products joined by +, from %s, "
                             "not %r" % (", ".join(PRODUCTS), item))
        out.append(names)
    return out


def _peers_build(a):
    """Read the cache, write the peer workbook and the series CSVs.

    Every stated setting is checked before anything is read or written. The
    series are computed first; the workbook and the CSVs are written beside
    their final names and moved into place only once all of them are written,
    so a refusal never leaves a new workbook beside an old or partial series
    set. A series with no value this run has its CSV from an earlier run
    removed, since that file was built under other rules."""
    from .peers import fdic, roster as R
    from .peers.books import bank_book, composite, industry, write_series
    from .peers.peers_workbook import build_peers_workbook

    for flag, value, low in (("--jump", a.jump, 0), ("--min-book", a.min_book, 0),
                             ("--index-min-book", a.index_min_book, 0), ("--min-banks", a.min_banks, 1),
                             ("--last-n", a.last_n, 1), ("--min-obs", a.min_obs, 1),
                             ("--lag-years", a.lag_years, 0)):
        _at_least(flag, value, low)
    quarters = fdic.quarter_ends(a.first, a.last)
    roster = R.load(a.roster)
    me = R.self_bank(roster)
    pack = R.peers(roster) if a.pack == "all" else R.regionals(roster)
    mergers = _load_mergers(a.mergers)
    extras = _extras(a.extra_acquisitions, roster, quarters)
    combined = _combined(a.industry_combined)

    cache = Path(a.cache)
    missing = [q for q in quarters if not (cache / ("q%s.json" % q)).exists()]
    if missing:
        raise ValueError("%s has no %d of the %d quarters asked for (first missing %s): run "
                         "'peers pull' first; build never fetches"
                         % (cache, len(missing), len(quarters), missing[0]))

    def no_fetch(url):
        raise ValueError("build reads the cache only and never fetches")
    data = fdic.pull(quarters, _fields(list(a.products) + [p for c in combined for p in c]),
                     cache, fetch=no_fetch)

    filers = len(data[quarters[-1]])
    ind = {p: industry(data, p) for p in a.products}
    rule = ("Rules: jump %g, minimum book %s ($000)%s, at least %d banks in a composite."
            % (a.jump, "{:,.0f}".format(a.min_book),
               ", %s exempt" % me["short"] if a.exempt_self else "", a.min_banks))
    source = "Source: FDIC BankFind financials, %s to %s, from the cache %s." % (a.first, a.last, cache)
    every = "every filer in the cache (%d in %s), no jump or minimum rule" % (filers, a.last)
    out_dir = Path(a.series_dir)
    pack_words = "all %d peers" % len(pack) if a.pack == "all" else "%d regionals" % len(pack)

    made = []                   # (product words, file slug, who, words, rules apply?, rows)
    for p in a.products:
        books = {b["cert"]: bank_book(data, b["cert"], p, a.jump, a.min_book,
                                      exempt_min_book=a.exempt_self and b is me) for b in roster}
        comp = composite(books, [b["cert"] for b in pack], a.min_banks)
        made += [
            (p, _slug(p), "pack-composite",
             "pack composite (%s): kept flows over kept average balances" % pack_words, True, comp),
            (p, _slug(p), _slug(me["short"]),
             "%s (certificate %s), its own book" % (me["short"], me["cert"]), True, books[me["cert"]]),
            (p, _slug(p), "industry", "industry: " + every, False, ind[p]),
        ]
    for names in combined:
        made.append((" plus ".join(names), _slug(" ".join(names)), "industry",
                     "industry, %s summed: %s" % (" and ".join(names), every), False,
                     industry(data, names[0], names[1:])))

    series = []                 # (path, tail, note lines, left out before, left out after)
    for words_p, slug, who, words, ruled, rows in made:
        for kind in ("gross", "net"):
            tail, before, after = _unbroken_tail([(r["quarter"], r[kind + "_rate"]) for r in rows])
            note = ["%s, %s charge-off rate, trailing four quarters, %%." % (words_p, kind),
                    words[0].upper() + words[1:] + ".", source] + ([rule] if ruled else [])
            series.append((out_dir / ("%s_%s_%s.csv" % (slug, who, kind)), tail,
                           _series_note(note, tail, before, after), before, after))

    out = Path(a.out)
    part_out = out.with_name(out.stem + ".part" + out.suffix)
    parts = []
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        info = build_peers_workbook(
            part_out, data, roster, a.products, a.jump, a.min_book, a.pack, mergers, extras,
            a.base_quarter, exempt_self=a.exempt_self, min_banks=a.min_banks, rank_by=a.rank_by,
            last_n=a.last_n, min_obs=a.min_obs, index_min_book=a.index_min_book,
            lagged_years=a.lagged_years, lag_years=a.lag_years,
            normalisation_years=a.normalisation_years, mix_base_year=a.mix_base_year,
            industry=ind, cache_dir=cache, mergers_file=a.mergers,
            sources=["Read from the cache %s, %d quarter files %s to %s, built %s"
                     % (cache, len(quarters), quarters[0], quarters[-1],
                        dt.date.today().isoformat())])
        for path, tail, lines, _, _ in series:
            if tail:
                part = path.with_name(path.name + ".part")
                parts.append(part)
                write_series(tail, part, lines)
        for part in parts:
            os.replace(str(part), str(part)[:-len(".part")])
        parts = []
        os.replace(str(part_out), str(out))
    finally:
        for f in parts + [part_out]:
            if f.exists():
                f.unlink()

    print("Wrote %s: %s, %d TTM quarters, pack of %d"
          % (out, ", ".join(info["products"]), len(info["quarters"]), len(info["pack"])))
    for path, tail, _, before, after in series:
        if not tail:
            gone = path.exists()
            if gone:
                path.unlink()
            print("Not written: %s has no value%s"
                  % (path.name, "; the file from an earlier run is removed" if gone else ""))
        else:
            print("Wrote %s: %d quarters%s%s"
                  % (path, len(tail), ", %d earlier left out at a break" % len(before) if before else "",
                     ", ends %s: %d later quarter%s with no value"
                     % (tail[-1][0], len(after), "" if len(after) == 1 else "s") if after else ""))
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
