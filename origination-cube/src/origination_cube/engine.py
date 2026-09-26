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
               reconciles as the rates do.
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
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from . import perm, stats
from .config import EACH_LOAN, PROFIT, Band, Config, Dimension, Measure, MissingRule
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


def band_labels(edges: tuple[float, ...], lo: float | None = None, hi: float | None = None) -> list[str]:
    """Bands as ranges: "620 - 679", with the lowest from the column's smallest
    value and the highest to its largest (the firm, 25 Sep 2026: "i want bands to
    be written in '0 - 660' form ... adding words over symbols makes a big
    difference to how cluttered it feels"). A band holds its first number and
    stops one step short of the next band's, the step being 1 for whole-number
    edges and the edges' own last decimal place otherwise."""
    dec = 0
    if min(abs(float(x)) for x in edges) < 100:          # scores and dollars read as whole numbers
        for x in edges:
            t = f"{float(x):.4f}".rstrip("0").rstrip(".")
            if "." in t:
                dec = max(dec, len(t.split(".")[1]))
    for d in range(dec, 7):
        step = 10.0 ** -d

        def f(x, d=d):
            return f"{x:,.{d}f}"

        first = f(math.floor(lo / step) * step) if lo is not None and lo < edges[0] else None
        last = f(math.ceil(hi / step) * step) if hi is not None and hi >= edges[-1] else None
        out = [f"{first} - {f(edges[0] - step)}" if first else f"up to {f(edges[0] - step)}"]
        out += [f"{f(a)} - {f(b - step)}" for a, b in zip(edges, edges[1:])]
        out.append(f"{f(edges[-1])} - {last}" if last else f"{f(edges[-1])} and up")
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
    the edges actually used are reported with the result."""
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
    return tuple(out)


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
    real = tested and p is not None and p < 1 - confidence
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
    if tested and (p is None or p >= 1 - bench.confidence):
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
    material: bool | None = None        # excess at or over the materiality line (None: not applied)
    # which test gave p_book and p_band (docs/statistics.md): "z" (A1), "exact" (B1, a pocket under
    # fewest loans), "shuffle" (B2, a dollar rate); None when nothing was tested
    test: str | None = None
    hits_book: int | None = None        # the shuffle test: shuffles with a gap at least as big, of `shuffles`
    hits_band: int | None = None
    shuffles: int | None = None

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
    aged_out: int = 0                                                       # loans younger than min_age_months
    loans_needed: dict[str, stats.LoansNeeded] = field(default_factory=dict)  # per rate, from the book
    min_units: dict[str, float] = field(default_factory=dict)               # per rate, the floor in use
    # the third layer (OC-23, OC-27): three-way pockets, tested like any other, and how
    # closely the split column moves with each number column that is cut into bands
    three_way: list["Grid"] = field(default_factory=list)
    split_moves_with: dict[str, float] = field(default_factory=dict)        # band column -> correlation


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


def age_filter(config: Config, table: Table, warnings: list[str]) -> tuple[list[dict], int]:
    """Keep loans at least `min_age_months` on book at the as-of date. Months on
    book are whole calendar months, one fewer when the as-of day of the month
    is earlier than the origination day (as the Portfolio Analysis Pack
    counts). A loan with no readable origination date is left out and counted,
    never assumed old enough."""
    if not config.min_age_months:
        return table.rows, 0
    from datetime import date as _date
    from .ingest import best_pattern, detect_date_format, parse_date
    orig = config.origination_date
    if orig not in table.columns:
        raise ColumnsMissing([(orig, "origination date, for loan age")], table.columns)
    det = detect_date_format(orig, [r.get(orig) for r in table.rows])
    fmt = det.resolved or best_pattern(det)
    as_of = config.as_of
    if isinstance(as_of, str) and as_of in table.columns:
        adet = detect_date_format(as_of, [r.get(as_of) for r in table.rows])
        vals = {parse_date(r.get(as_of), adet.resolved or best_pattern(adet)) for r in table.rows}
        vals = {v for v in vals if isinstance(v, _date)}
        if len(vals) != 1:
            raise NothingToCut(f"the as-of column `{as_of}` holds {len(vals)} different dates; loan age needs one")
        as_of = vals.pop()
    elif isinstance(as_of, str):
        as_of = _date.fromisoformat(as_of)
    kept, young, unreadable = [], 0, 0
    for r in table.rows:
        d = parse_date(r.get(orig), fmt)
        if not isinstance(d, _date):
            unreadable += 1
            continue
        months = (as_of.year - d.year) * 12 + (as_of.month - d.month) - (1 if as_of.day < d.day else 0)
        if months >= config.min_age_months:
            kept.append(r)
        else:
            young += 1
    warnings.append(f"loan age: {young:,} loans under {config.min_age_months} months on book at {as_of} were left "
                    f"out" + (f", and {unreadable:,} with no readable origination date" if unreadable else ""))
    return kept, young + unreadable


def _drop_outcome_cuts(config: Config, measures, warnings: list[str]) -> Config:
    """A band or dimension on a column that is the top of a rate would cut
    the book by its own outcome: every high-GCO band would show high GCO.
    Such a cut is left out and said so, never run."""
    from dataclasses import replace
    tops = {m.value if m.mode == "sumnum" else m.flag for m in measures if m.is_rate}
    marked = dict(config.not_cut)              # meanings never cut by: servicing data, dates, the key ...
    drop = tops | set(marked)
    keep_b = tuple(b for b in config.bands if b.field not in drop)
    keep_d = tuple(d for d in config.dimensions if d.field not in drop)
    for x in [b for b in config.bands if b.field in drop] + [d for d in config.dimensions if d.field in drop]:
        if x.field in tops:
            warnings.append(f"`{x.field}` is not cut by: it is the top of a rate, so cutting by it would cut the "
                            f"book by its own outcome")
        else:
            warnings.append(f"`{x.field}` is not cut by: `columns:` says it means {marked[x.field]}")
    if not keep_b or not keep_d:
        which = "band" if not keep_b else "dimension"
        raise NothingToCut(f"no {which} is left to cut by: every one listed is either the top of a rate or a "
                           f"column `columns:` says is not cut by ({', '.join(sorted(drop))}). Add a {which}, "
                           f"or change a column's meaning")
    return replace(config, bands=keep_b, dimensions=keep_d)


def run(config: Config, table: Table) -> Result:
    warnings: list[str] = []
    measures = _resolve_columns(config, table, warnings)
    config = _drop_outcome_cuts(config, measures, warnings)
    rows, aged_out = age_filter(config, table, warnings)
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
        labels = band_labels(edges, min(seen), max(seen)) if seen else band_labels(edges)
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
    halved: list[tuple[Grid, list, list]] = []         # grids split at each pocket's own median, and the labels
    tie_outs = 0
    for b in config.bands:
        for d in config.dimensions:
            grid = _build_grid(config, b, d, band_edges[b.name], bands[b.name], dims[d.name], measures, per_row,
                               topline, min_units, total, needed, materiality_line, band_label_sets[b.name])
            built.append((grid, b.name, list(zip(bands[b.name], dims[d.name]))))
            if split_vals is not None:
                labels = _split(grid, config, bands[b.name], dims[d.name], split_vals, measures, per_row)
                if config.split[1] == "own_median":
                    halved.append((grid, list(zip(bands[b.name], dims[d.name])), labels))
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
    _shuffle_tests(config, measures, per_row, n, built, halved)
    for g, _, _ in built:
        _judge(g, config, measures, min_units, materiality_line)
    for g, _, _ in halved:
        _finish_split(g, config, measures)
    moves_with: dict[str, float] = {}
    if config.split and config.split[1] == "own_median":
        for b in config.bands:
            r = _correlation(split_vals, [classify_number(raw, rules.get(b.field))[0] for raw in col(b.field)])
            if r is not None:
                moves_with[b.field] = r

    return Result(config=config, source=table.path, rows=n, measures=measures, total=total,
                  left_out=left_out, grids=grids, warnings=warnings, tie_outs=tie_outs,
                  band_edges=band_edges, loans_needed=needed, min_units=min_units,
                  materiality_line=materiality_line, aged_out=aged_out, three_way=three_way,
                  split_moves_with=moves_with)


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
    special = [BLANK_LABEL, NOT_NUMBER_LABEL, MISSING_RULE_LABEL]
    plain = sorted((x for x in set(labels) if x not in special), key=lambda s: s.lower())
    return plain + [x for x in special if x in set(labels)]


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
            s.vs_topline = gap_of(s.rate, top, pts)
            if bench is None:
                continue
            if ln is not None:
                s.smallest_gap = stats.smallest_gap_for(ln, s.units, bench.confidence, bench.power)
            if (b, d) == (ALL, ALL):
                continue
            rest_book, rest_band = _minus(book, s.sums()), None
            s.vs_rest = gap_of(s.rate, _rate(rest_book), pts)
            if b != ALL and d != ALL:
                s.vs_median = gap_of(s.rate, med, pts)
                rest_band = _minus(cells[(b, ALL)].rates[m.name].sums(), s.sums())
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
        for attr in ("p_book", "p_band"):
            adj = adjust([getattr(cells[k].rates[m.name], attr) for k in keys], bench.many_tests)
            for k, p in zip(keys, adj):
                setattr(cells[k].rates[m.name], attr, p)
        mat = materiality_line.get(m.name)
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
                    s.flag = s.reading_band
            if mat is not None and s.excess is not None:
                s.material = s.excess > 0 and s.excess >= mat


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
    for grid, keys, labels in halved:
        ids = {k: i for i, (k, _) in enumerate(grid.inner())}
        group = [ids[k] if lab in (HIGH, LOW) else None for k, lab in zip(keys, labels)]
        lay = [2 * g + (0 if lab == HIGH else 1) if g is not None else -1 for g, lab in zip(group, labels)]
        s = perm.Structure(f"halves of {grid.band} x {grid.dimension}", group, [lay])
        for m in dollar:
            tested = {ids[k] for k in grid.split_tested.get(m.name, [])}
            s.stats[(0, m.name)] = perm.HalfGap(pooled=tested)
        halves.append((grid, s, ids))
    perm.run(n, columns, [book, *bands.values(), *(s for _, s, _ in halves)], bench.shuffles,
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
    for grid, s, ids in halves:
        for m in dollar:
            st = s.stats[(0, m.name)]
            for k in grid.split_tested.get(m.name, []):
                got = st.answers.get(ids[k])
                idx, _, nh, nl = grid.split_compare[k][m.name]
                grid.split_compare[k][m.name] = (idx, got.p if got else None, nh, nl)
            pooled = grid.split_pooled.get(m.name)
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
        return labels
    bench = config.benchmark
    floor = bench.min_units if bench else 2
    min_events = bench.min_events if bench else 0
    for m in measures:
        if not m.is_rate:
            continue
        strata, o_sum, e_sum, v_sum, pockets, high_worse, high_den = [], 0.0, 0.0, 0.0, 0, 0, 0.0
        tested = grid.split_tested.setdefault(m.name, [])
        for (b, d), _ in grid.inner():
            h, lo = cells3.get((b, d, HIGH)), cells3.get((b, d, LOW))
            if h is None or lo is None:
                continue
            sh, sl = h.rates[m.name], lo.rates[m.name]
            # the same floors as every other test (the third walk, defect 4: two halves of 27 loans
            # were compared, painted deep red and counted, under a 30-loan minimum)
            thin = sh.units < floor or sl.units < floor or sl.rate is None or sh.rate is None
            few = m.higher_is == "worse" and sh.events + sl.events < min_events
            if thin or few:
                grid.split_compare.setdefault((b, d), {})[m.name] = (None, None, sh.units, sl.units)
                continue
            # profit: the high half's rate less the low half's, in points, never a multiple (NEXT-GOAL 3.2)
            idx = sh.rate - sl.rate if m.in_points else stats.multiple(sh.rate, sl.rate)
            # a yes/no per loan: A1, pooled; a dollar rate's p comes from the shuffle test
            p = stats.two_prop_z(sh.num, sh.units, sl.num, sl.units)[1] if yes_no(m) else None
            grid.split_compare.setdefault((b, d), {})[m.name] = (idx, p, sh.units, sl.units)
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
        grid.split_pooled[m.name] = out
    return labels


def _finish_split(grid: Grid, config: Config, measures) -> None:
    """The allowance for many tests on the split's pocket figures, once every
    p-value is in (the shuffle test fills the dollar rates')."""
    bench = config.benchmark
    for m in measures:
        if not m.is_rate:
            continue
        # the same allowance for many tests as every other pocket test, within this grid and measure
        # (asked on 25 Sep 2026: the split's "Luck alone" figures were the only ones shown without it)
        if bench is not None:
            keys = [k for k, got in grid.split_compare.items() if m.name in got and got[m.name][1] is not None]
            adj = adjust([grid.split_compare[k][m.name][1] for k in keys], bench.many_tests)
            for k, p in zip(keys, adj):
                idx, _, nh, nl = grid.split_compare[k][m.name]
                grid.split_compare[k][m.name] = (idx, p, nh, nl)


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
    ex = [c.rates[m.name].excess for _, c in grid.inner() if c.rates[m.name].excess is not None]
    # profit is laddered on the book's GCO, the same dollars its materiality line is drawn from
    base = total.rates["gco_rate"] if m.name in PROFIT and "gco_rate" in total.rates else total.rates[m.name]
    return stats.materiality_ladder(ex, abs(base.num))
