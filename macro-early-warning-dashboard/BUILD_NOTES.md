# BUILD NOTES — Macro Early-Warning Monitor (v1)

Deliverable: `Macro_Early_Warning_Monitor.xlsm` (+ the ASCII transmission
bundle `build_macro_monitor.py`). Built to `BUILD_SPEC_MACRO.md` under
`TEMPLATE_CONTRACT.md`, from the verified `COVERAGE_RESEARCH_MACRO.md`.
Implementation blueprint: the review-hardened bureau template — every one of
its post-review fixes (blank-guarded formulas, stress-direction heat, raw-
layout mismatch refusal, stateless block clearing, shift-based pct-change
math, MS-OVBA-correct VBA container) is carried from the first commit.

## What's new in this template

- **The watchlist lane is OPEN**: 151 state-keyed series admitted (51 `{ST}UR`
  + 50 `{ST}ICLAIMS` + 50 `{ST}PHCI`) through the default-deny gates
  (`watchlist_capable` AND `source_class="A"` AND `^state:[A-Z]{2}$`).
  Positive admission is itself tested (`test_watchlist_admits_states`), not
  just refusal.
- **Staleness as a first-class failure (spec 0.6).** The runner compares each
  series' last observation to `stale_multiplier x cadence`; stale rows are
  marked STALE in the digest, reported on the status line, sectioned in the
  email, and excluded from alert counts. Regression test freezes a series two
  years back and asserts the alert count drops. Lesson source: the Philly Fed
  state *leading* indexes — discontinued, frozen at Feb 2020, still serving
  data without error; they are excluded from the seed and their ids asserted
  absent in `test_config_parse`.
- **New pure transforms** for NSA-noise-safe alerting: `ma4`, `yoy_ma4`,
  `yoy_ma3`, `chg_3p`, and `sahm_gap` = mean(latest 3) − min(the 12
  observations before those 3) — defined EXACTLY the same in Python and in
  the Excel formula (`AVERAGE(v0:v2)-MIN(v3:v14)`) so the workbook and the
  email digest cannot disagree. All 11 registry transforms have hardcoded-
  expected-value tests AND workbook headline formulas (no silent fallback).
- **Live provider is plain urllib REST** (no fredapi): 0.6 s throttle
  (120/min documented limit), 429/5xx backoff, per-URL cache, `sort_order=
  desc&limit=raw_slots` so only what lands is fetched. Key from
  `FRED_API_KEY` env or the `_config` cell; never echoed; live mode fails
  fast without it. Parse/backoff/cache paths are unit-tested against fixtures
  — **the live path has not been exercised against the real API in this
  build environment (no key); first live run is the remaining validation.**
- **State alerting via one knob**: `sahm_state_band` (default 0.50) as a
  numeric `_config` cell wired to a DefinedName consumed by the Watchlist
  status formulas. The build's recalc check caught the cell landing as TEXT
  `"0.5"` — Excel's `number >= text` is silently FALSE, which downgraded
  every state ALERT to WATCH; fixed to numeric with a regression test. (New
  lesson for the contract: threshold cells must be numeric-typed, and recalc
  verification must compare statuses, not just values.)

## Verification (headless, offline, `--demo`)

- **16 tests green**, including the spec-named set plus
  `test_fred_provider_429_backoff` and `test_live_run_requires_key`.
- **email-sim PASS**: national alert summary + ranked top-10 state stress
  section + staleness section, self-contained rebuild from the .xlsm alone.
  Demo digest at `--asof 2026-03-31`: 172/172 pulled, 7 ALERT / 6 WATCH /
  0 STALE; 5 state ALERTs in the demo ranking.
- **`formulas` recalc**: 51/51 Watchlist UR-gap values AND statuses match the
  Python digest exactly; 11 dashboard headlines match to 1e-9.
- **Package**: olevba decompiles `MacroMonitor`; exact tab set; zero native
  charts; zero overlapping merges; zero dangling relationships (fallback
  .xlsx included); `keep_vba` round-trip preserves the project.
- **Bundle**: `build_macro_monitor.py` (64.5 KB pure ASCII — slightly over
  the spec's soft ~60 KB target; the state seed and extra transforms are the
  delta) executed in an empty folder → working demo-populated .xlsm +
  fallback .xlsx + runner.py + requirements.txt.
- **Control Center**: discovered with zero wiring (contract §10 working as
  designed).

## Spec deviations (recorded)

1. `sahm_gap` fixture arithmetic: implemented spec-exact (1..18 → 13); the
   build task's worked example (14) contradicted the spec's own definition
   and Excel formula. Excel parity machine-verified.
2. Licensing notes rendered ASCII ("(c)", "--") — the pure-ASCII gate (L3)
   binds harder than "verbatim".
3. Watchlist tab has 6 columns (no STALE formula column — staleness is
   runtime state, surfaced via digest/status/email instead).
4. `IC4WSA` transform = `level` (it is already a 4-week MA; `yoy_ma4` would
   double-smooth); `CCSA` = `yoy_ma4` mirroring ICSA.

## Data-quality traps carried (M1–M7)

Frozen-series staleness; ICE 3-yr window (thresholds are static references);
Oct-2025 collection hole (transforms tolerate interior NaN); spring benchmark
revisions (alerts are point-in-time); NSA weekly noise (claims alert only on
MA/YoY transforms); floating release calendars (no weekday heuristics);
series-ID churn (surface "(DISCONTINUED)" titles when fetched live).

## Dependencies

Runtime: `pandas`, `openpyxl` only. Test/verify-only: `pytest`, `oletools`,
`formulas`.
