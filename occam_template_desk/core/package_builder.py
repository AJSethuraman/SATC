from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime
from .audit import build_audit, write_json, now_iso
from .renderer import render_docx_template, render_email_template
from .simple_xlsx import write_xlsx


def sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._ -]+", "", name).strip().replace(" ", "_")
    return clean[:80] or "Untitled"

def create_output_package_folder(output_root: str | Path, client_name: str, template_name: str) -> Path:
    folder = Path(output_root) / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sanitize_filename(client_name)}_{sanitize_filename(Path(template_name).stem)}"
    folder.mkdir(parents=True, exist_ok=False)
    return folder

def write_validation_report(path: str | Path, fields: list[dict], validation: dict, audit: dict) -> str:
    rows_summary = [
        {"Item": "Run ID", "Value": audit.get("run_id", "")},
        {"Item": "Status", "Value": validation.get("status", "")},
        {"Item": "Client", "Value": audit.get("client_name", "")},
        {"Item": "Template", "Value": audit.get("template_name", "")},
        {"Item": "Timestamp", "Value": audit.get("timestamp", "")},
    ]
    rows_validation = []
    for b in validation.get("blockers", []):
        rows_validation.append({"Type": "Blocked", "Message": b, "Next Action": "Resolve before generation."})
    for w in validation.get("warnings", []):
        rows_validation.append({"Type": "Warning", "Message": w, "Next Action": "Review before sending or filing."})
    if not rows_validation:
        rows_validation.append({"Type": "Ready", "Message": "No blockers or warnings.", "Next Action": "Ready."})
    rows_audit = [{"Key": k, "Value": json.dumps(v) if isinstance(v, (list, dict)) else v} for k, v in audit.items()]
    return str(write_xlsx(path, {"Summary": rows_summary, "Fields": fields or [{"field":"","value":"","source":"","status":""}], "Validation Results": rows_validation, "Audit Log": rows_audit}, styles=True))

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
    audit = build_audit(str(template), template_type, client, validation_dict, generated_files, outlook_status)
    snapshot = {"selected_template": str(template), "selected_client": client, "detected_placeholders": detected_placeholders or [], "final_values": values, "field_sources": fields, "user_overrides": user_overrides or {}, "timestamp": now_iso()}
    write_json(package_dir / "input_snapshot.json", snapshot)
    write_json(package_dir / "rendered_values.json", values)
    write_json(package_dir / "audit_log.json", audit)
    if outlook_status:
        write_json(package_dir / "outlook_status.json", outlook_status)
    report_path = write_validation_report(package_dir / "validation_report.xlsx", fields, validation_dict, audit)
    return {"package_dir": str(package_dir), "rendered": rendered, "audit": audit, "validation_report": report_path, "generated_files": generated_files + [str(package_dir / "input_snapshot.json"), str(package_dir / "audit_log.json"), str(package_dir / "rendered_values.json"), report_path]}

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
