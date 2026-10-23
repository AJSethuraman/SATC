# Economic conditions tool

A separate tool from the loss thresholds. It reads public economic series and
says where each stands against its own history, for the firm and the consumer
and commercial teams. It looks only at conditions outside management's
control. Nothing from KeyBank's books goes in.

**Nothing is rated.** The firm, 22 Oct 2026: *"We are not rating these. At
most these are directional"*, and to taking the 1 to 5 ratings out of every
series, *"Yes direction only and ways to establish normal movement"*. Each
series now shows two things: where its level sits in its own history, and
whether its change is **Increasing, Stable or Decreasing** against its own
normal movement.

The core series are the "ready to rate" group in
[`reports/Macro risk indicators for lending.md`](reports/Macro%20risk%20indicators%20for%20lending.md),
chosen by the firm on 15 Oct 2026, with the prime rate and the NY Fed's
household debt by type added on 22 Oct. The report's next group, "usable with
care", was added on 21 Oct 2026 (the firm: *"expand what we keep in this book
after all - even if not super useful"*) and is read the same way.

## The catalog and the pull

- **144 series** in `src/threshold_engine/macro/catalog.py`: 107 core series
  read on their own (51 of them unemployment by state and 16 of them bank
  credit), 33 usable with care,
  and 4 inputs to three readings built from two series. Two are the
  report's: house prices against income (from income per person) and the
  mortgage rate over the Treasury (from the 10-year yield). The third is
  wages after inflation, usable with care (from the wage index and consumer
  prices, both before seasonal adjustment). Each entry gives the publisher, id,
  frequency, first observation, licence, known breaks, and the report
  section that put it on the list.
- **Licensed series stay out**, as the firm chose on 21 Oct 2026: University
  of Michigan sentiment and the Atlanta Fed's affordability index. The
  Atlanta Fed's wage tracker was out too until 22 Oct 2026, when FRED's page
  was found to tag it Public Domain: Citation Requested; it is now read from
  FRED, as every FRED series is. `list` names those and the rest of the group not read, with why.
- **The pull needs no API key.** It downloads every series into a folder
  named for the day and never overwrites an earlier one, so every reading can
  name the release it used. A shared file is fetched once. A failure is
  recorded and the rest still pull.
- **Bank credit is built, not downloaded** (added 23 Oct 2026; the firm:
  *"Yes, from FDIC each pull"*). Each product's net charge-offs (the past
  four quarters' over the average balance) and its loans 30+ days past due
  including nonaccrual, for credit card, other consumer, mortgage and home
  equity, every FDIC filer added together (all banks) and KeyBank on its own
  (certificate 17534). The threshold engine's own peers pull fills an FDIC
  cache (`CACHE/fdic`, every filer from 2006 Q1; a quarter on disk is never
  fetched again) and its own peers build makes the series, under the
  settings the consumer book records (`books/consumer-public.json`: jump
  0.25, acquisition share 0.05, KeyBank pro forma with the banks it
  absorbed), so every figure is the one the threshold workbook shows. The 16
  series go into the day's folder as one file, `fdic_credit.json`, with the
  build's own notes, which each series' tab prints. The build reads the
  book and the roster where they are kept, in `threshold-engine/`: an
  installed copy of the tool (`pip install .`) finds them when it is run
  from there, and refuses elsewhere, saying what it needs. On 23 Oct 2026 the first
  fetch of 82 quarters (about 230 MB) took about 6 minutes and the build about
  9; later pulls fetch only a new quarter, and the build runs each time. The quarter
  just ended is tried first and, before the FDIC publishes it, the one
  before. Tied out: the industry's card net charge-offs (3.4765% in 2006 Q4)
  and card 30+ (3.7503% in 2006 Q1) match the threshold engine's committed
  industry files to the last digit, and KeyBank's card net charge-offs for
  2026 Q2 are 3.76%, as the firm's Excel copy had them. The FDIC's website
  policies page, read 23 Oct 2026, states no terms of reuse for its own data.
- **Gaps stay gaps.** FRED's "." and BLS's dash or blank are read as missing,
  never as zero. October 2025 is missing in every BLS household series and in
  CPI.

## What each series shows

- **Level: at or above.** The latest reading, and the share of every reading
  in the series' history that it is at or above, counted from the lowest:
  100% is the highest it has been. It says where the reading sits, not
  whether that is good or bad. A level that climbs over the decades with
  prices and the economy (payrolls, prices, GDP, credit balances) sits near
  the top of its own history in almost every year, so its place there says
  nothing; those are read on their change only, as the report reads them.
