"""Print a few of this tie-out's figures, the workbook's beside the loan-file road's, for the pictures.

    python3 explain_new.py split WORK two "FICO x CHANNEL · SYS_FLAG Y vs N"
    python3 explain_new.py panel WORK flag "FICO x CHANNEL / SYS_FLAG" "Bad loans" "496 - 653" "Online · (blank)"
    python3 explain_new.py dots WORK q3 "FICO x CHANNEL"

Nothing here imports PocketBook: it reads the two JSON files the two roads wrote.
"""
import json
import sys
from pathlib import Path

what, work, book = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
figs = json.load(open(work / f"views-{book}" / "figures.json"))
exp = json.load(open(work / f"expected-{book}.json"))["expected"]


def ex(key):
    got = exp.get(json.dumps(key))
    return None if got is None else got["value"]


def wb(pred):
    return next((f for f in figs if f["kind"] == "figure" and pred(f["key"])), None)


def show(v):
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, list):
        return "[" + ", ".join(show(x) for x in v) + "]"
    return str(v)


if what == "split":
    label = sys.argv[4]
    print(f"{'Bad loans, ' + label:<60}")
    print(f"{'figure':<26} {'workbook':>26} {'loan file':>26}")
    for h in ("Pockets", "Worse than the rest in", "Value vs rest, all", "Range", "p-value", "As odds",
              "p-value, as odds"):
        f = wb(lambda k: k[:4] == ["split-sum", label, "Bad loans", h])
        print(f"{h:<26} {show(f['value'] if f else None):>26} {show(ex(['split-sum', label, 'Bad loans', h])):>26}")
    f = wb(lambda k: k[:2] == ["split-differ", label])
    b3 = exp[json.dumps(["split-differ", label])].get("b3")
    print("\nDo the values differ at all (B3), this road: Q %.6f on %d df, p %.3g, %d pockets" % tuple(b3))
    from openpyxl import load_workbook
    vw = load_workbook(work / f"views-{book}" / "as-written.xlsx", read_only=True)["_views"]
    for row in vw.iter_rows(values_only=True):
        if row[0] == f"S|{label}|sum|1":
            print("Do the values differ at all (B3), the workbook's own record (_views): p %.3g on %s df, %s pockets"
                  % (row[12], row[13], row[14]))
    print("workbook:", f["value"][:118])
elif what == "panel":
    grid, m, r, c = sys.argv[4:8]
    for lab in ("name", "Rate", "vs the book", "vs rest of band", "Loans", "The colour"):
        k = ["panel", grid, m, r, c, lab]
        f = wb(lambda kk: kk == k)
        print(f"{lab:<16} workbook  {show(f['value'])[:100]}")
        print(f"{'':<16} loan file {show(ex(k))[:100]}")
elif what == "dots":
    grid = sys.argv[4]
    print(f"{'band':<16} {'segment':<8} {'x (cost)':>9} {'y (kept)':>9} {'Together':<28} {'colour':<7} {'no.':>3}"
          f"   loan file: colour, no.")
    rows = [f for f in figs if f["kind"] == "figure" and f["key"][:2] == ["pck-dot", grid] and f["key"][-1] == "x"]
    for f in rows:
        _, g, b, s, _ = f["key"]
        get = lambda w: (wb(lambda k: k == ["pck-dot", g, b, s, w]) or {}).get("value")  # noqa: E731
        tog = ex(["pck", g, b, s, "together"]) or ""
        x, y = get("x"), get("y")
        print(f"{b:<16} {s:<8} {show(x) if x is not None else '-':>9.9} {show(y) if y is not None else '-':>9.9} "
              f"{tog:<28} {get('colour'):<7} {show(get('number')) if get('number') else '':>3}   "
              f"{ex(['pck-dot', g, b, s, 'colour'])}, {ex(['pck-dot', g, b, s, 'number']) or ''}")
