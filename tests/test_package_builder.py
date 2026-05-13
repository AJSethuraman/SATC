from pathlib import Path
from occam_template_desk.core.validation import validate_run
from occam_template_desk.core.package_builder import build_output_package


def test_output_package_contains_required_files_and_audit_report(tmp_path):
    template = "occam_template_desk/sample_templates/Emails/Invoice Delivery Email.html"
    values = {"Client Name":"Arbor & Finch LLC", "Client Email":"alex@example.com", "Invoice Number":"INV-1", "Invoice Amount":"100", "Firm Name":"Occam Advisors", "Contact First Name":"Alex", "Service Description":"Tax", "Due Date":"2026-05-20", "Payment Link":"https://pay", "Manager":"Mia"}
    fields = [{"field": k, "value": v, "source": "test", "status": "Filled"} for k, v in values.items()]
    validation = validate_run(template, "email", values, [], tmp_path, subject="Invoice INV-1")
    package = build_output_package(template, "email", values, fields, validation, {"Client Name":"Arbor & Finch LLC", "Client ID":"C-1"}, tmp_path, {"attempted": True, "created": False, "mode":"fallback_files"}, [], {})
    folder = Path(package["package_dir"])
    for name in ["input_snapshot.json", "audit_log.json", "validation_report.xlsx", "rendered_values.json", "outlook_status.json", "email_metadata.json"]:
        assert (folder / name).exists()
