#!/usr/bin/env python3
"""SATC branded local desktop GUI for the tax document sorter."""

from __future__ import annotations

import ctypes
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import clients_editor
import generate_documents
import preflight
import sign_documents
import sort_tax_docs
import tax_tools

APP_ROOT = Path(__file__).resolve().parent
DEFAULT_UPLOADS_FOLDER = APP_ROOT / "Uploads"
PYSIDE_AVAILABLE = importlib.util.find_spec("PySide6") is not None

if PYSIDE_AVAILABLE:
    from PySide6.QtCore import Qt, QThread, QUrl, Signal
    from PySide6.QtGui import QColor, QDesktopServices, QFont
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QProgressBar,
        QScrollArea,
        QStackedWidget,
        QTableWidget,
        QTableWidgetItem,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )


NAVY = "#0B1F3A"
NAVY_DEEP = "#061A35"
NAVY_SOFT = "#173361"
CHARCOAL = "#1F2733"
CHARCOAL_2 = "#3A4250"
GOLD = "#B08D57"
GOLD_LIGHT = "#D4B97E"
GOLD_DEEP = "#8A6F44"
CREAM = "#F6F2EA"
CREAM_2 = "#EFE9DC"
PAPER = "#FBF9F4"
HAIRLINE = "#D9CFB8"
INK = "#0E1726"


def ensure_default_uploads_folder() -> Path:
    """Create and return the default Uploads folder next to the app."""

    DEFAULT_UPLOADS_FOLDER.mkdir(exist_ok=True)
    return DEFAULT_UPLOADS_FOLDER


def is_manual_review_row(row: dict[str, Any]) -> bool:
    """Return True when a row should be highlighted for human review."""

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
    """Read the Excel inventory and create GUI summary values."""

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


