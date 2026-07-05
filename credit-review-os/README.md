# Credit Review OS

A portable, rules/framework-driven **loan-review workpaper system** for the
consulting side of SATC: it configures product/LOB-specific review programs
and produces bank-committee-grade Excel workpapers — linesheet per loan →
master roll-up → de-identified data mart → findings — with a built-in
regulatory crosswalk that proves the methodology satisfies the interagency
standard.

- **PRD:** [`docs/prd-credit-review-os.md`](docs/prd-credit-review-os.md)
- **Domain research (cited):** `docs/research/credit-review-methodology.md` at the repo root
- **Single-operator consulting tool.** The deliverable is a self-contained,
  emailable workbook per engagement. Not origination, not servicing, not the
  bank's system of record, not portfolio monitoring (the credit-risk `.xlsm`
  template series does that).

## What a build produces

One workbook per engagement, in the KeyBank house style:

| Tab | What it is |
|---|---|
| `Cover` | Engagement identity, scope, reviewer independence attestation |
| `LS_<loan>` | One linesheet per loan: identification & exposure, cash flow, collateral & leverage, compliance, evidence checklist — reviewer keys the cream input cells; exceptions and the rating-disagreement finding compute by live formula |
| `Master` | Portfolio roll-up: one formula-driven row per loan (exposure, both ratings, regulatory bucket, criticized/classified flags, open-exception count) |
| `Data Mart` | De-identified flat grid keyed by engagement-scoped ids — no name, no loan number, no TIN |
| `Findings` | Exception register (formula refs into each linesheet) + aggregates by class/severity/status/loan + the criticized/classified asset-quality summary |
| `_methodology` | Regulatory crosswalk (every program element → interagency requirement, cited) + coverage/independence/reporting evidence |
| `_config` | The knob panel: thresholds, rating-scale map, review as-of date — `[POL]`/`MAP()`/`[ASOF]` formulas resolve here, so editing a knob recomputes the workbook |
| `_readme` | Usage, pin-cite caveat, PII rules |

## Two-layer config

- **Program** (`src/credit_review/programs/<lob>.yaml`) — portable and
  **client-agnostic**: the interagency rating framework (Pass / Special
  Mention / Substandard / Doubtful / Loss with criticized/classified
  derivations), linesheet sections and exception rules, the evidence
  checklist, and the cited regulatory crosswalk. The loader rejects
  client-specific keys outright. Shipped programs: `c_and_i`,
  `cre_income_producing` (NOI DSCR, occupancy, appraised-value LTV, rent
  roll), `owner_occ_cre` (occupant-business global cash flow per the RC-C
  owner-occupied definition), `construction_adc` (loan-to-cost, interest
  reserve, as-completed LTV, draw inspections), and `agricultural` (farm
  operating DSCR, carryover debt, farmland/chattel LTV, crop insurance).
- **Engagement overlay** (`engagements/<name>.yaml`) — thin and per-bank:
  client identity, `review_as_of`, `rating_scale_map` (every internal grade →
  exactly one regulatory bucket), policy `thresholds` (DSCR floor, LTV and
  leverage ceilings, staleness windows — bank-policy values, so they are
  config), scope, reviewer independence, and the loan list.

Adding a client bank = writing an overlay. Adding a line of business = writing
a program. Neither is a code change.

## Two review modes — both built

| | Mode A — `loan_level` | Mode B — `product_conformance` |
|---|---|---|
| Reviews | individual commercial credit files | retail origination programs, on a sample |
| Tab per | loan (`LS_`) | product (`PS_`) |
| Reviewer keys | figures, ratings, evidence dates | attributes + pass/fail/na per sampled file; pool delinquency buckets |
| Findings | each fired exception | exception **rate vs tolerance** per test (compliance: per-occurrence) |
| Classification | reviewer's bucket via the rating-scale map | **URCCP by formula** (closed-end 90/120, open-end 90/180, residential qualifier + writedown); overlay may tighten, never loosen |
| Roll-up | `Master` | `Products` (+ buy-box fringe-vs-core and per-stratum analytics) |
| File identity | borrower name + loan # (workbook only) | **loan # only — no person names, ever** |
| Programs shipped | `c_and_i`, `cre_income_producing`, `owner_occ_cre`, `construction_adc`, `agricultural` | `retail` (indirect auto, credit card, HELOC) |

