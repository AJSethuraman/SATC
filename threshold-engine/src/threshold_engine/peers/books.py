"""Per-bank books, the pack composite, the band and the industry, from FDIC
Call Report rows. docs/PEERS-SPEC.md, "books.py", is the contract.

Input is ``{REPDTE: [rows]}`` as ``fdic.pull`` returns it: one list of rows per
quarter-end (``YYYYMMDD``), each row a dict with ``CERT``, ``REPDTE`` and the
fields. Amounts are $ thousands. Charge-offs (``DR*``) and recoveries
(``CR*``) are year-to-date; balances (``LN*``) are quarter-end. For the
consumer products a field filed as blank counts as 0, as the earlier build
counted it. For the commercial products (``COMMERCIAL``, 16 Oct 2026) there is
no earlier build to reproduce, so a blank field is **not filed**, never 0, as
``delinquency.py`` reads every field: the bank-quarter has no balance and no
flow for that product (``NOT_FILED``, ``filed_amount``). A bank with no row in
a quarter is missing, never 0.

The rule, as ``build_peers.py`` applied it (6 Oct 2026):

- quarterly flow: Q1 is its year-to-date; a later quarter is its year-to-date
  less the previous quarter's, or missing if the bank is absent from either;
  where the year-to-date fell and the bank's parent changed, it restarted
  (``restarted``) and is the quarter's flow;
- TTM: the four quarters i-3 to i; the average balance is the mean of their
  four quarter-end balances;
- a bank-quarter is kept only if the average balance is at least the minimum
  book (unless the bank is exempt) and above 0, all four flows are present,
  and no quarter k in i-4 to i moved its balance by more than the jump
  (``|b_k / b_(k-1) - 1| > jump``) or from 0 to above 0. Quarter i-4 is in the
  test because the first flow in the window is measured from its year-to-date;
- gross rate = 100 x TTM gross / average balance; net rate = 100 x (TTM gross
  - TTM recoveries) / average balance; both None when not kept.

The jump and the minimum book are judgements, so they are required arguments
with no default. So is the minimum number of banks a composite or band needs:
the spec's draft default of 3 does not reproduce the earlier build, which
required 5.

A TTM is four consecutive calendar quarters. Where the data skips a
quarter-end, or holds a quarter with no filer at all (a quarter the FDIC has
not published yet), the windows that touch it are refused as missing rather
than built from whatever quarters sit next to each other in the data.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..profile import percentile

#: Product -> (balance, gross charge-offs YTD, recoveries YTD) field names.
#: A name joined by "+" is the sum of those filed fields (``parts``). Other
#: consumer's balance is RC-C 6.d (LNCONOTH) plus 6.b, other revolving credit
#: plans (LNCONRP), because its charge-offs (RI-B 5.c) and past-due lines
#: (RC-N 5.c) both include those plans: 6.d alone left the numerator covering
#: more loans than the denominator (the firm, 13 Oct 2026: "Yes, fix it").
#: KeyBank, 30 Jun 2026: 4,200,208 + 268,825 = 4,469,033.
CONSUMER = {
    "Credit card": ("LNCRCD", "DRCRCD", "CRCRCD"),
    "Mortgage": ("LNRERSFM", "DRRERSFM", "CRRERSFM"),
    "Home equity": ("LNRELOC", "DRRELOC", "CRRELOC"),
    "Other consumer": ("LNCONOTH+LNCONRP", "DRCONOTH", "CRCONOTH"),
    "Auto": ("LNAUTO", "DRAUTO", "CRAUTO"),
}

#: The commercial products, 16 Oct 2026: (balance, gross charge-offs YTD,
#: recoveries YTD). Every name is one docs/commercial-2026-10/research-fdic.md
#: (on main) confirmed four ways: in the FDIC's definitions files, returning
#: values from the live API, NT = DR - CR in every KeyBank and JPMorgan
#: quarter, and the categories adding up to LNLSGR. The DR and CR fields are
#: year to date, as the consumer ones are; the FDIC's quarterly versions
#: (DRCIQ and so on) are FDIC-computed and differ in merger quarters, so they
#: are not read. The real estate items are domestic offices; C&I (LNCI) is
#: the whole bank, U.S. and non-U.S. addressees. First quarter any filer
#: files them: balances 1984Q1; C&I charge-offs 1984Q1; real estate
#: charge-offs 1990Q1; the two nonfarm nonresidential splits 2007Q1.
COMMERCIAL = {
    "C&I": ("LNCI", "DRCI", "CRCI"),
    "Construction": ("LNRECONS", "DRRECONS", "CRRECONS"),
    "Multifamily": ("LNREMULT", "DRREMULT", "CRREMULT"),
    "Nonfarm nonresidential": ("LNRENRES", "DRRENRES", "CRRENRES"),
    "Owner-occupied nonfarm nonresidential": ("LNRENROW", "DRRENROW", "CRRENROW"),
    "Other nonfarm nonresidential": ("LNRENROT", "DRRENROT", "CRRENROT"),
}

#: Every product the peers pull and build know: the consumer five, then the
#: commercial six.
PRODUCTS = {**CONSUMER, **COMMERCIAL}

#: The filed fields whose blank is not filed, never 0: every commercial
#: product's. The consumer fields keep the earlier build's reading.
NOT_FILED = frozenset(f for names in COMMERCIAL.values() for n in names for f in n.split("+"))

#: What a product's series notes must say about its definition. Stated in
#: every file built for the product, so the Sources tab carries it.
DEFINITIONS = {
    "Credit card": ("Securitized cards: before 2010, cards a bank had securitized were off its books, so "
                    "quarters before 2010Q1, and four-quarter windows holding one (through 2010Q3), exclude "
                    "them. From 1 Jan 2010 the accounting rules (FAS 166 and 167) brought them back on. The "
                    "firm chose to label these quarters, not drop them (14 Oct 2026); the comparability "
                    "tie-out measured the break in the industry rate at about +0.9 points."),
    "Other consumer": ("Other consumer's balance is RC-C 6.b, other revolving credit plans (LNCONRP), plus "
                       "6.d (LNCONOTH), matching its charge-offs (RI-B 5.c) and past-due lines (RC-N 5.c), "
                       "which both include those plans. The FDIC data has no 6.b before 2001Q1: before it "
                       "the balance is 6.d alone, so a series reaching back past 2001 breaks there. Auto "
                       "was inside 6.d until 2011Q1, when it got its own line (6.c)."),
}

#: Said on every commercial series. Measured on the peers cache pulled 16 Oct
#: 2026 (1991Q1 to 2026Q2); the call forms and names from the FDIC API that day.
NOT_FILED_NOTE = ("A blank field is not filed, never 0: a bank that left one blank is left out of that quarter, "
                  "its book and the industry's alike. In every quarter from 2006, 17 or 18 filers file no "
                  "charge-off, past-due or nonaccrual field, so they are in no commercial series: at 2026Q2, "
                  "17 filers on CALLFORM 2 whose names are foreign banks', with $77.6bn of C&I and $8.8bn of "
                  "nonfarm nonresidential.")
_SPLIT = ("{what} is RC-C {item} ({field}), first filed 2007Q1: before it every filer leaves it blank, which is "
          "not filed, so nothing is written before then. In 2007Q1 to 2007Q4, 2,925 to 3,044 filers with "
          "nonfarm nonresidential loans filed both parts of the split as 0 ($20.1bn to $27.0bn of those loans; "
          "the FDIC's definition of LNRENROW: before March 2008 a memoranda item for filers that met specific "
          "criteria); from 2008Q1 none did. The industry series counts them as filed, so in 2007, and in its "
          "four-quarter windows holding a 2007 quarter (through 2008Q3), it leaves those loans out: labelled, "
          "not dropped. Savings institutions filing the TFR (CALLFORM 100) never filed the split (838 filers, "
          "$64.1bn of nonfarm nonresidential loans at 2007Q1; the FDIC: \"not available for TFR Reporters\"): "
          "blank for 655 filers at 2011Q4 and 17 from 2012Q1.")
DEFINITIONS.update({
    "C&I": ("C&I is RC-C 4 for the whole bank (LNCI: U.S. and non-U.S. addressees); the real estate products "
            "are domestic offices. The FDIC's definitions say that for banks with assets under $300 million "
            "C&I charge-offs and recoveries (DRCI, CRCI) include all other loans (NTCI's says before 2001), "
            "and so do the past-due and nonaccrual items (P3CI, P9CI, NACI); whether that holds after 2001 "
            "was not checked. " + NOT_FILED_NOTE),
    "Construction": ("Construction is RC-C 1.a (LNRECONS), construction and land development, domestic "
                     "offices, 1-4 family and other together. " + NOT_FILED_NOTE),
    "Multifamily": "Multifamily (LNREMULT) is loans secured by 5 or more dwelling units, domestic offices. " + NOT_FILED_NOTE,
    "Nonfarm nonresidential": ("Nonfarm nonresidential is RC-C 1.e (LNRENRES), domestic offices, owner-occupied "
                               "and other together. " + NOT_FILED_NOTE),
    "Owner-occupied nonfarm nonresidential": _SPLIT.format(what="Owner-occupied nonfarm nonresidential",
                                                           item="1.e(1)", field="LNRENROW") + " " + NOT_FILED_NOTE,
    "Other nonfarm nonresidential": _SPLIT.format(what="Other nonfarm nonresidential", item="1.e(2)",
                                                  field="LNRENROT") + " " + NOT_FILED_NOTE,
})

#: A product the Call Report also files in parts that add up to it: RC-C item
#: 1.e, nonfarm nonresidential (LNRENRES), is 1.e(1), owner-occupied
#: (LNRENROW), plus 1.e(2), other (LNRENROT), as DEFINITIONS above say
#: ("owner-occupied and other together"). The parts are filed from 2007Q1.
SPLITS = {"Nonfarm nonresidential": ("Owner-occupied nonfarm nonresidential", "Other nonfarm nonresidential")}


def stacking(products: Sequence[str]) -> List[Tuple[str, Tuple[int, ...]]]:
    """How each of ``products`` goes into a stack that must count no loan
    twice (the share panel on Peers), as ``(role, parts)`` in their order.
    ``parts`` are the positions in ``products`` of the parts of its split.

    - ``("own", ())``: no other product built overlaps it; stacked as it is.
    - ``("whole", parts)``: a parent (``SPLITS``) whose every part is built:
      stacked only in a quarter in which not every part has a figure.
    - ``("part", parts)``: a part whose parent and every other part are
      built: stacked only in a quarter in which every part has a figure.
    - ``("inside", ())``: a part whose parent is built but not every other
      part is: the parent holds it, so it is never stacked.

    A part whose parent is not built has nothing to overlap: ``own``."""
    at = {p: i for i, p in enumerate(products)}
    out: List[Tuple[str, Tuple[int, ...]]] = []
    for p in products:
        role: Tuple[str, Tuple[int, ...]] = ("own", ())
        if p in SPLITS and any(q in at for q in SPLITS[p]):
            pieces = SPLITS[p]
            role = ("whole", tuple(at[q] for q in pieces)) if all(q in at for q in pieces) else ("own", ())
        for parent, pieces in SPLITS.items():
            if p in pieces and parent in at:
                role = ("part", tuple(at[q] for q in pieces)) if all(q in at for q in pieces) else ("inside", ())
        out.append(role)
    return out


WHY_JUMP = "book moved more than the jump in this window"
WHY_ACQUIRED = "an acquisition brought in at least the acquisition share in this window"
#: A stated acquisition (``peers.stated``): one the FDIC record cannot see,
#: listed with its filing, whose share of the book was never measured.
WHY_STATED = "a stated acquisition the FDIC record cannot see is in this window"

#: The FDIC field naming a filer's top holding company (its RSSD ID), filed
#: each quarter. Two banks with the same one are under common control.
PARENT = "RSSDHCR"
WHY_SMALL = "book under the minimum"
WHY_MISSING = "a quarter is missing"
#: A commercial product's field left blank by a bank that filed the quarter.
WHY_NOT_FILED = "a field of the product is not filed (blank) in this window"

_QUARTER_ENDS = ("0331", "0630", "0930", "1231")


def _month_quarter(q, month: str) -> int:
    """A month '01'-'12' -> its quarter 1-4; anything else is refused."""
    if not (len(month) == 2 and month.isdigit() and 1 <= int(month) <= 12):
        raise ValueError("not a quarter: %r (the month must be 01 to 12)" % (q,))
    return (int(month) - 1) // 3 + 1


def label(repdte: str) -> str:
    """'20260630' -> '2026Q2'. Only a YYYYMMDD date with a month 01-12 is
    labelled; anything else is refused rather than called 'Q0'."""
    if not (isinstance(repdte, str) and len(repdte) == 8 and repdte.isdigit()):
        raise ValueError("not a YYYYMMDD quarter-end: %r" % (repdte,))
    return "%sQ%d" % (repdte[:4], _month_quarter(repdte, repdte[4:6]))


def quarter_end(q: str) -> str:
    """A quarter as 'YYYYQn', 'YYYYMMDD' or an ISO date -> its quarter-end ISO
    date. A quarter outside 1-4 or a month outside 01-12 is refused
    (``ValueError``), never turned into some other date."""
    if not isinstance(q, str):
        raise ValueError("not a quarter: %r" % (q,))
    if len(q) == 6 and q[:4].isdigit() and q[4] == "Q" and q[5] in "1234":
        y, n = int(q[:4]), int(q[5])
    elif len(q) == 8 and q.isdigit():
        y, n = int(q[:4]), _month_quarter(q, q[4:6])
    elif len(q) == 10 and q[:4].isdigit() and q[4] == "-" and q[7] == "-":
        y, n = int(q[:4]), _month_quarter(q, q[5:7])
    else:
        raise ValueError("not a quarter: %r" % (q,))
    return "%d-%s" % (y, ("03-31", "06-30", "09-30", "12-31")[n - 1])


def parts(name: str) -> List[str]:
    """The filed fields a field name stands for: ``"A+B"`` -> ``["A", "B"]``."""
    return name.split("+")


def raw_fields(names: Iterable[str]) -> List[str]:
    """The filed fields to pull for ``names``, in order, each once."""
    out: List[str] = []
    for n in names:
        for f in parts(n):
            if f not in out:
                out.append(f)
    return out


def _fields(product: str) -> Tuple[str, str, str]:
    if product not in PRODUCTS:
        raise ValueError("product must be one of %s, not %r" % (sorted(PRODUCTS), product))
    return PRODUCTS[product]


def _num(row: dict, field: str) -> float:
    """A filed amount; blank counts as 0, as the earlier build counted it.
    An amount that is not a finite number (``json.loads`` reads a bare NaN,
    and ``float`` reads "inf") is refused, naming the bank, the quarter and the
    field, as ``delinquency`` refuses it: kept, it would carry through every
    rate and composite and be written to Excel as a blank."""
    if "+" in field:
        return sum(_num(row, f) for f in parts(field))
    x = float(row.get(field) or 0)
    if not math.isfinite(x):
        raise ValueError("certificate %s, %s: %s is %r, not a number"
                         % (row.get("CERT"), row.get("REPDTE"), field, row.get(field)))
    return x


def _blank(value) -> bool:
    return value is None or value == ""


def filed_amount(row: dict, field: str) -> Optional[float]:
    """``_num``, except that a blank ``NOT_FILED`` field (or a blank part of a
    sum) is None: not filed. A consumer field's blank stays 0."""
    if any(f in NOT_FILED and _blank(row.get(f)) for f in parts(field)):
        return None
    return _num(row, field)


