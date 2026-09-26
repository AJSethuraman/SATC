"""The shuffle test (docs/statistics.md B2) for a rate that is a ratio of totals.

A dollar rate - GCO per booked dollar, RANR per booked dollar, the share of
booked dollars that went bad - is SUM(y) / SUM(x) over a pocket's loans. A
formula that counts loans as equal units overstates how sure it can be (A1,
"breaks when"), so these rates are tested by dealing the pocket label out at
random instead:

    g   = rate(pocket) - rate(rest)                       the gap seen
    g*  = the same, after shuffling which loans carry the pocket label,
          each pocket keeping its number of loans           B times
    p   = ( #{ |g*| >= |g| } + 1 ) / ( B + 1 )             two-sided

The +1 keeps p off zero, which no finite number of shuffles can justify. The
shuffle stays inside the comparison group: against the rest of the book, every
loan that entered the rate is shuffled; against the rest of its band, loans are
shuffled within the band only, so a pocket is never set against loans from
another band. numpy does the work (ruling OC-34: plain Python took about 6
minutes a run on an 8,000-loan book).

HOW IT STAYS FAST. One random order of the run's rows per shuffle serves every
test in the run:
- every pocket of a grid is a consecutive slice of the same shuffled order, one
  slice per pocket, sized to the pocket;
- every grid takes its slices from that same order;
- a within-group shuffle is the same order, stably grouped (a uniform order
  restricted to a group is a uniform order of the group, and groups are
  independent of each other);
- each rate drops the rows that did not enter it (a uniform order restricted
  to them is still uniform).
So one random order does the work of all of them, and a pocket's answer never
depends on which other grids or rates ran.

REPRODUCIBLE. The seed is a hash of fixed names (`seed_of`), never run order or
the clock, so the same extract gives the same answer every time.

numpy is imported when a test runs, not when the module loads, so the launcher
can start without it and say it is missing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Sequence

#: fixed, and part of every seed: change it and every shuffle answer changes
BASE = "origination-cube shuffle test, 25 Sep 2026"
#: B, when the cube file doesn't say (benchmark.shuffles)
SHUFFLES = 10_000
#: |g*| >= |g| - TIE * scale counts as a hit, so an exact tie is never lost to rounding.
#: The scale is the size of the rates involved, taken over |y|, so a rate near zero because
#: its dollars cancel (RANR) still gets room for the rounding of its sums.
TIE = 1e-9


class NumpyMissing(ImportError):
    """The shuffle test needs numpy (ruling OC-34)."""


def numpy(needed_by: str = "the shuffle test for the dollar rates (docs/statistics.md B2)"):
    try:
        import numpy as np
    except ImportError as exc:
        raise NumpyMissing(f"{needed_by} needs numpy, which is not installed. Install it "
                           "(python -m pip install numpy), or ask IT for it") from exc
    return np


def seed_of(*names: str) -> int:
    """A 64-bit seed from names that don't change between runs."""
    h = hashlib.sha256("\x1f".join((BASE,) + tuple(str(n) for n in names)).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "little")


@dataclass(frozen=True)
class Shuffled:
    """One test's answer: the gap seen, how many shuffles made one at least as
    big either way, and out of how many."""
    gap: float
    hits: int
    shuffles: int

    @property
    def p(self) -> float:
        return (self.hits + 1) / (self.shuffles + 1)


# --------------------------------------------------------------------------
# What a run hands in


@dataclass
class Column:
    """One rate's rows: y and x per row of the run; None where the row did not
    enter the rate (left out, never a zero)."""
    name: str
    y: Sequence[float | None]
    x: Sequence[float | None]


@dataclass
class Structure:
    """One way of grouping the run's rows for shuffling, and the pockets cut
    inside it. `group` is a group number per row (None: the row is not in this
    structure), or None for one group holding every row. Each layout is a
    pocket number per row (numbers unique within the layout), every pocket
    inside one group. `stats` holds the statistic to feed per (layout index,
    column name)."""
    name: str
    group: Sequence[int | None] | None
    layouts: list[Sequence[int]]
    stats: dict[tuple[int, str], "Statistic"] = field(default_factory=dict)


class Statistic:
    """Told the pockets' observed sums once, then each chunk of shuffled sums.
    Arrays are per pocket, in slice order: `pockets` (the numbers), y and x
    (the pocket's sums), gy and gx (its group's sums), ay (its group's SUM|y|,
    for the tie scale)."""

    def start(self, np, pockets, y, x, gy, gx, ay) -> None:        # pragma: no cover - interface
        raise NotImplementedError

    def chunk(self, np, ys, xs) -> None:                            # pragma: no cover - interface
        raise NotImplementedError


