"""FRED's two-argument assemble, over the shared packager."""

from __future__ import annotations

import os

from credit_suite.engine import package


def assemble(base_xlsx: str, out_xlsm: str, macro_bas: str = None) -> str:
    """Wrap FRED's base .xlsx into the macro-enabled .xlsm."""
    macro_bas = macro_bas or os.path.join(os.path.dirname(__file__), "macro.bas")
    return package.assemble(base_xlsx, out_xlsm, macro_bas, "FREDDashboard")
