"""The result tabs, as the firm's redesign draws them (docs/redesign-2026-09-26/README.md, sections 5 to 8).

    Pockets           every pocket losing more than its share, for every measure, two-way or split (it merges
                      Where it bleeds and Three-way)
    Paid, cost, kept  what each pocket paid us, cost us and what we kept, one grid at a time, and the two read
                      together (it replaces Losses vs revenue)
    Grids             one grid and one measure at a time, in four blocks: the rate, against the book, against
                      the rest of its band, and the loans; then how common each group is (it absorbs Prevalence)
    Split             each pocket halved at its own median: the summary, and the two grids side by side

Every tab has the redesign's anatomy: the title band, one "How this tab works" note grouped so it folds away
(tenet T1: how a figure was worked out is said there once, never beside a row), the lines in use where a line
moves something, the dropdowns, and then result rows only.

Slicers are dropdown cells: openpyxl can't write slicers, and drops them when it saves a workbook again, which
every Run does. Each tab picks what it shows with INDEX and MATCH over hidden sheets the Run writes, and never
SORT, FILTER or LET, so Excel 2016 and LibreOffice 24.2 both calculate it:

    _choices   each dropdown's options, a column each
    _list      Pockets' rows in the last Run's order: every pocket losing more than its share against either
               comparison, for every measure and both kinds of pocket, with its live Worse? and Material? (read
               from _pockets), whether the dropdowns show it now, and a running count of those shown. The k-th
               row shown is the first whose running count reaches k
    _views     every other number these tabs show, one keyed row each ("G|FICO x CHANNEL|gco_rate|book|2")

Live (OC-40): Worse?, Material?, the dollars, the gaps, Together and every colour that depends on them are
formulas over _pockets, so they follow Control. The order of the rows, the smallest gap a pocket could have
caught and the heat maps are as of the last Run, and each tab says so once.
"""

from __future__ import annotations

import math

from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.chart.data_source import StrRef
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import SeriesLabel
from openpyxl.formatting.rule import Rule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.styles.numbers import NumberFormat
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

import zlib

from . import engine, house, live, prevalence, stats
from .config import PROFIT

POCKETS, PCK, GRIDS, SPLIT = "Pockets", "Paid, cost, kept", "Grids", "Split"
TABS = (POCKETS, PCK, GRIDS, SPLIT)
#: the tabs these replace; a workbook written before phase 3 has them, and a Run takes them off
OLD_TABS = ("Where it bleeds", "Three-way", "Losses vs revenue", "Prevalence")
CHOICES, LIST, VIEWS = "_choices", "_list", "_views"
HIDDEN = (CHOICES, LIST, VIEWS)

#: the measures in the analyst's words (the redesign's plain-words table), in the Measure dropdown's order
PLAIN = {"outcome_loans": "Bad loans", "outcome_booked": "Bad dollars", "gco_rate": "Charge-offs",
         "ranr_rate": "Kept after losses", "contribution_rate": "Earned before losses"}
SHOW = ("All", "Worse and material", "Worse or not sure")
TWO_WAY = "Two-way"
#: Together, the two sides read at once (Paid, cost, kept): charge-offs, then what we kept
TOGETHER = {("more", "more"): "Priced for it", ("more", "less"): "Net drain", ("less", "more"): "Strong",
            ("less", "less"): "Safe but idle", ("same", "less"): "Earns less, not from losses",
            # the mirror of the one before: charge-offs worse and real, what we kept no different (the firm, 27 Sep)
            ("more", "same"): "Losing more, profit holding"}
GOOD_TOGETHER, BAD_TOGETHER = ("Priced for it", "Strong"), ("Net drain",)

INK, ONYX, CANVAS, MIST, STONE, SLATE = house.INK, house.ONYX, house.CANVAS, house.MIST, house.STONE, house.SLATE
ALERT, CRIMSON, POSITIVE, POSITIVE_BG = house.ALERT_FG, house.CRIMSON, house.POSITIVE, house.POSITIVE_BG
#: the heat scale (the redesign's tokens), in steps: 0.5x and under HEAT_GOOD, 1x HEAT_MID, 2x HEAT_BAD and deeper
#: from 2x; the steps between are halfway colours, so the scale reads the same whatever the Measure dropdown says
HEAT_STEPS = ((1.0, house.HEAT_BAD2), (0.585, house.HEAT_BAD), (0.263, "EACBC9"), (-0.585, house.HEAT_GOOD),
              (-0.263, "D7E2D4"))
LOANS_STEPS = ((0.2, STONE), (0.1, "CFCAC2"), (0.05, MIST), (0.02, house.ROW_RULE))

P_FMT = '[<0.0001]"under 0.01%";[<0.01]0.00%;0.0%'
PTS_FMT = '+0.00" pts";-0.00" pts";0.00" pts"'
X_FMT = '0.00"×"'
AREA, KEYS = f"'{VIEWS}'!$B:$ZZ", f"'{VIEWS}'!$A:$A"


def col(n: int) -> str:
    return get_column_letter(n)


def plain(m) -> str:
    return PLAIN.get(m.name, m.title)


def rates(res) -> list:
    """The rates, in the Measure dropdown's order."""
    order = list(PLAIN)
    return sorted((m for m in res.measures if m.is_rate),
                  key=lambda m: order.index(m.name) if m.name in order else len(order))


def split_label(res) -> str | None:
    return f"Split by {res.config.split[0]}" if res.config.split else None


def pk(c: int) -> str:
    """A whole column of _pockets, for INDEX by the pocket's row."""
    return f"'{live.POCKETS}'!${col(c)}:${col(c)}"


def at(c: int, row: str) -> str:
    """One pocket's cell on _pockets, blank when there is no row or nothing in it."""
    x = f"INDEX({pk(c)},{row})"
    return f'IF({row}="","",IF({x}="","",{x}))'


# --------------------------------------------------------------------------
# The hidden sheets


class Choices:
    """Each dropdown's options, a column each, on the hidden _choices sheet."""

    def __init__(self, wb):
        if CHOICES in wb.sheetnames:
            del wb[CHOICES]
        self.ws = wb.create_sheet(CHOICES)
        self.ws.sheet_state = "hidden"
        self.n = 0

    def add(self, name: str, options: list, *beside: list) -> tuple[str, list[str]]:
        """A column of options, and columns beside it (a key per option, say). Returns the options' range and
        each beside column's range."""
        first = self.n + 1
        for k, values in enumerate((options,) + beside):
            c = first + k
            self.ws.cell(row=1, column=c, value=name if k == 0 else f"{name} ({k})")
            for i, v in enumerate(values, start=2):
                self.ws.cell(row=i, column=c, value=v)
        self.n = first + len(beside)
        last = len(options) + 1
        rng = lambda c: f"'{CHOICES}'!${col(c)}$2:${col(c)}${last}"         # noqa: E731
        return rng(first), [rng(first + k) for k in range(1, len(beside) + 1)]


class Views:
    """Keyed rows on the hidden _views sheet: the key in column A, the numbers from column B."""

    def __init__(self, wb):
        if VIEWS in wb.sheetnames:
            del wb[VIEWS]
        self.ws = wb.create_sheet(VIEWS)
        self.ws.sheet_state = "hidden"
        self.r = 0

    def put(self, key: str, values: list) -> int:
        self.r += 1
        self.ws.cell(row=self.r, column=1, value=key)
        for j, v in enumerate(values, start=2):
            if v is not None and v != "":
                self.ws.cell(row=self.r, column=j, value=v)
        return self.r


def xk(*parts) -> str:
    """A key as an Excel expression: a str part is words, a 1-tuple an expression ("C|"&$C$20&"|1")."""
    return "&".join(p[0] if isinstance(p, tuple) else live.q(p) for p in parts)


def match(key: str) -> str:
    """The _views row whose key is the Excel expression `key`, or blank."""
    return f'IFERROR(MATCH({key},{KEYS},0),"")'


def pick(row: str, j) -> str:
    """The j-th number on a _views row, blank when there is no row or nothing there."""
    x = f"INDEX({AREA},{row},{j})"
    return f'IF({row}="","",IF({x}="","",{x}))'


# --------------------------------------------------------------------------
# The parts every result tab shares


def _cell(ws, r: int, c: int, v=None, *, bold=False, size=10, color=house.INK_TEXT, h="center", fmt=None,
          name="Calibri", indent=0, wrap=False):
    x = ws.cell(row=r, column=c, value=v)
    x.font = Font(name=name, bold=bold, size=size, color=color)
    x.alignment = Alignment(horizontal=h, vertical="center", indent=indent, wrap_text=wrap or None)
    if fmt:
        x.number_format = fmt
    return x


def dropdown(ws, r: int, c: int, label: str, options_rng: str, default) -> str:
    """A dropdown cell (the redesign's slicer), its label above it; styled as an answer that changes the tab
    now. Returns the cell's absolute address."""
    _cell(ws, r - 1, c, label.upper(), bold=True, size=9, color=SLATE, h="left", name="Arial")
    x = ws.cell(row=r, column=c, value=default)
    house.changes_now(x)
    x.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    dv = DataValidation(type="list", formula1=f"={options_rng}", allow_blank=False, showErrorMessage=True,
                        errorTitle=label, error="Pick one from the list.")
    ws.add_data_validation(dv)
    dv.add(x)
    ws.row_dimensions[r].height = 20
    return f"${col(c)}${r}"


def cf(ws, rng: str, rules: list[tuple], row_line: str | None = None) -> None:
    """Conditional formats on one range, in order. LibreOffice applies one format to a cell, the first rule that
    holds, where Excel applies every rule that holds; so each rule carries all a cell needs (fill, font, number
    format) and each cell sits in one range only, and the two programs agree. `rules` are (formula, fill, font,
    number format), any of the last three None. `row_line`, a formula true on a row with something in it, adds
    the row's divider to every rule and a last rule of its own, so a blank row below the list draws nothing."""
    side = Side(style="thin", color=house.ROW_RULE)
    todo = list(rules) + ([(row_line, None, None, None)] if row_line else [])
    for formula, fill, font, fmt in todo:
        dxf = DifferentialStyle(
            font=font, fill=PatternFill("solid", fgColor=fill, bgColor=fill) if fill else None,
            numFmt=NumberFormat(numFmtId=300 + zlib.crc32(fmt.encode()) % 200, formatCode=fmt) if fmt else None,
            border=Border(bottom=side) if row_line else None)
        f = formula if not row_line or formula == row_line else f"AND({row_line},{formula})"
        ws.conditional_formatting.add(rng, Rule(type="expression", formula=[f], dxf=dxf))


def heat_t(cell: str, kind: str, bound: str) -> str:
    """A gap on the heat scale's one scale, as a formula: log2 of a multiple (2x is 1, 0.5x is -1), or a gap in
    points over the largest in the grid, turned so that worse is always above zero."""
    return (f'IFERROR(IF({kind}="pts",-{cell}/{bound},IF({kind}="x",LOG({cell},2),IF({kind}="xr",-LOG({cell},2),0))),0)')


#: the heat scale's steps in words, for the one cell read out under the blocks (HEAT_STEPS, the same order)
SHADE = {house.HEAT_BAD2: "deep red", house.HEAT_BAD: "red", "EACBC9": "light red", house.HEAT_GOOD: "green",
         "D7E2D4": "light green"}


def shade_of(cell: str, kind: str, bound: str) -> str:
    """The colour the heat scale gives `cell`, in words: the same steps, in the same order, as heat_rules."""
    t = heat_t(cell, kind, bound)
    out = '"pale"'
    for lim, colour in reversed(HEAT_STEPS):
        out = f'IF({t}{">=" if lim > 0 else "<="}{lim},"{SHADE[colour]}",{out})'
    return f'IF(ISNUMBER({cell}),{out},"blank")'


def heat_rules(cell: str, kind: str, bound: str, extra: str | None = None, fmt: str | None = None) -> list[tuple]:
    """The heat scale over a block whose measure changes with a dropdown, in the spec's tokens: each step is a rule
    over t, the gap on one scale (log2 of a multiple, so 2x is 1 and 0.5x is -1; a gap in points over the largest
    in the grid), reading `kind` and `bound` from the tab's hidden cells. With `extra` (a formula) each step comes
    twice, first with `fmt` for the cells `extra` holds on (a gap in points: its number format)."""
    t = heat_t(cell, kind, bound)
    steps = [(f"AND(ISNUMBER({cell}),{t}{'>=' if lim > 0 else '<='}{lim})", colour) for lim, colour in HEAT_STEPS]
    steps.append((f"ISNUMBER({cell})", house.HEAT_MID))
    out = []
    for f, colour in steps:
        if extra:
            out.append((f"AND({extra},{f})", colour, None, fmt))
        out.append((f, colour, None, None))
    return out


def lines_in_use(ws, r: int, label_col: int, spans: list[tuple[int, int]], material: str, note_col: int,
                 note_last: int, said: str) -> int:
    """The lines in use now (the redesign's Global rule 1.3): tiles whose values are formulas over Control, and
    beside them what stays as of the last Run and any change waiting for a Run. Returns the row after them."""
    _cell(ws, r, label_col, "LINES IN USE NOW", bold=True, size=8, color=SLATE, h="left", name="Arial")
    _cell(ws, r + 1, label_col, "live from Control", size=8, color=SLATE, h="left")
    tiles = [("Worse at", "=worse_at", X_FMT), ("Better at", "=better_at", X_FMT), ("How sure", "=confidence", "0%"),
             ("Material at", material, None),
             ("Judged against", '=IF(judged_band,"Rest of its band","Rest of the book")', None)]
    for (label, f, fmt), (a, b) in zip(tiles, spans):
        house.tile(ws, r, a, b, label, f, fmt)
    ws.merge_cells(start_row=r, start_column=note_col, end_row=r, end_column=note_last)
    _cell(ws, r, note_col, said, size=9, color=SLATE, h="left", indent=1)
    ws.merge_cells(start_row=r + 1, start_column=note_col, end_row=r + 1, end_column=note_last)
    n = f'COUNTIF(Status,"{house.WAITING}")'
    _cell(ws, r + 1, note_col, f'=IFERROR(IF({n}=0,"","↻ "&{n}&IF({n}=1," Control change waits for a Run.",'
                               f'" Control changes wait for a Run.")),"")', bold=True, size=9, color=CRIMSON, h="left",
          indent=1)
    return r + 3


def material_at(res, key: str | None = None, loans: str | None = None) -> str:
    """The Material at tile: the materiality line in use, in its measure's unit. `key` and `loans` are the
    cells holding a dropdown's measure (Pockets); otherwise charge-offs' line in dollars, or the outcome's in
    bad loans for a run without charge-offs."""
    from . import book as bk
    if key is None:
        has_gco = any(m.name == "gco_rate" for m in res.measures)
        m = next((m for m in rates(res) if m.name == "gco_rate"), (rates(res) or [None])[0])
        if m is None:
            return ""
        key, loans = live.q(m.name), ("TRUE" if bk._unit(m) == "loans" and not has_gco else "FALSE")
    x = f"INDEX(line_values,MATCH({key},line_keys,0))"
    return (f'=IFERROR(IF(materiality_kind="none","No floor",IF({x}="","No line",IF({loans},TEXT({x},"#,##0.0")'
            f'&" bad loans","$"&TEXT({x},"#,##0")))),"")')


def _widths(ws, widths: dict[int, float]) -> None:
    for c, w in widths.items():
        ws.column_dimensions[col(c)].width = w


def _hide(ws, first: int, last: int) -> None:
    for c in range(first, last + 1):
        ws.column_dimensions[col(c)].hidden = True


def _rule_row(ws, r: int, first: int, last: int) -> None:
    for c in range(first, last + 1):
        ws.cell(row=r, column=c).border = Border(bottom=Side(style="thin", color=house.ROW_RULE))
    ws.row_dimensions[r].height = 16


def _fit(ws) -> None:
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


#: Each tab's method-note line on Borderline (the firm, 29 Sep 2026, by pop-up, choosing the word), as live.text
#: parts: said at the end of the note's p-value item (Together's, on Paid, cost, kept), so no row of the tab moves.
#: Only a run with a dollar rate says it: nothing else is shuffled, so nothing else can be borderline
BORDER_WORDS = (" Borderline: the test's p-value is within the shuffle's own margin of the ",
                ('TEXT(significance_bar,"0%")',), " bar, so another run could read it the other way.")


def _allowance(b) -> str:
    return {"bh": "Benjamini-Hochberg", "bonferroni": "Bonferroni", "none": "none"}.get(b.many_tests, "none")


# --------------------------------------------------------------------------
# Pockets


# the table's columns
(K_NUM, K_BAND, K_SEG, K_HALF, K_LOANS, K_THIS, K_REST, K_GAP, K_EX, K_WORSE, K_P, K_MAT, K_CAUGHT, K_HOLDS) = \
    range(2, 16)
K_IDX, K_ROW = 18, 19                  # hidden: the row on _list, and the pocket's row on _pockets
K_SEL = 21                             # hidden: the selected measure's key, and whether it reads in points or loans
# _list's columns
(L_KIND, L_MEAS, L_ROW, L_BAND, L_SEG, L_HALF, L_LOANS, L_CAUGHT, L_HOLDS, L_RANK, L_WORSE, L_MAT, L_SHOWN, L_CUM,
 L_KKEY, L_MKEY) = range(1, 17)