def not_filed(row: dict, product: str) -> Optional[str]:
    """The first of ``product``'s fields this filing leaves blank where a
    blank is not filed (``NOT_FILED``), or None. Always None for a consumer
    product, whose blanks count as 0."""
    return next((f for n in _fields(product) for f in parts(n)
                 if f in NOT_FILED and _blank(row.get(f))), None)


def _at_least(name: str, value, low) -> None:
    """Refuse a judgement setting below its floor (NaN is refused too)."""
    if isinstance(value, bool) or not value >= low:
        raise ValueError("%s must be at least %s, not %r" % (name, low, value))


def _follows(prev: str, q: str) -> bool:
    """True when quarter-end ``q`` is the one straight after ``prev``."""
    a = int(prev[:4]) * 4 + (int(prev[4:6]) - 1) // 3
    b = int(q[:4]) * 4 + (int(q[4:6]) - 1) // 3
    return b == a + 1


def _contiguous(qs: Sequence[str]) -> List[bool]:
    """Per position, True when that quarter-end straight follows the one before
    it in the data. The first position has nothing before it, so False."""
    return [False] + [_follows(a, b) for a, b in zip(qs, qs[1:])]


def _by_cert(data: Dict[str, list]) -> Tuple[List[str], Dict[str, Dict[str, dict]]]:
    """Quarter-ends in order, and each quarter's rows keyed by certificate.
    The keys must be REPDTE quarter-ends (``YYYYMMDD`` ending 0331, 0630, 0930
    or 1231) as ``fdic.pull`` returns them; any other key is refused, because
    the Q1 test reads the month from the key."""
    for q in data:
        if not (isinstance(q, str) and len(q) == 8 and q.isdigit() and q[4:] in _QUARTER_ENDS):
            raise ValueError("data must be keyed by YYYYMMDD quarter-ends, not %r" % (q,))
    qs = sorted(data)
    return qs, {q: {str(r["CERT"]): r for r in data[q]} for q in qs}


