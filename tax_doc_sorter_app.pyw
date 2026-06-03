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

import generate_documents
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
        "intake": None,
        "extract": None,
        "checklist": None,
        "invoice": None,
        "generate": None,
        "sign": None,
        "email": None,
        "encyro": None,
    }

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

    return summary


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

        def run(self) -> None:
            try:
                context = tax_tools.ToolContext(
                    input_folder=self.input_folder,
                    move=self.move,
                    save_extracted_text=self.save_extracted_text,
                    split_combined=self.split_combined,
                    document_templates=self.document_templates,
                    signature_path=self.signature_path,
                    signature_anchor=self.signature_anchor,
                    status_callback=self.status_changed.emit,
                )
                results = tax_tools.run_tools(self.tool_keys, context)
                self.status_changed.emit("Summarizing results...")
                self.finished_successfully.emit(build_run_summary(results))
            except Exception as exc:
                self.failed.emit(str(exc))


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
            self.setWindowTitle("SATC Tax Document Sorter")
            self.resize(1120, 780)
            self.build_ui()
            self.apply_styles()
            self.set_selected_folder(self.selected_folder)

        def build_ui(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)
            root = QVBoxLayout(central)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            header = QFrame(objectName="Header")
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(34, 28, 34, 28)
            mark = QLabel("SATC", objectName="BrandMark")
            mark.setAlignment(Qt.AlignCenter)
            header_text = QVBoxLayout()
            eyebrow = QLabel("LOCAL DOCUMENT WORKFLOW", objectName="Eyebrow")
            title = QLabel("Tax Document Sorter", objectName="Title")
            subtitle = QLabel(
                "Organize client tax documents into review-ready folders.",
                objectName="Subtitle",
            )
            header_text.addWidget(eyebrow)
            header_text.addWidget(title)
            header_text.addWidget(subtitle)
            header_layout.addWidget(mark)
            header_layout.addLayout(header_text, stretch=1)
            root.addWidget(header)

            body = QWidget(objectName="Body")
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(28, 26, 28, 28)
            body_layout.setSpacing(18)
            root.addWidget(body, stretch=1)

            folder_card = QFrame(objectName="Card")
            folder_layout = QGridLayout(folder_card)
            folder_layout.setContentsMargins(24, 22, 24, 22)
            folder_layout.setHorizontalSpacing(12)
            folder_layout.setVerticalSpacing(12)
            folder_title = QLabel("Choose the client upload folder", objectName="SectionTitle")
            self.folder_path = QLineEdit()
            self.folder_path.setReadOnly(True)
            choose_button = QPushButton("Choose Folder")
            choose_button.clicked.connect(self.choose_folder)
            default_button = QPushButton("Use Default Uploads Folder")
            default_button.clicked.connect(lambda: self.set_selected_folder(ensure_default_uploads_folder()))
            safety = QLabel("Files are copied by default. Originals are not deleted.", objectName="SafetyNote")
            folder_layout.addWidget(folder_title, 0, 0, 1, 3)
            folder_layout.addWidget(self.folder_path, 1, 0, 1, 3)
            folder_layout.addWidget(choose_button, 2, 0)
            folder_layout.addWidget(default_button, 2, 1)
            folder_layout.addWidget(safety, 2, 2)
            body_layout.addWidget(folder_card)

            tools_card = QFrame(objectName="Card")
            tools_layout = QVBoxLayout(tools_card)
            tools_layout.setContentsMargins(24, 20, 24, 20)
            tools_layout.setSpacing(6)
            tools_layout.addWidget(QLabel("Choose tools to run", objectName="SectionTitle"))
            tools_layout.addWidget(
                QLabel(
                    "Select one or more tools. They run in order, top to bottom.",
                    objectName="StatusLabel",
                )
            )
            for tool in tax_tools.TOOLS:
                checkbox = QCheckBox(tool.name)
                checkbox.setChecked(True)
                description = QLabel(tool.description, objectName="ToolDesc")
                description.setWordWrap(True)
                tools_layout.addWidget(checkbox)
                tools_layout.addWidget(description)
                self.tool_checkboxes[tool.key] = checkbox
            body_layout.addWidget(tools_card)

            controls = QFrame(objectName="Card")
            controls_layout = QVBoxLayout(controls)
            controls_layout.setContentsMargins(24, 20, 24, 20)
            self.advanced_toggle = QToolButton(text="Advanced Options")
            self.advanced_toggle.setCheckable(True)
            self.advanced_toggle.setChecked(False)
            self.advanced_toggle.clicked.connect(self.toggle_advanced)
            self.advanced_panel = QWidget()
            advanced_layout = QVBoxLayout(self.advanced_panel)
            advanced_layout.setContentsMargins(0, 8, 0, 0)
            advanced_layout.setSpacing(10)

            flags_row = QHBoxLayout()
            self.move_checkbox = QCheckBox("Move files instead of copy")
            self.split_checkbox = QCheckBox("Split combined PDFs (multi-form)")
            self.split_checkbox.setChecked(True)
            self.debug_checkbox = QCheckBox("Save extracted text debug files")
            flags_row.addWidget(self.move_checkbox)
            flags_row.addWidget(self.split_checkbox)
            flags_row.addWidget(self.debug_checkbox)
            flags_row.addStretch()
            advanced_layout.addLayout(flags_row)

            advanced_layout.addWidget(
                QLabel("Templates to generate (drop .html or .docx files in the folder)",
                       objectName="SmallHeading")
            )
            self.templates_row = QHBoxLayout()
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

            self.advanced_panel.hide()

            run_row = QHBoxLayout()
            self.run_button = QPushButton("Run Selected Tools", objectName="PrimaryButton")
            self.run_button.clicked.connect(self.run_selected_tools)
            self.status_label = QLabel("Ready.", objectName="StatusLabel")
            run_row.addWidget(self.run_button)
            run_row.addWidget(self.status_label, stretch=1)
            self.progress = QProgressBar()
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.progress.hide()
            controls_layout.addWidget(self.advanced_toggle)
            controls_layout.addWidget(self.advanced_panel)
            controls_layout.addLayout(run_row)
            controls_layout.addWidget(self.progress)
            body_layout.addWidget(controls)

            self.results_card = QFrame(objectName="Card")
            results_layout = QVBoxLayout(self.results_card)
            results_layout.setContentsMargins(24, 22, 24, 22)
            self.summary_label = QLabel("Run the sorter to see results.", objectName="SectionTitle")
            self.needs_review_label = QLabel("", objectName="NeedsReview")
            self.category_list = QListWidget()
            self.results_table = QTableWidget(0, 4)
            self.results_table.setHorizontalHeaderLabels(
                ["Original File Name", "Detected Category", "Confidence", "Notes"]
            )
            self.results_table.horizontalHeader().setStretchLastSection(True)
            action_row = QHBoxLayout()
            button_labels = [
                "Open Organized Folder",
                "Open Intake Folder",
                "Open Inventory",
                "Open Log File",
                "Open Extracted Data",
                "Open Drake Export",
                "Open Checklists",
                "Open Invoices",
                "Open Generated Documents",
                "Open Signed Documents",
                "Open Email Drafts",
                "Open Encyro Packets",
            ]
            for label in button_labels:
                button = QPushButton(label)
                button.setEnabled(False)
                button.clicked.connect(lambda _checked=False, key=label: self.open_result_path(key))
                action_row.addWidget(button)
                self.open_buttons[label] = button
            action_row.addStretch()
            results_layout.addWidget(self.summary_label)
            results_layout.addWidget(self.needs_review_label)
            results_layout.addWidget(QLabel("Count by category", objectName="SmallHeading"))
            results_layout.addWidget(self.category_list)
            results_layout.addLayout(action_row)
            results_layout.addWidget(QLabel("Inventory preview", objectName="SmallHeading"))
            results_layout.addWidget(self.results_table, stretch=1)
            body_layout.addWidget(self.results_card, stretch=1)

        def apply_styles(self) -> None:
            heading_font = QFont("Cormorant Garamond")
            if not heading_font.exactMatch():
                heading_font = QFont("Georgia")
            self.setStyleSheet(
                f"""
                QMainWindow {{ background: {CREAM}; color: {INK}; }}
                #Header {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {NAVY_SOFT}, stop:1 {NAVY_DEEP}); border-bottom: 4px solid {GOLD}; }}
                #BrandMark {{ color: {GOLD_LIGHT}; border: 1px solid {GOLD_LIGHT}; min-width: 76px; min-height: 76px; font: 24px Georgia; letter-spacing: 2px; }}
                #Eyebrow {{ color: {GOLD_LIGHT}; font: 700 12px Arial; letter-spacing: 2px; }}
                #Title {{ color: {PAPER}; font: 56px Georgia; }}
                #Subtitle {{ color: {CREAM_2}; font-size: 17px; }}
                #Body {{ background: {CREAM}; }}
                #Card {{ background: {PAPER}; border: 1px solid {HAIRLINE}; border-radius: 16px; }}
                #SectionTitle {{ color: {NAVY}; font: 30px Georgia; }}
                #SmallHeading {{ color: {NAVY}; font: 700 14px Arial; }}
                #SafetyNote {{ color: {GOLD_DEEP}; font-weight: 700; }}
                #NeedsReview {{ color: {GOLD_DEEP}; font-weight: 800; padding: 8px; background: #fff8e8; border: 1px solid {GOLD_LIGHT}; border-radius: 10px; }}
                QLineEdit {{ border: 1px solid {HAIRLINE}; border-radius: 10px; padding: 10px; background: white; color: {CHARCOAL}; }}
                QPushButton {{ background: {CREAM}; border: 1px solid {GOLD}; border-radius: 18px; padding: 10px 18px; color: {NAVY}; font-weight: 800; }}
                QPushButton:hover {{ background: {GOLD_LIGHT}; }}
                QPushButton:disabled {{ color: {CHARCOAL_2}; border-color: {HAIRLINE}; background: {CREAM_2}; }}
                #PrimaryButton {{ background: {NAVY}; color: white; border: 1px solid {NAVY}; }}
                QToolButton {{ color: {NAVY}; font-weight: 800; border: none; }}
                QCheckBox {{ color: {CHARCOAL}; font-weight: 600; }}
                #ToolDesc {{ color: {CHARCOAL_2}; padding: 0 0 6px 22px; }}
                #StatusLabel {{ color: {CHARCOAL_2}; }}
                QProgressBar {{ border: 1px solid {HAIRLINE}; border-radius: 8px; text-align: center; }}
                QProgressBar::chunk {{ background: {GOLD}; border-radius: 8px; }}
                QTableWidget, QListWidget {{ background: white; border: 1px solid {HAIRLINE}; gridline-color: {HAIRLINE}; }}
                QHeaderView::section {{ background: {CREAM}; color: {NAVY}; font-weight: 800; padding: 8px; border: 0; }}
                """
            )
            self.summary_label.setFont(heading_font)

        def toggle_advanced(self) -> None:
            self.advanced_panel.setVisible(self.advanced_toggle.isChecked())

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

        def choose_signature(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Choose signature image", str(self.selected_folder),
                "Images (*.png *.jpg *.jpeg)"
            )
            if path:
                self.signature_path_edit.setText(path)

        def selected_tool_keys(self) -> list[str]:
            return [
                tool.key
                for tool in tax_tools.TOOLS
                if self.tool_checkboxes[tool.key].isChecked()
            ]

        def run_selected_tools(self) -> None:
            tool_keys = self.selected_tool_keys()
            if not tool_keys:
                QMessageBox.warning(self, "No tools selected", "Select at least one tool to run.")
                return
            if not self.selected_folder.exists() or not self.selected_folder.is_dir():
                QMessageBox.warning(self, "Invalid folder", "Please choose a valid folder.")
                return
            if not sort_tax_docs.check_dependencies(verbose=False):
                QMessageBox.warning(self, "Setup needed", dependency_message())
                return
            if sort_tax_docs.find_tesseract_executable() is None:
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

            review_lines = []
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
            email_result = result.get("email")
            if email_result is not None:
                review_lines.append(f"Email drafts: {email_result['draft_count']}")
            encyro_result = result.get("encyro")
            if encyro_result is not None:
                review_lines.append(f"Encyro packets: {encyro_result['client_count']}")
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
