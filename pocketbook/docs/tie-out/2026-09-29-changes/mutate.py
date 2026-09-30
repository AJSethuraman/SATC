"""Check the checker: plant wrong figures in what was read out of the workbook and prove compare.py catches every one.

    python3 mutate.py figures.json expected.json [ONLY]

The full tie-out's mutate.py (28 Sep 2026): it picks 200 named figures at random (seeded), moves each by one of: a
number 0.5% off, a count one off, a verdict word swapped, a p-value halved, a figure-in-words with one digit changed,
and runs compare.py's judge on the planted value. A plant that still reads TIED (or within sampling) is a hole in the
check, and is printed.

29 Sep 2026: with ONLY (comma-separated key kinds, e.g. panel,split-sum,split-pocket,split-differ,pck-dot,pck-listed,
look,look-dots,low-values) it plants only in the figures this tie-out's changes added, up to 200, and knows how to
break the new kinds too: a sentence gets one digit changed or, with no digit, one word ("blank" for "pale", "alone"
for "fewer"); a dot's colour is swapped red/green/none; a dot's number moves by one; a coordinate list is flipped;
a scatter gets one dot that is an answered-missing loan's value; the survey gets a bureau code on a result tab.
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
ONLY = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
E, meta = exp["expected"], exp["meta"]
rng = random.Random(28092026)
named = [f for f in figs if f["kind"] == "figure" and compare.normalise(f["key"]) in E
         and (ONLY is None or f["key"][0] in ONLY)]
caught = missed = 0
holes = []
SWAP = {"bigger in some pockets": "no sign the gap differs", "no sign the gap differs": "bigger in some pockets",
        "pale": "light red", "light red": "red", "red": "deep red", "deep red": "pale", "green": "light green",
        "light green": "green", "blank": "pale", "more": "less", "less": "more", "alone": "not alone",
        "fewer": "more", "yes": "no sign they do", "Net drain": "Strong", "Strong": "Net drain"}


def break_text(s):
    if re.search(r"\d", s):
        m = list(re.finditer(r"\d", s))[-1]
        return s[:m.start()] + str((int(m.group()) + 3) % 10) + s[m.end():]
    for a, b in SWAP.items():
        if re.search(rf"\b{re.escape(a)}\b", s):
            return re.sub(rf"\b{re.escape(a)}\b", b, s, count=1)
    return s + " (changed)"


kinds = {}
for f in rng.sample(named, min(200, len(named))):
    v = f["value"]
    e = E[compare.normalise(f["key"])]
    k0, last = f["key"][0], f["key"][-1]
    if isinstance(v, bool):
        continue
    if k0 == "look-dots":
        bad = v[:-1] + [[meta.get("codes", [-99000901])[0], v[-1][1]]]
    elif k0 == "low-values":
        bad = v + [["Look", "C72", meta.get("codes", [-99000901])[0], "visible"]]
    elif k0 == "pck-dot" and last == "colour":
        bad = {"red": "green", "green": "none", "none": "red"}.get(v, "red")
    elif k0 == "pck-dot" and last in ("red-at", "green-at"):
        bad = [not v[0], v[1]]
    elif k0 == "pck-dot" and last == "number":
        bad = 1 if v is None else v + 1
    elif v is None:
        bad = 0.5
    elif isinstance(v, (int, float)):
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
        else:
            bad = break_text(s)
    verdict = compare.judge(f, bad, e, meta, {})[0]
    kinds.setdefault(k0, [0, 0])
    if verdict in ("TIED", "TIED-WITHIN-SAMPLING"):
        missed += 1
        kinds[k0][1] += 1
        holes.append((f["tab"], f["cell"], f["key"], str(v)[:80], str(bad)[:80]))
    else:
        caught += 1
        kinds[k0][0] += 1
print(f"planted {caught + missed}, caught {caught}, missed {missed}")
print("  by kind (caught, missed):", {k: tuple(v) for k, v in sorted(kinds.items())})
for h in holes:
    print("  missed:", *h)
