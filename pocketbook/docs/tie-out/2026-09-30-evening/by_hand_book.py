"""The independent road, Where the book bleeds: every figure the workbook shows, worked out again from the loan file
alone. No PocketBook code is imported or copied; the rules are the ones the workbook states in words on its own tabs
(each rule below cites the cell that states it), and the statistics are the textbook ones from scipy and statsmodels.

    python3 by_hand_book.py LOANS.csv OUT/expected.json SHUFFLES SPLIT HOW FIGURES.json [WB-POCKETS.json]
    python3 by_hand_book.py "../2026-09-28/Consumer book Q3.csv" OUT/expected-q3.json 10000 REV_DEBT own_median \
        OUT/views-q3/figures.json
    python3 by_hand_book.py "Flag book.csv" OUT/expected-flag.json 10000 SYS_FLAG each_value OUT/views-flag/figures.json

The full tie-out's by_hand_bleed.py (28 Sep 2026), made general for this build's changes (29 Sep 2026):
  - the split may be a category (HOW each_value): every value against the rest of its pocket -- the value's rate over
    the rest's, the z test for bad loans, this road's own shuffles within the pocket for a dollar rate, the pooled
    actual against expected with its range, Mantel-Haenszel's odds with the Cochran-Mantel-Haenszel p, Cochran's Q,
    one Benjamini-Hochberg family over every value and pocket of a grid and rate, the pooled p-values a family across
    the values, and the K-group Mantel-Haenszel test of whether the values differ at all (B3), written here from the
    textbook;
  - "What one cell says" on Grids, sentence by sentence, from this road's own grid figures;
  - the Paid, cost, kept chart: each dot's place, colour and number, from this road's own verdicts;
  - Look leaves out what Columns answered missing (FICO's -9999), and every scatter dot must be a real loan's pair;
  - Record's figures are named by the label they sit under, since its rows move.
FIGURES (read_book.py's reading) is used only to know WHICH figures to work out -- the cell each Grids view picked,
which bars Look draws, where Record's lines sit -- never for a value.

Reads the extract with Python's csv module. Writes one expected value per figure, keyed the way read_book.py keys
what it reads, so compare.py can put each pair side by side.

The settings are the ones Control shows for this Run (Control!C15:C29, as answered on the walk): worse at the
suggested line, better at one over it, 95% sure, 1% of the book's charge-offs, the rest of its band, 65 loans for
the usual test, 10 losses, 5 bands of equal loans, 80% power, Benjamini-Hochberg. The two suggested values (1.34 and
0.75) and the 65 are themselves worked out below from the book, as Record!C41 says they are, and those are used.

The shuffle test (10,000 shuffles, Pockets!D8) is re-run here with this script's own random numbers. It cannot and
should not land on the same digits: its p-values are compared within sampling error (compare.py says how).
"""
import collections
import csv
import json
import re
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date

import numpy as np
from scipy import stats as st
from scipy.optimize import brentq
from statsmodels.stats.multitest import multipletests

X, OUT = sys.argv[1], sys.argv[2]
B = int(sys.argv[3]) if len(sys.argv) > 3 else 10_000
# 29 Sep 2026: the split column and how it splits (Record's "Split" line and the Split tab's title say it in words:
# "each pocket halved at its own median" or "each pocket split by each value"), and the figures read out of the
# workbook -- used only for WHICH figures to work out (the cells the Row and Column picked on Grids, where each Record
# figure sits), never for a value, as the full tie-out's by_hand_scout.py already did for the Look bars
SPLITCOL = sys.argv[4] if len(sys.argv) > 4 else "REV_DEBT"
HOW = sys.argv[5] if len(sys.argv) > 5 else "own_median"
FIGS = json.load(open(sys.argv[6])) if len(sys.argv) > 6 and sys.argv[6] != "-" else []
# Optional: the workbook's own p-values (read_book.py's wb-pockets.json). Given, the verdicts of pockets whose
# shuffled p-values sit either side of 5% but within sampling error of each other are taken on the workbook's side,
# and every figure is worked out again from there: compare.py uses that second set only to say which differences
# are sampling and nothing else. The first set, with no file, is the independent road on its own.
FLIPS_FROM = sys.argv[7] if len(sys.argv) > 7 else None
FLIPPED = []
RNG = np.random.default_rng(20260928)           # this road's own seed; nothing to do with PocketBook's

CONF, POWER, MIN_EVENTS, MAT_SHARE = 0.95, 0.80, 10, 0.01
ALPHA = 1 - CONF
Z = st.norm.ppf(1 - ALPHA / 2)
ZP = st.norm.ppf(POWER)


def number(s):
    try:
        return float(s)
    except ValueError:
        return None


# ------------------------------------------------------------------ the loans (Columns!H14: -9999 means missing)
with open(X, newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))
N = len(rows)
FICO = [None if r["FICO"] == "" else number(r["FICO"]) for r in rows]
FICO_WHY = ["(blank)" if r["FICO"] == "" else "(marked missing)" if number(r["FICO"]) == -9999 else None
            for r in rows]
BAL = [number(r["ORIG_BAL"]) if r["ORIG_BAL"] != "" else None for r in rows]
BAL_WHY = ["(blank)" if r["ORIG_BAL"] == "" else None for r in rows]
FLAG = [int(r["BAD_FLAG"]) if r["BAD_FLAG"] in ("0", "1") else None for r in rows]
GCO = [number(r["GCO_AMT"]) for r in rows]
RANR = [number(r["RANR_AMT"]) for r in rows]
REV = [number(r["REV_DEBT"]) for r in rows]
SPLV = [number(r[SPLITCOL]) for r in rows] if HOW == "own_median" else None
LATE = ("(no date)", "(blank)")


def values_of(name):
    """A category's value per loan; ORIG_YEAR (build 44734da4) is the year of ORIG_DATE, the column marked
    Origination date, as its first four characters, and "(no date)" for a loan with none (the launcher's words:
    "Origination year, from ORIG_DATE")."""
    if name == "ORIG_YEAR" and "ORIG_YEAR" not in rows[0]:
        return [r["ORIG_DATE"][:4] if r["ORIG_DATE"] else "(no date)" for r in rows]
    return [r[name] if r[name] != "" else "(blank)" for r in rows]


def order_of(vals):
    """Values in the order the tabs list them: sorted, then "(no date)", then the blank. The order changes no
    figure."""
    return sorted({v for v in vals if v not in LATE}) + [x for x in LATE if x in set(vals)]


VALUE = values_of(SPLITCOL) if HOW == "each_value" else None
VALUES = order_of(VALUE) if VALUE else []
# build 44734da4: Grids' "Only loans where" reads its own column, Filter by (FILTER, in the environment), whatever the
# split does; none when unset
FILTERCOL = os.environ.get("FILTER") or None
FVALUE = values_of(FILTERCOL) if FILTERCOL else None
FVALUES = order_of(FVALUE) if FVALUE else []
DIMS = {"CHANNEL": [r["CHANNEL"] if r["CHANNEL"] != "" else "(blank)" for r in rows],
        "ASSET_CLASS": [r["ASSET_CLASS"] if r["ASSET_CLASS"] != "" else "(blank)" for r in rows]}

# the five measures (Pockets!C17's list; Paid, cost, kept!C4:C6 for what each is): (y, x) per loan, or None
MEASURES = {
    "Bad loans": [None if f is None else (float(f), 1.0) for f in FLAG],
    "Bad dollars": [None if f is None or b is None else (b if f else 0.0, b) for f, b in zip(FLAG, BAL)],
    "Charge-offs": [None if g is None or b is None else (g, b) for g, b in zip(GCO, BAL)],
    "Kept after losses": [None if q is None or b is None else (q, b) for q, b in zip(RANR, BAL)],
    "Earned before losses": [None if q is None or g is None or b is None else (q + g, b)
                             for q, g, b in zip(RANR, GCO, BAL)],
}
PROFIT = {"Kept after losses", "Earned before losses"}           # read as a gap in points (Grids!C5)
DOLLAR = ("Bad dollars", "Charge-offs", "Kept after losses", "Earned before losses")   # shuffled (Pockets!D8)
MY = {m: np.array([v[0] if v else np.nan for v in vals]) for m, vals in MEASURES.items()}
MX = {m: np.array([v[1] if v else np.nan for v in vals]) for m, vals in MEASURES.items()}
IN = {m: ~np.isnan(MX[m]) for m in MEASURES}


def book(m):
    i = IN[m]
    return MY[m][i].sum(), MX[m][i].sum(), int(i.sum())


BOOK = {m: book(m) for m in MEASURES}
RATE = {m: BOOK[m][0] / BOOK[m][1] for m in MEASURES}
BAD_RATE = RATE["Bad loans"]

# ------------------------------------------------------------------ worked out from the book (Record!C41)
MIN_LOANS = math.ceil(5 / BAD_RATE)                        # "enough to expect 5 with the outcome at the book's rate"


# ------------------------------------------------------------------ bands (Record!C16:C17; Control!C26:C27)
def edges_of(vals, k=5):
    v = np.sort(np.array(vals))
    got = [float(np.quantile(v, i / k)) for i in range(1, k)]      # each band about the same number of loans
    out = []
    for e in got:
        if e > v[0] and (not out or e > out[-1]):
            out.append(e)
    return out


def labels_of(edges, lo, hi, whole=False):
    """Pockets!C21's band names: from the band's first whole number to one short of the next band's. Build 44734da4:
    on a column of whole numbers (a score) a band is named by the values it holds -- a band starting at an edge of
    654.2 holds 655 first, and the band below it ends at 654."""
    f = lambda x: f"{x:,.0f}"                                          # noqa: E731
    up = (lambda x: math.ceil(x)) if whole else (lambda x: x)          # noqa: E731
    out = [f"{f(math.floor(lo))} - {f(up(edges[0]) - 1)}"]
    out += [f"{f(up(a))} - {f(up(b) - 1)}" for a, b in zip(edges, edges[1:])]
    out.append(f"{f(up(edges[-1]))} - {f(math.ceil(hi))}")
    return out


WHOLE = {}


def banded(vals, why):
    seen = [v for v, w in zip(vals, why) if w is None]
    e = edges_of(seen)
    whole = all(float(v).is_integer() for v in seen)
    lab = labels_of(e, min(seen), max(seen), whole)
    WHOLE[id(vals)] = whole
    out = []
    for v, w in zip(vals, why):
        if w:
            out.append(w)
        else:
            out.append(lab[sum(v >= x for x in e)])
    return e, lab, out


EDGES, LABELS, BAND = {}, {}, {}
EDGES["FICO"], LABELS["FICO"], BAND["FICO"] = banded(FICO, FICO_WHY)
EDGES["ORIG_BAL"], LABELS["ORIG_BAL"], BAND["ORIG_BAL"] = banded(BAL, BAL_WHY)
SPECIAL = ["(blank)", "(not a number)", "(marked missing)"]


def order(labels, first=()):
    s = set(labels)
    plain = [x for x in first if x in s] + sorted((x for x in s if x not in first and x not in SPECIAL),
                                                 key=str.lower)
    return plain + [x for x in SPECIAL if x in s]


# the split: every two-way pocket halved at its own median REV_DEBT; the high half is above it (Split!C4)
def halves(bcol, dcol):
    groups = defaultdict(list)
    for i, (b, d, v) in enumerate(zip(BAND[bcol], DIMS[dcol], SPLV)):
        if v is not None:
            groups[(b, d)].append(v)
    med = {k: statistics.median(v) for k, v in groups.items()}
    return ["none" if v is None else "high" if v > med[(b, d)] else "low"
            for b, d, v in zip(BAND[bcol], DIMS[dcol], SPLV)]


GRIDS = []           # (name, band column, dim column, three-way?)
for bcol in ("FICO", "ORIG_BAL"):
    for dcol in ("CHANNEL", "ASSET_CLASS"):
        GRIDS.append((f"{bcol} x {dcol}", bcol, dcol, False))
for bcol in ("FICO", "ORIG_BAL"):
    for dcol in ("CHANNEL", "ASSET_CLASS"):
        GRIDS.append((f"{bcol} x {dcol} / {SPLITCOL}", bcol, dcol, True))
# each loan's side: "high"/"low" for the halves, its value for a category
HALF = {(b, d): halves(b, d) if HOW == "own_median" else VALUE for b in ("FICO", "ORIG_BAL")
        for d in ("CHANNEL", "ASSET_CLASS")}


def keys_of(g):
    name, bcol, dcol, three = g
    if not three:
        return list(zip(BAND[bcol], DIMS[dcol]))
    return [(b, (d, h)) for b, d, h in zip(BAND[bcol], DIMS[dcol], HALF[(bcol, dcol)])]


# ------------------------------------------------------------------ tests
def z_p(x1, n1, x2, n2):
    """The pooled two-proportion z test, two-sided (Pockets!D8, Record!F25)."""
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    return 2 * st.norm.sf(abs((x1 / n1 - x2 / n2) / se))


def fisher_p(x1, n1, x2, n2):
    return st.fisher_exact([[x1, n1 - x1], [x2, n2 - x2]])[1]


def share_p(x1, n1, x2, n2):
    if n1 <= 0 or n2 <= 0:
        return None
    return z_p(x1, n1, x2, n2) if n1 >= MIN_LOANS else fisher_p(round(x1), n1, round(x2), n2)


