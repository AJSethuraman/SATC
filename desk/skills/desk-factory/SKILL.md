---
name: desk-factory
description: Build a new expert desk by interviewing the firm about a subject — what it answers on, where the authority is, which sources bind and which merely interpret, what may lawfully be stored, and the known-answer set that proves it works — then open a pull request containing the desk. Never writes to the record; the merge is the yes. Use when a desk is wanted for a new subject, accounting or otherwise.
---

# desk-factory

**A desk is a definition, not code.** Subjects, sources with their tiers and
storage rules, a problem set, and the two record stores. That is what makes the
second desk cheap: this fills in a form, it compiles nothing, and the engine that
grades the hand-built desk is the engine that grades this one.

Nothing here is accounting-specific. The one accounting desk that exists —
`fixed-assets`, on Treas. Reg. § 1.263(a)-3 — is where the questions came from,
not what they are limited to.

## The line this skill does not cross

**It proposes. It never writes the record.** `factory.emit` writes into a git
checkout, on a branch that is not `main`, and refuses everything else — the
installed plugin is replaced whole on update, so a proposal into one is thrown
away silently the next time desk updates. The pull request is the firm's yes,
and there is no argument to any function here that stands in for one.

## Phase 1 — the interview. Write nothing.

Ten questions, in `factory.QUESTIONS`. Read them from there rather than from
this file: each carries `why` — what building `fixed-assets` by hand actually
required — and a test refuses a question that carries none. Print them:

```python
import factory
for q in factory.QUESTIONS:
    print(f"{q.id}  {q.asks}\n      → {q.why}\n")
```

Ask them **one at a time**, `AskUserQuestion`, **your recommended answer first**
and marked so. The firm should be able to accept the default and move on; you are
doing the thinking, not handing it back. Two rules on top of `grill-me`'s:

**Research the source before asking about it, never ask the firm to recall it.**
Tier, access and the licence are facts about a document. Go and read the
document's own terms and bring the finding back as the basis for the question —
"its terms say X, so I read that as `citation_only`; agree?" — rather than asking
what somebody remembers.

**Never guess a licence.** `SourceDraft` will not construct with `may_store`
above `license_check` unless you pass the term you read it from, and that term
renders into the record's `Why` field where a reviewer meets it in the diff.
`license_check` is the honest answer when the terms could not be established, and
it stores nothing. A licence the firm holds may permit an internal copy — which
is exactly why this is a fact recorded per source rather than one policy over
all of them.

### The two questions that decide whether the desk is worth building

**Q4, tier.** `authority_permits_choice` fires only on secondary or tertiary
authority. A desk built entirely on binding primary sources *cannot escalate* —
measured on `fixed-assets`, where the escalation half of the design could not
trigger once across 42 answers (#245). Answering settled questions is what the
firm's existing software already does; the value of a desk is knowing when the
rules leave a choice open. If every source comes back `primary`, say so before
building.

**Q10, the corpus.** If the authority you would store is the same text the
answers are read from, the citation score measures an assignment puzzle rather
than retrieval. Measured on `fixed-assets`, 4 September 2026: 21 problems, 21
stored passages, a bijection between them, and a citation number nobody could
interpret (#244). `guards.authority_is_more_than_the_answer_key` fails the build
on this rather than trusting the question to have been asked — but it is far
cheaper to answer here, where the corpus is still being chosen.

## Phase 2 — show them exactly what would be written

```python
draft = factory.DeskDraft(name=..., title=..., fires_on=(...),
                          sources=(...), problems=(...), passages=(...))
for name, text in factory.render(draft).items():
    print(f"── {name} ──\n{text}")
```

`render` touches no disk. Show the real files, not a summary of them —
`canon-mine`'s `Proposal.ask()` draws the same line, and for the same reason:
a description of a diff is not the diff.

## Phase 3 — emit, and open the pull request

```python
factory.emit(draft, "/path/to/checkout", branch="propose-<name>-desk")
```

It writes the desk, then runs `guards.check` over what it wrote — every gate the
shipped desk passes, by name, not a copy of them — and **deletes the directory
and raises if any gate refuses**. A generated record held to a weaker bar would
be a second definition of what a desk is, and the two would drift. So a desk
this emits is one the record already accepts, or it does not exist.

Then commit, push, and open a **draft** pull request. Say in the body: the
sources with their tiers, the storage permission and the term it was read from,
the size of the problem set and where its answers come from, and — if every
source is primary — that this desk cannot escalate.

## What it will refuse, and what to do about each

| Refusal | What it means |
|---|---|
| `no problem set` | A desk that cannot be scored cannot be trusted; there is no number to read, so nothing distinguishes it from one that guesses well. Find worked problems whose answers are somebody else's, or stop. |
| `no licence term recorded` | You set `may_store` from an assumption. Go and read the terms, or leave it at `license_check`. |
| `not a checkout` | You aimed it at an installed plugin. The record is read from the plugin and written only in the repository. |
| `did not pass the gates` | The definition is incomplete or the corpus is the answer key. The message names which gate; nothing was left on disk. |

## The step this skill cannot take for the firm

A desk whose authority is entirely **ratified positions** — a `human_only`
source, whose licence forbids the content reaching a model at all — cannot be
emitted here, because an agent never writes a ratified position. That desk is
proposed in two steps and the firm's ratification is the **first** of them. This
is a constraint of the design, not a gap in the tooling: a position the firm did
not give is one they will disown the moment it is read back to them.
