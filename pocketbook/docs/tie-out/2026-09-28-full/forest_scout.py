"""The independent road for the Scouting tab: the random forest grown again from the loan file, with the settings the
workbook states (Scouting!C7: 200 trees, each leaf at least 40 loans, seed 7, scikit-learn; C8: three runs by date,
five shuffles of each column; C12: partial dependence on 1,000 development loans over the column's own percentiles),
and nothing else from PocketBook.

    python3 forest_scout.py "Scouting book.csv" OUT/expected-forest.json figures-scout.json

What can and cannot land on the same digits:
  - the forests themselves: scikit-learn with a fixed seed grows the same trees from the same rows in the same order,
    so the AUCs (built, cross-fitted by date; unseen, on the held-back loans) can tie exactly, if the rows and the
    columns are laid out the way the workbook says (development loans in date order; candidates in the order they
    were ticked, then the new column; a category as its value's place in sorted order; the held-fixed columns last)
  - importance: the drop in AUC when a column is shuffled. The shuffles are this road's own random numbers, so the
    two can only agree within sampling error. This road shuffles each column 40 times a run, not 5, and uses the
    spread of the drops to say how far apart the two could honestly be (four standard errors of the difference)
  - partial dependence: the workbook averages over 1,000 development loans drawn by its seed; this road averages over
    every development loan, and allows four standard errors of a 1,000-loan average
  - the noise floor is the largest of 24 importances with the outcomes shuffled: one more draw of the same random
    thing is worked out here, and reported beside it, but a maximum of random draws has no sampling error small
    enough to call a tie, so it is COULD NOT
The figures file is read only for which percentiles the chart's x values sit at (checked here to be the development
loans' own percentiles) and nothing else.
"""
import csv
import json
import math
import sys
from datetime import date, timedelta

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

X, OUT, FIGS = sys.argv[1], sys.argv[2], sys.argv[3]
TREES, LEAF, SEED, FOLDS = 200, 40, 7, 3
MY_REPEATS, THEIR_REPEATS = 40, 5
rng = np.random.default_rng(20260928)

rows = list(csv.DictReader(open(X, newline="", encoding="utf-8")))
N = len(rows)


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def day(s):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


D = [day(r["ORIG_DATE"]) for r in rows]
Y = [int(r["BAD_FLAG"]) if r["BAD_FLAG"] in ("0", "1") else None for r in rows]
dated = sorted(d for d in D if d)
at = dated[max(1, math.ceil(0.7 * len(dated))) - 1]
this = at.replace(day=1)
nxt = (this + timedelta(days=32)).replace(day=1)
CUT = min((this, nxt), key=lambda d: (abs((d - at).days), d))
dev = [i for i in sorted(range(N), key=lambda i: (D[i] or date.max, i)) if D[i] and D[i] < CUT and Y[i] is not None]
hold = [i for i in range(N) if D[i] and D[i] >= CUT and Y[i] is not None]

CANDS = ["UTIL", "TENURE", "F1", "F2", "F3", "F4", "REGION", "income_to_sales"]   # ticked order, then made
CATEGORY = {"REGION", "CHANNEL"}
HELD = ["FICO", "CHANNEL"]


def raw(c, i):
    r = rows[i]
    if c == "income_to_sales":
        s, v = num(r["SALES"]), num(r["INCOME"])
        return None if s in (None, 0) or v is None else v / s
    if c == "FICO":
        v = num(r["FICO"])
        return None if v in (None, -9999) else v
    return r[c] if c in CATEGORY else num(r[c])


LEVELS = {c: sorted({raw(c, i) for i in dev if raw(c, i) not in (None, "")}) for c in CATEGORY}


def column(c, idx):
    if c in CATEGORY:
        where = {v: k for k, v in enumerate(LEVELS[c])}
        return np.array([where.get(raw(c, i), np.nan) for i in idx], dtype=float)
    return np.array([np.nan if raw(c, i) is None else raw(c, i) for i in idx], dtype=float)


