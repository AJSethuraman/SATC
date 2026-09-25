# Origination Cube: design

**The business argument:** if the overall buy box looks fine, find the places
where it isn't, and prove them. The firm advises the line of business (LOB).
The cube finds the pockets, and the proof stage shows each one is a real group
that can be told apart from its peers, not luck and not something else in
disguise.

**Who decides what.** The firm, 25 Sep 2026:

> i don't want the engine to decide a charge-off amount or something is or is
> not important, that is the professional's judgment to apply. this is meant to
> be a very efficient tool for helping perform such analysis.

So the tool does the arithmetic, runs the tests, and lays out the evidence for
each judgment. The professional makes every call about what matters. Where the
tool can reasonably guess (which column is GCO, which is the key), it suggests,
says why, and waits for a yes.

Written 25 Sep 2026. **Built:**
- the engine
- the per-pocket test
- `cube init`, with a meaning for every column and a memory that can be pruned
- the Control tab

**Proposed, and the firm reacts before it's built:**
- the workbook's other tabs
- drill-down
- the proof stage

## The three stages

```
 FIND                        DRILL                         PROVE
 every column alone,         each flagged pocket cut        the pocket as a rule on the
 every band x dimension      by every other column:         loans: does it hold on loans
 -> every pocket ranked      which factor explains          it wasn't found in, how many
    on "Where to look"          the bleed inside it?           dollars, and what the book
                                                               looks like without it
```

All three are commands of the one tool (`cube run`, `cube drill`, `cube
prove`), reading the same extract, the same cube file and the same Control tab.
Each writes what it checked beside what it found.

## Step 0: what an extract must carry, and how the tool finds it (built)

The firm's minimum, 25 Sep 2026. The run refuses if any of these is missing.

| Line | What it is | Why it's required |
|---|---|---|
| `key:` | loan or application number | "or we cannot perform the remapping exercise": every pocket must map back to its loans |
| `booked:` | booked or loan amount | "averages and stuff in consumer tends to be weighted on a reporting level" |
| `outcome:` | any yes/no: charged off, ever delinquent, decided by the system | the binary the rates are built on. `{field: X, is: AUTO}` makes any column yes/no |
| `gco:` | gross charge-off dollars | the ratio comparisons |
| `ranr:` | RANR dollars (negatives kept) | the ratio comparisons |

Every run builds four core rates from these:
- the outcome as a share of loans (straight)
- the outcome as a share of booked dollars (weighted)
- GCO per booked dollar
- RANR per booked dollar

Extras go under `measures:`, and `per: each_loan` gives a straight average of
any column.

The key used to be warn-not-stop in the VBA (D55). It is now required,
because remapping is part of the job.

**`cube init EXTRACT -o cube.yaml`** reads the extract and suggests what
**every** column means, not only the required five. The firm: *"it should suggest
all columns, and maybe we can teach it along the way ... it won't and should not
be able to guess them all off the bat - but some are obvious."*

The cube file lists every column in a `columns:` section. Each line has a meaning
and the reason it was suggested:

```
columns_confirmed: no
columns:
  LOAN_NBR: {means: key}        # suggested - name contains 'loan'; a different value on every row
  FICO:     {means: fico}       # suggested - name contains 'fico'; 98% of values between 300 and 850
  ORIG_BAL: {means: booked}     # REMEMBERED - you confirmed this as booked or loan amount on 2026-09-25
```

- **The meanings.** The catalog is in `settings.yaml` (`meanings:`), with name
  hints and a value check for each:
  - the required five: key, booked, outcome, gco, ranr
  - dates: origination date, as-of date
  - scores: FICO (whole numbers, 95% between 300 and 850), score (a custom or
    bank score)
  - ratios: DTI, LTV and rate, each by its median, whether written as a
    fraction or a percentage
  - term
  - **servicing**: a new line limit, a status, days past due, anything
    recorded after booking. It is never cut by. The firm: *"anything past that
    would be 'Servicing Data'"*.
  - the catch-alls: amount, category, id, unused, unknown
