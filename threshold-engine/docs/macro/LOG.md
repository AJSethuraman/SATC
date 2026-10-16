# Macro helper log

The fourth helper: economic data that explains, or warns early of, what loan
losses do. Kept here, not in the main LOG.md, because another session is
building in threshold-engine on `threshold-engine-design`. This work writes
only under `src/threshold_engine/macro/`, `tests/test_macro_*.py` and
`docs/macro/`.

## 14 October 2026, the proposal

The firm: *"design a fourth helper: economic data (unemployment and similar)
that explains, or gives early warning of, what loan losses do"*, and
*"discuss first; build nothing until I choose."*

**Nothing is built.** The proposal is a Claude Doc, *Economic Data as a
Fourth Helper: Proposal*
(https://claude.ai/code/artifact/1e9a8201-71b5-47bd-bc8f-80a48109b3e4), with a
copy in this folder (`PROPOSAL.md`). The scripts and data behind every figure
in it are `analysis/` and `data/`.

**Recommended:** option C, a stress scenario. The firm names a recession by
its rise in unemployment. The tool applies how far each product's losses rose
per point of unemployment in past recessions, as a fourth suggestion for
where 5 begins. On cards, the Fed's 2026 rise (+5.5 points) from the middle
of the kept history (3.76%) gives 7.5–10.6% added, 8.3–11.1% scaled. Not B:
on the public data, a level of unemployment does not map to a level of
losses. A, a warning beside the chart, is context to add later.

What the public data showed:

- **Cards.** Card losses rose 0.68, 1.03 and 1.25 points per point of
  unemployment rise in 1990–92, 2001–03 and 2007–10. In 2020 the rise was
  9.4 points and losses did not rise: they fell from 3.76% (2020Q2) to 1.76%
  (2022Q2). Fitted
  quarter by quarter on 1985–2007, a model got 2008–2019's direction
  (correlation 0.77 two quarters ahead) but not its size (2.6 forecast
  against 3.9 actual), and was wrong in sign on 2020–2026.
- **Other consumer.** 0.27 and 0.40 per point in 2001 and 2008; almost no fit
  quarter by quarter.
- **Mortgage and home equity.** House prices matched them three and four
  quarters later (correlation −0.85, −0.88, to 2019), but on one episode
  only: national house prices fell once since their loss series began,
  2007Q4 to 2012Q2. The Fed's residential series includes HELOCs.
- **Card lending standards and the debt service ratio** also track card
  losses some quarters later: standards (SLOOS) best five quarters ahead
  (correlation 0.74, to 2019), possibly banks reacting to delinquency; the
  debt service ratio best ten quarters ahead (0.66, to 2019, old method).
  Neither has a published test as an early warning of losses.
- **Levels.** At 6.5–7.5% unemployment, card losses a year later ran from
  2.4% to 9.4% (1985–2019).
- **The rehearsal card line for 5, 5.98%,** sits where card losses would be
  after a rise in unemployment of 1.8 to 3.3 points: a 2001-sized recession.
- **The Fed's 2026 severely adverse scenario** (unemployment +5.5 points to
  10%, house prices −30%) and its published projection for KeyCorp: cards
  17.4%, other consumer 11.6%, first-lien mortgage 1.6%, home equity and
  junior liens 3.7%, each over nine quarters. Opened at the Fed's own files.
- **Geography.** Deposit-weighted footprint unemployment against national:
  correlation 0.981 in levels, 0.986 in yearly changes, 1976–2026; recession
  peaks within 0.0–0.7 points. The largest single branch, in Cuyahoga County
  (Cleveland), books 34.6% of KeyBank's 2025 deposits; leaving it out gives
  0.985 and 0.989. Not worth building yet.

**Found on the way:**

- FRED's keyless download stalled after the first file; the national
  unemployment rate came through it once. Initial claims came from the Labor
  Department's own form, the debt service ratio from the Fed's archived page.
  No FRED or BLS key is set in this environment; none was needed or written.
- BLS published no October 2025 unemployment rate; 2025Q4 is left out of every
  calculation, not filled in.
- The repository's verified dataset (`credit-suite/verified-data/`) already
  holds the Fed loss and delinquency rates, FHFA house prices, G.19, SLOOS
  and all 51 state unemployment rates, checked against their publishers.
  Reused rather than re-pulled.
