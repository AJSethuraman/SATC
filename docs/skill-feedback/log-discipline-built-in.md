# Skill-improvement prompt: make "keep the running log" a built-in pipeline step

> **How to use this file:** hand the prompt in the block below to the architect
> of the Occam pipeline skills (`occam`, `grill-me`, `to-prd`, `to-issues`) — an
> agent or a person — to implement the change. The sections above the block are
> the context/rationale it draws on.

## Why this exists

Across a real Occam run (the **Credit Review OS** project, 2026-07-04), the owner
repeatedly steered toward capturing *future/deferred* scope in a durable running
log rather than losing it — and then said, explicitly:

> "the log we made — I want a prompt to give the architect of that skill a
> rundown of how we used the log … and how I want it as a **recommended and
> built-in idea when it makes sense so I don't need to remember to do it**."

So the goal: the pipeline should *offer to maintain the running log on its own*,
at the right moments, instead of relying on the operator to remember.

## How the log was used in that run (the pattern to bake in)

This repo already has a strong running-log culture the skills should lean on,
**not reinvent**:

- **`PLAN.md`** — a living log: "Where things stand", "In flight", a
  **Recommended roadmap** (phased), a **To-do**, an **Explicitly deferred
  (decided against for now)** section, and a **Decisions log** (dated, newest
  first).
- **`BACKLOG.md`** — a shared open/`~`/done to-do list with a dated **Done log**;
  its "Standing rules for new items" literally say *"New idea → add a line here."*
- **Per-project logs** — `BUILD_NOTES.md`, the `L1..Ln` carried-lessons notes in
  `TEMPLATE_CONTRACT.md`/build specs.

During the Credit Review OS run, the log discipline showed up as:

1. **Deferred scope was captured, not dropped.** When the owner said v1 keys
   assessments but "the log should also include adding data parsing and OCR …
   maybe a local LLM … but keep it deterministic," those items went into the PRD
   as **Non-Goals** + **Milestones/Roadmap**, *and* a dedicated **issue slice
   (Slice 9)** was created to write a running-log entry so they persist.
2. **A multi-phase roadmap was defined up front** (the cash-flow-out LOB order)
   because the owner "clearly wants everything" — the log is where "everything"
   stays the documented destination while v1 stays small.
3. **Cross-cutting principles were logged** (deterministic core authoritative;
   LLM never in the data path; PII bar) so they outlive the current issue set.
4. **Ephemerality forced persistence** — sessions here are wiped, so anything not
   committed to a log file is gone. The log entry had to be a committed artifact.

## The ask (paste this to the architect)

```
Update the Occam pipeline skills so that MAINTAINING THE RUNNING LOG is a
recommended, built-in step — offered automatically at the right moments — rather
than something the operator has to remember. Reuse this repo's existing log
convention (PLAN.md's Decisions log / Recommended roadmap / Explicitly-deferred
sections, and BACKLOG.md's open+done list); do NOT invent a new log file.

Trigger the log step "when it makes sense" — specifically when a run surfaces any
of: (a) deferred scope or a "later phase" that is really a roadmap item, not a
true non-goal; (b) a multi-phase roadmap the operator wants as the destination
while shipping a small v1; (c) a cross-cutting principle or decision that should
outlive the current PRD/issues; (d) an item explicitly decided-against-for-now.
Skip it for trivial one-off runs.

Concretely:

1. grill-me: when the interview parks something as "roadmap/deferred/decided
   against," tag it so the later stages know it belongs in the log, not just the
   conversation.

2. to-prd: after writing the PRD, if any roadmap/deferred/decided-against/
   principle items exist, RECOMMEND appending them to the durable running log
   (PLAN.md Decisions log + roadmap / Explicitly-deferred, or BACKLOG.md) — not
   only to the PRD's own Milestones section, which is easy to lose. Offer to make
   the edit and commit it (sessions may be ephemeral).

3. to-issues: when the roadmap outlives the current issue set, EMIT a small
   "update the running log / backlog" slice (as was done for Credit Review OS
   Slice 9) so the roadmap is a tracked, committed deliverable.

4. occam (orchestrator): at the end of a run, prompt to append a dated entry to
   the Decisions log summarizing what was decided and what was deferred — the
   default should be "yes, log it," with an easy skip.

Keep it lightweight and non-nagging: one offer at the natural moment, honoring
the operator's stated preference to not have to remember. Respect the
ephemeral-session reality — a log recommendation that isn't committed is lost, so
the step should include committing the change.
```

## Acceptance (how the architect knows it's done)

- A pipeline run that surfaces deferred scope or a roadmap **offers** (without
  being asked) to record it in `PLAN.md`/`BACKLOG.md`, and commits it.
- Trivial runs don't get nagged.
- `to-issues` emits a log/backlog-update slice when a roadmap outlives the issues.
- The behavior is documented in the skills' own instructions so it's discoverable.
