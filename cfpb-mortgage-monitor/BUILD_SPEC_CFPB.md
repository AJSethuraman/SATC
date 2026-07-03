# BUILD SPEC — County Mortgage Delinquency Monitor (v1)
### Lean Excel workbook: county-level mortgage credit OUTCOMES for a portfolio footprint, CFPB Mortgage Performance Trends provider

Grounded in `COVERAGE_RESEARCH_CFPB.md` (binding). Governed by
`TEMPLATE_CONTRACT.md`. Blueprints: `fdic-peer-monitor/` (the flexible SLOT
mechanism — reuse it wholesale for the footprint) and
`macro-early-warning-dashboard/` (staleness/continuity guard). Carry every
L1-L8 lesson. This is the LEANEST template in the suite — resist scope
growth.

**What it answers:** "In the counties where my collateral actually sits,
is mortgage delinquency rising?" — realized outcomes (30-89 and 90+ DPD),
monthly, ~6-7 months lagged, joinable on county FIPS. The confirming
counterpart to the macro template's leading indicators.

---

## Section 0 — Non-negotiables

0.1 **Watchlist hard gate:** only `^county:[0-9]{5}$` keys admitted
(default-deny; states/metros/national are dashboard context, never
watchlist). Series-named interpolated refusals.
0.2 Stateless full-replace every run — REQUIRED here beyond convention:
every CFPB vintage revises the ENTIRE history.
0.3 One provider (CFPB), isolated; plain urllib; keyless.
0.4 Workbook is source of truth (incl. the `[FOOTPRINT]` list).
0.5 Deterministic; no LLM; transforms pure, Python==Excel parity.
0.6 **Vintage/continuity is first-class:** the runner records the vintage
(`thru-YYYY-MM` from the filename) + publication discovery in the status
panel; if the newest vintage is older than `continuity_months` (default 9)
behind `--asof`, surface a CONTINUITY WARNING (the program publishes
informally and survived 2025 turmoil once). Suppressed footprint counties
render "SUPPRESSED (below sample threshold) — use the state row", never
blank-and-silent, never zero.
0.7 Two providers: live `CfpbProvider` + deterministic `CfpbDemoProvider`.

## Section 1 — Provider

- **Live fetch is TWO-STAGE:** (1) GET the download page
  (`consumerfinance.gov/data-research/mortgage-performance-trends/
  download-the-data/`), regex the CURRENT dated filenames per
  geo x measure (`{State|County}MortgagesPercent-{30-89|90-plus}DaysLate-
  thru-YYYY-MM.csv`); (2) GET the 4 CSVs (state + county, both measures;
  SKIP metro — mixed non-FIPS keys). Throttle 0.6s; retry/backoff;
  per-URL cache. If page-scrape fails, accept a `vintage` setting override
  (`thru-2025-09`) to construct URLs directly.
- **Parse (schema CONFIRMED):** wide CSV; header row `RegionType,State,
  Name,FIPSCode,2008-01,...`; unpivot by `^\d{4}-\d{2}$` header pattern
  (never position); **strip the literal single quotes around FIPS**; keep
  FIPS as TEXT; filter `RegionType` (National row `FIPSCode="-----"` is
  its own series, not a county); values are percent floats.
- Series ids: `nat_{d3089|d90}`, `st_{FIPS2}_{d3089|d90}`,
  `co_{slot:02d}_{d3089|d90}` (county series are SLOT-keyed like FDIC
  peers so footprint edits never move anchors).
- `--lookup "<county or state name>"` helper: greps the fetched county CSV
  for name matches and prints County, State, FIPS (works offline against
  the demo/bundled fixture too — implement as an offline-friendly search).

## Section 2 — `_config`

`[SETTINGS]`: demo_mode, raw_slots (default **72** months — 6 years),
http_min_interval 0.6, cfpb_max_retries 4, continuity_months 9,
vintage ("" = discover from the page), footprint_slots (built capacity,
informational), secret_env "".
`[THRESHOLDS]` keyed by measure/transform ids (below).
**`[FOOTPRINT]`** (the FDIC `[PEERS]` mechanism, verbatim pattern):
`slot | fips | name | state | active` — one row per county; 40 slots
built by default (`make_workbook.py --footprint-slots N`); over-capacity
REFUSED with a rebuild message; add/remove = edit + re-run. Seed: 12
illustrative large counties (verified FIPS from the inspected file, e.g.
01003 Baldwin AL, 01073 Jefferson AL, plus well-known: 06037 Los Angeles,
17031 Cook, 48201 Harris, 04013 Maricopa, 06073 San Diego, 12086
Miami-Dade, 36047 Kings NY, 39035 Cuyahoga, 42101 Philadelphia, 53033
King WA) — note in-sheet: replace with your footprint; `--lookup` finds
FIPS.
`[SERIES]`: national + state dashboard rows (states derived from the
seed footprint's distinct states at BUILD time, slot-provisioned to 15
state slots) + the 2-measure county template rows expanded per footprint
slot at run time.

## Section 3 — Transforms + gate

Registry (carry base set) + new pure transforms, Excel-parity exact:
- **`dev_12m`** = v0 − mean(v1..v12) (deviation from own trailing-12
  average, in percentage points). Excel: `v0-AVERAGE(v1:v12)`.
