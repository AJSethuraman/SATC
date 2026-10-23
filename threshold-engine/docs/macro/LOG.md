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

**Tied out** (`tie-out/gasoline-change-2026-10-16/`): the Ratings tab's top reading, gasoline's change over a
year, +41.49%, rated 4. It is traced from the workbook's cells (H19, I19, J19; the prices on the series' own
tab) to EIA, the publisher.

- **EIA's own weekly table, photographed and ringed:** 3.061 for the week of 13 Oct 2025, 4.331 for the week
  of 12 Oct 2026.
- **EIA's own history file:** all 1,881 priced weeks are identical to the FRED file the workbook read. The
  change, 41.4897%, and the percentile, 1,730 of 1,829, were worked again by code that does not import the
  tool, and by spreadsheet formulas run in LibreOffice.
- **Three more figures**, each against its publisher's own page or file:
  - the unemployment rate, 4.2, against BLS;
  - the Sahm reading, 0.00, against FRED's SAHMCURRENT;
  - government-backed mortgages 90+ days late, +0.9, against FHFA's file.
- **Result:** 4 of 4 tied, rendered through canon's checker.
- **What it found:** EIA prints 3.061 in three different weeks. My own first picture ringed the one in
  December 2007, which would have passed the red-ink check; I caught it reading the crop.

**One scare, recorded.** After the tie-out, one macro test failed locally: `list` printed the old "firm
sets direction". The source was right. The deliberate-break script had restored `__main__.py` within the
same second, at the same size: "firm sets direction" and "the firm's settings" are both 19 characters.
Python judged its cached bytecode of the broken version still current. With the caches cleared, all 78
pass. A deliberate-break run should not write bytecode at all (`PYTHONDONTWRITEBYTECODE=1`), or should
clear it when it puts the file back.

## 17 October 2026, the what-if (W12), and the workbook in PocketBook's look

The firm, on W12: *"i set yes"*, and *"i want to see an example workbook after this, take inspiration from
pocketbook for UI look and feel / workbook output"*, *"also the engine threshold you originate from has
graphs and charting designed by claude design"*.

**Built: `rate --compare WHAT-IF.json`** (`macro/compare.py`). It rates the same pull with a second
settings file and reports every reading under both: the rating, the percentile, where the history starts
and how many readings it holds, and the move between them. Both files must be complete. A what-if with a
gap refuses, naming its file and the gap. Neither file is changed and nothing is chosen.

**The workbook, in PocketBook's anatomy** (`pocketbook/src/pocketbook/house.py`, its redesign of 26 Sep):
- a dark title band with the red rule under it;
- one "How this tab works" note per tab, which folds away;
- tiles for the headline figures, and dark section bands;
- tabs coloured for what they hold: results dark, the record grey.

The helpers are written in `macro/workbook.py`, not copied: `credit-suite`'s conformance check fails any
whole-file copy of a style module. **The charts stay Claude Design's** (the threshold hand-off): the bands
shaded behind the history, the history in ink, the latest point ringed. The what-if's cut-offs are dashed,
as that workbook draws "what happens if". With `--compare`, the workbook gains a What if tab (what differs,
the grid of ratings, the counts drawn, every reading that moves, and the unchanged ones folded away), a
What if column on Ratings and States, and on each series' tab the what-if rating and its starting points.

**The example** (`examples/`), from a fresh pull of 17 Oct 2026 (85 of 85 series): the firm's settings
against `what-if-30-years.json`. 158 readings were rated under both: 145 at the same rating, 11 higher, 2
lower. Seven are national, the same seven the walk's hand-written script found the day before.

**Opened before it was called done.** Every tab was rendered through LibreOffice and read page by page.
- **Charts split across printed pages:** the panels at the top had grown. Each tab's charts now start a
  page.
- **Crowded year labels:** LibreOffice printed nearly every year along the bottom (1971 1973 1974 1976...).
  It was in the 16 Oct workbook too; nobody had flagged it. On a text axis LibreOffice ignores the label
  skip. The axis is now a date axis with a step of 1, 2, 5 or 10 years, at most ten labels. Every layer of
  a chart shares that one axis.
- **Cells sat on different lines** in one row (bottom against centre). Every cell is now centred in its row.

**Principles.** It rests on *propose never dispose*: two runs are set side by side, and neither is
preferred. It also rests on *refuse rather than default*: an incomplete what-if refuses. It strains none.

**Tests.** 12 new: 8 in `test_macro_compare.py` and 4 in `test_macro_workbook.py`. The macro suite is 91,
all passing. Eight deliberate breaks each made a test fail:
- the move's sign;
- the reason a reading is missing taken from the wrong side;
- the refusal's file name dropped;
- dashed lines drawn before the what-if's history;
- a change over a different horizon drawn as comparable;
- the grid transposed;
- the unchanged rows not folded;
- the Run tab showing one file's answers twice.

The runs used `PYTHONDONTWRITEBYTECODE=1`, the lesson of 16 Oct.

**Still open:** W1, `work/` is not ignored by git (`threshold-engine/.gitignore` is outside these paths).

**Codex on #452: three findings, each real, each fixed with a test.** Each test was shown to fail with the
old code put back.
- **A reading only the what-if rates** dropped its starting points from the series' table. The table was
  built from this run's ratings alone. It now takes every reading either run rates.
- **A change over a different horizon** was shown on the What if tab with the baseline's horizon and value,
  beside a rating of the what-if's own change. The row now names both horizons and shows neither value as
  shared. The series' table names the what-if's horizon too.
- **A series in neither run** (not in the pull) read "same rating" beside "not in this pull". It now reads
  "not rated under either".

None of the three arises in the example: all 85 series are in that pull, both settings count the change
over the same 12 months, and every reading is rated under both. The example is rebuilt from the fixed code;
its printout is unchanged. The macro suite is now 93, all passing.

**Codex's second review: the same horizon fault in the printout.** `rate --compare` still labelled a moved
change with the baseline's horizon only, so a 12-month rating could print as a "change over 6 months".

The cause was one level down. The comparison did not record each side's horizon, so every place that names
a change had to work it out again, and one did not. The comparison now records both (`months`), and one
function names a reading from them (`compare.reading_label`). The printout and the What if tab use it. The
What if column on Ratings and States now says whose horizon a moved change is.

Two tests fail with the old labels put back. The example's printout is unchanged, since both its settings
count over 12 months. The macro suite is now 94.

**Excel refused the example (the firm, 17 Oct 2026).** Opening `economic-conditions-what-if-2026-10-17.xlsx`,
Excel said it found a problem with some content, and after trying to recover: "The file is corrupt and
cannot be opened."

- **The cause:** every banded chart's value axis crossed axis 10, and the chart had no axis 10. The date
  axis (500) had replaced the text axis, and the value axis was left at its default. So were the Sahm
  chart's. The fix had been written about two hours earlier. It sat in the same command as a clean-up the
  safety check refused, so it never ran, and only the rebuild was run again. Nobody read the file back.
- **Why nothing caught it:**
  - LibreOffice drew every chart anyway.
  - The file passed the ISO/IEC 29500 schemas, since each element is valid on its own.
  - It also passed Microsoft's Open XML SDK validator (installed for this, .NET 8, `DocumentFormat.OpenXml`
    3.1). The SDK's only notes are on font element order, and a PocketBook workbook the firm uses in Excel
    gets the same notes.
- **The fix:** every layer's value axis crosses the date axis.
  `test_every_chart_crosses_axes_it_has_so_excel_can_open_it` opens every chart in three workbooks (plain,
  with a what-if, with the Sahm chart). It fails if an axis names or crosses one the chart does not have,
  and it does fail with either fix taken out.
- **Rich text removed:** the tab titles were rich text in one cell. No workbook the firm opens in Excel uses
  that, so the subtitle is now a cell of its own, as PocketBook writes it. The test also fails on any
  rich-text cell.
- **Still unverified in Excel itself:** there is no Excel here. The rebuilt example passes all three
  checks: the chart test, the ISO schemas (0 errors) and the Open XML SDK (font-order notes only). The firm
  opening it is the remaining check.
- **Lesson:** after a refused command, re-read the file before rebuilding from it. A refusal stops the whole
  command, including the edits in it.

**Codex's third review: one more branch without the horizon.** The Ratings and States summaries named the
what-if's horizon for a change that moved, but not for a change only one side rates. The series panel's
"Rated under the what-if only" did not name it either. Both now do, in every branch, and the panel gives
the what-if's percentile there too. One test, which fails with either old line put back. This does not
change the example (every reading there is rated under both, over one horizon), so the file the firm is
opening in Excel stands. The macro suite is now 96.

**A blank-context review by Fable (17 Oct 2026).** The firm asked for a thorough review by a model with no
context. The canon adversarial pass was handed to a new session on `claude-fable-5-1`; its record showed
that model configured and serving throughout. It wrote tests only and changed no code. It delivered on its
own branch, `fable/macro-adversarial`, with draft PR #453 marked "do not merge". It touched only its two
files.

