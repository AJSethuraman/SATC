# BUILD NOTES -- Bank Counterparty & Peer Monitor (v1)

Deliverable: `Bank_Peer_Monitor.xlsm` (+ the ASCII transmission bundle
`build_fdic_monitor.py`). Built to `BUILD_SPEC_FDIC.md` under
`TEMPLATE_CONTRACT.md`, from the verified `COVERAGE_RESEARCH_FDIC.md`.
Implementation blueprints: the macro-early-warning template (staleness guard,
urllib provider, generated seed) and the review-hardened bureau template --
every carried fix baked in from the first commit: blank-guarded formulas,
direction-aware stress heat, raw-layout mismatch refusal, stateless block
clearing, keep_vba gated on `.xlsm`, pure-ASCII embedded code, no native
charts, column-L status panel, MS-OVBA vba_writer, numeric-typed threshold
cells (the text-"0.5" lesson).

## What's new in this template

- **The inversion + flexible peers (USER REQUIREMENT).** Rows are BANKS. A
  new `[PEERS]` config section (`slot | cert | name | group | active`) is
  parsed alongside the contract sections; the runner expands active peers x
  the 15-metric `[SERIES]` dictionary into units `s{slot:02d}_{METRIC}`. Raw
  anchors depend ONLY on (slot, field); bank identity reaches dashboards BY
  FORMULA from the `[PEERS]` cells. `test_peer_flexibility` proves the loop
  on a BUILT+populated workbook: swap a new bank into a free slot +
  deactivate another, re-run demo, and the slot's raw block carries the new
  id/data, the deactivated slot is blanked, and the dashboard formula text is
  byte-identical (no rebuild). Capacity is a build knob
  (`make_workbook.py --peer-slots`, default 40; seed fills 12); over
  capacity the runner refuses with the exact rebuild command -- never
  truncation.
- **Entity-keyed watchlist gate.** Default-deny: active slot + Class A
  metric rows + entity key `^cert:[0-9]{1,7}$` built from the cert cell.
  Blank/malformed CERTs are refused BY NAME with a `--lookup` hint;
  inactive slots are EXCLUDED (blanked), not refused; a fabricated non-A
  metric row refuses the whole run, series-named. The Watchlist Status
  column renders REFUSED **by formula** too, so a bad cert is visible in
  the workbook itself, not just the digest.
- **One bulk request per refresh.** `FdicProvider` fetches the whole peer
  set in ONE `/financials` call (`CERT:(... OR ...) AND REPDTE:[oldest TO
  *]`, verified fields, `sort_by=REPDTE desc`, `limit=10000`) with a
  `meta.total > limit` guard (clear refusal, never silent truncation),
  double-wrap `data[i].data` parsing, JSON null -> None (never zero), plus
  one `/institutions` roster call (ACTIVE/ENDEFYMD -> merger notes).
  Throttle 0.6 s, 429/5xx backoff, per-URL cache;
  `meta.index.createTimestamp` recorded as the data-vintage line. **KEYLESS**
  -- no API key exists to configure; RUN.txt says so explicitly.
- **`--lookup "<name>"` CLI (USER REQUIREMENT):** fuzzy `/institutions`
  search printing CERT/ACTIVE/ASSET/CITY candidates for populating
  `[PEERS]` from PowerShell. Live-only, with a clear offline/demo message
  (`test_lookup_offline_message`).
- **Derived metrics defined twice, tested once.** PD3089R, TEXAS (variant),
  LNDEPR, BRODEPR, CRECONR are pure functions in `runner.METRICS` AND
  identical Excel formulas off the landed field blocks (blank + zero-denom
  guards match `_ratio` exactly). Every underlying raw field lands in
  `Raw_FDIC` (22 fields x 16 quarters per slot) as the audit trail.
