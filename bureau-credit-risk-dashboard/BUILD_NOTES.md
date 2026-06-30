# BUILD NOTES — Consumer Credit-Risk Monitor (bureau feed), v1

Deliverable: `Consumer_Credit_Risk_Monitor.xlsm` — a single self-contained,
macro-enabled workbook built to `BUILD_SPEC_BUREAU.md`, which was itself driven
by the cited coverage research in `COVERAGE_RESEARCH_BUREAU.md` (22 confirmed /
3 refuted claims). This file records the build decisions the spec asks for.

## What the data source is (and the honest tier split)

The free/public tier that can power the **dashboards** is the **NY Fed Household
Debt & Credit (HHDC)** report — an anonymized **5% (one-in-20) Equifax sample**,
aggregate-only and **not account-joinable**. None of the no-contract sources
carry a portfolio-joinable account key or a usable fine-grained geographic key,
so a buildable-today template is honestly **dashboard-only, with the watchlist
lane gated** until a licensed feed is contracted. The watchlist boundary is the
same hard rule the FRED template enforces: never plug a national/aggregate
series into a lane that implies a portfolio-localizable join key.

## Two providers behind one seam (mandatory, L6)

- **`HhdcProvider`** — the LIVE Class A source: downloads the NY Fed HHDC public
  tables and maps each `id` via its per-row source-locator. The literal HHDC
  column schema was **not** established by the research (Open Question #5), so
  `_parse_table` is deliberately **unbound** — it raises with a clear message
  until bound to the real published columns. No test hits the network.
- **`HhdcDemoProvider`** — the deterministic OFFLINE stand-in (seeded pseudo-walk
  per `id`, fixed `--asof`, no network/key). Every test and the `--demo` button
  use it; identical input → identical output (idempotent).
- **`ClassCStubProvider`** — an in-process OAuth `client_credentials` STUB for
  the v2 swap rehearsal. It asserts the **HTTP 401 / missing-token** fail-fast
  path **without any live request**. Live Class C calls are forbidden in v1.

The adapter seam is the only provider-specific code: every adapter implements
`fetch_series(spec, secret) -> list[NormalizedRow]` with a fixed normalized
schema, so the transform registry and watchlist validator never see the
provider. A licensed feed (Prama / Triggers / TruVision / Ascend) is a module
swap behind this seam, not a rebuild.

## The watchlist gate (default-deny, defense in depth)

Before anything reaches the `Watchlist` tab the validator applies a
**default-deny whitelist** (not a blacklist). A row is admitted only if ALL
three hold: `watchlist_capable=TRUE` **AND** `source_class="C"` **AND**
`geo_segment ∈ {msa, account}`. Under the v1 public stand-in every seeded series
is Class A / national / aggregate, so the lane is refused **by design**, with a
**series-named error built by interpolating the real `id` / `geo_segment` /
`source_class`** at runtime (never a hardcoded string).

Two independent gates make this defeat-proof:
- A build-time hard gate (`assert_no_public_in_watchlist`) refuses the build if
  any non-Class-C row is ever flagged `watchlist_capable`.
- The runtime evaluator refuses on the `source_class="A"` gate **even if** the
  `watchlist_capable` flag is flipped, and a `national` row is refused by **both**
  the `source_class` and the geo-whitelist gates. The negative test
  (`test_watchlist_gate_defense_in_depth`) proves both paths.

## Formula-driven, fixed-anchor design

Raw series are written newest-first into fixed-height blocks (60 slots) in the
single `Raw_HHDC` tab, so the dashboard formulas have stable anchors that never
shift across refreshes. The builder writes all presentation formulas once; the
runner only refills raw values. Thresholds live in `_config [THRESHOLDS]` and
the dashboards' OK/WATCH/ALERT **Status** column references those cells by
formula — so retuning a band never touches `_code_py`.

Verified by recalculating the demo-populated workbook with the pure-Python
`formulas` engine: the YoY-% headline cells compute (e.g. credit-card balance
+21.7%) and the formula-driven Status cells resolve to ALERT/WATCH/OK directly
from the `_config` threshold cells (4 ALERT in the demo).

## VBA embedding

The macro (`macro.bas`, module `CreditRiskMonitor`, sub `ExtractFiles` with the
`ExtractAndRun` alias) is embedded as a real `xl/vbaProject.bin` built from
scratch (`vba_writer.py`) to [MS-OVBA] + [MS-CFB], then switched to
macro-enabled (`assemble_xlsm.py`: macroEnabled content-type, vbaProject
content-type override, workbook→vbaProject relationship).

**Verified on this headless, no-Excel box:**
- `olevba` detects the project and enumerates the `CreditRiskMonitor` module
  (`ExtractFiles` / `ExtractAndRun` / `PaintSparklines`).
- The package has the macroEnabled + vbaProject content types and the
  workbook→vba relationship, the `vbaProject.bin` has the CFB magic
  (`D0CF11E0…`), and there are **no dangling relationships**.
- `openpyxl` loads the `.xlsm` with `keep_vba=True` and preserves `vba_archive`,
  so a runner refresh keeps the macro embedded.

**Honest caveat:** the build box has no Excel, so the final
open-in-Excel-and-click step was not exercised here. The portable VBA text also
lives in the `_code_vba` tab; if a specific Excel build ever rejects the embedded
project, the module imports in ~30 seconds (Developer → Visual Basic → Import).

## Lessons carried from the FRED build (L1–L6, hard requirements)

- **L1 — Bootstrap is EXTRACT-ONLY.** `ExtractFiles` writes only `runner.py` +
  `requirements.txt` + `RUN.txt`; the user runs `runner.py` from PowerShell
  against the **CLOSED** workbook (openpyxl). No in-Excel shell-out, no xlwings,
  no VBA `.Save` — this removes the cmd-quoting / file-lock / `.Save`-error class.
- **L2 — `keep_vba=True` ONLY for `.xlsm`.** On `.xlsx` it injects a dangling
  vbaProject relationship Excel rejects as "file format or extension is not
  valid." Gated on the file extension in `OpenpyxlBackend`.
- **L3 — Embedded code is PURE ASCII; the extractor writes UTF-8** (ADODB.Stream,
  not FSO ANSI). Confirmed: `runner.py`, `macro.bas`, `series_seed.py` are all
  ASCII, so extraction can never produce a `SyntaxError` from ANSI-written bytes.
- **L4 — No native openpyxl charts.** They are the top "unreadable content /
  recovered" trigger and re-emit on every refresh. Dashboards use formula cells +
  conditional-format heat + optional macro-painted sparklines only; a test
  asserts `ws._charts == []` on every sheet.
- **L5 — The adapter seam binds throttle/backoff + last-observation derivation**
  so the licensed v2 adapter inherits them; for the static HHDC download they
  manifest as conditional-fetch/idempotency, not an asserted API quota.
- **L6 — Clean seams** are the provider adapter (Section 1a contract), the
  transform registry, and the watchlist validator.

## Series dictionary totals

- 18 series seeded: 17 dashboard (7 balances, 5 delinquency rates/flows, 4
  originations, 1 annual state) + 1 gated watchlist placeholder.
- **0 watchlist-capable** under the public stand-in — by design. The annual
  state row is deliberately `watchlist_capable=FALSE` (state data is annual Q4
  only; quarterly all-state is withheld by Equifax contract, so it is not a
  usable fine-grained watchlist key).

## Compliance posture (design intent, several items UNKNOWN)

The operational mechanics — FCRA permissible-purpose attestation, redistribution
terms, retention limits, secure transfer, the precise licensed join-key fields —
are **NOT confirmed by research** and are tracked as UNKNOWN in the spec's Open
Questions #1–#7. v1 touches no licensed data. Secrets (for a future Class C
feed) come from an env var **named** in `_config` (`secret_env`) only — never
hardcoded, never written to disk by the bootstrap, never echoed; an absent var
fails the run fast. Scores are recorded with their scale (Equifax 280–850, prime
≥660; VantageScore; FICO) and never cross-compared without explicit
normalization.

## Tests (all headless, offline, `--demo`)

`tests/test_runner.py` — 10 tests green:
`test_config_parse`, `test_demo_provider_deterministic`, `test_raw_landing_idempotent`,
`test_transforms`, `test_threshold_engine`, `test_reload_headless`,
`test_watchlist_refusal`, `test_watchlist_gate_defense_in_depth`,
`test_class_c_stub`, `test_resolve_secret_fail_fast`.
Plus `email_sim.py` (Phase 7 acceptance): rebuilds from the `.xlsm` alone and
the simulated email carries both the dashboard alert summary and the licensed-
feed-named watchlist refusal.

## Python dependencies

Runtime: `pip install pandas openpyxl` (no `fredapi`, no `xlwings` — the bureau
runner is openpyxl-only against the closed workbook). Test/verify-only:
`pytest`, `oletools` (olevba), `formulas` (pure-Python recalc).
