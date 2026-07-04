# SATC System — Methodology

*Sethuraman Accounting, Tax & Consulting — "Complex work, made clear."*

## What this is (and is not)

This system is the **layer around Drake**, not a tax engine. Drake remains the
system of record for the filed return and for computations such as depreciation,
basis, and the §199A QBI deduction. This system owns everything *around* the
calculation: intake, document extraction with a human confirmation gate, organized
per-return workpapers with cross-checks, a dated tax-law reference layer, a
year-over-year client data mart, a Drake input/reconcile seam, client
communications, a document audit trail, and practice dashboards.

> **Reference implementation.** The kickoff referenced a `crr_system/`
> credit-risk-review system to reuse (document extraction → staging → confirmation
> → dated reference layer → config-driven line sheets → normalized DB →
> dashboards). That system is **not present in this repository**, so the same
> architecture was rebuilt from specification. The shapes are deliberately
> CRR-aligned so that, if the real `crr_system/` is added, the two converge.

## First principles

1. **PII never lives in the workbook.** Identity (legal name, full SSN/EIN,
   addresses, contacts) lives in an external, access-controlled vault. The
   workbook references clients only by an opaque `client_id` and stores only
   masked / last-4 values. Source documents are referenced by SharePoint link +
   `document_id` — never embedded. A test (`test_validation.py`) fails the build
   if a client legal name or full TIN ever appears in the workbook.
2. **Nothing is trusted until confirmed.** Extracted values land in a staging area
   with provenance and confidence. Only the preparer's confirmation promotes a
   value into a workpaper or the data mart. Unparseable values are flagged for
   review — never guessed.
3. **Every figure traces to a source.** A confirmed source document, a prior-year
   carryforward from the data mart, Drake output, a tax-law parameter, or a
   preparer entry. Provenance travels with the value.
4. **Formulas, not hardcoded results.** The workbook ships with live Excel
   formulas; carryforwards reference the data mart; tax parameters are *linked*
   from the dated reference sheet, never typed into a workpaper.
5. **Never guess tax law.** Each parameter carries a citation. Where a value is not
   yet published (e.g. a post-sunset figure), it is recorded as a **pending gap**,
   not invented.
6. **Build for the practice now; architect for the product later.** Solo practice
   today, but the data model is normalized and SQL-portable with stable keys, and
   clean seams are left for multiple preparers and an eventual multi-tenant
   product (per-firm isolation).

## Architecture (data flow)

```
   Source docs (SharePoint)                Drake preparer-set PDF (OUTPUT)
            │                                        │
   extraction engine                          preparer-set parser
   (conservative parsing)                     (keys off worksheet titles)
            │                                        │
            ▼                                        ▼
        ┌──────────────  STAGING / CONFIRMATION GATE  ──────────────┐
        │   only HIGH-confidence auto-confirms; rest needs review   │
        └───────────────────────────┬──────────────────────────────┘
                                     │ confirmed values
              ┌──────────────────────┼───────────────────────┐
              ▼                       ▼                        ▼
     Config-driven           Client DATA MART          Reconciliation
     line sheets   ◀── carryforwards ──  (normalized,   (workpaper vs Drake;
     (1040/1120S/                         year over year) flags tie to 0)
      1065/1120)                              │
              │                               ├── roll-forward / proforma → next year
              │                               └── prior-vs-current comparison (variance flags)
              ▼
     Dated TAX-LAW crosswalk (tax_year × jurisdiction; Fed + OH/MI/MA)
              │
              ▼
     Drake input generator ── (Clients/W2s shape) ──▶ drake-entry-assistant
              │
              ▼
     Client delivery package (summary + draft email + cover letter)  ──▶ Document & comm repository
              │
              ▼
     Practice dashboards (pipeline · deadlines · open items · fees · YoY)
```

## The dated tax-law crosswalk (versioning)

Parameters are keyed by **tax_year × jurisdiction**. A workpaper for (year Y,
jurisdiction J) links the parameters in force for (Y, J). Each parameter has a
status: `in_force`, `scheduled_reversion`, or `pending`. The TCJA-after-2025
sunset is the versioning test fixture: the 2026 Federal file deliberately mixes
published COLA items (in force), sunset-affected items (scheduled reversion), and
not-yet-published items (pending gaps) — proving the engine versions correctly and
records gaps instead of guessing. Re-verify any figure at build time; OBBBA
(P.L. 119-21) modified several TCJA provisions and is flagged where relevant.

## Stage map

1. Data model (vault vs mart) + extraction engine + staging/confirmation gate.
2. Dated tax-law reference layer (tax_year × jurisdiction; TCJA-sunset fixture).
3. 1040 reference line sheet (intake, schedules, state, §8867, Drake reconcile).
4. 1120-S / 1065 / 1120 line sheets (basis/capital/M-1 rollforwards).
5. Client data mart + roll-forward/proforma + prior-vs-current comparison.
6. Drake preparer-set parser + communication generator + data-mart seed.
7. Document & communication repository + practice dashboards.
8. Validation: synthetic multi-year clients, zero formula errors, provenance
   intact, carryforwards tie, no PII in the workbook; methodology + user guide.

## Build standards

* Zero formula errors — run `scripts/recalc.py` until clean. (LibreOffice Calc is
  required; without `libreoffice-calc` installed, recalc silently no-ops.)
* Formulas not hardcoded; carryforwards reference the data mart; tax parameters
  linked from the reference sheet.
* Data-validation dropdowns; consistent number/date formats; a source note on
  every hardcoded tax parameter.
* Conservative extraction: stage and flag uncertainty.
* Synthetic / masked fixtures only — never commit real client PII.
