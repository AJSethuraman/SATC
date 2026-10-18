# threshold-engine log

Newest at the bottom. What was decided, by whom, in their words where there
are any, and what is waiting.

## 6 October 2026

**Scope.** The bank: *"this tool we are creating is not meant to score
everything. It is meant to help assign thresholds which will score in another
file."* The engine proposes cutoffs. It does not rate a portfolio.

**Scale.** 1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High.
Outlook (increasing, stable, decreasing) is rated separately by the bank,
projected from recency-weighted quarterly changes. The bank: *"the outlook
rating is far less important ... It's just provided."*

**Judgement belongs to the expert.** The bank: *"This is seemingly judgment an
expert should have input on. I want you to supply literal information that can
be inferred upon."* So `profile` reports facts with no judgement settings, and
`evidence` puts statistics on each judgement point.

**What the evidence found on public net charge-off history.**
- Robust z of each spell's peak against the rest of history (3.5 = unusual,
  Iglewicz and Hoaglin 1993): mortgage 2002 = 0.8, home equity 2001 = 0.3,
  cards 2002 = 4.4, and 2008 = 7 to 32 in every product. So cards have two
  stress episodes and the other three have one each.
- Scenario C (remove 2008 only if another spell is unusual) removes it for
  cards only.
- Other consumer's dip in 2011Q1 is the Call Report splitting auto out, not
  credit.

**Recency.** The bank asked for more weight on recent years. Tested three ways:
1. On the normal level: barely moves cards or other consumer. Collapses
   mortgage and home equity to zero at a 5-year half-life, which is refused.
2. In an outlook rule (stand-in, not the bank's): fixed long-history
   thresholds did better for cards. For other consumer it was a trade-off.
3. On how predictive the level is (`backtest`): long history was the most
   predictive of the level a year ahead (cards 0.80, other consumer 0.76
   Spearman, against 0.68 and 0.70 at a 5-year half-life). No scale predicted
   deterioration: every score-vs-change correlation was negative.

The bank: *"I suppose this makes sense ... This should be a standard measure
we are going for. Determining how predictive stuff is and how recency affects
it."* Recency stays a hypothesis to test on KeyBank's own series on site.

**Shape of the finished tool.** The bank: *"the way pocketbook works is how I
want this to work. It has UI does everything at once and then gives you the
output inside of Excel using the numbers that it helped standardize. So I
guess sure individual commands are fine but eventually, it's gotta work this
way."*

### Waiting on the bank
- Materiality, and whether a spell must reach z 3.5 to count as stress, or
  some other line.
- Half-life, if any. The evidence so far argues for none on the thresholds.
- The boundary rule: does a value exactly on a line take the worse score?
- The top fraction (where score 5 begins) and the percentiles of the scale.

### Next
One run from one screen. Point it at the series, state the settings once, and
it runs profile, evidence, recency and backtest together. The output is one
Excel workbook, PocketBook-style, with a run stamp and every number traceable
to its source rows.

## 6 October 2026, later

**The workbook is built.** The bank: *"I expect this to move quickly because
it's far simpler in nature."* `workbook` writes one Excel file covering every
product: live cutoffs driven by a red Settings tab (the
portfolio-analysis-pack pattern: statistics as values, judgements as cells,
results as formulas), a chart with product switches on one scale, and the
evidence, backtest, data and run stamp. Style is the suite's vendored
`keybank_style.py`.

Checked in real Excel 16 and, in tests, with the `formulas` engine. As built,
the cutoffs equal scenario A. With the evidence's suggestion typed in (cards,
2007Q4 to 2012Q4), they equal scenario C to the third decimal.

Found while checking: the chart drew nothing, because Excel skips hidden
columns and its helper columns were hidden. Fixed with `visible_cells_only =
False`, and seen fixed in Excel.

### Next
The window (`Thresholds.pyw`), PocketBook-style: pick the files, state the
measure, run, and open the workbook.

## 6 October 2026, temporary departures

The bank: *"Is 2008 a specific thing in this book? ... Covid for instance had
a huge dip in delinquency that obviously didn't sustain because it was just
reporting differently than it did."* Then: *"you can literally see that dip
happen in charge offs ... If you remove it it basically continues."*

Two gaps it exposed:
- "2008" was hardcoded into a Settings explanation. It now describes whatever
  the data found.
- The engine looked for unusual periods only on the bad side, and by level.
  By level the pandemic dip is not unusual (cards z -2.3), because it sits
  inside a long stretch below the median.

What finds it is shape: a stretch that leaves the path between the quarters
either side and comes back. The bridge test does this, largest event first,
then sets that event aside with one window-length either side before looking
again. Cards: 2008, 2002, then 2021Q3-2023Q1 below the path. Other consumer:
2008, then the dip. Mortgage: no dip, because its losses were already near
zero. On card 90+ delinquency (FDIC, every filer) the dip starts in 2020Q1,
about a year before it shows in charge-offs, consistent with charge-off at
180 days past due.

Not hidden: the dip ranks deepest (1 of 91) but its z is -2.0, short of 3.5.
The data finds it and cannot prove its cause, which is why each leave-out
window now carries a Reason cell recorded on the Run tab. A first, naive
reversal statistic found nothing and flagged 2008's slopes. It was dropped,
not tuned. Home equity's second departure (2013-15) is the curved tail of its
2008 run-off, which a straight bridge reads as a dip. The workbook says so.

What the dip means for today: of cards' 2.2-point rise from the 2022 low,
about 2.0 is a return to the pre-dip level and 0.26 is above it. For other
consumer, 0.7 is the return and 0.44 is above it.

## 6 October 2026, the Assess tab

The bank: *"set credit card to ignore the periods for the crisis and covid and
show me the actual graph output that helps assess thresholds after that's
decided."* The Chart tab drew cutoff lines over series, which shows where the
lines are but not how history falls between them. Assess shades the five
bands behind one product's every quarter, marks the quarters left out as grey
dots, and counts the quarters in each score. All of it is live.

Cards, with 2007Q4-2012Q4 (financial crisis) and 2021Q3-2023Q1 (pandemic
forbearance) left out: cutoffs 3.757 / 4.469 / 5.180 / 5.892. Of the 135
quarters kept, 67 are Low, 29 Moderate-Low, 22 Moderate, 12 Moderate-High and
5 High (2002Q1-2003Q1). These match an independent recount in Python. Today's
3.98% is Moderate-Low, and the 2024-25 peak of 4.57% is Moderate.

Found in Excel, three times over: Excel drew no tick labels when the area
chart was the base of the combination, and giving the axes fonts didn't help.
A line chart as the base fixed it. Excel also joins a line across #N/A, so
left-out quarters are markers on the full line rather than a gapped line.

### Waiting on the bank
- Is High for cards right at once in about 33 years of kept history? If not,
  move "Score 5 begins" below 0.75.

**Left-out periods, shown as cut.** The bank: *"I want a better way to show
when we cut stuff out. Maybe on the bottom of the original chart it literally
displays them cut out?"* Each left-out period is now a dark strip under the
axis, and its dates and reason are listed under the chart, live from Settings.
The strip is an area: Excel drew 163 stacked columns on this shared axis as
thin slivers whatever their gap width.

## 6 October 2026, where score 2 begins

The bank: *"I feel as though low is too generous. It may be factually
reasonable but professional skepticism kicks in in thinking low is where the
curve spends a lot of its time."* That was right by construction: score 2
began at the median of the quarters kept, so Low covered half of history.
Where score 2 begins is now a Settings cell per product, a percentile of the
quarters kept, and the CLI requires a starting value.

Tested before building: lowering it mostly moves quarters from Low into
Moderate-Low, and High barely changes, because loss rates spend most of
their time low and spike rarely. Cards at the 33rd percentile: Low 33%,
Moderate-Low 27%, Moderate 26%, Moderate-High 9%, High 5%. Today's 3.98%
stays Moderate-Low. Other consumer's 1.78% becomes Moderate from the 40th
percentile down. Mortgage at the 33rd percentile starts score 2 at 0.08%, so
"0.01% is not a 2" still holds; at the 25th it is 0.05%.

### Waiting on the bank
- Score 2's percentile, per product. Recommended: 33 ("better than two-thirds
  of history"). The test: should cards' 2017-2020 stretch at 3.6-3.7% read
  Moderate-Low?

## 6 October 2026, the scale centred on normal, and a glossary

The bank: *"I would think median is a 3 if anything. I think it's not perfect
because there's likely a range around it that represents the same risk as
the center."* Moderate is now a band around the median of the quarters kept,
plus or minus a stated number of typical yearly moves. A typical yearly move
is 1.4826 x the MAD of every four-quarter change whose both ends are kept.
Moderate-Low begins a stated number of moves below the median, and High
begins a stated share of the way from Moderate-High's line to the worst kept.
All three are Settings cells, and the CLI requires starting values.
`scale.py` is the Python reference the workbook's formulas are tested
against.

Before building: a band of median +/- half a yearly move nearly matches the
middle third of history (cards 3.48-4.03 vs 3.42-4.38), so the band is not
arbitrary. Percentiles were rejected for the low end because mortgage's and
home equity's 15th percentiles are at or below zero.

Cards, both periods left out, 0.5 / 1.5 / 0.5: lines 2.879 / 3.464 / 4.050 /
5.326. Today: cards Moderate, other consumer Moderate-High, mortgage and home
equity Low, the same at every band width tried. The catch: cards then spend
34% of the quarters kept in Moderate-High and 3% in Low.

The Glossary tab has 33 terms, each with what it means and how it is
calculated. A test fails if a heading has no entry.

Found by mutation: the change-over-four-quarters formulas must not begin
before the fifth row. The formulas engine tolerated a reference above row 1
that Excel would report as a damaged file, so a test now scans every formula.

### TTM, checked
The firm asked whether the engine replicates TTM. Cards and mortgage come
from the Federal Reserve as the mean of four seasonally adjusted annualised
quarterly rates (all commercial banks). Home equity and other consumer are
built from FDIC filings: twelve months of net charge-offs over the average of
four quarter-end balances. For cards since 2006 the FDIC version runs a
median of +0.05 points above the Fed one, +0.2 in 2019, and +0.77 at most.
That is enough to move a rating near a line.

### Waiting on the bank
- Moderate's width. Does cards' 1996-2006 stretch read Moderate-High
  (0.5) or Moderate (0.75-1.0)?
- Moderate-Low's step: Low for cards is nearly empty at 1.5.
- Cards and mortgage on the FDIC TTM definition (matches the bank's; shorter
  history) or the Fed's (longer; a different definition)?

## 6 October 2026, TTM basis kept; the Fed's other consumer explored

**Decided.** Cards and mortgage stay on the Federal Reserve's definition for
now. The bank: *"I'm fine with leaving it as is for now knowing that it's
unlikely huge spikes are happening across all banks at all times unless for a
common reason it should be relatively stable."* Consistent with the check:
median gap +0.05 points against an FDIC TTM built the bank's way.

**Explored: the Fed's "consumer loans: other"** (charge-off release
chgallsa, 1985-2026, all commercial banks, SA; read from the HTML table,
with the card column tying to the engine's card series within 0.0005 over
163 quarters). "Other" is consumer less credit cards, so it includes auto
in every year. It tracks the FDIC series with auto added back (median gap
-0.08 before 2011, -0.09 after) and departs from the as-filed line after the
2011 split (-0.40). One definition from 1985, but half auto: right for
counting cycles, wrong for levels on a mostly unsecured book.

What it shows: 2008 is the only clearly unusual episode (z 12.1). The
early-2000s cycle peaked at 1.465% in 2003Q2, z 3.3 against quarters outside
both cycles: real, but under 3.5. 1990-91 barely registers (z 0.6). The
pandemic dip is clearer here (departure z -2.7, against -2.2 on FDIC as
filed). Under the 3.5 rule other consumer keeps 2008, the same answer the
FDIC series gave, now from two sources.

Saved with the evidence pack (fedco/), not added to the repository's test
data: nothing has adopted it yet.

### Waiting on the bank
- Add the Fed's other consumer to the workbook as a reference row, for its
  cycles and departures beside the FDIC line?

## 7 October 2026, High on a z, and dials on Assess

**Cards' settings agreed:** Moderate half-width 0.5, Moderate-Low step 1.0.
The bank: *"I think that makes sense. Unsure about High being arbitrary."*
Before agreeing, seven options were compared on the same tests: whether
the median is Moderate, spread across scores, real-time predictiveness, and
benchmark periods. 0.5 / 1.0 was the only option to pass all four (spread
0.95, Spearman 0.80; the range across options, 0.75-0.82, is within noise).
That comparison also corrected an earlier claim: widening Moderate to 0.75
does not pull cards' 1996-2006 stretch into Moderate. Only 1.0 does, and
only partly.

**High is now a robust z of levels:** median + z x 1.4826 x MAD of the
quarters kept. Halfway-to-worst moved 2.1 points for cards when 2008 was
kept or left out; z 2.5 moves 0.75. On cards with the crisis left out, the
textbook 3.5 puts High above everything kept, so the workbook refuses it.

**The bank, on how to choose it:** *"Can we just make this part of what we
do in the book to assess it? ... then they can be sort of dialed."* Assess
now has a dial for each of the three settings. Each row shows the four lines
and the kept quarters in each score at another value, the others as on
Settings, and the current setting is highlighted. Every row is tested
against `scale.py`.

Cards at 0.5 / 1.0 / 2.5: lines 3.171 / 3.464 / 4.050 / 5.981. Kept
quarters: Low 25, Moderate-Low 22, Moderate 29, Moderate-High 55, High 4
(2002 only). Today is Moderate.

Found while building: the dials first wrote into column L, where the Assess
chart's hidden helpers start. The dials now stop at K. A mutant that made
the dials ignore the on-the-line rule survived until a test put quarters on
a line.

### Waiting on the bank
- High's z for cards (2.5 recommended), and whether 41% in Moderate-High is
  acceptable. At z 2.0 it is 36%, and High is 7%.
- The same comparison for other consumer before reusing cards' settings.

## 7 October 2026, peers, and KeyBank's other consumer mix

**Peers.** Gross and net TTM charge-offs by product for credit-suite's 15
verified peers plus KeyBank, 2007-2026, from the FDIC pulls (evidence pack,
peers-gross-net/). A bank-product window is left out if it touches a quarter
where the book moved more than 25% (merger, sale, reclassification): 128
such quarters on books over $1bn. Books under $1bn are left out too, except
KeyBank's. Shown on a page where the pack is chosen bank by bank (the bank:
*"some peers like citi are not really peers"*), with two peers or the best
and worst at once. "Regionals only" is my grouping, not a definition.

**KeyBank's other consumer is held down by mix.** The bank: *"key's other
consumer is likely being held very down in charge offs by the laurel road
portfolio."* Public filings agree. The balance went from $2.3bn (end 2018) to
$6.5bn (2022) while net charge-off dollars stayed $25-60m a year. Against
every FDIC filer, KeyBank's rate tracked the industry until 2018 and then sat
at 0.4-0.5x of it from 2019 through 2025, after the pandemic had unwound for
the industry (1.49x its 2018 level by 2025). Year by year that factor matches
1 / KeyBank's balance growth: dilution by a book that loses next to nothing.
The 2021 low splits about 40% pandemic (shared by all banks) and 60%
KeyBank-specific, on a log scale. KeyCorp's 4Q20 release: consumer direct
loans averaged $3.13bn in 4Q19 and $4.58bn in 4Q20, yield 6.45% to 4.93%,
growth attributed to Laurel Road. Public data does not split out the student
loans.

Bounded: the book without student loans lost about 1.9-3.0% in 2024,
against a regional median of 1.56% and the industry's 1.63%. The blended
1.11% looks better than the pack.

The bank: *"private lenders offered plenty of forbearance by request ...
Laurel road never had a high charge off rate. It's a bad business model as
opposed to poor strategy."* So the student loans' issue is economics (yield,
margin), not credit. That belongs to an earnings or strategic assessment, not
to these thresholds.

### Decided, for the thresholds
- Other consumer is two books: student loans (Laurel Road) and the rest.
  Each gets its own scale, from internal data on site. A blended scale would
  rate the riskiest consumer book on a number held down by the safest.

## 12 October 2026, one scale, and all of it built in

The bank's answers to the release docket: *"1. Take recommendation 2. Yes 3.
Nope, all of it. Test it and make sure it works. 4. That works I mean what
else can we do"*, then *"1 and 2 are good for v1"*.

- **One scale.** The first engine and `cutoffs` retired; `evidence` now
  reports on the workbook's scale (`scale.py`).
- **A window.** `Thresholds.pyw` builds the workbook without a command line.
- **All of it.** Every side analysis run inline since 6 October is now in the
  tool: `peers pull`, `peers build`, and a peer workbook with the Pack, Peers,
  Balances, Lagged, Normalisation and Mix tabs. They were built to
  `docs/PEERS-SPEC.md` by a multi-agent run. Each module was then reviewed by
  two agents trying to break it: 71 findings, all reproduced and all fixed,
  each with a test that fails without its fix.
