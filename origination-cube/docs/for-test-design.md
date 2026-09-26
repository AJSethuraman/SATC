# Origination Cube: what it does, and tests you could design

Written 25 Sep 2026 from the repository at commit `73bc96f` on `claude/keen-franklin-4l01un`, plus the uncommitted change to the Losses vs revenue tab. The suite was not re-run for this write-up. Sources: `origination-cube/README.md`, `docs/design.md`, `BACKLOG.md` §6d, the sixth walk's defect list, and the code.

---

## 1. What it is, in five lines

- **In:** a loan extract (.csv or .xlsx) and your answers on the workbook's Control tab.
- **It needs five columns:** loan number, booked amount, a yes/no outcome, GCO dollars, RANR dollars (OC-14).
- **It cuts:** every number column into bands (FICO, loan size), crossed with every category column (channel, asset class). Each crossing is a **pocket**.
- **It measures four rates per pocket:** the outcome as a share of loans, the outcome as a share of booked dollars, GCO per booked dollar, and RANR per booked dollar.
- **The question:** where does the book bleed? Which pockets lose more than their share, can the gap be told from luck, and is it big enough in dollars to matter.

The tool does the arithmetic and lays out the evidence. You make every call about what matters (OC-13).

---

## 2. How a run works

1. Double-click **`Origination Cube.pyw`**. A small window opens.
2. Pick the extract and press **1. Set up from this extract**. A workbook named `<extract> - Origination Cube.xlsx` appears beside it.
3. Fill in the workbook:
   - **Start here:** the steps, and what is still open.
   - **Control:** your calls. Shaded cells need an answer. Judgment calls open blank and the run waits for them. Method settings open on the recommended option. After a Run, a *Last Run used* column shows the numbers actually used.
   - **Columns:** what each column is, with the reason it was guessed. You can also set *Cut by it?*, band edges (`620; 680; 740` or `every 20`), *Show per pocket* (median or average), and *Split pockets by it?*. Set C3 to Yes when done.
   - **Odd values:** answer "real" or "missing" for suspicious values, such as a -9999 or negatives in a mostly positive column. Unanswered ones are used as they are.
   - **Learned:** meanings remembered from earlier runs. Set a row to Forget to drop it.
4. Save, close, and press **2. Run the cube**. If anything is wrong, the window and the Log tab name the cell.

**Result tabs:**