- **Bank-level staleness (spec 0.6).** Per-bank latest REPDTE vs the
  peer-set max; > `stale_multiplier` quarters behind -> STALE, excluded
  from digest alert counts/medians, annotated "possible merger/closure --
  check /institutions ACTIVE, /history". Regression test freezes the demo
  ALERT-tier bank 3 quarters back and asserts the alert counts drop by
  exactly its flags.
- **openpyxl clearing bug found & fixed (new lesson).** `ws.cell(r, c,
  None)` is a silent NO-OP (openpyxl ignores a None value argument), so the
  blueprint's clear-then-rewrite pattern never actually blanked anything --
  masked upstream because those runners rewrite every cleared cell.
  Here stateless clearing is load-bearing (deactivated slots must blank),
  so `clear_slot_block`/`write_slot_block` assign `.value = None`
  explicitly; `test_peer_flexibility` regression-covers it. Candidate
  carry-back to the FRED/macro/bureau templates.

## Verification (headless, offline, `--demo`)

- **14 tests green** -- the spec-named set (`test_config_parse` incl.
  over-capacity refusal, `test_demo_provider_deterministic`,
  `test_fdic_provider_parse_and_cache` against a captured-envelope fixture,
  `test_fdic_provider_backoff`, `test_lookup_offline_message`,
  `test_transforms_and_derived`, `test_reload_headless`,
  `test_watchlist_entity_gates`, `test_stale_bank_flag`,
  `test_peer_flexibility`, `test_raw_landing_idempotent`,
  `test_raw_layout_mismatch_refused`, `test_vba_protection_keys_roundtrip`)
  plus the Class C seam stub.
- **email-sim PASS**: ranked peer table (12 rows, names + Texas + flag
  counts), per-dimension alert lines, staleness section, data-vintage line;
  self-contained rebuild from the .xlsm alone. Demo digest at
  `--asof 2026-03-31`: 12/12 banks, 2 ALERT / 5 WATCH / 0 STALE banks,
  12 ALERT flags (one illustrative Texas-ALERT bank at 108.1, one
  Texas-WATCH at 52.3 -- fiction assigned by hash, stated in-sheet).
- **`formulas` recalc parity -- 0 mismatches**: all 12 Watchlist Texas
  values, ALERT/WATCH flag counts AND bank-level statuses match the Python
  digest exactly (1e-9); the full Asset-Quality MEDIAN row (6 columns)
  matches; the BANKS-IN-ALERT KPI tile matches; empty slots render blank.
- **Package**: olevba decompiles module `PeerMonitor`; exact tab order
  `Dashboard_AssetQuality / Dashboard_Capital_Earnings /
  Dashboard_Funding_Concentration / Watchlist / Raw_FDIC / _config /
  _code_py / _code_vba / _readme`; zero native charts; zero overlapping
  merges; zero dangling relationships (fallback .xlsx audited too);
  `keep_vba` round-trip preserves the project.
- **Bundle**: `build_fdic_monitor.py` (75.7 KB pure ASCII) executed in an
  EMPTY folder -> working demo-populated .xlsm + fallback .xlsx +
  runner.py + macro.bas + requirements.txt (pandas+openpyxl).
- **Control Center**: discovers both the .xlsm and the fallback with zero
  wiring (contract sec 10).
- ASCII grep clean on all new files (`keybank_style.py` retains its
  pre-existing non-ASCII docstring; it is the byte-identical house module
  from both blueprints and is never embedded as text).

## Spec deviations (recorded)

1. **Demo seeding is per (cert, field), not per (slot, metric)** as the
   build task's parenthetical suggested: keying values to the BANK makes a
   `[PEERS]` swap visibly move data between slots (the flexibility test's
   whole point) and keeps a bank's history stable wherever it sits. Ranges
   are still per-metric-realistic and the Texas tiers land as specified
   (one ALERT-tier, one WATCH-tier illustrative bank).
