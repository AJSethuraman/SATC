# BACKLOG — Credit-Risk Template Suite

The shared to-do log. Statuses: `[ ]` open · `[~]` in progress · `[x]` done.
Anyone (human or agent) picking up work starts here; finished items move to
the bottom log with a date. Companion docs: `PROJECTS.md` (what exists),
`TEMPLATE_CONTRACT.md` (how everything must behave).

---

## 1 · Validation debts (needs YOUR desk — the build box can't do these)

- [ ] **Open each .xlsm in real Excel** and click ExtractFiles once
      (FRED, bureau, macro, FDIC). The embedded VBA container is
      olevba-verified but has never met desktop Excel. Fallback if any
      complain: `_code_vba` paste-in.
- [ ] **Macro template: first live FRED run** — needs your FRED_API_KEY
      (`$env:FRED_API_KEY`), then `runner.py -w <book>.xlsm` per RUN.txt.
- [ ] **FDIC template: first live run** — keyless, zero setup. Also run
      `runner.py --lookup` to verify/replace the 9 illustrative seed CERTs
      with your real peer list.
- [ ] **Bureau template: bind the live HHDC schema** — `_parse_table` is
      deliberately unbound (the NY Fed table layout was unverifiable);
      demo works fully; live needs the real column mapping (Open Q#5).

## 2 · v1.1 improvements (per shipped template)

- [ ] **FDIC:** blank stale banks' latest quarter + show STALE in the
      Watchlist status column (removes the documented median divergence);
      optional UBPR asset-band medians. (SVB metrics SHIPPED in pack v1.1.)
- [ ] **Macro:** county-level drill-down via FRED's LAUS county mirrors
      (ids must be enumerated via release 116, never constructed);
      consider `EQFXSUBPRIME*` county subprime share pending its FRED
      license note (Open Q).
- [ ] **FRED (template #1) contract-alignment pass:** it predates the
      contract — audit for the L7 clear-blocks bug class, grandfathered
      `--backend` flag, `Watchlist_Geo` tab name; align or explicitly
      re-grandfather each item.
- [ ] **Bureau:** licensed Class C adapter swap when/if a Prama-class
      feed is ever contracted (the gate opens only then).

## 3 · Next templates (researched, ranked; process per contract)

- [ ] **#7 BLS LAUS county unemployment monitor** — monthly county-FIPS
      early warning; free API key, 500 q/day. (Partially covered by the
      macro template's state lane; standalone only if county cadence
      proves valuable at your desk.)
- [ ] **Later bench:** HMDA loan-level (annual research pull), SBA 7(a)/504
      FOIA (commercial charge-offs by county+NAICS), NCUA credit-union
      sibling of FDIC, FHFA NMDB aggregates.

## 4 · Suite infrastructure ideas (unscheduled — promote when wanted)

- [x] **Provenance/tie-out (contract §12, user requirement) — SHIPPED
      for FDIC in pack v1.1** (_provenance tab + --tieout with facsimile/
      BankFind URLs); EDGAR gets accession provenance in its build;
      retrofit FRED/bureau/macro/CFPB opportunistically:** every value
      traceable to the official document — _provenance tab + `--tieout`
      mode. **Field→Call-Report mapping DONE** (fdic-peer-monitor/
      PROVENANCE_MAP_FDIC.md — MDRM codes verified against FFIEC's own
      bulk-data captions; direct facsimile URL keyed by CERT; RC-N
      column structure confirmed). Implementation lands with the
      competitor pack; EDGAR gets accession-based provenance; retrofit
      others opportunistically.
- [ ] Suite-level conformance check: one script asserting every template's
      shared modules are byte-identical, embedded code is ASCII, tabs match
      the contract, and all suites are green (CI-able).
- [x] Control Center v2 SHIPPED: status board (purpose + last run + alert
      counts read from each workbook, no opening needed), Refresh ALL
      (demo), Tie-out button, --doctor env/host check with allowlist
      guidance.
- [x] Single suite bundle SHIPPED: build_suite.py (one ASCII file = all
      template bundles + control_center; menu or --all; regenerate with
      make_suite_bundle.py — new templates join automatically).
- [x] SUITE_GUIDE.md SHIPPED: the two-page operator manual (setup, daily
      driving, which-workbook-answers-what, verification, troubleshooting).
- [ ] Regenerate the visual suite-overview page from live demo digests
      (currently hand-assembled).

- [ ] Idea (deferred): shared peer-list sync across FDIC/EDGAR workbooks —
      same banks, different keys (CERT vs CIK); needs a name-based
      crosswalk; revisit after both templates are in real use.

## 5 · Credit Review OS (`credit-review-os/` — consulting workpapers, not monitoring)

v1 (C&I loan-level engine) shipped 2026-07-05 — see Done log. Roadmap, in
order; each LOB = a new program YAML + crosswalk on the same engine:

- [x] **Second demo bank overlay** — SHIPPED 2026-07-05: `Sample State Bank`
      overlay (1-10 scale, tighter thresholds) builds on the unchanged C&I
      program; recalc tests prove threshold-flips (DSCR 1.22 vs 1.25 floor,
      leverage 3.95x vs 3.5x). 0 code changes (PRD success metric met).
- [~] **LOB build-out (cash-flow-out order):** SHIPPED 2026-07-05:
      **income-producing CRE** (NOI DSCR, occupancy, appraised-value LTV,
      rent-roll evidence), **owner-occ CRE** (occupant-business global cash
      flow per the RC-C owner-occupied definition), **construction/ADC**
      (loan-to-cost, interest-reserve depletion, as-completed LTV, draw
      inspections), **agricultural** (farm operating DSCR, carryover debt,
      farmland/chattel LTV, crop insurance) — all config + crosswalk, zero
      engine changes. Remaining (each GATED on its own grill/design pass):
      consumer+residential (**first Mode B / product_conformance build** —
      schema already carries the mode) → multifamily / leases / specialty.
      **Mode B SHIPPED 2026-07-05** (grilled with the owner same day; PRD:
      `credit-review-os/docs/prd-mode-b-product-conformance.md`; issues
      #73/#74) — per-product PS_ tabs (conformance sample grid + URCCP pool
      classification by live formula, cited to 65 FR 36903 / OCC 2000-20 /
      FDIC FIL-40-2000; overlay may tighten the clock, never loosen — loader
      enforced), rate-vs-tolerance findings (compliance per-occurrence),
      stratified random + judgmental segments with per-stratum analytics,
      computed buy-box FRINGE flag + fringe-vs-core norms block, shared test
      library with per-product knob overrides, loan-number-only identity
      (zero person names — stricter than Mode A), product-level de-identified
      mart + re-ingest. Three demo products span every URCCP branch
      (indirect auto / credit card / HELOC). Remaining LOBs (multifamily /
      leases / specialty) are config work on either mode as needed.
- [ ] **Mixed-mode workbooks** (one engagement covering commercial loan-level
      + retail conformance in one deliverable) — decided against for Mode B
      v1 (one mode per workbook); revisit if real engagements demand it.
- [ ] **Statistical sample-size calculator** (attribute sampling: confidence /
      tolerable rate → n) — decided against for Mode B v1; the documented
      stratified-random + judgmental basis is the method. Revisit on demand.
- [x] **ASCII-bundle build-on-target** — SHIPPED 2026-07-05: `credit-review
      bundle <engagement>` emits a single pure-ASCII script (contract §11
      pattern, gzip+base64) that rebuilds the workbook byte-identical in an
      empty folder on a machine with only openpyxl+PyYAML; tested for
      ASCII purity, byte-parity, and no crypto/formulas deps on target.
- [ ] **Doc parsing / OCR pre-fill** — proposal lane only; deterministic core
      stays authoritative (needs its own grill/design pass).
- [ ] **Optional local LLM extraction assist** — human-confirmed proposals
      only, never in the data path, never writes a rating (own design pass).
- [ ] **ACL/CECL export** — emit classifications for the bank's allowance
      system (OCC *Allowances for Credit Losses* is the source when scoped).
- [ ] **Pin-cite confirmation sprint (needs YOUR desk)** — verify crosswalk
      page cites against the live regulator PDFs before the first filed
      workpaper. Re-attempted 2026-07-05 from the build box: occ.gov /
      fdic.gov / federalregister.gov / cdfifund.gov all still 403 to
      automated egress — this requires a human browser.

## 6 · Consumer Credit Population Bench (`credit-population-bench/` — loan-level analysis, sibling to Credit Review OS)

PRD 2026-07-05 (`docs/prd-credit-population-bench.md`, grilled via `/occam`);
**v1 BUILT 2026-07-05** (issues #79–#87, PR #78). A standalone `.xlsm` + pandas
engine: a bank reviewer loads a **loan-level** consumer-loan flat file,
maps/cleans it, stratifies (mapped group-bys + derived cohorts, 5+
side-by-side), computes balance- and count-weighted metrics + URCCP + vintage,
and draws a documentable **judgmental sample** (OCC doc, non-extrapolable).
Distinct from Credit Review OS Mode B (which keys pool totals + documents a
drawn sample); this computes loan-level and helps DRAW the sample.

- [x] **Build M1 (tracer):** canonical-field contract + confirm-not-silent
      column mapping (units/scale) + population-validation/cleaning gate
      (`_cleaning`) + core metric engine (WA both bases, dollar/count
      delinquency, URCCP via shared floors) + group-by + workbook + Seams 1–4.
      (Slices #79/#81/#82.)
- [x] **Build M2:** derived-cohort layer (structured rules → shared evaluator →
      overlap matrix + residual), side-by-side + A/B comparison, band schemes
      (CFPB / Y-14Q preset / custom), gross charge-off rate. (Slices #82/#83/#84.)
- [x] **Build M3:** vintage curves/triangle, conditional roll matrix (only if a
      prior-bucket column is mapped), judgmental sampling (rank/flag + coverage +
      OCC doc), ASCII bundle + `_readme`/methodology. (Slices #84/#85/#86.)
- [x] **[LOG] Shared-core extraction (touched `credit-review-os`):** DONE —
      `satc_credit_core` holds `URCCP_FLOORS` + classification-clock resolver +
      TIN byte-scan; credit-review-os imports it (108 tests still green); bench
      imports it; vendored into the ASCII bundle. Cohort compiler is a fresh
      pandas-mask evaluator (credit-review-os's evaluator emits Excel formulas,
      not reusable) — safe structured rules, per PRD R9. One URCCP impl.
- [x] **[LOG] PII-boundary reversal (project-specific decision):** IMPLEMENTED —
      the bench's **runtime populated workbook may hold real borrower PII** (bank
      equipment/VPN, never leaves the machine; no gates/masking/vault; loan
      number is the pull key). The TIN byte-scan is **repointed** to guard only
      the shipped tool / repo / demo fixtures (100% synthetic). In `_readme` + PRD §7.
- [ ] **[LOG] Deferred (decided against for v1):** cross-period snapshot
      retention + multi-snapshot roll rates / Markov projection; net-of-recovery
      NCO (no recovery data — gross-only charge-off rate ships, labeled);
      statistical sampling / sample-size calculator; auto-drawing the sample
      (tool ranks/flags, reviewer picks); 8-digit FR Y-14Q segment-ID crosswalk
      (a Y-14Q band *preset* ships); at-rest workbook encryption.
- [ ] **Inherited debt (needs YOUR desk):** URCCP pin-cite verification vs live
      regulator PDFs before the first filed workpaper (same as Credit Review OS
      §5; regulator sites block automated fetch).

## 7 · Standing rules for new items

New idea -> add a line here (one sentence, why it matters). New lesson
found in any build -> `TEMPLATE_CONTRACT.md` carried lessons (L-series),
not here. Anything touching the watchlist boundary or licensing -> gets a
research pass before a spec, no exceptions.

---

## Done log

- 2026-07-05 -- Consumer Credit Population Bench v1 BUILT (issues #79-#87 on
  PR #78): standalone `credit-population-bench/` (pandas engine behind an
  `.xlsm` surface) + new shared `satc_credit_core` (URCCP floors + resolver +
  TIN byte-scan) imported by both this bench and Credit Review OS (one URCCP
  impl; CR-OS 108 tests still green). Delivered: confirm-not-silent column
  mapping with units (`_map`); refuse-on-hard-error cleaning gate (`_cleaning`);
  WA metrics both bases; delinquency (3 input forms) + dollar/count rates +
  URCCP classification (closed/open/residential); group-by + band schemes
  (CFPB default / Y-14Q preset / custom) + cardinality guard; derived cohorts
  (structured rules -> safe pandas masks, overlap matrix + residual, A/B);
  vintage summary/triangle + gross charge-off + conditional roll matrix;
  judgmental sampling (rank/flag + coverage + auto OCC doc, non-extrapolable);
  pure-ASCII emailable bundle (byte-identical empty-folder rebuild, shared core
  vendored) + `_code_py` discovery + expanded `_readme`/methodology. 57 bench
  tests + 7 shared-core; deterministic builds (a set-order determinism bug
  caught by the cross-process bundle test and fixed). Deferred/inherited items
  remain in Section 6.
- 2026-07-05 -- Consumer Credit Population Bench PRD written (`/occam` grill →
  PRD): `credit-population-bench/docs/prd-credit-population-bench.md`. New
  standalone loan-level analysis project (sibling to Credit Review OS). Locked:
  standalone project sharing URCCP/evaluator/PII-guard from credit-review-os
  (one URCCP impl); structured-rule derived cohorts with overlap matrix +
  residual; confirm-not-silent column mapping with units; refuse-on-hard-error
  cleaning gate with `_cleaning` audit trail; both-basis rates always labeled;
  gross-only charge-off; CFPB default + Y-14Q preset + custom bands; conditional
  roll matrix; reviewer-picks judgmental sampling + OCC doc; PII-boundary
  reversal (runtime workbook may hold PII, shipped tool must not). Open build +
  `[LOG]` items in §6. Next: `/to-issues`.
- 2026-07-05 -- Credit Review OS v1 shipped (credit-review-os/, issues
  #60-#68 on PR #71): config-driven C&I loan-review engine — two-layer
  config (portable program + engagement overlay), per-loan linesheets with
  live-formula exceptions (doc/policy/compliance + rating disagreement),
  evidence staleness vs [ASOF], Master roll-up + criticized/classified
  totals, de-identified Data Mart + formulas-engine re-ingest,
  _methodology regulatory crosswalk (every element cited), Seam-3
  no-PII-leak guard (TIN last-4 everywhere), AES-256-GCM encryption-at-
  rest + credit-review CLI; 64 tests across the PRD's three seams,
  byte-identical deterministic builds. Roadmap lives in §5 above.
- 2026-07-03 -- Template #6 EDGAR Crit/Class Tracker shipped: commercial
  criticized/classified per competitor HC (extracted-XBRL-instance path,
  family-honest N/A gating, member-map bootstrap), 8-K credit-event lane
  with 2.04 auto-WATCH, accession provenance + --tieout/--selftest;
  16 tests, email-sim PASS, recalc parity, 94.6KB ASCII bundle verified.
  SUITE COMPLETE AT SIX -- new-build freeze; next step is the user's
  desk validation sprint (build_suite.py + --doctor + one tie-out).
- 2026-07-03 -- Template #4 v1.1 competitor pack shipped: Dashboard_LoanBook
  two-track (consumer DQ surveillance + commercial Call-Report floor),
  SVB metrics (uninsured share, unrealized/capital, FHLB), _provenance
  tab (69 field + 28 derived rows, honesty-flagged) + --tieout mode;
  20 tests, email-sim PASS, recalc parity 455 values/636 statuses,
  105KB ASCII bundle verified in empty folder.
- 2026-07-03 — Template #5 CFPB Mortgage Delinquency Monitor shipped:
  county-FIPS watchlist (the suite's finest key), [FOOTPRINT] slots,
  dev-12m + rise-streak transforms, SUPPRESSED/vintage/continuity
  handling; 16 tests, email-sim PASS, recalc parity, bundle verified.
- 2026-07-03 — Template #4 FDIC Bank Peer Monitor shipped (flexible
  [PEERS], authority-labeled thresholds, entity watchlist); L7 openpyxl
  None-write bug found + carried back to bureau/macro.
- 2026-07-02/03 — Template #3 Macro Early-Warning Monitor shipped (open
  state watchlist, staleness first-class); TEMPLATE_CONTRACT.md +
  control_center.py + ASCII-bundle standard (§11) landed.
- 2026-07-02 — Bureau review pass: 16 findings fixed (heat inversion,
  IFERROR empty-cell coercion, raw_slots guard, MS-OVBA protection keys).
- 2026-06-30..07-01 — Templates #1 (FRED) and #2 (bureau) shipped; PR #53.
