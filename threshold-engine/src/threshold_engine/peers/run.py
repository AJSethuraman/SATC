"""What ``peers pull`` and ``peers build`` do, as two plain functions, so the
command line and the window call the same code and cannot drift
(docs/V1-ROUND2-SPEC.md, section C).

    pull(cache=..., first=..., last=..., products=..., delinquency=...,
         mergers_since=..., refresh=..., say=print)

fetches every FDIC filer's quarter into ``cache/q{YYYYMMDD}.json`` (only the
quarters not already there, unless ``refresh``), with the delinquency fields
of ``peers/delinquency.py`` added when ``delinquency`` is True, and, with
``mergers_since``, the classified merger record into ``cache/mergers.json``.

    build(OUT.xlsx, cache=..., roster=..., series_dir=..., first=..., ...,
          delinquency=..., say=print)

reads the cache (never the network), writes the peer workbook, and per product
the ``date,value`` CSVs the ``workbook`` command reads: the pack composite,
the bank itself and the industry, each gross and net; with ``delinquency``,
also per product, measure and basis, the same three series of delinquency
and nonaccrual rates.

Every argument is keyword-only and has no default, ``say`` aside (where the
progress lines go): each is a judgement, a location or the data, and none is
filled in. Every stated setting is checked before anything is read or
written; a refusal is a ``ValueError`` (an ``OSError`` or ``RuntimeError``
from the file system or the FDIC passes through), and its message names the
setting by its command-line flag, which is also the window's label.

The delinquency rules are the build's own stated rules, not a second set:
``jump``, ``min_book`` and ``exempt_self`` mean for delinquency what they mean
for charge-offs, as section A states them ("as in ``bank_book``"). Under
delinquency, ``jump`` blanks a bank's own four-quarter average, never a
quarter-end rate, and leaves that bank out of the pack composite's
four-quarter average too (``delinquency.composite_delinquency``); each file's
notes say which. ``min_book`` is read against the quarter-end balance. The workbook's
measure and basis pickers start at the first measure and basis in
``delinquency.MEASURES`` and ``delinquency.BASES`` order (``30-89``,
quarter-end): a starting position, like the product picker's, which the bank
changes in the workbook; every measure and basis is built and written.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from . import books, fdic, peers_workbook
from . import delinquency as D
from . import roster as R

#: The workbook's pickers start here; every measure and basis is built.
START_MEASURE = next(iter(D.MEASURES))
START_BASIS = next(iter(D.BASES))


def slug(text: str) -> str:
    """'Credit card' -> 'credit-card'; '90+ accruing' -> '90-plus-accruing'."""
    return re.sub(r"[^a-z0-9]+", "-", text.replace("+", " plus").lower()).strip("-")


def charge_off_fields(products: Sequence[str]) -> List[str]:
    """The balance, charge-off and recovery fields of the products named."""
    return [f for p in products for f in books.PRODUCTS[p]]


def _products(products) -> List[str]:
    """Distinct product names from ``books.PRODUCTS``, at least one."""
    names = [products] if isinstance(products, str) else list(products or [])
    if not names or len(set(names)) != len(names) or any(p not in books.PRODUCTS for p in names):
        raise ValueError("--products takes one or more distinct products from %s, not %r"
                         % (", ".join(books.PRODUCTS), products))
    return names


def _yes_no(flag, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be stated, yes or no, not %r" % (flag, value))


def unbroken_tail(rows):
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


def series_note(note, tail, before, after):
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


def at_least(flag, value, low):
    """Refuse a stated rule below its floor. NaN and infinity are refused too:
    nothing is above NaN, so a NaN jump would quietly switch the rule off.
    Anything that is not a number is refused the same way."""
    try:
        ok = (not isinstance(value, bool)) and math.isfinite(value) and value >= low
    except TypeError:
        ok = False
    if not ok:
        raise ValueError("%s must be a number of at least %s, not %r" % (flag, low, value))


def _whole(flag, value, low):
    """A whole number of at least ``low``."""
    at_least(flag, value, low)
    if value != int(value):
        raise ValueError("%s must be a whole number, not %r" % (flag, value))


def load_mergers(path):
    """``{cert: [quarter-end dates]}`` from the --mergers file, every date
    checked here, so a bad file is refused by name rather than failing later."""
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
                books.quarter_end(d)
            except ValueError:
                raise ValueError("%s: certificate %s has %r, which is not a quarter-end date"
                                 % (path, cert, d)) from None
    return mergers


def extras(items, roster, quarters):
    """``{cert: [YYYYQn]}`` from --extra-acquisitions. A certificate not on the
    roster, or a quarter outside the data read, is refused: a typo there would
    otherwise be ignored and the acquisition's growth counted as organic."""
    certs = {b["cert"] for b in roster}
    out = {}
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
                             % (q, cert, books.label(quarters[0]), books.label(quarters[-1])))
        out.setdefault(cert, []).append(q)
    return out


