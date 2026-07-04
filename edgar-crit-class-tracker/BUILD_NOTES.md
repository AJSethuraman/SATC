# BUILD NOTES -- EDGAR Criticized/Classified Tracker (pack 1.0)

Built to `BUILD_SPEC_EDGAR.md` (Sections 0-7, traps E1-E10), grounded in
`COVERAGE_RESEARCH_EDGAR.md`, governed by `TEMPLATE_CONTRACT.md`. Blueprints:
`fdic-peer-monitor/` (slot mechanism, entity gates, --lookup, --tieout,
provenance pattern) and `cfpb-mortgage-monitor/` (status styling,
full-replace semantics). `keybank_style.py`, `vba_writer.py`, `.gitignore`
copied VERBATIM from fdic-peer-monitor; `assemble_xlsm.py` adapted (module
`CritClassTracker`, workbook `Crit_Class_Tracker.xlsm`).

## Verification (all green at ship)

1. **pytest: 16/16 passed** -- every named test from spec Section 6:
   `test_config_parse`, `test_demo_provider_deterministic`,
   `test_submissions_parse` (columnar fixture + items harvest + 10-Q/A
   amendment dedupe by acceptanceDateTime + Q4-is-10-K + full `prime()`
   through stubbed transport incl. CIK-padding split E8 + per-URL cache),
   `test_instance_parse` (fixture extracted-instance XML: standard members
   AND one extension member AND vintage line items that are IGNORED, plus
   prior-period / extra-axis / class-only / subtotal trap contexts;
   hardcoded expected rollups: total 150,000 / criticized 14,000 /
   classified 8,000 / SM 6,000), `test_backoff` (429 retry+sleep, labeled
   5xx failure, 403 fails FAST with UA guidance, blank-UA fail-fast ->
   exit 3, 0.15s throttle floor), `test_member_bootstrap` (append as
   unmapped into the provisioned rows, idempotent, denominator-only, never
   guessed), `test_metrics` (hardcoded ratios/deltas; criticized_only Tier 1
   yes / Tier 2 None; ig_nig all None; excluded classes out of denominators;
   totals-only fallback blanks the mix), `test_reload_headless` (tabs exact,
   zero charts, VBA intact, numeric thresholds L8, N/A gates in-formula),
   `test_watchlist_entity_gates` (+ defense-in-depth non-Class-A metric),
   `test_stale_bank`, `test_8k_event_lane` (auto-WATCH on 2.04 incl. on an
   otherwise-OK bank and on an ig_nig bank; 2.06 informational),
   `test_provenance_and_tieout` (quoted definitions + viewer URL patterns +
   per-metric rows; tieout carries accession + /Archives URL + member
   breakdown + DEMO label; quarter arg both ISO and YYYYQn),
   `test_raw_landing_idempotent` (TRUE same-file idempotence incl. _config),
   `test_raw_layout_mismatch_refused`, `test_clear_actually_blanks` (L7:
   identity + metric + fact + event rows actually blank on deactivate),
   `test_vba_protection_keys_roundtrip`. NO network in any test.
2. **email_sim.py: PASS** -- fresh folder, workbook-only, extract-run-compose;
   ranked criticized table (10 rows) + family flags + Tier-2 n/a rendering +
   8-K events (item 2.04 flagged WATCH) + staleness + unmapped-member
   section + data-vintage line; workbook self-contained.
3. **Bundle in an EMPTY scratch folder**: `build_edgar_tracker.py`
   (94,588 bytes, pure ASCII) built `Crit_Class_Tracker.xlsm` (126,645 B,
   demo-populated) + `Crit_Class_Tracker_fallback.xlsx` (122,210 B, no VBA,
   demo-populated) + runner.py + macro.bas + requirements.txt.
   **olevba** decompiles module `CritClassTracker` from the .xlsm. OPC
   audit on BOTH packages: no dangling relationships, no overlapping
   merges, zero charts; fallback carries no vbaProject part or content type.
4. **formulas-engine recalc parity: PASS** -- the demo-populated fallback
   recalculated headlessly; per-slot Watchlist criticized ratios (9 decimal
   match), QoQ deltas, statuses (ALERT/WATCH/OK/N-A incl. the family gate),
   RANK column vs the digest-derived (ALERT-flags, criticized) ordering,
   N/A rows unranked, dashboard PEER MEDIAN (3.188513 = engine = digest),
   and the banks-in-alert KPI (1 = digest) all agree with `compute_digest`.
5. **ASCII grep clean** on every new file (runner, seeds, builder, macro,
   bundle, tests, email_sim).
6. **control_center.py --list** discovers `Crit_Class_Tracker` and reads its
   status line ("Banks 10/10 - 1 ALERT / 1 WATCH ... 1 UNMAPPED MEMBERS").

