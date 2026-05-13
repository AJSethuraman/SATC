# Occam Template Desk — Template Authoring Guide

This guide is for internal staff who create or update templates for Occam Template Desk.

## Where to put templates

Place templates in the local template folder configured in Settings:

- Document templates: `occam_template_desk/sample_templates/Documents/`
- Email templates: `occam_template_desk/sample_templates/Emails/`

For a pilot workbook/folder outside the sample area, keep the same two subfolders: `Documents` and `Emails`.

## Supported template types

- Word documents: `.docx`
- Plain text emails: `.txt`
- HTML emails: `.html`
- Markdown emails: `.md`

Generated sample `.docx` and `.xlsx` files are created locally with `python -m occam_template_desk.setup_samples` and are not committed to Git.

## Required placeholders

Use double braces around the Excel/settings header name:

```text
{{Client Name}}
{{Client Email}}
{{Tax Year}}
{{Fee Amount}}
{{Invoice Number}}
{{Invoice Amount}}
{{Due Date}}
{{Missing Items}}
```

Required placeholders must be filled before the output can be safely used. If a value is missing, the app blocks generation or marks the rendered output Do Not Send.

## Optional placeholders

Use the `optional:` prefix for fields that may be blank:

```text
{{optional:Spouse Name}}
{{optional:Additional Notes}}
{{optional:Retainer Amount}}
```

Optional placeholders appear in the field review table as Optional. If no value is found, they render as blank and do not block generation.

## Email subject lines

Email templates must start with a subject line:

```text
Subject: Invoice {{Invoice Number}} from {{Firm Name}}
```

The first line becomes the email subject and is removed from the body. Email templates without a `Subject:` line are blocked.

## Engagement letter templates

Use `.docx` and include clear placeholders for client, tax year, fee, partner, manager, and billing terms. Example:

```text
Dear {{Contact First Name}},
Thank you for selecting {{Firm Name}} for your {{Tax Year}} tax engagement.
Our fee is ${{Fee Amount}}.
```

## Invoice email templates

Invoice email templates should include invoice fields. If a client has multiple invoices, the user must select one.

```html
Subject: Invoice {{Invoice Number}} from {{Firm Name}}
<p>Amount due: ${{Invoice Amount}}</p>
<p>Due date: {{Due Date}}</p>
```

## Missing document request templates

Use `{{Missing Items}}` to insert a readable list. The user can edit the list for the current run without changing the workbook.

```text
Subject: Missing documents needed for {{Client Name}}
We still need:

{{Missing Items}}
```

## How Excel headers map to placeholders

Headers are matched by name with light normalization:

- `{{Client Name}}` matches `Client Name`
- `{{client_name}}` matches `Client Name`
- `{{client-name}}` matches `Client Name`
- Case does not matter

The app pulls values from Settings, Clients, Invoices, Missing Items, and user overrides.

## Common mistakes

- Missing `Subject:` line in email templates.
- Placeholder spelling does not match an Excel/settings header.
- Required placeholder is blank in the workbook.
- Invoice template is used for a client with no invoice.
- Old/draft/copy/deprecated file names create review warnings.

## Word placeholder limitations

Word can split text internally when formatting changes. To avoid broken placeholders:

- Type placeholders as one continuous token, e.g. `{{Client Name}}`.
- Do not bold, italicize, underline, or partially format inside a placeholder.
- Do not split placeholders across lines.
- Avoid copying placeholders from heavily formatted documents.
- If a placeholder does not fill, delete it and retype it manually in plain text.

## How to test a new template

1. Save the template in the correct folder.
2. Open Occam Template Desk and select the template.
3. Review Template Diagnostics and confirm placeholders are detected.
4. Select a test client.
5. Confirm fields are filled or intentionally optional.
6. Generate a package using non-client/test data first.
7. Open the validation report and generated files.
8. Confirm no unresolved `{{placeholder}}` tokens remain before using with a client.
