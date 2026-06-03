#!/usr/bin/env python3
"""Dynamic client intake: a fillable form plus response compilation into clients.json.

This tool does two things on each run, both fully local:

1. Generates a self-contained ``Intake/intake_form.html`` from a *dynamic* field
   schema (``intake_fields.json`` in the folder, created from a sensible default on
   first run so you can edit the questions). The form runs entirely in the browser
   and, on submit, downloads the answers as ``<name>_intake.json`` -- no server.

2. Compiles any ``*_intake.json`` response files found in the folder into
   ``clients.json`` (the data file the rest of the suite reads), appending only
   clients that are not already present so hand-edited data is never overwritten.

So the loop is: run the tool, send clients the form, drop their returned JSON in
the folder, run the tool again -- now clients.json is ready for the other tools.
"""

from __future__ import annotations

import json
from pathlib import Path

import sort_tax_docs

INTAKE_FOLDER_NAME = "Intake"
SCHEMA_FILENAME = "intake_fields.json"
FORM_FILENAME = "intake_form.html"
RESPONSE_GLOB = "*_intake.json"

# Each field: name (the clients.json key), label, type, and optional required/options.
# Types: text, email, tel, number, date, textarea, select (needs options),
#        checkboxes (multi-select -> a list of strings).
DEFAULT_SCHEMA: list[dict] = [
    {"name": "client_name", "label": "Full name", "type": "text", "required": True},
    {"name": "email", "label": "Email", "type": "email", "required": True},
    {"name": "phone", "label": "Phone", "type": "tel"},
    {"name": "tax_year", "label": "Tax year", "type": "text"},
    {
        "name": "filing_status",
        "label": "Filing status",
        "type": "select",
        "options": [
            "Single",
            "Married Filing Jointly",
            "Married Filing Separately",
            "Head of Household",
            "Qualifying Surviving Spouse",
        ],
    },
    {"name": "dependents", "label": "Number of dependents", "type": "number"},
    {"name": "address", "label": "Mailing address", "type": "textarea"},
    {
        "name": "expected_documents",
        "label": "Documents you expect to provide",
        "type": "checkboxes",
        "options": [
            "W-2",
            "1099-NEC",
            "1099-INT",
            "1099-DIV",
            "1099-R",
            "1098 (Mortgage)",
            "1098-T",
            "SSA-1099",
            "K-1",
            "Other",
        ],
    },
    {
        "name": "services",
        "label": "Additional services needed",
        "type": "checkboxes",
        # Values match fee_schedule.json keys so invoices price automatically.
        "options": [
            {"label": "State return", "value": "state_return"},
            {"label": "Schedule C (self-employment)", "value": "schedule_c"},
            {"label": "Schedule E (rental property)", "value": "schedule_e"},
            {"label": "Itemized deductions (Schedule A)", "value": "itemized_deductions"},
            {"label": "Amended return", "value": "amended_return"},
            {"label": "Extension filing", "value": "extension_filing"},
        ],
    },
    {"name": "notes", "label": "Anything else we should know?", "type": "textarea"},
]


def _escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def load_schema(input_folder: Path) -> tuple[list[dict], Path]:
    """Return (schema, schema_path), creating a default schema file if none exists."""

    schema_path = input_folder / SCHEMA_FILENAME
    if schema_path.exists():
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return data, schema_path
    schema_path.write_text(json.dumps(DEFAULT_SCHEMA, indent=2), encoding="utf-8")
    return DEFAULT_SCHEMA, schema_path


def _option_label_value(option) -> tuple[str, str]:
    """Allow options to be a plain string or a {label, value} dict."""

    if isinstance(option, dict):
        label = option.get("label", option.get("value", ""))
        return label, option.get("value", label)
    return option, option


def _field_html(field: dict) -> str:
    name = _escape(field.get("name", ""))
    label = _escape(field.get("label", field.get("name", "")))
    ftype = field.get("type", "text")
    required = " required" if field.get("required") else ""
    star = " <span class='req'>*</span>" if field.get("required") else ""
    head = f"<label for='{name}'>{label}{star}</label>"

    if ftype == "textarea":
        control = f"<textarea id='{name}' data-field='{name}'{required}></textarea>"
    elif ftype == "select":
        options = "".join(
            f"<option value='{_escape(value)}'>{_escape(text)}</option>"
            for text, value in map(_option_label_value, field.get("options", []))
        )
        control = f"<select id='{name}' data-field='{name}'{required}><option value=''></option>{options}</select>"
    elif ftype == "checkboxes":
        boxes = "".join(
            f"<label class='choice'><input type='checkbox' data-group='{name}' value='{_escape(value)}'> {_escape(text)}</label>"
            for text, value in map(_option_label_value, field.get("options", []))
        )
        control = f"<div class='choices' data-field='{name}'>{boxes}</div>"
    else:
        input_type = {"email": "email", "tel": "tel", "number": "number", "date": "date"}.get(ftype, "text")
        control = f"<input type='{input_type}' id='{name}' data-field='{name}'{required}>"

    return f"<div class='field'>{head}{control}</div>"


