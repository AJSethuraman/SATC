"""The Look tab: what each number column holds, before its edges are chosen.

Fix 3.8 (docs/NEXT-GOAL.md), from the audit's item f: band edges were typed
blind. The redesign (docs/redesign-2026-09-26/README.md, section 4), with the
firm's two additions of 26 Sep 2026 (the mean beside the median; live bars and
range, "if truly cheap"):

    each number column gets a block (since 3 Oct 2026, each band column and
    the split; below): loans, blank, not a number, a value that
    looks like a code (profile.odd_values, the same detection Columns asks
    about) with its count, and the smallest, median, mean and largest of the
    other values; and a column chart of its counts, with the code on a red bar
    of its own to the left, so it doesn't flatten the rest.

    The bars are live. Set up counts each column once, in 200 equal slices
    between round numbers around its 1st and 99th percentile, plus the loans
    below and above them, on the hidden sheet _look. Each block has a Bars
    cell (10, 20 or 50) and a From and To; SUMIFS over the slices regroups the
    counts into the bars the chart draws, with a grey bar at each end for the
    loans outside the range. No SORT, FILTER or LET, so LibreOffice 24.2
    calculates them as Excel does (tests/recalc.py).

    The band edges typed on Columns are drawn as red dashed lines: an XY series
    per edge on the chart's second axes, its place worked out by formula from
    the Columns cell, so the lines follow that tab as it is typed.

The firm, at the bank, 29 Sep 2026: "Shouldn't we have SD markings on the look
tab? Our FICO seems fairly distributed but other stuff is not". Offered
standard deviations or percentiles, they chose percentiles: the 10th, 25th,
50th, 75th and 90th are listed in the block and drawn as thin grey lines,
labelled P10 to P90, placed by the same formula as the red lines, so they move
with Bars, From and To and one outside the range isn't drawn. Worked out in
Python from the values the spread uses, as Excel's PERCENTILE.INC does
(statistics.quantiles, method="inclusive"; numpy's default "linear").

The labels under the bars are short (the same day: Excel wrapped 24,000 as
"24,0/00"): 1,000 and over read 24k, a million and over 1.2M, with as many
decimals as the step between labels needs; anything smaller keeps the
column's own format (a FICO of 620, a ratio of 0.35).

    A scatter of the column that splits the pockets against each band column
    (a random 2,000 loans, the same every time), with the correlation beside
    it: a correlation near zero misses a U, and a picture does not
    (docs/statistics.md A9).

Which columns get a block (the firm, 3 Oct 2026, shown 40 blocks on 22 pages
against 4 on 4 for a 47-column book, chose "Banded + split, redraw on Run"):
the band columns chosen in the launcher, and the split column when it is a
number. Set up records every number column that could have a block
(`eligible`, on _look); the blocks drawn are those of them cut into bands or
splitting the pockets (`wanted`).

The shapes can't change on the same extract, so a Run doesn't redraw the blocks
(found 26 Sep 2026: it did, every Run), unless the band columns or the split it
reads from Control differ from those Look was drawn for, or a Treat as answer on
Columns has changed since: then the whole tab is drawn again from what the Run
reads, keeping any Bars, From or To typed (at the bank, 29 Sep 2026: a
-99,000,901 answered missing still set the smallest and the mean). Otherwise it
redraws the scatters only when the split or the band columns differ.

Nothing here changes a number PocketBook uses. A value that looks like a code is
counted on its own row and left out of the spread and the bars; whether it
really is a code is answered on Columns (Treat as). A value answered missing
there is counted on a row of its own and left out of everything else, dots included.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import dataclass, field
from decimal import Decimal

from openpyxl.chart import BarChart, Reference, ScatterChart, Series
from openpyxl.chart.label import DataLabel, DataLabelList
from openpyxl.chart.marker import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.text import RichText
from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties, RichTextProperties
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.pagebreak import Break

from . import house, profile
from .ingest import Bad, is_blank, parse_number

LOOK = "Look"
DATA = "_look"            # the counts and the chart's live feed, hidden
DOTS = "_dots"            # the scatters' loans, hidden
AFTER = "Columns"         # where the tab goes when it is new
SLICES = 200              # equal slices between the round numbers around the 1st and 99th percentile
BARS = (10, 20, 50)       # the Bars dropdown; each divides SLICES, so the default range regroups exactly
DEFAULT_BARS = 20
SLOTS, LOW, MIDDLE = 120, 10, 100   # the chart's categories: 10 for the low end bar, 100 for the bars, 10 high
EDGE_LINES = 24           # red dashed lines at most (every 20 on FICO makes about 20)
LABELS = 5                # labels under the bars, whatever their number
SAMPLE = 2000             # dots on a scatter, at most
SEED = 7                  # so the same loans are drawn every time
FIRST = 10                # first block's row, under the method note (the Bank checklist names C20)
BLOCK = 20                # rows per block, the gap under it included
PAGE_BLOCKS = 2           # blocks per printed page
GROUP = 13                # _look columns per number column
DATA_TOP = 4              # _look's first data row

# where a block's lines and inputs sit, from its top row
R_LOANS, R_BLANK, R_TEXT, R_CODE, R_MIN, R_MEDIAN, R_MEAN, R_MAX = range(1, 9)
R_MARKED = 9                                        # loans a Treat as answer of Missing leaves out
R_BARS, R_FROM, R_TO, R_TREAT = 10, 11, 12, 13
R_PCT = 14                                          # the five percentiles, one a row, to R_PCT + 4
PERCENTILES = (10, 25, 50, 75, 90)
RULES_ROW = 4                                       # _look column A: the Treat as answers Look was drawn with
ELIGIBLE_ROW = 5                                    # _look column A: every column that could have a block, as JSON
STATS_COL, VALUE_COL, SHARE_COL = 2, 3, 4          # B, C, D
CODE_AT, CHART_AT = "F", "H"

# _look, within a column's group (offsets from its first column)
G_LO, G_MID, G_COUNT, G_LABEL, G_VALUE, G_START, G_BAR, G_SLOT_LABEL, G_SLOT, G_EX, G_EY, G_EDGE, G_BAR_LABEL = \
    range(13)
# _look scalar rows (G_LABEL / G_VALUE)
S_NAME, S_LO, S_HI, S_BELOW, S_ABOVE, S_CODE, S_AT_CODE, S_MIN, S_MAX, S_N, S_FROM, S_TO, S_WIDTH, S_PER, \
    S_LOWTAIL, S_HIGHTAIL, S_EDGES, S_FMT = range(DATA_TOP, DATA_TOP + 18)
S_PCT = DATA_TOP + 18                               # the five percentiles, one a row, to S_PCT + 4
S_LSTEP = S_PCT + len(PERCENTILES)                  # the step between two labels under the bars
S_TALL = S_LSTEP + 1                                # the tallest bar: the top of every edge and percentile line
PCT_TOP = DATA_TOP + 2 * EDGE_LINES                 # G_EX / G_EY: the grey lines' two points each, under the red

METHOD = [
    ("The bars", "How many loans fall in each step between From and To. Pick 10, 20 or 50 bars and change the "
                 "range; the chart follows. The grey bar at each end holds the loans outside the range."),
    ("The red bar", "A value that looks like a code, such as a score of -9999, gets a red bar of its own left of "
                    "the chart, so it doesn't flatten the rest. Columns asks whether it means missing."),
    ("The lines", "Red dashed: the band edges typed on Columns. They follow that tab as you type, so you can try "
                  "edges here before the next Run; blank edges are cut at the Run, so no lines show. Grey: the "
                  "10th, 25th, 50th, 75th and 90th percentile, P10 to P90. A tenth of the loans on the chart lie "
                  "below P10, half below P50 (the median). Worked out as Excel's PERCENTILE.INC does."),
    ("How it counts", "A block is drawn for each band column chosen on Control, and for the split column when it "
                      "is numeric. A Run after either changes draws the tab again. Each column is counted once, in "
                      "200 equal slices around its 1st to 99th percentile. A range you type is counted to the "
                      "nearest slice."),
    ("The dots", "The split column against each band column: a random 2,000 loans, the same every time. If the "
                 "dots slope, the two move together, and part of a gap on Split may belong to the band column."),
]


@dataclass
class Shape:
    """One column, counted."""
    name: str
    rows: int
    blank: int
    text: int                                   # not a number
    code: float | None                          # a value that looks like a code, or None
    at_code: int
    values: list[float]                         # the other numbers, sorted
    fmt: str = "#,##0"                          # the spread's format
    marked: int = 0                             # left out: answered Missing under Treat as on Columns
    rule: object = None                         # that answer, as the Run's MissingRule
    pcts: list[float] = field(default_factory=list)   # the 10th, 25th, 50th, 75th and 90th percentile of values


def number_columns(table, cols, few_values: int = 12, known: dict | None = None) -> list[str]:
    """The columns that get a block, from Set up's profile.classify reading
    (`cols`): numbers to cut into bands, and numbers it asks about because every
    loan's differs (a balance with cents does). A 0/1 flag, a four-value class,
    a fixed-width loan number or a date has no edges to choose. `known`: Set
    up's facts by column, whose numbers are used rather than read again."""
    out = []
    known = known or {}
    for c in cols:
        if c.role == "question":
            f = known.get(c.name)
            if f is not None:
                count, nums, numbers = f.nonblank, set(f.numbers), len(f.numbers)
            else:
                vals = [parse_number(r.get(c.name)) for r in table.rows if not is_blank(r.get(c.name))]
                count, nums = len(vals), {v for v in vals if not isinstance(v, Bad)}
                numbers = sum(not isinstance(v, Bad) for v in vals)
            if not count or len(nums) <= few_values or numbers < profile.NUMERIC_SHARE * count:
                continue
        elif c.role != "band":
            continue
        out.append(c.name)
    return out


