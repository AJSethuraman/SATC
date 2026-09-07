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

**And check which version you loaded before you trust what this file says.** A
session on the Forge invoked `desk:ask-desk` and the tool served it the SKILL.md
from a plugin cache three releases stale — a file with no mention of the two
fields the current release exists to deliver. Everything below would have been
followed correctly and produced the old output:

```
python3 -c "import json,os;p=os.path.expanduser('~/.claude/plugins/cache/satc/desk');print(sorted(os.listdir(p))[-1])"
```

If that is not the version in `claude plugin list`, **`/reload-plugins` before
going further** — an install does not reach the Skill tool until the session
reloads, and nothing says so at the point it bites.

```python
import os, sys
# `CLAUDE_PLUGIN_ROOT` is set when this skill is INVOKED as a skill, and is
# unset in a plain shell — so the documented first line of first use raised
# `KeyError` for a session that pasted it into `python3 -c`. Found on the Forge,
# 7 September 2026, closing a set of books. Fall back to the installed tree.
ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.expanduser(
    "~/.claude/plugins/cache/satc/desk")
if not os.path.isdir(os.path.join(ROOT, "desks")):          # a versioned cache
    ROOT = max((os.path.join(ROOT, v) for v in os.listdir(ROOT)), key=os.path.getmtime)
sys.path.insert(0, ROOT)
import ask

for desk, brief in ask.consult("the bank statement shows a $10 service charge "
                               "and nothing for it is in the books"):
    ...  # read `brief`, then answer from it
```

**Pass what your own file already says.** Some rules cannot be applied without a
fact the engagement should already have recorded — what the client does, whose
return it is. Hand it over; the desk will not work it out, deliberately.

```python
import record

for desk, brief in ask.consult(
        "they bought clothing at that store — is it a personal expense?",
        context=record.Context(facts={"trade": "general contractor"})):
    ...
```

**The caller passes what it already has.** There is no file to make and no place
to put one — the facts live wherever the firm keeps them, and this layer only
takes them. A desk that went looking for a container would be inferring, which
is the one thing it must not do.

**When you cannot supply a fact, that is the answer, not a failure.** Two
refusals, and they are not the same:

| | Meaning | Who fixes it |
|---|---|---|
| `context_not_on_file` | there IS somewhere to record this and it is not recorded | a preparer fills it in |
| `no_field_for_this_fact` | there is **nowhere** to record it, anywhere | the firm decides the fact exists at all |

The second is a **hole in what the firm tracks**, found by real work rather than
by an audit. `python3 $CLAUDE_PLUGIN_ROOT/tools/holes.py` reads them out.

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
| `document_not_requested` | a document that already exists settles it and nobody asked for it | request it by name |
| `context_not_on_file` | the rule needs a fact there IS somewhere to record and nobody has | record it — and fix the intake that skipped it |

**`context_not_on_file` is not the client's fault and not the desk's.** The firm,
5 September 2026: *"the Accountant should've already recorded and known what sort
of business we're dealing with ... if they're missing that piece of information,
something was just missing from the file."* Sending it to the client as a
question is the wrong queue.

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
source, and whether the subject could be checked at all.

**Every one of those is a property of the SOURCE, and none is about your
conclusion.** `tier` is the regulation's standing. `binding` means the firm
declared that source as authority that binds — not that your answer binds.
`checked_subject` is word overlap. `checked` is when somebody last confirmed the
passage against its publisher. Together they read as *"this was checked"*, and
the thing a reader thinks was checked is the one thing that was not.

**So a served answer carries two more fields, and you MUST pass both on:**

| | |
|---|---|
| `unchecked` | one sentence saying nobody verified the conclusion against the paragraph. Always set. Never drop it |
| `passage` | the cited text itself, so whoever reads your answer can do that check in one glance instead of going to look it up |

```python
print(out.position)
print(f"{out.citation} · {out.tier}" + (" · binds" if out.binding else ""))
print(out.unchecked)
print(f"> {out.passage}")
```

**This is not boilerplate to trim.** On 7 September 2026 a session aimed five
traps at the largest desk and four served — one citing § 1.263(a)-2(d)(1), whose
own text says *"a taxpayer must capitalize amounts paid to acquire or produce a
unit of real or personal property"*, to conclude **"deducted, not capitalized"**.
Primary, binding, no caveat. Printed with its passage underneath, that answer
refutes itself on sight. Printed without, it reads as settled law.

**Until a judge exists, the person reading your answer is the only check on it**
— and they cannot perform it if you hand them a conclusion without the words it
rests on.

## Two questions do not belong here

- **A decision the firm has to make once** — what the chart of accounts should
  distinguish, whether unreceipted cash is a draw. No authority settles those and
  a desk that answered would be inventing.
- **A defect in the software.** If two legs of a payment do not agree because the
  matcher failed, that is a bug, not a question.
