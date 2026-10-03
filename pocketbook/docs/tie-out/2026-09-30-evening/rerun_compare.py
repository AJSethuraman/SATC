"""The re-run against 28 Sep: every cell the full tie-out read, looked up in this build's roster by the same cell (and
view), and sorted by what happened to it -- the same figure and the same verdict; the figure moved; the verdict moved.

    python3 rerun_compare.py ../2026-09-28-full/roster.csv roster-q3.csv bleed roster-scout.csv scout > rerun.json
"""
import collections
import csv
import json
import sys

old = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8"))]
pairs = [(sys.argv[i], sys.argv[i + 1]) for i in range(2, len(sys.argv), 2)]
GOOD = ("TIED", "TIED-WITHIN-SAMPLING")


SEEN = collections.Counter()


def ident(r, fresh=False):
    """A figure is found again by what it is (its tab and its name: the grid, measure, pocket and column) -- a
    block that moved down the tab is the same figure. Record by its cell (its names were cells on 28 Sep). Words and
    names, which have no name of their own, by their text: the n-th time a text shows on a tab in a view."""
    view = r["cell"].split(" [")[1] if " [" in r["cell"] else ""
    if r["tab"] == "Record":
        # by its name (30 Sep 2026: Record gained rows, so a cell holds another line now): the label it sits under on
        # the bleed books, the cell it held on 29 Sep on the scouting book (read_scout.py names it so); words by cell
        return ("Record", r["figure"]) if r["figure"] else r["cell"]
    if not r["figure"]:
        k = (r["tab"], view, r["ours"])
        SEEN[k] += 1
        return k + (SEEN[k],)
    if r["tab"] == "Split" and " · " not in r["figure"]:
        return (r["tab"], r["figure"], r["cell"].split("!")[1][0])
    return (r["tab"], r["figure"])
out = {}
for path, run in pairs:
    new = {}
    SEEN.clear()
    for r in csv.DictReader(open(path, encoding="utf-8")):
        new.setdefault(ident(r), r)
    was = [r for r in old if r["run"] == run]
    SEEN.clear()
    ids = [ident(r) for r in was]
    t = collections.Counter()
    moved, verdicts, gone = [], [], []
    for r, i in zip(was, ids):
        n = new.get(i)
        if n is None:
            t["not read on this build"] += 1
            gone.append([r["cell"], r["figure"], r["ours"], r["verdict"]])
            continue
        same_fig = n["ours"] == r["ours"]
        t[("same figure" if same_fig else "figure moved") + ", " + (
            "same verdict" if n["verdict"] == r["verdict"] else f"{r['verdict']} -> {n['verdict']}")] += 1
        if not same_fig:
            moved.append([r["cell"], r["figure"], r["ours"], n["ours"], r["verdict"], n["verdict"]])
        if r["verdict"] in GOOD and n["verdict"] not in GOOD:
            verdicts.append([r["cell"], r["figure"], r["ours"], n["ours"], r["verdict"], n["verdict"], n["note"]])
    out[run] = {"cells read on 28 Sep": len(was), "tally": dict(t), "tied then, not now": verdicts,
                "figures that moved": moved, "not read now": gone,
                "new cells on this build": len(set(new) - set(ids))}
print(json.dumps(out, indent=1))
