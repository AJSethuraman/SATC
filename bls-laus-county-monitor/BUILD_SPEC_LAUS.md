# PRD / Build Spec: BLS LAUS County Unemployment Monitor (Template #7)

> Template #7 in the Credit-Risk Template Series. This is the pipeline PRD **and**
> the suite build spec for this template (`grill-me → to-prd → to-issues`).
> **Binding:** `TEMPLATE_CONTRACT.md` governs everything not restated here. Facts
> below are verified against BLS primary sources (see Sources).

**Status:** Draft · **Owner:** Arjun Sethuraman · **Last updated:** 2026-07-04

---

## 1. Problem

A lender/portfolio owner watching credit risk across a **county footprint** has
no monitor for the single most timely local-stress signal: **county
unemployment**. The macro template covers labor stress at the **state** level;
counties — the actual join key for a loan book — are a gap. County unemployment
turns before delinquency does, so an early-warning view keyed to the footprint is
valuable.

## 2. Solution

A standalone, self-contained `.xlsm` (contract-compliant) that pulls **BLS Local
Area Unemployment Statistics (LAUS)** for the user's footprint counties, lands raw
monthly data, and renders a formula-driven watchlist that flags counties whose
unemployment rate is deteriorating **year-over-year**. One provider (BLS) behind
the standard adapter seam, with a keyless demo provider for offline use.

## 3. Goals & Non-Goals

**Goals**
- Monthly county unemployment monitor keyed to a configurable `[FOOTPRINT]`.
- A watchlist that ranks/flags counties by a **seasonality-robust** stress signal.
- Full `TEMPLATE_CONTRACT.md` compliance (tabs, runner, seam, gate, verification).

**Non-Goals / Out of scope**
- No state/national rollups; **county geographies only**.
- **No seasonal adjustment of county data** (BLS does not publish it — see §6).
- No second data source; no live API key in tests; no charts (formulas only, L4).
- Not a forecast — it reports observed deterioration, not predicted.

## 4. User Stories

1. As the owner, I want to list my footprint counties by FIPS and see each one's
   latest unemployment rate, so that I have a portfolio-keyed view.
2. As the owner, I want counties flagged watch/alert when their unemployment rate
   has risen materially **vs the same month a year ago**, so that seasonal swings
   don't create false alarms.
3. As the owner, I want the watchlist ranked by that YoY deterioration, so that
   the worst-trending counties surface first.
4. As the owner, I want to edit my footprint (add/remove a county) by changing one
   config row and re-running, so that the tool tracks my real book.
5. As the owner, I want an offline demo mode that needs no API key, so that I can
   see it work before registering.
6. As the owner, I want the workbook to be the whole tool (email it, re-run it),
   so that it fits how the rest of the suite works.

## 5. Requirements

1. [P0] **Provider** `fetch_series(spec, secret=None) -> list[NormalizedRow]`
   pulling BLS LAUS. Two implementations: live BLS + a deterministic **keyless
   DemoProvider** (used by every test).
2. [P0] Pull, per footprint county, the **unemployment rate** (`…03`) and **labor
   force** (`…06`) county LAUS series: `LAU` + `U` (unadjusted) + `CN` + 5-digit
   county FIPS + `0000000` + measure. E.g. `LAUCN281070000000003`.
3. [P0] **Watchlist signal = YoY change** in the county unemployment rate
   (current month − same month prior year). Show current rate level + 12-month
   trend. **Do not** use MoM/Sahm-style momentum on this unadjusted data (§6).
4. [P0] **Thresholds** (`[THRESHOLDS]`, config-driven, `id|watch|alert|direction`,
   red = stress): **watch ≥ +0.5pp**, **alert ≥ +1.0pp** YoY.
5. [P0] **Watchlist gate** (default-deny, contract §7): admit only rows whose key
   matches `^county:[0-9]{5}$`, with `watchlist_capable=TRUE` and admitted
   `source_class`; refusals series-named; build-time hard gate backs the runtime
   gate.
