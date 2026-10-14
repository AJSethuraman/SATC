# KeyBank internal data: the import layout (draft, 13 Oct 2026)

What the tool will accept from KeyBank's own books, run on site only. No
internal figure is ever written to this repository; this file describes the
shape, never the numbers.

Agreed with the firm on 13 Oct 2026 (LOG.md, "The firm's answers to the
docket" and what followed). Still a draft: nothing is built against it yet.

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
(b). Home equity loans were discontinued in 2026, so the book runs off from
here and the run-off flag applies.

At 30 Jun 2026 (KeyCorp 10-Q against KeyBank's Call Report): lines about
$2,930m, loans about $2,478m (inferred by elimination, not published), of
which second liens at most $276m.

## Named exclusions

The check is filed, less named exclusions, against internal. Two are known
from the tie-out (KeyCorp against KeyBank, which ties within $1m once both
are added): education loans in discontinued operations, and residential
loans held for sale. The file lists any others it leaves out, with amounts
where known.

## The file

One row per segment per quarter. Amounts in $ thousands.

| Column | Required | What it holds |
|---|---|---|
| `quarter` | yes | e.g. `2024Q3` |
| `product` | yes | the tool's product: `Credit card`, `Mortgage`, `Home equity`, `Other consumer` |
| `segment` | yes | KeyBank's own split, e.g. `Unsecured lines of credit`, `Direct auto`; `All` for the product total |
| `balance` | yes | outstanding at quarter-end |
| `gross_charge_offs` | two of these three | for the quarter |
| `net_charge_offs` | | for the quarter |
| `recoveries` | | for the quarter; worked out as GCO − NCO when not given |
| `dpd_30_plus`, `dpd_60_plus`, `dpd_90_plus` | yes | balances at quarter-end, cumulative (30+ includes 60+ and 90+) |
| any further column | no | carried through and shown, never compared with public data (room for the deeper mortgage and home equity detail) |

The header states, as `# key: value` lines the Sources tab already reads:
`entity`, `as-of`, `basis`, `source`, and what each segment holds.

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
