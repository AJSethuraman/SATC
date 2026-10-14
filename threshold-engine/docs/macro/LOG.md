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
