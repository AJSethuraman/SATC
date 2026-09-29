"""The independent road, Test new variables: every figure on the New variables tab (and the Start here, Record,
Control, Columns and Look figures of that Run) worked out again from the loan file alone. No PocketBook code.

    python3 by_hand_scout.py "Scouting book.csv" OUT/expected-scout.json [figures-scout.json]

The rules are the ones the workbook states in words: the cutoff (Control!I30, "the month start nearest 70% of the
loans"), the pre-spec's bins and reference groups (Scouting!B41:B56, the file PocketBook wrote and then confirmed --
its bins are PocketBook's decision, taken here as given, the way the analyst would), the pockets FICO and CHANNEL make
(New variables!C13: FICO at the band edges on Record, which are worked out again here), and the statistics named on
New variables!C5, C9, C10, C16 and C17:

  conditional logistic regression   written out here from its definition: each pocket's likelihood is the chance of
                                    its bad loans falling where they did, given how many there were. With loans in a
                                    few groups that is a ratio of polynomial coefficients, worked in logs with numpy;
                                    its first and second derivatives are the conditional mean and covariance of the
                                    bad-loan counts, so Newton's method needs no numerical differentiation
  the general and trend tests       statistics.md B3 and B4, written out with numpy
  the joint model                   statsmodels' Logit, unconditional, one constant per pocket (New variables!C5)
  Benjamini-Hochberg                statsmodels' multipletests

The Look tab's bars are counted here from the file; the only thing taken from the workbook is where each bar starts
and ends (the chart's own labels), read from figures-scout.json when it is given.
"""
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

import numpy as np
from scipy import stats as st
from scipy.special import gammaln, logsumexp
from statsmodels.stats.multitest import multipletests

X, OUT = sys.argv[1], sys.argv[2]
FIGS = sys.argv[3] if len(sys.argv) > 3 else None
ALPHA, Z = 0.05, st.norm.ppf(0.975)
MAT = 0.01

with open(X, newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))
N = len(rows)


