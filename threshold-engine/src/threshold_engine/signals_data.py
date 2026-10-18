"""The public series behind the Signals tab, and where each comes from.

The Signals tab (``signals_tab.py``) lays every signal found in the October
2026 early-warning work beside the book's own series. Its data is public and
comes three ways:

1. **Fetched**, by ``peers signals-pull --cache DIR --quarter YYYYQn``: the
   Philadelphia Fed's credit card balances and originations files for the
   quarter (every quarter since 2012Q3 is in each) and the Federal Reserve's
   survey series DRTSCLCC from FRED's public CSV (no key). Each is kept under
   ``DIR/signals`` and named, with its SHA-256, in the series' notes.
2. **Committed**, under ``data/signals``: series read once from sources that
   are large or need a contact to fetch, kept as small JSON with a README
   that says how each was made: the FHFA National Mortgage Database
   aggregates (mark-to-market LTV, origination DTI), and each holding
   company's share of scored card balances under 660 from its 10-Q XBRL
   (``docs/early-warning-2026-10/record/peerfico_pull.py``).
3. **Computed at build** from the FDIC cache the book already reads: each
   product's balance, trailing gross charge-offs and 30+ incl. nonaccrual
   dollars for the bank and the industry (the peer group's are summed live
   on the tab from Peers data, so they follow Banks in the pack).

``load(spec, cache, data, roster, quarters)`` returns ``{"series": [(key,
title, unit, {YYYYQn: value})], "sources": [(what, file, sha256)]}``. Every
value is as published; nothing is filled in. A quarter a source does not
give is absent, never 0.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .peers import books, fdic
from .peers import delinquency as D
from .peers import large_banks as LB

FOLDER = "signals"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s"
SURVEY = "DRTSCLCC"
#: Book key -> what it is. Every key is required; a path or null.
KEYS = ("balances", "originations", "survey", "nmdb", "fico")
QUARTER = re.compile(r"^(19|20)\d\dQ[1-4]$")


def _get(u: str) -> bytes:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (threshold-engine)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def pull(cache, quarter: str, refresh: bool = False, say: Callable[[str], None] = print,
         fetch: Optional[Callable[[str], bytes]] = None) -> Dict[str, Path]:
    """Fetch the three public files into ``cache/signals`` (held already and
    not ``refresh``: not fetched). Returns ``{key: path}`` for balances,
    originations and survey."""
    get = fetch or _get
    folder = Path(cache) / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, name, url in (("balances", LB.file_name(quarter), LB.url(quarter)),
                           ("originations", LB.file_name(quarter).replace("Balances", "Originations"),
                            LB.url(quarter).replace("Balances", "Originations")),
                           ("survey", "%s.csv" % SURVEY, FRED_CSV % SURVEY)):
        path = folder / name
        if path.exists() and not refresh:
            say("Signals: %s already held" % name)
        else:
            body = get(url)
            head = body.decode("utf-8-sig", errors="replace").splitlines()[0] if body else ""
            if key == "survey" and not head.startswith("observation_date,%s" % SURVEY):
                raise ValueError("%s is not FRED's %s file; not kept" % (name, SURVEY))
            if key != "survey" and "YRQTR" not in head:
                raise ValueError("%s does not start with YRQTR; not the Philadelphia Fed file; not kept" % name)
            path.write_bytes(body)
            say("Signals: %s fetched, %d bytes" % (name, len(body)))
        out[key] = path
    return out


#: The Philadelphia Fed columns the tab draws: (key, file, column, title, unit).
PHILLY = (
    ("minpay", "balances", "Share of Accounts Making the Minimum Payment",
     "Card accounts paying only the minimum (large banks)", "%"),
    ("util90", "balances", "Utilization (Active Accounts Only) (90th percentile)",
     "Card utilization, 90th percentile of active accounts (large banks)", "%"),
    ("util50", "balances", "Utilization (Active Accounts Only) (50th percentile)",
     "Card utilization, median active account (large banks)", "%"),
    ("pv660", "balances", "Average Purchase Volume by Credit Score Group: < 660 Credit Score",
     "Average purchase volume per card account under 660 (large banks)", "$"),
    ("dpd30", "balances", "30+ Days Past Due Rates: Balances Based",
     "Card 30+ days past due, balance based (large banks)", "%"),
    ("score10", "originations", "Original Credit Score (10th percentile)",
     "New card accounts: credit score of the weakest tenth (large banks)", "score"),
    ("new660", "originations", "Percentage of New Accounts with < 660 Credit Score",
     "New card accounts with a score under 660 (large banks)", "%"),
)


def _fred(path) -> Dict[str, float]:
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.reader(fh):
            if not row or row[0] == "observation_date" or row[1] in ("", "."):
                continue
            y, m_ = int(row[0][:4]), int(row[0][5:7])
            out["%dQ%d" % (y, (m_ - 1) // 3 + 1)] = float(row[1])
    return out


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _committed(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def by_product(data: Dict[str, list], cert, products) -> Dict[str, Dict[str, dict]]:
    """Per product and quarter for one bank: ``{bal, gco4, d30}`` ($000):
    the quarter-end balance, gross charge-offs over the trailing four
    quarters (None until four flows exist), and 30-89 + 90+ accruing +
    nonaccrual (None when a field is not filed). ``cert`` None sums every
    filer (the industry): a bank counts in a quarter's sum when it filed the
    fields that quarter."""
    qs, snap = books._by_cert(data)
    out = {}
    for p in products:
        bal_f, p3, p9, na = D._fields(p)
        ln, dr, cr = books._fields(p)
        certs = [str(cert)] if cert is not None else None
        rows = {}
        flows = {}
        for c in (certs or sorted({c_ for q in qs for c_ in snap[q]})):
            fl = books._flows(qs, snap, c, p)
            for i, (q, g, r_, b) in enumerate(fl):
                row = snap[q].get(c)
                d30 = None
                if row is not None:
                    vals = [D._filed(row, f) for f in (p3, p9, na)]
                    d30 = None if any(v is None for v in vals) else sum(vals)
                flows.setdefault(q, []).append((g, b, d30))
        for i, q in enumerate(qs):
            fs = flows.get(q, [])
            bal = sum(b for _, b, _ in fs if b is not None) if any(b is not None for _, b, _ in fs) else None
            d30 = sum(d for _, _, d in fs if d is not None) if any(d is not None for _, _, d in fs) else None
            g4 = None
            if i >= 3:
                parts_ = []
                for k in range(i - 3, i + 1):
                    gs = [g for g, _, _ in flows.get(qs[k], []) if g is not None]
                    parts_.append(sum(gs) if gs else None)
                g4 = sum(parts_) if all(x is not None for x in parts_) else None
            rows[books.label(q)] = {"bal": bal, "gco4": g4, "d30": d30}
        out[p] = rows
    return out


def windows(data: Dict[str, list], product: str, ns=(1, 2, 3)) -> Dict[int, Dict[str, float]]:
    """The industry's 30+ to charge-off over the next 1, 2 and 3 quarters,
    four-quarter average, in %: every filer's delinquent dollars summed at
    the quarter-end over its gross charge-offs summed over the quarters
    after (the window test the analyst asked for, 18 Oct 2026)."""
    qs, snap = books._by_cert(data)
    _, p3, p9, na = D._fields(product)
    dq = {}; gco = {}
    for c in sorted({c_ for q in qs for c_ in snap[q]}):
        fl = books._flows(qs, snap, c, product)
        for q, g, _, _ in fl:
            if g is not None:
                gco[q] = gco.get(q, 0.0) + g
            row = snap[q].get(c)
            if row is not None:
                vals = [D._filed(row, f) for f in (p3, p9, na)]
                if not any(v is None for v in vals):
                    dq[q] = dq.get(q, 0.0) + sum(vals)
    out = {}
    for n in ns:
        rate = {}
        for i, q in enumerate(qs):
            if dq.get(q) and i + n < len(qs) and all(qs[k] in gco for k in range(i + 1, i + n + 1)):
                rate[q] = 100 * sum(gco[qs[k]] for k in range(i + 1, i + n + 1)) / dq[q]
        avg = {}
        for i in range(3, len(qs)):
            w = qs[i - 3:i + 1]
            if all(x in rate for x in w):
                avg[books.label(qs[i])] = sum(rate[x] for x in w) / 4
        out[n] = avg
    return out


def load(spec: dict, cache, data: Optional[Dict[str, list]], self_cert, products, say=print) -> dict:
    """Every series the tab draws. ``spec`` is the book's ``signals`` section
    with paths resolved; ``data`` the FDIC cache as the peers build read it
    (None: the by-product dollars are not computed)."""
    series: List[Tuple[str, str, str, Dict[str, float]]] = []
    sources: List[Tuple[str, str, str]] = []
    cols = {}
    for key in ("balances", "originations"):
        p = Path(spec[key])
        cols[key] = LB.read(p)
        sources.append(("Philadelphia Fed, large bank credit card %s" % key, p.name, _sha(p)))
    for key, file, col, title, unit in PHILLY:
        if col not in cols[file]:
            raise ValueError("%s has no column %r" % (Path(spec[file]).name, col))
        series.append((key, title, unit, {q: v for q, v in cols[file][col].items() if v is not None}))
    sv = Path(spec["survey"])
    series.append(("easing", "Net share of banks easing card standards (Senior Loan Officer Survey; above zero = easing)", "%",
                   {q: -v for q, v in _fred(sv).items()}))
    sources.append(("Federal Reserve, Senior Loan Officer Opinion Survey, %s via FRED" % SURVEY, sv.name, _sha(sv)))
    nm = _committed(spec["nmdb"])
    series.append(("ltv90", "Mortgages owing more than 90% of the home's value (FHFA NMDB, all lenders)", "%",
                   {q: float(v) for q, v in nm["over90"].items()}))
    series.append(("dti44", "New purchase mortgages with DTI 44% or more (FHFA NMDB)", "%",
                   {q: float(v) for q, v in nm["dti44"].items()}))
    sources.append(("FHFA National Mortgage Database aggregates, read into JSON", Path(spec["nmdb"]).name, _sha(spec["nmdb"])))
    fi = _committed(spec["fico"])
    for bank, d_ in fi["card"].items():
        series.append(("fico_" + re.sub(r"[^a-z0-9]+", "_", bank.lower()).strip("_"),
                       "%s: share of scored card balances with refreshed FICO under 660 (10-Q)" % bank, "%",
                       {q: float(v) for q, v in d_.items()}))
    sources.append(("Each holding company's 10-Q XBRL, FICO bands by class, read into JSON", Path(spec["fico"]).name, _sha(spec["fico"])))
    if data is not None:
        for who, cert in (("KeyBank", self_cert), ("Industry", None)):
            bp = by_product(data, cert, products)
            for p in products:
                for k, title in (("bal", "balance ($000), quarter-end"), ("gco4", "gross charge-offs, trailing four quarters ($000)"),
                                 ("d30", "30+ incl. nonaccrual dollars ($000), quarter-end")):
                    series.append(("%s_%s_%s" % (who.lower(), re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-"), k),
                                   "%s, %s: %s" % (who, p, title), "$000",
                                   {q: v[k] for q, v in bp[p].items() if v[k] is not None}))
        for n, d_ in windows(data, "Credit card").items():
            series.append(("win%d" % n, "Industry card: of the dollars 30+ incl. nonaccrual at quarter-end, %% charged off over the next %d quarter%s (4q avg)"
                           % (n, "" if n == 1 else "s"), "%", d_))
        sources.append(("FDIC Call Reports from the book's cache: each product's balance, charge-offs and past-due fields", "the cache", ""))
    say("signals: %d series from %d sources" % (len(series), len(sources)))
    return {"series": series, "sources": sources}
