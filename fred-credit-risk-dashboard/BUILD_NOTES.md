# BUILD NOTES — FRED Credit-Risk Dashboard Template (v1)

Deliverable: `FRED_Credit_Risk_Dashboard.xlsm` — a single self-contained,
macro-enabled workbook. This file records the build decisions the spec asks for.

## KeyBank house style (applied)

The workbook is skinned with the house **KeyBank** design system (Key Red + Ink
black + warm neutrals), dropped in as `keybank_style.py` (tokens + composed
helpers) and `keybank_charts.py` (native Excel line charts). `build_workbook.py`
now pulls every fill/font/border from those modules — no hardcoded hex — so this
template and any future one built from it look like one family. Per lane:

- **Dashboards** — Ink brand banner + one Key Red rule, a 3-tile KPI strip
  (Portfolio Stress Index / Series in Alert / Tightening Signals), a 12-quarter
  native trend chart, brand-muted diverging heat on the z-score column, and a
  per-row Trend (8q) sparkline column.
- **Watchlist_Geo** — the Key Red geographic-boundary gate banner; diverging
  heat on YoY (red = deterioration).
- **System tabs** — quiet Onyx section bands, Consolas code, no heat.

**Integration fix (not in the handoff):** the branded layout merges A:J for the
banner and A:I for the KPI strip, so the runner's old run-status block (H1:I4)
landed on merged cells and would have raised on refresh. The status readout was
moved to column **L** (free of every merge) as two compact masthead lines
("Last run …" / "Pulled n/total · s stale · a alerts"); the builder pre-styles
the panel, the runner fills L1/L2, the macro fills L4. Both write backends and
`macro.bas` were updated together.

**Sparklines (one honest caveat):** openpyxl can't write native Excel
sparklines, so the Trend column ships empty and the macro paints it after the
Raw_* tabs fill. The handoff's one-line snippet would have pointed every row at
the same range; because our raw layout is vertical-per-series, the macro instead
looks each series up in its Raw_* tab and sources that series' own 8-quarter
window (SLATE line, Key Red newest point). The routine is fully guarded
(`On Error Resume Next`) so it can never break a refresh — but, like the rest of
the VBA, it could not be exercised in Excel on this headless box.

Verified after restyle: 42 tests green, olevba round-trips the larger macro,
the `formulas` engine recalculates the KPI tiles (Stress Index, COUNTIF alert
counts) and z-score heat, charts and merged banners are present, and the
email-simulation still rebuilds from the `.xlsm` alone.

## Write-path choice: xlwings (primary) vs openpyxl (fallback)

**Chosen: `xlwings` as the recommended/primary path; `openpyxl` as an isolated
fallback.** The whole point is click-and-go on a work machine, and xlwings lets
Python write into the *already-open* workbook, so the button is a true one click
with no close/reopen dance. The trade-off is one extra dependency.

`openpyxl` is kept as a clean fallback (writes the closed file) for headless or
no-Excel use — it is also what every test and the email-simulation in this repo
run against, since the build environment has no Excel. The backend is selected
by `_config → [SETTINGS] → write_backend = auto|xlwings|openpyxl`; `auto` tries
xlwings and falls back. The two backends share one interface
(`runner.Backend`), so the presentation/transform/validator code never sees
which one is in use — the seam is a single class swap.

## VBA embedding

The macro (`macro.bas`, module `FREDDashboard`, sub `ExtractAndRun`) is embedded
as a real `xl/vbaProject.bin` built from scratch (`vba_writer.py`) to
[MS-OVBA] + [MS-CFB]:

- MS-OVBA compression uses raw chunks for full 4096-byte windows and an
  all-literal compressed chunk for the remainder (a short raw chunk is illegal
  and is rejected by both Excel and olevba — this was found and fixed during the
  build).
- Module source is stored uncompiled (`MODULEOFFSET = 0`); Excel compiles it on
  load — the well-tolerated shape for an injected standard module.
- The package is then switched to macro-enabled (`assemble_xlsm.py`): workbook
  content-type → `…sheet.macroEnabled.main+xml`, a `vbaProject` content-type
  override, and the workbook→vbaProject relationship.

**Verification done on this (headless, no-Excel) box:**
- `olevba` detects the project, enumerates the `FREDDashboard` module, and
  decompresses the source **byte-for-byte** equal to `macro.bas`.
