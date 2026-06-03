"""Global Cash Flow / Global DSCR engine — commercial capstone.

Rolls up the business cash flow (DSCR module) and the guarantor personal cash
flow (Guarantor module) into a single global coverage view:

    global CFADS        = business CFADS  + guarantor personal cash flow
    global debt service = business debt service + personal debt service
    global DSCR         = global CFADS / global debt service

Has no inputs of its own; it derives from the DSCR and Guarantor worksheets.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event
from .dscr_engine import summarize_dscr
from .guarantor_engine import summarize_guarantor

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "global_v1.yaml"


def load_global_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text()) or {}
    cfg.setdefault("thresholds", {})
    return cfg


def compute_global(dscr: dict | None, guarantor: dict | None, cfg: dict) -> dict:
    min_global = float(cfg.get("thresholds", {}).get("min_global_dscr", 1.15))
    business_cfads = (dscr or {}).get("cfads", 0.0) or 0.0
    business_ds = (dscr or {}).get("total_debt_service", 0.0) or 0.0
    personal_cf = (guarantor or {}).get("personal_cf_available", 0.0) or 0.0
    personal_ds = (guarantor or {}).get("personal_debt_service", 0.0) or 0.0

    global_cfads = business_cfads + personal_cf
    global_ds = business_ds + personal_ds
    global_dscr = round(global_cfads / global_ds, 2) if global_ds else 0.0

    if global_ds <= 0:
        assessment, severity = "Debt service required", None
    elif global_dscr < min_global:
        assessment, severity = "Below global DSCR guideline", "Finding"
    else:
        assessment, severity = "Meets global coverage", None

    return {
        "business_cfads": round(business_cfads, 2), "personal_cf_available": round(personal_cf, 2),
        "global_cfads": round(global_cfads, 2), "business_debt_service": round(business_ds, 2),
        "personal_debt_service": round(personal_ds, 2), "global_debt_service": round(global_ds, 2),
        "global_dscr": global_dscr, "min_global_dscr": min_global,
        "assessment": assessment, "severity": severity,
    }


def summarize_global(conn, review_case_id: int, cfg: dict | None = None):
    dscr = summarize_dscr(conn, review_case_id)
    guarantor = summarize_guarantor(conn, review_case_id)
    if not dscr and not guarantor:
        return None
    return compute_global(dscr, guarantor, cfg or load_global_config())


def carry_global(conn, review_case_id: int, user: str = "system", loan_id=None):
    """Recompute the global DSCR and reflect a below-guideline result as a
    finding. Called whenever the DSCR or Guarantor worksheets change."""
    result = summarize_global(conn, review_case_id)
    qid = "GLOBAL_DSCR"
    existing = conn.execute("SELECT exception_id FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, qid)).fetchone()
    if result and result["severity"] in ("Finding", "Blocked"):
        row = conn.execute("SELECT loan_record_id FROM review_cases WHERE review_case_id=?", (review_case_id,)).fetchone()
        lrid = row["loan_record_id"] if row else None
        issue = f"Global cash flow: global DSCR {result['global_dscr']:.2f}x — {result['assessment']}"
        conn.execute(
            """INSERT INTO exceptions (review_case_id, loan_record_id, question_id, section_id, issue_text, severity, status, reviewer_comment, evidence_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, question_id) DO UPDATE SET issue_text=excluded.issue_text, severity=excluded.severity, status=excluded.status, updated_at=excluded.updated_at""",
            (review_case_id, lrid, qid, "global_cash_flow", issue, result["severity"], "Open", None, "Not Required", now(), now()))
        append_audit_event(conn, user, "exception_updated" if existing else "exception_created", "exception", qid,
                           after_value=result["severity"], review_case_id=review_case_id, loan_id=loan_id)
    elif existing:
        conn.execute("DELETE FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, qid))
        append_audit_event(conn, user, "exception_resolved", "exception", qid, review_case_id=review_case_id, loan_id=loan_id)
    conn.commit()
    return result
