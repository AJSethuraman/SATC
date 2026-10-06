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
