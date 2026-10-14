# Economic data: the fourth helper (proposal stage)

Nothing in the tool reads this folder yet. It holds the proposal for adding
economic data (unemployment, house prices) to threshold-engine, and the
scripts and data behind every figure in it. Public data only.

| File | What it is |
|---|---|
| `PROPOSAL.md` | The proposal, copied from the Claude Doc the firm reads |
| `LOG.md` | This work's log (kept apart from the main LOG.md) |
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
