# Occam Template Desk

Occam Template Desk is a local, branded internal operations tool for generating client-facing documents and draft emails from reusable templates and an Excel workbook. It is designed for engagement letters, invoice emails, missing document request emails, and similar correspondence.

The first version is intentionally local-first and draft-only. It does **not** send email automatically, does **not** modify source templates, and does **not** modify the source Excel database.

## Workflow

1. Open the Streamlit UI.
2. Confirm settings for the data workbook, template folder, output folder, client sheet, client match field, and Outlook draft mode.
3. Choose a category: **Documents** or **Emails**.
4. Select a template from `occam_template_desk/sample_templates/Documents` or `occam_template_desk/sample_templates/Emails`.
5. Select a client from the Excel workbook.
6. The app scans the template for placeholders such as `{{Client Name}}`, `{{Tax Year}}`, and `{{Invoice Number}}`.
7. Matching values are pulled from workbook sheets and displayed with source/status labels.
8. Review and override values for the current run only.
9. Review validation status: **Ready**, **Needs Review**, or **Blocked**.
10. Preview the document/email.
11. Generate an output package with rendered files, audit log, input snapshot, rendered values, and validation report.
12. If enabled, Outlook draft integration can create/open a local draft; otherwise copy-ready fallback files are created.

## Generate local sample binary files

The PR intentionally does **not** commit generated binary artifacts such as `.xlsx` workbooks or `.docx` templates. Generate the sample workbook and Word engagement letter locally before running the demo or app:

```bash
python -m occam_template_desk.setup_samples
```

This creates:

- `occam_template_desk/sample_data/Occam_Data.xlsx`
- `occam_template_desk/sample_templates/Documents/Individual Tax Engagement Letter.docx`

The generator uses `openpyxl` for the workbook and `python-docx` for the Word template when those dependencies are installed. A lightweight fallback is available for constrained test environments.

## Run the app

```bash
python -m occam_template_desk.setup_samples
streamlit run occam_template_desk/app.py
```

If Streamlit is not installed, install dependencies first:

```bash
python -m pip install -r requirements.txt
```

## Run the CLI demo

```bash
python -m occam_template_desk.setup_samples
python -m occam_template_desk.demo
```

The demo also ensures sample assets exist, then generates one engagement letter package and one invoice email package using the sample data and templates.

## Run tests

```bash
pytest
```

The tests cover placeholder scanning, normalization, sample workbook loading, validation blockers/warnings, rendering, package artifacts, validation reports, audit logs, and Outlook fallback behavior.

## Template basics

Drop templates into:

- `occam_template_desk/sample_templates/Documents/` for `.docx` document templates.
- `occam_template_desk/sample_templates/Emails/` for `.txt`, `.html`, or `.md` email templates.

Use double-brace placeholders:

```text
{{Client Name}}
{{Client Email}}
{{Tax Year}}
{{Fee Amount}}
{{Invoice Number}}
{{Due Date}}
```

Placeholder matching supports light normalization:

- `{{Client Name}}`
- `{{client_name}}`
- `{{client-name}}`
- case-insensitive matching

Email templates may include a subject on the first line:

```text
Subject: Invoice {{Invoice Number}} from {{Firm Name}}
```

If an email template has no subject line, validation blocks generation.

## Expected workbook structure

The sample workbook is generated locally at `occam_template_desk/sample_data/Occam_Data.xlsx` and includes these sheets:

### Settings

| Setting | Value |
| --- | --- |
| Firm Name | Occam Advisors |
| Default Tax Year | 2025 |

### Clients

Required demo columns include:

- Client ID
- Client Name
- Client Email
- Contact First Name
- Entity Type
- Tax Year
- Fee Amount
- Partner
- Manager
- Billing Terms
- Payment Link

### Invoices

Required demo columns include:

- Invoice Number
- Client ID
- Invoice Amount
- Invoice Date
- Due Date
- Service Description
- Payment Link

### Missing Items

Required demo columns include:

- Client ID
- Missing Item
- Status
- Notes

## Settings

Settings are stored in `occam_settings.json` after first launch. If it does not exist, the app creates sensible defaults pointing to the locally generated sample workbook, sample templates, and output folder.

Editable settings in the UI:

- Data workbook path
- Template folder path
- Output folder path
- Client table/sheet
- Client match field
- Outlook draft mode

Supported Outlook modes:

- `disabled`: no Outlook draft attempt.
- `local_outlook`: attempt a local Outlook draft on Windows with pywin32 after validation passes.
- `fallback_files`: generate copy-ready email draft files and metadata only.

## Output packages

Each run creates a folder named like:

```text
YYYYMMDD_HHMMSS_ClientName_TemplateName
```

Each package includes:

- Generated `.docx`, `.txt`, `.html`, or `.md` output.
- `input_snapshot.json`
- `audit_log.json`
- `rendered_values.json`
- `validation_report.xlsx`
- `email_metadata.json` for email outputs.
- `outlook_status.json` if Outlook draft behavior was attempted or fallback was recorded.

The validation report workbook contains:

1. Summary
2. Fields
3. Validation Results
4. Audit Log

It uses branded status language and reviewer-friendly sheets.

## Validation model

**Blocked** means generation is not allowed. Examples:

- Missing Client Name.
- Missing or invalid Client Email for email templates.
- Required placeholder value is blank.
- Output folder cannot be created.
- Missing email subject line.
- Missing invoice number or amount for invoice email templates.
- Missing document request has no missing items and no manual missing items.

**Needs Review** means generation is allowed but the package clearly shows warnings. Examples:

- Fee Amount is zero/blank for engagement letters.
- Payment Link is missing for invoice emails.
- Due Date is in the past or within 7 days.
- Template name includes old/draft/copy/deprecated.
- User overrode auto-filled values.
- Outlook was requested but unavailable.

**Ready** means no blockers and no significant warnings.

## Outlook draft safety

Occam Template Desk never sends email. When `local_outlook` is enabled on Windows with pywin32 available, the app creates/opens a draft only after validation has no blockers. If Outlook or pywin32 is unavailable, the app generates fallback files instead and records that fallback in the audit trail.

## Binary artifact policy

Generated `.xlsx`, `.docx`, `.pdf`, image, output, and generated folders are intentionally ignored by Git. Keep source code, text templates, configs, tests, and documentation in the repository; regenerate sample binary files locally with `python -m occam_template_desk.setup_samples`.

## Known limitations

- This is a local-first V1; no cloud database, authentication, Microsoft Graph, or multi-user permission model is included.
- Word rendering preserves basic template package structure and replaces placeholders, but complex placeholders split across multiple Word runs may need template cleanup.
- PDF export is not included in V1.
- The sample workbook writer/reader is intentionally lightweight for local demo/test portability; production deployments should use pandas/openpyxl as listed in `requirements.txt`.

## Future enhancements

- Richer template diagnostics for Word run-splitting.
- Optional PDF export through LibreOffice.
- Expanded validation rules maintained in Excel.
- Attachment workflows for generated documents.
- More detailed audit search and package filtering.
- Practice-management integrations after pilot validation.
