"""The borderline flags side by side, for the report: every pocket on _pockets whose p-value was shuffled, the flag
the workbook printed and the one this road worked out, and where they differ, both p-values and this road's SE.

    python3 explain_border.py WORK q3 flag two grey
"""
import csv
import json
import sys
from pathlib import Path

W = Path(sys.argv[1])
for run in sys.argv[2:]:
    rows = [r for r in csv.DictReader(open(W / f"roster-{run}.csv", encoding="utf-8")) if r["kind"] == "pk-border"
            and r["figure"].endswith(" · any")]
    exp = json.load(open(W / f"expected-{run}.json"))["expected"]
    wb = sum(1 for r in rows if r["ours"])
    mine = sum(1 for r in rows if r["source"])
    both = sum(1 for r in rows if r["ours"] and r["source"])
    same = sum(1 for r in rows if r["ours"] and r["ours"] == r["source"])
    rule = [r for r in csv.DictReader(open(W / f"roster-{run}.csv", encoding="utf-8")) if r["kind"] == "pk-rule"]
    print(f"{run}: {len(rows)} pockets on _pockets; flagged borderline by the workbook {wb}, by this road {mine}, "
          f"by both {both} (the same printed p on {same}); the rule on the workbook's own p and SE: "
          f"{sum(1 for r in rule if r['verdict'] == 'TIED')} of {len(rule)} TIED")
    for r in rows:
        if r["ours"] != r["source"]:
            print(f"   {r['figure'][:-6]}: workbook {r['ours'] or '-'}, this road {r['source'] or '-'}  "
                  f"[{r['verdict']}] {r['note'][:150]}")