def bh(ps):
    """Benjamini-Hochberg over the p-values that exist (Control!C29), statsmodels' own."""
    idx = [i for i, p in enumerate(ps) if p is not None]
    out = list(ps)
    if idx:
        adj = multipletests([ps[i] for i in idx], method="fdr_bh")[1]
        for i, a in zip(idx, adj):
            out[i] = float(a)
    return out


def setter(ps):
    """For the sampling tolerance only (29 Sep 2026): the raw p-value that sets each Benjamini-Hochberg p. An adjusted
    p is the smallest p_(j) m / j over the ranks j at or above its own, so it can be set by another pocket's raw p --
    whose sampling error, when it sits nearer one half, is larger than its own. compare.py's tolerance is that raw p's
    error times m / j (found on the Flag book: a pocket whose raw p was 0.96 took its adjusted 0.99 from a neighbour)."""
    idx = sorted((i for i, p in enumerate(ps) if p is not None), key=lambda i: ps[i])
    m = len(idx)
    out = list(ps)
    best, who = None, None
    for rank in range(m, 0, -1):
        i = idx[rank - 1]
        v = ps[i] * m / rank
        if best is None or v < best:
            best, who = v, ps[i]
        out[i] = who
    return out


def power_2p(p1, n1, p2, n2):
    """statistics.md A3: the chance a pocket at true rate p1 is called different, two-sided at 95%."""
    pbar = (n1 * p1 + n2 * p2) / (n1 + n2)
    se0 = math.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2))
    se1 = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return st.norm.cdf((abs(p1 - p2) - Z * se0) / se1)


def mde_2p(n1, p2, n2, power):
    """The smallest multiple of p2 a pocket of n1 catches `power` of the time (A3)."""
    if power_2p(0.999, n1, p2, n2) < power:
        return None
    return brentq(lambda p1: power_2p(p1, n1, p2, n2) - power, p2 * (1 + 1e-12), 0.999, xtol=1e-15) / p2


def spread(m):
    """The book's rate, S_d (sd of y - R x across its loans) and the average x (statistics.md A3; Record!C31)."""
    i = IN[m]
    y, x = MY[m][i], MX[m][i]
    r = y.sum() / x.sum()
    return r, float(np.std(y - r * x, ddof=1)), float(x.mean())


SPREAD = {m: spread(m) for m in MEASURES}


def ratio_gap(n, m):
    """The smallest multiple a pocket of n loans shows 80% of the time at 95%: the sample-size formula
    n = ((z_a + z_b sqrt(g)) S_d / (xbar (g - 1) R))^2 solved for g."""
    r, sd, xb = SPREAD[m]
    need = lambda g: ((Z + ZP * math.sqrt(g)) * sd / (xb * (g - 1) * r)) ** 2 - n     # noqa: E731
    hi = 2.0
    while need(hi) > 0:
        hi *= 2
    return brentq(need, 1 + 1e-12, hi, xtol=1e-15)


def diff_gap(n, m):
    """Profit: the smallest gap in points, (z_a + z_b) (S_d / xbar) sqrt(1/n + 1/(N - n))."""
    r, sd, xb = SPREAD[m]
    rest = BOOK[m][2] - n
    if n < 2 or rest < 1:
        return None
    return (Z + ZP) * sd / abs(xb) * math.sqrt(1 / n + 1 / rest)


def caught(m, n):
    if m == "Bad loans":
        return mde_2p(n, BAD_RATE, BOOK[m][2] - n, POWER)
    if m in PROFIT:
        g = diff_gap(n, m)
        return None if g is None else -g * 100
    return ratio_gap(n, m)


# the two suggested lines (Control!I15:I16; Record!C41): the median, over two-way pockets of at least MIN_LOANS
# loans, of the smallest multiple each can call significant (caught half the time), to two places
def suggested_worse():
    gaps = []
    for g in GRIDS[:4]:
        cnt = Counter(k for k, v in zip(keys_of(g), MEASURES["Bad loans"]) if v is not None)
        for k, n in cnt.items():
            if n >= MIN_LOANS:
                x = mde_2p(n, BAD_RATE, BOOK["Bad loans"][2] - n, 0.5)
                if x:
                    gaps.append(x)
    return round(statistics.median(gaps), 2)


WORSE_AT = suggested_worse()
BETTER_AT = round(1 / WORSE_AT, 2)
GCO_LINE = MAT_SHARE * BOOK["Charge-offs"][0]
LINE = {"Bad loans": MAT_SHARE * BOOK["Bad loans"][0], "Bad dollars": MAT_SHARE * BOOK["Bad dollars"][0],
        "Charge-offs": GCO_LINE, "Kept after losses": GCO_LINE, "Earned before losses": GCO_LINE}


# ------------------------------------------------------------------ the shuffle test, this road's own
def shuffle_rest(m, layouts, group_of):
    """Two-sided shuffle test of rate(pocket) - rate(rest of its group), for every pocket of every layout at once:
    the loans that entered the rate are dealt at random within their group (the whole book when group_of is
    None), each pocket keeping its count. p = (hits + 1) / (B + 1). Returns {layout index: {pocket: p}}."""
    i = np.flatnonzero(IN[m])
    y, x = MY[m][i], MX[m][i]
    grp = np.zeros(len(i), dtype=np.int64) if group_of is None else np.array([group_of[j] for j in i])
    base = np.argsort(grp, kind="stable")
    out = []
    plans = []
    for lay in layouts:
        keys = [lay[j] for j in i]
        codes = {k: c for c, k in enumerate(sorted(set(keys), key=repr))}
        pk = np.array([codes[k] for k in keys])
        # slices: by group, then by pocket
        o = np.lexsort((pk, grp))
        ps, gs = pk[o], grp[o]
        starts = np.flatnonzero(np.r_[True, (ps[1:] != ps[:-1]) | (gs[1:] != gs[:-1])])
        ends = np.r_[starts[1:], len(o)]
        gstart = {g: np.flatnonzero(gs == g)[0] for g in np.unique(gs)}
        plans.append((codes, ps[starts], gs[starts], starts, ends, gstart))
    # observed pocket sums per layout
    obs_all = []
    for (codes, pks, gps, s0, s1, gstart), lay in zip(plans, layouts):
        keys = np.array([codes[lay[j]] for j in i])
        py = np.array([y[(keys == p_) & (grp == g_)].sum() for p_, g_ in zip(pks, gps)])
        px = np.array([x[(keys == p_) & (grp == g_)].sum() for p_, g_ in zip(pks, gps)])
        GY = np.array([y[grp == g_].sum() for g_ in gps])
        GX = np.array([x[grp == g_].sum() for g_ in gps])
        with np.errstate(divide="ignore", invalid="ignore"):
            g = py / px - (GY - py) / (GX - px)
        ok = (px != 0) & ((GX - px) != 0) & np.isfinite(g)
        obs_all.append((py, px, GY, GX, np.where(ok, g, 0.0), ok))
    hits = [np.zeros(len(p[1]), dtype=np.int64) for p in plans]
    chunk = 250
    order_by_group = grp[base]
    for start in range(0, B, chunk):
        k = min(chunk, B - start)
        noise = RNG.random((k, len(i)))
        # within each group a uniform random order: sort by (group, noise)
        o = np.lexsort((noise, np.broadcast_to(grp, noise.shape)), axis=1)
        ys, xs = y[o], x[o]
        cy = np.concatenate([np.zeros((k, 1)), np.cumsum(ys, axis=1)], axis=1)
        cx = np.concatenate([np.zeros((k, 1)), np.cumsum(xs, axis=1)], axis=1)
        for li, (codes, pks, gps, s0, s1, gstart) in enumerate(plans):
            py_, px_, GY, GX, g0, ok = obs_all[li]
            # positions: the group occupies the same block in the sorted order; the pocket its slice within it
            sy = cy[:, s1] - cy[:, s0]
            sx = cx[:, s1] - cx[:, s0]
            with np.errstate(divide="ignore", invalid="ignore"):
                gs_ = sy / sx - (GY - sy) / (GX - sx)
            hits[li] += (~(np.abs(gs_) < np.abs(g0) * (1 - 1e-9))).sum(axis=0)
    for li, (codes, pks, gps, s0, s1, gstart) in enumerate(plans):
        back = {c: k for k, c in codes.items()}
        py_, px_, GY, GX, g0, ok = obs_all[li]
        out.append({back[int(p_)]: float((h + 1) / (B + 1)) for p_, h, o_ in zip(pks, hits[li], ok) if o_})
    return out


def shuffle_halves(m, keys, half, tested):
    """The split's shuffle (Split!C7): loans dealt into the two halves at random inside their pocket. Per pocket,
    rate(high) - rate(low); pooled over the tested pockets, sum over pockets of (y_high - rate_low * x_high)."""
    i = np.array([j for j in np.flatnonzero(IN[m]) if half[j] in ("high", "low")])
    y, x = MY[m][i], MX[m][i]
    pkeys = sorted({keys[j] for j in i}, key=repr)
    code = {k: c for c, k in enumerate(pkeys)}
    grp = np.array([code[keys[j]] for j in i])
    hi = np.array([half[j] == "high" for j in i])
    o = np.lexsort((~hi, grp))                # by pocket, high half first
    g_o, h_o = grp[o], hi[o]
    starts = np.flatnonzero(np.r_[True, g_o[1:] != g_o[:-1]])
    ends = np.r_[starts[1:], len(o)]
    nh = np.array([h_o[a:b].sum() for a, b in zip(starts, ends)])
    pooled = np.array([pkeys[g] in tested for g in g_o[starts]])

    def stats_(ys, xs):
        cy = np.concatenate([np.zeros((ys.shape[0], 1)), np.cumsum(ys, axis=1)], axis=1)
        cx = np.concatenate([np.zeros((xs.shape[0], 1)), np.cumsum(xs, axis=1)], axis=1)
        yh, xh = cy[:, starts + nh] - cy[:, starts], cx[:, starts + nh] - cx[:, starts]
        yl, xl = cy[:, ends] - cy[:, starts + nh], cx[:, ends] - cx[:, starts + nh]
        with np.errstate(divide="ignore", invalid="ignore"):
            gap = yh / xh - yl / xl
            t = (yh - yl / xl * xh)[:, pooled].sum(axis=1)
        return gap, t
    g0, t0 = stats_(y[o][None, :], x[o][None, :])
    g0, t0 = g0[0], t0[0]
    hits, thits = np.zeros(len(starts), dtype=np.int64), 0
    for start in range(0, B, 250):
        k = min(250, B - start)
        noise = RNG.random((k, len(i)))
        oo = np.lexsort((noise, np.broadcast_to(grp, noise.shape)), axis=1)
        # each pocket's block, dealt at random; the first nh of the block are the "high" half
        ys, xs = y[oo], x[oo]
        gs, ts = stats_(ys, xs)
        hits += (~(np.abs(gs) < np.abs(g0) * (1 - 1e-9))).sum(axis=0)
        thits += int((~(np.abs(ts) < abs(t0) * (1 - 1e-9))).sum())
    per = {pkeys[g]: float((h + 1) / (B + 1)) for g, h, v in zip(g_o[starts], hits, g0) if np.isfinite(v)}
    return per, float((thits + 1) / (B + 1)), float(t0)


# ------------------------------------------------------------------ every grid
def sums(idx, m):
    i = idx[IN[m][idx]]
    y, x = MY[m][i], MX[m][i]
    return {"n": len(i), "sy": float(y.sum()), "sx": float(x.sum()), "ev": int((y != 0).sum()),
            "syy": float((y * y).sum()), "sxx": float((x * x).sum()), "sxy": float((x * y).sum())}


def minus(a, b):
    return {k: a[k] - b[k] for k in a}


def rate_of(s):
    return s["sy"] / s["sx"] if s["sx"] else None


def gap_of(r, base, m):
    if r is None or base is None:
        return None
    if m in PROFIT:
        return (r - base) * 100
    if base == 0:
        return None
    return r / base if base > 0 else 1 + (r - base) / abs(base)


def excess(s, base, m):
    if base is None:
        return None
    return s["sy"] - base * s["sx"] if m not in PROFIT else base * s["sx"] - s["sy"]


def verdict(m, s, gap, p):
    """Pockets!D7, Worse?: Yes at 1.34x or more with p under 5% (profit: short of it, its own test significant);
    Not sure: the gap is there, the p isn't; Too few losses: fewer than 10; No: anything else."""
    if m not in PROFIT and s["ev"] < MIN_EVENTS:
        return "Too few losses", "few"
    if gap is None:
        return None, None
    sig = p is not None and p < ALPHA
    if m in PROFIT:
        if not sig or gap == 0:
            return "No", "in line"
        return ("Yes", "worse") if gap < 0 else ("No", "better")
    if BETTER_AT < gap < WORSE_AT:
        return "No", "in line"
    worse = gap >= WORSE_AT
    if not sig:
        return ("Not sure", "unsure worse") if worse else ("No", "unsure better")
    return ("Yes", "worse") if worse else ("No", "better")


E = {}          # key (json) -> expected


