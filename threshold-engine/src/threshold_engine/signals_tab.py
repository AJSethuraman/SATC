"""The Signals tab: every public signal found in the October 2026
early-warning work, laid beside the book's own series, compared against
whichever product, measure and source the analyst picks, with the peer
group named under every section that draws on it.

The layout is Claude Design's round 3 (``docs/design/round-3/handoff``,
section "Signals"); the first mock-up the tab was built to is
``docs/early-warning-2026-10/record/signals-mock.html``. Three sheets:

- **Signals** (shown): a grid of 92 px columns (A 16 px, B to U). Rows 1-7
  hold the title, the controls, the pack line and the jump row (a link to
  each section), frozen at B8. Then: where the dollars are (a table, three
  small charts and a Yes/No per product that takes it off the charts), 30+
  incl. nonaccrual for four products, 30+ to charge-off and the gap to peers
  for the picked product (the gap priced, the window test), the pipeline,
  one block per signal (the two lines rescaled and slid, the two raw, the
  fit table with the pick first, the inputs of the rescale as a table) and
  across products.
- **Signals data** (shown, far right): the public series behind the tab,
  one column each, on the book's calendar, with each one's source.
- **Signals workings** (hidden): the formulas. The picked series is looked up
  on Data by its label; each signal's change over a year, its normal (the
  median of the quarters in the window) and its typical yearly move (1.4826
  times the median absolute deviation of its yearly changes, ``scale.py``'s
  rule) are columns; the fit tables are CORREL over the two series' yearly
  changes at every lead from four quarters after to twelve ahead. Every
  series a chart draws has its own column that holds #N/A where there is no
  number, so a chart leaves a gap there instead of drawing a zero.

Everything that depends on the pick, the window, the shift, the pack or the
Yes/No cells is a formula. The pack line is one cell on Peers workings,
read here through the workbook name ``PackLine``. Nothing is rated here; the
tab shows, the analyst decides on Decide.
"""
from __future__ import annotations

import re
from typing import Dict, Sequence, Tuple

from openpyxl.chart import AreaChart, LineChart, Reference
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.data_source import StrRef
from openpyxl.chart.layout import Layout, ManualLayout
from openpyxl.chart.marker import DataPoint, Marker
from openpyxl.chart.series import SeriesLabel
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.xml.functions import Element

from . import keybank_style as K

TITLE, DATA_TITLE, WORK_TITLE = "Signals", "Signals data", "Signals workings"
LEADS = list(range(-4, 13))
WINDOWS = ("All quarters", "Without 2020-23")
FIT_AUTO = "fits best"
OUT_FROM, OUT_TO = "2020Q1", "2023Q4"
YES, NO = "Yes", "No"
PACK = "=PackLine"                     # one cell on Peers workings, a workbook name
F_BODY = Font(name="Calibri", size=11, color=K.INK_TEXT)
F_BOLD = Font(name="Calibri", size=11, bold=True, color=K.INK_TEXT)
F_SMALL = Font(name="Calibri", size=10, color=K.INK_TEXT)
F_SMALL_B = Font(name="Calibri", size=10, bold=True, color=K.INK_TEXT)
F_NOTE = Font(name="Calibri", size=10, color=K.SLATE)
F_LAB = Font(name="Arial", size=9, bold=True, color=K.SLATE)
F_HEAD = Font(name="Arial", size=11, bold=True, color=K.INK)
F_JUMP = Font(name="Calibri", size=10, color=K.KEY_RED, underline="single")
INPUT = PatternFill("solid", fgColor=K.INPUT, bgColor=K.INPUT)
CANVAS = PatternFill("solid", fgColor=K.CANVAS, bgColor=K.CANVAS)
HAIR = Side(style="thin", color=K.MIST)
EDGE = Side(style="thin", color=K.INPUT_EDGE)
RULE = Side(style="thin", color=K.STONE)
RIGHT = Alignment(horizontal="right", vertical="bottom")
LEFT = Alignment(horizontal="left", vertical="bottom")

#: The grid: column A 16 px, then B to U at 92 px. openpyxl writes the file's
#: width, which carries Excel's 5 px of padding: 13.14 shows as 12.43 (92 px).
GRID_PX, LAST_COL = 92, 21
W_A, W_COL = 2.29, 13.14

#: The fixed series every fit table compares against: (product, measure, source) of the book.
FIT_TARGETS = (
    ("Credit card", "Net charge-offs", "Industry (every bank)"),
    ("Credit card", "Net charge-offs", "KeyBank"),
    ("Other consumer", "Net charge-offs", "Industry (every bank)"),
    ("Other consumer", "Net charge-offs", "KeyBank"),
    ("Credit card", "30-89 days past due", "Industry (every bank)"),
    ("Other consumer", "30+ days past due incl. nonaccrual", "KeyBank"),
    ("Mortgage", "90+ days past due incl. nonaccrual", "Industry (every bank)"),
    ("Home equity", "90+ days past due incl. nonaccrual", "Industry (every bank)"),
)
#: The signal sections, in order: (key in Signals data, section title, what it is, kind: level or change,
#: the source kind, the raw chart's number format).
SIGNALS = (
    ("fico_keycorp", "Refreshed FICO", "KeyCorp: share of scored card balances with a refreshed FICO under 660, from its 10-Qs; the peers that cut at 660 beside it on Signals data", "level", "fico", "0.0"),
    ("minpay", "Paying only the minimum", "Share of active card accounts at the large banks whose payment was only the minimum due", "level", "y14", "0.0"),
    ("util90", "Stretched utilization", "Utilization of the most stretched tenth of active card accounts at the large banks (90th percentile)", "level", "y14", "0.0"),
    ("pv660", "Purchase volume by low-score accounts", "Average purchase volume per card account scored under 660 (large banks); the fit reads its change over a year, in %", "level", "y14", "#,##0"),
    ("easing", "Underwriting: banks easing card standards", "Net share of banks reporting easier card standards (Senior Loan Officer Survey); above zero, more banks eased", "change", "survey", "0.0"),
    ("score10", "Underwriting: who got new accounts", "Credit score of the weakest tenth of new card accounts (large banks); lower is looser", "level", "y14", "0"),
    ("ltv90", "Mortgage: equity", "Share of outstanding mortgages owing more than 90% of the home's value (FHFA NMDB, all lenders)", "level", "nmdb", "0.0"),
)
#: How each signal shows on the tab: (head, with units; name in the jump row and the inputs table; columns
#: it takes in the jump row; raw chart's title; source; number format of its normal and yearly move).
SHOWN = {
    "fico_keycorp": ("Refreshed FICO under 660 · KeyCorp, share of scored card balances, %", "Refreshed FICO", 1,
                     "KeyCorp, refreshed FICO under 660, %", "KeyCorp 10-Q and 10-K (SEC EDGAR)", '0.00" %"'),
    "minpay": ("Paying only the minimum · large banks, share of active card accounts, %", "Paying only the minimum", 2,
               "Paying only the minimum, %", "Philadelphia Fed (FR Y-14M)", '0.00" %"'),
    "util90": ("Stretched utilization · large banks, 90th percentile of active card accounts, %", "Utilization", 1,
               "Utilization, 90th percentile, %", "Philadelphia Fed (FR Y-14M)", '0.00" %"'),
    "pv660": ("Purchase volume by low-score accounts · large banks, per card account scored under 660, $", "Purchase volume, low scores", 2,
              "Purchase volume under 660, $", "Philadelphia Fed (FR Y-14M)", '"$"#,##0'),
    "easing": ("Underwriting: banks easing card standards · net share of banks, %", "Banks easing standards", 2,
               "Net share easing, %", "Federal Reserve SLOOS (FRED DRTSCLCC)", '0.00" %"'),
    "score10": ("Underwriting: who got new accounts · large banks, credit score of the weakest tenth of new card accounts", "Origination score", 2,
                "Score, 10th percentile of new accounts", "Philadelphia Fed (FR Y-14M)", "0"),
    "ltv90": ("Mortgage: equity · share of mortgages owing more than 90% of the home's value, %", "Mortgage equity", 2,
              "Owing more than 90% of value, %", "FHFA National Mortgage Database", '0.00" %"'),
}
#: The jump row before and after the signal blocks: (name, columns it takes). With the signals: 20 columns, B to U.
JUMP_HEAD = (("Where the dollars are", 2), ("30+ incl. nonaccrual", 2), ("30+ to charge-off and the gap", 2), ("The pipeline", 1))
JUMP_TAIL = (("Across products", 1),)
PRODUCTS = ("Credit card", "Other consumer", "Home equity", "Mortgage", "Auto")
#: A product's line on the dollar charts.
PRODUCT_COLOR = {"Credit card": K.SIGNAL, "Other consumer": K.KEY_RED, "Home equity": K.INTERNAL, "Mortgage": K.SLATE, "Auto": K.STONE,
                 "All consumer": K.INK, "Credit card + Other consumer": K.MEDIAN}
#: The combined products, drawn dashed beside the five on Across products.
COMBINED = ("All consumer", "Credit card + Other consumer")
DQ30 = "30+ days past due incl. nonaccrual"
DQ90 = "90+ days past due incl. nonaccrual"
DQ_KEY_30 = "30+ incl. nonaccrual"                 # the measure's name on Peers delinquency data
CO = "30+ to charge-off"
#: The pipeline's three measures, in order.
PIPE = (DQ30, DQ90, "Gross charge-offs")
INDUSTRY = "Industry (every bank)"
#: Across products: the measure each product is read on.
XP_MEASURE = "30-89 days past due"

