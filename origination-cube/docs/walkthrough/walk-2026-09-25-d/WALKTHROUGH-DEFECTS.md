# Origination cube: defects from the fourth walk (25 Sep 2026)

**What was walked:** the no-commands route of ruling OC-22, on commit `1156ff4`, frozen with `git archive` into scratch:
1. The Tk window: Browse, **1. Set up from this extract**.
2. Start here, Control, Columns, Odd values and Learned, answered cell by cell.
3. **2. Run the cube**, then every result tab.
4. The new parts:
   - **Losses vs revenue** (OC-26) under every revenue option: luck, 5%, 10%, the loss lines, an own value of 0.15, and 95 and 0.95.
   - **Split** (OC-27) by REV_DEBT, then by ASSET_CLASS, and the **Three-way** tab for both.
   - The same REV_DEBT split on a copy of the book with no debt effect (`driver/noplant.py`, and through the window).
5. Show per pocket, the LOB's own edges, Set up again, and Forget with two Runs after it.
6. Twenty wrong turns, each in a folder of its own.

The procedure is `PROCEDURE-origination-workbook.pdf` beside this file. The scripts are in `driver/`.

**The book:** `synth.write_extract(n=8000)`, renamed `Consumer book Q3.csv`. It plants a bad pocket (FICO under 620 in Broker), a revolving-debt effect (above the usual debt for the score goes bad 1.8x as often) and asset class 4 at 1.4x. RANR carries no plant.

**The suite at `1156ff4`:** `pytest -q` gave **170 passed** (4 min, Python 3.12 under xvfb). `tools/mutation_check.py` exited 0 with **39 of 39** mutations caught. All of it passes with every defect below present, so none of them is caught.

**The result:**
- **The planted pocket comes out on top** of every loss measure, and on Losses vs revenue it reads **Losing more, earning the same** (GCO 2.62x the rest of its band, RANR 1.05x). With the LOB's edges it's FICO under 620 / Broker, same box, GCO 5.35x.
- **The split finds the debt effect in the score grids:** 1.95x and 1.92x as a bad-rate ratio, against a planted 1.8x, with ranges that include it. On the no-effect book the score grids read 1.16x and 1.15x, ranges including 1.
- **Tie-outs** agree on every run (132; 581 with the number split; 382 with the category split).

Of the sixteen walk-3 fixes, ten held on screen and six held in part. None failed outright. The table is at the end.

This walk found **11 defects**, ranked by what each would cost the firm or the bank on a real job.

---

## 1. On a book with no debt effect, the loan-size grids and the Three-way tab still report one

**What I did:** ran the REV_DEBT split through the window on a copy of the book with the debt plant switched off (the 1.8 set to 1.0, same seed). Read the Split and Three-way tabs.

**What the screen said:**
- **Split, ORIG_BAL x CHANNEL** opens: "The high-REV_DEBT half was worse in 13 of the 15 pockets big enough to test. Holding the pocket fixed, the high half has the outcome 1.62 times as often as the low half (95% range 1.37 to 1.87). Luck alone gives a gap this big under 0.01% of the time." The last of five sentences is: "REV_DEBT's correlation with FICO is -0.53: 0 means unrelated, and the further from 0, the more of this gap may be FICO." ORIG_BAL x ASSET_CLASS reads 1.66x the same way (`defect-1b-no-effect-book-split-sentence.png`).
- **Three-way** ranks ORIG_BAL 49,158 and over / Broker / REV_DEBT high half sixth, in red: 266 loans, 2.77x the rest of its band, flagged **worse** (`defect-1-no-effect-book-three-way.png`). It is flagged worse on all three loss measures. Nothing on the tab says what the pocket holds fixed.

