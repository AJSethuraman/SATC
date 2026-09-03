# Verification Report — FRED Credit-Risk Dashboard

**Date:** 2026-09-03 · **Verifier:** adversarial re-run (four independent checks:
test-suite + mutation, hazard hunt, adversarial compute, workbook-artifact open).
**Method:** every claim below was produced by running the code and/or **opening the
`.xlsm` and reading actual cells** — not by trusting a prior handoff, a passing
exit code, or a file's existence. Environment note: this box has **no Excel and no
network** (FRED egress-blocked), so the live-FRED path and the real-Excel one-click
acceptance test could not be exercised here — stated plainly, not papered over.

---

## What this tool is (one paragraph)

A **self-contained `.xlsm`** that pulls ~147 credit-risk series from **FRED** via an
embedded Python `runner.py`, lands them raw (newest-first, fixed-anchor blocks),
and presents them as **formula-driven** consumer/commercial/price dashboards plus a
gated commercial **geographic watchlist**. All code/config/docs live *inside* the
workbook (`_code_py`, `_code_vba`, `_config`, `_readme`); the VBA "Extract & Run"
button rewrites `runner.py` and executes it. It computes two alert types — a rolling
**8-quarter z-score** breach and a **SLOOS net-% level** breach — and flags them in
both Python (a count in the status line) and native Excel formulas. Design tenets:
**stateless** (clean rebuild every refresh, no persisted state), **one isolated FRED
provider**, **deterministic, no LLM in the data path**, and a **hard watchlist gate**
(only geographically-joinable house-price series may enter the watchlist).

---

## LIST 1 — What was verified (command → real output)

| Check | Command | Result |
|---|---|---|
| Test suite | `python3 -m pytest tests/ -v` | **44 passed, 0 skipped, 0 xfail, 0 deselected, 0 errors, 2.81s** |
| Email-sim acceptance (demo) | `python3 email_sim.py` | **EXIT 0** — `146/147 series, 17 alerts, 0 stale`; raw+watchlist+macro all present |
| Data path (demo) | `python3 runner.py -w …xlsm --backend openpyxl --demo` | **EXIT 0** — `{"ok":true,"series_pulled":146,"alert_count":17,...}`; 1 skipped = `FODSP` (correctly `is_dead`) |
| Determinism | two pinned-`--asof 2026-03-01` demo runs, full cell diff | **50,958 cells compared, 0 differing** |
| Artifact populated | open `.xlsm`, read cells | `Raw_Consumer` 33 blocks / `Raw_Commercial` 18 / `Raw_Price` 96 = 147; dates+values real; **missing obs are blank `None`, not `0`** |
| Formulas real | read `Dashboard_*` cells | e.g. `Dashboard_Consumer!J8 = =IF(AND(ISNUMBER($H8),$H8>=zscore_band),"⚠ ALERT","")` — genuine cross-sheet refs, correct row arithmetic |
| Operator agreement | shipped cells + Python | Python `evaluate_alert` and Excel flags **both `>=`**, both alert types — no mismatch; on-threshold (`z==band`) fires on both |
| SLOOS units | transform trace | net-% compared as a **level** vs band, **not** `pct_change` — correct pp-vs-pct treatment |
| Embedded code integrity | diff `_code_py` vs `runner.py`; `olevba` on `vbaProject.bin` | byte-identical (modulo trailing newline); real working VBA (`ExtractFiles`/`PaintSparklines`) |
| VBA survives write | `cmp` `vbaProject.bin` before/after openpyxl write | **byte-for-byte identical** (12,800 B); macro-enabled content-type intact |

## LIST 2 — What passed (numbers)

- **44/44 tests, 2.81s.** README/TESTING.md say "42" — **stale; the real count is 44.**
- **Mutation proof:** 11 of 14 primary mutations + the zscore-alert probe go **RED**
  when their fix is deleted — the suite is genuinely load-bearing for the watchlist
  gate, transform-misuse gate, YoY transform, `.`→NaN coercion, stale detection,
  config parse, demo determinism, VBA compression, build counts, FRED retry, and
  watchlist filter.
- **No `skipif`/`xfail`/`importorskip` anywhere** in `tests/` — a missing dependency
  is a loud collection-time `ImportError`, never a silently-green suite.

## LIST 3 — What was NOT checked, and why (the trust-earning list)

- **The live FRED pull has still never run.** `api.stlouisfed.org:443` is **403-blocked
  by the egress proxy** here (gateway `connect_rejected`). The tool has therefore
  **never done its actual job end-to-end**; only the offline demo/mocked seam is
  proven. **To run it live, the environment must allow outbound HTTPS/443 to
  `api.stlouisfed.org`** (the host `fredapi` calls) — request that, then run a real
  pull and confirm a real series flows to a flag.
- **The real-Excel one-click acceptance test** (native recalcalc, xlwings, macro-painted
  sparklines) is **unverified** — no Excel in this environment. TESTING.md already
  warns this. D1's Excel-side rendering (below) is therefore *reasoned from the shipped
  formula + observed write path*, not from a live recalc.
- **Three tests are decoration** (stay green with their fix removed) — see MUT below.
- **Untested surface:** `evaluate_alert`'s **`sloos_level` branch** (no direct test; all
  17 demo alerts are zscore), transforms `qoq_pct`/`mom_pct` (no test, no seed use),
  `XlwingsBackend`, `raw_layout`/`RawBlock` (indirect only).

---

## Defects (ranked)

### The audit-trail gap (the product's stated core feature — self-citation)
For a KeyBank flag to be re-derivable six months later, the output must carry six
things. **Two are present, four are missing/weak:**

