"""Step 4: every run's roster as one file, each line sorted into the change it checks, and the tallies the document
prints.

    python3 roster.py roster-q3.csv roster-scout.csv roster-flag.csv ... roster.csv > tallies.json

roster.csv has one row per figure read (run, change, tab, cell, figure, ours, source, diff, verdict, note). Every row
has exactly one verdict and one change, so the tallies are a partition: they add up to the number of rows.

The changes (the numbering of the brief, 30 Sep 2026: "everything built tonight"):
  1  Grids grey thin cells: each vs-the-book and vs-rest-of-band cell grey or not, the heat's bound over the cells
     not grey, the fewest loans, and What one cell says' grey line
  2  The book's own figure in the heading "vs the book (book: ...)", every measure, whole and filtered
  3  "Only loans where <column> is <value>", from Filter by (build 44734da4): every block of every grid, for every
     value, on the category books (SYS_FLAG) and the Year book (ORIG_YEAR, "(no date)" included)
  4  Loan size: the average and median booked per loan, and the two multiples, whole and filtered, with its panel
  5  Look's percentiles P10 to P90, the grey lines' places and the bars' short labels
  6  Borderline: every verdict shown in words (Pockets' Worse?, Paid-cost-kept's Together, Split's p cells, Start
     here's tile and its five largest, Record's Borderline now) and every pocket on _pockets (its flag, its Worse?
     flag, its standard error, and the rule applied to its own p and SE)
  7  Column widths: every displayed value against its column (widths_check.py), and the Grids blocks' one width
  8  ORIG_YEAR as Split by (build 44734da4): the Year-split book's Split tab, its split pockets and Record's split lines
  9  Band labels on whole-number columns (build 44734da4): each band label against the loans inside its range
  R  the re-run of 29 Sep's checks on this build: every other figure
"""
import csv
import json
import re
import sys
from collections import Counter

ORDER = ["DIFFERS", "COULD NOT", "TIED-WITHIN-SAMPLING", "TIED", "NAME", "ECHO", "NOT A FIGURE"]
CHANGES = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "R"]
BOOK = {"q3": "Consumer book Q3", "scout": "Scouting book", "flag": "Flag book", "two": "Two-flag book",
        "grey": "Grey book", "year": "Year book", "yearsplit": "Year-split book", "bureau": "Bureau book", "excel": "Consumer book Q3 (Excel-saved)",
        "excel-flag": "Flag book (Excel-saved)"}


def change(r):
    run, kind, tab, fig = r["run"], r.get("kind", ""), r["tab"], r["figure"]
    ours, src = str(r["ours"]), str(r["source"])
    if run.startswith("widths"):
        return "7"
    if kind == "band-label":
        return "9"
    if kind in ("grid-grey", "grid-bound", "grid-few") or (kind == "panel" and fig.endswith("The colour")
                                                           and (ours.startswith("Grey") or src.startswith("Grey"))):
        return "1"
    if kind in ("grid-head", "grid-bookfig"):
        return "2"
    if kind == "size-median" or (kind in ("grid", "panel") and "Loan size" in fig):
        return "4"
    if kind in ("grid", "panel") and " | where " in fig:
        return "3"
    if kind in ("look-label", "look-pline") or (kind == "look" and "percentile (P" in fig):
        return "5"
    if kind in ("pk-border", "pk-rule") or (kind == "pocket" and fig.endswith(" · worse")) or \
            (kind == "pck" and fig.endswith(" · together")) or (kind == "split-pocket" and fig.endswith(" · p")) or \
            (kind == "split-sum" and fig.endswith(" · p-value")) or (kind == "start-tile" and "charge-offs" in fig) \
            or (kind == "start-top" and fig.endswith(" · segment")) or "Borderline" in fig or "borderline" in ours:
        return "6"
    if run == "yearsplit" and (tab == "Split" or kind.startswith("split") or "ORIG_YEAR" in fig
                               or (tab == "Record" and re.search(r"Split|Families of tests|Reading a single red",
                                                                 fig))):
        return "8"
    return "R"


def main():
    rows = []
    for path in sys.argv[1:-1]:
        got = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
        if got and "column" in got[0]:
            # widths_check.py's rows: one per tab and column, and the Grids blocks from its .blocks.json
            for w in got:
                rows.append({"run": f"widths-{w['run']}", "kind": "widths", "tab": w["tab"],
                             "cell": f"{w['tab']}!{w['column']}",
                             "figure": f"column {w['column']}: every value shown, {w['cells checked']} cells",
                             "ours": w["worst"], "source": "fits its column (characters + 2; + 3 indented)",
                             "diff": w["cells that don't fit"] + " don't fit" if w["verdict"] == "DIFFERS" else "",
                             "verdict": w["verdict"], "note": w["what doesn't fit"]})
            for b in json.load(open(path[:-4] + ".blocks.json")):
                ok = b["same data width"] and b["same label width"] and b["band/loans under rate/book"]
                rows.append({"run": f"widths-{b['run']}", "kind": "widths", "tab": "Grids", "cell": "Grids!(blocks)",
                             "figure": "the four blocks: one data width, one label width (G1, G2, G5)",
                             "ours": f"data {b['data widths']}, labels {b['label widths']}",
                             "source": "one data width; both label columns equal",
                             "diff": "", "verdict": "TIED" if ok else "DIFFERS",
                             "note": f"{b['segments']} data columns a block"})
            continue
        rows += got
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
