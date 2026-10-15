# Peers: the build spec (12 Oct 2026)

The bank decided on 12 Oct that version 1 includes every side analysis, built
into the tool and tested: *"Nope, all of it. Test it and make sure it works."*
This is the contract the modules are built to. Each module owns its own files
and nothing else. Every number marked **acceptance** was produced earlier by a
separate script, so reproducing it is a real tie-out, not the code agreeing
with itself.

Public data only. Nothing from KeyBank's books, ever. Every setting that is a
judgement is a required argument with no default.

## Data as it arrives

The FDIC BankFind API (`https://banks.data.fdic.gov/api/financials`), one
request per quarter-end `REPDTE` (YYYYMMDD), every filer, paginated 10,000 rows
at a time. A row is a dict: `CERT`, `REPDTE` and the requested fields. Amounts
are **$ thousands**; charge-off (`DR*`) and recovery (`CR*`) fields are
**year-to-date**; balances (`LN*`) are quarter-end.

| Product | Balance | Gross charge-offs (YTD) | Recoveries (YTD) | Since |
|---|---|---|---|---|
| Credit card | LNCRCD | DRCRCD | CRCRCD | 2001 |
| Mortgage (1–4 family first liens) | LNRERSFM | DRRERSFM | CRRERSFM | balance 1992, flows 2003Q2 |
| Home equity | LNRELOC | DRRELOC | CRRELOC | 1992 |
| Other consumer (6.b + 6.d; auto split out from 2011; 6.b from 2001) | LNCONOTH + LNCONRP | DRCONOTH | CRCONOTH | 1992 |
| Auto | LNAUTO | DRAUTO | CRAUTO | 2011 |

Structure changes come from `https://banks.data.fdic.gov/api/history`, as
credit-suite does it (`credit-suite/src/credit_suite/sources/fdic/mergers.py`):
the change-code allowlist, the fields, `quarter_end`, and `classify`. **Copy
that logic into threshold-engine with a note saying where it came from. Do not
import credit-suite**, because each project must lift out whole.

## Test data in the repository

- `config/peers.json`: the roster. 16 banks, each with `cert`, `name`, `short`,
  `group` (`self` or `peer`), and `regional`.
- `tests/data/peers/roster_2006.json`: `{YYYYMMDD: [rows]}` for the 16 roster
  certs, 82 quarters 2006–2026, with every field in the first four products.
- `tests/data/peers/roster_1992.json`: the same shape, 138 quarters 1992–2026,
  home equity, other consumer and auto.
- `tests/data/peers/expected_books.json`: **acceptance.** The earlier
  `build_peers.py` output: per bank and product, TTM gross and net rates in %,
  quarters `2007Q1`–`2026Q2`, plus the all-15-peer composite.
- `tests/data/peers/mergers_roster.json`: `{cert: [YYYY-MM-DD quarter-ends]}`,
  each roster bank's acquisition quarters from the earlier classified pull.
- The full all-filer pulls (128MB and 229MB) are **not** in the repository.
  They are in the evidence pack, `C:\Users\ajish\SATC-evidence\threshold-analysis-2026-10-06\peers2006`
  and `peers1992`, for verification runs on this machine only.

Tests must never touch the network. A module that fetches takes the fetch
function as an argument, and its tests pass a fake.

## Modules (new package `src/threshold_engine/peers/`)

### `fdic.py`: pull and cache
- `quarter_ends(first, last)` → `["20060331", ...]`, where first and last are `"2006Q1"`.
- `pull(quarters, fields, cache_dir, fetch=None, refresh=False)` → `{q: rows}`. It
  reads `cache_dir/q{q}.json` if present and fetches only what is missing.
  Paginate at 10,000 rows. Retry up to 4 times with backoff, then raise. The
  default `fetch` is urllib with a 300-second timeout.
- `pull_mergers(since, fetch=None)` and `classify(rows)` →
  `{cert: [quarter-end dates]}` for acquirers, as credit-suite does it.
- **Tests:** pagination, retry, the cache never refetching, refresh, the
  quarter list, and classify on canned rows, including a code outside the
  allowlist being ignored.

### `roster.py`
- `load(path)` → a list of banks. It refuses (raises `ValueError` with the
  reason) unless there is exactly one `self`, the certs are unique, and the
  groups are valid. `peers(r)`, `regionals(r)`, `self_bank(r)`.

### `books.py`: per bank, the composite and the industry. The core.
Inputs are `{q: rows}` as `pull` returns, and a product name from the table.
- `quarterly_flows(data, cert, product)` → per quarter `(q, gross, recoveries,
  balance)`. A Q1 flow is its year-to-date. A later quarter's flow is its
  year-to-date less the previous quarter's, or `None` if the bank is missing
  from either quarter. The balance is the quarter-end figure.