def _segment(names, g, d) -> str:
    """A segment that is only a number reads with its column's name: "ASSET_CLASS 4", as the spec does."""
    return f"{names[g.dimension].split(' / ')[0]} {d}" if str(d).replace(".", "").isdigit() else str(d)


def _halves(res, dl: str) -> tuple[str, str]:
    """A three-way pocket's segment and its half: "Broker / REV_DEBT high half" is ("Broker", "high")."""
    seg, _, half = str(dl).rpartition(" / ")
    sf = res.config.split[0]
    half = half.replace(f"{sf} ", "", 1).removesuffix(" half") if half.startswith(f"{sf} ") else half
    return seg, half


def _caught(s, m) -> float | None:
    """The smallest gap this pocket could have caught (as of the last Run), as the tab prints it."""
    sg = s.smallest_gap
    if not sg:
        return None
    if m.in_points:
        return -sg * 100
    return sg if m.higher_is == "worse" else 1 / sg


def candidates(res, kind: str, m) -> list[tuple]:
    """The pockets Pockets lists for one kind and measure, in the last Run's order: every pocket losing more than
    its share against either comparison (a change of "judged against" on Control then finds every pocket it
    could flag). Worse pockets first, largest dollars first; then the rest by their dollars; then those losing
    more only against the comparison that doesn't decide now. On the split view, pockets from grids that don't
    hold the split's partner fixed come last (the fourth walk, defect 1)."""
    from . import book as bk
    grids = res.grids if kind == "grids" else res.three_way
    out = []
    for g in grids:
        held = 0.0 if kind == "grids" else bk._three_way_note(res, g)[1]
        for (bl, dl), c in g.inner():
            s = c.rates[m.name]
            d = s.dollars
            other = s.excess_band if not s.by_band else s.excess_rest
            if not ((d is not None and d > 0) or (other is not None and other > 0)):
                continue
            losing = d is not None and d > 0
            key = (held, 0 if s.flag == engine.WORSE and losing else 1, 0 if losing else 1,
                   -(d if losing else (other or 0.0)))
            out.append((key, g, bl, dl, s))
    out.sort(key=lambda t: t[0])
    return [t[1:] for t in out]


def _write_list(wb, res, lv, kinds, sel: dict) -> tuple[int, dict]:
    """_list: Pockets' rows in the last Run's order, each with its live verdicts and whether it is shown now.
    Returns the last row and the most rows any one view can show."""
    from . import book as bk
    if LIST in wb.sheetnames:
        del wb[LIST]
    ws = wb.create_sheet(LIST)
    ws.sheet_state = "hidden"
    heads = {L_KIND: "Pockets", L_MEAS: "Measure", L_ROW: "_pockets row", L_BAND: "Band", L_SEG: "Segment",
             L_HALF: "Half", L_LOANS: "Loans", L_CAUGHT: "Could have caught (last Run)", L_HOLDS: "Holds fixed?",
             L_RANK: "Order (last Run)", L_WORSE: "Worse? (live)", L_MAT: "Material? (live)",
             L_SHOWN: "Shown now (1: yes)", L_CUM: "Shown so far", L_KKEY: "Kind (key)", L_MKEY: "Measure (key)"}
    for c, h in heads.items():
        ws.cell(row=1, column=c, value=h).font = Font(bold=True)
    names = bk._names(res)
    pt = bk._partner(res) if res.config.split else None
    r = 2
    most: dict = {}
    for kind, label in kinds:
        for m in rates(res):
            n = 0
            for g, bl, dl, s in candidates(res, kind, m):
                prow = lv.rows.get((kind, id(g), bl, dl, m.name))
                if prow is None:
                    continue
                n += 1
                seg, half = (dl, None) if kind == "grids" else _halves(res, dl)
                seg = _segment(names, g, seg)
                holds = None
                if kind != "grids" and pt is not None:
                    holds = "Yes" if bk._holds_partner(res, g) else f"No: may be mostly {pt[0]}"
                P = lambda c: f"'{live.POCKETS}'!${col(c)}${prow}"         # noqa: E731
                vals = {L_KIND: label, L_MEAS: plain(m), L_ROW: prow, L_BAND: f"{names[g.band]} {bl}", L_SEG: seg,
                        L_HALF: half, L_LOANS: s.units, L_CAUGHT: _caught(s, m), L_HOLDS: holds, L_RANK: n,
                        L_WORSE: f"={P(live.P_WORSE)}", L_MAT: f"={P(live.P_MAT)}", L_KKEY: kind, L_MKEY: m.name}
                for c, v in vals.items():
                    if v is not None:
                        ws.cell(row=r, column=c, value=v)
                A = lambda c: f"${col(c)}{r}"                                # noqa: E731
                show = (f'OR({sel["show"]}="{SHOW[0]}",AND({sel["show"]}="{SHOW[1]}",{A(L_WORSE)}="{live.YES}",'
                        f'{A(L_MAT)}="{live.YES}"),AND({sel["show"]}="{SHOW[2]}",OR({A(L_WORSE)}="{live.YES}",'
                        f'{A(L_WORSE)}="{live.NOT_SURE}")))')
                ws.cell(row=r, column=L_SHOWN, value=f'=IF(AND({A(L_KIND)}={sel["kind"]},{A(L_MEAS)}='
                                                     f'{sel["measure"]},{show}),1,0)')
                ws.cell(row=r, column=L_CUM, value=f"={A(L_SHOWN)}" if r == 2 else
                        f"=${col(L_CUM)}{r - 1}+{A(L_SHOWN)}")
                r += 1
            most[(kind, m.name)] = n
    return r - 1, most


POCKETS_NOTE_ORDER = ("Sorted as of the last Run: worse pockets first, largest excess first, then the rest by "
                      "their excess.")


def _pockets_note(res) -> list[tuple[str, str]]:
    from . import book as bk
    b = res.config.benchmark
    sf = res.config.split[0] if res.config.split else None
    pt = bk._partner(res) if sf else None
    dollar_rates = bk._has_dollar_rates(res)
    profit = bk._has_profit(res)
    items = [
        ("A pocket", "One band of one column crossed with one segment of another, in every grid chosen in the "
                     "launcher. Loans: how many are in it."
                     + (f" Split by {sf}: each pocket halved at its own median {sf}, each half tested like any "
                        f"other pocket." if sf and res.config.split[1] == "own_median" else
                        f" Split by {sf}: each pocket split by each value of {sf}, each part tested like any other "
                        f"pocket." if sf else "")),
        ("Rest of band", live.text(
            "Every other loan in the same band. Judged against on Control picks it or the rest of the book (every "
            "other loan in the book); now ", ('IF(judged_band,"the rest of its band","the rest of the book")',),
            ". It decides the gap, the excess and both verdicts. A pocket alone in its band has nothing beside it "
            "to compare with, so it is judged against the rest of the book, whatever Control says.")),
        ("Excess", "What the pocket lost above what it would have lost at the rest's rate: bad loans for Bad loans, "
                   "dollars for the dollar measures."
                   + (" For Kept after losses and Earned before losses, the dollars it fell short of the rest, and "
                      "the gap is in points of booked dollars." if profit else "")),
        ("Worse?", live.text(
            "Yes: at least ", ('TEXT(worse_at,"0.00")',), "x the rest",
            " (for profit, short of it" + (" by the profit line on Control)" if profit else ")")
            if profit else "", ", with a p-value under ", ('TEXT(significance_bar,"0%")',),
            ". Not sure: the gap is there, but the p-value isn't under it. Too few losses: fewer than ",
            f"{b.min_events:,} (a setting for the next Run), so not tested. No: anything else.")),
        ("p-value", live.text(
            "The chance of a gap at least this big if the pocket were no different from the rest, after the "
            f"allowance for testing many pockets at once ({_allowance(b)}, across one grid and one measure). Bad "
            f"loans: the z test, or the exact test for a pocket under {b.min_units:,} loans."
            + (f" Dollar measures: the loans are shuffled {b.shuffles:,} times, within the band for the rest of "
               f"its band, and it is how often a gap as big turned up." if dollar_rates else ""),
            " Under ", ('TEXT(significance_bar,"0%")',), " counts.", *(BORDER_WORDS if dollar_rates else ()))),
        ("Material?", "Yes when the excess reaches the materiality line on Control (the Material at tile, in the "
                      "measure's own unit). It is judged apart from Worse?: a pocket can be one without the other."),
        ("Could have caught", f"The smallest gap a pocket this size would catch {b.power:.0%} of the time at the "
                              f"last Run's confidence. As of the last Run."),
        ("Order", POCKETS_NOTE_ORDER + " Last come pockets losing more only against the other comparison, so "
                                       "that changing Judged against on Control finds them here. A change on "
                                       "Control updates Worse?, Material?, the dollars and the colours at once, "
                                       "not the order. The caption counts what the dropdowns pick."),
    ]
    if sf and pt:
        items.append((f"Holds {pt[0]} fixed?", f"Split only. {sf} moves with {pt[0]} (correlation {pt[1]:+.2f}), so "
                                              f"a split pocket in a grid that doesn't hold {pt[0]} fixed may be "
                                              f"showing {pt[0]}, not {sf}. Those rows come last, in grey, with no "
                                              f"verdict colour."))
    return items


#: the label columns on Pockets, Paid cost kept and Start here (P1): fitted to the Run's labels, between these
LABELS_FLOOR, LABELS_CAP, HALF_FLOOR = 12, 32, 10


def label_widths(res) -> dict[str, float]:
    """The widths of the label columns Pockets, Paid cost kept and Start here show (P1), each the longest label the
    Run can put in it + 3 (left, indent 1), between LABELS_FLOOR and LABELS_CAP: `band`, a band with its column's
    name ("FICO 496 - 653", Pockets and Start here); `band_only`, without it (Paid cost kept); `seg`, a segment as
    Pockets and Start here show it ("ASSET_CLASS 4"); `seg_raw`, as Paid cost kept does; `half`, the split's part
    and its heading."""
    from . import book as bk
    names = bk._names(res)
    band, band_only, seg, seg_raw, half = [], [], [], [], []
    for g in res.grids:
        band += [f"{names[g.band]} {bl}" for bl in g.band_labels]
        band_only += [str(bl) for bl in g.band_labels]
        seg += [_segment(names, g, d) for d in g.dim_labels]
        seg_raw += [str(d) for d in g.dim_labels]
    for g in res.three_way:
        for d in g.dim_labels:
            s_, h_ = _halves(res, d)
            seg.append(_segment(names, g, s_))
            half.append(h_)
    if res.config.split:
        half.append(f"{res.config.split[0]} half" if res.config.split[1] == "own_median" else res.config.split[0])
    f = lambda xs, floor=LABELS_FLOOR: house.fit(xs, floor=floor, cap=LABELS_CAP, pad=3)      # noqa: E731
    return {"band": f(band), "band_only": f(band_only), "seg": f(seg), "seg_raw": f(seg_raw),
            "half": f(half, HALF_FLOOR)}


def write_pockets(wb, res, choices: Choices, stamp: str) -> None:
    """The Pockets tab (section 5): three dropdowns over one list."""
    from . import book as bk
    ws = wb.create_sheet(POCKETS)
    lv = live.ensure(wb, res)
    b = res.config.benchmark
    lw = label_widths(res)
    pt = bk._partner(res) if res.config.split else None
    kinds_ = [TWO_WAY] + ([split_label(res)] if res.three_way else [])
    # P1: the label columns fit the Run's labels and the dropdown over them; P2: a number column is its heading + 2
    # where the heading is the longer ("Could have caught"), never less than its value + 2
    widths = {1: 2, K_NUM: 5,
              K_BAND: max(lw["band"], house.fit([plain(m) for m in rates(res)], floor=0, cap=LABELS_CAP, pad=3)),
              K_SEG: max(lw["seg"], house.fit(kinds_, floor=0, cap=LABELS_CAP, pad=3)),
              K_HALF: max(lw["half"], house.fit(SHOW, floor=0, cap=LABELS_CAP, pad=3)),
              K_LOANS: 9, K_THIS: 11, K_REST: 12, K_GAP: 14, K_EX: 22,
              # the widest word Worse? can print, the borderline flag's included ("Not sure · borderline (p 0.052)")
              K_WORSE: house.fit([live.TOO_FEW, "Worse?", f"{live.NOT_SURE} · {stats.borderline_words(0.052, 0.95)}"],
                                 floor=11, cap=36),
              K_P: SPLIT_FLOOR, K_MAT: 11, K_CAUGHT: house.fit(["Could have caught"], floor=11, cap=20),
              K_HOLDS: house.fit([f"No: may be mostly {pt[0]}", f"Holds {pt[0]} fixed?"] if pt else [],
                                 floor=12, cap=LABELS_CAP, pad=3)}
    _widths(ws, widths)
    house.title_band(ws, POCKETS, "Which pockets lose more than their share, how much, and whether it's real "
                                  "and big enough to matter.", K_BAND, K_HOLDS, tab=house.TAB_RESULT)
    ws.cell(row=1, column=K_NUM).fill = house.fill(INK)             # the band runs over the # column too
    ws.cell(row=1, column=K_NUM).border = Border(bottom=Side(style="thick", color=house.KEY_RED))
    if b is None or not rates(res):
        _cell(ws, 3, 2, "Needs the Control settings.", h="left")
        return
    r = house.method_note(ws, 3, K_BAND, K_HOLDS, _pockets_note(res))
    ms = rates(res)
    kinds = [("grids", TWO_WAY)] + ([("three-way", split_label(res))] if res.three_way else [])
    m_rng, (k_rng, pts_rng, loans_rng) = choices.add(
        "Pockets: Measure", [plain(m) for m in ms], [m.name for m in ms], [1 if m.in_points else 0 for m in ms],
        [1 if bk._unit(m) == "loans" else 0 for m in ms])
    kind_rng, _ = choices.add("Pockets: Pockets", [label for _, label in kinds])
    show_rng, _ = choices.add("Pockets: Show", list(SHOW))
    # the selected measure's key and unit, in hidden cells beside the dropdowns
    s = r + 4
    sel = {"measure": f"'{POCKETS}'!" + dropdown(ws, s, K_BAND, "Measure", m_rng, plain(ms[0])),
           "kind": f"'{POCKETS}'!" + dropdown(ws, s, K_SEG, "Pockets", kind_rng, TWO_WAY),
           "show": f"'{POCKETS}'!" + dropdown(ws, s, K_HALF, "Show", show_rng, SHOW[0])}
    for name, ref in sel.items():
        wb.defined_names[f"pk_sel_{name}"] = DefinedName(f"pk_sel_{name}", attr_text=ref)
    M = sel["measure"]
    key, pts, loans = (f"${col(K_SEL)}${s}", f"${col(K_SEL)}${s + 1}", f"${col(K_SEL)}${s + 2}")
    ws[key.replace("$", "")] = f"=IFERROR(INDEX({k_rng},MATCH({M},{m_rng},0)),\"\")"
    ws[pts.replace("$", "")] = f"=IFERROR(INDEX({pts_rng},MATCH({M},{m_rng},0))=1,FALSE)"
    ws[loans.replace("$", "")] = f"=IFERROR(INDEX({loans_rng},MATCH({M},{m_rng},0))=1,FALSE)"
    material = material_at(res, key, loans)                   # the materiality line in the measure's own unit
    lines_in_use(ws, r, K_BAND, [(K_SEG, K_SEG), (K_HALF, K_HALF), (K_LOANS, K_THIS), (K_REST, K_GAP), (K_EX, K_EX)],
                 material, K_WORSE, K_HOLDS, f'Order and "Could have caught" are from the last Run, {stamp}.')
    last, most = _write_list(wb, res, lv, kinds, sel)
    Lr = lambda c: f"'{LIST}'!${col(c)}$2:${col(c)}${max(last, 2)}"      # noqa: E731
    cnt = lambda *crit: "COUNTIFS(" + ",".join([f"{Lr(L_KIND)},{sel['kind']}", f"{Lr(L_MEAS)},{M}", *crit]) + ")"
    worse_c, mat_c = f'{Lr(L_WORSE)},"{live.YES}"', f'{Lr(L_MAT)},"{live.YES}"'
    cap = ws.cell(row=s, column=K_LOANS, value=(
        f'=IFERROR({cnt(worse_c, mat_c)}&" worse and material · "&{cnt(worse_c)}&" worse · "&'
        f'SUM({Lr(L_SHOWN)})&" shown","")'))
    cap.font = Font(name="Calibri", size=10, color=SLATE)
    cap.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.merge_cells(start_row=s, start_column=K_LOANS, end_row=s, end_column=K_MAT)
    # the table
    h = s + 2
    J = "judged_band"
    half = ""
    if res.config.split:
        words = f"{res.config.split[0]} half" if res.config.split[1] == "own_median" else res.config.split[0]
        half = f'=IF({sel["kind"]}="{TWO_WAY}","","{words}")'
    heads = {K_NUM: "#", K_BAND: "Band", K_SEG: "Segment", K_HALF: half,
             K_LOANS: "Loans", K_THIS: "This pocket",
             K_REST: f'=IF({J},"Rest of band","Rest of book")',
             K_GAP: f'=IF({pts},"Gap in pts",IF({J},"× rest of band","× rest of book"))',
             K_EX: f'=IF({loans},"Bad loans above share",IF({pts},IF({J},"Dollars short of band","Dollars short of '
                   f'book"),"Dollars above share"))',
             K_WORSE: "Worse?", K_P: "p-value", K_MAT: "Material?", K_CAUGHT: "Could have caught"}
    pt = bk._partner(res) if res.config.split else None
    heads[K_HOLDS] = (f'=IF({sel["kind"]}="{TWO_WAY}","","Holds {pt[0]} fixed?")' if pt else "")
    house.header(ws, h, K_NUM, [heads[c] for c in range(K_NUM, K_HOLDS + 1)], centre_from=K_LOANS - K_NUM)
    ws.cell(row=h, column=K_NUM).alignment = Alignment(horizontal="center", vertical="center")
    first = h + 1
    n = max(max(most.values(), default=0), 1)
    for k in range(1, n + 1):
        rr = first + k - 1
        I, R = f"${col(K_IDX)}{rr}", f"${col(K_ROW)}{rr}"
        ws.cell(row=rr, column=K_IDX, value=f'=IFERROR(MATCH({k},{Lr(L_CUM)},0),"")')
        ws.cell(row=rr, column=K_ROW, value=f'=IF({I}="","",INDEX({Lr(L_ROW)},{I}))')
        lst = lambda c: f'IF({I}="","",IF(INDEX({Lr(c)},{I})="","",INDEX({Lr(c)},{I})))'     # noqa: E731
        vals = {K_NUM: f'=IF({I}="","",{k})', K_BAND: f"={lst(L_BAND)}", K_SEG: f"={lst(L_SEG)}",
                K_HALF: f"={lst(L_HALF)}", K_LOANS: f"={lst(L_LOANS)}", K_THIS: f"={at(live.P_RATE, R)}",
                K_REST: f"={at(live.P_REST, R)}",
                K_GAP: f'=IF({at(live.P_GAP, R)}="","",{at(live.P_GAP, R)}*IF({pts},100,1))',
                # Worse? with its borderline words, when it turns on a shuffled p-value that near the bar
                K_EX: f"={at(live.P_DOLLARS, R)}", K_WORSE: f"={at(live.P_WORSE_SAID, R)}", K_P: f"={at(live.P_P, R)}",
                K_MAT: f"={lst(L_MAT)}", K_CAUGHT: f"={lst(L_CAUGHT)}", K_HOLDS: f"={lst(L_HOLDS)}"}
        fmts = {K_LOANS: "#,##0", K_THIS: "0.00%", K_REST: "0.00%", K_GAP: X_FMT, K_EX: "#,##0", K_P: P_FMT,
                K_CAUGHT: X_FMT}
        for c, v in vals.items():
            _cell(ws, rr, c, v, h="left" if c in (K_BAND, K_SEG, K_HALF, K_HOLDS) else "center", fmt=fmts.get(c),
                  indent=1 if c in (K_BAND, K_SEG, K_HALF, K_HOLDS) else 0)
        ws.cell(row=rr, column=K_NUM).font = Font(name="Calibri", size=9, color=SLATE)
        ws.row_dimensions[rr].height = 16
    end = first + n - 1
    if not any(most.values()):
        _cell(ws, first, K_BAND, "Nothing is losing more than its share at the last Run's settings.", h="left")
    rng = lambda *cs: " ".join(f"{col(c)}{first}:{col(c)}{end}" for c in cs)     # noqa: E731
    # the colours, one set of rules per column (see cf): a split pocket whose grid doesn't hold the partner fixed
    # is grey, with no verdict colour; Worse? and Material? in the spec's verdict colours; a gap in points and
    # bad loans to one decimal follow the measure picked
    line = f'${col(K_NUM)}{first}<>""'
    loose = f'LEFT(${col(K_HOLDS)}{first},3)="No:"'
    # Worse?'s colour is its word's, borderline or not (the firm, 29 Sep 2026: flag it, the verdict stands)
    grey, W = Font(color=SLATE), live.base_word(f"${col(K_WORSE)}{first}")
    cf(ws, rng(K_NUM, K_BAND, K_SEG, K_HALF, K_LOANS, K_THIS, K_REST, K_P), [(loose, None, grey, None)], line)
    for c in (K_GAP, K_CAUGHT):
        cf(ws, rng(c), [(f"AND({loose},{pts})", None, grey, PTS_FMT), (loose, None, grey, None),
                        (pts, None, None, PTS_FMT)], line)
    cf(ws, rng(K_EX), [(f"AND({loose},{loans})", None, grey, "#,##0.0"), (loose, None, grey, None),
                       (loans, None, None, "#,##0.0")], line)
    cf(ws, rng(K_WORSE), [(loose, None, grey, None),
                          (f'{W}="{live.YES}"', ALERT, Font(color=CRIMSON, bold=True), None),
                          (f'{W}="{live.NOT_SURE}"', CANVAS, None, None),
                          (f'OR({W}="{live.NO}",{W}="{live.TOO_FEW}")', None, grey, None)], line)
    cf(ws, rng(K_MAT), [(loose, None, grey, None),
                        (f'${col(K_MAT)}{first}="{live.YES}"', MIST, Font(bold=True), None)], line)
    cf(ws, rng(K_HOLDS), [(loose, None, Font(color=CRIMSON, bold=True), None)], line)
    _hide(ws, K_IDX, K_SEL)
    ws.freeze_panes = f"A{first}"
    _fit(ws)


