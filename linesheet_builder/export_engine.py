from __future__ import annotations
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from .models import ExportResult
from .db import now
from .audit import append_audit_event, export_audit_log
from .review_engine import calculate_completion_status
from .template_engine import get_applicable_questions

ROOT = Path(__file__).resolve().parents[1]

# --- Palette -----------------------------------------------------------------
NAVY   = "1F3A5F"   # primary brand
INK    = "13263D"   # darkest band
GOLD   = "C8A24B"   # accent rule
BAND   = "EEF2F8"   # zebra band
LINE   = "D7DEE8"   # hairline borders
WHITE  = "FFFFFF"
MUTED  = "5B6B7B"   # secondary text
# status / severity chips (fill, text)
GREEN_F, GREEN_T = "DCF1E5", "1E7F4F"
AMBER_F, AMBER_T = "FBE9C7", "8A5A00"
RED_F,   RED_T   = "F7D9D9", "9B1C1C"
SLATE_F, SLATE_T = "E7ECF3", "5B6B7B"

FONT = "Calibri"
_HAIR = Side(style="thin", color=LINE)
BOTTOM = Border(bottom=_HAIR)

CHIP = {
    "Complete": (GREEN_F, GREEN_T), "Ready": (GREEN_F, GREEN_T), "QC Approved": (GREEN_F, GREEN_T),
    "Ready for QC": (GREEN_F, GREEN_T), "Pass": (GREEN_F, GREEN_T), "Attached": (GREEN_F, GREEN_T),
    "Waived": (GREEN_F, GREEN_T),
    "Warning": (AMBER_F, AMBER_T), "Needs Review": (AMBER_F, AMBER_T), "Needed": (AMBER_F, AMBER_T),
    "Exception": (RED_F, RED_T), "Finding": (RED_F, RED_T), "Blocked": (RED_F, RED_T), "Open": (RED_F, RED_T),
    "Incomplete": (SLATE_F, SLATE_T), "Not Started": (SLATE_F, SLATE_T), "Not Required": (SLATE_F, SLATE_T),
}

def _fill(color): return PatternFill("solid", fgColor=color)

def _ctx(conn, review_case_id):
    row = conn.execute("""SELECT rc.*, e.review_period,e.template_id,e.reviewer_name,e.qc_reviewer_name,c.client_name,lr.* FROM review_cases rc JOIN engagements e ON rc.engagement_id=e.engagement_id JOIN clients c ON e.client_id=c.client_id JOIN loan_records lr ON rc.loan_record_id=lr.loan_record_id WHERE rc.review_case_id=?""", (review_case_id,)).fetchone()
    return {k: row[k] for k in row.keys()}

def assert_export_allowed(conn, review_case_id, loan_record, template, override_reason=None):
    status = calculate_completion_status(conn, review_case_id, loan_record, template)
    if status["export_ready"] or override_reason: return status
    raise ValueError("Export blocked: " + "; ".join(status["blockers"] or ["Review status must be Ready for QC or QC Approved"]))

# --- Styling helpers ---------------------------------------------------------
def _short_date(v):
    s = "" if v is None else str(v)
    return s[:10] if len(s) >= 10 and s[4] == "-" and "T" in s else s

def _table_header(ws, headers, row=1):
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=i, value=h)
        c.fill = _fill(NAVY)
        c.font = Font(name=FONT, color=WHITE, bold=True, size=10)
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
        c.border = Border(bottom=Side(style="medium", color=GOLD))
    ws.row_dimensions[row].height = 24