- **`rise_streak3`** = IF(v0>v1,1,0)+IF(AND(v0>v1,v1>v2),1,0)+
  IF(AND(v0>v1,v1>v2,v2>v3),1,0) — consecutive-rise count capped at 3;
  identical capped definition in Python.
- `level`, `yoy_pct` retained.
Thresholds (heuristic, honest labels): d3089 `dev_12m` watch 0.3 / alert
0.6 above; d90 `rise_streak3` watch 2 / alert 3 above; d90 `level` watch
1.5 / alert 3.0 above (long-run non-crisis ~<1%; GFC county peaks far
higher). One knob per band in `[THRESHOLDS]`, numeric-typed (L8).
Watchlist gates: (1) footprint slot active; (2) `source_class="A"`;
(3) `^county:[0-9]{5}$` (built from the `[FOOTPRINT]` fips cell; blank/
malformed fips refused BY NAME with a `--lookup` hint). Build-time hard
gate backs them. Suppression handling per 0.6.

## Section 4 — Workbook

- `Dashboard_State` — footprint states + National: both measures, latest /
  dev_12m / 12m sparkline slot; National row pinned first as benchmark.
- `Dashboard_Trends` — National + worst-5 footprint counties by d90 level
  (formula-ranked), 24-month trend columns readout (formula-driven cells,
  no charts).
- `Watchlist` — footprint counties ranked: County | State | FIPS | 30-89
  latest | dev vs 12m avg | 90+ latest | rise streak | Status |
  (SUPPRESSED rendered explicitly). Rank by (status severity, d90 dev).
- `Raw_CFPB` — per (series x slot) fixed-anchor blocks, newest-first.
- `_config` (with `[FOOTPRINT]`), `_code_py`, `_code_vba`, `_readme`
  (NMDB 5% sample honesty, ~6-7 month lag labeling, suppression rule,
  full-history revision note, vintage provenance, continuity tripwire,
  public-domain status).
- Column L status: Last run · vintage `thru-YYYY-MM` · counts · continuity
  warning if stale. Heat: red = rising delinquency. All L1-L8 carried.

## Section 5 — Bootstrap + transmission

Macro module `MortgageMonitor` (STATUS_SHEET `Dashboard_State`); RUN.txt:
demo, live (keyless; explain vintage discovery + `vintage` override),
`--lookup`. `make_bundle.py` -> **`build_cfpb_monitor.py`** (pure ASCII).
requirements: pandas, openpyxl.

## Section 6 — Phases + named tests (headless, `--demo`)

1. `test_config_parse` — [FOOTPRINT] parses; slot expansion; over-capacity
   refused; state dashboard rows derived; all FIPS 5-digit text.
2. `test_demo_provider_deterministic`; `test_cfpb_provider_parse` — parse
   a FIXTURE CSV built from the REAL inspected header/rows (quoted FIPS
   stripped, National filtered, wide->long by header pattern, percent
   floats, absent county -> SUPPRESSED not zero); `test_filename_discovery`
   — regex the dated filenames out of a FIXTURE download-page HTML +
   the `vintage` override path; `test_provider_backoff` (stubbed).
3. `test_transforms` — dev_12m and rise_streak3 hardcoded expectations
   (incl. streak cap and NaN tolerance).
4. `test_reload_headless` — tabs exact, zero charts, VBA intact, numeric
   threshold cells.
5. `test_watchlist_county_gates` — positive admission; blank-fips refusal
   naming the slot + `--lookup` hint; inactive exclusion; malformed keys;
   defense-in-depth (non-A class).
6. `test_suppressed_county` — a footprint county absent from the demo
   data renders SUPPRESSED, excluded from alert counts, present in email.
7. `test_vintage_continuity` — vintage older than continuity_months
   triggers the warning in status + email.
8. `test_full_replace` — two runs with DIFFERENT demo vintages: second
   run's history fully replaces the first (no stale months survive) —
   the revision-semantics regression.
9. `test_raw_landing_idempotent`, `test_raw_layout_mismatch_refused`,
   `test_clear_actually_blanks` (L7), `test_vba_protection_keys_roundtrip`.
10. `email_sim.py` — ranked county watchlist + state summary + vintage
    line + suppression + continuity sections; deterministic. Then the full
    contract §9 bar + bundle-in-empty-folder.

## Section 7 — Scope fence

**In:** state + county lanes, both measures; flexible [FOOTPRINT];
vintage discovery + override; suppression + continuity handling; --lookup.
**Out (v1):** metro/non-metro file (no FIPS join); FHFA NMDB fallback
provider (research it if the CFPB program dies); any interpolation for
suppressed counties; HMDA enrichment; nowcasting (the lag is the lag).

## Traps carried (C1-C7)

C1 quoted FIPS (strip; text-typed) · C2 dated filenames (discover, never
hardcode) · C3 full-history revisions (full-replace; never diff vintages
as movement) · C4 suppression by omission (absent != zero) · C5 wide
format (header-pattern unpivot) · C6 ~6-7 month lag (label as-of
prominently) · C7 National row in every file (RegionType filter).
