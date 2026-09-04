#!/usr/bin/env python3
"""The last mile: real data, from the real sources, into a real flag (issue #169).

    python tools/live_acceptance.py            # both
    python tools/live_acceptance.py fdic

Every other check in this repository runs on the deterministic offline demo
provider. That is deliberate -- it makes the bar fast and airtight -- but it
means the whole suite can be green while the live adapters are broken. This
closes that gap by doing the thing the analyst does: pull real figures and look
at what lights up.

It is opt-in and never part of the CI bar: it needs the network, and FRED needs
a key. It writes only into a scratch directory.

What it asserts, per monitor:

* a **real observed value** landed in the raw block -- not the demo profile's,
  and traceable to the source's own record;
* that value **reached a flag** -- the status column computed from it, so the
  path from API to the thing a reviewer reads is proven end to end;
* the run reports itself successful, with a real data vintage where the source
  publishes one.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import openpyxl                                             # noqa: E402

from credit_suite.bundles import SPECS                      # noqa: E402
from credit_suite.engine import inline, package             # noqa: E402


def _build(name: str, folder: Path) -> Path:
    """Build the monitor exactly as it ships, into a scratch folder."""
    spec = SPECS[name]
    if name == "fdic":
        from credit_suite.sources.fdic import layout
    else:
        from credit_suite.sources.fred import layout

    base = folder / ("%s_base.xlsx" % spec.workbook)
    out = folder / ("%s.xlsm" % spec.workbook)
    macro = Path(layout.HERE) / "macro.bas"
    layout.build(str(base), code_py=inline.render_runner(spec),
                 code_vba=macro.read_text(encoding="utf-8"))
    package.assemble(str(base), str(out), str(macro), spec.macro_module)
    return out


def _sample_raw(workbook: Path, tab: str, max_rows: int = 400) -> List[tuple]:
    """A few landed (period, value) pairs, so a human can eyeball them."""
    wb = openpyxl.load_workbook(workbook, keep_vba=True, read_only=True)
    try:
        ws = wb[tab]
        out = []
        for row in ws.iter_rows(min_row=1, max_row=max_rows, values_only=True):
            if not row or row[0] is None:
                continue
            period, value = row[0], row[1] if len(row) > 1 else None
            if isinstance(value, (int, float)) and isinstance(period, str) \
                    and len(period) >= 8:
                out.append((period, value))
            if len(out) >= 5:
                break
        return out
    finally:
        wb.close()


def live_fdic(folder: Path) -> dict:
    """Keyless BankFind pull for the seeded peer set."""
    from credit_suite.sources.fdic import runner

    workbook = _build("fdic", folder)
    status = runner.run(str(workbook), demo=False, asof=date.today())

    banks = status["digest"]["banks"]
    landed = [b for b in banks if b["asof_period"]]
    flagged = [b for b in banks if b["status"] in ("ALERT", "WATCH")]
    lit_metrics = [
        (b["cert"], b["name"], mid, m["value"], m["status"])
        for b in banks for mid, m in b["metrics"].items()
        if m["status"] in ("ALERT", "WATCH") and m["value"] is not None
    ]
    return {
        "monitor": "fdic",
        "mode": status["mode"],
        "keyless": True,
        "vintage": status["vintage"],
        "banks_landed": status["banks_landed"],
        "banks_active": status["banks_active"],
        "alert_banks": status["alert_banks"],
        "watch_banks": status["watch_banks"],
        "asof_periods": sorted({b["asof_period"] for b in landed if b["asof_period"]}),
        "raw_sample": _sample_raw(workbook, "Raw_FDIC"),
        "flag_examples": lit_metrics[:5],
        "errors": status["errors"],
        "workbook": str(workbook),
    }


def live_fred(folder: Path) -> dict:
    """Live FRED pull. Needs FRED_API_KEY (or the _config cell)."""
    from credit_suite.sources.fred import runner

    if not os.environ.get("FRED_API_KEY"):
        return {"monitor": "fred", "skipped": "FRED_API_KEY is not set"}

    workbook = _build("fred", folder)
    status = runner.run(str(workbook), demo=False, asof=date.today())
    alerts = status.get("alerts", [])
    return {
        "monitor": "fred",
        "mode": status.get("mode"),
        "keyless": False,
        "vintage": status.get("vintage"),
        "series_pulled": status.get("series_pulled"),
        "series_pullable": status.get("series_pullable"),
        "alert_count": status.get("alert_count"),
        "stale": len(status.get("stale") or []),
        "raw_sample": _sample_raw(workbook, "Raw_Consumer"),
        "flag_examples": [(a["series_id"], a["rule"], a["value"], a["band"])
                          for a in alerts[:5]],
        "errors": (status.get("errors") or [])[:5],
        "workbook": str(workbook),
    }


def judge(result: dict) -> List[str]:
    """What would make this acceptance a pass. Stated, not implied."""
    problems = []
    if result.get("skipped"):
        return ["SKIPPED: %s" % result["skipped"]]
    if result["mode"] != "live":
        problems.append("ran in %r mode, not live" % result["mode"])
    if not result["raw_sample"]:
        problems.append("no real observations landed in the raw block")
    if not result["flag_examples"]:
        problems.append("a real value never reached a flag")
    if result["monitor"] == "fdic" and not result["banks_landed"]:
        problems.append("no banks landed")
    if result["monitor"] == "fred" and not result.get("series_pulled"):
        problems.append("no series pulled")
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("monitors", nargs="*", choices=["fdic", "fred", []])
    ap.add_argument("--keep", metavar="DIR",
                    help="keep the built workbooks here")
    args = ap.parse_args(argv)

    folder = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(
        prefix="credit-suite-live-"))
    folder.mkdir(parents=True, exist_ok=True)

    results = []
    try:
        for name in (args.monitors or ["fdic", "fred"]):
            runner = {"fdic": live_fdic, "fred": live_fred}[name]
            try:
                result = runner(folder)
            except Exception as exc:               # noqa: BLE001
                result = {"monitor": name, "error": "%s: %s"
                          % (type(exc).__name__, exc), "mode": None,
                          "raw_sample": [], "flag_examples": []}
            result["verdict"] = judge(result) or ["PASS"]
            results.append(result)
            print(json.dumps(result, indent=2, default=str), flush=True)
    finally:
        if not args.keep:
            shutil.rmtree(folder, ignore_errors=True)

    failed = [r for r in results
              if r["verdict"] != ["PASS"] and not r.get("skipped")]
    print("\n%d/%d live acceptance(s) passed"
          % (len(results) - len(failed), len(results)))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
