# BUILD NOTES -- Bank Counterparty & Peer Monitor (v1; v1.1 pack section at
# the end)

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

---

# v1.1 -- Competitor Loan-Book Metric Pack (SPEC_COMPETITOR_PACK.md)

Upgrade of the shipped v1 (all v1 behaviors and tests preserved; extended,
not rewritten). Grounded in `RESEARCH_COMPETITOR_PACK.md` (93/93 fields
verified) + `PROVENANCE_MAP_FDIC.md`; contract sec 12 (provenance/tie-out)
lands WITH this pack. The workbook is REBUILT (raw anchors recomputed);
`pack_version 1.1` in [SETTINGS], and the runner refuses a foreign field
layout (the last-field label sentinel in `_check_slot`).

## What was added

- **Metric dictionary 15 -> 53** (38 pack metrics). Consumer track (cards /
  auto / other consumer / 1-4 family + a HELOC drill-in): 30-89 PD, 90+ PD
  (still accruing, disjoint from NA), nonaccrual, QUARTERLY NCO annualized
  x4 (the FDIC's own NTLNLSQR convention; YTD `NT{c}` never fetched -- F1).
  Commercial floor (construction / CRE-nonfarm / multifamily / C&I): the
  same four rates, honestly subtitled as the public Call-Report proxy
  (criticized/classified arrives via the EDGAR template). SVB pack on
  Dashboard_Funding_Concentration: `UNINSDEPR` = DEPUNINS/DEP (null ->
  BLANK + digest note, never 0), `UNRLZCAPR` =
  ((SCHA-SCHF)+(SCAA-SCAF))/(EQ+LNATRES) -- both legs COMPUTED; `EQCCOMPI`
  is a FLOW, deliberately unused -- and `FHLBASSR` = OTHBFHLB/ASSET.
- **Field-naming honesty rule.** Verified R ratio twins consumed directly
  ONLY where the twin name fits the legacy 8-char field limit (P3CRCDR,
  P3AUTOR, P3RERESR, P3RELOCR, P3CIR families = 15 direct twins); the
  9-char twins (P3CONOTHR, P3RECONSR, ...) are COMPUTED from the verified
  dollar triple + balance instead. Quarterly NCO names carry the VERIFIED
  8-char truncation (NTRECONQ, NTRENREQ, NTREMULQ, NTCONOTQ).
- **ONE bulk request, still.** `fields=` grew 24 -> 70 entries (68 raw
  fields + CERT,REPDTE), asserted < 250 at module load AND request build;
  `test_pack_fields_in_bulk_request` locks the list (and bans the YTD/
  un-truncated/EQCCOMPI names).
- **Dashboard_LoanBook**: one tab, TWO slot-anchored bands (consumer 19
  columns, commercial 16), each with per-column threshold band rules,
  direction-aware heat and a PEER MEDIAN row; band captions carry the
  two-track rationale and the spec's commercial honesty subtitle verbatim.
  Status panel in column X (the tab is wider than the L-column standard).
- **Declarative parity table.** `runner.PACK_RATIOS` (num, den, mult)
  drives BOTH the Python functions and the Excel formulas
  (`build_workbook.metric_formula`), so the two definitions cannot drift
  (F5); `UNRLZCAPR` is the one hand-written pair, parity-tested.
- **Thresholds**: all 38 pack metrics banded (numeric-typed, L8),
  direction `above`; the seven spec-named bands are labeled `SPEC pack
  band`, the rest `heuristic` (QBP-context) in the authority column.
- **_provenance tab** (contract sec 12): `provenance_seed.py` transcribes
  PROVENANCE_MAP_FDIC.md -- citations of record + facsimile/UBPR/BankFind
  URL patterns in the header, then field | schedule | line/caption | MDRM |
  flag | notes for all 69 field rows (68 landed + informational DEPINS) and
  28 derived-metric rows (direct metrics resolve to their field row).
  Honesty flags carried per row: MDRMs NOT in the map say "(not in tie-out
  map)" with [~] match-by-caption -- nothing invented.
- **--tieout CERT [REPDTE]** runner mode: reads the metric dictionary and
  the _provenance tab OUT OF THE WORKBOOK (source of truth), fetches the
  bank (demo or live), and prints per metric: value + schedule/line + MDRM
  + flag, headed by the CDR facsimile URL
  (`...ViewFacsimileDirect.aspx?ds=call&idType=fdiccert&id={CERT}&date=
  {MMDDYYYY}`), the BankFind page URL and the data vintage. Demo output is
  loudly labeled fiction; the provenance columns are the real map.
- **Demo provider** seeds per-class rates, balances, securities marks,
  DEPUNINS and FHLB per (cert): tier-0 cert 6548 trips the new ALERT bands
  (card NCOq 4.99, auto PD 4.57, resi NA 2.49, constr PD 3.53, CRE NA 2.60,
  C&I NCOq 1.35, uninsured 71.7, unrealized/capital 58.2, FHLB 22.9);
  tier-1 cert 6384 sits in the WATCH bands. Two new null shapes: cert 3510
  reports NO auto book (whole-series nulls) and cert 7213's DEPUNINS is
  null for the whole series (blank + note, never 0).
