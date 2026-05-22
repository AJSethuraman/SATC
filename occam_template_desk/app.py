from __future__ import annotations

from pathlib import Path
import streamlit as st

from occam_template_desk.assets.styles import inject_streamlit_css, status_badge
from occam_template_desk.core.settings import OccamSettings, ensure_default_settings, save_settings
from occam_template_desk.core.template_scanner import list_templates, scan_template
from occam_template_desk.core.data_source import OccamWorkbook
from occam_template_desk.core.field_mapping import build_field_records, records_to_values
from occam_template_desk.core.invoice import invoice_selection_state, template_requires_invoice
from occam_template_desk.core.validation import validate_run
from occam_template_desk.core.renderer import parse_email_template, render_text
from occam_template_desk.core.preview import build_document_preview
from occam_template_desk.core.package_builder import build_output_package, list_recent_packages, update_outlook_status
from occam_template_desk.core.outlook import OutlookDraftService
from occam_template_desk.core.outlook_workflow import create_outlook_draft_if_allowed
from occam_template_desk.core.session_state import clear_generation_state, get_generation_state, save_generation_state
from occam_template_desk.setup_samples import ensure_sample_assets

st.set_page_config(page_title="Occam Template Desk", page_icon="📄", layout="wide")
inject_streamlit_css(st)


def friendly_load_workbook(path: str):
    try:
        return OccamWorkbook(path), None
    except Exception as exc:
        return None, f"Unable to load workbook. Check the path and workbook structure. Detail: {exc}"


def hero():
    st.markdown("<div class='occam-hero'><h1 style='color:white;margin:0'>Occam Template Desk</h1><p style='margin:.25rem 0 0'>Generate client-ready documents and draft emails from controlled templates. Draft-only. Audit-ready.</p></div>", unsafe_allow_html=True)


def dashboard(settings: OccamSettings):
    hero()
    docs = list_templates(settings.template_folder_path, "Documents")
    emails = list_templates(settings.template_folder_path, "Emails")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Document templates", len(docs))
    c2.metric("Email templates", len(emails))
    c3.metric("Outlook mode", settings.outlook_draft_mode)
    c4.metric("Default tax year", settings.default_tax_year)
    st.markdown("### Loaded paths")
    st.info(f"Data workbook: `{settings.data_workbook_path}`\n\nTemplate folder: `{settings.template_folder_path}`\n\nOutput folder: `{settings.output_folder_path}`")
    st.markdown("### Quick start")
    st.markdown("1. Open **Generate**. 2. Select Documents or Emails. 3. Pick a template and client. 4. Review fields and validation. 5. Generate a draft package. Nothing is sent automatically.")


def settings_page(settings: OccamSettings):
    hero(); st.header("Settings")
    st.markdown("Review local paths before generating client-facing drafts. Missing paths are warnings, not crashes.")
    for label, value in [("Data workbook", settings.data_workbook_path), ("Template folder", settings.template_folder_path), ("Output folder", settings.output_folder_path)]:
        if Path(value).exists():
            st.success(f"Ready: {label} exists — `{value}`")
        else:
            st.warning(f"Warning: {label} path does not exist — `{value}`")
    if st.button("Restore default sample settings"):
        defaults = OccamSettings.defaults()
        save_settings(defaults)
        st.success("Success: default sample settings restored. Refresh or switch pages to reload.")
    with st.form("settings"):
        data = st.text_input("Data workbook path", settings.data_workbook_path)
        templates = st.text_input("Template folder path", settings.template_folder_path)
        output = st.text_input("Output folder path", settings.output_folder_path)
        sheet = st.text_input("Client table/sheet", settings.client_sheet_name)
        match = st.text_input("Client match field", settings.client_match_field)
        mode = st.selectbox("Outlook draft mode", ["disabled", "local_outlook", "fallback_files"], index=["disabled", "local_outlook", "fallback_files"].index(settings.outlook_draft_mode))
        if st.form_submit_button("Save settings"):
            save_settings(OccamSettings(data, templates, output, sheet, match, settings.default_firm_name, settings.default_tax_year, mode))
            st.success("Success: settings saved. Refresh or switch pages to reload.")


