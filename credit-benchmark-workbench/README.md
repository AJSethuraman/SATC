# Commercial Credit Benchmark Workbench

Benchmarking toolkit for an independent credit-risk-review (challenge)
function: EDGAR public-company financials → normalized, provenance-carrying
benchmark library → size-/survivorship-adjusted peer distributions → an
interactive workbench that overlays a private middle-market borrower and
exports a defensible, source-anchored review memo.

Public data builds **benchmarks and assumption sets only — never direct
comps** for private names.

## Layout

```
pipeline/      Python package (ccbw) + 110 tests
  src/ccbw/    edgar_client, tags, parse, panel, segments, metrics,
               benchmarks, adjust, mechanisms, overlay, validate, synth,
               snapshot, cli
data/          benchmark_snapshot_v1.json   (versioned snapshot, SYNTHETIC_DEMO)
               validation_report.md/.json   (backtest + rule comparison)
               sample_borrower.json         (paste-ready worked example)
workbench/     CreditBenchmarkWorkbench.jsx (single-file React artifact,
                                             snapshot baked in)
               workbench.html               (standalone browser build)
               make_html.py, tests/         (smoke harness)
docs/          methodology_memo.md          (the full methodology + caveats)
               worked_example.md            (Meridian Fabrication walkthrough)
               sample_memo_export.md        (actual GUI memo export)
```

## Quickstart

```bash
cd pipeline
pip install -e .[dev]
python -m pytest                          # 110 tests

# regenerate the demo snapshot + validation report + bake into the GUI
python -m ccbw demo-snapshot \
    --out ../data/benchmark_snapshot_v1.json \
    --validation-out ../data/validation_report.md \
    --bake ../workbench/CreditBenchmarkWorkbench.jsx
python ../workbench/make_html.py          # regenerate standalone HTML
```

Open `workbench/workbench.html` in a browser (CDN access needed for React/
Babel), or use the JSX as a single-file React artifact. Click **Sample** for
the worked example; **Paste** accepts `data/sample_borrower.json`.

GUI smoke tests (33 interaction checks via jsdom):

```bash
cd workbench/tests && npm install && npm test
```

## Live EDGAR refresh

This snapshot is labeled **SYNTHETIC_DEMO**: the build environment could
not reach `data.sec.gov` (network allowlist), so the demonstration data is
a deterministic synthetic corpus shaped like CompanyFacts and run through
the identical parse→panel→benchmark path. On a machine with EDGAR access:

```bash
cd pipeline
python -m ccbw build-live --user-agent "Your Name you@bank.com" \
    --out ../data/benchmark_snapshot_v2.json \
    --validation-out ../data/validation_report.md \
    --bake ../workbench/CreditBenchmarkWorkbench.jsx
```

See `docs/methodology_memo.md` §10 for the full refresh runbook, and the
memo generally for every judgment call (tag fallback chains, restatement
policy, fiscal alignment, winsorization, the adjustment engine's tunable
parameters, and validation caveats).