- **email_sim** gains the PER-CLASS LOAN-BOOK ALERTS section (consumer
  classes first, commercial after, via `runner.LOANBOOK_CLASS`) and asserts
  at least one consumer AND one commercial class alerting.

## Verification (v1.1)

- **20 tests green** = the 14 v1 tests (counts updated 15 -> 53 where the
  dictionary size is the thing under test) + the six pack tests:
  `test_pack_fields_in_bulk_request`, `test_consumer_track_rates`,
  `test_svb_derived_metrics` (incl. DEPUNINS=None -> blank NOT zero),
  `test_loanbook_tab` (both bands, medians, statuses, Watchlist wiring),
  `test_provenance_tab` (every metric/field has a row; facsimile URL
  pattern regex-verified; honesty flags spot-checked),
  `test_tieout_mode` (demo-labeled; value + MDRM per metric; URLs; REPDTE
  selection; malformed-CERT refusal).
- **email-sim PASS**: ranked table (12 rows) + per-dimension + PER-CLASS +
  staleness + vintage + self-contained. Demo digest at `--asof 2026-03-31`:
  12/12 banks, 2 ALERT / 7 WATCH / 0 STALE banks, 45 ALERT flags (only the
  two hash-assigned fiction banks are ALERT; watch count rose 5 -> 7 with
  the new bands).
- **`formulas` recalc parity -- 0 mismatches**: 455 values (all 35 LoanBook
  columns x 12 banks, both bands, + 35 medians + empty-slot blanks) AND 636
  statuses (53 Watchlist helpers x 12 banks) AND flag counts / Texas /
  bank-level statuses x 12 AND the LoanBook KPI tile, vs the Python digest
  at 1e-9.
- **Package**: olevba decompiles module `PeerMonitor`; tab order
  `...Funding_Concentration / Dashboard_LoanBook / Watchlist / Raw_FDIC /
  _config / _provenance / _code_py / _code_vba / _readme`; zero native
  charts, zero overlapping merges, zero dangling relationships (fallback
  .xlsx audited too). Workbook 176.0 KB.
- **Bundle**: regenerated `build_fdic_monitor.py` (105.4 KB pure ASCII,
  now embedding `provenance_seed`) executed in an EMPTY scratch folder ->
  demo-populated .xlsm + fallback .xlsx + runner.py + macro.bas +
  requirements.txt; olevba + OPC audits clean on the scratch outputs.
- **Control Center** still discovers the template with zero wiring.
- ASCII grep clean on every template file (keybank_style.py keeps its
  grandfathered docstring, never embedded).

## v1.1 deviations (recorded)

1. **All 38 pack metrics are thresholded**, not only the seven bands the
   spec names: the template invariant (every metric banded; Excel helper
   formulas compare against numeric cells -- a blank threshold cell would
   coerce to 0 and mis-flag) makes unbanded metrics unsafe. Extra bands are
   labeled `heuristic` in the authority column; spec bands labeled `SPEC`.
2. **HELOC (RELOC) gets 3 columns, no NCO**: the spec says "(+ HELOC RELOC
   column)"; the three verified PD/NA ratio twins are landed, but LNRELOC
   is not in the research doc's verified balance list, so a HELOC NCO rate
   cannot be built without inventing a denominator -- documented in-sheet.
3. **NCO rates are annualized x4** (the spec says "NT{c}Q over balances"
   without stating annualization): chosen to match the FDIC's own NTLNLSQR
   convention and the QBP norms the spec's card bands (2.5/4.0) reference.
4. **R-twin cutoff at 8 chars**: the research doc asserts twins exist per
   category but names none beyond the pattern; rather than guess truncated
   twin spellings, twins are consumed only where the name is unambiguous
   (<= 8 chars) and computed otherwise. First live run will confirm.
5. **Bundle is 105.4 KB**, over the contract's soft ~60 KB target (v1 was
   75.7 KB; the 46 new fields, 38 metric rows, LoanBook builder and the
   provenance transcription are the delta). Still one pure-ASCII file.
6. **Four RI-B category MDRMs carry [~]** (NTRERESQ/NTCONOTQ/NTRENREQ/
   NTREMULQ): PROVENANCE_MAP_FDIC.md section D does not capture those rows;
   the tab says "match by caption" instead of inventing codes.

## v1.1 open items

- Live API still not exercised from this environment (proxy-blocked): the
  46 new field names ride the same fixture-tested request path; first live
  run validates the R-twin spellings (deviation 4) and the [~] RI-B rows.
- The v1 median-includes-stale divergence stands (unchanged scope).
- UBPR percentile benchmarking remains out (FFIEC bulk-ZIP job if needed).
