"""Document & communication repository sheet (audit trail) + missing-docs tracker.

Holds metadata + SharePoint links only — the files themselves stay in SharePoint.
Proves what was requested, sent, received, or signed, and drives the
missing-documents tracker (anything still in "Requested" status).
"""

from __future__ import annotations

from openpyxl.worksheet.worksheet import Worksheet

from satc.models.mart import DataMart
from satc.workbook import components as X
from satc.workbook import styles as S
from satc.workbook.styles import NF


def build_repository_sheet(ws: Worksheet, mart: DataMart) -> dict[str, object]:
    """Build the repository sheet. Returns the status-column range for dashboards."""
    S.paper_canvas(ws, max_col=11, max_row=max(60, len(mart.documents) + 25))
    X.set_widths(ws, {"A": 2, "B": 12, "C": 13, "D": 7, "E": 18, "F": 12,
                      "G": 12, "H": 10, "I": 30, "J": 30})
    X.merge_text(ws, 1, 2, 10, "Document & Communication Repository", S.TITLE)
    X.merge_text(ws, 2, 2, 10,
                 "Metadata + SharePoint links only — files stay in SharePoint. "
                 "Status: Requested / Received / Sent / Signed.", S.SUBTITLE)
    row = 4
    row = X.column_headers(ws, row, [
        "", "document_id", "client_id", "year", "doc type", "status",
        "date", "actor", "SharePoint link", "note"], start_col=1)
    X.freeze(ws, "A" + str(row))
    first = row
    for d in mart.documents:
        X.write(ws, row, 2, d.document_id, S.LABEL_MUTED)
        X.write(ws, row, 3, d.client_id, S.LABEL)
        X.write(ws, row, 4, d.tax_year, S.LABEL_MUTED, number_format=NF.YEAR)
        X.write(ws, row, 5, d.doc_type, S.LABEL)
        # Outstanding requests flagged red; everything else normal.
        X.write(ws, row, 6, d.status, S.EXCEPTION if d.status == "Requested" else S.LABEL)
        X.write(ws, row, 7, d.as_of.isoformat() if d.as_of else "", S.LABEL_MUTED)
        X.write(ws, row, 8, d.actor, S.LABEL_MUTED)
        X.write(ws, row, 9, d.sharepoint_link or "—", S.NOTE)
        X.write(ws, row, 10, d.note, S.NOTE)
        row += 1
    last = row - 1

    row += 1
    row = X.section_header(ws, row, "Missing-documents tracker (outstanding requests)", 10, first_col=2)
    outstanding = [d for d in mart.documents if d.status == "Requested"]
    if not outstanding:
        X.merge_text(ws, row, 2, 10, "No outstanding document requests.", S.NOTE)
        row += 1
    for d in outstanding:
        X.write(ws, row, 2, d.client_id, S.LABEL)
        X.write(ws, row, 3, d.doc_type, S.EXCEPTION)
        X.merge_text(ws, row, 5, 10, d.note or "Requested — not yet received", S.NOTE)
        row += 1

    X.page_setup(ws, "Document Repository", orientation="landscape")
    return {"sheet": ws.title, "status": "F", "first": first, "last": last}
