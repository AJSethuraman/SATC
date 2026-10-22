"""The Decide tab: one product and measure at a time, and the decisions kept in the workbook.

The bank, 14 Oct 2026: *"assess one thing at a time, save decisions, not a
guide"*, and *"it cannot be a huge list"*; banks block macros. So every
product and measure has one row in a table, ``Decisions``, at the top of the
tab, and two slicers (``slicers.py``) filter it to the one being looked at: a
product and a measure, clicked. Typing in that row is the decision; saving the
file keeps it. Everything under the table follows the one visible row.

One set of lines per product and measure, set from the history of one source
the bank picks (the firm, 15 Oct 2026: *"we don't need to set thresholds on
all 3, we need to use all 3 to set appropriate thresholds. industry,
competitor, and key reported"*). The row's yellow **Lines set from** names
that source; its settings and its period left out apply to that history. The
tab shows what every source's own history would give, every source's latest
quarter rated on the lines picked, and all of them on one chart.

Laid out to Claude Design's round 2 (docs/design/round-2/README.md, "Decide")
and round 3 (docs/design/round-3/handoff/README.md, "Decide"): the slicers as
three rows of buttons over B4:Q7, the table from row 9, then the headline,
the Check band, and the chart beside the panel of its numbers, all on the
first screen, with the pack line (the workbook's PackLine, from Peers) under
the chart when the peer tabs are in the workbook.

Assess's settings and periods-left-out cells become formulas reading the
table, so every source's lines (the Lines by source tab) are computed exactly
as they were; nothing here computes a line. The arithmetic on this tab is only
what draws and describes the picture, and each source's latest value rated on
the lines picked, as Thresholds rates it.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Set, Tuple

from openpyxl.chart import AreaChart, LineChart
from openpyxl.chart.data_source import AxDataSource, NumDataSource, NumRef, StrRef
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.layout import Layout, ManualLayout
from openpyxl.chart.series import Series, SeriesLabel
from openpyxl.formatting.rule import FormulaRule, Rule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.styles.numbers import NumberFormat
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

from . import keybank_style as K
from .assess_tab import HC as A_HC, LO_ROWS

TITLE = "Decide"
TABLE = "Decisions"
#: Every source's own lines, latest value and rating: the per-series table the
#: workbook builds as "Thresholds" and the book renames once Decide is built,
#: so that Thresholds is the one set of lines per product and measure.
LINES_TAB = "Lines by source"
HDR = 9                                   # the table's header row; the slicers sit over rows 4-7
SLICER_ROWS = (4, 7)
#: What the chart can show; the lines never depend on it. Each with the
#: quarters between its labels (the README: 2 / 4 / 8 / 12).
WINDOWS = ("Last 20 quarters", "Last 48 quarters", "Last 80 quarters", "Every quarter")
DEFAULT_WINDOW = WINDOWS[1]
#: Where the two slicers sit, as (from_col, from_row, to_col, to_row), 0-based
#: cells: over B:E and F:Q, and how many buttons to a row (round 3: Product
#: three to a row, Measure five, so every name fits in three rows). They
#: take in the 6 pt rows above and below 4-7, 108 px in all: Excel 16 drew
#: the caption and two rows of 0.25 in buttons in 94 px, so three rows take
#: buttons of 0.2 in.
SLICER_ANCHORS = ((1, 2, 5, 8), (5, 2, 17, 8))
SLICER_COLUMNS = (3, 5)
SLICER_STYLE = "SlicerStyleOther2"
SLICER_BUTTON_IN = 0.2
DECISIONS = ("Not decided", "Accept these lines", "Reject")
#: What a source with no series for the row shown reads, in STONE.
NO_SERIES = "—"
#: The workbook's pack line (peers_workbook.PACK_LINE), under the chart when the peer tabs are built.
PACK_LINE = "PackLine"
LINES_FROM = "Lines set from"
FIXED = [LINES_FROM, "Decision", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)",
         "On a line, rate it", "Periods left out", "Quarters left out", "Note", "Check", "Series", "Shown", "Key"]
#: Table columns that only the formulas read. They sit in O:Q, under the
#: panel's columns, so they are not hidden: their text is formatted away.
HIDDEN = ("Series", "Shown", "Key")
TYPED = (LINES_FROM, "Decision", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)",
         "On a line, rate it", "Note")
#: Read from the Periods left out list below the table, one or more per row (the analyst, 20 Oct 2026:
#: "how am I supposed to even address multiple stretches of quarters being left out").
LEFT_OUT_COLS = ("Periods left out", "Quarters left out")
#: Typed cells shown bold: the numbers and the picks.
BOLD_TYPED = (LINES_FROM, "Decision", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)",
              "On a line, rate it")
#: Column widths in pixels at 100% (docs/design/round-3/handoff/README.md,
#: Decide). The table's are the README's to K. L:Q take the right panel's
#: (220 · 130 · 110 · 90 · 90 · 120), so its source names fit: the README
#: gives L:Q two sets of widths, both 760 px in all, and a column has one,
#: so Note and Check take the panel's; N:P hold only the
#: table's hidden helpers.
COL_PX = {"A": 16, "B": 110, "C": 200, "D": 150, "E": 130, "F": 84, "G": 84, "H": 84, "I": 74, "J": 80, "K": 80,
          "L": 220, "M": 130, "N": 110, "O": 90, "P": 90, "Q": 120}
#: Assess's columns for each of Your settings, in order.
SETTING_COLS = (("Width of Moderate", "O"), ("Moderate-Low begins", "P"), ("How rare High is (z)", "Q"),
                ("On a line, rate it", "R"))
#: Assess's evidence text per series (assess_tab: hc + 18..20 with hc at Z).
EVIDENCE_COLS = (("Suggested", "AR"), ("Unusual stretches", "AS"), ("Why", "AT"))
#: Rating cells, 1 Low to 5 High (Summary reads it too).
SCALE = K.RATING_FILL
RATINGS = ("Low", "Moderate-Low", "Moderate", "Moderate-High", "High")
H = 27                                    # hidden helpers from column AA
SRC_TOP = 20                              # per-source helpers in AA:AE, from this row
CH = 32                                   # chart helpers from column AF
INK, SLATE = K.INK_TEXT, K.SLATE
F_BODY = Font(name="Calibri", size=11, color=INK)
F_BOLD = Font(name="Calibri", size=11, bold=True, color=INK)
F_SLATE = Font(name="Calibri", size=11, color=SLATE)
F_NOTE = Font(name="Calibri", size=10, color=SLATE)
F_LAB = Font(name="Arial", size=9, bold=True, color=SLATE)
F_HEAD = Font(name="Arial", size=11, bold=True, color=K.INK)
EDGE = Side(style="thin", color=K.INPUT_EDGE)
BOX = Border(EDGE, EDGE, EDGE, EDGE)
HAIR = Side(style="thin", color=K.MIST)
#: The per-series table's columns, by what they hold. A plain workbook keeps
#: the layout it has always had (its tab is Thresholds); a workbook with
#: Decide (the book) has it laid out to round 2 (its tab is Lines by source).
#: Every tab that reads it takes its letters from here, never from a literal,
#: so a column can move in one place.
TH_PLAIN = dict(series="A", median="B", move="C", worst="D", l2="E", l3="F", l4="G", l5="H", quarter="I",
                value="J", rating="K", rating_name="L", refusal="M", med_change="O", spread="P", med_all="Q",
                med_change_all="R", move_all="S", spread_all="T", fix="U")
TH_BOOK = dict(series="A", product="B", measure="C", source="D", median="E", move="F", worst="G", l2="H", l3="I",
               l4="J", l5="K", quarter="L", value="M", rating_shown="N", decision="O", check="P", rating="Q",
               rating_name="R", refusal="S", fix="T", med_change="U", spread="V", med_all="W", med_change_all="X",
               move_all="Y", spread_all="Z", floor="AA")
TH = TH_BOOK
#: The per-series table's first and last helper columns in the book: hidden.
TH_HIDDEN = ("Q", "AA")

#: The per-series refusal for a half-typed period says to look on Assess; on Decide the cells are here.
HERE = ('SUBSTITUTE(SUBSTITUTE({m},"its Status on Assess says what is missing","its row under Periods left out on '
        'Decide says what is missing"),"Finish that row under Periods left out (product, From, To and a reason), or '
        'clear all four of its cells","Finish its row under Periods left out on Decide (product, measure, From, To and '
        'Why), or clear all five of its cells")')


def fill(hex_):
    return PatternFill("solid", fgColor=hex_, bgColor=hex_)


def source_colors(third: Sequence[str]) -> Dict[str, str]:
    """The line colour of each source: KeyBank in KEY_RED, the rest in turn
    SLATE, INK, MEDIAN, INTERNAL (the README: Industry SLATE, Peer group INK)."""
    rest = [K.SLATE, K.INK, K.MEDIAN, K.INTERNAL, K.STONE]
    out, i = {}, 0
    for v in third:
        if "keybank" in v.casefold():
            out[v] = K.KEY_RED
        else:
            out[v] = rest[i % len(rest)]
            i += 1
    return out


def columns(part_names: Sequence[str]) -> Dict[str, int]:
    """Column number of every table column, from B: the first two parts, then
    Lines set from where the third part's column was."""
    return {name: 2 + i for i, name in enumerate(list(part_names[:2]) + FIXED)}


def pairs_of(labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]]
             ) -> Tuple[List[Tuple[str, str]], Dict[Tuple[str, str], Dict[str, str]]]:
    """The rows of Decide and Thresholds: each first and second part (product
    and measure) once, in the order the series first name them, and for each
    the label of every source it has."""
    pairs, by = [], {}
    for lab in labels:
        a, b, s = parts[lab]
        if (a, b) not in by:
            pairs.append((a, b))
            by[(a, b)] = {}
        by[(a, b)][s] = lab
    return pairs, by


def sources_of(labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]]) -> List[str]:
    out = []
    for lab in labels:
        if parts[lab][2] not in out:
            out.append(parts[lab][2])
    return out


#: The peer group's banks under the chart: two lists side by side, each (name columns, switch, this quarter).
PEER_LISTS = (((2, 3), 4, 5), ((6, 8), 9, (10, 11)))


