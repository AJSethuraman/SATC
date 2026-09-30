"""From the extract to the cube: every band crossed with every dimension.

The question the cube answers is *where does the book bleed*: which pockets
lose more than their share. So every rate cell carries three comparisons.

  vs topline   the cell's rate over the whole book's rate. The same number is
               the cell's share of the losses over its share of the volume,
               which is why it is the bleed measure. For profit (RANR, and
               contribution before losses) every comparison is the difference
               in points instead, never a multiple (NEXT-GOAL 3.2).
  excess       the cell's losses minus what it would have lost at the topline
               rate. In dollars, and it adds to zero across a grid, so it
               reconciles as the rates do. Since Option A it is the tie-out
               only (OC-4, superseded for the reading).
  excess_rest  the same against the rest of the book's rate (the book without
               the pocket, as vs_rest): what "judged against the book" counts
               as the pocket's dollars (Option A, the firm, 26 Sep 2026).
  excess_band  the same against the rest of its band's rate (the band without
               the pocket, as vs_band), so a pocket in a high-loss band that
               is in line with its neighbours has little. Control's "judged
               against" picks which of the two is the pocket's dollars, its
               materiality and its place in the ranking (the firm, 26 Sep 2026).
  vs median    the cell's rate over the median of the grid's cell rates, thin
               cells excluded from that median (the workbook's option 2, D61).

Every row lands in exactly one cell of every grid. A row that cannot enter a
rate - its value blank, not a number, or missing by rule - is left out of
that rate's top AND bottom and counted, never turned into a zero (findings 1
and 4, ruling OC-1). Before anything is returned, every grid is tied out
against totals accumulated separately: a grid that does not add up to the
book is an error, not a table.
"""

from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from . import perm, stats
from .choices import (NO_DATE, ORIG_YEAR, SPLIT_MOST_VALUES, same_filter_twice, too_many_to_filter,  # noqa: F401
                      too_many_values, too_many_views)
from .config import EACH_LOAN, PERIOD_WORDS, PROFIT, Band, Config, Dimension, Measure, MissingRule
from .ingest import BLANK, Bad, Table, cell_text, is_blank, parse_number

BLANK_LABEL = "(blank)"
NOT_NUMBER_LABEL = "(not a number)"
MISSING_RULE_LABEL = "(marked missing)"
REASON_LABEL = {"blank": BLANK_LABEL, "not a number": NOT_NUMBER_LABEL, "missing by rule": MISSING_RULE_LABEL}

# The words a pocket can get. Each says which way (walkthrough defect 11: "gap
# could be luck" on a pocket that was better did not say so). A gap past the line
# whose p-value is not below the bar is "not significant" (NEXT-GOAL 3.1, as
# docs/statistics.md's conventions say it).
WORSE, BETTER, IN_LINE = "worse", "better", "in line"
UNSURE_WORSE, UNSURE_BETTER = "worse, not significant", "better, not significant"
THIN, FEW = "too few loans to test", "too few losses to test"
UNSURE = UNSURE_WORSE
# the test behind a pocket's p-value (RateStat.test), in the words the workbook uses
Z_TEST, EXACT_TEST, SHUFFLE_TEST = "z", "exact", "shuffle"


def yes_no(m: Measure) -> bool:
    """A yes/no per loan (the share of loans): tested as a proportion, by A1 or
    B1. Every other rate - its bottom is dollars, or its top isn't a yes/no -
    is a ratio of totals and is shuffled (B2)."""
    return m.mode == "flagwt" and m.per == EACH_LOAN


class ColumnsMissing(Exception):
    """Columns the cube file names that the extract does not have."""

    def __init__(self, missing: list[tuple[str, str]], available: list[str]):
        self.missing = missing
        lines = [f"`{col}` (used by {who})" for col, who in missing]
        super().__init__("the extract has no column " + "; no column ".join(lines)
                         + f". Its columns are: {', '.join(available)}")


class NothingToCut(Exception):
    """Every band or every dimension was taken out, so there is no grid to build."""


class DataRefused(NothingToCut):
    """What the run was asked needs something the data can't give: a date that
    reads two ways, a new column named like one the extract already has. Said in words, caught where
    NothingToCut is, so every caller shows it without a traceback."""


class TieOutError(Exception):
    """A grid does not add up to the book. Never caught inside the engine."""


# --------------------------------------------------------------------------
# Reading one value


def classify_number(raw: Any, rule: MissingRule | None) -> tuple[float | None, str | None]:
    """(value, None) or (None, reason). A blank is never a zero."""
    p = parse_number(raw)
    if p is BLANK:
        return None, "blank"
    if isinstance(p, Bad):
        return None, "not a number"
    if rule is not None and _caught(p, rule):
        return None, "missing by rule"
    return p, None


def _caught(v: float, rule: MissingRule) -> bool:
    if rule.below is not None and v < rule.below:
        return True
    if rule.above is not None and v > rule.above:
        return True
    for m in rule.values:
        if isinstance(m, (int, float)) and not isinstance(m, bool) and float(m) == v:
            return True
    return False


def classify_text(raw: Any, rule: MissingRule | None) -> str:
    """A dimension label. Blank and missing-by-rule get their own visible row."""
    if is_blank(raw):
        return BLANK_LABEL
    text = cell_text(raw)
    if rule is not None:
        if any(cell_text(m) == text for m in rule.values):
            return MISSING_RULE_LABEL
        p = parse_number(raw)
        if not isinstance(p, Bad) and p is not BLANK and _caught(p, rule):
            return MISSING_RULE_LABEL
    return text


def all_whole(values) -> bool:
    """True when every value is a whole number: a score, a count, a term in months."""
    return all(float(v).is_integer() for v in values)


def reads_whole(edges) -> bool:
    """True when a column's band labels read in whole units: every edge 100 or more either way (dollars, scores).
    Under that, a ratio or a rate, the labels carry the edges' own decimals. The one test band_labels and the cuts use."""
    return bool(edges) and min(abs(float(x)) for x in edges) >= 100


def whole_cut(edges, values) -> tuple[float, ...]:
    """Edges PocketBook cut (never typed ones: those are the analyst's, kept exactly as typed) on a column whose labels
    read in whole units and whose values carry cents, each raised to the next whole number. The firm, 30 Sep 2026, on
    an equal-loan edge of $37,950.548 whose labels read "26,324 - 37,950" and "37,951 - 49,151" while a loan of
    $37,950.99 sat in the second: "Cut at whole dollars is fine". A whole-unit label reads a value with its cents
    dropped (the whole dollars at or below it: $37,950.99 reads 37,950), so a band [a, b) at whole a and b holds
    exactly the values whose reading is a to b - 1, which is what its label says. Raised, never rounded: on a column
    of whole numbers (a score) raising moves no value, which is why such a column is left as it is. An edge that
    raising puts on the one before it, or past the column's largest value, is dropped (a band with no loans); the
    caller's "asked for N bands, got M" says so. A column whose loans all read the same whole dollars (every one
    between $100 and $101) can't be cut at a whole dollar at all; its cut is kept as it was rather than refused."""
    edges = tuple(float(e) for e in edges)
    vals = [float(v) for v in values]
    if not edges or not vals or not reads_whole(edges) or all_whole(vals):
        return edges
    lo, hi = min(vals), max(vals)
    out: list[float] = []
    for e in edges:
        w = float(math.ceil(e))
        if lo < w <= hi and (not out or w > out[-1]):
            out.append(w)
    return tuple(out) or edges


def band_labels(edges: tuple[float, ...], lo: float | None = None, hi: float | None = None,
                whole: bool = False) -> list[str]:
    """Bands as ranges: "620 - 679", with the lowest from the column's smallest
    value and the highest to its largest (the firm, 25 Sep 2026: "i want bands to
    be written in '0 - 660' form ... adding words over symbols makes a big
    difference to how cluttered it feels"). A band holds its first number and
    stops one step short of the next band's, the step being 1 for whole-number
    edges and the edges' own last decimal place otherwise. `whole`: the column holds whole numbers only (a score),
    so an edge between them (654.2) starts its band at the next whole number (655)."""
    dec = 0
    if not reads_whole(edges):                           # scores and dollars read as whole numbers
        for x in edges:
            t = f"{float(x):.4f}".rstrip("0").rstrip(".")
            if "." in t:
                dec = max(dec, len(t.split(".")[1]))
    for d in range(dec, 7):
        step = 10.0 ** -d
        if dec and lo is not None and lo < edges[0] and edges[0] - step < lo and d < 6:
            # the lowest band would end below its own smallest value: 0.03 to 0.099 read "0.0 - 0.0" at edges of
            # one decimal (found 27 Sep 2026, on the bins scouting suggested for income / sales, [0.1, 2])
            continue

        def f(x, d=d):
            return f"{x:,.{d}f}"

        def up(x, step=step):
            # an edge finer than the step shown (a FICO cut at 654.2, read as whole numbers) starts its band at the
            # first shown value in it, 655, and the band below ends at 654, which it holds (found 30 Sep 2026: it
            # read "496 - 653" and held 654)
            return math.ceil(round(x / step, 9)) * step if whole else x

        first = f(math.floor(lo / step) * step) if lo is not None and lo < edges[0] else None
        # a whole-unit label reads a value with its cents dropped (the firm, 30 Sep 2026: "Cut at whole dollars is
        # fine"), so the highest band ends at its largest value's whole dollars: $49,151.40 ends "... - 49,151"
        last = (f((math.floor(hi / step) if d == 0 else math.ceil(hi / step)) * step)
                if hi is not None and hi >= edges[-1] else None)
        out = [f"{first} - {f(up(edges[0]) - step)}" if first else f"up to {f(up(edges[0]) - step)}"]
        out += [f"{f(up(a))} - {f(up(b) - step)}" for a, b in zip(edges, edges[1:])]
        out.append(f"{f(up(edges[-1]))} - {last}" if last else f"{f(up(edges[-1]))} and up")
        if len(set(out)) == len(out):
            return out
    return out


def band_of(v: float, edges: tuple[float, ...], labels: list[str]) -> str:
    for i, edge in enumerate(edges):
        if v < edge:
            return labels[i]
    return labels[-1]


def _fmt(x: float) -> str:
    """A band edge as a person reads it: 26,803 not 26803.1; 0.35 stays 0.35.
    Edges are cut points, so rounding the label never moves a loan: the edge
    itself is kept at full precision and printed on the Check tab."""
    x = float(x)
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    if abs(x) >= 100 or x.is_integer():
        return f"{x:.0f}" if abs(x - round(x)) < 0.05 or abs(x) >= 100 else f"{x:g}"
    return f"{x:.3g}"


def _quantile(sorted_vals: list[float], q: float) -> float:
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def _round_nice(x: float) -> float:
    """The nearest of 1, 2, 2.5, 5, 7.5 x 10^k, sign kept. Adapted from the Pack's
    suggest, with 7.5 added: without it the upper quartile of 1..100,000
    snapped to 50,000 and two of four bands merged."""
    if x == 0:
        return 0.0
    sign = -1.0 if x < 0 else 1.0
    a = abs(x)
    base = 10 ** math.floor(math.log10(a))
    return sign * min((m * base for m in (1, 2, 2.5, 5, 7.5, 10)), key=lambda c: abs(c - a))


def cut_edges(values: list[float], count: int, cut: str) -> tuple[float, ...]:
    """Edges for `count` bands. equal_loans: each band holds about the same
    number of loans (the quantiles). round: those quantiles snapped to round
    numbers. A column with many repeats can give fewer bands than asked for;
    the edges actually used are reported with the result. On a column read in
    whole dollars that carries cents, each edge is a whole number (whole_cut)."""
    vals = sorted(values)
    if not vals:
        return ()
    edges = [_quantile(vals, i / count) for i in range(1, count)]
    if cut == "round":
        edges = [_round_nice(e) for e in edges]
    out: list[float] = []
    for e in edges:
        if e > vals[0] and (not out or e > out[-1]):
            out.append(e)
    return whole_cut(out, vals)


