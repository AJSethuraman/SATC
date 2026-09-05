"""The filed page itself, for every bank in every quarter of the ten years.

The XBRL gives the numbers; the facsimile gives the PAGE -- the header carrying
the bank's name, the form type and the period, and the row a figure sits on. The
firm's position on why that matters: "i want the screenshot method used for
those quarters ... it's the only way i feel like i have been able to trust this
sort of audit."

Twelve banks, forty quarters, 480 documents. It refuses to report a document it
did not get, and it re-reports the ones already on disk rather than counting
them as fetched now -- a denominator that counts what was found is the failure
this whole exercise keeps running into.
"""
import json
import pathlib
import subprocess
import sys
import time

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
OUT = SB / "banks"
PY = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

index = json.loads((SB / "banks" / "index.json").read_text())
quarters = json.loads((SB / "deep" / "deep_quarters.json").read_text())

cached = fetched = failed = 0
misses = []
for entry in index:
    cert, name = entry["cert"], entry["name"]
    got = 0
    for iso in quarters:
        mmddyyyy = iso[5:7] + iso[8:10] + iso[:4]
        pdf = OUT / ("filing-%s-%s.pdf" % (cert, mmddyyyy))
        if pdf.exists() and pdf.stat().st_size > 20000:
            cached += 1
            got += 1
            continue
        try:
            subprocess.run([PY, str(SB / "get_pdf.py"), cert, mmddyyyy, str(pdf)],
                           capture_output=True, timeout=420)
        except subprocess.TimeoutExpired:
            pass
        if pdf.exists() and pdf.stat().st_size > 20000:
            fetched += 1
            got += 1
        else:
            failed += 1
            misses.append((name, iso))
            pdf.unlink(missing_ok=True)
        time.sleep(0.4)
    print("  %-26s %2d of %d filings on disk" % (name[:26], got, len(quarters)),
          flush=True)

print("\nalready cached : %d" % cached)
print("fetched now    : %d" % fetched)
print("could not get  : %d" % failed)
if misses:
    print("\nmissing -- these quarters have no photographed page, and any line")
    print("proved for them rests on the XBRL alone:")
    for name, iso in misses:
        print("   %-26s %s" % (name[:26], iso))
print("\ntotal facsimile PDFs on disk: %d"
      % len(list(OUT.glob("filing-*.pdf"))))
