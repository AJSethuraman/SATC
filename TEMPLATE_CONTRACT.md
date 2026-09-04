# Template Contract — what every credit-risk template MUST share

The point of this contract: every template in the series looks, behaves, and
operates identically, so (a) a user who learned one has learned them all, and
(b) one generic tool — `control_center.py` — can discover and drive any of
them with no per-template wiring. New templates MUST comply. The FRED template
predates this contract and is grandfathered where noted; the launcher handles
both shapes.

## 1. The workbook is the deliverable and the source of truth

One self-contained `.xlsm` per template. Everything needed to re-run it lives
inside it as plain-text tabs. Emailing the workbook transfers the whole tool.

## 2. Tab taxonomy (exact names)

| Tab | Content |
|-----|---------|
| `Dashboard_<Lane>` (1..n) | Formula-driven panels; no native charts in the refreshed workbook (L4, amended 4 Sep 2026 — charts live in a generated secondary workbook) |
| `Watchlist` | The gated lane (FRED template: `Watchlist_Geo` — grandfathered) |
| `Raw_<PROVIDER>` (1..n) | Fixed-anchor raw blocks, newest-first; runner writes, formulas read |
| `_config` | `[SETTINGS]` / `[THRESHOLDS]` / `[SERIES]` — the knob panel, source of truth |
| `_code_py` | The FULL runner source, one line per cell in column A, pure ASCII (L3) |
| `_code_vba` | The macro source (minus `Attribute` lines), paste-ready |
| `_readme` | Setup, run steps, provider notes, compliance/UNKNOWN flags |

## 3. `_config` schema

Sections in column A: `[SETTINGS]` (key/value/help), `[THRESHOLDS]`
(`id|watch|alert|direction`), `[SERIES]` (the 19-column dictionary from
BUILD_SPEC_BUREAU.md §2). Lines starting `#` are comments. Required settings
keys: `demo_mode`, `raw_slots` (build-bound — the runner refuses a mismatched
layout), `secret_env` (name of the env var for any licensed secret; the value
is NEVER stored anywhere).

## 4. Runner CLI contract

`python runner.py --workbook <path.xlsm> [--demo] [--asof YYYY-MM-DD]`

- `-w/--workbook` required; runs against the CLOSED workbook via openpyxl
  (`keep_vba=True` ONLY for `.xlsm` — L2).
- `--demo` = the deterministic offline DemoProvider (no key, no network);
  every test uses it.
- Exit codes: 0 OK, 1 run error, 2 gate error (watchlist/transform), 3 missing
  secret. JSON status on stdout, human summary on stderr.
- Grandfathered: the FRED runner also accepts `--backend`; new runners are
  openpyxl-only.

## 5. Macro contract (extract-only, L1)

Module exposes `ExtractFiles` (+ `ExtractAndRun` alias). It writes EXACTLY
`runner.py` (from `_code_py`, via ADODB.Stream UTF-8), `requirements.txt`,
and `RUN.txt` next to the workbook. No shell-out, no xlwings, no `.Save`.
Optional `PaintSparklines`, fully guarded.

## 6. Provider seam contract (BUILD_SPEC_BUREAU.md §1a)

One provider per template behind
`fetch_series(spec, secret=None) -> list[NormalizedRow]`,
`NormalizedRow = {id, period, value, geo_segment, source_class, units}`.
Two implementations mandatory: the live provider and a deterministic offline
DemoProvider. Licensed (Class C) adapters are a module swap; live Class C
calls are forbidden until contracted.

## 7. Watchlist gate (BUILD_SPEC_BUREAU.md §3 — non-negotiable)

Default-deny whitelist, three gates, all required:
`watchlist_capable=TRUE` AND `source_class` admitted for the lane AND
`geo_segment`/entity key in the template's explicit join-key whitelist.
Refusals are series-named, interpolated from the real config row. A build-time
hard gate backs the runtime gate (defense in depth).

## 8. Style

All visuals from the copied-in house style modules (`keybank_style.py`);
never a hardcoded fill/font in a builder. Heat direction must agree with the
threshold direction (red = stress).

## 9. Verification bar (every template, before it ships)

Headless pytest suite (config parse, demo determinism, TRUE same-file
idempotence, transforms vs hardcoded expected values, reload with
`keep_vba`, no-native-charts assert, watchlist refusal + defense-in-depth,
raw-layout mismatch refusal) + `email_sim.py` acceptance + `formulas`-engine
recalc spot-check + olevba decompile + OPC package audit (no dangling
relationships, no overlapping merges).

## 10. Control Center compatibility

`control_center.py` discovers any `.xlsm` with a `_code_py` tab, extracts the
embedded runner, and drives it per §4. A template that satisfies §2–§4 is
launcher-compatible by construction — no registration anywhere.

## 11. Transmission format (the corporate-security reality)

