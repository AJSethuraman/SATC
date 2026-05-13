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
8. If an invoice template is selected, choose the invoice when multiple invoices exist; a single invoice is auto-selected.
9. Review and override values for the current run only.
10. Review validation status: **Ready**, **Needs Review**, or **Blocked**.
11. Preview the document/email with template diagnostics and matched/missing fields.
12. Generate an output package with rendered files, audit log, input snapshot, rendered values, and validation report.
13. The post-generation success panel remains visible after Streamlit reruns and shows generated files, audit/report paths, copy-ready email content, next action, and **Clear / Start New Draft**.
14. If enabled, use the post-generation **Create Outlook Draft** action; otherwise copy-ready fallback files are created.

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

The tests cover placeholder scanning, normalization, openpyxl workbook loading when available, client match fields, invoice selection logic, validation blockers/warnings, rendering, post-render placeholder checks, package artifacts, validation reports, audit logs, source immutability, and Outlook draft/fallback behavior.

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
- `local_outlook`: optional, local-only Outlook draft creation on Windows with pywin32 after validation passes. The draft is opened/saved only; no email is sent automatically.
- `fallback_files`: generate copy-ready email draft files and metadata only when Outlook is disabled or unavailable.

## Output packages

Each run creates a collision-resistant folder named like:

```text
YYYYMMDD_HHMMSS_ClientName_TemplateName_ab12cd34
```

The short run ID suffix prevents duplicate generation in the same second from failing.

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

When `openpyxl` is installed, the report includes navy title rows, a large status summary area, blocker/warning counts, generated files, gold status accents, gray table headers, freeze panes, reviewer-friendly column widths, and explicit Ready / Needs Review / Blocked / Do Not Send / Warning text labels. A lightweight fallback writer is used in constrained environments.

## Workbook loading and matching

Occam Template Desk uses `openpyxl` to load normal Excel workbooks when available and falls back to the lightweight reader only in constrained environments. Loading is read-only and handles blank cells, dates, numeric values, and sparse rows. Client selection displays names for humans but matches internally using the configured `client_match_field`, such as `Client ID` or `Client Name`.

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

## Pilot documentation

- See `TEMPLATE_AUTHORING_GUIDE.md` for non-developer instructions on adding templates, required placeholders, optional placeholders, email subjects, Excel header matching, and Word placeholder limitations.
- See `PILOT_CHECKLIST.md` for setup, workbook, template, reviewer, Outlook, and go/no-go checklists for a limited internal pilot.

## Optional placeholders

Use `{{optional:Field Name}}` for values that may be blank, such as `{{optional:Spouse Name}}` or `{{optional:Additional Notes}}`. Optional fields show as Optional in the field review table, render as blank when missing, and do not block generation.

## Attachments

Email attachments are explicit and not guessed. In local Outlook mode, the final action panel lets the user select generated `.docx` or `.pdf` package files as attachments. If none are selected, the Outlook draft is created without attachments and the audit trail records that no attachments were included.

## Outlook draft safety

Occam Template Desk never sends email automatically. Outlook draft creation is optional, local-only, and available only when `local_outlook` is enabled on Windows with pywin32. The app shows a post-generation **Create Outlook Draft** action and creates/opens a draft only after validation has no blockers and no unresolved placeholders. If Outlook or pywin32 is unavailable, copy-ready email files are generated and remain available; the app shows a friendly warning, writes `outlook_status.json`, and updates `audit_log.json`. Attachments are not fully automated in V1 unless explicitly provided to the Outlook workflow by future local code changes.

## Missing items formatting

The generated workbook can provide `{{Missing Items}}` as a readable multiline list, for example:

```text
- Signed engagement letter
- December bank statement
```

HTML email rendering converts multiline values into simple line breaks for copy-ready review.

## Binary artifact policy

Generated `.xlsx`, `.docx`, `.pdf`, image, output, and generated folders are intentionally ignored by Git. Keep source code, text templates, configs, tests, and documentation in the repository; regenerate sample binary files locally with `python -m occam_template_desk.setup_samples`. During generation, the source Excel workbook and source templates are read-only inputs and are never modified.

## Known limitations

- This is a local-first V1; no cloud database, authentication, Microsoft Graph, or multi-user permission model is included.
- Word rendering preserves basic template package structure and replaces placeholders, but complex placeholders split across multiple Word runs may need template cleanup. Post-render checks mark output **Blocked - Do Not Send** and prevent Outlook draft creation if any `{{placeholder}}` tokens remain. Source Word templates are never modified.
- PDF export is not included in V1.
- The sample workbook writer/reader is intentionally lightweight for local demo/test portability; production deployments should use pandas/openpyxl as listed in `requirements.txt`.

## Future enhancements

- Richer template diagnostics for Word run-splitting.
- Optional PDF export through LibreOffice.
- Expanded validation rules maintained in Excel.
- Attachment workflows for generated documents.
- More detailed audit search and package filtering.
- Practice-management integrations after pilot validation.