- **Its denominator:** 46 hypotheses, 25 run, 9 failing tests (11 cases), 16 held, 21 judged by reading
  only.
- **Taken back by hand.** canon's intake script reads only `canon/findings/`, by design, so the test file
  and report were copied out with `git show`, read, and run against this branch. All 11 cases failed.
- **All nine judged real, and fixed:**
  1. A download the pull could not read stopped every rating with `BadZipFile`. It is now not rated, with
     the pull's own reason.
  2. The Sources tab copied each fingerprint from the manifest. It now hashes the file as the rating read
     it, and a file changed after the pull is flagged there and counted on the Run tab.
  3. A series with no rows crashed the workbook when the Sahm chart was on. The tab now says the pull holds
     no values.
  4. A fourth branch of the horizon labels. A change rated as you have it only was labelled with the
     what-if's horizon. Now only a rating the cell reports names its horizon.
  5. A direction for a reading a series never carries (CPI's level, or a misspelt reading) passed in
     silence. It is now refused by name.
  6. A refused pull left an empty folder for the day. Keys are now checked before anything is written.
  7. "No changes readings in the pull." The reason is now a sentence and names the cause: no reading has
     one that far before it, or none falls in the last N years.
  8. A history of one value gave a chart axis of no height. The axis now spans a step either side.
  9. `pull mortgage_spread` said "not in the catalog". It now pulls the two series the reading is made
     from.
- **Also fixed,** from its *not checked* list: the history, latest-point and dashed-line series carried no
  dates of their own. On a date axis Excel would place them at 1, 2, 3 and so on, in 1900. Every series now
  carries its dates, and the Excel-structure test checks every series in every chart.
- **Its tests** are now `tests/test_macro_review_fable.py`, failing before the fixes and passing after.
  Three deliberate breaks of the new fixes each fail a test. The macro suite is 107.
- **Its observations** are for the firm, not bugs. On the bands, it asks whether, when the firm's own
  history is a window, the bands behind a chart should be shaded only over that window, as the what-if's
  dashed lines are. That question is put to the firm. The rest are wording: the glossary names only one
  horizon, and "not answered" is used for an answer in the wrong place.
- **The rebuilt example** passes the chart test (58 charts, every series dated), the ISO schemas (0 errors)
  and the Open XML SDK (font-order notes only). Its printout is unchanged.
- **Codex, on the fix for 2.** The Sources tab hashed each file again when the workbook was built. A file
  changed between the rating and the build would be fingerprinted as it was at the build, not as it was
  rated. The pull now records the SHA-256 of the exact bytes it parses, as it reads them, and the tab uses
  that. A new test changes a file after the rating and before the build. It fails against the second read
  and passes now. The macro suite is 108.
- **Codex, again.** FHFA's zip holds three series and the Fed's file holds three more. Each was read once
  per series, so a file replaced part way through a run could mix two versions and publish the last one's
  fingerprint. `Pull` now reads each file once and parses every series it holds from those bytes.
  `read_sha` is the fingerprint of those bytes. A new test replaces the Fed's file between two of its series.
  It fails when the file is read again and passes now. The macro suite is 109. The real comparison's printout
  is unchanged.

- **Codex, a third time.** The comparison built its rows from the two runs' ratings only. A reading
  either run asked for and neither could rate had no row: for example, a change only the what-if asked
  for, of a series missing from the pull. The printout and the What if tab never reported it. Each such
  reading is now a row with each run's own reason. The printout counts them ("N under neither") and
  lists them, and the What if tab gives them a section of their own. Ratings and States still read "not
  rated under either", and the one-set tile does not count them. Two new tests fail without the fix.
  Four older tests assumed every row was rated by one run at least, and are narrowed to those rows. The
  macro suite is 111. The real comparison has no such reading, and its printout is unchanged.

- **Codex, a fifth branch of the horizon labels.** A change rated on one side only was printed under
  both horizons. "Change over 6 months; what if: over 12 months ... rated as you have it only" names a
  horizon under which nothing was rated. The What if tab's one-sided rows had the same label. One function,
  `compare.row_label`, now names only the horizons of the ratings a row holds, and both places use it.
  A new printout test covers both one-sided cases, and the What if tab check is added to the existing
  one-sided workbook test. Both fail with the two-sided label put back. The macro suite is 112, and the
  real comparison's printout is unchanged.

- **Codex: two more findings, fixed at the cause.**
  - **Horizon labels.** A change neither run rated was still labelled with both horizons, though only the
    what-if had asked for it. That was the sixth label branch. `row_label` now has one rule: name the
    horizon of each side the row speaks for, meaning the sides that rated it or, when neither did, the
    sides whose settings asked for it. The printout and the What if tab both use it.
  - **Files not read.** A file fetched by the pull but gone, or unreadable, by the time of the rating
    kept the manifest's fingerprint under "SHA-256 as read". Its cell is now blank, "Since the pull" says
    why it was not read, and the Run tab counts it ("Files fetched and not read").
  - Three new tests fail with either fault put back. The macro suite is 115. The real comparison's
    printout is unchanged. The example workbook predates the new Run line and is otherwise the same,
    since its pull read every file.

- **Codex: the summaries follow the rows they summarise.** Two findings, one cause: the Ratings and States
  cells, and the What if tab's "None" lines, were built from only some of a series' rows. In one case the
  level held and the what-if's change could not be counted, and the cell read "same rating". `move_text`
  now reads every row. A reading that moves, is rated on one side only, or is not rated where its settings
  asked for it says so ("Change (what if: over 400 months): not rated under the what-if"), and one at the
  same rating says nothing. "Same rating" is written only when nothing else is said and some reading held.
  The "None" lines now say "every national (state) reading rated under both takes the same rating", which
  stays true when some readings were rated under neither. A new test fails with either fault put back.
  The macro suite is 116, and the real comparison's printout is unchanged.

- **Codex: the rating's fingerprints travel with its ratings.** A library caller can let `rate_all` make
  its own `Pull` and then hand `build` a new one. A file replaced in between would be fingerprinted as the
  new bytes beside ratings made from the old ones. `rate_all` now returns `read_sha`, the fingerprint of
  every file as it read it. `build` publishes those, and refuses when its own `Pull` read any file as
  different bytes, naming the file. The command line always uses one `Pull`, so it is unaffected. Two new
  tests: the refusal, which fails without the check, and the unchanged case. The macro suite is 118, and
  the real comparison's printout is unchanged.

- **Codex: one pull is one set of bytes, not one folder name.** Two more findings in this family, so the
  rule changed at its root:
  - `build` now reads every file the rating could have read and compares the two sets of fingerprints
    whole. A file changed, gone or new since the rating is refused by name.
  - `compare` refuses two runs whose fingerprints differ anywhere, not only two runs of different
    vintages, because otherwise a file changed between the runs would show as a move the settings did
    not make.
  - Two new tests fail with the old checks. The macro suite is 120. The real build passes the check and
    the printout is unchanged.

- **Codex: the what-if is checked against the rating too.** A what-if made from an earlier reading of the
  pull, or against other baseline settings, was accepted by `build`. The comparison now carries the
  fingerprints and baseline settings it was made from, and `build` refuses one that does not match the
  rating. That closes this family: every input `build` takes (the rating, the what-if and the `Pull`) is now
  checked against one reading of the pull. The new test covers both mismatches and the matching case, and
  fails without the check. The macro suite is 121. The real build passes, and its printout is unchanged.

- **Codex: the pull's name is checked as well as its bytes.** A what-if from another vintage whose files
  happened to hash the same passed the check, and the What if tab would have named the wrong pull. `build`
  now refuses a what-if of another vintage. For the same reason it refuses a `Pull` of another day than
  the rating's, since the workbook names the rating's vintage as its source. Both checks fail their tests
  when removed. The macro suite is 122. The real build passes, and its printout is unchanged.

- **The example rebuilt from the final code.** Against the copy the firm is opening in Excel, only two
  parts differ: the file's timestamp and the Run tab, which gains "Files fetched and not read: none". All
  58 chart parts are byte-for-byte the same, so an Excel check of either copy holds for the charts. The
  rebuilt file has 0 errors against the ISO schemas (136 parts). The Open XML SDK gives the same font-order
  notes as before and nothing else. The printout is unchanged.

- **Codex: values only, whatever wrote them.** A what-if file named "=b.json" went into the Run tab as a
  formula, because openpyxl stores any text that begins with "=" as one. The workbook holds no formulas by
  design. So before saving, `build` now keeps every such cell as text: one guard for every caller, not an
  escape on one cell. It walks only the cells that exist. A first version walked every row, and that added
  an empty row element to every sheet, which would have changed the file the firm is checking in Excel.
  Built from the 17 Oct pull, the workbook differs from the committed example only in its timestamps. The
  new test fails without the guard. The macro suite is 123.

## 17 Oct 2026: Book 2 (consumer drivers), the plan before building

The brief proposes a second book, built alongside the Macrobook, that tests
which public indicators move with Book 1's consumer loss measures. It asked
for a written plan and objections before anything is built. Both are in
`consumer-drivers/PLAN.md`. Nothing is built yet.

- **Checked from the reviewer's points.** Confirmed: the weekly mortgage-rate
  leeway (104 of 2,899 readings), which the Glossary does not describe;
  latest-vintage data; quarterly series to 2026 Q2; the October 2025 blank,
  which will leave each monthly change a month older than its level once
  October 2026 is published; the firm's used-car direction; and the FHFA
  index's 20 falls, 19 of them in 2007 Q4-2012 Q2. Half right: every national
  tab states which way is worse, but none cites the research.
- **The first-pass figures, re-derived** (`consumer-drivers/checks.py`, output
  beside it). Card charge-offs and card 30-89 reproduce. Mortgage 30+ does not
  (0.92 / 0.80 against 0.88 / 0.60), and auto's sign differs (+0.20 against
  -0.15). The definitions move these figures by 0.1 to 0.4, so the plan fixes
  them in settings before the first run.
