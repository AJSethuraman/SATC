# BUILD SPEC — Macro Early-Warning Monitor (v1)
### Reusable Excel workbook: macro/credit-cycle early-warning signals for credit-risk review, FRED provider, state-keyed watchlist

Grounded in `COVERAGE_RESEARCH_MACRO.md` (every series ID verified; licensing
and discontinuation findings binding). Governed by `TEMPLATE_CONTRACT.md`
(tabs, `_config` schema, runner CLI, extract-only macro, seam, verification
bar, ASCII-bundle transmission). Blueprint implementation:
`bureau-credit-risk-dashboard/` (contract-compliant reference — reuse its
shapes; carry all its review-pass fixes).

**Audience note (why this template exists):** the user sits in **credit-risk
review**. Every lane is framed as a *leading indicator of credit
deterioration*: labor signals lead consumer delinquency; the curve and
recession probabilities time the cycle for loss forecasting; spreads price
wholesale credit; SLOOS tracks the underwriting cycle; the state watchlist
turns macro stress into *footprint-level* early warning a portfolio's state
exposure can join on. Keep dashboard subtitles/readme in that language.

---

## Section 0 — Non-negotiable rules

0.1 **Watchlist hard gate.** Only genuinely state-keyed series may feed the
`Watchlist` lane. National aggregates are REFUSED with a series-named error
interpolated from the real `_config` row (id, geo_segment, source_class) —
never a hardcoded string. Default-deny (Section 3).

0.2 **Stateless.** Every refresh blanks all raw blocks first, then rewrites
newest-first. A failed fetch shows empty under the fresh timestamp — never
stale values.

0.3 **One provider (FRED), isolated** behind the Section-1a seam. No fredapi
dependency: plain `urllib` REST against `api.stlouisfed.org` (keeps
requirements to pandas+openpyxl).

0.4 **Workbook is the source of truth** (`_config`, `_code_py`, `_code_vba`).

0.5 **Deterministic; no LLM in the data path.** Named pure transforms only.

0.6 **STALENESS IS A FIRST-CLASS FAILURE (the SLIND lesson).** The Philly Fed
state leading indexes still *return data* frozen at Feb 2020. The runner MUST
compare each series' last observation to its cadence
(`stale_multiplier × period length`) and (a) mark the row `STALE` in the
digest/status, (b) exclude stale rows from alert counts, (c) never let a
frozen series silently satisfy a dashboard/watchlist cell. Fetch success ≠
data currency.

0.7 **Two providers mandatory:** live `FredProvider` + deterministic offline
`FredDemoProvider` (all tests, `--demo`).

---

## Section 1 — Provider & key handling

- **Class A (public, keyed):** FRED REST API. Key from env `FRED_API_KEY`
  (preferred) or `_config` `[SETTINGS] fred_api_key` cell. Never hardcoded,
  never echoed. Demo mode needs no key/network.
- Throttle **0.6 s/request** (documented limit 120/min), retry with backoff on
  HTTP 429; derive last-observation from fetched data (L5).
- Endpoint: `fred/series/observations?series_id=…&file_type=json`
  (+`sort_order=desc&limit=<raw_slots>` to fetch only what lands).

## Section 1a — Adapter seam (contract §6)

`fetch_series(spec, secret=None) -> list[NormalizedRow]`;
`NormalizedRow = {id, period, value, geo_segment, source_class, units}`.
FRED "." missing-value marker → `None`.

---

## Section 2 — `_config` dictionary

Contract §3 schema (19 columns, `[SETTINGS]`/`[THRESHOLDS]`/`[SERIES]`).
Settings: `demo_mode`, `raw_slots` (default **60**, build-bound),
`fred_api_key` (blank cell fallback), `http_min_interval` (0.6),
`fred_max_retries` (4), `stale_multiplier` (2.0), `secret_env` (blank; v2).

### Seed rows — national lanes (~20 rows, all `lane="dashboard"`, `geo_segment="national"`, `watchlist_capable=FALSE`)

