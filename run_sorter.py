#!/usr/bin/env python3
"""Simple launcher for the local tax document sorter prototype."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DEFAULT_UPLOADS_FOLDER_NAME = "Uploads"
SORTER_SCRIPT_NAME = "sort_tax_docs.py"


def project_folder() -> Path:
    """Return the folder containing this launcher."""

    return Path(__file__).resolve().parent


def default_uploads_folder() -> Path:
    """Create and return the default Uploads folder next to the scripts."""

    uploads = project_folder() / DEFAULT_UPLOADS_FOLDER_NAME
    uploads.mkdir(exist_ok=True)
    return uploads


def choose_input_folder(uploads_folder: Path) -> Path | None:
    """Ask the user which folder to sort and validate the response."""

    print("Local Tax Document Sorter")
    print("-------------------------")
    print(f"Default Uploads folder: {uploads_folder}")
    print("Put client files there, or enter a different folder path below.")
    response = input(
        "\nEnter folder path to sort, or press Enter to use the default Uploads folder: "
    ).strip().strip('"')

    selected = uploads_folder if not response else Path(response).expanduser()
    selected = selected.resolve()
    if not selected.exists() or not selected.is_dir():
        print(f"\nFolder does not exist or is not a directory: {selected}")
        return None
    return selected


def run_sorter(input_folder: Path) -> int:
    """Run sort_tax_docs.py in safe copy mode for the selected folder."""

    sorter_script = project_folder() / SORTER_SCRIPT_NAME
    if not sorter_script.exists():
        print(f"Could not find sorter script: {sorter_script}")
        return 1

    output_folder = input_folder / "Organized_Tax_Documents"
    print("\nStarting sorter in COPY mode. Original files will not be moved or deleted.")
    print(f"Files being sorted from: {input_folder}")
    print(f"Organized output will be created at: {output_folder}")
    sys.stdout.flush()

    completed = subprocess.run([sys.executable, str(sorter_script), str(input_folder)], check=False)

    if completed.returncode == 0:
        print("\nSorter run succeeded.")
        print(f"Review organized files here: {output_folder}")
        print(f"Review the inventory here: {output_folder / 'Document_Inventory.xlsx'}")
        print(f"Review the log here: {output_folder / 'processing_log.txt'}")
    else:
        print("\nSorter run failed. Read the messages above for details.")
        print("If dependencies are missing, run: python setup_tax_doc_sorter.py")
    return completed.returncode


def main() -> int:
    """Launch the sorter with a simple prompt."""

    selected_folder = choose_input_folder(default_uploads_folder())
    if selected_folder is None:
        return 1
    return run_sorter(selected_folder)


if __name__ == "__main__":
    raise SystemExit(main())
