#!/usr/bin/env python3
"""Per-client folders mode: run the suite once per client, with clean attribution.

Instead of one shared folder, each client gets their own subfolder containing only
their documents, so sorting, extraction, the checklist, and retention are correct
per client (no cross-client mixing). This is an orchestrator: it reuses every
existing tool unchanged, running the selected ones on each client subfolder.

Two layouts are supported:
  * A parent ``clients.json`` (the roster) -> a subfolder named for each client
    (created if missing); the client's uploads go in their subfolder.
  * No parent ``clients.json`` -> every immediate subfolder is treated as a client
    (using its own clients.json if present, else the folder name).

Shared config at the parent (firm.json, intake_fields.json, checklist_map.json,
fee_schedule.json, document_templates/) is copied into each subfolder once, so the
same settings and templates apply everywhere. After running, each subfolder's
clients.json is aggregated back into the parent so practice-wide tools (dashboard,
payments) can run at the parent level afterwards.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import generate_documents
import sign_documents
import sort_tax_docs
import tax_tools

SHARED_CONFIG_FILES = (
    generate_documents.FIRM_SETTINGS_FILENAME,
    "intake_fields.json",
    "checklist_map.json",
    "fee_schedule.json",
)
SHARED_CONFIG_DIRS = (generate_documents.TEMPLATE_DIR_NAME,)
# Parent-level folders that are never treated as a client subfolder.
NON_CLIENT_DIRS = {sort_tax_docs.OUTPUT_FOLDER_NAME, generate_documents.TEMPLATE_DIR_NAME}


def client_folders(parent: Path) -> list[tuple[str, Path, dict]]:
    """Return (slug, subfolder, client_record) for each client under the parent."""

    parent = Path(parent)
    data_file = generate_documents.find_client_data_file(parent)
    entries: list[tuple[str, Path, dict]] = []
    if data_file is not None:
        for index, client in enumerate(generate_documents.load_clients(data_file), start=1):
            slug = generate_documents.client_slug(client, index)
            entries.append((slug, parent / slug, client))
        return entries

    for sub in sorted(p for p in parent.iterdir() if p.is_dir()):
        if sub.name in NON_CLIENT_DIRS or sub.name.startswith("."):
            continue
        sub_data = generate_documents.find_client_data_file(sub)
        if sub_data is not None:
            records = generate_documents.load_clients(sub_data)
            record = records[0] if records else {"client_name": sub.name}
        else:
            record = {"client_name": sub.name}
        entries.append((sub.name, sub, record))
    return entries


def propagate_config(parent: Path, sub: Path) -> None:
    """Copy shared config files/dirs from the parent into a subfolder if absent."""

    for name in SHARED_CONFIG_FILES:
        source = parent / name
        if source.is_file() and not (sub / name).exists():
            shutil.copy2(source, sub / name)
    for name in SHARED_CONFIG_DIRS:
        source = parent / name
        if source.is_dir() and not (sub / name).exists():
            shutil.copytree(source, sub / name)


def run_batch(
    parent_folder,
    tool_keys,
    *,
    move: bool = False,
    save_extracted_text: bool = False,
    split_combined: bool = True,
    document_templates=None,
    signature_path=None,
    signature_anchor: str = sign_documents.DEFAULT_ANCHOR,
    cert_path=None,
    cert_password=None,
    status_callback=None,
) -> dict:
    """Run the selected tools on each client subfolder; aggregate results."""

    parent = Path(parent_folder)
    entries = client_folders(parent)
    ordered = tax_tools.ordered_tool_keys(tool_keys)

    client_summaries: list[dict] = []
    aggregated: list[dict] = []
    for index, (slug, sub, client) in enumerate(entries, start=1):
        sub.mkdir(parents=True, exist_ok=True)
        propagate_config(parent, sub)
        (sub / "clients.json").write_text(json.dumps([client], indent=2), encoding="utf-8")
        if status_callback:
            status_callback(f"[{index}/{len(entries)}] {slug}")

        def relay(message, _slug=slug):
            if status_callback:
                status_callback(f"{_slug}: {message}")

        context = tax_tools.ToolContext(
            input_folder=sub,
            move=move,
            save_extracted_text=save_extracted_text,
            split_combined=split_combined,
            document_templates=document_templates,
            signature_path=signature_path,
            signature_anchor=signature_anchor,
            cert_path=cert_path,
            cert_password=cert_password,
            status_callback=relay,
        )
        results = tax_tools.run_tools(ordered, context)
        aggregated.extend(generate_documents.load_clients(sub / "clients.json"))
        client_summaries.append({
            "slug": slug,
            "folder": str(sub),
            "lines": [f"{tax_tools.TOOLS_BY_KEY[k].name}: {results[k]['summary']}" for k in ordered],
        })

    # Aggregate per-client records back to the parent so practice-wide tools see updates.
    if aggregated:
        (parent / "clients.json").write_text(json.dumps(aggregated, indent=2), encoding="utf-8")

    return {
        "tool": "batch",
        "parent_folder": parent,
        "client_count": len(entries),
        "tool_keys": ordered,
        "clients": client_summaries,
        "summary": (
            f"Processed {len(entries)} client folder(s) with {len(ordered)} tool(s) each."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the suite once per client subfolder.")
    parser.add_argument("parent_folder", help="Folder of client subfolders (and/or a clients.json roster).")
    parser.add_argument("--tools", default=",".join(tax_tools.DEFAULT_TOOL_KEYS),
                        help="Comma-separated tool keys to run per client.")
    parser.add_argument("--move", action="store_true")
    parser.add_argument("--no-split", action="store_true")
    args = parser.parse_args()

    parent = Path(args.parent_folder).expanduser().resolve()
    if not parent.is_dir():
        print(f"Folder does not exist or is not a directory: {parent}")
        return 1
    if not sort_tax_docs.check_dependencies():
        return 1

    keys = [k.strip() for k in args.tools.split(",") if k.strip()]
    result = run_batch(parent, keys, move=args.move, split_combined=not args.no_split,
                       status_callback=print)
    print("\n" + result["summary"])
    for client in result["clients"]:
        print(f"\n{client['slug']}  ({client['folder']})")
        for line in client["lines"]:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
