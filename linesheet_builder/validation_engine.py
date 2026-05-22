from __future__ import annotations
from datetime import datetime
import pandas as pd
from .models import ValidationIssue
from .db import now
from .audit import append_audit_event

BLOCK_FIELDS = {"loan_id":"Missing loan_id","borrower_name":"Missing borrower_name","product_type":"Missing product_type","outstanding_balance":"Missing outstanding_balance"}

def blank(v): return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""
def to_float(v):
    if blank(v): return None
    try: return float(str(v).replace(',', '').replace('$',''))
    except Exception: return None
def to_date(v):
    if blank(v): return None
    try: return pd.to_datetime(v).date()
    except Exception: return "INVALID"
def truthy(v): return str(v).strip().lower() in {"true","yes","y","1"}

def validate_loan_records(records, template=None):
    dicts = [r.model_dump() if hasattr(r,"model_dump") else dict(r) for r in records]
    counts = {}
    for r in dicts:
        loan_id = None if blank(r.get("loan_id")) else str(r.get("loan_id"))
        if loan_id: counts[loan_id] = counts.get(loan_id, 0) + 1
    results = []
    for r in dicts:
        issues = []
        def add(sev, code, msg, field): issues.append(ValidationIssue(loan_record_id=r.get("loan_record_id"), severity=sev, status="Open", issue_code=code, issue_message=msg, field_name=field))
        for f,msg in BLOCK_FIELDS.items():
            if blank(r.get(f)): add("Blocked", f"MISSING_{f.upper()}", msg, f)
        lid = None if blank(r.get("loan_id")) else str(r.get("loan_id"))
        if lid and counts.get(lid,0) > 1: add("Blocked", "DUPLICATE_LOAN_ID", "Duplicate loan_id within import batch", "loan_id")
        if not blank(r.get("outstanding_balance")) and to_float(r.get("outstanding_balance")) is None: add("Blocked", "INVALID_OUTSTANDING_BALANCE", "Invalid outstanding_balance", "outstanding_balance")
        od, md = to_date(r.get("origination_date")), to_date(r.get("maturity_date"))
        if od == "INVALID": add("Blocked", "INVALID_ORIGINATION_DATE", "Invalid date format on origination_date", "origination_date")
        if md == "INVALID": add("Blocked", "INVALID_MATURITY_DATE", "Invalid date format on maturity_date", "maturity_date")
        if od not in (None,"INVALID") and md not in (None,"INVALID") and md < od: add("Blocked", "MATURITY_BEFORE_ORIGINATION", "maturity_date before origination_date", "maturity_date")
        product = str(r.get("product_type") or "").lower()
        if ("secured" in product or "commercial" in product) and blank(r.get("collateral_type")): add("Warning", "MISSING_COLLATERAL", "Missing collateral_type for secured/commercial loan", "collateral_type")
        if blank(r.get("guarantor_name")): add("Warning", "MISSING_GUARANTOR", "Missing guarantor_name", "guarantor_name")
        dscr = to_float(r.get("dscr")); ltv = to_float(r.get("ltv"))
        if dscr is None: add("Warning", "MISSING_DSCR", "Missing dscr", "dscr")
        elif dscr < 1.20: add("Warning", "DSCR_BELOW_120", "DSCR below 1.20", "dscr")
        if ltv is not None and ltv > 80: add("Warning", "LTV_ABOVE_80", "LTV above 80", "ltv")
        rr = to_float(r.get("risk_rating"))
        if rr is None or rr < 1 or rr > 10: add("Warning", "RISK_RATING_SCALE", "Risk rating outside expected scale", "risk_rating")
        pdays = to_float(r.get("past_due_days")) or 0
        if pdays > 0: add("Warning", "PAST_DUE", "Past due days greater than 0", "past_due_days")
        if truthy(r.get("policy_exception_flag")): add("Warning", "POLICY_EXCEPTION", "policy_exception_flag = true", "policy_exception_flag")
        if truthy(r.get("nonaccrual_flag")): add("Warning", "NONACCRUAL", "nonaccrual_flag = true", "nonaccrual_flag")
        status = "Blocked" if any(i.severity == "Blocked" for i in issues) else ("Warning" if issues else "Ready")
        results.append({"loan_record": r, "status": status, "issues": issues})
    return results

def persist_validation_issues(conn, validation_results, engagement_id=None, user="system"):
    for res in validation_results:
        lrid = res["loan_record"].get("loan_record_id")
        conn.execute("DELETE FROM validation_issues WHERE loan_record_id=?", (lrid,))
        conn.execute("UPDATE loan_records SET validation_status=? WHERE loan_record_id=?", (res["status"], lrid))
        for i in res["issues"]:
            conn.execute("INSERT INTO validation_issues (loan_record_id, severity, status, issue_code, issue_message, field_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (lrid, i.severity, i.status, i.issue_code, i.issue_message, i.field_name, now()))
    conn.commit(); append_audit_event(conn, user, "validation_run", "validation_issues", after_value=f"{len(validation_results)} loans", engagement_id=engagement_id)

def validation_summary_table(validation_results):
    return pd.DataFrame([{"Loan ID": r["loan_record"].get("loan_id"), "Borrower": r["loan_record"].get("borrower_name"), "Product": r["loan_record"].get("product_type"), "Balance": r["loan_record"].get("outstanding_balance"), "Status": r["status"], "Issue count": len(r["issues"]), "Issues summary": "; ".join(i.issue_message for i in r["issues"][:4]), "Next action": "Resolve blockers" if r["status"]=="Blocked" else ("Acknowledge warnings/review" if r["status"]=="Warning" else "Begin review")} for r in validation_results])
