# PRD: Consumer Credit Population Analysis Bench

**Status:** Draft · **Owner:** SATC owner · **Last updated:** 2026-07-05

> A new **standalone** project in the credit-risk suite: an `.xlsm` template + a
> Python/pandas engine (single button) for **loan-level** consumer-loan
> population analysis. A bank credit reviewer loads a flat file, validates and
> cleans it, stratifies it deeply (mapped group-bys **and** user-defined derived
> cohorts, 5+ side-by-side), computes balance- and count-weighted portfolio
> metrics, and uses the ranked/flagged output to draw and document a **judgmental
> sample** for linesheet review. Grilled to alignment 2026-07-05 (`/occam`).
> Research reference: the supplied "Consumer Loan Portfolio Credit Review,
> Stratification, and Judgmental Sampling" technical reference is authoritative on
> formulas, thresholds, weighting, and guidance.

---

## 1. Problem

A bank credit reviewer preparing a retail linesheet review starts from a large,
homogeneous-looking flat file of consumer loans (one row per loan) — standard
loan-decision fields plus an open-ended tail of ad-hoc fields bolted on per
analysis. Today that work lives in ad-hoc spreadsheets: stratification is
hand-built and unrepeatable, weighted metrics are recomputed by hand (and easy to
get wrong on dollar-vs-count), the URCCP classification math is retyped, and the
sampling rationale is prose with no coverage math or self-proving methodology. The
reviewer needs to **partition the population by risk drivers**, compare subgroups
side by side to **surface off-linesheet findings**, and produce a **documentable,
non-extrapolable judgmental sample** — deterministically, on internal bank data
that never leaves the machine.

This is adjacent to `credit-review-os` Mode B (product-conformance), but Mode B
keys *pool totals* from a servicing report and *documents* a sample someone else
drew. This bench computes from **loan-level** data and helps the reviewer **draw**
the sample. It is a different tool that must not fork Mode B's correctness-critical
machinery (URCCP thresholds, the safe expression evaluator, the PII guard).

## 2. Solution

A self-contained `.xlsm` workbook whose one button runs a pandas engine:
**load → map columns (auto-propose + confirm) → validate/clean (gate) → compute →
write results back into the workbook.** The engine computes population-level
metrics (weighted averages, delinquency/default rates on **both** dollar and count
bases, counts, balances, URCCP classification, vintage curves, and a conditional
single-period roll/transition matrix) at two kinds of stratification: **(a)
group-by** mapped/derived columns and **(b) user-defined derived cohorts** built
from structured threshold/filter rules over canonical fields, compared side by
side (5+ simultaneous slices). It flags high-risk cells and computes coverage so
the reviewer can select a judgmental sample, then auto-generates the OCC-required
sampling documentation (population, areas of focus, sample size, selection
rationale, results), explicitly labeled non-extrapolable. Correctness-critical
constants (URCCP), the safe expression evaluator, and the PII byte-scan are
**shared from `credit-review-os`** so there is one implementation of each.

## 3. Goals & Non-Goals

**Goals**
- From a loan-level flat file, produce population and per-stratum metrics with the
  research doc's formulas: balance-weighted WA attributes (count-basis parallel)
  and **every rate on both dollar and count bases, always labeled**.
- Two stratification modes side by side: mapped **group-by** (a partition) and
  **derived cohorts** (arbitrary predicates, honestly reconciled with an overlap
  matrix and an unassigned residual); 5+ simultaneous slices.
- A **canonical-field contract** with a small hard-required core, feature-gated
  requirements per analysis, and a **confirm-not-silent** column-mapping layer
  that captures units/scale.
- A **population-validation / cleaning gate** that refuses on hard errors,
  auto-applies only safe declared normalizations, and records every change.
- URCCP classification, vintage analysis (within one file), and — **iff** a
  prior-bucket column is mapped — a single-period roll/transition matrix.
- Judgmental sampling support: rank/flag cells, compute coverage ($ and count),
  let the reviewer mark the selection, and auto-generate the OCC sampling doc,
  labeled non-extrapolable.
- A **clean hand-off deliverable**: self-contained `.xlsm`, emailable ASCII
  bundle (§11 of `TEMPLATE_CONTRACT.md`), workbook-is-source-of-truth.
