"""Collateral & LTV analysis engine.

Applies a type-specific advance rate to each collateral item's market value to
derive net (eligible) collateral value, then compares it to total exposure to
produce LTV, collateral coverage, and any excess/shortfall. Mirrors the DTI /
Cash Flow fixtures: config-driven, persisted per review case, results carry.
"""
from __future__ import annotations
from pathlib import Path
import yaml
from .db import now
from .audit import append_audit_event

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "collateral_v1.yaml"


def load_collateral_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    if not isinstance(cfg, dict) or "collateral" not in cfg or "exposure" not in cfg:
        raise ValueError("Collateral config must define 'collateral' and 'exposure' blocks")
    cfg.setdefault("thresholds", {})
    return cfg


def collateral_lines(cfg: dict):
    """Yield (key, label, default_advance_rate) for collateral items."""
    for ln in cfg["collateral"]["lines"]:
        yield ln["key"], ln["label"], float(ln.get("advance_rate", 100))


def exposure_lines(cfg: dict):
    for ln in cfg["exposure"]["lines"]:
        yield ln["key"], ln["label"]


from .calc_common import num as _num, carry_finding


def compute_collateral(values: dict, cfg: dict) -> dict:
    """values: {line_key: {"market_value","advance_rate"}} -> LTV / coverage."""
    th = cfg.get("thresholds", {})
    max_ltv = float(th.get("max_ltv", 80.0))
    min_coverage = float(th.get("min_coverage", 100.0))

    total_market = 0.0
    total_eligible = 0.0
    lines = []
    for key, label, default_ar in collateral_lines(cfg):
        v = values.get(key) or {}
        mv = _num(v.get("market_value"))
        ar = v.get("advance_rate")
        ar = float(ar) if ar not in (None, "") else default_ar
        eligible = round(mv * ar / 100.0, 2)
        total_market += mv
        total_eligible += eligible
        lines.append({"key": key, "label": label, "market_value": mv, "advance_rate": ar, "eligible_value": eligible})

    total_exposure = sum(_num((values.get(k) or {}).get("market_value")) for k, _ in exposure_lines(cfg))
    ltv = round(total_exposure / total_market * 100, 2) if total_market else 0.0
    coverage = round(total_eligible / total_exposure * 100, 2) if total_exposure else 0.0
    excess = round(total_eligible - total_exposure, 2)

    if total_exposure <= 0:
        assessment, severity = "Exposure required", None
    elif coverage < min_coverage:
        assessment, severity = "Undersecured — collateral shortfall", "Finding"
    elif ltv > max_ltv:
        assessment, severity = "Exceeds LTV guideline", "Finding"
    else:
        assessment, severity = "Adequately secured", None

    return {
        "lines": lines,
        "total_market_value": round(total_market, 2),
        "net_collateral_value": round(total_eligible, 2),
        "total_exposure": round(total_exposure, 2),
        "ltv": ltv,
        "coverage": coverage,
        "excess": excess,
        "max_ltv": max_ltv,
        "min_coverage": min_coverage,
        "assessment": assessment,
        "severity": severity,
    }


def save_collateral_inputs(conn, review_case_id: int, values: dict, user: str = "system", loan_id=None, cfg: dict | None = None) -> int:
    n = 0
    for key, v in values.items():
        v = v or {}
        ar = v.get("advance_rate")
        conn.execute(
            """INSERT INTO collateral_inputs (review_case_id, line_key, market_value, advance_rate, note, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(review_case_id, line_key)
               DO UPDATE SET market_value=excluded.market_value, advance_rate=excluded.advance_rate, note=excluded.note, updated_at=excluded.updated_at""",
            (review_case_id, key, _num(v.get("market_value")), float(ar) if ar not in (None, "") else None, v.get("note"), now()),
        )
        n += 1
    conn.commit()
    append_audit_event(conn, user, "collateral_updated", "collateral_worksheet", review_case_id,
                       after_value=f"{n} line items", review_case_id=review_case_id, loan_id=loan_id)
    cfg = cfg or load_collateral_config()
    _carry_collateral_finding(conn, review_case_id, compute_collateral(load_collateral_inputs(conn, review_case_id), cfg), user, loan_id)
    return n


def _carry_collateral_finding(conn, review_case_id, result, user="system", loan_id=None):
    issue = f"Collateral: LTV {result['ltv']:.1f}% / coverage {result['coverage']:.0f}% — {result['assessment']}"
    carry_finding(conn, review_case_id, "COLL_LTV", "collateral_ltv", result["severity"], issue, user, loan_id)


def load_collateral_inputs(conn, review_case_id: int) -> dict:
    rows = conn.execute(
        "SELECT line_key, market_value, advance_rate FROM collateral_inputs WHERE review_case_id=?", (review_case_id,)
    ).fetchall()
    return {r["line_key"]: {"market_value": r["market_value"], "advance_rate": r["advance_rate"]} for r in rows}


def summarize_collateral(conn, review_case_id: int, cfg: dict | None = None):
    values = load_collateral_inputs(conn, review_case_id)
    if not any(_num(v.get("market_value")) for v in values.values()):
        return None
    return compute_collateral(values, cfg or load_collateral_config())
