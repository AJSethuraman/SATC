# Advice sweep, 3 Oct 2026

The firm's rule, now in `pocketbook/VOICE.md` (*Facts, calculations and rules only — no advice or interpretation*):

> *"literal facts, calculations, our rules around leaving comments are fine. stuff like this i don't ask for"*

said of a Glossary line telling the reader to compare loans within a vintage because older loans have had more time
on book.

Every user-visible string in `src/pocketbook/audit.py` (the audit workbook) and `src/pocketbook/glossary.py` (the
Glossary tab) was read against it. A sentence came out or was rewritten when it told the reader how to read a figure,
what a figure implies, what to compare it with, what to conclude, or what to do next. Definitions, calculations, the
rules PocketBook applies, and how-to steps (every By hand instruction) were kept. No label a test looks up changed
except one note label, *The question*, which no test reads.

**15 strings changed: 6 in the Glossary, 9 in the audit workbook.**

## Glossary (`glossary.py`)

| # | Term, column | Before | After |
|---|---|---|---|
| G1 | Avg line / Line × book, What it means | … Line × book compares a pocket's average line with the whole book's. | … Line × book is a pocket's average line divided by the whole book's. |
| G2 | Rate (GCOs ÷ Booked, RANR ÷ Booked), What it means | Dollars per $100 booked, which allows a small pocket to be compared with a large one. A rate of 2.20% equals $2.20 per $100 booked. | Dollars per $100 booked: the dollar figure divided by booked dollars. A rate of 2.20% equals $2.20 per $100 booked. |
| G3 | Borderline, What it means | The p-value is within the shuffle test's margin of error of the threshold, so another Run could reach the opposite result. The reading stands, and the flag serves as a caution. | The shuffle test's p-value is within 2 standard errors of the threshold on Control, on either side. The reading is unchanged, and the flag is shown beside it. |
| G4 | Borderline, Example | A Worse? cell reading Yes · borderline (p 0.048) is under the 5% threshold, but close enough to change on another Run. | A Worse? cell reading Yes · borderline (p 0.048) has a p-value under the 5% threshold and within 2 standard errors of it. |
| G5 | Shuffle test / p-value, What it means | The p-value is how often chance alone would produce a gap this large. The shuffle test reassigns loans at random many times and counts how often that happens. | The shuffle test reassigns loans at random many times and counts the shuffles with a gap at least as large as the actual one. The p-value is (that count + 1) ÷ (shuffles + 1). |
| G6 | Odd values, Example | A score of -9999 on many loans is usually a code for no score. Select Missing under Treat as on Columns. | A score of -9999 on many loans is shown as an odd value. Missing under Treat as on Columns places those loans in (marked missing). |

G3 and G4 state the rule `stats.borderline` applies (`BORDERLINE_SE` = 2 standard errors, either side of the
threshold); the "2" is read from that constant.

## Audit workbook (`audit.py`)

| # | Where | Before | After |
|---|---|---|---|
| A1 | One pocket, RANR, Definition | RANR dollars for the same loans. A negative figure means the pocket lost money overall. | RANR dollars for the same loans. |
| A2 | One pocket, RANR gap in points, against the book, Definition | The pocket's RANR rate less the rest of the book's, in percentage points. A negative figure means the pocket keeps less per booked dollar. This is RANR's Gap pts … | The pocket's RANR rate less the rest of the book's, in percentage points. This is RANR's Gap pts … |
| A3 | One pocket, RANR dollars, against the book, Definition | … at the rest of the book's rate. A negative figure is a shortfall. This is RANR's Dollars … | … at the rest of the book's rate. This is RANR's Dollars … |
| A4 | One pocket, RANR + GCOs dollars, against the book, Definition | … at the rest of the book's rate. A negative figure is a shortfall. This is RANR + GCOs' Dollars … | … at the rest of the book's rate. This is RANR + GCOs' Dollars … |
| A5 | One pocket, RANR dollars, against its band, Definition | … at the rest of its band's rate. A negative figure is a shortfall. This is RANR's Dollars … | … at the rest of its band's rate. This is RANR's Dollars … |
| A6 | One pocket, RANR + GCOs dollars, against its band, Definition | … at the rest of its band's rate. A negative figure is a shortfall. This is RANR + GCOs' Dollars … | … at the rest of its band's rate. This is RANR + GCOs' Dollars … |
| A7 | Shuffle test, note | **The question:** Could the pocket's gap have arisen by chance? The test reassigns the pocket's label to loans at random many times, and counts how often chance alone produces a gap this large. | **The test:** The test reassigns the pocket's label to loans at random many times, and counts the shuffles that produce a gap at least as large as the actual one. |
| A8 | Shuffle test, part B, when the random pocket was not tested | This pocket was not tested (too few losses, or no comparison group), so it has no p-value. Select another pocket on the One pocket sheet. | This pocket was not tested (too few losses, or no comparison group), so it has no p-value and no shuffles are listed. |
| A9 | Shuffle test, part C note | … and it follows the selection on One pocket. If the two tests point in opposite directions, the pocket warrants a closer look. | … and it follows the selection on One pocket. |

A1 to A6: each definition already states the subtraction (*the pocket's RANR less the RANR it would have earned at
…*), so the sign follows from the calculation; the removed sentences told the reader what a negative figure means.
A8's removed step was also wrong: part B lists the shuffles of the pocket selected at random only, and picking
another pocket on One pocket does not change it.

## Read and kept

| Where | Text | Why it stays |
|---|---|---|
| Glossary, RANR + GCOs | RANR with GCOs added back, which shows what the loans earned before losses. | What the sum is: RANR is after charge-offs, so adding GCOs back is before them. A definition. |
| Glossary, × book | 2.00× means twice the GCOs per booked dollar. | The arithmetic of a multiple. |
| Glossary, Odd values, What it means | Values that may be codes rather than genuine numbers, such as … | The rule PocketBook uses to flag a value, in the Columns tab's own words (the Glossary repeats a tab's wording where one exists). |
| Glossary, Filter, Origination year examples | Choose … as Filter by in the launcher, then select … | How-to steps. |
| Audit, Start here | Suggested order of review: | The reading order of the sheets, a how-to; the label is `audit.ORDER`. |
| Audit, Start here | This workbook is independent of the main workbook, so it can be edited freely without affecting it. | A fact about the file; it is `VOICE.md`'s own approved example. |
| Audit, One pocket section titles | … (for reference only; the Run judged pockets against the book) | States which comparison the Run used. |
| Audit, every By hand column | Filter the Loans sheet to … ; the status bar shows … | How-to steps, kept as the rule says. |
