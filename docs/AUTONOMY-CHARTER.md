# The autonomy charter — how a capability earns the right to act

**Binding, like `DESIGN-PRINCIPLES.md`. Read it before changing anything under
`satc/autonomy/`. It is updated in the same commit as the decision that changes
it.**

This document governs one question: **under what evidence may SATC stop asking?**

It does not itself grant that. Read §10 before assuming otherwise.

---

## 1 · What this is

Every client-facing template begins **draft-only**. The owner reads it and
sends it themselves. That is principle 9 and it is not being softened.

What this system adds is a **measured record of whether the drafts were any
good**: how often the owner sent one unchanged, how often they corrected it,
and *why* when they did. A (template, client) pair that has been right many
times running has earned something. This says what, how it is counted, and how
it is lost.

The point is not to reach autonomy. The point is that **"is this good enough to
trust?" becomes a question with an answer** instead of a feeling.

## 2 · Scope — what can be on the ladder at all

**On:** client-facing communication templates (`configs/comms/*.txt`) —
eighteen today.

**Off, permanently, and not by omission:**

* Anything that **signs**, **files**, **transmits**, or **moves money**. Not a
  ladder rung; not a rung that exists.
* Anything that **computes a tax figure**. Drake is the system of record
  (principle 14).
* Anything that **closes a client request** or **confirms a staged value** on
  evidence a model produced (principle 7).
* **Deleting or amending** a record.

A capability outside §2 cannot accrue a streak, and the ledger refuses to record
one for it rather than silently ignoring it (principle 5).

## 3 · The preconditions gate

The ladder **refuses to accrue any streak at all** until each of these is a
**recorded fact** with a date and who recorded it (principle 2 — asserted is not
recorded):

| Precondition | Why it gates autonomy specifically |
|---|---|
| **Off-disk backup**, verified restorable | Autonomy raises the cost of a bad day. A mistake nobody reviewed is one you find late, and finding it late is only survivable if you can go back. |
| **Tailnet Lock** enabled | The machine holds the identity vault (principle 11a). Widening what runs unattended on it without pinning what may reach it is the wrong order. |
| **MFA** on the mail account and the tax accounts | The first thing autonomy would eventually touch is the outbox. |

Each is re-confirmed on a cadence set in `configs/firm_policy.yaml`. **A lapsed
confirmation freezes accrual and demotes nothing** — freezing is enough;
demoting on a paperwork lapse would train the owner to resent the gate.

This is a hard gate, not advice: `streaks()` returns every pair at rung zero
with the reason named, and no amount of clean approvals moves them.

## 4 · The ladder

A pair is `(template_key, client_id)`. Not a template alone: a letter that is
right for a retired couple may be wrong for a partnership, and the evidence is
about the pair.

    draft_only  ──[ N consecutive approvals, zero edits ]──▶  earned
                ◀────────────[ any correction ]──────────────

**N is firm policy, in `configs/firm_policy.yaml`, not code:**

* `routine: 5`
* `money_or_deadline: 10` — any template whose merge fields carry an amount, a
  statutory date, or a filing consequence.

Which templates are which is **config, not inference**. A template not
classified is treated as `money_or_deadline` — the stricter rung — because an
unclassified template is one nobody has thought about (principle 5).

**"Zero edits" means the body and subject the owner sent are byte-identical to
what SATC rendered.** Not "roughly the same". A changed comma is a correction:
the owner looked at it and decided it was wrong, and we do not get to grade our
own homework on how wrong.

**Consecutive** means consecutive *for that pair*, in time order, with no
correction between. A gap in time is not a break — a client who is emailed twice
a year takes three years to reach rung 5, and that is the correct amount of
evidence, not a problem to engineer around.

## 5 · Demotion — how trust is lost

**Any correction demotes the pair to `draft_only` and resets its streak to
zero.** No partial credit, no decay curve. A curve would be a number nobody
could argue with, standing where a judgment should be.

**One extension, and it is an inference from "fail toward the click" rather than
from the brief — flagged here so it can be vetoed:**

A `wrong_fact` correction demotes **every pair using that template**, not just
the one corrected. A merge field that produced a wrong figure for one client is
a defect in the *template or the data behind it*, and it is near-certain to be
wrong for the next client too. The other four reason codes demote the pair only.

## 6 · Reason codes — the whole point of the exercise

