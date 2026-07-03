# BUILD NOTES -- County Mortgage Delinquency Monitor (v1)

Deliverable: `Mortgage_Delinquency_Monitor.xlsm` (+ the ASCII transmission
bundle `build_cfpb_monitor.py`). Built to `BUILD_SPEC_CFPB.md` under
`TEMPLATE_CONTRACT.md`, from the verified `COVERAGE_RESEARCH_CFPB.md`.
Implementation blueprints: the FDIC peer template (the flexible SLOT
mechanism -- `[PEERS]` there is `[FOOTPRINT]` here, reused wholesale:
slot-keyed unit ids, identity-by-formula from config cells, over-capacity
refusal, `--lookup` helper, build-time slots knob) and the macro template
(staleness/continuity guard, urllib provider). Every carried fix baked in
from the first commit: blank-guarded formulas, direction-aware stress heat,
raw-layout mismatch refusal, stateless clearing with EXPLICIT `.value =
None` (L7), `keep_vba` gated on `.xlsm` (L2), pure-ASCII embedded code
(L3), no native charts (L4), column-L status panel, MS-OVBA `vba_writer`,
numeric-typed threshold cells (L8).

## What's new in this template

- **The county [FOOTPRINT] slot lane.** `slot | fips | name | state |
  active`, 40 built slots (`make_workbook.py --footprint-slots N`), 12
  illustrative seed counties (01003 Baldwin AL and 01073 Jefferson AL are
  quoted verbatim from the inspected CFPB file). County unit ids are
  slot-keyed (`co_{slot:02d}_{d3089|d90}`) so a footprint edit moves no
  anchor; identity reaches the Watchlist BY FORMULA from the config cells;
  over capacity refuses with the exact rebuild command. State dashboard
  rows (`st_{FIPS2}_{measure}`) were derived from the seed footprint's 10
  distinct states at BUILD time and provisioned to 15 fixed state slots;
  national is `nat_{measure}`.
- **Two-stage keyless live provider (traps C2/C5/C1/C7).** Stage 1 scrapes
  the download page for the CURRENT dated filenames
  (`(State|County)MortgagesPercent-(30-89|90-plus)DaysLate-thru-YYYY-MM
  .csv`), honoring a `vintage` settings override that skips the scrape;
  stage 2 fetches 4 CSVs (State + County x both measures; Metro skipped --
  mixed non-FIPS keys). Wide CSVs are unpivoted by the `^\d{4}-\d{2}$`
  HEADER pattern (never position), the literal single quotes around FIPS
  are stripped (FIPS kept TEXT end-to-end), the National row
  (`FIPSCode='-----'`) is filtered by RegionType into its own `nat_*`
  series, blank cells land as None. Throttle 0.6s, 429/5xx backoff,
  per-URL cache; 5 GETs per refresh total.
- **Suppression is first-class (trap C4).** A footprint county ABSENT from
  the fetched vintage renders `SUPPRESSED (below sample threshold) -- use
  the state row` -- in the runner digest, in the Watchlist Status column
  BY FORMULA (blank latest cells after a landed run), in the raw block
  header (identity + note written, data left blank), in the email, and in
  its own KPI tile -- and is EXCLUDED from every alert count. The demo
  provider deliberately omits seed slot 12 (King County WA 53033) so the
  path is exercised on every demo run.
- **Vintage + continuity (traps C3/C6, spec 0.6).** The vintage
  (`thru-YYYY-MM`) and its provenance (discovered/override/demo) go on
  status-panel line 3; line 4 is ALWAYS overwritten with either
  `Continuity OK (N months behind asof; tripwire M)` or the CONTINUITY
  WARNING (naming the DataLumos recovery mirror). Every run is a stateless
  FULL REPLACE because every vintage revises the whole history --
  `test_full_replace` proves two demo vintages leave no stale months and
  that overlapping history is actually revised.