class RestGap(Statistic):
    """Every pocket against the rest of its group: rate(pocket) - rate(rest).
    `answers` maps pocket number -> Shuffled; a pocket with no rest, or no
    dollars on either side, gets no answer. keep=True keeps every g* (the tests
    check the draws against every possible labelling)."""

    def __init__(self, keep: bool = False):
        self.keep = keep
        self.draws: list = []
        self.answers: dict[int, Shuffled] = {}

    def start(self, np, pockets, y, x, gy, gx, ay):
        self.pockets, self.gy, self.gx = pockets, gy, gx
        rx = gx - x
        with np.errstate(divide="ignore", invalid="ignore"):
            g = y / x - (gy - y) / rx
            scale = np.maximum(np.abs(g), np.abs(ay / gx))
        self.ok = (x != 0) & (rx != 0) & np.isfinite(g)
        self.g = np.where(self.ok, g, 0.0)
        self.thr = np.abs(self.g) - TIE * np.nan_to_num(scale, nan=0.0, posinf=0.0)
        self.hits = np.zeros(len(pockets), dtype=np.int64)
        self.n = 0

    def chunk(self, np, ys, xs):
        with np.errstate(divide="ignore", invalid="ignore"):
            g = ys / xs - (self.gy - ys) / (self.gx - xs)
        # a shuffled gap that can't be worked out (no dollars in a slice) counts against the pocket
        self.hits += (~(np.abs(g) < self.thr)).sum(axis=0)
        self.n += len(ys)
        if self.keep:
            self.draws.append(g)
        self.answers = {int(k): Shuffled(float(self.g[i]), int(self.hits[i]), self.n)
                        for i, k in enumerate(self.pockets) if self.ok[i]}