# --------------------------------------------------------------------------
# Comparisons (findings 2 and 8: an empty cell is never an index, and every
# threshold comes from the file)


def index_of(rate: float | None, base: float | None) -> float | None:
    """rate / base (stats.multiple: a negative base keeps the direction), or
    None. None and zero are refused explicitly: the VBA's IsNumeric(Empty) =
    True turned an empty cell into 0.00x (finding 2)."""
    if rate is None or base is None or base == 0:
        return None
    return stats.multiple(rate, base)


def gap_of(rate: float | None, base: float | None, points: bool) -> float | None:
    """A pocket against its comparison: rate - base for a measure in points
    (profit; the rate's own units, so 0.0035 is +0.35 points), else the
    multiple (index_of)."""
    if not points:
        return index_of(rate, base)
    return None if rate is None or base is None else rate - base


@dataclass(frozen=True)
class ProfitLine:
    """How far profit must move before it counts as more or less (the profit
    line on Control; the firm, 25 Sep 2026, after the seventh walk: one setting
    decides profit on every tab).
    test     each pocket's own test: any gap it calls significant (ruling OC-31)
    points   a gap of `value` or more either way, in the rate's units (0.0025 = 0.25 points)
    dollars  a shortfall or surplus of `value` dollars or more (the materiality line)"""
    kind: str
    value: float = 0.0


def profit_line(bench, dollar_line: float | None = None) -> ProfitLine | None:
    """The profit line in use. `dollar_line` is the materiality line in
    dollars (GCO's), used when the setting is materiality. Absent, each
    pocket's own test, the suggested option: the loss lines no longer lend
    profit a multiple (NEXT-GOAL 3.2)."""
    if bench is None:
        return None
    rl = getattr(bench, "revenue_line", None)
    if rl is None or rl == "luck":
        return ProfitLine("test")
    if rl == "materiality":
        return ProfitLine("dollars", float(dollar_line or 0.0))
    return ProfitLine("points", float(rl) / 100)


def reading_gap(gap: float | None, den: float, line: ProfitLine | None, p: float | None, confidence: float,
                tested: bool = True, units: int = 0, min_units: float = 0) -> str | None:
    """The word for a measure where more is better (profit), from its gap in
    points against its comparison (pocket - comparison; below zero keeps less).
    Each pocket's own test: a gap counts only when significant. A line in points
    or dollars: a gap past it counts, and one that isn't significant says so.
    `den` is the pocket's bottom (booked dollars), which turns the gap into
    dollars for a dollar line. `tested=False` is the median comparison, which
    has no test."""
    if gap is None or line is None:
        return None
    if not tested and units < min_units:
        return THIN
    real = tested and stats.significant(p, confidence)
    if line.kind == "test":
        if not tested:
            return None                     # no test, so nothing to read by it
        if not real or gap == 0:
            return IN_LINE
        return WORSE if gap < 0 else BETTER
    size = abs(gap) if line.kind == "points" else abs(gap * den)
    if gap == 0 or size < line.value * (1 - 1e-9):
        return IN_LINE
    worse = gap < 0
    if tested and not real:
        return UNSURE_WORSE if worse else UNSURE_BETTER
    return WORSE if worse else BETTER


def _signed(points: float) -> str:
    """Points with their sign: "+0.12", "-0.80", and "0.00" for no gap."""
    return f"{points:+.2f}" if round(points, 2) else "0.00"


def literal(word: str | None, gap: float | None, dollars: float | None, against: str, line: ProfitLine | None,
            p: float | None = None) -> str | None:
    """A profit reading said literally (the firm, 26 Sep 2026: "yes I prefer it to be literal"): the gap
    against the comparison that decides it, in points of booked dollars, and the shortfall or surplus it
    comes to in dollars, e.g. "short of its band by 0.80 points ($16,000)". `word` is reading_gap's word,
    `gap` the pocket less its comparison in the rate's units, `dollars` the shortfall against the same
    comparison, `against` "its band" or "the book". Too few to test says so; a gap inside the line gives
    the line and the gap."""
    if word is None or word in (THIN, FEW) or gap is None:
        return word
    if word == IN_LINE:
        if line is None or line.kind == "test":
            why = "not tested" if p is None else "not significant"
            return f"{_signed(gap * 100)} points against {against}, {why}"
        if line.kind == "points":
            return f"within {line.value * 100:.2f} points of {against} ({_signed(gap * 100)})"
        return f"within ${line.value:,.0f} of {against} ({_signed(gap * 100)} points)"
    side = "short of" if word in (WORSE, UNSURE_WORSE) else "ahead of"
    out = f"{side} {against} by {abs(gap) * 100:.2f} points"
    if dollars is not None:
        out += f" (${abs(dollars):,.0f})"
    if word in (UNSURE_WORSE, UNSURE_BETTER):
        out += " (not significant)"
    return out


def said(s: "RateStat", line: ProfitLine | None) -> str | None:
    """A pocket's profit reading, literal, against the comparison that decides it: its flag, its gap and
    its dollars all come from the one comparison."""
    if s.by_band:
        return literal(s.flag, s.vs_band, s.dollars, "its band", line, s.p_band)
    return literal(s.flag, s.vs_rest, s.dollars, "the book", line, s.p_book)


def reading_of(idx: float | None, units: int, bench, min_units: float, p: float | None = None,
               tested: bool = True, higher_is: str = "worse", events: int | None = None,
               min_events: int = 0) -> str | None:
    """The word for a cell, from its multiple. A gap past a threshold counts
    only when its p-value is below the bar at the file's confidence (after any
    allowance for testing many pockets). Only fewest losses stops a test: below
    fewest loans the share of loans gets the exact test and a dollar rate is
    shuffled, neither of which needs a minimum (docs/statistics.md A4, B1, B2;
    walk 6 defect 8: 29 bad of 50 read "too few loans to test"). A measure
    where higher is better is profit, read from its gap in points by
    reading_gap, never here. `tested=False` is the median comparison, which
    has no test at all, so the fewest-loans floor still keeps it off a handful
    of loans."""
    if idx is None or bench is None:
        return None
    if not tested and units < min_units:
        return THIN
    if events is not None and higher_is == "worse" and events < min_events:
        return FEW
    bad = idx if higher_is == "worse" else (1 / idx if idx > 0 else math.inf)
    if bench.better_at < bad < bench.worse_at:
        return IN_LINE
    worse = bad >= bench.worse_at
    if tested and not stats.significant(p, bench.confidence):
        return UNSURE_WORSE if worse else UNSURE_BETTER
    return WORSE if worse else BETTER


def adjust(ps: list[float | None], how: str) -> list[float | None]:
    """p-values after allowing for testing many pockets at once.
    bonferroni: p times the number of tests, capped at 1.
    bh (Benjamini-Hochberg 1995, J. R. Stat. Soc. B 57:289-300): the step-up
    adjusted p, p_(i) * m / i made monotone from the top."""
    idx = [i for i, p in enumerate(ps) if p is not None]
    m = len(idx)
    out = list(ps)
    if how == "none" or m == 0:
        return out
    if how == "bonferroni":
        for i in idx:
            out[i] = min(1.0, ps[i] * m)
        return out
    order = sorted(idx, key=lambda i: ps[i])
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, ps[i] * m / rank)
        out[i] = min(1.0, running)
    return out


def adjust_se(ps: list[float | None], ses: list[float | None], how: str) -> list[float | None]:
    """The standard error of each p-value after the allowance (adjust), for Borderline (docs/statistics.md B2a).
    The allowance multiplies a raw p-value, and its sampling error with it: Bonferroni's p x m carries SE x m; a
    Benjamini-Hochberg p is the smallest p_(j) x m / j over the ranks j at or above its own, so it carries the SE
    of the raw p-value that set it, times that same m / j (the tie-out of 29 Sep 2026 found one pocket's raw p
    setting 21 others'). None where the p-value that sets it has none (it wasn't shuffled)."""
    idx = [i for i, p in enumerate(ps) if p is not None]
    m = len(idx)
    out: list[float | None] = [None] * len(ps)
    if how == "none" or not m:
        return [ses[i] if ps[i] is not None else None for i in range(len(ps))]
    if how == "bonferroni":
        for i in idx:
            out[i] = ses[i] * m if ses[i] is not None and ps[i] * m < 1.0 else None
        return out
    order = sorted(idx, key=lambda i: ps[i])
    running, se = math.inf, None
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        v = ps[i] * m / rank
        if v < running:
            running, se = v, (ses[i] * m / rank if ses[i] is not None else None)
        # a p-value the allowance capped at 1 is nowhere near the bar: scaling its error by m / j would say it was
        out[i] = se if running < 1.0 else None
    return out


def p_decides(word: str | None, gap: float | None, line: "ProfitLine | None") -> bool:
    """Whether a reading's word turns on its p-value, so a p-value on the other side of the bar reads another
    word: worse against worse, not significant (and better likewise); for profit read by each pocket's own test,
    worse or better against in line. A multiple inside the loss line reads in line whatever the p-value, and too
    few to test was never tested."""
    if word in (WORSE, BETTER, UNSURE_WORSE, UNSURE_BETTER):
        return True
    return word == IN_LINE and line is not None and line.kind == "test" and gap not in (None, 0)


def worse_turns(word: str | None, gap: float | None, line: "ProfitLine | None") -> bool:
    """Whether Worse? (Yes / Not sure / No) turns on the p-value: worse against worse, not significant; and, for
    profit read by its own test, a shortfall in line (No) against worse (Yes). Better against better, not
    significant is No either way."""
    if word in (WORSE, UNSURE_WORSE):
        return True
    return word == IN_LINE and line is not None and line.kind == "test" and gap is not None and gap < 0


# --------------------------------------------------------------------------
# Result shapes


@dataclass
class RateStat:
    num: float = 0.0
    den: float = 0.0
    units: int = 0            # rows that entered this rate
    left_out: int = 0         # rows in the cell that could not
    rate: float | None = None
    vs_topline: float | None = None
    excess: float | None = None
    vs_median: float | None = None
    reading_topline: str | None = None
    reading_median: str | None = None
    syy: float = 0.0          # the sums the test needs; they add up like num and den
    sxx: float = 0.0
    sxy: float = 0.0
    # vs_*: a multiple of the comparison, or for a measure in points (profit) pocket - comparison
    vs_rest: float | None = None    # against the rest of the book (the book without this pocket)
    p_book: float | None = None     # the test of vs_rest, after the allowance for many tests
    vs_band: float | None = None    # against the rest of its band (its row, without it)
    p_band: float | None = None
    reading_band: str | None = None
    smallest_gap: float | None = None   # the smallest gap this pocket could show: a multiple, or a difference
    events: int = 0                     # loans whose top is not zero: losses, for a loss rate
    flag: str | None = None             # the reading that decides, per `compare_to`
    alone: bool = False                 # under peers, the only pocket in its band: flagged against the book
    # the dollars over the rest of its band's rate (a shortfall under it, for profit); None for a pocket
    # alone in its band, or a margin. `excess_rest` is the same over the rest of the book's rate
    excess_band: float | None = None
    # the dollars over the rest of the book's rate (the book without this pocket): what "judged against the
    # book" counts (Option A, NEXT-GOAL item 5). None for the whole book, which has no rest
    excess_rest: float | None = None
    # one comparison decides the flag, the dollars and materiality (the firm, 26 Sep 2026): True when it is
    # the rest of its band, and then `dollars` is excess_band; otherwise the book, and `dollars` is excess_rest
    by_band: bool = False
    dollars: float | None = None
    material: bool | None = None        # dollars at or over the materiality line (None: not applied)
    # which test gave p_book and p_band (docs/statistics.md): "z" (A1), "exact" (B1, a pocket under
    # fewest loans), "shuffle" (B2, a dollar rate); None when nothing was tested
    test: str | None = None
    hits_book: int | None = None        # the shuffle test: shuffles with a gap at least as big, of `shuffles`
    hits_band: int | None = None
    shuffles: int | None = None
    # Borderline (docs/statistics.md B2a): the shuffle's standard error of p_book and p_band, after the allowance
    # (adjust_se); None for a test that isn't shuffled. `borderline` is the flag's "borderline (p 0.048)" when the
    # p-value that decides it is that near the bar at the Run's confidence, and `worse_borderline` the same when it
    # is Worse? (Yes / Not sure / No) that turns on it
    se_book: float | None = None
    se_band: float | None = None
    borderline: str | None = None
    worse_borderline: str | None = None

    def sums(self) -> tuple:
        return (self.units, self.num, self.den, self.syy, self.sxx, self.sxy)