- **The main objection.** 2006-2026 holds one downturn. The effective sample
  of four-quarter changes is about 2 to 5 (first written as 2 to 6, with the
  autocorrelation paired across the 2020-22 and 2025Q4 gaps; Codex on #452),
  and unemployment rises in two runs
  under a ±0.5 band. The repository's longer public charge-off series (the
  Fed's card rate from 1985 Q4; FDIC home equity and other consumer from
  1992 Q4) give three or four episodes (first written as four or five, before a one-quarter gap was merged
  as the plan's own rule says; Codex on #452). On the card series the link holds without 2007-10 (+0.54).
  The plan recommends testing on both, labelled.
- **Waiting on the firm:** 17 decisions, listed in the plan, and a note for
  Book 1's agent asking for the left-out quarters as a file.

## 21 Oct 2026: the usable-with-care group, shown and never rated

The firm: *"after thinking for some time i would like to expand what we keep in this book after all - even if
not super useful"*. Asked which book and how far, they chose the Macrobook, the report's "usable with care"
group with licensed series left out, and **shown, not rated**.

- **What was added: 30 series** (`catalog.SHOWN`), each with the report's caveat in a sentence (`care`).
  27 come from FRED. The NY Fed survey's expected chance of missing a debt payment comes from the NY Fed's
  own workbook (`sources.read_nyfed_sce`), whose licence grants a worldwide right to reproduce, use and
  distribute with a stated attribution. That attribution is carried with the series and printed wherever
  its data are (`credit`).
- **How a shown series is read.** It is described, never rated: its latest reading, and the share of the
  readings in the firm's history window it is at or above, counted from the lowest, with the lowest and
  highest beside it. No direction is set, and nothing says better or worse. The rules for level and change
  are the rated series': a level that grows with prices and the economy is shown on its change only. The
  settings ask nothing about a shown series, so the firm's settings file still checks unchanged (a test
  says so).
- **One reading of the pull.** `rate_all` reads the shown series with the rated ones, so the run's
  fingerprints cover their files. `build` refuses a workbook whose Pull read a shown file differently,
  as it does a rated one (a test changes the survey file between the rating and the build).
- **The workbook** gains a *Shown, not rated* tab after States, with topics, links, what had nothing to
  show and the rest of the group with why it is not read. Each shown series gets its own slate tab, with
  its history in ink, the latest reading ringed and **no bands**, since nothing is rated. Ratings links to
  it, and Run and the Glossary count and define it.
- **Left out, and why** (`catalog.NOT_SHOWN`, printed by `list`):
  - licensed: University of Michigan sentiment; the Atlanta Fed's wage tracker and affordability index.
    The Atlanta Fed's terms of use (read 21 Oct 2026) allow reproduction only *"not for commercial gain or
    monetary profit"*;
  - terms not confirmed: VIX, the Yale tariff rate, NY Fed student loan delinquency;
  - no reader yet: county unemployment (about 3,200 series); CFPB delinquency, whose files are named for the
    month they run to; bankruptcy tables; the Census BTOS.
- **Found on the way.**
  - The new survey reader first accepted 201313 as a month. A test caught it, and the reader now refuses
    the file.
  - This log's first draft said the repository's `bls-laus-county-monitor` reads county rates. It is a
    draft spec, not built. Corrected before commit.
- **Could not check today.** The St. Louis Fed's whole site, FRED included, answered *"Site Maintenance"*
  from about 19:40 to at least 21:30 UTC on 21 Oct 2026, and data.bls.gov timed out. So the 27 FRED ids,
  first readings and licence tags are the report's (14-16 Oct), not re-read. The example workbook is not
  rebuilt yet. Both wait for FRED. The pull refuses a maintenance page in place of a file, because the
  FRED reader checks the header.
- **Codex on 26a2c538, two findings, both fixed:**
  - `rate` printed the NY Fed survey's numbers without the credit its licence requires. Each described
    reading now carries the credit, so `--json` has it too, and the printout ends with it.
  - On the Shown tab, a change could sit beside the latest reading's date when a reading the horizon back
    is missing, as October 2025 is. The change was then an earlier month's. A *Change to* column now gives
    the month each change runs to.
- **Codex on a446af65:** `show` printed the survey's numbers without the credit too. It now prints it
  with them. `show`, `rate` and the workbook are every place the tool prints a series' data, so each now
  carries the credit wherever a licence asks for one.
- **Codex on 341d60a9** (the what-if, not the shown series): a reading these settings do not rate and the
  what-if does had its table of starting points and no chart. It is now drawn without bands, with the
  what-if's lines dashed over the history, and the tab's note says why. The plain chart the shown series
  use now takes dashed lines too. Opened in LibreOffice and looked at.
- **Checks.** 136 macro tests pass, 13 of them new (139 after Codex's four; the last extends a test). Each new behaviour was broken in turn, and a test
  failed every time but one. Reading the shown series again in `build`'s fingerprint check is not
  separately testable, because the Shown tab has already read every one of them. It stays, so the check
  says what it means.

## 22 Oct 2026: FRED back; the shown series checked, the VIX added, the example rebuilt

FRED answered again at 05:45 UTC. It had served its maintenance page from about 19:40 on 21 Oct, then timed
out or returned 504 at 04:40.

- **Each of the 27 shown FRED series was checked on its own FRED series page** (title, units, frequency and
  licence tag) and in a live pull (first reading). All 27 match the catalog. The three regional manufacturing
  surveys are "Copyrighted: Citation Required", as recorded, and the other 24 are "Public Domain: Citation
  Requested". The two policy uncertainty indexes are public domain, as the report said.
- **The VIX is now shown** (31 series). Its FRED tag is "Copyrighted: Citation Required", the same as the
  Freddie Mac rate and the Chicago Fed indexes the tool already rates, so it is usable with the citation and
  is not among the licensed series the firm chose to leave out. FRED's note: *"Copyright, 2016, Chicago Board
  Options Exchange, Inc. Reprinted with permission."* It was taken off `NOT_SHOWN`. Its daily history from
  2 Jan 1990 has 302 market holidays, which FRED leaves blank; they are kept as missing.
- **Several readings agree with the report's own figures.** U-6 is 7.6% (September 2026), the saving rate
  4.1% (August), new-home supply 8.5 months (August), the NY Fed survey 12.2% (September), and each CRE
  standards series has 52 readings.
- **The example was rebuilt** from the day's second pull, `2026-10-22-2` (116 of 116 series; the first pull
  was made before the VIX was added). It is `examples/economic-conditions-what-if-2026-10-22.xlsx`, with its
  printout. The 17 Oct example and printout are removed. 16 of 158 readings move under the 30-year what-if:
  13 up, 3 down, 7 of them national. The mortgage rate's level still moves from 2 to 4 (52.5% of 2,899 weeks
  since 1971; 91.4% of 1,566 since 1996).
- **Checked:** the ISO schemas give 0 errors over 251 parts. The Open XML SDK gives 22, all of them the
  font-element order notes in `styles.xml`, the same kind the 17 Oct example had. Printed to PDF in
  LibreOffice (215 pages), the Shown tab and the minimum-payment, VIX and other tabs were looked at.
- **Not checked:** whether the rebuilt file opens in Excel. There is no Excel here. The merge waits on the
  firm.
- main was merged in first (f8f6ffd7). It adds colours to `keybank_style.py` and changes none the
  Macrobook uses.

## 22 Oct 2026: nothing rated; direction against normal movement; quarters left out; the zoom; the prime rate, household debt and a Dashboard

