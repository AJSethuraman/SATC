# Paid, cost, kept: gross booked, GCO and RANR, tied out to the loan file

You asked on 30 September: *"On the paid cost kept tab I would like to work on gross GCO gross booked and gross
RANR as well so we can also see if pockets are straight negative on returns"*. This reads every gross figure the tab
now shows, for every choice of its Grid dropdown, and works each one out a second time from the loan file with code
that imports nothing from PocketBook.

**481 figures read. 481 TIED, 0 DIFFERS.**

| Grid | Pocket figures | Totals | Count line | TIED | DIFFERS |
|---|---:|---:|---:|---:|---:|
| FICO x CHANNEL | 216 | 18 | 2 | 236 | 0 |
| FICO x ASSET_CLASS | 225 | 18 | 2 | 245 | 0 |
| **All** | **441** | **36** | **4** | **481** | **0** |

A figure is one cell: each pocket's Loans, Booked, GCO, RANR and RANR rate, and whether each of RANR, RANR rate,
Booked and GCO is drawn red (9 a pocket); the same for each total row under the table; and the count line beside the
dropdown and whether it is red. Dollars tie to half a cent, a rate to 1e-12, everything else exactly.

## The book

`Kiosk book.csv`, made up: the synthetic book of 8,000 loans (seed 30, with its dirt: a -9999 score code, a blank
score, a charge-off written `#N/A`, a blank balance), plus 90 loans through a **Kiosk** channel spread over every
score and asset class, each keeping -4% of what it booked less its charge-offs, one in nine charged off at 30%, and
one Kiosk loan's RANR left blank. So every score band has a Kiosk pocket that lost money outright.

## How the two roads meet

1. **Road 1** (`road1.py`): makes the book, runs PocketBook (this build), sets the Grid dropdown to each grid in
   turn, has LibreOffice 24.2 calculate the tab, and reads every gross cell, the totals, the count line, and whether
   each red-text rule the tab carries holds on each cell.
2. **Road 2** (`road2.py`): the csv and math modules only. Takes from Road 1 just what the analyst reads off the tab
   to place a loan (the band labels, "478 - 652", both ends in) and which pockets are listed; every number is summed
   from the loan file. A loan counts towards RANR and Booked when its balance and RANR both read as numbers, towards
   GCO when its balance and charge-off do.
3. `compare.py` sets them side by side, one verdict a figure, in `roster.csv`.

Rerun: from `pocketbook/`, `python3 docs/tie-out/2026-09-30-pck-gross/road1.py`, then `road2.py`, then
`compare.py` (about a minute; needs LibreOffice).

## What it shows

FICO x CHANNEL, as the tab reads (dollars rounded here):

| Band | Segment | Loans | Booked | GCO | RANR | RANR rate |
|---|---|---:|---:|---:|---:|---:|
| 478 - 652 | Broker | 528 | $16,694,974 | $2,094,152 | $2,465,300 | 14.77% |
| 478 - 652 | Kiosk | 36 | $759,410 | $23,715 | **-$54,092** | **-7.12%** |
| 746 - 896 | Kiosk | 22 | $539,202 | $17,105 | **-$38,673** | **-7.17%** |
| Pockets listed | | 8,090 | $260,847,571 | $10,814,898 | $32,702,548 | 12.54% |
| Whole book | | 8,090 | $260,847,571 | $10,814,898 | $32,702,548 | 12.54% |

(bold: red on the tab). The line beside the dropdown: *"6 pockets lost money outright, totalling $166,260: RANR below
zero, in red."* Five are the Kiosk pockets; the sixth is the one loan with a blank score, (blank) / Branch, which
charged off. On FICO x ASSET_CLASS the Kiosk loans are spread among thousands that make money, and the one negative
pocket is (blank) / 2, the same loan.

## Not covered

- **Not listed** (a pocket with nothing to compare it with) happens on neither grid here; its arithmetic is held by a
  unit test instead (`test_pck_gross_a_pocket_not_listed_gets_its_own_total_and_the_three_still_add_up`).
- **Thousands** ($1,234k) did not trigger: this book's $260.8m fits the column. Held by a unit test.
- Real Excel was not opened; LibreOffice calculated. The red is read from the conditional-format rule and the
  calculated value, not from a picture.
