"""Cash Flow / Income Analysis engine.

A broad, gross (pre-tax) income worksheet. Each income source line is entered
across up to two periods and normalized to one monthly qualifying figure using
a per-line basis (Annual/Monthly) and method (Latest/Average/Lower of). K-1
business owners qualify on cash distributions; pro-rata business income is
captured only as a reference (role: reference) and never added to qualifying
income.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "cash_flow_v1.yaml"


def load_cash_flow_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    if not isinstance(cfg, dict) or "sources" not in cfg:
        raise ValueError("Cash flow config must define a 'sources' list")
    cfg.setdefault("methods", ["Latest", "Average", "Lower of"])
    cfg.setdefault("bases", ["Annual", "Monthly"])
    cfg.setdefault("default_basis", "Annual")
    cfg.setdefault("default_method", "Average")
    return cfg


def source_lines(cfg: dict):
    """Yield (section_name, key, label, role) for every line, in order."""
    for sec in cfg["sources"]:
        for ln in sec["lines"]:
            yield sec["section_name"], ln["key"], ln["label"], ln.get("role", "qualifying")


from .calc_common import num as _num


def normalize_line(p1, p2, basis: str, method: str) -> float:
    """Combine two periods per method, then convert to a monthly figure."""
    p1, p2 = _num(p1), _num(p2)
    present = [x for x in (p1, p2) if x]  # treat 0 / blank as "not provided"
    if method == "Latest":
        base = p2 if p2 else p1
    elif method == "Lower of":
        base = min(present) if present else 0.0
    else:  # Average (default)
        base = sum(present) / len(present) if present else 0.0
    return round(base if basis == "Monthly" else base / 12.0, 2)


def compute_cash_flow(values: dict, cfg: dict) -> dict:
    """values: {line_key: {"period1","period2","basis","method"}} -> totals."""
    db, dm = cfg["default_basis"], cfg["default_method"]
    lines = []
    qualifying = 0.0
    reference = 0.0
    for section, key, label, role in source_lines(cfg):
        v = values.get(key) or {}
        basis = v.get("basis") or db
        method = v.get("method") or dm
        monthly = normalize_line(v.get("period1"), v.get("period2"), basis, method)
        lines.append({"section": section, "key": key, "label": label, "role": role,
                      "basis": basis, "method": method, "monthly": monthly})
        if role == "reference":
            reference += monthly
        else:
            qualifying += monthly
    return {
        "lines": lines,
        "qualifying_monthly": round(qualifying, 2),
        "qualifying_annual": round(qualifying * 12, 2),
        "business_income_reference_monthly": round(reference, 2),
    }


def save_cash_flow_inputs(conn, review_case_id: int, values: dict, user: str = "system", loan_id=None) -> int:
    """Upsert cash-flow line inputs for a review case and log one audit event."""
    n = 0
    for key, v in values.items():
        v = v or {}
        conn.execute(
            """INSERT INTO cash_flow_inputs (review_case_id, line_key, period1, period2, basis, method, note, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, line_key)
               DO UPDATE SET period1=excluded.period1, period2=excluded.period2, basis=excluded.basis,
                             method=excluded.method, note=excluded.note, updated_at=excluded.updated_at""",
            (review_case_id, key, _num(v.get("period1")), _num(v.get("period2")),
             v.get("basis"), v.get("method"), v.get("note"), now()),
        )
        n += 1
    conn.commit()
    append_audit_event(conn, user, "cash_flow_updated", "cash_flow_worksheet", review_case_id,
                       after_value=f"{n} line items", review_case_id=review_case_id, loan_id=loan_id)
    return n


def load_cash_flow_inputs(conn, review_case_id: int) -> dict:
    rows = conn.execute(
        "SELECT line_key, period1, period2, basis, method FROM cash_flow_inputs WHERE review_case_id=?",
        (review_case_id,),
    ).fetchall()
    return {r["line_key"]: {"period1": r["period1"], "period2": r["period2"], "basis": r["basis"], "method": r["method"]}
            for r in rows}


def summarize_cash_flow(conn, review_case_id: int, cfg: dict | None = None):
    """Return computed cash-flow totals for a case, or None if empty."""
    values = load_cash_flow_inputs(conn, review_case_id)
    if not any(_num(v.get("period1")) or _num(v.get("period2")) for v in values.values()):
        return None
    return compute_cash_flow(values, cfg or load_cash_flow_config())