- **One URCCP implementation** — shared from `credit-review-os`, never forked.

**Non-Goals / Out of scope**
- **No cross-period snapshot retention.** Single-file analysis only; time-series
  across reloaded periods is deferred (`[LOG]`). Vintage analysis *within* a
  single file **does** ship.
- **No multi-snapshot roll rates / Markov projection machinery.** Only the
  single-period transition matrix computable from a mapped prior-bucket column.
- **No net-of-recovery NCO.** The file carries charge-off flag + date + charged-off
  balance, **not** recoveries — so the tool reports a **gross** charge-off rate,
  explicitly labeled "gross-only, no recovery data." No net NCO, no
  average-balance annualization engine.
- **No statistical sampling / sample-size calculator** in v1. The documented
  judgmental basis is the method (statistical mode is a later option, per the
  research doc's benchmark note).
- **No auto-drawing of the sample.** The tool ranks, flags, and computes coverage;
  the **reviewer selects** the loans. (Consistent with Mode B: the tool documents
  and computes against the strata; it does not draw the sample.)
- **No provider seam, no network, no watchlist gate.** The flat file is the only
  input; the tool never fetches, scrapes, or leaves the machine.
- **No live Excel-formula math engine.** Computation is pandas behind the button;
  Excel is the load surface and the output (values) surface. (A minimal number of
  presentation formulas are acceptable but are not where correctness lives.)
- **No 8-digit FR Y-14Q segment-ID crosswalk** in v1 (a selectable Y-14Q *band
  preset* ships; the formal regulatory segment-ID emit is deferred, `[LOG]`).
- **No allowance/CECL provisioning.** Classification totals are produced, not
  provisioned.
- **No AI in the math path.** Deterministic, self-contained.

## 4. User Stories

1. As a reviewer, I want to paste/point the tool at a loan-level flat file on a
   raw tab and press one button, so the whole analysis runs without me writing
   code or formulas.
2. As a reviewer, I want the tool to **propose** a mapping from my messy headers
   to canonical fields and make me **confirm/override every row**, so a mis-named
   column never silently becomes the wrong metric.
3. As a reviewer, I want to declare each mapped column's **units/scale** (rate
   0.07 vs 7%; DTI/LTV scale; DPD as day-count vs bucket-label vs status; date
   format), so weighted metrics aren't silently 100× off.
4. As a reviewer, I want the mapping + units persisted in a visible `_map` tab
   that travels with the workbook, so the next person sees exactly how the file
   was interpreted.
5. As a reviewer, I want the tool to **refuse** on hard data errors (nulls in a
   required-for-analysis field, unparseable numerics/weights, duplicate loan ids)
   with a per-issue report, so I analyze a clean population, not a broken one.
6. As a reviewer, I want only **safe, declared** normalizations applied
   automatically (whitespace trim, declared unit rescale, canonical status
   mapping), each recorded in a `_cleaning` summary tab (rule + rows affected), so
   I can show exactly what was done to get the population clean.
7. As a reviewer, I want balance-weighted WA metrics (FICO, DTI, LTV/CLTV, rate,
   age/MOB, term) weighted by **current UPB** with a **count-basis parallel
   column**, so I see both the typical-dollar and typical-account views.
8. As a reviewer, I want **every delinquency/loss rate on both a dollar basis and
   a count basis, always labeled**, so I never present a delinquency number
   without its basis.
9. As a reviewer, I want URCCP classification computed from loan-level delinquency
   (closed-end Substandard ≥90 / Loss ≥120; open-end Substandard ≥90 / Loss ≥180;
   residential secured Substandard = qualifying ≥90-DPD with LTV>60%, 60% a knob),
   using the **same thresholds as `credit-review-os`**, so retail classification
   is enforced by one implementation.
10. As a reviewer, I want a **gross charge-off rate** (dollar + count) from the
    charge-off flag/date/charged-off balance, explicitly labeled "gross-only, no
    recovery data," so I don't overstate a net figure the data can't support.
11. As a reviewer, I want to **group-by** any mapped/banded field (FICO band, DTI
    band, LTV band, channel, product, vintage, delinquency status, balance band,
    ad-hoc tail field), so I get a clean partition of the population with per-cell
    metrics.
