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
            ("less", "less"): "Safe but idle", ("same", "less"): "Earns less, not from losses"}
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
          name="Calibri", indent=0):
    x = ws.cell(row=r, column=c, value=v)
    x.font = Font(name=name, bold=bold, size=size, color=color)
    x.alignment = Alignment(horizontal=h, vertical="center", indent=indent)
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


def heat_rules(cell: str, kind: str, bound: str, extra: str | None = None, fmt: str | None = None) -> list[tuple]:
    """The heat scale over a block whose measure changes with a dropdown, in the spec's tokens: each step is a rule
    over t, the gap on one scale (log2 of a multiple, so 2x is 1 and 0.5x is -1; a gap in points over the largest
    in the grid), reading `kind` and `bound` from the tab's hidden cells. With `extra` (a formula) each step comes
    twice, first with `fmt` for the cells `extra` holds on (a gap in points: its number format)."""
    t = (f'IFERROR(IF({kind}="pts",-{cell}/{bound},IF({kind}="x",LOG({cell},2),IF({kind}="xr",-LOG({cell},2),0))),0)')
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
            " Under ", ('TEXT(significance_bar,"0%")',), " counts.")),
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


def write_pockets(wb, res, choices: Choices, stamp: str) -> None:
    """The Pockets tab (section 5): three dropdowns over one list."""
    from . import book as bk
    ws = wb.create_sheet(POCKETS)
    lv = live.ensure(wb, res)
    b = res.config.benchmark
    widths = {1: 2, K_NUM: 5, K_BAND: 24, K_SEG: 20, K_HALF: 18, K_LOANS: 9, K_THIS: 11, K_REST: 12, K_GAP: 14,
              K_EX: 22, K_WORSE: 14, K_P: 12, K_MAT: 11, K_CAUGHT: 16, K_HOLDS: 26}
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
                K_EX: f"={at(live.P_DOLLARS, R)}", K_WORSE: f"={lst(L_WORSE)}", K_P: f"={at(live.P_P, R)}",
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
    grey, W = Font(color=SLATE), f"${col(K_WORSE)}{first}"
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
LABELLED = 8              # pockets named on the chart: the first rows, when they have a Together verdict
#: the chart's own cells, on a hidden sheet (Excel leaves out a chart's points in hidden columns): each row's point,
#: x then y, its name when it is read together and that point again, then the dashed lines and the corners
CHART = "_chart"
(H_X, H_Y, H_NAME, H_NX, H_NY) = range(1, 6)


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


