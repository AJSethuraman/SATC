"""Shared evaluation semantics for the Review Room card preview.

The workbook's formulas remain the authoritative computation in the
deliverable. This module exists so the UI can show the reviewer what a value
*means* the moment it is keyed — and a parity test pins these functions to
the recalc engine's results on the demo fixture, so preview and workbook can
never drift apart silently.

Deliberately supports exactly the grammar Mode B computed tests use — a
single comparison between a keyed attribute and a policy knob. Anything
richer raises, which fails the parity test and forces both sides to be
extended together.
"""

from __future__ import annotations

import re

from credit_review.config import ConfigError

_COMPARISON = re.compile(
    r"^\{(?P<attr>[a-z0-9_]+)\}\s*(?P<op>>=|<=|<>|>|<|=)\s*\[POL\s+(?P<key>[a-z0-9_]+)\]$")

_OPS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "=": lambda a, b: a == b,
    "<>": lambda a, b: a != b,
}


def computed_test_result(when: str, attributes: dict, knobs: dict) -> str:
    """Mirror the grid cell: 'fail' when the breach condition holds, else 'pass'."""
    m = _COMPARISON.match(when.strip())
    if not m:
        raise ConfigError(
            f"preview cannot evaluate {when!r} — extend evaluate.py AND the "
            f"sheet builder together (the parity test enforces this)")
    attr, op, key = m.group("attr"), m.group("op"), m.group("key")
    if attr not in attributes:
        raise ConfigError(f"missing attribute {attr!r}")
    if key not in knobs:
        raise ConfigError(f"missing policy knob {key!r}")
    return "fail" if _OPS[op](float(attributes[attr]), float(knobs[key])) else "pass"


def is_fringe(fringe_rules: tuple, attributes: dict, knobs: dict) -> bool:
    """Mirror the grid's FRINGE flag: within the band of a limit, on the
    approved side of the box."""
    for rule in fringe_rules:
        value = float(attributes[rule["attribute"]])
        limit = float(knobs[rule["limit_key"]])
        band = float(knobs[rule["band_key"]])
        if rule["direction"] == "floor":
            if limit <= value <= limit + band:
                return True
        else:
            if limit - band <= value <= limit:
                return True
    return False


def evaluate_file(product: dict, attributes: dict, attestations: dict,
                  knobs: dict) -> dict:
    """Everything the card shows for one file: per-test results + fringe."""
    results: dict[str, str] = {}
    for test in product["tests"]:
        if test["kind"] == "computed":
            results[test["id"]] = computed_test_result(test["when"], attributes, knobs)
        else:
            results[test["id"]] = attestations.get(test["id"]) or ""
    return {
        "tests": results,
        "fails": sum(1 for v in results.values() if v == "fail"),
        "fringe": is_fringe(product["fringe_rules"], attributes, knobs),
    }


def classify_pool(classification_type: str, pool: dict,
                  substandard_from_dpd: int = 90,
                  loss_from_dpd: int | None = None) -> dict:
    """Mirror the pool panel's URCCP sums (preview only)."""
    starts = {"current": 0, "dpd_30_59": 30, "dpd_60_89": 60, "dpd_90_119": 90,
              "dpd_120_179": 120, "dpd_180_plus": 180}
    if classification_type == "residential_secured":
        q, w = pool["qualifying_90_ltv60"], pool["writedown_loss"]
        return {"substandard": dict(q), "loss": dict(w)}
    if loss_from_dpd is None:
        loss_from_dpd = 120 if classification_type == "closed_end" else 180

    def total(from_dpd: int, key: str) -> float:
        return sum(pool[b][key] for b, start in starts.items() if start >= from_dpd)

    return {
        "substandard": {"count": total(substandard_from_dpd, "count"),
                        "dollars": total(substandard_from_dpd, "dollars")},
        "loss": {"count": total(loss_from_dpd, "count"),
                 "dollars": total(loss_from_dpd, "dollars")},
    }
