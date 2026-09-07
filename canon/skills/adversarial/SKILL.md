---
name: adversarial
description: Hand a codebase to another agent with one job — break it, writing only tests and never touching source — then take the findings back with one command. Use when the firm wants a second model to try to find bugs, when a suite has grown confident, before trusting a component with something that matters, or when asked what work to give another AI. Carries the brief to hand over and the intake that reads the result.
---

# The adversarial pass

Hand a codebase to a different model and give it one job: **break this.** It
writes tests, never source. Every finding comes back as a test that goes red
against the code as it stands.

## Why this is worth doing at all, given we already mutation-test

Mutation testing breaks a guard on purpose and confirms a test goes red. It is
the strongest check in the fifteen behaviours and it has a hard limit:

**Mutation grades the guards you wrote. It is silent about the case nobody
thought of.**

The proof is in this repository. `_in_scope` decides whether a conviction bears
on a decision by asking whether either scope string contains the other. Every
test written for it happened to use values that match. Mutate the function and a
test goes red — the mutant dies, the guard looks sound. But a conviction scoped
*everything*, checked against a decision scoped *SATC pricing*, matches in
neither direction, so the broadest entries on the record are the quietest ones.
138 tests passed. The case was never written, so there was nothing to mutate.

The second reason matters more and is harder to fix from inside: **whoever wrote
the code also wrote the tests and chose the mutants.** One blind spot is a blind
spot three times. Another model is not better at this. It is *differently
wrong*, and that is the whole value.

## What makes this safe rather than merely careful

**Only one file crosses over.** Not by instruction — by construction:

```
python "${CLAUDE_PLUGIN_ROOT}/intake.py" codex/canon-adversarial
```

That checks out exactly `canon/findings/test_findings.py` from the branch, runs
it, and reports. Whatever else the branch carries — scratch harnesses, fixtures,
an edited module, a half-finished refactor — is never read and cannot land.

So the far side is **free to write whatever code it needs**. Say so when you hand
the brief over: it changes what it optimises for, and a sandbox nobody can
contaminate is worth more than a promise not to.

**The findings do not join the suite.** They land in `findings/`, which
`pytest tests` does not collect. A red test in `tests/` would make the suite red
and every later run would report a failure that is a finding rather than a
regression — and after two days nobody reads either.

## The brief to hand over

Give this to the other agent verbatim. Swap the target if it is not `canon/`.

> You are looking for bugs in `canon/` in the SATC repository. Read the
> `how-we-work` skill first — the fifteen behaviours govern how you report.
>
> **You may not modify a single line of source code.** Not one. Your only
> deliverable is tests. This is not a style preference: it is what makes your
> findings free to be wrong.
>
> **What a finding is.** A test you wrote, that asserts correct behaviour, that
> **fails against the code as it stands**, and that you have run and watched
> fail. Prose is not a finding. A hypothesis is not a finding. If you cannot
> make it go red, you have not found anything — say so and move on.
>
> **What you are hunting.** Not weak tests — mutation testing already covers
> those and it runs here. You are hunting **cases the existing tests never
> exercise at all.** Mutation grades the guards that exist; it is silent about
> the one nobody wrote. That gap is your whole job.
>
> **A worked example of exactly the shape.** `_in_scope` in `challenge.py`
> decides whether a conviction applies to a decision by asking whether either
> string contains the other. Every existing test happens to use values that
> match. But a conviction scoped `everything`, checked against a decision scoped
> `SATC pricing`, matches in neither direction — so the broadest convictions on
> the record are the ones that fire least. 138 tests pass. Mutating that
> function kills the mutant, because the tests that exist do cover it. The case
> was simply never written. Find more like that.
>
> **Where to look, in rough order.** Values at the edges of a rule rather than
> in the middle. Empty, absent, and "cannot tell" travelling through a path that
> only ever saw populated inputs. Two functions that must agree, with nothing
> comparing them. Text handling where the fixture is always tidy — unicode, line
> wrapping, quotes inside quotes, an em-dash where a hyphen was assumed. A guard
> whose test proves it fires but never proves it stays quiet on the clean case.
>
> **Report the denominator.** Not "I found 3 bugs." Say how many hypotheses you
> formed, how many you tried, how many produced a red test, and how many turned
> out fine — and list what you checked and found clean. A survey that reports
> only what it found is not a survey.
>
> **Deliverable.** A branch `codex/canon-adversarial`. One file,
> `canon/findings/test_findings.py`, containing only tests that currently fail,
> each with a docstring saying what behaviour it expects and why. Plus your
> report.
>
> **Everything you write outside that one file will be discarded unread.** Write
> whatever scratch code, harnesses or fixtures you need — they are free — but
> that file is your entire deliverable. Never open a pull request against
> `main`. Never touch `client-documents/`, `satc_system/` or `website/`. There
> is no client data in `canon/` and you must not introduce any.
>
> **If everything passes, that is a result too.** Say what you tried and why you
> now believe it holds. Do not manufacture a finding in order to have one.

## Taking the result back

```
python "${CLAUDE_PLUGIN_ROOT}/intake.py" <branch>
```

It reports how many tests it took, how many reproduce, how many pass, and what
else the branch touched — listed but never read, because what a branch did
outside its lane says whether to trust it with a bigger job next time.

**Then triage, and the triage is yours, not the runner's.** A red test proves
the code differs from what that test expects. It does not prove the expectation
is right. Read each one, decide whether the behaviour it wants is the behaviour
the firm wants, and only then change anything. A finding you disagree with is
still worth its minute — say why, and delete it.

**When you fix one:** move its test into `tests/`, where it joins the suite and
stops anything putting the bug back. Then record the incident in `TENETS.md` —
that is what turns one bug into a rule, and it is the reason the tenets are
worth following.