def together_formula(g: str, k: str, untested: str) -> str:
    """Together as a formula over the two flags, blank on a row with a side untested."""
    W, B = f'"{engine.WORSE}"', f'"{engine.BETTER}"'
    same = f'OR({g}="{engine.IN_LINE}",{g}="{engine.UNSURE_WORSE}",{g}="{engine.UNSURE_BETTER}")'
    return (f'IF(OR({untested}=1,{untested}=""),"",IF(AND({g}={W},{k}={B}),"{TOGETHER[("more", "more")]}",'
            f'IF(AND({g}={W},{k}={W}),"{TOGETHER[("more", "less")]}",IF(AND({g}={B},{k}={B}),'
            f'"{TOGETHER[("less", "more")]}",IF(AND({g}={B},{k}={W}),"{TOGETHER[("less", "less")]}",'
            f'IF(AND({same},{k}={W}),"{TOGETHER[("same", "less")]}",""))))))')


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
    _widths(ws, {1: 2, C_BAND: 22, C_SEG: 18, C_LOANS: 9, C_PAID: 11, C_PAID_D: 13, C_COST: 11, C_COST_D: 13,
                 C_KEPT: 11, C_KEPT_D: 13, C_TOG: 28, 12: 3})
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
        ("Together", "The two sides read at once. Priced for it: more charge-offs and more kept. Net drain: more "
                     "charge-offs and less kept. Strong: fewer charge-offs and more kept. Safe but idle: fewer "
                     "charge-offs and less kept. Earns less, not from losses: less kept while charge-offs are "
                     "about the same. Blank: nothing to read together."),
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
        pts = lambda prow: f'=IF({at(live.P_GAP, prow)}="","",{at(live.P_GAP, prow)}*100)'         # noqa: E731
        short = lambda prow: f'=IF({at(live.P_DOLLARS, prow)}="","",-{at(live.P_DOLLARS, prow)})'  # noqa: E731
        vals = {C_BAND: f"={pick(V, 1)}", C_SEG: f"={pick(V, 2)}", C_LOANS: f"={pick(V, 3)}",
                C_PAID: pts(RC), C_PAID_D: short(RC), C_COST: f"={at(live.P_GAP, RG)}",
                C_COST_D: f"={at(live.P_DOLLARS, RG)}", C_KEPT: pts(RR), C_KEPT_D: short(RR),
                C_TOG: "=" + together_formula(f"${col(C_H_FG)}{rr}", f"${col(C_H_FR)}{rr}", f"${col(C_H_UN)}{rr}")}
        fmts = {C_LOANS: "#,##0", C_PAID: PTS_FMT, C_PAID_D: "#,##0", C_COST: X_FMT, C_COST_D: "#,##0",
                C_KEPT: PTS_FMT, C_KEPT_D: "#,##0"}
        for c, v in vals.items():
            _cell(ws, rr, c, v, h="left" if c in (C_BAND, C_SEG, C_TOG) else "center", fmt=fmts.get(c),
                  indent=1 if c in (C_BAND, C_SEG, C_TOG) else 0, bold=c == C_TOG)
        ws.row_dimensions[rr].height = 16
        # the chart's own cells: every pocket read, and the ones read together named
        T = f"'{PCK}'!"
        un, cost, kept, tog = (f"{T}${col(c)}${rr}" for c in (C_H_UN, C_COST, C_KEPT, C_TOG))
        hs.cell(row=k, column=H_X, value=f'=IF(OR({un}<>0,{cost}="",{kept}=""),NA(),{cost})')
        hs.cell(row=k, column=H_Y, value=f"=IF(ISNA({col(H_X)}{k}),NA(),{kept})")
        hs.cell(row=k, column=H_NAME, value=f'=IF({tog}="","",{T}${col(C_BAND)}${rr}&" / "&{T}${col(C_SEG)}${rr})')
        hs.cell(row=k, column=H_NX, value=f'=IF({tog}="",NA(),{cost})')
        hs.cell(row=k, column=H_NY, value=f'=IF({tog}="",NA(),{kept})')
    end = first + most - 1
    un = f"${col(C_H_UN)}{first}"
    line_on = f'${col(C_BAND)}{first}<>""'
    for (a, b_), fc in (((C_PAID, C_PAID_D), C_H_FC), ((C_COST, C_COST_D), C_H_FG), ((C_KEPT, C_KEPT_D), C_H_FR)):
        f = f"${col(fc)}{first}"
        cf(ws, f"{col(a)}{first}:{col(b_)}{end}", [(f'AND({un}=0,{f}="{engine.WORSE}")', ALERT, None, None),
                                                   (f'AND({un}=0,{f}="{engine.BETTER}")', POSITIVE_BG, None, None)],
           line_on)
    T = f"${col(C_TOG)}{first}"
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
    chart.x_axis.title = "Charge-offs × the rest (log scale)"
    chart.y_axis.title = "Kept: gap in points"
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
    # the named pockets: the first rows, which are the ones read together at the last Run; a row whose verdict
    # has gone (a line changed on Control) drops its point and its name
    for k in range(min(LABELLED, n)):
        rr = 1 + k
        one = Series(Reference(hs, min_col=H_NY, min_row=rr, max_row=rr),
                     Reference(hs, min_col=H_NX, min_row=rr, max_row=rr))
        one.tx = SeriesLabel(strRef=StrRef(f"'{CHART}'!${col(H_NAME)}${rr}"))
        one.marker.symbol = "circle"
        one.marker.size = 8
        one.marker.graphicalProperties.solidFill = house.KEY_RED
        one.marker.graphicalProperties.line.solidFill = house.KEY_RED
        one.graphicalProperties.line.noFill = True
        one.dLbls = _labels(pos=("r", "t", "b", "l")[k % 4])
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


