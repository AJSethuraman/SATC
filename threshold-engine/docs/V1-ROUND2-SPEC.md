# Version 1, round 2: the build spec (12 Oct 2026)

Three pieces the bank put into version 1 on 12 Oct: *"1 and 2 are good for
v1"* (delinquency and nonaccrual by product; templates for internal data),
and the window's Peers step, which the first round left on the command line.
Like `PEERS-SPEC.md`, this is a contract: each module owns its files and
nothing else.

Public data only. Nothing from KeyBank's books, ever. Every setting that is a
judgement is a required argument with no default. Where the bank has not
decided something, the tool asks for it instead of picking.

## A. Delinquency and nonaccrual, by product (`peers/delinquency.py`)

### Data
FDIC BankFind financials, the same API, quarters and cache as `fdic.pull`.
Amounts are **$ thousands at quarter-end** (stocks, not year-to-date flows).

| Product | Balance | 30–89 days past due | 90+ days, still accruing | Nonaccrual |
|---|---|---|---|---|
| Credit card | LNCRCD | P3CRCD | P9CRCD | NACRCD |
| Mortgage | LNRERSFM | P3RERSFM | P9RERSFM | NARERSFM |
| Home equity | LNRELOC | P3RELOC | P9RELOC | NARELOC |
| Other consumer | LNCONOTH | P3CONOTH | P9CONOTH | NACONOTH |
| Auto | LNAUTO | P3AUTO | P9AUTO | NAAUTO |

Confirmed on 12 Oct 2026 that all 15 fields exist, against JPMorgan's 2026Q2
filing. **The builder must find out, and record in the module docstring, the
first quarter each field is filed.** Probe the live API once, and record the
date of the probe.

### Measures: all of them are built, and the bank picks one per measure
The bank, on which 90+ definition it uses: *"It depends and you don't need to
know, if you're making all 3 it shouldn't matter."*

| Measure key | Numerator |
|---|---|
| `30-89` | P3 |
| `90+ accruing` | P9 |
| `nonaccrual` | NA |
| `90+ incl. nonaccrual` | P9 + NA |
| `30+ incl. nonaccrual` | P3 + P9 + NA |

Each is reported on two bases:
- **quarter-end:** `100 × numerator / balance`, both from the same filing;
- **four-quarter average:** the mean of the four quarter-end rates i−3..i,
  only when all four are present.

### Rules
- A bank's quarter-end rate is `None` when its balance is 0 or below, or when it
  is missing from that quarter. When the balance is under `min_book` and the
  bank is not exempt, the rate is also `None` and `why` says so.
- **Acquisitions.** A quarter-end rate is a ratio from one filing, so an
  acquisition does not mix two banks' flows into it. It is therefore not
  subject to the jump rule. A four-quarter average spans four filings, so it
  takes the jump rule, applied as in `books.bank_book` but over the window
  i−3..i: if any quarter k from i−2 to i moved its balance by more than `jump`
  against k−1, the average is `None` and `why` gives the jump. `jump`,
  `min_book` and the exemption are required arguments, as in `bank_book`.
- **Composite** over a set of certs: the summed numerators over the summed
  balances of the banks kept that quarter, with the number of banks in. It is
  `None` below `min_banks`, which is required. Its four-quarter average at i
  is the mean of the four composite quarter-end rates i−3..i, each recomputed
  without the banks whose own four-quarter average at i the jump blanked, so
  the composite and the band on that basis hold the same banks. Decided by
  the bank on 12 Oct 2026 (LOG.md), which also asked that everything left out,
  and why, be listed on the Glossary tab ("Left out, and why").
- **Band:** percentiles 10/25/75/90 of the kept bank rates, using
  `profile.percentile`.
- **Industry:** every filer in `data`, summed numerators over summed balances
  (quarter-end). The four-quarter average is the mean of the four industry
  quarter-end rates.

### Functions
- `bank_delinquency(data, cert, product, measure, jump, min_book,
  exempt_min_book)` returns, per quarter, a dict with `q`, `numerator`,
  `balance`, `rate`, `avg4`, `kept`, `why` and `why_avg4`.
- `composite_delinquency(...)`, `band_delinquency(...)` and
  `industry_delinquency(...)`, each built like its counterpart in `books.py`.
- `FIELDS`, a `{product: (balance, p3, p9, na)}` map, and `fields_for(products)`,
  so `peers pull` can add these fields to its request.

### Test data
A new fixture, `tests/data/peers/delinquency_roster.json`, in the same shape as
`roster_2006.json`: the 16 roster certs and every field in the table, for the
quarters 2017Q1 to 2026Q2. Pull it once from the live public API and write a
note beside it (a `README` line in `tests/data/peers/`) saying when and how it
was pulled. Tests never touch the network.

### Acceptance
1. Run the module's functions over the fixture and compare them with a
   **separate** computation done straight from the raw JSON in a throwaway
   script. KeyBank, every product and measure, quarter-end basis, 2026Q2: the
   two must match exactly. Print the numbers in the result.
2. **Tie one figure to the filing.** KeyBank (cert 17534), credit card, 90+
   days still accruing, 2026Q2. Read the value out of the peer workbook's
   Delinquency data. Then find the same line on KeyBank's filed Call Report,
   Schedule RC-N, which is obtainable from the FFIEC Central Data Repository
   (cdr.ffiec.gov, public, no login). Record the call, the cell, and the
   filed line side by side. If the filing cannot be reached, the answer is
   COULD NOT, with the precise reason; never a second copy of the API.
