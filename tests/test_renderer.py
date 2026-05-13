from pathlib import Path
from occam_template_desk.core.renderer import render_email_template, render_docx_template
from occam_template_desk.core.template_scanner import extract_docx_text


def test_rendered_email_replaces_placeholders_correctly(tmp_path):
    rendered = render_email_template("occam_template_desk/sample_templates/Emails/Invoice Delivery Email.html", {"Invoice Number":"INV-1", "Firm Name":"Occam Advisors", "Contact First Name":"Alex", "Service Description":"Tax", "Invoice Amount":"50", "Due Date":"2026-05-20", "Payment Link":"https://pay", "Manager":"Mia", "Client Email":"a@example.com"}, tmp_path)
    assert "INV-1" in rendered["subject"]
    assert "{{" not in rendered["body"]
    assert Path(rendered["body_path"]).exists()


def test_rendered_docx_file_is_created(tmp_path):
    out = render_docx_template("occam_template_desk/sample_templates/Documents/Individual Tax Engagement Letter.docx", {"Client Name":"Arbor", "Tax Year":"2025", "Contact First Name":"Alex", "Firm Name":"Occam Advisors", "Fee Amount":"100", "Billing Terms":"Due", "Partner":"Dana", "Manager":"Mia", "Payment Link":"https://pay"}, tmp_path)
    assert Path(out["document_path"]).exists()
    assert "Arbor" in extract_docx_text(out["document_path"])
