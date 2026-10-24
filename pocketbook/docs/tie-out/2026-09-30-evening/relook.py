"""Read the tabs that are read once (Start here, Control, Columns, Look, Record) again into a views folder's
figures.json, without reading every view again: read_book.read_once reads them from the first view only, so their
figures are replaced by its reading of that view. For a fix to the reader of those tabs.

    python3 relook.py VIEWS_DIR
"""
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
import read_book  # noqa: E402

ONCE = {"Start here", "Control", "Columns", "Look", "Record"}
d = Path(sys.argv[1])
plan = json.loads((d / "plan.json").read_text())
figs = json.loads((d / "figures.json").read_text())
first = plan[0]["file"]
keep = [f for f in figs if not (f["tab"] in ONCE and f["view"] == first[:-5])]
F = read_book.Figures()
read_book.read_once(F, load_workbook(d / "calculated" / first, data_only=True), first[:-5])
(d / "figures.json").write_text(json.dumps(keep + F.out, indent=0, default=str))
print(len(figs) - len(keep), "figures of the tabs read once replaced by", len(F.out))