- **Card settings** 0.5 / 1.0 / z 2.5, with the crisis and the pandemic left
  out, accepted for the rehearsal.
- **Next in v1:** delinquency and nonaccrual by product, and templates for
  the internal data. On the 90+ definition: *"It depends and you don't need
  to know, if you're making all 3 it shouldn't matter."* So every variant is
  built, and the bank picks one per measure.

Decided here without the bank, and open to its veto:
- **FDIC change code 215, "Failure Multiple Acquirer", counts as an
  acquisition.** The pull's own refusal caught it live: two rows in 2008,
  neither acquirer on the roster. A failed bank was split between buyers, so
  each buyer's next filing carries part of a bank it did not have. Marking it
  can only leave a quarter out of a window. It never adds a number.
- `min_banks` has no default. 5 reproduces the earlier build.

Run end to end against the real cache. Pull: 82 quarters, 0 fetched. The live
merger record matched the fixture for all 16 roster banks. Build: 4½ minutes.
Opened in Excel 16: every chart draws and no cell holds a formula error. The
CSVs it writes load into `workbook` unchanged. On the card settings above,
worst in pack is Citizens and best is JPMorgan (net, last 20 quarters).

Not done yet: the window's Peers step (command line only for now). The
KeyBank peer CSVs start in 2018Q1, because the First Niagara window breaks
everything before it, so on their own they cannot carry the 2008 crisis.

## 12 October 2026, round 2: delinquency, templates, the window's Peers step

Built to `docs/V1-ROUND2-SPEC.md` by a second multi-agent run: one builder
per part, one reviewer per part trying to break it, then fixes. 28 findings,
each reproduced; the fixes carry tests that fail without them.

- **Delinquency and nonaccrual by product** (`peers/delinquency.py`): five
  measures (30-89, 90+ accruing, nonaccrual, 90+ incl. nonaccrual, 30+ incl.
  nonaccrual) on two bases (quarter-end, four-quarter average), per bank, pack
  composite, band and industry. First filed quarter of each field recorded in
  the module (probed 12 Oct). A blank field is "not filed", never 0.
- **Templates** (`templates.py`, `template list|write|check`): seven, each a
  `date,value` file whose `#` notes ask what the bank must state. A third
  column is refused, so no account-level data can travel in one.
- **The window's Peers step** calls `peers/run.py`, which the command line
  also calls. A build puts its files in place together or not at all; a file
  open in Excel is named and nothing changes.

Run end to end on public data. Pull with `--delinquency yes --refresh`: 82
quarters fetched, 6 minutes; an old cache without the fields is refused by
name. Build: 11½ minutes, 180 series CSVs (30 charge-off, 150 delinquency).
Opened in Excel 16: the Delinquency chart draws under three settings with no
formula error. Opening it found the DelinquencyData headers clipped; columns
widened.

**Tied out:** KeyBank card 90+ days past due and still accruing, 2026Q2, read
from the workbook in Excel: 9,346 ($000). KeyBank's filed Call Report, RC-N
line 5.a column B (RCFDB576): 9,346, on the page and in the XBRL fetched
today. Balance and rate tie too. Exhibit:
`docs/tie-out/keybank-card-90plus-2026-10-12/`.

Found on the way, recorded not changed: Citizens files zero card 90+ accruing
in all 82 quarters, so that measure alone does not compare banks like for
like; KeyBank's card 90+ accruing is 0 in 2012Q3–2013Q2 on a ~$700m book.

Open, for the bank: whether the pack composite's four-quarter average applies
the jump rule (NEXT-GOAL section 1). Not done: `ssn`-shaped numbers pass
`template check` when the stated scale is wide enough to hold them; the
stated scale is the bank's own.

Suite: 675 passed (15 min).

## 12 October 2026, round 2 answers: the composite's average, code 215

The bank's answers to the two questions round 2 left open:
- **The pack composite's four-quarter average leaves out a bank the jump
  blanked.** *"yeah i think removing them makes sense - i want it to be clear
  though. like in the glossary or something it should list what we are
  omitting and why."* Each of the four composite quarter-end rates in the
  average at i is recomputed without the banks whose own four-quarter average
  at i the jump blanked, so the composite and the band are built from the
  same banks. The quarter-end composite is unchanged: one filing per bank,
  no jump. The same rule is in `delinquency.composite_delinquency` and in the
  live formula on the Delinquency tab (DelinquencyData gains a last column
  marking each bank left out); the workbook tests check one against the
  other. `avg4_jumped` is now `avg4_left_out`, and each composite CSV's note
  names the banks left out, by quarter.
- **What is omitted, and why:** the Glossary gains **Left out, and why**
  and under it one row per reason, seven in all: an acquisition (the jump), a
  small book, not filed, fewer than four quarters, not included, too few
  banks, and before a gap. Each says why, the rule, and where each omission
  is recorded (Data, DelinquencyData, the series notes). A test holds it to
  that list. The Delinquency tab's note points to it. A first draft put all
  of it in one cell; opened in Excel it was a wall of text, so it was split.
- **Code 215 counts as an acquisition.** *"sure"*. The Glossary's
  Acquisition quarter entry now names it.

Checked: the live Delinquency formula, opened in Excel 16 on mortgage
nonaccrual, four-quarter average, equals `composite_delinquency` in all 38
quarters (22 with a bank left out, e.g. JPMorgan, Flagstar and Citizens in
2023Q2), with no formula errors; the Glossary rows were read in Excel too.
Suite: 677 passed (14 min); the 88 affected tests rerun after the Glossary
was split into rows.

## 12 October 2026, the Codex review of PR #426: four findings, all real

Marking the PR ready started the Codex review. It found four things, none in
the day's change, each verified against the code before it was fixed:
- **Labels.** The window refused a product label Excel cannot hold (a comma,
  a double quote, a leading `=`, or two labels differing only in capitals,
  which `MATCH` treats as one); `workbook.build`, which the command line
  calls, did not. The rule now lives once, in `series.LABEL_RULE` /
  `label_ok`, and both apply it.
- **A value that is not a number.** `float()` reads `nan` and `inf`, so a CSV
  holding one reached the calculations. One reader, `series.read_csv`, now
  serves every front door and refuses it, naming the file and the date.
- **A half-life of 0 or below.** The window refused it; the command line let
  0 crash with a division error and a negative one quietly weigh old
  observations above new ones. `scale.recency_weights` refuses both.
- **Two versions.** `pyproject.toml` said 0.1.0 while the workbooks' Run tab
  writes 0.11.0. The package now takes its version from
  `threshold_engine.VERSION`; a wheel built from it reads 0.11.0.
