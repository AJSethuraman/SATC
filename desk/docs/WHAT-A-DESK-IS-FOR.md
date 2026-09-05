# What a desk is for — answering the firm's own questions about it

The firm asked three things about this project while reading the close questions.
This file answers them. Where the answer is *no*, it says no.

---

## "Is it critical for experts to consult each other and to synthesize an answer — is that what the desk's job is?"

> *"I guess maybe it's critical for experts to consult each other every now and
> then and to synthesize an answer is that what the desk's job is?"* — Q18

**Not synthesis. Ordering.** And the difference is the whole mechanism.

A desk answers only from authority it can cite. The moment two desks blend their
answers into a third, that third answer cites neither cleanly — it cites a
reasoning step that happened inside a model, which is precisely the thing this
project exists to stop. Synthesis is where the citation dies.

But the case behind the question is real, and the firm named it themselves:

> *"having an answer to something like the first question could immediately make
> all other questions basically not matter because we're under a safe harbor that
> we just accept"* — Q18

That is not two experts conferring. That is **one answer dissolving a question
before it is asked.** The capitalisation threshold does not combine with the
depreciation question to make a blended answer; it removes it. Ask in the right
order and the second question never reaches anybody.

So what a desk needs is not a conference table. It is:

1. **An order.** Some questions gate others. Ask the gating one first.
2. **A way to say a question is now moot** — which the engine cannot do, and
   which is the missing outcome described below.

Both keep every answer traceable to one paragraph in one source. A synthesised
answer would not be, and no amount of care in the prompt would make it so — that
was measured: the same policy written as prose was obeyed *"100%, 4%, 0% of
runs"*, which is why the citation rule lives in `engine.py` and not in a brief.

## "Tell an agent this is your job, and desk is just available when it gets stuck"

> *"it'd be cool to tell an agent like hey this is your job and then like desk is
> just going to be available so when it gets stuck it kind of can ask desk for
> the next best step ... but that's also kind of desk's job in the sense that it
> saves authoritative decisions"* — Q22

**That is exactly the shape, and it is already the design.** The doer does the
work; the desk is consulted when the doer is stuck; the firm is reached only when
the desk cannot answer either. Nothing about that needs changing.

**What is missing is the return path.** Today a desk can say two things: here is
the answer with its citation, or I escalate. Measured against 43 real questions
from a real close, that covers **11 of them**. The other 32 need a desk to be
able to say:

- *ask the client — this turns on a fact only they have* (11 questions)
- *request this document — it settles it in one look* (8 questions)
- *this is a decision for you, once, and here is what it turns on* (7 questions)
- *this changes nothing; carry on* (1 question)

None of those is an escalation. Sending them up as escalations is what makes a
desk look like it failed when it did its job perfectly.

## "It saves authoritative decisions"

**Yes, and that part is built.** `positions/` holds what the firm decided, in
their own words, with the authority it rests on. An agent proposes there and
never writes; the pull request is the yes. That store is the memory the firm is
describing, and it is deliberately kept apart from `extracted/` so a judgement
can never ride into the record inside a large extraction diff.

## "Maybe even iterate on itself over time"

**This is the one to be careful about, and the answer is a qualified no.**

A desk that learns from its own answers is a desk whose authority is eventually
its own output. Two things may safely accumulate, and they are the two that
already do:

- **`unsupported/`** — every question the desk could not take, with the reasoning
  intact. That queue growing is the desk telling you what it is missing.
- **`positions/`** — the firm's ratified decisions. Each one permanently removes
  a question from the escalation path.

Both grow over time. Neither is written by the desk about itself.

What must never accumulate is a desk's own conclusions fed back as authority.
There is a name for what that produces and the firm has already seen it: an agent
that knew J.Crew sells clothing, concluded *personal*, and was wrong — with every
step of it looking like reasoning.

## "We should probably not look everywhere for answers"

> *"it also makes me think we should probably not look everywhere for answers"*
> — Q20

**Agreed, and the record enforces it.** A desk's `SOURCES.md` is a closed list;
a citation from outside it is refused whatever it says. That is not a limitation
being tolerated, it is the point — an answer sourced from wherever the model
found something is an answer nobody can check.

It is also the correction the firm already made to this work once, on the cash
desk: it was built on **tax** sources for an **accounting** question, because
those were the sources that answered rather than the sources that governed.
*"There is a difference between tax and something like GAAP. I account like an
accountant, even in cash basis."* Reachable is not a reason to store.

---

## What this means for the next build

| The firm said | What is being built |
|---|---|
| experts should confer | an **order** between desks, not a synthesis; the gating question asked first |
| desk answers when the doer is stuck | already the design — but the **return path needs four more outcomes**, not one |
| desk saves authoritative decisions | `positions/`, already built |
| desk might iterate on itself | only the queue and the firm's ratifications accumulate; **never its own conclusions** |
| do not look everywhere | already enforced by a closed source list |

The measured version of all of this is in `CLOSE-QUESTIONS-TRIAGE.md`: **11 of 43
questions from a real close are ones a desk can answer today.** The other 32 are
not desk failures. They are four owners the software does not have yet.
