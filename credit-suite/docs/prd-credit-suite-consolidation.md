# PRD: credit-suite — one-engine consolidation of the Credit-Risk Monitor suite

**Status:** Draft · **Owner:** AJSethuraman · **Last updated:** 2026-09-03

> Pipeline: grilled 2026-09-03 (`grill-me`) → this PRD (`to-prd`) → `to-issues`.
> Roadmap/`[LOG]` items are mirrored to `BACKLOG.md` §"Suite infrastructure".

---

## 1. Problem

The Credit-Risk Template Suite is six shipped, emailable `.xlsm` monitors (FRED,
NY-Fed HHDC "bureau", macro early-warning, FDIC peer/Call-Report, CFPB mortgage,
EDGAR crit/class). They already share one written abstraction —
`TEMPLATE_CONTRACT.md` — but **only by convention and copy-paste**: every monitor
re-implements the same engine (workbook builder, `keybank_style`, threshold
engine, watchlist gate, VBA/macro, ASCII bundler, staleness guard), and FRED's
provider is implemented *twice* (once in `fred-credit-risk-dashboard/`, again in
`macro-early-warning-dashboard/`). A fix or a carried lesson (e.g. L7
clear-blocks, L8 numeric thresholds) must be hand-propagated to six folders; the
FRED template already drifted (it predates the contract). This is unsustainable
as the suite grows toward first-class **Call Report** ingestion and new sources.
The data the analyst most needs — bank-level Call Report figures for KeyBank and
peers — already exists in `fdic-peer-monitor` but on a copy of the machinery
that should be shared.

## 2. Solution

Build **`credit-suite/`**, one Python package (`src/` layout, mirroring
`credit-review-os/`) that owns the engine **once**. Each monitor collapses to a
**per-source provider adapter** (`fetch_series(spec, secret) -> list[NormalizedRow]`)
plus its **config/series-seed** — data, not code. The public deliverable stays a
self-contained, DLP-safe, emailable `.xlsm`: the shared library lives at dev time,
and a **build-time inliner** stitches it into each pure-ASCII self-contained
bundle (`TEMPLATE_CONTRACT.md §11`). We prove the seam on the two most divergent
monitors first — **FDIC** (bank-level, entity-keyed, Call-Report-derived) and
**FRED** (national time-series) — and require **cell-for-cell output parity** with
today's shipped workbooks so consolidation provably changes nothing a KeyBank
reviewer sees. The other four monitors, then raw FFIEC CDR / FR Y-9C, then new
sources, follow on the same engine.

## 3. Goals & Non-Goals

**Goals**
- One single-sourced engine; adding or fixing engine behavior touches one place.
- Spine: FDIC + FRED run through the shared engine, at full rigor **and** exact
  output parity with their current shipped `.xlsm`.
- The self-contained, emailable, DLP-safe deliverable and every carried lesson
  (L1–L8), the watchlist gate, `_provenance`/tie-out, and entity-as-config are
  preserved — nothing regresses.
- Adding a new source = one adapter + config, **zero engine edits** (the
  `credit-review-os` "new LOB = config only" success metric, applied to sources).
- On the unlocked build PC, "done" includes **live** verification, not just demo.

**Non-Goals / Out of scope**
- Merging `credit-review-os` (separate product; carries borrower PII + AES
  encryption the public-data monitors do not). It stays separate; it may later
  *consume* engine patterns, never merge.
- Any **live licensed Class-C feed** call (Prama/Experian/TransUnion) — stays
  gated/stubbed exactly as today; the gate opens only on a real contract.
- **Power BI** work — it is a downstream reader of engine outputs, not spine work.
- New sources beyond raw CDR / FR Y-9C (NCUA, HMDA, SBA, FHFA NMDB) — roadmap,
  not spine.
- Changing any monitor's *outputs* in the spine — parity forbids it; deliberate
  improvements come after parity is banked, as explicit, tested changes.

## 4. User Stories

1. As the analyst, I want the six monitors to behave identically and share one
   engine, so that a fix or new lesson lands everywhere at once instead of being
   hand-copied to six folders.