**What was true:**
- There is no debt effect in this book. The high-debt half of a loan-size pocket is the low-score half, and Broker holds the planted low-score pocket. The 1.62x and the red row are the score.
- The OC-27 fix put the caveat on the Split tab only, at the end of each paragraph, after the number and "under 0.01%". It gives a correlation, not how much of the gap it explains.
- **The Three-way tab has no caveat at all.** On the planted book, 12 of the 14 split pockets flagged *worse* for the bad-loan share come from ORIG_BAL grids, where debt and score are mixed. Only 2 come from FICO grids. The list a consultant reads first is mostly the grids the Split tab says not to trust.
- "This grid holds FICO fixed" is only true within a band of about 30 points. That leaves enough in for the planted 1.8x to read 1.95x, and for the no-effect book to read 1.16x.

**Cost:** the consultant tells the bank that large Broker loans with high revolving debt go bad at nearly three times their peers, from a tab that ranks and colours it like any finding. The effect isn't there.

**Fix:** carry the "holds fixed" words onto the Three-way tab: a column per row saying whether its band holds the split column's partner fixed, or a separate block for grids that don't. On the Split tab, say it before the number, not after it. A check that goes red: on the no-effect book, no three-way pocket from a grid that doesn't hold the score fixed should be flagged *worse* without a warning.

## 2. Losses vs revenue: the box compares with the band, but the dollars, the order and the chart's names compare with the book

**What I did:** read the FICO x CHANNEL block and its chart after the first run.

**What the screen said** (`defect-2-box-against-dollars.png`, `defect-2b-chart-names-losing-less.png`):

| Pocket | GCO vs comparison | Box, colour | GCO excess over the book |
|---|---|---|---|
| under 654 / Online | 0.55x, better | Losing less, green | **$271,012** |
| under 654 / Branch | 0.55x, better | Losing less, green | **$249,020** |
| 746 and over / Branch | 1.26x, could be luck | Losing more, red | **-$262,995** |

The chart names the three pockets with the most excess over the book. Two of them are these green *Losing less* pockets, labelled on top of each other left of the 0.80x line.

**What was true:**
- The box, the flag and the chart's x axis use the Control comparison (the rest of the band). The dollar columns, the row order and the choice of names use the book. Under 654 / Online loses more than the book, and less than Broker in its own band.
- Across the tab, **15 of 112 rows** contradict their own dollars: 8 in a *Losing more* box lose less than the book would expect, 7 in a *Losing less* box lose more.
- Walk 3's defect 5 was the box and the flag disagreeing. That's fixed. The dollars now disagree with both.

**Cost:** a pocket costing the bank a quarter of a million dollars over the book is shaded green and labelled on the chart as one of the three biggest, in the "losing less" corner. An analyst either drops a real cost or can't explain the chart.

**Fix:** make the dollars, the order and the names use the same comparison as the box: the excess over the rest of the band when Control says band. Or keep the book dollars and say in the column heading and on the chart that they are against the book, and don't name a pocket as a bleeder when its box says *Losing less*.

## 3. Losses vs revenue boxes and colours pockets the Control minimums say not to test

**What I did:** set *Fewest loans with a loss* to 10 on Control and read Losses vs revenue.

**What the screen said:** (marked missing) / Broker, 54 loans, GCO flag **too few losses to test**, sits in **Losing more, earning the same** and is shaded red. (marked missing) / Online, 55 loans, same flag, is in **Losing less, earning less**, shaded amber (`defect-3-untested-pockets-boxed.png`). With the 5% revenue line, the Broker one moves to **Losing more, earning more**.

**What was true:** the tab skips a pocket under the minimum *loans*, but not one under the minimum *losses*. Six rows on the first run are boxed on a GCO the tab itself calls too thin to test. Walk 3's defect 4 fix covered the Split tab and the heat maps and didn't reach this tab.

**Cost:** smaller than defect 2, because the flag beside it says "too few losses to test". But the box and colour are what a reader scans.

**Fix:** leave the box empty (or "not tested") and the row unshaded when either side's flag is *too few loans* or *too few losses*.

## 4. The suggested revenue line is one number for every pocket, and it moves when anything else in the run changes

**What I did:** picked *What luck alone can move it (suggested)*, ran, then ran again with a category split and with the LOB's edges, changing nothing else about revenue.

