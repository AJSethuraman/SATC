# PocketBook: design

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

Written 25 Sep 2026; the lists were brought up to date on 26 Sep. **Built:**
- the engine
- the per-pocket test
- `pocketbook init`, with a meaning for every column and a memory that can be pruned
- the Control tab
- the rest of the workbook: the launcher, Set up, Columns and every results tab

**Proposed, and the firm reacts before it's built:**
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

All three are commands of the one tool (`pocketbook run`, `pocketbook drill`, `pocketbook
prove`), reading the same extract, the same cube file and the same Control tab.
Each writes what it checked beside what it found.

## Step 0: what an extract must carry, and how the tool finds it (built)

The firm's minimum, 25 Sep 2026. The bleed analysis refuses if any of these is
missing. A test of a new variable needs only the key and the outcome from this
table, with the origination date, the column it tests and the pre-spec's strata;
the other three are optional for it (OC-14, amended 26 Sep 2026).

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

**`pocketbook init EXTRACT -o cube.yaml`** reads the extract and suggests what
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
  (`~/.pocketbook/memory.yaml`, one under `~/.origination-cube` still read, or `--memory PATH`, which a team can point
  at a shared folder). It is never in the repository.
- **Pruning.** The firm: *"an intuitive way to go and prune rules that shouldn't
  have been added."* You can:
  - list everything learned: `pocketbook memory`
  - forget a column: `pocketbook memory --forget COLUMN`
  - review it all in Excel: `pocketbook memory --out learned.xlsx`, set a row's
    dropdown from Keep to Forget, save, then `pocketbook memory --read learned.xlsx`
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
`pocketbook run` printed it on 25 Sep 2026:

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

## The Control tab (built: `pocketbook control --out control.xlsx`)

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

`pocketbook init --control control.xlsx` writes your answers into the cube file.
Without a Control tab, every judgment line stays `[CONFIRM: ...]`.

**Not wired yet:** loan age, fewest losses, materiality, judged-against, and
the multiple-test allowance are on the Control tab, but the engine doesn't
apply them yet. They arrive with the workbook.

## Prove: from the pocket to the loans (proposed)