- The three existing macro folders: `bls-laus-county-monitor/` is a spec only;
  the FRED code lives in `credit-suite/`; `macro-early-warning-dashboard/`
  has its own code. None records evidence that a series leads losses, and the
  thresholds they carry are uncited defaults. Reusable for the build: the
  standard-library FRED provider in `macro-early-warning-dashboard`, the BLS
  client in `credit-suite/tools/tieout/verify_new_macro.py`.

**Not verified** (also listed in the proposal): Agarwal and Liu (2003) and
Lown and Morgan (2006) could not be opened; four journal papers were read as
their working papers; start dates for national unemployment (1948), real
income (1959) and Case-Shiller (1987) seen only on FRED; real disposable
income not pulled; why 2020 broke not tested; the Fed's pre-2010 card rate
probably excludes securitized cards, not checked. None of the figures has been
tied out yet.

**Waiting on the firm:** which option; the size of the recession; which past
recession's rate per point; whether 5 should begin at a 2001-sized recession
or larger; products in the first build; whether to add A later.

## 14 October 2026, review round

An adversarial read of the proposal raised 21 findings; all were applied to
the Claude Doc and its copy here. The ones that changed a figure or a claim:

- **2020.** The log and the first draft said card losses rose 0.02 points
  per point and then fell to 2.05%. They did not rise at all: 3.76% in
  2020Q2, 1.76% in 2022Q2. Per point: none.
- **Out of sample** now says what the whole-recession rates miss: the two
  known before 2008, applied to 2008's 5.5-point rise, give +3.7 to +5.7
  against an actual +6.9; any of the three applied to 2020 gives +6.4 to
  +11.8 against a fall.
- **Card lending standards** were first written as moving with losses, not
  ahead. They match card losses best five quarters later (correlation 0.74;
  0.18 in the same quarter).
- **The debt service ratio** was first written as "never tested" and as
  working less well than unemployment in a 2025 Fed note. That note never
  uses it: it tried debt-to-income, and found those models fit worse than
  its preferred one. Corrected.
- **The 2007–10 card rate's starting point.** 1.25 is measured from 2006Q4,
  the decade's low. The reviewer gave 0.99 from 2004Q4 and 1.20 from 2007Q2;
  recomputed here, both are 1.21–1.22. The proposal states the start used
  and the alternatives.
- **KeyCorp's projected card loss, 7.7% a year** (17.4% over nine quarters),
  was first written as "inside that range" of past recessions' peak years. A
  nine-quarter average cannot be set against a peak year; the proposal now
  says so.
- **Labels.** "Other consumer" is now "other consumer including auto"; the
  residential series is labelled as including HELOCs; the largest branch is
  no longer called the head office.
- **Geography peaks** differ by 0.0–0.7 points, not 0.1–0.7.

Every other change was wording: plain terms defined once, a neutral decision
table, chart captions naming their files.

## 14 October 2026, docket

The firm asked for a docket. Published as a form:
https://claude.ai/artifact/LDbs7AsXfZ732TurabevcP. Answers save to its
`decisions` collection, one document per decision; read them back from there
and record them here.

**Next, which silence approves:** check the proposal's seven headline figures
against the publishers' own pages (canon:tie-out). It ends when each has the
publisher's number beside ours, or a stated reason it could not be checked.
0 of 7 done. Silence approves this checking only: not building anything, not
choosing an option or a setting, not merging #436.

