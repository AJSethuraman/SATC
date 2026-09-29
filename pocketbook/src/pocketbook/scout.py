"""Scouting (Goal 2 item 9; capability 4a; docs/statistics.md B7): find, on the development loans only, which of the
columns ticked Test it the book leans on, and where each one bends; then write the pre-spec the confirmation reads.

The firm, 26 Sep 2026: scouting is "to try and guess importance ... it should be wider", and "dates are for the
scouting pipeline" (OC-39). Wide: dozens of candidates. The confirmation stays narrow: the shortlist, on the loans
held back.

WHAT IT READS. The analyst picks a cutoff date on Control (OC-51; suggested, never pre-chosen: `suggest_cutoff`, the
month start nearest 70% of the loans). Loans made before it are the development loans; loans made on or after it are
held back. Only the dates of the held-back loans are read, to draw the line and to name the holdout's range in the
pre-spec; their outcome and every other value are never read by `run`. `development_rows` picks the development
loans from the dates alone, and everything after it sees only those. A test changes every held-back outcome and gets
the identical shortlist.

THE TREE'S OUT-OF-TIME CHECK (OC-51; the firm, 27 Sep 2026: "tree guesses on 2024 data if 2022-2023 are used to build
branches"). `out_of_time`, called only after the pre-spec is written and read: forests grown on every development
loan, with the held-fixed columns and without them, score the held-back loans, and their AUC there is set beside the
cross-fitted AUC on the development loans. It is a touch of the holdout, and Record's Log says so.

WHAT IT DOES, as docs/scout-vs-measure.py does it, with the changes said in `docs/design.md` OC-50:
- Candidates: the columns ticked Test it, and every new column made on Columns (one column divided by another),
  fed in as columns in their own right. A category is given one number per value, in the order of the values.
- A random forest (scikit-learn, an optional add-on) ranks them by permutation importance: on loans the forest did
  not train on, how far its AUC drops when one column is shuffled. Cross-fitted: the development loans are cut
  into FOLDS runs by origination date, each run is scored by a forest grown on the others, and the drops are
  averaged, so every development loan is scored once.
- Twice: once with the candidates alone, once with the Hold fixed columns in the model as well (the firm, 26 Sep
  2026: "test a set once with and once without").
- The noise floor: the same forests grown on the development loans with their outcomes shuffled, so no column can
  matter. The floor is the largest importance any candidate reached there, over at least MIN_NULL_DRAWS draws.
- Proposed for the shortlist: a number column whose importance clears the floor with the held-fixed columns in the
  model or without them, and whose shape bends somewhere to cut at.
- The shape: partial dependence (the model's bad rate with the column set to one value for every loan) over the
  column's own quantiles, from a forest grown on every development loan (with the held-fixed columns when there
  are any, as the confirmation holds them fixed). Bins go where the curve steps by at least STEP of its average,
  largest step first, each group holding at least MIN_SHARE of the development loans, at most MAX_GROUPS groups.
  Inside each step the edge sits where the forest itself split that column most (its own splits, weighted by how
  much each split separated bad from good), rounded to two significant figures. The reference is the group
  holding the development loans' median, as the example pre-spec's is.
- Strongly correlated pairs: rank correlation (Spearman's) of at least CORRELATED, either way, on the development
  loans that have both values, among the number candidates and the held-fixed number columns.

Seeded (SEED) and repeatable: the same extract and choices give the same forests, the same shortlist and the same
file, byte for byte on the same day (the file carries the day it was written). scikit-learn's forests are not
bit-identical across its versions, so the version is recorded.

THE FILE. `write` puts the pre-spec beside the workbook (`prespec_for`) only when none is there. One that is there
is confirmed as it stands: an edit is the analyst's to make, and Record labels a change made after a held-back run
(OC-47). The Scouting tab says where it differs from this Run's proposal. With no Hold fixed column chosen, `strata`
reads [CONFIRM: ...] (OC-13: it is suggested and left blank), which the file refuses until it is answered.
"""

from __future__ import annotations

import bisect
import importlib.util
import math
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from . import engine, prespec

SHEET = "Scouting"
NUMBER, CATEGORY = "number", "category"
#: the forest (scout-vs-measure.py grew 400 trees with leaves of at least 40 loans; see OC-50 for why 200)
TREES, LEAF, SEED = 200, 40, 7
FOLDS = 3                                  # cross-fitted by origination date
REPEATS = 5                                # shuffles of each column per fold
MIN_NULL_DRAWS = 20                        # the noise floor is the largest of at least this many null importances
CORRELATED = 0.7                           # |rank correlation| at or above this flags a pair
QUANTILES = (1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 75, 80, 85, 90, 92.5, 95, 97, 98, 99)
STEP = 0.25                                # a bend: the curve steps by at least this share of its average
MIN_SHARE = 0.02                           # each suggested group holds at least this share of development loans
MAX_GROUPS = 6
PD_ROWS = 1000                             # the development loans partial dependence averages over (a seeded draw)
PIP, MODULE = "scikit-learn", "sklearn"
CONFIRM_STRATA = ('"[CONFIRM: the columns to hold fixed, such as [FICO, CHANNEL]; [] for none]"')

