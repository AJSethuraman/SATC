from occam_template_desk.core.validation import validate_run

TPL = "occam_template_desk/sample_templates/Emails/Invoice Delivery Email.html"
DOC = "occam_template_desk/sample_templates/Documents/Individual Tax Engagement Letter.docx"


def test_missing_client_name_creates_blocker(tmp_path):
    result = validate_run(DOC, "document", {"Client Name": "", "Tax Year": "2025"}, ["Client Name"], tmp_path)
    assert result.status == "Blocked"
    assert any("Client Name" in b for b in result.blockers)


def test_invalid_client_email_creates_blocker_for_email_templates(tmp_path):
    result = validate_run(TPL, "email", {"Client Name": "A", "Client Email": "bad", "Invoice Number": "INV", "Invoice Amount": "10"}, [], tmp_path, subject="Invoice")
    assert result.status == "Blocked"
    assert any("invalid" in b.lower() for b in result.blockers)


def test_warning_does_not_block_generation(tmp_path):
    result = validate_run(DOC, "document", {"Client Name": "A", "Fee Amount": "0"}, [], tmp_path)
    assert result.status == "Needs Review"
    assert result.can_generate


def test_user_override_is_tracked(tmp_path):
    result = validate_run(DOC, "document", {"Client Name": "A", "Fee Amount": "100"}, [], tmp_path, overrides={"Fee Amount": "100"})
    assert result.status == "Needs Review"
    assert any("overrode" in w for w in result.warnings)