**What the firm said.** Looking at the Initial claims tab in Excel: *"Views
need to allow us to somehow normalize this or be able to exclude a spike or
something"*. Then: *"We are not rating these. At most these are directional.
I will take recommended ways of viewing tho. Also we need to be able up
exclude quarters we choose. Not an option"*; *"Yes direction only and ways to
establish normal movement"*; quarters to leave out to start, *"None yet"*;
normal movement, *"Typical move (Recommended)"*. While it was being built:
*"how do we not have the prime interest rate as a graph on this?"*;
*"household as a graph on this that split between as it is literally
reported. It's like credit cards mortgage and other"*, then *"NY Fed debt by
type (Recommended)"*; *"i want to be able to simply change the view of
quarters not change cutoffs or averages or anything but to literally zoom in
on a set of quarters"*, then *"Name it, then rebuild (Recommended)"*; *"is
wage growth available"*; and *"there should be a fairly simple to drive
dashboard tab that basically lets you layer any 2 charts or something see the
individual charts and see a chart the shows magnitude in movement"*.

**What changed.**

- **No ratings.** The cut-offs, the tie rule, the directions of stress and
  the change-for list leave the settings; a file that still answers one is
  refused, with why. `rate.py` is `readings.py`, and the command is `read`.
- **Every series, core and usable with care, is read the same way:** where its
  level sits (the share of its history it is at or above, counted from the
  lowest) and whether its change is Increasing, Stable or Decreasing against
  the median change plus or minus one typical move (1.4826 x the median
  absolute deviation, Book 1's measure). How many typical moves a change is
  from the median is shown as a number, and since when it has read that way.
- **New settings, each answered by the firm:** `normal_width` 1, `left_out`
  [], `axis_cut` 1. The template, `settings.json` and the two example
  what-ifs are rewritten to them.
- **Quarters left out** are taken out before anything is measured, drawn as
  gaps, kept in the tables with "left out", and named on every tab.
- **The zoom** is `--zoom 2019Q1:2026Q3` on `read --workbook`. Charts only; a
  test builds with and without it and finds the readings identical.
- **The axis cut**: each chart's axis may leave off up to 1% of its readings
  at each end, the latest reading and the normal range always kept on, and a
  note under the chart names the furthest one off.
- **The prime rate** (FRED `DPRIME`, daily from 1955-08-04, Public Domain:
  Citation Requested, all read on FRED's page today). The report named it but
  grouped it nowhere, which is how the catalog missed it.
- **Household debt by type**: the NY Fed's Page 3 Data (Mortgage, HE
  Revolving, Auto Loan, Credit Card, Student Loan, Other, Total), on one tab,
  stacked as the NY Fed draws it with its names, its attribution carried.
  The file is found through the report's own page. The NY Fed's terms of use
  (6/9/2023), read today, allow business use with that attribution, so the
  "terms not confirmed" reasons in the catalog were false and are rewritten.
- **The Dashboard**: two pickers; both changes in typical moves on one chart,
  both levels as where each sits in its history on another, and each one's
  own level and change. The dataviz guidance rules out a chart of two
  different units on two axes, so the layered charts are of scales the two
  share. Its formulas look up values written on a hidden tab; a test holds
  every other tab to values and the Dashboard to INDEX, MATCH, ROW, IF,
  IFERROR, ISNA, AND, NA, MIN and MAX.
- **Wage growth** was there already, in the usable-with-care group: ECI wages
  and salaries +3.1% in the year to 2026 Q2, average hourly earnings +3.0%
  in the year to September.

**What running it found.**

- From the pull of 22 Oct 2026 (folder `2026-10-22-3`, all 124 series), 219
  readings, none failed. Of the 42 national core changes, 6 read Increasing,
  34 Stable, 2 Decreasing.
- Leaving 2020 Q2 to 2021 Q2 out moves 2 of 124 changes, both downward. A
  normal range built on medians barely notices the pandemic spike, which is
  what the firm was told when it chose the typical move ("A big spike doesn't
  widen it"); the zoom and the axis cut are what change the view.
- The first fixtures were too regular: half their changes equalled the
  median, the typical move was zero, and the tool rightly refused to read
  them. The fixtures now vary; the refusal has its own test.
- A Fable test of 17 Oct, "a history of one value gets a chart axis with a
  span", searched the chart XML for `<c:scaling>`. openpyxl writes it without
  the prefix, so the test found no axis and could not fail. It now matches
  what is written and asserts it saw at least one axis.
- LibreOffice gave `#NAME?` for `AGGREGATE`: a function newer than Excel 2007
  needs a prefix in the file, and Excel would have shown the same. The
  Dashboard looks up each series' first and last month as values instead.
- A daily series' line broke at every holiday, the blank day being drawn as a
  gap. Daily lines now join across a day with no reading; a missing month or
  week is still a gap.

**Decisions carried over, for the firm to confirm or reverse.**

1. A change exactly on an edge of its normal range reads as moving, carried
   from the 16 Oct answer that a tie goes to the warning.
2. The axis cut applies at each end, though the option shown said "the top
   1%": a change spikes both ways.
3. The research's direction of stress is shown on each series' tab as a fact
   ("Higher readings signal stress, the research says"); it changes nothing.

**Checked, and not.** 157 tests pass (`tests/test_macro_*.py`). The example
workbook passes the ISO schemas (0 errors) and the Open XML SDK (only the 25
known font-order notes in styles.xml). Every tab was rendered in LibreOffice
and looked at; the Dashboard's lookups compute and its charts follow the
pickers there. **Not checked in Excel**: the firm's Excel is the check that
remains, the Dashboard above all, the first tab in this workbook with
formulas.

**Codex on #471, two findings, both fixed.** (1) The Sahm reading was worked
from every month, a quarter left out included, on the Overview and in its
chart; it is now worked from the months kept, and a reading dated in a
quarter left out is not shown, since its average borrows the months either
side. (2) The household debt chart sized its axis from every quarter, so a
quarter left out (not drawn) could still stretch it; it is now sized from the
quarters drawn. Each has a test, and each test fails with its fix taken out.
Neither changes the example, whose settings leave nothing out.

**Codex on #471, a third finding, fixed.** When the newest reading fell in a
quarter left out, the Overview's Latest, the household debt headline and
share, and the Dashboard summary still showed it, beside readings measured
from an earlier one. The latest shown is now the latest kept; the series' tab
says when later readings were left out. Tested, and the test fails with the
fix taken out.

**The Dashboard, rebuilt after the firm opened it in Excel (22 Oct 2026).**
The firm: *"Hard to read and I would really like to auto adjust the axis to
match and also why can't I have a custom view of quarters? Also how are these
dashes useful"*, and of the levels chart, *"this is just blank"*. What Excel
showed, and why, none of it seen in LibreOffice:

- **Rows of unnamed dashes** under each one-line chart: the chart did not say
  `varyColors` is off, so Excel coloured every point apart and gave each its
  own legend entry. It is now stated off, and a one-line chart has no legend.
- **Years from 1900 to 2036**, printed over the legends: the time axis was in
  day numbers, which Excel starts at zero unless the dates are close
  together, and its labels sat at the foot where the legend was. Time is now
  in years (2019.0 for January 2019), the legends sit above the charts.
- **A blank levels chart**: both picks (core prices and the wage index) are
  read on their change only, so neither has a place in its history to draw.
  A line above the chart now says so.
- **Axes that fit, and quarters to choose**: From and To boxes on the tab
  set the quarters every chart draws, and every axis fits the picks and the
  quarters. The fixed axis on the movement chart is gone.
- **A quarterly series drew nothing** in LibreOffice beside a monthly one:
  on the tab's monthly grid it has a reading one month in three, and the line
  broke at every other month. Lines on this tab now join across a month with
  no reading, as Excel already does; each series' own tab still shows a gap.

The rebuilt tab was rendered in LibreOffice with the firm's two picks and
2010 Q1 to 2026 Q3, and with the defaults; both drew as intended. It still
has not been opened in Excel here.


The movement chart's legend also named "Normal movement" twice, once for each
dashed line; it now names it once. Every fix above has a test, and each was
checked by breaking it (the colours stated, the axis at the foot, a legend on
a one-line chart, the boxes frozen in view, years for day numbers, the To
quarter, each pick's test in the "no line here" note, lines joined across a
month, the name once): each break turned a test red. Three did not on the
first try (the To quarter, the note, the joined lines), so those tests were
made exact. 162 tests pass.

**A design hand-off (22 Oct 2026).** The firm: *"I want a zip to hand off to
an agent to allow them to make a design for this workbook so you can apply
it."* The brief is `design/BRIEF-2026-10-22.md`, in the shape of the
threshold workbook's design rounds (`docs/design/`): every tab's job and
what looks wrong, the constraints the generator works under, and what to send
back (an HTML mock, a build spec tab by tab, a token sheet, a note to the
builder). The zip held the brief, the example workbook, every kind of tab
printed, the firm's three photos of the Dashboard in Excel before the
rebuild, the readings and the 73 series month by month as JSON, and the style
references. It is not in the repository: it is rebuilt from the example and
the brief.

**Wage growth checked against BLS, and two series added (22 Oct 2026).** The
firm, with a photo of BLS's June 2026 Employment Cost Index release (Table A):
*"Also do we note use the Atlanta fed wage growth data? And this report has
wage and salary growth adjusted for salary and I'm not sure the nominal
amounts match ours"* (the release's constant-dollar columns, adjusted for
inflation).

- **The nominal figure matches.** The book's wage index is private wages and
  salaries (FRED `ECIWAG`): +3.138% in the year to 2026 Q2, 3.1% as BLS
  prints it for private industry. Civilian workers (3.2%) and state and local
  government (3.4%, the figure in the release's opening paragraph) are other
  rows of the same table. From FRED's series before seasonal adjustment
  (`CIU2020000000000I`, `CIU1020000000000I`), all six figures BLS prints in
  current dollars come out to the decimal: private 3.5, 3.4, 3.1 and civilian
  3.6, 3.4, 3.2 for June 2025, March 2026 and June 2026. Civilian for March
  2026 is exactly 3.3500%, on the rounding edge.
- **Inflation-adjusted: five of six.** Dividing that index by consumer prices
  (`CPIAUCNS`, before seasonal adjustment) in the quarter's last month gives
  BLS's constant-dollar figures to the decimal in five of six: private 0.1 and
  -0.4, civilian 0.9, 0.1 and -0.3. The sixth, private for June 2025, comes out
  0.851% against BLS's 0.8%. Taking prices as the quarter's average, or its
  middle month, misses by 0.2 to 0.8 points; taking the index to one decimal
  first moves which figure misses (civilian June 2026 then fails) and does not
  close it. BLS's method note would settle it, but bls.gov refused every
  request from here (403) and its data API had hit its daily limit. Recorded,
  not explained.
- **Added:** wages after inflation, worked out as above, in the
  usable-with-care group (made from the two series before seasonal
  adjustment, so it ties to BLS's table; read on its change only, as an index
  of one index over another has no meaning as a level). Its tab says the five
  of six.
- **The Atlanta Fed's wage tracker is read now.** It was left out on 21 Oct
  under the Atlanta Fed's site terms ("not for commercial gain"). FRED's own
  page for it, read today, tags it *Public Domain: Citation Requested*, the tag
  every other FRED series the book reads carries. It is read from FRED under
  that tag: `FRBATLWGT3MMAUMHWGO`, the 3-month average of the median wage
  change, monthly from 1997, 3.9% in September 2026 (the 12-month average,
  also on FRED, was 3.7%). October 2025 has no value, as the household survey
  it is built from has none. **This reverses what the firm was told earlier
  today** ("licensed and stays out"); the firm can still leave it out.

The example was rebuilt from a fresh pull (folder `2026-10-22-4`, 127 of 127
series), so it carries both new series. Leaving out the pandemic now moves 4
of 126 changes, all more downward: initial claims (Stable to Decreasing, on
the week to 17 Oct), mortgages 90+ days late, nonresidential property
standards, and wages after inflation. Rendered, the wages-after-inflation tab
showed its what-if line running to a third line in a row two lines tall; the
row is now as tall as its words, tested, and the test fails with the fix
taken out. The four screenshots in `examples/` are from this build.

**Codex on #471, a fourth finding, fixed.** The Overview showed each type of
NY Fed household debt, its balance and its change, without the attribution
the NY Fed's terms of use ask for wherever its data are shown; only the
Household debt tab carried it. So did the What if tab and the Dashboard (any
series can be picked). Each of them, and Usable with care for the survey's
credit, now ends with "Credits the publishers' licences require": once for
each publisher whose series the tab shows and the pull read. Tested: each
tab carries the NY Fed's credit once, and a tab with no credited series read
carries none. Each part fails a test when taken out. 168 tests pass.

**Codex on #471, a fifth finding, fixed.** The Dashboard's From and To lists
held only quarters with a reading. So a zoom starting in a quarter left out
of every series (`--zoom 2020Q2:2026Q3` with the pandemic left out), or
ending past the data, opened the boxes on a quarter the lookup could not find
(#N/A), and every chart on the tab drew nothing. The list now runs quarter
after quarter from the first month drawn to the last, and out to a zoom's
ends. Tested both ways, and the test failed before the fix. In LibreOffice,
that zoom with the pandemic left out now computes, and both picks draw from
July 2021 to September 2026. 169 tests pass.

**Codex on #471, a sixth finding: did not reproduce, and found a gap in the
tests.** Codex read the Dashboard's dashed lines as having their ends clamped
the wrong way round, which would stretch every change chart back over the
whole history whatever From and To say. They were not: each line starts at
MAX(From, the pick's first month) and ends at MIN(To, its last), and in
LibreOffice From 2020 Q2 to To 2026 Q3 drew them from 2020.25 to 2026.7. But
reversing them failed none of the 56 workbook tests. A test now holds both
ends of the shared lines and of each pick's, and fails when they are
reversed.

**Codex on #471, a seventh finding, fixed.** A change read under the what-if
only, on a series whose first side still had a change in the drawn quarters,
sized its chart from the what-if's latest date in the column of the first
side's changes. That cell was empty, and the whole build failed with a
TypeError. Reproduced with a quarterly series leaving out every quarter but
two, six months apart: one change, too few to read, while the what-if read
it. The chart now uses the latest value only where its column holds one. The
test failed before the fix. The example is unchanged: its settings leave
nothing out. 171 tests pass.

## 22 Oct 2026 (evening): the design applied

**Claude Design's round 1 came back and is applied.** The firm sent the zip
back, *KeyBank_design_style.zip*, with no words: the mock, a build spec tab by
tab, seven tokens and a note to the builder. All of it is kept in
`design/round-1/`, with pictures of the mock drawn in Chromium. What changed,
in the spec's own order:

- **One grammar on every tab.** The changes, everywhere:
  - title band 27 pt with the subtitle beside it;
  - links in row 2;
  - section names over an ink rule (the dark bands are gone);
  - canvas headers with a stone rule, rows ruled in `EFEBE4`;
  - Calibri 11 data;
  - a direction bold on mist whichever way it moves, Calibri 11;
  - the method note ("How this tab works") moved from the top of every tab to
    its foot, folded away, with no word changed.
- **Overview.** One frozen header (it was repeated under each topic). The
  first series is on row 9, where it was on row 21. The month a change runs to
  is shown only when it is not the latest's, and then bold. The What if column
  is blank where a series reads the same way, since the tile counts those.
  Household debt shows its total, with the six types folded away under it.
- **Dashboard, one screen.**
  - The four boxes sit in one row (B5, H5, N5, Q5), and both picks' readings
    sit in the Overview's columns.
  - The two charts that set the picks together are side by side; under each
    pick's name come its level and its change.
  - **The spike rule:** past each series' cut (the firm's `axis_cut`, 1%, at
    each end of its whole history, with the latest reading and the normal
    range always kept on), a drawn value is #N/A by formula, so Excel's axis
    fits the rest.
  - A triangle marks each reading left off. The line under the two charts set
    together counts them and names the furthest. Checked in LibreOffice: with
    unemployment and claims over every quarter, *"9 readings run off the top,
    8 off the bottom; the furthest +13.9 typical moves in Apr 2020"* and
    *"7 ... 7 ...; the furthest +214.0 typical moves in Mar 2020"*.
  - The new functions are COUNTIF, ABS and TEXT, all older than Excel 2007,
    and the test's list of allowed functions grows by those three.
- **Series tab, one function for 66 tabs.**
  - Tiles for the level (with its lowest and highest), the change (normal
    range, typical moves, since, history from) and, on unemployment, the Sahm
    reading.
  - The level and change charts side by side; a change-only series gets one
    chart the full width.
  - Each chart has its note under it, then What it is, which now ends with
    the tool's two sentences, moved out of the tiles unchanged.
  - The history moves from N:Q to AA:AD.
  - Every history chart gets gridlines and a triangle at the edge for each
    reading off the axis, and the what-if's range is slate, dashed, 1 pt
    (it was red on some tabs and black on others).
- **Household debt:** the NY Fed's chart beside the table of every type, the
  total's change under the table, the credit line under both.
- **Usable with care:** in the Overview's columns, with why each needs care in
  a row under its name.
- **States:** two tables side by side, 26 and 25, all 51 on one screen.
- **What if:** canvas headers, section names, the method note at the foot.
- **Record tabs:** one template, a link back to the Overview on each.
- **Tab order** follows the Overview, coloured by topic (slate and stone in
  turn), States after the core series, and Usable with care in mist.

**Where the build departs from the spec, and why:**

1. **The tokens live in `workbook.py`**, not appended to `keybank_style.py`.
   That file also styles the threshold workbook, and this work writes only
   under the macro tool's own folders.
2. **Charts are anchored to their cells corner to corner**, not drawn at the
   spec's sizes in centimetres. LibreOffice gives a column different pixels
   from Excel, and the NY Fed's chart ran over the start of the table beside
   it. Anchored to cells, a chart fills the same columns in both.
3. **The latest reading's label sits left of its point**, not right. At the
   right, LibreOffice clipped it off the chart's edge.
4. **Daily and weekly series stay line charts on a date axis.** The spec says
   they "stay scatter"; they were never scatter, and the date axis is the one
   proven in Excel.
5. **Some columns are wider, and two strings of mine are shorter:**
   - States' "Unemployment rate" column is 12, not 9.57, because the header
     broke mid-word;
   - What if's normal-range columns are 20, because the size-11 text was cut
     off;
   - two strings written today for wages after inflation are shorter, because
     they ran past their columns. The title is now "Employment cost index:
     private wages, after inflation", and the unit "index: wages over
     prices, x 100". (The first shortening dropped "private", which its
     input is; Codex found it, below.)
6. **Choices the spec left open:**
   - the Dashboard freezes rows 1 to 5;
   - its "From is after To" warning moved to T5;
   - its change, date and range cells are text the tool writes, so one cell
     shows any pick in its own format;
   - its direction is bold on mist by conditional formatting;
   - the Household debt tiles have no what-if row (the spec's row table has
     none).
7. **One method-note sentence changed, because it would otherwise be false.**
   On the Dashboard, "the line above the chart says so" now reads "its name in
   the legend says so", since that line is gone. The Dashboard's note also
   gains an "Off the chart" entry, worded as the series tabs' is.

**The questions the note to the builder asked, and the default taken:**

- **The Dashboard's cut uses each series' whole history, at the firm's 1%.**
  Over the full history the claims movement chart still runs to about +20
  typical moves. A wider cut on the Dashboard alone would need a setting of
  its own.
- **Triangles are on the series tabs too.** LibreOffice draws them, with no
  legend entry. Excel has not been seen.
- **The normal range is drawn two ways:** a band on the series tabs, dashed on
  the Dashboard, where every chart is a scatter chart.
- **The x axis's step is fixed at build**, as the spec says.
- **Tab colours alternate by topic.** If the firm reads meaning into slate
  against stone, all core tabs can be slate.
- **The chart row on a series tab** follows whether the what-if row is there,
  as the note asks.

**New words, for the firm to approve or replace:**

- the tile labels "Lowest", "Highest" and "Sahm's published trigger";
- the levels chart's "<name>: change only";
- the line under the Dashboard's charts, "Off the chart, <name>: N readings
  run off the top, M off the bottom; the furthest +X typical moves in Mon
  YYYY.";
- What it is's labels "Level" and "Change over 12 months".

**Checked:**

- 175 tests pass. The new tests cover:
  - the Overview's one header and its folded note;
  - the series tab's tiles, side-by-side charts, gridlines and triangles;
  - a reading off the axis marked at the edge;
  - the Dashboard's cut, markers and note;
  - States in two tables;
  - the tab order and colours;
  - the What if column blank when the same;
  - the household types folded.
- Each was broken in turn and each break failed a test, nine in all.
- The rendered workbook in LibreOffice showed three faults that tests had not
  caught. Each is fixed and now tested:
  - tile figures sitting at the right of their cells (left alignment was
    never stated);
  - an empty Sahm chart (its columns are now hidden, and the chart was not
    told to plot hidden cells);
  - the overlapping NY Fed chart.
- **Not seen in Excel.**

**Codex on #471, three findings on the design build, all fixed.**

1. **Wages after inflation had lost "private" from its title** when it was
   shortened to fit its column, so it read as all workers. Its input is the
   private industry index. The title is now "Employment cost index: private
   wages, after inflation", 53 characters, which fits the column the longer
   one ran past. A test holds the word in both the title and its input's.
2. **A type of household debt blank in the NY Fed's newest quarter** would
   have shown its previous quarter's balance and change under "Each type,
   latest quarter". The NY Fed has not done that, but nothing stopped it.
   Such a row now says *"No 2026 Q2 value in the NY Fed's file; its latest
   is 2026 Q1."* and shows no figures.
3. **The household total's change chart drew no what-if range.** Every
   series tab dashes the what-if's normal range over its change chart; this
   chart is drawn by the tab's own code and had been left out. It now draws
   the same two slate dashed lines over the years the what-if's history
   covers, and says so in its title.

Each fix was taken out in turn and its test failed, three in all. The example
is rebuilt.

**Codex on #471, a fifth finding on the design build, fixed.** The household
total's change chart was drawn only when the total was read under these
settings. Too short to read here but read under the what-if, it was skipped,
so the tab showed neither the change nor the what-if's range; the series tabs
draw that case, titled "not read under these settings". The household chart
now does the same, with no shaded range of its own. A new test fails with the
fix taken out. The example is unchanged by it apart from its build time, so it
is not rebuilt.

## 23 Oct 2026: bankruptcies

**Asked:** *"what bankruptcy data do we have or can we get"*. Found, and told
the firm:

- **In our pull already, unread:** the NY Fed's household debt workbook, the
  file household debt by type comes from, has three bankruptcy sheets.
  Page 17 Data counts people with a new bankruptcy on their credit report,
  nationally, each quarter from 2003 Q1 (136.8 thousand in 2026 Q2, against
  131.3 thousand a year before). Page 30 Data splits the same by age from
  2000 Q1, and Page 40 Data gives the share of people by state, for eleven
  states only (AZ, CA, FL, IL, MI, NJ, NV, NY, OH, PA, TX).
- **US Courts' filing tables:** the official counts, by chapter, business
  and personal, by district, with a one-month table inside each quarter's
  release and county counts in F-5A. PDF only. Twelve months to 30 Sep 2026:
  621,111 filings, +11.4% (Table F); personal 594,057, business 27,054.
- **The Federal Judicial Center's case files**, new to this log: one row per
  bankruptcy case filed since October 2007, with the filing date, chapter,
  business or personal, the debtor's county and ZIP code, and assets, debts
  and income. No names. 887 MB zipped for FY2018 to 30 June 2026, 1.47 GB
  for FY2008 to 2017 (fjc.gov/research/idb).
- **Epiq / ABI:** monthly and fastest, but a commercial product: out, as the
  firm chose for licensed series.
- FRED could not be searched that day (its server sent nothing back).

**Built:** *"build it"*, on the NY Fed count, usable with care. The firm had
read, before answering, how the 2005 law change would affect it.

- **The 2005 law is a break, not quarters left out.** Public Law 109-8 was
  enacted 20 April 2005 and its section 1501(a) has it "take effect 180 days
  after the date of enactment", 17 October 2005 (govinfo.gov). People rushed
  to file before it: 948.6 thousand in 2005 Q4, 213.9 thousand in 2006 Q1.
  Leaving those quarters out would take them out of every series, and the
  readings barely need it: the normal range is -23.2% to +19.2% over the
  full history and -22.4% to +19.1% from 2007; its level sits at or above
  25.5% of its history, or 29% from 2006.
- **What it reads, 2026 Q2:** +4.17% on a year before, Stable, 0.3 typical
  moves above the median, Stable since 2024 Q3. The workbook's figures match
  the same arithmetic done by hand on the NY Fed's file.
- **Why with care, in the tab's words:** "estimated from a random sample of
  credit reports; the October 2005 bankruptcy law broke its history". The
  NY Fed's background page says the panel is "constructed from a nationally
  representative random sample of Equifax credit report data".
- **Not claimed: that it is revised each quarter.** The first draft said so,
  borrowing the household debt series' break. Checked against the NY Fed's
  2026 Q1 file, the 2026 Q2 report changed none of the 93 earlier quarters
  of this count, so the claim was taken out.
- **The reader** now reads a named sheet of the NY Fed's file ("Page 17
  Data: bankruptcy") as well as Page 3, and checks each sheet's own title
  and unit, so Page 3's table under Page 17's name is refused.
- **Checked:** 181 tests pass. The reader, its title check and the series'
  place on the Usable with care tab were each broken in turn, and each
  break failed a test. The example is rebuilt from the same pull (folder
  `2026-10-22-4`, which already held the file); under the pandemic what-if
  this count reads the same way, so still 4 of now 127 changes move. Its tab
  and the Usable with care tab were rendered in LibreOffice and looked at.
  **Not seen in Excel.**
- **New words, for the firm to approve or replace:** the title "People with
  a new bankruptcy on their credit report", the unit "thousands of people",
  the tab name "New bankruptcies", the care line above, the break's line and
  the note "Counts people whose credit report shows a new bankruptcy in the
  quarter, not cases filed in court."

## 23 Oct 2026 (afternoon): bank credit, and the Dashboard becomes the comparison

**Asked.** The firm sent a screenshot and a hand-off from another agent that
had worked in the Excel copy of the workbook: 16 bank credit series pasted
in as values, and a "Compare series" tab testing whether two series are
related. *"i do not necessarily want it exactly like this because a lot is
going on, but i want to work this to being the dashboard because it's the
same info but further."* Asked four questions, the firm answered:

- keep the answer line and the same-time r, and the lead table, condensed;
  *"but i am not a huge fan of the blue and orange - i would rather use more
  Keybank esque colors"*;
- the 16 bank series, *"Yes, from FDIC each pull (Recommended)"*;
- the test's settings, *"As the Excel version (Recommended)"*;
- *"Merge #471 first (Recommended)"*, which was done (f8dc4656), Codex's last
  point left as it was, as the firm chose.

The Excel copy's own tabs could not be carried: the tool writes the whole
workbook each run, so anything added by hand in Excel is gone at the next
build. Both are built into the tool instead.

**Bank credit.** Each product's net charge-offs (past four quarters over the
average balance) and its loans 30+ days past due including nonaccrual, for
credit card, other consumer, mortgage and home equity; every FDIC filer
summed, and KeyBank (certificate 17534). Built by the threshold engine's own
peers pull and build (`fdic_credit.py`), under the consumer book's recorded
settings, so each figure is the threshold workbook's. Its own notes (the
definition, KeyBank's rules, every reporting change touching the series) go
into the file and onto each tab, with the cache's local path taken out.

- **Tied out** against the threshold engine's committed industry files:
  card net charge-offs 3.476549939643245% at 2006 Q4 and card 30+
  3.750308262095038% at 2006 Q1, both to the last digit. KeyBank's card net
  charge-offs for 2026 Q2, 3.76%, as the firm's Excel copy had them. The
  test builds the series from the threshold engine's own test data and
  checks KeyBank's and every filer's card 30+ against the filings'
  arithmetic, worked separately.
- **Licence:** the FDIC's website policies page, read 23 Oct 2026, states
  no terms of reuse for its own data; the catalog says so.
- **Citations:** each series cites the report's labour section (losses: it
  reads card charge-offs against unemployment) or household section (30+);
  the firm added them, not the research, and the catalog says that too.
