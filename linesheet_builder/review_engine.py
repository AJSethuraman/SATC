from __future__ import annotations
import json
from .db import now
from .audit import append_audit_event
from .template_engine import get_applicable_questions
from .rules_engine import determine_question_status

def create_review_cases(conn, engagement_id: int, assigned_reviewer="", qc_reviewer=""):
    rows = conn.execute("SELECT loan_record_id FROM loan_records WHERE engagement_id=?", (engagement_id,)).fetchall()
    ids=[]
    for r in rows:
        existing = conn.execute("SELECT review_case_id FROM review_cases WHERE loan_record_id=?", (r[0],)).fetchone()
        if existing: ids.append(existing[0]); continue
        cur = conn.execute("INSERT INTO review_cases (engagement_id, loan_record_id, status, assigned_reviewer, qc_reviewer, started_at) VALUES (?, ?, ?, ?, ?, ?)", (engagement_id, r[0], "Not Started", assigned_reviewer, qc_reviewer, now()))
        ids.append(int(cur.lastrowid))
    conn.commit(); return ids

def get_review_case(conn, review_case_id: int):
    return conn.execute("SELECT rc.*, lr.* FROM review_cases rc JOIN loan_records lr ON rc.loan_record_id=lr.loan_record_id WHERE rc.review_case_id=?", (review_case_id,)).fetchone()

def _loan_dict(row): return {k: row[k] for k in row.keys() if k in {"loan_id","borrower_name","product_type","commitment_amount","outstanding_balance","origination_date","maturity_date","risk_rating","officer","collateral_type","guarantor_name","approval_date","approval_authority","financial_statement_date","dscr","ltv","covenant_status","past_due_days","nonaccrual_flag","policy_exception_flag","review_sample_id","validation_status"}}

def save_answer(conn, review_case_id: int, loan_record: dict, section, question, answer_value, reviewer_comment="", evidence_status="Not Required", answered_by="system", template_id=None, template_version=None):
    source = loan_record
    source_value = source.get(question.source_field) if question.source_field else None
    status = determine_question_status(question, answer=answer_value, source=source)
    evidence_required = bool(status["evidence_required"])
    if evidence_required and evidence_status == "Not Required": evidence_status = "Needed"
    answer_status = status["status"]
    conn.execute("""INSERT INTO review_answers (review_case_id, question_id, section_id, answer_value, source_field, source_value, answer_status, severity, reviewer_comment, evidence_required, evidence_status, answered_by, answered_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(review_case_id, question_id) DO UPDATE SET answer_value=excluded.answer_value, source_value=excluded.source_value, answer_status=excluded.answer_status, severity=excluded.severity, reviewer_comment=excluded.reviewer_comment, evidence_required=excluded.evidence_required, evidence_status=excluded.evidence_status, answered_by=excluded.answered_by, updated_at=excluded.updated_at""", (review_case_id, question.question_id, section.section_id, str(answer_value) if answer_value is not None else None, question.source_field, str(source_value) if source_value is not None else None, answer_status, status["severity"], reviewer_comment, int(evidence_required), evidence_status, answered_by, now(), now()))
    append_audit_event(conn, answered_by, "answer_changed", "review_answer", question.question_id, after_value=str(answer_value), review_case_id=review_case_id, loan_id=loan_record.get("loan_id"), template_id=template_id, template_version=template_version)
    if status["exception_flag"]:
        existing = conn.execute("SELECT exception_id FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, question.question_id)).fetchone()
        action = "exception_updated" if existing else "exception_created"
        conn.execute("""INSERT INTO exceptions (review_case_id, loan_record_id, question_id, section_id, issue_text, severity, status, reviewer_comment, evidence_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(review_case_id, question_id) DO UPDATE SET issue_text=excluded.issue_text, severity=excluded.severity, status=excluded.status, reviewer_comment=excluded.reviewer_comment, evidence_status=excluded.evidence_status, updated_at=excluded.updated_at""", (review_case_id, loan_record.get("loan_record_id"), question.question_id, section.section_id, question.question_text, status["severity"], "Open", reviewer_comment, evidence_status, now(), now()))
        append_audit_event(conn, answered_by, action, "exception", question.question_id, after_value=status["severity"], review_case_id=review_case_id, loan_id=loan_record.get("loan_id"), template_id=template_id, template_version=template_version)
    conn.execute("UPDATE review_cases SET status=? WHERE review_case_id=? AND status='Not Started'", ("In Review", review_case_id))
    conn.commit()
    return status

def calculate_completion_status(conn, review_case_id: int, loan_record: dict, template):
    answers = {r["question_id"]: r for r in conn.execute("SELECT * FROM review_answers WHERE review_case_id=?", (review_case_id,)).fetchall()}
    applicable = get_applicable_questions(loan_record, template)
    blockers=[]; required=0; complete=0
    for sec,q in applicable:
        a = answers.get(q.question_id)
        if q.required:
            required += 1
            if not a or not str(a["answer_value"] or "").strip(): blockers.append(f"Required unanswered: {q.question_id}")
            else: complete += 1
        if a and a["severity"] in ("Finding","Blocked") and not str(a["reviewer_comment"] or "").strip(): blockers.append(f"Reviewer comment required: {q.question_id}")
        if a and a["evidence_required"] and a["evidence_status"] not in ("Attached","Waived"): blockers.append(f"Evidence unresolved: {q.question_id}")
    val_blocked = conn.execute("SELECT COUNT(*) FROM validation_issues WHERE loan_record_id=? AND severity='Blocked'", (loan_record.get("loan_record_id"),)).fetchone()[0]
    if val_blocked: blockers.append("Blocked validation issues exist")
    pct = int((complete / required) * 100) if required else 100
    export_ready = not blockers and conn.execute("SELECT status FROM review_cases WHERE review_case_id=?", (review_case_id,)).fetchone()[0] in ("Ready for QC","QC Approved")
    return {"completion_pct": pct, "blockers": blockers, "export_ready": export_ready, "required_count": required, "answered_required": complete}

def set_review_status(conn, review_case_id: int, status: str):
    field = {"Ready for QC":"submitted_at","QC Approved":"approved_at","Finalized":"finalized_at"}.get(status)
    if field: conn.execute(f"UPDATE review_cases SET status=?, {field}=? WHERE review_case_id=?", (status, now(), review_case_id))
    else: conn.execute("UPDATE review_cases SET status=? WHERE review_case_id=?", (status, review_case_id))
    conn.commit()
