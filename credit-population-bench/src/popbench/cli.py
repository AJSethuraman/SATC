"""``popbench`` CLI — build the demo workbook (the button, headless).

Slice 1 ships the demo path: fabricate the synthetic population, auto-propose
and (here) accept the obvious mapping, run the engine, and write a deterministic
workbook. Real-file loading + the interactive confirm UI arrive on the ``.xlsm``
surface with later slices.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from popbench import contract, demo, mapping, report
from popbench.engine import build, run_analysis


def _demo_mapping(headers: list[str]) -> mapping.Mapping:
    """Accept the auto-proposal for the demo (every column resolves confidently);
    declare fraction units for the ambiguous-scale fields (the demo's LTV/CLTV
    is stored as a fraction)."""
    proposals = mapping.propose(headers)
    columns = []
    for p in proposals:
        if p.field_id is None:
            continue
        unit = contract.UNIT_FRACTION if p.needs_unit else None
        columns.append(mapping.ColumnMap(p.header, p.field_id, unit))
    return mapping.confirm(columns)


def _demo_inputs():
    pop = demo.demo_population_full()
    m = _demo_mapping(list(pop.columns))
    kw = dict(cohort_specs=demo.demo_cohorts(),
              sample_selection={"L-102", "L-103", "L-104"},
              sample_dimension="product_type")
    return pop, m, kw


def build_demo_bytes() -> bytes:
    """The canonical demo workbook build — used by the CLI and the ASCII bundle
    so both produce byte-identical output."""
    pop, m, kw = _demo_inputs()
    return build(pop, m, **kw)


def demo_report_html() -> str:
    """Render the demo run as an HTML examination workpaper."""
    pop, m, kw = _demo_inputs()
    return report.render(run_analysis(pop, m, **kw), title="Consumer portfolio review (demo)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="popbench",
                                 description="Consumer credit population bench")
    ap.add_argument("--demo", action="store_true",
                    help="build the synthetic demo workbook")
    ap.add_argument("-o", "--out", default="population_bench_demo.xlsx",
                    help="output workbook path")
    ap.add_argument("--report", metavar="HTML",
                    help="also write an HTML examination workpaper to this path")
    ap.add_argument("--workbook", metavar="PATH",
                    help="re-run from an existing workbook, reading the Selection "
                         "tab (the reviewer's judgmental pick) back and recomputing")
    args = ap.parse_args(argv)

    if args.workbook:
        from popbench.roundtrip import run_workbook
        run_workbook(args.workbook)
        print(f"re-ran {args.workbook} from its Selection tab")
        return 0

    if not args.demo and not args.report:
        ap.print_help()
        return 0

    if args.demo:
        data = build_demo_bytes()
        Path(args.out).write_bytes(data)
        print(f"wrote {args.out} ({len(data)} bytes)")
    if args.report:
        Path(args.report).write_text(demo_report_html(), encoding="utf-8")
        print(f"wrote {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
