"""The staging / confirmation gate as a workbook sheet (human-in-the-loop UI).

Lists every extracted field with its value, confidence, provenance and status, and
a Confirm dropdown. Only rows the preparer confirms feed the line sheets. Fields
the extractor could not parse are pre-flagged NEEDS_REVIEW in red — never guessed.
"""

from __future__ import annotations

from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from satc.ingest.staging_gate import StagingGate
from satc.workbook import components as X
from satc.workbook import styles as S
from satc.workbook.styles import C, NF

_STATUS_CHOICES = ["CONFIRMED", "NEEDS_REVIEW", "REJECTED"]


def build_staging_sheet(ws: Worksheet, gate: StagingGate) -> None:
    S.paper_canvas(ws, max_col=10, max_row=max(60, len(gate.all_fields()) + 20))
    X.set_widths(ws, {"A": 2, "B": 12, "C": 13, "D": 26, "E": 18, "F": 13,
                      "G": 13, "H": 15, "I": 13, "J": 30})

    X.merge_text(ws, 1, 2, 10, "Staging & Confirmation Gate", S.TITLE)
    X.merge_text(ws, 2, 2, 10,
                 "Nothing flows into a workpaper until it is CONFIRMED here. "
                 "Unparseable values are flagged for review — never guessed.", S.SUBTITLE)

    s = gate.summary()
    X.merge_text(ws, 3, 2, 10,
                 f"Confirmed {s['CONFIRMED']}   ·   Needs review "
                 f"{s['NEEDS_REVIEW'] + s['STAGED']}   ·   Rejected {s['REJECTED']}", S.LABEL)

    row = 5
    row = X.column_headers(ws, row, [
        "", "Document", "Doc type", "Field", "Staged value", "Amount",
        "Confidence", "Status", "Confirm", "Provenance"], start_col=1)
    X.freeze(ws, "A" + str(row))

    dv = DataValidation(type="list", formula1='"' + ",".join(_STATUS_CHOICES) + '"',
                        allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)

    for fld in gate.all_fields():
        X.write(ws, row, 2, fld.document_id, S.LABEL)
        X.write(ws, row, 3, gate_doc_type(gate, fld.document_id), S.LABEL_MUTED)
        X.write(ws, row, 4, fld.label, S.LABEL)
        X.write(ws, row, 5, fld.effective_text(), S.INPUT_TEXT)
        amt = fld.effective_amount()
        X.write(ws, row, 6, float(amt) if amt is not None else None, S.COMPUTED, number_format=NF.USD)
        X.write(ws, row, 7, fld.provenance.confidence, S.LABEL_MUTED)
        status_style = S.EXCEPTION if fld.status in ("NEEDS_REVIEW", "STAGED") else S.LABEL
        X.write(ws, row, 8, fld.status, status_style)
        confirm_cell = ws.cell(row=row, column=9,
                               value=("CONFIRMED" if fld.status == "CONFIRMED" else "NEEDS_REVIEW"))
        S.INPUT_TEXT.apply(confirm_cell)
        dv.add(confirm_cell)
        X.write(ws, row, 10, fld.provenance.short_source(), S.NOTE)
        row += 1

    X.page_setup(ws, "Staging & Confirmation", orientation="landscape")


def gate_doc_type(gate: StagingGate, document_id: str) -> str:
    for doc in gate.documents:
        if doc.document_id == document_id:
            return str(doc.doc_type)
    return ""
