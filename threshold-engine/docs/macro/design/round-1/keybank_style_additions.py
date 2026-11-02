# ===========================================================================
# MACROBOOK, ROUND 1  (Claude Design's hand-off for the economic conditions
# workbook, 22 Oct 2026: docs/design/macrobook-round-1/README.md is the spec)
# Append to keybank_style.py. Nothing above this block changes.
# ===========================================================================
MACRO_LINK  = "1F4E79"   # every link: series names, the nav row, the What if tile; no underline
MACRO_RULE  = "EFEBE4"   # the rule under every data row; chart gridlines (ROW_RULE in workbook.py today)
#: The Dashboard's two picks: box edge, table edge, label rule, lines. 4.4:1 and 3.0:1 on white,
#: so every chart that draws them carries a legend, and the readings table names them.
PICK        = ("2A78D6", "EB6834")
#: The NY Fed's six types of household debt, in its order: mortgage, HE revolving, auto loan,
#: credit card, student loan, other. Three sit under 3:1, so the tab keeps its legend and table.
DEBT_TYPES  = ("2A78D6", "EB6834", "1BAF7A", "EDA100", "E87BA4", "008300")
NORMAL_BAND = MIST       # the shaded normal range on every change chart
WHATIF_LINE = SLATE      # the what-if normal range, dashed (sysDash), 1 pt
OFF_AXIS    = STONE      # fill of the triangle marking a reading off the axis; edge SLATE 0.75 pt
#: Tab colours: the front tabs and States; core series alternating by topic; usable with care.
TAB_FRONT, TAB_TOPIC, TAB_CARE = INK, (SLATE, STONE), MIST


def macro_title(ws, title, sub, last, record=False, sub_col=None):
    """Row 1, 27 pt: the tab's name in Arial 16 bold PAPER on INK (SLATE on record tabs), the
    subtitle in Calibri 10 STONE (MIST on record tabs) from ``sub_col``, a thick KEY_RED rule
    (STONE on record tabs) under A:last."""


def macro_section(ws, row, label, first_col, last_col):
    """A section name: Arial 10 bold INK, bottom-aligned, over a medium INK rule; 18 pt. No fill."""
    return quiet_section(ws, row, label, last_col - first_col + 1, first_col)


def direction_cell(cell, direction):
    """▲ Increasing / ▼ Decreasing: Calibri 11 bold INK on MIST, centred. Stable: Calibri 11 SLATE,
    no fill. The same fill both ways: it says moving, never better or worse."""
