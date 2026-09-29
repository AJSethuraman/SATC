"""Step 4: the two runs' rosters as one file, and the tallies the document prints.

    python3 roster.py roster-bleed.csv roster-scout.csv roster.csv > tallies.json

roster.csv has one row per figure read (tab, cell, figure, ours, source, diff, verdict, and the run and a note).
Every row has exactly one verdict, so the tallies are a partition: they add up to the number of rows.
"""
import csv
import json
import sys
from collections import Counter

ORDER = ["DIFFERS", "COULD NOT", "TIED-WITHIN-SAMPLING", "TIED", "NAME", "ECHO", "NOT A FIGURE"]
rows = []
for path in sys.argv[1:3]:
    rows += list(csv.DictReader(open(path, newline="", encoding="utf-8")))
fields = ["run", "tab", "cell", "figure", "ours", "source", "diff", "verdict", "note"]
with open(sys.argv[3], "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in fields})
by_verdict = Counter(r["verdict"] for r in rows)
by_tab = {}
for r in rows:
    t = by_tab.setdefault(f'{r["run"]}|{r["tab"]}', Counter())
    t[r["verdict"]] += 1
assert sum(by_verdict.values()) == len(rows)
assert set(by_verdict) <= set(ORDER), set(by_verdict) - set(ORDER)
print(json.dumps({"total": len(rows), "by_verdict": {v: by_verdict.get(v, 0) for v in ORDER},
                  "by_run": {run: {v: sum(1 for r in rows if r["run"] == run and r["verdict"] == v) for v in ORDER}
                             for run in ("bleed", "scout")},
                  "by_tab": {k: {v: c.get(v, 0) for v in ORDER} for k, c in by_tab.items()},
                  "attention": [r for r in rows if r["verdict"] in ("DIFFERS", "COULD NOT")]}, indent=1))
