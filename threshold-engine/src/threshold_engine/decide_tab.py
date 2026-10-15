"""The Decide tab: one series at a time, and the decisions kept in the workbook.

The bank, 14 Oct 2026: *"assess one thing at a time, save decisions, not a
guide"*, and *"it cannot be a huge list"*; banks block macros. So every series
has one row in a table, ``Decisions``, at the top of the tab, and three
slicers (``slicers.py``) filter it to the one being looked at: a product, a
measure and a source, clicked. Typing in that row is the decision; saving the
file keeps it. Everything under the table follows the one visible row.

Assess's settings and periods-left-out cells become formulas reading the
table, so Thresholds, Summary and Assess are computed exactly as they were;
nothing here computes a line. The only arithmetic on this tab is the shading
behind its chart: the gaps between the lines Thresholds already holds.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from openpyxl.chart import AreaChart, LineChart
from openpyxl.chart.data_source import AxDataSource, NumDataSource, NumRef, StrRef
from openpyxl.chart.series import Series, SeriesLabel
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.table import Table, TableStyleInfo

from . import keybank_style as K

TITLE = "Decide"
TABLE = "Decisions"
HDR = 12                                  # the table's header row; the slicers sit in rows 3-11
SLICER_ROWS = (3, 11)
#: What the chart can show; the lines never depend on it.
WINDOWS = ("All quarters", "Last 80 quarters", "Last 48 quarters", "Last 20 quarters")
#: Where the three slicers sit, as (from_col, from_row, to_col, to_row), 0-based
#: cells: over B-C, D-H and I-L, from row 3 to the table's header.
SLICER_ANCHORS = ((1, 2, 3, 11), (3, 2, 8, 11), (8, 2, 12, 11))
DECISIONS = ("Not decided", "Accept these lines", "Reject")
FIXED = ["Decision", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)", "On a line, rate it",
         "Leave out from", "Leave out to", "Why left out", "Note", "Check", "Series", "Shown", "Left out no."]
HIDDEN = ("Series", "Shown", "Left out no.")
TYPED = ("Decision", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)", "On a line, rate it",
         "Leave out from", "Leave out to", "Why left out", "Note")
#: Assess's columns for each of Your settings, in order.
SETTING_COLS = (("Width of Moderate", "O"), ("Moderate-Low begins", "P"), ("How rare High is (z)", "Q"),
                ("On a line, rate it", "R"))
#: Assess's evidence text per series (assess_tab: hc + 18..20 with hc at Z).
EVIDENCE_COLS = (("Suggested", "AR"), ("Unusual stretches", "AS"), ("Why", "AT"))
SCALE = ("D9EAD3", "EEF2C6", "FCE8B2", "F6C9A4", "E6A0A0")
#: The lines laid over the chart, one per source, in the colour of its name in the table.
OVERLAY = ("1F5F99", "2E7D4F", "8A5A00", "6B3FA0", "007C80")
H = 27                                    # hidden helpers from column AA
CH = 32                                   # chart helpers from column AF
INK, SLATE = K.INK_TEXT, K.SLATE
F_BODY = Font(name="Calibri", size=11, color=INK)
F_BOLD = Font(name="Calibri", size=11, bold=True, color=INK)
F_NOTE = Font(name="Calibri", size=10, color=SLATE)
F_BIG = Font(name="Calibri", size=14, bold=True, color=INK)
F_LAB = Font(name="Arial", size=9, bold=True, color=SLATE)
F_ALERT = Font(name="Calibri", size=12, bold=True, color=K.CRIMSON)
YELLOW_EDGE = Side(style="thin", color="D6B656")


#: Thresholds' refusal for a half-typed period says to look on Assess; on Decide the cells are here.
HERE = ('SUBSTITUTE(SUBSTITUTE({m},"its Status on Assess says what is missing","fill in Leave out from, Leave out to '
        'and Why left out in its row on Decide"),"Finish that row under Periods left out","Finish its row on Decide")')


def fill(hex_):
    return PatternFill("solid", fgColor=hex_, bgColor=hex_)


def columns(part_names: Sequence[str]) -> Dict[str, int]:
    """Column number of every table column, from B."""
    return {name: 2 + i for i, name in enumerate(list(part_names) + FIXED)}


def layout(n: int, n_third: int, compare: bool) -> dict:
    """Where everything sits on Decide for n series and n_third values of the
    third part: one place for the builder, the tests and the walkthrough."""
    first, last = HDR + 1, HDR + n
    top = last + 2
    cmp_head = top + 5
    last_cmp = cmp_head + n_third
    ch = last_cmp + 3
    nr = ch + 19
    chk = nr + 5
    return dict(first=first, last=last, message=top, too_many=top + 1, headline=top + 3, compare_head=cmp_head,
                compare_first=cmp_head + 1, compare_line=last_cmp + 1 if compare else None, chart_band=ch,
                chart_note=nr, lines=nr + 3, history=nr + 4, check=chk, evidence=chk + 4)


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


def build(wb, *, labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]], part_names: Sequence[str],
          settings: Dict[str, Tuple[float, float, float, str]], lay: dict, n_quarters: int,
          absent: Sequence[dict], compare: Optional[Tuple[str, str]], unit: str = "") -> dict:
    """Add the Decide tab to ``wb`` (which already holds Assess, Thresholds and
    Data for ``labels``) and point Assess's typed cells at it.

    ``parts``: each label's three part values, in ``part_names`` order;
    ``settings``: each label's starting Your settings; ``lay``: Assess's layout
    (``assess_tab.layout``); ``absent``: the book's notes on combinations not
    in the workbook (``{"parts": {...}, "why": text}``), printed as given;
    ``compare``: (this, against), two values of the third part to set side
    by side, or None. Returns where things are, for the slicers and tests."""
    validate(part_names)
    th, asx = wb["Thresholds"], wb["Assess"]
    n = len(labels)
    q_last = n_quarters + 1                                  # Data rows 2..q_last
    d_last = L(1 + n)
    TH_END = 4 + n
    SET_TOP, LO_TOP = lay["set_top"], lay["lo_top"]
    LO_N = lay["lo_end"] - LO_TOP + 1
    C = columns(part_names)
    p0, p1, p2 = part_names

    ws = wb.create_sheet(TITLE)
    ws.sheet_properties.tabColor = K.KEY_RED
    ws.sheet_view.showGridLines = False

    ws["B1"] = "Decide · one series at a time"
    ws["B1"].font = Font(name="Arial", size=16, bold=True, color=INK)
    ws["B2"] = ("Click a %s, a %s and a %s. The yellow row under the buttons is that series' decision: type in it, "
                "and everything below follows. Save the file (Ctrl+S) to keep your decisions."
                % (p0.lower(), p1.lower(), p2.lower()))
    ws["B2"].font = F_NOTE
    for r in range(SLICER_ROWS[0], SLICER_ROWS[1] + 1):
        ws.row_dimensions[r].height = 25

    # ---- the table: one row per series; the slicers show one ----
    FIRST, LAST = HDR + 1, HDR + n
    for name, c in C.items():
        cell = ws.cell(HDR, c, name)
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[HDR].height = 30
    box = Border(YELLOW_EDGE, YELLOW_EDGE, YELLOW_EDGE, YELLOW_EDGE)
    for i, lab in enumerate(labels):
        r = FIRST + i
        for name, v in zip(part_names, parts[lab]):
            ws.cell(r, C[name], v)
        ws.cell(r, C["Decision"], DECISIONS[0])
        for (name, _), v in zip(SETTING_COLS, settings[lab]):
            ws.cell(r, C[name], v)
        ws.cell(r, C["Check"], '=IF(Thresholds!$M${t}="","OK",{m}&". To fix: "&{u})'
                .format(t=5 + i, m=HERE.format(m="Thresholds!$M$%d" % (5 + i)),
                        u=HERE.format(m="Thresholds!$U$%d" % (5 + i))))
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
            c_.alignment = Alignment(vertical="center", wrap_text=name in ("Why left out", "Note", "Check") or
                                     name in part_names)
            c_.font = F_BOLD if name in TYPED else F_BODY
            if name in TYPED:
                c_.fill = fill("FFF2CC")
                c_.border = box
        ws.cell(r, C["Check"]).font = Font(name="Calibri", size=10, color=INK)
        ws.row_dimensions[r].height = 45
    tbl = Table(displayName=TABLE, ref="%s%d:%s%d" % (L(C[p0]), HDR, L(C["Left out no."]), LAST))
    tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium15", showRowStripes=False)
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
                                  FormulaRule(formula=['LEFT(%s,8)="Refused:"' % chk], fill=fill("F8D7D7"),
                                              font=Font(bold=True, color=K.CRIMSON)))
    dec = "%s%d" % (L(C["Decision"]), FIRST)
    ws.conditional_formatting.add(rng("Decision").replace("$", ""),
                                  FormulaRule(formula=['%s="%s"' % (dec, DECISIONS[1])], fill=fill(SCALE[0])))
    ws.conditional_formatting.add(rng("Decision").replace("$", ""),
                                  FormulaRule(formula=['%s="%s"' % (dec, DECISIONS[2])], fill=fill("F8D7D7")))
    # Wide enough that a header still reads beside its filter arrow.
    widths = {p0: 13, p1: 17, p2: 13, "Decision": 15, "Width of Moderate": 12, "Moderate-Low begins": 13,
              "How rare High is (z)": 12, "On a line, rate it": 11, "Leave out from": 11, "Leave out to": 11,
              "Why left out": 18, "Note": 24, "Check": 30, "Series": 4, "Shown": 4, "Left out no.": 4}
    for name, w in widths.items():
        ws.column_dimensions[L(C[name])].width = w
    ws.column_dimensions["A"].width = 2
    for name in HIDDEN:
        ws.column_dimensions[L(C[name])].hidden = True

    D = rng("Decision")
    ws["L1"] = ('="Decided: "&(COUNTIF({d},"{a}")+COUNTIF({d},"{r}"))&" of {n}  ·  accepted "&COUNTIF({d},"{a}")'
                '&", rejected "&COUNTIF({d},"{r}")').format(d=D, a=DECISIONS[1], r=DECISIONS[2], n=n)
    ws["L1"].font = Font(name="Arial", size=12, bold=True, color=INK)

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

    # ---- under the table: the series the buttons picked ----
    SER, SHOWN = rng("Series"), rng("Shown")
    LBL = "$%s$1" % L(H)
    ws.cell(1, H, '=IFERROR(INDEX(%s,MATCH(1,%s,0)),"")' % (SER, SHOWN))
    ws.cell(2, H, "=SUM(%s)" % SHOWN)
    ROW = "$%s$3" % L(H)
    ws.cell(3, H, "=MATCH(%s,Thresholds!$A$5:$A$%d,0)" % (LBL, TH_END))
    COUNT = "$%s$2" % L(H)
    HAS = "AND(%s=1,ISNUMBER(%s))" % (COUNT, ROW)

    def th_(col):
        return "INDEX(Thresholds!$%s$5:$%s$%d,%s)" % (col, col, TH_END, ROW)

    def shown(name):
        return "INDEX(%s,MATCH(1,%s,0))" % (rng(name), SHOWN)

    def band(row, text):
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=14)
        c_ = ws.cell(row, 2, text)
        c_.font = Font(name="Arial", size=11, bold=True, color=K.PAPER)
        c_.fill = fill(INK)
        c_.alignment = Alignment(indent=1, vertical="center")
        ws.row_dimensions[row].height = 20

    def line_text(row, formula, font=F_BODY, height=None):
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=14)
        c_ = ws.cell(row, 2, formula)
        c_.font = font
        c_.alignment = Alignment(wrap_text=True, vertical="top", indent=1)
        if height:
            ws.row_dimensions[row].height = height
        return c_

    top = LAST + 2
    whys = [a["why"] for a in absent]
    none_msg = "No series in this workbook matches those buttons."
    if whys:
        none_msg += " Not in this workbook: " + " ".join(whys)
    line_text(top, '=IF({c}=1,"",IF({c}=0,"{z}",{c}&" series match. Click one {a}, one {b} and one {d}."))'
              .format(c=COUNT, z=none_msg.replace('"', "'"), a=p0.lower(), b=p1.lower(), d=p2.lower()),
              F_ALERT, 45 if whys else 30)
    line_text(top + 1, '=IF({n}>{m},"More than {m} series have a period left out; only the first {m} are used. '
                       'Clear one.","")'.format(n=n_lo, m=LO_N), F_ALERT)
    band(top + 2, "Where it stands now")
    line_text(top + 3, '=IF(NOT({h}),"",{s}&", "&LOWER({m})&", "&LOWER({p})&": "&TEXT({j},"{nf}")&"{u} in "&{i}'
                       '&"  ·  "&IF({k}="","no rating: see the Check","rating "&{k}&" "&{l}))'
              .format(h=HAS, s=shown(p2), m=shown(p1), p=shown(p0), j=th_("J"), i=th_("I"), k=th_("K"),
                      l=th_("L"), nf="0.00", u=unit.replace('"', "")), F_BIG, 24)

    # the same product and measure from every source
    cmp_r = top + 5
    ws.cell(cmp_r, 2, "Same %s and %s" % (p0.lower(), p1.lower())).font = F_LAB
    ws.cell(cmp_r, 5, "Latest").font = F_LAB
    ws.cell(cmp_r, 6, "Rating").font = F_LAB
    ws.cell(cmp_r, 8, "Decision").font = F_LAB
    ws.cell(cmp_r, 10, "On chart").font = F_LAB
    third = []
    for lab in labels:
        v = parts[lab][2]
        if v not in third:
            third.append(v)
    rows = {}
    for i, v in enumerate(third):
        r = cmp_r + 1 + i
        rows[v] = r
        ws.cell(r, 2, v).font = F_BODY
        lab = '{a}&" - "&{b}&" - {v}"'.format(a=shown(p0), b=shown(p1), v=v)
        m = "MATCH(%s,Thresholds!$A$5:$A$%d,0)" % (lab, TH_END)
        c_ = ws.cell(r, 5, '=IF({c}<>1,"",IFERROR(INDEX(Thresholds!$J$5:$J${e},{m}),""))'.format(c=COUNT, e=TH_END,
                                                                                                   m=m))
        c_.number_format = "0.00"
        c_.font = F_BODY
        ws.cell(r, 6, '=IF({c}<>1,"",IFERROR(IF(INDEX(Thresholds!$K$5:$K${e},{m})="","Refused",INDEX(Thresholds!'
                      '$K$5:$K${e},{m})&" "&INDEX(Thresholds!$L$5:$L${e},{m})),"Not in this workbook"))'
                .format(c=COUNT, e=TH_END, m=m)).font = F_BODY
        ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=7)
        ws.cell(r, 8, '=IF({c}<>1,"",IFERROR(INDEX({d},MATCH({l},{s},0)),""))'.format(c=COUNT, d=D, l=lab,
                                                                                       s=SER)).font = F_BODY
        ws.merge_cells(start_row=r, start_column=8, end_row=r, end_column=9)
        on = ws.cell(r, 10, "No")
        on.fill = fill("FFF2CC")
        on.border = Border(YELLOW_EDGE, YELLOW_EDGE, YELLOW_EDGE, YELLOW_EDGE)
        on.font = F_BOLD
        on.alignment = Alignment(horizontal="center")
        ws.cell(r, 2).font = Font(name="Calibri", size=11, bold=True, color=OVERLAY[i % len(OVERLAY)])
        for cc in range(2, 10):
            ws.cell(r, cc).border = Border(bottom=Side(style="thin", color="D9D4CB"))
    last_cmp = cmp_r + len(third)
    dv_on = DataValidation(type="list", formula1='"Yes,No"', showErrorMessage=True, errorTitle="On chart",
                           error="Yes or No.")
    ws.add_data_validation(dv_on)
    dv_on.add("J%d:J%d" % (cmp_r + 1, last_cmp))
    for k in range(5):
        ws.conditional_formatting.add("F%d:G%d" % (cmp_r + 1, last_cmp),
                                      FormulaRule(formula=['LEFT($F%d,1)="%d"' % (cmp_r + 1, k + 1)],
                                                  fill=fill(SCALE[k])))
    if compare:
        a, b = compare
        ws.cell(last_cmp + 1, 2, '=IF(AND(ISNUMBER(E{x}),ISNUMBER(E{y})),"{a} is "&TEXT(ABS(E{x}-E{y}),"0.00")'
                                 '&" points "&IF(E{x}>E{y},"higher than","lower than")&" {b}.","")'
                .format(x=rows[a], y=rows[b], a=a, b=b)).font = F_BOLD

    # ---- the chart: this series over its five rating zones, with any other source laid over ----
    ch_r = last_cmp + 3
    band(ch_r, "The history, over the five rating zones")
    # How much of it to draw (the firm, 14 Oct 2026: "it can focus - like maybe
    # the last 48 quarters"). Only the picture: the lines use every quarter kept.
    win_r = ch_r - 1
    ws.cell(win_r, 2, "Chart shows").font = F_LAB
    ws.cell(win_r, 2).alignment = Alignment(vertical="center")
    win = ws.cell(win_r, 4, WINDOWS[2])
    win.fill = fill("FFF2CC")
    win.border = Border(YELLOW_EDGE, YELLOW_EDGE, YELLOW_EDGE, YELLOW_EDGE)
    win.font = F_BOLD
    ws.merge_cells(start_row=win_r, start_column=4, end_row=win_r, end_column=5)
    dv_w = DataValidation(type="list", formula1='"%s"' % ",".join(WINDOWS), showErrorMessage=True,
                          errorTitle="Chart shows", error="Pick one from the list.")
    ws.add_data_validation(dv_w)
    dv_w.add("D%d" % win_r)
    ws.cell(win_r, 7, "Only the picture: the lines are set from every quarter kept.").font = F_NOTE
    WIN = '$D$%d' % win_r
    hdrs = ["Quarter", "History", "base", "1 Low", "2 Moderate-Low", "3 Moderate", "4 Moderate-High", "5 High"]
    for j, t in enumerate(hdrs):
        ws.cell(1, CH + j, t)
    col_of = 'MATCH(%s,Data!$B$1:$%s$1,0)' % (LBL, d_last)
    lines = [th_(c_) for c_ in "EFGH"]
    okl = "AND(%s,%s)" % (HAS, ",".join("ISNUMBER(%s)" % x for x in lines))
    vals = "Data!$B$2:$%s$%d" % (d_last, q_last)
    FLOOR, TOPV = "$%s$2" % L(CH + 9), "$%s$2" % L(CH + 10)
    # The history as numbers or blanks: the chart's column holds #N/A for a
    # missing quarter (so it is not drawn), which MIN and MAX would return.
    num = "$%s$2:$%s$%d" % (L(CH + 11), L(CH + 11), q_last)
    ws.cell(1, CH + 9, "floor")
    ws.cell(1, CH + 10, "top")
    ws.cell(1, CH + 11, "drawn and shown, numbers only")
    # The axis fits what is drawn inside the window (the firm: "the axis
    # should adjust to fit"): the zones are cut at the floor and the top.
    lows = "$%s$2:$%s$%d" % (L(CH + 14 + len(third)), L(CH + 14 + len(third)), q_last)
    ws.cell(2, CH + 9, "=MIN(0,MIN(%s))" % lows)
    ws.cell(2, CH + 10, "=IF(MAX(%s)>0,MAX(%s)*1.08,1)" % (num, num))
    OV = CH + 12                                         # one column per source switched on above
    ANY = OV + len(third)                                # the row's number when anything is drawn there
    FIT = ANY + 1                                        # the first row drawn, and how many: the chart's range
    for k, v in enumerate(third):
        ws.cell(1, OV + k, v)
    ws.cell(1, ANY, "drawn")
    ws.cell(1, FIT, "first, count")
    ws.cell(1, FIT + 1, "drawn and shown, lowest")
    for r in range(2, q_last + 1):
        ws.cell(r, CH, "=Data!$A%d" % r)
        ws.cell(r, CH + 1, '=IF({c}<>1,NA(),IFERROR(IF(ISNUMBER(INDEX({v},{i},{o})),INDEX({v},{i},{o}),NA()),NA()))'
                .format(c=COUNT, v=vals, i=r - 1, o=col_of))
        ws.cell(r, CH + 2, "=%s" % FLOOR)
        cols_ = [L(CH + 1)] + [L(OV + k) for k in range(len(third))]
        inwin = "AND({r}>=${f}$2,{r}<${f}$2+${f}$3)".format(r=r, f=L(FIT))
        # A line not drawn holds #N/A here, which MAX and MIN would return: skip it.
        refs = ["%s%d" % (c_, r) for c_ in cols_]
        ws.cell(r, CH + 11, '=IF(AND({w},COUNT({c})>0),MAX({m}),"")'.format(
            w=inwin, c=",".join(refs), m=",".join("IF(ISNUMBER(%s),%s,-1E+300)" % (x, x) for x in refs)))
        ws.cell(r, CH + 12 + len(third) + 2, '=IF(AND({w},COUNT({c})>0),MIN({m}),"")'.format(
            w=inwin, c=",".join(refs), m=",".join("IF(ISNUMBER(%s),%s,1E+300)" % (x, x) for x in refs)))
        clip = lambda e: "MIN(MAX(%s,%s),%s)" % (e, FLOOR, TOPV)            # noqa: E731
        edges = [FLOOR] + [clip(x) for x in lines] + [TOPV]
        for k in range(5):
            ws.cell(r, CH + 3 + k, "=IF(%s,MAX(%s-%s,0),NA())" % (okl, edges[k + 1], edges[k]))
        for k, v in enumerate(third):
            lab = '{a}&" - "&{b}&" - {v}"'.format(a=shown(p0), b=shown(p1), v=v)
            oc = 'MATCH(%s,Data!$B$1:$%s$1,0)' % (lab, d_last)
            # Not the source picked: that one is the black line already.
            ws.cell(r, OV + k, '=IF(AND({c}=1,$J${t}="Yes",{s}<>"{v}"),IFERROR(IF(ISNUMBER(INDEX({vv},{i},{o})),'
                               'INDEX({vv},{i},{o}),NA()),NA()),NA())'.format(c=COUNT, t=rows[v], s=shown(p2), v=v,
                                                                              vv=vals, i=r - 1, o=oc))
        drawn = ",".join("ISNUMBER(%s%d)" % (L(c_), r) for c_ in [CH + 1] + [OV + k for k in range(len(third))])
        ws.cell(r, ANY, '=IF(OR(%s),%d,"")' % (drawn, r))
    anyr = "$%s$2:$%s$%d" % (L(ANY), L(ANY), q_last)
    # The chart draws from the first quarter any line has to the last. An
    # axis cannot follow a cell, but a named range can (the firm, 14 Oct 2026:
    # "the axis should adjust to fit").
    span = 'IF({w}="{a}",{q},VALUE(MID({w},6,3)))'.format(w=WIN, a=WINDOWS[0], q=q_last)
    ws.cell(2, FIT, "=IF(COUNT({a})=0,2,MAX(MIN({a}),MAX({a})-{s}+1))".format(a=anyr, s=span))
    ws.cell(3, FIT, "=IF(COUNT({a})=0,{n},MAX({a})-{f}+1)".format(a=anyr, n=q_last - 1, f=L(FIT) + "2"))

    def name_for(col, nm):
        ws.defined_names[nm] = DefinedName(nm, attr_text="OFFSET(%s!$%s$1,%s!$%s$2-1,0,%s!$%s$3,1)" % (
            TITLE, L(col), TITLE, L(FIT), TITLE, L(FIT)))
        return "%s!%s" % (TITLE, nm)

    cats = name_for(CH, "dq_quarter")

    def series(col, nm, title):
        s_ = Series(val=NumDataSource(numRef=NumRef(f=name_for(col, nm))), tx=SeriesLabel(v=title))
        s_.cat = AxDataSource(strRef=StrRef(f=cats))
        return s_

    area = AreaChart()
    area.grouping = "stacked"
    for k, nm in enumerate(["base"] + ["zone%d" % i for i in range(1, 6)]):
        s_ = series(CH + 2 + k, "dq_" + nm, hdrs[2 + k])
        s_.idx = s_.order = 1 + len(third) + k
        if k == 0:
            s_.graphicalProperties.noFill = True
        else:
            s_.graphicalProperties.solidFill = SCALE[k - 1]
        s_.graphicalProperties.line.noFill = True
        area.series.append(s_)
    line = LineChart()
    main = series(CH + 1, "dq_history", "History")
    main.idx = main.order = 0
    main.smooth = False
    main.graphicalProperties.line.solidFill = INK
    main.graphicalProperties.line.width = 28000
    line.series.append(main)
    for k, v in enumerate(third):
        s_ = series(OV + k, "dq_over%d" % (k + 1), v)
        s_.idx = s_.order = 1 + k
        s_.smooth = False
        s_.graphicalProperties.line.solidFill = OVERLAY[k % len(OVERLAY)]
        s_.graphicalProperties.line.width = 19050
        s_.graphicalProperties.line.prstDash = "dash"
        line.series.append(s_)
    line.y_axis.majorGridlines = None
    line.x_axis.tickLblSkip = 4
    line.x_axis.tickLblPos = "low"
    line.x_axis.delete = False
    line.y_axis.delete = False
    line.legend = None                                  # the key is the table above and the note below
    line += area
    line.visible_cells_only = False                     # its data sits in hidden columns
    line.height, line.width = 9, 26
    ws.add_chart(line, "B%d" % (ch_r + 1))
    nr = ch_r + 19
    line_text(nr, "Black line: the series picked. Dashed lines: any other source switched on under On chart above, "
                  "in the colour of its name. Shading, from the bottom: green 1 Low, pale green 2 Moderate-Low, "
                  "yellow 3 Moderate, orange 4 Moderate-High, red 5 High. The chart starts at the first quarter any "
                  "line has, within what Chart shows. A period you leave out still shows; it is not used to set the "
                  "lines.", F_NOTE, 44)

    band(nr + 2, "Where each rating begins, and whether your settings fit")
    line_text(nr + 3, '=IF(NOT({h}),"","Rating 2 begins at "&TEXT({a},"0.00")&", 3 at "&TEXT({b},"0.00")&", 4 at "'
                      '&TEXT({c},"0.00")&", 5 at "&TEXT({d},"0.00")&".")'.format(h=HAS, a=lines[0], b=lines[1],
                                                                                 c=lines[2], d=lines[3]), F_BOLD)
    line_text(nr + 4, '=IF(NOT({h}),"","From this series\' own history: its middle (median) is "&TEXT({b},"0.00")'
                      '&", a typical yearly move is "&TEXT({c},"0.00")&", the worst quarter kept was "'
                      '&TEXT({d},"0.00")&".")'.format(h=HAS, b=th_("B"), c=th_("C"), d=th_("D")))
    chk_r = nr + 5
    line_text(chk_r, '=IF(NOT({h}),"",IF({m}="","Check: OK, your settings fit this series.",{mm}&". To fix: "&{u}))'
              .format(h=HAS, m=th_("M"), mm=HERE.format(m=th_("M")), u=HERE.format(m=th_("U"))), F_BOLD, 32)
    ws.conditional_formatting.add("B%d:N%d" % (chk_r, chk_r),
                                  FormulaRule(formula=['LEFT($B$%d,8)="Refused:"' % chk_r], fill=fill("F8D7D7"),
                                              font=Font(bold=True, color=K.CRIMSON)))
    line_text(chk_r + 1, "What each setting does when you raise it. Width of Moderate: more quarters rate Moderate. "
                         "Moderate-Low begins: fewer quarters rate Low. How rare High is (z): fewer quarters rate "
                         "High (2.5 is rare; 3.5 is the usual line for an outlier). On a line: worse gives a value "
                         "exactly on a line the worse rating.", F_NOTE, 44)

    band(chk_r + 3, "What the history suggests: keep every period, or leave one out?")
    srow = "MATCH(%s,Assess!$N$%d:$N$%d,0)" % (LBL, SET_TOP, SET_TOP + n - 1)
    for i, (t, col) in enumerate(EVIDENCE_COLS):
        r = chk_r + 4 + i
        ws.cell(r, 2, t).font = F_LAB
        ws.cell(r, 2).alignment = Alignment(vertical="top")
        c_ = ws.cell(r, 4, '=IF(NOT(%s),"",IFERROR(INDEX(Assess!$%s$%d:$%s$%d,%s),""))'
                     % (HAS, col, SET_TOP, col, SET_TOP + n - 1, srow))
        c_.font = F_BOLD if i == 0 else F_BODY
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=14)
        c_.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 18 if i == 0 else 30
    line_text(chk_r + 7, "To leave a period out, type its first and last quarter and why in the yellow row above. "
                         "To put it back, clear those three cells.", F_NOTE)
    for col in range(H, CH + 16 + len(third)):
        ws.column_dimensions[L(col)].hidden = True
    lay_d = layout(n, len(third), bool(compare))
    assert (lay_d["first"], lay_d["last"], lay_d["message"], lay_d["headline"], lay_d["compare_head"],
            lay_d["chart_band"], lay_d["lines"], lay_d["check"]) == (FIRST, LAST, top, top + 3, cmp_r, ch_r, nr + 3,
                                                                     chk_r)
    return {"sheet": TITLE, "table": TABLE, "header_row": HDR, "first": FIRST, "last": LAST, "columns": C,
            "screen_top": top, "check_row": chk_r, "compare_rows": rows, "leave_out_rows": LO_N, "layout": lay_d}