# --------------------------------------------------------------------------
# Paid, cost, kept


SIDES = (("contribution_rate", "Paid us", "gap vs"), ("gco_rate", "Cost us", "charge-offs"),
         ("ranr_rate", "Kept", "gap vs"))
(C_BAND, C_SEG, C_LOANS, C_PAID, C_PAID_D, C_COST, C_COST_D, C_KEPT, C_KEPT_D, C_TOG) = range(2, 12)
C_H = 40                  # hidden: the _views row, untested, each side's _pockets row and flag
(C_H_ROW, C_H_UN, C_H_RC, C_H_RG, C_H_RR, C_H_FC, C_H_FG, C_H_FR) = range(C_H, C_H + 8)
# Together's word alone (the chart and the colours read it), and each side's borderline p-value (live.P_BTXT)
C_H_TOG, C_H_BG, C_H_BR = C_H + 8, C_H + 9, C_H + 10
LABELLED = 8              # pockets numbered on the chart and named under it: the first rows, with a Together verdict
CHART_ROWS = 23           # rows the chart covers (11 cm at the tab's row height), so the names list starts under it
#: the chart's own cells, on a hidden sheet (Excel leaves out a chart's points in hidden columns): each row's point,
#: x then y, its name when it is read together and that point again, then the dashed lines and the corners
CHART = "_chart"
(H_X, H_Y, H_NAME, H_NX, H_NY, H_RX, H_RY, H_GX, H_GY, H_NUM) = range(1, 11)


def side_of(flag: str | None, higher: str) -> str | None:
    """A side's word for Together: "more" or "less" when its flag is worse or better and significant, "same"
    when it is tested and neither, None when untested. Charge-offs: worse is more; kept: worse is less."""
    if flag in (engine.WORSE, engine.BETTER):
        worse_is = "more" if higher == "worse" else "less"
        return worse_is if flag == engine.WORSE else ("less" if worse_is == "more" else "more")
    if flag in (engine.IN_LINE, engine.UNSURE_WORSE, engine.UNSURE_BETTER):
        return "same"
    return None


def together_of(gco_flag: str | None, ranr_flag: str | None) -> str:
    """Together, in Python: the engine's side of the formula on Paid, cost, kept."""
    return TOGETHER.get((side_of(gco_flag, "worse"), side_of(ranr_flag, "better")), "")


def together_said(tog: str | None, gco_border: str | None, ranr_border: str | None) -> str | None:
    """Together as the tab prints it, in Python: the word, and " · borderline (p 0.048)" when a side it turns on is
    borderline; with both, the two p-values, charge-offs first ("p 0.048 and 0.052"). The borderline words are
    each side's RateStat.borderline."""
    if not tog:
        return tog
    ps = [b[len("borderline (p "):-1] for b in (gco_border, ranr_border) if b]
    return f"{tog}{live.JOIN}borderline (p {' and '.join(ps)})" if ps else tog


def together_said_formula(tog: str, bg: str, br: str) -> str:
    """together_said as a formula, over Together's word and each side's live.P_BTXT."""
    both = f'IF(AND({bg}<>"",{br}<>""),{bg}&" and "&{br},{bg}&{br})'
    return (f'IF(OR({tog}="",AND({bg}="",{br}="")),{tog},{tog}&{live.q(live.JOIN + "borderline (p ")}&{both}'
            f'&")")')


def together_formula(g: str, k: str, untested: str) -> str:
    """Together as a formula over the two flags, blank on a row with a side untested."""
    W, B = f'"{engine.WORSE}"', f'"{engine.BETTER}"'
    same = f'OR({g}="{engine.IN_LINE}",{g}="{engine.UNSURE_WORSE}",{g}="{engine.UNSURE_BETTER}")'
    same_k = f'OR({k}="{engine.IN_LINE}",{k}="{engine.UNSURE_WORSE}",{k}="{engine.UNSURE_BETTER}")'
    return (f'IF(OR({untested}=1,{untested}=""),"",IF(AND({g}={W},{k}={B}),"{TOGETHER[("more", "more")]}",'
            f'IF(AND({g}={W},{k}={W}),"{TOGETHER[("more", "less")]}",IF(AND({g}={B},{k}={B}),'
            f'"{TOGETHER[("less", "more")]}",IF(AND({g}={B},{k}={W}),"{TOGETHER[("less", "less")]}",'
            f'IF(AND({same},{k}={W}),"{TOGETHER[("same", "less")]}",IF(AND({g}={W},{same_k}),'
            f'"{TOGETHER[("more", "same")]}","")))))))')


def pck_rows(res, g) -> list[dict]:
    """One grid's pockets for Paid, cost, kept, in the last Run's order: every pocket with all three comparisons
    against either comparison (below fewest loans a dollar rate is still shuffled, docs/statistics.md B2), those
    read together first, then by charge-off dollars; a row with a side untested last."""
    mates: dict = {}
    for (bl, _), _c in g.inner():
        mates[bl] = mates.get(bl, 0) + 1
    rows = []
    for (bl, dl), c in g.inner():
        ss = {k: c.rates[k] for k, *_ in SIDES}
        band = {k: s.vs_band for k, s in ss.items()}
        book = {k: s.vs_rest for k, s in ss.items()}
        if any(v is None for v in band.values()) and any(v is None for v in book.values()):
            continue
        untested = any(s.flag in (engine.THIN, engine.FEW) for s in ss.values())
        tog = "" if untested else together_of(ss["gco_rate"].flag, ss["ranr_rate"].flag)
        rows.append({"band": bl, "seg": dl, "units": c.rows, "untested": untested, "together": tog,
                     "g_over": ss["gco_rate"].dollars or 0.0, "gaps": [(v, x) for v, x in
                                                                     ((band["gco_rate"], band["ranr_rate"]),
                                                                      (book["gco_rate"], book["ranr_rate"]))]})
    rows.sort(key=lambda x: (x["untested"], x["together"] == "", -x["g_over"]))
    return rows


