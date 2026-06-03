"""Guarantor / Global Financial engine.

Personal financial position (net worth, liquidity), personal cash flow and
personal debt service for a guarantor. Produces the personal-cash-flow and
personal-debt-service figures the Global DSCR module rolls up. Same
config -> engine -> table -> carry pattern as the other fixtures.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "guarantor_v1.yaml"


def load_guarantor_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    if not isinstance(cfg, dict) or "financial_position" not in cfg or "cash_flow" not in cfg:
        raise ValueError("Guarantor config must define 'financial_position' and 'cash_flow' blocks")
    for b in ("debt_service", "contingent"):
        cfg.setdefault(b, {"section_name": b.title(), "lines": []})
    cfg.setdefault("thresholds", {})
    return cfg


def position_lines(cfg):
    for ln in cfg["financial_position"]["lines"]:
        yield ln["key"], ln["label"], ln.get("type", "asset"), bool(ln.get("liquid", False))


def cash_flow_lines(cfg):
    for ln in cfg["cash_flow"]["lines"]:
        yield ln["key"], ln["label"], int(ln.get("sign", 1))


def debt_service_lines(cfg):
    for ln in cfg.get("debt_service", {}).get("lines", []):
        yield ln["key"], ln["label"]


def contingent_lines(cfg):
    for ln in cfg.get("contingent", {}).get("lines", []):
        yield ln["key"], ln["label"]


def _num(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def compute_guarantor(values: dict, cfg: dict) -> dict:
    th = cfg.get("thresholds", {})
    min_pdscr = float(th.get("min_personal_dscr", 1.00))

    assets = sum(_num(values.get(k)) for k, _, typ, _ in position_lines(cfg) if typ == "asset")
    liabilities = sum(_num(values.get(k)) for k, _, typ, _ in position_lines(cfg) if typ == "liability")
    liquid = sum(_num(values.get(k)) for k, _, _, liq in position_lines(cfg) if liq)
    net_worth = assets - liabilities

    personal_cf = sum(_num(values.get(k)) * sign for k, _, sign in cash_flow_lines(cfg))
    personal_ds = sum(_num(values.get(k)) for k, _ in debt_service_lines(cfg))
    contingent = sum(_num(values.get(k)) for k, _ in contingent_lines(cfg))
    personal_dscr = round(personal_cf / personal_ds, 2) if personal_ds else 0.0

    has_data = any(_num(v) for v in values.values())
    if not has_data:
        assessment, severity = "Inputs required", None
    elif personal_ds > 0 and personal_dscr < min_pdscr:
        assessment, severity = "Below personal coverage", "Finding"
    elif net_worth <= 0:
        assessment, severity = "Negative net worth", "Finding"
    else:
        assessment, severity = "Adequate guarantor support", None

    return {
        "total_assets": round(assets, 2), "total_liabilities": round(liabilities, 2),
        "liquid_assets": round(liquid, 2), "net_worth": round(net_worth, 2),
        "personal_cf_available": round(personal_cf, 2), "personal_debt_service": round(personal_ds, 2),
        "personal_dscr": personal_dscr, "contingent_liabilities": round(contingent, 2),
        "min_personal_dscr": min_pdscr, "assessment": assessment, "severity": severity,
    }


def save_guarantor_inputs(conn, review_case_id: int, values: dict, user: str = "system", loan_id=None, cfg: dict | None = None) -> int:
    n = 0
    for key, amount in values.items():
        conn.execute(
            """INSERT INTO guarantor_inputs (review_case_id, line_key, amount, note, updated_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, line_key) DO UPDATE SET amount=excluded.amount, updated_at=excluded.updated_at""",
            (review_case_id, key, _num(amount), None, now()))
        n += 1
    conn.commit()
    append_audit_event(conn, user, "guarantor_updated", "guarantor_worksheet", review_case_id,
                       after_value=f"{n} line items", review_case_id=review_case_id, loan_id=loan_id)
    cfg = cfg or load_guarantor_config()
    _carry_guarantor_finding(conn, review_case_id, compute_guarantor(load_guarantor_inputs(conn, review_case_id), cfg), user, loan_id)
    from .global_engine import carry_global
    carry_global(conn, review_case_id, user, loan_id)
    return n


def _carry_guarantor_finding(conn, review_case_id, result, user="system", loan_id=None):
    qid = "GUARANTOR"
    row = conn.execute("SELECT loan_record_id FROM review_cases WHERE review_case_id=?", (review_case_id,)).fetchone()
    lrid = row["loan_record_id"] if row else None
    existing = conn.execute("SELECT exception_id FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, qid)).fetchone()
    if result["severity"] in ("Finding", "Blocked"):
        issue = f"Guarantor: net worth ${result['net_worth']:,.0f}, personal DSCR {result['personal_dscr']:.2f}x — {result['assessment']}"
        conn.execute(
            """INSERT INTO exceptions (review_case_id, loan_record_id, question_id, section_id, issue_text, severity, status, reviewer_comment, evidence_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, question_id) DO UPDATE SET issue_text=excluded.issue_text, severity=excluded.severity, status=excluded.status, updated_at=excluded.updated_at""",
            (review_case_id, lrid, qid, "guarantor", issue, result["severity"], "Open", None, "Not Required", now(), now()))
        append_audit_event(conn, user, "exception_updated" if existing else "exception_created", "exception", qid,
                           after_value=result["severity"], review_case_id=review_case_id, loan_id=loan_id)
    elif existing:
        conn.execute("DELETE FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, qid))
        append_audit_event(conn, user, "exception_resolved", "exception", qid, review_case_id=review_case_id, loan_id=loan_id)
    conn.commit()


def load_guarantor_inputs(conn, review_case_id: int) -> dict:
    return {r["line_key"]: r["amount"] for r in conn.execute(
        "SELECT line_key, amount FROM guarantor_inputs WHERE review_case_id=?", (review_case_id,)).fetchall()}


def summarize_guarantor(conn, review_case_id: int, cfg: dict | None = None):
    values = load_guarantor_inputs(conn, review_case_id)
    if not any(_num(v) for v in values.values()):
        return None
    return compute_guarantor(values, cfg or load_guarantor_config())