def rec_key(cell):
    """A Record figure's name: the label it sits under and how many rows below it (Record's rows move with the run;
    read_book.py names what it reads the same way). The full tie-out named them by the cell they held on 28 Sep, and
    these are those cells' labels."""
    col, r = cell[0], int(cell[1:])
    ms = list(MEASURES)
    table = {"C11": ("Loans run", 0), "C15": ("Origination dates", 0), "C16": ("Band edges used: FICO", 0),
             "C17": ("Band edges used: ORIG_BAL", 0), "C19": ("Split", 1),
             "C20": (f"How closely {SPLITCOL} moves with FICO", 0),
             "C21": (f"How closely {SPLITCOL} moves with ORIG_BAL", 0),
             "C41": ("Worked out from this book", 0), "C42": ("Worked out from this book", 1),
             "C43": ("Pockets tested", 0), "C44": ("Pocket budget", 0), "C45": ("Pocket budget", 1),
             "C63": ("Pockets in all", 0), "C73": ("Alone in its band", 0), "F68": ("(the run's time)", 0),
             "F25": ("Tests", 0), "F39": ("How profit reads", 1), "F40": ("How profit reads", 2),
             "F41": ("How profit reads", 3), "F43": ("Families of tests", 0)}
    for i, m in enumerate(ms):
        table[f"C{26 + i}"] = (f"Worse now: {m}", 0)
        table[f"C{36 + i}"] = (f"Materiality line: {m}", 0)
        table[f"C{68 + i}"] = (f"Left out of {m}", 0)
    for i, m in enumerate(ms[:3]):
        table[f"C{31 + i}"] = (f"Loans needed for a {WORSE_AT:.2f}x gap: {m}", 0)
    for i, m in enumerate(ms[3:]):
        table[f"C{34 + i}"] = (f"Smallest gap a typical pocket could show: {m}", 0)
    lab, k = table[cell]
    return ["record", col, lab, k]


def put(key, value, how="", **extra):
    if key[0] == "record" and len(key) == 2:
        key = rec_key(key[1])
    E[json.dumps(key)] = {"value": value, "how": how, **extra}


P = {}          # (grid, measure, cell) -> everything about a pocket
WB_P = {}
if FLIPS_FROM:
    MKEY = {"outcome_booked": "Bad dollars", "gco_rate": "Charge-offs", "ranr_rate": "Kept after losses",
            "contribution_rate": "Earned before losses"}
    for r in json.load(open(FLIPS_FROM)):
        if r["Rate (key)"] not in MKEY:
            continue
        seg = str(r["Segment"])
        if f" / {SPLITCOL} " in str(seg):
            d_, h_ = seg.split(f" / {SPLITCOL} ")
            seg = (d_, h_.replace(" half", ""))
        for att, col in (("book", "p-value vs book, after the allowance"),
                         ("band", "p-value vs band, after the allowance")):
            v = r.get(col)
            if v not in (None, ""):
                WB_P[(r["Grid"], (str(r["Band"]), seg), MKEY[r["Rate (key)"]], att)] = float(v)
GRID_CELLS = {}
for g in GRIDS:
    name, bcol, dcol, three = g
    keys = keys_of(g)
    idx_of = defaultdict(list)
    for j, k in enumerate(keys):
        idx_of[k].append(j)
    idx_of = {k: np.array(v) for k, v in idx_of.items()}
    bands = order([k[0] for k in keys], LABELS[bcol])
    dims = order([k[1] for k in keys]) if not three else sorted(set(k[1] for k in keys), key=repr)
    GRID_CELLS[name] = (bands, dims, idx_of)
    for m in MEASURES:
        whole = sums(np.arange(N), m)
        band_tot = {b: sums(np.concatenate([v for k, v in idx_of.items() if k[0] == b]), m) for b in bands}
        mates = Counter(k[0] for k in idx_of)
        for k, idx in idx_of.items():
            s = sums(idx, m)
            s["rows"] = len(idx)
            rb = minus(band_tot[k[0]], s)
            rr = minus(whole, s)
            alone = mates[k[0]] == 1
            s["rate"] = rate_of(s)
            s["rb_rate"] = rate_of(rb) if rb["sx"] else None
            s["rr_rate"] = rate_of(rr) if rr["sx"] else None
            s["vs_band"] = gap_of(s["rate"], s["rb_rate"], m)
            s["vs_rest"] = gap_of(s["rate"], s["rr_rate"], m)
            s["vs_top"] = gap_of(s["rate"], RATE[m], m)
            s["ex_band"] = excess(s, s["rb_rate"], m)
            s["ex_rest"] = excess(s, s["rr_rate"], m)
            s["alone"], s["by_band"] = alone, not alone
            s["dollars"] = s["ex_band"] if not alone else s["ex_rest"]
            s["other"] = s["ex_rest"] if not alone else s["ex_band"]
            if m == "Bad loans":
                s["p_band_raw"] = share_p(s["sy"], s["n"], rb["sy"], rb["n"]) if rb["n"] > 0 else None
                s["p_book_raw"] = share_p(s["sy"], s["n"], rr["sy"], rr["n"])
            if m not in PROFIT and s["ev"] < MIN_EVENTS:      # too few losses: not tested (Pockets!D7)
                s["tested"] = False
            else:
                s["tested"] = True
            P[(name, m, k)] = s

# the dollar measures' shuffles: against the rest of the book (every loan), and of its band (within the band)
CACHE = OUT.replace("-flip", "").replace(".json", "") + "-shuffles.json"
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def enc(k):
    return json.dumps([k[0], list(k[1]) if isinstance(k[1], tuple) else k[1]])


def dec(s):
    a, b = json.loads(s)
    return (a, tuple(b) if isinstance(b, list) else b)


for m in DOLLAR:
    for bcol in ("FICO", "ORIG_BAL"):
        gs = [g for g in GRIDS if g[1] == bcol]
        lays = [keys_of(g) for g in gs]
        band_code = {b: c for c, b in enumerate(sorted(set(BAND[bcol])))}
        ck = f"rest|{m}|{bcol}"
        if ck not in cache:
            bb = shuffle_rest(m, lays, [band_code[b] for b in BAND[bcol]])
            br = shuffle_rest(m, lays, None)
            cache[ck] = [[{enc(k): v for k, v in d_.items()} for d_ in bb], [{enc(k): v for k, v in d_.items()}
                                                                            for d_ in br]]
        by_band = [{dec(k): v for k, v in d_.items()} for d_ in cache[ck][0]]
        by_book = [{dec(k): v for k, v in d_.items()} for d_ in cache[ck][1]]
        for g, pb, pr in zip(gs, by_band, by_book):
            for k in GRID_CELLS[g[0]][2]:
                s = P[(g[0], m, k)]
                s["p_band_raw"] = pb.get(k) if s["rb_rate"] is not None else None
                s["p_book_raw"] = pr.get(k)
    print("shuffled", m, flush=True)

# the allowance: one grid, one measure, one comparison; pockets not tested have no p (Pockets!D7-D8)
for g in GRIDS:
    for m in MEASURES:
        ks = list(GRID_CELLS[g[0]][2])
        for attr in ("p_band", "p_book"):
            raw = [P[(g[0], m, k)][attr + "_raw"] if P[(g[0], m, k)]["tested"] else None for k in ks]
            for k, a in zip(ks, bh(raw)):
                P[(g[0], m, k)][attr] = a
                P[(g[0], m, k)][attr + "_mult"] = None
            # the allowance's own multiplier for each p, for the sampling tolerance (compare.py)
            idx = [i for i, p in enumerate(raw) if p is not None]
            for i in idx:
                P[(g[0], m, ks[i])][attr + "_family"] = len(idx)
            for k, sp in zip(ks, setter(raw)):
                P[(g[0], m, k)][attr + "_setter"] = sp
        for k in ks:
            s = P[(g[0], m, k)]
            gap = s["vs_band"] if s["by_band"] else s["vs_rest"]
            p = s["p_band"] if s["by_band"] else s["p_book"]
            s["gap"], s["p"] = gap, p
            s["rest_rate"] = s["rb_rate"] if s["by_band"] else s["rr_rate"]
            pv = p
            if WB_P and m in DOLLAR and p is not None:
                theirs = WB_P.get((g[0], k, m, "band" if s["by_band"] else "book"))
                raw = s[("p_band" if s["by_band"] else "p_book") + "_raw"]
                mult = max(1.0, p / raw) if raw else 1.0
                tol = max(4 * math.sqrt(2 * raw * (1 - raw) / B), 4 / B) * mult
                if theirs is not None and (theirs < ALPHA) != (p < ALPHA) and abs(theirs - p) <= tol:
                    pv = theirs
                    FLIPPED.append([g[0], m, k[0], json.dumps(k[1]), p, theirs])
            s["worse"], s["flag"] = verdict(m, s, gap, pv)
            s["material"] = "Yes" if s["dollars"] is not None and s["dollars"] > 0 and s["dollars"] >= LINE[m] \
                else "No"
            s["caught"] = caught(m, s["n"]) if s["n"] >= 1 else None

from decimal import Decimal, ROUND_HALF_UP  # noqa: E402

# ------------------------------------------------------------------ Borderline (30 Sep 2026; docs/statistics.md B2a)
# A verdict is borderline when the p-value that decides it came from shuffling and sits within 2 of its own standard
# errors of the bar (5%), either side, and the verdict's word turns on it (Record's "Borderline" rule, in words). The
# standard error of a shuffled p is sqrt(p (1 - p) / shuffles); after the allowance, the SE of the raw p that SET the
# adjusted one (Benjamini-Hochberg: p_(j) m / j, the smallest over the ranks at or above), times that m / j, and none
# when the allowance capped it at 1 (B2a says so in words). Written here from those words: this road's own p-values,
# its own setter.
BAR, BORDER_SE = ALPHA, 2.0