Xd = np.column_stack([column(c, dev) for c in CANDS])
Xdh = np.column_stack([Xd] + [column(c, dev) for c in HELD])
yd = np.array([Y[i] for i in dev])
Xo = np.column_stack([column(c, hold) for c in CANDS])
Xoh = np.column_stack([Xo] + [column(c, hold) for c in HELD])
yo = np.array([Y[i] for i in hold])


def forest():
    return RandomForestClassifier(n_estimators=TREES, min_samples_leaf=LEAF, random_state=SEED, n_jobs=-1)


def cross_fit(X, y, repeats):
    """AUC on each run by date from a forest grown on the other two, and every column's drop when shuffled."""
    n, m = X.shape
    bounds = [round(n * i / FOLDS) for i in range(FOLDS + 1)]
    aucs, drops = [], np.zeros((FOLDS, m, repeats))
    for f in range(FOLDS):
        va = np.zeros(n, bool)
        va[bounds[f]:bounds[f + 1]] = True
        rf = forest().fit(X[~va], y[~va])
        Xv, yv = X[va], y[va]
        base = roc_auc_score(yv, rf.predict_proba(Xv)[:, 1])
        aucs.append(base)
        for j in range(m):
            for k in range(repeats):
                Xs = Xv.copy()
                Xs[:, j] = rng.permutation(Xv[:, j])
                drops[f, j, k] = base - roc_auc_score(yv, rf.predict_proba(Xs)[:, 1])
    return float(np.mean(aucs)), drops


E = {}


def put(key, value, how="", **extra):
    E[json.dumps(key)] = {"value": value, "how": how, **extra}


auc_plain, drops = cross_fit(Xd, yd, MY_REPEATS)
auc_held, drops_h = cross_fit(Xdh, yd, MY_REPEATS)
imp = drops.mean(axis=2).mean(axis=0)
imp_h = drops_h.mean(axis=2).mean(axis=0)


def tol(dr, j):
    s2 = dr[:, j, :].var(axis=1, ddof=1)                  # per run, the spread of one shuffle's drop
    se_t = math.sqrt(s2.sum() / THEIR_REPEATS) / FOLDS
    se_m = math.sqrt(s2.sum() / MY_REPEATS) / FOLDS
    return 4 * math.sqrt(se_t ** 2 + se_m ** 2) + 5e-7   # the tab shows six decimals


rf_plain = forest().fit(Xd, yd)
rf_held = forest().fit(Xdh, yd)
auc_unseen = roc_auc_score(yo, rf_plain.predict_proba(Xo)[:, 1])
auc_unseen_h = roc_auc_score(yo, rf_held.predict_proba(Xoh)[:, 1])
put(["sc-text", "C8"], [None, FOLDS, THEIR_REPEATS, auc_plain], "cross-fitted AUC, three runs by date")
put(["sc-text", "C9"], [auc_held], "")
first, dev_end, last = min(D[i] for i in dev), CUT - timedelta(days=1), max(d for d in D if d)
ymd = lambda d: [d.year, d.month, d.day]                                  # noqa: E731
words = ymd(first) + ymd(dev_end) + [auc_plain] + ymd(CUT) + ymd(last) + [auc_unseen, auc_held, auc_unseen_h]
put(["nv-text", "C29"], words, "the forests grown again, scored on the held-back loans")
put(["record", "C23"], ymd(first) + ymd(dev_end) + [auc_plain] + ymd(CUT) + ymd(last) + [auc_unseen], "")
put(["record", "C24"], [auc_held, auc_unseen_h], "")
put(["record", "F92"], ymd(first) + ymd(dev_end) + [auc_plain], "")
put(["record", "F93"], ymd(CUT) + ymd(last) + [auc_unseen, auc_held, auc_unseen_h], "")

# the noise floor: one more draw of the same random thing
floor_draws = []
for _ in range(math.ceil(20 / len(CANDS))):
    _, dr = cross_fit(Xd, rng.permutation(yd), THEIR_REPEATS)
    floor_draws += list(dr.mean(axis=2).mean(axis=0))
floor = max(floor_draws)

for j, c in enumerate(CANDS):
    put(["sc-cand", c, "Importance"], float(imp[j]), "", sampled=True, tol=tol(drops, j))
    put(["sc-cand", c, "FICO and CHANNEL held fixed"], float(imp_h[j]), "", sampled=True, tol=tol(drops_h, j))
