# credit-suite

**One engine behind the Credit-Risk Template Suite.** Each monitor is a provider
adapter plus a config seed; everything else is shared and written once.

- **Spec:** [`docs/prd-credit-suite-consolidation.md`](docs/prd-credit-suite-consolidation.md)
- **Contract every monitor obeys:** [`../TEMPLATE_CONTRACT.md`](../TEMPLATE_CONTRACT.md)
- **Roadmap (M2–M4):** [`../BACKLOG.md` §6](../BACKLOG.md)

## Why this exists

The suite is six shipped, emailable `.xlsm` monitors. They already shared one
*written* abstraction — the template contract — but only by convention and
copy-paste. Every monitor re-implemented the same workbook builder, house style,
threshold engine, watchlist gate, VBA emitter and ASCII bundler, and FRED was
implemented twice. A fix, or a carried lesson, had to be hand-propagated to six
folders, and one of them had already drifted.

That is a single failure shape: **a claim in one place, the behaviour in
another, and nothing comparing them.** Consolidating removes the copies;
`conformance.py` stops them coming back.

## The split

```
credit_suite/
  engine/          written once, imported by every source
    config.py        the _config tab: settings, thresholds, series, entity slots
    gates.py         the watchlist gate -- default-deny, three gates
    thresholds.py    OK / WATCH / ALERT, direction-aware
    staleness.py     "fetch success is not data currency"
    metrics.py       the metric registry and its ratio helpers
    rawlayout.py     fixed block anchors, shared with the builders
    provider.py      the fetch_series seam + the Class C rehearsal stub
    workbook.py      the openpyxl writer (carries L2 and L7)
    digest.py        per-entity values, statuses and flag counts
    runtime.py       gate -> blank -> fetch -> land -> digest
    style.py         the house style; no hardcoded fill or font in a builder
    vba.py           the VBA project container writer
    package.py       .xlsx + macro -> .xlsm, by zip surgery
    inline.py        the build-time inliner (see "How it still travels")
  sources/
    fdic/            adapter + fields + spec + layout + runner
    fred/            the same, grandfathered where parity pins it
  parity.py        the golden harness
  conformance.py   has the duplication crept back?
```

**The engine never imports a source.** Sources depend on the engine, and the
conformance check fails if that inverts.

## The seam

One function, and everything source-specific lives behind it
(`TEMPLATE_CONTRACT.md` §6):

```python
fetch_series(spec, secret=None) -> list[NormalizedRow]

NormalizedRow = {id, period, value, geo_segment, source_class, units}
```

Two implementations are mandatory per source: the live adapter, and a
deterministic offline `DemoProvider` that needs no key and no network. Every
test uses the demo one, which is why the whole verification bar runs on an
aeroplane.

FDIC's one bulk BankFind call, FRED's `.`-means-missing coercion and rate-limit
backoff, EDGAR's two-stage fetch — all of that stays on the source side. The
engine sees only rows.

FRED is the interesting case. It predates the contract and speaks pandas, so its
adapter **translates**: `fetch_series` emits `NormalizedRow`s and the runner
rebuilds the Series from them. The seam is on the data path, not bolted beside
it, and the round trip is asserted lossless observation by observation.

## Adding a source

The success metric is *one adapter and a config, zero engine edits*.

1. **`sources/<name>/spec.py`** — a `MonitorSpec`. This is where the monitor's
   vocabulary lives: what its entity key is called and what pattern admits it,
   which source classes the gated lane takes, how long a period is for the
   staleness math, and the refusal prose. A message about FDIC certificates
   would be nonsense in the EDGAR monitor, so the voice belongs to the source.
2. **`sources/<name>/fields.py`** — the field table, the declarative ratio table
   and the metric registry. The ratio table drives *both* the Python function
   and the Excel formula, so the two cannot drift.
3. **`sources/<name>/adapter.py`** — the live provider and the demo provider.
4. **`sources/<name>/layout.py`** — the dashboards and the gated lane.
5. **`sources/<name>/runner.py`** — status wording, any digest annotations, the CLI.
6. **`bundles.py`** — one `BundleSpec` entry so the inliner can ship it.

If you find yourself editing `engine/`, that is the signal to ask whether the
thing you need is genuinely shared or genuinely yours.

## How it still travels

Corporate email rewrites or blocks binary attachments; plain text survives. So
the workbook is never transmitted — one pure-ASCII script is, and the workbook is
*built* where it will live (contract §11).

Sharing an engine threatened that, because a monitor no longer carries its own
runner to embed. `engine/inline.py` walks the import graph from a source's entry
modules, collects every `credit_suite` module it reaches, and emits them into one
file that registers them in `sys.modules` under their **real dotted names** before
executing them in dependency order. The inlined code's own
`from credit_suite.engine.config import …` then resolves against that registry —
nothing is rewritten to travel, so the code that ships is the code that was
tested.

```
python tools/make_bundle.py                  # both spine monitors
python tools/make_bundle.py fdic -o .        # one, into a directory
```

The bundle is byte-identical run to run (gzip's header timestamp is pinned to
zero — without that, "did this change?" has no answer). `_code_py` carries the
same inlined runner, so the VBA button's output runs alone too.

## Running the verification bar

```
cd credit-suite
python -m pytest -q                    # the whole bar
python tools/check_parity.py           # values + statuses vs the goldens
python tools/conformance.py            # has duplication crept back?
python tools/mutation_check.py         # can each test actually fail?
```

What each one is for:

| | |
|---|---|
| `pytest` | contract §9: config parse, demo determinism, idempotence, transforms vs hardcoded expected values, reload with `keep_vba`, no native charts, watchlist refusal + defence in depth, raw-layout refusal, olevba decompile, OPC package audit, and the empty-folder email simulation |
| `check_parity.py` | builds each monitor, **recomputes every formula**, and diffs cell for cell against the pre-consolidation golden. Statuses are formula-driven, so a raw-cell snapshot would read `=IF(...)` and miss a status moving underneath it — which is carried lesson L8 |
| `conformance.py` | no copy of an engine module (content-hashed, so renaming does not hide one), no loose source in a migrated folder, tabs match §2, CLI and exit codes match §4 |
| `mutation_check.py` | breaks each guard on purpose and demands the test go red. A survivor is a finding: either the guard is decoration or the test is too weak |

Every one of them reports its denominator. A green check that examined nothing
looks exactly like a green check that examined everything.

### The goldens

`tests/goldens/` holds four files captured from the monitors **before** any
consolidation, and they are read-only from here on — see
[`tests/goldens/README.md`](tests/goldens/README.md). Two per monitor, because
the shipped `.xlsm` is an *unpopulated* template: it pins the shape, and only the
demo golden pins values and statuses.

Do not recapture a golden to make a failing parity test pass. The diff is the
signal. Recapture only when an output is *deliberately* changed, and say so in
the commit.

## What is not here

- **`credit-review-os`** is a separate product. It carries borrower PII and AES
  encryption the public-data monitors do not. It may consume patterns; it never
  merges.
- **Live licensed (Class C) feeds** stay gated. `ClassCStubProvider` rehearses
  the seam without making a call, and exists so the gate is testable — delete it
  and the gate can only be proven by the absence of code.
- **The other four monitors.** Bureau, macro, CFPB and EDGAR migrate in M2; the
  conformance check lists their outstanding copies rather than hiding them.

## Data handling

Public regulatory data only — FRED, FDIC Call Reports, EDGAR, CFPB, BLS. No
client PII anywhere. The only secret is an optional API key read from the
environment variable named in `[SETTINGS] secret_env`; the value is never written
to a tab, a bundle or a workbook.
