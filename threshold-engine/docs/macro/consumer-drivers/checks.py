"""The figures the Book 2 plan quotes, re-derived from public files (17 Oct 2026).

A check of the first-pass numbers in the brief, not Book 2: nothing here is a
result, a setting or a verdict. Run from threshold-engine/:

    python docs/macro/consumer-drivers/checks.py PULL_FOLDER

PULL_FOLDER is one day's macro pull (it holds fred-UNRATE.csv, fred-ICSA.csv,
fred-USSTHPI.csv). The loss series are read from data/industry/ (the FDIC's,
every filer) and tests/data/ (the Federal Reserve's card series and the FDIC's
longer charge-off series). Rules used, each a choice the plan puts to the firm:
a monthly series is averaged over the quarter, and a quarter missing a month is
left out; a weekly one is averaged over its weeks; a change is over four
quarters and is left out when either end falls in 2020Q1-2021Q4 (the brief's
illustrative window, not a decision); the effective sample is n(1 - r1 r2) /
(1 + r1 r2) from the two series' lag-1 autocorrelations (approximate).
"""
import csv
import math
import pathlib
import statistics as st
import sys

HERE = pathlib.Path(__file__).resolve().parents[3]          # threshold-engine/


def label(d):
    return "%sQ%d" % (d[:4], (int(d[5:7]) - 1) // 3 + 1)


def shift(t, k):
    n = int(t[:4]) * 4 + int(t[5]) - 1 + k
    return "%dQ%d" % (n // 4, n % 4 + 1)


def rows(path):
    for row in csv.reader(open(path)):
        if row and row[0][:1].isdigit():
            yield row[0], None if row[1] in (".", "") else float(row[1])


def quarter_mean(path, need=None):
    """Quarter average; with ``need`` (months per quarter) a short quarter is left out."""
    got = {}
    for d, v in rows(path):
        got.setdefault(label(d), []).append(v)
    out = {}
    for t, vs in got.items():
        vs_ = [v for v in vs if v is not None]
        if vs_ and (need is None or len(vs_) == need):
            out[t] = sum(vs_) / len(vs_)
    return out


def quarterly(path):
    return {label(d): v for d, v in rows(path) if v is not None}


def d4(s):
    return {t: s[t] - s[shift(t, -4)] for t in s if shift(t, -4) in s}


def left_out(t):
    return any("2020Q1" <= e <= "2021Q4" for e in (t, shift(t, -4)))


def corr(a, b):
    ma, mb = st.mean(a), st.mean(b)
    return (sum((x - ma) * (y - mb) for x, y in zip(a, b))
            / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)))


def typical(changes):
    m = st.median(changes)
    return 1.4826 * st.median(abs(c - m) for c in changes)


def runs(ts, test):
    """Episodes: runs of quarters where ``test`` holds, as (first, last). A gap of one quarter is merged, as
    the plan's episode rule says (2001Q2-2002Q4 and 2003Q2-Q3 are one episode)."""
    out = []
    for t in ts:
        if test(t):
            if out and shift(out[-1][1], 1) == t or out and shift(out[-1][1], 2) == t:
                out[-1][1] = t
            else:
                out.append([t, t])
    return out


