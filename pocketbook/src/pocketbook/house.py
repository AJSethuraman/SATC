"""The house colours, in one place: the launcher and the workbook both read them.

The firm's redesign (docs/redesign-2026-09-26/README.md, "Design tokens") uses
the bank's workbook palette. The values are written here once, as the cube's
own module: `credit-suite` owns the palette's shared code, and a copy of that
file anywhere else in the repository fails its conformance test. Nothing here
imports openpyxl or Tk, so the launcher can read the colours before it has
checked that the add-ons are installed (ruling OC-34).

Hex is written without the '#', the way openpyxl takes it; `tk()` adds it for
the window.
"""

from __future__ import annotations

INK = "0A0908"          # title bands, column headers, a done step
ONYX = "16130F"         # section bands on the record; data text
INK_TEXT = ONYX
KEY_RED = "CC0000"      # the accent rule, the current step, the primary button
CRIMSON = "960019"      # alert text: "4 left", a refusal's tag
PAPER = "FFFFFF"        # the page
CANVAS = "F4F1EC"       # tiles, method notes, the step rail
MIST = "E4DFD5"         # dividers, the read-only band, a disabled button
STONE = "B9B4AC"        # a step still to do, faint rules, a greyed row
SLATE = "57534B"        # secondary text
ALERT_FG = "F7DEDE"     # a cell that needs an answer, a worse pocket, the workbook-open banner
POSITIVE = "1E7A47"     # tie-outs, holds up
POSITIVE_BG = "EAF6EE"
DISABLED_TEXT = "9A958C"
ROW_RULE = "EFEBE4"     # the one-pixel line between rows
HEAT_GOOD, HEAT_MID, HEAT_BAD, HEAT_BAD2 = "BBD3BD", "F4F1EC", "E0A6A6", "CF7777"

PALETTE = {"INK": INK, "ONYX": ONYX, "KEY_RED": KEY_RED, "CRIMSON": CRIMSON, "PAPER": PAPER, "CANVAS": CANVAS,
           "MIST": MIST, "STONE": STONE, "SLATE": SLATE, "ALERT_FG": ALERT_FG, "POSITIVE": POSITIVE,
           "POSITIVE_BG": POSITIVE_BG, "HEAT_GOOD": HEAT_GOOD, "HEAT_MID": HEAT_MID, "HEAT_BAD": HEAT_BAD,
           "HEAT_BAD2": HEAT_BAD2}


def tk(hex_: str) -> str:
    """A colour as Tk takes it: '#CC0000'."""
    return f"#{hex_}"


def fill(hex_: str):
    """A solid cell fill (openpyxl, imported only when a workbook is being written)."""
    from openpyxl.styles import PatternFill
    return PatternFill("solid", fgColor=hex_, bgColor=hex_)


def band(ws, row: int, first: int, last: int, text: str, hex_: str = INK, color: str = PAPER,
         rule: str | None = KEY_RED, key_col: int | None = None, key: str | None = None) -> None:
    """A section's header band across columns first..last: a fill, bold white text, and a rule under it."""
    from openpyxl.styles import Border, Font, Side
    for col in range(first, last + 1):
        c = ws.cell(row=row, column=col)
        c.fill = fill(hex_)
        if rule:
            c.border = Border(bottom=Side(style="medium", color=rule))
    head = ws.cell(row=row, column=first, value=text)
    head.font = Font(name="Arial", bold=True, size=10, color=color)
    if key_col and key:
        ws.cell(row=row, column=key_col, value=key)


# --------------------------------------------------------------------------
# The redesign's sheet anatomy (docs/redesign-2026-09-26/README.md, "Global rules"): the same on every tab it
# has reached. Each helper takes the sheet and the columns it spans, so a tab keeps its own widths.

TAB_YOU, TAB_RESULT, TAB_RECORD = KEY_RED, INK, STONE      # the tab colours: you fill it in, a result, the record
WAITING, SAME = "↻ Waiting for a Run", "Same as last Run"


def _side(style: str, color: str):
    from openpyxl.styles import Side
    return Side(style=style, color=color)


def _letter(col: int) -> str:
    from openpyxl.utils import get_column_letter
    return get_column_letter(col)