def _parent(row: dict) -> str:
    v = str(row.get(PARENT) or "").strip()
    return "" if v == "0" else v


#: Set by ``without_repeats`` on the rows it touches: whether that filing
#: restarted, decided on the filings as filed. A row it changed holds a
#: reduced year to date, which must not be read as a fall.
_RESTARTED = "_restarted"


def _ytd_fields(row: dict, prev: dict) -> List[str]:
    """The year-to-date fields (charge-offs ``DR*``, recoveries ``CR*``) both
    filings carry."""
    return [k for k in row if k[:2] in ("DR", "CR") and k in prev
            and not (k in NOT_FILED and (_blank(row[k]) or _blank(prev[k])))]


def restarted(row: dict, prev: dict) -> bool:
    """True when a bank's year to date started again mid-year: its parent
    (``PARENT``) changed between the two filings and at least one of its
    year-to-date fields fell. A bank bought by a new holding company can
    restart its year to date from the acquisition (push-down accounting), and
    then every year-to-date field restarts together, so the decision is one
    per filing, never one per field: the filed year-to-date is the quarter's
    flow for charge-offs and recoveries alike. Found on 14 Oct 2026 against
    the FDIC's Quarterly Banking Profile: National City under PNC, 2008Q4,
    -$94.6m of card charge-offs, and four quarters like it. Both parents must
    be filed: an unknown parent is never read as a change."""
    if _RESTARTED in row:
        return row[_RESTARTED]
    a, b = _parent(row), _parent(prev)
    return bool(a and b and a != b) and any(_num(row, f) < _num(prev, f) for f in _ytd_fields(row, prev))


