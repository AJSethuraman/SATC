"""The independent road, Where the book bleeds: every figure the workbook shows, worked out again from the loan file
alone. No PocketBook code is imported or copied; the rules are the ones the workbook states in words on its own tabs
(each rule below cites the cell that states it), and the statistics are the textbook ones from scipy and statsmodels.

    python3 by_hand_bleed.py "Consumer book Q3.csv" OUT/expected.json [shuffles]

Reads the extract with Python's csv module. Writes one expected value per figure, keyed the way read_bleed.py keys
what it reads, so compare.py can put each pair side by side.

The settings are the ones Control shows for this Run (Control!C15:C29, as answered on the walk): worse at the
suggested line, better at one over it, 95% sure, 1% of the book's charge-offs, the rest of its band, 65 loans for
the usual test, 10 losses, 5 bands of equal loans, 80% power, Benjamini-Hochberg. The two suggested values (1.34 and
0.75) and the 65 are themselves worked out below from the book, as Record!C41 says they are, and those are used.

The shuffle test (10,000 shuffles, Pockets!D8) is re-run here with this script's own random numbers. It cannot and
should not land on the same digits: its p-values are compared within sampling error (compare.py says how).
"""
import csv
import json
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
# Optional: the workbook's own p-values (read_bleed.py's wb-pockets.json). Given, the verdicts of pockets whose
# shuffled p-values sit either side of 5% but within sampling error of each other are taken on the workbook's side,
# and every figure is worked out again from there: compare.py uses that second set only to say which differences
# are sampling and nothing else. The first set, with no file, is the independent road on its own.
FLIPS_FROM = sys.argv[4] if len(sys.argv) > 4 else None
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


def labels_of(edges, lo, hi):
    """Pockets!C21's band names: from the band's first whole number to one short of the next band's."""
    f = lambda x: f"{x:,.0f}"                                          # noqa: E731
    out = [f"{f(math.floor(lo))} - {f(edges[0] - 1)}"]
    out += [f"{f(a)} - {f(b - 1)}" for a, b in zip(edges, edges[1:])]
    out.append(f"{f(edges[-1])} - {f(math.ceil(hi))}")
    return out


def banded(vals, why):
    seen = [v for v, w in zip(vals, why) if w is None]
    e = edges_of(seen)
    lab = labels_of(e, min(seen), max(seen))
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
    for i, (b, d, v) in enumerate(zip(BAND[bcol], DIMS[dcol], REV)):
        if v is not None:
            groups[(b, d)].append(v)
    med = {k: statistics.median(v) for k, v in groups.items()}
    return ["none" if v is None else "high" if v > med[(b, d)] else "low"
            for b, d, v in zip(BAND[bcol], DIMS[dcol], REV)]


GRIDS = []           # (name, band column, dim column, three-way?)
for bcol in ("FICO", "ORIG_BAL"):
    for dcol in ("CHANNEL", "ASSET_CLASS"):
        GRIDS.append((f"{bcol} x {dcol}", bcol, dcol, False))
for bcol in ("FICO", "ORIG_BAL"):
    for dcol in ("CHANNEL", "ASSET_CLASS"):
        GRIDS.append((f"{bcol} x {dcol} / REV_DEBT", bcol, dcol, True))
HALF = {(b, d): halves(b, d) for b in ("FICO", "ORIG_BAL") for d in ("CHANNEL", "ASSET_CLASS")}


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


