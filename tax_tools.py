#!/usr/bin/env python3
"""Registry of local tax tools that can be run individually or in sequence.

Each tool shares one ``ToolContext`` (input folder plus options) and returns a
result dict. The desktop app, the legacy web app, and the command line all run
tools through this single registry so behavior stays consistent everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import compose_emails
import export_encyro
import extract_form_data
import generate_documents
import sign_documents
import sort_tax_docs


@dataclass
class ToolContext:
    """Inputs and options shared by every tool in a run."""

    input_folder: Path
    move: bool = False
    save_extracted_text: bool = False
    split_combined: bool = True
    document_templates: tuple[str, ...] | None = None
    signature_path: str | None = None
    signature_anchor: str = sign_documents.DEFAULT_ANCHOR
    status_callback: Callable[[str], None] | None = None

    def status(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)


@dataclass(frozen=True)
class Tool:
    """A named tool that operates on a ToolContext and returns a result dict."""

    key: str
    name: str
    description: str
    run: Callable[[ToolContext], dict]


def _run_sorter(context: ToolContext) -> dict:
    return sort_tax_docs.run_sort(
        context.input_folder,
        move=context.move,
        save_extracted_text=context.save_extracted_text,
        split_combined=context.split_combined,
        status_callback=context.status_callback,
    )


def _run_extractor(context: ToolContext) -> dict:
    return extract_form_data.run_extraction(
        context.input_folder,
        save_extracted_text=context.save_extracted_text,
        status_callback=context.status_callback,
    )


def _run_generator(context: ToolContext) -> dict:
    return generate_documents.run_generation(
        context.input_folder,
        status_callback=context.status_callback,
        templates=context.document_templates,
    )


def _run_signer(context: ToolContext) -> dict:
    return sign_documents.run_signing(
        context.input_folder,
        signature_path=context.signature_path,
        anchor=context.signature_anchor,
        status_callback=context.status_callback,
    )


def _run_emailer(context: ToolContext) -> dict:
    return compose_emails.run_email_drafts(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_encyro(context: ToolContext) -> dict:
    return export_encyro.run_encyro_export(
        context.input_folder,
        status_callback=context.status_callback,
    )


TOOLS: tuple[Tool, ...] = (
    Tool(
        "sort",
        "Sort Documents",
        "Classify uploads and copy (or move) them into category folders with an inventory.",
        _run_sorter,
    ),
    Tool(
        "extract",
        "Extract Form Data",
        "Pull key fields from W-2 and 1099 forms into a spreadsheet and Drake CSVs.",
        _run_extractor,
    ),
    Tool(
        "generate",
        "Generate Documents",
        "Fill engagement letters, invoices, and client letters from a clients.json/csv data file.",
        _run_generator,
    ),
    Tool(
        "sign",
        "Sign Documents",
        "Stamp your signature image onto PDFs that carry a signature anchor phrase.",
        _run_signer,
    ),
    Tool(
        "email",
        "Compose Email Drafts",
        "Build review-ready .eml drafts per client with their documents attached (no auto-send).",
        _run_emailer,
    ),
    Tool(
        "encyro",
        "Export for Encyro",
        "Convert each client's letters to PDF and merge an upload-ready packet for Encyro e-sign.",
        _run_encyro,
    ),
)

TOOLS_BY_KEY: dict[str, Tool] = {tool.key: tool for tool in TOOLS}
DEFAULT_TOOL_KEYS: tuple[str, ...] = tuple(tool.key for tool in TOOLS)
_TOOL_ORDER: dict[str, int] = {tool.key: index for index, tool in enumerate(TOOLS)}


def ordered_tool_keys(keys) -> list[str]:
    """Validate the requested keys and return them in canonical pipeline order.

    Selection order does not matter: you choose any subset of tools and they always
    run in the order that makes sense (sort -> ... -> encyro), with duplicates removed.
    """

    unknown = [key for key in keys if key not in TOOLS_BY_KEY]
    if unknown:
        raise KeyError(f"Unknown tool(s): {', '.join(unknown)}")
    return sorted(set(keys), key=_TOOL_ORDER.__getitem__)


def run_tools(keys, context: ToolContext) -> dict[str, dict]:
    """Run the requested tools in canonical pipeline order; return key -> result."""

    results: dict[str, dict] = {}
    for key in ordered_tool_keys(keys):
        tool = TOOLS_BY_KEY[key]
        context.status(f"Running: {tool.name}")
        results[key] = tool.run(context)
    return results


def main() -> int:
    """Run one or more tools from the command line for a single folder."""

    import argparse

    parser = argparse.ArgumentParser(description="Run local tax tools on an upload folder.")
    parser.add_argument("input_folder", help="Folder containing uploaded tax documents.")
    parser.add_argument(
        "--tools",
        default=",".join(DEFAULT_TOOL_KEYS),
        help=(
            "Comma-separated tool keys to run. Pick any subset; they always run in "
            f"pipeline order regardless of how you list them. Available: {', '.join(DEFAULT_TOOL_KEYS)}."
        ),
    )
    parser.add_argument("--move", action="store_true", help="Move files instead of copying them.")
    parser.add_argument(
        "--save-extracted-text",
        action="store_true",
        help="Save selectable/OCR/combined text and scores for troubleshooting.",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Do not split combined PDFs that contain more than one form type.",
    )
    parser.add_argument(
        "--signature", default="", help="Path to a signature image (PNG) for the sign tool."
    )
    parser.add_argument(
        "--anchor",
        default=sign_documents.DEFAULT_ANCHOR,
        help="Anchor phrase the sign tool places the signature above.",
    )
    args = parser.parse_args()

    keys = [key.strip() for key in args.tools.split(",") if key.strip()]
    unknown = [key for key in keys if key not in TOOLS_BY_KEY]
    if unknown:
        print(f"Unknown tool(s): {', '.join(unknown)}. Available: {', '.join(DEFAULT_TOOL_KEYS)}.")
        return 1

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1
    if not sort_tax_docs.check_dependencies():
        return 1

    context = ToolContext(
        input_folder=folder,
        move=args.move,
        save_extracted_text=args.save_extracted_text,
        split_combined=not args.no_split,
        signature_path=args.signature or None,
        signature_anchor=args.anchor,
        status_callback=lambda message: print(message),
    )
    results = run_tools(keys, context)
    print("\nDone.")
    for key in keys:
        print(f"  {TOOLS_BY_KEY[key].name}: {results[key].get('summary', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
