"""Industry card charge-offs per quarter, as threshold-engine computes them,
against the FDIC's Quarterly Banking Profile time series (2Q 2026 release).

    python docs/tie-out/card-qbp-2026-10-14/check.py CACHE QBP.xlsx

CACHE is a `peers pull` cache of every filer 2006Q1-2026Q2 with LNCRCD,
DRCRCD, CRCRCD and RSSDHCR, and absorptions.json beside it. QBP.xlsx is
https://www.fdic.gov/quarterly-banking-profile/qbp-time-series-spreadsheets-second-quarter-2026.xlsx,
sheet "Loan Performance", "Credit Cards" block: row 342 total outstanding,
346 total charge-offs, 347 recoveries, 348 net charge-offs, $ millions, all
FDIC-insured institutions; quarter labels in row 5. Needs openpyxl. Writes
card_vs_qbp.csv beside this file: per quarter the gross flow as differenced
(raw), after the absorption fix, after the restart rule too (the tool now),
and QBP's figure."""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))
from threshold_engine.peers import books, fdic, run  # noqa: E402


def qbp(path):
    import openpyxl
    rows = list(openpyxl.load_workbook(path, read_only=True, data_only=True)["Loan Performance"].iter_rows(values_only=True))
    assert rows[337][1].strip() == "Credit Cards"
    return {h: {"gross": rows[345][j], "net": rows[347][j], "bal": rows[341][j]}
            for j, h in enumerate(rows[4]) if isinstance(h, str) and len(h) == 6 and h[4] == "Q"}


def flows(data, rule):
    qs, snap = books._by_cert(data)
    out = {}
    for i, q in enumerate(qs):
        cur = snap[q]
        if q[4:6] == "03":
            g = sum(books._num(r, "DRCRCD") for r in cur.values())
        else:
            prev = snap[qs[i - 1]]
            both = [c for c in cur if c in prev]
            g = sum(books.flow(cur[c], prev[c], "DRCRCD") if rule else
                    books._num(cur[c], "DRCRCD") - books._num(prev[c], "DRCRCD") for c in both)
        out[books.label(q)] = g / 1000
    return out


def main(cache, xlsx):
    cache = Path(cache)

    def refuse(url):
        raise RuntimeError("reads the cache only")
    data = fdic.pull(fdic.quarter_ends("2006Q1", "2026Q2"), ["LNCRCD", "DRCRCD", "CRCRCD", "RSSDHCR"], cache,
                     fetch=refuse)
    fixed = books.without_repeats(data, books.repeated_ytd(data, run.load_absorptions(cache / "absorptions.json"),
                                                           ["Credit card"]))
    raw, fix, now, Q = flows(data, False), flows(fixed, False), flows(fixed, True), qbp(xlsx)
    with open(HERE / "card_vs_qbp.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["quarter", "differenced", "absorption_fix", "tool_now", "qbp", "tool_now_less_qbp"])
        for q in raw:
            w.writerow([q, "%.1f" % raw[q], "%.1f" % fix[q], "%.1f" % now[q], "%.1f" % Q[q]["gross"],
                        "%.1f" % (now[q] - Q[q]["gross"])])
    for name, s in (("differenced", raw), ("absorption fix", fix), ("tool now", now)):
        gaps = [abs(s[q] - Q[q]["gross"]) for q in s]
        print("%-15s %d of %d quarters within $0.05m; total absolute gap $%.1fm"
              % (name, sum(g < 0.05 for g in gaps), len(gaps), sum(gaps)))


if __name__ == "__main__":
    main(*sys.argv[1:])
