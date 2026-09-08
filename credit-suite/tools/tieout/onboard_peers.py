"""Take every peer that has no data yet through the whole chain.

The chain is already proven to run on a bank it has never seen -- six of six
stages on cert 6672, no script edited. This is that, for however many banks are
in the peer table without data, so the work is volume rather than new ground.

Runs only what is MISSING. A bank already on disk is skipped, so this is safe to
re-run after an interruption and picks up where it stopped.

    python tools/tieout/onboard_peers.py            # every peer lacking data
    python tools/tieout/onboard_peers.py 588 12368  # just these

Reports the distance to the goal as a number that goes UP as banks complete, and
names the ones still outstanding rather than saying "in progress".
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
from credit_suite.sources.fdic import series_seed as SEED        # noqa: E402

QUARTERS = json.loads((SB / "deep" / "deep_quarters.json").read_text())
ALL_FIELDS = sorted(set(RF.RAW_FIELDS) | set(FF.FEED_FIELDS))
PY = sys.executable
API = "https://banks.data.fdic.gov/api/financials"

only = [a for a in sys.argv[1:] if a.isdigit()]
have = {e["cert"] for e in
        json.loads((SB / "banks" / "index.json").read_text())}
todo = [(str(c), n) for _s, c, n, _g, a in SEED.PEERS
        if a == "TRUE" and str(c) not in have]
if only:
    todo = [(c, n) for c, n in todo if c in only]

print("peers in the table : %d" % len(SEED.PEERS))
print("already with data  : %d" % len(have))
print("to onboard         : %d\n" % len(todo))
if not todo:
    raise SystemExit("nothing to do")


def filings(cert):
    got = 0
    for iso in QUARTERS:
        p = SB / "filings" / ("facts-%s-%s.json" % (cert, iso))
        if p.exists():
            got += 1
            continue
        try:
            p.write_text(json.dumps(
                FILING.parse_facts(FILING.fetch_xbrl(cert, iso), iso)),
                encoding="utf-8")
            got += 1
            time.sleep(0.15)
        except Exception:                                        # noqa: BLE001
            pass
    return got


def facsimiles(cert):
    got = 0
    for iso in QUARTERS:
        mmdd = iso[5:7] + iso[8:10] + iso[:4]
        pdf = SB / "banks" / ("filing-%s-%s.pdf" % (cert, mmdd))
        if pdf.exists() and pdf.stat().st_size > 20000:
            got += 1
            continue
        subprocess.run([PY, str(SB / "get_pdf.py"), cert, mmdd, str(pdf)],
                       capture_output=True, timeout=420)
        if pdf.exists() and pdf.stat().st_size > 20000:
            got += 1
        else:
            pdf.unlink(missing_ok=True)
        time.sleep(0.3)
    return got


def fields(cert):
    rows, cursor = [], 0
    while len(rows) < len(QUARTERS):
        url = ("%s?filters=CERT%%3A%s&fields=CERT,REPDTE,%s&sort_by=REPDTE"
               "&sort_order=DESC&limit=%d&offset=%d&format=json"
               % (API, cert, ",".join(ALL_FIELDS),
                  min(50, len(QUARTERS) - len(rows)), cursor))
        with urllib.request.urlopen(url, timeout=180) as fh:
            got = [r.get("data", r)
                   for r in json.loads(fh.read()).get("data", [])]
        if not got:
            break
        rows.extend(got)
        cursor += len(got)
        time.sleep(0.15)
    return rows[:len(QUARTERS)]


started = time.time()
new_rows, done, partial = {}, [], []
for cert, name in todo:
    t0 = time.time()
    nf = filings(cert)
    nx = facsimiles(cert)
    rows = fields(cert)
    values = sum(1 for r in rows for f in ALL_FIELDS if r.get(f) is not None)
    new_rows[cert] = rows
    ok = (nf >= len(QUARTERS) * 0.9 and nx >= len(QUARTERS) * 0.9 and
          len(rows) >= len(QUARTERS) * 0.9)
    (done if ok else partial).append((cert, name))
    print("  %-32s %2d filings  %2d facsimiles  %2d quarters  %5d values  %s  %.0fs"
          % (name[:32], nf, nx, len(rows), values,
             "ok" if ok else "PARTIAL", time.time() - t0), flush=True)

out = SB / "deep" / "bank_peer_add.json"
prev = json.loads(out.read_text()) if out.exists() else {}
prev.update(new_rows)
out.write_text(json.dumps(prev), encoding="utf-8")

print("\nDISTANCE: %d of %d banks pulled clean, %.0f min"
      % (len(done), len(todo), (time.time() - started) / 60))
if partial:
    print("still outstanding:")
    for cert, name in partial:
        print("   %-7s %s" % (cert, name))
print("\nPulled, not yet verified. Verification is the next stage and is what")
print("decides whether these can be trusted, not this.")
