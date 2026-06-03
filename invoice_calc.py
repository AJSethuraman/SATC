#!/usr/bin/env python3
"""Compute client invoice line items from an editable fee schedule.

Third new module. For each client it builds invoice ``line_items`` from a base
preparation fee, the documents they reported at intake, and any explicit
``services`` on the record, then writes those line items back into ``clients.json``
so the Generate Documents tool renders a finished invoice. It also writes an
``Invoices/fee_worksheet.csv`` you can review.

The fee schedule is *dynamic*: ``fee_schedule.json`` is created in the folder on
first run, so prices and descriptions are yours to edit. Standard-library only.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import generate_documents
import sort_tax_docs

INVOICE_FOLDER_NAME = "Invoices"
FEE_SCHEDULE_FILENAME = "fee_schedule.json"
WORKSHEET_FILENAME = "fee_worksheet.csv"
BASE_FEE_KEY = "base_preparation"

# service/document key -> {description, price}. Document keys match intake labels so
# a client's expected_documents price automatically. Prices are placeholders to edit.
DEFAULT_FEE_SCHEDULE: dict[str, dict] = {
    BASE_FEE_KEY: {"description": "Form 1040 preparation", "price": 200.00},
    "W-2": {"description": "W-2 entry", "price": 15.00},
    "1099-NEC": {"description": "1099-NEC / Schedule C income", "price": 75.00},
    "1099-MISC": {"description": "1099-MISC income", "price": 35.00},
    "1099-INT": {"description": "Interest income (1099-INT)", "price": 15.00},
    "1099-DIV": {"description": "Dividend income (1099-DIV)", "price": 20.00},
    "1099-R": {"description": "Retirement income (1099-R)", "price": 25.00},
    "1098 (Mortgage)": {"description": "Mortgage interest (Schedule A)", "price": 40.00},
    "1098-T": {"description": "Education credits (1098-T)", "price": 30.00},
    "SSA-1099": {"description": "Social Security income (SSA-1099)", "price": 15.00},
    "K-1": {"description": "Schedule K-1", "price": 90.00},
    "1099-G": {"description": "Government payments (1099-G)", "price": 15.00},
    "1099-K": {"description": "Payment card income (1099-K)", "price": 50.00},
    "state_return": {"description": "State return", "price": 75.00},
    "schedule_c": {"description": "Schedule C (self-employment)", "price": 150.00},
    "schedule_e": {"description": "Schedule E (rental property)", "price": 125.00},
    "itemized_deductions": {"description": "Itemized deductions (Schedule A)", "price": 60.00},
    "amended_return": {"description": "Amended return", "price": 200.00},
    "extension_filing": {"description": "Extension filing", "price": 50.00},
}


def load_fee_schedule(input_folder: Path) -> tuple[dict, Path]:
    """Return (schedule, path), creating an editable default file if none exists."""

    path = input_folder / FEE_SCHEDULE_FILENAME
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data:
            return data, path
    path.write_text(json.dumps(DEFAULT_FEE_SCHEDULE, indent=2), encoding="utf-8")
    return DEFAULT_FEE_SCHEDULE, path


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _service_entries(client: dict) -> list[tuple[str, int, dict | None]]:
    """Normalize a client's explicit services into (key, quantity, inline) tuples."""

    entries: list[tuple[str, int, dict | None]] = []
    for service in client.get("services", []) or []:
        if isinstance(service, str):
            entries.append((service, 1, None))
        elif isinstance(service, dict):
            key = service.get("service") or service.get("key") or ""
            quantity = int(service.get("quantity", 1) or 1)
            inline = service if ("description" in service and "price" in service) else None
            entries.append((key, quantity, inline))
    return entries


def compute_line_items(client: dict, schedule: dict) -> tuple[list[dict], float, list[str]]:
    """Build (line_items, total, warnings) for one client from the fee schedule."""

    line_items: list[dict] = []
    warnings: list[str] = []

    def add(description: str, price: float, quantity: int = 1) -> None:
        amount = price * quantity
        label = description if quantity == 1 else f"{description} (x{quantity})"
        line_items.append({"description": label, "amount": _money(amount)})

    if BASE_FEE_KEY in schedule:
        base = schedule[BASE_FEE_KEY]
        add(base.get("description", "Tax preparation"), float(base.get("price", 0)))

    expected = client.get("expected_documents") or []
    if isinstance(expected, str):
        expected = [expected]
    for label in expected:
        fee = schedule.get(label)
        if fee:
            add(fee.get("description", label), float(fee.get("price", 0)))

    for key, quantity, inline in _service_entries(client):
        if inline is not None:
            add(str(inline["description"]), float(inline["price"]), quantity)
        elif key in schedule:
            fee = schedule[key]
            add(fee.get("description", key), float(fee.get("price", 0)), quantity)
        elif key:
            warnings.append(f"service '{key}' is not in the fee schedule; skipped.")

    total = sum(float(item["amount"].replace(",", "")) for item in line_items)
    return line_items, total, warnings


def run_invoice_calc(input_folder, status_callback=None) -> dict:
    """Compute line items for every client, update clients.json, write a worksheet."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "invoice",
        "output_folder": output_folder,
        "invoice_folder": None,
        "worksheet_path": None,
        "client_count": 0,
        "invoiced_count": 0,
        "grand_total": "0.00",
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; no invoices computed."}

    clients = generate_documents.load_clients(data_file)
    schedule, _ = load_fee_schedule(input_folder)
    invoice_folder = output_folder / INVOICE_FOLDER_NAME
    invoice_folder.mkdir(exist_ok=True)

    warnings: list[str] = []
    worksheet_rows: list[dict] = []
    invoiced = 0
    grand_total = 0.0
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"Calculating invoice for {slug} ({index} of {len(clients)})")
        line_items, total, client_warnings = compute_line_items(client, schedule)
        warnings.extend(f"{slug}: {w}" for w in client_warnings)
        if not line_items:
            warnings.append(f"{slug}: nothing to bill (no base fee, expected documents, or services).")
            continue
        client["line_items"] = line_items
        client["total"] = _money(total)
        invoiced += 1
        grand_total += total
        for item in line_items:
            worksheet_rows.append({"client": slug, "description": item["description"], "amount": item["amount"]})
        worksheet_rows.append({"client": slug, "description": "TOTAL", "amount": _money(total)})

    # Persist computed line items so Generate Documents can render the invoices.
    clients_json = input_folder / "clients.json"
    clients_json.write_text(json.dumps(clients, indent=2), encoding="utf-8")

    worksheet_path = invoice_folder / WORKSHEET_FILENAME
    with worksheet_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["client", "description", "amount"])
        writer.writeheader()
        writer.writerows(worksheet_rows)

    return {
        **base_result,
        "invoice_folder": invoice_folder,
        "worksheet_path": worksheet_path,
        "client_count": len(clients),
        "invoiced_count": invoiced,
        "grand_total": _money(grand_total),
        "warnings": warnings,
        "summary": (
            f"Computed invoices for {invoiced} of {len(clients)} client(s); "
            f"total billed {_money(grand_total)}."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute client invoice line items from an editable fee schedule."
    )
    parser.add_argument("input_folder", help="Folder containing clients.json or clients.csv.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_invoice_calc(folder, status_callback=print)
    print(result["summary"])
    if result["worksheet_path"]:
        print(f"Fee worksheet: {result['worksheet_path']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