12. As a reviewer, I want to define **derived cohorts** as structured rule rows
    (field │ op │ value, ANDed, with OR-groups) on a `_cohorts` tab — e.g.
    "low-tradeline low-asset system-driven" = tradelines < X AND assets < Y AND
    channel = system — so I can express judgmental risk lenses without code.
13. As a reviewer, I want cohorts compared **side by side (5+ at once)** with each
    reported **independently**, plus a **pairwise overlap matrix ($ and count)**
    and an **"in no cohort" residual**, so I see double-counting and gaps instead
    of being misled by cohorts that don't partition.
14. As a reviewer, I want configurable band edges with a **CFPB six-tier FICO +
    36/43 DTI default**, a selectable **FR Y-14Q preset** (≤620/>620 + six DPD
    buckets), and **fully custom edges**, so the segmentation matches my bank
    without hard-coded bands.
15. As a reviewer, I want **vintage analysis within the one file**: group by
    origination period, and cumulative **delinquency/ever-bad** and **gross-loss**
    curves by months-on-book (loss keyed origination-date → charge-off-date), so I
    can see seasoning and underwriting drift.
16. As a reviewer, if my file carries a **prior-DPD-bucket** column and I map it, I
    want a **single-period roll/transition matrix** (dollar and count) computed
    within the one file, so I get migration signal without a second snapshot.
17. As a reviewer, I want an **A/B subgroup comparison** (e.g. indirect vs direct
    channel) reporting both weightings and flagging where dollar and count diverge
    materially, so I can spot where large balances hide behind small counts.
18. As a reviewer, I want the tool to **flag the highest-risk cells** and compute
    **coverage ($ and count) per segment**, and let me **mark the loans I select**,
    so my judgmental sample is deliberate and its penetration is documented.
19. As a reviewer, I want an auto-generated **OCC sampling doc** (population, areas
    of focus, sample size, selection rationale, results) that carries per-segment
    coverage and is **explicitly labeled non-extrapolable**, so the deliverable
    meets the OCC "Sampling Methodologies" documentation bar.
20. As a reviewer, I want the selected sample listed by **loan number** so I can
    pull the physical files for linesheet review.
21. As the maintainer, I want a self-contained `.xlsm` plus a pure-ASCII builder
    bundle, so I can email the tool through corporate DLP and rebuild it where it
    lives.
22. As the maintainer, I want the URCCP constants, the safe expression evaluator,
    and the PII byte-scan **imported from `credit-review-os`** (vendored into the
    ASCII bundle at transmission), so there is one source of truth for each and no
    drift.
23. As the maintainer, I want the tool to be **product-agnostic** — a file may be
    cards *or* auto *or* HELOC — with metrics **self-suppressing by applicability**
    (no WA-LTV on an unsecured card pool), so one tool serves every consumer
    product.

## 5. Requirements

1. [P0] **Canonical-field contract.** A declared set of canonical fields with,
   for each: id, label, dtype, expected units/scale options, and role
   (`universal-required` | `feature-gated` | `optional-slice`). **Universal
   (file will not load without):** `loan_id`, `current_balance`, and one
   `delinquency_signal` (a DPD day-count, a bucket label, or a status code).
   **Feature-gated (the specific analysis refuses, with a named-missing-field
   message, if absent):** URCCP needs `open_closed_end_flag` + `product_type`;
   vintage needs `orig_date`; loss curves need `chargeoff_flag` + `chargeoff_date`
   + `chargeoff_balance`; WA-FICO/DTI/LTV each need their field; roll matrix needs
   `prior_dpd_bucket`. **Everything else** (including the ad-hoc tail) is an
   optional auto-detected slice dimension. The file loads regardless; only the
   dependent metric refuses.
2. [P0] **Column-mapping layer (confirm-not-silent).** On load, fuzzy-match
   headers to canonical fields and **propose** a mapping; the reviewer must
   confirm/override **every** proposed row before compute runs — nothing is
   applied silently. Each mapped column carries a declared **unit/scale** where
   ambiguous (rate as fraction vs percent; DTI/LTV as fraction vs percent; DPD as
   day-count vs bucket-label vs status; date format). Unmapped canonical fields
   are surfaced, never guessed through. Mapping + units persist in a visible
   **`_map`** tab that travels with the workbook (edit + re-run pattern, per
   `TEMPLATE_CONTRACT.md` §13 ethos).
