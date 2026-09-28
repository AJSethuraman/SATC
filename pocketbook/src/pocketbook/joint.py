"""The joint model (OC-51; docs/statistics.md B10): every shortlisted input in one logistic regression on the held-back
loans, so each one's groups are read net of the others.

The firm, 27 Sep 2026: *"shouldn't it regress all of those identified variables if it actually deems them important?
import --> tree runs --> tree guesses on 2024 data if 2022-2023 are used to build branches --> regress shortlist?"*

    ln( p / (1 - p) ) = a_pocket + sum over inputs v, sum over groups k of v other than its reference  b_vk [loan in k]

One constant per pocket (the pockets the held-fixed columns make, cut as the grids cut them): the ordinary logistic
regression with the pockets as control dummies, not the conditional one. B10 in statistics.md says why and when that
stops being safe, and `MIN_BAD_PER_POCKET` is the line past which it refuses instead.

Per input: each group's odds ratio against its reference (Wald's p-value and standard error, the range drawn live on
the tab), and a likelihood ratio test for taking the input out, all its groups at once: what it adds net of every
other input and the pockets. Those p-values then get the run's allowance for testing many at once (Control's
"Allowing for testing many pockets at once"), across the shortlist.

The fit is on grouped rows (one per pocket and combination of groups, weighted by its loans), which is the loan-level
likelihood exactly. numpy only, as kgroups is: `kgroups.logistic` does Newton's method.

Where the likelihood has no finite answer it is not printed:
- a group with no held-back loan in the pockets that say something has no odds ratio;
- a group where no loan, or every loan, went bad sits at the limit the likelihood heads to (odds ratio 0 or
  infinite): as in kgroups, its loans are taken out with their bad loans and the rest is fitted, and the group is
  said to have no odds ratio;
- a group holding exactly the loans other groups already hold can't be told apart from them, and is said so;
- an input whose reference group has no loan, or no bad loan, or only bad loans, can't be compared with it, and is
  left out of the joint model, said so;
- a fit that still doesn't settle (a combination of groups with no bad loan or only bad loans) refuses the whole
  joint model in words.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field

from . import engine, kgroups, stats

#: the unconditional fit gives each pocket its own constant; below this many bad loans per pocket on average, those
#: constants are too thin to estimate without biasing the odds ratios (statistics.md B10), and the model refuses
MIN_BAD_PER_POCKET = 5
#: a coefficient past this (an odds ratio beyond e^15, about 3 million) or a standard error past MAX_SE is the fit
#: running off towards a limit: separation, refused rather than printed
#: why the joint model refuses when its fit runs off
DIDNT_SETTLE = ("the regression didn't settle on an answer: some combination of groups has no bad loan, or only "
                "bad loans, so its odds ratios would be meaningless")
MAX_BETA, MAX_SE = 15.0, 50.0
NO_LOANS = "no held-back loan is in it, in the pockets that say something"
NO_BAD = "no loan in it went bad, in the pockets that say something"
ALL_BAD = "every loan in it went bad, in the pockets that say something"
ALIASED = "it holds exactly the loans other candidates' groups hold, so it can't be told apart from them"


@dataclass
class Term:
    """One input in the joint model."""
    column: str
    groups: tuple[str, ...]
    ref: int
    odds: list[float | None] = field(default_factory=list)     # per group; the reference's 1.0
    beta: list[float | None] = field(default_factory=list)
    se: list[float | None] = field(default_factory=list)
    p: list[float | None] = field(default_factory=list)        # Wald's, two-sided, per group
    loans: list[int] = field(default_factory=list)             # held-back loans in the model, per group
    bad: list[int] = field(default_factory=list)
    lr: float | None = None                                    # 2 (loglik with it - without it)
    df: int = 0                                                # its groups estimated
    p_lr: float | None = None
    p_allowed: float | None = None                             # after the allowance, across the shortlist
    not_estimable: dict = field(default_factory=dict)          # group -> why, in words
    partners: list[tuple[str, float]] = field(default_factory=list)     # (column, rank correlation)
    problem: str | None = None                                 # why it isn't in the joint model


@dataclass
class Joint:
    terms: list[Term]
    strata: tuple[str, ...]
    loans: int = 0                   # held-back loans in the model
    bad: int = 0
    pockets: int = 0                 # pockets that say something
    quiet_loans: int = 0             # loans in pockets where none, or every one, went bad: they say nothing
    left_out: dict = field(default_factory=dict)
    loglik: float | None = None
    settled: bool = True
    allowance: str = "bh"
    problem: str | None = None

    @property
    def fitted(self) -> list[Term]:
        return [t for t in self.terms if t.problem is None]


# --------------------------------------------------------------------------
# The loans


NO_DATE, NO_OUTCOME = "no readable origination date", "no readable outcome"


def _no_value(column: str) -> str:
    return f"no readable value of {column}"


def _cells(res, ps, tests, labels):
    """The held-back loans as grouped rows: {(pocket, group of input 1, ..., group of input V): [loans, bad]}, and
    what was left out, by why (a loan is counted under the first reason only)."""
    from . import confirmatory
    read, why = confirmatory._reader(res)
    if read is None:
        return None, {}, why
    m = next((x for x in res.measures if x.name == "outcome_loans"), None)
    if m is None:
        return None, {}, "this run has no yes/no outcome"
    cfg = res.config
    col, rules = cfg.origination_date, cfg.missing
    left: dict[str, int] = {}
    cells: dict[tuple, list[int]] = {}
    for r, st in zip(res.table.rows, labels):
        d = confirmatory._date_or_none(read(r.get(col)))
        if d is None or not ps.holdout.holds(d):
            continue                                   # only the held-back loans; the rest aren't this model's
        y = confirmatory.outcome_of(r.get(m.flag), m, rules)
        if y is None:
            left[NO_OUTCOME] = left.get(NO_OUTCOME, 0) + 1
            continue
        key = [st]
        for t in tests:
            v, bad_v = engine.classify_number(r.get(t.column), rules.get(t.column))
            if bad_v:
                key = None
                left[_no_value(t.column)] = left.get(_no_value(t.column), 0) + 1
                break
            key.append(bisect.bisect_right(t.bins, v))
        if key is None:
            continue
        c = cells.setdefault(tuple(key), [0, 0])
        c[0] += 1
        c[1] += y
    return cells, left, None


# --------------------------------------------------------------------------
# One fit


@dataclass
class _Fit:
    loglik: float
    beta: dict                       # (term index, group) -> coefficient
    se: dict
    settled: bool
    gone: dict                       # (term index, group) -> why it has no odds ratio
    pockets: int
    loans: int
    bad: int
    quiet: int
    problem: str | None = None


def _fit(cells: dict, terms: list[Term], use: list[int]) -> _Fit:
    """The unconditional logistic regression with one constant per pocket and the groups of the inputs in `use` (term
    indexes), on the grouped rows. Groups at a limit are taken out as kgroups does; aliased ones are dropped."""
    import numpy as np
    work = [(k, n, b) for k, (n, b) in cells.items()]
    gone: dict[tuple[int, int], str] = {}
    while True:
        # the pockets that say something: some bad and some not
        per: dict = {}
        for k, n, b in work:
            x = per.setdefault(k[0], [0, 0])
            x[0] += n
            x[1] += b
        live = {s for s, (n, b) in per.items() if 0 < b < n}
        quiet = sum(n for s, (n, b) in per.items() if s not in live)
        work = [(k, n, b) for k, n, b in work if k[0] in live]
        hit = None
        for i in use:
            t = terms[i]
            for g in range(len(t.groups)):
                if g == t.ref or (i, g) in gone:
                    continue
                n = sum(nn for k, nn, _ in work if k[1 + i] == g)
                b = sum(bb for k, _, bb in work if k[1 + i] == g)
                if n == 0:
                    gone[(i, g)] = NO_LOANS
                elif b == 0 or b == n:
                    hit = (i, g, NO_BAD if b == 0 else ALL_BAD)
                    break
            if hit:
                break
        if hit is None:
            break
        i, g, why = hit
        gone[(i, g)] = why
        work = [(k, n, b) for k, n, b in work if k[1 + i] != g]       # the limit: its loans and bad loans out
    pockets = sorted({k[0] for k, _, _ in work}, key=repr)
    loans, bad = sum(n for _, n, _ in work), sum(b for _, _, b in work)
    if not work:
        return _Fit(0.0, {}, {}, True, gone, 0, 0, 0, quiet, "no pocket holds both a bad loan and a good one")
    where = {s: j for j, s in enumerate(pockets)}
    cols = [(i, g) for i in use for g in range(len(terms[i].groups))
            if g != terms[i].ref and (i, g) not in gone]
    X = np.zeros((len(work), len(pockets) + len(cols)))
    for r, (k, _, _) in enumerate(work):
        X[r, where[k[0]]] = 1.0
        for j, (i, g) in enumerate(cols):
            if k[1 + i] == g:
                X[r, len(pockets) + j] = 1.0
    w = np.array([n for _, n, _ in work], dtype=float)
    y = np.array([b / n for _, n, b in work], dtype=float)
    # aliased groups: a column the pockets and the groups before it already make
    keep = list(range(len(pockets)))
    rank = np.linalg.matrix_rank(X[:, keep]) if keep else 0
    for j, ig in enumerate(cols):
        trial = keep + [len(pockets) + j]
        got = np.linalg.matrix_rank(X[:, trial])
        if got > rank:
            keep, rank = trial, got
        else:
            gone[ig] = ALIASED
    cols = [ig for ig in cols if ig not in gone]
    X = X[:, keep]
    try:
        beta, se, ll, settled = kgroups.logistic(X, y, w)
    except np.linalg.LinAlgError:
        # the columns were checked independent above, so the solver only breaks down when the fit runs off towards
        # a combination with no bad loan (or only bad): the same case as not settling, and said the same way on
        # every machine (found 28 Sep 2026: CI's numpy failed here where this machine's ran off without settling)
        return _Fit(0.0, {}, {}, False, gone, len(pockets), loans, bad, quiet, DIDNT_SETTLE)
    b = {ig: float(beta[len(pockets) + j]) for j, ig in enumerate(cols)}
    s = {ig: float(se[len(pockets) + j]) for j, ig in enumerate(cols)}
    wild = [ig for ig in cols if not (math.isfinite(b[ig]) and math.isfinite(s[ig]))
            or abs(b[ig]) > MAX_BETA or s[ig] > MAX_SE]
    problem = None
    if not settled or wild:
        problem = DIDNT_SETTLE
    return _Fit(float(ll), b, s, settled, gone, len(pockets), loans, bad, quiet, problem)


# --------------------------------------------------------------------------
# The joint model


def run(res, ps, tests, labels, allowance: str = "bh") -> Joint:
    """The joint model of every input that ran (`tests`, confirmatory.run_tests's), on the pre-spec's held-back loans,
    with its strata's pockets (`labels`, one per extract row) held fixed."""
    ran = [t for t in tests if t.problem is None]
    terms = [Term(t.column, tuple(t.groups), t.ref) for t in ran]
    j = Joint(terms=terms, strata=tuple(ps.strata), allowance=allowance)
    if len(ran) < 2:
        j.problem = ("the shortlist holds one candidate, so there is nothing to read it net of" if ran else
                     "no candidate could be tested")
        return j
    if labels is None:
        j.problem = "the loans can't be cut into the pockets the pre-spec holds fixed"
        return j
    cells, j.left_out, why = _cells(res, ps, ran, labels)
    if cells is None:
        j.problem = why
        return j
    fit_cells(j, cells)
    if j.problem is None:
        _partners(res, ps, j)
    return j


def fit_cells(j: Joint, cells: dict) -> Joint:
    """The joint model on grouped rows already read: {(pocket, group of term 1, ..., group of term V): [loans, bad]}.
    Fills `j` (its terms, in the order of the groups in the keys) and returns it."""
    terms = j.terms
    # an input whose reference can't be compared with: out of the joint model, said so
    use = []
    for i, t in enumerate(terms):
        n = sum(nn for k, (nn, _) in cells.items() if k[1 + i] == t.ref)
        b = sum(bb for k, (_, bb) in cells.items() if k[1 + i] == t.ref)
        if n == 0 or b == 0 or b == n:
            what = "has no held-back loan" if n == 0 else "has no bad loan" if b == 0 else "has only bad loans"
            t.problem = f"its reference group, {t.groups[t.ref]}, {what}, so nothing can be compared with it"
        else:
            use.append(i)
    if len(use) < 2:
        j.problem = ("only one candidate's reference group can be compared with, so there is nothing to read it "
                     "net of" if use else "no candidate's reference group can be compared with")
        return j
    full = _fit(cells, terms, use)
    j.loans, j.bad, j.pockets, j.quiet_loans = full.loans, full.bad, full.pockets, full.quiet
    j.loglik, j.settled = full.loglik, full.settled
    if full.problem:
        j.problem = full.problem
        return j
    if full.pockets and full.bad / full.pockets < MIN_BAD_PER_POCKET:
        j.problem = (f"the pockets are too thin for a constant each: {full.bad:,} bad loans across {full.pockets:,} "
                     f"pockets, under {MIN_BAD_PER_POCKET} a pocket. Hold fewer columns fixed, or cut them into fewer "
                     f"bands")
        return j
    for i in use:
        t = terms[i]
        K = len(t.groups)
        t.odds, t.beta, t.se, t.p = [None] * K, [None] * K, [None] * K, [None] * K
        t.odds[t.ref], t.beta[t.ref] = 1.0, 0.0
        for g in range(K):
            if (i, g) in full.gone:
                t.not_estimable[g] = full.gone[(i, g)]
            elif g != t.ref:
                b, s = full.beta[(i, g)], full.se[(i, g)]
                t.beta[g], t.se[g], t.odds[g], t.p[g] = b, s, math.exp(b), kgroups.p_normal(b / s)
        t.df = sum(1 for g in range(K) if g != t.ref and t.beta[g] is not None)
        t.loans = [sum(n for k, (n, _) in cells.items() if k[1 + i] == g) for g in range(K)]
        t.bad = [sum(b for k, (_, b) in cells.items() if k[1 + i] == g) for g in range(K)]
        if t.df:
            without = _fit(cells, terms, [x for x in use if x != i])
            if without.problem is None:
                t.lr = max(2.0 * (full.loglik - without.loglik), 0.0)
                t.p_lr = stats.chi2_sf(t.lr, t.df)
    adjusted = engine.adjust([t.p_lr for t in terms], j.allowance)
    for t, p in zip(terms, adjusted):
        t.p_allowed = p
    return j


def _ranks(v):
    """Ranks 1 to n, ties given their average (as scipy's rankdata does), numpy only."""
    import numpy as np
    order = np.argsort(v, kind="mergesort")
    r = np.empty(len(v), dtype=float)
    r[order] = np.arange(1, len(v) + 1, dtype=float)
    _, inv = np.unique(v, return_inverse=True)
    return (np.bincount(inv, r) / np.bincount(inv))[inv]


def _partners(res, ps, j: Joint) -> None:
    """Pairs whose values rise and fall together, as scouting flags them (scout.CORRELATED, Spearman's rank
    correlation on the development loans with both values), among the inputs and the held-fixed number columns. Said
    beside both inputs."""
    import numpy as np
    from . import confirmatory, scout
    read, _ = confirmatory._reader(res)
    if read is None:
        return
    cfg = res.config
    col = cfg.origination_date
    bands = {b.field for b in cfg.bands}
    names = [t.column for t in j.terms] + [s for s in j.strata if s in bands]
    held = set(j.strata)
    vals = {c: [] for c in names}
    for r in res.table.rows:
        d = confirmatory._date_or_none(read(r.get(col)))
        if d is None or not ps.development.holds(d):
            continue
        for c in names:
            v, bad_v = engine.classify_number(r.get(c), cfg.missing.get(c))
            vals[c].append(np.nan if bad_v else v)
    arr = {c: np.array(v, dtype=float) for c, v in vals.items()}
    by = {t.column: t for t in j.terms}
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            na, nb = names[a], names[b]
            if na not in by and nb not in by:
                continue
            both = ~np.isnan(arr[na]) & ~np.isnan(arr[nb])
            if both.sum() < 3:
                continue
            ra, rb = _ranks(arr[na][both]), _ranks(arr[nb][both])
            if ra.std() == 0 or rb.std() == 0:
                continue
            rho = float(np.corrcoef(ra, rb)[0, 1])
            if abs(rho) >= scout.CORRELATED:
                if na in by:
                    by[na].partners.append((nb + (" (held fixed)" if nb in held else ""), rho))
                if nb in by:
                    by[nb].partners.append((na + (" (held fixed)" if na in held else ""), rho))
