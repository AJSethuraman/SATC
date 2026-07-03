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

- [ ] **FDIC:** SVB metrics UNBLOCKED (fields verified: DEPUNINS,
      SCHF/SCHA, SCAF/SCAA) -- folded into the competitor metric pack
      (section 3). Separately: blank stale banks' latest quarter + show
      STALE in the Watchlist status column (removes the documented median
      divergence); optional UBPR asset-band medians.
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

- [~] **#5 CFPB Mortgage Performance Trends** — county-level 30–89 and
      90+ DPD mortgage delinquency, free CSVs, public domain. The finest
      watchlist key of the whole suite (county), and actual credit
      OUTCOMES, not indicators. Small source -> lean build.
      *Research DONE (schema confirmed from a real file + CFPB's own
      generator code); spec written; build in flight.*
- [ ] **Competitor loan-book METRIC PACK on template #4** — RESOLVED:
      no FFIEC template needed. 93/93 fields verified in the FDIC API
      (full loan-category PD/nonaccrual/NCO matrix + the SVB pack:
      SCHF/SCHA HTM fair-vs-amortized, SCAF/SCAA, DEPUNINS uninsured
      deposits, OTHBFHLB). See fdic-peer-monitor/
      RESEARCH_COMPETITOR_PACK.md + SPEC_COMPETITOR_PACK.md (spec WRITTEN,
      build-ready). Build after #5 ships: Dashboard_LoanBook
      lane (consumer classes = the DQ surveillance track: card/auto/
      consumer/resi 30-89, 90+, NA, NCO; commercial classes as public
      proxy pending EDGAR crit/class) + SVB metrics + thresholds. FFIEC-only residue (category loan
      yields, UBPR percentiles) = bulk-ZIP ingest job only if ever needed.
- [ ] **#6 SEC EDGAR tracker — commercial crit/class mission (user
      design decision):** the suite's two-track competitor surveillance is
      CONSUMER = DQ/NCO via the FDIC metric pack (retail classification is
      formula-driven off DPD under the Uniform Retail Credit Classification
      policy — 90+ card DQ IS the substandard pipeline), and COMMERCIAL =
      criticized/classified via 10-Q/10-K credit-quality-indicator XBRL
      (C&I/CRE risk ratings lead delinquency; SM/Substandard/Doubtful carry
      UNIFORM interagency definitions, so cross-bank comparison is
      defensible — residual caveat is application timing only). Research
      pass must verify: XBRL tags/axes for internal grades (FinancingReceivable
      CreditQualityIndicator-family), criticized-total disclosures by class,
      coverage across regional banks. Original scope rides along: corporate
      counterparty fundamentals + 8-K event lane. Keyless (10 req/s,
      User-Agent header). *Research DONE — feasibility GREEN, tiered design
      (edgar-crit-class-tracker/COVERAGE_RESEARCH_EDGAR.md): extracted-XBRL-
      instance path for dimensional CQI, standard CriticizedMember exists,
      per-bank member-mapping table required, 8-K item 2.04 event lane.
      Spec next; build after the pack.*
- [ ] **#7 BLS LAUS county unemployment monitor** — monthly county-FIPS
      early warning; free API key, 500 q/day. (Partially covered by the
      macro template's state lane; standalone only if county cadence
      proves valuable at your desk.)
- [ ] **Later bench:** HMDA loan-level (annual research pull), SBA 7(a)/504
      FOIA (commercial charge-offs by county+NAICS), NCUA credit-union
      sibling of FDIC, FHFA NMDB aggregates.

## 4 · Suite infrastructure ideas (unscheduled — promote when wanted)

- [~] **Provenance/tie-out (contract §12, user requirement):** every value
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
- [ ] Control Center: "Refresh all (demo)" batch action; show each
      workbook's last-run timestamp + staleness at a glance.
- [ ] Single suite bundle (one ASCII file = Control Center + all template
      builders) if multi-file transfer ever becomes annoying (~200KB —
      may exceed comfortable paste size; per-template bundles remain
      primary).
- [ ] Regenerate the visual suite-overview page from live demo digests
      (currently hand-assembled).

## 5 · Standing rules for new items

New idea -> add a line here (one sentence, why it matters). New lesson
found in any build -> `TEMPLATE_CONTRACT.md` carried lessons (L-series),
not here. Anything touching the watchlist boundary or licensing -> gets a
research pass before a spec, no exceptions.

---

## Done log

- 2026-07-03 — Template #4 FDIC Bank Peer Monitor shipped (flexible
  [PEERS], authority-labeled thresholds, entity watchlist); L7 openpyxl
  None-write bug found + carried back to bureau/macro.
- 2026-07-02/03 — Template #3 Macro Early-Warning Monitor shipped (open
  state watchlist, staleness first-class); TEMPLATE_CONTRACT.md +
  control_center.py + ASCII-bundle standard (§11) landed.
- 2026-07-02 — Bureau review pass: 16 findings fixed (heat inversion,
  IFERROR empty-cell coercion, raw_slots guard, MS-OVBA protection keys).
- 2026-06-30..07-01 — Templates #1 (FRED) and #2 (bureau) shipped; PR #53.
