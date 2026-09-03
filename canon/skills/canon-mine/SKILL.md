---
name: canon-mine
description: Read the seed corpus of the firm's own words and PROPOSE convictions for confirmation, one at a time, quoting them verbatim with the date. Use when the firm asks what convictions are hiding in their history, when a new corpus of their writing arrives, or when the record feels thin. Never writes to the record — every proposal waits for an explicit yes.
---

# canon-mine

Two files hold everything the firm typed between 21 August and 3 September
2026, pulled out of the session transcripts before the container holding them
was wiped:

- `corpus/the-firms-own-words.md` — 173 turns, 20 of them a screenshot and
  nothing else, 7,665 words
- `corpus/decisions-in-their-words.md` — 44 interview answers, **17 typed**
  rather than picked

The convictions are in there. Nobody has read them back.

## The line this skill does not cross

**Mining does not decide what a conviction is.** It narrows a corpus to
passages; a person reads them. The alternative — code that reads eight thousand
words of somebody's writing and announces what they believe — would be wrong
about the firm's own convictions, in their name, in the file they will later be
challenged from.

So: `mine.py` surfaces. You draft. **They confirm.** There is no fourth step
where something gets written on its own.

## Run it

```
python mine.py
```

It prints its denominator first — what it examined, what carried no words, how
many answers were typed — then two lists that are **never merged**:

**The certain half.** Every typed answer, surfaced unconditionally. An
interview offered options and the firm rejected the framing and wrote their
own; that rejection *is* the signal, and detecting it takes no judgement.

**The guessed half.** Turns carrying a marker word. This is a guess about
relevance and is labelled as one everywhere it appears. Read it with that in
mind and dismiss freely — a marker hit is an invitation to look, not a claim.

## Propose one at a time

For a passage that looks like a conviction, draft it and ask. **One.** A batch
of eight proposals gets one answer for all eight, and that answer is not
consent to any of them individually.

```python
from record import Conviction, HELD, load
from mine import Proposal, commit, load_corpus, read_decisions

draft = Conviction(
    id="C3", title="…",                      # a title, not a summary of the quote
    state=HELD, recorded="2026-08-30",       # the date THEY said it
    applies="everything",
    quote="You shouldn't ever touch the website itself.",   # verbatim, from the passage
    said_by="the firm, 30 August 2026",
    why="…",                                 # the reason, which is what gets re-examined
    fires_on=("website", "site", "index.html"),
)
proposal = Proposal(draft=draft, passage=passage)
print(proposal.ask())          # shows the EXACT text that would be stored
```

`Proposal` refuses to exist if the quote is not literally in the passage, or if
the reason or the date is missing. Paraphrase is the failure that burns the
whole mechanism — a conviction in somebody else's words is one the firm disowns
the moment it is read back at them — so it is made impossible rather than
warned about.

Then, and only on an explicit yes:

```python
convictions = commit(convictions, proposal, confirmed=True)
```

`confirmed=False` raises. There is no other way out of the module.

## What to look for

A conviction is a belief that would still hold next year, not a decision about
this week's work. The tell is that it carries a **reason about people or
principle**, not about scheduling:

- **Is** a conviction: *"I just don't think it's right to fuck them over"* —
  who the practice is willing to make money from.
- **Is not**: *"unblock the estimate first"* — an ordering call, correct at
  the time, meaningless as a standing rule.

When you cannot tell, it is not one yet. A thin record challenges rarely and
accurately; a padded one challenges constantly and gets ignored, and then the
accurate challenges are ignored too.

## Two things already known about this corpus

- **It is incomplete, and that is not a defect to hide.** Transcripts from
  other containers — the Forge session, earlier archived sessions — are not in
  it. Say so rather than letting the denominator imply completeness.
- **One passage carries a production Square location id** the firm pasted in
  answer to a direct question. It is an identifier, not a secret, and it is
  their own — but do not lift it into a conviction's quote, a title, or any
  artifact that leaves the record.
