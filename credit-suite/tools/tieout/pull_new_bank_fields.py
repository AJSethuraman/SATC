"""Pull the nineteen new bank fields, ten years, twelve banks.

The firm took every candidate in the ranked list's first two tiers. On the bank
side that is nineteen fields: the two utilization lines, the two halves of the
CRE charge-off, the HELOC loss line, the regulatory capital denominator, the two
Texas-ratio components, the three commercial commitment lines, lending to
non-banks, and the seven restructured-loan lines.

They go into the FEED and not into `RAW_FIELDS`. The firm's answer on that was
"feed only": `RAW_FIELDS` drives `raw_slots`, which the layout says is built
into every dashboard formula, and re-cutting that geometry is a change to a
working product nobody asked to change.

Every name was requested from the FDIC before this ran and all nineteen came
back. That check is not ceremony -- the FDIC omits a field name it does not have
instead of rejecting the request, and one field in the existing set has been
asked for in every run this software ever made and returned never.
"""
import json
import pathlib
import sys
import time
import urllib.request

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
OUT = SB / "deep"
OUT.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

#: The nineteen, in the order the firm's ranked list took them.
NEW_FIELDS = [
    "UCCRCD", "UCLOC",                                   # 1-2 utilization
    "DRRENRSQ", "CRRENRSQ",                              # 3   the blank column
    "NTRELOCQ",                                          # 4   HELOC losses
    "RBC",                                               # 5   capital denominator
    "ORE", "INTAN",                                      # 6   the real Texas ratio
    "UCCOMRES", "UCCOMREU", "UCOTHER",                   # 9   commercial commitments
    "LNNDEPD",                                           # 10  lending to non-banks
    "RSLNLTOT", "RSLNREFM", "RSCI", "RSCONS",            # 12  restructured loans
    "RSMULT", "RSOTHER", "NARSNRES",
]

API = "https://banks.data.fdic.gov/api/financials"
QUARTERS = 40
index = json.loads((SB / "banks" / "index.json").read_text())


def pull(cert):
    rows, cursor = [], 0
    while len(rows) < QUARTERS:
        url = ("%s?filters=CERT%%3A%s&fields=CERT,REPDTE,%s"
               "&sort_by=REPDTE&sort_order=DESC&limit=%d&offset=%d&format=json"
               % (API, cert, ",".join(NEW_FIELDS),
                  min(50, QUARTERS - len(rows)), cursor))
        with urllib.request.urlopen(url, timeout=180) as fh:
            data = json.loads(fh.read())
        got = [r.get("data", r) for r in data.get("data", [])]
        if not got:
            break
        rows.extend(got)
        cursor += len(got)
        time.sleep(0.2)
    return rows[:QUARTERS]


all_rows, absent = {}, {f: 0 for f in NEW_FIELDS}
for entry in index:
    cert, name = entry["cert"], entry["name"]
    rows = pull(cert)
    all_rows[cert] = rows
    for r in rows:
        for f in NEW_FIELDS:
            if f not in r:
                absent[f] += 1
    values = sum(1 for r in rows for f in NEW_FIELDS if r.get(f) is not None)
    print("  %-26s %2d quarters  %5d values" % (name[:26], len(rows), values),
          flush=True)

(OUT / "bank_new_fields.json").write_text(json.dumps(all_rows), encoding="utf-8")

total = sum(1 for rs in all_rows.values() for r in rs
            for f in NEW_FIELDS if r.get(f) is not None)
quarters = sorted({str(r["REPDTE"]) for rs in all_rows.values() for r in rs})
print("\n%d banks x %d quarters x %d fields = %d expected"
      % (len(all_rows), len(quarters), len(NEW_FIELDS),
         len(all_rows) * len(quarters) * len(NEW_FIELDS)))
print("values actually returned : %d" % total)
missing = [f for f, n in absent.items() if n]
if missing:
    print("\nFIELDS THE FDIC OMITTED IN SOME QUARTER -- these cannot be trusted")
    print("to be a bank reporting nothing:")
    for f in missing:
        print("   %-10s absent in %d of %d bank-quarters"
              % (f, absent[f], len(all_rows) * len(quarters)))
else:
    print("no field was omitted in any bank-quarter")
