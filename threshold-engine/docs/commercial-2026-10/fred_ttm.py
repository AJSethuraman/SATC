"""A Federal Reserve charge-off series from FRED as the four-quarter mean the
`compare` command can set beside an FDIC trailing-twelve-month series.

    python fred_ttm.py FRED.csv OUT.csv

FRED.csv is FRED's own download (https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>,
columns observation_date and the ID): each quarter's net charge-offs over the
quarter's average loans, annualized (x 400), dated at the quarter's first day.
OUT.csv is date,value with '#' notes: each quarter, the mean of that quarter's
rate and the three before, exact (not rounded), written only where all four
are there; the date stays the quarter's first day, and `compare` matches by
calendar quarter. Nothing is filled in: a missing quarter ('' or '.') ends the
windows that hold it. Public data only.
"""
import csv
import sys
from pathlib import Path


def main(src, out):
    src, out = Path(src), Path(out)
    with open(src, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "observation_date" not in rows[0] or len(rows[0]) != 2:
        raise SystemExit("%s is not a FRED download (observation_date and one series)" % src)
    sid = [k for k in rows[0] if k != "observation_date"][0]
    vals = [(r["observation_date"], None if r[sid] in ("", ".") else float(r[sid])) for r in rows]
    for (a, _), (b, _) in zip(vals, vals[1:]):
        ya, ma = int(a[:4]), int(a[5:7])
        if (int(b[:4]) * 12 + int(b[5:7])) - (ya * 12 + ma) != 3:
            raise SystemExit("%s: %s does not follow %s by one quarter" % (src, b, a))
    kept = [(d, sum(v for _, v in vals[i - 3:i + 1]) / 4) for i, (d, _) in enumerate(vals)
            if i >= 3 and all(v is not None for _, v in vals[i - 3:i + 1])]
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write("# measure: Federal Reserve series %s (FRED), the mean of four quarterly annualized net charge-off "
                 "rates\n" % sid)
        fh.write("# basis: each quarter's rate is net charge-offs over the quarter's average loans x 400, insured "
                 "U.S.-chartered commercial banks; this file is the mean of the quarter's rate and the three "
                 "before, exact, dated at the quarter's first day\n")
        fh.write("# source: %s, as downloaded from FRED\n" % src.name)
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["date", "value"])
        for d, v in kept:
            w.writerow([d, repr(v)])
    print("Wrote %s: %d quarters, %s to %s" % (out, len(kept), kept[0][0], kept[-1][0]))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
