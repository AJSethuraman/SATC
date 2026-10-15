"""The Decide tab: one series at a time, and the decisions kept in the workbook.

The bank, 14 Oct 2026: *"assess one thing at a time, save decisions, not a
guide"*, and *"it cannot be a huge list"*; banks block macros. So every series
has one row in a table, ``Decisions``, at the top of the tab, and three
slicers (``slicers.py``) filter it to the one being looked at: a product, a
measure and a source, clicked. Typing in that row is the decision; saving the
file keeps it. Everything under the table follows the one visible row.

Laid out to Claude Design's round 2 (docs/design/round-2/README.md, "Decide"):
the slicers as rows of buttons over B4:Q6, the table from row 8, then the
headline, the Check band, and the chart beside the panel of its numbers, all
on the first screen.

Assess's settings and periods-left-out cells become formulas reading the
table, so Thresholds, Summary and Assess are computed exactly as they were;
nothing here computes a line. The arithmetic on this tab is only what draws
and describes the picture: the gaps between the lines Thresholds already
holds, and each kept quarter rated on them as Thresholds rates the latest.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

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

TITLE = "Decide"
TABLE = "Decisions"
HDR = 8                                   # the table's header row; the slicers sit over rows 4-6
SLICER_ROWS = (4, 6)
#: What the chart can show; the lines never depend on it. Each with the
#: quarters between its labels (the README: 2 / 4 / 8 / 12).
WINDOWS = ("Last 20 quarters", "Last 48 quarters", "Last 80 quarters", "Every quarter")
DEFAULT_WINDOW = WINDOWS[1]
#: Where the three slicers sit, as (from_col, from_row, to_col, to_row), 0-based
#: cells: over B:D, E:L and M:Q, and how many buttons to a row. They take in
#: the 6 pt rows above and below 4-6: Excel 16 drew the caption and two rows
#: of 0.25 in buttons in 94 px, and rows 4-6 alone are 78 px, which cut the
#: second row in half.
SLICER_ANCHORS = ((1, 2, 4, 7), (4, 2, 12, 7), (12, 2, 17, 7))
SLICER_COLUMNS = (3, 4, 3)
SLICER_STYLE = "SlicerStyleOther2"
SLICER_BUTTON_IN = 0.25
DECISIONS = ("Not decided", "Accept these lines", "Reject")
FIXED = ["Decision", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)", "On a line, rate it",
         "Leave out from", "Leave out to", "Why left out", "Note", "Check", "Series", "Shown", "Left out no."]
#: Table columns that only the formulas read. They sit in O:Q, under the
#: panel's columns, so they are not hidden: their text is formatted away.
HIDDEN = ("Series", "Shown", "Left out no.")
TYPED = ("Decision", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)", "On a line, rate it",
         "Leave out from", "Leave out to", "Why left out", "Note")
#: Typed cells shown bold: the numbers and the picks.
BOLD_TYPED = ("Decision", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)", "On a line, rate it")
#: Assess's columns for each of Your settings, in order.
SETTING_COLS = (("Width of Moderate", "O"), ("Moderate-Low begins", "P"), ("How rare High is (z)", "Q"),
                ("On a line, rate it", "R"))
#: Assess's evidence text per series (assess_tab: hc + 18..20 with hc at Z).
EVIDENCE_COLS = (("Suggested", "AR"), ("Unusual stretches", "AS"), ("Why", "AT"))
#: Rating cells, 1 Low to 5 High (Summary reads it too).
SCALE = K.RATING_FILL
RATINGS = ("Low", "Moderate-Low", "Moderate", "Moderate-High", "High")
H = 27                                    # hidden helpers from column AA
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
#: Thresholds' columns, by what they hold. A plain workbook keeps the layout
#: it has always had; a workbook with Decide (the book) has Thresholds laid
#: out to round 2. Every tab that reads Thresholds takes its letters from
#: here, never from a literal, so a column can move in one place.
TH_PLAIN = dict(series="A", median="B", move="C", worst="D", l2="E", l3="F", l4="G", l5="H", quarter="I",
                value="J", rating="K", rating_name="L", refusal="M", med_change="O", spread="P", med_all="Q",
                med_change_all="R", move_all="S", spread_all="T", fix="U")
TH_BOOK = dict(series="A", product="B", measure="C", source="D", median="E", move="F", worst="G", l2="H", l3="I",
               l4="J", l5="K", quarter="L", value="M", rating_shown="N", decision="O", check="P", rating="Q",
               rating_name="R", refusal="S", fix="T", med_change="U", spread="V", med_all="W", med_change_all="X",
               move_all="Y", spread_all="Z")
TH = TH_BOOK
#: Thresholds' first and last helper columns in the book: hidden.
TH_HIDDEN = ("Q", "Z")

#: Thresholds' refusal for a half-typed period says to look on Assess; on Decide the cells are here.
HERE = ('SUBSTITUTE(SUBSTITUTE({m},"its Status on Assess says what is missing","fill in Leave out from, Leave out to '
        'and Why left out in its row on Decide"),"Finish that row under Periods left out","Finish its row on Decide")')


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
    """Column number of every table column, from B."""
    return {name: 2 + i for i, name in enumerate(list(part_names) + FIXED)}


def layout(n: int, n_third: int, compare: bool) -> dict:
    """Where everything sits on Decide for n series and n_third values of the
    third part: one place for the builder, the tests and the walkthrough.
    For the book (105 series, three sources) these are the README's rows:
    headline 115, Check 116, section headings 118, chart and panel 119-136."""
    first, last = HDR + 1, HDR + n
    head = last + 2
    sec = head + 3
    t = n_third
    panel_end = sec + 15 + t
    hist = panel_end + 2
    sett = hist + 6
    return dict(first=first, last=last, headline=head, chip=head, compare_line=head if compare else None,
                check=head + 1, section=sec, chart_top=sec + 1, chart_end=panel_end, ratings_head=sec + 1,
                ratings_first=sec + 2, sources_title=sec + 8, sources_head=sec + 9, compare_first=sec + 10,
                window=sec + 10 + t, lines_label=sec + 12 + t, median=sec + 13 + t, move=sec + 14 + t,
                worst=sec + 15 + t, history=hist, evidence=hist + 1, left_now=hist + 4, settings=sett,
                notes=sett + 6)


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


def _rule(ws, row, c1, c2, side):
    for c in range(c1, c2 + 1):
        ws.cell(row, c).border = Border(bottom=side)


def build(wb, *, labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]], part_names: Sequence[str],
          settings: Dict[str, Tuple[float, float, float, str]], lay: dict, n_quarters: int,
          absent: Sequence[dict], compare: Optional[Tuple[str, str]], unit: str = "", higher: bool = True,
          floor_at_zero: bool = True) -> dict:
    """Add the Decide tab to ``wb`` (which already holds Assess, Thresholds and
    Data for ``labels``) and point Assess's typed cells at it.

    ``parts``: each label's three part values, in ``part_names`` order;
    ``settings``: each label's starting Your settings; ``lay``: Assess's layout
    (``assess_tab.layout``); ``absent``: the book's notes on combinations not
    in the workbook (``{"parts": {...}, "why": text}``), printed as given;
    ``compare``: (this, against), two values of the third part to set side
    by side, or None; ``higher``, ``floor_at_zero``: the measure's direction
    and floor, as Thresholds rates with them. Returns where things are, for
    the slicers and tests."""
    validate(part_names)
    asx = wb["Assess"]
    T = TH_BOOK
    n = len(labels)
    q_last = n_quarters + 1                                  # Data rows 2..q_last
    d_raw_last = L(1 + n)
    d_kept_last = L(1 + 2 * n)
    TH_END = 4 + n
    SET_TOP, LO_TOP = lay["set_top"], lay["lo_top"]
    LO_N = lay["lo_end"] - LO_TOP + 1
    C = columns(part_names)
    p0, p1, p2 = part_names
    third = []
    for lab in labels:
        v = parts[lab][2]
        if v not in third:
            third.append(v)
    colors = source_colors(third)
    lay_d = layout(n, len(third), bool(compare))
    FIRST, LAST = lay_d["first"], lay_d["last"]
    fz = floor_at_zero and higher

    ws = wb.create_sheet(TITLE)
    ws.sheet_properties.tabColor = K.TAB_WORK
    ws.sheet_view.showGridLines = False

    # ---- columns and the rows above the table (the README, px -> units) ----
    widths = {"A": 1.57, "B": 16.43, "C": 20.71, "D": 17.86, "E": 17.86, "F": 11.29, "G": 11.29, "H": 11.29,
              "I": 9.86, "J": 10.71, "K": 10.71, "L": 27.86, "M": 30.71, "N": 15.0, "O": 13.57, "P": 13.57,
              "Q": 14.43}
    for c_, w in widths.items():
        ws.column_dimensions[c_].width = w
    for r, h in ((1, 25.5), (2, 15), (3, 6), (4, 19.5), (5, 19.5), (6, 19.5), (7, 6), (HDR, 27)):
        ws.row_dimensions[r].height = h

    ws["B1"] = "Decide · one series at a time"
    ws["B1"].font = Font(name="Arial", size=16, bold=True, color=K.INK)
    ws["B1"].alignment = Alignment(vertical="bottom")
    ws["B2"] = ("Pick a %s, a %s and a %s with the buttons. The yellow cells in the row below them are that "
                "series' settings and decision; save the file (Ctrl+S) to keep them."
                % (p0.lower(), p1.lower(), p2.lower()))
    ws["B2"].font = F_SLATE
    _rule(ws, 2, 2, 17, Side(style="medium", color=K.KEY_RED))

    # ---- the table: one row per series; the slicers show one ----
    for name, c in C.items():
        cell = ws.cell(HDR, c, name)
        right = name in ("Width of Moderate", "Moderate-Low begins", "How rare High is (z)")
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="right" if right else "left")
        if name in HIDDEN:
            cell.font = Font(name="Arial", size=9, color=K.PAPER)
        else:
            cell.font = Font(name="Arial", size=9, bold=True, color=K.PAPER)
            cell.fill = fill(K.INK)
    for i, lab in enumerate(labels):
        r = FIRST + i
        for name, v in zip(part_names, parts[lab]):
            ws.cell(r, C[name], v)
        ws.cell(r, C["Decision"], DECISIONS[0])
        for (name, _), v in zip(SETTING_COLS, settings[lab]):
            ws.cell(r, C[name], v)
        ws.cell(r, C["Check"], '=IF(Thresholds!${m}${t}="","OK","Refused: see the fix below")'
                .format(m=T["refusal"], t=5 + i))
        ws.cell(r, C["Series"], lab)
        ws.cell(r, C["Shown"], "=SUBTOTAL(103,%s%d)" % (L(C["Series"]), r))
        # 1, 2, 3 down the rows with anything typed under Leave out: Assess's
        # periods-left-out rows find them by number.
        lo = L(C["Left out no."])
        ws.cell(r, C["Left out no."], '=IF(({f}{r}<>"")+({t}{r}<>"")+({w}{r}<>"")>0,MAX({c}${h}:{c}{p})+1,"")'
                .format(f=L(C["Leave out from"]), t=L(C["Leave out to"]), w=L(C["Why left out"]), r=r, c=lo,
                        h=HDR, p=r - 1))
        for name in C:
            c_ = ws.cell(r, C[name])
            c_.alignment = Alignment(vertical="center", wrap_text=name in ("Why left out", "Note", "Check")
                                     or name in part_names)
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
    tbl = Table(displayName=TABLE, ref="%s%d:%s%d" % (L(C[p0]), HDR, L(C["Left out no."]), LAST))
    # No table style: the header is styled by hand, and the helper columns'
    # header must not be drawn (an unnamed style is what Excel writes for None).
    tbl.tableStyleInfo = TableStyleInfo(name=None, showRowStripes=False)
    ws.add_table(tbl)

    def rng(name, sheet=""):
        return "%s$%s$%d:$%s$%d" % (sheet, L(C[name]), FIRST, L(C[name]), LAST)

    for name, lst in (("Decision", '"%s"' % ",".join(DECISIONS)), ("On a line, rate it", '"worse,better"'),
                      ("Leave out from", "=Data!$A$2:$A$%d" % q_last), ("Leave out to", "=Data!$A$2:$A$%d" % q_last)):
        dv = DataValidation(type="list", formula1=lst, showErrorMessage=True, errorTitle=name,
                            error="Pick one from the list.")
        ws.add_data_validation(dv)
        dv.add(rng(name).replace("$", ""))
    chk = "%s%d" % (L(C["Check"]), FIRST)
    ws.conditional_formatting.add(rng("Check").replace("$", ""),
                                  FormulaRule(formula=['LEFT(%s,8)="Refused:"' % chk], fill=fill(K.CANVAS),
                                              font=Font(bold=True, color=K.CRIMSON)))
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
                '&" · rejected "&COUNTIF({d},"{r}")').format(d=D, a=DECISIONS[1], r=DECISIONS[2], n=n)
    ws["L1"].font = Font(name="Arial", size=12, bold=True, color=K.INK)
    ws["L1"].alignment = Alignment(horizontal="right", vertical="bottom")

    # ---- Assess reads the table: its settings and periods left out are set here ----
    none = PatternFill(fill_type=None)
    for i in range(n):
        r, sr = FIRST + i, SET_TOP + i
        for name, col in SETTING_COLS:
            c_ = asx["%s%d" % (col, sr)]
            c_.value = '=IF(Decide!{c}{r}="","",Decide!{c}{r})'.format(c=L(C[name]), r=r)
            c_.fill = none
    for k in range(LO_N):
        # The k-th series with anything typed under Leave out, in table order.
        kth = "MATCH(%d,%s,0)" % (k + 1, rng("Left out no.", "Decide!"))
        for col, name in (("N", "Series"), ("O", "Leave out from"), ("P", "Leave out to"), ("Q", "Why left out")):
            c_ = asx["%s%d" % (col, LO_TOP + k)]
            c_.value = '=IFERROR(INDEX(%s,%s)&"","")' % (rng(name, "Decide!"), kth)
            c_.fill = none
    asx.cell(lay["set_title"], 14).value = "Your settings · set on the Decide tab, shown here"
    asx.cell(lay["lo_title"], 14).value = "Periods left out · set on the Decide tab, shown here"
    for row in range(1, 4):
        for col in range(1, 25):
            v = asx.cell(row, col).value
            if isinstance(v, str) and v.startswith("Choose what to show in B5"):
                asx.cell(row, col).value = ("Detail for the series in B5. Settings, periods left out and decisions "
                                            "are made on the Decide tab.")
    n_lo = "MAX(%s)" % rng("Left out no.")

    # ---- hidden helpers: the series the buttons picked, and its lines ----
    SER, SHOWN = rng("Series"), rng("Shown")
    hc = L(H)
    LBL, COUNT, ROW, SRC = ("$%s$%d" % (hc, r) for r in (1, 2, 3, 4))
    LN = ["$%s$%d" % (hc, 5 + j) for j in range(4)]              # where 2, 3, 4 and 5 begin
    REFUSAL, RULE, KEPT_OF = ("$%s$%d" % (hc, r) for r in (9, 10, 11))
    ws.cell(1, H, '=IFERROR(INDEX(%s,MATCH(1,%s,0)),"")' % (SER, SHOWN))
    ws.cell(2, H, "=SUM(%s)" % SHOWN)
    ws.cell(3, H, "=MATCH(%s,Thresholds!$A$5:$A$%d,0)" % (LBL, TH_END))
    HAS = "AND(%s=1,ISNUMBER(%s))" % (COUNT, ROW)

    def th_(key):
        c_ = T[key]
        return "INDEX(Thresholds!$%s$5:$%s$%d,%s)" % (c_, c_, TH_END, ROW)

    def shown(name):
        return "INDEX(%s,MATCH(1,%s,0))" % (rng(name), SHOWN)

    ws.cell(4, H, '=IF(%s,%s,"")' % (HAS, shown(p2)))
    for j, k_ in enumerate(("l2", "l3", "l4", "l5")):
        ws.cell(5 + j, H, '=IF(%s,IFERROR(%s+0,""),"")' % (HAS, th_(k_)))
    ws.cell(9, H, '=IF(%s,%s,"")' % (HAS, th_("refusal")))
    ws.cell(10, H, '=IF(%s,%s&"","")' % (HAS, shown("On a line, rate it")))
    ws.cell(11, H, '=IFERROR(MATCH(%s&", kept",Data!$B$1:$%s$1,0),"")' % (LBL, d_kept_last))
    lines_ok = "AND(%s,%s)" % (HAS, ",".join("ISNUMBER(%s)" % x for x in LN))

    # ---- the headline: the series, its rating, and the comparison ----
    hr = lay_d["headline"]
    ws.row_dimensions[hr - 1].height = 7.5
    ws.row_dimensions[hr].height = 30
    whys = [a["why"] for a in absent]
    none_msg = "No series in this workbook matches those buttons."
    if whys:
        none_msg += " Not in this workbook: " + " ".join(whys)
    ws.merge_cells(start_row=hr, start_column=2, end_row=hr, end_column=8)
    c_ = ws.cell(hr, 2, '=IF({c}=0,"{z}",IF({c}>1,{c}&" series match. Pick one {a}, one {b} and one {d}.",'
                        'IF(NOT({h}),"",{s}&", "&LOWER({m})&", "&LOWER({p})&": "&TEXT({j},"0.00")&"{u} in "&{i})))'
                 .format(c=COUNT, z=none_msg.replace('"', "'"), a=p0.lower(), b=p1.lower(), d=p2.lower(), h=HAS,
                         s=shown(p2), m=shown(p1), p=shown(p0), j=th_("value"), i=th_("quarter"),
                         u=unit.replace('"', "")))
    c_.font = Font(name="Arial", size=14, bold=True, color=K.INK)
    c_.alignment = Alignment(vertical="center", shrink_to_fit=True)
    ws.merge_cells(start_row=hr, start_column=9, end_row=hr, end_column=11)
    chip = ws.cell(hr, 9, '=IF(NOT({h}),"",IF({k}="","No rating: see the Check",{k}&" "&{l}))'
                   .format(h=HAS, k=th_("rating"), l=th_("rating_name")))
    chip.font = Font(name="Arial", size=12, bold=True, color=K.INK)
    chip.alignment = Alignment(vertical="center", indent=1)
    CHIP = "$I$%d" % hr
    for k in range(5):
        ws.conditional_formatting.add("I%d:K%d" % (hr, hr), FormulaRule(
            formula=['LEFT(%s,1)="%d"' % (CHIP, k + 1)], fill=fill(SCALE[k]), stopIfTrue=True))
    ws.conditional_formatting.add("I%d:K%d" % (hr, hr), FormulaRule(
        formula=['LEFT(%s,9)="No rating"' % CHIP], fill=fill(K.CANVAS), font=Font(bold=True, color=K.CRIMSON)))

    # ---- the Check band, under the headline: the reason, and what to type ----
    cr = lay_d["check"]
    ws.row_dimensions[cr].height = 25.5
    ws.merge_cells(start_row=cr, start_column=2, end_row=cr, end_column=8)
    ws.merge_cells(start_row=cr, start_column=9, end_row=cr, end_column=17)
    too_many = '{n}>{m}'.format(n=n_lo, m=LO_N)
    many_msg = "More than %d series have a period left out; only the first %d are used. Clear one." % (LO_N, LO_N)
    ws.cell(cr, 2, '=IF({t},"{mm}",IF(NOT({h}),"",IF({r}="","Check: OK, your settings fit this series.",{why})))'
            .format(h=HAS, t=too_many, mm=many_msg, r=REFUSAL, why=HERE.format(m=REFUSAL)))
    ws.cell(cr, 9, '=IF(OR(NOT({h}),{t}),"",IF({r}="","","To fix: "&{fix}))'
            .format(h=HAS, t=too_many, r=REFUSAL, fix=HERE.format(m=th_("fix"))))
    for c in (2, 9):
        ws.cell(cr, c).font = Font(name="Arial", size=12, bold=True, color=K.INK)
        ws.cell(cr, c).alignment = Alignment(vertical="center", indent=1 if c == 2 else 0, shrink_to_fit=True)
    for c in range(2, 18):
        ws.cell(cr, c).fill = fill(K.CANVAS)
        ws.cell(cr, c).border = Border(top=HAIR, bottom=HAIR)
    band = "B%d:Q%d" % (cr, cr)
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
    ws.cell(S, 2, '="The history over the five rating zones · "&LOWER(%s)' % WIN)
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
                      ("any", "drawn"), ("fit", "first, count, last, label every"), ("ft", "floor, top")):
        col(key, head)
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
    drawn = [cl["left"]] + pick_cols + over_cols
    if higher:
        ge_w, ge_b = "<=", "<"                           # a line at or below the value: the value is at least that rating
    else:
        ge_w, ge_b = ">=", ">"
    for r in range(2, q_last + 1):
        x = "%s%d" % (cl["kept"], r)
        ws.cell(r, cols_["q"], "=Data!$A%d" % r)
        ws.cell(r, cols_["cat"], '=IF(AND({r}>={f},{r}<={l},MOD({l}-{r},{s})=0),{q}{r},"")'
                .format(r=r, f=FIT, l=FIT_LAST, s=SKIP, q=cl["q"]))
        ws.cell(r, cols_["raw"], '=IF({c}<>1,NA(),IFERROR(IF(ISNUMBER(INDEX({v},{i},{o})),INDEX({v},{i},{o}),NA()),'
                                 'NA()))'.format(c=COUNT, v=vals, i=r - 1, o=raw_of))
        ws.cell(r, cols_["kept"], '=IF(OR({c}<>1,NOT(ISNUMBER({k}))),"",IFERROR(IF(ISNUMBER(INDEX({v},{i},{k})),'
                                  'INDEX({v},{i},{k}),""),""))'.format(c=COUNT, v=vals, i=r - 1, k=KEPT_OF))
        cmp_ = lambda op: "+".join("IF(%s%s%s,1,0)" % (ln, op, x) for ln in LN)   # noqa: E731
        ws.cell(r, cols_["rate"], '=IF(OR(NOT({ok}),{rf}<>"",NOT(ISNUMBER({x}))),"",IF({fz},IF({x}<=0,1,0),0)'
                                  '+IF(AND({fz},{x}<=0),0,1+IF({rule}="worse",{w},{b})))'
                .format(ok=lines_ok, rf=REFUSAL, x=x, fz="TRUE" if fz else "FALSE", rule=RULE, w=cmp_(ge_w),
                        b=cmp_(ge_b)))
        ws.cell(r, cols_["lo"], '=IF(AND(ISNUMBER({h}{r}),{k}{r}=""),1,0)'.format(h=cl["raw"], k=cl["kept"], r=r))
        nb = ["%s%d" % (cl["lo"], rr) for rr in (r - 1, r + 1) if 2 <= rr <= q_last]
        ws.cell(r, cols_["left"], '=IF(AND(ISNUMBER({h}{r}),OR({lo}{r}=1{nb})),{h}{r},NA())'.format(
            h=cl["raw"], r=r, lo=cl["lo"], nb="".join("," + c_ + "=1" for c_ in nb)))
        for k, v in enumerate(third):
            ws.cell(r, cols_["pick%d" % k], '=IF(AND({c}=1,{s}="{v}",ISNUMBER({x})),{x},NA())'
                    .format(c=COUNT, s=SRC, v=v, x=x))
            lab = '{a}&" - "&{b}&" - {v}"'.format(a=shown(p0), b=shown(p1), v=v)
            oc = 'MATCH(%s,Data!$B$1:$%s$1,0)' % (lab, d_raw_last)
            ws.cell(r, cols_["over%d" % k], '=IF(AND({c}=1,$Q${t}="Yes",{s}<>"{v}"),IFERROR(IF(ISNUMBER(INDEX({vv},'
                                             '{i},{o})),INDEX({vv},{i},{o}),NA()),NA()),NA())'
                    .format(c=COUNT, t=lay_d["compare_first"] + k, s=SRC, v=v, vv=vals, i=r - 1, o=oc))
        inwin = "AND({r}>={f},{r}<={l})".format(r=r, f=FIT, l=FIT_LAST)
        refs = ["%s%d" % (c_, r) for c_ in [cl["raw"]] + over_cols]
        ws.cell(r, cols_["num"], '=IF(AND({w},COUNT({c})>0),MAX({m}),"")'.format(
            w=inwin, c=",".join(refs), m=",".join("IF(ISNUMBER(%s),%s,-1E+300)" % (y, y) for y in refs)))
        ws.cell(r, cols_["low"], '=IF(AND({w},COUNT({c})>0),MIN({m}),"")'.format(
            w=inwin, c=",".join(refs), m=",".join("IF(ISNUMBER(%s),%s,1E+300)" % (y, y) for y in refs)))
        ws.cell(r, cols_["base"], "=%s" % FLOOR)
        for k in range(5):
            ws.cell(r, cols_["z%d" % (k + 1)], "=IF(%s,MAX(%s-%s,0),NA())" % (lines_ok, edges[k + 1], edges[k]))
        for j in range(4):
            ws.cell(r, cols_["lab%d" % j], '=IF(AND({r}={l},{ok},{x}>={f},{x}<={t}),{x},NA())'
                    .format(r=r, l=FIT_LAST, ok=lines_ok, x=LN[j], f=FLOOR, t=TOPV))
        any_ = ",".join("ISNUMBER(%s%d)" % (c_, r) for c_ in [cl["raw"]] + over_cols)
        ws.cell(r, cols_["any"], '=IF(OR(%s),%d,"")' % (any_, r))
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
        s_ = series("pick%d" % k, "dq_pick%d" % (k + 1), "%s (picked)" % v)
        s_.graphicalProperties.line = _ln(colors[v], 2.5)
        picks.append(s_)
    labs = []
    for j in range(4):
        s_ = series("lab%d" % j, "dq_label%d" % (j + 2), tx_ref="%s!$%s$1" % (TITLE, cl["lab%d" % j]))
        s_.graphicalProperties.line.noFill = True
        s_.dLbls = DataLabelList(showSerName=True, showVal=False, showLegendKey=False, showCatName=False,
                                 showPercent=False, showLeaderLines=False, dLblPos="r", txPr=_text(9, K.SLATE))
        labs.append(s_)
    for s_ in over + [left] + picks + labs:
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

    # ---- the panel, right: where each rating begins ----
    rh = lay_d["ratings_head"]
    for c, t_ in zip(range(12, 17), ("Rating", "Begins at" + (" (%s)" % unit if unit else ""), "Quarters kept",
                                     "Share", "Latest")):
        cell = ws.cell(rh, c, t_)
        cell.font = F_LAB
        cell.alignment = Alignment(horizontal="right" if c in (13, 14, 15) else "left", vertical="center")
    _rule(ws, rh, 12, 17, Side(style="thin", color=K.STONE))
    rate_r, kept_r = rng_("rate"), rng_("kept")
    for k in range(5):
        r = lay_d["ratings_first"] + k
        c_ = ws.cell(r, 12, "%d %s" % (k + 1, RATINGS[k]))
        c_.font = F_BOLD
        c_.fill = fill(SCALE[k])
        if k == 0:
            begins = "the bottom" if higher else "the top"
            ws.cell(r, 13, '=IF(%s,"%s","")' % (HAS, begins))
        else:
            ws.cell(r, 13, '=IF(ISNUMBER(%s),%s,"")' % (LN[k - 1], LN[k - 1]))
        ws.cell(r, 14, '=IF(OR(NOT({h}),{rf}<>""),"",COUNTIF({rr},{k}))'.format(h=HAS, rf=REFUSAL, rr=rate_r,
                                                                              k=k + 1))
        ws.cell(r, 15, '=IF(OR(NOT({h}),{rf}<>"",COUNT({kr})=0),"",COUNTIF({rr},{k})/COUNT({kr}))'
                .format(h=HAS, rf=REFUSAL, rr=rate_r, k=k + 1, kr=kept_r))
        ws.cell(r, 16, '=IF(AND({h},{rt}={k}),"◀ "&{q},"")'.format(h=HAS, rt=th_("rating"), k=k + 1,
                                                                  q=th_("quarter")))
        ws.cell(r, 13).font = F_BOLD
        ws.cell(r, 13).number_format = "0.00"
        ws.cell(r, 13).alignment = Alignment(horizontal="right")
        ws.cell(r, 14).font = F_BODY
        ws.cell(r, 15).font = F_BODY
        ws.cell(r, 15).number_format = "0%"
        ws.cell(r, 16).font = F_BOLD
        for c in range(12, 18):
            ws.cell(r, c).border = Border(bottom=HAIR)

    # ---- the same product and measure from every source ----
    st = lay_d["sources_title"]
    ws.cell(st, 12, "Same %s and %s, every %s" % (p0.lower(), p1.lower(), p2.lower())).font = F_HEAD
    ws.cell(st, 12).alignment = Alignment(vertical="bottom")
    _rule(ws, st, 12, 17, Side(style="medium", color=K.INK))
    sh = lay_d["sources_head"]
    for c, t_ in ((12, "%s (line color)" % p2), (13, "Rating"), (14, "Latest"), (15, "Decision"), (17, "On chart")):
        cell = ws.cell(sh, c, t_)
        cell.font = F_LAB
        cell.alignment = Alignment(horizontal="right" if c == 14 else "left", vertical="center")
    _rule(ws, sh, 12, 17, Side(style="thin", color=K.STONE))
    rows = {}
    for i, v in enumerate(third):
        r = lay_d["compare_first"] + i
        rows[v] = r
        lab = '{a}&" - "&{b}&" - {v}"'.format(a=shown(p0), b=shown(p1), v=v)
        m = "MATCH(%s,Thresholds!$A$5:$A$%d,0)" % (lab, TH_END)
        at = lambda key: "INDEX(Thresholds!${c}$5:${c}${e},{m})".format(c=T[key], e=TH_END, m=m)   # noqa: E731
        nm = ws.cell(r, 12, '=IF({s}="{v}","━ ","╍ ")&"{v}"'.format(s=SRC, v=v))
        nm.font = Font(name="Calibri", size=11, bold=True, color=colors[v])
        ws.cell(r, 13, '=IF({c}<>1,"",IFERROR(IF({k}="","Refused",{k}&" "&{l}),"Not in this workbook"))'
                .format(c=COUNT, k=at("rating"), l=at("rating_name"))).font = F_BOLD
        c_ = ws.cell(r, 14, '=IF({c}<>1,"",IFERROR({j},""))'.format(c=COUNT, j=at("value")))
        c_.number_format = "0.00"
        c_.font = F_BODY
        ws.cell(r, 15, '=IF({c}<>1,"",IFERROR(INDEX({d},MATCH({l},{s},0)),""))'.format(c=COUNT, d=D, l=lab,
                                                                                        s=SER)).font = F_BODY
        on = ws.cell(r, 17, "No")
        on.fill = fill(K.INPUT)
        on.border = BOX
        on.font = F_BOLD
        for c in range(12, 17):
            ws.cell(r, c).border = Border(bottom=HAIR)
        # The picked source is the solid line already: its switch reads Picked.
        ws.conditional_formatting.add("Q%d" % r, Rule(type="expression", formula=['%s="%s"' % (SRC, v)],
                                                      stopIfTrue=True, dxf=DifferentialStyle(
                                                          numFmt=NumberFormat(numFmtId=190, formatCode=';;;"Picked"'),
                                                          font=Font(bold=False, color=K.SLATE), fill=fill(K.PAPER))))
    cf, cl_ = lay_d["compare_first"], lay_d["compare_first"] + len(third) - 1
    for k in range(5):
        ws.conditional_formatting.add("M%d:M%d" % (cf, cl_), FormulaRule(
            formula=['LEFT($M%d,1)="%d"' % (cf, k + 1)], fill=fill(SCALE[k]), stopIfTrue=True))
    ws.conditional_formatting.add("M%d:M%d" % (cf, cl_), FormulaRule(
        formula=['$M%d="Refused"' % cf], fill=fill(K.CANVAS), font=Font(bold=True, color=K.CRIMSON)))
    dv_on = DataValidation(type="list", formula1='"Yes,No"', showErrorMessage=True, errorTitle="On chart",
                           error="Yes or No.")
    ws.add_data_validation(dv_on)
    dv_on.add("Q%d:Q%d" % (cf, cl_))
    if compare:
        a, b = compare
        pts = "percentage points" if unit.strip() == "%" else "points"
        ws.merge_cells(start_row=hr, start_column=12, end_row=hr, end_column=17)
        c_ = ws.cell(hr, 12, '=IF(AND({h},ISNUMBER(N{x}),ISNUMBER(N{y})),"{a} is "&TEXT(ABS(N{x}-N{y}),"0.00")'
                             '&" {p} "&IF(N{x}>=N{y},"higher","lower")&" than {b}.","")'
                     .format(h=HAS, x=rows[a], y=rows[b], a=a, b=b, p=pts))
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
    ws.cell(lr, 12, "What the lines rest on: this series' own history, quarters kept").font = F_LAB
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
    fr, to, why = shown("Leave out from"), shown("Leave out to"), shown("Why left out")
    c_ = ws.cell(r, 4, '=IF(NOT({h}),"",IF(AND({f}="",{t}=""),"No period is left out; every quarter is kept.",'
                       '"Left out: "&{f}&" to "&{t}&IF({w}="","",", "&{w})&". The chart draws these quarters in '
                       'gray; the lines are set without them."))'.format(h=HAS, f=fr, t=to, w=why))
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
    nt = lay_d["notes"]
    ws.cell(nt, 2, "The solid line is the series picked. A dashed line is another %s switched on under On chart, "
                   "in the color of its name. A gray stretch is a period left out: it is drawn, and it does not set "
                   "the lines." % p2.lower()).font = F_NOTE
    ws.cell(nt + 1, 2, "The shading runs from 1 Low to 5 High. The chart starts at the first quarter any line has, "
                       "within the window set under Chart shows. Every term is defined on the Glossary tab."
            ).font = F_NOTE

    for c in range(H, nxt[0]):
        ws.column_dimensions[L(c)].hidden = True
    return {"sheet": TITLE, "table": TABLE, "header_row": HDR, "first": FIRST, "last": LAST, "columns": C,
            "check_row": lay_d["check"], "compare_rows": rows, "leave_out_rows": LO_N, "layout": lay_d,
            "helpers": {k: L(v) for k, v in cols_.items()}}
