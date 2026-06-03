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
    return [k for b in BLOCKS for k, _ in block_lines(cfg, b)]


def _num(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("$", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def compute_dti(values: dict, cfg: dict) -> dict:
    """Compute ability-to-repay metrics from a {line_key: amount} mapping."""
    th = cfg.get("thresholds", {})
    front_target = float(th.get("front_end_target", 28.0))
    back_target = float(th.get("back_end_target", 43.0))
    back_max = float(th.get("back_end_max", 50.0))
    residual_min = float(th.get("residual_income_min", 0.0))

    income = sum(_num(values.get(k)) for k, _ in block_lines(cfg, "income"))
    housing = sum(_num(values.get(k)) for k, _ in block_lines(cfg, "housing"))
    other_debt = sum(_num(values.get(k)) for k, _ in block_lines(cfg, "debts"))
    obligations = housing + other_debt
    residual = income - obligations

    front = round(housing / income * 100, 2) if income else 0.0
    back = round(obligations / income * 100, 2) if income else 0.0

    if income <= 0:
        assessment, severity = "Income required", None
    elif back > back_max:
        assessment, severity = "Fails ATR — exceeds maximum DTI", "Blocked"
    elif back > back_target or front > front_target or (residual_min > 0 and residual < residual_min):
        assessment, severity = "Exceeds guidelines — documented exception required", "Finding"
    else:
        assessment, severity = "Within ability-to-repay guidelines", None

    return {
        "total_income": round(income, 2),
        "total_housing": round(housing, 2),
        "total_other_debt": round(other_debt, 2),
        "total_obligations": round(obligations, 2),
        "front_end_dti": front,
        "back_end_dti": back,
        "residual_income": round(residual, 2),
        "front_end_target": front_target,
        "back_end_target": back_target,
        "back_end_max": back_max,
        "residual_income_min": residual_min,
        "assessment": assessment,
        "severity": severity,
    }


def save_dti_inputs(conn, review_case_id: int, values: dict, user: str = "system",
                    notes: dict | None = None, loan_id=None) -> int:
    """Upsert worksheet line items for a review case and log one audit event."""
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
    return n


def load_dti_inputs(conn, review_case_id: int) -> dict:
    rows = conn.execute(
        "SELECT line_key, amount FROM dti_inputs WHERE review_case_id=?", (review_case_id,)
    ).fetchall()
    return {r["line_key"]: r["amount"] for r in rows}