@dataclass
class MedianStat:
    values: list[float] = field(default_factory=list, repr=False)
    left_out: int = 0
    median: float | None = None
    mean: float | None = None

    @property
    def units(self) -> int:
        return len(self.values)


@dataclass
class Cell:
    rows: int = 0
    rates: dict[str, RateStat] = field(default_factory=dict)
    medians: dict[str, MedianStat] = field(default_factory=dict)


@dataclass
class Size:
    """What the loans in one cell booked (Grids' Loan size, the firm, 29 Sep 2026: "we tend to give these loan
    amounts to these FICO scores within this category"): the loans with a booked amount, their booked dollars
    added up, and the median. A description, never tested."""
    loans: int = 0
    booked: float = 0.0
    median: float | None = None

    @property
    def average(self) -> float | None:
        return self.booked / self.loans if self.loans else None


@dataclass
class Summary:
    """One band column on its own, for the Summary tab (the firm, 30 Sep 2026: "bands of FICO on the left and straight
    up unit counts, loan amounts, % of units, % of loan amounts, charged off dollars, ratio"): each band's cell, added
    up from the loans as a grid's are, and its booked dollars. `labels` are the bands in order, then (blank), (not a
    number) and (marked missing) where the column has them, then ALL; a view on one value of the Filter by column
    keeps the whole book's labels, so its rows stay put, and a band with none of its loans is an empty cell."""
    band: str
    labels: list[str]
    cells: dict[str, Cell]
    booked: dict[str, float] = field(default_factory=dict)     # empty without a booked amount


ALL = "All"
HIGH = "above its pocket's median"
LOW = "at or below its pocket's median"
NO_SPLIT_VALUE = "(no value to split on)"


@dataclass
class Grid:
    band: str
    dimension: str
    band_labels: list[str]
    dim_labels: list[str]
    cells: dict[tuple[str, str], Cell]          # (band label, dim label); margins use ALL
    benchmarks: dict[str, float | None]         # per rate measure: median of in-scope cell rates
    # the third layer, when the file asks for one: every pocket split by another column
    split_labels: list[str] = field(default_factory=list)
    split_cells: dict[tuple[str, str, str], Cell] = field(default_factory=dict)
    split_compare: dict[tuple[str, str], dict[str, tuple]] = field(default_factory=dict)  # high vs low
    split_pooled: dict[str, dict] = field(default_factory=dict)
    # per measure, the pockets whose halves both clear the floors: the only ones compared or pooled
    split_tested: dict[str, list] = field(default_factory=dict, repr=False)
    # a split by a category: each value set against the rest of its pocket (the other values together), keyed by
    # the value, each as split_compare, split_pooled and split_tested are for the halves
    split_parts: list[str] = field(default_factory=list)
    part_compare: dict[str, dict] = field(default_factory=dict)
    part_pooled: dict[str, dict] = field(default_factory=dict)
    part_tested: dict[str, dict] = field(default_factory=dict, repr=False)
    # and, for a yes/no per loan, whether the values differ at all, pooled over the pockets (B3, on K - 1 df)
    split_general: dict[str, dict] = field(default_factory=dict)
    # Borderline (docs/statistics.md B2a): each split pocket's p-value's standard error after the allowance, as
    # split_compare and part_compare hold the p-values ({(band, seg): {measure: se}}); None where not shuffled
    split_se: dict[tuple[str, str], dict[str, float | None]] = field(default_factory=dict, repr=False)
    part_se: dict[str, dict] = field(default_factory=dict, repr=False)
    # Grids' "Only loans where" (the firm, 29 Sep 2026; since 30 Sep by the Filter by column, whatever the split
    # does): this grid again on only the loans with each value of that column, keyed by (Filter 1's value, Filter 2's
    # value), None for All loans, so (v, None), (None, w) and (v, w): both filters at once hold together (AND). Built like any grid, so "vs the book" is still against the whole
    # book and "vs rest of band" is against the rest of the band among those loans. Shown on Grids only: never
    # listed as pockets, counted in a family or tied out
    filtered: dict[str, "Grid"] = field(default_factory=dict, repr=False)
    # what each cell booked, margins included (Size); empty without a booked amount
    sizes: dict[tuple[str, str], Size] = field(default_factory=dict, repr=False)

    def cell(self, band_label: str, dim_label: str) -> Cell:
        return self.cells[(band_label, dim_label)]

    def inner(self):
        for (b, d), c in self.cells.items():
            if b != ALL and d != ALL:
                yield (b, d), c


@dataclass
class Result:
    config: Config
    source: str
    rows: int
    measures: tuple[Measure, ...]               # the measures that ran
    total: Cell
    left_out: dict[str, Counter]                # measure -> Counter[(column, reason)]
    grids: list[Grid]
    warnings: list[str]
    tie_outs: int                               # checks that passed
    band_edges: dict[str, tuple[float, ...]] = field(default_factory=dict)   # the edges actually used
    materiality_line: dict[str, float] = field(default_factory=dict)       # per rate, in its own units
    loans_needed: dict[str, stats.LoansNeeded] = field(default_factory=dict)  # per rate, from the book
    min_units: dict[str, float] = field(default_factory=dict)               # per rate, the floor in use
    # the third layer (OC-23, OC-27): three-way pockets, tested like any other, and how
    # closely the split column moves with each number column that is cut into bands
    three_way: list["Grid"] = field(default_factory=list)
    split_moves_with: dict[str, float] = field(default_factory=dict)        # band column -> correlation
    # fix 3.9: the new columns made; and the origination dates of the loans run, for Check
    dates: "OriginationDates | None" = None
    derived: list["DerivedReport"] = field(default_factory=list)
    table: Table | None = None                  # the extract as the run read it, new columns included
    bleed: bool = True                          # False: a test of a new variable, which builds no grid (OC-42)
    book_size: Size | None = None               # what the whole book booked, per loan (Grids' Loan size)
    filter_values: list[str] = field(default_factory=list)  # the Filter by column's values, in order (Grids)
    filter_values2: list[str] = field(default_factory=list)  # Filter 2's values, in order
    # Summary: {(band name, Filter 1's value, Filter 2's value): Summary}, None for All loans, every band column the
    # Run cut; (band, None, None) is the whole book
    summaries: dict[tuple[str, str | None, str | None], Summary] = field(default_factory=dict)


# --------------------------------------------------------------------------


def gco_dollar_line(bench, total) -> float | None:
    """The materiality answer on Control as GCO dollars: a share of the book's
    total GCO, or the dollar amount itself. None without GCO or a benchmark."""
    if bench is None or "gco_rate" not in total.rates:
        return None
    kind, v = bench.materiality
    return 0.0 if kind == "none" else v * abs(total.rates["gco_rate"].num) if kind == "share" else v


def _materiality_lines(bench, measures, total, warnings) -> dict[str, float]:
    """Each rate's materiality line in its own units. A share of the book's
    total applies to every loss rate. A dollar amount is a GCO amount (the
    Control question is the smallest excess loss): it applies to GCO, and the
    outcome rates say they have no line rather than borrow GCO's dollars (the
    third walk, defect 8). Profit and contribution are dollars like GCO, so a
    shortfall is material at the same dollar line as the loss side: a share of
    |total RANR| collapsed when the book's profit was near zero (the audit,
    item a)."""
    out: dict[str, float] = {}
    if bench is None:
        return out
    kind, v = bench.materiality
    gco_line = gco_dollar_line(bench, total)
    for m in measures:
        if not m.is_rate:
            continue
        if kind == "none":
            out[m.name] = 0.0
        elif m.name in PROFIT and gco_line is not None:
            out[m.name] = gco_line
        elif kind == "share":
            out[m.name] = v * abs(total.rates[m.name].num)
        elif m.name == "gco_rate":
            out[m.name] = v
        else:
            warnings.append(f"{m.title}: no materiality line. The dollar line is a GCO amount, so it is only "
                            f"applied to GCO")
    return out


# --------------------------------------------------------------------------
# New columns (fix 3.9), and the range of origination dates


@dataclass
class DerivedReport:
    """One new column as made: how many loans got a value, and why the rest are blank."""
    name: str
    top: str
    bottom: str
    made: int
    blank: Counter                                  # why -> loans, e.g. "SALES is zero"

    def text(self) -> str:
        return f"{self.top} ÷ {self.bottom}"


def derive(config: Config, table: Table, warnings: list[str]) -> tuple[Table, list[DerivedReport]]:
    """The extract with the cube file's new columns added, each worked out on
    every loan before anything else reads it. The missing rules of the top and
    bottom apply, so an answered -9999 is blank here too."""
    if not config.derived:
        return table, []
    out, reports = derive_columns(table, config.derived, config.missing)
    for d in config.derived:
        pt, pb = config.periods.get(d.top), config.periods.get(d.bottom)
        if pt and pb and pt != pb:
            # fix 3.10: warn, never stop, and never rescale: which one is right is the person's to say
            factor = {("per_year", "per_month"): ", so it reads 12 times a like-for-like ratio",
                      ("per_month", "per_year"): ", so it reads a twelfth of a like-for-like ratio"}.get((pt, pb), "")
            warnings.append(f"{d.name} divides `{d.top}` ({PERIOD_WORDS[pt]}) by `{d.bottom}` ({PERIOD_WORDS[pb]}): "
                            f"they aren't over the same period{factor}")
    return out, reports


def derive_columns(table: Table, defs, rules: dict | None = None) -> tuple[Table, list[DerivedReport]]:
    """`defs` in order, each (name, top, bottom). A zero or blank bottom, or a
    blank top, gives a blank value: never a zero, never infinity, and each is
    counted by why. A new column may use one made before it."""
    rules = rules or {}
    cols = list(table.columns)
    for d in defs:
        if d.name in table.columns:
            raise DataRefused(f"the new column `{d.name}` has the name of a column the extract already has. Give it "
                              f"a name of its own")
    known = set(cols)
    missing: list[tuple[str, str]] = []
    for d in defs:
        missing += [(c, f"new column {d.name}") for c in (d.top, d.bottom) if c not in known]
        known.add(d.name)
    if missing:
        raise ColumnsMissing(missing, table.columns)
    rows = [dict(r) for r in table.rows]
    reports = []
    for d in defs:
        blank: Counter = Counter()
        made = 0
        rt, rb = rules.get(d.top), rules.get(d.bottom)
        for r in rows:
            b, why_b = classify_number(r.get(d.bottom), rb)
            t, why_t = classify_number(r.get(d.top), rt)
            v = None
            if why_b:
                blank[f"{d.bottom} {why_b}"] += 1
            elif b == 0:
                blank[f"{d.bottom} is zero"] += 1
            elif why_t:
                blank[f"{d.top} {why_t}"] += 1
            else:
                v = t / b
                made += 1
            r[d.name] = v
        cols.append(d.name)
        reports.append(DerivedReport(d.name, d.top, d.bottom, made, blank))
    return Table(path=table.path, sha256=table.sha256, columns=cols, rows=rows, kind=table.kind), reports


@dataclass
class OriginationDates:
    """When the loans run were made, for one line on Check. It removes nothing:
    every loan in the extract is run, whatever its dates (the firm, 26 Sep 2026:
    "when we are doing our bleed analysis and such I don't want to hide things
    from view"). A wrong extract then shows on the first page."""
    column: str
    loans: int                                      # the loans run
    first: Any = None                               # the earliest and latest readable date among them
    last: Any = None
    unreadable: int = 0                             # loans with no readable date
    problem: str | None = None                      # why the column couldn't be read at all, in words


