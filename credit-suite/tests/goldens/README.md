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

## When a golden is re-banked on purpose

A golden that moves is normally a defect. Twice now it has been the point, so
the reason lives here rather than in a commit message somebody has to go find.

### `fred-demo.json`, 2026-09-04 — issue #181

Eleven of the eighteen metro house-price series were pulling ids FRED does not
publish. FHFA publishes those metros at metropolitan *division* level, and the
seed derived every id from the CBSA code, so a live pull 404'd eleven times
while the whole offline bar stayed green.

Fixing the ids changes the seed, so it changes the demo workbook: the metro
labels, the series ids, and every demo figure derived from them (the demo
provider is deterministic in the series id, so a different id is a different
number by construction). 846-plus cells moved on `Watchlist_Geo` alone.

That is a deliberate output change, approved before it was made, and the golden
was re-banked *after* confirming it detected the change first. The
pre-consolidation FRED shipped golden is untouched — it still pins the shape.

Re-banking now runs through `monitorbuild.built_monitor`, not
`capture_baselines.py`: the legacy runners that tool drives were deleted by the
migration, so it can no longer produce a FRED baseline.

### `fred-demo.json`, 2026-09-04 (second re-bank) — staleness + retired series

Two approved changes in one build, both of which move cells by design:

1. **Five series retired.** `FODSP` (FRED marks it DISCONTINUED, last published
   July 2023), `COMREPUSQ159N` (stalled April 2025; superseded by
   `BOGZ1FL075035503Q`, already in the seed), and three FHFA metro house-price
   series stalled at October 2024 — Washington, Atlanta and Tampa. Each was
   checked against the FRED `series` endpoint for a live successor; none exists.
   The seed count goes 147 → 142. The reasons live in `series_seed.RETIRED`
   rather than only here, because the next person extending that file is exactly
   who needs them.

2. **A publication-lag allowance per category**, added to `[SETTINGS]` as
   `lag_days.<category>`. That adds rows to the `_config` tab, which moves
   everything below them.

The golden was confirmed to DETECT both before it was re-banked. The
pre-consolidation FRED shipped golden is untouched.
