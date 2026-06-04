"""Leverage & Liquidity engine — commercial balance-sheet spreads.

From a handful of balance-sheet / earnings inputs computes current ratio,
working capital, debt-to-worth and debt-to-EBITDA, scored against guidelines.
Same config -> engine -> table -> carry pattern as the other fixtures.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "leverage_v1.yaml"


def load_leverage_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    if not isinstance(cfg, dict) or "inputs" not in cfg:
        raise ValueError("Leverage config must define an 'inputs' block")
    cfg.setdefault("thresholds", {})
    return cfg


def input_lines(cfg):
    for ln in cfg["inputs"]["lines"]:
        yield ln["key"], ln["label"]


from .calc_common import num as _num, carry_finding


def compute_leverage(values: dict, cfg: dict) -> dict:
    th = cfg.get("thresholds", {})
    min_cr = float(th.get("min_current_ratio", 1.20))
    max_dtw = float(th.get("max_debt_to_worth", 4.0))
    max_dte = float(th.get("max_debt_to_ebitda", 4.0))

    ca = _num(values.get("current_assets"))
    cl = _num(values.get("current_liabilities"))
    tl = _num(values.get("total_liabilities"))
    tnw = _num(values.get("tangible_net_worth"))
    debt = _num(values.get("total_debt"))
    ebitda = _num(values.get("ebitda"))

    current_ratio = round(ca / cl, 2) if cl else 0.0
    working_capital = round(ca - cl, 2)
    debt_to_worth = round(tl / tnw, 2) if tnw else 0.0
    debt_to_ebitda = round(debt / ebitda, 2) if ebitda else 0.0

    breaches = []
    if cl and current_ratio < min_cr:
        breaches.append("current ratio")
    if tnw and debt_to_worth > max_dtw:
        breaches.append("debt-to-worth")
    if ebitda and debt_to_ebitda > max_dte:
        breaches.append("debt-to-EBITDA")

    if not any(_num(v) for v in values.values()):
        assessment, severity = "Inputs required", None
    elif breaches:
        assessment, severity = "Exceeds leverage / liquidity guidelines", "Finding"
    else:
        assessment, severity = "Within leverage guidelines", None

    return {
        "current_ratio": current_ratio, "working_capital": working_capital,
        "debt_to_worth": debt_to_worth, "debt_to_ebitda": debt_to_ebitda,
        "min_current_ratio": min_cr, "max_debt_to_worth": max_dtw, "max_debt_to_ebitda": max_dte,
        "breaches": breaches, "assessment": assessment, "severity": severity,
    }


def save_leverage_inputs(conn, review_case_id: int, values: dict, user: str = "system", loan_id=None, cfg: dict | None = None) -> int:
    n = 0
    for key, amount in values.items():
        conn.execute(
            """INSERT INTO leverage_inputs (review_case_id, line_key, amount, note, updated_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, line_key) DO UPDATE SET amount=excluded.amount, updated_at=excluded.updated_at""",
            (review_case_id, key, _num(amount), None, now()))
        n += 1
    conn.commit()
    append_audit_event(conn, user, "leverage_updated", "leverage_worksheet", review_case_id,
                       after_value=f"{n} line items", review_case_id=review_case_id, loan_id=loan_id)
    cfg = cfg or load_leverage_config()
    _carry_leverage_finding(conn, review_case_id, compute_leverage(load_leverage_inputs(conn, review_case_id), cfg), user, loan_id)
    return n


def _carry_leverage_finding(conn, review_case_id, result, user="system", loan_id=None):
    issue = f"Leverage/liquidity: {', '.join(result['breaches'])} outside guideline — {result['assessment']}"
    carry_finding(conn, review_case_id, "LEVERAGE", "leverage", result["severity"], issue, user, loan_id)


def load_leverage_inputs(conn, review_case_id: int) -> dict:
    return {r["line_key"]: r["amount"] for r in conn.execute(
        "SELECT line_key, amount FROM leverage_inputs WHERE review_case_id=?", (review_case_id,)).fetchall()}


def summarize_leverage(conn, review_case_id: int, cfg: dict | None = None):
    values = load_leverage_inputs(conn, review_case_id)
    if not any(_num(v) for v in values.values()):
        return None
    return compute_leverage(values, cfg or load_leverage_config())