def build_run_summary(results: dict[str, dict]) -> dict[str, Any]:
    """Turn raw tool results into GUI-friendly summary data."""

    summary: dict[str, Any] = {
        "tool_lines": [],
        "open_paths": {},
        "sort": None,
        "validate": None,
        "import": None,
        "intake": None,
        "extract": None,
        "diagnostics": None,
        "packet": None,
        "checklist": None,
        "invoice": None,
        "generate": None,
        "sign": None,
        "certsign": None,
        "engagement": None,
        "form8879": None,
        "filing": None,
        "reminders": None,
        "summary": None,
        "email": None,
        "encyro": None,
        "retention": None,
        "payments": None,
        "dashboard": None,
        "rollover": None,
        "pdftools": None,
        "feeworkbook": None,
    }

    validate_result = results.get("validate")
    if validate_result is not None:
        summary["validate"] = {
            "error_count": validate_result["error_count"],
            "warning_count": validate_result["warning_count"],
        }
        summary["tool_lines"].append(f"Validate Config: {validate_result['summary']}")
        if validate_result.get("validation_folder"):
            summary["open_paths"]["Open Validation"] = str(validate_result["validation_folder"])

    import_result = results.get("import")
    if import_result is not None:
        summary["import"] = {"added": import_result["added"], "imported": import_result["imported"]}
        summary["tool_lines"].append(f"Import Clients: {import_result['summary']}")
        if import_result.get("clients_file"):
            summary["open_paths"]["Open Clients File"] = str(import_result["clients_file"])

    intake_result = results.get("intake")
    if intake_result is not None:
        summary["intake"] = {
            "clients_added": intake_result["clients_added"],
            "responses_found": intake_result["responses_found"],
            "warnings": intake_result["warnings"],
        }
        summary["tool_lines"].append(f"Client Intake: {intake_result['summary']}")
        if intake_result.get("intake_folder"):
            summary["open_paths"]["Open Intake Folder"] = str(intake_result["intake_folder"])

    sort_result = results.get("sort")
    if sort_result is not None:
        inventory = summarize_inventory(Path(sort_result["inventory_path"]))
        summary["sort"] = inventory
        summary["tool_lines"].append(f"Sort Documents: {sort_result['summary']}")
        summary["open_paths"]["Open Organized Folder"] = str(sort_result["output_folder"])
        summary["open_paths"]["Open Inventory"] = str(sort_result["inventory_path"])
        summary["open_paths"]["Open Log File"] = str(sort_result["log_path"])

    extract_result = results.get("extract")
    if extract_result is not None:
        summary["extract"] = {
            "total_forms": extract_result["total_forms"],
            "counts_by_category": extract_result["counts_by_category"],
            "review_count": extract_result["review_count"],
        }
        summary["tool_lines"].append(f"Extract Form Data: {extract_result['summary']}")
        if extract_result["data_path"]:
            summary["open_paths"]["Open Extracted Data"] = str(extract_result["data_path"])
        if extract_result.get("drake_export_folder"):
            summary["open_paths"]["Open Drake Export"] = str(extract_result["drake_export_folder"])

    diagnostics_result = results.get("diagnostics")
    if diagnostics_result is not None:
        summary["diagnostics"] = {
            "warning_count": diagnostics_result["warning_count"],
            "finding_count": diagnostics_result["finding_count"],
        }
        summary["tool_lines"].append(f"Data Diagnostics: {diagnostics_result['summary']}")
        if diagnostics_result.get("diagnostics_folder"):
            summary["open_paths"]["Open Diagnostics"] = str(diagnostics_result["diagnostics_folder"])

    packet_result = results.get("packet")
    if packet_result is not None:
        summary["packet"] = {"clients_updated": packet_result["clients_updated"], "unmatched": packet_result["unmatched"]}
        summary["tool_lines"].append(f"Read Filed Forms: {packet_result['summary']}")
        if packet_result.get("clients_file"):
            summary["open_paths"]["Open Clients File"] = str(packet_result["clients_file"])

    checklist_result = results.get("checklist")
    if checklist_result is not None:
        summary["checklist"] = {
            "total_missing": checklist_result["total_missing"],
            "client_count": checklist_result["client_count"],
            "warnings": checklist_result["warnings"],
        }
        summary["tool_lines"].append(f"Document Checklist: {checklist_result['summary']}")
        if checklist_result.get("checklist_folder"):
            summary["open_paths"]["Open Checklists"] = str(checklist_result["checklist_folder"])

    invoice_result = results.get("invoice")
    if invoice_result is not None:
        summary["invoice"] = {
            "invoiced_count": invoice_result["invoiced_count"],
            "grand_total": invoice_result["grand_total"],
            "warnings": invoice_result["warnings"],
        }
        summary["tool_lines"].append(f"Calculate Invoices: {invoice_result['summary']}")
        if invoice_result.get("invoice_folder"):
            summary["open_paths"]["Open Invoices"] = str(invoice_result["invoice_folder"])

    generate_result = results.get("generate")
    if generate_result is not None:
        summary["generate"] = {
            "document_count": generate_result["document_count"],
            "client_count": generate_result["client_count"],
            "warnings": generate_result["warnings"],
        }
        summary["tool_lines"].append(f"Generate Documents: {generate_result['summary']}")
        if generate_result.get("generated_folder"):
            summary["open_paths"]["Open Generated Documents"] = str(
                generate_result["generated_folder"]
            )

    sign_result = results.get("sign")
    if sign_result is not None:
        summary["sign"] = {
            "signed_count": sign_result["signed_count"],
            "warnings": sign_result["warnings"],
        }
        summary["tool_lines"].append(f"Sign Documents: {sign_result['summary']}")
        if sign_result.get("signed_folder"):
            summary["open_paths"]["Open Signed Documents"] = str(sign_result["signed_folder"])

    certsign_result = results.get("certsign")
    if certsign_result is not None:
        summary["certsign"] = {
            "signed_count": certsign_result["signed_count"],
            "warnings": certsign_result["warnings"],
        }
        summary["tool_lines"].append(f"Certificate Sign (PAdES): {certsign_result['summary']}")
        if certsign_result.get("signed_folder"):
            summary["open_paths"]["Open Certified Documents"] = str(certsign_result["signed_folder"])

    for tracker_key, tracker_label in (("engagement", "Engagement Letter Tracker"),
                                       ("form8879", "Form 8879 Tracker"),
                                       ("filing", "Filing Tracker")):
        tracker_result = results.get(tracker_key)
        if tracker_result is not None:
            summary[tracker_key] = {
                "on_file_count": tracker_result["on_file_count"],
                "outstanding_count": tracker_result["outstanding_count"],
            }
            summary["tool_lines"].append(f"{tracker_label}: {tracker_result['summary']}")
            if tracker_result.get("status_folder"):
                summary["open_paths"]["Open Status Reports"] = str(tracker_result["status_folder"])

    reminders_result = results.get("reminders")
    if reminders_result is not None:
        summary["reminders"] = {
            "reminder_count": reminders_result["reminder_count"],
            "warnings": reminders_result["warnings"],
        }
        summary["tool_lines"].append(f"Send Reminders: {reminders_result['summary']}")
        if reminders_result.get("reminders_folder"):
            summary["open_paths"]["Open Reminders"] = str(reminders_result["reminders_folder"])

    summary_email_result = results.get("summary")
    if summary_email_result is not None:
        summary["summary"] = {"email_count": summary_email_result["email_count"]}
        summary["tool_lines"].append(f"Client Summary Email: {summary_email_result['summary']}")
        if summary_email_result.get("summary_folder"):
            summary["open_paths"]["Open Summary Emails"] = str(summary_email_result["summary_folder"])

    email_result = results.get("email")
    if email_result is not None:
        summary["email"] = {
            "draft_count": email_result["draft_count"],
            "warnings": email_result["warnings"],
        }
        summary["tool_lines"].append(f"Compose Email Drafts: {email_result['summary']}")
        if email_result.get("drafts_folder"):
            summary["open_paths"]["Open Email Drafts"] = str(email_result["drafts_folder"])

    encyro_result = results.get("encyro")
    if encyro_result is not None:
        summary["encyro"] = {
            "client_count": encyro_result["client_count"],
            "warnings": encyro_result["warnings"],
        }
        summary["tool_lines"].append(f"Export for Encyro: {encyro_result['summary']}")
        if encyro_result.get("encyro_folder"):
            summary["open_paths"]["Open Encyro Packets"] = str(encyro_result["encyro_folder"])

    retention_result = results.get("retention")
    if retention_result is not None:
        summary["retention"] = {
            "archived_count": retention_result["archived_count"],
            "warnings": retention_result["warnings"],
        }
        summary["tool_lines"].append(f"Records Retention: {retention_result['summary']}")
        if retention_result.get("retention_folder"):
            summary["open_paths"]["Open Retention Archives"] = str(retention_result["retention_folder"])

    payments_result = results.get("payments")
    if payments_result is not None:
        summary["payments"] = {
            "total_outstanding": payments_result["total_outstanding"],
            "total_billed": payments_result["total_billed"],
        }
        summary["tool_lines"].append(f"Payments & AR: {payments_result['summary']}")
        if payments_result.get("payments_folder"):
            summary["open_paths"]["Open AR Report"] = str(payments_result["payments_folder"])

    dashboard_result = results.get("dashboard")
    if dashboard_result is not None:
        summary["dashboard"] = {"client_count": dashboard_result["client_count"]}
        summary["tool_lines"].append(f"Practice Dashboard: {dashboard_result['summary']}")
        if dashboard_result.get("dashboard_path"):
            summary["open_paths"]["Open Dashboard"] = str(dashboard_result["dashboard_path"])

    rollover_result = results.get("rollover")
    if rollover_result is not None:
        summary["rollover"] = {"client_count": rollover_result["client_count"], "new_year": rollover_result["new_year"]}
        summary["tool_lines"].append(f"Year Rollover: {rollover_result['summary']}")
        if rollover_result.get("target_folder"):
            summary["open_paths"]["Open Next Year Folder"] = str(rollover_result["target_folder"])

    pdftools_result = results.get("pdftools")
    if pdftools_result is not None:
        summary["pdftools"] = {
            "merged_inputs": pdftools_result["merged_inputs"],
            "split_files": pdftools_result["split_files"],
        }
        summary["tool_lines"].append(f"PDF Merge/Split: {pdftools_result['summary']}")
        if pdftools_result.get("output_folder"):
            summary["open_paths"]["Open PDF Output"] = str(pdftools_result["output_folder"])

    feeworkbook_result = results.get("feeworkbook")
    if feeworkbook_result is not None:
        summary["feeworkbook"] = {"year": feeworkbook_result["year"], "sheets": feeworkbook_result["sheets"]}
        summary["tool_lines"].append(f"Fee Workbook: {feeworkbook_result['summary']}")
        if feeworkbook_result.get("workbook_path"):
            summary["open_paths"]["Open Fee Workbook"] = str(feeworkbook_result["workbook_path"])

    return summary