def _date_reader(table: Table, col: str, what: str):
    """How to read one date column: the pattern its text fits, found once. A
    column whose every date reads two ways (01/02/2024: January or February?) is
    refused, never read one way by default."""
    from .ingest import best_pattern, detect_date_format, parse_date
    det = detect_date_format(col, [r.get(col) for r in table.rows])
    if det.ambiguous:
        ways = " or ".join(day for _, day in det.readings()[:2])
        raise DataRefused(f"the dates in `{col}` ({what}) read two ways: {det.sample} is {ways}. Write them "
                          f"year-month-day in the extract, such as 2024-01-02")
    fmt = det.resolved or best_pattern(det)
    return lambda raw: parse_date(raw, fmt)


def origination_dates(config: Config, table: Table, rows: list[dict]) -> OriginationDates | None:
    """The range of origination dates among `rows`, and how many have no
    readable date; None when no column is marked as the origination date. A
    column whose dates read two ways is said, not read one way, and never stops
    the run."""
    from datetime import date as _date
    col = config.origination_date
    if not col:
        return None
    out = OriginationDates(column=col, loans=len(rows))
    if col not in table.columns:
        out.problem = f"{col} isn't in the extract"
        return out
    try:
        read = _date_reader(table, col, "when each loan was made")
    except DataRefused as exc:
        out.problem = str(exc)
        return out
    seen = []
    for r in rows:
        d = read(r.get(col))
        if isinstance(d, _date):
            seen.append(d)
        else:
            out.unreadable += 1
    if seen:
        out.first, out.last = min(seen), max(seen)
    return out


def origination_years(table: Table, col: str) -> list[str]:
    """The year each loan was made, as text ("2023"), read from `col` (the column marked Origination date) the way
    the Run reads that column's dates; NO_DATE for a loan whose date is blank or can't be read, so it is never put
    in a year. The one definition of ORIG_YEAR: Split by and Filter by both use it (the firm, 30 Sep 2026). Dates
    that read two ways are refused (DataRefused), never read one way by default."""
    from datetime import date as _date
    read = _date_reader(table, col, "when each loan was made")
    out = []
    for r in table.rows:
        d = read(r.get(col))
        out.append(str(d.year) if isinstance(d, _date) else NO_DATE)
    return out


def with_year(config: Config, table: Table) -> Table:
    """The extract with ORIG_YEAR added when the split or the filter names it (and the extract has no column of
    that name already): the year of the column marked Origination date. Refused, in words, when none is marked."""
    wanted = {config.split[0] if config.split else None, config.filter_by, config.filter_by2}
    if ORIG_YEAR not in wanted or ORIG_YEAR in table.columns:
        return table
    col = config.origination_date
    if not col or col not in table.columns:
        raise DataRefused(f"{ORIG_YEAR} is the year each loan was made, read from the column marked Origination "
                          f"date on Columns, and no column in this extract is marked so. Mark it, or split and "
                          f"filter by another column")
    years = origination_years(table, col)
    rows = [{**r, ORIG_YEAR: y} for r, y in zip(table.rows, years)]
    return Table(path=table.path, sha256=table.sha256, columns=list(table.columns) + [ORIG_YEAR], rows=rows,
                 kind=table.kind)


def _drop_outcome_cuts(config: Config, measures, warnings: list[str]) -> Config:
    """A band or dimension on a column that is the top of a rate would cut
    the book by its own outcome: every high-GCO band would show high GCO.
    Such a cut is left out and said so, never run."""
    from dataclasses import replace
    tops = {m.value if m.mode == "sumnum" else m.flag for m in measures if m.is_rate}
    # a new column made from a rate's top is that outcome too (fix 3.9): GCO over the booked amount, cut into
    # bands, puts every loan with GCO in the top band
    made_from = {}
    for d in config.derived:
        hit = next((c for c in (d.top, d.bottom) if c in tops or c in made_from), None)
        if hit is not None:
            made_from[d.name] = made_from.get(hit, hit)
    if config.split and config.split[0] in made_from:
        raise DataRefused(f"`{config.split[0]}` is made from `{made_from[config.split[0]]}`, the top of a rate, so "
                          f"splitting by it would split the book by its own outcome. Split by another column")
    marked = dict(config.not_cut)              # meanings never cut by: servicing data, dates, the key ...
    drop = tops | set(marked) | set(made_from)
    keep_b = tuple(b for b in config.bands if b.field not in drop)
    keep_d = tuple(d for d in config.dimensions if d.field not in drop)
    for x in [b for b in config.bands if b.field in drop] + [d for d in config.dimensions if d.field in drop]:
        if x.field in made_from:
            warnings.append(f"`{x.field}` is not cut by: it is made from `{made_from[x.field]}`, the top of a rate, "
                            f"so cutting by it would cut the book by its own outcome")
        elif x.field in tops:
            warnings.append(f"`{x.field}` is not cut by: it is the top of a rate, so cutting by it would cut the "
                            f"book by its own outcome")
        else:
            warnings.append(f"`{x.field}` is not cut by: `columns:` says it means {marked[x.field]}")
    # a test of a new variable cuts only the columns held fixed, a number, a category, both or neither (OC-42)
    if (not keep_b or not keep_d) and config.run_kind != "new_variable":
        which = "band" if not keep_b else "dimension"
        raise NothingToCut(f"no {which} is left to cut by: every one listed is either the top of a rate or a "
                           f"column `columns:` says is not cut by ({', '.join(sorted(drop))}). Add a {which}, "
                           f"or change a column's meaning")
    return replace(config, bands=keep_b, dimensions=keep_d)