def flow(row: dict, prev: dict, field: str) -> float:
    """A non-Q1 quarter's flow: year-to-date less the quarter before's, or
    the year-to-date itself where the filing ``restarted``. ``field`` may be
    a sum (``"A+B"``)."""
    return _num(row, field) if restarted(row, prev) else _num(row, field) - _num(prev, field)


def quarterly_flows(data: Dict[str, list], cert, product: str) -> List[tuple]:
    """``(q, gross, recoveries, balance)`` per quarter-end ``q`` in the data.

    A Q1 flow is its year-to-date. A later quarter's flow is its year-to-date
    less the previous quarter's (``flow``: a restarted year-to-date is the
    flow itself), or None if the bank is missing from either
    quarter (or the previous quarter-end is not in the data). The balance is
    the quarter-end figure, None when the bank did not file that quarter."""
    qs, snap = _by_cert(data)
    return _flows(qs, snap, cert, product)


def _flows(qs, snap, cert, product: str) -> List[tuple]:
    """``quarterly_flows`` over data already keyed by ``_by_cert``."""
    ln, dr, cr = _fields(product)
    cert = str(cert)
    out = []
    for i, q in enumerate(qs):
        r = snap[q].get(cert)
        p = snap[qs[i - 1]].get(cert) if i and _follows(qs[i - 1], q) else None
        if r and not_filed(r, product):
            r = None                    # the product not filed: no balance, no flow
        if p and not_filed(p, product):
            p = None                    # no year to date to measure this quarter's flow from
        bal = _num(r, ln) if r else None
        if r and q[4:6] == "03":
            out.append((q, _num(r, dr), _num(r, cr), bal))
        elif r and p:
            out.append((q, flow(r, p, dr), flow(r, p, cr), bal))
        else:
            out.append((q, None, None, bal))
    return out


def combination(data: Dict[str, list], links: Sequence[dict], certs: Iterable) -> Dict[str, dict]:
    """Pro forma: per certificate in ``certs``, the banks whose figures are
    added to its own, ``{"members": [(absorbed, until)], "uncombined":
    [(absorbed, YYYYMMDD)]}``.

    ``links`` are ``fdic.absorptions`` rows. A bank's members are every bank
    it absorbed, and every bank those absorbed before them, through the whole
    chain. ``until`` is the quarter-end (``YYYYMMDD``) of the absorption that
    brought the member in, the earliest along the chain: the member counts in
    every quarter up to and including it in which it filed itself. After it,
    its book is in the absorber's own filing. A bank absorbed inside the
    data's quarters that never filed in them up to then cannot be added: it
    is listed under ``uncombined``, and its acquisition is treated as it is
    without pro forma (``acquired_quarters``)."""
    qs, snap = _by_cert(data)
    filed: Dict[str, List[str]] = {}
    for q in qs:
        for c in snap[q]:
            filed.setdefault(c, []).append(q)
    by_acq: Dict[str, List[Tuple[str, str]]] = {}
    for ln in links:
        by_acq.setdefault(str(ln["acquirer"]), []).append((str(ln["absorbed"]), _yyyymmdd(ln["quarter"])))
    out: Dict[str, dict] = {}
    for cert in certs:
        cert = str(cert)
        members: List[Tuple[str, str]] = []
        uncombined: List[Tuple[str, str]] = []
        seen = {cert}

        def walk(acq: str, until: Optional[str]) -> None:
            for b, q in sorted(by_acq.get(acq, [])):
                if b in seen:
                    continue
                seen.add(b)
                u = q if until is None else min(q, until)
                if any(x <= u for x in filed.get(b, ())):
                    members.append((b, u))
                elif qs and qs[0] <= q <= qs[-1]:
                    uncombined.append((b, q))
                walk(b, u)

        walk(cert, None)
        out[cert] = {"members": members, "uncombined": uncombined}
    return out


def combined_flows(data: Dict[str, list], cert, product: str,
                   members: Sequence[Tuple[str, str]] = ()) -> List[tuple]:
    """``quarterly_flows`` for a bank with its ``members`` (``combination``)
    added: per quarter-end, the balance is the sum of the quarter-end balances
    of every one of them that filed that quarter, and each flow the sum of
    each one's own flow, measured within its own filings, so a merger never
    reads as a fall or a rise in a year to date. A member counts only up to
    its ``until``. A quarter in which none of them filed has no balance; a
    quarter in which one of them filed but has no flow (it did not file the
    quarter before) has no flow.

    The quarter of the absorption itself holds the absorbed bank's book in
    the balance but its charge-offs only from the day the deal closed: the
    absorbed bank files nothing for that quarter, and the absorber's filing
    covers the acquired loans from the close. The absorber also books the
    loans it buys at fair value, so their charge-offs in the first quarters
    after a deal are not exactly what the absorbed bank would have reported."""
    qs, snap = _by_cert(data)
    own = _flows(qs, snap, cert, product)
    if not members:
        return own
    parts_ = [(own, None)] + [(_flows(qs, snap, b, product), until) for b, until in members]
    out = []
    for i, (q, _, _, _) in enumerate(own):
        g = rc = bal = 0.0
        filed = broken = False
        for rows, until in parts_:
            if until is not None and q > until:
                continue
            _, gi, ri, bi = rows[i]
            if bi is None:
                continue
            filed = True
            bal += bi
            if gi is None:
                broken = True
            else:
                g += gi
                rc += ri
        flows_ok = filed and not broken
        out.append((q, g if flows_ok else None, rc if flows_ok else None, bal if filed else None))
    return out


def members_by_quarter(data: Dict[str, list], members: Sequence[Tuple[str, str]]) -> Dict[str, List[Tuple[str, str]]]:
    """Per TTM quarter ('YYYYQn'), the ``members`` whose own filings are in
    it: each that filed in one of its four quarter-ends, up to its
    ``until``."""
    qs, snap = _by_cert(data)
    out = {}
    for k, q in enumerate(qs):
        win = qs[max(0, k - 3):k + 1]
        out[label(q)] = [(b, u) for b, u in members if any(w <= u and b in snap[w] for w in win)]
    return out


