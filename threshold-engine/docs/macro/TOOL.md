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

- **124 series** in `src/threshold_engine/macro/catalog.py`: 91 core series
  read on their own (51 of them unemployment by state), 31 usable with care,
  and 2 inputs (income per person, the 10-year Treasury) to the two readings
  the report builds from two series (house prices against income, the
  mortgage rate over the Treasury). Each entry gives the publisher, id,
  frequency, first observation, licence, known breaks, and the report
  section that put it on the list.
- **Licensed series stay out**, as the firm chose on 21 Oct 2026: University
  of Michigan sentiment and the Atlanta Fed's wage tracker and affordability
  index. `list` names those and the rest of the group not read, with why.
- **The pull needs no API key.** It downloads every series into a folder
  named for the day and never overwrites an earlier one, so every reading can
  name the release it used. A shared file is fetched once. A failure is
  recorded and the rest still pull.
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
without the firm's settings. Its look is PocketBook's (17 Oct 2026, the firm:
*"take inspiration from pocketbook for UI look and feel"*) and its charts
follow Claude Design's for the threshold workbook (`docs/design/HANDOFF.md`).
Every number is a value written by the tool. The Dashboard is the one place
with formulas, and they only look up values written on its hidden data tab.

- **Overview:** every core series under five topics (jobs; prices and
  insurance; housing and household credit; business and the economy;
  markets and financial conditions): its latest value, where its level sits,
  its change and the month it runs to, its normal range, its direction, how
  many typical moves it is from the median, since when, and the start of its
  history. Tiles count the changes in each direction.
- **Dashboard.** The firm, 22 Oct 2026: *"a fairly simple to drive dashboard
  tab that basically lets you layer any 2 charts or something see the
  individual charts and see a chart the shows magnitude in movement"*, and,
  having opened it in Excel, *"I would really like to auto adjust the axis to
  match and also why can't I have a custom view of quarters?"*. Four boxes:
  two series, each from a list, and a From and a To quarter. Every chart on
  the tab follows them, and every axis fits what is picked and the quarters
  chosen:
  - both changes, in typical moves from each one's median, on one chart,
    with normal movement dashed: the magnitude of each one's movement on a
    scale they share;
  - both levels, as where each sits in its own history, 0% to 100% (a series
    read on its change only has no line here, and the tab says so);
  - each series on its own: its level, and its change with its normal range
    dashed.

  Over the full history the 2020 spike in jobless claims flattens the rest:
  pick quarters after it and the axis refits. Two series in different units
  are never drawn against two different axes: that misleads, so the layered
  charts use scales the two share. Time runs in years, not day numbers:
  Excel starts a day-number axis at 1900 unless the dates are close together.
  The tab is drawn month by month, a daily or weekly series at each month's
  last reading, and a line runs across a month with no reading (each series'
  own tab shows the gap). **Its formulas are the only ones in the workbook**,
  and use only functions every Excel since 2007 knows.
- **What if:** only with `--compare`; see below.
- **States:** unemployment by state, level and change, moving states first.
- **Household debt.** The firm, 22 Oct 2026: *"household as a graph on this
  that split between as it is literally reported. It's like credit cards
  mortgage and other"*, and to which, *"NY Fed debt by type"*. The NY Fed's
  own chart, Total Debt Balance and Its Composition: mortgage, home equity
  revolving, auto loan, credit card, student loan and other, stacked, in
  trillions of dollars, from 2003 Q1, with the NY Fed's own names. Beside it,
  each type's balance, share of the total, change over 12 months and
  direction, and the total's change drawn over its normal range.
- **Usable with care:** the research's usable-with-care group, read the same
  way, with why each needs care; then what had nothing to show, the rest of
  the group with why it is not read, and the credits the publishers' licences
  require.
- **One tab per series:** its level and change with the sentence behind each;
  its level drawn against its history and its change over its shaded normal
  range, the latest reading ringed; what it is, where it comes from, its
  licence and breaks; and every reading, with "no value published" where the
  publisher left a gap and "left out" for a quarter the firm left out. The
  unemployment tab also draws the Sahm reading against its 0.50 trigger.
- **State data, Not read, Glossary, Run and Sources.**

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
  `2026-10-22-3`), 2 of the 124 changes read another way, both more
  downward: mortgages 90+ days late (Increasing to Stable) and banks
  tightening nonresidential property loan standards (Stable to Decreasing).
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

**Wage growth** was asked about the same day. It is in the book already, in
the usable-with-care group: the employment cost index for wages and salaries
(+3.1% in the year to 2026 Q2) and average hourly earnings (+3.0% in the year
to September 2026). The Atlanta Fed's wage growth tracker stays out: its
terms allow reproduction only "not for commercial gain or monetary profit".

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