def run(config: Config, table: Table) -> Result:
    warnings: list[str] = []
    table, derived = derive(config, table, warnings)
    table = with_year(config, table)
    measures = _resolve_columns(config, table, warnings)
    config = _drop_outcome_cuts(config, measures, warnings)
    rows = table.rows                          # every loan: nothing is left out for its age or dates
    dates = origination_dates(config, table, rows)
    n = len(rows)
    rules = config.missing

    for col in rules:
        if col not in table.columns:
            warnings.append(f"`missing:` has a rule for `{col}`, which is not a column in the extract; "
                            f"the rule was not applied")

    # One pass per column: every value is read once, however many grids use it.
    def col(name: str) -> list[Any]:
        return [r.get(name) for r in rows]

    for q in config.questions:
        if q.column not in table.columns:
            warnings.append(f"data question on `{q.column}`, which is not a column in the extract")
        elif q.answer is None:
            warnings.append(f"open data question: {q.text()}. Used as recorded until answered "
                            f"(real, or missing) in `questions:`")

    bands = {}
    band_edges: dict[str, tuple[float, ...]] = {}
    band_label_sets: dict[str, list[str]] = {}
    for b in config.bands:
        read = [classify_number(raw, rules.get(b.field)) for raw in col(b.field)]
        edges = b.edges or cut_edges([v for v, why in read if why is None], b.count, b.cut)
        if not edges:
            raise ColumnsMissing([(b.field, f"band {b.name}: no readable numbers to cut")], table.columns)
        if b.count and len(edges) + 1 < b.count:
            warnings.append(f"band {b.name}: asked for {b.count} bands, got {len(edges) + 1} "
                            f"(`{b.field}` has too many repeated values to cut finer)")
        band_edges[b.name] = edges
        seen = [v for v, why in read if why is None]
        labels = band_labels(edges, min(seen), max(seen), whole=all_whole(seen)) if seen else band_labels(edges)
        band_label_sets[b.name] = labels
        bands[b.name] = [band_of(v, edges, labels) if why is None else REASON_LABEL[why] for v, why in read]
    dims = {d.name: [classify_text(raw, rules.get(d.field)) for raw in col(d.field)]
            for d in config.dimensions}

    # Per measure, per row: (num, den) for a rate, value for a median, or a reason.
    per_row: dict[str, list] = {}
    left_out: dict[str, Counter] = {}
    for m in measures:
        lo: Counter = Counter()
        vals: list = []
        if m.mode == "count":
            vals = [1] * n
        elif m.mode == "median":
            for raw in col(m.value):
                v, why = classify_number(raw, rules.get(m.value))
                if why:
                    lo[(m.value, why)] += 1
                vals.append(v)
        else:
            top_col = m.flag if m.mode == "flagwt" else m.value
            per_vals = [1.0] * n if m.per == EACH_LOAN else col(m.per)
            plus_vals = col(m.plus) if m.plus else [None] * n
            for raw_top, raw_per, raw_plus in zip(col(top_col), per_vals, plus_vals):
                if m.per == EACH_LOAN:
                    d, why_d = 1.0, None
                else:
                    d, why_d = classify_number(raw_per, rules.get(m.per))
                if m.mode == "flagwt" and m.flag_is is not None:
                    # yes when the value is the one named, no otherwise; a blank is neither
                    if is_blank(raw_top):
                        t, why_t = None, "blank"
                    elif classify_text(raw_top, rules.get(top_col)) == MISSING_RULE_LABEL:
                        t, why_t = None, "missing by rule"
                    else:
                        t, why_t = (1.0 if cell_text(raw_top) == cell_text(m.flag_is) else 0.0), None
                else:
                    t, why_t = classify_number(raw_top, rules.get(top_col))
                where_t = top_col
                if m.plus and why_t is None:
                    # contribution before losses = RANR + GCO, per loan (OC-35); either unreadable leaves it out
                    q, why_q = classify_number(raw_plus, rules.get(m.plus))
                    t, why_t, where_t = (t + q, None, top_col) if why_q is None else (None, why_q, m.plus)
                if why_t is None and m.mode == "flagwt" and t not in (0.0, 1.0):
                    t, why_t = None, "flag not 0 or 1"
                if why_t or why_d:
                    lo[(where_t, why_t) if why_t else (m.per, why_d)] += 1
                    vals.append(None)
                else:
                    num = (d if t == 1.0 else 0.0) if m.mode == "flagwt" else t
                    vals.append((num, d))
        per_row[m.name] = vals
        left_out[m.name] = lo

    total = _accumulate(measures, per_row, [None] * n)[None]
    _finish_cell(total, measures)
    topline = {m.name: total.rates[m.name].rate for m in measures if m.is_rate}
    for m in measures:
        if m.is_rate and topline[m.name] is None:
            warnings.append(f"{m.name}: SUM({m.per}) over the whole book is zero, so there is no topline "
                            f"rate and no cell can be compared with it")

    bench = config.benchmark
    needed: dict[str, stats.LoansNeeded] = {}
    min_units: dict[str, float] = {}
    if bench is not None:
        for m in measures:
            if not m.is_rate:
                continue
            if yes_no(m):
                # A3, exactly: a pocket of this book against the rest of it (ruling OC-37)
                t = total.rates[m.name]
                ln = stats.loans_needed_two_prop(m.name, t.rate, t.units, bench.worse_at, bench.confidence,
                                                 bench.power)
            elif m.in_points:
                # profit: a gap in points, never a multiple of a rate that can sit at zero (NEXT-GOAL 3.2)
                pl = profit_line(bench)
                ln = stats.loans_needed_difference(m.name, [v for v in per_row[m.name] if v is not None],
                                                   pl.value if pl.kind == "points" else None, bench.confidence,
                                                   bench.power)
            else:
                ln = stats.loans_needed(m.name, [v for v in per_row[m.name] if v is not None],
                                        bench.worse_at, bench.confidence, bench.power)
            needed[m.name] = ln
            min_units[m.name] = bench.min_units

    materiality_line = _materiality_lines(bench, measures, total, warnings)
    split_vals = None
    if config.split:
        sfield, how = config.split
        if sfield not in table.columns:
            raise ColumnsMissing([(sfield, "the split")], table.columns)
        if how == "each_value":
            split_vals = [classify_text(raw, rules.get(sfield)) for raw in col(sfield)]
        else:
            split_vals = [classify_number(raw, rules.get(sfield))[0] for raw in col(sfield)]
    grids, three_way = [], []
    built: list[tuple[Grid, str, list]] = []           # every grid, its band, and each row's pocket
    # every grid whose pockets are split in two sides and compared: the halves, or each value against the rest
    halved: list[tuple[Grid, list, list]] = []
    tie_outs = 0
    # a test of a new variable builds no bleed analysis (OC-42; the firm, 26 Sep 2026: "They have entirely
    # different outputs generally"): no grid, no three-way or split grid, no shuffle test. The bands are still
    # cut above, since the pre-spec's strata are read in them (confirmatory._stratum_labels)
    bleed = config.run_kind != "new_variable"
    if bleed and split_vals is not None and config.split[1] == "each_value":
        _few_enough(config.split[0], split_vals)
    # Grids' "Only loans where" reads the Filter by column (the firm, 30 Sep 2026: "Wait only works on split by?"),
    # never the split: a number split into halves, a category split, or none, the filter is the same
    filter_vals = None
    if bleed and config.filter_by:
        ff = config.filter_by
        if ff not in table.columns:
            raise ColumnsMissing([(ff, "the Grids' filter")], table.columns)
        filter_vals = [classify_text(raw, rules.get(ff)) for raw in col(ff)]
        _few_enough_to_filter(ff, filter_vals)
    # Filter 2 (the firm, 30 Sep 2026: "independently and in conjunction with each other"): another column, its
    # values offered beside Filter 1's, each alone or both at once
    filter_vals2 = None
    if bleed and config.filter_by and config.filter_by2:
        ff2 = config.filter_by2
        if ff2 == config.filter_by:
            raise DataRefused(same_filter_twice(ff2))
        if ff2 not in table.columns:
            raise ColumnsMissing([(ff2, "the Grids' second filter")], table.columns)
        filter_vals2 = [classify_text(raw, rules.get(ff2)) for raw in col(ff2)]
        _few_enough_to_filter(ff2, filter_vals2)
        said = too_many_views(config.filter_by, len(set(filter_vals)), ff2, len(set(filter_vals2)))
        if said:
            raise DataRefused(said)
    for b in config.bands if bleed else ():
        for d in config.dimensions:
            grid = _build_grid(config, b, d, band_edges[b.name], bands[b.name], dims[d.name], measures, per_row,
                               topline, min_units, total, needed, materiality_line, band_label_sets[b.name])
            built.append((grid, b.name, list(zip(bands[b.name], dims[d.name]))))
            if split_vals is not None:
                labels = _split(grid, config, bands[b.name], dims[d.name], split_vals, measures, per_row)
                halved.append((grid, list(zip(bands[b.name], dims[d.name])), _sides(grid, config, labels)))
                # the three-way pockets go through the same machinery as any pocket: tested, flagged,
                # given dollars and tied out (OC-27; the third walk, defect 3: they were pictures only)
                sfield = config.split[0]
                word = {HIGH: f"{sfield} high half", LOW: f"{sfield} low half",
                        NO_SPLIT_VALUE: f"no {sfield}"}
                composite = [f"{dd} / {word.get(lab, f'{sfield} {lab}')}" for dd, lab in zip(dims[d.name], labels)]
                three = _build_grid(config, b, Dimension(name=f"{d.name} / {sfield}", field=d.field),
                                    band_edges[b.name], bands[b.name], composite, measures, per_row, topline,
                                    min_units, total, needed, materiality_line, band_label_sets[b.name])
                built.append((three, b.name, list(zip(bands[b.name], composite))))
                tie_outs += tie_out(three, total, measures, n)
                three_way.append(three)
            tie_outs += tie_out(grid, total, measures, n)
            grids.append(grid)
    # the dollar rates' shuffle test (B2), one random order per shuffle for every grid at once; then the
    # allowance for many tests and the words, which need every p-value in
    if bleed:
        _shuffle_tests(config, measures, per_row, n, built, halved)
    for g, _, _ in built:
        _judge(g, config, measures, min_units, materiality_line)
    for g, _, _ in halved:
        _finish_split(g, config, measures)
    # Grids' Loan size and "Only loans where" (the firm, 29 Sep 2026): each grid's booked dollars per cell, and each
    # grid again on only the loans with one value of the Filter by column
    booked = None
    if bleed and config.booked and config.booked in table.columns:
        booked = [classify_number(raw, rules.get(config.booked))[0] for raw in col(config.booked)]
    book_size = None
    if booked is not None:
        book_size = loan_sizes([(ALL, ALL)] * n, booked).get((ALL, ALL), Size())
        for g, _, keys in built:
            g.sizes = loan_sizes(keys, booked)
    values: list[str] = []
    values2: list[str] = _order(filter_vals2) if filter_vals2 is not None else []
    rows_of: dict[tuple, list[int]] = {}
    if filter_vals is not None:
        values = _order(filter_vals)
        by_name = {b.name: b for b in config.bands}
        # every view: each value of Filter 1 alone, each of Filter 2 alone, and every pair, both holding (AND)
        for v, w in [(v, None) for v in values] + [(None, w) for w in values2] + [(v, w) for v in values
                                                                                   for w in values2]:
            rows_of[(v, w)] = [i for i in range(n) if (v is None or filter_vals[i] == v)
                               and (w is None or filter_vals2[i] == w)]
        for g, bname, keys in built:
            for v in rows_of:
                idx = rows_of[v]
                if not idx:
                    continue                    # no loan has both values: nothing to build, the view is empty
                sub = [keys[i] for i in idx]
                fg = _build_grid(config, by_name[bname], Dimension(name=g.dimension, field=""), band_edges[bname],
                                 [k[0] for k in sub], [k[1] for k in sub], measures,
                                 {m: [vals[i] for i in idx] for m, vals in per_row.items()}, topline, min_units,
                                 total, needed, materiality_line, band_label_sets[bname])
                _judge(fg, config, measures, min_units, materiality_line)
                if booked is not None:
                    fg.sizes = loan_sizes(sub, [booked[i] for i in idx])
                g.filtered[v] = fg
    summaries: dict[tuple[str, str | None], Summary] = {}
    for b in config.bands if bleed else ():
        whole = summaries[(b.name, None, None)] = _summary(b.name, measures, per_row, bands[b.name], booked,
                                                     band_label_sets[b.name], range(n))
        _tie_summary(whole, total, measures)
        for v, w in rows_of:
            if not rows_of[(v, w)]:
                continue
            part = summaries[(b.name, v, w)] = _summary(b.name, measures, per_row, bands[b.name], booked,
                                                        whole.labels, rows_of[(v, w)])
            _tie_summary(part, part.cells[ALL], measures)
    moves_with: dict[str, float] = {}
    if bleed and config.split and config.split[1] == "own_median":
        for b in config.bands:
            r = _correlation(split_vals, [classify_number(raw, rules.get(b.field))[0] for raw in col(b.field)])
            if r is not None:
                moves_with[b.field] = r

    return Result(config=config, source=table.path, rows=n, measures=measures, total=total,
                  left_out=left_out, grids=grids, warnings=warnings, tie_outs=tie_outs,
                  band_edges=band_edges, loans_needed=needed, min_units=min_units,
                  materiality_line=materiality_line, three_way=three_way,
                  split_moves_with=moves_with, dates=dates, derived=derived, table=table, bleed=bleed,
                  book_size=book_size, filter_values=values, filter_values2=values2, summaries=summaries)


def _summary(band: str, measures, per_row, labels_of, booked, order, idx) -> Summary:
    """The Summary of one band column over the loans at `idx`: each band's cell and booked dollars, and ALL. `order`
    is the column's band labels in order; a label no loan here carries is an empty cell, and a special row ((blank)
    and the others) comes after the bands."""
    idx = list(idx)
    cells = _accumulate(measures, {m: [vals[i] for i in idx] for m, vals in per_row.items()},
                        [labels_of[i] for i in idx])
    labels = [x for x in order if x != ALL]
    labels += [x for x in _order(cells) if x not in labels]
    out = {lab: cells.get(lab) or _merge([], measures) for lab in labels}
    for c in out.values():
        _finish_cell(c, measures)
    out[ALL] = _merge(list(out.values()), measures)
    dollars: dict[str, float] = {}
    if booked is not None:
        for lab in labels:
            dollars[lab] = math.fsum(booked[i] for i in idx if labels_of[i] == lab and booked[i] is not None)
        dollars[ALL] = math.fsum(booked[i] for i in idx if booked[i] is not None)
    return Summary(band=band, labels=labels + [ALL], cells=out, booked=dollars)


def _tie_summary(s: Summary, want: Cell, measures) -> None:
    """Summary's bands, added up, against `want` (the book's totals, accumulated in their own pass, for the whole
    book): the loans, and each rate's loans, top and bottom. Raises TieOutError, as a grid that doesn't add up does."""
    parts = [s.cells[lab] for lab in s.labels if lab != ALL]
    where = f"Summary of {s.band}"
    got = sum(c.rows for c in parts)
    if got != want.rows:
        raise TieOutError(f"{where}: the bands hold {got} loans, but the book says {want.rows}")
    for m in measures:
        if not m.is_rate:
            continue
        t = want.rates[m.name]
        for what, a, b in (("loans counted", sum(c.rates[m.name].units for c in parts), t.units),
                           ("numerator", math.fsum(c.rates[m.name].num for c in parts), t.num),
                           ("denominator", math.fsum(c.rates[m.name].den for c in parts), t.den)):
            if not _close(a, b, b):
                raise TieOutError(f"{where}: {m.name} {what} adds up to {a!r} across the bands, but the book says {b!r}")
    if s.booked:
        a, b = math.fsum(v for lab, v in s.booked.items() if lab != ALL), s.booked[ALL]
        if not _close(a, b, b):
            raise TieOutError(f"{where}: booked dollars add up to {a!r} across the bands, but the book says {b!r}")


#: Summary's columns, in the firm's order (30 Sep 2026), each with what it needs: None, the booked amount (BOOKED) or
#: the rate it is taken from. A column whose source this Run has not got is left off, and the tab says so
BOOKED = "booked"
SUMMARY_COLUMNS = (("loans", None), ("loans_share", None), ("bad", "outcome_loans"), ("bad_rate", "outcome_loans"),
                   ("booked", BOOKED), ("booked_share", BOOKED), ("gco", "gco_rate"), ("gco_rate", "gco_rate"),
                   ("gco_x", "gco_rate"), ("gco_share", "gco_rate"), ("ranr", "ranr_rate"),
                   ("ranr_rate", "ranr_rate"), ("ranr_share", "ranr_rate"))


def summary_columns(res) -> list[str]:
    """The Summary columns this Run can fill, in order."""
    have = {m.name for m in res.measures}
    booked = any(s.booked for s in res.summaries.values())
    return [k for k, need in SUMMARY_COLUMNS if need is None or (need == BOOKED and booked) or need in have]


def summary_rows(res, band: str, value: str | None = None,
                 value2: str | None = None) -> list[tuple[str, dict[str, float | None]]]:
    """Summary's rows for one band column (on only the loans with one value of the Filter by column, when `value`
    is given, and of Filter 2, when `value2` is; both given, only the loans with both): each label, and every column summary_columns gives, as arithmetic on the loans and never a test.
    Loans and bad loans are counts; a share is the row's over the All row's, so the shares add to 100% over the
    bands and the special rows; bad loans % is the Bad loans rate (bad loans over the loans whose outcome reads 0
    or 1); a charge-off or RANR rate is that measure's rate (its dollars over the booked dollars of the loans with
    both amounts), and x book is the charge-off rate over the whole book's, filter or none."""
    s = res.summaries[(band, value, value2)]
    keys = summary_columns(res)
    whole = res.total.rates.get("gco_rate")
    top = s.cells[ALL]

    def share(a, b):
        return a / b if b else None

    out = []
    for lab in s.labels:
        c = s.cells[lab]
        row: dict[str, float | None] = {"loans": c.rows, "loans_share": share(c.rows, top.rows)}
        if "outcome_loans" in c.rates:
            o = c.rates["outcome_loans"]
            row.update(bad=o.num, bad_rate=o.rate)
        if s.booked:
            row.update(booked=s.booked[lab], booked_share=share(s.booked[lab], s.booked[ALL]))
        if "gco_rate" in c.rates:
            g = c.rates["gco_rate"]
            row.update(gco=g.num, gco_rate=g.rate, gco_x=index_of(g.rate, whole.rate if whole else None),
                       gco_share=share(g.num, top.rates["gco_rate"].num))
        if "ranr_rate" in c.rates:
            r = c.rates["ranr_rate"]
            row.update(ranr=r.num, ranr_rate=r.rate, ranr_share=share(r.num, top.rates["ranr_rate"].num))
        out.append((lab, {k: row.get(k) for k in keys}))
    return out