#: Rows of the fixed top of the tab, and of Where the dollars are.
R_LABELS, R_INPUTS, R_PACK, R_JUMP = 4, 5, 6, 7
A_HEAD, A_TH, A_FIRST = 9, 10, 11
A_TOTAL = A_FIRST + len(PRODUCTS)
A_ONLAB, A_ONNAME, A_ON = A_TOTAL + 2, A_TOTAL + 3, A_TOTAL + 4


def _q(s: str) -> str:
    return s.replace('"', '""')


def _sheet(title: str) -> str:
    return "'%s'!" % title.replace("'", "''")


def _slug(p: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-")


def _short(product: str, measure: str, source: str) -> str:
    """A series' name in a fit table: product · measure · source, shortened only where the words repeat."""
    return " · ".join((product, measure.replace(" days past due incl.", " incl."), source.replace(" (every bank)", "")))


def _ln(hex_, w=None, dash=None):
    from .assess_tab import _ln as ln
    return ln(hex_, w, dash)


def _emu(px: float) -> int:
    return int(round(px * 9525))


def _put(ws, ch, col: int, row: int, w: int, h: int, dx: int = 0):
    """A chart w x h px, its top-left corner at the top-left of (col, row): sized
    in pixels, so it keeps its size whatever the row heights under it."""
    ch.anchor = OneCellAnchor(_from=AnchorMarker(col=col - 1, colOff=_emu(dx), row=row - 1, rowOff=0),
                              ext=XDRPositiveSize2D(_emu(w), _emu(h)))
    ws.add_chart(ch)


def _no_auto_title(ch):
    """Excel titles a one-series chart with the series' name unless told not to;
    the title is in the cell above the chart."""
    write = ch._write

    def _write():
        tree = write()
        ns = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
        for p in ("", ns):                       # openpyxl writes the chart's tags with or without the namespace
            c = tree.find(p + "chart")
            if c is not None:
                if c.find(p + "autoTitleDeleted") is None:
                    c.insert(0 if c.find(p + "title") is None else 1, Element(p + "autoTitleDeleted", val="1"))
                break
        return tree
    ch._write = _write
    return ch


def _chart(lines, cats, first, last, fmt, tick, legend=True, grid=False, low=False, y=None, major=None, wide_legend=False):
    """A line chart over rows ``first..last``. ``lines`` are dicts: ws, col,
    name (text) or ref (a cell holding it), color, w, dash, dot (the row index,
    from 0, that carries the last-point marker)."""
    from .assess_tab import _quiet_axes, _text
    ch = LineChart()
    ch.title = None
    ch.varyColors = False                                  # one series: a legend entry per quarter otherwise
    for ln_ in lines:
        ch.add_data(Reference(ln_["ws"], min_col=ln_["col"], min_row=first, max_row=last), titles_from_data=False)
        s_ = ch.series[-1]
        s_.tx = SeriesLabel(strRef=StrRef(f=ln_["ref"])) if ln_.get("ref") else SeriesLabel(v=ln_["name"])
        s_.graphicalProperties.line = _ln(ln_["color"], ln_.get("w", 1.5), ln_.get("dash"))
        s_.smooth = False
        s_.marker.symbol = "none"
        if ln_.get("dot") is not None:
            dp = DataPoint(idx=ln_["dot"], marker=Marker(symbol="circle", size=6))
            dp.marker.graphicalProperties = GraphicalProperties(solidFill=ln_["color"], ln=_ln(ln_["color"], 0.75))
            dp.graphicalProperties = GraphicalProperties(ln=_ln(ln_["color"], ln_.get("w", 1.5), ln_.get("dash")))
            s_.dPt.append(dp)
    ch.set_categories(Reference(cats[0], min_col=cats[1], min_row=first, max_row=last))
    _quiet_axes(ch, tick)
    _finish(ch, fmt, legend, grid, low, y, major, wide_legend)
    return _no_auto_title(ch)


def _finish(ch, fmt, legend, grid, low, y=None, major=None, wide_legend=False):
    from .assess_tab import _square, _text
    _square(ch)                                            # no frame: the grid and the titles above are the frame
    if legend:
        ch.legend.position = "t"
        ch.legend.overlay = False
        ch.legend.txPr = _text(9)
        if wide_legend:
            # five products on two rows across the whole width, the plot under them
            ch.legend.layout = Layout(manualLayout=ManualLayout(xMode="edge", yMode="edge", x=0.0, y=0.0, w=1.0, h=0.2))
            ch.layout = Layout(manualLayout=ManualLayout(layoutTarget="inner", xMode="edge", yMode="edge", x=0.14, y=0.24, w=0.83, h=0.62))
    else:
        ch.legend = None
    if grid:
        ch.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=_ln(K.MIST, 0.5)))
    if low:
        ch.x_axis.tickLblPos = "low"
    if y is not None:
        ch.y_axis.scaling.min, ch.y_axis.scaling.max = y
    if major is not None:
        ch.y_axis.majorUnit = major
        if grid and major > 1:
            # the rescaled chart: a grid line at every yearly move, a label at every second
            ch.y_axis.minorUnit = 1
            ch.y_axis.minorGridlines = ChartLines(spPr=GraphicalProperties(ln=_ln(K.MIST, 0.5)))
    ch.y_axis.number_format = fmt
    ch.y_axis.numFmt.sourceLinked = False
    ch.display_blanks_as = "gap"