**Ten decisions open**, each with a recommendation on the form: which option
(C recommended); the size of the recession (the Fed's, yearly); which past
recessions (all four, 2020 marked); where C starts (the middle of the kept
history); add or scale (show both); where rating 5 begins (about a
2001-sized recession, as now); products (all, marked by evidence); auto
(borrow other consumer's rates, labelled); A later (yes, after C); merge
#436 now (yes: it decides nothing).

**Measured for the docket:** threshold-engine's suite, run in this session on
899043e: 767 passed, 5 skipped, of 772. The 5: two Windows-only, three that
open a window. The repository's CI does not run this suite at all; its
test workflow covers nine other projects.

## 14 October 2026, redirected

The firm, mid-way through the tie-out: *"Hold on you are not actually going to
supplement the data with things like unemployment data. The idea is to use
separate separately, unemployment data, and a tool that's very similar to it
and other data such as maybe home insurance prices. Reassess what we're
thinking here this really doesn't have anything to do with the KeyBank
itself."*

So the proposal's frame was wrong: economic data is not a fourth helper to
KeyBank's loss thresholds. It is its own subject, rated by a tool like this
one. The tie-out of the proposal's seven figures is stopped (the figures it
had checked all agreed with the publishers; nothing committed from it), the
docket's ten decisions are on hold, and #436 stays open. Nothing is built.

## 14 October 2026, the firm's answers on the reframed tool

Asked: same engine or a separate tool; who reads it; which series first.

- **Tool:** *"it would still be time series data, and we might want to find
  outliers in that data. However, it will be a separate tool and the sense
  that we may make specific to it modifications."* A separate tool, built on
  the same idea (time series, normal level, outliers), free to change where
  economic data needs it.
- **Readers:** *"I will read it along with the consumer team and possibly the
  commercial team and it's meant to help drive a macro economic narrative
  that is essentially outside of the control of management."*
- **Series:** not chosen yet. The firm: *"Maybe spawn a deep researcher to see
  what things similar to unemployment and home insurance prices you can find
  that would be used for this sort of analysis."* Research started; nothing is
  built.

## 14 October 2026, indicator research

Five research strands (labor and income; household costs and insurance;
household balance sheets and housing; business and commercial; how regulators
and banks use macro data), then one report:
`reports/Macro risk indicators for lending.md` (about 12,000 words, 212
sources). The first run died with a machine restart at about 21:14 UTC before
any notes were written; it was relaunched with notes saved as it went.

What it found, in short:

- The core every bank and the Fed's stress test share: unemployment (level
  and how fast it rises), real GDP, house prices, CRE prices, corporate
  spreads; rates and inflation in support. All nine regional banks' FY2025
  10-Ks name unemployment and GDP.
- Home insurance: no free series of what owners pay. CPI "tenants' and
  household insurance" prices renters' policies (+5% 2019–24 against +62% in
  escrow data). Best free proxy: BLS PPI homeowner's insurance premiums, from
  June 1998, rated on its change over a year.
- Commercial side is limited by licences: FRED keeps 3 years of ICE BofA
  spreads (internal use only); free substitutes are the Fed's GZ spread and
  excess bond premium (from 1973) and the Z.1 CRE price index.
- Published ways to flag a reading: percentile in its own history (the Fed's
  FSR; a 2015 Fed staff heat map at the 65th/80th/85th percentiles), change
  from a recent low (Sahm 0.50), fixed cut-offs on composites (CFNAI −0.70),
  gaps from trend. The Fed's scenario guides (final rule, 2 Oct 2026) are the
  only official sizes of a severe move. The Sahm rule, the yield-curve model
  and the Conference Board index all fired in 2022–25 with no recession.
- The report sorts about three dozen series as ready to rate, a group usable
  with care, and a context-only group (licensed, stopped or stale).

**Not found:** any study of how far an indicator leads C&I or CRE charge-offs;
any test of the NY Fed survey's missed-payment probability against actual
delinquency; licence terms for several sources (listed in the report).

**Waiting on the firm:** which series the tool starts with. Nothing is built.

## 15 October 2026, the firm chose the series; slice 1 built

The firm: *"let's go for ready to rate"*: the report's "ready to rate" group.

**Built (slice 1 of 3), in `src/threshold_engine/macro/`:** the catalog (85
series; 83 rated, 2 inputs), a keyless pull into dated folders with a
manifest, and readers that keep every gap as missing. Live pull, 15 Oct 2026:
85 of 85 series in 31 seconds. Tests: `tests/test_macro_*.py`, 18, offline;
two deliberate breaks (gaps read as zero; blank months dropped) each made
tests fail. Run it and what is missing: `TOOL.md`.

**Found on the way:**

- FRED's keyless CSV stalls (20-second timeouts) on any request that names a
  browser, and answers in under a second without one; the Federal Reserve
  Board refuses (403) a request that does not name one. The pull sets the
  User-Agent by host, and a test pins it.
- FRED does not carry the CPI for motor vehicle insurance (CUSR0000SETE
  returns 404); it is read from the BLS page instead.
- BLS left November 2025 blank (no dash) for motor vehicle insurance; the
  first reader dropped it as "not published yet". Fixed: a blank between two
  numbers is missing; only blanks after the last number are unpublished.
- Licence tags as FRED shows them: Freddie Mac's mortgage rate, the Chicago,
  St. Louis and Kansas City Fed indexes and T10Y3M are "Copyrighted: Citation
  Required"; the rest are public domain.

**Waiting on the firm (for slice 2):** the cut-offs for each rating, the
history window, the change horizon, and the direction of stress for the eight
series the research leaves open. Nothing in slice 2 has a default.