- `bank_book(data, cert, product, jump, min_book, exempt_min_book=False)` → one
  row per TTM quarter, starting with the fifth quarter, labelled `YYYYQn`:
  `{quarter, gross_rate, net_rate, gross, recoveries, avg_balance, kept, why}`.
  The rule, exactly as `build_peers.py` applied it:
  - the window is quarters i−3 to i; `avg_balance` is the mean of their four
    balances;
  - **kept** only if `avg_balance >= min_book` (unless exempt) and
    `avg_balance > 0`, every flow in the window is present, and **no quarter k
    in i−4 to i** has a balance move `|b_k / b_{k−1} − 1| > jump`, or a move
    from 0 to above 0;
  - rates are `100 × sum(gross) / avg_balance` and `100 × (sum(gross) −
    sum(recoveries)) / avg_balance`, or `None` when not kept;
  - `why` is one of `"book moved more than the jump in this window"`, `"book
    under the minimum"`, `"a quarter is missing"`, or `None`.
- `composite(books, certs, min_banks)` → per quarter: summed kept flows over
  summed kept average balances (gross and net %), with the number of banks in.
  `None` below `min_banks`. `min_banks` is required, with no default; 5 is
  what reproduces the earlier build (`build_peers.py`), and 3 does not.
- `band(books, certs, kind, pcts=(10, 25, 75, 90), min_banks)` → per quarter,
  the percentiles of the kept rates (`profile.percentile`, which works like
  Excel's PERCENTILE.INC).
- `best_worst(books, certs, kind, last_n=20, min_obs=12)` → `(best_cert,
  worst_cert)`, the lowest and highest mean over the last `last_n` quarters
  among banks with at least `min_obs` kept values.
- `industry(data, product, products=None)` → per TTM quarter, the aggregate of
  **every** bank in `data`. Each quarter's flow is summed bank by bank: a Q1 flow
  is its year-to-date; a later quarter counts only banks present in both
  quarters. Balances are summed. TTM is `100 × sum of four flows / mean of four
  balance sums`, gross and net. `products` sums several products together, e.g.
  other consumer plus auto.
- `write_series(rows, path, note)` → a `date,value` CSV the workbook reads, with
  quarter-end ISO dates and `#` note lines.
- **Acceptance:**
  1. Run on `roster_2006.json` with jump 0.25, min book $1bn (1,000,000 in
     $000) and KeyBank exempt from the minimum: every bank's gross and net rate
     equals `expected_books.json` to 4 decimals, every quarter and product,
     including which quarters are `None`.
  2. The all-15-peer composite equals `expected_books.json["composite"]` to 4
     decimals.
  3. **Verification only, never in the test suite** (it needs the evidence
     pack): `industry` over the full `peers1992` pull for other consumer as
     filed equals `tests/data/other_consumer_as_filed_nco_ttm.csv`, and with
     auto equals `other_consumer_with_auto_nco_ttm.csv`, both to 3 decimals.
  4. A synthetic test: a bank missing from one quarter has its flow left out
     of the industry sum, not counted as a negative.

### `analyses.py`
Definitions, each a pure function over `books` and `data` output.
- **Calendar-year figures for one bank:** net dollars = the Q4 year-to-date
  (DR − CR) **as filed**; the balance = the mean of that year's four quarter-end
  balances.
- `lagged_rate(data, cert, product, year, lag_years)` → `100 × net(year) /
  balance(year − lag)`, plus the same for a pack total (sums).
- `normalisation(series, base_year, end_year)` → the mean of each year's
  quarterly TTM values, and the ratio end ÷ base.
- `organic_index(data, cert, product, base_quarter, acquisitions)` → quarter-end
  balance as an index (base = 100), chain-linked, with growth set to 1 in each
  acquisition quarter. Acquisitions are the bank's classified quarters plus
  declared extras, such as Fifth Third's Dividend Finance (2022Q2: a nonbank
  purchase, so not in the FDIC record).
- `mix_factor(bank_rate, industry_rate, bank_balance, base_year)` → per year:
  the bank's rate ÷ its base-year rate, the industry's likewise, the bank's own
  factor (the first ÷ the second), and 1 ÷ balance growth.
- `balance_trend(data, cert, product)` → quarter-end balances and quarter-on-
  quarter changes.