- **Change, and its normal movement.** The change over the firm's horizon (12
  months), in points for a rate, a spread or an index and in percent for a
  level that grows. Normal movement is the median of every such change in
  the series' history, plus or minus one **typical move**: 1.4826 times the
  median distance of the changes from their median. It is the measure the
  loss thresholds use for ordinary year-to-year movement
  (`src/threshold_engine/scale.py`), and a spike does not widen it, as it
  would a standard deviation. The firm chose it on 22 Oct 2026: *"Typical
  move (Recommended)"*.
- **Direction.** Inside the normal range the change reads **Stable**; at or
  past its top, **Increasing**; at or past its bottom, **Decreasing**. A
  change exactly on an edge reads as moving, as a tie went to the warning
  when the tool rated (the firm's settings of 16 Oct 2026). For a series
  that usually grows, such as prices, Increasing means growing faster than
  it normally does, and Decreasing slower. None of the three says better or
  worse.
- **Typical moves**, as a number: how far the change is from the median
  change, in typical moves. It puts every series' movement on one scale.
- **Since:** the first of the unbroken run of changes, up to the latest, that
  read the same way, each against the same normal range. The report asks for
  it because of 2022-25: a one-month crossing should look like one.
- **In the research:** where the report says which way a series signals
  stress, its tab says so, as a fact about the research. It changes no
  reading.

A series with too little history for a normal range (one change), or whose
changes are so regular that half of them equal the median (a typical move of
zero), is not read, and the Not read tab says why.

## The firm's settings

Every setting is required and none has a default; the tool refuses, naming
each missing answer, until all are in. The answers are in
[`settings.json`](settings.json); the blank form is
[`settings-template.json`](settings-template.json). A settings file that
still answers a question the tool no longer asks (the cut-offs, the
directions) is refused, with why.

| Setting | The firm's answer | When |
|---|---|---|
| History each reading is measured against | the full history | 16 Oct 2026, "Good with those recommendations" |
| Change counted over | 12 months | 16 Oct 2026 |
| Sahm reading shown | yes | 16 Oct 2026 |
| Normal movement | the median change plus or minus one typical move | 22 Oct 2026, "Typical move (Recommended)" |
| Quarters left out | none | 22 Oct 2026, "None yet" |
| Readings a chart may leave off its axis | 1% at each end | 22 Oct 2026, "I will take recommended ways of viewing" |

**Quarters left out.** The firm, 22 Oct 2026: *"we need to be able up
exclude quarters we choose. Not an option"*. List them in `settings.json` as
quarters or runs, `["2020Q2-2021Q2"]`. A reading in a quarter left out is not
measured against and not drawn; a change with either end in one is not
counted. Every tab says what was left out. If the latest reading itself falls
in a quarter left out, the tool reads the latest one that does not and says
so; it never presents the older reading as current.

**The axis cut.** The recommendation the firm took: each chart's axis may
leave off up to 1% of its readings at each end, so a spike such as the 2020
jobless claims does not flatten the rest. A note under the chart names the
furthest reading off it and its date. The latest reading and the normal range
always stay on, and no reading changes. The option the firm was shown said
"the top 1%"; the tool applies it at each end, because a change runs both
ways. Set it to 0 to keep every reading on every chart.

## The zoom

The firm, 22 Oct 2026: *"i want to be able to simply change the view of
quarters not change cutoffs or averages or anything but to literally zoom in
on a set of quarters"*, and on where to set it, *"Name it, then rebuild"*.
The Dashboard's From and To boxes do the same live, for any two series; the
series tabs are values only, so their zoom is set when the workbook is built,
and it also sets the quarters the Dashboard opens on.

```
python -m threshold_engine.macro read --cache work/macro-cache --settings docs/macro/settings.json --workbook work/zoomed.xlsx --zoom 2019Q1:2026Q3
```

Every chart is drawn over those quarters only; every reading, median and
normal range is worked out exactly as without it (a test compares the two
runs). The tables keep the whole history, and the Run tab records the zoom.

## The workbook

`read --workbook OUT.xlsx` writes it from the same run, so it cannot exist
without the firm's settings. **Its design is Claude Design's round 1**
(`design/round-1/`: the mock, the build spec, the tokens and the note to the
builder), asked for on 22 Oct 2026 (*"I want a zip to hand off to an agent to
allow them to make a design for this workbook so you can apply it"*). One
grammar on every tab: a dark title band with the red rule, tiles of figures
under the labels the tables use, section names over an ink rule, canvas
column headers, a direction bold on mist whichever way it moves, and the
method note ("How this tab works") at the foot of each tab, folded away.
Every number is a value written by the tool. The Dashboard is the one place
with formulas, and they only look up values written on its hidden data tab.

The tab bar follows the Overview: Overview, Dashboard, What if, then every
core series in the Overview's order (tabs slate and stone in turn, by topic),
States, Usable with care and its series (mist), then State data, Glossary,
Not read, Run and Sources.

- **Overview:** every core series under six topics (jobs; prices and
  insurance; housing and household credit; business and the economy;
  markets and financial conditions; bank credit quality, all banks and
  KeyBank), under one frozen header: its latest
  value, where its level sits, its change (and the month it runs to, when
  that is not the latest's), its normal range, its direction, how many typical
  moves it is from the median, since when, and the start of its history.
  Household debt shows its total, the six types folded away under it. Tiles
  count the changes in each direction.
- **Dashboard: whether two series move together, and whether one leads.**
  The firm, 22 Oct 2026, asked for a tab to layer any two charts and see
  the size of their movement; on 23 Oct 2026, having worked a comparison of
  two series with another agent in Excel, *"i want to work this to being the
  dashboard because it's the same info but further"*, keeping the answer
  line, the same-time r and a condensed lead table, in KeyBank's colours
  (*"not a huge fan of the blue and orange"*). One screen:
  - four boxes in a row: two series, each from a list of every series, and
    a From and a To quarter;
  - both picks' readings in the Overview's columns;
  - **one line that answers**: whether the changes move together (or
    opposite), at which lead, and whether that holds, then the same-time r;
    bold on mist when a lead holds, plain when none does;
  - **at the same time**, on every reading the two share in the quarters
    chosen: r, the readings, the effective readings and p. Neighbouring
    readings repeat most of their data (a trailing four-quarter rate above
    all), so the effective readings are n x (1 - r1 x r2) / (1 + r1 x r2),
    r1 and r2 each series' correlation with its own previous reading, never
    more than n, and p is Student's t on them, two-tailed;
  - **does one lead the other**: for each lead the settings name (-24 to +36
    months, every 6), the first series' change beside the second's that many
    months later, on one reading a year from four starting points a quarter
    apart. A year's change can run on into the next, so each starting
    point's p is on its effective pairs, r1 and r2 then each series'
    correlation with its own change a year earlier. r is the average of the
    four, pairs the fewest, and a lead holds when all four agree in sign and
    each passes p < 0.05 divided by the number of leads tested. A lead with
    fewer than 6 pairs, or too few effective pairs for a p, is not tested
    and does not count among them. The strongest lead is bold on mist;
  - **both changes drawn**, in typical moves from each one's median, normal
    movement dashed, in KeyBank ink and red. Past the firm's cut (1% at each
    end of each series' history) a reading is left off the chart by formula
    and a triangle marks it; the tests use every reading.

  The levels-together chart and each pick's own small charts went: each
  series' own tab has those. It opens on the unemployment rate against card
  net charge-offs for all banks. **Its formulas are the only ones in the
  workbook**, and use only functions every Excel since 2007 knows (CORREL,
  TDIST and SUMPRODUCT among them). Checked on 23 Oct 2026: recalculated in
  LibreOffice, every r, pair count, effective count, p and verdict matched
  an independent computation from the values on the hidden data tab to 5e-13.
- **What if:** only with `--compare`; see below.
- **States:** unemployment by state, level and change, moving states first,
  in two tables side by side so all 51 fit on one screen.
- **Household debt.** The firm, 22 Oct 2026: *"household as a graph on this
  that split between as it is literally reported. It's like credit cards
  mortgage and other"*, and to which, *"NY Fed debt by type"*. The NY Fed's
  own chart, Total Debt Balance and Its Composition: mortgage, home equity
  revolving, auto loan, credit card, student loan and other, stacked, in
  trillions of dollars, from 2003 Q1, with the NY Fed's own names. Beside it,
  each type's balance, share of the total, change over 12 months and
  direction, and under that the total's change drawn over its normal range.
- **Usable with care:** the research's usable-with-care group, in the
  Overview's columns, with why each needs care under its name; then what had
  nothing to show, the rest of the group with why it is not read, and the
  credits the publishers' licences require.
- **One tab per series:** tiles of its level (with the lowest and highest
  in its history) and its change (with its normal range, typical moves,
  since and history from); its level drawn against its history and its change
  over its shaded normal range side by side, the latest reading ringed and a
  triangle at the edge for each reading off the axis (a series read on its
  change only has one chart, the full width); what it is, where it comes
  from, its licence and breaks, and the tool's two sentences behind the
  tiles; and every reading in columns AA to AD, with "no value published"
  where the publisher left a gap and "left out" for a quarter the firm left
  out. The unemployment tab adds the Sahm reading in a tile and its chart
  against the 0.50 trigger.
- **State data, Not read, Glossary, Run and Sources**, on one template.

Run from `threshold-engine/`:

```
python -m threshold_engine.macro list
python -m threshold_engine.macro pull --cache work/macro-cache
python -m threshold_engine.macro show --cache work/macro-cache unemployment
python -m threshold_engine.macro settings-template work/macro-settings.json
python -m threshold_engine.macro read --cache work/macro-cache --settings docs/macro/settings.json --workbook work/economic-conditions.xlsx
python -m threshold_engine.macro read --cache work/macro-cache --settings docs/macro/settings.json --compare docs/macro/what-if-pandemic-left-out.json --workbook work/what-if.xlsx
```

`read` prints every reading, the moving ones first; `--json` gives the full
record, and `--vintage 2026-10-15` reads an earlier pull. Until every answer
is filled in, it prints `REFUSED:` with each missing answer named, and exits
2. Before 22 Oct 2026 the command was `rate`.

## What if: two sets of settings side by side (17 Oct 2026)

The walk found it (W12): asking what changes if each reading is measured
against the last 30 years took a script written by hand. The firm, 17 Oct
2026, to building it: *"i set yes"*.

- **`read --compare WHAT-IF.json`** reads the same pull a second time, with a
  second settings file. It prints what differs between the two files, the
  totals, and every change whose direction moves, with both typical moves
  and both histories.
- **Both files must be complete.** A what-if with a gap refuses, naming its
  file and the gap. Neither file is changed, and nothing is chosen: the tool
  reports, the firm decides.
- **With `--workbook`**, the workbook gains a **What if** tab after the
  Dashboard (what differs, a grid of each national change's direction as you
  have it against the what-if's, every change that reads another way, and
  the rest folded away), a **What if** column on the Overview and States,
  and the what-if's normal range dashed on each change chart, where both
  count the change over the same months.
- **The example** (`examples/`): the firm's settings against
  `what-if-pandemic-left-out.json`, the same answers with 2020 Q2 to 2021 Q2
  left out of every history. From the pull of 22 Oct 2026 (folder
  `2026-10-23`), 4 of the 143 changes read another way, all more
  downward: initial jobless claims (Stable to Decreasing), mortgages 90+
  days late (Increasing to Stable), banks tightening nonresidential property
  loan standards (Stable to Decreasing) and wages after inflation (Stable to
  Decreasing).
  So few move because the normal range rests on medians, which the pandemic
  spike hardly moves. `what-if-30-years.json` is kept as a second example.

## How each series is read

These follow the report's rules by type of series.

- **A change is counted in points or in percent.** Points are used for a
  rate, a spread or an index around zero. Percent of the earlier reading is
  used for a level that grows, and for jobless claims.
- **Valuation is read only for house prices.** It is house prices against
  income per person: the FHFA index divided by the quarter's average
  disposable income per person. The tool reads no measure of what commercial
  property is worth against rents or income.
- **Changes are counted as FRED counts them.** Monthly and quarterly series
  compare the same month a year (or horizon) earlier. Weekly and daily series
  count whole weeks, so 12 months is 52 weeks. A daily reading is compared
  with the same weekday. A day with no reading that many weeks before has no
  change, and nothing is filled in.
- **A daily series has no reading on a holiday.** Its line joins the days
  either side; a month or a week with no value still leaves a gap.
- **The Sahm reading is shown beside the national unemployment rate, never
  used to read it.** It is the 3-month average minus its lowest 3-month
  average in the 12 months before. Where a month has no value (October 2025),
  the average is taken from the two months that do.

## The series added on 22 Oct 2026

- **The prime rate.** The firm: *"how do we not have the prime interest
  rate as a graph on this?"* The report names it (FRED `MPRIME`, the free
  benchmark for business-loan rates since the Fed's survey of them ended in
  2017) but put it in none of its three groups, so the catalog, built from
  those groups, never took it. It is now read daily from FRED `DPRIME`
  (Board of Governors, H.15), from 4 Aug 1955, tagged *Public Domain:
  Citation Requested*: all checked on FRED's series page on 22 Oct 2026. On
  13 Oct 2026 it was 7.00%, against 7.25% a year before.
- **Household debt by type.** The NY Fed's Quarterly Report on Household Debt
  and Credit. Its data file is named for the quarter it runs to, so the pull
  reads the link on the report's own page
  (`HHD_C_Report_2026Q2` on 22 Oct 2026; a name guessed for the next quarter
  was served as a page of HTML). Its terms of use (last updated 6/9/2023),
  read 22 Oct 2026, license use, copying and distribution for personal or
  business purposes and name the attribution for these data: *"New York Fed
  Consumer Credit Panel / Equifax"*. That settles the question the research
  left open; the workbook carries the attribution and labels its own
  arithmetic as not the NY Fed's. In 2026 Q2 the total was $18.77 trillion,
  credit cards $1.263 trillion.
- **People with a new bankruptcy on their credit report**, added 23 Oct 2026
  (the firm: *"build it"*), usable with care. The same NY Fed file, its
  Page 17 Data, in thousands of people a quarter from 2003 Q1. The panel is
  "constructed from a nationally representative random sample of Equifax
  credit report data" (the NY Fed's background page). It counts people, not
  court cases. The bankruptcy law of April 2005 (Public Law 109-8) took
  effect on 17 October 2005 and people rushed to file before it: 948.6
  thousand in 2005 Q4, 213.9 thousand the next quarter. That is marked as a
  break, not left out, because leaving quarters out takes them out of every
  series; the normal range barely moves without it (-23.2% to +19.2% over
  the full history, -22.4% to +19.1% from 2007). In 2026 Q2: 136.8 thousand,
  +4.2% on a year before, Stable; its level at or above 25.5% of its
  history. US Courts' own filing counts are still not read: PDF tables only.

**Wage growth** was asked about the same day. Four measures sit in the
usable-with-care group:

- the employment cost index for private wages and salaries, +3.1% in the
  year to 2026 Q2, as BLS's June 2026 release prints it;
- the same index **after inflation**: divided by consumer prices in the
  quarter's last month, both before seasonal adjustment. Worked this way,
  five of BLS's six figures after inflation in that release (private and
  all civilian workers; June 2025, March and June 2026) come out to the
  decimal. The sixth, private for June 2025, is 0.851% against BLS's 0.8%;
- average hourly earnings, +3.0% in the year to September 2026;
- the Atlanta Fed's wage growth tracker, the median of each person's own
  wage change, 3-month average: 3.9% in September 2026, read from FRED,
  which tags it Public Domain: Citation Requested. The Atlanta Fed's own
  site terms allow reproduction only "not for commercial gain or monetary
  profit"; the tool reads it from FRED under FRED's tag.

## Checked against the publishers' own figures (15 Oct 2026)

- **The Sahm reading:** all 931 months agree with FRED's `SAHMCURRENT`,
  including October and November 2025.
- **The change over 12 months:** FRED computes its own change from a year
  ago. The tool agrees with it on every date for 13 series:
  - unemployment, payrolls, CPI, real GDP, house prices, revolving credit;
  - initial and continuing claims, the mortgage rate, gasoline, NFCI;
  - the 10-year minus 3-month spread, and the 10-year yield.

  The one exception is a rounding tie. For gasoline in the week of 4 Mar
  2019, the exact change is −5.390625%: FRED rounds it to −5.39063, the tool
  to −5.39062.
- **The first version disagreed, and was changed.** It counted calendar
  dates for weekly and daily series. It differed from FRED in 2 holiday weeks
  of the mortgage rate, and on most days of the yield curve. FRED counts
  whole weeks, and so does the tool now.

## Walked and tied out (16 Oct 2026, when the tool rated)

- **Walked:** `walkthrough/refresh-2026-10-16/PROCEDURE-refresh-2026-10-16.pdf` is the monthly refresh as it
  was then, step by step with screenshots. `walkthrough/WALKTHROUGH-DEFECTS.md` lists what the walk found.
- **Tied out:** `tie-out/gasoline-change-2026-10-16/TIE-OUT-gasoline-change-2026-10-16.pdf` traces gasoline's
  change over a year, +41.49%, from the cell to EIA's own table and history file. The change is worked out
  the same way now; only its rating is gone.

## Not read yet, and why

The usable-with-care group's own list is in the catalog's `CARE_NOT_READ`
and printed by `list`. The ready-to-rate group's:

- **NY Fed recession probability.** It is published only as an old-format
  Excel file, which needs a reader the tool does not have. The 10-year minus
  3-month spread it is built from is read.
- **NY Fed flows into delinquency.** Its terms now allow it (read 22 Oct
  2026); the firm chose the same report's debt by type first.
- **FHFA mortgage delinquency by state.** Not wired in yet; the national and
  loan-type figures are.

## Gaps in the workbook

A month with no value published is an empty cell, with "no value published"
beside it, and every chart leaves a gap there. The first version wrote the
word "missing" in the cell instead. Opened in LibreOffice, the unemployment
chart then dropped to zero in October 2025, the error the tool exists to
prevent. A test now fails if a gap is written as anything but an empty cell.