- **What gets suggested.** Only the obvious cases:
  - a name hint *and* values that fit
  - or values that stand alone: a 300-850 score, or one date on every row
    (the as-of date)
  - a ratio with no telling name is just a number to cut, until someone says
    otherwise
  - a custom score on the FICO scale is suggested as FICO, with a note to
    confirm it as `score` if it is one
- **Fixing a wrong suggestion** is a one-word change to `means:`. Bands and
  dimensions follow the meanings. A column marked servicing, the key, or a date
  is never cut by, and the run says so.
- **It learns.** A file that runs with `columns_confirmed: yes` is remembered:
  each column name and its meaning, and each answered odd-value question (FICO's
  -9999 is missing). Next time, the remembered answer outranks every hint. If the
  values no longer fit it, it says CHECK. Only names, meanings and dates are
  stored, never values. The memory file lives on the machine that runs the tool
  (`~/.origination-cube/memory.yaml`, or `--memory PATH`, which a team can point
  at a shared folder). It is never in the repository.
- **Pruning.** The firm: *"an intuitive way to go and prune rules that shouldn't
  have been added."* You can:
  - list everything learned: `cube memory`
  - forget a column: `cube memory --forget COLUMN`
  - review it all in Excel: `cube memory --out learned.xlsx`, set a row's
    dropdown from Keep to Forget, save, then `cube memory --read learned.xlsx`