class HalfGap(Statistic):
    """Two halves of every group (pocket numbers 2g and 2g + 1: high and low),
    shuffled within the group. Per group, rate(high) - rate(low); and, pooled
    over the groups named in `pooled`, O - E: the high halves' actual total
    less what they would be at their own low half's rate (A7's E')."""

    def __init__(self, pooled: set[int] | None = None):
        self.pooled_groups = set(pooled or ())
        self.answers: dict[int, Shuffled] = {}
        self.pooled: Shuffled | None = None

    def start(self, np, pockets, y, x, gy, gx, ay):
        at = {int(k): i for i, k in enumerate(pockets)}
        self.groups = sorted({int(k) // 2 for k in pockets if (int(k) ^ 1) in at})
        self.hi = np.array([at[2 * g] for g in self.groups], dtype=np.int64)
        self.lo = np.array([at[2 * g + 1] for g in self.groups], dtype=np.int64)
        self.in_pool = np.array([g in self.pooled_groups for g in self.groups], dtype=bool)
        gap, t = self._stats(np, y[None, :], x[None, :])
        self.gap, self.t = gap[0], float(t[0])
        with np.errstate(divide="ignore", invalid="ignore"):
            scale = np.maximum(np.abs(self.gap), np.abs(ay[self.hi] / gx[self.hi]))
        self.thr = np.abs(self.gap) - TIE * np.nan_to_num(scale, nan=0.0, posinf=0.0)
        self.t_thr = abs(self.t) - TIE * max(float(ay[self.hi][self.in_pool].sum()), abs(self.t))
        self.hits = np.zeros(len(self.groups), dtype=np.int64)
        self.t_hits = 0
        self.n = 0

    def _stats(self, np, ys, xs):
        yh, xh, yl, xl = ys[:, self.hi], xs[:, self.hi], ys[:, self.lo], xs[:, self.lo]
        with np.errstate(divide="ignore", invalid="ignore"):
            gap = yh / xh - yl / xl
            t = (yh - yl / xl * xh)[:, self.in_pool].sum(axis=1)
        return gap, t

    def chunk(self, np, ys, xs):
        gap, t = self._stats(np, ys, xs)
        self.hits += (~(np.abs(gap) < self.thr)).sum(axis=0)
        self.t_hits += int((~(np.abs(t) < self.t_thr)).sum())
        self.n += len(ys)
        self.answers = {g: Shuffled(float(self.gap[i]), int(self.hits[i]), self.n)
                        for i, g in enumerate(self.groups) if np.isfinite(self.gap[i])}
        self.pooled = (Shuffled(self.t, self.t_hits, self.n)
                       if self.in_pool.any() and np.isfinite(self.t) else None)


# --------------------------------------------------------------------------
# The run


def _layout(np, rows_grp, pk, y, x):
    """How one layout's pockets lie in the shuffled order: by group, then by
    pocket. Returns (pockets, slice starts, pocket sums y and x, the pocket's
    group sums y, x and |y|), everything in slice order."""
    order = np.lexsort((pk, rows_grp))
    ps, gs = pk[order], rows_grp[order]
    first = np.flatnonzero(np.concatenate(([True], ps[1:] != ps[:-1])))
    pockets = ps[first]
    if len(np.unique(pockets)) != len(pockets):
        raise ValueError("a pocket lies in more than one group")
    gfirst = np.flatnonzero(np.concatenate(([True], gs[1:] != gs[:-1])))
    ys, xs = y[order], x[order]
    py, px = np.add.reduceat(ys, first), np.add.reduceat(xs, first)
    at = np.searchsorted(gfirst, first, side="right") - 1          # each pocket's group, as a group index
    gy, gx = np.add.reduceat(ys, gfirst)[at], np.add.reduceat(xs, gfirst)[at]
    ay = np.add.reduceat(np.abs(ys), gfirst)[at]
    return pockets, first, py, px, gy, gx, ay


def run(n: int, columns: list[Column], structures: list[Structure], shuffles: int, seed: int,
        chunk: int = 256) -> None:
    """Shuffle the `n` rows `shuffles` times and feed every statistic. One random
    order per shuffle serves every structure, layout and column."""
    np = numpy()
    cols = {}
    for c in columns:
        enter = np.array([a is not None and b is not None for a, b in zip(c.y, c.x)], dtype=bool)
        yx = np.zeros((2, n), dtype=np.float64)
        yx[0, enter] = [a for a, b in zip(c.y, c.x) if a is not None and b is not None]
        yx[1, enter] = [b for a, b in zip(c.y, c.x) if a is not None and b is not None]
        # y and x travel together as one complex number, so a shuffle gathers and sums once, not twice
        cols[c.name] = (enter, yx, yx[0] + 1j * yx[1])

    work = []
    for s in structures:
        if s.group is None:
            codes, inside = None, np.ones(n, dtype=bool)
        else:
            raw = np.array([-1 if g is None else g for g in s.group], dtype=np.int64)
            inside = raw >= 0
            top = int(raw.max()) + 1 if n else 1
            raw[~inside] = top                      # rows outside the structure sort last and are dropped
            # small unsigned codes sort by radix (one pass for uint8): the grouping is a third of a shuffle's cost
            codes = raw.astype(np.uint8 if top < 256 else np.uint16 if top < 65536 else np.int64)
        per_col = []
        for cname in sorted({cn for (_, cn) in s.stats}):
            enter, yx, z = cols[cname]
            keep = enter & inside
            rows = np.flatnonzero(keep)
            if not len(rows):
                continue
            grp = np.zeros(len(rows), dtype=np.int64) if codes is None else codes[rows].astype(np.int64)
            y, x = yx[0, rows], yx[1, rows]
            lays, bounds = [], set()
            for li, lay in enumerate(s.layouts):
                st = s.stats.get((li, cname))
                if st is None:
                    continue
                pockets, first, py, px, gy, gx, ay = _layout(np, grp, np.asarray(lay, dtype=np.int64)[rows], y, x)
                st.start(np, pockets, py, px, gy, gx, ay)
                bounds.update(first.tolist())
                lays.append((st, first))
            if not lays:
                continue
            seg = np.array(sorted(bounds), dtype=np.int64)
            lays = [(st, np.searchsorted(seg, first)) for st, first in lays]
            # a rate every row of the structure entered needs no dropping: its rows are the first ones
            fast = len(rows) if keep[inside].all() else None
            per_col.append((z, keep, fast, seg, lays, np.empty((chunk, len(seg)), dtype=np.complex128)))
        if per_col:
            work.append((codes, per_col))
    if not work or shuffles <= 0:
        return

    rng = np.random.Generator(np.random.PCG64(seed))
    done = 0
    while done < shuffles:
        b = min(chunk, shuffles - done)
        for j in range(b):
            pi = rng.permutation(n)
            for codes, per_col in work:
                # within groups: the same random order, stably grouped
                order = pi if codes is None else pi[np.argsort(codes[pi], kind="stable")]
                for z, keep, fast, seg, lays, buf in per_col:
                    sig = order[:fast] if fast is not None else order[keep[order]]
                    buf[j] = np.add.reduceat(z.take(sig), seg)
        for codes, per_col in work:
            for z, keep, fast, seg, lays, buf in per_col:
                part = buf[:b]
                for st, idx in lays:
                    sums = np.add.reduceat(part, idx, axis=1)
                    st.chunk(np, sums.real, sums.imag)
        done += b


# --------------------------------------------------------------------------
# One pocket against the rest, for checking a number by hand


def pocket_vs_rest(y_pocket: Sequence[float], x_pocket: Sequence[float], y_rest: Sequence[float],
                   x_rest: Sequence[float], shuffles: int = SHUFFLES, seed: int | None = None,
                   keep: bool = False) -> tuple[Shuffled, Any]:
    """B2 for one pocket against one rest. Returns the answer and the statistic
    (whose .draws hold every g* when keep=True)."""
    y = list(y_pocket) + list(y_rest)
    x = list(x_pocket) + list(x_rest)
    lay = [0] * len(y_pocket) + [1] * len(y_rest)
    st = RestGap(keep=keep)
    s = Structure("pocket vs rest", None, [lay], {(0, "rate"): st})
    run(len(y), [Column("rate", y, x)], [s], shuffles, seed_of("pocket vs rest") if seed is None else seed)
    return st.answers[0], st