#: why a candidate was or wasn't proposed, as its row says it (the rule is said once, in the method note)
CLEARS, BELOW, NO_BEND, A_CATEGORY, TOO_FEW = ("clears the noise floor", "below the noise floor", "no bend to cut at",
                                               "a category", "too few values")


class ScoutMissing(Exception):
    """scikit-learn isn't installed: finding is refused in words; confirming a saved shortlist still works."""


def missing() -> str | None:
    """The sentence a Run and the launcher say when scikit-learn isn't here; None when it is. Looked for without
    loading it (deps.py's rule)."""
    try:
        there = importlib.util.find_spec(MODULE) is not None
    except (ImportError, ValueError):
        import sys
        there = sys.modules.get(MODULE) is not None
    if there:
        return None
    return (f"Finding new variables needs one add-on: {PIP}, which grows the random forest that ranks them. Install "
            f"it from the launcher (Choose tests, Install {PIP}), or confirm a saved shortlist instead.")


def version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version(PIP)
    except Exception:  # noqa: BLE001 - only recorded
        return "unknown"


@dataclass
class Candidate:
    name: str
    kind: str                                  # NUMBER or CATEGORY
    importance: float | None = None            # without the held-fixed columns in the model
    importance_held: float | None = None       # with them; None when nothing is held fixed
    loans: int = 0                             # development loans with a readable value
    bins: tuple[float, ...] = ()
    groups: tuple[str, ...] = ()
    reference_index: int | None = None
    curve: list[tuple[float, float]] = field(default_factory=list)     # (value, the model's bad rate)
    partners: list[tuple[str, float]] = field(default_factory=list)    # (column, rank correlation)
    proposed: bool = False
    why: str = ""
    rank: int = 0

    @property
    def reference(self) -> str | None:
        return self.groups[self.reference_index] if self.reference_index is not None and self.groups else None

    @property
    def best(self) -> float:
        vals = [v for v in (self.importance, self.importance_held) if v is not None]
        return max(vals) if vals else -math.inf


@dataclass
class Scouting:
    outcome: str
    hold: tuple[str, ...]
    cutoff: date | None
    candidates: list[Candidate] = field(default_factory=list)          # ranked
    held: list[tuple[str, float]] = field(default_factory=list)        # the held-fixed columns' own importance
    floor: float | None = None
    draws: int = 0
    development: prespec.DateRange | None = None
    holdout: prespec.DateRange | None = None
    n_dev: int = 0
    n_dev_bad: int = 0
    n_held_back: int = 0                       # loans made after the development range: counted by date, never read
    left_out: dict[str, int] = field(default_factory=dict)
    auc: float | None = None
    auc_held: float | None = None
    confidence: float = 0.95
    version: str = ""
    problem: str | None = None
    # the file (write)
    path: Path | None = None
    text: str = ""                             # what this Run's scouting proposes, as a file
    action: str = ""                           # WROTE, KEPT or SAME
    differs: list[str] = field(default_factory=list)
    fingerprint: str = ""
    written_on: date | None = None
    #: the tree's out-of-time check (`out_of_time`), once the pre-spec is written; None before, or when not run
    oot: "OutOfTime | None" = None
    #: kept from `run` for `out_of_time`: the forests grown on every development loan, and each category's values
    forests: dict = field(default_factory=dict, repr=False)
    levels: dict = field(default_factory=dict, repr=False)

    @property
    def proposed(self) -> list[Candidate]:
        return [c for c in self.candidates if c.proposed]


@dataclass
class OutOfTime:
    """The tree on loans it never saw: forests grown on every development loan score the held-back loans."""
    held_back: prespec.DateRange | None       # when the held-back loans scored were made
    loans: int = 0                             # held-back loans scored (a readable outcome)
    bad: int = 0
    auc: float | None = None                   # the candidates alone
    auc_held: float | None = None              # with the held-fixed columns; None when nothing is held fixed
    left_out: dict[str, int] = field(default_factory=dict)
    problem: str | None = None
    #: what the AUCs were worked out from, for a test to check them independently
    y: object = field(default=None, repr=False)
    scores: object = field(default=None, repr=False)
    scores_held: object = field(default=None, repr=False)


WROTE, KEPT, SAME = "wrote", "kept", "same"


# --------------------------------------------------------------------------
# The loans


#: the share of loans the suggested cutoff sits nearest (the launcher's old "Find on 70%"; OC-51 keeps it only here)
SUGGEST_SHARE = 0.7
#: Control's cutoff options that are worked out from the dates, by the share of loans each sits nearest
CUTOFF_SHARES = {"calc": SUGGEST_SHARE, "calc80": 0.8}


