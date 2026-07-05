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

from popbench import contract, demo, mapping
from popbench.engine import build


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="popbench",
                                 description="Consumer credit population bench")
    ap.add_argument("--demo", action="store_true",
                    help="build the synthetic demo workbook")
    ap.add_argument("-o", "--out", default="population_bench_demo.xlsx",
                    help="output workbook path")
    args = ap.parse_args(argv)

    if not args.demo:
        ap.print_help()
        return 0

    pop = demo.demo_population_full()
    m = _demo_mapping(list(pop.columns))
    data = build(pop, m, cohort_specs=demo.demo_cohorts())
    Path(args.out).write_bytes(data)
    print(f"wrote {args.out} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
