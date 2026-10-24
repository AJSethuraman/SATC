"""A closer look at "Do the values differ at all?": the tab prints the p-value only as "under 0.0001" when it is that
small, so the sentence ties loosely. The workbook keeps the p-value itself on its hidden _views sheet (the cell the
sentence is built from); this sets it beside the loan-file road's to six figures, for every grid of both category
books. A supplementary check: hidden cells are not counted on the roster.

    python3 b3_hidden.py WORK
"""
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

work = Path(sys.argv[1])
worst = 0.0
for book in ("flag", "two"):
    exp = json.load(open(work / f"expected-{book}.json"))["expected"]
    vw = load_workbook(work / f"views-{book}" / "as-written.xlsx", read_only=True)["_views"]
    rows = {r[0]: r for r in vw.iter_rows(values_only=True) if isinstance(r[0], str) and r[0].startswith("S|")}
    for k, e in exp.items():
        key = json.loads(k)
        if key[0] != "split-differ" or not e.get("b3"):
            continue
        q, df, p, n = e["b3"]
        r = rows[f"S|{key[1]}|sum|1"]
        rel = abs(r[12] - p) / p
        worst = max(worst, rel)
        print(f"{book:5s} {key[1]:48s} workbook p {r[12]:.6g} df {r[13]} pockets {r[14]} | loan file p {p:.6g} "
              f"df {df} pockets {n} | {'TIED' if rel < 1e-6 and r[13] == df and r[14] == n else 'DIFFERS'}")
print(f"largest relative difference {worst:.2g}")