def suggest_cutoff(dates, share: float = SUGGEST_SHARE) -> date | None:
    """The suggested cutoff (OC-51, OC-13: shown beside the setting, never chosen for you): the first day of a month,
    the one nearest the date by which `share` of the loans had been made, keeping at least one loan on each side.
    None when there aren't two dated loans on different days."""
    dated = sorted(d for d in dates if d is not None)
    if len(dated) < 2 or dated[0] == dated[-1]:
        return None
    at = dated[max(1, math.ceil(share * len(dated))) - 1]
    this = at.replace(day=1)
    nxt = (this + timedelta(days=32)).replace(day=1)
    picks = sorted((this, nxt), key=lambda d: (abs((d - at).days), d))
    for d in picks:
        if dated[0] < d <= dated[-1]:
            return d
    return dated[-1]                          # every loan in one month or two: the last day still leaves one each side


def development_rows(res, cutoff: date) -> tuple[list[int], date, date, date, int, str | None]:
    """The development loans: those with a readable origination date before `cutoff`. Returns (their row numbers in
    date order, the first date of all, the day before the cutoff, the last date of all, how many loans were made on
    or after the cutoff, why not). Reads the dates and nothing else."""
    from .confirmatory import _date_or_none, _reader
    read, why = _reader(res)
    if read is None:
        return [], None, None, None, 0, f"the loans can't be split into development and held back: {why}"
    if cutoff is None:
        return [], None, None, None, 0, "no cutoff date is chosen on Control"
    col = res.config.origination_date
    dated = []
    for i, r in enumerate(res.table.rows):
        d = _date_or_none(read(r.get(col)))
        if d is not None:
            dated.append((d, i))
    if not dated:
        return [], None, None, None, 0, "no loan has a readable origination date"
    dated.sort()
    dev = [i for d, i in dated if d < cutoff]
    after = len(dated) - len(dev)
    if not dev:
        return [], None, None, None, 0, (f"no loan was made before the cutoff, {cutoff.isoformat()}: the first was "
                                         f"made {dated[0][0].isoformat()}")
    if not after:
        return [], None, None, None, 0, (f"no loan was made on or after the cutoff, {cutoff.isoformat()}: the last "
                                         f"was made {dated[-1][0].isoformat()}, so none is left to hold back")
    return dev, dated[0][0], cutoff - timedelta(days=1), dated[-1][0], after, None


def _kind(res, name: str) -> str:
    from . import meanings
    code = (res.config.columns or {}).get(name)
    code = code[0] if isinstance(code, (tuple, list)) else code
    cat = meanings.catalog()
    if code in cat and cat[code].cut == "dimension":
        return CATEGORY
    return NUMBER


def candidates_of(res, chosen) -> list[str]:
    """The columns ticked Test it, then every new column (one divided by another) not already among them, never an
    outcome or a held-fixed column."""
    hold = set(chosen.hold or ())
    outcome = chosen.outcome
    out = []
    for c in list(chosen.test or ()) + [d.name for d in res.config.derived]:
        if c not in out and c not in hold and c != outcome:
            out.append(c)
    return out


def _values(res, rows: list[dict], name: str, kind: str, levels: list[str] | None = None):
    """One column over the development loans, as numbers (a category as its value's place in sorted order), NaN
    where unreadable. `levels`: a category's values as the development loans have them, for the held-back loans
    (a value they never had is NaN)."""
    import numpy as np
    rule = res.config.missing.get(name)
    if kind == NUMBER:
        vals = [engine.classify_number(r.get(name), rule) for r in rows]
        return np.array([v if why is None else np.nan for v, why in vals], dtype=float), None
    labels = [engine.classify_text(r.get(name), rule) for r in rows]
    blank = {engine.BLANK_LABEL, engine.MISSING_RULE_LABEL}
    if levels is None:
        levels = sorted({x for x in labels if x not in blank})
    where = {x: i for i, x in enumerate(levels)}
    return np.array([where.get(x, np.nan) for x in labels], dtype=float), levels


# --------------------------------------------------------------------------
# The forest


def _forest(seed: int = SEED):
    from sklearn.ensemble import RandomForestClassifier
    return RandomForestClassifier(n_estimators=TREES, min_samples_leaf=LEAF, random_state=seed, n_jobs=-1)


def proba(rf, X):
    """The forest's bad rate for each loan: every tree's, added up in the trees' own order. scikit-learn's own
    predict_proba adds the trees up in whichever order its threads finish, so the last digit can differ from one
    Run to the next (found 27 Sep 2026: the partial dependence of an unchanged book differed in its 17th figure);
    here the trees run in threads too, but the sum is always taken in the same order."""
    import numpy as np
    from concurrent.futures import ThreadPoolExecutor
    X32 = np.ascontiguousarray(X, dtype=np.float32)
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 1) as pool:
        parts = list(pool.map(lambda est: est.predict_proba(X32, check_input=False)[:, 1], rf.estimators_))
    return np.sum(np.vstack(parts), axis=0) / len(parts)