def _blank_quarters(data: Dict[str, list], cert, product: str,
                    members: Sequence[Tuple[str, str]] = ()) -> List[bool]:
    """Per quarter-end in the data, True when the bank, or one of its
    ``members`` up to its ``until``, filed that quarter but left a field of
    ``product`` blank where a blank is not filed (``not_filed``)."""
    qs, snap = _by_cert(data)
    who = [(str(cert), None)] + [(str(b), u) for b, u in members]
    return [any(c in snap[q] and (u is None or q <= u) and bool(not_filed(snap[q][c], product))
                for c, u in who) for q in qs]


def bank_book(data: Dict[str, list], cert, product: str, jump: float, min_book: float,
              exempt_min_book: bool = False, *, acquired: Iterable[str],
              stated: Iterable[str], members: Sequence[Tuple[str, str]] = ()) -> List[dict]:
    """One row per TTM quarter, from the fifth quarter in the data, labelled
    ``YYYYQn``: ``{quarter, gross_rate, net_rate, gross, recoveries,
    avg_balance, kept, why, jumped, why_without_jump}``.

    ``jump`` is the largest quarter-on-quarter balance move (0.25 = 25%) that
    is still credit rather than a merger, sale or reclassification;
    ``min_book`` is the smallest average balance ($ thousands) whose rate is
    kept. Either below 0 is refused. ``exempt_min_book`` lifts the minimum for
    the bank drawn as itself. A quarter with no filing counts as a balance of
    0 in the jump and average tests, as the earlier build counted it. ``why``
    names the first reason a quarter is not kept, in the order: jump,
    acquisition, stated acquisition, minimum, missing. Ahead of all of them, a window whose
    quarters i-4 to i are not consecutive quarter-ends in the data is missing:
    neither the jump nor a TTM can be measured across a quarter the data does
    not hold. Next, for a commercial product, a window is not filed
    (``WHY_NOT_FILED``) when, in any quarter its jump test reads (i-5 to i:
    the move into i-4 is measured from i-5), the bank or a bank added pro
    forma filed but left a field of the product blank: a blank is not a 0,
    so neither the jump nor the TTM can be measured over it. Quarters before
    the first in the data are not read (for the first window, i-5 is one).
    Where one of the window's own four quarters (i-3 to i) is not filed,
    ``avg_balance`` is None too: the balance is not known, and three filed
    balances over four, or a 0, would be a figure nobody filed.

    ``acquired`` is this bank's quarter-ends (``YYYYMMDD``) in which recorded
    acquisitions brought in at least the acquisition share of its book
    (:func:`acquired_quarters`). A TTM window holding one is left out: its
    flows mix two books. Required; an empty list states there are none.
    ``stated`` is this bank's quarter-ends of stated acquisitions, the ones
    the FDIC record cannot see (``peers.stated``; the firm, 17 Oct 2026,
    question 14): a window holding one is left out too, right after the
    recorded ones, with its own reason (``WHY_STATED``), since no share of
    the book was measured. Required, like ``acquired``: an empty list states
    there are none, so a caller cannot leave them out without saying so.

    ``jumped`` names the quarters (``YYYYQn``, i-4 to i) whose move tripped
    the jump, when the jump is the reason; else it is empty.
    ``why_without_jump`` is the reason the window would have if those moves
    had not tripped it (None: it would be kept), so a caller can tell a
    window left out only by the jump (the firm, 17 Oct 2026, question 16:
    a move in a quarter a reporting change names, never an event, does not break
    the series written; ``peers.run.unbroken_tail``). For a window the jump
    does not leave out it is ``why`` itself.

    ``members`` (``combination``) are the banks it absorbed, added to its own
    figures quarter by quarter (``combined_flows``): pro forma. With none,
    the book is the bank's own filings alone."""
    _at_least("jump", jump, 0)
    _at_least("min_book", min_book, 0)
    if isinstance(acquired, str):
        raise ValueError("acquired is a list of quarter-ends, not %r" % (acquired,))
    acquired = set(acquired)
    flows = combined_flows(data, cert, product, members)
    follows = _contiguous([q for q, _, _, _ in flows])
    blank = _blank_quarters(data, cert, product, members)
    bal = [0.0 if b is None else b for _, _, _, b in flows]
    moved = [False] + [bool(a > 0 and abs(b / a - 1) > jump) or (a == 0 and b > 0)
                       for a, b in zip(bal, bal[1:])]
    if isinstance(stated, str):
        raise ValueError("stated is a list of quarter-ends, not %r" % (stated,))
    stated = set(stated)
    bought = [q in acquired for q, _, _, _ in flows]
    told = [q in stated for q, _, _, _ in flows]
    out = []
    for i in range(4, len(flows)):
        win = range(i - 3, i + 1)
        avg = None if any(blank[k] for k in win) else sum(bal[k] for k in win) / 4
        unbroken = all(follows[k] for k in win)
        complete = unbroken and all(flows[k][1] is not None for k in win)
        g = sum(flows[k][1] for k in win) if complete else None
        rc = sum(flows[k][2] for k in win) if complete else None
        jumped = []
        if not unbroken:
            why = WHY_MISSING
        elif any(blank[k] for k in range(max(0, i - 5), i + 1)):
            why = WHY_NOT_FILED
        else:
            jumped = [label(flows[k][0]) for k in range(i - 4, i + 1) if moved[k]]
            if any(bought[k] for k in win):
                rest = WHY_ACQUIRED
            elif any(told[k] for k in win):
                rest = WHY_STATED
            elif not ((avg >= min_book or exempt_min_book) and avg > 0):
                rest = WHY_SMALL
            elif not complete:
                rest = WHY_MISSING
            else:
                rest = None
            why = WHY_JUMP if jumped else rest
        kept = why is None
        out.append({
            "quarter": label(flows[i][0]),
            "gross_rate": 100 * g / avg if kept else None,
            "net_rate": 100 * (g - rc) / avg if kept else None,
            "gross": g, "recoveries": rc, "avg_balance": avg,
            "kept": kept, "why": why,
            "jumped": jumped if why == WHY_JUMP else [],
            "why_without_jump": rest if why == WHY_JUMP else why,
        })
    return out