def grid_views(res, views: Views) -> tuple[list[str], list, int, int]:
    """Every grid's four blocks on _views, two-way and split; returns the grids' names, the measures, and the
    most rows and columns any grid has."""
    from . import book as bk
    names = bk._names(res)
    ms = rates(res)
    shows = [m for m in res.measures if m.mode == "median"]
    untested = (engine.THIN, engine.FEW)
    gnames, most_r, most_c = [], 1, 1
    for g in list(res.grids) + list(res.three_way):
        gname = f"{names[g.band]} x {names[g.dimension]}"
        gnames.append(gname)
        rows_ = g.band_labels + [engine.ALL]
        cols_ = g.dim_labels + [engine.ALL]
        most_r, most_c = max(most_r, len(rows_)), max(most_c, len(cols_))
        views.put(f"G|{gname}|cols", [_short(res, d) if d != engine.ALL else "All" for d in cols_])
        views.put(f"G|{gname}|rows", [bl if bl != engine.ALL else "All" for bl in rows_])
        views.put(f"G|{gname}|names", [names[g.band], names[g.dimension]])
        total = g.cells[(engine.ALL, engine.ALL)].rows
        views.put(f"G|{gname}|total", [total])
        for i, bl in enumerate(rows_, start=1):
            views.put(f"G|{gname}|loans|{i}", [g.cells[(bl, d)].rows if (bl, d) in g.cells else None for d in cols_])
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
                    got += [abs(v) for v in (bv, nv) if isinstance(v, (int, float))]
                views.put(f"G|{gname}|{m.name}|rate|{i}", rate)
                views.put(f"G|{gname}|{m.name}|book|{i}", book)
                views.put(f"G|{gname}|{m.name}|band|{i}", band)
            views.put(f"G|{gname}|{m.name}|meta", [heat_kind(m), max(got + [0.01])])
        for sm in shows:
            key = f"show_{sm.name}"
            for i, bl in enumerate(rows_, start=1):
                vals = []
                for d in cols_:
                    c = g.cells.get((bl, d))
                    med = c.medians.get(sm.name) if c is not None else None
                    vals.append(None if med is None else (med.mean if sm.show == "average" else med.median))
                views.put(f"G|{gname}|{key}|rate|{i}", vals)
            views.put(f"G|{gname}|{key}|meta", ["amt", 1])
    return gnames, ms, most_r, most_c


