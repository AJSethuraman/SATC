#!/usr/bin/env python3
"""Build upload-ready Encyro packets for each client.

Sixth tool in the suite. Encyro has no public API, so this does the next best
thing: for every client it assembles an Encyro_Ready/<client>/ folder containing

  * each generated letter converted to PDF (Encyro e-sign takes PDFs/Office files),
  * any signed PDFs and extra attachments for that client,
  * a single merged <client>_packet.pdf to upload for an e-signature request, and
  * an UPLOAD_NOTES.txt with the recipient email and a signing checklist.

You then drag the packet (or individual files) into Encyro's web app / Outlook
add-in and place signature fields there. Everything here is local; nothing is
sent. Conversion keeps text selectable so signature anchors still work.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import generate_documents
import sort_tax_docs

ENCYRO_FOLDER_NAME = "Encyro_Ready"
PACKET_SUFFIX = "_packet.pdf"
NOTES_FILENAME = "UPLOAD_NOTES.txt"
# File types Encyro accepts directly (Office files are auto-converted on upload).
COPYABLE_SUFFIXES = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".png", ".jpg", ".jpeg"}
PAGE_MARGIN = (54, 54, -54, -54)


def html_to_pdf(html_text: str, dest_path: Path) -> Path:
    """Render an HTML string to a PDF using PyMuPDF (text stays selectable)."""

    import fitz  # PyMuPDF

    story = fitz.Story(html=html_text)
    writer = fitz.DocumentWriter(str(dest_path))
    rect = fitz.paper_rect("letter")
    area = rect + PAGE_MARGIN
    more = 1
    while more:
        device = writer.begin_page(rect)
        more, _ = story.place(area)
        story.draw(device)
        writer.end_page()
    writer.close()
    return dest_path


def merge_pdfs(pdf_paths: list[Path], dest_path: Path) -> Path | None:
    """Concatenate PDFs into one packet. Returns the packet path, or None if empty."""

    import fitz  # PyMuPDF

    if not pdf_paths:
        return None
    merged = fitz.open()
    try:
        for path in pdf_paths:
            with fitz.open(path) as source:
                merged.insert_pdf(source)
        merged.save(str(dest_path))
    finally:
        merged.close()
    return dest_path


def write_upload_notes(notes_path: Path, client: dict, files: list[Path], packet: Path | None) -> None:
    """Write a short checklist the preparer follows when uploading to Encyro."""

    recipient = client.get("email") or "(no email on file)"
    name = client.get("client_name") or client.get("name") or notes_path.parent.name
    lines = [
        f"Encyro upload notes for {name}",
        "=" * 40,
        f"Recipient email: {recipient}",
        "",
        "Upload for e-signature:",
        f"  - {packet.name}" if packet else "  - (no PDFs to merge)",
        "",
        "Files in this folder:",
    ]
    lines += [f"  - {path.name}" for path in files] or ["  - (none)"]
    lines += [
        "",
        "In Encyro: upload the packet, add signature/date fields where needed,",
        "and configure KBA, signing order, and reminders per your e-sign options.",
    ]
    notes_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _matching_files(folder: Path, slug: str) -> list[Path]:
    if not folder.is_dir():
        return []
    found = set(folder.glob(f"{slug}_*")) | set(folder.glob(f"Signed_{slug}_*"))
    return sorted(found)


def run_encyro_export(input_folder, status_callback=None) -> dict:
    """Assemble an Encyro_Ready/<client>/ packet folder for every client."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "encyro",
        "output_folder": output_folder,
        "encyro_folder": None,
        "packets": [],
        "client_count": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; no Encyro packets created."}

    clients = generate_documents.load_clients(data_file)
    generated_folder = output_folder / generate_documents.GENERATED_FOLDER_NAME
    signed_folder = output_folder / "Signed_Documents"
    encyro_root = output_folder / ENCYRO_FOLDER_NAME
    encyro_root.mkdir(exist_ok=True)

    packets: list[Path] = []
    warnings: list[str] = []
    exported = 0
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"Building Encyro packet for {slug} ({index} of {len(clients)})")

        client_dir = encyro_root / slug
        client_dir.mkdir(parents=True, exist_ok=True)
        included: list[Path] = []
        packet_sources: list[Path] = []

        for html_file in sorted(generated_folder.glob(f"{slug}_*.html")):
            pdf_path = client_dir / f"{html_file.stem}.pdf"
            try:
                html_to_pdf(html_file.read_text(encoding="utf-8"), pdf_path)
            except Exception as exc:
                warnings.append(f"{slug}: could not convert {html_file.name} ({exc}).")
                continue
            included.append(pdf_path)
            packet_sources.append(pdf_path)

        # Generated Word documents upload to Encyro as-is (it converts them on upload).
        for docx_file in sorted(generated_folder.glob(f"{slug}_*.docx")):
            destination = sort_tax_docs.unique_destination_path(client_dir, docx_file.name)
            shutil.copy2(docx_file, destination)
            included.append(destination)

        extras = _matching_files(signed_folder, slug)
        for extra in client.get("attachments", []) or []:
            candidate = (input_folder / str(extra)).expanduser()
            if candidate.is_file():
                extras.append(candidate)
        for source in extras:
            if source.suffix.lower() not in COPYABLE_SUFFIXES:
                continue
            destination = sort_tax_docs.unique_destination_path(client_dir, source.name)
            shutil.copy2(source, destination)
            included.append(destination)
            if destination.suffix.lower() == ".pdf":
                packet_sources.append(destination)

        if not included:
            warnings.append(f"{slug}: no documents found to package (run Generate/Sign first?).")

        packet = None
        if packet_sources:
            packet = merge_pdfs(packet_sources, client_dir / f"{slug}{PACKET_SUFFIX}")
            if packet:
                packets.append(packet)

        write_upload_notes(client_dir / NOTES_FILENAME, client, included, packet)
        if included:
            exported += 1

    return {
        **base_result,
        "encyro_folder": encyro_root,
        "packets": packets,
        "client_count": exported,
        "warnings": warnings,
        "summary": (
            f"Built {len(packets)} Encyro packet(s) for {exported} client(s)"
            + (f"; {len(warnings)} note(s)." if warnings else ".")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Assemble upload-ready Encyro packets (merged PDF + notes) per client."
    )
    parser.add_argument("input_folder", help="Folder containing clients.json or clients.csv.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1
    if not sort_tax_docs.check_dependencies():
        return 1

    result = run_encyro_export(folder, status_callback=print)
    print(result["summary"])
    if result["encyro_folder"]:
        print(f"Encyro packets folder: {result['encyro_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
