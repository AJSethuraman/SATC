#!/usr/bin/env python3
"""Archive each client's complete package for records retention.

Sixth new module and the end of the pipeline. For every client it collects the
artifacts produced for them -- generated documents, signed PDFs, checklist, Encyro
packet, and their intake response -- into a single ``Retention/<client>_<year>.zip``
with a ``MANIFEST.txt`` (contents plus a "keep until" date based on the retention
period). When the folder holds exactly one client, the sorted source documents are
included too; with several clients they cannot be attributed automatically, so they
are noted instead. Standard-library only.
"""

from __future__ import annotations

import re
import zipfile
from datetime import date
from pathlib import Path

import generate_documents
import sort_tax_docs

RETENTION_FOLDER_NAME = "Retention"
DEFAULT_RETENTION_YEARS = 3
# Per-client artifact folders and the glob (formatted with the slug) to pull from each.
ARTIFACT_SOURCES = (
    ("Generated_Documents", "{slug}_*"),
    ("Signed_Documents", "{slug}_*"),
    ("Signed_Documents", "Signed_{slug}_*"),
    ("Checklists", "{slug}_*"),
)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def gather_client_files(input_folder: Path, output_folder: Path, slug: str, all_slugs=()) -> list[Path]:
    """Collect the per-client artifact files (deduped, order preserved).

    Files belonging to a longer client slug are excluded so a client's archive never
    captures another client's documents.
    """

    longer = generate_documents.longer_slugs(slug, all_slugs)
    files: list[Path] = []
    for folder_name, pattern in ARTIFACT_SOURCES:
        folder = output_folder / folder_name
        if folder.is_dir():
            files.extend(
                p for p in sorted(folder.glob(pattern.format(slug=slug)))
                if p.is_file() and not generate_documents.file_belongs_to_other_client(p.name, longer)
            )

    encyro_dir = output_folder / "Encyro_Ready" / slug
    if encyro_dir.is_dir():
        files.extend(p for p in sorted(encyro_dir.rglob("*")) if p.is_file())

    slug_norm = _norm(slug)
    for response in sorted(input_folder.glob("*_intake.json")):
        if slug_norm and slug_norm in _norm(response.stem):
            files.append(response)

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in files:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def gather_source_documents(output_folder: Path) -> list[Path]:
    """All sorted source files (used only when a folder has a single client)."""

    sources: list[Path] = []
    for key, folder_name in sort_tax_docs.CATEGORY_FOLDERS.items():
        if key == "NeedsReview":
            continue
        folder = output_folder / folder_name
        if folder.is_dir():
            sources.extend(p for p in sorted(folder.iterdir()) if p.is_file())
    return sources


def build_manifest(client: dict, slug: str, arcnames: list[str], keep_until: str) -> str:
    name = client.get("client_name") or client.get("name") or slug
    lines = [
        f"Records retention archive for {name}",
        "=" * 48,
        f"Archived: {date.today().isoformat()}",
        f"Tax year: {client.get('tax_year', '(not specified)')}",
        f"Keep until: December 31, {keep_until}",
        "",
        f"Contents ({len(arcnames)} file(s)):",
    ]
    lines += [f"  - {name}" for name in arcnames] or ["  - (none)"]
    return "\n".join(lines) + "\n"


def run_retention(input_folder, retention_years: int = DEFAULT_RETENTION_YEARS, status_callback=None) -> dict:
    """Build a retention zip per client."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "retention",
        "output_folder": output_folder,
        "retention_folder": None,
        "archives": [],
        "client_count": 0,
        "archived_count": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; no archives created."}

    clients = generate_documents.load_clients(data_file)
    retention_folder = output_folder / RETENTION_FOLDER_NAME
    retention_folder.mkdir(exist_ok=True)
    keep_until = str(date.today().year + retention_years)
    single_client = len(clients) == 1
    source_documents = gather_source_documents(output_folder) if single_client else []

    all_slugs = [generate_documents.client_slug(c, i) for i, c in enumerate(clients, start=1)]
    archives: list[Path] = []
    warnings: list[str] = []
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"Archiving {slug} ({index} of {len(clients)})")

        files = gather_client_files(input_folder, output_folder, slug, all_slugs)
        members: list[tuple[Path, str]] = [(p, f"{p.parent.name}/{p.name}") for p in files]
        for source in source_documents:
            members.append((source, f"Source_Documents/{source.parent.name}/{source.name}"))
        if not single_client:
            warnings.append(f"{slug}: source uploads not auto-attributed (multiple clients); artifacts only.")
        if not members:
            warnings.append(f"{slug}: nothing to archive yet (run the other tools first?).")
            continue

        tax_year = str(client.get("tax_year") or date.today().year)
        zip_path = sort_tax_docs.unique_destination_path(retention_folder, f"{slug}_{tax_year}.zip")
        arcnames = [arc for _, arc in members]
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, arcname in members:
                archive.write(path, arcname=arcname)
            archive.writestr("MANIFEST.txt", build_manifest(client, slug, arcnames, keep_until))
        archives.append(zip_path)

    return {
        **base_result,
        "retention_folder": retention_folder,
        "archives": archives,
        "client_count": len(clients),
        "archived_count": len(archives),
        "warnings": warnings,
        "summary": (
            f"Archived {len(archives)} client package(s); keep until Dec 31, {keep_until}."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Archive each client's package for records retention.")
    parser.add_argument("input_folder", help="Folder containing clients.json and tool output.")
    parser.add_argument(
        "--years", type=int, default=DEFAULT_RETENTION_YEARS, help="Retention period in years."
    )
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_retention(folder, retention_years=args.years, status_callback=print)
    print(result["summary"])
    if result["retention_folder"]:
        print(f"Retention folder: {result['retention_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
