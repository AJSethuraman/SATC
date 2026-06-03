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

The YAML template includes 27 questions across 10 sections:

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
- Cash Flow Analysis
- Ability-to-Repay (DTI)
- Collateral & LTV
- Debt Service (DSCR)
- Guarantor
- Global Cash Flow
- Leverage & Liquidity
- Borrowing Base
- Linesheet Questions
- Exceptions & Findings
- Evidence Checklist
- Audit Summary

## Cash Flow / Income Analysis worksheet

A broad, gross (pre-tax) income worksheet (the **Cash Flow** page and the **Cash Flow Analysis** Excel tab) that derives one **total qualifying monthly income** from any mix of sources: W-2 wages / paystub, self-employment (Schedule C, with depreciation add-back), business / K-1, rental (Schedule E), and other income.

- Each line is entered across up to **two periods** and normalized with a per-line **basis** (Annual / Monthly) and **method** (Latest / Average / Lower of). Salaried income uses one period + Latest; self-employed or variable income uses two periods + Average. Defaults live in `configs/cash_flow_v1.yaml`.
- Banking convention is built in: everything is gross/pre-tax, and for **K-1 business owners the qualifying cash flow is cash distributions actually received** — pro-rata ordinary business income is captured as a *reference only* line (role `reference`) and never added to qualifying income, because the company's earnings are separate from cash paid to the owner.
- In Excel the Monthly column is a live formula (basis + method via `SWITCH`), with dropdowns on the basis/method cells. Results carry into the linesheet: the qualifying income summary prints on the Cover and the metrics (qualifying monthly/annual income, business-income reference) are written to the data mart under a `cash_flow` section. The qualifying monthly income is the income basis the DTI / ATR worksheet expects.

## Ability-to-Repay (DTI) worksheet

The **DTI / ATR** page and the matching **Ability-to-Repay (DTI)** Excel tab capture a consumer ability-to-repay calculation from three fillable, config-driven blocks: monthly gross income, proposed housing expense (PITIA), and other monthly debt obligations. It computes total obligations, front-end and back-end DTI, and monthly residual income, and scores them against ability-to-repay guidelines.

- Line items and thresholds live in `configs/dti_worksheet_v1.yaml` — add or remove categories, or change the front-end / back-end / residual thresholds, without touching code.
- The Excel tab is a **live calculator**: subtotals and ratios are real formulas, and the ratio / residual / assessment cells are color-coded with conditional formatting (green within guidelines, amber exceeds target, red fails the maximum) that updates as amounts are edited.
- Default thresholds: 28% front-end target, 43% back-end target, 50% back-end maximum. Worksheet inputs are persisted per review case and every save is written to the audit log.
- An optional **Payroll Deductions** block (for purely payrolled / W-2 borrowers) lets you enter taxes and withholding straight from a pay stub to also show **net monthly income** and **net residual income**. It does not estimate taxes; leave it blank and the worksheet stays gross-only. DTI ratios remain gross-based; when withholding is entered, the residual-income floor is judged on net residual.
- The worksheet is a static fixture, but its **results carry into the linesheet**: when filled, an over-guideline ATR result is recorded as a case finding (so it appears in the Exceptions tab, the exception report and the cover findings count), the ability-to-repay summary is printed on the Cover, and the metrics (income, obligations, front/back DTI, residual, assessment) are written to the data mart export. An empty worksheet carries nothing.

## Collateral & LTV worksheet

The **Collateral** page and the **Collateral & LTV** Excel tab analyze how well a credit is secured. Each collateral item takes a market value and a type-specific **advance rate** (editable; defaults in `configs/collateral_v1.yaml`) to produce a net (eligible) collateral value, which is compared to total exposure (loan balance, senior liens, other) to compute:

- **LTV** (exposure ÷ market value) against a guideline (default 80%),
- **Collateral coverage** (net value ÷ exposure) against a minimum (default 100%), and
- **Excess / (shortfall)** of net collateral.

In Excel the eligible-value, totals and ratios are live formulas with color-coded conditional formatting. Like the other calculation fixtures, results carry into the linesheet: an undersecured or over-LTV result is recorded as a finding, the summary prints on the Cover, and the metrics flow to the data mart (`collateral_ltv` section and a `Collateral` table in the data mart workbook).

## Commercial analysis worksheets (DSCR, Leverage)

Two commercial-credit calculation fixtures complement Collateral:

- **Debt Service Coverage (DSCR)** — the **Debt Service (DSCR)** tab / **DSCR** page build cash flow available for debt service (CFADS) from signed line items (NOI/EBITDA, other cash flow, less capex/distributions), divide by total annual debt service for the **DSCR ratio**, and compute **debt yield** (NOI ÷ loan amount) for CRE. Thresholds (min DSCR 1.20x, min debt yield 9%) live in `configs/dscr_v1.yaml`.
- **Leverage & Liquidity** — the **Leverage & Liquidity** tab / **Leverage** page spread a few balance-sheet/earnings figures into **current ratio**, **working capital**, **debt-to-worth** and **debt-to-EBITDA**, scored against guidelines in `configs/leverage_v1.yaml`.

