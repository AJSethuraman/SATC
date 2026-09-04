---
name: docket
description: The standing check-in — what changed, what is open, and what needs the firm's decision, each with both outcomes and a recommendation. Reads the repository's own log and state rather than the conversation. Use when the firm asks where things are, what needs deciding, for a status or a hand-off, at the end of a working session, or before handing a repository to another agent. Writes the answers back into the log.
---

# docket

A docket is the list of matters awaiting decision. That is what this produces:
not a summary of what happened, but **the shortest thing the firm can act on**,
with everything they do not need to act on underneath it.

Behaviour 14 says keep the log where the work is. This is how the log gets read
back out.

## Where it reads from

**The repository, not the conversation.** A session's memory of its own week is
the least reliable account of it — it remembers what it did, not what it
skipped, and the skipped things are what the firm needs.

1. `LOG.md` (or the project's own running log) since the last entry the firm saw.
2. `git log` since then — what actually landed, as opposed to what was intended.
3. The test suite's real numbers, run now. **Report the denominator.**
4. Whatever the project's own state is: open pull requests, a failing check, a
   branch that has not merged.

If any of those cannot be read, say so in the docket. "Not checked" is a finding.

## The shape

**Findings before green. Decisions before findings.** The order is not cosmetic:
a page that opens with what went well is a page the firm skims.

1. **Waiting on you** — every open decision, each as *what is being asked, what
   happens either way, and what I would do.* Answerable in one line by somebody
   who was not there. If there are none, say so in those words.
2. **What changed** — with denominators. `948 → 1,298 passing` says something;
   "improved the tests" says nothing.
3. **What I did not check** — its own list, plainly. A clean result is a
   finding; a silent gap is not.
4. **What I got wrong** — if the session corrected itself, that belongs here
   rather than being quietly absorbed. It is the part that tells the firm how
   much to trust the rest.

## Recommend, do not survey

Every decision carries a recommendation with a one-line reason. Handing back
three options and no opinion is handing back the work. The firm can overrule a
recommendation in a word; they cannot overrule an absence.

## Then write it down

When they answer, **append the answers to the log** — the decision, their words,
and what it caused. That is what makes the next docket start from a real
baseline instead of from a session's memory. An answer that lives only in a
conversation has to be asked again.

If an answer settles something the firm believes rather than something they want
done, that is a conviction: draft it quoting them and take it to `bassy`.
Nothing enters the record without an explicit yes.

## Where it goes

A docket is written for the person holding the screen. In the terminal that is
prose in the reply. Where the firm would rather read it away from the machine —
on a phone, later, or hand it to somebody else — publish it as a page and give
them the link, and keep the answers with the work either way.

## What this is not

- **Not a report of everything.** Everything is what the log is for. This is
  what is actionable, plus the denominators that make it believable.
- **Not a place to decide.** If a decision is the firm's, it stays open here
  with a recommendation attached — it does not get resolved fluently and
  reported as done.
- **Not silence when there is nothing.** "Nothing needs deciding" is a useful
  sentence. An empty docket that skips the section reads as an unfinished one.
