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
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import books, fdic, peers_workbook
from . import delinquency as D
from . import flows as FL
from . import roster as R
from . import stated as ST
from .. import reporting_changes as RC
from ..series import left_out_line

#: The workbook's pickers start here; every measure and basis is built.
START_MEASURE = next(iter(D.MEASURES))
START_BASIS = next(iter(D.BASES))


def slug(text: str) -> str:
    """'Credit card' -> 'credit-card'; '90+ accruing' -> '90-plus-accruing'."""
    return re.sub(r"[^a-z0-9]+", "-", text.replace("+", " plus").lower()).strip("-")


def charge_off_fields(products: Sequence[str]) -> List[str]:
    """The balance, charge-off and recovery fields of the products named."""
    return books.raw_fields(f for p in products for f in books._fields(p))


def _products(products) -> List[str]:
    """Distinct product names, at least one: from ``books.PRODUCTS``, or
    combined (``books.members``)."""
    names = [products] if isinstance(products, str) else list(products or [])
    if not names or len(set(names)) != len(names) or not all(books.is_product(p) for p in names):
        raise ValueError("--products takes one or more distinct products from %s, %r, or two or more "
                         "joined by %r, not %r" % (", ".join(books.PRODUCTS), books.ALL, books.JOIN, products))
    return names


def _yes_no(flag, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be stated, yes or no, not %r" % (flag, value))


def unbroken_tail(rows, bridge=()):
    """The latest unbroken run of ``(quarter, value)`` pairs, the quarters
    before it that are left out, and the quarters after it that are left out.

    The workbook refuses a series with a gap, and a gap is never filled, so a
    series whose values break off (a quarter not kept) is written from the
    first quarter after its last break. A series whose latest quarters have no
    value ends at its last value. What is left out, at either end, is named,
    not hidden: unnamed, an older value would be read as the latest one.

    ``bridge`` names the quarters whose missing value does not break the run:
    the windows the jump left out only for a move in a quarter a reporting
    change names for the series (the firm, 17 Oct 2026, the commercial
    proposal's question 16; ``bridged``). An event never does. They stay in the run as
    ``(quarter, None)``, never filled: the file declares them on a
    ``left-out:`` line (``series_note``) and the readers take that gap and no
    other (``series.check``). The run never begins or ends on one. Every
    other quarter with no value breaks the run as before.
    """
    rows = list(rows)
    bridge = set(bridge)
    end = len(rows)
    while end and rows[end - 1][1] is None:
        end -= 1
    start = end
    while start and (rows[start - 1][1] is not None or rows[start - 1][0] in bridge):
        start -= 1
    while start < end and rows[start][1] is None:
        start += 1
    return rows[start:end], [q for q, _ in rows[:start]], [q for q, _ in rows[end:]]


def values(tail):
    """The quarters of ``tail`` (``unbroken_tail``'s) that hold a value: the
    quarters written. A quarter the series continues across holds None and
    is declared, not written."""
    return sum(v is not None for _, v in tail)


def labelled_for(entries, product, measure):
    """Every quarter (``YYYYQn``) an entry in ``entries`` names for
    ``product`` on ``measure`` (``reporting_changes.labelled_quarters``); for
    a combined product (``books.members``), an entry naming any of its parts,
    as the Peers charts mark a combined product's changes
    (``peers_workbook.change_quarters``) and its files note them."""
    return set().union(*(RC.labelled_quarters(entries, n, measure) for n in books.members(product)))


def bridged(rows, marks, *, jumped="jumped", without="why_without_jump", quarter="quarter"):
    """The quarters (``YYYYQn``) of ``rows`` (``books.bank_book``'s, or
    ``delinquency.bank_delinquency``'s with ``without="why_avg4_without_jump"``
    and ``quarter="q"``) left out by the jump alone, every move that tripped
    it in a quarter of ``marks`` (``labelled_for``): left out, and nothing
    else would have left them out."""
    return {r[quarter] for r in rows
            if r[jumped] and r[without] is None and set(r[jumped]) <= set(marks)}


def named_for(entries, product, measure, quarters_):
    """``(name, parts)`` for each entry in ``entries`` (the reporting changes,
    for a ``left-out:`` line) that names any of ``quarters_`` for ``product``
    on ``measure``, in registry order; ``parts`` are the products of
    ``product`` (``books.members``: itself, unless combined) it names."""
    qs, names = set(quarters_), books.members(product)
    return [(c["name"], [n for n in names if n in c["products"]]) for c in entries
            if set(names) & set(c["products"]) and measure in c["measures"]
            and qs & set(RC.quarters(c["first"], c["last"]))]


def break_reason(row, key: str, min_banks: int) -> str:
    """Why ``row`` has no value under ``key`` ("net_rate", "rate", "avg4"):
    its own stated reason where it has one (a bank's ``why``, or ``why_avg4``
    for a four-quarter average); for a composite, the banks it had against
    the banks needed; else "no value". ``row`` None: not in the data."""
    if row is None:
        return "not in the data"
    why = row.get("why_avg4" if key == "avg4" else "why")
    if why:
        return why
    if isinstance(row.get("banks"), int) and row["banks"] < min_banks:
        return "%d banks kept, fewer than the %d needed" % (row["banks"], min_banks)
    return "no value"


def left_out_spans(before, after, reasons) -> List[Tuple[str, str, str]]:
    """``(first, last, why)`` for each span ``unbroken_tail`` left out as
    built: the quarters before the last break, and the latest quarters with no
    value. ``reasons`` is ``{quarter: break_reason}``."""
    spans = []
    if before:
        spans.append((before[0], before[-1],
                       "before the last break: %s has no value (%s); a series is written from the first "
                       "quarter after its last break, because the workbook refuses a gap"
                       % (before[-1], reasons.get(before[-1], "no value"))))
    if after:
        spans.append((after[0], after[-1], "the latest quarters have no value: %s (%s)"
                       % (after[0], reasons.get(after[0], "no value"))))
    return spans


#: The reason the left-out file gives for quarters a series continues across.
WHY_WITHIN = ("within the series: the jump left these windows out and nothing else would have, every move that "
              "tripped it in a quarter a reporting change names; not written, never filled, and the series "
              "continues across them (the file's left-out line names the moves and the changes)")


def within_spans(tail) -> List[Tuple[str, str, str]]:
    """``(first, last, why)`` for each run of quarters with no value inside
    ``tail`` (``unbroken_tail``'s, with a ``bridge``): the windows a series
    continues across, for the left-out file beside ``left_out_spans``'."""
    spans, run_ = [], []
    for q, v in list(tail) + [(None, 0)]:
        if v is None:
            run_.append(q)
        elif run_:
            spans.append((run_[0], run_[-1], WHY_WITHIN))
            run_ = []
    return spans


def series_note(note, tail, before, after, why_gap=None):
    """The note lines for a series written from ``tail``: the given note, then
    what is left out before the run and after it, and, where the run holds
    quarters with no value (``unbroken_tail``'s ``bridge``), the ``left-out:``
    line declaring them, with ``why_gap``, the reason in words. An empty
    ``tail`` is not written, so it has no note."""
    if not tail:
        return []
    lines = list(note)
    gaps = [q for q, v in tail if v is None]
    if gaps:
        if not why_gap:
            raise ValueError("a series continuing across quarters left out must say why")
        lines.append(left_out_line(gaps, why_gap))
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


#: The command that writes a merger record that states the date it starts
#: from (the firm, 18 Oct 2026, question 22); named in every refusal of one
#: that does not.
REPULL = ("'peers pull --cache DIR --first YYYYQn --last YYYYQn --products ... --delinquency yes|no "
          "--mergers SINCE', SINCE on or before the first day of the build's first quarter")


def quarter_start(first: str) -> str:
    """The first day (``YYYY-MM-DD``) of a quarter written ``YYYYQn``,
    ``YYYYMMDD`` or as an ISO date."""
    end = books.quarter_end(first)
    return "%s-%02d-01" % (end[:4], int(end[5:7]) - 2)


def _dated(path, key: str, what: str, again: str):
    """``(since, body)`` from a merger or absorption file that records the
    date it starts from, ``{"since": YYYY-MM-DD, key: body}``. A file without
    it (the format before 18 Oct 2026) is refused with the command to pull
    it again, ``again``."""
    try:
        got = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("%s is not valid JSON: %s" % (path, exc)) from None
    if not (isinstance(got, dict) and "since" in got):
        raise ValueError("%s does not record the date %s starts from, so whether it reaches back to the first "
                         "quarter cannot be checked (a file written before 18 Oct 2026). Pull it again: %s"
                         % (path, what, again))
    if set(got) != {"since", key} or not fdic._is_date(got["since"]):
        raise ValueError("%s must hold {\"since\": a date written like 2005-10-01, \"%s\": ...}, as the pull "
                         "writes it, not keys %s with since %r; pull it again: %s"
                         % (path, key, sorted(got), got.get("since"), again))
    return got["since"], got[key]


def reaches_back(path, since: str, first: str, what: str, again: str) -> None:
    """Refuse a record that starts after the first day of ``first``: an
    acquisition between the two would be invisible to it, its quarters
    neither left out nor added pro forma (the firm, 18 Oct 2026, question
    22: "A build stops if its merger list does not reach back as far as the
    history"). Names both dates."""
    start = quarter_start(first)
    if start < since:
        raise ValueError("the first quarter, %s, starts on %s, before %s (%s) starts, on %s: an acquisition "
                         "between the two would not be seen. Pull it again from %s or earlier (%s), or start "
                         "at a quarter beginning on or after %s"
                         % (books.label(books.quarter_end(first).replace("-", "")), start, what, Path(path).name,
                            since, start, again, since))


def load_mergers(path, first: str):
    """``{cert: [quarter-end dates]}`` from the --mergers file, every date
    checked here, so a bad file is refused by name rather than failing later.
    The file is ``{"since": YYYY-MM-DD, "acquirers": {cert: [...]}}`` as
    'peers pull --mergers' writes it; one without ``since`` is refused with
    the command to pull it again, and so is one whose ``since`` is after the
    first day of ``first`` (``reaches_back``)."""
    since, mergers = _dated(path, "acquirers", "the merger record", REPULL)
    reaches_back(path, since, first, "the merger record", REPULL)
    if not isinstance(mergers, dict):
        raise ValueError("%s: acquirers must be {cert: [quarter-end dates]}" % path)
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


def load_absorptions(path, first: str, *, again: str):
    """``[{acquirer, absorbed, quarter}]`` from the file 'peers pull --mergers'
    writes beside the merger record (``read_absorptions``), refused, like the
    merger record (``load_mergers``), when its ``since`` is after the first
    day of ``first`` (question 22). ``again`` is the command that writes it
    ('internal pull' writes its own)."""
    since, links = read_absorptions(path, again=again)
    reaches_back(path, since, first, "the absorptions record", again)
    return links


def read_absorptions(path, *, again: str):
    """``(since, [{acquirer, absorbed, quarter}])`` from an absorptions file,
    every row checked here, so a bad file is refused by name rather than
    failing later. The file is ``{"since": YYYY-MM-DD, "absorptions":
    [...]}``; one without ``since`` is refused with the command that writes
    it, ``again``. Whether it reaches back is not checked here: the caller
    decides (``load_absorptions``; 'peers industry-long' reads a record that
    starts later than its history on purpose, and says so)."""
    since, links = _dated(path, "absorptions", "the absorptions record", again)
    if not isinstance(links, list):
        raise ValueError("%s: absorptions must be [{acquirer, absorbed, quarter}]" % path)
    for ln in links:
        ok = (isinstance(ln, dict) and set(ln) == {"acquirer", "absorbed", "quarter"}
              and all(isinstance(ln[k], str) and ln[k].isdigit() for k in ("acquirer", "absorbed")))
        if ok:
            try:
                books.quarter_end(ln["quarter"])
            except ValueError:
                ok = False
        if not ok:
            raise ValueError("%s: %r is not {acquirer, absorbed, quarter}" % (path, ln))
    return since, links


#: The FDIC institutions record, as 'peers pull --mergers' writes it into the
#: cache: each institution's establishment date (the firm, 18 Oct 2026,
#: question 21). The build reads it from the cache and never fetches it.
INSTITUTIONS = "institutions.json"


def write_institutions(cache, fetch=None, say: Callable[[str], None] = print) -> Path:
    """Pull the FDIC institutions record (``fdic.institutions``) and write
    ``cache/institutions.json``: ``{source, fields, pulled, rows,
    established: {cert: {name, established}}, undated: {cert: {name,
    established}}}``. ``established`` dates are ``YYYY-MM-DD``; ``undated``
    keeps the rows whose date is not a real one, as the FDIC gave it. Written
    through a temporary file, so a failed pull leaves the last file whole."""
    rows = fdic.institutions(fetch)
    if not rows:
        raise RuntimeError("the FDIC returned no institutions: the record is not there. Nothing was written; "
                           "pull again later")
    dated, undated = fdic.established(rows)
    path = Path(cache) / INSTITUTIONS
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps({"source": fdic.INSTITUTIONS_URL, "fields": fdic.INSTITUTION_FIELDS,
                               "pulled": dt.date.today().isoformat(), "rows": len(rows),
                               "established": dated, "undated": undated}, indent=1, sort_keys=True),
                   encoding="utf-8")
    os.replace(str(tmp), str(path))
    say("Wrote %s: %d institutions, %d with an establishment date, %d without one (kept as given)"
        % (path, len(rows), len(dated), len(undated)))
    return path


