"""Put what Excel said beside what was expected, and write RESULT.md.

Run from threshold-engine/ after walk.ps1. A number passes within 1e-9 of the
expected (relative, or absolute near zero); text passes only exactly.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
exp = json.load(open(HERE / "steps.json", encoding="utf-8"))
obs = json.load(open(HERE / "out" / "observed.json", encoding="utf-8-sig"))
low = json.load(open(HERE / "out" / "observed-low.json", encoding="utf-8-sig"))
exp["steps"] += json.load(open(HERE / "steps-low.json", encoding="utf-8"))["steps"]
obs["steps"] += low["steps"]
restored_low = all(t == "" for t in low.get("check_after", []))
SHEETS = ["Thresholds", "Settings", "Assess", "Chart", "Evidence", "Backtest", "Glossary", "Data", "Run"]


def same(want, got):
    v, t = got.get("value"), got.get("text")
    if isinstance(want, bool):
        return v is want or t == str(want).upper()
    if isinstance(want, (int, float)):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and \
            math.isclose(v, want, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(want, str) and want.startswith("#"):
        return t == want
    if want == "":
        return v in (None, "") and t == ""
    return v == want or t == want


def show(x):
    if isinstance(x, float):
        return "%.6f" % x
    return "(blank)" if x in ("", None) else str(x)


rows, fails = [], []
by_id = {s["id"]: s for s in obs["steps"]}
for s in exp["steps"]:
    got = by_id.get(s["id"])
    if not got:
        fails.append((s["id"], "not run", "", ""))
        rows.append((s, None, 0))
        continue
    bad = 0
    for want, g in zip(s["reads"], got["reads"]):
        assert (want["sheet"], want["cell"]) == (g["sheet"], g["cell"])
        if not same(want["expected"], g):
            bad += 1
            fails.append((s["id"], "%s!%s" % (want["sheet"], want["cell"]), show(want["expected"]),
                          show(g.get("value")) + " / " + show(g.get("text"))))
    rows.append((s, got, bad))

total = sum(len(s["reads"]) for s in exp["steps"])
sheets_ok = obs["sheets"] == SHEETS
restored = all(t == "" for t in obs.get("check_after", [])) and restored_low
lines = ["# Walkthrough result", "",
         "Excel %s, workbook `%s`." % (obs["excel"], Path(obs["workbook"]).name), "",
         "**%d of %d cells as expected, in %d of %d steps.** Tabs in order: %s. Workbook back as built after "
         "every step: %s." % (total - len(fails), total, sum(1 for _, g, b in rows if g and not b), len(rows),
                               "yes" if sheets_ok else "NO: %s" % obs["sheets"], "yes" if restored else "NO"), "",
         "| Step | What | Cells | Result |", "|---|---|---|---|"]
for s, g, b in rows:
    lines.append("| %s | %s | %d | %s |" % (s["id"], s["title"], len(s["reads"]),
                                           "not run" if g is None else ("as expected" if not b else "%d differ" % b)))
if fails:
    lines += ["", "## Differences", "", "| Step | Cell | Expected | Excel (value / text) |", "|---|---|---|---|"]
    lines += ["| %s | %s | %s | %s |" % f for f in fails]
(HERE / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:5]))
for f in fails:
    print(f)
sys.exit(1 if fails or not sheets_ok or not restored else 0)