def build_batch_summary(batch_result: dict) -> dict:
    """Render a per-client-folders batch result for the results panel."""

    lines = [batch_result["summary"]]
    for client in batch_result["clients"]:
        lines.append(f"— {client['slug']} —")
        lines.extend(f"    {line}" for line in client["lines"])
    return {
        "tool_lines": lines,
        "open_paths": {"Open Parent Folder": str(batch_result["parent_folder"])},
    }


def dependency_message() -> str:
    """Return a friendly dependency message for the GUI."""

    tesseract_missing = sort_tax_docs.find_tesseract_executable() is None
    message = (
        "Some required dependencies are missing.\n\n"
        "Please run Setup Tax Document Sorter.bat, or run setup_tax_doc_sorter.py, "
        "then reopen this app."
    )
    if tesseract_missing:
        message += (
            "\n\nTesseract OCR is needed for scanned PDFs and image files. "
            "If setup prompts you to install it, please allow that install."
        )
    return message


if PYSIDE_AVAILABLE:

    class ToolsWorker(QThread):
        """Background worker that runs the selected tools without freezing the GUI."""

        status_changed = Signal(str)
        finished_successfully = Signal(dict)
        failed = Signal(str)

        def __init__(
            self,
            tool_keys: list[str],
            input_folder: Path,
            move: bool,
            save_extracted_text: bool,
            split_combined: bool,
            document_templates: tuple[str, ...] | None = None,
            signature_path: str | None = None,
            signature_anchor: str = sign_documents.DEFAULT_ANCHOR,
            cert_path: str | None = None,
            cert_password: str | None = None,
            per_client: bool = False,
        ) -> None:
            super().__init__()
            self.tool_keys = tool_keys
            self.input_folder = input_folder
            self.move = move
            self.save_extracted_text = save_extracted_text
            self.split_combined = split_combined
            self.document_templates = document_templates
            self.signature_path = signature_path
            self.signature_anchor = signature_anchor
            self.cert_path = cert_path
            self.cert_password = cert_password
            self.per_client = per_client

        def run(self) -> None:
            try:
                if self.per_client:
                    import batch

                    result = batch.run_batch(
                        self.input_folder, self.tool_keys, move=self.move,
                        save_extracted_text=self.save_extracted_text,
                        split_combined=self.split_combined,
                        document_templates=self.document_templates,
                        signature_path=self.signature_path,
                        signature_anchor=self.signature_anchor,
                        cert_path=self.cert_path, cert_password=self.cert_password,
                        status_callback=self.status_changed.emit,
                    )
                    self.status_changed.emit("Summarizing results...")
                    self.finished_successfully.emit(build_batch_summary(result))
                    return
                context = tax_tools.ToolContext(
                    input_folder=self.input_folder,
                    move=self.move,
                    save_extracted_text=self.save_extracted_text,
                    split_combined=self.split_combined,
                    document_templates=self.document_templates,
                    signature_path=self.signature_path,
                    signature_anchor=self.signature_anchor,
                    cert_path=self.cert_path,
                    cert_password=self.cert_password,
                    status_callback=self.status_changed.emit,
                )
                results = tax_tools.run_tools(self.tool_keys, context)
                self.status_changed.emit("Summarizing results...")
                self.finished_successfully.emit(build_run_summary(results))
            except Exception as exc:
                self.failed.emit(str(exc))


    class ClientsEditorDialog(QDialog):
        """A simple table editor for clients.json -- no JSON editing required."""

        def __init__(self, folder: Path, parent=None) -> None:
            super().__init__(parent)
            self.folder = Path(folder)
            self.setWindowTitle("Edit Clients")
            self.resize(940, 520)

            layout = QVBoxLayout(self)
            layout.addWidget(QLabel(
                "Add, edit, or remove clients. Documents and Services are comma-separated. "
                "Other fields a client already has (totals, signed status) are preserved.",
                objectName="StatusLabel",
            ))

            self.table = QTableWidget(0, len(clients_editor.COLUMN_LABELS))
            self.table.setHorizontalHeaderLabels(list(clients_editor.COLUMN_LABELS))
            self.table.setSortingEnabled(False)
            self.table.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(self.table, stretch=1)

            # Hidden full records, parallel to table rows, so unshown fields survive a save.
            self.row_records: list[dict] = []
            for client in clients_editor.load_clients(self.folder):
                self._append_row(client)

            controls = QHBoxLayout()
            add_button = QPushButton("Add Client")
            add_button.clicked.connect(lambda: self._append_row({}))
            remove_button = QPushButton("Remove Selected")
            remove_button.clicked.connect(self._remove_selected)
            controls.addWidget(add_button)
            controls.addWidget(remove_button)
            controls.addStretch()
            save_button = QPushButton("Save", objectName="PrimaryButton")
            save_button.clicked.connect(self._save)
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(self.reject)
            controls.addWidget(cancel_button)
            controls.addWidget(save_button)
            layout.addLayout(controls)

        def _append_row(self, client: dict) -> None:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, text in enumerate(clients_editor.client_to_row(client)):
                self.table.setItem(row, column, QTableWidgetItem(text))
            self.row_records.append(client)

        def _remove_selected(self) -> None:
            row = self.table.currentRow()
            if row >= 0:
                self.table.removeRow(row)
                del self.row_records[row]

        def _collect(self) -> list[dict]:
            clients: list[dict] = []
            for row in range(self.table.rowCount()):
                cells = [
                    (self.table.item(row, column).text() if self.table.item(row, column) else "")
                    for column in range(self.table.columnCount())
                ]
                client = clients_editor.row_to_client(cells, self.row_records[row])
                if client.get("client_name"):
                    clients.append(client)
            return clients

        def _save(self) -> None:
            try:
                clients_editor.save_clients(self.folder, self._collect())
            except OSError as exc:
                QMessageBox.warning(self, "Could not save", str(exc))
                return
            self.accept()


    class TaxDocumentSorterWindow(QMainWindow):
        """Main SATC desktop window."""

        def __init__(self) -> None:
            super().__init__()
            self.worker: ToolsWorker | None = None
            self.tool_checkboxes: dict[str, QCheckBox] = {}
            self.open_buttons: dict[str, QPushButton] = {}
            self.open_paths: dict[str, str] = {}
            self.selected_folder = ensure_default_uploads_folder().resolve()
            self.result: dict[str, Any] | None = None
            self.setWindowTitle("SATC Tax Workflow")
            self.resize(1000, 640)
            self.setMinimumSize(880, 560)
            self.build_ui()
            self.apply_styles()
            self.set_selected_folder(self.selected_folder)

        OPTIONS_LABEL = "Options"
        RESULTS_LABEL = "Results"

        def build_ui(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)
            root = QHBoxLayout(central)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            root.addWidget(self._build_sidebar())

            main = QWidget(objectName="Main")
            main_layout = QVBoxLayout(main)
            main_layout.setContentsMargins(18, 14, 18, 16)
            main_layout.setSpacing(10)
            main_layout.addWidget(self._build_top_bar())
            main_layout.addLayout(self._build_selection_bar())

            self.pages = QStackedWidget()
            self.group_checkboxes: dict[str, QCheckBox] = {}
            self.group_pages: list[str] = []
            for group, tools in tax_tools.tools_by_group().items():
                if not tools:
                    continue
                self.group_pages.append(group)
                self.pages.addWidget(self._build_group_page(group, tools))
            self.pages.addWidget(self._build_options_page())
            self.pages.addWidget(self._build_results_page())
            main_layout.addWidget(self.pages, stretch=1)
            root.addWidget(main, stretch=1)

            self.nav.setCurrentRow(0)
            self.update_selected_count()

        def _build_sidebar(self) -> "QFrame":
            sidebar = QFrame(objectName="Sidebar")
            sidebar.setFixedWidth(212)
            side = QVBoxLayout(sidebar)
            side.setContentsMargins(16, 18, 16, 16)
            side.setSpacing(6)
            side.addWidget(QLabel("SATC", objectName="Brand"))
            side.addWidget(QLabel("Tax Workflow", objectName="Tagline"))
            side.addSpacing(10)

            self.nav = QListWidget(objectName="Nav")
            self.nav.setFrameShape(QFrame.NoFrame)
            for group in self.group_pages_order():
                self.nav.addItem(group)
            self.nav.addItem(self.OPTIONS_LABEL)
            self.nav.addItem(self.RESULTS_LABEL)
            self.nav.currentRowChanged.connect(self._on_nav_changed)
            side.addWidget(self.nav, stretch=1)

            self.selected_count = QLabel("", objectName="SideNote")
            self.selected_count.setWordWrap(True)
            side.addWidget(self.selected_count)
            self.run_button = QPushButton("Run Selected", objectName="PrimaryButton")
            self.run_button.clicked.connect(self.run_selected_tools)
            side.addWidget(self.run_button)
            self.progress = QProgressBar()
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.progress.hide()
            side.addWidget(self.progress)
            self.status_label = QLabel("Ready.", objectName="SideNote")
            self.status_label.setWordWrap(True)
            side.addWidget(self.status_label)
            return sidebar

        @staticmethod
        def group_pages_order() -> list[str]:
            return [g for g, tools in tax_tools.tools_by_group().items() if tools]

        def _on_nav_changed(self, row: int) -> None:
            if 0 <= row < self.pages.count():
                self.pages.setCurrentIndex(row)

        def _build_top_bar(self) -> "QFrame":
            bar = QFrame(objectName="TopBar")
            layout = QHBoxLayout(bar)
            layout.setContentsMargins(14, 9, 14, 9)
            layout.setSpacing(8)
            layout.addWidget(QLabel("Folder:", objectName="StatusLabel"))
            self.folder_path = QLineEdit()
            self.folder_path.setReadOnly(True)
            layout.addWidget(self.folder_path, stretch=1)
            choose = QPushButton("Choose…")
            choose.clicked.connect(self.choose_folder)
            default = QPushButton("Default")
            default.clicked.connect(lambda: self.set_selected_folder(ensure_default_uploads_folder()))
            edit_clients = QPushButton("Edit Clients")
            edit_clients.setToolTip("Add or edit clients in a table (no JSON editing).")
            edit_clients.clicked.connect(self.open_clients_editor)
            for button in (choose, default, edit_clients):
                layout.addWidget(button)
            return bar

        def _build_selection_bar(self) -> "QHBoxLayout":
            row = QHBoxLayout()
            row.addWidget(QLabel("Preset:", objectName="StatusLabel"))
            self.preset_combo = QComboBox()
            self.preset_combo.addItem("Choose…")
            for label, _keys in tax_tools.PRESETS:
                self.preset_combo.addItem(label)
            self.preset_combo.activated.connect(self._on_preset_chosen)
            row.addWidget(self.preset_combo)
            row.addStretch()
            select_all = QPushButton("Select all", objectName="GhostButton")
            select_all.clicked.connect(lambda: self.set_all_tools(True))
            clear = QPushButton("Clear", objectName="GhostButton")
            clear.clicked.connect(lambda: self.set_all_tools(False))
            row.addWidget(select_all)
            row.addWidget(clear)
            return row

        def _on_preset_chosen(self, index: int) -> None:
            if index >= 1:
                _label, keys = tax_tools.PRESETS[index - 1]
                self.apply_preset(tuple(keys))
            self.preset_combo.setCurrentIndex(0)

        def _build_group_page(self, group: str, tools) -> "QWidget":
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(8)
            header = QHBoxLayout()
            header.addWidget(QLabel(group, objectName="PageTitle"))
            header.addStretch()
            group_toggle = QCheckBox("Select all in group")
            group_toggle.setChecked(True)
            group_toggle.clicked.connect(lambda checked, g=group: self.set_group_tools(g, checked))
            self.group_checkboxes[group] = group_toggle
            header.addWidget(group_toggle)
            layout.addLayout(header)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setObjectName("ToolScroll")
            host = QWidget()
            host_layout = QVBoxLayout(host)
            host_layout.setContentsMargins(4, 4, 10, 4)
            host_layout.setSpacing(6)
            for tool in tools:
                checkbox = QCheckBox(tool.name)
                checkbox.setChecked(True)
                checkbox.toggled.connect(self._on_tool_toggled)
                description = QLabel(tool.description, objectName="ToolDesc")
                description.setWordWrap(True)
                host_layout.addWidget(checkbox)
                host_layout.addWidget(description)
                self.tool_checkboxes[tool.key] = checkbox
            host_layout.addStretch()
            scroll.setWidget(host)
            layout.addWidget(scroll, stretch=1)
            return page

        def _on_tool_toggled(self, _checked: bool = False) -> None:
            self.sync_group_toggles()
            self.update_selected_count()

        def update_selected_count(self) -> None:
            total = len(self.tool_checkboxes)
            selected = sum(1 for box in self.tool_checkboxes.values() if box.isChecked())
            self.selected_count.setText(f"{selected} of {total} tools selected")
            self.run_button.setText(f"Run Selected ({selected})")

        def _build_options_page(self) -> "QWidget":
            page = QWidget()
            outer = QVBoxLayout(page)
            outer.setContentsMargins(2, 2, 2, 2)
            outer.addWidget(QLabel(self.OPTIONS_LABEL, objectName="PageTitle"))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setObjectName("ToolScroll")
            host = QWidget()
            advanced_layout = QVBoxLayout(host)
            advanced_layout.setContentsMargins(8, 8, 12, 8)
            advanced_layout.setSpacing(10)

            self.move_checkbox = QCheckBox("Move files instead of copy")
            self.split_checkbox = QCheckBox("Split combined PDFs (multi-form)")
            self.split_checkbox.setChecked(True)
            self.debug_checkbox = QCheckBox("Save extracted text debug files")
            self.per_client_checkbox = QCheckBox("Per-client subfolders (batch)")
            self.per_client_checkbox.setToolTip(
                "Run the selected tools once per client subfolder for clean per-client attribution."
            )
            for box in (self.move_checkbox, self.split_checkbox, self.debug_checkbox, self.per_client_checkbox):
                advanced_layout.addWidget(box)

            advanced_layout.addWidget(
                QLabel("Templates to generate (drop .html or .docx files in the folder)",
                       objectName="SmallHeading")
            )
            self.templates_row = QVBoxLayout()
            self.template_checkboxes: dict[str, QCheckBox] = {}
            advanced_layout.addLayout(self.templates_row)

            advanced_layout.addWidget(QLabel("Signature for the Sign tool", objectName="SmallHeading"))
            signature_row = QHBoxLayout()
            self.signature_path_edit = QLineEdit()
            self.signature_path_edit.setPlaceholderText(
                "Signature image (optional; defaults to signature.png in the folder)"
            )
            signature_browse = QPushButton("Browse…")
            signature_browse.clicked.connect(self.choose_signature)
            self.anchor_edit = QLineEdit(sign_documents.DEFAULT_ANCHOR)
            self.anchor_edit.setMaximumWidth(220)
            signature_row.addWidget(self.signature_path_edit, stretch=1)
            signature_row.addWidget(signature_browse)
            signature_row.addWidget(QLabel("Anchor:"))
            signature_row.addWidget(self.anchor_edit)
            advanced_layout.addLayout(signature_row)

            advanced_layout.addWidget(
                QLabel("Certificate for the Certificate Sign tool", objectName="SmallHeading")
            )
            cert_row = QHBoxLayout()
            self.cert_path_edit = QLineEdit()
            self.cert_path_edit.setPlaceholderText("PKCS#12 certificate (.p12/.pfx) for PAdES signing")
            cert_browse = QPushButton("Browse…")
            cert_browse.clicked.connect(self.choose_certificate)
            self.cert_password_edit = QLineEdit()
            self.cert_password_edit.setEchoMode(QLineEdit.Password)
            self.cert_password_edit.setPlaceholderText("Password (not stored)")
            self.cert_password_edit.setMaximumWidth(220)
            cert_row.addWidget(self.cert_path_edit, stretch=1)
            cert_row.addWidget(cert_browse)
            cert_row.addWidget(self.cert_password_edit)
            advanced_layout.addLayout(cert_row)
            advanced_layout.addStretch()

            scroll.setWidget(host)
            outer.addWidget(scroll, stretch=1)
            return page

        def _build_results_page(self) -> "QWidget":
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(8)
            self.summary_label = QLabel("Run tools to see results here.", objectName="PageTitle")
            self.summary_label.setWordWrap(True)
            self.needs_review_label = QLabel("", objectName="NeedsReview")
            self.needs_review_label.setWordWrap(True)
            layout.addWidget(self.summary_label)
            layout.addWidget(self.needs_review_label)

            # Open-output buttons in a wrapping grid inside a short scroll area.
            button_labels = [
                "Open Parent Folder", "Open Validation", "Open Clients File",
                "Open Organized Folder", "Open Intake Folder", "Open Inventory",
                "Open Log File", "Open Extracted Data", "Open Drake Export",
                "Open Diagnostics", "Open Checklists", "Open Invoices",
                "Open Generated Documents", "Open Signed Documents", "Open Certified Documents",
                "Open Status Reports", "Open Reminders", "Open Summary Emails", "Open Email Drafts",
                "Open Encyro Packets", "Open Retention Archives", "Open AR Report",
                "Open Dashboard", "Open Next Year Folder", "Open PDF Output",
                "Open Fee Workbook",
            ]
            actions_scroll = QScrollArea()
            actions_scroll.setWidgetResizable(True)
            actions_scroll.setObjectName("ToolScroll")
            actions_scroll.setMaximumHeight(150)
            actions_host = QWidget()
            grid = QGridLayout(actions_host)
            grid.setContentsMargins(6, 6, 6, 6)
            grid.setSpacing(6)
            for index, label in enumerate(button_labels):
                button = QPushButton(label)
                button.setEnabled(False)
                button.clicked.connect(lambda _checked=False, key=label: self.open_result_path(key))
                grid.addWidget(button, index // 3, index % 3)
                self.open_buttons[label] = button
            actions_scroll.setWidget(actions_host)
            layout.addWidget(QLabel("Open outputs", objectName="SmallHeading"))
            layout.addWidget(actions_scroll)

            layout.addWidget(QLabel("Count by category", objectName="SmallHeading"))
            self.category_list = QListWidget()
            self.category_list.setMaximumHeight(120)
            layout.addWidget(self.category_list)

            layout.addWidget(QLabel("Inventory preview", objectName="SmallHeading"))
            self.results_table = QTableWidget(0, 4)
            self.results_table.setHorizontalHeaderLabels(
                ["Original File Name", "Detected Category", "Confidence", "Notes"]
            )
            self.results_table.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(self.results_table, stretch=1)
            return page

        def apply_styles(self) -> None:
            self.setStyleSheet(
                f"""
                QMainWindow {{ background: {PAPER}; color: {INK}; }}
                * {{ font-size: 13px; }}
                #Sidebar {{ background: {NAVY_DEEP}; border-right: 3px solid {GOLD}; }}
                #Brand {{ color: {GOLD_LIGHT}; font: 700 20px Georgia; letter-spacing: 3px; }}
                #Tagline {{ color: {CREAM_2}; font-size: 11px; letter-spacing: 1px; }}
                #SideNote {{ color: {CREAM_2}; font-size: 11px; }}
                #Nav {{ background: transparent; border: none; color: {CREAM}; }}
                #Nav::item {{ padding: 9px 10px; border-radius: 8px; margin: 1px 0; }}
                #Nav::item:selected {{ background: {NAVY_SOFT}; color: white; }}
                #Nav::item:hover {{ background: {NAVY}; }}
                #Main {{ background: {PAPER}; }}
                #TopBar {{ background: {CREAM}; border: 1px solid {HAIRLINE}; border-radius: 10px; }}
                #PageTitle {{ color: {NAVY}; font: 700 18px Georgia; }}
                #SmallHeading {{ color: {NAVY}; font: 700 12px Arial; letter-spacing: .5px; }}
                #NeedsReview {{ color: {GOLD_DEEP}; font-weight: 700; padding: 8px 10px; background: #fff8e8; border: 1px solid {GOLD_LIGHT}; border-radius: 8px; }}
                #ToolDesc {{ color: {CHARCOAL_2}; padding: 0 0 4px 22px; font-size: 12px; }}
                #StatusLabel {{ color: {CHARCOAL_2}; }}
                #ToolScroll {{ border: 1px solid {HAIRLINE}; border-radius: 10px; background: {CREAM}; }}
                QLineEdit, QComboBox {{ border: 1px solid {HAIRLINE}; border-radius: 8px; padding: 6px 8px; background: white; color: {CHARCOAL}; }}
                QPushButton {{ background: {CREAM}; border: 1px solid {GOLD}; border-radius: 8px; padding: 6px 12px; color: {NAVY}; font-weight: 700; }}
                QPushButton:hover {{ background: {GOLD_LIGHT}; }}
                QPushButton:disabled {{ color: {CHARCOAL_2}; border-color: {HAIRLINE}; background: {CREAM_2}; }}
                #PrimaryButton {{ background: {GOLD}; color: {NAVY_DEEP}; border: 1px solid {GOLD}; padding: 9px 12px; font-weight: 800; }}
                #PrimaryButton:hover {{ background: {GOLD_LIGHT}; }}
                #GhostButton {{ background: transparent; border: 1px solid {HAIRLINE}; padding: 5px 12px; }}
                #GhostButton:hover {{ background: {CREAM}; }}
                QCheckBox {{ color: {CHARCOAL}; font-weight: 600; }}
                QProgressBar {{ border: 1px solid {NAVY_SOFT}; border-radius: 6px; text-align: center; background: {NAVY}; color: white; }}
                QProgressBar::chunk {{ background: {GOLD}; border-radius: 6px; }}
                QTableWidget, QListWidget {{ background: white; border: 1px solid {HAIRLINE}; gridline-color: {HAIRLINE}; }}
                QHeaderView::section {{ background: {CREAM}; color: {NAVY}; font-weight: 700; padding: 6px; border: 0; }}
                """
            )

        def set_selected_folder(self, folder: Path) -> None:
            self.selected_folder = folder.resolve()
            self.folder_path.setText(str(self.selected_folder))
            self.refresh_template_options()

        def refresh_template_options(self) -> None:
            """Rebuild the template checkboxes from the templates the folder offers."""

            previous = {key: box.isChecked() for key, box in self.template_checkboxes.items()}
            while self.templates_row.count():
                item = self.templates_row.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self.template_checkboxes = {}

            directory = generate_documents.template_dir(self.selected_folder)
            for key, path in generate_documents.available_templates(directory).items():
                label = key.replace("_", " ").title()
                if path.suffix.lower() == ".docx":
                    label += " (Word)"
                checkbox = QCheckBox(label)
                checkbox.setChecked(previous.get(key, True))
                self.templates_row.addWidget(checkbox)
                self.template_checkboxes[key] = checkbox
            self.templates_row.addStretch()

        def choose_folder(self) -> None:
            folder = QFileDialog.getExistingDirectory(
                self, "Choose client upload folder", str(self.selected_folder)
            )
            if folder:
                self.set_selected_folder(Path(folder))

        def open_clients_editor(self) -> None:
            if not self.selected_folder.is_dir():
                QMessageBox.warning(self, "Invalid folder", "Please choose a valid folder first.")
                return
            dialog = ClientsEditorDialog(self.selected_folder, self)
            if dialog.exec():
                self.status_label.setText("Clients saved to clients.json.")

        def choose_signature(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Choose signature image", str(self.selected_folder),
                "Images (*.png *.jpg *.jpeg)"
            )
            if path:
                self.signature_path_edit.setText(path)

        def choose_certificate(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Choose signing certificate", str(self.selected_folder),
                "PKCS#12 (*.p12 *.pfx)"
            )
            if path:
                self.cert_path_edit.setText(path)

        def selected_tool_keys(self) -> list[str]:
            return [
                tool.key
                for tool in tax_tools.TOOLS
                if self.tool_checkboxes[tool.key].isChecked()
            ]

        def set_all_tools(self, checked: bool) -> None:
            for checkbox in self.tool_checkboxes.values():
                checkbox.setChecked(checked)
            self.sync_group_toggles()
            self.update_selected_count()

        def apply_preset(self, keys: tuple[str, ...]) -> None:
            wanted = set(keys)
            for key, checkbox in self.tool_checkboxes.items():
                checkbox.setChecked(key in wanted)
            self.sync_group_toggles()
            self.update_selected_count()

        def set_group_tools(self, group: str, checked: bool) -> None:
            for tool in tax_tools.TOOLS:
                if tool.group == group and tool.key in self.tool_checkboxes:
                    self.tool_checkboxes[tool.key].setChecked(checked)

        def sync_group_toggles(self, _checked=None) -> None:
            """Reflect each group's checkbox as the AND of its tools (no signal loop).

            Accepts an ignored argument so it can be wired directly to QCheckBox.toggled.
            """
            for group, toggle in getattr(self, "group_checkboxes", {}).items():
                tools = [t for t in tax_tools.TOOLS if t.group == group]
                all_on = all(self.tool_checkboxes[t.key].isChecked() for t in tools)
                toggle.blockSignals(True)
                toggle.setChecked(all_on)
                toggle.blockSignals(False)

        def run_selected_tools(self) -> None:
            tool_keys = self.selected_tool_keys()
            if not tool_keys:
                QMessageBox.warning(self, "No tools selected", "Select at least one tool to run.")
                return
            if not self.selected_folder.exists() or not self.selected_folder.is_dir():
                QMessageBox.warning(self, "Invalid folder", "Please choose a valid folder.")
                return
            needs_deps = tax_tools.needs_dependencies(tool_keys)
            if needs_deps and not sort_tax_docs.check_dependencies(verbose=False):
                QMessageBox.warning(self, "Setup needed", dependency_message())
                return

            # Pre-run input checks: warn (don't block) if a selected tool lacks its inputs.
            if not self.per_client_checkbox.isChecked():
                issues = preflight.precheck(
                    self.selected_folder, tool_keys,
                    {tool.key: tool.name for tool in tax_tools.TOOLS},
                    signature_path=self.signature_path_edit.text().strip() or None,
                    cert_path=self.cert_path_edit.text().strip() or None,
                )
                if issues:
                    message = (
                        "Some selected tools may be missing what they need:\n\n• "
                        + "\n• ".join(issues)
                        + "\n\nRun anyway?"
                    )
                    if QMessageBox.question(self, "Check inputs", message) != QMessageBox.Yes:
                        return

            if needs_deps and sort_tax_docs.find_tesseract_executable() is None:
                QMessageBox.information(
                    self,
                    "Tesseract OCR needed",
                    "Tesseract OCR is needed for scanned PDFs and images. Run setup if OCR fails.",
                )

            self.run_button.setEnabled(False)
            self.progress.setRange(0, 0)
            self.progress.show()
            self.status_label.setText("Starting tools...")
            self.worker = ToolsWorker(
                tool_keys,
                self.selected_folder,
                move=self.move_checkbox.isChecked(),
                save_extracted_text=self.debug_checkbox.isChecked(),
                split_combined=self.split_checkbox.isChecked(),
                document_templates=tuple(
                    key for key, box in self.template_checkboxes.items() if box.isChecked()
                ),
                signature_path=self.signature_path_edit.text().strip() or None,
                signature_anchor=self.anchor_edit.text().strip() or sign_documents.DEFAULT_ANCHOR,
                cert_path=self.cert_path_edit.text().strip() or None,
                cert_password=self.cert_password_edit.text() or None,
                per_client=self.per_client_checkbox.isChecked(),
            )
            self.worker.status_changed.connect(self.status_label.setText)
            self.worker.finished_successfully.connect(self.on_tools_finished)
            self.worker.failed.connect(self.on_tools_failed)
            self.worker.start()

        def on_tools_finished(self, result: dict) -> None:
            self.result = result
            self.open_paths = result.get("open_paths", {})
            self.run_button.setEnabled(True)
            self.progress.hide()
            self.progress.setRange(0, 1)
            self.status_label.setText("Finished.")
            self.populate_results(result)
            for label, button in self.open_buttons.items():
                button.setEnabled(label in self.open_paths)

        def on_tools_failed(self, message: str) -> None:
            self.run_button.setEnabled(True)
            self.progress.hide()
            self.status_label.setText("Sorter failed.")
            QMessageBox.critical(self, "Sorter failed", message)

        def populate_results(self, result: dict) -> None:
            sort_result = result.get("sort")
            extract_result = result.get("extract")
            self.summary_label.setText("\n".join(result.get("tool_lines", [])) or "Run complete.")
            self.nav.setCurrentRow(self.nav.count() - 1)  # jump to the Results page

            review_lines = []
            validate_result = result.get("validate")
            if validate_result is not None:
                review_lines.append(
                    f"Config errors: {validate_result['error_count']} | "
                    f"warnings: {validate_result['warning_count']}"
                )
            import_result = result.get("import")
            if import_result is not None:
                review_lines.append(f"Clients imported: {import_result['added']}")
            intake_result = result.get("intake")
            if intake_result is not None:
                review_lines.append(
                    f"Intake clients added: {intake_result['clients_added']} | "
                    f"Responses: {intake_result['responses_found']}"
                )
            if sort_result is not None:
                review_lines.append(
                    f"Needs Review: {sort_result['needs_review_count']} | "
                    f"Low confidence/manual review: {sort_result['manual_review_count']}"
                )
            if extract_result is not None:
                review_lines.append(
                    f"Forms extracted: {extract_result['total_forms']} | "
                    f"Flagged for manual entry: {extract_result['review_count']}"
                )
            diagnostics_result = result.get("diagnostics")
            if diagnostics_result is not None:
                review_lines.append(f"Diagnostics warnings: {diagnostics_result['warning_count']}")
            packet_result = result.get("packet")
            if packet_result is not None:
                review_lines.append(f"Filed forms read: {packet_result['clients_updated']} client(s)")
            checklist_result = result.get("checklist")
            if checklist_result is not None:
                review_lines.append(f"Documents still missing: {checklist_result['total_missing']}")
            invoice_result = result.get("invoice")
            if invoice_result is not None:
                review_lines.append(
                    f"Invoices computed: {invoice_result['invoiced_count']} | "
                    f"Total billed: {invoice_result['grand_total']}"
                )
            generate_result = result.get("generate")
            if generate_result is not None:
                review_lines.append(
                    f"Documents generated: {generate_result['document_count']} | "
                    f"With blank fields: {len(generate_result['warnings'])}"
                )
            sign_result = result.get("sign")
            if sign_result is not None:
                review_lines.append(f"PDFs signed: {sign_result['signed_count']}")
            certsign_result = result.get("certsign")
            if certsign_result is not None:
                review_lines.append(f"PDFs certified: {certsign_result['signed_count']}")
            engagement_result = result.get("engagement")
            if engagement_result is not None:
                review_lines.append(f"Engagement letters outstanding: {engagement_result['outstanding_count']}")
            form8879_result = result.get("form8879")
            if form8879_result is not None:
                review_lines.append(f"8879s outstanding: {form8879_result['outstanding_count']}")
            filing_result = result.get("filing")
            if filing_result is not None:
                review_lines.append(f"Returns not filed: {filing_result['outstanding_count']}")
            payments_result = result.get("payments")
            if payments_result is not None:
                review_lines.append(f"AR outstanding: {payments_result['total_outstanding']}")
            reminders_result = result.get("reminders")
            if reminders_result is not None:
                review_lines.append(f"Reminders drafted: {reminders_result['reminder_count']}")
            email_result = result.get("email")
            if email_result is not None:
                review_lines.append(f"Email drafts: {email_result['draft_count']}")
            rollover_result = result.get("rollover")
            if rollover_result is not None:
                review_lines.append(
                    f"Rolled forward to {rollover_result['new_year']}: {rollover_result['client_count']} client(s)"
                )
            pdftools_result = result.get("pdftools")
            if pdftools_result is not None:
                review_lines.append(
                    f"PDFs merged: {pdftools_result['merged_inputs']} | split files: {pdftools_result['split_files']}"
                )
            encyro_result = result.get("encyro")
            if encyro_result is not None:
                review_lines.append(f"Encyro packets: {encyro_result['client_count']}")
            retention_result = result.get("retention")
            if retention_result is not None:
                review_lines.append(f"Retention archives: {retention_result['archived_count']}")
            self.needs_review_label.setText("     ".join(review_lines))

            self.category_list.clear()
            if sort_result is not None:
                for category, count in sort_result["category_counts"].items():
                    self.category_list.addItem(f"{category}: {count}")
            elif extract_result is not None:
                for category, count in extract_result["counts_by_category"].items():
                    self.category_list.addItem(f"{category}: {count}")

            rows = sort_result["rows"] if sort_result is not None else []
            review_background = QColor("#FFF8E8")
            self.results_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                values = [
                    row.get("Original File Name", ""),
                    row.get("Detected Category", ""),
                    row.get("Confidence", ""),
                    row.get("Notes", ""),
                ]
                highlight = is_manual_review_row(row)
                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    if highlight:
                        item.setBackground(review_background)
                    self.results_table.setItem(row_index, column_index, item)
            self.results_table.resizeColumnsToContents()

        def open_result_path(self, key: str) -> None:
            path = self.open_paths.get(key, "")
            if path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def show_missing_pyside_message() -> int:
    """Show a no-console message when PySide6 is missing."""

    message = (
        "PySide6 is not installed.\n\n"
        "Run Setup Tax Document Sorter.bat, or run:\n"
        "py -3.12 setup_tax_doc_sorter.py"
    )
    if sys.platform.startswith("win"):
        ctypes.windll.user32.MessageBoxW(None, message, "Tax Document Sorter", 0x10)
    else:
        print(message)
    return 1


def main() -> int:
    """Start the desktop GUI."""

    if not PYSIDE_AVAILABLE:
        return show_missing_pyside_message()
    app = QApplication(sys.argv)
    window = TaxDocumentSorterWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