def shape_of(table, col: str, known=None, rule=None) -> Shape:
    """`known`: the column's facts from Set up, whose numbers are used rather
    than read again. `rule`: the column's Treat as answers of Missing, as the
    Run reads them; the values it catches are counted and left out of
    everything else here (at the bank, 29 Sep 2026: -99,000,901 answered
    missing still set the smallest and the mean)."""
    if known is not None:
        nums, blank, text = list(known.numbers), known.rows - known.nonblank, known.nonblank - len(known.numbers)
    else:
        nums, blank, text = [], 0, 0
        for r in table.rows:
            v = r.get(col)
            if is_blank(v):
                blank += 1
                continue
            p = parse_number(v)
            if isinstance(p, Bad):
                text += 1
            else:
                nums.append(p)
    everything = nums                                   # as recorded, answered missing included
    kept_nums = [x for x in nums if not caught(x, rule)]
    marked = len(everything) - len(kept_nums)
    nums = kept_nums
    code = next((q["value"] for q in profile.odd_values(col, nums) if q["pattern"] == "repeated_value"), None)
    values = sorted(x for x in nums if x != code)
    s = Shape(col, len(table.rows), blank, text, code, len(nums) - len(values), values, marked=marked, rule=rule)
    if values:
        s.fmt = _format(values)
    s.pcts = percentiles(values)
    return s


def caught(v: float, rule) -> bool:
    """True when a Treat as answer of Missing catches the value: the Run's own test (engine._caught)."""
    if rule is None:
        return False
    from .engine import _caught
    return _caught(v, rule)


def rules_key(rules: dict | None, columns) -> str:
    """The Treat as answers for these columns, in one line: Look is drawn again when it changes."""
    parts = []
    for c in sorted(columns):
        r = (rules or {}).get(c)
        floor = getattr(r, "at_or_below", None)
        if r is not None and (r.below is not None or r.above is not None or r.values or floor is not None):
            parts.append(f"{c}:{r.below}:{r.above}:{sorted(float(v) for v in r.values if isinstance(v, (int, float)))}"
                         + (f":{floor}" if floor is not None else ""))
    return "|".join(parts)


def drawn_columns(wb) -> list[str]:
    """The columns Look has a block for, in their order."""
    if DATA not in wb.sheetnames:
        return []
    hs = wb[DATA]
    return [str(hs.cell(row=1, column=i).value) for i in range(2, hs.max_column + 1) if hs.cell(row=1, column=i).value]


def eligible_columns(wb) -> list[str]:
    """Every column Set up found could have a block (a number column), in order. A workbook drawn before this was
    recorded gives the columns drawn."""
    if DATA not in wb.sheetnames:
        return []
    got = wb[DATA].cell(row=ELIGIBLE_ROW, column=1).value
    try:
        out = json.loads(got) if isinstance(got, str) else None
    except ValueError:
        out = None
    return [str(c) for c in out] if isinstance(out, list) else drawn_columns(wb)


def wanted(eligible, bands, split: str | None) -> list[str]:
    """The columns that get a block (the firm, 3 Oct 2026, "Banded + split"): of the eligible, in their order,
    those cut into bands and the one that splits the pockets."""
    cut = set(bands or ())
    return [c for c in eligible if c in cut or c == split]


def columns_moved(wb, bands, split: str | None) -> bool:
    """True when the band columns or the split call for blocks other than those Look has."""
    if DATA not in wb.sheetnames or LOOK not in wb.sheetnames:
        return False
    return wanted(eligible_columns(wb), bands, split) != drawn_columns(wb)


