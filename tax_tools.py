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

import extract_form_data
import sort_tax_docs


@dataclass
class ToolContext:
    """Inputs and options shared by every tool in a run."""

    input_folder: Path
    move: bool = False
    save_extracted_text: bool = False
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
        status_callback=context.status_callback,
    )


def _run_extractor(context: ToolContext) -> dict:
    return extract_form_data.run_extraction(
        context.input_folder,
        save_extracted_text=context.save_extracted_text,
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
        "Pull key fields from W-2, 1099-NEC, 1099-INT/DIV, and 1099-R forms into a spreadsheet.",
        _run_extractor,
    ),
)

TOOLS_BY_KEY: dict[str, Tool] = {tool.key: tool for tool in TOOLS}
DEFAULT_TOOL_KEYS: tuple[str, ...] = tuple(tool.key for tool in TOOLS)


def run_tools(keys, context: ToolContext) -> dict[str, dict]:
    """Run the named tools in order and return a mapping of key to result."""

    results: dict[str, dict] = {}
    for key in keys:
        tool = TOOLS_BY_KEY.get(key)
        if tool is None:
            raise KeyError(f"Unknown tool: {key}")
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
        help=f"Comma-separated tool keys to run in order. Available: {', '.join(DEFAULT_TOOL_KEYS)}.",
    )
    parser.add_argument("--move", action="store_true", help="Move files instead of copying them.")
    parser.add_argument(
        "--save-extracted-text",
        action="store_true",
        help="Save selectable/OCR/combined text and scores for troubleshooting.",
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
        status_callback=lambda message: print(message),
    )
    results = run_tools(keys, context)
    print("\nDone.")
    for key in keys:
        print(f"  {TOOLS_BY_KEY[key].name}: {results[key].get('summary', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
