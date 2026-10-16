# Economic conditions tool

A separate tool from the loss thresholds. It reads public economic series and
says where each stands against its own history, for the firm and the consumer
and commercial teams. It looks only at conditions outside management's
control. Nothing from KeyBank's books goes in.

The series are the "ready to rate" group in
[`reports/Macro risk indicators for lending.md`](reports/Macro%20risk%20indicators%20for%20lending.md),
chosen by the firm on 15 Oct 2026.

## What works now (all three slices)

- **The catalog: 85 series, 83 of them rated, and 2 readings made from
  them.** Two series are only inputs (income per person, the 10-year
  Treasury). They feed the two readings the report builds from two series:
  house prices against income, and the 30-year mortgage rate over the 10-year
  Treasury. The catalog lives in `src/threshold_engine/macro/catalog.py`.
  Each entry gives the publisher, id, frequency, first observation, licence,
  known breaks, and the report section that put it on the list. Every id was
  checked on FRED or at the publisher on 15 Oct 2026.
- **The pull: no API key.** It downloads every series into a folder named
  for the day and never overwrites an earlier one, so every rating can name
  the release it used. A shared file is fetched once. A failure is recorded
  and the rest still pull.
- **Gaps stay gaps.** FRED's "." and BLS's dash or blank are read as
  missing, never as zero. October 2025 is missing in every BLS household
  series and in CPI. November 2025 is also missing for motor vehicle
  insurance.
- **The ratings, 1 Low to 5 High.** They refuse to run until the firm has
  answered every setting.
  - Each series is rated on its **position**: the latest value against every
    value in its history.
  - It is also rated on its **change** over the firm's horizon, against every
    such change in its history.
  - A percentile is the share of that history the latest reading is at or
    above. Where lower is worse, it is the share it is at or below. The
    firm's four cut-offs turn the percentile into a rating.
  - Every rating says what drove it:
    - the value and its date;
    - the percentile, and how many readings it is measured against;
    - where that history starts;
    - which pull the data came from;
    - how long the series has held that rating;
    - where each rating starts, in the series' own units.
