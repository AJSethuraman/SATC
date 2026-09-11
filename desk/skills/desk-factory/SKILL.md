---
name: desk-factory
description: Add a new subject to the corpus by interviewing the firm about it — what it answers on, where the authority is, which sources bind and which merely interpret, what may lawfully be stored, and the known-answer set that proves it works — then open a pull request containing the merge. Never writes to the record; the merge is the yes. Use when the desk holds nothing on a subject, accounting or otherwise.
---

# desk-factory

**A subject is a definition, not code.** Sources with their tiers and storage
rules, a problem set, the passages, and which source answers what. That is what
makes the second subject cheap: this fills in a form, it compiles nothing, and
the engine that grades the hand-written corpus is the engine that grades this.

**It lands in the one corpus.** `dec-kill`, 8 September 2026 — *"Kill the desks;
one pool."* There are no per-desk folders to add one to: `factory.emit` merges
into `desk/corpus/`, which is the record a question actually reaches. It wrote a
`desk/desks/<name>/` directory until 11 September, a day after that directory
was deleted — passing every gate and landing somewhere nothing loads.

Nothing here is accounting-specific. Treas. Reg. § 1.263(a)-3 is where the
questions came from, not what they are limited to.

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

**Look where the authority is, not where the fetch succeeds.** Building the
cash-and-bank desk, the sources reached first were *tax* sources for an
*accounting* question — because eCFR and irs.gov answered and everything else
was refused by the environment's network policy. The firm, 5 September 2026:
*"there is a difference between tax and something like GAAP."* A streetlight
search produces a desk whose record is about the wrong subject and reads as
thorough. Two facts to carry: **eCFR serves every CFR title**, so accounting and
banking authority is there too (Reg S-X is 17 CFR 210, FDIC deposit rules are
12 CFR 330); and **reachable is not a reason to store** — Reg S-X came back
clean and mentions reconciliation and outstanding checks zero times, so it was
left out. Authority that does not bear on the question is padding that reads as
rigour.

**Every subject names the source that answers it.** `SUBJECTS.md` is written as
`**Answered from S2:** cash, bank, bank statement, ...` — one line per source —
and `fires_on` is the union, so there is no second list to keep in step. This is
not bookkeeping: it is the only thing that lets the engine tell a *right*
citation from a merely *real* one. Without it, `serve()` handed a caller four
bank-reconciliation answers citing a CFR paragraph about accounting records,
stamped `tier='primary'` (#266). Ask it per subject, not per desk — on the cash
desk the section number routes to the regulation and everything else to the
publication.

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
draft = factory.DeskDraft(name=..., title=..., sources=(...),
                          answered_from={"S1": (...), "S2": (...)},
                          problems=(...), passages=(...))
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

It assembles the merge in a temporary copy of the corpus and **touches the
checkout only if that copy passes** — so a refusal leaves nothing to clean up.
It grades **twice**, and the second does not subsume the first: the proposal on
its own, where `authority_is_more_than_the_answer_key` can still fire (merged
into 785 other passages, that guard compares two sets that can never be equal
again), and then the whole merged corpus, where the guards about the record as a
body mean something. Then it reads the subjects back out of the merged
`SUBJECTS.md` through `parse_subjects` — a merge that tallies and a merge that
landed are different claims.

**It proposes; it does not overwrite.** A source id, a citation prefix, a
problem id or a citation the corpus already holds is refused by name. The
migration that built this corpus resolved six duplicate citations by keeping the
longest text — correct for a migration nobody chose, wrong here: it means the
interview covered recorded ground, and that is a diff somebody reads.

Then commit, push, and open a **draft** pull request. Say in the body: the
sources with their tiers, the storage permission and the term it was read from,
the size of the problem set and where its answers come from, and — if every
source is primary — that this subject cannot escalate.

## What it will refuse, and what to do about each

| Refusal | What it means |
|---|---|
| `no problem set` | A desk that cannot be scored cannot be trusted; there is no number to read, so nothing distinguishes it from one that guesses well. Find worked problems whose answers are somebody else's, or stop. |
| `no licence term recorded` | You set `may_store` from an assumption. Go and read the terms, or leave it at `license_check`. |
| `not a checkout` | You aimed it at an installed plugin. The record is read from the plugin and written only in the repository. |
| `no corpus at ...` | The checkout has no `desk/corpus/`. It refuses rather than inventing a home — a new directory beside the corpus is a record nothing loads. |
| `would land on top of what the corpus already holds` | A source, prefix, problem or citation is already recorded. Read what is there; the overlap is the finding. |
| `did not pass the gates` | The definition is incomplete or the passages are exactly the answer key. The message names which gate and whether it failed alone or merged. Nothing was written. |
| `merged and then did not read back` | The subjects went into `SUBJECTS.md` and did not come out of it. Nothing was written. |

## The step this skill cannot take for the firm

A subject whose authority is entirely **ratified positions** — a `human_only`
source, whose licence forbids the content reaching a model at all — cannot be
emitted here, because an agent never writes a ratified position. That subject is
proposed in two steps and the firm's ratification is the **first** of them. This
is a constraint of the design, not a gap in the tooling: a position the firm did
not give is one they will disown the moment it is read back to them.