def loan_sizes(keys, booked) -> dict[tuple[str, str], Size]:
    """Each cell's Size, margins included: `keys` each loan's (band, segment), `booked` its booked amount (None
    when it has none, and then it is left out). The values are held only while one grid is worked out."""
    groups: dict[tuple, list[float]] = {}
    for (b, d), v in zip(keys, booked):
        if v is None:
            continue
        for k in {(b, d), (b, ALL), (ALL, d), (ALL, ALL)}:
            groups.setdefault(k, []).append(v)
    return {k: Size(len(v), math.fsum(v), statistics.median(v)) for k, v in groups.items()}


def size_vs(sizes: dict, b: str, d: str, book: Size | None) -> tuple:
    """One cell's loan size as Grids shows it: the average booked per loan, the median, the average as a multiple
    of the whole book's, and as a multiple of the rest of its band's (its row without it; None for a margin, or
    a cell alone in its band). Every figure None where there is nothing to divide by."""
    s = sizes.get((b, d))
    if s is None or not s.loans:
        return None, None, None, None
    avg = s.average
    vs_book = index_of(avg, book.average) if book is not None else None
    vs_band = None
    row = sizes.get((b, ALL))
    if b != ALL and d != ALL and row is not None and row.loans > s.loans:
        vs_band = index_of(avg, (row.booked - s.booked) / (row.loans - s.loans))
    return avg, s.median, vs_book, vs_band


def _correlation(xs, ys) -> float | None:
    """Pearson's r over the loans where both are readable numbers."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    n = len(pairs)
    mx = math.fsum(x for x, _ in pairs) / n
    my = math.fsum(y for _, y in pairs) / n
    sxy = math.fsum((x - mx) * (y - my) for x, y in pairs)
    sxx = math.fsum((x - mx) ** 2 for x, _ in pairs)
    syy = math.fsum((y - my) ** 2 for _, y in pairs)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def _resolve_columns(config: Config, table: Table, warnings: list[str]) -> tuple[Measure, ...]:
    have = set(table.columns)
    missing: list[tuple[str, str]] = []
    if config.key not in have:
        # required (the firm, 25 Sep 2026): without it no pocket can be mapped back to its loans
        missing.append((config.key, "key"))
    else:
        seen = Counter(cell_text(r.get(config.key)) for r in table.rows)
        dupes = {k: v for k, v in seen.items() if v > 1}
        blanks = seen.get(BLANK_LABEL, 0)
        if blanks:
            warnings.append(f"`{config.key}` is blank on {blanks:,} rows: those loans cannot be mapped back")
        dupes.pop(BLANK_LABEL, None)
        if dupes:
            some = "1 value appears" if len(dupes) == 1 else f"{len(dupes):,} values appear"
            warnings.append(f"`{config.key}` repeats: {some} on more than one row "
                            f"({sum(dupes.values()):,} rows), so a pocket's loan list will hold them more than once")
    for b in config.bands:
        if b.field not in have:
            missing.append((b.field, f"band {b.name}"))
    for d in config.dimensions:
        if d.field not in have:
            missing.append((d.field, f"dimension {d.name}"))
    kept = []
    for m in config.measures:
        absent = [c for c in m.columns() if c not in have]
        if not absent:
            kept.append(m)
        elif m.optional:
            warnings.append(f"measure {m.name} skipped: the extract has no column {', '.join(absent)} "
                            f"(it is marked optional)")
        else:
            missing += [(c, f"measure {m.name}") for c in absent]
    if missing:
        raise ColumnsMissing(missing, table.columns)
    if not kept:
        raise ColumnsMissing([("(every measure)", "measures")], table.columns)
    return tuple(kept)


def _accumulate(measures, per_row, keys) -> dict[Any, Cell]:
    cells: dict[Any, Cell] = {}
    for i, k in enumerate(keys):
        c = cells.get(k)
        if c is None:
            c = cells[k] = Cell(rates={m.name: RateStat() for m in measures if m.is_rate or m.mode == "count"},
                                medians={m.name: MedianStat() for m in measures if m.mode == "median"})
        c.rows += 1
        for m in measures:
            v = per_row[m.name][i]
            if m.mode == "median":
                s = c.medians[m.name]
                if v is None:
                    s.left_out += 1
                else:
                    s.values.append(v)
            elif m.mode == "count":
                s = c.rates[m.name]
                s.units += 1
            else:
                s = c.rates[m.name]
                if v is None:
                    s.left_out += 1
                else:
                    y, x = v
                    s.num += y
                    s.den += x
                    s.syy += y * y
                    s.sxx += x * x
                    s.sxy += x * y
                    s.units += 1
                    if y != 0:
                        s.events += 1
    return cells


def _finish_cell(c: Cell, measures) -> None:
    for m in measures:
        if m.is_rate:
            s = c.rates[m.name]
            s.rate = s.num / s.den if s.den != 0 else None
        elif m.mode == "median":
            s = c.medians[m.name]
            if s.values:
                s.median = statistics.median(s.values)
                s.mean = math.fsum(s.values) / len(s.values)


def _merge(parts: list[Cell], measures) -> Cell:
    out = Cell(rates={m.name: RateStat() for m in measures if m.is_rate or m.mode == "count"},
               medians={m.name: MedianStat() for m in measures if m.mode == "median"})
    for p in parts:
        out.rows += p.rows
        for k, s in p.rates.items():
            o = out.rates[k]
            o.num += s.num
            o.den += s.den
            o.units += s.units
            o.left_out += s.left_out
            o.syy += s.syy
            o.sxx += s.sxx
            o.sxy += s.sxy
            o.events += s.events
        for k, s in p.medians.items():
            o = out.medians[k]
            o.values.extend(s.values)
            o.left_out += s.left_out
    _finish_cell(out, measures)
    return out


def _order(labels) -> list[str]:
    special = [NO_DATE, BLANK_LABEL, NOT_NUMBER_LABEL, MISSING_RULE_LABEL]
    plain = sorted((x for x in set(labels) if x not in special), key=_natural)
    return plain + [x for x in special if x in set(labels)]


def _natural(label: str) -> list:
    """A label's sort key with its numbers read as numbers (at the bank, 29 Sep 2026: "$5k-<$10k" came after
    "$40k+", as text sorts, on a loan amount bucket)."""
    return [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.split(r"(\d+)", str(label).lower()) if t]


def _minus(a: tuple, b: tuple) -> tuple:
    return tuple(x - y for x, y in zip(a, b))


def _proportion_p(x1: float, n1: int, rest: tuple, floor: float) -> tuple[float | None, str | None]:
    """A yes/no per loan: the pocket's x1 bad of n1 against the rest's. The
    pooled two-proportion z test (A1, ruling OC-37) at or above fewest loans;
    Fisher's exact test (B1) below it, where A1's bell curve is too sure of
    itself (walk 6 defect 8: 29 bad of 50 went untested)."""
    n2, x2 = rest[0], rest[1]
    if n1 <= 0 or n2 <= 0:
        return None, None
    if n1 >= floor:
        return stats.two_prop_z(x1, n1, x2, n2)[1], Z_TEST
    k, big_k = round(x1), round(x1 + x2)
    return stats.fisher_exact(k, n1, big_k, n1 + n2), EXACT_TEST


def _build_grid(config, band: Band, dim, edges, bl, dl, measures, per_row, topline, min_units, total,
                needed, materiality_line, labels: list[str] | None = None) -> Grid:
    """The grid's cells, rates, multiples and excess, and the share of loans'
    tests. The dollar rates' shuffle test runs across every grid at once
    (_shuffle_tests), and the words come after it (_judge)."""
    inner = _accumulate(measures, per_row, list(zip(bl, dl)))
    for c in inner.values():
        _finish_cell(c, measures)
    blabels = labels or band_labels(edges)
    band_order = [x for x in blabels if x in set(bl)] + [x for x in _order(bl) if x not in blabels]
    dim_order = _order(dl)

    cells: dict[tuple[str, str], Cell] = dict(inner)
    for b in band_order:
        cells[(b, ALL)] = _merge([c for (bb, _), c in inner.items() if bb == b], measures)
    for d in dim_order:
        cells[(ALL, d)] = _merge([c for (_, dd), c in inner.items() if dd == d], measures)
    cells[(ALL, ALL)] = _merge(list(inner.values()), measures)
    # the pockets tested, and so the family the allowance for many tests covers (A2): one grid, one
    # rate, one comparison, the inner pockets only. The band and segment totals are never shown, and
    # counting them made a 2 x 2 grid's family 8 where A2 says 4 (the audit, item b)
    pockets = [k for k in cells if k[0] != ALL and k[1] != ALL]

    bench = config.benchmark
    benchmarks: dict[str, float | None] = {}
    for m in measures:
        if not m.is_rate:
            continue
        top = topline[m.name]
        floor = min_units.get(m.name, 0)
        in_scope = [c.rates[m.name].rate for c in inner.values()
                    if c.rates[m.name].rate is not None and c.rates[m.name].units >= floor]
        med = statistics.median(in_scope) if (bench is not None and in_scope) else None
        benchmarks[m.name] = med
        book = total.rates[m.name].sums()
        ln = needed.get(m.name)
        hi = m.higher_is
        pts = m.in_points
        for (b, d), c in cells.items():
            s = c.rates[m.name]
            if top is not None:
                # the bleed: losses over the topline, or for profit a shortfall under it
                s.excess = (s.num - top * s.den) if hi == "worse" else (top * s.den - s.num)
            s.dollars = s.excess                    # until _judge knows which comparison decides
            s.vs_topline = gap_of(s.rate, top, pts)
            rest_band = None
            if b != ALL and d != ALL:
                # the rest of its band: its row without it, the same rest vs_band is taken against
                rest_band = _minus(cells[(b, ALL)].rates[m.name].sums(), s.sums())
                rb = _rate(rest_band)
                if rb is not None:
                    s.excess_band = (s.num - rb * s.den) if hi == "worse" else (rb * s.den - s.num)
            if bench is None:
                continue
            if ln is not None:
                s.smallest_gap = stats.smallest_gap_for(ln, s.units, bench.confidence, bench.power)
            if (b, d) == (ALL, ALL):
                continue
            rest_book = _minus(book, s.sums())
            s.vs_rest = gap_of(s.rate, _rate(rest_book), pts)
            # Option A (the firm, 26 Sep 2026: "i think this makes most seense"): judged against the book, the
            # dollars are over the rest of the book, the same rest the gap and its test are taken against, as the
            # band's are over the rest of its band. `excess` (over the whole book) stays for the tie-out only
            rr = _rate(rest_book)
            if rr is not None:
                s.excess_rest = (s.num - rr * s.den) if hi == "worse" else (rr * s.den - s.num)
                s.dollars = s.excess_rest
            if b != ALL and d != ALL:
                s.vs_median = gap_of(s.rate, med, pts)
                s.vs_band = gap_of(s.rate, _rate(rest_band), pts)
            if (b, d) not in pockets:
                continue
            if yes_no(m):
                s.p_book, s.test = _proportion_p(s.num, s.units, rest_book, floor)
                s.p_band = _proportion_p(s.num, s.units, rest_band, floor)[0] if rest_band else None
            else:
                s.test = SHUFFLE_TEST if bench.shuffles else None        # filled in by _shuffle_tests
    return Grid(band=band.name, dimension=dim.name, band_labels=band_order, dim_labels=dim_order,
                cells=cells, benchmarks=benchmarks)


def _rate(sums: tuple) -> float | None:
    return sums[1] / sums[2] if sums[2] else None


def _judge(grid: Grid, config, measures, min_units, materiality_line) -> None:
    """The allowance for many tests, then each cell's words and materiality."""
    bench = config.benchmark
    if bench is None:
        return
    cells = grid.cells
    for m in measures:
        if not m.is_rate:
            continue
        floor = min_units.get(m.name, 0)
        hi = m.higher_is
        # allow for testing many pockets at once: across this grid's pockets, per comparison (A2)
        keys = [k for k in cells if k != (ALL, ALL)]
        # a pocket with too few losses is not tested (its reading says so), so it has no p-value and is not one
        # of the tests the allowance is for. Found by the tie-out of 28 Sep 2026: three such pockets still
        # showed a p-value and were counted, so the grid's allowance ran over 18 pockets where 15 were tested
        for k in keys:
            s = cells[k].rates[m.name]
            if hi == "worse" and s.events < bench.min_events:
                s.p_book = s.p_band = None
                s.test = None
        for attr in ("p_book", "p_band"):
            raw = [getattr(cells[k].rates[m.name], attr) for k in keys]
            # a shuffled p-value's own sampling error, before the allowance scales it (Borderline, B2a)
            ses = [stats.shuffle_se(p, cells[k].rates[m.name].shuffles)
                   if cells[k].rates[m.name].test == SHUFFLE_TEST else None for k, p in zip(keys, raw)]
            adj = adjust(raw, bench.many_tests)
            se_adj = adjust_se(raw, ses, bench.many_tests)
            for k, p, se in zip(keys, adj, se_adj):
                setattr(cells[k].rates[m.name], attr, p)
                setattr(cells[k].rates[m.name], "se_" + attr[2:], se)
        mat = materiality_line.get(m.name)
        mates = Counter(b for b, d in cells if b != ALL and d != ALL)
        # profit is read in points by the profit line on Control, on every tab (OC-32; NEXT-GOAL 3.2)
        line = profit_line(bench, materiality_line.get("gco_rate")) if m.in_points else None
        for (b, d), c in cells.items():
            s = c.rates[m.name]
            kw = dict(higher_is=hi, events=s.events, min_events=bench.min_events)
            # the reading and its test describe the same comparison: the pocket against the rest without it
            if line is not None:
                s.reading_topline = reading_gap(s.vs_rest, s.den, line, s.p_book, bench.confidence)
            else:
                s.reading_topline = reading_of(s.vs_rest, s.units, bench, floor, s.p_book, **kw)
            s.flag = s.reading_topline
            if b != ALL and d != ALL:
                if line is not None:
                    s.reading_median = reading_gap(s.vs_median, s.den, line, None, bench.confidence, tested=False,
                                                   units=s.units, min_units=floor)
                    s.reading_band = reading_gap(s.vs_band, s.den, line, s.p_band, bench.confidence)
                else:
                    s.reading_median = reading_of(s.vs_median, s.units, bench, floor, tested=False, **kw)
                    s.reading_band = reading_of(s.vs_band, s.units, bench, floor, s.p_band, **kw)
                if bench.compare_to == "peers":
                    # nothing in its band to compare it with, so the rest of the book (the firm, 26 Sep 2026)
                    s.alone = mates[b] == 1
                    if not s.alone:
                        s.flag = s.reading_band
                        # the same comparison gives the dollars, and so materiality and the ranking
                        s.by_band, s.dollars = True, s.excess_band
            if mat is not None and s.dollars is not None:
                s.material = s.dollars > 0 and s.dollars >= mat
            s.borderline = s.worse_borderline = None
            if (b, d) != (ALL, ALL):
                p, se, gap = (s.p_band, s.se_band, s.vs_band) if s.by_band else (s.p_book, s.se_book, s.vs_rest)
                if stats.borderline(p, se, bench.confidence) and p_decides(s.flag, gap, line):
                    s.borderline = stats.borderline_words(p, bench.confidence)
                    if worse_turns(s.flag, gap, line):
                        s.worse_borderline = s.borderline