def answers_moved(wb, rules: dict | None) -> bool:
    """True when the Treat as answers differ from those Look was drawn with."""
    if DATA not in wb.sheetnames or LOOK not in wb.sheetnames:
        return False
    was = wb[DATA].cell(row=RULES_ROW, column=1).value or ""
    return str(was) != rules_key(rules, drawn_columns(wb))


def _format(values: list[float]) -> str:
    """Scores and dollars read as whole numbers; a ratio keeps its decimals."""
    if all(float(x).is_integer() for x in values):
        return "#,##0"
    big = max(abs(values[0]), abs(values[-1]), abs(statistics.median(values)))
    return "#,##0" if big >= 100 else "#,##0.0" if big >= 10 else "0.00" if big >= 1 else "0.000"


def percentiles(values: list[float]) -> list[float]:
    """The 10th, 25th, 50th, 75th and 90th percentile of the sorted values, as Excel's PERCENTILE.INC and numpy's
    default ("linear") work them out: the value at position p x (n - 1), counted from 0, read between its two
    neighbours (statistics.quantiles, method="inclusive"). The 50th is the median."""
    if len(values) < 2:
        return [float(values[0])] * len(PERCENTILES) if values else []
    cuts = statistics.quantiles(values, n=100, method="inclusive")
    return [cuts[p - 1] for p in PERCENTILES]


def _nice(raw: float) -> float:
    """The smallest of 1, 2 or 5 times a power of ten that is at least raw:
    a width a person would type as "every 20"."""
    if raw <= 0:
        return 1.0
    k = math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        w = float(f"{m * 10 ** k:.12g}")
        if w >= raw:
            return w
    return w


def span(values: list[float]) -> tuple[float, float]:
    """The range the slices cover: round numbers around the 1st and 99th percentile, so one $2m loan or a
    stray score of 12 doesn't squash everything into one bar, and the default bars start on round numbers."""
    n = len(values)
    lo, hi = values[int(0.01 * (n - 1))], values[math.ceil(0.99 * (n - 1))]
    if hi <= lo:
        lo, hi = values[0], values[-1]
    if hi <= lo:                                             # one value only
        return lo - 0.5, lo + 0.5
    unit = _nice((hi - lo) / 10)
    # whole steps worked out in exact decimals, so a round edge is that number and not 1.2000000000000002 (the full
    # tie-out of 28 Sep 2026 found loans at exactly 0.24 counted a bar low), at any scale: a fixed number of decimal
    # places would flatten a column whose values are all below it (Codex on #404)
    step = Decimal(repr(unit))
    return float(step * math.floor(lo / unit)), float(step * math.ceil(hi / unit))


def slices(values: list[float], lo: float, hi: float) -> tuple[list[int], int, int]:
    """Each value counted into one of SLICES equal slices from lo to hi (hi itself in the last), and the counts
    below lo and above hi."""
    counts, below, above = [0] * SLICES, 0, 0
    w = (hi - lo) / SLICES
    for v in values:
        if v < lo:
            below += 1
        elif v > hi:
            above += 1
        else:
            # a value on a slice's lower edge belongs to that slice: rounded before cutting, so float error
            # (0.24 / 0.006 = 39.99999999) never drops it into the slice below
            counts[min(int(round((v - lo) / w, 9)), SLICES - 1)] += 1
    return counts, below, above


def regroup(values: list[float], bars: int, lo: float, hi: float, frm: float, to: float) -> tuple[list[int], int, int]:
    """What the live formulas give, worked out in Python from the loans (for the tests): the slices from lo to hi
    regrouped into `bars` equal bars from `frm` to `to`, each slice by its middle, and the two end bars."""
    counts, below, above = slices(values, lo, hi)
    w = (hi - lo) / SLICES
    mids = [lo + (i + 0.5) * w for i in range(SLICES)]
    step = (to - frm) / bars
    out = []
    for j in range(bars):
        a, b = frm + j * step, frm + (j + 1) * step
        last = j == bars - 1
        out.append(sum(k for m, k in zip(mids, counts) if m >= a and (m <= b if last else m < b)))
    low = below + sum(k for m, k in zip(mids, counts) if m < frm)
    high = above + sum(k for m, k in zip(mids, counts) if m > to)
    return out, low, high


# --------------------------------------------------------------------------
# The tab


def write_look(wb, table, columns, split: str | None = None, bands=(), known: dict | None = None,
               edge_rows: dict | None = None, treat_rows: dict | None = None, rules: dict | None = None,
               keep_inputs: bool = False, eligible=None) -> None:
    """Write (or write again) the Look tab and its hidden sheets. `columns` are the number columns to show,
    `split` the column that splits the pockets and `bands` the band columns it is plotted against. `known` is Set
    up's facts by column, so no column's numbers are read twice; `edge_rows` each column's row on Columns (its
    Band edges cell feeds the red lines), `treat_rows` each column's first odd value there. `rules` the Treat as
    answers of Missing, as the Run reads them. `keep_inputs`: a Bars, From or To the analyst typed stays.
    `eligible`: every column that could have a block, kept for the Run's redraw; None keeps what was recorded, or
    the columns shown when nothing was."""
    typed = _typed_inputs(wb) if keep_inputs else {}
    if eligible is None:
        eligible = eligible_columns(wb) if DATA in wb.sheetnames else list(columns)
    eligible = [c for c in eligible if c in table.columns]
    at = wb.sheetnames.index(LOOK) if LOOK in wb.sheetnames else (
        wb.sheetnames.index(AFTER) + 1 if AFTER in wb.sheetnames else None)
    for t in (LOOK, DATA, DOTS):
        if t in wb.sheetnames:
            del wb[t]
    ws = wb.create_sheet(LOOK, at)
    hs = wb.create_sheet(DATA)
    hs.sheet_state = "hidden"
    columns = [c for c in columns if c in table.columns]
    hs.cell(row=1, column=1, value="columns")                     # read back by refresh()
    for i, c in enumerate(columns, start=2):
        hs.cell(row=1, column=i, value=c)
    known = known or {}
    shapes = {c: shape_of(table, c, known.get(c), (rules or {}).get(c)) for c in columns}
    # L1: B fits the longest stat label this tab writes, C the longest value (the survey's per-character 0.9 for
    # Calibri 10); the rest as drawn
    for col, w in zip("ABCDEFGH", (2, label_width(shapes.values()), value_width(shapes.values()), 9, 2, 13, 2, 10)):
        ws.column_dimensions[col].width = w
    house.title_band(ws, "Look", "Each band column and the split before you choose band edges.", 2, 17)
    top = house.method_note(ws, 3, 2, 17, METHOD)
    assert top == FIRST, top
    hs.cell(row=RULES_ROW, column=1, value=rules_key(rules, columns) or None)
    hs.cell(row=ELIGIBLE_ROW, column=1, value=json.dumps(eligible))
    dv = DataValidation(type="list", formula1=f'"{",".join(str(b) for b in BARS)}"', allow_blank=False,
                        showErrorMessage=True)
    dv.error = "Pick 10, 20 or 50 bars."
    ws.add_data_validation(dv)
    r = FIRST
    for i, c in enumerate(columns):
        if i and i % PAGE_BLOCKS == 0:
            _page(ws, r)
        _block(ws, hs, r, shapes[c], 2 + GROUP * i, dv, (edge_rows or {}).get(c), (treat_rows or {}).get(c))
        for row, v in typed.get(c, {}).items():
            ws.cell(row=r + row, column=VALUE_COL).value = v
        r += BLOCK
    hs.cell(row=2, column=1, value=r)                             # where the scatters start, for refresh()
    end = _scatters(wb, ws, r, table, shapes, split, [b for b in bands if b != split])
    ws.print_area = f"A1:Q{end}"                                   # to the foot of the last chart
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.freeze_panes = "A2"


