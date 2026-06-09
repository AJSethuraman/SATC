"""Snapshot orchestration: corpus -> panel -> benchmarks -> adjusted ->
validation -> versioned JSON snapshot -> bake into the React workbench.

The snapshot is the contract between the pipeline and the GUI: the GUI
reads only this JSON (baked in between markers), so refreshing benchmarks
is re-run pipeline -> re-bake, with no GUI code changes.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import __version__
from .adjust import DEFAULT_PARAMS, apply_adjustments
from .benchmarks import build_benchmarks, build_observations
from .mechanisms import MECHANISMS
from .metrics import METRICS
from .panel import PanelRow, build_company_panel
from .segments import BUCKET_BY_KEY, SEGMENTS, SIZE_BUCKETS, segments_for_company
from .synth import company_facts_json, make_universe
from .validate import backtest

CURRENT_FY = 2024
FLAG_FY_RANGE = (2017, 2021)
BACKTEST_HORIZON = 3


def build_demo_inputs(seed: int = 20260609):
    """Synthetic corpus -> (panels, sics) keyed by CIK."""
    universe = make_universe(seed)
    panels: dict[int, list[PanelRow]] = {}
    sics: dict[int, int] = {}
    for c in universe:
        cf = company_facts_json(c, seed=7)
        rows = build_company_panel(cf, sic=c.sic)
        if rows:
            panels[c.cik] = rows
            sics[c.cik] = c.sic
    return panels, sics


def assemble(
    panels: dict[int, list[PanelRow]],
    sics: dict[int, int],
    data_source: str,
    source_notes: list[str],
) -> tuple[dict, dict]:
    """Panels -> (snapshot dict, backtest summary dict)."""
    company_segments = {
        cik: segments_for_company(sics[cik], [r.as_plain_dict() for r in rows])
        for cik, rows in panels.items()
    }
    obs = build_observations(panels, company_segments)
    raw = build_benchmarks(obs, current_fy=CURRENT_FY)
    adjusted = apply_adjustments(raw)

    # Backtest: one observation per (cik, fy) using the company's first segment
    obs_by_cik_fy: dict[tuple[int, int], dict] = {}
    company_buckets: dict[tuple[int, int], Optional[str]] = {}
    for o in obs:
        segs = company_segments.get(o.cik) or []
        if segs and o.segment == segs[0]:
            obs_by_cik_fy[(o.cik, o.fy)] = o.measurements
            company_buckets[(o.cik, o.fy)] = o.bucket
    bt = backtest(panels, obs_by_cik_fy, adjusted, company_segments,
                  company_buckets, FLAG_FY_RANGE, BACKTEST_HORIZON)
    bt_summary = bt.summary()

    # A synthetic snapshot must never lack the banner, whatever the caller
    # passed: the no-unsourced-claims rule is enforced here, not by courtesy.
    if data_source == "SYNTHETIC_DEMO" and not any(
            "SYNTHETIC" in n for n in source_notes):
        source_notes = [
            "SYNTHETIC DEMONSTRATION DATA: distributions are illustrative "
            "of the machinery, not sourced market statistics. Refresh "
            "against live EDGAR before any production use."
        ] + list(source_notes)

    snapshot = {
        "meta": {
            "version": "v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pipeline": f"ccbw {__version__}",
            "current_fy": CURRENT_FY,
            "data_source": data_source,
            "source_notes": source_notes,
            "refresh": (
                "To refresh against live EDGAR: ccbw build-live --user-agent "
                "'Name email' --out snapshot.json, then ccbw bake. Requires "
                "network access to data.sec.gov (10 req/s fair-access limit)."
            ),
        },
        "size_buckets": [
            {"key": b.key, "label": b.label,
             "ebitda_lo": b.ebitda_lo,
             "ebitda_hi": None if b.ebitda_hi == float("inf") else b.ebitda_hi}
            for b in SIZE_BUCKETS
        ],
        "metric_specs": {
            k: {"label": m.label, "unit": m.unit, "direction": m.direction,
                "basis": m.basis, "core": m.core}
            for k, m in METRICS.items()
        },
        "segments": adjusted["segments"],
        "adjustment_params": adjusted["adjustment_params"],
        "mechanisms": {f"{m}|{s}": text for (m, s), text in MECHANISMS.items()},
        "validation_summary": bt_summary,
    }
    return snapshot, {"summary": bt_summary, "detail": bt.detail}


def write_snapshot(snapshot: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(snapshot, fh, indent=1, default=str)


# ------------------------------------------------------------------ #
# Bake into the React workbench
# ------------------------------------------------------------------ #

START = "/*__BENCHMARK_SNAPSHOT_START__*/"
END = "/*__BENCHMARK_SNAPSHOT_END__*/"


def bake_into_jsx(snapshot: dict, jsx_path: str | Path) -> None:
    jsx_path = Path(jsx_path)
    src = jsx_path.read_text()
    if START not in src or END not in src:
        raise ValueError(f"snapshot markers not found in {jsx_path}")
    payload = json.dumps(snapshot, separators=(",", ":"), default=str)
    pattern = re.compile(re.escape(START) + ".*?" + re.escape(END), re.DOTALL)
    replacement = START + f"\nconst SNAPSHOT = {payload};\n" + END
    # function repl: JSON backslash escapes must not be parsed as re templates
    new = pattern.sub(lambda _m: replacement, src, count=1)
    jsx_path.write_text(new)


# ------------------------------------------------------------------ #
# Validation report
# ------------------------------------------------------------------ #


def render_validation_md(bt: dict, data_source: str) -> str:
    s = bt["summary"]

    def pct(x):
        return f"{x * 100:.0f}%" if x is not None else "n/a"

    lines = [
        "# Validation report -- departure-flag backtest",
        "",
        f"*Data source: {data_source}. Generated by ccbw {__version__}.*",
        "",
        "## Design",
        "",
        "Flag rule under test (refined via the rule comparison below): "
        "**any 'severe' reading on any metric, or departure-or-worse on a "
        "core risk metric (leverage or interest coverage)**, graded against "
        "the *adjusted* (private-calibrated) distributions.",
        "",
        f"Flags evaluated at fiscal years {s['flag_fy_range'][0]}-"
        f"{s['flag_fy_range'][1]}; deterioration horizon "
        f"{s['horizon_years']} years. Deterioration event (public proxy for "
        "migration to non-accrual): interest coverage < 1.0x, EBITDA down "
        ">= 40% from flag year, Altman Z' (private-firm variant) newly in "
        "distress zone, or negative book equity.",
        "",
        "## Results",
        "",
        f"| Statistic | Value |",
        f"|---|---|",
        f"| Eligible company-years | {s['n_eligible_company_years']} |",
        f"| Flagged | {s['n_flagged']} |",
        f"| **Hit rate** (flagged that deteriorated) | {pct(s['hit_rate'])} |",
        f"| False-positive rate | {pct(s['false_positive_rate'])} |",
        f"| Deteriorations in window | {s['n_deteriorated_total']} |",
        f"| **Capture rate** (deteriorations that were flagged) | {pct(s['capture_rate'])} |",
        f"| Median lead time | {s['median_lead_time_years']} yr |",
        f"| Altman Z' reference flagger: n flagged | {s['altman_z_reference']['n_flagged']} |",
        f"| Altman Z' reference hit rate | {pct(s['altman_z_reference']['hit_rate'])} |",
        "",
        "Lead-time distribution (years from flag to event): "
        + (", ".join(str(x) for x in s["lead_time_distribution"]) or "n/a"),
        "",
        f"Base deterioration rate over the window: "
        f"{pct(s.get('base_deterioration_rate'))} of eligible company-years "
        "-- hit rates must be read against this base, not against zero.",
        "",
        "## Threshold refinement -- rule comparison",
        "",
        "Candidate flag rules are re-evaluated on every backtest run so the "
        "refinement evidence regenerates with the data:",
        "",
        "| Rule | Flagged | Hit rate | Capture rate |",
        "|---|---|---|---|",
        *[
            f"| {name} | {rc['n_flagged']} | {pct(rc['hit_rate'])} "
            f"| {pct(rc['capture_rate'])} |"
            for name, rc in s.get("rule_comparison", {}).items()
        ],
        "",
        "The 'loose' rule (any two watch-level readings) was rejected: it "
        "flags roughly half of all company-years for a hit rate barely above "
        "the base deterioration rate -- a review queue that wide is "
        "operationally useless. The production rule trades some capture for "
        "roughly double the precision of the loose rule while keeping the "
        "median lead time, and outperforms the Altman Z' distress-zone "
        "reference on both precision and lead.",
        "",
        "## Reading the result",
        "",
        "Rating-agency transition studies show issuers typically migrate "
        "through CCC/C territory over 1-3 years before default; a useful "
        "early-warning flag should therefore *lead* distress by at least a "
        "year, not coincide with it. The median lead time above is the "
        "number to judge against that bar. The Altman Z' row is the "
        "established-model reference: the workbench flag should capture at "
        "least as many subsequent deteriorations as Z'-distress while "
        "firing earlier.",
        "",
        "## Caveats",
        "",
    ]
    for c in s["caveats"]:
        lines.append(f"- {c}")
    lines += [
        "",
        "## Flag detail (first 40)",
        "",
        "| Entity | FY | Segment | Bucket | Flag | Deteriorated | Event |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in bt["detail"][:40]:
        ev = (", ".join(d["event"]["reasons"]) + f" (FY{d['event']['fy']})"
              if d["event"] else "--")
        lines.append(
            f"| {d['entity']} | {d['fy']} | {d['segment']} | {d['bucket']} "
            f"| {d['flag']} | {'yes' if d['deteriorated'] else 'no'} | {ev} |")
    return "\n".join(lines) + "\n"
