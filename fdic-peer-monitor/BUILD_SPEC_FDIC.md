# BUILD SPEC — Bank Counterparty & Peer Monitor (v1)
### Reusable Excel workbook: CERT-keyed peer/counterparty bank monitoring for credit-risk review, FDIC BankFind provider

Grounded in `COVERAGE_RESEARCH_FDIC.md` (binding). Governed by
`TEMPLATE_CONTRACT.md`. Blueprints: `bureau-credit-risk-dashboard/`
(contract shapes) and `macro-early-warning-dashboard/` (staleness guard,
urllib provider, generated seed) — carry every review-pass fix from both.

**The inversion that defines this template:** rows are BANKS, not series
types. The user's hand-picked peer/counterparty list IS the watchlist,
keyed by FDIC CERT. **USER REQUIREMENT (binding):** the peer list must be
flexible — one `[PEERS]` row per bank; add/remove = edit a line + re-run,
no rebuild, within slot-provisioned headroom.

---

## Section 0 — Non-negotiable rules

0.1 **Watchlist hard gate (entity form).** Only rows carrying a genuine
entity join key are admitted: `entity_key` matching `^cert:[0-9]{1,7}$`.
Anything else (aggregates, name-only rows, unanticipated key forms) is
REFUSED with a series-named interpolated error. Default-deny.

0.2 **Stateless** (blank all blocks first; failed fetch = empty, never
stale).

0.3 **One provider (FDIC), isolated** behind the seam; plain `urllib`
REST; keyless (no secret handling needed in v1; `secret_env` stays wired
per contract for a hypothetical authenticated v2).

0.4 **Workbook is the source of truth** — including the `[PEERS]` list.

0.5 **Deterministic; no LLM.** All derived ratios are named pure functions
defined identically in Python and Excel.

0.6 **Staleness is first-class** (macro lesson, doubly relevant here:
merged-away banks return stale REPDTEs with no error). A bank whose latest
REPDTE is older than `stale_multiplier x 1 quarter` behind the peer-set
max is marked STALE, excluded from alert counts and medians, and surfaced
("possible merger/closure — check /institutions ACTIVE, /history").

0.7 **Two providers mandatory:** live `FdicProvider` + deterministic
offline `FdicDemoProvider` (all tests, `--demo`).

---

## Section 1 — Provider

- Endpoint: `https://api.fdic.gov/banks/financials` — **ONE bulk request
  per refresh**: `filters=CERT:(c1 OR c2 ...) AND REPDTE:[<oldest> TO *]`,
  `fields=<the ~30 verified fields>`, `sort_by=REPDTE&sort_order=DESC`,
  `limit=10000`, `format=json`. Guard: if `meta.total > limit`, error
  clearly (never silent truncation). Parse `data[i].data` (double wrap);
  JSON nulls -> None (never zero). Plus one `/institutions` roster call
  (`CERT,NAME,FED_RSSD,ACTIVE,BKCLASS,ENDEFYMD`) for identity + merger
  detection.
- Throttle 0.6s between calls; retry/backoff on 429/5xx; per-URL cache.
  Record `meta.index.createTimestamp` in the run status (data vintage).
- **`--lookup "<name>"` CLI flag (USER REQUIREMENT):** queries
  `/institutions?search=<name>&fields=NAME,CERT,CITY,STALP,ASSET,ACTIVE`
  and prints candidates + CERTs, so the user can populate `[PEERS]` from
  PowerShell. Live-only (clear message in demo/offline).

## Section 1a — Seam

`fetch_series(spec, secret=None) -> list[NormalizedRow]` unchanged;
`NormalizedRow.geo_segment` carries the ENTITY key (`cert:628`). The
provider fetches the bulk response once per run (cached), then slices per
series id.

---

## Section 2 — `_config`

Sections: `[SETTINGS]` (`demo_mode`, `raw_slots` default **16** quarters,
`http_min_interval` 0.6, `fdic_max_retries` 4, `stale_multiplier` 2.0,
`peer_slots` — the BUILT capacity, informational, `secret_env` blank),
`[THRESHOLDS]` (keyed by METRIC id, below), **`[PEERS]`** (new section:
`slot | cert | name | group | active` — one row per bank; `group` in
{peer, counterparty, self}; `active` TRUE/FALSE), `[SERIES]` = the METRIC
dictionary (19 columns per contract; one row per metric, bank-agnostic;
`geo_segment="entity"`, expanded at run time).

### The flexible-peers mechanism (USER REQUIREMENT, binding)

- Workbook is BUILT with `--peer-slots N` capacity (default **40**); the
  seed `[PEERS]` list fills ~12 slots, the rest are empty rows.
- The runner expands `active [PEERS] x [SERIES] metrics` into fetch/land
  units with ids `s{slot:02d}_{METRIC}`; raw-block anchors depend only on
  (slot, metric) — so editing WHICH bank occupies a slot changes no
  anchor. Bank identity (name/cert) flows into dashboards **by formula**
  from the `[PEERS]` cells, so a renamed slot re-labels everywhere on
  recalc.
