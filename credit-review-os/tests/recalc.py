"""Recalc helper for tests: evaluate a built workbook with the `formulas` engine.

The workbook ships live Excel formulas; these helpers prove the credit logic is
correct *as evaluated by Excel semantics*, not just as Python — the same
recalc-spot-check discipline the credit-risk templates use.
"""

from __future__ import annotations

import os
import tempfile

import formulas


class Recalc:
    """Calculate a workbook once, then look cells up as ``('Sheet', 'C7')``."""

    def __init__(self, wb_bytes: bytes) -> None:
        # `formulas` loads from a path; keys embed the (upper-cased) file name.
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(wb_bytes)
            model = formulas.ExcelModel().loads(path).finish()
            self._solution = model.calculate()
            self._book = os.path.basename(path).upper()
        finally:
            os.unlink(path)

    def value(self, sheet: str, cell: str):
        key = f"'[{self._book}]{sheet.upper()}'!{cell.upper()}"
        for k, v in self._solution.items():
            if k.upper() == key:
                return v.value[0, 0]
        raise KeyError(f"cell {sheet}!{cell} not in recalc solution")
