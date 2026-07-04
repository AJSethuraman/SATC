"""``_config`` — the knob panel: engagement settings, policy thresholds, and
the rating-scale map, written as plain key/value rows with onyx section bands
(the quiet system-tab treatment every template in this repo uses).

The thresholds block doubles as the resolution target for the linesheet's
``[POL key]`` formula token: ``write_config_sheet`` returns a registry mapping
each threshold key to its absolute ``_config!$B$n`` cell so workbook formulas
reference the knob panel live — edit a threshold, the linesheets recompute.
"""

from __future__ import annotations

from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

from credit_review import keybank_style as KB
from credit_review.config import Engagement, Program

_INK_BOLD = Font(name="Arial", bold=True, size=11, color=KB.INK)


def write_config_sheet(ws: Worksheet, program: Program,
                       engagement: Engagement) -> dict[str, str]:
    """Populate ``_config`` and return the ``[POL]`` registry
    (threshold key -> ``_config!$B$n``)."""
    KB.hide_gridlines(ws)
    rows: list[list] = [
        ["Credit Review OS -- CONFIG (the knob panel). Thresholds here drive "
         "the linesheet formulas; edit values, no code change needed."],
        [],
        ["[ENGAGEMENT]"],
        ["key", "value", "help"],
        ["client_name", engagement.client_name, "Client bank under review."],
        ["engagement_id", engagement.engagement_id, "Unique engagement identifier."],
        ["lob", program.lob, "Line of business this program covers."],
        ["review_mode", program.review_mode,
         "loan_level (v1) | product_conformance (reserved for consumer/resi)."],
        [],
        ["[THRESHOLDS]"],
        ["key", "value", "help"],
    ]
    threshold_row_of: dict[str, int] = {}
    for key in sorted(engagement.thresholds):
        rows.append([key, engagement.thresholds[key],
                     "Engagement policy threshold (overlay); [POL] formulas point here."])
        threshold_row_of[key] = len(rows)

    rows += [[], ["[RATING_SCALE_MAP]"], ["internal grade", "regulatory bucket"]]
    for grade in sorted(engagement.rating_scale_map, key=lambda g: (len(g), g)):
        rows.append([grade, engagement.rating_scale_map[grade]])
    rows += [[], ["[RATING_FRAMEWORK]"], ["bucket", "criticized", "classified"]]
    for bucket in program.buckets:
        rows.append([bucket,
                     "TRUE" if bucket in program.criticized else "FALSE",
                     "TRUE" if bucket in program.classified else "FALSE"])

    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row, start=1):
            ws.cell(i, j, val)
        if row and isinstance(row[0], str) and row[0].startswith("["):
            band = ws.cell(i, 1)
            band.font = KB.SECTION_FONT
            band.fill = KB.SECT_FILL
    ws["A1"].font = _INK_BOLD
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 72

    return {key: f"_config!$B${r}" for key, r in threshold_row_of.items()}
