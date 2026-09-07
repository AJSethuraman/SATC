# What "autonomy" means here — and what the local model is actually for

**Read with `LOCAL-LLM-PATTERN.md` (the ten rules) and `AUTONOMY-CHARTER.md`
(the ladder). This one says *why* those are shaped the way they are, because the
shape is counter-intuitive and easy to undo by accident.**

---

## 1 · The goal, stated once

> A human can do this work. The end state is that the **machine** can do it —
> and does it by **deterministic action**, not by judgment.

Both halves matter. "The machine can do it" is not "the model decides." The
model's role does not grow on the way to autonomy. If anything it **shrinks**.

## 2 · A premise worth correcting

A natural way to describe a local model is: *it runs commands, it doesn't really
think.* In this codebase the truth is closer to the opposite, and the difference
is load-bearing.

**The model cannot run anything.** It has no write capability at all — it cannot
send, sign, file, transmit, move money, close a client request, confirm a staged
value, or compute a tax figure. Not by convention, and not by omitting a tool
from a prompt: those capabilities do not exist on its tool surface, and the
engine refuses them from every path including paths that do not exist yet
(`models/actor.py`, `require_human`). An actor is **derived from request
context** — nothing can *claim* to be the owner, it can only *be* in a live
browser request.

**What the model does is the only genuinely judgment-shaped part of the job:
choosing between options the engine has already enumerated.** Which of four
pre-written sentences fits this client. Which of three open invoices this
payment belongs to. It returns a **KEY**; the engine looks up the text
(principle 6a).

So the division is not "model thinks / code executes." It is:

| | Does what | Why |
|---|---|---|
| **Deterministic engine** | Everything computable from recorded facts: noticing, ranking, refusing, dates, money, classification | Reproducible, auditable, testable |
| **Model** | Picks one item from a list the engine built | The only part that is actually a judgment call |
| **Human** | The irreversible act — sending, signing, filing | Because it is irreversible |

## 3 · Why a finite set, rather than a better prompt

A model that generates has an **infinite output space**. Nobody can read every
sentence that might reach a client, so the only protection is a filter run
afterwards — and a filter is a guess about what you forgot to think of.

A finite set can be read in a minute and edited in a second. The worst failure
becomes *a slightly wrong sentence the practice already approved* rather than
*an invented one*. Those are different orders of problem.

This is why `configs/comms/wording.yaml` exists, and why `compose.py` — which
generated prose — was **deleted** rather than filtered. It also means the system
works with **no model at all**: absent Ollama the default variant is used, which
is a real answer rather than a blank.

## 4 · The move that keeps recurring — judgment is usually a missing fact

This is the most useful pattern in the codebase, and worth naming because it
looks like a constraint and is actually the shortcut.

**Every time this project was tempted to ask the model for a judgment, the right
answer turned out to be "record a fact instead."**

* *Is this job delivered?* Looks like judgment — every task is ticked, surely it
  went out? It is not judgment, it is a **missing fact**.
  `satc.work.stage.derive_stage` refused to conclude it for weeks. Then
  `models/deliverable.py` recorded the outbound act and the question became
  arithmetic. No model involved, ever.
* *Which invoice is this payment for?* Mostly not judgment. If the payment names
  the invoice, nobody decides. If it matches exactly one open balance, nobody
  decides. Only genuine ambiguity reaches a person or a model — and then only as
  *pick one of these three ids*, never *what should this be?*
  (`billing/payment.py`, principle 11b).
* *Is this client on a reduced rate?* Not judgment — a recorded agreement with a
  written basis, or it is refused.

**The instinct to carry forward:** when something seems to need the model to be
clever, first ask whether the practice simply is not writing something down.
Recording the fact is cheaper, permanent and testable. Making the model smarter
is none of those.

`LOCAL-LLM-PATTERN.md` rule 8 says the same thing from the other end: *shrink
the problem before asking the model to be smarter.* Deterministic rules do the
bulk, so the model's tiny budget goes only on the margin.

