"""With two values, "do the values differ at all" (B3) is the Cochran-Mantel-Haenszel test over every pocket that says
something (docs/statistics.md B3: "With two groups it collapses to A6"). statsmodels' own CMH, from the loan file.

    python3 cmh_check.py "Two-flag book.csv"

FICO x CHANNEL: FICO in the bands Record prints (654; 686; 712; 746), -9999 answered missing, a blank its own band.
"""
import csv
import sys
from collections import defaultdict

import numpy as np
from scipy import stats as st
from statsmodels.stats.contingency_tables import StratifiedTable

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))


def band(f):
    if f == "":
        return "(blank)"
    v = float(f)
    return "(marked missing)" if v == -9999 else sum(v >= e for e in (654, 686, 712, 746))


t = defaultdict(lambda: np.zeros((2, 2)))
for r in rows:
    if r["BAD_FLAG"] in ("0", "1"):
        t[(band(r["FICO"]), r["CHANNEL"])][0 if r["SYS_FLAG"] == "Y" else 1, 0 if r["BAD_FLAG"] == "1" else 1] += 1
tabs = [x for x in t.values() if x.sum() >= 2 and 0 < x[:, 0].sum() < x.sum()]
s = StratifiedTable(tabs).test_null_odds(correction=False).statistic
print(f"{len(tabs)} pockets; statsmodels Cochran-Mantel-Haenszel chi2 {s:.6f}, p {st.chi2.sf(s, 1):.4g}")