- The card series for all banks carry the 2010 Q1 securitization break
  (FAS 166 and 167), as the threshold engine labels it. KeyBank's card
  history starts after it (2012 Q3 for 30+, 2013 Q4 for losses).
- Units shortened to fit their columns: "% of loans, past year" and "% of
  loans, quarter-end"; the full definition is under "From the build".

**The Dashboard.** Kept: the four boxes, both picks' readings, both changes
in typical moves. Gone: the levels-together chart and each pick's own small
charts (each series' tab has them). New:

- one line that answers: the strongest lead, whether it holds, and the
  same-time r; bold on mist when a lead holds;
- at the same time, every shared reading: r, readings, effective readings
  n x (1 - r1 r2) / (1 + r1 r2) and p (Student's t, two-tailed);
- each lead the settings name, on one reading a year from four starting
  points: r (average of four), pairs (fewest), holds in x of 4; a lead holds
  when all four agree in sign and pass p < 0.05 divided by the leads tested;
  the strongest bold on mist;
- the picks in KeyBank ink and red (0A0908, CC0000) in place of blue and
  orange.

Four new settings, each the firm's answer of 23 Oct: `compare_p` 0.05,
`compare_leads` -24 to +36 every 6, `compare_starts` 4, `compare_min_pairs` 6
(the Excel copy's "Lags with under 6 annual pairs are not tested"). The
month grid now runs one row a month with none skipped, padded by the longest
lead each way, so each lead's ranges are fixed addresses (no OFFSET).
Formulas use only Excel 2007 functions: CORREL, TDIST, SUMPRODUCT, SQRT,
AVERAGE, SUM and COUNT join the list.

**Checked.**

- LibreOffice recalculated the Dashboard and every figure matched an
  independent computation from the hidden data tab's values (a separate
  script, its own Pearson and its own Student's t), largest difference
  5e-13: same-time r +0.3987 on 704 readings, effective 243.2, p 1.1e-10
  for unemployment against claims; each of 11 leads' r, pairs and holds.
- Card 30+ against card net charge-offs, all banks, 2013 Q3 to 2026 Q2:
  the first leads by 6 months, r = +0.96, holding at 4 of 4, and at 12
  months +0.89, holding too: the Excel copy's own finding (+0.96 at +6, 4 of
  4; industry holds at 12).
- The default pair, unemployment against card net charge-offs for all
  banks: no lead holds; at the same time r = +0.41 on 74 readings, effective
  22.0, p 0.056, which does not pass.
- 197 tests pass. Eight breaks of the new code each failed a test: the lead
  offset, the starting months, the allowance for leads tried, the effective
  readings, the colours, the all-four rule, the FDIC step back past an
  unpublished quarter, and the cache path kept out of the notes.
- The example (`examples/economic-conditions-2026-10-23.xlsx`, from a fresh
  pull of all 144 series) passes the ISO schemas (0 errors); rendered in
  LibreOffice, the Overview, the Dashboard and a bank tab looked at, and the
  five pictures redrawn. The pandemic what-if still moves 4 changes, now of
  143. **Not seen in Excel.** In particular, that Excel's CORREL skips a
  pair with text in it as LibreOffice's does is from Excel's documentation,
  not from a run.
- Not run: the threshold engine's own tests (they take about 28 minutes and
  this change writes nothing under its folders, though it calls its peers
  code).

## 23 Oct 2026 (evening): Codex on #472, readings a year apart, and the starting points

Codex reviewed #472 and found two things. Both were real.

**Readings a year apart are not independent (its P1).** The lead test took
each starting point's one-a-year pairs as independent. That was the reason
given to the firm when it chose "As the Excel version": "One reading per 12
months at four starting points, so no two readings share data." It is true
of a level and not of a change: a 12-month change ends where the next one
begins, and a cycle runs over several years, so one year's change runs on
into the next. On the raw count of pairs, p came out too small. Now each
starting point's p is on its effective pairs, the same allowance the
same-time test makes: n x (1 - r1 r2) / (1 + r1 r2), with r1 and r2 each
series' correlation with its own change a year earlier, in the quarters
chosen. Effective readings and effective pairs are never more than n: when
r1 r2 is negative the formula gives more readings than there are, and the
Dashboard no longer counts them.

What it changes, from the 23 Oct pull on the firm's settings (eleven pairs
worked by a separate script before the change was made):

