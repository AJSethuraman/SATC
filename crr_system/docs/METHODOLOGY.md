# CRR Line Sheet System — Methodology

## Purpose and supervisory basis

This system supports an independent credit risk review (CRR) function operating
under the 2020 **Interagency Guidance on Credit Risk Review Systems** (OCC,
FRB, FDIC, NCUA). The governing principle is that a credit risk review unit
*may use information produced by the line of business — the credit memo, the
LOB spread, the assigned grade — but must critically evaluate it and form its
own view rather than rely on it exclusively.*

Every design decision below operationalizes that principle:

| Guidance principle | System mechanism |
|---|---|
| Form an independent view | Ratio engine recomputes every asserted ratio from the reviewer's own spread; asserted and independent values sit side by side with a variance flag |
| Traceability | Every extracted fact carries the verbatim source span and page/section it came from; no row exists without provenance |
| Critically evaluate, don't transcribe | Extracted rows are **staged**, never live, until a human confirms them |
| Cite the rule in force | Thresholds are agency-tagged and dated; each line sheet looks up the threshold in force **on its own review date** for the relevant agency |

## The extraction → staging → confirmation → live pipeline

```
source documents                 staging (quarantine)            live reference layer
─────────────────                ─────────────────────           ─────────────────────
regulatory PDFs    ─┐            Staging_TypeA                   Crosswalk
internal policy    ─┼─ engine ─► Staging_TypeB     ─ reviewer ─► Assertions
credit memos (CAM) ─┘            (verbatim span,     confirms    (read by line sheets
pasted text / URLs               page, confidence,               and dashboards)
                                 Pending status)
```

1. **Ingest** (`engine/ingest.py`). PDF (pdfplumber, with an OCR fallback hook
   for scanned files via pytesseract/pdf2image when installed), Word (.docx),
   pasted text (form-feed = page break), and URLs (PDF or HTML) all normalize
   to a list of pages with 1-based numbers. Section labels are inferred from
   heading-like lines so every anchor reads "p.2, UNDERWRITING STANDARDS".