def _typed_inputs(wb) -> dict[str, dict[int, object]]:
    """Each block's Bars, From and To as the analyst left them, when they differ from what Look wrote: a From
    and To still at the drawn range are left to follow the new one."""
    if DATA not in wb.sheetnames or LOOK not in wb.sheetnames:
        return {}
    hs, ws, out = wb[DATA], wb[LOOK], {}
    for i, c in enumerate(drawn_columns(wb)):
        g, r = 2 + GROUP * i, FIRST + BLOCK * i
        drawn = {R_BARS: DEFAULT_BARS, R_FROM: hs.cell(row=S_LO, column=g + G_VALUE).value,
                 R_TO: hs.cell(row=S_HI, column=g + G_VALUE).value}
        now = {k: ws.cell(row=r + k, column=VALUE_COL).value for k in drawn}
        out[c] = {k: v for k, v in now.items() if isinstance(v, (int, float)) and v != drawn[k]}
    return out


def refresh(wb, table, split: str | None = None, bands=(), rules: dict | None = None) -> bool:
    """At Run, in the open workbook: the scatters again, and only when the split or the band columns differ
    from those drawn. The blocks are left as they are: their shapes can't change on the same extract. A
    workbook set up before the Look tab existed gets it at its next Set up. True when anything was redrawn."""
    if DATA not in wb.sheetnames or LOOK not in wb.sheetnames:
        return False
    hs, ws = wb[DATA], wb[LOOK]
    bands = [b for b in bands if b != split]
    if hs.cell(row=3, column=1).value == _drawn(split, bands):
        return False
    start = hs.cell(row=2, column=1).value
    if not isinstance(start, int):
        return False
    ws._charts = [ch for ch in ws._charts if _anchor_row(ch) < start]
    for rng in [m for m in ws.merged_cells.ranges if m.min_row >= start]:
        ws.unmerge_cells(str(rng))
    if ws.max_row >= start:
        ws.delete_rows(start, ws.max_row - start + 1)
    ws.row_breaks.brk = [b for b in ws.row_breaks.brk if b.id < start - 2]
    shapes = {}
    for i in range(2, hs.max_column + 1):
        name = hs.cell(row=1, column=i).value
        if name:
            g = 2 + GROUP * (i - 2)
            code = hs.cell(row=S_CODE, column=g + G_VALUE).value
            fmt = hs.cell(row=S_FMT, column=g + G_VALUE).value or "#,##0"
            shapes[str(name)] = Shape(str(name), 0, 0, 0, code if isinstance(code, (int, float)) else None, 0, [],
                                      fmt, rule=(rules or {}).get(str(name)))
    if DOTS in wb.sheetnames:
        del wb[DOTS]
    end = _scatters(wb, ws, start, table, shapes, split, bands)
    ws.print_area = f"A1:Q{end}"
    return True


def _drawn(split, bands) -> str:
    return f"{split or ''}|{','.join(bands) if split else ''}"


def _anchor_row(ch) -> int:
    a = ch.anchor
    if isinstance(a, str):
        return int("".join(x for x in a if x.isdigit()))
    return a._from.row + 1


def _page(ws, r: int) -> None:
    """A new printed page before the block at row r. The break sits in the gap
    row above, not on the chart's top edge, which would print a stray line."""
    ws.row_breaks.append(Break(id=r - 2))


def _axis(ax, vals: list[float], fmt: str) -> None:
    """A scatter axis on round numbers, set rather than left to the program:
    Excel starts a FICO axis at 0 and squashes every dot to the right."""
    lo, hi = min(vals), max(vals)
    unit = _nice((hi - lo) / 8)                                     # about eight gridlines
    ax.scaling.min, ax.scaling.max = math.floor(lo / unit) * unit, math.ceil(hi / unit) * unit
    if ax.scaling.max <= ax.scaling.min:
        ax.scaling.max = ax.scaling.min + unit
    ax.majorUnit = unit
    ax.number_format = axis_format(ax.scaling.min, unit, fmt)
    ax.delete = False


def axis_format(lo: float, unit: float, fmt: str) -> str:
    """A scatter axis's numbers, short as the bars' labels are: 200k, 1.5M. Only when every tick is a whole
    thousand (the step is 1,000 or more), so none is rounded; a millions step shows each tick exactly. A
    condition in a format is left to axes that start at 0 or above, whose negatives never show."""
    if unit < 1000:
        return fmt
    if lo < 0:
        return '#,##0,,"M"' if unit >= 1e6 else '#,##0.0,,"M"' if unit >= 1e5 else '#,##0,"k"'
    if unit >= 1e5:
        return '[>=1000000]0.0,,"M";[>=1000]#,##0,"k";0'
    return '[>=1000]#,##0,"k";0'


#: the stat labels every block and scatter writes in B (L1); a likely code's label is added per column
STAT_LABELS = ("Loans", "Blank", "Not a number", "Likely a code", "Smallest", "Median", "Mean", "Largest",
               "Answered missing, left out", "Bars", "From", "To", "Loans with both values", "Dots shown",
               "Moves together (correlation)") + tuple(
    f"{p}th percentile (P{p})" + (", the median" if p == 50 else "") for p in PERCENTILES)
#: Calibri 10 against Excel's width unit (the survey: 0.9 fits the longest label without a gap)
LOOK_PER_CHAR = 0.9