| Pair | Before | Now | Each series' change against its own a year earlier |
|---|---|---|---|
| Mortgages 30-89 days late, then mortgage net charge-offs (all banks) | +12 months holds, r +0.65 | no lead holds (0 of 4) | +0.35, +0.61 |
| NY Fed household card debt, then card net charge-offs (all banks) | +18 months holds, r +0.66 | no lead holds (0 of 4) | +0.50, +0.35 |
| Card 30+ late, then card net charge-offs, all banks, 2013 Q3 to 2026 Q2 | +6 (r +0.96) and +12 (r +0.89) hold | the same | +0.30, +0.30 |
| Unemployment rate and initial claims | at the same time holds, r +0.70 | the same | -0.12, -0.06 |
| Unemployment rate and card net charge-offs, all banks (the default) | none | none | -0.12, +0.35 |
| KeyBank card 30+ late, then KeyBank card net charge-offs | none | none (best 2 of 4) | +0.14, +0.03 |

Of the other five pairs tried, card 30+ against card losses over the whole
history held at +6 and +12 months before and after, and four held nowhere
before and after. The test is now
stricter than the Excel copy's, which used the raw count. The firm's answers
(p 0.05, the leads, four starting points, six pairs at the fewest) are
unchanged.

**Starting points must fall on a quarter (its P2).** `compare_starts`
accepted 1, 2, 3, 4, 6 or 12. With 3, 6 or 12 some starting months (May,
September and others) never hold a quarterly reading, so with a bank series
picked every lead would have said not tested. The settings now accept 1, 2
or 4 and refuse anything else, saying why. The firm's answer, 4, stands. The
question and its reason are reworded in `settings.json`, the what-if and the
template ("keeps them a year apart" where it said "shares none").

