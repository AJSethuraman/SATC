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
  of four-quarter changes is about 2 to 6, and unemployment rises in two runs
  under a ±0.5 band. The repository's longer public charge-off series (the
  Fed's card rate from 1985 Q4; FDIC home equity and other consumer from
  1992 Q4) give four or five runs. On the card series the link holds without
  2007-10 (+0.54). The plan recommends testing on both, labelled.
- **Waiting on the firm:** 17 decisions, listed in the plan, and a note for
  Book 1's agent asking for the left-out quarters as a file.
