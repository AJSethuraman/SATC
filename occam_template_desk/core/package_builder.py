from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from datetime import datetime

from .audit import build_audit, write_json, now_iso
from .renderer import render_docx_template, render_email_template, scan_rendered_output_for_placeholders
from .simple_xlsx import write_xlsx

NAVY = "0B1F3A"
GOLD = "C9A227"
GRAY = "E5E7EB"
GREEN = "C6EFCE"
AMBER = "FFEB9C"
RED = "FFC7CE"


def sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._ -]+", "", name).strip().replace(" ", "_")
    return clean[:80] or "Untitled"


def create_output_package_folder(output_root: str | Path, client_name: str, template_name: str) -> Path:
    folder = Path(output_root) / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sanitize_filename(client_name)}_{sanitize_filename(Path(template_name).stem)}"
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def _report_rows(fields: list[dict], validation: dict, audit: dict) -> dict[str, list[dict]]:
    rows_summary = [
        {"Item": "Run ID", "Value": audit.get("run_id", "")},
        {"Item": "Status", "Value": validation.get("status", "")},
        {"Item": "Client", "Value": audit.get("client_name", "")},
        {"Item": "Template", "Value": audit.get("template_name", "")},
        {"Item": "Timestamp", "Value": audit.get("timestamp", "")},
        {"Item": "Next Actions", "Value": "; ".join(validation.get("next_actions", []))},
    ]
    rows_validation = []
    for blocker in validation.get("blockers", []):
        rows_validation.append({"Type": "Blocked", "Message": blocker, "Next Action": "Resolve before generation or use."})
    for warning in validation.get("warnings", []):
        rows_validation.append({"Type": "Warning", "Message": warning, "Next Action": "Review before sending or filing."})
    if not rows_validation:
        rows_validation.append({"Type": "Ready", "Message": "No blockers or warnings.", "Next Action": "Ready."})
    rows_audit = [{"Key": key, "Value": json.dumps(value) if isinstance(value, (list, dict)) else value} for key, value in audit.items()]
    return {
        "Summary": rows_summary,
        "Fields": fields or [{"field": "", "value": "", "source": "", "status": ""}],
        "Validation Results": rows_validation,
        "Audit Log": rows_audit,
    }


def _openpyxl_available() -> bool:
    return importlib.util.find_spec("openpyxl") is not None


def _status_fill(status: str):
    from openpyxl.styles import PatternFill

    normalized = str(status).lower()
    if "ready" in normalized or "success" in normalized:
        return PatternFill("solid", fgColor=GREEN)
    if "blocked" in normalized or "error" in normalized:
        return PatternFill("solid", fgColor=RED)
    if "warning" in normalized or "needs review" in normalized:
        return PatternFill("solid", fgColor=AMBER)
    return PatternFill("solid", fgColor=GRAY)


def _write_openpyxl_report(path: Path, rows_by_sheet: dict[str, list[dict]], validation: dict) -> str:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    workbook.remove(workbook.active)
    navy_fill = PatternFill("solid", fgColor=NAVY)
    gold_fill = PatternFill("solid", fgColor=GOLD)
    gray_fill = PatternFill("solid", fgColor=GRAY)
    white_font = Font(color="FFFFFF", bold=True)
    dark_font = Font(color=NAVY, bold=True)

    for sheet_name, rows in rows_by_sheet.items():
        ws = workbook.create_sheet(sheet_name)
        headers = list(rows[0].keys()) if rows else ["Item", "Value"]
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(headers)))
        title = ws.cell(row=1, column=1, value=f"Occam Template Desk - {sheet_name}")
        title.fill = navy_fill
        title.font = white_font
        title.alignment = Alignment(horizontal="center")
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col, value=header)
            cell.fill = gray_fill
            cell.font = dark_font
        for row_index, row in enumerate(rows, 3):
            for col, header in enumerate(headers, 1):
                value = row.get(header, "")
                cell = ws.cell(row=row_index, column=col, value=value)
                if header.lower() in {"status", "type"} or str(value) in {"Ready", "Needs Review", "Blocked", "Warning", "Error"}:
                    cell.fill = _status_fill(str(value))
                if any(token in header.lower() for token in ["amount", "fee"]):
                    cell.number_format = '$#,##0.00'
                if "date" in header.lower() or header.lower() == "timestamp":
                    cell.number_format = 'yyyy-mm-dd'
        if sheet_name == "Summary":
            status_cell = ws.cell(row=4, column=2)
            status_cell.fill = _status_fill(validation.get("status", ""))
            ws.cell(row=4, column=1).fill = gold_fill
            ws.cell(row=4, column=1).font = dark_font
        ws.freeze_panes = "A3"
        for col in range(1, len(headers) + 1):
            width = max(14, min(60, max(len(str(ws.cell(row=row, column=col).value or "")) for row in range(1, ws.max_row + 1)) + 3))
            ws.column_dimensions[get_column_letter(col)].width = width
    workbook.save(path)
    return str(path)