def _auc(y, p) -> float | None:
    from sklearn.metrics import roc_auc_score
    if y.min() == y.max():
        return None
    return float(roc_auc_score(y, p))


def importances(X, y, seed: int = SEED) -> tuple[list[float], float | None]:
    """Each column's permutation importance, cross-fitted over FOLDS runs of the loans in date order: the drop in
    AUC when the column is shuffled, on loans the forest didn't train on, REPEATS shuffles a fold, averaged. Also
    the cross-fitted AUC."""
    import numpy as np
    n, m = X.shape
    bounds = [round(n * i / FOLDS) for i in range(FOLDS + 1)]
    drops = np.zeros((FOLDS, m))
    aucs = []
    rng = np.random.default_rng(seed)
    for f in range(FOLDS):
        va = np.zeros(n, dtype=bool)
        va[bounds[f]:bounds[f + 1]] = True
        Xv, yv = X[va], y[va]
        if y[~va].min() == y[~va].max() or yv.min() == yv.max():
            continue
        rf = _forest(seed).fit(X[~va], y[~va])
        base = _auc(yv, proba(rf, Xv))
        aucs.append(base)
        nv = len(yv)
        for j in range(m):
            stack = np.tile(Xv, (REPEATS, 1))
            for k in range(REPEATS):
                stack[k * nv:(k + 1) * nv, j] = rng.permutation(Xv[:, j])
            p = proba(rf, stack)
            drops[f, j] = np.mean([base - _auc(yv, p[k * nv:(k + 1) * nv]) for k in range(REPEATS)])
    used = len(aucs)
    if not used:
        return [None] * m, None
    return [float(x) for x in drops.sum(axis=0) / used], float(np.mean(aucs))


def noise_floor(X, y, seed: int = SEED) -> tuple[float | None, int]:
    """The largest importance any candidate reached with the outcomes shuffled among the development loans, over
    enough shuffles for at least MIN_NULL_DRAWS draws: what a column that cannot matter scores by chance."""
    import numpy as np
    m = X.shape[1]
    runs = max(1, math.ceil(MIN_NULL_DRAWS / m))
    rng = np.random.default_rng(seed + 1000)
    draws = []
    for _ in range(runs):
        got, _ = importances(X, rng.permutation(y), seed)
        draws += [v for v in got if v is not None]
    return (max(draws) if draws else None), len(draws)


# --------------------------------------------------------------------------
# The shape, and the bins


def _grid(v) -> list[float]:
    import numpy as np
    seen = v[~np.isnan(v)]
    if not len(seen):
        return []
    return sorted({float(x) for x in np.quantile(seen, [q / 100 for q in QUANTILES])})


def curve(rf, X, j: int, grid: list[float], seed: int = SEED) -> list[float]:
    """Partial dependence: the forest's average bad rate with column j set to each grid value on PD_ROWS development
    loans (a seeded draw), every other column as the loan has it."""
    import numpy as np
    rng = np.random.default_rng(seed + 2000 + j)
    S = X[rng.choice(len(X), min(PD_ROWS, len(X)), replace=False)] if len(X) > PD_ROWS else X
    stack = np.tile(S, (len(grid), 1))
    for i, x in enumerate(grid):
        stack[i * len(S):(i + 1) * len(S), j] = x
    p = proba(rf, stack)
    return [float(x) for x in p.reshape(len(grid), len(S)).mean(axis=1)]


def _shares(v, grid: list[float]) -> list[float]:
    """The share of development loans (with a value) nearest each grid point."""
    import numpy as np
    seen = v[~np.isnan(v)]
    mids = [(a + b) / 2 for a, b in zip(grid, grid[1:])]
    counts = [0] * len(grid)
    for x in seen:
        counts[bisect.bisect_right(mids, x)] += 1
    total = sum(counts) or 1
    return [c / total for c in counts]


def steps(pd: list[float], w: list[float]) -> list[int]:
    """Where the curve steps: each returned i cuts between grid points i and i + 1. Largest step first (the
    split that best separates the curve, weighted by loans), kept only while its two sides differ by at least STEP
    of the curve's average and each side holds at least MIN_SHARE of the loans, at most MAX_GROUPS groups."""
    total = sum(w)
    if total <= 0 or len(pd) < 2:
        return []
    mean = sum(a * b for a, b in zip(pd, w)) / total
    if mean <= 0:
        return []
    cuts: list[int] = []
    segs = [(0, len(pd))]

    def wmean(a, b):
        ww = sum(w[a:b])
        return (sum(pd[i] * w[i] for i in range(a, b)) / ww) if ww > 0 else None, ww

    while len(cuts) + 1 < MAX_GROUPS:
        best = None
        for a, b in segs:
            for s in range(a + 1, b):
                (ml, wl), (mr, wr) = wmean(a, s), wmean(s, b)
                if ml is None or mr is None or wl < MIN_SHARE or wr < MIN_SHARE:
                    continue
                if abs(ml - mr) < STEP * mean:
                    continue
                gain = wl * wr / (wl + wr) * (ml - mr) ** 2
                if best is None or gain > best[0]:
                    best = (gain, a, s, b)
        if best is None:
            break
        _, a, s, b = best
        segs.remove((a, b))
        segs += [(a, s), (s, b)]
        cuts.append(s - 1)
    return sorted(cuts)