3. Synthetic tests:
   - a bank missing from one quarter is left out of the composite that
     quarter and does not count as zero;
   - a jump inside i−2..i blanks the four-quarter average but not the
     quarter-end rate;
   - a balance of 0 gives `None`, not a division error.

### In the peer workbook and the command line
- `peers_workbook.py` gains a **Delinquency** tab, driven by the same Pack tab
  through the same Include cells:
  - a measure picker (the five keys) and a basis picker (quarter-end,
    four-quarter average);
  - a chart with the pack band, the pack composite, KeyBank, Peer A and Peer B,
    live, the same way the Peers tab draws charge-offs;
  - the data on a **DelinquencyData** tab.
  
  Its tests recalculate with `formulas`, as `test_peers_workbook.py` does.
- `peers pull --products ...` also pulls the delinquency fields when the new
  flag `--delinquency yes|no` says so. The flag is required.
- `peers build` takes the same required `--delinquency yes|no`. With `yes`, it
  writes per product, measure and basis the `date,value` CSVs the `workbook`
  command reads, for the pack composite, KeyBank and the industry. With the
  default naming, that comes to 5 products × 5 measures × 2 bases × 3 series.
  Each CSV carries `#` notes naming the measure, the basis and the rules, like
  the charge-off CSVs.
- Glossary entries for every new term, in `peers/glossary.py`.

## B. Templates for internal data (`templates.py`, command `template`)

The bank runs internal measures on site. Nothing internal comes back. A
template says what a file must look like, and lists what the bank must state
about the measure. A check command then refuses a file that does not match,
before a build.

### The templates
Each template has a key, a title, the measure's unit, and its direction
(higher or lower is worse). Each also carries the questions the bank must
answer in the file's `#` notes. None of them supplies an answer.

| Key | Title | Unit | Direction |
|---|---|---|---|
| `wapd` | Weighted average probability of default | % | higher_is_worse |
| `refreshed-score` | Refreshed credit score (portfolio average) | score | lower_is_worse |
| `epd` | Early payment default rate | % | higher_is_worse |
| `student-loans` | Other consumer: student loans only (Laurel Road) | % | higher_is_worse |
| `other-consumer-ex-student` | Other consumer without student loans | % | higher_is_worse |
| `card-rewards` | Credit card: rewards cards only | % | higher_is_worse |
| `card-non-rewards` | Credit card: non-rewards cards only | % | higher_is_worse |

The last four are the two-book splits decided on 7 Oct, and the measure they
carry (net charge-offs, delinquency) is itself one of the questions.

Every template asks, as required `#` notes in the form `# key: answer`:
- `measure`: what is measured, in the bank's words;
- `numerator` and `denominator` (for a rate), or `scale` for a score, giving
  the scale's lowest and highest possible values, e.g. `300-850`;
- `as-of`: the convention, e.g. quarter-end balances;
- `basis`: e.g. trailing twelve months, or quarter-end;
- `source`: the internal system or report, by name;
- `prepared-by` and `prepared-on`.

Template-specific notes are added where the measure needs one, e.g.
`epd` asks for `window`, the months on book that define early.

### Commands
- `threshold-engine template list` lists every template: key, title, unit and
  direction.
- `threshold-engine template write KEY OUT.csv` writes an empty template. It
  holds the `#` note lines, each with its question as the placeholder text
  (for example, `# measure: [STATE: what is measured]`), then the `date,value`
  header and no rows. Beside it, `OUT.checklist.md` lists the steps in plain
  words.
- `threshold-engine template check KEY FILE.csv` reports OK, or every problem
  at once, and exits 2 on any problem:
  - every required note is present and none still holds `[STATE:`;
  - the header is exactly `date,value`, and there are **no other columns**
    (refusing anything that could carry account-level data or PII);
  - dates are quarter-ends (`YYYY-03-31` and so on), contiguous, and never
    repeated. *As built:* `YYYYQn` is refused, naming the quarter-end date to
    write instead, because the build reads only dates written YYYY-MM-DD (since 13 Oct 2026 it refuses `YYYYQn` outright);
  - *As built:* the `# template: KEY` line `write` puts first must name the
    template being checked, and every `#` line must be one of its notes;
  - every value is a finite number;
  - a `%` value lies within 0–100, and a `score` value within the scale the
    file states;
  - enough history for the workbook: at least 9 quarters, the two
    four-quarter changes `scale.py` needs (cite its refusal).
- The `workbook` command and the window are unchanged. A checked file is an
  ordinary series.

### Acceptance
- A test writes each template, fills it with synthetic values, and checks that
  it passes `check` and builds through `workbook.build`.
- One test per refusal, each giving the exact message.
- A test for the no-PII rule: a third column, such as `account`, is refused,
  and the message says why.
- No template, test or fixture holds anything resembling bank data. Synthetic
  values only.

## C. The window's Peers step (`launcher.py`)

The **Peers** step becomes usable. It has:
- the cache folder;
- the roster file;
- the quarters (first and last);
- the products;
- every rule `peers build` requires, with each field empty until stated, as on
  the other steps;
- **Pull**, which calls `fdic.pull` / `pull_mergers`;
- **Build**, which calls the same function `peers build` calls. Factor that out
  of `cli.py` into a function both use, so the window and the command line
  cannot drift.

Long operations run on a worker thread, with a status line, and a second press
while one is running is refused. Every decision is a plain function over the
form, tested without a display, as the existing steps are. The smoke test
opens the real window.