def combined(items):
    """``[[product, ...]]`` from --industry-combined: two or more distinct
    product names joined by ``+``. The same products given twice, in any
    order, are refused: it is one industry series, and two would be written
    to the same file or to two files holding the same numbers."""
    out, seen = [], {}
    for item in items:
        names = [n.strip() for n in item.split("+")]
        if len(names) < 2 or len(set(names)) != len(names) or any(n not in books.PRODUCTS for n in names):
            raise ValueError("--industry-combined takes two or more products joined by +, from %s, "
                             "not %r" % (", ".join(books.PRODUCTS), item))
        key = frozenset(names)
        if key in seen:
            raise ValueError("--industry-combined gives %r and %r, the same products summed; give "
                             "each combination once" % (seen[key], item))
        seen[key] = item
        out.append(names)
    return out


# ---------------------------------------------------------------- pull

def pull(*, cache, first: str, last: str, products: Sequence[str], delinquency: bool,
         mergers_since: Optional[str], refresh: bool, say: Callable[[str], None] = print) -> dict:
    """Fetch the quarters not already cached (every one with ``refresh``);
    with ``delinquency``, the delinquency fields of the products too; with
    ``mergers_since`` (YYYY-MM-DD, or None for no merger record), the merger
    record into ``cache/mergers.json``.

    Everything stated is checked before the first request, so a typo in the
    mergers date never costs a whole pull before the refusal. A quarter
    already cached without a field now asked for (the delinquency fields, say)
    is refused by ``fdic.pull`` with that reason, never read as zeros.

    Returns ``{quarters, fetched, already, filers, fields, mergers,
    acquirers}``; ``mergers`` is the file written, or None."""
    _yes_no("--delinquency", delinquency)
    _yes_no("--refresh", refresh)
    products = _products(products)
    quarters = fdic.quarter_ends(first, last)
    if mergers_since:
        fdic.quarter_end(mergers_since)                     # refuses anything but YYYY-MM-DD
    fields = charge_off_fields(products)
    if delinquency:
        fields += [f for f in D.fields_for(products) if f not in fields]
    cache = Path(cache)
    before = {q for q in quarters if (cache / ("q%s.json" % q)).exists()}
    data = fdic.pull(quarters, fields, cache, refresh=refresh)
    fetched = len(quarters) if refresh else len(quarters) - len(before)
    say("Cache %s: %d quarters %s to %s, %d fetched, %d already there"
        % (cache, len(quarters), first, last, fetched, len(quarters) - fetched))
    if delinquency:
        say("With the delinquency and nonaccrual fields of %s" % ", ".join(products))
    filers = len(data[quarters[-1]])
    say("Filers in %s: %d" % (last, filers))
    path, acquirers = None, None
    if mergers_since:
        m = fdic.pull_mergers(mergers_since)
        path = cache / "mergers.json"
        path.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")
        acquirers = len(m)
        say("Wrote %s: %d acquirers since %s" % (path, acquirers, mergers_since))
    return dict(quarters=quarters, fetched=fetched, already=len(quarters) - fetched, filers=filers,
                fields=fields, mergers=path, acquirers=acquirers)


# ---------------------------------------------------------------- build