for j, c in enumerate(HELD):
    put(["sc-held", c], float(imp_h[len(CANDS) + j]), "", sampled=True, tol=tol(drops_h, len(CANDS) + j))
order = sorted(range(len(CANDS)), key=lambda j: (-max(imp[j], imp_h[j]), j))
best_tol = [max(tol(drops, j), tol(drops_h, j)) for j in range(len(CANDS))]
bestv = [max(imp[j], imp_h[j]) for j in range(len(CANDS))]
for rank, j in enumerate(order, 1):
    # the ranks this candidate could take, given how far each importance could honestly move
    above = sum(1 for k in range(len(CANDS)) if k != j and bestv[k] - best_tol[k] > bestv[j] + best_tol[j])
    below = sum(1 for k in range(len(CANDS)) if k != j and bestv[k] + best_tol[k] < bestv[j] - best_tol[j])
    put(["sc-cand", CANDS[j], "Rank"], rank, f"by the larger importance; ranks {above + 1} to "
        f"{len(CANDS) - below} are within sampling error", sampled=True, rank_range=[above + 1, len(CANDS) - below],
        tol=0.5)

# the shapes: partial dependence from the forest with the held-fixed columns in it (Scouting!C12)
figs = json.load(open(FIGS))
curves = {}
for f in figs:
    if f["key"][0] == "sc-curve":
        curves.setdefault(f["key"][1], {}).setdefault(f["key"][2], {})[f["key"][3]] = f["value"]
for c, pts in curves.items():
    j = CANDS.index(c)
    v = Xd[:, j][~np.isnan(Xd[:, j])]
    for i, p in sorted(pts.items()):
        x = p["x"]
        qs = [q for q in np.arange(0.5, 100, 0.5) if abs(np.quantile(v, q / 100) - x) <= 1e-9 * max(1, abs(x))]
        put(["sc-curve", c, i, "x"], float(np.quantile(v, qs[0] / 100)) if qs else None,
            f"the development loans' {qs[0]:g}th percentile" if qs else "not a percentile of the development loans")
        S = Xdh.copy()
        S[:, j] = x
        pr = rf_held.predict_proba(S)[:, 1]
        se = pr.std(ddof=1) / math.sqrt(1000) * math.sqrt(1 - 1000 / len(pr))
        put(["sc-curve", c, i, "rate"], float(pr.mean()), "every development loan, not a draw of 1,000",
            sampled=True, tol=4 * se + 1e-12)

# the bins, one attempt at the rule Scouting!C12 states in words: a cut where the curve steps by at least 25% of
# its average, largest step first, each group at least 2% of the loans, at most 6 groups; the edge where the forest
# split the column most inside that step, rounded to two figures
def attempt_bins(c):
    j = CANDS.index(c)
    v = Xd[:, j][~np.isnan(Xd[:, j])]
    grid = [float(np.quantile(v, q / 100)) for q in (1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 75, 80,
                                                        85, 90, 92.5, 95, 97, 98, 99)]
    grid = sorted(set(grid))
    pd_ = []
    for x in grid:
        S = Xdh.copy()
        S[:, j] = x
        pd_.append(float(rf_held.predict_proba(S)[:, 1].mean()))
    mids = [(a + b) / 2 for a, b in zip(grid, grid[1:])]
    w = np.bincount(np.searchsorted(mids, v, side="right"), minlength=len(grid)) / len(v)
    pd_ = np.array(pd_)
    avg = float((w * pd_).sum() / w.sum())
    cuts = []

    def split(a, b):
        if len(cuts) + 1 >= 6:
            return
        best = None
        for i in range(a, b - 1):
            L, R = slice(a, i + 1), slice(i + 1, b)
            if w[L].sum() < 0.02 or w[R].sum() < 0.02:
                continue
            step = abs((w[L] * pd_[L]).sum() / w[L].sum() - (w[R] * pd_[R]).sum() / w[R].sum())
            if best is None or step > best[0]:
                best = (step, i)
        if best is None or best[0] < 0.25 * avg:
            return
        cuts.append(best[1])
        split(a, best[1] + 1)
        split(best[1] + 1, b)
    split(0, len(grid))
    edges = []
    for i in sorted(cuts):
        th = [t for est in rf_held.estimators_ for f_, t in zip(est.tree_.feature, est.tree_.threshold)
              if f_ == j and grid[i] < t <= grid[i + 1]]
        if not th:
            continue
        vals, cnt = np.unique(np.array([float(f"{t:.2g}") for t in th]), return_counts=True)
        edges.append(float(vals[np.argmax(cnt)]))
    return edges


