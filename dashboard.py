#!/usr/bin/env python3
"""A one-page practice dashboard: where every client stands across the pipeline.

Reads what the other tools already produced and renders a single, sleek HTML page
(``Dashboard/dashboard.html``) with one row per client and a column per stage:
email on file, documents received, invoice, documents generated, engagement letter,
Form 8879, Encyro packet, and archived. A summary bar across the top shows the
counts that matter (missing documents, outstanding signatures, not yet invoiced or
archived). Standard-library only; run it any time for a current snapshot.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import checklist
import core
import generate_documents
import sort_tax_docs
import status_tracker

DASHBOARD_FOLDER_NAME = "Dashboard"
DASHBOARD_FILENAME = "dashboard.html"

# Cell states drive the colour of each pill.
OK, PENDING, ATTENTION = "ok", "pending", "attention"


def _has_files(folder: Path, pattern: str) -> bool:
    return folder.is_dir() and any(p.is_file() for p in folder.glob(pattern))


def client_row(client, slug, input_folder, output_folder, doc_map, received, search_files,
               more_specific=()) -> dict:
    """Compute the dashboard cells for one client."""

    generated_dir = output_folder / generate_documents.GENERATED_FOLDER_NAME
    signed_dir = output_folder / status_tracker.SIGNED_FOLDER_NAME
    encyro_dir = output_folder / "Encyro_Ready" / slug
    retention_dir = output_folder / "Retention"

    rows, _ = checklist.evaluate_client(client, doc_map, received)
    expected = len(rows)
    missing = sum(1 for r in rows if r["status"] == checklist.STATUS_MISSING)

    engagement = status_tracker.evaluate(client, slug, status_tracker.ENGAGEMENT_TRACKER, search_files, more_specific)[0]
    form_8879 = status_tracker.evaluate(client, slug, status_tracker.FORM_8879_TRACKER, search_files, more_specific)[0]
    on_file = status_tracker.STATUS_ON_FILE

    return {
        "name": client.get("client_name") or client.get("name") or slug,
        "email": (OK, "✓") if client.get("email") else (ATTENTION, "missing"),
        "documents": (
            (PENDING, "—") if expected == 0
            else (OK, f"{expected}/{expected}") if missing == 0
            else (ATTENTION, f"{expected - missing}/{expected}")
        ),
        "invoice": (OK, str(client.get("total") or "✓")) if client.get("line_items") else (PENDING, "—"),
        "generated": (OK, "✓") if _has_files(generated_dir, f"{slug}_*") else (PENDING, "—"),
        "engagement": (OK, "✓") if engagement == on_file else (ATTENTION, "outstanding"),
        "form8879": (OK, "✓") if form_8879 == on_file else (ATTENTION, "outstanding"),
        "encyro": (OK, "✓") if (encyro_dir.is_dir() and any(encyro_dir.iterdir())) else (PENDING, "—"),
        "archived": (OK, "✓") if _has_files(retention_dir, f"{slug}_*.zip") else (PENDING, "—"),
    }


_COLUMNS = [
    ("email", "Email"),
    ("documents", "Documents"),
    ("invoice", "Invoice"),
    ("generated", "Generated"),
    ("engagement", "Engagement"),
    ("form8879", "8879"),
    ("encyro", "Encyro"),
    ("archived", "Archived"),
]
_PILL_COLORS = {
    OK: ("#0d4429", "#d6f3e1"),
    PENDING: ("#5b6b7b", "#eef1f5"),
    ATTENTION: ("#8a1c1c", "#fbe0e0"),
}


def _pill(state: str, label: str) -> str:
    fg, bg = _PILL_COLORS[state]
    text = core.escape_html(label)
    return f"<span class='pill' style='color:{fg};background:{bg}'>{text}</span>"


def build_dashboard_html(rows: list[dict], summary: dict) -> str:
    headers = "".join(f"<th>{label}</th>" for _, label in _COLUMNS)
    body = ""
    for row in rows:
        cells = "".join(f"<td>{_pill(*row[key])}</td>" for key, _ in _COLUMNS)
        body += f"<tr><td class='name'>{core.escape_html(row['name'])}</td>{cells}</tr>"
    if not rows:
        body = f"<tr><td colspan='{len(_COLUMNS) + 1}'>No clients.</td></tr>"

    chips = "".join(
        f"<div class='chip'><span class='num'>{value}</span><span class='lbl'>{label}</span></div>"
        for label, value in summary["chips"]
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Practice Dashboard</title>
<style>
 :root {{ color-scheme: light; }}
 body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; background: #f6f8fb; color: #1c2733; }}
 header {{ background: #0B1F3A; color: #fff; padding: 22px 28px; }}
 header h1 {{ margin: 0; font-size: 1.3rem; letter-spacing: .3px; }}
 header .sub {{ opacity: .8; font-size: .85rem; margin-top: 4px; }}
 .chips {{ display: flex; flex-wrap: wrap; gap: 12px; padding: 18px 28px; }}
 .chip {{ background: #fff; border: 1px solid #e1e6ec; border-radius: 12px; padding: 12px 16px; min-width: 92px; }}
 .chip .num {{ display: block; font-size: 1.5rem; font-weight: 700; }}
 .chip .lbl {{ font-size: .78rem; color: #5b6b7b; }}
 .wrap {{ padding: 0 28px 28px; }}
 table {{ border-collapse: collapse; width: 100%; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(16,33,58,.08); }}
 th, td {{ padding: 11px 12px; text-align: center; border-bottom: 1px solid #eef1f5; font-size: .9rem; }}
 th {{ background: #f0f3f8; color: #36506e; font-weight: 600; position: sticky; top: 0; }}
 td.name, th:first-child {{ text-align: left; font-weight: 600; }}
 .pill {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .8rem; font-weight: 600; }}
</style></head><body>
<header><h1>Practice Dashboard</h1><div class="sub">{summary['client_count']} client(s) · generated {date.today().isoformat()}</div></header>
<div class="chips">{chips}</div>
<div class="wrap"><table><thead><tr><th>Client</th>{headers}</tr></thead><tbody>{body}</tbody></table></div>
</body></html>
"""


