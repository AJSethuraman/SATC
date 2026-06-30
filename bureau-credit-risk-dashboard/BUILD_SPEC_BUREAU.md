# BUILD SPEC — Consumer Credit-Risk Monitor (.xlsm Template, v1)
### Reusable Excel workbook for portfolio-level consumer credit-risk monitoring from a credit-bureau data source

**Status:** Buildable v1 against a free public stand-in (NY Fed Household Debt & Credit / HHDC), with a deterministic offline DemoProvider for all tests. Licensed feeds documented as v2 provider-adapter swaps.
**Modeled on:** FRED BUILD SPEC (section-for-section).
**Grounding rule:** Every factual claim about a product or source traces to a CONFIRMED finding in the VERIFIED RESEARCH. Refuted claims are never used. Unconfirmed items are flagged as UNKNOWN/OPEN QUESTION, never asserted.

---

## Section 0 — Non-negotiable rules

These are gates, not guidelines. A build that violates any of them is rejected.

**0.1 — THE WATCHLIST BOUNDARY IS A HARD GATE (centerpiece).**
The commercial **watchlist lane** exists in the workbook but is **GATED**. No series may populate it unless that series carries **a geographic key (MSA-level or finer) OR a segment/account key that a real loan portfolio can join on**, AND that series is sourced from a **licensed Class C adapter** (not the free/public source class). The v1 public stand-in (HHDC) carries **neither a portfolio-joinable account key nor a usable fine-grained geographic key**: HHDC state data is **annual (Q4) only**, with quarterly all-state granularity **withheld by Equifax contract**, and it is **not account-joinable** (it is an anonymized 5% sample). The Philly Fed CCE geographic-join claim was **REFUTED** and must never be used as a watchlist key.

Therefore the **watchlist validator MUST REFUSE** to populate the watchlist lane from any public / national / annual-aggregate series, and must surface a clear, series-named error built by **interpolating the real `id` and `geo_segment` from the offending `_config` row at runtime** (never a hardcoded string), e.g. for the seeded row `hhdc_card_90plus`:

> `WATCHLIST REFUSED: series "hhdc_card_90plus" has geo_segment="national", watchlist_capable=FALSE, source_class="A". The watchlist lane requires a licensed (Class C) MSA feed (TransUnion Prama Benchmarking) or an account-level feed (Experian Risk & Retention Triggers / TransUnion TruVision). No public/national/annual-aggregate series may feed this lane.`

This is the stricter analog of the FRED never-plug rule. The refusal is **structural** (driven by `watchlist_capable` + `source_class` in `_config`), not advisory.

**0.2 — Stateless clean rebuild every refresh.** Each refresh re-fetches source data and rebuilds all derived tabs from scratch. No incremental state, no hidden accumulation. The workbook is reproducible from `_config` + source data alone **for a fixed snapshot** (and byte-for-byte deterministic only in DemoProvider mode against a fixed `--asof`; the live HHDC source revises — see 0.7 and the buildability notes).

**0.3 — One provider per template; adapter isolated behind a stated interface contract.** A single provider drives one workbook instance. The provider adapter is an isolated module (one clean seam) so swapping the DemoProvider/HHDC adapter → a licensed feed is a module swap, not a rewrite. The seam is enforced by an **explicit interface contract** (Section 1a): every adapter implements `fetch_series(config_row, secret) -> list[NormalizedRow]` with a fixed normalized schema; the runner, transforms, and validator consume **only** that normalized schema and never call provider-specific code.

**0.4 — The workbook is the source of truth.** All Python, VBA, config, and README live in plain-text tabs (`_code_py`, `_code_vba`, `_config`, `_readme`). Nothing load-bearing lives outside the workbook.

**0.5 — Determinism; no AI/LLM in the data path.** Transforms are named, deterministic functions. No model inference, no nondeterministic enrichment, anywhere between source and output.

**0.6 — Output is Excel.** The deliverable is an `.xlsm` workbook. No external dashboard, no BI server.

**0.7 — Two providers: a deterministic DemoProvider and a live HHDC provider.** Mirroring the FRED reference, the template ships **two** providers behind the same seam: a deterministic offline **HhdcDemoProvider** (seeded pseudo-walk per `id`, fixed `--asof`, NO network, NO key) selected by `--demo` / `demo_mode=TRUE`, and a live **HhdcProvider** (plain-HTTP download of published HHDC tables). **All per-phase tests and the email-simulate acceptance test run in `--demo` mode** and are deterministic/offline. The live HHDC provider is exercised separately and is **not** claimed reproducible byte-for-byte (HHDC figures are point-in-time and revise).

