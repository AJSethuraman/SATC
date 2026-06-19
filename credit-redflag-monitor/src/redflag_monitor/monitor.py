"""Run orchestration: fetch -> evaluate -> persist -> write workbook.

Wires the five components (spec section 4) into a single monthly run. Pure
glue: every decision lives in the engine and the config, never here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from redflag_monitor import excel_writer
from redflag_monitor.config import Signal, active_signals
from redflag_monitor.excel_writer import (
    DATA_COLUMNS,
    has_dictionary,
    read_dictionary_signals,
    write_workbook,
)
from redflag_monitor.fred import FredClient, Observation
from redflag_monitor.history import HistoryRow, append_history, read_history
from redflag_monitor.metrics import MetricResult, evaluate
from redflag_monitor.seed import seed_signals

DEFAULT_WORKBOOK = "credit_redflag_monitor.xlsx"
DEFAULT_HISTORY = "signal_history.csv"


class Fetcher(Protocol):
    """Anything exposing ``fetch_observations`` (real client or demo)."""

    def fetch_observations(self, series_id: str) -> list[Observation]: ...


@dataclass
class RunSummary:
    workbook: str
    history: str
    n_signals: int
    n_flagged: int
    n_errors: int
    flagged_labels: list[str]


def resolve_signals(workbook_path: str | Path) -> list[Signal]:
    """Use the workbook's editable dictionary if present, else the seed set."""
    if has_dictionary(workbook_path):
        return read_dictionary_signals(workbook_path)
    return seed_signals()


def _fmt_cell(value: float | None, places: int = 2) -> float | None:
    return round(value, places) if value is not None else None


def _flag_row(result: MetricResult) -> dict[str, Any]:
    """Map a metric result to the Flags sheet data columns."""
    s = result.signal
    if result.error:
        return {
            "Series ID": s.series_id,
            "Signal": s.label,
            "Category": s.category,
            "Current": f"ERR: {result.error}",
            "As-Of": "(no data)",
            "Prior": None,
            "Δ Abs": None,
            "Δ %": None,
            "Direction": s.direction_that_matters,
            "Threshold": result.threshold_display,
            "Auto-Flag": "N",
        }
    return {
        "Series ID": s.series_id,
        "Signal": s.label,
        "Category": s.category,
        "Current": _fmt_cell(result.current, 4),
        "As-Of": result.as_of,
        "Prior": _fmt_cell(result.prior, 4),
        "Δ Abs": _fmt_cell(result.delta_abs),
        "Δ %": _fmt_cell(result.delta_pct),
        "Direction": s.direction_that_matters,
        "Threshold": result.threshold_display,
        "Auto-Flag": "Y" if result.auto_flag else "N",
    }


def _history_row(result: MetricResult, run_date: str, retrieved: str) -> HistoryRow:
    s = result.signal
    return HistoryRow(
        run_date=run_date,
        retrieved_date=retrieved,
        series_id=s.series_id,
        label=s.label,
        category=s.category,
        as_of=result.as_of or "(no data)",
        current=_fmt_cell(result.current, 4),
        prior=_fmt_cell(result.prior, 4),
        prior_period=result.prior_period,
        delta_abs=_fmt_cell(result.delta_abs),
        delta_pct=_fmt_cell(result.delta_pct),
        auto_flag="Y" if result.auto_flag else "N",
    )


def run(
    fetcher: Fetcher,
    *,
    workbook_path: str | Path = DEFAULT_WORKBOOK,
    history_path: str | Path = DEFAULT_HISTORY,
    run_date: str | None = None,
    include_news: bool = True,
) -> RunSummary:
    """Execute one monthly run and write/refresh the workbook.

    ``fetcher`` is injected so production uses :class:`FredClient` and tests /
    demo use a synthetic client -- the orchestration is identical either way.
    """
    run_date = run_date or date.today().isoformat()
    signals = active_signals(resolve_signals(workbook_path))

    results: list[MetricResult] = []
    for signal in signals:
        try:
            observations = fetcher.fetch_observations(signal.series_id)
            results.append(evaluate(signal, observations))
        except Exception as exc:  # noqa: BLE001 - surface per-signal failures
            results.append(MetricResult(signal=signal, error=str(exc)))

    flag_rows = [_flag_row(r) for r in results]
    history_rows = [_history_row(r, run_date, run_date) for r in results if not r.error]

    append_history(history_path, history_rows)
    history_sheet_rows = read_history(history_path)

    write_workbook(
        workbook_path,
        flag_rows=flag_rows,
        history_rows=history_sheet_rows,
        signals=signals,
        include_news=include_news,
    )

    flagged = [r for r in results if not r.error and r.auto_flag]
    return RunSummary(
        workbook=str(workbook_path),
        history=str(history_path),
        n_signals=len(results),
        n_flagged=len(flagged),
        n_errors=sum(1 for r in results if r.error),
        flagged_labels=[r.signal.label for r in flagged],
    )


def build_fetcher(demo: bool = False, signals: list[Signal] | None = None) -> Fetcher:
    """Construct the real FRED client, or the demo client when ``demo`` is set."""
    if demo:
        from redflag_monitor.demo import DemoFredClient

        return DemoFredClient(signals or seed_signals())
    return FredClient()


# Re-export for convenience.
__all__ = [
    "run",
    "build_fetcher",
    "resolve_signals",
    "RunSummary",
    "DEFAULT_WORKBOOK",
    "DEFAULT_HISTORY",
    "DATA_COLUMNS",
    "excel_writer",
]
