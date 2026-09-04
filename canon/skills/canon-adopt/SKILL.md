---
name: canon-adopt
description: Adopt a repository that predates canon — read its history and documents, propose candidate tenets each citing a real commit in that repo, and write its identity card for the register. Use when canon is installed somewhere new, when a project should be added to the register, or when the firm asks what rules a codebase's own history already proves. Proposes; never writes to the record.
---

# canon-adopt

Point canon at a codebase it has never seen. Two questions:

1. **What rules does this repository's own history already prove?**
2. **What is this project, in four lines**, so a session arriving cold knows
   where it is?

## Where the record is, and where it is not

Installed as a plugin, the record travels with it:

```
${CLAUDE_PLUGIN_ROOT}/CONVICTIONS.md      what the firm believes, and why
${CLAUDE_PLUGIN_ROOT}/TENETS.md           how to build, with the incidents
${CLAUDE_PLUGIN_ROOT}/record.py           parse it, render it, change it
```

**Read from there, always — not from a copy you happened to find.** A machine
with the canon repository checked out has a second copy at `canon/`, and a
session that reads that one is reading whatever is on that working tree: a
branch, a half-finished edit, someone else's experiment. This is not
hypothetical. It happened on the first install: asked where it had read the
record from, a session in an unrelated repo answered with the path to a checkout
on that machine rather than the plugin's own copy, and would simply have found
nothing on any machine without it.

**Never write there.** The plugin directory is versioned and replaced on update,
so anything recorded into it is thrown away the next time canon updates. To add,
retire, or decline a conviction, change `CONVICTIONS.md` in the **canon
repository** and open a pull request; other machines pick it up with
`claude plugin marketplace update satc`. The plugin is how the record is read
everywhere. The repository is the only place it is written.

## Run the reading

```
python "${CLAUDE_PLUGIN_ROOT}/adopt.py" <repo> [subdirectory]
```

The subdirectory argument is how a monorepo folder is adopted as its own
project — the nine analytics projects live that way.

It prints its denominator first, and the denominator is the part that keeps the
rest honest. It says how many commits it read **of how many exist**, and it
lists what it did **not** examine — including that it never read the code and
never found out whether a single test passes.

Then two lists that are never merged:

- **Commits that changed a test and a source file together.** A mistake
  somebody thought worth pinning. A fact about the commit, not a judgement.
- **Commits whose subject carries a fix-word.** A guess about relevance,
  labelled as one.

## Two things the first real run taught

**The certain tier is not always a signal.** On a project built test-first, 14
of 17 commits touched a test alongside source — the normal case there, not
evidence of anything. The report now says so when the share goes past half. If
you see that note, read the list as history, not as a shortlist.

**The guessed tier can be empty and that is information.** The same project's
commits were all slice-shaped (*"slice 7: no-PII-leak guard"*), never
fix-shaped, so the fix-word tier returned nothing. That is a fact about how
that team writes commits, not a clean bill of health.

## Propose, one at a time

A candidate's text is the **commit's own subject**. Generalising it into a rule
is the step that turns *"this repo fixed a thing"* into *"this repo proves a
law"*, and that step belongs to a person — it is exactly where a plausible,
wrong tenet would enter the record and never leave.

So: read the commits, write the rule in your own words, and take it to the firm
the way a mined conviction goes — one at a time, quoting what it came from,
with `record.add_evidence` or `record.add` behind an explicit yes.

## Write the card

```python
from adopt import Card, convictions_for

card = Card(
    project="credit-review-os",
    what_it_is="…",          # what it IS
    what_it_is_for="…",      # who it serves and what it replaces
    stack="…",
    where_it_lives="…",
    convictions=convictions_for(convictions, text),
)
```

**A card never says what the code currently does.** No file inventory, no
counts, no status, no version, no "currently", no TODO. Those are true the day
they are written and quietly false a week later — and a card that has been wrong
once is still consulted, which is what makes it worse than no card.

That is enforced twice: `Card` has a fixed set of fields, so it cannot *grow* an
inventory, and every text field is checked, because a free-text line can carry
"1,249 tests passing" through any structure you like. It caught the first real
card on the first attempt — both entries named the documents that govern them,
and both read better without.

Append the rendered card to `projects/REGISTER.md`. Cards are written by a
person after a run, never generated from one.

## What adoption never does

It does not write to the record, does not touch the repository it is reading,
and does not call anything in it a tenet. `tests/test_adopt.py` holds all three.
