#!/usr/bin/env python3
"""Local Flask UI for the SATC tax document sorter."""

from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from flask import Flask, redirect, render_template, request, url_for
except ImportError:
    print("Flask is not installed.")
    print("Run Setup Tax Document Sorter.bat or: py -3.12 setup_tax_doc_sorter.py")
    raise SystemExit(1)

import sort_tax_docs

APP_ROOT = Path(__file__).resolve().parent
DEFAULT_UPLOADS_FOLDER = APP_ROOT / "Uploads"

app = Flask(__name__)
app.secret_key = "local-tax-document-sorter"


def ensure_default_uploads_folder() -> Path:
    """Create and return the default Uploads folder next to the app."""

    DEFAULT_UPLOADS_FOLDER.mkdir(exist_ok=True)
    return DEFAULT_UPLOADS_FOLDER


def selected_input_folder(form: dict[str, str]) -> Path:
    """Return the selected input folder from form values."""

    if form.get("use_default") == "on":
        return ensure_default_uploads_folder().resolve()
    folder_path = form.get("folder_path", "").strip().strip('"')
    if not folder_path:
        return ensure_default_uploads_folder().resolve()
    return Path(folder_path).expanduser().resolve()


def is_manual_review_row(row: dict[str, Any]) -> bool:
    """Return True when a row should be emphasized for human review."""

    category = str(row.get("Detected Category", ""))
    confidence = str(row.get("Confidence", ""))
    notes = str(row.get("Notes", ""))
    return (
        category == "NeedsReview"
        or confidence == "Low"
        or sort_tax_docs.MULTIPLE_MATCH_NOTE in notes
        or "manual review" in notes.lower()
    )


def summarize_inventory(inventory_path: Path) -> dict[str, Any]:
    """Read the Excel inventory and create display-ready summary data."""

    import pandas as pd

    dataframe = pd.read_excel(inventory_path).fillna("")
    rows = dataframe.to_dict(orient="records")
    category_counts = dict(Counter(str(row.get("Detected Category", "")) for row in rows))
    manual_review_rows = [row for row in rows if is_manual_review_row(row)]
    return {
        "total_files": len(rows),
        "category_counts": category_counts,
        "needs_review_count": category_counts.get("NeedsReview", 0),
        "manual_review_count": len(manual_review_rows),
        "rows": rows,
        "manual_review_rows": manual_review_rows,
    }


def run_sorter_from_ui(input_folder: Path, move: bool, save_extracted_text: bool) -> dict[str, Any]:
    """Run the existing sorter backend and return paths plus inventory summary."""

    output_folder = sort_tax_docs.setup_output_folders(input_folder)
    debug_folder = sort_tax_docs.setup_debug_text_folder(output_folder, save_extracted_text)
    sort_tax_docs.setup_logging(output_folder)

    rows: list[dict[str, object]] = []
    for file_path in sort_tax_docs.iter_supported_files(input_folder, output_folder):
        rows.append(sort_tax_docs.process_file(file_path, output_folder, move, debug_folder))

    inventory_path = sort_tax_docs.write_inventory(rows, output_folder)
    summary = summarize_inventory(inventory_path)
    return {
        "output_folder": str(output_folder),
        "inventory_path": str(inventory_path),
        "log_path": str(output_folder / sort_tax_docs.LOG_FILE_NAME),
        "debug_folder": str(debug_folder) if debug_folder is not None else "",
        **summary,
    }


def open_local_path(path: Path) -> None:
    """Open a local file/folder using the current OS when feasible."""

    if not path.exists():
        raise FileNotFoundError(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
        return
    subprocess.Popen(["xdg-open", str(path)])


@app.route("/", methods=["GET", "POST"])
def index():
    """Render the main app page and optionally run the sorter."""

    default_uploads_folder = ensure_default_uploads_folder().resolve()
    context: dict[str, Any] = {
        "default_uploads_folder": str(default_uploads_folder),
        "folder_path": "",
        "use_default": True,
        "move": False,
        "save_extracted_text": False,
        "error": "",
        "result": None,
    }

    if request.method == "POST":
        context["use_default"] = request.form.get("use_default") == "on"
        context["move"] = request.form.get("move") == "on"
        context["save_extracted_text"] = request.form.get("save_extracted_text") == "on"
        context["folder_path"] = request.form.get("folder_path", "").strip()
        input_folder = selected_input_folder(request.form)

        if not input_folder.exists() or not input_folder.is_dir():
            context["error"] = f"Folder does not exist or is not a directory: {input_folder}"
            return render_template("index.html", **context)

        if not sort_tax_docs.check_dependencies(verbose=False):
            context["error"] = (
                "Required dependencies are missing. Run Setup Tax Document Sorter.bat "
                "or py -3.12 setup_tax_doc_sorter.py, then reopen this app."
            )
            return render_template("index.html", **context)

        try:
            context["result"] = run_sorter_from_ui(
                input_folder,
                move=context["move"],
                save_extracted_text=context["save_extracted_text"],
            )
        except Exception as exc:  # Friendly page-level failure; per-file errors are handled by sorter.
            context["error"] = f"The sorter could not complete: {exc}"

    return render_template("index.html", **context)


@app.route("/open")
def open_path():
    """Open an output folder or inventory file from a local browser button."""

    path_value = request.args.get("path", "")
    try:
        open_local_path(Path(path_value).expanduser().resolve())
    except Exception as exc:
        return f"Could not open path: {exc}", 400
    return redirect(url_for("index"))


if __name__ == "__main__":
    ensure_default_uploads_folder()
    app.run(host="127.0.0.1", port=5000, debug=False)
