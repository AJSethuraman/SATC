from __future__ import annotations

from .core.settings import OccamSettings
from .core.data_source import OccamWorkbook
from .core.template_scanner import scan_template
from .core.field_mapping import build_field_records, records_to_values
from .core.renderer import parse_email_template, render_text
from .core.validation import validate_run
from .core.package_builder import build_output_package
from .core.outlook import OutlookDraftService
from .core.settings import PACKAGE_ROOT
from .setup_samples import ensure_sample_assets


def generate_demo_packages() -> list[dict]:
    ensure_sample_assets()
    settings = OccamSettings.defaults()
    wb = OccamWorkbook(settings.data_workbook_path)
    client = wb.get_client_by_id("C-1001")
    outputs = []
    for rel in ["Documents/Individual Tax Engagement Letter.docx", "Emails/Invoice Delivery Email.html"]:
        template = PACKAGE_ROOT / "sample_templates" / rel
        scan = scan_template(template)
        pool = wb.field_pool_for_client(client)
        pool.setdefault("firm name", (settings.default_firm_name, "Settings"))
        fields = build_field_records(scan["placeholders"], pool)
        values = records_to_values(fields)
        values.setdefault("Client Name", client.get("Client Name", "")); values.setdefault("Client Email", client.get("Client Email", ""))
        subject = ""
        if scan["template_type"] == "email":
            subject_t, _ = parse_email_template(template)
            subject = render_text(subject_t, values)
        validation = validate_run(template, scan["template_type"], values, scan["placeholders"], settings.output_folder_path, subject=subject, missing_items=wb.missing_items_for_client(client.get("Client ID")))
        outlook_status = None
        if scan["template_type"] == "email":
            outlook_status = OutlookDraftService().fallback_status(None, "Demo uses fallback files and never sends email.")
        outputs.append(build_output_package(str(template), scan["template_type"], values, fields, validation, client, settings.output_folder_path, outlook_status, scan["placeholders"], {}))
    return outputs

if __name__ == "__main__":
    for package in generate_demo_packages():
        print(f"Generated: {package['package_dir']}")