- `olefile` reads the compound structure; all five streams present and sized.
- `openpyxl` loads the `.xlsm` with `keep_vba=True` and preserves `vba_archive`,
  so a runner refresh keeps the macro embedded.
- MS-OVBA `compress()` round-trips through oletools' real decompressor across
  sizes 0…12000, including the 3641–4095 remainder edge case.

**Honest caveat:** the build environment has no Excel, so the final
"open-in-Excel-and-click" step could not be exercised here. Every layer Excel
relies on (CFB structure, MS-OVBA streams, OOXML content-types/rels, formula
recalc) was validated with the tools above, and the email-simulation proves
self-containment. The portable VBA text also lives in the `_code_vba` tab; if a
specific Excel build ever rejects the embedded project, the module imports in
~30 seconds (Developer → Visual Basic → Import `_code_vba`).

## Formula-driven, fixed-anchor design

Raw series are written newest-first into fixed-height blocks (100 slots), so the
dashboard/watchlist formulas have stable anchors that never shift across
refreshes. The builder writes all presentation formulas once; the runner only
refills raw values. Dashboards therefore re-render from formulas without
re-running Python, and a refresh is a clean stateless rebuild.

Verified by recalculating the demo-populated workbook with the pure-Python
`formulas` engine: z-scores compute, ALERT/TIGHTENING flags fire, the watchlist
`RANK` orders geographies (Dallas −0.93% = rank 1 in the demo), trend arrows
render, and each dashboard shows only its own lane.

## Series status at build time

The build environment had **no FRED API key**, so series were **not pulled
live** during the build; live staleness is detected and logged by the runner's
stale-check at run time (`is_stale`, multiplier in `_config`). The documented
non-live items baked into `_config`:

- **`FODSP`** — Financial Obligations Ratio: **discontinued after 2023:Q3**.
  Marked documented-dead in `notes`; `dashboard_capable=FALSE`; excluded from
  live pulls (the runner skips `is_dead` series — confirmed: demo pulls 146/147).
- **Debt-service ratios (`TDSP`, `MDSP`, `CDSP`)** — methodology switched to a
  credit-bureau basis in **2024:Q2**; noted so a level shift isn't misread.
- **G.19 (`TOTALSL` family)** — the nonfinancial-business sector was dropped from
  the **May 2025** release; noted.
- **Bank-tier delinquency/charge-off series** (`…T100S`, `…OBS`) — several lag a
  quarter; the stale-check logs any whose latest observation is overdue.
- **Case-Shiller metros** (`*XRSA`) — copyrighted; internal monitoring only, not
  for redistribution.

A handful of less-common bank-tier series IDs (e.g. `CORCOBS`, `DROCLACBS`) are
seeded from the spec's suffix conventions; if any is not a live FRED ID, the
runner logs it under `errors` and continues — it cannot break the build.

## Series dictionary totals

- 147 series seeded across lanes: consumer 33, commercial 18, price 96.
- 89 watchlist-capable (geographic HPI only): 51 FHFA state (50 + DC), 18 FHFA
  metro CBSAs, 20 Case-Shiller metros.
- The watchlist boundary is enforced at build time and at run time; the suite
  includes a test that a delinquency series marked watchlist-capable is refused.

## Python dependencies + versions (build environment)

| package  | version  | role |
|----------|----------|------|
| python   | 3.11.15  | interpreter |
| pandas   | 3.0.3    | series handling, transforms |
| numpy    | 2.4.6    | (pandas dep; used in tests) |
| openpyxl | 3.1.5    | workbook read/write, fallback backend |
| fredapi  | 0.5.2    | FRED provider adapter |
| xlwings  | (work machine) | primary write-into-open-book backend |

Test/verify-only (not needed at run time): `pytest`, `oletools` (olevba VBA
validation), `formulas` (pure-Python recalc).

Work-machine runtime needs only: `pip install fredapi xlwings openpyxl pandas`.

## What v1 does not do (scope fence)

No portfolio ingest, no credit-quality geo targeting (FRED doesn't carry it),
no CRE geo targeting (FRED CRE prices are national), no persisted state, no LLM
in the data path, one provider (FRED). The seams — provider adapter, transform
registry, watchlist validator, write backend — are isolated so v2 (a different
or internal source) is a module swap, not a rebuild.
