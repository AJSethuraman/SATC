---
name: ask-desk
description: Consult an expert desk when a question is outside your authority — bookkeeping, tax treatment, whether a cost is the business's, what a purchase is. Use when you are doing the work and hit something you cannot settle from what is in front of you, rather than guessing and moving on. The desk answers only from authority it can cite, or tells you who has to be asked.
---

# Ask a desk

**You are doing the work. The desk is who you ask when you cannot settle
something.** It is not a second opinion on your judgement — it is the authority
you do not have.

## The two calls

**Reach the module from the installed plugin, not from wherever you are.** This
skill runs inside whatever repository you are working in, and `desk` is installed
elsewhere — so a bare `import ask` raises `ModuleNotFoundError` on the first line
of the first use.

```python
import os, sys
sys.path.insert(0, os.environ["CLAUDE_PLUGIN_ROOT"])
import ask

for desk, brief in ask.consult("the bank statement shows a $10 service charge "
                               "and nothing for it is in the books"):
    ...  # read `brief`, then answer from it
```

`consult` routes the question and hands back **everything that desk will let you
answer from** — its sources, the firm's own ratified positions, and its stored
authority. Nothing else.

```python
out = ask.answer(question, desk,
                 position="an entry in the books",
                 citation='IRS Pub. 583 (12/2024), "Reconciling the checking '
                          'account" — what the books are updated for',
                 model="whoever you are")
```

Or, when nothing in the brief settles it:

```python
out = ask.answer(question, desk, escalate="facts_not_established",
                 working="the rule is clear; nobody has said what was bought")
```

## Four things that will surprise you

**1 · Silence is an answer.** `consult` returns an empty list when no desk
answers on that subject. That is not a failure to route — it means no expert here
holds the question, and inventing one is the thing this exists to stop.

**2 · Escalating is a real answer, and often the right one.** Measured on eleven
real questions from a close, thirteen of eighteen answers were escalations and
that was correct. The reasons:

| reason | what it means | who resolves it |
|---|---|---|
| `facts_not_established` | the rule is clear; a fact about the client is missing | ask the client |
| `authority_permits_choice` | the rule leaves a choice, or only non-binding authority reaches it | the firm, once |
| `authority_absent` | nothing this desk holds reaches the question | a desk is missing |

**Do not stretch.** A desk that reaches for the nearest paragraph and calls it an
answer is the exact failure this system was built to prevent. The origin case: an
agent knew a retailer sells clothing, concluded *personal expense*, and was
wrong — the regulation it should have reached has no vendor in it at all.

**3 · Your citation is verified, and a wrong one is refused.** `answer()` does
not take your word for it. The citation must resolve inside that desk's record,
its source must be one the desk declares answers that subject, and where the
firm has ratified a position on it **you must return the firm's words, not your
own restatement of them.** A real citation from the wrong paragraph of the right
publication is refused too.

**4 · A refusal is kept.** Every one lands in the desk's `unsupported/` queue
with your reasoning intact. That queue is the only thing that tells the firm what
authority is missing, so **write a real `working`** — "could not tell" helps
nobody; "the rule turns on whether the item takes the place of ordinary civilian
clothing, and nothing says what was bought" is a work item.

## What comes back if it is served

The firm's own words where a position exists, the citation, the tier of the
source, and whether the subject could be checked at all. **What it does not
verify is that the conclusion follows** — only that the authority exists, that it
binds or carries the firm's word, and that it shares a subject with the question.

## Two questions do not belong here

- **A decision the firm has to make once** — what the chart of accounts should
  distinguish, whether unreceipted cash is a draw. No authority settles those and
  a desk that answered would be inventing.
- **A defect in the software.** If two legs of a payment do not agree because the
  matcher failed, that is a bug, not a question.
