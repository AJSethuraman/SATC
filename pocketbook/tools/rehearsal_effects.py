"""Read what a Run found out of the workbook it wrote, as aggregates, for checking against published effects.

    python tools/rehearsal_effects.py WORKBOOK.xlsx [--measure outcome_loans] [--grids "A x B" ...]

For the public-data rehearsal (docs/rehearsal-public-data-2026-09.md). Two things per grid, read from the hidden
sheets the result tabs point at (nothing is recomputed from the loans):

- the margins: each segment's rate over every band (the grid's All row) and each band's rate over every segment
  (its All column), with loans, from `_views` (`G|<grid>|<measure>|rate|<row>`, `G|<grid>|loans|<row>`);
- the pockets: for each segment value, how many of its pockets read worse and how many better, from `_pockets`'
  stored multiples and p-values, judged as Control was answered (--worse-at, --better-at, --confidence, and against
  the rest of the band, or the book with --against book). The workbook's own verdicts are Excel formulas and are not
  calculated by openpyxl; this is the same rule applied in Python to the same stored numbers, and says so.

Aggregates only: no loan is read.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook


def read(book: Path, measure: str, worse_at: float, better_at: float, confidence: float, against: str) -> dict:
    wb = load_workbook(book, read_only=True, data_only=False)
    views = {}
    for r in wb["_views"].iter_rows(values_only=True):
        if r and isinstance(r[0], str):
            views[r[0]] = list(r[1:])
    grids = sorted({k.split("|")[1] for k in views if k.startswith("G|") and k.endswith("|cols")})
    out = {}
    for g in grids:
        cols = [c for c in views[f"G|{g}|cols"] if c is not None]
        rows = [c for c in views[f"G|{g}|rows"] if c is not None]
        ai, aj = rows.index("All"), cols.index("All")
        rate = {i: views.get(f"G|{g}|{measure}|rate|{i + 1}") for i in range(len(rows))}   # rows count from 1
        loans = {i: views.get(f"G|{g}|loans|{i + 1}") for i in range(len(rows))}
        if rate[ai] is None:
            continue
        seg = {cols[j]: (rate[ai][j], loans[ai][j]) for j in range(len(cols)) if cols[j] != "All"}
        band = {rows[i]: (rate[i][aj], loans[i][aj]) for i in range(len(rows)) if rows[i] != "All"}
        out[g] = {"topline": rate[ai][aj], "loans": loans[ai][aj], "segments": seg, "bands": band,
                  "pockets": defaultdict(lambda: {"worse": 0, "better": 0, "other": 0})}
    ws = wb["_pockets"]
    head = None
    bar = round(1 - confidence, 12)
    for r in ws.iter_rows(values_only=True):
        if head is None:
            if r and r[0] == "Grids or three-way":
                head = {h: i for i, h in enumerate(r) if h}
            continue
        if r[head["Rate (key)"]] != measure or r[0] != "grids" or r[head["Grid"]] not in out:
            continue
        few = r[head["Too few losses to test (fewest losses is a Run setting)"]]
        alone = r[head["Alone in its band"]]
        if against == "band" and not alone:
            gap, p = r[head["Vs rest of band"]], r[head["p-value vs band, after the allowance"]]
        else:
            gap, p = r[head["Vs rest of book (a multiple; profit: the gap, 0.01 = 1 point)"]], \
                r[head["p-value vs book, after the allowance"]]
        tally = out[r[head["Grid"]]]["pockets"][str(r[head["Segment"]])]
        if few or gap is None or p is None:
            tally["other"] += 1
        elif gap >= worse_at and p < bar:
            tally["worse"] += 1
        elif gap <= better_at and p < bar:
            tally["better"] += 1
        else:
            tally["other"] += 1
    wb.close()
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="rehearsal_effects")
    p.add_argument("book", type=Path)
    p.add_argument("--measure", default="outcome_loans")
    p.add_argument("--grids", nargs="*")
    p.add_argument("--worse-at", type=float, required=True)
    p.add_argument("--better-at", type=float, required=True)
    p.add_argument("--confidence", type=float, required=True)
    p.add_argument("--against", choices=("band", "book"), required=True)
    a = p.parse_args(argv)
    got = read(a.book, a.measure, a.worse_at, a.better_at, a.confidence, a.against)
    for g, x in got.items():
        if a.grids and g not in a.grids:
            continue
        print(f"== {g}: {a.measure} topline {x['topline']:.4%} over {x['loans']:,} loans")
        print("  segments (All row), highest first:")
        for s, (rate, n) in sorted(x["segments"].items(), key=lambda t: -(t[1][0] or 0)):
            t = x["pockets"].get(s, {"worse": 0, "better": 0, "other": 0})
            print(f"    {s:<42} {rate:8.2%}  n={n:>9,}  pockets worse {t['worse']}, better {t['better']}, "
                  f"neither/untested {t['other']}")
        print("  bands (All column):")
        for b, (rate, n) in x["bands"].items():
            print(f"    {b:<42} {rate:8.2%}  n={n:>9,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
