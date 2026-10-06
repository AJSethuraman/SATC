"""Figure 3, the independent road: the p-value of FICO under 654 / Broker on Bad loans, from the extract alone.

    python3 pvalue.py "Consumer book Q3.csv"

No PocketBook code. The csv module reads the extract; scipy gives the normal tail; statsmodels gives the
Benjamini-Hochberg adjustment. The method is the one the workbook states in words (Pockets!D8, Record!F25):
  - Bad loans, a pocket of 65 loans or more: the two-proportion z test, pooled, two-sided, pocket against the rest
    of its band (every other loan in the same FICO band).
  - Allowing for many tests: Benjamini-Hochberg across one grid and one measure, here the FICO x CHANNEL grid on
    Bad loans, over the pockets with at least 10 bad loans (the only ones tested: Record!C47, "15 ... can be
    tested").
A loan whose BAD_FLAG is neither 0 nor 1 is left out (Record!C68).

It prints the adjustment twice. First over the 15 pockets the workbook says were tested. Then over every pocket
that has a rest of its band to compare with (18: the 15, plus the three "marked missing" FICO pockets, which have
fewer than 10 bad loans and, under 65 loans, would take Fisher's exact test) -- because the first reading did not
land on the workbook's figure, and this is the reading that does. See the tie-out's "What it found".
"""
import csv
import math
import sys
from collections import defaultdict

from scipy.stats import fisher_exact, norm
from statsmodels.stats.multitest import multipletests

EDGES = (654, 686, 712, 746)          # Record!C16


def band(fico):
    if fico == "":
        return "(blank)"
    f = int(fico)
    if f == -9999:
        return "(marked missing)"
    return "band %d" % (1 + sum(f >= e for e in EDGES))


n = defaultdict(int)
bad = defaultdict(int)
with open(sys.argv[1], newline="") as fh:
    for row in csv.DictReader(fh):
        if row["BAD_FLAG"] not in ("0", "1"):
            continue
        key = (band(row["FICO"]), row["CHANNEL"])
        n[key] += 1
        bad[key] += int(row["BAD_FLAG"])

def z_test(x1, n1, x2, n2):
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (x1 / n1 - x2 / n2) / se
    return z, 2 * norm.sf(abs(z))


def family(keep):
    rows = []
    for (b, ch), size in sorted(n.items()):
        rest_n = sum(v for (b2, c2), v in n.items() if b2 == b and c2 != ch)
        rest_bad = sum(v for (b2, c2), v in bad.items() if b2 == b and c2 != ch)
        if rest_n == 0 or not keep(b, ch):
            continue
        x1, n1, x2, n2 = bad[(b, ch)], size, rest_bad, rest_n
        if n1 >= 65:
            z, p = z_test(x1, n1, x2, n2)
            how = "z"
        else:
            z, p = float("nan"), fisher_exact([[x1, n1 - x1], [x2, n2 - x2]])[1]
            how = "exact"
        rows.append((b, ch, x1, n1, x2, n2, how, z, p))
    return rows


def show(title, rows):
    adjusted = multipletests([r[-1] for r in rows], method="fdr_bh")[1]
    print("%s: %d pockets in the Benjamini-Hochberg family" % (title, len(rows)))
    print("%-17s %-7s %5s %5s %6s %7s %-5s %9s %14s %14s" % ("band", "channel", "bad", "loans", "r.bad", "r.loans",
                                                            "test", "z", "p raw", "p after BH"))
    for r, q in zip(rows, adjusted):
        print("%-17s %-7s %5d %5d %6d %7d %-5s %9.4f %14.6e %14.6e" % (*r, q))
    print()


tested = family(lambda b, ch: b not in ("(blank)", "(marked missing)") and bad[(b, ch)] >= 10)
show("A. The pockets with at least 10 bad loans (what Record!C47 says was tested)", tested)
show("B. Every pocket with a rest of its band to compare with", family(lambda b, ch: True))