2. **Extract** (`engine/extract.py`). One engine, two row types sharing one
   schema (`engine/schema.py`):
   - **Type A — thresholds** from regulatory/policy documents: metric, value,
     unit, basis, citation, issuing agency, effective date, rescinded date
     (nullable), status. Interagency documents emit **one row per issuing
     agency**, which is what makes per-agency rescission representable.
   - **Type B — credit-memo assertions**: borrower, facility, stated ratios,
     assigned grade, repayment sources, guarantor support, covenants,
     collateral, key assumptions. Each row has empty independent-value,
     variance, and agree/disagree columns for the reviewer.

   Value selection is positional: the engine prefers the numeric candidate
   nearest *after* the metric phrase ("DSCR of 1.25x"), then *inside* a long
   keyword match, then nearest *before* ("in excess of 6.0x Total Debt to
   EBITDA"). A second distinct candidate inside the proximity window marks the
   row **Low confidence** and the extractor note names the competing values —
   the engine never guesses; the reviewer resolves it in staging.

3. **Stage** (`engine/staging.py`). Rows are appended (deduplicated by content
   hash) to `Staging_TypeA` / `Staging_TypeB` with confirmation = **Pending**.
   Low-confidence rows are amber; **Coverage Gap** rows (status that could not
   be verified at extraction time, `--unverified`) are red. Nothing downstream
   reads staging.

4. **Confirm**. A human reviews each row against the cited span and sets the
   dropdown to Confirmed or Rejected. This is the contamination barrier: a
   misparsed threshold that went straight to live logic would silently distort
   every line sheet citing it.

5. **Promote** (`python -m engine promote`). Only Confirmed rows copy to the
   live sheets. Type A rows land on **Crosswalk** with a status formula
   (`Active` / `Rescinded` / `Not Yet Effective` / `Unknown (Coverage Gap)`)
   evaluated against the workbook's as-of date, plus a `Metric|Agency` key
   column the line sheets use for lookups. Type B rows land on **Assertions**
   with the asserted-vs-independent comparison preserved.

## Crosswalk versioning

A threshold row is in force for agency *X* on date *D* when
`effective ≤ D` and (`rescinded` is empty or `D < rescinded`).

Because rows are per-agency, the December 2025 rescission of the 2013
leveraged-lending guidance by the OCC and FDIC (with the FRB not joining) is
representable exactly: the OCC and FDIC rows carry a rescinded date of
2025-12-16 while the FRB row's stays empty. As of 2026-06-10 the same 6.0x
threshold is simultaneously **Rescinded (OCC, FDIC)** and **Active (FRB)** —
this scenario is a permanent test fixture (`tests/test_engine.py`,
`tests/test_workbook.py`).

Two lookup contexts use the dating differently, deliberately:

- **Line sheets** resolve thresholds **as of the form's own review date**
  (`$F$5`), so a credit reviewed in August 2025 cites the 6.0x criterion that
  governed it, and the identical form dated January 2026 shows no OCC
  threshold at all.
- **Dashboards** (concentration, agency-status table) resolve **as of the
  global Review As-Of Date** on Settings — the current-state view for
  reporting.

Rescission notices are themselves extracted documents
(`engine extract-rescissions` / `apply-rescission`): the engine finds
"rescind" sentences, tags the agencies named in them, parses the date, and
stamps only matching agency rows (keyword overlap against the citation, with
the provenance of the rescission notice appended to the row's notes).

## The answer schema

Every question on every line sheet is answered from one four-value vocabulary,
enforced by data validation and used identically by all rollups:

| Answer | Meaning | Note | Counted in exceptions | In rate denominators |
|---|---|---|---|---|
| **Yes** | Clean pass | optional | no | yes |
| **No** | Exception / finding | required (rationale) | **yes — the only driver** | yes |
| **N/A** | Not applicable | optional | no | **no — excluded from numerator and denominator** |
| **Obs** | Pass with a note on record | **required** | **never** | yes |

Enforcement: a formula check column flags `Obs` or `No` with a blank note
("Note required" / "Rationale required"), conditional formatting highlights
the row, and the exceptions dashboard carries a "Notes Missing" KPI.
Observations surface **only** in the Observations view, which also rolls them
up by section — one Obs is noise; the same Obs across many files is a
potential thematic finding. Obs never auto-escalates.

## Independent-view mechanics on the line sheets

Each segment form's ratio engine has, per ratio:

- **CRR Independent** — computed by formula from the reviewer's own spread
  inputs (blue cells), never typed in;
- **Per CAM (Asserted)** — the LOB's stated value (blue input; for the C&I
  demo credit these tie to the Assertions sheet extracted from the sample CAM);
- **Variance** and an **Alignment** flag (>5% relative variance flags
  "Variance" and shades the row amber);
- **Threshold (In Force)** — green cross-sheet lookup against the Crosswalk,
  dated to the review; **Vs Threshold** — Pass / Exception / n/a.

The C&I sample credit intentionally demonstrates a disagreement: the memo
asserts 3.6x interest coverage, the independent spread computes 5.0x, and the
asserted global DSCR of 1.55x re-derives at 1.46x.

## Data model

- **Database** — one row per credit per review: identifiers, segment, dates,
  reviewer, LOB vs CRR grade with concurrence formula, key ratios, exception /
  observation counts, completion %, exception rate, status. Derived columns
  are formulas over Responses, so the table recalculates as answers change.
- **Responses** — one row per question per credit: the single source for the
  exception dashboard (No only), observations view (Obs only), aging (days
  since review date vs the as-of date), and rates. Helper index columns
  (`ObsIdx`, `NoIdx`) drive the formula-based detail lists without array
  formulas.
- **Questions** — the registry (QID, segment, section, text, severity) from
  which all forms are generated and which `save-form` joins against.

## Sampling and demo data

The 24 sample credits (4 per segment, seeded RNG) exist to validate and
demonstrate: answers follow a realistic distribution, review dates span four
quarters for the trend views, and roughly a quarter of credits carry a
one-notch CRR downgrade. The "simulated reviewer" in the build script confirms
only High-confidence staged rows — Medium/Low rows are left Pending
deliberately so the gate is visible in the delivered file. In production, that
step is a human in Excel.

## Extending the system

Segments are configuration, not code. To add agribusiness, healthcare, or a
small-business-via-consumer-KRI segment:

1. Copy `SEGMENT_TEMPLATE` in `workbook/content.py` into `SEGMENTS` with a new
   code, name, sheet name, segment-specific sections/questions, inputs, and
   ratio templates (placeholders `[Input Label]`, denominators guarded).
2. Rebuild. The form, question registry, database vocabulary, and dashboards
   pick the segment up automatically (`question_rows` iterates `SEGMENTS`).
3. Add threshold patterns to `engine/extract.py` only if the new segment needs
   metrics the extractor doesn't already recognize.

Core questions (`CORE_QUESTIONS`) apply to every credit segment and map to
the 2020 criteria; segment files only declare what is *specific* to them.

### Non-credit review programs (general audit shops)

The **IA segment** in `content.py` is a worked example of repurposing the
template outside credit review. Optional config keys:

- `use_core_questions: False` — skip the credit core question set entirely;
- `header_labels` — relabel the Section A fields (Engagement ID, Auditable
  Entity, Mgmt Self-Assessed vs IA Concluded Rating, etc.);
- `form_title`, `asserted_label`, `independent_label` — retitle the form and
  the assert-vs-reperform columns ("Per Mgmt (Asserted)" / "IA Re-Performed");
- `commitment_fmt` — number format for the population/commitment field.

The architecture carries over unchanged: the staged-evidence pipeline, the
four-value answer schema with note enforcement, severity-tiered questions,
exception aging, and the thematic observations view are audit-generic. The
IA form's "ratio engine" becomes a sampling block (coverage, completion,
exception rate vs tolerable) with the same independent-vs-asserted variance
mechanics.

## Build standards

- Zero formula errors, verified by an actual LibreOffice recalculation
  (`scripts/recalc.py`; see USER_GUIDE for the libreoffice-calc prerequisite).
- Formulas, not hardcoded results: ratios, statuses, counts, and rates all
  reference inputs, Responses, or the Crosswalk.
- Color conventions: blue inputs, black formulas, green cross-sheet links,
  yellow key assumptions. Arial throughout.
- Number formats: `$#,##0` with units in headers, `0.0x` / `0.00x` multiples,
  `0.0%`, negatives in parentheses, zeros as "-".
- Hardcoded bank inputs on Settings carry source documentation (Call Report
  schedule and date).