| Tab | What it shows |
|---|---|
| **Where it bleeds** | Every pocket with losses above the book's rate, largest dollar excess first, for all four rates. Each row gives the rate, the book's rate, the excess, whether it's material, the multiple against the rest of the book and against the rest of its band (each with "Luck alone"), the flag, and the smallest gap the pocket could show. Red: worse. Amber: worse, but could be luck. Blue: material but too small to test. |
| **Losses vs revenue** | GCO and RANR side by side for each tested pocket. Details below. |
| **Grids** | Heat maps for each band × segment grid: the rate, the rate against the book, and the rate against the rest of its band. Pockets under the minimums are left blank. |
| **Split** | Only when a column splits the pockets. Explains its method once, then gives each grid's high-half-vs-low-half summary and heat maps. |
| **Three-way** | Only with a split. Every band / segment / split-value pocket, tested and ranked like Where it bleeds, with a *Holds FICO fixed?* column. |
| **Materiality** | For each grid and rate: how many pockets each level (0.5% to 10% of the book's total) would keep, and what share of the grid's excess they hold. |
| **Check** | The extract, loans run, tie-outs, loans left out and why, the band edges used, the numbers worked out from the book, what the allowance for many tests covers, and every setting. |
| **Log** | Every run and refusal, newest first. |

Every Run also writes `<book> - what ran.yaml` beside the workbook. It records every setting that run used.

**Losses vs revenue, current layout.** Each grid has two blocks side by side: *Losses: GCO per booked dollar* and *Revenue: RANR per booked dollar*. Each block has the same five columns:

- **This pocket:** the pocket's rate.
- **Rest of band** (or **Rest of book**, depending on Control): the rate of what it's compared with.
- **Multiple:** the first over the second.
- **Reading:** "losing more / about the same / losing less", or "earning more / about the same / earning less".
- **Over the rest ($):** the pocket's dollars minus what it would have at the rest's rate. The sign means opposite things on the two sides. Positive on GCO is bad. Positive on RANR is good.

Colour goes on the Multiple and Reading cells of each side. GCO losing more is red and losing less is green. RANR earning less is red and earning more is green. A reading that could be luck says "(could be luck)" and is left plain. The old "Which box" column is gone, so the pair of readings is the trade-off. Rows run from the largest GCO over the rest down. Pockets untested on either side come last and have no colour. Pockets under *fewest loans* are left off the tab entirely. Each grid gets one scatter chart that names the three biggest GCO bleeders. Band labels read as ranges, for example "496 - 619" and "620 - 679".

---

## 3. The decisions the tool makes, and the rule behind each

| Decision | Rule | Ruling |
|---|---|---|
| **What a pocket is compared with** | Three comparisons, each with its own multiple and test: the rest of the book (without the pocket), the rest of its band (without the pocket), and the rest of its segment. Control's *What a pocket is judged against* picks which one decides the flag. The excess dollars on Where it bleeds are always against the whole book's rate, so they add to zero across a grid. | OC-4, OC-6 |
| **When a pocket is tested at all** | Two floors, both yours. *Fewest loans* stops a test on a handful of loans. The suggested option is **5 expected losses at the book's rate**: loans = 5 ÷ book bad rate, rounded up (8,000-loan synthetic book: 5 ÷ 7.13% = 71). *Fewest losses* checks the pocket's own count of loans with a loss (5, 10 or 20). Below either floor the pocket reads "too few loans/losses to test". | OC-30 |
| **What "worse" means** | The multiple must be at or past the *How much worse* line **and** the test must say the gap is unlikely to be luck. Past the line but not significant reads "worse, but could be luck". Between the lines reads "in line". The suggested line is **what luck alone can move a typical pocket**: for each pocket big enough to test, the smallest outcome gap it could tell from luck at your confidence, then the median of those (never below 1.05x). *Better* is one over that. If nothing is big enough, 1.25x / 0.80x are used and labelled "the usual value". | OC-28, walk 4, walk 6 defect 3 |
| **"Could be luck"** | The test compares the pocket's rate with the rest's, allowing for how much a rate wobbles at that size. For a yes/no outcome it is the textbook two-proportion test, checked to nine digits. It gives a **p-value**, shown as "Luck alone": how often a gap this big turns up by chance when there is no real difference. The p-value is then adjusted by **Benjamini-Hochberg**: when you scan many pockets, it raises each p-value so that, of the pockets called real, only about 5% (at 95%) are expected to be luck. The adjustment runs within one grid, one rate and one comparison at a time, not across the whole run. | OC-28 |
| **Confidence and catch rate** | *Confidence* (90/95/99%) is the bar for "not luck". *Power*, the catch rate, is how often a real gap of a given size would be caught. It is used only for "smallest gap it could show" and "loans needed". It never flags anything. | settings |
| **Materiality** | Applied when reading, never when building. Pockets below the line stay listed as "below the line". The options are a share of the book's total (of that rate's own numerator), no floor, or your own dollar amount. A dollar amount is GCO only; other rates say they have no line. | OC-8, walk 3 defect 8 |
| **Material but too small to test** | Shaded blue on Where it bleeds and counted in the window, for you to look at by hand. There is no exact small-sample test; the firm left that as a materiality question. | BACKLOG, 25 Sep |
| **Losses vs revenue readings** | GCO uses the worse/better lines. Revenue has its own Control line. The **suggested** option reads more or less only when that pocket's own RANR test says the gap isn't luck, so a small pocket needs a bigger move. The fixed options (5%, 10%, or the loss lines) are the same line for every pocket, with luck marked. Nothing is netted, because RANR already includes credit losses. | OC-24, OC-26, OC-29, OC-30, OC-31 |
| **Split** | One column can split every pocket. A number is cut at **each pocket's own median**, so band and segment are the same on both halves. The high half is compared with the low half in each pocket, then pooled across pockets as actual against expected, with a range. For the yes/no outcome it also gives **Mantel-Haenszel odds**, a standard way to combine pockets without mixing their loans. **Cochran's Q** asks whether the gap is about the same size in every pocket. Each grid prints the split column's **correlation** with each band column (-1 to 1; 0 means unrelated). Grids that don't hold the partner column fixed are marked and come last. A category split repeats each grid once per value. | OC-23, OC-27 |
| **Three-way** | Every band / segment / split-value pocket goes through the same test, floors, dollars and tie-out as any other pocket. | OC-27 |
| **Bands** | Yours to set: a count (3 to 20) with equal-loan or round edges, your own edges, or a width (`every 20`). Edges you type are remembered for the next extract. A loan exactly on an edge goes into the upper band (620 falls in "620 - 679"). | OC-11, OC-28 |
| **Tie-out** | Every grid is re-added against separately kept book totals: rows, numerators, denominators, and excess summing to zero. A mismatch stops the run. | engine |