def load_institutions(path) -> dict:
    """``cache/institutions.json``, as :func:`write_institutions` writes it,
    checked here, so a bad file is refused by name rather than failing later."""
    try:
        got = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("%s is not valid JSON: %s" % (path, exc)) from None
    keys = {"source", "fields", "pulled", "rows", "established", "undated"}
    if not isinstance(got, dict) or set(got) != keys:
        raise ValueError("%s must hold {%s}, as 'peers pull --mergers' writes it; pull the merger record "
                         "again" % (path, ", ".join(sorted(keys))))
    # 'pulled' decides whether a member the record lacks could have been in
    # it (opened_members); a value that is not a date would compare as text
    # and pass or fail that check by accident. 'rows' is printed as a count.
    if not (isinstance(got["pulled"], str) and fdic._is_date(got["pulled"])):
        raise ValueError("%s: pulled is %r, which is not a date written like 2026-10-18; it says whether a bank "
                         "the record lacks could have been in it. Pull the merger record again"
                         % (path, got["pulled"]))
    if isinstance(got["rows"], bool) or not isinstance(got["rows"], int) or got["rows"] < 1:
        raise ValueError("%s: rows is %r, which is not a count of institutions (a whole number, at least 1: the "
                         "pull refuses an empty record). Pull the merger record again" % (path, got["rows"]))
    for key in ("established", "undated"):
        if not isinstance(got[key], dict):
            raise ValueError("%s: %s must be {certificate: {name, established}}" % (path, key))
        for cert, v in got[key].items():
            if not (cert.isdigit() and isinstance(v, dict) and set(v) == {"name", "established"}):
                raise ValueError("%s: %s, certificate %r: %r is not {name, established}" % (path, key, cert, v))
    for cert, v in got["established"].items():
        if not fdic._is_date(v["established"]):
            raise ValueError("%s: certificate %s has %r, which is not a date written like 1991-06-07"
                             % (path, cert, v["established"]))
    return got


