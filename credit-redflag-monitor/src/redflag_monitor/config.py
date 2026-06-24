"""Signal Dictionary configuration model and loaders.

One ``Signal`` is one row of the Signal Dictionary (spec section 5). The
dictionary lives in a spreadsheet so a non-technical owner tunes thresholds by
editing cells rather than touching code. We load it from the workbook's
``Signal Dictionary`` sheet when present, otherwise from a sibling CSV, and
fall back to the bundled seed set (spec section 6) on first run.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# --- Allowed enum values -----------------------------------------------------

CATEGORIES = {"Rate", "Macro", "Credit-Benchmark", "Internal"}
SOURCES = {"FRED"}
FREQUENCIES = {"daily", "monthly", "quarterly"}
THRESHOLD_TYPES = {
    "abs_change",
    "pct_change",
    "level_above",
    "level_below",
    "yoy_change",
}
DIRECTIONS = {"up", "down", "both"}

# Canonical column order for the Signal Dictionary sheet / CSV.
DICTIONARY_COLUMNS = [
    "series_id",
    "label",
    "category",
    "source",
    "native_frequency",
    "threshold_type",
    "threshold_value",
    "direction_that_matters",
    "active",
    "notes",
]


class ConfigError(Exception):
    """Raised when the Signal Dictionary is missing or malformed."""


@dataclass(frozen=True)
class Signal:
    """A single configured signal (one Signal Dictionary row)."""

    series_id: str
    label: str
    category: str
    source: str
    native_frequency: str
    threshold_type: str
    threshold_value: float
    direction_that_matters: str
    active: bool
    notes: str = ""

    def as_row(self) -> dict[str, Any]:
        """Render back to a dictionary-sheet row (active as ``Y``/``N``)."""
        return {
            "series_id": self.series_id,
            "label": self.label,
            "category": self.category,
            "source": self.source,
            "native_frequency": self.native_frequency,
            "threshold_type": self.threshold_type,
            "threshold_value": self.threshold_value,
            "direction_that_matters": self.direction_that_matters,
            "active": "Y" if self.active else "N",
            "notes": self.notes,
        }


# --- Parsing helpers ---------------------------------------------------------


def _truthy(value: Any) -> bool:
    """Interpret a spreadsheet ``active`` cell as a boolean."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"y", "yes", "true", "1", "active"}


def _require(value: Any, field: str, allowed: set[str], series_id: str) -> str:
    text = str(value).strip()
    if text not in allowed:
        raise ConfigError(
            f"signal {series_id!r}: {field} must be one of {sorted(allowed)}, got {text!r}"
        )
    return text


def signal_from_mapping(raw: dict[str, Any]) -> Signal:
    """Build and validate a ``Signal`` from a raw row mapping.

    Keys are matched case-insensitively against :data:`DICTIONARY_COLUMNS` so a
    hand-edited sheet with stray capitalisation still loads.
    """
    lower = {str(k).strip().lower(): v for k, v in raw.items()}

    series_id = str(lower.get("series_id", "")).strip()
    if not series_id:
        raise ConfigError("signal row is missing a series_id")

    label = str(lower.get("label", "")).strip() or series_id

    threshold_raw = lower.get("threshold_value")
    try:
        threshold_value = float(threshold_raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            f"signal {series_id!r}: threshold_value must be numeric, got {threshold_raw!r}"
        ) from exc

    return Signal(
        series_id=series_id,
        label=label,
        category=_require(lower.get("category"), "category", CATEGORIES, series_id),
        source=_require(lower.get("source", "FRED"), "source", SOURCES, series_id),
        native_frequency=_require(
            lower.get("native_frequency"), "native_frequency", FREQUENCIES, series_id
        ),
        threshold_type=_require(
            lower.get("threshold_type"), "threshold_type", THRESHOLD_TYPES, series_id
        ),
        threshold_value=threshold_value,
        direction_that_matters=_require(
            lower.get("direction_that_matters"),
            "direction_that_matters",
            DIRECTIONS,
            series_id,
        ),
        active=_truthy(lower.get("active", "Y")),
        notes=str(lower.get("notes", "") or "").strip(),
    )


def signals_from_rows(rows: Iterable[dict[str, Any]]) -> list[Signal]:
    """Validate a sequence of raw rows into ``Signal`` objects.

    Empty rows (no ``series_id``) are skipped so trailing blank spreadsheet
    rows do not raise. Duplicate series ids are rejected.
    """
    signals: list[Signal] = []
    seen: set[str] = set()
    for raw in rows:
        if not str(raw.get("series_id", "") or "").strip():
            continue
        signal = signal_from_mapping(raw)
        if signal.series_id in seen:
            raise ConfigError(f"duplicate series_id in dictionary: {signal.series_id!r}")
        seen.add(signal.series_id)
        signals.append(signal)
    if not signals:
        raise ConfigError("Signal Dictionary contains no usable signals")
    return signals


def load_signals_from_csv(path: str | Path) -> list[Signal]:
    """Load signals from a sibling CSV file."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise ConfigError(f"Signal Dictionary CSV not found: {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return signals_from_rows(reader)


def active_signals(signals: Iterable[Signal]) -> list[Signal]:
    """Return only the signals flagged active."""
    return [s for s in signals if s.active]