6. [P0] **`[FOOTPRINT]`** section (`slot | fips | name | state | active`), **40
   slots** built by default (`make_workbook.py --footprint-slots N`), seeded with
   a few illustrative counties + an in-sheet "replace with your footprint" note;
   `--lookup` resolves county names/FIPS. Reuse the FDIC `[PEERS]` / CFPB
   `[FOOTPRINT]` mechanism verbatim.
7. [P0] **`_config`**: `[SETTINGS]` (`demo_mode`, `raw_slots` = **72** months,
   `secret_env` = `BLS_API_KEY`, `footprint_slots`), `[THRESHOLDS]`, `[SERIES]`.
8. [P0] **Runner CLI** `python runner.py --workbook <path.xlsm> [--demo]
   [--asof YYYY-MM-DD]`, openpyxl against the closed workbook (`keep_vba=True`),
   exit codes 0/1/2/3, JSON status on stdout.
9. [P0] **Extract-only macro** exposing `ExtractFiles`/`ExtractAndRun`, writing
   `runner.py`, `requirements.txt`, `RUN.txt` (contract §5).
10. [P1] Watchlist **ranked** by YoY deterioration (worst first); ties broken
    deterministically.
11. [P1] **Staleness guard**: a county with no fresh month (or missing YoY base
    month) is marked STALE and excluded from ranking, not silently zero.

## 6. Implementation Decisions

- **County LAUS is NOT seasonally adjusted** (BLS publishes SA only for regions,
  states/DC/PR, and a few large substate/metro areas — never counties). Therefore
  the signal is **YoY** (same-month-prior-year), which nulls the seasonal
  component. A Sahm-style 3-mo-avg-vs-12-mo-low trigger (used by the macro
  template on *state SA* data) is **explicitly rejected here** because on
  unadjusted county data it fires on seasonality. Series use the **`U`
  (unadjusted)** seasonal code.
- **Series construction:** for a footprint FIPS `F`, request
  `LAUCN{F}0000000003` (rate) and `LAUCN{F}0000000006` (labor force). Normalize to
  `NormalizedRow{id, period, value, geo_segment="county:{F}", source_class,
  units}`.
- **API + auth:** BLS Public Data API v2. A **free registered key** is required
  for a real footprint: a 40-county × 2-series pull = **80 series**, and v2 allows
  **50 series/request, 500 queries/day only when registered** (keyless is 25/25),
  so batch into ≤50-series requests. Key via `secret_env=BLS_API_KEY`, never
  stored in the workbook; `--demo` needs no key. A bulk flat-file mirror
  (`download.bls.gov/pub/time.series/la/`) exists as a fallback but is out of
  scope for v1.
- **Data caveat to encode in `_readme`:** LAUS **re-benchmarks annually
  (Jan–Mar)**, revising history; note it (the macro template already documents
  this).
- **Tabs / style / bootstrap:** exactly per contract — `Dashboard_<Lane>`,
  `Watchlist`, `Raw_BLS`, `_config`, `_code_py`, `_code_vba`, `_readme`; all
  visuals from `keybank_style.py`; no native charts (L4).
- **Reuse, don't reinvent:** copy the `[FOOTPRINT]`/`--lookup` mechanism and the
  county-key gate from `cfpb-mortgage-monitor` (which already uses
  `^county:[0-9]{5}$`); copy the raw-landing + idempotence + `keep_vba` reload
  patterns from `fdic-peer-monitor`.

## 7. Testing Decisions