2. **Watchlist has 8 columns** (spec lists 7): a `Rank` column between the
   flag counts and Status makes the (ALERT count, Texas) ordering
   sortable/auditable in-sheet, plus per-metric helper status columns J-X
   and a rank-score column Z feeding the COUNTIF/RANK formulas (labeled as
   helpers in the sheet).
3. **Texas-WATCH demo bank carries an NCLNLSR ALERT flag** (so 2 banks show
   bank-level ALERT status): arithmetic reality -- any bank with Texas >= 50
   under the seeded thresholds has noncurrents above the NCLNLSR alert
   band unless equity is thinner than the capital-ALERT floor. The TEXAS
   metric itself trips exactly one WATCH and one ALERT as specified.
4. **Bundle is 75.7 KB**, over the contract's soft ~60 KB target (the
   22-field raw landing, 15 metric formula builders and the peers machinery
   are the delta; macro shipped at 64.5 KB with the same note).
5. **Inactive slots render "OFF"** in the Watchlist Status column (spec
   silent); refusals/staleness wording follows the spec's entity form.

## The v1 median-includes-stale divergence (deliberate, spec test 6)

The dashboards' PEER MEDIAN rows are Excel `MEDIAN()` formulas over the
landed slot rows. Excel cannot see runtime staleness, so a STALE bank's
last-landed values still enter the WORKBOOK medians, while the runner's
DIGEST medians exclude stale banks (spec 0.6). Documented honestly in
`_readme` ("KNOWN v1 DIVERGENCE"), asserted in `test_stale_bank_flag`, and
labeled on the median row itself ("includes stale -- see _readme"). v1.1
candidate: blank stale slots' latest-quarter cells at land time.

## Data-quality traps carried (F1-F8)

F1 quarterly variants only (ROAQ/NTLNLSQR; YTD fields never fetched) |
F2 merged-bank stale REPDTEs (staleness guard + roster ACTIVE/ENDEFYMD) |
F3 JSON null != 0 (CBLR RBCRWAJ, BRO -- blank cells, None-propagating sums) |
F4 mixed units per record (units carried per field; $000 vs pct) |
F5 computed-ratio parity (Python == Excel, machine-verified 0 mismatches) |
F6 merger survivorship (>25% single-quarter ASSET jump noted in digest) |
F7 NCO Q4 seasonality (YoY note in the Asset-Quality subtitle) |
F8 regulatory vintages dated (CBLR 8% eff 7/1/2026; UBPR 8-band eff
2/26/2026; PCA 12 CFR 324.403) in `_readme` and the threshold authority
column.

## Open items

- **Live API not exercised from this environment** (api.fdic.gov is
  proxy-blocked here): the provider's parse/backoff/cache/guard paths are
  fixture-tested against the captured envelope, but the first live run --
  at the user's desk, keyless -- is the remaining validation, including the
  `--lookup` flow.
- **Unverified field ids** (Open Questions in the research): `ORE` (OREO),
  `INTAN`, tier-1 dollar level, insured/uninsured deposit estimates, AOCI,
  HTM fair value. The Texas VARIANT and CRE PROXY denominators stand until
  these are confirmed; uninsured share + unrealized-loss metrics are the
  v1.1 priorities.
- **Nine of twelve seeded CERTs are illustrative** (628/3511/639 verified);
  the `_config` comment tells the user to `--lookup` each before live use.
- **v1.1 candidates**: blank stale slots' latest quarter (kills the median
  divergence); surface STALE in the Watchlist Status column via a landed
  status cell; UBPR asset-band medians over all banks (needs the
  aggregation endpoint -- response shape unverified, out of v1).
- Excel-side CERT rendering treats a TEXT-typed cert cell as REFUSED
  (ISNUMBER gate) while the runner accepts digit strings; typing digits in
  a General-format cell yields a number, so this only surfaces on
  deliberately text-formatted cells.

## Dependencies

Runtime: `pandas`, `openpyxl` only. Test/verify-only: `pytest`, `oletools`,
`formulas`.
