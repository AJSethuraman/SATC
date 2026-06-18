# SATC System — Tax Line-Sheet, Client Data Mart & Drake-Adjacent Tooling

**Sethuraman Accounting, Tax & Consulting (SATC)** — *Complex work, made clear.*

A layer **around** Drake Software for a tax practice that prepares 1040, 1120-S,
1065, and 1120 returns plus related state returns (Ohio, Michigan, Massachusetts
first). This tool is **not** a tax engine and does **not** replace Drake's
calculation or e-file. Drake remains the system of record for the filed return and
for computations like depreciation and basis. This system provides the workpapers,
the cross-checks, the year-over-year client data, the Drake input/reconcile seam,
and the client communications around it.

> Architecture note: this package re-implements the proven CRR
> (credit-risk-review) reference shape — document extraction → staging →
> human confirmation → dated reference layer → config-driven line sheets →
> normalized database → dashboards — adapted to a tax practice. The
> `crr_system/` reference was not present in this repository, so the patterns
> were rebuilt from specification.

## Hard rule: PII never lives in the workbook

Two physically separated layers:

| Layer | Contents | Where |
|-------|----------|-------|
| **Identity vault** | `client_id` ↔ legal name, full SSN/EIN, addresses, contacts | external / access-controlled (Teams/SharePoint) — `satc.models.identity` models the seam |
| **Working data mart** | de-identified records keyed by `client_id + tax_year + return_type + jurisdiction`; only masked/last-4 values | the Excel workbook now; a SQL database later — `satc.models.mart` |

Source documents are referenced by **SharePoint link + `document_id`**, never
embedded. The whole model is designed to port to SQL with no restructuring (stable
keys, normalized line-item tables, no data in merged cells). Solo practice today —
clean seams left for multiple preparers and an eventual multi-tenant product.

## What's here

```
satc_system/
  src/satc/
    ids.py                stable composite keys (client_id|year|return_type|jurisdiction)
    masking.py            SSN/EIN masking (shared convention with drake-entry-assistant)
    models/               provenance · review schema · identity vault · staging gate · data mart
    crosswalk/            dated tax-law reference layer (loader)
    ingest/               document extraction + staging/confirmation gate        (Stage 1)
    workbook/             SATC branding + config-driven line-sheet/dashboard builders
    proforma/             roll-forward / proforma + prior-vs-current comparison   (Stage 5)
    drake/                preparer-set PDF parser · comms generator · input gen   (Stage 6)
    fixtures/             synthetic, masked clients (NEVER real PII)
  configs/
    crosswalk/<JURIS>/<YEAR>.yaml   tax-law parameters by tax year × jurisdiction (Stage 2)
    line_sheets/<RETURN>.yaml       config-driven workpaper definitions
    extraction/                     document field maps
    drake/ · comms/                 preparer-set titles · communication templates
  scripts/
    recalc.py             LibreOffice formula recalculation (vendored from the xlsx skill)
    export_pdf.py         branded PDF export (headless LibreOffice)
    build_workbook.py     assemble the full workbook, recalc to zero errors
  docs/                   METHODOLOGY · USER_GUIDE · DATA_MODEL
  tests/
```

## Build standards

* Zero formula errors (run `scripts/recalc.py` until clean).
* Formulas, never hardcoded values; carryforwards reference the data mart.
* Every hardcoded tax parameter carries a source citation (see `configs/crosswalk`).
* Conservative extraction: stage and flag uncertainty; never guess a dollar amount
  or a tax-law value (a missing value is recorded as a *pending* gap).

## Coordination with `drake-entry-assistant`

This system does **not** duplicate the Drake auto-entry tool. Its Drake **input
generator** emits an intake workbook in the exact `Clients` / `W2s` shape that
`drake-entry-assistant` already consumes, so the existing tool produces the keying
action plan. This system owns the workpapers, the data mart, reconciliation back to
Drake's output, and client communications.

## Environment setup

```bash
# LibreOffice Calc is REQUIRED for recalculation (core-only silently no-ops):
apt-get install -y libreoffice-calc
pip install -e .[dev]            # from satc_system/

PYTHONPATH=src pytest -q                       # run tests
PYTHONPATH=src python scripts/build_workbook.py # build the demo workbook
python scripts/recalc.py build/SATC_Workbook.xlsx
```

## The app: door-to-return flow

A local, hand-holding GUI backed by the SQLite store of record (Excel stays a
first-class *export*). Point it at a folder and it carries documents all the way
to posted, sourced facts on the return.

```bash
pip install -e .[dev]          # flask + pypdf + reportlab
satc app                       # opens http://127.0.0.1:5050
```

1. **Intake** — point at any folder. A combined multi-form PDF (one scanned stack)
   is **split into its parts first** (per-page classification; an illegible or
   continuation page stays attached to the form before it). Each document is then
   classified by *content*, not its name (a W-2 saved as `scan0012.pdf` is still
   recognized), and read by the cheapest sufficient backend:

   | Rung | Signal / reader | Cost |
   |------|-----------------|------|
   | 1 | PDF form fields (a fillable form's field names are its fingerprint) | free, exact |
   | 2 | Embedded PDF text — weighted-keyword typing + **label-anchored value extraction** | free, no OCR |
   | 3 | Filename hint | free, weak — fallback only |
   | 4 | Vision/OCR (`ANTHROPIC_API_KEY`) | small per-doc cost — true scans only |

   Classification uses weighted keyword scoring with a *don't-guess* threshold: when
   two forms score close (a consolidated 1099, an 1120-S vs 1065 K-1), the result is
   flagged MEDIUM for review rather than guessed. Signatures live in
   `configs/classification.yaml`; form-field fingerprints derive automatically from
   the extraction maps. Sensitive identifiers (SSN/EIN/any TIN) are always masked.

2. **Sort & re-label** — `satc sort FOLDER` previews a clean by-type tree
   (`_SATC_Sorted/W-2/W-2 - <employer>.pdf`); `--apply` writes it. Combined PDFs are
   split into one file per form in the tree. **Non-destructive:** it only ever
   *copies* (or writes split pages) — originals are never moved, renamed, or deleted.

3. **Staging** — extracted values land here and are *not trusted* until confirmed.
   HIGH-confidence values auto-confirm; everything else waits for review. SSN/EIN are
   masked to last-4; unreadable amounts are flagged, never guessed.

4. **Post** — confirmed values project onto the 1040 line ids (every W-2 box 1 summed
   into wages, etc.) and are written to the data mart's normalized `line_items` with
   SOURCE_DOC provenance, then persisted. Re-posting is idempotent.

```bash
satc sort /path/to/client/folder          # preview the sort plan
satc sort /path/to/client/folder --apply  # write clean copies
satc seed && satc export DataMart.xlsx     # seed store, export the mart to Excel
```
