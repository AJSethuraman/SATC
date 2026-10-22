# Economic data

On 14 Oct 2026 the firm redirected the work: economic data is its own
subject, read by a separate tool built on the same idea, not a helper to
KeyBank's loss thresholds (see `LOG.md`). Since 22 Oct 2026 it rates nothing:
each series shows where it sits in its own history and whether its change is
Increasing, Stable or Decreasing against its normal movement. That tool is
`src/threshold_engine/macro/`; what it does and how to run it is in
`TOOL.md`. Its tests read two files here: the report (every series must cite
a section it has) and the settings template. The earlier proposal, and the
scripts and data behind it, are kept below for the record. Public data only.

| File | What it is |
|---|---|
| `TOOL.md` | The economic conditions tool: what works, how each series is read, what was checked, what waits on the firm |
| `settings-template.json` | The tool's settings, every answer empty, with a recommendation beside each |
| `settings.json` | The firm's answers (16 and 22 Oct 2026), each with where it came from |
| `what-if-pandemic-left-out.json` | An example what-if, not the firm's settings: theirs with 2020 Q2 to 2021 Q2 left out |
| `what-if-30-years.json` | Another example what-if: theirs with history set to the last 30 years |
| `examples/` | The workbook from the pull of 22 Oct 2026 (folder `2026-10-22-3`) with the pandemic what-if, its printout, and four screenshots of it: the Overview, the Dashboard, household debt, and the initial claims charts with the 2020 spike off the axis |
| `walkthrough/` | The walk of the monthly refresh: the procedure as one PDF, and the defects it found |
| `tie-out/gasoline-change-2026-10-16/` | The workbook's top reading tied to EIA, with three more tied to BLS, FRED and FHFA, as one PDF |
| `LOG.md` | This work's log (kept apart from the main LOG.md) |
| `PROPOSAL.md` | The earlier proposal, copied from the Claude Doc the firm reads |
| `reports/Macro risk indicators for lending.md` | Which public economic series banks and regulators use for a macro risk narrative, how to get each, and how to flag an unusual reading (14 Oct 2026) |
| `research_notes/Macro risk indicators for lending/` | The five research strands behind that report, every claim linked |
| `data/card_losses_and_unemployment_change.csv` | Chart 1: Fed card charge-off rate (four-quarter mean) and the four-quarter change in unemployment, 1986Q1–2026Q2 |
| `data/unemployment_bands_card_losses_1985_2019.csv` | Chart 2: card losses four quarters later, by unemployment band |
| `analysis/fetch.py` | Downloads every public file used. No API key is used or needed |
| `analysis/analyse.py` | Lead and lag by product, recession turning points, unemployment bands |
| `analysis/sensitivity.py` | Loss rise per point of unemployment, recession by recession; out-of-sample fits |
| `analysis/geo.py` | KeyBank's deposit footprint against national unemployment |
| `analysis/chart_data.py` | Writes the two chart files from `analyse.py`'s output |

## Rebuilding it

Run every command from `threshold-engine/`. Outputs go under `work/`.
Standard library only.

```
python docs/macro/analysis/fetch.py --sources work/macro-sources
python docs/macro/analysis/analyse.py .. work/macro-sources work/macro-analysis.json
python docs/macro/analysis/sensitivity.py work/macro-analysis.json work/macro-sensitivity.json
python docs/macro/analysis/geo.py --sources work/macro-sources --states ../credit-suite/verified-data/macro-observations.csv --out work/macro-geo.json
python docs/macro/analysis/chart_data.py work/macro-analysis.json work/macro-data
```

The two files `chart_data.py` writes are byte-identical to `data/` (checked
14 Oct 2026).

`analyse.py` also reads the tool's own public loss series
(`tests/data/*.csv`) and the repository's verified series
(`../credit-suite/verified-data/macro-observations.csv`).