def write_grids(wb, res, choices: Choices, views: Views) -> None:
    """Grids (section 7): a Grid and a Measure dropdown, four blocks by INDEX and MATCH, and how common each
    group is under them (it absorbs Prevalence)."""
    ws = wb.create_sheet(GRIDS)
    gnames, ms, nr, nc = grid_views(res, views)
    shows = [m for m in res.measures if m.mode == "median"]
    w = nc + 1                          # a block: the band column, then the segments
    left, right = 2, 2 + w + 1
    last = right + w - 1
    _widths(ws, {1: 2, **{c: 11 for c in range(2, last + 1)}, left: 20, right: 20, right - 1: 3})
    house.title_band(ws, GRIDS, "One grid at a time: the rate, how it compares, and how many loans sit in each "
                                "pocket.", 2, last, tab=house.TAB_RESULT)
    profit = any(m.name in PROFIT for m in ms)
    r = house.method_note(ws, 3, 2, last, [
        ("Rate", "The measure picked above, in every pocket: one band (down) by one segment (across), with the "
                 "band's and the segment's totals in All."),
        ("vs the book", "The pocket's rate over the book's: 2.00× goes bad twice as often as the book."
                        + (" Kept after losses and Earned before losses are a gap in points instead." if profit
                           else "")),
        ("vs rest of band", "The pocket's rate over every other loan in its band, so a band that is bad all "
                            "through doesn't make each of its pockets look bad."),
        ("Colour", "Red is worse, green better, pale in line: 0.5× and under the greenest, 2× and over the "
                   "deepest red; for a gap in points, the largest in the grid is the deepest. A blank: fewer "
                   "losses than fewest losses on Control, so not compared (a setting for the next Run)."),
        ("Loans", "How many loans are in each pocket, shaded by its share of the grid: darker is more. A count, "
                  "not a test, so no red or green."),
        ("Groups", "Under the blocks: how many loans" + (", and booked dollars," if res.config.booked else "")
                   + " fall in each group of the split column or a new column, pocket by pocket. The count is "
                     "checked against the grid's before it is shown."),
        ("As of", "Everything here is as of the last Run: no line on Control changes it."),
    ])
    m_opts = [plain(m) for m in ms] + [f"{'Average' if sm.show == 'average' else 'Median'} {sm.value} per pocket"
                                       for sm in shows]
    m_keys = [m.name for m in ms] + [f"show_{sm.name}" for sm in shows]
    g_rng, _ = choices.add("Grids: Grid", gnames)
    m_rng, (k_rng,) = choices.add("Grids: Measure", m_opts, m_keys)
    s = r + 1
    G = dropdown(ws, s, left, "Grid", g_rng, gnames[0] if gnames else "")
    ws.merge_cells(start_row=s, start_column=left, end_row=s, end_column=left + 2)
    M = dropdown(ws, s, left + 4, "Measure", m_rng, m_opts[0] if m_opts else "")
    ws.merge_cells(start_row=s, start_column=left + 4, end_row=s, end_column=left + 6)
    hid = last + 2                                         # hidden cells: the keys and the heat's kind and bound
    KEY = f"${col(hid)}${s}"
    ws[f"{col(hid)}{s}"] = f'=IFERROR(INDEX({k_rng},MATCH({M},{m_rng},0)),"")'
    META = f"${col(hid)}${s + 1}"
    ws[f"{col(hid)}{s + 1}"] = "=" + match(xk("G|", (G,), "|", (KEY,), "|meta"))
    KIND, BOUND = f"${col(hid + 1)}${s}", f"${col(hid + 1)}${s + 1}"
    ws[KIND.replace("$", "")] = f"={pick(META, 1)}"
    ws[BOUND.replace("$", "")] = f"={pick(META, 2)}"
    COLS, ROWS, NAMES, TOTAL = (f"${col(hid)}${s + k}" for k in (2, 3, 4, 5))
    for k, what in ((2, "cols"), (3, "rows"), (4, "names"), (5, "total")):
        ws[f"{col(hid)}{s + k}"] = "=" + match(xk("G|", (G,), f"|{what}"))
    top = s + 2
    blocks = (("Rate", "rate", left, top, False), ("vs the book", "book", right, top, True),
              ("vs rest of band", "band", left, top + nr + 3, True), ("Loans", "loans", right, top + nr + 3, False))
    for title, what, c0, t, heated in blocks:
        _block_head(ws, t, c0, w, f'="Rate · "&{M}' if what == "rate" else title)
        _cell(ws, t + 1, c0, f"={pick(NAMES, 1)}", bold=True, size=9, color=SLATE, h="left", name="Arial", indent=1)
        ws.cell(row=t + 1, column=c0).fill = house.fill(CANVAS)
        for j in range(1, nc + 1):
            hc = _cell(ws, t + 1, c0 + j, f"={pick(COLS, j)}", bold=True, size=9, color=SLATE, name="Arial")
            hc.fill = house.fill(CANVAS)
        for i in range(1, nr + 1):
            rr = t + 1 + i
            key = xk("G|", (G,), f"|loans|{i}") if what == "loans" else xk("G|", (G,), "|", (KEY,), f"|{what}|{i}")
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
            rules = [(f'{KIND}="amt"', None, None, "#,##0.00")]
        if heated:
            rules = heat_rules(corner, KIND, BOUND, f'{KIND}="pts"', PTS_FMT)
        if what == "loans":
            margin = f'OR(${col(c0)}{t + 2}="All",{col(c0 + 1)}${t + 1}="All")'
            rules = [(f"AND(ISNUMBER({corner}),NOT({margin}),{corner}/{pick(TOTAL, 1)}>={lim})", colour, None, None)
                     for lim, colour in LOANS_STEPS]
        cf(ws, inner, rules, line_on)
    r = top + 2 * (nr + 3)
    _cell(ws, r, left, "A blank: fewer losses than the minimum, so not compared.", size=9, color=SLATE, h="left")
    r = _groups(ws, res, views, G, r + 2, left, hid + 4)
    _hide(ws, hid, hid + 6)
    ws.freeze_panes = f"A{s + 1}"
    _fit(ws)


def _block_head(ws, r: int, c0: int, w: int, title: str) -> None:
    for c in range(c0, c0 + w):
        x = ws.cell(row=r, column=c)
        x.fill = house.fill(INK)
        x.border = Border(bottom=Side(style="medium", color=house.KEY_RED))
    _cell(ws, r, c0, title, bold=True, color=house.PAPER, h="left", name="Arial", indent=1)
    ws.row_dimensions[r].height = 20