def _yyyymmdd(quarter: str) -> str:
    return quarter_end(quarter).replace("-", "")


def _links_by_quarter(links: Sequence[dict]) -> Dict[Tuple[str, str], List[str]]:
    """``{(acquirer, YYYYMMDD): [absorbed]}`` from ``fdic.absorptions`` rows."""
    out: Dict[Tuple[str, str], List[str]] = {}
    for ln in links:
        key = (str(ln["acquirer"]), _yyyymmdd(ln["quarter"]))
        if str(ln["absorbed"]) not in out.setdefault(key, []):
            out[key].append(str(ln["absorbed"]))
    return out


def repeated_ytd(data: Dict[str, list], links: Sequence[dict],
                 products: Sequence[str]) -> List[dict]:
    """``repeated_ytd_fields`` for the charge-off and recovery fields of
    ``products``."""
    return repeated_ytd_fields(data, links, raw_fields(f for p in products for f in _fields(p)[1:]))


def repeated_ytd_fields(data: Dict[str, list], links: Sequence[dict],
                        fields: Sequence[str]) -> List[dict]:
    """The year-to-date amounts a survivor's filing repeats after absorbing a
    bank under common control, read from the filings:
    ``[{acquirer, absorbed, quarter, field, amount}]``, ``quarter`` YYYYMMDD.

    The Call Report instructions (Glossary, "Business Combinations",
    transactions between entities under common control) have the survivor
    report the combined year to date, so its year-to-date charge-offs and
    recoveries already carry what the absorbed bank filed itself earlier in
    the year. Year-to-date differencing would count that twice (the
    comparability tie-out, 14 Oct 2026: six card quarters, $74m to $4.8bn).

    A link counts when its quarter is in the data and is not a Q1 (a Q1
    year-to-date starts afresh); the quarter before is in the data; both banks
    filed that quarter and only the acquirer files the merger quarter; and
    both carry the same, non-blank parent (``PARENT``) in the quarter before.
    That parent is the filed fact that says common control. A row without the
    field was pulled without it: refused, never read as a different parent.
    Each repeated amount is the absorbed bank's year-to-date at its last
    filing, for every year-to-date field in ``fields``."""
    qs, snap = _by_cert(data)
    out = []
    for (acq, q), absorbed in sorted(_links_by_quarter(links).items()):
        if q not in snap or q[4:6] == "03":
            continue
        i = qs.index(q)
        if not i or not _follows(qs[i - 1], q):
            continue
        prev = snap[qs[i - 1]]
        a_prev, a_now = prev.get(acq), snap[q].get(acq)
        if a_prev is None or a_now is None:
            continue
        for b in absorbed:
            b_prev = prev.get(b)
            if b_prev is None or b in snap[q]:
                continue
            for who, row in ((acq, a_prev), (b, b_prev)):
                if PARENT not in row:
                    raise ValueError(
                        "certificate %s, %s: no %s (holding company), so whether %s absorbed %s "
                        "under common control cannot be read. Pull again with refresh"
                        % (who, qs[i - 1], PARENT, acq, b))
            pa, pb = str(a_prev[PARENT] or "").strip(), str(b_prev[PARENT] or "").strip()
            if not pa or pa == "0" or pa != pb:
                continue
            for f in fields:
                amt = _num(b_prev, f)
                if amt:
                    out.append({"acquirer": acq, "absorbed": b, "quarter": q, "field": f,
                                "amount": amt})
    return out


def without_repeats(data: Dict[str, list], repeats: Sequence[dict]) -> Dict[str, list]:
    """``data`` with each repeated amount taken off the survivor's
    year-to-date, in the merger quarter and every later quarter of the same
    calendar year, so every flow measured from it counts each dollar once.

    Where the survivor's own year to date ``restarted`` (a new parent), the
    restarted figure never held the absorbed bank's amounts: nothing is taken
    off from that quarter on, and nothing at all when it restarted in the
    merger quarter itself. Whether a filing restarted is decided on the
    filings as filed and kept on the rows changed, so a reduced year to date
    is never read as a fall. The rows changed are copies; ``data`` itself is
    not touched."""
    if not repeats:
        return data
    qs, snap = _by_cert(data)
    out = {q: list(rows) for q, rows in data.items()}
    pos = {q: {str(r["CERT"]): k for k, r in enumerate(rows)} for q, rows in data.items()}

    def raw_restart(cert, i):
        if i == 0 or not _follows(qs[i - 1], qs[i]) or qs[i][4:6] == "03":
            return False
        row, prev = snap[qs[i]].get(cert), snap[qs[i - 1]].get(cert)
        return bool(row and prev) and restarted(row, prev)

    for rp in repeats:
        cert = rp["acquirer"]
        for i, q in enumerate(qs):
            if q[:4] != rp["quarter"][:4] or q < rp["quarter"]:
                continue
            if raw_restart(cert, i):
                k = pos[q].get(cert)
                if k is not None:
                    out[q][k] = dict(out[q][k], **{_RESTARTED: True})
                break
            k = pos[q].get(cert)
            if k is None:
                continue
            r = dict(out[q][k])
            if rp["field"] in NOT_FILED and _blank(r.get(rp["field"])):
                continue                    # not filed: nothing to take off
            r[rp["field"]] = _num(r, rp["field"]) - rp["amount"]
            r[_RESTARTED] = False           # raw_restart said no, for this quarter
            out[q][k] = r
    return out


