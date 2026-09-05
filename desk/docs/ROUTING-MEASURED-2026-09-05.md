# Does a real question reach the right desk? Measured on the close's own words

**Recall: 16 of 16.** Every question that had a desk built for it routes to that
desk, using the close's own wording rather than a rephrasing.

**Precision: 14 extra desks fire across those 16 questions** — near enough one
spurious consultation each. Q5 fires four desks.

Both numbers matter and they say different things.

---

## What was measured

Six desks are registered. Sixteen of the 43 close questions had a desk
commissioned for them, and each question was routed as `title + why it matters`,
verbatim from `CLOSE-QUESTIONS-2026-09-05.md`. No question was rewritten to help
it match — that was the whole point, and it is how the capitalisation desk found
that *"Where is the line between a tool and a fixed asset?"* routed to **nothing**
while *"what is our capitalisation threshold"* routed fine.

| | |
|---|---|
| questions with a desk built for them | 16 |
| reaching that desk | **16** |
| reaching no desk | **0** |
| additional desks fired | **14** |

## The spurious firing is a cost, not a defect — but it is a real cost

A question reaching a desk that has nothing to say gets a refusal, not a wrong
answer. Nothing is mis-answered. What it costs is a round trip per extra desk,
and on a small local model each round trip is a chance to lose the thread.

The cause is that `fires_on` is the **union** of a desk's declared subjects, and
a question mentioning a chart of accounts, a card, a purchase and a client
touches four desks' vocabularies honestly. `Q5 · meals: book or refuse` fires
`cash-and-bank`, `meals-and-entertainment`, `personal-or-business` and
`vehicle-expense`, and only one of them can answer it.

**This is the case `WHAT-A-DESK-IS-FOR.md` describes as ordering.** Four desks
firing is not four experts conferring; it is one question that has not been asked
in the right order. Nothing here proposes a fix, because a relevance score is
exactly the inexact gate the firm already declined once — measured at 4 false
refusals in 16 on `fixed-assets`. The number is recorded so that whatever is
built next has something to beat.

## What this does not measure

- **Whether the desk answers correctly.** Routing is the doorbell, not the
  answer. Every desk's own problems grade `correct` or `escalated` against its
  own record, and that is a different claim.
- **The 27 questions with no desk.** Their owners are a client, a document, the
  firm, or the issue tracker; a router firing on them would be noise.
- **Anything a model does.** This is deterministic routing over the record. No
  brain has answered a question from this corpus.
