"""Pull every FDIC filer's quarter, cache it, and read the merger record.

Public data only: the FDIC BankFind API. Nothing from KeyBank's books.

    financials  https://banks.data.fdic.gov/api/financials -- one request per
                quarter-end REPDTE (YYYYMMDD), every filer, 10,000 rows a page.
                A row is a dict: CERT, REPDTE and the fields asked for. Amounts
                are $ thousands; DR* and CR* are year-to-date, LN* quarter-end.
    history     https://banks.data.fdic.gov/api/history -- structure changes.
                Which quarters a whole-bank acquisition makes uncomparable.

The rules, as the earlier pull scripts applied them (pull_peers_2006.py and
pull_mergers_2006.py in the 6 Oct 2026 evidence pack), tightened on 12 Oct 2026:

- A quarter on disk (``cache_dir/q{YYYYMMDD}.json``) is never fetched again
  unless ``refresh`` is asked for. Only the missing quarters are fetched.
- A page of 10,000 rows means there may be another; a shorter page is the last.
  Pages are asked for in a fixed sort order, so offset paging cannot reshuffle
  rows between pages. When the API states a total, the rows must add up to it
  and the total must not change between pages; no row may arrive twice (by
  CERT for a quarter, by ID for history). Otherwise the pull refuses.
- A quarter with no filers at all is one the FDIC has not published yet. It is
  refused and never cached, so it cannot stand in for the quarter later.
- A failed request is tried 4 times in all, waiting 5, 10 and 15 seconds
  between attempts, and the 4th failure is raised, never swallowed.

Offline by construction: ``fetch`` is the downloader, ``fetch(url) -> dict``
(the parsed JSON). Nothing here opens a socket unless the default is used, and
every test passes a fake.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

FINANCIALS_URL = "https://banks.data.fdic.gov/api/financials"
HISTORY_URL = "https://banks.data.fdic.gov/api/history"
PAGE = 10000
ATTEMPTS = 4
BACKOFF_SECONDS = 5          # wait 5 x attempt number between attempts
TIMEOUT_SECONDS = 300
MAX_ROWS = 2000000           # no query here comes near it; past it, paging is broken
QUARTER_END = r"\d{4}(0331|0630|0930|1231)"

Fetch = Callable[[str], dict]


def urllib_fetch(url: str) -> dict:
    """The default downloader: one GET, a 300-second timeout, parsed JSON."""
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------- quarters

def quarter_ends(first: str, last: str) -> List[str]:
    """Every quarter-end REPDTE from ``first`` to ``last``, both included.

    ``quarter_ends("2006Q1", "2006Q3") -> ["20060331", "20060630", "20060930"]``.
    Refuses a label that is not ``YYYYQn`` or a range that runs backwards.
    """
    def parse(label: str):
        m = re.fullmatch(r"(\d{4})Q([1-4])", str(label))
        if not m:
            raise ValueError("a quarter is written like 2006Q1, not %r" % (label,))
        return int(m.group(1)), int(m.group(2))

    y, q = parse(first)
    ly, lq = parse(last)
    if (y, q) > (ly, lq):
        raise ValueError("first quarter %s is after last quarter %s" % (first, last))
    out = []
    while (y, q) <= (ly, lq):
        out.append("%04d%s" % (y, ("0331", "0630", "0930", "1231")[q - 1]))
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


# ---------------------------------------------------------------- fetching

def _with_retry(fetch: Fetch, url: str, sleep: Callable[[float], None]) -> dict:
    """``fetch(url)``, tried ATTEMPTS times with a growing wait; the last
    failure is raised. Any exception is retried, a cut-off JSON body
    (ValueError) as much as a dropped connection (OSError)."""
    for attempt in range(ATTEMPTS):
        try:
            return fetch(url)
        except Exception:                                   # noqa: BLE001
            if attempt == ATTEMPTS - 1:
                raise
            sleep(BACKOFF_SECONDS * (attempt + 1))
    raise AssertionError("unreachable")


def _total(payload: dict) -> Optional[int]:
    """The row count the API says the query has, when it says one."""
    total = (payload.get("meta") or {}).get("total")
    if isinstance(total, dict):
        total = total.get("value")
    return None if total is None else int(total)


def _paged(base: str, params: Dict[str, str], key: str, fetch: Fetch,
           sleep: Callable[[float], None]) -> List[dict]:
    """Every row of one query, 10,000 at a time, until a short page.

    Refuses, rather than return a result a sum could be silently wrong on:
    - a row count that differs from the total the API stated on the first page;
    - a stated total that changes between pages (the data moved mid-pull);
    - the same ``key`` (CERT, or history's ID) twice: pages overlapped, so some
      other row was lost while the count still added up;
    - more rows than stated, or than MAX_ROWS when no total is stated: paging
      that would otherwise never end.
    """
    rows: List[dict] = []
    seen = set()
    offset, stated = 0, None
    while True:
        query = dict(params, limit=str(PAGE), offset=str(offset), format="json")
        payload = _with_retry(fetch, base + "?" + urllib.parse.urlencode(query), sleep)
        got = [r.get("data", r) for r in payload.get("data", [])]
        total = _total(payload)
        if offset == 0:
            stated = total
        elif total != stated:
            raise RuntimeError(
                "the FDIC stated %s rows for %s, then %s on a later page: the "
                "data changed during the pull; pull again"
                % (stated, params.get("filters"), total))
        for row in got:
            k = row.get(key)
            if k is None:
                continue
            if k in seen:
                raise RuntimeError(
                    "%s %s arrived twice for %s: the pages overlapped, so another "
                    "row was lost; refusing the pull" % (key, k, params.get("filters")))
            seen.add(k)
        rows += got
        ceiling = MAX_ROWS if stated is None else stated
        if len(rows) > ceiling:
            raise RuntimeError(
                "more than %d rows arrived for %s: the paging is not ending; "
                "refusing the pull" % (ceiling, params.get("filters")))
        if len(got) < PAGE:
            break
        offset += PAGE
    if stated is not None and stated != len(rows):
        raise RuntimeError(
            "the FDIC stated %d rows for %s but %d arrived: refusing an "
            "incomplete pull" % (stated, params.get("filters"), len(rows)))
    return rows


def _field_list(fields: Union[str, Sequence[str]]) -> List[str]:
    """The fields asked for, always with CERT and REPDTE first, no repeats."""
    names = fields.split(",") if isinstance(fields, str) else list(fields)
    out = ["CERT", "REPDTE"]
    for name in (n.strip() for n in names):
        if name and name not in out:
            out.append(name)
    return out


def _write(path: Path, rows: List[dict]) -> None:
    """Write through a temporary file, so a crash never leaves half a quarter
    on disk to be read as the whole of it next time."""
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(rows), encoding="utf-8")
    os.replace(str(tmp), str(path))


def pull(quarters: Sequence[str], fields: Union[str, Sequence[str]],
         cache_dir: Union[str, Path], fetch: Optional[Fetch] = None,
         refresh: bool = False,
         sleep: Callable[[float], None] = time.sleep) -> Dict[str, List[dict]]:
    """``{REPDTE: rows}`` for every quarter, every filer, from cache or the API.

    ``cache_dir/q{REPDTE}.json`` is read when it exists and fetched (then
    written) when it does not, or for every quarter when ``refresh``. A cached
    quarter that holds none of a requested field was pulled for something else;
    it is refused with that reason rather than read as zeros.

    A quarter is a quarter-end REPDTE (``20240331``); anything else is refused
    before it becomes a filter or a file name. A quarter the FDIC returns no
    filers for is not published yet: it is refused and nothing is written, so
    a good cache is never overwritten with nothing and an empty quarter is
    never read later as a complete one. An empty cached quarter (one written
    before this rule) is refused the same way.
    """
    for q in quarters:
        if not re.fullmatch(QUARTER_END, str(q)):
            raise ValueError("a quarter is a quarter-end date written like "
                             "20240331, not %r" % (q,))
    names = _field_list(fields)
    fetch = fetch or urllib_fetch
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    out: Dict[str, List[dict]] = {}
    for q in quarters:
        path = cache / ("q%s.json" % q)
        if path.exists() and not refresh:
            rows = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(rows, list) or not rows:
                raise ValueError(
                    "%s holds no filers: the quarter was cached before the FDIC "
                    "published it. Delete the file, or pull again with refresh"
                    % path)
            absent = [f for f in names if not any(f in r for r in rows)]
            if absent:
                raise ValueError(
                    "%s has no %s: it was pulled with other fields. Pull again "
                    "with refresh, or use another cache folder"
                    % (path, ", ".join(absent)))
        else:
            rows = _paged(FINANCIALS_URL,
                          {"filters": "REPDTE:%s" % q, "fields": ",".join(names),
                           "sort_by": "CERT", "sort_order": "ASC"},
                          "CERT", fetch, sleep)
            if not rows:
                raise RuntimeError(
                    "the FDIC has no filers for %s: the quarter is not published "
                    "yet. Nothing was cached; pull it once it is" % q)
            _write(path, rows)
        out[q] = rows
    return out


# ---------------------------------------------------------------- mergers
#
# Copied, not imported, from credit-suite:
#   credit-suite/src/credit_suite/sources/fdic/mergers.py (ACQUISITIONS,
#   NOT_AN_ACQUISITION, FIELDS, quarter_end, classify), as of 12 Oct 2026.
# Each project must lift out whole, so threshold-engine carries its own copy.
# The why, from there: a quarterly flow is the year-to-date total less the
# previous quarter's, so in a quarter where a bank absorbed another it mixes
# two banks and is not a quarter of anything (Capital One, 2022Q4, 670%). The
# guard is the FDIC's own merger record, never a merger inferred from numbers.
# Like credit-suite, a row that cannot be classified is reported, never
# dropped: here classify gives the acquisitions and unrecognised gives the rest.

#: Whole-institution acquisitions: the acquirer's next filing covers a bank
#: that was not there before. An ALLOWLIST: a code not named here is not an
#: acquisition for this purpose. Codes and wording are the FDIC's own.
ACQUISITIONS: Dict[int, str] = {
    211: "Failure - Whole Institution",
    # Added 12 Oct 2026, after this module's own refusal caught it live (two
    # rows, 2008, neither acquirer on the roster). A failed bank's business
    # was split between several buyers, so each buyer's next filing carries a
    # piece of a bank it did not have. Marking it can only leave a quarter
    # out of a window; it never adds a number. credit-suite does not list it.
    215: "Failure Multiple Acquirer",
    216: "Bridge Bank Resolution",
    217: "Passthrough Receivorship/Conservatorship Resolution",
    221: "Absorbtion - Without Assistance",
    222: "Consolidated - Without Assistance",
    223: "Merger -Without Assistance",
    224: "Affiliated Institution Merger (Pooling)",
}

#: Events that name an acquirer but do NOT bring a whole bank onto the filing.
NOT_AN_ACQUISITION: Dict[int, str] = {
    712: "a branch purchase -- some offices changed hands, not a bank",
    810: "the mirror entry the FDIC writes against the acquirer for an "
         "absorption, consolidation or merger already counted above",
    811: "the mirror entry for an FDIC-assisted merger already counted above",
    812: "the mirror entry for an RTC-assisted merger already counted above",
}

FIELDS = ("CERT,EFFDATE,CHANGECODE,CHANGECODE_DESC,ACQ_CERT,OUT_CERT,"
          "OUT_NAME,PROCDATE")


def _is_date(text: str) -> bool:
    """True for a real calendar date written ``YYYY-MM-DD``."""
    text = str(text)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return False
    try:
        datetime.date(int(text[0:4]), int(text[5:7]), int(text[8:10]))
    except ValueError:
        return False
    return True


def quarter_end(iso_date: str) -> str:
    """The Call Report quarter an effective date falls in.

    ``2022-10-03 -> 2022-12-31``: the December filing is the first one that
    covers the combined bank, so December's flow is the contaminated one.
    Refuses anything that is not a real ``YYYY-MM-DD`` date.
    """
    if not _is_date(iso_date):
        raise ValueError("an effective date is written like 2022-10-03, not %r"
                         % (iso_date,))
    year, month = int(iso_date[0:4]), int(iso_date[5:7])
    end_month = ((month - 1) // 3) * 3 + 3
    last_day = {3: 31, 6: 30, 9: 30, 12: 31}[end_month]
    return "%04d-%02d-%02d" % (year, end_month, last_day)


def _code(row: dict) -> Optional[int]:
    try:
        return int(row.get("CHANGECODE"))
    except (TypeError, ValueError):
        return None


def _acquisition(row: dict) -> Optional[Tuple[str, str]]:
    """``(acquirer cert, quarter-end)`` for an allowlisted row that names its
    acquirer by certificate number and gives a real effective date; else None."""
    if _code(row) not in ACQUISITIONS:
        return None
    cert = str(row.get("ACQ_CERT") or "").strip()
    effective = str(row.get("EFFDATE") or "")[:10]
    if not (cert.isascii() and cert.isdigit()) or not _is_date(effective):
        return None
    return cert, quarter_end(effective)


def classify(rows: Sequence[dict]) -> Dict[str, List[str]]:
    """``{acquirer cert: [quarter-end ISO dates]}`` from FDIC history rows.

    A row counts only when its change code is on the ACQUISITIONS allowlist
    and it names the acquirer (ACQ_CERT) and a real effective date. Every
    other row is left out of this answer; :func:`unrecognised` lists the ones
    that are not a known non-acquisition, so they are reported, not lost.
    Each bank's quarters are sorted and listed once.
    """
    out: Dict[str, set] = {}
    for row in rows:
        hit = _acquisition(row)
        if hit:
            out.setdefault(hit[0], set()).add(hit[1])
    return {cert: sorted(qs) for cert, qs in sorted(out.items())}


def absorptions(rows: Sequence[dict]) -> List[dict]:
    """``[{acquirer, absorbed, quarter}]`` from FDIC history rows: who took in
    whom, and the quarter-end of the acquirer's first filing that covers both.

    The same allowlist as :func:`classify`; a row counts only when it also
    names the absorbed bank by certificate, OUT_CERT (a failure's row leaves
    CERT blank and fills OUT_CERT, so CERT is not read). Two uses read
    it, both against the filings in the cache: the share of a product's book
    an acquisition brought in, and, when the two banks had the same parent,
    the absorbed bank's year-to-date figures that the survivor's filing
    repeats. Sorted, each link once."""
    out = set()
    for row in rows:
        hit = _acquisition(row)
        absorbed = str(row.get("OUT_CERT") or "").strip()
        if hit and absorbed.isascii() and absorbed.isdigit() and absorbed != hit[0]:
            out.add((hit[1], hit[0], absorbed))
    return [{"acquirer": a, "absorbed": b, "quarter": q} for q, a, b in sorted(out)]


def unrecognised(rows: Sequence[dict]) -> List[dict]:
    """The rows :func:`classify` could not place: a change code on neither
    list, or an allowlisted code with no acquirer or no real effective date
    (credit-suite's ``unclassified``). Unknown is a third answer, to be shown
    to a person, not folded into "not a merger"."""
    return [r for r in rows
            if _code(r) not in NOT_AN_ACQUISITION and _acquisition(r) is None]


def pull_mergers(since: str, fetch: Optional[Fetch] = None,
                 sleep: Callable[[float], None] = time.sleep) -> Dict[str, List[str]]:
    """Every whole-bank acquisition by any filer effective on or after
    ``since`` (``YYYY-MM-DD``), classified: ``{cert: [quarter-ends]}``.
    :func:`history`'s rows, through :func:`classify`."""
    return classify(history(since, fetch, sleep))


def history(since: str, fetch: Optional[Fetch] = None,
            sleep: Callable[[float], None] = time.sleep) -> List[dict]:
    """Every FDIC history row effective on or after ``since`` that names an
    acquirer, once each row is known to be classifiable.

    One history query for every row since then that names an acquirer, paged
    and retried like :func:`pull`. It is deliberately NOT narrowed to the
    allowlisted codes: as in credit-suite, every code comes back, so a code on
    neither list is seen (that is how 216, the SVB bridge bank, was caught).
    If any row cannot be classified the pull refuses and names each one,
    because a merger nobody sees is a quarter nobody marks. What a new code
    means is a person's decision: add it to ACQUISITIONS or NOT_AN_ACQUISITION.
    """
    if not _is_date(since):
        raise ValueError("since is a date written like 2005-10-01, not %r" % (since,))
    params = {"filters": "EFFDATE:[%s TO *] AND ACQ_CERT:[1 TO *]" % since,
              "fields": FIELDS + ",ID",
              "sort_by": "EFFDATE", "sort_order": "ASC"}
    rows = _paged(HISTORY_URL, params, "ID", fetch or urllib_fetch, sleep)
    odd = unrecognised(rows)
    if odd:
        listed = "\n".join(
            "  code %s (%s), acquirer %s, effective %s"
            % (r.get("CHANGECODE"), r.get("CHANGECODE_DESC") or "no description",
               r.get("ACQ_CERT") or "not named",
               str(r.get("EFFDATE") or "not given")[:10])
            for r in odd)
        raise RuntimeError(
            "%d FDIC history row(s) since %s cannot be classified, so the merger "
            "record would be incomplete:\n%s\nOnce someone has decided what each "
            "code means, add it to ACQUISITIONS or NOT_AN_ACQUISITION in "
            "peers/fdic.py." % (len(odd), since, listed))
    return rows
