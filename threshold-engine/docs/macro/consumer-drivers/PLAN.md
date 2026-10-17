# Book 2, consumer drivers: plan and objections (17 Oct 2026)

Written before anything is built, as the brief asks. Nothing here is a setting
or a verdict. Every figure is reproduced by `checks.py` beside this file, and
its output is `checks-output-2026-10-17.txt`. Its inputs are the macro pull of
17 Oct 2026 and the FDIC files in `data/industry/`.

## In short

Build it, alongside the Macrobook, as its own workbook. It reads the same pull
and Book 1's own series files. Five changes to the brief matter most:

1. **2006-2026 holds one downturn.** On Book 1's history, every pair rests on
   2008-10. The "effective sample" is the number of independent observations
   the overlapping changes are worth, and it comes out at about 2 to 6.
   Public loss series back to 1985 and 1992 already sit in the repository, and
   they give four or five episodes of rising unemployment instead of one or
   two. **I recommend testing on both:** Book 1's files, so the figures tie
   out, and the longer series, labelled as a different source.
2. **"Drivers" claims a cause the data cannot show.** With one or two
   downturns, every cyclical indicator moves with every cyclical loss measure.
   The book can show which indicators moved with losses, and how often. It
   cannot show why. I'd name it for what it shows.
3. **One test form, four-quarter changes, judged episode by episode.** Drop
   the one-quarter form. It needs a seasonal adjustment we would be inventing,
   and it doubles the ways to find a result. Replace "both halves" and
   "excluding 2008-10" with one rule: the sign must hold with each episode
   left out in turn, and there must be at least two episodes.
4. **A placebo on every pair:** the same test with the timing reversed, so the
   loss measure leads the indicator. If the reversed test reads as strongly,
   the indicator is not ahead of anything.
5. **The scatter of overlapping changes overstates the evidence.** Sixty-two
   dots that are worth about four observations look like a cloud. Draw them
   in time order, joined, so the reader sees one path.

The decisions are at the end, each with my recommendation. The note for Book
1's agent is the last section, ready to pass on.

## What I checked from your review

| Your point | What I found | How |
|---|---|---|
| Weekly mortgage rates use the nearest reading about 52 weeks back (104 readings), not what the Glossary says | **Confirmed.** 104 of the mortgage rate's 2,899 readings are compared with a reading 1 to 3 days off the date 52 weeks before. The other six weekly series never need it. The Glossary says nothing about the leeway, and says a day with no reading then has no change. That is wrong for weekly series. | `rate.py` allows 3 days for weekly series only; counted on the 17 Oct pull |
| The Glossary says each tab states which way is worse; you found none, and no citations | **Half right.** All 34 national tabs state it under "Which way is worse", in the What it is section below the charts (row 64 on most). None cites the research behind it. | Read every tab of the example workbook |
| Latest vintage | **Confirmed, by design.** The pull takes the publisher's values as they are on the day. | `pull.py` |
| Quarterly series run to 2026 Q2 | **Confirmed** for the FHFA index, FHFA's mortgage delinquency and GDP. The two SLOOS series run to 2026 Q3, from the October survey. FRED dates a quarter by its first day (2026-04-01). Book 1 dates it by its last (2026-06-30). | The pull's manifest |
| Oct 2026 monthly readings will have no 12-month change, because Oct 2025 is blank (your inference) | **Confirmed in code.** Once October 2026 is published, each monthly series' level will be October's and its change September's. The sentence names the month ("Change over 12 months to Sep 2026"), but it is easy to miss. | Rated a test series running to Oct 2026 with Oct 2025 blank |
| You could not check how the mortgage spread and house prices against income are built | They are built from the code as follows. House prices against income: the FHFA index divided by the quarter's average disposable income per person (A229RC0), in thousands. A quarter missing any month of income is left out, so 2025 Q4 is out. The spread: the weekly mortgage rate minus the 10-year yield on the same day, or the last day in the week before. Neither ratio is published by anyone, so neither can be tied to a publisher's figure. Only their inputs can. | `rate.py` `derive` |
| The Macrobook treats higher used-car prices as worse | **Confirmed.** It is the firm's setting ("higher is worse" on the change). The catalog's note gives both views. | `docs/macro/settings.json` |
| The FHFA index fell year over year in only 20 quarters, 19 of them 2007 Q4 to 2012 Q2 | **Confirmed.** The 20th is 1982 Q3. | `checks.py` §1 |
| KeyBank series start late | **Matches Book 1's own notes:** card 2013 Q4, other consumer 2015 Q4, auto 2022 Q4. | `books/consumer-public.json` on `threshold-engine-book` |
| Book 1 has five products and seven measures | **Now seven products.** It added All consumer and Credit card + Other consumer on 17 Oct. It still has seven measures. Industry delinquency runs from 2006 Q1 and charge-offs from 2006 Q4. Auto runs only from 2011 Q1. | Book 1's series list and `data/industry/` |
| You recomputed all 158 readings and they matched | Not re-checked by me. | |
| Book 1's Backtest tests a rating against the same series' next-year move | Not checked. I have not opened a Book 1 workbook. | |

