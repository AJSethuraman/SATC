"""Tax-law reference sheet builder + cell registry.

Renders one :class:`~satc.crosswalk.Crosswalk` (one tax_year x jurisdiction) onto a
worksheet, laying every parameter into a stable cell with its citation and status.
Returns a *registry* mapping ``"<JURIS>:<param>"`` (and ``":<subkey>"`` for dict
parameters) to the cell address that holds the value, so line-sheet formulas can
LINK to a tax-law value instead of hardcoding it.

Pending / scheduled-reversion values are written in red as gaps (never a guessed
number) and are intentionally not registered as usable numerics.
"""

from __future__ import annotations

from openpyxl.worksheet.worksheet import Worksheet

from satc.crosswalk import Crosswalk
from satc.workbook import components as X
from satc.workbook import styles as S
from satc.workbook.styles import C, NF

# Parameters rendered as a bracket sub-table rather than a single value.
_LIST_PARAMS_SUFFIX = ("brackets_single", "brackets_mfj", "brackets_mfs", "brackets_hoh",
                       "brackets_nonbusiness")


def _unit_format(unit: str) -> str:
    if unit in ("usd",):
        return NF.USD
    if unit == "usd_per_mile":
        return NF.RATE_PER_MILE
    if unit == "ratio":
        return NF.PCT2
    return NF.TEXT


def build_reference_sheet(ws: Worksheet, xwalk: Crosswalk) -> dict[str, str]:
    """Build the reference sheet and return ``{registry_key: 'Sheet!Cell'}``."""
    registry: dict[str, str] = {}
    # Quote the sheet name so cross-sheet formula references survive spaces.
    sheet = f"'{ws.title}'"
    juris = xwalk.jurisdiction

    S.paper_canvas(ws, max_col=8, max_row=160)
    X.set_widths(ws, {"A": 2, "B": 34, "C": 16, "D": 14, "E": 10, "F": 18, "G": 52})

    X.merge_text(ws, 1, 2, 7, f"Tax Law Reference — {juris} {xwalk.tax_year}", S.TITLE)
    X.merge_text(ws, 2, 2, 7, f"Source: {xwalk.source_label}   ·   Retrieved: {xwalk.retrieved}"
                              f"   ·   Status: {xwalk.status}", S.SUBTITLE)
    row = 3
    if xwalk.notes:
        row = X.note_row(ws, row, xwalk.notes.strip(), last_col=7, first_col=2)
    row += 1

    row = X.column_headers(ws, row, ["", "Parameter", "Value", "Sub-key", "Unit", "Status", "Citation"],
                           start_col=1)
    X.freeze(ws, "A" + str(row))

    for name, param in xwalk.params.items():
        is_list = any(name == s or name.endswith(s) for s in _LIST_PARAMS_SUFFIX)

        if param.is_pending:
            X.write(ws, row, 2, name, S.LABEL)
            X.write(ws, row, 3, "PENDING", S.EXCEPTION)
            X.write(ws, row, 6, param.status, S.NOTE)
            X.merge_text(ws, row, 7, 7, (param.pending_reason or param.citation).strip(), S.NOTE)
            ws.row_dimensions[row].height = max(14, 12 + 6 * (len(param.pending_reason) // 60))
            row += 1
            continue

        if is_list and isinstance(param.value, list):
            X.write(ws, row, 2, name, S.LABEL)
            X.write(ws, row, 6, param.status, S.NOTE)
            X.merge_text(ws, row, 7, 7, param.citation, S.NOTE)
            row += 1
            for i, tier in enumerate(param.value):
                rate = tier.get("rate")
                upto = tier.get("up_to")
                X.write(ws, row, 2, f"   rate {i + 1}", S.LABEL_MUTED)
                vcell = X.write(ws, row, 3, rate, S.LINK, number_format=NF.PCT2)
                X.write(ws, row, 4, "up to", S.LABEL_MUTED)
                X.write(ws, row, 5, upto if upto is not None else "no cap", S.COMPUTED,
                        number_format=NF.USD if upto is not None else NF.TEXT)
                registry[f"{juris}:{name}:{i}:rate"] = f"{sheet}!{vcell.coordinate}"
                row += 1
            continue

        if isinstance(param.value, dict):
            X.write(ws, row, 2, name, S.LABEL)
            X.write(ws, row, 6, param.status, S.NOTE)
            X.merge_text(ws, row, 7, 7, param.citation, S.NOTE)
            row += 1
            for sub, val in param.value.items():
                X.write(ws, row, 2, f"   {sub}", S.LABEL_MUTED)
                vcell = X.write(ws, row, 3, val, S.LINK, number_format=_unit_format(param.unit))
                X.write(ws, row, 4, sub, S.LABEL_MUTED)
                X.write(ws, row, 5, param.unit, S.LABEL_MUTED)
                registry[f"{juris}:{name}:{sub}"] = f"{sheet}!{vcell.coordinate}"
                row += 1
            continue

        if isinstance(param.value, list):
            # Generic list (e.g. filing_statuses, a rate schedule) -> reference text only.
            X.write(ws, row, 2, name, S.LABEL)
            X.write(ws, row, 3, ", ".join(str(x) for x in param.value), S.LABEL_MUTED)
            X.write(ws, row, 6, param.status, S.NOTE)
            X.merge_text(ws, row, 7, 7, param.citation, S.NOTE)
            row += 1
            continue

        # Scalar value
        X.write(ws, row, 2, name, S.LABEL)
        vcell = X.write(ws, row, 3, param.value, S.LINK, number_format=_unit_format(param.unit))
        X.write(ws, row, 5, param.unit, S.LABEL_MUTED)
        X.write(ws, row, 6, param.status, S.NOTE)
        X.merge_text(ws, row, 7, 7, param.citation, S.NOTE)
        registry[f"{juris}:{name}"] = f"{sheet}!{vcell.coordinate}"
        row += 1

    X.page_setup(ws, f"Tax Law {juris} {xwalk.tax_year}", orientation="landscape")
    return registry