Both are live-formula Excel tabs with conditional formatting and follow the same carry pattern: a below-guideline result becomes a finding, the summary prints on the Cover, and metrics flow to the data mart (`debt_service` / `leverage` sections, and `DSCR` / `Leverage` tables in the data mart workbook).

### Guarantor and Global Cash Flow (Global DSCR)

- **Guarantor / Global Financial** — the **Guarantor** tab / page captures personal financial position (net worth, liquid assets), personal cash flow and personal debt service, producing **personal DSCR** and the personal-cash-flow figure the global roll-up needs (`configs/guarantor_v1.yaml`).
- **Global Cash Flow / Global DSCR** — the capstone. The **Global Cash Flow** tab combines **business CFADS** (DSCR) **+ guarantor personal cash flow** over **total** debt service for a single **global DSCR**. It has no inputs of its own; in Excel it uses **live cross-sheet references** to the Debt Service (DSCR) and Guarantor tabs, so editing either flows straight through. It carries its own finding when global coverage is below guideline, and is recomputed automatically whenever the DSCR or Guarantor worksheets change. Both add `Guarantor` / `Global` tables (and columns) to the data mart workbook.

### Borrowing Base (revolving lines / ABL)

The **Borrowing Base** tab / page computes eligible collateral × advance rate (eligible A/R, inventory, other), less reserves, to derive the **borrowing base**, then compares it to the line commitment and current outstanding for **net availability** (or any **overadvance**). Live-formula Excel tab with conditional formatting; carries an overadvance as a finding and adds a `BorrowingBase` table to the data mart workbook (`configs/borrowing_base_v1.yaml`).

## Per-template calc tabs and auto-feed

Each template declares which calculation worksheets attach to it via a `modules` list (empty = all). A consumer template might attach `cash_flow`, `dti`, `collateral`; a commercial one `cash_flow`, `dscr`, `guarantor`, `global`, `collateral`, `leverage` (selecting `global` automatically pulls in its `dscr` + `guarantor` feeders). Only the selected tabs are built and only their results print on the Cover. Pick the tabs in the **Template Builder** UI or set `modules=[...]` in `build_template`.

**Auto-feed:** when the **Cash Flow** worksheet is filled, its qualifying monthly income becomes the **DTI income basis** — in Excel the DTI income line is a live cross-sheet reference (`='Cash Flow Analysis'!F24`), so editing Cash Flow recalculates DTI. The Global DSCR tab similarly references the DSCR and Guarantor tabs. Enter income once; it flows through.

## Building custom templates en masse

Linesheet templates are plain YAML in `configs/templates/`, and the app is multi-template aware: it discovers every template in that folder, you pick one per engagement on the **Setup** page, and the **Templates** page browses them. The whole pipeline (validation, review, export) runs against whichever template the engagement uses.

Rather than hand-writing template YAML, use the **template builder** (`linesheet_builder/template_builder.py`) to author sheets in a few lines:

```python
from linesheet_builder.template_builder import q, section, build_template, write_template_yaml

t = build_template("consumer_mortgage_atr_v1", "Consumer Mortgage — Ability to Repay", [
    section("borrower", "Borrower / Relationship", [
        q("BR1", "Is the borrower identity documented?", required=True,
          exception_if='answer == "No"', severity="Finding", evidence_required_if='answer == "No"'),
    ]),
    section("income", "Employment & Income", [
        q("EI1", "Qualifying monthly income", "currency", required=True),
    ]),
])
write_template_yaml(t, "configs/templates/consumer_mortgage_atr_v1.yaml")
```

`build_template` validates structure and fills in display orders and `data_mart_field` / `export_label` defaults; `write_template_yaml` emits valid YAML that round-trips through `load_template_yaml`. A preset library (`preset_borrower`, `preset_employment_income`, `preset_atr`, `preset_collateral_property`, `preset_documentation`, `preset_conclusion_signoff`) makes assembly fast, and `template_builder.write_catalog()` writes a whole starter catalog at once (Consumer Mortgage ATR, HELOC, Auto/Installment, Small Business). Every template shares the same calculation fixtures (Cash Flow, DTI) and audit/export machinery.

## Engagement data mart (Excel)

The **Export** page can consolidate every linesheet in an engagement into a single pivot-ready Excel database (`outputs/data_mart/linesheet_data_mart.xlsx`, via `export_engine.generate_data_mart_workbook`). It is a small star schema of normalized Excel **Tables** you can pivot off directly:

- **Linesheets** — one row per loan / review case (the grain): client, template, validation & review status, completion %, findings count, and the carried DTI and Cash Flow results (back-end DTI, ATR assessment, qualifying income).
- **Answers** — one row per case × question (status, severity, exception flag, evidence).
- **Findings** — every exception/finding across the engagement.
- **DTI**, **CashFlow**, **Collateral**, **DSCR** and **Leverage** — the calculation results per case.
- **Audit** — the engagement's audit trail.
- **Overview** and **Data Dictionary** sheets describe the tables and key columns.

Each sheet is a named Excel Table (`tbl_Linesheets`, `tbl_Answers`, …) with autofilter and banded rows, so PivotTables and structured references work immediately. `review_case_id` is the key linking every table back to **Linesheets**.

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
