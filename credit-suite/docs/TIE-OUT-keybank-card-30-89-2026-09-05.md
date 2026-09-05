# Tie-out — KeyBank, card loans 30–89 days past due, 30 June 2026

**Verdict: TIED.** Executed end to end on 5 September 2026. Every link below was
run, not described.

The figure was chosen because it is the one that moved. Until 5 September this
template showed the FDIC's own published card delinquency rate, which divides
by **total assets**; it now computes the rate over the **card book** (#268).
The number on the screen changed from 0.005 to 0.92, so it is the number most
in need of proof.

---

## 1 · The figure

`Bank_Peer_Monitor.xlsm` → tab **`Dashboard_LoanBook`** → row for **KeyBank NA**
→ column **`Card 30-89`**.

| | |
|---|---|
| Cell | `Dashboard_LoanBook!D16` |
| Displayed | **0.92** |
| Underlying value | 0.9203649082818812 |
| Meaning | card balances 30–89 days past due and still accruing, as a percentage of the card book |
| As at | 2026-06-30 |

Read by opening the workbook in Excel and forcing a full recalculation
(`CalculateFullRebuild`), because the cell is a formula and openpyxl does not
compute one. The displayed text is what a person sees; the long value is what
Excel holds.

## 2 · The call

One request, copy-pastable, with the real parameters in it:

```
https://banks.data.fdic.gov/api/financials?filters=CERT:17534%20AND%20REPDTE:20260630&fields=CERT,REPDTE,P3CRCD,LNCRCD&limit=1&format=json
```

Response, as returned:

```json
{"data":[{"data":{"CERT":17534,"REPDTE":"20260630","P3CRCD":8528,"LNCRCD":926589,"ID":"17534_20260630"}}]}
```

Both values are in **thousands of dollars**, which is how the FDIC publishes
them and how the workbook lands them.

## 3 · The derivation

Nothing here is "then the system computes it". Every step is a cell you can
open and read.

1. The runner lands the two fields into the fixed raw block for KeyBank, which
   is peer slot 9, newest quarter first:

   | field | cell | value |
   |---|---|---|
   | `P3CRCD` (card 30–89, still accruing) | `Raw_FDIC!X164` | 8,528 |
   | `LNCRCD` (card balances) | `Raw_FDIC!AM164` | 926,589 |

   Row 164 is the newest quarter of slot 9; `Raw_FDIC!A164` reads `2026-06-30`.

2. The dashboard cell is a formula over those two cells and nothing else:

   ```
   =IF(OR(Raw_FDIC!X164="",Raw_FDIC!AM164=""),"",IF(Raw_FDIC!AM164=0,"",Raw_FDIC!X164/Raw_FDIC!AM164*100))
   ```

   In words: if either input is blank, show blank; if the card book is zero,
   show blank; otherwise past-due divided by the book, times 100.

3. By hand:

   ```
   8,528 / 926,589 × 100 = 0.9203649082818812
   ```

   Excel holds 0.9203649082818812 and displays 0.92 at two decimal places.

The engine computes the identical value in Python from the same declarative
table that generates the formula, so the two cannot drift:
`metric_value("P3CRCD_BOOK", {"P3CRCD": 8528, "LNCRCD": 926589})`.

## 4 · The independent source

**KeyBank's own Call Report as filed with its regulators** — not the FDIC's
API, not a second reading of our own data.

- **What:** Consolidated Reports of Condition and Income, **FFIEC 031**
- **Who:** KEYBANK NATIONAL ASSOCIATION, Cleveland OH, RSSD-ID 280110, FDIC
  Certificate 17534
- **As at:** Report Date **6/30/2026**, last updated 7/30/2026
- **Where you get it yourself:** FFIEC Central Data Repository, public data
  distribution —
  <https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx?ds=call&idType=fdiccert&id=17534&date=06302026>
  (no login; the page offers the same filing as PDF, XBRL and SDF)
- **Captured:** the two pages are filed beside this document, with the figures
  visible in the shot and the bank's name, form type and report date printed in
  the page header of each.

### Locating the numerator

`docs/tie-out/keybank-card-30-89-2026-09-05/source-rc-n-page46-card-past-due.jpg`

> **Schedule RC-N — Past Due and Nonaccrual Loans, Leases and Other Assets
> (Form Type – 031)**, facsimile page 46 of 75 (printed form page 45)
> **Line 5.a, "Credit cards"**, **Column A, "Past due 30 through 89 days and
> still accruing"**, MDRM **RCFDB575** = **8,528**, dollar amounts in thousands.

Line 5 reads "Loans to individuals for household, family, and other personal
expenditures", and 5.a is its credit-card component. The neighbouring cells on
the same row are Column B `RCFDB576` 9,346 and Column C `RCFDB577` 6,401, which
are the 90+ and nonaccrual figures — not this one.

### Locating the denominator

`docs/tie-out/keybank-card-30-89-2026-09-05/source-rc-c-page24-card-balances.jpg`

> **Schedule RC-C Part I — Loans and Leases (Form Type – 031)**, facsimile page
> 24 of 75 (printed form page 23)
> **Line 6.a, "Credit cards"**, **Column A, "Consolidated Bank"**, MDRM
> **RCFDB538** = **926,589**, dollar amounts in thousands.

Column A is the consolidated bank, which is the basis the FDIC's own totals
use for a bank filing form 031. Column B, "Domestic Offices", reads the same
926,589 here because KeyBank holds no card balances in foreign offices.

### The digits were checked twice

The values above were read off the rendered pages **and** independently off the
same filing's XBRL instance, fetched from the same regulator, and they agree:

```
RCFDB575   8,528,000 dollars =   8,528 thousand
RCFDB538 926,589,000 dollars = 926,589 thousand
```

That double reading caught one mistake of mine: reading the HELOC balance off
the image I recorded `RCFD1797 = 2,929,670`; the XBRL says **2,929,570**. The
XBRL is right and the image is small — the error was mine, in the reading, not
in the filing or the software. It does not touch this figure, and it is
recorded here because a tie-out that hides its own misreads is worth nothing.

## 5 · The comparison

```
ours    Bank_Peer_Monitor.xlsm -> Dashboard_LoanBook!D16 (KeyBank, Card 30-89)
        = 8,528 / 926,589 x 100                                     0.9203649082818812

source  KeyBank FFIEC 031 as filed 2026-06-30 (FFIEC CDR facsimile)
        RC-N line 5.a col A  RCFDB575                                  8,528  ($000)
        RC-C Pt I line 6.a col A  RCFDB538                           926,589  ($000)
        = 8,528 / 926,589 x 100                                     0.9203649082818812

diff                                                                          0
```

The four things that have to be the same, each checked rather than assumed:

| | ours | source | same? |
|---|---|---|---|
| entity | CERT 17534, KeyBank NA | CERT 17534 / RSSD 280110, KeyBank National Association | yes |
| date | 2026-06-30 | Report Date 6/30/2026 | yes |
| basis | consolidated (`RCFD`), still-accruing only | Column A Consolidated Bank; Column A of RC-N is "still accruing", disjoint from nonaccrual | yes |
| units & scale | thousands of dollars, ratio ×100 | "Dollar amounts in thousands" | yes |

---

## The roster — 48 KeyBank lines, not one

Every dollar line this template lands for KeyBank, compared against the same
filing. Full output: `docs/tie-out/keybank-card-30-89-2026-09-05/roster-tieout-17534-20260630.txt`,
reproducible with:

```
python -m credit_suite.sources.fdic.runner -w example-output/Bank_Peer_Monitor.xlsm --tieout 17534 --filing
```

```
Tied out: 48 of 53 landed lines
  TIED        48
  DIFFERS      0
  COULD NOT    5   2 published ratios (recomputed from dollar lines instead)
                   3 quarterly charge-off flows (the filing carries year-to-date)
```

The five that could not be tied, each with its obstacle named:

- `RBC1AAJ`, `RBCRWAJ` — the FDIC publishes these as percentages; there is no
  single filed line to compare a percentage with. Their components are tied
  elsewhere and the ratio is recomputed in the arithmetic leg.
- `NTCRCDQ`, `NTAUTOQ`, `NTCIQ` — quarterly charge-off flows. The Call Report
  reports charge-offs **year-to-date**, so a quarter is a difference of two
  filings, not a line in one. Different basis; reconciling it is a separate
  piece of work, and it is the same year-to-date convention that produced the
  670% chart on 4 September.

## What this exercise found

Running it changed the software, which is the point of doing it rather than
describing it.

**Three C&I lines were pointing at the wrong code.** `P3CI`, `P9CI` and `NACI`
came back **NOT IN FILING** on the first run. The provenance map cited MDRM
`1606` / `1607` / `1608`, which are the **form 041** codes. KeyBank files form
**031**, which splits commercial and industrial loans into 4.a (US addressees)
and 4.b (non-US). The filing shows `RCFD1251` = 32,260, `RCFD1252` = 32,424,
`RCFD1253` = 295,171 — exactly the values this template had landed. The map now
reads `RCON1606 (031: RCFD1251+1254)` and the three lines tie. The C&I
*balance* row already carried that pattern; the past-due rows had simply never
been given it.

45 of 48 became 48 of 48 as a result. Nothing was plugged and no value moved:
only the citation was wrong, and the tie-out is what found it.

## What I had to know

The reusable half, invisible once the numbers agree:

- **`RCFD` before `RCON`.** For a bank with foreign offices (form 031) the
  FDIC's totals are the *consolidated* ones. Following a bare `RCON` code to
  the facsimile lands on the domestic-only column and looks like a difference.
- **Column A of RC-N excludes nonaccrual.** "Past due 30 through 89 days and
  still accruing" is disjoint from Column C. Adding them would double count.
- **The FDIC's own class rates are over total assets.** Its published
  `P3CRCDR` for this bank and quarter is 0.005; the figure tied here is 0.920.
  Both are correct and they answer different questions. That is why this
  template's own rates are named `P3CRCD_BOOK` and not `P3CRCDR` (#268).
- **The facsimile is an ASP.NET page, not a file.** Getting the PDF or the
  XBRL means a postback to the form's *action* URL, carrying `__VIEWSTATE`;
  a plain GET returns the page, politely, with no document.

## What was not proven

- **One bank, one quarter, one figure in full.** The roster covers 48 lines for
  KeyBank at 2026-06-30. Coverage across banks and quarters is a different job.
- **The chart workbook** was not part of this. It reads the same cells, but
  that link is asserted here, not executed.
- **The browser could not be driven to the pages.** The FFIEC's embedded viewer
  stopped responding to automation; the filing was fetched and served locally
  to capture the two pages. The document is byte-for-byte the regulator's, and
  the fetch is the same postback the tie-out tool uses, but the capture is of a
  locally served copy rather than of the FFIEC page itself. Marked, because it
  is a step performed differently from how it reads.
