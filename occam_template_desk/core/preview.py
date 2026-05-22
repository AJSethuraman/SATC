from __future__ import annotations

from .renderer import parse_email_template, render_text


def build_preview(template_path: str, template_type: str, values: dict, output_name: str) -> dict:
    if template_type == "email":
        subject_t, body_t = parse_email_template(template_path)
        return {"type": "email", "to": values.get("Client Email", ""), "cc": values.get("CC", ""), "subject": render_text(subject_t, values), "body": render_text(body_t, values), "attachments": []}
    return {"type": "document", "output_filename": output_name, "fields": values, "note": "Text approximation preview; generated Word file is saved in the output package."}


def build_document_preview(template_name: str, output_filename: str, fields: list[dict], validation: dict) -> dict:
    matched = [field for field in fields if field.get("status") == "Filled"]
    missing = [field for field in fields if field.get("status") != "Filled"]
    return {
        "type": "document",
        "template_name": template_name,
        "output_filename": output_filename,
        "matched_fields_count": len(matched),
        "missing_fields_count": len(missing),
        "field_table": [
            {"Field": field.get("field", ""), "Value": field.get("value", ""), "Source": field.get("source", ""), "Status": field.get("status", "")}
            for field in fields
        ],
        "validation_status": validation.get("status", ""),
        "blockers": validation.get("blockers", []),
        "warnings": validation.get("warnings", []),
    }
