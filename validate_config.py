#!/usr/bin/env python3
"""Pre-flight validation of the folder's configuration and client data.

A read-only leaf tool: it checks clients.json/csv, firm.json, fee_schedule.json,
intake_fields.json, and checklist_map.json for problems that would otherwise cause
silent surprises later (a client with no name, a service that isn't in the fee
schedule, a checklist mapping to an unknown category, etc.) and writes a report to
Validation/. It changes nothing.

The checks are pure functions over already-loaded data (easy to test in isolation);
run_validation is the thin layer that loads the files and writes the report.
Standard library only.
"""

from __future__ import annotations

import json
from pathlib import Path

import generate_documents
import sort_tax_docs

VALIDATION_FOLDER_NAME = "Validation"
REPORT_FILENAME = "validation.txt"
ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"
KNOWN_FIELD_TYPES = {"text", "email", "tel", "number", "date", "textarea", "select", "checkboxes"}


def _finding(area: str, severity: str, message: str) -> dict:
    return {"area": area, "severity": severity, "message": message}


def check_clients(clients: list[dict]) -> list[dict]:
    findings: list[dict] = []
    if not clients:
        return [_finding("clients", ERROR, "No client records found.")]

    emails: dict[str, int] = {}
    slugs: dict[str, list[str]] = {}
    for index, client in enumerate(clients, start=1):
        name = client.get("client_name") or client.get("name")
        label = name or f"record {index}"
        if not name:
            findings.append(_finding("clients", ERROR, f"Record {index}: missing client_name."))
        if not client.get("email"):
            findings.append(_finding("clients", INFO, f"{label}: no email (email/reminders will skip this client)."))
        for field in ("expected_documents", "services"):
            if field in client and not isinstance(client[field], list):
                findings.append(_finding("clients", WARNING, f"{label}: '{field}' should be a list."))
        email = str(client.get("email", "")).lower()
        if email:
            emails[email] = emails.get(email, 0) + 1
        slug = generate_documents.client_slug(client, index)
        slugs.setdefault(slug, []).append(label)

    for email, count in emails.items():
        if count > 1:
            findings.append(_finding("clients", WARNING, f"Email '{email}' is used by {count} clients."))
    for slug, labels in slugs.items():
        if len(labels) > 1:
            findings.append(_finding(
                "clients", WARNING,
                f"Clients {', '.join(labels)} share the slug '{slug}' (batch mode will disambiguate)."
            ))
    return findings


def check_firm(firm: dict) -> list[dict]:
    if not firm:
        return [_finding("firm", INFO, "No firm.json; firm fields will be blank in documents.")]
    findings = []
    for field in ("firm_name", "firm_email"):
        if not firm.get(field):
            findings.append(_finding("firm", INFO, f"firm.json is missing '{field}'."))
    return findings


def check_fee_schedule(schedule: dict, clients: list[dict]) -> list[dict]:
    findings: list[dict] = []
    if not schedule:
        return findings
    for key, entry in schedule.items():
        price = entry.get("price") if isinstance(entry, dict) else None
        if not isinstance(price, (int, float)):
            findings.append(_finding("fee_schedule", ERROR, f"Service '{key}' has a non-numeric price."))
    for index, client in enumerate(clients, start=1):
        label = client.get("client_name") or f"record {index}"
        for service in client.get("services", []) or []:
            key = service if isinstance(service, str) else (service or {}).get("service")
            inline = isinstance(service, dict) and "price" in service
            if key and key not in schedule and not inline:
                findings.append(_finding("fee_schedule", WARNING, f"{label}: service '{key}' is not in the fee schedule."))
    return findings


def check_intake_schema(schema: list[dict]) -> list[dict]:
    findings: list[dict] = []
    if not schema:
        return findings
    for field in schema:
        name = field.get("name", "?")
        if not field.get("name"):
            findings.append(_finding("intake_fields", ERROR, "A field is missing 'name'."))
        ftype = field.get("type", "text")
        if ftype not in KNOWN_FIELD_TYPES:
            findings.append(_finding("intake_fields", WARNING, f"Field '{name}': unknown type '{ftype}'."))
        if ftype in ("select", "checkboxes") and not field.get("options"):
            findings.append(_finding("intake_fields", WARNING, f"Field '{name}': '{ftype}' has no options."))
    return findings


def check_checklist_map(mapping: dict, category_keys) -> list[dict]:
    findings: list[dict] = []
    if not mapping:
        return findings
    valid = set(category_keys)
    for label, categories in mapping.items():
        for category in (categories if isinstance(categories, list) else [categories]):
            if category not in valid:
                findings.append(_finding("checklist_map", WARNING, f"'{label}' maps to unknown category '{category}'."))
    return findings


def _load_json(path: Path):
    """Return (data, error). error is a finding if the file exists but is invalid."""

    if not path.exists():
        return None, None
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, _finding(path.name, ERROR, f"{path.name} is not valid JSON ({exc}).")


def run_validation(input_folder, status_callback=None) -> dict:
    """Validate config + client data; write a report. Read-only."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)
    if status_callback:
        status_callback("Validating configuration and client data")

    findings: list[dict] = []
    data_file = generate_documents.find_client_data_file(input_folder)
    clients: list[dict] = []
    if data_file is None:
        findings.append(_finding("clients", WARNING, "No clients.json or clients.csv found."))
    else:
        try:
            clients = generate_documents.load_clients(data_file)
            findings.extend(check_clients(clients))
        except Exception as exc:
            findings.append(_finding("clients", ERROR, f"Could not read {data_file.name} ({exc})."))

    findings.extend(check_firm(generate_documents.load_firm_settings(input_folder)))

    fee_schedule, error = _load_json(input_folder / "fee_schedule.json")
    findings.append(error) if error else findings.extend(check_fee_schedule(fee_schedule or {}, clients))

    intake_schema, error = _load_json(input_folder / "intake_fields.json")
    findings.append(error) if error else findings.extend(check_intake_schema(intake_schema or []))

    checklist_map, error = _load_json(input_folder / "checklist_map.json")
    findings.append(error) if error else findings.extend(
        check_checklist_map(checklist_map or {}, sort_tax_docs.CATEGORY_FOLDERS.keys())
    )

    errors = sum(1 for f in findings if f["severity"] == ERROR)
    warnings = sum(1 for f in findings if f["severity"] == WARNING)

    validation_folder = output_folder / VALIDATION_FOLDER_NAME
    validation_folder.mkdir(exist_ok=True)
    report_path = validation_folder / REPORT_FILENAME
    lines = ["Configuration validation", "=" * 32,
             f"{errors} error(s), {warnings} warning(s), {len(findings) - errors - warnings} note(s).", ""]
    lines += [f"[{f['severity']}] {f['area']}: {f['message']}" for f in findings] or ["No issues found."]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "tool": "validate",
        "output_folder": output_folder,
        "validation_folder": validation_folder,
        "report_path": report_path,
        "findings": findings,
        "error_count": errors,
        "warning_count": warnings,
        "summary": (
            f"Validated configuration: {errors} error(s), {warnings} warning(s)."
            + (" Fix errors before running other tools." if errors else "")
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate folder configuration and client data (read-only).")
    parser.add_argument("input_folder", help="Folder containing clients.json and config files.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_validation(folder, status_callback=print)
    print(result["summary"])
    for finding in result["findings"]:
        print(f"  [{finding['severity']}] {finding['area']}: {finding['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