def write_pck(wb, res, choices: Choices, views: Views, stamp: str) -> None:
    """Paid, cost, kept (section 6): one grid at a time, three sides in column groups, Together, and the scatter."""
    from . import book as bk
    ws = wb.create_sheet(PCK)
    lv = live.ensure(wb, res)
    names = bk._names(res)
    lw = label_widths(res)
    # P1: Band and Segment fit the Run's labels; Band also the "live from Control" under the lines in use
    _widths(ws, {1: 2, C_BAND: max(lw["band_only"], house.fit(["live from Control"], floor=0, cap=32, pad=3)),
                 C_SEG: lw["seg_raw"], C_LOANS: 9, C_PAID: 11, C_PAID_D: 13, C_COST: 11, C_COST_D: 13,
                 C_KEPT: 11, C_KEPT_D: 13,
                 # the longest verdict with the borderline flag on one side; on both it runs on over the gap beside it
                 C_TOG: house.fit([f"{t} · {stats.borderline_words(0.048, 0.95)}" for t in TOGETHER.values()],
                                  floor=28, cap=56), 12: 3})
    house.title_band(ws, PCK, "What each pocket paid us, what it cost us, and what we kept.", C_BAND, C_TOG + 8,
                     tab=house.TAB_RESULT)
    line = bk.profit_line(res)
    r = house.method_note(ws, 3, C_BAND, C_TOG, [
        ("Paid us", "Earned before losses: RANR + GCO per booked dollar. RANR already has the charge-offs taken "
                    "out, so this adds them back. Gap: points of booked dollars ahead of (+) or short of (-) the "
                    "rest; Dollars: what that comes to."),
        ("Cost us", "Charge-offs (GCO) per booked dollar, as a multiple of the rest; Dollars: charge-offs above "
                    "the rest's rate."),
        ("Kept", "Kept after losses: RANR per booked dollar, as a gap in points and dollars, like Paid us."),
        ("The rest", live.text("Judged against on Control picks it: now ",
                               ('IF(judged_band,"the rest of its band","the rest of the book")',),
                               ". A pocket alone in its band is compared with the rest of the book.")),
        ("Shading", live.text(
            "Pink: worse, and real. Green: better, and real. None: it could be chance (the p-value isn't under ",
            ('TEXT(significance_bar,"0%")',), "), or the pocket has too few losses to test. Charge-offs count at ",
            ('TEXT(worse_at,"0.00")',), "x or ", ('TEXT(better_at,"0.00")',), "x; profit ",
            ('IF(profit_kind="test","when its own test says so",IF(profit_kind="points","at "&TEXT(profit_line*100,'
             '"0.00")&" points either way","at a gap of $"&TEXT(profit_line,"#,##0")))',), ".")),
        ("Together", live.text("The two sides read at once. Priced for it: more charge-offs and more kept. Net drain: "
                               "more charge-offs and less kept. Strong: fewer charge-offs and more kept. Safe but "
                               "idle: fewer charge-offs and less kept. Earns less, not from losses: less kept while "
                               "charge-offs are about the same. Losing more, profit holding: more charge-offs while "
                               "what we kept is about the same. Blank: nothing to read together.", *BORDER_WORDS,
                               " Together gives the p-value of each side that is, charge-offs first.")),
        ("Order and chart", "Rows are as of the last Run: the pockets read together first, then by charge-off "
                            "dollars; a pocket with too few losses last. The chart shows the grid picked above, "
                            "live; the pockets read together are named on it."),
    ])
    grids = res.grids
    gnames = [f"{names[g.band]} x {names[g.dimension]}" for g in grids]
    g_rng, _ = choices.add("Paid, cost, kept: Grid", gnames)
    lines_in_use(ws, r, C_BAND, [(C_SEG, C_SEG), (C_LOANS, C_PAID), (C_PAID_D, C_COST), (C_COST_D, C_KEPT),
                                 (C_KEPT_D, C_TOG)],
                 material_at(res),
                 C_TOG + 2, C_TOG + 9, f"The order is from the last Run, {stamp}.")
    if CHART in wb.sheetnames:
        del wb[CHART]
    hs = wb.create_sheet(CHART)
    hs.sheet_state = "hidden"
    s = r + 4
    G = dropdown(ws, s, C_BAND, "Grid", g_rng, gnames[0] if gnames else "")
    ws.merge_cells(start_row=s, start_column=C_BAND, end_row=s, end_column=C_SEG)
    # the rows, every grid's, on _views
    most = 1
    bounds_x, bounds_y = [], []
    for g, gname in zip(grids, gnames):
        rows = pck_rows(res, g)
        most = max(most, len(rows))
        for k, x in enumerate(rows, start=1):
            prows = [lv.rows.get(("grids", id(g), x["band"], x["seg"], m)) for m, *_ in SIDES]
            views.put(f"C|{gname}|{k}", [x["band"], x["seg"], x["units"], 1 if x["untested"] else 0, *prows])
            if not x["untested"]:
                for gx, gy in x["gaps"]:
                    if gx:
                        bounds_x.append(gx)
                    if gy is not None:
                        bounds_y.append(gy * 100)
    # the column groups, each under a 2 px INK rule, then the headers
    h = s + 2
    J = "judged_band"
    for a, b_, words in ((C_PAID, C_PAID_D, f'="Paid us · gap vs "&IF({J},"band","book")'),
                         (C_COST, C_COST_D, "Cost us · charge-offs"),
                         (C_KEPT, C_KEPT_D, f'="Kept · gap vs "&IF({J},"band","book")'), (C_TOG, C_TOG, "")):
        ws.merge_cells(start_row=h, start_column=a, end_row=h, end_column=b_)
        _cell(ws, h, a, words, bold=True, size=9, name="Arial")
        for c in range(a, b_ + 1):
            ws.cell(row=h, column=c).border = Border(bottom=Side(style="medium", color=INK))
    house.header(ws, h + 1, C_BAND, ["Band", "Segment", "Loans", "Gap pts", "Dollars",
                                     f'=IF({J},"× band","× book")', "Dollars", "Gap pts", "Dollars", "Together"],
                 centre_from=2)
    first = h + 2
    for k in range(1, most + 1):
        rr = first + k - 1
        V = f"${col(C_H_ROW)}{rr}"
        ws.cell(row=rr, column=C_H_ROW, value="=" + match(xk("C|", (G,), f"|{k}")))
        for c, j in ((C_H_UN, 4), (C_H_RC, 5), (C_H_RG, 6), (C_H_RR, 7)):
            ws.cell(row=rr, column=c, value=f"={pick(V, j)}")
        RC, RG, RR = (f"${col(c)}{rr}" for c in (C_H_RC, C_H_RG, C_H_RR))
        for c, prow in ((C_H_FC, RC), (C_H_FG, RG), (C_H_FR, RR)):
            ws.cell(row=rr, column=c, value=f"={at(live.P_FLAG, prow)}")
        # Together turns on both sides' flags, so it is borderline when either is (the firm, 29 Sep 2026)
        for c, prow in ((C_H_BG, RG), (C_H_BR, RR)):
            ws.cell(row=rr, column=c, value=f"={at(live.P_BTXT, prow)}")
        TOG = f"${col(C_H_TOG)}{rr}"
        ws.cell(row=rr, column=C_H_TOG, value="=" + together_formula(f"${col(C_H_FG)}{rr}", f"${col(C_H_FR)}{rr}",
                                                                     f"${col(C_H_UN)}{rr}"))
        pts = lambda prow: f'=IF({at(live.P_GAP, prow)}="","",{at(live.P_GAP, prow)}*100)'         # noqa: E731
        short = lambda prow: f'=IF({at(live.P_DOLLARS, prow)}="","",-{at(live.P_DOLLARS, prow)})'  # noqa: E731
        vals = {C_BAND: f"={pick(V, 1)}", C_SEG: f"={pick(V, 2)}", C_LOANS: f"={pick(V, 3)}",
                C_PAID: pts(RC), C_PAID_D: short(RC), C_COST: f"={at(live.P_GAP, RG)}",
                C_COST_D: f"={at(live.P_DOLLARS, RG)}", C_KEPT: pts(RR), C_KEPT_D: short(RR),
                C_TOG: "=" + together_said_formula(TOG, f"${col(C_H_BG)}{rr}", f"${col(C_H_BR)}{rr}")}
        fmts = {C_LOANS: "#,##0", C_PAID: PTS_FMT, C_PAID_D: "#,##0", C_COST: X_FMT, C_COST_D: "#,##0",
                C_KEPT: PTS_FMT, C_KEPT_D: "#,##0"}
        for c, v in vals.items():
            _cell(ws, rr, c, v, h="left" if c in (C_BAND, C_SEG, C_TOG) else "center", fmt=fmts.get(c),
                  indent=1 if c in (C_BAND, C_SEG, C_TOG) else 0, bold=c == C_TOG)
        ws.row_dimensions[rr].height = 16
        # the chart's own cells: every pocket read, and the ones read together named
        T = f"'{PCK}'!"
        un, cost, kept, tog = (f"{T}${col(c)}${rr}" for c in (C_H_UN, C_COST, C_KEPT, C_H_TOG))
        hs.cell(row=k, column=H_X, value=f'=IF(OR({un}<>0,{cost}="",{kept}=""),NA(),{cost})')
        hs.cell(row=k, column=H_Y, value=f"=IF(ISNA({col(H_X)}{k}),NA(),{kept})")
        hs.cell(row=k, column=H_NAME, value=f'=IF({tog}="","",{T}${col(C_BAND)}${rr}&" / "&{T}${col(C_SEG)}${rr})')
        hs.cell(row=k, column=H_NX, value=f'=IF({tog}="",NA(),{cost})')
        hs.cell(row=k, column=H_NY, value=f'=IF({tog}="",NA(),{kept})')
        # coloured by verdict, whatever the row (the firm, 29 Sep 2026: a Net drain drawn black read as nothing)
        bad = f'{tog}="{BAD_TOGETHER[0]}"'
        good = f'OR({tog}="{GOOD_TOGETHER[0]}",{tog}="{GOOD_TOGETHER[1]}")'
        hs.cell(row=k, column=H_RX, value=f"=IF(AND(NOT(ISNA({col(H_X)}{k})),{bad}),{col(H_X)}{k},NA())")
        hs.cell(row=k, column=H_RY, value=f"=IF(ISNA({col(H_RX)}{k}),NA(),{col(H_Y)}{k})")
        hs.cell(row=k, column=H_GX, value=f"=IF(AND(NOT(ISNA({col(H_X)}{k})),{good}),{col(H_X)}{k},NA())")
        hs.cell(row=k, column=H_GY, value=f"=IF(ISNA({col(H_GX)}{k}),NA(),{col(H_Y)}{k})")
        hs.cell(row=k, column=H_NUM, value=f'=IF({col(H_NAME)}{k}="","",{k})')
    end = first + most - 1
    un = f"${col(C_H_UN)}{first}"
    line_on = f'${col(C_BAND)}{first}<>""'
    for (a, b_), fc in (((C_PAID, C_PAID_D), C_H_FC), ((C_COST, C_COST_D), C_H_FG), ((C_KEPT, C_KEPT_D), C_H_FR)):
        f = f"${col(fc)}{first}"
        cf(ws, f"{col(a)}{first}:{col(b_)}{end}", [(f'AND({un}=0,{f}="{engine.WORSE}")', ALERT, None, None),
                                                   (f'AND({un}=0,{f}="{engine.BETTER}")', POSITIVE_BG, None, None)],
           line_on)
    T = f"${col(C_H_TOG)}{first}"                  # the word alone: borderline or not, the colour is the word's
    cf(ws, f"{col(C_TOG)}{first}:{col(C_TOG)}{end}",
       [(f'OR({T}="{GOOD_TOGETHER[0]}",{T}="{GOOD_TOGETHER[1]}")', None, Font(color=POSITIVE, bold=True), None),
        (f'{T}="{BAD_TOGETHER[0]}"', None, Font(color=CRIMSON, bold=True), None)], line_on)
    cf(ws, f"{col(C_BAND)}{first}:{col(C_LOANS)}{end}", [], line_on)
    if grids and bounds_x:
        _scatter(ws, hs, res, most, bounds_x, bounds_y, line, h)
    _hide(ws, C_H, C_H + 20)
    ws.freeze_panes = f"A{first}"
    _fit(ws)


def _nice_step(span: float) -> float:
    for step in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50):
        if span / step <= 8:
            return step
    return 100.0


def _scatter(ws, hs, res, n: int, xs: list, ys: list, line, anchor: int) -> None:
    """The scatter of the grid picked (section 6): charge-offs' multiple across on a log scale, the profit gap in
    points up, a dashed line at 1x and at 0, the four corners named, and the pockets read together named. Its
    points are the table's cells, so it follows the Grid dropdown and Control."""
    b = res.config.benchmark
    chart = ScatterChart()
    chart.title = "Cost us against what we kept, the grid picked above"
    chart.style = 13
    # no axis titles: Excel drew them over the axes' own numbers (the firm, 29 Sep 2026); the line above the chart
    # says what each axis is
    x_lo = min(0.1, 10 ** math.floor(math.log10(min([v for v in xs if v > 0] + [b.better_at]))))
    x_hi = max(10.0, 10 ** math.ceil(math.log10(max(xs + [b.worse_at]))))
    band = line.value * 100 if line is not None and line.kind == "points" else 0.0
    lo_y, hi_y = min(ys + [-band, 0.0]), max(ys + [band, 0.0])
    step = _nice_step((hi_y - lo_y) or 1.0)
    y_lo, y_hi = math.floor(lo_y / step) * step - step, math.ceil(hi_y / step) * step + step
    X, Y = (Reference(hs, min_col=c, min_row=1, max_row=n) for c in (H_X, H_Y))
    pts = Series(Y, X, title="Pockets")
    pts.marker.symbol = "circle"
    pts.marker.size = 6
    pts.marker.graphicalProperties.solidFill = INK
    pts.marker.graphicalProperties.line.solidFill = INK
    pts.graphicalProperties.line.noFill = True
    chart.series.append(pts)
    for cx, cy, fill in ((H_RX, H_RY, house.KEY_RED), (H_GX, H_GY, POSITIVE)):
        dots = Series(*(Reference(hs, min_col=c, min_row=1, max_row=n) for c in (cy, cx)))
        dots.marker.symbol = "circle"
        dots.marker.size = 8
        dots.marker.graphicalProperties.solidFill = fill
        dots.marker.graphicalProperties.line.solidFill = fill
        dots.graphicalProperties.line.noFill = True
        chart.series.append(dots)
    # the lines and the corners, under the points
    hr = n + 3
    lines = [((1.0, y_lo), (1.0, y_hi)), ((x_lo, 0.0), (x_hi, 0.0))]
    for (x1, y1), (x2, y2) in lines:
        for k, (xv, yv) in enumerate(((x1, y1), (x2, y2))):
            hs.cell(row=hr + k, column=H_X, value=xv)
            hs.cell(row=hr + k, column=H_Y, value=yv)
        ln = Series(Reference(hs, min_col=H_Y, min_row=hr, max_row=hr + 1),
                    Reference(hs, min_col=H_X, min_row=hr, max_row=hr + 1), title="line")
        ln.marker.symbol = "none"
        ln.graphicalProperties.line.solidFill = house.KEY_RED
        ln.graphicalProperties.line.dashStyle = "dash"
        chart.series.append(ln)
        hr += 2
    corners = (("Priced for it", x_hi / 1.6, y_hi - step / 2), ("Net drain", x_hi / 1.6, y_lo + step / 2),
               ("Strong", x_lo * 1.6, y_hi - step / 2), ("Safe but idle", x_lo * 1.6, y_lo + step / 2))
    for name, xv, yv in corners:
        hs.cell(row=hr, column=H_X, value=xv)
        hs.cell(row=hr, column=H_Y, value=yv)
        c = Series(Reference(hs, min_col=H_Y, min_row=hr, max_row=hr),
                   Reference(hs, min_col=H_X, min_row=hr, max_row=hr), title=name)
        c.marker.symbol = "none"
        c.graphicalProperties.line.noFill = True
        c.dLbls = _labels(pos="ctr")
        chart.series.append(c)
        hr += 1
    # the named pockets: the first rows, which are the ones read together at the last Run, numbered on the chart
    # and named in the list beside it (their names overlapped when written on the chart); a row whose verdict has
    # gone (a line changed on Control) drops its number
    for k in range(min(LABELLED, n)):
        rr = 1 + k
        one = Series(Reference(hs, min_col=H_NY, min_row=rr, max_row=rr),
                     Reference(hs, min_col=H_NX, min_row=rr, max_row=rr))
        one.tx = SeriesLabel(strRef=StrRef(f"'{CHART}'!${col(H_NUM)}${rr}"))
        one.marker.symbol = "none"
        one.graphicalProperties.line.noFill = True
        one.dLbls = _labels(pos="r")
        chart.series.append(one)
    chart.legend = None
    chart.x_axis.scaling.logBase = 10
    chart.x_axis.scaling.min, chart.x_axis.scaling.max = x_lo, x_hi
    chart.y_axis.scaling.min, chart.y_axis.scaling.max = y_lo, y_hi
    chart.y_axis.majorUnit = step
    chart.x_axis.number_format = '0.0"×"'
    chart.y_axis.number_format = '+0" pts";-0" pts";0" pts"'
    chart.x_axis.delete = chart.y_axis.delete = False
    chart.x_axis.crosses = "min"
    chart.y_axis.crosses = "min"
    chart.width, chart.height = 17, 11
    ws.add_chart(chart, f"{col(C_TOG + 2)}{anchor}")
    # what the axes are, above the chart, and the numbered pockets' names under it
    _cell(ws, anchor - 1, C_TOG + 2, "Across: charge-offs × the rest, on a log scale. Up: kept, as a gap in points. "
                                     "Red: Net drain. Green: Strong or Priced for it.", size=9, name="Arial", h="left")
    below = anchor + CHART_ROWS
    _cell(ws, below, C_TOG + 2, "Numbered on the chart", bold=True, size=9, name="Arial", h="left")
    for k in range(min(LABELLED, n)):
        _cell(ws, below + 1 + k, C_TOG + 2,
              f"=IF('{CHART}'!${col(H_NAME)}${1 + k}=\"\",\"\",\"{1 + k}  \"&'{CHART}'!${col(H_NAME)}${1 + k})",
              size=9, name="Arial", h="left")


def _labels(pos: str):
    d = DataLabelList()
    d.showSerName = True
    for flag in ("showVal", "showCatName", "showLegendKey", "showPercent", "showBubbleSize"):
        setattr(d, flag, False)
    d.position = pos
    return d


# --------------------------------------------------------------------------
# Grids


def _short(res, label: str) -> str:
    """A three-way segment in a grid's header: "Broker · high"."""
    if not res.config.split or " / " not in str(label):
        return str(label)
    seg, half = _halves(res, label)
    return f"{seg} · {half}"


def heat_kind(m) -> str:
    """How a gap reads on the heat scale: a multiple where more is worse ("x"), where more is better ("xr"), or a
    gap in points where more is better ("pts")."""
    if m.in_points:
        return "pts"
    return "x" if m.higher_is == "worse" else "xr"


#: Grids' Loan size (the firm, 29 Sep 2026): its key, its name in the Measure dropdown, and its shades, a single
#: neutral hue by how many times the book's average a cell's loans are (darker is bigger, as the Loans block's
#: darker is more): a description, not a finding, so never red or green
SIZE, SIZE_NAME = "loan_size", "Loan size"
SIZE_STEPS = ((2.0, STONE), (1.5, "CFCAC2"), (1.25, MIST), (1.1, house.ROW_RULE))
SIZE_FMT = '"$"#,##0'
#: Grids' "Only loans where" (the firm, 29 Sep 2026): the option that filters nothing, and a filtered view's key
ALL_LOANS = "All loans"
WHERE = "|where {}"


def fewest(res) -> int | None:
    """The fewest loans in a pocket the Run used (Control's "Fewest loans in a pocket", its suggestion worked out
    when that was picked): a Grids cell with fewer is grey and sets no colour."""
    b = res.config.benchmark
    return b.min_units if b is not None else None


#: Grids' column widths (the firm, 29 Sep 2026: "i prefer to have nice even layouts, or at least the column sizes
#: should make sense for the data we see"; docs/column-widths-survey-2026-09-29.md): one width for every data column
#: of the four blocks, and one for both label columns, each fitted per Run to what any grid can show, between these
DATA_FLOOR, DATA_CAP = 9, 16
LABEL_FLOOR, LABEL_CAP = 12, 28
#: a header line of Arial bold 9, in points
HEAD_LINE = 12
#: the labels What one cell says puts in the left label column
ONE_CELL_LABELS = ("Rate", "vs the book", "vs rest of band", "Loans", "The colour")


def _shown(v, fmt: str) -> str:
    """A number as its cell's format shows it, for measuring a column (the formats Grids and Split write)."""
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return "" if v is None else str(v)
    return {"pct": f"{v * 100:.2f}%", "x": f"{v:.2f}×", "pts": f"{v:+.2f} pts", "usd": f"${v:,.0f}",
            "amt": f"{v:,.2f}"}.get(fmt, f"{v:,.0f}")


def _split_layout(res) -> list[str]:
    """A split grid's parts, each as the engine writes it after the segment ("REV_DEBT high half", "SYS_FLAG N"),
    in one order for every split grid of the Run (G4, decided for the firm 29 Sep 2026): every segment gets every
    part, so the segment row over them is merged once for all the split grids the Grid dropdown can pick. A part a
    segment has no loans in is an empty column, never a missing one, so the columns under a segment stay put."""
    sf = res.config.split[0] if res.config.split else None
    if not res.three_way or sf is None:
        return []
    word = {engine.HIGH: f"{sf} high half", engine.LOW: f"{sf} low half", engine.NO_SPLIT_VALUE: f"no {sf}"}
    tails: list[str] = []
    for t in ([word.get(lab, f"{sf} {lab}") for g in res.grids for lab in g.split_labels]
              + [str(d).rpartition(" / ")[2] for g in res.three_way for d in g.dim_labels]):
        if t not in tails:
            tails.append(t)
    return tails


def _split_cols(g, tails: list[str]) -> list[str]:
    """A split grid's columns in that layout: each segment in the engine's order, then every part."""
    segs: list[str] = []
    for d in g.dim_labels:
        seg = str(d).rpartition(" / ")[0]
        if seg not in segs:
            segs.append(seg)
    return [f"{seg} / {t}" for seg in segs for t in tails]


