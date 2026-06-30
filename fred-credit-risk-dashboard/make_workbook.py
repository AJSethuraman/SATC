#!/usr/bin/env python3
"""One-shot build: base workbook (formulas, tabs, code, docs) -> macro-enabled
.xlsm with the embedded VBA project. Run: python3 make_workbook.py
"""
import os

import assemble_xlsm
import build_workbook

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    base = os.path.join(HERE, "build", "FRED_Credit_Risk_Dashboard_base.xlsx")
    out = os.path.join(HERE, "FRED_Credit_Risk_Dashboard.xlsm")
    _, n, nwl = build_workbook.build(base)
    assemble_xlsm.assemble(base, out)
    print(f"built {out}")
    print(f"  series: {n} | watchlist-capable: {nwl} | size: {os.path.getsize(out)} bytes")
    return out


if __name__ == "__main__":
    main()