**What the screen said:**
- First run: "Revenue counts as more at 1.25x or above and less at 0.80x or below: what luck alone can move it: in a pocket of typical size, a revenue gap smaller than 1.25x can't be told from luck at 95% sure and 80% caught" (`step-13-losses-vs-revenue.png`).
- With ASSET_CLASS split: **1.22x and 0.82x**. (marked missing) / Broker moves from *Losing more, earning the same* to **Losing more, earning more**, and REV_DEBT 6,559 to under 9,837 / Branch from *About the same on both* to **Losing the same, earning more**. Their numbers didn't change (`defect-4-line-moves-with-the-split.png`).
- With the LOB's edges: 1.24x.
- On Control, the *In use* cell says "What luck alone can move it (suggested)" and no number. The number first appears after a Run.

**What was true:**
- The line is the median, over the pockets in this run's grids, of each pocket's smallest detectable RANR gap. Change the grids and the median changes, so boxes move on a split or a band change.
- It is applied to every pocket alike. For a 530-loan pocket, 1.25x is about right. For a 55-loan pocket, luck alone moves revenue much further. So (marked missing) / Online reads **earning less** at 0.73x on 55 loans, where its own flag says "could be luck". That is the walk-3 defect 1 pattern, a box on noise, for the small pockets.
- It isn't what luck alone moves. It's the gap a typical pocket catches 80% of the time. What luck alone moves a typical pocket is about **1.17x** (the same sum with the catch rate at 50%: `driver/luckline.py`). So it also moves if someone changes *How often a real gap should be caught*, a method setting.
- On this book it is 1.248, and *The same lines as for losses* is 1.25. The two options gave identical boxes, so this walk couldn't show the suggested option doing anything its neighbour doesn't.

**Cost:** two runs of the same book, one with a split added, put the same pocket in different boxes. An analyst comparing runs, or a reviewer rerunning one, can't reconcile them.

**Fix:** work the line out from the book, not the run's grids: each pocket's own luck range (its RANR test at the Control confidence), or one line from the whole book fixed at Set up and shown on Control before the Run. Call it what it is if it stays the 80% gap.

## 5. A revenue own value of 95 is told to type 0.95, which is then refused

**What I did:** typed 95 in *Or enter your own* for *How far revenue must move* (wrong turn M). Then did what the message said.

**What the screen said:** "Control!D21: "How far revenue must move before it counts as more or less" needs a share, such as 0.1 for 10%, from 0.01 to 0.9; got 95. For 95%, type 0.95." Then, with 0.95: "... from 0.01 to 0.9; got 0.95." (`step-13d-revenue-95-refused.png`, `step-13e-revenue-095-refused.png`)

**What was true:** the "For 95%, type 0.95" hint was carried over from the *How sure* row, where 0.95 is valid. Here the most allowed is 0.9.

**Cost:** two refused runs and a message that contradicts itself. Small, but it's the first thing someone hits when trying their own line.

**Fix:** for this row, say "For 15%, type 0.15", or work out the hint from the value typed, and only when it's in range.

## 6. The booked amount can split the pockets

**What I did:** set *Split pockets by it?* on ORIG_BAL, the column marked *Booked amount* (wrong turn I2).

**What the screen said:** it ran, "571 tie-out checks agree", "Split by ORIG_BAL ... ORIG_BAL isn't cut on its own while it splits" (`wrong-split-booked.png`). GCO, the key and the outcome were each refused, naming the cell: "Only a score, ratio, amount or category can."

**What was true:** OC-27 and the walk-3 status table say only a score, ratio, amount or category can split. The booked amount is none of those as marked, and walk 3's fix list named it as one to refuse. It's also the weight in two of the four rates, and splitting by it takes ORIG_BAL out of the bands.

**Cost:** low. A split by loan size is a question someone might ask. But the rule on screen and the behaviour disagree.

**Fix:** refuse it like the other required columns, or change the message and OC-27 to say the booked amount can split.

