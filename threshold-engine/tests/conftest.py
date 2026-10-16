import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from threshold_engine import Point  # noqa: E402

DATA = ROOT / "tests" / "data"


def load(name):
    """A public series from tests/data: '#' lines are its source note."""
    with open(DATA / name, encoding="utf-8") as fh:
        rows = csv.DictReader(line for line in fh if not line.startswith("#"))
        return [Point(r["date"], float(r["value"])) for r in rows]


def quarters(values, first_year=2000):
    """Synthetic quarterly points, one per value, from first_year Q1."""
    out = []
    for i, v in enumerate(values):
        y, q = divmod(i, 4)
        out.append(Point("%d-%02d-01" % (first_year + y, 3 * q + 1), float(v)))
    return out



#: The workbook's scale at the settings agreed for cards (7 Oct 2026).
SCALE = dict(halfwidth=0.5, low_step=1.0, high_z=2.5, on_the_line="worse")


def as_earlier_build(data):
    """Roster data as the 6 Oct 2026 build read it. That build divided other
    consumer by RC-C 6.d alone; the balance is now 6.b + 6.d (LNCONRP +
    LNCONOTH, books.PRODUCTS). The acceptance numbers it produced are
    reproduced on this copy, which has 6.b at 0; the data itself is not
    changed."""
    return {q: [dict(r, LNCONRP=0) if "LNCONRP" in r else r for r in rows] for q, rows in data.items()}
