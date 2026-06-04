"""Borrowing Base engine — revolving lines / ABL.

Eligible collateral x advance rate, less reserves, gives the borrowing base;
compared to the line commitment and current outstanding for net availability
(or any overadvance). Same config -> engine -> table -> carry pattern.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "borrowing_base_v1.yaml"


def load_borrowing_base_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    if not isinstance(cfg, dict) or "collateral" not in cfg or "line" not in cfg:
        raise ValueError("Borrowing base config must define 'collateral' and 'line' blocks")
    cfg.setdefault("reserves", {"section_name": "Reserves", "lines": []})
    cfg.setdefault("thresholds", {})
    return cfg


def collateral_lines(cfg):
    for ln in cfg["collateral"]["lines"]:
        yield ln["key"], ln["label"], float(ln.get("advance_rate", 100))


def reserve_lines(cfg):
    for ln in cfg.get("reserves", {}).get("lines", []):
        yield ln["key"], ln["label"]


def line_lines(cfg):
    for ln in cfg["line"]["lines"]:
        yield ln["key"], ln["label"]


from .calc_common import num as _num, carry_finding


def compute_borrowing_base(values: dict, cfg: dict) -> dict:
    gross = 0.0
    lines = []
    for key, label, default_ar in collateral_lines(cfg):
        v = values.get(key) or {}
        val = _num(v.get("value"))
        ar = v.get("advance_rate")
        ar = float(ar) if ar not in (None, "") else default_ar
        eligible = round(val * ar / 100.0, 2)
        gross += eligible
        lines.append({"key": key, "label": label, "value": val, "advance_rate": ar, "eligible": eligible})

    reserves = sum(_num((values.get(k) or {}).get("value")) for k, _ in reserve_lines(cfg))
    borrowing_base = round(gross - reserves, 2)
    commitment = _num((values.get("line_commitment") or {}).get("value"))
    outstanding = _num((values.get("current_outstanding") or {}).get("value"))
    cap = commitment if commitment > 0 else borrowing_base
    net_availability = round(min(borrowing_base, cap) - outstanding, 2)
    overadvance = round(max(outstanding - borrowing_base, 0), 2)

    has_data = gross or reserves or commitment or outstanding
    if not has_data:
        assessment, severity = "Inputs required", None
    elif outstanding > borrowing_base:
        assessment, severity = "Overadvance — borrowing base shortfall", "Finding"
    else:
        assessment, severity = "Within borrowing base", None

    return {
        "lines": lines, "gross_availability": round(gross, 2), "total_reserves": round(reserves, 2),
        "borrowing_base": borrowing_base, "line_commitment": round(commitment, 2),
        "current_outstanding": round(outstanding, 2), "net_availability": net_availability,
        "overadvance": overadvance, "assessment": assessment, "severity": severity,
    }


def save_borrowing_base_inputs(conn, review_case_id: int, values: dict, user: str = "system", loan_id=None, cfg: dict | None = None) -> int:
    n = 0
    for key, v in values.items():
        v = v or {}
        ar = v.get("advance_rate")
        conn.execute(
            """INSERT INTO borrowing_base_inputs (review_case_id, line_key, value, advance_rate, note, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, line_key) DO UPDATE SET value=excluded.value, advance_rate=excluded.advance_rate, note=excluded.note, updated_at=excluded.updated_at""",
            (review_case_id, key, _num(v.get("value")), float(ar) if ar not in (None, "") else None, v.get("note"), now()))
        n += 1
    conn.commit()
    append_audit_event(conn, user, "borrowing_base_updated", "borrowing_base_worksheet", review_case_id,
                       after_value=f"{n} line items", review_case_id=review_case_id, loan_id=loan_id)
    cfg = cfg or load_borrowing_base_config()
    _carry_bb_finding(conn, review_case_id, compute_borrowing_base(load_borrowing_base_inputs(conn, review_case_id), cfg), user, loan_id)
    return n


def _carry_bb_finding(conn, review_case_id, result, user="system", loan_id=None):
    issue = f"Borrowing base: outstanding ${result['current_outstanding']:,.0f} vs base ${result['borrowing_base']:,.0f} — {result['assessment']}"
    carry_finding(conn, review_case_id, "BORROWING_BASE", "borrowing_base", result["severity"], issue, user, loan_id)


def load_borrowing_base_inputs(conn, review_case_id: int) -> dict:
    rows = conn.execute(
        "SELECT line_key, value, advance_rate FROM borrowing_base_inputs WHERE review_case_id=?", (review_case_id,)
    ).fetchall()
    return {r["line_key"]: {"value": r["value"], "advance_rate": r["advance_rate"]} for r in rows}


def summarize_borrowing_base(conn, review_case_id: int, cfg: dict | None = None):
    values = load_borrowing_base_inputs(conn, review_case_id)
    if not any(_num(v.get("value")) for v in values.values()):
        return None
    return compute_borrowing_base(values, cfg or load_borrowing_base_config())