## Your first-pass numbers, re-derived

| Figure | Yours | Mine | |
|---|---|---|---|
| Unemployment, card net charge-offs, 2007+ / 2012+ | 0.70 / 0.58 | 0.70 / 0.60 | reproduces |
| Unemployment, card 30-89, overlapping | 0.49 | 0.49 | reproduces |
| Unemployment, mortgage 30+, 2007+ / 2012+ | 0.88 / 0.60 | 0.92 / 0.80 | **does not reproduce** (mine is 30+ including nonaccrual) |
| Unemployment, auto 30+ | -0.15 | **+0.20** | **sign differs** |
| Effective sample, four-quarter changes | about 3-6 | 1.9-5.8 | same order |
| Card net charge-offs, one change a year | 0.77 (n=17) | 0.62-0.79 | depends on which quarter ends each year |
| Card 30-89, one change a year | about 0.30-0.33 | 0.40-0.53 | **does not reproduce** |
| Claims, card charge-offs; mortgage 30-89 and 90+ annual; the 2008-10 turning points | | not re-derived | |

The lesson is not that either set is wrong. It is that the definitions move
these figures by 0.1 to 0.4, and flip one sign: which "30+", how 2020-21 is
left out, how months become quarters, and which quarter anchors a year. So the
plan fixes every one of them in the settings before the first run, and the
book prints them.

## Objections, most consequential first

**1. One downturn.** Under a Stable band of ±0.5 typical moves, unemployment
rises in two runs in 2007-2026: 2007 Q4 to 2010 Q1, and 2024 Q2 to Q3. Under
±1 it rises in one. "Excluding 2008-10" leaves almost nothing that moved. I
expect most pairs to read Untestable on Book 1's history. That is honest, but
it is not what the brief expects. The longer series change that:

- **Credit card:** the Fed's charge-off rate from 1985 Q4 (`tests/data/cards_nco_ttm.csv`)
  holds five runs of rising unemployment: 1990-92, 2001-02, 2003, 2007-10 and
  2024-25. The together correlation is +0.67, and it stays +0.54 with 2007-10
  and the year after taken out.
- **Home equity and other consumer:** the FDIC's every-filer charge-offs from
  1992 Q4 hold four runs. Taking out 2007-10 moves them from +0.76 to +0.51
  and from +0.72 to +0.63.

For cards, 2008-10 also straddles a break. Before 2010, securitized cards were
off banks' books. Book 1 labels those quarters and measured the step in the
industry rate at about +0.9 points. The Fed's series is built from the same
filings, so it should carry the same break; I have not measured it there. Any
card result that rests on 2008-10 has to say so.

These are charge-offs only. I have not checked whether delinquency by product
exists before 2006 in the FDIC's data. Whether Book 1's pull can start
earlier is a question for its agent. The Fed's card series is commercial
banks only and seasonally adjusted. It is not Book 1's series, so it is
labelled and never spliced onto it.

**2. The name.** "Drivers" says the indicator causes the loss. One or two
downturns cannot separate cause from both moving with the economy. A placebo
pair with no mechanism (industrial production against mortgage delinquency,
say) would probably pass the same rule. The book should say what it shows:
which indicators moved with each loss measure, how often, and whether they
moved first.

**3. Overlapping changes.** A four-quarter change shares three quarters with
the next one, so 62 quarters behave like about 2 to 6 independent ones. Put the
effective sample beside every result, as you proposed, and draw the scatter as
a path in time order.

**4. A trailing-twelve-month charge-off rate has a built-in lag.** Its
four-quarter change compares the last four quarters with the four before, so
it responds about a quarter and a half after the four-quarter change in a
quarterly average does. Charge-offs that move at the same time as an indicator
therefore look as if they follow it. Part of any "Ahead" result for
charge-offs is how the rate is built. Cards also charge off at 180 days past
due, which adds a real lag behind delinquency. Delinquency is a quarter-end
stock and carries no built-in lag. The book should state the lag on every
charge-off result, rather than treat the two kinds of measure as alike.

