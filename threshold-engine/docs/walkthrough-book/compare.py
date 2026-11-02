"""Put what Excel said beside what was expected, read by read. Writes RESULT.md.

Run from threshold-engine/ after walk.ps1:  python docs/walkthrough-book/compare.py
A number passes within 1e-9 of the expected value; text, lists and the
slicer picks must be exactly equal; 'contains' and 'startswith' reads say so.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
plan = json.loads((HERE / "steps.json").read_text(encoding="utf-8"))
obs = json.loads((HERE / "out" / "observed.json").read_text(encoding="utf-8-sig"))
got_by = {s["id"]: s for s in obs["steps"]}


def norm(v):
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def ok(read, got):
    v = got["value"]
    if "contains" in read:
        return isinstance(v, str) and read["contains"] in v
    if "startswith" in read:
        return isinstance(v, str) and v.startswith(read["startswith"])
    want = read["expect"]
    if v is None and want == "":
        return True
    if isinstance(want, (int, float)) and not isinstance(want, bool) and isinstance(v, (int, float)):
        return math.isclose(float(v), float(want), rel_tol=0, abs_tol=1e-9)
    if want == [] and v in ({}, None, "", []):                    # PowerShell hands an empty list back as {}
        return True
    if read.get("special") == "visible_rows" and not isinstance(v, list):
        v = [] if v in (None, "") else [v]
    return norm(v) == norm(want)


lines = ["# Result: the book walkthrough", "",
         "Excel %s, `%s`. Each read: what the step expected, what Excel said." % (obs["excel"], obs["workbook"]), ""]
total = passed = 0
failures = []
for s in plan["steps"]:
    g = got_by.get(s["id"])
    if g is None:
        failures.append("%s: not run" % s["id"])
        lines += ["## %s · %s: NOT RUN" % (s["id"], s["what"]), ""]
        continue
    n_ok = 0
    rows = []
    for read, got in zip(s["reads"], g["reads"]):
        total += 1
        good = ok(read, got)
        n_ok += good
        passed += good
        where = read.get("special") or "%s!%s" % (read["sheet"], read["cell"])
        want = read.get("expect", read.get("contains", read.get("startswith")))
        if not good:
            failures.append("%s %s: expected %r, Excel said %r" % (s["id"], where, want, got["value"]))
        rows.append("| %s | %s | %s | %s |" % ("ok" if good else "**DIFFERS**", where, str(want)[:90].replace("|", "/"),
                                              str(got["value"])[:90].replace("|", "/")))
    lines += ["## %s · %s: %d of %d" % (s["id"], s["what"], n_ok, len(s["reads"])), "", s["shows"] + ".", "",
              "| | Cell | Expected | Excel |", "|---|---|---|---|"] + rows + [""]
lines[3:3] = ["**%d of %d reads as expected.**" % (passed, total), ""] + (
    ["Differences:", ""] + ["- " + f for f in failures] + [""] if failures else ["No differences.", ""])
(HERE / "RESULT.md").write_text("\n".join(lines), encoding="utf-8")
print("%d of %d reads as expected" % (passed, total))
for f in failures:
    print("  " + f)
