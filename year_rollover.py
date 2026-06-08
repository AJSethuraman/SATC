#!/usr/bin/env python3
"""Roll clients forward into a fresh tax year.

A start-of-season leaf tool: it creates a new ``<year>/`` subfolder containing a
clients.json where every client's static details carry forward (name, contact,
filing status, dependents, expected documents, services, and any custom fields)
while the prior year's per-year status is wiped (invoice totals, payments, and the
engagement/8879/filing flags), and ``tax_year`` is bumped. Your configuration
(firm.json, fee schedule, intake fields, checklist map, templates) is copied in so
the new year starts with the same settings.

It is non-destructive: the current folder is untouched, and nothing is archived
(run Records Retention separately if you want last year zipped). Built as a pure
``roll_forward`` transform plus a thin run_rollover I/O layer. Standard library only.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import core
import fee_workbook
import generate_documents
import invoice_calc
import sort_tax_docs

# Per-year fields cleared on rollover; everything else carries forward.
RESET_FIELDS = frozenset({
    "line_items", "subtotal", "discount", "discount_lines", "total", "express_applied",
    "amount_paid", "paid", "invoice_date", "generated_date",
    "returns", "efiled_returns", "return_filed",
    "engagement_letter_signed", "form_8879_signed",
})
SHARED_CONFIG_FILES = (
    generate_documents.FIRM_SETTINGS_FILENAME,
    "fee_schedule.json",
    "intake_fields.json",
    "checklist_map.json",
)
SHARED_CONFIG_DIRS = (generate_documents.TEMPLATE_DIR_NAME,)


def roll_forward(client: dict, new_year: str) -> dict:
    """Carry a client into the new year: keep static fields, drop per-year status."""

    carried = {key: value for key, value in client.items() if key not in RESET_FIELDS}
    carried["tax_year"] = str(new_year)
    return carried


def next_year(clients: list[dict], explicit=None) -> str:
    """The target year: explicit if given, else max client tax_year + 1, else this year."""

    if explicit:
        return str(explicit)
    years: list[int] = []
    for client in clients:
        try:
            years.append(int(str(client.get("tax_year", "")).strip()[:4]))
        except (ValueError, TypeError):
            continue
    return str((max(years) + 1) if years else date.today().year)


def _copy_config(source_folder: Path, target_folder: Path) -> None:
    for name in SHARED_CONFIG_FILES:
        src = source_folder / name
        if src.is_file() and not (target_folder / name).exists():
            shutil.copy2(src, target_folder / name)
    for name in SHARED_CONFIG_DIRS:
        src = source_folder / name
        if src.is_dir() and not (target_folder / name).exists():
            shutil.copytree(src, target_folder / name)


def run_rollover(input_folder, new_year=None, status_callback=None) -> dict:
    """Create a next-year folder with clients carried forward and config copied."""

    input_folder = Path(input_folder)

    base_result = {
        "tool": "rollover",
        "target_folder": None,
        "new_year": None,
        "client_count": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; nothing to roll forward."}

    clients = generate_documents.load_clients(data_file)
    year = next_year(clients, new_year)
    if status_callback:
        status_callback(f"Rolling {len(clients)} client(s) forward to {year}")

    target_folder = input_folder / year
    target_folder.mkdir(parents=True, exist_ok=True)
    _copy_config(input_folder, target_folder)

    # If a year-by-year fee workbook has a sheet for the new year, use that year's
    # prices for the new folder instead of copying last year's fee_schedule.json.
    workbook_applied = False
    workbook_schedule = fee_workbook.schedule_for_year(
        input_folder / fee_workbook.WORKBOOK_FILENAME, year
    )
    if workbook_schedule:
        (target_folder / invoice_calc.FEE_SCHEDULE_FILENAME).write_text(
            json.dumps(workbook_schedule, indent=2), encoding="utf-8"
        )
        workbook_applied = True

    carried = [roll_forward(client, year) for client in clients]
    clients_file = target_folder / "clients.json"
    existing: list[dict] = []
    if clients_file.exists():
        try:
            loaded = json.loads(clients_file.read_text(encoding="utf-8"))
            existing = loaded if isinstance(loaded, list) else [loaded]
        except json.JSONDecodeError:
            existing = []
    merged, added, skipped = core.append_new_clients(existing, carried)
    clients_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    warnings = [f"{skipped} client(s) already present in {year}/clients.json."] if skipped else []
    return {
        **base_result,
        "target_folder": target_folder,
        "new_year": year,
        "client_count": added,
        "workbook_applied": workbook_applied,
        "warnings": warnings,
        "summary": (
            f"Rolled {added} client(s) forward to {year}"
            + (f"; applied {year} fees from the workbook" if workbook_applied else "")
            + (f" ({skipped} already present)." if skipped else ".")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Roll clients forward into a new tax year.")
    parser.add_argument("input_folder", help="Current year's folder (with clients.json).")
    parser.add_argument("--year", default="", help="Target tax year (default: latest + 1).")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_rollover(folder, new_year=args.year or None, status_callback=print)
    print(result["summary"])
    if result["target_folder"]:
        print(f"New year folder: {result['target_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
