"""Print what the independent road worked out for one pocket, from its own expected-figures file.

    python3 explain.py OUT/expected-bleed.json "Two-way" "Kept after losses" "FICO 496 - 653" "4"

Nothing here reads the workbook. It is for looking at one pocket the way the document does.
"""
import json
import sys

exp = json.load(open(sys.argv[1]))["expected"]
kind, measure, band, seg = sys.argv[2:6]
fields = ("rank", "loans", "rate", "rest-rate", "gap", "dollars", "p", "worse", "material", "caught")
print(f"{kind} · {measure} · {band} / {seg}  (worked out from the loan file)")
for f in fields:
    e = exp.get(json.dumps(["pocket", kind, measure, band, seg, None, f]))
    if e is None:
        continue
    v = e["value"]
    extra = ""
    if f == "p" and e.get("shuffled"):
        extra = f"   (shuffled 10,000 times; before the allowance {e['raw']:.4f}, family of {e['family']})"
    print(f"  {f:<10} {v:.6f}{extra}" if isinstance(v, float) else f"  {f:<10} {v}{extra}")