def _skip(n: int) -> int:
    """A raw chart's tick-label step: three or four quarters labelled, a multiple of four."""
    return max(4, 4 * -(-n // 16))


def _input(ws, row, c1, c2, value=None, center=False):
    """An input: one cell, its yellow carried across c1..c2 without a merge."""
    for c in range(c1, c2 + 1):
        cell = ws.cell(row, c)
        cell.fill = INPUT
        cell.font = F_BOLD
        cell.border = Border(top=EDGE, bottom=EDGE, left=EDGE if c == c1 else None, right=EDGE if c == c2 else None)
        cell.alignment = Alignment(horizontal="center" if center else "left", vertical="center")
    if value is not None:
        ws.cell(row, c1, value)
    return ws.cell(row, c1)


def layout_rows(n_quarters: int) -> dict:
    return {"first": 2, "last": 1 + n_quarters}


def build(wb, *, labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]], grid: Sequence[str],
          signals: dict, peers: Sequence[dict], include: Dict[str, str], peers_sheet: str,
          data_sheet: str, dq_sheet: str, self_short: str, latest: str) -> dict:
    """Add Signals, Signals data and Signals workings to ``wb`` (which holds
    Data, Peers data and Peers delinquency data). ``signals`` is what
    ``signals_data.load`` returned; ``latest`` the last quarter on the
    calendar. The pack line is the workbook name ``PackLine`` (Peers
    workings); ``peers``, ``include``, ``peers_sheet`` and ``dq_sheet`` are
    kept for the callers and the dollars the peer group sums."""
    R0, R1 = 2, 1 + len(grid)
    N = len(grid)
    F06 = R0 + (grid.index("2006Q1") if "2006Q1" in grid else 0)         # the first row charts draw from
    by_key = {k: (t, u, d) for k, t, u, d in signals["series"]}
    sources = signals["sources"]
    present = {lbl: parts[lbl] for lbl in labels}
    prods = list(dict.fromkeys(parts[lbl][0] for lbl in labels))                  # every product in the book
    DA = _sheet(data_sheet)
    PD = _sheet("Peers data")
    DD = _sheet(dq_sheet)

    # ---------------------------------------------------------------- Signals data
    sd = wb.create_sheet(DATA_TITLE)
    sd.sheet_properties.tabColor = K.TAB_DATA
    sd.cell(1, 1, "Quarter").font = F_LAB
    keys = [k for k, _, _, _ in signals["series"]]
    kcol = {k: 2 + i for i, k in enumerate(keys)}
    for i, q in enumerate(grid):
        sd.cell(R0 + i, 1, q)
    for k, title, unit, d in signals["series"]:
        c = kcol[k]
        sd.cell(1, c, k).font = F_LAB
        for i, q in enumerate(grid):
            if q in d:
                sd.cell(R0 + i, c, d[q])
    # the series, described, to the right of the values
    sc = 2 + len(keys) + 1
    for j, h in enumerate(("Key", "What it is", "Unit", "Quarters")):
        sd.cell(1, sc + j, h).font = F_LAB
    for i, (k, title, unit, d) in enumerate(signals["series"]):
        sd.cell(2 + i, sc, k); sd.cell(2 + i, sc + 1, title); sd.cell(2 + i, sc + 2, unit)
        sd.cell(2 + i, sc + 3, "%d, %s to %s" % (len(d), min(d), max(d)) if d else "none")
    r = 3 + len(signals["series"])
    sd.cell(r, sc, "Sources").font = F_HEAD
    for i, (what, file, sha) in enumerate(sources):
        sd.cell(r + 1 + i, sc, what); sd.cell(r + 1 + i, sc + 1, file); sd.cell(r + 1 + i, sc + 2, sha)
    # the data-tab treatment: header MIST, frozen at B2, the quarters before
    # the first value grouped and hidden; row 1 keeps the keys the workings MATCH
    from . import reference_tabs as RT
    RT.data_layout(sd, 1, R0, R1, 1 + len(keys), None)
    sd.column_dimensions[L(sc + 1)].width = 90
    SDt = _sheet(DATA_TITLE)

    # ---------------------------------------------------------------- Signals: the frame and the controls
    ws = wb.create_sheet(TITLE)
    ws.sheet_properties.tabColor = K.TAB_WORK
    ws.sheet_view.showGridLines = False
    ws.sheet_format.defaultRowHeight = 16.5
    ws.sheet_format.customHeight = True
    ws.column_dimensions["A"].width = W_A
    for c_ in range(2, LAST_COL + 1):
        ws.column_dimensions[L(c_)].width = W_COL
    ws.row_dimensions[1].height = 25.5
    c = ws.cell(1, 2, "Signals · every signal found, beside any series in the book")
    c.font = Font(name="Arial", size=16, bold=True, color=K.INK); c.alignment = Alignment(vertical="bottom")
    c = ws.cell(1, LAST_COL, "Latest quarter %s · nothing on this tab is rated" % latest)
    c.font = Font(name="Arial", size=12, bold=True, color=K.INK); c.alignment = Alignment(horizontal="right", vertical="bottom")
    ws.row_dimensions[2].height = 15
    ws.cell(2, 2, "Pick what to compare against in the yellow cells; every chart and fit table follows.").font = \
        Font(name="Calibri", size=11, color=K.SLATE)
    for c_ in range(2, LAST_COL + 1):
        ws.cell(2, c_).border = Border(bottom=Side(style="medium", color=K.KEY_RED))
    ws.row_dimensions[3].height = 6
    ws.row_dimensions[R_INPUTS].height = 19.5
    products = sorted({p for p, _, _ in present.values()}, key=lambda p: (list(PRODUCTS).index(p) if p in PRODUCTS else 99, p))
    measures = list(dict.fromkeys(m for _, m, _ in present.values()))
    srcs = list(dict.fromkeys(s for _, _, s in present.values()))
    CTRL = (("Compare against: product", 2, 4, "Other consumer"), ("Measure", 5, 8, DQ30), ("Source", 9, 10, self_short),
            ("Shift the signal by", 11, 12, FIT_AUTO), ("Window for the normal", 13, 14, WINDOWS[0]))
    for lab, c1, c2, start in CTRL:
        ws.cell(R_LABELS, c1, lab).font = F_LAB
        _input(ws, R_INPUTS, c1, c2, start)
    lists_at = 2 + len(keys) + 6                                           # on Signals data, out of the way
    for j, items in enumerate((products, measures, srcs)):
        col_ = lists_at + j
        sd.cell(1, col_, ("Products", "Measures", "Sources")[j]).font = F_LAB
        for i, v in enumerate(items):
            sd.cell(2 + i, col_, v)
        dv = DataValidation(type="list", formula1="=%s$%s$2:$%s$%d" % (SDt, L(col_), L(col_), 1 + len(items)), allow_blank=False)
        ws.add_data_validation(dv)
        dv.add("%s%d" % (L(CTRL[j][1]), R_INPUTS))
    dv = DataValidation(type="list", formula1='"%s,0,1,2,3,4,5,6,7,8,9,10,11,12"' % FIT_AUTO, allow_blank=False)
    ws.add_data_validation(dv); dv.add("%s%d" % (L(CTRL[3][1]), R_INPUTS))
    dv = DataValidation(type="list", formula1='"%s"' % ",".join(WINDOWS), allow_blank=False)
    ws.add_data_validation(dv); dv.add("%s%d" % (L(CTRL[4][1]), R_INPUTS))
    SG = _sheet(TITLE)
    # The controls, as every other sheet's formula must name them: a bare $B$5 on
    # the workings would be the workings' own B5 (found the hard way, 18 Oct 2026:
    # a circular reference and an empty picked series).
    P_, M_, S_, SH, WIN = (SG + "$%s$%d" % (L(c1), R_INPUTS) for _, c1, _, _ in CTRL)
    LBL = '%s&" - "&%s&" - "&%s' % (P_, M_, S_)
    PICK_SHORT = '%s&" · "&SUBSTITUTE(%s," days past due incl."," incl.")&" · "&SUBSTITUTE(%s," (every bank)","")' % (P_, M_, S_)
    ws.cell(R_LABELS, 16, "Picked").font = F_LAB
    c = ws.cell(R_INPUTS, 16, '=IF(ISNUMBER(MATCH(%s,%s$1:$1,0)),%s&" · "&%s&" · "&%s,"No such series in the book: pick another")'
                % (LBL, DA, P_, M_, S_))
    c.font = Font(name="Calibri", size=11, color=K.SLATE); c.alignment = LEFT
    ws.cell(R_PACK, 2, PACK).font = F_NOTE
    for c_ in range(2, LAST_COL + 1):
        ws.cell(R_JUMP, c_).border = Border(bottom=HAIR)
    ws.row_dimensions[8].height = 7.5
    # the Yes/No cells under the dollars table, one per product: the dollar charts draw a product only on Yes
    on_cell = {}
    ws.cell(A_ONLAB, 2, "On the charts · Yes or No per product").font = F_LAB
    dv = DataValidation(type="list", formula1='"%s,%s"' % (YES, NO), allow_blank=False)
    ws.add_data_validation(dv)
    for i, p in enumerate(PRODUCTS):
        c = ws.cell(A_ONNAME, 2 + i, p)
        c.font = F_SMALL; c.alignment = Alignment(horizontal="center", vertical="center")
        _input(ws, A_ON, 2 + i, 2 + i, YES, center=True)
        dv.add("%s%d" % (L(2 + i), A_ON))
        on_cell[p] = SG + "$%s$%d" % (L(2 + i), A_ON)
        ws.conditional_formatting.add("%s%d" % (L(2 + i), A_ONNAME),
                                      FormulaRule(formula=['%s$%d="%s"' % (L(2 + i), A_ON, NO)], font=Font(color=K.SLATE)))
    ws.row_dimensions[A_ON].height = 19.5

    # ---------------------------------------------------------------- Signals workings
    wk = wb.create_sheet(WORK_TITLE)
    wk.sheet_state = "hidden"
    WK = _sheet(WORK_TITLE)
    col = {"q": 1}
    nxt = [2]

    def take(name, n=1):
        col[name] = nxt[0]; nxt[0] += n
        return col[name]

    def A(name, r, j=0):
        return "%s%d" % (L(col[name] + j), r)

    def R(name, j=0):
        return "$%s$%d:$%s$%d" % (L(col[name] + j), R0, L(col[name] + j), R1)

    def RW(name, j=0):
        return WK + R(name, j)

    for i, q in enumerate(grid):
        wk.cell(R0 + i, 1, q)
    wk.cell(1, 1, "Quarter")
    QN = lambda r: "$A%d" % r                                                          # noqa: E731
    WQ = "%s$A$%d:$A$%d" % (WK, R0, R1)
    out_window = lambda r: 'AND(%s="%s",%s>="%s",%s<="%s")' % (WIN, WINDOWS[1], QN(r), OUT_FROM, QN(r), OUT_TO)   # noqa: E731

    def series_block(name, value_formula, change: str = "diff"):
        """Columns for one series: value, change over a year, value in the
        window, change in the window, absolute deviation of that change, and
        the standardized value (its z). ``change`` 'diff' or 'pct'."""
        c0 = take(name, 8)
        heads = ("value", "change over a year", "value, in the window", "change, in the window", "deviation of the change", "z",
                 "change, without 2020-23", "value, without 2020-23")
        for j, h in enumerate(heads):
            wk.cell(1, c0 + j, "%s: %s" % (name, h))
        v, ch, vw, cw, dev, z = (L(c0 + j) for j in range(6))
        for r in range(R0, R1 + 1):
            wk.cell(r, c0, value_formula(r))
            if r - 4 >= R0:
                if change == "pct":
                    wk.cell(r, c0 + 1, '=IF(AND(ISNUMBER({v}{r}),ISNUMBER({v}{p}),{v}{p}<>0),100*({v}{r}/{v}{p}-1),"")'.format(v=v, r=r, p=r - 4))
                else:
                    wk.cell(r, c0 + 1, '=IF(AND(ISNUMBER({v}{r}),ISNUMBER({v}{p})),{v}{r}-{v}{p},"")'.format(v=v, r=r, p=r - 4))
            else:
                wk.cell(r, c0 + 1, '=""')
            wk.cell(r, c0 + 2, '=IF(OR({ow},NOT(ISNUMBER({v}{r}))),"",{v}{r})'.format(ow=out_window(r), v=v, r=r))
            wk.cell(r, c0 + 3, '=IF(OR({ow},NOT(ISNUMBER({c}{r}))),"",{c}{r})'.format(ow=out_window(r), c=ch, r=r))
            wk.cell(r, c0 + 4, '=IF(ISNUMBER({cw}{r}),ABS({cw}{r}-MEDIAN({cwr})),"")'.format(cw=cw, r=r, cwr=R(name, 3)))
            wk.cell(r, c0 + 5, '=IF(AND(ISNUMBER({v}{r}),COUNT({vw})>0,MEDIAN({dv})>0),({v}{r}-MEDIAN({vw}))/(1.4826*MEDIAN({dv})),"")'
                    .format(v=v, r=r, vw=R(name, 2), dv=R(name, 4)))
            # the fit table's "without 2020-23" always leaves those quarters out, whatever the window control says
            wk.cell(r, c0 + 6, '=IF(OR(AND({q}>="{a}",{q}<="{b}"),NOT(ISNUMBER({c}{r}))),"",{c}{r})'
                    .format(q=QN(r), a=OUT_FROM, b=OUT_TO, c=ch, r=r))
            wk.cell(r, c0 + 7, '=IF(OR(AND({q}>="{a}",{q}<="{b}"),NOT(ISNUMBER({v}{r}))),"",{v}{r})'
                    .format(q=QN(r), a=OUT_FROM, b=OUT_TO, v=v, r=r))
        return c0

    def drawn(name, of: str, head: str, gate=None, scale=None):
        """A column a chart draws: the number in ``of`` (a column on the
        workings, by A1 letter), #N/A where there is none so the chart leaves
        a gap; ``gate`` a cell that must read Yes; ``scale`` a divisor."""
        c0 = take(name)
        wk.cell(1, c0, head)
        for r in range(R0, R1 + 1):
            x = "%s%d" % (of, r)
            cond = "ISNUMBER(%s)" % x if gate is None else 'AND(%s="%s",ISNUMBER(%s))' % (gate, YES, x)
            wk.cell(r, c0, "=IF(%s,%s,NA())" % (cond, x if scale is None else "%s/%s" % (x, scale)))
        return c0

    def lookup(lbl_formula, r):
        return ('=IFERROR(IF(INDEX({d}${r}:${r},1,MATCH({l},{d}$1:$1,0))="","",INDEX({d}${r}:${r},1,MATCH({l},{d}$1:$1,0))),"")'
                .format(d=DA, r=r, l=lbl_formula))

    # the picked series, looked up on Data by its label
    series_block("picked", lambda r: lookup(LBL, r))
    # the fixed fit targets
    targets = []
    for p, m, s in FIT_TARGETS:
        lbl = " - ".join((p, m, s))
        if lbl not in present:
            continue
        name = "t%d" % len(targets)
        series_block(name, lambda r, lbl=lbl: lookup('"%s"' % _q(lbl), r))
        targets.append((name, _short(p, m, s), lbl))

    # each signal, from Signals data
    def sd_value(key):
        c_ = L(kcol[key])
        return lambda r: '=IF(%s$%s%d="","",%s$%s%d)' % (SDt, c_, r, SDt, c_, r)

    sig_cols = {}
    for key, title, what, kind, panel, fmt in SIGNALS:
        sig_cols[key] = series_block(key, sd_value(key), "pct" if key == "pv660" else "diff")
    # the where-the-dollars-are workings: per product, by the source picked
    for p in PRODUCTS:
        slug = _slug(p)
        c0 = take("dollars_" + slug, 3)
        for j, (k, head) in enumerate((("bal", "balance"), ("gco4", "gross charge-offs, 4q"), ("d30", "30+ incl. nonaccrual"))):
            wk.cell(1, c0 + j, "%s: %s, source picked" % (p, head))
            kb, ind = "keybank_%s_%s" % (slug, k), "industry_%s_%s" % (slug, k)
            kbc = L(kcol[kb]) if kb in kcol else None
            inc = L(kcol[ind]) if ind in kcol else None
            for r in range(R0, R1 + 1):
                if k == "bal":
                    pack = 'SUMIFS({pd}$N:$N,{pd}$A:$A,"{p}",{pd}$D:$D,{q},{pd}$P:$P,TRUE)'.format(pd=PD, p=_q(p), q=QN(r))
                elif k == "gco4":
                    pack = 'SUMIFS({pd}$E:$E,{pd}$A:$A,"{p}",{pd}$D:$D,{q},{pd}$J:$J,TRUE,{pd}$P:$P,TRUE)'.format(pd=PD, p=_q(p), q=QN(r))
                else:
                    pack = 'SUMIFS({dd}$F:$F,{dd}$A:$A,"{p}",{dd}$B:$B,"{m}",{dd}$E:$E,{q},{dd}$O:$O,TRUE)'.format(dd=DD, p=_q(p), m=DQ_KEY_30, q=QN(r))
                kb_v = ('IF({s}$%s%d="","",{s}$%s%d)' % (kbc, r, kbc, r)).format(s=SDt) if kbc else '""'
                in_v = ('IF({s}$%s%d="","",{s}$%s%d)' % (inc, r, inc, r)).format(s=SDt) if inc else '""'
                wk.cell(r, c0 + j, '=IF({src}="{me}",{kb},IF(LEFT({src},10)="Peer group",IF({pk}=0,"",{pk}),IF({src}="{ind_}",{ind},"")))'
                        .format(src=S_, me=_q(self_short), kb=kb_v, pk=pack, ind=in_v, ind_=INDUSTRY))
    # what the dollar charts draw: $m, and only the products set to Yes under the table
    for p in PRODUCTS:
        slug = _slug(p)
        for j, k in enumerate(("bal", "gco4", "d30")):
            drawn("dchart_%s_%s" % (slug, k), L(col["dollars_" + slug] + j), "%s: %s, $m, on the charts" % (p, k), gate=on_cell[p], scale=1000)

    # single cells the tab reads: label in one column, the formula beside it
    take("cells_label"); take("cells_value")
    wk.cell(1, col["cells_label"], "single cells"); wk.cell(1, col["cells_value"], "value")
    cells = {}

    def cell_(key, label, formula):
        r = R0 + len(cells)
        wk.cell(r, col["cells_label"], label)
        wk.cell(r, col["cells_value"], formula)
        cells[key] = "%s$%s$%d" % (WK, L(col["cells_value"]), r)
        return cells[key]

    # each product's key on Signals data (the window test and the dollars), as Python spells it
    take("prod_name"); take("prod_slug")
    wk.cell(1, col["prod_name"], "product"); wk.cell(1, col["prod_slug"], "its key on Signals data")
    for i, p_ in enumerate(prods):
        wk.cell(R0 + i, col["prod_name"], p_); wk.cell(R0 + i, col["prod_slug"], _slug(p_))
    SLUG = lambda p_cell: 'VLOOKUP(%s,%s$%s$%d:$%s$%d,2,FALSE)' % (                       # noqa: E731
        p_cell, WK, L(col["prod_name"]), R0, L(col["prod_slug"]), R0 + len(prods) - 1)
    # 30+ to charge-off and the gap, for the picked product. Read from Signals data, where the build
    # puts every product's (the analyst, 20 Oct 2026: the gap "doesn't change and I would think it
    # should"); without those, from Data, where the book rates it, else credit card.
    pg_src = next((s for s in srcs if s.startswith("Peer group")), "Peer group")
    co_sd = any(k.startswith("co_keybank_") for k in keys)
    co_key = {self_short: "keybank", pg_src: "pack-composite", INDUSTRY: "industry"}
    # Always the picked product: where it has none, the section says so rather than draw another product.
    co_prod = cell_("co_product", "30+ to charge-off: the product drawn", "=%s" % P_)
    if co_sd:
        co_has = cell_("co_has", "30+ to charge-off: the product drawn has it",
                       '=ISNUMBER(MATCH("co_keybank_"&IFERROR(%s,""),%s$1:$1,0))' % (SLUG(P_), SDt))
    else:
        co_has = cell_("co_has", "30+ to charge-off: the product drawn has it",
                       '=ISNUMBER(MATCH(%s&" - %s - %s",%s$1:$1,0))' % (P_, CO, _q(self_short), DA))

    def co_at(src, r):
        """``src``'s 30+ to charge-off for the product drawn, on row ``r`` of the calendar."""
        if co_sd:
            return ('=IFERROR(IF(INDEX({d}${r}:${r},1,MATCH("co_{w}_"&{s},{d}$1:$1,0))="","",'
                    'INDEX({d}${r}:${r},1,MATCH("co_{w}_"&{s},{d}$1:$1,0))),"")'
                    .format(d=SDt, r=r, w=co_key[src], s=SLUG(co_prod)))
        return lookup('%s&" - %s - %s"' % (co_prod, CO, _q(src)), r)

    for nm, src in (("co_kb", self_short), ("co_pg", pg_src), ("co_ind", INDUSTRY)):
        c0 = take(nm)
        wk.cell(1, c0, "%s: %s, the product drawn" % (CO, src))
        for r in range(R0, R1 + 1):
            wk.cell(r, c0, co_at(src, r))
    c0 = take("gap", 3)
    for j, h in enumerate(("gap to peers, points", "gap above zero", "gap below zero")):
        wk.cell(1, c0 + j, h)
    for r in range(R0, R1 + 1):
        a, b = A("co_kb", r), A("co_pg", r)
        wk.cell(r, c0, '=IF(AND(ISNUMBER({a}),ISNUMBER({b})),{a}-{b},"")'.format(a=a, b=b))
        wk.cell(r, c0 + 1, '=IF(ISNUMBER({g}),MAX({g},0),0)'.format(g=A("gap", r)))
        wk.cell(r, c0 + 2, '=IF(ISNUMBER({g}),MIN({g},0),0)'.format(g=A("gap", r)))
    for nm in ("co_kb", "co_pg", "co_ind", "gap"):
        drawn(nm + "_c", L(col[nm]), "%s, drawn" % nm)
    # the gap, priced: at the last quarter with a gap, KeyBank's 30+ dollars in the product drawn
    q_gap = cell_("q_gap", "last quarter with a gap", '=IFERROR(LOOKUP(2,1/ISNUMBER(%s),%s),"")' % (RW("gap"), WQ))
    gap_at = cell_("gap_at", "gap at that quarter, points", '=IFERROR(INDEX(%s,MATCH(%s,%s,0)),"")' % (RW("gap"), q_gap, WQ))
    last_sd = L(sc - 2)
    d30_at = cell_("d30_at", "KeyBank 30+ incl. nonaccrual at that quarter, the product drawn ($000)",
                   '=IFERROR(INDEX(%s$A$1:$%s$%d,MATCH(%s,%s$A$1:$A$%d,0),MATCH("keybank_"&%s&"_d30",%s$1:$1,0)),"")'
                   % (SDt, last_sd, R1, q_gap, SDt, R1, SLUG(co_prod), SDt))
    cell_("priced", "the gap priced ($000): gap / 100 x KeyBank's 30+ dollars",
          '=IF(AND(ISNUMBER(%s),ISNUMBER(%s)),%s/100*%s,"")' % (gap_at, d30_at, gap_at, d30_at))
    # the pipeline, for the picked product where KeyBank has 30+ incl. nonaccrual, else credit card:
    # each measure and source looked up on Data by its label, so the charts follow the pick
    pipe_prod = cell_("pipe_product", "the pipeline: the product drawn", "=%s" % P_)
    pipe_has = cell_("pipe_has", "the pipeline: the product drawn has 30+ incl. nonaccrual",
                     '=ISNUMBER(MATCH(%s&" - %s - %s",%s$1:$1,0))' % (P_, DQ30, _q(self_short), DA))
    for j, m in enumerate(PIPE):
        for s in (INDUSTRY, pg_src, self_short):
            nm = "pipe%d_%s" % (j, _slug(s))
            c0 = take(nm)
            wk.cell(1, c0, "the pipeline: %s, %s, the product drawn" % (m, s))
            for r in range(R0, R1 + 1):
                wk.cell(r, c0, lookup('%s&" - %s - %s"' % (pipe_prod, m, _q(s)), r))
            drawn(nm + "_c", L(c0), "the pipeline: %s, %s, drawn" % (m, s))
    # the window test: the last quarter every window has a rate
    # for the product drawn above (30+ to charge-off); its industry windows found on Signals data by key
    SD_LAST = L(1 + len(keys))
    win_at = lambda n_, q_: ('IFERROR(INDEX(%s$A$1:$%s$%d,MATCH(%s,%s$A$1:$A$%d,0),MATCH("win%d_"&%s,%s$1:$1,0)),"")'   # noqa: E731
                             % (SDt, SD_LAST, R1, q_, SDt, R1, n_, SLUG(co_prod), SDt))
    if any(k.startswith("win") for k in keys):
        cell_("q_win", "window test: last quarter with all three windows, the product drawn",
              '=IFERROR(LOOKUP(2,1/ISNUMBER(INDEX(%s$B$%d:$%s$%d,0,MATCH("win3_"&%s,%s$B$1:$%s$1,0))),%s$A$%d:$A$%d),"")'
              % (SDt, R0, SD_LAST, R1, SLUG(co_prod), SDt, SD_LAST, SDt, R0, R1))

    # shifted z per signal: the signal's z moved k quarters later, k from the shift cell or the best fit
    shift_cells, best_cells = {}, {}
    for key, *_ in SIGNALS:
        c0 = take(key + "_zs", 1)
        wk.cell(1, c0, "%s: z, slid" % key)
    # fit grids: per signal, 17 leads x targets (+ the picked), all quarters and without 2020-23
    FIT0 = R1 + 4
    fit_at = {}
    tcols = [(name, nice, lbl) for name, nice, lbl in targets] + [("picked", "the picked series", None)]
    for si, (key, title, what, kind, panel, fmt) in enumerate(SIGNALS):
        top = FIT0 + si * (len(LEADS) + 4)
        fit_at[key] = top
        wk.cell(top, 1, "%s: fit by lead, all quarters" % key).font = F_LAB
        wk.cell(top, 2 + len(tcols) + 1, "%s: fit by lead, without 2020-23" % key).font = F_LAB
        for j, (tname, nice, lbl) in enumerate(tcols):
            wk.cell(top + 1, 2 + j, nice); wk.cell(top + 1, 2 + len(tcols) + 2 + j, nice)
        for i, k in enumerate(LEADS):
            r = top + 2 + i
            wk.cell(r, 1, k)
            n = N - abs(k)
            s_off, t_off = max(0, -k), max(0, k)
            for j, (tname, nice, lbl) in enumerate(tcols):
                # a level signal's fit reads its change over a year; a change signal (the survey) its value; the
                # "without 2020-23" fit reads the columns that always leave those quarters out (Codex on #457)
                for g, (sj, tj) in enumerate(((1 if kind == "level" else 0, 1), (6 if kind == "level" else 7, 6))):
                    sig_first = "%s$%s$%d" % (WK, L(col[key] + sj), R0)
                    tgt_first = "%s$%s$%d" % (WK, L(col[tname] + tj), R0)
                    f = '=IFERROR(CORREL(OFFSET(%s,%d,0,%d,1),OFFSET(%s,%d,0,%d,1)),"")' % (sig_first, s_off, n, tgt_first, t_off, n)
                    wk.cell(r, 2 + j + g * (len(tcols) + 2), f)
        # the best lead per target (all quarters), and the shift this signal uses
        rb = top + 2 + len(LEADS)
        wk.cell(rb, 1, "best lead")
        for j in range(len(tcols)):
            rng = "$%s$%d:$%s$%d" % (L(2 + j), top + 2, L(2 + j), top + 1 + len(LEADS))
            wk.cell(rb, 2 + j, '=IFERROR(INDEX($A$%d:$A$%d,MATCH(MAX(%s),%s,0)),"")' % (top + 2, top + 1 + len(LEADS), rng, rng))
            wk.cell(rb, 2 + j + len(tcols) + 2, '=IFERROR(INDEX(%s,MATCH(%s,$A$%d:$A$%d,0)),"")'
                    % ("$%s$%d:$%s$%d" % (L(2 + j + len(tcols) + 2), top + 2, L(2 + j + len(tcols) + 2), top + 1 + len(LEADS)),
                       "%s%d" % (L(2 + j), rb), top + 2, top + 1 + len(LEADS)))
        # the shift used: typed, or the best lead against the picked series, never below zero
        sh = "%s$%s$%d" % (WK, L(2 + len(tcols) - 1), rb)
        wk.cell(rb + 1, 1, "shift used")
        wk.cell(rb + 1, 2, '=IF(ISNUMBER(%s),%s,IF(ISNUMBER(%s),MAX(0,%s),0))' % (SH, SH, sh, sh))
        shift_cells[key] = "%s$B$%d" % (WK, rb + 1)
        best_cells[key] = sh
        zc = col[key + "_zs"]
        for r in range(R0, R1 + 1):
            wk.cell(r, zc, '=IFERROR(IF(INDEX(%s,%d-%s)="","",INDEX(%s,%d-%s)),"")'
                    % (RW(key, 5), r - R0 + 1, shift_cells[key], RW(key, 5), r - R0 + 1, shift_cells[key]))
    # across products: each product's industry 30-89 days past due against the picked series, as a
    # signal is (the analyst, 20 Oct 2026, on three fixed charts: "Why in the world is it literally just
    # three graphs that don't change")
    xprods = [p_ for p_ in PRODUCTS + COMBINED if " - ".join((p_, XP_MEASURE, INDUSTRY)) in present]
    for p_ in xprods:
        series_block("xp_" + _slug(p_), lambda r, l_=" - ".join((p_, XP_MEASURE, INDUSTRY)): lookup('"%s"' % _q(l_), r))
    XF0 = FIT0 + len(SIGNALS) * (len(LEADS) + 4)
    wk.cell(XF0, 1, "across products: fit by lead against the picked series, all quarters and without 2020-23").font = F_LAB
    xfit = {}
    for i, p_ in enumerate(xprods):
        ca, cx = 2 + 2 * i, 3 + 2 * i
        wk.cell(XF0 + 1, ca, "%s, all quarters" % p_); wk.cell(XF0 + 1, cx, "%s, without 2020-23" % p_)
        for li, k in enumerate(LEADS):
            r = XF0 + 2 + li
            wk.cell(r, 1, k)
            n = N - abs(k)
            s_off, t_off = max(0, -k), max(0, k)
            for c_, j_ in ((ca, 1), (cx, 6)):
                sig_first = "%s$%s$%d" % (WK, L(col["xp_" + _slug(p_)] + j_), R0)
                tgt_first = "%s$%s$%d" % (WK, L(col["picked"] + j_), R0)
                wk.cell(r, c_, '=IFERROR(CORREL(OFFSET(%s,%d,0,%d,1),OFFSET(%s,%d,0,%d,1)),"")'
                        % (sig_first, s_off, n, tgt_first, t_off, n))
        xfit[p_] = ("%s$%s$%d:$%s$%d" % (WK, L(ca), XF0 + 2, L(ca), XF0 + 1 + len(LEADS)),
                    "%s$%s$%d:$%s$%d" % (WK, L(cx), XF0 + 2, L(cx), XF0 + 1 + len(LEADS)))
    XLEADS = "%s$A$%d:$A$%d" % (WK, XF0 + 2, XF0 + 1 + len(LEADS))
    # what the signal blocks draw: each line with #N/A for no number, and the overlay's two names
    drawn("picked_c", L(col["picked"]), "picked: value, drawn")
    drawn("picked_zc", L(col["picked"] + 5), "picked: z, drawn")
    picked_name = cell_("picked_name", "the picked series, its name on the charts", "=%s" % PICK_SHORT)
    names = {}
    for key, *_ in SIGNALS:
        drawn(key + "_c", L(col[key]), "%s: value, drawn" % key)
        drawn(key + "_zsc", L(col[key + "_zs"]), "%s: z, slid, drawn" % key)
        # On fits best, a best lead below zero is not used; the name says so and gives the lead.
        nm, sc_, b_ = _q(SHOWN[key][1]), shift_cells[key], best_cells[key]
        names[key] = cell_(key + "_name", "%s: its name on the overlay" % key,
                           '=IF(AND(NOT(ISNUMBER({SH})),ISNUMBER({b}),N({b})<0),'
                           '"{n}, not shifted: fits best at lead "&{b},'
                           '"{n}, shifted "&{s}&IF({s}=1," quarter"," quarters"))'.format(SH=SH, b=b_, n=nm, s=sc_))

    # ---------------------------------------------------------------- Signals: the sections
    jumps = []                                                            # (name, columns, row)
    cats = (wk, 1)

    def head(row, label, jump, span, right=None):
        K.quiet_section(ws, row, label, LAST_COL - 1, first_col=2)
        if right:
            c_ = ws.cell(row, LAST_COL, right)
            c_.font = F_NOTE; c_.alignment = Alignment(horizontal="right", vertical="bottom")
        jumps.append((jump, span, row))

    def title(row, col_, text):
        c_ = ws.cell(row, col_, text)
        c_.font = F_LAB; c_.alignment = Alignment(vertical="bottom")

    def num(row, col_, formula, fmt, font=F_SMALL):
        c_ = ws.cell(row, col_, formula)
        c_.number_format = fmt; c_.font = font; c_.alignment = RIGHT
        return c_

    def rule(row, c1, c2, side=RULE):
        for c_ in range(c1, c2 + 1):
            ws.cell(row, c_).border = Border(bottom=side)

    def spacer(row):
        ws.row_dimensions[row].height = 9

    data_ws = wb[data_sheet]
    head_ = {data_ws.cell(1, c_).value: c_ for c_ in range(1, data_ws.max_column + 1)}

    def last_idx(lbl, first):
        """The row index, from ``first``, of a Data series' last number: its last point carries the marker."""
        c_ = head_.get(lbl)
        if c_ is None:
            return None
        rows_ = [r for r in range(first, R1 + 1) if isinstance(data_ws.cell(r, c_).value, (int, float))]
        return rows_[-1] - first if rows_ else None

    def style(s):
        if s == self_short:
            return {"color": K.KEY_RED, "w": 2.25}
        if s.startswith("Peer group"):
            return {"color": K.INK, "w": 1.5}
        return {"color": K.SLATE, "w": 1.5, "dash": "dash"}

    def three(p, m, first):
        """Industry, peer group and KeyBank for one product and measure, from Data, KeyBank drawn last."""
        out = []
        for s in (INDUSTRY, pg_src, self_short):
            lbl = " - ".join((p, m, s))
            if lbl in head_:
                out.append(dict(ws=data_ws, col=head_[lbl], name=s, dot=last_idx(lbl, first) if s == self_short else None, **style(s)))
        return out

    # A. where the dollars are
    head(A_HEAD, '="Where the dollars are · "&%s&", %s"' % (S_, latest), "Where the dollars are", 2)
    NOD = 'NOT(OR({s}="{me}",LEFT({s},10)="Peer group",{s}="{ind}"))'.format(s=S_, me=_q(self_short), ind=INDUSTRY)
    ws.row_dimensions[A_TH].height = 39
    for c_, h in ((2, "Product"), (4, "Balance ($000)"), (5, "Share"), (6, "Gross charge-offs, 4 quarters ($000)"), (7, "Share"),
                  (8, "30+ incl. nonaccrual ($000)"), (9, "Share")):
        cell = ws.cell(A_TH, c_, h)
        cell.font = F_LAB
        cell.alignment = Alignment(horizontal="left" if c_ == 2 else "right", vertical="bottom", wrap_text=True)
    rule(A_TH, 2, 9)
    rl = R1                                                                # the latest quarter's row on the workings
    tot = {k: "SUM(%s)" % ",".join("%s%s%d" % (WK, L(col["dollars_" + _slug(p)] + j), rl) for p in PRODUCTS)
           for j, k in enumerate(("bal", "gco4", "d30"))}
    for i, p in enumerate(PRODUCTS):
        r = A_FIRST + i
        ws.row_dimensions[r].height = 15
        ws.cell(r, 2, p).font = F_BODY
        cp = col["dollars_" + _slug(p)]
        for j, k in enumerate(("bal", "gco4", "d30")):
            v = "%s%s%d" % (WK, L(cp + j), rl)
            num(r, 4 + 2 * j, '=IF(%s,"—",IF(%s="","",%s))' % (NOD, v, v), "#,##0", F_BODY)
            num(r, 5 + 2 * j, '=IF(%s,"—",IF(OR(%s="",%s=0),"",%s/%s))' % (NOD, v, tot[k], v, tot[k]), "0%",
                Font(name="Calibri", size=11, color=K.SLATE))
    ws.cell(A_TOTAL, 2, "Consumer, %s" % latest).font = F_BOLD
    for j, k in enumerate(("bal", "gco4", "d30")):
        num(A_TOTAL, 4 + 2 * j, '=IF(%s,"—",%s)' % (NOD, tot[k]), "#,##0", F_BOLD)
    for c_ in range(2, 10):
        ws.cell(A_TOTAL, c_).border = Border(top=Side(style="thin", color=K.INK))
    spacer(A_TOTAL + 1)
    for j, (k, ttl) in enumerate((("bal", "Balances by product, $m"), ("gco4", "Gross charge-offs by product, 4 quarters, $m"),
                                  ("d30", "30+ incl. nonaccrual by product, $m"))):
        lines = [dict(ws=wk, col=col["dchart_%s_%s" % (_slug(p), k)], name=p, color=PRODUCT_COLOR[p], w=1.5) for p in PRODUCTS]
        title(A_TH, 10 + 4 * j, ttl)
        _put(ws, _chart(lines, cats, F06, R1, "#,##0", 16, low=True, wide_legend=True), 10 + 4 * j, A_FIRST, 4 * GRID_PX - 16, 200, dx=8)
    row = A_ON + 1
    spacer(row)
    row += 1

    # B. 30+ incl. nonaccrual, every product
    head(row, "30+ days past due incl. nonaccrual, every product · quarter-end, %", "30+ incl. nonaccrual", 2)
    ws.row_dimensions[row + 1].height = 15
    # every product, five across on the 20-column grid (Auto was missing: "every product" said otherwise)
    for i, p in enumerate(("Credit card", "Other consumer", "Mortgage", "Home equity", "Auto")):
        title(row + 1, 2 + 4 * i, "%s · 30+ incl. nonaccrual, %%" % p)
        _put(ws, _chart(three(p, DQ30, F06), (data_ws, 1), F06, R1, "0.0", 16), 2 + 4 * i, row + 2, 4 * GRID_PX - 8, 220)
    ws.cell(row + 12, 2, PACK).font = F_NOTE
    spacer(row + 13)
    row += 14

    # C. 30+ to charge-off and the gap, for the product drawn
    head(row, '="30+ to charge-off, and the gap to peers · "&%s&IF(%s,""," · none for this product in this workbook")'
         % (co_prod, co_has), "30+ to charge-off and the gap", 2)
    ws.row_dimensions[row + 1].height = 15
    title(row + 1, 2, "Of the dollars 30+ incl. nonaccrual at quarter-end, the share charged off over the next two quarters, %")
    title(row + 1, 12, "KeyBank minus the peer group, points · shaded above zero (worse) and below (better)")
    d_kb = [last_idx(" - ".join((p_, CO, self_short)), F06) for p_ in {"Credit card", "Other consumer"}]
    dot = d_kb[0] if len(set(d_kb)) == 1 else None                       # the same last quarter whichever product is drawn
    # a rate counts the charge-offs of the next two quarters, so the last two quarters have none: the charts stop before them
    RC = R1 - 2
    lines = [dict(ws=wk, col=col["co_ind_c"], name=INDUSTRY, **style(INDUSTRY)), dict(ws=wk, col=col["co_pg_c"], name=pg_src, **style(pg_src)),
             dict(ws=wk, col=col["co_kb_c"], name=self_short, dot=dot, **style(self_short))]
    _put(ws, _chart(lines, cats, F06, RC, "0.0", 8), 2, row + 2, 10 * GRID_PX - 8, 264)
    # the gap: shaded above and below zero, the line over it; the axis follows the data (the gap reaches -25)
    from .assess_tab import _quiet_axes
    area = AreaChart(); area.grouping = "standard"; area.varyColors = False
    for j, (cn, color) in enumerate((("gap", K.GAP_WORSE), ("gap", K.GAP_BETTER))):
        area.add_data(Reference(wk, min_col=col["gap"] + 1 + j, min_row=F06, max_row=RC), titles_from_data=False)
        s_ = area.series[-1]; s_.tx = SeriesLabel(v=("above zero", "below zero")[j])
        s_.graphicalProperties.solidFill = color; s_.graphicalProperties.line.noFill = True
    area.set_categories(Reference(wk, min_col=1, min_row=F06, max_row=RC))
    gl = LineChart()
    gl.add_data(Reference(wk, min_col=col["gap_c"], min_row=F06, max_row=RC), titles_from_data=False)
    s_ = gl.series[-1]
    s_.tx = SeriesLabel(v="Gap to peers, points (above zero: more of KeyBank's delinquent dollars became losses)")
    s_.graphicalProperties.line = _ln(K.KEY_RED, 2.25); s_.smooth = False; s_.marker.symbol = "none"
    if dot is not None:
        dp = DataPoint(idx=dot, marker=Marker(symbol="circle", size=6))
        dp.marker.graphicalProperties = GraphicalProperties(solidFill=K.KEY_RED, ln=_ln(K.KEY_RED, 0.75))
        dp.graphicalProperties = GraphicalProperties(ln=_ln(K.KEY_RED, 2.25))
        s_.dPt.append(dp)
    area += gl
    _quiet_axes(area, 8)
    # no legend: one line, named in the title above; Excel does not honor a deleted legend entry openpyxl writes
    # one decimal: the axis steps by half a point on a small gap (mortgage), and "+0" read "+2, +2, +1, +1"
    _finish(area, "+0.0;-0.0;0", False, True, True)
    area.x_axis.spPr = GraphicalProperties(ln=_ln(K.SLATE, 0.75))       # the zero line: the category axis crosses at zero
    _put(ws, _no_auto_title(area), 12, row + 2, 10 * GRID_PX - 8, 264)
    ws.cell(row + 14, 12, PACK).font = F_NOTE
    # the gap, priced
    g0 = row + 16
    c_ = ws.cell(g0, 2, '="Gap, priced in KeyBank\'s delinquent "&LOWER(%s)&" dollars"' % co_prod); c_.font = F_LAB
    rule(g0, 2, 7)
    rows_ = (("Delinquent dollars ($000)", "=%s" % d30_at, "#,##0", "=%s" % q_gap, F_SMALL),
             ("Gap to peers (points)", "=%s" % gap_at, "+0.00;-0.00;0.00", "KeyBank minus peer group", F_SMALL),
             ("Dollars the gap is worth ($000)", '=IF(ISNUMBER(%s),ABS(%s),"")' % (cells["priced"], cells["priced"]), "#,##0",
              '=IF(N(%s)<0,"fewer charged off within two quarters",IF(N(%s)>0,"more charged off within two quarters",""))' % (gap_at, gap_at),
              F_SMALL_B))
    for i, (lab, val, fmt, note, font) in enumerate(rows_):
        r = g0 + 1 + i
        ws.cell(r, 2, lab).font = font
        num(r, 5, val, fmt, font)
        ws.cell(r, 6, note).font = F_NOTE
        if i < 2:
            rule(r, 2, 7, HAIR)
    # the window test: the product drawn above, the industry over the next 1, 2 and 3 quarters;
    # KeyBank and the peer group over two (the book's definition)
    if "q_win" in cells:
        qw = cells["q_win"]
        c_ = ws.cell(g0 - 1, 9, '=%s&" · charged off within the window, %% of delinquent dollars, "&%s' % (co_prod, qw))
        c_.font = F_LAB
        for j, h in enumerate(("Window", "KeyBank", "Peer group", "Industry", "Gap to peers")):
            cc = ws.cell(g0, 9 + j, h); cc.font = F_LAB; cc.alignment = LEFT if j == 0 else RIGHT
        rule(g0, 9, 13)
        at = lambda s_: ('IFERROR(INDEX(%s,MATCH(%s,%s,0)),"")'                                 # noqa: E731
                         % (RW("co_kb" if s_ == self_short else "co_pg"), qw, WQ))
        for i, n_ in enumerate((1, 2, 3)):
            r = g0 + 1 + i
            font = F_SMALL_B if n_ == 2 else F_SMALL
            ws.cell(r, 9, "%d quarter%s" % (n_, "" if n_ == 1 else "s")).font = font
            if n_ == 2:
                kb_, pg_ = at(self_short), at(pg_src)
                num(r, 10, "=" + kb_, "0.00", font); num(r, 11, "=" + pg_, "0.00", font)
                c_ = num(r, 13, '=IF(AND(ISNUMBER(J{r}),ISNUMBER(K{r})),J{r}-K{r},"")'.format(r=r), "+0.00;-0.00;0.00", font)
                c_.font = Font(name="Calibri", size=10, bold=True, color=K.CRIMSON)
            num(r, 12, "=" + win_at(n_, qw), "0.00", font)
            for c_ in range(9, 14):
                if n_ == 2:
                    ws.cell(r, c_).fill = CANVAS
                if n_ < 3:
                    ws.cell(r, c_).border = Border(bottom=HAIR)
    spacer(g0 + 4)
    row = g0 + 5

    # D. the pipeline, for the product drawn (the picked one, where KeyBank has 30+ incl. nonaccrual)
    pp = cells["pipe_product"]
    head(row, '="The pipeline · "&LOWER(%s)&IF(%s,": 30+ incl. nonaccrual, then 90+ incl. nonaccrual, then charge-offs",'
         '" · none for this product in this workbook")' % (pp, cells["pipe_has"]),
         "The pipeline", 1)
    ws.row_dimensions[row + 1].height = 15
    for j, ttl in enumerate(('="1. "&%s&" 30+ incl. nonaccrual, %%"' % pp, '="2. "&%s&" 90+ incl. nonaccrual, %%"' % pp,
                             '="3. "&%s&" gross charge-offs, 4 quarters, %%"' % pp)):
        title(row + 1, 2 + 6 * j, ttl)
        lines = [dict(ws=wk, col=col["pipe%d_%s_c" % (j, _slug(s_))], name=s_,
                      dot=(R1 - F06) if s_ == self_short else None, **style(s_))
                 for s_ in (INDUSTRY, pg_src, self_short)]
        _put(ws, _chart(lines, (data_ws, 1), F06, R1, "0.0", 16), 2 + 6 * j, row + 2, 6 * GRID_PX - 8, 220)
    ws.cell(row + 12, 2, PACK).font = F_NOTE
    spacer(row + 13)
    row += 14

    # E. one block per signal
    fit_rows = {}
    for key, title_, what, kind, pkind, fmt in SIGNALS:
        name, jname, span, raw_t, src, vfmt = SHOWN[key][0], SHOWN[key][1], SHOWN[key][2], SHOWN[key][3], SHOWN[key][4], SHOWN[key][5]
        d = by_key[key][2]
        span_txt = "%s to %s" % (min(d), max(d)) if d else "no quarters"
        head(row, name, jname, span, "%s · %s · quarterly" % (src, span_txt))
        r0 = row
        ws.row_dimensions[r0 + 1].height = 15
        title(r0 + 1, 2, "Both lines rescaled: yearly moves from each line's own normal · one grid line = one yearly move")
        title(r0 + 1, 12, raw_t)
        title(r0 + 7, 12, "The picked series, own units")
        over = [dict(ws=wk, col=col[key + "_zsc"], ref=names[key], color=K.SIGNAL, w=2),
                dict(ws=wk, col=col["picked_zc"], ref=picked_name, color=K.KEY_RED, w=2)]
        _put(ws, _chart(over, cats, F06, R1, "+0;-0;0", 8, grid=True, low=True, major=2), 2, r0 + 2, 10 * GRID_PX - 8, 264)
        f_sig = R0 + grid.index(min(d)) if d and min(d) in grid else F06       # the raw signal from its first quarter
        _put(ws, _chart([dict(ws=wk, col=col[key + "_c"], name=jname, color=K.SIGNAL, w=1.75)], cats, f_sig, R1, fmt,
                        _skip(R1 - f_sig + 1), legend=False),
             12, r0 + 2, 3 * GRID_PX - 8, 106)
        _put(ws, _chart([dict(ws=wk, col=col["picked_c"], name="the picked series", color=K.KEY_RED, w=1.75)], cats, F06, R1, "0.00", _skip(R1 - F06 + 1),
                        legend=False), 12, r0 + 8, 3 * GRID_PX - 8, 106)
        # the fit table, beside the charts: the pick first, then the eight fixed series
        for j, h in enumerate(("Against", "", "", "Lead", "Fit (r)", "Excl. 2020-23", "Qtrs")):
            if h:
                cc = ws.cell(r0 + 1, 15 + j, h); cc.font = F_LAB; cc.alignment = Alignment(horizontal="left" if j == 0 else "right", vertical="bottom")
        rule(r0 + 1, 15, 21)
        top = fit_at[key]
        rb = top + 2 + len(LEADS)
        order = [len(tcols) - 1] + list(range(len(tcols) - 1))
        for i, j in enumerate(order):
            tname, nice, lbl = tcols[j]
            rr = r0 + 2 + i
            font = F_SMALL_B if tname == "picked" else F_SMALL
            if tname == "picked":
                ws.merge_cells(start_row=rr, start_column=15, end_row=rr, end_column=17)
                cc = ws.cell(rr, 15, "=" + PICK_SHORT)
                cc.alignment = Alignment(horizontal="left", vertical="bottom", shrink_to_fit=True)
            else:
                cc = ws.cell(rr, 15, nice)
            cc.font = font
            best = "%s%s%d" % (WK, L(2 + j), rb)
            rng = "%s$%s$%d:$%s$%d" % (WK, L(2 + j), top + 2, L(2 + j), top + 1 + len(LEADS))
            ex = "%s%s%d" % (WK, L(2 + j + len(tcols) + 2), rb)
            num(rr, 18, '=IF(%s="","",%s)' % (best, best), "+0;-0;0", font)
            num(rr, 19, '=IFERROR(MAX(%s),"")' % rng, "0.00", font)
            num(rr, 20, '=IF(%s="","",%s)' % (ex, ex), "0.00", font)
            # the quarters the fit at that lead rests on (Codex on #466: not both full columns)
            sf_ = "%s$%s$%d" % (WK, L(col[key] + (1 if kind == "level" else 0)), R0)
            tf_ = "%s$%s$%d" % (WK, L(col[tname] + 1), R0)
            num(rr, 21, '=IF(ISNUMBER($R{r}),SUMPRODUCT(--ISNUMBER(OFFSET({s},MAX(0,-$R{r}),0,{n}-ABS($R{r}),1)),'
                        '--ISNUMBER(OFFSET({t},MAX(0,$R{r}),0,{n}-ABS($R{r}),1))),"")'.format(r=rr, s=sf_, t=tf_, n=N), "0", font)
            for c_ in range(15, 22):
                if tname == "picked":
                    ws.cell(rr, c_).fill = CANVAS
                ws.cell(rr, c_).border = Border(bottom=HAIR)
        first_fixed, last_fixed = r0 + 3, r0 + 1 + len(tcols)
        if last_fixed >= first_fixed:
            ws.conditional_formatting.add("S%d:S%d" % (first_fixed, last_fixed),
                                          FormulaRule(formula=["AND(ISNUMBER(S%d),ABS(S%d)>=0.7)" % (first_fixed, first_fixed)], font=Font(bold=True)))
        fit_rows[key] = {"pick": r0 + 2, "first_fixed": first_fixed}
        # the inputs of the rescale, under the overlay
        ri = r0 + 14
        # Line B:E; Normal F; One yearly move H, its header reaching over the empty G; Shift I; Window J
        for c_, h in ((2, "Line"), (6, "Normal"), (8, "One yearly move"), (9, "Shift (quarters)"), (10, "Window")):
            cc = ws.cell(ri, c_, h); cc.font = F_LAB
            cc.alignment = Alignment(horizontal="left" if c_ in (2, 10) else "right", vertical="bottom", indent=1 if c_ == 10 else 0)
        rule(ri, 2, 11)
        ws.cell(ri + 1, 2, jname).font = Font(name="Calibri", size=10, color=K.SIGNAL)
        num(ri + 1, 6, '=IFERROR(MEDIAN(%s),"")' % RW(key, 2), vfmt)
        num(ri + 1, 8, '=IFERROR(1.4826*MEDIAN(%s),"")' % RW(key, 4), vfmt)
        num(ri + 1, 9, '=%s&IF(ISNUMBER(%s),""," · %s")' % (shift_cells[key], SH, FIT_AUTO), "General")
        cc = ws.cell(ri + 1, 10, "=%s" % WIN); cc.font = F_SMALL; cc.alignment = Alignment(vertical="bottom", indent=1)
        ws.cell(ri + 2, 2, "=" + PICK_SHORT).font = Font(name="Calibri", size=10, color=K.KEY_RED)
        num(ri + 2, 6, '=IFERROR(MEDIAN(%s),"")' % RW("picked", 2), "0.00")
        num(ri + 2, 8, '=IFERROR(1.4826*MEDIAN(%s),"")' % RW("picked", 4), "0.00")
        num(ri + 2, 9, 0, "0")
        cc = ws.cell(ri + 2, 10, "=%s" % WIN); cc.font = F_SMALL; cc.alignment = Alignment(vertical="bottom", indent=1)
        rule(ri + 1, 2, 11, HAIR)
        ws.cell(ri + 3, 2, PACK).font = F_NOTE
        spacer(ri + 4)
        row = ri + 5

    # F. across products: each product's industry 30-89 days past due, raw, and how each runs against the pick
    head(row, "Across products · %s, %s, against the picked series" % (XP_MEASURE.lower(), INDUSTRY), "Across products", 1)
    ws.row_dimensions[row + 1].height = 15
    title(row + 1, 2, "%s, every product, %s, %%" % (XP_MEASURE, INDUSTRY))
    lines = [dict(ws=data_ws, col=head_[" - ".join((p_, XP_MEASURE, INDUSTRY))], name=p_, color=PRODUCT_COLOR[p_], w=1.75,
                  dash="dash" if p_ in COMBINED else None) for p_ in xprods]
    if lines:
        _put(ws, _chart(lines, (data_ws, 1), F06, R1, "0.0", 16), 2, row + 2, 10 * GRID_PX - 8, 264)
    c_ = ws.cell(row + 1, 13, '="Against "&%s' % PICK_SHORT); c_.font = F_LAB
    c_.alignment = Alignment(vertical="bottom")                   # runs over the empty N:U, never shrunk
    for c_, h in ((13, "Product"), (18, "Lead"), (19, "Fit (r)"), (20, "Excl. 2020-23"), (21, "Qtrs")):
        cc = ws.cell(row + 2, c_, h); cc.font = F_LAB
        cc.alignment = Alignment(horizontal="left" if c_ == 13 else "right", vertical="bottom")
    rule(row + 2, 13, 21)
    for i, p_ in enumerate(xprods):
        rr = row + 3 + i
        ws.cell(rr, 13, p_).font = F_SMALL
        a_, x_ = xfit[p_]
        best = 'INDEX(%s,MATCH(MAX(%s),%s,0))' % (XLEADS, a_, a_)
        num(rr, 18, '=IFERROR(%s,"")' % best, "+0;-0;0")
        num(rr, 19, '=IFERROR(MAX(%s),"")' % a_, "0.00")
        num(rr, 20, '=IFERROR(INDEX(%s,MATCH(%s,%s,0)),"")' % (x_, best, XLEADS), "0.00")
        # the quarters the fit at that lead rests on: both yearly changes there, the signal led by the lead
        sf_, tf_ = ("%s$%s$%d" % (WK, L(col[k_] + 1), R0) for k_ in ("xp_" + _slug(p_), "picked"))
        num(rr, 21, '=IF(ISNUMBER($R{r}),SUMPRODUCT(--ISNUMBER(OFFSET({s},MAX(0,-$R{r}),0,{n}-ABS($R{r}),1)),'
                    '--ISNUMBER(OFFSET({t},MAX(0,$R{r}),0,{n}-ABS($R{r}),1))),"")'.format(r=rr, s=sf_, t=tf_, n=N), "0")
        for c_ in range(13, 22):
            ws.cell(rr, c_).border = Border(bottom=HAIR)
    if xprods:
        f0, f1 = row + 3, row + 2 + len(xprods)
        ws.conditional_formatting.add("S%d:S%d" % (f0, f1), FormulaRule(
            formula=["AND(ISNUMBER(S%d),ABS(S%d)>=0.7)" % (f0, f0)], font=Font(bold=True)))
    row += 16

    # the jump row: a link to each section's head
    c_ = 2
    for name, span, r in jumps:
        cell = ws.cell(R_JUMP, c_, name)
        cell.hyperlink = Hyperlink(ref=cell.coordinate, location="%sB%d" % (SG, r), display=name)
        cell.font = F_JUMP
        c_ += span
    # Every row a height of its own: Excel fits a row with text to its font (15 pt for Calibri 11) whatever the
    # sheet's default says, and the charts are laid on 22 px rows.
    for r in range(1, row + 1):
        if ws.row_dimensions[r].height is None:
            ws.row_dimensions[r].height = 16.5
    ws.freeze_panes = "B8"
    return {"sheet": TITLE, "data": DATA_TITLE, "workings": WORK_TITLE, "rows": row, "signals": [k for k, *_ in SIGNALS],
            "fit_targets": [t[2] for t in targets],
            "controls": {"product": "B5", "measure": "E5", "source": "I5", "shift": "K5", "window": "M5", "picked": "P5"},
            "dollars": {"header": A_TH, "first": A_FIRST, "total": A_TOTAL, "on": "B%d:F%d" % (A_ON, A_ON)},
            "fit_tables": fit_rows, "jumps": [(n, r) for n, _, r in jumps]}