**Also.** The Dashboard's folded method note cut its longer labels short
("What is co", "At the same", "Together, m", "Off the char"). Its labels now
take two columns, as the States tab's do. The last two were cut on main too.
The note under the lead table now says p is on effective pairs; it was
shortened to fit its one line.

**Checked.**

- LibreOffice recalculated the Dashboard for six pairs (the default,
  unemployment against claims, card 30+ against card losses for all banks
  from 2013 Q3, mortgages 30-89 late against mortgage losses, household card
  debt against card losses, KeyBank card 30+ against KeyBank card losses).
  Every figure matched a separate script with its own Pearson, its own
  Student's t, its own year-apart correlations and its own reading of the
  From and To quarters. Largest difference 5e-13; no row differed.
- Seven breaks of the new code each failed a test: p on raw pairs, its
  degrees of freedom on raw pairs, a month apart in place of a year, no cap
  at a lead, no cap at the same time, the second series' year-apart
  correlation taken from the first, and three starting points accepted.
- 198 tests pass. The example was rebuilt from the same pull and passes
  the ISO schemas (0 errors); the Dashboard was redrawn (picture 2) and its
  method note looked at unfolded. The what-if printout is unchanged.
- **Not seen in Excel.** That Excel truncates TDIST's degrees of freedom to a
  whole number, as LibreOffice and the check do, is from Excel's
  documentation, not from a run.

