"""Every quarter's filed Call Report for all twelve banks.

The first pass verified one quarter. The instruction is all of the raw data,
verified, and the workbook holds sixteen quarters per bank -- so this fetches
the bank's own XBRL for each of them, 192 filings in total, and caches them.

Nothing is compared here. This only fetches, so the comparing step can be run
and re-run without hammering the regulator.
"""
import json
import pathlib
import sys
import time

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
OUT = SB / "filings"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import filing as F                # noqa: E402

index = json.loads((SB / "banks" / "index.json").read_text())
quarters = json.loads((SB / "bank_quarters.json").read_text())

todo = [(e["cert"], e["name"], q) for e in index for q in quarters]
print("filings wanted: %d (%d banks x %d quarters)"
      % (len(todo), len(index), len(quarters)))

got = miss = cached = 0
problems = []
for cert, name, iso in todo:
    path = OUT / ("facts-%s-%s.json" % (cert, iso))
    if path.exists():
        cached += 1
        continue
    try:
        facts = F.parse_facts(F.fetch_xbrl(cert, iso), iso)
        if not facts:
            raise ValueError("no facts parsed")
        path.write_text(json.dumps(facts), encoding="utf-8")
        got += 1
        if got % 20 == 0:
            print("   fetched %d ..." % got, flush=True)
    except Exception as exc:                                     # noqa: BLE001
        miss += 1
        problems.append({"cert": cert, "name": name, "repdte": iso,
                         "error": str(exc)[:160]})
    time.sleep(0.25)

(SB / "filing_fetch_problems.json").write_text(json.dumps(problems, indent=1),
                                               encoding="utf-8")
print("\nalready cached : %d" % cached)
print("fetched now    : %d" % got)
print("could not get  : %d" % miss)
for p in problems[:15]:
    print("   %-24s %s  %s" % (p["name"][:24], p["repdte"], p["error"][:70]))
print("\ntotal filings on disk: %d" % len(list(OUT.glob("facts-*.json"))))
