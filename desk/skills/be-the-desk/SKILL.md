---
name: be-the-desk
description: You ARE the desk — a request has arrived from somebody doing the work and you answer it from recorded authority, then hand the answer back to them. Use when a message opens "DESK REQUEST", when this session is the one holding the desks, or when running the desks locally to test them. To ASK a desk rather than be one, use ask-desk.
---

# Be the desk

**Somebody else is doing the work. You are the authority they do not have.**
A request has reached you — usually as a message opening `DESK REQUEST <ref>` —
and your job is to answer it from what the desks actually record, then send the
answer back to whoever asked.

**To ask a desk rather than be one, that is `ask-desk`, and it is a different
skill.** The split is the architecture: `docs/THE-DESK-IS-A-SESSION.md`. You
hold the record; the asker does not, and must not.

## Answering a request that arrived from somewhere else

`DESK REQUEST` messages carry their own instructions and those win over anything
here, because this file can be four releases stale in a plugin cache and the
message cannot. Three things they will always say, and all three matter:

- **No context came with the question, deliberately.** The firm, 8 September
  2026: *"we don't add context to it, that defeats the purpose. it falls the
  same rules and gets the de-identified data so it can ensure it answers and
  asks things objectively."* An asker who writes the context writes the answer.
  Read the facts off the record through `consult`, and escalate on a missing one
  rather than infer it.
- **Reply POKE-ONLY.** `create_trigger` with the asker's session id and NO
  `run_once_at` and NO `cron_expression`, then `fire_trigger` once. A trigger
  that carries a schedule and is then poked **delivers twice** — measured, and
  it is why every Forge round on 7 September arrived in duplicate.
- **`fire_trigger` returning success is not delivery.** Its `last_fired_at` is
  not corroborated by the durable record. Say what you sent and stop; do not
  chase your own message.

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
python3 -c "import os;p=os.path.expanduser('~/.claude/plugins/cache/satc/desk');print(max(os.listdir(p), key=lambda v:[int(n) for n in v.split('.')]))"
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
if os.path.isdir(ROOT) and not os.path.isdir(os.path.join(ROOT, "desks")):
    # NEWEST BY NUMBER, NEVER BY STRING. This read `sorted(...)[-1]` for one
    # release. It is correct today and through 0.9.x, and on the first bump past
    # .9 it silently picks 0.7.3 over 0.10.0 — an agent loading a stale plugin
    # while believing it is current, which is the exact failure the version
    # check above exists to catch, shipped inside the fix for it. Found by the
    # Forge, 7 September 2026, reading the fix rather than running it.
    def _release(name):                    # ("0.10.0") sorts above ("0.7.3")
        try:
            return (1, tuple(int(n) for n in name.split(".")))
        except ValueError:
            return (0, ())                 # not a version dir; never the newest
    versions = sorted(os.listdir(ROOT), key=_release)        # a versioned cache
    ROOT = os.path.join(ROOT, versions[-1]) if versions else ROOT
if not os.path.isdir(os.path.join(ROOT, "desks")):
    raise SystemExit(
        f"no desk plugin at {ROOT}. Install it — `claude plugin marketplace "
        f"update satc && claude plugin update desk@satc` — or set "
        f"CLAUDE_PLUGIN_ROOT to where it lives. There is no desk to ask.")
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

**So a served answer carries three more fields, and you MUST pass them all on:**

| | |
|---|---|
| `unchecked` | one sentence saying nobody verified the conclusion against the paragraph. Always set. Never drop it |
| `passage` | the cited text itself, so whoever reads your answer can do that check in one glance instead of going to look it up |
| `alongside` | the firm's OTHER positions on this same passage, where they hold one. Empty on most answers. See below |

```python
print(out)          # every field below, laid out. Not `repr`, not field by field
```

**`print(out)` is the whole instruction, and that is deliberate.** This file
went stale in a plugin cache four releases running while the code moved
underneath it, so a session was reading a list of fields that no longer matched
what it had. The rendering lives on the object now — `Served.__str__` — which is
current whenever the code is. A skill can go stale; what it tells you to print
cannot. Do not reassemble it field by field: anything added after the version of
this file you are reading will be in the object and not in the list.

`repr(out)` is a different thing and is for the log — it carries the counters
(`showed`, `showed_by_source`) that exist to falsify a model's claim about its
own record, and those are not for a preparer.

**This is not boilerplate to trim.** On 7 September 2026 a session aimed five
traps at the largest desk and four served — one citing § 1.263(a)-2(d)(1), whose
own text says *"a taxpayer must capitalize amounts paid to acquire or produce a
unit of real or personal property"*, to conclude **"deducted, not capitalized"**.
Primary, binding, no caveat. Printed with its passage underneath, that answer
refutes itself on sight. Printed without, it reads as settled law.

**Until a judge exists, the person reading your answer is the only check on it**
— and they cannot perform it if you hand them a conclusion without the words it
rests on.

### The firm can hold two opposite positions on one passage

Where they do, `alongside` carries the other one and `print(out)` shows it under
the answer. **Read it before passing the answer on.** It is not a footnote: it
means the firm split that passage because it carries two answers, and which of
them applies is a question about the facts in front of you — which nothing in
the desk has looked at.

The reason it exists: on 7 September 2026 a session asked about a deposit made on
the last day of the month and not yet on the statement, and cited the nearer of
`cash-and-bank`'s two Pub. 583 positions. It served **"an entry in the books"** —
binding, in the firm's own words — where the desk's own answer key says *"a
reconciling item, no entry in the books"*. The engine cannot catch that: the
agent was not disagreeing with the firm, it was quoting them about something
else. Nothing checks a position against facts, so the other answer is put where
you cannot miss it instead.

## Two questions do not belong here

- **A decision the firm has to make once** — what the chart of accounts should
  distinguish, whether unreceipted cash is a draw. No authority settles those and
  a desk that answered would be inventing.
- **A defect in the software.** If two legs of a payment do not agree because the
  matcher failed, that is a bug, not a question.
