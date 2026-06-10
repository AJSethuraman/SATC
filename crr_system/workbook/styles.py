"""Shared styling for the CRR workbook (industry model conventions).

Blue = hardcoded inputs, Black = formulas, Green = cross-sheet links,
Yellow fill = key assumptions. Arial throughout.
"""

from __future__ import annotations

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

FONT = "Arial"

NAVY = "1F3864"
MID_BLUE = "2E5597"
LIGHT_BLUE = "D9E2F3"
PALE = "F2F6FC"
AMBER = "FFF2CC"
PALE_RED = "FCE4E4"
PALE_GREEN = "E2EFDA"
GREY = "808080"
LIGHT_GREY = "F2F2F2"

INPUT_FONT = Font(name=FONT, size=10, color="0000FF")
FORMULA_FONT = Font(name=FONT, size=10, color="000000")
LINK_FONT = Font(name=FONT, size=10, color="008000")
BODY_FONT = Font(name=FONT, size=10)
BOLD_FONT = Font(name=FONT, size=10, bold=True)
SMALL_FONT = Font(name=FONT, size=8, color=GREY, italic=True)
TITLE_FONT = Font(name=FONT, size=16, bold=True, color="FFFFFF")
H2_FONT = Font(name=FONT, size=11, bold=True, color="FFFFFF")
H3_FONT = Font(name=FONT, size=10, bold=True, color=NAVY)

TITLE_FILL = PatternFill("solid", start_color=NAVY)
SECTION_FILL = PatternFill("solid", start_color=MID_BLUE)
SUBHEAD_FILL = PatternFill("solid", start_color=LIGHT_BLUE)
ASSUMPTION_FILL = PatternFill("solid", start_color="FFFF00")
BAND_FILL = PatternFill("solid", start_color=PALE)

THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BOTTOM = Border(bottom=THIN)

WRAP_TOP = Alignment(vertical="top", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(horizontal="left", vertical="center")

FMT_USD = "$#,##0;($#,##0);\"-\""
FMT_USD_K = "$#,##0,;($#,##0,);\"-\""
FMT_X = "0.0x;(0.0x);\"-\""
FMT_X2 = "0.00x;(0.00x);\"-\""
FMT_PCT = "0.0%;(0.0%);\"-\""
FMT_NUM = "#,##0;(#,##0);\"-\""
FMT_DATE = "mm/dd/yyyy"


def title_bar(ws, text, last_col, row=1, subtitle=None):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    c = ws.cell(row=row, column=1, value=text)
    c.font = TITLE_FONT
    c.fill = TITLE_FILL
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[row].height = 28
    for col in range(1, last_col + 1):
        ws.cell(row=row, column=col).fill = TITLE_FILL
    if subtitle:
        ws.merge_cells(start_row=row + 1, start_column=1, end_row=row + 1, end_column=last_col)
        s = ws.cell(row=row + 1, column=1, value=subtitle)
        s.font = Font(name=FONT, size=10, italic=True, color="FFFFFF")
        s.fill = SECTION_FILL
        s.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        for col in range(1, last_col + 1):
            ws.cell(row=row + 1, column=col).fill = SECTION_FILL


def section_bar(ws, row, text, first_col=1, last_col=8):
    ws.merge_cells(start_row=row, start_column=first_col, end_row=row, end_column=last_col)
    c = ws.cell(row=row, column=first_col, value=text)
    c.font = H2_FONT
    c.fill = SECTION_FILL
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for col in range(first_col, last_col + 1):
        ws.cell(row=row, column=col).fill = SECTION_FILL
    ws.row_dimensions[row].height = 18


def col_headers(ws, row, headers, start_col=1, fill=SUBHEAD_FILL, height=24):
    for i, h in enumerate(headers, start=start_col):
        c = ws.cell(row=row, column=i, value=h)
        c.font = Font(name=FONT, size=9, bold=True, color=NAVY)
        c.fill = fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BOX
    ws.row_dimensions[row].height = height


def set_widths(ws, widths, start_col=1):
    for i, w in enumerate(widths, start=start_col):
        ws.column_dimensions[get_column_letter(i)].width = w


def style_cell(c, *, font=None, fmt=None, fill=None, border=BOX, align=None):
    c.font = font or BODY_FONT
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if border:
        c.border = border
    if align:
        c.alignment = align
    return c
