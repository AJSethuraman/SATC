# Origination cube: defects from the third walk (25 Sep 2026)

**What was walked:** the no-commands route of ruling OC-22, on commit `00c0bdd`, frozen with `git archive` into scratch:
1. The Tk window: Browse, **1. Set up from this extract**.
2. Start here, Control, Columns, Odd values and Learned, answered cell by cell.
3. **2. Run the cube**, then every result tab: Where it bleeds, Losses vs revenue, Grids, Materiality, Check, Log.
4. The new parts: **Split** by REV_DEBT (a number), then by ASSET_CLASS (a category); **Show per pocket**; own band edges with semicolons.
5. **Set up** again after a run, and **Forget** on Learned.
6. Fourteen wrong turns, each in a folder of its own.

The procedure is `PROCEDURE-origination-workbook.pdf` beside this file. The scripts are in `driver/`.

**The book:** `synth.write_extract(n=8000)`, renamed `Consumer book Q3.csv`. It plants a bad pocket (FICO under 620 in Broker), a revolving-debt effect (above the usual debt for the score goes bad 1.8x as often) and asset class 4 at 1.4x. RANR carries no plant.

**The suite at `00c0bdd`:** `pytest -q` gave **160 passed** (3 min). `tools/mutation_check.py` exited 0 with **32 of 32** mutations caught. All of it passes with every defect below present, so none of them is caught.

**The result:**
- **The planted pocket comes out on top.** FICO under 654 / Broker is first for all three loss measures: 523 loans, 24.47% bad against 7.13%, 4.14x the rest of the book. With the LOB's edges (620; 680; 740) it's FICO under 620 / Broker at 53.4%, 8.78x.
- **The split finds the revolving-debt effect,** but reads it as 1.97x to 2.57x (bad-rate ratio) depending on the grid. On a copy of the book with no revolving-debt effect at all, two of the four grids still report one, with "chance it's luck under 0.0001" (defect 2).
- **Tie-outs** agree on every run (132, 493 with the split, 316 with the category split).

Twelve of the sixteen walk-2 fixes held on screen, three held in part, and one (the scrolling message box) was already marked open. The table is at the end.

This walk found **16 defects**, ranked by what each would cost the firm or the bank on a real job.

---

## 1. Losses vs revenue puts the worst loss pockets in "earning more" on revenue differences the tool itself calls noise

**What I did:** ran the answered workbook and opened **Losses vs revenue**.

**What the screen said:** the three pockets with the biggest GCO excess are in the amber box **Losing more, earning more** (`defect-1-worst-pockets-in-earning-more.png`):

| Pocket | GCO vs book | RANR vs book | GCO excess | RANR flag |
|---|---|---|---|---|
| FICO under 654 / Broker (the planted pocket) | 3.67x | 1.05x | $1,757,039 | in line |
| REV_DEBT 17,187 and over / Broker | 3.05x | 1.02x | $1,272,421 | in line |
| FICO under 654 / asset class 4 | 3.19x | 1.04x | $1,039,185 | in line |

**What was true:**
- **The box is decided by which side of 1.00x the rate falls, and nothing else** (`book.py`, `_losses_vs_revenue`).
- **The extra revenue isn't real.** All 24 pockets in *Losing more, earning more* have a RANR flag of *in line*. The test data gives RANR no relation to anything.
- **The biggest bleeder is 19th on the tab.** The rows sort by box first, so 18 smaller pockets in the red box come above the planted one.

**Cost:** this tab exists for the firm's question, "GCO is high but profit is high, do we care? maybe" (OC-24). Here it answers "maybe" for the three worst pockets in the book, on a revenue gap of 2 to 5% that its own test says is luck. An analyst reading the boxes would soften the finding that matters most.

**Fix:** put a pocket in an "earning more" or "earning less" box only when the RANR flag says the difference is real. Otherwise use a fifth state, like "revenue in line". Sort by GCO excess across boxes, or at least say the order.

## 2. The split reports a revolving-debt effect in grids where the score isn't held fixed, including on a book with no effect

