# Next goal: out the door, through a walkthrough

**Set by the bank, 12 Oct 2026:** *"where we are in terms of getting it out the
door for use and we're gonna have to run it through a walk-through and out to
make sure it all works."*

This is the in-repo docket. Each item is ticked when it lands, with the commit
and the test that holds it, so the next session reads its job from the
repository and not from a conversation. The running log is `LOG.md`.

**What would end it:** every box below is ticked or handed back as a question
with a recommendation; the walkthrough has been run end to end with its
expected answers written down first; and a final check has been done by an
agent that has not seen the work, with the facts checked against sources, the
arithmetic checked by running it, and the workbook checked by opening it.

## 1. Decisions waiting on the bank (each with a recommendation)

- [ ] **The two scales.** The `cutoffs` command and the scenario cutoffs in
  `evidence` use the first scale; the workbook uses the centred one.
  *Recommend:* retire `cutoffs`, and have `evidence` report scenarios on the
  workbook's scale (`scale.py`), so there is one answer.
- [ ] **A window to run it from**, PocketBook-style, or the command line for
  version 1. *Recommend:* a small window (pick the CSVs, set the measure, run,
  open the workbook). The bank runs it on site, and a command line is a step
  someone gets wrong.
- [ ] **What version 1 includes from the side analyses.** *Recommend:*
  version 1 is the workbook from series files. The peer composite (pick a pack,
  gross and net) becomes version 2, built as a command that writes series files
  the workbook already takes. The inline analyses are saved as scripts in the
  evidence pack either way.
- [ ] **Cards' settings** (0.5 / 1.0 / z 2.5) and the leave-out windows as
  the starting point for the rehearsal: confirm.
- [ ] **Other consumer as two books** (student loans and the rest), from
  internal data: confirmed 7 Oct. Nothing to build; it is two input files.

## 2. Fix before the walkthrough

- [x] The command's help said "Two commands"; there are five. (Found on the
  clean install, 12 Oct; fixed the same day.)
- [ ] Lower-is-worse measures (a credit score) are tested in `scale.py` but
  never through the workbook. Add a workbook test with a mirrored series, and
  open it once in Excel.
- [ ] A monthly series is refused by the workbook ("the calendar is
  quarterly"). Confirm that's acceptable for version 1, or build it.
- [ ] Save the inline analyses (Laurel Road mix, lagged rates, post-Covid,
  growth without acquisitions) as scripts in the evidence pack, so every number
  shown can be re-run.

## 3. The walkthrough (rehearsal on public data)

Written first, as a script with the expected answer at each step, then run.
Like PocketBook's rehearsal: every step is done the way the bank would do it,
and every answer is read off the workbook, not off Python.

- [x] **Clean install.** Fresh clone, fresh Python, `pip install .`, workbook
  built; `pip install ".[test]"`, 138 tests pass. (12 Oct 2026)
- [ ] **Build** the four-product workbook from `tests/data/`. Expected: four
  rows on Thresholds, Check blank, 163 quarters on Data.
- [ ] **Each tab opened in Excel** and read against the script: Thresholds,
  Settings, Assess (each product), Chart, Evidence, Backtest, Glossary, Data,
  Run.
- [ ] **Each kind of Settings change** made by hand, with the expected effect
  written beside it: a leave-out window, a second window with a reason, each
  of the three distances, the on-the-line rule, a z that is refused. Each
  answer read off Thresholds, Assess and the dials.
- [ ] **A refusal of each kind** triggered on purpose, with the Check text
  read off.
- [ ] **Run tab** checked: fingerprints match the input files; decisions and
  reasons follow Settings.
- [ ] **The card scale tied out** to the public source: one line recomputed by
  hand from the Federal Reserve series, in a short tie-out exhibit.

## 4. On site (the bank)

- [ ] A bank-machine checklist: what Python and add-ons are needed, how to
  install without internet if blocked, how to run. (PocketBook has one to copy.)
- [ ] One internal series run on site, nothing brought back but the result's
  shape (whether it built, any refusal, anything unclear).

## 5. Final check

- [ ] An agent that has not seen the work reads WHAT-IT-DOES.md, runs the
  walkthrough script, opens the workbook, and reports anything that doesn't
  match.
