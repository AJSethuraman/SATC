"""SATC command-line entry point.

    satc app                 launch the local web GUI
    satc build [out.xlsx]    build the demo workpaper workbook (and recalc note)
    satc seed [--dir DIR]    initialize the SQLite store from synthetic fixtures
    satc export [out.xlsx]   export the data mart to Excel
    satc reset [--dir DIR]   delete the local databases (start fresh)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="satc", description="SATC tax tooling")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("app", help="launch the local web GUI")

    p_build = sub.add_parser("build", help="build the demo workpaper workbook")
    p_build.add_argument("out", nargs="?", default=None)
    p_build.add_argument("--tax-year", type=int, default=2024)

    p_seed = sub.add_parser("seed", help="initialize the SQLite store from fixtures")
    p_seed.add_argument("--dir", default=None)

    p_export = sub.add_parser("export", help="export the data mart to Excel")
    p_export.add_argument("out", nargs="?", default="SATC_DataMart.xlsx")
    p_export.add_argument("--dir", default=None)

    p_reset = sub.add_parser("reset", help="delete the local databases")
    p_reset.add_argument("--dir", default=None)

    args = parser.parse_args(argv)

    if args.cmd == "app":
        from satc.app.server import main as app_main
        app_main()
        return 0

    if args.cmd == "build":
        from satc.build import build_demo_workbook
        out = build_demo_workbook(args.out, args.tax_year) if args.out else build_demo_workbook(tax_year=args.tax_year)
        print(f"Built {out}  (run scripts/recalc.py on it to evaluate formulas)")
        return 0

    if args.cmd == "seed":
        from satc.persistence import SATCStore
        store = SATCStore(args.dir)
        seeded = store.seed_if_empty()
        print(f"{'Seeded' if seeded else 'Already populated'}: {store.dir}")
        return 0

    if args.cmd == "export":
        from satc.persistence import SATCStore, export_mart_to_excel
        store = SATCStore(args.dir)
        store.seed_if_empty()
        out = export_mart_to_excel(store, args.out)
        print(f"Exported {out}")
        return 0

    if args.cmd == "reset":
        from satc.persistence.store import DEFAULT_DIR
        d = Path(args.dir) if args.dir else DEFAULT_DIR
        for name in ("satc_vault.db", "satc_mart.db"):
            (d / name).unlink(missing_ok=True)
        print(f"Reset store in {d}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