2. As the analyst, I want each monitor to still be a single self-contained
   `.xlsm` I can email through corporate DLP as plain text, so that consolidation
   does not cost me the property the suite was built around.
3. As the analyst, I want the migrated FDIC and FRED workbooks to produce the
   exact same values and statuses as today's shipped workbooks, so that I can
   trust the rebuild did not silently move a number headed for KeyBank.
4. As the analyst, I want every flagged value to remain traceable to its official
   record (Call Report schedule/line/MDRM, EDGAR accession, FRED series URL) via
   the `_provenance` tab and `--tieout`, so that I can defend a flag in minutes.
5. As the analyst, on my unlocked PC I want a real live FRED pull and a real live
   FDIC pull to flow an actual value into a flag, and to open the `.xlsm` in real
   Excel and click ExtractFiles once, so that the tool is proven end-to-end, not
   just in demo.
6. As a maintainer, I want to add a new data source by writing one provider
   adapter + a config/seed and nothing else, so that the suite grows without
   touching the engine.
7. As a maintainer, I want a conformance check that fails if any monitor
   re-copies an engine module or drifts from the tab/CLI contract, so that
   duplication cannot silently creep back.
8. As the analyst, I want my peer/entity set to be editable config (CERT/CIK/FIPS
   slots) with a `--lookup` helper, so that changing who I watch is a config edit,
   not a code change.
9. As a colleague who receives a bundle, I want to run one pure-ASCII script and
   get the working `.xlsm` locally, so that I never need the shared library
   installed or any binary to survive email.
10. As the analyst, I want the roadmap (raw CDR, FR Y-9C, NCUA/HMDA/SBA/NMDB,
    cross-monitor peer sync) captured so that the ground-up rebuild reaches the
    full vision without dropping ideas.

## 5. Requirements

1. [P0] A `credit-suite/` package (`src/` + `pyproject`) exposes the engine once:
   config model + parser, transform registry, threshold engine, watchlist
   default-deny gate, raw-layout, workbook builder, `keybank_style`, VBA/macro
   emitter, `_provenance` registry, staleness guard, ASCII bundler + inliner.
2. [P0] A single provider seam: `fetch_series(spec, secret=None) -> list[NormalizedRow]`,
   `NormalizedRow = {id, period, value, geo_segment, source_class, units}`
   (`TEMPLATE_CONTRACT.md §6`). Each source implements a live adapter + a
   deterministic offline `DemoProvider`.
3. [P0] FDIC and FRED migrated onto the engine as provider-adapter + config only;
   their duplicated engine modules deleted.
4. [P0] **Output parity:** a regression proves each migrated monitor reproduces
   its current shipped `.xlsm` **values and statuses cell-for-cell** (golden
   file), and emits a byte-identical self-contained ASCII bundle.
5. [P0] The full `TEMPLATE_CONTRACT.md §9` verification bar passes through the
   engine for each migrated monitor; carried lessons L1–L8 hold (regression tests
   for L7 clear-actually-blanks and L8 numeric-typed thresholds live in the
   engine, run once, cover all monitors).
6. [P0] The deliverable stays self-contained + emailable: build-time inliner
   produces the ASCII bundle (`§11`); Control Center (`§10`) still discovers and
   drives the workbook with no per-monitor wiring.
7. [P0] New engine tests carry mutation-proof discipline (a test that stays green
   with its target code removed is rejected).
8. [P1] Live acceptance on the unlocked PC: a live FRED pull (`FRED_API_KEY`) and
   a keyless live FDIC pull each flow a real value to a flag; a real-Excel
   ExtractFiles + recalc smoke passes. Runbook documented.
9. [P1] Conformance check: engine modules are single-sourced (no per-monitor
   copy), tabs/CLI match the contract — CI-runnable.
10. [P2] Provider adapters for the remaining four monitors reuse the engine with
    zero engine edits (proves the seam before Phase 2 formally migrates them).

## 6. Implementation Decisions

- **Package shape.** `credit-suite/src/credit_suite/…` with `pyproject.toml`,
  a CLI, and `tests/`, mirroring `credit-review-os`. Monitors live as
  `credit_suite.sources.<name>` (adapter) + a `configs/<name>/` seed. The engine
  never imports a source; sources depend on the engine.
