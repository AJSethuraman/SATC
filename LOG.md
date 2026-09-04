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

### The Square payout field, and what it cannot tell you

The firm: *"that $482 is in my bank right now, i'm unsure you can see it through
this but that is certainly interesting."*

They were right to doubt it. Square's Payouts API reports
`destination.type: SQUARE_STORED_BALANCE` for **all three** payouts — including
the April and May ones the firm confirms reached their bank. The field reads
identically for money that arrived and money that has not, so it cannot answer
"did the transfer land". The suggestion to add it to `payments --check` is
withdrawn: it would have been a line that looks like an answer and is not one.

### Every screen, opened

*"it's time to work through all of the screens — like for real."*
`tests/test_every_screen_in_a_browser.py` now opens all 27 of them in Chromium,
with the list discovered from the app's own `url_map` so a screen added next
month is covered the day it lands. Two findings, and **two of the first three
were my own test being wrong**, which is the reason to check the checker:

- the contrast walker never read an element's own background, so it reported a
  badge that was dark red on pale pink as 2.08:1 red on navy — a colour that
  was never wrong and would have been "fixed";
- the STAGED badge is genuinely 3.85:1, on the screen where a preparer confirms
  an extracted figure before it reaches a workpaper. Darkened to 4.80:1;
- `/source` was flagged as a broken screen. It is not a screen: it serves an
  original client document and refuses any path the last intake did not read.
  The 404 was the allow-list working, and it is now asserted rather than merely
  excluded — an exclusion outlives the guard it was written around.

### And every button

*"sounds like you know what to do, then."*

The crawl follows links rather than reading a list, so it reaches **46 pages**
where the screen sweep reached 27 — the difference being every detail page,
which is where the buttons live. **203 forms**, and every one of them lands on
a route that accepts the method it uses. Then all 202 POST buttons were pressed
with an empty form, which is what a person does by accident: **no 500s**.

**Three of the findings were the checker, not the app.** It reported two dead
buttons that were `method="get"` filter forms; it called two self-posting forms
orphans when a form with no `action` posts to its own page; and its own registry
of "endpoints with no button" was wrong in both directions at once — one missing,
three carrying excuses that had gone stale.

**And two of my own tests were order-dependent**, which is the fault this
repository hunts hardest. `STATE` is module-level, so the crawl sees whatever
store the previous 1,600 tests left behind: staged fields get confirmed, drafts
get cleared, and buttons that render alone do not render after a full run. Split
rather than pinned — what is structurally never a button is asserted in both
directions, and what depends on the data is documented and asserted in neither.

### Still open at the end of the day

- **W5 / B4** — the seven-year destruction promise has no mechanism. Deferred
  to run alongside the backup work.
- **W8** — written notice is recorded nowhere. Gated to the bookkeeping launch.
- **B8** — the disk is not encrypted. Measured, recorded, not acted on.
- **The WISP** — 49 open questions and no signature.
- ~~Every screen except Documents has never been opened by anything.~~ **Closed 4 September.** All 27 open in a browser on every run. What is still unasserted is what the BUTTONS on them do: only the Documents screen has had anything pressed, and there are 48 POST endpoints.
