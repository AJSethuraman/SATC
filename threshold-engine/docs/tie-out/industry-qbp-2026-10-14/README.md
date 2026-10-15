# The industry series against the FDIC's own totals (14 Oct 2026)

**The figure:** quarterly gross credit card charge-offs, every FDIC-insured
institution, $ millions, as `peers/books.py` computes the industry flow
(year-to-date differenced bank by bank), 2006Q1 to 2026Q2.

**The source:** the FDIC's Quarterly Banking Profile time series, 2Q 2026
release:
https://www.fdic.gov/quarterly-banking-profile/qbp-time-series-spreadsheets-second-quarter-2026.xlsx,
sheet "Loan Performance", block "Credit Cards", row 346 "Total charge-offs"
(gross, quarterly, $ millions, all FDIC-insured institutions). This is the
current, restated series; the figures as first published were not fetched.
Card balances (row 342) equal ours to $0.0m in every quarter, so both count
the same banks.

**Run it:** `python docs/tie-out/card-qbp-2026-10-14/check.py CACHE QBP.xlsx`
(the docstring says what CACHE must hold). It writes `card_vs_qbp.csv`.

| | Quarters within $0.05m | Total absolute gap |
|---|---|---|
| Year-to-date differenced, as before 14 Oct | 52 of 82 | $14,683.2m |
| With the absorption fix (`repeated_ytd`) | 70 of 82 | $151.1m |
| With the restart rule too (the tool now) | 76 of 82 | $5.6m |

**The restart rule** (`books.restarted`): when a bank's parent changes and
any of its year-to-date figures falls, the filing restarted under the new
owner, and its year to date is the quarter's flow, for charge-offs and
recoveries alike (one decision per filing: a review on 14 Oct found the first
version deciding field by field, and that the absorption fix kept
subtracting after a restart; both fixed). It closed National City under PNC (2008Q4, -$94.6m), BBVA
USA under PNC (2021Q2, -$20.4m), First Niagara under KeyCorp (2016Q3,
-$6.4m) and two smaller quarters, and 2007Q3 from -$14.0m to -$0.1m. The rule
is read from the numbers and the Call Report's push-down accounting, not from
an FDIC statement of its method; the QBP's Notes to Users do not describe it.

**Still different (tool now less QBP):**

| Quarter | $m | What is known |
|---|---|---|
| 2018Q4 | +4.4 | Bank 25894 absorbed 15432 under a *different* parent; QBP takes off 15432's year-to-date (4.364), the tool does not (it does so only under common control) |
| 2011Q2 | +0.7 | The restart rule fired on bank 680 (year-to-date 709 to 0, new parent); QBP differenced it. The rule overshoots here |
| 2015Q3 | +0.1 | The same, bank 58978 |
| 2007Q3, 2020Q3, 2025Q2 | -0.1 each | Rounding-sized |

**Found, and harmless to every number drawn:** the FDIC record says
Capital One N.A. (4297) absorbed 34191 in 2007Q3, but the card book and its
$151.0m year-to-date went to its sister, Capital One Bank (USA) (33954). The
industry total is right; 4297 bank by bank reads -$151.0m that quarter, and
those windows are already left out (no card book; an acquisition quarter).
33954 is not on the roster.


## Every product, and delinquency (`check_all.py`)

The same spreadsheet holds the same block for home equity lines (row 95),
closed-end first-lien mortgages (124), auto (368) and "Other Loans to
Individuals" (353). `check_all.py CACHE QBP.xlsx` compares, per quarter,
the quarter-end balance, 30-89, 90+ and nonaccrual (sums of the filed
fields), and gross and net charge-offs (the tool's flow). It writes
`industry_vs_qbp.csv`. Quarters within $0.5m, of those the QBP fills:

| Product | Balance | 30-89 | 90+ | Nonaccrual | Gross | Net |
|---|---|---|---|---|---|---|
| Credit card | 82/82 | 82/82 | 82/82 | 82/82 | 80/82 | 80/82 |
| Auto (QBP from 2013Q3) | 52/52 | 52/52 | 52/52 | 52/52 | 52/52 | 52/52 |
| Other consumer + auto (6.b + 6.c + 6.d) | 80/82 | 80/82 | 82/82 | 80/82 | 73/82 | 76/82 |
| Home equity lines | 35/82 | 80/82 | 82/82 | 80/82 | 76/82 | 77/82 |
| First-lien mortgage | 78/82 | 79/82 | 81/82 | 79/82 | 66/82 | 51/82 |

- **Other consumer:** the QBP's "Other Loans to Individuals" is 6.b + 6.c +
  6.d. Its balance equals ours in 80 of 82 quarters, which supports the new
  balance (6.b + 6.d, with auto beside it); 6.d alone would not.
- **2008Q3-Q4, every product but card and auto:** ours is larger (mortgage
  balance +$12.1bn and +$10.9bn; home equity +$3.0bn and +$2.7bn) and
  charge-offs fall in the other quarter (mortgage net -$571m, then +$948m).
  Not identified. The balances are 0.4% to 0.65% larger than the QBP's;
  the effect on the four-quarter rates was not measured.
- **First-lien mortgage, 2006-2011:** net charge-offs $6m to $43m a quarter
  apart while gross mostly ties, so the difference is in recoveries, in the
  years savings institutions filed their own report (the TFR). Not
  identified; at most 4.3% of the quarter's net charge-offs (2006Q1,
  when they were small).
- **Home equity balance, 2009-2020:** $1m to $12m apart on a book of about
  $261-674bn. Not identified.

**Not proved:** the QBP is the restated series; the figures as first
published were not fetched. Nothing before 2006 was compared.