def _show_template_diagnostics(scan: dict, fields: list[dict], template: Path):
    missing = [field for field in fields if field["status"] == "Missing"]
    matched = [field for field in fields if field["status"] == "Filled"]
    suspicious = any(word in template.name.lower() for word in ["old", "draft", "copy", "deprecated"])
    health = "Problem Detected" if not scan["placeholders"] else ("Needs Review" if missing or suspicious else "Ready")
    modified = "Unknown"
    try:
        from datetime import datetime
        modified = datetime.fromtimestamp(template.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        pass
    st.markdown("### Template health check")
    st.markdown(f"<div class='occam-card'><strong>Template Health:</strong> {status_badge(health)}<br><strong>Template name:</strong> {template.name}<br><strong>Template path:</strong> <code>{scan['path']}</code><br><strong>Template type:</strong> {scan['template_type']}<br><strong>Last modified:</strong> {modified}<br><strong>Placeholders detected:</strong> {len(scan['placeholders'])}<br><strong>Matched fields:</strong> {len(matched)}<br><strong>Missing fields:</strong> {len(missing)}<br><strong>Word template note:</strong> type each placeholder as one continuous unformatted token, e.g. <code>{{{{Client Name}}}}</code>. Do not format only part of a placeholder or split it across lines.</div>", unsafe_allow_html=True)
    if not scan["placeholders"]:
        st.warning("Warning: no placeholders were detected in this template.")
    if suspicious:
        st.warning("Warning: the template filename suggests it may be old, draft, copy, or deprecated.")
    if scan["placeholders"]:
        st.caption("Placeholders: " + ", ".join(scan["placeholders"]))
    if missing:
        st.warning("Missing fields: " + ", ".join(field["field"] for field in missing))


def _next_action_for_package(validation: dict, email_rendered: dict | None, settings: OccamSettings) -> str:
    if validation.get("unresolved_placeholders"):
        return "Do Not Send: fix unresolved placeholders, then regenerate the package."
    if "blocked" in str(validation.get("status", "")).lower():
        return "Resolve blockers before using this output."
    if email_rendered and settings.outlook_draft_mode == "local_outlook":
        return "Review the copy-ready email, then create an Outlook draft if appropriate."
    return "Review the generated files before sending or filing."


def _show_generation_success_state(state: dict, settings: OccamSettings):
    package = state["package"]
    email_rendered = state.get("rendered_email")
    validation = state.get("validation", package.get("validation", {}))
    values = state.get("final_values", {})
    validation_status = validation.get("status", "Ready")
    audit = package.get("audit", {})
    st.markdown("## Step 9 — Final Actions")
    st.markdown(f"<div class='occam-card'><h3>Operational handoff</h3>{status_badge(validation_status)}<br><br><strong>Client:</strong> {audit.get('client_name', state.get('selected_client', {}).get('Client Name', ''))}<br><strong>Template:</strong> {audit.get('template_name', state.get('selected_template', ''))}<br><strong>Timestamp:</strong> {audit.get('timestamp', '')}<br><strong>Output package folder:</strong> <code>{package['package_dir']}</code><br><strong>Validation report:</strong> <code>{package['validation_report']}</code><br><strong>Audit log:</strong> <code>{package['audit_log']}</code><br><strong>Next action:</strong> {_next_action_for_package(validation, email_rendered, settings)}</div>", unsafe_allow_html=True)
    unresolved = validation.get("unresolved_placeholders") or package.get("unresolved_placeholders") or []
    if unresolved:
        st.error("Do Not Send: unresolved placeholders remain: " + ", ".join(f"{{{{{token}}}}}" for token in unresolved))
    st.markdown("**Generated files**")
    for file_path in package["generated_files"]:
        st.code(file_path)
    if email_rendered:
        st.markdown("### Copy-ready email")
        st.text_input("Subject", email_rendered.get("subject", ""), disabled=True, key="generated_email_subject")
        st.text_area("Body", email_rendered.get("body", ""), height=260, disabled=True, key="generated_email_body")
        generated_attachment_candidates = [path for path in package.get("generated_files", []) if Path(path).suffix.lower() in {".docx", ".pdf"}]
        selected_attachments = st.multiselect("Optional attachments from this output package", generated_attachment_candidates, default=[])
        if selected_attachments:
            st.info("Attachments selected explicitly: " + ", ".join(selected_attachments))
        else:
            st.caption("Attachments: none selected. No files will be attached automatically.")
        if settings.outlook_draft_mode == "disabled":
            st.info("Outlook draft mode is disabled. Use the copy-ready files if you need to draft manually.")
        elif settings.outlook_draft_mode == "local_outlook":
            if st.button("Create Outlook Draft", disabled=bool(unresolved) or "blocked" in validation_status.lower()):
                status = create_outlook_draft_if_allowed(validation, settings.outlook_draft_mode, email_rendered, values, attachments=selected_attachments, service=OutlookDraftService(), output_dir=package["package_dir"])
                update_outlook_status(package["package_dir"], status)
                state["outlook_status"] = status
                state["selected_attachments"] = selected_attachments
                if status.get("created"):
                    st.success("Success: Outlook draft created. No email was sent.")
                else:
                    st.warning(f"Warning: {status.get('message', 'Outlook draft was not created. Fallback files are available.')}")
    if st.button("Clear / Start New Draft"):
        clear_generation_state(st.session_state)
        st.rerun()


def generate_page(settings: OccamSettings):
    hero(); st.header("Generate output package")
    saved_state = get_generation_state(st.session_state)
    if saved_state:
        _show_generation_success_state(saved_state, settings)
        st.divider()
    wb, err = friendly_load_workbook(settings.data_workbook_path)
    if err:
        st.error(f"Error: {err}"); return
    st.markdown("## Step 1 — Choose Template")
    category = st.radio("Template category", ["Documents", "Emails"], horizontal=True)
    templates = list_templates(settings.template_folder_path, category)
    if not templates:
        st.warning("Warning: no supported templates found in this category."); return
    template = st.selectbox("Select template", templates, format_func=lambda p: p.name)
    scan = scan_template(template)
    st.markdown("## Step 2 — Template Diagnostics")
    options = wb.client_options(settings.client_match_field, settings.client_sheet_name)
    if not options:
        st.error("Error: no clients found in the selected workbook sheet."); return
    st.markdown("## Step 3 — Choose Client")
    selected_option = st.selectbox("Select client", options, format_func=lambda option: option["label"])
    client = wb.get_client(selected_option["match_value"], settings.client_match_field, settings.client_sheet_name)
    if not client:
        st.error(f"Error: selected client could not be matched by {settings.client_match_field}."); return

    requires_invoice = template_requires_invoice(scan["placeholders"], template.name)
    invoices = wb.invoices_for_client(client.get("Client ID", ""))
    invoice_state = invoice_selection_state(invoices, requires_invoice)
    selected_invoice = invoice_state["selected_invoice"]
    st.markdown("## Step 4 — Related Records")
    if requires_invoice:
        st.markdown("### Invoice selection")
        if invoice_state["status"] == "multiple":
            selected_invoice = st.selectbox("Select invoice for this output", invoices, format_func=lambda invoice: f"{invoice.get('Invoice Number', 'Invoice')} — ${invoice.get('Invoice Amount', '')} due {invoice.get('Due Date', '')}")
        elif invoice_state["status"] == "auto_selected":
            st.info(invoice_state["message"])
        else:
            st.warning("Warning: this template needs invoice fields, but no invoice was found for the selected client.")

    if not requires_invoice:
        st.info("No invoice selection is required for this template.")
    missing_items = wb.missing_items_for_client(client.get("Client ID", ""))
    manual_missing_items = ""
    if "missing" in template.name.lower():
        default_missing = "\n".join(f"- {item.get('Missing Item', '')}" for item in missing_items if str(item.get("Status", "")).lower() != "received" and item.get("Missing Item"))
        st.markdown("### Missing items for this run")
        st.caption("Edit this list for the current run only. The source workbook is not changed.")
        manual_missing_items = st.text_area("Missing items", value=default_missing, height=140)
    pool = wb.field_pool_for_client(client, selected_invoice)
    if manual_missing_items:
        pool["missing items"] = (manual_missing_items, "User override")
    pool.setdefault("firm name", (settings.default_firm_name, "Settings"))
    pool.setdefault("default tax year", (settings.default_tax_year, "Settings"))
    auto_fields = build_field_records(scan["placeholders"], pool)
    _show_template_diagnostics(scan, auto_fields, template)

    st.markdown("## Step 5 — Review Auto-Filled Fields")
    overrides = {}
    cols = st.columns([2, 1, 3, 2, 1])
    cols[0].markdown("**Field**"); cols[1].markdown("**Required?**"); cols[2].markdown("**Current value / override**"); cols[3].markdown("**Source**"); cols[4].markdown("**Status**")
    for field in auto_fields:
        c1, c_req, c2, c3, c4 = st.columns([2, 1, 3, 2, 1])
        c1.write(field["field"])
        c_req.write("Required" if field.get("required", True) else "Optional")
        val = c2.text_input(field["field"], value=field["value"], label_visibility="collapsed", key=f"field_{field['field']}")
        if val != field["value"]:
            overrides[field.get("placeholder", field["field"])] = val
        c3.write(field["source"])
        c4.write(field["status"] if field.get("value") == val else "Overridden")
    fields = build_field_records(scan["placeholders"], pool, overrides)
    values = records_to_values(fields)
    for key, value in client.items():
        values.setdefault(key, value)
    if selected_invoice:
        for key, value in selected_invoice.items():
            values.setdefault(key, value)
    subject = ""
    if scan["template_type"] == "email":
        subject_t, _ = parse_email_template(template)
        subject = render_text(subject_t, values)
    outlook_requested = scan["template_type"] == "email" and settings.outlook_draft_mode == "local_outlook"
    outlook_service = OutlookDraftService()
    validation = validate_run(template, scan["template_type"], values, scan["placeholders"], settings.output_folder_path, subject=subject, overrides=overrides, outlook_requested=outlook_requested, outlook_available=outlook_service.is_available(), missing_items=wb.missing_items_for_client(client.get("Client ID", "")))
    st.markdown("## Step 6 — Validate")
    st.markdown(status_badge(validation.status), unsafe_allow_html=True)
    for b in validation.blockers:
        st.error(f"Blocked: {b}")
    for w in validation.warnings:
        st.warning(f"Warning: {w}")
    for action in validation.next_actions:
        st.info(action)

    st.markdown("## Step 7 — Preview")
    if scan["template_type"] == "email":
        _, body_t = parse_email_template(template)
        body = render_text(body_t, values)
        st.text_input("To", values.get("Client Email", ""), disabled=True)
        st.text_input("Subject", subject, disabled=True)
        st.text_area("Body preview", body, height=260, disabled=True)
        st.caption("Attachments: none selected. Attachments must be selected explicitly after generation.")
    else:
        preview = build_document_preview(template.name, f"{client.get('Client Name', 'Client')}_{template.stem}.docx", fields, validation.to_dict())
        st.markdown(f"<div class='occam-card'><strong>Template:</strong> {preview['template_name']}<br><strong>Output filename:</strong> {preview['output_filename']}<br><strong>Matched fields:</strong> {preview['matched_fields_count']}<br><strong>Missing fields:</strong> {preview['missing_fields_count']}<br><strong>Validation:</strong> {preview['validation_status']}</div>", unsafe_allow_html=True)
        st.dataframe(preview["field_table"], use_container_width=True)

    st.markdown("## Step 8 — Generate Package")
    if st.button("Generate output package", disabled=not validation.can_generate):
        outlook_status = None
        if scan["template_type"] == "email" and settings.outlook_draft_mode == "fallback_files":
            outlook_status = {"attempted": True, "created": False, "mode": "fallback_files", "message": "Fallback copy-ready files generated. No email was sent."}
        package = build_output_package(str(template), scan["template_type"], values, fields, validation, client, settings.output_folder_path, outlook_status, scan["placeholders"], overrides, selected_invoice, [])
        rendered_email = package["rendered"] if scan["template_type"] == "email" else None
        state = save_generation_state(st.session_state, package, rendered_email, package["validation"], str(template), client, values)
        _show_generation_success_state(state, settings)


def audit_page(settings: OccamSettings):
    hero(); st.header("Recent Outputs / Audit")
    recent = list_recent_packages(settings.output_folder_path)
    if not recent:
        st.info("No output packages found yet."); return
    for item in recent:
        st.markdown(f"<div class='occam-card'><strong>{item['client']}</strong> — {item['template']}<br>Status: {item['status']}<br>Timestamp: {item['timestamp']}<br>Blockers: {item.get('blocker_count', 0)} | Warnings: {item.get('warning_count', 0)}<br>Outlook: {item.get('outlook_status', 'Not attempted')}<br>Folder: <code>{item['folder']}</code></div>", unsafe_allow_html=True)
        if item.get("generated_files"):
            st.caption("Generated files: " + ", ".join(item["generated_files"]))


def main():
    ensure_sample_assets()
    settings = ensure_default_settings()
    page = st.sidebar.radio("Navigation", ["Home / Dashboard", "Settings", "Generate", "Recent Outputs / Audit"])
    if page == "Home / Dashboard": dashboard(settings)
    elif page == "Settings": settings_page(settings)
    elif page == "Generate": generate_page(settings)
    else: audit_page(settings)

if __name__ == "__main__":
    main()