- More active peers than built slots -> the runner REFUSES with "rebuild
  with --peer-slots M" (never truncation). Empty slots render blank
  (blank-guards).
- Removing a bank (active=FALSE or clearing the row) blanks its slot on
  the next run (stateless clearing).

### Metric dictionary (the `[SERIES]` rows; ~15 metrics, verified fields only)

| metric id | fields | derivation | units | dimension |
|---|---|---|---|---|
| NCLNLSR | NCLNLSR | direct | % | asset quality |
| NTLNLSQR | NTLNLSQR | direct (quarterly NCO) | % | asset quality |
| PD3089R | P3LNLS, LNLSGR | P3LNLS/LNLSGR*100 | % | asset quality |
| LNATRESR | LNATRESR | direct | % | asset quality |
| LNRESNCR | LNRESNCR | direct (coverage) | % | asset quality |
| TEXAS | NCLNLS, EQ, LNATRES | NCLNLS/(EQ+LNATRES)*100 — documented VARIANT (OREO/intangibles pending field verification) | % | composite |
| RBC1AAJ | RBC1AAJ | direct (Tier 1 leverage — universal, incl. CBLR) | % | capital |
| RBCRWAJ | RBCRWAJ | direct (null for CBLR electors — blank-tolerated) | % | capital |
| EQV | EQV | direct | % | capital |
| ROAQ | ROAQ | direct (quarterly, NOT YTD ROA) | % | earnings |
| NIMY | NIMY | direct | % | earnings |
| EEFFR | EEFFR | direct | % | earnings |
| LNDEPR | LNLSNET, DEP | LNLSNET/DEP*100 | % | funding |
| BRODEPR | BRO, DEP | BRO/DEP*100 | % | funding |
| CRECONR | LNRECONS, LNRENRES, LNREMULT, EQ, LNATRES | (sum)/(EQ+LNATRES)*100 — documented PROXY denominator (guidance uses total RBC; CBLR electors lack it) | % | concentration |

Derived metrics are computed by the runner as pure functions of the
fetched fields AND by Excel formulas off the landed field blocks —
identical definitions, tested for parity. Every underlying raw field
lands in `Raw_FDIC` (audit trail).

### `[THRESHOLDS]` (metric-keyed; authority labels in the help column)

TEXAS 50/100 above (Cassidy/StL Fed) · RBC1AAJ 8/5 below (CBLR floor
7/2026; PCA well-cap) · RBCRWAJ 12/10 below (PCA) · NCLNLSR 2/4 above
(heuristic vs QBP) · NTLNLSQR 1/2 above (heuristic; QBP 0.59% Q1'26) ·
PD3089R 1.5/3 above · LNRESNCR 100/60 below · LNATRESR 1.0/0.75 below ·
ROAQ 0.5/0 below · NIMY 2.5/2.0 below · EEFFR 70/85 above · LNDEPR 90/105
above · BRODEPR 10/25 above · CRECONR 250/300 above (2006 interagency
guidance at ALERT; WATCH approach-band). Every heuristic labeled
"heuristic"; every authority named. Regulatory vintages (CBLR 8% eff
7/1/2026; UBPR 8-band eff 2/26/2026) dated in `_readme`.

---

## Section 3 — Validator + staleness

Gates (default-deny, all required): (1) the expanded row's peer slot is
`active=TRUE`; (2) `source_class="A"` (this template's only admitted
class); (3) entity key matches `^cert:[0-9]{1,7}$` (built from the
`[PEERS]` cert cell; a malformed/blank cert is refused BY NAME, telling
the user to run `--lookup`). Build-time hard gate backs them. Refusal
message: entity form of 0.1 — only CERT-keyed institutions can be
monitored as counterparties; aggregates/name-only rows cannot.

Staleness per 0.6: per-bank latest REPDTE vs peer-set max REPDTE.

---

## Section 4 — Workbook structure

- `Dashboard_AssetQuality` — banks as rows; columns: noncurrent, NCO(q),
  PD30-89, ALLL/loans, coverage, Texas; per-cell status vs metric
  thresholds; **peer-median row** (Excel MEDIAN over slot rows — MEDIAN
  ignores blanks) + QBP Q1'26 static reference line in the subtitle.
- `Dashboard_Capital_Earnings` — leverage, total RBC (CBLR-blank
  tolerated), equity/assets, ROAQ, NIMY, efficiency; peer-median row.
- `Dashboard_Funding_Concentration` — loans/deposits, brokered %, CRE
  concentration (proxy denominator noted); peer-median row.
- `Watchlist` — the ranked peer list: Bank | CERT | Group | Texas | # of
  ALERT flags | # of WATCH flags | Status | (STALE surfaced via status
  line/digest). Ranked by (ALERT count, Texas) descending. Refused rows
  render their interpolated refusal.
