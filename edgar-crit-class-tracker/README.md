# EDGAR Criticized/Classified Tracker

**Whose commercial book is being risk-rated down -- before delinquency shows
it?** One self-contained Excel workbook (`Crit_Class_Tracker.xlsm`) pulls each
competitor holding company's own filed 10-Q/10-K **Credit Quality Indicators**
note (ASC 326-20-50-5: amortized cost by internal credit grade x loan class,
quarterly) straight from SEC EDGAR -- keyless, public domain -- plus an
**8-K credit-event lane** (2.04 debt acceleration, 2.06 impairment, 4.02
non-reliance, 1.03 receivership), and renders criticized/classified ratios,
migration deltas, class mix, and a ranked Watchlist.

This is the **commercial half** of the two-track competitor surveillance
design: the FDIC Bank Peer Monitor carries the consumer DQ/NCO track and the
commercial Call-Report floor; this tracker carries the criticized/classified
view commercial ratings show **before** delinquency.

Spec: `BUILD_SPEC_EDGAR.md` (binding). Research: `COVERAGE_RESEARCH_EDGAR.md`.
Contract: `../TEMPLATE_CONTRACT.md`. Build details: `BUILD_NOTES.md`.

## Quick start

```
pip install pandas openpyxl
python3 make_workbook.py                 # build Crit_Class_Tracker.xlsm
python3 runner.py -w Crit_Class_Tracker.xlsm --demo     # offline demo fill
```

Live runs are **keyless** but REQUIRE `edgar_user_agent` set in the `_config`
tab to `"{your org} {your email}"` (SEC fair-access policy; a blank/generic
User-Agent earns silent 403s and a ~10-minute IP block):

```
python3 runner.py -w Crit_Class_Tracker.xlsm                       # live
python3 runner.py -w Crit_Class_Tracker.xlsm --lookup "Frost"      # name->CIK
python3 runner.py -w Crit_Class_Tracker.xlsm --tieout 35527 2026Q1 # verify
python3 runner.py -w Crit_Class_Tracker.xlsm --selftest            # proxy check
python3 email_sim.py                                               # acceptance
python3 -m pytest tests/ -q                                        # 16 tests
python3 make_bundle.py                   # -> build_edgar_tracker.py (ASCII)
```

In Excel: Alt+F8 -> `ExtractFiles` writes `runner.py` + `requirements.txt` +
`RUN.txt` next to the workbook. Nothing ever runs inside Excel.

## The core honesty mechanism

Banks disclose commercial credit quality in **dialects**. Each bank carries a
family flag derived from its `_config` `[MEMBER_MAP]` rows:

| family | disclosure | metrics |
|---|---|---|
| `grades_full` | Pass/SM/Substandard/Doubtful(/Loss) | Tier 1 + Tier 2 |
| `criticized_only` | Pass/Criticized-accruing/-nonaccruing (KeyCorp, M&T) | Tier 1 only; SM/classified render **N/A (family)** |
| `ig_nig` | Investment/Non-investment grade only (USB, JPM) | everything **N/A**; MD&A text fallback is v1.1 |
| `unmapped` | not yet mapped | N/A until mapped |

Members not in `[MEMBER_MAP]` bootstrap in as `grade="unmapped"` (visible,
flagged, **never guessed**); map them by hand and re-run. Same for class
members in `[CLASS_MAP]`.

## Files

| file | role |
|---|---|
| `runner.py` | the data path (embedded in `_code_py`): EdgarProvider (live, two-stage) + EdgarDemoProvider, metric engine, gates, staleness, `--tieout/--lookup/--selftest` |
| `build_workbook.py` | workbook builder (formulas, tabs, style) |
| `member_seed.py` | `_config` seeds: 10 research-verified peers + member/class maps + thresholds |
| `provenance_seed.py` | `_provenance` tab content incl. QUOTED uniform interagency definitions |
| `macro.bas` / `assemble_xlsm.py` / `vba_writer.py` | extract-only macro `CritClassTracker` + VBA embedding |
| `make_workbook.py` / `make_bundle.py` | build the .xlsm / the pure-ASCII transmission bundle |
| `email_sim.py` | acceptance: extract-run-compose against a fresh folder |
| `tests/test_runner.py` | the 16 named headless tests (no network) |