def forest_splits(rf, j: int) -> list[tuple[float, float]]:
    """Every split the forest made on column j: (its threshold, how much it separated bad from good: the node's
    impurity less its children's, weighted by their loans)."""
    out = []
    for est in rf.estimators_:
        t = est.tree_
        for node in range(t.node_count):
            if t.feature[node] != j:
                continue
            l, r = t.children_left[node], t.children_right[node]
            gain = (t.weighted_n_node_samples[node] * t.impurity[node]
                    - t.weighted_n_node_samples[l] * t.impurity[l] - t.weighted_n_node_samples[r] * t.impurity[r])
            out.append((float(t.threshold[node]), max(float(gain), 0.0)))
    return out


def round_edge(x: float, lo: float, hi: float) -> float:
    """x at two significant figures, or as few more as keep it above lo and at or below hi."""
    if x == 0:
        return 0.0
    for sig in range(2, 8):
        r = float(f"{x:.{sig}g}")
        if lo < r <= hi:
            return r
    return x


def edge(splits: list[tuple[float, float]], lo: float, hi: float) -> float:
    """Where a step between grid values lo and hi sits: the forest's own splits there, the weighted median of their
    thresholds; the midpoint when it made none there. Rounded (round_edge)."""
    inside = sorted((t, g) for t, g in splits if lo < t <= hi and g > 0)
    if inside:
        half = sum(g for _, g in inside) / 2
        run = 0.0
        for t, g in inside:
            run += g
            if run >= half:
                x = t
                break
    else:
        x = (lo + hi) / 2
    # a forest threshold sits halfway between two values it saw; a loan at `hi` must land above the edge
    return round_edge(x, lo, hi)


def merge_small(bins: list[float], v, grid: list[float], pd: list[float]) -> list[float]:
    """The edges with any group under MIN_SHARE of the development loans merged into a neighbour: the edge that
    made the smallest such group goes, on the side whose curve sits closer to it (the lowest group's upper edge,
    the highest's lower). Two steps found close together (a ramp over two grid points) otherwise leave a sliver."""
    import numpy as np
    seen = v[~np.isnan(v)]
    bins = list(bins)
    while bins:
        counts = np.bincount(np.searchsorted(np.array(bins), seen, side="right"), minlength=len(bins) + 1)
        share = counts / max(len(seen), 1)
        small = [k for k in range(len(share)) if share[k] < MIN_SHARE]
        if not small:
            break
        k = min(small, key=lambda i: (share[i], i))
        if k == 0:
            bins.pop(0)
            continue
        if k == len(bins):
            bins.pop()
            continue

        def level(g):                                     # the curve's average over the grid points in group g
            at = [p for x, p in zip(grid, pd) if bisect.bisect_right(bins, x) == g]
            return sum(at) / len(at) if at else None
        mine, low, high = level(k), level(k - 1), level(k + 1)
        if mine is None or low is None or high is None:
            bins.pop(k)                                   # nothing to tell the sides apart: merge upwards
        elif abs(mine - low) <= abs(mine - high):
            bins.pop(k - 1)
        else:
            bins.pop(k)
    return bins


def _reference(v, bins: tuple[float, ...]) -> int:
    import numpy as np
    seen = v[~np.isnan(v)]
    return bisect.bisect_right(list(bins), float(np.median(seen)))


# --------------------------------------------------------------------------
# The whole scouting step


