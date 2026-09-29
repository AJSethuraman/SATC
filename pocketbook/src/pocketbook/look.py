"""The Look tab: what each number column holds, before its edges are chosen.

Fix 3.8 (docs/NEXT-GOAL.md), from the audit's item f: band edges were typed
blind. The redesign (docs/redesign-2026-09-26/README.md, section 4), with the
firm's two additions of 26 Sep 2026 (the mean beside the median; live bars and
range, "if truly cheap"):

    each number column gets a block: loans, blank, not a number, a value that
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

    A scatter of the column that splits the pockets against each band column
    (a random 2,000 loans, the same every time), with the correlation beside
    it: a correlation near zero misses a U, and a picture does not
    (docs/statistics.md A9).

The shapes can't change on the same extract, so a Run doesn't redraw the blocks
(found 26 Sep 2026: it did, every Run). It redraws the scatters only when the
split or the band columns differ from those drawn.

Nothing here changes a number PocketBook uses. A value that looks like a code is
counted on its own row and left out of the spread and the bars; whether it
really is a code is answered on Columns (Treat as).
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from decimal import Decimal

from openpyxl.chart import BarChart, Reference, ScatterChart, Series
from openpyxl.chart.marker import DataPoint
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
FIRST = 10                # first block's row, under the method note
BLOCK = 19                # rows per block, the gap under it included
PAGE_BLOCKS = 2           # blocks per printed page
GROUP = 13                # _look columns per number column
DATA_TOP = 4              # _look's first data row

# where a block's lines and inputs sit, from its top row
R_LOANS, R_BLANK, R_TEXT, R_CODE, R_MIN, R_MEDIAN, R_MEAN, R_MAX = range(1, 9)
R_BARS, R_FROM, R_TO, R_TREAT = 10, 11, 12, 13
STATS_COL, VALUE_COL, SHARE_COL = 2, 3, 4          # B, C, D
CODE_AT, CHART_AT = "F", "H"

# _look, within a column's group (offsets from its first column)
G_LO, G_MID, G_COUNT, G_LABEL, G_VALUE, G_START, G_BAR, G_SLOT_LABEL, G_SLOT, G_EX, G_EY, G_EDGE = range(12)
# _look scalar rows (G_LABEL / G_VALUE)
S_NAME, S_LO, S_HI, S_BELOW, S_ABOVE, S_CODE, S_AT_CODE, S_MIN, S_MAX, S_N, S_FROM, S_TO, S_WIDTH, S_PER, \
    S_LOWTAIL, S_HIGHTAIL, S_EDGES, S_FMT = range(DATA_TOP, DATA_TOP + 18)

METHOD = [
    ("The bars", "How many loans fall in each step between From and To. Pick 10, 20 or 50 bars and change the "
                 "range; the chart follows. The grey bar at each end holds the loans outside the range."),
    ("The red bar", "A value that looks like a code, such as a score of -9999, gets a red bar of its own left of "
                    "the chart, so it doesn't flatten the rest. Columns asks whether it means missing."),
    ("Red dashed lines", "The band edges typed on Columns. They follow that tab as you type, so you can try edges "
                         "here before the next Run. Blank edges are cut at the Run, so no lines show."),
    ("How it counts", "Set up counts each column once, in 200 equal slices around its 1st to 99th percentile. A "
                      "range you type is counted to the nearest slice."),
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


def shape_of(table, col: str, known=None) -> Shape:
    """`known`: the column's facts from Set up, whose numbers are used rather
    than read again."""
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
    code = next((q["value"] for q in profile.odd_values(col, nums) if q["pattern"] == "repeated_value"), None)
    values = sorted(x for x in nums if x != code)
    s = Shape(col, len(table.rows), blank, text, code, len(nums) - len(values), values)
    if values:
        s.fmt = _format(values)
    return s


def _format(values: list[float]) -> str:
    """Scores and dollars read as whole numbers; a ratio keeps its decimals."""
    if all(float(x).is_integer() for x in values):
        return "#,##0"
    big = max(abs(values[0]), abs(values[-1]), abs(statistics.median(values)))
    return "#,##0" if big >= 100 else "#,##0.0" if big >= 10 else "0.00" if big >= 1 else "0.000"


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
               edge_rows: dict | None = None, treat_rows: dict | None = None) -> None:
    """Write (or write again) the Look tab and its hidden sheets. `columns` are the number columns to show,
    `split` the column that splits the pockets and `bands` the band columns it is plotted against. `known` is Set
    up's facts by column, so no column's numbers are read twice; `edge_rows` each column's row on Columns (its
    Band edges cell feeds the red lines), `treat_rows` each column's first odd value there."""
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
    for col, w in zip("ABCDEFGH", (2, 26, 12, 9, 2, 13, 2, 10)):
        ws.column_dimensions[col].width = w
    house.title_band(ws, "Look", "Each number column before you choose its band edges.", 2, 17)
    top = house.method_note(ws, 3, 2, 17, METHOD)
    assert top == FIRST, top
    known = known or {}
    shapes = {c: shape_of(table, c, known.get(c)) for c in columns}
    dv = DataValidation(type="list", formula1=f'"{",".join(str(b) for b in BARS)}"', allow_blank=False,
                        showErrorMessage=True)
    dv.error = "Pick 10, 20 or 50 bars."
    ws.add_data_validation(dv)
    r = FIRST
    for i, c in enumerate(columns):
        if i and i % PAGE_BLOCKS == 0:
            _page(ws, r)
        _block(ws, hs, r, shapes[c], 2 + GROUP * i, dv, (edge_rows or {}).get(c), (treat_rows or {}).get(c))
        r += BLOCK
    hs.cell(row=2, column=1, value=r)                             # where the scatters start, for refresh()
    end = _scatters(wb, ws, r, table, shapes, split, [b for b in bands if b != split])
    ws.print_area = f"A1:Q{end}"                                   # to the foot of the last chart
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.freeze_panes = "A2"


