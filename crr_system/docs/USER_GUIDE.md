# CRR Line Sheet System — User Guide

## Setup

```bash
pip install openpyxl pdfplumber pypdf python-docx fpdf2 pytest
# Optional, for scanned-PDF OCR:
pip install pytesseract pdf2image

# LibreOffice is used for recalculation and PDF export. IMPORTANT: many
# minimal images ship only libreoffice-core, which makes every spreadsheet
# operation fail with "type detection failed" while recalc reports a false
# success. Install Calc explicitly:
apt-get update && apt-get install -y libreoffice-calc
```

All commands below run from the `crr_system/` directory.

## Build the workbook

```bash
python3 fixtures/make_fixtures.py     # regenerate sample source documents
python3 -m workbook.build             # builds output/CRR_Line_Sheet_System.xlsx
```

The build prints the recalculation report; `"status": "success"` with
`"total_errors": 0` is the acceptance bar. To verify everything:

```bash
python3 -m pytest tests/ -q           # engine + workbook validation tests
python3 scripts/export_pdf.py output/CRR_Line_Sheet_System.xlsx   # visual PDF
```

## Daily workflow

### 1. Ingest documents into staging

```bash
# Regulatory guidance / internal policy (Type A thresholds):
python3 -m engine extract-thresholds path/to/bulletin.pdf \
    --workbook output/CRR_Line_Sheet_System.xlsx \
    --citation "OCC Bulletin 2013-9" \
    [--agency OCC --agency FDIC]          # override auto-detection
    [--effective 2013-03-21]              # override date parsing
    [--unverified]                        # status unknown -> Coverage Gap rows
    [--rescission-doc path/to/notice.pdf] # apply a rescission in the same pass

# A rescission notice against rows already staged:
python3 -m engine apply-rescission path/to/notice.pdf \
    --workbook output/CRR_Line_Sheet_System.xlsx

# A credit memo / underwriting package (Type B assertions):
python3 -m engine extract-cam path/to/CAM.docx \
    --workbook output/CRR_Line_Sheet_System.xlsx [--borrower "Name"]
```

Accepted inputs: `.pdf` (OCR fallback if scanned and pytesseract is
installed), `.docx`, `.txt`/`.md`, `https://` URLs. For pasted text, call
`engine.ingest.ingest("label", pasted_text="...")` from Python.

### 2. Confirm staged rows (in Excel)

Open the workbook, go to **Staging_TypeA** / **Staging_TypeB**:

- Check each row's **Verbatim Source Span** and **Page / Section** against the
  source document.
- Amber rows = Low confidence (the extractor found competing values — its note
  says which). Red rows = Coverage Gap (status unverified; resolve before
  confirming).
- Set **Reviewer Confirmation** to `Confirmed` or `Rejected`. For Type B rows,
  enter your **CRR Independent Value** and `Agree`/`Disagree`.

### 3. Promote confirmed rows

```bash
python3 -m engine promote --workbook output/CRR_Line_Sheet_System.xlsx
```

Confirmed thresholds appear on **Crosswalk** (with Active/Rescinded status as
of the Settings date); confirmed assertions appear on **Assertions**. Pending
and Rejected rows never leave staging.

### 4. Complete a line sheet

Open the segment's `LS_*` sheet:

1. Fill Section A (credit identification — blue cells; grades from the 1-8
   dropdown). **Review Date drives which thresholds apply to this credit.**
2. Enter your own spread in Section B. These are *your* numbers, not the
   memo's.
3. In Section C, type the memo's stated ratios into **Per CAM (Asserted)**
   (or read them off the Assertions sheet). The form computes your
   independent value, the variance, and the threshold flag.
4. Answer every question `Yes / No / N/A / Obs`. `No` and `Obs` require a
   note — the Check column and row highlighting will not let a blank slide.
5. Watch the Review Summary: completion %, exceptions, observations, and
   outstanding note checks.
6. Write the grade rationale in the conclusion box.

### 5. Save the form to the database

```bash
python3 -m engine save-form --workbook output/CRR_Line_Sheet_System.xlsx \
    --sheet LS_CI --status Complete
python3 scripts/recalc.py output/CRR_Line_Sheet_System.xlsx
```

`save-form` upserts the Database row (matched on Credit ID) and replaces that
credit's Responses rows; the recalc refreshes every dashboard. Then clear the
form for the next credit.

## Reading the dashboards

- **Dash_Portfolio** — reviews/exceptions/downgrades by segment, LOB-vs-CRR
  grade distribution, and the migration matrix (shading right of the diagonal
  = downgrades).
- **Dash_Exceptions** — counts **No answers only**, by segment (rate excludes
  N/A), severity, and aging bucket, plus a detail list with rationales.
- **Obs_View** — observations only. The by-section rollup highlights sections
  with 2+ observations across files: candidate thematic findings.
- **Dash_Concentration** — CLD/capital, CRE/capital and 36-month growth
  against the 2006 criteria in force per the Crosswalk (criteria trigger
  heightened scrutiny, not caps), and the leveraged-lending status-by-agency
  table demonstrating per-agency versioning.
- **Dash_Trends** — reviews, watch (SM), and classified (6+) counts by review
  quarter.

## Settings that matter

- **Review As-Of Date** — "today" for reporting: drives crosswalk status on
  dashboards and exception aging. Line-sheet thresholds use each form's own
  review date instead.
- **Primary Supervisory Agency** — whose thresholds the dashboards and the
  regulatory-threshold lookups on forms cite (internal-policy metrics always
  use the `Internal` tag).
- Capital inputs feed Dash_Concentration; keep the source notes current.

## Adding a segment

See "Extending the system" in METHODOLOGY.md — add one entry to
`workbook/content.py` and rebuild; no builder changes needed.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| recalc reports success but dashboards show no numbers in Excel-free tooling | libreoffice-calc not installed — the macro silently no-ops. `apt-get install -y libreoffice-calc`, rerun recalc. |
| Threshold cell blank, flag "n/a" | No confirmed Active crosswalk row for that metric/agency as of the form's review date — either genuinely rescinded/not yet effective, nothing promoted yet, or a Coverage Gap awaiting resolution. |
| Row red in Staging_TypeA | Coverage Gap: the extractor could not verify current status. Verify the rule's status, fill effective/rescinded dates, then confirm. |
| `save-form` ratios land empty in Database | The workbook was not recalculated since inputs changed — run `scripts/recalc.py` (or open/save in Excel) before `save-form`. |
| Duplicate staging rows | Re-running extraction on the same document is deduplicated by row ID; "skipped" in the CLI output is normal. |