3. [P0] **Population-validation / cleaning gate.** Before compute, a validation
   pass flags: nulls in required-for-analysis fields, unparseable numerics,
   values out of declared-unit range, duplicate `loan_id`, and current-balance
   gaps where a $-weighted metric is requested. **Hard errors block** the affected
   analysis with a per-issue report (issue, column, row count, examples). Only
   **safe, explicitly-declared normalizations** run automatically (whitespace
   trim, declared unit rescale, canonical status/label mapping); each is recorded
   in a **`_cleaning`** summary tab (rule + rows affected). Nothing is silently
   imputed; the reviewer resolves the rest upstream and reloads.
4. [P0] **Weighted-average metric engine.** For each WA attribute
   (FICO orig/refreshed, DTI, LTV/CLTV, rate, age/MOB, term):
   `WA(x) = Σ(Bᵢ·xᵢ)/ΣBᵢ` with `Bᵢ` = current UPB (default weight, configurable),
   plus a **count-basis** parallel `Σxᵢ/N`. Balance-weighted metrics **refuse**
   (do not silently degrade) when current balance is absent — the cleaning gate
   surfaces it. LTV/CLTV self-suppresses for unsecured products.
5. [P0] **Delinquency & loss rates — dollar AND count, always labeled.** Canonical
   DPD buckets (Current, 1–29, 30–59, 60–89, 90–119, 120–149, 150–179, 180+) with
   cumulative roll-ups (30+/60+/90+). For each bucket: dollar ratio
   `Σbal_k/Σbal` and count ratio `n_k/N`. **Gross** charge-off rate (dollar +
   count) from `chargeoff_*`, labeled "gross-only, no recovery data." Every
   emitted rate carries an explicit basis label.
6. [P0] **URCCP classification — shared constants.** Import `URCCP_FLOORS` and the
   classification-clock resolver from `credit-review-os`
   (`credit_review/product_sheet.py`: closed_end {substandard 90, loss 120},
   open_end {substandard 90, loss 180}; overlay overrides may only **tighten**,
   never loosen). Residential-secured branch uses the ≥90-DPD LTV>60% qualifier
   with the 60% line as a knob; the 180-day fair-value writedown is out of scope
   as computation. Cite 65 FR 36903 / OCC Bulletin 2000-20 / FDIC FIL-40-2000.
7. [P0] **Configurable bands (never hard-coded).** Band edges for FICO, DTI, LTV
   live in `_config`. Ship three selectable schemes: **CFPB six-tier** FICO +
   **36/43** DTI (default), a **FR Y-14Q preset** (score ≤620/>620/NA + six DPD
   buckets 01–06), and **fully custom** edges. Bands drive group-by dimensions and
   are referenceable from cohort rules.
8. [P0] **Group-by stratification.** Group-by any mapped field or derived band;
   per-cell counts, balances, all WA metrics, and both-basis rates. A cardinality
   guard refuses/warns on a group-by field with excessive distinct values (e.g. a
   raw id-like tail field).
9. [P0] **Derived-cohort layer.** Cohorts declared on a `_cohorts` tab as named
   blocks of structured rule rows (`field │ op │ value`), **ANDed within a
   cohort with optional OR-groups**, ops from a whitelist (`<, <=, >, >=, ==, !=,
   in, not-in, between, is-null, not-null`). Rules compile to pandas masks via the
   **shared safe token evaluator** (no `eval`/`df.query`). Cohort rules may
   reference canonical fields **and** derived bands. **Missing-data semantics:** a
   rule testing a null/unparseable field for a loan is a **hard error surfaced by
   the cleaning gate** (per R3) — cohorts run on a clean population, so
   three-valued ambiguity does not arise silently at compute time. Support **5+
   cohorts simultaneously**.
10. [P0] **Cohort reconciliation (honest overlap).** Cohorts are reported
    **independently** (a loan may be in several). Always render a **pairwise
    overlap matrix** ($ and count) and an **"in no cohort" residual**; never sum
    cohorts as if they partition. Group-by remains the partition view.
