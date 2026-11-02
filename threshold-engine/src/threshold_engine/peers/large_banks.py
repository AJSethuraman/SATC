"""The Federal Reserve Bank of Philadelphia's large bank credit card data: one
public CSV per quarter holding every quarter since 2012Q3, from the FR Y-14M
reports of the bank holding companies with $100 billion or more in assets.

Used for one measure the analyst chose (17 Oct 2026: *"let's officialize
using minimum payments"*): the share of active card accounts whose payment
in the quarter was only the minimum due. It is a count of accounts, not
dollars, across the panel's banks, so it is an industry reading; no public
figure gives it for one bank.

``pull`` fetches the quarter's file into ``cache/large-banks/``; the build
reads the file it is given and never fetches. The series file's notes carry
the file's name and SHA-256, so Run's fingerprint traces to the file as
downloaded. The Philadelphia Fed's own page draws the same series, which is
where a tie-out reads a quarter off.
"""
from __future__ import annotations

import csv
import hashlib
import re
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .books import quarter_end, write_series

SOURCE = "Large banks (Philadelphia Fed)"
PRODUCT = "Credit card"
#: Measure -> the column in the balances file.
MEASURES = {"Share paying only the minimum": "Share of Accounts Making the Minimum Payment"}
DEFINITIONS = {"Share paying only the minimum":
               ("Share paying only the minimum: of the active consumer credit card accounts at the large banks, the "
                "percent whose payment in the quarter was the minimum due (the Philadelphia Fed's 'Share of Accounts "
                "Making the Minimum Payment'). A count of accounts, not dollars; the panel is the bank holding "
                "companies that file FR Y-14M, those with $100 billion or more in assets, and it can change as banks "
                "cross that line. Quarterly from 2012Q3.")}
FOLDER = "large-banks"
PAGE = "https://www.philadelphiafed.org/surveys-and-data/large-bank-credit-card-and-mortgage-data"
URL = "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/Y14/%s/Q%s/%s"
QUARTER = re.compile(r"^(19|20)\d\dQ[1-4]$")


def file_name(quarter: str) -> str:
    """'2026Q2' -> '26Q2-CreditCardBalances.csv', as the Philadelphia Fed names it."""
    if not QUARTER.match(quarter or ""):
        raise ValueError("quarter must be YYYYQn, not %r" % (quarter,))
    return "%sQ%s-CreditCardBalances.csv" % (quarter[2:4], quarter[5])


def url(quarter: str) -> str:
    return URL % (quarter[:4], quarter[5], file_name(quarter))


def _get(u: str) -> bytes:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (threshold-engine)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def pull(cache, quarter: str, refresh: bool = False, say: Callable[[str], None] = print,
         fetch: Optional[Callable[[str], bytes]] = None) -> Path:
    """Fetch the quarter's balances file into ``cache/large-banks/`` and return
    its path. Held already and not ``refresh``: not fetched. A file that does
    not carry every column the measures need is refused and not kept."""
    folder = Path(cache) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / file_name(quarter)
    if path.exists() and not refresh:
        say("Large banks: %s already held" % path.name)
        return path
    body = (fetch or _get)(url(quarter))
    missing = [c for c in MEASURES.values() if c not in body.decode("utf-8-sig", errors="replace").splitlines()[0]]
    if missing:
        raise ValueError("%s does not carry %s; not kept" % (file_name(quarter), ", ".join(missing)))
    path.write_bytes(body)
    say("Large banks: %s fetched, %d bytes" % (path.name, len(body)))
    return path


def read(path) -> Dict[str, Dict[str, Optional[float]]]:
    """Every column of the file by quarter (``YYYYQn``): a number, or None
    where the file has none ('', 'null'). '$', ',' and '%' are stripped."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    head = rows[0]
    if not head or head[0] != "YRQTR":
        raise ValueError("%s does not start with the YRQTR column; not the Philadelphia Fed's balances file" % path.name)
    out: Dict[str, Dict[str, Optional[float]]] = {c: {} for c in head[1:]}
    for r in rows[1:]:
        if not r or not QUARTER.match(r[0]):
            continue
        for c, v in zip(head[1:], r[1:]):
            v = v.strip()
            out[c][r[0]] = None if v in ("", "null", ".") else float(v.replace("$", "").replace(",", "").replace("%", ""))
    return out


def series(path, measure: str) -> List[Tuple[str, Optional[float]]]:
    """``(YYYYQn, value)`` per quarter in the file for ``measure``."""
    if measure not in MEASURES:
        raise ValueError("measure must be one of %s, not %r" % (list(MEASURES), measure))
    col = read(path).get(MEASURES[measure])
    if col is None:
        raise ValueError("%s has no column %r" % (Path(path).name, MEASURES[measure]))
    return sorted(col.items())


def write(path, out_dir, say: Callable[[str], None] = print) -> List[Tuple[Tuple[str, str, str], Path]]:
    """Write each measure's series file into ``out_dir``, with its notes;
    returns ``[((product, measure, source), written path)]``."""
    path = Path(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    out = []
    for measure in MEASURES:
        rows = series(path, measure)
        held = [(q, v) for q, v in rows if v is not None]
        gaps = [q for q, v in rows if v is None]
        note = ["%s, %s, quarter-end, %%." % (PRODUCT, measure), DEFINITIONS[measure],
                "Source: Federal Reserve Bank of Philadelphia, Large Bank Credit Card and Mortgage Data, the credit "
                "card balances file %s (%s), SHA-256 %s." % (path.name, PAGE, sha),
                "%s quarters, %s to %s.%s" % (len(held), held[0][0], held[-1][0],
                                              (" No value in the file for %s." % ", ".join(gaps)) if gaps else "")]
        target = Path(out_dir) / ("credit-card_large-banks_%s_quarter-end.csv"
                                  % re.sub(r"[^a-z0-9]+", "-", measure.lower()).strip("-"))
        write_series(held, target, note)
        say("Large banks: %s, %d quarters, written to %s" % (measure, len(held), target))
        out.append(((PRODUCT, measure, SOURCE), target))
    return out


def quarter_iso(q: str) -> str:
    return quarter_end(q)
