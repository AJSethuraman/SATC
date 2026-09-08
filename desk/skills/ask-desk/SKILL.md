---
name: ask-desk
description: Consult an expert desk when a question is outside your authority — bookkeeping, tax treatment, whether a cost is the business's, what a purchase is. Use when you are doing the work and hit something you cannot settle from what is in front of you, rather than guessing and moving on. Sends the question to the session that holds the desks and receives the answer back; the desk answers only from authority it can cite, or tells you who has to be asked.
---

# Ask a desk

**You are doing the work. The desk is who you ask when you cannot settle
something.** It is not a second opinion on your judgement — it is the authority
you do not have.

**You may well be able to read the desks. Do not.** `desk/desks/` is very
likely sitting in the checkout you are working in, and nothing stops you opening
it. This file used to say *"you do not hold the desks and you cannot read them"*,
and a doer on 8 September read five files out of it before sending anything —
correctly noting that a skill asserting you are unable, where you are plainly
able, gives you no rule to follow:

> *"a check that runs on the honour system, because the skill does not ask the
> doer to refrain, it asserts they are unable. A doer who reads that sentence,
> notices the files, and infers the skill is describing some other deployment
> has been given no rule to follow. I would rather it said: you may be able to
> read them, do not, and here is why."*

So: **the rule is do not read them, and here is why.** You send a question to the
session that holds them, and it sends an answer back. Two things that buys:

- **The desk can go and look.** It runs on the Forge with a browser. Where its
  record does not reach a question it can search, tie the find out against the
  publisher's own page, and come back with the passage — or with *"looked, and
  it is not there"*, which is a real answer and one a library cannot give.
- **You cannot cite past what you were handed.** Holding the record means being
  able to reach for authority the desk did not offer. Not holding it makes the
  citation gate a boundary rather than a check.

`docs/THE-DESK-IS-A-SESSION.md` is the argument in full.

## First: is the skill you are reading the one that is installed?

**Ask the CLI, not the file you are holding.** One command, and the disagreement
is the whole defect:

```
claude plugin details desk@satc
```

It prints the version and a **Component inventory** listing the skills that
plugin has. **If a skill it names cannot be resolved by the Skill tool, or the
version it reports is not the version you think you are following, the session's
skill table is stale and you are reading old instructions.**

Measured on the firm's machine, 8 September 2026, minutes after a clean install:

| | version | `be-the-desk` |
|---|---|---|
| the files on disk | 0.10.1 | present |
| `claude plugin details` | 0.10.1 | **known** |
| the running session's Skill tool | **0.4.0** | **Unknown skill** |

Five releases apart, in one session, at the same moment. **Neither installing
nor `/reload-plugins` fixed it** — a reload ran earlier that night with 0.6.2
installed and bound 0.4.0 anyway, which the desk proved by fingerprint: a
two-skill set (`ask-desk`, `desk-factory`) exists only in 0.4.0.

