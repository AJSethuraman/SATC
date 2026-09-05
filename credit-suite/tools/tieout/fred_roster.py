"""Merge the six runs into one roster, and refuse if the denominator is wrong.

Six scripts each tied one publisher's slice. This assembles them into a single
roster over the workbook's 142 series and checks the arithmetic that makes a
roster mean anything:

  * every series in the workbook appears exactly once
  * no series appears in two sets
  * nothing appears that the workbook does not hold

A roster whose parts do not add to the whole is a roster that has quietly
dropped something, and dropping something is the failure this exists to catch.
"""
import json
import pathlib
import sys
from collections import Counter

SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ours = json.loads((SB / "fred_ours.json").read_text())

#: Three series sit in the FHFA run's output that are not FHFA quarterly
#: series: two are S&P's national indexes and one is FHFA's MONTHLY index.
#: They are tied in their own sets and must not be counted twice here.
NOT_FHFA_QUARTERLY = {"CSUSHPINSA", "CSUSHPISA", "HPIPONM226S"}

SETS = [
    ("FHFA All-Transactions house price indexes",
     "Federal Housing Finance Agency",
     "fred_fhfa_results.json",
     lambda r: r["series"] not in NOT_FHFA_QUARTERLY),
    ("Charge-off and delinquency rates at commercial banks",
     "Federal Reserve Board",
     "fred_fed_results.json",
     lambda r: r["verdict"] != "COULD NOT" or "not in the workbook" not in
               (r.get("why") or "")),
    ("G.19 consumer credit, the debt service ratios, FHFA monthly",
     "Federal Reserve Board and FHFA",
     "fred_other_results.json", lambda r: True),
    ("Senior Loan Officer Opinion Survey",
     "Federal Reserve Board",
     "fred_sloos_results.json", lambda r: True),
    ("S&P Cotality Case-Shiller house price indexes",
     "S&P Dow Jones Indices",
     "fred_caseshiller_results.json", lambda r: True),
    ("Z.1 commercial property price indexes",
     "Federal Reserve Board",
     "fred_z1_results.json", lambda r: True),
]

roster, seen = [], Counter()
for label, publisher, fname, keep in SETS:
    rows = [r for r in json.loads((SB / fname).read_text()) if keep(r)]
    for r in rows:
        r["set"] = label
        r["publisher"] = publisher
        seen[r["series"]] += 1
    roster.extend(rows)
    print("%-58s %3d  %s" % (label, len(rows),
                             Counter(r["verdict"] for r in rows).most_common()))

problems = []
dupes = sorted(s for s, n in seen.items() if n > 1)
if dupes:
    problems.append("counted twice: %s" % dupes)
missing = sorted(set(ours) - set(seen))
if missing:
    problems.append("in the workbook but tied by nothing: %s" % missing)
extra = sorted(set(seen) - set(ours))
if extra:
    problems.append("tied but not in the workbook: %s" % extra)

print("\nworkbook series : %d" % len(ours))
print("roster lines    : %d" % len(roster))
print("distinct series : %d" % len(seen))
counts = Counter(r["verdict"] for r in roster)
print("verdicts        : %s" % dict(counts))

if problems:
    print("\nREFUSING to publish a roster that does not add up:")
    for p in problems:
        print("   " + p)
    sys.exit(1)

(SB / "fred_roster.json").write_text(json.dumps(roster, indent=1), encoding="utf-8")
print("\nroster written: %d of %d series, %d tied, %d differ, %d could not"
      % (len(roster), len(ours), counts.get("TIED", 0),
         counts.get("DIFFERS", 0), counts.get("COULD NOT", 0)))
