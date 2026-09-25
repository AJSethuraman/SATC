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

from .config import Band, Config, Measure, MissingRule
from .ingest import BLANK, Bad, Table, cell_text, is_blank, parse_number

BLANK_LABEL = "(blank)"
NOT_NUMBER_LABEL = "(not a number)"
MISSING_RULE_LABEL = "(missing by rule)"
REASON_LABEL = {"blank": BLANK_LABEL, "not a number": NOT_NUMBER_LABEL, "missing by rule": MISSING_RULE_LABEL}

WORSE, BETTER, IN_LINE, THIN = ("worse than benchmark", "better than benchmark", "in line",
                                "too few loans to read")


class ColumnsMissing(Exception):
    """Columns the cube file names that the extract does not have."""

    def __init__(self, missing: list[tuple[str, str]], available: list[str]):
        self.missing = missing
        lines = [f"`{col}` (used by {who})" for col, who in missing]
        super().__init__("the extract has no column " + "; no column ".join(lines)
                         + f". Its columns are: {', '.join(available)}")


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
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


# --------------------------------------------------------------------------
# Comparisons (findings 2 and 8: an empty cell is never an index, and every
# threshold comes from the file)


def index_of(rate: float | None, base: float | None) -> float | None:
    """rate / base, or None. None and zero are refused explicitly: the VBA's
    IsNumeric(Empty) = True turned an empty cell into 0.00x (finding 2)."""
    if rate is None or base is None or base == 0:
        return None
    return rate / base


def reading_of(idx: float | None, units: int, bench) -> str | None:
    if idx is None or bench is None:
        return None
    if units < bench.min_units:
        return THIN
    if idx >= bench.worse_at:
        return WORSE
    if idx <= bench.better_at:
        return BETTER
    return IN_LINE


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


# --------------------------------------------------------------------------


def run(config: Config, table: Table) -> Result:
    warnings: list[str] = []
    measures = _resolve_columns(config, table, warnings)
    rows = table.rows
    n = len(rows)
    rules = config.missing

    for col in rules:
        if col not in table.columns:
            warnings.append(f"`missing:` has a rule for `{col}`, which is not a column in the extract; "
                            f"the rule was not applied")

    # One pass per column: every value is read once, however many grids use it.
    def col(name: str) -> list[Any]:
        return [r.get(name) for r in rows]

    bands = {}
    for b in config.bands:
        labels = band_labels(b.edges)
        out = []
        for raw in col(b.field):
            v, why = classify_number(raw, rules.get(b.field))
            out.append(band_of(v, b.edges, labels) if why is None else REASON_LABEL[why])
        bands[b.name] = out
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
            for raw_top, raw_per in zip(col(top_col), col(m.per)):
                d, why_d = classify_number(raw_per, rules.get(m.per))
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

    grids = []
    tie_outs = 0
    for b in config.bands:
        for d in config.dimensions:
            grid = _build_grid(config, b, d, bands[b.name], dims[d.name], measures, per_row, topline)
            tie_outs += tie_out(grid, total, measures, n)
            grids.append(grid)

    return Result(config=config, source=table.path, rows=n, measures=measures, total=total,
                  left_out=left_out, grids=grids, warnings=warnings, tie_outs=tie_outs)


def _resolve_columns(config: Config, table: Table, warnings: list[str]) -> tuple[Measure, ...]:
    have = set(table.columns)
    if config.key is None:
        warnings.append("no `key:` line: the cube runs, but no cell can be traced back to its loans")
    elif config.key not in have:
        warnings.append(f"`key:` names `{config.key}`, which is not a column in the extract: the cube runs, "
                        f"but no cell can be traced back to its loans")
    missing: list[tuple[str, str]] = []
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
                    s.num += v[0]
                    s.den += v[1]
                    s.units += 1
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


def _build_grid(config, band: Band, dim, bl, dl, measures, per_row, topline) -> Grid:
    inner = _accumulate(measures, per_row, list(zip(bl, dl)))
    for c in inner.values():
        _finish_cell(c, measures)
    blabels = band_labels(band.edges)
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
        in_scope = [c.rates[m.name].rate for c in inner.values()
                    if c.rates[m.name].rate is not None
                    and (bench is None or c.rates[m.name].units >= bench.min_units)]
        med = statistics.median(in_scope) if (bench is not None and in_scope) else None
        benchmarks[m.name] = med
        for (b, d), c in cells.items():
            s = c.rates[m.name]
            if top is not None:
                s.excess = s.num - top * s.den
            s.vs_topline = index_of(s.rate, top)
            if bench is None:
                continue
            s.reading_topline = reading_of(s.vs_topline, s.units, bench)
            if b != ALL and d != ALL:
                s.vs_median = index_of(s.rate, med)
                s.reading_median = reading_of(s.vs_median, s.units, bench)
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