def _chip(cell):
    style = CHIP.get(str(cell.value or "").strip())
    if style:
        fill, text = style
        cell.fill = _fill(fill)
        cell.font = Font(name=FONT, color=text, bold=True, size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center")

def _finish_table(ws, header_row, ncols, chip_cols=(), widths=None, landscape=False):
    """Zebra-band, border, freeze, autofilter and lay out a simple table."""
    last = ws.max_row
    for r in range(header_row + 1, last + 1):
        band = _fill(BAND) if (r - header_row) % 2 == 0 else _fill(WHITE)
        for cidx in range(1, ncols + 1):
            c = ws.cell(row=r, column=cidx)
            c.fill = band
            c.border = BOTTOM
            c.font = Font(name=FONT, size=10)
            c.alignment = Alignment(vertical="center", wrap_text=cidx not in chip_cols)
        for cidx in chip_cols:
            _chip(ws.cell(row=r, column=cidx))
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    if last >= header_row:
        ws.auto_filter.ref = f"A{header_row}:{get_column_letter(ncols)}{last}"
    ws.sheet_view.showGridLines = False
    ws.print_options.horizontalCentered = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    if landscape:
        ws.page_setup.orientation = "landscape"

# --- Cover -------------------------------------------------------------------
def _build_cover(ws, ctx, template, metrics):
    ws.sheet_view.showGridLines = False
    widths = [2.5, 22, 30, 4, 18, 22]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # gold top rule
    ws.merge_cells("A1:F1"); ws.row_dimensions[1].height = 5
    ws["A1"].fill = _fill(GOLD)
    # banner
    ws.merge_cells("A2:F2"); ws.row_dimensions[2].height = 40
    t = ws["A2"]; t.value = "LINESHEET BUILDER"
    t.fill = _fill(NAVY); t.font = Font(name=FONT, color=WHITE, bold=True, size=22)
    t.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    ws.merge_cells("A3:F3"); ws.row_dimensions[3].height = 22
    s = ws["A3"]; s.value = "Audit-Ready Commercial Loan Linesheet"
    s.fill = _fill(NAVY); s.font = Font(name=FONT, color="C9D6E5", italic=True, size=11)
    s.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    for addr in ("A2", "A3"):
        for col in range(1, 7):
            ws.cell(row=int(addr[1:]), column=col).fill = _fill(NAVY)
    ws.merge_cells("A4:F4"); ws.row_dimensions[4].height = 5
    ws["A4"].fill = _fill(GOLD)

    # KPI strip (row 6-8)
    kpis = [
        ("OVERALL STATUS", ctx["status"], True),
        ("COMPLETION", f"{metrics['completion_pct']}%", False),
        ("FINDINGS", str(metrics["findings"]), False),
        ("EVIDENCE OPEN", str(metrics["evidence_open"]), False),
    ]
    ws.row_dimensions[6].height = 8
    cells = ["B", "C", "D", "E"]
    for (label, value, is_status), col in zip(kpis, cells):
        lab = ws[f"{col}7"]; lab.value = label
        lab.font = Font(name=FONT, color=MUTED, bold=True, size=8)
        lab.alignment = Alignment(horizontal="center")
        lab.fill = _fill(BAND); lab.border = Border(top=_HAIR, left=_HAIR, right=_HAIR)
        val = ws[f"{col}8"]; val.value = value
        val.alignment = Alignment(horizontal="center", vertical="center")
        val.fill = _fill(BAND); val.border = Border(bottom=_HAIR, left=_HAIR, right=_HAIR)
        if is_status:
            style = CHIP.get(str(value).strip(), (NAVY, WHITE))
            val.fill = _fill(style[0]); val.font = Font(name=FONT, color=style[1], bold=True, size=13)
        else:
            val.font = Font(name=FONT, color=NAVY, bold=True, size=16)
    ws.row_dimensions[8].height = 30

    # Engagement detail card (rows 10+)
    ws["B10"] = "ENGAGEMENT"
    ws["B10"].font = Font(name=FONT, color=GOLD, bold=True, size=10)
    rows = [
        ("Client", ctx["client_name"]),
        ("Review period", ctx["review_period"]),
        ("Template", f"{template.template_name}  ·  v{template.version}"),
        ("Loan ID", ctx["loan_id"]),
        ("Borrower", ctx["borrower_name"]),
        ("Product type", ctx.get("product_type")),
        ("Reviewer", ctx["reviewer_name"]),
        ("QC reviewer", ctx["qc_reviewer_name"]),
        ("Generated", _short_date(now()) + "  " + now()[11:19]),
    ]
    r0 = 11
    for i, (label, value) in enumerate(rows):
        r = r0 + i
        lc = ws.cell(row=r, column=2, value=label)
        lc.font = Font(name=FONT, color=MUTED, bold=True, size=10)
        lc.alignment = Alignment(vertical="center")
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=6)
        vc = ws.cell(row=r, column=3, value=value)
        vc.font = Font(name=FONT, color=INK, size=10)
        vc.alignment = Alignment(vertical="center")
        for col in range(2, 7):
            ws.cell(row=r, column=col).border = BOTTOM

    foot = r0 + len(rows) + 1
    ws.merge_cells(start_row=foot, start_column=2, end_row=foot, end_column=6)
    fc = ws.cell(row=foot, column=2, value="Confidential — prepared for internal credit review. Generated by Linesheet Builder.")
    fc.font = Font(name=FONT, color=MUTED, italic=True, size=8)
    ws.page_setup.orientation = "portrait"