- **The workbook the teams read.** `rate --workbook OUT.xlsx` writes it from
  the same run, so it cannot exist without the firm's settings. Every number
  in it is a value, not a formula. It follows the threshold workbook's design
  (Claude Design's hand-off, in `keybank_style.py`): titles on paper, canvas
  headers, and the same five rating colours, as chips in the tables and as
  shaded bands behind every chart. Its tabs:
  - **Ratings:** every national series under five topics (jobs; prices and
    insurance; housing and household credit; business and the economy;
    markets and financial conditions). Each row gives the series' level and
    change, each rated, and the sentence behind the higher rating. A series'
    name opens its tab.
  - **States:** unemployment by state, level and change, worst first.
  - **One tab per series:** both ratings with what drove them; where each
    rating starts and how many readings in its history took it; its history
    drawn over the five bands, level and change; what it is, where it comes
    from and its breaks; and every reading, with "no value published" where
    the publisher left a gap. The unemployment tab also draws the Sahm
    reading against its 0.50 trigger.
  - **State data, Glossary, Run and Sources.** The glossary explains every
    term from the settings the run used. Run says when the workbook was
    built, from which pull, with which answers. Sources lists every file the
    pull fetched, with its address, licence, fetch time and SHA-256.
  - **Not rated:** only when something could not be rated, with the reason.

Run from `threshold-engine/`:

```
python -m threshold_engine.macro list
python -m threshold_engine.macro pull --cache work/macro-cache
python -m threshold_engine.macro show --cache work/macro-cache unemployment
python -m threshold_engine.macro settings-template work/macro-settings.json
python -m threshold_engine.macro rate --cache work/macro-cache --settings work/macro-settings.json --workbook work/economic-conditions.xlsx
```

`rate` prints every rating, highest first; `--json` gives the full record, and
`--vintage 2026-10-15` rates an earlier pull. Until every answer is filled in,
it prints `REFUSED:` with each missing answer named, and exits 2.

## How each series is read

These follow the report's rules by type of series. Each is a call the firm can
reverse for any series.

- **Twelve series are rated on their change only.** They are payrolls, CPI
  and core CPI, gasoline, motor and home insurance prices, used cars, house
  prices, revolving credit, real GDP, industrial production and CRE prices.
  Each is a level that climbs over the decades with prices and the economy,
  so it sits near the top of its own history in almost every year. Its place
  there says nothing. The report rates these on their change: "PPI
  homeowner's insurance (1998, change over the year)", "G.19 revolving credit
  growth".
- **A change is counted in points or in percent.** Points are used for a
  rate, a spread or an index around zero. Percent of the earlier reading is
  used for a level that grows, and for jobless claims.
- **Valuation is read only for house prices.** It is house prices against
  income per person: the FHFA index divided by the quarter's average
  disposable income per person. The tool reads no measure of what commercial
  property is worth against rents or income.
- **The mortgage spread: wider is worse.** The Fed's scenario guide sizes a
  severe move as a spread up 0.70 to 1.60 points, or at 3 points or more,
  whichever is higher.
- **Changes are counted as FRED counts them.** Monthly and quarterly series
  compare the same month a year (or horizon) earlier. Weekly and daily series
  count whole weeks, so 12 months is 52 weeks. A daily reading is compared
  with the same weekday. A day with no reading that many weeks before has no
  change, and nothing is filled in.
- **The Sahm reading is shown beside the national unemployment rate, never
  rated.** It is the 3-month average minus its lowest 3-month average in the
  12 months before. Where a month has no value (October 2025), the average is
  taken from the two months that do.

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

## Walked and tied out (16 Oct 2026)

- **Walked:** `walkthrough/refresh-2026-10-16/PROCEDURE-refresh-2026-10-16.pdf` is the monthly refresh,
  step by step with screenshots. `walkthrough/WALKTHROUGH-DEFECTS.md` lists what the walk found (13, against
  73 passing tests that caught none; 11 fixed, 2 open).
- **Tied out:** `tie-out/gasoline-change-2026-10-16/TIE-OUT-gasoline-change-2026-10-16.pdf` traces the Ratings
  tab's top reading, gasoline's change over a year, +41.49%, rated 4, from the cell to EIA's own table and
  history file, worked again by hand and by spreadsheet formula. It ties three more of the tab's figures to
  BLS, FRED and FHFA. All 4 of 4 tied.

## The firm's settings (16 Oct 2026)

The firm: *"Good with those recommendations"*. The answers are in
[`settings.json`](settings.json); the blank form is
[`settings-template.json`](settings-template.json). Every setting is
required and none has a default; change an answer in `settings.json` and
every rating follows.

1. Ratings 2, 3, 4 and 5 start at the 50th, 75th, 90th and 95th percentiles.
2. A reading exactly on a cut-off takes the worse rating.
3. Each reading is measured against the full history the publisher has, and
   its start is shown.
4. A change is counted over 12 months, and the Sahm reading is shown.
5. Every series is also rated on its change.
6. The nine directions the research leaves open:
   - prices (all items, core, used cars): a faster rise is worse;
   - house prices: a fall is worse; against income, a high level is worse
     and a fall is worse;
   - the mortgage rate: higher is worse, and a rise is worse;
   - revolving credit: faster growth is worse;
   - CRE prices: a fall is worse;
   - business loan demand: weaker is worse, and a fall is worse.

## Not read yet, and why

- **NY Fed recession probability.** It is published only as an old-format
  Excel file, which needs a reader the tool does not have. The 10-year minus
  3-month spread it is built from is read.
- **NY Fed flows into delinquency.** Its reuse terms are not confirmed.
- **FHFA mortgage delinquency by state.** Not wired in yet; the national and
  loan-type figures are.

## Gaps in the workbook

A month with no value published is an empty cell, with "no value published"
beside it, and every chart leaves a gap there. The first version wrote the
word "missing" in the cell instead. Opened in LibreOffice, the unemployment
chart then dropped to zero in October 2025, the error the tool exists to
prevent. A test now fails if a gap is written as anything but an empty cell,
or if a chart draws one.
