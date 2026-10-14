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
- **Not handled:** where KeyBank absorbed a bank under the same parent, its
  filing can repeat that bank's year to date; reconcile flags such a
  remainder and does not explain it (the notes say so). The FDIC record
  has one in range: certificate 16004 merged into KeyBank effective 8 Oct
  2016 (code 223). Whether 2016Q4's year to date repeats it was not
  checked. No run-off note on the internal series yet.
- `tests/test_internal.py`: 86 passed. Full suite: 914 passed, 0 failed
  (49 minutes).
