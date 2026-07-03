# County Mortgage Delinquency Monitor (v1)

A self-contained, macro-enabled Excel workbook
(`Mortgage_Delinquency_Monitor.xlsm`) for **county-level mortgage credit
OUTCOMES in your collateral footprint**: monthly 30-89 and 90+ DPD shares
from the **CFPB Mortgage Performance Trends** files (NMDB 5% sample) --
public domain, **KEYLESS** (no API key, no account; five small CSV
downloads). The leanest template in the series; the confirming counterpart
to the macro template's leading indicators (~6-7 months lagged by design).
Built to `TEMPLATE_CONTRACT.md`.

## The flexible footprint (the point of this template)

`[FOOTPRINT]` in `_config` is the watchlist, keyed by 5-digit county FIPS
(the FDIC template's `[PEERS]` slot mechanism, carried wholesale):

```
[FOOTPRINT]   slot | fips | name | state | active
```

- **Add a county**: fill a free slot row, re-run the runner. **No rebuild.**
  Find FIPS from PowerShell: `python runner.py --lookup "Cook"` (live greps
  the fetched county file; `--demo` searches an offline mini-index).
- **Remove a county**: `active=FALSE` (or clear the row) -- the slot blanks
  on the next run (stateless clearing).
- **Capacity** is a build knob (`make_workbook.py --footprint-slots N`,
  default 40). Over capacity the runner **refuses with the exact rebuild
  command** -- it never truncates.
- Raw anchors depend only on the **slot**; county identity flows into every
  tab **by formula** from the `[FOOTPRINT]` cells. Keep FIPS cells
  TEXT-formatted -- the CFPB quote-wraps them for exactly this reason.

## The lanes

| Tab | Content |
|-----|---------|
| `Dashboard_State` | National (pinned benchmark) + 15 provisioned state slots: latest / dev vs own 12m avg / 12m ASCII trend strip, both measures |
| `Dashboard_Trends` | National + worst-5 footprint counties by 90+ level (formula-ranked via LARGE/MATCH/INDEX), 24-month readout -- no charts |
| `Watchlist` | Footprint counties ranked by (status severity, 90+ dev): County \| State \| FIPS \| 30-89 latest \| dev 12m \| 90+ latest \| rise streak \| Status \| Rank |
| `Raw_CFPB` | One fixed-anchor block per geo slot (nat, st01-15, co01-40), 72 months x 2 measures, newest-first |

Thresholds (heuristic, honestly labeled, numeric `_config` cells): 30-89
dev-vs-12m-avg 0.3/0.6pp; 90+ rise streak 2/3 (capped); 90+ level 1.5/3.0%.
Red = rising delinquency everywhere.

## Suppression, vintages, continuity (the source's three sharp edges)

- **Suppression by omission**: only ~470 large counties clear the CFPB's
  ~1,000-sample-mortgage bar; absent counties render
  `SUPPRESSED (below sample threshold) -- use the state row`, excluded from
  every alert KPI. Absence is never zero. The demo deliberately omits one
  seeded county (King County WA) so this path is always visible.
- **Full-history revisions**: every vintage revises the ENTIRE history, so
  every run is a stateless FULL REPLACE and the vintage (`thru-YYYY-MM`,
  from the dated filename) is recorded in the status panel. Never diff
  vintages as movement.
- **Continuity tripwire**: the CFPB publishes informally (~semiannually,
  ~6-7 month lag, no promise -- it survived the 2025 turmoil once). A
  vintage more than `continuity_months` (default 9) behind `--asof` raises
  a CONTINUITY WARNING in the status panel and email. Filenames are DATED;
  the live provider discovers them by scraping the download page, with a
  `vintage` settings override if the page ever changes.

## Quick start (dev)

```bash
pip install pandas openpyxl
python3 make_workbook.py             # build the .xlsm (--footprint-slots N)
python3 -m pytest tests/ -q          # 16 tests, headless/offline
python3 email_sim.py                 # acceptance: ranked counties + states +
                                     #   vintage + suppression + continuity
python3 make_bundle.py               # the transmission artifact (below)
```

## Delivery to a locked-down machine

Send **`build_cfpb_monitor.py`** (one pure-ASCII file). On the target
machine, from PowerShell:

```powershell
python -m pip install pandas openpyxl
python build_cfpb_monitor.py
```

It locally builds the demo-populated `.xlsm` (macro embedded), a fallback
`.xlsx` + `macro.bas` (if Excel rejects the embedded project: open the
fallback, paste the macro via Alt+F11, save as `.xlsm`), `runner.py`, and
`requirements.txt`. Live refresh is **keyless**:
`python runner.py -w Mortgage_Delinquency_Monitor.xlsm`.
`control_center.py` (repo root) discovers and drives this template
automatically.

## Honest limits (v1)

- The **lag is the lag** (~6-7 months): a confirming indicator, never a
  nowcast.
- **Metro file is out** (mixed CBSA + synthetic non-metro keys -- no FIPS
  join); FHFA NMDB aggregates are only a partial fallback (state/CBSA,
  quarterly) if the program ever dies; no interpolation for suppressed
  counties, ever.
- Seeded counties are illustrative (01003/01073 verified verbatim in the
  inspected file); replace them with your own footprint. Demo stress
  counties are FICTION assigned by hand, stated in-sheet.
- Live path is fixture-tested only in this build environment (cfpb hosts
  proxy-blocked); the first live run is the remaining validation.

Provenance: `COVERAGE_RESEARCH_CFPB.md` (verified source research) ->
`BUILD_SPEC_CFPB.md` (binding spec) -> this build. Decisions and
verification in `BUILD_NOTES.md`.