---

## 4. What is already tested

The README counts **189 tests** and **56 re-inserted bugs**. A "mutation" check puts a known bug back into the code and confirms at least one test goes red. All 56 must be caught.

| Area | What the tests hold |
|---|---|
| Arithmetic | Rates by hand. Multiple = share of losses ÷ share of volume. The tie-out can fail. Peers are the parent minus the pocket. A big pocket is read against the rest, not against itself. |
| The old macros' breaks (`vba-findings.md`) | A blank is never a zero. An empty cell never becomes an index. Text in an amount column is left out and counted. A flag that isn't 0/1 is counted, not guessed. Columns are found by name. No threshold has a default. |
| Statistics | Sample sizes match the textbook two-proportion answer. A dollar rate needs more loans than a count rate. The materiality ladder by hand. The pocket test matches a hand two-proportion z to nine digits. Mantel-Haenszel and CMH against known values. |
| Control applied | RANR more-is-better. The loss floor. The Benjamini-Hochberg allowance by hand. Judged-against decides the flag. Materiality as a share and in dollars. (Loan age was here until 26 Sep 2026; removed by OC-39: every loan runs.) |
| Workbook route | Refusals name the cell. Set up again keeps answers. Band edges and widths. Suggested values are worked out, or the fallback is labelled. Losses vs revenue readings follow the Control lines, and the multiple equals this pocket's rate ÷ the rest's. Luck-marked readings stay plain. Small material pockets are blue. |
| Split | Finds the planted debt effect. A column with no effect comes out near 1. Halves tie out. Floors apply. The allowance applies. |
| Columns and memory | Obvious meanings are suggested and the rest wait for you. Confirmed meanings are remembered. Only names, never values, are stored. Forget works. |

**The synthetic book** (`synth.py`, seed 7; the walks use 8,000 loans) plants:

- **FICO under 620 in Broker:** bad rate 30%, against 6% for other under-680 loans. That is 5x its band's usual rate. GCO per bad loan is 30–80% of balance. With edges 620/680/740 it is the top bleeder. On 8,000 loans it is 176 loans at about 5.35x the rest of its band on GCO. With the default five bands the first edge lands near 653, which dilutes it to about 2.6x.
- **Revolving debt:** above the usual debt for the score goes bad 1.8x as often. The split finds about 1.84x, worse in 20 of 20 pockets.
- **Asset class 4:** 1.4x.
- **Dirt:** FICO -9999 on every 50th loan, a blank FICO, a GCO of "#N/A", a blank balance, and a flag of 2.
- **RANR:** a flat –$200 to +$400 per loan, with no plant.

**One thing to know about RANR in the synthetic book.** RANR isn't scaled to balance, so RANR per booked dollar falls about fivefold with loan size (0.96% in the smallest fifth, 0.18% in the largest). "RANR has no plant" holds within a loan-size band. It does not hold across loan-size bands, or against the rest of the book.

---

## 5. What is NOT tested or checked yet

- **Real Excel** (Open (a)). Every tab has been seen through LibreOffice only. Dropdowns, validation pop-ups, conditional colour, the charts and printing are unchecked in Excel.
- **A real extract, and the bank machine** (Python, the add-ons, .pyw opening with Python). Nothing has met real data.
- **A real revenue effect.** RANR is never planted, so no true "earning more" or "earning less" has been seen to land.
- **A big low-default book** (50,000+ loans at 1–2%). The walks could only show that a small one tests nothing.
- **Small pockets with many losses.** A 50-loan pocket with 29 bad loans is still "too few loans to test" (walk 6 defect 8, open).
- **The charts** (open since walk 5). Axis ticks and labels are rough and the lines are unlabelled.
- **Two people sharing one memory file.** Edge memory is "whatever the last Run of any workbook had", by design.
- **Drill and prove** (Open (b)). Designed, not built.
- **The seventh walk is under way.** Its screenshots are in `docs/walkthrough/walk-2026-09-25-g/` with no defect list yet. The file names point at: the revenue option explained wrongly, `every 20` earning less, Check's fallback wording, the blue count in the window, and the no-effect split.

**Noticed while reading, not covered by any test:**