def _check_build(s):
    """Refuse a stated setting outside its range, before anything is read."""
    for flag, key, low in (("--jump", "jump", 0), ("--min-book", "min_book", 0),
                           ("--index-min-book", "index_min_book", 0)):
        at_least(flag, s[key], low)
    for flag, key, low in (("--min-banks", "min_banks", 1), ("--last-n", "last_n", 1),
                           ("--min-obs", "min_obs", 1), ("--lag-years", "lag_years", 0)):
        _whole(flag, s[key], low)
    _yes_no("--exempt-self", s["exempt_self"])
    _yes_no("--delinquency", s["delinquency"])
    if s["pack"] not in ("all", "regionals"):
        raise ValueError("--pack must be all or regionals, not %r" % (s["pack"],))
    if s["rank_by"] not in ("gross", "net"):
        raise ValueError("--rank-by must be gross or net, not %r" % (s["rank_by"],))
    for flag, key, n in (("--lagged-years", "lagged_years", None),
                         ("--normalisation-years", "normalisation_years", 2)):
        years = list(s[key])
        if not years or (n and len(years) != n):
            raise ValueError("%s needs %s year(s), not %r" % (flag, n or "one or more", s[key]))
        for y in years:
            _whole(flag, y, 0)
    _whole("--mix-base-year", s["mix_base_year"], 0)
    for flag, key in (("--extra-acquisitions", "extra_acquisitions"),
                      ("--industry-combined", "industry_combined")):
        if isinstance(s[key], str) or s[key] is None:
            raise ValueError("%s takes a list (empty to state there are none), not %r" % (flag, s[key]))
    return _products(s["products"])


def quarter_runs(labels):
    """'2024Q1, 2024Q2, 2024Q3, 2025Q1' -> '2024Q1 to 2024Q3, 2025Q1'."""
    def n(lbl):
        return int(lbl[:4]) * 4 + int(lbl[5]) - 1
    runs = []
    for q in labels:
        if runs and n(q) == n(runs[-1][1]) + 1:
            runs[-1][1] = q
        else:
            runs.append([q, q])
    return ", ".join(a if a == b else "%s to %s" % (a, b) for a, b in runs)


def left_out_note(left_out, tail, names):
    """The note line on a pack composite's four-quarter average naming, over
    the quarters written (``tail``), the banks left out of it because the jump
    blanked their own four-quarter average. ``left_out`` is ``{YYYYQn: [cert]}``
    (``composite_delinquency``'s ``avg4_left_out``), ``names`` ``{cert: label}``.
    Written either way, so what was left out is never hidden."""
    written = {q for q, _ in tail}
    by_bank = {}
    for q, certs in left_out.items():
        if q in written:
            for c in certs:
                by_bank.setdefault(c, []).append(q)
    if not by_bank:
        return "No bank was left out of this average by the jump in the quarters written."
    return ("Left out of this average because the jump blanked their own four-quarter average (the "
            "book moved by more than the jump, usually an acquisition): %s."
            % "; ".join("%s %s" % (names.get(c, c), quarter_runs(sorted(qs)))
                        for c, qs in by_bank.items()))


def _delinquency_series(data, roster, me, pack, pack_words, products, jump, min_book, exempt_self,
                        min_banks, source, every, out_dir):
    """Per product, measure and basis, the pack composite, the bank itself and
    the industry, as ``(path, rows, note, product, left_out)``: the delinquency
    CSVs. ``left_out`` is ``{YYYYQn: [cert]}`` for a pack composite's
    four-quarter average and None for every other file.

    The rules note says what each series was built under, and no more. The
    jump blanks a bank's own four-quarter average, and a bank so blanked is
    left out of the composite's four-quarter average for that quarter
    (``delinquency.composite_delinquency``), which names the banks."""
    exempt = ", %s exempt" % me["short"] if exempt_self else ""
    book = "{:,.0f}".format(min_book)
    rule = ("Rules: minimum book %s ($000), read against the quarter-end balance%s; the jump %g "
            "blanks a four-quarter average when the book moved by more than that in any of its last "
            "three quarters, and never a quarter-end rate, which is one filing's; at least %d banks "
            "in a composite." % (book, exempt, jump, min_banks))
    comp_rule = ("Rules: minimum book %s ($000), read against each bank's quarter-end balance%s; at "
                 "least %d banks in a composite. The jump %g never touches a quarter-end rate, which is "
                 "one filing per bank; the four-quarter average is the mean of four composite "
                 "quarter-end rates, each without the banks whose own four-quarter average the jump "
                 "blanked that quarter." % (book, exempt, min_banks, jump))
    certs = [b["cert"] for b in pack]
    made = []
    for p in products:
        balance = D.FIELDS[p][0]
        for m in D.MEASURES:
            nums = " + ".join(D._numerator_fields(p, m))
            banks_ = {b["cert"]: D.bank_delinquency(data, b["cert"], p, m, jump, min_book,
                                                    exempt_self and b is me) for b in roster}
            comp = D.composite_delinquency(banks_, certs, min_banks)
            for who, words, ruled, rows in (
                    ("pack-composite", "pack composite (%s): kept banks' numerators summed over their "
                     "balances summed" % pack_words, comp_rule, comp),
                    (slug(me["short"]), "%s (certificate %s), its own book" % (me["short"], me["cert"]),
                     rule, banks_[me["cert"]]),
                    ("industry", "industry: " + every, None, D.industry_delinquency(data, p, m))):
                for basis in D.BASES:
                    how = ("quarter-end rate: 100 x %s / %s, both from the same filing" % (nums, balance)
                           if basis == "quarter-end" else
                           "four-quarter average: the mean of the four quarter-end rates (100 x %s / %s) "
                           "of this quarter and the three before, only when all four exist" % (nums, balance))
                    note = ["%s, delinquency: %s, %s, %%." % (p, m, how),
                            "Amounts are $ thousands at quarter-end, as filed; a field not filed is "
                            "never read as 0.",
                            words[0].upper() + words[1:] + ".", source] + ([ruled] if ruled else [])
                    left_out = ({r["q"]: r["avg4_left_out"] for r in comp}
                                if rows is comp and basis == "four-quarter average" else None)
                    made.append((out_dir / ("%s_%s_delinquency-%s_%s.csv" % (slug(p), who, slug(m), slug(basis))),
                                 D.values(rows, basis), note, p, left_out))
    return made