Each has tests (28 new cases), at the command line and on `build` itself.
The full suite then caught one more: a test built a workbook labelled with
the template title "Refreshed credit score, portfolio average", which the new
label rule refuses (the comma would split it in Excel's dropdown). The title
is now "Refreshed credit score (portfolio average)", and a test holds every
template title to the label rule. Suite: 706 passed.

## 13 October 2026, the second Codex pass, and a CI failure missed

Codex's review of the fixes (1722a00) found four more; each checked:
- **A file without the `date,value` header** crashed with a `KeyError`
  traceback instead of a refusal. `series.read_csv` now refuses it, naming
  what the header holds.
- **Smoothing longer than the series** returned nothing, and the commands
  crashed further on. `series.smooth` refuses it.
- **The Backtest tab always labelled five change columns**, so with three
  percentiles "Quarters tested" sat under "after 5". The columns now follow
  the number of scores.
- **"The mean change is sign-flipped for lower-is-worse."** Not changed: it is
  in the measure's own units, as the mean level beside it is, so a score that
  fell 50 points shows -50. The "positive = deterioration" line Codex quoted
  is about the Spearman column, which is oriented. Nothing said which units,
  so the report and the Backtest tab now say so, and a test holds it.

**A CI failure I had not looked at:** `pytest (credit-suite)` had failed on
this branch since 1bc8905. credit-suite's conformance check forbids a
byte-identical copy of its `engine/style.py`, and `keybank_style.py` is one,
deliberately: this project imports nothing from credit-suite so it can lift
out whole (docs/PEERS-SPEC.md). The check already exempts separate products
for that reason (credit-review-os, portfolio-analysis-pack); threshold-engine
is added to that list, citing the spec. My earlier note that only Cloudflare
was pending was wrong: the PR's red check was never read.
Two template tests had asserted that the build crashes (`KeyError`) on a bad
header, to show why `template check` refuses it; the build now refuses in
words, and they assert that instead. Suite: 714 passed in the full run, and
the two rewritten tests pass, 716 in all.

## 13 October 2026, the third Codex pass

On 90995b5, three more, each in code written before today and each real:
- **P1: smoothing above 1 split the workbook in two.** Evidence and backtest
  used the smoothed series; Data, Thresholds, the latest value and the score
  used the raw file. The workbook now builds every line from the smoothed
  series (the window already said smoothing comes "before anything else");
  the Run tab says so and keeps the file's own row count. A test with
  smoothing 4 checks Excel's live lines against `scale()` on the smoothed
  values. Every workbook built so far used smoothing 1, so none is affected.
- **A NaN or "inf" charge-off in the cache** was kept and carried into every
  rate. `books._num` refuses it, naming the bank, quarter and field, as
  delinquency already did.
- **Monthly evidence measured a four-month "yearly" move.** `scale()` takes
  `periods_per_year` (4 or 12, from the declared frequency, not a judgement)
  and evidence passes it. The workbook stays quarterly-only.
Suite: 731 passed (14 min).

## 13 October 2026, the fourth Codex pass

On 022b898, seven, all in code older than this week, all checked and fixed:
- **P1: the workbook could be written over its own input.** `build` now
  refuses an output that is not `.xlsx` or that resolves to any input file.
- **The Assess chart, lower-is-worse:** the lines fall, so the stacked bands
  had negative widths. The stack now starts at score 5. Opened in Excel 16 on
  a mirrored score series: five bands, High at the bottom, no formula error.
- **Leave-outs are checked live.** Half a range, a reversed one, one off the
  calendar, or one with no reason silently kept every quarter. The Check
  column now refuses each, ahead of every other check (seen in Excel too).
  It also refuses a negative half-width or a z at or below 0, and `scale()`
  refuses both, in the same words, for the command line.
- **A row without a value** was a `TypeError` traceback; the shared reader
  refuses it naming the file and row.
- **A missing file** was a traceback for `profile`, `evidence` and
  `backtest`; it is refused, as the workbook and templates already did.
- **Monthly evidence spoke in quarters**, and its departure windows were 8,
  12 and 16 months. Labels follow the frequency, and windows are 2, 3 and 4
  years either way.
Six workbook tests had set leave-outs without a reason, which is now
refused; they state one. Suite: 746 in the full run, then test_workbook.py
rerun whole (34 passed): 752.

## 13 October 2026, the fifth Codex pass

On 04905ef, three, all real:
- **P1: the peer build could replace its own inputs.** A workbook path equal
  to the roster or merger record replaced it; one not ending `.xlsx` could
  be a series CSV, which then replaced the workbook. `peers build` now
  refuses both before anything is read or written.
- **Impossible dates passed.** `2020-13-31` cleared the step test and
  became 2020Q5. `series.check` now requires a real calendar date written
  YYYY-MM-DD.
- **The Assess bands below zero.** The first band was the cut-off itself, a
  negative width. The stack now starts at an invisible base, the chart's
  floor (the lowest of 0, the data and the cut-offs), and the top takes in
  the cut-offs too. Opened in Excel on a series shifted below zero: five
  bands, each between its own lines.

Opening it found one more: the Assess axis hid every negative label (a
format that keeps the grey strip unlabelled). The public mortgage and home
equity series go below zero (net recoveries), so the chart already hid real
values for them. Negative labels now show whenever the measure is not
floored or any value is below zero.
The full run then had one failure: a template test expected `2015Q1` to be
refused as a gap; it is now refused as not a date, and the template check's
message and the spec, which gave the old reason, now give the true one. The
Assess axis change came after the full run began, so test_workbook.py and
the template tests were rerun whole (113 and 99 passed). Suite: 762 in the
full run plus the one fixed: 763.

## 13 October 2026, the sixth Codex pass

On 4903237, four, no P1, all real:
- **Text in the Moderate-Low step** gave `#VALUE!` in the line, the score
  and Assess. The Check column now refuses it ("must be a number") and the
  line is blank, as the half-width and z already were.
- **Two peer shorts differing only in capitals** ('Alpha', 'alpha') loaded,
  and Excel's MATCH would plot the first for both. The roster refuses them.
- **The product pickers were inline lists**, which Excel drops or repairs
  past 255 characters. They read from cells now. Opened in Excel 16 with
  four long labels (over 255 together): no repair, and picking one works.
  (This also closes the 255-character item noted on 12 Oct.)
- **The Backtest tab said "only the history before it"**; the history runs
  up to and including the quarter scored, never after. Kept as built (a
  quarter's own value is known when it is scored) and the words corrected
  on the tab, in the Glossary and in WHAT-IT-DOES.
Suite: 768 passed (18 min).

## 13 October 2026, merged without a final Codex review

Codex answered the sixth pass's fixes (604e92d) with its usage limit, so
they have no Codex review. The firm, asked for recommendations and
consequences, answered "Agree" to both:
- **Keep credit-suite's SEPARATE_PRODUCTS exemption** for threshold-engine,
  which keeps its own copy of keybank_style.py so it lifts out whole. The
  copy does not follow credit-suite's styling; a change there is copied by
  hand.
- **Merge without that review**, CI 18 of 18 green on 604e92d and the branch
  containing main. This skips the merge rule's Codex step, by the firm's
  decision. #426 merged as a26a20a. **Open:** run Codex on main when its
  limit resets, and fix what it finds in a new PR.

## 13 October 2026, Codex on #426 after the merge

Its quota back, Codex reviewed 604e92d (asked for on the merged #426). Two
P2, both real:
- **The Assess dials multiplied a setting that was text** and showed
  `#VALUE!`, while the Thresholds tab refused it. Codex named the low step;
  the half-width and z did the same. A dial row is now blank when a setting
  it uses is not a number, and its last column says "refused: a setting is
  not a number". Opened in Excel 16 with text in each of the three: no
  error on Assess, 11 rows refused (the 4 that put their own value in place
  of the text still compute), and the numbers return when it is restored.
- **The Backtest glossary entry** said the scored quarter is included and,
  one sentence on, "built from the quarters before it". Both now say up to
  and including the quarter scored.
Suite: 772 passed (18 min).

## 13 October 2026, the walkthrough, the card tie-out and the site kit

The bank: *"come on finish this out - walk it, tie it, etc. i want this done
until you need me."*

**The walkthrough** (`docs/walkthrough/`, one PDF). The expected answer for
every cell was written first by `expected.py` and committed (6f3505d) before
Excel was opened. `walk.ps1` then built the workbooks with the command a
person types, typed each step into Excel 16 through its automation
interface, and read every cell back from Excel. 30 steps, 407 cells, all as
expected in the final run. The card lines under the rehearsal settings equal
the 7 Oct record, 3.171 / 3.464 / 4.050 / 5.981 and 25 / 22 / 29 / 55 / 4.
The script first took the 6 Oct figures, which belong to the scale retired
that evening; it stopped on the mismatch before anything ran.

What it found, all fixed with a test each:
- **Assess drew wrong bands for mortgage, home equity and other consumer.**
  The chart's top and floor were MAX and MIN over a column holding #N/A for
  quarters before a product's data begins, so both were #N/A: Low and High
  vanished and the rest were drawn from zero. Every count was right. The
  tests charted cards only, whose data covers the whole calendar.
- **A credit score's chart started at zero**, the bands crowded into the top
  half. Excel starts an automatic axis at zero unless the data sits within
  about a sixth of its top; a measure not floored at zero now gets a fixed
  round minimum at build, under the floor and the left-out strip, and the
  strip stands on an invisible base so it no longer pulls the axis down.
- **The Chart tab's legend covered the cutoff lines' right-hand ends**; it
  sits below the plot.
- **WHAT-IT-DOES.md said 33 Glossary terms; there are 35.** The script's
  expected answer came from that document and Excel disagreed.
Four readings failed on the first run because of the runner (a formula that
returns a cell, and #N/A in a hidden column reading as blank text). Steps W3
and W14 gained readings of the chart's floor and top after the first run,
because every cell read was right while the pictures were wrong.

**The tie-out** (`docs/tie-out/cards-moderate-line-2026-10-13/`). Credit card,
3 Moderate from, rehearsal settings: 3.4641865 in Excel against 3.4646865
recomputed by hand from the Federal Reserve Board's own table (Charge-Off
Rates, All Banks, SA, last update 25 Aug 2026), with exact decimals and
nothing from the tool. DIFFERS by 0.0005, cause found: the repository's
`cards_nco_ttm.csv` holds each four-quarter mean to three decimals, and in 80
of 163 quarters the exact mean ends in 5 (43 saved up, 37 down). 2020Q2,
3.7575 saved as 3.757, is the median kept, so all four lines sit 0.0005 low.
No kept quarter and not the latest changes score. The file is left as it is.
FRED could not be reached from this machine for a second reading.

**The site kit.** `docs/ON-SITE-CHECKLIST.md` (and `.pdf`) and
`tools/bank_kit.py`: one zip with the code, the window, the public practice
files and the two add-ons as wheels (openpyxl, et-xmlfile). Dry-run on a
fresh Python with neither installed: unzipped with Windows' tar, installed
offline from the kit, every command run as written in Command Prompt, the
practice numbers and the rehearsal lines read in Excel, a made-up score file
taken through `template write`, `check` and a build. Found: the template's
message told the user to run `threshold-engine template check`, a command
that exists only once the package is installed; it now says `python -m
threshold_engine`.

**Lower-is-worse through the workbook** (NEXT-GOAL section 2): a mirrored
series is held to `scale()` and `score()` under each on-the-line rule, and
walked in Excel as W14.

**Handed back:** monthly series in the workbook. Recommended acceptable for
v1: every source v1 reads is quarterly, and every template asks for
quarter-end dates.

Suite: 778 passed (23 min).

## 13 October 2026, Assess becomes the one place to work

The bank, on the workbook with card's settings: *"i want it way easier to
fill out - i want to be able to "assess" something and easily select
quarters to leave out"*, *"also needs to be easier to understand this
stuff"*, and *"i dont want to flip back and forth - that makes no sense."*
Asked how leave-outs should work, it chose a list on Assess over dropdowns
on Settings or macro buttons (banks block macros).

- **The Settings tab is gone; its inputs are on Assess, under the chart.**
  *Periods left out* is a list of 12 rows: product, first and last quarter
  from dropdowns of the quarters in the data, and a reason, for any product
  and any number of periods. A Status says what a row is missing; a row in
  use but not whole refuses its product, in words. *Your settings* is a
  table, one row per product, the picked product's row highlighted: without
  macros one input cell cannot follow the product picker and still keep a
  value per product. Plain-English notes say what raising each setting does,
  and the evidence box speaks for the picked product.
- **The latest quarter's score sits beside the product picker**, so the
  Thresholds tab is not needed while working. The workbook opens on Assess.
- **A refused product keeps its colours.** The bank, of other consumer at z
  2.5 with the crisis left out: *"what happened to the colors"*. A refused
  product drew no bands and no counts, and the dials went blank too: the
  picture vanished when it was most needed. Bands and counts now draw while
  the four lines are numbers in order; only the Check says refused, and the
  chart shows why (nothing kept reaches High).
- **Scenarios, side by side.** The bank: *"a few different views in assess
  for charts that show what changes as you remove quarters or adjust the
  columns in settings."* A table and a chart of the lines as the bank has
  them against keeping every quarter (the same settings, nothing left out),
  and a stacked chart per setting of the quarters kept in each score at the
  dial's values.
- Every Assess row number comes from `assess_layout()`, used by the builder,
  the tests and the walkthrough.

**Found on the way, fixed:** the highlight drew white (a conditional
format's fill is read from its background colour); merged Reason cells made
Excel refuse to clear a row ("We can't do that to a merged cell"), so no
input row is merged.

**The walkthrough on the new layout:** 30 steps, 433 cells, all as expected
in Excel 16. Its expected answers keep naming the old Settings cells and are
moved to their Assess places, as the tests do.

**Corrected, from the independent final check of 57f65ae** (an agent that
had not seen the work; every number it checked held, against Excel, its own
recomputation and the Federal Reserve page): this log, WHAT-IT-DOES and the
walkthrough said every expected answer was written before the run. 355 of
407 were (6f3505d); W14a/W14b and the W3 chart readings were added after the
first run. Also wrong: the window has 61 tests, and three open a real
window, not one; and the glossary-heading test exempts the plain headings,
now Product, From, To, Reason. All three are corrected where they were made.
Its own full test run overlapped this session's edits in the same checkout,
so it proves nothing about 57f65ae; #432's CI does.

**Codex on #432:** the checklist allowed nine quarters, but its build
command needs min-history + horizon = 13. Checked both ways and fixed on
#432: a nine-quarter file builds with `--min-history 5`.

Suite: 783 passed (28 min).

## 13 October 2026, the redesign, the readability pass and a docket

- **Redesign** from the Claude Design hand-off (docs/design/): Assess is
  one tab with the list of periods left out, your settings, scenarios and
  the chart; reference tabs restyled; a **Sources** tab that prints what
  each file says about itself and marks a missing key "Not stated in the
  file", never filling it in.
- **Readability pass** for a reader who did not build it: "product"
  became "series", the 1-5 result a "rating", plain Check and status
  wording, number formats that fit the measure. Two wrong headings fixed
  (Backtest's "quarters" over rating columns; Sources asking a score for
  a numerator). The backtest note had dropped "and including it"; restored.
- **Suite:** 788 passed, 9 failed of 797 on the first run, all nine tests
  expecting the old tab order or wording; fixed, the nine rerun green.
  Walkthrough in Excel: 433 of 433.
- **The firm turned the tool purpose-built** (13 Oct): industry, peers and
  KeyBank's filed figures; charge-offs and delinquency; generic pieces
  removed. Mortgage stays first-lien only ("we have hardly any junior
  liens"). Other consumer shown two ways side by side: blended, where
  every source meets, and split on KeyBank's own data. Comparability
  report: 30 of 30 fields matched to KeyBank's 30 June 2026 Call Report.
- **Docket** published with seven open decisions (other consumer balance,
  FDIC industry series, the seven gaps, one internal import, auto scope,
  total vs peer median, merge order).
- **Next** (silence approves only this): merge #432, #434 and this branch in
  order, then start the purpose-built data layer with whatever the docket
  approves.

### The firm's answers to the docket (13 Oct 2026)

| Decision | Answer | Their words |
|---|---|---|
| Other consumer balance = 6.b + 6.d | Yes, fix it | "fix it but what can we get from the LOC info then - at least balances compared to PLs or something? commitments?" |
| FDIC for every industry series | Yes, FDIC for all | Fed kept as a cross-check |
| The seven comparability gaps | Yes, all seven | "this has to be well-documented and tied out" |
| One import for internal data | Yes, one import | "i need this to be able to accept like-data - so internal data i will give the tool in a form it wants. so let's discuss the structure of what we have i cannot give you real numbers" |
| Auto | Set thresholds | "we have auto in the bank it's just direct" |
| Industry figure | Both: total and peer median | |
| Merge order | Merge as is, purpose-built on top | |

Found while reading them back, from KeyBank's 30 June 2026 filing:
- Lines of credit: public data gives the balance only (RC-C 6.b, about
  268,825). Unused commitments are filed for home equity lines (RC-L 1.a,
  7,581,816) and credit cards (1.b, 5,750,823) but not for other consumer
  lines, which fall into "all other" with commercial (1.e). So the public
  LOC view is balance and its share against installment (6.d), not usage.
- Auto: the filing's auto loans (RC-C 6.c) are 62,212 ($000). If KeyBank's
  direct auto book is larger than that, part of it is filed elsewhere, and
  that goes into the "which entity / which line" check.

### The goal, in the firm's words (13 Oct 2026)

"i still want the first part to exist. so i want to get an industry
perspective, competitive perspective, and internal. all of this to somehow
synthesize reasonable thresholds." Also: internal metrics "may exclude
certain things because they were not credit related", so the internal-to-
filed check is a reconciliation (filed, less named exclusions, against
internal; only the unexplained remainder flagged against a tolerance the
firm sets), not an equality. How the three perspectives combine is open.

### The comparability tie-out, and the firm's answers (14 Oct 2026)

A separate session tied out the seven gaps: 147 figures against documents
the firm does not control, 131 TIED, 13 DIFFERS, 3 COULD NOT
(docs/tie-out/comparability-2026-10/ on its own branch). It found a defect in
the tool: the industry series counts an absorbed affiliate's year-to-date
charge-offs twice in the merger quarter (six card quarters, $74m to $4.8bn;
the industry card rate up to 0.71 pts high for four quarters). The firm's
answers:

- **A. Card industry series and the 2010Q1 securitization break:** "Label".
  Keep 2006-2010Q3, marked "excludes securitized cards".
- **B. Home equity:** internal lines and loans as separate segments. Lines
  check against RC-C 1.c.(1); loans plus mortgage against 1.c.(2)(a) +
  (b). Peer comparison stays first-lien. The firm: "We have some second
  liens but mostly first"; "Loans were just discontinued". Internal figures
  to look for at 30 Jun 2026: lines about $2,930m, loans about $2,478m,
  second-lien loans at most $276m (all junior liens at the bank). The
  $2,478m is inferred by elimination, not published.
- **C. Acquisition leave-out:** 5% ("good on the merger thing"): leave out
  the four quarters after any quarter whose recorded acquisitions together
  add 5% or more to a product's book. A required setting; 5% is the firm's.
- To build: the merger double-count fix (tested against the FDIC's QBP
  totals), the peer median, cross-bank delinquency on 90+ and 30+ including
  nonaccrual only, mortgage compared on nonaccrual and charge-offs (not 90+
  accruing, because of rebooked GNMA), a run-off flag for shrinking books,
  and the import's two named exclusions (education loans in discontinued
  operations; residential loans held for sale).

## 13 October 2026, Codex on #432's fix

Two P2, both real:
- **The fixed axis minimum held only the starting settings.** A measure not
  floored at zero gets a fixed minimum at build (Excel starts an automatic
  axis at zero), and an axis cannot follow a cell, so raising Moderate-Low's
  step later could push score 2's line off the bottom. The minimum now sits
  under every line the dials offer (width to 1, step to 2, z from 2 to 3.5)
  as well as the starting ones. A setting beyond the dials' range can still
  run off it; the Check and the numbers are unaffected. Test: a noisy series
  whose step-2 line falls below every value it took; it fails on the old code.
- **compare.py zipped expected and observed readings**, so a stale
  observed.json from before a step gained readings passed them silently. A
  missing or misplaced reading is now a difference.

## 13 October 2026, Codex on e703a86

Three P2, all real:
- **The axis floor could not follow leave-outs.** Leaving out a calm stretch
  widens the spread and can push a line below the fixed minimum. No fixed
  axis can follow every edit, and one loose enough to try would flatten the
  chart, so the cell over the chart now says, in red, when a line or the
  left-out strip falls below the axis ("the numbers are right, the picture is
  cut off"). Checked in Excel 16 on a noisy series at step 6.
- **compare.py counted a step that never ran as one failure**; it now counts
  every reading in it, so the headline cannot overstate what Excel checked.
- **The walkthrough's build command wrote the workbook where the runner does
  not look**; it now writes to docs/walkthrough/out/.

## 14 October 2026, mergers: counted once, and the 5% rule

The comparability tie-out's gap 5, built.

- **The double count.** When a bank absorbs another under the same parent,
  the Call Report has the survivor report the combined year to date, so
  year-to-date differencing counted the absorbed bank's earlier quarters
  twice. `books.repeated_ytd` reads, from the filings, the absorbed bank's
  last year-to-date wherever both banks filed the quarter before with the
  same parent (RSSDHCR, now pulled every quarter), and `without_repeats`
  takes it off the survivor for the rest of that year. Every series reads
  the corrected data: the banks, the pack, the industry.
- **Checked against the FDIC's own totals** (the Quarterly Banking Profile
  figures the tie-out quoted), industry card charge-offs, $m, on a fresh
  pull of every filer 2006Q1 to 2026Q2:

  | Quarter | Before | After | QBP | After less QBP |
  |---|---|---|---|---|
  | 2006Q4 | 6,622.1 | 3,664.0 | 3,664.0 | 0.0 |
  | 2010Q2 | 20,508.3 | 20,434.1 | 20,434.1 | 0.0 |
  | 2011Q3 | 15,584.4 | 10,738.1 | 10,738.1 | 0.0 |
  | 2014Q4 | 9,133.8 | 6,478.8 | 6,479.6 | -0.8 |
  | 2019Q2 | 11,458.7 | 10,603.1 | 10,603.1 | 0.0 |
  | 2022Q4 | 10,380.3 | 7,679.6 | 7,688.2 | -8.6 |

  "Before" reproduces the tie-out's figures exactly. The 2022Q4 gap is the
  tie-out's own: Capital One (USA)'s last year-to-date was 2,700.6, the
  survivor repeated 2,692.0. The fix also moved 35 other card quarters,
  2007Q3 by 184.0 and 2009Q3-Q4 by 175.3 the largest; those were **not**
  checked against the QBP, whose figures for them were not in hand.
- **The acquisition share, 5% (the firm's).** A required setting,
  `--acquisition-share`: a quarter whose recorded acquisitions, added
  together, brought in at least that share of a product's book leaves out
  the bank's four TTM windows holding it, and blanks delinquency's
  four-quarter average as the jump does. On the roster, 2006-2026: 152
  acquisition quarters at 5%, 84 of which the 25% jump also caught, 68 only
  this rule (the tie-out counted 60 on a stricter test of material).
- **Found while building:** FDIC history leaves CERT blank on a failure's
  row; the absorbed bank is OUT_CERT on every row, so that is read.
- `peers pull --mergers` now also writes `absorptions.json` (who took in
  whom); `peers build` requires `--absorptions` and `--acquisition-share`.
  A cache pulled before today has no RSSDHCR: build refuses, naming the
  banks, only where an absorption needs it. Pull again with refresh.
- **Then, same day:** a **pack median** series beside the pack composite
  (charge-offs and every delinquency measure and basis): the middle bank,
  each counted once whatever its size, as the firm chose "both" over a total
  alone. Every delinquency file now carries the tie-out's comparability
  findings in its notes (nonaccrual is partly policy; mortgage past-due
  includes rebooked GNMA), so the Sources tab says it. KeyBank's own series
  state the book's path over nine quarters (balance at both ends, quarters
  it fell): facts, no line drawn for "run-off". Full suite before these:
  825 passed; the peers CLI and combination tests after: 142 passed.

## 14 October 2026, the purpose-built data layer: other consumer, FDIC industry, QBP, synthesis

The firm, 14 Oct: "Build until you cannot." The approved items, in order.

- **Other consumer divides by RC-C 6.b + 6.d** (approved 13 Oct, "Yes, fix
  it"). Its charge-offs (RI-B 5.c) and past-due lines (RC-N 5.c) include
  other revolving credit plans; the balance now does too (LNCONOTH +
  LNCONRP; KeyBank 30 Jun 2026: 4,200,208 + 268,825 = 4,469,033, confirmed
  live on the FDIC API). The FDIC data has no 6.b before 2001Q1 (industry sum
  0 in 2000Q4, $24.7bn in 2001Q1); every other consumer series says so. The
  industry other consumer net rate is 0.246 points lower on average than the
  earlier as-filed file, 2006-2026 (this fix and the merger fixes together). The QBP's "Other Loans to Individuals" (6.b + 6.c + 6.d)
  equals ours in 80 of 82 quarters.
- **The industry series are the FDIC's** (approved 13 Oct, "FDIC for all").
  `data/industry/`: 62 files, every filer 2006-2026, all five products,
  charge-offs and delinquency, from a fresh pull of 14 Oct. README points
  the workbook at them. Card quarters before 2010 are labelled as excluding
  securitized cards (the firm's "Label"). `compare` puts two series side by
  side by calendar quarter: the FDIC card series against the Fed's, 79
  quarters, mean difference 0.000 points, largest 0.229 (2011Q3).
- **Every industry quarter against the FDIC's own totals** (the QBP time
  series, 2Q 2026). A separate agent checked card; it found two defects
  beyond the merger double count:
  - A bank bought by a new holding company can restart its year to date
    (push-down accounting); differencing read a negative flow. National
    City under PNC, 2008Q4: -$94.6m. Now `books.restarted`: a year-to-date
    that falls while the parent changes is the quarter's flow. Card: 75 of
    82 quarters within $0.05m (70 with the absorption fix alone, 52 before
    either); total gap $14,683m -> $151m -> $14m. The rule overshoots in two
    small cases (2011Q2 +$0.7m, 2015Q3 +$0.1m); 2022Q4 -$8.7m and 2018Q4
    +$4.4m remain (one unexplained, one an absorption across parents).
  - The FDIC record names Capital One N.A. as absorbing 34191 in 2007Q3; the
    book went to its sister, Capital One Bank (USA). The industry total is
    right; no drawn number moves (those windows are already left out).
  - All products (`check_all.py`): card, auto and other consumer tie;
    home equity and mortgage tie outside 2008Q3-Q4 (balances 0.4-0.65%
    larger, cause not identified) and small pre-2012 mortgage recovery
    differences (up to 4.3% of a quarter's net charge-offs). Recorded in
    `docs/tie-out/industry-qbp-2026-10-14/`.
- **The synthesis** (`synthesize`, `synthesis.py`): for one product and
  measure, internal, industry and peers each propose the four lines; the
  firm names which source leads each line (`--leads`, no default). Industry
  is translated by the median internal/industry ratio (or not, the firm's
  choice); peers are the stated percentiles of each peer's median, carried
  by internal/filed. A calm history places lines 2-4 and refuses line 5,
  saying so, which is the gap the industry fills. Run on public card data
  with KeyBank's filed series standing in for internal (mechanics only, not
  a recommendation): internal lines 2.657 / 3.016 / 3.735 and no High;
  industry's High, translated, 5.625. `peers build` now writes each peer's
  own series to `banks/` for it.
- **Built in parallel:** the internal import, by a separate agent on its
  own branch (`threshold-engine-internal-import`), to INTERNAL-IMPORT.md.
- **The FDIC industry files in the workbook** (README's command, all five
  products, opened in Excel 16): every tab recalculates with no formula
  error. Under the card settings applied to every product, card, home
  equity and other consumer rate (3, 1, 4 at 2026Q2); mortgage is refused
  ("Moderate-Low would begin at or below zero") and auto too ("High would
  begin beyond the worst quarter kept": auto's own line starts in 2011, so
  its history holds no crisis). Each refusal says what would clear it; the
  settings per product are the firm's.

## 14 October 2026, the internal import, built

`docs/INTERNAL-IMPORT.md` was a draft with nothing built. It is now
`internal.py` and the `internal` command: `template`, `check`, `series`,
`pull` and `reconcile`. Made-up figures only in the repository; nothing has
been run on KeyBank's data.

- **The file** is as agreed: one row per quarter, product and segment, any
  two of gross, net and recoveries (the third worked out; three that
  disagree are refused, compared exactly as written, so no tolerance is
  assumed), past due cumulative and not above the balance, one
  `# segment-NAME:` description per segment the rows use. Auto is a
  product of its own (the firm: "we have auto in the bank it's just
  direct"). Every problem is listed at once, each with its line.
- **Decided here, for the firm to overrule:**
  - Exclusions are a separate file, not a section: different columns,
    public sources, their own `--exclusions`.
  - Each exclusion names its `segment` and its `measure` (balance, gross or
    net charge-offs), two columns beyond the agreed four: home equity's
    two segments meet different public lines, and a balance left out says
    nothing about its charge-offs.
  - Charge-offs are reconciled for every comparison, not only card and
    other consumer: each RI-B line used covers the same loans as its RC-C
    balance line (1.c.(1), 1.c.(2)(a) and (b), 5.a, 5.b, 5.c).
  - The remainder's share is of the internal figure. An internal figure of
    0 is within only when the remainder is 0.
  - A blank filed field is "not filed", so that row is not measured, never
    counted as 0. Before 2011Q1 auto (6.c) was not filed separately, so
    other consumer and auto are not measured before then.
  - Further columns hold numbers or nothing; a column named like an
    identifier is refused. The file holds totals by segment.
  - `reconcile` takes `--roster` (the filer is the roster's `self` bank),
    and `internal pull` exists because a peers cache has no junior-lien
    fields (LNRERSF2, DRRERSF2, CRRERSF2): reconcile reads a cache of its
    own and says, row by row, when a field was not pulled.
- **Checked against a real cache:** `internal pull` fetched 2026Q1-Q2 from
  the live FDIC API with every field it names. A stand-in built from
  KeyBank's own public figures (scratch only, never committed) reconciled
  to a remainder of 0 on all 36 rows at tolerance 0. The 2026Q2 lines the
  doc quotes hold: LNRELOC 2,929,570, LNRERSF2 276,020; other consumer
  268,825 + 62,212 + 4,200,208 = 4,531,245.
- **Handled the same day, after the merge:** where KeyBank absorbed a bank
  under the same parent, its filing repeats that bank's year to date.
  Reconcile now takes it off as the public series do (`internal pull`
  writes `absorptions.json`; `books.repeated_ytd_fields`), and reads a year
  to date that restarted under a new parent as the quarter's own. The one in
  range: First Niagara (16004) into KeyBank, 2016Q4, which the industry
  build lists among the repeats it took off. No run-off note on the
  internal series yet.
- `tests/test_internal.py`: 86 passed. Full suite: 914 passed, 0 failed
  (49 minutes).

## 14 October 2026, an independent review of the day's code (Codex still over its limit)

Codex has been over its usage limit since #432. In its place, four review
agents, one angle each (arithmetic, the no-default rule, input edges, tests
that would not catch a bug), each followed by an agent told to refute what
it found by running the code. 30 raised, 30 reproduced. Fixed:

- **The absorption fix kept subtracting after a restart.** A bank that
  absorbed an affiliate and was then sold, the same year, read a negative
  flow (-15 for 25). `without_repeats` now stops at the first quarter the
  survivor's year to date restarted, and takes nothing off when it
  restarted in the merger quarter itself.
- **A restart was decided field by field.** Push-down accounting restarts
  every year to date together; one filing could be read as restarted for
  charge-offs and differenced for recoveries. Now one decision per filing
  (parent changed, and any year-to-date field fell), for the public series
  and internal reconcile alike. With both fixes the card industry series
  ties to the QBP in 76 of 82 quarters, total gap $5.6m (from $14.3m);
  2022Q4's -$8.7m, unexplained this morning, closed.
- **`peers build` now requires each filer's parent (RSSDHCR)** in the cache:
  without it the restart rule was off without a word. A cache pulled
  before today is refused and says to pull again with refresh. The three
  peers fixtures gained RSSDHCR from the public API (blank only for Zions
  from 2018Q3, when its holding company merged into the bank).
- **Synthesis:** a line 2 at or below zero is refused under the floor
  (scale.py checks it after High, so it never got to); every series is
  checked as the workbook checks it (real dates, no gap, no repeat); peers
  without `--filed`, and a peer named twice, are refused by name.
  `compare` refuses a date that is not a calendar date.
- **Internal import:** `internal pull` records absorptions back to the
  earliest quarter in its cache, so a later short pull drops none; two
  segments whose series files would share a name are refused.
- **Notes:** the composite's four-quarter average names each bank's own
  reason (the jump or the acquisition share), and its rule line names the
  share; other consumer delinquency says no rate is written before 2001Q1
  and names LNCONRP as the line not filed. Per-peer files for a bank no
  longer drawn are removed with the build's other files.
- **Tests that would not have caught a bug** (pack median, per-peer
  values, the build's absorption and acquisition wiring, the composite's
  acquisition left-outs, synthesis lower-is-worse, guards in
  `repeated_ytd_fields` and `acquired_quarters`): 14 tests by a separate
  agent, each proved by applying the finding's mutation to a scratch copy
  and watching that test fail; none needed the code changed. Its
  window-restriction peer had a gap, which synthesis now refuses; made
  unbroken, and the mutation still fails it.
- **Then:** every internal series states its book's path (the four-quarter
  average balance over the last nine windows, and in how many it fell), as
  KeyBank's public series do: home equity loans were "just discontinued", so
  a rate can rise as the book shrinks. Facts only; no run-off line drawn.

## 14 October 2026, the synthesis in the workbook

The firm agreed the synthesis goes on Assess: *where each colour starts*.
Built on branch `threshold-engine-synthesis-tab` (from `e401c5be`), in
`synthesis_tab.py`; `synthesis.py` stays the arithmetic and the reference.

- **What it is.** `workbook --synthesis "LABEL=industry:FILE;filed:FILE;
  peers:FOLDER-OR-PATTERN"` adds a red **Synthesis** tab beside Thresholds:
  per series, the four lines from internal, industry and peers side by side,
  which one each line is taken from, the chosen lines, the latest quarter
  rated on them, the competitive check and a Check; its series on
  **SynthesisData**. Every number is a live formula on Your settings on
  Assess. On Assess, under What each setting does, *Where each colour starts*
  shows the series in B5 with a link to the tab. Without a synthesis flag the
  command and the workbook are unchanged (the existing tests pass as they
  were).
- **Choices, none defaulted.** Per series `--translation`, `--leads`, and
  `--peer-percentiles` when it has peers; each starts its yellow cell. Stated
  per series, not one set for all: a lead chosen for cards, whose industry
  history holds 2008, was not chosen for a series whose does not. A series
  given `--synthesis` without one of them, or one of them without
  `--synthesis`, is refused by name.
- **Decided while building, to be confirmed.** (1) The internal lines are
  Thresholds' lines, so periods left out on Assess move them; the
  translations and the peer window use every quarter the internal series
  holds, as `synthesis.py` does. (2) The industry, filed and peer series are
  smoothed as the measure says, like the internal one. (3) Each peer is named
  by its file (`credit-card_bank-of-america_net`); nothing is read out of the
  file to name it.
- **Refusals in the Check, in synthesis.py's words:** a line taken from a
  view without it, lines out of order (the pair and their values), peers
  without KeyBank's filed series, percentiles that are not four numbers 0-100
  or do not rise, a lead or translation typed outside its list.
- **Proof.** `tests/test_workbook_synthesis.py`: recalculated with `formulas`,
  every candidate, chosen line, rating and Check equal to
  `synthesis.synthesize` on the same inputs (all internal but High from the
  industry; peers leading lines; translation none; percentiles and Your
  settings changed in the workbook; a period left out; lower is worse;
  smoothing; a latest value exactly on a chosen line under worse and better;
  each refusal), plus the command's refusals. 42 tests. Nine hand-made
  faults in `synthesis_tab.py` (percentile not flipped when lower is worse,
  peer and filed medians over every quarter, order check blind to direction,
  a line-5 refusal dropping lines 2-4, translation none ignored, percentiles
  allowed to tie, on-the-line ignored, synthesis series left unsmoothed):
  all nine turn a test red. The on-the-line fault survived the first round;
  the test for a value exactly on a line was added for it. Full suite on
  this branch: 889 passed, none failed or skipped (53 min).
- **Opened in Excel 16** on public files: KeyBank's filed card series
  standing in for internal (and as filed, so peers are carried by exactly
  1.000), the FDIC industry card series, and the 11 peers `peers build` wrote
  to `banks/`; leads internal x3 and High from industry, median ratio,
  percentiles 20/40/75/95 (stand-in choices for the mechanics, not a
  recommendation). Excel's numbers equal `synthesize`'s: internal 2.657 /
  3.016 / 3.735 and no High; industry 2.749 / 3.116 / 3.850 / 5.625 (x 0.922
  over 34 quarters); peers 3.464 / 3.795 / 3.985 / 4.921; 2026Q2 rated 4;
  KeyBank's filed median 3.376%, worse than 2 of 11 peers. No #VALUE!,
  #REF!, #DIV/0!, #NUM! or #NAME? on any tab; 67 #N/A on Assess, all in its
  hidden chart helpers (the NA() that keeps a chart from drawing a point),
  none visible. Changing line 4 to peers and High's z to 2.0 moved the chosen
  lines and the rating (4 to 3); taking High from internal showed the
  refusal on the tab and on Assess.
- **Not done:** the window (`Thresholds.pyw`) does not offer the synthesis
  inputs yet; the command line does.
- **Merged after the review, and brought into line with it:** the tab's
  internal and industry candidates now refuse a line 2 at or below zero
  under the floor when High cannot be drawn (as `synthesis.py` does since
  the review), and peers without KeyBank's filed series are refused before
  anything is drawn, in `synthesize`'s words. Two tests hold each to
  `synthesize` on the same inputs.

## 14 October 2026, the merges, and one workbook for the meeting

**Merges.** Codex stayed over its usage limit. Asked whether the independent
agent review was enough to merge #432, #434 and #438 (the PocketBook rule of
3 Oct), the firm: *"Yes"*. Merged in the agreed order. Before #432 merged, its
walkthrough page was fixed: the expected build line had a carriage return
where `\r` was meant (`outehearsal.xlsx`), and the file had become CRLF.
Merging #432 into #434 and #438 conflicted in LOG.md, the tests and the
checklist PDF (kept both sides; PDF re-rendered); in #438 also in
`workbook.py`, where Assess is now built by `assess_tab.py`. #432's warning
when a line falls below the fixed axis moved to B7:L7, the row over the
chart. Suites on the merged trees: #432's workbook, template and CLI tests
186 passed; #434 785 passed; #438 1,012 passed.

**The meeting workbook.** The firm: *"I have a meeting tomorrow send me a ran
workbook to see if I want to use it"*, *"All data that we have so far"*, then
*"i did not want a bunch of workbooks i wanted one workbook with a lot of
good info"*. Sent one: `Consumer credit thresholds.xlsx`, 95 series (five
products by seven measures: net and gross charge-offs, trailing twelve
months; 30-89, 90+ accruing, nonaccrual, 30+ and 90+ including nonaccrual,
quarter-end), each from the industry (every filer), the 15-peer pack
composite and KeyBank; with the `peers build` tabs copied in as "Peers ...".
Card's settings throughout (0.5 / 1.0 / 2.5, worse, 41 quarters), stated as
card's, not a decision for the rest. 42 of 95 refused, card in none.
KeyBank's charge-offs are not in it: 34 quarters since the First Niagara
break, 45 needed. Calculated in Excel 16, 0 visible errors on 20 tabs; the
60 series also built as separate workbooks match them exactly. The copied
peers tabs left an external link to `peers.xlsx` that nothing used; broken,
and all 698,135 cells compared equal before and after.

- **Found while building it:** a workbook of 36 or more series failed (the
  Chart tab's title ran into its helpers at column AN). Fixed; test added.
- **Got wrong, corrected:** a first note said 28 of 60 refused in the
  separate workbooks; it was 27 (KeyBank 14, not 15). An Excel process was
  force-closed during the run; any workbook the firm had open in Excel then
  closed unsaved.
## 14 October 2026, table slicers without Excel

The bank blocks macros, so a row of a table is picked with slicer buttons,
and openpyxl cannot write slicers. `slicers.add_table_slicers(path, sheet,
table, slicers)` adds them to the finished .xlsx by editing the package, in
the parts and places Excel 16 itself used when it added the same three
slicers to the Decide table over COM. Not yet wired into the build.

- A table slicer stores no selection. Excel reads it from the table's
  autoFilter on open and does not re-filter, so the autoFilter is written to
  the selection and the rows it hides are written hidden, as Excel wrote them.
- It refuses rather than guess: a value not in the column, a column that is
  not text (a button shows displayed text, unknowable here for a number), a
  table already filtered, a sheet that already has slicers.
- `tools/check_slicers_in_excel.ps1` opens the result as a user would
  (excel.exe /x, watching for any dialog), then over COM counts every cache,
  slicer, shape and selection, clicks a different button, checks the rows
  shown against the cells, saves, and reopens. Passed on a sample with `&`,
  `<`, quotes and `+` in the names (`tools/slicer_sample.py`), and on
  core-decide.xlsx.
- Found on the negative controls: Excel repairs in two ways. A malformed part
  prompts ("We found a problem...") interactively, and over COM only makes
  Open fail. A well-formed but wrong part (a cache naming a column that is not
  there) is dropped silently, with no prompt, no repair log and no
  "[Repaired]", interactively and over COM. Only counting what survived
  catches the second.
- On Decide, the Measure slicer has seven buttons and rows 3-11 at their
  current height show five, so the selected one can be below the fold.
  Excel's own run set those rows to 25pt first.

## 14 October 2026, tie-out: KeyBank card nonaccrual, 2026Q2, in the book workbook

`docs/tie-out/keybank-card-nonaccrual-2026-10-14/`, the deliverable
`TIE-OUT-keybank-card-nonaccrual-2026-10-14.pdf` (checked and rendered by
canon). The 0.69% on Summary (G11) and in Decide's headline, read in Excel 16
from a `book` build of d1e353a1, against KeyBank, N.A.'s filed Call Report for
30 June 2026, fetched again tonight. **TIED**: Excel holds 0.6908132947833397,
exactly 100 x RC-N 5.a column C (6,401) / RC-C Part I 6.a column A (926,589),
read off the page and the XBRL.

- **Found:** the FDIC's dictionary names no Call Report line for NACRCD or
  LNCRCD. Against the FFIEC bulk file for 2026Q2 they equal B577 and B538 for
  all 4,295 banks in both, 0 differ; neither is a sum.
- **Found:** Thresholds!J (Latest value) is a value Python writes, not a
  formula on the Data tab, so a corrected quarter pasted into Data would move
  the lines but not Latest, the rating, Summary or Decide.
- **Found:** Thresholds column A is clipped in Excel ("Credit card - Non" on
  every source of a measure), and Summary H7:H8 read "Not in this workbool".
- **Found:** Decide's "KeyBank is 0.68 points higher than Peer group" sits
  beside a measure on which 10 of 16 roster banks file zero card nonaccrual;
  the warning is only on the Sources tab.
- `scripts/read_workbook.ps1 -Workbook X` reads any build the same way (the
  series is a parameter), so the firm's own `book books/consumer-public.json`
  can be tied out next; that build was not run here.
- No code changed.

## 14-15 October 2026, the book: one command builds the workbook

The firm, on the meeting workbook assembled by hand that evening: *"assess one
thing at a time, save decisions, not a guide"*, *"it cannot be a huge list"*,
then *"i want you to make it work so i can generate this workbook at work with
the script, it should be debugged and walked through and tied out. you have
all night basically"*.

- **`book BOOK.json OUT.xlsx`** (book.py): one file says everything the
  workbook is built from; every key required; with a `peers` section the
  peers build runs into the same workbook. `books/consumer-public.json`: 105
  series. `books/README.md`: the steps at work.
- **Decide** (decide_tab.py): three slicers pick one series; its yellow row is
  the decision (Accept these lines / Reject, the four settings, a period left
  out, a note), kept in the file by saving. Assess's typed cells read it;
  Assess and Chart are hidden in a book. **Summary** (summary_tab.py).
  Slicers are written into the file (slicers.py, an agent; no Excel needed).
  Peer tabs inside the same file (into/names, an agent).
- Asked for while it was built, and done: **life to date** ("we need to allow
  life to date": a series shorter than the backtest needs keeps its lines;
  KeyBank's charge-offs are back, 34 and 35 quarters, auto 15); **the axis
  fits** (named ranges from the first quarter drawn; "Chart shows" last 48 by
  default, after "maybe the last 48 quarters"); **overlays** ("how do we
  overlay": On chart per source).
- **Proof.** Walkthrough in Excel 16 on the full build (peers build inside it,
  12 min 42 s from the cache): 320 of 320 reads as expected, including save,
  close and reopen (`docs/walkthrough-book/`, PDF). No repair as a user opens
  it (tools/check_slicers_in_excel.ps1, RESULT: PASS). Tie-out of KeyBank
  card nonaccrual 2026Q2, 0.6908%: TIED to the filed Call Report, page and
  XBRL, difference 0 (`docs/tie-out/keybank-card-nonaccrual-2026-10-14/`).
- **Answered:** KeyBank's auto series is RC-C 6.c, which by its instructions
  includes direct and indirect; KeyBank sold its indirect book in 2021Q3 and
  6.c is $62.2m at 30 Jun 2026.
- **Open:** the peer analysis as one dashboard tab with filters ("it is
  annoying to flip between stuff", "peers balances do not follow peer pack
  stuff", "does this have to go to design again") is being built.
  Thresholds' latest value is written by the build, not live on Data (the
  tie-out). 10 of the 16 roster banks file zero card nonaccrual, so KeyBank
  against the peer group on that measure says little (the tie-out).
- **Got wrong, corrected:** test mistakes (a rating read as 3.0, a row
  misplaced); the chart's range ignored the window at first, then its zones
  vanished when an overlay was off (#N/A in MAX), both seen in Excel's
  picture and fixed; the peer-tabs agent's tests were written against main's
  older peers code and failed on this branch (16 and 5 errors), handed to the
  dashboard work to fix.
## 14 October 2026, the peers on one tab: a dashboard

The firm, looking at the peer tabs in the built workbook: *"it is annoying to
flip between stuff for peer analysis - can't they all exist on one tab with
filters like a dashboard at the top?"*, *"peers balances do not follow peer
pack stuff so i cant turn off like JPM"*, *"same with peers lagged and
normalized"*, and *"these views look crazy bad formatting-wise, does this have
to go to design again"*. Redesigned, not patched.

**What the bank now sees.** One red tab, **Peers**. At the top, yellow cells:
product, charge-off rate (net or gross), Peer A and Peer B, Chart shows (all,
last 80, 48 (the start, the firm's own) or 20 quarters), the delinquency
measure and basis, a Yes/No under each of the fifteen peers, and the ranking
settings. Under them: headline numbers (KeyBank latest, pack latest, KeyBank's
rank among the banks switched on, industry latest; the same for delinquency),
then the views in a two-column grid: charge-offs (band, composite, KeyBank,
Peer A and B, and now the industry), delinquency, book size, lagged rates,
how far each rate moved, against the industry, and every bank's row. 16
columns, 1,100 pixels wide at 100%. The old Pack, Peers, Delinquency,
Balances, Lagged, Normalisation and Mix tabs are gone; **Workings** (hidden)
holds the live helpers; Glossary, Data, DelinquencyData and Run stay.

**Why Balances, Lagged and Normalisation ignored JPMorgan switched off.** They
were values written once by Python: Balances listed every bank, Lagged's
"All peers, total" and Normalisation's "All-peer composite" were over every
peer whatever Include said, and none had a formula reading Include. Now:
the book-size view draws the band and median of the indexes of the banks
switched on; the lagged pack total is SUMIF over the banks switched on
(blank if any of them lacks a year, as before); the normalised pack
composite is worked from the live composite. Mix has no pack in it (KeyBank
against the industry); it follows the product and Peer A and B.

**Decisions taken here, each the firm's to overturn.**
- One product picker for every view. A delinquency product the charge-offs
  were not built for is listed too; the charge-off views then say so in
  words. Best and worst are ranked on that product's charge-offs.
- The book-size view's "pack" is the median of the indexes of the banks
  switched on (each bank once), with the 10th-90th and 25th-75th band: a
  percentile, as the rate band is, not a new aggregate.
- Normalisation follows the rate picker (net or gross); Lagged and Mix are
  net by definition and say so.
- A base quarter before the first TTM quarter is now refused, in words: the
  book index is drawn on the TTM quarters.
- Each bank's acquisition quarters moved to the Run tab (the bank table had
  First Citizens' nineteen wrapping the rows).

**Proof.**
- tests/test_peers_workbook.py (rewritten for the dashboard), recalculated
  with `formulas`: switching JPMorgan off moves the composite, band, best and
  worst, book-size band and median, lagged pack total, normalised pack
  composite and the headline numbers, each equal to the module over the
  other fourteen. 62 passed.
- tests/test_peers_dashboard.py (new): every view against the builder it
  replaced (tests/data/peers/peers_workbook_642ff55f.py, copied unchanged),
  with every bank on: net and gross charge-offs, best/worst and the ranking
  window, delinquency, the book index, lagged rates and the pack total,
  normalisation, the mix. And "Chart shows" at 20 changes only the window
  cells the named ranges read. 9 passed.
- tests/test_peers_into.py: **the standalone pin is retired** (it compared
  the .xlsx part for part with d1e353a1's; this change alters the standalone
  output on purpose, and the pin said to retire it then). It was also failing
  on this branch before this work (16 failed, 5 errors: written against
  older signatures). Now: the series CSVs `peers build` writes are byte for
  byte the old builder's run's (over 100 files, banks/ included); into a host
  with its own Data, Glossary and Run every peer cell recalculates to the
  standalone value; refusals and foreign_refs as before. 28 passed.
- Excel 16 over COM, the real cache with books/consumer-public.json's
  settings: 0 visible error cells before and after.
  Headline strip, card net, before -> after JPMorgan is switched off: KeyBank
  3.76 -> 3.76; pack 3.54 -> 3.81; KeyBank's rank 6 of 11 -> 5 of 10;
  industry 4.01 -> 4.01; delinquency (card, 30-89, quarter-end) KeyBank 0.92
  -> 0.92, pack 1.33 -> 1.48, rank 4 of 13 -> 3 of 12, banks with a rate 12
  -> 11. One value per view: lagged pack total 2025 4.97 -> 5.42; normalised
  pack ratio 1.14 -> 1.25; book-size pack median 104 -> 101; mix own factor
  2025 1.09 -> 1.09 (no pack in it); best in pack JPMorgan -> Bank of America.
  The charge-off chart draws 2014Q3 to 2026Q2, 48 quarters.
- `book`: the dashboard inside the thresholds workbook (PEER_TAB_NAMES now
  Peers, Peers workings, Peers glossary, Peers data, Peers delinquency data,
  Peers run): 17 tabs, Peers fifth, Peers workings hidden at the
  end; 0 visible error cells on 14 visible tabs before and after; the same
  reads as standalone, before and after; the notes name "the Peers data tab".

**Not done.** The full suite was not run (an hour); the peers, book and
launcher tests were. tests/test_launcher.py::test_too_little_history_for_the_
backtest_comes_back_from_the_real_build fails, and is not about the peers:
642ff55f ("life to date") made a short series keep its lines instead of
refusing, and the test still expects the refusal (it fails the same at
642ff55f, checked in a clean worktree).

## 15 October 2026, Claude Design's round 2, built by the tool

The firm sent Claude Design's hand-off (`docs/design/round-2/`) and answered
its questions: the internal extract is quarterly by product and measure, then,
before it was built, *"i will have more granular data ... sometimes we may also
want to see its components like other consumer is 4 different things ... balances
and stuff are definitely important too"*: the Internal tabs take the internal
import layout (segments, $ thousands) instead. Keep the lagged peer view; Excel
at work is Microsoft 365. Wording to canon's voice (1.23.0, PR #439, not yet
installed): the analyst register, American spelling.

- Built in four parts, each in its own worktree, then combined: Decide and
  Thresholds (Thresholds read by meaning through `decide_tab.TH_BOOK`);
  Summary and the reference tabs; Peers (peer glossary and run folded into
  Glossary and Run); Internal and Internal data (`internal_tab.py`, a book's
  required `internal` key).
- Voice pass over every visible string (1,557, 21,333 words): one tell,
  fixed; American spelling also in text a book hides.
- Proof: tests per part (Decide 23, slicers 19, book 11, peers 460, Summary
  and reference 250 + 115, Internal 19 + 103) and combined (87, then 30);
  `book` with the peers build inside, 7 min 57 s; walkthrough 328 of 328; no
  repair as a user opens it.
- Not run: the complete suite in one run. Not done: right-edge line labels on
  the Internal chart; slicer buttons sort A-Z (Excel offers no data order).

## 15 October 2026, one set of lines per product and measure

The firm, on Decide: *"we don't need to set thresholds on all 3, we need to
use all 3 to set appropriate thresholds. industry, competitor, and key
reported"*. Asked how, they picked "Pick per row": a yellow cell on each
product and measure naming the source whose history sets its lines, with what
each source's own history would give side by side, all three on one chart,
and each source rated on the lines picked.

- Decide: 35 rows (product × measure), two slicers, a required **Lines set
  from** in the column the source had. A row's settings apply to every
  source's own lines; its period left out to the source picked. The consumer
  book starts every row blank (`lines_from: {"part": "Source", "start":
  null}`): until a source is picked the row has no lines and no ratings, and
  its Check, Thresholds and Summary say Pick a source.
- Thresholds is one row per product and measure (`thresholds_tab.py`): the
  source, what the lines rest on, the four lines (blank while refused), every
  source's latest value and rating on them, the decision and the Check. The
  per-series table it reads is the old Thresholds, renamed **Lines by
  source**; `decide_tab.rename_tab` rewrites every reference to it.
- Proof: test_decide 31 of 31, test_book 16, test_internal_tab 19,
  test_slicers 19, test_workbook 71, each run alone. Walkthrough rewritten
  (`expected.py`) and run in Excel 16: **1,463 of 1,463** reads as expected
  (B1 to B10; three rows given a source; every series' own lines read on
  Lines by source); the build took 8 min 48 s. Slicer check: PASS, 0 dialogs
  opened as a user, 1 of 35 rows shown after a click, kept after save.
- Two harness fixes found on the way, both timing in Excel's automation, not
  the workbook: `check_slicers_in_excel.ps1` asks again while Excel is busy
  recalculating after a click (RPC_E_CALL_REJECTED on save, close, reopen);
  `walk.ps1` counts visible errors with Excel's own visible-cells set, since
  asking each cell whether its column is hidden counted a hidden #N/A as
  visible on one run in two (Decide!AZ65, then Internal!IU50; both in hidden
  helper columns, checked in Excel).

**Not done.** The complete suite in one run. The peers histories are being
changed on another branch (pro forma acquisitions); this branch was walked on
the peers code as it stood at d0aa99a0. The 32 rows not given a source in
the walk are read only as Pick a source.

## 15 October 2026, afternoon: what each peer's consumer book holds, tied out

The analyst, asking whether peers' other consumer rates say anything about
unsecured lending: *"I don't know how to prove out that these guys don't have
much student and stuff. Is there a way to do that"*, then *"Build it in and
tie it out"*.

- **Peer loan classes**, a new tab in the book (`peers/classes.py`,
  `peers/loan_classes_tab.py`, the book's required key `loan_classes`): for
  the 15 peers, KeyCorp and SoFi, each holding company's 10-Q for the quarter
  ended 30 June 2026: who holds student loans, unsecured or personal loans and
  lines, and secured non-auto lending; each consumer class as filed; and the
  filing's words behind every finding. `peers classes-pull` fetches the
  filings from SEC EDGAR into a cache (SEC requires a contact email in the
  User-Agent header: a required flag, never stored; the window asks for it).
- Amounts are never typed in `config/peer-loan-classes.json`: a class the
  filing tags names its XBRL members and the build reads the amount (18
  classes); a class printed but not tagged by class gives the figure as
  printed and where (15). What each class counts as is a judgment, stated per
  class with the filing's words. The file is written by
  `docs/tie-out/peer-loan-classes-2026q2/record/make_config.py` from three
  readers' records of the filings.
- **Tie-out** (`docs/tie-out/peer-loan-classes-2026q2/`): every class amount
  read out of the workbook in Excel against the 10-Q as filed, through a
  different file (the inline-XBRL document, fetched fresh) and a different
  parser: **33 of 33 TIED**. One figure traced end to end with the filed table
  photographed: Citizens' Education, $8,044m. Every quote checked against the
  filed text: 24 found word for word, 27 findings "not stated" (searches).
- What it found: student loans are a class at Citizens ($8.0bn) and SoFi
  ($16.9bn, fair value), inside PNC's other consumer since 1 Jan 2026, $182m
  in KeyCorp's discontinued operations; Capital One's 10-Q says Discover sold
  its student portfolio before the merger; "student" appears in none of the
  other twelve. The one clean comparison for unsecured lending: Capital One
  (personal loans $8.6bn; its Call Report other consumer is these loans).
  Fifth Third splits out $626m unsecured, but its Call Report other consumer
  is $10.2bn, mostly solar, RV and marine: first marked Clean, corrected to
  Mixed the same evening. Solar is counted as unsecured by the analyst's
  ruling (*"solar might as well be considered unsecured"*, 15 Oct 2026):
  Fifth Third's unsecured is then $4.9bn, about half its other consumer, and
  it stays Mixed.
- What I got wrong: the readers recorded "not stated" for KeyCorp's secured
  non-auto lending and Capital One's student loans; the tie-out's own search
  found both sentences, and the file was corrected. The comparison script
  first misread "$2.8 billion" (3 false DIFFERS; the workbook was right).
- The peers' minimum book is now 0 (the analyst: *"for peers we should not
  worry about a $1b minimum if keybank is not held to that standard"*).
- The whole tool also ships as one file with a window
  (`tools/make_app.py`, `app.py`), and the complete suite was run once:
  1,138 passed before this tab was added.

## 15 October 2026, evening: the peer group follows the pack, and a faster pack

The analyst, on Decide: *"this tab needs to adjust with peers and i need a
faster way to select and de-select peers"*.

- **Banks in the pack**, a new picker on Peers: every peer, regionals only,
  large banks only (the five the roster does not mark regional), none. Each
  bank's cell reads **Pack** (follow it), Yes or No (override); a bank out of
  the pack is gray with its name struck through. Every view reads one
  switch per peer on Workings, so nothing else changed.
- **The Peer group series are live** (`book._live_peer_group`): each
  quarter a series had a value, its Data cell sums Peers data (or Peers
  delinquency data) over the banks kept that quarter and in the pack now,
  needing the banks the Peers tab asks for; its latest value and quarter on
  Lines by source follow. Decide, Thresholds and Summary follow from there.
  Evidence, Backtest and Decide's "What the history suggests" stay as built.
  The source keeps its name, "Peer group (15 banks)".
- Walkthrough, three new steps (B11 to B13): Regionals only, every peer but
  JPMorgan, then as built; the expected composites are summed in Python from
  the per-bank rows. **1,514 of 1,514** reads as expected in Excel 16; slicer
  check PASS. Credit card net, peer group latest: 3.95% as built, 3.79%
  regionals only, 4.25% without JPMorgan.
- Tests: the peers files, test_book, test_peer_loan_classes, test_app: 126
  passed before two tests were updated to the new switch values and the new
  delinquency data column; those two then passed.

## 15 October 2026, late: What fits the history the lines are set from

The analyst: *"i feel like adjusting those widths should somehow work in such
a way that it would bring the others into an acceptable range"*, then, on the
proposal to show every setting's range at once, *"okay your idea works"*.

- Decide, beside "What each setting does when you raise it": for the source
  picked, the range in which each setting fits that history and whether the
  setting typed does. Width of Moderate below Moderate-Low begins;
  Moderate-Low above the width and (floored at zero) below median / yearly
  move; How rare High is above width x move / spread and up to (worst -
  median) / spread. The Check's own rules; nothing is changed for the
  analyst, so each line keeps one meaning.
- Walkthrough: 8 new reads of the panel's text (B3, B4) against the ranges
  computed in Python from scale.py; **1,522 of 1,522** in Excel 16, slicer
  check PASS. test_decide and test_book: 47 passed.

## 16 October 2026, reporting changes marked on every series they touch

The firm, on the commercial proposal's question 13: *"Definitely mark
reporting changes."* Every change to the Call Report's definitions or forms
is labelled on every series it touches, in the quarter it took effect, a
change spread over several quarters included, the consumer book too.
Built on `commercial-build`, from `threshold-engine-book` (draft PR #442).

- **The registry**, `config/reporting-changes.json`, read and checked by
  `reporting_changes.py`: one entry per change, every key required (first
  and last quarter it took effect, the tool's products and measures it
  touches, the Call Report items for commercial later, one sentence of what
  changed, its sources with their addresses, and a link to a definition
  note that already says it). A malformed entry is refused by name, every
  problem at once, as the book refuses. Twelve changes, each marked verified
  in `docs/commercial-2026-10/research-breaks.md` or `research-fdic.md` (on
  main), and each citing its primary source, not those files. Six touch the
  consumer products: loans classified as trading (2008Q1, all five);
  FAS 166 and 167 (2010Q1, card and other consumer); auto split out of other
  consumer (2011Q1, from the FDIC's own LNAUTO definition); CECL (2020Q1);
  COVID-19 deferrals not reported as past due (2020Q2, the past-due measures,
  not nonaccrual); and the NDFI and margin-loan revision (2024Q4 to 2025Q2,
  other consumer, best efforts until 30 June 2025).
- **Not duplicated:** the card securitization label before 2010 was already
  in every card series (`books.DEFINITIONS`), and the auto split in every
  other consumer series. Those two entries link to that note ("The note above
  that says ... describes this change") with the source, and the registry is
  refused if the note stops saying it.
- **The series notes.** `peers build` takes `--reporting-changes FILE`
  (required; the window's Peers step has the field; the book's new required
  key `reporting_changes`, null only for a book with no Call Report series).
  Every file it writes carries a `# reporting-change:` line for each change
  touching its product and measure within its quarters, so Sources shows it
  as "Reporting change". The Run tab names the file, the count and its
  SHA-256.
- **The table.** The book's workbook has a **Reporting changes** tab after
  Sources, on the reference-tab template: the registry's own words on what it
  leaves out, then one row per change (Change, Took effect, Products touched,
  Measures touched, Call Report items, What changed, Source document). Every
  heading, the tab and "Reporting change" have Glossary entries, with a test.
- **The charts.** Carried as one more series of the kind each chart already
  has, no new machinery. Decide: a diamond along the top of the rating zones
  in each quarter a change took effect for the row shown, read from its
  series files' notes, within the window. Peers: a diamond on the pack
  composite, charge-offs (product and rate picked) and delinquency (product
  and measure picked), in the legend as "Reporting change". No diamond where
  the composite has no rate (the test data's other consumer composite is
  blank in 2011Q1, so the auto split shows no diamond there).

**Left out of the registry, and why** (also in its `_what`): the proposed
2025 modification-reporting change (final notice not found, NOT CHECKED);
FAS 141(R) in 2009 (an accounting change the agencies declined to add to
the report); the 2018 FFIEC 031 scope rule (names no loan category, which
roster banks switched was not checked); ASC 842 in 2019 (no loan item
changed); the 2020 drawdowns and PPP (not reporting changes; question 15 is
open). The 2013Q2 consolidated real estate breakdown is labelled on the
commercial items only: the record names construction, multifamily, nonfarm
and farmland, not 1-4 family.

**Proof.** Each test file run on its own (a Python 3.13 environment with
`openpyxl` and `formulas`): `test_reporting_changes.py` (new) 40 passed: the
registry in the repository, 18 malformed entries refused by name, every
problem listed at once, the notes on an affected and an unaffected series
(other consumer carries the NDFI revision, card does not; 30-89 carries the
deferrals, nonaccrual does not), a spread change touching a series that
holds any of its quarters, the link instead of a repeat, Sources, Decide's
marker recalculated (2020Q1 in the last 48 quarters, 2010Q1 too on every
quarter, nothing on two rows shown or on mortgage), the book's key and tab.
`test_peers_workbook.py` 66 passed (the Peers markers recalculated, card net
2008Q1, 2010Q1 and 2020Q1 where the composite has a rate; card 90+ accruing
2020Q1 and 2020Q2, nonaccrual 2020Q1 only). `test_peers_cli.py` 125 passed,
1 skipped, 2 failed: `test_the_regionals_pack_and_no_exemption` and
`test_pro_forma_adds_the_absorbed_banks_and_leaves_nothing_out` fail the same
on `threshold-engine-book` as it stands (checked in a clean worktree), from
the 15 Oct pack picker, not this work. `test_peers_into.py` and
`test_peers_dashboard.py` 39 passed (the series files byte for byte the same
under the old and new peer workbook builders). `test_decide.py` 31 and
`test_workbook.py` 71 passed. `test_book.py`, `test_app.py`,
`test_launcher.py`, `test_peers_books.py` 184 passed, 4 skipped (Windows and
window-only). `test_internal_tab.py` and `test_peer_loan_classes.py` 25
passed; two internal-tab book tests failed before this work too (their test
book lacked `loan_classes`), fixed with the new key.

- **Got wrong, corrected:** a test first assumed the other consumer
  composite has a rate in 2011Q1; in the test data it does not, so there is
  no diamond to draw, and the test now says so.

**Not done.** Not opened in Excel, and the walkthrough was not re-run: the
diamonds, the tab's layout and the Sources rows are proved by the tests and
`formulas`, not seen. The book was not built against the real FDIC cache
(none on this machine), so no consumer series file from real data was read.
The window's new field was not opened (no display here; the three window
tests skip). The complete suite was not run in one go. The Peers chart notes
do not mention the diamond: each note has one 140-character line and it is
full; the legend and the Glossary carry it.

## 16 October 2026, evening: the commercial data layer

The data every answer to the commercial proposal's open decisions needs, and
nothing that depends on them: no commercial book file, no segment choice, no
settings. On `commercial-build`.

- **Six commercial products** that `peers pull` and `peers build` know,
  beside the consumer five (`books.COMMERCIAL`, `delinquency.FIELDS`): C&I
  (LNCI; DRCI, CRCI year to date; P3CI, P9CI, NACI), construction
  (LNRECONS ...), multifamily (LNREMULT ...), nonfarm nonresidential
  (LNRENRES ...) and its owner-occupied (LNRENROW ...) and other (LNRENROT
  ...) splits. Every field is one `docs/commercial-2026-10/research-fdic.md`
  (on main) confirmed; the first-filed quarters are in `delinquency.py`.
  Built exactly as the consumer products are: year-to-date differencing,
  the repeated year-to-date and push-down fixes, the jump, the acquisition
  share, pro forma.
- **A blank commercial field is not filed, never 0.** The consumer products
  keep the earlier build's reading (blank = 0), which their tie-outs
  reproduce; commercial has no earlier build. A bank-quarter with a blank
  field is out of the bank's book, with its own reason ("a field of the
  product is not filed (blank) in this window", read over the quarters the
  jump test reads, i-5 to i) and out of the industry. Read as 0, the splits'
  2006 quarters would have been a book of 0, 2007Q1 a "jump", and the
  industry would have written windows over balances of 0.
- **The 2007 splits: labelled, not started at 2008Q1.** The code's own
  pattern is the label (card before 2010, other consumer before 2001), so
  every split series says: 2,925 to 3,044 filers filed the split as 0 and 0
  in 2007 ($20.1bn to $27.0bn of nonfarm loans), none from 2008Q1, so the
  industry in 2007 and its windows through 2008Q3 leave those loans out; TFR
  filers never filed it (838, $64.1bn at 2007Q1; 655 blank at 2011Q4, 17
  from 2012Q1). Measured on the cache, call forms read from the API.
- **17 filers on CALLFORM 2** (names of foreign banks) file balances and no
  charge-off, past-due or nonaccrual field in any quarter since 2006
  ($77.6bn of C&I at 2026Q2): in no commercial series, said on each.
- **The reporting-change registry** names the commercial products its
  entries' own Call Report items touch (none for the 2010 NDFI line, which
  its source says came out of other loans, not C&I); the 2007Q1 split change
  links to the splits' "first filed 2007Q1" note.
- **Fixed on the way:** the peer workbook refused a build of the six (its
  one-line not-built note listed every product and did not fit); it now
  counts them when the names do not fit. The window and the internal import
  keep the consumer five.
- **Run for real** (cache outside the repository): pull 2006Q1-2026Q2 with
  `--delinquency yes --mergers 2005-01-01`; build with the consumer book's
  rule settings, stated as the consumer book's, from 2006Q1 and from 2005Q1
  (KeyBank's 2006Q4 window needs 2005Q4). The stress table and the Fed
  comparison are in `docs/commercial-2026-10/stress-tool-rules.md`, every
  command written out.

**What it found.** Industry within 0.034 points of the as-filed table in
every segment (0.03 or less on every figure but C&I nonaccrual's worst quarter;
corrected 17 Oct, the first wording said 0.03 throughout); the C&I gap is the 17 no-flow filers' balances (checked:
3.1664% with them is the as-filed 3.166%). KeyBank nonaccrual unchanged.
KeyBank's C&I charge-off series as the workbook would read it is **two
quarters**: the December 2024 NDFI move (28.6% of its C&I) trips the 25%
jump for 2024Q4-2025Q4. Over every kept quarter its largest z is 16.4 (2006Q4
on) and 3.0 (2014Q1 on), against 13.0 and 4.1 as filed. Multifamily's z is
still in the hundreds. FDIC against the Fed's four-quarter means, 2006Q4 on:
C&I mean +0.030, largest 0.178 (2010Q1); CRE mean -0.013, largest 0.094
(2009Q4).

**Proof.** `test_peers_commercial.py` (new): 14 passed, on a fixture taken
from the real pull (KeyBank, JPMorgan, a TFR filer, a CALLFORM 2 filer, a
filer that filed the split as 0, 2006Q3-2008Q2), the rates checked against
arithmetic on the fixture, with the consumer reading shown to give the wrong
reason. Each file run on its own: peers books 54, delinquency 39, analyses
33, fdic 45, combinations 36, roster 23, loan classes 6, internal 92,
reporting changes 40, peers workbook 66, peers into 30, peers dashboard 9,
internal tab 19, book 16, app 4: all passed. `test_peers_cli.py` 125 passed,
1 skipped, 2 failed: the same two that fail on the commit before this work
(checked again today in a detached worktree of 32ce97e4, since removed).
Also run, after the change: launcher 110 passed, 4 skipped (the window; the
product test now says it offers the consumer five), compare 6, workbook 71,
decide 31, synthesis 22, templates 77, workbook synthesis 44. The complete
suite was not run in one go.

**Not done.** No build before 2005: the 1991Q1-2005Q4 quarters were pulled
(the pull needed nothing new), but the merger record since 1990 is refused on
four rows with change codes 213 ("Merger - Assisted") and 225 ("Partial
Purchase & Assumption - Without Assistance"), which are on neither of
`fdic.py`'s lists; what they mean is the firm's call. Whether the jump should
read the December 2024 NDFI move as a book move is the firm's call too;
nothing was changed. The peer workbook and the series were not opened in
Excel. The peer dashboard still says "consumer book" in two places. The
window does not offer the commercial products. The industry delinquency
effect of the 2007 zero-filed split was not measured.

## 17 October 2026, review fixes to the commercial data layer

A review of the branch raised eight findings. Each was reproduced before it
was fixed, and each fix has a test in `test_peers_commercial.py` that failed
before the fix (8 new tests, all red first, for the reason the finding gave).

- **First window marked not filed by the last quarter** (raised twice).
  `bank_book`'s not-filed test read `range(i - 5, i + 1)`. For the first window
  that range starts at -1, which Python reads as the last quarter. Now
  `max(0, i - 5)`.
- **A 0 where the balance is not filed.** A window with a not-filed quarter
  among its own four now has no `avg_balance`. Before, a bank that never
  filed the split showed 0, and KeyBank's owner-occupied 2007Q3 showed three
  filed balances divided by four (3,244,472) in the Data tab's column G,
  which the balance charts read. A window where only the quarters the jump
  test reads (i-5, i-4) are blank keeps its average. `balance_path` now
  says when an average is missing, rather than failing.
- **A summed industry written where one of its products was not filed.**
  `industry` now gives a quarter a flow only if every product in the sum has
  a filer. Before, any one product was enough. On the real cache (2005Q1 to
  2026Q2), C&I plus owner-occupied lost the eight windows 2005Q4 to 2007Q3,
  which had been C&I alone. The CRE sum is unchanged.
- **Balance kept where the flow was dropped.** In the quarter after a filer
  left a field blank, its flow was out of the industry but its balance was
  in. Now both are out (`_counted`). On the real cache this moves 20
  owner-occupied and 20 other nonfarm windows by at most 0.0010 and 0.0018
  points. C&I, construction, multifamily and nonfarm are unchanged. **Not
  changed:** a filer missing from the previous quarter altogether still has
  its balance counted and its flow left out. That is the earlier build's rule
  for every product, consumer included, and it was not part of the finding.
- **An absorbed book that was not filed was read as no book.**
  `acquired_quarters` now lists the quarter when an absorbed bank's last
  filing leaves the commercial balance blank, because its share cannot be
  shown to be under the threshold. The window's reason still reads "an
  acquisition brought in at least the acquisition share". For these
  quarters that is stronger than what is known. A separate label would need
  a new argument through `bank_book` and delinquency, and was not added.
- **Wrong denominator in the industry notes.** A commercial industry note
  said "every filer in the cache (4313 in 2026Q2)", but 17 of those file no
  flow field. Charge-off notes now count the filers whose figures are in
  the sums (`industry_filers`). Delinquency notes use the industry's own
  `banks`. On the real cache that is 4,296 of 4,313 for all six commercial
  products and the CRE sum. Where every filer counts, the wording is
  unchanged.
- **2013Q2 real estate breakdown too narrow.** 78 FR 30922 was fetched again
  today. It says "the nine-category breakdown of loans secured by real
  estate for the consolidated institution". Three of the nine are 1-4 family
  (1.c(1), 1.c(2)(a), 1.c(2)(b), recorded in `docs/INTERNAL-IMPORT.md`), so
  the entry now also labels mortgage and home equity. The 16 Oct entry above
  ("labelled on the commercial items only ... not 1-4 family") read the
  research table's category column and not its event text. It was wrong,
  and it is left in place as written. Whether the FDIC's fields moved is NOT
  CHECKED, for the 1-4 family lines as for the others.

**Proof.** Each file run on its own (uv, Python 3.13, openpyxl 3.1.5,
formulas): peers commercial 22, peers books 54, combinations 36, delinquency
39, analyses 33, peers into 30, peers dashboard 9: all passed. `test_peers_cli.py`:
125 passed, 1 skipped and 2 failed. The two failures are the same two that
fail on the commit before these fixes; this was checked today in a detached
worktree, since removed. Peers workbook: 66 passed, after re-running two
chart-XML tests with `OPENPYXL_LXML=False`. This machine has lxml, which
writes `<x/>` where the tests expect `<x />`. Reporting changes: 40
passed, run with `OPENPYXL_LXML=False`. Before the expectations were
updated, three tests failed: the registry's product list and mortgage's
notes, which this change moves on purpose, and the same lxml chart-XML
difference. The complete suite was not run.

**The review's minor findings, 17 Oct.** Five of the six were fixed, each with
a test:
- The registry refuses a line break of any kind (`\r`, U+2028 as well as `\n`)
  in a name, a sentence or a citation, since a series note is split into
  lines.
- A source's address must start `https://`, as its refusal already said.
- A folder or a file that is not UTF-8, named as the registry, is refused
  by name instead of crashing.
- A summed industry series says each definition note once.
- The stress table's "within 0.03 points" is corrected to 0.034: C&I
  nonaccrual's worst quarter differs by that much.

Left as found: the 2008Q1 completion of the owner-occupied split is not a
registry entry. The FDIC's own LNRENROW definition records it, but it is a
coverage change in the 2007 filings, not a revision, and the split series
already say so in their notes. `test_reporting_changes.py` and
`test_peers_commercial.py`: 67 passed. The new duplicate-note assertion was
not run against the code before its fix.

## 17 Oct 2026, question 17: FDIC history codes 213 and 225 placed

The firm answered the commercial proposal's open questions on 17 Oct 2026,
each "agreed with the recommendation" on the docket form
(`docs/COMMERCIAL-PROPOSAL.md` on main, section 5). Built on
`commercial-round2`, from `threshold-engine-book` (draft PR #442) at 4d92d7a9.

- **Question 17, 17 Oct 2026, agreed with the recommendation:** *"How are the
  FDIC history codes 213 ("Merger - Assisted", 3 rows, May 1990) and 225
  ("Partial Purchase & Assumption - Without Assistance", 1991) classified?"*
  The answer: *"agreed, so 213 is an acquisition and 225 is not"*.
- **In code.** `peers/fdic.py`: 213 joins `ACQUISITIONS`, like 211; 225 joins
  `NOT_AN_ACQUISITION`, like 712. A code on neither list is still refused by
  name (`unrecognised`), so the next unplaced code stops the pull the same way.
- **Counted live today** (`api.fdic.gov/banks/history`, filtered by code):
  213 has 332 rows in all, 3 of them since 1990-01-01 (4, 11 and 25 May 1990;
  acquirers 33097, 33057, 33110); 225 has 1 row (9 Oct 1991, acquirer 15689).
  None of the four acquirers is on the roster (`config/peers.json`, 16 banks),
  so no roster bank's windows move because of this answer.
- **The merger record since 1990** in the commercial cache (pulled earlier
  today by the interrupted run, with these two codes placed): 5,946
  acquirers, 16,362 absorptions. It was not re-pulled for this entry.
- **Proof.** `tests/test_peers_fdic.py`: the allowlist test now names 213 and
  225, and a new test runs the three kinds (213, 225, 712) through
  `unrecognised`, `classify`, `absorptions` and `pull_mergers`. Run at this
  commit alone, in a clean worktree (uv venv, Python 3.13, openpyxl 3.1.5,
  formulas, `OPENPYXL_LXML=False`): `test_peers_fdic.py` 46 passed. With 213
  taken back off the list, the two tests above fail (checked, then put back).
  Every test file importing `fdic`: `test_peers_fdic`, `test_internal`,
  `test_launcher`, `test_peers_cli`, `test_peers_combinations`,
  `test_peers_commercial`, `test_peers_delinquency`, `test_reporting_changes`.
  Together: 515 passed, 5 skipped and 2 failed. The two are
  `test_peers_cli.py`'s `test_the_regionals_pack_and_no_exemption` and
  `test_pro_forma_adds_the_absorbed_banks_and_leaves_nothing_out`, the two
  this log already records failing on `threshold-engine-book` before this
  work (the 15 Oct pack picker). The rest of the suite was not run.

## 17 Oct 2026, question 14: the stated acquisitions the FDIC record cannot see

- **Question 14, 17 Oct 2026, agreed with the recommendation:** *"Add a
  stated list of acquisitions the FDIC record cannot see (JPMorgan/WaMu,
  M&T/Wilmington Trust, and asset purchases such as Wells/GE Capital), each
  with its 8-K, read by the build like the FDIC record?"* If yes: *"Those
  windows are left out with a reason."*
- **The list.** `config/stated-acquisitions.json`, read and checked by the
  new `peers/stated.py`. Each entry has five keys, all required, none with a
  default: the acquirer's certificate, the quarter, what happened, the
  citation and the filing's address. A malformed entry is refused by number,
  certificate and quarter, every problem at once; so are a missing or extra
  key and the same deal listed twice. A certificate not on the roster is
  refused. An entry outside the quarters read is named on Run as not read.
- **What is in it.** Four entries, only from
  `docs/commercial-2026-10/research-breaks.md` on main, section B, the rows
  marked not in the record:

  | Acquirer (certificate) | Quarter | Close, as the filing gives it | Filing |
  |---|---|---|---|
  | JPMorgan (628) | 2008Q3 | Washington Mutual's banks, from the FDIC, 25 Sep 2008 | 8-K, Item 8.01 |
  | M&T (588) | 2011Q2 | Wilmington Trust, effective 16 May 2011 | 8-K, Item 2.01 |
  | Wells Fargo (3511) | 2016Q1 | GE Capital's commercial loans and leases, $26.7bn, 1 Mar 2016 | 8-K, Exhibit 99.1 |
  | Capital One (4297) | 2015Q4 | GE Capital's Healthcare Financial Services, 1 Dec 2015 | 8-K, Exhibit 99.2 |

  Each filing was fetched from EDGAR today at the address in the file, and
  each citation now quotes it word for word. The interrupted run's
  citations had paraphrased two of them (JPMorgan's and M&T's) after a
  colon, and called Capital One's exhibit an earnings release; its title is
  the Financial Supplement.
- **Left out: Huntington / Macquarie Equipment Finance.** research-breaks.md
  records its close date as NOT CHECKED. The 8-K exhibit it cites (24 Feb
  2015, fetched today) announces the agreement and says the purchase "is
  anticipated to be completed by March 31, 2015"; no filing of the close was
  read, so its quarter is not known and no entry was written. The file's
  `_what` says so. Also not listed: the branch purchases research-breaks.md
  measured as negligible in commercial, and Capital One / HSBC cards
  (2012Q2, consumer), which the question does not name.
- **How it is read.** `peers build --stated-acquisitions FILE|none`, required.
  The window has the same field (`none` states that none is read). In a
  book it is `peers.stated_acquisitions`, required, null or a file. The
  consumer book states null and says so in its notes, so its build is
  unchanged.
- **What it does.** For the acquirer, every product's charge-off windows
  holding the quarter are left out with their own reason, *"a stated
  acquisition the FDIC record cannot see is in this window"*
  (`books.WHY_STATED`). It comes right after a recorded acquisition in the
  order of reasons, since no share of the book is measured. The four-quarter
  delinquency average is blanked the same way (`delinquency.WHY_STATED`),
  never a quarter-end rate, and a bank so blanked is left out of the pack's
  average, which names it. The bank's book index reads the quarter as
  declared, as for an extra acquisition.
- **Where it is recorded.** Run names the file, its SHA-256, and the entries
  inside and outside the quarters. Every series file the rules apply to,
  charge-offs and delinquency, carries a line naming the entries in its
  quarters with their citations. The glossary has "Left out: a stated
  acquisition", and "Kept" names it among the reasons.
- **What it changes on the real cache** (`scratchpad/cache-commercial`,
  public FDIC data, not in the repository; 2006Q1 to 2026Q2, the commercial
  example book's rules: jump 0.25, share 0.05, minimum 0, pro forma, the
  merger record since 2005). Measured with the build's own steps, by
  `bank_book` and `bank_delinquency` with and without the list, not by a
  full build:
  - **Charge-offs.** The four acquirers, six products, four windows each:
    96 windows hold a stated quarter. 60 now give the stated reason:
    - 56 were kept before, two books mixed: M&T's C&I, construction,
      multifamily and nonfarm nonresidential; Wells Fargo's six; Capital
      One's C&I, construction, multifamily and owner-occupied;
    - 4 (JPMorgan C&I, 2008Q3 to 2009Q2) were left out before as "a quarter
      is missing", the last reason in the order.
    
    The other 36 were already left out for an earlier reason, which still
    shows: the jump (JPMorgan construction and multifamily; Capital One
    nonfarm nonresidential and other nonfarm), or a field not filed
    (JPMorgan's three nonfarm series; M&T owner-occupied and other nonfarm).
  - **Delinquency.** 235 of the 360 four-quarter averages (four banks, six
    products, five measures, three quarters) are newly blanked: Wells Fargo
    90, M&T 85, Capital One 60, JPMorgan none (the jump had blanked them).
- **Proof.** `tests/test_stated_acquisitions.py`, 30 tests:
  - the file in the repository;
  - each refusal;
  - `by_cert`;
  - a stated quarter leaving out four charge-off windows and three
    delinquency averages;
  - a build writing the note, the Run lines and the declared index quarter;
  - the pack's delinquency note naming the bank;
  - `none`;
  - the build's refusals before anything is read;
  - the command line requiring the flag;
  - the book key, required and null or a file;
  - the consumer book's null.
  
  With the stated reason taken out of `bank_book`, two tests fail; with it
  taken out of `bank_delinquency`, two others fail (checked, then put back).
  Existing tests were given the new required setting, and two were updated
  for it: the peer glossary's list of "Left out" terms, and the
  byte-for-byte series comparison against the frozen round-1 builder, which
  takes no `stated` keyword (none is read there, so the files are the same).
- **Results.** Run at this commit alone, in a clean worktree (uv venv,
  Python 3.13, openpyxl 3.1.5, formulas, `OPENPYXL_LXML=False`), every test
  file that imports a module changed here, 24 files:
  - `test_stated_acquisitions` 30 passed;
  - the peers files (`cli`, `workbook`, `dashboard`, `into`, `books`,
    `delinquency`, `roster`, `fdic`, `commercial`, `combinations`,
    `analyses`);
  - `test_launcher`, `test_book`, `test_cli`, `test_compare`,
    `test_internal`, `test_internal_tab`, `test_peer_loan_classes`,
    `test_app`, `test_reporting_changes`, `test_synthesis`,
    `test_templates_cli`, `test_workbook_synthesis`.

  In all, 958 passed, 5 skipped and 2 failed. The two are the
  `test_peers_cli.py` failures recorded above as failing before this work.
  The first pass also failed three tests that this commit then fixed: the
  two updated above, and `test_reporting_changes.py`'s registry refusal,
  which called the build without the new setting. Those files were re-run:
  `test_reporting_changes.py` 45 passed, and the two updated tests passed.
  The rest of the suite was not run.
- **Not done.** Nothing was opened in Excel; none can be here. No full
  build was run with the list: the effect above was measured with the
  build's own functions. The window's new field was not opened (no
  display). The commercial example book (local branch
  `commercial-example`) does not have the new required key
  `peers.stated_acquisitions`, so it is now refused until it states the
  list or null. It was not rebuilt.

## 17 Oct 2026, question 15: the 2020 drawdowns and the PPP loans labelled on C&I, as events

- **Question 15, 17 Oct 2026, agreed with the recommendation** on the docket
  form (`docs/COMMERCIAL-PROPOSAL.md` on main, section 5): *"Also label
  2020Q1–2021Q4 on C&I (revolver drawdowns and PPP: not definition changes,
  but they move the book), and leave out the windows the 25% rule catches
  across both periods?"* The recommendation: labelled; windows left out
  where the rule fires.
- **The events.** `config/reporting-changes.json` has a second required
  list, `events`, beside `changes`. Its entries take the same keys and are
  checked by the same rules, and a name may be used only once across both
  lists. Two events, both on C&I and every measure, each citing the FDIC
  Quarterly Banking Profile figures `docs/commercial-2026-10/research-breaks.md`
  (on main) records, with the addresses that file lists:
  - **Revolving-line drawdowns, 2020Q1.** QBP Q1 2020: C&I up $339.4 billion
    (15.4 percent); unfunded C&I commitments down $269 billion.
  - **Paycheck Protection Program loans, 2020Q2 to 2021Q4.** QBP Q2 2020:
    C&I up $146.5 billion, attributed to the PPP, with $482.2 billion of
    PPP loans. 2021Q4 is the end of the span the firm chose. When the PPP
    loans left the books was not checked, and the entry says so.
  - Both say "Not a change to the report". The registry's `_what` no longer
    calls question 15 open.
- **How an event is written.** Every series file `peers build` writes
  carries a `# event:` line for each event touching its product and measure
  within its quarters, beside its `# reporting-change:` lines. Sources shows
  it as "Event". The Reporting changes tab lists the events after the
  changes, under their own heading, "Events". The Glossary has "Event". Run
  counts them ("12 changes and 2 events").
- **What an event does not do.** It is never called a reporting change.
  Decide's diamonds and the Peers charts' diamonds still mark reporting
  changes only: events are not drawn on the charts. An event leaves nothing
  out and keeps nothing in. The jump alone decides, as before: the event
  list reaches only the note lines, never `bank_book` or
  `bank_delinquency`.
- **Where this came from.** The interrupted run's code, carried in the
  partial commit ae64d732 (now replaced by this one and the next). It was
  reviewed and narrowed to this question. Two things were changed:
  - `write_tab`'s `events` no longer has a default; `[]` states none;
  - `labelled_quarters` moved to question 16, which uses it.
- **Proof.** `tests/test_reporting_changes.py` has these tests:
  - the two events in the registry, their sources and words;
  - an event labelled as an event, on C&I only, and never read as a change;
  - a malformed event refused by name, and a name used once across both
    lists;
  - the tab's Events heading;
  - the book's tab and Glossary entry;
  - a `peers build` from KeyBank's public C&I filings
    (`tests/data/peers/keybank_ci_2005.json`, 2018Q1 to 2023Q4).

  In that build, KeyBank's C&I rose 18.0% in 2020Q1, under the 25% jump.
  Its net and gross series, the industry's, and two delinquency files carry
  both events, and none as a reporting change. The net series keeps all 20
  of its windows, and Run says "12 changes and 2 events".

  The fixture's 86 quarters were compared, field by field, with the
  commercial cache `peers pull` wrote on 16 Oct 2026: no difference. With
  the event lines taken out of the charge-off series, the build test fails
  (checked, then put back).
- **Results.** Run at this commit alone (scratch venv, Python 3.13,
  openpyxl 3.1.5, formulas 1.3.4, pytest-xdist, 4 workers).
  - `test_reporting_changes.py`: 52 passed.
  - Every other test file that imports a module changed here, 16 files:
    `test_app`, `test_book`, `test_cli`, `test_decide`,
    `test_internal_tab`, `test_launcher`, the peers files (`books`, `cli`,
    `combinations`, `commercial`, `dashboard`, `into`, `workbook`),
    `test_stated_acquisitions`, `test_workbook` and
    `test_workbook_synthesis`.

    726 passed, 5 skipped and 2 failed, in 1 h 33 min. The two failures are
    `test_peers_cli.py`'s `test_the_regionals_pack_and_no_exemption` and
    `test_pro_forma_adds_the_absorbed_banks_and_leaves_nothing_out`. This
    log already records both as failing before this work.

  The rest of the suite was not run.
- **Not done.** Nothing was opened in Excel; nothing can be opened in Excel
  here. No real-cache build was run at this commit. The FFIEC instruction
  that places PPP loans in C&I was not read: research-breaks.md records
  that ffiec.gov returned 403.

## 17 Oct 2026, question 6: PARTIAL, the interrupted run's 1991 build, kept unreviewed

**A partial commit, not reviewed.** Question 6 was not in this step's scope
(questions 15 and 16 were). The run that was cut off by a usage limit left
its notes on question 6 in its WIP commit. They are kept here, word for
word apart from the heading, this paragraph and the closing "Not done", and
one note in brackets, so that they are not lost. Every figure below
is the interrupted run's: it ran on that run's own code, before questions
17, 14, 15 and 16 were reviewed and committed, and none of it was re-checked
here.

- **Question 6, 17 Oct 2026, agreed with the recommendation:** *"Pull
  commercial history from 1991Q1, not 2006Q1 as for consumer?"* No code was
  needed beyond question 17. The build was run once, from 1991Q1. Results
  below.

**Run on the real cache** (`scratchpad/cache-commercial`, public FDIC data, not
in the repository; the commercial example book's settings, with the stated
list):

- **From 1991Q1** (question 6; the merger record since 1990). 27 min 23 s,
  142 quarters.
  - **Industry.** 139 windows, 1991Q4 to 2026Q2.
  - **Early-1990s peaks against 2006 on** (net, not checked against the QBP):

    | Series | Peak 1991Q4 to 1995 | Peak 2006 on |
    |---|---|---|
    | CRE sum | 1.858 (1993Q2) | 2.480 (2010Q2) |
    | C&I | 2.037 (1992Q1) | 2.520 (2010Q1) |
    | Construction | 3.249 (1993Q2) | 6.485 (2010Q1) |
    | Multifamily | 1.449 (1993Q2) | 1.332 (2010Q2) |
    | Nonfarm nonresidential | 1.608 (1992Q3) | 1.251 (2010Q4) |

  - **The pack composites** start at 1998Q4.
  - **KeyBank's C&I** runs from 2003Q4. 47 earlier windows are left out as
    "a quarter is missing".
  - **The cause.** Pro forma adds 122 banks to KeyBank. 12 of them are new
    charters whose first filing falls mid-year, so the existing rule gives
    that quarter no flow, and every window holding it is missing. The rule
    was not changed. (The interrupted run's text pointed to "the decisions
    below"; it wrote none, so none is recorded here.)
  - **Across the 1990s C&I windows.** 553 bank-windows are missing, 35 are
    left out by the jump, and 16 by a stated acquisition.

**Not done.** No review, no test, no rebuild for question 6. The early-1990s
industry figures were not tied out to the QBP. Nothing was opened in Excel.

*Superseded:* question 6 was tested and rebuilt on the reviewed code; see
"17 Oct 2026, question 6: a peers build from 1991Q1", below.

## 17 Oct 2026, question 16: a series continues across windows left out only for a labelled change

- **Question 16, 17 Oct 2026, agreed with the recommendation** on the docket
  form (`docs/COMMERCIAL-PROPOSAL.md` on main, section 5): *"When a labeled
  reporting change trips the 25% jump (KeyBank's C&I in 2024Q4, the NDFI
  move), keep the series going across it instead of starting it after the
  gap?"* The recommendation: *"KeyBank's C&I charge-off history runs 2006
  on, with the change labeled and its windows left out. This changes how
  every series is written, consumer included: today each starts after its
  last left-out window."*
- **What counts.** A bank's own window that the jump alone left out:
  - every move that tripped it falls in a quarter that a reporting change or
    an event names for the series' product and measure
    (`reporting_changes.labelled_quarters`);
  - and no other reason would have left the window out.

  `bank_book` gives `jumped` and `why_without_jump` for this, and
  `bank_delinquency` gives `jumped` and `why_avg4_without_jump`.
  `peers.run.bridged` picks the windows. Every row's `why` is what it was
  before; only the two new keys were added.
- **How the series is written.** It continues across those windows. They
  are not written and never filled. A `# left-out:` line declares them:
  their quarters, the moves, the changes or events that name them, and that
  the earlier history is kept. Sources shows it as "Continues across". The
  run never begins or ends on a left-out window.
- **What does not change.** Every other reason a window is left out still
  starts the series after it:
  - an acquisition, recorded or stated;
  - the minimum book;
  - a missing or unfiled quarter;
  - a jump in a quarter nothing names, or one where a move that nothing
    names trips it too.

  Only a bank's own series continue across a gap: KeyBank's, and each
  peer's own file under `banks/`. The pack composites, the medians and the
  industry are written as before.
- **The readers.** Each reader takes the declared gap and no other.
  `series.check(points, frequency, left_out)` returns the calendar, with
  None in each declared quarter. A gap the file does not declare is
  refused, as is a declared quarter that holds a value or lies outside the
  first and last values.
  - Profile, evidence and backtest count only values. A year is four
    calendar quarters. A spell, a change or a departure window never spans
    the gap. The backtest tests a period only when the period `horizon`
    later has a value; its `min_history` counts values.
  - Smoothing never averages across the gap.
  - The workbook keeps those quarters on Data, blank. The live formulas
    already test each cell with ISNUMBER, so a year is still four rows.
  - The synthesis reads the gap in peer and filed files. It refuses it in
    the internal and industry series: their typical yearly move is taken
    quarter by quarter in order.
  - The command-line `profile`, `evidence`, `backtest` and `synthesize`
    read it too.
- **Proof.** `tests/test_left_out.py`, 15 tests:
  - the reader, refusals included;
  - the `left-out:` line round trip;
  - smoothing;
  - profile, spells, evidence and the backtest across a gap;
  - `unbroken_tail` and `series_note`;
  - KeyBank's C&I from the public filings
    (`tests/data/peers/keybank_ci_2005.json`): before, 2 quarters
    (2026Q1 to 2026Q2); now 2006Q1 to 2026Q2, with 2024Q4 to 2025Q4 left
    out and declared;
  - an acquisition, a stated acquisition, the minimum book, and the same
    move in a quarter nothing names, each still breaking the series;
  - the delinquency average (2024Q4 to 2025Q2 left out);
  - a full `peers build` and the workbook built from it, with those quarters
    blank on Data;
  - a consumer series: a card book up 60% in 2010Q1 (FAS 166 and 167,
    labelled for credit card) continues; a 40% jump in 2014Q1, which
    nothing names, still starts the series after it.

  **Checked by mutation:** each test was run against a deliberately broken
  copy of the code, then the code was put back.
  - When `bridged` also took windows with another reason, the acquisition
    test failed.
  - When the backtest's `min_history` counted calendar quarters, the
    backtest history test failed. That test was added here because the
    interrupted run's tests did not catch the mutation.
- **Where this came from.** The interrupted run's code, carried in the
  partial commit ae64d732, reviewed and kept. Changed here:
  - a paragraph `peers.run.build`'s docstring said twice was removed;
  - the backtest history test was added;
  - one existing test was updated, as described under Results.
- **Run on the real cache** (`scratchpad/cache-commercial`, public FDIC
  data, not in the repository). The commercial example book's settings
  from 2005Q1 to 2026Q2, with the merger record since 2005 and
  `config/stated-acquisitions.json`. It ran at this commit's code and took
  11 min 47 s.
  - **Denominator.** 15 of the 470 series files written (290, plus 180
    peers' own under `banks/`) continue across a gap. None of the pack
    composite, median or industry files does.
  - **KeyBank**, 9 files:
    - C&I gross and net run 2006Q1 to 2026Q2: 77 quarters, with 2024Q4 to
      2025Q4 declared left out (NDFI and margin-loan revision);
    - its five C&I four-quarter delinquency averages continue across
      2024Q4 to 2025Q2;
    - multifamily gross and net continue across 2009Q1 to 2010Q1 ("Secured
      by real estate, clarified"). See below.
  - **The peers' own C&I gross and net**, 6 files:
    - Citizens, 2024Q4 to 2025Q4 (NDFI);
    - JPMorgan, 2020Q1 to 2021Q1 (CECL, and the revolving-line drawdowns
      event);
    - Zions, 2020Q2 to 2021Q2 (the PPP event).
  - These are the same 15 files the interrupted run reported on its own
    code.
- **A gap this opens: KeyBank's multifamily, 2009Q1.** KeyBank's own
  filings:
  - multifamily went from 1,007,146 to 1,539,618 (+52.9%) in 2009Q1;
  - construction fell from 7,880,797 to 6,359,536 in the same quarter.

  The registry's "Secured by real estate, clarified" entry names 2009Q1 for
  multifamily, so the series now continues across those windows. That
  entry's own words say the change applied to new loans only, "so the move
  is gradual". It cannot explain a 53% step in one quarter. The cause of
  KeyBank's move was not checked: a reclassification out of construction
  is a reading of those two figures, not a finding.

  The rule follows the firm's answer as worded: a jump in a quarter the
  registry names for the product. The registry does not say whether an
  entry can move a balance at all. Some cannot: "COVID-19 deferrals not
  reported as past due" (2020Q2, eight products) changes only past-due
  reporting. Put to the firm as a decision; nothing was changed for it.
- **Results.** Run at this commit alone (scratch venv, Python 3.13,
  openpyxl 3.1.5, formulas 1.3.4, pytest-xdist, 4 workers), every test
  file in `tests/`: 1,261 passed, 5 skipped and 4 failed, in 1 h 6 min.
  - Two failures are `test_peers_cli.py`'s
    `test_the_regionals_pack_and_no_exemption` and
    `test_pro_forma_adds_the_absorbed_banks_and_leaves_nothing_out`, which
    this log records as failing before this work.
  - `test_decide.py`'s
    `test_with_no_source_picked_a_period_left_out_sets_nothing_and_the_row_says_pick`
    did not fail: its worker crashed while the real-cache build shared the
    machine. Re-run alone: 1 passed.
  - `test_peers_cli.py`'s
    `test_each_peers_banks_file_is_its_own_book_for_that_product` failed on
    purpose. It recomputed each peer's file with the old `unbroken_tail`,
    and U.S. Bank's other consumer file now starts at 2007Q1. The test now
    takes the bridge and checks each file's declared quarters, and at least
    one file must continue across a gap. Re-run: 1 passed.

  **The consumer series, in that test's data.** The data is
  `roster_2006.json`: public FDIC filings for the 16 banks, 2006Q1 to
  2026Q2. Measured with `bank_book`, `bridged` and `unbroken_tail`, at a
  minimum book of $1bn, with other consumer as it is defined now (6.b +
  6.d). 14 of the 118 charge-off files written now continue across a gap,
  all of them other consumer, gross and net:
  - Bank of America from 2007Q1 instead of 2026Q1 (2 to 68 values);
  - U.S. Bank and M&T from 2007Q1 instead of 2012Q2 (57 to 73);
  - Citizens from 2008Q4 instead of 2012Q2 (57 to 66);
  - PNC from 2011Q1 instead of 2026Q1 (2 to 57);
  - JPMorgan from 2018Q3 instead of 2026Q2 (1 to 27);
  - Capital One from 2009Q2 instead of 2012Q2 (5 to 12).

  The moves are the 2011Q1 auto split ("Auto loans get their own line"),
  the NDFI revision of 2024Q4 to 2025Q2, and, for Capital One, also 2008Q1
  ("Loans classified as trading"). KeyBank's own consumer files do not
  change. This is not the consumer book's own build: it is the test's
  data, at the test's minimum book.
- **Not done.** Nothing was opened in Excel; nothing can be opened in Excel
  here. No consumer cache is on this machine, so no real consumer build ran.
  The consumer series are covered only by the synthetic card test above.
  The consumer book was not rebuilt.

  `threshold-engine-book` gained combined products ("All consumer", and
  "A + B") after this branch left it. `labelled_quarters` matches a product
  name exactly, so a combined product would never continue across a gap
  until the registry names it. That was not checked, because that code is
  not on this branch.

## 17 Oct 2026, question 6: a peers build from 1991Q1

- **Question 6, 17 Oct 2026, agreed with the recommendation** on the docket
  form (`docs/COMMERCIAL-PROPOSAL.md` on main, section 5): *"Pull commercial
  history from 1991Q1, not 2006Q1 as for consumer?"* The recommendation:
  *"The early-1990s CRE losses are in it; splits still start 2007Q1."*
- **No code was needed beyond question 17.** What stopped a build from
  1991Q1 was the merger record since 1990, refused on codes 213 and 225.
  With both placed, `peers pull --mergers 1990-01-01` and `peers build
  --first 1991Q1` run as they are.
- **The merger record since 1990, re-pulled today** with this branch's
  code (`fdic.history("1990-01-01")`, public): 35,742 rows (213: 3; 225: 1).
  Classified, 5,946 acquirers and 16,362 absorptions, the same as the
  cache's `mergers-since-1990.json` and `absorptions-since-1990.json`,
  compared whole. So the record the build read is the one today's code
  writes.
- **Proof.** `tests/test_from_1991.py`, 5 tests, on public data:
  - `tests/data/peers/keybank_ci_1991.json`: KeyBank and the four banks the
    record says it absorbed in 1992 and 1993, 1991Q1 to 1993Q4, from the
    commercial cache;
  - `tests/data/peers/history_1990.json`: twelve history rows as the API
    returned them today (the three 213 rows, the 225 row, and KeyBank's four
    absorptions with their mirror rows);
  - `peers pull --first 1991Q1 --mergers 1990-01-01` writes the record: the
    three 213 acquirers marked in 1990Q2, the 225 acquirer not;
  - with 213 taken off the list, the same pull is refused, naming the three
    rows, and writes no record;
  - `peers build --first 1991Q1` reads it. KeyBank's C&I runs 1992Q1 to
    1993Q4, 8 windows, none left out: pro forma adds the absorbed banks,
    so the 1992 steps (37% and 60% as filed) neither break it nor trip the
    jump. Its 1992Q1 value is checked against arithmetic on the fixture.
    The industry's first window is 1991Q4. KeyBank's nonaccrual rate, as
    filed, runs from 1991Q1. No 30-89 series is written: 30-89 is blank
    before 2001Q1.

  **Checked by mutation**, then put back:
  - with KeyBank's absorptions taken out of the history rows, the build
    test fails: KeyBank's C&I is one window, 1993Q4;
  - with 213 taken off `ACQUISITIONS` in `fdic.py`, the pull test fails and
    the build fixture errors.
- **Run on the real cache** (`scratchpad/cache-commercial`, public FDIC
  data, not in the repository). At this branch's code (250d8c67; the test
  commit after it changes no code), the commercial example book's
  settings, with `--first 1991Q1`, the merger record and absorptions since
  1990 (`mergers-since-1990.json`, `absorptions-since-1990.json`) and
  `config/stated-acquisitions.json`:
  - **Time.** 25 min 31 s. Exit 0. **Nothing was refused.**
  - **Quarters.** 142 quarter files, 1991Q1 to 2026Q2.
  - **Banks.** The roster's 16 (KeyBank and a pack of 15). Filers: 15,294
    in 1991Q1, 4,313 in 2026Q2. The four stated acquisitions are all inside
    the quarters; none is outside.
  - **Files.** 470 series files: 290, plus 180 peers' own under `banks/`.
    15 continue across a declared gap, as at the 2005 build (question 16).
  - **Industry.** Every product's net charge-off series runs 1991Q4 to
    2026Q2, 139 windows. The two nonfarm splits run 2007Q4 on, as the
    recommendation says. Nonaccrual and 90+ run 1991Q1 on; 30-89 and 30+
    run 2001Q1 on.
  - **Early-1990s peaks against 2006 on**, industry net, % (not tied out
    to the QBP). The same figures as the interrupted run's table:

    | Series | Peak 1991Q4 to 1995 | Peak 2006 on |
    |---|---|---|
    | CRE sum | 1.858 (1993Q2) | 2.480 (2010Q2) |
    | C&I | 2.037 (1992Q1) | 2.520 (2010Q1) |
    | Construction | 3.249 (1993Q2) | 6.485 (2010Q1) |
    | Multifamily | 1.449 (1993Q2) | 1.332 (2010Q2) |
    | Nonfarm nonresidential | 1.608 (1992Q3) | 1.251 (2010Q4) |

  - **The pack composites' net series** start at 1998Q4 (multifamily
    1999Q3; the splits 2010Q4).
  - **KeyBank's net series.** C&I, multifamily and nonfarm nonresidential
    are written from 2003Q4; construction from 2015Q3; the splits from
    2011Q3. The C&I and multifamily files continue across their declared
    gaps.
- **Why the banks' series do not reach the 1990s.** Every roster bank's C&I
  windows 1992Q1 to 2005Q4, measured with the build's own steps
  (`bank_book` on the same data, rules and record): 896 windows (16 banks,
  56 each). 501 are left out as "a quarter is missing", and 10 by the jump
  (Citizens). All 501 hold a quarter in which a pro forma member filed for
  the first time, in a quarter other than Q1.

  The rule: a member's flow in a non-Q1 quarter is its year-to-date less
  the quarter before's. It has no quarter before, so the flow is not
  known, and the window is missing. KeyBank has 12 such members, and they
  account for its 32 missing windows exactly. The FDIC institutions record
  (api.fdic.gov/banks/institutions, read today) gives each of the 12 an
  establishment date in the quarter of its first filing: they were new
  charters. Examples: Far West Federal Savings Bank, 7 Jun 1991; Key Bank
  USA, 5 Sep 1995. The other banks' members were not looked up.

  The rule was not changed. Whether a new charter's first year-to-date may
  be read as its flow is put to the firm as a decision. The lines do not
  wait on it: the recommendation rates the banks on lines set from the
  industry's 1991 to 2026 history, and the industry series reach 1991Q4.
- **A gap the build does not check: the record's first date.** A merger
  record is `{cert: [quarter-ends]}` and does not say the date it was
  pulled from. `peers build` does not check that it reaches back to
  `--first`. Each `pull --mergers` also writes `mergers.json` over the last
  one. A build script left in the scratchpad by the interrupted run names
  the since-2005 files, whatever first quarter it is given.

  Measured on the real cache, a 1991Q1 build reading the since-2005 record:
  - KeyBank's C&I has 14 pro forma members instead of 122;
  - its 1992Q1 to 1993Q3 and 1997Q2 to 1998Q2 windows are left out by the
    jump instead;
  - 21 of its kept windows (1993Q4 to 2005Q3) hold a quarter in which the
    record since 1990 says KeyBank absorbed a bank. Those windows mix two
    books, and no message says so.

  The run above read the since-1990 files. `stress-tool-rules.md` now copies
  each record under the date it starts from, names the files a 1991Q1 build
  must read, and says its build command, run before question 14, now needs
  `--stated-acquisitions`.
  The guard itself (the pull records the date, and the build refuses a
  first quarter before it) changes the merger file format that the consumer
  window's caches also use. It is put to the firm as a decision; nothing
  was changed for it.
- **Results.** `tests/test_from_1991.py` 5 passed and `test_peers_fdic.py`
  46 passed (scratch venv, Python 3.13, openpyxl 3.1.5, formulas 1.3.4).
  No source module was changed, so no other test file imports anything
  changed here. The rest of the suite was not run.
- **Not done.** Nothing was opened in Excel; nothing can be opened in Excel
  here. The early-1990s industry figures were not tied out to the QBP or
  the Fed's series. The commercial example book (local branch
  `commercial-example`) still says 2006Q1. It is not on this branch and was
  not changed or rebuilt. No Thresholds workbook was built from these
  series.