**What I did:** set **Split pockets by it?** = Yes on REV_DEBT and ran (step 18). Then I built a copy of the same book with the revolving-debt plant switched off (`driver/noplant.py`: the 1.8 set to 1.0, same seed, everything else the same) and ran the same split through the window.

**What the screen said:** four grids, four answers to one question, with no guidance on which to read (`step-18c-split-tab.png`, `step-18d-split-orig-bal.png`):

| Grid | Planted book: odds / bad-rate ratio | Book with **no** effect: odds / bad-rate ratio |
|---|---|---|
| FICO x CHANNEL | 2.13x / 1.97x, worse in 16 of 18 | 1.19x / 1.18x, worse in 9 of 18, p 0.096 |
| FICO x ASSET_CLASS | 2.06x / 1.93x, worse in 20 of 24 | 1.16x / 1.15x, worse in 11 of 24, p 0.17 |
| ORIG_BAL x CHANNEL | 2.73x / 2.55x, worse in 15 of 15 | **1.66x** / 1.62x, worse in 13 of 15, **p 0.0000013** |
| ORIG_BAL x ASSET_CLASS | 2.76x / 2.57x, worse in 20 of 20 | **1.70x** / 1.66x, worse in 17 of 20, **p 0.00000046** |

On the no-effect book the Split tab reads: "The high-REV_DEBT half was worse in 17 of 20 pockets. Pooled across pockets, its odds of the outcome are 1.70x the low half's (95% range 1.38 to 2.09); chance it's luck under 0.0001. The effect is about the same in every pocket" (`defect-2-split-finds-debt-that-isnt-there.png`).

**What was true:** revolving debt runs higher as the score falls. Splitting at each pocket's own median only holds fixed what the pocket holds fixed. In a loan-size pocket, the high-debt half is also the low-score half, so the split re-sorts the score. That is the exact problem OC-23 chose the per-pocket median to avoid, and it only avoids it in the score grids. Even there, five equal bands leave some of it: 1.97x against a planted 1.8x.

**Cost:** a consultant tells the bank revolving debt nearly triples the odds of going bad, from a grid that can't separate it from the score. Or reports an effect that isn't there at all, with "chance it's luck under 0.0001" beside it.

**Fix:**
- Say on the Split tab what each grid holds fixed, and point the reader to the grid whose band is the score. Or show the split only in grids whose band is a score.
- Test whether the split column moves with the band (it does here), and say so in the pooled sentence.
- Add a check that goes red: a split on a book with no effect should come out near 1.

## 3. A split by a category produces pictures only, and quietly removes that column from everything else

**What I did:** set ASSET_CLASS to split and ran (step 19).

**What the screen said:**
- **Grids** repeats each grid once per asset class, as multiples of the book only (`step-19b-category-split-grids.png`).
- **The Split tab** is a title and one sentence (`step-19c-split-tab-category.png`).
- **The window** doesn't mention the split (`step-19-after-category-split.png`).

**What was true:**
- **The three-way pockets are never tested or ranked.** FICO under 654 / Broker / asset class 3 at 4.17x the book (111 loans) is in no list, has no test and no dollars. Nothing shows loan counts. The *(marked missing)* pockets hold 11 to 16 loans each and are painted as strongly as the rest.
- **ASSET_CLASS stops being a segment without a word.** `read_book` adds the split column to the skip list. Where it bleeds, Losses vs revenue and Materiality lose both ASSET_CLASS grids. Before the split, the third and fourth largest bad-loan excesses were FICO under 654 / asset class 4 (52 loans) and REV_DEBT 17,187 and over / asset class 4 (49 loans). After it, both rows are gone.
- **Check doesn't record the split** for either kind: which column, how, or what it took out of the cuts. The audit trail is only in the `what ran.yaml` file.

**Cost:** the layer the firm asked for ("kind of specifically want this option") can't be defended to the LOB, because it carries no test. The rest of the analysis silently changes shape.

**Fix:** rank and test the split pockets (on Where it bleeds, or on the Split tab with loans, rate, excess and flag). Say in the window and on Check that ASSET_CLASS is split, and so isn't a segment. Put the split on Check.

