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

### `fdic-demo.json`, 2026-09-05 — issue #259, a ratio on a book that does not exist

Bank of New York Mellon has no credit-card book. The FDIC publishes 0.00 for
its card delinquency rate, 0.00 is a number, and the Watchlist read **OK** —
"checked and clean" where the truth was "nothing to check". The firm's answer
on the docket: change it to N/A.

Two formula families moved, on every peer slot:

1. **The value cell of a direct class ratio** (card, auto, other consumer and
   1–4 family 30–89 / 90+ / nonaccrual rates — twelve metrics) now blanks
   when the class balance is zero or missing:
   `=IF(OR(ref="",bal="",bal=0),"",ref)` instead of `=IF(ref="","",ref)`.
   The engine's `metric_value` returns None for the same inputs, so the digest
   and the workbook still agree cell for cell.
2. **The Watchlist status helper** for every metric that stands on a book
   (the guarded directs above plus every declarative ratio) says `N/A` when
   that book is zero or missing, and `""` when there is a book but no number.
   Metrics with no single book (Texas, CRE concentration) are unchanged.

3,366 cells moved: 1,843 formula texts on `Dashboard_LoanBook` and
`Watchlist`, and 1,523 recomputed Watchlist helper *values* that went from
`""` to `N/A` -- the demo peer set does carry banks with empty classes. No
value moved to or from OK, WATCH or ALERT, and the flag counts the spine test
pins (50 ALERT, 47 WATCH) did not move. The golden
was confirmed to DETECT the change before it was re-banked. HELOC rates are
not guarded: no HELOC balance is landed, and the code says so rather than
guessing one.

### `fdic-demo.json`, 2026-09-05 (second re-bank) — the rename and the merger record

Two docket answers, in one re-bank so the golden moves once.

**D2, "rename ours."** The FDIC publishes nineteen of the twenty class ratios
this template computes — `NTCONOTQR`, `P3CONOTHR` and the rest — under exactly
the names it was using, and its versions divide by **average total assets**
where ours divide by the **loan class**. Same code, different ratio. Verified
live against the FDIC's published values (Capital One, CERT 4297, 2025-12-31):
their `P3CRCDR` of 0.861 is card 30-89 over total assets (0.861), not over the
card book (2.215). Ours are now `<numerator field>_BOOK` — `NTCONOTQ_BOOK`,
`P3CONOTH_BOOK` — which is not an FDIC code and names its own denominator. A
name shaped like an FDIC field is now always the FDIC's own number.

**D1, "merger flag only."** A new `_mergers` tab (contract §2, amended the
same day) carries the FDIC's own merger record for the peer set, written by
the runner on every live run. The trend tool blanks quarterly-flow rates for
a quarter that spans a merger and says why; balances and 30-89 / 90+ /
nonaccrual rates are untouched. The materiality floor built the day before was
removed: it hid the 670% by luck of the book size rather than recognising the
cause.

158 cells moved — 42 on `_config` and 77 on `_provenance` (the metric ids and
their formulas), 20 Watchlist helper headers, 17 on the new tab, plus the
sheet itself. No dashboard value moved and the flag counts the spine test pins
(50 ALERT, 47 WATCH) did not change: a rename is not a recalculation. The
golden was confirmed to DETECT all of it before it was re-banked.

### `fdic-demo.json`, 2026-09-05 (third re-bank) — #268, every class rate over its own book

The FDIC's published loan-class rates divide by **average total assets**. This
template landed fifteen of them — card, auto, resi, HELOC and C&I 30-89 / 90+
/ nonaccrual — and showed them on the loan-book dashboard beside the twenty it
computes over the class, under thresholds set for book rates. Capital One's
card 30-89 read 0.86 (of assets) where the card-book rate is 2.21, and card
30-89 watches at 2.5, so eight early-warning flags could not trip. The firm's
answer on the docket: compute over the book.

The fifteen ratio twins are no longer landed. In their place: the fifteen
dollar numerators (their MDRM codes were already in the provenance map, inside
the twin rows) plus `LNRELOC`, so HELOC finally has a book to stand on. 68 →
69 landed fields, and every one of the 35 loan-class rates is now
`numerator / its own class balance × 100`.

11,332 cells moved. Most of that is `Raw_FDIC` (8,755) where fifteen columns
changed identity and one was added, plus the formulas and ids on
`Dashboard_LoanBook`, `_provenance`, `Watchlist` and `_config`.

**No demo value actually changed.** The demo profile built each class rate
from a seeded percentage and landed the percentage; it now lands
`rate/100 × balance` and the engine divides by the same balance, so the
numbers come back identical — the 192 dashboard "value" diffs are the same
figures at full precision instead of the FDIC's four decimal places (1.6434 →
1.64341584569). The flag counts the spine test pins did not move: 50 ALERT,
47 WATCH, 2 alert banks, 2 watch banks. On live data the values do change,
because that is the point of the issue.

Also gone: the *guarded direct* metric added the day before for #259. It
existed to make a landed rate read None on a zero book; a ratio does that by
construction, so the machinery had no users and was removed with its tests
and mutations re-pointed at the ratio.

### `fdic-demo.json`, 2026-09-05 (fourth re-bank) — a tie-out found three wrong citations

Tying out one KeyBank figure end to end against the bank's own filed Call
Report (`docs/TIE-OUT-keybank-card-30-89-2026-09-05.md`) ran the filing check
over all 48 landed dollar lines. Three came back **NOT IN FILING**: `P3CI`,
`P9CI`, `NACI`. The provenance map cited MDRM `1606` / `1607` / `1608`, the
**form 041** codes. KeyBank files form **031**, which splits commercial and
industrial loans into 4.a (US) and 4.b (non-US), and the filing carries the
landed values under `RCFD1251` / `1252` / `1253`. The C&I *balance* row already
carried that 031 alternative; the past-due rows never had it.

9 cells moved, all on `_provenance` — three MDRM citations and their notes.
No value moved anywhere: the numbers were right and the citation was wrong,
which is exactly the failure a tie-out exists to find. 45 of 48 became 48 of 48.

### `fdic-demo.json`, 2026-09-05 (fifth re-bank) — five citations pinned to the domestic column

Tying all twelve banks to their own filed Call Reports returned **18 DIFFERS**:
every one a real-estate loan balance, every one at a bank with foreign
real-estate lending (JPMorgan, Citi, Wells, Bank of America, PNC, Goldman), and
every one with the filed figure larger than the landed one. The domestic column
matches the landed value to the dollar in all eighteen:

```
JPMorgan 1-4 family   landed        322,339,000
                      consolidated  325,722,000   (cited -- wrong column)
                      domestic      322,339,000   (the FDIC's basis -- matches)
```

The data was right and the citation was wrong. `RCON`/`RCFD` are a convention
this template resolves consolidated-first, correct for most lines and wrong for
these, and there was no way to pin a line to the domestic column. `filing.py`
now honours a `(domestic)` marker in the map, and the five RC-C real-estate
balances carry it: `LNRECONS`, `LNRENRES`, `LNREMULT`, `LNRERES`, `LNRELOC`.

It also reverses part of the 4 September fix, honestly: `LNREMULT` was given a
`(RCFD1460 031)` twin that day, verified against KeyBank — whose consolidated
and domestic columns happen to be equal. One bank agreed; twelve did not.

29 cells moved, all on `_provenance` — five MDRM citations and their notes. No
value moved anywhere. **576 of 576 dollar lines across twelve banks now tie,
0 differ.**