def write_validation_report(path: str | Path, fields: list[dict], validation: dict, audit: dict) -> str:
    path = Path(path)
    rows_by_sheet = _report_rows(fields, validation, audit)
    if _openpyxl_available():
        return _write_openpyxl_report(path, rows_by_sheet, validation)
    return str(write_xlsx(path, rows_by_sheet, styles=True))


def _post_render_placeholder_warnings(rendered: dict) -> list[str]:
    warnings = []
    seen = set()
    for file_path in rendered.get("generated_files", []):
        path = Path(file_path)
        if path.name == "email_metadata.json":
            continue
        if path.suffix.lower() not in {".docx", ".txt", ".html", ".md"}:
            continue
        remaining = scan_rendered_output_for_placeholders(path)
        if remaining:
            token_list = ", ".join(f"{{{{{token}}}}}" for token in remaining)
            message = f"Rendered output still contains unreplaced placeholder(s) in {path.name}: {token_list}."
            if message not in seen:
                seen.add(message)
                warnings.append(message)
    return warnings


def build_output_package(template_path: str, template_type: str, values: dict, fields: list[dict], validation, client: dict, output_root: str | Path, outlook_status: dict | None = None, detected_placeholders: list[str] | None = None, user_overrides: dict | None = None) -> dict:
    if validation.blockers:
        raise ValueError("Blocked runs cannot generate output packages.")
    template = Path(template_path)
    package_dir = create_output_package_folder(output_root, client.get("Client Name", "Client"), template.name)
    if template_type == "email":
        rendered = render_email_template(template, values, package_dir, values.get("Client Email", ""), validation.status)
    else:
        rendered = render_docx_template(template, values, package_dir, f"{sanitize_filename(client.get('Client Name','Client'))}_{sanitize_filename(template.stem)}.docx")
    generated_files = rendered.get("generated_files", [])
    validation_dict = validation.to_dict()
    post_render_warnings = _post_render_placeholder_warnings(rendered)
    if post_render_warnings:
        validation_dict["warnings"] = validation_dict.get("warnings", []) + post_render_warnings
        if validation_dict.get("status") == "Ready":
            validation_dict["status"] = "Needs Review"
        validation_dict["next_actions"] = validation_dict.get("next_actions", []) + ["Review unreplaced placeholders in the rendered output before use."]
    audit = build_audit(str(template), template_type, client, validation_dict, generated_files, outlook_status)
    snapshot = {"selected_template": str(template), "selected_client": client, "detected_placeholders": detected_placeholders or [], "final_values": values, "field_sources": fields, "user_overrides": user_overrides or {}, "post_render_warnings": post_render_warnings, "timestamp": now_iso()}
    write_json(package_dir / "input_snapshot.json", snapshot)
    write_json(package_dir / "rendered_values.json", values)
    write_json(package_dir / "audit_log.json", audit)
    if outlook_status:
        write_json(package_dir / "outlook_status.json", outlook_status)
    report_path = write_validation_report(package_dir / "validation_report.xlsx", fields, validation_dict, audit)
    return {"package_dir": str(package_dir), "rendered": rendered, "audit": audit, "validation": validation_dict, "validation_report": report_path, "audit_log": str(package_dir / "audit_log.json"), "generated_files": generated_files + [str(package_dir / "input_snapshot.json"), str(package_dir / "audit_log.json"), str(package_dir / "rendered_values.json"), report_path]}


def update_outlook_status(package_dir: str | Path, status: dict) -> None:
    package_dir = Path(package_dir)
    write_json(package_dir / "outlook_status.json", status)
    audit_path = package_dir / "audit_log.json"
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["outlook_draft_status"] = status
        write_json(audit_path, audit)


def list_recent_packages(output_root: str | Path, limit: int = 20) -> list[dict]:
    root = Path(output_root)
    if not root.exists():
        return []
    packages = []
    for folder in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        audit_path = folder / "audit_log.json"
        data = {"folder": str(folder), "timestamp": "", "status": "", "client": "", "template": "", "generated_files": []}
        if audit_path.exists():
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            data.update({"timestamp": audit.get("timestamp", ""), "status": audit.get("validation_status", ""), "client": audit.get("client_name", ""), "template": audit.get("template_name", ""), "generated_files": audit.get("generated_files", [])})
        packages.append(data)
    return packages