def put(key, value, how="", **extra):
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
        if " / REV_DEBT " in str(seg):
            d_, h_ = seg.split(" / REV_DEBT ")
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
        tot = {"loans": 0, "booked": 0.0, "High half|loans": 0, "High half|booked": 0.0, "Low half|loans": 0,
               "Low half|booked": 0.0}
        for (b, d), idx in idx_of.items():
            bk = sum(BAL[j] or 0.0 for j in idx)
            hi = [j for j in idx if half[j] == "high"]
            lo = [j for j in idx if half[j] == "low"]
            vals = {"loans": len(idx), "booked": bk, "High half|loans": len(hi),
                    "High half|booked": sum(BAL[j] or 0.0 for j in hi), "Low half|loans": len(lo),
                    "Low half|booked": sum(BAL[j] or 0.0 for j in lo)}
            for w, v in vals.items():
                put(["groups", name, b, d, w], v, "count and booked dollars, by hand")
                tot[w] += v
        for w, v in tot.items():
            put(["groups", name, "Every pocket", "None", w], v, "")
        for w in ("High half|loans", "Low half|loans"):
            put(["groups", name, "Share of the grid", "None", w], tot[w] / tot["loans"], "")
        for w in ("High half|booked", "Low half|booked"):
            put(["groups", name, "Share of the grid", "None", w], tot[w] / tot["booked"], "")

# ------------------------------------------------------------------ Pockets
PARTNER = "FICO"            # the band column REV_DEBT moves with most (Record!C20:C21)
for kind, three in (("Two-way", False), ("Split by REV_DEBT", True)):
    for m in MEASURES:
        cand = []
        for gi, g in enumerate(GRIDS):
            if g[3] != three:
                continue
            held = 0 if (not three or PARTNER in (g[1], g[2])) else 1
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
            put(["pocket", *who, "worse"], s["worse"], "the rule on Pockets!D7")
            if s["p"] is not None:
                att = "p_band" if s["by_band"] else "p_book"
                put(["pocket", *who, "p"], s["p"], "z / exact, or this road's shuffle; then BH",
                    raw=s[att + "_raw"], family=s.get(att + "_family"), shuffled=m in DOLLAR)
            put(["pocket", *who, "material"], s["material"], "dollars at or over the line")
            if s["caught"] is not None:
                put(["pocket", *who, "caught"], s["caught"], "power formula, statistics.md A3")
            if three:
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
        put(who + ["together"], together, "Paid, cost, kept!C9's words")

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


SPLIT_RESULTS = {}
for g in GRIDS[:4]:
    name, bcol, dcol, _ = g
    half = HALF[(bcol, dcol)]
    bands, dims, idx_of = GRID_CELLS[name]
    for m in MEASURES:
        per, strata, O, Ev, V, hden, worse_n = {}, [], 0.0, 0.0, 0.0, 0.0, 0
        for k, idx in idx_of.items():
            sh, sl = half_sums(idx, m, half)
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
            # the high half's total against what it would be at its low half's rate (Split!C6), with the variance
            # of that difference: the high half's own spread about the low half's rate, plus the low half's
            # rate's uncertainty carried on the high half's dollars
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
        if m in PROFIT:
            out["value"] = (O - Ev) / hden * 100
            h = Z * math.sqrt(V) / hden * 100
            out["lo"], out["hi"] = out["value"] - h, out["value"] + h
        else:
            out["value"] = O / Ev
            h = Z * math.sqrt(V) / Ev
            out["lo"], out["hi"] = max(out["value"] - h, 0.0), out["value"] + h
            if m == "Bad loans":
                out["p"] = math.erfc(abs(O - Ev) / math.sqrt(V) / math.sqrt(2))
        if m == "Bad loans":
            out["odds"], out["odds_lo"], out["odds_hi"] = rb_or(strata, Z)
            out["odds_p"] = cmh_p(strata)
            out["steady_p"] = cochran_q_p(strata)
        if m in DOLLAR:
            ck = f"halves|{m}|{name}"
            if ck not in cache:
                a_, b_, _ = shuffle_halves(m, keys_of(g), half, set(per))
                cache[ck] = [{enc(k): v for k, v in a_.items()}, b_]
            pk_p = {dec(k): v for k, v in cache[ck][0].items()}
            pooled_p = cache[ck][1]
            for k in per:
                per[k][1] = pk_p.get(k)
            out["p"] = pooled_p
        ks = list(per)
        raw = [per[k][1] for k in ks]
        adj = bh(raw)
        fam = len([1 for p_ in raw if p_ is not None])
        for k, a, r_ in zip(ks, adj, raw):
            per[k][1] = a
            per[k] += [fam, r_]
        SPLIT_RESULTS[(name, m)] = (out, per)
        put(["split-sum", name, m, "Pockets"], out["pockets"], "")
        put(["split-sum", name, m, "High half worse in"], [out["worse"], out["pockets"]], "")
        put(["split-sum", name, m, "High vs low, all"], out["value"], "")
        put(["split-sum", name, m, "Range"], [out["lo"], out["hi"]], "")
        if "p" in out:
            put(["split-sum", name, m, "p-value"], out["p"], "", raw=out["p"], family=1, shuffled=m in DOLLAR)
        if "odds" in out:
            put(["split-sum", name, m, "As odds"], out["odds"], "")
            put(["split-sum", name, m, "p-value, as odds"], out["odds_p"], "")
        for (b, d), (v, p, fam, r_) in per.items():
            put(["split-pocket", name, m, b, d, "gap"], v, "", p=p, shuffled=m in DOLLAR, raw=r_, family=fam)
            if p is not None:
                put(["split-pocket", name, m, b, d, "p"], p, "", raw=r_, family=fam, shuffled=m in DOLLAR)
    sp = SPLIT_RESULTS[(name, "Bad loans")][0]["steady_p"]
    put(["split-steady", name], "no sign" if sp >= ALPHA else "differs", "Cochran's Q p = %.4f" % sp)
    put(["split-chip", name], [PARTNER in (bcol, dcol)], "")

