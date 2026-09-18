"""Recalculate a built pack with the `formulas` engine and read cells back.

Prior art: credit-review-os/tests/recalc.py. The point is to read the
workbook the way Excel would: every formula evaluated, named cells resolved,
so a test asserts on what a reviewer sees rather than on what Python meant.
"""

from __future__ import annotations

import os
import tempfile

import formulas


class Recalc:
    def __init__(self, wb_bytes: bytes) -> None:
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(wb_bytes)
            model = formulas.ExcelModel().loads(path).finish()
            self._solution = model.calculate()
        finally:
            os.unlink(path)
        self._cells: dict[str, dict[str, object]] = {}
        for k, v in self._solution.items():
            ku = k.upper()
            if "]" not in ku or "'!" not in ku:
                continue
            sheet = ku.split("]")[1].split("'!")[0]
            cell = ku.split("'!")[1]
            self._cells.setdefault(sheet, {})[cell] = v.value[0][0]

    def value(self, sheet: str, cell: str):
        try:
            return self._cells[sheet.upper()][cell.upper()]
        except KeyError:
            raise KeyError(f"cell {sheet}!{cell} not in the recalculated solution")

    def column(self, sheet: str, col: str) -> dict[int, object]:
        out = {}
        for cell, v in self._cells.get(sheet.upper(), {}).items():
            if cell.startswith(col.upper()) and cell[len(col):].isdigit():
                out[int(cell[len(col):])] = v
        return out

    def find_text(self, sheet: str, needle: str) -> list[str]:
        return [str(v) for v in self._cells.get(sheet.upper(), {}).values()
                if isinstance(v, str) and needle in v]
