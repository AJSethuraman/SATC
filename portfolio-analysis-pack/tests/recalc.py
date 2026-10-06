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
    def __init__(self, wb_bytes: bytes, inputs: dict[tuple[str, str], object] | None = None) -> None:
        """`inputs` overrides cells before calculating, keyed by (sheet, cell):
        the way a reviewer moves a knob on _config and watches the words move."""
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(wb_bytes)
            model = formulas.ExcelModel().loads(path).finish()
            book = os.path.basename(path)          # the engine keys inputs by the file name as written
            if inputs:
                keyed = {f"'[{book}]{sheet.upper()}'!{cell.upper()}": value for (sheet, cell), value in inputs.items()}
                self._solution = model.calculate(inputs=keyed)
            else:
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
            val = v.value[0][0] if hasattr(v, "value") else v      # an overridden input comes back as a plain value
            self._cells.setdefault(sheet, {})[cell] = val

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

    def exact(self, sheet: str, values: set[str]) -> list[str]:
        """Every cell on the sheet whose whole value is one of `values`."""
        return [str(v) for v in self._cells.get(sheet.upper(), {}).values() if isinstance(v, str) and v in values]

    def find_text(self, sheet: str, needle: str) -> list[str]:
        return [str(v) for v in self._cells.get(sheet.upper(), {}).values()
                if isinstance(v, str) and needle in v]