def label_width(shapes) -> float:
    """Look's B: the longest stat label + 2 (L1)."""
    codes = [f"At {_plain(s.code)}, likely a code" for s in shapes if s.code is not None]
    # one width unit a character: at 0.9 "50th percentile (P50), the median" was cut short (the evening tie-out)
    return house.fit(list(STAT_LABELS) + codes, floor=20, cap=40)


def value_width(shapes) -> float:
    """Look's C: the longest value any block shows, in its column's format, + 2, at least 10 (L1)."""
    texts = ["none found"]
    for s in shapes:
        dec = 2 if "." in s.fmt else 0
        texts += [f"{v:,.{dec}f}" for v in ([s.rows] + (s.values[:1] + s.values[-1:] if s.values else [])
                                               + list(s.pcts or []))]
    return house.fit(texts, floor=10, cap=20)


def _bar_row(ws, r: int, text: str, last: int = SHARE_COL) -> None:
    for col in range(STATS_COL, last + 1):
        ws.cell(row=r, column=col).fill = house.fill(house.INK)
    c = ws.cell(row=r, column=STATS_COL, value=text)
    c.font = Font(name="Arial", bold=True, size=11, color=house.PAPER)
    ws.row_dimensions[r].height = 18


def _line(ws, r: int, label: str | None, value=None, share=None, fmt: str = "#,##0") -> None:
    a = ws.cell(row=r, column=STATS_COL, value=label)
    a.font = Font(name="Calibri", size=10, color=house.INK_TEXT)
    if value is not None:
        b = ws.cell(row=r, column=VALUE_COL, value=value)
        b.number_format = fmt
        b.font = Font(name="Calibri", size=10, color=house.INK_TEXT)
        b.alignment = Alignment(horizontal="center")
    if share is not None:
        d = ws.cell(row=r, column=SHARE_COL, value=share)
        d.number_format = "0.0%"
        d.font = Font(name="Calibri", size=10, color=house.SLATE)
        d.alignment = Alignment(horizontal="center")


def _L(col: int, row: int, absolute: bool = True) -> str:
    c = get_column_letter(col)
    return f"${c}${row}" if absolute else f"{c}{row}"