def opened_members(cache, members: Dict[str, Sequence[Tuple[str, str]]], data,
                   names: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str], Optional[dict]]:
    """The firm, 18 Oct 2026, question 21: a bank added pro forma whose first
    filing falls partway through a year counts it as that quarter's activity
    when the FDIC institutions record shows it opened in that quarter;
    otherwise that quarter stays missing.

    Returns ``(firsts, opened, record)``: ``firsts`` ``{member: YYYYMMDD}``
    (``books.first_filings``, over every roster bank's ``members``),
    ``opened`` the ones whose establishment date is in that quarter
    (``books.opened_in_first_quarter``), and the institutions record read
    (None when no member needed it). The record is the cache's
    ``institutions.json``; the build never fetches it. Refused, naming each
    bank and the roster bank whose history it is in: a cache without the
    file, and a member the file does not hold when the file was pulled
    before that member's first filing quarter ended, so it could not have
    held it. A member the record does not hold although pulled after that
    (the FDIC has no row for it), or holds without a date, is not shown to
    have opened then: its quarter stays missing, and the Run tab names it
    (``opened_lines``)."""
    firsts: Dict[str, str] = {}
    owner: Dict[str, List[str]] = {}
    for c, mem in members.items():
        for b, q in books.first_filings(data, mem).items():
            firsts[b] = q
            owner.setdefault(b, []).append(c)
    if not firsts:
        return {}, {}, None

    def who(certs):
        return "; ".join("certificate %s (first filed %s, in %s's history)" % (
            b, books.label(firsts[b]), " and ".join(names.get(c, c) for c in owner[b])) for b in certs)
    path = Path(cache) / INSTITUTIONS
    again = ("Pull the merger record again ('peers pull --cache %s ... --mergers SINCE'), which writes it "
             "beside the merger record; build never fetches" % cache)
    if not path.exists():
        raise ValueError("pro forma needs the date each of these banks opened, since each first filed partway "
                         "through a year (a new charter's first filing counts as that quarter's activity: the "
                         "firm, 18 Oct 2026, question 21), and %s is not there: %s. %s"
                         % (path, who(sorted(firsts)), again))
    record = load_institutions(path)
    held = set(record["established"]) | set(record["undated"])
    stale = sorted(b for b in firsts if b not in held and record["pulled"] <= books.quarter_end(firsts[b]))
    if stale:
        raise ValueError("%s was pulled on %s, before the end of the quarter in which each of these banks added "
                         "pro forma first filed, so it cannot say whether they opened then: %s. %s"
                         % (path, record["pulled"], who(stale), again))
    dates = {c: v["established"] for c, v in record["established"].items()}
    return firsts, books.opened_in_first_quarter(firsts, dates), record


def opened_lines(firsts: Dict[str, str], opened: Dict[str, str], record: Optional[dict],
                 combo: Dict[str, dict], names: Dict[str, str]) -> List[str]:
    """The Run tab's lines on question 21: per roster bank, the banks added
    pro forma whose first filing falls partway through a year, those counted
    as that quarter's activity (opened then, per the FDIC record) and those
    not: opened in another quarter, or not in the record, or in it without a
    date (that quarter has no flow, so the windows holding it are missing)."""
    if not firsts:
        return []
    est, undated = record["established"], record["undated"]
    lines = ["A bank added pro forma whose first filing falls partway through a year: its first year to date "
             "counts as that quarter's activity where the FDIC institutions record (%s, pulled %s, %d "
             "institutions) shows it opened in that quarter; otherwise that quarter has no flow and the windows "
             "holding it are missing (the firm, 18 Oct 2026, question 21)."
             % (INSTITUTIONS, record["pulled"], record["rows"])]
    for cert, v in combo.items():
        mine = [b for b, _ in v["members"] if b in firsts]
        if not mine:
            continue
        def one(b):
            return "%s (certificate %s), first filed %s, opened %s" % (
                est[b]["name"], b, books.label(firsts[b]), est[b]["established"])
        groups = (
            ("counted", [one(b) for b in mine if b in opened]),
            ("not counted, opened in another quarter",
             [one(b) for b in mine if b in est and b not in opened]),
            ("not counted, the record gives no date",
             ["%s (certificate %s), first filed %s, the record's date %r" % (
                 undated[b]["name"], b, books.label(firsts[b]), undated[b]["established"])
              for b in mine if b in undated]),
            ("not counted, not in the record",
             ["certificate %s, first filed %s" % (b, books.label(firsts[b]))
              for b in mine if b not in est and b not in undated]))
        for words, items in groups:
            if items:
                lines.append("First filing %s, %s: %d bank%s: %s." % (
                    words, names.get(cert, cert), len(items), "" if len(items) == 1 else "s", "; ".join(items)))
    return lines


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
    record into ``cache/mergers.json``, who absorbed whom into
    ``cache/absorptions.json`` and the FDIC institutions record, each
    institution's establishment date, into ``cache/institutions.json``
    (``write_institutions``; question 21). Every quarter carries each filer's parent
    (``books.PARENT``), which says whether an absorption was under common
    control.

    Everything stated is checked before the first request, so a typo in the
    mergers date never costs a whole pull before the refusal. A quarter
    already cached without a field now asked for (the delinquency fields, say)
    is refused by ``fdic.pull`` with that reason, never read as zeros.

    Returns ``{quarters, fetched, already, filers, fields, mergers,
    acquirers, absorptions}``; ``mergers`` and ``absorptions`` are the files
    written, or None."""
    _yes_no("--delinquency", delinquency)
    _yes_no("--refresh", refresh)
    products = _products(products)
    quarters = fdic.quarter_ends(first, last)
    if mergers_since:
        fdic.quarter_end(mergers_since)                     # refuses anything but YYYY-MM-DD
    fields = charge_off_fields(products) + [books.PARENT]
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
    path, acquirers, links_path = None, None, None
    if mergers_since:
        rows = fdic.history(mergers_since)
        m = fdic.classify(rows)
        path = cache / "mergers.json"
        # Question 22 (the firm, 18 Oct 2026): each record states the date it
        # starts from, so a build can refuse one that does not reach back.
        path.write_text(json.dumps({"since": mergers_since, "acquirers": m}, indent=1, sort_keys=True),
                        encoding="utf-8")
        acquirers = len(m)
        say("Wrote %s: %d acquirers since %s" % (path, acquirers, mergers_since))
        links = fdic.absorptions(rows)
        links_path = cache / "absorptions.json"
        links_path.write_text(json.dumps({"since": mergers_since, "absorptions": links}, indent=1),
                              encoding="utf-8")
        say("Wrote %s: %d absorptions since %s (who took in whom)"
            % (links_path, len(links), mergers_since))
        write_institutions(cache, say=say)
    return dict(quarters=quarters, fetched=fetched, already=len(quarters) - fetched, filers=filers,
                fields=fields, mergers=path, acquirers=acquirers, absorptions=links_path)


# ---------------------------------------------------------------- build

def pro_forma_lines(pro_forma: bool, combo: Dict[str, dict], names: Dict[str, str]) -> List[str]:
    """The Run tab's lines on pro forma: whether it is on, each roster bank's
    banks added in (certificate and the quarter it was absorbed), and each
    absorption that could not be added because the absorbed bank never filed
    in these quarters."""
    if not pro_forma:
        return ["Pro forma: no. Each bank's charge-offs and balances are its own filings alone; a quarter "
                "whose four-quarter window holds an acquisition of at least the acquisition share is left out."]
    lines = ["Pro forma: yes. Each bank's charge-offs and balances include those of every bank it absorbed, "
             "in the quarters before the absorption, from that bank's own filings. Delinquency is each bank "
             "as filed."]
    for cert, v in combo.items():
        who = names.get(cert, cert)
        if v["members"]:
            lines.append("Pro forma, %s: %d bank%s added in: %s." % (
                who, len(v["members"]), "" if len(v["members"]) == 1 else "s",
                ", ".join("certificate %s to %s" % (b, books.label(u)) for b, u in v["members"])))
        if v["uncombined"]:
            lines.append("Pro forma, %s: not added, no filing in these quarters: %s. Their acquisitions are "
                         "treated as without pro forma." % (
                             who, ", ".join("certificate %s (%s)" % (b, books.label(q)) for b, q in v["uncombined"])))
    return lines


def _check_build(s):
    """Refuse a stated setting outside its range, before anything is read."""
    for flag, key, low in (("--jump", "jump", 0), ("--min-book", "min_book", 0),
                           ("--index-min-book", "index_min_book", 0),
                           ("--acquisition-share", "acquisition_share", 0)):
        at_least(flag, s[key], low)
    for flag, key, low in (("--min-banks", "min_banks", 1), ("--last-n", "last_n", 1),
                           ("--min-obs", "min_obs", 1), ("--lag-years", "lag_years", 0)):
        _whole(flag, s[key], low)
    _yes_no("--exempt-self", s["exempt_self"])
    _yes_no("--pro-forma", s["pro_forma"])
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
    the quarters written (``tail``), the banks left out of it and why: their
    own four-quarter average was blanked by the jump or by the acquisition
    share. ``left_out`` is ``{YYYYQn: [(cert, reason)]}``, the reason "the
    jump", "the acquisition share" or "a stated acquisition" (``composite_delinquency``'s
    ``avg4_left_out`` with each bank's own ``why_avg4``), ``names`` ``{cert:
    label}``. Written either way, so what was left out is never hidden."""
    written = {q for q, _ in tail}
    by_bank = {}
    for q, items in left_out.items():
        if q in written:
            for c, why in items:
                by_bank.setdefault((why, c), []).append(q)
    if not by_bank:
        return ("No bank was left out of this average by the jump, the acquisition share or a stated "
                "acquisition in the quarters written.")
    parts_ = []
    for why in ("the jump", "the acquisition share", "a stated acquisition"):
        banks = [(c, qs) for (w, c), qs in by_bank.items() if w == why]
        if banks:
            parts_.append("blanked by %s (%s): %s" % (
                why, "the book moved by more than the jump" if why == "the jump" else
                "recorded acquisitions brought in at least that share of the book"
                if why == "the acquisition share" else
                "an acquisition the FDIC record cannot see, listed with its filing",
                "; ".join("%s %s" % (names.get(c, c), quarter_runs(sorted(qs))) for c, qs in banks)))
    return "Left out of this average because their own four-quarter average was " + "; and ".join(parts_) + "."


