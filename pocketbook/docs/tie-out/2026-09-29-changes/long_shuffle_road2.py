"""The one DIFFERS, looked at with far more shuffles -- the loan-file road (no PocketBook code).

    python3 long_shuffle_road2.py "Flag book.csv" SHUFFLES REPEATS

The pocket FICO 746 - 921 / ASSET_CLASS 1 / SYS_FLAG Y on Earned before losses ((RANR_AMT + GCO_AMT) per ORIG_BAL
booked dollar, Paid, cost, kept!C4), against the rest of its band (Pockets!D8): every other loan in FICO 746 - 921,
whatever its segment or flag. The loans that entered the rate (all three amounts numbers) are dealt at random within
the band, the pocket keeping its number of loans; a shuffle counts when its gap is at least as big either way;
p = (hits + 1) / (shuffles + 1). The band edge 746 and the top 921 are Record's (Record!C16). Each repeat uses its
own seed from numpy's default generator.
"""
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

path, B, R = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])


def num(s):
    try:
        return float(s)
    except ValueError:
        return None


y, x, mine = [], [], []
for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
    f = num(r["FICO"]) if r["FICO"] != "" else None
    if f is None or f == -9999 or f < 746:
        continue
    q, g, b = num(r["RANR_AMT"]), num(r["GCO_AMT"]), num(r["ORIG_BAL"]) if r["ORIG_BAL"] != "" else None
    if q is None or g is None or b is None:
        continue
    y.append(q + g)
    x.append(b)
    mine.append(r["ASSET_CLASS"] == "1" and r["SYS_FLAG"] == "Y")
y, x, mine = np.array(y), np.array(x), np.array(mine)
n, k = len(y), int(mine.sum())
Y, X = y.sum(), x.sum()


def gap(sy, sx):
    return sy / sx - (Y - sy) / (X - sx)


g0 = gap(y[mine].sum(), x[mine].sum())
out = []
for rep in range(R):
    rng = np.random.default_rng(29092026 + 1000 * rep)
    hits, done = 0, 0
    while done < B:
        c = min(2000, B - done)
        pick = np.argsort(rng.random((c, n)), axis=1)[:, :k]          # a uniform random k of the band's loans
        gs = gap(y[pick].sum(axis=1), x[pick].sum(axis=1))
        hits += int((~(np.abs(gs) < abs(g0) * (1 - 1e-9))).sum())
        done += c
    p = (hits + 1) / (B + 1)
    se = math.sqrt(p * (1 - p) / B)
    out.append({"seed": 29092026 + 1000 * rep, "gap": g0, "hits": hits, "shuffles": B, "p": p, "se": se})
    print(f"  loan file   seed {29092026 + 1000 * rep}  gap {g0:+.9f}  hits {hits:7d} of {B}  p {p:.5f}  se {se:.5f}"
          f"   ({n} loans in the band, {k} in the pocket)", flush=True)
Path(Path(__file__).resolve().parent / "results" / "long-shuffle-road2.json").write_text(json.dumps(out, indent=1))
