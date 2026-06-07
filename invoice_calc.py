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

import core
import generate_documents
import sort_tax_docs

INVOICE_FOLDER_NAME = "Invoices"
FEE_SCHEDULE_FILENAME = "fee_schedule.json"
WORKSHEET_FILENAME = "fee_worksheet.csv"
BASE_FEE_KEY = "base_1040"
EXPRESS_KEY = "express_discount"

# Form/schedule key -> {description, price, [additional]}. "price" is the fee for the
# first of that form; "additional" (optional, defaults to price) is the fee for each
# extra copy (e.g. a second state). Prices mirror a typical individual fee schedule
# and are yours to edit in fee_schedule.json.
DEFAULT_FEE_SCHEDULE: dict[str, dict] = {
    BASE_FEE_KEY: {"description": "Form 1040 - Individual Return", "price": 170.0, "additional": 170.0},
    "schedule_a": {"description": "Schedule A - Itemized Deductions", "price": 30.0},
    "schedule_b": {"description": "Schedule B - Interest & Dividends", "price": 5.0},
    "schedule_c": {"description": "Schedule C - Business Income", "price": 200.0},
    "schedule_d": {"description": "Schedule D - Capital Gains/Losses", "price": 50.0},
    "schedule_e": {"description": "Schedule E - Rental/Supplemental Income", "price": 130.0},
    "schedule_se": {"description": "Schedule SE - Self-Employment Tax", "price": 20.0},
    "schedule_eic": {"description": "Schedule EIC - Earned Income Credit", "price": 100.0},
    "education_8863": {"description": "Form 8863 - Education Credits", "price": 30.0},
    "childcare_2441": {"description": "Form 2441 - Child & Dependent Care", "price": 30.0},
    "hsa_8889": {"description": "Form 8889 - Health Savings Account", "price": 10.0},
    "additional_ctc_8812": {"description": "Form 8812 - Additional Child Tax Credit", "price": 25.0},
    "energy_5695": {"description": "Form 5695 - Residential Energy Credits", "price": 20.0},
    "amended_1040x": {"description": "Form 1040-X - Amended Return", "price": 170.0},
    "state_return": {"description": "State Return", "price": 30.0, "additional": 30.0},
    "s_corp_1120s": {"description": "Form 1120-S - S Corporation", "price": 800.0},
    "partnership_1065": {"description": "Form 1065 - Partnership", "price": 800.0},
    "corporation_1120": {"description": "Form 1120 - Corporation", "price": 800.0},
    "estate_1041": {"description": "Form 1041 - Estate / Trust", "price": 400.0},
    # Express discount applied to simple filers (set amount, or "percent": 15). Remove
    # this entry to turn the discount off.
    EXPRESS_KEY: {"description": "Express discount - simple filer", "amount": -40.0},
}

# Income documents -> the schedules/forms they typically require, so an invoice can be
# computed straight from a client's expected_documents (W-2 needs no extra schedule).
DOC_TO_FORMS: dict[str, list[str]] = {
    "1099-INT": ["schedule_b"],
    "1099-DIV": ["schedule_b"],
    "1099-NEC": ["schedule_c", "schedule_se"],
    "1099-MISC": ["schedule_c", "schedule_se"],
    "K-1": ["schedule_e"],
    "1099-B": ["schedule_d"],
    "1098 (Mortgage)": ["schedule_a"],
    "1098-T": ["education_8863"],
}

# A "simple filer" (express-eligible): only these income types and no complex services.
SIMPLE_DOCS = frozenset({"W-2", "1099-INT", "1099-DIV", "1099-R", "SSA-1099", "1099-G"})
SIMPLE_SERVICES = frozenset({"state_return"})


def load_fee_schedule(input_folder: Path) -> tuple[dict, Path]:
    """Return (schedule, path), creating an editable default file if none exists."""

    path = input_folder / FEE_SCHEDULE_FILENAME
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data:
            return data, path
    path.write_text(json.dumps(DEFAULT_FEE_SCHEDULE, indent=2), encoding="utf-8")
    return DEFAULT_FEE_SCHEDULE, path


_money = core.format_money


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


def _expected_documents(client: dict) -> list[str]:
    expected = client.get("expected_documents") or []
    return [expected] if isinstance(expected, str) else list(expected)