def _block(ws, hs, r: int, s: Shape, g: int, dv, edge_row: int | None, treat) -> None:
    """One column's block at row r, its counts and live feed in _look's group from column g."""
    n = s.rows or 1
    _bar_row(ws, r, s.name)
    _line(ws, r + R_LOANS, "Loans", s.rows)
    _line(ws, r + R_BLANK, "Blank", s.blank, s.blank / n)
    _line(ws, r + R_TEXT, "Not a number", s.text, s.text / n)
    if s.code is not None:
        _line(ws, r + R_CODE, f"At {_plain(s.code)}, likely a code", s.at_code, s.at_code / n)
    else:
        _line(ws, r + R_CODE, "Likely a code", "none found")
    if s.values:
        _line(ws, r + R_MIN, "Smallest", s.values[0], fmt=s.fmt)
        _line(ws, r + R_MEDIAN, "Median", statistics.median(s.values), fmt=s.fmt)
        _line(ws, r + R_MEAN, "Mean", statistics.fmean(s.values), fmt=s.fmt)
        _line(ws, r + R_MAX, "Largest", s.values[-1], fmt=s.fmt)
    else:
        _line(ws, r + R_MIN, "No numbers to show.")
    if s.marked:
        _line(ws, r + R_MARKED, "Answered missing, left out", s.marked, s.marked / n)
    pcts = s.pcts
    for k, (p, v) in enumerate(zip(PERCENTILES, pcts)):
        _line(ws, r + R_PCT + k, f"{p}th percentile (P{p})" + (", the median" if p == 50 else ""), v, fmt=s.fmt)
    if treat is not None and treat[1].startswith("negatives|"):
        row = treat[0]
        cell = f"Columns!$H${row}"
        c = ws.cell(row=r + R_TREAT, column=STATS_COL, value=(
            f'=IF({cell}="Missing","Answered on Columns: its negative values mean missing.",IF({cell}="Real",'
            f'"Answered on Columns: its negative values are real.","Not answered on Columns yet (row {row}): its '
            f'negative values are used as recorded."))'))
        c.font = Font(name="Calibri", size=9, italic=True, color=house.SLATE)
    elif s.code is not None and treat is not None and treat[1].startswith("repeated_value|"):
        row = treat[0]
        cell = f"Columns!$H${row}"
        c = ws.cell(row=r + R_TREAT, column=STATS_COL, value=(
            f'=IF({cell}="Missing","Answered on Columns: {_plain(s.code)} means missing.",IF({cell}="Real",'
            f'"Answered on Columns: {_plain(s.code)} is a real value.","Not answered on Columns yet (row {row}): '
            f'{_plain(s.code)} is used as recorded."))'))
        c.font = Font(name="Calibri", size=9, italic=True, color=house.SLATE)
    if not s.values:
        return
    lo, hi = span(s.values)
    counts, below, above = slices(s.values, lo, hi)
    L = lambda off: get_column_letter(g + off)                # noqa: E731
    V = lambda row: _L(g + G_VALUE, row)                       # noqa: E731
    hs.cell(row=DATA_TOP - 1, column=g, value=s.name)
    for off, h in ((G_LO, "slice from"), (G_MID, "middle"), (G_COUNT, "loans"), (G_START, "bar from"),
                   (G_BAR, "bar loans"), (G_SLOT_LABEL, "chart label"), (G_SLOT, "chart loans"),
                   (G_EX, "edge x"), (G_EY, "edge y"), (G_EDGE, "edge"), (G_BAR_LABEL, "bar label")):
        hs.cell(row=DATA_TOP - 2, column=g + off, value=h)
    w = (hi - lo) / SLICES
    for i, k in enumerate(counts):
        hs.cell(row=DATA_TOP + i, column=g + G_LO, value=lo + i * w)
        hs.cell(row=DATA_TOP + i, column=g + G_MID, value=lo + (i + 0.5) * w)
        hs.cell(row=DATA_TOP + i, column=g + G_COUNT, value=k)
    # the inputs, on Look: they change the chart at once
    ws.cell(row=r + R_BARS, column=STATS_COL, value="Bars")
    ws.cell(row=r + R_FROM, column=STATS_COL, value="From")
    ws.cell(row=r + R_TO, column=STATS_COL, value="To")
    for rr, v, fmt in ((R_BARS, DEFAULT_BARS, "0"), (R_FROM, lo, s.fmt), (R_TO, hi, s.fmt)):
        ws.cell(row=r + rr, column=STATS_COL).font = Font(name="Calibri", size=10, color=house.INK_TEXT)
        c = ws.cell(row=r + rr, column=VALUE_COL, value=v)
        house.changes_now(c)
        c.number_format = fmt
        c.alignment = Alignment(horizontal="center")
    dv.add(ws.cell(row=r + R_BARS, column=VALUE_COL))
    bars_in, from_in, to_in = (f"{LOOK}!{_L(VALUE_COL, r + x)}" for x in (R_BARS, R_FROM, R_TO))
    cnt = f"${L(G_COUNT)}${DATA_TOP}:${L(G_COUNT)}${DATA_TOP + SLICES - 1}"
    mid = f"${L(G_MID)}${DATA_TOP}:${L(G_MID)}${DATA_TOP + SLICES - 1}"
    code_val = s.code if s.code is not None else None
    vmin, vmax = s.values[0], s.values[-1]
    scal = {S_NAME: ("column", s.name), S_LO: ("slices from", lo), S_HI: ("slices to", hi),
            S_BELOW: ("loans below the slices", below), S_ABOVE: ("loans above the slices", above),
            S_CODE: ("likely code", code_val), S_AT_CODE: ("loans at the code", s.at_code),
            S_MIN: ("smallest", vmin), S_MAX: ("largest", vmax),
            S_N: ("bars", f"={bars_in}"), S_FROM: ("from", f"={from_in}"), S_TO: ("to", f"={to_in}"),
            S_WIDTH: ("bar width", f"=({V(S_TO)}-{V(S_FROM)})/{V(S_N)}"),
            S_PER: ("chart slots per bar", f"={MIDDLE}/{V(S_N)}"),
            S_LOWTAIL: ("low end bar", f'={V(S_BELOW)}+SUMIFS({cnt},{mid},"<"&{V(S_FROM)})'),
            S_HIGHTAIL: ("high end bar", f'={V(S_ABOVE)}+SUMIFS({cnt},{mid},">"&{V(S_TO)})'),
            S_EDGES: ("band edges on Columns", f'=Columns!$I${edge_row}&""' if edge_row else ""),
            S_FMT: ("format", s.fmt),
            S_LSTEP: ("step between labels", f"=({V(S_TO)}-{V(S_FROM)})/{LABELS}"),
            # worked out once, not in each of the 58 line ends (30 Sep 2026: the workbook was slow to open)
            S_TALL: ("tallest bar", f"=MAX(${L(G_SLOT)}${DATA_TOP}:${L(G_SLOT)}${DATA_TOP + SLOTS - 1})")}
    for k, (p, v) in enumerate(zip(PERCENTILES, pcts)):
        scal[S_PCT + k] = (f"P{p}", v)
    for row, (label, v) in scal.items():
        hs.cell(row=row, column=g + G_LABEL, value=label)
        hs.cell(row=row, column=g + G_VALUE, value=v)
    N, F, W, P = V(S_N), V(S_FROM), V(S_WIDTH), V(S_PER)
    counts_rng = f"${L(G_BAR)}${DATA_TOP}:${L(G_BAR)}${DATA_TOP + max(BARS) - 1}"
    for j in range(1, max(BARS) + 1):
        row = DATA_TOP + j - 1
        st = _L(g + G_START, row)
        hs.cell(row=row, column=g + G_START, value=f'=IF({j}<={N},{F}+({j}-1)*{W},"")')
        hs.cell(row=row, column=g + G_BAR_LABEL, value=_short_label(st, V(S_LSTEP), s.fmt))
        hs.cell(row=row, column=g + G_BAR, value=(
            f'=IF({j}>{N},"",SUMIFS({cnt},{mid},">="&{st},{mid},IF({j}={N},"<=","<")&({st}+{W})))'))
    labels_rng = f"${L(G_BAR_LABEL)}${DATA_TOP}:${L(G_BAR_LABEL)}${DATA_TOP + max(BARS) - 1}"
    for k in range(1, SLOTS + 1):
        row = DATA_TOP + k - 1
        if k <= LOW:
            value = f"=IF(AND({k}>={LOW + 1}-{P},{k}<={LOW - 1}),{V(S_LOWTAIL)},0)"
            label = '=""'
        elif k <= LOW + MIDDLE:
            m = k - LOW - 1
            j = f"(INT({m}/{P})+1)"
            value = f"=IF(MOD({m},{P})={P}-1,0,INDEX({counts_rng},{j}))"
            label = f'=IF(AND(MOD({m},{P})=0,MOD({j}-1,{N}/{LABELS})=0),INDEX({labels_rng},{j}),"")'
        else:
            h = k - LOW - MIDDLE - 1
            value = f"=IF({h}<={P}-2,{V(S_HIGHTAIL)},0)"
            label = '=""'
        hs.cell(row=row, column=g + G_SLOT_LABEL, value=label)
        hs.cell(row=row, column=g + G_SLOT, value=value)
    # the band edges typed on Columns, one per row, and each drawn as a two-point line
    src = V(S_EDGES)
    text = f'SUBSTITUTE(SUBSTITUTE(TRIM({src}),",",";")," ","")'
    every = f'LEFT(LOWER(TRIM({src})),5)="every"'
    step = f"VALUE(TRIM(MID(TRIM({src}),6,99)))"
    first = f"(INT({V(S_MIN)}/{step})*{step}+{step})"
    for k in range(1, EDGE_LINES + 1):
        row = DATA_TOP + k - 1
        token = f'TRIM(MID(SUBSTITUTE({text},";",REPT(" ",99)),{(k - 1) * 99 + 1},99))'
        nth = f"({first}+{k - 1}*{step})"
        hs.cell(row=row, column=g + G_EDGE, value=(
            f"=IFERROR(IF({every},IF({nth}<={V(S_MAX)},{nth},NA()),VALUE({token})),NA())"))
        e = _L(g + G_EDGE, row)
        x = (f"=IFERROR(IF(AND({e}>={F},{e}<={V(S_TO)}),{LOW}+0.5+{MIDDLE}*({e}-{F})/({V(S_TO)}-{F}),NA()),NA())")
        # from the floor to the tallest bar: LibreOffice draws the lines on the bars' own axis, Excel on the
        # lines' second one, and both then show a line the height of the chart
        for p, y in ((0, "0"), (1, V(S_TALL))):
            xr = DATA_TOP + 2 * (k - 1) + p
            hs.cell(row=xr, column=g + G_EX, value=x)
            # no edge: both ends not a number, so no program draws a stray point
            hs.cell(row=xr, column=g + G_EY, value=f"=IF(ISNA({_L(g + G_EX, xr)}),NA(),{y})")
    # the percentiles, placed as the edges are: the same mapping, so they follow Bars, From and To, and a
    # percentile outside From..To is not a number, so no line
    for k in range(len(PERCENTILES)):
        pv = V(S_PCT + k)
        x = f"=IFERROR(IF(AND({pv}>={F},{pv}<={V(S_TO)}),{LOW}+0.5+{MIDDLE}*({pv}-{F})/({V(S_TO)}-{F}),NA()),NA())"
        for p, y in ((0, "0"), (1, V(S_TALL))):
            xr = PCT_TOP + 2 * k + p
            hs.cell(row=xr, column=g + G_EX, value=x)
            hs.cell(row=xr, column=g + G_EY, value=f"=IF(ISNA({_L(g + G_EX, xr)}),NA(),{y})")
    at = f"'{DATA}'!{src}"
    edges_now = ws.cell(row=r, column=8, value=(
        f'=IF({at}="","{s.name} · no edges on Columns yet","{s.name} · edges now "&{at})'))
    edges_now.font = Font(name="Calibri", size=9, color=house.SLATE)
    _chart(ws, hs, r, s, g)


