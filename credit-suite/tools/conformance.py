#!/usr/bin/env python3
"""Run the spine conformance check (issue #168).

    python tools/conformance.py            # every check
    python tools/conformance.py --quick    # skip the checks that build a workbook

Exit 0 when the spine conforms, 2 when it does not -- drift is a gate error,
not a crash.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import monitorbuild                                        # noqa: E402
from credit_suite import conformance                       # noqa: E402
from credit_suite.engine import runtime                    # noqa: E402


def _built_tabs() -> dict:
    import openpyxl

    tabs = {}
    for name in sorted(conformance.MIGRATED_FOLDERS.values()):
        with monitorbuild.built_monitor(name, run_demo=False) as (workbook, _):
            wb = openpyxl.load_workbook(workbook, keep_vba=True, read_only=True)
            try:
                tabs[name] = list(wb.sheetnames)
            finally:
                wb.close()
    return tabs


def _parsers() -> dict:
    from credit_suite.sources.fdic import runner as fdic_runner
    from credit_suite.sources.fred import runner as fred_runner

    out = {"fdic": fdic_runner.build_parser()}
    builder = getattr(fred_runner, "build_parser", None)
    if builder is not None:
        out["fred"] = builder()
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="skip checks that build a workbook")
    args = ap.parse_args(argv)

    findings = []
    pending = []
    examined = {}

    found, still_pending, counts = conformance.check_single_sourced()
    findings.extend(found)
    pending.extend(still_pending)
    examined.update(counts)

    for found, counts in (conformance.check_exit_codes(runtime),
                          conformance.check_cli(_parsers())):
        findings.extend(found)
        examined.update(counts)

    if not args.quick:
        found, counts = conformance.check_tabs(_built_tabs())
        findings.extend(found)
        examined.update(counts)
    else:
        print("(--quick: tab check skipped -- it builds a workbook)")

    report = conformance.Report(findings, examined, pending)
    print(report.describe())
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