def acquired_quarters(data: Dict[str, list], links: Sequence[dict], product: str,
                      share: float) -> Dict[str, List[str]]:
    """``{acquirer: [YYYYMMDD]}``: quarters whose recorded acquisitions,
    added together, brought in at least ``share`` of the acquirer's book of
    ``product`` (0.05 = 5%).

    Each absorbed bank's balance is read at its last filing before the merger
    quarter, and the acquirer's at the quarter before. Counted by acquirer
    and quarter, not bank by bank: eleven absorptions each under 5% can be
    16.5% together (PNC, 2007Q3, mortgage). An acquirer with no book the
    quarter before takes any book in as a whole one. An absorbed bank with no
    filing in the data cannot be measured and is skipped. An absorbed bank
    whose last filing leaves a commercial product's balance blank
    (``filed_amount``: not filed) brought in a book nobody filed: it is not
    read as no book, so the quarter is listed, since its share cannot be
    shown to be under ``share`` (for the owner-occupied split, every savings
    institution on the TFR, which never filed it). ``share`` is the firm's
    judgement, required, and refused below 0."""
    _at_least("share", share, 0)
    ln = _fields(product)[0]
    qs, snap = _by_cert(data)
    out: Dict[str, List[str]] = {}
    for (acq, q), absorbed in sorted(_links_by_quarter(links).items()):
        if q not in snap:
            continue
        before = qs[:qs.index(q)]
        if not before:
            continue
        a_prev = snap[before[-1]].get(acq)
        base = _num(a_prev, ln) if a_prev else 0.0
        brought = 0.0
        unknown = False
        for b in absorbed:
            last = next((snap[p][b] for p in reversed(before) if b in snap[p]), None)
            if last is not None:
                amount = filed_amount(last, ln)
                if amount is None:
                    unknown = True
                else:
                    brought += amount
        if unknown or (brought > 0 and (base <= 0 or brought / base >= share)):
            out.setdefault(acq, []).append(q)
    return out


def _quarters(books: Dict[str, List[dict]], certs: Sequence) -> List[str]:
    return sorted({r["quarter"] for c in certs for r in books[str(c)]})


def _index(books: Dict[str, List[dict]], certs: Sequence) -> Dict[str, Dict[str, dict]]:
    return {str(c): {r["quarter"]: r for r in books[str(c)]} for c in certs}


def composite(books: Dict[str, List[dict]], certs: Sequence, min_banks: int) -> List[dict]:
    """Per quarter, ``{quarter, gross_rate, net_rate, banks}``: the kept flows
    of the named banks summed, over their kept average balances summed, in %.
    Every dollar counts once, so a large book weighs more than a small one.
    The rates are None when fewer than ``min_banks`` banks are kept that
    quarter; ``min_banks`` below 1 is refused. ``books`` is
    ``{cert: bank_book(...)}``."""
    _at_least("min_banks", min_banks, 1)
    idx = _index(books, certs)
    out = []
    for q in _quarters(books, certs):
        rows = [idx[str(c)][q] for c in certs if q in idx[str(c)] and idx[str(c)][q]["kept"]]
        if len(rows) >= min_banks:
            G = sum(r["gross"] for r in rows)
            R = sum(r["recoveries"] for r in rows)
            B = sum(r["avg_balance"] for r in rows)
            g, n = 100 * G / B, 100 * (G - R) / B
        else:
            g = n = None
        out.append({"quarter": q, "gross_rate": g, "net_rate": n, "banks": len(rows)})
    return out


def _rate_key(kind: str) -> str:
    if kind not in ("gross", "net"):
        raise ValueError("kind must be 'gross' or 'net', not %r" % (kind,))
    return kind + "_rate"


def band(books: Dict[str, List[dict]], certs: Sequence, kind: str,
         pcts: Sequence[float] = (10, 25, 75, 90), *, min_banks: int) -> List[dict]:
    """Per quarter, ``{quarter, banks, p10, p25, ...}``: percentiles of the named
    banks' kept rates (``kind`` 'gross' or 'net'), each bank once, interpolated
    as Excel's PERCENTILE.INC does. None below ``min_banks`` kept banks.
    ``min_banks`` is required: how many banks make a band is a judgement, and
    below 1 it is refused."""
    _at_least("min_banks", min_banks, 1)
    key = _rate_key(kind)
    idx = _index(books, certs)
    out = []
    for q in _quarters(books, certs):
        vals = [idx[str(c)][q][key] for c in certs
                if q in idx[str(c)] and idx[str(c)][q]["kept"]]
        row = {"quarter": q, "banks": len(vals)}
        for p in pcts:
            row["p%g" % p] = percentile(vals, p) if len(vals) >= min_banks else None
        out.append(row)
    return out


def best_worst(books: Dict[str, List[dict]], certs: Sequence, kind: str,
               last_n: int = 20, min_obs: int = 12) -> Tuple[Optional[str], Optional[str]]:
    """``(best_cert, worst_cert)``: the lowest and the highest mean kept rate
    over the last ``last_n`` quarters, among banks with at least ``min_obs``
    kept values in those quarters. A tie goes to the bank named first. None
    for both when no bank qualifies. ``last_n`` or ``min_obs`` below 1 is
    refused (a ``last_n`` of 0 would otherwise read as every quarter)."""
    _at_least("last_n", last_n, 1)
    _at_least("min_obs", min_obs, 1)
    key = _rate_key(kind)
    idx = _index(books, certs)
    window = _quarters(books, certs)[-last_n:]
    means = []
    for c in certs:
        vals = [idx[str(c)][q][key] for q in window
                if q in idx[str(c)] and idx[str(c)][q]["kept"]]
        if len(vals) >= min_obs:
            means.append((sum(vals) / len(vals), str(c)))
    if not means:
        return None, None
    best = min(means, key=lambda m: m[0])[1]
    worst = max(means, key=lambda m: m[0])[1]
    return best, worst


def _counted(qs, snap, follows, i, cols) -> Dict[str, List[Tuple[str, str, str]]]:
    """Per filer in quarter ``qs[i]``, the field names of the products in
    ``cols`` whose figures are in the industry's sums that quarter: each
    product it filed (``not_filed``), less, where the quarter's flow is
    measured from the quarter before (not a Q1, and that quarter-end is in
    the data), any it filed there as blank: that flow is out, so its balance
    is out too. A filer absent the quarter before keeps its balance, as the
    earlier build counted it."""
    q = qs[i]
    prev = snap[qs[i - 1]] if i and follows[i] and q[4:6] != "03" else {}
    return {c: [f for p, f in cols if not not_filed(r, p) and not (c in prev and not_filed(prev[c], p))]
            for c, r in snap[q].items()}


def industry_filers(data: Dict[str, list], products: Sequence[str], quarter: str) -> int:
    """How many filers in ``quarter`` (``YYYYMMDD``, in ``data``) have figures
    of at least one of ``products`` in ``industry``'s sums that quarter: for
    a consumer product every filer, for a commercial one each that filed it
    (``_counted``). The denominator a series note states."""
    cols = [(p, _fields(p)) for p in dict.fromkeys(products)]
    qs, snap = _by_cert(data)
    if quarter not in snap:
        raise ValueError("%r is not a quarter in the data" % (quarter,))
    return sum(1 for fs in _counted(qs, snap, _contiguous(qs), qs.index(quarter), cols).values() if fs)