## 23 Oct 2026 (evening, second round): Codex on 7a03c63b

Codex reviewed the fix and found two more things. Both were real.

**A lead without a p counted as tested (its P1).** When the effective pairs
at a starting point are too few for Student's t (fewer than 3), that
starting point has no p. The lead still counted as tested, because the
test looked only at the raw pairs and the r. So it read "0 of 4", could be
picked as the strongest, and raised the number of leads the firm's level is
divided by, which made every other lead harder to pass. Now a lead is tested
only with a p at every starting point; otherwise it reads "not tested". Two
real cases from the 23 Oct pull, recalculated in LibreOffice and matched to
the separate script (no row differing, largest difference 7e-16):

- core prices against mortgage net charge-offs (all banks), 2014 Q1 to 2023
  Q4: each series' change against its own a year earlier +0.58 and +0.75,
  so the leads at +30 and +36 months, with 7 pairs at each starting point,
  have too few effective pairs. They now read not tested, and the level is
  0.05 divided by 9, not 11;
- house prices against mortgages 30+ days late (all banks), 2004 Q1 to 2013
  Q4: the leads with the second ahead by 6 and 12 months, 6 pairs each, now
  read not tested; 7 leads are tested.

**An installed copy could not find the book (its P1).** The README installs
the engine with `pip install .`, which puts the package under site-packages.
The bank build found the consumer book and the roster from its own file's
place, so an installed copy looked in the wrong folder and all 16 series
failed with "file not found". Seen, not inferred: the pushed version,
installed into a scratch site-packages with uv, looked in `.../inst/lib` and
raised FileNotFoundError. Now the build looks in the source checkout first,
then in the folder the tool is run from (the tool's instructions say
`threshold-engine/`), and refuses elsewhere, naming the three files it needs.
The files are not copied into the package, where a second copy of the book
could drift from the one the firm answers. The threshold engine's own app
(`app.py`) finds the same files the same way; it is not touched here.

**Checked.**

- The installed copy, run from `threshold-engine/`, found the book (jump
  0.25); run from another folder, it refused with the sentence above.
- Three breaks each failed a test: tested without a p at every starting
  point, no working-directory fallback, and the checkout taken without
  checking it holds the files.
- 199 tests pass. The example was rebuilt from the same pull; the what-if
  printout is unchanged.

## 23 Oct 2026 (evening): the firm opens it in Excel, and a near miss gets its own words

The firm opened the workbook in Excel and set KeyBank's card 30+ late
against KeyBank's card net charge-offs, 2010 Q1 to 2026 Q4. Excel's figures
were the ones LibreOffice and the separate script gave for that pair: at +12
months r +0.76, 11 pairs at the fewest, 2 of 4; at the same time r +0.35 on
47 readings, 7.2 effective, p 0.428. The firm: *"it just seems so unlikely
this does not track."*

It does track, and the line said otherwise. Every starting point's r at +6
and +12 months is positive, from +0.51 to +0.85. What fails is the bar:
KeyBank filed no card loans until 2012 Q3 (LNCRCD 0, then 709,567 thousand
dollars in its 30 Sep 2012 Call Report), so its changes start in 2013 and
2014 and each starting point has about 12 readings a year apart. With 11
leads tried, each must pass p below 0.05/11, which on 12 readings needs r of
about +0.76 at every one: at +12 the four are +0.67, +0.74, +0.81 and +0.80.
The all-banks pair, with 16 readings and r +0.94 to +0.97, clears it. The
year-apart allowance barely enters here (effective 11.9 of 12).

The answer line said "No lead holds at every starting point", which reads
as no link. Asked, the firm chose to reword near misses, not to loosen the
test ("Reword near-misses"), then: *"shorten it though, just say something
like 2 of 4, tested x"*, and, for a lead passing at none of the four, "Only
1 of 4 or more". So when the strongest lead has the same sign at every
starting point and passes at one or more but not all, the line reads:

> The changes move together when the first leads by 12 months: r = +0.76,
> holds in 2 of 4, 11 years tested.

The years are the table's fewest pairs at that lead. Passing nowhere keeps
"No lead holds at every starting point ...", as the default pair
(unemployment against card losses) still reads.

**Checked.** LibreOffice computed the line for four pairs: the KeyBank pair
(the words above), the default pair and mortgages 30-89 against mortgage
losses (both pass nowhere: "No lead holds"), and card 30+ against card
losses for all banks (holds). Every figure matched the separate script.
Five breaks of the new line each failed a test: the branch never taken, the
years from the r column, a near miss on any pass without the same sign, 0 of
4 let in, and a positive r in place of a pass. 199 tests pass.

## 23 Oct 2026 (night): Codex on 450302f9, the lead the line speaks of

Codex found that the answer line, and the mist, followed the tested lead
with the largest r even when it missed and a weaker lead held. The line then
reported a miss and never named the lead that holds; before the near-miss
wording it said "No lead holds", which was false. The flaw was there from
the Dashboard's first commit. Now a lead that holds ranks above every lead
that does not (|r| is at most 1, so its rank is |r| + 2), then the size of
r.

Seen on the 23 Oct pull: a scan of all 91 series in pairs found 4 pairs,
each in both orders, where the largest r misses and another lead holds.
Recalculated in LibreOffice and matched to the separate script:

- card 30+ late (all banks) against revolving consumer credit: the second
  leading by 6 months has r +0.74 and passes at 3 of 4; by 12 months, r
  +0.71, holds. The line now reads "The changes move together when the
  second leads by 12 months: r = +0.71 on one reading a year, holding at all
  4 starting points", and that row is the one on mist (looked at);
- industrial production against the Philadelphia Fed's current activity:
  +12 months has r -0.49 at 3 of 4; +6 months, r -0.46, holds, and the line
  now speaks of +6.

The default pair and KeyBank's card pair read as before. A break (the rank
by r alone) failed the test. 199 tests pass.

Codex on e5dbbe4b: with From and To the same quarter, two quarterly series
share one reading, CORREL gives no r, and the line printed "r =  on 1, too
few to test." The same-time sentence is now left out when there is no r.
In LibreOffice, card 30+ against card losses (all banks), 2020 Q1 to 2020
Q1, reads "Too few readings in these quarters to test a lead: pick a longer
span." and nothing more; the default pair reads as before. A break (the
sentence on the count of readings alone) failed the test. 199 tests
pass.

Codex on a877c290, two findings, both real:

- `what-if-30-years.json`, the second example what-if, was refused: it did
  not carry the four Dashboard answers, so `read --compare` would not take
  it. It now carries the firm's answers, as the other two files do, and a
  test reads every settings file in the docs folder.
- The all-banks net charge-off series for other consumer, mortgage and home
  equity said they start in 2006 Q1; their first value is 2006 Q4, as the
  card series already said (a rate over the past four quarters). Checked
  against the 23 Oct pull's file: those three were the only starts of the 16
  that differed. A test holds every all-banks start to the rule.

Also, my own: each bank series' source note read "from the cache the pull's
FDIC cache", the path taken out and its words left in. It reads "from the
pull's FDIC cache" now, and the test says so. The 23 Oct pull's bank file
was built again with the fix from the same cache: all 16 series' figures
identical, only the 16 source notes changed; the pull's record now gives
that file's size, hash and the time it was built (22:32 UTC).

Two breaks (the mortgage start back to 2006 Q1; the 30-year what-if without
the Dashboard answers) and the old note wording each failed a test.
201 tests pass.

Codex on 1f41c1c3, two findings:

- **Fixed: the Dashboard's opening picks.** Every title was in the pick
  list whether or not its data came, so a pull whose bank build failed (an
  installed copy run outside threshold-engine/, say) opened on unemployment
  against an empty card series. The picks now come from the series that
  have readings in this pull. The test pull, which holds five series and no
  bank series, now opens on two series with readings; on the old code it
  opened on the empty card series, and the new test fails there.
- **Put to the firm, not changed: where each lead's year-apart correlations
  come from.** Codex asked for each lead and starting point's own, from its
  pairwise-complete annual readings, in place of the whole window's. Worked
  on eight real pairs: per subsample, r1 x r2 swings widely (card 30+
  against card losses, all banks: +0.01 to +0.25 across the 44 lead and
  start subsamples, against +0.10 over the window), because each rests on
  about ten pairs a year apart, and a correlation on so few is noisy and
  biased low. The verdicts matched in six of the eight; in two they moved,
  one each way (card 30+ against revolving credit gained the second leading
  by 6 months; the minimum-payment share against card losses lost +12). The
  usual practice is the whole series' autocorrelation, which the window
  gives from every month's pair a year apart. Recommended: keep it.
