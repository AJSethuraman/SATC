"""Debt Service Coverage (DSCR) engine — commercial / CRE.

Builds cash flow available for debt service (CFADS) from signed line items,
compares it to annual debt service for the DSCR ratio, and computes debt yield
(NOI / loan amount). Same config -> engine -> table -> carry pattern as DTI.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "dscr_v1.yaml"


def load_dscr_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    if not isinstance(cfg, dict) or "cash_flow" not in cfg or "debt_service" not in cfg:
        raise ValueError("DSCR config must define 'cash_flow' and 'debt_service' blocks")
    cfg.setdefault("loan", {"section_name": "Loan", "lines": []})
    cfg.setdefault("thresholds", {})
    return cfg


def cash_flow_lines(cfg):
    for ln in cfg["cash_flow"]["lines"]:
        yield ln["key"], ln["label"], int(ln.get("sign", 1))


def debt_service_lines(cfg):
    for ln in cfg["debt_service"]["lines"]:
        yield ln["key"], ln["label"]


def loan_lines(cfg):
    for ln in cfg.get("loan", {}).get("lines", []):
        yield ln["key"], ln["label"]


def _num(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def compute_dscr(values: dict, cfg: dict) -> dict:
    th = cfg.get("thresholds", {})
    min_dscr = float(th.get("min_dscr", 1.20))
    min_debt_yield = float(th.get("min_debt_yield", 9.0))

    cfads = sum(_num(values.get(k)) * sign for k, _, sign in cash_flow_lines(cfg))
    noi = _num(values.get("net_operating_income"))
    debt_service = sum(_num(values.get(k)) for k, _ in debt_service_lines(cfg))
    loan_amount = sum(_num(values.get(k)) for k, _ in loan_lines(cfg))

    dscr = round(cfads / debt_service, 2) if debt_service else 0.0
    debt_yield = round(noi / loan_amount * 100, 2) if loan_amount else 0.0
    excess = round(cfads - debt_service, 2)

    if debt_service <= 0:
        assessment, severity = "Debt service required", None
    elif dscr < min_dscr:
        assessment, severity = "Below DSCR guideline", "Finding"
    elif loan_amount and debt_yield < min_debt_yield:
        assessment, severity = "Below debt yield guideline", "Finding"
    else:
        assessment, severity = "Meets coverage guidelines", None

    return {
        "cfads": round(cfads, 2), "net_operating_income": round(noi, 2),
        "total_debt_service": round(debt_service, 2), "loan_amount": round(loan_amount, 2),
        "dscr": dscr, "debt_yield": debt_yield, "excess_cash_flow": excess,
        "min_dscr": min_dscr, "min_debt_yield": min_debt_yield,
        "assessment": assessment, "severity": severity,
    }


def save_dscr_inputs(conn, review_case_id: int, values: dict, user: str = "system", loan_id=None, cfg: dict | None = None) -> int:
    n = 0
    for key, amount in values.items():
        conn.execute(
            """INSERT INTO dscr_inputs (review_case_id, line_key, amount, note, updated_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, line_key) DO UPDATE SET amount=excluded.amount, updated_at=excluded.updated_at""",
            (review_case_id, key, _num(amount), None, now()))
        n += 1
    conn.commit()
    append_audit_event(conn, user, "dscr_updated", "dscr_worksheet", review_case_id,
                       after_value=f"{n} line items", review_case_id=review_case_id, loan_id=loan_id)
    cfg = cfg or load_dscr_config()
    _carry_dscr_finding(conn, review_case_id, compute_dscr(load_dscr_inputs(conn, review_case_id), cfg), user, loan_id)
    return n


def _carry_dscr_finding(conn, review_case_id, result, user="system", loan_id=None):
    qid = "DSCR"
    row = conn.execute("SELECT loan_record_id FROM review_cases WHERE review_case_id=?", (review_case_id,)).fetchone()
    lrid = row["loan_record_id"] if row else None
    existing = conn.execute("SELECT exception_id FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, qid)).fetchone()
    if result["severity"] in ("Finding", "Blocked"):
        issue = f"Debt service coverage: DSCR {result['dscr']:.2f}x — {result['assessment']}"
        conn.execute(
            """INSERT INTO exceptions (review_case_id, loan_record_id, question_id, section_id, issue_text, severity, status, reviewer_comment, evidence_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, question_id) DO UPDATE SET issue_text=excluded.issue_text, severity=excluded.severity, status=excluded.status, updated_at=excluded.updated_at""",
            (review_case_id, lrid, qid, "debt_service", issue, result["severity"], "Open", None, "Not Required", now(), now()))
        append_audit_event(conn, user, "exception_updated" if existing else "exception_created", "exception", qid,
                           after_value=result["severity"], review_case_id=review_case_id, loan_id=loan_id)
    elif existing:
        conn.execute("DELETE FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, qid))
        append_audit_event(conn, user, "exception_resolved", "exception", qid, review_case_id=review_case_id, loan_id=loan_id)
    conn.commit()


def load_dscr_inputs(conn, review_case_id: int) -> dict:
    return {r["line_key"]: r["amount"] for r in conn.execute(
        "SELECT line_key, amount FROM dscr_inputs WHERE review_case_id=?", (review_case_id,)).fetchall()}


def summarize_dscr(conn, review_case_id: int, cfg: dict | None = None):
    values = load_dscr_inputs(conn, review_case_id)
    if not any(_num(v) for v in values.values()):
        return None
    return compute_dscr(values, cfg or load_dscr_config())
