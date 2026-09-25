# Origination cube: defects from the seventh walk (25 Sep 2026)

**What was walked:** the no-commands route of ruling OC-22, on commit `a5a8aa2`, frozen with `git archive` into scratch:
1. The Tk window: Browse, **1. Set up from this extract**.
2. Start here, Control, Columns, Odd values and Learned, answered cell by cell, taking every suggestion Control offers.
3. **2. Run the cube**, then every result tab.
4. The new parts:
   - Losses vs revenue under the suggested revenue option (each pocket's own luck range) and under 5%, 10%, the loss lines and an own 0.15, each on the default bands, `620; 680; 740` and `every 20`: fifteen runs, read back row by row with `driver/revcheck.py`
   - blue rows on Where it bleeds, with `every 20`, a floor of 450, a floor of 3,000 and a low-default book, counted with `driver/bluecheck.py`
   - the fallback wording (wrong turns S and T) in the window, on Control and on Check
   - Control's *Last Run used* in print and after Set up
   - the Split tab's brackets and method block, and `driver/noplant.py` again, through the window
   - remembered band edges across three extracts (Q3, Q4, Q1), with edges typed on a category
5. Set up again, Forget with two Runs after it, and the 22 wrong turns in the procedure's table (A to U), each in a folder of its own.

The procedure is `PROCEDURE-origination-workbook.pdf` beside this file. The scripts are in `driver/`.

**The book:** `synth.write_extract(n=8000)`, renamed `Consumer book Q3.csv`. It plants a bad pocket (FICO under 620 in Broker, 5x the usual rate), a revolving-debt effect (above the usual debt for the score goes bad 1.8x as often) and asset class 4 at 1.4x. RANR carries no plant, so every revenue gap on this book is noise.

**The suite at `a5a8aa2`:** `pytest -q` gave **188 passed** (6 min 49 s, Python 3.12 under xvfb). `tools/mutation_check.py` caught **54 of 54**. All 188 tests pass with every defect below present, so none of them is caught.

**What held:**
- **The suggested revenue option does what OC-31 asked.** The planted pocket reads **Losing more, earning the same**, shaded red, on all three band settings: under 654 / Broker (RANR 1.05x), under 620 / Broker (RANR 1.17x, which walk 6 read as *earning more*) and 600 to under 620 / Broker (RANR 1.20x). Under this option a revenue side only moves when its own test says so, so no revenue side carries a luck mark.
- **Marked boxes are unshaded and counted apart** on every run: `revcheck.py` finds no marked box shaded, no plain box off "the same" unshaded, and every count line agrees with its rows, across all fifteen runs.
- **RANR reading** agrees with the box's revenue side on every row of every run.
- **Blue rows appear** where they should: with `every 20`, 580 to under 600 / Broker (50 loans, 29 bad, walk 6's defect 8) is blue; with a floor of 450, 58 rows are.
- **The fallback reaches the window and Control.** Wrong turn S: "No pocket had enough loans or losses to test ... (fewest loans: 3,000)" for each measure, and "Nothing in this book to work these out from, so the usual values were used: worse at 1.25x; better at 0.80x." Control: "1.25 times (the usual value: nothing in this book to work it out from)". The record no longer says "worked out".
- **Last Run used** is inside Control's print area and survives Set up again, values intact.
- **Band edges:** edges typed on CHANNEL are no longer remembered; Q4's Set up says "3 columns to look at first" and three rows are shaded, the remembered `every 20` among them.
- **The Split tab:** could-be-luck multiples are bracketed and unshaded (on the no-effect book every FICO-grid pocket is); the block says which figures carry the allowance; Mantel-Haenszel is glossed; the correlation is explained once, in *What it assumes*; *Same size* reads "yes/no outcome only" on the dollar measures.
- **Every wrong turn from walk 6 behaves as it did, or better:** `every 1` names Columns!F7 and says "50 bands or fewer"; 0.95 as a revenue line gets "The most it takes is 0.9."
- **Tie-outs** agree on every run (132; 581 with the number split; 571 with the booked amount).

Of the eleven walk-6 defects, six held, four held in part, and one (the no-effect book) stands as walk 6's status table left it. None came back whole. The table is at the end.

This walk found **8 defects**, and a list of smaller things, ranked by what each would cost the firm or the bank on a real job.

---

## 1. Under a fixed revenue option, a real loss finding loses its colour and its count when its revenue side is noise

**What I did:** ran the five revenue options on each of the three band settings, and read every row back (`driver/revcheck.py`, and a count of rows whose GCO flag is *worse*, not luck, but that carry no fill).

**What the screen said:**
- **`620; 680; 740`, 5 percent either way,** FICO x CHANNEL: FICO **under 620 / Broker**, 176 loans, GCO **5.35x**, flag **worse**; RANR 1.17x, *earning more (could be luck)*. Which box: "Losing more, earning more (revenue gap could be luck)". **Not shaded.** The count line: "About the same on both: 5; Losing less, earning the same: 1. Marked could be luck, not counted above: 6". **No *Losing more* at all** in the grid whose worst pocket is five times its band (`defect-1-lob-edges-5-percent.png`).
- **`every 20`, 5 percent:** 600 to under 620 / Broker (99 loans, GCO 4.63x, *worse*) reads the same way (`defect-1b-every-20-5-percent.png`). **All three** real *worse* rows on the tab are unshaded.
- **Default bands, 5 percent:** ORIG_BAL 49,152 and over / Broker, GCO **2.03x worse**, RANR 0.79x *earning less (could be luck)*, is unshaded, and ORIG_BAL x CHANNEL's count line reads "About the same on both: 2. Marked could be luck, not counted above: 13" (`defect-1c-default-bands-5-percent.png`). REV_DEBT 17,187 and over / Broker (1.84x worse) goes the same way.

Real *worse* rows left unshaded, of all real *worse* rows on the tab:

| Revenue option | Default bands | `620; 680; 740` | `every 20` |
|---|---|---|---|
| Each pocket's own luck range | 0 of 4 | 0 of 4 | 0 of 3 |
| 5 percent either way | 2 of 4 | 3 of 4 | **3 of 3** |
| 10 percent either way | 1 of 4 | 2 of 4 | 2 of 3 |
| Your own: 0.15 | 1 of 4 | 2 of 4 | 2 of 3 |
| The same lines as for losses | 0 of 4 | 0 of 4 | 0 of 3 |

Real *better* rows go the same way (1 of 3 on `620; 680; 740` at 5%).

**What was true:**
- The loss side of these rows is a finding: past the Control line and not luck by its own test. Only the revenue side could be luck. The row reads as if the whole pocket could be luck.
- It follows from how walk 6's defect 2 was fixed: "a luck-marked box isn't shaded or counted" treats a box as marked when *either* side is. OC-31 says "A luck-marked box isn't shaded or counted with the findings", which doesn't say what happens to the side that is a finding.
- This is the fifth walk in a row where the top defect sits where a box with one luck side meets the colour and the count. Walk 6 coloured and counted the planted pocket as *earning more*; walk 7 colours and counts it as nothing.
- The suggested option doesn't have this problem. Only the fixed options do, and they're on the list for the firm to pick.

**Cost:** a consultant who picks 5% or 10% (both read as ordinary choices) and scans the colours or the count lines sees no bleeding pocket in the grid the LOB asked about. The bank's worst pocket, at five times its band, is white.

**Fix:** the firm's call. Options:
- shade and count by the side that isn't luck ("Losing more: 1, revenue could be luck");
- name the box by the real side only ("Losing more; revenue can't be told from the book");
- keep the marked box as is but never drop a *worse* GCO flag from its own colour.

A check that goes red: on the synthetic book with `620; 680; 740` and 5 percent either way, FICO under 620 / Broker must be shaded and counted as losing more.

## 2. Control explains the suggested revenue option as the old single line

**What I did:** read Control before and after the Run, and Check after it.

**What the screen said:**
- Control row 21, *How far revenue must move*, option "What luck alone can move it (suggested)". *What it means*: "Worked out from this book: the revenue gap luck alone can make in a pocket of typical size. Revenue inside that gap reads as about the same." In the next column, *Last Run used*: "each pocket's own luck range" (`defect-2-revenue-option-explained-wrong.png`).
- *In use* repeats "What luck alone can move it (suggested)". Check's settings list says the same, a few rows under "Revenue counts as more or less: when it's past what luck alone can move that pocket".
- The worse and better rows use the same label, "What luck alone can move it", for a different thing: one line for every pocket, worked out from the book.

**What was true:** OC-31 replaced the typical-pocket line with each pocket's own test. `settings.yaml` still carries walk 6's explanation. The tab's own two columns contradict each other on one row.

**Cost:** the analyst reads what the option means from the sentence beside it, and that's what goes into the method note to the bank: a single revenue line from a typical pocket. The workbook is meant to be auditable, and its only description of the option describes one that no longer exists.

**Fix:** rewrite the option's label and explanation, e.g. "Past what luck can move each pocket (suggested)" / "Each pocket's own test decides. A small pocket needs a bigger move than a large one." Use a different label from worse / better.

## 3. The same pocket reads *earning less* on one tab and *in line* on another

**What I did:** ran `every 20` with every suggestion, and set Losses vs revenue's RANR reading against Where it bleeds' RANR flag for each pocket.

**What the screen said:**
- **Losses vs revenue:** REV_DEBT 6,559 to under 9,837 / Broker, RANR **0.74x**, reading **earning less**, box "Losing the same, earning less", shaded red (`defect-3-every-20-earning-less.png`).
- **Where it bleeds**, RANR per booked dollar, same pocket: 0.74x, luck alone 2.2%, flag **in line** (`defect-3b-every-20-where-it-bleeds-in-line.png`).
- **The window:** "Nothing is worse for RANR per booked dollar at these settings." (`defect-3c-every-20-window.png`)
- Under 5 percent either way on the default bands, 22 rows read *earning less (could be luck)* on Losses vs revenue beside *in line* on Where it bleeds.

**What was true:** Where it bleeds judges RANR by the loss lines (worse at 1.37x, so 0.73x for RANR on this run). Losses vs revenue judges it by the revenue option. Walk 6's defect 4 was fixed on the one tab by renaming the column; the disagreement moved to between tabs. On the default bands the loss line happened to be 0.75x, just above 0.74x, so the two tabs agreed by chance.

**Cost:** the window and the main list say revenue is fine, and the revenue tab shows a red revenue shortfall. Whichever one the consultant quotes, the other contradicts it in the same file.

**Fix:** judge RANR on Where it bleeds by the revenue option too, or say on both tabs which line each uses.

## 4. On Losses vs revenue, a wrapped box sits half a line above its own row

**What I did:** read Losses vs revenue as LibreOffice prints it, on every run.

**What the screen said:** a marked box, "Losing more, earning the same (loss gap could be luck)", wraps. Its cell is set to the top of the row; every other cell in the row sits at the bottom. So the box text prints on a line of its own above the row's numbers, and the numbers' line shows an empty *Which box*. Scanning across, "Losing more, earning the same (loss gap could be luck)" sits under *under 654 / 4* (the red row) and above *654 to under 686 / 4* (`defect-4-box-text-off-its-row.png`). 35 rows do it on the first run, 73 under 5 percent.

**What was true:** the text belongs to the row below it. Whether Excel wraps these at a column width of 44 wasn't checked; the longer boxes ("Losing the same, earning more (revenue gap could be luck)") wrap in any font.

**Cost:** a reader reading across the line gives a pocket the box of the one below it, or none at all. Where the red planted row is followed by a marked row, it can look as if the planted row is the one that could be luck.

**Fix:** set the whole row to the same vertical alignment (top), or keep the box on one line.

## 5. Under a fixed option, "(could be luck)" is cut off in the RANR reading column

**What I did:** read Losses vs revenue under 5 percent either way.

**What the screen said:** *RANR reading* is 11 wide. "earning more (could be luck)" runs into *Which box* and is cut at "(could be luck" (`defect-5-ranr-reading-cut-off.png`). In Excel the next cell holds text, so it would be cut there too.

**What was true:** this is walk 6's defect 2 moved to the new column. Under the suggested option the readings are short and it doesn't happen.

**Cost:** the reading column is the one a reader checks to see whether the revenue side is real, and the part that says it isn't is the part that's cut.

**Fix:** widen or wrap the column (with the alignment fix in defect 4).

## 6. Check still calls the fallback "the outcome gap luck alone can make in a pocket of typical size"

**What I did:** wrong turn S (fewest loans 3,000, luck suggested for worse and better) and wrong turn T (the 5,000-loan book at 1.34% bad, every suggestion).

**What the screen said:** Check, *Suggested values*: "worse at 1.25x; better at 0.80x (the outcome gap luck alone can make in a pocket of typical size); where nothing could be worked out (no rate, or no pocket big enough), the usual value was used instead: better_at, worse_at" (`defect-6-check-fallback.png`, `defect-6b-check-fallback-low-default.png`).

**What was true:**
- 1.25x and 0.80x are the usual values; nothing was worked out. The bracket says the opposite of the clause after it.
- "better_at, worse_at" are the code's names for Control's rows.
- Check never says that no pocket had enough loans to test. The window does.

**Cost:** smaller than walk 6. The window and Control are now right, so the analyst isn't misled at the time. Check is what goes in the file for a reviewer, and it still says the number was worked out.

**Fix:** leave the bracket off values that fell back; name them as Control does ("How much worse", "How much better"); add Check's own line "No pocket had enough loans or losses to test (fewest loans 3,000; largest pocket 568)".

## 7. The blue-row count counts rows, not pockets, and doesn't always match the blue

**What I did:** compared the window's "N pockets are material but too small to test" with the blue rows on Where it bleeds (`driver/bluecheck.py`).

**What the screen said:**

| Run | Window says | Blue rows | Pockets behind them |
|---|---|---|---|
| `every 20` | 13 pockets | 13 | 5 |
| Floor 450 | 58 pockets (`defect-7-blue-count-window.png`) | 58 | 23 |
| Floor 3,000 | 101 pockets | 101 | 40 |
| Low-default book | 130 pockets | **126** | 50 |

On the low-default book the other 4 are pockets with a missing FICO ("(marked missing)"). They're material and untested, but their flag is blank, so they aren't blue.

**What was true:** each pocket is counted once per measure it's material on. Three-way uses the same blue rule, and the window's count leaves Three-way out.

**Cost:** "58 pockets to look at by hand" is more than twice the work there is, and on the low-default book, four of the 130 can't be found by colour.

**Fix:** count distinct pockets ("23 pockets, 58 rows"); shade the missing-score pockets too, or leave them out of the count.

## 8. On a book with no debt effect, the grids that don't hold FICO fixed still read as an effect

**What I did:** `driver/noplant.py`, and the REV_DEBT split through the window on the book with the debt plant switched off.

**What the screen said:** as walk 6 found it. Under the heading "Grids that don't hold FICO fixed. ... part of every gap below may be FICO", ORIG_BAL x CHANNEL: **1.62x** (1.37x to 1.87x), 13 of 15, luck alone under 0.01% (`defect-8-no-effect-book-split.png`). Three-way: ORIG_BAL 49,158 and over / Broker / REV_DEBT high half, 266 loans, **2.77x** its band, **worse**, shaded red, "no: part of this may be FICO" (`defect-8b-no-effect-book-three-way.png`).

**What was true:** there is no debt effect; all of the 1.62x is FICO. Walk 6's status table marked this "fixed in part", and nothing has changed since. The brackets now make the FICO grids read honestly (every pocket bracketed on this book); the ORIG_BAL grids aren't touched by that, because their pocket tests are strong.

**Cost:** as walk 6 said: small for a reader who reads the heading, real for one who copies the summary or sorts Three-way by flag.

**Fix:** as walk 6 proposed: "may be mostly FICO"; no red on Three-way rows where *Holds FICO fixed?* is *no*.

## Smaller things

- **Last Run used** is blank on four rows (the category limits, band count, band placement), though the Run used them (`step-09-control-answered.png`).
- **Edges typed on a category** are still accepted without a word and ignored. They're no longer remembered.
- **Learned** still reads "fico; band edges every 20", a code, where other rows read "FICO score" or "Category".
- **Charts:** still open, as walk 6 left them. The three named pockets include luck-marked ones (FICO x ASSET_CLASS names 654 to under 686 / 4 and 712 to under 746 / 4, whose loss gaps could be luck), and their labels overprint (`step-13c-chart.png`).
- **The low-default book:** "Worked out from this book: fewest loans 374" sits beside "No pocket had enough loans or losses to test", and the largest pocket is 363. The window doesn't say the suggested floor is the reason.
- **The Split tab** now says "The summary's figure is one pooled test per grid and measure, with no allowance". `docs/design.md` still says "Every 'Luck alone' figure is after the allowance for many tests, the Split tab's included". One of them is out of date.
- **Split heat maps** mix bracketed text (left-aligned) with numbers (right-aligned) in one column.
- **"The same lines as for losses"** prints revenue at 1.33x beside GCO at 1.34x (1 / 0.75 against the rounded 1.34).
- **Three-way in print:** "1.82x or more" and "no: part of this may be FICO" run together at the page edge (`defect-8b-no-effect-book-three-way.png`).
- **The window remembers the last extract from any session**, including a copy in another folder. On reopening, check the path before pressing Set up.

---

## What I couldn't check

- **Real Excel.** Every tab was seen through LibreOffice and set with openpyxl. Not seen:
  - whether Excel wraps the box text at width 44, and so whether defect 4 happens there
  - the blue, red and amber conditional formats as Excel draws them
  - the charts as Excel draws them
  - dropdowns and validation pop-ups
- **Windows.** The file dialog (it opens behind the window on the virtual display, so it isn't pictured), Segoe UI, **Open the workbook**, and a real Excel lock (simulated with `chattr +i`).
- **A book with a real revenue effect.** RANR is noise in the synthetic book. Under the suggested option one pocket (REV_DEBT 6,559 to under 9,837 / Broker, 0.74x) passes its own test by chance, which is about what 95% allows over some hundred tests. I couldn't see a true revenue gap land.
- **A big low-default book.** Wrong turn T is 5,000 loans at 1.34%: too small for any test. Whether blue rows and the 5-expected-losses floor find a planted pocket at a 1% rate needs 50,000 loans or more.
- **Two people sharing one memory file.** The walk's folders share one scratch memory, which shows last-Run-wins but not two users at once.
- **The repository moved during the walk.** `73bc96f` ("bands read as ranges (620 - 679)") landed on the branch, and uncommitted changes to `book.py`, `control.py` and the tests appeared in the working tree. They redo Losses vs revenue: the box column is no longer printed, each side is shaded on its own, and a luck-marked side isn't shaded. That may answer defects 1, 4 and 5 on the next commit, or move them. I walked `a5a8aa2` as frozen and haven't looked at the new layout on screen.
- **Whether the firm meant OC-31's "isn't shaded or counted" to cover a box whose other side is a finding.** Defect 1 turns on that reading. The walk can only show what the screen does now.

---

## Where each walk-6 defect stands (seen on screen, `a5a8aa2`)

| # | Walk-6 defect | Now |
|---|---|---|
| 1 | Under the LOB's bands, the worst pocket reads "earning more" | **Held under the suggested option**: under 620 / Broker and 600 to under 620 / Broker read *Losing more, earning the same*, red (`step-21b`, `step-21f`). **Under 5%, 10% and your own line** it reads *Losing more, earning more (revenue gap could be luck)*, now unshaded and uncounted, so the loss finding disappears instead (defect 1). |
| 2 | The luck mark cut off, shaded and counted like a finding | **Held in part.** The box column is 44 wide and wraps; marked boxes are unshaded and counted apart, and every count line ties to its rows. But the wrapped text sits above its row (defect 4), the new RANR reading column cuts "(could be luck)" (defect 5), and unshading a box hides its real side (defect 1). |
| 3 | A fallback called "worked out"; "Nothing is worse" when nothing was tested | **Held in part.** The window and Control say "the usual value", and the window says "No pocket had enough loans or losses to test" for each measure (`wrong-min-huge`, `wrong-lowdef`). Check still calls 1.25x the luck gap and names `better_at, worse_at` (defect 6). |
| 4 | RANR flag and box on different lines | **Held on the tab** (RANR reading agrees with the box on every row of fifteen runs). **Moved between tabs**: Where it bleeds and the window still judge RANR by the loss lines (defect 3). |
| 5 | A no-effect book can still read as an effect | **As walk 6's status table left it.** Heat maps bracket luck (every FICO-grid pocket on the no-effect book); the ORIG_BAL grids' 1.62x and the red 2.77x Three-way row remain (defect 8). |
| 6 | Last Run used off the page; Set up empties it | **Held.** In the print area and kept through Set up (`step-09`, `step-22b`). Four rows still blank (smaller things). |
| 7 | Edge memory: category edges, the count | **Held.** Category edges aren't remembered; Set up counts remembered edges ("3 columns to look at first", `step-24b`). Category edges are still accepted silently. |
| 8 | A 50-loan pocket with 29 bad is "too few loans" | **Held the way the firm chose:** it's blue on Where it bleeds and counted in the window (`step-21e`). The count counts rows, not pockets (defect 7). |
| 9 | Split tab points | **Held.** Which figures carry the allowance, glosses, the correlation once, "yes/no outcome only". The tab now contradicts `design.md` on the summary's allowance (smaller things). |
| 10 | Three-way lead and print | **Held.** One sentence; the column is on the page. Its text abuts the column before it (smaller things). |
| 11 | Smaller things | **Held except the charts.** `every 1` names Columns!F7 and says "50 bands or fewer"; 0.95 gets "The most it takes is 0.9"; no double colon. Charts still name luck-marked pockets. |
