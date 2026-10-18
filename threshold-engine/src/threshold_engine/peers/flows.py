"""30+ to charge-off: of the dollars past due at a quarter-end, the share
charged off over the next two quarters. From FDIC Call Report rows, as
``fdic.pull`` returns them (``{REPDTE: [rows]}``, $ thousands).

The analyst, 17 Oct 2026, on the roll-rate work: *"looking at how much 30+
tracks with everyone else, and seems generally smooth i think that's our
choice. 30+ nonaccrual"*. The level is the inherent-risk reading (how much
delinquency turns into loss); the gap to the peer group and to the industry
is the relative reading (*"we would want to know when we are doing something
worse than peers relatively speaking"*).

Per bank and quarter-end q:

- delinquent = 30-89 days past due + 90+ days still accruing + nonaccrual,
  the three RC-N fields of the product at q, each read as filed (a blank is
  not filed, never 0, as ``delinquency`` reads them);
- charged off = the product's gross charge-offs (RI-B, year to date
  differenced as ``books.quarterly_flows`` does) in the two quarters after
  q, the bank's own filings only (not pro forma: the delinquency fields are
  the bank's own, so the charge-offs are too);
- rate = 100 x charged off / delinquent; avg4 = the mean of the rates at
  q-3..q, when all four exist on consecutive quarter-ends.

Why two quarters: a card charges off at 180 days past due and a closed-end
consumer loan at 120, so every dollar delinquent at q has either charged off
or left delinquency within two quarters. Not a tracked cohort: an aggregate
estimate of the waterfall, and for other consumer it also counts loans
charged off within two quarters that were current at q.

A quarter-end is not kept (``why`` says which, first that applies): the bank
did not file at q; a delinquency field is blank; no delinquent dollars; the
next two quarter-ends are not in the data, or the bank did not file them (a
flow needs both filings); the product's balance moved more than the jump
between q and q+2 (a sale or purchase moves charge-offs against the stock);
an acquisition quarter in q+1..q+2; a stated acquisition (one the FDIC
record cannot see, ``peers.stated``) in q+1..q+2. The jump, the acquisition
quarters and the stated acquisitions are the build's, as for every other
series.

The composite over a set of banks is the kept banks' charged-off summed over
their delinquent summed, needing at least ``min_banks`` banks; the industry
is the composite over every filer, with no minimum. The gap is one source's
avg4 less another's, same quarter, when both exist.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from . import delinquency as D
from .books import WHY_ACQUIRED, WHY_JUMP, WHY_STATED, _at_least, _by_cert, _contiguous, _flows, label

MEASURE = "30+ to charge-off"
GAP_PEERS = "Gap to peers on 30+ to charge-off"
GAP_INDUSTRY = "Gap to industry on 30+ to charge-off"
SLUG = "30-plus-to-charge-off"
WHY_ABSENT = D.WHY_ABSENT
WHY_NONE = "no delinquent dollars at the quarter-end"
WHY_NEXT_MISSING = "the next two quarter-ends are not both in the data"
WHY_NEXT_NOT_FILED = "the bank did not file both of the next two quarters"
WHY_FEWER_THAN_FOUR = D.WHY_FEWER_THAN_FOUR
WHY_TOO_FEW = "fewer than %d banks kept"

DEFINITION = ("30+ to charge-off: of the dollars 30-89 days past due, 90+ days past due and still accruing, and on "
              "nonaccrual at a quarter-end (RC-N, the three fields of the product), the share charged off, gross "
              "(RI-B, before recoveries), over the next two quarters, in %. A card charges off at 180 days past due "
              "and a closed-end consumer loan at 120, so every delinquent dollar has charged off or left delinquency "
              "within two quarters; one minus this share is the estimated cure. An aggregate estimate, not a tracked "
              "cohort: it also counts loans charged off within the two quarters that were current at the quarter-end. "
              "Each bank's own filings, not pro forma. The latest two quarter-ends have no value yet.")
DEFINITION_AVG4 = "Four-quarter average: the mean of the four quarter-end shares ending at the quarter, when all four exist."
DEFINITION_GAP = ("%s: %s's four-quarter average 30+ to charge-off less %s's, the same quarter, in percentage points. "
                  "Above zero, %s turns more of its delinquent dollars into loss than %s; below zero, less. A measure "
                  "with no floor at zero.")


def bank_flow(data: Dict[str, list], cert, product: str, jump: float, *, acquired: Iterable[str],
              stated: Iterable[str]) -> List[dict]:
    """One row per quarter-end in ``data``: ``{q, delinquent, charged_off,
    rate, avg4, kept, why, why_avg4}``, ``q`` labeled ``YYYYQn``.
    ``jump`` (0.25 = 25%), ``acquired`` (the bank's acquisition quarter-ends,
    ``YYYYMMDD``, as ``books.acquired_quarters`` gives them) and ``stated``
    (the bank's stated acquisitions' quarter-ends, ``YYYYMMDD``,
    ``peers.stated``; the firm, 17 Oct 2026, question 14: every product's
    windows holding one are left out, with their own reason) are required."""
    _at_least("jump", jump, 0)
    for name, v in (("acquired", acquired), ("stated", stated)):
        if isinstance(v, str):
            raise ValueError("%s is a list of quarter-ends, not %r" % (name, v))
    qs, snap = _by_cert(data)
    return _bank_flow(qs, snap, _contiguous(qs), str(cert), product, jump, {label(q) for q in acquired},
                      {label(q) for q in stated})


def industry(data: Dict[str, list], product: str) -> List[dict]:
    """The composite over every filer in ``data``: each bank's own flow
    (``bank_flow`` without the jump or acquisition rule, as the industry
    series have none), summed over the banks kept each quarter, no minimum.
    ``banks`` in each row says how many were kept."""
    qs, snap = _by_cert(data)
    follows = _contiguous(qs)
    certs = sorted({c for q in qs for c in snap[q]})
    books = {c: _bank_flow(qs, snap, follows, c, product, None, set(), set()) for c in certs}
    return composite(books, certs, 0)


def _bank_flow(qs, snap, follows, cert: str, product: str, jump: Optional[float], bought: set,
               told: set) -> List[dict]:
    flows = _flows(qs, snap, cert, product)                   # (q, gross, recoveries, balance), own filings
    _, p3, p9, na = D._fields(product)
    rows = []
    for i, q in enumerate(qs):
        r = snap[q].get(cert)
        delinquent = co = None
        why = None
        if r is None:
            why = WHY_ABSENT
        else:
            vals = [D._filed(r, f) for f in (p3, p9, na)]
            blank = next((f for f, v in zip((p3, p9, na), vals) if v is None), None)
            if blank:
                why = D.WHY_BLANK % blank
            else:
                delinquent = sum(vals)
                if delinquent <= 0:
                    why = WHY_NONE
                elif i + 2 >= len(qs) or not (follows[i + 1] and follows[i + 2]):
                    why = WHY_NEXT_MISSING
                elif flows[i + 1][1] is None or flows[i + 2][1] is None:
                    why = WHY_NEXT_NOT_FILED
                else:
                    moved = None
                    if jump is not None:
                        for k in (i + 1, i + 2):
                            a, b = flows[k - 1][3], flows[k][3]
                            if a is None or b is None:
                                continue
                            if (a > 0 and abs(b / a - 1) > jump) or (a == 0 and b > 0):
                                moved = WHY_JUMP
                                break
                    if moved:
                        why = moved
                    elif any(label(qs[k]) in bought for k in (i + 1, i + 2)):
                        why = WHY_ACQUIRED
                    elif any(label(qs[k]) in told for k in (i + 1, i + 2)):
                        why = WHY_STATED
                    else:
                        co = flows[i + 1][1] + flows[i + 2][1]
        rate = 100 * co / delinquent if why is None else None
        rows.append({"q": label(q), "delinquent": delinquent, "charged_off": co, "rate": rate, "avg4": None,
                     "kept": why is None, "why": why, "why_avg4": None})
    _fill_avg4(rows, follows)
    return rows


def _fill_avg4(rows: List[dict], follows: Sequence[bool]) -> None:
    rates = [r["rate"] for r in rows]
    for i, row in enumerate(rows):
        if i < 3 or not all(follows[k] for k in range(i - 2, i + 1)):
            row["why_avg4"] = WHY_FEWER_THAN_FOUR
            continue
        missing = next((k for k in range(i - 3, i + 1) if rates[k] is None), None)
        if missing is not None:
            row["why_avg4"] = D.WHY_RATE_MISSING % (rows[missing]["q"], rows[missing]["why"])
            continue
        row["avg4"] = sum(rates[i - 3:i + 1]) / 4


def composite(books: Dict[str, List[dict]], certs: Sequence, min_banks: int) -> List[dict]:
    """Per quarter-end, ``{q, delinquent, charged_off, rate, avg4, banks, kept,
    why, why_avg4}`` over ``certs``: the kept banks' charged-off summed over
    their delinquent summed, needing at least ``min_banks`` banks (0 for no
    minimum, the industry). ``books`` is ``{cert: bank_flow(...)}`` over the
    same quarter-ends."""
    if isinstance(min_banks, bool) or not isinstance(min_banks, int) or min_banks < 0:
        raise ValueError("min_banks must be a whole number, 0 or more, not %r" % (min_banks,))
    certs = [str(c) for c in certs]
    if not certs:
        return []
    qs = [r["q"] for r in books[certs[0]]]
    out = []
    for i, q in enumerate(qs):
        kept = [books[c][i] for c in certs if books[c][i]["kept"]]
        n = len(kept)
        if n < max(min_banks, 1):
            out.append({"q": q, "delinquent": None, "charged_off": None, "rate": None, "avg4": None, "banks": n,
                        "kept": False, "why": WHY_TOO_FEW % max(min_banks, 1), "why_avg4": None})
            continue
        dq = sum(r["delinquent"] for r in kept)
        co = sum(r["charged_off"] for r in kept)
        out.append({"q": q, "delinquent": dq, "charged_off": co, "rate": 100 * co / dq, "avg4": None, "banks": n,
                    "kept": True, "why": None, "why_avg4": None})
    follows = [True] + [_follows_label(qs[k - 1], qs[k]) for k in range(1, len(qs))]
    _fill_avg4(out, follows)
    return out


def _follows_label(prev: str, q: str) -> bool:
    a = int(prev[:4]) * 4 + int(prev[5]) - 1
    b = int(q[:4]) * 4 + int(q[5]) - 1
    return b == a + 1


def gap(mine: Sequence[dict], theirs: Sequence[dict]) -> List[dict]:
    """Per quarter-end, ``{q, avg4, kept, why}``: ``mine``'s four-quarter
    average less ``theirs``', or None with why when either has none."""
    by = {r["q"]: r for r in theirs}
    out = []
    for r in mine:
        o = by.get(r["q"])
        if r["avg4"] is None:
            why = "no four-quarter average of its own: %s" % r["why_avg4"]
        elif o is None or o["avg4"] is None:
            why = "no four-quarter average to take away: %s" % (o["why_avg4"] if o else "not in the data")
        else:
            why = None
        out.append({"q": r["q"], "avg4": (r["avg4"] - o["avg4"]) if why is None else None, "kept": why is None,
                    "why": why})
    return out


def values(rows: Iterable[dict], basis: str) -> List[tuple]:
    """``(q, value)`` pairs on ``basis`` ('quarter-end' or 'four-quarter
    average'), the shape ``books.write_series`` takes."""
    key = D.basis_key(basis)
    return [(r["q"], r[key]) for r in rows]