- **Acceptance**, all from `roster_2006.json`. The regionals: U.S. Bank 6548,
  PNC 6384, Fifth Third 6672, Huntington 6560, Citizens 57957, Regions 12368;
  KeyBank 17534.
  - Card lagged net rate, 2025 net over the 2023 balance, in %: Fifth Third
    3.47, PNC 3.50, KeyBank 3.82, U.S. Bank 4.54, Regions 4.59, Citizens 4.75,
    Huntington 4.92; the six regionals' total 4.35. For 2019 over 2017: Fifth
    Third 6.18, Huntington 7.89, PNC 4.49, Regions 4.80, Citizens 4.66, U.S. Bank
    4.24, KeyBank 3.52; total 4.53. (2 decimals.)
  - Card normalisation, annual mean of the net TTM from `bank_book` (jump 0.25,
    min $1bn, KeyBank exempt), 2019 → 2025: KeyBank 3.29 → 4.30; PNC 3.53 →
    4.07; Citizens 3.82 → 5.51; Fifth Third 5.07 → 3.79; Regions 4.34 → 4.07;
    U.S. Bank 3.82 → 4.16. The composite over ten regionals (the six plus Truist
    9846, First Citizens 11063, M&T 588, Zions 2270): 3.82 → 4.25.
  - Organic index, base 2019Q4 = 100, at 2026Q2, books of at least $500m at the
    base. Acquisitions are `mergers_roster.json` plus Fifth Third 2022Q2. As
    reported / without acquisitions: cards M&T 156/145, U.S. Bank 133/126,
    Huntington 138/123, Regions 108/104, Citizens 104/99, KeyBank 82/82, PNC
    100/80, Truist 78/78, Fifth Third 66/67. Other consumer M&T 246/238, Fifth
    Third 296/226, U.S. Bank 132/130, Huntington 163/121, KeyBank 109/109, Truist
    104/104, Regions 129/61, Citizens 59/59, PNC 39/34. (Rounded to whole
    numbers.)
  - KeyBank other consumer, calendar-year net rate (four quarterly flows summed
    over the mean balance): 2018 1.67, 2019 1.34, 2020 0.66, 2021 0.47, 2022
    0.50, 2023 0.76, 2024 1.11, 2025 1.04. Mean balances ($m): 2018 2,394, 2021
    5,416, 2025 4,681.

### `peers_workbook.py`: the peer workbook (Excel, PocketBook conventions)
Written with openpyxl and `keybank_style` like `workbook.py`. The choices are
live cells and the results are formulas wherever practical.
- **Pack** (red tab): every roster peer with an Include cell (TRUE/FALSE,
  starting from a required argument: all peers or regionals), its regional
  flag, a product picker, and two picker cells (Peer A and Peer B), each taking
  any peer, "Worst in pack" or "Best in pack".
- **Peers:** for the picked product, gross and net charts. The pack band
  (10th–90th and 25th–75th, live from the included peers through helper cells
  holding the value or blank), the live pack composite (included flows over
  included balances), KeyBank, Peer A and Peer B, and a caption naming who
  best and worst resolved to.
- **Balances:** balance index as reported and without acquisitions for every
  bank (values from `analyses`), KeyBank highlighted, and the acquisition
  quarters listed.
- **Lagged, Normalisation, Mix:** tables of values from `analyses`.
- **Data:** per bank, product and quarter: gross, recoveries, average balance,
  rates, kept, why.
- **Run:** sources, pull dates, the cache fingerprints, roster, and the rules
  (jump, minimum book) as stated.
- **Glossary:** this workbook's terms (structural move, pack, composite, band,
  lagged rate, organic index, own factor). Add them as `PEER_TERMS` in a new
  `peers/glossary.py`. **Do not edit `glossary.py`.**
- **Tests:** recalculated with `formulas` (as `tests/test_workbook.py` does).
  The live composite equals `books.composite` for the all-peers and regionals
  packs; flipping one Include changes it to `books.composite` without that
  bank; the band equals `books.band`.
- **Into another workbook** (added 14 Oct 2026, so the thresholds workbook and
  the peers are one file built by Python alone, with no Excel at build time):
  `build_peers_workbook(None, ..., into=wb, names={tab: title})`, and the same
  two options on `peers.run.build`. The tabs go after `wb`'s own and nothing
  is saved; the caller saves and runs `na_as_gap(path, info["sheets"])`, which
  leaves the host's charts alone. `names` titles every tab in `TABS`; a title
  the host already has is refused (its Data, Glossary and Run would otherwise
  be read by the peers' formulas). Formulas name tabs only through `_Tabs`,
  and `foreign_refs` stops the build if any reference on a peer tab names
  another tab. Proved by `tests/test_peers_into.py`: the standalone file is
  part-for-part what the builder at d1e353a1 wrote, and into a host with its
  own Data, Glossary and Run every peer cell recalculates to its standalone
  value.

### `cli.py` additions (the integration step, after the modules)
- `threshold-engine peers pull --cache DIR --first 2006Q1 --last 2026Q2`
  (plus `--mergers`)
- `threshold-engine peers build OUT.xlsx --cache DIR --roster config/peers.json
  --jump 0.25 --min-book 1000000 --pack all|regionals --series-dir DIR` writes the
  peer workbook and, per product, series CSVs for the main workbook: pack
  composite gross and net, KeyBank gross and net, and the industry.
  *As built (12 Oct 2026):* every rule and side-analysis setting is a required
  flag (`--help` lists 23), including `--industry-combined PRODUCT+PRODUCT`
  for an industry series of products summed (other consumer with auto), and
  `--extra-acquisitions CERT=QUARTER` for an acquisition the FDIC record does
  not show. Either may be given bare to state there are none.

### Window (`launcher.py` and `Thresholds.pyw`)
Tkinter, PocketBook's pattern (`pocketbook/src/pocketbook/launcher.py` to read,
not import). Steps down the left: **Series** (add CSVs with labels), **Measure**,
**Settings** (the scale's starting values), **Build** (output path, Run, then
open the workbook). Optionally **Peers** (cache folder, pull, build).
Everything the window decides is in plain functions the tests call without a
display. A smoke test opens and closes the window if a display is present, and
skips with the reason otherwise.
