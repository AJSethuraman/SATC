# The practice log

**What the firm decided, in their words, and what it caused.**

Canon's behaviour 14 is *keep the log where the work is*, and the docket is
written to read from this file. There was no such file until 4 September 2026,
so every answer given that day lived in three places and no single one —
commit messages, `docs/DEFECT-REGISTER.md`, and pages published to the firm.
A session tomorrow would have started from whichever it happened to find.

**What belongs here:** a decision the firm made, quoted where they wrote it,
with what it caused. Not a summary of the work — that is what the git history
and the defect register are for.

**What does not:** anything a client said, any name, any figure off a return.
This file is read by every session and shared with none of them.

---

## 4 September 2026

The day Square went live, the day the payment loop was proved with real money,
and the day the firm asked whether anything actually presses the buttons.

### Decided

| | The firm | What it caused |
|---|---|---|
| **The retention clock** | *"end of engagement"*, then: *"you can look at the engagement letter, it outlines the end of the engagement and you likely need to build a control to record it"* | `satc/retention.py`. Read out of the letters rather than assumed: delivery, or signature **and** transmission, or written notice — never acceptance, and payment is not in the clause. Bookkeeping has no "concludes when" at all, so notice is its only ending |
| **Bookkeeping retention** | *"note those as things to deal with when we are ready to market the bookkeeping officially"* | W8 gated to the bookkeeping launch. A tax engagement ends by itself; a bookkeeping one never does, so it cannot get a disposal date until written notice is recorded |
| **No login for the local apps** | *"this is all local to here and you'd have to be literally on my lan"* | Compensating controls written into WISP §A4a. Still needs his signature as Qualified Individual |
| **The screen not locking** | *"leave it and outline it in the WISP so we know it's a risk"* | B11 recorded as an **accepted risk**, not closed. It is the assumption A4a rests on |
| **`forge-readonly`** | *"Disable it"* | Disabled. `Account active: No`. Its Full Name was "Forge read-only agent" — created deliberately, never used |
| **The Render deploy workflow** | *"Delete it"* | `.github/workflows/deploy-invoicer.yml` deleted. It fired on every merge and failed every time; the hook was never set, so nothing ever reached Render |
| **Invoicer** | *"Retire Invoicer"* | Closed PR #139. The firm takes Square; Invoicer was Stripe end to end |
| **The $1 live test** | *"i can invoice myself for $1 and pay it with a live card as our final test"*, then *"i got the notification from square that i was paid $1 i trust it"* | Done. 7 of 7 on the live account, order `T3yIEJw8D0j…`, settled. Recorded as P1 |
| **The vault key** | Confirmed stored in Bitwarden | W6 closed. The copy that matters is the 44 characters inside the DPAPI wrapper, not the wrapped file — a wrapped copy cannot be unwrapped on a replacement machine |
| **Three non-practice PRs** | *"Close those three"* | #100, #101, #102 closed. Branches kept |
| **The other 38** | *"Leave them, triage later"* | Untouched. One triage of all of them when there is a quiet slot |
| **The cross-checkout venv** | *"Fix it"* | `client-documents/.venv` built in the real checkout; the launchers no longer reach into a scratch folder |
| **Opening the software** | *"Go and look"*, then *"do the instructions you understand have you not only open screens and screenshot them, but you are pressing buttons and opening screens and 'typing' stuff to make sure it actually works?"* | Five browser tests that press the buttons, and the bug they immediately found — see below. Plus `exercise.py` run for the first time in this checkout |
| **This file** | *"Start one, backfill today"* | This file |

### What the firm's questions found, that the software did not

- **The N/A button recorded documents as received.** An empty reason box took
  the *satisfied* path, so the register would say a client sent a document they
  had not. The refusal existed in the model and the browser could not reach it.
  Found by the first test that pressed a button, an hour after the firm asked
  whether anything did. 1,685 tests were green throughout.
- **Every panel count was invisible** — `#1F2733` on `#0B1F3A`, 1.10:1, across
  32 headings in ten templates. Found by opening the page.
- **The test suite was driving desktop Outlook**, opening compose windows on
  the firm's own screen across two runs, four of which saved themselves into
  Drafts. *"it opened once and i didnt know what was happening."* Nothing was
  ever sent — there is no `.Send()` in this codebase. Fixing it also made the
  suite five times faster: 957s → 197s.

### Corrections to the record

- Commit `0906429` claimed it recorded the BitLocker finding and the retention
  answer. It carried three files, not four; a `git stash` had dropped them.
  Redone in `1967bf1`.
- The open pull request count was reported as 12, then 14, then 20 in one day.
  All three were a row limit read back as a total. **It is 38.**
- `CLAUDE.md` said the suite was 1,412 / 2 and that `exercise.py` produces
  **190 documents**. Measured 4 September: the suite is **1,434 / 2** and the
  harness produced **109** documents across 29 scenarios. The count was
  corrected; the 190 was not explained and is flagged in place rather than
  quietly rewritten.
- **Ten tests skip until the harnesses have run**, and say so only in the
  skip reason. A checkout that has never run them reports 1,424 / 12 and looks
  healthy. Both checkouts now read 1,434 / 2, and the two remaining skips are a
  real data condition rather than a missing capability.

### Still open at the end of the day

- **W5 / B4** — the seven-year destruction promise has no mechanism. Deferred
  to run alongside the backup work.
- **W8** — written notice is recorded nowhere. Gated to the bookkeeping launch.
- **B8** — the disk is not encrypted. Measured, recorded, not acted on.
- **The WISP** — 49 open questions and no signature.
- **Every screen except Documents** has still never been opened by anything.