## 4. The split and the heat maps ignore the minimum loans and losses the analyst set

**What I did:** set "Fewest loans in a pocket before it is tested" to 30 and "Fewest loans with a loss" to 10 on Control, then read Split and Grids.

**What the screen said:**
- **Split, FICO x CHANNEL:** *(marked missing) / Broker* high half vs low **6.00x**, deep red, chance it's luck 0.0386 (`step-18c-split-tab.png`). It's counted in "worse in 16 of 18 pockets".
- **Grids:** the *(blank)* row (1 loan) shows 0.00x in green. *(marked missing) / Broker* (54 loans, "too few losses to test" on Where it bleeds) is 4.58x the rest of its band, the reddest cell on the page (`step-14-grids.png`).

**What was true:** the halves of that pocket hold 27 and 27 loans, with 6 and 1 bad. Both are under the 30-loan minimum. `engine._split` compares any half with 2 loans or more, and the heat maps colour every cell.

**Cost:** the reddest cells a reader sees first are the ones the analyst told the tool not to judge.

**Fix:** apply the same minimums in the split, and leave untested cells unshaded (or grey) on Grids and Split, with loan counts available.

## 5. On Losses vs revenue, the box and the flag compare different things

**What I did:** read the flags beside the boxes.

**What the screen said:** FICO under 654 / Branch sits in **Losing more, earning less** (GCO 1.40x the book) with a GCO flag of **better** (`step-13-losses-vs-revenue.png`). Across the tab, 7 pockets in a *Losing more* box are flagged better or "better, but could be luck", and 8 in a *Losing less* box are flagged worse. The subtitle says: "The flags say whether each difference is more than luck."

**What was true:** the box compares with **the book**, and the flag with **the rest of the band** (the Control answer). The headers "GCO flag" and "RANR flag" don't say which. Where it bleeds does say it ("Flag (vs the rest of its band)").

**Cost:** a row that contradicts itself, on the tab meant to settle "do we care?".

**Fix:** name the comparison in the flag headings, and fix the subtitle. Better, flag against the book here, since the boxes are against the book.

## 6. "Chance it's luck" is a p-value, and the split's headline number is odds, not the bad rate

**What the screen said:**
- Every tab heads its p-value **"Chance it's luck"**.
- The split sentence for the bad-loan share gives **odds**: "its odds of the outcome are 2.13x the low half's". The sentence below it, for booked dollars, gives a rate ratio ("loses 2.08x what it would at the low half's rate").

