# PocketBook handoff

Read this first in any new session that touches PocketBook. It is one page by design. A new session that starts
here does not need the conversation that built the tool, and that is the point: a long session is the main cost.

## What it is

A loan-book analysis tool for a consumer cards book (Booked = committed credit line). It finds pockets (a band of
one column x a segment) that lose more than their share, tests each with a shuffle test with a multiple-testing
allowance, and writes an Excel workbook. Optionally it also writes an audit workbook that proves one randomly chosen
pocket step by step. The analyst runs it on a bank machine from one pasted script.

## Where things are

| What | Where |
|---|---|
| Code | `src/pocketbook/`: `ingest` reads the extract, `engine` and `perm`/`stats` do the arithmetic and the test, `results`/`summary_chart`/`compare`/`look`/`glossary` write tabs, `audit` writes the audit workbook, `book` runs Set up and Run, `launcher` is the window |
| How copy must read | `VOICE.md` (professional credit-risk register; facts, calculations and rules only, no advice) |
| Standing rules | `TENETS.md` (method said once; a check shown only where it can fail) |
| Every decision, in the firm's words | root `BACKLOG.md` §6d and its Done log |
| What the analyst follows at the bank | `docs/BANK-MACHINE-CHECKLIST.md` (HTML/PDF are built from it with weasyprint) |
| Independent tie-out of the audit workbook | `docs/audit-tieout-2026-10-03/` (`tieout.py` imports nothing from PocketBook) |
| Planted bugs | `tools/mutation_check.py` (each entry's old text must occur exactly once) |

## How a change ships

1. Branch, change, and run the **targeted** tests for the files touched: `cd pocketbook && python -m pytest -q -p no:cacheprovider tests/<file>.py`. Leave the full suite (about 1,100 tests, 50+ minutes) to CI.
2. For each new guard, add a planted bug to `tools/mutation_check.py` and confirm it is caught with DISPLAY unset.
3. Draft PR. CI must be green on a head that contains current `main`.
4. Review: Codex has been over its usage limit; the firm's rule (3 Oct 2026) is green CI plus an independent review by a separate agent, noted on the PR. Fix every verified finding before merging.
5. Merge (merge commit, pinned head). Then build the kit: `python3 pocketbook/tools/bank_kit.py --out <scratchpad>/kit`. Check that the single script unpacks with "N files, every one checked", copy `PocketBook.py` to `PocketBook.txt` and send it with the checklist PDF. The firm renames it to `.py`.

## Working with the firm

- Short, results-first replies. One decision at a time, each with a recommendation and what happens either way.
- Show before/after for layout and wording changes before building them.
- Never real bank data in the repository; synthetic or public only. Figures derived from LendingClub data are not published (4 Oct 2026).

## Keeping the cost down

- **Use a fresh session per feature.** Start from this file, not from an old conversation. End the session by updating this file's Open items.
- **Settle the questions before building.** Wording, layout and behaviour get decided first; rework was the largest cost.
- **Use smaller models for routine work** (reviews, CI checks); keep the largest model for design and hard fixes.
- **Run targeted tests locally;** the full suite and the planted bugs run in CI.
- **Watch a PR only while it is yours to merge.**

## Open items (4 Oct 2026)

- **First Run with the new kit:** compare Record's rows read with the source system's loan count. Before 4 Oct, certain control characters could split one CSV row into two without warning. Fixed; the comparison confirms whether earlier Runs were affected.
- **Excel itself is unverified.** Every check used LibreOffice. Ask the firm to report any "Excel repaired this file" message.
- **The launcher's Next overwrites a category limit typed on Control.** Existing behaviour, not yet fixed.
- **Only the audit workbook and Glossary are rewritten to `VOICE.md`.** The other tabs still need the same pass. Show the firm a numbered before/after page first.
- **The Summary vintage chart breaks past about 42 distinct origination years.** Not a card-book concern.
- **The filter view limits can be bypassed:** a pair refused at 49 views is accepted with a small third filter. The firm chose to leave it.
- **Proposed next project:** a tool that sets objective, product-specific thresholds for inherent (gross charge-offs) and residual (net charge-offs) risk ratings. Design first; the firm holds the brief.
