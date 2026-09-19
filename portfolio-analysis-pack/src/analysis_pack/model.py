"""Step 6 in plain Python: two logistic regressions and a small tree.

No numpy: the bank desk has none. A logistic regression here is fitted by
iteratively reweighted least squares (Newton's method on the log-likelihood),
which for a dozen predictors over tens of thousands of loans is a few seconds
of plain arithmetic. The tree is CART with Gini impurity, depth two or three,
printed as rules.

What the numbers mean, in the words the tabs use: an odds ratio of 2.0 on the
flag means flagged loans carry twice the odds of the outcome with every other
term held fixed; the interval is the range it plausibly sits in. Events per
parameter is the number of outcome events divided by the number of estimated
coefficients; below ten the estimates are known to be unstable (Peduzzi,
Concato, Kemper, Holford & Feinstein 1996, J. Clin. Epidemiol. 49:1373), and
the tab says so above the table rather than in a footnote.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

EPP_WARN = 10
MAX_ITER = 25
TOL = 1e-8
BETA_LIMIT = 15.0


class ModelError(Exception):
    pass


@dataclass
class Term:
    name: str
    coef: float
    se: float
    odds_ratio: float
    lo: float
    hi: float


@dataclass
class Fit:
    label: str                      # "M1" | "M2"
    terms: list[Term]               # excludes the intercept
    intercept: float
    loans: int
    events: int
    coefficients: int               # excluding the intercept
    epp: float | None
    warning: str | None
    estimable: bool
    reason: str | None = None       # when not estimable
    implicated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    references: dict[str, str] = field(default_factory=dict)   # categorical -> reference level
    iterations: int = 0

    def flag(self) -> Term | None:
        for t in self.terms:
            if t.name == "flag":
                return t
        return None


# --------------------------------------------------------------------------
# Linear algebra, small and explicit
# --------------------------------------------------------------------------

def _solve(a: list[list[float]], b: list[float]) -> list[float] | None:
    """Gauss-Jordan with partial pivoting on a copy. None when singular."""
    n = len(a)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            return None
        m[col], m[piv] = m[piv], m[col]
        p = m[col][col]
        for j in range(col, n + 1):
            m[col][j] /= p
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                f = m[r][col]
                for j in range(col, n + 1):
                    m[r][j] -= f * m[col][j]
    return [m[i][n] for i in range(n)]


def _inverse(a: list[list[float]]) -> list[list[float]] | None:
    n = len(a)
    m = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            return None
        m[col], m[piv] = m[piv], m[col]
        p = m[col][col]
        for j in range(col, 2 * n):
            m[col][j] /= p
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                f = m[r][col]
                for j in range(col, 2 * n):
                    m[r][j] -= f * m[col][j]
    return [row[n:] for row in m]


# --------------------------------------------------------------------------
# Logistic regression by IRLS
# --------------------------------------------------------------------------

def fit_logistic(x: list[list[float]], y: list[int], names: list[str], label: str, z: float) -> Fit:
    """`x` rows include a leading 1.0 for the intercept; `names` are the
    non-intercept column names."""
    n = len(y)
    k = len(names) + 1
    events = sum(y)
    epp = None if k - 1 == 0 else events / (k - 1)
    warning = None
    if epp is not None and epp < EPP_WARN:
        warning = (f"Thin: {events:,} events for {k - 1} estimated coefficients is {epp:.1f} events per "
                   f"parameter; below {EPP_WARN} the estimates are unstable (Peduzzi et al. 1996). Read the "
                   f"intervals, not the point estimates.")
    base = Fit(label=label, terms=[], intercept=0.0, loans=n, events=events, coefficients=k - 1, epp=epp,
               warning=warning, estimable=False)
    if n == 0 or events == 0 or events == n:
        base.reason = "not estimable (no variation in the outcome)"
        return base
    beta = [0.0] * k
    p0 = events / n
    beta[0] = math.log(p0 / (1 - p0))
    it = 0
    # Most columns are 0/1 dummies, so a row has a handful of non-zero entries
    # out of k. Precomputing them once turns the k^2 Hessian loop per row into
    # nnz^2, which is what makes a 25,000-loan fit take a second rather than ten.
    nz = [[(j, xj) for j, xj in enumerate(row) if xj != 0.0] for row in x]
    for it in range(1, MAX_ITER + 1):
        # gradient and Hessian in one pass
        g = [0.0] * k
        h = [[0.0] * k for _ in range(k)]
        for pairs, yi in zip(nz, y):
            eta = 0.0
            for j, xj in pairs:
                eta += beta[j] * xj
            if eta > 35:
                p = 1.0
            elif eta < -35:
                p = 0.0
            else:
                p = 1.0 / (1.0 + math.exp(-eta))
            w = p * (1.0 - p)
            r = yi - p
            for a, (j, xj) in enumerate(pairs):
                g[j] += xj * r
                wj = w * xj
                hj = h[j]
                for l, xl in pairs[a:]:
                    hj[l] += wj * xl
        for j in range(k):
            for l in range(j):
                h[j][l] = h[l][j]
        step = _solve(h, g)
        if step is None:
            base.reason = "not estimable (separation or singular design)"
            base.implicated = [names[j - 1] for j in range(1, k) if abs(beta[j]) > 5.0]
            base.iterations = it
            return base
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < TOL:
            break
    big = [names[j - 1] for j in range(1, k) if abs(beta[j]) > BETA_LIMIT]
    if big or it >= MAX_ITER:
        base.reason = "not estimable (separation or singular design)"
        base.implicated = big
        base.iterations = it
        return base
    # standard errors from the inverse Hessian at the solution
    h = [[0.0] * k for _ in range(k)]
    for pairs in nz:
        eta = 0.0
        for j, xj in pairs:
            eta += beta[j] * xj
        p = 1.0 / (1.0 + math.exp(-eta)) if -35 < eta < 35 else (1.0 if eta >= 35 else 0.0)
        w = p * (1.0 - p)
        for a, (j, xj) in enumerate(pairs):
            wj = w * xj
            hj = h[j]
            for l, xl in pairs[a:]:
                hj[l] += wj * xl
    for j in range(k):
        for l in range(j):
            h[j][l] = h[l][j]
    inv = _inverse(h)
    if inv is None:
        base.reason = "not estimable (separation or singular design)"
        base.iterations = it
        return base
    terms = []
    for j in range(1, k):
        se = math.sqrt(max(inv[j][j], 0.0))
        terms.append(Term(names[j - 1], beta[j], se, math.exp(beta[j]),
                          math.exp(beta[j] - z * se), math.exp(beta[j] + z * se)))
    base.terms = terms
    base.intercept = beta[0]
    base.estimable = True
    base.iterations = it
    return base


# --------------------------------------------------------------------------
# CART, depth 2-3, Gini
# --------------------------------------------------------------------------

@dataclass
class Leaf:
    path: list[str]
    loans: int
    events: int

    @property
    def rate(self) -> float | None:
        return None if self.loans == 0 else self.events / self.loans


@dataclass
class TreeResult:
    leaves: list[Leaf]
    overall_rate: float | None
    first_split: str | None
    loans: int
    events: int


def _gini(e: int, n: int) -> float:
    if n == 0:
        return 0.0
    p = e / n
    return 2.0 * p * (1.0 - p)


def _candidates(values: list[float], limit: int = 200) -> list[float]:
    distinct = sorted(set(values))
    if len(distinct) < 2:
        return []
    mids = [(distinct[i] + distinct[i + 1]) / 2.0 for i in range(len(distinct) - 1)]
    if len(mids) <= limit:
        return mids
    step = len(mids) / limit
    return [mids[int(i * step)] for i in range(limit)]


def grow_tree(rows: list[dict], y: list[int], features: list[tuple[str, str, list[str] | None]],
              depth: int, min_loans: int, min_events: int) -> TreeResult:
    """`features`: (name, kind, levels) with kind numeric|categorical. Rows are
    dicts of feature name -> value (float for numeric, str for categorical)."""
    n = len(rows)
    total = sum(y)
    leaves: list[Leaf] = []
    first_split: list[str | None] = [None]

    def best_split(idx: list[int]):
        """One sorted sweep per numeric feature and one counting pass per
        categorical one; only the winning split materialises its two sides."""
        n_here = len(idx)
        e_here = sum(y[i] for i in idx)
        g_here = _gini(e_here, n_here)
        best = None   # (gain, feature, kind, cut_or_level, desc_left, desc_right, left_fn)
        for fname, kind, levels in features:
            if kind == "numeric":
                order = sorted(idx, key=lambda i: rows[i][fname])
                vals = [rows[i][fname] for i in order]
                cum = [0]
                for i in order:
                    cum.append(cum[-1] + y[i])
                cuts = _candidates(vals)
                pos = 0
                for cut in cuts:
                    while pos < n_here and vals[pos] < cut:
                        pos += 1
                    nl, nr = pos, n_here - pos
                    el, er = cum[pos], e_here - cum[pos]
                    gain = _score_counts(nl, el, nr, er, g_here, n_here)
                    if gain is not None and (best is None or gain > best[0]):
                        best = (gain, fname, kind, cut, f"{fname} < {cut:,.6g}", f"{fname} ≥ {cut:,.6g}",
                                (lambda i, f=fname, c=cut: rows[i][f] < c))
            else:
                counts: dict[str, list[int]] = {}
                for i in idx:
                    c = counts.setdefault(rows[i][fname], [0, 0])
                    c[0] += 1
                    c[1] += y[i]
                for lev in (levels or []):
                    nl, el = counts.get(lev, (0, 0))
                    nr, er = n_here - nl, e_here - el
                    gain = _score_counts(nl, el, nr, er, g_here, n_here)
                    if gain is not None and (best is None or gain > best[0]):
                        best = (gain, fname, kind, lev, f"{fname} = {lev}", f"{fname} ≠ {lev}",
                                (lambda i, f=fname, lv=lev: rows[i][f] == lv))
        if best is None:
            return None
        gain, fname, kind, cut, dl, dr, left_fn = best
        left = [i for i in idx if left_fn(i)]
        right = [i for i in idx if not left_fn(i)]
        return gain, fname, kind, cut, left, right, dl, dr

    def _score_counts(nl, el, nr, er, g_here, n_here):
        if nl < min_loans or nr < min_loans or el < min_events or er < min_events:
            return None
        g = (nl / n_here) * _gini(el, nl) + (nr / n_here) * _gini(er, nr)
        gain = g_here - g
        return gain if gain > 1e-12 else None

    def grow(idx: list[int], path: list[str], d: int):
        e = sum(y[i] for i in idx)
        if d >= depth:
            leaves.append(Leaf(path, len(idx), e))
            return
        best = best_split(idx)
        if best is None:
            leaves.append(Leaf(path, len(idx), e))
            return
        gain, fname, kind, cut, left, right, dl, dr = best
        if first_split[0] is None:
            first_split[0] = dl.split(" ")[0]
        grow(left, path + [dl], d + 1)
        grow(right, path + [dr], d + 1)

    grow(list(range(n)), [], 0)
    return TreeResult(leaves=leaves, overall_rate=(None if n == 0 else total / n), first_split=first_split[0],
                      loans=n, events=total)
