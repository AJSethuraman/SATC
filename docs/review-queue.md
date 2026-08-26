# What still needs the firm — 26 August 2026

**The sign-off room, round three** — nine documents rendered fresh, each card
saying what changed since round two, and the last card answering "show me how
you can tell it all goes together":
<https://claude.ai/code/artifact/7878d079-30bd-44df-9b81-d5b43bfbbd05>

Two documents are in it that were not in round two: the **organizer cover
letter** and the **invoice**. The bookkeeping engagement letter is still not —
it has no interview behind it, which is a deferral rather than an omission.

Round two (<https://claude.ai/code/artifact/b298916e-8fc3-45b5-b69f-b61bdca0ff7b>)
and round one (<https://claude.ai/code/artifact/42b96c6d-0f0f-4ec3-b31e-bdb0c145ec7d>)
hold the feedback that produced it and are superseded.

The documents are embedded as the **real rendered output**, each in its own
shadow root so the firm's print stylesheet and the page cannot reach each
other. Start there rather than with the zip.

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
