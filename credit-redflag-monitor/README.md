# Consumer Credit Red-Flag Monitor (External Signals v1)

A deterministic, config-driven Python tool that:

1. Pulls external macro / rate / consumer-credit signals from **FRED** on a monthly cadence,
2. Compares each signal to its prior **valid** reading against a configured threshold,
3. Auto-flags moves that breach threshold,
4. Writes an **Excel** workbook where the consumer team dispositions whether each flagged move *matters* to their book.

**No AI/ML anywhere in the compute path.** All flagging is pure threshold logic. All *judgment* is human — the team fills a `Matters? (Y/N)` column. The tool reports and flags; people decide. This separation is intentional and non-negotiable.

---

## Quick start

```bash
# from this directory
pip install -e .            # installs openpyxl + requests
# or: pip install openpyxl requests

# Offline demo — deterministic synthetic data, no API key or network needed:
python redflag_monitor.py --demo

# Live monthly run (needs a free FRED key):
export FRED_API_KEY=your_key_here     # https://fredaccount.stlouisfed.org/apikeys
python redflag_monitor.py
```

A run produces `credit_redflag_monitor.xlsx` (the disposition workbook) and appends to `signal_history.csv` (the time-series log).

### CLI options

| Flag | Meaning |
|---|---|
| `--demo` | Use deterministic synthetic data (no key/network). |
| `--workbook PATH` | Output workbook path (default `credit_redflag_monitor.xlsx`). |
| `--history PATH` | History CSV path (default `signal_history.csv`). |
| `--run-date YYYY-MM-DD` | Override the run date (defaults to today). |
| `--no-news` | Omit the optional `News (manual)` stub sheet. |

---

## The monthly loop

1. Someone runs `python redflag_monitor.py` once a month.
2. They open the workbook; the team dispositions each auto-flagged row (`Matters? (Y/N)`, notes, owner, reviewed).
3. The owner tunes thresholds directly in the `Signal Dictionary` sheet as noise reveals itself — **no code change required.**
4. Next run reads the tuned dictionary and **preserves every prior disposition.**

---

## Workbook layout

| Sheet | Purpose |
|---|---|
| `Flags` | One row per signal/observation-period — the disposition surface. `Matters?` has a Y/N dropdown; auto-flagged rows get a red fill. The last four columns are team-filled and **carry forward across runs**. |
| `All Signals (History)` | Every signal, every run — the append-only time-series log, so the team sees 3-month creep, not just a snapshot. |
| `Signal Dictionary` | The editable config (schema below). The owner tunes thresholds here; the engine reads it next run. Created from the seed set on first run, never clobbered after. |
| `Internal (paste)` | Empty, same shape as `Flags`. Drop internal flags (segment growth, book losses) here so internal + external get dispositioned together — this is what enables "our book vs. the industry". |
| `News (manual)` | Optional paste tab for headlines (human skim). No scraping. |

---

## Signal Dictionary schema

One row = one signal. Edit in the workbook's `Signal Dictionary` sheet, or supply a sibling CSV (see `examples/signal_dictionary.csv`).

| Field | Meaning |
|---|---|
| `series_id` | FRED series ID |
| `label` | Human-readable name |
| `category` | `Rate` / `Macro` / `Credit-Benchmark` / `Internal` |
| `source` | `FRED` |
| `native_frequency` | `daily` / `monthly` / `quarterly` |
| `threshold_type` | see below |
| `threshold_value` | numeric |
| `direction_that_matters` | `up` / `down` / `both` |
| `active` | `Y` / `N` |
| `notes` | why it matters / context |

**`threshold_type` options:**

- `abs_change` — flag if `|current − prior| ≥ value`
- `pct_change` — flag if `|% change vs prior| ≥ value`
- `level_above` / `level_below` — flag if current breaches an absolute level
- `yoy_change` — flag if change vs same period prior year `≥ value` (for noisy/seasonal credit series)

`direction_that_matters` gates change-based flags: `up` only fires on increases, `down` only on decreases, `both` on either. The magnitude test still has to pass.

The seed set (14 verified FRED series across rates, macro, and consumer-credit benchmarks) is materialized into the dictionary on first run.

---

## Architecture

Five components, mirrored in `src/redflag_monitor/`:

| Component | Module | Responsibility |
|---|---|---|
| Config loader | `config.py`, `seed.py` | Read/validate the Signal Dictionary; materialize the seed set. |
| FRED fetcher | `fred.py` | Pull observations; robust to FRED missing-value behavior. |
| Metric engine | `metrics.py` | Clean → derive current/prior valid → compute change → apply threshold → set auto-flag. Pure, deterministic, fully unit-tested. |
| History store | `history.py` | Append each run's latest reading to a persisted CSV log. |
| Excel writer | `excel_writer.py` | Produce/refresh the workbook and **preserve prior human dispositions.** |

`monitor.py` wires them together; `cli.py` is the entry point.

### Implementation notes (the tricky parts)

- **FRED missing values (§7.1):** the API returns `"."` for missing periods. Several "monthly"-labeled series (notably `TERMCBCCALLNS`) actually populate only quarterly. We always parse `"."` to `None` and take the last two *valid* observations — never a naive "last row."
- **Mixed frequencies (§7.2):** every signal normalizes to "latest valid value + `as_of` date." A quarterly series is unchanged in 2 of every 3 monthly runs — expected, not a flag, and never blank.
- **Disposition persistence (§7.3):** each disposition row is keyed by `(series_id, observation_period)`. On re-run we match existing rows, preserve the human columns, update only the data columns, and append rows for new periods. We never clobber a human cell.
- **Threshold logic lives in config (§7.4):** the engine branches on `threshold_type`; adding or retuning a signal never touches code.
- **Vintage / revisions (§7.5):** the history log persists both the value and the `retrieved_date` alongside the observation period.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

The metric engine and the disposition-persistence layer are the highest-value tests:
`tests/test_metrics.py` covers every threshold branch and direction; `tests/test_persistence.py`
runs the acceptance test from the spec (run twice, dispositions survive).

No network is required for the test suite — FRED access is isolated behind an injectable
requester and the demo client.