A correction is a one-click reason. **Five, and they are a finite set the owner
picks from — never free text as the primary record** (principle 6a applied to
the owner's own input, so the digest can count them):

| Code | Means | Tells us |
|---|---|---|
| `wrong_fact` | It stated something untrue | The data or the merge is broken. **Fix before anything else** — this is the one that reaches a client as a falsehood. |
| `wrong_judgment` | Facts right, call wrong | The rule that chose this template or this wording is off. |
| `should_not_have_flagged` | Nothing needed doing | Noise. Principle 13 — this is the one that trains the owner to scroll past. |
| `gave_up` | Incomplete or abandoned | The give-up tail (`LOCAL-LLM-PATTERN` rule 9). Expected, ~1 in 6–9. Must be *harmless*, not absent. |
| `missing_capability` | Right idea, SATC cannot do it | A feature request written by the work itself, at the moment it was needed. |

A free-text note is **optional and additional**. It never replaces the code.

These five are not interchangeable and must never be totalled into one
"accuracy" number. `should_not_have_flagged` at 30% and `wrong_fact` at 30% are
different practices in different trouble.

## 7 · Traps and tripwires

A nightly drill runs the whole engine against a **synthetic practice seeded with
known traps** — a $0 invoice, a chase whose date has gone stale, a merge that
would put one client's fact in another's letter, a payment already recorded.
Each trap has one correct behaviour, and it is refusal or a flag, never silence.

* **A miss auto-demotes the affected capability to `draft_only`** and says so on
  the morning digest.
* **Tripwires fail toward the click.** If a tripwire cannot run — the drill
  errors, the synthetic practice will not load, the model is down — that counts
  as a **miss**, not a skip. A check that quietly stops running is worse than
  one that fails, because it looks like a pass.
* Traps live in `configs/` and are **added when a real defect is found**. Every
  bug this project has shipped is a candidate: the $0 invoice, the retroactive
  reprice, the 1999 cheque matching a 2026 invoice.

Each tripwire is **mutation-tested**: break the rule on purpose, confirm the
demotion actually fires (principle 12). A tripwire that has never demoted
anything is not evidence.

## 8 · The digest and the scoreboard

**Read from engine state. Never from model prose.** (`LOCAL-LLM-PATTERN`
rule 10 — every score reads the workbook, never the claims.)

End of day: actions proposed, approvals vs corrections **broken out by reason
code**, streak position for every pair, trap results, give-ups. Weekly: one
page, the same numbers over seven days, plus what moved.

The digest is deterministic and reproducible: the same state produces the same
digest, and it is regenerable for any past day from the recorded facts. A digest
that cannot be recomputed is a claim, not a record.

## 9 · Abort criteria — when this stops

The experiment ends, and the ladder is removed rather than tuned, if:

* `wrong_fact` corrections are **not trending to zero** over eight weeks. A
  system that states untrue things to clients does not get to keep trying.
* Any trap miss reaches a **real** client artefact rather than the synthetic
  practice.
* The digest and the underlying records **disagree** and the cause is not found
  the same day. A scoreboard nobody can trust is worse than none.
* The owner finds themselves **checking more carefully** because of the ladder
  rather than less. That is a net loss and the whole justification is gone.

## 10 · What this does NOT authorise, and what it strains

**NOTHING HERE SENDS ANYTHING.** No SMTP is added. The AST test that proves
there is no send path in this codebase **stands and must keep passing**. A pair
reaching `earned` changes one thing: a recorded fact that says it has been right
N times running.

**Turning `earned` into "actually sends" is a separate, deliberate doctrine
amendment**, made in its own commit, which must:

1. amend principle 9 in `DESIGN-PRINCIPLES.md` explicitly, in the same commit;
2. state what replaces the click as the last line of defence;
3. retire the no-SMTP AST test *by name*, so its disappearance is a decision in
   the diff rather than an absence nobody notices.

Until that commit exists, this system **measures a permission it does not
grant** — and that is on purpose. The measurement is worth having whether or not
the permission is ever given.

**What this strains, said out loud** (per `DESIGN-PRINCIPLES.md` §"Keeping this
current"):

* **Principle 9** most of all. The honest statement is that this builds the
  evidence base for weakening it later. The mitigation is §10: the weakening is
  a separate decision that has to argue for itself, and the invariant that
  enforces 9 keeps passing until then.
* **Principle 13.** A ladder is a thing to check. If the streak positions become
  a screen the owner scrolls past, that is the §9 abort criterion firing.
* **Principle 12.** A streak is a check that has *only ever passed* — that is
  what a streak is. Which is exactly why §7's traps exist: they are the part
  that can fail.

## 11 · A gap in the foundation, named rather than assumed

**The approvals this ladder counts do not currently exist as recorded facts.**

Today the Today queue's dismissal lives in `session[_DISMISSED]` — browser
session state, gone when the cookie clears, invisible to the engine, carrying no
actor and no date. Nothing anywhere records "the owner read this draft and sent
it unchanged."

So the streak ledger cannot merely *derive* from existing approval actions; the
recorded fact has to be created first, with the shape everything else in this
codebase uses: **what, when, who — the actor derived from request context, never
passed in** (principle 6), **an id derived from what the thing is** (principle
8), and **durable** so a digest is regenerable for a past day.

That record is the actual first deliverable. Building the ladder on session
state would have produced a scoreboard that resets when a cookie clears.
