from __future__ import annotations

from pathlib import Path
from .renderer import parse_email_template, render_text

def build_preview(template_path: str, template_type: str, values: dict, output_name: str) -> dict:
    if template_type == "email":
        subject_t, body_t = parse_email_template(template_path)
        return {"type": "email", "to": values.get("Client Email", ""), "cc": values.get("CC", ""), "subject": render_text(subject_t, values), "body": render_text(body_t, values), "attachments": []}
    return {"type": "document", "output_filename": output_name, "fields": values, "note": "Text approximation preview; generated Word file is saved in the output package."}