def stated_note(file, in_range: Sequence[dict], product: str, names: Dict[str, str]) -> str:
    """The line every series file of ``product`` the rules apply to carries:
    the stated acquisitions in its quarters that brought it, each with its
    citation and where its list of products comes from, and those that did
    not, which leave nothing out of it (the firm, 18 Oct 2026, question 18).
    ``file`` is the stated acquisitions file, or None when none is read."""
    head = "Stated acquisitions, the ones the FDIC record cannot see (%s): " % (
        Path(file).name if file is not None else "none read")
    if file is None:
        return head + "none named, so none is read."
    if not in_range:
        return head + "none in these quarters."
    told = [e for e in in_range if ST.touches(e, product)]
    other = [e for e in in_range if not ST.touches(e, product)]
    rest = "; ".join("%s %s (it brought %s)" % (names[e["acquirer"]], e["quarter"], ", ".join(e["products"]))
                     for e in other)
    if not told:
        return head + "none of the %d in these quarters brought %s, so nothing is left out for them: %s." % (
            len(in_range), product, rest)
    said = "%d of the %d in these quarters brought %s, so each bank's windows holding one are left out: " % (
        len(told), len(in_range), product)
    said += "; ".join("%s %s (%s; products: %s%s)" % (
        names[e["acquirer"]], e["quarter"], e["citation"], e["products_source"],
        "; listed because the source does not settle them: %s" % ", ".join(e["products_unsettled"])
        if e["products_unsettled"] else "") for e in told)
    if other:
        said += ". The rest did not bring %s, so nothing is left out for them: %s" % (product, rest)
    return head + said + "."


def _delinquency_series(data, roster, me, pack, pack_words, products, jump, min_book, exempt_self,
                        min_banks, source, every, out_dir, acquired, acquisition_share, stated, stated_notes,
                        bridging):
    """Per product, measure and basis, the pack composite, the bank itself and
    the industry, as ``(path, rows, note, product, measure, left_out, bridge, reasons)``: the delinquency
    CSVs. ``left_out`` is ``{YYYYQn: [cert]}`` for a pack composite's
    four-quarter average and None for every other file. ``every`` words
    the industry from how many filers its last quarter counts (``banks``).
    ``stated`` is ``{product: {cert: [YYYYMMDD]}}``, the stated acquisitions
    in these quarters that brought each product (``peers.stated.for_product``),
    and ``stated_notes`` ``{product: the line naming them}``, given to every
    file of that product the rules apply to. ``bridge`` is ``{YYYYQn:
    [quarters that moved]}``, the bank's own four-quarter average quarters
    left out by the jump alone, for a move in a quarter a reporting change
    in ``bridging`` names for the product and measure (``bridged``; never an
    event); empty for every other file. ``reasons`` is ``{YYYYQn: why no
    value}`` (``break_reason``), for the left-out file.

    The rules note says what each series was built under, and no more. The
    jump blanks a bank's own four-quarter average, and a bank so blanked is
    left out of the composite's four-quarter average for that quarter
    (``delinquency.composite_delinquency``), which names the banks."""
    exempt = ", %s exempt" % me["short"] if exempt_self else ""
    book = "{:,.0f}".format(min_book)
    rule = ("Rules: minimum book %s ($000), read against the quarter-end balance%s; the jump %g "
            "blanks a four-quarter average when the book moved by more than that in any of its last "
            "three quarters, and so does an acquisition bringing in %g of the book or more, never a "
            "quarter-end rate, which is one filing's; at least %d banks in a composite."
            % (book, exempt, jump, acquisition_share, min_banks))
    comp_rule = ("Rules: minimum book %s ($000), read against each bank's quarter-end balance%s; at "
                 "least %d banks in a composite. The jump %g never touches a quarter-end rate, which is "
                 "one filing per bank; the four-quarter average is the mean of four composite "
                 "quarter-end rates, each without the banks whose own four-quarter average the jump "
                 "or the acquisition share (%g) blanked that quarter." % (book, exempt, min_banks, jump,
                                                                          acquisition_share))
    certs = [b["cert"] for b in pack]
    made = []
    for p in products:
        balance = D._fields(p)[0]
        balance = "(%s)" % " + ".join(books.parts(balance)) if "+" in balance else balance
        for m in D.MEASURES:
            nums = " + ".join(f for n in D._numerator_fields(p, m) for f in books.parts(n))
            banks_ = {b["cert"]: D.bank_delinquency(data, b["cert"], p, m, jump, min_book,
                                                    exempt_self and b is me,
                                                    acquired=acquired[p].get(b["cert"], []),
                                                    stated=stated[p].get(b["cert"], []))
                      for b in roster}
            own_bridge = bridged(banks_[me["cert"]], labelled_for(bridging, p, m),
                                 without="why_avg4_without_jump", quarter="q")
            comp = D.composite_delinquency(banks_, certs, min_banks)
            mid = {b_: D.band_delinquency(banks_, certs, b_, (50,), min_banks=min_banks) for b_ in D.BASES}
            median = [{"q": a["q"], D.BASES["quarter-end"]: a["p50"],
                       D.BASES["four-quarter average"]: f["p50"]}
                      for a, f in zip(mid["quarter-end"], mid["four-quarter average"])]
            ind = D.industry_delinquency(data, p, m)
            for who, words, ruled, rows in (
                    ("pack-composite", "pack composite (%s): kept banks' numerators summed over their "
                     "balances summed" % pack_words, comp_rule, comp),
                    ("pack-median", "pack median (%s): the middle bank's rate, each bank counted once "
                     "whatever its size, under each bank's own rules" % pack_words, rule, median),
                    (slug(me["short"]), "%s (certificate %s), its own book" % (me["short"], me["cert"]),
                     rule, banks_[me["cert"]]),
                    ("industry", "industry: " + every(ind[-1]["banks"] if ind else 0), None, ind)):
                for basis in D.BASES:
                    how = ("quarter-end rate: 100 x %s / %s, both from the same filing" % (nums, balance)
                           if basis == "quarter-end" else
                           "four-quarter average: the mean of the four quarter-end rates (100 x %s / %s) "
                           "of this quarter and the three before, only when all four exist" % (nums, balance))
                    note = ["%s, delinquency: %s, %s, %%." % (p, m, how),
                            "Amounts are $ thousands at quarter-end, as filed; a field not filed is "
                            "never read as 0.",
                            words[0].upper() + words[1:] + ".", source] + ([ruled, stated_notes[p]] if ruled else [])
                    note += D.comparability(p, m)
                    if p not in books.PRODUCTS:
                        note += books.definitions(p)[:1] + [D.COMBINED]
                    for n in books.members(p):
                        said = D.DEFINITIONS.get(n, books.DEFINITIONS.get(n))
                        note += [said] if said else []
                    own = {c: {x["q"]: x["why_avg4"] or "" for x in banks_[c]} for c in certs}
                    left_out = ({r["q"]: [(c, "the jump" if own[c].get(r["q"], "").startswith(D.WHY_JUMP_PREFIX)
                                           else "a stated acquisition"
                                           if own[c].get(r["q"], "").startswith(D.WHY_STATED_PREFIX)
                                           else "the acquisition share") for c in r["avg4_left_out"]]
                                 for r in comp}
                                if rows is comp and basis == "four-quarter average" else None)
                    bridge = ({r["q"]: r["jumped"] for r in banks_[me["cert"]] if r["q"] in own_bridge}
                              if rows is banks_[me["cert"]] and basis == "four-quarter average" else {})
                    made.append((out_dir / ("%s_%s_delinquency-%s_%s.csv" % (slug(p), who, slug(m), slug(basis))),
                                 D.values(rows, basis), note, p, m, left_out, bridge,
                                 {r["q"]: break_reason(r, D.BASES[basis], min_banks) for r in rows}))
    return made