def layout(n: int, n_third: int, compare: bool, n_peers: int = 0) -> dict:
    """Where everything sits on Decide for n rows (products × measures) and
    n_third sources: one place for the builder, the tests and the walkthrough.
    For the book (56 rows, five sources) the table is rows 10 to 65, the
    headline 67, the Check 68, the section headings 70, the chart 71 to 90
    and the pack line 91. ``n_peers``: the banks the peer group can add up,
    listed under the chart with their switches (none without the peer tabs)."""
    first, last = HDR + 1, HDR + n
    head = last + 2
    sec = head + 3
    t = n_third
    chart_end = sec + 15 + t
    gives = chart_end + 2
    panel_end = gives + 1 + t
    # under the chart: a title with Banks in the pack, a header, then the banks in two lists, the rows
    # level with What each source's own history would give
    peers_title = chart_end + 2 if n_peers else None
    half = -(-n_peers // 2)
    # Why out, under the two lists: its heading, then as many rows as a list has
    why_head = chart_end + 3 + half + 2 if n_peers else None
    peers_end = why_head + half if n_peers else 0
    hist = max(panel_end, peers_end) + 2
    lo_title = hist + 6
    sett = lo_title + 2 + LO_ROWS + 1
    return dict(first=first, last=last, headline=head, chip=head, compare_line=head if compare else None,
                check=head + 1, section=sec, chart_top=sec + 1, chart_end=chart_end, ratings_head=sec + 1,
                pack_line=chart_end + 1, ratings_first=sec + 2, sources_title=sec + 8, sources_head=sec + 9,
                compare_first=sec + 10,
                window=sec + 10 + t, lines_label=sec + 12 + t, median=sec + 13 + t, move=sec + 14 + t,
                worst=sec + 15 + t, gives_title=gives, gives_head=gives + 1, gives_first=gives + 2,
                history=hist, evidence=hist + 1, left_now=hist + 4, settings=sett, notes=sett + 6,
                lo_title=lo_title, lo_head=lo_title + 1, lo_first=lo_title + 2, lo_last=lo_title + 1 + LO_ROWS,
                peers_title=peers_title, peers_pick=peers_title,
                peers_head=chart_end + 3 if n_peers else None, peers_first=chart_end + 4 if n_peers else None,
                why_head=why_head, why_first=why_head + 1 if n_peers else None)


def validate(part_names: Sequence[str]) -> None:
    if len(part_names) != 3:
        raise ValueError("the Decide tab needs exactly three parts to pick by (for example Product, Measure "
                         "and Source); %d were given" % len(part_names))
    for p in part_names:
        if not p.strip() or p in FIXED or "," in p or '"' in p:
            raise ValueError("%r can't name a part: it must be words, not one of the tab's own columns (%s), "
                             "and hold no comma or double quote" % (p, ", ".join(FIXED)))
    if len({p.casefold() for p in part_names}) != 3:
        raise ValueError("the three parts need three different names")


def check_start(start: Optional[str], labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]]) -> None:
    """``start``, the source every row's Lines set from starts as, or None to
    start blank. A source some row does not have is refused, naming the rows."""
    if start is None:
        return
    pairs, by = pairs_of(labels, parts)
    if start not in sources_of(labels, parts):
        raise ValueError("lines_from starts as %r, which is not a source of the series (%s)"
                         % (start, ", ".join(sources_of(labels, parts))))
    lacking = [" - ".join(pr) for pr in pairs if start not in by[pr]]
    if lacking:
        raise ValueError("lines_from starts as %r, and these have no %s series: %s. Start it blank (null) and "
                         "pick a source on each row" % (start, start, ", ".join(lacking)))


def _rule(ws, row, c1, c2, side):
    for c in range(c1, c2 + 1):
        ws.cell(row, c).border = Border(bottom=side)


def _q(s: str) -> str:
    """Text for a formula's string literal."""
    return s.replace('"', '""')