- **New pure transforms, Excel-parity exact.** `dev_12m` =
  `v0-AVERAGE(v1:v12)` (Python mean skips missing months exactly as
  AVERAGE ignores blanks) and `rise_streak3` = `IF(v0>v1,1,0)+
  IF(AND(v0>v1,v1>v2),1,0)+IF(AND(v0>v1,v1>v2,v2>v3),1,0)` capped at 3,
  blank-guarded on `COUNT(v0:v3)=4` in both languages; `level`/`yoy_pct`
  retained. Thresholds keyed by measure/transform (`d3089_dev12m` 0.3/0.6,
  `d90_streak3` 2/3, `d90_level` 1.5/3.0), all `above`, numeric cells (L8).
- **Offline-friendly `--lookup`.** `--demo` searches an embedded 24-county
  mini-index (the 12 seeds + 12 well-known counties); live mode greps the
  fetched county CSV (~470 rows) and prints County/State/FIPS with the
  keep-it-text reminder.

## Verification (headless, offline, `--demo`)

- **16 tests green** -- the spec-named set: `test_config_parse` (incl.
  over-capacity + duplicate-slot + >15-state refusals, FIPS text
  normalization), `test_demo_provider_deterministic` (incl. vintage
  revision semantics), `test_cfpb_provider_parse` (REAL-schema fixture:
  header `RegionType,State,Name,FIPSCode,2008-01,...`, National row
  `'-----'`, QUOTED FIPS `'01003'`, MetroArea row filtered, blank cell ->
  None, absent county -> [], newest-window, per-URL cache, schema-drift
  refusals), `test_filename_discovery` (HTML fixture with two vintages +
  the override path making zero page calls), `test_provider_backoff`,
  `test_lookup_offline`, `test_transforms`, `test_reload_headless`,
  `test_watchlist_county_gates`, `test_suppressed_county`,
  `test_vintage_continuity`, `test_full_replace`,
  `test_raw_landing_idempotent`, `test_raw_layout_mismatch_refused`,
  `test_clear_actually_blanks` (L7), `test_vba_protection_keys_roundtrip`.
- **email-sim PASS**: ranked county watchlist (11 rows) + state summary
  (NATIONAL + 10 states) + vintage line + suppression section (King County
  -> "use the WA state row") + continuity section; self-contained rebuild
  from the .xlsm alone. Demo digest at `--asof 2026-04-30`: 11/12 counties
  landed, 2 ALERT (Miami-Dade FL, Harris TX) / 2 WATCH (Maricopa AZ,
  Cuyahoga OH) / 1 SUPPRESSED (King WA), 10 states, vintage thru-2025-09
  (demo), continuity OK (7 months behind, tripwire 9).
- **`formulas` recalc parity -- 0 mismatches**: all 40 Watchlist slot rows
  (30-89 dev_12m, 90+ rise streak, 90+ latest, STATUS text incl. the full
  SUPPRESSED string and blank empty slots), all 11 Rank cells, the 3 KPI
  tiles (incl. the `SUPPRESSED*` wildcard COUNTIF), national + state
  Dashboard_State cells, the worst-5 Dashboard_Trends identities
  (LARGE/MATCH/INDEX) and their newest-month values, the month header, and
  the 12-char ASCII trend strip -- all vs the Python digest at 1e-9.
- **Package**: olevba decompiles module `MortgageMonitor`; exact tab order
  `Dashboard_State / Dashboard_Trends / Watchlist / Raw_CFPB / _config /
  _code_py / _code_vba / _readme`; zero native charts; zero overlapping
  merges; zero dangling relationships (.xlsm and fallback .xlsx both
  audited); `keep_vba` round-trip preserves the project.
- **Bundle**: `build_cfpb_monitor.py` (~79 KB pure ASCII) executed in an
  EMPTY folder -> working demo-populated .xlsm + fallback .xlsx +
  runner.py + macro.bas + requirements.txt (pandas + openpyxl).
- **Control Center**: discovers the workbook with zero wiring (contract
  sec 10).
- ASCII grep clean on every new file (`keybank_style.py` retains its
  pre-existing non-ASCII docstring; it is the byte-identical house module
  from the blueprints and is never embedded as text).

## Spec deviations (recorded)

