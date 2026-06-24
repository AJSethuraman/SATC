"""Build the SATC demo workbook and recalculate it to zero formula errors.

Usage:
    PYTHONPATH=src python scripts/build_workbook.py [output.xlsx] [tax_year]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))          # scripts/ (office shim)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # src/

from satc.build import build_demo_workbook  # noqa: E402
from recalc import recalc  # noqa: E402


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else None
    tax_year = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
    path = build_demo_workbook(out, tax_year) if out else build_demo_workbook(tax_year=tax_year)
    print(f"Built {path}")
    result = recalc(str(path), timeout=120)
    print(json.dumps(result, indent=2))
    if result.get("status") != "success":
        sys.exit(2)


if __name__ == "__main__":
    main()
