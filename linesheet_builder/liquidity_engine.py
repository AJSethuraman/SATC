"""Liquidity & Reserves engine.

Liquid assets vs. monthly obligations -> months of reserves, scored against a
guideline. Same config -> engine -> table -> carry pattern as the other
fixtures (single-amount inputs, like Leverage).
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "liquidity_v1.yaml"


def load_liquidity_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    if not isinstance(cfg, dict) or "inputs" not in cfg:
        raise ValueError("Liquidity config must define an 'inputs' block")
    cfg.setdefault("thresholds", {})
    return cfg


def input_lines(cfg):
    for ln in cfg["inputs"]["lines"]:
        yield ln["key"], ln["label"]


from .calc_common import num as _num, carry_finding


def compute_liquidity(values: dict, cfg: dict) -> dict:
    min_months = float(cfg.get("thresholds", {}).get("min_months_reserves", 6.0))
    liquid = (_num(values.get("cash_equivalents")) + _num(values.get("marketable_securities"))
              + _num(values.get("other_liquid_assets")))
    monthly_obligations = _num(values.get("monthly_obligations"))
    months_reserves = round(liquid / monthly_obligations, 2) if monthly_obligations else 0.0

    if not any(_num(v) for v in values.values()):
        assessment, severity = "Inputs required", None
    elif monthly_obligations > 0 and months_reserves < min_months:
        assessment, severity = "Below reserve guideline", "Finding"
    else:
        assessment, severity = "Adequate reserves", None

    return {
        "liquid_assets": round(liquid, 2), "monthly_obligations": round(monthly_obligations, 2),
        "months_reserves": months_reserves, "min_months_reserves": min_months,
        "assessment": assessment, "severity": severity,
    }


def save_liquidity_inputs(conn, review_case_id: int, values: dict, user: str = "system", loan_id=None, cfg: dict | None = None) -> int:
    n = 0
    for key, amount in values.items():
        conn.execute(
            """INSERT INTO liquidity_inputs (review_case_id, line_key, amount, note, updated_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, line_key) DO UPDATE SET amount=excluded.amount, updated_at=excluded.updated_at""",
            (review_case_id, key, _num(amount), None, now()))
        n += 1
    conn.commit()
    append_audit_event(conn, user, "liquidity_updated", "liquidity_worksheet", review_case_id,
                       after_value=f"{n} line items", review_case_id=review_case_id, loan_id=loan_id)
    cfg = cfg or load_liquidity_config()
    _carry_liquidity_finding(conn, review_case_id, compute_liquidity(load_liquidity_inputs(conn, review_case_id), cfg), user, loan_id)
    return n


def _carry_liquidity_finding(conn, review_case_id, result, user="system", loan_id=None):
    issue = f"Liquidity: {result['months_reserves']:.1f} months of reserves — {result['assessment']}"
    carry_finding(conn, review_case_id, "LIQUIDITY", "liquidity", result["severity"], issue, user, loan_id)


def load_liquidity_inputs(conn, review_case_id: int) -> dict:
    return {r["line_key"]: r["amount"] for r in conn.execute(
        "SELECT line_key, amount FROM liquidity_inputs WHERE review_case_id=?", (review_case_id,)).fetchall()}


def summarize_liquidity(conn, review_case_id: int, cfg: dict | None = None):
    values = load_liquidity_inputs(conn, review_case_id)
    if not any(_num(v) for v in values.values()):
        return None
    return compute_liquidity(values, cfg or load_liquidity_config())