## 5 · What the ladder is actually for

The autonomy ladder does **not** make the model more capable, and does not
loosen anything about it. It measures a different thing entirely.

Every client-facing template starts **draft-only**. The owner reads it and sends
it. The ladder counts how often the draft was **good enough to send unchanged**,
per (template, client) pair, and *why* when it was not — from five fixed reason
codes, never free text.

Note what is being measured: **the quality of the deterministic pipeline's
output**, not the model's cleverness. A draft is right or wrong mostly because
the *facts and the template* behind it are right or wrong. `wrong_fact` at 30%
and `should_not_have_flagged` at 30% are different practices in different
trouble — which is exactly why the charter forbids ever totalling them into one
accuracy number.

So the eventual removal of a human click is earned by **evidence that a specific
deterministic path has been right N times running**, in a lane narrow enough to
name: this letter, this client. Not "the AI is good now."

**And it grants nothing today.** Charter §10: nothing sends, the no-SMTP AST
test walks all 137 modules and must keep passing, and turning `earned` into
"actually sends" is a separate, deliberate doctrine amendment that must amend
principle 9 by name and retire that test *explicitly*, so its disappearance is a
decision visible in the diff. The system **measures a permission it does not
grant, on purpose** — the measurement is worth having either way.

## 6 · Why deterministic, concretely

Not aesthetics. Four practical properties, none of which a model can give:

1. **Reproducible.** The same facts produce the same answer, so a digest for a
   past day can be regenerated and checked. One that cannot be recomputed is a
   claim, not a record.
2. **Auditable.** Every row carries its evidence in one line, in the owner's
   language. A rank with no reason is a number nobody can argue with.
3. **Testable.** 1481 tests, and invariants that are **mutation-tested** —
   broken on purpose to confirm the suite catches it. You cannot mutation-test a
   prompt.
4. **Refusable.** Deterministic code can say *I will not answer that* and name
   the next step. A state with no sourced rules raises rather than borrowing the
   federal calendar; a plan with no recorded basis will not issue.

## 7 · The give-up tail, designed for rather than fixed

Small models abandon long tasks — roughly 1 run in 6–9, worse under VRAM
pressure. **No prompt fixes this** (`LOCAL-LLM-PATTERN.md` rule 9).

So it is not fixed; it is made **harmless**. Half-finished runs are inert by
construction — nothing committed, nothing postable — and re-running is safe and
cheap because ids derive from what a thing *is* (principle 8). The wrapper
retries; the model does not have to persist. `gave_up` is one of the five reason
codes precisely because it is an expected outcome to be counted, not a defect to
be prompted away.

## 8 · Measure against engine state, never model prose

`LOCAL-LLM-PATTERN.md` rule 10, and it has bitten this project repeatedly. Three
live-model tests asserted on what the model *said* and were flaky for reasons the
code did not control; each was rewritten to assert the **tool call** or the
**engine state** instead. One of those fixes was silently reverted and had to be
reapplied — worth knowing, because the pattern is easy to reintroduce.

The digest and scoreboard follow the same rule: every number is counted from
recorded facts, and nothing on those screens is generated text.

## 9 · Failure directions, stated so they are not inverted

When something is uncertain the system fails **toward the human click**, never
away from it:

* A tripwire that cannot run counts as a **miss**, not a skip. "Nobody ran it"
  is the strongest form of "could not run."
* A capability whose blast radius nobody wrote down holds **everything**.
* A template nobody classified takes the **stricter** rung.
* A precondition never recorded holds every pair at zero, however clean the
  history.

Each of those was got backwards at least once during the build, and corrected.
Expect the same pressure: the "helpful" default is always the unsafe one.

## 10 · The one-line version

> **Deterministic where it can be; recorded where it cannot; the model only ever
> picks from a list; and the human keeps the irreversible act until the evidence
> says otherwise — evidence about a specific lane, not about the model.**