Mode B PRD: [`docs/prd-mode-b-product-conformance.md`](docs/prd-mode-b-product-conformance.md).
Sampling is segment-based — stratified random (e.g. commitment band ×
subproduct, 90/10 allocation) and judgmental strata are both first-class, and
a computed FRINGE flag compares buy-box-edge originations to core norms.

## Build & verify

```bash
pip install -e .
credit-review build src/credit_review/engagements/demo_engagement.yaml --plain -o demo.xlsx
credit-review build src/credit_review/engagements/demo_engagement.yaml          # encrypted
credit-review ingest DEMO-2026-01.xlsx.enc --json findings.json
credit-review bundle src/credit_review/engagements/demo_engagement.yaml         # DLP-safe ASCII
credit-review build src/credit_review/engagements/demo_retail_engagement.yaml --program retail --plain -o retail.xlsx
pip install -e .[test] && pytest -q                                              # 106 tests
```

The `bundle` command emits a single pure-ASCII script (the repo's contract
§11 transmission pattern): run `python build_credit_review.py` on a machine
behind a bank's DLP boundary (only openpyxl + PyYAML needed) and it rebuilds
the workbook there, byte-identical, printing its SHA-256.

Tests run at three seams (PRD §7): the in-memory builder with the `formulas`
recalc engine against hardcoded expected values (Seam 1), the re-ingest
round-trip (Seam 2), and the no-PII-leak byte scan (Seam 3).

## Principles (binding)

- **Deterministic core.** No network, no clock in outputs: same inputs →
  byte-identical workbook (`workbook_bytes` pins zip and docProps
  timestamps). Evidence currency is measured against the engagement's
  `review_as_of`, never `TODAY()`.
- **The workbook is the source of truth.** Exceptions, rating validation, and
  roll-ups are live Excel formulas resolved from the token grammar
  (`{row_id}`, `[POL key]`, `[ASOF]`, `MAP(expr)`) — never precomputed
  results. The Python re-ingest pass re-evaluates the workbook
  deterministically; it does not shadow-compute its own answers.
- **No LLM in the data path — ever.** Roadmap items (OCR pre-fill, a local
  extraction assist) may only propose values a human confirms into the
  workbook; nothing generated writes a review value or a rating.
- **PII.** Borrower name + loan number appear in the engagement workbook only
  (the bank's own data, returned to the bank), which is **AES-256-GCM
  encrypted at rest** (key DPAPI-sealed on Windows, 0600 elsewhere —
  `satc_system`'s vault pattern). TINs are last-4 only, everywhere — loaders
  reject full-TIN shapes and the builder masks defensively. The Data Mart and
  every re-ingest export are de-identified (engagement-scoped ids). Every
  fixture in this repo is synthetic, and Seam-3 tests fail the build on any
  leak.
- **Cite the method.** Every program element carries its interagency citation
  in the crosswalk; page pin-cites must be confirmed against the live PDFs
  before a filed workpaper (the `_readme`/`_methodology` tabs carry this
  caveat).

## LOB roadmap (cash-flow-out order)

~~income-producing CRE~~ → ~~owner-occupied CRE~~ → ~~construction/ADC~~ →
~~agricultural~~ (all shipped, config-only) →
**consumer + residential (first product-conformance build — needs its own
design pass)** → multifamily / leases / specialty. Each is a new program
config + crosswalk on the same engine. Further out (each needs its own
design pass): document parsing/OCR pre-fill, an optional **local**
human-confirmed LLM extraction assist (never in the data path), and export
of classifications for the bank's ACL/CECL system.