- **Odd values** are raised as questions and never stop the run: a -9999
  repeated far outside the rest, or negatives in a mostly positive column
  (RANR's are real). A question answered before comes back pre-answered and
  marked REMEMBERED.

## What "every band crossed with every dimension" means

- **A band** is a number column cut into ranges: score, DTI, LTV, loan amount.
- **A dimension** is a category column: channel, asset class, state.
- **A grid** is one band crossed with one dimension. Each crossing is a
  **pocket**.

A problem that only exists in a combination hides on each column alone. For
example, under-620 at 1.3x the book and marine at 1.1x can hide under-620
marine at 4x.

**Bands are yours to set** (the firm: "we could make more or less bands"). Each
band is either:
- **cut points you give**: `edges: [620, 680, 740]`
- **a count**: `count: 5, cut: equal_loans` (equal numbers of loans per band)
  or `cut: round` (the same, snapped to round numbers like 650 and 700)

The edges actually used are printed with every run.

A synthetic run showed why band count matters. The planted pocket sits below
620, but five equal bands put the first edge at 653, which diluted the
pocket's gap from 6.6x to 3.3x. Ten bands, or your own edges, sharpen it.

## Does a pocket underperform, and is it real (built)

Every pocket is compared three ways. Each comparison has its own multiple and
its own test.

| Compared with | What it shows |
|---|---|
| The rest of the book (without the pocket) | Does it stand out overall? |
| The rest of its band (without the pocket) | Does it stand out *within* its band? For example, under-653 Broker against under-653 Branch and Online |
| The rest of its dimension level | The same, the other way |

A fourth figure, **share of losses / share of volume**, is the pocket's rate
over the whole book's rate. It's the bleed measure, and the excess dollars
behind it add to zero across a grid, which the tie-out checks.

**The word for a pocket needs two things:**
- its multiple is past your threshold, and
- the test says the gap is unlikely to be luck at your confidence.

Past the threshold but not significant reads **"gap could be luck"**. Under
your minimum loan count reads **"too few loans to test"**. The word always
comes from the comparison its test made. A test proves this: a pocket holding
60% of the book at 1.4x the rest of it would pass as "in line" if it were
compared with itself included.

The synthetic run shows the within-band view doing its job. Under-653 is worse
than the book, but under-653 Online and Branch are 0.6x the *rest of their
band*. The band's problem is Broker, and Broker alone.

**How the test works.** Each pocket keeps six sums: loans, Σ top, Σ bottom,
Σ top², Σ bottom², and Σ top×bottom. The standard error of a ratio of two sums
comes from those sums (Cochran's ratio estimator). A pocket's peers are its
parent's sums minus its own, so Excel can repeat the arithmetic from the same
six columns. With every loan weighted 1, the test is the textbook
two-proportion z-test, and a test checks that to nine digits.

## How many loans is enough (the firm: "30 sounds low")

The suggestion used to be a fixed 30. It is now worked out from the book:
- **how many loans a pocket needs** before a gap of your size reliably shows
- **the smallest gap each pocket's size could show**

That depends on the book's loss rate, how much loss sizes vary, your
confidence, and how often a real gap should be caught (power). On the
synthetic book, a 1.25x gap needs about 2,800 loans in the bad-loan share,
3,500 in the booked-weighted bad rate, 3,700 in the GCO rate and 450 in the
RANR rate. It shows beside every run.

**It is evidence, not a gate.** The first version used it as the minimum, and
that hid the planted pocket: 531 loans at 6.6x, obviously real. A big gap
shows in a small pocket. So the minimum loan count stays yours (the old
workbook used 30), and only stops a test from running on a handful of loans.
Each pocket's own test decides whether its gap is real.

The calculation agrees with the textbook two-proportion answer within 6% (for
a 4.65% rate: about 2,750 loans for a 1.25x gap and about 200 for 2x). A
dollar rate needs more loans than a count rate, because loss sizes vary; a test
proves that too.

## Is it material (evidence built; the call is yours)

The tool never sets materiality. For every grid it shows what each level
would keep. This is the synthetic book's score × channel grid, GCO rate, as
`cube run` printed it on 25 Sep 2026:

```
Materiality evidence: what each level would keep (the level is your call)
   0.5% of book losses (83,185): 6 pocket(s), 98% of this grid's excess
   1.0% of book losses (166,370): 6 pocket(s), 98% of this grid's excess
   2.0% of book losses (332,741): 3 pocket(s), 82% of this grid's excess
   5.0% of book losses (831,852): 1 pocket(s), 56% of this grid's excess
  10.0% of book losses (1,663,703): 1 pocket(s), 56% of this grid's excess
```

Read it as a trade-off: going from 1% to 2% drops three pockets and 16 points
of the bleed.

You choose on the Control tab: 1% of losses, 5% of losses, no floor, or your
own dollar amount. Pockets under the level are listed below the line with their
combined total, never hidden (ruling OC-8).

## The Control tab (built: `cube control --out control.xlsx`)

Each setting is either **your judgment** or **method**:

- **Your judgment**: opens blank, and the run waits until you choose. Where the
  old workbook had a value, the option says so, but it isn't chosen for you.
- **Method**: opens on the recommended option, which is printed on every
  output.

| Group | Setting | Whose call | Takes effect |
|---|---|---|---|
| What the cube looks at | Which cuts / drill depth | method | re-run |
| | Loan age | **judgment** | re-run |
| How columns are recognised | Few values = category (12) / too many categories (50) | method | re-run |
| | How many bands (5) / where edges fall (equal loans) | method | re-run |
| Is it enough loans to matter | Fewest loans to test / fewest losses | **judgment** | live |
| Is it material | Smallest excess worth reporting | **judgment** | live |
| Does it underperform | Judged against / worse at / better at | **judgment** | live |
| Is it real | Confidence | **judgment** | live |
| | Power, multiple-test allowance | method | live |
| Proving it | Where it's tested (later originations) | method | re-run |

`cube init --control control.xlsx` writes your answers into the cube file.
Without a Control tab, every judgment line stays `[CONFIRM: ...]`.

**Not wired yet:** loan age, fewest losses, materiality, judged-against, and
the multiple-test allowance are on the Control tab, but the engine doesn't
apply them yet. They arrive with the workbook.

## Prove: from the pocket to the loans (proposed)

The firm asked for this to be "integrated into that script ... as a separate
function ... and checks should be built in yes. this has to be auditable".
So `cube prove` runs in the same tool, on the same cube file, and takes a
pocket written as a rule, for example `FICO < 620 AND CHANNEL = Broker`. It
shows:

1. **The group against the rest of its peers:** rate, multiple, test, and the
   allowance for many tests.
2. **That it held on loans it wasn't found in:** later originations, or the
   other half.
3. **That it isn't something else in disguise:** the gap within each level of
   every other column. The Portfolio Analysis Pack's step 4 is copied for
   this, extended from yes/no outcomes to dollar rates.
4. **The buy box with and without it:** the loss rate without the group,
   losses avoided, and volume given up.
5. **The loans:** every key in the group, so the LOB can check them. This is
   why the key is required.

**Auditable means each of these:**
- every figure sits beside the arithmetic that produced it
- every tab ties out to the book
- the output records the extract's hash, row counts and settings
- the list of loans reproduces every number from the loans alone

## Size

The firm's example population is 17,000 rows by about 80 columns. 100 grids
over 17,000 synthetic loans took 3.7 seconds with 1,700 tie-out checks
(measured 25 Sep 2026, before the per-pocket test was added). Pure Python is
enough.

## Rulings, 25 Sep 2026 (OC-1 to OC-4 are in `vba-findings.md`)

- **OC-5:** cross everything and rank it.
- **OC-6:** compare each pocket with the book and with its peers, a level down
  as well.
- **OC-7:** odd values are raised as questions and never stop the run.
- **OC-8:** materiality applies when reading, never when building.
- **OC-9:** a control center with explained options, and your own value
  allowed.
- **OC-10:** a proof stage on the loans themselves.
- **OC-11:** band count and cut points are the professional's to set (*"we could
  make more or less bands"*).
- **OC-12:** columns are recognised as band, dimension or neither by the tool,
  and only the clear cases are decided (*"hopefully we are self-identifying"*).
- **OC-13:** judgment settings are never pre-chosen; the tool gives evidence
  (*"that is the professional's judgment to apply"*).
- **OC-14:** the minimum an extract must carry is a yes/no outcome, GCO, RANR,
  the booked amount and a key. The key becomes required, reversing D55's
  warn-not-stop for this tool.
- **OC-15:** the required columns are suggested with reasons and confirmed by one
  line (*"make assumptions for suggestions but ultimately ask for confirmation
  ... and be able to fix it easily"*).
- **OC-16:** proof is a separate command of the same tool, with its checks built
  in and auditable.
- **OC-17:** every column gets a suggested meaning, and what is confirmed is
  remembered and outranks guesses the next time.
- **OC-18:** everything learned can be listed and pruned, by name or in Excel.
- **OC-19:** data recorded after booking is called **servicing** data, never
  "after origination". It is never cut by.
- **OC-20:** the Control tab shades what still needs an answer instead of
  labelling it, and its instructions are written the way the firm talks.
- **OC-21:** RANR is revenue, so bigger is better (*"RANR is a revenue metric - so
  it is profitability to some degree. bigger is better"*). Its bleed is a
  shortfall. Every extra rate has to say `higher_is: worse` or `better`.
- **OC-22:** nobody types commands. The firm: *"my preference is this is either in
  a GUI or something the workbook can help with it because i don't want this to
  be a technical exercise for users to run nor me to debug"*. They chose one
  workbook where every decision is made, plus a double-click launcher that does
  the running. An Excel button that starts Python was not chosen, because bank
  IT commonly blocks macros that start programs (and the repo's macro contract
  forbids it). It can be added later if the bank allows it.

- **OC-23: a third layer, by splitting every pocket.** The firm: *"we have FICO
  band, we have asset classes (1, 2, 3, 4) and then we want to add something
  based on the average or median revolving debt at origination"*, and on the
  two-at-a-time limit, *"kind of specifically want this option"*. One column can
  split the pockets (Columns, *Split pockets by it?*):
  - **A number is split at each pocket's own median.** Revolving debt moves with
    the score, so one cut for the whole book would mostly re-sort the score.
    Inside each pocket the high half is compared with the low half, and the
    pockets are pooled: Mantel-Haenszel odds for the yes/no outcome (with the
    CMH test and a check that the effect is steady from pocket to pocket), and
    observed against expected for the dollar rates.
  - **A category repeats the grid once per value**, side by side on Grids.
  - **The split column isn't also cut.** Its own band split by itself says nothing.
  - **The halves tie out:** every pocket is the sum of its halves, rows and
    numerators, and the tie-out can fail (`test_every_pocket_is_the_sum_of_its_halves`).
  - Checked on a planted book: `synth.py` makes a borrower above the usual debt
    for their score go bad 1.8x as often. The split finds 1.84x (1.67 to 2.01),
    worse in 20 of 20 pockets, steady (p 0.21). Loan size, which carries no
    plant, comes out between 0.8 and 1.2.
- **OC-24: GCO and RANR are read together, and neither is netted against the
  other.** The firm: *"we need a way to look at both together as well and gleam
  results. like GCO is high but profit is high - do we care? maybe"*. The
  **Losses vs revenue** tab puts every pocket in one of four boxes (losing
  more/less than the book, earning more/less), with each side's own flag and a
  scatter chart. Nothing is netted, because whether RANR already has credit
  losses taken out isn't known yet (Open, (c)).
- **OC-25: a median or average per pocket, for any number column** (Columns,
  *Show per pocket*). It's evidence beside the rates. It is never tested and
  never adds up across pockets, and the grid says so.

- **OC-26: the boxes on Losses vs revenue follow the lines on Control.** The
  third walk found the three worst bleeders in "Losing more, earning more" on
  revenue 2 to 5% above the book, which their own flags called luck. Asked to
  choose, the firm took "your own Control lines" over a luck test or no boxes,
  and asked for *"some mathematically defensible norm that the tool can
  suggest. Like yeah I'm definitely not counting your example as a pass simply
  because the revenue is on par"*. So:
  - Each side reads more, about the same, or less, and the box is the pair: nine
    boxes, worst first.
  - GCO uses "how much worse" and "how much better" from Control.
  - Revenue has its own Control call, *How far revenue must move before it
    counts*. The suggested option is **what luck alone can move it**, worked out
    from the book: the median, over pockets big enough to test, of the smallest
    RANR gap each pocket can tell from luck at the confidence and catch rate on
    Control. It is suggested in its label and never pre-chosen (OC-13 holds).
  - Box and flags use the same comparison, the one Control names.
  - One chart per grid, GCO on a doubling scale, the Control lines drawn, the
    three biggest bleeders named.
- **OC-27: the third layer is tested, and says what it holds fixed.** The firm
  chose, on 25 Sep 2026:
  - **Every grid stays, labelled.** In a grid that doesn't hold the score fixed,
    the high-debt half is also the low-score half, and a book with no debt
    effect read 1.7x. Each grid now says what it holds fixed, and gives the
    split column's correlation with the band column it doesn't. Grids that hold
    fixed what the split moves with come first. The reader decides; nothing is
    dropped.
  - **Three-way pockets on their own tab.** Every band / segment / split value
    pocket goes through the same test, flags, dollars and tie-out as any other,
    and is ranked on the Three-way tab. Where it bleeds stays two-way.
  - **The same floors apply.** A half under the minimum loans or losses isn't
    compared or counted.
  - **The rate ratio leads.** The odds follow as the test's own number. The
    p-value is called "luck alone": how often a gap this big turns up with no
    real difference.
  - **Only a score, ratio, amount or category can split.**
- **OC-28: the docket's answers (25 Sep 2026, 18:27 UTC).**
  - **The allowance for many tests stays per grid** and per comparison. Check says
    so.
  - **Suggestions where there's a calculation.** Each is a labelled Control option,
    never pre-chosen:
    - *Fewest loans*: enough to expect 10 with the outcome at the book's rate. Ten
      is the usual floor for a rate test.
    - *How much worse / better*: the smallest outcome gap a typical pocket can tell
      from luck (the median over pockets big enough to test), and one over it.
    - *Revenue line*: as in OC-26.

    A run with a suggestion does a first pass to work the number out, then runs
    with it. Check says what was worked out.
  - **Band edges are remembered** with a column's meaning. **A band width** ("every
    20") cuts at every 20 points across the column's values. The firm: *"20 point
    bands look very different. i assume all banding is adjustable to a degree"*. It
    is: a count (now up to 20 on offer), the placement, own edges, or a width.
  - **Not ready for work use until the firm says so**: *"you keep working and such
    on it and debugging, i will tell you when i think it's in a position to be
    used at work"*. The pull request stays a draft until then.
- **OC-29: RANR already includes credit losses.** The firm, 25 Sep 2026: *"ranr
  does include the credit loss as far as we can tell"*. So nothing is netted
  (Open (c) is closed): RANR less GCO would count the losses twice. It also means a
  pocket reading "earning more" is earning more after its losses, and the
  Losses vs revenue tab says so.
- **The fourth walk tightened OC-26 and OC-27.**
  - **A box side needs more than the line.** It moves off "the same" only when the
    gap is past the Control line and its own test says it isn't luck. That is how
    every other word in the tool is decided. With one line for every pocket, a
    176-loan pocket at 1.17x crossed a 1.16x line on noise.
  - **The suggested lines are luck alone:** the gap luck can make in a typical
    pocket at the Control confidence. The catch rate is left out; with it, the
    number was the gap a pocket can find (1.25x), not what luck moves (1.17x).
  - **The dollars on Losses vs revenue use the same comparison as the box.**
    Untested pockets get no box.
  - **What each grid holds fixed comes first** on the Split tab. It's on every
    row of the Three-way tab, where grids that hold it fixed come first.
  - **The booked amount can split.** It's an amount, like any other.
- **OC-30: the firm's calls on the fifth walk (25 Sep 2026).**
  - **The lines on Control decide the boxes, and luck is marked.** A side whose own
    test says the gap could be luck keeps its box, which then reads e.g. "Losing
    more, earning more (revenue gap could be luck)". The luck gate added after
    walk 4 is gone: with the test's bar near 1.5x, above every line, it had made
    the lines decide nothing.
  - **The suggested fewest loans is 5 expected losses at the book's rate** (n x p
    of 5 or more, the textbook floor), not 10. At 10 it hid a 99-loan pocket with
    50 bad loans. The firm: *"prior to now i had never considered having the
    floor be 5 of the output as opposed to X amount of the inputs"*. The loss
    floor (fewest losses) still checks the pocket's own count.
  - Also from the walk:
    - Remembered band edges only fill a column the workbook hasn't seen.
    - Clearing an edge cell forgets it.
    - Control shows what the last Run used.
    - The Split and Three-way tabs mark the grids that don't hold the split's
      partner column fixed.
- **OC-31: the suggested revenue line is each pocket's own luck range** (the firm,
  25 Sep 2026, after the sixth walk). Picked on Control, revenue counts as more
  or less only when its own test says the gap isn't luck. A small pocket needs a
  bigger move than a large one. The fixed options (5%, 10%, the loss lines, your
  own number) stay plain lines, the same for every pocket, with the luck mark.
  The sixth walk showed why one number couldn't work: 1.16x was right for a
  typical pocket, and the 176-loan planted pocket crossed it on noise.
  - A luck-marked box isn't shaded or counted with the findings.
  - The RANR column reads against the same line as the box.
  - The Split heat maps show a could-be-luck multiple in brackets, unshaded.
- **Every "Luck alone" figure is after the allowance for many tests**, the Split
  tab's included (they were the only raw ones until 25 Sep 2026). **The Split tab
  says its method once**, at the top: what it does, the numbers, the tests and what
  it assumes. Each grid then gets one line on what it holds fixed and a summary
  table. The firm: *"i would want it to outline what it is doing, what tests it
  used, assumptions and such"*, rather than the same paragraph four times.
- **Materiality in dollars is a GCO amount.** Control asks for the smallest
  excess *loss*, so a dollar line applies to GCO only and every other rate says
  it has no line (the third walk, defect 8).

## Open

- **(a) Real Excel.** Every tab has been seen through LibreOffice only. Still to
  check in Excel: how dropdown picks are stored, the validation pop-ups, and the
  chart.
- **(b) Proof stage** (OC-10, OC-16): from a pocket to its loans. Proposed, not built.
- **(c) Closed by OC-29:** RANR includes credit losses, so there is no net figure.