def _groups(ws, res, views: Views, G: str, r: int, first: int, hid: int) -> int:
    """How common each group is, pocket by pocket, for the grid picked (the Prevalence tab, absorbed): loans, and
    booked dollars when there is a booked amount, per group of the split column or a new column. Nothing is
    tested. Returns the row after it."""
    from . import book as bk
    gs, notes = prevalence.groupings(res)
    if not gs and not notes:
        return r
    names = bk._names(res)
    dollars = bool(res.config.booked)
    step = 2 if dollars else 1
    rows = prevalence.rows_run(res)
    bands = prevalence._labels_by_band(res, rows)
    _block_head(ws, r, first, 8, "How common each group is: a count, not a test")
    r += 1
    for n in notes:
        _cell(ws, r, first, n, size=9, color=SLATE, h="left")
        r += 1
    for gi, grouping in enumerate(gs):
        _cell(ws, r, first, grouping.title, bold=True, h="left", name="Arial")
        r += 1
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
            views.put(f"P|{gi}|{gname}|head", [names[g.band], names[g.dimension], "Loans"]
                      + (["Booked dollars"] if dollars else []) + [x for s in shown for x in ([s, ""] if dollars
                                                                                             else [s])])
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
            loans_ = sum(x[0] for x in totals.values())
            booked = math.fsum(x[1] for x in totals.values())
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
        width = 2 + step + step * widest
        SAY = f"${col(hid)}${r}"
        ws[SAY.replace("$", "")] = "=" + match(xk(f"P|{gi}|", (G,), "|say"))
        _cell(ws, r, first, f'={pick(SAY, 1)}', size=9, color=SLATE, h="left")
        HEAD = f"${col(hid)}${r + 1}"
        ws[HEAD.replace("$", "")] = "=" + match(xk(f"P|{gi}|", (G,), "|head"))
        for j in range(1, width + 1):
            x = _cell(ws, r + 1, first + j - 1, f"={pick(HEAD, j)}", bold=True, size=9, color=house.PAPER,
                      name="Arial", h="left" if j <= 2 else "center")
            x.fill = house.fill(INK)
        sub = [None, None, None] + ([None] if dollars else []) + ["Loans", "Booked dollars"] * widest if dollars \
            else [None, None, None] + ["Loans"] * widest
        for j, v in enumerate(sub, start=1):
            if v:
                j0 = j - (j - (3 + step)) % step
                x = _cell(ws, r + 2, first + j - 1, f'=IF({pick(HEAD, j0)}="","","{v}")' if j > 2 + step else v,
                          bold=True, size=9, color=SLATE, name="Arial")
                x.fill = house.fill(CANVAS)
            else:
                ws.cell(row=r + 2, column=first + j - 1).fill = house.fill(CANVAS)
        t = r + 3
        for k in range(1, most + 1):
            rr = t + k - 1
            RW = f"${col(hid)}{rr}"
            ws[RW.replace("$", "")] = "=" + match(xk(f"P|{gi}|", (G,), f"|{k}"))
            for j in range(1, width + 1):
                _cell(ws, rr, first + j - 1, f"={pick(RW, j)}", h="left" if j <= 2 else "center",
                      fmt=None if j <= 2 else "#,##0", indent=1 if j <= 2 else 0)
            ws.row_dimensions[rr].height = 16
        rng = f"{col(first)}{t}:{col(first + width - 1)}{t + most - 1}"
        lab = f"${col(first)}{t}"
        cf(ws, rng, [(f'{lab}="Share of the grid"', CANVAS, Font(bold=True), "0.0%"),
                     (f'{lab}="Every pocket"', CANVAS, Font(bold=True), None)], f'{lab}<>""')
        r = t + most + 1
    return r


# --------------------------------------------------------------------------
# Split