def number(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def when(s):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


FLAG = [int(r["BAD_FLAG"]) if r["BAD_FLAG"] in ("0", "1") else None for r in rows]
DATE = [when(r["ORIG_DATE"]) for r in rows]
GCO = [number(r["GCO_AMT"]) for r in rows]


def income_to_sales(r):
    s, i = number(r["SALES"]), number(r["INCOME"])
    return None if s in (None, 0) or i is None else i / s


VAL = {"UTIL": [number(r["UTIL"]) for r in rows], "income_to_sales": [income_to_sales(r) for r in rows]}
FICO = [None if r["FICO"] == "" or number(r["FICO"]) == -9999 else number(r["FICO"]) for r in rows]
FICO_WHY = ["(blank)" if r["FICO"] == "" else "(marked missing)" if number(r["FICO"]) == -9999 else None
            for r in rows]

E = {}


def put(key, value, how="", **extra):
    E[json.dumps(key)] = {"value": value, "how": how, **extra}


def ymd(d):
    return [d.year, d.month, d.day]


# ------------------------------------------------------------------ the cutoff (Control!I30)
dated = sorted(d for d in DATE if d is not None)
at = dated[max(1, math.ceil(0.7 * len(dated))) - 1]
this = at.replace(day=1)
nxt = (this + timedelta(days=32)).replace(day=1)
CUT = min((this, nxt), key=lambda d: (abs((d - at).days), d))
FIRST, LAST = dated[0], dated[-1]
DEV_END = CUT - timedelta(days=1)
before = sum(1 for d in DATE if d is not None and d < CUT)
after = sum(1 for d in DATE if d is not None and d >= CUT)
DEV = [i for i in sorted(range(N), key=lambda i: (DATE[i] or date.max, i)) if DATE[i] is not None and DATE[i] < CUT]
HOLD = [i for i in range(N) if DATE[i] is not None and DATE[i] >= CUT]
dev_y = [i for i in DEV if FLAG[i] is not None]
hold_y = [i for i in HOLD if FLAG[i] is not None]
put(["control", "F30"], ymd(CUT), "the month start nearest 70% of the loans")
put(["control", "I30"], ymd(CUT) + [before, after], "")

# ------------------------------------------------------------------ the pre-spec's groups (Scouting!B41:B56)
BINS = {"UTIL": [0.9], "income_to_sales": [0.1, 2.0]}
REF = {"UTIL": 0, "income_to_sales": 1}
CANDS = ["UTIL", "income_to_sales"]


def labels(c):
    """The groups as the tab names them: first value to one step short of the next edge (Scouting!F24)."""
    v = [x for x in VAL[c] if x is not None]
    lo, hi = min(v), max(v)
    e = BINS[c]
    for d in range(1, 7):
        step = 10 ** -d
        first = math.floor(lo / step) * step
        if e[0] - step < lo:
            continue
        f = lambda x: f"{x:.{d}f}"                                 # noqa: E731
        out = [f"{f(first)} - {f(e[0] - step)}"] + [f"{f(a)} - {f(b - step)}" for a, b in zip(e, e[1:])]
        out.append(f"{f(e[-1])} - {f(math.ceil(hi / step) * step)}")
        return out


LAB = {c: labels(c) for c in CANDS}


def group(c, i):
    v = VAL[c][i]
    return None if v is None else sum(v >= x for x in BINS[c])


# ------------------------------------------------------------------ the pockets FICO and CHANNEL make (New variables!C13)
fv = np.sort([f for f in FICO if f is not None])
EDGES = []
for q in (0.2, 0.4, 0.6, 0.8):
    e = float(np.quantile(fv, q))
    if e > fv[0] and (not EDGES or e > EDGES[-1]):
        EDGES.append(e)
put(["record", "C17"], [round(x) for x in EDGES] + [len(EDGES) + 1], "the quintiles of every readable FICO")


def pocket(i):
    b = FICO_WHY[i] if FICO_WHY[i] else sum(FICO[i] >= x for x in EDGES)
    return (b, rows[i]["CHANNEL"])


# ------------------------------------------------------------------ conditional logistic regression
def log_poly(ns, ws):
    """log coefficients of prod_g (1 + w_g z)^{n_g}: binomial coefficients times powers, convolved in logs."""
    out = np.array([0.0])
    for n, lw in zip(ns, ws):
        j = np.arange(n + 1)
        term = gammaln(n + 1) - gammaln(j + 1) - gammaln(n - j + 1) + j * lw
        conv = np.full(len(out) + n, -np.inf)
        for a, va in enumerate(out):
            conv[a:a + n + 1] = np.logaddexp(conv[a:a + n + 1], va + term)
        out = conv
    return out


def stratum_moments(ns, k, beta):
    """For one pocket with ns loans in each group, k of them bad, and log odds ratios beta (group 0 the reference):
    log of the denominator, and the conditional mean and covariance of the bad counts in groups 1..G-1."""
    G = len(ns)
    lw = np.r_[0.0, beta]
    lp = log_poly(ns, lw)
    base = lp[k]
    mean = np.zeros(G - 1)
    cov = np.zeros((G - 1, G - 1))
    for g in range(1, G):
        if ns[g] == 0 or k < 1:
            continue
        m2 = list(ns)
        m2[g] -= 1
        mean[g - 1] = math.exp(math.log(ns[g]) + lw[g] + log_poly(m2, lw)[k - 1] - base)
    for g in range(1, G):
        for h in range(g, G):
            m2 = list(ns)
            m2[g] -= 1
            m2[h] -= 1
            nn = ns[g] * (ns[g] - 1) if g == h else ns[g] * ns[h]
            if k < 2 or min(m2) < 0 or nn == 0:          # two bad loans can't both be drawn from here
                e2 = 0.0
            else:
                e2 = math.exp(math.log(nn) + lw[g] + lw[h] + log_poly(m2, lw)[k - 2] - base)
            if g == h:
                cov[g - 1, g - 1] = e2 + mean[g - 1] - mean[g - 1] ** 2
            else:
                cov[g - 1, h - 1] = cov[h - 1, g - 1] = e2 - mean[g - 1] * mean[h - 1]
    return base, mean, cov


def clogit(strata, G, fixed=None):
    """strata: list of (loans per group, bad per group), group 0 the reference. Returns beta, se, loglik. `fixed`
    pins every beta at 0 (the null)."""
    use = [(np.array(n), np.array(b)) for n, b in strata if 0 < sum(b) < sum(n)]
    beta = np.zeros(G - 1)

    def parts(beta):
        ll, grad, info = 0.0, np.zeros(G - 1), np.zeros((G - 1, G - 1))
        for n, b in use:
            base, mean, cov = stratum_moments(list(map(int, n)), int(b.sum()), beta)
            ll += float(b[1:] @ beta) - base
            grad += b[1:] - mean
            info += cov
        return ll, grad, info
    if fixed is not None:
        return None, None, parts(np.zeros(G - 1))[0]
    for _ in range(100):
        ll, grad, info = parts(beta)
        step = np.linalg.solve(info, grad)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-12:
            break
    ll, grad, info = parts(beta)
    se = np.sqrt(np.diag(np.linalg.inv(info)))
    return beta, se, ll


def reorder(c, groups):
    """groups in the reference-first order clogit wants, and back."""
    ref = REF[c]
    return [ref] + [g for g in range(groups) if g != ref]


def tables(c, idx, by_pocket):
    """per stratum: loans and bad per group (reference first)."""
    G = len(BINS[c]) + 1
    order = reorder(c, G)
    cells = defaultdict(lambda: [np.zeros(G, int), np.zeros(G, int)])
    for i in idx:
        g = group(c, i)
        if g is None or FLAG[i] is None:
            continue
        key = pocket(i) if by_pocket else "all"
        cells[key][0][order.index(g)] += 1
        cells[key][1][order.index(g)] += FLAG[i]
    return [(list(n), list(b)) for n, b in cells.values()], order


def general_trend(strata, G, order):
    """statistics.md B3 (general association, K - 1 df) and B4 (trend, scores 1..K by the groups' own order)."""
    d = np.zeros(G - 1)
    V = np.zeros((G - 1, G - 1))
    T = Var = 0.0
    s = np.array([order.index(g) for g in range(G)], dtype=float)       # position of natural group g in `order`
    scores = np.zeros(G)
    for g in range(G):
        scores[order.index(g)] = g + 1
    for n, b in strata:
        n, b = np.array(n, float), np.array(b, float)
        Nh, Ch = n.sum(), b.sum()
        if Nh < 2:
            continue
        Eh = n * Ch / Nh
        f = Ch * (Nh - Ch) / (Nh * Nh * (Nh - 1))
        d += (b - Eh)[:G - 1]
        R = n[:G - 1]
        V += f * (Nh * np.diag(R) - np.outer(R, R))
        T += float((scores * (b - Eh)).sum())
        Var += f * (Nh * float((scores ** 2 * n).sum()) - float((scores * n).sum()) ** 2)
    q = float(d @ np.linalg.solve(V, d))
    qt = T * T / Var
    return (q, G - 1, float(st.chi2.sf(q, G - 1))), (qt, 1, float(st.chi2.sf(qt, 1)))


def rng_(beta, se):
    return math.exp(beta - Z * se), math.exp(beta + Z * se)


def bh(ps):
    return [float(x) for x in multipletests(ps, method="fdr_bh")[1]]


# ------------------------------------------------------------------ each candidate on its own
SETS = {"Found": DEV, "Confirmed": HOLD}
R = {}
for c in CANDS:
    G = len(BINS[c]) + 1
    for sname, idx in SETS.items():
        for held in (False, True):
            strata, order = tables(c, idx, held)
            beta, se, ll = clogit(strata, G)
            _, _, ll0 = clogit(strata, G, fixed=True)
            gen, trend = general_trend(strata, G, order)
            R[(c, sname, held)] = {"order": order, "beta": beta, "se": se, "ll": ll, "ll0": ll0, "gen": gen,
                                   "trend": trend, "block": (2 * (ll - ll0), G - 1, float(st.chi2.sf(2 * (ll - ll0),
                                                                                                        G - 1)))}
# the allowance: across every candidate's groups on each set of loans (New variables!C11)
for sname in SETS:
    for held in (False, True):
        items = [(c, j) for c in CANDS for j in range(len(BINS[c]))]
        raw = []
        for c, j in items:
            r = R[(c, sname, held)]
            raw.append(2 * st.norm.sf(abs(r["beta"][j] / r["se"][j])))
        adj = bh(raw)
        for (c, j), p, a in zip(items, raw, adj):
            R[(c, sname, held)].setdefault("p", {})[j] = p
            R[(c, sname, held)].setdefault("p_adj", {})[j] = a


def counts(c, idx, g=None):
    use = [i for i in idx if FLAG[i] is not None and group(c, i) is not None and (g is None or group(c, i) == g)]
    return len(use), sum(FLAG[i] for i in use), use


book_gco = sum(g for g in GCO if g is not None)
LINE = MAT * book_gco
put(["nv-text", "L23"], [LINE], "1% of the book's charge-offs")
put(["control", "E19"], [LINE], "")
holds_n = 0
worse_groups = 0
cands_worse = set()
for c in CANDS:
    G = len(BINS[c]) + 1
    order = R[(c, "Found", False)]["order"]
    ref = REF[c]
    n_hold, bad_hold, use_hold = counts(c, HOLD)
    gco_hold = sum(GCO[i] for i in use_hold if GCO[i] is not None)
    holds_any = False
    for j, g in enumerate(order[1:]):
        comp = f"{LAB[c][g]} vs {LAB[c][ref]}"
        who = ["nv-main", c, comp]
        f_, cf, ch = R[(c, "Found", False)], R[(c, "Confirmed", False)], R[(c, "Confirmed", True)]
        gf, gc, gh = (math.exp(r["beta"][j]) for r in (f_, cf, ch))
        pf, pc, ph = f_["p_adj"][j], cf["p_adj"][j], ch["p_adj"][j]
        put(who + ["Found: Gap"], gf, "conditional logistic regression, one pocket")
        put(who + ["Found: p, allowed"], pf, "Wald, then Benjamini-Hochberg")
        put(who + ["Confirmed on the held-back loans: Gap"], gc, "")
        put(who + ["Confirmed on the held-back loans: p, allowed"], pc, "")
        holds = pc < ALPHA and (gc > 1) == (gf > 1)
        still = ph < ALPHA and (gh > 1) == (gf > 1)
        holds_any |= holds
        put(who + ["Confirmed on the held-back loans: Holds up?"], "Yes" if holds else "No", "New variables!C11")
        put(who + ["Confirmed, FICO and CHANNEL held fixed: Gap"], gh, "conditional, pockets held fixed")
        put(who + ["Confirmed, FICO and CHANNEL held fixed: p, allowed"], ph, "")
        put(who + ["Confirmed, FICO and CHANNEL held fixed: Still holds?"], "Yes" if still else "No", "")
        n_g, b_g, use_g = counts(c, HOLD, g)
        gco_g = sum(GCO[i] for i in use_g if GCO[i] is not None)
        excess = (gco_g - n_g / n_hold * gco_hold) * book_gco / gco_hold
        put(who + ["Confirmed, FICO and CHANNEL held fixed: Excess $"], excess, "New variables!C14")
        put(who + ["Confirmed, FICO and CHANNEL held fixed: Material?"], "Yes" if excess >= LINE else "No", "")
        words = ("Holds up, and not just FICO and CHANNEL" if holds and still else
                 "Holds up, but it was mostly FICO and CHANNEL" if holds else
                 "Holds up only with them held fixed" if still else "Didn't hold up on held-back loans")
        put(who + ["Confirmed, FICO and CHANNEL held fixed: In words"], words, "New variables!C15")
        # Start here: the held-back groups, held fixed
        sig_worse = ph < ALPHA and gh > 1
        worse_groups += sig_worse
        if sig_worse:
            cands_worse.add(c)
        name = f"{c}: {LAB[c][g]}"
        put(["st-row", name, "Loans"], n_g, "")
        put(["st-row", name, "Bad rate"], b_g / n_g, "")
        put(["st-row", name, "× its reference's odds, FICO and CHANNEL held fixed"], gh, "")
        put(["st-row", name, "p-value"], ph, "")
        put(["st-row", name, "Significant?"], "Yes, worse" if sig_worse else ("Yes, better" if ph < ALPHA else "No"),
            "")
        put(["st-row", name, "Share of bad loans"], b_g / bad_hold, "")
    holds_n += holds_any
    n_r, b_r, _ = counts(c, HOLD, ref)
    name = f"{c}: {LAB[c][ref]}"
    put(["st-row", name, "Loans"], n_r, "")
    put(["st-row", name, "Bad rate"], b_r / n_r, "")
    put(["st-row", name, "× its reference's odds, FICO and CHANNEL held fixed"], 1, "the reference")
    put(["st-row", name, "Share of bad loans"], b_r / bad_hold, "")

    # the tests in full
    names = {("Found", False): "Found, nothing held fixed", ("Found", True): "Found, FICO and CHANNEL held fixed",
             ("Confirmed", False): "Confirmed on the held-back loans, nothing held fixed",
             ("Confirmed", True): "Confirmed on the held-back loans, FICO and CHANNEL held fixed"}
    for (sname, held), block in names.items():
        r = R[(c, sname, held)]
        for test, (stat, df, p) in (("Any difference across the groups (general)", r["gen"]),
                                    ("A steady climb or fall (trend)", r["trend"]),
                                    ("Any difference, from the regression (block test)", r["block"])):
            who = ["nv-test", c, block, test]
            put(who + ["Statistic"], stat, "")
            put(who + ["Degrees of freedom"], df, "")
            put(who + ["p-value"], p, "")
            put(who + ["Reading"], "significant" if p < ALPHA else "not significant", "")

    # the group tables, found and confirmed (raw p-values, before the allowance)
    for sname, blockname in (("Found", "Found"), ("Confirmed", "Confirmed on the held-back loans")):
        idx = SETS[sname]
        rn, rh = R[(c, sname, False)], R[(c, sname, True)]
        sentence_plain, sentence_held = [], []
        for g in range(G):
            n_g, b_g, _ = counts(c, idx, g)
            who = ["nv-group", c, blockname, LAB[c][g]]
            put(who + ["Loans"], n_g, "")
            put(who + ["Bad loans"], b_g, "")
            put(who + ["Bad rate"], b_g / n_g, "")
            if g == REF[c]:
                put(who + ["Odds ratio"], [1.00], "the reference")
                put(who + ["Odds ratio, FICO and CHANNEL held fixed"], [1.00], "the reference")
                continue
            j = order.index(g) - 1
            for r, suffix, sent in ((rn, "", sentence_plain), (rh, ", FICO and CHANNEL held fixed", sentence_held)):
                orr = math.exp(r["beta"][j])
                lo, hi = rng_(r["beta"][j], r["se"][j])
                put(who + ["Odds ratio" + suffix], orr, "")
                put(who + ["p-value" + (" (held fixed)" if suffix else "")], r["p"][j], "Wald, before the allowance")
                put(who + ["Range (95% sure)" + (" (held fixed)" if suffix else "")], [lo, hi], "")
                if r["p"][j] < ALPHA:
                    sent.append((g, orr, lo, hi))
        for sent, held in ((sentence_plain, False), (sentence_held, True)):
            nums = []
            for g, orr, lo, hi in sent:
                nums += [float(x) for x in LAB[c][g].split(" - ")] + [orr] + \
                        [float(x) for x in LAB[c][REF[c]].split(" - ")] + [lo, hi]
            if sent:
                put(["nv-words", c, sname, "held" if held else "plain"], nums,
                    "the groups whose raw p-value is under 5%, as the sentence names them")
    # how much of the held-back loans' losses sit in each group (holdout only)
    for g in list(range(G)) + ["all"]:
        if g == "all":
            n_g, b_g, gg, lab = n_hold, bad_hold, gco_hold, "All held-back loans in the test"
        else:
            n_g, b_g, use_g = counts(c, HOLD, g)
            gg, lab = sum(GCO[i] for i in use_g if GCO[i] is not None), LAB[c][g]
        who = ["nv-conc", c, lab]
        put(who + ["Loans"], n_g, "")
        put(who + ["Share of loans"], n_g / n_hold, "")
        put(who + ["Bad loans"], b_g, "")
        put(who + ["Share of bad loans"], b_g / bad_hold, "")
        put(who + ["GCO"], gg, "")
        put(who + ["Share of GCO"], gg / gco_hold, "")
        put(who + ["Bad rate"], b_g / n_g, "")
        put(who + ["Times the holdout's bad rate"], (b_g / n_g) / (bad_hold / n_hold), "")
        if g != "all" and g != REF[c]:
            rh = R[(c, "Confirmed", True)]
            if rh["p"][order.index(g) - 1] < ALPHA:
                put(["nv-words", c, "Confirmed", "conc"],
                    [float(x) for x in LAB[c][g].split(" - ")] + [100 * n_g / n_hold, 100 * b_g / bad_hold,
                                                                  100 * gg / gco_hold, (b_g / n_g) / (bad_hold / n_hold)],
                    "")

put(["nv-text", "F23"], [len(CANDS), holds_n], "")
put(["st-text", "B17"], [worse_groups, sum(len(BINS[c]) for c in CANDS)], "")
put(["st-text", "D17"], [len(cands_worse), len(CANDS)], "")

# ------------------------------------------------------------------ every candidate together (New variables!C5)
import statsmodels.api as sm  # noqa: E402

use = [i for i in HOLD if FLAG[i] is not None and all(VAL[c][i] is not None for c in CANDS)]
left_joint = sum(1 for i in HOLD if FLAG[i] is not None and any(VAL[c][i] is None for c in CANDS))
pk = defaultdict(list)
for i in use:
    pk[pocket(i)].append(FLAG[i])
live = sorted((p for p, ys in pk.items() if 0 < sum(ys) < len(ys)), key=repr)
use = [i for i in use if pocket(i) in live]
cols = [(c, g) for c in CANDS for g in range(len(BINS[c]) + 1) if g != REF[c]]
Xd = np.zeros((len(use), len(live) + len(cols)))
for n, i in enumerate(use):
    Xd[n, live.index(pocket(i))] = 1.0
    for k, (c, g) in enumerate(cols):
        Xd[n, len(live) + k] = float(group(c, i) == g)
yv = np.array([FLAG[i] for i in use], dtype=float)
full = sm.Logit(yv, Xd).fit(method="newton", tol=1e-12, maxiter=200, disp=0)
lr = {}
for c in CANDS:
    keep = [j for j in range(Xd.shape[1]) if j < len(live) or cols[j - len(live)][0] != c]
    red = sm.Logit(yv, Xd[:, keep]).fit(method="newton", tol=1e-12, maxiter=200, disp=0)
    lr[c] = (2 * (full.llf - red.llf), len(BINS[c]))
lr_p = {c: float(st.chi2.sf(*lr[c])) for c in CANDS}
lr_adj = dict(zip(CANDS, bh([lr_p[c] for c in CANDS])))
for k, (c, g) in enumerate(cols):
    comp = f"{LAB[c][g]} vs {LAB[c][REF[c]]}"
    b, s_ = full.params[len(live) + k], full.bse[len(live) + k]
    n_g, b_g, _ = counts(c, HOLD, g)
    who = ["nv-joint", c, comp]
    put(who + ["Loans"], n_g, "")
    put(who + ["Bad rate"], b_g / n_g, "")
    put(who + ["Odds ratio, together"], math.exp(b), "statsmodels Logit, pockets as constants")
    put(who + ["Range (95% sure)"], list(rng_(b, s_)), "")
    put(who + ["p-value"], float(2 * st.norm.sf(abs(b / s_))), "Wald")
    if g == [x for x in range(len(BINS[c]) + 1) if x != REF[c]][0]:
        put(who + ["Adds: statistic"], [lr[c][0], lr[c][1]], "likelihood ratio, the candidate taken out")
        put(who + ["Adds: p, allowed"], lr_adj[c], "")
        put(who + ["Adds?"], "Yes" if lr_adj[c] < ALPHA else "No", "")
put(["nv-text", "C39"], [left_joint], "held-back loans without every candidate's value")
put(["nv-text", "C11"], [len(CANDS), sum(len(BINS[c]) for c in CANDS)], "")
put(["record", "F72"], [len(CANDS)], "")
# figures that sit inside words on the tabs, keyed by their cell (compare.py looks for ["cell", tab, cell])
dev_dates, hold_dates = ymd(FIRST) + ymd(DEV_END), ymd(CUT) + ymd(LAST)
for cell in ("B85", "B91", "B111", "B136", "B142", "B162"):
    put(["cell", "New variables", cell], dev_dates, "the development loans' dates")
for cell in ("B97", "B103", "B118", "B148", "B154", "B170"):
    put(["cell", "New variables", cell], hold_dates, "the held-back loans' dates")
put(["cell", "New variables", "C1"], [len(CANDS)], "")
put(["cell", "New variables", "B31"], [len(CANDS)], "")
put(["cell", "New variables", "C4"], ymd(CUT) + [None, None], "the cutoff; then 0.5 and 1, the AUC's scale")
for c in CANDS:
    put(["sc-cand", c, "Reference"], LAB[c][REF[c]], "the group holding the development loans' median")
put(["cell", "New variables", "C6"], [len(CANDS)] + [x for c in CANDS for x in [len(BINS[c]) + 1] +
                                                     [float(y) for lab in LAB[c] for y in lab.split(" - ")]], "")
put(["cell", "Scouting", "B41"], [None, None, None, len(dev_y)] + dev_dates, "the Run's date, then the counts")
put(["cell", "Scouting", "B42"], [len(HOLD)] + hold_dates, "")
put(["cell", "Scouting", "B49"], [REF["UTIL"]] + [float(x) for x in LAB["UTIL"][REF["UTIL"]].split(" - ")],
    "the group holding the development loans' median")
put(["cell", "Scouting", "B52"], [REF["income_to_sales"]] +
    [float(x) for x in LAB["income_to_sales"][REF["income_to_sales"]].split(" - ")], "")
put(["cell", "Scouting", "B58"], BINS["UTIL"], "the pre-spec's bins")
put(["cell", "Scouting", "B84"], BINS["income_to_sales"], "")
for c in CANDS:
    med = statistics.median(VAL[c][i] for i in dev_y if VAL[c][i] is not None)
    assert sum(med >= x for x in BINS[c]) == REF[c], (c, med)     # the reference holds the median (Scouting!C13)
put(["record", "F73"], [sum(len(BINS[c]) for c in CANDS)], "")
put(["nv-text", "C7"], [float(x) for c in CANDS for x in LAB[c][REF[c]].split(" - ")], "each pre-spec reference")

# the second way (New variables!C17): each odds ratio held fixed by Mantel-Haenszel, group against reference
gaps = []
for c in CANDS:
    order = R[(c, "Confirmed", True)]["order"]
    ref = REF[c]
    for j, g in enumerate(order[1:]):
        num = den = 0.0
        byp = defaultdict(lambda: [0, 0, 0, 0])
        for i in HOLD:
            gi = group(c, i)
            if FLAG[i] is None or gi not in (g, ref):
                continue
            t = byp[pocket(i)]
            if gi == g:
                t[0 if FLAG[i] else 1] += 1
            else:
                t[2 if FLAG[i] else 3] += 1
        for a, b_, c_, d in byp.values():
            n = a + b_ + c_ + d
            num += a * d / n
            den += b_ * c_ / n
        mh = num / den
        gaps.append(abs(math.exp(R[(c, "Confirmed", True)]["beta"][j]) / mh - 1))     # measured from MH
put(["nv-text", "C17"], [95, 100 * max(gaps)], "")

# the counts in words (New variables!C8, Scouting!C5, Record)
nd = {c: counts(c, DEV) for c in CANDS}
nh = {c: counts(c, HOLD) for c in CANDS}
no_val = {c: sum(1 for i in HOLD + DEV if VAL[c][i] is None and FLAG[i] is not None) for c in CANDS}
no_out = sum(1 for i in HOLD + DEV if FLAG[i] is None)
put(["nv-text", "C8"], ymd(FIRST) + ymd(DEV_END) + [nd["UTIL"][0], nd["UTIL"][1], nd["income_to_sales"][0],
                                                     nd["income_to_sales"][1]] + ymd(CUT) + ymd(LAST) +
    [nh["UTIL"][0], nh["UTIL"][1], nh["income_to_sales"][0], nh["income_to_sales"][1], no_out,
     no_val["income_to_sales"], no_out], "")
put(["nv-text", "N23"], [len(dev_y), len(hold_y)], "")
put(["st-text", "F17"], [len(dev_y), len(hold_y)], "")
put(["st-text", "C1"], [N, len(rows[0]), None, None, None, None, None], "the Run's date and time are its own clock")
put(["sc-text", "C5"], [len(dev_y)] + ymd(FIRST) + ymd(DEV_END) + [sum(FLAG[i] for i in dev_y)] + ymd(CUT) +
    [len(HOLD), len(DEV) - len(dev_y)], "")
put(["sc-text", "H19"], [len(dev_y), sum(FLAG[i] for i in dev_y)], "")
put(["sc-prespec", "holdout"], ymd(CUT) + ymd(LAST), "")
put(["sc-prespec", "development"], ymd(FIRST) + ymd(DEV_END), "")
put(["sc-prespec", "bins", "UTIL"], BINS["UTIL"], "the pre-spec, taken as given")
put(["sc-prespec", "bins", "income_to_sales"], BINS["income_to_sales"], "")

# ------------------------------------------------------------------ Record, Columns, Look for this Run
inc_made = sum(1 for v in VAL["income_to_sales"] if v is not None)
sales_zero = sum(1 for r in rows if number(r["SALES"]) == 0)
sales_blank = sum(1 for r in rows if r["SALES"] == "")
put(["record", "C11"], [N], "")
put(["record", "C15"], ymd(FIRST) + ymd(LAST) + [N, N - len(dated)], "")
put(["record", "C16"], [inc_made, N - inc_made, sales_zero, sales_blank], "")
put(["record", "C18"], [8, len(dev_y)] + ymd(FIRST) + ymd(DEV_END) + [2], "8 candidates ticked or made")
put(["record", "C20"], [len(HOLD)] + ymd(CUT) + ymd(LAST), "")
put(["record", "C30"], [len(CANDS)], "")
put(["record", "C31"], [1], "")
put(["record", "C32"], [1, 0.9] + [float(x) for lab in LAB["UTIL"] for x in lab.split(" - ")], "")
put(["record", "C33"], [1] + [float(x) for x in LAB["UTIL"][0].split(" - ")], "")
put(["record", "C34"], [2], "")
put(["record", "C35"], [2, 0.1, 2] + [float(x) for lab in LAB["income_to_sales"] for x in lab.split(" - ")], "")
put(["record", "C36"], [2] + [float(x) for x in LAB["income_to_sales"][1].split(" - ")], "")
put(["record", "C39"], ymd(CUT) + ymd(LAST), "")
put(["record", "C40"], ymd(FIRST) + ymd(DEV_END), "")
put(["record", "C43"], [len(HOLD)] + ymd(CUT) + ymd(LAST) + ymd(min(DATE[i] for i in HOLD)), "")
put(["record", "C44"], ymd(max(DATE[i] for i in HOLD)), "")
put(["record", "C45"], ymd(FIRST) + ymd(DEV_END) + [nd["UTIL"][0], nd["UTIL"][1]] + ymd(CUT) + ymd(LAST) +
    [nh["UTIL"][0]], "")
put(["record", "C46"], [nh["UTIL"][1], no_out], "")
put(["record", "C48"], ymd(FIRST) + ymd(DEV_END) + [nd["income_to_sales"][0], nd["income_to_sales"][1]] + ymd(CUT)
    + ymd(LAST), "")
put(["record", "C49"], [nh["income_to_sales"][0], nh["income_to_sales"][1]], "")
put(["record", "C50"], [no_val["income_to_sales"], no_out], "")
put(["record", "G10"], ymd(CUT), "")
put(["record", "F13"], [1.0, LINE], "")
put(["record", "G13"], [1.0, LINE], "")
put(["record", "F82"], [N], "")
put(["record", "F84"], [len(dev_y)] + ymd(FIRST) + ymd(DEV_END) + [len(HOLD), 2, 8], "")
put(["record", "F88"], [len(HOLD)] + ymd(CUT) + ymd(LAST), "")
put(["record", "F91"], [len(HOLD)] + ymd(CUT) + ymd(LAST), "")
neg = {c: sum(1 for r in rows if number(r[c]) is not None and number(r[c]) < 0) for c in ("RANR_AMT", "F1", "F2")}
put(["record", "C87"], [neg["RANR_AMT"]], "")
put(["record", "C89"], [neg["F1"]], "")
put(["record", "C91"], [neg["F2"]], "")
put(["record", "F95"], [neg["RANR_AMT"]], "")
put(["record", "F97"], [neg["F1"]], "")
put(["record", "F99"], [neg["F2"]], "")
bad_flag = sum(1 for f in FLAG if f is None)
bal_blank = sum(1 for r in rows if r["ORIG_BAL"] == "")
gco_bad = sum(1 for g in GCO if g is None)
put(["record", "C82"], [bad_flag, 0, 1], "")
put(["record", "C83"], [bal_blank, bad_flag, 0, 1], "")
put(["record", "C84"], [gco_bad, bal_blank], "")
put(["record", "C85"], [bal_blank], "")
put(["record", "C86"], [gco_bad, bal_blank], "")

cols_ = list(rows[0].keys())
for c in cols_:
    put(["columns", c, "blank"], sum(1 for r in rows if r[c] == "") / N, "")
put(["columns", "income_to_sales", "blank"], (N - inc_made) / N, "")
ficov = [number(r["FICO"]) for r in rows if number(r["FICO"]) is not None]
put(["columns", "FICO", "why"], [round(100 * sum(300 <= f <= 850 for f in ficov) / len(ficov)), 300, 850], "")
put(["columns", "FICO", "odd"], [-9999, sum(1 for f in ficov if f == -9999)], "")
put(["columns", "BAD_FLAG", "why"], [0, 1, round(100 * sum(1 for f in FLAG if f == 1) / N, 1), 1], "")
put(["columns", "BAD_FLAG", "check"], [bad_flag, 0, 1], "")
put(["columns", "GCO_AMT", "why"], [round(100 * sum(1 for g in GCO if g == 0) / N)], "")
put(["columns", "GCO_AMT", "check"], [gco_bad, N - gco_bad], "")
put(["columns", "RANR_AMT", "odd"], [neg["RANR_AMT"]], "")
put(["columns", "F1", "odd"], [neg["F1"]], "")
put(["columns", "F2", "odd"], [neg["F2"]], "")
for c in ("CHANNEL", "ASSET_CLASS", "REGION"):
    k = len(set(r[c] for r in rows if r[c] != ""))
    put(["columns", c, "why"], [k], "")
    put(["columns", c, "check"], [k], "")
for c in ("REV_DEBT", "SALES", "INCOME", "UTIL", "TENURE", "F1", "F2", "F3", "F4"):
    k = len(set(number(r[c]) for r in rows if number(r[c]) is not None))
    put(["columns", c, "why"], [k], "")
    put(["columns", c, "check"], [k], "")

LOOKV = {}
for c in ("FICO", "ORIG_BAL", "REV_DEBT", "SALES", "INCOME", "UTIL", "TENURE", "F1", "F2", "F3", "F4",
          "income_to_sales"):
    raw = [r.get(c, "") for r in rows] if c != "income_to_sales" else \
        ["" if v is None else str(v) for v in VAL["income_to_sales"]]
    vals = [number(x) for x in raw]
    code = -9999 if c == "FICO" else None
    real = [v for v in vals if v is not None and v != code]
    LOOKV[c] = real
    blank = sum(1 for x in raw if x == "")
    notnum = sum(1 for x in raw if x != "" and number(x) is None)
    put(["look", c, "Loans", 3], len(raw), "")
    put(["look", c, "Blank", 3], blank, "")
    put(["look", c, "Blank", 4], blank / len(raw), "")
    put(["look", c, "Not a number", 3], notnum, "")
    put(["look", c, "Not a number", 4], notnum / len(raw), "")
    if code is not None:
        at_ = sum(1 for v in vals if v == code)
        put(["look", c, "At -9999, likely a code", 3], at_, "")
        put(["look", c, "At -9999, likely a code", 4], at_ / len(raw), "")
    put(["look", c, "Smallest", 3], min(real), "")
    put(["look", c, "Median", 3], statistics.median(real), "")
    put(["look", c, "Mean", 3], statistics.fmean(real), "")
    put(["look", c, "Largest", 3], max(real), "")
if FIGS:
    for f in json.load(open(FIGS)):
        k = f["key"]
        if k[0] == "look-bar" and k[1] in LOOKV:
            _, name, a, w, last = k
            v = np.array(LOOKV[name])
            b_ = a + w
            put(k, int(((v >= a) & ((v <= b_) if last else (v < b_))).sum()), "loans from the bar's start to its end")
    ranges = {}
    for f in json.load(open(FIGS)):
        k = f["key"]
        if k[0] == "look-bar":
            lo_, hi_ = ranges.get(k[1], (math.inf, -math.inf))
            ranges[k[1]] = (min(lo_, k[2]), max(hi_, k[2] + k[3]))
    for f in json.load(open(FIGS)):
        k = f["key"]
        if k[0] == "look-end" and k[1] in LOOKV:
            v = np.array(LOOKV[k[1]])
            lo_, hi_ = ranges[k[1]]
            if k[2] == "low end":
                put(k, int((v < lo_).sum()), "loans below the chart's first bar")
            elif k[2] == "high end":
                put(k, int((v > hi_ + 1e-9).sum()), "loans above the chart's last bar")
            else:
                put(k, sum(1 for r in rows if number(r["FICO"]) == -9999), "")
json.dump({"expected": E, "meta": {"columns": list(rows[0].keys()) + ["income_to_sales"], "cutoff": CUT.isoformat(),
                                   "labels": LAB, "edges": EDGES, "n": N,
                                   "dev": len(dev_y), "hold": len(hold_y)}}, open(OUT, "w"), indent=0, default=float)
print(len(E), "expected figures; cutoff", CUT, "dev", len(dev_y), "held back", len(hold_y))
for c in CANDS:
    for s_ in SETS:
        for h in (False, True):
            r = R[(c, s_, h)]
            print(c, s_, "held" if h else "plain", "OR", np.round(np.exp(r["beta"]), 6), "gen", round(r["gen"][0], 6),
                  "trend", round(r["trend"][0], 6), "block", round(r["block"][0], 6))
