#!/usr/bin/env python3
"""One-shot build: base workbook (formulas, tabs, code, docs) -> macro-enabled
.xlsm with the embedded VBA project.

    python3 make_workbook.py [--footprint-slots N]

--footprint-slots is the BUILT county capacity (default 40): the [FOOTPRINT]
table, the slot-anchored Raw_CFPB blocks and every Watchlist row are
provisioned for N counties. Within capacity, the footprint is a config edit;
beyond it, the runner refuses with this exact rebuild command.
"""
import argparse
import os

import assemble_xlsm
import build_workbook
import runner as R

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(
        description="Build the County Mortgage Delinquency Monitor workbook")
    ap.add_argument("--footprint-slots", type=int,
                    default=R.FOOTPRINT_SLOTS_DEFAULT,
                    help="built county capacity (default %(default)s)")
    args = ap.parse_args()
    if args.footprint_slots < 1:
        ap.error("--footprint-slots must be >= 1")
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    base = os.path.join(HERE, "build", "Mortgage_Delinquency_Monitor_base.xlsx")
    out = os.path.join(HERE, "Mortgage_Delinquency_Monitor.xlsm")
    _, n_series, n_admitted, cap = build_workbook.build(
        base, footprint_slots=args.footprint_slots)
    assemble_xlsm.assemble(base, out)
    print(f"built {out}")
    print(f"  series rows: {n_series} | county slots: {cap} | seed counties "
          f"admitted: {n_admitted} | size: {os.path.getsize(out)} bytes")
    return out


if __name__ == "__main__":
    main()