def _chart(ws, hs, r: int, s: Shape, g: int) -> None:
    """The column chart of the live feed (INK bars, the two end bars STONE), the red dashed edges on its second
    axes, and the likely code on a red bar of its own to its left."""
    last = DATA_TOP + SLOTS - 1
    ch = BarChart()
    ch.type = "col"
    ch.gapWidth = 0
    ch.add_data(Reference(hs, min_col=g + G_SLOT, min_row=DATA_TOP, max_row=last), titles_from_data=False)
    ch.set_categories(Reference(hs, min_col=g + G_SLOT_LABEL, min_row=DATA_TOP, max_row=last))
    ser = ch.series[0]
    ser.graphicalProperties.solidFill = house.INK
    ser.graphicalProperties.line.noFill = True
    for k in list(range(LOW)) + list(range(LOW + MIDDLE, SLOTS)):
        pt = DataPoint(idx=k)
        pt.graphicalProperties.solidFill = house.STONE
        pt.graphicalProperties.line.noFill = True
        ser.dPt.append(pt)
    ch.legend = None
    # no axis title: Excel drew "Loans" over the axis's own numbers (the firm, at the bank, 29 Sep 2026: "The axis
    # title is out of place"); "The bars" above the charts says they count loans
    ch.y_axis.number_format = "#,##0"
    ch.y_axis.scaling.min = 0
    ch.y_axis.majorGridlines = None
    ch.x_axis.tickLblSkip = 1
    ch.x_axis.tickMarkSkip = MIDDLE
    # short labels (24k), set flat and never wrapped: Excel wrapped 24,000 as "24,0/00" at the bank, 29 Sep 2026
    ch.x_axis.txPr = _small_text(house.INK_TEXT, size=900, no_wrap=True)
    ch.x_axis.delete = ch.y_axis.delete = False
    lines = ScatterChart()
    # the grey percentile lines first, so a red edge on the same spot is drawn over them
    for k, p in enumerate(PERCENTILES):
        xs = Reference(hs, min_col=g + G_EX, min_row=PCT_TOP + 2 * k, max_row=PCT_TOP + 2 * k + 1)
        ys = Reference(hs, min_col=g + G_EY, min_row=PCT_TOP + 2 * k, max_row=PCT_TOP + 2 * k + 1)
        line = Series(ys, xs, title=f"P{p}")
        line.marker.symbol = "none"
        line.smooth = False
        line.graphicalProperties.line.solidFill = house.SLATE
        line.graphicalProperties.line.width = 9525                   # 0.75 pt, thinner than the red edges
        line.dLbls = _name_at_top()
        lines.series.append(line)
    for k in range(EDGE_LINES):
        xs = Reference(hs, min_col=g + G_EX, min_row=DATA_TOP + 2 * k, max_row=DATA_TOP + 2 * k + 1)
        ys = Reference(hs, min_col=g + G_EY, min_row=DATA_TOP + 2 * k, max_row=DATA_TOP + 2 * k + 1)
        line = Series(ys, xs)
        line.marker.symbol = "none"
        line.smooth = False
        line.graphicalProperties.line.solidFill = house.KEY_RED
        line.graphicalProperties.line.dashStyle = "dash"
        line.graphicalProperties.line.width = 19050
        lines.series.append(line)
    # the lines' own axes, crossing each other: x in chart slots, y from 0 to 1 whatever the bars' height
    lines.x_axis.axId, lines.y_axis.axId = 500, 600
    lines.x_axis.crossAx, lines.y_axis.crossAx = 600, 500
    lines.x_axis.scaling.min, lines.x_axis.scaling.max = 0.5, SLOTS + 0.5
    lines.y_axis.scaling.min = 0
    lines.y_axis.crosses = "max"
    lines.x_axis.delete = lines.y_axis.delete = True
    lines.x_axis.majorGridlines = lines.y_axis.majorGridlines = None
    ch += lines
    ch.width, ch.height = 17, 8
    ws.add_chart(ch, f"{CHART_AT}{r + 1}")
    if s.code is None or not s.at_code:
        return
    code = BarChart()
    code.type = "col"
    code.add_data(Reference(hs, min_col=g + G_VALUE, min_row=S_AT_CODE, max_row=S_AT_CODE), titles_from_data=False)
    code.set_categories(Reference(hs, min_col=g + G_VALUE, min_row=S_CODE, max_row=S_CODE))
    code.series[0].graphicalProperties.solidFill = house.KEY_RED
    code.series[0].graphicalProperties.line.noFill = True
    code.legend = None
    code.y_axis.scaling.min = 0
    code.y_axis.number_format = "#,##0"
    code.y_axis.majorGridlines = None
    code.x_axis.number_format = "0"
    code.x_axis.delete = code.y_axis.delete = False
    code.width, code.height = 2.6, 8
    ws.add_chart(code, f"{CODE_AT}{r + 1}")


def _short_label(x: str, step: str, fmt: str) -> str:
    """The formula for a bar's label under the chart, from the bar's start in cell x: 24k for 24,000, 1.2M for
    1,200,000, with the decimals the step between two labels (cell `step`) needs to tell them apart (24.5k when
    they are 500 apart); under 1,000 the column's own format, so a FICO reads 620 and a ratio 0.35. Built from
    ROUND and joined text, not a conditional number format, so a negative (-24k) and the decimals come out the
    same in Excel and LibreOffice."""
    own = f'TEXT({x},"{fmt.replace(chr(34), "")}")'

    def unit(size: str, suffix: str) -> str:
        return f'ROUND({x}/{size},MAX(0,1-INT(LOG10({step}/{size}))))&"{suffix}"'
    return (f'=IF({x}="","",IFERROR(IF(ABS({x})>=1000000,{unit("1000000", "M")},IF(ABS({x})>=1000,'
            f'{unit("1000", "k")},{own})),{own}))')