def _shuffle_tests(config, measures, per_row, n, built, halved) -> None:
    """The shuffle test (B2) for every dollar rate, every grid and both
    comparisons, and for the split's halves: one perm.run, so one random order
    per shuffle serves them all (perm.py says why that is sound). Against the
    rest of the book, all the loans that entered the rate are shuffled;
    against the rest of its band, loans move only within their band; the
    split's halves only within their pocket."""
    bench = config.benchmark
    dollar = [m for m in measures if m.is_rate and not yes_no(m)]
    if bench is None or not dollar or not bench.shuffles or not n:
        return
    columns = [perm.Column(m.name, [v[0] if v is not None else None for v in per_row[m.name]],
                           [v[1] if v is not None else None for v in per_row[m.name]]) for m in dollar]
    book = perm.Structure("rest of the book", None, [])
    bands: dict[str, perm.Structure] = {}
    placed = []                                   # (grid, where its book layout is, where its band layout is)
    for grid, bname, keys in built:
        ids = {k: i for i, (k, _) in enumerate(grid.inner())}
        lay = [ids[k] for k in keys]
        if bname not in bands:
            codes = {lab: i for i, lab in enumerate(sorted({b for b, _ in keys}))}
            bands[bname] = perm.Structure(f"rest of the band ({bname})", [codes[b] for b, _ in keys], [])
        sb = bands[bname]
        for s in (book, sb):
            s.layouts.append(lay)
            for m in dollar:
                s.stats[(len(s.layouts) - 1, m.name)] = perm.RestGap()
        placed.append((grid, len(book.layouts) - 1, sb, len(sb.layouts) - 1))
    halves = []
    for grid, keys, sets in halved:
        # one structure per grid, shuffled within each pocket; one layout per comparison: the halves, or each
        # value against the rest of its pocket (side 0 is pocket 2g, side 1 is 2g + 1)
        ids = {k: i for i, (k, _) in enumerate(grid.inner())}
        group = [ids[k] if any(sides[i] is not None for sides, *_ in sets) else None for i, k in enumerate(keys)]
        s = perm.Structure(f"halves of {grid.band} x {grid.dimension}", group, [])
        for li, (sides, _, _, tested) in enumerate(sets):
            s.layouts.append([2 * g + sd if g is not None and sd is not None else -1 for g, sd in zip(group, sides)])
            for m in dollar:
                s.stats[(li, m.name)] = perm.HalfGap(pooled={ids[k] for k in tested.get(m.name, [])})
        halves.append((s, ids, sets))
    perm.run(n, columns, [book, *bands.values(), *(s for s, _, _ in halves)], bench.shuffles,
             perm.seed_of("one order per shuffle, shared by every test in the run"))
    for grid, bi, sb, si in placed:
        for m in dollar:
            got_book, got_band = book.stats[(bi, m.name)].answers, sb.stats[(si, m.name)].answers
            for i, (_, c) in enumerate(grid.inner()):
                s = c.rates[m.name]
                s.shuffles = bench.shuffles
                if i in got_book:
                    s.p_book, s.hits_book = got_book[i].p, got_book[i].hits
                if i in got_band:
                    s.p_band, s.hits_band = got_band[i].p, got_band[i].hits
                if s.p_book is None and s.p_band is None:
                    s.test = None           # nothing could be shuffled for this pocket (the adversarial pass)
    for s, ids, sets in halves:
        for li, (_, compare, pooled_by, tested) in enumerate(sets):
            for m in dollar:
                st = s.stats[(li, m.name)]
                for k in tested.get(m.name, []):
                    got = st.answers.get(ids[k])
                    idx, _, nh, nl = compare[k][m.name]
                    compare[k][m.name] = (idx, got.p if got else None, nh, nl)
                pooled = pooled_by.get(m.name)
                if pooled is not None and ("ratio" in pooled or "gap" in pooled) and st.pooled is not None:
                    pooled["ratio_p"], pooled["ratio_hits"], pooled["shuffles"] = (st.pooled.p, st.pooled.hits,
                                                                                  st.pooled.shuffles)


# --------------------------------------------------------------------------
# The third layer


def _split(grid: Grid, config: Config, bl, dl, split_vals, measures, per_row) -> list[str]:
    """Split every pocket of the grid by a third column. `each_value`: one
    layer per value (asset class 1, 2, 3, 4). `own_median`: two halves per
    pocket, at that pocket's own median, so the split says what the column adds
    beyond the band and segment already fixed (revolving debt moves with the
    score; one cut for everyone would mostly re-sort the score).

    The share of loans is tested here: each pocket's halves by A1 (pooled), and
    pooled across pockets by Mantel-Haenszel and CMH (A5, A6). A dollar rate's
    halves are shuffled within their pocket (B2), with every other shuffle
    test, and its pooled actual-against-expected is tested the same way; the
    allowance for many tests comes after that (_finish_split)."""
    field_, how = config.split
    if how == "each_value":
        labels = split_vals
        order = _order(labels)
    else:
        groups: dict[tuple, list[float]] = {}
        for b, d, v in zip(bl, dl, split_vals):
            if v is not None:
                groups.setdefault((b, d), []).append(v)
        med = {k: statistics.median(v) for k, v in groups.items()}
        labels = [NO_SPLIT_VALUE if v is None else (HIGH if v > med[(b, d)] else LOW)
                  for b, d, v in zip(bl, dl, split_vals)]
        order = [x for x in (HIGH, LOW, NO_SPLIT_VALUE) if x in set(labels)]
    cells3 = _accumulate(measures, per_row, list(zip(bl, dl, labels)))
    for c in cells3.values():
        _finish_cell(c, measures)
    grid.split_labels = order
    grid.split_cells = cells3
    if how != "own_median":
        _by_value(grid, config, cells3, order, measures)
        return labels
    grid.split_compare, grid.split_pooled, grid.split_tested = _compare(
        grid, lambda b, d: (cells3.get((b, d, HIGH)), cells3.get((b, d, LOW))), config, measures)
    return labels


def _by_value(grid: Grid, config: Config, cells3, order, measures) -> None:
    """A split by a category: each value of it set against the rest of its pocket (every other value there,
    together), by the same comparison the halves get, so with two values it is one against the other. And for a
    yes/no per loan, whether the values differ at all, pooled over the pockets: B3, the K-group Mantel-Haenszel
    statistic on K - 1 degrees of freedom (docs/statistics.md; kgroups.association), which with two values is
    the Cochran-Mantel-Haenszel test the halves get. No pocket is left out of it for being small (B3's rule)."""
    parts = list(order)
    grid.split_parts = parts
    rest: dict[tuple, Cell] = {}
    for (b, d), _ in grid.inner():
        here = {p: cells3[(b, d, p)] for p in parts if (b, d, p) in cells3}
        for p in here:
            others = [c for q, c in here.items() if q != p]
            if others:
                rest[(b, d, p)] = _merge(others, measures)
    for p in parts:
        grid.part_compare[p], grid.part_pooled[p], grid.part_tested[p] = _compare(
            grid, lambda b, d, p=p: (cells3.get((b, d, p)), rest.get((b, d, p))), config, measures)
    if len(parts) < 2:
        return
    from . import kgroups
    for m in measures:
        if not (m.is_rate and yes_no(m)):
            continue
        pockets = [kgroups.Pocket([cells3[(b, d, p)].rates[m.name].units if (b, d, p) in cells3 else 0
                                   for p in parts],
                                  [cells3[(b, d, p)].rates[m.name].events if (b, d, p) in cells3 else 0
                                   for p in parts]) for (b, d), _ in grid.inner()]
        try:
            a = kgroups.association(pockets, range(1, len(parts) + 1))
        except Exception:                   # a singular variance: no statistic, never a made-up one
            continue
        if a.p_general is not None:
            grid.split_general[m.name] = {"q": a.general, "df": a.df, "p": a.p_general, "pockets": a.pockets}