def grid_views(res, views: Views) -> tuple[list[str], list, int, int, dict]:
    """Every grid's four blocks on _views, two-way and split, and each again on only the loans with one value of a
    category split (G|<grid>|where <value>|...); returns the grids' names, the measures, the most rows and
    columns any grid has, and what Grids' columns must fit (G1, G2): `heads`, every column label as the lower
    header row shows it; `segs`, every split grid's segment, shown over its parts; `parts`, how many parts each
    segment has (0 with no split grid) and `spans`, the most segments a split grid has; `rows`, every row label
    and band name; `values`, the longest value any block shows."""
    from . import book as bk
    names = bk._names(res)
    ms = rates(res)
    tails = _split_layout(res)
    tails = tails if len(tails) > 1 else []            # one part is one column: no segment row over it
    fit = {"heads": {"All"}, "segs": set(), "parts": len(tails), "spans": 0, "rows": {"All"}, "values": 0}
    gnames, most_r, most_c = [], 1, 1
    for g in list(res.grids) + list(res.three_way):
        gname = f"{names[g.band]} x {names[g.dimension]}"
        gnames.append(gname)
        split = bool(tails) and g in res.three_way
        rows_ = g.band_labels + [engine.ALL]
        cols_ = (_split_cols(g, tails) if split else list(g.dim_labels)) + [engine.ALL]
        most_r, most_c = max(most_r, len(rows_)), max(most_c, len(cols_))
        fit["rows"] |= {str(x) for x in g.band_labels} | {names[g.band]}
        for d in cols_[:-1]:
            seg, half = _halves(res, d) if split else ("", _short(res, d))
            fit["heads"].add(str(half))
            if split:
                fit["segs"].add(seg)
        if split:
            fit["spans"] = max(fit["spans"], (len(cols_) - 1) // len(tails))
        _grid_view(res, views, f"G|{gname}", g, g, names, rows_, cols_, ms, fit, split)
        for v in res.split_values:
            if v in g.filtered:
                _grid_view(res, views, f"G|{gname}" + WHERE.format(v), g.filtered[v], g, names, rows_, cols_, ms,
                           fit, split)
    views.put("G|fewest", [fewest(res)])
    return gnames, ms, most_r, most_c, fit


def grid_widths(fit: dict, grp: dict | None = None) -> tuple[float, float]:
    """Grids' two widths (G1, G2): the data width, one for every data column of the four blocks and the groups table
    under them, is the larger of the longest value + 2 and the two-line width of the longest column label + 2 (a
    split grid's segment across all its parts), kept between DATA_FLOOR and DATA_CAP; the label width, the longest
    row label or band name + 3 (indent 1), between LABEL_FLOOR and LABEL_CAP."""
    grp = grp or {}
    parts = fit["parts"]
    need = [fit["values"] + 2, grp.get("values", 0) + 2]
    need += [house.two_line_width(h) + 2 for h in list(fit["heads"]) + list(grp.get("heads", ()))]
    need += [math.ceil((house.two_line_width(sg) + 2) / parts) for sg in fit["segs"]] if parts else []
    need += [len(sg) + 3 for sg in grp.get("segs", ())]           # the groups' segments: one line, indent 1
    dw = min(DATA_CAP, max([DATA_FLOOR] + need))
    lw = house.fit(list(fit["rows"]) + list(ONE_CELL_LABELS) + list(grp.get("bands", ())), floor=LABEL_FLOOR,
                   cap=LABEL_CAP, pad=3)
    return dw, lw


def _grid_view(res, views: Views, key: str, g, whole, names, rows_, cols_, ms, fit=None, split=False) -> None:
    """One view of one grid on _views: its labels (the whole grid's, so the Row and Column picked stay put), its
    loans, and each measure's rate, against the book and against the rest of the band, with the heat's kind,
    its bound, the fewest losses, the book's own figure and the fewest loans. A cell under the fewest loans is
    left out of the bound (the firm, 29 Sep 2026: a 3-loan cell at -50 points was setting the scale)."""
    from . import book as bk
    b = res.config.benchmark
    few = fewest(res)
    shows = [m for m in res.measures if m.mode == "median"]
    untested = (engine.THIN, engine.FEW)
    views.put(f"{key}|cols", [_short(res, d) if d != engine.ALL else "All" for d in cols_])
    # the header's two rows (G4): a split grid's segment over its parts, then each part; any other grid's labels
    # sit on the lower row
    views.put(f"{key}|heads", [_halves(res, d)[1] if split and d != engine.ALL else _short(res, d)
                               if d != engine.ALL else "All" for d in cols_])
    views.put(f"{key}|segs", [_halves(res, d)[0] for d in cols_[:-1:max(fit["parts"], 1)]]
              if split and fit else [""])
    views.put(f"{key}|rows", [bl if bl != engine.ALL else "All" for bl in rows_])

    def seen(vals, fmt):
        if fit is not None:
            fit["values"] = max([fit["values"]] + [len(_shown(v, fmt)) for v in vals if v is not None])
    views.put(f"{key}|names", [names[whole.band], names[whole.dimension]])
    total = g.cells[(engine.ALL, engine.ALL)].rows if (engine.ALL, engine.ALL) in g.cells else 0
    views.put(f"{key}|total", [total])
    thin = lambda c: c is None or (few is not None and c.rows < few)          # noqa: E731
    for i, bl in enumerate(rows_, start=1):
        views.put(f"{key}|loans|{i}", [g.cells[(bl, d)].rows if (bl, d) in g.cells else None for d in cols_])
        seen([g.cells[(bl, d)].rows for d in cols_ if (bl, d) in g.cells], "n")
    for m in ms:
        got = []
        for i, bl in enumerate(rows_, start=1):
            rate, book, band = [], [], []
            for d in cols_:
                c = g.cells.get((bl, d))
                s = c.rates[m.name] if c is not None else None
                rate.append(s.rate if s is not None else None)
                bv = bk._shown(s.vs_topline, m) if s is not None and s.reading_topline not in untested else None
                book.append(bv)
                nv = (bk._shown(s.vs_band, m) if s is not None and bl != engine.ALL and d != engine.ALL
                      and s.reading_band not in untested else None)
                band.append(nv)
                if not thin(c):
                    got += [abs(v) for v in (bv, nv) if isinstance(v, (int, float))]
            views.put(f"{key}|{m.name}|rate|{i}", rate)
            views.put(f"{key}|{m.name}|book|{i}", book)
            views.put(f"{key}|{m.name}|band|{i}", band)
            seen(rate, "pct")
            seen(book + band, "pts" if m.in_points else "x")
        views.put(f"{key}|{m.name}|meta", [heat_kind(m), max(got + [0.01]), b.min_events if b else None,
                                           res.total.rates[m.name].rate, few])
    if res.book_size is not None and res.book_size.loans:
        for i, bl in enumerate(rows_, start=1):
            got = [engine.size_vs(g.sizes, bl, d, res.book_size) for d in cols_]
            for j, what in enumerate(("rate", "median", "book", "band")):
                views.put(f"{key}|{SIZE}|{what}|{i}", [x[j] for x in got])
                seen([x[j] for x in got], "usd" if what in ("rate", "median") else "x")
        views.put(f"{key}|{SIZE}|meta", ["size", 1, None, res.book_size.average, few])
    for sm in shows:
        k = f"show_{sm.name}"
        for i, bl in enumerate(rows_, start=1):
            vals = []
            for d in cols_:
                c = g.cells.get((bl, d))
                med = c.medians.get(sm.name) if c is not None else None
                vals.append(None if med is None else (med.mean if sm.show == "average" else med.median))
            views.put(f"{key}|{k}|rate|{i}", vals)
            seen(vals, "amt")
        views.put(f"{key}|{k}|meta", ["amt", 1, None, None, few])


#: One cell read out in words under the Grids' blocks (the firm, 29 Sep 2026: "select a particular line and say I
#: want this as an example"). Fixed by measure, so they read the same from run to run; only the names and numbers
#: change. {these} is "These 237 loans" (or "This one loan"), {their} "their" (or "its"), {r} the rate, {x} a
#: multiple, {pts} a gap in points and {more} its side, {against} what it is set against, {measure} the measure's name. A measure not named here takes its kind's.
SAY = {"outcome_loans": ("{these}: {r} went bad.", "{x}× the bad-loan rate of {against}."),
       "outcome_booked": ("{these}: {r} of {their} booked dollars were in loans that went bad.",
                          "{x}× the bad-dollar rate of {against}."),
       "gco_rate": ("{these} charged off {r} of {their} booked dollars.",
                    "{x}× the charge-off rate of {against}."),
       "ranr_rate": ("{these} kept {r} of {their} booked dollars after losses.",
                     "Kept {pts} points {more} of their booked dollars than {against}."),
       "contribution_rate": ("{these} earned {r} of {their} booked dollars before losses.",
                             "Earned {pts} points {more} of their booked dollars than {against}."),
       # {med} the median booked per loan (the firm, 29 Sep 2026)
       SIZE: ("{these} averaged {r} booked, median {med}.", "{x}× the average loan of {against}.")}
SAY_KIND = {"x": ("{these}: {measure} is {r}.", "{x}× the rate of {against}."),
            "pts": ("{these}: {measure} is {r}.", "{pts} points {more} than {against}."),
            "amt": ("{these}: {measure} is {r}.", "Not compared: this figure is shown, not tested.")}
SAY_BOOK = "the whole book"
SAY_BAND = "the other loans in {row}"
SAY_ALONE = "Blank: alone in its band. Nothing else in {row} to compare with."
SAY_FEW = "Blank: fewer losses than the minimum ({min} losses), so not compared."
SAY_NOT = "Blank: not compared."
SAY_LOANS = "{loans}; {row} has {m} in all."
SAY_COLOUR = ("vs the book is {book}, vs rest of band {band}. Red is worse, green better, deeper a bigger gap. "
              "It is the size of the gap, not a test.")
#: a cell under the fewest loans (the firm, 29 Sep 2026: "grey out cells with too few loans")
SAY_GREY = "Grey: only {loans}, fewer than the {min} set on Control, so not coloured."
SAY_SIZE = ("No red or green: loan size is a description, not a finding. Shaded darker the bigger the loans are "
            "against the book's.")
#: filtering needs a category to filter by (Split by, in the launcher)
SAY_NO_FILTER = "Filtering needs Split by a category."
SAY_PICK = "Pick a Row and a Column above: their lists follow the Grid."
SAY_EMPTY = "No loans in this pocket."
SAY_NORATE = "No rate: these loans have nothing to divide by for this measure."
#: other columns named after "the other loans in <row>" when there are this many or fewer
SAY_NAMED = 3


def say_for(key: str, kind: str) -> tuple[str, str]:
    """A measure's two sentences, the rate and the gap: by its name, or else by its kind."""
    return SAY.get(key) or SAY_KIND.get("x" if kind == "xr" else kind, SAY_KIND["x"])


def fill_in(template: str, **parts: str) -> str:
    """A fixed template as an Excel expression: each {name} replaced by its expression, the words between quoted."""
    out, rest = [], template
    while "{" in rest:
        a = rest.index("{")
        b = rest.index("}", a)
        if rest[:a]:
            out.append(live.q(rest[:a]))
        out.append(f"({parts[rest[a + 1:b]]})")
        rest = rest[b + 1:]
    if rest:
        out.append(live.q(rest))
    return "&".join(out) or '""'


def sub(template: str, **parts: str) -> str:
    """A template held in a cell (`template` the cell), its {name}s replaced by SUBSTITUTE."""
    for k, v in parts.items():
        template = f'SUBSTITUTE({template},"{{{k}}}",{v})'
    return template


def write_grids(wb, res, choices: Choices, views: Views) -> None:
    """Grids (section 7): a Grid, a Measure and an "Only loans where" dropdown, four blocks by INDEX and MATCH, and
    how common each group is under them (it absorbs Prevalence)."""
    ws = wb.create_sheet(GRIDS)
    gnames, ms, nr, nc, fit = grid_views(res, views)
    grp = _group_tables(res, views)
    shows = [m for m in res.measures if m.mode == "median"]
    sized = res.book_size is not None and bool(res.book_size.loans)
    sf = res.config.split[0] if res.config.split and res.config.split[1] == "each_value" else None
    w = nc + 1                          # a block: the band column, then the segments
    left, right = 2, 2 + w + 1
    last = right + w - 1
    hid = max(last, left + 18) + 2                         # hidden cells: the keys and the heat's kind and bound
    dw, lw = grid_widths(fit, grp)
    parts, hdr = fit["parts"], (2 if fit["parts"] else 1)   # a split grid's header is two rows (G4)
    # G1, G2, G5: one width for every data column of the four blocks, and one for both label columns
    _widths(ws, {1: 2, **{c: dw for c in range(2, hid)}, left: lw, right: lw, right - 1: 3})
    house.title_band(ws, GRIDS, "One grid at a time: the rate, how it compares, and how many loans sit in each "
                                "pocket.", 2, last, tab=house.TAB_RESULT)
    profit = any(m.name in PROFIT for m in ms)
    few = fewest(res)
    note = [
        ("Rate", "The measure picked above, in every pocket: one band (down) by one segment (across), with the "
                 "band's and the segment's totals in All."),
        ("vs the book", "The pocket's rate over the whole book's, which the heading gives: 2.00× goes bad twice as "
                        "often as the book."
                        + (" Kept after losses and Earned before losses are a gap in points instead." if profit
                           else "")),
        ("vs rest of band", "The pocket's rate over every other loan in its band, so a band that is bad all "
                            "through doesn't make each of its pockets look bad. No rate in its heading: the rest "
                            "of the band is different in every row."),
        ("Colour", "Red is worse, green better, pale in line: 0.5× and under the greenest, 2× and over the "
                   "deepest red; for a gap in points, the largest in the grid is the deepest. A blank: alone in "
                   "its band, or fewer losses than fewest losses on Control, so not compared (a setting for the "
                   "next Run)."
                   + (f" Grey: fewer loans than the {few:,} in Fewest loans in a pocket on Control, so not "
                      f"coloured, and left out of the largest gap." if few is not None else "")),
        ("Loans", "How many loans are in each pocket, shaded by its share of the grid: darker is more. A count, "
                  "not a test, so no red or green."),
    ]
    if sized:
        # said inside Rate, so the note keeps its rows and the dropdowns stay where the bank's checklist says
        note[0] = ("Rate", note[0][1] + " Loan size: booked dollars per loan, the average; against the book's and "
                                        "the rest of the band's average as a multiple. It is a description, not a "
                                        "finding: no red or green, only darker the bigger the loans against the "
                                        "book's.")
    note += [
        ("Only loans where", f"Pick a value of {sf} to see the grid on only its loans. vs the book is still against "
                             f"the whole book; vs rest of band, the rest of the band among those loans."
         if sf else SAY_NO_FILTER),
        ("Groups", "Under the blocks: how many loans" + (", and booked dollars," if res.config.booked else "")
                   + " fall in each group of the split column or a new column, pocket by pocket, for every loan "
                     "in the grid. The count is checked against the grid's before it is shown. Everything on this "
                     "tab is as of the last Run: no line on Control changes it."),
    ]
    r = house.method_note(ws, 3, 2, last, note)
    m_opts = ([plain(m) for m in ms] + ([SIZE_NAME] if sized else [])
              + [f"{'Average' if sm.show == 'average' else 'Median'} {sm.value} per pocket" for sm in shows])
    m_keys = [m.name for m in ms] + ([SIZE] if sized else []) + [f"show_{sm.name}" for sm in shows]
    says = ([say_for(m.name, heat_kind(m)) for m in ms] + ([SAY[SIZE]] if sized else [])
            + [say_for("", "amt") for _ in shows])
    g_rng, _ = choices.add("Grids: Grid", gnames)
    m_rng, (k_rng, rs_rng, gs_rng) = choices.add("Grids: Measure", m_opts, m_keys, [x[0] for x in says],
                                                 [x[1] for x in says])
    f_rng, _ = choices.add("Grids: Only loans where", [ALL_LOANS] + (list(res.split_values) if sf else []))
    s = r + 1
    G = dropdown(ws, s, left, "Grid", g_rng, gnames[0] if gnames else "")
    ws.merge_cells(start_row=s, start_column=left, end_row=s, end_column=left + 2)
    M = dropdown(ws, s, left + 4, "Measure", m_rng, m_opts[0] if m_opts else "")
    ws.merge_cells(start_row=s, start_column=left + 4, end_row=s, end_column=left + 6)
    F = dropdown(ws, s, left + 8, f"Only loans where {sf} is" if sf else "Only loans where", f_rng, ALL_LOANS)
    ws.merge_cells(start_row=s, start_column=left + 8, end_row=s, end_column=left + 10)
    if not sf:
        _cell(ws, s + 1, left + 8, SAY_NO_FILTER, size=9, color=SLATE, h="left")
    # one cell to read out in words (the firm, 29 Sep 2026): a Row and a Column of the grid picked, each list the
    # grid's own labels, laid out in hidden cells as the Grid dropdown changes, and offered as many as there are
    RL, CL, H2 = hid + 7, hid + 8, hid + 9
    RN, CN = f"${col(H2)}${s}", f"${col(H2)}${s + 1}"
    first_row, first_col = _first_pocket(res, ms)
    R = dropdown(ws, s, left + 12, "Row", f"OFFSET(${col(RL)}${s},0,0,MAX(1,{RN}),1)", first_row)
    ws.merge_cells(start_row=s, start_column=left + 12, end_row=s, end_column=left + 14)
    C = dropdown(ws, s, left + 16, "Column", f"OFFSET(${col(CL)}${s},0,0,MAX(1,{CN}),1)", first_col)
    ws.merge_cells(start_row=s, start_column=left + 16, end_row=s, end_column=left + 18)
    # the view: the grid picked, or it on only the loans with the value picked
    VW = f"${col(hid + 1)}${s + 2}"
    ws[VW.replace("$", "")] = f'={G}&IF(OR({F}="",{F}="{ALL_LOANS}"),"",{live.q(WHERE.format(""))}&{F})'
    KEY = f"${col(hid)}${s}"
    ws[f"{col(hid)}{s}"] = f'=IFERROR(INDEX({k_rng},MATCH({M},{m_rng},0)),"")'
    META = f"${col(hid)}${s + 1}"
    ws[f"{col(hid)}{s + 1}"] = "=" + match(xk("G|", (VW,), "|", (KEY,), "|meta"))
    KIND, BOUND = f"${col(hid + 1)}${s}", f"${col(hid + 1)}${s + 1}"
    ws[KIND.replace("$", "")] = f"={pick(META, 1)}"
    ws[BOUND.replace("$", "")] = f"={pick(META, 2)}"
    BOOK, FEW = f"${col(hid + 1)}${s + 3}", f"${col(hid + 1)}${s + 4}"
    ws[BOOK.replace("$", "")] = f"={pick(META, 4)}"
    ws[FEW.replace("$", "")] = f"={pick(META, 5)}"
    COLS, ROWS, NAMES, TOTAL, HEADS, SEGS = (f"${col(hid)}${s + k}" for k in (2, 3, 4, 5, 6, 7))
    for k, what in ((2, "cols"), (3, "rows"), (4, "names"), (5, "total"), (6, "heads"), (7, "segs")):
        ws[f"{col(hid)}{s + k}"] = "=" + match(xk("G|", (VW,), f"|{what}"))
    for c_, labels, n in ((RL, ROWS, nr), (CL, COLS, nc)):         # the grid's own labels, All left off
        for i in range(1, max(n - 1, 1) + 1):
            ws.cell(row=s + i - 1, column=c_, value=f'=IF({pick(labels, i)}="All","",{pick(labels, i)})')
    for cnt, c_, n in ((RN, RL, nr), (CN, CL, nc)):
        ws[cnt.replace("$", "")] = f"=SUMPRODUCT(--(LEN(${col(c_)}${s}:${col(c_)}${s + max(n - 1, 1) - 1})>0))"
    top = s + 2
    # the book's own figure in the heading of vs the book (the firm, 29 Sep 2026), as the Rate block shows it
    book_head = (f'=IF(ISNUMBER({BOOK}),"vs the book (book: "&IF({KIND}="size",TEXT({BOOK},"$#,##0"),'
                 f'TEXT({BOOK},"0.00%"))&")","vs the book")')
    down = nr + 2 + hdr                 # the lower blocks start this far under the upper
    blocks = (("Rate", "rate", left, top, False), ("vs the book", "book", right, top, True),
              ("vs rest of band", "band", left, top + down, True), ("Loans", "loans", right, top + down, False))
    # each block by its column and the row over its data's header, so its header is `t + 1` and its first data
    # row `t + 2` whether the header is one row or two
    at_ = {what: (c0, t + hdr - 1) for _, what, c0, t, _ in blocks}
    lc, lt = at_["loans"]
    # G3: the headers wrap, to two lines when a label needs it, and every block's header rows are the same height
    lower = max(house.lines_at(h, dw - 2) for h in fit["heads"])
    upper = max([house.lines_at(sg, parts * dw - 2) for sg in fit["segs"]] or [1])
    for title, what, c0, t0, heated in blocks:
        _block_head(ws, t0, c0, w, f'="Rate · "&{M}' if what == "rate" else book_head if what == "book" else title)
        t = t0 + hdr - 1
        if hdr == 2:                    # G4: a split grid's segment, merged over its parts
            ws.cell(row=t0 + 1, column=c0).fill = house.fill(CANVAS)
            for j in range(1, nc + 1):
                ws.cell(row=t0 + 1, column=c0 + j).fill = house.fill(CANVAS)
            for k in range(fit["spans"]):
                j0 = 1 + k * parts
                _cell(ws, t0 + 1, c0 + j0, f"={pick(SEGS, k + 1)}", bold=True, size=9, color=SLATE, name="Arial",
                      wrap=True)
                if parts > 1:
                    ws.merge_cells(start_row=t0 + 1, start_column=c0 + j0, end_row=t0 + 1,
                                   end_column=c0 + j0 + parts - 1)
            ws.row_dimensions[t0 + 1].height = HEAD_LINE * upper + 4
        _cell(ws, t + 1, c0, f"={pick(NAMES, 1)}", bold=True, size=9, color=SLATE, h="left", name="Arial", indent=1)
        ws.cell(row=t + 1, column=c0).fill = house.fill(CANVAS)
        for j in range(1, nc + 1):
            hc = _cell(ws, t + 1, c0 + j, f"={pick(HEADS, j)}", bold=True, size=9, color=SLATE, name="Arial",
                       wrap=True)
            hc.fill = house.fill(CANVAS)
        ws.row_dimensions[t + 1].height = HEAD_LINE * lower + 4
        for i in range(1, nr + 1):
            rr = t + 1 + i
            key = xk("G|", (VW,), f"|loans|{i}") if what == "loans" else xk("G|", (VW,), "|", (KEY,), f"|{what}|{i}")
            hcell = f"${col(hid + 2 + (0 if c0 == left else 1))}{rr}"
            ws[hcell.replace("$", "")] = f"={match(key)}"
            _cell(ws, rr, c0, f"={pick(ROWS, i)}", h="left", indent=1)
            for j in range(1, nc + 1):
                _cell(ws, rr, c0 + j, f"={pick(hcell, j)}", fmt="#,##0" if what == "loans" else
                      ("0.00%" if what == "rate" else X_FMT))
            ws.row_dimensions[rr].height = 16
        inner = f"{col(c0 + 1)}{t + 2}:{col(c0 + nc)}{t + 1 + nr}"
        corner = f"{col(c0 + 1)}{t + 2}"
        line_on = f'${col(c0)}{t + 2}<>""'
        cf(ws, f"{col(c0)}{t + 2}:{col(c0)}{t + 1 + nr}", [], line_on)
        rules = []
        if what == "rate":
            rules = [(f'{KIND}="amt"', None, None, "#,##0.00"), (f'{KIND}="size"', None, None, SIZE_FMT)]
        if heated:
            # a cell under the fewest loans: its number in grey, no colour (the firm, 29 Sep 2026); its loans are
            # the Loans block's cell in the same place
            loans_at = f"{col(lc + 1)}{lt + 2}"
            grey = f"AND(ISNUMBER({corner}),ISNUMBER({loans_at}),ISNUMBER({FEW}),{loans_at}<{FEW})"
            dim = Font(color=house.DISABLED_TEXT)
            rules = [(f'AND({grey},{KIND}="pts")', None, dim, PTS_FMT), (grey, None, dim, None)]
            # Loan size: one neutral hue, darker the bigger, never red or green. Every colour also says NOT grey:
            # Excel applies every rule that holds, where LibreOffice stops at the first (see cf)
            rules += [(f'AND(NOT({grey}),{KIND}="size",ISNUMBER({corner}),{corner}>={lim})', colour, None, None)
                      for lim, colour in SIZE_STEPS]
            rules += [(f'AND(NOT({grey}),{KIND}<>"size",{f})', fill, font, fmt)
                      for f, fill, font, fmt in heat_rules(corner, KIND, BOUND, f'{KIND}="pts"', PTS_FMT)]
        if what == "loans":
            margin = f'OR(${col(c0)}{t + 2}="All",{col(c0 + 1)}${t + 1}="All")'
            rules = [(f"AND(ISNUMBER({corner}),NOT({margin}),{corner}/{pick(TOTAL, 1)}>={lim})", colour, None, None)
                     for lim, colour in LOANS_STEPS]
        cf(ws, inner, rules, line_on)
    r = top + 2 * down
    _cell(ws, r, left, "A blank: alone in its band, or fewer losses than the minimum, so not compared.", size=9,
          color=SLATE, h="left")
    r = _one_cell(ws, r + 2, left, last, nr, nc, at_, dict(M=M, R=R, C=C, F=F, sf=sf, KIND=KIND, BOUND=BOUND,
                  META=META, FEW=FEW, VW=VW, KEY=KEY, RN=RN, CN=CN, RL=RL, CL=CL, H=hid + 10, s=s, rs=rs_rng,
                  gs=gs_rng, m=m_rng, COLS=COLS))
    r = _groups(ws, grp, G, r + 2, left, hid + 4, dw)
    _hide(ws, hid, hid + 10)
    ws.freeze_panes = f"A{s + 1}"
    _fit(ws)


def _first_pocket(res, ms) -> tuple[str, str]:
    """The first grid's first pocket with a rate for the first measure: the Row and Column the tab opens on."""
    grids = list(res.grids) + list(res.three_way)
    if not grids:
        return "", ""
    g = grids[0]
    for bl in g.band_labels:
        for d in g.dim_labels:
            c = g.cells.get((bl, d))
            if c is not None and (not ms or c.rates[ms[0].name].rate is not None):
                return bl, _short(res, d)
    return "", ""


def _one_cell(ws, r: int, left: int, last: int, nr: int, nc: int, at_: dict, x: dict) -> int:
    """What one cell says (the firm, 29 Sep 2026): the Row and Column picked, read out in words from the same
    cells the four blocks show, so no number here is worked out again. The sentences are the measure's (SAY,
    held on _choices beside the Measure dropdown's options); a blank says why it is blank, and a grey cell why it
    is grey. Returns the last row."""
    M, R, C, KIND, BOUND, s, H = x["M"], x["R"], x["C"], x["KIND"], x["BOUND"], x["s"], x["H"]
    F, FEW = x["F"], x["FEW"]
    rng = lambda what: (f"${col(at_[what][0] + 1)}${at_[what][1] + 2}:"          # noqa: E731
                        f"${col(at_[what][0] + nc)}${at_[what][1] + 1 + nr}")
    lc, lt = at_["loans"]
    names = ["RI", "CJ", "RV", "BV", "NV", "LV", "MV", "OTH", "OTHN", "RT", "GT", "MIN", "MD", "GR"]
    h = {n: f"${col(H)}${s + k}" for k, n in enumerate(names)}
    RI, CJ, RV, BV, NV, LV, MV, OTH, OTHN, RT, GT, MIN, MD, GR = (h[n] for n in names)
    rl = f"${col(x['RL'])}${s}:${col(x['RL'])}${s + max(nr - 1, 1) - 1}"
    cl = f"${col(x['CL'])}${s}:${col(x['CL'])}${s + max(nc - 1, 1) - 1}"
    none = f'OR({RI}="",{CJ}="")'
    med_row = match(xk("G|", (x["VW"],), "|", (x["KEY"],), "|median|", (RI,)))
    got = {
        RI: f'IF({R}="","",IFERROR(MATCH({R},{rl},0),""))',
        CJ: f'IF({C}="","",IFERROR(MATCH({C},{cl},0),""))',
        RV: f'IF({none},"",INDEX({rng("rate")},{RI},{CJ}))',
        BV: f'IF({none},"",INDEX({rng("book")},{RI},{CJ}))',
        NV: f'IF({none},"",INDEX({rng("band")},{RI},{CJ}))',
        LV: f'IF({none},"",INDEX({rng("loans")},{RI},{CJ}))',
        MV: f'IF({RI}="","",INDEX({rng("loans")},{RI},{x["CN"]}+1))',
        # the other pockets in the row with loans, and their columns' names
        OTH: f'IF({none},"",COUNT(OFFSET(${col(lc + 1)}${lt + 2},{RI}-1,0,1,{x["CN"]}))-IF(ISNUMBER({LV}),1,0))',
        OTHN: "IFERROR(MID(" + "&".join(
            f'IF(AND({j}<>{CJ},{j}<={x["CN"]},ISNUMBER(INDEX({rng("loans")},{RI},{j}))),", "&{pick(x["COLS"], j)},"")'
            for j in range(1, nc + 1)) + ',3,999),"")',
        RT: f'IFERROR(INDEX({x["rs"]},MATCH({M},{x["m"]},0)),"")',
        GT: f'IFERROR(INDEX({x["gs"]},MATCH({M},{x["m"]},0)),"")',
        MIN: f'{pick(x["META"], 3)}',
        # Loan size's median, from its own _views row: the blocks don't show it
        MD: f'IF(OR({none},{KIND}<>"size"),"",{pick(f"({med_row})", CJ)})',
        # under the fewest loans: grey, and no colour (the blocks' rule, the same cells)
        GR: f"AND(ISNUMBER({LV}),ISNUMBER({FEW}),{LV}<{FEW})",
    }
    for cell, f in got.items():
        ws[cell.replace("$", "")] = f"={f}"
    n = f'TEXT({LV},"#,##0")'
    one = f"{LV}=1"

    def gap(v: str, against: str, blank: str) -> str:
        said = sub(GT, x=f'TEXT({v},"0.00")', pts=f'TEXT(ABS({v}),"0.00")', more=f'IF({v}<0,"less","more")',
                   against=against)
        return f'IF(OR({none},NOT(ISNUMBER({LV}))),"",IF(ISNUMBER({v}),{said},IF({KIND}="amt",{GT},{blank})))'

    few = fill_in(SAY_FEW, min=MIN)
    not_ = live.q(SAY_NOT)
    untested = f'OR({KIND}="pts",{KIND}="size")'                # blank for no want of losses
    band_against = (fill_in(SAY_BAND, row=R) + f'&IF(AND({OTH}>=1,{OTH}<={SAY_NAMED})," (the "&{OTHN}&" loans)","")')
    where = (f'IF(OR({F}="",{F}="{ALL_LOANS}"),"",", only loans where {x["sf"]} is "&{F})' if x["sf"] else '""')
    loans_ = f'{n}&IF({one}," loan"," loans")'
    lines = [
        (None, f'IF({none},{live.q(SAY_PICK)},{R}&" · "&{C}&", "&{M}&{where})'),
        ("Rate", f'IF({none},"",IF(NOT(ISNUMBER({LV})),{live.q(SAY_EMPTY)},IF({RV}="",{live.q(SAY_NORATE)},'
                 + sub(RT, these=f'IF({one},"This one loan","These "&{n}&" loans")', their=f'IF({one},"its","their")',
                       r=f'IF({KIND}="amt",TEXT({RV},"#,##0.00"),IF({KIND}="size",TEXT({RV},"$#,##0"),'
                         f'TEXT({RV},"0.00%")))', measure=M, med=f'TEXT({MD},"$#,##0")') + ")))"),
        ("vs the book", gap(BV, live.q(SAY_BOOK), f'IF({untested},{not_},{few})')),
        ("vs rest of band", gap(NV, band_against,
                                f'IF({OTH}<1,{fill_in(SAY_ALONE, row=R)},IF({untested},{not_},{few}))')),
        ("Loans", f'IF(OR({none},NOT(ISNUMBER({LV}))),"",'
                  + fill_in(SAY_LOANS, loans=loans_, row=R, m=f'TEXT({MV},"#,##0")') + ")"),
        ("The colour", f'IF(OR({none},NOT(ISNUMBER({LV}))),"",IF({KIND}="amt","No colour: this figure is not '
                       f'compared.",IF({GR},' + fill_in(SAY_GREY, loans=loans_, min=f'TEXT({FEW},"#,##0")')
                       + f',IF({KIND}="size",{live.q(SAY_SIZE)},'
                       + fill_in(SAY_COLOUR, book=shade_of(BV, KIND, BOUND), band=shade_of(NV, KIND, BOUND)) + "))))"),
    ]
    end = max(last, left + 18)
    _block_head(ws, r, left, end - left + 1, "What one cell says")
    for k, (label, f) in enumerate(lines, start=1):
        rr = r + k
        if label is None:
            ws.merge_cells(start_row=rr, start_column=left, end_row=rr, end_column=end)
            _cell(ws, rr, left, f"={f}", bold=True, h="left", name="Arial", indent=1)
        else:
            _cell(ws, rr, left, label, bold=True, size=9, color=SLATE, h="left", name="Arial", indent=1)
            ws.merge_cells(start_row=rr, start_column=left + 1, end_row=rr, end_column=end)
            _cell(ws, rr, left + 1, f"={f}", h="left", indent=1)
        ws.row_dimensions[rr].height = 18
    return r + len(lines)


def _block_head(ws, r: int, c0: int, w: int, title: str) -> None:
    for c in range(c0, c0 + w):
        x = ws.cell(row=r, column=c)
        x.fill = house.fill(INK)
        x.border = Border(bottom=Side(style="medium", color=house.KEY_RED))
    _cell(ws, r, c0, title, bold=True, color=house.PAPER, h="left", name="Arial", indent=1)
    ws.row_dimensions[r].height = 20


def _group_tables(res, views: Views) -> dict:
    """How common each group is, pocket by pocket, for every grid (the Prevalence tab, absorbed): loans, and booked
    dollars when there is a booked amount, per group of the split column or a new column, put on _views. Nothing
    is tested. Worked out before Grids is laid out, so its headings and numbers enter the tab's one data width
    (G6): what it returns is the tables and what their columns must fit. Booked dollars too long for the widest
    data column show in thousands ($1,234k), never as ####."""
    from . import book as bk
    gs, notes = prevalence.groupings(res)
    out = {"gs": gs, "notes": notes, "tables": [], "heads": set(), "segs": set(), "bands": set(), "values": 0,
           "thousands": False, "dollars": bool(res.config.booked)}
    if not gs and not notes:
        return out
    names = bk._names(res)
    dollars = out["dollars"]
    rows = prevalence.rows_run(res)
    bands = prevalence._labels_by_band(res, rows)
    counts, booked_ = [0], [0.0]
    for gi, grouping in enumerate(gs):
        most, widest = 1, 1
        for g in res.grids:
            gname = f"{names[g.band]} x {names[g.dimension]}"
            if grouping.skip_band is not None and g.band == grouping.skip_band:
                views.put(f"P|{gi}|{gname}|say", [f"Not counted here: this grid is cut by {grouping.column} itself."])
                continue
            got = prevalence.count(res, g, grouping, rows, bands)
            if got is None:
                views.put(f"P|{gi}|{gname}|say", ["Not shown: the count didn't add up to this grid's loans."])
                continue
            order, per, shown = got
            widest = max(widest, len(shown))
            head = ([names[g.band], names[g.dimension], "Loans"] + (["Booked dollars"] if dollars else [])
                    + [x for s in shown for x in ([s, ""] if dollars else [s])])
            views.put(f"P|{gi}|{gname}|head", head)
            out["heads"] |= {str(x) for x in head[1:] if x}
            out["bands"].add(names[g.band])
            k = 0
            totals = {x: [0, 0.0] for x in order}
            for bl in g.band_labels:
                for dl in g.dim_labels:
                    cell = per.get((bl, dl))
                    if cell is None:
                        continue
                    k += 1
                    loans_ = sum(x[0] for x in cell.values())
                    booked = math.fsum(x[1] for x in cell.values())
                    vals = [bl, dl, loans_] + ([booked] if dollars else [])
                    for x in order:
                        v = cell.get(x, [0, 0.0])
                        vals += [v[0], v[1]] if dollars else [v[0]]
                        totals[x][0] += v[0]
                        totals[x][1] += v[1]
                    views.put(f"P|{gi}|{gname}|{k}", vals)
                    out["bands"].add(str(bl))
                    out["segs"].add(str(dl))
            loans_ = sum(x[0] for x in totals.values())
            booked = math.fsum(x[1] for x in totals.values())
            counts.append(loans_)
            booked_.append(booked)
            views.put(f"P|{gi}|{gname}|{k + 1}", ["Every pocket", "", loans_] + ([booked] if dollars else [])
                      + [v for x in order for v in ((totals[x][0], totals[x][1]) if dollars else (totals[x][0],))])
            share = ["Share of the grid", "", None] + ([None] if dollars else [])
            for x in order:
                share += ([totals[x][0] / loans_ if loans_ else None, totals[x][1] / booked if booked else None]
                          if dollars else [totals[x][0] / loans_ if loans_ else None])
            views.put(f"P|{gi}|{gname}|{k + 2}", share)
            most = max(most, k + 2)
        for g in res.three_way:          # a split grid is already cut by the split: its own groups are its pockets
            gname = f"{names[g.band]} x {names[g.dimension]}"
            views.put(f"P|{gi}|{gname}|say", ["Counted on the two-way grids: pick one without the split."])
        out["tables"].append((grouping, most, widest))
    out["bands"] |= {"Every pocket", "Share of the grid"}
    # the largest figure is a grid's whole book: every pocket's loans, and its booked dollars
    top = max(booked_)
    out["thousands"] = dollars and len(f"{top:,.0f}") + 2 > DATA_CAP
    out["values"] = max([len(f"{max(counts):,}"), len("100.0%")]
                        + ([len(f"${top / 1000:,.0f}k") if out["thousands"] else len(f"{top:,.0f}")] if dollars
                           else []))
    return out


#: booked dollars in thousands, when the whole book's would be too long for Grids' data columns (G6)
THOUSANDS_FMT = '"$"#,##0,"k"'


def _groups(ws, grp: dict, G: str, r: int, first: int, hid: int, dw: float) -> int:
    """How common each group is, for the grid picked, from what _group_tables put on _views. The headings wrap to
    the lines they need at the tab's data width. Returns the row after it."""
    if not grp["gs"] and not grp["notes"]:
        return r
    dollars = grp["dollars"]
    step = 2 if dollars else 1
    _block_head(ws, r, first, 8, "How common each group is: a count, not a test")
    r += 1
    for n in grp["notes"]:
        _cell(ws, r, first, n, size=9, color=SLATE, h="left")
        r += 1
    lines = max([house.lines_at(h, dw - 2) for h in grp["heads"]] or [1])
    for gi, (grouping, most, widest) in enumerate(grp["tables"]):
        _cell(ws, r, first, grouping.title, bold=True, h="left", name="Arial")
        r += 1
        width = 2 + step + step * widest
        SAY = f"${col(hid)}${r}"
        ws[SAY.replace("$", "")] = "=" + match(xk(f"P|{gi}|", (G,), "|say"))
        _cell(ws, r, first, f'={pick(SAY, 1)}', size=9, color=SLATE, h="left")
        HEAD = f"${col(hid)}${r + 1}"
        ws[HEAD.replace("$", "")] = "=" + match(xk(f"P|{gi}|", (G,), "|head"))
        for j in range(1, width + 1):
            x = _cell(ws, r + 1, first + j - 1, f"={pick(HEAD, j)}", bold=True, size=9, color=house.PAPER,
                      name="Arial", h="left" if j <= 2 else "center", wrap=True)
            x.fill = house.fill(INK)
        ws.row_dimensions[r + 1].height = HEAD_LINE * lines + 4
        sub = [None, None, None] + ([None] if dollars else []) + ["Loans", "Booked dollars"] * widest if dollars \
            else [None, None, None] + ["Loans"] * widest
        for j, v in enumerate(sub, start=1):
            if v:
                j0 = j - (j - (3 + step)) % step
                x = _cell(ws, r + 2, first + j - 1, f'=IF({pick(HEAD, j0)}="","","{v}")' if j > 2 + step else v,
                          bold=True, size=9, color=SLATE, name="Arial", wrap=True)
                x.fill = house.fill(CANVAS)
            else:
                ws.cell(row=r + 2, column=first + j - 1).fill = house.fill(CANVAS)
        ws.row_dimensions[r + 2].height = HEAD_LINE * max(house.lines_at(v, dw - 2) for v in sub if v) + 4 \
            if any(sub) else None
        t = r + 3
        # booked dollars: the 4th column, then every second one after it
        money = {j for j in range(4, width + 1) if dollars and (j - 4) % 2 == 0}
        for k in range(1, most + 1):
            rr = t + k - 1
            RW = f"${col(hid)}{rr}"
            ws[RW.replace("$", "")] = "=" + match(xk(f"P|{gi}|", (G,), f"|{k}"))
            for j in range(1, width + 1):
                _cell(ws, rr, first + j - 1, f"={pick(RW, j)}", h="left" if j <= 2 else "center",
                      fmt=None if j <= 2 else THOUSANDS_FMT if j in money and grp["thousands"] else "#,##0",
                      indent=1 if j <= 2 else 0)
            ws.row_dimensions[rr].height = 16
        rng = f"{col(first)}{t}:{col(first + width - 1)}{t + most - 1}"
        lab = f"${col(first)}{t}"
        cf(ws, rng, [(f'{lab}="Share of the grid"', CANVAS, Font(bold=True), "0.0%"),
                     (f'{lab}="Every pocket"', CANVAS, Font(bold=True), None)], f'{lab}<>""')
        r = t + most + 1
    return r


# --------------------------------------------------------------------------
# Split


def _value_vs(sf: str, v: str, others: list[str]) -> str:
    """What one value of a category split is set against: "SYS_FLAG Y vs N" with two values, "... vs rest" with
    more."""
    return f"{sf} {v} vs {others[0]}" if len(others) == 1 else f"{sf} {v} vs rest"


def _value_note(res, sf: str, b, dollar_rates: bool, profit: bool) -> list[tuple]:
    """The Split tab's note for a category split: each value against the rest of its pocket. The halves' note
    says the same things of the high half against the low."""
    return [
        ("What it does", f"Inside each pocket the loans are split by their {sf}. Pick a grid and a value: that "
                         f"value's loans are compared with the rest of the pocket (the other value, when there are "
                         f"two), so the band and segment are the same on both sides. {sf} isn't a segment of its "
                         f"own while it splits. At most {engine.SPLIT_MOST_VALUES} values."),
        ("Value vs rest", "The value's rate over the rest's: 2.00× means it goes bad"
                          + (", or loses," if dollar_rates else "") + " twice as often."
                          + (" Kept after losses and Earned before losses are a gap in points instead: +0.30 pts "
                             "means the value keeps 0.30 points more per booked dollar." if profit else "")),
        ("Value vs rest, all", live.text(
            "The value's actual total against what it would be at the rest's rates, added over every pocket, with "
            "its range at ", ('TEXT(confidence,"0%")',), " sure. For Bad loans only, the odds are pooled too "
            "(Mantel-Haenszel), with their p-value (Cochran-Mantel-Haenszel), and Cochran's Q asks whether the gap "
            "is the same size in every pocket.")),
        ("Do the values differ?", "For Bad loans, one test of every value at once, pooled over the grid's pockets "
                                  "(the K-group Mantel-Haenszel test, on one fewer degrees of freedom than there "
                                  "are values). Every pocket counts here, however small, so with two values it can "
                                  "differ a little from the odds' p-value, which uses only pockets above the "
                                  "minimums. Not worked out for the dollar measures: the tool has no test of more "
                                  "than two groups at once for a dollar rate."),
        ("p-value", live.text(
            "The chance of a gap at least this big if the value were no different from the rest. Under ",
            ('TEXT(significance_bar,"0%")',), " counts, and is bold. Bad loans: the gap in standard errors"
            + (f"; a dollar measure: the loans dealt at random inside their pocket, {b.shuffles:,} times"
               if dollar_rates else "")
            + f". The allowance for many tests ({_allowance(b)}) covers every value and pocket of one grid and "
              f"measure, and the summary's p-values across the values; a gap that is not significant is in "
              f"brackets, unshaded. A blank: the value or the rest has fewer loans or losses than the minimums "
              f"({b.min_units:,} loans, {b.min_events:,} losses).", *(BORDER_WORDS if dollar_rates else ()))),
        ("What it holds", f"A grid holds fixed only its band and segment. How closely {sf} moves with a band "
                          f"column isn't worked out for a category, so a gap here may partly be a column the grid "
                          f"doesn't hold fixed. Loans are treated as independent of each other."),
        ("As of", "The numbers are the last Run's. The range, the brackets and the bold follow the confidence on "
                  "Control."),
    ]


def split_p(p: str, se: str) -> str:
    """A split p-value as the tab prints it: the number, or "borderline (p 0.048)" when it is a shuffled one that near
    the bar (stats.borderline). Significance is the whole verdict here: plain against bracketed, bold or not."""
    near = f"ABS({p}-{live.BAR})<={stats.BORDERLINE_SE!r}*{se}"
    return (f'IF(AND(ISNUMBER({p}),ISNUMBER({se})),IF({near},"borderline (p "&{live.p_text(p)}&")",{p}),'
            f'IF({p}="","",{p}))')


def split_said(p: float | None, se: float | None, confidence: float):
    """split_p in Python: the words for a borderline p-value, else the p-value."""
    if p is not None and stats.borderline(p, se, confidence):
        return stats.borderline_words(p, confidence)
    return p

#: Split: the chip saying whether a grid holds the split's partner fixed, beside the Grid dropdown (B:D)
SPLIT_CHIP = 5
#: the shortest a Split data column may be: a p-value can read "under 0.01%", a value that could be luck "(+0.28 pts)"
SPLIT_FLOOR = len("under 0.01%") + 2


def split_widths(res, shown, ms, by_value: bool, left: int, right: int, last: int) -> tuple[dict, int, int]:
    """Split's widths (S1): the two grids' data columns one width, fitted as Grids' are (G1) over their column labels
    and values; both label columns one width (G2) over the band labels and the summary's measure names; each
    summary column at least what its heading (on two lines) and its values need. Returns the widths, and the lines
    the summary's headings and the grids' headers take."""
    z = stats.z_for_confidence(res.config.benchmark.confidence)
    heads = {3: "Pockets", 4: "Worse than the rest in" if by_value else "High half worse in",
             5: "Value vs rest, all" if by_value else "High vs low, all",
             6: f"Range ({res.config.benchmark.confidence:.0%} sure)", 7: "p-value", 8: "As odds",
             9: "p-value, as odds"}
    vals: dict[int, list[str]] = {c: [] for c in heads}
    for _, g, _c, pooled, *_se in shown:
        for m in ms:
            p = pooled.get(m.name, {})
            vals[4].append(f"{p['high_worse']} of {p['pockets']}" if p.get("pockets") else "none big enough")
            if m.in_points and p.get("gap") is not None:
                g0 = p["gap"] * 100
                se = (p["gap_hi"] - p["gap"]) * 100 / z if p.get("gap_hi") is not None else 0
                vals[5].append(_shown(g0, "pts"))
                vals[6].append(f"{g0 - z * se:+.2f} to {g0 + z * se:+.2f} pts")
            elif p.get("ratio") is not None:
                g0 = p["ratio"]
                se = (p["ratio_hi"] - g0) / z if p.get("ratio_hi") else 0
                vals[5].append(_shown(g0, "x"))
                vals[6].append(f"{max(g0 - z * se, 0):.2f}× to {g0 + z * se:.2f}×")
            vals[8].append(_shown(p.get("odds"), "x"))
    vals[7] = vals[9] = ["under 0.01%", "borderline (p 0.048)"]      # the borderline flag's words, too
    cols = [str(d) for _, g, _c, _p, *_se in shown for d in g.dim_labels]
    dw = min(DATA_CAP, max([SPLIT_FLOOR] + [house.two_line_width(c) + 2 for c in cols]))
    lw = house.fit([str(b) for _, g, _c, _p, *_se in shown for b in g.band_labels] + [plain(m) for m in ms]
                   + ["Measure", "(marked missing)"], floor=LABEL_FLOOR, cap=LABEL_CAP, pad=3)
    widths = {c: dw for c in range(2, last + 1)}
    widths[left] = widths[right] = lw
    for c, h in heads.items():
        widths[c] = max(widths[c], house.two_line_width(h) + 2, max((len(v) + 2 for v in vals[c]), default=0))
    sum_lines = max(house.lines_at(h, widths[c] - 2) for c, h in heads.items())
    grid_lines = max([house.lines_at(c, dw - 2) for c in cols] or [1])
    return widths, sum_lines, grid_lines


def write_split(wb, res, choices: Choices, views: Views, stamp: str) -> None:
    """Split (section 8): a Grid dropdown and a chip saying whether it holds the split's partner fixed; the
    summary for every measure; the line on whether the gap is the same in every pocket; and the two grids side
    by side for the measure picked."""
    from . import book as bk
    ws = wb.create_sheet(SPLIT)
    sf, how = res.config.split
    names = bk._names(res)
    b = res.config.benchmark
    by_value = how == "each_value"
    if b is None:
        _widths(ws, {1: 2, 2: 22, 3: 100})
        house.title_band(ws, SPLIT, f"Every pocket split by {sf}.", 2, 3, tab=house.TAB_RESULT)
        house.method_note(ws, 3, 2, 3, [("Where to look", f"The Grids tab shows the split grids (pick one ending / "
                                                          f"{sf}). The comparisons need the Control settings.")])
        return
    ms = rates(res)
    pt = None if by_value else bk._partner(res)
    grids = sorted(res.grids, key=lambda x: bk._holds_fixed(res, x)[1])
    # what the Grid dropdown picks: a grid for the halves; a grid and one value of a category, set against the
    # rest of its pocket (the other value, when there are two)
    shown = []
    for g in grids:
        gname = f"{names[g.band]} x {names[g.dimension]}"
        if not by_value:
            shown.append((gname, g, g.split_compare, g.split_pooled, g.split_se))
            continue
        for v in g.split_parts if len(g.split_parts) > 1 else ():
            others = [x for x in g.split_parts if x != v]
            shown.append((f"{gname} · {_value_vs(sf, v, others)}", g, g.part_compare[v], g.part_pooled[v],
                          g.part_se.get(v, {})))
    gnames = [x[0] for x in shown]
    nb = max((len(g.band_labels) for g in grids), default=1)
    nd = max((len(g.dim_labels) for g in grids), default=1)
    w = nd + 1
    left, right = 2, 2 + w + 1
    last = max(right + w - 1, 9)
    widths, sum_heads, grid_lines = split_widths(res, shown, ms, by_value, left, right, last)
    _widths(ws, {1: 2, **widths})
    house.title_band(ws, SPLIT, f"Every pocket split by each value of {sf}: does one value do worse than the rest "
                                f"of its pocket?" if by_value else
                     f"Every pocket split in two at its own median {sf}: does the high half do worse?",
                     2, last, tab=house.TAB_RESULT)
    dollar_rates, profit = bk._has_dollar_rates(res), bk._has_profit(res)
    r = house.method_note(ws, 3, 2, last, _value_note(res, sf, b, dollar_rates, profit) if by_value else [
        ("What it does", f"Inside each pocket the loans are sorted by {sf} and cut at that pocket's own median. The "
                         f"high half is compared with the low half, so the band and segment are the same on both "
                         f"sides. {sf} isn't cut into bands of its own while it splits."),
        ("High vs low", "The high half's rate over the low half's: 2.00× means the high half goes bad"
                        + (", or loses," if dollar_rates else "") + " twice as often."
                        + (" Kept after losses and Earned before losses are a gap in points instead: +0.30 pts "
                           "means the high half keeps 0.30 points more per booked dollar." if profit else "")),
        ("High vs low, all", live.text(
            "The high halves' actual total against what it would be at their low halves' rates, added over every "
            "pocket, with its range at ", ('TEXT(confidence,"0%")',), " sure. For Bad loans only, the odds are "
            "pooled too (Mantel-Haenszel: a standard way to combine pockets without mixing their loans), with "
            "their p-value (Cochran-Mantel-Haenszel), and Cochran's Q asks whether the gap is the same size in "
            "every pocket.")),
        ("p-value", live.text(
            "The chance of a gap at least this big if the two halves were no different. Under ",
            ('TEXT(significance_bar,"0%")',), " counts, and is bold. Bad loans: the gap in standard errors"
            + (f"; a dollar measure: the loans dealt into the two halves at random inside their pocket, "
               f"{b.shuffles:,} times" if dollar_rates else "")
            + f". The pockets are after the allowance for many tests ({_allowance(b)}, across one grid and one "
              f"measure); a gap that is not significant is in brackets, unshaded. The summary is one pooled test "
              f"per grid and measure, with no allowance. A blank: a half has fewer loans or losses than the "
              f"minimums ({b.min_units:,} loans, {b.min_events:,} losses).", *(BORDER_WORDS if dollar_rates else ()))),
        ("What it holds", (f"A grid holds fixed only its band and segment. {sf} moves with {pt[0]} (correlation "
                           f"{pt[1]:+.2f}), so in a grid that doesn't hold {pt[0]} fixed part of every gap may be "
                           f"{pt[0]}, not {sf}: the chip says which. Grids that hold it fixed come first in the "
                           f"list." if pt else f"A grid holds fixed only its band and segment.")
         + " Loans are treated as independent of each other."),
        ("As of", "The numbers are the last Run's. The range, the brackets and the bold follow the confidence on "
                  "Control."),
    ])
    lines_in_use(ws, r, 2, [(3, 3), (4, 4), (5, 5), (6, 6), (7, 8)],
                 material_at(res),
                 9, last, f"The numbers are from the last Run, {stamp}.")
    # every grid's numbers on _views
    for gname, g, compare, pooled, ses in shown:
        held = bk._holds_partner(res, g) if pt else None
        views.put(f"S|{gname}|chip", [("Holds " if held else "Doesn't hold ") + f"{pt[0]} fixed" if pt else "",
                                      (1 if held else 0) if pt else None,
                                      "" if by_value else bk._holds_fixed(res, g)[0]])
        views.put(f"S|{gname}|rows", list(g.band_labels))
        views.put(f"S|{gname}|cols", [str(d) for d in g.dim_labels])
        z_run = stats.z_for_confidence(b.confidence)
        for i, m in enumerate(ms, start=1):
            p = pooled.get(m.name, {})
            if m.in_points:
                g0 = p.get("gap")
                se = (p["gap_hi"] - p["gap"]) / z_run if p.get("gap_hi") is not None else None
                g0, se = (g0 * 100 if g0 is not None else None), (se * 100 if se is not None else None)
            else:
                g0 = p.get("ratio")
                se = (p["ratio_hi"] - p["ratio"]) / z_run if p.get("ratio_hi") else None
            steady = p.get("steady_p")
            general = g.split_general.get(m.name, {})
            views.put(f"S|{gname}|sum|{i}", [
                plain(m), p.get("pockets", 0),
                f"{p['high_worse']} of {p['pockets']}" if p.get("pockets") else "none big enough",
                g0, se, heat_kind(m), p.get("ratio_p"), p.get("odds"), p.get("odds_p"), steady,
                bk._same_size(m, p, b.confidence) if steady is None else None,
                general.get("p"), general.get("df"), general.get("pockets"), p.get("ratio_se")])
            got = [abs(bk._shown(x[m.name][0], m)) for x in compare.values()
                   if m.name in x and x[m.name][0] is not None]
            views.put(f"S|{gname}|{m.name}|meta", [heat_kind(m), max(got + [0.01])])
            for bi, bl in enumerate(g.band_labels, start=1):
                vs, ps, es = [], [], []
                for d in g.dim_labels:
                    x = compare.get((bl, d), {}).get(m.name)
                    vs.append(bk._shown(x[0], m) if x and x[0] is not None else None)
                    ps.append(x[1] if x else None)
                    es.append(ses.get((bl, d), {}).get(m.name))
                views.put(f"S|{gname}|{m.name}|v|{bi}", vs)
                views.put(f"S|{gname}|{m.name}|p|{bi}", ps)
                # Borderline: each pocket's shuffle standard error, beside its p-value (B2a)
                views.put(f"S|{gname}|{m.name}|se|{bi}", es)
    g_rng, _ = choices.add("Split: Grid", gnames)
    m_rng, (k_rng,) = choices.add("Split: Measure", [plain(m) for m in ms], [m.name for m in ms])
    s = r + 4
    G = dropdown(ws, s, 2, "Grid", g_rng, gnames[0] if gnames else "")
    # the Grid dropdown spans B:D, so a long grid name ("FICO x CHANNEL · SYS_FLAG N vs rest") fits without
    # widening B (S1); the chip beside it, then the grid's note
    ws.merge_cells(start_row=s, start_column=2, end_row=s, end_column=4)
    hid = last + 2
    CHIP = f"${col(hid)}${s}"
    ws[CHIP.replace("$", "")] = "=" + match(xk("S|", (G,), "|chip"))
    _cell(ws, s, SPLIT_CHIP, f"={pick(CHIP, 1)}", bold=True, size=9, h="center", name="Arial")
    ws.merge_cells(start_row=s, start_column=SPLIT_CHIP, end_row=s, end_column=SPLIT_CHIP + 1)
    cf(ws, f"{col(SPLIT_CHIP)}{s}:{col(SPLIT_CHIP + 1)}{s}",
       [(f"{pick(CHIP, 2)}=1", POSITIVE_BG, Font(color=POSITIVE, bold=True), None),
        (f"{pick(CHIP, 2)}=0", ALERT, Font(color=CRIMSON, bold=True), None)])
    ws.merge_cells(start_row=s, start_column=SPLIT_CHIP + 2, end_row=s, end_column=last)
    _cell(ws, s, SPLIT_CHIP + 2, f"={pick(CHIP, 3)}", size=9, color=SLATE, h="left", indent=1)
    # the summary, every measure
    h = s + 2
    z = "NORMSINV(1-(1-confidence)/2)"
    house.header(ws, h, 2, ["Measure", "Pockets", "Worse than the rest in" if by_value else "High half worse in",
                            "Value vs rest, all" if by_value else "High vs low, all",
                            f'="Range ("&TEXT(confidence,"0%")&" sure)"', "p-value", "As odds", "p-value, as odds"],
                 centre_from=1)
    # S1: the summary's headings wrap, to the lines the longest needs at its column's width
    for c in range(2, 10):
        ws.cell(row=h, column=c).alignment = Alignment(horizontal="left" if c == 2 else "center", vertical="center",
                                                       wrap_text=True)
    ws.row_dimensions[h].height = HEAD_LINE * sum_heads + 6
    for i in range(1, len(ms) + 1):
        rr = h + i
        R = f"${col(hid)}{rr}"
        ws[R.replace("$", "")] = "=" + match(xk("S|", (G,), f"|sum|{i}"))
        g0, se, kind = pick(R, 4), pick(R, 5), pick(R, 6)
        rng_x = (f'TEXT(MAX({g0}-{z}*{se},0),"0.00")&"× to "&TEXT({g0}+{z}*{se},"0.00")&"×"')
        rng_p = (f'TEXT({g0}-{z}*{se},"+0.00;-0.00")&" to "&TEXT({g0}+{z}*{se},"+0.00;-0.00")&" pts"')
        vals = [f"={pick(R, 1)}", f"={pick(R, 2)}", f"={pick(R, 3)}", f"={g0}",
                f'=IF(OR({se}="",{g0}=""),"",IF({kind}="pts",{rng_p},{rng_x}))', "=" + split_p(pick(R, 7), pick(R, 15)),
                f"={pick(R, 8)}", f"={pick(R, 9)}"]
        for j, v in enumerate(vals):
            _cell(ws, rr, 2 + j, v, h="left" if j == 0 else "center",
                  fmt={3: X_FMT, 5: P_FMT, 6: X_FMT, 7: P_FMT}.get(j), indent=1 if j == 0 else 0)
        cf(ws, f"E{rr}", heat_rules(f"E{rr}", kind, "1", f'{kind}="pts"', PTS_FMT))
        _rule_row(ws, rr, 2, 9)
    # Same in every pocket? under the table (Cochran's Q, the yes/no outcome only)
    r = h + len(ms) + 1
    # Cochran's Q (A8) runs on the yes/no outcome only: its answer, then the dollar measures said not tested,
    # never left to read as an answer (the final check, F9)
    parts = []
    for i, m in enumerate(ms, start=1):
        if m.name == "outcome_loans":
            R = f"${col(hid)}{h + i}"
            steady, said = pick(R, 10), pick(R, 11)
            parts.append(f'"{plain(m)}: "&IF({steady}="",IF({said}="","not tested",{said}),IF({live.sig(steady)},'
                         f'"bigger in some pockets than others","no sign the gap differs between pockets"))')
    dollars = [plain(m) for m in ms if not engine.yes_no(m)]
    if dollars:
        parts.append(live.q(f"{', '.join(dollars)}: not tested: dollar rate"))
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=last)
    _cell(ws, r, 2, '="Same in every pocket? "&' + '&"; "&'.join(parts or ['""']) + '&"."', size=10, h="left",
          indent=1)
    if by_value:
        # B3: do the values differ at all, every value at once, pooled over the grid's pockets (bad loans only)
        r += 1
        said = []
        for i, m in enumerate(ms, start=1):
            if engine.yes_no(m):
                R = f"${col(hid)}{h + i}"
                gp, df, n = pick(R, 12), pick(R, 13), pick(R, 14)
                said.append(f'"{plain(m)}: "&IF({gp}="","not tested",IF({live.sig(gp)},"yes","no sign they do")'
                            f'&" (p-value "&IF({gp}<0.0001,"under 0.0001",TEXT({gp},"0.0000"))&", on "&{df}&'
                            f'IF({df}=1," degree"," degrees")&" of freedom, "&{n}&" pockets)")')
        if dollars:
            said.append(live.q(f"{', '.join(dollars)}: not tested: dollar rate"))
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=last)
        _cell(ws, r, 2, f'="Do the values of {sf} differ at all? "&' + '&"; "&'.join(said or ['""']) + '&"."',
              size=10, h="left", indent=1)
    r += 2
    # the two grids side by side, for the measure picked
    M = dropdown(ws, r + 1, 2, "Measure", m_rng, plain(ms[0]) if ms else "")
    KEY = f"${col(hid + 1)}${r + 1}"
    ws[KEY.replace("$", "")] = f'=IFERROR(INDEX({k_rng},MATCH({M},{m_rng},0)),"")'
    META = f"${col(hid + 1)}${r + 2}"
    ws[META.replace("$", "")] = "=" + match(xk("S|", (G,), "|", (KEY,), "|meta"))
    KIND, BOUND = f"${col(hid + 2)}${r + 1}", f"${col(hid + 2)}${r + 2}"
    ws[KIND.replace("$", "")] = f"={pick(META, 1)}"
    ws[BOUND.replace("$", "")] = f"={pick(META, 2)}"
    ROWS, COLS = f"${col(hid + 1)}${r + 3}", f"${col(hid + 1)}${r + 4}"
    ws[ROWS.replace("$", "")] = "=" + match(xk("S|", (G,), "|rows"))
    ws[COLS.replace("$", "")] = "=" + match(xk("S|", (G,), "|cols"))
    t = r + 3
    for c0, title, what in ((left, f'={M}&", value vs rest"' if by_value else f'={M}&", high vs low"', "v"),
                            (right, "p-value per pocket", "p")):
        _block_head(ws, t, c0, w, title)
        ws.cell(row=t + 1, column=c0).fill = house.fill(CANVAS)
        for j in range(1, nd + 1):
            x = _cell(ws, t + 1, c0 + j, f"={pick(COLS, j)}", bold=True, size=9, color=SLATE, name="Arial",
                      wrap=True)
            x.fill = house.fill(CANVAS)
        ws.row_dimensions[t + 1].height = HEAD_LINE * grid_lines + 4
        for i in range(1, nb + 1):
            rr = t + 1 + i
            V = f"${col(hid + 3)}{rr}"
            P = f"${col(hid + 4)}{rr}"
            E = f"${col(hid + 5)}{rr}"
            if c0 == left:
                ws[V.replace("$", "")] = "=" + match(xk("S|", (G,), "|", (KEY,), f"|v|{i}"))
                ws[P.replace("$", "")] = "=" + match(xk("S|", (G,), "|", (KEY,), f"|p|{i}"))
                ws[E.replace("$", "")] = "=" + match(xk("S|", (G,), "|", (KEY,), f"|se|{i}"))
            _cell(ws, rr, c0, f"={pick(ROWS, i)}", h="left", indent=1)
            for j in range(1, nd + 1):
                if what == "v":
                    v, p = pick(V, j), pick(P, j)
                    words = f'IF({KIND}="pts","("&TEXT({v},"+0.00;-0.00")&" pts)","("&TEXT({v},"0.00")&"×)")'
                    f = f'=IF({v}="","",IF({live.sig(p)},{v},{words}))'
                    _cell(ws, rr, c0 + j, f, fmt=X_FMT, color=house.INK_TEXT)
                else:
                    _cell(ws, rr, c0 + j, "=" + split_p(pick(P, j), pick(E, j)), fmt=P_FMT)
            ws.row_dimensions[rr].height = 16
        inner = f"{col(c0 + 1)}{t + 2}:{col(c0 + nd)}{t + 1 + nb}"
        corner = f"{col(c0 + 1)}{t + 2}"
        line_on = f'${col(c0)}{t + 2}<>""'
        cf(ws, f"{col(c0)}{t + 2}:{col(c0)}{t + 1 + nb}", [], line_on)
        if what == "v":
            cf(ws, inner, [(f"ISTEXT({corner})", None, Font(color=SLATE), None)]
               + heat_rules(corner, KIND, BOUND, f'{KIND}="pts"', PTS_FMT), line_on)
        else:
            # bold when significant; a borderline p-value prints in words and is bold as its number would be, so
            # one range a column, since the number sits on _views at that column (the firm, 29 Sep 2026: flag it,
            # the verdict stands)
            for j in range(1, nd + 1):
                cj, pj = f"{col(c0 + j)}{t + 2}", pick(f"${col(hid + 4)}{t + 2}", j)
                cf(ws, f"{cj}:{col(c0 + j)}{t + 1 + nb}",
                   [(f"OR({live.sig(cj)},AND(ISTEXT({cj}),{live.sig(pj)}))", None, Font(bold=True), None)], line_on)
    _hide(ws, hid, hid + 5)
    ws.freeze_panes = f"A{s + 1}"
    _fit(ws)


# --------------------------------------------------------------------------


def write(wb, res, stamp: str) -> None:
    """Every result tab this run has, and the hidden sheets they read, each written afresh. The tabs these replace
    in an older workbook are taken off by book._write_results, with every other result tab."""
    for t in TABS + HIDDEN + (CHART,):                  # book._write_results takes off the ones replaced
        if t in wb.sheetnames:
            del wb[t]
    for name in [n for n in wb.defined_names if n.startswith("pk_sel_")]:
        del wb.defined_names[name]
    choices, views = Choices(wb), Views(wb)
    write_pockets(wb, res, choices, stamp)
    have = {m.name for m in res.measures}
    if res.config.benchmark is not None and {"gco_rate", "ranr_rate", "contribution_rate"} <= have:
        # a test of a new variable run without GCO and RANR has nothing to put on it, so there is no tab
        write_pck(wb, res, choices, views, stamp)
    write_grids(wb, res, choices, views)
    if res.config.split:
        write_split(wb, res, choices, views, stamp)
