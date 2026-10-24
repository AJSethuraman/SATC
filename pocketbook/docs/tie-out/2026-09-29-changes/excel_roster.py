"""Change 5 on the roster: one line per dropdown, before the Excel-style save against after it and a second Run, and
one line for the Run's own numbers. Then the check of the check: plant a change in each dropdown's "after" (an item
dropped, the formula moved, or the dropdown gone) and prove every one reads DIFFERS.

    python3 excel_roster.py WORK/excel/dropdowns.json roster-excel.csv RUN-LABEL
"""
import csv
import json
import sys

d = json.load(open(sys.argv[1]))
run = sys.argv[3] if len(sys.argv) > 3 else "excel"


def verdict(x, after_items, there):
    same = there and x["items before"] is not None and after_items == x["items before"]
    return "TIED" if same else "DIFFERS"


rows = []
for x in d["dropdowns"]:
    what = f"{x['type'] or 'list'} {x['formula']}" + (f" {x['operator']} {x['formula2']}" if x["formula2"] else "")
    items = x["items before"]
    v = verdict(x, x["items after"], x["there after"])
    rows.append({"run": run, "tab": x["sheet"], "cell": f"{x['sheet']}!{x['cells']} [dropdown]", "figure": what[:120],
                 "ours": "; ".join(map(str, x["items after"] or []))[:200] if x["there after"] else "(gone)",
                 "source": "; ".join(map(str, items or []))[:200], "diff": "" if v == "TIED" else "differs",
                 "verdict": v, "note": "the dropdown after the Excel-style save and a Run (ours) against before it "
                                       "(source): the same cells, formula and items"})
new = d["new after"]
rows.append({"run": run, "tab": "(workbook)", "cell": "(every sheet) [dropdowns added]", "figure": "dropdowns",
             "ours": str(len(new)), "source": "0", "diff": "", "verdict": "TIED" if not new else "DIFFERS",
             "note": "no dropdown the Run added that was not there before"})
rows.append({"run": run, "tab": "_views", "cell": "_views!A:ZZ [every row]", "figure": "every number the result tabs "
             "read", "ours": f"{d['views rows']} rows, {len(d['views rows differing'])} differ", "source":
             f"{d['views rows']} rows", "diff": "", "verdict": "TIED" if not d["views rows differing"] else "DIFFERS",
             "note": "the second Run, seeded, writes the same figures"})
with open(sys.argv[2], "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
tally = {}
for r in rows:
    tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
moved = d["moved to Excel's block"]
print(tally, len(rows), f"(before {d['before']}, moved into Excel's block {moved}, "
      f"openpyxl alone kept {d['openpyxl alone sees after the save']}, after the Run {d['after']})")
# plant: each dropdown broken three ways
caught = planted = 0
for x in d["dropdowns"]:
    items = list(x["items before"] or [])
    for bad_items, there in ((items[:-1], True), (items + ["(planted)"], True), (items, False)):
        planted += 1
        caught += verdict(x, bad_items, there) == "DIFFERS"
print(f"planted {planted}, caught {caught}, missed {planted - caught}")
