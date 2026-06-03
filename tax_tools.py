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

import cert_sign
import checklist
import compose_emails
import dashboard
import diagnostics
import export_encyro
import extract_form_data
import generate_documents
import import_clients
import intake
import invoice_calc
import payments
import pdf_tools
import reminders
import retention
import sign_documents
import sort_tax_docs
import status_tracker
import validate_config
import year_rollover


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
    cert_path: str | None = None
    cert_password: str | None = None
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
    group: str = "Other"


def _run_validate(context: ToolContext) -> dict:
    return validate_config.run_validation(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_import(context: ToolContext) -> dict:
    return import_clients.run_import(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_intake(context: ToolContext) -> dict:
    return intake.run_intake(
        context.input_folder,
        status_callback=context.status_callback,
    )


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


def _run_checklist(context: ToolContext) -> dict:
    return checklist.run_checklist(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_invoice(context: ToolContext) -> dict:
    return invoice_calc.run_invoice_calc(
        context.input_folder,
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


def _run_engagement_tracker(context: ToolContext) -> dict:
    return status_tracker.run_engagement_tracker(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_8879_tracker(context: ToolContext) -> dict:
    return status_tracker.run_8879_tracker(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_filing_tracker(context: ToolContext) -> dict:
    return status_tracker.run_filing_tracker(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_diagnostics(context: ToolContext) -> dict:
    return diagnostics.run_diagnostics(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_payments(context: ToolContext) -> dict:
    return payments.run_payments(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_cert_sign(context: ToolContext) -> dict:
    return cert_sign.run_cert_signing(
        context.input_folder,
        cert_path=context.cert_path,
        cert_password=context.cert_password,
        status_callback=context.status_callback,
    )


def _run_reminders(context: ToolContext) -> dict:
    return reminders.run_reminders(
        context.input_folder,
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


def _run_retention(context: ToolContext) -> dict:
    return retention.run_retention(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_dashboard(context: ToolContext) -> dict:
    return dashboard.run_dashboard(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_rollover(context: ToolContext) -> dict:
    return year_rollover.run_rollover(
        context.input_folder,
        status_callback=context.status_callback,
    )


def _run_pdf_tools(context: ToolContext) -> dict:
    return pdf_tools.run_pdf_tools(
        context.input_folder,
        status_callback=context.status_callback,
    )


_INTAKE_DOCS = "Onboarding & Documents"
_PREP = "Preparation"
_SIGNING = "Signing"
_TRACKING = "Tracking & Reminders"
_DELIVERY = "Delivery & Records"
_MANAGEMENT = "Practice Management"

TOOLS: tuple[Tool, ...] = (
    Tool(
        "validate",
        "Validate Config",
        "Pre-flight check of clients.json and config files for problems (read-only).",
        _run_validate,
        group=_INTAKE_DOCS,
    ),
    Tool(
        "import",
        "Import Clients",
        "Import an existing CSV/Excel client list into clients.json (deduped append).",
        _run_import,
        group=_INTAKE_DOCS,
    ),
    Tool(
        "intake",
        "Client Intake",
        "Generate a dynamic fillable intake form and compile returned responses into clients.json.",
        _run_intake,
        group=_INTAKE_DOCS,
    ),
    Tool(
        "sort",
        "Sort Documents",
        "Classify uploads and copy (or move) them into category folders with an inventory.",
        _run_sorter,
        group=_INTAKE_DOCS,
    ),
    Tool(
        "extract",
        "Extract Form Data",
        "Pull key fields from W-2 and 1099 forms into a spreadsheet and Drake CSVs.",
        _run_extractor,
        group=_INTAKE_DOCS,
    ),
    Tool(
        "diagnostics",
        "Data Diagnostics",
        "Sanity-check extracted form data (withholding vs. wages, blanks, duplicates).",
        _run_diagnostics,
        group=_INTAKE_DOCS,
    ),
    Tool(
        "checklist",
        "Document Checklist",
        "Compare each client's expected documents (from intake) against what was sorted.",
        _run_checklist,
        group=_INTAKE_DOCS,
    ),
    Tool(
        "invoice",
        "Calculate Invoices",
        "Compute invoice line items from an editable fee schedule and write them to clients.json.",
        _run_invoice,
        group=_PREP,
    ),
    Tool(
        "generate",
        "Generate Documents",
        "Fill engagement letters, invoices, and client letters from a clients.json/csv data file.",
        _run_generator,
        group=_PREP,
    ),
    Tool(
        "sign",
        "Sign Documents",
        "Stamp your signature image onto PDFs that carry a signature anchor phrase.",
        _run_signer,
        group=_SIGNING,
    ),
    Tool(
        "certsign",
        "Certificate Sign (PAdES)",
        "Apply a tamper-evident digital signature to PDFs using a PKCS#12 certificate.",
        _run_cert_sign,
        group=_SIGNING,
    ),
    Tool(
        "engagement",
        "Engagement Letter Tracker",
        "Report which clients have a signed engagement letter on file vs. outstanding.",
        _run_engagement_tracker,
        group=_TRACKING,
    ),
    Tool(
        "form8879",
        "Form 8879 Tracker",
        "Report which clients have a signed Form 8879 (e-file authorization) on file.",
        _run_8879_tracker,
        group=_TRACKING,
    ),
    Tool(
        "filing",
        "Filing Tracker",
        "Report which clients' returns have been filed/accepted vs. outstanding.",
        _run_filing_tracker,
        group=_TRACKING,
    ),
    Tool(
        "reminders",
        "Send Reminders",
        "Draft reminder emails for clients with outstanding signatures or missing documents.",
        _run_reminders,
        group=_TRACKING,
    ),
    Tool(
        "email",
        "Compose Email Drafts",
        "Build review-ready .eml drafts per client with their documents attached (no auto-send).",
        _run_emailer,
        group=_DELIVERY,
    ),
    Tool(
        "encyro",
        "Export for Encyro",
        "Convert each client's letters to PDF and merge an upload-ready packet for Encyro e-sign.",
        _run_encyro,
        group=_DELIVERY,
    ),
    Tool(
        "retention",
        "Records Retention",
        "Archive each client's complete package into a dated zip with a manifest and keep-until date.",
        _run_retention,
        group=_DELIVERY,
    ),
    Tool(
        "payments",
        "Payments & AR",
        "Track invoice payments and build an accounts-receivable aging report.",
        _run_payments,
        group=_MANAGEMENT,
    ),
    Tool(
        "dashboard",
        "Practice Dashboard",
        "Build a one-page overview of where every client stands across the whole pipeline.",
        _run_dashboard,
        group=_MANAGEMENT,
    ),
    Tool(
        "rollover",
        "Year Rollover",
        "Carry clients forward into a new tax year subfolder, resetting per-year status.",
        _run_rollover,
        group=_MANAGEMENT,
    ),
    Tool(
        "pdftools",
        "PDF Merge/Split",
        "Merge PDFs in PDF_Tools/merge and split PDFs in PDF_Tools/split (one page each).",
        _run_pdf_tools,
        group=_MANAGEMENT,
    ),
)

# Tool groups in canonical (pipeline) order, for the desktop UI sections.
TOOL_GROUPS: tuple[str, ...] = (_INTAKE_DOCS, _PREP, _SIGNING, _TRACKING, _DELIVERY, _MANAGEMENT)

TOOLS_BY_KEY: dict[str, Tool] = {tool.key: tool for tool in TOOLS}
DEFAULT_TOOL_KEYS: tuple[str, ...] = tuple(tool.key for tool in TOOLS)
_TOOL_ORDER: dict[str, int] = {tool.key: index for index, tool in enumerate(TOOLS)}

# "Full pipeline" processes a season; the manual utilities (Year Rollover, PDF
# Merge/Split) are excluded from the everything-preset but remain selectable on their own.
_MANUAL_UTILITIES = {"rollover", "pdftools"}
_FULL_PIPELINE_KEYS = tuple(key for key in DEFAULT_TOOL_KEYS if key not in _MANUAL_UTILITIES)

# Named one-click presets (label -> selected tool keys) for the desktop app.
PRESETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Full pipeline", _FULL_PIPELINE_KEYS),
    ("Intake & documents", ("import", "intake", "sort", "extract", "diagnostics", "checklist")),
    ("Prepare & generate", ("invoice", "generate")),
    ("Sign & deliver", ("sign", "email", "encyro")),
    ("Status & reminders", ("engagement", "form8879", "filing", "reminders", "dashboard")),
)

def tools_by_group() -> "dict[str, list[Tool]]":
    """Tools grouped by their pipeline phase, preserving registry order."""

    grouped: dict[str, list[Tool]] = {group: [] for group in TOOL_GROUPS}
    for tool in TOOLS:
        grouped.setdefault(tool.group, []).append(tool)
    return grouped


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
    parser.add_argument(
        "--cert", default="", help="Path to a PKCS#12 certificate (.p12/.pfx) for the certsign tool."
    )
    parser.add_argument(
        "--templates", default="",
        help="Comma-separated template keys for the generate tool (default: all).",
    )
    parser.add_argument(
        "--per-client",
        action="store_true",
        help="Per-client folders mode: run the selected tools on each client subfolder.",
    )
    args = parser.parse_args()

    import os

    cert_password = os.environ.get("SATC_CERT_PASSWORD")
    document_templates = tuple(t.strip() for t in args.templates.split(",") if t.strip()) or None

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

    if args.per_client:
        import batch  # local import avoids an import cycle (batch imports tax_tools)

        result = batch.run_batch(
            folder, keys, move=args.move, save_extracted_text=args.save_extracted_text,
            split_combined=not args.no_split, document_templates=document_templates,
            signature_path=args.signature or None, signature_anchor=args.anchor,
            cert_path=args.cert or None, cert_password=cert_password,
            status_callback=lambda m: print(m),
        )
        print("\n" + result["summary"])
        for client in result["clients"]:
            print(f"\n{client['slug']}  ({client['folder']})")
            for line in client["lines"]:
                print(f"  {line}")
        return 0

    context = ToolContext(
        input_folder=folder,
        move=args.move,
        save_extracted_text=args.save_extracted_text,
        split_combined=not args.no_split,
        document_templates=document_templates,
        signature_path=args.signature or None,
        signature_anchor=args.anchor,
        cert_path=args.cert or None,
        cert_password=cert_password,
        status_callback=lambda message: print(message),
    )
    results = run_tools(keys, context)
    print("\nDone.")
    for key in keys:
        print(f"  {TOOLS_BY_KEY[key].name}: {results[key].get('summary', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
