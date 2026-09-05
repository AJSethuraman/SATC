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

## Saturday 5 September 2026 — I raised a collision that was not there

I told the firm their price decision collided with two things they believe, and
stopped D10 one step from finished to say so. **The challenge was wrong, and it
was wrong because I had invented what "the student rate" meant.**

The firm, asked:

> *when i say college student gets it cheaper, i literally mean hey if you are
> in college and working that's rough, we have the simple filer deal just for
> you - same with someone not in college.*
>
> *so like the estimate generator is supposed to find the lowest cost we can for
> someone based on their situation whether that be starting with one of our 4
> packages and adding to it, or making some sort of weird custom package that is
> lower than a standard package but gets you what you need*
>
> *this was assured that it was done to me... is it not??*

**It is a cheap tier, not a percentage off.** I had assumed the reduction lived
in `satc_system/configs/billing/rate_plans.yaml` — `household`, `hardship`,
`pro_bono` — and built a whole Bassy challenge on the fee schedule having no
discounts. The fee schedule is right not to have discounts. The deal *is* the
ladder finding the cheapest package that covers the client.

**And it is built.** `pricing.derive_tier` returns "the tier that costs this
client LEAST", its docstring quotes the firm from 25 August saying to put it in
the mechanism rather than a test, and it runs inside `line_items()` → `price()`
→ `intake.finish`, which is the path the client's own estimate comes from.
Measured, not read:

| the client | the estimate |
|---|---|
| working student, W-2 only | **$100.00** Simple Filer |
| the same person plus a brokerage statement | $200.00 Essentials |
| student with a second state | **$150.00** — Simple Filer plus one state |
| self-employed, standard books | $500.00 Self-Employed |

The $150 is exactly the *"weird custom package that is lower than a standard
package"*. And `cli.py ladder` sweeps the shapes and reports Essentials eligible
24 times and chosen 12 — **beaten by Simple Filer the other twelve**, which is
the guarantee working out loud.

**Then the second half of the mistake.** `rate_plan_key` — the percentage
mechanism I stopped work to protect — is written by nothing but the store's own
loader and four test files. No route, no form, no command sets a rate plan on an
engagement, and until last night the product never created the row it sits on.
**I halted a decision to defend a mechanism that has never been reachable.**

What I should have done before raising it: price a student. It took one command.


## Friday 4 September 2026, late — the second docket, and one overrule

Asked directly whether I was trying to say the work was finished. I was not, but
the reporting read that way: shipping one decision at a time and calling each
verified is accurate per item and misleading in aggregate.

| | Asked | Answered |
|---|---|---|
| **D7** | five client documents ship past the pre-send gate | *"Gate the five documents next"* |
| **D8** | nothing records that a return was filed, so the 7-year clock never starts | **overruled me** — *"Defer with W5/W8 to the bookkeeping launch"* |
| **D9** | `make web` always opens the real client store | *"Let make web take a store"* |
| **D10** | the price, with the third option D3 unlocked | *"Show the engagement price via the ref"* |

**D8 is the one I was wrong to raise, and the overrule was already on record.**
I argued the filing writer should come next because it is the missing piece
under W5 and W8. The firm deferred it to the same place — and W8's own entry
already carried their words for it: *"note those as things to deal with when we
are ready to market the bookkeeping officially."* The answer was in the register
before I asked the question. Nothing is destroyed today, so nothing is at risk
today, and the three pieces of the retention promise get built together rather
than one at a time.

**The false gate claim was corrected without asking**, and that half was never a
decision. `CLAUDE.md` told every session that every client document passes a
blocking pre-send gate; the gate has two callers and neither is on the `event`
path. A wrong safety claim in the file every session loads is worse than the gap
it describes, because a gap invites a look and a claim forecloses one.

**Then closing the gap caught something my own test did not.** The first version
applied the pack gate wholesale and refused an ordinary single-document render:
the fee estimate promises the engagement letter as an enclosure, and a
one-document render does not hold one. That is the estimate being correct.
**A gate that refuses correct everyday use is a gate everybody learns to
`--force` past, and then it protects nothing.** Exactly one of the nine checks
is about completeness rather than about the documents, so that one is skipped
for a deliberate subset — and *named* as skipped, never dropped. Nine checks for
a chosen document, ten for a whole pack, and a test pins the difference at one.

My test had only asserted that a gate was mentioned. Running it found the rest.


## Friday 4 September 2026, evening — the docket came back, six for six

