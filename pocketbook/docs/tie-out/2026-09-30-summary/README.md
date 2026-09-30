# Tie-out: the Summary tab, 30 Sep 2026

**14 views, 1,274 cells: 1,274 TIED, 0 DIFFERS.**

## What was checked

Every number the Summary tab shows, for both band columns the Run cut (FICO, and REV_DEBT in dollars) and for every
value of the Filter by column (All loans, and each origination year 2021 to 2026): 7 views of FICO (8 rows by
13 columns) and 7 of REV_DEBT (6 by 13).

- **Road 1** (`build.py`): the synthetic book, 8,000 loans, seed 7 (`Summary book.csv`), set up with FICO and
  REV_DEBT as bands, CHANNEL and ASSET_CLASS as segments and ORIG_YEAR as Filter by, answered as the tests answer
  it (FICO -9999 is Missing), and Run. For each view the two dropdowns were set and LibreOffice calculated the
  workbook; every cell was read back (`shown.csv`).
- **Road 2** (`road2.py`): the same figures from the CSV alone, with the standard library and nothing from
  PocketBook. Each loan is placed by reading the band label the tab shows ("496 - 653"; a dollar value with its
  cents dropped), so the labels are checked too: a loan that fits no label, or two, stops the run. Bad loans are
  BAD_FLAG = 1 over the loans whose flag reads 0 or 1. Each rate is its dollars over ORIG_BAL on the loans with
  both amounts. × book is against the whole book's charge-off rate, and each share is of the view's All row.
- A cell ties when the two agree within one part in a billion. The rows must also come in order: bands, then the
  special rows, then All.

## What it found

Nothing differs. Road 2 does catch a change: a copy of `shown.csv` with one cell moved by 0.1% read
*1,273 TIED, 1 DIFFERS*.

The whole book, FICO (read from `shown.csv`):

| FICO | Loans | % of loans | Bad loans | Bad loans % | Booked $ | % of booked | Charged off $ | Charge-off rate | × book | % of charge-offs | RANR $ | RANR rate | % of RANR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 496 - 653 | 1,556 | 19.4% | 234 | 15.05% | $50,747,952 | 19.7% | $4,235,047 | 8.35% | 2.01× | 39.4% | $9,650,827 | 19.02% | 29.2% |
| 654 - 685 | 1,539 | 19.2% | 130 | 8.45% | $49,349,596 | 19.1% | $2,231,319 | 4.52% | 1.09× | 20.8% | $8,047,707 | 16.31% | 24.4% |
| 686 - 711 | 1,562 | 19.5% | 96 | 6.15% | $51,016,427 | 19.8% | $1,607,783 | 3.15% | 0.76× | 15.0% | $7,240,165 | 14.19% | 21.9% |
| 712 - 745 | 1,611 | 20.1% | 87 | 5.40% | $51,112,484 | 19.8% | $1,545,666 | 3.03% | 0.73× | 14.4% | $4,905,226 | 9.60% | 14.9% |
| 746 - 921 | 1,571 | 19.6% | 62 | 3.95% | $50,525,744 | 19.6% | $980,621 | 1.94% | 0.47× | 9.1% | $2,361,746 | 4.67% | 7.2% |
| (blank) | 1 | 0.0% | 0 | 0.00% | $27,999 | 0.0% | $0 | 0.00% | 0.00× | 0.0% | $3,928 | 14.03% | 0.0% |
| (marked missing) | 160 | 2.0% | 10 | 6.25% | $5,288,243 | 2.0% | $134,920 | 2.55% | 0.61× | 1.3% | $820,594 | 15.52% | 2.5% |
| All | 8,000 | 100.0% | 619 | 7.74% | $258,068,446 | 100.0% | $10,735,355 | 4.16% | 1.00× | 100.0% | $33,030,193 | 12.80% | 100.0% |

## Not checked

- Real Excel. LibreOffice did the calculating, and the formulas only look values up (INDEX/MATCH).
- The widths and shading as they look on screen. The tests check the shading rule; nobody has looked at the tab
  in Excel.
- A real extract.

## Rerun it

    cd pocketbook
    python3 docs/tie-out/2026-09-30-summary/build.py    # about 2 minutes; needs LibreOffice
    python3 docs/tie-out/2026-09-30-summary/road2.py    # writes results.csv, prints the counts
