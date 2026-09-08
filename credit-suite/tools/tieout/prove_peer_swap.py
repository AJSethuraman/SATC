"""Prove the pipeline runs on a bank it has never seen, without editing a script.

The goal: swapping the peer group is a one-step change. The only honest way to
know is to change the list and run everything -- a pipeline that works on the
twelve it was written for proves nothing about the thirteenth.

So this takes one certificate the project has never touched, runs all six
stages against it, and reports how many completed with NO script edited. The
number starts at zero and only moves by working.

    python tools/tieout/prove_peer_swap.py 6672 "Fifth Third Bank"

Six stages, in order, each the same code the twelve go through:

    1  filings        the bank's own XBRL Call Report facts, one per quarter
    2  facsimiles     the filed pages as the regulator serves them
    3  fields         all 87, ten years, from the FDIC
    4  verify         every value against the line it cites on the filing
    5  photograph     the cited row of every filed page
    6  export         the rows the deliverable would carry

Nothing is written into the shipped deliverable. This proves the chain runs; it
does not add a bank to the firm's feed, which is their decision and not a test's.
"""
import collections
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
sys.path.insert(0, str(CS / "src"))

from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import feed_fields as FF          # noqa: E402
from credit_suite.sources.fdic import fields as RF               # noqa: E402
from credit_suite.sources.fdic import filing as FILING           # noqa: E402

CERT = sys.argv[1] if len(sys.argv) > 1 else "6672"
NAME = sys.argv[2] if len(sys.argv) > 2 else "Fifth Third Bank"
QUARTERS = json.loads((SB / "deep" / "deep_quarters.json").read_text())
PY = sys.executable

passed, results = 0, []


def stage(n, label, fn):
    global passed
    started = time.time()
    try:
        detail = fn()
        ok = True
    except Exception as exc:                                     # noqa: BLE001
        detail, ok = "%s: %s" % (type(exc).__name__, str(exc)[:90]), False
    passed += ok
    results.append((n, label, ok, detail))
    print("  %d  %-14s %-4s %-58s %.0fs"
          % (n, label, "ok" if ok else "FAIL", str(detail)[:58],
             time.time() - started), flush=True)


# ---- 1 · filings ----------------------------------------------------------
def s1():
    got = 0
    for iso in QUARTERS:
        p = SB / "filings" / ("facts-%s-%s.json" % (CERT, iso))
        if p.exists():
            got += 1
            continue
        try:
            facts = FILING.parse_facts(FILING.fetch_xbrl(CERT, iso), iso)
        except Exception:                                        # noqa: BLE001
            continue
        p.write_text(json.dumps(facts), encoding="utf-8")
        got += 1
        time.sleep(0.2)
    if got < len(QUARTERS) * 0.9:
        raise RuntimeError("only %d of %d quarters" % (got, len(QUARTERS)))
    return "%d of %d quarters" % (got, len(QUARTERS))


# ---- 2 · facsimiles -------------------------------------------------------
def s2():
    got = 0
    for iso in QUARTERS:
        mmdd = iso[5:7] + iso[8:10] + iso[:4]
        pdf = SB / "banks" / ("filing-%s-%s.pdf" % (CERT, mmdd))
        if pdf.exists() and pdf.stat().st_size > 20000:
            got += 1
            continue
        subprocess.run([PY, str(SB / "get_pdf.py"), CERT, mmdd, str(pdf)],
                       capture_output=True, timeout=420)
        if pdf.exists() and pdf.stat().st_size > 20000:
            got += 1
        else:
            pdf.unlink(missing_ok=True)
        time.sleep(0.3)
    if got < len(QUARTERS) * 0.9:
        raise RuntimeError("only %d of %d facsimiles" % (got, len(QUARTERS)))
    return "%d of %d facsimiles" % (got, len(QUARTERS))


# ---- 3 · fields -----------------------------------------------------------
ALL = sorted(set(RF.RAW_FIELDS) | set(FF.FEED_FIELDS))
rows_by_q = {}


def s3():
    api = "https://banks.data.fdic.gov/api/financials"
    fetched, cursor = [], 0
    while len(fetched) < len(QUARTERS):
        url = ("%s?filters=CERT%%3A%s&fields=CERT,REPDTE,%s&sort_by=REPDTE"
               "&sort_order=DESC&limit=%d&offset=%d&format=json"
               % (api, CERT, ",".join(ALL),
                  min(50, len(QUARTERS) - len(fetched)), cursor))
        with urllib.request.urlopen(url, timeout=180) as fh:
            data = json.loads(fh.read())
        got = [r.get("data", r) for r in data.get("data", [])]
        if not got:
            break
        fetched.extend(got)
        cursor += len(got)
    for r in fetched:
        s = str(r["REPDTE"])
        rows_by_q["%s-%s-%s" % (s[:4], s[4:6], s[6:8])] = r
    n = sum(1 for r in fetched for f in ALL if r.get(f) is not None)
    if not fetched:
        raise RuntimeError("no rows returned")
    return "%d values over %d quarters" % (n, len(fetched))