def _few_enough(field_: str, labels) -> None:
    """A category splits every pocket by each of its values, so a column with many values cuts each pocket into
    parts too thin to read: refused, said in words, never run."""
    said = too_many_values(field_, _values_counted(labels))
    if said:
        raise DataRefused(said)


def _values_counted(labels) -> int:
    """How many values a category holds for the six-value limits: a blank, a value answered missing and a loan with
    no date are parts of their own, never counted against the limit."""
    return len({v for v in labels if v not in (BLANK_LABEL, MISSING_RULE_LABEL, NO_DATE)})


def _few_enough_to_filter(field_: str, labels) -> None:
    """The Grids' filter builds every grid again on each value's loans: a column with many values is refused, said
    in words, never run."""
    said = too_many_to_filter(field_, _values_counted(labels))
    if said:
        raise DataRefused(said)


def _sides(grid: Grid, config: Config, labels) -> list[tuple]:
    """Each comparison a split makes, for the shuffle test: each row's side (0 or 1, None when it is in neither)
    and where its figures go. The halves are one comparison; a category makes one per value."""
    if config.split[1] == "own_median":
        return [([0 if lab == HIGH else 1 if lab == LOW else None for lab in labels], grid.split_compare,
                 grid.split_pooled, grid.split_tested)]
    return [([0 if lab == p else 1 for lab in labels], grid.part_compare[p], grid.part_pooled[p],
             grid.part_tested[p]) for p in grid.split_parts]


def _compare(grid: Grid, sides, config: Config, measures) -> tuple[dict, dict, dict]:
    """Two sides of every pocket compared, pocket by pocket and pooled: the high half against the low, or one
    value against the rest of its pocket. `sides(b, d)` gives the two cells. Returns what split_compare,
    split_pooled and split_tested hold."""
    compare: dict = {}
    pooled_by: dict = {}
    tested_by: dict = {}
    bench = config.benchmark
    floor = bench.min_units if bench else 2
    min_events = bench.min_events if bench else 0
    for m in measures:
        if not m.is_rate:
            continue
        strata, o_sum, e_sum, v_sum, pockets, high_worse, high_den = [], 0.0, 0.0, 0.0, 0, 0, 0.0
        tested = tested_by.setdefault(m.name, [])
        for (b, d), _ in grid.inner():
            h, lo = sides(b, d)
            if h is None or lo is None:
                continue
            sh, sl = h.rates[m.name], lo.rates[m.name]
            # the same floors as every other test (the third walk, defect 4: two halves of 27 loans
            # were compared, painted deep red and counted, under a 30-loan minimum)
            thin = sh.units < floor or sl.units < floor or sl.rate is None or sh.rate is None
            few = m.higher_is == "worse" and sh.events + sl.events < min_events
            if thin or few:
                compare.setdefault((b, d), {})[m.name] = (None, None, sh.units, sl.units)
                continue
            # profit: the high half's rate less the low half's, in points, never a multiple (NEXT-GOAL 3.2)
            idx = sh.rate - sl.rate if m.in_points else stats.multiple(sh.rate, sl.rate)
            # a yes/no per loan: A1, pooled; a dollar rate's p comes from the shuffle test
            p = stats.two_prop_z(sh.num, sh.units, sl.num, sl.units)[1] if yes_no(m) else None
            compare.setdefault((b, d), {})[m.name] = (idx, p, sh.units, sl.units)
            tested.append((b, d))
            pockets += 1
            # a high half with losses against a low half with none has no multiple, and is worse
            if m.in_points:
                worse = idx < 0
            elif idx is not None:
                worse = idx > 1 if m.higher_is == "worse" else idx < 1
            else:
                worse = sh.rate > sl.rate if m.higher_is == "worse" else sh.rate < sl.rate
            high_worse += worse
            if m.mode == "flagwt" and m.per == EACH_LOAN:
                # odds count loans; a dollar-weighted rate gets observed against expected below
                strata.append((sh.events, sh.units - sh.events, sl.events, sl.units - sl.events))
            # observed high-half total against what it would be at the low half's rate
            r = sl.rate
            o_sum += sh.num
            e_sum += r * sh.den
            high_den += sh.den
            n = sh.units
            s_dd = max(sh.syy - 2 * r * sh.sxy + r * r * sh.sxx, 0.0) * n / max(n - 1, 1)
            se_l = stats.ratio_se(*sl.sums()) or 0.0
            v_sum += s_dd + (sh.den * se_l) ** 2
        out = {"pockets": pockets, "high_worse": high_worse, "measure": m.name}
        z = stats.norm_s_inv(1 - (1 - (bench.confidence if bench else 0.95)) / 2)
        if m.in_points:
            # (O - E) over the high halves' booked dollars: how many points more (or less) the high halves
            # keep than they would at their own low halves' rates. No ratio, so no hole when E is at or
            # below zero (the audit, item a: -2.15, range 0.00 to -1.85)
            if high_den > 0:
                out["gap"] = (o_sum - e_sum) / high_den
                half = z * math.sqrt(v_sum) / high_den
                out["gap_lo"], out["gap_hi"] = out["gap"] - half, out["gap"] + half
        elif e_sum > 0:
            out["ratio"] = o_sum / e_sum
            if yes_no(m):
                out["ratio_p"] = (math.erfc(abs(o_sum - e_sum) / math.sqrt(v_sum) / math.sqrt(2))
                                  if v_sum > 0 else None)
            half = z * math.sqrt(v_sum) / e_sum
            out["ratio_lo"], out["ratio_hi"] = max(out["ratio"] - half, 0.0), out["ratio"] + half
        if strata:
            orr, lo_ci, hi_ci = stats.mantel_haenszel(strata, z)
            out.update({"odds": orr, "odds_lo": lo_ci, "odds_hi": hi_ci, "odds_p": stats.cmh_p(strata)})
            out["steady_p"], out["steady_pockets"] = stats.steadiness_p(strata, orr)
        pooled_by[m.name] = out
    return compare, pooled_by, tested_by


def _finish_split(grid: Grid, config: Config, measures) -> None:
    """The allowance for many tests on the split's pocket figures, once every
    p-value is in (the shuffle test fills the dollar rates')."""
    bench = config.benchmark
    for m in measures:
        if not m.is_rate:
            continue
        # the same allowance for many tests as every other pocket test, within this grid and measure
        # (asked on 25 Sep 2026: the split's "Luck alone" figures were the only ones shown without it)
        # a dollar rate's split p-values are shuffled (B2), bench.shuffles times: their own sampling error, before
        # the allowance scales it (Borderline, B2a); a yes/no's are the z test's and have none
        shuffled = bench is not None and not yes_no(m) and bool(bench.shuffles)
        se_of = (lambda p: stats.shuffle_se(p, bench.shuffles) if shuffled else None)       # noqa: E731
        if bench is not None:
            keys = [k for k, got in grid.split_compare.items() if m.name in got and got[m.name][1] is not None]
            raw = [grid.split_compare[k][m.name][1] for k in keys]
            adj = adjust(raw, bench.many_tests)
            for k, p, se in zip(keys, adj, adjust_se(raw, [se_of(x) for x in raw], bench.many_tests)):
                idx, _, nh, nl = grid.split_compare[k][m.name]
                grid.split_compare[k][m.name] = (idx, p, nh, nl)
                grid.split_se.setdefault(k, {})[m.name] = se
            pooled = grid.split_pooled.get(m.name, {})
            if pooled.get("ratio_p") is not None:
                # one pooled test per grid and measure, no allowance (the tab says so)
                pooled["ratio_se"] = stats.shuffle_se(pooled["ratio_p"], pooled.get("shuffles")) if shuffled else None
        if bench is not None and grid.split_parts:
            # a category: every value's pockets are one family, so a column with more values pays for more tests;
            # and each pooled figure is a family across the values, one test per value
            keys = [(v, k) for v in grid.split_parts for k, got in grid.part_compare[v].items()
                    if m.name in got and got[m.name][1] is not None]
            raw = [grid.part_compare[v][k][m.name][1] for v, k in keys]
            adj = adjust(raw, bench.many_tests)
            for (v, k), p, se in zip(keys, adj, adjust_se(raw, [se_of(x) for x in raw], bench.many_tests)):
                idx, _, nh, nl = grid.part_compare[v][k][m.name]
                grid.part_compare[v][k][m.name] = (idx, p, nh, nl)
                grid.part_se.setdefault(v, {}).setdefault(k, {})[m.name] = se
            for what in ("ratio_p", "odds_p", "steady_p"):
                vs = [v for v in grid.split_parts if grid.part_pooled[v].get(m.name, {}).get(what) is not None]
                raw = [grid.part_pooled[v][m.name][what] for v in vs]
                ses = [stats.shuffle_se(x, grid.part_pooled[v][m.name].get("shuffles"))
                       if shuffled and what == "ratio_p" else None for v, x in zip(vs, raw)]
                for v, p, se in zip(vs, adjust(raw, bench.many_tests), adjust_se(raw, ses, bench.many_tests)):
                    grid.part_pooled[v][m.name][what] = p
                    if what == "ratio_p":
                        grid.part_pooled[v][m.name]["ratio_se"] = se


# --------------------------------------------------------------------------


def _close(a: float, b: float, scale: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9 * max(1.0, abs(scale)))


def tie_out(grid: Grid, total: Cell, measures, n_rows: int) -> int:
    """Every inner cell of the grid, added up, against the book's totals
    accumulated in their own pass. Raises TieOutError naming the grid, the
    figure and both numbers; returns how many checks passed."""
    where = f"grid {grid.band} x {grid.dimension}"
    inner = [c for _, c in grid.inner()]
    checks = 0

    def check(what: str, got: float, want: float, scale: float) -> None:
        nonlocal checks
        if not _close(got, want, scale):
            raise TieOutError(f"{where}: {what} adds up to {got!r} across the cells, but the book says {want!r}")
        checks += 1

    rows = sum(c.rows for c in inner)
    check("rows", rows, n_rows, n_rows)
    # the third layer: every pocket's parts add back up to the pocket
    if grid.split_cells:
        for (b, d), c in grid.inner():
            parts = [p for (bb, dd, _), p in grid.split_cells.items() if (bb, dd) == (b, d)]
            check(f"split rows in {b} / {d}", sum(p.rows for p in parts), c.rows, c.rows)
            for m in measures:
                if m.is_rate:
                    check(f"split {m.name} numerator in {b} / {d}", math.fsum(p.rates[m.name].num for p in parts),
                          c.rates[m.name].num, c.rates[m.name].num)
    for m in measures:
        if not m.reconciles:
            continue
        t = total.rates[m.name]
        units = sum(c.rates[m.name].units for c in inner)
        lo = sum(c.rates[m.name].left_out for c in inner)
        check(f"{m.name} loans counted", units, t.units, n_rows)
        if m.is_rate:
            check(f"{m.name} loans left out", lo, t.left_out, n_rows)
            check(f"{m.name} numerator", math.fsum(c.rates[m.name].num for c in inner), t.num, t.num)
            check(f"{m.name} denominator", math.fsum(c.rates[m.name].den for c in inner), t.den, t.den)
            if t.rate is not None:
                check(f"{m.name} excess (must add to zero)",
                      math.fsum(c.rates[m.name].excess for c in inner), 0.0, t.num)
    return checks


def materiality(grid: Grid, m: Measure, total: Cell) -> list[stats.MaterialityRow]:
    """Evidence for the professional's materiality call, never the call: for
    each candidate threshold, how many pockets it keeps and how much of the
    grid's bleed they hold."""
    # the dollars Control's "judged against" picks, the same ones the materiality line is held to
    ex = [c.rates[m.name].dollars for _, c in grid.inner() if c.rates[m.name].dollars is not None]
    # profit is laddered on the book's GCO, the same dollars its materiality line is drawn from
    base = total.rates["gco_rate"] if m.name in PROFIT and "gco_rate" in total.rates else total.rates[m.name]
    return stats.materiality_ladder(ex, abs(base.num))