def _commit(moves, removals, say):
    """Put a build's files in place all together, or not at all.

    ``moves`` is ``[(part, final)]``, each part already written in full, and
    ``removals`` the finals from an earlier run that this run has no value
    for. First every final that exists is moved aside to ``final.prev``; a
    file that cannot be moved (on Windows, one open in Excel) stops the
    build there, with what was moved aside put back, so the old workbook and
    the old series stay together. Then every part is moved into place; a
    failure there takes the new files out and puts the old ones back. Only
    then are the ``.prev`` files deleted. Returns the removals that existed
    and are now gone."""
    aside, placed = [], []

    def undo():
        stuck = []
        for f in placed:
            try:
                f.unlink()
            except OSError:
                stuck.append(f)
        for final, prev in reversed(aside):
            try:
                os.replace(str(prev), str(final))
            except OSError:
                stuck.append(final)
        return stuck

    step = None
    try:
        for final in [f for _, f in moves] + list(removals):
            if final.exists():
                step = final
                prev = final.with_name(final.name + ".prev")
                os.replace(str(final), str(prev))
                aside.append((final, prev))
        for part, final in moves:
            step = final
            os.replace(str(part), str(final))
            placed.append(final)
    except OSError as exc:
        stuck = undo()
        err = OSError("%s could not be replaced (%s); if it is open, in Excel say, close it and build "
                      "again. %s" % (step, exc.strerror or exc,
                                     "Nothing was changed." if not stuck else
                                     "These could not be put back as they were: %s"
                                     % ", ".join(str(f) for f in stuck)))
        # For the window, which names the file in its own words: which file
        # stopped the build, and what could not be put back (empty: nothing).
        err.not_replaced, err.stuck = step, stuck
        raise err from None
    gone = set()
    for final, prev in aside:
        try:
            prev.unlink()
        except OSError as exc:
            say("Could not delete %s, the earlier run's file (%s); delete it by hand" % (prev, exc))
        if final in removals:
            gone.add(final)
    return gone


def _check_out(out, *, roster, mergers) -> None:
    """Refuse a workbook path that would replace a file the build reads,
    before anything is read or written. It must be a .xlsx file: the series
    are .csv and the cache .json, so it can never be one of them, and it must
    not be the roster or the merger record, whatever they are named."""
    out = Path(out)
    if out.suffix.lower() != ".xlsx":
        raise ValueError("the peer workbook must be written to a .xlsx file, not %s" % out.name)
    for name, path in (("the roster", roster), ("the merger record", mergers)):
        if path is not None and out.resolve() == Path(path).resolve():
            raise ValueError("the peer workbook would be written over %s, %s; write it elsewhere"
                             % (name, Path(path).name))