**What was true:**
- A p-value is the chance of a gap this big if there were no real difference. It isn't the chance the finding is luck. An analyst who says "a 5% chance this is luck" to the LOB is wrong.
- The pooled bad-rate ratio for FICO x CHANNEL is 1.97x (the engine computes it; the sentence doesn't show it). Odds overstate a rate ratio, more so in pockets with high bad rates, like the planted one at 24%.

**Cost:** the two figures a consultant is most likely to quote are both slightly wrong in plain words.

**Fix:** a heading that is true and plain, like "How often a gap this big happens by chance". Lead the split sentence with the bad-rate ratio, and keep the odds as the test.

## 7. Split takes any column, and says nonsense for the wrong ones

**What I did:** set the split on GCO_AMT, then on LOAN_NBR (wrong turn I).

**What the screen said:**
- **GCO_AMT:** it ran, with 677 tie-outs agreeing. The Split tab says "The high-GCO_AMT half was worse in **1 of 14** pockets. Holding the pocket fixed, the high half loses **93.83x** what it would at the low half's rate; chance it's luck under 0.0001" (`wrong-split-gco-tab.png`).
- **LOAN_NBR:** it ran. The Split tab says "Not enough loans in both halves of any pocket to compare" (`wrong-split-key.png`).

**What was true:**
- **GCO is the loss itself,** so splitting by it is circular.
- **"1 of 14" undercounts.** A pocket whose low half has no losses has no multiple, so it isn't counted as worse. The same thing happens on REV_DEBT, where *(marked missing) / Branch* has a blank multiple and is counted in the 18 but not the 16.
- **The loan number isn't a number.** The message blames the pocket sizes.

**Fix:** refuse a split on the key, the outcome, GCO, RANR, the booked amount, dates and servicing columns, naming the cell. Count a high half with losses against a low half with none as worse.

## 8. A dollar materiality line applies the same dollars to revenue

**What I did:** typed 100000 in *Or enter your own* for "Smallest excess loss worth reporting" (wrong turn J).

**What the screen said:**
- **Check:** "Materiality line: RANR per booked dollar: 100,000 RANR_AMT dollars" (it was 8,288 at 1%). "Smallest excess loss worth reporting: 100000", with no separator.
- **Warning:** "outcome_loans counts loans, not dollars, so the dollar materiality line is not applied to it" (`wrong-own-materiality-check.png`).
- **The window:** the *Worst for RANR* line disappears, and nothing says why (`wrong-own-materiality.png`).

**What was true:** RANR's total on this book is about $830,000 against $9.96 million of GCO. A loss line in dollars makes every RANR shortfall immaterial. The setting is worded as a loss, the Materiality tab offers no dollar levels to compare, and the warning uses a machine name.

**Fix:** keep a dollar line for losses only, and give RANR its own line (or a share). Print the setting with its unit, and the measure in words.

## 9. Forget on Learned lasts one Run

**What I did:** set CHANNEL to Forget, ran, then ran again (step 23).

**What the screen said:** the first Run says "Forgot CHANNEL, as marked on Learned." (`step-23b-after-forget-run.png`). The second Run says nothing, and Learned shows CHANNEL back with *Times* 1 (`step-23c-learned-after-second-run.png`). Between the two, Columns still says "Remembered: you confirmed this as a category..." for CHANNEL.

**What was true:** the fix for walk-2 defect 5 stops the same run re-learning the column. The next Run learns it again from Columns, which still says category with C3 = Yes. The Learned subtitle does say "To stop it being learned again, also change it on Columns", but a correct meaning that the analyst wanted forgotten has no way to stay forgotten.

**Fix:** after a Forget, clear C3 for that column or shade it "forgotten: confirm again", so re-learning needs a person's yes (OC-15).

## 10. Picking the workbook as the extract sets up a workbook from the workbook

**What I did:** after Set up, picked `Consumer book Q3 - Origination Cube.xlsx` in Browse (the file filter offers .xlsx, and both files sit side by side), then pressed Set up (wrong turn K).

**What the screen said:** "Set up Consumer book Q3 - Origination Cube - Origination Cube.xlsx from Consumer book Q3 - Origination Cube.xlsx: 11 loans, 4 columns." (`wrong-picked-workbook.png`)

**What was true:** it read the Start here tab as loans and wrote a second workbook. Only "11 loans" gives it away. On a bank whose extracts arrive as .xlsx, the two files look alike in the picker.

**Fix:** refuse a file whose name ends " - Origination Cube.xlsx", and name the extract beside it.

## 11. The Losses vs revenue chart is hard to read

Seen in `step-13b-chart.png`:
- **No labels.** None of the 112 dots is labelled, and nothing on the chart links a dot to a row. The planted pocket is one unlabelled dot among many.
- **The 1.00x line isn't on a tick.** The axis starts at 0.1, so the ticks are 0.1x, 0.6x, 1.1x, 1.6x, and the dashed line sits between labels.
- **One pocket squashes the rest.** With the LOB's edges, FICO under 620 / Broker is at 8.1x, and every other dot is packed into the left eighth.
- **The boxes aren't named** on the chart, and the helper numbers for the dashed lines are printed on the tab ("Chart guide lines ...").
- **The same loans appear many times.** Six grids' pockets share one chart, so the box counts (18, 24, 38, 32) count the same loans up to six times.

**Fix:** one chart per grid, box names in the corners, a tick at 1.00x, and labels on the pockets that are flagged.

## 12. Labels cut off

- **Band labels** on Where it bleeds, Losses vs revenue and Split: "15,449 to under 26,", "37,951 to under 49,15", "13,051 to under 17,". The upper bound is lost mid-number (`step-12-where-it-bleeds.png`, `step-13-losses-vs-revenue.png`).
- **Grids:** the third block's heading reads "Vs the rest of its b" (`step-14-grids.png`).

## 13. Excess in loans is still shown as whole numbers against a line with a decimal

Walk-2 defect 7 was a line of 2.3 shown as 2 beside a pocket whose excess also showed as 2 but sat below it. The fix put the line to one decimal on Check and Materiality ("5.7 loans"). Where it bleeds still formats Excess as `#,##0`. A pocket with an excess of 5.6 would show "6 loans" and "below the line" beside a line of 5.7. This book had no pocket between 5.2 and 6.3, so it wasn't seen, but nothing prevents it.

## 14. Show per pocket doesn't say what it isn't

OC-25 says the median or average "is never tested and never adds up across pockets, and the grid says so". The block on Grids is headed "FICO x CHANNEL: average ORIG_BAL per pocket" and says nothing else (`step-20-show-per-pocket.png`). The number format `#,##0.##` gives ragged figures: 32,583.3, then 32,967, then 32,706.55. In Excel that format prints a whole number with a trailing point ("32,967."). Not checked in Excel.

## 15. Window and status wording

- **The split is invisible in the window.** A split run's message is the same as an unsplit one (`step-18b-after-split-run.png`).
- **Long lists still scroll out of sight.** The first refused run's last line is below the fold (`step-08-run-before-answering.png`). This was already marked open after walk 2.
- **Two splits:** "Columns!H: only one column can split the pockets; ASSET_CLASS, REV_DEBT are all set to Yes." "Columns!H" isn't a cell, and "all" is for two (`wrong-two-splits.png`).
- **A split that empties the segments:** "Nothing is left to cut across ... Changed from what was suggested: ASSET_CLASS (Columns!D13, Cut by it? No)". It doesn't say the split on CHANNEL took CHANNEL out (`wrong-split-only-segment.png`).
- **A renamed column:** "the extract has no column "CHANNEL" (used by dimension channel)". It uses the old word *dimension*, and doesn't say to press Set up (`wrong-extract-renamed-col.png`).
- **The Extract box** shows the front of the path, so the file name is out of sight on any real folder path (`step-02b-extract-picked.png`).
- **Stale counts:**
  - after a run, Start here still says "Things to look at first on Columns: 7" (`step-17b-start-here-after-run.png`)
  - after a run on a changed extract, it still says "Set up from Consumer book Q3.csv: 8,000 loans" while Check says 6,000 or 3,000
  - Set up with two new columns says "2 things to look at first" without counting them (`wrong-new-columns-set-up.png`)

## 16. Materiality tab: levels that can't be chosen, and a heading without its noun

The tab shows what 0.5%, 1%, 2%, 5% and 10% would keep (`step-15-materiality.png`). Control offers only 1%, 5%, no floor, or your own dollar amount. To use 2%, the analyst reads the dollars off this tab and types them in, and hits defect 8. The first heading, "Share of the book's total", doesn't say total what (bad loans, bad balances, GCO or RANR, depending on the block).

---

## What I couldn't check

- **Real Excel.** Every tab was seen through LibreOffice and set with openpyxl. Not seen:
  - the scatter chart as Excel draws it (defect 11)
  - how dropdown picks are stored (walk-2 defect 3's fix rests on this)
  - `#,##0.##` in Excel (defect 14)
  - conditional shading, frozen panes and column widths on screen
  - whether the workbook survives Excel's own save after openpyxl rewrote it with a chart
- **Windows.** Not seen:
  - the Windows file dialog
  - Segoe UI in the window
  - **Open the workbook** (`os.startfile`)
  - a real Excel lock. It was simulated with `chattr +i`, which raises the same `PermissionError`. Excel's share mode might let `open(..., "r+b")` fail differently.
- **Scale.** 8,000 loans. Each run took a few seconds in the window.
- **The RANR "worst" line.** RANR carries no plant, yet a RANR pocket is flagged *worse* (REV_DEBT 6,559 to under 9,837 / Broker, 0.74x the rest of its band, p 0.0215). With 5% of lucky passes allowed across many pockets, that's expected. I didn't check whether the allowance runs per grid or across all grids and measures.
- **Excel's handling of a typed `620,680,740` in a Text cell.** The cell is formatted `@`. The walk wrote the text directly, not through Excel's typing.
- **Numbers above 850 in a FICO column.** The synthetic book has FICO up to 921, and nothing flagged it. Real bureau scores stop at 850, so I didn't rank it.

---

## Where each walk-2 defect stands (seen on screen, `00c0bdd`)

| # | Walk-2 defect | Now |
|---|---|---|
| 1 | A copied workbook runs the old folder's extract | **Held.** In a copied folder with a 3,000-loan extract of the same name, it ran 3,000 loans and said the extract had changed since Set up (`wrong-copied-folder.png`). |
| 2 | 620,680,740 read as one edge | **Held.** Refused as a single number, naming the cell (`wrong-edges-commas-number.png`). An edge outside the range is refused (`wrong-edges-outside.png`). Commas kept as text give 4 bands, and Check says so (`wrong-edges-commas-text-check.png`). |
| 3 | 95% stored as 0.95 | **Held, as far as it can be seen here.** The options read "95% sure". 0.95 as a number in the Choose cell ran. Excel's own storage of a pick not checked. |
| 4 | Yes carries over to new columns | **Held.** C3 cleared, rows shaded "New since the last check", window names both (`wrong-new-columns-set-up.png`, `wrong-new-columns-tab.png`). The "things to look at" count leaves them out (defect 15). |
| 5 | Forget re-learned in the same run | **Held in part.** The same run no longer re-learns it, and the window says what was forgotten. The next Run re-learns it silently (defect 9). |
| 6 | Set up again deletes results and the Log | **Held.** Results, Log and the chart all kept (`step-22b-start-here-after-set-up-again.png`). |
| 7 | No materiality evidence, no units | **Held in part.** Materiality tab present, every line has its unit, loans to one decimal (`step-15-materiality.png`, `step-16-check.png`). Where it bleeds still rounds Excess to whole loans, so the original contradiction can recur (defect 13). |
| 8 | A refused run still changes memory and the record | **Held.** With the workbook locked, Run and Set up refused, `memory.yaml` was byte-for-byte unchanged, and no record file was written (`wrong-open-run.png`). |
| 9 | Start here counts go stale | **Held in part.** Calls left goes to 0 and Last run gives the time and what ran (`step-17b-start-here-after-run.png`). "Things to look at first" and the loan count still go stale (defect 15). |
| 10 | "Answer it at the bottom" | **Held.** "Used as it is until you answer it on the Odd values tab" (`step-06-columns.png`). |
| 11 | "Enter your own in column D" on a row with none | **Held.** Row 18 says "Pick one from the list" in the window and on the tab (`step-08-run-before-answering.png`). |
| 12 | Meaning text cut at commas; codes in the dropdown | **Held.** "a category to cut by: channel, state, product"; labels such as "FICO score" and "Amount or number" (`wrong-new-columns-tab.png`). |
| 13 | Machine names, two Pocket headers, no unit, p on untested pockets, RANR gap | **Held.** Column names as in the extract; Band column / Band / Segment column / Segment; "Excess is in"; p blank on "too few losses to test"; "under 0.0001"; RANR "0.82x or less"; "(marked missing)" (`step-12-where-it-bleeds.png`). New: labels cut off (defect 12), "Chance it's luck" (defect 6). |
| 14 | RANR grids look like loss grids | **Held.** "(more is better)", colours reversed, and the arithmetic in words ("Total RANR_AMT over total ORIG_BAL") (`step-14b-grids-ranr.png`). |
| 15 | Window wording | **Held, except the one already marked open.** No "(s)", no backticks, the range said once with "For 95%, type 0.95", the Next line changes ("Everything is answered"), the changed column named. The message box still scrolls (`step-08b-scrolled.png`). New wording problems are in defect 15. |
| 16 | Layout and print | **Held** in LibreOffice: Check wide and wrapped, Log headed and on one page width, Blank and Samples apart, Learned titled, the record file named on Check. New clipping on Grids (defect 12). Fonts in Excel not seen. |
