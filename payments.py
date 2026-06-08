#!/usr/bin/env python3
"""Track invoice payments and produce an accounts-receivable aging report.

Reads clients.json (after Calculate Invoices has set each client's ``total``) and
each client's payment fields -- ``amount_paid`` (or ``paid: true``) and an
``invoice_date`` -- to compute the outstanding balance and how long it has been
outstanding. Writes Payments/ar_aging.csv with each balance bucketed by age
(0-30 / 31-60 / 61-90 / 90+ days). Standard-library only.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import core
import generate_documents
import sort_tax_docs

PAYMENTS_FOLDER_NAME = "Payments"
AGING_FILENAME = "ar_aging.csv"
AGING_BUCKETS = ("0-30", "31-60", "61-90", "90+")

STATUS_PAID, STATUS_PARTIAL, STATUS_UNPAID = "Paid", "Partial", "Unpaid"


_money = core.format_money


def _is_truthy(value) -> bool:
    """Interpret a paid flag robustly (handles JSON bools and CSV strings)."""

    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "y", "1", "paid")
    return bool(value)


def _amount_paid(client: dict, total: float) -> float:
    if "amount_paid" in client:
        return core.parse_money(client.get("amount_paid"))
    return total if _is_truthy(client.get("paid")) else 0.0


def _age_days(client: dict, today: date) -> int | None:
    raw = client.get("invoice_date") or client.get("generated_date")
    if not raw:
        return None
    try:
        invoiced = date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
    return max((today - invoiced).days, 0)


def aging_bucket(days: int | None) -> str:
    if days is None:
        return ""  # undated: don't claim it is current (0-30)
    if days <= 30:
        return "0-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


def evaluate_client(client: dict, today: date | None = None) -> dict:
    """Compute a single AR row for one client."""

    today = today or date.today()
    total = core.parse_money(client.get("total"))
    paid = min(_amount_paid(client, total), total) if total else _amount_paid(client, total)
    balance = round(total - paid, 2)
    if balance <= 0:
        status = STATUS_PAID  # nothing outstanding (covers zero-total / fully paid)
    elif paid > 0:
        status = STATUS_PARTIAL
    else:
        status = STATUS_UNPAID
    days = _age_days(client, today)
    return {
        "total": total,
        "paid": paid,
        "balance": max(balance, 0.0),
        "status": status,
        "days": days,
        "bucket": aging_bucket(days) if balance > 0 else "",
    }


def run_payments(input_folder, status_callback=None) -> dict:
    """Build the AR aging report from clients.json."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "payments",
        "output_folder": output_folder,
        "payments_folder": None,
        "report_path": None,
        "total_billed": "0.00",
        "total_collected": "0.00",
        "total_outstanding": "0.00",
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; no AR report built."}

    clients = generate_documents.load_clients(data_file)
    today = date.today()
    rows: list[dict] = []
    billed = collected = outstanding = 0.0
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"AR: {slug} ({index} of {len(clients)})")
        info = evaluate_client(client, today)
        billed += info["total"]
        collected += info["paid"]
        outstanding += info["balance"]
        rows.append({
            "client": slug,
            "total": _money(info["total"]),
            "paid": _money(info["paid"]),
            "balance": _money(info["balance"]),
            "status": info["status"],
            "days_outstanding": "" if info["days"] is None else info["days"],
            "bucket": info["bucket"],
        })

    payments_folder = output_folder / PAYMENTS_FOLDER_NAME
    payments_folder.mkdir(exist_ok=True)
    report_path = payments_folder / AGING_FILENAME
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["client", "total", "paid", "balance", "status", "days_outstanding", "bucket"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return {
        **base_result,
        "payments_folder": payments_folder,
        "report_path": report_path,
        "total_billed": _money(billed),
        "total_collected": _money(collected),
        "total_outstanding": _money(outstanding),
        "summary": (
            f"AR: {_money(outstanding)} outstanding of {_money(billed)} billed "
            f"across {len(rows)} client(s)."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build an accounts-receivable aging report.")
    parser.add_argument("input_folder", help="Folder containing clients.json.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_payments(folder, status_callback=print)
    print(result["summary"])
    if result["report_path"]:
        print(f"AR report: {result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
