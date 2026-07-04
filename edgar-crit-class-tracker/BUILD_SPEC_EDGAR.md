# BUILD SPEC — EDGAR Criticized/Classified Tracker (v1)
### Excel workbook: commercial criticized/classified trends + 8-K credit events for publicly-traded competitor banks, SEC EDGAR provider

Grounded in `COVERAGE_RESEARCH_EDGAR.md` (binding). Governed by
`TEMPLATE_CONTRACT.md` (L1-L8, §12 provenance, §13 entity sets).
Blueprints: `fdic-peer-monitor/` (slot mechanism, entity watchlist,
--lookup) and `cfpb-mortgage-monitor/` (vintage/continuity styling). This
is the COMMERCIAL half of the two-track competitor surveillance design
(consumer = the FDIC pack's DQ track).

**What it answers:** "Whose commercial book is being risk-rated down —
before delinquency shows it?" Criticized/classified per competitor holding
company, quarterly, from their own filed 10-Q/10-K credit-quality tables,
plus an 8-K credit-event feed.

---

## Section 0 — Non-negotiables

0.1 **Watchlist gate (entity):** only `^cik:[0-9]{1,10}$` keys admitted
(default-deny; series-named interpolated refusals). The `[PEERS]` CIK list
IS the watchlist (§13: slots, `--peer-slots`, over-capacity refused,
`--lookup` name→CIK via company_tickers.json).
0.2 Stateless full-replace; amendments dedupe (cik, period, tag, dims) by
latest acceptanceDateTime.
0.3 One provider (EDGAR), isolated; plain urllib; keyless; **User-Agent
"{org} {email}" REQUIRED on every request** (from `_config` `edgar_user_agent`
setting — fail fast if blank in live mode; absent/generic UA = silent 403s).
Throttle >=0.15s/request (well under 10/s).
0.4 Workbook is source of truth — including `[PEERS]` and `[MEMBER_MAP]`.
0.5 Deterministic; no LLM. All aggregation is table-driven.
0.6 **Disclosure-dialect honesty:** each bank carries a `family` flag
(`grades_full` | `criticized_only` | `ig_nig` | `unmapped`). Metrics a
family cannot support render "N/A (disclosure family)" — never approximated.
New/unmapped members surface as "needs manual mapping" — never silently
guessed (§13 bootstrap).
0.7 Two providers: live `EdgarProvider` + deterministic `EdgarDemoProvider`.

## Section 1 — Provider (two-stage, per research)

- **Stage 1 — discovery:** `data.sec.gov/submissions/CIK{10d}.json`
  (COLUMNAR arrays; older history via `filings.files[]`). Select latest
  10-Q/10-K per calendar quarter (Q4 = the 10-K; dedupe /A amendments).
  Also harvest the 8-K event lane from the SAME response: `items` array
  filtered to {1.03, 2.04, 2.06, 4.02} (+2.02 informational) — zero extra
  requests.
- **Stage 2 — dimensional CQI:** fetch the filing directory `index.json`
  (`www.sec.gov/Archives/edgar/data/{cik}/{accession}/`), locate the
  EDGAR-generated extracted instance `*_htm.xml`, parse with stdlib XML:
  contexts (`xbrldi:explicitMember` pairs) + facts on
  `FinancingReceivableBeforeAllowanceForCreditLoss` (and the
  `ExcludingAccruedInterest` twin — per-bank preference order) dimensioned
  by `InternalCreditAssessmentAxis` x the class axis. **Ignore vintage
  line items entirely** (grade totals are single facts; summing vintages
  double-counts). Keep namespace-qualified member names (extensions!).
- **CIK padding:** 10-digit for data.sec.gov, UNPADDED in /Archives.
- companyfacts JSON = the consolidated fundamentals lane only (assets,
  loans, equity, NI — context columns). FSNDS bulk zips: out of v1
  (documented backfill path).
- Per-URL cache; retry/backoff; record accession + acceptance timestamp
  per fact (provenance §12). Connectivity self-test (`--selftest`): probes
  the three SEC hosts and prints allowlist guidance (corporate proxies
  block sec.gov — observed fact).

## Section 2 — `_config`

`[SETTINGS]`: demo_mode, raw_slots (default **12** quarters),
edgar_user_agent (""), http_min_interval (0.2), edgar_max_retries (4),
peer_slots, secret_env (""). `[THRESHOLDS]` by metric id. `[PEERS]`
(§13): `slot | cik | name | ticker | active` — 20 built slots default;
seed = the 10 research-verified banks: Fifth Third 35527, Regions 1281761,
Zions 109380, Comerica 28412, Huntington 49196, Truist 92230, KeyCorp
91576, M&T 36270, U.S. Bancorp 36104, BOK 875357 (families per research).
**`[MEMBER_MAP]`** (§13 bootstrap): `cik | family | member_qname | grade`
rows mapping each bank's observed members to canonical grades
{pass, special_mention, substandard, doubtful, loss, criticized_accruing,
criticized_nonaccruing, unmapped}; seeded for the 10 banks from the
research families; the runner appends newly-observed members with
grade="unmapped" and flags them. **`[CLASS_MAP]`**: coarse normalization
of each bank's class members to {ci, cre, construction, other_commercial}
— same bootstrap behavior.

## Section 3 — Metrics + gates

Canonical rollups per bank x quarter (commercial classes via [CLASS_MAP]):
- **criticized_ratio** (Tier 1, all families): (SM + substandard + doubtful
  + loss | native criticized rows) / total commercial amortized cost.
- **classified_ratio**, **sm_ratio** (Tier 2, grades_full only — flag-gated).
- **crit_qoq_delta**, **crit_yoy_delta** (pp) and criticized-$ growth.
- **class mix**: criticized$ share by {ci, cre, construction}.
- 8-K lane: per bank, count + latest date of {2.04 acceleration, 2.06
  impairment, 4.02 non-reliance, 1.03 receivership} filings, trailing 4
  quarters, with accession links.
Thresholds (heuristic, labeled): criticized_ratio watch 4 / alert 6 (%);
crit_qoq_delta watch +0.5 / alert +1.0 pp; sm_ratio watch 2 / alert 3;
any 2.04/4.02/1.03 8-K = automatic WATCH flag on the bank row.
Watchlist gates: slot active AND source_class="A" AND `^cik:[0-9]{1,10}$`;
build-time hard gate; malformed/blank cik refused BY NAME with --lookup
hint. Staleness (0.6 macro-lesson): a bank whose latest CQI quarter lags
the peer-set max by > stale_multiplier quarters is STALE (excluded from
alert counts; "check submissions — late filer or delisted?").

## Section 4 — Workbook

- `Dashboard_Criticized` — banks as rows: criticized_ratio, QoQ/YoY delta,
  sm_ratio + classified_ratio (N/A-gated), family flag, status; peer-median
  row (grades-capable subset labeled).
- `Dashboard_Mix_Events` — criticized-$ mix by class per bank; 8-K event
  lane (bank | item | date | accession link | one-line form type).
- `Watchlist` — ranked: Bank | CIK | Family | Criticized % | ΔQoQ | 8-K
  flags | Status. Refusals + STALE + unmapped-member notices rendered.
- `Raw_EDGAR` — fixed-anchor blocks per (slot x canonical metric),
  newest-first, 12 quarterly slots (+ a per-slot facts block carrying the
  member-level amounts that feed the rollups, for audit).
- `_provenance` (§12): metric → 10-Q note ("Credit Quality Indicators" /
  ASC 326-20-50-5) → tag/axis → per-fact accession; EDGAR viewer URL
  pattern `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=...`
  + per-filing `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/`
  links; the uniform interagency definitions (1938/1949/1979/2004
  agreement; SR 93-30) QUOTED with citations. `--tieout CIK [quarter]`
  prints value + tag + members + accession + viewer URL.
- `_config`, `_code_py`, `_code_vba`, `_readme` (two-track design context,
  family limitations table, application-timing caveat, Q4-via-10-K lag,
  HC-vs-CERT reconciliation note, proxy/allowlist note).
- Column L status (+ latest accession vintage); no charts; blank-guards;
  numeric thresholds; heat red = rising criticized.

## Section 5 — Bootstrap + transmission

Macro module `CritClassTracker` (STATUS_SHEET `Dashboard_Criticized`);
RUN.txt: demo, live (NEEDS edgar_user_agent set — explain; still keyless),
--lookup, --tieout, --selftest. `make_bundle.py` → **`build_edgar_tracker.py`**
(pure ASCII). requirements: pandas, openpyxl.

## Section 6 — Phases + named tests (headless, `--demo`; NO network in tests)

1. `test_config_parse` — [PEERS]/[MEMBER_MAP]/[CLASS_MAP] parse; slot
   expansion; over-capacity refused; 10 seed banks with families.
2. `test_demo_provider_deterministic`; `test_submissions_parse` (columnar
   fixture incl. items arrays + amendment dedupe + Q4-is-10-K selection);
   `test_instance_parse` (a FIXTURE extracted-instance XML with explicit
   dimensions: standard members AND one extension member AND vintage line
   items that MUST be ignored; quoted expected rollups); `test_backoff`.
3. `test_member_bootstrap` — unknown member → [MEMBER_MAP] append as
   unmapped + flagged, never guessed; family N/A gating works.
4. `test_metrics` — hardcoded criticized/classified/sm ratios + deltas from
   fixture facts; criticized_only bank computes Tier 1 but N/A Tier 2.
5. `test_reload_headless` — tabs exact (incl. _provenance), zero charts,
   VBA intact, numeric thresholds.
6. `test_watchlist_entity_gates` (+ defense-in-depth), `test_stale_bank`,
   `test_8k_event_lane` (items filter from fixture).
7. `test_provenance_and_tieout` — every metric has a provenance row;
   tieout output carries accession + viewer URL.
8. Carried: `test_raw_landing_idempotent`, `test_raw_layout_mismatch_refused`,
   `test_clear_actually_blanks` (L7), `test_vba_protection_keys_roundtrip`.
9. `email_sim.py` — ranked criticized table + family flags + 8-K events +
   staleness + unmapped-member section; deterministic. Then contract §9
   bar + bundle-in-empty-folder.

## Section 7 — Scope fence

**In:** the 10-bank seed (expandable via [PEERS]); Tier 1+2 metrics;
8-K event lane; member/class bootstrap; accession provenance + tieout.
**Out (v1):** MD&A full-text fallback for ig_nig banks (v1.1 — those banks
show family="ig_nig", criticized N/A); FSNDS bulk backfill; vintage-level
stress metrics; corporate (non-bank) counterparty fundamentals beyond the
context columns; any paid data; HC↔CERT automated reconciliation.

## Traps carried (E1-E10)

E1 convenience APIs are non-dimensional (instances only for CQI) · E2
accrued-interest twin tags (per-bank preference) · E3 vintage line-item
double-count (ignore vintages) · E4 extension members (bootstrap + drift
flag) · E5 class taxonomies differ (coarse map) · E6 no Q4 10-Q (10-K lag
60-90d; vintage columns re-label at fiscal roll) · E7 amendment dedupe ·
E8 CIK padding split · E9 uniform definitions / bank-specific application
timing (exam-cycle artifacts — note in _readme) · E10 corporate proxies may
block sec.gov (--selftest + allowlist note).
