# What still needs the firm — 26 August 2026

**The sign-off room, round four** — every note from round three applied, every
document re-rendered from it, and the organizer question answered:
<https://claude.ai/code/artifact/8dd9d78e-7eff-4098-b03b-8b70a69a21e5>

**One document is new**: the records release authorization, built to the note
*"let's just make an attachment that we send for them to sign by default along
with the engagement letter."* It goes out automatically to any client who had a
predecessor.

**One card has no document.** There is no organizer — see below.

Round three (<https://claude.ai/code/artifact/7878d079-30bd-44df-9b81-d5b43bfbbd05>),
round two (<https://claude.ai/code/artifact/b298916e-8fc3-45b5-b69f-b61bdca0ff7b>)
and round one (<https://claude.ai/code/artifact/42b96c6d-0f0f-4ec3-b31e-bdb0c145ec7d>)
are superseded. The firm's notes from each are recorded in
`docs/sign-off-register.md`, because a page gets superseded and the reasoning
should not.

The documents are embedded as the **real rendered output**, each in its own
shadow root so the firm's print stylesheet and the page cannot reach each
other.

**The queue itself** (this list, as a page):
<https://claude.ai/code/artifact/4536ea0b-7016-4c90-bf78-9c7183d5d3c3>

This file is the committed copy, so the list survives the session that made it.
Everything settled is on PR #153 and test-backed; this is only the remainder.

**The schedule itself is complete.** No unpriced item, no unanswered decision —
`python cli.py doctor` reads clean, and a test holds it that way.

**And the package agrees with itself.** `make check` renders the documents and
compares six joins across them — one reference, one date, one scope stated by
both the letter and the estimate, nothing billed outside that scope, a total
that is the sum of its lines, one materials deadline. All six pass. Each has a
test that breaks its join on purpose.

## To read — no decision, just eyes

1. **The ten client documents.** All render for real, all sent 26 August, none
   read since. The four that were DRAFT are not any more.
2. **Five sentences a client will read** that I wrote from decisions the firm
   made: the **Self-Employed** name and its line, the **Amendment** line, the
   **Extension** line, the soft-cap sentence, and the four entity starting
   notes. `docs/sign-off-register.md`.
3. **The six per-form situations and their assumptions.** Marked *changes*
   since 25 August because the firm asked to walk them. Each assumption is
   what decides whether a client pays $50 or an hourly rate.

## The organizer — asked 26 August, answered here

The firm, on that card: *"i want to see this when i see the organizer - what
is this and how do they fill it out? it should be as simple as we can make it
for both of our sakes."*

**There is no organizer.** There is a cover letter for one. It says *"Your
organizer for the 2026 tax year is enclosed. It is prefilled with what we
carried forward from last year"* — a promise about a document that does not
exist in this repo, and the reason the card could not answer the question.

The letter is not broken. Its `Requested` list is registered as required, so a
render with nothing in it **refuses** rather than printing "What to send" over
a gap. What it cannot do is describe a document nobody has built.

**Chasing that found a real bug and it is fixed.** `doctor --engagement`
reported the organizer letter **"Ready now"** while `render` refused it —
doctor's readiness check left out the required-lists guard that render
applies. Two halves of one tool disagreeing about the same document is worse
than either answer alone: whichever you happen to run is the one you believe.
They now ask the same question, and a test holds every document to that.

### A recommendation, asked for on 26 August

The firm: *"you help me decide with suggestions based on industry norms and
ease of use."* So here is a recommendation rather than three questions. It is
a proposal, not a decision — but it is what I would build.

**Recommendation: do not build an organizer. Build a returning-client
confirmation, and let Drake keep the figures.**

**1 · Form or checklist? Neither, and only one half is new.**

The traditional organizer — the booklet of prior-year figures with blanks
beside them — is the part to skip. Every major package generates one, Drake
included, and firms report most come back untouched: clients skim it, tick
nothing, and send a shoebox anyway. Building a second prefilled booklet in
SATC would also mean copying last year's numbers out of Drake, which is the
one thing `CLAUDE.md` says not to do. **Drake holds the figures. If a client
genuinely needs a prefilled organizer, Drake already prints it.**

What a returning client actually needs from us is two things, and we have
most of both already:

- **Last year's answers, shown back for confirmation.** Not questions — a
  list of what we recorded, with "still true?" beside each one.
- **The document request list**, which `requests.for_answers()` already
  builds from those answers.

**2 · Return path: a web form, on the front door that already exists.**

`web.py` is already a browser interview, drafts already persist after every
answer, and the raw answers for every past engagement are already on disk at
`engagements/<ref>/interview.json`. A confirmation is that same machinery with
the answers pre-loaded. **This is what keeping the raw answers separately was
for**, and it is why that decision is worth more than it looked at the time.

A PDF that comes back as a scan is not data — somebody re-keys it. That is
the same cost the firm just refused to bill for on brokerage statements:
*"we will figure out how to make it efficient."* The same logic applies here,
and more cheaply, because the form already exists.

**3 · How much is already the interview? Most of it — with one real gap.**

Of the 49 questions, the fee-driving counts, `return_features`, the states and
localities and the prior-year block are all things a returning client would
simply be confirming. **What the interview does not ask is change.** It asks
filing status and dependents as *facts* — `joint_return`, `has_dependents` —
never as *what is different since last year*. No question anywhere asks about
a marriage, a divorce, a birth, a death, a house bought or sold, a move to
another state, a retirement, or an inheritance.

That is the genuinely new content, and it is short — one section of yes/no
questions, each of which, when ticked, opens the questions we already have.
**It is also the section that earns the whole exercise**, because those are
exactly the events that change a return and that a client will not think to
mention.

**What this costs and what it buys**

| | |
|---|---|
| **New content to write** | One life-changes section. Everything else is reuse. |
| **New software** | A seed-from-last-year path into the existing web interview. |
| **What the client does** | Reads a list, ticks what changed, uploads documents. No booklet, no figures to copy. |
| **What we get** | Structured data, not a scan — so the fee, the schedules and the request list all derive as they already do. |

**One consequence, and it needs the firm's word.** The organizer cover letter
currently promises *"Your organizer for the 2026 tax year is enclosed. It is
prefilled with what we carried forward from last year."* If the recommendation
above is taken, that sentence describes something that will never exist and
has to be rewritten. If the firm would rather keep a prefilled booklet, then
the answer is to send **Drake's** organizer and have this letter carry it —
which is a smaller job than building ours, and is the honest alternative.

`[CONFIRM: build the returning-client confirmation, or send Drake's organizer
under this cover letter?]`

## The predecessor's records — who actually sends the authorization?

Asked 26 August on the onboarding letter: *"can we just get their written
consent to get the records from them? or do they have to contact? my intention
was to collect their consent upfront."*

**Today the client does the sending.** Section 03 says *"We have included a
short authorization for you to sign. Send it to <PriorFirmName> and they will
release your prior records to us."* So we hand them a form and a task, and the
step happens outside our sight — we cannot tell a client who forgot from a
predecessor who is stalling.

**Recommendation: collect it upfront and send it ourselves.** The
authorization is already in the opening package and already conditional on
there being a predecessor, so the client signs it in the same sitting as the
engagement letter, through the same route, and it comes back to us with
everything else. We then send it on.

Three reasons, in order of weight:

1. **It is one fewer thing that can silently not happen.** A signed
   authorization sitting in our file is a fact we can act on. A form we asked
   a client to post is a hope.
2. **It matches how the rest of the package already works.** Everything else
   is signed through Encyro and comes back to us. This one item asked the
   client to break that pattern and use a different channel to a different
   recipient.
3. **A predecessor answers a firm faster than a forwarded email.** A request
   from us, with the client's signed authorization attached, is a complete
   request. A client forwarding a PDF is not.

**What would change:** section 03's sentence stops being *"send it to them"*
and becomes *"sign it and we will send it"*. Nothing about the
authorization itself changes — it is still the client's consent, addressed to
the predecessor, and the predecessor still decides when to release.

**What does not change, and should not:** *"We will not wait on them to
start."* That sentence is the reason the whole section is safe to have, and it
survives either way.

`[CONFIRM: switch section 03 to "sign it and we will send it", or leave the
client to send it?]` I have not changed the letter — who transmits a records
request is a practice decision, not a wording one.

## To decide — a question only the firm can answer

1. **Merge PR #153.** Nothing from the last two days is on `main`: fifteen
   commits, every price from rounds eleven and twelve, the publication policy,
   five bug fixes. An agent reading `main` finds the old schedule and
   correctly concludes the information is not there.
2. **Has any package name already gone to a real prospect?** Names render from
   config, so a rename is one line *while that holds*.
3. **Is the records-sorting fee withheld on the firm's judgement or mine?**
   The farm one beside it is the firm's. The entity prices sat withheld on my
   reasoning for two days before it was reversed.
4. **How much should the page claim about the estimate guarantee?** A bill
   over the estimate refuses without a variance note. What the page says about
   that is a sentence a client reads.
5. **T-18 — build the time capture, or not yet?** The load-bearing unknown is
   what manual entry costs in seconds.
6. **T-11 — capturing the processes themselves.** Open since raised.
7. **T-10 — the free client literature.** Answered with a recommendation,
   waiting on a call.
~~8. Does "A letter from the IRS or the state you would like us to handle" stay
   on the price page's hourly list?~~ **Answered 26 Aug: let it drop.** A notice
   response is a separately quoted engagement, not hourly work. No schedule
   change needed; the patch is **B7** in `docs/site-open-questions.md`, for the
   site agent whenever the page is next touched.

Nothing here blocks anything else. Item 1 is the only one with a clock on it.

`published prices match the fee schedule` is **green again as of 26 August.**
It was left red by decision — *"the website half is unnecessary"* — until it
re-fired on every push and the firm asked for it gone. Three dead references
deleted from `website/build-pricing-config.py`, config regenerated, 58/61 →
61/61. The page lost one line and no price moved. **The fee-schedule walkthrough
the firm asked for still stands** and is in `PLAN.md`.