def refresh(wb, table, split: str | None = None, bands=()) -> bool:
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
                                      fmt)
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
    ax.number_format = fmt
    ax.delete = False


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
    if s.code is not None and treat is not None and treat[1].startswith("repeated_value|"):
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
                   (G_EX, "edge x"), (G_EY, "edge y"), (G_EDGE, "edge")):
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
            S_FMT: ("format", s.fmt)}
    for row, (label, v) in scal.items():
        hs.cell(row=row, column=g + G_LABEL, value=label)
        hs.cell(row=row, column=g + G_VALUE, value=v)
    N, F, W, P = V(S_N), V(S_FROM), V(S_WIDTH), V(S_PER)
    starts = f"${L(G_START)}${DATA_TOP}:${L(G_START)}${DATA_TOP + max(BARS) - 1}"
    counts_rng = f"${L(G_BAR)}${DATA_TOP}:${L(G_BAR)}${DATA_TOP + max(BARS) - 1}"
    for j in range(1, max(BARS) + 1):
        row = DATA_TOP + j - 1
        st = _L(g + G_START, row)
        hs.cell(row=row, column=g + G_START, value=f'=IF({j}<={N},{F}+({j}-1)*{W},"")')
        hs.cell(row=row, column=g + G_BAR, value=(
            f'=IF({j}>{N},"",SUMIFS({cnt},{mid},">="&{st},{mid},IF({j}={N},"<=","<")&({st}+{W})))'))
    fmt = s.fmt.replace('"', "")
    for k in range(1, SLOTS + 1):
        row = DATA_TOP + k - 1
        if k <= LOW:
            value = f"=IF(AND({k}>={LOW + 1}-{P},{k}<={LOW - 1}),{V(S_LOWTAIL)},0)"
            label = '=""'
        elif k <= LOW + MIDDLE:
            m = k - LOW - 1
            j = f"(INT({m}/{P})+1)"
            value = f"=IF(MOD({m},{P})={P}-1,0,INDEX({counts_rng},{j}))"
            label = (f'=IF(AND(MOD({m},{P})=0,MOD({j}-1,{N}/{LABELS})=0),TEXT(INDEX({starts},{j}),"{fmt}"),"")')
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
        slots = f"${L(G_SLOT)}${DATA_TOP}:${L(G_SLOT)}${DATA_TOP + SLOTS - 1}"
        for p, y in ((0, "0"), (1, f"MAX({slots})")):
            xr = DATA_TOP + 2 * (k - 1) + p
            hs.cell(row=xr, column=g + G_EX, value=x)
            # no edge: both ends not a number, so no program draws a stray point
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
    ch.x_axis.delete = ch.y_axis.delete = False
    lines = ScatterChart()
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


def _plain(x: float) -> str:
    """A value as the Columns tab writes it: -9999, 0.35."""
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def _note(ws, r: int, text: str) -> None:
    c = ws.cell(row=r, column=STATS_COL, value=text)
    c.font = Font(name="Calibri", size=10, color=house.SLATE)


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
                         "tests; a scatter of it against each band column shows here.")
        return r + 2
    if split not in shapes:
        _bar_row(ws, r, f"{split} splits the pockets")
        _note(ws, r + 1, f"{split} isn't a number column, so it has no scatter. Pockets shows it value by value "
                         f"(Pockets: Split by {split}).")
        return r + 2
    if r > FIRST:
        _page(ws, r)
    ds = wb.create_sheet(DOTS) if DOTS not in wb.sheetnames else wb[DOTS]
    ds.sheet_state = "hidden"
    ys = _readable(table, split, shapes[split].code)
    for j, band in enumerate(b for b in bands if b in table.columns):
        sb = shapes.get(band) or shape_of(table, band)
        pairs = [(x, y) for x, y in zip(_readable(table, band, sb.code), ys) if x is not None and y is not None]
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


def _readable(table, col: str, code: float | None) -> list[float | None]:
    """Each loan's value, None where it is blank, not a number or the code."""
    out: list[float | None] = []
    for row in table.rows:
        p = parse_number(row.get(col))
        out.append(p if isinstance(p, float) and p != code else None)
    return out