## 15 October 2026 (later), slice 2 built; nothing rated until the firm answers

The firm: *"Continue"*. That does not answer the settings, so none was
chosen for them. What could be built without them was: the ratings engine,
which refuses until every answer is in, and the settings file to answer in.

**Built, in `src/threshold_engine/macro/`:**

- `settings.py`: seven questions, each with a recommendation and its reason
  beside an empty answer.
  - The tool reads only the answers.
  - A file with empty answers is refused, with every gap named in one
    message.
  - A direction the research already states cannot be overridden there.
  - The template is never written over an existing file.
  - A copy is in `settings-template.json`, and a test keeps it equal to what
    the tool writes.
- `rate.py`: position and change ratings; the Sahm reading shown beside
  unemployment; the two readings built from two series.
- `python -m threshold_engine.macro settings-template OUT` and
  `rate --cache DIR --settings FILE`.

**Calls made that the firm can reverse.** These are method, not settings, and
each is written out in `TOOL.md`:

1. Twelve series that climb over the decades (prices, payrolls, GDP,
   industrial production, revolving credit, house and CRE prices) are rated
   on their change only. Their place in their own history says nothing; the
   report rates these on their change.
2. A change is counted in points for rates, spreads and indexes around zero,
   and in percent for levels that grow and for claims.
3. The report's two readings built from two series are added.
   - House prices against income: its direction is left to the firm. That
     makes nine open series, not eight.
   - The mortgage spread: wider is worse, from the Fed's scenario guide.
4. A percentile is the share of the window the latest reading is at or
   beyond, in the direction of stress. The latest reading counts in its own
   window, so a record is 100%.
5. "How long it has held" rates each earlier reading against the same window.
6. A seventh question was added: does a reading exactly on a cut-off take
   the worse rating or the better one? The loss thresholds ask it too.

**Checked against the publishers' own figures:**

- **The Sahm reading:** all 931 months agree with FRED's `SAHMCURRENT`. That
  includes October 2025, where FRED averages the two months it has.
  - Files: `SAHMCURRENT` sha256 `49749abb…a192` and `UNRATE` sha256
    `621ff6fa…a06c`, fetched 15 Oct 2026.
- **The change over 12 months:** every date agrees with FRED's own change
  from a year ago, for 13 series.
  - The one exception is a rounding tie: gasoline, 4 Mar 2019, where the
    exact change is −5.390625%.
- **The first version disagreed.** It counted calendar dates for weekly and
  daily series, and differed in 2 holiday weeks of the mortgage rate and on
  most days of the yield curve.
  - FRED counts whole weeks, and compares a daily reading with the same
    weekday 52 weeks earlier, with no change when that day has no reading.
  - The tool now does the same, and all 10,720 yield-curve and 15,563
    10-year values agree.

**A trial run, not the firm's settings.** The recommendations were copied
into a scratch settings file to open the output; nothing from it is
committed.

- On the pull of 15 Oct 2026, 158 readings were rated and none was skipped.
- Ratings 1 to 5 came out 94, 44, 18, 2 and 0.
- The two 4s:
  - gasoline's change over a year: +41.5%, at or above 94.6% of 1,829 such
    changes since Aug 1991;
  - government-backed mortgages 90+ days late: +0.9 points over a year, at
    or above 93.6% of 94 changes since 2003.
- The Sahm reading for September 2026 is 0.00.

**Tests:**

- 59 macro tests, 41 of them new, all offline.
- Sixteen deliberate breaks of the engine; 14 made tests fail. The other two
  can never take effect, because the settings check already blocks them:
  - letting the firm's direction override the research's (the check refuses
    such a direction before the engine sees it);
  - reading the recommendation on a line reached only after an empty answer
    has been refused.

  A second, reachable way of reading the recommendation was caught.

**Waiting on the firm:** the seven answers in `settings-template.json`.
"Yes to all" takes every recommendation. Their words go here, and the answers
go in `settings.json` beside the template.

## 15 October 2026 (later still), slice 3: the workbook

Built the same way as the ratings: `rate --workbook OUT.xlsx` writes it from a
finished run, so it cannot exist without the firm's settings.
- `src/threshold_engine/macro/workbook.py` uses the repository's house style
  (`keybank_style.py`).
- Every number in it is a value, not a formula.
- The sheets are Ratings, States, one sheet per national series, State data,
  Not rated (only when needed), Settings and Sources. `TOOL.md` lists what
  each holds.