The firm asked for this to be "integrated into that script ... as a separate
function ... and checks should be built in yes. this has to be auditable".
So `pocketbook prove` runs in the same tool, on the same cube file, and takes a
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
  warn-not-stop for this tool. *(Superseded in part on 26 Sep 2026, for a test of
  a new variable only. Asked whether that run needs the dollar columns, the firm:
  *"what's the point in that if you are searching for possibly important
  variables to the outcome?"* (`BACKLOG.md` §6d). That run needs the key, the
  outcome, the origination date, the column it tests and the pre-spec's strata.
  The booked amount, GCO and RANR are optional for it, and the Confirmatory test
  shows GCO dollars only when there is a GCO column. The bleed analysis still
  needs all five, and refuses without any of them.)*
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
    *(The words and the revenue multiple were superseded on 26 Sep by OC-38: profit
    reads "keeps more", not "earning more", and "not significant", not "could be
    luck". The rule that the lines decide and an unsure side is marked still holds.)*
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

  *(Superseded in part on 26 Sep by OC-38. The fixed options are now 0.25 points,
  0.5 points, the materiality line or your own number of points. "The loss lines"
  is refused, since a multiple can't judge a difference. A not-significant gap is
  bracketed, in points for profit. Each pocket's own test is still the suggested
  option.)*
- **OC-32: the revenue setting decides revenue on every tab** (the firm, 25 Sep
  2026, after the seventh walk). Before this, Where it bleeds judged RANR by the
  loss lines while Losses vs revenue used the revenue setting, so one pocket
  could read "earning less" on one tab and "in line" on the other. The engine now
  reads RANR by the revenue setting (`engine.revenue_bench`), and Losses vs
  revenue takes its revenue reading from the engine, so the two can't disagree.
  Consequence the firm accepted: under the suggested setting, any revenue gap a
  pocket's own test calls real is flagged, so more revenue rows reach Where it
  bleeds; the materiality line still drops the small-dollar ones.
- **OC-33: no red on a Three-way row whose grid doesn't hold the split's
  partner fixed** (the firm, 25 Sep 2026, after the seventh walk). Its gap may be
  mostly that column (the score, usually). The row keeps its reading and says "no:
  may be mostly FICO, so not red". A real effect of the split column still shows
  red in the grids that hold the partner fixed. Testing those rows within score
  bands is the fuller answer, and is left for later.
- **OC-34: the dollar-rate permutation test runs on numpy** (the firm, 25 Sep 2026:
  *"add numpy; this is the kind of script where it should outline what is missing and
  try to download it, right?"*). Plain Python took about 6 minutes a run on an
  8,000-loan book. numpy joins openpyxl and PyYAML as a required add-on. When any of
  them is missing, the launcher says which ones and offers to install them, and says
  what to ask IT for if the install is blocked.
- **OC-35: the losses inside RANR are GCO** (the firm, 25 Sep 2026). Contribution
  before losses = RANR + GCO. If RANR turns out to net recoveries, contribution is
  overstated by the recoveries; the definition is recorded on Check.
- **OC-36: the CMH test runs without the continuity correction** (the firm, 25 Sep
  2026), matching `docs/statistics.md` A6, and Check names it.
- **OC-37: share of loans uses the pooled two-proportion test** (`statistics.md` A1;
  the firm, 25 Sep 2026). It had been an unpooled test on n − 1: on one example that
  gave p 0.090, where A1 gives 0.035.
- **OC-38: profit is profit after losses, compared in points** (the firm's goal, 25
  Sep 2026, in `docs/NEXT-GOAL.md`; built 26 Sep, fixes 3.1–3.5).
  - RANR = interest income + fees − cost of funds − losses. It is compared as a
    difference in points of booked dollars (pocket − rest), never as a multiple. A
    multiple of two negatives read as "earning more", and a rest near zero blew it
    up.
  - Contribution before losses (RANR + GCO, OC-35) sits beside it.
  - Losses vs revenue reads *what they paid us / what they cost us / what we kept*,
    with a Together column: "priced for it", "net drain", "safe but idle".
  - The words are "p-value" and "not significant" rather than "Luck alone" and
    "could be luck". Profit reads "keeps more / about the same / keeps less".
  - This supersedes the multiples and wording in OC-30, OC-31 and the Losses vs
    revenue layout below. The rule that the lines on Control decide stands.
- **OC-39: dates are for the scouting pipeline, not the bleed analysis** (the firm, 26 Sep
  2026). *"The only instance in which our suite cares about dates is when we are doing the
  random analysis to try and find coefficients that are relevant ... when we are doing our
  bleed analysis and such I don't want to hide things from view. They are distinct."* And:
  *"Data hygiene we would already have sorted this issue out. We wouldn't have data in the
  future."*
  - **Removed:** the loan-age filter, the outcome window, the as-of date, the outcome date
    role, and `window_months` in the pre-spec. Each hid loans, or relabelled them, in a run
    that should show everything. Choosing the period is data preparation, done before the
    extract reaches the cube.
  - **Kept:** the origination date, for the pipeline only: splitting development years from
    the holdout, and flagging a run that touches the holdout. Check also prints the range
    of origination dates in the run, one line that removes nothing, so a wrong extract is
    obvious on the first page.
  - **The trees and the regression are optional steps.** *"We may skip those steps in
    particular altogether if we already have professional judgment to pick coefficient."*
    4b runs straight from a pre-spec whose column the analyst chose, with or without 4a.
  - **What I got wrong:** fixes 3.13 and 3.14 were built into every run without asking how
    they fit a generic analysis. The firm: *"Shouldn't have added that date work without
    conferring with me ... it's clearly non generic."*
- **OC-40: the judging settings are live in the workbook** (the firm, 26 Sep 2026: *"this is
  the stuff i want to be able to adjust in book on the fly ... i know it cannot reband and
  such"*).
  - **Live, as Excel formulas and conditional formatting:** the loss line (a multiple), the
    profit line (points), the materiality dollars, the confidence level, and judged against
    the book or the band. Each only judges numbers the run has already worked out.
  - **Still a re-run:** band edges, segments, the split column, the fewest-loans and
    fewest-losses floors, the shuffle count and the allowance for many tests.
  - **Guards:**
    - every tab shows the settings its readings are using, so a line changed since the run
      is obvious beside the Log's record;
    - significance compares with one rounded bar, `ROUND(1 − confidence, 12)`, as S36 requires;
    - ordering and Check's counts follow live only where the bank's Excel has `SORT` and
      `FILTER` (Microsoft 365); otherwise they are labelled as of the run.
- **OC-41: the shuffle test uses every core, and its answer does not depend on how many
  there are** (the firm, 26 Sep 2026: *"I'm good with plan"*, logged in `BACKLOG.md` §6d
  "Shuffle test across cores"; built the same day).
  - **Each shuffle has its own random stream**, the i-th child of the run's fixed seed
    (numpy's `SeedSequence(seed).spawn(...)[i]`, `perm.order_of`). Shuffle i is the same
    order whichever process deals it and whatever that process dealt before.
  - **The shuffles are split into runs of consecutive shuffles, one per worker**, and the
    counts added up in order. Workers are the cores this process may use, at most 8
    (`perm.MAX_WORKERS`); a run under 20 million loan-shuffles stays in one process,
    because starting workers costs about a third of a second. Workers are started the
    way Windows must start them ("spawn") on every machine, so the tests run what the
    bank's machine runs; `PocketBook.pyw` opens its window only when it is the
    program, never in a worker.
  - **Proved bit for bit**: every count, answer and kept shuffled gap is the same on 1, 2,
    3 and 4 workers (`tests/test_perm.py`). A machine that will not start workers, or a
    worker that dies, falls back to one process and gets the same answer.
  - **The p-values moved once**, because the 10,000 shuffles are a different 10,000. On the
    synthetic books (3,000 and 8,000 loans, 465 shuffle p-values) the largest move was
    0.0149 (6,145 → 5,996 of 10,000), about 2 standard errors of the difference between two
    independent runs; the moves' spread was 0.91 of that error, and no allowed-for p-value
    crossed 0.05.
  - **Timing**, `perm.run` on the realistic 17,000-loan bleed run (160 statistics), 10,000
    shuffles, under a 4 GB memory limit on a 4-core machine: 53.6 s before; 57.9 s on one
    worker, 27.4 s on 2, 20.5 s on 3, 20.9 s on 4. Each worker peaks at about 70 MB.
- **OC-42: a test of a new variable builds no bleed analysis** (the firm, 26 Sep 2026, on
  `BACKLOG.md` §6d: *"Yes. Seems obvious I think. They have entirely different outputs
  generally"*).
  - **What it runs:** the confirmatory test and only what that needs. The pre-spec's strata
    are cut into the bands they get on Columns (the engine still works out every band's
    edges). The loans are split into development and holdout, and 4e's concentration is
    worked out. Check and the Log are written as usual. `engine.run` builds no pocket grid,
    no three-way or split grid, and no shuffle test when `run_kind` is `new_variable`
    (`Result.bleed` is False).
  - **What it writes:** the Confirmatory test, Check and the Log. The bleed's tabs (Where
    it bleeds, Losses vs revenue, Grids, Split, Three-way, Prevalence) are **taken off**
    if an earlier bleed Run left them. Keeping them would put another Run's pockets beside
    this one's test, and their Start here tiles would read verdicts that no longer match
    anything. Check says so in one line ("Bleed tabs") where the tie-outs were, and leaves
    off the bleed's own lines: pockets, budget, families, the loans needed, and the
    materiality line. Prevalence goes with the bleed because it counts the grids' own
    pockets and is tied out to them.
  - **What it shows:** Start here's *What the last Run found* and the launcher's last step
    read the confirmation instead of nought pockets of nought. They show the groups that
    go bad significantly more often than the reference on the holdout, those groups'
    share of the holdout's bad loans, the loans tested, and whether the run followed the
    pre-spec. Start here's count follows the confidence on Control (`significance_bar`).
  - **The bleed Run is unchanged:** on the synthetic book (4,000 loans, split by REV_DEBT),
    all 136,762 cell values are the same before and after, and so are the launcher's lines
    and the record of what ran. The one exception is the extract's path.
  - **Timing:** a pre-spec Run on 17,000 loans × 80 columns, under a 4 GB limit, went from
    23.4 s (12 grids, one shuffle test) to 4.5 s (none).
  - **Not settled:** Control still asks the fewest loans and the loss lines for a new
    variable, and still suggests them. Those suggestions were worked out from the bleed's
    grids, so on such a Run the loss lines fall back to the usual values.
- **OC-43: the result tabs pick what they show with dropdown cells over hidden sheets** (the
  redesign's phase 3, 26 Sep 2026; the firm's redesign, sections 5 to 8, with the rulings given
  for the build: slicers become dropdown cells, the column is "p-value", never "luck").
  - **Four tabs where there were seven:** *Pockets* (Where it bleeds and Three-way), *Paid, cost,
    kept* (Losses vs revenue), *Grids* (with Prevalence under its blocks) and *Split*. A Run takes
    the old ones off an older workbook.
  - **Dropdowns, not slicers:** openpyxl cannot write slicers and drops them when it saves a
    workbook, which every Run does. Pockets has Measure, Pockets (two-way or split) and Show;
    Paid cost kept a Grid; Grids a Grid and a Measure; Split a Grid and a Measure.
  - **How a dropdown picks rows without SORT or FILTER:** Pockets' candidate rows sit on the
    hidden `_list` in the last Run's order, each with its live Worse? and Material? (read from
    `_pockets`), a 1 when the dropdowns show it, and a running count of those. The k-th row shown
    is the first whose running count reaches k (`MATCH(k, …, 0)`). Every other number these tabs
    show is one keyed row on the hidden `_views` ("G|FICO x CHANNEL|gco_rate|book|2"), read by
    `INDEX`/`MATCH`. LibreOffice 24.2 calculates it, so the tests prove it.
  - **Live and as of the Run:** Worse?, Material?, the dollars, the gaps, Together and every colour
    follow Control (OC-40). The order of the rows, the smallest gap each pocket could have caught
    and the heat maps are the last Run's, and each tab says so once. Ranking: the worse pockets
    first, by the dollars that decide; then the rest by theirs; then the pockets losing more only
    against the other comparison, so a change of *Judged against* finds them.
  - **Worse? and Material? are separate columns** (NEXT-GOAL item 7): Yes / Not sure / No / Too
    few losses, and Yes / No.
  - **Tenet T1:** the Test column and the lone-pocket note are off the rows. Each tab's one method
    note says which test gave the p-value and that a pocket alone in its band is judged against
    the rest of the book. The test behind each p-value stays pocket by pocket on `_pockets`.
  - **Together reads five pairs** (the redesign, section 6): priced for it, net drain, strong
    (fewer charge-offs, more kept), safe but idle, and earns less, not from losses (less kept,
    charge-offs about the same). Blank on a row with a side untested.
  - **One rule per cell:** LibreOffice applies one conditional format to a cell, the first that
    holds; Excel applies every one that holds. So each rule carries everything its cell needs
    (fill, font, number format, the row's divider), and a cell sits in one range only.
  - **The scatter is live:** its points are the table's cells (through the hidden `_chart`, since
    Excel leaves out a chart's points in hidden columns), so it follows the Grid dropdown and
    Control. The spec said "as of the last Run"; live is the stronger promise.
- **OC-44: judged against the book counts points and dollars against the rest of the book**
  (Option A, NEXT-GOAL item 5; the firm, 26 Sep 2026: *"i think this makes most seense"*).
  - A pocket's dollars under *the rest of the book* are its losses less what it would have lost
    at the rate of every other loan in the book (`excess_rest`), the same rest its gap and its
    test are taken against, as the band's are over the rest of its band.
  - OC-4's excess over the whole book stays as the tie-out only (`vba-findings.md`): across a
    grid it adds to zero, and the Run checks that on every grid.
  - A worse pocket now always has dollars above zero under either comparison, so every pocket
    Pockets could flag is on its list whatever Control says.
- **OC-45: New variables replaces the Confirmatory test tab, each candidate with and without the
  held-fixed columns** (the redesign, section 9; the firm's lean pre-spec, 26 Sep 2026: each input
  reported on its own and with the columns held fixed).
  - **A row is one comparison:** a group of the pre-spec's column against its reference group. *Found*
    is the development loans with nothing held fixed; *Confirmed* the held-back loans with nothing
    held fixed, and *Holds up?*; *Confirmed, X held fixed* the same loans inside the pockets the
    pre-spec's strata make (the test the Confirmatory test tab showed), and *Still holds?*. Then
    *Excess*, *Material?* and *In words*.
  - **Without the held-fixed columns** is the same conditional logistic regression with every loan of
    a range in one pocket (`confirmatory.Test.development_plain`, `holdout_plain`). It costs about 0.2 s
    a range at 12,000 loans.
  - **No `hold` list in the pre-spec:** its `strata` are the columns held fixed. The launcher already
    shows a saved shortlist's strata under *Hold fixed*, and with `strata: []` there is one
    confirmation and the held-fixed columns read "Nothing held fixed". Old pre-specs read unchanged.
  - **Holds up? / Still holds?:** significant against the one rounded bar (OC-40), on the side of 1 the
    found loans showed. Live, as is *In words*.
  - **Excess** is a group's charge-offs on the held-back loans above its share of them (its share of
    the held-back loans), times the book's charge-offs over the held-back loans', so it is on the scale
    of Control's line (a share of the book's losses). Bad loans instead when the run has no GCO per
    booked dollar. *Material?* compares it with the line in use, live.
  - **A saved shortlist hides the Found columns** (the spec), and Record names the file. Every run of a
    new variable today confirms a saved shortlist, so Found is always hidden; the columns are still
    written, and the tests in full show both sets of loans. Nothing else sits in those two columns, so
    unhiding them is safe.
  - **Every statistic the Confirmatory test tab showed is kept**, under the chart as *the tests in
    full*: B3 and B4 and the block test, B5 with its live range, each on the found and the held-back
    loans with and without the held-fixed columns, and 4e's concentration on the holdout. Each keeps
    its one plain line; the method notes merged into the tab's one folding note (T1).
  - **The chart** reads the table's cells: Confirmed INK, held fixed KEY_RED (Found STONE when shown),
    and a dashed red line at `worse_at`, fed by a hidden column so it follows Control.
- **OC-46: Record merges Check and the Log** (the redesign, section 10).
  - **Six sections in three pairs:** This Run | Settings; Does it add up | Tests used; Left out |
    Every Run. Each of Check's lines is sorted into its section by its label (`record.section_of`); a
    warning goes with the line before it, and the engine's own warnings (about the extract) go under
    Left out.
  - **Settings** has one row per Control setting the run asked: in use now (a formula over Control:
    `_live`'s words for a Changes-now line, the answer's label for a Needs-a-Run one), what the last Run
    used, and a hidden flag that is 1 while they differ, which shades the pair. It replaces Check's
    "In use now" block and its "What the last Run used" list.
  - **The Log is kept on the hidden `_log`,** in the Log tab's own layout, so a refused Run adds its
    entry and Every Run is drawn again without the rest of the Run. An older workbook's Log becomes
    `_log` as it is, and its Check goes. What counts the held-back runs reads `_log`.
  - **Departures:** rows keep one line where their words fit and wrap where they don't (Check's lines
    are sentences, some of 500 characters); a pair's two rows share a height. A value of several lines
    (what the pre-spec says) is one row a line. The tab has a short folding method note, as every tab
    does (Global rule 1.2), though the mock shows none.
- **OC-47: a pre-spec is recorded, never blocked** (the firm, 26 Sep 2026, reopening "lock first": *"i
  don't think there's a reason to have some sort of over the top control in place"*).
  - **Its fingerprint** is the first 12 characters of the SHA-256 of the file as read. The first Run
    to read a fingerprint logs *"Pre-spec prespec.yaml written: fingerprint …, dated … in the file,
    committed … in …; first read by this run."*; later runs log it *as before*.
  - **A change after a held-back run** (the last earlier run on that pre-spec that touched the holdout
    read another fingerprint) logs *"Changed pre-spec: prespec.yaml changed after the held-back run of
    …: fingerprint A then, B now. This run is on the changed pre-spec."*, and Record warns. The run goes
    ahead.
  - Record's *This pre-spec's held-back runs* lists them in order, each with its fingerprint, a change
    marked. The git commit is recorded where it exists, as before.
- **OC-48: Control asks a new variable only what it uses** (the redesign, phase 4).
  - **Asked:** worse at (the New variables chart's line), materiality, confidence, and the band count
    and cut (the held-fixed columns are banded). **Hidden:** fewest loans, fewest losses, better at,
    judged against, the catch rate and the allowance for many tests (`only_when: {run_kind: bleed}`),
    as the profit line already was. *(Amended 27 Sep 2026, OC-49: the allowance for many tests is asked
    of a new variable too, since a shortlist's groups are many tests at once. Control's method note says
    only worse at is worked out on that run, and its levels panel, which counts pockets, is hidden.)* Hidden rows are not asked, and the Run stands in their defaults,
    which decide nothing without a pocket.
  - **Worse at is suggested from the confirmation's own groups** (`book.test_gap`): the smallest odds
    ratio a group of typical size could call significant against the reference, on the development
    loans: the median over groups of exp(z × √(1/(n p q) + 1/(n_ref p q))). It reads group sizes and
    the overall bad rate, never which group went bad.
  - **Set up builds no bleed grid for a new variable.** Found 27 Sep 2026: the suggestion pass forced
    the run to Where the book bleeds and cut every column it was given; the timing harness's Set up,
    written without the launcher's choices, cut all 74 number and category columns (1,248 grids) and
    peaked at 2.5 GB. A new variable's Set up now runs the confirmation instead: that Set up went from
    92.7 s and 2.41 GB to 12.8 s and 0.27 GB, under a 4 GB limit. A bleed Set up with nothing chosen still
    cuts every column (87.5 s, 2.43 GB); the launcher always chooses, so only a script meets it. Through
    the launcher a pre-spec Set up was 0.29 GB before and after.
- **OC-49: the lean pre-spec is an outcome plus a shortlist of inputs** (Goal 2 item 3; the firm, 26 Sep
  2026: *"well it cannot be one column, but a shortlist whatever. one column makes no sense - it can't be
  used in a tree"*, and *"we might want to test a set once with and once without"* FICO).
  - **The file:** `outcome:` and `inputs:`, each input exactly `column`, `bins` and `reference`, beside
    `strata`, `confidence`, `holdout` and `development`. Every line is required, none has a default,
    and an input with a line missing or unknown is refused by its place (`inputs[1].bins:`). An input
    listed twice, a stratum that is also an input, the outcome listed as an input or held fixed, and a
    file with `inputs:` and a top-level `column:` as well are refused.
  - **The one-column pre-spec is still read, as a shortlist of one.** It names no outcome (the line did not
    exist), so it is tested against the outcome the run marks, as before, and Record echoes it as it did.
    A file with no input's line at the top is read as a shortlist, so a file missing its inputs is asked
    for `inputs:`, not for the old lines. Written as a shortlist of one, the same input gives the same
    tab, number for number (`tests/test_shortlist.py`).
  - **The outcome is recorded, not enforced:** a run tested against another outcome than the file names
    says so on Record as a deviation, like any other. The launcher picks the file's outcome when the
    extract has it.
  - **The allowance for many tests spread across the shortlist:** every group of every candidate
    against its own reference is one test, and each set of loans (found and confirmed, with and without
    the held-fixed columns) is one family, as a grid's pockets are one family per rate (statistics.md
    A2: "one grid, one rate, one comparison"). The method is Control's *Allowing for testing many pockets
    at once* (`engine.adjust`, Benjamini-Hochberg by default), now asked of a new variable too. The table's
    p-value columns show the allowed p-value and read *p, allowed* (*p-value* with No allowance);
    *Holds up?* and *Still holds?* read it; the tests in full keep every raw p-value, and their own
    readings are the raw ones, as they were. The allowed p-value does not depend on the confidence, so
    the verdicts stay live.
  - **Departure, and why:** a shortlist of one now allows for its own groups, where phase 4 read each
    group raw. A grid of one column's bands is allowed for across its bands, and a candidate's groups are
    the same kind of family; keeping one input raw while two inputs are allowed for would make the
    allowance jump from none to eleven tests when a second input is added. Every odds ratio, raw p-value,
    count and excess is unchanged; only a verdict whose group sat between its own p-value and the allowed
    one moves, and with *No allowance* on Control the verdicts are phase 4's exactly.
  - **New variables:** one block of rows per candidate in the pre-spec's order (the name bold on its
    first row, a heavier rule between blocks), a chart per candidate read from its own block, and the
    *Candidates* tile counting the candidates with a group that holds up, live ("3 · 2 hold up"). The
    tests in full come candidate by candidate under *The tests in full: X*. The method note names the
    allowance once (*Many at once*). A shortlist of one reads as before.
  - **Start here and the launcher's last step** count groups worse than their reference across every
    candidate, after the allowance. With several candidates the share of bad loans is replaced by the
    candidates with a group worse, since several candidates' groups hold the same loans and their shares
    don't add up.
  - **The suggested worse line** is the median over every candidate's groups (`book.test_gap`), each
    against its own reference, on the development loans.
  - **Strata are suggested and left blank** in what PocketBook writes (OC-13; the firm's answer on the 26
    Sep docket): the line offered for a missing `strata:` reads `[CONFIRM: ...]`, which the file refuses
    until it is answered, and so does the committed shortlist example.
  - **Phase 4's loose ends:** on a new-variable run Control's method note says only worse at is worked
    out, and says Material? is on New variables; the levels panel (it counts pockets, and that run builds
    none) is hidden, and shown again for the bleed.
- **OC-50: scouting finds on the development loans, writes the pre-spec, and the confirmation reads it, in one
  Run** (Goal 2 item 9; capability 4a; statistics.md B7; the firm, 26-27 Sep 2026: scouting is *"to try and
  guess importance ... it should be wider"*, *"dates are for the scouting pipeline"* (OC-39), and *"test a set
  once with and once without"*). `scout.py` does the work, `scout_tab.py` writes the Scouting tab and its lines on
  Record and the Log.
  - **The loans.** *(Since OC-51, the line is a cutoff date picked on Control, not a share.)* Ordered by origination date, the first `find_share` of them (the launcher's *Find on 70%*)
    are the development loans; the loans made after the last development date are held back. Scouting reads
    the held-back loans' dates only, to draw the line and to name the holdout's range; `development_rows`
    picks the development loans from the dates alone and nothing after it sees the others. A test turns every
    held-back outcome over and scrambles every other value of theirs, and gets the same shortlist number for
    number and the same file.
  - **Candidates:** the columns ticked Test it, plus every new column made on Columns (one divided by
    another), never an outcome or a held-fixed column. Wide is fine. A category is given one number per value,
    in the order of its values, and is ranked but never proposed (the pre-spec cuts a number at its bins).
  - **The forest and the ranking.** scikit-learn's random forest, 200 trees, leaves of at least 40 loans, seed
    7; permutation importance as the drop in AUC when a column is shuffled, on loans the forest did not train
    on, cross-fitted: the development loans are cut into 3 runs by date, each scored by a forest grown on the
    other two, 5 shuffles a column a run, averaged. Twice: with the candidates alone, and with the Hold fixed
    columns in the forest too; the held-fixed columns' own importance is shown under the table.
  - **The noise floor and the proposal.** The same forests on the development loans with their outcomes
    shuffled among them (so no column can matter), repeated until there are at least 20 importances; the floor
    is the largest. **Proposed:** a number column whose importance clears the floor with the held-fixed columns
    in the forest or without them, and whose shape bends somewhere to cut. Said once, in the tab's note.
  - **Bins and reference.** Partial dependence over the column's own percentiles (1% to 99%), from a forest
    grown on every development loan (with the held-fixed columns in it when there are any, as the confirmation
    holds them fixed), averaged over 1,000 development loans drawn by seed. A cut where the curve steps by at
    least 25% of its average, largest step first, each group at least 2% of the development loans (a sliver
    left between two close steps joins the neighbour whose rate is closer), at most 6 groups. The edge inside a
    step is where the forest itself split the column most (the weighted median of its thresholds there,
    weighted by how much each split separated bad from good), at two significant figures. The reference is the
    group holding the development loans' median, as scout-vs-measure.py's is.
  - **Correlated pairs:** Spearman's rank correlation of 0.7 or more either way, on the development loans with
    both values, among the number candidates and the held-fixed number columns; each row lists its partners,
    and the note says the line once.
  - **The file.** `<extract> - pre-spec.yaml` beside the workbook, in the shortlist format (OC-49): the proposed
    inputs in rank order, each reference written as its number with its name in a comment, `strata` the Hold
    fixed columns chosen in the launcher or, with none chosen, `[CONFIRM: ...]` (OC-13), which the file refuses
    until answered: the Run then writes Scouting and Record, tests no held-back loan, and returns the file's line
    as what it waits for. Written only when no file is there. **A file already there is confirmed as it stands**
    and never written over: an edit is the analyst's, Record's Log labels an edit made after a held-back run
    (OC-47, unchanged), and the Scouting tab lists where the file differs from this Run's proposal (the day it
    was written is not a difference). Delete it to have the next Run write the proposal again.
  - **Record, don't block:** the Log's entry has scouting's line (the development loans, how many were held
    back and not read, what was proposed, the file written with its fingerprint and date, or kept) ahead of the
    held-back lines; Record has *Scouting*, *Scouting held back*, *Scouting's pre-spec* and *Tests: scouting*.
    The file is written to disk before the confirmation reads a held-back loan.
  - **The confirmation is the shortlist path, unchanged:** the file is handed to it as a saved one is. Its Found
    columns show (they were found on this Run's development loans), and its note says the pre-spec was written by
    scouting.
  - **Seeded and repeatable.** The same extract and choices give the same forests, the same shortlist and the
    same file, byte for byte on the same day. scikit-learn's own `predict_proba` adds the trees up in whichever
    order its threads finish, which moved the partial dependence in its 17th figure between two Runs of one
    book; the trees' votes are added up here in the trees' own order. scikit-learn's version is recorded, since
    forests are not bit-identical across its versions.
  - **scikit-learn is optional** (`deps.OPTIONAL`, the `scout` extra; the firm, 26 Sep 2026: "Optional
    add-on"). Without it the cube starts and runs; finding is refused by the Control cell that chose it, in
    words; confirming a saved shortlist works; the launcher's Choose tests offers *Install scikit-learn* where
    finding needs it. CI installs it, so the scouting path is checked (S14), and a test simulates it missing.
  - **Of `docs/scout-vs-measure.py`:**

    | Part | | Why |
    |---|---|---|
    | Random forest, leaves of at least 40, fixed seed | Kept | B7's model |
    | Permutation importance by drop in AUC, on loans the forest didn't train on | Kept | B7's ranking |
    | Partial dependence (the column set to one value for every loan, the predicted rate averaged) | Kept, worked out directly | Same arithmetic, over the column's own percentiles instead of a typed grid, on a seeded draw of 1,000 loans, with missing values allowed |
    | The reference: the group holding the median | Kept | as `ref = 2` there |
    | 400 trees, 10 shuffles, one 70 / 30 split by row position | Changed: 200 trees, 5 shuffles, cross-fitted in 3 runs by date | Time at 17,000 x 80 with 40 candidates; cross-fitting scores every development loan once: on the first book (20,000 loans, three candidates, 400 trees either way) the floor went from 0.018 to 0.014 and income / sales from 0.020 to 0.025 with FICO and CHANNEL in the forest |
    | Edges "written down after looking at (2)" | Changed: found from the curve's steps and placed at the forest's own splits | Wide: dozens of candidates can't each be read by eye. The analyst can still edit the file |
    | Two books, "development" and "holdout", as separate arrays | Changed | One extract, split by origination date, the held-back loans removed in code and proved unread by a test |
    | A noise floor | Added | The firm's "clearly above the noise floor from a shuffled-label baseline" |
    | `make_book` | Dropped | PocketBook reads the extract |
    | The plain logistic regression with the ratio as a number | Dropped from the cube, kept in the doc | B7's worked example of why a straight line misses a cliff |
    | The binned regression on the holdout | Moved, unchanged | It is the confirmation (4b, OC-45, OC-49) |
    | The frozen forest's AUC on the holdout | Dropped *(put back by OC-51, 27 Sep 2026, after the pre-spec is written)* | B7: development only. The holdout's one job is the pre-specified test |
    | `n_jobs=-1` on permutation importance (processes) | Dropped | Threads, and the trees' votes summed in their own order, for repeatability |
  - **Found building it, fixed:** (1) a test of a new variable with nothing held fixed, or with a number held
    fixed and no category, was refused by the bleed's own minimum ("Nothing is left to cut"); it builds no grid
    (OC-42), so it needs none (`config.py`, `engine._drop_outcome_cuts`). (2) Over values from 0.03, bins at
    [0.1, 2] named the lowest group "0.0 - 0.0", a range below every value in it; with fractional edges the
    lowest group now takes the decimals its own values need ("0.03 - 0.09", "0.10 - 1.99"; whole-number edges
    are named as before), and the pre-spec recognises a group named from the run's range, so a run held to such
    bins doesn't read as deviating.
  - **Choices made here that no ruling settles yet:** the proposal rule (either forest, not both); the floor as
    the largest of at least 20 null importances; the 25% step, 2% share and 6 groups; a category ranked and not
    proposed; a file already there never written over.
- **OC-51: the tree is the main path: a cutoff the analyst picks, the tree checked on later loans, and the
  shortlist regressed together** (Goal 4; the firm, 27 Sep 2026: *"isn't the tree the entire point? how can it be
  optional."*, then *"shouldn't it regress all of those identified variables if it actually deems them important?
  import --> tree runs --> tree guesses on 2024 data if 2022-2023 are used to build branches --> regress
  shortlist?"*, then *"yes build it out"*). `scout.py`, `joint.py`, `confirm_tab.py`; statistics.md B10 and B11.
  - **The cutoff replaces "Find on 70%".** A judgment setting on Control (`cutoff`, Needs a Run), asked only when
    scouting: *Loans made before this date find the candidates; the rest are held back*. OC-13: the suggestion
    (the first of the month nearest the date by which 70% of the loans had been made, keeping a loan each side) is
    worked out at Set up and shown under *Worked out from the loans* with how many loans fall each side; the answer
    is blank until the analyst picks the suggestion or types a date under *Or your own*, and a blank one refuses
    the Run by its cell, like every other judgment setting. The pre-spec scouting writes carries it exactly:
    `development` ends the day before the cutoff and `holdout` starts on it. The launcher's share picker is gone;
    70% survives only as where the suggestion comes from (`scout.SUGGEST_SHARE`). A saved shortlist is confirmed
    on its own ranges and is not asked the cutoff.
  - **Scouting is the main path.** In the launcher, *Test new variables* scouts unless a saved shortlist is picked
    (*Or confirm a saved shortlist instead*, the secondary way in); Control's step reads *Scout first*, the main
    path, and *Test from a pre-spec*, a shortlist saved earlier. The Choose tests table itself is untouched.
  - **The tree's out-of-time check (B11).** Only after the pre-spec is written and read (a pre-spec still waiting for
    an answer stops before it), the forest grown on every development loan scores the held-back loans; with columns
    held fixed, the forest with them in it too. One line, on New variables first and on Record: *"Built on loans
    made … : AUC 0.62. On loans made … , unseen: 0.60."* It reads the held-back loans, so the Log gives it a line
    of its own starting *Touched the holdout:*, and Record's count of runs that touched the holdout now counts runs,
    not lines (one Run touches it twice when it scouts). This reverses OC-50's "the frozen forest's AUC on the
    holdout: dropped" for this one check, after the file is fixed.
  - **Every candidate together (B10).** One logistic regression on the held-back loans with every shortlisted
    candidate's groups (each against its pre-spec reference) and one constant per pocket the held-fixed columns
    make. Unconditional with the pockets as control dummies, not conditional: the conditional likelihood over
    every combination of every candidate's groups does not finish at the bank, and PocketBook's pockets are the
    large-strata case where the constants are well estimated (Breslow & Day 1980, ch. 6); under 5 bad loans a
    pocket it refuses instead. Per candidate: each group's odds ratio together with its live range and Wald
    p-value, and a likelihood ratio test of taking the candidate out (what it adds net of the others), with the
    run's allowance across the shortlist. A group with no loan, no bad loan or only bad loans has no odds ratio (its
    loans taken out, as kgroups does); a group holding exactly another candidate's loans is said to be
    indistinguishable; a candidate whose reference can't be compared with is left out, said so; a fit that still
    runs off refuses the whole model in words. Pairs moving together (Spearman's 0.7 on the development loans, as
    scouting flags them) are named beside both, with one line under the table on how to read "adds nothing" for
    such a pair. With one candidate the section is not drawn: together is the same as alone.
  - **New variables leads with them.** The method note's first items are *The tree, unseen* and *All together*
    (T1: said once); then the tiles; then *The tree on loans it never saw* (the line), *All N candidates
    together* (the table, *Adds?* live against the bar, and a live line naming which add something), then *Each
    candidate on its own*: the per-candidate table, charts and tests in full, unchanged. No check figure that can't
    fail (T2).
  - **Figures on the synthetic books** (the current build; the tab as LibreOffice draws it is
    `docs/new-variables-together.png`):
    - *The scouting book* (`tests/test_scout.py`: 12,000 loans, nine candidates, FICO and CHANNEL held fixed). The
      suggested cutoff is 2024-11-01: 8,394 development loans (673 bad), 3,605 held back. Proposed: UTIL and
      income / sales. The tree: *Built on loans made 2021-06-30 to 2024-10-31: AUC 0.63. On loans made 2024-11-01
      to 2026-03-30, unseen: 0.60. With FICO and CHANNEL in the forest too: 0.69 built, 0.68 unseen.* Together, on
      3,596 held-back loans (278 bad) in 18 pockets: UTIL above 0.9 2.35× (1.82 to 3.04), adds 41.12 on 1 df,
      p 3 × 10⁻¹⁰ after Benjamini–Hochberg; income / sales above 2.00 2.62× (1.66 to 4.13) and below 0.10 2.00×
      (0.99 to 4.06), adds 17.36 on 2 df, p 0.0002. Both add something the other doesn't.
    - *The shortlist book* (`tests/test_shortlist.py`, 20,000 loans, income / sales, UTIL and TENURE, FICO and
      CHANNEL): income / sales adds 19.67 on 5 df (p 0.002 allowed), UTIL 47.19 on 3 (p 1 × 10⁻⁹), TENURE 3.56
      on 3 (p 0.31): statistics.md B10's table.
    - *A near copy* (UTIL_COPY, UTIL plus a little noise, ρ = 0.96 on the development loans): flagged beside both;
      alone it holds up (1.83×, significant), together it adds 1.96 on 1 df, p 0.16, its odds ratio 0.74.
    - *The walk's book* (8,000 loans, the procedure's Part C): only REV_DEBT is proposed, so the joint table is not
      drawn; the tree: built 0.67, unseen 0.63 (0.69 and 0.65 with FICO).
  - **Timing**, a scouting Run at 17,000 × 80 (40 candidates, FICO and CHANNEL held fixed, 4 processors shared
    with other work, load about 1.5): 72.6 s and 72.4 s before, 76.6 s and 74.8 s after; peak memory 0.76 to 0.79
    GB either way. The few seconds are the forest without the held-fixed columns grown once more on every
    development loan, the held-back loans scored by both, and the joint fits.
  - **Choices made here that no ruling settles yet:** the suggestion's month start (nearest, earlier on a tie);
    the joint model's floor of 5 bad loans a pocket; the out-of-time forest being the same 200 trees as the
    ranking's; one likelihood ratio p-value per candidate as the family the allowance covers.
- **Every pocket's "Luck alone" figure is after the allowance for many tests**,
  the Split tab's heat maps included (they were the only raw ones until 25 Sep
  2026). The Split summary's pooled figure is one test per grid and measure, so
  there is nothing to allow for. **The Split tab
  says its method once**, at the top: what it does, the numbers, the tests and what
  it assumes. Each grid then gets one line on what it holds fixed and a summary
  table. The firm: *"i would want it to outline what it is doing, what tests it
  used, assumptions and such"*, rather than the same paragraph four times.
- **Materiality in dollars is a GCO amount.** Control asks for the smallest
  excess *loss*, so a dollar line applies to GCO only and every other rate says
  it has no line (the third walk, defect 8).

- **Bands read as ranges: "620 - 679".** The firm, 25 Sep 2026: *"i want bands
  to be written in "0 - 660" form, or whatever. adding words over symbols makes a
  big difference to how cluttered it feels and the easy of reading"*. The lowest
  band starts at the column's smallest value and the highest ends at its largest,
  so every band has two ends. Scores and dollars read as whole numbers; a ratio
  keeps the decimals its edges need.

- **Losses vs revenue shows the numbers behind each reading, and no box.** The
  firm, 25 Sep 2026: *"i don't think that which box is a relevant thing to need,
  i can just visually see that. conditional formatting is fine to draw attention
  to stuff. also i want to see the underlying - instead of just listing GCO vs
  Comparison, find a clean way to display the comparable metrics"*. Each side
  (losses, revenue) has its own five columns: this pocket's rate, the rest's
  rate, the multiple, the reading and the dollars over the rest. Red and green
  sit on each side's multiple and reading; a side that could be luck is marked
  and left plain. The box is still worked out, to order the rows and name the
  chart's worst pockets, but it is not printed. *(Since 26 Sep, OC-38: three
  sides, paid, cost and kept, plus Together. Profit and contribution show a gap in
  points where losses show a multiple, and "not significant" replaces "could be
  luck".)*
- **Control's In use takes a number the run takes.** Excel stores a pick of
  "95%" as 0.95. The run already read that as the 95% option, but In use said
  "not an option". Found on the render, 25 Sep 2026.

- **The engine knows no column, value or number by name.** The firm, 25 Sep
  2026: *"it's confusing to me that you talk in terms of specific datapoints
  because it worries me we are not working with a generic engine"*. It works from
  a column's *meaning* (outcome, booked amount, GCO, RANR, a score, a category),
  confirmed on Columns; everything else comes from the book or from Control.
  That covers the bands and their edges, the segments, the split column and the
  column it moves with, the lines and the floors. Every number quoted from a walk
  comes from the one synthetic book. `tests/test_generic.py` runs the whole route
  on another book (an auto book with other column names and a problem planted in
  a dealer and a region) and checks that the workbook finds that problem and
  carries nothing from the synthetic book. Writing that test found the one place
  that did: Control's explanations used the synthetic book's pocket as their
  example.

- **The adversarial pass (26 Sep 2026).** Another model was given the arithmetic
  (`stats.py`, `perm.py`, the engine's use of them, `checks.py`) with one job:
  break it, writing tests only.
  - **The count:** it formed 33 hypotheses and ran them. 4 produced a failing test
    (8 tests), 27 came out clean, and 2 went red only on inputs it judged unlikely.
    It reported those 2 without filing them: a book where every loan loses exactly
    the book's rate, and a pocket alone in its band under "the rest of its band"
    (its flag is blank; see the hand-back). About 10 more were settled by reading
    the code. *(The "2" was left out of this note until the final check found 4 +
    27 ≠ 33.)* It cross-checked against scipy and statsmodels:
    Fisher, the chi-square and normal tails, Mantel–Haenszel, CMH, BH, the power
    search, the family count and seed determinism.
  - **The four findings, all fixed** and held by `tests/test_adversarial_2026_09_26.py`:
    - **A p-value exactly at the bar** read significant at 95% but not at 90%,
      because 1 − 0.95 is not 0.05 in floating point. There is now one rounded
      bar, `stats.bar`.
    - **Cochran's Q** was centred on ln OR_MH instead of A8's weighted mean, which
      could only lean toward "the pockets disagree".
    - **A rate that couldn't be worked out** read as "the book's rate is zero".
      Unknown is its own answer now.
    - **A pocket the shuffle test couldn't answer** still named the shuffle test.
  - **Two assertions were corrected in triage:** the Q cases asserted the flip
    itself, and one family count was wrong about a pocket with no band neighbour.

## Open

- **(a) Real Excel.** Every tab has been seen through LibreOffice only. Still to
  check in Excel: how dropdown picks are stored, the validation pop-ups, and the
  chart.
- **(b) Proof stage** (OC-10, OC-16): from a pocket to its loans. Proposed, not built.
- **(c) Closed by OC-29:** RANR includes credit losses, so there is no net figure.