def _name_at_top() -> DataLabelList:
    """A grey line's name (P10), beside its top point only."""
    top = DataLabel(idx=1)
    for flag in ("showVal", "showCatName", "showLegendKey", "showPercent", "showBubbleSize"):
        setattr(top, flag, False)
    top.showSerName = True
    top.position = "r"
    top.txPr = _small_text(house.SLATE)
    top.spPr = GraphicalProperties(solidFill=house.PAPER)          # readable where it sits over a bar
    d = DataLabelList(dLbl=[top])
    for flag in ("showSerName", "showVal", "showCatName", "showLegendKey", "showPercent", "showBubbleSize"):
        setattr(d, flag, False)
    return d


def _small_text(color: str, size: int = 800, no_wrap: bool = False) -> RichText:
    """Chart text: `size` in hundredths of a point, in `color`, and set flat. `no_wrap`: Excel's "Wrap text in
    shape" off (wrap="none"), which openpyxl reads as no setting at all, so it is put in past its check."""
    props = CharacterProperties(sz=size, solidFill=color)
    body = RichTextProperties(rot=0, vert="horz")
    if no_wrap:
        body.__dict__["wrap"] = "none"
    return RichText(bodyPr=body, p=[Paragraph(pPr=ParagraphProperties(defRPr=props), endParaRPr=props, r=[])])


def _plain(x: float) -> str:
    """A value as the Columns tab writes it: -9,999, -99,000,900, 0.35, never in scientific notation."""
    from .config import plain_value
    return plain_value(x)


def _note(ws, r: int, text: str, wrap_to: int | None = None) -> None:
    """A note under a block; with `wrap_to`, merged from B to that column and wrapped, the row grown to its lines."""
    c = ws.cell(row=r, column=STATS_COL, value=text)
    c.font = Font(name="Calibri", size=10, color=house.SLATE)
    if wrap_to:
        ws.merge_cells(start_row=r, start_column=STATS_COL, end_row=r, end_column=wrap_to)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        width = sum(ws.column_dimensions[get_column_letter(k)].width or 9 for k in range(STATS_COL, wrap_to + 1))
        ws.row_dimensions[r].height = 14 * house.lines_at(text, width / LOOK_PER_CHAR - 2) + 3


def correlation(pairs: list[tuple[float, float]]) -> float | None:
    """Pearson's correlation over every loan with both values, or None when either doesn't vary."""
    if len(pairs) < 3:
        return None
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    sxx, syy = sum((x - mx) ** 2 for x in xs), sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def _scatters(wb, ws, r: int, table, shapes: dict[str, Shape], split: str | None, bands: list[str]) -> int:
    """The split column against each band column, one scatter each, on a page
    of their own. Returns the row under the last one."""
    if DATA in wb.sheetnames:
        wb[DATA].cell(row=3, column=1, value=_drawn(split, bands))
    if not split:
        _bar_row(ws, r, "Scatters")
        _note(ws, r + 1, "None: nothing splits the pockets. Pick a column to split by in the launcher's Choose "
                         "tests; a scatter of it against each band column shows here.", wrap_to=17)
        return r + 2
    if split not in shapes:
        _bar_row(ws, r, f"{split} splits the pockets")
        _note(ws, r + 1, f"{split} isn't a number column, so it has no scatter. Pockets shows it value by value "
                         f"(Pockets: Split by {split}).", wrap_to=17)
        return r + 2
    if r > FIRST:
        _page(ws, r)
    ds = wb.create_sheet(DOTS) if DOTS not in wb.sheetnames else wb[DOTS]
    ds.sheet_state = "hidden"
    ys = _readable(table, split, shapes[split].code, shapes[split].rule)
    for j, band in enumerate(b for b in bands if b in table.columns):
        sb = shapes.get(band) or shape_of(table, band)
        pairs = [(x, y) for x, y in zip(_readable(table, band, sb.code, sb.rule), ys) if x is not None and y is not None]
        shown = pairs
        if len(pairs) > SAMPLE:
            # a sample keeps the workbook light; drawn with a fixed seed, so the same loans show every time
            shown = [pairs[i] for i in sorted(random.Random(SEED).sample(range(len(pairs)), SAMPLE))]
        if j and j % PAGE_BLOCKS == 0:
            _page(ws, r)
        _bar_row(ws, r, f"{split} against {band}")
        _line(ws, r + 1, "Loans with both values", len(pairs))
        _line(ws, r + 2, "Dots shown", len(shown))
        rho = correlation(pairs)
        _line(ws, r + 3, "Moves together (correlation)", round(rho, 2) if rho is not None else "none",
              fmt="+0.00;-0.00;0.00")
        if len(shown) < len(pairs):
            _note(ws, r + 4, f"A random sample of {len(shown):,}: the same loans every time.")
        elif not pairs:
            _note(ws, r + 4, "No loan has both, so there is nothing to plot.")
        if pairs:
            c = 1 + 2 * j
            ds.cell(row=3, column=c, value=band)
            ds.cell(row=3, column=c + 1, value=split)
            for k, (x, y) in enumerate(shown, start=4):
                ds.cell(row=k, column=c, value=x)
                ds.cell(row=k, column=c + 1, value=y)
            ch = ScatterChart()
            ch.title = f"{split} against {band}"
            ch.style = 13
            ser = Series(Reference(ds, min_col=c + 1, min_row=4, max_row=3 + len(shown)),
                         Reference(ds, min_col=c, min_row=4, max_row=3 + len(shown)), title=split)
            ser.marker.symbol = "circle"
            ser.marker.size = 3
            ser.marker.graphicalProperties.solidFill = house.INK
            ser.marker.graphicalProperties.line.solidFill = house.INK
            ser.graphicalProperties.line.noFill = True
            ch.series.append(ser)
            ch.legend = None
            ch.x_axis.title, ch.y_axis.title = band, split
            _axis(ch.x_axis, [x for x, _ in shown], sb.fmt)
            _axis(ch.y_axis, [y for _, y in shown], shapes[split].fmt)
            ch.width, ch.height = 17, 8
            ws.add_chart(ch, f"{CHART_AT}{r + 1}")
        r += BLOCK
    return r


def _readable(table, col: str, code: float | None, rule=None) -> list[float | None]:
    """Each loan's value, None where it is blank, not a number, the code or answered missing."""
    out: list[float | None] = []
    for row in table.rows:
        p = parse_number(row.get(col))
        out.append(p if isinstance(p, float) and p != code and not caught(p, rule) else None)
    return out
