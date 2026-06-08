#!/usr/bin/env python3
"""Turn a client's finished return into a plain-English summary email.

This is the client-facing companion to the return packet: it takes what was filed
(the returns, refund/balance, e-file status, fee, and pay link already on the client
record) and writes a short, friendly ``.eml`` the client can actually read -- not a
formal letter. As with the other email tools, nothing is sent: you open each draft,
glance, and send it yourself.

The wording is an editable template (``document_templates/summary_email_template.txt``).
Standard library only.
"""

from __future__ import annotations

from pathlib import Path

import compose_emails
import generate_documents
import sort_tax_docs

SUMMARY_FOLDER_NAME = "Summary_Emails"
TEMPLATE_FILENAME = "summary_email_template.txt"
DEFAULT_TEMPLATE = (
    "Subject: Your {{tax_year}} tax return summary\n\n"
    "Hi {{client_name}},\n\n"
    "Your {{tax_year}} tax returns are done. Here's the short version:\n\n"
    "{{#returns_display}}  - {{line}}\n{{/returns_display}}\n"
    "{{#all_efiled}}Everything was e-filed, so there is nothing for you to mail.\n{{/all_efiled}}"
    "{{#total}}Our fee for this year is ${{total}}.\n{{/total}}"
    "{{#pay_link}}You can pay online here: {{pay_link}}\n{{/pay_link}}\n"
    "Thank you,\n{{preparer_name}}\n{{firm_name}}\n"
)


def load_template(input_folder: Path) -> str:
    directory = generate_documents.template_dir(input_folder)
    candidate = directory / TEMPLATE_FILENAME
    return candidate.read_text(encoding="utf-8") if candidate.exists() else DEFAULT_TEMPLATE


def summary_context(client: dict) -> dict:
    """Build the rendering context: preformatted return lines + an all-e-filed flag."""

    returns = client.get("returns") or []
    lines = []
    for entry in returns:
        if not isinstance(entry, dict):
            continue
        text = f"{entry.get('return_type', 'Return')}: {entry.get('refund_or_balance', '')}".strip().rstrip(":")
        method = entry.get("transaction_method")
        if method:
            text += f" ({method})"
        lines.append({"line": text})
    context = {
        "returns_display": lines,
        "all_efiled": bool(client.get("efiled_returns")),
    }
    return context


def has_summary_content(client: dict) -> bool:
    """A summary email is worth drafting only if there is something to report."""

    return bool(client.get("returns") or client.get("total"))


def run_summary_emails(input_folder, status_callback=None) -> dict:
    """Draft a plain-English summary .eml for each client that has a return summary."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "summary",
        "output_folder": output_folder,
        "summary_folder": None,
        "emails": [],
        "email_count": 0,
        "skipped_no_email": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; no summary emails created."}

    clients = generate_documents.load_clients(data_file)
    template_text = load_template(input_folder)
    firm = generate_documents.load_firm_settings(input_folder)
    summary_folder = output_folder / SUMMARY_FOLDER_NAME
    summary_folder.mkdir(exist_ok=True)

    emails: list[Path] = []
    warnings: list[str] = []
    skipped_no_email = 0
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if not has_summary_content(client):
            continue
        if not client.get("email"):
            skipped_no_email += 1
            warnings.append(f"{slug}: return summary ready but no email; skipped.")
            continue
        if status_callback:
            status_callback(f"Drafting summary email for {slug} ({index} of {len(clients)})")

        context = generate_documents.augment_context(client, firm)
        context.update(summary_context(client))
        rendered = generate_documents.render_template(template_text, context, escape=False)
        subject, body = compose_emails.split_subject_and_body(rendered)
        message = compose_emails.build_message(context, subject, body, [])
        path = sort_tax_docs.unique_destination_path(summary_folder, f"{slug}_summary.eml")
        path.write_bytes(bytes(message))
        emails.append(path)

    return {
        **base_result,
        "summary_folder": summary_folder,
        "emails": emails,
        "email_count": len(emails),
        "skipped_no_email": skipped_no_email,
        "warnings": warnings,
        "summary": (
            f"Drafted {len(emails)} client summary email(s)"
            + (f"; {skipped_no_email} had no email." if skipped_no_email else ".")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Draft plain-English client summary emails from filed returns.")
    parser.add_argument("input_folder", help="Folder containing clients.json or clients.csv.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_summary_emails(folder, status_callback=print)
    print(result["summary"])
    if result["summary_folder"]:
        print(f"Summary emails: {result['summary_folder']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