- **Negative RANR breaks the multiple.** RANR includes credit losses, so a deep subprime band can be net negative. The multiple is pocket ÷ rest, so two negatives divide into a positive. I checked this in a scratch run of the engine, with no repository change. In a band where one channel earned –3.8% and the other –1.8%, the worse channel read **"better"** (2.11x). The other read **"worse"**. The dollar shortfall was correct. On Losses vs revenue the worse channel would read "earning more" in green.
- **Control's text for the suggested revenue option is out of date.** It still describes one "typical pocket" number. Since OC-31 it is each pocket's own test.
- **Values like "35%" or "-" in an amount column** are read as not-a-number. They are left out and counted on Check, not converted. "(125.00)" is read as -125.
- **An unanswered -9999 is used as a real score.** It lands in the lowest band.
- **Two different dollar figures for one pocket.** Where it bleeds uses excess against the whole book. Losses vs revenue uses dollars against the rest of the band.
- **The allowance for many tests is per grid.** A run with 6 grids × 4 rates has 24 separate families. Expect somewhat more lucky finds across the whole run than the 5% figure suggests.

---

## 6. Tests the firm could design

Every one of these can be built in Excel, saved as CSV, and run through the launcher. Where one starts from the synthetic book, ask the session for a copy of the 8,000-loan extract used in the walks.

### Test 1: a book you can work out by hand ★ start here

- **Question:** does every number on every tab match arithmetic you did yourself?
- **Set-up:**
  - 4,000 loans, each booked at $10,000.
  - Two FICO bands: half at 600, half at 700. Change one good 700 loan to exactly 620.
  - Two channels, 1,000 loans in each band × channel.
  - Bad loans: 50 in each pocket except FICO 600 / Broker, which has 150. Each bad loan has GCO of $5,000.
  - RANR: a flat $200 on every loan.
  - Control: own edges `620`, fewest loans 30, fewest losses 10, judged against the rest of the band, worse 1.25, better 0.8, 95%, no materiality floor.
- **Right answer:**
  - Book bad rate 7.5%.
  - Broker 600: bad rate 15%. Rest of its band 5%, so the multiple is 3.00x. Excess is 150 – 75 = 75 loans, and $375,000 of GCO against the book's rate.
  - Every other pocket shows negative excess, and the excesses add to zero.
  - The 620 loan sits in "620 - 700".
  - RANR reads "about the same" everywhere.
- **What it catches:** arithmetic, the definition of "rest of band", signs, where edges fall, and whether the tie-outs mean what they say. It also becomes the base book for Test 2.

### Test 2: a band whose RANR is negative ★ start here

- **Question:** does the tool read revenue correctly when RANR after losses is below zero?
- **Set-up:** copy Test 1. In the 600 band, set RANR to –$400 per loan for Broker and –$200 for Branch. Leave the 700 band at +$200. Run with the same Control answers, then again with the revenue line at 10%.
- **Right answer:** Broker 600 is the worse revenue pocket. It should read "earning less" in red, with a positive RANR shortfall. Branch 600 is the better of two bad pockets. It should not read "earning less".
- **What I expect:** based on the scratch run, it will fail. The multiple comes out 2.0x and Broker reads "better" / "earning more".
- **What it catches:** a live flaw that only matters because RANR includes losses (OC-29). Only someone who knows that would build this book.

### Test 3: a pocket that should not be flagged

- **Question:** does "worse than the book" stay separate from "worse than its peers"?
- **Set-up:** the synthetic book, edges `620; 680; 740`. Look at FICO under 620 / Branch and / Online. Run once judged against the rest of the band, then against the rest of the book.
- **Right answer:**
  - Both appear on Where it bleeds, because they are above the book's rate.
  - Against the band, they read better or in line: Broker drags the band up.
  - Against the book, they can read worse.
  - Asset classes 1–3 should never be red on a flag that holds FICO fixed.
- **What it catches:** the comparison being mixed up (OC-6), and red spreading to innocent neighbours of a bad pocket.

### Test 4: the trade-off pocket, losing more and earning more

- **Question:** does a real "do we care?" case land where the firm would put it?
- **Set-up:** the synthetic book. For Online, FICO 620–679:
  - Flip enough good loans to bad so the bad rate roughly doubles, and give them GCO.
  - Add 3% of balance to RANR, then subtract the new GCO, so RANR stays net of losses.
  - Run with each revenue option.