def build(out, *, cache, roster, series_dir, first: str, last: str, products: Sequence[str],
          mergers, extra_acquisitions: Sequence[str], industry_combined: Sequence[str],
          jump: float, min_book: float, exempt_self: bool, pack: str, min_banks: int, rank_by: str,
          last_n: int, min_obs: int, base_quarter: str, index_min_book: float,
          lagged_years: Sequence[int], lag_years: int, normalisation_years: Sequence[int],
          mix_base_year: int, delinquency: bool, say: Callable[[str], None] = print) -> dict:
    """Read the cache, write the peer workbook and the series CSVs.

    ``mergers`` is the file 'peers pull --mergers' writes; ``extra_acquisitions``
    is ``CERT=YYYYQn`` items and ``industry_combined`` ``PRODUCT+PRODUCT``
    items, each an empty list to state there are none. ``delinquency`` True
    pulls the delinquency fields out of the cache too (refused, by field, if
    the cache was pulled without them), draws the Delinquency tabs, and writes
    per product, measure and basis the pack composite, the bank and the
    industry; False draws tabs that say it was not built and writes none.

    Every stated setting is checked before anything is read or written, and
    two series that would land in the same file are refused then too. The
    series are computed first; the workbook and the CSVs are written beside
    their final names and put in place together by ``_commit`` only once all
    of them are written: the earlier run's files are moved aside first, so a
    file that cannot be replaced (a workbook open in Excel) stops the build
    with every earlier file where it was. A refusal never leaves a new
    workbook beside an old or partial series set, nor the reverse. A series
    with no value this run has its CSV from an earlier run removed in the
    same step, since that file was built under other rules.

    Returns ``{out, info, series}``: the workbook written, what
    ``build_peers_workbook`` returned, and per series ``(path, quarters
    written, left out before, left out after)`` (0 quarters: not written)."""
    s = dict(locals())
    products = _check_build(s)
    _check_out(out, roster=roster, mergers=mergers)
    quarters = fdic.quarter_ends(first, last)
    roster_ = R.load(roster)
    me = R.self_bank(roster_)
    pack_ = R.peers(roster_) if pack == "all" else R.regionals(roster_)
    mergers_ = load_mergers(mergers)
    extras_ = extras(extra_acquisitions, roster_, quarters)
    combined_ = combined(industry_combined)

    cache = Path(cache)
    missing = [q for q in quarters if not (cache / ("q%s.json" % q)).exists()]
    if missing:
        raise ValueError("%s has no %d of the %d quarters asked for (first missing %s): run "
                         "'peers pull' first; build never fetches"
                         % (cache, len(missing), len(quarters), missing[0]))

    def no_fetch(url):
        raise ValueError("build reads the cache only and never fetches")
    fields = charge_off_fields(list(products) + [p for c in combined_ for p in c])
    if delinquency:
        fields += [f for f in D.fields_for(products) if f not in fields]
    data = fdic.pull(quarters, fields, cache, fetch=no_fetch)

    filers = len(data[quarters[-1]])
    ind = {p: books.industry(data, p) for p in products}
    rule = ("Rules: jump %g, minimum book %s ($000)%s, at least %d banks in a composite."
            % (jump, "{:,.0f}".format(min_book),
               ", %s exempt" % me["short"] if exempt_self else "", min_banks))
    source = "Source: FDIC BankFind financials, %s to %s, from the cache %s." % (first, last, cache)
    every = "every filer in the cache (%d in %s), no jump or minimum rule" % (filers, last)
    out_dir = Path(series_dir)
    pack_words = "all %d peers" % len(pack_) if pack == "all" else "%d regionals" % len(pack_)

    made = []                   # (product words, file slug, who, words, rules apply?, rows)
    for p in products:
        bks = {b["cert"]: books.bank_book(data, b["cert"], p, jump, min_book,
                                          exempt_min_book=exempt_self and b is me) for b in roster_}
        comp = books.composite(bks, [b["cert"] for b in pack_], min_banks)
        made += [
            (p, slug(p), "pack-composite",
             "pack composite (%s): kept flows over kept average balances" % pack_words, True, comp),
            (p, slug(p), slug(me["short"]),
             "%s (certificate %s), its own book" % (me["short"], me["cert"]), True, bks[me["cert"]]),
            (p, slug(p), "industry", "industry: " + every, False, ind[p]),
        ]
    for names in combined_:
        made.append((" plus ".join(names), slug(" ".join(names)), "industry",
                     "industry, %s summed: %s" % (" and ".join(names), every), False,
                     books.industry(data, names[0], names[1:])))

    series = []                 # (path, tail, note lines, left out before, left out after, group)
    for words_p, slug_, who, words, ruled, rows in made:
        for kind in ("gross", "net"):
            tail, before, after = unbroken_tail([(r["quarter"], r[kind + "_rate"]) for r in rows])
            note = ["%s, %s charge-off rate, trailing four quarters, %%." % (words_p, kind),
                    words[0].upper() + words[1:] + ".", source] + ([rule] if ruled else [])
            series.append((out_dir / ("%s_%s_%s.csv" % (slug_, who, kind)), tail,
                           series_note(note, tail, before, after), before, after, None))
    dq_spec = None
    if delinquency:
        names = {b["cert"]: "%s (%s)" % (b["short"], b["cert"]) for b in roster_}
        for path, rows, note, p, left_out in _delinquency_series(
                data, roster_, me, pack_, pack_words, products, jump, min_book, exempt_self,
                min_banks, source, every, out_dir):
            tail, before, after = unbroken_tail(rows)
            if left_out is not None and tail:
                note = note + [left_out_note(left_out, tail, names)]
            series.append((path, tail, series_note(note, tail, before, after), before, after, p))
        dq_spec = dict(data=data, products=list(products), jump=jump, min_book=min_book,
                       exempt_self=exempt_self, measure=START_MEASURE, basis=START_BASIS)

    paths = [str(path).lower() for path, *_ in series]
    twice = sorted({p for p in paths if paths.count(p) > 1})
    if twice:                   # combined() refuses the known cause; this is the backstop
        raise ValueError("two series would be written to the same file, %s; nothing is written"
                         % ", ".join(twice))

    out = Path(out)
    part_out = out.with_name(out.stem + ".part" + out.suffix)
    parts = []
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        info = peers_workbook.build_peers_workbook(
            part_out, data, roster_, products, jump, min_book, pack, mergers_, extras_,
            base_quarter, exempt_self=exempt_self, min_banks=min_banks, rank_by=rank_by,
            last_n=last_n, min_obs=min_obs, index_min_book=index_min_book,
            lagged_years=lagged_years, lag_years=lag_years,
            normalisation_years=normalisation_years, mix_base_year=mix_base_year,
            industry=ind, delinquency=dq_spec, cache_dir=cache, mergers_file=mergers,
            sources=["Read from the cache %s, %d quarter files %s to %s, built %s"
                     % (cache, len(quarters), quarters[0], quarters[-1],
                        dt.date.today().isoformat())])
        moves = [(part_out, out)]
        for path, tail, lines, _, _, _ in series:
            if tail:
                part = path.with_name(path.name + ".part")
                parts.append(part)
                books.write_series(tail, part, lines)
                moves.append((part, path))
        gone = _commit(moves, [path for path, tail, *_ in series if not tail], say)
        parts = []
    finally:
        for f in parts + [part_out]:
            if f.exists():
                f.unlink()

    say("Wrote %s: %s, %d TTM quarters, pack of %d"
        % (out, ", ".join(info["products"]), len(info["quarters"]), len(info["pack"])))
    written = {}                # delinquency: product -> [written, of, starting after a break]
    for path, tail, _, before, after, group in series:
        if group is not None:
            w = written.setdefault(group, [0, 0, 0])
            w[1] += 1
        if not tail:
            say("Not written: %s has no value%s"
                % (path.name, "; the file from an earlier run is removed" if path in gone else ""))
            continue
        if group is not None:
            written[group][0] += 1
            written[group][2] += bool(before)
            if not after:
                continue        # 150 files: counted below; what each leaves out is in its notes
        say("Wrote %s: %d quarters%s%s"
            % (path, len(tail), ", %d earlier left out at a break" % len(before) if before else "",
               ", ends %s: %d later quarter%s with no value"
               % (tail[-1][0], len(after), "" if len(after) == 1 else "s") if after else ""))
    for p, (n, of, broke) in written.items():
        say("Delinquency, %s: %d of %d series written to %s%s"
            % (p, n, of, out_dir, "; %d start after a break (a four-quarter average always does), "
               "the quarters left out named in each file's notes" % broke if broke else ""))
    return dict(out=out, info=info,
                series=[(path, len(tail), before, after) for path, tail, _, before, after, _ in series])
