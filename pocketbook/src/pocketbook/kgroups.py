"""A column cut into K groups, tested against a reference group inside pockets:
docs/statistics.md B3, B4, B5 and B6, for capability 4b and 4e
(docs/capabilities-scope.md).

numpy only: there is no statsmodels or scipy on the bank's machine.

The data is one table per pocket (a stratum): for each of the K groups, how many
loans it holds there and how many of them went bad. `Pocket(loans, bad)`, two
arrays of length K. A pocket where no loan, or every loan, went bad says nothing
about the groups and adds nothing to any statistic here; neither does a pocket of
one loan. No other pocket is ever left out: the floors on Control (fewest loans,
fewest losses) govern per-pocket readings, and this is one pooled test, so a
pocket too small to read on its own still counts (the goal's rule, 4b).

B3  `association`: the K-group Mantel-Haenszel statistic, general association,
    on K - 1 degrees of freedom, as B3 writes it. Groups with no loan in any
    pocket that says something are left out of it, and its degrees of freedom
    fall with them; the result says how many it rests on.
B4  the same call: the trend statistic on 1 degree of freedom, with the scores
    given (the confirmatory run passes 1, 2, ... K: see `confirmatory`).
B5  `conditional_fit`: conditional logistic regression. Each pocket's own total
    of bad loans is conditioned out rather than estimated, so hundreds of thin
    pockets don't bias the odds ratios (B5, "Breaks when"). The conditional
    likelihood of one pocket, with the groups' loans exchangeable inside it, is

        L_h = exp(sum_k d_hk b_k) / D_h,   D_h = sum over (m_1..m_K), sum m_k = m_h,
                                                 of  prod_k C(R_hk, m_k) exp(m_k b_k)

    the standard recursive computation (Gail, Lubin & Rubinstein 1981) done group
    by group: D_h is the coefficient of t^m_h in prod_k sum_j C(R_hk, j) e^(j b_k) t^j,
    a product of K polynomials. To keep every number in range each polynomial is
    tilted into a binomial distribution (the saddle point), so the coefficient
    needed is a probability near the middle of its distribution, never a number
    of 300 digits. The first derivatives are d_hk - E[m_hk] and the second are
    minus the covariance of the m_hk, from the same polynomials.
    `score_test` is the score test of that model at "no effect", worked out
    from those derivatives. It is B3's statistic by another road, and a test
    holds the two equal to 1e-9.
    `unconditional_fit`: the ordinary logistic regression with one constant per
    pocket, for comparison and for the worked example; the confirmatory run
    does not use it (see `confirmatory`).
    `logistic`: Newton's method for any design, which unconditional_fit and the
    worked example in docs/scout-vs-measure.py both use.
B6  `concentration`: flag rate, capture and lift, on the loans given (the
    holdout's).

A group can be "not estimable": no bad loan in it, or only bad loans, across the
pockets that say something. Its odds ratio would be 0 or infinite. The fit then
does what the likelihood does at that limit: the group's loans are taken out of
their pockets, with their bad loans, and the rest is fitted. The block test still
uses the full likelihood at "no effect", and its K - 1 degrees of freedom.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

try:
    import numpy as np
except ImportError:             # OC-34: the cube starts without numpy; perm.numpy() says what is missing when used
    np = None

from . import stats


@dataclass
class Pocket:
    loans: np.ndarray        # per group
    bad: np.ndarray          # per group

    def __post_init__(self):
        self.loans = np.asarray(self.loans, dtype=float)
        self.bad = np.asarray(self.bad, dtype=float)

    @property
    def n(self) -> float:
        return float(self.loans.sum())

    @property
    def m(self) -> float:
        return float(self.bad.sum())

    def informative(self) -> bool:
        """Says something about the groups: two loans or more, some bad and some not."""
        return self.n >= 2 and 0 < self.m < self.n


def informative(pockets: list[Pocket]) -> list[Pocket]:
    return [p for p in pockets if p.informative()]


def p_normal(z: float) -> float:
    """Two-sided p-value of a z."""
    return math.erfc(abs(z) / math.sqrt(2.0))


# --------------------------------------------------------------------------
# B3 and B4


@dataclass
class Association:
    general: float | None          # B3's Q
    df: int                        # K - 1, less any group with no loan in a pocket that says something
    p_general: float | None
    trend: float | None            # B4's Q
    p_trend: float | None
    direction: int                 # +1: the bad rate climbs with the scores; -1: falls; 0: no trend statistic
    pockets: int                   # pockets it rests on (those that say something)
    groups_used: list[int] = field(default_factory=list)


def association(pockets: list[Pocket], scores) -> Association:
    """B3 and B4, pooled over the pockets, exactly as docs/statistics.md writes them."""
    use = informative(pockets)
    if not use:
        return Association(None, 0, None, None, None, 0, 0)
    K = len(use[0].loans)
    s = np.asarray(scores, dtype=float)
    present = [k for k in range(K) if any(p.loans[k] > 0 for p in use)]
    keep = present[:-1]                                   # K - 1 of the groups: which one is left out doesn't matter
    d = np.zeros(len(keep))
    V = np.zeros((len(keep), len(keep)))
    T = VT = 0.0
    for p in use:
        R, n, N, C = p.loans, p.bad, p.n, p.m
        E = R * C / N
        f = C * (N - C) / (N * N * (N - 1))
        d += (n - E)[keep]
        Rk = R[keep]
        V += f * (N * np.diag(Rk) - np.outer(Rk, Rk))
        T += float((s * (n - E)).sum())
        VT += f * (N * float((s * s * R).sum()) - float((s * R).sum()) ** 2)
    general = p_general = None
    if keep:
        general = float(d @ np.linalg.solve(V, d))
        p_general = stats.chi2_sf(general, len(keep))
    trend = p_trend = None
    direction = 0
    if VT > 0:
        trend = T * T / VT
        p_trend = stats.chi2_sf(trend, 1)
        direction = 1 if T > 0 else -1 if T < 0 else 0
    return Association(general, len(keep), p_general, trend, p_trend, direction, len(use), present)


# --------------------------------------------------------------------------
# B5: the conditional likelihood, one pocket at a time


def _log_choose(R: int, top: int) -> np.ndarray:
    """log C(R, j) for j = 0 .. top."""
    j = np.arange(1, top + 1, dtype=float)
    return np.concatenate([[0.0], np.cumsum(np.log((R - j + 1) / j))])


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _tilt(R: np.ndarray, b: np.ndarray, m: float) -> float:
    """The lambda at which the K binomials, each with odds e^(b_k + lambda), expect m bad loans in all."""
    lo, hi = -60.0 - float(b.max()), 60.0 - float(b.min())
    lam = math.log(m / (R.sum() - m)) - float((R * b).sum() / R.sum())
    lam = min(max(lam, lo), hi)
    for _ in range(200):
        p = _sigmoid(b + lam)
        g = float((R * p).sum()) - m
        if abs(g) < 1e-12 * max(m, 1.0):
            break
        if g > 0:
            hi = lam
        else:
            lo = lam
        if hi - lo < 1e-15:
            break
        slope = float((R * p * (1 - p)).sum())
        step = lam - g / slope if slope > 0 else (lo + hi) / 2
        lam = step if lo < step < hi else (lo + hi) / 2
    return lam


def _mul(a: np.ndarray, b: np.ndarray, top: int) -> np.ndarray:
    return np.convolve(a, b)[: top + 1]


def _prod(polys: list[np.ndarray], top: int) -> np.ndarray:
    out = np.ones(1)
    for q in polys:
        out = _mul(out, q, top)
    return out


def _coef(poly: np.ndarray, m: int) -> float:
    return float(poly[m]) if m < len(poly) else 0.0


def pocket_terms(p: Pocket, b: np.ndarray, second: bool = True):
    """One pocket's conditional log-likelihood at b (b for every group), its gradient and, with `second`, its
    Hessian: (loglik, grad, hess)."""
    K = len(p.loans)
    R = p.loans.astype(int)
    m = int(round(p.m))
    if not p.informative():
        return 0.0, np.zeros(K), np.zeros((K, K))
    lam = _tilt(p.loans, b, m)
    f, g, h = [], [], []
    for k in range(K):
        top = min(R[k], m)
        j = np.arange(top + 1, dtype=float)
        x = b[k] + lam
        log1p = math.log1p(math.exp(-abs(x))) + max(x, 0.0)        # log(1 + e^x)
        logpmf = _log_choose(R[k], top) + j * x - R[k] * log1p
        pmf = np.exp(logpmf)
        f.append(pmf)
        g.append(j * pmf)
        h.append(j * j * pmf)
    full = _prod(f, m)
    B = _coef(full, m)
    logD = math.log(B) + sum(float(R[k]) * (math.log1p(math.exp(-abs(b[k] + lam))) + max(b[k] + lam, 0.0))
                             for k in range(K)) - m * lam
    ll = float((p.bad * b).sum()) - logD
    others = [_prod([f[l] for l in range(K) if l != k], m) for k in range(K)]
    E = np.array([_coef(_mul(g[k], others[k], m), m) / B for k in range(K)])
    grad = p.bad - E
    if not second:
        return ll, grad, None
    cov = np.zeros((K, K))
    for k in range(K):
        cov[k, k] = _coef(_mul(h[k], others[k], m), m) / B - E[k] ** 2
        for l in range(k + 1, K):
            rest = _prod([f[q] for q in range(K) if q not in (k, l)], m)
            e_kl = _coef(_mul(_mul(g[k], g[l], m), rest, m), m) / B
            cov[k, l] = cov[l, k] = e_kl - E[k] * E[l]
    return ll, grad, -cov


def conditional_loglik(pockets: list[Pocket], b) -> float:
    """The conditional log-likelihood at b (one number per group, the reference's 0)."""
    b = np.asarray(b, dtype=float)
    return sum(pocket_terms(p, b, second=False)[0] for p in pockets)


def conditional_terms(pockets: list[Pocket], b):
    b = np.asarray(b, dtype=float)
    K = len(b)
    ll, grad, hess = 0.0, np.zeros(K), np.zeros((K, K))
    for p in pockets:
        a, g, h = pocket_terms(p, b)
        ll += a
        grad += g
        hess += h
    return ll, grad, hess


def loglik_at_zero(pockets: list[Pocket]) -> float:
    """At "no effect" every set of m loans is as likely as any other: log 1 / C(n, m) per pocket."""
    return -sum(math.lgamma(p.n + 1) - math.lgamma(p.m + 1) - math.lgamma(p.n - p.m + 1)
                for p in informative(pockets))


def score_test(pockets: list[Pocket], ref: int) -> tuple[float, int]:
    """The score test of the conditional logistic model at "no effect": U' I^-1 U, with U and I the conditional
    likelihood's own first derivatives and minus its second, at b = 0. (Q, degrees of freedom)."""
    use = informative(pockets)
    K = len(use[0].loans)
    present = [k for k in range(K) if any(p.loans[k] > 0 for p in use)]
    free = [k for k in present if k != ref] if ref in present else present[:-1]
    _, grad, hess = conditional_terms(use, np.zeros(K))
    U = grad[free]
    info = -hess[np.ix_(free, free)]
    return float(U @ np.linalg.solve(info, U)), len(free)


# --------------------------------------------------------------------------
# B5: the fit


CONDITIONAL = "conditional"
UNCONDITIONAL = "unconditional"


@dataclass
class Fit:
    method: str
    odds: list[float | None]          # per group; the reference's 1.0
    beta: list[float | None]          # ln of the odds ratio
    se: list[float | None]            # its standard error
    p: list[float | None]             # Wald's two-sided p-value
    loglik: float | None              # at the fit
    loglik0: float | None             # with no group effect
    block: float | None               # 2 (loglik - loglik0), the likelihood-ratio block test
    df: int
    p_block: float | None
    not_estimable: dict = field(default_factory=dict)      # group -> why, in words
    settled: bool = True              # Newton's method converged
    pockets: int = 0                  # pockets that say something

    def interval(self, k: int, z: float) -> tuple[float, float] | None:
        if self.beta[k] is None or self.se[k] is None:
            return None
        return math.exp(self.beta[k] - z * self.se[k]), math.exp(self.beta[k] + z * self.se[k])


NO_BAD = "no loan in it went bad, in the pockets that say something"
ALL_BAD = "every loan in it went bad, in the pockets that say something"
NO_LOANS = "no loans, in the pockets that say something"


def _boundary(pockets: list[Pocket], k: int) -> str | None:
    """Is group k's bad count at the least or the most its pockets allow? Then its odds ratio is 0 or infinite."""
    lo = hi = got = 0.0
    for p in pockets:
        R = p.loans[k]
        lo += max(0.0, p.m - (p.n - R))
        hi += min(R, p.m)
        got += p.bad[k]
    if hi == 0:
        return NO_LOANS
    if got <= lo:
        return NO_BAD
    if got >= hi:
        return ALL_BAD
    return None


def _drop(pockets: list[Pocket], k: int) -> list[Pocket]:
    """The limit of the likelihood as group k's odds go to 0 or infinity: its loans, and their bad loans, out."""
    out = []
    for p in pockets:
        loans, bad = p.loans.copy(), p.bad.copy()
        loans[k] = bad[k] = 0.0
        out.append(Pocket(loans, bad))
    return informative(out)


def conditional_fit(pockets: list[Pocket], ref: int, groups: int | None = None, max_iter: int = 100) -> Fit:
    """B5 by conditional logistic regression: an odds ratio for every group against `ref`, each with its
    standard error and Wald p-value, and the likelihood-ratio block test on K - 1 degrees of freedom."""
    use = informative(pockets)
    K = len(pockets[0].loans) if pockets else (groups or 0)
    none = [None] * K
    if not use:
        return Fit(CONDITIONAL, none, none, none, none, None, None, None, max(K - 1, 0), None,
                   {k: NO_LOANS for k in range(K)}, pockets=0)
    ll0 = loglik_at_zero(use)
    work = use
    gone: dict[int, str] = {}
    while True:                       # a group at its bound, one at a time: taking one out can move another
        hit = next(((k, why) for k in range(K) if k not in gone and (why := _boundary(work, k))), None)
        if hit is None:
            break
        gone[hit[0]] = hit[1]
        work = _drop(work, hit[0])
        if not work:
            break
    if ref in gone or not work:
        return Fit(CONDITIONAL, none, none, none, none, None, ll0, None, K - 1, None,
                   {**gone, **({} if ref in gone else {})}, pockets=len(use))
    free = [k for k in range(K) if k != ref and k not in gone]
    b = np.zeros(K)
    ll, grad, hess = conditional_terms(work, b)
    settled = False
    for _ in range(max_iter):
        if not free:
            settled = True
            break
        info = -hess[np.ix_(free, free)]
        step = np.linalg.solve(info, grad[free])
        t = 1.0
        while True:
            nb = b.copy()
            nb[free] += t * step
            nll, ngrad, nhess = conditional_terms(work, nb)
            if nll >= ll - 1e-12 or t < 1e-6:
                break
            t /= 2
        b, ll, grad, hess = nb, nll, ngrad, nhess
        if float(np.max(np.abs(t * step))) < 1e-10:
            settled = True
            break
    se = [None] * K
    if free:
        cov = np.linalg.inv(-hess[np.ix_(free, free)])
        for i, k in enumerate(free):
            se[k] = float(math.sqrt(cov[i, i]))
    beta = [0.0 if k == ref else float(b[k]) if k in free else None for k in range(K)]
    odds = [None if x is None else math.exp(x) for x in beta]
    pz = [None if (k == ref or se[k] is None) else p_normal(beta[k] / se[k]) for k in range(K)]
    block = 2.0 * (ll - ll0)
    return Fit(CONDITIONAL, odds, beta, se, pz, ll, ll0, block, K - 1, stats.chi2_sf(max(block, 0.0), K - 1),
               gone, settled, len(use))


# --------------------------------------------------------------------------
# The ordinary logistic regression


def logistic(X, y, weights=None, max_iter: int = 100):
    """Newton's method for the ordinary logistic regression with design X (a column of ones included when
    wanted), outcomes y (0 to 1: with `weights`, y is the share bad of that many loans). Returns
    (beta, standard errors, log-likelihood, settled)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.ones(len(y)) if weights is None else np.asarray(weights, dtype=float)
    beta = np.zeros(X.shape[1])

    def ll_of(bt):
        eta = X @ bt
        return float((w * (y * eta - (np.maximum(eta, 0) + np.log1p(np.exp(-np.abs(eta)))))).sum())

    ll = ll_of(beta)
    settled = False
    for _ in range(max_iter):
        p = _sigmoid(X @ beta)
        grad = X.T @ (w * (y - p))
        H = (X * (w * p * (1 - p))[:, None]).T @ X
        step = np.linalg.solve(H, grad)
        t = 1.0
        while True:
            nb = beta + t * step
            nll = ll_of(nb)
            if nll >= ll - 1e-12 or t < 1e-6:
                break
            t /= 2
        beta, ll = nb, nll
        if float(np.max(np.abs(t * step))) < 1e-10:
            settled = True
            break
    p = _sigmoid(X @ beta)
    H = (X * (w * p * (1 - p))[:, None]).T @ X
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return beta, se, ll, settled


def unconditional_fit(pockets: list[Pocket], ref: int, groups: int | None = None) -> Fit:
    """B5 as the ordinary logistic regression with one constant per pocket: grouped, one row per pocket and
    group. Biased when pockets are thin (B5, "Breaks when"); kept for comparison and for the tests."""
    use = informative(pockets)
    K = len(pockets[0].loans) if pockets else (groups or 0)
    none = [None] * K
    if not use:
        return Fit(UNCONDITIONAL, none, none, none, none, None, None, None, max(K - 1, 0), None, pockets=0)
    gone = {}
    work = use
    while True:
        hit = next(((k, why) for k in range(K) if k not in gone and (why := _boundary(work, k))), None)
        if hit is None:
            break
        gone[hit[0]] = hit[1]
        work = _drop(work, hit[0])
        if not work:
            break
    free = [k for k in range(K) if k != ref and k not in gone]
    H = len(work)
    rows, ys, ws = [], [], []
    for h, p in enumerate(work):
        for k in range(K):
            if p.loans[k] == 0:
                continue
            x = np.zeros(H + len(free))
            x[h] = 1.0
            if k in free:
                x[H + free.index(k)] = 1.0
            rows.append(x)
            ys.append(p.bad[k] / p.loans[k])
            ws.append(p.loans[k])
    X, y, w = np.array(rows), np.array(ys), np.array(ws)
    beta, se_, ll, settled = logistic(X, y, w)
    _, _, ll0, _ = logistic(X[:, :H], y, w)
    beta_k = [0.0 if k == ref else float(beta[H + free.index(k)]) if k in free else None for k in range(K)]
    se = [None if k not in free else float(se_[H + free.index(k)]) for k in range(K)]
    pz = [None if se[k] is None else p_normal(beta_k[k] / se[k]) for k in range(K)]
    block = 2.0 * (ll - ll0)
    return Fit(UNCONDITIONAL, [None if x is None else math.exp(x) for x in beta_k], beta_k, se, pz, ll, ll0, block,
               K - 1, stats.chi2_sf(max(block, 0.0), K - 1), gone, settled, len(use))


# --------------------------------------------------------------------------
# The Mantel-Haenszel odds ratio of one group against the reference: the cross-check


def mh_odds(pockets: list[Pocket], k: int, ref: int) -> float | None:
    tables = [(p.bad[k], p.loans[k] - p.bad[k], p.bad[ref], p.loans[ref] - p.bad[ref]) for p in pockets]
    return stats.mantel_haenszel(tables, 1.96)[0]


# --------------------------------------------------------------------------
# B6


@dataclass
class Concentration:
    loans: int
    flag_rate: float | None          # the group's loans / all loans
    bad: int
    capture: float | None            # its bad loans / all bad loans
    gco: float
    gco_capture: float | None        # its GCO / all GCO
    bad_rate: float | None
    lift: float | None               # its bad rate / the book's


def concentration(group: list, bad: list, gco: list, groups) -> Concentration:
    """B6 for the loans in `groups` (a group, or a set of them) against all the loans given. `group`, `bad` and
    `gco` are per loan; a loan's GCO of None is left out of the GCO figures only."""
    want = set(groups) if isinstance(groups, (set, frozenset, list, tuple)) else {groups}
    n = len(group)
    total_bad = sum(bad)
    total_gco = math.fsum(g for g in gco if g is not None)
    inside = [i for i in range(n) if group[i] in want]
    k = len(inside)
    kb = sum(bad[i] for i in inside)
    kg = math.fsum(gco[i] for i in inside if gco[i] is not None)
    book_rate = total_bad / n if n else None
    rate = kb / k if k else None
    return Concentration(loans=k, flag_rate=k / n if n else None, bad=kb,
                         capture=kb / total_bad if total_bad else None, gco=kg,
                         gco_capture=kg / total_gco if total_gco else None, bad_rate=rate,
                         lift=rate / book_rate if (rate is not None and book_rate) else None)
