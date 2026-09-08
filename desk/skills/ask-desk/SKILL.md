---
name: ask-desk
description: Consult an expert desk when a question is outside your authority — bookkeeping, tax treatment, whether a cost is the business's, what a purchase is. Use when you are doing the work and hit something you cannot settle from what is in front of you, rather than guessing and moving on. Sends the question to the session that holds the desks and receives the answer back; the desk answers only from authority it can cite, or tells you who has to be asked.
---

# Ask a desk

**You are doing the work. The desk is who you ask when you cannot settle
something.** It is not a second opinion on your judgement — it is the authority
you do not have.

**You do not hold the desks and you cannot read them.** You send a question to
the session that does, and it sends an answer back. That is not a limitation
working around a packaging problem; it is the design, and it buys two things:

- **The desk can go and look.** It runs on the Forge with a browser. Where its
  record does not reach a question it can search, tie the find out against the
  publisher's own page, and come back with the passage — or with *"looked, and
  it is not there"*, which is a real answer and one a library cannot give.
- **You cannot cite past what you were handed.** Holding the record means being
  able to reach for authority the desk did not offer. Not holding it makes the
  citation gate a boundary rather than a check.

`docs/THE-DESK-IS-A-SESSION.md` is the argument in full.

## Sending a question

**`SATC_DESK_SESSION` must be set** — it holds the session id of the session
running `be-the-desk`. It is deployment state and is deliberately not committed:
an id shipped with the plugin would be stale for everyone but the machine it was
written on. If it is unset, `relay` says so rather than guessing, and the fix is
to export it — not to hunt for a session id and paste one in.

```python
import os, sys
sys.path.insert(0, os.environ.get("CLAUDE_PLUGIN_ROOT", "."))
import relay

desk = relay.desk_session()                    # refuses if SATC_DESK_SESSION is unset
a = relay.ask("the bank statement shows a $10 service charge and nothing for "
              "it is in the books — what do I do with it?",
              reply_to=<this session's own id>)   # get_session, omit session_id
print(a.ref)                # note it — the answer opens with it
print(desk)
print(relay.as_prompt(a))   # the message to send
```

Then send that text to the desk session it printed, **poke-only**:

```
create_trigger(name=f"Desk request {a.ref}",
               persistent_session_id=<what desk_session() returned>,
               initiation="human_schedule",
               prompt=relay.as_prompt(a))     # NO run_once_at, NO cron
fire_trigger(<the id it returns>)
```

Then **end your turn**. The answer arrives as a message and wakes you. Do not
poll, do not sleep, and do not chase — see below.

## Four rules, each of them from something that went wrong

**1 · Omit `run_once_at` and `cron_expression`, always.** A trigger that carries
a schedule and is then poked **delivers twice** — once on the poke, once when
the scheduler reaches the minute. Measured 8 September 2026 on three of this
repository's own triggers. On a close that means every question answered twice.
Poke-only delivers once, in about eight seconds.

**2 · Do not chase.** `fire_trigger` returns a `last_fired_at` the durable
record does not corroborate, so "sent" can precede arrival. A session chased its
own request on 8 September and wrote *"nothing arrived here"* **1.67 seconds
after** the answer had landed. If you must check, read `list_triggers` — not
your own tool result — and never sooner than a minute.

**3 · Send no context, and no client identifier.** `relay.ask` refuses a TIN,
and it has nowhere to put context on purpose. The firm, 8 September 2026:
*"we don't add context to it, that defeats the purpose. it falls the same rules
and gets the de-identified data so it can ensure it answers and asks things
objectively."* An asker who writes the context writes the answer, and then the
desk is your own reasoning coming back with a citation attached. The desk reads
the facts off the record itself, where the ones nobody holds are named as
missing.

**4 · One question per envelope.** Each carries a `ref`. If two answers arrive
with the same one, the second is a duplicate delivery and not a second opinion —
read one and discard the other.

## What comes back, and what you must pass on

The desk returns a served answer or a refusal. **Print what it sent you, whole.**
Every field is there because a reader needed it, and the ones that look like
boilerplate are the ones that are not:

| | |
|---|---|
| `unchecked` | nobody verified the conclusion against the paragraph. Always set |
| `passage` | the cited text, so whoever reads your answer can do that check at a glance |
| `alongside` | the firm's OTHER positions on this same passage, where they hold one — with their authority underneath |

**None of it is yours to trim.** On 7 September a session cited
§ 1.263(a)-2(d)(1) — whose text opens *"a taxpayer must capitalize amounts paid
to acquire or produce a unit of real or personal property"* — to conclude
**"deducted, not capitalized"**. Primary, binding, no caveat. With its passage
underneath, that answer refutes itself on sight. Without, it reads as settled
law.

And where `alongside` is not empty, **read it before you act**: the firm has
answered that passage more than once, the other answer is not this one, and
which applies is a question about facts that nothing in the desk has looked at.

## A refusal is an answer

`authority_absent`, `context_not_on_file`, `wrong_body_of_authority` and the rest
are findings, not failures. The refusal carries `working` — the desk's own
reasoning — and that is usually the part you hand to a person. Do not retry a
refusal with a softer question until it serves; that is how a guess acquires a
citation.

## Two questions do not belong here

- **A decision the firm has to make once** — what the chart of accounts should
  distinguish, whether unreceipted cash is a draw. No authority settles those and
  a desk that answered would be inventing.
- **A defect in the software.** If two legs of a payment do not agree because the
  matcher failed, that is a bug, not a question.
