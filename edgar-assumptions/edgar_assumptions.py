#!/usr/bin/env python3
"""Entry point: ``python edgar_assumptions.py --sic 5140 --years 7 --out food_dist``.

Thin wrapper so the tool can be run directly without installation. All logic
lives in the ``satc_edgar`` package.
"""

import sys

from satc_edgar.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
