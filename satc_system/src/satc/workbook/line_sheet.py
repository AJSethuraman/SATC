"""Config-driven line-sheet (workpaper) builder.

A return's workpaper is defined entirely by a YAML config (see
``configs/line_sheets/<RETURN>.yaml``). This builder renders the config to a
branded worksheet and wires up the formulas. It is the tax analogue of the CRR
config-driven segment builder.

Formula token grammar (resolved at build time so the workbook ships with live
Excel formulas, never hardcoded results):

  ``{line_id}``                    -> the value cell of another line on this sheet
  ``[XW JURIS param]``             -> a scalar tax-law value on the reference sheet
  ``[XW JURIS param subkey]``      -> a dict-valued tax-law value (e.g. by status)
  ``[XWFS JURIS param fs_line]``   -> tax-law value chosen by a filing-status cell
  ``[CF cf_key]``                  -> a carryforward value from the data mart

Row ``kind`` vocabulary: input / input_num / input_text / computed / total /
xwlink / xwfs / cflink / crosscheck / review / subhead / note / spacer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

from satc.workbook import components as X
from satc.workbook import styles as S
from satc.workbook.styles import C, NF

# Column layout (the value column is C / col 3).
COL_LABEL = 2
COL_VALUE = 3
COL_SOURCE = 4
COL_REVIEW = 5
COL_NOTE = 6
LAST_COL = 6
VALUE_LETTER = "C"

_FMT = {"usd": NF.USD, "num": NF.NUM, "pct": NF.PCT2, "text": NF.TEXT, "rate": NF.RATE_PER_MILE}

_FILING_ORDER = [("MFJ", "mfj"), ("HOH", "hoh"), ("MFS", "mfs"), ("QSS", "qss")]  # default -> single


class LineSheetError(Exception):
    """Raised when a line-sheet config or formula token cannot be resolved."""


@dataclass
class BuildContext:
    """Everything a line sheet needs to resolve cross-references."""

    xw_registry: dict[str, str] = field(default_factory=dict)   # crosswalk param -> 'Sheet!Cell'
    cf_registry: dict[str, str] = field(default_factory=dict)   # carryforward key -> 'Sheet!Cell'
    values: dict[str, Any] = field(default_factory=dict)        # line_id -> prefilled value
    default_jurisdiction: str = "US"


class LineSheetBuilder:
    """Renders one line-sheet config to a worksheet."""

    def __init__(self, ws: Worksheet, config: dict, ctx: BuildContext) -> None:
        self.ws = ws
        self.config = config
        self.ctx = ctx
        self.line_cells: dict[str, str] = {}   # line_id -> unqualified same-sheet cell, e.g. 'C12'
        self._crosscheck_rows: list[int] = []
        self._review_dv = None

    # -- formula resolution ------------------------------------------------
    def _resolve_tokens(self, formula: str) -> str:
        text = formula

        def sub_line(m: re.Match) -> str:
            lid = m.group(1)
            if lid not in self.line_cells:
                raise LineSheetError(f"Unknown line id referenced: {{{lid}}}")
            return self.line_cells[lid]

        text = re.sub(r"\{([a-zA-Z0-9_]+)\}", sub_line, text)

        def sub_xw(m: re.Match) -> str:
            juris, param, sub = m.group(1), m.group(2), m.group(3)
            key = f"{juris}:{param}" + (f":{sub}" if sub else "")
            if key not in self.ctx.xw_registry:
                raise LineSheetError(f"Unknown tax-law reference [XW {juris} {param} {sub or ''}]")
            return self.ctx.xw_registry[key]

        text = re.sub(r"\[XW\s+([A-Za-z]+)\s+([a-z0-9_]+)(?:\s+([a-z0-9_]+))?\]", sub_xw, text)

        def sub_xwfs(m: re.Match) -> str:
            juris, param, fs_line = m.group(1), m.group(2), m.group(3)
            if fs_line not in self.line_cells:
                raise LineSheetError(f"[XWFS] references unknown filing-status line {fs_line}")
            fs = self.line_cells[fs_line]

            def addr(sub: str) -> str:
                key = f"{juris}:{param}:{sub}"
                if key not in self.ctx.xw_registry:
                    raise LineSheetError(f"[XWFS] missing tax-law subkey {key}")
                return self.ctx.xw_registry[key]

            expr = addr("single")
            for label, sub in _FILING_ORDER:
                expr = f'IF(UPPER({fs})="{label}",{addr(sub)},{expr})'
            return expr

        text = re.sub(r"\[XWFS\s+([A-Za-z]+)\s+([a-z0-9_]+)\s+([a-zA-Z0-9_]+)\]", sub_xwfs, text)

        def sub_cf(m: re.Match) -> str:
            key = m.group(1)
            if key not in self.ctx.cf_registry:
                # Carryforward not present this year -> treat as zero, not an error.
                return "0"
            return self.ctx.cf_registry[key]

        text = re.sub(r"\[CF\s+([a-zA-Z0-9_:|.-]+)\]", sub_cf, text)
        return text

    # -- row writers -------------------------------------------------------
    def _write_value_row(self, row: int, item: dict, style: S.CellStyle, formula: str | None) -> None:
        ws = self.ws
        X.write(ws, row, COL_LABEL, item.get("label", ""), S.LABEL)
        fmt = _FMT.get(item.get("fmt", "usd"))
        if formula is not None:
            cell = X.write(ws, row, COL_VALUE, formula, style, number_format=fmt)
        else:
            prefill = self.ctx.values.get(item.get("id", ""), None)
            cell = X.write(ws, row, COL_VALUE, prefill, style, number_format=fmt)
        if item.get("source"):
            X.write(ws, row, COL_SOURCE, item["source"], S.LABEL_MUTED)
        if item.get("note"):
            X.write(ws, row, COL_NOTE, item["note"], S.NOTE)
        lid = item.get("id")
        if lid:
            self.line_cells[lid] = f"{VALUE_LETTER}{row}"

    def _add_review(self, row: int, gating: bool = False) -> None:
        if self._review_dv is None:
            self._review_dv = X.review_validation(self.ws)
        cell = self.ws.cell(row=row, column=COL_REVIEW)
        S.INPUT_TEXT.apply(cell)
        self._review_dv.add(cell)
        if gating:
            # Mark gating checklist cells with a subtle gold edge.
            cell.font = Font(name=S.BODY_FONT, size=10, color=C.GOLD_DEEP, bold=True)

    def _render_row(self, row: int, item: dict) -> int:
        kind = item.get("kind", "input")
        ws = self.ws

        if kind == "spacer":
            ws.row_dimensions[row].height = 6
            return row + 1
        if kind == "subhead":
            return X.subsection(ws, row, item["label"], LAST_COL, first_col=COL_LABEL)
        if kind == "note":
            return X.note_row(ws, row, item["label"], LAST_COL, first_col=COL_LABEL)

        if kind in ("input", "input_num", "input_text"):
            style = S.INPUT_TEXT if kind == "input_text" else S.INPUT
            if kind == "input_num" and "fmt" not in item:
                item = {**item, "fmt": "num"}
            self._write_value_row(row, item, style, formula=None)
            self._add_review(row, item.get("gating", False))
            return row + 1

        if kind in ("computed", "total"):
            style = S.COMPUTED_BOLD if kind == "total" else S.COMPUTED
            formula = "=" + self._resolve_tokens(item["formula"]).lstrip("=")
            self._write_value_row(row, item, style, formula=formula)
            return row + 1

        if kind == "xwlink":
            formula = "=" + self._resolve_tokens(item["formula"]).lstrip("=")
            self._write_value_row(row, item, S.LINK, formula=formula)
            return row + 1

        if kind == "xwfs":
            param = item["param"]
            fs_line = item.get("fs_line", "filing_status")
            juris = item.get("jurisdiction", self.ctx.default_jurisdiction)
            formula = "=" + self._resolve_tokens(f"[XWFS {juris} {param} {fs_line}]").lstrip("=")
            self._write_value_row(row, item, S.LINK, formula=formula)
            return row + 1

        if kind == "cflink":
            formula = "=" + self._resolve_tokens(item["formula"]).lstrip("=")
            self._write_value_row(row, item, S.CARRYFORWARD, formula=formula)
            return row + 1

        if kind == "crosscheck":
            formula = "=" + self._resolve_tokens(item["formula"]).lstrip("=")
            self._write_value_row(row, item, S.COMPUTED, formula=formula)
            if item.get("source") is None:
                X.write(ws, row, COL_SOURCE, "should tie to 0", S.LABEL_MUTED)
            self._crosscheck_rows.append(row)
            self._add_review(row, item.get("gating", False))
            return row + 1

        if kind == "review":
            X.write(ws, row, COL_LABEL, item["label"], S.LABEL)
            if item.get("source"):
                X.write(ws, row, COL_SOURCE, item["source"], S.LABEL_MUTED)
            self._add_review(row, item.get("gating", False))
            lid = item.get("id")
            if lid:
                self.line_cells[lid] = f"{chr(64 + COL_REVIEW)}{row}"
            return row + 1

        raise LineSheetError(f"Unknown row kind: {kind!r}")

    # -- public ------------------------------------------------------------
    def build(self) -> dict[str, str]:
        ws = self.ws
        meta = self.config.get("meta", {})
        S.paper_canvas(ws, max_col=LAST_COL + 1, max_row=400)
        X.set_widths(ws, {"A": 2, "B": 46, "C": 16, "D": 34, "E": 12, "F": 40})

        X.merge_text(ws, 1, COL_LABEL, LAST_COL, meta.get("title", "Workpaper"), S.TITLE)
        subtitle = meta.get("subtitle", "")
        if subtitle:
            X.merge_text(ws, 2, COL_LABEL, LAST_COL, subtitle, S.SUBTITLE)
        row = 4
        row = X.column_headers(
            ws, row, ["", "Line", "Amount", "Source / tie-out", "Review", "Note"], start_col=1)
        X.freeze(ws, "A" + str(row))

        for section in self.config.get("sections", []):
            row = X.section_header(ws, row, section["title"], LAST_COL, first_col=COL_LABEL)
            if section.get("columns"):
                row = X.column_headers(ws, row, [""] + section["columns"], start_col=1)
            for item in section.get("rows", []):
                row = self._render_row(row, item)
            row += 1  # gap between sections

        # Conditional formatting: crosscheck cells turn red unless they tie to zero.
        for cc_row in self._crosscheck_rows:
            addr = f"{VALUE_LETTER}{cc_row}"
            rule = FormulaRule(formula=[f"ABS({addr})>0.5"],
                               font=Font(name=S.BODY_FONT, color=C.RED, bold=True))
            ws.conditional_formatting.add(addr, rule)

        X.page_setup(ws, meta.get("title", "Workpaper"), orientation="portrait")
        return dict(self.line_cells)
