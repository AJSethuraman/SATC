"""Client delivery package sheet — refund/balance-due summary + draft comms.

Shows the per-jurisdiction aggregation (Federal + every state) and the DRAFT
delivery email and cover letter. Drafts only — never auto-sent. The client's
name is left as a merge-field placeholder so no PII enters the workbook (the
real salutation is filled from the vault at send time).
"""

from __future__ import annotations

from openpyxl.worksheet.worksheet import Worksheet

from satc.drake.comms import DeliverySummary, render_cover_letter, render_delivery_email
from satc.workbook import components as X
from satc.workbook import styles as S
from satc.workbook.styles import NF

_SALUTATION = "[client first name]"   # merge field; filled from the vault at send time


def _dump_text(ws: Worksheet, row: int, text: str, last_col: int = 9) -> int:
    for line in text.splitlines():
        X.merge_text(ws, row, 2, last_col, line if line.strip() else " ", S.NOTE)
        ws.row_dimensions[row].height = 13
        row += 1
    return row


def build_delivery_sheet(ws: Worksheet, summary: DeliverySummary) -> None:
    S.paper_canvas(ws, max_col=10, max_row=120)
    X.set_widths(ws, {"A": 2, "B": 16, "C": 12, "D": 10, "E": 12, "F": 12,
                      "G": 16, "H": 16, "I": 26, "J": 4})
    X.merge_text(ws, 1, 2, 9, "Client Delivery Package — DRAFT", S.TITLE)
    X.merge_text(ws, 2, 2, 9,
                 f"{summary.client_id}  ·  TY{summary.tax_year}  ·  preparer review required; "
                 "nothing is sent automatically.", S.SUBTITLE)
    row = 4

    row = X.section_header(ws, row, "Refund / balance-due summary (all jurisdictions)", 9, first_col=2)
    row = X.column_headers(ws, row, [
        "", "jurisdiction", "form", "method", "refund", "balance due", "due date",
        "e-file status", "how to pay / where to mail"], start_col=1)
    for r in summary.results:
        X.write(ws, row, 2, r.name, S.LABEL)
        X.write(ws, row, 3, r.form, S.LABEL_MUTED)
        X.write(ws, row, 4, "paper" if r.method == "paper" else "e-file", S.LABEL_MUTED)
        X.write(ws, row, 5, r.refund or None, S.COMPUTED, number_format=NF.USD)
        X.write(ws, row, 6, r.balance_due or None, S.COMPUTED, number_format=NF.USD)
        X.write(ws, row, 7, r.due_date, S.LABEL_MUTED)
        X.write(ws, row, 8, r.ef_status, S.LABEL_MUTED)
        X.write(ws, row, 9, r.pay_instructions, S.NOTE)
        row += 1
    net = summary.net_refund - summary.net_balance_due
    net_label = ("Net refund" if net > 0 else "Net balance due")
    X.write(ws, row, 2, net_label, S.LABEL)
    X.write(ws, row, 6, abs(net), S.COMPUTED_BOLD, number_format=NF.USD)
    row += 2

    row = X.section_header(ws, row, "Draft delivery email (review before sending)", 9, first_col=2)
    row = _dump_text(ws, row, render_delivery_email(summary, salutation=_SALUTATION))
    row += 1
    row = X.section_header(ws, row, "Draft cover letter", 9, first_col=2)
    row = _dump_text(ws, row, render_cover_letter(summary, salutation=_SALUTATION))

    X.page_setup(ws, "Client Delivery", orientation="portrait")