def p_text(p):
    """The printed p: TEXT(p, "0.000"), or "0.0000" where three places would round it onto the bar (Record's rule)."""
    d = Decimal(repr(float(p)))
    three = d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if three == Decimal(repr(BAR)).quantize(Decimal("0.001")):
        return str(d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
    return str(three)


def se_after(adj, setter_raw):
    """The SE of an adjusted shuffled p: its setter's SE times m / j (= adj / setter's raw); None when capped."""
    if adj is None or setter_raw is None or setter_raw <= 0 or adj >= 1.0:
        return None
    return math.sqrt(setter_raw * (1 - setter_raw) / B) * (adj / setter_raw)


def tol_of(adj, setter_raw):
    """compare.py's sampling tolerance for an adjusted p: four SEs of the difference of two roads' estimates of the
    setter's raw p, times m / j."""
    r = setter_raw if setter_raw is not None else adj
    mult = max(1.0, adj / r) if r else 1.0
    return max(4 * math.sqrt(2 * r * (1 - r) / B), 4 / B) * mult


def near(p, se):
    return p is not None and se is not None and abs(p - BAR) <= BORDER_SE * se


def decides(flag, gap, m):
    """engine's rule in words: worse against worse-not-significant, better likewise; profit read by its own test, in
    line against worse or better, when there is a gap."""
    if flag in ("worse", "better", "unsure worse", "unsure better"):
        return True
    return m in PROFIT and flag == "in line" and gap not in (None, 0)


def turns_worse(flag, gap, m):
    if flag in ("worse", "unsure worse"):
        return True
    return m in PROFIT and flag == "in line" and gap is not None and gap < 0


for (gname, m, k), s in P.items():
    s["bl"] = s["wbl"] = ""
    s["se"] = s["tol"] = None
    if m not in DOLLAR or s.get("p") is None or not s["tested"]:
        continue
    att = "p_band" if s["by_band"] else "p_book"
    r_ = s.get(att + "_setter") or s[att + "_raw"]
    s["se"] = se_after(s["p"], r_)
    s["tol"] = tol_of(s["p"], r_)
    if near(s["p"], s["se"]) and decides(s["flag"], s["gap"], m):
        s["bl"] = p_text(s["p"])
        if turns_worse(s["flag"], s["gap"], m):
            s["wbl"] = s["bl"]


def with_flag(word, pt):
    return f"{word} · borderline (p {pt})" if word and pt else word


def wb_row(gname, m, k):
    """How this pocket is named on _pockets (read_book.py's wb-pockets.json), to find the workbook's own p."""
    mk = {"Bad loans": "outcome_loans", "Bad dollars": "outcome_booked", "Charge-offs": "gco_rate",
          "Kept after losses": "ranr_rate", "Contribution": "contribution_rate",
          "Earned before losses": "contribution_rate"}[m]
    seg = k[1] if isinstance(k[1], str) else (f"{k[1][0]} / {SPLITCOL} {k[1][1]} half" if HOW == "own_median"
                                              else f"{k[1][0]} / {SPLITCOL} {k[1][1]}")
    return [gname, str(k[0]), seg, mk]


def border_extra(gname, m, k):
    s = P[(gname, m, k)]
    att = "p_band" if s["by_band"] else "p_book"
    return {"border": {"p": s.get("p"), "se": s["se"], "tol": s["tol"], "bl": s["bl"], "wbl": s["wbl"],
                       "r": s.get(att + "_setter") or s.get(att + "_raw"), "m": s.get(att + "_family"),
                       "row": wb_row(gname, m, k)}}


# every pocket on _pockets: the borderline p-value that decides (P_BTXT), and the one for Worse? (P_WBTXT)
def wrong_bl(s, m):
    """A plausible wrong method (a plant for mutate.py): the adjusted p's own SE, sqrt(p (1 - p) / shuffles)."""
    p = s.get("p")
    if p is None or m not in DOLLAR or not s["tested"] or p >= 1:
        return ""
    se = math.sqrt(p * (1 - p) / B)
    return p_text(p) if near(p, se) and decides(s["flag"], s["gap"], m) else ""


for (gname, m, k), s in P.items():
    who = ["pk-border", *wb_row(gname, m, k)]
    put(who + ["any"], s["bl"], "B2a from this road's p and its setter's SE", **border_extra(gname, m, k),
        **({"plant": wrong_bl(s, m)} if wrong_bl(s, m) != s["bl"] else {}))
    put(who + ["worse"], s["wbl"], "B2a, only where Worse? turns on it", **border_extra(gname, m, k))
    if s["se"] is not None:
        put(who + ["se"], s["se"], "the setter's SE times m / j", **border_extra(gname, m, k))


# ------------------------------------------------------------------ Grids: the four blocks, and how common
for g in GRIDS:
    name, bcol, dcol, three = g
    bands, dims, idx_of = GRID_CELLS[name]
    colname = (lambda d: f"{d[0]} · {d[1]}") if three else (lambda d: d)
    for m in MEASURES:
        def cell_sums(b, d):
            ks = [k for k in idx_of if (b == "All" or k[0] == b) and (d == "All" or k[1] == d)]
            if not ks:
                return None
            return sums(np.concatenate([idx_of[k] for k in ks]), m)
        for b in bands + ["All"]:
            for d in dims + ["All"]:
                s = cell_sums(b, d)
                if s is None:
                    continue
                r = rate_of(s)
                if r is not None:
                    put(["grid", name, m, "rate", b, colname(d) if d != "All" else "All"], r, "rate = sum y / sum x")
                few = m not in PROFIT and s["ev"] < MIN_EVENTS
                vt = gap_of(r, RATE[m], m)
                if vt is not None and not few:
                    put(["grid", name, m, "book", b, colname(d) if d != "All" else "All"], vt,
                        "pocket rate against the whole book's")
                if b != "All" and d != "All":
                    ps = P[(name, m, (b, d))]
                    if ps["vs_band"] is not None and not few:
                        put(["grid", name, m, "band", b, colname(d)], ps["vs_band"],
                            "pocket rate against the rest of its band")
                n_rows = sum(len(idx_of[k]) for k in idx_of if (b == "All" or k[0] == b) and (d == "All" or k[1] == d))
                put(["grid", name, "*", "loans", b, colname(d) if d != "All" else "All"], n_rows, "loans in the cell")
    if not three:
        half = HALF[(bcol, dcol)]
        sides = [("High half", "high"), ("Low half", "low")] if HOW == "own_median" else [(v, v) for v in VALUES]
        tot = {"loans": 0, "booked": 0.0}
        for lab, _ in sides:
            tot[f"{lab}|loans"], tot[f"{lab}|booked"] = 0, 0.0
        for (b, d), idx in idx_of.items():
            vals = {"loans": len(idx), "booked": sum(BAL[j] or 0.0 for j in idx)}
            for lab, side in sides:
                mine = [j for j in idx if half[j] == side]
                vals[f"{lab}|loans"], vals[f"{lab}|booked"] = len(mine), sum(BAL[j] or 0.0 for j in mine)
            for w, v in vals.items():
                put(["groups", name, b, d, w], v, "count and booked dollars, by hand")
                tot[w] += v
        for w, v in tot.items():
            put(["groups", name, "Every pocket", "None", w], v, "")
        for lab, _ in sides:
            put(["groups", name, "Share of the grid", "None", f"{lab}|loans"], tot[f"{lab}|loans"] / tot["loans"], "")
            put(["groups", name, "Share of the grid", "None", f"{lab}|booked"],
                tot[f"{lab}|booked"] / tot["booked"], "")

# ------------------------------------------------------------------ Pockets
# the band column REV_DEBT moves with most (Record!C20:C21); a category has none (Split!C9: "How closely SYS_FLAG
# moves with a band column isn't worked out for a category")
PARTNER = "FICO" if HOW == "own_median" else None
for kind, three in (("Two-way", False), (f"Split by {SPLITCOL}", True)):
    for m in MEASURES:
        cand = []
        for gi, g in enumerate(GRIDS):
            if g[3] != three:
                continue
            held = 0 if (not three or PARTNER is None or PARTNER in (g[1], g[2])) else 1
            for k in GRID_CELLS[g[0]][2]:
                s = P[(g[0], m, k)]
                d, o = s["dollars"], s["other"]
                if not ((d is not None and d > 0) or (o is not None and o > 0)):
                    continue
                losing = d is not None and d > 0
                key = (held, 0 if s["flag"] == "worse" and losing else 1, 0 if losing else 1,
                       -(d if losing else (o or 0.0)))
                cand.append((key, g, k, s))
        cand.sort(key=lambda t: t[0])
        for rank, (_, g, k, s) in enumerate(cand, 1):
            band = f"{g[1]} {k[0]}"
            seg, half = (k[1], None) if not three else k[1]
            who = [kind, m, band, seg, half]
            put(["pocket", *who, "rank"], rank, "worse and losing first, then by dollars (Pockets!D11)")
            put(["pocket", *who, "loans"], s["n"], "loans that entered the rate")
            put(["pocket", *who, "rate"], s["rate"], "")
            if s["rest_rate"] is not None:
                put(["pocket", *who, "rest-rate"], s["rest_rate"], "")
            if s["gap"] is not None:
                put(["pocket", *who, "gap"], s["gap"], "")
            if s["dollars"] is not None:
                put(["pocket", *who, "dollars"], s["dollars"], "")
            put(["pocket", *who, "worse"], with_flag(s["worse"], s["wbl"]),
                "the rule on Pockets!D7; with the borderline words where Worse? turns on a p that near the bar",
                **border_extra(g[0], m, k))
            if s["p"] is not None:
                att = "p_band" if s["by_band"] else "p_book"
                put(["pocket", *who, "p"], s["p"], "z / exact, or this road's shuffle; then BH",
                    raw=s.get(att + "_setter") or s[att + "_raw"], family=s.get(att + "_family"),
                    shuffled=m in DOLLAR)
            put(["pocket", *who, "material"], s["material"], "dollars at or over the line")
            if s["caught"] is not None:
                put(["pocket", *who, "caught"], s["caught"], "power formula, statistics.md A3")
            if three and PARTNER:
                put(["pocket", *who, "holds"], "Yes" if PARTNER in (g[1], g[2]) else "No: may be mostly FICO", "")
        nw = sum(1 for c in cand if c[3]["worse"] == "Yes")
        nwm = sum(1 for c in cand if c[3]["worse"] == "Yes" and c[3]["material"] == "Yes")
        put(["pockets-count", kind, m], [nwm, nw, len(cand)], "")

# ------------------------------------------------------------------ Paid, cost, kept (two-way grids)
def flag_word(s):
    return s["flag"]


for g in GRIDS[:4]:
    for k in GRID_CELLS[g[0]][2]:
        c, q, e = (P[(g[0], m, k)] for m in ("Charge-offs", "Kept after losses", "Earned before losses"))
        who = ["pck", g[0], k[0], k[1]]
        put(who + ["loans"], c["rows"], "")
        if e["gap"] is not None:
            put(who + ["earned-gap"], e["gap"], "")
            put(who + ["earned-dollars"], -e["dollars"], "")
        if c["gap"] is not None:
            put(who + ["gco-multiple"], c["gap"], "")
        if c["dollars"] is not None:
            put(who + ["gco-dollars"], c["dollars"], "")
        if q["gap"] is not None:
            put(who + ["kept-gap"], q["gap"], "")
            put(who + ["kept-dollars"], -q["dollars"], "")
        cf, kf = c["flag"], q["flag"]
        together = ""
        if cf != "few":
            if cf == "worse" and kf == "better":
                together = "Priced for it"
            elif cf == "worse" and kf == "worse":
                together = "Net drain"
            elif cf == "better" and kf == "better":
                together = "Strong"
            elif cf == "better" and kf == "worse":
                together = "Safe but idle"
            elif kf == "worse":
                together = "Earns less, not from losses"
            elif cf == "worse":
                together = "Losing more, profit holding"
        # Borderline: Together turns on both sides' flags, so it carries either side's borderline p-value (the
        # charge-offs first, "p 0.048 and 0.052")
        ps_ = [x["bl"] for x in (c, q) if x["bl"]] if together else []
        put(who + ["together"], f"{together} · borderline (p {' and '.join(ps_)})" if ps_ else together,
            "Paid, cost, kept!C9's words, and either side's borderline p",
            sides=[border_extra(g[0], "Charge-offs", k)["border"], border_extra(g[0], "Kept after losses", k)["border"]])

# ------------------------------------------------------------------ Split
def half_sums(idx, m, half):
    hi = np.array([j for j in idx if half[j] == "high"], dtype=np.int64)
    lo = np.array([j for j in idx if half[j] == "low"], dtype=np.int64)
    return sums(hi, m), sums(lo, m)


def rb_or(strata, z):
    """Mantel-Haenszel's pooled odds ratio with the Robins-Breslow-Greenland range (statistics.md A5)."""
    R = S = PR = PS = QR = QS = 0.0
    for a, b, c, d in strata:
        n = a + b + c + d
        p, q, r, s = (a + d) / n, (b + c) / n, a * d / n, b * c / n
        R += r
        S += s
        PR += p * r
        PS += p * s
        QR += q * r
        QS += q * s
    o = R / S
    se = math.sqrt(PR / (2 * R * R) + (PS + QR) / (2 * R * S) + QS / (2 * S * S))
    return o, math.exp(math.log(o) - z * se), math.exp(math.log(o) + z * se)


def cmh_p(strata):
    """Cochran-Mantel-Haenszel, no continuity correction (Record!F28:F30), from statsmodels."""
    from statsmodels.stats.contingency_tables import StratifiedTable
    t = StratifiedTable([np.array([[a, b], [c, d]], dtype=float) for a, b, c, d in strata])
    # the statistic from statsmodels, its tail from scipy: statsmodels' own p-value is 1 - cdf, which reads 0 below
    # about 1e-16, and these run to 1e-30
    return float(st.chi2.sf(t.test_null_odds(correction=False).statistic, 1))


def cochran_q_p(strata):
    """Cochran's Q about the Woolf-weighted mean log odds ratio, 0.5 added to a pocket with a zero (A8)."""
    th, w = [], []
    for a, b, c, d in strata:
        if a + c == 0 or b + d == 0 or a + b == 0 or c + d == 0:
            continue
        if min(a, b, c, d) == 0:
            a, b, c, d = a + .5, b + .5, c + .5, d + .5
        th.append(math.log(a * d / (b * c)))
        w.append(1 / (1 / a + 1 / b + 1 / c + 1 / d))
    th, w = np.array(th), np.array(w)
    q = float((w * (th - (w * th).sum() / w.sum()) ** 2).sum())
    return float(st.chi2.sf(q, len(w) - 1))


def steady_or_none(strata):
    usable = [t for t in strata if not (t[0] + t[2] == 0 or t[1] + t[3] == 0 or t[0] + t[1] == 0 or t[2] + t[3] == 0)]
    return cochran_q_p(strata) if len(usable) >= 2 else None


def compare_sides(g, m, mine_of, rest_of, shuffle_key):
    """One side of every pocket against the other (Split!C4-C8): the high half against the low, or one value against
    the rest of its pocket. `mine_of(idx)` and `rest_of(idx)` pick each side's loans. Returns the pooled figures
    and, per pocket, [gap, p]."""
    name, bcol, dcol, _ = g
    bands, dims, idx_of = GRID_CELLS[name]
    per, strata, O, Ev, V, hden, worse_n = {}, [], 0.0, 0.0, 0.0, 0.0, 0
    for k, idx in idx_of.items():
        sh, sl = sums(np.array(mine_of(idx), dtype=np.int64), m), sums(np.array(rest_of(idx), dtype=np.int64), m)
        thin = sh["n"] < MIN_LOANS or sl["n"] < MIN_LOANS or not sh["sx"] or not sl["sx"]
        few = m not in PROFIT and sh["ev"] + sl["ev"] < MIN_EVENTS
        if thin or few:
            continue
        rh, rl = sh["sy"] / sh["sx"], sl["sy"] / sl["sx"]
        v = (rh - rl) * 100 if m in PROFIT else (rh / rl if rl else None)
        p = z_p(sh["sy"], sh["n"], sl["sy"], sl["n"]) if m == "Bad loans" else None
        per[k] = [v, p]
        if m in PROFIT:
            worse_n += (rh - rl) < 0
        else:
            worse_n += (rh / rl > 1) if rl else rh > rl
        if m == "Bad loans":
            strata.append((sh["ev"], sh["n"] - sh["ev"], sl["ev"], sl["n"] - sl["ev"]))
        # the side's total against what it would be at the other side's rate (Split!C6), with the variance of that
        # difference: the side's own spread about the other's rate, plus the other's rate's uncertainty carried on
        # the side's dollars
        O += sh["sy"]
        Ev += rl * sh["sx"]
        hden += sh["sx"]
        n = sh["n"]
        s_dd = max(sh["syy"] - 2 * rl * sh["sxy"] + rl * rl * sh["sxx"], 0.0) * n / max(n - 1, 1)
        n_l = sl["n"]
        s_l = max(sl["syy"] - 2 * rl * sl["sxy"] + rl * rl * sl["sxx"], 0.0) / (n_l - 1)
        se_l = math.sqrt(s_l / n_l) / (sl["sx"] / n_l)
        V += s_dd + (sh["sx"] * se_l) ** 2
    out = {"pockets": len(per), "worse": worse_n}
    if per:
        if m in PROFIT:
            out["value"] = (O - Ev) / hden * 100
            h = Z * math.sqrt(V) / hden * 100
            out["lo"], out["hi"] = out["value"] - h, out["value"] + h
        elif Ev > 0:
            out["value"] = O / Ev
            h = Z * math.sqrt(V) / Ev
            out["lo"], out["hi"] = max(out["value"] - h, 0.0), out["value"] + h
            if m == "Bad loans" and V > 0:
                out["p"] = math.erfc(abs(O - Ev) / math.sqrt(V) / math.sqrt(2))
        if m == "Bad loans" and strata:
            out["odds"], out["odds_lo"], out["odds_hi"] = rb_or(strata, Z)
            out["odds_p"] = cmh_p(strata)
            out["steady_p"] = steady_or_none(strata)
        if m in DOLLAR:
            if shuffle_key not in cache:
                side = np.full(N, "none", dtype=object)
                for k, idx in idx_of.items():
                    for j in mine_of(idx):
                        side[j] = "high"
                    for j in rest_of(idx):
                        side[j] = "low"
                a_, b_, _ = shuffle_halves(m, keys_of(g), list(side), set(per))
                cache[shuffle_key] = [{enc(k): v for k, v in a_.items()}, b_]
            pk_p = {dec(k): v for k, v in cache[shuffle_key][0].items()}
            for k in per:
                per[k][1] = pk_p.get(k)
            out["p"] = cache[shuffle_key][1]
    return out, per


def split_family(results):
    """The allowance on the pocket p-values: one family per grid and measure -- every value's pockets together for a
    category (Split!C8: "covers every value and pocket of one grid and measure")."""
    ks = [(sk, k) for sk, (out, per) in results.items() for k in per]
    raw = [results[sk][1][k][1] for sk, k in ks]
    adj = bh(raw)
    fam = len([1 for p_ in raw if p_ is not None])
    for (sk, k), a, r_ in zip(ks, adj, setter(raw)):
        results[sk][1][k][1] = a
        results[sk][1][k] += [fam, r_]


def put_split(label, m, out, per, words):
    shown = out.get("p")
    put(["split-sum", label, m, "Pockets"], out["pockets"], "")
    put(["split-sum", label, m, words[0]], [out["worse"], out["pockets"]] if out["pockets"] else "none big enough", "")
    if "value" in out:
        put(["split-sum", label, m, words[1]], out["value"], "")
        put(["split-sum", label, m, "Range"], [out["lo"], out["hi"]], "")
    if shown is not None:
        se_ = se_after(shown, out.get("p_setter", out.get("p_raw", shown))) if m in DOLLAR else None
        put(["split-sum", label, m, "p-value"], f"borderline (p {p_text(shown)})" if near(shown, se_) else shown, "",
            raw=out.get("p_setter", out.get("p_raw", shown)), family=out.get("fam", 1), shuffled=m in DOLLAR,
            border={"p": shown, "se": se_, "tol": tol_of(shown, out.get("p_setter", out.get("p_raw", shown))),
                    "bl": p_text(shown) if near(shown, se_) else "", "split": True})
    if "odds" in out:
        put(["split-sum", label, m, "As odds"], out["odds"], "")
        put(["split-sum", label, m, "p-value, as odds"], out["odds_p"], "", raw=out.get("odds_p_raw"),
            family=out.get("fam", 1))
    for (b, d), (v, p, fam, r_) in per.items():
        put(["split-pocket", label, m, b, d, "gap"], v, "", p=p, shuffled=m in DOLLAR, raw=r_, family=fam)
        if p is not None:
            se_ = se_after(p, r_) if m in DOLLAR else None
            put(["split-pocket", label, m, b, d, "p"], f"borderline (p {p_text(p)})" if near(p, se_) else p, "",
                raw=r_, family=fam, shuffled=m in DOLLAR,
                border={"p": p, "se": se_, "tol": tol_of(p, r_) if m in DOLLAR else None,
                        "bl": p_text(p) if near(p, se_) else "", "split": True})


def kgroup_mh(pockets):
    """B3, the K-group Mantel-Haenszel test of general association (docs/statistics.md B3; Landis, Heyman and Koch
    1978), written here from the textbook: in each pocket, bad counts per group against their expectation under no
    difference, the hypergeometric covariance, summed over pockets; Q = d' V^-1 d on K - 1 degrees of freedom. This
    road leaves out the FIRST group present (PocketBook's docs leave out the last): Q does not depend on which one,
    so the two roads agreeing is a check on both. Pockets that say nothing (under 2 loans, all bad or none bad) are
    dropped, as the docs say."""
    use = [(np.array(R, float), np.array(b, float)) for R, b in pockets]
    use = [(R, b) for R, b in use if R.sum() >= 2 and 0 < b.sum() < R.sum()]
    if not use:
        return None
    K = len(use[0][0])
    present = [k for k in range(K) if any(R[k] > 0 for R, _ in use)]
    keep = present[1:]
    if not keep:
        return None
    d = np.zeros(len(keep))
    Vm = np.zeros((len(keep), len(keep)))
    for R, b in use:
        Nh, Ch = R.sum(), b.sum()
        E = R * Ch / Nh
        d += (b - E)[keep]
        Rk = R[keep]
        Vm += Ch * (Nh - Ch) / (Nh * Nh * (Nh - 1)) * (Nh * np.diag(Rk) - np.outer(Rk, Rk))
    q = float(d @ np.linalg.solve(Vm, d))
    return {"q": q, "df": len(keep), "p": float(st.chi2.sf(q, len(keep))), "pockets": len(use)}


def text4(p):
    """TEXT(p, "0.0000"), rounding a half up as Excel does."""
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(repr(float(p))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


SPLIT_RESULTS = {}
SPLIT_GENERAL = {}
for g in GRIDS[:4]:
    name, bcol, dcol, _ = g
    half = HALF[(bcol, dcol)]
    if HOW == "own_median":
        for m in MEASURES:
            res = {name: compare_sides(g, m, lambda idx: [j for j in idx if half[j] == "high"],
                                       lambda idx: [j for j in idx if half[j] == "low"], f"halves|{m}|{name}")}
            split_family(res)
            out, per = res[name]
            if "p" in out:
                out["p_raw"] = out["p"]
            SPLIT_RESULTS[(name, m)] = (out, per)
            put_split(name, m, out, per, ("High half worse in", "High vs low, all"))
        sp = SPLIT_RESULTS[(name, "Bad loans")][0]["steady_p"]
        put(["split-steady", name], "no sign" if sp >= ALPHA else "differs", "Cochran's Q p = %.4f" % sp)
        # 30 Sep 2026: the chip is its words alone ("Holds FICO fixed"); the correlations are Record's
        put(["split-chip", name], "Holds FICO fixed" if PARTNER in (bcol, dcol) else "Doesn't hold FICO fixed",
            "the grid has FICO as its band or segment, or not")
        continue
    # a category: each value against the rest of its pocket (every other value there, together)
    labels = {v: f"{name} · {SPLITCOL} {v} vs " + (VALUES[1 - VALUES.index(v)] if len(VALUES) == 2 else "rest")
              for v in VALUES}
    for m in MEASURES:
        res = {}
        for v in VALUES:
            res[v] = compare_sides(g, m, lambda idx, v=v: [j for j in idx if half[j] == v],
                                   lambda idx, v=v: [j for j in idx if half[j] != v], f"value {v}|{m}|{name}")
        split_family(res)
        # each pooled p-value is a family across the values: one test per value (Split!C8)
        for what in ("p", "odds_p", "steady_p"):
            vs = [v for v in VALUES if res[v][0].get(what) is not None]
            for v, a, st_ in zip(vs, bh([res[v][0][what] for v in vs]), setter([res[v][0][what] for v in vs])):
                res[v][0][what + "_raw"] = res[v][0][what]
                res[v][0][what + "_setter"] = st_
                res[v][0][what] = a
                res[v][0]["fam"] = len(vs)
        for v in VALUES:
            out, per = res[v]
            SPLIT_RESULTS[(labels[v], m)] = (out, per)
            put_split(labels[v], m, out, per, ("Worse than the rest in", "Value vs rest, all"))
    # do the values differ at all: B3 over every pocket of the grid, however small (Split!C7), bad loans only
    bands, dims, idx_of = GRID_CELLS[name]
    pk = []
    for k, idx in idx_of.items():
        i_ = [j for j in idx if IN["Bad loans"][j]]
        pk.append(([sum(1 for j in i_ if half[j] == v) for v in VALUES],
                   [sum(1 for j in i_ if half[j] == v and FLAG[j] == 1) for v in VALUES]))
    b3 = kgroup_mh(pk)
    SPLIT_GENERAL[name] = b3
    dollars = ", ".join(m for m in MEASURES if m != "Bad loans")
    if b3 is None:
        said = "Bad loans: not tested"
    else:
        said = (f"Bad loans: {'yes' if b3['p'] < ALPHA else 'no sign they do'} (p-value "
                f"{'under 0.0001' if b3['p'] < 0.0001 else text4(b3['p'])}, on {b3['df']} "
                f"{'degree' if b3['df'] == 1 else 'degrees'} of freedom, {b3['pockets']} pockets)")
    for v in VALUES:
        sp = SPLIT_RESULTS[(labels[v], "Bad loans")][0].get("steady_p")
        put(["split-steady", labels[v]], "not tested" if sp is None else "no sign" if sp >= ALPHA else "differs",
            "Cochran's Q, after the allowance across the values")
        put(["split-differ", labels[v]], f"Do the values of {SPLITCOL} differ at all? {said}; {dollars}: not tested: "
                                          f"dollar rate.", "B3 written here from the textbook",
            b3=None if b3 is None else [b3["q"], b3["df"], b3["p"], b3["pockets"]])

# ------------------------------------------------------------------ Start here, Control
two = [(g, k) for g in GRIDS[:4] for k in GRID_CELLS[g[0]][2]]
n_two = len(two)
wm = [P[(g[0], "Charge-offs", k)] for g, k in two if P[(g[0], "Charge-offs", k)]["worse"] == "Yes"
      and P[(g[0], "Charge-offs", k)]["material"] == "Yes"]
nb_ = sum(1 for s_ in wm if s_["wbl"])
put(["start-tile", "Pockets worse and material, charge-offs"], [len(wm), n_two] + ([nb_] if nb_ else []),
    "worse and material; then how many of them are borderline on Worse?",
    members=[border_extra(g[0], "Charge-offs", k)["border"] for g, k in two
             if P[(g[0], "Charge-offs", k)]["worse"] == "Yes" and P[(g[0], "Charge-offs", k)]["material"] == "Yes"])
put(["start-tile", "Dollars above their share, in those"], sum(s["dollars"] for s in wm), "")
km = [P[(g[0], "Kept after losses", k)] for g, k in two
      if P[(g[0], "Kept after losses", k)]["worse"] == "Yes" and P[(g[0], "Kept after losses", k)]["material"] == "Yes"]
put(["start-tile", "Pockets keeping less, worse and material"], [len(km), sum(s["dollars"] for s in km)], "")
top = sorted(((P[(g[0], "Charge-offs", k)], g, k) for g, k in two
              if P[(g[0], "Charge-offs", k)]["worse"] == "Yes" and P[(g[0], "Charge-offs", k)]["material"] == "Yes"),
             key=lambda t: -t[0]["dollars"])[:5]
for i, (s, g, k) in enumerate(top, 1):
    band, seg = f"{g[1]} {k[0]}", k[1]
    put(["start-top", i, band, seg, "loans"], s["rows"], "")
    put(["start-top", i, band, seg, "multiple"], s["gap"], "")
    put(["start-top", i, band, seg, "dollars"], s["dollars"], "")
    put(["start-top", i, band, seg, "segment"], with_flag(f"ASSET_CLASS {seg}" if g[2] == "ASSET_CLASS" else seg, s["wbl"]),
        "the segment, borderline words when Worse? is",
        **border_extra(g[0], "Charge-offs", k))

gco_d = [P[(g[0], "Charge-offs", k)]["dollars"] for g, k in two if P[(g[0], "Charge-offs", k)]["dollars"] is not None]
pos = [d for d in gco_d if d > 0]
for i, share in enumerate((0.005, 0.01, 0.02, 0.05, 0.10), 1):
    t = share * BOOK["Charge-offs"][0]
    kept = [d for d in pos if d >= t]
    put(["ladder", i, "M"], [share * 100], "")
    put(["ladder", i, "N"], t, "")
    put(["ladder", i, "O"], len(kept), "")
    put(["ladder", i, "P"], sum(kept) / sum(pos), "")
put(["line", "worse", "*"], WORSE_AT, "the suggested line, worked out above")
put(["line", "better", "*"], BETTER_AT, "")
for m in MEASURES:
    put(["line", "material", m], [LINE[m]], "1% of the book's total for the measure; profit: the charge-off line")
put(["control", "E15"], [WORSE_AT], "")
put(["control", "F15"], [WORSE_AT], "")
put(["control", "I15"], [WORSE_AT], "")
put(["control", "K15"], WORSE_AT, "")
put(["control", "E16"], [BETTER_AT], "")
put(["control", "F16"], [BETTER_AT], "")
put(["control", "I16"], [BETTER_AT], "")
put(["control", "K16"], BETTER_AT, "")
put(["control", "E19"], [GCO_LINE], "")
put(["control", "F24"], [MIN_LOANS], "")
put(["control", "I24"], [MIN_LOANS], "")

# ------------------------------------------------------------------ Columns
cols = list(rows[0].keys())
for c in cols:
    blank = sum(1 for r in rows if r[c] == "")
    put(["columns", c, "blank"], blank / N, "")
put(["columns", "FICO", "odd"], [-9999, sum(1 for f in FICO if f == -9999)], "")
put(["columns", "RANR_AMT", "odd"], [sum(1 for q in RANR if q is not None and q < 0)], "")
fnum = [f for f in FICO if f is not None]
put(["columns", "FICO", "why"], [round(100 * sum(300 <= f <= 850 for f in fnum) / len(fnum)), 300, 850], "")
put(["columns", "BAD_FLAG", "why"], [0, 1, round(100 * sum(1 for f in FLAG if f == 1) / N, 1), 1], "")
put(["columns", "GCO_AMT", "why"], [round(100 * sum(1 for g in GCO if g == 0) / N)], "")
put(["columns", "CHANNEL", "why"], [len(set(DIMS["CHANNEL"]))], "")
put(["columns", "ASSET_CLASS", "why"], [len(set(DIMS["ASSET_CLASS"]))], "")
put(["columns", "REV_DEBT", "why"], [len(set(v for v in REV if v is not None))], "")
put(["columns", "BAD_FLAG", "check"], [sum(1 for f in FLAG if f is None), 0, 1], "")
put(["columns", "GCO_AMT", "check"], [sum(1 for g in GCO if g is None), sum(1 for g in GCO if g is not None)], "")
put(["columns", "CHANNEL", "check"], [len(set(DIMS["CHANNEL"]))], "")
put(["columns", "ASSET_CLASS", "check"], [len(set(DIMS["ASSET_CLASS"]))], "")
put(["columns", "REV_DEBT", "check"], [len(set(v for v in REV if v is not None))], "")
if HOW == "each_value" and SPLITCOL in rows[0]:     # the split category (a column the 28 Sep book did not have;
    nv = len({r[SPLITCOL] for r in rows if r[SPLITCOL] != ""})   # ORIG_YEAR is no column of the file's)
    put(["columns", SPLITCOL, "why"], [nv], "")
    put(["columns", SPLITCOL, "check"], [nv], "")

# ------------------------------------------------------------------ Look
def looks_like_code(vals):
    """The Look tab's red bar, from its own words (Look, "The red bar"; statistics.md): one value held by 1% of the
    loans or more that sits outside the rest by half their spread or more, such as -9999 among scores of 500-850."""
    nums = [v for v in vals if v is not None]
    value, k = collections.Counter(nums).most_common(1)[0]
    rest = [v for v in nums if v != value]
    if not rest or k < 0.01 * len(nums):
        return None
    span = (max(rest) - min(rest)) or abs(max(rest)) or 1.0
    return value if value < min(rest) - 0.5 * span or value > max(rest) + 0.5 * span else None


def look_stats(name, vals, raw, code=None, missing=()):
    """`missing`: values the analyst answered Missing on Columns (the walk answers FICO's -9999 so). On this build
    Look leaves them out of everything and counts them on a row of their own (change 4, 29 Sep 2026)."""
    marked = sum(1 for v in vals if v is not None and v in missing)
    vals = [None if v is not None and v in missing else v for v in vals]
    real = [v for v in vals if v is not None and v != code]
    blank = sum(1 for r in raw if r == "")
    notnum = sum(1 for r in raw if r != "" and number(r) is None)
    put(["look", name, "Loans", 3], len(raw), "")
    put(["look", name, "Blank", 3], blank, "")
    put(["look", name, "Blank", 4], blank / len(raw), "")
    put(["look", name, "Not a number", 3], notnum, "")
    put(["look", name, "Not a number", 4], notnum / len(raw), "")
    if code is None:
        put(["look", name, "Likely a code", 3], "none found" if looks_like_code(vals) is None else "a code",
            "no value on 1% of loans or more sits half the spread or further outside the rest")
    if code is not None:
        at = sum(1 for v in vals if v == code)
        put(["look", name, f"At {code:.0f}, likely a code", 3], at, "")
        put(["look", name, f"At {code:.0f}, likely a code", 4], at / len(raw), "")
    if marked:
        put(["look", name, "Answered missing, left out", 3], marked, "the analyst answered these Missing on Columns")
        put(["look", name, "Answered missing, left out", 4], marked / len(raw), "")
    put(["look", name, "Smallest", 3], min(real), "")
    put(["look", name, "Median", 3], statistics.median(real), "")
    put(["look", name, "Mean", 3], statistics.fmean(real), "")
    put(["look", name, "Largest", 3], max(real), "")
    # 30 Sep 2026: P10 to P90, PERCENTILE.INC (Look's words: "the 10th, 25th, 50th, 75th and 90th percentile"),
    # numpy's "linear", which is the same definition, over the values Look draws (answered missing and a code left out)
    for p_, lab in zip(PCTS, PCT_LABELS):
        put(["look", name, lab, 3], float(np.percentile(np.array(real, dtype=float), p_)),
            "PERCENTILE.INC, numpy's linear, answered-missing values left out",
            plant=float(np.percentile(np.array(real, dtype=float), p_, method="weibull")))
    return real


PCTS = (10, 25, 50, 75, 90)
PCT_LABELS = ("10th percentile (P10)", "25th percentile (P25)", "50th percentile (P50), the median",
              "75th percentile (P75)", "90th percentile (P90)")


def text_fmt(v, fmt):
    """TEXT(v, fmt) for Look's formats: "#,##0", "#,##0.0", "0.00", "0.000" (a half rounded away from zero)."""
    places = {"#,##0": 0, "#,##0.0": 1, "0.00": 2, "0.000": 3}[fmt]
    d = Decimal(f"{float(v):.15g}").quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return f"{d:,}" if fmt.startswith("#,") else str(d)


def general(v):
    """A number joined to text in Excel or LibreOffice: its General form, no trailing zeros."""
    s = f"{float(v):.10g}"
    return s[:-2] if s.endswith(".0") else s


def short_label(x, step, fmt):
    """Look's words for the labels under the bars: 24k for 24,000, 1.2M for 1,200,000, with the decimals the step
    between two labels needs to tell them apart; under 1,000 the column's own format."""
    def unit(size, suffix):
        places = max(0, 1 - math.floor(math.log10(step / size)))
        d = Decimal(f"{float(x) / size:.15g}").quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        return general(float(d)) + suffix
    if abs(x) >= 1_000_000:
        return unit(1_000_000, "M")
    if abs(x) >= 1000:
        return unit(1000, "k")
    return text_fmt(x, fmt)


def look_format(vals):
    """Look's number format for a column (the tab's rule: whole numbers as #,##0; else by size)."""
    v = sorted(vals)
    if all(float(x).is_integer() for x in v):
        return "#,##0"
    big = max(abs(v[0]), abs(v[-1]), abs(statistics.median(v)))
    return "#,##0" if big >= 100 else "#,##0.0" if big >= 10 else "0.00" if big >= 1 else "0.000"


def look_lines(name, real, lo, hi, bars):
    """Each bar's short label, and the five grey lines' places on the chart: the chart's 120 slots, 10 for the low
    end, 100 for the bars, 10 for the high; a value v sits at 10 + 0.5 + 100 (v - From) / (To - From), and a
    percentile outside From..To has no line."""
    w, step, fmt = (hi - lo) / bars, (hi - lo) / 5, look_format(real)
    for i in range(bars):
        a = lo + i * w
        put(["look-label", name, float(a)], short_label(a, step, fmt), f"the bar's start, step {step:g}, {fmt}",
            plant=f"{a / 1000:.1f}k" if abs(a) >= 1000 else f"{a:.1f}")
    for k, p_ in enumerate(PCTS):
        pv = float(np.percentile(np.array(real, dtype=float), p_))
        put(["look-pline", name, k], 10 + 0.5 + 100 * (pv - lo) / (hi - lo) if lo <= pv <= hi else None,
            f"P{p_} = {pv:g} placed on the chart",
            plant=100 * (pv - lo) / (hi - lo) if lo <= pv <= hi else 50.0)


real = {"FICO": look_stats("FICO", FICO, [r["FICO"] for r in rows], missing={-9999.0}),
        "ORIG_BAL": look_stats("ORIG_BAL", BAL, [r["ORIG_BAL"] for r in rows]),
        "REV_DEBT": look_stats("REV_DEBT", REV, [r["REV_DEBT"] for r in rows])}
LOOK_RANGE = {"FICO": (550, 850, 20), "ORIG_BAL": (0, 60000, 20), "REV_DEBT": (0, 30000, 20)}   # Look!C20:C22 ...
for name, (lo, hi, bars) in LOOK_RANGE.items():
    w = (hi - lo) / bars
    v = np.array(real[name])
    for i in range(bars):
        a = lo + i * w
        last = i == bars - 1
        cnt = int(((v >= a) & ((v <= a + w) if last else (v < a + w))).sum())
        put(["look-bar", name, float(a), float(w), last], cnt, "loans from the bar's start to its end")
    put(["look-end", name, "low end"], int((v < lo).sum()), "")
    put(["look-end", name, "high end"], int((v > hi).sum()), "")
    look_lines(name, real[name], lo, hi, bars)
    # FICO's -9999 is answered missing, so no longer a code with a bar of its own (change 4)
both = [(r, f) for r, f in zip(REV, FICO) if r is not None and f is not None and f != -9999]
put(["look", "REV_DEBT against FICO", "Loans with both values", 3], len(both), "")
put(["look", "REV_DEBT against FICO", "Dots shown", 3], min(2000, len(both)), "every pair, at most 2,000")
put(["look", "REV_DEBT against FICO", "Moves together (correlation)", 3],
    float(np.corrcoef(*zip(*both))[0, 1]), "Pearson over every loan with both")
both2 = [(r, b) for r, b in zip(REV, BAL) if r is not None and b is not None]
put(["look", "REV_DEBT against ORIG_BAL", "Loans with both values", 3], len(both2), "")
put(["look", "REV_DEBT against ORIG_BAL", "Dots shown", 3], min(2000, len(both2)), "every pair, at most 2,000")
put(["look", "REV_DEBT against ORIG_BAL", "Moves together (correlation)", 3],
    float(np.corrcoef(*zip(*both2))[0, 1]), "")
CORR = {"FICO": float(np.corrcoef(*zip(*both))[0, 1]), "ORIG_BAL": float(np.corrcoef(*zip(*both2))[0, 1])}
# the dots drawn: each a real loan's pair, none answered missing (change 4), as many as the tab says it shows
put(["look-dots", "REV_DEBT against FICO"], {"pairs": sorted((f, r) for r, f in both), "shown": min(2000, len(both))})
put(["look-dots", "REV_DEBT against ORIG_BAL"], {"pairs": sorted((b, r) for r, b in both2),
                                                "shown": min(2000, len(both2))})

# ------------------------------------------------------------------ Record
dates = [date.fromisoformat(r["ORIG_DATE"]) for r in rows if r["ORIG_DATE"]]
put(["record", "C11"], [N], "")
put(["record", "C15"], [min(dates).year, min(dates).month, min(dates).day, max(dates).year, max(dates).month,
                        max(dates).day, N, N - len(dates)], "every loan, and those without a readable date")
put(["record", "C16"], [round(e) for e in EDGES["FICO"]] + [len(EDGES["FICO"]) + 1], "")
put(["record", "C17"], [round(e) for e in EDGES["ORIG_BAL"]] + [len(EDGES["ORIG_BAL"]) + 1], "")
put(["record", "C19"], [sum(len(GRID_CELLS[g[0]][2]) for g in GRIDS[4:])], "")
put(["record", "C20"], [round(CORR["FICO"], 2)], "")
put(["record", "C21"], [round(CORR["ORIG_BAL"], 2)], "")
for r_, m in zip(range(26, 31), MEASURES):
    ss = [P[(g[0], m, k)] for g, k in two]
    put(["record", f"C{r_}"], [sum(s["flag"] == "worse" for s in ss), n_two,
                               sum(s["flag"] == "worse" and s["material"] == "Yes" for s in ss)], "")
# build 44734da4: Record's "Grids filter" line -- each value of the Filter by column and its loans, in the tabs' order
if FILTERCOL:
    got_ = []
    for v in FVALUES:
        got_ += [float(x) for x in re.findall(r"\d+", v)] + [sum(1 for x in FVALUE if x == v)]
    put(["record", "C", "Grids filter", 0], got_, "each value of the Filter by column, and its loans")
# 30 Sep 2026: how many two-way pockets have a borderline verdict, and how many of those on Worse? (dollar rates only:
# nothing else is shuffled)
for m in DOLLAR:
    ss = [(g, k, P[(g[0], m, k)]) for g, k in two]
    put(["record", "F", f"Borderline now: {m}", 0], [sum(1 for _, _, s in ss if s["bl"]), n_two,
                                                     sum(1 for _, _, s in ss if s["wbl"])],
        "B2a from this road's p-values and their setters' SEs",
        members=[border_extra(g[0], m, k)["border"] for g, k, _ in ss])


def two_prop_needed(gap):
    n, rate = BOOK["Bad loans"][2], BAD_RATE
    lo, hi = 1, n // 2
    while lo < hi:
        mid = (lo + hi) // 2
        if power_2p(gap * rate, mid, rate, n - mid) >= POWER:
            hi = mid
        else:
            lo = mid + 1
    return lo


def ratio_needed(m, gap):
    r, sd, xb = SPREAD[m]
    return math.ceil(((Z + ZP * math.sqrt(gap)) * sd / (xb * (gap - 1) * r)) ** 2)


put(["record", "C31"], [two_prop_needed(WORSE_AT)], "")
put(["record", "C32"], [ratio_needed("Bad dollars", WORSE_AT)], "")
put(["record", "C33"], [ratio_needed("Charge-offs", WORSE_AT)], "")
for r_, m in ((34, "Kept after losses"), (35, "Earned before losses")):
    gaps = [diff_gap(P[(g[0], m, k)]["n"], m) for g, k in two]
    put(["record", f"C{r_}"], [statistics.median([x for x in gaps if x is not None]) * 100, 80, 95], "")
put(["record", "C36"], [LINE["Bad loans"]], "")
put(["record", "C37"], [LINE["Bad dollars"]], "")
put(["record", "C38"], [LINE["Charge-offs"]], "")
put(["record", "C39"], [GCO_LINE], "")
put(["record", "C40"], [GCO_LINE], "")
put(["record", "C41"], [MIN_LOANS, 5, BAD_RATE * 100, WORSE_AT], "")
put(["record", "C42"], [BETTER_AT], "")
put(["record", "C43"], [sum(P[(g[0], "Bad loans", k)]["ev"] >= MIN_EVENTS for g, k in two), n_two], "")
bad_total = int(BOOK["Bad loans"][0])
put(["record", "C44"], [bad_total // 5, 5], "")
put(["record", "C45"], [bad_total, bad_total, 5, bad_total // 5], "")
for g in GRIDS:
    cells = GRID_CELLS[g[0]][2]
    testable = [k for k in cells if P[(g[0], "Bad loans", k)]["ev"] >= MIN_EVENTS]
    loans_t = sum(len(cells[k]) for k in testable)
    bk_all = sum(BAL[j] or 0.0 for k in cells for j in cells[k])
    bk_t = sum(BAL[j] or 0.0 for k in testable for j in cells[k])
    lab = f"Pockets: Split: {g[0]}" if g[3] else f"Pockets: {g[0]}"
    put(["record", "C", lab, 0], [len(cells), bad_total // 5, len(testable), MIN_EVENTS, round(100 * loans_t / N)], "")
    put(["record", "C", lab, 1], [round(100 * bk_t / bk_all)], "")
put(["record", "C63"], [sum(len(GRID_CELLS[g[0]][2]) for g in GRIDS), len(GRIDS), MIN_EVENTS], "")
left = {m: Counter() for m in MEASURES}
for r in rows:
    fl_bad = r["BAD_FLAG"] not in ("0", "1")
    bal_blank = r["ORIG_BAL"] == ""
    gco_bad = number(r["GCO_AMT"]) is None
    ranr_bad = number(r["RANR_AMT"]) is None
    if fl_bad:
        left["Bad loans"]["flag"] += 1
    if fl_bad or bal_blank:
        left["Bad dollars"]["bal" if bal_blank and not fl_bad else "flag" if fl_bad and not bal_blank else "both"] += 1
    if gco_bad or bal_blank:
        left["Charge-offs"]["gco" if gco_bad else "bal"] += 1
    if ranr_bad or bal_blank:
        left["Kept after losses"]["ranr" if ranr_bad else "bal"] += 1
    if ranr_bad or gco_bad or bal_blank:
        left["Earned before losses"]["gco" if gco_bad else "ranr" if ranr_bad else "bal"] += 1
put(["record", "C68"], [left["Bad loans"]["flag"], 0, 1], "")
put(["record", "C69"], [left["Bad dollars"]["bal"], left["Bad dollars"]["flag"], 0, 1], "")
put(["record", "C70"], [left["Charge-offs"]["gco"], left["Charge-offs"]["bal"]], "")
put(["record", "C71"], [left["Kept after losses"]["bal"]], "")
put(["record", "C72"], [left["Earned before losses"]["gco"], left["Earned before losses"]["bal"]], "")
put(["record", "C73"], [sum(1 for g in GRIDS for k in GRID_CELLS[g[0]][2]
                            if P[(g[0], "Bad loans", k)]["alone"])], "")
put(["record", "F68"], [N], "")
put(["record", "F25"], [MIN_LOANS], "the fewest loans for the usual test, worked out above")

# the two examples Record!F39:F41 quotes, for Kept after losses
# 30 Sep 2026: chosen by Record's own words -- "this run's own pockets as the examples": of the two-way pockets with a
# Kept reading, the one with the most dollars at stake whose gap is significant, and the one whose gap is not (on 29 Sep
# they were named here from the Q3 book; the Grey book's Kiosk pocket moves the second)
best_ = {}
for g in GRIDS[:4]:
    for k in GRID_CELLS[g[0]][2]:
        s_ = P[(g[0], "Kept after losses", k)]
        if s_["dollars"] is None or s_["flag"] in (None, "few"):
            continue
        sig_ = s_["flag"] in ("worse", "better")
        if sig_ not in best_ or abs(s_["dollars"]) > best_[sig_][0]:
            best_[sig_] = (abs(s_["dollars"]), g, k, s_)


def nums_of(label):
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", label)]


_, g1, k1, ex1 = best_[True]
put(["record", "F39"], nums_of(k1[0]) + nums_of(k1[1]) + [abs(ex1["gap"])],
    f"the significant example: {g1[0]} {k1}, the most dollars at stake")
put(["record", "F40"], [abs(ex1["dollars"])], "")
_, g2, k2, ex2 = best_[False]
put(["record", "F41"], nums_of(k2[0]) + nums_of(k2[1]) + [ex2["gap"]],
    f"the example not significant: {g2[0]} {k2}, the most dollars at stake")

# tests and families (Record!F43)
n_tests = 0
for g in GRIDS:
    for m in MEASURES:
        for k in GRID_CELLS[g[0]][2]:
            s = P[(g[0], m, k)]
            n_tests += (s["p_band"] is not None) + (s["p_book"] is not None)
for (name, m), (out, per) in SPLIT_RESULTS.items():
    n_tests += sum(1 for v in per.values() if v[1] is not None)
# a family is one grid, one rate and one comparison: vs band and vs book on the two-way and three-way grids, and one
# for the split (the halves; or every value together, for a category) -- counted where it holds a test
FAMILIES = 4 * 5 * 2 + 4 * 5 * 2 + sum(1 for g in GRIDS[:4] for m in MEASURES if any(
    v[1] is not None for (nm, mm), (out, per) in SPLIT_RESULTS.items() if mm == m and nm.startswith(g[0] + " ·")
    or (nm == g[0] and mm == m) for v in per.values()))
put(["record", "F43"], [FAMILIES, n_tests, 4, 5, 2, 4, 5, 2], "")
put(["record", "F", "Families of tests", 1], [4, 5], "the split's families, the line's second half")
put(["record", "F", "Reading a single red", 0], [FAMILIES], "how many families, again")


# ------------------------------------------------------------------ Grids: what one cell says (change 2)
# The words are the tab's own, transcribed (they are the firm's fixed sentences, the same every Run: Grids' _choices
# lists and the note under the blocks); every number and every choice between them is worked out here from this
# road's own grid figures above -- the rate, the two gaps, the loans, the row's loans in all, which other pockets of
# the row have loans, and the heat scale's steps (Grids!C7 in words: 2x and over the deepest red, 0.5x and under the
# greenest; the steps between, 1.5x and 1.2x, are read from results.HEAT_STEPS, as the full tie-out read the code
# where the words stop)
from decimal import Decimal, ROUND_HALF_UP  # noqa: E402

KIND = {"Bad loans": "x", "Bad dollars": "x", "Charge-offs": "x", "Kept after losses": "pts",
        "Earned before losses": "pts"}
SAY_RATE = {"Bad loans": "{these}: {r} went bad.",
            "Bad dollars": "{these}: {r} of {their} booked dollars were in loans that went bad.",
            "Charge-offs": "{these} charged off {r} of {their} booked dollars.",
            "Kept after losses": "{these} kept {r} of {their} booked dollars after losses.",
            "Earned before losses": "{these} earned {r} of {their} booked dollars before losses."}
SAY_GAP = {"Bad loans": "{x}× the bad-loan rate of {against}.",
           "Bad dollars": "{x}× the bad-dollar rate of {against}.",
           "Charge-offs": "{x}× the charge-off rate of {against}.",
           "Kept after losses": "Kept {pts} points {more} of their booked dollars than {against}.",
           "Earned before losses": "Earned {pts} points {more} of their booked dollars than {against}."}
STEPS = ((1.0, "deep red"), (0.585, "red"), (0.263, "light red"), (-0.585, "green"), (-0.263, "light green"))


def text2(v):
    """TEXT(v, "0.00"): two places, a half rounded away from zero, as Excel and LibreOffice do."""
    return str(Decimal(repr(float(v))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def pct2(v):
    return str((Decimal(repr(float(v))) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) + "%"


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def ev(key):
    got = E.get(json.dumps(key))
    return num(got["value"]) if got else None


def panel(gkey, m, R, C):
    """The six lines of What one cell says, worked out from this road's grid figures (GV: the view, whole or on only
    the loans with one value). 30 Sep 2026: a cell under the fewest loans says it is grey; Loan size has its own two
    sentences and no colour; the name says which loans."""
    V = GV[gkey]
    bands, cols, cells = V["bands"], V["cols"], V["cells"]
    labels = ("name", "Rate", "vs the book", "vs rest of band", "Loans", "The colour")
    if R not in bands or C not in cols:
        return dict(zip(labels, ["Pick a Row and a Column above: their lists follow the Grid.", "", "", "", "", ""]))
    where = f", only loans where {FILTERCOL} is {gkey.split(' | where ')[1]}" if " | where " in gkey else ""
    out = {"name": f"{R} · {C}, {m}{where}"}
    cell = cells.get((R, C))
    if cell is None:
        return {**out, "Rate": "No loans in this pocket.", "vs the book": "", "vs rest of band": "", "Loans": "",
                "The colour": ""}
    LV = cell["loans"]
    x = cell[m]
    RV, BV, NV = x["rate"], x["book"], x["band"]
    MV = cells[(R, "All")]["loans"]
    others = [c for c in cols if c != C and (R, c) in cells]
    one = LV == 1
    these = "This one loan" if one else f"These {LV:,} loans"
    their = "its" if one else "their"
    kind = "size" if m == SIZE_M else KIND[m]
    few = f"Blank: fewer losses than the minimum ({MIN_EVENTS} losses), so not compared."
    blank = "Blank: not compared." if kind in ("pts", "size") else few

    def gap(v, against):
        if kind == "size":
            return f"{text2(v)}× the average loan of {against}."
        if kind == "pts":
            return SAY_GAP[m].format(pts=text2(abs(v)), more="less" if v < 0 else "more", against=against)
        return SAY_GAP[m].format(x=text2(v), against=against)
    if RV is None:
        out["Rate"] = "No rate: these loans have nothing to divide by for this measure."
    elif kind == "size":
        out["Rate"] = f"{these} averaged {dollars0(RV)} booked, median {dollars0(x['median'])}."
    else:
        out["Rate"] = SAY_RATE[m].format(these=these, their=their, r=pct2(RV))
    out["vs the book"] = gap(BV, "the whole book") if BV is not None else blank
    against = f"the other loans in {R}" + (f" (the {', '.join(others)} loans)" if 1 <= len(others) <= 3 else "")
    out["vs rest of band"] = gap(NV, against) if NV is not None else (
        f"Blank: alone in its band. Nothing else in {R} to compare with." if not others else blank)
    out["Loans"] = f"{LV:,} loan{'' if one else 's'}; {R} has {MV:,.0f} in all."
    bound = ev(["grid-bound", gkey, m])

    def shade(v):
        if v is None:
            return "blank"
        t = -v / bound if kind == "pts" else (math.log2(v) if v > 0 else 0.0)
        for lim, word in STEPS:
            if (t >= lim if lim > 0 else t <= lim):
                return word
        return "pale"
    if cell["thin"]:
        out["The colour"] = (f"Grey: only {LV:,} loan{'' if one else 's'}, fewer than the {MIN_LOANS:,} set on "
                             f"Control, so not coloured.")
        # a plant for mutate.py: the heat's sentence, as if the cell weren't grey
        out["_plant"] = (f"vs the book is {shade(BV)}, vs rest of band {shade(NV)}. Red is worse, green better, "
                         f"deeper a bigger gap. It is the size of the gap, not a test.")
    elif kind == "size":
        out["The colour"] = ("No red or green: loan size is a description, not a finding. Shaded darker the bigger "
                             "the loans are against the book's.")
    else:
        out["The colour"] = (f"vs the book is {shade(BV)}, vs rest of band {shade(NV)}. Red is worse, green better, "
                             f"deeper a bigger gap. It is the size of the gap, not a test.")
    return out


# ------------------------------------------------------------------ Grids, 30 Sep 2026: grey, the bound, the heading,
# "Only loans where", Loan size
# Grids!C7 in words: a pocket with fewer loans than "Fewest loans in a pocket" on Control (the Run's 65, worked out
# above as Record!C41 says) is grey, not coloured, and left out of the largest gap the heat is read against. The
# heading of vs the book gives the whole book's own figure. "Only loans where" (Grids' note): the grid on only the
# loans with one value; "vs the book is still against the whole book; vs rest of band, the rest of the band among
# those loans". Loan size (the note under Rate): booked dollars per loan, the average; against the book's average and
# the rest of the band's as a multiple; a loan with no readable booked amount is left out of it.
SIZE_M = "Loan size"
SZ_OK = np.array([b is not None for b in BAL])
SZ_V = np.array([b if b is not None else 0.0 for b in BAL])
BOOK_AVG = math.fsum(b for b in BAL if b is not None) / int(SZ_OK.sum())
GV = {}                  # view key -> {"bands", "cols", "cells": {(row, col): {...}}}


def dollars0(v):
    """TEXT(v, "$#,##0")."""
    return "$" + f"{int(Decimal(repr(float(v))).quantize(Decimal('1'), rounding=ROUND_HALF_UP)):,}"


def size_of(idx):
    i = idx[SZ_OK[idx]]
    if not len(i):
        return None
    vals = [float(SZ_V[j]) for j in i]
    return {"loans": len(i), "booked": math.fsum(vals), "median": statistics.median(vals)}


def grid_view(g, gkey, keep=None):
    """One view of a grid: every cell of its four blocks (and Loan size's), from the loans in `keep` (all when None)."""
    name, bcol, dcol, three = g
    bands, dims, idx_all = GRID_CELLS[name]
    colname = (lambda d: f"{d[0]} · {d[1]}" if d != "All" else "All") if three else (lambda d: d)
    idx_of = {}
    for k, v in idx_all.items():
        v = v[keep[v]] if keep is not None else v
        if len(v):
            idx_of[k] = v
    cells = {}
    for b in bands + ["All"]:
        for d in dims + ["All"]:
            ks = [k for k in idx_of if (b == "All" or k[0] == b) and (d == "All" or k[1] == d)]
            if ks:
                cells[(b, colname(d))] = {"idx": np.concatenate([idx_of[k] for k in ks]), "b": b, "d": d}
    for cell in cells.values():
        cell["loans"] = len(cell["idx"])
        cell["thin"] = cell["loans"] < MIN_LOANS
        cell["size"] = size_of(cell["idx"])
    for (b, c), cell in cells.items():
        for m in MEASURES:
            s = sums(cell["idx"], m)
            r = rate_of(s)
            few = m not in PROFIT and s["ev"] < MIN_EVENTS and (b, c) != ("All", "All")
            vt = gap_of(r, RATE[m], m)
            nv = None
            if b != "All" and c != "All":
                rb = minus(sums(cells[(b, "All")]["idx"], m), s)
                nv = gap_of(r, rate_of(rb) if rb["sx"] else None, m)
            cell[m] = {"rate": r, "book": None if few else vt, "band": None if few else nv}
        sz = cell["size"]
        avg = sz["booked"] / sz["loans"] if sz else None
        bv = avg / BOOK_AVG if avg is not None else None
        nv = None
        row = cells[(b, "All")]["size"] if b != "All" else None
        if sz and b != "All" and c != "All" and row is not None and row["loans"] > sz["loans"]:
            nv = avg / ((row["booked"] - sz["booked"]) / (row["loans"] - sz["loans"]))
        cell[SIZE_M] = {"rate": avg, "book": bv, "band": nv, "median": sz["median"] if sz else None}
    cols_ = [colname(d) for d in dims]
    if three:
        # a split grid lists every segment with every part (Grids' two-row header: each segment over all its
        # parts), so a Column can name a part no loan of that segment has -- the Grey book's Kiosk has only a low
        # half, each of its pockets being one loan -- and its pocket then has no loans
        segs_ = list(dict.fromkeys(d[0] for d in dims))
        parts_ = list(dict.fromkeys(d[1] for d in sorted(dims, key=lambda d: repr(d[1]))))
        cols_ = [f"{s_} · {p_}" for s_ in segs_ for p_ in parts_]
    GV[gkey] = {"bands": bands, "cols": cols_, "cells": cells, "grid": name}
    return cells


def put_view(g, gkey, cells, whole):
    """Put a view's figures: every block when `whole` is False (a filtered view), and for every view the grey, the
    bound, the heading, the book's figure, the fewest loans and Loan size."""
    for (b, c), cell in cells.items():
        if not whole:
            put(["grid", gkey, "*", "loans", b, c], cell["loans"], "loans in the cell, among these loans")
        for m in list(MEASURES) + [SIZE_M]:
            x = cell[m]
            if whole and m != SIZE_M:
                continue
            # plants (mutate.py, semantic): what a plausible wrong method would show -- Loan size with a loan whose
            # booked amount is unreadable counted as $0; vs the book against the value's own loans' rate
            own = cells[("All", "All")][m]["rate"]
            if x["rate"] is not None:
                wrong = (cell["size"]["booked"] / cell["loans"] if m == SIZE_M and cell["size"]
                         and cell["size"]["loans"] < cell["loans"] else None)
                put(["grid", gkey, m, "rate", b, c], x["rate"],
                    "average booked per loan (readable booked only)" if m == SIZE_M else
                    "rate = sum y / sum x, among these loans", **({"plant": wrong} if wrong is not None else {}))
            for blk, how in (("book", "against the WHOLE book's"), ("band", "against the rest of its band, among "
                                                                            "these loans")):
                if x[blk] is not None:
                    wrong = None
                    if blk == "book" and not whole and m != SIZE_M and x["rate"] is not None:
                        wrong = gap_of(x["rate"], own, m)
                    put(["grid", gkey, m, blk, b, c], x[blk], how,
                        **({"plant": wrong} if wrong is not None and wrong != x[blk] else {}))
            if m == SIZE_M and x["median"] is not None:
                put(["size-median", gkey, b, c], x["median"], "median booked per loan")
    for m in list(MEASURES) + [SIZE_M]:
        for (b, c), cell in cells.items():
            for blk in ("book", "band"):
                v = cell[m][blk]
                if v is not None:
                    put(["grid-grey", gkey, m, blk, b, c], cell["thin"],
                        f"{cell['loans']} loans against the fewest, {MIN_LOANS}", plant=not cell["thin"])
        got = [abs(cell[m][blk]) for cell in cells.values() if not cell["thin"] for blk in ("book", "band")
               if cell[m][blk] is not None]
        every = [abs(cell[m][blk]) for cell in cells.values() for blk in ("book", "band") if cell[m][blk] is not None]
        put(["grid-bound", gkey, m], 1 if m == SIZE_M else max(got + [0.01]),
            "no heat scale" if m == SIZE_M else "largest gap over the cells not grey",
            **({"plant": max(every + [0.01])} if m != SIZE_M and max(every + [0.01]) != max(got + [0.01]) else {}))
        put(["grid-few", gkey, m], MIN_LOANS, "Fewest loans in a pocket, worked out (Record!C41)")
        fig = BOOK_AVG if m == SIZE_M else RATE[m]
        put(["grid-bookfig", gkey, m], fig, "the whole book's own figure")
        own = cells[("All", "All")][m]["rate"]
        put(["grid-head", gkey, m], f"vs the book (book: {dollars0(fig) if m == SIZE_M else pct2(fig)})",
            "the heading, with the whole book's figure",
            **({"plant": f"vs the book (book: {dollars0(own) if m == SIZE_M else pct2(own)})"}
               if not whole and own is not None else {}))


for g in GRIDS:
    put_view(g, g[0], grid_view(g, g[0]), True)
    for v in FVALUES:                        # Filter by's values (build 44734da4: not the split's)
        keep = np.array([x == v for x in FVALUE])
        if True:
            gk = f"{g[0]} | where {v}"
            put_view(g, gk, grid_view(g, gk, keep), False)


# build 44734da4: a whole-number column's band label holds exactly the loans in its band. For each band label the
# workbook shows (read_book.py: the band's loans in the Loans block's All column), the loans whose value lies inside
# the label's range, counted from the file; this road's band, by the edges, must hold the same loans, its smallest and
# largest value inside the label. A plant: the label as the build before named it (the band below an edge of 654.2
# ending at 653), which leaves the 654s out
COLV = {"FICO": FICO, "ORIG_BAL": BAL}


def label_range(lab):
    m = re.fullmatch(r"([\d,.-]+) - ([\d,.-]+)", str(lab))
    return (float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))) if m else None


for f in FIGS:
    k = f["key"]
    if k[0] == "band-label" and k[1] in COLV:
        col, lab = k[1], k[2]
        rng_ = label_range(lab)
        why_ = FICO_WHY if col == "FICO" else BAL_WHY
        vals = [v for v, w in zip(COLV[col], why_) if w is None]
        if rng_ is None:                               # a band of its own: "(blank)", "(marked missing)"
            put(k, sum(1 for w in why_ if w == lab), f"loans whose {col} is {lab}")
            continue
        if not all(float(v).is_integer() for v in vals):
            # a column with cents: a label names whole dollars, so its band runs to just short of the next start
            a, b = rng_
            put(k, sum(1 for v in vals if a <= v < b + 1), f"loans of {col} from {a:g} to just under {b + 1:g}")
            continue
        a, b = rng_
        inside = [v for v in vals if a <= v <= b]
        mine = [v for v, bb in zip(COLV[col], BAND[col]) if bb == lab]
        old = labels_of(EDGES[col], min(vals), max(vals), False)
        oldr = label_range(old[LABELS[col].index(lab)]) if lab in LABELS[col] else None
        put(k, len(inside), f"loans of {col} from {a:g} to {b:g}: {len(inside)}; this road's band by the edges: "
                            f"{len(mine)}, {min(mine) if mine else '-'} to {max(mine) if mine else '-'}",
            **({"plant": sum(1 for v in vals if oldr[0] <= v <= oldr[1])} if oldr and oldr != rng_ else {}))
        if len(inside) != len(mine) or (mine and not (a <= min(mine) and max(mine) <= b)):
            print("band label does not hold its band:", col, lab, len(inside), len(mine))


done = {}
for f in FIGS:
    k = f["key"]
    if k[0] == "panel":
        _, grid, m, R, C, lab = k
        if (grid, m, R, C) not in done:
            done[(grid, m, R, C)] = panel(grid, m, R, C)
        got_ = done[(grid, m, R, C)]
        put(k, got_[lab], "the tab's words, with this road's own numbers in them",
            **({"plant": got_["_plant"]} if lab == "The colour" and "_plant" in got_ else {}))

# ------------------------------------------------------------------ Paid, cost, kept: the chart (change 3)
# Each dot is its row's cost multiple (across) and kept gap (up); red when its Together verdict is Net drain, green
# when Strong or Priced for it (the line above the chart says so), the verdict being this road's own (above). A dot is
# numbered, 1 to 8, when its row is among the first eight and has a verdict; "Numbered on the chart" names the row that
# carries each number. The row's place is the tab's (its order was not re-derived, as on 28 Sep).
dots = {}
for f in FIGS:
    k = f["key"]
    if k[0] == "pck-dot":
        _, grid, band, seg, what = k
        who = ["pck", grid, band, seg]
        x, y = ev(who + ["gco-multiple"]), ev(who + ["kept-gap"])
        # a pocket with too few losses to test its charge-offs has no verdict and no dot (the tab's rows with a
        # side untested come last and are not drawn)
        if P[(grid, "Charge-offs", (band, seg))]["flag"] == "few":
            x = y = None
        # the word alone: the borderline words after it leave the colour the word's (Paid, cost, kept's rule)
        tog = ((E.get(json.dumps(who + ["together"])) or {}).get("value", "") or "").split(" · borderline")[0]
        row = int(re.sub(r"\D", "", f["cell"].split("!")[1].split(":")[0]))
        if what == "x":
            put(k, x, "the row's charge-off multiple")
        elif what == "y":
            put(k, y, "the row's kept gap")
        elif what == "colour":
            put(k, "none" if x is None else "red" if tog == "Net drain" else
                "green" if tog in ("Strong", "Priced for it") else "none", f"its Together verdict here: {tog or 'none'}")
        elif what in ("red-at", "green-at"):
            put(k, [True, True], "the coloured dot sits on the row's own point")
        elif what == "number":
            n = row if tog and row <= 8 else None
            put(k, n, "numbered when among the first eight rows with a verdict")
            if n:
                dots[(grid, n)] = f"{band} / {seg}"
for f in FIGS:
    k = f["key"]
    if k[0] == "pck-listed":
        put(k, dots.get((k[1], k[2]), "(no dot carries this number)"), "the row the chart's number is on")


# every family of pocket p-values, raw and after the allowance, for looking at one side by side with the workbook
FAM = {}
for (gname, m, k), s_ in P.items():
    for att in ("p_band", "p_book"):
        if s_.get(att + "_raw") is not None and s_["tested"]:
            FAM.setdefault(f"{gname}|{m}|{att}", []).append([k[0], k[1] if isinstance(k[1], str) else " / ".join(k[1]),
                                                             s_[att + "_raw"], s_[att]])
json.dump(FAM, open(OUT.replace(".json", "-families.json"), "w"), indent=0, default=float)
json.dump(cache, open(CACHE, "w"))
meta = {"flipped": FLIPPED, "edges": EDGES, "labels": LABELS, "worse_at": WORSE_AT, "better_at": BETTER_AT, "min_loans": MIN_LOANS,
        "shuffles": B, "book": {m: list(v) for m, v in BOOK.items()}, "lines": LINE, "n": N,
        "corr_fico": CORR["FICO"], "corr_bal": CORR["ORIG_BAL"], "ncols": len(rows[0])}
json.dump({"expected": E, "meta": meta}, open(OUT, "w"), indent=0, default=float)
print(len(E), "expected figures;", "worse at", WORSE_AT, "better at", BETTER_AT, "fewest loans", MIN_LOANS)