# ------------------------------------------------------------------ Start here, Control
two = [(g, k) for g in GRIDS[:4] for k in GRID_CELLS[g[0]][2]]
n_two = len(two)
wm = [P[(g[0], "Charge-offs", k)] for g, k in two if P[(g[0], "Charge-offs", k)]["worse"] == "Yes"
      and P[(g[0], "Charge-offs", k)]["material"] == "Yes"]
put(["start-tile", "Pockets worse and material, charge-offs"], [len(wm), n_two], "")
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

# ------------------------------------------------------------------ Look
def look_stats(name, vals, raw, code=None):
    real = [v for v in vals if v is not None and v != code]
    blank = sum(1 for r in raw if r == "")
    notnum = sum(1 for r in raw if r != "" and number(r) is None)
    put(["look", name, "Loans", 3], len(raw), "")
    put(["look", name, "Blank", 3], blank, "")
    put(["look", name, "Blank", 4], blank / len(raw), "")
    put(["look", name, "Not a number", 3], notnum, "")
    put(["look", name, "Not a number", 4], notnum / len(raw), "")
    if code is not None:
        at = sum(1 for v in vals if v == code)
        put(["look", name, f"At {code:.0f}, likely a code", 3], at, "")
        put(["look", name, f"At {code:.0f}, likely a code", 4], at / len(raw), "")
    put(["look", name, "Smallest", 3], min(real), "")
    put(["look", name, "Median", 3], statistics.median(real), "")
    put(["look", name, "Mean", 3], statistics.fmean(real), "")
    put(["look", name, "Largest", 3], max(real), "")
    return real


