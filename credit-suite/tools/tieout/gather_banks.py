"""Gather, for every bank in the monitor, the evidence a tie-out needs.

Per bank: the roster (the workbook's own cells against the bank's filed Call
Report), both filings as PDF (June and the prior March, because a quarterly
flow is the difference between two), and both filings' XBRL facts.

Nothing is compared here. This only fetches, so the comparing step can be run
and re-run without hammering the regulator.
"""
import json
import pathlib
import subprocess
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
OUT = SB / "banks"
OUT.mkdir(exist_ok=True)
PY = r"C:\Users\ajish\SATC\.venv\Scripts\python.exe"
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import engine_api as R          # noqa: E402
from credit_suite.sources.fdic import filing                    # noqa: E402
import openpyxl                                                 # noqa: E402

WB = CS / "example-output" / "Bank_Peer_Monitor.xlsm"
book = openpyxl.load_workbook(WB, keep_vba=True, data_only=True)
cfg = R.parse_config(list(book["_config"].iter_rows(values_only=True)))
book.close()
banks = [(str(e.entity_key).split(":")[-1], e.name, e.slot)
         for e in cfg.entities if getattr(e, "has_entity", False)]
print("banks in the monitor: %d" % len(banks))

QUARTERS = [("2026-06-30", "06302026"), ("2026-03-31", "03312026")]
index = []
for cert, name, slot in banks:
    entry = {"cert": cert, "name": name, "slot": slot, "filings": {}, "roster": None}
    print("\n=== %s (cert %s, slot %d)" % (name, cert, slot))

    # 1. the roster: the workbook's cells against the filing
    roster = OUT / ("roster-%s.txt" % cert)
    if not roster.exists():
        run = subprocess.run(
            [PY, "-X", "utf8", "-m", "credit_suite.sources.fdic.runner",
             "-w", str(WB), "--tieout", cert, "--filing"],
            cwd=str(CS), capture_output=True, text=True,
            env={**__import__("os").environ, "PYTHONPATH": str(CS / "src")})
        roster.write_text(run.stdout or "", encoding="utf-8")
        if run.returncode != 0:
            (OUT / ("roster-%s.err" % cert)).write_text(run.stderr or "", encoding="utf-8")
            print("   roster FAILED rc=%d: %s" % (run.returncode, (run.stderr or "")[:160]))
    entry["roster"] = roster.name
    line = [l for l in roster.read_text(encoding="utf-8", errors="replace").splitlines()
            if "raw dollar lines compared" in l]
    print("   %s" % (line[0].strip() if line else "no comparison line in the roster"))

    # 2. both filings, as the regulator serves them
    for iso, mmddyyyy in QUARTERS:
        pdf = OUT / ("filing-%s-%s.pdf" % (cert, mmddyyyy))
        if not pdf.exists():
            got = subprocess.run([PY, str(SB / "get_pdf.py"), cert, mmddyyyy, str(pdf)],
                                 capture_output=True, text=True)
            if pdf.exists():
                print("   filing %s: %d KB" % (iso, pdf.stat().st_size // 1024))
            else:
                print("   filing %s: NOT AVAILABLE -- %s" % (iso, (got.stdout or got.stderr)[-120:].strip()))
        facts = OUT / ("facts-%s-%s.json" % (cert, mmddyyyy))
        if not facts.exists():
            try:
                data = filing.parse_facts(filing.fetch_xbrl(cert, iso), iso)
                facts.write_text(json.dumps(data), encoding="utf-8")
                print("   facts  %s: %d" % (iso, len(data)))
            except Exception as exc:
                print("   facts  %s: UNAVAILABLE -- %s" % (iso, str(exc)[:120]))
        entry["filings"][iso] = {"pdf": pdf.name if pdf.exists() else None,
                                 "facts": facts.name if facts.exists() else None}
    index.append(entry)

(OUT / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
print("\nindex written: %d banks" % len(index))