**5. One lead for every pair.** A fixed lead of four quarters avoids hunting
for the best lag. That is right: your scan flipped sign. But revolving credit
growth (pair 6) works through loans ageing, which takes longer than a year.
Set each pair's lead in the pair list from its mechanism, before the first
run, and never pick it from the results.

**6. The quarters left out live in Book 1's workbook.** The firm types them on
Book 1's Decide tab, one product and measure at a time. They are saved only in
that workbook. Book 2 cannot read them reliably from there, so I'm asking Book
1's agent to write them to a small file (the note below). Until then Book 2
reads a file you fill in, and refuses without it. There is no default window,
and the 2020-21 window in the checks was illustrative. A change is out when
either end is out. That is Book 1's "both ends kept" rule.

**7. The verdict rule.** "Both halves" and "excluding 2008-10" are nearly the
same check. The second half of 2007-2026 is 2017-2026 less 2020-22, and in it
unemployment rose only in 2024. I'd replace both with:

- **Supported:** the expected sign in the full sample, and with each episode
  left out in turn; at least two episodes; and the reversed-timing placebo
  weaker.
- **Mixed:** the expected sign in the full sample, but not with some episode
  left out.
- **Not supported:** the wrong sign, or no correlation.
- **Untestable:** fewer than two episodes, or a loss measure that barely moves.

An episode is a run of quarters in the adverse state, with a one-quarter gap
merged. That is why 2001 Q2-2002 Q4 and 2003 Q2-Q3 count as one. The size a
correlation must reach is yours to set. I'd judge on episodes and size, and
never on p-values.

**8. Revisions.** Version 1 uses the latest values and says so on every chart.
Values as first published need FRED's vintage service, which needs the FRED
API key from the environment. That is worth adding later for the Ahead test of
the pairs that pass. Unemployment is barely revised. The saving rate is
revised a lot: October 2025 was first 3.7% and is now 4.9% (my research of
16 Oct). So I'd keep income and saving out of the pair list until vintages
exist.

**9. Months into quarters.** I'd take the quarter's average for monthly,
weekly and daily series. A quarter missing a month (2025 Q4, without October)
is left out, as house prices against income already does. That loses every
change that ends in 2025 Q4 or 2026 Q4. The alternative is FRED's Sahm rule:
average the months that were published, and mark the quarter "2 of 3 months".

**10. The Stable band.** ±0.5 typical moves gives unemployment 12 rising
quarters in two runs. ±1 gives 8 in one, which leaves the event view a single
episode. 0.5 is also Book 1's Moderate half-width. I'd keep ±0.5. The typical
move depends on the window: 0.69 points over 2007-2026, and 0.54 over
1986-2026. The book should print the one each state uses.

**11. Loss measures that cannot be tested.** Card nonaccrual moved once. It
rose from about 0.2% to 0.65% in 2008-09, then stepped down to about 0.1%
between 2013 and 2014 and has sat there since. The step looks like a change in
how banks report it, not the economy, but I have not checked. Most card
balances are charged off rather than placed on nonaccrual. Under the
two-episode rule it reads Untestable, with that reason shown. Gross and net
charge-offs move together: their four-quarter changes correlate 0.99 or more
(auto 0.96). Testing both doubles the count of results without adding
evidence, so I'd test net and put gross in the appendix.
Mortgage and home equity charge-offs near zero since 2014-18 make those
Untestable on 2007+, apart from the 2008-10 episode. Home equity is testable
on the series from 1992.

**12. Auto starts in 2011.** Its only downturn after 2011 is 2020, which is
left out. Pairs 11 and 12, and the auto half of pair 4, will be Untestable on
the FDIC data. The NY Fed's household debt report has auto flows into
delinquency from 2003, but I have not found its reuse terms.

**13. The Explore tab.** It should run the same fixed tests only, with no
pickers for lead or window. Otherwise it becomes the lag hunt the pair list
exists to prevent. It should be labelled exploratory, as you proposed.

**14. "Today's state reconciles to the Macrobook."** The reading reconciles;
the state does not. The Macrobook rates September's 12-month change against
its history. Book 2 sorts the quarter's four-quarter change into Decreasing,
Stable or Increasing. Book 2 reads the same pull file (same fingerprint) and
prints the months it averaged, so the Macrobook's latest reading can be found
among them.

