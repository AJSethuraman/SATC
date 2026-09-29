"""The independent road for change 4: Look honours the Treat as answers. From Bureau book.csv alone -- Python's csv
module, statistics and numpy; no PocketBook -- with the analyst's answers on Columns: FICO's -9999 means missing, and
SHORT_HIST's negative values (the bureau's codes -99,000,901 to -99,000,904) mean missing.

    python3 by_hand_look.py "Bureau book.csv" OUT/expected-bureau.json OUT/figures-bureau.json

For every block on Look: Loans, Blank (count and share), Not a number, whether a value looks like a code, Smallest,
Median, Mean, Largest, and "Answered missing, left out" (count and share) -- with the answered values left out of
everything but that row. The bars at the default Bars, From and To: which bars, and where each starts, are taken from
what was read (the analyst's view, as the full tie-out's by_hand_scout.py did), and the loans in each are counted
here in exact decimals, with those below From and above To. The scatters: loans with both values and the
correlation, without the answered values; and every dot drawn must be a real loan's pair of values, none of them an
answered missing one. Last, the survey: where a bureau code (or anything at or below -99,000,000) may appear in the
calculated workbook -- only in Columns' sample of raw values.
"""
import collections
import csv
import json
import statistics
import sys
from decimal import Decimal

import numpy as np

X, OUT, FIGS = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
rows = list(csv.DictReader(open(X, newline="", encoding="utf-8")))
N = len(rows)
E = {}


def put(key, value, how="", **extra):
    E[json.dumps(key)] = {"value": value, "how": how, **extra}


def number(s):
    try:
        return float(s)
    except ValueError:
        return None


# the analyst's answers on Columns (walk_bleed_run.py answers them so)
MISSING = {"FICO": lambda v: v == -9999, "SHORT_HIST": lambda v: v < 0}


def looks_like_code(vals):
    nums = [v for v in vals if v is not None]
    value, k = collections.Counter(nums).most_common(1)[0]
    rest = [v for v in nums if v != value]
    if not rest or k < 0.01 * len(nums):
        return None
    span = (max(rest) - min(rest)) or abs(max(rest)) or 1.0
    return value if value < min(rest) - 0.5 * span or value > max(rest) + 0.5 * span else None


READ = {}
for c in ("FICO", "ORIG_BAL", "REV_DEBT", "SHORT_HIST"):
    raw = [r[c] for r in rows]
    vals = [number(x) if x != "" else None for x in raw]
    gone = MISSING.get(c, lambda v: False)
    marked = sum(1 for v in vals if v is not None and gone(v))
    vals = [None if v is not None and gone(v) else v for v in vals]
    READ[c] = vals
    real = [v for v in vals if v is not None]
    blank = sum(1 for x in raw if x == "")
    notnum = sum(1 for x in raw if x != "" and number(x) is None)
    put(["look", c, "Loans", 3], N)
    put(["look", c, "Blank", 3], blank)
    put(["look", c, "Blank", 4], blank / N)
    put(["look", c, "Not a number", 3], notnum)
    put(["look", c, "Not a number", 4], notnum / N)
    put(["look", c, "Likely a code", 3], "none found" if looks_like_code(vals) is None else "a code",
        "no value on 1% of loans or more sits half the spread or further outside the rest")
    put(["look", c, "Smallest", 3], min(real))
    put(["look", c, "Median", 3], statistics.median(real))
    put(["look", c, "Mean", 3], statistics.fmean(real))
    put(["look", c, "Largest", 3], max(real))
    if marked:
        put(["look", c, "Answered missing, left out", 3], marked, "answered Missing on Columns")
        put(["look", c, "Answered missing, left out", 4], marked / N)

ranges = {}
for f in FIGS:
    k = f["key"]
    if k[0] == "look-bar" and k[1] in READ:
        _, name, a, w, last = k
        dv = [Decimal(repr(x)) for x in READ[name] if x is not None]
        a_, b_ = Decimal(repr(round(a, 9))), Decimal(repr(round(a + w, 9)))
        put(k, sum(1 for x in dv if x >= a_ and (x <= b_ if last else x < b_)),
            "loans from the bar's start to its end, in exact decimals, answered missing left out")
        lo, hi = ranges.get(name, (None, None))
        ranges[name] = (a_ if lo is None else min(lo, a_), b_ if hi is None else max(hi, b_))
for name, (lo, hi) in ranges.items():
    dv = [Decimal(repr(x)) for x in READ[name] if x is not None]
    put(["look-end", name, "low end"], sum(1 for x in dv if x < lo), "loans below From")
    put(["look-end", name, "high end"], sum(1 for x in dv if x > hi), "loans above To")

for band in ("FICO", "SHORT_HIST"):
    pairs = [(x, y) for x, y in zip(READ[band], READ["REV_DEBT"]) if x is not None and y is not None]
    name = f"REV_DEBT against {band}"
    put(["look", name, "Loans with both values", 3], len(pairs))
    put(["look", name, "Dots shown", 3], min(2000, len(pairs)), "a sample of 2,000 when there are more")
    put(["look", name, "Moves together (correlation)", 3], float(np.corrcoef(*zip(*pairs))[0, 1]),
        "Pearson over every loan with both, shown to two places")
    put(["look-dots", name], {"pairs": sorted(pairs), "shown": min(2000, len(pairs))},
        "every dot a real loan's pair, none answered missing; as many as the tab says it shows")

# the survey: a bureau code, or anything at or below -99,000,000, only in Columns' sample of raw values
codes = sorted({number(r["SHORT_HIST"]) for r in rows if number(r["SHORT_HIST"]) < 0})
put(["low-values"], {"codes": codes, "allowed": [["Columns", "the sample of raw values"]]},
    "no code anywhere but the sample Columns shows of each column's raw values")
json.dump({"expected": E, "meta": {"n": N, "labels": {}, "codes": codes}}, open(OUT, "w"), indent=0)
print(len(E), "expected;", "codes", codes)
