from __future__ import annotations

from pathlib import Path
import streamlit as st

from occam_template_desk.assets.styles import inject_streamlit_css, status_badge
from occam_template_desk.core.settings import OccamSettings, ensure_default_settings, save_settings
from occam_template_desk.core.template_scanner import list_templates, scan_template
from occam_template_desk.core.data_source import OccamWorkbook
from occam_template_desk.core.field_mapping import build_field_records, records_to_values
from occam_template_desk.core.validation import validate_run
from occam_template_desk.core.renderer import parse_email_template, render_text
from occam_template_desk.core.preview import build_preview
from occam_template_desk.core.package_builder import build_output_package, list_recent_packages
from occam_template_desk.core.outlook import OutlookDraftService
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


def generate_page(settings: OccamSettings):
    hero(); st.header("Generate output package")
    wb, err = friendly_load_workbook(settings.data_workbook_path)
    if err:
        st.error(f"Error: {err}"); return
    category = st.radio("1. Select template category", ["Documents", "Emails"], horizontal=True)
    templates = list_templates(settings.template_folder_path, category)
    if not templates:
        st.warning("Warning: no supported templates found in this category."); return
    template = st.selectbox("2. Select template", templates, format_func=lambda p: p.name)
    scan = scan_template(template)
    clients = wb.clients(settings.client_sheet_name)
    if not clients:
        st.error("Error: no clients found in the selected workbook sheet."); return
    client_name = st.selectbox("3. Select client", [c.get("Client Name", "Unnamed") for c in clients])
    client = wb.get_client_by_name(client_name, settings.client_sheet_name)
    pool = wb.field_pool_for_client(client)
    pool.setdefault("firm name", (settings.default_firm_name, "Settings"))
    pool.setdefault("default tax year", (settings.default_tax_year, "Settings"))
    st.subheader("4. Review auto-filled fields")
    auto_fields = build_field_records(scan["placeholders"], pool)
    overrides = {}
    cols = st.columns([2, 3, 2, 1])
    cols[0].markdown("**Field label**"); cols[1].markdown("**Current value / override**"); cols[2].markdown("**Source**"); cols[3].markdown("**Status**")
    for field in auto_fields:
        c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
        c1.write(field["field"])
        val = c2.text_input(field["field"], value=field["value"], label_visibility="collapsed", key=f"field_{field['field']}")
        if val != field["value"]:
            overrides[field["field"]] = val
        c3.write(field["source"])
        c4.write("Filled" if val.strip() else "Missing")
    fields = build_field_records(scan["placeholders"], pool, overrides)
    values = records_to_values(fields)
    for k, v in client.items():
        values.setdefault(k, v)
    subject = ""
    if scan["template_type"] == "email":
        subject_t, _ = parse_email_template(template)
        subject = render_text(subject_t, values)
    outlook_requested = scan["template_type"] == "email" and settings.outlook_draft_mode == "local_outlook"
    outlook_service = OutlookDraftService()
    validation = validate_run(template, scan["template_type"], values, scan["placeholders"], settings.output_folder_path, subject=subject, overrides=overrides, outlook_requested=outlook_requested, outlook_available=outlook_service.is_available(), missing_items=wb.missing_items_for_client(client.get("Client ID", "")))
    st.subheader("5. Validation status")
    st.markdown(status_badge(validation.status), unsafe_allow_html=True)
    for b in validation.blockers:
        st.error(f"Blocked: {b}")
    for w in validation.warnings:
        st.warning(f"Warning: {w}")
    for action in validation.next_actions:
        st.info(action)
    st.subheader("6. Preview")
    preview = build_preview(str(template), scan["template_type"], values, f"{client_name}_{template.stem}.docx")
    if preview["type"] == "email":
        st.text_input("To", preview["to"], disabled=True)
        st.text_input("Subject", preview["subject"], disabled=True)
        st.text_area("Body preview", preview["body"], height=260, disabled=True)
    else:
        st.json(preview)
    st.subheader("7. Generate output")
    if st.button("Generate output package", disabled=not validation.can_generate):
        outlook_status = None
        if scan["template_type"] == "email" and settings.outlook_draft_mode == "local_outlook":
            outlook_status = outlook_service.fallback_status(None, "Draft creation is attempted after package files are prepared if Outlook is available.") if not outlook_service.is_available() else {"attempted": True, "created": False, "mode": "local_outlook", "message": "Outlook draft can be created from generated package."}
        elif scan["template_type"] == "email" and settings.outlook_draft_mode == "fallback_files":
            outlook_status = {"attempted": True, "created": False, "mode": "fallback_files", "message": "Fallback copy-ready files generated. No email was sent."}
        package = build_output_package(str(template), scan["template_type"], values, fields, validation, client, settings.output_folder_path, outlook_status, scan["placeholders"], overrides)
        st.success(f"Success: output package generated at {package['package_dir']}")


def audit_page(settings: OccamSettings):
    hero(); st.header("Recent Outputs / Audit")
    recent = list_recent_packages(settings.output_folder_path)
    if not recent:
        st.info("No output packages found yet."); return
    for item in recent:
        st.markdown(f"<div class='occam-card'><strong>{item['client']}</strong> — {item['template']}<br>Status: {item['status']}<br>Timestamp: {item['timestamp']}<br>Folder: <code>{item['folder']}</code></div>", unsafe_allow_html=True)
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
