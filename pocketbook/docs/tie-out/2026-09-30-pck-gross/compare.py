"""Set Road 1 (what PocketBook shows) beside Road 2 (the loan file, worked out without PocketBook), one verdict a
figure: TIED, or DIFFERS with both values. A figure on one road only DIFFERS. Writes roster.csv and prints the
counts.

    python3 docs/tie-out/2026-09-30-pck-gross/compare.py
"""
import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
TOL = {"booked": 0.005, "gco": 0.005, "ranr": 0.005, "ranr_rate": 1e-12, "loans": 0}


def read(name):
    return {(r["grid"], r["kind"], r["band"], r["segment"], r["figure"]): r["value"]
            for r in csv.DictReader((WORK / name).open(encoding="utf-8"))}


def same(figure, a, b) -> bool:
    if figure in TOL:
        if a in ("", "None") or b in ("", "None"):
            return a in ("", "None") and b in ("", "None")
        return abs(float(a) - float(b)) <= TOL[figure]
    return a == b


def main() -> None:
    one, two = read("road1.csv"), read("road2.csv")
    rows, tally = [], Counter()
    for key in sorted(set(one) | set(two)):
        a, b = one.get(key), two.get(key)
        verdict = "TIED" if a is not None and b is not None and same(key[-1], a, b) else "DIFFERS"
        tally[verdict] += 1
        rows.append((*key, a, b, verdict))
    with (HERE / "roster.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["grid", "kind", "band", "segment", "figure", "pocketbook", "loan file", "verdict"])
        w.writerows(rows)
    by = Counter((r[0], r[1], r[-1]) for r in rows)
    for k in sorted(by):
        print(*k, by[k], sep=" | ")
    print(f"TIED {tally['TIED']} · DIFFERS {tally['DIFFERS']} of {len(rows)}")
    for r in rows:
        if r[-1] == "DIFFERS":
            print("DIFFERS", r)


if __name__ == "__main__":
    main()
