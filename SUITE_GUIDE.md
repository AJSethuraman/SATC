# Suite Guide — the only two pages you need

Everything else in this repo is build tooling and specs. Day to day, this
is the whole manual.

## One-time setup (at your desk)

1. Get **`build_suite.py`** onto the machine (it's one pure-ASCII file —
   email it to yourself; nothing binary to mangle).
2. In PowerShell, in an empty folder:
   ```powershell
   python -m pip install pandas openpyxl
   python build_suite.py          # menu -- pick templates, or 'a' for all
   ```
   Each template lands in its own subfolder as a **demo-populated workbook**
   (dashboards already lit with synthetic data) plus a fallback `.xlsx` +
   `macro.bas` if your Excel rejects embedded macros.
3. ```powershell
   python control_center.py --doctor
   ```
   One command answers "will this machine work?": python deps, credential
   status, and which data hosts your proxy allows (with the exact
   hostnames to give IT if any are blocked). **Demo mode always works
   offline.**
4. Credentials — the whole surface is ONE free key + one identifier,
   stored in the workbooks themselves. Configure once, applied everywhere:
   ```powershell
   python control_center.py --configure fred_api_key "your-key"
   python control_center.py --configure edgar_user_agent "YourOrg you@bank.com"
   ```
   (Or the GUI's **Configure keys...** button — one dialog, both values.)
   FDIC, CFPB and NY Fed need nothing. The FRED key is free at
   fredaccount.stlouisfed.org/apikeys; the EDGAR value is just SEC's
   identify-yourself rule, not a secret.

## Daily driving

```powershell
python control_center.py
```
The GUI shows every workbook with its purpose, **last run, and alert counts
at a glance** (no need to open them). Pick one:

| Button | What it does |
|---|---|
| Refresh (Demo) | offline synthetic refresh — safe anytime |
| Refresh (Live) | pulls that template's real data (close the workbook first) |
| Refresh ALL (Demo) | one click, everything refreshed |
| Tie-out / verify... | prints each value beside its official document location (Call Report schedule/line + facsimile link; SEC accession + viewer link) |
| Doctor | re-run the environment check |

Prefer PowerShell? Same verbs: `--list`, `--run <name> --demo`,
`--run-all --demo`, `--tieout <name> <entity>`, `--doctor`.

## Which workbook answers which question

| Question | Workbook |
|---|---|
| How is national credit quality trending? Which geographies' collateral is softening? | FRED_Credit_Risk_Dashboard |
| Where is the consumer cycle by product (card/auto/mortgage/student)? | Consumer_Credit_Risk_Monitor |
| Is credit deterioration coming — and which states in the footprint turn first? | Macro_Early_Warning_Monitor |
| How do our peer/competitor banks stack up? Whose loan book is cracking? (consumer DQ track + SVB metrics) | Bank_Peer_Monitor |
| Is mortgage delinquency rising in our counties? | Mortgage_Delinquency_Monitor |
| Whose COMMERCIAL book is being risk-rated down (criticized/classified) — and who filed a covenant-breach 8-K? | Crit_Class_Tracker |

## Changing who/what you monitor

Open the workbook's **`_config`** tab. Your lists are just rows:
`[PEERS]` (banks, by CERT or CIK), `[FOOTPRINT]` (counties, by FIPS) —
edit a line, save, close, refresh. `--lookup "name"` on any template's
runner finds the id for you. Thresholds live in `[THRESHOLDS]` — numbers,
not code.

## Verifying a number (audit-style)

Every workbook has a **`_provenance`** tab (metric → source document →
schedule/line or note/tag → link). For a full sample check:
`Tie-out` button (or `--tieout`), then follow the printed link to the
bank's actual filed Call Report / 10-Q and compare by eye.

## When something looks wrong

1. `Doctor` — is it deps or a blocked host?
2. Was the workbook **open in Excel** during refresh? (Close it, rerun.)
3. Status panel (column L of the first dashboard) shows the last run,
   counts, fetch errors, and staleness/continuity warnings.
4. A frozen/absent number is usually the template being honest: STALE
   (stopped filing — merger?), SUPPRESSED (below sample threshold), or
   N/A (that bank's disclosure family doesn't support the metric).
   The `_readme` tab in each workbook explains its own caveats.

## Notes per source (the one-liners that matter)

- **FRED / Macro**: live needs `$env:FRED_API_KEY` (free). ICE-spread and
  UMich-sentiment tiles carry licensing labels — leave them as rendered.
- **FDIC**: keyless. Quarterly data lands ~35-60 days after quarter-end.
- **NY Fed HHDC**: demo works; live needs a one-time schema binding (see
  its _readme).
- **CFPB**: keyless; data lags ~6-7 months (confirming, not nowcasting);
  history revises each release — that's the source, not a bug.
- **EDGAR**: keyless but REQUIRES a User-Agent — put "YourOrg your.email"
  in its `_config` `edgar_user_agent` cell once. Q4 arrives via the 10-K
  (slower than Q1-Q3).