def build(wb, *, labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]], part_names: Sequence[str],
          settings: Dict[str, Tuple[float, float, float, str]], lay: dict, n_quarters: int,
          absent: Sequence[dict], compare: Optional[Tuple[str, str]], lines_from: Optional[str],
          changes: Dict[str, Set[str]], quarters: Sequence[str], unit: str = "", higher: bool = True,
          floor_at_zero: bool = True, floor_off: Sequence[str] = (), peers: Optional[dict] = None) -> dict:
    """Add the Decide tab to ``wb`` (which already holds Assess, the per-series
    table titled Thresholds, and Data for ``labels``) and point Assess's typed
    cells at it.

    ``parts``: each label's three part values, in ``part_names`` order;
    ``settings``: each label's starting Your settings (a row takes its first
    series'); ``lay``: Assess's layout (``assess_tab.layout``); ``absent``:
    the book's notes on combinations not in the workbook (``{"parts": {...},
    "why": text}``), printed as given; ``compare``: (this, against), two
    values of the third part to set side by side, or None; ``lines_from``:
    the source every row's Lines set from starts as, or None for blank;
    ``higher``, ``floor_at_zero``: the measure's direction and floor, as the
    lines rate with them. ``changes``: each label's quarters a reporting
    change took effect in, as its file's notes name them
    (``reporting_changes.quarters_in_notes``; an empty set for none), and
    ``quarters`` the Data tab's quarters, in order: the chart marks them, along the top of the rating zones, for the row shown
    (any of its sources' quarters). ``peers``: None, or the peer tabs' switches to set
    here instead (``names``, ``sheet``, ``include``, ``states``, ``pack``; peer_switches).
    Returns where things are, for the
    slicers, the Thresholds tab and tests."""
    validate(part_names)
    check_start(lines_from, labels, parts)
    asx = wb["Assess"]
    T = TH_BOOK
    n = len(labels)
    pairs, by_pair = pairs_of(labels, parts)
    rows_n = len(pairs)
    q_last = n_quarters + 1                                  # Data rows 2..q_last
    d_raw_last = L(1 + n)
    d_kept_last = L(1 + 2 * n)
    TH_END = 4 + n
    SET_TOP, LO_TOP = lay["set_top"], lay["lo_top"]
    LO_N = lay["lo_end"] - LO_TOP + 1
    C = columns(part_names)
    p0, p1, p2 = part_names
    third = sources_of(labels, parts)
    colors = source_colors(third)
    lead = compare[0] if compare else third[0]
    lay_d = layout(rows_n, len(third), bool(compare), len(peers["names"]) if peers else 0)
    FIRST, LAST = lay_d["first"], lay_d["last"]
    row_of = {pr: FIRST + i for i, pr in enumerate(pairs)}
    # Periods left out, below: its rows, and per row (hidden, from AA) the quarters it leaves out when
    # whole, 1 when whole, and the words of the row shown's periods so far, "; " between them
    LO1, LO9 = lay_d["lo_first"], lay_d["lo_last"]
    lo_rng = lambda c_: "$%s$%d:$%s$%d" % (c_, LO1, c_, LO9)               # noqa: E731
    LO_Q, LO_W = (lo_rng(L(H + i)) for i in range(2))
    LO_SAID = "$%s$%d" % (L(H + 2), LO9)
    fz = floor_at_zero and higher

    ws = wb.create_sheet(TITLE)
    ws.sheet_properties.tabColor = K.TAB_WORK
    ws.sheet_view.showGridLines = False

    # ---- columns and the rows above the table (the README, px -> units) ----
    for c_, px in COL_PX.items():
        ws.column_dimensions[c_].width = round(px / 7, 2)
    for r, h in ((1, 25.5), (2, 15), (3, 6), (4, 15), (5, 18), (6, 18), (7, 18), (8, 6), (HDR, 27)):
        ws.row_dimensions[r].height = h

    ws["B1"] = "Decide · one %s and %s at a time" % (p0.lower(), p1.lower())
    ws["B1"].font = Font(name="Arial", size=16, bold=True, color=K.INK)
    ws["B1"].alignment = Alignment(vertical="bottom")
    ws["B2"] = ("Pick a %s and a %s. The yellow row sets one set of lines from the history of the %s under %s; "
                "save the file (Ctrl+S) to keep them." % (p0.lower(), p1.lower(), p2.lower(), LINES_FROM))
    ws["B2"].font = F_SLATE
    _rule(ws, 2, 2, 17, Side(style="medium", color=K.KEY_RED))

    # ---- the table: one row per product and measure; the slicers show one ----
    for name, c in C.items():
        cell = ws.cell(HDR, c, name)
        right = name in ("Width of Moderate", "Moderate-Low begins", "How rare High is (z)")
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="right" if right else "left")
        if name in HIDDEN:
            cell.font = Font(name="Arial", size=9, color=K.PAPER)
        else:
            cell.font = Font(name="Arial", size=9, bold=True, color=K.PAPER)
            cell.fill = fill(K.INK)
    th_a = "Thresholds!$A$5:$A$%d" % TH_END
    th_col = lambda key: "Thresholds!$%s$5:$%s$%d" % (T[key], T[key], TH_END)   # noqa: E731
    for i, pr in enumerate(pairs):
        r = FIRST + i
        ws.cell(r, C[p0], pr[0])
        ws.cell(r, C[p1], pr[1])
        ws.cell(r, C[LINES_FROM], lines_from if lines_from is not None else None)
        ws.cell(r, C["Decision"], DECISIONS[0])
        first_lab = next(iter(by_pair[pr].values()))
        for (name, _), v in zip(SETTING_COLS, settings[first_lab]):
            ws.cell(r, C[name], v)
        lf, ser = "%s%d" % (L(C[LINES_FROM]), r), "%s%d" % (L(C["Series"]), r)
        ws.cell(r, C["Series"], '=IF({lf}="","",{a}{r}&" - "&{b}{r}&" - "&{lf})'.format(
            lf=lf, a=L(C[p0]), b=L(C[p1]), r=r))
        ws.cell(r, C["Check"], '=IF({lf}="","Pick a source",IFERROR(IF(INDEX({m},MATCH({s},{a},0))="","OK",'
                               '"Refused: see the fix below"),"No such series: pick another"))'
                .format(lf=lf, m=th_col("refusal"), s=ser, a=th_a))
        ws.cell(r, C["Shown"], "=SUBTOTAL(103,%s%d)" % (L(C[p0]), r))
        ws.cell(r, C["Key"], '={a}{r}&" · "&{b}{r}'.format(a=L(C[p0]), b=L(C[p1]), r=r))
        ws.cell(r, C["Periods left out"], '=SUMIFS({s},{lb},{a}{r},{lc},{b}{r})'.format(
            s=LO_W, lb=lo_rng("B"), lc=lo_rng("C"), a=L(C[p0]), b=L(C[p1]), r=r)).number_format = '0;-0;;@'
        # The quarters the lines lose: the series' values less those it keeps on Data, so
        # periods that overlap count each quarter once, as the lines do (Codex on #467).
        d_all, d_hdr = "Data!$B$2:$%s$%d" % (d_kept_last, q_last), "Data!$B$1:$%s$1" % d_kept_last
        ws.cell(r, C["Quarters left out"], '=IF({s}="","",SUMPRODUCT(({h}={s})*ISNUMBER({v}))'
                                           '-SUMPRODUCT(({h}={s}&", kept")*ISNUMBER({v})))'
                .format(s=ser, v=d_all, h=d_hdr)).number_format = '0;-0;;@'
        for name in C:
            c_ = ws.cell(r, C[name])
            c_.alignment = Alignment(vertical="center", wrap_text=name in ("Note", "Check", LINES_FROM)
                                     or name in part_names, horizontal="right" if name in LEFT_OUT_COLS else None)
            if name in TYPED:
                c_.font = F_BOLD if name in BOLD_TYPED else F_BODY
                c_.fill = fill(K.INPUT)
                c_.border = BOX
            elif name in HIDDEN:
                c_.number_format = ";;;"
                c_.font = Font(name="Calibri", size=11, color=K.PAPER)
            else:
                c_.font = F_SLATE
                c_.border = Border(bottom=Side(style="thin", color=K.STONE))
        for name in ("Width of Moderate", "Moderate-Low begins", "How rare High is (z)"):
            ws.cell(r, C[name]).number_format = "0.0#"
        ws.row_dimensions[r].height = 34.5
    tbl = Table(displayName=TABLE, ref="%s%d:%s%d" % (L(C[p0]), HDR, L(C["Key"]), LAST))
    # No table style: the header is styled by hand, and the helper columns'
    # header must not be drawn (an unnamed style is what Excel writes for None).
    tbl.tableStyleInfo = TableStyleInfo(name=None, showRowStripes=False)
    ws.add_table(tbl)

    def rng(name, sheet=""):
        return "%s$%s$%d:$%s$%d" % (sheet, L(C[name]), FIRST, L(C[name]), LAST)

    for name, lst in ((LINES_FROM, '"%s"' % ",".join(third)), ("Decision", '"%s"' % ",".join(DECISIONS)),
                      ("On a line, rate it", '"worse,better"')):
        dv = DataValidation(type="list", formula1=lst, showErrorMessage=True, errorTitle=name,
                            error="Pick one from the list.")
        ws.add_data_validation(dv)
        dv.add(rng(name).replace("$", ""))
    chk = "%s%d" % (L(C["Check"]), FIRST)
    ws.conditional_formatting.add(rng("Check").replace("$", ""),
                                  FormulaRule(formula=['LEFT(%s,8)="Refused:"' % chk], fill=fill(K.CANVAS),
                                              font=Font(bold=True, color=K.CRIMSON)))
    ws.conditional_formatting.add(rng("Check").replace("$", ""),
                                  FormulaRule(formula=['OR(%s="Pick a source",LEFT(%s,8)="No such ")' % (chk, chk)],
                                              font=Font(bold=True, color=K.INK)))
    dec = "%s%d" % (L(C["Decision"]), FIRST)
    ws.conditional_formatting.add(rng("Decision").replace("$", ""),
                                  FormulaRule(formula=['%s="%s"' % (dec, DECISIONS[1])], font=Font(bold=True,
                                                                                                   color=K.INK)))
    ws.conditional_formatting.add(rng("Decision").replace("$", ""),
                                  FormulaRule(formula=['%s="%s"' % (dec, DECISIONS[2])], font=Font(bold=True,
                                                                                                   color=K.SLATE)))

    D = rng("Decision")
    ws.merge_cells("L1:Q1")
    ws["L1"] = ('="Decided: "&(COUNTIF({d},"{a}")+COUNTIF({d},"{r}"))&" of {n} · accepted "&COUNTIF({d},"{a}")'
                '&" · rejected "&COUNTIF({d},"{r}")').format(d=D, a=DECISIONS[1], r=DECISIONS[2], n=rows_n)
    ws["L1"].font = Font(name="Arial", size=12, bold=True, color=K.INK)
    ws["L1"].alignment = Alignment(horizontal="right", vertical="bottom")

    # ---- Assess reads the table: every source's settings are its row's, and
    # the period left out is the history the lines are set from ----
    none = PatternFill(fill_type=None)
    for i, lab in enumerate(labels):
        r, sr = row_of[tuple(parts[lab][:2])], SET_TOP + i
        for name, col in SETTING_COLS:
            c_ = asx["%s%d" % (col, sr)]
            c_.value = '=IF(Decide!{c}{r}="","",Decide!{c}{r})'.format(c=L(C[name]), r=r)
            c_.fill = none
    assert LO_N == LO_ROWS, "Periods left out on Decide and on Assess hold the same rows"
    for k in range(LO_N):
        # Row k of Periods left out on Decide: its series is the product and measure's
        # under the source its row's lines are set from.
        dr = lay_d["lo_first"] + k
        lf_ = 'INDEX(%s,MATCH(Decide!$B$%d&" · "&Decide!$C$%d,%s,0))' % (rng(LINES_FROM, "Decide!"), dr, dr,
                                                                       rng("Key", "Decide!"))
        asx["N%d" % (LO_TOP + k)].value = ('=IF(OR(Decide!$B${r}="",Decide!$C${r}=""),"",IFERROR(IF({lf}="","",'
                                           'Decide!$B${r}&" - "&Decide!$C${r}&" - "&{lf}),""))').format(r=dr, lf=lf_)
        for col, dc in (("O", "D"), ("P", "E"), ("Q", "F")):
            asx["%s%d" % (col, LO_TOP + k)].value = '=Decide!$%s$%d&""' % (dc, dr)
        for col in "NOPQ":
            asx["%s%d" % (col, LO_TOP + k)].fill = none
    asx.cell(lay["set_title"], 14).value = "Your settings · set on the Decide tab, shown here"
    asx.cell(lay["lo_title"], 14).value = "Periods left out · set on the Decide tab, shown here"
    for row in range(1, 4):
        for col in range(1, 25):
            v = asx.cell(row, col).value
            if isinstance(v, str) and v.startswith("Choose what to show in B5"):
                asx.cell(row, col).value = ("Detail for the series in B5. Settings, periods left out and decisions "
                                            "are made on the Decide tab.")

    # ---- hidden helpers: the row the buttons picked, and its lines ----
    SER, SHOWN = rng("Series"), rng("Shown")
    hc = L(H)
    LBL, COUNT, ROW, SRC = ("$%s$%d" % (hc, r) for r in (1, 2, 3, 4))
    LN = ["$%s$%d" % (hc, 5 + j) for j in range(4)]              # where 2, 3, 4 and 5 begin
    LNR = "$%s$5:$%s$8" % (hc, hc)
    REFUSAL, RULE, KEPT_OF = ("$%s$%d" % (hc, r) for r in (9, 10, 11))
    ONE = "%s=1" % COUNT
    ws.cell(1, H, '=IFERROR(INDEX(%s,MATCH(1,%s,0))&"","")' % (SER, SHOWN))
    ws.cell(2, H, "=SUM(%s)" % SHOWN)
    ws.cell(3, H, "=MATCH(%s,%s,0)" % (LBL, th_a))
    HAS = "AND(%s,ISNUMBER(%s))" % (ONE, ROW)

    def th_(key):
        c_ = T[key]
        return "INDEX(Thresholds!$%s$5:$%s$%d,%s)" % (c_, c_, TH_END, ROW)

    def shown(name):
        return "INDEX(%s,MATCH(1,%s,0))" % (rng(name), SHOWN)

    ws.cell(4, H, '=IF(%s,%s&"","")' % (ONE, shown(LINES_FROM)))
    for j, k_ in enumerate(("l2", "l3", "l4", "l5")):
        ws.cell(5 + j, H, '=IF(%s,IFERROR(%s+0,""),"")' % (HAS, th_(k_)))
    ws.cell(9, H, '=IF(%s,%s,"")' % (HAS, th_("refusal")))
    ws.cell(10, H, '=IF(%s,%s&"","")' % (ONE, shown("On a line, rate it")))
    ws.cell(11, H, '=IFERROR(MATCH(%s&", kept",Data!$B$1:$%s$1,0),"")' % (LBL, d_kept_last))
    # Whether the row shown has a floor at zero: its series' own flag on Lines
    # by source (a measure in the book's floor_off has none), so a gap that is
    # negative rates on its lines, never as 1 Low by the floor.
    ws.cell(12, H, '=IF(%s,%s,FALSE)' % (HAS, th_("floor")))
    FZ = "$%s$12" % hc
    lines_ok = "AND(%s,%s)" % (HAS, ",".join("ISNUMBER(%s)" % x for x in LN))
    stand = "AND(%s,%s=\"\")" % (lines_ok, REFUSAL)               # the lines picked stand

    # Per source, from row SRC_TOP: its label for the row shown (AA), its row
    # on the per-series table (AB), its latest value (AC) and that value's
    # rating on the lines picked (AD), as Thresholds rates it.
    if higher:
        op_w, op_b = "<=", "<"
    else:
        op_w, op_b = ">=", ">"
    src_rows = {}
    for k, v in enumerate(third):
        r = SRC_TOP + k
        src_rows[v] = r
        ws.cell(r, H, '=IF(%s,%s&" - "&%s&" - %s","")' % (ONE, shown(p0), shown(p1), _q(v)))
        ws.cell(r, H + 1, '=IF({a}{r}="","",IFERROR(MATCH({a}{r},{t},0),""))'.format(a=hc, r=r, t=th_a))
        ws.cell(r, H + 2, '=IF({b}{r}="","",IFERROR(INDEX({v},{b}{r})+0,""))'.format(b=L(H + 1), r=r,
                                                                                   v=th_col("value")))
        x = "%s%d" % (L(H + 2), r)
        ws.cell(r, H + 3, '=IF(OR(NOT({ok}),NOT(ISNUMBER({x}))),"",IF(AND({fz},{x}<=0),1,1+IF({rule}="worse",'
                          'COUNTIF({ln},"{w}"&{x}),COUNTIF({ln},"{b}"&{x}))))'
                .format(ok=stand, x=x, fz=FZ, rule=RULE, ln=LNR, w=op_w, b=op_b))
    LEADK = "$%s$%d" % (L(H + 3), src_rows[lead])
    LEADQ = "$%s$%d" % (L(H + 1), src_rows[lead])

    # ---- the headline: the row, its lines' source, and the lead source's rating ----
    hr = lay_d["headline"]
    ws.row_dimensions[hr - 1].height = 7.5
    ws.row_dimensions[hr].height = 30
    whys = [a["why"] for a in absent]
    none_msg = "No %s and %s in this workbook match those buttons." % (p0.lower(), p1.lower())
    if whys:
        none_msg += " Not in this workbook: " + " ".join(whys)
    ws.merge_cells(start_row=hr, start_column=2, end_row=hr, end_column=8)
    c_ = ws.cell(hr, 2, '=IF({c}=0,"{z}",IF({c}>1,{c}&" rows match. Pick one {a} and one {b}.",'
                        '{p}&", "&LOWER({m})&IF({s}="",": no {d} picked to set the lines yet",'
                        '": lines set from "&{s})))'
                 .format(c=COUNT, z=_q(none_msg), a=p0.lower(), b=p1.lower(), d=p2.lower(), s=SRC,
                         m=shown(p1), p=shown(p0)))
    c_.font = Font(name="Arial", size=14, bold=True, color=K.INK)
    c_.alignment = Alignment(vertical="center", shrink_to_fit=True)
    ws.merge_cells(start_row=hr, start_column=9, end_row=hr, end_column=11)
    chip = ws.cell(hr, 9, '=IF(NOT({o}),"",IF({k}="","No rating: see the Check","{n}: "&{k}&" "&CHOOSE({k},'
                          '"{r0}","{r1}","{r2}","{r3}","{r4}")))'
                   .format(o=ONE, k=LEADK, n=_q(lead), r0=RATINGS[0], r1=RATINGS[1], r2=RATINGS[2], r3=RATINGS[3],
                           r4=RATINGS[4]))
    chip.font = Font(name="Arial", size=12, bold=True, color=K.INK)
    chip.alignment = Alignment(vertical="center", indent=1, shrink_to_fit=True)
    CHIP = "$I$%d" % hr
    for k in range(5):
        ws.conditional_formatting.add("I%d:K%d" % (hr, hr), FormulaRule(
            formula=['%s=%d' % (LEADK, k + 1)], fill=fill(SCALE[k]), stopIfTrue=True))
    ws.conditional_formatting.add("I%d:K%d" % (hr, hr), FormulaRule(
        formula=['LEFT(%s,9)="No rating"' % CHIP], fill=fill(K.CANVAS), font=Font(bold=True, color=K.CRIMSON)))

    # ---- the Check band, under the headline: the reason, and what to type ----
    cr = lay_d["check"]
    ws.row_dimensions[cr].height = 25.5
    ws.merge_cells(start_row=cr, start_column=2, end_row=cr, end_column=8)
    ws.merge_cells(start_row=cr, start_column=9, end_row=cr, end_column=17)
    ws.cell(cr, 2, '=IF(NOT({o}),"",IF({s}="","Check: pick the {d} whose history sets the lines, '
                   'under {lf}.",IF(NOT(ISNUMBER({row})),"Check: this workbook has no "&{s}&" series for this {a} '
                   'and {b}.",IF({r}="","Check: OK, your settings fit the history the lines are set from.",{why}))))'
            .format(o=ONE, s=SRC, d=p2.lower(), lf=LINES_FROM, row=ROW, a=p0.lower(),
                    b=p1.lower(), r=REFUSAL, why=HERE.format(m=REFUSAL)))
    ws.cell(cr, 9, '=IF(NOT({h}),"",IF({r}="","","To fix: "&{fix}))'
            .format(h=HAS, r=REFUSAL, fix=HERE.format(m=th_("fix"))))
    for c in (2, 9):
        ws.cell(cr, c).font = Font(name="Arial", size=12, bold=True, color=K.INK)
        ws.cell(cr, c).alignment = Alignment(vertical="center", indent=1 if c == 2 else 0, shrink_to_fit=True)
    for c in range(2, 18):
        ws.cell(cr, c).fill = fill(K.CANVAS)
        ws.cell(cr, c).border = Border(top=HAIR, bottom=HAIR)
    refused_band = 'OR(LEFT($B${r},8)="Refused:",LEFT($B${r},9)="More than")'.format(r=cr)
    crimson = Side(style="thin", color=K.CRIMSON)
    ws.conditional_formatting.add("B%d:H%d" % (cr, cr), FormulaRule(
        formula=[refused_band], fill=fill(K.REFUSE_BAND), font=Font(bold=True, color=K.CRIMSON),
        border=Border(top=crimson, bottom=crimson)))
    ws.conditional_formatting.add("I%d:Q%d" % (cr, cr), FormulaRule(
        formula=[refused_band], fill=fill(K.REFUSE_BAND), font=Font(bold=True, color=K.INK),
        border=Border(top=crimson, bottom=crimson)))
    ws.row_dimensions[cr + 1].height = 7.5

    # ---- section headings over the chart and the panel ----
    S = lay_d["section"]
    for r in range(S, lay_d["chart_end"] + 1):
        ws.row_dimensions[r].height = 16.5
    WIN = "$M$%d" % lay_d["window"]
    ws.merge_cells(start_row=S, start_column=2, end_row=S, end_column=11)
    ws.cell(S, 2, '="Every %s over the five rating zones · "&LOWER(%s)' % (p2.lower(), WIN))
    ws.cell(S, 12, "Where each rating begins")
    for c1, c2 in ((2, 11), (12, 17)):
        ws.cell(S, c1).font = F_HEAD
        ws.cell(S, c1).alignment = Alignment(vertical="bottom")
        _rule(ws, S, c1, c2, Side(style="medium", color=K.INK))

    # ---- chart helpers (hidden), one row per quarter ----
    cols_ = {}
    nxt = [CH]

    def col(key, header):
        cols_[key] = nxt[0]
        ws.cell(1, nxt[0], header)
        nxt[0] += 1
        return cols_[key]

    for key, head in (("q", "Quarter"), ("cat", "Label"), ("raw", "History, every quarter"), ("kept", "Kept"),
                      ("rate", "Rating of the quarter kept"), ("lo", "Left out"), ("left", "Left-out stretch")):
        col(key, head)
    for k, v in enumerate(third):
        col("pick%d" % k, v)
    for k, v in enumerate(third):
        col("over%d" % k, v)
    for key, head in (("base", "base"), ("z1", "1 Low"), ("z2", "2 Moderate-Low"), ("z3", "3 Moderate"),
                      ("z4", "4 Moderate-High"), ("z5", "5 High")):
        col(key, head)
    for j in range(4):
        col("lab%d" % j, "")
    for key, head in (("num", "drawn and shown, numbers only"), ("low", "drawn and shown, lowest"),
                      ("any", "drawn"), ("fit", "first, count, last, label every"), ("ft", "floor, top"),
                      ("zero", "Zero, a measure without a floor")):
        col(key, head)
    # The quarters a reporting change took effect, per row of the table (any
    # of its sources' files names it), and the marker for the row shown.
    if len(quarters) != n_quarters:
        raise ValueError("quarters must be the Data tab's %d quarters, not %d" % (n_quarters, len(quarters)))
    missing = [lbl for lbl in labels if lbl not in changes]
    if missing:
        raise ValueError("changes must give every series its reporting change quarters (an empty set for none); "
                         "missing for %s" % ", ".join(missing))
    took = [set().union(*(changes[lbl] for lbl in by_pair[pr].values())) for pr in pairs]
    for i, pr in enumerate(pairs):
        col("chg%d" % i, "Reporting change took effect: %s - %s" % pr)
    col("chg", "Reporting change")
    cl = {k: L(v) for k, v in cols_.items()}
    FIT, FIT_N, FIT_LAST, SKIP = ("$%s$%d" % (cl["fit"], r) for r in (2, 3, 4, 5))
    FLOOR, TOPV = "$%s$2" % cl["ft"], "$%s$3" % cl["ft"]
    rng_ = lambda k: "$%s$2:$%s$%d" % (cl[k], cl[k], q_last)              # noqa: E731
    vals = "Data!$B$2:$%s$%d" % (d_kept_last, q_last)
    raw_of = 'MATCH(%s,Data!$B$1:$%s$1,0)' % (LBL, d_raw_last)
    span = 'IF({w}="{a}",{q},VALUE(MID({w},6,3)))'.format(w=WIN, a=WINDOWS[3], q=q_last)
    clip = lambda e: "MIN(MAX(%s,%s),%s)" % (e, FLOOR, TOPV)                # noqa: E731
    edges = [FLOOR] + [clip(x) for x in LN] + [TOPV]
    pick_cols = [cl["pick%d" % k] for k in range(len(third))]
    over_cols = [cl["over%d" % k] for k in range(len(third))]
    if higher:
        ge_w, ge_b = "<=", "<"                           # a line at or below the value: the value is at least that rating
    else:
        ge_w, ge_b = ">=", ">"
    for r in range(2, q_last + 1):
        x = "%s%d" % (cl["kept"], r)
        ws.cell(r, cols_["q"], "=Data!$A%d" % r)
        ws.cell(r, cols_["cat"], '=IF(AND({r}>={f},{r}<={l},MOD({l}-{r},{s})=0),{q}{r},"")'
                .format(r=r, f=FIT, l=FIT_LAST, s=SKIP, q=cl["q"]))
        ws.cell(r, cols_["raw"], '=IF(NOT({h}),NA(),IFERROR(IF(ISNUMBER(INDEX({v},{i},{o})),INDEX({v},{i},{o}),NA()),'
                                 'NA()))'.format(h=HAS, v=vals, i=r - 1, o=raw_of))
        ws.cell(r, cols_["kept"], '=IF(OR(NOT({h}),NOT(ISNUMBER({k}))),"",IFERROR(IF(ISNUMBER(INDEX({v},{i},{k})),'
                                  'INDEX({v},{i},{k}),""),""))'.format(h=HAS, v=vals, i=r - 1, k=KEPT_OF))
        cmp_ = lambda op: "+".join("IF(%s%s%s,1,0)" % (ln, op, x) for ln in LN)   # noqa: E731
        ws.cell(r, cols_["rate"], '=IF(OR(NOT({ok}),{rf}<>"",NOT(ISNUMBER({x}))),"",IF({fz},IF({x}<=0,1,0),0)'
                                  '+IF(AND({fz},{x}<=0),0,1+IF({rule}="worse",{w},{b})))'
                .format(ok=lines_ok, rf=REFUSAL, x=x, fz=FZ, rule=RULE, w=cmp_(ge_w),
                        b=cmp_(ge_b)))
        ws.cell(r, cols_["lo"], '=IF(AND(ISNUMBER({h}{r}),{k}{r}=""),1,0)'.format(h=cl["raw"], k=cl["kept"], r=r))
        nb = ["%s%d" % (cl["lo"], rr) for rr in (r - 1, r + 1) if 2 <= rr <= q_last]
        ws.cell(r, cols_["left"], '=IF(AND(ISNUMBER({h}{r}),OR({lo}{r}=1{nb})),{h}{r},NA())'.format(
            h=cl["raw"], r=r, lo=cl["lo"], nb="".join("," + c_ + "=1" for c_ in nb)))
        for k, v in enumerate(third):
            ws.cell(r, cols_["pick%d" % k], '=IF(AND({h},{s}="{v}",ISNUMBER({x})),{x},NA())'
                    .format(h=HAS, s=SRC, v=_q(v), x=x))
            lab = "$%s$%d" % (hc, SRC_TOP + k)
            oc = 'MATCH(%s,Data!$B$1:$%s$1,0)' % (lab, d_raw_last)
            ws.cell(r, cols_["over%d" % k], '=IF(AND({o},$Q${t}="Yes",{s}<>"{v}"),IFERROR(IF(ISNUMBER(INDEX({vv},'
                                             '{i},{oc})),INDEX({vv},{i},{oc}),NA()),NA()),NA())'
                    .format(o=ONE, t=lay_d["compare_first"] + k, s=SRC, v=_q(v), vv=vals, i=r - 1, oc=oc))
        inwin = "AND({r}>={f},{r}<={l})".format(r=r, f=FIT, l=FIT_LAST)
        refs = ["%s%d" % (c_, r) for c_ in [cl["raw"]] + over_cols]
        ws.cell(r, cols_["num"], '=IF(AND({w},COUNT({c})>0),MAX({m}),"")'.format(
            w=inwin, c=",".join(refs), m=",".join("IF(ISNUMBER(%s),%s,-1E+300)" % (y, y) for y in refs)))
        ws.cell(r, cols_["low"], '=IF(AND({w},COUNT({c})>0),MIN({m}),"")'.format(
            w=inwin, c=",".join(refs), m=",".join("IF(ISNUMBER(%s),%s,1E+300)" % (y, y) for y in refs)))
        ws.cell(r, cols_["base"], "=%s" % FLOOR)
        # Where the axis crosses: a measure without a floor (a gap) can be
        # either side of zero, so zero is drawn, SLATE.
        ws.cell(r, cols_["zero"], "=IF(AND(%s,NOT(%s),%s),0,NA())" % (HAS, FZ, inwin))
        for k in range(5):
            ws.cell(r, cols_["z%d" % (k + 1)], "=IF(%s,MAX(%s-%s,0),NA())" % (lines_ok, edges[k + 1], edges[k]))
        for j in range(4):
            ws.cell(r, cols_["lab%d" % j], '=IF(AND({r}={l},{ok},{x}>={f},{x}<={t}),{x},NA())'
                    .format(r=r, l=FIT_LAST, ok=lines_ok, x=LN[j], f=FLOOR, t=TOPV))
        any_ = ",".join("ISNUMBER(%s%d)" % (c_, r) for c_ in [cl["raw"]] + over_cols)
        ws.cell(r, cols_["any"], '=IF(OR(%s),%d,"")' % (any_, r))
        q_r = quarters[r - 2]
        for i, qs in enumerate(took):
            ws.cell(r, cols_["chg%d" % i], 1 if q_r in qs else None)
        ws.cell(r, cols_["chg"], '=IF(AND({one},{w}),IF(INDEX(${a}{r}:${b}{r},MATCH(1,{sh},0))=1,{top},NA()),NA())'
                .format(one=ONE, w=inwin, a=cl["chg0"], b=cl["chg%d" % (len(pairs) - 1)], r=r, sh=SHOWN, top=TOPV))
    for j in range(4):
        ws.cell(1, cols_["lab%d" % j], '=IF(ISNUMBER({x}),"{k} from "&TEXT({x},"0.00"),"")'.format(x=LN[j], k=j + 2))
    anyr = rng_("any")
    # The chart draws from the first quarter any line has to the last, inside
    # the window. An axis cannot follow a cell, but a named range can (the
    # firm, 14 Oct 2026: "the axis should adjust to fit").
    ws.cell(2, cols_["fit"], "=IF(COUNT({a})=0,2,MAX(MIN({a}),MAX({a})-{s}+1))".format(a=anyr, s=span))
    ws.cell(3, cols_["fit"], "=IF(COUNT({a})=0,{n},MAX({a})-{f}+1)".format(a=anyr, n=q_last - 1, f=FIT))
    ws.cell(4, cols_["fit"], "=%s+%s-1" % (FIT, FIT_N))
    ws.cell(5, cols_["fit"], '=IF({w}="{e}",12,IF({s}<=20,2,IF({s}<=48,4,8)))'.format(w=WIN, e=WINDOWS[3], s=span))
    num, lows = rng_("num"), rng_("low")
    # The zones' base: 0, or the lowest value drawn when a gap runs below
    # it. Taking it down to a whole step of the range was tried, so the base
    # would sit at the axis minimum: Excel then took its axis a step lower
    # still (seen in Excel, 19 Oct 2026), and the axis is Excel's to set.
    ws.cell(2, cols_["ft"], "=MIN(0,MIN(%s))" % lows)
    # The top fits what is drawn, and takes in a line that sits within 60% of
    # the drawn range above it, so its zone and label show.
    reach = ",".join('IF(AND(ISNUMBER({x}),{x}<=MAX({n})+0.6*(MAX({n})-MIN({lo}))),{x},0)'
                     .format(x=x, n=num, lo=lows) for x in LN)
    ws.cell(3, cols_["ft"], "=IF(MAX(%s)>0,MAX(MAX(%s),%s)*1.08,1)" % (num, num, reach))

    def name_for(col_, nm):
        ws.defined_names[nm] = DefinedName(nm, attr_text="OFFSET(%s!$%s$1,%s-1,0,%s,1)" % (
            TITLE, L(col_), "%s!%s" % (TITLE, FIT), "%s!%s" % (TITLE, FIT_N)))
        return "%s!%s" % (TITLE, nm)

    cats = name_for(cols_["cat"], "dq_quarter")

    def series(key, nm, title=None, tx_ref=None):
        s_ = Series(val=NumDataSource(numRef=NumRef(f=name_for(cols_[key], nm))),
                    tx=SeriesLabel(strRef=StrRef(f=tx_ref)) if tx_ref else SeriesLabel(v=title))
        s_.cat = AxDataSource(strRef=StrRef(f=cats))
        s_.smooth = False
        s_.marker.symbol = "none"
        return s_

    from .assess_tab import _ln, _text                       # the shared chart styling
    line = LineChart()
    idx = 0
    over = []
    for k, v in enumerate(third):
        s_ = series("over%d" % k, "dq_over%d" % (k + 1), v)
        s_.graphicalProperties.line = _ln(colors[v], 1.5, "dash")
        over.append(s_)
    left = series("left", "dq_left", "Left out")
    left.graphicalProperties.line = _ln(K.STONE, 2.5)
    picks = []
    for k, v in enumerate(third):
        s_ = series("pick%d" % k, "dq_pick%d" % (k + 1), "%s (lines set from it)" % v)
        s_.graphicalProperties.line = _ln(colors[v], 2.5)
        picks.append(s_)
    labs = []
    for j in range(4):
        s_ = series("lab%d" % j, "dq_label%d" % (j + 2), tx_ref="%s!$%s$1" % (TITLE, cl["lab%d" % j]))
        s_.graphicalProperties.line.noFill = True
        s_.dLbls = DataLabelList(showSerName=True, showVal=False, showLegendKey=False, showCatName=False,
                                 showPercent=False, showLeaderLines=False, dLblPos="r", txPr=_text(9, K.SLATE))
        labs.append(s_)
    # A diamond along the top of the zones in each quarter a reporting change
    # took effect for the row shown (the firm, 16 Oct 2026: "Definitely mark
    # reporting changes.").
    mark = series("chg", "dq_change", "Reporting change")
    mark.graphicalProperties.line.noFill = True
    mark.marker.symbol = "diamond"
    mark.marker.size = 7
    from openpyxl.chart.shapes import GraphicalProperties as _GP
    mark.marker.graphicalProperties = _GP(solidFill=K.INK)
    mark.marker.graphicalProperties.line.solidFill = K.INK
    zero = series("zero", "dq_zero", "Zero")
    zero.graphicalProperties.line = _ln(K.SLATE, 0.75)
    for s_ in [zero] + over + [left] + picks + labs + [mark]:
        s_.idx = s_.order = idx
        idx += 1
        line.series.append(s_)
    area = AreaChart()
    area.grouping = "stacked"
    for k, key in enumerate(["base", "z1", "z2", "z3", "z4", "z5"]):
        s_ = series(key, "dq_" + ("base" if k == 0 else "zone%d" % k), "zone" if k else "base")
        s_.idx = s_.order = idx
        idx += 1
        if k == 0:
            s_.graphicalProperties.noFill = True
        else:
            s_.graphicalProperties.solidFill = K.ZONE_FILL[k - 1]
        s_.graphicalProperties.line.noFill = True
        area.series.append(s_)
    for ax in (line.x_axis, line.y_axis):
        ax.delete = False
        ax.majorGridlines = None
        ax.txPr = _text(9, K.SLATE)
        from openpyxl.chart.shapes import GraphicalProperties
        ax.spPr = GraphicalProperties(ln=_ln(K.STONE, 0.75))
    line.y_axis.number_format = "0.00"
    line.y_axis.majorTickMark = "out"
    line.x_axis.tickLblSkip = 1                    # the labels are thinned in the helper, by the window
    line.x_axis.tickMarkSkip = 1
    line.x_axis.tickLblPos = "low"
    line.x_axis.noMultiLvlLbl = True
    line.legend = None                             # the key is the panel's list of sources, in their colours
    line += area
    line.visible_cells_only = False                # its data sits in hidden columns
    line.roundedCorners = False
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.drawing.line import LineProperties
    line.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))
    # Room on the right for the labels on each rating's line.
    line.plot_area.layout = Layout(manualLayout=ManualLayout(layoutTarget="inner", xMode="edge", yMode="edge",
                                                             x=0.06, y=0.03, w=0.83, h=0.86))
    from .assess_tab import _place
    _place(ws, line, 2, lay_d["chart_top"], 12, lay_d["chart_end"] + 1)
    # Under the chart, the pack line: which peers the peer group's line is
    # summed over this quarter. Only where the peer tabs define it.
    if PACK_LINE in wb.defined_names:
        c_ = ws.cell(lay_d["pack_line"], 2, "=" + PACK_LINE)
        c_.font = F_NOTE
        c_.alignment = Alignment(vertical="center")
        ws.row_dimensions[lay_d["pack_line"]].height = 15

    # ---- the panel, right: where each rating begins ----
    rh = lay_d["ratings_head"]
    for c, t_ in zip(range(12, 17), ("Rating", "Begins at" + (" (%s)" % unit if unit else ""), "Quarters kept",
                                     "Share", "Latest")):
        cell = ws.cell(rh, c, t_)
        cell.font = F_LAB
        cell.alignment = Alignment(horizontal="right" if c in (13, 14, 15) else "left", vertical="center")
    _rule(ws, rh, 12, 17, Side(style="thin", color=K.STONE))
    rate_r, kept_r = rng_("rate"), rng_("kept")
    lead_q = 'IFERROR(INDEX(%s,%s),"")' % (th_col("quarter"), LEADQ)
    for k in range(5):
        r = lay_d["ratings_first"] + k
        c_ = ws.cell(r, 12, "%d %s" % (k + 1, RATINGS[k]))
        c_.font = F_BOLD
        c_.fill = fill(SCALE[k])
        if k == 0:
            # With a floor, 1 Low begins at it; without one (a gap) it has
            # no bottom, so it reads as what it is below (or above).
            begins, side = ("the bottom", "below") if higher else ("the top", "above")
            ws.cell(r, 13, '=IF({ok},IF({fz},"{b}","{s} "&TEXT({l2},"0.00")),"")'.format(
                ok=lines_ok, fz=FZ, b=begins, s=side, l2=LN[0]))
        else:
            ws.cell(r, 13, '=IF(ISNUMBER(%s),%s,"")' % (LN[k - 1], LN[k - 1]))
        ws.cell(r, 14, '=IF(OR(NOT({h}),{rf}<>""),"",COUNTIF({rr},{k}))'.format(h=HAS, rf=REFUSAL, rr=rate_r,
                                                                              k=k + 1))
        ws.cell(r, 15, '=IF(OR(NOT({h}),{rf}<>"",COUNT({kr})=0),"",COUNTIF({rr},{k})/COUNT({kr}))'
                .format(h=HAS, rf=REFUSAL, rr=rate_r, k=k + 1, kr=kept_r))
        # The lead source's latest quarter, on the lines picked.
        ws.cell(r, 16, '=IF({lk}={k},"◀ {n} "&{q},"")'.format(lk=LEADK, k=k + 1, n=_q(lead), q=lead_q))
        ws.cell(r, 13).font = F_BOLD
        ws.cell(r, 13).number_format = "0.00"
        ws.cell(r, 13).alignment = Alignment(horizontal="right")
        ws.cell(r, 14).font = F_BODY
        ws.cell(r, 15).font = F_BODY
        ws.cell(r, 15).number_format = "0%"
        ws.cell(r, 16).font = F_BOLD
        for c in range(12, 18):
            ws.cell(r, c).border = Border(bottom=HAIR)

    # ---- every source on these lines ----
    st = lay_d["sources_title"]
    ws.cell(st, 12, "Every %s on these lines" % p2.lower()).font = F_HEAD
    ws.cell(st, 12).alignment = Alignment(vertical="bottom")
    _rule(ws, st, 12, 17, Side(style="medium", color=K.INK))
    sh = lay_d["sources_head"]
    for c, t_ in ((12, "%s (line color)" % p2), (13, "Rating on these lines"), (14, "Latest"), (15, "Quarter"),
                  (16, "Quarters kept"), (17, "On chart")):
        cell = ws.cell(sh, c, t_)
        cell.font = F_LAB
        cell.alignment = Alignment(horizontal="right" if c in (14, 16) else "left", vertical="center",
                                   wrap_text=False)
    _rule(ws, sh, 12, 17, Side(style="thin", color=K.STONE))
    kept_hdr = "Data!$B$1:$%s$1" % d_kept_last
    rows = {}
    for i, v in enumerate(third):
        r = lay_d["compare_first"] + i
        rows[v] = r
        sr_ = src_rows[v]
        a_, b_, x_, k_ = ("$%s$%d" % (L(H + j), sr_) for j in range(4))
        # A source with no series for the row shown is blank there, its name too (the analyst, 20 Oct 2026,
        # on the Philadelphia Fed grayed on 55 rows of 56: "What do we have this for if we don't have it?").
        nm = ws.cell(r, 12, '=IF(AND({o},{b}=""),"",IF({s}="{v}","━ ","╍ ")&"{v}")'.format(o=ONE, b=b_, s=SRC,
                                                                                         v=_q(v)))
        nm.font = Font(name="Calibri", size=11, bold=True, color=colors[v])
        ws.cell(r, 13, '=IF(NOT({o}),"",IF({b}="","",IF({k}="",IF({s}="","{n}",'
                       '"No rating"),{k}&" "&CHOOSE({k},"{r0}","{r1}","{r2}","{r3}","{r4}"))))'
                .format(o=ONE, b=b_, k=k_, s=SRC, n=NO_SERIES, r0=RATINGS[0], r1=RATINGS[1],
                        r2=RATINGS[2], r3=RATINGS[3], r4=RATINGS[4])).font = F_BOLD
        c_ = ws.cell(r, 14, '=IF(ISNUMBER({x}),{x},"")'.format(x=x_))
        c_.number_format = "0.00"
        c_.font = F_BODY
        c_.alignment = Alignment(horizontal="right")
        ws.cell(r, 15, '=IF({b}="","",IFERROR(INDEX({q},{b})&"",""))'.format(b=b_, q=th_col("quarter"))
                ).font = F_SLATE
        ws.cell(r, 16, '=IF({b}="","",SUMPRODUCT(ISNUMBER({v})*({h}={a}&", kept")))'
                .format(a=a_, b=b_, v=vals, h=kept_hdr)).font = F_BODY
        on = ws.cell(r, 17, "Yes")
        on.fill = fill(K.INPUT)
        on.border = BOX
        on.font = F_BOLD
        for c in range(12, 17):
            ws.cell(r, c).border = Border(bottom=HAIR)
        # The source the lines are set from is the solid line already: its switch reads Lines from it.
        ws.conditional_formatting.add("Q%d" % r, Rule(type="expression", formula=['AND(%s,%s="")' % (ONE, b_)],
                                                      stopIfTrue=True, dxf=DifferentialStyle(
                                                          numFmt=NumberFormat(numFmtId=191, formatCode=';;;'),
                                                          fill=fill(K.PAPER), border=Border(
                                                              *(Side(style="thin", color=K.PAPER),) * 4))))
        ws.conditional_formatting.add("Q%d" % r, Rule(type="expression", formula=['%s="%s"' % (SRC, _q(v))],
                                                      stopIfTrue=True, dxf=DifferentialStyle(
                                                          numFmt=NumberFormat(numFmtId=190,
                                                                              formatCode=';;;"Lines from it"'),
                                                          font=Font(bold=False, color=K.SLATE), fill=fill(K.PAPER))))
    cf, cl_ = lay_d["compare_first"], lay_d["compare_first"] + len(third) - 1
    for k in range(5):
        ws.conditional_formatting.add("M%d:M%d" % (cf, cl_), FormulaRule(
            formula=['LEFT($M%d,1)="%d"' % (cf, k + 1)], fill=fill(SCALE[k]), stopIfTrue=True))
    ws.conditional_formatting.add("M%d:M%d" % (cf, cl_), FormulaRule(
        formula=['$M%d="No rating"' % cf], fill=fill(K.CANVAS), font=Font(bold=True, color=K.CRIMSON)))
    dv_on = DataValidation(type="list", formula1='"Yes,No"', showErrorMessage=True, errorTitle="On chart",
                           error="Yes or No.")
    ws.add_data_validation(dv_on)
    dv_on.add("Q%d:Q%d" % (cf, cl_))
    if compare:
        a, b = compare
        pts = "percentage points" if unit.strip() == "%" else "points"
        ws.merge_cells(start_row=hr, start_column=12, end_row=hr, end_column=17)
        c_ = ws.cell(hr, 12, '=IF(AND({o},ISNUMBER(N{x}),ISNUMBER(N{y})),"{a} is "&TEXT(ABS(N{x}-N{y}),"0.00")'
                             '&" {p} "&IF(N{x}>=N{y},"higher","lower")&" than {b}.","")'
                     .format(o=ONE, x=rows[a], y=rows[b], a=_q(a), b=_q(b), p=pts))
        c_.font = F_SLATE
        c_.alignment = Alignment(vertical="center", indent=1, shrink_to_fit=True)

    # ---- what the chart shows: only the picture ----
    wr = lay_d["window"]
    ws.cell(wr, 12, "Chart shows").font = F_LAB
    win = ws.cell(wr, 13, DEFAULT_WINDOW)
    win.fill = fill(K.INPUT)
    win.border = BOX
    win.font = F_BOLD
    dv_w = DataValidation(type="list", formula1='"%s"' % ",".join(WINDOWS), showErrorMessage=True,
                          errorTitle="Chart shows", error="Pick one from the list.")
    ws.add_data_validation(dv_w)
    dv_w.add("M%d" % wr)
    ws.cell(wr, 14, "The lines are set from every quarter kept, whatever the chart shows.").font = F_NOTE

    # ---- what the lines rest on ----
    lr = lay_d["lines_label"]
    ws.cell(lr, 12, '="What the lines rest on: "&IF(%s="","no %s picked yet",%s&"\'s history")&", quarters kept"'
            % (SRC, p2.lower(), SRC)).font = F_LAB
    _rule(ws, lr, 12, 17, Side(style="thin", color=K.STONE))
    worst_q = 'IFERROR(INDEX({q},MATCH({w},{k},0)),"")'.format(q=rng_("q"), w=th_("worst"), k=kept_r)
    for r, label, key, note in (
            (lay_d["median"], "Median kept", "median",
             '=IF(NOT({h}),"",COUNT({k})&" of the "&COUNT({raw})&" quarters on file are kept.")'
             .format(h=HAS, k=kept_r, raw=rng_("raw"))),
            (lay_d["move"], "Typical yearly move", "move",
             '=IF(NOT({h}),"","Lines 2 and 3 are set as multiples of it.")'.format(h=HAS)),
            (lay_d["worst"], "Worst quarter kept", "worst",
             '=IF(NOT({h}),"","Kept in "&{q}&". High must begin at or {d} it.")'
             .format(h=HAS, q=worst_q, d="below" if higher else "above"))):
        ws.cell(r, 12, label).font = F_BODY
        v_ = ws.cell(r, 13, '=IF(NOT({h}),"",IFERROR({x},""))'.format(h=HAS, x=th_(key)))
        v_.font = F_BOLD
        v_.number_format = "0.00"
        v_.alignment = Alignment(horizontal="right")
        ws.cell(r, 14, note).font = F_SLATE
        for c in range(12, 18):
            ws.cell(r, c).border = Border(bottom=HAIR)

    # ---- what each source's own history would give, on the same settings ----
    gt, gh = lay_d["gives_title"], lay_d["gives_head"]
    ws.cell(gt, 12, "What each %s's own history would give" % p2.lower()).font = F_HEAD
    ws.cell(gt, 12).alignment = Alignment(vertical="bottom")
    _rule(ws, gt, 12, 17, Side(style="medium", color=K.INK))
    ws.row_dimensions[gt].height = 16.5
    for c, t_ in ((12, p2), (13, "2 Moderate-Low"), (14, "3 Moderate"), (15, "4 Moderate-High"), (16, "5 High"),
                  (17, "Worst kept")):
        cell = ws.cell(gh, c, t_)
        cell.font = F_LAB
        # "4 Moderate-High" is wider than O (90 px): two lines, never shrunk.
        cell.alignment = Alignment(horizontal="left" if c == 12 else "right", vertical="bottom", wrap_text=True)
    ws.row_dimensions[gh].height = 30
    _rule(ws, gh, 12, 17, Side(style="thin", color=K.STONE))
    gives = {}
    for i, v in enumerate(third):
        r = lay_d["gives_first"] + i
        gives[v] = r
        b_ = "$%s$%d" % (L(H + 1), src_rows[v])
        nm = ws.cell(r, 12, '=IF(AND({o},{b}=""),"","{v}")'.format(o=ONE, b=b_, v=_q(v)))
        nm.font = Font(name="Calibri", size=11, bold=True, color=colors[v])
        refused_ = 'INDEX(%s,%s)<>""' % (th_col("refusal"), b_)
        for c, key in ((13, "l2"), (14, "l3"), (15, "l4"), (16, "l5"), (17, "worst")):
            if c == 13:
                f = ('=IF({b}="","",IF({rf},"Refused",IFERROR(INDEX({x},{b})+0,"")))'
                     .format(b=b_, rf=refused_, x=th_col(key)))
            elif key == "worst":
                f = '=IF({b}="","",IFERROR(INDEX({x},{b})+0,""))'.format(b=b_, x=th_col(key))
            else:
                f = '=IF({b}="","",IF({rf},"",IFERROR(INDEX({x},{b})+0,"")))'.format(b=b_, rf=refused_,
                                                                                      x=th_col(key))
            c_ = ws.cell(r, c, f)
            c_.number_format = "0.00"
            c_.font = F_BODY
            c_.alignment = Alignment(horizontal="right")
        for c in range(12, 18):
            ws.cell(r, c).border = Border(bottom=HAIR)
        ws.row_dimensions[r].height = 16.5
    g1, g2 = lay_d["gives_first"], lay_d["gives_first"] + len(third) - 1
    ws.conditional_formatting.add("M%d:M%d" % (g1, g2), FormulaRule(
        formula=['$M%d="Refused"' % g1], font=Font(bold=True, color=K.CRIMSON)))

    # ---- Periods left out: as many per row as needed, each read by Assess's row of the same number ----
    lt = lay_d["lo_title"]
    ws.cell(lt, 2, "Periods left out").font = F_HEAD
    _rule(ws, lt, 2, 17, Side(style="medium", color=K.INK))
    lh = lay_d["lo_head"]
    for c, t_ in ((2, p0), (3, p1), (4, "From"), (5, "To"), (6, "Why"), (12, "Status")):
        ws.cell(lh, c, t_).font = F_LAB
        ws.cell(lh, c).alignment = Alignment(vertical="bottom")
    _rule(ws, lh, 2, 17, Side(style="thin", color=K.STONE))
    # the two lists the first columns pick from, hidden beside the helpers
    lists = {}
    for i, vals in enumerate((list(dict.fromkeys(a for a, _ in pairs)), list(dict.fromkeys(b for _, b in pairs)))):
        c = H + 3 + i
        for j, v in enumerate(vals):
            assert ws.cell(LO1 + j, c).value is None, "Periods left out's lists overlap a helper"
            ws.cell(LO1 + j, c, v)
        lists[i] = "=$%s$%d:$%s$%d" % (L(c), LO1, L(c), LO1 + len(vals) - 1)
    dvs = [DataValidation(type="list", formula1=f_, showErrorMessage=True, errorTitle=t_, error="Pick one from the list.")
           for f_, t_ in ((lists[0], p0), (lists[1], p1), ("=Data!$A$2:$A$%d" % q_last, "Quarter"))]
    for dv_ in dvs:
        ws.add_data_validation(dv_)
    akey = 'IFERROR(INDEX({k},MATCH(1,{s},0)),"")'.format(k=rng("Key"), s=SHOWN)
    z_, aa_, ok_ = (L(A_HC + 14 + i) for i in range(3))
    for k in range(LO_N):
        r, ar = LO1 + k, LO_TOP + k
        for c in range(2, 7):
            c_ = ws.cell(r, c)
            c_.fill, c_.border = fill(K.INPUT), BOX
            c_.font = F_BODY if c == 6 else F_BOLD
            c_.alignment = Alignment(vertical="center")
        ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=11)
        dvs[0].add("B%d" % r)
        dvs[1].add("C%d" % r)
        dvs[2].add("D%d:E%d" % (r, r))
        for c, f in ((H, '=IF(Assess!${o}${a}=1,Assess!${t}${a}-Assess!${f}${a}+1,0)'),
                     (H + 1, '=IF(Assess!${o}${a}=1,1,0)'),
                     (H + 2, '=IF(AND(${w}{r}=1,$B{r}&" · "&$C{r}={k}),{p}$D{r}&" to "&$E{r}&IF(TRIM($F{r})="","",'
                             '", "&TRIM($F{r})),{q})')):
            assert ws.cell(r, c).value is None, "Periods left out's helpers overlap another"
            prev = "$%s$%d" % (L(H + 2), r - 1)
            ws.cell(r, c, f.format(o=ok_, a=ar, t=aa_, f=z_, w=L(H + 1), r=r, k=akey,
                                   p='IF(%s="","",%s&"; ")&' % (prev, prev) if k else "", q=prev if k else '""'))
        ws.merge_cells(start_row=r, start_column=12, end_row=r, end_column=17)
        st = ws.cell(r, 12, '=IF(AND($B{r}="",$C{r}="",$D{r}="",$E{r}="",TRIM($F{r})=""),"",IF(ISNA(MATCH($B{r}&" · "&$C{r},'
                            '{key},0)),"Pick a {a} and a {b} from the lists",IF(INDEX({lf},MATCH($B{r}&" · "&$C{r},{key},'
                            '0))="","Pick a {d} under {lfn} on its row first",Assess!$T${ar})))'
                     .format(r=r, ar=ar, key=rng("Key"), lf=rng(LINES_FROM), a=p0.lower(), b=p1.lower(),
                             d=p2.lower(), lfn=LINES_FROM))
        st.font = F_SLATE
        st.alignment = Alignment(vertical="center", shrink_to_fit=True)
        ws.row_dimensions[r].height = 18
    ws.conditional_formatting.add("L%d:Q%d" % (LO1, LO9), FormulaRule(
        formula=['ISNUMBER(SEARCH("refused",$L%d))' % LO1], font=Font(bold=True, color=K.CRIMSON)))

    # ---- below the fold: the evidence, and what each setting does ----
    hi = lay_d["history"]
    ws.cell(hi, 2, "What the history suggests: keep every period, or leave one out?").font = F_HEAD
    _rule(ws, hi, 2, 17, Side(style="medium", color=K.INK))
    srow = "MATCH(%s,Assess!$N$%d:$N$%d,0)" % (LBL, SET_TOP, SET_TOP + n - 1)
    for i, (t_, col_) in enumerate(EVIDENCE_COLS):
        r = lay_d["evidence"] + i
        ws.cell(r, 2, t_).font = F_LAB
        c_ = ws.cell(r, 4, '=IF(NOT(%s),"",IFERROR(INDEX(Assess!$%s$%d:$%s$%d,%s),""))'
                     % (HAS, col_, SET_TOP, col_, SET_TOP + n - 1, srow))
        c_.font = F_BOLD if i == 0 else F_BODY
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=17)
        c_.alignment = Alignment(vertical="center", shrink_to_fit=True)
    r = lay_d["left_now"]
    ws.cell(r, 2, "Left out now").font = F_LAB
    said = LO_SAID
    c_ = ws.cell(r, 4, '=IF(NOT({o}),"",IF({s}="","No period is left out; every quarter is kept.",'
                       '"Left out: "&{s}&". The chart draws these quarters in gray; the lines are set without them."))'
                 .format(o=ONE, s=said))
    c_.font = F_BODY
    ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=17)
    c_.alignment = Alignment(vertical="center", shrink_to_fit=True)
    for r in range(lay_d["evidence"], lay_d["left_now"] + 1):
        _rule(ws, r, 2, 17, HAIR)

    se = lay_d["settings"]
    ws.cell(se, 2, "What each setting does when you raise it").font = F_HEAD
    _rule(ws, se, 2, 17, Side(style="medium", color=K.INK))
    for i, (name, said) in enumerate((
            ("Width of Moderate", "More quarters rate 3 Moderate."),
            ("Moderate-Low begins", "Fewer quarters rate 1 Low."),
            ("How rare High is (z)", "Fewer quarters rate 5 High. A z of 2.5 is rare; 3.5 is the usual line "
                                     "for an outlier."),
            ("On a line, rate it", "With worse, a value exactly on a line takes the worse rating."))):
        r = se + 1 + i
        ws.cell(r, 2, name).font = F_BOLD
        ws.cell(r, 5, said).font = F_BODY
        _rule(ws, r, 2, 17, HAIR)
    # What fits the history the lines are set from: every setting's range at
    # once, from the same median, yearly move, spread and worst quarter the
    # lines use (the analyst, 15 Oct 2026: "adjusting those widths should
    # somehow work in such a way that it would bring the others into an
    # acceptable range"). Nothing is changed for the analyst; each line says
    # whether the setting typed fits. The ranges are the Check's own rules:
    # Moderate-Low further out than Moderate, line 2 above zero (when the
    # floor is at zero), High beyond Moderate-High and within the worst kept.
    ws.cell(se, 12, "What fits the history the lines are set from").font = F_HEAD
    hw_, ls_, z_ = shown("Width of Moderate"), shown("Moderate-Low begins"), shown("How rare High is (z)")
    med, mv, sp, wo = th_("median"), th_("move"), th_("spread"), th_("worst")
    sg = "" if higher else "-"
    zmax = "{sg}({w}-{m})/{s}".format(sg=sg, w=wo, m=med, s=sp)
    zmin = "{h}*{v}/{s}".format(h=hw_, v=mv, s=sp)
    lsmax = "{m}/{v}".format(m=med, v=mv)
    floor_ok = "AND(%s,TRUE)" % FZ
    say_ = lambda ok: 'IF({ok},"It fits.","It does not fit.")'.format(ok=ok)        # noqa: E731
    need = '"Pick a %s under %s to see what fits."' % (p2.lower(), LINES_FROM)
    fits = (
        '"Fits below "&TEXT({ls},"0.00")&", where Moderate-Low begins. "&{say}'
        .format(ls=ls_, say=say_("%s<%s" % (hw_, ls_))),
        ('"Fits above "&TEXT({hw},"0.00")&IF({fl},", and below "&TEXT({mx},"0.00")&" so line 2 stays above zero",'
         '"")&". "&{say}').format(hw=hw_, fl=floor_ok, mx=lsmax,
                                  say=say_("AND({ls}>{hw},OR(NOT({fl}),{ls}<{mx}))".format(
                                      ls=ls_, hw=hw_, fl=floor_ok, mx=lsmax))),
        ('"Fits above "&TEXT({mn},"0.00")&" (High beyond Moderate-High) and up to "&TEXT({mx},"0.00")&'
         '" (some quarter kept can rate High). "&{say}').format(
            mn=zmin, mx=zmax, say=say_("AND({z}>{mn},{z}<={mx})".format(z=z_, mn=zmin, mx=zmax))),
        '"Either fits."')
    for i, f in enumerate(fits):
        c_ = ws.cell(se + 1 + i, 12, '=IF(NOT({one}),"",IF(NOT({h}),{need},IFERROR({f},"")))'.format(
            one=ONE, h=HAS, need=need, f=f))
        c_.font = F_BODY
    nt = lay_d["notes"]
    ws.cell(nt, 2, "The solid line is the %s the lines are set from. A dashed line is another %s switched on under "
                   "On chart, in the color of its name. A gray stretch is a period left out of the history the lines "
                   "are set from: it is drawn, and it does not set the lines." % (p2.lower(), p2.lower())
            ).font = F_NOTE
    ws.cell(nt + 1, 2, "The settings apply to every %s's history: the lines picked, and what each %s's own history "
                       "would give. The shading runs from 1 Low to 5 High." % (p2.lower(), p2.lower())).font = F_NOTE
    ws.cell(nt + 2, 2, "The chart starts at the first quarter any line has, within the window set under Chart shows.%s "
                       "Every term is defined on the Glossary tab."
            % (" A diamond at the top of the shading marks a quarter in which a reporting change took effect "
               "(Sources tab, Reporting changes)." if any(took) else "")).font = F_NOTE

    for c in range(H, nxt[0]):
        ws.column_dimensions[L(c)].hidden = True
    switches = None
    if peers:
        from .peers import peers_workbook as PW
        switches = peer_switches(wb, lay_d, peers["names"], peers["sheet"], peers["include"], peers["states"],
                                 peers["pack"], PW.PACK_PICKS, PW.FOLLOW, PW.YES, PW.NO, PW.OUT, PW.STATE_OFF,
                                 why_out=peers.get("why_out"))
    return {"sheet": TITLE, "table": TABLE, "header_row": HDR, "first": FIRST, "last": LAST, "columns": C, "switches": switches,
            "check_row": lay_d["check"], "compare_rows": rows, "gives_rows": gives, "leave_out_rows": LO_N,
            "layout": lay_d, "helpers": {k: L(v) for k, v in cols_.items()}, "pairs": pairs, "by_pair": by_pair,
            "row_of": row_of, "sources": third, "lead": lead, "source_rows": src_rows}


