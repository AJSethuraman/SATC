# TESTING — how to try the FRED Credit-Risk Dashboard

Three tests, easiest first. Tests 1–2 need only Python; Test 3 is the real
one-click run in Excel. Get the workbook from this branch:
`fred-credit-risk-dashboard/FRED_Credit_Risk_Dashboard.xlsm` (download it from
the PR's *Files* tab, or `git pull` and grab it from the folder).

```bash
cd fred-credit-risk-dashboard
pip install fredapi xlwings openpyxl pandas      # xlwings only needed for Test 3
pip install pytest oletools formulas             # only to run the test suite / preview checks
```

---

## Test 1 — fastest, no Excel, no FRED key (demo data)

Proves the data path, formulas, raw layout, watchlist gate and styling end to
end using deterministic synthetic data.

```bash
# populate the workbook with offline demo data (writes into the file):
python3 runner.py --workbook FRED_Credit_Risk_Dashboard.xlsm --backend openpyxl --demo
# then open FRED_Credit_Risk_Dashboard.xlsm in Excel / LibreOffice / Google Sheets
```

You should see: Raw_* tabs filled, the three dashboards lit up (Latest / Prior /
YoY / Z-score / Flag), brand heat on the z-score column, the KPI tiles and trend
charts populated, and Watchlist_Geo ranked by YoY with the red boundary gate.
(The native Trend sparklines are painted by the Excel macro — see Test 3 — so
that one column stays empty until you run in Excel.)

Other quick checks:
```bash
python3 -m pytest tests/ -q     # 42 tests: transforms, validator, VBA, build, refresh
python3 email_sim.py            # email-simulate: rebuild from the .xlsm alone
python3 render_preview.py       # writes build/dashboard_preview.html (open in a browser)
```

## Test 2 — live FRED data, still no Excel (the real adapter)

Tests the actual FRED pull end to end. Needs internet and a free key
(https://fredaccount.stlouisfed.org/apikeys).

```bash
# macOS/Linux:
FRED_API_KEY=your_key_here python3 runner.py \
    --workbook FRED_Credit_Risk_Dashboard.xlsm --backend openpyxl
# Windows PowerShell:
$env:FRED_API_KEY="your_key_here"
python3 runner.py --workbook FRED_Credit_Risk_Dashboard.xlsm --backend openpyxl
```

It prints a JSON summary (series pulled, alerts, any stale/discontinued series it
skipped) and writes the live values into the file. Open it to review. The
runner refuses, by design, if anything in `_config` tries to route a
non-geographic series into the watchlist.

## Test 3 — the real one-click run in Excel (the acceptance test)

This is the piece that could not be exercised in the build sandbox (no Excel
there), so it's the important one to confirm.

1. **Unblock + open.** If you downloaded the file from the web, right-click it →
   *Properties* → check *Unblock* → OK. Open it in Excel and **Enable Content**
   (macros) when prompted.
2. **Install xlwings** (the button writes into the open workbook):
   `pip install xlwings fredapi openpyxl pandas`.
3. **Pick a mode in the `_config` tab:**
   - Demo (no key): set `[SETTINGS]` → `demo_mode` = `TRUE`.
   - Live: set `demo_mode` = `FALSE` and either set the `FRED_API_KEY`
     environment variable or paste your key into the `fred_api_key` cell.
4. **Run the macro.** Press **Alt+F8 → `ExtractAndRun` → Run.**
   (There's no pre-drawn button shape yet — see the note below. To make it a
   literal button: *Developer ▸ Insert ▸ Button (Form Control)* ▸ draw it ▸
   assign `ExtractAndRun`. ~20 seconds.)
5. **Expected:** a status line appears top-right of `Dashboard_Consumer`
   ("Last run … / Pulled n/total · s stale · a alerts"), the Raw_* tabs fill,
   the dashboards recalc, and the **Trend (8q) sparklines** paint (slate line,
   red dot on the newest point). On error, the macro surfaces Python's stderr in
   a message box and the status cell — no silent failures.

---

## Known caveats (be honest with yourself while testing)

- **No pre-drawn button.** openpyxl can't add a Form-Control button from the
  build side, so the macro ships callable (Alt+F8) but unbuttoned. Add one in
  ~20 s as above, or ask and it can be injected.
- **Sparklines are macro-painted and Excel-unverified.** openpyxl can't write
  native sparklines, so they're added by `ExtractAndRun` after data lands. The
  routine is guarded (`On Error Resume Next`) so it can never break a refresh,
  but it has not been run in a real Excel — Test 3 is where you confirm it.
- **xlwings vs openpyxl.** The button uses xlwings to write into the *open*
  workbook; that's why it's required for Test 3. The openpyxl backend (Tests
  1–2) writes the *closed* file, so don't have the workbook open in Excel while
  running those.
- **If macros are blocked by policy,** the embedded VBA also lives as plain text
  in the `_code_vba` tab; you can import it (Developer ▸ Visual Basic ▸ import)
  if your environment ever strips the embedded project.

If anything in Test 3 misbehaves, copy the message-box / status text back here
and it can be diagnosed.
