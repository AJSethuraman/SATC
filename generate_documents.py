#!/usr/bin/env python3
"""Generate client documents (engagement letters, invoices, etc.) from templates.

This is the third tool in the suite. Like the others it is fully local: it fills
editable HTML templates with values from a clients data file (clients.json or
clients.csv) in the input folder and writes finished HTML you can open and print
or save as PDF from any browser. No AI, cloud, or paid APIs.

Templates use a tiny Mustache-style syntax:
  {{field}}                         -> a value from the client record
  {{#line_items}}...{{/line_items}} -> repeat the block for each item in a list
                                       (a non-list truthy value renders the block once)
Single braces (for example CSS rules) are left untouched.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import date
from pathlib import Path

import sort_tax_docs

GENERATED_FOLDER_NAME = "Generated_Documents"
CLIENT_DATA_FILENAMES = ("clients.json", "clients.csv")
TEMPLATE_DIR_NAME = "document_templates"
REPO_TEMPLATE_DIR = Path(__file__).with_name(TEMPLATE_DIR_NAME)

# Template key -> file name. The key is also used in output file names.
TEMPLATE_FILES = {
    "engagement_letter": "engagement_letter.html",
    "invoice": "invoice.html",
    "extension_cover_letter": "extension_cover_letter.html",
    "client_organizer_letter": "client_organizer_letter.html",
}

_SECTION_RE = re.compile(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", re.DOTALL)
_FIELD_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _escape(value: object) -> str:
    """Minimal HTML escaping for substituted values (templates are trusted)."""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _render_fields(text: str, context: dict) -> str:
    return _FIELD_RE.sub(lambda match: _escape(context.get(match.group(1), "")), text)


def render_template(template_text: str, context: dict) -> str:
    """Render a template: repeating sections first, then simple field substitution."""

    def section(match: re.Match) -> str:
        key, inner = match.group(1), match.group(2)
        value = context.get(key)
        if isinstance(value, list):
            return "".join(_render_fields(inner, {**context, **item}) for item in value)
        return _render_fields(inner, context) if value else ""

    return _render_fields(_SECTION_RE.sub(section, template_text), context)


def referenced_fields(template_text: str) -> set[str]:
    """Top-level fields a template references (excluding section-internal ones)."""

    return set(_FIELD_RE.findall(_SECTION_RE.sub("", template_text)))


def missing_fields(template_text: str, context: dict) -> list[str]:
    """Return referenced top-level fields that are absent or blank in the context."""

    return sorted(name for name in referenced_fields(template_text) if not context.get(name))


def _to_float(value: object) -> float:
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return 0.0


def augment_context(client: dict) -> dict:
    """Add convenience values (today's date, computed invoice total)."""

    context = dict(client)
    context.setdefault("generated_date", date.today().isoformat())
    line_items = context.get("line_items")
    if isinstance(line_items, list) and line_items and "total" not in context:
        total = sum(_to_float(item.get("amount")) for item in line_items)
        context["total"] = f"{total:,.2f}"
    return context


def find_client_data_file(input_folder: Path) -> Path | None:
    for name in CLIENT_DATA_FILENAMES:
        candidate = input_folder / name
        if candidate.exists():
            return candidate
    return None


def load_clients(data_file: Path) -> list[dict]:
    """Load client records from a JSON list/object or a CSV file."""

    if data_file.suffix.lower() == ".json":
        data = json.loads(data_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]
    with data_file.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def template_dir(input_folder: Path) -> Path:
    """Use a document_templates/ folder in the input folder if present, else the shipped one."""

    override = input_folder / TEMPLATE_DIR_NAME
    return override if override.is_dir() else REPO_TEMPLATE_DIR


def available_templates(directory: Path, keys=None) -> dict[str, Path]:
    """Map template key -> path for templates that exist in the directory."""

    wanted = keys or TEMPLATE_FILES.keys()
    return {
        key: directory / TEMPLATE_FILES[key]
        for key in wanted
        if key in TEMPLATE_FILES and (directory / TEMPLATE_FILES[key]).exists()
    }


def _client_slug(client: dict, index: int) -> str:
    name = str(client.get("client_name") or client.get("name") or f"client_{index}")
    return sort_tax_docs.safe_filename_part(name).replace(" ", "_")


def run_generation(input_folder, status_callback=None, templates=None) -> dict:
    """Generate the selected templates for every client in the data file."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "generate",
        "output_folder": output_folder,
        "generated_folder": None,
        "documents": [],
        "client_count": 0,
        "document_count": 0,
        "warnings": [],
    }

    data_file = find_client_data_file(input_folder)
    if data_file is None:
        return {
            **base_result,
            "summary": (
                "No clients.json or clients.csv found in the folder; no documents generated."
            ),
        }

    directory = template_dir(input_folder)
    selected = available_templates(directory, templates)
    if not selected:
        return {**base_result, "summary": "No document templates were found to generate."}

    clients = load_clients(data_file)
    generated_folder = output_folder / GENERATED_FOLDER_NAME
    generated_folder.mkdir(exist_ok=True)

    documents: list[Path] = []
    warnings: list[str] = []
    template_text = {key: path.read_text(encoding="utf-8") for key, path in selected.items()}
    for index, client in enumerate(clients, start=1):
        context = augment_context(client)
        slug = _client_slug(client, index)
        if status_callback:
            status_callback(f"Generating documents for {slug} ({index} of {len(clients)})")
        for key, text in template_text.items():
            output_path = sort_tax_docs.unique_destination_path(
                generated_folder, f"{slug}_{key}.html"
            )
            output_path.write_text(render_template(text, context), encoding="utf-8")
            documents.append(output_path)
            missing = missing_fields(text, context)
            if missing:
                warnings.append(f"{output_path.name}: blank field(s): {', '.join(missing)}")

    return {
        **base_result,
        "generated_folder": generated_folder,
        "documents": documents,
        "client_count": len(clients),
        "document_count": len(documents),
        "warnings": warnings,
        "summary": (
            f"Generated {len(documents)} document(s) for {len(clients)} client(s)"
            + (f"; {len(warnings)} had blank fields." if warnings else ".")
        ),
    }


def main() -> int:
    """Generate documents from the command line for one folder."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Generate client documents from templates and a clients data file."
    )
    parser.add_argument("input_folder", help="Folder containing clients.json or clients.csv.")
    parser.add_argument(
        "--templates",
        default="",
        help=f"Comma-separated template keys to generate. Available: {', '.join(TEMPLATE_FILES)}.",
    )
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    keys = [key.strip() for key in args.templates.split(",") if key.strip()] or None
    result = run_generation(folder, status_callback=print, templates=keys)
    print(result["summary"])
    if result["generated_folder"]:
        print(f"Generated documents folder: {result['generated_folder']}")
    for warning in result["warnings"]:
        print(f"  WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
