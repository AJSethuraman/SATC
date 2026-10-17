"""Delinquency and nonaccrual, by product, per bank, for the pack composite, the
band and the industry, from FDIC Call Report rows. docs/V1-ROUND2-SPEC.md,
section A, is the contract.

Input is ``{REPDTE: [rows]}`` as ``fdic.pull`` returns it, the same shape
``books.py`` reads. Every amount is **$ thousands at quarter-end**: the past-due
and nonaccrual fields (``P3*``, ``P9*``, ``NA*``) are stocks on the filing date,
not year-to-date flows, so nothing here is differenced between quarters.

=============== ========== ============ ================= ==========
Product         Balance    30-89 days   90+ days accruing Nonaccrual
=============== ========== ============ ================= ==========
Credit card     LNCRCD     P3CRCD       P9CRCD            NACRCD
Mortgage        LNRERSFM   P3RERSFM     P9RERSFM          NARERSFM
Home equity     LNRELOC    P3RELOC      P9RELOC           NARELOC
Other consumer  LNCONOTH   P3CONOTH     P9CONOTH          NACONOTH
Auto            LNAUTO     P3AUTO       P9AUTO            NAAUTO
C&I             LNCI       P3CI         P9CI              NACI
Construction    LNRECONS   P3RECONS     P9RECONS          NARECONS
Multifamily     LNREMULT   P3REMULT     P9REMULT          NAREMULT
Nonfarm nonres  LNRENRES   P3RENRES     P9RENRES          NARENRES
... owner-occ.  LNRENROW   P3RENROW     P9RENROW          NARENROW
... other       LNRENROT   P3RENROT     P9RENROT          NARENROT
=============== ========== ============ ================= ==========

(The last three are "Nonfarm nonresidential", "Owner-occupied nonfarm
nonresidential" and "Other nonfarm nonresidential".)

First quarter each field is filed. Probed against the live API
(``https://api.fdic.gov/banks/financials``, filter ``FIELD:[* TO *]``,
sorted by REPDTE ascending, every filer) on **12 Oct 2026**. "Filed" means at
least one filer has a value that quarter; 1984Q1 is the first quarter the API
holds at all, so a field shown as 1984Q1 may have been filed earlier:

- Credit card: P3CRCD 2001Q1; P9CRCD 1984Q1; NACRCD 1984Q1 (LNCRCD 1984Q1).
- Mortgage: P3RERSFM, P9RERSFM and NARERSFM 2002Q1 (LNRERSFM 1991Q1).
- Home equity: P3RELOC 2001Q1; P9RELOC 1991Q1; NARELOC 1991Q1 (LNRELOC 1987Q4).
- Other consumer: P3CONOTH 2001Q1; P9CONOTH 1984Q1; NACONOTH 1984Q1
  (LNCONOTH 1984Q1). Auto was inside other consumer until it was split out.
- Auto: P3AUTO, P9AUTO and NAAUTO 2011Q1 (LNAUTO 2011Q1).

The commercial products, from docs/commercial-2026-10/research-fdic.md (on
main), probed the same way on **16 Oct 2026** (any filer, first value):

- C&I: P3CI 2001Q1; P9CI 1984Q1; NACI 1984Q1 (LNCI 1984Q1).
- Construction: P3RECONS 2001Q1; P9RECONS 1986Q1; NARECONS 1986Q1
  (LNRECONS 1984Q1).
- Multifamily: P3REMULT 2001Q1; P9REMULT 1991Q1; NAREMULT 1991Q1
  (LNREMULT 1984Q1).
- Nonfarm nonresidential: P3RENRES 2001Q1; P9RENRES 1991Q1; NARENRES 1991Q1
  (LNRENRES 1984Q1).
- Owner-occupied and other nonfarm nonresidential: every field 2007Q1
  (LNRENROW, LNRENROT 2007Q1), and never filed by savings institutions that
  filed the TFR (the FDIC: "This item was not available for TFR Reporters").

So a measure that uses the 30-89 field (``30-89`` and ``30+ incl.
nonaccrual``) starts in 2001Q1 for cards, home equity and other consumer,
2002Q1 for mortgage and 2011Q1 for auto, 2001Q1 for the four commercial
totals and 2007Q1 for the two nonfarm splits. Before that the field is blank, and a
blank field is **not filed**, never 0: the rate is None and ``why`` names the
field. (``books.py`` counts a blank as 0 because the earlier build did; there
is no earlier build of delinquency to reproduce, so nothing is filled in.)

The measures. All five are built; which one the bank reports is its choice:

=======================  ====================
Measure key              Numerator
=======================  ====================
``30-89``                P3
``90+ accruing``         P9
``nonaccrual``           NA
``90+ incl. nonaccrual`` P9 + NA
``30+ incl. nonaccrual`` P3 + P9 + NA
=======================  ====================

Two bases:

- **quarter-end**: ``100 x numerator / balance``, both from the same filing;
- **four-quarter average**: the mean of the four quarter-end rates i-3..i,
  only when all four are present and are four consecutive quarter-ends.

The rules:

- A bank's quarter-end rate is None when it has no row that quarter, when its
  balance is blank, 0 or below, when its balance is under ``min_book`` and it
  is not exempt, or when a numerator field is blank. ``why`` says which.
- A quarter-end rate is a ratio from one filing, so an acquisition does not
  mix two banks into it, and the jump rule does not apply to it. A
  four-quarter average spans four filings, so it takes the jump rule as
  ``books.bank_book`` applies it, over the window i-3..i: if any quarter k from
  i-2 to i moved its balance by more than ``jump`` against k-1
  (``|b_k / b_(k-1) - 1| > jump``, or from 0 to above 0), the average is None
  and ``why_avg4`` names the quarter and the move.
- ``jump``, ``min_book`` and the exemption are judgements, so all three are
  required arguments with no default, as is ``min_banks`` for a composite or
  band.
- Composite over a set of certs: the summed numerators over the summed
  balances of the banks kept that quarter, with the number of banks in; None
  below ``min_banks``. A bank not kept, or missing, is left out of both sums,
  never counted as 0. Its four-quarter average at i is the mean of four
  composite quarter-end rates i-3..i, each recomputed **without the banks
  whose own four-quarter average at i the jump blanked** (an acquirer
  mid-merger), so on that basis the composite and the band are built from
  the same banks. Decided by the bank, 12 Oct 2026 (LOG.md): *"removing them
  makes sense"*. Each composite row names the banks this left out, in
  ``avg4_left_out``, and the notes and the Glossary say so.
- A composite or band takes each cert once: a cert named twice is refused, not
  counted twice. A band percentile outside 0..100 is refused.
- An amount that is not a finite number (NaN, infinity: ``json.loads`` reads a
  bare ``NaN``) is refused, naming the bank, the quarter and the field; it is
  neither kept nor read as not filed.
- Band: percentiles 10/25/75/90 of the kept bank rates on the basis asked
  for, interpolated as Excel's PERCENTILE.INC (``profile.percentile``).
- Industry: every filer in ``data``, summed numerators over summed balances,
  quarter-end. A filer counts when it filed the balance and every numerator
  field of the measure. The four-quarter average is the mean of the four
  industry quarter-end rates.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..profile import percentile
from .books import _at_least, _by_cert, _contiguous, label, members, parts, quarter_end, raw_fields

#: Product -> (balance, 30-89 days past due, 90+ days still accruing,
#: nonaccrual) field names. All quarter-end, $ thousands.
FIELDS = {
    "Credit card": ("LNCRCD", "P3CRCD", "P9CRCD", "NACRCD"),
    "Mortgage": ("LNRERSFM", "P3RERSFM", "P9RERSFM", "NARERSFM"),
    "Home equity": ("LNRELOC", "P3RELOC", "P9RELOC", "NARELOC"),
    "Other consumer": ("LNCONOTH+LNCONRP", "P3CONOTH", "P9CONOTH", "NACONOTH"),
    "Auto": ("LNAUTO", "P3AUTO", "P9AUTO", "NAAUTO"),
    "C&I": ("LNCI", "P3CI", "P9CI", "NACI"),
    "Construction": ("LNRECONS", "P3RECONS", "P9RECONS", "NARECONS"),
    "Multifamily": ("LNREMULT", "P3REMULT", "P9REMULT", "NAREMULT"),
    "Nonfarm nonresidential": ("LNRENRES", "P3RENRES", "P9RENRES", "NARENRES"),
    "Owner-occupied nonfarm nonresidential": ("LNRENROW", "P3RENROW", "P9RENROW", "NARENROW"),
    "Other nonfarm nonresidential": ("LNRENROT", "P3RENROT", "P9RENROT", "NARENROT"),
}

#: What a product's delinquency notes must say about its definition, where
#: it differs from the charge-off series' (``books.DEFINITIONS``).
DEFINITIONS = {
    "Other consumer": ("Other consumer's balance is RC-C 6.b, other revolving credit plans (LNCONRP), plus "
                       "6.d (LNCONOTH), matching its past-due lines (RC-N 5.c), which include those plans. "
                       "The FDIC data has no 6.b before 2001Q1, so no other consumer delinquency rate is "
                       "written before then. Auto was inside 6.d until 2011Q1, when it got its own line "
                       "(6.c)."),
}

#: Measure key -> which of (p3, p9, na) make its numerator.
MEASURES = {
    "30-89": ("p3",),
    "90+ accruing": ("p9",),
    "nonaccrual": ("na",),
    "90+ incl. nonaccrual": ("p9", "na"),
    "30+ incl. nonaccrual": ("p3", "p9", "na"),
}

#: Basis -> the key in a row that holds the value on that basis.
BASES = {"quarter-end": "rate", "four-quarter average": "avg4"}

WHY_ABSENT = "the bank did not file this quarter"
WHY_NO_BOOK = "no book (balance 0 or below)"
WHY_SMALL = "book under the minimum"
WHY_BLANK = "not filed this quarter: %s is blank"
#: Every jump reason in ``why_avg4`` starts with this.
WHY_JUMP_PREFIX = "book moved more than the jump in this window"
WHY_JUMP = WHY_JUMP_PREFIX + ": %s %+.1f%% against the quarter before"
WHY_JUMP_FROM_ZERO = WHY_JUMP_PREFIX + ": %s from 0 to above 0"
WHY_ACQUIRED_PREFIX = "an acquisition brought in at least the acquisition share in this window"
WHY_ACQUIRED = WHY_ACQUIRED_PREFIX + ": %s"
#: A bank whose own four-quarter average is blanked for one of these reasons
#: is left out of the composite's four-quarter average for that quarter.
LEFT_OUT = (WHY_JUMP_PREFIX, WHY_ACQUIRED_PREFIX)
WHY_FEWER_THAN_FOUR = "fewer than four consecutive quarter-ends in the data"
WHY_RATE_MISSING = "a quarter-end rate in the window is None: %s (%s)"


def fields_for(products: Iterable[str]) -> List[str]:
    """Every delinquency field (balance, P3, P9, NA) of the products named, in
    table order, each once, so ``peers pull`` can add them to its request.
    An unknown product is refused."""
    return raw_fields(f for p in products for f in _fields(p))


def _fields(product: str) -> Tuple[str, str, str, str]:
    """(balance, P3, P9, NA) fields; a combined product's are its parts'
    joined by "+" (``books.members``), and a sum with one part not filed is
    not filed (``_filed``)."""
    names = members(product)
    return tuple("+".join(FIELDS[n][k] for n in names) for k in range(4))


#: Said of every combined product's delinquency.
COMBINED = ("A combined product's delinquency is written only for quarters in which every part's fields "
            "were filed: auto's past-due and nonaccrual fields begin in 2011Q1.")


def _numerator_fields(product: str, measure: str) -> List[str]:
    if measure not in MEASURES:
        raise ValueError("measure must be one of %s, not %r" % (list(MEASURES), measure))
    _, p3, p9, na = _fields(product)
    named = {"p3": p3, "p9": p9, "na": na}
    return [named[k] for k in MEASURES[measure]]


def basis_key(basis: str) -> str:
    """'quarter-end' -> 'rate', 'four-quarter average' -> 'avg4'; anything else
    is refused."""
    if basis not in BASES:
        raise ValueError("basis must be one of %s, not %r" % (list(BASES), basis))
    return BASES[basis]


def _filed(row: dict, field: str) -> Optional[float]:
    """A filed amount, or None when the field is absent or blank (not filed).
    An amount that is not a finite number (NaN, infinity) is refused: it is
    neither a filing nor a blank, and NaN passes every comparison guard.
    A sum of fields (``"A+B"``) is filed when every part is; one blank part
    makes it blank, since the sum would be part of a book."""
    if "+" in field:
        vals = [_filed(row, f) for f in parts(field)]
        return None if any(v is None for v in vals) else sum(vals)
    v = row.get(field)
    if v is None or v == "":
        return None
    x = float(v)
    if not math.isfinite(x):
        raise ValueError("CERT %s, REPDTE %s: %s is %r, not a filed amount"
                         % (row.get("CERT"), row.get("REPDTE"), field, v))
    return x


def _amounts(row: dict, balance: str, nums: Sequence[str]):
    """(numerator, balance, the first blank field or None) for one filing."""
    bal = _filed(row, balance)
    vals = [_filed(row, f) for f in nums]
    blank = next((f for f, v in zip(nums, vals) if v is None), None)
    num = None if blank else sum(vals)
    if bal is None:                 # name the part not filed, not the sum
        blank = next((f for f in parts(balance) if _filed(row, f) is None), balance)
    return num, bal, blank


def _avg4(rates: Sequence[Optional[float]], follows: Sequence[bool], i: int) -> Optional[float]:
    """Mean of the rates at i-3..i when all four are present and consecutive."""
    if i < 3 or not all(follows[k] for k in range(i - 2, i + 1)):
        return None
    win = rates[i - 3:i + 1]
    if any(r is None for r in win):
        return None
    return sum(win) / 4


def bank_delinquency(data: Dict[str, list], cert, product: str, measure: str,
                     jump: float, min_book: float, exempt_min_book: bool, *,
                     acquired: Iterable[str]) -> List[dict]:
    """One row per quarter-end in ``data``: ``{q, numerator, balance, rate,
    avg4, kept, why, why_avg4}``, ``q`` labelled ``YYYYQn``.

    ``rate`` is ``100 x numerator / balance`` from the one filing, ``kept``
    whether it was computed, and ``why`` the reason it was not (first that
    applies: the bank did not file; the balance is blank; no book, 0 or below;
    under ``min_book`` and not ``exempt_min_book``; a numerator field is
    blank). ``avg4`` is the mean of the quarter-end rates i-3..i, None (with
    ``why_avg4``) when the four are not consecutive quarter-ends, when any
    quarter k in i-2..i moved its balance by more than ``jump`` against k-1,
    or when any of the four rates is None.

    ``jump`` (0.25 = 25%) and ``min_book`` ($ thousands) are judgements and
    are required; below 0 they are refused. ``exempt_min_book`` lifts the
    minimum for the bank drawn as itself and is required too, since whether a
    bank is exempt is also a judgement.

    ``acquired`` is the bank's quarter-ends (``YYYYMMDD``) in which recorded
    acquisitions brought in at least the acquisition share of its book
    (``books.acquired_quarters``): one in i-2..i blanks the average like a
    jump, never a quarter-end rate. Required; an empty list states none."""
    _at_least("jump", jump, 0)
    if isinstance(acquired, str):
        raise ValueError("acquired is a list of quarter-ends, not %r" % (acquired,))
    bought = {label(q) for q in acquired}
    _at_least("min_book", min_book, 0)
    if not isinstance(exempt_min_book, bool):
        raise ValueError("exempt_min_book must be True or False, not %r" % (exempt_min_book,))
    balance_field = _fields(product)[0]
    nums = _numerator_fields(product, measure)
    cert = str(cert)
    qs, snap = _by_cert(data)
    follows = _contiguous(qs)
    rows = []
    for q in qs:
        r = snap[q].get(cert)
        num = bal = None
        if r is None:
            why = WHY_ABSENT
        else:
            num, bal, blank = _amounts(r, balance_field, nums)
            if bal is None:                 # the balance, or a part of it, not filed
                why = WHY_BLANK % blank
            elif bal <= 0:
                why = WHY_NO_BOOK
            elif bal < min_book and not exempt_min_book:
                why = WHY_SMALL
            elif blank:
                why = WHY_BLANK % blank
            else:
                why = None
        rate = 100 * num / bal if why is None else None
        rows.append({"q": label(q), "numerator": num, "balance": bal, "rate": rate,
                     "avg4": None, "kept": why is None, "why": why, "why_avg4": None})
    rates = [r["rate"] for r in rows]
    for i, row in enumerate(rows):
        if i < 3 or not all(follows[k] for k in range(i - 2, i + 1)):
            row["why_avg4"] = WHY_FEWER_THAN_FOUR
            continue
        jumped = None
        for k in range(i - 2, i + 1):
            a, b = rows[k - 1]["balance"], rows[k]["balance"]
            if a is None or b is None:
                continue
            if a > 0 and abs(b / a - 1) > jump:
                jumped = WHY_JUMP % (rows[k]["q"], 100 * (b / a - 1))
                break
            if a == 0 and b > 0:
                jumped = WHY_JUMP_FROM_ZERO % rows[k]["q"]
                break
        if not jumped:
            hit = next((rows[k]["q"] for k in range(i - 2, i + 1) if rows[k]["q"] in bought), None)
            if hit:
                jumped = WHY_ACQUIRED % hit
        if jumped:
            row["why_avg4"] = jumped
            continue
        missing = next((k for k in range(i - 3, i + 1) if rates[k] is None), None)
        if missing is not None:
            row["why_avg4"] = WHY_RATE_MISSING % (rows[missing]["q"], rows[missing]["why"])
            continue
        row["avg4"] = _avg4(rates, follows, i)
    return rows


def _consecutive(labels: Sequence[str]) -> List[bool]:
    """Per position, True when that 'YYYYQn' straight follows the one before."""
    def n(lbl):
        return int(lbl[:4]) * 4 + int(lbl[5]) - 1
    return [False] + [n(b) == n(a) + 1 for a, b in zip(labels, labels[1:])]


def _distinct(certs: Sequence) -> None:
    """Refuse a cert named twice: it would be counted twice."""
    seen, twice = set(), []
    for c in certs:
        c = str(c)
        if c in seen and c not in twice:
            twice.append(c)
        seen.add(c)
    if twice:
        raise ValueError("certs must each be named once; named twice: %s" % ", ".join(twice))


def _quarters(books: Dict[str, List[dict]], certs: Sequence) -> List[str]:
    return sorted({r["q"] for c in certs for r in books[str(c)]})


def _index(books: Dict[str, List[dict]], certs: Sequence) -> Dict[str, Dict[str, dict]]:
    return {str(c): {r["q"]: r for r in books[str(c)]} for c in certs}


def composite_delinquency(books: Dict[str, List[dict]], certs: Sequence,
                          min_banks: int) -> List[dict]:
    """Per quarter, ``{q, numerator, balance, rate, banks, avg4, avg4_left_out}``
    for the named banks. ``books`` is ``{cert: bank_delinquency(...)}``, every
    bank on the same product and measure; ``certs`` names each bank once (a
    cert named twice is refused).

    ``rate`` is the kept banks' numerators summed over their balances summed,
    in %, so a large book weighs more than a small one; a bank not kept that
    quarter (missing, under the minimum, a blank field) is in neither sum.
    ``banks`` is how many were in. None below ``min_banks``, which is required
    and refused below 1.

    ``avg4`` at i is the mean of four composite rates i-3..i, only on four
    consecutive quarters, each rate recomputed over the banks kept that
    quarter less those whose own four-quarter average at i the jump blanked,
    and each needing ``min_banks``. ``avg4_left_out`` lists, in ``certs``
    order, the banks that took out: blanked by the jump at i and kept in at
    least one of the four quarters (a bank kept in none was never in)."""
    _at_least("min_banks", min_banks, 1)
    _distinct(certs)
    idx = _index(books, certs)

    def summed(q, leave_out=()):
        rows = [idx[str(c)][q] for c in certs
                if str(c) not in leave_out and q in idx[str(c)] and idx[str(c)][q]["kept"]]
        if len(rows) < min_banks:
            return None, None, None, len(rows)
        N = sum(r["numerator"] for r in rows)
        B = sum(r["balance"] for r in rows)
        return N, B, 100 * N / B, len(rows)

    out = []
    for q in _quarters(books, certs):
        N, B, rate, n = summed(q)
        out.append({"q": q, "numerator": N, "balance": B, "rate": rate,
                    "banks": n, "avg4": None, "avg4_left_out": []})
    follows = _consecutive([r["q"] for r in out])
    for i, r in enumerate(out):
        win = [o["q"] for o in out[max(0, i - 3):i + 1]]
        for c in certs:
            own = idx[str(c)]
            mine = own.get(r["q"])
            if (mine and (mine["why_avg4"] or "").startswith(LEFT_OUT)
                    and any(w in own and own[w]["kept"] for w in win)):
                r["avg4_left_out"].append(str(c))
        if i < 3 or not all(follows[k] for k in range(i - 2, i + 1)):
            continue
        rates = [summed(w, set(r["avg4_left_out"]))[2] for w in win]
        if all(x is not None for x in rates):
            r["avg4"] = sum(rates) / 4
    return out


def band_delinquency(books: Dict[str, List[dict]], certs: Sequence, basis: str,
                     pcts: Sequence[float] = (10, 25, 75, 90), *, min_banks: int) -> List[dict]:
    """Per quarter, ``{q, banks, p10, p25, p75, p90}``: percentiles of the named
    banks' rates on ``basis`` ('quarter-end' or 'four-quarter average'), each
    bank once, leaving out a bank whose value is None, interpolated as Excel's
    PERCENTILE.INC. None below ``min_banks``, which is required and refused
    below 1. A cert named twice, or a percentile outside 0..100, is refused."""
    _at_least("min_banks", min_banks, 1)
    _distinct(certs)
    for p in pcts:
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 100:
            raise ValueError("percentiles must be numbers from 0 to 100, not %r" % (p,))
    key = basis_key(basis)
    idx = _index(books, certs)
    out = []
    for q in _quarters(books, certs):
        vals = [idx[str(c)][q][key] for c in certs
                if q in idx[str(c)] and idx[str(c)][q][key] is not None]
        row = {"q": q, "banks": len(vals)}
        for p in pcts:
            row["p%g" % p] = percentile(vals, p) if len(vals) >= min_banks else None
        out.append(row)
    return out


def industry_delinquency(data: Dict[str, list], product: str, measure: str) -> List[dict]:
    """Per quarter-end in ``data``, ``{q, date, numerator, balance, rate, banks,
    avg4}`` for every filer: the numerators summed over the balances summed,
    in %. A filer counts when it filed the balance and every numerator field
    of the measure; ``banks`` is how many did. The rate is None when no filer
    counts or the summed balance is 0 or below. ``avg4`` is the mean of the
    four industry rates i-3..i, None unless all four are present on
    consecutive quarter-ends."""
    balance_field = _fields(product)[0]
    nums = _numerator_fields(product, measure)
    qs, snap = _by_cert(data)
    follows = _contiguous(qs)
    out = []
    for q in qs:
        N = B = 0.0
        n = 0
        for r in snap[q].values():
            num, bal, blank = _amounts(r, balance_field, nums)
            if blank:
                continue
            N += num
            B += bal
            n += 1
        rate = 100 * N / B if n and B > 0 else None
        out.append({"q": label(q), "date": quarter_end(q), "numerator": N if n else None,
                    "balance": B if n else None, "rate": rate, "banks": n, "avg4": None})
    rates = [r["rate"] for r in out]
    for i, r in enumerate(out):
        r["avg4"] = _avg4(rates, follows, i)
    return out


#: What the comparability tie-out (14 Oct 2026) found about comparing a
#: measure across banks. Each is stated in the notes of every series it
#: touches, so the Sources tab carries it; none changes a number.
POLICY = ("Across banks, read with care: whether a late consumer or 1-4 family loan stays accruing or "
          "goes to nonaccrual is partly each bank's policy (the Call Report allows both; at 30 Jun 2026, "
          "10 of the 16 roster banks filed zero card nonaccrual). Compare banks on 90+ incl. nonaccrual "
          "or 30+ incl. nonaccrual.")
GUARANTEED = ("Mortgage: past-due counts include government-guaranteed loans (rebooked GNMA, RC-N items 11 "
              "to 11.b), at no loss to the bank. At some peers they are most of first-lien 90+ accruing (up "
              "to 94-103%, an upper bound: the line is not split by loan type). Compare mortgage across "
              "banks on nonaccrual and charge-offs.")


def comparability(product: str, measure: str) -> List[str]:
    """The note lines on comparing ``product``'s ``measure`` across banks;
    empty when the tie-out found nothing to say."""
    if measure not in MEASURES:
        raise ValueError("measure must be one of %s, not %r" % (list(MEASURES), measure))
    lines = []
    if measure in ("90+ accruing", "nonaccrual"):
        lines.append(POLICY)
    if "Mortgage" in members(product) and "p9" in MEASURES[measure]:
        lines.append(GUARANTEED)
    return lines


def values(rows: Iterable[dict], basis: str) -> List[Tuple[str, Optional[float]]]:
    """``(q, value)`` pairs on ``basis`` from any of this module's row lists,
    the shape ``books.write_series`` takes."""
    key = basis_key(basis)
    return [(r["q"], r[key]) for r in rows]