def run(res, chosen, confidence: float | None = None, cutoff: date | None = None) -> Scouting:
    """Scout the development loans, those made before `cutoff`, for the candidates `chosen` names (choices.Choices:
    test, hold, outcome). Never raises for the data: a problem is said on `problem`. Raises ScoutMissing without
    scikit-learn."""
    why = missing()
    if why:
        raise ScoutMissing(why)
    try:
        # loaded here, before anything is found, so an add-on that is there but can't load says so in words. The
        # public-data rehearsal (29 Sep 2026): Windows' Smart App Control blocked newly installed compiled files of
        # scikit-learn at first load (a block that later cleared, and not tied to one version); missing() looks
        # without loading, so it read as there, and the Run crashed on the forest's import
        import sklearn.ensemble  # noqa: F401
        import sklearn.metrics  # noqa: F401
    except ImportError as exc:
        raise ScoutMissing(f"Finding new variables needs {PIP}, and {PIP} is installed but won't load on this "
                           f"machine: {exc} A security policy that blocks add-on files is the usual cause: ask IT "
                           f"to allow it, or confirm a saved shortlist instead.") from exc
    import numpy as np
    from . import confirmatory
    m = next((x for x in res.measures if x.name == "outcome_loans"), None)
    outcome = m.flag if m is not None else (chosen.outcome or "")
    b = res.config.benchmark
    sc = Scouting(outcome=outcome, hold=tuple(chosen.hold or ()), cutoff=cutoff,
                  confidence=confidence if confidence is not None else (b.confidence if b is not None else 0.95),
                  version=version())
    names = candidates_of(res, chosen)
    if not names:
        sc.problem = "no column is ticked Test it, and no new column is made on Columns"
        return sc
    if m is None:
        sc.problem = "this run has no yes/no outcome to scout against"
        return sc
    table = res.table
    gone = [c for c in names + list(sc.hold) if table is None or c not in table.columns]
    if gone:
        sc.problem = f"{', '.join(gone)} isn't among the columns this run read"
        return sc
    dev, first, last_dev, last, after, why = development_rows(res, cutoff)
    if why:
        sc.problem = why
        return sc
    sc.development = prespec.DateRange(first, last_dev)
    sc.holdout = prespec.DateRange(last_dev + timedelta(days=1), last)
    sc.n_held_back = after
    # from here on only the development loans are read
    rows = [table.rows[i] for i in dev]
    ys = [confirmatory.outcome_of(r.get(m.flag), m, res.config.missing) for r in rows]
    keep = [i for i, y in enumerate(ys) if y is not None]
    if len(keep) < len(rows):
        sc.left_out["no readable outcome"] = len(rows) - len(keep)
    rows = [rows[i] for i in keep]
    y = np.array([ys[i] for i in keep], dtype=int)
    sc.n_dev, sc.n_dev_bad = len(y), int(y.sum())
    if not sc.n_dev_bad or sc.n_dev_bad == sc.n_dev:
        sc.problem = "no development loan went bad" if not sc.n_dev_bad else "every development loan went bad"
        return sc
    cands = [Candidate(c, _kind(res, c)) for c in names]
    sc.forests = {"names": list(names)}
    cols = []
    for c in cands:
        v, lv = _values(res, rows, c.name, c.kind)
        c.loans = int((~np.isnan(v)).sum())
        cols.append(v)
        if lv is not None:
            sc.levels[c.name] = lv
    held_cols = []
    for h in sc.hold:
        v, lv = _values(res, rows, h, _kind(res, h))
        held_cols.append(v)
        if lv is not None:
            sc.levels[h] = lv
    X = np.column_stack(cols)
    imp, sc.auc = importances(X, y)
    for c, v in zip(cands, imp):
        c.importance = v
    Xh = X
    if held_cols:
        Xh = np.column_stack(cols + held_cols)
        imp_h, sc.auc_held = importances(Xh, y)
        for c, v in zip(cands, imp_h):
            c.importance_held = v
        sc.held = [(h, v) for h, v in zip(sc.hold, imp_h[len(cands):])]
    sc.floor, sc.draws = noise_floor(X, y)

    # the shape and the bins, from a forest grown on every development loan
    rf = _forest().fit(Xh, y)
    sc.forests.update({"held" if held_cols else "plain": rf, "dev": (X, y)})
    for j, (c, v) in enumerate(zip(cands, cols)):
        if c.kind != NUMBER:
            continue
        grid = _grid(v)
        if len(grid) < 2:
            continue
        pd = curve(rf, Xh, j, grid)
        c.curve = list(zip(grid, pd))
        cut_at = steps(pd, _shares(v, grid))
        splits = forest_splits(rf, j)
        bins = []
        for i in cut_at:
            e = edge(splits, grid[i], grid[i + 1])
            if not bins or e > bins[-1]:
                bins.append(e)
        bins = merge_small(bins, v, grid, pd)
        if bins:
            c.bins = tuple(bins)
            lo, hi = float(np.nanmin(v)), float(np.nanmax(v))
            c.groups = tuple(engine.band_labels(c.bins, lo, hi))
            c.reference_index = _reference(v, c.bins)

    # the correlated pairs, among the number columns
    _pairs(cands, cols, [(h, v) for h, v in zip(sc.hold, held_cols) if _kind(res, h) == NUMBER])

    for c in cands:
        clears = sc.floor is not None and any(v is not None and v > sc.floor
                                              for v in (c.importance, c.importance_held))
        if c.kind == CATEGORY:
            c.why = A_CATEGORY
        elif not clears:
            c.why = BELOW
        elif not c.bins:
            c.why = NO_BEND if len(c.curve) >= 2 else TOO_FEW
        else:
            c.why, c.proposed = CLEARS, True
    cands.sort(key=lambda c: (-(c.best if c.best != -math.inf else -1e9), names.index(c.name)))
    for i, c in enumerate(cands, start=1):
        c.rank = i
    sc.candidates = cands
    return sc