def run_dashboard(input_folder, status_callback=None) -> dict:
    """Build the practice dashboard from current clients and tool output."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    base_result = {
        "tool": "dashboard",
        "output_folder": output_folder,
        "dashboard_folder": None,
        "dashboard_path": None,
        "client_count": 0,
        "warnings": [],
    }

    data_file = generate_documents.find_client_data_file(input_folder)
    if data_file is None:
        return {**base_result, "summary": "No clients.json or clients.csv found; dashboard not built."}

    clients = generate_documents.load_clients(data_file)
    doc_map, _ = checklist.load_doc_map(input_folder)
    received = checklist.received_categories(output_folder)
    search_files = status_tracker.gather_search_files(input_folder, output_folder)
    all_slugs = [generate_documents.client_slug(c, i) for i, c in enumerate(clients, start=1)]

    rows: list[dict] = []
    for index, client in enumerate(clients, start=1):
        slug = generate_documents.client_slug(client, index)
        if status_callback:
            status_callback(f"Dashboard: {slug} ({index} of {len(clients)})")
        more_specific = status_tracker.more_specific_token_sets(slug, all_slugs)
        rows.append(client_row(client, slug, input_folder, output_folder, doc_map, received,
                               search_files, more_specific))

    def count(key: str, *states: str) -> int:
        return sum(1 for r in rows if r[key][0] in states)

    summary = {
        "client_count": len(rows),
        "chips": [
            ("Clients", len(rows)),
            ("Missing docs", count("documents", ATTENTION)),
            ("Engagement out", count("engagement", ATTENTION)),
            ("8879 out", count("form8879", ATTENTION)),
            ("Not invoiced", count("invoice", PENDING)),
            ("Not archived", count("archived", PENDING)),
        ],
    }

    dashboard_folder = output_folder / DASHBOARD_FOLDER_NAME
    dashboard_folder.mkdir(exist_ok=True)
    dashboard_path = dashboard_folder / DASHBOARD_FILENAME
    dashboard_path.write_text(build_dashboard_html(rows, summary), encoding="utf-8")

    missing = summary["chips"][1][1]
    eng_out = summary["chips"][2][1]
    return {
        **base_result,
        "dashboard_folder": dashboard_folder,
        "dashboard_path": dashboard_path,
        "client_count": len(rows),
        "summary": (
            f"Dashboard built for {len(rows)} client(s): {missing} with missing docs, "
            f"{eng_out} engagement letter(s) outstanding."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build a one-page practice status dashboard.")
    parser.add_argument("input_folder", help="Folder containing clients.json and tool output.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_dashboard(folder, status_callback=print)
    print(result["summary"])
    if result["dashboard_path"]:
        print(f"Dashboard: {result['dashboard_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