- `Raw_FDIC` — per (slot x field) fixed-anchor blocks, newest-first,
  16 quarterly slots.
- `_config` (with `[PEERS]`), `_code_py`, `_code_vba`, `_readme` (metric
  definitions + authorities + regulatory vintages + the honest
  not-available list: CAMELS confidential, problem-bank names, Y-9C
  holding-company data, intraquarter).
- Column L status panel (+ `meta.index.createTimestamp` vintage line);
  no native charts; blank-guards everywhere; heat = red-is-stress with
  per-metric direction (below-is-bad metrics heat inverted — extend the
  bureau stress_heat to a direction-aware variant).

## Section 5 — Bootstrap + transmission

`ExtractFiles` macro (module `PeerMonitor`, STATUS_SHEET
`Dashboard_AssetQuality`); RUN.txt documents `--demo`, live (keyless — no
env var needed!), and `--lookup "<bank name>"`. `make_bundle.py` ->
**`build_fdic_monitor.py`** (pure ASCII) per contract §11.
`make_workbook.py --peer-slots N` build knob. requirements: pandas,
openpyxl.

## Section 6 — Phases + named tests (all headless, `--demo`)

1. `test_config_parse` — [PEERS] parses (slots, certs, groups, active);
   metric dictionary rows parse; expansion peers x metrics produces
   expected ids; >capacity refused with the rebuild message.
2. `test_demo_provider_deterministic`; `test_fdic_provider_parse_and_cache`
   — parse a FIXED captured-response fixture (double wrap, nulls->None,
   $000 vs % units, REPDTE ordering), bulk-call slicing per series, cache
   hit, `meta.total>limit` guard, 429/5xx backoff (stubbed, no network);
   `test_lookup_offline_message`.
3. `test_transforms_and_derived` — hardcoded expected values for every
   derived metric (PD3089R, TEXAS variant, LNDEPR, BRODEPR, CRECONR) incl.
   None-field tolerance (missing BRO -> blank not zero).
4. `test_reload_headless` — tabs exact, zero charts, VBA intact, headline
   formulas present for every metric column, MEDIAN rows present.
5. `test_watchlist_entity_gates` — POSITIVE: active peers admitted and
   ranked; NEGATIVE: blank cert refused by name (with --lookup hint);
   inactive slot excluded; defense-in-depth: fabricated non-"A" class row
   and malformed entity key both refused.
6. `test_stale_bank_flag` — a peer frozen 3 quarters behind the set max
   is STALE, excluded from alert counts AND from the Excel median (the
   runner blanks stale slots' latest-quarter cells… no — the median
   formula ignores blanks only if the cell is blank; therefore the runner
   must leave stale slots' data landed but the DIGEST excludes them and
   the Watchlist status shows STALE. The Excel median includes stale
   values — document this divergence honestly in `_readme` (v1) rather
   than hiding it.)
7. `test_peer_flexibility` — edit [PEERS] in a built workbook (swap a
   bank into a slot, deactivate another), re-run demo, assert the slot's
   raw block now carries the new id and the deactivated slot is blank —
   NO rebuild.
8. `test_raw_landing_idempotent`, `test_raw_layout_mismatch_refused`,
   `test_vba_protection_keys_roundtrip` (carried).
9. `email_sim.py` — extract from the .xlsm alone; email contains the
   ranked peer table (bank names + Texas + flag counts), per-dimension
   alert lines, staleness section, and the data-vintage line;
   deterministic at fixed `--asof`. Then the full contract §9 bar +
   bundle-in-empty-folder.

## Section 7 — Scope fence

**In:** the 15 verified metrics; flexible [PEERS] (40-slot default);
peer-median context; --lookup; failures/history awareness via the roster
call (ACTIVE/ENDEFYMD surfaced); ASCII bundle; Control Center compat.
**Out (v1):** uninsured-deposit share and unrealized-HTM/AOCI metrics
(fields UNVERIFIED — Open Q; the 2023-failure metrics are v1.1 priorities
once field ids are confirmed live); UBPR asset-band medians computed over
ALL banks (needs bulk/agg — v2); QBP XLSX ingestion; holding-company
(Y-9C) data; aggregation endpoints; CAMELS anything.

## Traps carried (F1-F8, additive)

F1 YTD-vs-quarterly field variants (use *Q/*QR) · F2 merged-bank stale
REPDTE (staleness guard + roster ACTIVE check) · F3 JSON null != 0 (esp.
CBLR risk-based ratios) · F4 mixed units per record ($000 vs %) · F5
computed-ratio parity (Python == Excel, tested) · F6 merger survivorship
(flag >25% single-quarter asset jumps in notes/digest) · F7 NCO Q4
seasonality (YoY context in subtitle) · F8 regulatory vintage dating
(CBLR 8%, UBPR 8-band).