**15. Every number as a formula.** Each published statistic should be a live
formula (CORREL, COUNTIFS) over the Data tab. Python computes the same, and a
test recalculates the workbook and compares, as Book 1's tests do. Excluded
quarters are grey bands, as Book 1 marks them, not hatching. Excel and
LibreOffice draw hatching differently.

## The pair list

| # | Pair | Keep? | Likely on Book 1's history | On the longer series |
|---|---|---|---|---|
| 1 | Unemployment, card early delinquency (+) | Keep | Two episodes; testable | Delinquency before 2006 not checked |
| 2 | Unemployment, card net charge-offs (+) | Keep | Two episodes; 2024's is small | Five runs; holds without 2007-10 (+0.54) |
| 3 | Initial claims, card early delinquency (+) | Keep | Three runs at ±0.5 (2023-24 are short) | Not checked |
| 4 | Gasoline, card and auto early delinquency (+) | Keep, low | The swings are 2008, 2014-15 (no delinquency move) and 2022, when delinquency was rising from its pandemic low anyway. Auto is Untestable | |
| 5 | Core CPI, card early delinquency (+) | Keep, low | Core CPI moved only in 2021-23, alongside the same post-pandemic rise. One confounded episode | |
| 6 | Revolving credit growth, card charge-offs later (+) | Keep, with its own longer lead | Growth also enlarges the balance a rate is divided by, so it can lower the rate first | |
| 7 | Unemployment, mortgage delinquency (+) | Keep | One episode in practice | |
| 8 | House price declines, mortgage delinquency and charge-offs (-) | **Untestable**, say so | One episode: 19 of the 20 falls are 2007 Q4 to 2012 Q2 | Same: the index's only other fall is 1982 Q3 |
| 9 | Mortgage rate, home equity delinquency (+) | **Use the prime rate** | Home equity lines are usually priced off prime, not the 30-year fixed rate. Prime is public on FRED (DPRIME daily from 1955, MPRIME monthly from 1949) but not in the Macrobook | |
| 10 | House prices against income, mortgage delinquency later (+) | Keep, low | A rising level; one cycle; 2025 Q4 missing | |
| 11 | Used-car price declines, auto net charge-offs (-) | Your call on direction | Untestable (auto from 2011) | The Manheim index is licensed. The CPI used-car index is public, but it is retail and trails wholesale prices |
| 12 | Unemployment, auto delinquency (+) | Keep | Untestable (auto from 2011) | NY Fed data, if its terms allow |

**Candidates not in the Macrobook,** from my research of 16 Oct, which has the
links. I could not re-check them today: FRED closed the connection.

- **Wage growth:** the Atlanta Fed tracker (monthly, 1997), ECIWAG (2001) and
  average hourly earnings (2006).
- **Saving rate:** PSAVERT, from 1959, but heavily revised.
- **Household debt service:** TDSP. It was rebuilt in 2024 and now starts in
  2005.
- **Prime rate:** MPRIME and DPRIME.
- **Student loans:** the NY Fed report. Its regime break runs 2020-25.
- **Underwriting:** the SLOOS card series (already in the Macrobook), and the
  SLOOS auto and other consumer series from 2011.

## What would be built, once you decide

- **Where it lives:** `src/threshold_engine/macro/drivers/`, tests in
  `tests/test_macro_drivers_*.py` and docs here. All three are inside my
  folders. The command is `python -m threshold_engine.macro drivers`.
- **What it reads, all read-only:** the macro pull folder and Book 1's series
  folder. It reads Book 1's files with its own small reader and touches none
  of Book 1's code. The typical yearly move is computed independently, and a
  test checks it against Book 1's `scale.py` on the same input. If either
  drifts, the test fails.
- **Two files it needs, neither with defaults.** The settings file holds the
  band, the test windows, the verdict sizes, the months-into-quarters rule and
  the missing-month rule. The pair list holds each pair's indicator, product,
  measure, expected direction, mechanism, lead and placebo. A gap in either is
  refused by name, as the Macrobook does.
- **Tabs, as you proposed:**
  - Summary
  - Drivers (renamed per decision 1)
  - Hypotheses
  - Link
  - Evidence charts
  - Flags and scorecard
  - Explore
  - Data, every series on one quarter-end calendar with its fingerprint
  - Glossary
  - Run
  - Sources

  The look is PocketBook's, with Claude Design's charts, as the Macrobook has.
