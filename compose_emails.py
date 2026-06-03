#!/usr/bin/env python3
"""Compose review-ready email drafts (.eml) for each client, with attachments.

Fourth tool in the suite. For every client in the clients data file that has an
email address, this builds a standard .eml message (subject + body rendered from
an editable template, plus that client's generated documents and any signed PDFs
attached) and writes it to Email_Drafts/. You open each .eml in your mail app,
review it, and send it yourself.

Nothing is sent automatically and no credentials are stored. Because tax
documents contain PII, a human reviewing each draft before sending is the point;
for highly sensitive delivery prefer a secure portal (such as Encyro) over email.
"""

from __future__ import annotations

import mimetypes
from email.message import EmailMessage
from pathlib import Path

import generate_documents
import sort_tax_docs

EMAIL_DRAFTS_FOLDER_NAME = "Email_Drafts"
EMAIL_TEMPLATE_FILENAME = "email_template.txt"
DEFAULT_EMAIL_TEMPLATE = (
    "Subject: Your {{tax_year}} Tax Documents from {{firm_name}}\n\n"
    "Dear {{client_name}},\n\n"
    "Please find your {{tax_year}} tax documents attached.\n\n"
    "Sincerely,\n{{preparer_name}}\n{{firm_name}}\n"
)
# Output folders whose files (matched by client slug) are attached to the email.
ATTACHMENT_SOURCE_FOLDERS = (
    generate_documents.GENERATED_FOLDER_NAME,
    "Signed_Documents",
)


def load_email_template(input_folder: Path) -> str:
    """Load the email template, preferring an override in the input folder."""

    directory = generate_documents.template_dir(input_folder)
    candidate = directory / EMAIL_TEMPLATE_FILENAME
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return DEFAULT_EMAIL_TEMPLATE


def split_subject_and_body(rendered: str) -> tuple[str, str]:
    """Split a rendered template into (subject, body).

    If the first non-empty line starts with 'Subject:', it becomes the subject and
    the remainder is the body; otherwise a generic subject is used.
    """

    lines = rendered.splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body = "\n".join(lines[index + 1 :]).strip("\n")
            return subject, body
        break
    return "Your Tax Documents", rendered.strip("\n")


def client_attachments(
    input_folder: Path, output_folder: Path, client: dict, slug: str, all_slugs=()
) -> list[Path]:
    """Collect attachment paths for a client: generated/signed files plus extras.

    Files belonging to a longer client slug (e.g. Jo_Sample_Jr when this client is
    Jo_Sample) are excluded so one client's documents never attach to another's email.
    """

    longer = generate_documents.longer_slugs(slug, all_slugs)
    attachments: list[Path] = []
    for folder_name in ATTACHMENT_SOURCE_FOLDERS:
        folder = output_folder / folder_name
        if folder.is_dir():
            matches = sorted(folder.glob(f"{slug}_*")) + sorted(folder.glob(f"Signed_{slug}_*"))
            attachments.extend(
                p for p in matches if not generate_documents.file_belongs_to_other_client(p.name, longer)
            )

    for extra in client.get("attachments", []) or []:
        path = (input_folder / str(extra)).expanduser()
        if path.is_file():
            attachments.append(path)

    # De-duplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in attachments:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def build_message(client: dict, subject: str, body: str, attachments: list[Path]) -> EmailMessage:
    """Build an EmailMessage with body and file attachments."""

    message = EmailMessage()
    message["To"] = str(client.get("email", ""))
    sender = client.get("firm_email") or client.get("from_email")
    if sender:
        message["From"] = str(sender)
    message["Subject"] = subject
    message.set_content(body)

    for path in attachments:
        guessed, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (guessed.split("/", 1) if guessed else ("application", "octet-stream"))
        message.add_attachment(
            path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name
        )
    return message


def run_email_drafts(input_folder, status_callback=None) -> dict:
    """Write one .eml draft per client that has an email address."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "email",
        "output_folder": output_folder,
        "drafts_folder": None,
        "drafts": [],
        "draft_count": 0,
        "skipped_no_email": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; no email drafts created."}

    clients = generate_documents.load_clients(data_file)
    template_text = load_email_template(input_folder)
    firm = generate_documents.load_firm_settings(input_folder)
    all_slugs = [generate_documents.client_slug(c, i) for i, c in enumerate(clients, start=1)]
    drafts_folder = output_folder / EMAIL_DRAFTS_FOLDER_NAME
    drafts_folder.mkdir(exist_ok=True)

    drafts: list[Path] = []
    warnings: list[str] = []
    skipped = 0
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if not client.get("email"):
            skipped += 1
            warnings.append(f"{slug}: no email address; skipped.")
            continue
        if status_callback:
            status_callback(f"Composing email for {slug} ({index} of {len(clients)})")

        context = generate_documents.augment_context(client, firm)
        rendered = generate_documents.render_template(template_text, context, escape=False)
        subject, body = split_subject_and_body(rendered)
        attachments = client_attachments(input_folder, output_folder, client, slug, all_slugs)
        if not attachments:
            warnings.append(f"{slug}: no attachments found (run Generate/Sign first?).")

        message = build_message(context, subject, body, attachments)
        draft_path = sort_tax_docs.unique_destination_path(drafts_folder, f"{slug}.eml")
        draft_path.write_bytes(bytes(message))
        drafts.append(draft_path)

    return {
        **base_result,
        "drafts_folder": drafts_folder,
        "drafts": drafts,
        "draft_count": len(drafts),
        "skipped_no_email": skipped,
        "warnings": warnings,
        "summary": (
            f"Created {len(drafts)} email draft(s)"
            + (f"; skipped {skipped} client(s) with no email." if skipped else ".")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compose review-ready .eml email drafts with attachments for each client."
    )
    parser.add_argument("input_folder", help="Folder containing clients.json or clients.csv.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_email_drafts(folder, status_callback=print)
    print(result["summary"])
    if result["drafts_folder"]:
        print(f"Email drafts folder: {result['drafts_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