Demo digest at --asof 2026-03-31: Comerica ALERT (criticized 7.86%, SM
ALERT), Zions WATCH (4.67% + the 2.04 8-K auto-WATCH), USB N/A (ig_nig),
KeyCorp/M&T Tier-2 n/a (criticized_only), Fifth Third carries the one
unseeded extension member (`fitb:CriticizedRestructuredMember`) exercising
the bootstrap.

## Deviations from spec/contract (each justified)

- **No `[SERIES]` section** (contract sec 3). Spec Section 2 defines this
  template's `_config` as [SETTINGS]/[THRESHOLDS]/[PEERS]/[MEMBER_MAP]/
  [CLASS_MAP], and the spec is authoritative. The metrics here are fixed
  derived rollups of ONE disclosure (not user-selectable series), held in
  the in-code `METRIC_SPECS` registry carrying the contract's
  `source_class`/`watchlist_capable` gate fields (defense-in-depth tested).
  Launcher compatibility needs only `_code_py` (contract sec 10) -- verified.
- **Grade vocabulary extended** beyond the spec list with
  `investment_grade`/`noninvestment_grade` (so the ig_nig dialect is MAPPED,
  not flooding the unmapped lane, while still rendering N/A) and `ignore`
  (filer-tagged SUBTOTALS: us-gaap:CriticizedMember parents the adverse
  leaves -- summing both would double-count; seeded `ignore` for every
  grades_full bank).
- **Unmapped grade members enter the DENOMINATOR only** (they are part of
  total commercial amortized cost -- a fact, not a guess), never a
  numerator, and are flagged until manually mapped. Unmapped CLASS members
  are excluded from rollups entirely (commerciality unknowable).
- **Class axis acceptance widened**: the legacy
  `FinancingReceivableRecordedInvestmentByClassOfFinancingReceivableAxis`
  AND `FinancingReceivablePortfolioSegmentAxis` are accepted (many filers
  dimension the CQI table by portfolio segment); any OTHER axis on a
  context drops the fact (double-count guard).
- **Fact audit block = latest quarter, 36 rows/slot.** The spec's per-slot
  facts block is bounded to fixed anchors; the headline rollups are
  latest-quarter, and any historical quarter is auditable via
  `--tieout CIK <quarter>` (full member breakdown from the same engine).
  Overflow rows carry a "(+N more -- see --tieout)" note.
- **8-K events are windowed at land time** (trailing 366 days ~ 4 quarters,
  8 rows/slot) so the Excel COUNTIF lane needs no date math.
- **Exit code 3 for a blank `edgar_user_agent`** (contract reserves 3 for
  "missing secret"; the UA is this template's analogous missing
  credential-like prerequisite).
- **Bundle is 94.6 KB** vs the contract's "target <= ~60 KB" -- consistent
  with the blueprints (fdic 105 KB, cfpb 79 KB); still one pure-ASCII file.
- **Excel PEER MEDIAN includes stale banks** (Excel cannot see runtime
  staleness); the digest median excludes them -- carried, documented
  divergence (same as fdic), noted in `_readme` and asserted in
  `test_stale_bank`.
- **Extension-member seed qnames (`key:`/`mtb:`/`hban:`) are ILLUSTRATIVE**
  placeholders for the researched disclosure shapes -- flagged as such in
  `_config` comments; the first live fetch resolves the real qnames through
  the same bootstrap the tests exercise.

## Open items (v1.1 candidates / validate live)

- **Live path is fixture-tested only.** The sandbox's proxy blocks sec.gov
  (trap E10 observed here too), so `EdgarProvider` stages 1-2 are verified
  against captured-shape fixtures (columnar submissions incl. items arrays,
  index.json, extracted-instance XML), not a live pull. First live run:
  `--selftest`, then `--tieout 35527` against the actual filing, then a
  full refresh; expect the member bootstrap to land real extension qnames
  to map.
- **Family-coverage estimate to validate live**: research put grades_full
  at ~60-75% of $10B+ regionals and pass-vs-criticized at >90% -- BOTH
  UNVERIFIED estimates; measure across the seed set + any additions on the
  first live quarter.
- ig_nig MD&A full-text fallback (efts.sec.gov lane) -- those banks stay
  honestly N/A in v1.
- FSNDS bulk-ZIP backfill for deep history; pre-2019 EX-101.INS instances
  (v1 skips them with a per-filing error note).
- Fiscal-year (non-calendar) filers: quarters key off reportDate, so
  off-calendar fiscal ends land as their own periods; the staleness guard
  covers lag, but Q4-is-10-K commentary assumes calendar-year filers (true
  for all 10 seeds).
- HC vs CERT reconciliation stays manual/approximate (noted in _readme).
- The recalc-parity check runs at verification time via the `formulas`
  package (not in requirements); it is not a shipped test.