- **The seam is the contract's `NormalizedRow`.** FDIC is already
  contract-compliant and migrates by moving its `fetch_series` adapter over
  unchanged. **FRED is grandfathered and is a real translation, not a lift:** its
  current runner uses a `SeriesSpec` dataclass + pandas `Series` + `coerce_series`
  + `evaluate_alert` + a `--backend` flag + a `Watchlist_Geo` tab. The migration
  wraps FRED's fetch to **emit `NormalizedRow`s**, and the engine reproduces
  FRED's existing outputs (including the grandfathered `Watchlist_Geo` tab name
  and `--backend` acceptance) **because parity (Req 4) pins them**. Any later
  de-grandfathering (rename tab, drop `--backend`) is a separate, post-parity
  change with its own regression update — never silently during migration.
- **Source-specific quirks live in the adapter, never the engine:** EDGAR's
  two-stage submissions→XBRL fetch + member-map bootstrap; CFPB's page-scrape →
  CSV download; FDIC's BankFind bulk call; FRED's `.`→NaN coercion and rate-limit
  backoff. The engine sees only `NormalizedRow`s.
- **Provenance is an engine output, not a per-template retrofit.** The engine
  consumes a per-source provenance seed (the model already authored in
  `fdic-peer-monitor/provenance_seed.py` — Call Report schedule/line/MDRM + FFIEC
  facsimile URL — and `edgar-crit-class-tracker/provenance_seed.py` — 10-Q note +
  XBRL tag + accession) and emits the `_provenance` tab + `--tieout` for every
  monitor uniformly (`§12`).
- **Inliner.** Extends the existing `make_bundle.py` pattern: instead of embedding
  a single copied `runner.py`, it resolves the engine's shared modules + the
  source adapter + config and emits them as the self-contained `_code_py` /
  bundle, pure ASCII, ≤ contract size target. Output is byte-identical run-to-run
  for a fixed input (determinism).
- **Config schema unchanged** (`§3`): `[SETTINGS]` / `[THRESHOLDS]`
  (`id|watch|alert|direction`) / `[SERIES]` (19-col) / `[PEERS]`|`[FOOTPRINT]`
  slots (`§13`). Threshold cells numeric-typed (L8); a non-numeric/absent band an
  alert rule reads is refused, not silently coerced (carried from this session's
  FRED fix — now an engine-level `validate_thresholds`).
- **Runner CLI** per `§4` (exit 0/1/2/3, JSON stdout + human stderr), plus the
  zero-pull-is-failure guard from this session's FRED fix promoted into the
  engine.

## 7. Testing Decisions

- **Seam(s) (confirm):**
  1. **Primary — the monitor runner + workbook artifact**, headless, per source.
     The engine is tested *through* each migrated monitor's runner and the `.xlsm`
     it writes (behavior, not internals) — the existing `test_runner.py` /
     `test_build.py` seam, now pointed at the engine. Highest, fewest seams; it's
     what the suite already uses.
  2. **New — output-parity golden file.** A committed snapshot of each current
     shipped monitor's values+statuses; the migrated build must reproduce it
     cell-for-cell. This is the top consolidation-safety seam.
  3. **New — engine unit seam** for pure logic shared across sources (transforms,
     threshold/`validate_thresholds`, watchlist gate, raw-layout, staleness),
     tested once with hardcoded expected values, mutation-proven.
  4. **New — conformance seam** (Req 9): asserts single-sourced engine + contract
     tab/CLI shape.
  5. **Live acceptance (opt-in, unlocked PC)** (Req 8): a marked test / runbook
     doing a real FRED + FDIC pull and a real-Excel ExtractFiles+recalc — not run
     in CI, run on the free PC as the last mile.
- **What a good test proves:** the migrated monitor produces the *same* numbers
  and statuses as before (parity), through single-sourced engine code, and no new
  test passes with its target code deleted (mutation). Reuse existing prior art:
  `fdic-peer-monitor/tests/` (contract-compliant reference) and this session's
  mutation-proven `fred-credit-risk-dashboard/tests/`.