Binary files do not survive the corporate email/DLP boundary; plain text does.
Therefore every template MUST ship a `make_bundle.py` that generates a single
**pure-ASCII** builder script (`build_<template>.py`, code embedded as
gzip+base64, target ≤ ~60 KB) which, run on the target machine
(`python build_<template>.py` from PowerShell), locally produces:

- the demo-populated `.xlsm` (macro embedded), AND
- a demo-populated fallback `.xlsx` + `macro.bas` (if the local Excel rejects
  the embedded VBA project: open the `.xlsx`, paste `macro.bas` via Alt+F11,
  save as `.xlsm`), AND
- `runner.py` + `requirements.txt`.

Nothing binary is ever transmitted — the workbook is *built* where it will
live. `control_center.py` is itself plain ASCII and travels the same way;
its discovery accepts both `.xlsm` and fallback `.xlsx` workbooks.

## 12. Provenance & tie-out (verification against the official record)

Every fetched value must be traceable to a human-readable official
rendering a reviewer can check by eye. Each template ships:

- **`_provenance` tab**: one row per metric/field — source document,
  location within it (Call Report schedule + line / MDRM code; 10-Q note +
  XBRL tag + accession; series page URL), and the URL pattern to the
  official rendering (FFIEC PDF facsimile, EDGAR viewer, FRED/CFPB page).
- **Tie-out mode**: `runner.py --tieout <entity/series> <period>` prints
  each pulled value alongside its document location + URL, enabling
  sample verification of a feed in minutes.
- Run provenance in the status panel where the source supports it (data
  vintage, accession numbers, index timestamps).

Retrofit priority: the FDIC template (with the competitor pack) and the
EDGAR template; earlier templates gain `_provenance` opportunistically.

## 13. Entity sets are config, not code

Any template that monitors a definable set of entities (peer banks,
competitors, footprint counties, counterparties) MUST hold that set as an
editable `_config` section (the `[PEERS]`/`[FOOTPRINT]` slot pattern:
`slot | key | name | group | active`): add/remove = edit a line + re-run,
within slot-provisioned headroom (build-time `--*-slots` knob);
over-capacity is REFUSED with a rebuild message, never truncated; a
`--lookup` helper resolves human names to keys (CERT, CIK, FIPS, ...).
Where a source has per-entity dialects (e.g., EDGAR disclosure families /
member maps), first fetch of a new entity bootstraps its mapping into a
visible `_config` section — unmappable cases are surfaced for manual
decision, never silently guessed.

## Carried lessons

L1–L6 (see BUILD_SPEC_BUREAU.md) are incorporated by reference; new lessons
append there and to this contract.

- **L7 — openpyxl's `ws.cell(r, c, None)` silently IGNORES `None`.** Cells
  are blanked ONLY by assigning `.value` explicitly
  (`ws.cell(r, c).value = None`). Found in the FDIC build; the earlier
  templates' clear-blocks pattern was a silent no-op masked by same-shape
  rewrites — a failed live fetch after a successful run would have left
  stale data under a fresh timestamp. Every template carries a
  `test_clear_actually_blanks` regression.
- **L8 — Threshold/DefinedName cells must be NUMERIC-typed.** Excel's
  `number >= text` comparison is silently FALSE: a `"0.5"` text cell
  downgraded every ALERT to WATCH in the macro build. Recalc verification
  must compare statuses, not just values.
- **L4, amended 4 September 2026 — tested, half of it did not reproduce.**
  L4 as written (BUILD_SPEC_BUREAU.md) gives two grounds for "no native
  charts": they are *"the top unreadable-content / recovered trigger"*, and
  they *"re-emit on every refresh"*. Both were tested on the Windows build
  PC in Excel 16.0 (Click-to-Run, 16.0.20326) rather than inherited:
  - A native openpyxl `LineChart` in a bare `.xlsx` opened with **zero
    dialogs**. The same chart added to the real `Bank_Peer_Monitor.xlsm`
    beside its VBA project also opened with **zero dialogs, and the
    ExtractFiles macro still ran** afterwards. The corruption ground does
    not reproduce on this Excel. Recorded as a test result, not a proof
    for every Excel that exists.
  - The refresh ground is still true and is the binding one: the runner
    rewrites the monitor on every run, so any chart in it is regenerated
    each time and an analyst's customisation is lost.
  **So L4 now reads:** no native charts in the *refreshed* workbook. A
  **generated secondary chart workbook** — rebuilt wholesale, never edited
  in place, no macros — is the sanctioned home for charts
  (`credit-suite/tools/chartbook.py`). Its own carried lesson, learned the
  same day: **look at a rendered chart before calling it done.** The first
  two builds "opened with zero dialogs" and had no axis numbers and a legend
  drawn over the data; a harness reading a cell cannot see either. Export
  a chart to PNG through Excel and read it. Decided by the firm on the
  4 September docket: *"Amend L4, cite the tests."*