| # | Element | Status | Evidence |
|---|---|---|---|
| i | FRED series ID | ✅ present | `Raw_Consumer!A2="CORCCACBS"` |
| ii | Observation date | ✅ present | `Raw_Consumer!A4="2026-03-31"` |
| iii | **Vintage / as-of pull date** (distinct from obs date) | ❌ **missing** | only one global `Last run` = the `--asof`; **no `realtime_start`/vintage anywhere** in `runner.py` |
| iv | Threshold value **+ basis** | ⚠ partial | value present (`zscore_band=1`, `sloos_band=20`); **no recorded basis/citation for *why* 1.0/20.0** |
| v | Units + transform applied | ⚠ partial | transform on the raw cell; **units only via `_config` lookup**, not on the cell |
| vi | Link to FRED series page | ❌ **missing** | zero `fred.stlouisfed.org`/`HYPERLINK` anywhere in workbook or repo |

**Root cause (iii):** `FredProvider.fetch` calls `get_series(series_id)` (runner.py:437)
with **no realtime params** — i.e. FRED "latest". The README makes it a design tenet
("stateless… no persisted state"). So a flag computed Tuesday **will not re-derive
Friday** after a FRED revision. This is the single most serious defect for a tool of
this shape and it is **by design** — closing it is a real change (persist the
realtime/vintage date per observation; pull with pinned `realtime_start`/`realtime_end`
or ALFRED), not a one-liner.

### Silent failure modes

- **[CRITICAL] Malformed threshold → opposite silent failures on the two auditable
  surfaces.** A threshold cell that is **blank/non-numeric** becomes **`0.0`**
  (`parse_config`, runner.py:194-196) → Python flags **~everything**; but the Excel
  flag never coerces the threshold, and Excel's `number >= text` is always FALSE → the
  Flag column goes **silently, permanently blank** on every dashboard. An **absent**
  threshold row instead silently falls back to `1.0`/`20.0`. **There is no
  `validate_thresholds()`** to match the real `validate_watchlist`/`validate_transforms`
  gates. Negative bands fire on ~everything too, unguarded.
- **[CRITICAL] Exit code reads success even if every fetch fails.** `pulled==0` still
  returns `0` / `{"ok":true}` (runner.py:752-757, 788-815). A FRED outage or revoked
  key → the workbook silently re-presents **stale raw data as current**, and any
  scheduler gating on exit code sees green. The tool violates its own "never trust an
  exit code" rule.
- **[HIGH] Silent xlwings→openpyxl downgrade** (runner.py:693-702) can write the closed
  file while Excel holds a stale open copy → next Excel save silently clobbers the
  refresh. Only a stderr line marks it.
- **[MEDIUM] `write_backend` config knob is a documented no-op** — `cfg.setting("write_backend")`
  is never read; backend is CLI-only. Docs (BUILD_NOTES.md:54) and code disagree.
- **[MEDIUM] D1 — Python vs Excel disagree when the *newest* observation is NaN.**
  Python alerts on the last **valid** point; Excel reads the blank newest cell as `0`,
  mis-rendering Latest/YoY/z-score and suppressing the flag. Plausible live case
  ("period awaiting release"). Excel side reasoned, not recalced (no Excel here).
- **[MEDIUM] Demo cadence bug corrupts the acceptance test's core numbers.**
  `DemoProvider.fetch` picks monthly-vs-quarterly by a **series-ID-suffix guess**
  (runner.py:473), not the declared `frequency`. 23 of 28 monthly series — **including
  the entire Case-Shiller roster feeding `Watchlist_Geo`** — land quarterly, while the
  watchlist YoY formula uses a 12-row (monthly) offset. In the mandated `--demo` path
  the flagship watchlist **"YoY %" is really a ~3-year change mislabeled as 1-year.**
  Demo-only (live FRED supplies true monthly), but the email-sim acceptance runs in
  demo, so its watchlist numbers are wrong.
- **[MEDIUM] Unknown/blank `frequency`** silently → quarterly (runner.py:72-82); **bad
  boolean** → silently `False` (drops a series off every dashboard). Real hazards on the
  documented hand-edit/extension path; not present in the shipped seed.
- **[LOW] Date-index parse failure swallowed** (runner.py:388-391) → lexicographic sort
  scrambles newest-first. Relevant if the provider is swapped.

### MUT — decoration tests (green with the fix removed)
1. `test_zscore_8q_needs_full_window_and_flags_a_jump` — relaxing `min_periods` 8→1
   does not fail it (flat warm-up → NaN regardless); "needs full window" is unproven.
2. `test_zscore_flat_series_is_nan_not_inf` — deleting the div-by-zero guard does not
   fail it (0/0 = NaN anyway).
3. `sloos_level` branch of `evaluate_alert` — no test catches disabling it.

### Cleared (checked and safe)
`.`→NaN never `0` (tested); zscore flat → NaN not inf; retry only on rate-limit;
`main()` top-level returns nonzero; `validate_watchlist`/`validate_transforms` genuinely
raise (hard gates, tested); `resolve_api_key` SystemExit on no key; `assemble_xlsm`
raises on malformed package; `email_sim` genuinely ANDs all assertions; determinism
under pinned `--asof`.

---

## The two known gaps

- **A — live FRED has never run.** Blocked here at the egress proxy (403 to
  `api.stlouisfed.org:443`). **Access needed: outbound HTTPS/443 to `api.stlouisfed.org`.**
  Until a real series returns from FRED and flows to a flag in the workbook, the tool is
  unproven end-to-end. The demo path is **not** a substitute.
- **B — CI did not cover this project.** `.github/workflows/test.yml` ran pytest only in
  `satc_system/`. **Closed in this change:** a `pytest-fred-dashboard` job now runs
  `fred-credit-risk-dashboard/tests` on every push/PR (offline, no Excel — matches what
  the suite needs).
