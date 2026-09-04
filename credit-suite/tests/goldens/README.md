# Parity goldens — the M1 consolidation safety net

These four files are the answer to one question: *did consolidating the suite
onto a shared engine move a number headed for KeyBank?*

They were captured from the **pre-consolidation** monitors (issue #164, Slice 0)
and are read-only from here on. A migrated monitor must reproduce them
cell-for-cell.

| File | What it is |
|---|---|
| `fdic-shipped.json` | `fdic-peer-monitor/Bank_Peer_Monitor.xlsm` exactly as committed |
| `fdic-demo.json` | the same monitor built fresh and run `--demo --asof 2026-03-31` |
| `fred-shipped.json` | `fred-credit-risk-dashboard/FRED_Credit_Risk_Dashboard.xlsm` as committed |
| `fred-demo.json` | the same monitor built fresh and run `--demo --asof 2026-03-01` |

**Why two per monitor.** The shipped `.xlsm` is an *unpopulated template* — it
was built and never run, so every raw block in it is empty. It pins the shape
(formulas, config, labels, defined names) and nothing else; it cannot pin a
status, because no status in it is lit. The demo golden is the one with data in
it, so it is the one that pins values and statuses. `test_parity.py` refuses a
demo golden whose flag column does not actually discriminate — a vacuous
baseline would pass every future check while proving nothing.

**What a cell looks like.** One cell per line, so `git diff` of a golden reads
as a list of changed cells:

```
"Watchlist!H10": ["ALERT", "=IF(_config!$C$77=\"\",\"\",IF(...))"]
"Watchlist!B10": [1836000.0]
```

A formula cell stores `[computed_value, formula_text]`; a literal stores
`[value]`. The computed value comes from the `formulas` engine, because statuses
are formula-driven — a raw-cell snapshot would record `=IF(...)` and be blind to
the status underneath it moving, which is exactly carried lesson L8.

**Known gap.** The recalc engine does not implement `HYPERLINK` (see
`parity.UNSUPPORTED_FUNCTIONS`), so FRED's 146 provenance-link cells resolve to
`#NAME?`. That costs parity nothing: the result is deterministic and identical on
both sides of a comparison, and the *formula text* is compared too, so a changed
URL is still caught. `test_every_unpinned_formula_is_one_the_engine_documents_it_cannot_run`
fails if that list ever silently grows.

## Recapturing

Don't — not to make a failing parity test pass. A diff against these files is
the signal. Recapture only when a monitor's output is *deliberately* changed,
and say so in the commit.

```
python tools/capture_baselines.py              # both monitors, all four goldens
python tools/capture_baselines.py fred         # one monitor
```

The tool drives each monitor's own legacy `make_workbook.py` + `runner.py`, so
it stops working once those are deleted by the migration — by then these files
are the record.

## Proving the harness can fail

```
python tools/mutation_check.py                 # 17 mutations, all must be killed
python tools/mutation_check.py --list
```

Each mutation neuters one behaviour (drop the recalc, blind the value diff,
tamper with a golden) and names the tests that must go red because of it.
