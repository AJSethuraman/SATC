#!/usr/bin/env python3
"""Per-client document checklist: expected (from intake) vs. received (from sorting).

Second of the new modules. For each client in clients.json it compares the
``expected_documents`` they reported at intake against the document categories
that actually have files in the sorted output, and writes a printable checklist
plus an aggregate CSV. Use it to see at a glance what is still outstanding and to
send a client their "still needed" list.

The label -> category mapping is *dynamic*: a ``checklist_map.json`` is written to
the folder on first run so you can adjust how intake labels map to sorter
categories. Everything is local and standard-library only.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import generate_documents
import sort_tax_docs

CHECKLIST_FOLDER_NAME = "Checklists"
MAP_FILENAME = "checklist_map.json"
SUMMARY_FILENAME = "checklist_summary.csv"

# Intake document label -> sorter category key(s) that satisfy it.
DEFAULT_DOC_MAP: dict[str, list[str]] = {
    "W-2": ["W2"],
    "1099-NEC": ["1099_NEC"],
    "1099-MISC": ["1099_MISC"],
    "1099-INT": ["1099_INT_DIV"],
    "1099-DIV": ["1099_INT_DIV"],
    "1099-R": ["1099_R"],
    "1098 (Mortgage)": ["1098_Mortgage"],
    "1098-T": ["1098_Tuition"],
    "SSA-1099": ["SSA_1099"],
    "K-1": ["K1"],
    "1099-G": ["1099_G"],
    "1099-K": ["1099_K"],
}

STATUS_RECEIVED = "Received"
STATUS_MISSING = "Missing"
STATUS_MANUAL = "Manual check"


def load_doc_map(input_folder: Path) -> tuple[dict, Path]:
    """Return (mapping, path), creating an editable default file if none exists."""

    map_path = input_folder / MAP_FILENAME
    if map_path.exists():
        data = json.loads(map_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data:
            return data, map_path
    map_path.write_text(json.dumps(DEFAULT_DOC_MAP, indent=2), encoding="utf-8")
    return DEFAULT_DOC_MAP, map_path


def received_categories(output_folder: Path) -> set[str]:
    """Sorter category keys whose folder exists and contains at least one file."""

    received: set[str] = set()
    for key, folder_name in sort_tax_docs.CATEGORY_FOLDERS.items():
        if key == "NeedsReview":
            continue
        folder = output_folder / folder_name
        if folder.is_dir() and any(p.is_file() for p in folder.iterdir()):
            received.add(key)
    return received


def _expected_list(client: dict) -> list[str]:
    expected = client.get("expected_documents") or []
    return [expected] if isinstance(expected, str) else list(expected)


def evaluate_client(client: dict, doc_map: dict, received: set[str]) -> tuple[list[dict], list[str]]:
    """Return (rows, extras) where each row is {document, status} for one expected doc."""

    rows: list[dict] = []
    expected_categories: set[str] = set()
    for label in _expected_list(client):
        categories = doc_map.get(label) or []
        expected_categories.update(categories)
        if not categories:
            rows.append({"document": label, "status": STATUS_MANUAL})
        elif any(category in received for category in categories):
            rows.append({"document": label, "status": STATUS_RECEIVED})
        else:
            rows.append({"document": label, "status": STATUS_MISSING})

    extras = sorted(received - expected_categories)
    return rows, extras


def _missing_count(rows: list[dict]) -> int:
    return sum(1 for row in rows if row["status"] == STATUS_MISSING)


def build_checklist_html(client: dict, rows: list[dict], extras: list[str]) -> str:
    name = generate_documents._escape(client.get("client_name") or client.get("name") or "Client")
    colors = {STATUS_RECEIVED: "#1a7f37", STATUS_MISSING: "#c0392b", STATUS_MANUAL: "#9a6700"}
    body_rows = "".join(
        f"<tr><td>{generate_documents._escape(r['document'])}</td>"
        f"<td style='color:{colors.get(r['status'], '#333')};font-weight:600'>{r['status']}</td></tr>"
        for r in rows
    ) or "<tr><td colspan='2'>No expected documents on file.</td></tr>"
    extra_note = (
        f"<p class='note'>Also received (not on the expected list): {', '.join(extras)}.</p>"
        if extras else ""
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Document Checklist - {name}</title>
<style>
 body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 640px; margin: 2rem auto; color: #1c2733; }}
 h1 {{ font-size: 1.4rem; }} table {{ border-collapse: collapse; width: 100%; }}
 td, th {{ border-bottom: 1px solid #e1e6ec; padding: .5rem .4rem; text-align: left; }}
 .note {{ color: #5b6b7b; }}
</style></head><body>
<h1>Document Checklist — {name}</h1>
<table><tr><th>Document</th><th>Status</th></tr>{body_rows}</table>
{extra_note}
</body></html>
"""


def run_checklist(input_folder, status_callback=None) -> dict:
    """Build a checklist per client and an aggregate CSV summary."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "checklist",
        "output_folder": output_folder,
        "checklist_folder": None,
        "checklists": [],
        "client_count": 0,
        "total_missing": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; no checklists created."}

    clients = generate_documents.load_clients(data_file)
    doc_map, _ = load_doc_map(input_folder)
    received = received_categories(output_folder)
    checklist_folder = output_folder / CHECKLIST_FOLDER_NAME
    checklist_folder.mkdir(exist_ok=True)

    checklists: list[Path] = []
    warnings: list[str] = []
    total_missing = 0
    summary_rows: list[dict] = []
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"Checking documents for {slug} ({index} of {len(clients)})")
        rows, extras = evaluate_client(client, doc_map, received)
        if not rows:
            warnings.append(f"{slug}: no expected_documents recorded (collect intake first?).")
        missing = _missing_count(rows)
        total_missing += missing

        path = checklist_folder / f"{slug}_checklist.html"
        path.write_text(build_checklist_html(client, rows, extras), encoding="utf-8")
        checklists.append(path)
        for row in rows:
            summary_rows.append({"client": slug, "document": row["document"], "status": row["status"]})

    summary_path = checklist_folder / SUMMARY_FILENAME
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["client", "document", "status"])
        writer.writeheader()
        writer.writerows(summary_rows)

    return {
        **base_result,
        "checklist_folder": checklist_folder,
        "checklists": checklists,
        "client_count": len(clients),
        "total_missing": total_missing,
        "warnings": warnings,
        "summary": (
            f"Built {len(checklists)} checklist(s); {total_missing} document(s) still missing"
            + (" (no documents sorted yet?)." if not received else ".")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build a per-client expected-vs-received document checklist."
    )
    parser.add_argument("input_folder", help="Folder containing clients.json and sorted output.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_checklist(folder, status_callback=print)
    print(result["summary"])
    if result["checklist_folder"]:
        print(f"Checklists folder: {result['checklist_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