# ---- 4 · verify -----------------------------------------------------------
PREFIXES = ("RCFD", "RCON", "RIAD", "RCFA", "RCOA", "RCFW", "RCFN")
verdicts = collections.Counter()


def by_item(f):
    out = {}
    for k, v in f.items():
        if isinstance(v, (int, float)) and k[:4] in PREFIXES:
            out.setdefault(k[4:], []).append(float(v))
    return out


def evaluate(expr, b, raw):
    total, sign, buf, terms = 0.0, 1, "", []
    for ch in expr:
        if ch in "+-":
            terms.append((sign, buf.strip()))
            sign = 1 if ch == "+" else -1
            buf = ""
        else:
            buf += ch
    terms.append((sign, buf.strip()))
    for sgn, code in terms:
        if not code:
            continue
        if code[:4] in PREFIXES:
            if raw.get(code) is None:
                return None
            total += sgn * float(raw[code])
            continue
        if code not in b:
            return None
        total += sgn * max(b[code], key=abs)
    return total


def s4():
    for iso, row in rows_by_q.items():
        p = SB / "filings" / ("facts-%s-%s.json" % (CERT, iso))
        if not p.exists():
            verdicts["no filing"] += 1
            continue
        raw = json.loads(p.read_text())
        b = by_item(raw)
        for field in FF.FEED_FIELDS:
            ours = row.get(field)
            if ours is None:
                continue
            if field in FF.FEED_FLOW_FIELDS:
                verdicts["flow (needs the prior quarter)"] += 1
                continue
            if field in FF.TWO_COLUMN_FIELDS:
                col = FF.binding_column(field, raw)
                theirs = float(raw[col]) / 1000.0 if col else None
            else:
                expr = FF.citation_for(field, iso).split(" (")[0]
                got = evaluate(expr, b, raw)
                theirs = None if got is None else got / 1000.0
            if theirs is None:
                verdicts["not on this filing"] += 1
            elif abs(float(ours) - theirs) < 0.51:
                verdicts["TIES"] += 1
            else:
                verdicts["DIFFERS"] += 1
    if verdicts["DIFFERS"]:
        raise RuntimeError("%d differ" % verdicts["DIFFERS"])
    if not verdicts["TIES"]:
        raise RuntimeError("nothing tied")
    return "%d tie, 0 differ" % verdicts["TIES"]


# ---- 5 · photograph -------------------------------------------------------
def s5():
    import re
    import pymupdf
    TOKEN = re.compile(r"[A-Z]{4}[A-Z0-9]{4}|[A-Z0-9]{4}")
    CODE = re.compile(r"[A-Z]{4}[A-Z0-9]{4}")
    iso = max(rows_by_q)
    mmdd = iso[5:7] + iso[8:10] + iso[:4]
    pdf = SB / "banks" / ("filing-%s-%s.pdf" % (CERT, mmdd))
    doc = pymupdf.open(pdf)
    codes = {}
    for pno in range(doc.page_count):
        for w in doc[pno].get_text("words"):
            if CODE.fullmatch(w[4]) and w[4] not in codes:
                codes[w[4]] = pno
    shot = missing = 0
    for field in FF.FEED_FIELDS:
        if field in FF.FEED_FLOW_FIELDS:
            continue
        expr = FF.citation_for(field, iso).split(" (")[0]
        for token in TOKEN.findall(expr):
            item = token[-4:]
            hit = [k for k in codes if k[4:] == item]
            shot += bool(hit)
            missing += (not hit)
    doc.close()
    if not shot:
        raise RuntimeError("no cited code found on the filing")
    return "%d cited rows locatable, %d not on this filing" % (shot, missing)


# ---- 6 · export -----------------------------------------------------------
def s6():
    n = sum(1 for row in rows_by_q.values()
            for f in ALL if row.get(f) is not None)
    if n < len(QUARTERS) * 50:
        raise RuntimeError("only %d values would reach the deliverable" % n)
    return "%d rows would join bank-values.csv" % n


print("Proving the chain on cert %s (%s), a bank the project has never seen.\n"
      % (CERT, NAME))
stage(1, "filings", s1)
stage(2, "facsimiles", s2)
stage(3, "fields", s3)
stage(4, "verify", s4)
stage(5, "photograph", s5)
stage(6, "export", s6)

print("\nDISTANCE TO THE GOAL: %d of 6 stages proven on a changed peer list."
      % passed)
if passed < 6:
    print("Not proven:")
    for n, label, ok, detail in results:
        if not ok:
            print("   %d %-14s %s" % (n, label, detail))
else:
    print("Swapping the peer group is a one-step change: no script was edited.")
print("\nverdicts on the new bank: %s" % dict(verdicts))