11. [P0] **Side-by-side comparison + A/B.** Render 5+ slices (group-by cells
    and/or cohorts) side by side. Provide an **A/B subgroup comparison** reporting
    both weightings and flagging where dollar and count diverge beyond a knob.
12. [P0] **Vintage analysis (single file).** Group by origination period
    (month/quarter/year, configurable); cumulative **delinquency/ever-bad** curves
    (count and balance ÷ original cohort) and cumulative **gross-loss** curves
    (charged-off balance ÷ original balance) by MOB (loss keyed `orig_date` →
    `chargeoff_date`); a vintage × MOB triangle.
13. [P1] **Roll/transition matrix (conditional).** If `prior_dpd_bucket` is mapped,
    compute a single-period transition matrix and roll rates (dollar and count)
    from prior→current within the one file. Otherwise omit cleanly. No
    multi-snapshot machinery.
14. [P0] **Judgmental sampling support.** Rank/flag highest-risk cells; compute
    **coverage per segment ($ and count)**; provide a reviewer-marked **selection**
    (loan-number level). No auto-draw. Auto-generate the **OCC sampling doc**:
    population, areas of focus, sample size, selection rationale, results, with
    per-segment coverage, **explicitly labeled non-extrapolable**.
15. [P0] **Workbook / packaging.** Self-contained `.xlsm`: raw-input tab, `_map`,
    `_cleaning`, `_config` (SETTINGS/THRESHOLDS/BANDS/cohorts), output/dashboard
    tabs, `_code_py` (full runner, one line per cell, pure ASCII), extract-only
    macro (`ExtractFiles`), `_readme`. Pure-ASCII builder bundle per
    `TEMPLATE_CONTRACT.md` §11. **No** provider seam, **no** watchlist gate.
    control_center discovery works for free (keys on a `_code_py` tab) but is not
    required.
16. [P0] **Shared-core reuse.** URCCP constants + classifier, the safe token
    evaluator, and the PII byte-scan guard are imported from `credit-review-os`
    (source-time shared; **vendored into the ASCII bundle at transmission**), not
    reimplemented. Extract them into an importable module if they are not already
    cleanly importable.
17. [P0] **PII boundary (reverses the suite default — see §7).** The runtime
    populated workbook **may contain real borrower PII** (bank equipment/VPN,
    never leaves the machine; no PII gates, no masking, no vault). The PII
    byte-scan guard is **repointed** to assert zero **real** PII in the shipped
    tool / repo / demo fixtures (100% synthetic), **not** the runtime workbook.
18. [P1] **`_readme` + methodology block.** Setup, run steps, the URCCP citation
    spine, the sampling-design/non-extrapolable caveat, the dollar-vs-count and
    gross-only-charge-off caveats, and the PII boundary statement.

## 6. Implementation Decisions

- **Project shape.** New top-level `credit-population-bench/` mirroring the suite
  layout (its own `src/`, `tests/`, `docs/`, README, builder). Python package
  (e.g. `popbench`) with a small module split: `contract` (canonical fields +
  units), `mapping` (auto-propose + confirm + `_map`), `cleaning` (validation
  gate + `_cleaning`), `metrics` (WA + dollar/count rates + gross charge-off),
  `strata` (bands + group-by + cardinality guard), `cohorts` (rule model →
  shared evaluator → overlap/residual), `vintage`, `rolls`, `sampling` (rank/flag
  + coverage + OCC doc), `workbook` (openpyxl assembly, `keep_vba` for `.xlsm`),
  and a CLI/runner + macro + `make_bundle.py`.
- **Compute placement.** Math is **pandas behind the button**; the engine writes
  computed **values** into output tabs. Excel is load + output surface, not a
  formula engine — so the primary correctness proof is the pandas API vs
  hand-tallied values (see §7), not Excel recalc. Determinism: stable sort +
  fixed column order → byte-identical builds from the same input.
- **Shared core (verified to exist).** `credit_review/product_sheet.py` already
  holds `URCCP_FLOORS` (closed_end 90/120, open_end 90/180) and an
  override-can-only-tighten resolver; a safe token evaluator exists across
  `config.py`/`linesheet.py`/`product_sheet.py`; the PII byte-scan lives in
  `tests/test_pii_guard.py` + `ingest.py`/`mart.py`. Build task: factor these
  three into an importable shared surface (a small `credit_review` sub-package or
  a shared `satc_credit_core`) consumed by both projects and inlined by each
  project's ASCII bundler so the emailed workbook stays self-contained.
