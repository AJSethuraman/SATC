"""Step 4: every run's roster as one file, each line sorted into the change it checks, and the tallies the document
prints.

    python3 roster.py roster-q3.csv roster-scout.csv roster-flag.csv ... roster.csv > tallies.json

roster.csv has one row per figure read (run, change, tab, cell, figure, ours, source, diff, verdict, note). Every row
has exactly one verdict and one change, so the tallies are a partition: they add up to the number of rows.

The changes (the numbering of the brief, 29 Sep 2026):
  1  Split by a category column: on the two category-split books, everything the split made -- the Split tab, the
     Pockets split by SYS_FLAG, the Grids split by SYS_FLAG and how common each value is, SYS_FLAG on Columns, and
     Record's split and family lines
  2  Grids' "What one cell says"
  3  Paid, cost, kept's chart: each dot, its colour, its number, and the names listed under it
  4  Look honouring Treat as Missing: the Bureau book's Look, the survey for codes, the "Answered missing" rows and
     the scatters' dots on every book, and the FICO block whose -9999 is now answered missing
  5  Dropdowns kept after an Excel-style save
  R  the re-run of 28 Sep's figures on this build (the Q3 bleed book and the scouting book), and, on the category
     books, every figure that is not the split's (tied again, on two new books)
"""
import csv
import json
import re
import sys
from collections import Counter

ORDER = ["DIFFERS", "COULD NOT", "TIED-WITHIN-SAMPLING", "TIED", "NAME", "ECHO", "NOT A FIGURE"]
CHANGES = ["1", "2", "3", "4", "5", "R"]
BOOK = {"bleed": "Consumer book Q3", "q3": "Consumer book Q3", "scout": "Scouting book", "flag": "Flag book",
        "two": "Two-flag book", "bureau": "Bureau book", "excel": "Consumer book Q3 (Excel-saved)",
        "excel-flag": "Flag book (Excel-saved)"}


def change(r):
    run, kind, tab, fig, cell = r["run"], r.get("kind", ""), r["tab"], r["figure"], r["cell"]
    if run.startswith("excel"):
        return "5"
    if run == "bureau" or kind in ("look-dots", "low-values") or "Answered missing" in fig or \
            (tab == "Look" and fig.startswith("FICO · Likely a code")):
        return "4"
    if kind == "panel":
        return "2"
    if kind in ("pck-dot", "pck-listed"):
        return "3"
    if run in ("flag", "two"):
        if tab == "Split" or "SYS_FLAG" in fig or kind == "groups" or \
                (tab == "Record" and re.search(r"Split|Families of tests|Reading a single red|Tests|Pockets tested",
                                               fig)):
            return "1"
    return "R"


def main():
    rows = []
    for path in sys.argv[1:-1]:
        rows += list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    for r in rows:
        r["change"] = change(r)
    fields = ["run", "change", "tab", "cell", "figure", "ours", "source", "diff", "verdict", "note"]
    with open(sys.argv[-1], "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    by_verdict = Counter(r["verdict"] for r in rows)
    assert sum(by_verdict.values()) == len(rows)
    assert set(by_verdict) <= set(ORDER), set(by_verdict) - set(ORDER)
    runs = list(dict.fromkeys(r["run"] for r in rows))
    by_tab = {}
    for r in rows:
        by_tab.setdefault(f'{r["run"]}|{r["tab"]}', Counter())[r["verdict"]] += 1
    print(json.dumps({
        "total": len(rows), "by_verdict": {v: by_verdict.get(v, 0) for v in ORDER},
        "by_run": {run: {v: sum(1 for r in rows if r["run"] == run and r["verdict"] == v) for v in ORDER}
                   for run in runs},
        "by_change": {c: {v: sum(1 for r in rows if r["change"] == c and r["verdict"] == v) for v in ORDER}
                      for c in CHANGES},
        "by_change_run": {c: {run: {v: sum(1 for r in rows if r["change"] == c and r["run"] == run
                                          and r["verdict"] == v) for v in ORDER} for run in runs} for c in CHANGES},
        "by_tab": {k: {v: c.get(v, 0) for v in ORDER} for k, c in by_tab.items()},
        "books": BOOK,
        "attention": [r for r in rows if r["verdict"] in ("DIFFERS", "COULD NOT")]}, indent=1))


if __name__ == "__main__":
    main()
