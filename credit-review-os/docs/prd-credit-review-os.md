# PRD: Credit Review OS (`credit-review-os/`)

**Status:** Draft · **Owner:** SATC owner · **Last updated:** 2026-07-04

> A portable, rules/framework-driven **Credit Review Operating System**: it
> configures product/LOB-specific loan-review programs and produces
> professional-grade, bank-committee-ready review workpapers (linesheet → master
> → de-identified data mart → findings), tracks exceptions to resolution, and
> proves — with a built-in regulatory crosswalk — that the methodology satisfies
> the interagency standard. Domain facts are grounded and cited in
> [`docs/research/credit-review-methodology.md`](../../docs/research/credit-review-methodology.md).

---

## 1. Problem

The owner performs **loan/credit review as a consulting service** (the "C" in
SATC — Sethuraman Accounting, Tax & **Consulting**) for community/regional banks:
independently examining a sample of loan files against the bank's credit policy
and the interagency standard, validating risk ratings, cataloguing exceptions,
and reporting portfolio-level findings to the bank's credit committee and board.

Today that work is done by hand in ad-hoc Excel — every engagement rebuilds the
linesheet from scratch, the methodology's regulatory defensibility lives only in
the reviewer's head, exception tracking is manual, and nothing carries forward
across engagements or across lines of business. The disciplined methodology (the
owner's strongest domain edge, from a bank credit-review background) is not yet
packaged into an enforceable, presentable, repeatable system. It needs to be —
so a review is faster to produce, consistent across banks and LOBs, and
**self-proving to an examiner or board** that it was conducted to standard.

## 2. Solution

A new top-level project, `credit-review-os/`, that generates a **self-contained,
emailable `.xlsm` workbook per engagement** in the KeyBank house style. A
config-driven Python builder reads a portable **per-LOB program** plus a thin
**engagement/client overlay** and emits the full workpaper set: a cover, one
**linesheet per loan**, a **master/summary** roll-up, a **de-identified data
mart**, a **findings/exception report**, a **`_methodology` regulatory
crosswalk**, and **engagement coverage/independence/reporting evidence**. The
reviewer keys assessments directly into the workbook; **exception flags, risk-
rating validation, and findings roll-ups compute via live Excel formulas** (the
workbook is the source of truth). A Python **re-ingest** pass reads the filled
workbook back to produce the de-identified mart and portfolio findings for
cross-engagement analysis.

It reuses the repo's proven machinery — the config-driven line-sheet pattern
(`satc_system`'s `LineSheetBuilder` + YAML), the `keybank_style.py` design
system, the de-identified `Data Mart` sheet pattern, and the pytest + formula-
recalc + no-PII-leak verification bar — without being bound by the monitoring-
specific `TEMPLATE_CONTRACT` clauses (provider seam, runner-fetch, watchlist
gate) that don't fit reviewer-entry work.

## 3. Goals & Non-Goals

**Goals**
- Produce a bank-committee-grade C&I review workbook from config + synthetic
  loan data, end-to-end, with formula-driven exceptions and rating validation.
- Make the review program **portable**: adding a LOB or a client bank is editing
  config, not writing code.
- **Prove the method**: every program element links to the interagency
  requirement it satisfies, and each engagement captures the guidance's own asks
  (coverage/scope, independence, findings-to-board reporting).
- Hold borrower PII to the repo's bar: encrypted at rest, TINs masked to last-4,
  de-identified cross-engagement mart, 100% synthetic repo fixtures.
- Keep the deterministic core authoritative; leave a clear roadmap for
  parsing/OCR and an optional **local** LLM assist that never enters the data path.

**Non-Goals / Out of scope** (prevents build balloon — do not build these in v1)
- **Not a loan origination, servicing, or credit-decisioning system.** It reviews
  existing credits; it does not originate, underwrite for approval, or price.
- **Not the bank's system of record.** The bank's core/loan system and its ACL/CECL
  allowance engine stay authoritative — analogous to "Drake stays SoR" for tax.
  Classifications are *produced*; **feeding them into an allowance/CECL calc is a
  non-goal** (roadmap: export classifications for the bank's ACL system).
- **Not portfolio monitoring.** The credit-risk `.xlsm` template series already does
  public-data surveillance; this is individual loan-file review, not data-pull.
- **No document ingestion / OCR / extraction in v1.** Loan-file formats are too
  heterogeneous to parse reliably; the reviewer keys assessments. (Roadmap item.)
- **No LLM anywhere in v1**, and never in the deterministic data path at any phase.
- **Not multi-user product software.** Single-operator (the owner); no roles,
  accounts, server, or bank-hosted deployment.
- **Mode B (product-conformance) not implemented in v1** — only *designed into the
  schema*. First built when the roadmap reaches consumer/residential.
- **No `.xlsm`→ASCII-bundle transmission machinery in v1** (contract §11) — the
  workbook is self-contained and emailable; the build-on-target bundle is a
  documented fast-follow.

## 4. User Stories

1. As a reviewer, I want to generate a complete engagement workbook from a program
   config + a client overlay + a loan list, so that I never rebuild a linesheet
   from scratch.
2. As a reviewer, I want one linesheet per loan pre-structured with the C&I
   program's fields, tests, and evidence checklist, so that I only key figures and
   judgments, not layout.
3. As a reviewer, I want to enter both the **originator's assigned rating** and my
   **independent rating**, and have a disagreement automatically raised as a
   rating exception/finding, so that independent validation is enforced, not
   optional. (Interagency 2020 §independence.)
4. As a reviewer, I want exception flags (documentation / policy / compliance) to
   compute from the values I enter against the client's policy thresholds, so that
   the workbook catches exceptions rather than relying on my memory.
5. As a reviewer, I want each exception to carry class, policy-subtype
   (approved-with-mitigant vs. unapproved), severity, status (open/cleared/waived),
   owner, due date, and cleared date, so that I track exceptions to resolution.
6. As a reviewer, I want a master/summary sheet that rolls up every loan's
   exposure, ratings (originator vs. reviewer), classification bucket, and open
   exception count, so that the credit committee sees the portfolio at a glance.
7. As a reviewer, I want criticized/classified totals (criticized = SM+SS+D+L;
   classified = SS+D+L) computed automatically from the loan ratings, so that the
   asset-quality summary is correct and consistent.
8. As a reviewer, I want a `_methodology` crosswalk tab that maps each program
   element (rating validation, exception tracking, evidence tests, sampling) to the
   specific interagency requirement it satisfies **with citation**, so that the
   deliverable is self-proving to an examiner/board.
9. As a reviewer, I want the engagement to capture coverage/scope (% of portfolio
   and $ reviewed, sampling basis), reviewer independence, and the findings-to-board
   reporting section, so that the review demonstrates it was conducted to standard.
10. As a reviewer, I want borrower names and loan numbers to appear in the
    deliverable (the bank's own data, returned to them) but full SSN/EIN masked to
    last-4 everywhere, so that the workbook is usable yet minimizes TIN exposure.
11. As the owner, I want the engagement workbook encrypted at rest, so that a
    third party's confidential borrower data is protected on my machine.
12. As a reviewer, I want a re-ingest pass that reads a filled workbook and emits a
    **de-identified** cross-engagement data mart + a portfolio findings dataset, so
    that I can analyze patterns across banks without moving PII.
13. As the owner, I want a new client bank to be a thin overlay file (their rating
    scale mapped to the 5 buckets, their policy thresholds, their scope), so that
    the same program serves any bank by editing config.
14. As the owner, I want the program-config schema to already carry a `review_mode`
    (loan-level vs. product-conformance) selector, so that consumer/retail (Mode B)
    slots in later without reworking the schema.
15. As the owner, I want a synthetic demo engagement (fake bank, fake C&I loans) I
    can build and inspect, so that I can validate the tool without touching real
    borrower data.
16. As a maintainer, I want the whole thing verified headlessly (config parse,
    determinism, exception/rating logic vs. hardcoded expected values, formula
    recalc, no-PII-leak), so that a change can't silently break correctness.

## 5. Requirements

1. [P0] A **program config** (YAML) per LOB declaring: `meta` (lob, review_mode,
   title), `rating_framework` (the 5 regulatory buckets + derived `is_criticized`
   / `is_classified`), `sections[].rows[]` (linesheet fields with `kind`), the
   `evidence[]` checklist, the `exception_rules[]`, and the `crosswalk[]`
   (element → interagency requirement + citation). v1 ships `c_and_i`.
2. [P0] An **engagement/client overlay** (YAML) declaring: client identity,
   `rating_scale_map` (each internal grade → one of Pass/SM/SS/D/Loss),
   `thresholds` (DSCR floor, LTV/advance-rate ceilings, leverage ceiling, doc
   staleness windows in days), `scope` (portfolio $ and count, sampling basis),
   `reviewer` (name, independence attestation), and the `loans[]` list (or a
   pointer to a synthetic loan fixture).
3. [P0] A **builder** `build_engagement_workbook(program, engagement, loans) ->
   openpyxl.Workbook` that assembles: `Cover`, one `LS_<loan_id>` linesheet per
   loan, `Master`, `Data Mart` (de-identified), `Findings`, `_methodology`, and
   `_config`, all in `keybank_style`.
4. [P0] Linesheet fields, exceptions, rating rollups, and criticized/classified
   totals are **live Excel formulas** resolved at build time (extend the existing
   token grammar), never hardcoded results.
5. [P0] **Rating validation**: originator rating and reviewer rating are distinct
   cells; a formula raises a `rating` finding when they map to different buckets.
6. [P0] **Exception model** per §4 of the research: `class`
   (documentation/policy/compliance), `policy_subtype`
   (approved_with_mitigant/unapproved), `severity` (configurable tier),
   `status` (open/cleared/waived), `owner`, `due_date`, `cleared_date`; the
   `Findings` sheet aggregates by class/severity/status and by loan.
7. [P0] **Evidence/currency tests**: each evidence item `{type, as_of_date,
   quality_tier, required_frequency, policy_staleness_days}` produces a
   documentation exception when stale vs. the overlay's `policy_staleness_days`.
8. [P0] **`_methodology` crosswalk tab**: one row per program element → interagency
   requirement satisfied → citation (from the research doc). Plus engagement
   coverage/independence/reporting evidence captured from the overlay.
9. [P0] **PII handling** (see Testing Decisions): borrower legal name + loan number
   appear in the workbook; **full TIN masked to last-4 everywhere**; the `Data
   Mart` and re-ingest output are **de-identified** (borrower → engagement-scoped
   id); **all repo fixtures are synthetic**; a build-time test fails on real-PII
   leakage patterns.
10. [P0] Engagement workbooks are **encrypted at rest**, mirroring `satc_system`'s
    AES-256-GCM + OS-key-seal approach (reuse the pattern; the *repo* stores only
    synthetic demo artifacts, so this gates real-engagement use, not the demo).
11. [P0] A **re-ingest** function `ingest_workbook(path) -> (DeIdentifiedMart,
    PortfolioFindings)` that reads a filled workbook and emits the de-identified
    mart + portfolio findings.
12. [P0] **Schema carries `review_mode`** with `loan_level` (v1) and
    `product_conformance` (designed, not built) values.
13. [P1] A **synthetic demo engagement** (fake bank + N fake C&I loans) that builds
    the full workbook, used by tests and for owner inspection.
14. [P1] A **README** documenting the two-config-layer model, the LOB roadmap, the
    determinism principle, and the PII rules.
15. [P2] The pre-filing pin-cite verification note surfaced in the workbook's
    `_methodology`/`_readme` (research citations are page-unconfirmed; see Risks).

## 6. Implementation Decisions

**Project layout** (own top-level folder, per repo convention; mirrors how each
credit-risk template owns its builder rather than importing `satc_system`):

```
credit-review-os/
  README.md
  pyproject.toml            # deps: openpyxl, pyyaml, cryptography, formulas (test), pytest
  src/credit_review/
    programs/               # portable per-LOB program YAML (v1: c_and_i.yaml)
    engagements/            # example synthetic overlay(s) + loan fixtures (SYNTHETIC only)
    config.py               # load + validate program + overlay (schema)
    linesheet.py            # LinesheetBuilder (adapts satc_system LineSheetBuilder pattern)
    workbook.py             # build_engagement_workbook(program, engagement, loans)
    master.py, findings.py, mart.py, methodology.py, cover.py   # per-sheet builders
    ingest.py               # ingest_workbook(path) -> (DeIdentifiedMart, PortfolioFindings)
    crypto.py               # encryption-at-rest (mirror satc_system persistence/crypto)
    keybank_style.py        # copied house-style module (per repo's per-project copy rule)
    cli.py                  # `credit-review build <engagement>` / `ingest <workbook>`
  tests/
  docs/prd-credit-review-os.md   # this file
```

**Config schema — program (portable, client-agnostic).** Reuse the tax line-sheet
row-`kind` vocabulary (`input`/`input_num`/`input_text`/`computed`/`total`/
`crosscheck`/`subhead`/`note`/`spacer`) and add credit-review kinds:
`rating_input` (validated against the framework), `exception` (emits a findings
row), `evidence` (currency-tested). Example shape:

```yaml
meta: { lob: c_and_i, review_mode: loan_level, title: "C&I Loan Review Linesheet" }
rating_framework:
  buckets: [Pass, "Special Mention", Substandard, Doubtful, Loss]
  criticized: ["Special Mention", Substandard, Doubtful, Loss]   # is_criticized
  classified: [Substandard, Doubtful, Loss]                       # is_classified
sections:
  - title: "Identification & exposure"
    rows:
      - {id: borrower_name, kind: input_text, label: "Borrower (name; TIN last-4 only)", pii: name}
      - {id: total_commitment, kind: input, label: "Total commitment"}
      - {id: outstanding, kind: input, label: "Outstanding"}
      - {id: rating_originator, kind: rating_input, label: "Originator risk rating"}
      - {id: rating_reviewer, kind: rating_input, label: "Reviewer risk rating (independent)"}
      - {id: rating_exception, kind: exception, class: policy, label: "Rating disagreement",
         when: "MAP({rating_reviewer})<>MAP({rating_originator})", severity: high}
  - title: "Cash flow & coverage"
    rows:
      - {id: dscr, kind: computed, label: "DSCR", formula: "{cash_flow}/{debt_service}"}
      - {id: dscr_exception, kind: exception, class: policy, label: "DSCR below policy floor",
         when: "{dscr}<[POL dscr_floor]", severity: high, subtype: unapproved}
evidence:
  - {type: financial_statements, required_frequency: annual, quality_tiers: [audited, reviewed, compiled, tax_return, company_prepared]}
  - {type: appraisal, condition_driven: true}       # re-order when no longer valid (2010 Guidelines)
  - {type: borrowing_base_certificate, required_frequency: monthly}
  - {type: covenant_compliance_certificate, required_frequency: quarterly}
crosswalk:
  - {element: independent_rating_validation, requirement: "Independent assessment/adjustment of risk ratings",
     source: "Interagency Guidance on Credit Risk Review Systems, 85 FR 33278 (2020)"}
  - {element: exception_tracking, requirement: "Systematically identify and resolve documentation exceptions; track aggregate levels",
     source: "OCC Loan Portfolio Management, Comptroller's Handbook"}
```

New formula token: **`[POL key]`** resolves to a threshold cell from the
engagement overlay written into `_config` (analogous to the tax builder's
`[XW ...]` / `[CF ...]` tokens, which resolve to `Sheet!Cell` at build time so the
workbook ships live formulas). A `MAP(...)` helper resolves an internal grade to
its regulatory bucket via the overlay's `rating_scale_map` (implemented as a
lookup against a mapping block on `_config`, so the disagreement test is a live
formula, not a precomputed boolean).

**Config schema — engagement overlay (thin, per client bank).**

```yaml
client: { name: "Demo Community Bank", engagement_id: "DEMO-2026-01" }
rating_scale_map:            # every internal grade -> exactly one regulatory bucket
  "1": Pass
  "6": "Special Mention"
  "7": Substandard
thresholds: { dscr_floor: 1.20, ltv_ceiling: 0.80, leverage_ceiling: 4.0, stmt_staleness_days: 365, bbc_staleness_days: 45 }
scope: { portfolio_dollars: 42000000, portfolio_count: 210, sample_basis: "risk-based; all >$1MM + 10% random" }
reviewer: { name: "SATC", independent: true, independence_note: "No lending authority; reports to board audit committee" }
loans: "engagements/demo_c_and_i_loans.yaml"    # SYNTHETIC fixture
```

**Sheets produced.** `Cover` (engagement identity, scope, independence
attestation), `LS_<loan_id>` (linesheet per loan), `Master` (one row per loan:
exposure, originator vs. reviewer rating, bucket, criticized/classified flags,
open-exception count — formulas referencing each linesheet), `Data Mart`
(de-identified flat grid, reusing the `mart_sheets` pattern), `Findings`
(exceptions aggregated by class/severity/status + a criticized/classified asset-
quality summary), `_methodology` (crosswalk + coverage/independence/reporting
evidence), `_config` (thresholds, rating-scale map, settings — the knob panel and
formula-resolution target), `_readme` (setup, the pin-cite caveat, PII notes).

**Determinism principle (architecture-level).** The builder and re-ingest are pure
and deterministic (no network, no clock-dependent values in outputs, no LLM).
Roadmap phases (doc parsing/OCR; optional **local** LLM extraction assist) MUST
keep the deterministic core authoritative — any assisted value is written to a
proposal lane a human confirms into the workbook; the LLM never writes a
review value or a rating directly. Recorded in the README + BACKLOG log.

**Reuse vs. copy.** Adapt (don't import) `satc_system`'s `LineSheetBuilder` token
grammar and `mart_sheets` flat-grid renderer; **copy** `keybank_style.py` per the
repo's deliberate per-project-copy rule so the workbook stays self-contained.

## 7. Testing Decisions

- **Seam 1 (primary): the in-memory builder** — `build_engagement_workbook(program,
  engagement, loans) -> openpyxl.Workbook`. Tests assert against the returned
  workbook object without disk I/O: config parses; every loan yields a linesheet;
  Master/Findings/methodology/mart sheets exist; formulas are wired (not hardcoded);
  the rating-disagreement and DSCR/LTV/leverage/staleness exception formulas
  evaluate correctly via the **`formulas` recalc engine against hardcoded expected
  values** (same recalc-spot-check discipline the credit-risk templates use); build
  is **deterministic/idempotent** (same inputs → byte-identical workbook).
- **Seam 2: the re-ingest round-trip** — build demo → programmatically fill
  synthetic assessment values → `ingest_workbook` → assert the mart is
  de-identified (no name/full-TIN) and portfolio findings aggregate correctly.
- **Seam 3: no-PII-leak guard** — save the demo workbook + mart export to bytes and
  assert no full-SSN/EIN pattern appears (only last-4), borrower names appear ONLY
  in the engagement workbook (never the mart/findings export), and all committed
  fixtures are synthetic. Mirrors the existing suite's leak tests.
- **What a good test proves:** the workbook is structurally complete, the credit
  logic is correct *as evaluated by Excel* (not just as Python), the build is
  reproducible, and PII never escapes its boundary.

**Prior art:** `satc_system/tests` (line-sheet/mart/workbook build tests) and each
credit-risk template's `test_*` suite (config parse, demo determinism, recalc
parity, clear-actually-blanks). Follow both.

> **PII / sensitive-data rules (binding).** Borrower **name + loan number** may
> appear in the engagement workbook only (the bank's own data, returned to the
> bank), which is **encrypted at rest**. **Full SSN/EIN are masked to last-4
> everywhere** — linesheets identify by name + loan/obligor number, never full
> TIN. The **`Data Mart` and any re-ingest/cross-engagement output are
> de-identified** (borrower → engagement-scoped id). **Every repo fixture is 100%
> synthetic**; a build-time test fails the build if a real-PII pattern (full TIN,
> or a name outside the synthetic set) leaks into any artifact. No LLM/cloud call
> ever touches borrower data in v1.

## 8. Success Metrics

- One command builds a complete C&I engagement workbook for the synthetic demo
  bank with **zero manual layout**.
- 100% of program elements in `c_and_i` appear in the `_methodology` crosswalk with
  a citation; engagement coverage/independence/reporting evidence is populated.
- Exception + rating-validation logic matches hardcoded expected values under the
  `formulas` recalc engine (0 discrepancies).
- No-PII-leak test passes; 0 full TINs and 0 real names in any artifact.
- Build is byte-identical across two runs (determinism).
- Adding the demo second-bank overlay requires **0 code changes**.

## 9. Milestones / Rollout

- **M1 (v1 MVP):** `c_and_i` program + synthetic demo overlay + `build_engagement_
  workbook` producing all sheets, formula-driven exceptions & rating validation,
  the de-identified mart + re-ingest pass, `_methodology` crosswalk + coverage
  evidence, encryption-at-rest, the full test bar, and the README. (This PRD.)
- **M2 (fast-follow):** ASCII-bundle build-on-target transmission (contract §11) so
  the workbook crosses a bank DLP boundary; second demo bank to prove portability.
- **M3+ (LOB roadmap, cash-flow-out order):** income-producing CRE → owner-occ CRE
  → construction/ADC → agricultural → **consumer + residential (first Mode B,
  product-conformance)** → multifamily / leases / specialty. Each = new config +
  crosswalk, reusing the engine.
- **Roadmap (separate design + grill each):** document parsing/OCR pre-fill;
  optional **local**, human-confirmed LLM extraction assist (never in the data
  path); export classifications for the bank's ACL/CECL system.

## 10. Risks & Open Questions

- **Risk — formula complexity in-workbook.** Global cash flow / rating-map lookups
  as live Excel formulas can get gnarly. Mitigation: keep the `MAP()`/`[POL]`
  resolution to `_config` lookups; recalc-verify every logic cell against hardcoded
  expected values; if a rule is infeasible as a formula, compute it in the
  re-ingest pass (Seam 2) rather than hardcoding a result into the workbook.
- **Risk — citation pin-cites unconfirmed.** The research doc's regulator quotes
  were retrieved via search (direct PDFs 403'd); exact page pin-cites are
  unconfirmed. Mitigation: the `_methodology`/`_readme` carries the "confirm page
  cites against live PDFs before a filed workpaper" note; substance is
  high-confidence (single interagency standard).
- **Open question (needs your decision):** which agency's classification wording is
  canonical for your clients (OCC / FDIC / FRB)? They are substantively identical —
  **recommend citing FDIC RMS §3.2** (fullest verbatim) and noting OCC/FRB parity.
  Not a build blocker; the builder cites whatever the program's `crosswalk` names.
- **Open question (needs your decision):** confirm the demo bank's illustrative
  policy thresholds (DSCR floor, LTV/leverage ceilings, staleness windows) for the
  synthetic overlay — **recommend** DSCR ≥1.20, LTV ≤80%, leverage ≤4.0x, annual
  statements / 45-day BBC as reasonable placeholders (they are config, easily
  changed).

## 11. Done Criteria

- [ ] `c_and_i` program + synthetic engagement overlay + loan fixture (all synthetic)
- [ ] `build_engagement_workbook` emits Cover, per-loan linesheets, Master, Data
      Mart, Findings, `_methodology`, `_config`, `_readme` in KeyBank house style
- [ ] Rating validation + doc/policy/compliance exceptions + evidence-staleness are
      live formulas; criticized/classified totals compute correctly
- [ ] `_methodology` crosswalk covers every program element with a citation; coverage/
      independence/reporting evidence populated from the overlay
- [ ] Re-ingest emits a de-identified mart + portfolio findings
- [ ] Encryption-at-rest implemented (real engagements) mirroring `satc_system`
- [ ] Tests pass at all three seams (build/recalc/determinism, re-ingest round-trip,
      no-PII-leak)
- [ ] Verified by building + opening the demo workbook and eyeballing it, not just tests
- [ ] README documents the two-layer config, LOB roadmap, determinism principle, PII rules
- [ ] BACKLOG/log entry records the roadmap (OCR/parse, local-LLM assist, ACL export, LOBs)
