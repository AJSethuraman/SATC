"""The evening's checks counted, book by book and kind by kind, for the report: every roster line the changes of
30 Sep 2026 made (roster.py's change 1 to 6), by what it checks and its verdict.

    python3 explain_new.py WORK q3 flag two grey
"""
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import roster  # noqa: E402

W = Path(sys.argv[1])
for run in sys.argv[2:]:
    rows = list(csv.DictReader(open(W / f"roster-{run}.csv", encoding="utf-8")))
    c = collections.Counter()
    for r in rows:
        ch = roster.change(r)
        if ch != "R":
            what = r["kind"]
            if r["kind"] == "grid":
                what = "grid: " + ("Loan size" if "Loan size" in r["figure"] else "filtered" if " | where " in
                                   r["figure"] else "whole")
            if r["kind"] == "panel":
                what = "panel: " + ("grey" if str(r["ours"]).startswith("Grey") else "Loan size" if "Loan size" in
                                    r["figure"] else "filtered" if " | where " in r["figure"] else "other")
            c[(ch, what, r["verdict"])] += 1
    print(f"== {run}")
    for k, v in sorted(c.items()):
        print("  ", *k, v)
    grey = [r for r in rows if r["kind"] == "grid-grey"]
    print("   grey cells:", sum(1 for r in grey if r["ours"] == "True"), "of", len(grey), "numbers in vs the book / vs "
          "rest of band are grey")
