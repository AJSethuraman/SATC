# PRD: Mode B — Product-Conformance Review (consumer / residential)

**Status:** Draft · **Owner:** SATC owner · **Last updated:** 2026-07-05

> The second review mode the Credit Review OS schema has carried since v1
> (`review_mode: product_conformance`, reserved). Where Mode A analyzes the
> credit of individual commercial files, Mode B tests whether a **retail
> origination program conforms to policy** on a sampled basis, and classifies
> the pool by **delinquency per the Uniform Retail Credit Classification and
> Account Management Policy (URCCP)**. Grilled to alignment 2026-07-05; parent
> PRD: `prd-credit-review-os.md`.

---

## 1. Problem

The owner's retail-side review work — consumer installment, cards, home
equity — doesn't fit the loan-level engine: retail credit is underwritten by
scorecard and policy, reviewed by **testing the origination process on a
sample** (did files conform to the credit box?) and by **pool-level
delinquency classification**, not by re-analyzing each borrower's cash flow.
This is the owner's deepest domain strength, and today it lives in ad-hoc
spreadsheets with none of the enforcement, self-proving methodology, PII
discipline, or repeatability the Mode A engine now provides.

## 2. Solution

Extend `credit-review-os` with the product-conformance mode: one **`PS_<product>`
tab per retail product** holding (a) a **conformance sample grid** — one row
per sampled file (loan number only, never a person's name), one column per
program-declared policy test, mixing reviewer attestations with **computed
tests over keyed underwriting attributes** — and (b) a **pool classification
panel** where keyed delinquency buckets classify **by live formula per URCCP**.
Findings fire on **exception rate vs per-class tolerance knobs** (compliance
fails per-occurrence), a computed **FRINGE flag** drives a live buy-box
fringe-vs-core norms comparison, and everything rolls into the existing
Findings / de-identified mart / `_methodology` machinery. Same two-layer
config, same deterministic core, same workbook-is-source-of-truth principle.

## 3. Goals & Non-Goals

**Goals**
- A committee-grade retail review workbook from config + synthetic data: per-
  product conformance grids, URCCP classification, tolerance-based findings,
  fringe-vs-core analytics, sampling evidence — all live formulas.
- Both **random and judgmental sampling first-class**: the sample plan is
  named segments with documented basis and size; every grid row is
  segment-tagged; coverage math is live.
- URCCP enforced by formula the way Mode A enforces the criticized/classified
  boundary — with the bank's stricter policy expressible via overlay knobs.
- PII bar **stricter than Mode A**: zero individual-person names anywhere in
  Mode B artifacts; loan/account number is the file identity.

**Non-Goals / Out of scope**
- **No computed regulatory compliance.** Reg checks (flood determination,
  TRID timing evidenced, right of rescission, re-aging within URCCP limits)
  are reviewer-keyed attestations — the tool never recomputes APRs, TRID
  timelines, HMDA data, or adverse-action logic.
- **No statistical sample-size calculator** in v1 (attribute-sampling math is
  roadmap; the documented judgmental/random basis IS the v1 method).
- **No mixed-mode workbooks.** One engagement workbook = one `review_mode`; a
  bank getting both books gets two workbooks. (Roadmap if engagements demand.)
- **No allowance/CECL math**, same as Mode A — classification totals are
  produced, not provisioned.
- **No per-file credit re-underwriting** — that's Mode A's job; Mode B tests
  conformance of the origination decision, not its wisdom.
- **No fair-value computation** for the residential 180-day writedown — the
  URCCP writedown is captured as an attestation test, not a calculation.

## 4. User Stories

1. As a reviewer, I want one `PS_` tab per retail product with the sample
   grid and pool panel together, so a product's whole story sits on one sheet.
2. As a reviewer, I want grid rows identified by loan/account number only, so
   no individual's name ever enters the deliverable.
3. As a reviewer, I want each product's conformance tests declared in the
   program config (attestation or computed), so adding a test is config, not
   code.
4. As a reviewer, I want to key underwriting attributes (score, DTI, LTV/CLTV,
   term) per file and have attribute tests computed against the overlay's
   policy limits, so conformance is objective where it can be.
5. As a reviewer, I want a computed FRINGE flag when a file's attributes sit
   within the overlay's fringe band of a policy limit, so buy-box-edge
   originations are identified by formula, not memory.
6. As a reviewer, I want a live fringe-vs-core comparison of exception rates,
   so I can show the committee whether edge-of-box lending underperforms norms.
7. As a reviewer, I want every sampled file tagged with its selection segment
   (random / judgmental strata from the sample plan), so the methodology
   demonstrates both sampling approaches and results can be read by segment.
7a. As a reviewer, I want random sampling to support stratification — e.g.
    stratify by commitment band and subproduct, then allocate 90/10 across
    strata — with each stratum a named segment carrying its own size, basis,
    and live analytics, so my actual sampling design is representable, not
    flattened into prose.
7b. As a reviewer, I want the conformance test set defined once in a shared
    library and referenced per product (DTI recalculation, credit-report
    review, income verification, and the like are near-uniform across retail
    products), so tests stay consistent across products and a wording fix
    lands everywhere.
8. As a reviewer, I want per-test exception rates computed against per-class
   tolerance knobs, with a finding firing when tolerance is exceeded, so one
   stray doc miss is noise but a pattern is a finding.
9. As a reviewer, I want compliance-test failures to be findings
   per-occurrence regardless of rate, because there is no tolerable rate of
   flood-insurance violations.
10. As a reviewer, I want to key the pool's delinquency buckets from the
    servicing report and get Substandard/Loss totals computed per URCCP by
    product type, so retail classification is enforced, not asserted.
11. As a reviewer, I want the residential panel to take qualifying ≥90-DPD
    balances (LTV > 60%) with the 60% line as a documented knob, and the
    180-day fair-value writedown captured as an attestation, so the resi
    branch follows URCCP without inventing a valuation engine.
12. As a reviewer, I want a product roll-up sheet (population, sample,
    coverage, exception rates, classification totals per product), so the
    committee sees the retail book at a glance.
13. As a reviewer, I want Mode B findings in the same Findings register
    machinery (status/owner/due/cleared) keyed by (product, test), so
    exception tracking to resolution works identically across modes.
14. As the owner, I want the de-identified mart and re-ingest to emit
    product-level records (and segment-level rates), so cross-engagement
    retail analytics need no PII ever.
15. As the owner, I want `_methodology` to cite URCCP for the classification
    spine and document the segment-based sampling design, so the deliverable
    is self-proving for the retail book too.
16. As a maintainer, I want the whole mode verified at the existing seams
    (recalc vs hand-tallied values, re-ingest round-trip, PII byte-scan,
    determinism), so Mode B can't silently regress Mode A.

## 5. Requirements

1. [P0] **Program schema, Mode B shape.** A `review_mode: product_conformance`
   program declares a shared **`test_library[]`** — the largely-uniform retail
   test set defined once (`{id, label, class: policy|documentation|compliance,
   severity, kind: attestation | computed, when:}`; e.g. DTI recalculated and
   within policy, credit report present and reviewed, income verified, flood
   determination, re-aging within URCCP limits) — and `products[]`; each
   product: `id`, `label`, `classification_type` (`closed_end` | `open_end` |
   `residential_secured`), `attributes[]` (numeric grid columns:
   `{id, label, fmt}`), `tests[]` (references into the library by id, plus
   product-specific test definitions or overrides inline), and `fringe_rules[]`
   (`{attribute, limit_key, band_key, direction}`). `computed` tests use the
   existing token grammar over attribute columns and `[POL]` knobs — the
   "calculate DTI and check it" style test is a keyed `dti` attribute plus a
   computed comparison to the overlay ceiling. The builder's current
   `ConfigError` gate on `product_conformance` is removed by this build.
2. [P0] **Overlay, Mode B shape.** Per product: `population` (count + $),
   `sample_plan.segments[]` where each segment is
   `{id, label, method: random | judgmental, stratum: {<dimension>: <band>},
   size, basis}` — **stratified random sampling is first-class**: a random
   design stratified by e.g. commitment band × subproduct with a 90/10
   allocation is expressed as one random segment per stratum (allocation
   rationale documented in `basis`); judgmental segments (targeted officer,
   vintage, all ≥120 DPD, buy-box fringe pulls) sit beside them. Every grid
   row is tagged with its segment id; coverage and exception-rate analytics
   compute **per segment/stratum** as well as overall. Plus policy limits and
   fringe bands as `thresholds` knobs, per-class `tolerances`
   (`{policy: 0.05, documentation: 0.10, compliance: 0.0}`-style), and the
   loans/files fixture pointer.
3. [P0] **`PS_<product>` sheet.** Sample grid: one row per sampled file —
   loan number, segment tag (validated against the sample plan), keyed
   attribute columns, one column per conformance test (attestation dropdown
   pass/fail/na, or computed flag), and a computed per-file FRINGE flag.
   Pool panel: keyed delinquency buckets (current, 30-59, 60-89, 90-119,
   120-179, 180+; count + $) with URCCP classification computed live:
   closed-end Substandard = 90-119 + 120-179 + 180+, Loss = 120-179 + 180+;
   open-end Substandard = ≥90, Loss = ≥180; residential Substandard = keyed
   qualifying ≥90-DPD balances (LTV > 60% qualifier; 60% line a knob) and the
   180-day fair-value writedown as an attestation test. Citations: 65 FR
   36903 (June 12, 2000); OCC Bulletin 2000-20; FDIC FIL-40-2000.
4. [P0] **Test analytics per (product, test):** applicable n (na excluded),
   fail count, exception rate, tolerance (from `[POL]`-style knob cells on
   `_config`), and a finding flag — all live formulas. Compliance-class tests
   flag on any fail regardless of rate.
5. [P0] **Fringe-vs-core norms block** per product: overall fail rate for
   FRINGE rows vs non-fringe rows (live), plus a flag when the fringe rate
   exceeds core by the overlay's margin knob.
6. [P0] **Findings integration.** Register rows keyed (product, test) with
   rate/tolerance/flag references and the standard tracking lane
   (status/owner/due/cleared); aggregates by class/severity/status/product;
   an asset-quality block with URCCP Substandard/Loss totals per product and
   portfolio.
7. [P0] **Product roll-up sheet** (Mode B's Master): one formula row per
   product — population count/$, sample n, coverage %, open findings,
   exception rate, Substandard $, Loss $.
8. [P0] **De-identified mart + re-ingest.** Mart rows per product (and
   per-segment rates); `ingest_workbook` handles Mode B workbooks via the
   `_map` structure; outputs carry loan numbers? **No** — mart and re-ingest
   outputs are product/segment level only; loan numbers stay in the workbook.
9. [P0] **PII (stricter than Mode A):** zero individual-person names anywhere
   in Mode B sheets, fixtures, marts, or exports; file identity = loan number;
   TIN never (not even last-4 — retail files don't need it). Seam-3 guard
   extended accordingly. Encryption-at-rest unchanged.
10. [P0] **v1 program + demo:** one `retail` program with three products —
    indirect auto (closed_end), credit card (open_end), HELOC
    (residential_secured) — plus a synthetic demo overlay/fixtures with
    hand-tallied expected values covering: each URCCP branch, a
    tolerance-exceeded policy test, a compliance per-occurrence finding, a
    fringe-vs-core gap, and both segment types.
11. [P1] **`_methodology` for Mode B:** crosswalk gains URCCP-cited
    classification element and a sampling-design element (segments, basis,
    coverage); pin-cite caveat unchanged.
12. [P1] **README + BACKLOG** updates (mode matrix, PII delta, roadmap
    check-offs).

## 6. Implementation Decisions

- **Reuse, don't fork.** `_config` knob panel, `[POL]` token resolution,
  Findings tracking-lane pattern, mart flat-grid, `_map` JSON, determinism
  helpers, and the crypto/CLI/bundle layers are shared. Mode B adds sibling
  sheet builders (product sheet, product roll-up) and mode branches at the
  workbook-assembly seam only; `build_engagement_workbook` dispatches on
  `program.review_mode`.
- **Grid computed tests use the existing grammar** with row-relative
  attribute references (each grid row resolves `{attr}` to that row's
  attribute cell — the Mode B analogue of Mode A's `{row_id}` resolution).
- **FRINGE flag** = OR over the product's `fringe_rules`: attribute within
  `band` of `limit` on the policy side (e.g. score ≤ floor + band; DTI ≥
  ceiling − band). Both `limit_key` and `band_key` resolve to `_config` cells.
- **Segment tags** are data-validated against the overlay's segment ids;
  segment/stratum analytics use SUMPRODUCT over the tag column (same
  discipline as the Findings aggregates). Stratum descriptors are free-form
  key/value pairs rendered into the sampling-evidence block — the tool
  documents and computes against the strata; it does not draw the sample.
- **Test library resolution** happens at config load: each product's `tests[]`
  expands referenced library ids into full test definitions (inline overrides
  win), so the sheet builders see one flat per-product test list — no
  library awareness below the config layer.
- **Delinquency buckets are the interface to the bank.** The tool never
  computes DPD from dates; the reviewer keys the servicing report's bucket
  totals. Re-aging abuse is covered by an attestation test citing URCCP's
  re-aging standards, not by recomputation.
- **CLI/bundle** work unchanged (`--program retail`); `credit-review build`
  on a Mode B overlay produces the retail workbook.

## 7. Testing Decisions

- **Seam 1 (primary, existing): the in-memory builder + `formulas` recalc**
  against hand-tallied expected values for the synthetic demo: URCCP totals
  per branch, per-test rates and tolerance flags, per-occurrence compliance
  finding, fringe-vs-core rates and gap flag, segment coverage math,
  determinism (byte-identical).
- **Seam 2 (existing): re-ingest round-trip** — build → key values → ingest →
  product/segment-level outputs match the workbook's own aggregates; no loan
  numbers in re-ingest output.
- **Seam 3 (existing, strengthened): no-PII byte-scan** — zero person-name
  strings in any Mode B artifact (fixtures carry no person names to leak, and
  the guard asserts the absence class-wide), no TIN patterns, loan numbers
  absent from mart/export.
- **What a good test proves:** URCCP is enforced by the workbook as Excel
  evaluates it; tolerance and fringe analytics match hand arithmetic; Mode A's
  85 tests keep passing untouched.
- **Prior art:** `tests/test_exceptions.py`, `test_master.py`,
  `test_ingest.py`, `test_pii_guard.py`, `test_lob_programs.py`.

> **PII / sensitive-data rules (binding, stricter than Mode A):** Mode B
> artifacts contain **no individual-person names, ever** — workbook, fixtures,
> mart, exports, logs. File identity is the loan/account number, which stays
> in the (encrypted-at-rest) workbook only; mart and re-ingest outputs are
> product/segment level. No TIN in any form. All fixtures 100% synthetic.

## 8. Success Metrics

- One command builds the three-product retail demo workbook; recalc shows 0
  discrepancies vs hand-tallied URCCP totals, rates, and fringe analytics.
- Adding a fourth retail product (e.g. unsecured personal) is config-only.
- Seam-3 scan: zero person names / TIN patterns in every Mode B artifact.
- Mode A suite unchanged and green (85 tests) alongside the new Mode B tests.

## 9. Milestones / Rollout

- **M1:** schema + one product (indirect auto) end-to-end: grid, URCCP panel,
  rates/tolerances, Findings, roll-up, mart/ingest, PII guard. (Tracer.)
- **M2:** credit card + HELOC branches, fringe-vs-core block, segments math,
  `_methodology` additions, demo + full test bar, README/BACKLOG.

## 10. Risks & Open Questions

- **Risk — grid width.** Attributes + tests can push `PS_` sheets wide;
  mitigation: per-product column sets are config, keep demo ≤ ~14 columns,
  and the committee reads the analytics blocks, not the raw grid.
- **Risk — URCCP nuance drift.** Program/overlay knobs must stay ≥ URCCP
  floors; a validation rule should reject tolerances/thresholds that would
  *loosen* the regulatory floor (e.g. Loss later than 120/180 days).
- **Open question (needs your desk):** confirm URCCP pin-cites against the
  live PDFs before the first filed retail workpaper (same caveat as Mode A;
  regulator sites block automated fetch).

## 11. Done Criteria

- [ ] Requirements R1–R12 met; user stories 1–16 satisfied
- [ ] Tests green at Seams 1–3, including hand-tallied URCCP branch coverage,
      tolerance/per-occurrence findings, fringe-vs-core, segment coverage
- [ ] Mode A's existing suite untouched and green
- [ ] Demo workbook built, opened, and eyeballed (LibreOffice render)
- [ ] README (mode matrix, PII delta) + BACKLOG (roadmap check-offs, [LOG]
      items: mixed-mode workbooks, statistical sample-size calculator) updated
- [ ] URCCP citations added to `docs/research/credit-review-methodology.md`
