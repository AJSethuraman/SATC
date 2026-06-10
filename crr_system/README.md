# Credit Risk Review (CRR) Line Sheet System

Tooling for an independent credit risk review function: a **document-driven
extraction engine** that pulls regulatory thresholds and credit-memo
assertions into a staged, human-confirmed crosswalk, and a **single Excel
workbook** with line-sheet intake forms for six lending segments, a normalized
review database, and recalculating dashboards.

Built around the 2020 Interagency Guidance on Credit Risk Review Systems:
*use the line of business's information, but critically evaluate it and form
an independent view — never rely on it exclusively.* Every extracted fact
carries its verbatim source span and page; nothing goes live without reviewer
confirmation; every asserted ratio sits next to an independently derived one.

## Layout

```
crr_system/
├── engine/            extraction engine + CLI (python -m engine)
│   ├── ingest.py        PDF / DOCX / text / URL -> pages with anchors
│   ├── extract.py       Type A thresholds & Type B assertions, with provenance
│   ├── crosswalk.py     agency-tagged, as-of-date versioning & rescissions
│   ├── staging.py       staging sheets + Confirmed-only promotion
│   └── formio.py        save-form: line sheet -> Database/Responses
├── workbook/          workbook builder (python -m workbook.build)
│   ├── content.py       segments, questions, ratio specs (config-driven)
│   ├── forms.py         line-sheet template (C&I reference, all segments)
│   ├── database.py      credit-record + responses tables
│   ├── dashboards.py    portfolio / exceptions / observations / concentration / trends
│   └── build.py         orchestrator (build -> extract -> promote -> recalc)
├── fixtures/          synthetic known-value test documents (NOT live content)
├── tests/             31 tests: extraction, versioning, gating, workbook math
├── scripts/           recalc.py + export_pdf.py (LibreOffice; needs libreoffice-calc)
├── docs/              METHODOLOGY.md, USER_GUIDE.md
└── output/            CRR_Line_Sheet_System.xlsx (generated)
```

## Quick start

```bash
pip install openpyxl pdfplumber pypdf python-docx fpdf2 pytest
apt-get update && apt-get install -y libreoffice-calc   # core alone is NOT enough

cd crr_system
python3 fixtures/make_fixtures.py
python3 -m workbook.build          # must end status=success, total_errors=0
python3 -m pytest tests/ -q
```

Then see `docs/USER_GUIDE.md` for the ingest → confirm → promote → review →
save workflow, and `docs/METHODOLOGY.md` for the design rationale.

## Segments

C&I / Commercial (reference template) · CRE (with FIRREA/USPAP appraisal
checklist and property subtypes) · Leveraged Lending (add-back scrutiny,
repayment-capacity test, dated 2013-guidance crosswalk) · ABL (borrowing-base
mechanics) · ARG / Workout (ASC 326, nonaccrual, exit strategy) · General
Compliance (rating scale, CECL linkage, flood/HMDA touchpoints) ·
**Internal Audit (Generic)** — a non-credit template for general audit shops:
engagement scoping, control design/operating effectiveness, evidence and
workpaper standards, issue management, and a sampling block (coverage,
exception rate vs tolerable). It opts out of the credit core questions and
relabels the form (Engagement ID, Auditable Entity, IA Re-Performed vs Per
Mgmt Asserted), showing how to repurpose the template for any review program.
New segments are config entries in `workbook/content.py`, not code changes.

## Versioning proof (test fixture)

The 2013 leveraged-lending guidance fixture (6.0x / 4.0x / 3.0x, repay ≥50%
in 5–7 years) plus a December 2025 rescission notice prove that one threshold
can be simultaneously **Rescinded for the OCC and FDIC** and **Active for the
FRB** as of a date — and that a line sheet dated before the rescission still
cites the rule that governed it. These documents are *test fixtures only*; the
tool's real content comes from documents you supply at run time, and values
the engine cannot verify are recorded as Coverage Gaps, not asserted.
