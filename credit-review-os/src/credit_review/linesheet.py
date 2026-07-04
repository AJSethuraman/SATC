"""Config-driven loan linesheet builder (one ``LS_<loan_id>`` sheet per loan).

Adapts — does not import — the ``satc_system`` ``LineSheetBuilder`` token
grammar, restyled to the KeyBank house style. Formula tokens are resolved at
build time so the workbook ships live Excel formulas, never hardcoded results:

  ``{row_id}``     -> the value cell of another row on this linesheet
  ``[POL key]``    -> the engagement policy-threshold cell on ``_config``

Row ``kind`` vocabulary rendered in slice 1: input / input_num / input_text /
rating_input / computed / subhead / note / spacer. The ``exception`` and
``evidence`` kinds are schema-reserved for later slices and refused loudly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from credit_review import keybank_style as KB
from credit_review.config import RESERVED_KINDS

# Column layout: A margin, B label, C value, D note. Value column is C.
COL_LABEL = 2
COL_VALUE = 3
COL_NOTE = 4
LAST_COL = 4
VALUE_LETTER = "C"

# Number formats (currency shows parens for negatives, dash for zero).
FMT_USD = '$#,##0;($#,##0);"-"'
FMT_NUM = '#,##0;(#,##0);"-"'
FMT_TEXT = "@"
_FMT = {"usd": FMT_USD, "num": FMT_NUM, "text": FMT_TEXT, "pct": "0.00%"}

# House-styled cell vocabulary. Inputs sit on the CANVAS tint so reviewer-entry
# cells read differently from computed ones; computed values are plain INK.
_INPUT_FILL = PatternFill("solid", fgColor=KB.CANVAS)
_hair = Side(style="thin", color=KB.MIST)
_CELL_BORDER = Border(left=_hair, right=_hair, top=_hair, bottom=_hair)
_RIGHT = Alignment(horizontal="right", vertical="center")
_CENTER = Alignment(horizontal="center", vertical="center")


class LinesheetError(Exception):
    """Raised when a linesheet row or formula token cannot be resolved."""


@dataclass
class BuildContext:
    """Everything a linesheet needs to resolve cross-references and prefills."""

    pol_registry: dict[str, str] = field(default_factory=dict)  # threshold key -> '_config!$B$n'
    values: dict[str, Any] = field(default_factory=dict)        # row_id -> prefilled value
    rating_grades: tuple[str, ...] = ()                         # overlay's internal grades


class LinesheetBuilder:
    """Renders one program's linesheet config onto a worksheet for one loan."""

    def __init__(self, ws: Worksheet, program_sections: tuple[dict, ...],
                 title: str, subtitle: str, ctx: BuildContext) -> None:
        self.ws = ws
        self.sections = program_sections
        self.title = title
        self.subtitle = subtitle
        self.ctx = ctx
        self.row_cells: dict[str, str] = {}   # row_id -> unqualified same-sheet cell, e.g. 'C9'
        self._rating_dv: DataValidation | None = None

    # -- formula resolution ------------------------------------------------
    def _resolve_tokens(self, formula: str) -> str:
        text = formula

        def sub_row(m: re.Match) -> str:
            rid = m.group(1)
            if rid not in self.row_cells:
                raise LinesheetError(f"Unknown row id referenced: {{{rid}}}")
            return self.row_cells[rid]

        text = re.sub(r"\{([a-zA-Z0-9_]+)\}", sub_row, text)

        def sub_pol(m: re.Match) -> str:
            key = m.group(1)
            if key not in self.ctx.pol_registry:
                raise LinesheetError(f"Unknown policy threshold [POL {key}] — not in the "
                                     f"engagement overlay's thresholds")
            return self.ctx.pol_registry[key]

        text = re.sub(r"\[POL\s+([a-z0-9_]+)\]", sub_pol, text)
        return text

    # -- row writers -------------------------------------------------------
    def _write_value_row(self, row: int, item: dict, *, formula: str | None,
                         font: Font, fill: PatternFill | None,
                         align: Alignment, fmt: str) -> None:
        ws = self.ws
        label = ws.cell(row, COL_LABEL, item.get("label", ""))
        label.font = KB.DATA_FONT
        cell = ws.cell(row, COL_VALUE)
        if formula is not None:
            cell.value = formula
        else:
            cell.value = self.ctx.values.get(item.get("id", ""), None)
        cell.font = font
        if fill is not None:
            cell.fill = fill
        cell.border = _CELL_BORDER
        cell.alignment = align
        cell.number_format = fmt
        if item.get("note"):
            note = ws.cell(row, COL_NOTE, item["note"])
            note.font = KB.NOTE_FONT
            note.alignment = Alignment(wrap_text=True, vertical="center")
        rid = item.get("id")
        if rid:
            self.row_cells[rid] = f"{VALUE_LETTER}{row}"

    def _render_row(self, row: int, item: dict) -> int:
        kind = item.get("kind", "input")
        ws = self.ws

        if kind == "spacer":
            ws.row_dimensions[row].height = 6
            return row + 1
        if kind == "subhead":
            cell = ws.cell(row, COL_LABEL, item["label"])
            cell.font = Font(name="Arial", bold=True, size=10, color=KB.SLATE)
            return row + 1
        if kind == "note":
            cell = ws.cell(row, COL_LABEL, item["label"])
            cell.font = KB.NOTE_FONT
            return row + 1

        if kind in ("input", "input_num", "input_text"):
            fmt = _FMT[item.get("fmt", {"input": "usd", "input_num": "num",
                                        "input_text": "text"}[kind])]
            align = Alignment(horizontal="left", vertical="center") \
                if kind == "input_text" else _RIGHT
            self._write_value_row(row, item, formula=None, font=KB.DATA_FONT,
                                  fill=_INPUT_FILL, align=align, fmt=fmt)
            return row + 1

        if kind == "rating_input":
            self._write_value_row(row, item, formula=None, font=KB.DATA_FONT,
                                  fill=_INPUT_FILL, align=_CENTER, fmt=FMT_TEXT)
            if self.ctx.rating_grades:
                if self._rating_dv is None:
                    grades = ",".join(self.ctx.rating_grades)
                    self._rating_dv = DataValidation(
                        type="list", formula1=f'"{grades}"', allow_blank=True,
                        showErrorMessage=True,
                        error="Pick one of the bank's internal grades (see _config).")
                    self.ws.add_data_validation(self._rating_dv)
                self._rating_dv.add(self.ws.cell(row, COL_VALUE))
            return row + 1

        if kind == "computed":
            formula = "=" + self._resolve_tokens(item["formula"]).lstrip("=")
            self._write_value_row(row, item, formula=formula, font=KB.DATA_FONT,
                                  fill=None, align=_RIGHT,
                                  fmt=_FMT[item.get("fmt", "usd")])
            return row + 1

        if kind in RESERVED_KINDS:
            raise LinesheetError(
                f"Row kind {kind!r} is schema-reserved and not built yet "
                f"(rating validation is issue #61, exceptions/evidence are #62)")
        raise LinesheetError(f"Unknown row kind: {kind!r}")

    # -- public ------------------------------------------------------------
    def build(self) -> dict[str, str]:
        ws = self.ws
        KB.hide_gridlines(ws)
        for letter, width in {"A": 2, "B": 42, "C": 18, "D": 44}.items():
            ws.column_dimensions[letter].width = width

        row = KB.brand_banner(ws, 1, LAST_COL, self.title, self.subtitle)
        row += 1

        for section in self.sections:
            # Ink section band with the white Arial-bold label — the content-tab
            # section treatment (section_band's onyx is for system tabs).
            last = get_column_letter(LAST_COL)
            ws.merge_cells(f"B{row}:{last}{row}")
            band = ws.cell(row, COL_LABEL, section["title"])
            band.fill = KB.HDR_FILL
            band.font = KB.WHITE_BOLD
            band.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            ws.row_dimensions[row].height = 20
            row += 1
            for item in section.get("rows", []):
                row = self._render_row(row, item)
            row += 1  # gap between sections

        return dict(self.row_cells)
