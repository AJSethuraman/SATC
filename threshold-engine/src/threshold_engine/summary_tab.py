"""The Summary tab: every series' latest quarter and rating on one page.

Rows are the first two parts (product, then measure); columns the third
(source). Every number is a live lookup into Thresholds by series label, so it
follows what is typed on Decide; nothing is computed here but one optional
difference, ``compare``'s two sources side by side.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

from . import keybank_style as K
from .decide_tab import SCALE, fill

TITLE = "Summary"
HDR = 5
INK, SLATE = K.INK_TEXT, K.SLATE


def _order(values):
    out = []
    for v in values:
        if v not in out:
            out.append(v)
    return out


def build(wb, *, name: str, unit: str, labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]],
          part_names: Sequence[str], absent: Sequence[dict], compare: Optional[Tuple[str, str]],
          notes: Sequence[str]) -> dict:
    """Add the Summary tab. ``absent`` and ``notes`` are the book's own words,
    printed as given; nothing is said about a missing series that the book
    did not say."""
    ws = wb.create_sheet(TITLE)
    n = len(labels)
    end_th = 4 + n
    A, J, K_, L_, M = ("Thresholds!$%s$5:$%s$%d" % (c, c, end_th) for c in "AJKLM")
    p0, p1, p2 = part_names
    rows = _order((parts[lab][0], parts[lab][1]) for lab in labels)
    cols = _order(parts[lab][2] for lab in labels)
    by = {parts[lab]: lab for lab in labels}

    ws.sheet_properties.tabColor = K.KEY_RED
    ws.sheet_view.showGridLines = False
    ws["A1"] = "%s: where each series stands in the latest quarter" % name
    ws["A1"].font = Font(name="Arial", size=16, bold=True, color=INK)
    ws["A2"] = ('="Latest quarter: "&INDEX(Thresholds!$I$5:$I$%d,1)&". Each rating compares that quarter with the '
                'series\' own history: 1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High."' % end_th)
    ws["A2"].font = Font(name="Calibri", size=10, color=SLATE)
    ws["A3"] = ("Live: the ratings follow what is typed on the Decide tab. Click a series there to see its chart, "
                "its lines, and to record a decision.")
    ws["A3"].font = Font(name="Calibri", size=10, color=SLATE)

    head_font = Font(name="Arial", size=10, bold=True, color=K.PAPER)
    sub_font = Font(name="Arial", size=9, bold=True, color=SLATE)
    thick, hair = Side(style="medium", color=INK), Side(style="thin", color="D9D4CB")
    col_of = {}
    for i, v in enumerate(cols):
        c = 3 + 2 * i
        col_of[v] = c
        ws.merge_cells(start_row=HDR, start_column=c, end_row=HDR, end_column=c + 1)
        cell = ws.cell(HDR, c, v)
        cell.font, cell.fill = head_font, fill(INK)
        cell.alignment = Alignment(horizontal="center")
    last_col = 2 + 2 * len(cols)
    if compare:
        a, b = compare
        last_col += 1
        cell = ws.cell(HDR, last_col, "%s vs %s" % (a, b))
        cell.font, cell.fill = head_font, fill(INK)
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        ws.row_dimensions[HDR].height = 28
    subs = [p0, p1] + ["Latest" + (" (%s)" % unit if unit else ""), "Rating"] * len(cols) + (
        ["difference"] if compare else [])
    for c, t in enumerate(subs, start=1):
        cell = ws.cell(HDR + 1, c, t)
        cell.font = sub_font
        cell.border = Border(bottom=thick)
        cell.alignment = Alignment(horizontal="left" if c <= 2 else "center")

    def look(col, label):
        return 'INDEX(%s,MATCH("%s",%s,0))' % (col, label, A)

    r = HDR + 2
    first_rating_row = r
    prev = None
    for a_, b_ in rows:
        ws.cell(r, 1, a_ if a_ != prev else None).font = Font(name="Calibri", size=11, bold=True, color=INK)
        if prev is not None and a_ != prev:
            for c in range(1, last_col + 1):
                ws.cell(r - 1, c).border = Border(bottom=thick)
        prev = a_
        ws.cell(r, 2, b_).font = Font(name="Calibri", size=11, color=INK)
        for v in cols:
            c = col_of[v]
            lab = by.get((a_, b_, v))
            val = ws.cell(r, c, '=IFERROR(%s,"")' % look(J, lab) if lab else "")
            val.number_format = "0.00"
            rt = ws.cell(r, c + 1, ('=IFERROR(IF(%s="",IF(%s<>"","Refused",""),%s&" "&%s),"")'
                                    % (look(K_, lab), look(M, lab), look(K_, lab), look(L_, lab)))
                         if lab else "Not in this workbook")
            for cell in (val, rt):
                cell.font = Font(name="Calibri", size=11, color=INK)
                cell.alignment = Alignment(horizontal="center")
        if compare:
            x, y = col_of[compare[0]], col_of[compare[1]]
            d = ws.cell(r, last_col, '=IF(AND(ISNUMBER({x}{r}),ISNUMBER({y}{r})),{x}{r}-{y}{r},"")'
                        .format(x=L(x), y=L(y), r=r))
            d.number_format = "+0.00;-0.00;0.00"
            d.alignment = Alignment(horizontal="center")
        for c in range(1, last_col + 1):
            if ws.cell(r, c).border.bottom is None or ws.cell(r, c).border.bottom.style is None:
                ws.cell(r, c).border = Border(bottom=hair)
        r += 1
    end = r - 1
    for c in range(1, last_col + 1):
        ws.cell(end, c).border = Border(bottom=thick)

    rating_rng = " ".join("%s%d:%s%d" % (L(col_of[v] + 1), first_rating_row, L(col_of[v] + 1), end) for v in cols)
    anchor = "%s%d" % (L(col_of[cols[0]] + 1), first_rating_row)
    for k in range(5):
        ws.conditional_formatting.add(rating_rng, FormulaRule(formula=['LEFT(%s,1)="%d"' % (anchor, k + 1)],
                                                              fill=fill(SCALE[k]),
                                                              font=Font(bold=k >= 3, color=INK)))
    ws.conditional_formatting.add(rating_rng, FormulaRule(
        formula=['OR(%s="Refused",%s="Not in this workbook")' % (anchor, anchor)],
        font=Font(italic=True, color=SLATE)))

    r = end + 2
    told = ["How to read it",
            "Rating: where the latest quarter falls against that series' own history, under the settings on Decide.",
            "Refused: those settings do not fit that series (for example, a line would fall at or below zero). "
            "Its Check on Decide says why and what to change. Nothing is filled in instead."]
    told += ["Not in this workbook: " + a["why"] for a in absent]
    if compare:
        told.append("%s vs %s: the first's latest value less the second's. Above zero means %s is higher."
                    % (compare[0], compare[1], compare[0]))
    told += list(notes)
    for i, t in enumerate(told):
        c = ws.cell(r + i, 1, t)
        c.font = Font(name="Calibri", size=11 if i == 0 else 10, bold=i == 0, color=INK if i == 0 else SLATE)
        if i:
            ws.merge_cells(start_row=r + i, start_column=1, end_row=r + i, end_column=last_col)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r + i].height = 28
    widths = [16, 34] + [10, 17] * len(cols) + ([17] if compare else [])
    for i, w in enumerate(widths):
        ws.column_dimensions[L(i + 1)].width = w
    ws.freeze_panes = "C7"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    return {"sheet": TITLE, "first": HDR + 2, "last": end, "columns": col_of, "rows": rows}
