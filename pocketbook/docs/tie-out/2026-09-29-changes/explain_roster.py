"""Print the DIFFERS and COULD NOT lines of a roster, grouped by the kind of figure, a few of each.

    python3 explain_roster.py roster.csv [how many of each]
"""
import collections
import csv
import sys

rows = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if r["verdict"] in ("DIFFERS", "COULD NOT")]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
by = collections.defaultdict(list)
for r in rows:
    by[(r["verdict"], r["tab"], r["figure"].split(" · ")[0] if r["tab"] != "Record" else r["cell"])].append(r)
for k, rs in sorted(by.items()):
    print(f"== {k} x{len(rs)}")
    for r in rs[:n]:
        print(f"   {r['cell']} | {r['figure'][:70]} | ours {r['ours'][:70]!r} | src {r['source'][:70]!r} | {r['diff'][:30]} "
              f"| {r['note'][:70]}")