def _flow_series(data, roster, me, pack, pack_words, products, jump, acquisition_share, min_banks, source, every,
                 out_dir, acquired, stated, stated_notes):
    """The 30+ to charge-off series files (``flows``), per product: the pack
    composite, the bank itself and the industry, each on both bases, and the
    bank's gap to the peer group and to the industry (four-quarter average).
    Each is ``(path, rows, note, product, measure, reasons)``, ``reasons``
    ``{quarter: why no value}`` for the left-out file. ``stated`` is
    ``{product: {cert: [YYYYMMDD]}}``, the stated acquisitions in these
    quarters that brought each product (``peers.stated.for_product``), applied
    as the acquisition quarters are, and ``stated_notes`` ``{product: the line
    naming them}``, given to every file of that product the rules apply to."""
    rule = ("Rules: each bank's own filings (not pro forma); jump %g, acquisition share %g and the stated "
            "acquisitions, applied to the two quarters after the quarter-end (a sale, purchase or acquisition "
            "there moves the charge-offs against the stock); at least %d banks in the composite. The industry "
            "has no jump, acquisition or minimum rule."
            % (jump, acquisition_share, min_banks))
    certs = [b["cert"] for b in pack]
    made = []
    for p in products:
        banks_ = {b["cert"]: FL.bank_flow(data, b["cert"], p, jump, acquired=acquired[p].get(b["cert"], []),
                                          stated=stated[p].get(b["cert"], []))
                  for b in roster}
        comp = FL.composite(banks_, certs, min_banks)
        ind = FL.industry(data, p)
        mine = banks_[me["cert"]]
        n_ind = next((r["banks"] for r in reversed(ind) if r["kept"]), 0)
        for who, words, rows in (
                ("pack-composite", "pack composite (%s): the kept banks' dollars charged off summed over their "
                                   "delinquent dollars summed" % pack_words, comp),
                (slug(me["short"]), "%s (certificate %s), its own book" % (me["short"], me["cert"]), mine),
                ("industry", "industry: " + every(n_ind), ind)):
            for basis in D.BASES:
                key = D.BASES[basis]
                note = ["%s, %s, %s, %%." % (p, FL.MEASURE, basis), FL.DEFINITION]
                if basis == "four-quarter average":
                    note.append(FL.DEFINITION_AVG4)
                note += [words[0].upper() + words[1:] + ".", source, rule, stated_notes[p]] + books.definitions(p)
                reasons = {r["q"]: (r["why_avg4"] if key == "avg4" else r["why"]) or "no value" for r in rows}
                made.append((out_dir / ("%s_%s_%s_%s.csv" % (slug(p), who, FL.SLUG, slug(basis))),
                             FL.values(rows, basis), note, p, FL.MEASURE, reasons))
        for other, meas, words in ((comp, FL.GAP_PEERS, "the peer group (%s)" % pack_words),
                                   (ind, FL.GAP_INDUSTRY, "the industry (every filer)")):
            g = FL.gap(mine, other)
            note = ["%s, %s, four-quarter average, percentage points." % (p, meas),
                    FL.DEFINITION_GAP % (meas, me["short"], words, me["short"], words), FL.DEFINITION,
                    FL.DEFINITION_AVG4, source, rule, stated_notes[p]] + books.definitions(p)
            made.append((out_dir / ("%s_%s_%s_four-quarter-average.csv" % (slug(p), slug(me["short"]), slug(meas))),
                         FL.values(g, "four-quarter average"), note, p, meas,
                         {r["q"]: r["why"] or "no value" for r in g}))
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


def _check_out(out, *, roster, mergers, absorptions=None) -> None:
    """Refuse a workbook path that would replace a file the build reads,
    before anything is read or written. It must be a .xlsx file: the series
    are .csv and the cache .json, so it can never be one of them, and it must
    not be the roster or the merger record, whatever they are named."""
    out = Path(out)
    if out.suffix.lower() != ".xlsx":
        raise ValueError("the peer workbook must be written to a .xlsx file, not %s" % out.name)
    for name, path in (("the roster", roster), ("the merger record", mergers),
                       ("the absorptions", absorptions)):
        if path is not None and out.resolve() == Path(path).resolve():
            raise ValueError("the peer workbook would be written over %s, %s; write it elsewhere"
                             % (name, Path(path).name))


