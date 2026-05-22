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
NAVY="1F4E78"; GOLD="D9A441"; GRAY="D9E2F3"; GREEN="C6EFCE"; AMBER="FFEB9C"; RED="FFC7CE"

def _ctx(conn, review_case_id):
    row = conn.execute("""SELECT rc.*, e.review_period,e.template_id,e.reviewer_name,e.qc_reviewer_name,c.client_name,lr.* FROM review_cases rc JOIN engagements e ON rc.engagement_id=e.engagement_id JOIN clients c ON e.client_id=c.client_id JOIN loan_records lr ON rc.loan_record_id=lr.loan_record_id WHERE rc.review_case_id=?""", (review_case_id,)).fetchone()
    return {k: row[k] for k in row.keys()}

def assert_export_allowed(conn, review_case_id, loan_record, template, override_reason=None):
    status = calculate_completion_status(conn, review_case_id, loan_record, template)
    if status["export_ready"] or override_reason: return status
    raise ValueError("Export blocked: " + "; ".join(status["blockers"] or ["Review status must be Ready for QC or QC Approved"]))

def _style_header(ws, row=1):
    for cell in ws[row]:
        cell.fill = PatternFill("solid", fgColor=NAVY); cell.font = Font(color="FFFFFF", bold=True); cell.alignment = Alignment(wrap_text=True)
        cell.border = Border(bottom=Side(style="thin", color="808080"))

def _autosize(ws):
    for col in ws.columns:
        width = min(max(len(str(c.value or "")) for c in col) + 2, 48)
        ws.column_dimensions[get_column_letter(col[0].column)].width = width

def generate_excel_linesheet(conn, review_case_id: int, template, output_dir: str | Path = ROOT / "outputs" / "excel", generated_by="system", override_reason=None):
    ctx = _ctx(conn, review_case_id); loan = ctx.copy()
    assert_export_allowed(conn, review_case_id, loan, template, override_reason)
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"linesheet_{ctx['loan_id']}_{now().replace(':','')}.xlsx"
    wb = Workbook(); ws = wb.active; ws.title = "Cover"
    cover = [("Client", ctx['client_name']),("Review period", ctx['review_period']),("Template", f"{template.template_name} / {template.version}"),("Borrower", ctx['borrower_name']),("Loan ID", ctx['loan_id']),("Reviewer", ctx['reviewer_name']),("QC reviewer", ctx['qc_reviewer_name']),("Generated timestamp", now()),("Overall status", ctx['status'])]
    ws.append(["Linesheet Builder", "Audit-Ready Commercial Loan Linesheet"]); ws["A1"].fill=PatternFill("solid", fgColor=NAVY); ws["A1"].font=Font(color="FFFFFF", bold=True, size=16); ws["B1"].fill=PatternFill("solid", fgColor=GOLD)
    for r in cover: ws.append(r)
    _autosize(ws)
    ws = wb.create_sheet("Loan Summary"); ws.append(["Field","Value"]); _style_header(ws)
    fields = ["loan_id","borrower_name","product_type","commitment_amount","outstanding_balance","origination_date","maturity_date","risk_rating","officer","collateral_type","guarantor_name","dscr","ltv","validation_status"]
    for f in fields: ws.append([f.replace('_',' ').title(), ctx.get(f)])
    for cell in ws[4:5][0]+ws[5:6][0]: cell.fill = PatternFill("solid", fgColor=GOLD)
    _autosize(ws)
    ws = wb.create_sheet("Linesheet Questions"); ws.append(["Section","Question","Answer","Source Value","Status","Severity","Reviewer Comment","Evidence Status"]); _style_header(ws)
    ans = {r['question_id']: r for r in conn.execute("SELECT * FROM review_answers WHERE review_case_id=?", (review_case_id,)).fetchall()}
    for sec,q in get_applicable_questions(loan, template):
        a = ans.get(q.question_id)
        ws.append([sec.section_name, q.question_text, a['answer_value'] if a else '', a['source_value'] if a else ctx.get(q.source_field) if q.source_field else '', a['answer_status'] if a else 'Incomplete', a['severity'] if a else '', a['reviewer_comment'] if a else '', a['evidence_status'] if a else 'Not Required'])
    _autosize(ws)
    ws = wb.create_sheet("Exceptions & Findings"); ws.append(["Finding ID","Section","Question ID","Issue","Severity","Status","Reviewer Comment","Evidence Status"]); _style_header(ws)
    for e in conn.execute("SELECT * FROM exceptions WHERE review_case_id=?", (review_case_id,)).fetchall(): ws.append([e['exception_id'], e['section_id'], e['question_id'], e['issue_text'], e['severity'], e['status'], e['reviewer_comment'], e['evidence_status']])
    _autosize(ws)
    ws = wb.create_sheet("Evidence Checklist"); ws.append(["Section","Question","Evidence Required","Evidence Status","Comment"]); _style_header(ws)
    for sec,q in get_applicable_questions(loan, template):
        a = ans.get(q.question_id); req = bool(a and a['evidence_required'])
        ws.append([sec.section_name, q.question_text, "Yes" if req else "No", a['evidence_status'] if a else 'Not Required', a['reviewer_comment'] if a else ''])
    _autosize(ws)
    ws = wb.create_sheet("Audit Summary"); ws.append(["Audit ID","Timestamp","User","Action","Entity","Reason"]); _style_header(ws)
    for a in conn.execute("SELECT audit_id,timestamp,user,action_type,entity_type,reason FROM audit_log WHERE review_case_id=? OR loan_id=? ORDER BY audit_id", (review_case_id, ctx['loan_id'])).fetchall(): ws.append(list(a))
    _autosize(ws)
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
