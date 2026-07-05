"""``Master`` — the portfolio-at-a-glance roll-up.

One row per loan; **every data cell is a formula referencing that loan's
linesheet** (or the ``_config`` lookup blocks) — no recomputation, no
hardcoded results. The regulatory bucket derives from the reviewer's
independent rating when keyed, falling back to the originator's; the
criticized/classified flags derive from the bucket via the rating-framework
block on ``_config``.
"""

from __future__ import annotations

from dataclasses import dataclass

from openpyxl.styles import Alignment
from openpyxl.worksheet.worksheet import Worksheet

from credit_review import keybank_style as KB
from credit_review.config import Engagement, Loan
from credit_review.findings import FindingsRefs
from credit_review.linesheet import FMT_NUM, FMT_USD

_COLS = ["Loan", "Borrower", "Loan #", "Committed", "Outstanding",
         "Orig rating", "Rev rating", "Bucket", "Criticized", "Classified",
         "Open exc"]


@dataclass(frozen=True)
class MasterRefs:
    """Register geometry for downstream aggregation (asset-quality summary)."""

    first_row: int
    last_row: int
    outstanding_col: str = "E"
    committed_col: str = "D"
    criticized_col: str = "I"
    classified_col: str = "J"


def build_master(ws: Worksheet, engagement: Engagement,
                 per_loan: list[tuple[Loan, dict[str, str]]],
                 map_range: str, framework_range: str,
                 findings: FindingsRefs) -> MasterRefs:
    """``per_loan`` pairs each loan with its linesheet's row_id -> cell map."""
    KB.hide_gridlines(ws)
    widths = {"A": 12, "B": 30, "C": 12, "D": 13, "E": 13, "F": 10, "G": 10,
              "H": 16, "I": 10, "J": 10, "K": 9}
    for letter, width in widths.items():
        ws.column_dimensions[letter].width = width

    row = KB.brand_banner(
        ws, 1, len(_COLS), "Master — Portfolio Roll-up",
        f"{engagement.client_name}  ·  {engagement.engagement_id}")
    row = KB.header_row(ws, row, _COLS, right_from=3, center_cols=(5, 6, 7, 8, 9, 10))
    KB.freeze_below(ws, row - 1)

    first = row
    for loan, cells in per_loan:
        sheet = f"'{loan.sheet_name}'"

        def ref(row_id: str) -> str:
            return f"{sheet}!{cells[row_id]}"

        orig, rev = ref("rating_originator"), ref("rating_reviewer")
        bucket = (f"=IFERROR(IF({rev}=\"\","
                  f"VLOOKUP({orig},{map_range},2,FALSE),"
                  f"VLOOKUP({rev},{map_range},2,FALSE)),\"\")")
        bucket_cell = f"$H{row}"

        def text_ref(addr: str) -> str:
            # a bare =ref renders a blank source cell as 0 — keep blanks blank
            return f'=IF({addr}="","",{addr})'

        values = [
            (1, loan.loan_id, None, "left"),
            (2, text_ref(ref("borrower_name")), None, "left"),
            (3, text_ref(ref("loan_number")), None, "left"),
            (4, f"={ref('total_commitment')}", FMT_USD, "right"),
            (5, f"={ref('outstanding')}", FMT_USD, "right"),
            (6, text_ref(orig), None, "center"),
            (7, text_ref(rev), None, "center"),
            (8, bucket, None, "center"),
            (9, f'=IFERROR(VLOOKUP({bucket_cell},{framework_range},2,FALSE)="TRUE",FALSE)',
             None, "center"),
            (10, f'=IFERROR(VLOOKUP({bucket_cell},{framework_range},3,FALSE)="TRUE",FALSE)',
             None, "center"),
            (11, findings.open_count_formula(("A", loan.loan_id)), FMT_NUM, "center"),
        ]
        for col, value, fmt, align in values:
            cell = ws.cell(row, col, value)
            cell.font = KB.DATA_FONT
            cell.alignment = Alignment(horizontal=align, vertical="center")
            if fmt:
                cell.number_format = fmt
        row += 1

    return MasterRefs(first_row=first, last_row=row - 1)
