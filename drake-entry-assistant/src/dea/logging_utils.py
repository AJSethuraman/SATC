"""Logging and report helpers for safe, masked diagnostics."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from openpyxl import Workbook

from dea.models import ActionStep, EntryLogRecord, ValidationIssue


_ENTRY_HEADERS = [
    "timestamp",
    "client_id",
    "tax_year",
    "mode",
    "screen",
    "field",
    "source_sheet",
    "source_cell",
    "masked_value",
    "action",
    "status",
    "error_message",
]

_VALIDATION_HEADERS = ["severity", "client_id", "field", "message", "source_sheet", "source_cell"]


def _default_status_for_action(action: str) -> str:
    if action == "SKIP_MANUAL_REVIEW":
        return "SKIPPED_MANUAL_REVIEW"
    if action == "SKIP_UNSUPPORTED":
        return "SKIPPED_UNSUPPORTED"
    return "PLANNED"


def action_step_to_log_record(
    step: ActionStep,
    *,
    client_id: str,
    tax_year: int,
    mode: str,
    status: str | None = None,
    error_message: str | None = None,
    timestamp: datetime | None = None,
) -> EntryLogRecord:
    """Convert an action step into a masked log record."""
    return EntryLogRecord(
        timestamp=timestamp or datetime.now(tz=UTC),
        client_id=client_id,
        tax_year=tax_year,
        mode=mode,
        screen=step.screen,
        field=step.field,
        source_sheet=step.source_sheet,
        source_cell=step.source_cell,
        masked_value=step.masked_value,
        action=step.action,
        status=(status or _default_status_for_action(step.action)),  # type: ignore[arg-type]
        error_message=error_message,
    )


def write_entry_log_csv(records: list[EntryLogRecord], path: str | Path) -> None:
    """Write masked entry log records to CSV."""
    output = Path(path)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(_ENTRY_HEADERS)
        for rec in records:
            writer.writerow(
                [
                    rec.timestamp.isoformat(),
                    rec.client_id,
                    rec.tax_year,
                    rec.mode,
                    rec.screen,
                    rec.field,
                    rec.source_sheet or "",
                    rec.source_cell or "",
                    rec.masked_value,
                    rec.action,
                    rec.status,
                    rec.error_message or "",
                ]
            )


def write_entry_log_xlsx(records: list[EntryLogRecord], path: str | Path) -> None:
    """Write masked entry log records to XLSX."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Entry Log"
    ws.append(_ENTRY_HEADERS)
    for rec in records:
        ws.append(
            [
                rec.timestamp.isoformat(),
                rec.client_id,
                rec.tax_year,
                rec.mode,
                rec.screen,
                rec.field,
                rec.source_sheet or "",
                rec.source_cell or "",
                rec.masked_value,
                rec.action,
                rec.status,
                rec.error_message or "",
            ]
        )
    wb.save(Path(path))


def write_validation_report_xlsx(issues: list[ValidationIssue], path: str | Path) -> None:
    """Write validation issues to an XLSX report without raw sensitive values."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Validation Report"
    ws.append(_VALIDATION_HEADERS)
    for issue in issues:
        ws.append(
            [
                issue.severity,
                issue.client_id,
                issue.field,
                issue.message,
                issue.source_sheet or "",
                issue.source_cell or "",
            ]
        )
    wb.save(Path(path))