# --- Main export -------------------------------------------------------------
def generate_excel_linesheet(conn, review_case_id: int, template, output_dir: str | Path = ROOT / "outputs" / "excel", generated_by="system", override_reason=None):
    ctx = _ctx(conn, review_case_id); loan = ctx.copy()
    assert_export_allowed(conn, review_case_id, loan, template, override_reason)
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"linesheet_{ctx['loan_id']}_{now().replace(':','')}.xlsx"

    applicable = get_applicable_questions(loan, template)
    ans = {r["question_id"]: r for r in conn.execute("SELECT * FROM review_answers WHERE review_case_id=?", (review_case_id,)).fetchall()}
    exceptions = conn.execute("SELECT * FROM exceptions WHERE review_case_id=?", (review_case_id,)).fetchall()
    completion = calculate_completion_status(conn, review_case_id, loan, template)
    evidence_open = sum(1 for _, q in applicable if (a := ans.get(q.question_id)) and a["evidence_required"] and a["evidence_status"] not in ("Attached", "Waived"))
    metrics = {"completion_pct": completion["completion_pct"], "findings": len(exceptions), "evidence_open": evidence_open}

    wb = Workbook()
    wb.properties.title = f"Linesheet — {ctx['loan_id']} {ctx['borrower_name']}"
    wb.properties.creator = "Linesheet Builder"

    # Cover
    ws = wb.active; ws.title = "Cover"
    _build_cover(ws, ctx, template, metrics)

    # Loan Summary
    ws = wb.create_sheet("Loan Summary")
    _table_header(ws, ["Field", "Value"])
    summary = [
        ("Loan ID", ctx.get("loan_id"), None), ("Borrower", ctx.get("borrower_name"), None),
        ("Product type", ctx.get("product_type"), None),
        ("Commitment amount", ctx.get("commitment_amount"), "$#,##0"),
        ("Outstanding balance", ctx.get("outstanding_balance"), "$#,##0"),
        ("Origination date", _short_date(ctx.get("origination_date")), None),
        ("Maturity date", _short_date(ctx.get("maturity_date")), None),
        ("Risk rating", ctx.get("risk_rating"), None), ("Officer", ctx.get("officer"), None),
        ("Collateral type", ctx.get("collateral_type"), None), ("Guarantor", ctx.get("guarantor_name"), None),
        ("DSCR", ctx.get("dscr"), '0.00"x"'), ("LTV", ctx.get("ltv"), '0"%"'),
        ("Validation status", ctx.get("validation_status"), None),
    ]
    for label, value, fmt in summary:
        ws.append([label, value])
        if fmt and isinstance(value, (int, float)):
            ws.cell(row=ws.max_row, column=2).number_format = fmt
    _finish_table(ws, 1, 2, chip_cols=(), widths=[24, 34])
    # bold the field labels; chip the validation status value
    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=1).font = Font(name=FONT, size=10, bold=True, color=NAVY)
    _chip(ws.cell(row=ws.max_row, column=2))

    # Linesheet Questions  (header MUST remain at row 1, A1 == "Section")
    ws = wb.create_sheet("Linesheet Questions")
    _table_header(ws, ["Section", "ID", "Question", "Answer", "Source Value", "Status", "Severity", "Reviewer Comment", "Evidence"])
    prev_section = None
    for sec, q in applicable:
        a = ans.get(q.question_id)
        section_label = sec.section_name if sec.section_name != prev_section else ""
        prev_section = sec.section_name
        ws.append([
            section_label, q.question_id, q.question_text,
            a["answer_value"] if a else "",
            _short_date(a["source_value"]) if a else (_short_date(ctx.get(q.source_field)) if q.source_field else ""),
            a["answer_status"] if a else "Incomplete",
            a["severity"] if a else "",
            a["reviewer_comment"] if a else "",
            a["evidence_status"] if a else "Not Required",
        ])
    _finish_table(ws, 1, 9, chip_cols=(6, 7, 9), widths=[20, 6, 46, 12, 16, 13, 13, 34, 12], landscape=True)
    for r in range(2, ws.max_row + 1):
        ws.cell(row=r, column=1).font = Font(name=FONT, size=10, bold=True, color=NAVY)
        ws.cell(row=r, column=2).font = Font(name=FONT, size=9, color=MUTED)

    # Exceptions & Findings
    ws = wb.create_sheet("Exceptions & Findings")
    _table_header(ws, ["ID", "Section", "Question", "Issue", "Severity", "Status", "Reviewer Comment", "Evidence"])
    if exceptions:
        for e in exceptions:
            ws.append([e["exception_id"], e["section_id"], e["question_id"], e["issue_text"], e["severity"], e["status"], e["reviewer_comment"], e["evidence_status"]])
    else:
        ws.append(["", "", "", "No findings or exceptions recorded for this loan.", "", "", "", ""])
    _finish_table(ws, 1, 8, chip_cols=(5, 6, 8), widths=[6, 22, 12, 44, 13, 11, 30, 12], landscape=True)

    # Evidence Checklist
    ws = wb.create_sheet("Evidence Checklist")
    _table_header(ws, ["Section", "Question", "Evidence Required", "Evidence Status", "Comment"])
    for sec, q in applicable:
        a = ans.get(q.question_id); req = bool(a and a["evidence_required"])
        ws.append([sec.section_name, q.question_text, "Yes" if req else "No", a["evidence_status"] if a else "Not Required", a["reviewer_comment"] if a else ""])
    _finish_table(ws, 1, 5, chip_cols=(4,), widths=[22, 46, 16, 16, 36], landscape=True)

    # Audit Summary
    ws = wb.create_sheet("Audit Summary")
    _table_header(ws, ["ID", "Timestamp", "User", "Action", "Entity", "Reason"])
    for a in conn.execute("SELECT audit_id,timestamp,user,action_type,entity_type,reason FROM audit_log WHERE review_case_id=? OR loan_id=? ORDER BY audit_id", (review_case_id, ctx["loan_id"])).fetchall():
        ws.append([a["audit_id"], str(a["timestamp"]).replace("T", "  "), a["user"], a["action_type"], a["entity_type"], a["reason"]])
    _finish_table(ws, 1, 6, chip_cols=(), widths=[6, 22, 14, 22, 16, 28], landscape=True)

    wb.save(path)
    conn.execute("INSERT INTO exports (engagement_id, review_case_id, export_type, file_path, generated_by, generated_at, export_status) VALUES (?, ?, ?, ?, ?, ?, ?)", (ctx['engagement_id'], review_case_id, "excel", str(path), generated_by, now(), "Generated")); conn.commit()
    append_audit_event(conn, generated_by, "export_generated", "export", "excel", after_value=str(path), reason=override_reason, engagement_id=ctx['engagement_id'], review_case_id=review_case_id, loan_id=ctx['loan_id'], template_id=template.template_id, template_version=template.version)
    return ExportResult(export_type="excel", file_path=str(path), export_status="Generated")

