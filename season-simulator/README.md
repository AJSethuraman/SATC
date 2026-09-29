# season-simulator

**The 2027 tax season, played day by day through the real SATC code.**

Sixty invented clients walk from 1 January to 15 October 2027 — the ones who
send everything in February, the ones who go quiet, the ones who need an
extension, the partnership whose K-1 holds up two personal returns. Every
thing the owner does goes through a real front door: a `satc_system` route
(Flask's test client, in-process) or a `client-documents` command
(`cli.main([...])`). The machine clock is frozen on each simulated day, so the
routes run unmodified. Every day, every screen and every engine is read, and
50 invariants — each citing the rule it holds the code to — are checked
against what they say.

It answers one question: **when the season actually happens, what do the two
applications tell the firm, and where is that wrong?** The answer for three
seeds is in [`reports/`](reports/).

No production code was changed to build this. The recon brief showed that a
frozen clock reaches every read the season depends on, so no clock seam was
needed; the one clock read that an explicit `--today` does not reach is
reported as a finding (K1) rather than patched.

## Run it

```
cd season-simulator
python -m venv .venv && .venv\Scripts\activate          # Windows
pip install -e "../satc_system[dev]" -r ../client-documents/requirements.txt -e ".[test]"

python -m season_sim run --seed 42 --report               # one full season, ~20 min
python -m season_sim run --seed 42 7 1066 --report        # three seeds, one after another
python -m season_sim repro --seed 42 --until 2027-03-20 --client SIM-008 --check B8
python -m season_sim mutants --seed 42                    # check the checker (below)
python -m pytest -q                                       # the mechanics, ~2 min
```

`run` writes `world.json`, `findings.jsonl`, `summary.json` and `timings.json`
under `%TEMP%\satc-sim\out\seed-N\` and, with `--report`, the Markdown and HTML
report into `reports/`. `--days checkpoints` reads fourteen dates instead of
all 288 (the owner still acts every weekday). `--keep` keeps the run directory
for inspection.

**Do not install the PyPI `requests`.** client-documents has its own
`requests.py` and `packaging.py`; the simulator refuses to run if either name
resolves anywhere but `client-documents/`.

## How it is built

| Module | Job |
|---|---|
| `guard.py` | Runs before anything imports satc. Pins `SATC_DATA_DIR`, `SATC_ENGAGEMENTS`, the library and intake roots to a run directory under `%TEMP%\satc-sim\` by **assignment** (satc's own conftest uses `setdefault`, so an exported value would win there); sets `SATC_ROLE=owner` (firm decision D2), `SATC_OLLAMA=0` and a fixed Flask secret; removes every other `SATC_*` variable and `ANTHROPIC_API_KEY`. Refuses a run directory under `~/.satc`, `Documents\Main`, the stale `C:\Users\ajish\SATC`, `C:\Occam`, any `C:\DRAKE*`, or the worktree — by path arithmetic, never touching them. Then replaces sockets, Square (`payments.processor`), the Windows credential store and desktop Outlook with functions that raise `SimRefused`. |
| `paths.py` | Puts `client-documents/` at `sys.path[0]` and this checkout's `satc_system/src` right behind it, then asserts `requests` and `packaging` resolve inside client-documents. |
| `clock.py` | `time_machine.travel(<day> 14:00 UTC, tick=False)` per simulated day; a seeded `uuid.uuid4` (its only caller is `ids.opaque_id`); `leaks()` for the clock-leak audit. |
| `world.py` | Draws everything random once, from `random.Random(seed)`, and writes `world.json`: who the clients are, when each document arrives, who never signs. The season is then a script. |
| `firm.py` | The two actors. The world says what happens; the owner records it through a door. |
| `doors_satc.py`, `doors_cd.py` | The front doors, and nothing else. Every client-documents call carries `--store`; `invoice` always `--no-link`; `event` always `--skip-render --no-pdf --out RUN/out`. |
| `observe.py` | The daily read pass: `/today`, the engine behind it, the agent door, `/work` and every job page, the documents sweep, the season board and `cli season --today`, the signature list, `may_file`, the stages bar, the close-out sweep. Both SQLite files and the engagements tree are hashed before and after (B5). |
| `invariants.py` | The checks. Each returns `(hits, examined)`; `examined` is the denominator (S2). |
| `observations.py` | What the season looked like where no rule says what it should be. Never called a failure. |
| `findings.py`, `report.py` | Hits folded into one finding per (rule, client), first day's evidence kept; the report. |
| `mutations.py` | Real functions broken in this process only, for checking the checker. |

One worker process per seed: `satc.app.state` builds `STATE` at import time
and it cannot be re-pointed. The launcher gives each worker
`PYTHONHASHSEED=0` and `PYTHONDONTWRITEBYTECODE=1`, and compares the worktree's
`git status --porcelain --ignored` before and after it — a difference is a
run-level failure.

## The owner, and every other number: assumptions

Everything in `scenario.yaml` is an **invented simulation parameter**, labelled
as one. Only one date is anchored to authority: core income documents cannot
arrive before 2 February 2027, because Forms W-2 and 1099-NEC are furnished by
31 January (`satc_system/configs/obligations/federal.yaml`) and 31 January 2027
is a Sunday.

| Assumption | Value |
|---|---|
| Clients | 60: 16 on time, 6 late papers, 4 go quiet, 3 never sign the 8879, 2 joint returns where the spouse never signs, 5 extensions, 4 waiting on a partnership K-1, 2 partnerships, 3 S corporations, 2 C corporations, 3 disengage in March, 3 returning clients who never come back, 2 amended 2025 returns, 2 re-quotes, 3 with a rental |
| Returning / joint / check payers | 40% / 20% / 30% |
| The owner works | weekdays; records arrivals the same day |
| Preparation | 4 returns started a day, 2 business days each, earliest statutory date first |
| Extensions | filed a week before the original date for anything not ready — *"We will file an extension on your behalf where one is needed"* (Tax Preparation letter, line 83) |
| Billing | at delivery, through **one door per seed**: even seeds bill in satc_system, odd seeds in client-documents |
| Transmitting | only when client-documents' `may_file` is clear; then `cli.py close` records what was filed |
| Disengagement | open requests closed as not-applicable with a reason — the only satc door that stops a chase (`withdrawn` is never set) |
| A refusal by the pre-send gate | recorded as evidence, then sent with `--force --reason`, as the refusal instructs |
| A satc billing refusal naming the estimate | the estimate total billed as one line, as the refusal instructs |

## What it checks

Kinds: **failure** (the code breaks a rule written in this repository),
**cross_store** (the two applications disagree where the firm recorded that
they must agree), **known** (reproduced, not new). Each finding is also sorted
into **clear bug** or **the firm's decision**.

| # | What must hold | Kind | If it fails | Source |
|---|---|---|---|---|
| A1 | due dates land on business days, never early | failure | clear bug | `docs/DESIGN-PRINCIPLES.md:49`; `satc_system/tests/test_obligations_calendar.py:138`; `satc_system/tests/test_obligations_calendar.py:147` |
| A2 | the two deadline engines agree | failure | clear bug | `satc_system/configs/obligations/federal.yaml:61`; `satc_system/configs/obligations/federal.yaml:74`; `client-documents/deadlines.py:29-41`; `docs/SOFTWARE-TENETS.md:150` |
| A3 | the materials deadline on the letters is the computed one | failure | clear bug | `client-documents/settings.py:83-127`; `client-documents/deadlines.py:154` |
| B1 | one row per thing, one chase per client-year | failure | clear bug | `docs/DESIGN-PRINCIPLES.md:235-243`; `satc_system/src/satc/actions/__init__.py:124-127`; `satc_system/tests/test_actions.py:99` |
| B2 | every row carries its evidence | failure | clear bug | `docs/DESIGN-PRINCIPLES.md:243`; `satc_system/tests/test_actions.py:241` |
| B3 | Today is in rule order, and the screen shows the engine's order | failure | clear bug | `satc_system/src/satc/actions/propose.py:810`; `docs/SOFTWARE-TENETS.md:103`; `satc_system/src/satc/app/templates/today.html:67` |
| B4 | the same day gives the same queue | failure | clear bug | `docs/DESIGN-PRINCIPLES.md:130-137`; `satc_system/tests/test_actions.py:199` |
| B5 | reads write nothing | failure | clear bug | `docs/DESIGN-PRINCIPLES.md:148-149`; `satc_system/tests/test_actions.py:251` |
| B6 | every client waiting on paper gets chased | failure | clear bug | `satc_system/src/satc/actions/propose.py:150-177`; `canon/corpus/the-firms-own-words.md:849` |
| B7 | urgency follows the rule as written | failure | clear bug | `satc_system/src/satc/actions/propose.py:111-120`; `satc_system/src/satc/actions/propose.py:176`; `satc_system/src/satc/actions/propose.py:229-251` |
| B8 | a deadline row is dated at the operative deadline | failure | firm's decision | `satc_system/src/satc/obligations/due_dates.py:109-110`; `docs/DESIGN-PRINCIPLES.md:64-74` |
| B9 | a row built on an assumption says so | failure | clear bug | `satc_system/src/satc/actions/propose.py:241`; `docs/DESIGN-PRINCIPLES.md:27-40` |
| B10 | no row claims what nobody recorded | failure | clear bug | `satc_system/tests/test_actions.py:173`; `satc_system/tests/test_actions.py:365` |
| B11 | a client with nothing started for the year is invited | failure | clear bug | `satc_system/src/satc/actions/propose.py:44`; `satc_system/src/satc/app/today_views.py:86`; `docs/SOFTWARE-TENETS.md:706` |
| B12 | the agent sees what the owner sees | failure | clear bug | `satc_system/src/satc/agent/tools.py:103-114`; `docs/SOFTWARE-TENETS.md:103` |
| B13 | the prior-year question does not ask for a new-client-only document | failure | firm's decision | `satc_system/configs/workflows/personal_1040_core.yaml:170-176`; `satc_system/src/satc/actions/propose.py:180-200`; `satc_system/src/satc/rollover/diff.py:111-138`; `docs/DESIGN-PRINCIPLES.md:235-243` |
| C1 | every job is in exactly one half of the board | failure | clear bug | `satc_system/src/satc/app/work_views.py:46-57` |
| C2 | nothing finished is offered as workable | failure | clear bug | `satc_system/src/satc/work/stage.py:73-86` |
| C3 | delivered and complete need a recorded fact | failure | clear bug | `satc_system/src/satc/work/stage.py:57-62`; `satc_system/src/satc/work/stage.py:96-119` |
| C4 | a job waiting on a blocking document says so | failure | clear bug | `satc_system/src/satc/work/stage.py:126-129`; `satc_system/src/satc/work/stage.py:147-153` |
| C5 | the board and the job page agree on a job's stage | failure | clear bug | `docs/SOFTWARE-TENETS.md:103`; `satc_system/src/satc/work/queue.py:559`; `satc_system/src/satc/app/work_views.py:280` |
| C6 | the work order is total and repeatable | failure | clear bug | `satc_system/src/satc/work/queue.py:567-570`; `satc_system/tests/test_work_queue.py:245` |
| C7 | a job stronger on every factor ranks higher | failure | clear bug | `satc_system/src/satc/work/queue.py:139-152`; `satc_system/tests/test_work_queue.py:1-8` |
| C8 | the deadline factor is known exactly when a duty is on file | failure | clear bug | `satc_system/src/satc/work/queue.py:37-41`; `satc_system/src/satc/work/queue.py:400-409` |
| C9 | the work queue ranks against the operative deadline | failure | firm's decision | `satc_system/src/satc/obligations/due_dates.py:109-110` |
| D1 | the documents sweep adds up to the register | failure | clear bug | `satc_system/src/satc/intake/chasing.py:113-127`; `satc_system/src/satc/intake/chasing.py:195-196`; `docs/SOFTWARE-TENETS.md:72` |
| D2 | the sweep is longest-wait first and holds back today's asks | failure | clear bug | `satc_system/src/satc/intake/chasing.py:191-199`; `satc_system/src/satc/intake/chasing.py:202-210` |
| D3 | the signature list holds everyone with a signature out | failure | clear bug | `client-documents/signing.py:612-647` |
| D4 | an ended engagement is not chased for signatures | failure | clear bug | `docs/DESIGN-PRINCIPLES.md:235-243`; `client-documents/signing.py:612-647` |
| E1 | every engagement is on the board or named unplaced | failure | clear bug | `client-documents/deadlines.py:414-422` |
| E2 | the board is soonest first | failure | clear bug | `client-documents/deadlines.py:472` |
| E3 | nothing is placed without a readable form and year | failure | clear bug | `client-documents/deadlines.py:399-405` |
| E4 | `cli season --today` prints the board it computes | failure | clear bug | `client-documents/cli.py:2094-2097`; `docs/SOFTWARE-TENETS.md:103` |
| E5 | an amended return is not placed at the original return's dates | failure | firm's decision | `client-documents/deadlines.py:348-356`; `docs/DESIGN-PRINCIPLES.md:64-74` |
| E6 | an ended engagement is not shown as due | failure | clear bug | `docs/DESIGN-PRINCIPLES.md:64-74`; `docs/DESIGN-PRINCIPLES.md:235-243`; `client-documents/deadlines.py:414` |
| E7 | an extended engagement is shown at its extended date | known | known | `client-documents/deadlines.py:197-202`; `canon/corpus/decisions-in-their-words.md:123-125` |
| F1 | the transmit gate blocks on every missing promise | failure | clear bug | `client-documents/signing.py:486-570`; `satc-handoff/04-TEMPLATES/SATC Tax Return Delivery Letter.html:91`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:95` |
| F2 | the stages bar never runs ahead of itself | failure | clear bug | `client-documents/stages.py:29-34`; `client-documents/stages.py:108-119` |
| F3 | the close-out control examines every engagement | failure | clear bug | `client-documents/closeout.py:278-305` |
| G1 | each ref names exactly one satc engagement | cross_store | firm's decision | `LOG.md:847`; `satc_system/src/satc/persistence/store.py:701-721`; `satc_system/tests/test_the_join_has_a_writer.py` |
| G2 | the price shown through the ref is the estimate | cross_store | firm's decision | `LOG.md:744`; `LOG.md:848`; `satc_system/src/satc/billing/engagement_price.py:98-161` |
| G4 | the papers-due date matches what the client was told | cross_store | firm's decision | `LOG.md:847`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:79`; `client-documents/registry/firm-settings.yaml:114`; `satc_system/configs/firm_policy.yaml:34-39` |
| G5 | what client-documents records, satc_system reflects | cross_store | firm's decision | `LOG.md:847`; `satc_system/src/satc/actions/__init__.py:96-98` |
| G6 | both systems know whether the bill is paid | cross_store | firm's decision | `LOG.md:847-854`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:95`; `client-documents/signing.py:541-572`; `satc_system/src/satc/app/today_views.py:81-96` |
| G8 | no extension flag while the client is inside the date they were told | cross_store | firm's decision | `LOG.md:847`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:79`; `satc_system/src/satc/actions/propose.py:254-280`; `satc_system/configs/firm_policy.yaml:34-39` |
| K1 | an explicit --today governs the whole read | failure | clear bug | `client-documents/cli.py:3082`; `client-documents/deadlines.py:414-434`; `client-documents/deadlines.py:395` |
| L1 | a document the process calls for can pass its own gate | failure | clear bug | `satc-handoff/04-TEMPLATES/FIELDS - Extension Notice.md:54`; `satc-handoff/04-TEMPLATES/FIELDS - Extension Notice.md:68`; `satc-handoff/04-TEMPLATES/SATC Extension Notice.html:75-81`; `client-documents/registry/required.yaml:60-66`; `docs/SOFTWARE-TENETS.md:150` |
| L2 | following the billing screen's instruction gives the quoted price | failure | clear bug | `satc_system/src/satc/billing/invoice.py:217-257`; `LOG.md:848` |
| L3 | an extension notice can restate what the extension changed | failure | firm's decision | `client-documents/consistency.py:313-345`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:83`; `client-documents/registry/lifecycle.yaml` |
| L4 | a payment made another way can be recorded | failure | firm's decision | `client-documents/signing.py:564-570`; `client-documents/registry/firm-settings.yaml:100-102`; `client-documents/payments.py:622-634`; `client-documents/cli.py:859-900`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:95`; `docs/SOFTWARE-TENETS.md:706` |

Observations — stage dwell, the Work queue against a real March, SLAs at
season end, the two chase thresholds, the K-1 lag, facts with no door — are in
the report under their own heading and are never failures.

## How we know it can fail

Principle 12 (`docs/DESIGN-PRINCIPLES.md:224`): a check that has never failed is
not evidence. Two layers:

**Every checker goes red on a planted violation.** `tests/test_checkers_go_red.py`
builds the smallest snapshot that breaks each rule, with the real record classes,
and asserts the checker reports it; most also assert the clean twin stays
clean. A test fails if any registered invariant has no such test. The tests
were themselves checked: with B6, E6, G4 and L2 replaced by a checker that
never fires, exactly those four tests failed.

**Six real functions, broken on purpose, each caught.** `python -m season_sim
mutants` runs a baseline season and then one season per mutation. Each
mutation replaces a real production function **in the worker process only** —
nothing on disk changes, and the process ending is the restore. Run on
29 September 2026 (commit `7ddb58e6`), seed 42, 16 clients, checkpoint days:

| Mutation | What was broken | Must fire | Baseline findings | Mutant findings | |
|---|---|---|---|---|---|
| `deadline_shift` | client-documents `deadlines.filing_date` one day later | A2 | 0 | 15 | caught |
| `drop_chase` | `chase_outstanding` removed from `build_queue` | B6 | 0 | 14 | caught |
| `unsorted_queue` | `build_queue` sorted with urgency reversed | B3 | 0 | 2 | caught |
| `board_drops_job` | the work board silently drops its first job | C1 | 0 | 4 | caught |
| `signing_list_drops` | `signing.waiting` drops its first engagement | D3 | 0 | 2 | caught |
| `season_unsorted` | `deadlines.board` returns its rows reversed | E2 | 0 | 1 | caught |

The breaks spread the way they should. `deadline_shift` also turned A1 (a due
date no longer on the statute's day) and A3 red, and client-documents' own
guard in `settings._materials_deadline` then refused to print any letter date
— which the simulator recorded as a crashed door call rather than dying.
`unsorted_queue` was caught twice over: the rows out of rule order, and the
`/today` page (which groups by urgency) no longer listing the engine's order.

Three of these (A2, B6, E2) run in CI on every pull request
(`tests/test_season.py`).

## What CI holds, and what it does not

CI (`.github/workflows/test.yml`, job `pytest (season-simulator)`) holds the
**mechanics** only, as S22 asks (`docs/SOFTWARE-TENETS.md:389-416`): the guard
refuses live paths and bans the outside world; one seed writes byte-identical
findings twice; every checker goes red on a planted violation; three mutations
are caught; the core checks examined something; every citation points at a line
that exists. **It never asserts "zero findings", and never asserts that a
particular finding exists** — either would be a test that goes green or red for
the wrong reason (S25). The full season is desk-run, and its report is read.

## Run log

| Date | Seed | Billing door | Days read | Findings | Clear bugs · firm's decision · known | Wall time | Commit |
|---|---|---|---|---|---|---|---|
| 2026-09-29 | 42 | satc_system | 288 of 288 | 370 | 138 (7 rules) · 224 (9) · 8 (1) | 19 min | `7ddb58e6` |
| 2026-09-29 | 7 | client-documents | 288 of 288 | 335 | 116 (6 rules) · 211 (10) · 8 (1) | 19 min | `7ddb58e6` |
| 2026-09-29 | 1066 | satc_system | 288 of 288 | 394 | 147 (7 rules) · 237 (9) · 10 (1) | 20 min | `7ddb58e6` |

All three: 60 clients, 0 checker crashes, every run-level guard held (worktree
unchanged, store in the run directory, environment still pinned, the
client-documents default store and `out/` untouched, no banned call). The three
ran in parallel on the Forge. A finding count is one per (rule, client), not
one per day; the denominators table in each report says how much each rule
examined.

The headline for the firm, the same on every seed:

* **Clear bugs:** the board and the job page disagree about a delivered job
  (C5); the season board shows closed-out and disengaged engagements OVERDUE
  forever, including last year's (E6); a returning client is never invited
  (B11); an extension notice with no payment can never pass the pre-send gate
  (L1 -- the compliance floor's only satisfying sentence sits inside
  `[[IF PaymentEnclosed]]`); the signature list keeps chasing disengaged
  clients (D4); `cli season --today` still reads the machine clock (K1);
  satc's billing screen tells the owner to put the whole estimate on every
  engagement-priced line, so doing what it says bills the estimate once per
  line -- $975 against a $325 estimate (L2, satc door only).
* **The firm's decision:** satc's cutoff (1 Mar / 1 Feb) is not the date the
  client was told (25 Mar / 22 Feb) and Today proposes extensions for clients
  inside their date (G4, G8); filed, extended and disengaged clients are told
  their return is overdue (B8) and still chased (G5) because no door carries
  those facts into satc_system; whichever system bills, the other cannot see
  it (G6), and under client-documents billing **no return could be
  transmitted all season** -- 50 delivered, 0 closed out -- because a check
  has no door (L4) and card payments only settle through Square; every
  extension notice is also refused because the interview's first-deliverable
  promise predates the extended materials date and the event cannot restate it
  (L3); returning clients are asked where last year's prior-year return went
  (B13); amended returns sit at the original return's dates (E5); satc_system
  has no workflow for a Form 1120 (G1).

## Not covered

See the last sections of each report. In short: no document is read or opened,
no money moves, no Filing/extension/disengagement exists in satc_system because
no door writes one, profiles are not persisted so only federal returns reach
Today, fiscal-year filers and disaster postponements are not modelled, and
client-documents' browser front door was not driven.
