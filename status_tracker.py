#!/usr/bin/env python3
"""Track whether a signed document is on file for each client.

Powers two tools that share one engine:
  * Engagement Letter Tracker -- is a signed engagement letter on file?
  * Form 8879 Tracker         -- is a signed Form 8879 (e-file authorization) on file?

For each client it reports "On file" or "Outstanding". A document counts as on file
if the client record sets the tracker's flag (for example ``form_8879_signed: true``)
or if a matching file is found -- one whose name contains the client's name and the
tracker's keyword -- in the folder, its subfolders, or Signed_Documents/. Reports are
written to Status/ as CSV and a printable HTML table. Standard-library only.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import generate_documents
import sort_tax_docs

STATUS_FOLDER_NAME = "Status"
SIGNED_FOLDER_NAME = "Signed_Documents"
SEARCH_SUFFIXES = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

STATUS_ON_FILE = "On file"
STATUS_OUTSTANDING = "Outstanding"


@dataclass(frozen=True)
class TrackerConfig:
    key: str          # tool key
    title: str        # report title
    keywords: tuple[str, ...]  # any of these (normalized) in the filename
    signed_field: str          # clients.json field that declares it signed
    basename: str              # output file base name


ENGAGEMENT_TRACKER = TrackerConfig(
    key="engagement",
    title="Engagement Letter Status",
    keywords=("engagement",),
    signed_field="engagement_letter_signed",
    basename="engagement_letter_status",
)
FORM_8879_TRACKER = TrackerConfig(
    key="form8879",
    title="Form 8879 Status",
    keywords=("8879",),
    signed_field="form_8879_signed",
    basename="form_8879_status",
)
FILING_TRACKER = TrackerConfig(
    key="filing",
    title="Filing Status",
    keywords=("filed", "accepted", "efile", "e-file"),
    signed_field="return_filed",
    basename="filing_status",
)


def _norm(text: str) -> str:
    """Reduce to lowercase alphanumerics so separators/spacing don't matter."""

    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _tokens(text: str) -> set[str]:
    """Lowercase alphanumeric tokens, split on any separator."""

    return {token for token in re.split(r"[^a-z0-9]+", str(text).lower()) if token}


def gather_search_files(input_folder: Path, output_folder: Path) -> list[Path]:
    """Candidate files to match against: inputs (excluding output) plus Signed_Documents."""

    files: list[Path] = []
    for path in input_folder.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SEARCH_SUFFIXES:
            continue
        try:
            path.relative_to(output_folder)
            in_output = True
        except ValueError:
            in_output = False
        if not in_output:
            files.append(path)

    signed_folder = output_folder / SIGNED_FOLDER_NAME
    if signed_folder.is_dir():
        files.extend(p for p in signed_folder.iterdir() if p.is_file())
    return files


def evaluate(client: dict, slug: str, config: TrackerConfig, search_files: list[Path]) -> tuple[str, str]:
    """Return (status, source) for one client and tracker."""

    if client.get(config.signed_field):
        value = client[config.signed_field]
        source = f"declared in record ({value})" if value is not True else "declared in record"
        return STATUS_ON_FILE, source

    # Match the client by whole name tokens (so "Jo" does not match "Jones"); match the
    # keyword as a substring of the normalized name (so "8879" matches "form8879").
    slug_tokens = _tokens(slug)
    for path in search_files:
        name_norm = _norm(path.name)
        if (
            slug_tokens
            and slug_tokens <= _tokens(path.name)
            and any(_norm(keyword) in name_norm for keyword in config.keywords)
        ):
            return STATUS_ON_FILE, path.name
    return STATUS_OUTSTANDING, ""


def _build_html(config: TrackerConfig, rows: list[dict]) -> str:
    colors = {STATUS_ON_FILE: "#1a7f37", STATUS_OUTSTANDING: "#c0392b"}
    body = "".join(
        f"<tr><td>{generate_documents._escape(r['client'])}</td>"
        f"<td style='color:{colors[r['status']]};font-weight:600'>{r['status']}</td>"
        f"<td>{generate_documents._escape(r['source'])}</td></tr>"
        for r in rows
    ) or "<tr><td colspan='3'>No clients.</td></tr>"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{generate_documents._escape(config.title)}</title>
<style>
 body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 760px; margin: 2rem auto; color: #1c2733; }}
 h1 {{ font-size: 1.4rem; }} table {{ border-collapse: collapse; width: 100%; }}
 td, th {{ border-bottom: 1px solid #e1e6ec; padding: .5rem .4rem; text-align: left; }}
</style></head><body>
<h1>{generate_documents._escape(config.title)}</h1>
<table><tr><th>Client</th><th>Status</th><th>Source</th></tr>{body}</table>
</body></html>
"""


def run_tracker(input_folder, config: TrackerConfig, status_callback=None) -> dict:
    """Build the status report for one tracker configuration."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": config.key,
        "output_folder": output_folder,
        "status_folder": None,
        "report_path": None,
        "client_count": 0,
        "on_file_count": 0,
        "outstanding_count": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": f"No clients.json or clients.csv found; {config.title} not built."}

    clients = generate_documents.load_clients(data_file)
    search_files = gather_search_files(input_folder, output_folder)
    status_folder = output_folder / STATUS_FOLDER_NAME
    status_folder.mkdir(exist_ok=True)

    rows: list[dict] = []
    on_file = 0
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"{config.title}: checking {slug} ({index} of {len(clients)})")
        status, source = evaluate(client, slug, config, search_files)
        if status == STATUS_ON_FILE:
            on_file += 1
        rows.append({"client": slug, "status": status, "source": source})

    csv_path = status_folder / f"{config.basename}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["client", "status", "source"])
        writer.writeheader()
        writer.writerows(rows)
    (status_folder / f"{config.basename}.html").write_text(_build_html(config, rows), encoding="utf-8")

    outstanding = len(rows) - on_file
    return {
        **base_result,
        "status_folder": status_folder,
        "report_path": csv_path,
        "client_count": len(clients),
        "on_file_count": on_file,
        "outstanding_count": outstanding,
        "summary": f"{config.title}: {on_file} on file, {outstanding} outstanding of {len(rows)} client(s).",
    }


def run_engagement_tracker(input_folder, status_callback=None) -> dict:
    return run_tracker(input_folder, ENGAGEMENT_TRACKER, status_callback)


def run_8879_tracker(input_folder, status_callback=None) -> dict:
    return run_tracker(input_folder, FORM_8879_TRACKER, status_callback)


def run_filing_tracker(input_folder, status_callback=None) -> dict:
    return run_tracker(input_folder, FILING_TRACKER, status_callback)


def main() -> int:
    import argparse

    trackers = {
        "engagement": ENGAGEMENT_TRACKER,
        "form8879": FORM_8879_TRACKER,
        "filing": FILING_TRACKER,
    }
    parser = argparse.ArgumentParser(description="Track signed engagement letters or Form 8879 per client.")
    parser.add_argument("input_folder", help="Folder containing clients.json or clients.csv.")
    parser.add_argument("--tracker", choices=sorted(trackers), default="engagement")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_tracker(folder, trackers[args.tracker], status_callback=print)
    print(result["summary"])
    if result["report_path"]:
        print(f"Report: {result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