def write_split(wb, res, choices: Choices, views: Views, stamp: str) -> None:
    """Split (section 8): a Grid dropdown and a chip saying whether it holds the split's partner fixed; the
    summary for every measure; the line on whether the gap is the same in every pocket; and the two grids side
    by side for the measure picked."""
    from . import book as bk
    ws = wb.create_sheet(SPLIT)
    sf, how = res.config.split
    names = bk._names(res)
    b = res.config.benchmark
    if how == "each_value" or b is None:
        _widths(ws, {1: 2, 2: 22, 3: 100})
        house.title_band(ws, SPLIT, f"Every pocket split by each value of {sf}.", 2, 3, tab=house.TAB_RESULT)
        house.method_note(ws, 3, 2, 3, [("Where to look", f"Every pocket split by each value of {sf}: the Grids "
                                                          f"tab shows the split grids (pick one ending / {sf}), "
                                                          f"and Pockets lists every part, tested like any other "
                                                          f"pocket (Pockets: Split by {sf}). {sf} isn't a segment "
                                                          f"of its own while it splits.")])
        return
    ms = rates(res)
    pt = bk._partner(res)
    grids = sorted(res.grids, key=lambda x: bk._holds_fixed(res, x)[1])
    gnames = [f"{names[g.band]} x {names[g.dimension]}" for g in grids]
    nb = max((len(g.band_labels) for g in grids), default=1)
    nd = max((len(g.dim_labels) for g in grids), default=1)
    w = nd + 1
    left, right = 2, 2 + w + 1
    last = max(right + w - 1, 9)
    widths = {c: 12 for c in range(2, last + 1)}
    for c, wd in ((2, 26), (5, 16), (6, 20), (9, 16), (right, 20)):
        widths[c] = max(widths.get(c, 0), wd)
    _widths(ws, {1: 2, **widths})
    house.title_band(ws, SPLIT, f"Every pocket split in two at its own median {sf}: does the high half do worse?",
                     2, last, tab=house.TAB_RESULT)
    dollar_rates, profit = bk._has_dollar_rates(res), bk._has_profit(res)
    r = house.method_note(ws, 3, 2, last, [
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
              f"minimums ({b.min_units:,} loans, {b.min_events:,} losses).")),
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
    for g, gname in zip(grids, gnames):
        held = bk._holds_partner(res, g)
        views.put(f"S|{gname}|chip", [("Holds " if held else "Doesn't hold ") + f"{pt[0]} fixed" if pt else "",
                                      1 if held else 0, bk._holds_fixed(res, g)[0]])
        views.put(f"S|{gname}|rows", list(g.band_labels))
        views.put(f"S|{gname}|cols", [str(d) for d in g.dim_labels])
        z_run = stats.z_for_confidence(b.confidence)
        for i, m in enumerate(ms, start=1):
            p = g.split_pooled.get(m.name, {})
            if m.in_points:
                g0 = p.get("gap")
                se = (p["gap_hi"] - p["gap"]) / z_run if p.get("gap_hi") is not None else None
                g0, se = (g0 * 100 if g0 is not None else None), (se * 100 if se is not None else None)
            else:
                g0 = p.get("ratio")
                se = (p["ratio_hi"] - p["ratio"]) / z_run if p.get("ratio_hi") else None
            steady = p.get("steady_p")
            views.put(f"S|{gname}|sum|{i}", [
                plain(m), p.get("pockets", 0),
                f"{p['high_worse']} of {p['pockets']}" if p.get("pockets") else "none big enough",
                g0, se, heat_kind(m), p.get("ratio_p"), p.get("odds"), p.get("odds_p"), steady,
                bk._same_size(m, p, b.confidence) if steady is None else None])
            got = [abs(bk._shown(x[m.name][0], m)) for x in g.split_compare.values()
                   if m.name in x and x[m.name][0] is not None]
            views.put(f"S|{gname}|{m.name}|meta", [heat_kind(m), max(got + [0.01])])
            for bi, bl in enumerate(g.band_labels, start=1):
                vs, ps = [], []
                for d in g.dim_labels:
                    x = g.split_compare.get((bl, d), {}).get(m.name)
                    vs.append(bk._shown(x[0], m) if x and x[0] is not None else None)
                    ps.append(x[1] if x else None)
                views.put(f"S|{gname}|{m.name}|v|{bi}", vs)
                views.put(f"S|{gname}|{m.name}|p|{bi}", ps)
    g_rng, _ = choices.add("Split: Grid", gnames)
    m_rng, (k_rng,) = choices.add("Split: Measure", [plain(m) for m in ms], [m.name for m in ms])
    s = r + 4
    G = dropdown(ws, s, 2, "Grid", g_rng, gnames[0] if gnames else "")
    hid = last + 2
    CHIP = f"${col(hid)}${s}"
    ws[CHIP.replace("$", "")] = "=" + match(xk("S|", (G,), "|chip"))
    chip = _cell(ws, s, 3, f"={pick(CHIP, 1)}", bold=True, size=9, h="center", name="Arial")
    ws.merge_cells(start_row=s, start_column=3, end_row=s, end_column=4)
    cf(ws, f"C{s}:D{s}", [(f"{pick(CHIP, 2)}=1", POSITIVE_BG, Font(color=POSITIVE, bold=True), None),
                          (f"{pick(CHIP, 2)}=0", ALERT, Font(color=CRIMSON, bold=True), None)])
    del chip
    ws.merge_cells(start_row=s, start_column=5, end_row=s, end_column=last)
    _cell(ws, s, 5, f"={pick(CHIP, 3)}", size=9, color=SLATE, h="left", indent=1)
    # the summary, every measure
    h = s + 2
    z = "NORMSINV(1-(1-confidence)/2)"
    house.header(ws, h, 2, ["Measure", "Pockets", "High half worse in", "High vs low, all",
                            f'="Range ("&TEXT(confidence,"0%")&" sure)"', "p-value", "As odds", "p-value, as odds"],
                 centre_from=1)
    for i in range(1, len(ms) + 1):
        rr = h + i
        R = f"${col(hid)}{rr}"
        ws[R.replace("$", "")] = "=" + match(xk("S|", (G,), f"|sum|{i}"))
        g0, se, kind = pick(R, 4), pick(R, 5), pick(R, 6)
        rng_x = (f'TEXT(MAX({g0}-{z}*{se},0),"0.00")&"× to "&TEXT({g0}+{z}*{se},"0.00")&"×"')
        rng_p = (f'TEXT({g0}-{z}*{se},"+0.00;-0.00")&" to "&TEXT({g0}+{z}*{se},"+0.00;-0.00")&" pts"')
        vals = [f"={pick(R, 1)}", f"={pick(R, 2)}", f"={pick(R, 3)}", f"={g0}",
                f'=IF(OR({se}="",{g0}=""),"",IF({kind}="pts",{rng_p},{rng_x}))', f"={pick(R, 7)}", f"={pick(R, 8)}",
                f"={pick(R, 9)}"]
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
    for c0, title, what in ((left, f'={M}&", high vs low"', "v"), (right, "p-value per pocket", "p")):
        _block_head(ws, t, c0, w, title)
        ws.cell(row=t + 1, column=c0).fill = house.fill(CANVAS)
        for j in range(1, nd + 1):
            x = _cell(ws, t + 1, c0 + j, f"={pick(COLS, j)}", bold=True, size=9, color=SLATE, name="Arial")
            x.fill = house.fill(CANVAS)
        for i in range(1, nb + 1):
            rr = t + 1 + i
            V = f"${col(hid + 3)}{rr}"
            P = f"${col(hid + 4)}{rr}"
            if c0 == left:
                ws[V.replace("$", "")] = "=" + match(xk("S|", (G,), "|", (KEY,), f"|v|{i}"))
                ws[P.replace("$", "")] = "=" + match(xk("S|", (G,), "|", (KEY,), f"|p|{i}"))
            _cell(ws, rr, c0, f"={pick(ROWS, i)}", h="left", indent=1)
            for j in range(1, nd + 1):
                if what == "v":
                    v, p = pick(V, j), pick(P, j)
                    words = f'IF({KIND}="pts","("&TEXT({v},"+0.00;-0.00")&" pts)","("&TEXT({v},"0.00")&"×)")'
                    f = f'=IF({v}="","",IF({live.sig(p)},{v},{words}))'
                    _cell(ws, rr, c0 + j, f, fmt=X_FMT, color=house.INK_TEXT)
                else:
                    _cell(ws, rr, c0 + j, f"={pick(P, j)}", fmt=P_FMT)
            ws.row_dimensions[rr].height = 16
        inner = f"{col(c0 + 1)}{t + 2}:{col(c0 + nd)}{t + 1 + nb}"
        corner = f"{col(c0 + 1)}{t + 2}"
        line_on = f'${col(c0)}{t + 2}<>""'
        cf(ws, f"{col(c0)}{t + 2}:{col(c0)}{t + 1 + nb}", [], line_on)
        if what == "v":
            cf(ws, inner, [(f"ISTEXT({corner})", None, Font(color=SLATE), None)]
               + heat_rules(corner, KIND, BOUND, f'{KIND}="pts"', PTS_FMT), line_on)
        else:
            cf(ws, inner, [(live.sig(corner), None, Font(bold=True), None)], line_on)
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
