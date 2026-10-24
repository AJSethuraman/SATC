"""Every product's industry figures, as threshold-engine computes them,
against the FDIC's Quarterly Banking Profile time series (2Q 2026 release).

    python docs/tie-out/industry-qbp-2026-10-14/check_all.py CACHE QBP.xlsx

CACHE: a `peers pull --delinquency yes` cache of every filer 2006Q1-2026Q2
(all five products, RSSDHCR), absorptions.json beside it. QBP.xlsx: as in
check.py. Per product and quarter it compares, $ millions: quarter-end
balance, 30-89 days past due, 90+ days past due, nonaccrual (all sums of the
filed fields, as delinquency.industry_delinquency sums them), and gross and
net charge-offs (the quarterly flow as books.industry builds it: absorption
fix and restart rule). Writes industry_vs_qbp.csv and prints a roster."""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))
from threshold_engine.peers import books, delinquency as D, fdic, run  # noqa: E402

#: QBP "Loan Performance" block start row (1-based) -> our products. The
#: block rows: +1 30-89, +2 90+, +3 nonaccrual, +4 total outstanding, +8
#: total charge-offs, +9 recoveries, +10 net charge-offs.
BLOCKS = {
    "Credit card": (338, "Credit Cards", ["Credit card"]),
    "Home equity": (95, "Home Equity Lines of Credit", ["Home equity"]),
    "Mortgage": (124, "Closed-End First Lien 1-4 Family Residential Mortgages", ["Mortgage"]),
    "Auto": (368, "Auto Loans", ["Auto"]),
    "Other consumer + Auto": (353, "Other Loans to Individuals", ["Other consumer", "Auto"]),
}
MEASURES = (("balance", 4), ("p3", 1), ("p9", 2), ("na", 3), ("gross", 8), ("net", 10))


def qbp(path):
    import openpyxl
    rows = list(openpyxl.load_workbook(path, read_only=True, data_only=True)["Loan Performance"]
                .iter_rows(values_only=True))
    out = {}
    for name, (start, title, _) in BLOCKS.items():
        assert rows[start - 1][1].strip() == title, (name, rows[start - 1][1])
        for j, h in enumerate(rows[4]):
            if isinstance(h, str) and len(h) == 6 and h[4] == "Q":
                out[(name, h)] = {m: (lambda v: v if isinstance(v, (int, float)) else None)(rows[start - 1 + k][j])
                                  for m, k in MEASURES}
    return out


def ours(data):
    qs, snap = books._by_cert(data)
    out = {}
    for name, (_, _, products) in BLOCKS.items():
        cols = [books.PRODUCTS[p] for p in products]
        dq = [D.FIELDS[p] for p in products]
        for i, q in enumerate(qs):
            cur = snap[q]
            row = {"balance": sum(books._num(r, c[0]) for r in cur.values() for c in cols)}
            for m, k in (("p3", 1), ("p9", 2), ("na", 3)):
                row[m] = sum(books._num(r, f[k]) for r in cur.values() for f in dq)
            if q[4:6] == "03":
                g = sum(books._num(r, c[1]) for r in cur.values() for c in cols)
                rc = sum(books._num(r, c[2]) for r in cur.values() for c in cols)
            else:
                prev = snap[qs[i - 1]]
                both = [c for c in cur if c in prev]
                g = sum(books.flow(cur[c], prev[c], f[1]) for c in both for f in cols)
                rc = sum(books.flow(cur[c], prev[c], f[2]) for c in both for f in cols)
            row["gross"], row["net"] = g, g - rc
            out[(name, books.label(q))] = {m: v / 1000 for m, v in row.items()}
    return out


def main(cache, xlsx):
    cache = Path(cache)

    def refuse(url):
        raise RuntimeError("reads the cache only")
    products = ["Credit card", "Mortgage", "Home equity", "Other consumer", "Auto"]
    fields = run.charge_off_fields(products) + D.fields_for(products) + [books.PARENT]
    data = fdic.pull(fdic.quarter_ends("2006Q1", "2026Q2"), list(dict.fromkeys(fields)), cache, fetch=refuse)
    data = books.without_repeats(data, books.repeated_ytd(data, run.load_absorptions(cache / "absorptions.json"),
                                                          products))
    mine, Q = ours(data), qbp(xlsx)
    with open(HERE / "industry_vs_qbp.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["product", "quarter", "measure", "tool", "qbp", "tool_less_qbp"])
        for key in mine:
            for m, _ in MEASURES:
                a, b = mine[key][m], Q[key][m]
                w.writerow([key[0], key[1], m, "%.3f" % a, "" if b is None else "%.3f" % b,
                            "" if b is None else "%.3f" % (a - b)])
    print("%-22s %-8s %s" % ("product", "measure", "quarters within $0.5m / of those QBP fills; largest gap"))
    for name in BLOCKS:
        for m, _ in MEASURES:
            gaps = [(mine[k][m] - Q[k][m], k[1]) for k in mine if k[0] == name and Q[k][m] is not None]
            worst = max(gaps, key=lambda g: abs(g[0]))
            print("%-22s %-8s %3d / %3d; %+.1f in %s" % (name, m, sum(abs(g) < 0.5 for g, _ in gaps), len(gaps),
                                                         worst[0], worst[1]))


if __name__ == "__main__":
    main(*sys.argv[1:])
