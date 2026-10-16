# KeyBank internal data: the import layout (built 14 Oct 2026)

What the tool accepts from KeyBank's own books, run on site only. No
internal figure is ever written to this repository; this file describes the
shape, never the numbers.

Agreed with the firm on 13 Oct 2026 (LOG.md, "The firm's answers to the
docket" and what followed). Built on 14 Oct 2026 as `internal.py` and the
`internal` command; tested on made-up figures only. Nothing has been run on
KeyBank's data.

## The commands

| Command | What it does |
|---|---|
| `internal template OUT.csv` | Writes the empty file and `OUT.exclusions.csv` beside it. Every note holds `[STATE: ...]`, so neither passes until answered |
| `internal check FILE [--exclusions FILE]` | OK, or every problem at once, each naming its line (exit 2) |
| `internal series FILE --out-dir DIR` | One `date,value` CSV per product, segment and measure, for the `workbook` command |
| `internal pull --cache DIR --first YYYYQn --last YYYYQn` | Fetches every Call Report field reconcile reads, into a cache folder of its own (a peers cache lacks the junior-lien fields and is refused by name) |
| `internal reconcile FILE --cache DIR --roster FILE --exclusions FILE --tolerance X --out FILE.csv` | Filed, less named exclusions, against internal, from the cache only. Every setting required; `--tolerance` has no default |

## What KeyBank's segments are

The firm's description of internal **other consumer**: direct unsecured
loans, unsecured lines of credit, direct auto ("with some random other stuff
but close enough to auto"), and direct student loans. Internally there is
also deeper mortgage and home equity detail.

That is wider than the Call Report's other consumer, which files auto on its
own line. So the public match for KeyBank's internal other consumer is **all
consumer loans less credit cards**:

| | Balance (RC-C) | Charge-offs and recoveries (RI-B) | Delinquency (RC-N) |
|---|---|---|---|
| Internal other consumer, all segments | 6.b + 6.c + 6.d | 5.b + 5.c | 5.b + 5.c |
| Lines of credit, installment, auto, student, each alone | no public split | no public split | no public split |

## Home equity: lines and loans, separately

The Call Report sorts by structure, not product name: revolving home equity
lines are RC-C 1.c.(1); closed-end home equity loans are filed with
mortgages, first liens in 1.c.(2)(a) and second liens in 1.c.(2)(b). So the
file gives `Home equity lines` and `Home equity loans` as separate segments.
Lines check against 1.c.(1). Loans plus mortgage check against 1.c.(2)(a) +
(b). Home equity loans were recently discontinued ("Loans were just
discontinued", 14 Oct 2026), so the book runs off from
here and the run-off flag applies.

At 30 Jun 2026 (KeyCorp 10-Q against KeyBank's Call Report): lines about
$2,930m, loans about $2,478m (inferred by elimination, not published), of
which second liens at most $276m.

## Named exclusions

The check is filed, less named exclusions, against internal. Two are known
from the tie-out (KeyCorp against KeyBank, which ties within $1m once both
are added): education loans in discontinued operations, and residential
loans held for sale. Their amounts are never assumed: each is a row in the
exclusions file, with its amount.

The exclusions are **a separate file**, not a section of the internal one:
their columns differ, their amounts come from public filings rather than
internal systems, and the command takes them as their own `--exclusions`.
One row per exclusion, quarter and measure:

| Column | What it holds |
|---|---|
| `quarter` | e.g. `2024Q3` |
| `product`, `segment` | the internal figure it belongs to, e.g. `Mortgage`, `All` |
| `measure` | `balance`, `gross_charge_offs` or `net_charge_offs`: a balance left out says nothing about the charge-offs on it |
| `name` | what is left out, e.g. `Residential mortgages held for sale` |
| `amount` | $ thousands; taken off the filed figure. Negative: something internal holds that the filing does not |

One note, `# source:`, says where the amounts come from. A file with the
header and no rows states that nothing is left out. An exclusion no
comparison would take (a segment not compared, or a quarter the internal
file does not hold) is refused.

## The file

One row per segment per quarter. Amounts in $ thousands. Rows in any order.

| Column | Required | What it holds |
|---|---|---|
| `quarter` | yes | e.g. `2024Q3` |
| `product` | yes | the tool's product: `Credit card`, `Mortgage`, `Home equity`, `Other consumer`, `Auto` (KeyBank's direct auto, set separately: "we have auto in the bank it's just direct") |
| `segment` | yes | KeyBank's own split, e.g. `Unsecured lines of credit`, `Direct auto`; `All` for the product total; `Home equity lines` and `Home equity loans` for home equity |
| `balance` | yes | outstanding at quarter-end |
| `gross_charge_offs` | two of these three | for the quarter |
| `net_charge_offs` | | for the quarter |
| `recoveries` | | for the quarter. The one not given is worked out (gross − recoveries = net); when all three are given they must agree exactly, as written |
| `dpd_30_plus`, `dpd_60_plus`, `dpd_90_plus` | yes | balances at quarter-end, cumulative: 0 ≤ 90+ ≤ 60+ ≤ 30+ ≤ balance |
| any further column | no | carried through and shown, never compared with public data (room for the deeper mortgage and home equity detail). Numbers or blank only; a column named like an identifier (account, borrower, customer, name, id, SSN...) is refused |

The header states, as `# key: value` lines the Sources tab already reads:
`entity`, `as-of`, `basis`, `source`, and one `# segment-NAME: what it
holds` per segment the rows use. A segment with no such line is "not
stated" and refused; any other `#` line is refused.

Refused as well: a quarter not written `YYYYQn`; a blank or non-numeric
required cell (no thousands separators); a balance, past-due amount, gross
charge-off or recovery below 0; the same quarter, product and segment
twice; a gap in a product and segment's quarters (never filled in); a
byte-order mark.

## The series it writes

Per product and segment, by the public method: net and gross charge-off
rates over four quarters (100 × the four quarters' charge-offs over the mean
of the four quarter-end balances), and 30+, 60+ and 90+ past-due rates at
quarter-end and as the mean of four quarter-end rates. The first three
quarters of each have no four-quarter window and are not written; the notes
say so. Each file's notes give the measure, numerator, denominator and
basis (the method), and copy the file's own as-of, source, entity, basis
and segment description, so the Sources tab shows them.

## The reconciliation

Per quarter, comparison and measure (balance, gross and net charge-offs):
filed, less the exclusions, less internal is the unexplained remainder; its
share of the internal figure is within tolerance or not. Where a side is not
stated (a field the cache lacks, a blank field, the quarter before not
cached, an internal half missing) the row says `not measured` and why.

| Comparison | Internal | Public (RC-C; RI-B) |
|---|---|---|
| Credit card | Credit card / All | 6.a (LNCRCD); 5.a |
| Mortgage | Mortgage / All | 1.c.(2)(a) (LNRERSFM); 1.c.(2)(a) |
| Home equity lines | Home equity / Home equity lines | 1.c.(1) (LNRELOC); 1.c.(1) |
| Mortgage and home equity loans | Mortgage / All + Home equity / Home equity loans | 1.c.(2)(a) + (b) (LNRERSFM + LNRERSF2); same |
| Other consumer | Other consumer / All | 6.b + 6.c + 6.d (LNCONRP + LNAUTO + LNCONOTH); 5.b + 5.c |
| Auto | Auto / All | 6.c (LNAUTO); 5.b |

Charge-offs are filed year to date; a quarter is its year to date less the
quarter before's. A blank filed field is not filed, never 0: auto (6.c)
was not filed on its own before 2011Q1, so other consumer and auto are not
measured before then. The output names both entities (the file's `entity`, and
the roster's `self` bank with its certificate).

## Where the internal and public figures meet, and how closely

- **Charge-offs:** like for like. Net charge-offs over the average balance,
  four quarters, the same method as the public series.
- **Delinquency:** close, not exact. KeyBank's buckets are days past due,
  cumulative. The Call Report files 30–89, 90+ still accruing, and
  **nonaccrual** (loans the bank has stopped booking interest on, some of
  which are not late at all). The nearest matches: internal 30+ against
  public 30–89 + 90+ + nonaccrual; internal 90+ against public 90+ +
  nonaccrual. The gap is nonaccrual loans that are current. 60+ has no
  public counterpart.
- **Entity:** the firm's data is KeyCorp (the 10-K); the Call Report is
  KeyBank, N.A. Nearly all of KeyCorp's consumer loans sit in the bank, so
  the gap should be small. It is measured once, from public filings (10-K
  against the Call Report), not assumed.

## History

Most series from 2014, some from 2008. From 2014 the only stress is the
pandemic. A crisis appears only in the internal series that reach 2008.
Where they do not, industry and peer history are what show a crisis. How far
that stand-in can be trusted is the open question for the extrapolation work.