Every decision answered, every one taking the recommendation, no amendments.
Recorded here because an answer that lives only in a form has to be asked again.

| | Asked | Answered |
|---|---|---|
| **D1** | `--store` reaches production Square | *"--no-link defaults on any non-default --store"* |
| **D2** | a script with a request context is the owner | *"Adopt the Occam shape — launcher-set role and assignment"* |
| **D3** | two applications, one practice, no join | *"client-documents owns the engagement; satc_system holds the return"* |
| **D4** | two price lists disagreeing by 55% | *"registry/fee-schedule.yaml is the price"* |
| **D5** | should we use Fable 5.1 | *"No Fable for SATC work"* |
| **D6** | `desk/` is failing the same way | *"Tell the other session"* |

**D3 is the one that unlocks the others.** Naming `client-documents` the owner of
an engagement settles the join, the price question and the invoice numbering at
once — they were three symptoms of not having decided it.

**D5 is NOT a standing position, and I had it wrong within the hour.** I wrote
that it was, and offered to draft it as a conviction. The firm: *"this isn't a
conviction, i will just use it when i feel like it or want to test it."*

So the finding stands and the rule does not. Fable 5.1 requires 30-day data
retention with no zero-retention option, and it produced the weaker of two
reports on the same brief at roughly twice the cost per token — all true, and
none of it makes a policy. **A measurement is not a commitment**, and turning
one into a rule on the firm's behalf is how a record fills up with things they
never decided. Declined on the record so it is not re-proposed.

**D1 built the same evening.** `payments.link_follows_the_store` decides once,
at the seam: `--no-link` never, `--link` always, otherwise the default store
gets a link and no other store does — and the suppression is printed rather than
silent. `--link` had to exist, because a safety default with no override is not
a default, it is a wall.

**The test for it was decoration on the first attempt, and only the mutation run
found that out.** It put a tripwire on the HTTP transport and asserted the
output said "no link". Both halves were wrong. `processor()` refuses before any
transport is touched when no token is configured — the state of every test
machine — so the tripwire could never fire and the test proved *no token here*,
not *no call made*. And "No link on this bill —" is exactly what the **old** code
printed when the processor refused, so the assertion matched the bug's own
output. It passed against the defect it was written to catch. Rebuilt to watch
`link_for`, to stub `processor` so the tripwire is genuinely reachable, and to
assert the one phrase only the new path produces. Then mutated again: it fails
now, on the tripwire, which is what makes the nine passes worth anything.


## Friday 4 September 2026, evening — the evening two agents read the code and one ran it

Two agents got the byte-identical brief — *can a person run this end to end, can
an agent* — one on Fable 5.1, one on Opus 5, as the honest test of whether Fable
earns a place. **The comparison answered itself in a way I did not expect: the
difference that mattered was not the model, it was that one of them ran the
software.** Both serious findings came from the run that executed things, and
neither is visible from reading.

**`--store` isolates the files and not the money.** `cli.py invoice` reaches the
firm's production Square account whichever store you point it at. The standing
instruction on this machine is *point tests at a temp store*; an agent obeying it
believes it is isolated and is not. It came back `400 — idempotency key already
used`, so nothing was created — and a 400 is what a *differing* body returns. A
matching amount returns the existing link, and the test client is handed a real
client's payment link.

**A script with no human in it is the owner.** `acting_actor()` returns
`Actor.owner()` for anything holding a Flask request context, which
`app.test_client()` creates. Its docstring promises the opposite in the sentence
above it, naming *a script* as the case it catches. Reproduced here independently.

Both are one shape: **a control that reads how a call arrived rather than who
made it.** Neither was patched — a security gate and a money seam are the firm's
call — and both are recorded as W9 and W10.

**Then two of my own, found the same way.** `SATC_DATA_DIR` was documented as
always winning and honoured by two callers out of eight; one of the six was
`reset`, which deletes the vault, so a run scoped to a scratch directory would
have deleted the live store. And a locked `pytest-of-<user>` directory on this
machine — a DACL even `icacls` cannot read back — was erroring **467 tests here
and 1,165 in client-documents** at setup. `canon/conftest.py` had already solved
that one and written down both of its traps.

**The number I would have reported was false.** I was carrying "1,712 passed" and
"1,434 passed", both true when measured that morning, and the second was actually
*zero passing* by evening. A green number goes stale the moment the machine under
it changes — which is this repository's own first tenet pointed at its own test
run. It only got caught because something else made me re-run them.