So the stale thing is not the plugin cache. **It is the session's skill table,
bound once when the session started**, and nothing observed rebinds it. That is
a harness fact this repository cannot fix — but it is cheaply *detectable*, and
the desk that found it said why this is the right check: *"`claude plugin
details` is a reliable oracle for what SHOULD be loaded, from inside the
session, cheaply."*

**And a version that is only on a branch can NEVER be installed.**
`claude plugin update desk@satc` resolves through the marketplace listing on
`main`, so while work sits on a feature branch the installed plugin is whatever
`main` last carried — by construction, not by fault. On 8 September a session
told the desk to *stop unless `plugin details` reports 0.10.2*, and the desk
answered that the rule *"can only ever fire, never clear"*: 0.10.2 existed only
on the branch. **Do not write a stop condition against an unmerged version.**
Check that the CHECKOUT is current, and read the version off the brief's own
header, which comes from the code doing the work.

**If they disagree, work from the checkout** — `import` from the repository's
own `desk/` — and do not follow the skill the tool serves you. A fresh session
is the only known cure and you probably cannot start one.

## Sending a question

**`SATC_DESK_SESSION` must be set** — it holds the session id of the session
running `be-the-desk`. If it is unset, `relay` says so rather than guessing.

**Which one it is IS written down: `docs/WHERE-THE-DESK-IS.md`.** That page
carries the id, the date it was last confirmed, and what to do if it looks
wrong. Read it and export the value.

**It is a record to read, never a default the code applies**, and both halves
were paid for. On 8 September 2026 a session with the variable unset told the
firm the round trip *"cannot be done from this container"* — then found the id
in ninety seconds in `list_triggers`, where every past round trip had left one.
Nothing in the repository said where the desk was, and a step that needs
archaeology is a step that gets skipped. But `relay.desk_session()` still
REFUSES rather than reading that page, because a session id changes when a
container is replaced and **a stale id fails silently**: the question goes
somewhere, the asker waits, and nothing says the desk never saw it. A human or a
session exporting the value is the check that it is still the right one.

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

**Then COPY what it printed into the tool call.** `relay.as_prompt(a)` is a
Python expression and `create_trigger` is a harness tool in a different
execution context — there is no way to pass one to the other, and the earlier
version of this section wrote `prompt=relay.as_prompt(a)` as though there were.
A doer had to invent the copy step and said so:

> *"I printed the prompt in the Python block and hand-copied the printed text
> into the tool call, which works but is an invented step and a transcription
> risk on a multi-hundred-word string with backticks and em-dashes in it."*

Copy it **whole and unedited** — the envelope carries the protocol the desk
needs, and a paraphrase drops it. Then, poke-only.

**FIRST: THE TOOL NAMES DIFFER BY SURFACE, AND FOLLOWING THIS SECTION LITERALLY
CAN LEAVE YOU UNABLE TO SEND ANYTHING.** Measured on the first live close,
8 September 2026: Forge-Occam had **no `create_trigger` and no `fire_trigger`
at all.** A doer following the sequence below as written got HTTP 400 —
*"One of job_config or session_request must be set"* — and recovered only by
listing existing triggers and reverse-engineering the body from one of them.
Their words: *"A doer following ask-desk as written cannot send anything at
all, and nothing in the skill hints at it."*

**So look at what you actually have before you compose the call.** Two shapes
are known to exist:

**A · `create_trigger` / `fire_trigger`** — separate tools, flat arguments:

```
create_trigger(name="Desk request <the ref you printed>",
               persistent_session_id="<the id desk_session() printed>",
               initiation="human_schedule",
               prompt="<paste the printed envelope here, entire>")
