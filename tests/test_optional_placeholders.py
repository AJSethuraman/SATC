from pathlib import Path

from occam_template_desk.core.field_mapping import build_field_records, records_to_values
from occam_template_desk.core.renderer import create_minimal_docx, extract_docx_text, render_docx_template, render_email_template
from occam_template_desk.core.template_scanner import detect_placeholders_from_text
from occam_template_desk.core.validation import validate_run


def test_optional_placeholder_missing_does_not_block_and_renders_blank_text(tmp_path):
    template = tmp_path / "optional.txt"
    template.write_text("Subject: Hello {{Client Name}}\nSpouse: {{optional:Spouse Name}}", encoding="utf-8")
    placeholders = detect_placeholders_from_text(template.read_text())
    fields = build_field_records(placeholders, {"client name": ("Alex", "Clients sheet")})
    values = records_to_values(fields)
    values["Client Email"] = "alex@example.com"
    validation = validate_run(template, "email", values, placeholders, tmp_path, subject="Hello Alex")
    rendered = render_email_template(template, values, tmp_path)
    assert validation.can_generate
    assert fields[1]["required"] is False
    assert fields[1]["status"] == "Optional Blank"
    assert "{{optional:Spouse Name}}" not in rendered["body"]
    assert rendered["body"].strip() == "Spouse:"


def test_optional_placeholder_renders_in_html_and_docx(tmp_path):
    html_template = tmp_path / "optional.html"
    html_template.write_text("Subject: Hi {{Client Name}}\n<p>{{optional:Additional Notes}}</p>", encoding="utf-8")
    rendered_html = render_email_template(html_template, {"Client Name": "Alex", "Additional Notes": "Bring ID"}, tmp_path / "html")
    assert "Bring ID" in rendered_html["body"]
    assert "optional:" not in rendered_html["body"]

    docx_template = tmp_path / "optional.docx"
    create_minimal_docx(docx_template, ["Client {{Client Name}}", "Notes {{optional:Additional Notes}}"])
    rendered_docx = render_docx_template(docx_template, {"Client Name": "Alex"}, tmp_path / "docx")
    text = extract_docx_text(rendered_docx["document_path"])
    assert "Alex" in text
    assert "optional:" not in text
