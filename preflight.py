#!/usr/bin/env python3
"""Pre-run input checks: warn when a selected tool is missing what it needs.

A pure, read-only coordinator: given the chosen folder and the selected tool keys,
it returns plain-language warnings (e.g. "Generate needs client data but no
clients.json was found"). The desktop app shows these before running so problems
are caught up front rather than reported as an empty result afterward. Warnings are
advisory -- the caller decides whether to proceed.

Standard library only (plus read-only use of public constants from a few modules).
"""

from __future__ import annotations

from pathlib import Path

import extract_form_data
import generate_documents
import import_clients
import pdf_tools
import sign_documents
import sort_tax_docs

# Tools that read client records and produce nothing useful without them.
CLIENTS_REQUIRED = frozenset({
    "checklist", "invoice", "generate", "engagement", "form8879", "filing",
    "reminders", "email", "encyro", "retention", "payments", "dashboard", "rollover",
})


def _has_pdfs(folder: Path) -> bool:
    return folder.is_dir() and any(folder.glob("*.pdf"))


def precheck(folder, tool_keys, labels=None, *, signature_path=None, cert_path=None) -> list[str]:
    """Return advisory warnings about missing inputs for the selected tools."""

    folder = Path(folder)
    selected = set(tool_keys)
    labels = labels or {}
    name = lambda key: labels.get(key, key)  # noqa: E731 - tiny local alias
    output_folder = folder / sort_tax_docs.OUTPUT_FOLDER_NAME
    issues: list[str] = []

    # Client data: aggregate the tools that need it into one message.
    if not generate_documents.find_client_data_file(folder):
        needing = [name(k) for k in tool_keys if k in CLIENTS_REQUIRED]
        if needing:
            issues.append(
                "No clients.json/csv found, but these need client data: "
                + ", ".join(needing)
                + ". Add clients with Edit Clients, Import Clients, or Client Intake."
            )

    if "import" in selected and import_clients.find_source_file(folder) is None:
        issues.append(f"{name('import')}: no client_list.csv or client_list.xlsx in the folder.")

    if selected & {"sort", "extract"}:
        try:
            has_docs = any(True for _ in sort_tax_docs.iter_supported_files(folder, output_folder))
        except Exception:
            has_docs = True  # never block on a detection hiccup
        if not has_docs:
            which = ", ".join(name(k) for k in ("sort", "extract") if k in selected)
            issues.append(f"{which}: no documents found in the folder to process.")

    if "sign" in selected:
        signature = Path(signature_path) if signature_path else (folder / sign_documents.DEFAULT_SIGNATURE_FILENAME)
        if not signature.is_file():
            issues.append(
                f"{name('sign')}: no signature image "
                f"(add {sign_documents.DEFAULT_SIGNATURE_FILENAME} or set a path in Advanced Options)."
            )

    if "certsign" in selected and not (cert_path and Path(cert_path).is_file()):
        issues.append(f"{name('certsign')}: no certificate selected (set a .p12/.pfx in Advanced Options).")

    if "diagnostics" in selected and "extract" not in selected:
        drake = output_folder / extract_form_data.DRAKE_EXPORT_FOLDER_NAME
        if not (drake.is_dir() and any(drake.glob("*.csv"))):
            issues.append(
                f"{name('diagnostics')}: no extracted data yet "
                "(also select Extract Form Data, or run it first)."
            )

    if "pdftools" in selected:
        root = folder / pdf_tools.PDF_TOOLS_FOLDER_NAME
        if not (_has_pdfs(root / pdf_tools.MERGE_SUBFOLDER) or _has_pdfs(root / pdf_tools.SPLIT_SUBFOLDER)):
            issues.append(
                f"{name('pdftools')}: no PDFs in "
                f"{pdf_tools.PDF_TOOLS_FOLDER_NAME}/{pdf_tools.MERGE_SUBFOLDER} or "
                f"{pdf_tools.PDF_TOOLS_FOLDER_NAME}/{pdf_tools.SPLIT_SUBFOLDER}."
            )

    return issues