def title_band(ws, title: str, sub: str, first: int, last: int, tab: str = TAB_YOU, fill_hex: str = INK,
               rule: str = KEY_RED, sub_color: str = STONE) -> None:
    """Row 1: the tab's name in white Arial 16 on INK, a one-line subtitle in STONE beside it, and a 3 pt Key Red
    rule under the band. Gridlines off, and the tab coloured for what it is. The Record tab's band is SLATE with a
    STONE rule (the spec's Global rule 1.1)."""
    from openpyxl.styles import Alignment, Border, Font
    for col in range(first, last + 1):
        c = ws.cell(row=1, column=col)
        c.fill = fill(fill_hex)
        c.border = Border(bottom=_side("thick", rule))
    head = ws.cell(row=1, column=first, value=title)
    head.font = Font(name="Arial", bold=True, size=16, color=PAPER)
    head.alignment = Alignment(vertical="center")
    subc = ws.cell(row=1, column=first + 1, value=sub)
    subc.font = Font(name="Arial", size=10, color=sub_color)
    subc.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = tab


def method_note(ws, top: int, first: int, last: int, items: list[tuple[str, str]], label_width: int = 1) -> int:
    """The tab's one method note (tenet T1): a heading row, then one row per item, the label bold and the words in
    one merged cell that wraps, on CANVAS. The rows are grouped, so the reader folds them away with the outline's
    minus. Returns the first row under it, after a blank one."""
    from openpyxl.styles import Alignment, Font
    for col in range(first, last + 1):
        ws.cell(row=top, column=col).fill = fill(CANVAS)
    h = ws.cell(row=top, column=first, value="How this tab works")
    h.font = Font(name="Arial", bold=True, size=9, color=SLATE)
    r = top + 1
    text_col = first + label_width
    per_line = sum((ws.column_dimensions[_letter(c)].width or 9) for c in range(text_col, last + 1)
                   if not ws.column_dimensions[_letter(c)].hidden) * 1.15
    for label, words in items:
        for col in range(first, last + 1):
            ws.cell(row=r, column=col).fill = fill(CANVAS)
        a = ws.cell(row=r, column=first, value=label)
        a.font = Font(name="Calibri", bold=True, size=10, color=INK_TEXT)
        a.alignment = Alignment(vertical="top", wrap_text=True)
        if last > text_col:
            ws.merge_cells(start_row=r, start_column=text_col, end_row=r, end_column=last)
        b = ws.cell(row=r, column=text_col, value=words)
        b.font = Font(name="Calibri", size=10, color=INK_TEXT)
        b.alignment = Alignment(vertical="top", wrap_text=True)
        lines = max(1, -(-len(words) // max(int(per_line), 20)))
        ws.row_dimensions[r].height = 14 * lines + 3
        r += 1
    ws.row_dimensions.group(top, r - 1, outline_level=1, hidden=False)
    ws.sheet_properties.outlinePr.summaryBelow = False
    return r + 1


# --------------------------------------------------------------------------
# Column widths (the firm, 29 Sep 2026: "i prefer to have nice even layouts, or at least the column sizes should make
# sense for the data we see"; docs/column-widths-survey-2026-09-29.md). A width is in Excel's units, about one
# character of Calibri 10 or Arial bold 9, so a width is worked out from the text the column shows, never set per
# bank. A centred cell needs its characters + 2; a left label with indent 1, + 3.


def _pieces(text) -> list[tuple[str, bool]]:
    """Where Excel may break a line: at a space, or after a hyphen. Each piece, and whether a space comes before it."""
    import re
    out = []
    for k, word in enumerate(str(text).split()):
        for j, p in enumerate(re.findall(r"[^-]*-+|[^-]+", word)):
            out.append((p, k > 0 and j == 0))
    return out


def lines_at(text, chars: int) -> int:
    """How many lines `text` wraps to at `chars` characters a line, as Excel wraps: at a space or after a hyphen,
    and inside a word only when the word is longer than a line."""
    chars = max(1, int(chars))
    lines = cur = 0
    for p, spaced in _pieces(text):
        add = len(p) + (1 if spaced else 0)
        if cur and cur + add <= chars:
            cur += add
            continue
        lines += 1 + (len(p) - 1) // chars
        cur = len(p) - (len(p) - 1) // chars * chars
    return max(lines, 1)


def two_line_width(text) -> int:
    """The fewest characters a line needs for `text` to fit on two lines, breaking as Excel does and never inside
    a word."""
    text = str(text if text is not None else "")
    if not text.strip():
        return 0
    unbroken = max(len(p) for p, _ in _pieces(text))          # never inside a word
    return next(w for w in range(unbroken, len(text) + 1) if lines_at(text, w) <= 2)


def fit(texts, *, floor: float, cap: float, pad: float = 2, per_char: float = 1.0) -> float:
    """A column width that fits the longest of `texts` (as displayed) on one line: characters x per_char + pad,
    kept between floor and cap."""
    import math
    longest = max((len(str(t)) for t in texts if t is not None and str(t) != ""), default=0)
    return min(cap, max(floor, math.ceil(longest * per_char + pad)))


def section(ws, row: int, first: int, last: int, text: str, hex_: str = INK, rule: str | None = KEY_RED,
            color: str = PAPER) -> None:
    """A section's dark header band, one row, with its rule under it."""
    from openpyxl.styles import Alignment, Border, Font
    for col in range(first, last + 1):
        c = ws.cell(row=row, column=col)
        c.fill = fill(hex_)
        c.border = Border(bottom=_side("medium", rule)) if rule else Border()
    c = ws.cell(row=row, column=first, value=text)
    c.font = Font(name="Arial", bold=True, size=10, color=color)
    c.alignment = Alignment(vertical="center")
    ws.row_dimensions[row].height = 20


def sub_header(ws, row: int, first: int, heads: list, centre_from: int = 1) -> None:
    """The CANVAS row under a section band naming its columns. Headings from `centre_from` on are centred, like
    the answers under them."""
    from openpyxl.styles import Alignment, Font
    for i, h in enumerate(heads):
        c = ws.cell(row=row, column=first + i, value=h)
        c.fill = fill(CANVAS)
        c.font = Font(name="Arial", bold=True, size=9, color=SLATE)
        c.alignment = Alignment(horizontal="left" if i < centre_from else "center", vertical="center")


def header(ws, row: int, first: int, heads: list, centre_from: int = 1) -> None:
    """A table's column headers: INK fill, white Arial bold 9, one line."""
    from openpyxl.styles import Alignment, Font
    for i, h in enumerate(heads):
        c = ws.cell(row=row, column=first + i, value=h)
        c.fill = fill(INK)
        c.font = Font(name="Arial", bold=True, size=9, color=PAPER)
        c.alignment = Alignment(horizontal="left" if i < centre_from else "center", vertical="center")
    ws.row_dimensions[row].height = 18


def changes_now(cell) -> None:
    """An answer that changes the result tabs at once: CANVAS, a thin solid INK border, bold."""
    from openpyxl.styles import Border, Font
    s = _side("thin", INK_TEXT)
    cell.fill = fill(CANVAS)
    cell.border = Border(left=s, right=s, top=s, bottom=s)
    cell.font = Font(name="Calibri", bold=True, size=10, color=INK_TEXT)


def needs_run(cell) -> None:
    """An answer that takes effect at the next Run: white, a dashed SLATE border, bold."""
    from openpyxl.styles import Border, Font
    s = _side("dashed", SLATE)
    cell.fill = fill(PAPER)
    cell.border = Border(left=s, right=s, top=s, bottom=s)
    cell.font = Font(name="Calibri", bold=True, size=10, color=INK_TEXT)


def still_needed(formula: str):
    """The conditional format for a cell that still needs an answer: ALERT_FG while `formula` is true."""
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import PatternFill
    return FormulaRule(formula=[formula], fill=PatternFill("solid", fgColor=ALERT_FG, bgColor=ALERT_FG))


def tile(ws, row: int, first: int, last: int, label: str, value, fmt: str | None = None,
         top: str = KEY_RED) -> None:
    """A KPI tile over two rows: CANVAS, a 3 pt rule on top, the label in Calibri 9 SLATE and the value (often a
    formula) in Arial bold 12 under it."""
    from openpyxl.styles import Alignment, Border, Font
    for r in (row, row + 1):
        for col in range(first, last + 1):
            c = ws.cell(row=r, column=col)
            c.fill = fill(CANVAS)
            c.border = Border(top=_side("thick", top)) if r == row else Border()
        if last > first:
            ws.merge_cells(start_row=r, start_column=first, end_row=r, end_column=last)
    a = ws.cell(row=row, column=first, value=label)
    a.font = Font(name="Calibri", size=9, color=SLATE)
    a.alignment = Alignment(vertical="top", indent=1)
    b = ws.cell(row=row + 1, column=first, value=value)
    b.font = Font(name="Arial", bold=True, size=12, color=INK_TEXT)
    b.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    if fmt:
        b.number_format = fmt
    ws.row_dimensions[row].height = 15
    ws.row_dimensions[row + 1].height = 22
