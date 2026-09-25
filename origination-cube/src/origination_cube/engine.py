"""From the extract to the cube: every band crossed with every dimension.

The question the cube answers is *where does the book bleed*: which pockets
lose more than their share. So every rate cell carries three comparisons.

  vs topline   the cell's rate over the whole book's rate. The same number is
               the cell's share of the losses over its share of the volume,
               which is why it is the bleed measure.
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

from . import stats
from .config import EACH_LOAN, Band, Config, Measure, MissingRule
from .ingest import BLANK, Bad, Table, cell_text, is_blank, parse_number

BLANK_LABEL = "(blank)"
NOT_NUMBER_LABEL = "(not a number)"
MISSING_RULE_LABEL = "(missing by rule)"
REASON_LABEL = {"blank": BLANK_LABEL, "not a number": NOT_NUMBER_LABEL, "missing by rule": MISSING_RULE_LABEL}

# The words a pocket can get. Each says which way (walkthrough defect 11: "gap
# could be luck" on a pocket that was better did not say so).
WORSE, BETTER, IN_LINE = "worse", "better", "in line"
UNSURE_WORSE, UNSURE_BETTER = "worse, but could be luck", "better, but could be luck"
THIN, FEW = "too few loans to test", "too few losses to test"
UNSURE = UNSURE_WORSE


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


def band_labels(edges: tuple[float, ...]) -> list[str]:
    e = [_fmt(x) for x in edges]
    if len(set(e)) < len(e):
        # two edges would print alike and their bands would merge under one label: keep the precision
        e = [f"{float(x):,.6g}" for x in edges]
    out = [f"under {e[0]}"]
    out += [f"{a} to under {b}" for a, b in zip(e, e[1:])]
    out.append(f"{e[-1]} and over")
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
    """rate / base, or None. None and zero are refused explicitly: the VBA's
    IsNumeric(Empty) = True turned an empty cell into 0.00x (finding 2)."""
    if rate is None or base is None or base == 0:
        return None
    return rate / base


def reading_of(idx: float | None, units: int, bench, min_units: float, p: float | None = None,
               tested: bool = True, higher_is: str = "worse", events: int | None = None,
               min_events: int = 0) -> str | None:
    """The word for a cell. A gap past a threshold counts only when the test
    says it is unlikely to be luck at the file's confidence (after any
    allowance for testing many pockets); the floors only stop a test being run
    on a handful of loans or losses. For a measure where higher is better
    (RANR), a rate below its comparison is the bad direction. `tested=False` is
    the median comparison, which has no peer group to test against."""
    if idx is None or bench is None:
        return None
    if units < min_units:
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
    vs_rest: float | None = None    # against the rest of the book (the book without this pocket)
    p_book: float | None = None     # the test of vs_rest
    vs_band: float | None = None    # against the rest of its band (its row, without it)
    p_band: float | None = None
    vs_dim: float | None = None     # against the rest of its dimension level (its column, without it)
    p_dim: float | None = None
    reading_band: str | None = None
    smallest_gap: float | None = None   # the smallest multiple of the book's rate this pocket could show
    events: int = 0                     # loans whose top is not zero: losses, for a loss rate
    flag: str | None = None             # the reading that decides, per `compare_to`
    material: bool | None = None        # excess at or over the materiality line (None: not applied)

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


@dataclass
class Grid:
    band: str
    dimension: str
    band_labels: list[str]
    dim_labels: list[str]
    cells: dict[tuple[str, str], Cell]          # (band label, dim label); margins use ALL
    benchmarks: dict[str, float | None]         # per rate measure: median of in-scope cell rates

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


# --------------------------------------------------------------------------


def _materiality_lines(bench, measures, total, warnings) -> dict[str, float]:
    """Each rate's materiality line in its own units. A share of the book's
    total applies to every rate; a dollar amount only to rates counted in
    dollars, and a rate counted in loans says so rather than borrow it."""
    out: dict[str, float] = {}
    if bench is None:
        return out
    kind, v = bench.materiality
    for m in measures:
        if not m.is_rate:
            continue
        if kind == "none":
            out[m.name] = 0.0
        elif kind == "share":
            out[m.name] = v * abs(total.rates[m.name].num)
        elif m.per == EACH_LOAN and m.mode == "flagwt":
            warnings.append(f"{m.name} counts loans, not dollars, so the dollar materiality line is not applied "
                            f"to it")
        else:
            out[m.name] = v
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
    for b in config.bands:
        read = [classify_number(raw, rules.get(b.field)) for raw in col(b.field)]
        edges = b.edges or cut_edges([v for v, why in read if why is None], b.count, b.cut)
        if not edges:
            raise ColumnsMissing([(b.field, f"band {b.name}: no readable numbers to cut")], table.columns)
        if b.count and len(edges) + 1 < b.count:
            warnings.append(f"band {b.name}: asked for {b.count} bands, got {len(edges) + 1} "
                            f"(`{b.field}` has too many repeated values to cut finer)")
        band_edges[b.name] = edges
        labels = band_labels(edges)
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
            for raw_top, raw_per in zip(col(top_col), per_vals):
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
                if why_t is None and m.mode == "flagwt" and t not in (0.0, 1.0):
                    t, why_t = None, "flag not 0 or 1"
                if why_t or why_d:
                    lo[(top_col, why_t) if why_t else (m.per, why_d)] += 1
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
            ln = stats.loans_needed(m.name, [v for v in per_row[m.name] if v is not None],
                                    bench.worse_at, bench.confidence, bench.power)
            needed[m.name] = ln
            min_units[m.name] = bench.min_units

    materiality_line = _materiality_lines(bench, measures, total, warnings)
    grids = []
    tie_outs = 0
    for b in config.bands:
        for d in config.dimensions:
            grid = _build_grid(config, b, d, band_edges[b.name], bands[b.name], dims[d.name], measures, per_row,
                               topline, min_units, total, needed, materiality_line)
            tie_outs += tie_out(grid, total, measures, n)
            grids.append(grid)

    return Result(config=config, source=table.path, rows=n, measures=measures, total=total,
                  left_out=left_out, grids=grids, warnings=warnings, tie_outs=tie_outs,
                  band_edges=band_edges, loans_needed=needed, min_units=min_units,
                  materiality_line=materiality_line, aged_out=aged_out)


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
            warnings.append(f"`{config.key}` repeats: {len(dupes):,} value(s) appear on more than one row "
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


def _build_grid(config, band: Band, dim, edges, bl, dl, measures, per_row, topline, min_units, total,
                needed, materiality_line) -> Grid:
    inner = _accumulate(measures, per_row, list(zip(bl, dl)))
    for c in inner.values():
        _finish_cell(c, measures)
    blabels = band_labels(edges)
    band_order = [x for x in blabels if x in set(bl)] + [x for x in _order(bl) if x not in blabels]
    dim_order = _order(dl)

    cells: dict[tuple[str, str], Cell] = dict(inner)
    for b in band_order:
        cells[(b, ALL)] = _merge([c for (bb, _), c in inner.items() if bb == b], measures)
    for d in dim_order:
        cells[(ALL, d)] = _merge([c for (_, dd), c in inner.items() if dd == d], measures)
    cells[(ALL, ALL)] = _merge(list(inner.values()), measures)

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
        for (b, d), c in cells.items():
            s = c.rates[m.name]
            if top is not None:
                # the bleed: losses over the topline, or for revenue a shortfall under it
                s.excess = (s.num - top * s.den) if hi == "worse" else (top * s.den - s.num)
            s.vs_topline = index_of(s.rate, top)
            if bench is None:
                continue
            if (b, d) != (ALL, ALL):
                s.vs_rest, s.p_book = stats.compare(s.sums(), _minus(book, s.sums()))
            if ln is not None:
                s.smallest_gap = stats.smallest_gap(s.units, ln.rate, ln.s_d, ln.x_bar, bench.confidence, bench.power)
            if b != ALL and d != ALL:
                s.vs_median = index_of(s.rate, med)
                s.vs_band, s.p_band = stats.compare(s.sums(), _minus(cells[(b, ALL)].rates[m.name].sums(), s.sums()))
                s.vs_dim, s.p_dim = stats.compare(s.sums(), _minus(cells[(ALL, d)].rates[m.name].sums(), s.sums()))
        if bench is None:
            continue
        # allow for testing many pockets at once: across this grid's pockets, per comparison
        keys = [k for k in cells if k != (ALL, ALL)]
        for attr in ("p_book", "p_band", "p_dim"):
            adj = adjust([getattr(cells[k].rates[m.name], attr) for k in keys], bench.many_tests)
            for k, p in zip(keys, adj):
                setattr(cells[k].rates[m.name], attr, p)
        mat = materiality_line.get(m.name)
        for (b, d), c in cells.items():
            s = c.rates[m.name]
            kw = dict(higher_is=hi, events=s.events, min_events=bench.min_events)
            # the reading and its test describe the same comparison: the pocket against the rest without it
            s.reading_topline = reading_of(s.vs_rest, s.units, bench, floor, s.p_book, **kw)
            s.flag = s.reading_topline
            if b != ALL and d != ALL:
                s.reading_median = reading_of(s.vs_median, s.units, bench, floor, tested=False, **kw)
                s.reading_band = reading_of(s.vs_band, s.units, bench, floor, s.p_band, **kw)
                if bench.compare_to == "peers":
                    s.flag = s.reading_band
            if mat is not None and s.excess is not None:
                s.material = s.excess > 0 and s.excess >= mat
    return Grid(band=band.name, dimension=dim.name, band_labels=band_order, dim_labels=dim_order,
                cells=cells, benchmarks=benchmarks)


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
    return stats.materiality_ladder(ex, abs(total.rates[m.name].num))
