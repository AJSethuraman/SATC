# Consumer Credit-Risk Monitor — bureau feed (v1)

A single self-contained, macro-enabled Excel workbook
(`Consumer_Credit_Risk_Monitor.xlsm`) that pulls aggregate consumer credit-risk
metrics from a **credit-bureau-sourced public feed** (the NY Fed Household Debt
& Credit report, built on an anonymized 5% Equifax sample), lands them raw, and
presents them as **formula-driven dashboards**. A **gated "watchlist" lane** is
reserved for a future licensed (Class C) MSA / account feed and is **refused
under the public stand-in by design**.

All code, config and docs live inside the workbook, so it can be emailed, opened
elsewhere, and re-run. No AI is involved in the data path — transforms,
thresholds and the watchlist gate are deterministic and config-driven.

## Provenance

1. `COVERAGE_RESEARCH_BUREAU.md` — cited deep-research pass (22 confirmed / 3
   refuted claims) on U.S. consumer credit-bureau data feeds.
2. `BUILD_SPEC_BUREAU.md` — the build spec derived from that research.
3. This template — built to the spec, verified headless.

(All three live in `fred-credit-risk-dashboard/` for the research/spec docs and
here for the implementation.)

## Quick start

```bash
pip install pandas openpyxl
python3 make_workbook.py            # build the .xlsm
python3 -m pytest tests/ -q         # 10 tests, headless/offline
python3 email_sim.py                # Phase 7 acceptance (rebuild + email sim)
```

## Using it in Excel (locked-down, no .bat needed)

1. Open the `.xlsm`, enable macros, press **Alt+F8 → ExtractFiles**. It writes
   `runner.py`, `requirements.txt`, and `RUN.txt` next to the workbook. **Nothing
   runs inside Excel.**
2. **Save and close** the workbook.
3. From PowerShell, follow `RUN.txt`: install deps, then run `runner.py` against
   the **closed** workbook — `--demo` for offline synthetic data, or no flag for
   a live HHDC download.
4. Reopen — the formulas recalc into the populated dashboards. Optional:
   **Alt+F8 → PaintSparklines** for the Trend column.

## Tabs

| Tab | What it is |
|---|---|
| `Dashboard_Balances` / `_Delinquency` / `_Originations` | Formula panels: latest, prior, a named-transform headline, optional trend sparkline, config-driven OK/WATCH/ALERT status, heat shading. |
| `Watchlist` | The **gated lane** — shows the series-named refusal and the licensed-feed requirement, not data, under the public stand-in. |
| `Raw_HHDC` | Raw observations, newest-first (the audit trail). |
| `_config` | The knob panel: series dictionary + `[THRESHOLDS]` (source of truth). |
| `_code_py` / `_code_vba` | `runner.py` and `macro.bas` as plain text. |
| `_readme` | In-workbook provider notes, score-scale + compliance, run steps. |

## The watchlist boundary

A row feeds the watchlist only if **all three** hold: `watchlist_capable=TRUE`
**AND** `source_class="C"` (licensed) **AND** `geo_segment ∈ {msa, account}`.
Every public stand-in series is Class A / national / aggregate, so the lane is
refused — and stays refused even if a single capability flag is flipped, because
the `source_class="A"` gate still catches it. No public/national/annual-aggregate
series can localize a portfolio subset.

## Scope

**In scope (v1):** Class A public HHDC ingestion (live `HhdcProvider`) + a
deterministic offline `HhdcDemoProvider`; balances / delinquency rates & flows /
originations dashboards; deterministic transforms + config-driven thresholds; the
gated watchlist with structural default-deny refusal; the adapter seam; the
extract-only bootstrap; the email-simulate acceptance.

**Out of scope (v1):** any live licensed feed (Prama / Triggers / TruVision /
Ascend — v2 module swap only); populating the watchlist with real data;
cross-score-scale crosswalk (record-and-refuse only); account-level joins; any
in-Excel Python, xlwings, native charts, or hardcoded secrets; redistribution of
licensed data.

See `BUILD_NOTES.md` for the full build decisions, verification, and the L1–L6
lessons carried from the FRED build.
