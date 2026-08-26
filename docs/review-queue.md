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

**What the firm has to decide before an organizer can be built**, because none
of it is an agent's to assert:

1. **Is it a form, or a checklist?** A traditional organizer is a booklet of
   prior-year figures with blanks beside them. The cover letter promises
   "prefilled with what we carried forward" — which needs last year's return
   in the software, and Drake is the system of record for that.
2. **What is the return path?** The cover letter says the secure upload link.
   A booklet that comes back as a scan is not data; a web form is.
3. **How much of it is already the interview?** `return_features`,
   `extra_forms` and the request list ask most of what an organizer asks. The
   honest question is whether the organizer for a RETURNING client is anything
   more than last year's answers, shown back for confirmation.

The third is the one worth answering first, and it is close to the firm's own
words — *"as simple as we can make it for both of our sakes"*.

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

Nothing here blocks anything else. Item 1 is the only one with a clock on it.
