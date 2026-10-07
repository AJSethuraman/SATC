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