## 7. The Losses vs revenue charts are still hard to read

Seen in `step-13b-chart.png`, `step-21b-own-edges-losses-vs-revenue.png` and `step-13c-revenue-5-percent.png`:
- **Names overlap.** "under 654 / Online" and "under 654 / Branch" print on top of each other and over other dots. The REV_DEBT charts have the same.
- **The revenue axis has no 1.00x tick.** Ticks run 0.68x, 0.78x, 0.88x, 0.98x, 1.08x.
- **Only three ticks across:** 0.10x, 1.00x, 10.00x. Every pocket sits between 0.2x and 5x, and the 0.80x and 1.25x lines have no labels.
- **The revenue axis title is cut off** on some charts ("RANR vs comparison (up = earning more)").
- **Box names aren't on the chart.** Known from walk 3.
- **With nine boxes filled**, the count line above a block runs under the chart and is cut off ("... Losing the same, earning more: 2; Lo").
- **In print**, charts break across pages with the table headers not repeated.

**Fix:** labels only for the named three with a leader line, or a table beside the chart; a tick at 1.00x on both axes; the Control lines labelled; the count line wrapped.

## 8. "Luck alone" shows 0.0% beside "under 0.01%"

On Where it bleeds, Split and Three-way, a p-value between 0.01% and 0.05% prints as **0.0%**, next to others that print "under 0.01%". FICO under 654 / Online on Where it bleeds reads "0.0%" (it's 0.037%). *0.0%* reads as "never", which is stronger than "under 0.01%" (`step-12-where-it-bleeds.png`).

**Fix:** a format of `0.00%` for small values, or "under 0.1%".

## 9. Start here doesn't recount after a Run, and the message box still hides the end of a refusal

- **Start here** after the first run says **Things to look at first on Columns: 7**, with C3 = Yes and every column confirmed. It drops to 2 only at the next Set up (`step-17b-start-here-after-run.png`, `step-22b-start-here-after-set-up-again.png`). Walk 3's status table says Start here now recounts; on screen it recounts at Set up only.
- **The window's box** hides the last three lines of the first refusal, including the new revenue call and Columns!C3 (`step-08-run-before-answering.png`). Marked open since walk 2.

## 10. Losses vs revenue and Control: small layout and wording

- On Control, the revenue question wraps to two lines and squashes the *Is it real* heading under it (`step-09-control-answered.png`).
- The option's label, "(suggested)" and all, is copied into *In use* and onto Check: "What luck alone can move it (suggested)".
- The option's explanation, "Inside it, revenue reads as about the same", doesn't say inside what.
- The *GCO excess over the book ($)* heading wraps and the "($)" is cut off.

## 11. Other wording

- **Show per pocket:** "not tested, and a average doesn't add up across pockets" (`step-20-show-per-pocket.png`).
- **After a Forget, Columns contradicts itself:** CHANNEL's row says "Forgotten on Learned: confirm what it is." beside "Remembered: you confirmed this as a category ... on 2026-09-25" (`step-23d-columns-after-forget.png`).
- **The second Run after a Forget** says only "Columns!C3: set Checked every column to Yes", not that CHANNEL was forgotten (`step-23c-second-run-refused.png`).
- **The Learned subtitle** still says "To stop it being learned again, also change it on Columns". A Forget now does that by itself.
- **Control, materiality:** the 2% option explains itself as "Between the two." There are now five levels.
- **Picked the workbook, then Run:** Set up refuses correctly, but Run then says "There's no workbook for Consumer book Q3 - Origination Cube.xlsx yet. Press 1. Set up from this extract first." Set up will refuse again (`wrong-picked-workbook-run.png`).
- **A renamed column:** the message ends "press Set up again" with no full stop (`wrong-extract-renamed-col.png`).
- **After Set up, the window says** "fill in the shaded cells on Control and Columns" and leaves out Odd values (`step-03-after-set-up.png`).
- **A split run drops the "Worst for RANR" line** without a word, because REV_DEBT stops being a band (`step-18b-after-split-run.png`).

---

## What I couldn't check

- **Real Excel.** Every tab was seen through LibreOffice and set with openpyxl. Not seen:
  - the charts as Excel draws them: the scale of tens, the dashed Control lines from the hidden `_chart` sheet, the data labels. LibreOffice drew them; Excel may place labels differently.
  - whether Excel's data validation stops 95 in *Or enter your own* before Run sees it (openpyxl writes past it)
  - how dropdown picks are stored, conditional shading, frozen panes and column widths
- **Windows.** The file dialog, Segoe UI, **Open the workbook**, and a real Excel lock (simulated with `chattr +i`).
- **A book where the luck line and the loss lines differ.** On this book they came out at 1.248 and 1.25, so the suggested option and *The same lines as for losses* couldn't be told apart on screen.
- **Why "the three biggest bleeders" are picked by excess over the book.** The code does it that way (`_revenue_chart`, `rows[:3]` after sorting by book excess). Whether the firm meant that is a question for them.
- **Whether a split half with losses against one with none counts as worse** (walk-3 defect 7's second half). The counts looked right ("14 of the 15"), but no pocket on this book had a zero-loss low half at the minimums, so I didn't see the case.
- **The many-tests allowance across grids.** Still open from walk 3: a RANR pocket is flagged *worse* on a book with no RANR effect.
- **Scale.** 8,000 loans. Each run took a few seconds.
- **Memory across the wrong turns.** Every folder used one scratch memory file, so *Times* on Learned counts every run of the walk.

---

## Where each walk-3 defect stands (seen on screen, `1156ff4`)

| # | Walk-3 defect | Now |
|---|---|---|
| 1 | Worst bleeders read "earning more" on noise | **Held.** Nine boxes; the planted pocket reads *Losing more, earning the same*; rows sort by GCO excess (`step-13-losses-vs-revenue.png`). New problems in the same tab: defects 2, 3 and 4. |
| 2 | A split finds debt where the score isn't held fixed | **Held in part.** Each grid says what it holds fixed, with the correlation, and FICO grids come first (`step-18c-split-tab.png`). On the no-effect book the ORIG_BAL grids still lead with 1.62x "under 0.01%", and the Three-way tab ranks the same thing in red with no caveat (defect 1). |
| 3 | A category split gives pictures only | **Held.** Every three-way pocket tested and ranked (`step-19b-three-way-category.png`); Check and the window name the split (`step-19-after-category-split.png`). |
| 4 | Split and heat maps ignore the minimums | **Held in part.** Split halves and heat-map cells under the minimums are blank, with a note (`step-14-grids.png`). Losses vs revenue still boxes and colours pockets with too few losses (defect 3). |
| 5 | Box and flag compare different things | **Held in part.** Box and flag now agree, and the subtitle says which comparison. The dollars, order and chart names use the book, so rows now contradict their dollars (defect 2). |
| 6 | "Chance it's luck"; odds lead | **Held.** "Luck alone", explained on each tab; the rate ratio leads (1.95x), odds follow. Small: 0.0% beside "under 0.01%" (defect 8). |
| 7 | Split takes any column | **Held in part.** GCO, the key and the outcome are refused, naming the cell (`wrong-split-gco.png`, `wrong-split-key.png`, `wrong-split-outcome.png`). The booked amount is accepted (defect 6). |
| 8 | A dollar line applies to RANR | **Held.** "$100,000 of GCO"; every other rate says "no line" with a warning in words; the window keeps its RANR line (`wrong-own-materiality-check.png`). |
| 9 | Forget lasts one Run | **Held.** The second Run refuses until C3 is Yes, and Columns names the forgotten column (`step-23c-second-run-refused.png`, `step-23d-columns-after-forget.png`). Wording in defect 11. |
| 10 | The workbook taken as the extract | **Held.** Refused, naming the extract (`wrong-picked-workbook.png`). Run afterwards points back to Set up (defect 11). |
| 11 | The chart | **Held in part.** One chart per grid, 1.00x on an x tick, the Control lines drawn, three pockets named. Names overlap, the y axis has no 1.00x tick, and two of the three names can be *Losing less* pockets (defects 2 and 7). |
| 12 | Labels cut off | **Held.** Band labels whole on every tab ("15,449 to under 26,324"); "Vs the rest of its band" whole. New: the "($)" in one heading (defect 10). |
| 13 | Excess in whole loans | **Held.** "90.7 loans" (`step-12-where-it-bleeds.png`). |
| 14 | Show per pocket | **Held.** A note says it isn't tested and doesn't add up; whole numbers for amounts. "a average" (defect 11). |
| 15 | Window and status wording | **Held in part.** Held: the split named in the window, two splits naming both cells, a split that empties the segments saying why, a renamed column saying "a segment" and to press Set up, the file name showing in the Extract box, Set up counting new columns. Not held: Start here's "things to look at" still stale after a Run, and the box still scrolls (defect 9). |
| 16 | Materiality levels Control can't pick | **Held.** Control offers 0.5%, 1%, 2%, 5% and 10%; each heading names its total (`step-15-materiality.png`). The 2% option's text is stale (defect 11). |

---

## Where each defect stands (25 Sep 2026, after the fixes)

These fixes also cover the two commits this walk didn't see (`4e5d7aa`, `83a7b01`). Every fix is held by a test, and `tools/mutation_check.py` puts the bug back to prove it. Seen through LibreOffice.

| # | Defect | Now | Test |
|---|---|---|---|
| 1 | A debt effect reported where the score isn't held fixed | **Fixed within the firm's choice (keep every grid, labelled).** The Split tab says what each grid holds fixed before the number. Every Three-way row carries it, and rows from grids that hold it fixed come first | `test_three_way_rows_say_what_their_grid_holds_fixed` |
| 2 | Box against the band, dollars against the book | **Fixed.** The dollars, the order and the chart's names all use the box's comparison. Only pockets in a "Losing more" box are named | `test_losses_vs_revenue_dollars_agree_*` |
| 3 | Untested pockets boxed and coloured | **Fixed.** "Not tested: too few loans or losses", no colour, off the chart | `test_losses_vs_revenue_dollars_agree_*` |
| 4 | The luck line | **Fixed in part.** It is now luck alone at the Control confidence, not the 80% catch gap (1.16x on the demo book, not 1.25x). A side only counts as more or less when its own test agrees, so a small pocket can't cross on noise. It is still one number worked out from the run's pockets, so it moves a little with the bands; Check and the tab say so | `test_the_luck_line_is_luck_alone_*`, `test_the_planted_pocket_is_not_read_as_earning_more_*` |
| 5 | 95 told to type 0.95, then refused | **Fixed.** The hint is given only when it's allowed; otherwise "for 15%, type 0.15" | `test_a_revenue_share_of_95_*` |
| 6 | The booked amount can split | **No change, by design.** It's an amount; the message now says so | — |
| 7 | Charts | **Fixed in part.** A tick at 1.00x on both axes, a shorter title, names only for "Losing more" pockets and placed apart, and the count line wraps above the table. The box names still aren't on the chart, and a page break can still split a table | seen on render |
| 8 | 0.0% beside "under 0.01%" | **Fixed.** Two places under 1% | — |
| 9 | Start here after a Run; the message box | **Fixed.** After a Run the count is what a Forget marked; the window is taller | — |
| 10 | Control layout and wording | **Fixed in part.** "(suggested)" is dropped where the answer is read back, and the explanation says "inside that gap". The question row's wrap on Control is not changed | — |
| 11 | Other wording | **Fixed.** "an average"; after a Forget the Why cell no longer says "Remembered", and the C3 refusal names what was forgotten; the Learned subtitle; the 2% option; Run with the workbook picked; the full stop; Odd values in the Next line; "Nothing is worse for ..." when a measure has no worst pocket | `test_the_learned_tab_prunes_*` |