real = {"FICO": look_stats("FICO", FICO, [r["FICO"] for r in rows], -9999),
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
    if name == "FICO":
        put(["look-end", name, "at the code"], sum(1 for f in FICO if f == -9999), "")
both = [(r, f) for r, f in zip(REV, FICO) if r is not None and f is not None and f != -9999]
put(["look", "REV_DEBT against FICO", "Loans with both values", 3], len(both), "")
put(["look", "REV_DEBT against FICO", "Moves together (correlation)", 3],
    float(np.corrcoef(*zip(*both))[0, 1]), "Pearson over every loan with both")
both2 = [(r, b) for r, b in zip(REV, BAL) if r is not None and b is not None]
put(["look", "REV_DEBT against ORIG_BAL", "Loans with both values", 3], len(both2), "")
put(["look", "REV_DEBT against ORIG_BAL", "Moves together (correlation)", 3],
    float(np.corrcoef(*zip(*both2))[0, 1]), "")
CORR = {"FICO": float(np.corrcoef(*zip(*both))[0, 1]), "ORIG_BAL": float(np.corrcoef(*zip(*both2))[0, 1])}

# ------------------------------------------------------------------ Record
dates = [date.fromisoformat(r["ORIG_DATE"]) for r in rows if r["ORIG_DATE"]]
put(["record", "C11"], [N], "")
put(["record", "C15"], [min(dates).year, min(dates).month, min(dates).day, max(dates).year, max(dates).month,
                        max(dates).day, len(dates), N - len(dates)], "")
put(["record", "C16"], [round(e) for e in EDGES["FICO"]] + [len(EDGES["FICO"]) + 1], "")
put(["record", "C17"], [round(e) for e in EDGES["ORIG_BAL"]] + [len(EDGES["ORIG_BAL"]) + 1], "")
put(["record", "C19"], [sum(len(GRID_CELLS[g[0]][2]) for g in GRIDS[4:])], "")
put(["record", "C20"], [round(CORR["FICO"], 2)], "")
put(["record", "C21"], [round(CORR["ORIG_BAL"], 2)], "")
for r_, m in zip(range(26, 31), MEASURES):
    ss = [P[(g[0], m, k)] for g, k in two]
    put(["record", f"C{r_}"], [sum(s["flag"] == "worse" for s in ss), n_two,
                               sum(s["flag"] == "worse" and s["material"] == "Yes" for s in ss)], "")


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
row = 47
for g in GRIDS:
    cells = GRID_CELLS[g[0]][2]
    testable = [k for k in cells if P[(g[0], "Bad loans", k)]["ev"] >= MIN_EVENTS]
    loans_t = sum(len(cells[k]) for k in testable)
    bk_all = sum(BAL[j] or 0.0 for k in cells for j in cells[k])
    bk_t = sum(BAL[j] or 0.0 for k in testable for j in cells[k])
    put(["record", f"C{row}"], [len(cells), bad_total // 5, len(testable), MIN_EVENTS, round(100 * loans_t / N)], "")
    put(["record", f"C{row + 1}"], [round(100 * bk_t / bk_all)], "")
    row += 2
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
ex1 = P[("FICO x CHANNEL", "Kept after losses", ("496 - 653", "Broker"))]
put(["record", "F39"], [math.floor(min(v for v in FICO if v is not None and v != -9999)),
                        round(EDGES["FICO"][0] - 1), -ex1["gap"]], "")
put(["record", "F40"], [ex1["dollars"]], "")
ob = [k for k in GRID_CELLS["ORIG_BAL x ASSET_CLASS"][2] if k == (LABELS["ORIG_BAL"][3], "4")][0]
ex2 = P[("ORIG_BAL x ASSET_CLASS", "Kept after losses", ob)]
put(["record", "F41"], [round(EDGES["ORIG_BAL"][2]), round(EDGES["ORIG_BAL"][3] - 1), 4, ex2["gap"]], "")

# tests and families (Record!F43)
n_tests = 0
for g in GRIDS:
    for m in MEASURES:
        for k in GRID_CELLS[g[0]][2]:
            s = P[(g[0], m, k)]
            n_tests += (s["p_band"] is not None) + (s["p_book"] is not None)
for (name, m), (out, per) in SPLIT_RESULTS.items():
    n_tests += sum(1 for v in per.values() if v[1] is not None)
put(["record", "F43"], [4 * 5 * 2 + 4 * 5 * 2 + 4 * 5, n_tests, 4, 5, 2, 4, 5, 2], "")

json.dump(cache, open(CACHE, "w"))
meta = {"flipped": FLIPPED, "edges": EDGES, "labels": LABELS, "worse_at": WORSE_AT, "better_at": BETTER_AT, "min_loans": MIN_LOANS,
        "shuffles": B, "book": {m: list(v) for m, v in BOOK.items()}, "lines": LINE, "n": N,
        "corr_fico": CORR["FICO"], "corr_bal": CORR["ORIG_BAL"]}
json.dump({"expected": E, "meta": meta}, open(OUT, "w"), indent=0, default=float)
print(len(E), "expected figures;", "worse at", WORSE_AT, "better at", BETTER_AT, "fewest loans", MIN_LOANS)