1. **State-slot identity is runtime state, not config-cell formulas.**
   County identity is by formula from `[FOOTPRINT]` cells (the binding slot
   requirement); state rows read their abbrev/FIPS2 from the raw block
   header the runner writes. Rationale: the state list lives in [SERIES]
   (per spec) where rows are appended, not slot-anchored, so config-cell
   anchors could not survive user edits; state rows are dashboard context,
   not gated watchlist. Documented in the Dashboard_State note row.
2. **Watchlist has 9 columns** (spec lists 8): a `Rank` column after
   Status makes the (severity, 90+ dev) ordering sortable in-sheet, plus
   labeled helper columns K (90+ dev_12m) and L (rank score) feeding the
   RANK formula -- FDIC precedent.
3. **"12m sparkline slot" is a formula-built ASCII trend strip**
   (`^`/`v`/`-`, newest left) rather than a reserved empty cell: openpyxl
   cannot create real sparklines, charts are banned (L4), and the strip is
   deterministic and recalc-verifiable. One per measure per state row.
4. **Demo default vintage derives from `--asof`** (asof minus 7 months,
   mirroring the real lag) instead of a fixed date, so a bundle built on
   any date shows a healthy continuity line; tests pin explicit vintages
   (via the `vintage` setting or provider arg) when they need staleness or
   revision semantics. At the canonical test asof 2026-04-30 this yields
   thru-2025-09 -- the real current vintage.
5. **Bundle is ~79 KB**, over the contract's soft ~60 KB target (FDIC
   shipped 75.7 KB, macro 64.5 KB, with the same note); the 3-geo landing,
   trends INDEX machinery and the suppression/continuity paths are the
   delta.
6. **Excel-side FIPS gate requires a TEXT cell** (`ISTEXT` + `LEN=5`),
   while the runner re-pads NUMERIC cells (a user typing 6037 into a
   General cell) back to "06037". A number-typed cell therefore shows
   REFUSED in the sheet while the runner accepts it -- same class of
   divergence as FDIC's ISNUMBER cert gate, documented here; the refusal
   text itself points at --lookup, which prints the correctly-formatted
   FIPS.

## Data-quality traps carried (C1-C7)

C1 quote-wrapped FIPS (stripped in parse; TEXT `@` format + ISTEXT gate;
`_norm_fips` re-pads numeric cells) | C2 dated filenames (page-scrape
discovery + `vintage` override; never hardcoded) | C3 full-history
revisions (stateless full replace; vintage on the status panel; trends tab
labeled "not a stitched archive") | C4 suppression by omission (explicit
SUPPRESSED everywhere; excluded from KPIs; never zero/interpolated) | C5
wide format (header-pattern unpivot; fixture includes non-contiguous month
columns) | C6 ~6-7 month lag (masthead, vintage line, email wording;
"confirming, not nowcast") | C7 National row in every file (RegionType
filter; `nat_*` series read from the state file).

## Open items

- **Live path fixture-tested only**: consumerfinance.gov is proxy-blocked
  in this build environment, so discovery/parse/backoff/cache are verified
  against the captured-schema fixtures; the first live run (keyless, at
  the user's desk) is the remaining validation, including live `--lookup`.
- **Informal publication cadence**: the ~semiannual schedule is not
  promised; the 9-month tripwire is a heuristic. If it fires: download
  page first, DataLumos mirror second, FHFA NMDB aggregates (state/CBSA
  quarterly -- NOT county-monthly) as the partial fallback. Researching an
  FHFA fallback provider is deliberately out of v1.
- **Open questions from the research carry forward**: exact county count
  in the current vintage (~470 estimated), whether threshold_year ever
  moved off 2016, the six literal current URLs (pattern confirmed, page
  blocked here).
- **Ten of twelve seeded FIPS are well-known but not file-verified**
  (01003/01073 are); the in-sheet comment tells the user to `--lookup`
  before relying on any seed row.
- **v1.1 candidates**: surface the per-county vintage/as-of month in the
  Watchlist (currently implicit in the shared month grid); optional real
  sparklines via a guarded PaintSparklines macro; state-row auto-derivation
  from the live footprint at run time (currently a documented [SERIES]
  edit).

## Dependencies

Runtime: `pandas`, `openpyxl` only. Test/verify-only: `pytest`, `oletools`,
`formulas`.