def is_simple_filer(client: dict) -> bool:
    """True when a client only has simple income and no complex services."""

    docs = set(_expected_documents(client))
    services = {key for key, _qty, inline in _service_entries(client) if inline is None and key}
    return docs <= SIMPLE_DOCS and services <= SIMPLE_SERVICES


def express_eligible(client: dict) -> bool:
    """Whether the express discount applies: explicit ``express`` flag, else auto-detected."""

    if "express" in client:
        return bool(client["express"])
    return is_simple_filer(client)


def compute_line_items(client: dict, schedule: dict) -> tuple[list[dict], float, float, float, list[str]]:
    """Build (line_items, subtotal, discount, total, warnings) for one client.

    Pricing is form/schedule driven: a base Form 1040, plus the schedules implied by
    the client's expected_documents, plus any explicit ``services`` (each a form key,
    or ``{"service": key, "quantity": n}``, or an inline ``{"description", "price"}``).
    Each form is priced as initial + (quantity - 1) x additional. A simple filer then
    receives the express discount.
    """

    line_items: list[dict] = []
    warnings: list[str] = []

    def add(description: str, price: float, quantity: int = 1, additional=None) -> None:
        per_extra = price if additional is None else float(additional)
        amount = price + (quantity - 1) * per_extra
        label = description if quantity == 1 else f"{description} (x{quantity})"
        line_items.append({"description": label, "amount": _money(amount)})

    if BASE_FEE_KEY in schedule:
        base = schedule[BASE_FEE_KEY]
        add(base.get("description", "Tax preparation"), float(base.get("price", 0)), 1, base.get("additional"))

    # Collect form keys (deduped, order-preserving) from documents and explicit services.
    order: list[str] = []
    quantities: dict[str, int] = {}
    inline_lines: list[tuple[dict, int]] = []

    def want_form(key: str, quantity: int = 1) -> None:
        if key not in quantities:
            order.append(key)
            quantities[key] = quantity
        else:
            quantities[key] = max(quantities[key], quantity)

    for label in _expected_documents(client):
        for key in DOC_TO_FORMS.get(label, []):
            want_form(key)
    for key, quantity, inline in _service_entries(client):
        if inline is not None:
            inline_lines.append((inline, quantity))
        elif key:
            want_form(key, quantity)

    for key in order:
        fee = schedule.get(key)
        if fee:
            add(fee.get("description", key), float(fee.get("price", 0)), quantities[key], fee.get("additional"))
        else:
            warnings.append(f"form '{key}' is not in the fee schedule; skipped.")
    for inline, quantity in inline_lines:
        add(str(inline["description"]), float(inline["price"]), quantity)

    subtotal = sum(core.parse_money(item["amount"]) for item in line_items)

    discount = 0.0
    if express_eligible(client) and EXPRESS_KEY in schedule:
        config = schedule[EXPRESS_KEY]
        if "percent" in config:
            discount = -round(subtotal * abs(float(config["percent"])) / 100.0, 2)
        else:
            discount = -abs(float(config.get("amount", 0)))

    total = round(subtotal + discount, 2)
    return line_items, subtotal, discount, total, warnings


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
        "express_count": 0,
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
    express_count = 0
    grand_total = 0.0
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"Calculating invoice for {slug} ({index} of {len(clients)})")
        line_items, subtotal, discount, total, client_warnings = compute_line_items(client, schedule)
        warnings.extend(f"{slug}: {w}" for w in client_warnings)
        if not line_items:
            warnings.append(f"{slug}: nothing to bill (no base fee or services).")
            continue
        client["line_items"] = line_items
        client["subtotal"] = _money(subtotal)
        client["discount"] = _money(discount) if discount else ""
        client["total"] = _money(total)
        client["express_applied"] = bool(discount)
        invoiced += 1
        express_count += 1 if discount else 0
        grand_total += total
        for item in line_items:
            worksheet_rows.append({"client": slug, "description": item["description"], "amount": item["amount"]})
        if discount:
            worksheet_rows.append({"client": slug, "description": "Express discount", "amount": _money(discount)})
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
        "express_count": express_count,
        "grand_total": _money(grand_total),
        "warnings": warnings,
        "summary": (
            f"Computed invoices for {invoiced} of {len(clients)} client(s); "
            f"total billed {_money(grand_total)}"
            + (f" ({express_count} express)." if express_count else ".")
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