def industry(data: Dict[str, list], product: str,
             products: Optional[Sequence[str]] = None) -> List[dict]:
    """Per TTM quarter, the aggregate of every bank in ``data``:
    ``{quarter, date, gross_rate, net_rate, gross, recoveries, avg_balance}``.

    Each quarter's flow is summed bank by bank: a Q1 flow is its year-to-date;
    a later quarter counts only banks present in both it and the quarter
    before, so a bank that did not file is left out rather than counted as a
    negative. Balances are the quarter-end sums over every bank filing. TTM is
    100 x the sum of four flows / the mean of four balance sums, gross and net;
    the first TTM quarter is the fourth with a flow. ``products`` adds further
    products into the same sums (other consumer plus auto); ``product`` is
    always included, and a product named twice still counts once.

    A quarter with no filer at all has no flow (it is not a quarter of zero
    charge-offs), and neither has a later quarter measured from it; a window
    that is not four consecutive quarter-ends is not written.

    For a commercial product, a filer that left a field of it blank
    (``not_filed``) is left out of that quarter's balance and flow, and out
    of the next quarter's flow, which is measured from it, and so out of that
    quarter's balance too: the denominator holds the banks whose flows are in
    the numerator (``_counted``). A quarter in which no filer filed one of
    the products has no flow, like a quarter with no filer at all, so a
    product filed from 2007Q1 starts there and not as years of zeros, and a
    sum of products starts where every one of them is filed, never as one of
    them alone under the names of all."""
    names = []
    for p in [product] + list(products or ()):
        if p not in names:
            names.append(p)
    cols = [(p, _fields(p)) for p in names]
    qs, snap = _by_cert(data)
    follows = _contiguous(qs)

    def filed(rows):
        rows = list(rows)
        return all(any(not not_filed(r, p) for r in rows) for p, _ in cols)

    flows, bals = [], []
    for i, q in enumerate(qs):
        cur = snap[q]
        counted = _counted(qs, snap, follows, i, cols)
        bals.append(sum(_num(cur[c], f[0]) for c, fs in counted.items() for f in fs))
        if not cur or not filed(cur.values()):
            g = rc = None
        elif q[4:6] == "03":
            g = sum(_num(cur[c], f[1]) for c, fs in counted.items() for f in fs)
            rc = sum(_num(cur[c], f[2]) for c, fs in counted.items() for f in fs)
        elif follows[i] and snap[qs[i - 1]] and filed(snap[qs[i - 1]].values()):
            prev = snap[qs[i - 1]]
            both = [c for c in cur if c in prev]
            g = sum(flow(cur[c], prev[c], f[1]) for c in both for f in counted[c])
            rc = sum(flow(cur[c], prev[c], f[2]) for c in both for f in counted[c])
        else:
            g = rc = None
        flows.append((g, rc))
    out = []
    for i in range(3, len(qs)):
        win = range(i - 3, i + 1)
        if any(flows[k][0] is None for k in win) or not all(follows[k] for k in win[1:]):
            continue
        avg = sum(bals[k] for k in win) / 4
        g = sum(flows[k][0] for k in win)
        rc = sum(flows[k][1] for k in win)
        out.append({
            "quarter": label(qs[i]), "date": quarter_end(qs[i]),
            "gross_rate": 100 * g / avg if avg > 0 else None,
            "net_rate": 100 * (g - rc) / avg if avg > 0 else None,
            "gross": g, "recoveries": rc, "avg_balance": avg,
        })
    return out


def balance_path(rows: Sequence[dict], quarters: int) -> Optional[str]:
    """One note line on where a bank's book has gone over its last
    ``quarters`` TTM quarters, from ``bank_book`` rows: the four-quarter
    average balance at both ends, the change, and in how many of the
    quarters it fell. None when fewer quarters are held. It states the path
    and draws no line for what counts as a shrinking book: a rate rising
    while the balance falls may be the balance, not the risk. Where a
    window among them has no average balance (a commercial field not filed,
    ``bank_book``), the path is not stated, and the line says why."""
    _at_least("quarters", quarters, 2)
    if len(rows) < quarters:
        return None
    last = rows[-quarters:]
    gaps = [r["quarter"] for r in last if r["avg_balance"] is None]
    if gaps:
        return ("Book: no four-quarter average balance in %s (a field of the product not filed), so its "
                "path over the last %d quarters is not stated" % (", ".join(gaps), quarters))
    a, b = last[0]["avg_balance"], last[-1]["avg_balance"]
    fell = sum(1 for x, y in zip(last, last[1:]) if y["avg_balance"] < x["avg_balance"])
    change = "%+.1f%%" % (100 * (b / a - 1)) if a > 0 else "from none"
    return ("Book: four-quarter average balance %s ($000) at %s, %s at %s (%s); it fell in %d of the "
            "%d quarters since. A rate rising while the balance falls can be the balance, not the risk"
            % ("{:,.0f}".format(a), last[0]["quarter"], "{:,.0f}".format(b), last[-1]["quarter"], change,
               fell, quarters - 1))


def write_series(rows: Iterable[tuple], path, note) -> Path:
    """Write ``(quarter, value)`` pairs as the ``date,value`` CSV the workbook
    reads: quarter-end ISO dates, the note as ``#`` lines first. A quarter
    whose value is None is not written and is named in a closing note line,
    so a gap is stated rather than filled. Every line of the note is a ``#``
    line, a line break inside one note item included. The same quarter given
    twice, in any spelling, is refused. Returns the path."""
    path = Path(path)
    items = note if isinstance(note, (list, tuple)) else [note]
    lines = [ln for item in items for ln in str(item).splitlines()]
    kept, left_out, seen = [], [], set()
    for q, v in rows:
        d = quarter_end(q)
        if d in seen:
            raise ValueError("quarter %s is given twice (as %r)" % (d, q))
        seen.add(d)
        if v is None:
            left_out.append(d)
        else:
            kept.append((d, float(v)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        for line in lines:
            fh.write("# %s\n" % line)
        if left_out:
            fh.write("# no value, so not written: %s\n" % ", ".join(left_out))
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["date", "value"])
        for d, v in kept:
            w.writerow([d, repr(v)])
    return path