- **Data handling:** PUBLIC regulatory data only (FRED, FDIC/Call Reports, EDGAR,
  CFPB, BLS). No client PII, no secrets in any artifact; the only secret is an
  optional API key read from an env var named in `[SETTINGS] secret_env`, never
  stored in a tab or bundle. (Borrower-PII/encryption is `credit-review-os`'s
  concern and out of scope here.)

## 8. Success Metrics

- **0** duplicated engine modules across monitors (conformance check green);
  FRED implemented **once** (the double implementation is gone).
- FDIC + FRED: **100%** cell parity (values + statuses) vs current shipped
  `.xlsm`, and a byte-identical bundle.
- Full `§9` bar + new parity + mutation tests green; L7/L8 regressions green.
- A new source demonstrably adds via **1 adapter + config, 0 engine edits**.
- On the unlocked PC: a live FRED value and a live FDIC value each reach a flag;
  real-Excel ExtractFiles + recalc succeeds.

## 9. Milestones / Rollout

- **M1 (MVP / spine):** `credit-suite` engine + inliner; FDIC + FRED migrated;
  full rigor + output parity; live FRED/FDIC + real-Excel acceptance on the
  unlocked PC. `[LOG]`
- **M2:** migrate bureau, macro, CFPB, EDGAR onto the engine; retrofit `§12`
  provenance to all six; suite-wide conformance CI. `[LOG]`
- **M3:** **raw FFIEC CDR** provider + **FR Y-9C** holding-company. **Opens with a
  `research` pass** (CDR bulk Public Data Distribution vs SOAP webservice; RSSD vs
  CERT keying; Call Report FFIEC 031/041 vs FR Y-9C) — resolve from primary
  sources before speccing. `[LOG]`
- **M4 (bench):** NCUA, HMDA, SBA, FHFA NMDB adapters; cross-monitor peer sync
  (one entity list across FDIC CERT + EDGAR CIK via a name crosswalk). `[LOG]`

## 10. Risks & Open Questions

- **Risk — parity vs. cleanup tension.** Output parity pins FRED's grandfathered
  quirks (`Watchlist_Geo`, `--backend`). Mitigation: bank parity first; schedule
  de-grandfathering as explicit post-parity changes with updated goldens.
- **Risk — inliner regressions self-containment.** A shared library that fails to
  fully inline would ship a workbook that needs the library present. Mitigation:
  the bundle test builds and runs in an empty folder (existing `email_sim`/
  bundle-in-empty-folder pattern) as a hard gate.
- **Risk — engine abstraction wrong for a later source.** Mitigation: the spine
  deliberately spans the two most divergent shapes (entity-keyed bank-level vs
  national series) before four monitors depend on it.
- **Resolved (2026-09-03):** the build PC is **Windows with Excel installed**, and
  a **`FRED_API_KEY`** will be provisioned there. Live FRED + real-Excel
  ExtractFiles/recalc acceptance are therefore in-scope for "done" (M1). FDIC live
  is keyless.
- **Open question (business):** replace the illustrative seed peer set (CERTs /
  CIKs) with your real KeyBank peer list — a config edit via `--lookup`, yours to
  supply.

## 11. Done Criteria

- [ ] `credit-suite` engine exists; FDIC + FRED run through it as adapter+config;
      their duplicated engine modules are deleted.
- [ ] Output parity: FDIC + FRED reproduce current shipped `.xlsm` values+statuses
      cell-for-cell; byte-identical ASCII bundle; builds/runs in an empty folder.
- [ ] `§9` verification bar + engine unit tests + L7/L8 regressions pass, all
      mutation-proven; conformance check confirms single-sourced engine.
- [ ] Live acceptance on the unlocked PC: real FRED + real FDIC value each reach a
      flag; real-Excel ExtractFiles + recalc succeeds.
- [ ] `_provenance` + `--tieout` present for FDIC and FRED.
- [ ] Roadmap (M2–M4) recorded in `BACKLOG.md`; `credit-suite/README.md` written.
