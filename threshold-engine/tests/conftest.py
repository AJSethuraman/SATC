import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from threshold_engine import Measure, Point, Settings  # noqa: E402

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


NCO = Measure(name="net charge-off rate, trailing twelve months", unit="%",
              direction="higher_is_worse", frequency="quarterly",
              smoothing=1, floor_at_zero=True)


def settings(**over):
    """Settings for tests. Every field is still stated; tests override."""
    base = dict(scale_points=5, top_fraction=0.75, episode_height=0.25,
                materiality=None, outlier_ratio=2.0, min_other_episodes=1,
                window=None, exclusions=())
    base.update(over)
    return Settings(**base)