- **Tie-outs, built in as tests:**
  - Each loss file's SHA-256 is printed and must equal Book 1's Run tab. I
    can't check this here: Book 1 builds its series at work into
    `books/out/series`, which is not in the repository.
  - Each indicator's quarter lists the readings it averaged, from a pull
    whose fingerprint matches the Macrobook's.
  - Every statistic is a formula that recalculates to Python's value.
- **Slices:**
  1. The two files and their refusals, and the Data tab with its tie-outs.
  2. The tests, states, episodes and effective sample, as formulas and in
     Python.
  3. The tabs.
  4. The charts.
  5. The walk, a figure tied to its publisher, Codex and the merge.

**Not done, by rule:**

- Nothing touches Book 1, its files or its outputs.
- No threshold, rating or reserve is set or fed.
- Nothing internal is used.

**Macrobook corrections, mine to make** (they do not touch Book 2):

- The weekly-change wording in the Glossary and the settings question.
- A citation for each "from the research".
- A line on the tab that names the month when a change is a month older than
  its level.

## Decisions for you

The first option in each is my recommendation.

1. **Name:** "Indicators and consumer losses", or keep "consumer drivers".
2. **Longer history:**
   - (a) Test on Book 1's files and the longer public series, side by side and
     labelled.
   - (b) Book 1's files only.
3. **Test form:**
   - (a) Four-quarter changes only.
   - (b) Add one-quarter changes for delinquency, which needs a seasonal
     adjustment we choose.
4. **Stable band:** ±0.5 typical moves, or ±1.
5. **Verdict rule:** the one in objection 7, with you setting the size a
   correlation must reach. Or the brief's rule (full sample, both halves,
   excluding 2008-10).
6. **Does Mixed get a chart?** I'd say yes, smaller, beside its reason.
7. **Quarters left out:**
   - (a) Book 1 writes its list to a file, and Book 2 reads it.
   - (b) You keep a separate list for Book 2.
8. **A quarter missing a month:** leave it out, or average the months
   published and mark it.
9. **Months into quarters:** the quarter's average, or its last reading.
10. **Used cars (pair 11):** Book 2's pair keeps the collateral view (falling
    prices are worse for auto losses) and says where it differs from the
    Macrobook. Or change the Macrobook's direction. Or drop the pair.
11. **Prime rate:**
    - (a) Add it to the Macrobook's catalog, which needs your direction for it.
    - (b) Book 2 only.
12. **Charge-offs:** net tested and gross in the appendix, or both tested.
13. **Auto:** Untestable on the FDIC data for now, or I look up the NY Fed
    report's reuse terms.
14. **Placebo pairs:** the reversed timing on every pair, plus two pairs with
    no mechanism that your SMEs name before the first run.
15. **Alongside or replace:** alongside the Macrobook, from the same pull.
16. **Level note:** kept, measured over the test window.
17. **Branch:** Book 2 is built on this branch after PR #452 merges, from a
    fresh main.

## Note for Book 1's agent (pass on as is)

> From the agent building Book 2 (consumer drivers; economic indicators against
> consumer losses, context only, never an input to Book 1). Nothing below
> changes Book 1 unless you agree to it.
>
> 1. **Read-only use of your outputs.** Book 2 will read your series files as
>    you write them (`books/out/series/*.csv`, `# notes` then `date,value`,
>    quarter-end dates). It will print each file's SHA-256 and require it to
>    equal your Run tab's. It will not import your code. It will not run
>    `book` or `peers build`, or write into `books/`.
> 2. **Names.** Book 2 uses your Product, Measure and Source names exactly as
>    on your series list. Today those are: Credit card, Mortgage, Home equity,
>    Other consumer, Auto; Net charge-offs, Gross charge-offs, 30-89 days past
>    due, Nonaccrual; Industry (every bank). Please say before renaming any.
> 3. **One additive request: the left-out quarters as a file.** Today they are
>    typed on Decide and saved only in the workbook. Would you write them, as
>    built, to a small CSV beside the series? For example,
>    `left-out.csv`: `Product,Measure,Source,first,last,why`. Book 2 would
>    read that and nothing else. If you'd rather not, Book 2 will take a list
>    the firm keeps separately.
> 4. **The typical yearly move.** Book 2 computes "1.4826 × the median absolute
>    deviation of every four-quarter change with both ends kept" itself. A test
>    of its own compares the result with your `scale.py` on the same input.
>    Please say if that definition changes.
> 5. **A question, not a request:** can the FDIC pull start before 2006 for
>    charge-offs and delinquency by product? 2006-2026 holds one downturn.
>    `tests/data/` already has FDIC every-filer home equity and other consumer
>    charge-offs from 1992 Q4.