PRESPEC = {"UTIL": [0.9], "income_to_sales": [0.1, 2.0]}      # what the pre-spec says (Scouting!B48, B51)


def group_labels(c, e):
    """The groups' names, from the first value to one step short of the next edge (Scouting!F24)."""
    v = Xd[:, CANDS.index(c)]
    v = v[~np.isnan(v)]
    lo, hi = float(v.min()), float(v.max())
    for d in range(1, 7):
        step = 10 ** -d
        if e[0] - step < lo:
            continue
        f = lambda x: f"{x:.{d}f}"                                 # noqa: E731
        out = [f"{f(math.floor(lo / step) * step)} - {f(e[0] - step)}"]
        out += [f"{f(a)} - {f(b - step)}" for a, b in zip(e, e[1:])]
        return out + [f"{f(e[-1])} - {f(math.ceil(hi / step) * step)}"]


ATTEMPT = {}
for c in ("UTIL", "income_to_sales"):
    got = attempt_bins(c)
    ATTEMPT[c] = got
    print("bins attempt", c, got)
    if got == PRESPEC[c]:
        put(["sc-cand", c, "Suggested bins"], "; ".join(group_labels(c, got)),
            "this road's reading of the rule on Scouting!C12, on its own partial dependence", sampled_word=True)

# the rest of the table
num_cands = [c for c in CANDS if c not in CATEGORY]
for c in CANDS:
    j = CANDS.index(c)
    corr = []
    for o in num_cands + ["FICO"]:
        if o == c or c in CATEGORY:
            continue
        a = Xd[:, j] if o != "FICO" else None
        b = Xdh[:, CANDS.index(o)] if o in CANDS else Xdh[:, len(CANDS)]
        both = ~np.isnan(Xd[:, j]) & ~np.isnan(b)
        rho = spearmanr(Xd[both, j], b[both])[0]
        if abs(rho) >= 0.7:
            corr.append(round(rho, 2))
    if corr:
        put(["sc-cand", c, "Correlated with"], corr, "Spearman on the development loans with both")
best = {c: max(imp[CANDS.index(c)], imp_h[CANDS.index(c)]) for c in CANDS}
for c in CANDS:
    proposed = c not in CATEGORY and best[c] > floor and c in ("UTIL", "income_to_sales")
    put(["sc-cand", c, "Proposed?"], "Yes" if proposed else "No",
        f"a number column above this road's own noise floor ({floor:.4f}) with a bend to cut", sampled_word=True)
put(["sc-text", "D19"], [len(CANDS), 2], "")
json.dump({"expected": E, "meta": {"bins_attempt": ATTEMPT, "floor_replicate": floor, "floor_draws": len(floor_draws),
                                   "auc": [auc_plain, auc_held, auc_unseen, auc_unseen_h],
                                   "imp": dict(zip(CANDS, map(float, imp))), "imp_held": dict(zip(CANDS, map(float, imp_h))),
                                   "best": best}}, open(OUT, "w"), indent=0, default=float)
print(f"AUC built {auc_plain:.6f}   with FICO and CHANNEL, held {auc_held:.6f}")
print(f"AUC unseen {auc_unseen:.6f}   with FICO and CHANNEL, held {auc_unseen_h:.6f}")
print("importance, candidates alone:     " + "  ".join(f"{c} {v:.6f}" for c, v in zip(CANDS, imp)))
print("importance, FICO and CHANNEL in:  " + "  ".join(f"{c} {v:.6f}" for c, v in zip(CANDS + HELD, imp_h)))
print(f"noise floor, one more draw: {floor:.6f} (the largest of {len(floor_draws)})")