- **Seam (contract-mandated §9): pure transforms + the gate, tested vs hardcoded
  expected values, plus demo determinism** — mirroring `fdic-peer-monitor/tests/
  test_runner.py`. Named headless tests (all `--demo`, no network, no key):
  - `test_config_parse` — `_config` sections/keys parse; `raw_slots` build-bound.
  - `test_demo_provider_deterministic` — DemoProvider is byte-stable.
  - `test_transforms_and_derived` — **YoY signal** and **threshold classification
    (+0.5 / +1.0)** computed against hand-set expected values (independent of the
    code's own formula), incl. a county that crosses each boundary.
  - `test_watchlist_gates` — a `^county:[0-9]{5}$` key is admitted; a state/MSA/
    malformed key is **refused** (series-named), with the build-time hard gate
    also refusing (defense in depth).
  - `test_raw_landing_idempotent` — same-file re-run is idempotent.
  - `test_raw_layout_mismatch_refused` — a mismatched `raw_slots` layout is
    refused (exit 2).
  - `test_reload_headless` — reload with `keep_vba=True` preserves the macro.
  - no-native-charts assertion.
- Plus the suite acceptance rung: `email_sim.py`, a `formulas`-engine recalc
  spot-check, olevba decompile, OPC package audit.

## 8. Success Metrics

- On demo data, the watchlist flags exactly the counties whose YoY rate rise
  crosses the configured thresholds — no seasonal false positives.
- The workbook re-runs deterministically and refuses non-county keys.
- Passes the full contract verification bar headlessly.

## 9. Milestones / Rollout

- **M1 (v1):** provider (live + demo) → `_config`/`[FOOTPRINT]` → transforms +
  gate → workbook/tabs → macro bootstrap → full headless verification + email-sim.

## 10. Risks & Open Questions

*All researchable/codebase gaps are closed above. Open Questions are user-only.*
- **Risk:** the not-seasonally-adjusted nature is the crux — the YoY choice
  depends on it; any future "momentum" lane must not regress to MoM/Sahm on this
  data.
- **Risk:** registered-key rate limits (500/day) bound footprint × frequency;
  batching ≤50 series/request is required.
- **Open question (needs your action — bucket C only):** the **first live run on
  your Windows Excel** — open the `.xlsm`, click `ExtractFiles` once, register a
  free `BLS_API_KEY`, load your **real footprint counties**, and confirm the live
  pull matches. The build box can't do this (it's the suite's standing validation
  debt for every template).

## 11. Done Criteria

- [ ] Provider (live BLS + keyless DemoProvider) behind `fetch_series`.
- [ ] `_config` with `[FOOTPRINT]` (40 slots), `[THRESHOLDS]` (+0.5/+1.0),
      `raw_slots=72`, `secret_env=BLS_API_KEY`.
- [ ] YoY signal + threshold classification + county-key gate implemented and
      passing tests vs hardcoded expected values.
- [ ] Watchlist refuses non-county keys (runtime + build-time).
- [ ] Contract tabs/macro/style present; no native charts; idempotent re-run.
- [ ] Full headless verification bar + `email_sim.py` green.
- [ ] `_readme` documents the not-SA nature, YoY basis, Jan–Mar benchmark
      revisions, and the `BLS_API_KEY` step.

## Sources

- BLS, *Series ID Formats* — LAUS `LAUCN{FIPS}0000000{measure}` structure; measure
  `03` = unemployment rate, `06` = labor force. <https://www.bls.gov/help/hlpforma.htm>
- BLS, *LAUS Seasonal Adjustment* — county series are **not** seasonally adjusted.
  <https://www.bls.gov/lau/lauseas.htm>
- BLS, *Public Data API v2 / features* — 50 series/request & 500 queries/day
  (registered), 25/25 keyless; registration free.
  <https://www.bls.gov/developers/api_features.htm>
- Sahm rule (0.50pp, 3-mo avg vs trailing 12-mo low; national SA) — the magnitude
  the +0.5pp watch echoes. <https://fred.stlouisfed.org/series/SAHMCURRENT>
- Repo: `TEMPLATE_CONTRACT.md`; `cfpb-mortgage-monitor` (`[FOOTPRINT]` + county
  gate); `fdic-peer-monitor` (raw landing, `keep_vba`, test shape).