fire_trigger("<the id create_trigger returned>")
```

**B · `RemoteTrigger`** — one tool with an `action` of `create` then `run`, and
the message is NESTED rather than a flat `prompt`. As reported from the Forge,
the envelope goes in `session_request.events[].payload.message.content`, with
`persist_session` and `persistent_session_id` alongside. **This shape is
recorded from one doer's report, not from a schema this repository holds** — so
read your own tool's description, and if it disagrees, the tool wins.

**If neither is present, say so and stop.** Do not invent a transport. The
question not being sent is a better outcome than a question sent somewhere
nobody reads.

**No `run_once_at`. No `cron_expression`.** A trigger carrying either, then
poked, delivers twice.

Then **end your turn**. The answer arrives as a message and wakes you. Do not
poll, do not sleep, and do not chase — see below.

## Four rules, each of them from something that went wrong

**1 · Omit `run_once_at` and `cron_expression`, always.** A trigger that carries
a schedule and is then poked **delivers twice** — once on the poke, once when
the scheduler reaches the minute. Measured 8 September 2026 on three of this
repository's own triggers. On a close that means every question answered twice.
Poke-only delivers once, in about eight seconds.

**2 · Do not chase — but do not die silently either.** Before you end your turn,
set ONE fallback reminder to yourself, 20–30 minutes out, and cancel it when the
answer lands. The skill said only "do not chase", and a doer had to invent this:

> *"It never says what to do at the point where the answer is genuinely not
> coming. I invented a 25-minute fallback reminder to myself so the work would
> not stall silently [...] The failure mode it guards against — doer ends turn,
> nothing ever wakes it, task dies without a word — is worse than the chasing
> the skill correctly prohibits."*

Right. A dead task nobody is told about is the worse failure. One reminder is
not chasing; a loop is.

**2b · And when you do check, check the durable record.** `fire_trigger` returns a `last_fired_at` the durable
record does not corroborate, so "sent" can precede arrival. A session chased its
own request on 8 September and wrote *"nothing arrived here"* **1.67 seconds
after** the answer had landed. If you must check, read `list_triggers` — not
your own tool result — and never sooner than a minute.

**3 · A CHARACTERISATION IS CONTEXT. This is the one that got past a careful
doer.** On the first live close, 8 September 2026, Forge-Occam asked *"a sole
proprietor bought hand tools for the trade..."*. **The record says LLC.** It had
written the entity from the shape of the books — one operator, no payroll —
rather than from the file, and did not check before sending. Its own reading,
and it is sharper than the rule it broke:

> *"the rule 'send no context' is stated as being about CLIENT IDENTIFIERS and
> privacy. The failure mode I hit is different and more dangerous — a
> DESCRIPTIVE fact smuggled in as scene-setting, which reads as harmless and is
> not. 'a sole proprietor bought' feels like framing; it is a legal
> characterisation."*

It changed nothing that night **by luck** — the tools question turned on a
policy date, not the entity. On *"is this income to the taxpayer"* it would have
steered the desk with an unverified characterisation and left no way to know.

So: **sole proprietor, LLC, S-corp, employee, contractor, business, personal,
rental, capital** — every one of these is a conclusion wearing the clothes of a
description. Name the thing that happened and let the desk ask. If you genuinely
know the entity because you READ IT IN THE FILE, it is a `Context` fact with a
name, not an adjective in a sentence.

**3b · Send no context, and no client identifier.** `relay.ask` refuses a TIN,
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

The desk returns **one of two things**, and they carry different fields. Print
what it sent you, whole, either way.

**If it ANSWERED**, and none of this is yours to trim:

| | |
|---|---|
| `unchecked` | nobody verified the conclusion against the paragraph. Always set |
| `passage` | the cited text, so whoever reads your answer can do that check at a glance |
| `alongside` | the firm's OTHER positions on this same passage, where they hold one — with their authority underneath |

**If it REFUSED**, you get none of those and that is correct — a refusal cites
nothing, which is what makes it a refusal:

| | |
|---|---|
| `reason` | one of a closed set. `facts_not_established`, `authority_absent`, … |
| `desk` | which desk refused. A question reaches more than one |
| `working` | the desk's own reasoning. Usually the part you hand to a person |
| `ask` | **the follow-up question.** Set wherever a person can resolve it |

This split is here because the single table that used to sit above read as
universal. A doer on 8 September went looking for `passage` on a refusal:
*"A doer looking for `passage` in a refusal will not find it and has been given
no signal that is expected."*

**None of it is yours to trim.** On 7 September a session cited
§ 1.263(a)-2(d)(1) — whose text opens *"a taxpayer must capitalize amounts paid
to acquire or produce a unit of real or personal property"* — to conclude
**"deducted, not capitalized"**. Primary, binding, no caveat. With its passage
underneath, that answer refutes itself on sight. Without, it reads as settled
law.

And where `alongside` is not empty, **read it before you act**: the firm has
answered that passage more than once, the other answer is not this one, and
which applies is a question about facts that nothing in the desk has looked at.

## `authority_absent` is not a dead end — send it on

**When every desk says `authority_absent`, nobody holds the rule.** That is not
the end of the question; it is a job for the session that can go and look. The
firm, 8 September 2026: *"the skill also has to direct questions to this
container when they need research, obviously."*

```python
gap = relay.research(question, reply_to=<your session id>,
                     refused_by=(("capitalization-and-de-minimis", "authority_absent"),
                                 ("vehicle-expense", "authority_absent")))
print(gap.ref)
print(relay.research_prompt(gap, reply_to=<your session id>))
```

Send that to the same desk session, **poke-only**, exactly as you sent the
question. It comes back opening `FOUND <ref>` or `LOOKED <ref>`.

**`refused_by` is required and only `authority_absent` is accepted.** Every other
refusal is answered by a person, by the firm, or by asking a different desk —
and sending one to a searcher is how a refusal gets talked out of: the desk said
no, so go and find something that says yes. `relay.research` refuses them.

**`LOOKED <ref>` — searched, and the authority is not reachable — is a real
result.** It turns a gap nobody has examined into a gap somebody has, which is
the difference between a queue and a pile. Do not treat it as a failed lookup.

**Nothing found this way is authority yet.** The searcher proposes; the firm
admits a source. An answer that cites something no desk holds is refused by the
engine exactly as before, and correctly.

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