def out_of_time(res, sc: Scouting) -> OutOfTime | None:
    """The tree's out-of-time check (OC-51): forests grown on every development loan score the loans made on or after
    the cutoff, and their AUC there is worked out, with the held-fixed columns in the forest and without them. Call it
    only once the pre-spec is written and read: this reads the held-back loans' outcomes and values, which is a touch
    of the holdout (Record's Log says so). None when scouting didn't get as far as a forest."""
    if sc.problem or "dev" not in sc.forests or sc.cutoff is None:
        return None
    import numpy as np
    from . import confirmatory
    oot = sc.oot = OutOfTime(held_back=sc.holdout)
    m = next((x for x in res.measures if x.name == "outcome_loans"), None)
    read, why = confirmatory._reader(res)
    if read is None or m is None:
        oot.problem = why or "this run has no yes/no outcome"
        return oot
    col = res.config.origination_date
    rows, ys = [], []
    for r in res.table.rows:
        d = confirmatory._date_or_none(read(r.get(col)))
        if d is None or d < sc.cutoff:
            continue
        y = confirmatory.outcome_of(r.get(m.flag), m, res.config.missing)
        if y is None:
            oot.left_out["no readable outcome"] = oot.left_out.get("no readable outcome", 0) + 1
            continue
        rows.append(r)
        ys.append(y)
    y = np.array(ys, dtype=int)
    oot.loans, oot.bad = len(y), int(y.sum())
    if not oot.loans or not oot.bad or oot.bad == oot.loans:
        oot.problem = ("no held-back loan has a readable outcome" if not oot.loans else
                       "no held-back loan went bad" if not oot.bad else "every held-back loan went bad")
        return oot
    kinds = {c.name: c.kind for c in sc.candidates}
    # the columns in the order `run` fed them to the forest: the candidates as candidates_of named them, then held
    cols = [_values(res, rows, n, kinds[n], sc.levels.get(n))[0] for n in sc.forests["names"]]
    held = [_values(res, rows, h, _kind(res, h), sc.levels.get(h))[0] for h in sc.hold]
    plain = sc.forests.get("plain")
    if plain is None:
        Xd, yd = sc.forests["dev"]
        plain = sc.forests["plain"] = _forest().fit(Xd, yd)
    oot.y = y
    oot.scores = proba(plain, np.column_stack(cols))
    oot.auc = _auc(y, oot.scores)
    if held and "held" in sc.forests:
        oot.scores_held = proba(sc.forests["held"], np.column_stack(cols + held))
        oot.auc_held = _auc(y, oot.scores_held)
    return oot


def auc_words(sc: Scouting) -> str | None:
    """The one plain line: "Built on loans made 2022-01-01 to 2023-12-31: AUC 0.71. On loans made 2024-01-01 to
    2024-12-31, unseen: 0.69." With columns held fixed, the forest with them in it is said too. None when the check
    didn't run."""
    o = getattr(sc, "oot", None)
    if o is None or o.problem or o.auc is None:
        return None
    built = f"{sc.auc:.2f}" if sc.auc is not None else "not worked out"
    said = (f"Built on loans made {sc.development.text()}: AUC {built}. On loans made {o.held_back.text()}, "
            f"unseen: {o.auc:.2f}.")
    if o.auc_held is not None:
        bh = f"{sc.auc_held:.2f}" if sc.auc_held is not None else "not worked out"
        said += f" With {' and '.join(sc.hold)} in the forest too: {bh} built, {o.auc_held:.2f} unseen."
    return said


def _pairs(cands, cols, held) -> None:
    import numpy as np
    from scipy.stats import rankdata
    nums = [(c.name, v, c) for c, v in zip(cands, cols) if c.kind == NUMBER] + [(h, v, None) for h, v in held]
    for a in range(len(nums)):
        for b in range(a + 1, len(nums)):
            na, va, ca = nums[a]
            nb, vb, cb = nums[b]
            both = ~np.isnan(va) & ~np.isnan(vb)
            if both.sum() < 3:
                continue
            ra, rb = rankdata(va[both]), rankdata(vb[both])
            if ra.std() == 0 or rb.std() == 0:
                continue
            rho = float(np.corrcoef(ra, rb)[0, 1])
            if abs(rho) >= CORRELATED:
                if ca is not None:
                    ca.partners.append((nb + (" (held fixed)" if cb is None else ""), rho))
                if cb is not None:
                    cb.partners.append((na + (" (held fixed)" if ca is None else ""), rho))


# --------------------------------------------------------------------------
# The file