Per research: `T10Y3M` (level; threshold below: watch 0.0 / alert −0.5),
`T10Y2Y`, `T10Y3MM`; `SAHMREALTIME` (level; watch 0.30 / alert 0.50 above —
the canonical trigger), `SAHMCURRENT` (context; notes: history mutates with
revisions), `ICSA` (yoy_ma4; watch +10 / alert +25), `IC4WSA`, `CCSA` (notes:
one week behind ICSA); `BAMLH0A0HYM2` (level; watch 5.0 / alert 8.0 — notes
MUST carry: "© Ice Data Indices — display-only; FRED serves ~3yr window from
Apr 2026; thresholds are static references, not computed percentiles"),
`BAMLC0A0CM` (same flag), `NFCI` (level; watch 0.0 / alert 0.5), `ANFCI`,
`STLFSI4` (level; watch 0.0 / alert 1.0), `DRTSCILM` (level; watch 20 /
alert 40 — underwriting cycle), `KCFSI` (optional monthly complement),
`PERMIT` (yoy_pct on 3m-smoothed — use `yoy_ma3`; notes: preliminary prints),
`HOUST` (yoy_ma3), `UMCSENT` (yoy_pct; notes MUST carry: "source-mandated
1-month delay — as of prior month; © University of Michigan"), `AWHMAN`
(level), `NEWORDER` (yoy_pct; notes: nominal, not deflated),
`RECPROUSM156N` (level; watch 20 / alert 50; notes: 2-3 month lag,
confirmatory only). EXCLUDED (dead/absent — must not appear as fetchable
rows): TEDRATE, CFSI, `{ST}SLIND`/USSLIND, Conference Board LEI.

### Seed rows — geographic watchlist (`lane="watchlist"`, `watchlist_capable=TRUE`, `geo_segment="state:XX"`)

Generated (not hand-typed) from the state list:
- **`{ST}UR`** — 50 states + DC (51 rows). Monthly SA. transform **sahm_gap**.
- **`{ST}ICLAIMS`** — 50 states (DC unverified — omit). Weekly NSA. transform
  **yoy_ma4** (never raw deltas — NSA noise).
- **`{ST}PHCI`** — 50 states (no DC — verified gap). Monthly SA. transform
  **chg_3p**. Notes: annual benchmark re-estimation revises full history;
  no Oct-2025 observation (survey never collected).

≈ 171 series total. Weekly cadence needs ≥56 observations for yoy_ma4 —
`raw_slots=60` satisfies it; assert this in `test_config_parse`.

---

## Section 3 — Transforms, thresholds, watchlist gate

### Transform registry (pure; extends the contract set)

`level`, `yoy_pct`, `qoq_pct`, `mom_pct`, `zscore_8q`, `index_to_pct`
(base-relative — carry the bureau fix), plus new named transforms:
- **`ma4`** — 4-period moving average (weekly claims smoothing).
- **`yoy_ma4`** — percent change of the 4-period MA vs the 4-period MA one
  year of periods earlier (52 for weekly, 12 for monthly).
- **`yoy_ma3`** — same with a 3-period MA (monthly housing).
- **`chg_3p`** — arithmetic change over 3 periods (PHCI 3-month change).
- **`sahm_gap`** — mean(latest 3 observations) − min(the 12 observations
  before those 3). Defined EXACTLY this way in BOTH Python and the Excel
  formula (`AVERAGE(v0:v2) − MIN(v3:v14)`) so workbook and digest can never
  disagree (bureau lesson). Documented as a Sahm-STYLE state gap (the
  canonical Sahm rule uses the min of the trailing 3m-MA; this variant is
  chosen for exact Excel parity).

Every transform must have a hardcoded-expected-value test, and
`_headline_formula` must implement EVERY registry name (bureau review lesson —
no silent level fallback).

### Threshold engine

Config-driven `[THRESHOLDS]` (id, watch, alert, direction) as in the bureau
template; national ids seeded per Section 2. State watchlist alerting uses a
single config setting `sahm_state_band` (default 0.50) referenced by defined
name from the Watchlist formulas — 151 per-id threshold rows would be noise.

### Watchlist validator — default-deny, three gates + staleness

1. REFUSE unless `watchlist_capable=TRUE`.
2. REFUSE unless `source_class="A"` — this template's only admitted class is
   the public FRED adapter; anything else (including a future Class C swap)
   requires its own review before admission. A flipped flag on an
   unanticipated class must not slip through.
3. REFUSE unless `geo_segment` matches `^state:[A-Z]{2}$` (explicit whitelist
   pattern; `national`, `us`, `msa`, `county`, anything else → refused
   default-deny; MSA/county promotion is a spec change, not a config edit).
4. **Runtime staleness guard (0.6):** an admitted row whose last observation
   is older than `stale_multiplier × cadence` is marked STALE, shown as such,
   and excluded from alert KPIs. Build-time hard gate
   (`assert_no_national_in_watchlist`) backs gates 1–3.

Refusal message shape (0.1): series-named, interpolated, naming the required
key: national/aggregate series cannot localize a portfolio footprint; the
watchlist admits only state-keyed labor/coincident series.

---

## Section 4 — Workbook structure (contract §2)

- `Dashboard_Conditions` — curve, credit spreads (⚠ display-only lane), NFCI/
  ANFCI/STLFSI4, SLOOS. Subtitle: cycle position & wholesale credit pricing.
- `Dashboard_Labor` — Sahm pair, claims family, AWHMAN. Subtitle: labor leads
  consumer delinquency.
- `Dashboard_Housing_Sentiment` — PERMIT/HOUST (3m-smoothed), UMCSENT (⚠ 1-mo
  delay label), NEWORDER, RECPROUSM156N. Subtitle: demand, sentiment, and the
  confirmatory lane.
- `Watchlist` — ADMITTED state rows, ranked: state, UR sahm_gap, claims
  yoy_ma4, PHCI chg_3p, composite rank, STALE flag column. Boundary banner
  states the geographic rule. Refused rows (if any) render the refusal.
- `Raw_FRED` — single raw tab, fixed-anchor blocks, newest-first.
- `_config`, `_code_py`, `_code_vba`, `_readme` per contract. `_readme`
  carries the ICE/UMich licensing flags verbatim, the SLIND discontinuation
  note, the Oct-2025 hole, and the credit-risk framing of each lane.
- Column L status panel; no native charts (L4); pure-ASCII embedded code (L3);
  heat direction = red-is-stress everywhere it's used (bureau lesson); blank-
  guard every raw reference (bureau lesson); `keep_vba` gated on `.xlsm` (L2).

## Section 5 — Bootstrap + transmission (contract §5/§11)

`ExtractFiles` macro (module `MacroMonitor`) writes runner.py /
requirements.txt / RUN.txt — extract-only. `make_bundle.py` generates
**`build_macro_monitor.py`** (pure ASCII, ≤~60 KB) producing the
demo-populated `.xlsm`, fallback `.xlsx` + `macro.bas`, runner.py,
requirements.txt locally. requirements: `pandas>=1.5`, `openpyxl>=3.0` only.

## Section 6 — Build phases, each with a named headless test (all `--demo`)

1. **Skeleton + seed** — `test_config_parse`: ~171 rows parse; every state row
   matches `^state:[A-Z]{2}$`; raw_slots ≥ 56; no excluded/dead id (SLIND,
   TEDRATE, CFSI) present; every national row watchlist_capable=FALSE.
2. **Providers** — `test_demo_provider_deterministic` (fixed asof, identical
   twice); `test_fred_provider_parse_and_cache` (parse a FIXED in-test JSON
   fixture incl. "." → None, cache serves repeat calls, 429 backoff path unit-
   tested with a stub — NO network).
3. **Transforms** — `test_transforms`: hardcoded expected values for ALL
   registry names, incl. sahm_gap and yoy_ma4 on a fixture; NaN propagation.
4. **Dashboards** — `test_reload_headless`: keep_vba reload, tab set exact,
   zero native charts, headline formulas exist for every dashboard row.
5. **Watchlist** — `test_watchlist_admits_states` (POSITIVE: state rows pass
   all gates and render ranked in the tab); `test_watchlist_refusal`
   (a national row placed in the lane is refused, series-named);
   `test_watchlist_gate_defense_in_depth` (flip a national row's flag → geo
   gate still refuses; fabricate class "C" state row → class gate refuses).
6. **Staleness** — `test_stale_flag`: a demo series fabricated with a frozen
   last-observation is marked STALE, excluded from alert counts, and visible
   in the digest (the SLIND regression test).
7. **Idempotence + layout** — `test_raw_landing_idempotent` (TRUE same-file
   double run), `test_raw_layout_mismatch_refused` (raw_slots flip refused).
8. **Acceptance** — `email_sim.py`: extract from the .xlsm alone, demo run,
   composed email contains the national alert summary AND the ranked state
   stress section AND any staleness flags; deterministic at fixed `--asof`.
   Then the full verification bar (contract §9): formulas-engine recalc spot-
   check, olevba decompile, OPC package audit, bundle built and executed in an
   empty folder.

## Section 7 — Scope fence

**In:** the ~20 verified national series; the 3 verified state families; the
composite-free-LEI framing via individual components; ASCII bundle; Control
Center compatibility.
**Out (v1):** county/MSA watchlist rows (enumeration-dependent IDs; promotion
path documented), `EQFXSUBPRIME*` (license note unverified — Open Q), any
Conference Board data, computed full-cycle OAS percentiles (3-yr window),
ALFRED vintage replay, portfolio ingest (the workbook shows footprint stress;
joining exposure weights stays manual, as in the FRED template's boundary).

## Compliance / licensing (binding, from research)

ICE BofA: display-only, attribution, 3-yr window, flag-for-legal on cached
values. UMCSENT: 1-month delay label + attribution. FRED terms: no
redistribution of third-party content; key mandatory. Fed/Treasury/BLS/Census
series unproblematic. All UNKNOWNs stay flagged in `_readme` (Open Questions
of the research doc incorporated by reference).

## Traps carried (M1–M7, additive to L1–L6)

M1 frozen-series staleness (0.6) · M2 ICE 3-yr window · M3 Oct-2025 hole
(transforms tolerate interior NaN) · M4 spring benchmark revisions (histories
mutate — alerts are point-in-time, not replayable without ALFRED) · M5 NSA
weekly noise (only MA/YoY transforms on claims) · M6 release calendars float
(never weekday heuristics; poll `fred/release/dates` if scheduling is ever
added) · M7 series-ID churn (surface "(DISCONTINUED)" in titles when fetched
live).