def build_form_html(schema: list[dict], title: str = "Client Tax Intake") -> str:
    """Build a self-contained fillable HTML intake form (downloads answers as JSON)."""

    fields_html = "\n".join(_field_html(field) for field in schema)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(title)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #1c2733; }}
  h1 {{ font-size: 1.5rem; }}
  .field {{ margin: 1rem 0; }}
  label {{ display: block; font-weight: 600; margin-bottom: .3rem; }}
  input, select, textarea {{ width: 100%; padding: .55rem; border: 1px solid #c3ccd6; border-radius: 8px; font-size: 1rem; box-sizing: border-box; }}
  textarea {{ min-height: 5rem; }}
  .choices {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: .35rem; }}
  .choice {{ font-weight: 400; display: flex; align-items: center; gap: .4rem; }}
  .choice input {{ width: auto; }}
  .req {{ color: #c0392b; }}
  button {{ background: #1f6feb; color: #fff; border: 0; border-radius: 8px; padding: .7rem 1.4rem; font-size: 1rem; cursor: pointer; }}
  .note {{ color: #5b6b7b; font-size: .9rem; }}
</style>
</head>
<body>
<h1>{_escape(title)}</h1>
<p class="note">Fill this out, then click <b>Download my answers</b> and send us the saved file. Nothing is uploaded from this page.</p>
<form id="intake" onsubmit="return downloadAnswers(event)">
{fields_html}
<div class="field"><button type="submit">Download my answers</button></div>
</form>
<script>
function downloadAnswers(event) {{
  event.preventDefault();
  var data = {{}};
  document.querySelectorAll('[data-field]').forEach(function(el) {{
    var name = el.getAttribute('data-field');
    if (el.classList.contains('choices')) {{
      var picked = [];
      el.querySelectorAll("input[type=checkbox]:checked").forEach(function(b) {{ picked.push(b.value); }});
      data[name] = picked;
    }} else {{
      data[name] = el.value.trim();
    }}
  }});
  var safe = (data.client_name || 'client').replace(/[^A-Za-z0-9]+/g, '_');
  var blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = safe + '_intake.json';
  document.body.appendChild(a); a.click(); a.remove();
  return false;
}}
</script>
</body>
</html>
"""


def compile_responses(response_paths: list[Path]) -> tuple[list[dict], list[str]]:
    """Load intake response JSON files into client records, with per-file warnings."""

    clients: list[dict] = []
    warnings: list[str] = []
    for path in response_paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            warnings.append(f"{path.name}: could not read ({exc}).")
            continue
        if not isinstance(record, dict) or not record.get("client_name"):
            warnings.append(f"{path.name}: missing client_name; skipped.")
            continue
        clients.append(record)
    return clients, warnings


def _merge_into_clients(clients_file: Path, new_records: list[dict]) -> tuple[int, int]:
    """Append only records whose email is not already present. Returns (added, skipped)."""

    existing: list[dict] = []
    if clients_file.exists():
        try:
            loaded = json.loads(clients_file.read_text(encoding="utf-8"))
            existing = loaded if isinstance(loaded, list) else [loaded]
        except json.JSONDecodeError:
            existing = []

    seen_emails = {str(c.get("email", "")).lower() for c in existing if c.get("email")}
    seen_names = {str(c.get("client_name", "")).lower() for c in existing}
    added = skipped = 0
    for record in new_records:
        email = str(record.get("email", "")).lower()
        name = str(record.get("client_name", "")).lower()
        if (email and email in seen_emails) or (not email and name in seen_names):
            skipped += 1
            continue
        existing.append(record)
        if email:
            seen_emails.add(email)
        seen_names.add(name)
        added += 1

    if added:
        clients_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return added, skipped


def run_intake(input_folder, status_callback=None) -> dict:
    """Generate the intake form and compile any returned responses into clients.json."""

    input_folder = Path(input_folder)
    output_folder = sort_tax_docs.setup_output_folders(input_folder)

    if status_callback:
        status_callback("Building intake form from schema")
    schema, schema_path = load_schema(input_folder)
    intake_folder = output_folder / INTAKE_FOLDER_NAME
    intake_folder.mkdir(exist_ok=True)
    form_path = intake_folder / FORM_FILENAME
    form_path.write_text(build_form_html(schema), encoding="utf-8")

    response_paths = sorted(
        set(input_folder.glob(RESPONSE_GLOB)) | set(intake_folder.glob(RESPONSE_GLOB))
    )
    new_records, warnings = compile_responses(response_paths)
    clients_file = input_folder / "clients.json"
    added, skipped = _merge_into_clients(clients_file, new_records)

    summary = f"Intake form ready ({len(schema)} fields)."
    if response_paths:
        summary += f" Compiled {len(response_paths)} response(s): added {added} new client(s)"
        summary += f", {skipped} already present." if skipped else "."

    return {
        "tool": "intake",
        "output_folder": output_folder,
        "intake_folder": intake_folder,
        "form_path": form_path,
        "schema_path": schema_path,
        "responses_found": len(response_paths),
        "clients_added": added,
        "clients_skipped": skipped,
        "warnings": warnings,
        "summary": summary,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a dynamic intake form and compile responses into clients.json."
    )
    parser.add_argument("input_folder", help="Folder for the intake form, schema, and responses.")
    args = parser.parse_args()

    folder = Path(args.input_folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {folder}")
        return 1

    result = run_intake(folder, status_callback=print)
    print(result["summary"])
    print(f"Intake form: {result['form_path']}")
    print(f"Edit questions in: {result['schema_path']}")
    for warning in result["warnings"]:
        print(f"  NOTE: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
