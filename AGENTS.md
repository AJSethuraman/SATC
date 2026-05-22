# Occam Template Desk Agent Instructions

## Project purpose
Occam Template Desk is an internal, local-first operations tool for generating client-facing documents and draft emails from reusable templates and an Excel workbook.

## Design philosophy
- Build practical, polished workflows that are pilot-ready, not throwaway scripts.
- Keep business-editable content in Excel, templates, or settings where reasonable.
- Preserve source templates and source data. Generation must create copies only.
- Prioritize clear validation, auditability, and user-facing explanations.
- Use restrained professional services styling: navy structure, gold accents, grays, green Ready/success, amber Needs Review/warnings, red Blocked/errors.
- Never rely on color alone; include labels such as Ready, Needs Review, Blocked, Warning, Success, and Error.

## Commands
- Run tests: `pytest`
- Run the Streamlit app: `streamlit run occam_template_desk/app.py`
- Run the CLI demo: `python -m occam_template_desk.demo`

## Test expectations
- Add or update pytest coverage for scanner, data loading, validation, rendering, package building, audit, and Outlook fallback behavior.
- Tests should not require Outlook, pywin32, network access, or mutation of source sample templates/data.

## Style requirements
- Keep Python modules focused and readable.
- Prefer small dataclasses and plain dictionaries over heavy frameworks for V1.
- Avoid raw stack traces in the UI; show friendly errors and log details in output artifacts.
- Do not put try/catch blocks around imports.

## Safety constraints
- Do not auto-send emails.
- Do not modify source templates during generation.
- Do not modify the Excel database during generation.
- Outlook integration may create/open drafts only when explicitly enabled and validation has no blockers.
- If Outlook/pywin32 is unavailable, gracefully fall back to copy-ready files.
- Do not add cloud databases, authentication, Microsoft Graph, automatic sending, e-signature, production deployment, or practice management integrations in V1.
