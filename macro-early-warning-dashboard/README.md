# Macro Early-Warning Monitor (v1)

A self-contained, macro-enabled Excel workbook
(`Macro_Early_Warning_Monitor.xlsm`) of **credit-cycle early-warning signals
for credit-risk review**, pulled from FRED. National lanes time the cycle;
a **state-keyed watchlist ranks all 50 states + DC by labor-market stress**
that a loan portfolio's footprint can join on. Third template in the series;
built to `TEMPLATE_CONTRACT.md`.

## Why these signals (the credit-risk framing)

| Lane | Signals | What it leads |
|------|---------|---------------|
| `Dashboard_Conditions` | Yield-curve spreads, HY/IG OAS (display-only), NFCI/ANFCI/STLFSI4, SLOOS C&I tightening | Cycle position, wholesale credit pricing, the underwriting cycle |
| `Dashboard_Labor` | Sahm rule (real-time + revised), initial/continued claims (4-wk MA) | Unemployment → consumer delinquency, the strongest lead |
| `Dashboard_Housing_Sentiment` | Permits/starts (3-mo smoothed), UMich sentiment (1-mo delayed), core capex orders, recession probability (confirmatory) | Demand and confirmation lanes |
| `Watchlist` | Per-state: UR **Sahm-style stress gap**, claims YoY of 4-wk MA, Philly Fed coincident 3-mo change, ranked | *Which states in the footprint deteriorate first* |

## The watchlist is OPEN in this template

Unlike the bureau template (gated pending a licensed feed), this lane admits
151 verified state-keyed series — 51 `{ST}UR`, 50 `{ST}ICLAIMS`, 50 `{ST}PHCI`
— through the same default-deny validator: `watchlist_capable=TRUE` AND
`source_class="A"` AND `geo_segment` matching `^state:[A-Z]{2}$`. National
aggregates are refused by name. **Staleness is a first-class failure**: the
runner checks every series' last observation against its cadence (the
discontinued-but-still-serving Philly Fed leading indexes are the cautionary
tale) and stale rows are flagged and excluded from alert counts.

## Quick start (dev)

```bash
pip install pandas openpyxl
python3 make_workbook.py            # build the .xlsm
python3 -m pytest tests/ -q         # 16 tests, headless/offline
python3 email_sim.py                # acceptance: alerts + state ranking + staleness
python3 make_bundle.py              # the transmission artifact (below)
```

## Delivery to a locked-down machine

Send **`build_macro_monitor.py`** (one pure-ASCII file). On the target
machine, from PowerShell:

```powershell
python -m pip install pandas openpyxl
python build_macro_monitor.py
```

It locally builds the demo-populated `.xlsm` (macro embedded), a fallback
`.xlsx` + `macro.bas` (if Excel rejects the embedded project: open the
fallback, paste the macro via Alt+F11, save as `.xlsm`), `runner.py`, and
`requirements.txt`. Live data: `$env:FRED_API_KEY = "your_key"` then run
`runner.py` per `RUN.txt`. `control_center.py` (repo root) discovers and
drives this template automatically.

## Licensing flags (carried in `_config` notes + `_readme`)

- **ICE BofA OAS** (`BAMLH0A0HYM2`, `BAMLC0A0CM`): display-only, attribution
  required, FRED serves ~3-year window from Apr 2026 — thresholds are static
  references, never computed percentiles; flag-for-legal before wide sharing.
- **UMich sentiment** (`UMCSENT`): source-mandated 1-month delay — the tile is
  labeled "as of prior month"; attribution required.

Provenance: `COVERAGE_RESEARCH_MACRO.md` (verified series research) →
`BUILD_SPEC_MACRO.md` (binding spec) → this build. Decisions and verification
in `BUILD_NOTES.md`.
