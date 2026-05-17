# Linesheet Builder

Linesheet Builder is a local, pilot-ready Python product for producing consistent, professional, audit-ready commercial loan linesheets from a controlled workpaper workflow.

It helps credit review, internal audit, compliance/testing, and loan review teams:

1. Create/select a client engagement.
2. Upload and preserve a raw loan tape.
3. Map incoming columns to a standard schema.
4. Validate source records conservatively.
5. Generate review cases.
6. Answer configurable YAML-driven linesheet questions.
7. Track warnings, blockers, findings, comments, evidence status, reviewer/QC status, and audit events.
8. Export polished Excel workbooks and data mart, exceptions, and audit CSV files.

## What this is not

Linesheet Builder is **not** an underwriting system, loan origination system, credit decision model, predictive score, AI extraction tool, or LOS integration. It does not make credit decisions and does not use external paid APIs.

## Stack

- Python
- Streamlit
- SQLite
- Pandas
- Pydantic
- PyYAML
- OpenPyXL
- pytest

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

The app initializes `data/app.db`, creates demo data, and uses the sidebar navigation:

- Dashboard
- Setup
- Upload
- Mapping
- Validation
- Review
- Export
- Audit

## Run tests

```bash
pytest
```

## Demo workflow

1. Run the app.
2. Select **Demo Bank**.
3. Select **Commercial Linesheet v1**.
4. Upload or load demo loan tape.
5. Confirm mapping.
6. Run validation.
7. Select a Ready or Warning loan.
8. Complete review questions.
9. Generate Excel linesheet.
10. Export data mart CSV.
11. Review audit log.

## Included demo data and template

- Demo loan tape: `data/demo_loan_tape.xlsx`
- Mapping profile: `configs/mappings/demo_bank_mapping.yaml`
- Standard schema: `configs/standard_schema.yaml`
- Template: `configs/templates/commercial_linesheet_v1.yaml`

The demo loan tape includes 11 commercial loans with Ready, Warning, and Blocked examples, including duplicate loan IDs, missing borrower name, invalid maturity/origination relationship, low DSCR, high LTV, nonaccrual, past due, and policy exception scenarios.

The YAML template includes 25 questions across 10 sections:

1. Borrower / Relationship
2. Loan Terms
3. Approval / Authority
4. Collateral / Guarantors
5. Financial Analysis
6. Covenants
7. Documentation
8. Policy Exceptions
9. Review Conclusion
10. Signoff

## Generated files

- Raw preserved imports: `data/raw_imports/`
- Excel linesheet workbooks: `outputs/excel/`
- Data mart CSV: `outputs/data_mart/review_answers_export.csv`
- Exception report CSV: `outputs/exceptions/exceptions_report.csv`
- Audit log CSV: `outputs/audit/audit_log.csv`

Excel workbooks include:

- Cover
- Loan Summary
- Linesheet Questions
- Exceptions & Findings
- Evidence Checklist
- Audit Summary

## Auditability and blocking behavior

The app writes audit events for import creation, mapping saved, loan normalization, validation runs, answer changes, exception creation/update, and exports. Final Excel export is blocked unless validation blockers are clear, required answers are complete, findings/blockers have comments, evidence requirements are resolved, and the case status is Ready for QC or QC Approved. A pilot override reason can be entered in the Export screen and is logged.

## Known limitations

- Authentication is intentionally not implemented for the pilot.
- Evidence files are tracked by status only; file attachment storage is not implemented.
- PDF/DOCX output is not included in the MVP because the core required outputs are Excel/CSV.
- Rule expressions are intentionally limited to safe comparisons and boolean logic.
- The Streamlit UI is local-only and not cloud-deployed.

## Recommended next improvements

- Add lightweight local user profiles and role labels.
- Add evidence attachment upload and checksums.
- Add richer QC review and returned-item workflows.
- Add additional templates for CRE, SBA, and consumer compliance testing.
- Add export packaging for engagement-level batches.
- Add migration versioning for database upgrades.