- Each rating now also says where each rating starts, in the series' own
  units. For example, from the trial's full history: unemployment rates 2
  from 5.4 percent, 3 from 6.7, 4 from 7.8 and 5 from 9.0.

**Opened, not assumed.** The trial workbook (the recommendations as
settings, scratch only, not committed) was rendered to PDF in LibreOffice
and read page by page. That found five faults, all fixed:

1. **The unemployment chart dropped to zero in October 2025.** The cell held
   the word "missing", and the chart drew text as zero, the very error the
   tool exists to prevent.
   - A gap is now an empty cell, with "no value published" beside it.
   - Every chart is set to leave gaps.
   - Two tests pin both.
2. **Numeric headers sat left over right-aligned numbers.** Each value read as
   if under the next column.
3. **The derived series printed ten decimal places.**
4. **On the activity index, the axis labels crossed the line at zero.** They
   now sit below the plot.
5. **The settings showed code names** ("cutoffs", "True"). They now read as
   words.

**The tests found one fault the trial could not.** A state missing from the
pull crashed the States sheet, because a formatting loop had been put in the
wrong place.

**Tests:**

- 68 macro tests, all offline.
- Five deliberate breaks of the workbook: all caught, after two test gaps
  were closed. The fixture pull had held no state series, and had always
  shown the Sahm reading. One state was added to it, and both Sahm answers
  are now tested.
- Two breaks of where each rating starts: both caught.

**Waiting on the firm:** unchanged. The seven answers in
`settings-template.json`; "yes to all" takes every recommendation.

**The whole threshold-engine suite**, which CI does not run, was run on this
branch after merging current main. None of its 1,081 tests failed; 5 were
skipped. It took two runs:

- The full run hit its 30-minute limit after 1,026 tests: 1,021 passed, 5
  skipped.
- It had not reached the two main workbook test files, so those were run
  whole: 115 passed, in 57 minutes.

## 16 October 2026, the firm answered the settings

The firm: *"Good with those recommendations"*. Every answer in
`settings.json` is the recommendation the firm was shown beside it, and a
test holds that, as it holds the file usable. Changing one answer in the
file makes the test fail (checked).

**The first real run**, on a fresh pull of 16 Oct 2026, rated 158 readings
and skipped none.

- Ratings 1 to 5 came out 96, 43, 17, 2 and 0.
- The two 4s:
  - gasoline's change over a year: +41.49%, from $3.061 a gallon (week of
    13 Oct 2025) to $4.331 (week of 12 Oct 2026);
  - government-backed mortgages 90+ days late: 1.9% to 2.8% of mortgages
    over the year to 2026 Q2.
- The Sahm reading for September 2026 is 0.00.

**What a day changed.** Homeowner's insurance fell from a 3 (yesterday's
pull) to a 1. This is not an error, and it shows why every pull is kept:

- September 2026 was published, and August was revised (279.164 to 279.364;
  BLS marks the latest four months preliminary).
- The year to September 2026 now measures one September against the next.
  The 2025 step was +4.5% in one month (265.926 to 277.777); the 2026 step
  was +0.05%. So the 12-month change is +0.62%, at or above only 4.6% of
  its history.

**Checked:** the gasoline figure against EIA's own weekly table: 3.061 and
4.331, the same as the tool. The FHFA figures are read from FHFA's own file.

The firm also asked: *"Make it nice walk out and tie it out. Look at the
original repo you were given for inspiration - the threshold engine"*, and
*"do not notify me of non events"*.

## 16 October 2026, made nice, walked

**Made nice.** The workbook now follows the threshold workbook's design (`TOOL.md`): light titles, the
five rating colours as chips and as bands behind every chart, series under five topics, a tab per series
with where each rating starts, a glossary and a run tab. Opening it found two chart faults before it was
committed: no bands at all (they live in hidden columns, which a chart skips unless told), then bands
drawn over the line. Both are pinned by a test.

**Walked** (`walkthrough/`): the monthly refresh, as the analyst does it, from a clean install to the last
tab; 16 steps, every one screenshotted. Against 73 passing tests the walk found 13 things; the tests had
caught none. Eleven are fixed, each with a test that a deliberate break makes fail (78 tests now). Open:
W1, `work/` is not ignored by git (a line in `threshold-engine/.gitignore`, outside the paths this work
may write); W12, no side-by-side what-if (a proposal). The procedure is one 20-page PDF with the
screenshots in it, from the second walk, after the fixes: `walkthrough/refresh-2026-10-16/`.
