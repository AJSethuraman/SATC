"""Which quarters a merger makes uncomparable, from the FDIC's own record.

The incident, 4 September 2026. A chart drew Capital One's other-consumer
charge-off rate at **670%** for the quarter ending 31 December 2022. The firm
did not believe it and asked for the cause rather than a threshold::

    "it's just odd because that calc was all of a sudden really high and
     inconsistent with the others - it reads like an abnormality. make me
     believe you recognized the cause"

The cause is a merger. Capital One Bank (USA), N.A. (CERT 33954) merged into
Capital One, N.A. (CERT 4297) on 3 October 2022 -- FDIC history, change code
223. The Call Report reports charge-offs year-to-date, and the FDIC turns
that into a quarter by subtraction; in a merger quarter it subtracts *both*
banks' September totals from the merged bank's December total. Verified on
the card book, where the numbers are large enough to be certain::

    2,926,715 - 140,331 - 1,767,237 = 1,019,147 = the FDIC's own NTCRCDQ

The acquired bank reported no other-consumer book and no other-consumer
charge-offs of its own, yet the merged year-end total was $6.3M against the
survivor's $1.0M through September and a $0.3M-a-quarter run rate. The extra
$5.3M is that bank's activity landing in a category it never used under its
own name, divided by the survivor's $3.2M residual book.

So the number is arithmetically right and describes nothing. **A quarterly
flow that spans a merger is not a quarter of anything** -- and the guard has
to be the merger, not the size of the book: had the survivor carried a $500M
book the same $5.3M would have drawn a plausible 4.3% that nobody questioned.

This module reads the FDIC's merger record and says which quarters that makes
uncomparable. It never infers a merger from the numbers.

Offline by construction: ``fetch`` takes the downloader, so nothing here opens
a socket on its own and every test drives it with recorded rows.
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

HISTORY_URL = "https://banks.data.fdic.gov/api/history"

#: Whole-institution acquisitions: the acquiring bank's next filing covers a
#: bank that was not there before. An ALLOWLIST -- a code that is not named
#: here is never silently treated as "not a merger" (see :func:`classify`).
#: Codes and wording are the FDIC's own, observed live on 5 September 2026
#: across the twelve-bank peer set (870 history rows).
ACQUISITIONS: Dict[int, str] = {
    211: "Failure - Whole Institution",
    217: "Passthrough Receivorship/Conservatorship Resolution",
    221: "Absorbtion - Without Assistance",
    222: "Consolidated - Without Assistance",
    223: "Merger -Without Assistance",
    224: "Affiliated Institution Merger (Pooling)",
}

#: Events that name an acquirer but do NOT bring a whole bank onto the
#: filing. Named explicitly so an unrecognised code is genuinely unrecognised
#: rather than quietly lumped in with these.
NOT_AN_ACQUISITION: Dict[int, str] = {
    712: "a branch purchase -- some offices changed hands, not a bank",
    810: "the mirror entry the FDIC writes against the acquirer for an "
         "absorption, consolidation or merger already counted above",
    811: "the mirror entry for an FDIC-assisted merger already counted above",
    812: "the mirror entry for an RTC-assisted merger already counted above",
}

#: The plain sentence for each acquisition code. The firm, 5 September 2026:
#: "i dont know what RCON2200 means without looking it up so lets start
#: making things have plain definitions in addition to the code."
MEANING: Dict[int, str] = {
    211: "the FDIC closed a failing bank and this bank took it on",
    217: "a failed bank was resolved through a bridge arrangement and this "
         "bank took it on",
    221: "this bank absorbed another, with no regulator assistance",
    222: "two banks were combined into this one, with no regulator assistance",
    223: "this bank merged another into itself, with no regulator assistance",
    224: "this bank merged in an affiliate under the same parent",
}

FIELDS = ("CERT,EFFDATE,CHANGECODE,CHANGECODE_DESC,ACQ_CERT,OUT_CERT,"
          "OUT_NAME,PROCDATE")


@dataclass(frozen=True)
class Merger:
    """One whole-bank acquisition, and the quarter whose flows it spans."""

    cert: str                 # the surviving bank, the one we monitor
    effective: str            # ISO date the FDIC recorded it as effective
    quarter: str              # ISO quarter-end whose flows are uncomparable
    out_cert: str             # the bank that disappeared
    out_name: str
    code: int
    description: str          # the FDIC's own wording

    @property
    def meaning(self) -> str:
        return MEANING.get(self.code, self.description)

    def sentence(self, bank: str = "") -> str:
        """One line a person can act on, with the jargon and its meaning."""
        who = ("%s " % bank) if bank else ""
        # the history endpoint leaves OUT_NAME empty, so the cert is often
        # all there is; do not print it twice when that is the case
        name = ("%s (CERT %s)" % (self.out_name, self.out_cert)
                if self.out_name else "CERT %s" % self.out_cert)
        return ("%squarter ending %s spans a merger: %s, effective %s. "
                "FDIC change code %d, \"%s\" -- %s. A quarterly flow is the "
                "year-to-date total less the previous quarter's, so across a "
                "merger it mixes two banks and is not a quarter of anything."
                % (who, self.quarter, name, self.effective,
                   self.code, self.description, self.meaning))


def quarter_end(iso_date: str) -> str:
    """The Call Report quarter an effective date falls in.

    ``2022-10-03 -> 2022-12-31``: the December filing is the first one that
    covers the combined bank, so December's flow is the contaminated one.
    """
    year, month = int(iso_date[0:4]), int(iso_date[5:7])
    end_month = ((month - 1) // 3) * 3 + 3
    last_day = {3: 31, 6: 30, 9: 30, 12: 31}[end_month]
    return "%04d-%02d-%02d" % (year, end_month, last_day)


def quarter_start(iso_date: str) -> str:
    """The first day of the quarter an ISO date falls in.

    The window to ask for. A merger on 1 July contaminates the quarter ending
    30 September, so asking from the quarter-END misses it by two months --
    which is exactly what happened to Citibank's July 2022 merger on the first
    live run.
    """
    year, month = int(iso_date[0:4]), int(iso_date[5:7])
    return "%04d-%02d-01" % (year, ((month - 1) // 3) * 3 + 1)


def classify(rows: Sequence[dict]) -> Tuple[List[Merger], List[dict]]:
    """Split FDIC history rows into acquisitions and rows we cannot classify.

    Returns ``(mergers, unclassified)``. A change code in neither list is
    **reported**, never dropped: "unknown" is a third answer, and a merger
    silently discarded is exactly the quarter this module exists to mark.
    """
    mergers: Dict[Tuple[str, str], Merger] = {}
    unclassified: List[dict] = []
    for row in rows:
        try:
            code = int(row.get("CHANGECODE"))
        except (TypeError, ValueError):
            unclassified.append(row)
            continue
        if code in NOT_AN_ACQUISITION:
            continue
        if code not in ACQUISITIONS:
            unclassified.append(row)
            continue
        cert = str(row.get("ACQ_CERT") or "").strip()
        effective = str(row.get("EFFDATE") or "")[:10]
        if not cert or len(effective) != 10:
            unclassified.append(row)
            continue
        merger = Merger(
            cert=cert, effective=effective, quarter=quarter_end(effective),
            out_cert=str(row.get("OUT_CERT") or "").strip(),
            out_name=(row.get("OUT_NAME") or "").strip(),
            code=code,
            description=(row.get("CHANGECODE_DESC") or
                         ACQUISITIONS[code]).strip())
        # one bank can file several rows for one event; keep one per date
        mergers.setdefault((cert, effective), merger)
    return sorted(mergers.values(), key=lambda m: (m.cert, m.effective)), unclassified


def by_cert(mergers: Sequence[Merger]) -> Dict[str, List[Merger]]:
    out: Dict[str, List[Merger]] = {}
    for merger in mergers:
        out.setdefault(merger.cert, []).append(merger)
    return out


def request_url(certs: Sequence[str], since: Optional[str] = None,
                limit: int = 1000) -> str:
    """The one history request for the whole peer set."""
    filters = "ACQ_CERT:(%s)" % " OR ".join(sorted(str(c) for c in certs if c))
    if since:
        filters += " AND EFFDATE:[%s TO *]" % since
    return HISTORY_URL + "?" + urllib.parse.urlencode({
        "filters": filters, "fields": FIELDS,
        "sort_by": "EFFDATE", "sort_order": "DESC",
        "limit": str(limit), "format": "json"})


def fetch(certs: Sequence[str], download: Callable[[str, str], bytes],
          since: Optional[str] = None, limit: int = 1000
          ) -> Tuple[List[Merger], List[dict]]:
    """One request for every bank's acquisitions. ``download`` is injected.

    Refuses a truncated page rather than reporting fewer mergers than exist:
    a merger this never saw is a quarter nothing marks, which is the whole
    failure being guarded against.
    """
    certs = [str(c) for c in certs if str(c).strip()]
    if not certs:
        return [], []
    url = request_url(certs, since=since, limit=limit)
    payload = json.loads(download(url, "history").decode("utf-8"))
    meta = payload.get("meta") or {}
    total = meta.get("total")
    if isinstance(total, dict):
        total = total.get("value")
    if total is not None and int(total) > limit:
        raise RuntimeError(
            "FDIC history reports %s rows for this peer set but the request "
            "limit is %d: refusing a truncated merger record, because a "
            "merger nobody sees is a quarter nobody marks. Narrow the peer "
            "list or raise the limit." % (total, limit))
    return classify([rec.get("data") or {} for rec in payload.get("data", [])])
