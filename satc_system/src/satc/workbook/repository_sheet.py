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
    _rows = len(mart.requested_items) + len(mart.received_documents)
    S.paper_canvas(ws, max_col=11, max_row=max(60, _rows + 25))
    X.set_widths(ws, {"A": 2, "B": 12, "C": 13, "D": 7, "E": 18, "F": 12,
                      "G": 12, "H": 10, "I": 30, "J": 30})
    X.merge_text(ws, 1, 2, 10, "Document & Communication Repository", S.TITLE)
    X.merge_text(ws, 2, 2, 10,
                 "Metadata + SharePoint links only — files stay in SharePoint. "
                 "Status: Requested / Received / Sent / Signed.", S.SUBTITLE)
    row = 4
    # One sheet, both registers — an "asked for" row and an "arrived" row are
    # visibly different kinds now, rather than one row with a status string that
    # meant four different things.
    row = X.column_headers(ws, row, [
        "", "id", "client_id", "year", "doc type", "kind / status",
        "date", "how obtained", "blocks", "note"], start_col=1)
    X.freeze(ws, "A" + str(row))
    first = row
    for i in mart.requested_items:
        X.write(ws, row, 2, i.request_id, S.LABEL_MUTED)
        X.write(ws, row, 3, i.client_id, S.LABEL)
        X.write(ws, row, 4, i.tax_year, S.LABEL_MUTED, number_format=NF.YEAR)
        X.write(ws, row, 5, i.doc_type, S.LABEL)
        X.write(ws, row, 6, f"asked · {i.status}",
                S.EXCEPTION if i.is_open else S.LABEL)
        X.write(ws, row, 7, i.requested_at.isoformat() if i.requested_at else "",
                S.LABEL_MUTED)
        X.write(ws, row, 8, "", S.LABEL_MUTED)
        X.write(ws, row, 9, i.blocking, S.LABEL_MUTED)
        X.write(ws, row, 10, i.not_applicable_reason or i.request_text, S.NOTE)
        row += 1
    for d in mart.received_documents:
        X.write(ws, row, 2, d.document_id, S.LABEL_MUTED)
        X.write(ws, row, 3, d.client_id, S.LABEL)
        X.write(ws, row, 4, d.tax_year, S.LABEL_MUTED, number_format=NF.YEAR)
        X.write(ws, row, 5, d.doc_type, S.LABEL)
        X.write(ws, row, 6, "arrived", S.LABEL)
        X.write(ws, row, 7, d.obtained_at.date().isoformat() if d.obtained_at else "",
                S.LABEL_MUTED)
        # How and from whom — 26 CFR §1.6695-2(b)(4)(i)(C). The display NAME is
        # deliberately absent: filenames carry the client's own name.
        X.write(ws, row, 8, f"{d.obtained_how}"
                            f"{' · ' + d.furnished_by if d.furnished_by else ''}",
                S.LABEL_MUTED)
        X.write(ws, row, 9, "", S.LABEL_MUTED)
        X.write(ws, row, 10, d.note, S.NOTE)
        row += 1
    last = row - 1

    row += 1
    row = X.section_header(ws, row, "Missing-documents tracker (outstanding requests)", 10, first_col=2)
    outstanding = [i for i in mart.requested_items if i.is_open]
    if not outstanding:
        X.merge_text(ws, row, 2, 10, "No outstanding document requests.", S.NOTE)
        row += 1
    for i in outstanding:
        X.write(ws, row, 2, i.client_id, S.LABEL)
        X.write(ws, row, 3, i.doc_type, S.EXCEPTION)
        blocks = (" [blocks prep]" if i.blocks_prep
                  else " [blocks filing]" if i.blocks_transmission else "")
        X.merge_text(ws, row, 5, 10,
                     (i.request_text or "Requested — not yet received") + blocks, S.NOTE)
        row += 1

    X.page_setup(ws, "Document Repository", orientation="landscape")
    return {"sheet": ws.title, "status": "F", "first": first, "last": last}