def generate_data_mart_csv(conn, review_case_id: int, template, output_path: str | Path = ROOT / "outputs" / "data_mart" / "review_answers_export.csv", generated_by="system"):
    ctx=_ctx(conn, review_case_id); rows=[]
    for a in conn.execute("SELECT * FROM review_answers WHERE review_case_id=?", (review_case_id,)).fetchall():
        rows.append({"client_name":ctx['client_name'],"review_period":ctx['review_period'],"template_id":template.template_id,"template_version":template.version,"review_case_id":review_case_id,"loan_id":ctx['loan_id'],"borrower_name":ctx['borrower_name'],"question_id":a['question_id'],"section":a['section_id'],"answer_value":a['answer_value'],"status":a['answer_status'],"severity":a['severity'],"exception_flag":bool(a['severity']),"reviewer_comment":a['reviewer_comment'],"evidence_status":a['evidence_status'],"answered_by":a['answered_by'],"answered_at":a['answered_at'],"exported_at":now()})
    Path(output_path).parent.mkdir(parents=True, exist_ok=True); pd.DataFrame(rows).to_csv(output_path, index=False)
    conn.execute("INSERT INTO exports (engagement_id, review_case_id, export_type, file_path, generated_by, generated_at, export_status) VALUES (?, ?, ?, ?, ?, ?, ?)", (ctx['engagement_id'], review_case_id, "data_mart", str(output_path), generated_by, now(), "Generated")); conn.commit()
    append_audit_event(conn, generated_by, "export_generated", "export", "data_mart", after_value=str(output_path), engagement_id=ctx['engagement_id'], review_case_id=review_case_id, loan_id=ctx['loan_id'], template_id=template.template_id, template_version=template.version)
    return ExportResult(export_type="data_mart", file_path=str(output_path), export_status="Generated")

def generate_exception_report_csv(conn, output_path: str | Path = ROOT / "outputs" / "exceptions" / "exceptions_report.csv"):
    df = pd.read_sql_query("""SELECT c.client_name,e.review_period,lr.loan_id,lr.borrower_name,x.section_id as section,x.question_id,x.issue_text,x.severity,x.status,x.reviewer_comment,x.evidence_status,x.created_at,x.updated_at FROM exceptions x JOIN review_cases rc ON x.review_case_id=rc.review_case_id JOIN loan_records lr ON x.loan_record_id=lr.loan_record_id JOIN engagements e ON rc.engagement_id=e.engagement_id JOIN clients c ON e.client_id=c.client_id ORDER BY x.exception_id""", conn)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True); df.to_csv(output_path, index=False)
    return ExportResult(export_type="exceptions", file_path=str(output_path), export_status="Generated")

def generate_audit_log_csv(conn, output_path: str | Path = ROOT / "outputs" / "audit" / "audit_log.csv"):
    return ExportResult(export_type="audit", file_path=export_audit_log(conn, output_path), export_status="Generated")
