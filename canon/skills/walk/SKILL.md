---
name: walk
description: Drive the product through a real browser as the person whose job it is, end to end, and write TWO documents as you go — the procedure, numbered and screenshotted, that a person can follow, and the defects that only surface on a screen. Use when the firm wants to prove a build works visually and literally, wants a written procedure or SOP for staff, wants to know what a green test suite is missing, or says walk the product, click through it, or do it like a real user would.
---

# Walk the product

Take one complete job a real person does, and do it **through the screens** —
clicking the actual interface in a browser. Not through the API. Not through the
test suite. Front to back, on real-shaped data, to the end of the job.

Load the `claude-in-chrome` skill before touching a browser tool.

## Why this finds what the suite cannot

**A test knows the answer before it runs, so it cannot be surprised.** It asserts
what somebody already believed. It cannot notice that a button's label describes
the opposite of what the button does, because nobody writes an assertion about a
thing they do not know is wrong.

On 4 September 2026 one walk of Occam produced ten defects against a suite of
**1,520 Python tests and 68 web tests, all passing**. None of the ten was caught
by any of them. Almost none was a wrong *result* — they were a screen promising a
warning no code path can emit, copy describing the opposite of its own button, a
control missing from the one run that most needed it, and an order of operations
the product had never told anybody.

## Two documents come out, and writing only one throws away half the run

This is the rule the skill exists for. **The same run produces both. Neither is
optional.**

**1 · The procedure** — `docs/PROCEDURE-<job>.md`

Written for the person who will do this job without you: numbered steps, one
action each, a screenshot per step, and what a correct screen looks like so they
can tell when it is wrong. This is the deliverable that becomes staff training,
a client-facing SOP, and the script for the next walk. **It is the half that gets
skipped**, because the defects feel like the findings and the route feels like
scaffolding. The route is the asset.

**2 · The defects** — `docs/WALKTHROUGH-DEFECTS.md`

Ranked by what each would cost a real client, not by how interesting it is. Each
one: what you did, what the screen said, what was actually true, and the fix.
Open with the suite's real numbers and how many of these it caught — usually
none, and that is the finding.

**Write both as you go, not at the end.** A procedure reconstructed from memory
records the route you remember rather than the one you walked, and the fumbles
are the first thing to vanish — which is exactly where the next person will get
stuck. Behaviour 14 is the same rule for the same reason.

## Screenshots

Capture one at **every** step, not only at failures — a procedure needs the
screen that looks right as much as the one that does not. Save them beside the
procedure, named by step:

```
docs/walkthrough/<job>-<date>/step-03-import-mapped.png
```

Reference them inline in the procedure. A step without its screenshot is a step
somebody has to guess at, and behaviour 11 applies to your own output: open the
document and look at it before calling it done.

## What you are hunting

These are the shapes a walk finds and a suite does not. Every one is a real
finding from the first run.

- **A green that cannot go red.** Debits equal credits by construction — every
  journal the poster accepts is balanced — so a "trial balance foots" verdict is
  an identity, not a test. Name the input that would make it red. If you cannot,
  it is an identity: write down why it holds, put that sentence where the reader
  is standing, and delete the green.
- **A side effect reported as a count.** *"1 similar row pre-filled"* is the
  correct number and still useless: the reviewer's question is *which one, and is
  it right*. List what changed, `old → new`, one line each. Where the list would
  be too long to read, **that is the finding** — narrow the operation rather than
  shortening the list.
- **Two fields that contradict each other with nothing comparing them.** A memo
  reading *"Office supplies"* on a row coded to a credit-card liability. Both
  produced by different passes, neither aware of the other.
- **Copy that describes the opposite of what its control does.**
- **A warning the product promises that no code path can emit.**
- **A control present on every later run but missing from the first**, which is
  the run that most needed it.
- **An order of operations the product never told anybody**, discovered only by
  getting it wrong.

## What not to do

- **Do not fix anything mid-walk.** The moment you repair a screen you have
  destroyed the record of what a real person hits, and you can no longer say what
  the product does — only what it does after you helped. Note it and keep going.
- **Do not fall back to the API when a screen is awkward.** The awkwardness *is*
  the finding. A walk that routes around the interface has stopped being a walk.
- **Do not stop at the first defect.** Finish the job. The worst one on the first
  run was the last screen, and a walk abandoned early reports the shallowest
  problems as though they were the set.
- **Do not report a count of defects without the suite's denominator beside it.**
  "Ten defects" means little; "ten defects against 1,588 passing tests, none of
  which caught any of them" is the argument.

## The second run

The procedure you wrote is the script. Walk it again after a change and every
step either matches its screenshot or does not — which is a regression check a
person can run, on the half of the product no test reaches. A step that no longer
matches is either a defect or an out-of-date procedure, and finding out which is
the job.

**Incident:** on 4 September 2026 a session walked Occam end to end in Chrome and
found the ten defects above. It wrote them up, ranked, with the denominator. It
never wrote down **how it had walked** — no steps, no screenshots, no route — so
the one thing that could be repeated by anybody else was the one thing not
recorded. The firm: *"Job one is what will help me literally create software…
and prove it works both visually and literally, and the screenshots and steps can
be used to make procedures for people."* Nothing had told the session that the
route was a deliverable, so it treated it as scaffolding and threw it away.
