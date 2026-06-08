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
import sys
from datetime import date
from pathlib import Path

import core
import sort_tax_docs

GENERATED_FOLDER_NAME = "Generated_Documents"
CLIENT_DATA_FILENAMES = ("clients.json", "clients.csv")
TEMPLATE_DIR_NAME = "document_templates"


def _bundled_resource_root() -> Path:
    """Where shipped resources live: the PyInstaller bundle dir when frozen, else here."""

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


REPO_TEMPLATE_DIR = _bundled_resource_root() / TEMPLATE_DIR_NAME

# Any file with one of these extensions in the templates folder is offered as a
# template. The file name (without extension) becomes the template key, so adding
# a template is just dropping a file in the folder -- no code change needed.
#   .html  -> {{field}} and {{#section}}...{{/section}} (the built-in letters)
#   .docx  -> a Word document using {{ field }} / {% for %} (rendered via docxtpl)
TEMPLATE_EXTENSIONS = (".html", ".docx")

# The letters that ship with the suite (used only for the CLI help listing).
SHIPPED_TEMPLATE_KEYS = (
    "engagement_letter",
    "invoice",
    "extension_cover_letter",
    "client_organizer_letter",
    "tax_results_letter",
)

_SECTION_RE = re.compile(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", re.DOTALL)
_FIELD_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


# Shared primitives live in core; kept as module-local names for internal callers.
_escape = core.escape_html


def _render_fields(text: str, context: dict, escape: bool = True) -> str:
    def replace(match: re.Match) -> str:
        value = context.get(match.group(1), "")
        return _escape(value) if escape else str(value)

    return _FIELD_RE.sub(replace, text)


def render_template(template_text: str, context: dict, escape: bool = True) -> str:
    """Render a template: repeating sections first, then simple field substitution.

    Set escape=False for plain-text output (for example email bodies), where HTML
    escaping is not wanted.
    """

    def section(match: re.Match) -> str:
        key, inner = match.group(1), match.group(2)
        value = context.get(key)
        if isinstance(value, list):
            return "".join(_render_fields(inner, {**context, **item}, escape) for item in value)
        return _render_fields(inner, context, escape) if value else ""

    return _render_fields(_SECTION_RE.sub(section, template_text), context, escape)


def referenced_fields(template_text: str) -> set[str]:
    """Top-level fields a template references (excluding section-internal ones)."""

    return set(_FIELD_RE.findall(_SECTION_RE.sub("", template_text)))


def missing_fields(template_text: str, context: dict) -> list[str]:
    """Return referenced top-level fields that are absent or blank in the context."""

    return sorted(name for name in referenced_fields(template_text) if not context.get(name))


_to_float = core.parse_money


FIRM_SETTINGS_FILENAME = "firm.json"


def load_firm_settings(input_folder: Path) -> dict:
    """Firm-wide defaults (firm name/address/phone, preparer, payment terms).

    Stored once in firm.json so they need not be repeated on every client record.
    """

    path = Path(input_folder) / FIRM_SETTINGS_FILENAME
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {}


def augment_context(client: dict, firm: dict | None = None) -> dict:
    """Add convenience values (today's date, computed invoice total).

    Firm-wide defaults are merged underneath the client, so a client record can
    still override any firm field.
    """

    context = {**(firm or {}), **client}
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


def discover_templates(directory: Path) -> dict[str, Path]:
    """Map template key (file name without extension) -> path for every template file.

    Scans the folder, so dropping a new .html or .docx file in makes it available
    immediately with no code change. If two files share a stem, .docx wins.
    """

    found: dict[str, Path] = {}
    if directory.is_dir():
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix.lower() in TEMPLATE_EXTENSIONS:
                if path.stem not in found or path.suffix.lower() == ".docx":
                    found[path.stem] = path
    return found


def available_templates(directory: Path, keys=None) -> dict[str, Path]:
    """Discovered template key -> path, optionally narrowed to ``keys``.

    None means "all discovered templates"; an explicit (possibly empty) list is
    honored as-is.
    """

    discovered = discover_templates(directory)
    if keys is None:
        return discovered
    return {key: discovered[key] for key in keys if key in discovered}


def _docx_template(template_path: Path):
    """Load a Word template, with a clear error if the Word library is missing."""

    try:
        from docxtpl import DocxTemplate
    except ImportError as exc:  # pragma: no cover - exercised only without the dep
        raise RuntimeError(
            "Word (.docx) templates require the 'docxtpl' package (pip install docxtpl)."
        ) from exc
    return DocxTemplate(str(template_path))


def render_template_to_file(template_path: Path, context: dict, output_path: Path) -> Path:
    """Render one template (HTML or Word) for a client and write the output file."""

    if template_path.suffix.lower() == ".docx":
        document = _docx_template(template_path)
        document.render(context)
        document.save(str(output_path))
    else:
        text = template_path.read_text(encoding="utf-8")
        output_path.write_text(render_template(text, context), encoding="utf-8")
    return output_path


def template_missing_fields(template_path: Path, context: dict) -> list[str]:
    """Referenced fields that are absent or blank, for either template type."""

    if template_path.suffix.lower() == ".docx":
        try:
            names = _docx_template(template_path).get_undeclared_template_variables()
        except Exception:
            return []
        return sorted(name for name in names if not context.get(name))
    return missing_fields(template_path.read_text(encoding="utf-8"), context)


def output_extension(template_path: Path) -> str:
    """Extension for a generated file: Word templates produce .docx, others .html."""

    return ".docx" if template_path.suffix.lower() == ".docx" else ".html"


def client_slug(client: dict, index: int = 1) -> str:
    """A filesystem-safe identifier for a client, used in output file names."""

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
    firm = load_firm_settings(input_folder)
    for index, client in enumerate(clients, start=1):
        context = augment_context(client, firm)
        slug = client_slug(client, index)
        if status_callback:
            status_callback(f"Generating documents for {slug} ({index} of {len(clients)})")
        for key, path in selected.items():
            output_path = sort_tax_docs.unique_destination_path(
                generated_folder, f"{slug}_{key}{output_extension(path)}"
            )
            try:
                render_template_to_file(path, context, output_path)
            except Exception as exc:
                warnings.append(f"{slug}_{key}: could not render template ({exc}).")
                continue
            documents.append(output_path)
            missing = template_missing_fields(path, context)
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
        help=(
            "Comma-separated template keys to generate (file names without extension). "
            "Default: every template in the folder. Shipped: "
            f"{', '.join(SHIPPED_TEMPLATE_KEYS)}."
        ),
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
