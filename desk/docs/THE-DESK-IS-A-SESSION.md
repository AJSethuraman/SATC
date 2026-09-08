# The desk is a session, not a library

**Decided by the firm, 8 September 2026**, setting the bar for V1:

> *"the final check for this for V1 will be to have Forge - Occam install the
> new plugin we are designing and run a close from start to finish on Sarcia
> Services [...] this implies that the skill is able to call for questions and
> receive back answers from Forge - Desk"*

And the reason, which is better than the one this document was first drafted
around:

> *"this is my solution to getting as much info as possible because the ask-desk
> session (in this case Forge - Desk) is on the Forge itself so it can use its
> browser and such."*

---

## What changes

Today `ask-desk` is a skill that does `sys.path.insert(ROOT); import ask`. The
desks are files on the calling agent's disk, and consulting one is a function
call. Every problem this repository has fought for three days follows from that:
the plugin has to be installed, the install has to be current, the SKILL.md the
harness serves has to match the code, and a doer holding the record can read past
whatever it was handed.

**In the new shape the doer holds none of it.** It sends a question to a session
that holds the desks, and receives an answer. Two consequences, in the order they
matter.

### 1 · `authority_absent` stops being terminal

This is the change the firm is actually buying, and it is larger than the
boundary argument.

A desk that is a library can only ever answer from what was stored. When nothing
reaches the question it refuses `authority_absent` — *"we do not have the rule
yet"* — files it in `unsupported/`, and somebody runs `run-down-a-question` by
hand, later, if at all. **A refusal that nobody has looked for is
indistinguishable from a refusal after a competent search.**

A desk that is a session on the Forge has a browser. It can answer that refusal
in the same breath: search, verify against the publisher's own page, and come
back either with the passage or with *"looked, and it is not there"* — which is a
real finding and one this system currently cannot produce. `searching.py` and the
`run-down-a-question` skill already exist for exactly this and have only ever run
as a separate manual step.

The refusal vocabulary in `engine.REASONS` does not change. What changes is that
`authority_absent` acquires a next step that happens automatically, at the desk,
where the browser is.

### 2 · The doer cannot cite past what it was handed

The engine's whole design is *the model proposes, the engine disposes* — an agent
reads the authority it was given and proposes a conclusion, and `serve` refuses a
citation that does not resolve. Today that is enforced by a check the doer could
in principle route around, because the doer has the record on disk.

Across a session boundary it is not a check, it is a boundary. The doer receives
a brief and returns a proposal; nothing else crosses. This was the argument this
document was first written around, and it is the smaller of the two.

### 3 · The distribution problem deletes itself

The doer needs no plugin, so the install cannot be stale, so the SKILL.md the
harness serves cannot be four releases behind the code. Three of the last five
releases were spent hardening that path. One session installs the desks — the
Desk session — and it is the one that also runs the tests.

---

## The transport

Both legs exist today and neither needs new infrastructure:

| leg | mechanism | proven |
|---|---|---|
| doer → desk | `create_trigger(persistent_session_id=<desk>)` then `fire_trigger` | **yes** — six firings, 7 Sep 2026 |
| desk → doer | the same, bound back to the asking session | **being tested, 8 Sep 2026** |

`get_session` reports `cross_session_inbound: available` on a session that can
receive. A trigger may bind to any session on the same account.

**Every answer before 8 September came back through a person.** Questions were
fired into a Forge session by trigger and the reports were copied out of a window
by the firm and pasted back. **At 00:41 UTC on 8 September a Desk session
answered a question and woke the asking session with it, and no person carried
anything.** That is the leg V1 needed.

### Send it POKE-ONLY, and never with a schedule attached

Measured on this repository's own traffic, 8 September 2026. **A trigger created
with a `run_once_at` and then poked with `fire_trigger` DELIVERS TWICE** — once
on the poke, and again when the scheduler reaches the scheduled minute:

| trigger | `run_once_at` | poked at | durable `last_fired_at` |
|---|---|---|---|
| the desk's answer | 00:42:19 | 00:41:21 | **00:43:19** |
| the 0.7.3 round | 23:55:00 | 23:32:11 | **23:55:07** |
| the 0.7.2 round | 23:20:00 | 23:05:46 | **23:20:44** |

A trigger created with **neither** `cron_expression` **nor** `run_once_at` — the
poke-only routine — delivered **once**, in **eight seconds**, and its record
carries `next_run_at: 0001-01-01` with no `run_once_at` field, so a second copy
is not merely unlikely but impossible.

**This is not a tidiness point. On a close it duplicates the work**: every
question the doer asks would be answered twice, and every answer delivered twice.
It is also the explanation for something already reported and wrongly dismissed —
the Forge session, 7 September: *"Six firings, three distinct prompts, and each
has fired exactly twice [...] That is a consistent duplicate, not drift."* It was
read as a scheduling misconfiguration and never diagnosed. It was this.

### `fire_trigger`'s success is not delivery

The second half, found by the Desk session pulling `list_triggers` after being
wrongly accused of having stopped:

> *"`fire_trigger`'s response says the message fired when it has not. An agent
> that trusts its own tool result — the only thing it has — will report the
> return leg complete up to two minutes before it is, every time. The asking side
> then cannot distinguish 'not sent' from 'sent, not yet polled', so it chases,
> and the chase is indistinguishable from a real failure."*

Which is exactly what happened: the chase routine was created at 00:43:20.920 and
the answer had landed at 00:43:19.253. **1.67 seconds.** A session read a stale
`post_turn_summary`, concluded the return leg had failed, and published that to
the firm while the answer was already in the queue.

Poke-only delivery removes the two-minute window that made this possible. The
rule that outlives it: **a tool result saying a message was sent is not evidence
that it arrived**, and a summary of another session is not that session.

### Compute the timestamp last

One more, from the same run, worth a line because it will happen to anyone
composing a long report: a resend was rejected with *"run_once_at must be in the
future (run_once_at in past)"* because the timestamp was computed at the START of
composing a long prompt and the composition outlived it. Poke-only avoids this
too — there is no timestamp to outlive.

---

## Books, and the access ladder that was never walked

The firm, the same evening:

> *"longer-term note - this is also what i meant by books... like we could have
> pdf texts or something to search through right?"*

`record.ACCESS` already declares the ladder:

    ("public_fetch", "headless_browser", "signed_in_browser", "human_only")

**All 36 sources sit on the bottom rung**, and the ladder has never been walked —
because a desk that is a library can only fetch. A desk that is a session moves
the ceiling: a PDF the firm holds becomes searchable authority whose citation
resolves to a page, without the text being republished anywhere this repository
controls.

That also reframes the FASB question honestly rather than routing around it. ASC
is `human_only` because of a licence, not because it is unreachable — the Basic
View is behind a reCAPTCHA and a terms click and is marked *"For Personal and
Non-Commercial Use"*. **"A session with a licensed copy in front of it" is a
different question from "a model trained on it", and it is the firm's question,
not this software's.** Nothing here should assume an answer.

---

## What is NOT decided

- **Whether the Forge sees real client data.** The desks never need a name to
  answer whether a deposit is a reconciling item, so a de-identified close is
  buildable and is the default assumption until the firm says otherwise. Real
  Sarcia figures crossing into a container is their call.
- **What a close consists of, step by step.** The desks answer questions; they do
  not hold books, a trial balance, or a transaction list. `client-documents`
  holds the engagement lifecycle and `satc_system` holds the interview and the
  Drake seam, and nothing today wires a desk consultation into either. That
  wiring is the bulk of V1 and is not designed.
- **The judge.** A second model handed the paragraph and the conclusion, asked
  whether one supports the other. Still the general answer to every "confident
  and wrong" the Forge has found, still not built, and unaffected by any of the
  above.
