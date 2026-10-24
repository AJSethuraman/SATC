"""Check the checker: plant wrong figures in what was read out of the workbook and prove compare.py catches every one.

    python3 mutate.py figures.json expected.json [expected-flip.json]

It picks 200 named figures at random (seeded), moves each by one of: a number 0.5% off, a count one off, a
verdict word swapped, a p-value halved, a figure-in-words with one digit changed, and runs compare.py's judge on the
planted value. A plant that still reads TIED (or within sampling) is a hole in the check, and is printed.
"""
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare  # noqa: E402

figs = json.load(open(sys.argv[1]))
exp = json.load(open(sys.argv[2]))
E, meta = exp["expected"], exp["meta"]
rng = random.Random(28092026)
named = [f for f in figs if f["kind"] == "figure" and compare.normalise(f["key"]) in E]
caught = missed = 0
holes = []
for f in rng.sample(named, min(200, len(named))):
    v = f["value"]
    e = E[compare.normalise(f["key"])]
    if isinstance(v, bool) or v is None:
        continue
    if isinstance(v, (int, float)):
        if e.get("shuffled"):
            bad = v * 0.5 if v > 0.002 else v + 0.01          # well outside sampling
        elif isinstance(v, int) or float(v).is_integer():
            bad = v + 1
        else:
            bad = v * 1.005
    else:
        s = str(v)
        if s in ("Yes", "No", "Not sure", "Too few losses"):
            bad = {"Yes": "No", "No": "Yes", "Not sure": "Yes", "Too few losses": "No"}[s]
        elif re.search(r"\d", s):
            m = list(re.finditer(r"\d", s))[-1]
            bad = s[:m.start()] + str((int(m.group()) + 3) % 10) + s[m.end():]
        else:
            bad = s + " (changed)"
    verdict = compare.judge(f, bad, e, meta, {})[0]
    if verdict in ("TIED", "TIED-WITHIN-SAMPLING"):
        missed += 1
        holes.append((f["tab"], f["cell"], f["key"], v, bad))
    else:
        caught += 1
print(f"planted {caught + missed}, caught {caught}, missed {missed}")
for h in holes:
    print("  missed:", *h)
