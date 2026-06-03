"""Consumer ability-to-repay (DTI) worksheet engine.

Pure-ish helpers that load the YAML worksheet config, compute the standard
ability-to-repay metrics (front-end / back-end DTI, total obligations,
residual income) and persist the fillable line-item inputs per review case.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "dti_worksheet_v1.yaml"
BLOCKS = ("income", "housing", "debts")


def load_dti_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    if not isinstance(cfg, dict) or not all(b in cfg for b in BLOCKS):
        raise ValueError("DTI config must define 'income', 'housing' and 'debts' blocks")
    cfg.setdefault("thresholds", {})
    return cfg


def block_lines(cfg: dict, block: str) -> list[tuple[str, str]]:
    """Return [(key, label), ...] for a block, in display order."""
    return [(ln["key"], ln["label"]) for ln in cfg[block]["lines"]]


def all_line_keys(cfg: dict) -> list[str]:
    keys = [k for b in BLOCKS for k, _ in block_lines(cfg, b)]
    if cfg.get("deductions"):
        keys += [k for k, _ in block_lines(cfg, "deductions")]
    return keys


def _num(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def compute_dti(values: dict, cfg: dict, income_override=None) -> dict:
    """Compute ability-to-repay metrics from a {line_key: amount} mapping.
    income_override (e.g. qualifying income from the Cash Flow worksheet), when
    provided, is used as monthly gross income instead of the entered lines."""
    th = cfg.get("thresholds", {})
    front_target = float(th.get("front_end_target", 28.0))
    back_target = float(th.get("back_end_target", 43.0))
    back_max = float(th.get("back_end_max", 50.0))
    residual_min = float(th.get("residual_income_min", 0.0))

    entered_income = sum(_num(values.get(k)) for k, _ in block_lines(cfg, "income"))
    if income_override is not None and float(income_override) > 0:
        income = round(float(income_override), 2); income_source = "Cash Flow worksheet"
    else:
        income = entered_income; income_source = "Worksheet entry"
    housing = sum(_num(values.get(k)) for k, _ in block_lines(cfg, "housing"))
    other_debt = sum(_num(values.get(k)) for k, _ in block_lines(cfg, "debts"))
    obligations = housing + other_debt
    residual = income - obligations

    # Optional payroll withholding -> net income / net residual (W-2 borrowers).
    ded_lines = block_lines(cfg, "deductions") if cfg.get("deductions") else []
    withholding = sum(_num(values.get(k)) for k, _ in ded_lines)
    net_income = income - withholding
    net_residual = net_income - obligations
    # When withholding is provided, the residual floor is judged on net residual.
    residual_for_check = net_residual if withholding > 0 else residual

    front = round(housing / income * 100, 2) if income else 0.0
    back = round(obligations / income * 100, 2) if income else 0.0

    if income <= 0:
        assessment, severity = "Income required", None
    elif back > back_max:
        assessment, severity = "Fails ATR — exceeds maximum DTI", "Blocked"
    elif back > back_target or front > front_target or (residual_min > 0 and residual_for_check < residual_min):
        assessment, severity = "Exceeds guidelines — documented exception required", "Finding"
    else:
        assessment, severity = "Within ability-to-repay guidelines", None

    return {
        "total_income": round(income, 2),
        "income_source": income_source,
        "total_housing": round(housing, 2),
        "total_other_debt": round(other_debt, 2),
        "total_obligations": round(obligations, 2),
        "front_end_dti": front,
        "back_end_dti": back,
        "residual_income": round(residual, 2),
        "total_withholding": round(withholding, 2),
        "net_income": round(net_income, 2),
        "net_residual_income": round(net_residual, 2),
        "front_end_target": front_target,
        "back_end_target": back_target,
        "back_end_max": back_max,
        "residual_income_min": residual_min,
        "assessment": assessment,
        "severity": severity,
    }


def save_dti_inputs(conn, review_case_id: int, values: dict, user: str = "system",
                    notes: dict | None = None, loan_id=None, cfg: dict | None = None) -> int:
    """Upsert worksheet line items for a review case, carry the ATR result into
    the case findings, and log audit events."""
    notes = notes or {}
    n = 0
    for key, amount in values.items():
        conn.execute(
            """INSERT INTO dti_inputs (review_case_id, line_key, amount, note, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, line_key)
               DO UPDATE SET amount=excluded.amount, note=excluded.note, updated_at=excluded.updated_at""",
            (review_case_id, key, _num(amount), notes.get(key), now()),
        )
        n += 1
    conn.commit()
    append_audit_event(conn, user, "dti_updated", "dti_worksheet", review_case_id,
                       after_value=f"{n} line items", review_case_id=review_case_id, loan_id=loan_id)
    cfg = cfg or load_dti_config()
    result = summarize_dti(conn, review_case_id, cfg)
    if result:
        _carry_dti_finding(conn, review_case_id, result, user, loan_id)
    return n


def _carry_dti_finding(conn, review_case_id, result, user="system", loan_id=None):
    """Reflect an over-guideline ATR result as a case finding so it carries
    into the Exceptions tab, exception report and cover findings count."""
    qid = "DTI_ATR"
    row = conn.execute("SELECT loan_record_id FROM review_cases WHERE review_case_id=?", (review_case_id,)).fetchone()
    lrid = row["loan_record_id"] if row else None
    existing = conn.execute("SELECT exception_id FROM exceptions WHERE review_case_id=? AND question_id=?",
                            (review_case_id, qid)).fetchone()
    if result["severity"] in ("Finding", "Blocked"):
        issue = f"Ability-to-repay: back-end DTI {result['back_end_dti']:.1f}% (front-end {result['front_end_dti']:.1f}%) — {result['assessment']}"
        conn.execute(
            """INSERT INTO exceptions (review_case_id, loan_record_id, question_id, section_id, issue_text, severity, status, reviewer_comment, evidence_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, question_id) DO UPDATE SET issue_text=excluded.issue_text, severity=excluded.severity, status=excluded.status, updated_at=excluded.updated_at""",
            (review_case_id, lrid, qid, "ability_to_repay", issue, result["severity"], "Open", None, "Not Required", now(), now()),
        )
        append_audit_event(conn, user, "exception_updated" if existing else "exception_created", "exception", qid,
                           after_value=result["severity"], review_case_id=review_case_id, loan_id=loan_id)
    elif existing:
        conn.execute("DELETE FROM exceptions WHERE review_case_id=? AND question_id=?", (review_case_id, qid))
        append_audit_event(conn, user, "exception_resolved", "exception", qid,
                           review_case_id=review_case_id, loan_id=loan_id)
    conn.commit()


def load_dti_inputs(conn, review_case_id: int) -> dict:
    rows = conn.execute(
        "SELECT line_key, amount FROM dti_inputs WHERE review_case_id=?", (review_case_id,)
    ).fetchall()
    return {r["line_key"]: r["amount"] for r in rows}


def summarize_dti(conn, review_case_id: int, cfg: dict | None = None, auto_income: bool = True):
    """Return the computed ATR result, or None if empty. Auto-feed: when the
    Cash Flow worksheet is filled, its qualifying monthly income is used as the
    DTI income basis."""
    values = load_dti_inputs(conn, review_case_id)
    override = None
    if auto_income:
        from .cash_flow_engine import summarize_cash_flow
        cf = summarize_cash_flow(conn, review_case_id)
        if cf and cf.get("qualifying_monthly"):
            override = cf["qualifying_monthly"]
    if override is None and not any(_num(v) for v in values.values()):
        return None
    return compute_dti(values, cfg or load_dti_config(), income_override=override)