---

## Section 1 — Provider classification + key/secret handling

Providers are classified into two classes the template must distinguish. (We use class labels **A** and **C** to mirror the FRED taxonomy; class B — keyed-but-free public APIs — is intentionally absent here.) Each `_config` row also carries an explicit `source_class` tag (A or C) used by the watchlist gate.

### Class A — Free public tables (downloadable, no key)
- **No authentication, no contract, no key.** Plain HTTP download of published tables.
- **v1 stand-in:** **NY Fed Household Debt & Credit (HHDC)** public downloadable tables. Built on the NY Fed Consumer Credit Panel (CCP): an anonymized, nationally representative **5% (one-in-20) random sample** of individuals with an SSN + credit report (usually 19+), **sourced from Equifax**. Supports **national and regional (state-level) aggregate** balances and delinquencies by product type; **NOT account-joinable**. **State data is annual (Q4) only** for all 50 states + PR; **quarterly all-state granularity is withheld by Equifax contract**. Microdata is restricted to Fed researchers. Coverage **through 2026Q1**. *(Source: newyorkfed.org/microeconomics/faq.)*
- **Fetch-granularity note:** HHDC is a **bulk published-table** source (workbook/PDF of aggregate tables), **not a per-series API** — unlike FRED, there is no `get_series(id)` endpoint. The literal column schema is UNKNOWN (Open Question #5); the adapter must be written **defensively** against the actual published columns, and each `_config` row must carry a per-id source-locator (see Section 1a).
- **Related free reference surfaces (read-only, NOT watchlist sources):**
  - **Philadelphia Fed Consumer Credit Explorer (CCE):** same CCP/Equifax 5% sample; credit use, average debt, delinquency by product (auto/student/mortgage/cards), segmentable by age, credit score, neighborhood income, race/ethnicity; **Equifax Risk Score 280–850 (prime ≥660)**. Public tool. **NOTE: the claim that CCE offers a census-tract/ZIP/county/MSA geographic join key is REFUTED — do not use CCE as a watchlist geographic key.** *(Source: philadelphiafed.org consumer-credit-explorer.)*
  - **TransUnion CIIR (free portion):** only press-release **trend summaries** are free; the full dataset requires a Prama license. National, aggregate, **no joinable key**. Use only for metric *shape* seeding and as a published-figure reference. *(Source: newsroom.transunion.com/q1-2026-ciir.)*
  - **Equifax Market Pulse:** monthly U.S. national consumer-credit trend reports (originations, balances, delinquencies across mortgage, auto loans/leases, student, bankcard, private-label, personal); full charts gated behind emailing RiskAdvisors@Equifax.com (free contact gate, not open download). *(Source: equifax.com/business/trends-insights/marketpulse.)* *(Whether Market Pulse offers a state/MSA cut is UNRESOLVED — do not assert either way.)*

### Class C — Licensed feed (the v2 swap targets)
Accessed under contract.

**Confirmed auth pattern:**
- **OAuth 2.0 client_credentials grant** — the **Equifax Developer Portal** pattern: obtain an access token from `client_id` + `client_secret` + `scope`; requests without a valid token return **HTTP 401**. *(Source: developer.equifax.com/documentation.)* **This is the only CONFIRMED Class C auth pattern** and is the reference auth model for the licensed provider adapter.
- **Secure batch / file-transfer mechanics (including whether SFTP is used) are UNKNOWN** at spec time (Open Question #2) and must be confirmed per contract; **do not assume SFTP**.

**Compliance basis (scoped to what research supports; broader gating is a design assumption, not a confirmed fact):**
- **Account-level** licensed feeds (Experian Risk & Retention Triggers, TransUnion TruVision Credit Risk) are documented as operating under **FCRA permissible purpose = "account review"** (monitoring an **existing** portfolio, not prospecting) per the research.
- For **depersonalized/aggregate** feeds (TransUnion Prama Benchmarking), whether/how FCRA permissible purpose applies is **NOT established by the research (UNKNOWN, Open Question #1)**.
- The exact attestation/enforcement mechanics for any feed are **UNKNOWN (Open Question #1)**. The template does **not** assert a single blanket FCRA gate across all Class C; it treats broader gating as a design assumption to confirm at contract time.
- Licensed bureau contracts are **EXPECTED** to restrict redistribution, but the specific data-use/redistribution terms are **UNKNOWN at spec time (Open Question #2)** and must be confirmed per contract; the v2 adapter must be **designed to enforce whatever redistribution restriction the contract specifies**, while the spec does not assert the term as a confirmed fact.

**Watchlist-capable licensed targets (documented, not built in v1):**
- **TransUnion Prama Benchmarking** (LICENSED): on-demand depersonalized national credit file, **60 months account history updated monthly**, viewable at **MSA level**, 4 segments (auto/card/mortgage/personal), segmentable by **risk band (subprime/prime), geography, and vintage**. **This is the one confirmed product carrying an MSA geographic key + segment key → watchlist-capable** for an MSA watchlist. *(Source: transunion.com/product/prama-benchmarking.)*
- **Experian Risk and Retention Triggers** (LICENSED, account-level, FCRA account review): daily alerts within minutes of a triggering event — new trades, increasing utilization/over-limit, new collections, charge-offs, closed accounts, new delinquency 30–180 DPD, short-term high-risk financing activity, bankruptcy/deceased. *(Source: experian.com/business/products/risk-and-retention-triggers.)*
- **TransUnion TruVision Credit Risk** (LICENSED, account-level, FCRA account review): an account-review process + event-based monitoring of an existing portfolio (identify/segment/prioritize accounts). *(Source: transunion.com/solution/truvision.)*

> **Equifax account-level swap target — UNCONFIRMED.** No specific Equifax account-level portfolio-review **product** is confirmed in the research. Only the Equifax OAuth 2.0 client_credentials auth pattern (developer.equifax.com) is confirmed. Any Equifax account-level swap target, its account-level capability, and its FCRA basis are **UNKNOWN (Open Question #7)**. Do not claim such a product is account-level or watchlist-capable.

**Supplementary licensed analytics (not watchlist sources, documented for completeness):**
- **Experian Ascend Analytical Sandbox** (LICENSED): hosted hybrid-cloud; ~18–20 yrs monthly snapshots of de-identified full-file data (~245M reach / 220M+ full-file) + commercial/property/auto/alt; SAS/R/Python/H2O/Hue/Tableau; combine own data. **Not an open API.** *(Source: experian.com/business/products/ascend-analytical-sandbox.)*
- **TransUnion Prama Vintage Analysis** (LICENSED): 200M+ consumers, **seven years** cohort/vintage performance. *(Source: transunion.com/product/prama-vintage-analysis.)* **NOTE: the claim that Prama Vintage Analysis delivers delinquency by tier/geography/LOB/product over nine quarters is REFUTED — do not assert it.**

### Key / secret handling (all classes)
- Class A needs no secret. The base URL / table path lives in a **config cell** in `_config`.
- Class C secrets (`client_id`, `client_secret`, scope) are read **from environment variables**, with the env-var **name** recorded in a `_config` cell. **Secrets are never hardcoded** in any tab, never written to disk by the bootstrap, and never echoed into output tabs or logs.
- The runner reads the secret at runtime via `os.environ[...]`; if the named env var is absent, the runner fails fast with a clear message and does **not** proceed.

---

## Section 1a — The adapter seam interface contract (explicit boundary)

The provider adapter is the primary clean seam (L6). Its boundary is a **stated contract**, not an aspiration:

- **Interface:** `fetch_series(config_row, secret=None) -> list[NormalizedRow]`.
- **Normalized schema (fixed for all providers):** `NormalizedRow = {id, period, value, geo_segment, source_class}` (plus optional `units` carried from config). Every adapter — `HhdcDemoProvider`, live `HhdcProvider`, and any Class C licensed adapter — returns rows in exactly this schema.
- **Consumption rule:** the runner, transform registry, threshold engine, and watchlist validator consume **only** the normalized schema. They never call provider-specific auth, pagination, or column code. Provider-specific concerns (OAuth token acquisition, table-locator parsing, retry/backoff, last-observation derivation) live **inside** the adapter module.
- **Result:** a Class C swap is a **provable single-module + credential change** — replace the adapter module and supply the env-var secret; transforms and the validator are untouched.

**Seam-contract requirements that BIND every adapter (esp. the licensed v2 adapter):**
- **L5 throttle/backoff + last-observation-date derivation** are mandatory in the adapter seam contract so the licensed swap inherits them (rate limits are real for licensed APIs). For the Class A HHDC stand-in this manifests as **conditional-fetch / idempotency** (avoid redundant re-download by deriving the last-observation date from already-fetched data) — **not** an assertion that the static HHDC table download is rate-limited (no HHDC rate limit is established by research).
- **Per-id source-locator:** because HHDC is a bulk table and its literal schema is UNKNOWN (Open Q#5), each `_config` row carries source-locator fields (`source_url`, `table_id`, `sheet`, `series_label`) so `fetch_series` deterministically maps each `id` to a cell range in a downloaded table. The `HhdcDemoProvider` satisfies the same `id` contract **offline** (deterministic synthetic series per `id`) so Phase 2's test passes without the real schema.

---

## Section 2 — The `_config` dictionary that drives everything

`_config` is a flat table; each row is one series. The template reads only this tab to decide what to fetch, transform, threshold, and route. Columns:

`id | title | category | lane | metric_type | frequency | sa_nsa | units | level_rate_index | geo_segment | source_class | dashboard_capable | watchlist_capable | source_url | table_id | sheet | series_label | transform | notes`

**Lane routing rule:** `lane="dashboard"` → presentation Dashboard tabs. `lane="watchlist"` → watchlist tab **only if** `watchlist_capable=TRUE` **AND** `source_class="C"` **AND** `geo_segment` is in the allowed join-key whitelist (Section 3). For the v1 public stand-in, **every seeded row is `source_class="A"`, `dashboard_capable=TRUE`, and `watchlist_capable=FALSE`** — so the watchlist validator (Section 3) refuses to populate the watchlist lane, by design (0.1).

### Seed rows (public HHDC + CIIR-style metric shapes)
Metric shapes by product segment: **mortgage, HELOC, auto, credit card / bankcard, student, personal / unsecured**. Metric types: **balances, delinquency rates/flows by DPD bucket, originations**. (Source-locator columns omitted from the display table below for width; every row carries them per Section 1a.)

| id | title | category | lane | metric_type | frequency | sa_nsa | units | level_rate_index | geo_segment | source_class | dashboard_capable | watchlist_capable | transform | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hhdc_total_balance | Total household debt balance | aggregate | dashboard | balance | quarterly | NSA | USD_tn | level | national | A | TRUE | FALSE | yoy_pct | 5% sample, not census |
| hhdc_mortgage_balance | Mortgage balance | mortgage | dashboard | balance | quarterly | NSA | USD_tn | level | national | A | TRUE | FALSE | yoy_pct |  |
| hhdc_heloc_balance | HELOC balance | heloc | dashboard | balance | quarterly | NSA | USD_bn | level | national | A | TRUE | FALSE | yoy_pct |  |
| hhdc_auto_balance | Auto loan balance | auto | dashboard | balance | quarterly | NSA | USD_tn | level | national | A | TRUE | FALSE | yoy_pct |  |
| hhdc_card_balance | Credit card balance | card | dashboard | balance | quarterly | NSA | USD_tn | level | national | A | TRUE | FALSE | yoy_pct | CIIR Q1'26 ref: bankcard $1.12tn (+4.6% YoY) |
| hhdc_student_balance | Student loan balance | student | dashboard | balance | quarterly | NSA | USD_tn | level | national | A | TRUE | FALSE | yoy_pct |  |
| hhdc_personal_balance | Personal/unsecured balance | personal | dashboard | balance | quarterly | NSA | USD_bn | level | national | A | TRUE | FALSE | yoy_pct |  |
| hhdc_card_90plus | Credit card 90+ DPD rate | card | dashboard | delinq_rate | quarterly | NSA | pct | rate | national | A | TRUE | FALSE | level | CIIR Q1'26 ref: bankcard 90+ DPD 2.53% (+10bps YoY) |
| hhdc_auto_90plus | Auto 90+ DPD rate | auto | dashboard | delinq_rate | quarterly | NSA | pct | rate | national | A | TRUE | FALSE | level |  |
| hhdc_mortgage_90plus | Mortgage 90+ DPD rate | mortgage | dashboard | delinq_rate | quarterly | NSA | pct | rate | national | A | TRUE | FALSE | level |  |
| hhdc_flow_to_30 | Flow into 30+ DPD (all products) | aggregate | dashboard | delinq_flow | quarterly | NSA | pct | rate | national | A | TRUE | FALSE | level | transition flow |
| hhdc_flow_to_90 | Flow into 90+ DPD (all products) | aggregate | dashboard | delinq_flow | quarterly | NSA | pct | rate | national | A | TRUE | FALSE | level | transition flow |
| hhdc_card_orig | Bankcard originations | card | dashboard | origination | quarterly | NSA | count_m | level | national | A | TRUE | FALSE | yoy_pct | one-quarter lag; CIIR ref 21.9M (+13% YoY, Q4'25) |
| hhdc_personal_orig | Personal-loan originations | personal | dashboard | origination | quarterly | NSA | count_m | level | national | A | TRUE | FALSE | yoy_pct | CIIR ref record 7.6M (+21.7%) |
| hhdc_auto_orig | Auto originations | auto | dashboard | origination | quarterly | NSA | count_m | level | national | A | TRUE | FALSE | yoy_pct | one-quarter lag |
| hhdc_mortgage_orig | Mortgage originations | mortgage | dashboard | origination | quarterly | NSA | USD_bn | level | national | A | TRUE | FALSE | yoy_pct | one-quarter lag |
| hhdc_state_balance_annual | State total balance (annual Q4) | aggregate | dashboard | balance | annual | NSA | USD_bn | level | state_annual | A | TRUE | FALSE | yoy_pct | annual Q4 only; NOT a watchlist geo key — quarterly all-state withheld by Equifax contract |
| WATCHLIST_MSA_PLACEHOLDER | MSA watchlist (LICENSED req'd) | aggregate | watchlist | delinq_rate | monthly | NSA | pct | rate | msa | A | FALSE | FALSE | level | GATED: requires Class C Prama MSA feed; refused under public stand-in (source_class=A) |

> The `hhdc_state_balance_annual` row is deliberately seeded `watchlist_capable=FALSE` even though it has a `state_annual` geo tag: state data is **annual Q4 only** and **quarterly all-state is withheld by Equifax contract**, so it is **not a usable fine-grained watchlist key**. The `WATCHLIST_MSA_PLACEHOLDER` row documents the lane's existence and its licensed requirement; it is seeded `source_class=A` and stays unpopulated under the public stand-in. **Even if an implementer flips `watchlist_capable=TRUE`, the `source_class=A` gate (Section 3) still refuses it** — defense in depth that cannot be defeated by editing a single capability flag.

### Score-scale normalization (honest note, carried in `_config.notes` and `_readme`)
Risk scores **differ by scale and must be normalized** before any cross-source comparison:
- **Equifax Risk Score: 280–850, prime ≥660** (the scale used by the CCP-based public surfaces).
- **VantageScore** and **FICO** use different ranges/cutoffs.
A series tagged with one score scale must **not** be compared to another without an explicit normalization step. v1 does not invent a crosswalk; it records the scale per series and **refuses silent cross-scale comparison**. (Exact normalization mapping across scales is out of v1 scope.)

---

## Section 3 — Deterministic named transform registry + threshold engine

### Transform registry (named, deterministic, no LLM)
Each `_config.transform` value names exactly one function:
- `level` — pass-through of the raw value.
- `yoy_pct` — year-over-year percent change (for quarterly series, value vs. same quarter prior year; for annual, vs. prior year).
- `qoq_pct` / `mom_pct` — period-over-period percent change (quarter-over-quarter for quarterly; month-over-month for monthly licensed feeds).
- `zscore_8q` — rolling 8-quarter z-score (standardize a series against its own recent 2-year window).
- `index_to_pct` — convert an indexed series to percent terms relative to its base.

All transforms are pure functions of the fetched series; identical input → identical output (0.5).

### Config-driven threshold engine
Thresholds live in `_config` (or a threshold sub-table keyed by `id`), not in code. The engine flags a series when its transformed value crosses a configured bound (e.g., 90+ DPD rate above an absolute level; YoY balance growth above a band; a `zscore_8q` beyond ±k). Output is a per-series status (`OK` / `WATCH` / `ALERT`) consumed by the Dashboard tabs and the email-simulate step. Thresholds are data, not code, so retuning never touches `_code_py`.

### Watchlist validator (the gate from 0.1) — DEFAULT-DENY WHITELIST
Before anything is written to the watchlist tab, the validator iterates `_config` rows where `lane="watchlist"` and applies a **default-deny whitelist** (not a blacklist):

1. **REFUSE** unless `watchlist_capable=TRUE`. → emit the series-named error (0.1), interpolating the real `id`/`geo_segment`/`source_class`. **Never** silently coerce.
2. **REFUSE** unless `source_class="C"` (licensed adapter). Any `lane="watchlist"` row with `source_class="A"` is refused **regardless of its geo tag** — so a public row cannot be promoted into the lane by flipping a single flag.
3. **REFUSE** unless `geo_segment` is in the explicit allowed join-key set **{`msa`, `account`, finer}**. Any other value (`national`, `state_annual`, `region`, `census_division`, or any unanticipated/aggregate tag) is refused by default-deny — no open-ended "any aggregate" catch-all to read narrowly.
4. Populate **only** rows that pass all three gates (i.e., a true MSA/segment/account join key from a licensed v2 feed).

Under the v1 public stand-in, gate 2 (`source_class="A"`) always refuses — which is the correct, designed behavior, and it holds even if gate 1's flag is edited.

---

## Section 4 — Workbook structure

**Presentation tabs:**
- `Dashboard_Balances` — balances by product, with `yoy_pct` and threshold status.
- `Dashboard_Delinquency` — delinquency rates and **flows by DPD bucket** by product.
- `Dashboard_Originations` — originations by product (with the **one-quarter origination lag** annotated).
- `Watchlist` — the gated lane. Under the public stand-in this tab shows the **refusal message** and the licensed-feed requirement, not data.
- `Raw_HHDC` — raw fetched HHDC tables (or DemoProvider output in `--demo` mode), unmodified, as the audit trail.

**System tabs (plain text):**
- `_config` — the Section 2 dictionary + thresholds (source of truth).
- `_code_py` — the full `runner.py` as flat text.
- `_code_vba` — the `ExtractFiles` macro as flat text.
- `_readme` — provider notes, score-scale normalization note, compliance summary (with UNKNOWN banner), run instructions.

**Rendering rules (carry L4):** No native openpyxl charts. Use **formula-driven cells + conditional-format heat**, and optional **macro-painted sparklines** only. All embedded code in tabs is **flat ASCII text** (L3).

---

## Section 5 — One-click bootstrap (EXTRACT-ONLY)

The bootstrap macro is **extract-only** (L1). The `ExtractFiles` VBA macro, when run from the open workbook, writes **only** three files next to the workbook:
- `runner.py`
- `requirements.txt`
- `RUN.txt` (instructions)

It does **not** run Python, does **not** shell out, does **not** call `.Save`, and does **not** depend on xlwings. The user then runs `runner.py` from PowerShell **against the CLOSED workbook**, using the **openpyxl** backend. Tests and the email-simulate acceptance run default to `--demo` mode (deterministic, offline); the live HHDC download is an explicit non-demo run.

Backend rules:
- openpyxl loads with **`keep_vba=True` ONLY for `.xlsm`** (L2). On a plain `.xlsx`, `keep_vba=True` injects a dangling vbaProject relationship Excel rejects as "file format or extension is not valid" — never do it.
- The extractor writes files as **UTF-8**; all embedded code is **pure ASCII** (L3) so extraction can never produce a `SyntaxError` from ANSI-written non-ASCII bytes.

---

## Section 6 — Ordered build phases (each ends in a concrete, headless test; final test is email-simulate)

All phase tests run on **Linux/CI with no Excel and no network**, in `--demo` mode, via a pytest suite (`tests/test_runner.py`-style) plus an `email_sim.py`-style acceptance script. Named test artifacts and assertions below mirror the FRED reference harness.

**Phase 1 — Skeleton + `_config` seed.**
Build all tabs; seed `_config` (Section 2). *Test (`test_config_parse`):* every `_config` row parses; lane/capability/`source_class`/source-locator columns load; assert no row has `lane="watchlist"` with (`watchlist_capable=TRUE` AND `source_class="C"`) under the public stand-in.

**Phase 2 — Provider adapters (HhdcDemoProvider + live HhdcProvider, Class A).**
Implement `HhdcDemoProvider` (deterministic seeded pseudo-walk per `id`, fixed `--asof`, no network/key) and the live `HhdcProvider` (public table download mapped per-id via source-locator; conditional-fetch using last-observation date derived from fetched data, with retry/backoff inside the adapter). *Test (`test_demo_provider_deterministic`):* `Raw_HHDC` populates from a closed-workbook `--demo` run; the DemoProvider yields identical output across runs at a fixed `--asof` (idempotent, 0.2). **Live-source idempotence is scoped to a fixed upstream snapshot** and tested only by mocking/caching the downloaded bytes — never by re-hitting the network (HHDC revises; coverage "through 2026Q1").

**Phase 3 — Transform registry + thresholds.**
Wire the named transforms and the config-driven threshold engine. *Test (`test_transforms`):* `yoy_pct`/`level`/`zscore_8q` outputs match **hardcoded expected values** on a fixed fixture series; thresholds produce expected `OK/WATCH/ALERT` on fixture inputs.

**Phase 4 — Dashboard rendering.**
Populate `Dashboard_Balances`, `Dashboard_Delinquency`, `Dashboard_Originations` with formula cells + conditional-format heat (no native charts, L4). *Test (`test_reload_headless`, headless proxy for Excel):* openpyxl reloads the written `.xlsm` with `keep_vba=True` successfully; assert expected cells are present and **no native chart objects exist** (the top "unreadable content / recovered" trigger). Excel is not required in CI.

**Phase 5 — Watchlist gate.**
Run the watchlist validator. *Test (`test_watchlist_refusal`):* `Watchlist` tab shows the **series-named refusal message** (interpolated real `id`/`geo_segment`/`source_class`) and licensed-feed requirement; **no public/national/annual series leaks into the lane** (0.1). *Negative test (`test_watchlist_gate_defense_in_depth`):* flipping the `WATCHLIST_MSA_PLACEHOLDER` row to `watchlist_capable=TRUE` is **still refused by the `source_class="A"` gate**; flipping a `national` public row to `watchlist_capable=TRUE` is refused by both the `source_class` and the geo-whitelist gates.

**Phase 6 — Provider-adapter swap rehearsal (dry, fully stubbed).**
Confirm the adapter seam isolates the provider using a **pure in-process stub/mock** of the Class C OAuth `client_credentials` flow (Equifax pattern). **No live request to any Equifax (or other licensed) endpoint is made — live Class C calls are forbidden in v1 tests (no contract/credentials exist).** *Test (`test_class_c_stub`):* (a) the runner raises a clear **fail-fast** error when the named env var is absent; (b) the stubbed adapter returns the normalized schema (Section 1a) so transforms/validator are untouched; (c) the swap touches only the provider module. The stub asserts the **HTTP 401 / missing-token** code path without a live token request.

**Phase 7 — Email-simulate acceptance test (final, `--demo`).**
Run the full pipeline end-to-end against the closed workbook in `--demo` mode (fixed `--asof`); generate the alert digest (threshold `ALERT`/`WATCH` rows + the watchlist refusal notice) and **simulate the monitoring email** (compose to console/file, no send). *Acceptance (`email_sim.py`):* the simulated email contains the dashboard alert summary AND the explicit watchlist-gated message naming the licensed-feed requirement; the run is **deterministic and reproducible from `_config` + the DemoProvider alone** (the live HHDC provider is exercised separately and is not claimed byte-for-byte reproducible).

---

## Section 7 — Scope fence (explicit)

**In scope (v1):** Class A public HHDC ingestion (live `HhdcProvider`) plus a deterministic offline `HhdcDemoProvider`; dashboard lanes (balances, delinquency rates/flows by DPD bucket, originations) by product segment; deterministic transforms + config-driven thresholds; the **gated** watchlist lane with structural default-deny refusal; the adapter seam interface contract; extract-only bootstrap; email-simulate (`--demo`).

**Out of scope (v1):**
- Any live licensed feed (Prama / Triggers / TruVision / Ascend, and any Equifax account-level target) — documented as v2 swap only; any live Class C call is forbidden in v1.
- Populating the watchlist with real data (requires a licensed MSA or account-level feed).
- Cross-score-scale normalization crosswalk (Equifax 280–850 ↔ VantageScore ↔ FICO) — record-and-refuse only.
- Account-level joins (the public stand-in is **not account-joinable**).
- Any in-Excel Python execution, xlwings, native charts, or hardcoded secrets.
- Redistribution of any licensed data (the v2 adapter must enforce whatever the contract specifies; terms UNKNOWN at spec time).

---

## Compliance

> **NOTE — design intent, not verified contract facts.** The operational mechanics of every item below (FCRA permissible-purpose attestation/enforcement, redistribution terms, retention limits, secure transfer) are **NOT confirmed by research** and are tracked as **UNKNOWN in Open Questions #1–#2**. This section states design intent and scopes confirmed labels narrowly; it does not assert any contract term as fact.

- **FCRA permissible purpose (scoped).** The research ties **FCRA permissible purpose = "account review"** specifically to the **account-level** products **Experian Risk & Retention Triggers** and **TransUnion TruVision Credit Risk** — monitoring **accounts already in the portfolio**, not prospecting. For **depersonalized/aggregate** feeds (**Prama Benchmarking**), whether/how FCRA permissible purpose applies is **NOT established (UNKNOWN, Open Question #1)**. The template does **not** assert a single blanket FCRA gate across all Class C; broader gating is a design assumption to confirm at contract time. Exact attestation/enforcement mechanics are **UNKNOWN (Open Question #1)**.
- **Redistribution.** Licensed bureau contracts are **EXPECTED** to restrict redistribution, but the specific data-use/redistribution terms are **UNKNOWN at spec time (Open Question #2)** and must be confirmed per contract. The v2 adapter must be **designed to enforce whatever redistribution restriction the contract specifies**; v1 (public HHDC only) does not touch licensed data. The spec does not assert any redistribution term as a confirmed fact.
- **Data governance.** Secrets via env var + `_config` cell only; never hardcoded, never written to disk by bootstrap, never echoed to output (Section 1). Public HHDC is an anonymized 5% sample (not census), **not account-joinable**, with microdata restricted to Fed researchers — it is **not designed to identify individuals** and exposes only aggregate figures.
- **Score-scale honesty.** Scores are recorded with their scale (Equifax 280–850, prime ≥660; VantageScore; FICO) and never cross-compared without explicit normalization.

---

## Open Questions (UNKNOWNS — flag, never assert; resolve at contract time)

These are in scope but **not confirmed** by the research. The spec must treat each as UNKNOWN:
1. **Exact FCRA permissible-purpose attestation mechanics** for each licensed feed (how "account review" is attested/enforced operationally), and whether/how FCRA permissible purpose applies to depersonalized/aggregate feeds (Prama Benchmarking). — UNKNOWN.
2. **Data-use / redistribution restrictions, retention limits, and secure-transfer requirements** (including whether SFTP is used) per licensed contract. — UNKNOWN.
3. **The precise sub-national geographic join-key field** for each licensed feed (the exact MSA/segment/account key field names). — UNKNOWN.
4. **Concrete pricing / licensing structure** for Prama / Triggers / TruVision / Ascend (and any Equifax target). — UNKNOWN.
5. **The literal field schemas / data dictionaries** for the NY Fed HHDC public tables and the Philly Fed CCE. — UNKNOWN (the live adapter must be written defensively against the actual published columns; the per-id source-locator and the DemoProvider cover this for v1 build/test).
6. **Whether Equifax Market Pulse offers a state/MSA cut.** — UNRESOLVED; do not assert either way.
7. **Whether any Equifax account-level portfolio-review product exists, its capability, and its FCRA basis.** — UNKNOWN; only the Equifax OAuth 2.0 client_credentials auth pattern is confirmed.

> Refuted items that must **never** appear as capabilities: (a) Philly Fed CCE census-tract/ZIP/county/MSA geographic join key; (b) Prama Vintage Analysis delinquency by tier/geography/LOB/product over nine quarters; (c) the claim that Equifax Market Pulse is national-only with no state/MSA cut (do not assert either way).

---

## Implementation Notes / Lessons Carried (L1–L6 as hard requirements)

- **L1 — Bootstrap is EXTRACT-ONLY.** `ExtractFiles` writes only `runner.py` + `requirements.txt` + `RUN.txt`; the user runs `runner.py` from PowerShell against the **CLOSED** workbook (openpyxl). No in-Excel shell-out, no xlwings, no VBA `.Save`. Removes the cmd-quoting / file-lock / `.Save`-error failure class.
- **L2 — `keep_vba=True` ONLY for `.xlsm`.** On `.xlsx` it injects a dangling vbaProject relationship Excel rejects as "file format or extension is not valid." Hard rule, gated on file extension.
- **L3 — Embedded code is PURE ASCII; extractor writes UTF-8.** Non-ASCII written as ANSI causes a Python `SyntaxError` on extraction. No exceptions.
- **L4 — No native openpyxl charts.** They are the top "unreadable content / recovered" trigger and re-emit on every refresh. Use formula cells + conditional-format heat + optional macro-painted sparklines.
- **L5 — Adapter seam binds throttle/backoff + last-observation derivation.** These are **seam-contract requirements** so the licensed v2 adapter (where API rate limits are real) inherits them. For the static Class A HHDC download they manifest as conditional-fetch/idempotency (avoid redundant re-download), **not** an asserted HHDC API quota (none is in the research).
- **L6 — Clean seams are the provider adapter (with the Section 1a interface contract), the transform registry, and the watchlist validator.** **Two providers are mandatory:** a deterministic offline `HhdcDemoProvider` (the synthetic stand-in used by ALL tests, no contract/key/network) and the live `HhdcProvider` (the free no-contract LIVE source). These are **distinct**: HHDC is the free live source; the DemoProvider is the deterministic offline stand-in. The licensed adapter is a module swap behind the same seam (Section 1a), exercised only via in-process stubs in v1.