def build(out, *, cache, roster, series_dir, first: str, last: str, products: Sequence[str],
          mergers, absorptions, extra_acquisitions: Sequence[str], industry_combined: Sequence[str],
          jump: float, acquisition_share: float, min_book: float, exempt_self: bool, pro_forma: bool,
          pack: str, min_banks: int, rank_by: str,
          last_n: int, min_obs: int, base_quarter: str, index_min_book: float,
          lagged_years: Sequence[int], lag_years: int, normalisation_years: Sequence[int],
          mix_base_year: int, delinquency: bool, reporting_changes, stated_acquisitions,
          say: Callable[[str], None] = print, into=None, names: Optional[Dict[str, str]] = None,
          book_kind: Optional[str] = None) -> dict:
    """Read the cache, write the peer workbook and the series CSVs.

    ``book_kind`` is the kind a book states (``kinds.KINDS``), given by the
    book command; the standalone command states none (``build_peers_workbook``).

    ``mergers`` and ``absorptions`` are the files 'peers pull --mergers'
    writes. Each records the date it starts from, and a build whose first
    quarter begins before it is refused, naming both (the firm, 18 Oct 2026,
    question 22), as is a file written before that date was recorded. ``acquisition_share`` (0.05 = 5%) is the share of a product's
    book an acquisition quarter must bring in for the windows holding it to
    be left out (``books.acquired_quarters``), the firm's judgement. In a
    survivor's merger quarter under common control, the absorbed bank's
    year-to-date is taken off the survivor's (``books.repeated_ytd``), for
    every series, the industry's included. ``pro_forma`` True adds to each
    roster bank's charge-offs and balances those of every bank it absorbed
    (``books.combination``), quarter by quarter before the absorption, so an
    acquisition neither breaks its history nor leaves it out; the acquisition
    share then applies only to an absorbed bank with no filing to add. The
    jump still applies. Delinquency is each bank as filed either way.
    ``extra_acquisitions``
    is ``CERT=YYYYQn`` items and ``industry_combined`` ``PRODUCT+PRODUCT``
    items, each an empty list to state there are none. ``delinquency`` True
    pulls the delinquency fields out of the cache too (refused, by field, if
    the cache was pulled without them), draws the delinquency view, and writes
    per product, measure and basis the pack composite, the bank and the
    industry; False draws tabs that say it was not built and writes none.

    ``reporting_changes`` is the registry of Call Report changes
    (``config/reporting-changes.json``, ``reporting_changes.py``): every
    series file carries a ``reporting-change`` note for each change that
    touches its product and measure within its quarters (the firm, 16 Oct
    2026: "Definitely mark reporting changes."), and the Peers charts mark the
    quarters each took effect. A registry that is not there or not well formed
    is refused, by entry, before anything is read. Its events (the 2020
    drawdowns and PPP loans in C&I; the firm, 17 Oct 2026, question 15) are
    labelled the same way, as ``event`` notes, on every series they touch;
    they leave nothing out and keep nothing in: the jump still decides.

    Where the jump leaves a bank's own window out and nothing else would
    have, every move that tripped it in a quarter a reporting change names
    for the product and measure, the series written continues across those
    windows instead of starting after them (the firm, 17 Oct 2026, question
    16: "When a labeled reporting change trips the 25% jump"): they stay out,
    unwritten, declared on a ``left-out:`` line, and the earlier history is
    kept. An event is not a reporting change (question 13's record: the 2020
    drawdowns and PPP "are not reporting changes"), so a window that only an
    event names breaks the series, as every other reason a window is left
    out does.

    ``stated_acquisitions`` is the file of acquisitions the FDIC record cannot
    see (``config/stated-acquisitions.json``, ``peers.stated``; the firm, 17
    Oct 2026, question 14), or None to state that none is read; required.
    The windows holding one are left out for its acquirer, with their own
    reason, charge-offs, the delinquency average and 30+ to charge-off alike,
    for the products the entry says it brought and no others (question 18, 18
    Oct 2026: "A listed deal leaves out only the portfolios it brought"); a
    malformed entry, or one naming a certificate not on the roster, is
    refused by entry before anything is read, and one outside the quarters
    read is named on the Run tab as not read.

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

    ``into`` and ``names`` go to ``build_peers_workbook`` as they are: with
    ``into`` (an openpyxl Workbook; ``out`` must then be None) the peer tabs
    are written into that workbook, under the titles ``names`` gives, and no
    peer workbook is saved -- the caller saves it, and then runs
    ``peers_workbook.na_as_gap`` over the tabs ``info["sheets"]`` names. The
    peer glossary and run record go into that workbook's own Glossary and Run
    tabs as second sections (``info["folded"]``). The series CSVs are written
    and put in place as ever.

    Returns ``{out, info, series}``: the workbook written (None with
    ``into``), what ``build_peers_workbook`` returned, and per series
    ``(path, quarters written, left out before, left out after)`` (0
    quarters: not written). Quarters written counts values only: the
    windows a series continues across are declared, not written.
    ``left_out`` is ``{path: [(first, last, why)]}`` for every series
    written (``left_out_spans``), for the book's left-out file."""
    s = dict(locals())
    products = _check_build(s)
    if reporting_changes is None or isinstance(reporting_changes, bool):
        raise ValueError("--reporting-changes must name the registry of Call Report changes "
                         "(config/reporting-changes.json), not %r" % (reporting_changes,))
    try:
        changes, events = RC.load_all(reporting_changes)
    except RC.RegistryError as e:
        raise ValueError("--reporting-changes: %s" % e) from None
    # Question 16: a reporting change, never an event; question 20 (18 Oct
    # 2026): only one whose own source says it can step a balance in one quarter.
    bridging = RC.can_step(changes)
    if isinstance(stated_acquisitions, bool) or not (stated_acquisitions is None
                                                     or isinstance(stated_acquisitions, (str, Path))):
        raise ValueError("--stated-acquisitions must name the file of acquisitions the FDIC record cannot see "
                         "(config/stated-acquisitions.json), or none, not %r" % (stated_acquisitions,))
    try:
        stated_ = [] if stated_acquisitions is None else ST.load(stated_acquisitions)
    except ST.StatedError as e:
        raise ValueError("--stated-acquisitions: %s" % e) from None
    if into is None:
        _check_out(out, roster=roster, mergers=mergers, absorptions=absorptions)
    elif out is not None:
        raise ValueError("into writes the peer tabs into that workbook and saves no peer workbook, so out must "
                         "be None, not %r" % (out,))
    quarters = fdic.quarter_ends(first, last)
    roster_ = R.load(roster)
    me = R.self_bank(roster_)
    pack_ = R.peers(roster_) if pack == "all" else R.regionals(roster_)
    # Question 22: each record must reach back to the first quarter.
    mergers_ = load_mergers(mergers, first)
    links_ = load_absorptions(absorptions, first, again=REPULL)
    extras_ = extras(extra_acquisitions, roster_, quarters)
    combined_ = combined(industry_combined)
    try:
        stated_q, stated_outside = ST.by_cert(stated_, [b["cert"] for b in roster_], quarters)
    except ST.StatedError as e:
        raise ValueError("--stated-acquisitions: %s" % e) from None
    # Question 18 (the firm, 18 Oct 2026): a deal leaves out only the
    # windows of the products it brought.
    stated_by = {p: ST.for_product(stated_, p, quarters) for p in products}
    # The book index reads a stated acquisition as one the bank declared.
    for c, qs in stated_q.items():
        for q in qs:
            if books.label(q) not in extras_.get(c, []):
                extras_.setdefault(c, []).append(books.label(q))

    cache = Path(cache)
    missing = [q for q in quarters if not (cache / ("q%s.json" % q)).exists()]
    if missing:
        raise ValueError("%s has no %d of the %d quarters asked for (first missing %s): run "
                         "'peers pull' first; build never fetches"
                         % (cache, len(missing), len(quarters), missing[0]))

    def no_fetch(url):
        raise ValueError("build reads the cache only and never fetches")
    flow_products = list(products) + [p for c in combined_ for p in c if p not in products]
    # The parent (books.PARENT) is required: every flow reads it to tell a
    # year to date restarted under a new owner (books.restarted), and without
    # it that rule would be off without a word. A cache pulled without it is
    # refused by fdic.pull, which says to pull again with refresh.
    fields = charge_off_fields(flow_products) + [books.PARENT]
    if delinquency:
        fields += [f for f in D.fields_for(products) if f not in fields]
    data = fdic.pull(quarters, fields, cache, fetch=no_fetch)
    repeats = books.repeated_ytd(data, links_, flow_products)
    data = books.without_repeats(data, repeats)
    acquired = {p: books.acquired_quarters(data, links_, p, acquisition_share) for p in products}
    # Pro forma: each roster bank's own figures plus those of every bank it
    # absorbed. An absorption that is added in is no longer a reason to leave
    # a quarter out; one that cannot be added (no filing) is, as before.
    combo = books.combination(data, links_, [b["cert"] for b in roster_]) if pro_forma else {}
    members = {c: v["members"] for c, v in combo.items()}
    names_ = {b["cert"]: b["short"] for b in roster_}
    # Question 21 (the firm, 18 Oct 2026): a member's first filing partway
    # through a year is that quarter's activity where it opened that quarter.
    firsts, opened, inst = opened_members(cache, members, data, names_)
    if pro_forma:
        added = {(c, b) for c, v in combo.items() for b, _ in v["members"]}
        rest = [ln for ln in links_ if (str(ln["acquirer"]), str(ln["absorbed"])) not in added]
        acquired_co = {p: books.acquired_quarters(data, rest, p, acquisition_share) for p in products}
    else:
        acquired_co = acquired
    merged = sorted({(r["acquirer"], r["quarter"]) for r in repeats})
    in_range = [e for e in stated_ if e not in stated_outside]
    stated_notes = {p: stated_note(stated_acquisitions, in_range, p, names_) for p in products}
    on_roster = [(c, q) for c, q in merged if c in names_]
    repeat_note = ("Absorptions under common control: the absorbed bank's year-to-date charge-offs and "
                   "recoveries, which the survivor's filing repeats, are taken off the survivor's for the "
                   "rest of that year. %s" % (
                       "None in these quarters." if not merged else
                       "%d survivor-quarters across every filer (each in %s); on the roster: %s."
                       % (len(merged), Path(absorptions).name,
                          ", ".join("%s in %s" % (names_[c], books.label(q)) for c, q in on_roster)
                          if on_roster else "none")))

    filers = len(data[quarters[-1]])
    ind = {p: books.industry(data, p) for p in products}
    rule = ("Rules: jump %g, acquisition share %g, minimum book %s ($000)%s, at least %d banks in a "
            "composite, %s." % (jump, acquisition_share, "{:,.0f}".format(min_book),
                                ", %s exempt" % me["short"] if exempt_self else "", min_banks,
                                "pro forma (each bank with the banks it absorbed)" if pro_forma
                                else "each bank as filed"))
    source = "Source: FDIC BankFind financials, %s to %s, from the cache %s." % (first, last, cache)

    def every(n):
        """The industry's denominator, ``n`` of the filers in the last
        quarter: a commercial series leaves out a filer that left a field
        blank (books.NOT_FILED_NOTE), so it is not always every filer."""
        if n == filers:
            return "every filer in the cache (%d in %s), no jump or minimum rule" % (filers, last)
        return ("%d of the %d filers in the cache in %s, the others leaving a field it needs blank (not "
                "filed), no jump or minimum rule" % (n, filers, last))
    out_dir = Path(series_dir)
    pack_words = "all %d peers" % len(pack_) if pack == "all" else "%d regionals" % len(pack_)

    made = []                   # (product words, file slug, who, words, rules apply?, rows)
    peer_books = {}
    for p in products:
        bks = {b["cert"]: books.bank_book(data, b["cert"], p, jump, min_book,
                                          exempt_min_book=exempt_self and b is me,
                                          acquired=acquired_co[p].get(b["cert"], []),
                                          members=members.get(b["cert"], ()), opened=opened,
                                          stated=stated_by[p].get(b["cert"], [])) for b in roster_}
        peer_books[p] = bks
        comp = books.composite(bks, [b["cert"] for b in pack_], min_banks)
        mids = {k: books.band(bks, [b["cert"] for b in pack_], k, (50,), min_banks=min_banks)
                for k in ("gross", "net")}
        median = [{"quarter": g["quarter"], "gross_rate": g["p50"], "net_rate": n["p50"]}
                  for g, n in zip(mids["gross"], mids["net"])]
        made += [
            (p, slug(p), "pack-composite",
             "pack composite (%s): kept flows over kept average balances" % pack_words, True, comp),
            (p, slug(p), "pack-median",
             "pack median (%s): the middle bank's kept rate, each bank counted once whatever its "
             "size" % pack_words, True, median),
            (p, slug(p), slug(me["short"]),
             "%s (certificate %s), its own book. %s" % (me["short"], me["cert"],
                                                       books.balance_path(bks[me["cert"]], 9) or
                                                       "Book: fewer than nine quarters held, so its path "
                                                       "is not stated"), True, bks[me["cert"]]),
            (p, slug(p), "industry", "industry: " + every(books.industry_filers(data, [p], quarters[-1])),
             False, ind[p]),
        ]
    for summed in combined_:
        made.append((" plus ".join(summed), slug(" ".join(summed)), "industry",
                     "industry, %s summed: %s" % (" and ".join(summed),
                                                  every(books.industry_filers(data, summed, quarters[-1]))), False,
                     books.industry(data, summed[0], summed[1:])))

    def gap_why(product, measure, gaps, rows, key="quarter"):
        """The words of a ``left-out:`` line: which moves left the windows out,
        and which reporting changes name their quarters; for a combined
        product, which of its parts each names (``named_for``)."""
        moved = sorted({q for r in rows if r[key] in gaps for q in r["jumped"]})
        named = named_for(bridging, product, measure, moved)
        if product in books.PRODUCTS:
            who = "%s names for %s" % (" and ".join(n for n, _ in named), product)
        else:
            parts_ = list(dict.fromkeys(x for _, ps in named for x in ps))
            who = "%s, %s of %s" % (" and ".join("%s names for %s" % (n, " and ".join(ps)) for n, ps in named),
                                    "a part" if len(parts_) == 1 else "parts", product)
        return ("The jump left these windows out and nothing else would have: every move that tripped it "
                "(%s) is in a quarter %s, %s. They are not written and never filled; the series "
                "continues across them and keeps every quarter before (the firm, 17 Oct 2026)."
                % (", ".join(moved), who, measure))

    def written(tail, before, after, note, product, measure, rows, key="quarter"):
        """The note lines of a series written from ``tail``: the reporting
        changes and events touching it (for a combined product, touching any
        of its parts, ``books.members``), and the left-out line."""
        if not tail:
            return []
        prods = [m for n in product.split(" plus ") for m in books.members(n)]
        note = note + RC.note_lines(changes, prods, measure, tail[0][0], tail[-1][0], note)
        note = note + RC.event_lines(events, prods, measure, tail[0][0], tail[-1][0], note)
        gaps = [q for q, v in tail if v is None]
        return series_note(note, tail, before, after,
                           gap_why(product, measure, set(gaps), rows, key) if gaps else None)

    series = []                 # (path, tail, note lines, left out before, left out after, group)
    left_out_ = {}              # path -> [(first, last, why)], as built
    for words_p, slug_, who, words, ruled, rows in made:
        own = who == slug(me["short"])
        for kind in ("gross", "net"):
            measure = RC.charge_off_measure(kind)
            bridge = bridged(rows, labelled_for(bridging, words_p, measure)) if own else set()
            tail, before, after = unbroken_tail([(r["quarter"], r[kind + "_rate"]) for r in rows], bridge)
            left_out_[out_dir / ("%s_%s_%s.csv" % (slug_, who, kind))] = left_out_spans(
                before, after, {r["quarter"]: break_reason(r, kind + "_rate", min_banks) for r in rows})
            note = ["%s, %s charge-off rate, trailing four quarters, %%." % (words_p, kind),
                    words[0].upper() + words[1:] + ".", source] + ([rule, stated_notes[words_p]] if ruled else []) \
                + [repeat_note]
            note += [d for d in dict.fromkeys(d for n in words_p.split(" plus ") for d in books.definitions(n))
                     if d not in note]
            series.append((out_dir / ("%s_%s_%s.csv" % (slug_, who, kind)), tail,
                           written(tail, before, after, note, words_p, measure, rows), before, after, None))
    # Each peer's own book, for the synthesis's peer percentiles: banks/ keeps
    # them apart from the pack, KeyBank and industry files beside it.
    for p in products:
        for b in R.peers(roster_):
            rows = peer_books[p][b["cert"]]
            for kind in ("gross", "net"):
                measure = RC.charge_off_measure(kind)
                tail, before, after = unbroken_tail([(r["quarter"], r[kind + "_rate"]) for r in rows],
                                                    bridged(rows, labelled_for(bridging, p, measure)))
                note = ["%s, %s charge-off rate, trailing four quarters, %%." % (p, kind),
                        "%s (certificate %s), its own book, a peer." % (b["short"], b["cert"]),
                        source, rule, stated_notes[p], repeat_note] + books.definitions(p)
                series.append((out_dir / "banks" / ("%s_%s_%s.csv" % (slug(p), slug(b["short"]), kind)), tail,
                               written(tail, before, after, note, p, measure, rows), before, after, ("banks", p)))
    dq_spec = None
    if delinquency:
        labels = {b["cert"]: "%s (%s)" % (b["short"], b["cert"]) for b in roster_}
        for path, rows, note, p, m, left_out, bridge, reasons in _delinquency_series(
                data, roster_, me, pack_, pack_words, products, jump, min_book, exempt_self,
                min_banks, source, every, out_dir, acquired, acquisition_share, stated_by, stated_notes, bridging):
            tail, before, after = unbroken_tail(rows, bridge)
            left_out_[path] = left_out_spans(before, after, reasons)
            if left_out is not None and tail:
                note = note + [left_out_note(left_out, tail, labels)]
            moved = [{"q": q, "jumped": j} for q, j in bridge.items()]
            series.append((path, tail, written(tail, before, after, note, p, m, moved, "q"), before, after, p))
        dq_spec = dict(data=data, products=list(products), jump=jump, min_book=min_book,
                       exempt_self=exempt_self, acquired=acquired, measure=START_MEASURE,
                       basis=START_BASIS)
        # 30+ to charge-off and the gaps (flows.py): the delinquency fields and
        # the gross charge-offs of each bank's own filings. The pack composite
        # is as built; it does not follow Banks in the pack.
        for path, rows, note, p, m, reasons in _flow_series(
                data, roster_, me, pack_, pack_words, products, jump, acquisition_share, min_banks, source, every,
                out_dir, acquired, stated_by, stated_notes):
            tail, before, after = unbroken_tail(rows)
            left_out_[path] = left_out_spans(before, after, reasons)
            if tail:
                # The changes and events touching what it is made of: gross charge-offs and the three
                # delinquency fields, each once.
                for lines_ in (RC.note_lines, RC.event_lines):
                    for under in (RC.charge_off_measure("gross"), "30-89", "90+ accruing", "nonaccrual"):
                        note = note + [x for x in lines_(changes if lines_ is RC.note_lines else events,
                                                         books.members(p), under, tail[0][0], tail[-1][0], note)
                                       if x not in note]
            series.append((path, tail, series_note(note, tail, before, after), before, after, ("flows", p)))

    # The left-out file lists the windows a series continues across too, in
    # order with what was left out before and after it.
    for path, tail, *_ in series:
        if path in left_out_ and any(v is None for _, v in tail):
            left_out_[path] = sorted(left_out_[path] + within_spans(tail))
    paths = [str(path).lower() for path, *_ in series]
    twice = sorted({p for p in paths if paths.count(p) > 1})
    if twice:                   # combined() refuses the known cause; this is the backstop
        raise ValueError("two series would be written to the same file, %s; nothing is written"
                         % ", ".join(twice))

    out = Path(out) if into is None else None
    part_out = out.with_name(out.stem + ".part" + out.suffix) if out is not None else None
    parts = []
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        info = peers_workbook.build_peers_workbook(
            part_out, data, roster_, products, jump, min_book, pack, mergers_, extras_,
            base_quarter, exempt_self=exempt_self, min_banks=min_banks, rank_by=rank_by,
            last_n=last_n, min_obs=min_obs, index_min_book=index_min_book,
            lagged_years=lagged_years, lag_years=lag_years,
            normalisation_years=normalisation_years, mix_base_year=mix_base_year,
            industry=ind, delinquency=dq_spec, acquired=acquired_co, cache_dir=cache, mergers_file=mergers,
            combined=members, opened=opened, changes=changes, stated=stated_by,
            sources=["Read from the cache %s, %d quarter files %s to %s, built %s"
                     % (cache, len(quarters), quarters[0], quarters[-1],
                        dt.date.today().isoformat())] + pro_forma_lines(pro_forma, combo, names_)
            + opened_lines(firsts, opened, inst, combo, names_)
            + ["Reporting changes: %s, %d changes and %d events, SHA-256 %s; each series file notes those touching it"
               % (reporting_changes, len(changes), len(events),
                  hashlib.sha256(Path(reporting_changes).read_bytes()).hexdigest())]
            + ["Stated acquisitions: none read (none was named)" if stated_acquisitions is None else
               "Stated acquisitions: %s, %d entries, SHA-256 %s; in these quarters: %s; outside them, not read: %s"
               % (stated_acquisitions, len(stated_), hashlib.sha256(Path(stated_acquisitions).read_bytes()).hexdigest(),
                  "; ".join("%s %s (brought %s)" % (names_[e["acquirer"]], e["quarter"], ", ".join(e["products"]))
                            for e in in_range) or "none",
                  "; ".join("%s %s" % (names_[e["acquirer"]], e["quarter"]) for e in stated_outside) or "none")],
            into=into, names=names, book_kind=book_kind)
        moves = [(part_out, out)] if out is not None else []
        for path, tail, lines, _, _, _ in series:
            if tail:
                part = path.with_name(path.name + ".part")
                parts.append(part)
                books.write_series(tail, part, lines)
                moves.append((part, path))
        # A peer's file from an earlier run whose bank this run does not draw
        # (it left the roster, or its short name changed) is removed too, so
        # the synthesis is never fed a bank that is no longer a peer.
        planned = {str(path).lower() for path, *_ in series}
        stale = [f for f in sorted((out_dir / "banks").glob("*.csv"))
                 if f.name.split("_")[0] in {slug(p) for p in products} and str(f).lower() not in planned]
        gone = _commit(moves, [path for path, tail, *_ in series if not tail] + stale, say)
        parts = []
    finally:
        for f in parts + ([part_out] if part_out is not None else []):
            if f.exists():
                f.unlink()

    say("Wrote %s: %s, %d TTM quarters, pack of %d"
        % (out if out is not None else "the peer tabs into the workbook given (%s)" % ", ".join(info["sheets"]),
           ", ".join(info["products"]), len(info["quarters"]), len(info["pack"])))
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
            if not after or isinstance(group, tuple):
                continue        # 150 files: counted below; what each leaves out is in its notes
        gaps = len(tail) - values(tail)
        say("Wrote %s: %d quarters%s%s%s"
            % (path, values(tail), ", %d left out within it, not written (left-out line)" % gaps if gaps else "",
               ", %d earlier left out at a break" % len(before) if before else "",
               ", ends %s: %d later quarter%s with no value"
               % (tail[-1][0], len(after), "" if len(after) == 1 else "s") if after else ""))
    for p, (n, of, broke) in written.items():
        if isinstance(p, tuple) and p[0] == "flows":
            say("30+ to charge-off, %s: %d of %d series written to %s (the latest two quarter-ends have no "
                "value yet; each file's notes say what is left out)" % (p[1], n, of, out_dir))
            continue
        if isinstance(p, tuple):
            say("Each peer's own book, %s: %d of %d series written to %s"
                % (p[1], n, of, out_dir / "banks"))
            continue
        say("Delinquency, %s: %d of %d series written to %s%s"
            % (p, n, of, out_dir, "; %d start after a break (a four-quarter average always does), "
               "the quarters left out named in each file's notes" % broke if broke else ""))
    return dict(out=out, info=info,
                series=[(path, values(tail), before, after) for path, tail, _, before, after, _ in series],
                left_out={path: spans for path, spans in left_out_.items()
                          if str(path).lower() in {str(p_).lower() for p_, t_, *_ in series if t_}})