def prespec_for(book: Path) -> Path:
    """Where scouting writes the pre-spec: beside the workbook, named after it."""
    book = Path(book)
    stem = book.stem.removesuffix(" - PocketBook")
    return book.with_name(f"{stem} - pre-spec.yaml")


def _num(x: float) -> str:
    return repr(float(x)).removesuffix(".0") if float(x).is_integer() else repr(float(x))


def text(sc: Scouting, today: date) -> str:
    """The pre-spec this scouting proposes, in the shortlist format prespec.py reads. Strata are the Hold fixed
    columns chosen in the launcher; with none chosen they read [CONFIRM: ...], so the file refuses until answered."""
    strata = f"[{', '.join(sc.hold)}]" if sc.hold else CONFIRM_STRATA
    lines = [f"# Written by PocketBook's scouting on {today.isoformat()}, from {sc.n_dev:,} development loans made "
             f"{sc.development.text()}.",
             f"# The {sc.n_held_back:,} loans held back (made {sc.holdout.text()}) were not read. Edit it if you "
             f"like: Record logs every change.",
             "prespec: 1",
             f"written: {today.isoformat()}",
             f"outcome: {_quote(sc.outcome)}",
             "inputs:"]
    for c in sc.proposed:
        lines += [f"  - column: {_quote(c.name)}",
                  f"    bins: [{', '.join(_num(x) for x in c.bins)}]",
                  f"    reference: {c.reference_index}                  # {c.reference}, the group holding the median"]
    lines += [f"strata: {strata}" + ("" if sc.hold else "   # held fixed; each input is reported with and without"),
              f"confidence: {_num(sc.confidence)}",
              f"holdout: {{from: {sc.holdout.start.isoformat()}, to: {sc.holdout.end.isoformat()}}}",
              f"development: {{from: {sc.development.start.isoformat()}, to: {sc.development.end.isoformat()}}}"]
    return "\n".join(lines) + "\n"


def _quote(name: str) -> str:
    import json
    plain = name.replace("_", "").replace(".", "").isalnum() and not name[:1].isdigit()
    return name if plain else json.dumps(name)


def differences(spec: prespec.PreSpec, sc: Scouting) -> list[str]:
    """Where a pre-spec on disk differs from what this Run's scouting proposes, one sentence each. The day it was
    written, and strata still to be answered in the proposal, are not differences."""
    out = []
    want = {c.name: c for c in sc.proposed}
    have = {i.column: i for i in spec.inputs}
    for name, c in want.items():
        i = have.get(name)
        if i is None:
            out.append(f"scouting proposes {name}; the file doesn't list it")
        elif tuple(i.bins) != tuple(c.bins) or i.reference_index != c.reference_index:
            out.append(f"{name}: the file cuts at {', '.join(_num(x) for x in i.bins)} against group "
                       f"{i.reference_index}; scouting proposes {', '.join(_num(x) for x in c.bins)} against group "
                       f"{c.reference_index}")
    for name in have:
        if name not in want:
            out.append(f"the file lists {name}; scouting doesn't propose it")
    if sc.hold and tuple(spec.strata) != tuple(sc.hold):
        out.append(f"the file holds {', '.join(spec.strata) or 'nothing'} fixed; the launcher chose "
                   f"{', '.join(sc.hold)}")
    if spec.outcome is not None and spec.outcome != sc.outcome:
        out.append(f"the file's outcome is {spec.outcome}; this run's is {sc.outcome}")
    if spec.development != sc.development or spec.holdout != sc.holdout:
        out.append(f"the file's development and holdout are {spec.development.text()} and {spec.holdout.text()}; "
                   f"this run's are {sc.development.text()} and {sc.holdout.text()}")
    if not math.isclose(spec.confidence, sc.confidence):
        out.append(f"the file's confidence is {spec.confidence:g}; Control's is {sc.confidence:g}")
    return out


def write(sc: Scouting, book: Path, today: date | None = None) -> Path | None:
    """The pre-spec beside the workbook: written from the proposal when there is none, kept as it stands when there
    is (its differences from the proposal said on `sc.differs`). None when scouting proposed nothing and there is
    no file: there is nothing to confirm."""
    from .confirmatory import fingerprint
    today = today or date.today()
    p = prespec_for(book)
    sc.path = p
    sc.text = text(sc, today) if sc.proposed else ""
    if p.is_file():
        now = p.read_text(encoding="utf-8")
        sc.fingerprint = fingerprint(now)
        try:
            spec = prespec.load(p)
        except prespec.PreSpecError:
            spec = None
        sc.differs = differences(spec, sc) if spec is not None else []
        sc.action = SAME if spec is not None and not sc.differs else KEPT
        return p
    if not sc.proposed:
        return None
    p.write_text(sc.text, encoding="utf-8")
    sc.fingerprint = fingerprint(sc.text)
    sc.action, sc.written_on = WROTE, today
    return p
