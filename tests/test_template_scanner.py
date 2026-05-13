from pathlib import Path
from occam_template_desk.core.template_scanner import detect_placeholders_from_text, normalize_field_name, scan_template


def test_placeholder_detection_from_text_html_templates():
    text = "Subject: Hi {{Client Name}}<p>{{client-email}}</p>{{ Client Name }}"
    assert detect_placeholders_from_text(text) == ["Client Name", "client-email"]


def test_placeholder_normalization():
    assert normalize_field_name("Client Name") == normalize_field_name("client_name") == normalize_field_name("CLIENT-NAME")


def test_docx_scan_sample():
    scan = scan_template(Path("occam_template_desk/sample_templates/Documents/Individual Tax Engagement Letter.docx"))
    assert "Client Name" in scan["placeholders"]
    assert scan["template_type"] == "document"
