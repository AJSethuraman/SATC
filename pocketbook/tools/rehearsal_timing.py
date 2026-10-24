"""Where a bleed Run's time goes, measured on one recorded Run: reading the extract, the engine without the shuffle
test (as book.run's first pass builds it), and the engine with it.

    python tools/rehearsal_timing.py RUN_FOLDER STEM

RUN_FOLDER holds `<STEM>.csv` and the `<STEM> - PocketBook - what ran.yaml` a Run wrote beside its workbook (the
public-data rehearsal's `runs/sba-foia-bleed`, STEM `sba-foia-fy2000-2009`). The engine is run twice, so this takes
longer than the Run did. For docs/rehearsal-public-data-2026-09.md section 3; kept here so the figure can be rerun.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import yaml

from pocketbook import config as cfgmod, engine
from pocketbook.ingest import read_table


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    d, stem = Path(argv[0]), argv[1]
    ran, extract = d / f"{stem} - PocketBook - what ran.yaml", d / f"{stem}.csv"
    missing = [str(p) for p in (ran, extract) if not p.exists()]
    if missing:
        print(f"REFUSED: {', '.join(missing)} isn't there", file=sys.stderr)
        return 2
    raw = yaml.safe_load(ran.read_text(encoding="utf-8"))
    t = time.perf_counter()
    table = read_table(extract)
    print(f"read_table: {time.perf_counter() - t:.1f} s, {len(table.rows):,} rows", flush=True)
    cfg = cfgmod.parse(raw)
    none = cfgmod.Config(**{**cfg.__dict__, "benchmark": cfgmod.Benchmark(**{**cfg.benchmark.__dict__, "shuffles": 0})})
    t = time.perf_counter()
    res = engine.run(none, table)
    print(f"engine.run without the shuffle test: {time.perf_counter() - t:.1f} s, {len(res.grids)} grids", flush=True)
    t = time.perf_counter()
    engine.run(cfg, table)
    print(f"engine.run with {cfg.benchmark.shuffles:,} shuffles: {time.perf_counter() - t:.1f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
