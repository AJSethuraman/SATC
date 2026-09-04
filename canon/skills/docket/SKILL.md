---
name: docket
description: The standing check-in, published as a form the firm fills in — what changed, what is open, and every decision waiting on them with both outcomes, a recommendation, and a box to answer in. Reads the repository's own log and state rather than the conversation. Use when the firm asks where things are, what needs deciding, for a status or a hand-off, at the end of a working session, or before handing a repository to another agent. Reads their answers back and writes them into the log.
---

# docket

A docket is the list of matters awaiting decision, **and a place to answer
them**. Not a summary of what happened: the shortest thing the firm can act on,
as a page they fill in, with everything they do not need to act on underneath
it.

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

## It is a form, not a report

**A docket is a thing you fill in.** Publish it as a page with a written answer
field on every open decision, and give them the link. Prose in the reply is not
a docket — it is a status update that happens to end in questions, and it makes
the firm hold four decisions in their head and type the answers back in order.

The page carries, for each decision: the context, both outcomes, the
recommendation marked as the recommendation, quick-pick buttons for the obvious
answers, and a free-text box for the answer that is not on the list. It saves as
they type, so a docket half-answered at midnight is still half-answered in the
morning.

Build it with the `artifact` tool: `capabilities: {db: {}}`, one document per
decision (`decisions/<id>`), `set` on change with a short debounce, and
`onSnapshot` so a second device shows the same state. Load the
`artifact-capabilities` skill before writing it rather than working from memory
of the API.

**Then go and read what they wrote.** `read_db` against the same artifact,
collection `decisions`. An answer sitting in a store nobody reads back is worse
than no form at all — the firm did the work and it went nowhere.

**Incident:** on 4 September 2026 this skill said a docket was "prose in the
reply", with publishing offered as a nicety for reading away from the machine.
It produced four decisions as paragraphs. The firm: *"the docket needs to come
as a docket, a form where i can read context you give me, have your
recommendations, fill it out and save it for you to review."* The form was
already built and working in that same session — for one report, by hand,
because nothing said it was the shape.

## Then write it down

When they answer, **append the answers to the log** — the decision, their words,
and what it caused. The form is where an answer is given; the log is where it
lives. That is what makes the next docket start from a real baseline instead of
from a session's memory. An answer that lives only in a conversation, or only in
a page, has to be asked again.

If an answer settles something the firm believes rather than something they want
done, that is a conviction: draft it quoting them and take it to `bassy`.
Nothing enters the record without an explicit yes.

## What this is not

- **Not a report of everything.** Everything is what the log is for. This is
  what is actionable, plus the denominators that make it believable.
- **Not a place to decide.** If a decision is the firm's, it stays open here
  with a recommendation attached — it does not get resolved fluently and
  reported as done.
- **Not silence when there is nothing.** "Nothing needs deciding" is a useful
  sentence. An empty docket that skips the section reads as an unfinished one.