def main(pull):
    pull = pathlib.Path(pull)
    ind, fed = HERE / "data" / "industry", HERE / "tests" / "data"
    u = d4(quarter_mean(pull / "fred-UNRATE.csv", need=3))
    claims = d4(quarter_mean(pull / "fred-ICSA.csv"))

    hpi = quarterly(pull / "fred-USSTHPI.csv")
    falls = sorted(t for t in hpi if shift(t, -4) in hpi and hpi[t] < hpi[shift(t, -4)])
    print("1. FHFA all-transactions index below its level a year before: %d quarters; %d in 2007Q4-2012Q2; the "
          "others: %s" % (len(falls), sum("2007Q4" <= t <= "2012Q2" for t in falls),
                          ", ".join(t for t in falls if not "2007Q4" <= t <= "2012Q2")))

    print("\n2. Unemployment's four-quarter change against each loss measure's, together (same year)")
    for f, name in (("credit-card_industry_net.csv", "Credit card, Net charge-offs"),
                    ("credit-card_industry_delinquency-30-89_quarter-end.csv", "Credit card, 30-89 days past due"),
                    ("mortgage_industry_delinquency-30-plus-incl-nonaccrual_quarter-end.csv",
                     "Mortgage, 30+ days past due incl. nonaccrual"),
                    ("auto_industry_delinquency-30-plus-incl-nonaccrual_quarter-end.csv",
                     "Auto, 30+ days past due incl. nonaccrual")):
        y = d4(quarterly(ind / f))
        shown = set()
        for start in ("2007Q4", "2012Q1"):
            ts = sorted(t for t in y if t in u and t >= start and not left_out(t))
            if ts[0] in shown:                      # auto starts in 2011: one window, not two
                continue
            shown.add(ts[0])
            a, b = [u[t] for t in ts], [y[t] for t in ts]
            r1, r2 = corr(a[:-1], a[1:]), corr(b[:-1], b[1:])
            print("   %-46s from %s to %s: %d quarters, r %+.2f, effective sample about %.1f"
                  % (name, ts[0], ts[-1], len(ts), corr(a, b), len(ts) * (1 - r1 * r2) / (1 + r1 * r2)))
        one = []
        for q in "1234":
            ts = sorted(t for t in y if t in u and t[5] == q and t >= "2007Q4" and not left_out(t))
            one.append("ending Q%s: %d years, r %+.2f" % (q, len(ts), corr([u[t] for t in ts], [y[t] for t in ts])))
        print("   %-46s one change a year, %s" % ("", "; ".join(one)))

    print("\n3. How a Stable band of +/-0.5 and +/-1 typical yearly moves sorts 2007Q4-2026Q2")
    for s, name in ((u, "Unemployment"), (claims, "Initial jobless claims"),
                    (d4(quarterly(ind / "credit-card_industry_net.csv")), "Credit card, Net charge-offs"),
                    (d4(quarterly(ind / "credit-card_industry_delinquency-30-89_quarter-end.csv")),
                     "Credit card, 30-89 days past due")):
        ts = sorted(t for t in s if t >= "2007Q4" and not left_out(t))
        tm = typical([s[t] for t in ts])
        for band in (0.5, 1.0):
            up = runs(ts, lambda t: s[t] > band * tm)
            n_up = sum(1 for t in ts if s[t] > band * tm)
            n_dn = sum(1 for t in ts if s[t] < -band * tm)
            print("   %-34s +/-%.1f (typical move %.3g): %d decreasing, %d stable, %d increasing in %d episodes: %s"
                  % (name, band, tm, n_dn, len(ts) - n_up - n_dn, n_up, len(up),
                     ", ".join("%s-%s" % (r[0], r[-1]) for r in up)))

    print("\n4. The longer public series, unemployment together with net charge-offs")
    for f, name, start in (("cards_nco_ttm.csv", "Credit card (Federal Reserve, all banks)", "1986Q4"),
                           ("other_consumer_as_filed_nco_ttm.csv", "Other consumer (FDIC, as filed)", "1993Q4"),
                           ("home_equity_nco_ttm.csv", "Home equity (FDIC)", "1993Q4")):
        y = d4(quarterly(fed / f))
        ts = sorted(t for t in y if t in u and t >= start and not left_out(t))
        tm = typical([u[t] for t in ts])
        eps = runs(ts, lambda t: u[t] > 0.5 * tm)
        print("   %-40s %s-%s: %d quarters, r %+.2f; rising-unemployment episodes: %s"
              % (name, ts[0], ts[-1], len(ts), corr([u[t] for t in ts], [y[t] for t in ts]),
                 ", ".join("%s-%s" % (e[0], e[-1]) for e in eps)))
        for e in eps:
            keep = [t for t in ts if not e[0] <= t <= shift(e[-1], 4)]
            print("   %-40s without %s-%s and the year after: r %+.2f"
                  % ("", e[0], e[-1], corr([u[t] for t in keep], [y[t] for t in keep])))


if __name__ == "__main__":
    main(sys.argv[1])
