# SATC System — User Guide

## Setup

```bash
# LibreOffice Calc is REQUIRED for recalculation. Without it, recalc silently
# no-ops (reports success while computing nothing) — a known trap.
apt-get update && apt-get install -y libreoffice-calc

cd satc_system
pip install -e .[dev]          # or: pip install openpyxl PyYAML pytest
PYTHONPATH=src pytest -q       # run the test suite
```

## Build the demo workbook

```bash
PYTHONPATH=src python scripts/build_workbook.py      # builds + recalculates
python scripts/export_pdf.py build/SATC_Workbook.xlsx build   # branded PDF
```

The demo workbook contains: a branded **Cover**; the **Staging** confirmation
gate; **Tax Law** reference sheets (US + OH/MI/MA); a **1040** plus **1120-S /
1065 / 1120** workpapers; the **Data Mart**, **Prior-vs-Current**, and
**Proforma** sheets; the **Client Delivery** package; the **Document Repository**;
and the **Dashboards**.

## The engagement workflow

1. **Intake.** Source documents are stored in SharePoint and logged in the
   Document Repository (status `Requested` → `Received`). The missing-documents
   tracker lists anything still outstanding.
2. **Extract & stage.** Documents are reduced to labeled fields (form-field read /
   OCR / `pdftotext`) and run through a `MapExtractor` (config in
   `configs/extraction/`). Values land in **Staging** with provenance and
   confidence. Money that does not parse cleanly is flagged `NEEDS_REVIEW` — never
   guessed. Sensitive SSN/EIN fields are masked to last-4.
3. **Confirm.** The preparer confirms (or corrects) each staged field on the
   Staging sheet. Only `CONFIRMED` values flow into the workpaper and data mart.
4. **Workpaper.** The confirmed intake prefills the line sheet. Tax-law values are
   *linked* (gold) from the Tax Law sheet; carryforwards (green) come from the data
   mart; computed lines are formulas. Cross-checks show a live flag: green
   **ties** / red **REVIEW**.
5. **Key into Drake.** The Drake input generator emits a `Clients`/`W2s` workbook
   that the existing `drake-entry-assistant` consumes to drive keying.
6. **Reconcile.** Enter Drake's figures in the Reconciliation block; differences
   must tie to 0 and be signed off. §8867 EITC due-diligence items gate "ready to
   file".
7. **Deliver.** Parse the Drake preparer-set PDF (titles → fields). The Client
   Delivery sheet aggregates Federal + every state into one refund/balance-due
   summary and produces a **draft** email + cover letter (never auto-sent). Log the
   delivery to the repository.
8. **Seed next year.** The Comparison + Carryover pages seed the data mart; the
   Proforma roll-forward carries open carryforwards and basis/capital opening
   balances into next year.

## Extending the system

| To add… | Do this |
|---------|---------|
| a **tax year** | add `configs/crosswalk/<JURIS>/<YEAR>.yaml` with sourced citations; mark unpublished values `pending` |
| a **state** | add `configs/crosswalk/<STATE>/<YEAR>.yaml`; the line sheets pick it up via `{{STATE}}` templating |
| a **line** to a workpaper | add a row to `configs/line_sheets/<RETURN>.yaml` (kinds: input / computed / total / xwlink / xwfs / cflink / crosscheck / review). Reference earlier lines with `{id}`, tax law with `[XW …]`, carryforwards with `[CF …]` |
| a **document type** | add `configs/extraction/<doc>.yaml` (label → canonical field_path; `sensitive: true` masks SSN/EIN) and a `LineMapping` if it feeds a line sheet |
| a **client** | add an `IdentityRecord` to the vault; the workbook references it by `client_id` |

## Formula token grammar (line sheets)

```
{line_id}                 another value cell on the same sheet
[XW JURIS param]          a scalar tax-law value on the reference sheet
[XW JURIS param subkey]   a dict-valued tax-law value (e.g. by filing status)
[XWFS JURIS param fsline] tax-law value chosen by a filing-status cell
[CF cf_key]               a carryforward from the data mart (0 if none)
```

## Color legend

| Color | Meaning |
|-------|---------|
| Navy | Input — confirmed from a source document or keyed by the preparer |
| Ink/black | Computed — an in-sheet formula |
| Gold | Link — pulls a tax-law parameter from the Tax Law sheet |
| Green | Carryforward — pulled from the client data mart |
| Red | Exception / pending — needs attention |

## Guarantees

Run the validation suite before relying on a build:

```bash
PYTHONPATH=src pytest tests/test_validation.py -q   # no PII, provenance, carryforwards tie
python scripts/recalc.py build/SATC_Workbook.xlsx   # must report 0 errors
```
