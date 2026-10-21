# Economic conditions tool

A separate tool from the loss thresholds. It reads public economic series and
says where each stands against its own history, for the firm and the consumer
and commercial teams. It looks only at conditions outside management's
control. Nothing from KeyBank's books goes in.

The rated series are the "ready to rate" group in
[`reports/Macro risk indicators for lending.md`](reports/Macro%20risk%20indicators%20for%20lending.md),
chosen by the firm on 15 Oct 2026. The report's next group, "usable with
care", was added on 21 Oct 2026, shown and never rated (the firm: *"expand
what we keep in this book after all - even if not super useful"*).

## What works now (all three slices)

- **The catalog: 85 series, 83 of them rated, and 2 readings made from
  them.** Two series are only inputs (income per person, the 10-year
  Treasury). They feed the two readings the report builds from two series:
  house prices against income, and the 30-year mortgage rate over the 10-year
  Treasury. The catalog lives in `src/threshold_engine/macro/catalog.py`.
  Each entry gives the publisher, id, frequency, first observation, licence,
  known breaks, and the report section that put it on the list. Every id was
  checked on FRED or at the publisher on 15 Oct 2026.
- **30 more series, shown and never rated** (21 Oct 2026): the report's
  "usable with care" group, as far as the tool can read it. They are short,
  broken or heavily revised: underemployment, job openings, layoffs and quits,
  temporary help, two wage measures, real income with and without transfers,
  the saving rate, the three debt service ratios, the large-bank minimum
  payment share, the NY Fed survey's expected chance of missing a debt
  payment, the auto, other consumer and three CRE lending-standards series,
  new homes' months' supply, equipment orders, business applications, three
  regional manufacturing surveys, customs duties and two policy uncertainty
  indexes. None has a direction of stress and the settings ask nothing about
  them, so the firm's settings stay as they are. Each is described, not
  rated: its latest reading, and the share of the readings in the same
  history window it is at or above, counted from the lowest. That says where
  it sits, not whether that is good or bad. The ids, first readings and
  licences come from the report (14-16 Oct 2026); the live pull that checks
  them is in the log. **Licensed series stay out**, as the firm chose:
  University of Michigan sentiment (no redistribution) and the Atlanta Fed's
  wage tracker and affordability index (its terms allow reproduction only
  "not for commercial gain or monetary profit"). `list` names those and the
  rest of the group that is not read, with why.
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
  in it is a value, not a formula.
  - **Its look is PocketBook's** (17 Oct 2026, the firm: *"take inspiration
    from pocketbook for UI look and feel"*): a dark title band with the red
    rule under it, one "How this tab works" note per tab that folds away,
    tiles for the headline figures, dark section bands, and tabs coloured for
    what they hold (results dark, the record grey).
  - **Its charts are Claude Design's**, from the threshold workbook's
    hand-off (`docs/design/HANDOFF.md`, in `keybank_style.py`): the five
    rating colours shaded behind every history, the history in ink, the
    latest reading ringed and labelled. A what-if's cut-offs are dashed
    lines, as that workbook draws "what happens if". The years along the
    bottom are a date axis, one label every 1, 2, 5 or 10 years.
  - Its tabs:
  - **Ratings:** every national series under five topics (jobs; prices and
    insurance; housing and household credit; business and the economy;
    markets and financial conditions). Each row gives the series' level and
    change, each rated, and the sentence behind the higher rating. A series'
    name opens its tab.
  - **What if:** only with `--compare`; see below.
  - **States:** unemployment by state, level and change, worst first.
  - **Shown, not rated:** every shown series under four topics, with its
    latest reading, where its level and change sit in its history, and why it
    is only usable with care; then what had nothing to show, the rest of the
    group with why it is not read, and the credit the NY Fed's licence
    requires for its survey data.
  - **One tab per series:** both ratings with what drove them; where each
    rating starts and how many readings in its history took it; its history
    drawn over the five bands, level and change; what it is, where it comes
    from and its breaks; and every reading, with "no value published" where
    the publisher left a gap. The unemployment tab also draws the Sahm
    reading against its 0.50 trigger.
  - **One tab per shown series:** its tab is slate. It gives the latest level
    and change with where each sits, the history drawn in ink with the latest
    reading ringed and no bands, and what it is, its licence, why it needs
    care and its breaks.
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
python -m threshold_engine.macro rate --cache work/macro-cache --settings docs/macro/settings.json --compare docs/macro/what-if-30-years.json --workbook work/what-if.xlsx
```

`rate` prints every rating, highest first; `--json` gives the full record, and
`--vintage 2026-10-15` rates an earlier pull. Until every answer is filled in,
it prints `REFUSED:` with each missing answer named, and exits 2.

## What if: two sets of settings side by side (17 Oct 2026)

The walk found it (W12): asking what changes if each reading is measured
against the last 30 years took a script written by hand. The firm, 17 Oct
2026, to building it: *"i set yes"*.

- **`rate --compare WHAT-IF.json`** rates the same pull a second time, with a
  second settings file. It prints what differs between the two files, the
  totals, and every reading whose rating moves, with both percentiles and
  both histories.
- **Both files must be complete.** A what-if with a gap refuses, naming its
  file and the gap, exactly as the firm's own does. Neither file is changed,
  and nothing is chosen: the tool reports, the firm decides.
- **With `--workbook`**, the workbook gains:
  - a **What if** tab, second: what differs, a grid of each national
    reading's rating as you have it against its rating under the what-if,
    the counts at each rating drawn side by side, every reading that moves
    (national, then states), and the readings at the same rating, folded away
    so the count can be checked;
  - a **What if** column on Ratings and States, saying which readings move;
  - on each series' tab, the what-if rating beside each rating, where its
    ratings start, and its cut-offs drawn as dashed lines over the years its
    history covers. A change over a different number of months is a
    different measure, so it is not drawn on the same chart.
- **The example** (`examples/`): the firm's settings against
  `what-if-30-years.json`, the same answers with history set to the last 30
  years. From the pull of 17 Oct 2026, 13 of 158 readings move: 11 up, 2
  down. Seven are national, as the walk's hand-written script found on 16
  Oct, including the mortgage rate's level, from 2 to 4 (52.5% of 2,899
  weeks since 1971; 91.4% of 1,566 since 1996).

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
  73 passing tests that caught none; 12 fixed, W12 built on 17 Oct; W1 open).
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

The usable-with-care group's own list is in the catalog's `NOT_SHOWN` and
printed by `list`. The ready-to-rate group's:

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