- **Canonical contract + units.** The contract is data (a declared table), not
  code branches, so adding a field/unit is config. Units are captured per mapped
  column at map-confirm time; the cleaning gate applies declared rescales and
  records them. Delinquency signal is normalized to canonical DPD buckets from
  whichever form the file carries (day-count → bucketize; bucket-label → map;
  status → map), with the mapping recorded in `_cleaning`.
- **Cohort rule model.** Structured rows, not free text:
  `{cohort_id, group_id, field, op, value}`. Within a `group_id` rows OR; groups
  AND. This is safe, validatable (unknown field/op → refuse at load), and
  round-trips to the `_cohorts` tab. Compilation goes through the shared evaluator
  so the grammar matches Mode B's.
- **Overlap/residual.** Membership is an N×K boolean matrix (loans × cohorts);
  overlap matrix = pairwise AND aggregates ($ and count); residual = rows with no
  cohort membership. Group-by outputs stay separate and reconcile to the
  population.
- **Bands.** Edges in `_config [BANDS]`; a scheme selector picks CFPB / Y-14Q /
  custom. `cut`-style bucketing with explicit, documented edge inclusivity.
- **Sampling doc.** Generated from the reviewer's selection column + coverage
  math into a formatted OCC-doc tab; the non-extrapolable label is fixed text, not
  optional.
- **PII.** No masking/vault/gates at runtime. Demo fixtures are synthetic; the
  PII byte-scan test runs against repo/shipped artifacts only.

## 7. Testing Decisions

- **Seam 1 (primary): the pandas engine's Python API vs hand-tallied expected
  values**, on a small deterministic synthetic population. This is the highest
  behavioral seam for the correctness-critical math — WA metrics (both bases),
  dollar/count delinquency + gross charge-off rates, URCCP totals per branch
  (closed/open/residential), band bucketing (CFPB + Y-14Q + custom), cohort masks,
  the **overlap matrix + residual**, vintage curves/triangle, the conditional
  roll matrix, and coverage math. Because the math is pandas-side, this seam (not
  Excel recalc) is where correctness is proven. Prior art: credit-review-os
  `tests/test_exceptions.py`, `test_master.py`, `test_lob_programs.py`.
- **Seam 2: mapping + cleaning contract round-trip.** Feed messy headers + dirty
  values; assert the auto-propose→confirm mapping, the declared-unit rescale
  (e.g. 7.25 → 0.0725), the **hard-error refusals** (null in required field,
  unparseable weight, duplicate loan_id, missing balance for a $-metric), and the
  `_cleaning` record of every applied normalization. Prior art:
  `test_ingest.py`.
- **Seam 3: workbook build/reload + determinism + no-native-charts.** Build the
  `.xlsm`, reload with `keep_vba`, assert tab taxonomy, byte-identical rebuild
  from the same input, and the extract-macro contract. Prior art:
  `test_portability.py`, `test_bundle.py`, the suite's recalc/OPC audits.
- **Seam 4: PII byte-scan (repointed).** Assert zero **real** PII patterns
  (person names, SSN) in the shipped tool / repo / demo fixtures — the runtime
  populated workbook is explicitly out of scope for this guard. Prior art:
  `test_pii_guard.py`.
- **What a good test proves:** the research doc's formulas hold as the engine
  computes them; dollar and count are both produced and labeled; URCCP uses the
  shared floors (a shared-constant change flows to both projects); dirty input is
  refused with a documented cleaning trail; cohorts never silently double-count;
  builds are deterministic; no synthetic-artifact PII leak.

> **Sensitive-data rules (binding, project-specific — a documented reversal of the
> suite default):** The **runtime populated workbook may hold real borrower PII**
> and is used only on bank equipment/VPN and never transmitted with data in it —
> so there are **no PII gates, no masking, no vault** at runtime; loan number is
> the file-pull key. The **shipped tool, repository, ASCII bundle, tests, and demo
> fixtures carry zero real PII** (100% synthetic) and the PII byte-scan enforces
> that. This reversal, and its exact boundary (repo/tool = clean; runtime workbook
> = may contain PII), is recorded in `BACKLOG.md` and stated in `_readme`.