**And my own walker was wrong four times out of four.** Written to walk the app
like a person, it read the first `<form>` on each page — the sidebar's "clear
sample data" form, on every screen — so it pressed that button and reported that
`/clients/new` had no fields and created no client. Scoped to the page's own
content, the app did the right thing at every step. That is the fourth time in
two days a checker built to find faults produced the fault itself, and it is why
the count above can be believed at all: **the walker's findings were checked
before they were reported, and none of them survived.**


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

### What the buttons do, not just that they work

*"All of them, take the time."* — and *"Close anything older than August,
unless this sound super destructive."*

**32 open pull requests → 9.** Twenty-three closed, branches and commits kept.
**Two deliberately not closed**, which is what the caveat was for: **#23**, the
Consumer Credit Red-Flag Monitor the firm had already asked to keep, and
**#88**, opened in July and worked on this week — closing by creation date
would have killed live work.

**Twelve behavioural tests**, pressing through the front door and reading the
store back. 202 buttons are about fifteen verbs; the verbs now carry the state
change their labels promise: Received records satisfied and invents no reason;
N/A with a reason keeps the reason; a blank N/A changes nothing and refuses
visibly; Confirm confirms, Reject does not confirm, Delete removes, Edit stores
what was typed, and an unrecognised action is inert. Endpoints not asserted here
are named with where they are covered instead — a list, not silence.

**And the same lesson twice more, in my own tests.** Five of them SKIPPED in the
full suite while passing alone, because they borrowed a staged field the earlier
1,600 tests had already confirmed. The first fix added a fallback that built
one — worse, because alone the fallback never ran, so a wrong import inside it
passed in isolation and failed only in the full suite. **A branch that runs in
one ordering and not the other is not covered.** There is no branch now.

### Late: the model question, and two projects that were not on the map

**Fable 5.1 — asked, read, answered.** The firm: *"should you be using fable 5.1
for anything"*. Read from the model reference rather than from memory, which was
the right call: it is **$10/$50 per MTok against Opus 5's $5/$25**, and it
**requires 30-day data retention** — not available under zero data retention
unless Anthropic expressly authorises it. The vision reader (`claude-opus-4-8`
today) can send client tax documents to Anthropic, so a mandated 30-day retention
is a compliance problem there, not a feature. The recommendation was to stay;
**the firm overruled it** — *"Try Fable on one hard task and compare"* — and the
end-to-end process assessment was run on both Fable 5.1 and Opus 5 on the same
brief.

**`canon` and `desk` were not in `CLAUDE.md`.** Canon had **zero mentions** in
the file every session reads first, and `desk` — 43 files, 174 tests, arrived
that day across five pull requests — none. Both added.

The firm corrected the desk entry as it was being written: *"some of the stuff
you are reading and is in-process under design by another session - such as
desk"*. The row was rewritten to say so. **A map entry written from a README by
a session that does not own the design is a pointer, not a specification**, and
one that reads as settled is worse than none — the next session would build
against a description that is still moving. The repository map going stale is
the failure `docs/REPO-INVENTORY.md` exists for; a map that is confidently wrong
about live work is the same failure arriving faster.

**BitLocker** — *"Remind me in a week"*. A cloud routine fires 11 September at
10:00, carrying the steps and the recovery-key warning. `CronCreate` was the
wrong tool: it is session-only and would not have survived the night.

### Still open at the end of the day

- **W5 / B4** — the seven-year destruction promise has no mechanism. Deferred
  to run alongside the backup work.
- **W8** — written notice is recorded nowhere. Gated to the bookkeeping launch.
- **B8** — the disk is not encrypted. Measured, recorded, not acted on.
- **The WISP** — 49 open questions and no signature.
- ~~Every screen except Documents has never been opened by anything.~~
  **Closed 4 September.** All 27 open in a browser on every run, and 203
  forms across 46 pages were pressed — none breaks the app.
- ~~Pressing a button proves only that it does not crash.~~ **Closed
  4 September.** Fifteen verbs now assert the record they write. What is still
  only crash-tested are the client-side withholding controls and anything
  needing state the demo store does not build — named in `NOT_ASSERTED`
  rather than left to inference.
- **B8 — BitLocker.** The firm read the steps and said *"Not tonight."*
  Deferred deliberately; the disk holding the vault is unencrypted and the
  recovery key must go to Bitwarden before it is turned on.