- **Right answer:**
  - GCO side red: "losing more".
  - RANR side green: "earning more", with over-the-rest dollars positive on both sides.
  - The chart shows it top-right.
  - Under the suggested option it should read "earning more" without "(could be luck)", if the move is big enough for its size.
- **What it catches:** the revenue side has never been tested with a real effect. This is the first true positive for it.

### Test 5: a tiny pocket that matters

- **Question:** is a small, expensive pocket visible even though it can't be tested?
- **Set-up:** add 40 jumbo loans at $400,000 in one band / segment, 12 of them charged off at 60%. Use the suggested fewest loans. Materiality 1% of losses.
- **Right answer:**
  - Where it bleeds: "too few loans to test", Material "yes", shaded blue, counted in the window line.
  - It is absent from Losses vs revenue.
  - Variant: 50 loans with 29 bad. It should arguably be tested, because it has far more losses than the 5-loss floor asks for (walk 6 defect 8).
- **What it catches:** a floor hiding dollars. It also gives you evidence on the open small-pocket question.

### Test 6: a split column that is only FICO in disguise

- **Question:** does the split warn you strongly enough?
- **Set-up:** add a column such as "UTIL" that is only a function of FICO plus noise, for example 90 – FICO/10 + a random 0–10. It has no effect of its own. Split by it.
- **Right answer:**
  - FICO grids: high vs low near 1.00x, with Luck alone large.
  - Non-FICO grids: a sizeable "effect" under the warning heading, with a strong negative correlation printed.
  - Three-way rows marked "no: part of this may be FICO".
  - You judge whether "part of" is honest wording when it is all FICO.
- **What it catches:** false third-layer findings (walk 6 defect 5).

### Test 7: band edges that change the story

- **Question:** how much does the answer depend on where the edges fall?
- **Set-up:** the synthetic book, run four ways:
  - the default 5 bands
  - `620; 680; 740`
  - `every 20`
  - `600; 620; 640; 660`
- **Right answer:**
  - The plant always shows up in Broker below 620.
  - Its multiple is diluted when an edge sits above 620 (about 653 by default).
  - It sharpens with 620 as an edge.
  - No neighbouring Broker band above 620 should read worse.
  - Band labels read cleanly, for example "600 - 619".
- **What it catches:** edge off-by-ones, dilution you would otherwise mistake for a weaker problem, and how much the suggested lines move with the bands.

### Test 8: real-extract quirks

- **Question:** does dirty data get counted, asked about, or silently dropped?
- **Set-up:** in a copy of a realistic extract, include:
  - FICO codes -9999, 0 and 999
  - DTI written as "35%"
  - GCO shown as "-" for zero
  - RANR in parentheses
  - a repeated loan number
  - a blank booked amount
  - dates as text

  Run once with -9999 unanswered, then answered "missing".
- **Right answer:**
  - Odd values asks about -9999. Unanswered, it sits in the lowest band. Answered, it gets its own "(marked missing)" row.
  - Check lists what was left out of each rate and why.
  - The repeated key is warned about.
  - Decide whether "35%" and "-" being left out is acceptable.
- **What it catches:** silent data loss on the formats a bank really sends.

### Test 9: a big, prime, low-default book

- **Question:** do the suggested floors and lines still find a real pocket at a 1–2% bad rate?
- **Set-up:** 60,000 loans at about 1.2% bad, built with RAND() in Excel. Plant one pocket of about 800 loans at 3x. Take every suggestion.
- **Right answer:**
  - Suggested fewest loans about 417 (5 ÷ 1.2%).
  - The plant is red.
  - Very few other reds.
  - The window names the plant as worst.
- **What it catches:** the usual bank case, which the walks could not reach.

### Test 10: no effect anywhere

- **Question:** how many false alarms does a clean book raise?
- **Set-up:** take the synthetic book and shuffle the outcome, GCO and RANR columns together as a block against the other columns (sort that block by RAND()). Every relationship is gone and the totals are unchanged.
- **Right answer:** almost no red. Some amber is expected. Count the reds across all grids and rates. With the allowance per grid, one or two across the run is about what luck gives.
- **What it catches:** overconfidence. It also gives you a feel for how much to trust a single red on a real book.

### Which two to start with

- **Test 1:** it checks every number against your own arithmetic in one go. Tests 2 and 5 are small edits to it.
- **Test 2:** it will probably find a real flaw today. It only needs a domain fact the tool's own synthetic book never exercises: RANR after losses can be negative.
