#!/usr/bin/env python3
"""Local PDF merge and split utility.

A standalone tool exposing the suite's PDF plumbing. It works by convention: in a
``PDF_Tools/`` folder inside the input folder,

  * every PDF you drop in ``PDF_Tools/merge/`` is combined (in name order) into one
    ``PDF_Tools/output/merged.pdf``;
  * every PDF in ``PDF_Tools/split/`` is split into one PDF per page in
    ``PDF_Tools/output/``.

Nothing else is touched, and the source PDFs are left in place. The fitz-backed
operations live in pdf_utils so this tool and the Encyro export share one
implementation.
"""

from __future__ import annotations

from pathlib import Path

import pdf_utils
import sort_tax_docs

PDF_TOOLS_FOLDER_NAME = "PDF_Tools"
MERGE_SUBFOLDER = "merge"
SPLIT_SUBFOLDER = "split"
OUTPUT_SUBFOLDER = "output"
MERGED_FILENAME = "merged.pdf"


def _pdfs_in(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.pdf") if p.is_file())


def run_pdf_tools(input_folder, status_callback=None) -> dict:
    """Merge PDFs in PDF_Tools/merge and split PDFs in PDF_Tools/split."""

    input_folder = Path(input_folder)

    base_result = {
        "tool": "pdftools",
        "pdf_folder": None,
        "output_folder": None,
        "merged_path": None,
        "merged_inputs": 0,
        "split_files": 0,
        "warnings": [],
    }

    root = input_folder / PDF_TOOLS_FOLDER_NAME
    merge_inputs = _pdfs_in(root / MERGE_SUBFOLDER)
    split_inputs = _pdfs_in(root / SPLIT_SUBFOLDER)
    if not merge_inputs and not split_inputs:
        return {
            **base_result,
            "summary": (
                f"No PDFs found in {PDF_TOOLS_FOLDER_NAME}/{MERGE_SUBFOLDER} or "
                f"{PDF_TOOLS_FOLDER_NAME}/{SPLIT_SUBFOLDER}; nothing to do."
            ),
        }

    output_folder = root / OUTPUT_SUBFOLDER
    output_folder.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    merged_path = None
    if merge_inputs:
        if status_callback:
            status_callback(f"Merging {len(merge_inputs)} PDF(s)")
        destination = sort_tax_docs.unique_destination_path(output_folder, MERGED_FILENAME)
        try:
            merged_path = pdf_utils.merge_pdfs(merge_inputs, destination)
        except Exception as exc:
            warnings.append(f"Merge failed ({exc}).")

    split_count = 0
    for index, pdf in enumerate(split_inputs, start=1):
        if status_callback:
            status_callback(f"Splitting {index} of {len(split_inputs)}: {pdf.name}")
        try:
            split_count += len(pdf_utils.split_pdf(pdf, output_folder))
        except Exception as exc:
            warnings.append(f"{pdf.name}: split failed ({exc}).")

    parts = []
    if merged_path:
        parts.append(f"merged {len(merge_inputs)} PDF(s)")
    if split_count:
        parts.append(f"split into {split_count} page file(s)")
    return {
        **base_result,
        "pdf_folder": root,
        "output_folder": output_folder,
        "merged_path": merged_path,
        "merged_inputs": len(merge_inputs) if merged_path else 0,
        "split_files": split_count,
        "warnings": warnings,
        "summary": ("PDF tools: " + ", ".join(parts) + ".") if parts else "PDF tools: nothing produced.",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Merge/split PDFs via a PDF_Tools/ convention folder.")
    parser.add_argument("input_folder", help="Folder containing a PDF_Tools/ subfolder.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1
    if not sort_tax_docs.check_dependencies():
        return 1

    result = run_pdf_tools(folder, status_callback=print)
    print(result["summary"])
    if result["output_folder"]:
        print(f"Output folder: {result['output_folder']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
