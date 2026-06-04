"""Shared helpers for the analysis calculation engines (DTI, cash flow,
collateral, DSCR, leverage, guarantor, global, borrowing base, liquidity).

Previously each engine carried its own copy of these.
"""
from __future__ import annotations
from .db import now
from .audit import append_audit_event


def num(v) -> float:
    """Parse a currency-ish value to float; blanks / junk -> 0.0."""
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def carry_finding(conn, review_case_id, question_id, section_id, severity, issue_text,
                  user="system", loan_id=None):
    """Reflect a computed worksheet result as a case finding: upsert the
    exception when severity is Finding/Blocked, delete it (self-heal) when it
    returns to None, and write the matching audit event. Idempotent per
    (review_case_id, question_id)."""
    row = conn.execute("SELECT loan_record_id FROM review_cases WHERE review_case_id=?", (review_case_id,)).fetchone()
    lrid = row["loan_record_id"] if row else None
    existing = conn.execute("SELECT exception_id FROM exceptions WHERE review_case_id=? AND question_id=?",
                            (review_case_id, question_id)).fetchone()
    if severity in ("Finding", "Blocked"):
        conn.execute(
            """INSERT INTO exceptions (review_case_id, loan_record_id, question_id, section_id, issue_text, severity, status, reviewer_comment, evidence_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, question_id) DO UPDATE SET issue_text=excluded.issue_text, severity=excluded.severity, status=excluded.status, updated_at=excluded.updated_at""",
            (review_case_id, lrid, question_id, section_id, issue_text, severity, "Open", None, "Not Required", now(), now()))
        append_audit_event(conn, user, "exception_updated" if existing else "exception_created", "exception", question_id,
                           after_value=severity, review_case_id=review_case_id, loan_id=loan_id)
    elif existing:
        conn.execute("DELETE FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, question_id))
        append_audit_event(conn, user, "exception_resolved", "exception", question_id,
                           review_case_id=review_case_id, loan_id=loan_id)
    conn.commit()
