#!/usr/bin/env python3
"""Draft reminder emails for clients with outstanding items.

Combines the two signature trackers and the document checklist: for each client it
gathers what is still outstanding -- a signed engagement letter, a signed Form 8879,
and any missing documents -- and, when anything is outstanding and the client has an
email, writes a review-ready reminder ``.eml`` to ``Reminders/``. As with the email
tool, nothing is sent: you open each draft, review it, and send it yourself.

The reminder wording is an editable template (``document_templates/reminder_template.txt``).
Standard-library only.
"""

from __future__ import annotations

from pathlib import Path

import checklist
import compose_emails
import generate_documents
import sort_tax_docs
import status_tracker

REMINDERS_FOLDER_NAME = "Reminders"
REMINDER_TEMPLATE_FILENAME = "reminder_template.txt"
DEFAULT_REMINDER_TEMPLATE = (
    "Subject: Reminder: items still needed for your {{tax_year}} tax return\n\n"
    "Dear {{client_name}},\n\n"
    "To finish your {{tax_year}} tax return, we are still waiting on the following:\n\n"
    "{{#outstanding_items}}  - {{item}}\n{{/outstanding_items}}\n"
    "Please send these at your earliest convenience.\n\n"
    "Thank you,\n{{preparer_name}}\n{{firm_name}}\n"
)


def load_reminder_template(input_folder: Path) -> str:
    directory = generate_documents.template_dir(input_folder)
    candidate = directory / REMINDER_TEMPLATE_FILENAME
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return DEFAULT_REMINDER_TEMPLATE


def outstanding_for_client(client: dict, slug: str, search_files, doc_map, received) -> list[str]:
    """Human-readable list of everything still outstanding for one client."""

    items: list[str] = []
    engagement, _ = status_tracker.evaluate(client, slug, status_tracker.ENGAGEMENT_TRACKER, search_files)
    if engagement == status_tracker.STATUS_OUTSTANDING:
        items.append("a signed engagement letter")
    form_8879, _ = status_tracker.evaluate(client, slug, status_tracker.FORM_8879_TRACKER, search_files)
    if form_8879 == status_tracker.STATUS_OUTSTANDING:
        items.append("a signed Form 8879 (e-file authorization)")

    rows, _ = checklist.evaluate_client(client, doc_map, received)
    for row in rows:
        if row["status"] == checklist.STATUS_MISSING:
            items.append(f"your {row['document']}")
    return items


def run_reminders(input_folder, status_callback=None) -> dict:
    """Build a reminder .eml for each client that has outstanding items and an email."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "reminders",
        "output_folder": output_folder,
        "reminders_folder": None,
        "reminders": [],
        "reminder_count": 0,
        "skipped_complete": 0,
        "skipped_no_email": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; no reminders created."}

    clients = generate_documents.load_clients(data_file)
    search_files = status_tracker.gather_search_files(input_folder, output_folder)
    doc_map, _ = checklist.load_doc_map(input_folder)
    received = checklist.received_categories(output_folder)
    template_text = load_reminder_template(input_folder)
    firm = generate_documents.load_firm_settings(input_folder)
    reminders_folder = output_folder / REMINDERS_FOLDER_NAME
    reminders_folder.mkdir(exist_ok=True)

    reminders: list[Path] = []
    warnings: list[str] = []
    skipped_complete = skipped_no_email = 0
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"Checking outstanding items for {slug} ({index} of {len(clients)})")
        items = outstanding_for_client(client, slug, search_files, doc_map, received)
        if not items:
            skipped_complete += 1
            continue
        if not client.get("email"):
            skipped_no_email += 1
            warnings.append(f"{slug}: outstanding items but no email; skipped.")
            continue

        context = generate_documents.augment_context(client, firm)
        context["outstanding_items"] = [{"item": item} for item in items]
        rendered = generate_documents.render_template(template_text, context, escape=False)
        subject, body = compose_emails.split_subject_and_body(rendered)
        message = compose_emails.build_message(context, subject, body, [])
        path = sort_tax_docs.unique_destination_path(reminders_folder, f"{slug}_reminder.eml")
        path.write_bytes(bytes(message))
        reminders.append(path)

    return {
        **base_result,
        "reminders_folder": reminders_folder,
        "reminders": reminders,
        "reminder_count": len(reminders),
        "skipped_complete": skipped_complete,
        "skipped_no_email": skipped_no_email,
        "warnings": warnings,
        "summary": (
            f"Drafted {len(reminders)} reminder(s); {skipped_complete} client(s) had nothing outstanding"
            + (f", {skipped_no_email} had no email." if skipped_no_email else ".")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Draft reminder emails for clients with outstanding items."
    )
    parser.add_argument("input_folder", help="Folder containing clients.json and tool output.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_reminders(folder, status_callback=print)
    print(result["summary"])
    if result["reminders_folder"]:
        print(f"Reminders folder: {result['reminders_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