## 8. Success Metrics

- One button turns a synthetic loan-level flat file into population + per-stratum
  metrics, cohort comparison with overlap/residual, vintage curves, and the OCC
  sampling doc; Seam-1 shows **0 discrepancies** vs hand-tallied expected values
  across every URCCP branch and both rate bases.
- A dirty synthetic file is **refused** with a per-issue report; the same file
  cleaned upstream then runs, with every applied normalization recorded in
  `_cleaning`.
- Adding a canonical field, a band scheme, or a cohort is **config-only** (no
  engine change).
- A URCCP floor change made once in the shared core changes both this bench and
  `credit-review-os` (proven by the shared import, not a copy).
- Builds are byte-identical; the ASCII bundle rebuilds the workbook in an empty
  folder with only pandas + openpyxl; Seam-4 scan is clean on all shipped
  artifacts.

## 9. Milestones / Rollout

- **M1 (tracer):** contract + mapping (auto-propose/confirm + units) + cleaning
  gate + core metric engine (WA both bases, dollar/count delinquency, URCCP via
  shared floors) + group-by + workbook build + Seams 1–4 on a synthetic file.
- **M2:** derived-cohort layer (rules → shared evaluator → overlap/residual),
  side-by-side + A/B comparison, band schemes (CFPB/Y-14Q/custom), gross
  charge-off rate.
- **M3:** vintage curves/triangle, conditional roll matrix, judgmental sampling
  (rank/flag + coverage + OCC doc), ASCII bundle + `_readme`/methodology, shared-
  core extraction finalized.

## 10. Risks & Open Questions

- **Risk — shared-core extraction touches `credit-review-os`.** Factoring
  `URCCP_FLOORS` + evaluator + PII guard into an importable surface must not
  regress Mode A/B's suites. Mitigation: extract behind the existing symbols,
  keep those imports working, run credit-review-os's full suite as a gate.
- **Risk — cohort/group-by cardinality blowup** on a raw tail field. Mitigation:
  a cardinality guard that refuses/warns above a configurable distinct-value cap.
- **Risk — units mis-declaration** still lets a wrong scale through if the reviewer
  confirms wrong. Mitigation: range sanity checks in the cleaning gate flag
  out-of-band values (a DTI of 43 when fraction was declared) for confirmation.
- **Risk — dollar/count divergence misread.** Mitigation: every rate is
  basis-labeled and the A/B view flags material divergence.
- **Known inherited debt (needs your desk):** URCCP pin-cite verification against
  the live regulator PDFs before the first filed workpaper — same caveat as
  credit-review-os (regulator sites block automated fetch). Tracked in
  `BACKLOG.md` §5.
- **Open question (needs your decision):** none outstanding — all design branches
  were resolved in grilling. Product-agnostic behavior and "no bench-level de-id
  mart" were stated as assumptions and confirmed.

## 11. Done Criteria

- [ ] Requirements R1–R18 met; user stories 1–23 satisfied.
- [ ] Seam 1: engine vs hand-tallied values, 0 discrepancies across URCCP branches
      + both rate bases + cohort overlap/residual + vintage + coverage.
- [ ] Seam 2: mapping/units round-trip + cleaning-gate refusals + `_cleaning`
      record verified.
- [ ] Seam 3: `.xlsm` build/reload, byte-identical determinism, extract-macro,
      no-native-charts.
- [ ] Seam 4: PII byte-scan clean on all shipped/repo/demo artifacts.
- [ ] `credit-review-os` full suite still green after shared-core extraction.
- [ ] Verified by running the real one-button flow on a synthetic file (not just
      tests); demo workbook built and eyeballed.
- [ ] ASCII bundle rebuilds the workbook in an empty folder (pandas + openpyxl
      only).
- [ ] README + `_readme` (URCCP citations, dollar/count + gross-only caveats,
      non-extrapolable label, **PII boundary**) written.
- [ ] `BACKLOG.md` updated (new project line, PII-boundary decision, `[LOG]`
      deferrals).
