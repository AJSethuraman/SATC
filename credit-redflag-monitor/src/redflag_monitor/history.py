"""Append-only history store (spec section 4, component 4).

Each run appends every signal's latest reading to a persisted CSV log so the
team can see multi-month creep -- not just a point-in-time snapshot. We persist
both the value and ``retrieved_date`` alongside the observation period so FRED
revisions (spec section 7.5) stay auditable.

The Excel ``All Signals (History)`` sheet (spec section 8) is rendered from
this log by the writer.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

HISTORY_COLUMNS = [
    "run_date",
    "retrieved_date",
    "series_id",
    "label",
    "category",
    "as_of",
    "current",
    "prior",
    "prior_period",
    "delta_abs",
    "delta_pct",
    "auto_flag",
]


@dataclass(frozen=True)
class HistoryRow:
    run_date: str
    retrieved_date: str
    series_id: str
    label: str
    category: str
    as_of: str
    current: float | None
    prior: float | None
    prior_period: str | None
    delta_abs: float | None
    delta_pct: float | None
    auto_flag: str  # "Y" / "N"


def append_history(path: str | Path, rows: list[HistoryRow]) -> None:
    """Append rows to the history CSV, writing the header if the file is new."""
    if not rows:
        return
    history_path = Path(path)
    is_new = not history_path.exists() or history_path.stat().st_size == 0
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HISTORY_COLUMNS)
        if is_new:
            writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def read_history(path: str | Path) -> list[dict[str, str]]:
    """Read the full history log (empty list if absent)."""
    history_path = Path(path)
    if not history_path.exists():
        return []
    with history_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
