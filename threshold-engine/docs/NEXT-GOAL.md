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

## 1. Decisions (answered 12 Oct 2026)

- [x] **One scale.** The bank: take the recommendation. `cutoffs` and the first
  engine retired; `evidence` reports its scenarios and recency on `scale.py`.
- [x] **A window to run it from**, PocketBook-style. The bank: *"Yes."*
  `Thresholds.pyw` / `launcher.py`, 60 tests (12 Oct). Its Peers step is
  not wired yet: peers run from the command line. See section 2.
- [x] **Version 1 includes all of the side analyses, built into the tool and
  tested.** The bank: *"Nope, all of it. Test it and make sure it works."*
  That means FDIC pulls and caching, the peer roster, gross and net rates by
  bank and product with the structural-jump rule, the pack composite with
  best and worst, balance trends, growth without acquisitions, lagged rates,
  normalisation against a baseline year, and mix against the industry.
  Built 12 Oct: `peers pull`, `peers build` and the peer workbook (see
  WHAT-IT-DOES.md, "Peers"). Run end to end on the real cache and opened in
  Excel the same day.
- [x] **Cards' settings** for the rehearsal: 0.5 / 1.0 / z 2.5, crisis and
  pandemic periods left out. The bank: *"That works."*
- [x] **Other consumer as two books**, from internal data (7 Oct).
- [x] **Delinquency and nonaccrual by product, for every peer.** The bank, 12
  Oct: *"1 and 2 are good for v1."* FDIC fields confirmed to exist on 12 Oct
  against JPMorgan's 2026Q2 data (all 15 returned values): `P3` (30-89 days),
  `P9` (90+ days, still accruing) and `NA` (nonaccrual), for `CRCD`, `RERSFM`,
  `RELOC`, `CONOTH` and `AUTO`. Built as rates on the quarter-end balance, the
  TTM average of the four quarter-end rates, and "90+ including nonaccrual"
  (P9 + NA). All of them are built; the bank picks per measure. The bank: *"It
  depends and you don't need to know, if you're making all 3 it shouldn't
  matter."* Built 12 Oct to `docs/V1-ROUND2-SPEC.md`: `peers/delinquency.py`,
  the Delinquency and DelinquencyData tabs, `--delinquency yes|no`, 150
  series CSVs. Tied to the filing: KeyBank card 90+ accruing 2026Q2, read
  from the workbook in Excel, is 9,346 ($000), the same as RC-N 5.a column B
  (`docs/tie-out/keybank-card-90plus-2026-10-12/`).
- [x] **Templates for internal data on site.** The bank, 12 Oct: *"1 and 2 are
  good for v1."* One CSV layout plus a checklist per internal measure (WAPD,
  refreshed credit score as lower-is-worse, early payment default, and the
  two-book splits: student loans vs the rest, rewards vs non-rewards cards), and
  a command that checks a file against its template before a build.
  Built 12 Oct: `templates.py`, `template list|write|check`, seven templates.
- [ ] **Pack composite, four-quarter average: does the jump rule apply?** The
  band and each bank's own average leave out a bank mid-acquisition; the
  composite's average (the mean of four composite quarter-end rates) keeps
  it. On the fixture that is 9–43 bank-quarters per product (e.g. JPMorgan
  mortgage in 2023Q2–Q4, the First Republic quarters). Recommended: yes,
  apply it, so composite and band are built from the same banks. Until the
  bank answers, each composite row names the banks concerned
  (`avg4_jumped`) and the CSV notes say so.

## 2. Fix before the walkthrough

- [x] The command's help said "Two commands"; there are five. (Found on the
  clean install, 12 Oct; fixed the same day.)
- [ ] Lower-is-worse measures (a credit score) are tested in `scale.py` but
  never through the workbook. Add a workbook test with a mirrored series, and
  open it once in Excel.
- [ ] A monthly series is refused by the workbook ("the calendar is
  quarterly"). Confirm that's acceptable for version 1, or build it.
- [x] ~~Save the inline analyses as scripts.~~ Superseded: they are in the
  tool now (Mix, Lagged, Normalisation and Balances tabs), with the spec's
  numbers as acceptance tests.
- [x] The window's **Peers** step: pull and build from the window, through
  `peers/run.py`, the same function the command line calls (12 Oct).
- [ ] Code 215 ("Failure Multiple Acquirer") counted as an acquisition,
  decided without the bank (LOG.md, 12 Oct). Open to its veto.

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
