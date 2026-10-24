"""Step 1 of the PocketBook road: every view of a workbook an analyst can pick, calculated.

    python3 views.py "Consumer book Q3 - PocketBook.xlsx" OUT

The full tie-out's views.py (28 Sep 2026), with one addition for this build: Grids now has a Row and a Column
dropdown (J13 and N13) that pick one cell for "What one cell says" to read out in words. Each view sets them too:

  - the 40 (or more) views that walk every Grid x Measure also walk the cells: view i picks the grid's inner
    cell number 7i (counting across, then down, wrapping), so different views read different cells;
  - then extra views, one per (grid, kind of cell, measure), picking the cells a blank or a word depends on: a
    pocket alone in its band, a pocket with loans whose comparison is blank (too few losses), a one-loan pocket,
    and an empty pocket -- each under Bad loans, and the alone one under Kept after losses too. Which cells those
    are is read from the workbook's own hidden _views sheet (the numbers the Run wrote), only to choose the picks.

The result tabs show one thing at a time through dropdown cells: Pockets (MEASURE, POCKETS, SHOW), Grids
(GRID, MEASURE, ROW, COLUMN), Split (GRID, MEASURE) and Paid, cost, kept (GRID), each found under its label. The
options are read from the workbook's own lists (_choices). LibreOffice calculates every copy with the repository's
own helper profile (pocketbook/tests/recalc.py: "recalculate Excel files on load: always"), in three batches at once.
Nothing here imports PocketBook.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tests"))          # pocketbook/tests, for recalc.py
import recalc  # noqa: E402


def options(wb):
    ws = wb["_choices"]
    heads = {ws.cell(1, c).value: c for c in range(1, ws.max_column + 1)}

    def col(name):
        c = heads[name]
        return [ws.cell(r, c).value for r in range(2, ws.max_row + 1) if ws.cell(r, c).value not in (None, "")]
    return {"pockets_measure": col("Pockets: Measure"), "pockets_kind": col("Pockets: Pockets"),
            "grids_grid": col("Grids: Grid"), "grids_measure": col("Grids: Measure"),
            "split_grid": col("Split: Grid"), "split_measure": col("Split: Measure"),
            "pck_grid": col("Paid, cost, kept: Grid")}


def below(ws, label):
    """The dropdown under a label ("GRID", "MEASURE", ...): the cell beneath the first cell that holds it. The tabs'
    rows move with the note above them (a category split's note has one more line), so no cell is typed here."""
    for row in ws.iter_rows(min_row=8, max_row=40, max_col=16):
        for c in row:
            if c.value == label:
                return ws.cell(c.row + 1, c.column)
    raise KeyError(f"{ws.title}: no {label}")


def views_rows(wb):
    ws = wb["_views"]
    out = {}
    for r in range(1, ws.max_row + 1):
        k = ws.cell(r, 1).value
        if isinstance(k, str) and k.startswith("G|"):
            vals, c = [], 2
            while c <= ws.max_column:
                vals.append(ws.cell(r, c).value)
                c += 1
            out[k] = vals
    return out


def grid_cells(V, grid):
    """The grid's rows and columns (All left off), its loans by cell, and the Bad loans / Kept after losses book and
    band values by cell -- as the Run wrote them on _views."""
    rows = [x for x in V[f"G|{grid}|rows"] if x not in (None, "All")]
    cols = [x for x in V[f"G|{grid}|cols"] if x not in (None, "All")]
    loans, blk = {}, {}
    for i, r in enumerate(rows, start=1):
        for j, c in enumerate(cols):
            loans[(r, c)] = V[f"G|{grid}|loans|{i}"][j]
            for m in ("outcome_loans", "ranr_rate"):
                blk[(m, "book", r, c)] = V[f"G|{grid}|{m}|book|{i}"][j]
                blk[(m, "band", r, c)] = V[f"G|{grid}|{m}|band|{i}"][j]
    return rows, cols, loans, blk


def specials(V, grid):
    rows, cols, loans, blk = grid_cells(V, grid)
    has = {k: v for k, v in loans.items() if isinstance(v, (int, float)) and v > 0}
    mates = lambda k: sum(1 for j in has if j[0] == k[0])            # noqa: E731
    out = []
    alone = [k for k in has if mates(k) == 1]
    few = [k for k in has if mates(k) > 1 and blk[("outcome_loans", "book", *k)] is None]
    one = [k for k in has if has[k] == 1]
    empty = [k for k in loans if k not in has]
    for what, ks, measures in (("alone", alone, ("Bad loans", "Kept after losses")), ("few", few, ("Bad loans",)),
                               ("one loan", one, ("Bad loans", "Charge-offs")), ("empty", empty, ("Bad loans",))):
        if ks:
            for m in measures:
                out.append((what, ks[0], m))
    return out


def main():
    book, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    (out / "set").mkdir(parents=True, exist_ok=True)
    wb = load_workbook(book)
    opt = options(wb)
    V = views_rows(wb)
    pockets = [(m, k) for k in opt["pockets_kind"] for m in opt["pockets_measure"]]
    grids = [(g, m) for g in opt["grids_grid"] for m in opt["grids_measure"]]
    split = [(g, m) for g in opt["split_grid"] for m in opt["split_measure"]]
    pck = opt["pck_grid"]
    n = max(len(pockets), len(grids), len(split), len(pck))
    todo = []
    for i in range(n):
        g, m = grids[i % len(grids)]
        rows, cols, _, _ = grid_cells(V, g)
        inner = [(r, c) for r in rows for c in cols]
        cell = inner[(7 * i) % len(inner)]
        todo.append({"pockets": pockets[i % len(pockets)], "grids": [g, m], "cell": list(cell),
                     "split": split[i % len(split)], "pck": pck[i % len(pck)], "why": "every view"})
    for g in opt["grids_grid"]:
        for what, cell, m in specials(V, g):
            todo.append({"pockets": pockets[0], "grids": [g, m], "cell": list(cell), "split": split[0],
                         "pck": pck[0], "why": what})
    plan = []
    for i, v in enumerate(todo):
        wb = load_workbook(book)
        ws = wb["Pockets"]
        below(ws, "MEASURE").value, below(ws, "POCKETS").value, below(ws, "SHOW").value = (*v["pockets"], "All")
        ws = wb["Grids"]
        below(ws, "GRID").value, below(ws, "MEASURE").value = v["grids"]
        below(ws, "ROW").value, below(ws, "COLUMN").value = v["cell"]
        ws = wb["Split"]
        below(ws, "GRID").value, below(ws, "MEASURE").value = v["split"]
        below(wb["Paid, cost, kept"], "GRID").value = v["pck"]
        name = f"view-{i:02d}.xlsx" if i < 100 else f"view-{i}.xlsx"
        wb.save(out / "set" / name)
        plan.append({"file": name, **v})
    (out / "plan.json").write_text(json.dumps(plan, indent=1))
    files = sorted(str(p) for p in (out / "set").glob("view-*.xlsx"))
    batches = [files[k::3] for k in range(3)]
    procs = []
    for b in batches:
        prof = Path(tempfile.mkdtemp(prefix="tieout-lo-"))
        (prof / "user").mkdir(parents=True)
        (prof / "user" / "registrymodifications.xcu").write_text(recalc.PROFILE_XCU, encoding="utf-8")
        procs.append(subprocess.Popen([recalc.SOFFICE, f"-env:UserInstallation={prof.as_uri()}", "--headless",
                                       "--calc", "--convert-to", "xlsx", "--outdir", str(out / "calculated"), *b],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    codes = [p.wait(timeout=6000) for p in procs]
    done = sorted((out / "calculated").glob("view-*.xlsx"))
    print(f"{len(done)} of {len(files)} views calculated", codes)
    shutil.copy(book, out / "as-written.xlsx")


if __name__ == "__main__":
    main()
