# FRED Credit-Risk Dashboard Template

A reusable, self-contained Excel template that pulls credit-risk data from
**FRED** via Python, lands it raw, presents it as formula-driven dashboards, and
carries a commercial **geographic watchlist** lane — all source, config and docs
live *inside* the workbook so it can be emailed, opened anywhere, and re-run with
one button click.

The shipped artifact is **`FRED_Credit_Risk_Dashboard.xlsm`**. This folder holds
the build tooling that produces it (the workbook is the source of truth at run
time; this repo regenerates it).

## Build the workbook

```bash
pip install fredapi openpyxl pandas        # build deps
python3 make_workbook.py                    # -> FRED_Credit_Risk_Dashboard.xlsm
```

## Run / verify

```bash
pip install pytest oletools formulas        # verify deps
python3 -m pytest tests/ -q                 # 42 tests: transforms, validator, VBA, build
python3 email_sim.py                        # email-simulate the one-click acceptance test
# try the data path with no FRED key / no Excel:
python3 runner.py --workbook FRED_Credit_Risk_Dashboard.xlsm --backend openpyxl --demo
```

## Using it for real (work machine)

1. `pip install fredapi xlwings openpyxl pandas`
2. Get a free FRED key (https://fredaccount.stlouisfed.org/apikeys); set
   `FRED_API_KEY` or paste it into the workbook's `_config` tab.
3. Open the `.xlsm`, enable macros, click **Extract & Run** on `Dashboard_Consumer`.

Full end-user instructions are in the workbook's `_readme` tab.

## Files

| file | role |
|------|------|
| `runner.py` | **The data path** (embedded into `_code_py`): FRED provider adapter, transform registry, watchlist validator, fixed-anchor raw layout, xlwings/openpyxl backends. The one place FRED specifics live. |
| `series_seed.py` | Canonical seed of the `_config` series dictionary (147 series; state/metro/Case-Shiller expansion). Build-time only. |
| `macro.bas` | The VBA "Extract & Run" macro (embedded into `_code_vba` and into `vbaProject.bin`). |
| `build_workbook.py` | Assembles the base `.xlsx`: `_config`, raw scaffolds, formula-driven dashboards + watchlist, code/readme tabs, conditional-formatting heat. |
| `vba_writer.py` | Builds a real `vbaProject.bin` (MS-OVBA + MS-CFB) from `macro.bas`. |
| `assemble_xlsm.py` | Wraps the base `.xlsx` into the macro-enabled `.xlsm`. |
| `make_workbook.py` | One-shot: build + assemble. |
| `email_sim.py` | Reproduces the email→open→click acceptance test (workbook-as-source-of-truth). |
| `tests/` | `test_runner.py` (data path) + `test_build.py` (pipeline, VBA, refresh). |
| `BUILD_NOTES.md` | Design choices, VBA-embedding verification, deps + versions, series status. |

## Design rules (encoded, not preferences)

- **Watchlist boundary is a hard gate.** Only geographically-keyed house-price
  indices (FHFA state/metro, Case-Shiller) may feed `Watchlist_Geo`. Any
  charge-off/delinquency/G.19/DSR/SLOOS/CRE-price series marked
  watchlist-capable is refused with an error naming it.
- **Stateless.** Every refresh is a clean rebuild from FRED; no persisted state.
- **One provider, isolated.** FRED specifics live only in `runner.py`'s provider
  adapter so v2 can swap the source without touching dashboards or watchlist.
- **Workbook is the source of truth.** All Python/VBA/config/docs live in tabs as
  plain text; the `.xlsm` regenerates `runner.py` from `_code_py` on click.
- **Deterministic, no LLM in the data path.** Same FRED data → same workbook.
