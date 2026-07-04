#!/usr/bin/env python3
"""One-shot build: base workbook (formulas, tabs, code, docs) -> macro-enabled
.xlsm with the embedded VBA project.

    python3 make_workbook.py [--peer-slots N]

--peer-slots is the BUILT peer capacity (default 20): the [PEERS] table, the
slot-anchored Raw_EDGAR blocks and every dashboard/Watchlist row are
provisioned for N banks. Within capacity, the peer list is a config edit;
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
        description="Build the EDGAR Criticized/Classified Tracker workbook")
    ap.add_argument("--peer-slots", type=int, default=R.PEER_SLOTS_DEFAULT,
                    help="built peer capacity (default %(default)s)")
    args = ap.parse_args()
    if args.peer_slots < 1:
        ap.error("--peer-slots must be >= 1")
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    base = os.path.join(HERE, "build", "Crit_Class_Tracker_base.xlsx")
    out = os.path.join(HERE, "Crit_Class_Tracker.xlsm")
    _, n_metrics, n_admitted, cap = build_workbook.build(
        base, peer_slots=args.peer_slots)
    assemble_xlsm.assemble(base, out)
    print(f"built {out}")
    print(f"  metrics: {n_metrics} | peer slots: {cap} | seed peers admitted: "
          f"{n_admitted} | size: {os.path.getsize(out)} bytes")
    return out


if __name__ == "__main__":
    main()