# ---- the rename: the per-series table becomes Lines by source ----

def _sheet_ref(title: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", title):
        return title + "!"
    return "'%s'!" % title.replace("'", "''")


def rename_tab(wb, old: str, new: str) -> int:
    """Retitle ``old`` as ``new`` and rewrite every reference to it: cell
    formulas, conditional formats, data validations, defined names and chart
    series, on every tab. openpyxl renames a tab and nothing that points at
    it. Returns how many references were rewritten."""
    pat = re.compile(r"(?<![\w.'])%s" % re.escape(_sheet_ref(old)))
    to = _sheet_ref(new)
    count = [0]

    def fix(s):
        if not isinstance(s, str):
            return s
        out, k = pat.subn(to, s)
        count[0] += k
        return out

    wb[old].title = new
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    c.value = fix(c.value)
        for cf in ws.conditional_formatting:
            for rule in cf.rules:
                rule.formula = [fix(f) for f in rule.formula]
        for dv in ws.data_validations.dataValidation:
            dv.formula1, dv.formula2 = fix(dv.formula1), fix(dv.formula2)
        for dn in ws.defined_names.values():
            dn.attr_text = fix(dn.attr_text)
        for ch in ws._charts:
            for part in [ch] + list(getattr(ch, "_charts", [])):
                for s_ in part.series:
                    for ref in (s_.val and s_.val.numRef, s_.cat and (s_.cat.numRef or s_.cat.strRef),
                                s_.tx and s_.tx.strRef):
                        if ref is not None:
                            ref.f = fix(ref.f)
    for dn in wb.defined_names.values():
        dn.attr_text = fix(dn.attr_text)
    return count[0]


def peer_switches(wb, lay_d: dict, peers: Sequence[str], peers_sheet: str, include: Dict[str, str],
                  states: Dict[str, str], pack_cell: str, picks: Sequence[str], follow: str, yes: str, no: str,
                  state_out: str, state_off: str, why_out: Optional[dict] = None) -> Dict[str, str]:
    """Each peer's switch, and Banks in the pack, set on Decide under the chart; the
    cells on ``peers_sheet`` that held them read Decide instead, so there is one
    place to set each (the analyst, 20 Oct 2026: "I think we should be able to set
    peers on here probably even individually"). ``include``/``states``: each
    peer's switch and state cell on Peers; ``pack_cell``: Banks in the pack there.
    Each switch starts as Peers had it. ``state_out`` begins every out state ("out: jump").
    ``why_out`` (peers_workbook's): under the lists, each bank out and why, in roster order.
    Returns each peer's switch cell on Decide."""
    from .peers.peers_workbook import _quoted
    ws, pe = wb[TITLE], wb[peers_sheet]
    PE = _quoted(peers_sheet) + "!"
    t = lay_d["peers_title"]
    ws.cell(t, 2, "Peer group").font = F_HEAD
    ws.cell(t, 2).alignment = Alignment(vertical="bottom")
    _rule(ws, t, 2, 11, Side(style="medium", color=K.INK))
    pr = lay_d["peers_pick"]
    ws.cell(pr, 3, "Banks in the pack").font = F_LAB
    ws.cell(pr, 3).alignment = Alignment(horizontal="right", vertical="bottom", indent=1)
    pk = ws.cell(pr, 4, pe[pack_cell].value)
    pk.font, pk.fill, pk.border = F_BOLD, fill(K.INPUT), BOX
    pk.alignment = Alignment(vertical="center", indent=1)
    dv_pk = DataValidation(type="list", formula1='"%s"' % ",".join(picks), showErrorMessage=True,
                           errorTitle="Banks in the pack", error="Pick one from the list.")
    ws.add_data_validation(dv_pk)
    dv_pk.add(pk.coordinate)
    dv_sw = DataValidation(type="list", formula1='"%s,%s,%s"' % (follow, yes, no), showErrorMessage=True,
                           errorTitle="In the peer group", error="%s (follow Banks in the pack), %s or %s."
                           % (follow, yes, no))
    ws.add_data_validation(dv_sw)
    hr = lay_d["peers_head"]
    for names, sw, st in PEER_LISTS:
        st0 = st if isinstance(st, int) else st[0]
        if not isinstance(st, int):
            ws.merge_cells(start_row=hr, start_column=st[0], end_row=hr, end_column=st[1])
        for c, h in ((names[0], "Bank"), (sw, "Switch"), (st0, "This quarter")):
            ws.cell(hr, c, h).font = F_LAB
            ws.cell(hr, c).alignment = Alignment(horizontal="left" if c == names[0] else "center",
                                                 vertical="bottom")
    _rule(ws, hr, 2, 11, Side(style="thin", color=K.STONE))
    half = -(-len(peers) // 2)
    out = {}
    for j, short in enumerate(peers):
        (names, sw, st), r = PEER_LISTS[j // half], lay_d["peers_first"] + j % half
        if names[1] > names[0]:
            ws.merge_cells(start_row=r, start_column=names[0], end_row=r, end_column=names[1])
        ws.cell(r, names[0], short).font = F_BODY
        c_ = ws.cell(r, sw, pe[include[short]].value)
        c_.font, c_.fill, c_.border = F_BOLD, fill(K.INPUT), BOX
        c_.alignment = Alignment(horizontal="center", vertical="center")
        dv_sw.add(c_.coordinate)
        st0 = st if isinstance(st, int) else st[0]
        if not isinstance(st, int):
            ws.merge_cells(start_row=r, start_column=st[0], end_row=r, end_column=st[1])
        s_ = ws.cell(r, st0, "=%s%s" % (PE, "$%s$%s" % _split(states[short])))
        s_.font = F_SLATE
        s_.alignment = Alignment(horizontal="center", vertical="center")
        sref = "$%s$%d" % (L(st0), r)
        # in (INK), out (SLATE italic), off (STONE, struck through), as on Peers
        for where, struck in ((s_.coordinate, True), (c_.coordinate, False)):
            ws.conditional_formatting.add(where, FormulaRule(formula=['LEFT(%s,%d)="%s"' % (sref, len(state_out),
                                                                                            state_out)],
                                                             font=Font(color=K.SLATE, italic=True)))
            ws.conditional_formatting.add(where, FormulaRule(formula=['%s="%s"' % (sref, state_off)],
                                                             font=Font(color=K.STONE, strike=struck)))
        for c in range(names[0], (st if isinstance(st, int) else st[1]) + 1):
            ws.cell(r, c).border = Border(bottom=HAIR) if c != sw else BOX
        out[short] = "$%s$%d" % (L(sw), r)
        # Peers reads the switch from here: no longer an input there.
        _peers_reads(pe, include[short], "=%s!%s" % (TITLE, out[short]))
    _peers_reads(pe, pack_cell, "=%s!$D$%d" % (TITLE, pr))
    if why_out:
        # Why out, under the lists: the k-th bank out this quarter and its reason, as many rows as a list
        # has; when more are out, the last row says how many more.
        wh = lay_d["why_head"]
        h_ = ws.cell(wh, 2, "=" + why_out["head"])
        h_.font, h_.alignment = F_LAB, Alignment(vertical="bottom")
        _rule(ws, wh, 2, 11, Side(style="thin", color=K.STONE))
        n_out = "MAX(%s)" % why_out["numbers"]
        for k in range(1, half + 1):
            r = lay_d["why_first"] + k - 1
            at = "MATCH(%d,%s,0)" % (k, why_out["numbers"])
            more = '{n}>{h}'.format(n=n_out, h=half) if k == half else "FALSE"
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
            nm = ws.cell(r, 2, '=IF({m},"",IFERROR(INDEX({b},{a}),""))'.format(m=more, b=why_out["names"], a=at))
            nm.font, nm.alignment = F_BODY, Alignment(vertical="center")
            ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=11)
            wy = ws.cell(r, 4, ('=IF({m},"And "&({n}-{h}+1)&" more: the rule for each is under This '
                                'quarter.",IFERROR(INDEX({w},{a}),""))').format(
                m=more, n=n_out, h=half, w=why_out["whys"], a=at))
            wy.font, wy.alignment = F_SLATE, Alignment(vertical="center")
            for c in range(2, 12):
                ws.cell(r, c).border = Border(bottom=HAIR)
    # The pack line names where a bank is switched off: here now.
    if PACK_LINE in wb.defined_names:
        sh, at = wb.defined_names[PACK_LINE].attr_text.rsplit("!", 1)
        c = wb[sh.strip("'")][at.replace("$", "")]
        c.value = c.value.replace(" · switched off on %s: " % peers_sheet, " · switched off on %s: " % TITLE)
    return out


def _split(coord: str):
    return re.fullmatch(r"([A-Z]+)(\d+)", coord).groups()


def _peers_reads(pe, coord: str, formula: str) -> None:
    """A Peers input cell made to read Decide: the formula, out of its list, no longer yellow."""
    c = pe[coord]
    c.value = formula
    c.fill = PatternFill(fill_type=None)
    c.border = Border()
    c.font = Font(name="Calibri", size=11, bold=True, color=K.SLATE)
    for dv in pe.data_validations.dataValidation:
        if coord in dv.sqref:
            dv.sqref.remove(coord)
