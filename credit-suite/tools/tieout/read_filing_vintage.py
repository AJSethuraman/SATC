"""Read the version stamp off every filing, so a value says which one it is.

Each FFIEC facsimile prints `Last Updated on <date>` on its interior pages --
it is visible in the header of every photograph in every exhibit, and it says
which revision of that filing the value was checked against. It was never
captured, so the workbook told the firm "THERE IS NO VINTAGE... nothing here
records which revision a figure is". The first half of that was wrong: the
vintage was on every page we had already photographed.

Measured over the 760 filings on 7 September 2026, 58% were last updated more
than 90 days after the quarter they report and 289 more than a year after it.
Amendments are not a hypothetical risk in this panel; they are the normal case.

    python tools/tieout/read_filing_vintage.py
"""
import collections
import datetime
import json
import pathlib
import re
import sys

import pymupdf

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
sys.path.insert(0, str(CS / "src"))

from credit_suite.workdir import workdir        # noqa: E402

SB = workdir()
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

STAMP = re.compile(r"Last Updated on (\d{1,2}/\d{1,2}/\d{4})")

out, missing = {}, []
for pdf in sorted((SB / "banks").glob("filing-*.pdf")):
    _, cert, mmdd = pdf.stem.split("-")
    iso = "%s-%s-%s" % (mmdd[4:], mmdd[:2], mmdd[2:4])
    doc = pymupdf.open(pdf)
    found = None
    # The cover pages do not carry it; the schedule pages do.
    for page in range(min(doc.page_count, 6), doc.page_count):
        m = STAMP.search(doc[page].get_text())
        if m:
            found = m.group(1)
            break
    doc.close()
    if not found:
        missing.append(pdf.name)
        continue
    month, day, year = (int(x) for x in found.split("/"))
    quarter = datetime.date(*(int(x) for x in iso.split("-")))
    out["%s|%s" % (cert, iso)] = [
        (datetime.date(year, month, day) - quarter).days, found]

(SB / "filing_vintage.json").write_text(json.dumps(out), encoding="utf-8")

buckets = collections.Counter()
for days, _ in out.values():
    buckets["within 90 days -- the ordinary filing window" if days <= 90
            else "91 to 180 days" if days <= 180
            else "181 to 365 days" if days <= 365
            else "more than a year after the quarter"] += 1

print("filings read            : %d" % len(out))
print("no stamp found          : %d%s"
      % (len(missing), ("  " + ", ".join(missing[:5])) if missing else ""))
for label in ("within 90 days -- the ordinary filing window", "91 to 180 days",
              "181 to 365 days", "more than a year after the quarter"):
    print("  %-46s %d" % (label, buckets[label]))
print("\nA figure is only as current as the filing it was checked against, and")
print("the FDIC republishes on its own cycle. Where the two disagree, this")
print("column is the first place to look.")
