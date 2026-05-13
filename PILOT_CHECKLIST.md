# Occam Template Desk — Pilot Checklist

Use this checklist before and during a limited internal pilot.

## Setup checklist

- [ ] Install dependencies from `requirements.txt`.
- [ ] Generate local sample assets with `python -m occam_template_desk.setup_samples`.
- [ ] Launch the app with `streamlit run occam_template_desk/app.py`.
- [ ] Confirm Settings paths are correct.
- [ ] Confirm output folder is writable.

## Data workbook checklist

- [ ] Workbook has `Settings`, `Clients`, `Invoices`, and `Missing Items` sheets.
- [ ] Client sheet includes `Client ID`, `Client Name`, and `Client Email`.
- [ ] Invoice sheet includes `Invoice Number`, `Client ID`, `Invoice Amount`, and `Due Date`.
- [ ] Missing Items sheet includes `Client ID`, `Missing Item`, and `Status`.
- [ ] Test clients include at least one complete client and one incomplete client for validation testing.
- [ ] Source workbook is backed up and treated as read-only during generation.

## Template checklist

- [ ] Templates are in `Documents` or `Emails` subfolders.
- [ ] Email templates begin with `Subject:`.
- [ ] Required placeholders match workbook/settings headers.
- [ ] Optional placeholders use `{{optional:Field Name}}`.
- [ ] Word placeholders are typed as continuous unformatted tokens.
- [ ] No production template file name contains old/draft/copy/deprecated unless intentional.

## Test run checklist

- [ ] Generate an engagement letter package.
- [ ] Generate an invoice email package.
- [ ] Generate a missing document request package.
- [ ] Confirm validation report opens.
- [ ] Confirm generated files have no unresolved `{{placeholder}}` tokens.
- [ ] Confirm output package includes audit log, input snapshot, rendered values, and validation report.

## Reviewer checklist

- [ ] Review final status: Ready, Needs Review, Blocked, or Do Not Send.
- [ ] Review blockers and warnings.
- [ ] Review field sources and overrides.
- [ ] Review generated files.
- [ ] Confirm any manual overrides are appropriate.
- [ ] Confirm no email was sent automatically.

## Outlook draft checklist

- [ ] Outlook mode is intentionally set.
- [ ] Output status is not Blocked or Do Not Send.
- [ ] No unresolved placeholders remain.
- [ ] Attachments are explicitly selected if needed.
- [ ] If Outlook is unavailable, use copy-ready fallback files.
- [ ] Confirm `outlook_status.json` and `audit_log.json` record the attempt.

## Known limitations

- Local-first only; no cloud database or multi-user permissions.
- No Microsoft Graph integration.
- No automatic sending.
- Attachments are explicit and not guessed.
- Complex Word formatting can split placeholders; retype broken placeholders in plain text.
- PDF export is not part of V1.

## Go/no-go criteria

Go when:

- [ ] Test packages are generated successfully.
- [ ] Validation reports are reviewer-friendly.
- [ ] Staff understand how to add templates and read validation results.
- [ ] Outlook fallback behavior is acceptable.

No-go when:

- [ ] Required fields are unclear or frequently missing.
- [ ] Templates produce unresolved placeholders.
- [ ] Reviewers cannot interpret validation reports.
- [ ] Users expect automatic sending or automatic attachment guessing.
